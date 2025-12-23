"""
Zone-Level Energy Data Models
=============================

Data classes for zone-level energy consumption and LCCA results.

These models enable:
- Per-zone energy tracking (dwelling units and common areas)
- Zone-level cost calculations with TOU rates
- CUAC utility allowance computation
- Integration with building-level LCCA
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any
from enum import Enum

from .cuac.models import ZoneType, DwellUnitAllocation, classify_zone_type
from .res_other.models import CommonAreaCategory, classify_space_function


# =============================================================================
# ZONE ENERGY SUMMARY
# =============================================================================

@dataclass
class ZoneEnergySummary:
    """
    Energy consumption summary for a single zone.

    Captures annual energy use, peak demand, and renewable allocations
    for either a dwelling unit or common area zone.
    """
    zone_name: str
    zone_type: ZoneType
    category: Optional[CommonAreaCategory] = None  # For common areas

    # Annual energy consumption
    elec_kwh: float = 0.0
    gas_therm: float = 0.0

    # Peak demand
    peak_demand_kw: float = 0.0

    # End-use breakdown (from CSE hourly data)
    cooling_kwh: float = 0.0
    heating_kwh: float = 0.0
    heating_therm: float = 0.0
    lighting_kwh: float = 0.0
    receptacle_kwh: float = 0.0
    dhw_kwh: float = 0.0
    dhw_therm: float = 0.0
    ventilation_kwh: float = 0.0
    other_kwh: float = 0.0

    # Zone characteristics
    area_sqft: float = 0.0
    num_bedrooms: int = 0  # For dwelling units
    multiplier: int = 1

    # PV/Battery allocations
    pv_allocation_kwdc: float = 0.0
    pv_generation_kwh: float = 0.0
    battery_allocation_kwh: float = 0.0
    battery_allocation_kw: float = 0.0

    # Hourly data reference (for TOU calculations)
    hourly_elec_kwh: Optional[List[float]] = None  # 8760 values
    hourly_gas_therm: Optional[List[float]] = None  # 8760 values

    @property
    def total_area(self) -> float:
        """Total area including multiplier."""
        return self.area_sqft * self.multiplier

    @property
    def eui_kbtu_sqft(self) -> float:
        """Energy Use Intensity in kBtu/sqft."""
        if self.area_sqft <= 0:
            return 0.0
        elec_kbtu = self.elec_kwh * 3.412
        gas_kbtu = self.gas_therm * 100
        return (elec_kbtu + gas_kbtu) / self.area_sqft

    @property
    def elec_eui_kbtu_sqft(self) -> float:
        """Electric EUI in kBtu/sqft."""
        if self.area_sqft <= 0:
            return 0.0
        return (self.elec_kwh * 3.412) / self.area_sqft

    @property
    def gas_eui_kbtu_sqft(self) -> float:
        """Gas EUI in kBtu/sqft."""
        if self.area_sqft <= 0:
            return 0.0
        return (self.gas_therm * 100) / self.area_sqft

    @property
    def net_elec_kwh(self) -> float:
        """Net electricity after PV generation."""
        return max(0, self.elec_kwh - self.pv_generation_kwh)

    @property
    def pv_offset_pct(self) -> float:
        """Percentage of consumption offset by PV."""
        if self.elec_kwh <= 0:
            return 0.0
        return min(100.0, (self.pv_generation_kwh / self.elec_kwh) * 100)

    @property
    def is_dwelling_unit(self) -> bool:
        """True if this is a dwelling unit zone."""
        return self.zone_type == ZoneType.DWELLING_UNIT

    @property
    def is_common_area(self) -> bool:
        """True if this is a common area zone."""
        return self.zone_type == ZoneType.COMMON_AREA

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'zone_name': self.zone_name,
            'zone_type': self.zone_type.value,
            'category': self.category.value if self.category else None,
            'elec_kwh': self.elec_kwh,
            'gas_therm': self.gas_therm,
            'peak_demand_kw': self.peak_demand_kw,
            'area_sqft': self.area_sqft,
            'num_bedrooms': self.num_bedrooms,
            'eui_kbtu_sqft': self.eui_kbtu_sqft,
            'pv_allocation_kwdc': self.pv_allocation_kwdc,
            'pv_generation_kwh': self.pv_generation_kwh,
            'net_elec_kwh': self.net_elec_kwh,
        }


@dataclass
class ZoneEnergySummaryBuilder:
    """Builder for constructing ZoneEnergySummary from various sources."""

    @staticmethod
    def from_allocation(
        allocation: DwellUnitAllocation,
        elec_kwh: float = 0.0,
        gas_therm: float = 0.0,
        peak_demand_kw: float = 0.0,
    ) -> ZoneEnergySummary:
        """
        Create ZoneEnergySummary from a DwellUnitAllocation.

        Args:
            allocation: DwellUnitAllocation from CUAC parser
            elec_kwh: Annual electricity consumption
            gas_therm: Annual gas consumption
            peak_demand_kw: Peak demand

        Returns:
            ZoneEnergySummary
        """
        zone_type = allocation.zone_type
        category = None
        if zone_type == ZoneType.COMMON_AREA:
            category = classify_space_function(allocation.space_function)

        return ZoneEnergySummary(
            zone_name=allocation.zone_name,
            zone_type=zone_type,
            category=category,
            elec_kwh=elec_kwh,
            gas_therm=gas_therm,
            peak_demand_kw=peak_demand_kw,
            area_sqft=allocation.floor_area_sqft,
            num_bedrooms=allocation.bedroom_count or 0,
            multiplier=allocation.multiplier,
            pv_allocation_kwdc=allocation.prescriptive_pv_kwdc,
            battery_allocation_kwh=allocation.prescriptive_batt_kwh,
            battery_allocation_kw=allocation.prescriptive_batt_kw,
        )


# =============================================================================
# ZONE LCCA RESULT
# =============================================================================

@dataclass
class ZoneLccaResult:
    """
    LCCA results for a single zone.

    Contains annual costs, TOU breakdown, and CUAC utility allowance.
    """
    zone_name: str
    zone_type: ZoneType
    category: Optional[CommonAreaCategory] = None

    # Energy consumption
    annual_elec_kwh: float = 0.0
    annual_gas_therm: float = 0.0

    # Gross energy costs (before PV/battery credits)
    gross_elec_cost: float = 0.0
    gross_gas_cost: float = 0.0
    gross_demand_cost: float = 0.0
    gross_fixed_cost: float = 0.0

    # TOU breakdown (electricity only)
    summer_on_peak_cost: float = 0.0
    summer_mid_peak_cost: float = 0.0
    summer_off_peak_cost: float = 0.0
    winter_on_peak_cost: float = 0.0
    winter_mid_peak_cost: float = 0.0
    winter_off_peak_cost: float = 0.0

    # PV/Battery credits
    pv_credit: float = 0.0
    battery_credit: float = 0.0
    nem_credit: float = 0.0  # Net export credit

    # Net annual costs
    net_elec_cost: float = 0.0
    net_gas_cost: float = 0.0
    net_total_cost: float = 0.0

    # Per-unit metrics (for dwelling units)
    num_units: int = 1
    cost_per_unit: float = 0.0
    cost_per_sqft: float = 0.0

    # CUAC utility allowance
    utility_allowance_monthly: float = 0.0
    utility_allowance_annual: float = 0.0

    # Area for reference
    area_sqft: float = 0.0
    num_bedrooms: int = 0

    @property
    def gross_total_cost(self) -> float:
        """Total gross cost before credits."""
        return (self.gross_elec_cost + self.gross_gas_cost +
                self.gross_demand_cost + self.gross_fixed_cost)

    @property
    def total_credits(self) -> float:
        """Total credits (PV + battery + NEM)."""
        return self.pv_credit + self.battery_credit + self.nem_credit

    @property
    def is_dwelling_unit(self) -> bool:
        """True if this is a dwelling unit zone."""
        return self.zone_type == ZoneType.DWELLING_UNIT

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'zone_name': self.zone_name,
            'zone_type': self.zone_type.value,
            'category': self.category.value if self.category else None,
            'annual_elec_kwh': self.annual_elec_kwh,
            'annual_gas_therm': self.annual_gas_therm,
            'gross_elec_cost': self.gross_elec_cost,
            'gross_gas_cost': self.gross_gas_cost,
            'gross_total_cost': self.gross_total_cost,
            'pv_credit': self.pv_credit,
            'net_total_cost': self.net_total_cost,
            'utility_allowance_monthly': self.utility_allowance_monthly,
            'area_sqft': self.area_sqft,
            'num_bedrooms': self.num_bedrooms,
        }


# =============================================================================
# AGGREGATED RESULTS
# =============================================================================

@dataclass
class DwellingUnitSummary:
    """Summary of all dwelling units by bedroom count."""
    num_bedrooms: int
    unit_count: int = 0
    total_area_sqft: float = 0.0

    # Totals for this bedroom count
    total_elec_kwh: float = 0.0
    total_gas_therm: float = 0.0
    total_annual_cost: float = 0.0

    # Per-unit averages
    avg_elec_kwh: float = 0.0
    avg_gas_therm: float = 0.0
    avg_annual_cost: float = 0.0
    avg_area_sqft: float = 0.0

    # CUAC allowance for this bedroom count
    utility_allowance_monthly: float = 0.0

    # PV/Battery allocations
    pv_per_unit_kwdc: float = 0.0
    battery_per_unit_kwh: float = 0.0

    def add_unit(self, result: ZoneLccaResult):
        """Add a unit's results to this summary."""
        self.unit_count += 1
        self.total_area_sqft += result.area_sqft
        self.total_elec_kwh += result.annual_elec_kwh
        self.total_gas_therm += result.annual_gas_therm
        self.total_annual_cost += result.net_total_cost

        # Update averages
        if self.unit_count > 0:
            self.avg_elec_kwh = self.total_elec_kwh / self.unit_count
            self.avg_gas_therm = self.total_gas_therm / self.unit_count
            self.avg_annual_cost = self.total_annual_cost / self.unit_count
            self.avg_area_sqft = self.total_area_sqft / self.unit_count


