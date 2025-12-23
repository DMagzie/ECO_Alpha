"""
Meter Category Aggregation Engine
=================================

Aggregates zone-level energy data into meter categories for:
- Common area meter rollups (LOBBY, CORRIDOR, PARKING, etc.)
- Mixed-use building separation (Residential vs Commercial)
- Master meter allocation and reconciliation
- Multiple tariff support for different building sections

Phase 4 of LCCA module development.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any, Union
from enum import Enum

from .zone_energy import ZoneEnergySummary, ZoneLccaResult, BuildingZoneLccaSummary
from .cuac.models import ZoneType
from .res_other.models import CommonAreaCategory, ResOtherZone
from .tariffs import TouTariff
from .model import SimulationOutput, AnnualEnergySummary


# =============================================================================
# BUILDING SECTION TYPES
# =============================================================================

class BuildingSectionType(Enum):
    """
    Building section types for mixed-use buildings.

    Each section may have different tariffs and cost allocation methods.
    """
    RESIDENTIAL = "residential"          # Dwelling units
    COMMON_AREA = "common_area"          # Shared residential spaces
    COMMERCIAL = "commercial"            # Retail, office, etc.
    PARKING = "parking"                  # Parking structure
    AMENITY = "amenity"                  # Fitness, pool, etc.

    @classmethod
    def from_zone_type(cls, zone_type: ZoneType) -> "BuildingSectionType":
        """Map ZoneType to BuildingSectionType."""
        if zone_type == ZoneType.DWELLING_UNIT:
            return cls.RESIDENTIAL
        elif zone_type == ZoneType.COMMON_AREA:
            return cls.COMMON_AREA
        elif zone_type == ZoneType.NONRESIDENTIAL:
            return cls.COMMERCIAL
        else:
            return cls.COMMON_AREA  # Default unconditioned to common


# =============================================================================
# METER CATEGORY AGGREGATE
# =============================================================================

@dataclass
class MeterCategoryAggregate:
    """
    Aggregated energy data for a common area meter category.

    Groups multiple zones of the same category (e.g., all corridors)
    into a single meter category for cost allocation.
    """
    category: CommonAreaCategory
    meter_name: str

    # Constituent zones
    zones: List[ZoneEnergySummary] = field(default_factory=list)

    # Aggregated energy
    total_elec_kwh: float = 0.0
    total_gas_therm: float = 0.0
    peak_demand_kw: float = 0.0

    # End-use breakdown
    cooling_kwh: float = 0.0
    heating_kwh: float = 0.0
    heating_therm: float = 0.0
    lighting_kwh: float = 0.0
    ventilation_kwh: float = 0.0
    receptacle_kwh: float = 0.0

    # Area totals
    total_area_sqft: float = 0.0
    conditioned_area_sqft: float = 0.0

    # LCCA results (calculated after cost allocation)
    annual_cost: float = 0.0
    cost_per_sqft: float = 0.0

    @property
    def zone_count(self) -> int:
        """Number of zones in this category."""
        return len(self.zones)

    @property
    def zone_names(self) -> List[str]:
        """List of zone names."""
        return [z.zone_name for z in self.zones]

    @property
    def eui_kbtu_sqft(self) -> float:
        """Combined EUI for this meter category."""
        if self.total_area_sqft <= 0:
            return 0.0
        elec_kbtu = self.total_elec_kwh * 3.412
        gas_kbtu = self.total_gas_therm * 100
        return (elec_kbtu + gas_kbtu) / self.total_area_sqft

    @property
    def elec_intensity_kwh_sqft(self) -> float:
        """Electric intensity in kWh/sqft."""
        if self.total_area_sqft <= 0:
            return 0.0
        return self.total_elec_kwh / self.total_area_sqft

    def add_zone(self, zone: ZoneEnergySummary) -> None:
        """
        Add a zone to this meter category aggregate.

        Updates all aggregate totals.
        """
        self.zones.append(zone)

        # Update energy totals
        self.total_elec_kwh += zone.elec_kwh
        self.total_gas_therm += zone.gas_therm
        self.peak_demand_kw = max(self.peak_demand_kw, zone.peak_demand_kw)

        # Update end-use breakdown
        self.cooling_kwh += zone.cooling_kwh
        self.heating_kwh += zone.heating_kwh
        self.heating_therm += zone.heating_therm
        self.lighting_kwh += zone.lighting_kwh
        self.ventilation_kwh += zone.ventilation_kwh
        self.receptacle_kwh += zone.receptacle_kwh

        # Update area
        zone_area = zone.area_sqft * zone.multiplier
        self.total_area_sqft += zone_area
        if zone.zone_type != ZoneType.UNCONDITIONED:
            self.conditioned_area_sqft += zone_area

    def get_area_fraction(self, total_common_area: float) -> float:
        """Get fraction of total common area."""
        if total_common_area <= 0:
            return 0.0
        return self.total_area_sqft / total_common_area

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'category': self.category.value,
            'meter_name': self.meter_name,
            'zone_count': self.zone_count,
            'zone_names': self.zone_names,
            'total_elec_kwh': self.total_elec_kwh,
            'total_gas_therm': self.total_gas_therm,
            'peak_demand_kw': self.peak_demand_kw,
            'total_area_sqft': self.total_area_sqft,
            'eui_kbtu_sqft': self.eui_kbtu_sqft,
            'annual_cost': self.annual_cost,
            'cost_per_sqft': self.cost_per_sqft,
        }


# =============================================================================
# BUILDING SECTION
# =============================================================================

@dataclass
class BuildingSection:
    """
    A section of a mixed-use building with its own tariff and LCCA.

    Examples:
    - Residential section (dwelling units on floors 2-10)
    - Commercial section (retail on ground floor)
    - Common area section (corridors, lobby, fitness)
    """
    section_type: BuildingSectionType
    name: str

    # Zones in this section
    zones: List[ZoneEnergySummary] = field(default_factory=list)

    # Meter categories (for common areas)
    meter_categories: Dict[CommonAreaCategory, MeterCategoryAggregate] = field(
        default_factory=dict
    )

    # Tariff for this section
    tariff: Optional[TouTariff] = None
    tariff_name: str = ""

    # Aggregated energy
    total_elec_kwh: float = 0.0
    total_gas_therm: float = 0.0
    peak_demand_kw: float = 0.0
    total_area_sqft: float = 0.0

    # PV/Battery allocations
    pv_allocation_kwdc: float = 0.0
    pv_generation_kwh: float = 0.0
    battery_allocation_kwh: float = 0.0

    # LCCA results
    annual_elec_cost: float = 0.0
    annual_gas_cost: float = 0.0
    annual_demand_cost: float = 0.0
    total_annual_cost: float = 0.0

    @property
    def zone_count(self) -> int:
        """Number of zones in this section."""
        return len(self.zones)

    @property
    def dwelling_unit_count(self) -> int:
        """Number of dwelling units (if residential section)."""
        return sum(
            z.multiplier for z in self.zones
            if z.zone_type == ZoneType.DWELLING_UNIT
        )

    @property
    def eui_kbtu_sqft(self) -> float:
        """Combined EUI for this section."""
        if self.total_area_sqft <= 0:
            return 0.0
        elec_kbtu = self.total_elec_kwh * 3.412
        gas_kbtu = self.total_gas_therm * 100
        return (elec_kbtu + gas_kbtu) / self.total_area_sqft

    @property
    def cost_per_sqft(self) -> float:
        """Annual cost per square foot."""
        if self.total_area_sqft <= 0:
            return 0.0
        return self.total_annual_cost / self.total_area_sqft

    @property
    def cost_per_unit(self) -> float:
        """Annual cost per dwelling unit (residential only)."""
        if self.dwelling_unit_count <= 0:
            return 0.0
        return self.total_annual_cost / self.dwelling_unit_count

    @property
    def net_elec_kwh(self) -> float:
        """Net electricity after PV generation."""
        return max(0, self.total_elec_kwh - self.pv_generation_kwh)

    def add_zone(self, zone: ZoneEnergySummary) -> None:
        """Add a zone to this section and update aggregates."""
        self.zones.append(zone)
        self._update_totals(zone)

        # If common area, add to meter category
        if zone.zone_type == ZoneType.COMMON_AREA and zone.category:
            self._add_to_meter_category(zone)

    def _update_totals(self, zone: ZoneEnergySummary) -> None:
        """Update aggregate totals from zone."""
        multiplier = zone.multiplier
        self.total_elec_kwh += zone.elec_kwh * multiplier
        self.total_gas_therm += zone.gas_therm * multiplier
        self.peak_demand_kw += zone.peak_demand_kw * multiplier
        self.total_area_sqft += zone.area_sqft * multiplier

        # PV/Battery
        self.pv_allocation_kwdc += zone.pv_allocation_kwdc * multiplier
        self.pv_generation_kwh += zone.pv_generation_kwh * multiplier
        self.battery_allocation_kwh += zone.battery_allocation_kwh * multiplier

    def _add_to_meter_category(self, zone: ZoneEnergySummary) -> None:
        """Add zone to appropriate meter category aggregate."""
        category = zone.category
        if category not in self.meter_categories:
            self.meter_categories[category] = MeterCategoryAggregate(
                category=category,
                meter_name=f"MtrElec_{category.value.title()}"
            )
        self.meter_categories[category].add_zone(zone)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'section_type': self.section_type.value,
            'name': self.name,
            'zone_count': self.zone_count,
            'dwelling_unit_count': self.dwelling_unit_count,
            'total_elec_kwh': self.total_elec_kwh,
            'total_gas_therm': self.total_gas_therm,
            'peak_demand_kw': self.peak_demand_kw,
            'total_area_sqft': self.total_area_sqft,
            'eui_kbtu_sqft': self.eui_kbtu_sqft,
            'pv_allocation_kwdc': self.pv_allocation_kwdc,
            'pv_generation_kwh': self.pv_generation_kwh,
            'tariff_name': self.tariff_name,
            'annual_elec_cost': self.annual_elec_cost,
            'annual_gas_cost': self.annual_gas_cost,
            'total_annual_cost': self.total_annual_cost,
            'cost_per_sqft': self.cost_per_sqft,
            'meter_categories': {
                k.value: v.to_dict()
                for k, v in self.meter_categories.items()
            },
        }


# =============================================================================
# METER AGGREGATOR
# =============================================================================

class MeterAggregator:
    """
    Aggregate zone-level energy data into meter categories.

    Supports:
    - Common area meter categorization
    - Mixed-use building section separation
    - Master meter allocation and reconciliation
    - Multiple tariff application

    Example:
        >>> aggregator = MeterAggregator()
        >>> aggregator.add_zones(zone_summaries)
        >>> common_area_meters = aggregator.get_common_area_meters()
        >>> mixed_use_sections = aggregator.get_building_sections()
    """

    def __init__(
        self,
        residential_tariff: Optional[TouTariff] = None,
        commercial_tariff: Optional[TouTariff] = None,
        common_area_tariff: Optional[TouTariff] = None,
    ):
        """
        Initialize the meter aggregator.

        Args:
            residential_tariff: Tariff for dwelling units
            commercial_tariff: Tariff for commercial spaces
            common_area_tariff: Tariff for common areas (defaults to residential)
        """
        self.residential_tariff = residential_tariff
        self.commercial_tariff = commercial_tariff
        self.common_area_tariff = common_area_tariff or residential_tariff

        # Internal storage
        self._zones: List[ZoneEnergySummary] = []
        self._sections: Dict[BuildingSectionType, BuildingSection] = {}
        self._meter_categories: Dict[CommonAreaCategory, MeterCategoryAggregate] = {}

        # Building-level totals (for reconciliation)
        self._building_elec_kwh: float = 0.0
        self._building_gas_therm: float = 0.0

        # Initialize sections
        self._init_sections()

    def _init_sections(self) -> None:
        """Initialize building sections."""
        self._sections = {
            BuildingSectionType.RESIDENTIAL: BuildingSection(
                section_type=BuildingSectionType.RESIDENTIAL,
                name="Dwelling Units",
                tariff=self.residential_tariff,
                tariff_name="Residential TOU"
            ),
            BuildingSectionType.COMMON_AREA: BuildingSection(
                section_type=BuildingSectionType.COMMON_AREA,
                name="Common Areas",
                tariff=self.common_area_tariff,
                tariff_name="Common Area"
            ),
            BuildingSectionType.COMMERCIAL: BuildingSection(
                section_type=BuildingSectionType.COMMERCIAL,
                name="Commercial",
                tariff=self.commercial_tariff,
                tariff_name="Commercial TOU"
            ),
        }

    @property
    def zone_count(self) -> int:
        """Total number of zones."""
        return len(self._zones)

    @property
    def total_elec_kwh(self) -> float:
        """Total electricity consumption."""
        return sum(z.elec_kwh * z.multiplier for z in self._zones)

    @property
    def total_gas_therm(self) -> float:
        """Total gas consumption."""
        return sum(z.gas_therm * z.multiplier for z in self._zones)

    @property
    def total_area_sqft(self) -> float:
        """Total floor area."""
        return sum(z.area_sqft * z.multiplier for z in self._zones)

    @property
    def dwelling_unit_count(self) -> int:
        """Total dwelling units."""
        return self._sections[BuildingSectionType.RESIDENTIAL].dwelling_unit_count

    def add_zones(self, zones: List[ZoneEnergySummary]) -> None:
        """
        Add multiple zones and categorize them.

        Args:
            zones: List of zone energy summaries
        """
        for zone in zones:
            self.add_zone(zone)

    def add_zone(self, zone: ZoneEnergySummary) -> None:
        """
        Add a zone and categorize it by section and meter category.

        Args:
            zone: Zone energy summary to add
        """
        self._zones.append(zone)

        # Determine section type
        section_type = BuildingSectionType.from_zone_type(zone.zone_type)

        # Special handling for common areas
        if zone.zone_type == ZoneType.COMMON_AREA and zone.category:
            # Parking might have its own section
            if zone.category == CommonAreaCategory.PARKING:
                section_type = BuildingSectionType.PARKING
                if BuildingSectionType.PARKING not in self._sections:
                    self._sections[BuildingSectionType.PARKING] = BuildingSection(
                        section_type=BuildingSectionType.PARKING,
                        name="Parking",
                        tariff=self.common_area_tariff,
                        tariff_name="Common Area"
                    )
            # Fitness/amenity might have its own section
            elif zone.category == CommonAreaCategory.FITNESS:
                section_type = BuildingSectionType.AMENITY
                if BuildingSectionType.AMENITY not in self._sections:
                    self._sections[BuildingSectionType.AMENITY] = BuildingSection(
                        section_type=BuildingSectionType.AMENITY,
                        name="Amenity",
                        tariff=self.common_area_tariff,
                        tariff_name="Common Area"
                    )
            else:
                section_type = BuildingSectionType.COMMON_AREA

        # Add to section
        if section_type in self._sections:
            self._sections[section_type].add_zone(zone)

        # Add to global meter category tracking
        if zone.zone_type == ZoneType.COMMON_AREA and zone.category:
            if zone.category not in self._meter_categories:
                self._meter_categories[zone.category] = MeterCategoryAggregate(
                    category=zone.category,
                    meter_name=f"MtrElec_{zone.category.value.title()}"
                )
            self._meter_categories[zone.category].add_zone(zone)

    def set_building_totals(
        self,
        building_elec_kwh: float,
        building_gas_therm: float
    ) -> None:
        """
        Set building-level totals for master meter reconciliation.

        Args:
            building_elec_kwh: Total building electricity from master meter
            building_gas_therm: Total building gas from master meter
        """
        self._building_elec_kwh = building_elec_kwh
        self._building_gas_therm = building_gas_therm

    def get_meter_categories(self) -> Dict[CommonAreaCategory, MeterCategoryAggregate]:
        """Get all meter category aggregates."""
        return self._meter_categories.copy()

    def get_common_area_meters(self) -> List[MeterCategoryAggregate]:
        """
        Get list of common area meter categories.

        Returns meters sorted by total consumption.
        """
        meters = list(self._meter_categories.values())
        return sorted(meters, key=lambda m: m.total_elec_kwh, reverse=True)

    def get_building_sections(self) -> Dict[BuildingSectionType, BuildingSection]:
        """Get all building sections."""
        return {k: v for k, v in self._sections.items() if v.zone_count > 0}

    def get_section(self, section_type: BuildingSectionType) -> Optional[BuildingSection]:
        """Get a specific building section."""
        return self._sections.get(section_type)

    def aggregate_by_category(self) -> Dict[CommonAreaCategory, MeterCategoryAggregate]:
        """
        Aggregate all common area zones by meter category.

        Returns:
            Dictionary mapping category to aggregate
        """
        return self._meter_categories.copy()

    def allocate_master_meter(
        self,
        method: str = "by_area"
    ) -> Dict[BuildingSectionType, float]:
        """
        Allocate master meter consumption to building sections.

        Reconciles sum-of-zones to master meter reading.

        Args:
            method: Allocation method ("by_area", "by_modeled", "equal")

        Returns:
            Dictionary of section allocations as fractions
        """
        allocations = {}

        if method == "by_area":
            total_area = self.total_area_sqft
            for section_type, section in self._sections.items():
                if section.zone_count > 0 and total_area > 0:
                    allocations[section_type] = section.total_area_sqft / total_area
                else:
                    allocations[section_type] = 0.0

        elif method == "by_modeled":
            total_elec = self.total_elec_kwh
            for section_type, section in self._sections.items():
                if section.zone_count > 0 and total_elec > 0:
                    allocations[section_type] = section.total_elec_kwh / total_elec
                else:
                    allocations[section_type] = 0.0

        elif method == "equal":
            active_sections = [s for s in self._sections.values() if s.zone_count > 0]
            fraction = 1.0 / len(active_sections) if active_sections else 0.0
            for section_type, section in self._sections.items():
                allocations[section_type] = fraction if section.zone_count > 0 else 0.0

        return allocations

    def reconcile_to_master_meter(
        self,
        building_elec_kwh: Optional[float] = None,
        building_gas_therm: Optional[float] = None,
    ) -> Dict[str, float]:
        """
        Reconcile zone-level totals to master meter readings.

        Calculates the reconciliation factor and unaccounted energy.

        Args:
            building_elec_kwh: Master meter electricity reading
            building_gas_therm: Master meter gas reading

        Returns:
            Dictionary with reconciliation statistics
        """
        building_elec = building_elec_kwh or self._building_elec_kwh
        building_gas = building_gas_therm or self._building_gas_therm

        zone_elec = self.total_elec_kwh
        zone_gas = self.total_gas_therm

        results = {
            'master_meter_elec_kwh': building_elec,
            'master_meter_gas_therm': building_gas,
            'zone_total_elec_kwh': zone_elec,
            'zone_total_gas_therm': zone_gas,
        }

        # Calculate reconciliation factors
        if building_elec > 0 and zone_elec > 0:
            results['elec_reconciliation_factor'] = building_elec / zone_elec
            results['elec_unaccounted_kwh'] = building_elec - zone_elec
            results['elec_unaccounted_pct'] = (building_elec - zone_elec) / building_elec * 100
        else:
            results['elec_reconciliation_factor'] = 1.0
            results['elec_unaccounted_kwh'] = 0.0
            results['elec_unaccounted_pct'] = 0.0

        if building_gas > 0 and zone_gas > 0:
            results['gas_reconciliation_factor'] = building_gas / zone_gas
            results['gas_unaccounted_therm'] = building_gas - zone_gas
            results['gas_unaccounted_pct'] = (building_gas - zone_gas) / building_gas * 100
        else:
            results['gas_reconciliation_factor'] = 1.0
            results['gas_unaccounted_therm'] = 0.0
            results['gas_unaccounted_pct'] = 0.0

        return results

    def calculate_section_costs(
        self,
        elec_rate: float = 0.25,
        gas_rate: float = 1.50,
        demand_rate: float = 15.0,
    ) -> None:
        """
        Calculate costs for each building section.

        Uses flat rates if TOU tariffs not available.

        Args:
            elec_rate: Default electricity rate ($/kWh)
            gas_rate: Default gas rate ($/therm)
            demand_rate: Default demand charge ($/kW)
        """
        for section in self._sections.values():
            if section.zone_count == 0:
                continue

            # Use TOU if available, otherwise flat rates
            if section.tariff:
                # TOU calculation would go here
                # For now, use simplified calculation
                pass

            section.annual_elec_cost = section.total_elec_kwh * elec_rate
            section.annual_gas_cost = section.total_gas_therm * gas_rate
            section.annual_demand_cost = section.peak_demand_kw * demand_rate * 12  # Monthly
            section.total_annual_cost = (
                section.annual_elec_cost +
                section.annual_gas_cost +
                section.annual_demand_cost
            )

            # Also update meter category costs
            for meter in section.meter_categories.values():
                meter.annual_cost = meter.total_elec_kwh * elec_rate
                if meter.total_area_sqft > 0:
                    meter.cost_per_sqft = meter.annual_cost / meter.total_area_sqft

    def summary(self) -> Dict[str, Any]:
        """
        Generate summary of all aggregations.

        Returns:
            Dictionary with complete aggregation summary
        """
        sections = self.get_building_sections()

        return {
            'zone_count': self.zone_count,
            'total_elec_kwh': self.total_elec_kwh,
            'total_gas_therm': self.total_gas_therm,
            'total_area_sqft': self.total_area_sqft,
            'dwelling_unit_count': self.dwelling_unit_count,
            'sections': {
                k.value: v.to_dict() for k, v in sections.items()
            },
            'meter_categories': {
                k.value: v.to_dict() for k, v in self._meter_categories.items()
            },
        }


# =============================================================================
# MIXED-USE LCCA RESULTS
# =============================================================================

@dataclass
class MixedUseLccaResults:
    """
    LCCA results for a mixed-use building.

    Contains separate results for each building section plus combined totals.
    """
    building_name: str

    # Section results
    residential_result: Optional[BuildingSection] = None
    commercial_result: Optional[BuildingSection] = None
    common_area_result: Optional[BuildingSection] = None
    parking_result: Optional[BuildingSection] = None

    # Combined totals
    total_annual_cost: float = 0.0
    total_elec_kwh: float = 0.0
    total_gas_therm: float = 0.0
    total_area_sqft: float = 0.0

    # PV/Battery totals
    total_pv_kwdc: float = 0.0
    total_pv_generation_kwh: float = 0.0
    total_battery_kwh: float = 0.0

    # Cost allocations
    residential_share_pct: float = 0.0
    commercial_share_pct: float = 0.0
    common_area_share_pct: float = 0.0

    @property
    def eui_kbtu_sqft(self) -> float:
        """Combined building EUI."""
        if self.total_area_sqft <= 0:
            return 0.0
        elec_kbtu = self.total_elec_kwh * 3.412
        gas_kbtu = self.total_gas_therm * 100
        return (elec_kbtu + gas_kbtu) / self.total_area_sqft

    @property
    def cost_per_sqft(self) -> float:
        """Annual cost per square foot."""
        if self.total_area_sqft <= 0:
            return 0.0
        return self.total_annual_cost / self.total_area_sqft

    def calculate_shares(self) -> None:
        """Calculate cost shares by section."""
        if self.total_annual_cost <= 0:
            return

        if self.residential_result:
            self.residential_share_pct = (
                self.residential_result.total_annual_cost / self.total_annual_cost * 100
            )
        if self.commercial_result:
            self.commercial_share_pct = (
                self.commercial_result.total_annual_cost / self.total_annual_cost * 100
            )
        if self.common_area_result:
            self.common_area_share_pct = (
                self.common_area_result.total_annual_cost / self.total_annual_cost * 100
            )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        result = {
            'building_name': self.building_name,
            'total_annual_cost': self.total_annual_cost,
            'total_elec_kwh': self.total_elec_kwh,
            'total_gas_therm': self.total_gas_therm,
            'total_area_sqft': self.total_area_sqft,
            'eui_kbtu_sqft': self.eui_kbtu_sqft,
            'cost_per_sqft': self.cost_per_sqft,
            'total_pv_kwdc': self.total_pv_kwdc,
            'residential_share_pct': self.residential_share_pct,
            'commercial_share_pct': self.commercial_share_pct,
            'common_area_share_pct': self.common_area_share_pct,
        }

        if self.residential_result:
            result['residential'] = self.residential_result.to_dict()
        if self.commercial_result:
            result['commercial'] = self.commercial_result.to_dict()
        if self.common_area_result:
            result['common_area'] = self.common_area_result.to_dict()
        if self.parking_result:
            result['parking'] = self.parking_result.to_dict()

        return result


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def aggregate_zones_by_meter_category(
    zones: List[ZoneEnergySummary],
) -> Dict[CommonAreaCategory, MeterCategoryAggregate]:
    """
    Aggregate zones by meter category.

    Simple convenience function for common area aggregation.

    Args:
        zones: List of zone energy summaries

    Returns:
        Dictionary mapping category to aggregate
    """
    aggregator = MeterAggregator()
    aggregator.add_zones(zones)
    return aggregator.aggregate_by_category()


def create_mixed_use_lcca(
    zones: List[ZoneEnergySummary],
    residential_tariff: Optional[TouTariff] = None,
    commercial_tariff: Optional[TouTariff] = None,
    common_area_tariff: Optional[TouTariff] = None,
    building_name: str = "Mixed-Use Building",
    elec_rate: float = 0.25,
    gas_rate: float = 1.50,
) -> MixedUseLccaResults:
    """
    Create mixed-use building LCCA results.

    Separates zones into building sections and calculates costs.

    Args:
        zones: List of zone energy summaries
        residential_tariff: Tariff for dwelling units
        commercial_tariff: Tariff for commercial spaces
        common_area_tariff: Tariff for common areas
        building_name: Name for the building
        elec_rate: Default electricity rate if no tariff
        gas_rate: Default gas rate if no tariff

    Returns:
        MixedUseLccaResults with section breakdowns
    """
    # Create aggregator and add zones
    aggregator = MeterAggregator(
        residential_tariff=residential_tariff,
        commercial_tariff=commercial_tariff,
        common_area_tariff=common_area_tariff,
    )
    aggregator.add_zones(zones)

    # Calculate costs
    aggregator.calculate_section_costs(
        elec_rate=elec_rate,
        gas_rate=gas_rate,
    )

    # Get sections
    sections = aggregator.get_building_sections()

    # Build results
    results = MixedUseLccaResults(building_name=building_name)

    results.residential_result = sections.get(BuildingSectionType.RESIDENTIAL)
    results.commercial_result = sections.get(BuildingSectionType.COMMERCIAL)
    results.common_area_result = sections.get(BuildingSectionType.COMMON_AREA)
    results.parking_result = sections.get(BuildingSectionType.PARKING)

    # Calculate totals
    results.total_elec_kwh = aggregator.total_elec_kwh
    results.total_gas_therm = aggregator.total_gas_therm
    results.total_area_sqft = aggregator.total_area_sqft

    for section in sections.values():
        results.total_annual_cost += section.total_annual_cost
        results.total_pv_kwdc += section.pv_allocation_kwdc
        results.total_pv_generation_kwh += section.pv_generation_kwh
        results.total_battery_kwh += section.battery_allocation_kwh

    # Calculate shares
    results.calculate_shares()

    return results


def format_meter_aggregation_table(
    meters: Dict[CommonAreaCategory, MeterCategoryAggregate]
) -> str:
    """
    Format meter aggregation data as text table.

    Args:
        meters: Dictionary of meter category aggregates

    Returns:
        Formatted text table
    """
    lines = [
        "=" * 90,
        "COMMON AREA METER AGGREGATION",
        "=" * 90,
        "",
        f"{'Category':<15} {'Zones':>6} {'Area (sqft)':>12} "
        f"{'Elec (kWh)':>12} {'Gas (therm)':>12} {'EUI':>8}",
        "-" * 90,
    ]

    total_area = 0
    total_elec = 0
    total_gas = 0

    for category, meter in sorted(meters.items(), key=lambda x: x[1].total_elec_kwh, reverse=True):
        lines.append(
            f"{category.value.title():<15} {meter.zone_count:>6} "
            f"{meter.total_area_sqft:>12,.0f} "
            f"{meter.total_elec_kwh:>12,.0f} "
            f"{meter.total_gas_therm:>12,.1f} "
            f"{meter.eui_kbtu_sqft:>8.1f}"
        )
        total_area += meter.total_area_sqft
        total_elec += meter.total_elec_kwh
        total_gas += meter.total_gas_therm

    lines.extend([
        "-" * 90,
        f"{'TOTAL':<15} {'':<6} "
        f"{total_area:>12,.0f} "
        f"{total_elec:>12,.0f} "
        f"{total_gas:>12,.1f} "
        f"{'':>8}",
        "=" * 90,
    ])

    return "\n".join(lines)


def format_building_sections_table(
    sections: Dict[BuildingSectionType, BuildingSection]
) -> str:
    """
    Format building sections data as text table.

    Args:
        sections: Dictionary of building sections

    Returns:
        Formatted text table
    """
    lines = [
        "=" * 100,
        "BUILDING SECTIONS SUMMARY",
        "=" * 100,
        "",
        f"{'Section':<20} {'Zones':>6} {'Units':>6} {'Area (sqft)':>12} "
        f"{'Elec (kWh)':>12} {'Gas (therm)':>12} {'Annual Cost':>12}",
        "-" * 100,
    ]

    total_zones = 0
    total_units = 0
    total_area = 0
    total_elec = 0
    total_gas = 0
    total_cost = 0

    for section_type, section in sorted(
        sections.items(),
        key=lambda x: x[1].total_annual_cost,
        reverse=True
    ):
        lines.append(
            f"{section.name:<20} {section.zone_count:>6} "
            f"{section.dwelling_unit_count:>6} "
            f"{section.total_area_sqft:>12,.0f} "
            f"{section.total_elec_kwh:>12,.0f} "
            f"{section.total_gas_therm:>12,.1f} "
            f"${section.total_annual_cost:>11,.0f}"
        )
        total_zones += section.zone_count
        total_units += section.dwelling_unit_count
        total_area += section.total_area_sqft
        total_elec += section.total_elec_kwh
        total_gas += section.total_gas_therm
        total_cost += section.total_annual_cost

    lines.extend([
        "-" * 100,
        f"{'TOTAL':<20} {total_zones:>6} "
        f"{total_units:>6} "
        f"{total_area:>12,.0f} "
        f"{total_elec:>12,.0f} "
        f"{total_gas:>12,.1f} "
        f"${total_cost:>11,.0f}",
        "=" * 100,
    ])

    return "\n".join(lines)
