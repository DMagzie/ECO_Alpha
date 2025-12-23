"""
Zone-Level Cost Allocation Engine
==================================

Allocates building-level energy costs to individual zones for:
- Per-dwelling-unit LCCA
- Common area cost allocation
- CUAC utility allowance calculations
- Mixed-use building cost separation
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any
from datetime import date

from .zone_energy import (
    ZoneEnergySummary, ZoneLccaResult, BuildingZoneLccaSummary,
    DwellingUnitSummary, CommonAreaSummary, CuacAllowanceResult,
    filter_zones_by_type, group_zones_by_bedroom_count, group_zones_by_category,
)
from .cuac.models import ZoneType, DwellUnitAllocation, CuacConfig
from .res_other.models import CommonAreaCategory, ResOtherZone
from .tariffs import TouTariff, TouSchedule, TouRates, calculate_tou_costs, HourlyUsage
from .model import SimulationOutput


# =============================================================================
# ALLOCATION METHODS
# =============================================================================

class AllocationMethod:
    """Allocation method constants."""
    BY_AREA = "by_area"  # Proportional to conditioned area
    BY_CONSUMPTION = "by_consumption"  # Based on modeled consumption
    BY_UNIT_COUNT = "by_unit_count"  # Equal per dwelling unit
    BY_BEDROOM = "by_bedroom"  # Based on bedroom count
    BY_METER = "by_meter"  # Based on meter assignments


# =============================================================================
# ZONE COST ALLOCATOR
# =============================================================================

@dataclass
class ZoneCostAllocator:
    """
    Allocate building-level costs to individual zones.

    Supports multiple allocation strategies for different use cases:
    - Area-based: Proportional to conditioned floor area
    - Consumption-based: Using modeled zone energy
    - CUAC: Using bedroom-based allocations for affordable housing
    """

    # Input data
    zone_summaries: List[ZoneEnergySummary] = field(default_factory=list)
    tariff: Optional[TouTariff] = None

    # Building-level totals (for reconciliation)
    building_elec_kwh: float = 0.0
    building_gas_therm: float = 0.0

    # CUAC configuration (optional)
    cuac_config: Optional[CuacConfig] = None

    # Allocation settings
    allocation_method: str = AllocationMethod.BY_AREA

    def __post_init__(self):
        """Calculate derived values."""
        if self.zone_summaries and self.building_elec_kwh == 0:
            self.building_elec_kwh = sum(z.elec_kwh for z in self.zone_summaries)
            self.building_gas_therm = sum(z.gas_therm for z in self.zone_summaries)

    @property
    def total_area(self) -> float:
        """Total conditioned area."""
        return sum(z.area_sqft for z in self.zone_summaries)

    @property
    def dwelling_units(self) -> List[ZoneEnergySummary]:
        """Get dwelling unit zones."""
        return filter_zones_by_type(self.zone_summaries, ZoneType.DWELLING_UNIT)

    @property
    def common_areas(self) -> List[ZoneEnergySummary]:
        """Get common area zones."""
        return filter_zones_by_type(self.zone_summaries, ZoneType.COMMON_AREA)

    @property
    def dwelling_area(self) -> float:
        """Total dwelling unit area."""
        return sum(z.area_sqft for z in self.dwelling_units)

    @property
    def common_area(self) -> float:
        """Total common area."""
        return sum(z.area_sqft for z in self.common_areas)

    # -------------------------------------------------------------------------
    # Main allocation methods
    # -------------------------------------------------------------------------

    def allocate_all(self) -> BuildingZoneLccaSummary:
        """
        Allocate costs to all zones and return summary.

        Returns:
            BuildingZoneLccaSummary with all zone results
        """
        summary = BuildingZoneLccaSummary()

        for zone in self.zone_summaries:
            result = self.allocate_zone(zone)
            summary.add_result(result)

        # Calculate CUAC allowances if config provided
        if self.cuac_config:
            self._apply_cuac_allowances(summary)

        return summary

    def allocate_zone(self, zone: ZoneEnergySummary) -> ZoneLccaResult:
        """
        Allocate costs to a single zone.

        Args:
            zone: ZoneEnergySummary to allocate

        Returns:
            ZoneLccaResult with calculated costs
        """
        result = ZoneLccaResult(
            zone_name=zone.zone_name,
            zone_type=zone.zone_type,
            category=zone.category,
            annual_elec_kwh=zone.elec_kwh,
            annual_gas_therm=zone.gas_therm,
            area_sqft=zone.area_sqft,
            num_bedrooms=zone.num_bedrooms,
        )

        # Calculate electricity costs
        if zone.hourly_elec_kwh and self.tariff:
            result = self._calculate_tou_costs(zone, result)
        else:
            result = self._calculate_simple_costs(zone, result)

        # Apply PV/battery credits
        result = self._apply_pv_credits(zone, result)

        # Calculate net costs
        result.net_elec_cost = max(0, result.gross_elec_cost - result.pv_credit -
                                    result.battery_credit - result.nem_credit)
        result.net_gas_cost = result.gross_gas_cost
        result.net_total_cost = result.net_elec_cost + result.net_gas_cost

        # Per-unit metrics
        if result.area_sqft > 0:
            result.cost_per_sqft = result.net_total_cost / result.area_sqft
        if result.is_dwelling_unit:
            result.num_units = 1
            result.cost_per_unit = result.net_total_cost

        return result

    def _calculate_tou_costs(
        self,
        zone: ZoneEnergySummary,
        result: ZoneLccaResult
    ) -> ZoneLccaResult:
        """Calculate TOU costs from hourly data."""
        if not zone.hourly_elec_kwh or not self.tariff:
            return result

        # Convert to HourlyUsage format
        hourly_usage = []
        hour_of_year = 0
        for month in range(1, 13):
            days_in_month = self._days_in_month(month)
            for day in range(1, days_in_month + 1):
                for hour in range(24):
                    if hour_of_year < len(zone.hourly_elec_kwh):
                        is_weekend = date(2024, month, day).weekday() >= 5
                        hourly_usage.append(HourlyUsage(
                            month=month,
                            day=day,
                            hour=hour,
                            kwh=zone.hourly_elec_kwh[hour_of_year],
                            is_weekend=is_weekend
                        ))
                    hour_of_year += 1

        # Calculate TOU breakdown
        breakdown = calculate_tou_costs(hourly_usage, self.tariff)

        # Populate result
        result.summer_on_peak_cost = breakdown.summer_on_peak_cost
        result.summer_mid_peak_cost = breakdown.summer_mid_peak_cost
        result.summer_off_peak_cost = breakdown.summer_off_peak_cost
        result.winter_on_peak_cost = breakdown.winter_on_peak_cost
        result.winter_mid_peak_cost = breakdown.winter_mid_peak_cost
        result.winter_off_peak_cost = breakdown.winter_off_peak_cost
        result.gross_elec_cost = breakdown.total_energy_cost
        result.gross_demand_cost = breakdown.total_demand_cost
        result.gross_fixed_cost = breakdown.total_fixed_cost

        # Gas costs
        result.gross_gas_cost = zone.gas_therm * self.tariff.gas_rate

        return result

    def _calculate_simple_costs(
        self,
        zone: ZoneEnergySummary,
        result: ZoneLccaResult
    ) -> ZoneLccaResult:
        """Calculate simple costs using average rates."""
        if self.tariff:
            # Use weighted average of TOU rates
            avg_rate = (self.tariff.energy_rates.summer_off_peak * 0.4 +
                       self.tariff.energy_rates.summer_on_peak * 0.1 +
                       self.tariff.energy_rates.winter_off_peak * 0.4 +
                       self.tariff.energy_rates.winter_on_peak * 0.1)
            gas_rate = self.tariff.gas_rate
            fixed_monthly = self.tariff.monthly_customer_charge
        else:
            avg_rate = 0.25  # Default $/kWh
            gas_rate = 1.50  # Default $/therm
            fixed_monthly = 10.0

        result.gross_elec_cost = zone.elec_kwh * avg_rate
        result.gross_gas_cost = zone.gas_therm * gas_rate
        result.gross_fixed_cost = fixed_monthly * 12

        return result

    def _apply_pv_credits(
        self,
        zone: ZoneEnergySummary,
        result: ZoneLccaResult
    ) -> ZoneLccaResult:
        """Apply PV and battery credits."""
        if zone.pv_generation_kwh > 0 and self.tariff:
            # Value PV at weighted export rate (typically off-peak)
            export_rate = self.tariff.energy_rates.summer_off_peak * 0.8

            # Self-consumption valued at full retail
            self_consumption = min(zone.elec_kwh, zone.pv_generation_kwh)
            excess = max(0, zone.pv_generation_kwh - zone.elec_kwh)

            # Average retail rate for self-consumption value
            retail_rate = (self.tariff.energy_rates.summer_off_peak +
                          self.tariff.energy_rates.summer_on_peak) / 2

            result.pv_credit = (self_consumption * retail_rate +
                               excess * export_rate)

            if excess > 0:
                result.nem_credit = excess * export_rate

        return result

    def _apply_cuac_allowances(self, summary: BuildingZoneLccaSummary):
        """Apply CUAC utility allowances to dwelling unit summaries."""
        if not self.cuac_config:
            return

        for bedrooms, dwelling_summary in summary.dwelling_summaries.items():
            if dwelling_summary.unit_count > 0:
                # Calculate monthly allowance from annual cost
                monthly_allowance = dwelling_summary.avg_annual_cost / 12

                # Apply PV credit reduction
                pv_kwdc = self.cuac_config.allocate_pv_to_unit(bedrooms)
                if pv_kwdc > 0:
                    # Estimate PV generation and value
                    pv_kwh = pv_kwdc * 1500  # Rough CA capacity factor
                    if self.tariff:
                        pv_value = pv_kwh * self.tariff.energy_rates.summer_off_peak * 0.8
                        monthly_allowance = max(0, monthly_allowance - pv_value / 12)

                dwelling_summary.utility_allowance_monthly = monthly_allowance
                dwelling_summary.pv_per_unit_kwdc = pv_kwdc
                dwelling_summary.battery_per_unit_kwh = self.cuac_config.allocate_battery_to_unit(bedrooms)

    def _days_in_month(self, month: int, year: int = 2024) -> int:
        """Get days in month."""
        days = [31, 29 if year % 4 == 0 else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
        return days[month - 1]

    # -------------------------------------------------------------------------
    # Area-based allocation
    # -------------------------------------------------------------------------

    def allocate_by_area(
        self,
        total_cost: float
    ) -> Dict[str, float]:
        """
        Allocate a total cost proportionally by area.

        Args:
            total_cost: Total cost to allocate

        Returns:
            Dict of {zone_name: allocated_cost}
        """
        allocations = {}
        total_area = self.total_area

        if total_area <= 0:
            return allocations

        for zone in self.zone_summaries:
            fraction = zone.area_sqft / total_area
            allocations[zone.zone_name] = total_cost * fraction

        return allocations

    def allocate_common_costs_to_units(
        self,
        common_cost: float,
        method: str = AllocationMethod.BY_AREA
    ) -> Dict[str, float]:
        """
        Allocate common area costs to dwelling units.

        Args:
            common_cost: Total common area cost to allocate
            method: Allocation method

        Returns:
            Dict of {zone_name: allocated_cost} for dwelling units only
        """
        allocations = {}
        dwelling_units = self.dwelling_units

        if not dwelling_units:
            return allocations

        if method == AllocationMethod.BY_AREA:
            total_dwelling_area = self.dwelling_area
            for zone in dwelling_units:
                fraction = zone.area_sqft / total_dwelling_area if total_dwelling_area > 0 else 0
                allocations[zone.zone_name] = common_cost * fraction

        elif method == AllocationMethod.BY_UNIT_COUNT:
            per_unit = common_cost / len(dwelling_units)
            for zone in dwelling_units:
                allocations[zone.zone_name] = per_unit

        elif method == AllocationMethod.BY_BEDROOM:
            total_bedrooms = sum(z.num_bedrooms or 1 for z in dwelling_units)
            for zone in dwelling_units:
                bedrooms = zone.num_bedrooms or 1
                fraction = bedrooms / total_bedrooms if total_bedrooms > 0 else 0
                allocations[zone.zone_name] = common_cost * fraction

        return allocations

    # -------------------------------------------------------------------------
    # Meter-based allocation
    # -------------------------------------------------------------------------

    def allocate_by_meter_category(self) -> Dict[CommonAreaCategory, ZoneLccaResult]:
        """
        Aggregate costs by common area meter category.

        Returns:
            Dict of {category: aggregated_result}
        """
        category_results: Dict[CommonAreaCategory, ZoneLccaResult] = {}
        category_groups = group_zones_by_category(self.zone_summaries)

        for category, zones in category_groups.items():
            # Create aggregated result
            agg_result = ZoneLccaResult(
                zone_name=f"Common-{category.value.title()}",
                zone_type=ZoneType.COMMON_AREA,
                category=category,
            )

            for zone in zones:
                zone_result = self.allocate_zone(zone)
                agg_result.annual_elec_kwh += zone_result.annual_elec_kwh
                agg_result.annual_gas_therm += zone_result.annual_gas_therm
                agg_result.gross_elec_cost += zone_result.gross_elec_cost
                agg_result.gross_gas_cost += zone_result.gross_gas_cost
                agg_result.net_total_cost += zone_result.net_total_cost
                agg_result.area_sqft += zone_result.area_sqft

            category_results[category] = agg_result

        return category_results

    # -------------------------------------------------------------------------
    # Dwelling unit allocation
    # -------------------------------------------------------------------------

    def allocate_dwelling_units(self) -> List[ZoneLccaResult]:
        """
        Calculate per-unit LCCA for dwelling units.

        Returns:
            List of ZoneLccaResult for dwelling units only
        """
        results = []
        for zone in self.dwelling_units:
            result = self.allocate_zone(zone)
            results.append(result)
        return results

    def calculate_cuac_allowances(self) -> Dict[int, CuacAllowanceResult]:
        """
        Calculate CUAC utility allowances by bedroom count.

        Returns:
            Dict of {num_bedrooms: CuacAllowanceResult}
        """
        allowances: Dict[int, CuacAllowanceResult] = {}
        bedroom_groups = group_zones_by_bedroom_count(self.zone_summaries)

        for num_bedrooms, zones in bedroom_groups.items():
            # Aggregate zone results
            total_elec_kwh = sum(z.elec_kwh for z in zones)
            total_gas_therm = sum(z.gas_therm for z in zones)
            unit_count = len(zones)

            if unit_count == 0:
                continue

            avg_elec_kwh = total_elec_kwh / unit_count
            avg_gas_therm = total_gas_therm / unit_count

            # Calculate costs
            if self.tariff:
                avg_rate = (self.tariff.energy_rates.summer_off_peak +
                           self.tariff.energy_rates.winter_off_peak) / 2
                gas_rate = self.tariff.gas_rate
            else:
                avg_rate = 0.25
                gas_rate = 1.50

            annual_elec_cost = avg_elec_kwh * avg_rate
            annual_gas_cost = avg_gas_therm * gas_rate

            # Create allowance result
            allowance = CuacAllowanceResult(num_bedrooms=num_bedrooms)

            # Simplified allocation to components (would need actual end-use data)
            allowance.elec_cooling_allowance = annual_elec_cost * 0.25 / 12
            allowance.elec_heating_allowance = annual_elec_cost * 0.15 / 12
            allowance.elec_water_heating_allowance = annual_elec_cost * 0.20 / 12
            allowance.elec_lighting_allowance = annual_elec_cost * 0.15 / 12
            allowance.elec_other_allowance = annual_elec_cost * 0.25 / 12

            allowance.gas_heating_allowance = annual_gas_cost * 0.60 / 12
            allowance.gas_water_heating_allowance = annual_gas_cost * 0.35 / 12
            allowance.gas_cooking_allowance = annual_gas_cost * 0.05 / 12

            # Apply PV credits if CUAC config available
            if self.cuac_config:
                pv_kwdc = self.cuac_config.allocate_pv_to_unit(num_bedrooms)
                if pv_kwdc > 0:
                    pv_kwh_annual = pv_kwdc * 1500  # Rough estimate
                    pv_value = pv_kwh_annual * avg_rate
                    allowance.pv_credit_monthly = pv_value / 12

            allowances[num_bedrooms] = allowance

        return allowances


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def create_zone_allocator(
    simulation: SimulationOutput,
    zone_allocations: List[DwellUnitAllocation],
    tariff: TouTariff,
    cuac_config: Optional[CuacConfig] = None,
) -> ZoneCostAllocator:
    """
    Create a ZoneCostAllocator from simulation data.

    Args:
        simulation: SimulationOutput from parser
        zone_allocations: List of zone allocations from CUAC parser
        tariff: TOU tariff for cost calculations
        cuac_config: Optional CUAC configuration

    Returns:
        Configured ZoneCostAllocator
    """
    zone_summaries = []

    for alloc in zone_allocations:
        summary = ZoneEnergySummary(
            zone_name=alloc.zone_name,
            zone_type=alloc.zone_type,
            category=None,
            area_sqft=alloc.floor_area_sqft,
            num_bedrooms=alloc.bedroom_count or 0,
            multiplier=alloc.multiplier,
            pv_allocation_kwdc=alloc.prescriptive_pv_kwdc,
            battery_allocation_kwh=alloc.prescriptive_batt_kwh,
        )

        # Set category for common areas
        if summary.zone_type == ZoneType.COMMON_AREA:
            from .res_other.models import classify_space_function
            summary.category = classify_space_function(alloc.space_function)

        zone_summaries.append(summary)

    # Get building-level totals from simulation
    building_elec = simulation.annual.elec_total_kwh if simulation.annual else 0.0
    building_gas = simulation.annual.gas_total_therm if simulation.annual else 0.0

    return ZoneCostAllocator(
        zone_summaries=zone_summaries,
        tariff=tariff,
        building_elec_kwh=building_elec,
        building_gas_therm=building_gas,
        cuac_config=cuac_config,
    )


def calculate_zone_lcca(
    zone_summaries: List[ZoneEnergySummary],
    tariff: TouTariff,
    cuac_config: Optional[CuacConfig] = None,
) -> BuildingZoneLccaSummary:
    """
    Calculate complete zone-level LCCA.

    Args:
        zone_summaries: List of zone energy summaries
        tariff: TOU tariff for cost calculations
        cuac_config: Optional CUAC configuration

    Returns:
        BuildingZoneLccaSummary with all results
    """
    allocator = ZoneCostAllocator(
        zone_summaries=zone_summaries,
        tariff=tariff,
        cuac_config=cuac_config,
    )
    return allocator.allocate_all()


def estimate_zone_energy_from_building(
    building_elec_kwh: float,
    building_gas_therm: float,
    zone_allocations: List[DwellUnitAllocation],
    method: str = AllocationMethod.BY_AREA,
) -> List[ZoneEnergySummary]:
    """
    Estimate zone energy from building totals.

    Useful when zone-level energy data is not available.

    Args:
        building_elec_kwh: Building total electricity
        building_gas_therm: Building total gas
        zone_allocations: Zone allocation data
        method: Allocation method

    Returns:
        List of ZoneEnergySummary with estimated consumption
    """
    total_area = sum(a.floor_area_sqft for a in zone_allocations)
    if total_area <= 0:
        return []

    summaries = []
    for alloc in zone_allocations:
        fraction = alloc.floor_area_sqft / total_area

        summary = ZoneEnergySummary(
            zone_name=alloc.zone_name,
            zone_type=alloc.zone_type,
            elec_kwh=building_elec_kwh * fraction,
            gas_therm=building_gas_therm * fraction,
            area_sqft=alloc.floor_area_sqft,
            num_bedrooms=alloc.bedroom_count or 0,
            multiplier=alloc.multiplier,
            pv_allocation_kwdc=alloc.prescriptive_pv_kwdc,
            battery_allocation_kwh=alloc.prescriptive_batt_kwh,
        )

        if summary.zone_type == ZoneType.COMMON_AREA:
            from .res_other.models import classify_space_function
            summary.category = classify_space_function(alloc.space_function)

        summaries.append(summary)

    return summaries


def format_zone_lcca_summary(summary: BuildingZoneLccaSummary) -> str:
    """
    Format zone LCCA summary as text report.

    Args:
        summary: BuildingZoneLccaSummary

    Returns:
        Formatted text report
    """
    lines = [
        "=" * 70,
        "ZONE-LEVEL LCCA SUMMARY",
        "=" * 70,
        "",
        f"Building: {summary.building_name or 'N/A'}",
        f"Total Area: {summary.total_area_sqft:,.0f} sqft",
        f"Dwelling Units: {summary.dwelling_unit_count}",
        f"Common Area Zones: {summary.common_area_count}",
        "",
        "-" * 70,
        "ANNUAL COSTS",
        "-" * 70,
        f"  Total Electricity: {summary.total_elec_kwh:,.0f} kWh",
        f"  Total Gas: {summary.total_gas_therm:,.0f} therms",
        f"  Total Annual Cost: ${summary.total_annual_cost:,.2f}",
        f"    Dwelling Units: ${summary.dwelling_unit_cost:,.2f}",
        f"    Common Areas: ${summary.common_area_cost:,.2f}",
        "",
    ]

    # Dwelling unit summary
    if summary.dwelling_summaries:
        lines.extend([
            "-" * 70,
            "DWELLING UNITS BY BEDROOM COUNT",
            "-" * 70,
        ])
        for bedrooms in sorted(summary.dwelling_summaries.keys()):
            ds = summary.dwelling_summaries[bedrooms]
            lines.append(
                f"  {bedrooms}-BR: {ds.unit_count} units, "
                f"${ds.avg_annual_cost:,.2f}/yr avg, "
                f"${ds.utility_allowance_monthly:,.2f}/mo allowance"
            )
        lines.append("")

    # Common area summary
    if summary.common_summaries:
        lines.extend([
            "-" * 70,
            "COMMON AREAS BY CATEGORY",
            "-" * 70,
        ])
        for category in sorted(summary.common_summaries.keys(), key=lambda x: x.value):
            cs = summary.common_summaries[category]
            lines.append(
                f"  {category.value.title()}: {cs.zone_count} zones, "
                f"{cs.total_area_sqft:,.0f} sqft, "
                f"${cs.total_annual_cost:,.2f}/yr"
            )
        lines.append("")

    lines.append("=" * 70)

    return "\n".join(lines)