@dataclass
class CommonAreaSummary:
    """Summary of all common areas by category."""
    category: CommonAreaCategory
    zone_count: int = 0
    total_area_sqft: float = 0.0

    # Energy totals
    total_elec_kwh: float = 0.0
    total_gas_therm: float = 0.0
    total_annual_cost: float = 0.0

    # EUI metrics
    eui_kbtu_sqft: float = 0.0
    cost_per_sqft: float = 0.0

    zone_names: List[str] = field(default_factory=list)

    def add_zone(self, result: ZoneLccaResult):
        """Add a zone's results to this summary."""
        self.zone_count += 1
        self.total_area_sqft += result.area_sqft
        self.total_elec_kwh += result.annual_elec_kwh
        self.total_gas_therm += result.annual_gas_therm
        self.total_annual_cost += result.net_total_cost
        self.zone_names.append(result.zone_name)

        # Update metrics
        if self.total_area_sqft > 0:
            elec_kbtu = self.total_elec_kwh * 3.412
            gas_kbtu = self.total_gas_therm * 100
            self.eui_kbtu_sqft = (elec_kbtu + gas_kbtu) / self.total_area_sqft
            self.cost_per_sqft = self.total_annual_cost / self.total_area_sqft


@dataclass
class BuildingZoneLccaSummary:
    """
    Complete zone-level LCCA summary for a building.

    Aggregates results by zone type and category.
    """
    building_name: str = ""
    total_area_sqft: float = 0.0

    # Zone counts
    dwelling_unit_count: int = 0
    common_area_count: int = 0

    # Building-level totals
    total_elec_kwh: float = 0.0
    total_gas_therm: float = 0.0
    total_annual_cost: float = 0.0

    # Dwelling unit summaries by bedroom count
    dwelling_summaries: Dict[int, DwellingUnitSummary] = field(default_factory=dict)

    # Common area summaries by category
    common_summaries: Dict[CommonAreaCategory, CommonAreaSummary] = field(default_factory=dict)

    # Individual zone results
    zone_results: List[ZoneLccaResult] = field(default_factory=list)

    @property
    def dwelling_unit_cost(self) -> float:
        """Total cost for all dwelling units."""
        return sum(s.total_annual_cost for s in self.dwelling_summaries.values())

    @property
    def common_area_cost(self) -> float:
        """Total cost for all common areas."""
        return sum(s.total_annual_cost for s in self.common_summaries.values())

    @property
    def dwelling_unit_area(self) -> float:
        """Total area for all dwelling units."""
        return sum(s.total_area_sqft for s in self.dwelling_summaries.values())

    @property
    def common_area_total(self) -> float:
        """Total area for all common areas."""
        return sum(s.total_area_sqft for s in self.common_summaries.values())

    def add_result(self, result: ZoneLccaResult):
        """Add a zone result to the summary."""
        self.zone_results.append(result)
        self.total_elec_kwh += result.annual_elec_kwh
        self.total_gas_therm += result.annual_gas_therm
        self.total_annual_cost += result.net_total_cost
        self.total_area_sqft += result.area_sqft

        if result.is_dwelling_unit:
            self.dwelling_unit_count += 1
            bedrooms = result.num_bedrooms
            if bedrooms not in self.dwelling_summaries:
                self.dwelling_summaries[bedrooms] = DwellingUnitSummary(
                    num_bedrooms=bedrooms
                )
            self.dwelling_summaries[bedrooms].add_unit(result)
        else:
            self.common_area_count += 1
            category = result.category or CommonAreaCategory.OTHER
            if category not in self.common_summaries:
                self.common_summaries[category] = CommonAreaSummary(
                    category=category
                )
            self.common_summaries[category].add_zone(result)

    def get_dwelling_summary_by_bedrooms(self, num_bedrooms: int) -> Optional[DwellingUnitSummary]:
        """Get summary for a specific bedroom count."""
        return self.dwelling_summaries.get(num_bedrooms)

    def get_common_summary_by_category(self, category: CommonAreaCategory) -> Optional[CommonAreaSummary]:
        """Get summary for a specific common area category."""
        return self.common_summaries.get(category)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'building_name': self.building_name,
            'total_area_sqft': self.total_area_sqft,
            'dwelling_unit_count': self.dwelling_unit_count,
            'common_area_count': self.common_area_count,
            'total_elec_kwh': self.total_elec_kwh,
            'total_gas_therm': self.total_gas_therm,
            'total_annual_cost': self.total_annual_cost,
            'dwelling_unit_cost': self.dwelling_unit_cost,
            'common_area_cost': self.common_area_cost,
            'dwelling_summaries': {
                k: {
                    'num_bedrooms': v.num_bedrooms,
                    'unit_count': v.unit_count,
                    'total_area_sqft': v.total_area_sqft,
                    'avg_annual_cost': v.avg_annual_cost,
                    'utility_allowance_monthly': v.utility_allowance_monthly,
                }
                for k, v in self.dwelling_summaries.items()
            },
            'common_summaries': {
                k.value: {
                    'category': k.value,
                    'zone_count': v.zone_count,
                    'total_area_sqft': v.total_area_sqft,
                    'total_annual_cost': v.total_annual_cost,
                    'eui_kbtu_sqft': v.eui_kbtu_sqft,
                }
                for k, v in self.common_summaries.items()
            },
        }


# =============================================================================
# CUAC UTILITY ALLOWANCE
# =============================================================================

@dataclass
class CuacAllowanceResult:
    """
    CUAC utility allowance calculation result.

    Contains the monthly allowance by bedroom count per HUD guidelines.
    """
    num_bedrooms: int

    # Monthly allowance components
    elec_heating_allowance: float = 0.0
    elec_cooling_allowance: float = 0.0
    elec_cooking_allowance: float = 0.0
    elec_water_heating_allowance: float = 0.0
    elec_lighting_allowance: float = 0.0
    elec_other_allowance: float = 0.0

    gas_heating_allowance: float = 0.0
    gas_cooking_allowance: float = 0.0
    gas_water_heating_allowance: float = 0.0

    # PV/Battery credits (reduces allowance)
    pv_credit_monthly: float = 0.0
    battery_credit_monthly: float = 0.0

    @property
    def gross_elec_allowance(self) -> float:
        """Gross electric allowance before credits."""
        return (self.elec_heating_allowance + self.elec_cooling_allowance +
                self.elec_cooking_allowance + self.elec_water_heating_allowance +
                self.elec_lighting_allowance + self.elec_other_allowance)

    @property
    def gross_gas_allowance(self) -> float:
        """Gross gas allowance."""
        return (self.gas_heating_allowance + self.gas_cooking_allowance +
                self.gas_water_heating_allowance)

    @property
    def gross_total_allowance(self) -> float:
        """Gross total allowance before credits."""
        return self.gross_elec_allowance + self.gross_gas_allowance

    @property
    def net_total_allowance(self) -> float:
        """Net allowance after PV/battery credits."""
        return max(0, self.gross_total_allowance -
                   self.pv_credit_monthly - self.battery_credit_monthly)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for CUAC report."""
        return {
            'num_bedrooms': self.num_bedrooms,
            'gross_elec_allowance': self.gross_elec_allowance,
            'gross_gas_allowance': self.gross_gas_allowance,
            'gross_total_allowance': self.gross_total_allowance,
            'pv_credit_monthly': self.pv_credit_monthly,
            'battery_credit_monthly': self.battery_credit_monthly,
            'net_total_allowance': self.net_total_allowance,
        }


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def create_zone_energy_from_hourly(
    zone_name: str,
    zone_type: ZoneType,
    hourly_elec: List[float],
    hourly_gas: Optional[List[float]] = None,
    area_sqft: float = 0.0,
    num_bedrooms: int = 0,
    category: Optional[CommonAreaCategory] = None,
) -> ZoneEnergySummary:
    """
    Create ZoneEnergySummary from hourly data.

    Args:
        zone_name: Zone name
        zone_type: ZoneType enum
        hourly_elec: 8760 hourly electricity values (kWh)
        hourly_gas: 8760 hourly gas values (therm), optional
        area_sqft: Zone area
        num_bedrooms: Bedroom count (for dwelling units)
        category: CommonAreaCategory (for common areas)

    Returns:
        ZoneEnergySummary with calculated totals
    """
    summary = ZoneEnergySummary(
        zone_name=zone_name,
        zone_type=zone_type,
        category=category,
        area_sqft=area_sqft,
        num_bedrooms=num_bedrooms,
    )

    if hourly_elec:
        summary.elec_kwh = sum(hourly_elec)
        summary.peak_demand_kw = max(hourly_elec) if hourly_elec else 0.0
        summary.hourly_elec_kwh = hourly_elec

    if hourly_gas:
        summary.gas_therm = sum(hourly_gas)
        summary.hourly_gas_therm = hourly_gas

    return summary


def aggregate_zone_energies(
    zone_summaries: List[ZoneEnergySummary]
) -> Tuple[float, float, float]:
    """
    Aggregate zone energy summaries.

    Args:
        zone_summaries: List of ZoneEnergySummary

    Returns:
        Tuple of (total_elec_kwh, total_gas_therm, total_area_sqft)
    """
    total_elec = sum(z.elec_kwh for z in zone_summaries)
    total_gas = sum(z.gas_therm for z in zone_summaries)
    total_area = sum(z.area_sqft for z in zone_summaries)
    return total_elec, total_gas, total_area


def filter_zones_by_type(
    zone_summaries: List[ZoneEnergySummary],
    zone_type: ZoneType
) -> List[ZoneEnergySummary]:
    """Filter zone summaries by type."""
    return [z for z in zone_summaries if z.zone_type == zone_type]


def filter_zones_by_category(
    zone_summaries: List[ZoneEnergySummary],
    category: CommonAreaCategory
) -> List[ZoneEnergySummary]:
    """Filter zone summaries by common area category."""
    return [z for z in zone_summaries if z.category == category]


def group_zones_by_bedroom_count(
    zone_summaries: List[ZoneEnergySummary]
) -> Dict[int, List[ZoneEnergySummary]]:
    """Group dwelling unit zones by bedroom count."""
    groups: Dict[int, List[ZoneEnergySummary]] = {}
    for z in zone_summaries:
        if z.is_dwelling_unit:
            bedrooms = z.num_bedrooms
            if bedrooms not in groups:
                groups[bedrooms] = []
            groups[bedrooms].append(z)
    return groups


def group_zones_by_category(
    zone_summaries: List[ZoneEnergySummary]
) -> Dict[CommonAreaCategory, List[ZoneEnergySummary]]:
    """Group common area zones by category."""
    groups: Dict[CommonAreaCategory, List[ZoneEnergySummary]] = {}
    for z in zone_summaries:
        if z.is_common_area and z.category:
            if z.category not in groups:
                groups[z.category] = []
            groups[z.category].append(z)
    return groups
