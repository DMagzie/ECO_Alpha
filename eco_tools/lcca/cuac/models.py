"""
CUAC Data Models
================

Data classes for representing CUAC (California Utility Allowance Calculator)
configuration and output data from CBECC.

These models support:
- CUAC configuration (utility, tariff, PV/battery settings)
- Dwelling unit type definitions (bedrooms, area, HVAC)
- Per-unit PV and battery allocations
- Utility rate structures with TOU periods
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from enum import Enum


class FuelType(Enum):
    """Fuel type enumeration for appliances."""
    ELECTRICITY = "Electricity"
    GAS = "Gas"
    NONE = "- none -"


class ZoneType(Enum):
    """
    Zone type classification for multifamily and mixed-use buildings.

    Used to distinguish between:
    - DWELLING_UNIT: Individual tenant units (ResZn in CBECC)
    - COMMON_AREA: Shared spaces like corridors, lobbies (ResOtherZn in CBECC)
    - NONRESIDENTIAL: Commercial spaces in mixed-use buildings (retail, office)
    - UNCONDITIONED: Attics, garages, etc.
    """
    DWELLING_UNIT = "dwelling_unit"
    COMMON_AREA = "common_area"
    NONRESIDENTIAL = "nonresidential"  # Mixed-use building support (Phase 4)
    UNCONDITIONED = "unconditioned"


# Space functions that indicate dwelling units
DWELLING_UNIT_SPACE_FUNCTIONS = {
    "High-Rise Residential Living Spaces",
    "Low-Rise Residential Living Spaces",
    "Residential Living Spaces",
    "Hotel/Motel Guest Room",  # Some projects use this
}

# Space functions that indicate common areas
COMMON_AREA_SPACE_FUNCTIONS = {
    "Corridor Area",
    "Corridor/Transition",
    "Lobby - Hotel",
    "Lobby - Main Entry",
    "Lobby - Elevator",
    "Lobby Area",
    "Stairway Area",
    "Stairwell",
    "Conference, Multipurpose and Meeting Area",
    "Exercise/Fitness Center and Gymnasium Areas",
    "Laundry, within a Dwelling Unit or Common Laundry",
    "Laundry - Apartment",
    "Storage, General",
    "Electrical/Mechanical Room",
    "Restroom",
    "Restroom Area",
    "Office - Open Plan",
    "Office Area",
    "Kitchen/Food Preparation",
}


def classify_zone_type(
    space_function: str,
    conditioning_type: str = "Conditioned"
) -> ZoneType:
    """
    Classify a zone as dwelling unit, common area, or unconditioned.

    Args:
        space_function: The SpcFunc from CBECC
        conditioning_type: "Conditioned", "Unconditioned", etc.

    Returns:
        ZoneType classification
    """
    if conditioning_type.lower() == "unconditioned":
        return ZoneType.UNCONDITIONED

    # Normalize for comparison
    normalized = space_function.strip()

    # Check dwelling unit functions first
    for duf in DWELLING_UNIT_SPACE_FUNCTIONS:
        if duf.lower() in normalized.lower() or normalized.lower() in duf.lower():
            return ZoneType.DWELLING_UNIT

    # Check common area functions
    for caf in COMMON_AREA_SPACE_FUNCTIONS:
        if caf.lower() in normalized.lower() or normalized.lower() in caf.lower():
            return ZoneType.COMMON_AREA

    # Default heuristics based on keywords
    lower_func = normalized.lower()
    dwelling_keywords = ["residential", "living", "dwelling", "apartment", "unit"]
    common_keywords = ["corridor", "lobby", "stair", "laundry", "fitness",
                       "office", "storage", "mechanical", "electrical", "restroom"]

    for kw in dwelling_keywords:
        if kw in lower_func:
            return ZoneType.DWELLING_UNIT

    for kw in common_keywords:
        if kw in lower_func:
            return ZoneType.COMMON_AREA

    # Unknown - assume common area (safer for billing)
    return ZoneType.COMMON_AREA


def extract_bedroom_count(zone_name: str) -> Optional[int]:
    """
    Extract bedroom count from zone name pattern.

    Common patterns:
    - "S-1-2-BD-699 1-R-2" -> 2 bedrooms (from "2-BD")
    - "F1 Res Zn N 1-bed" -> 1 bedroom (from "1-bed")
    - "Unit 101 2BR" -> 2 bedrooms (from "2BR")

    Args:
        zone_name: Zone name string

    Returns:
        Bedroom count or None if not detected
    """
    import re

    # Pattern: N-BD (e.g., "2-BD", "3-BD")
    match = re.search(r'(\d+)-BD', zone_name, re.IGNORECASE)
    if match:
        return int(match.group(1))

    # Pattern: N-bed (e.g., "1-bed", "2-bed")
    match = re.search(r'(\d+)-bed', zone_name, re.IGNORECASE)
    if match:
        return int(match.group(1))

    # Pattern: NBR (e.g., "2BR", "3BR")
    match = re.search(r'(\d+)BR', zone_name, re.IGNORECASE)
    if match:
        return int(match.group(1))

    # Pattern: N Bedroom (e.g., "2 Bedroom")
    match = re.search(r'(\d+)\s*[Bb]edroom', zone_name)
    if match:
        return int(match.group(1))

    return None


class PVBillingOption(Enum):
    """PV billing option for affordable housing."""
    OFFSETS_MONTHLY = "PV Offsets Monthly Use"
    NET_METERING = "Net Energy Metering"
    VNEM = "Virtual Net Energy Metering"


@dataclass
class Tier:
    """Rate tier for tiered pricing."""
    tier_number: int
    price: float  # $/kWh or $/therm
    quantity: Optional[float] = None  # kWh or therms threshold (None = unlimited)


@dataclass
class EnergyCostComponent:
    """Energy cost component within a TOU period."""
    name: str
    cost_component_period_type: str  # "PerBillingCycle", "PerDayBilled"
    delivery: bool  # True = distribution charge
    non_bypassable: bool
    total_consumption: bool
    tiers: List[Tier] = field(default_factory=list)


@dataclass
class TouPeriod:
    """Time-of-Use period definition."""
    name: str  # e.g., "Seasonal", "On-Peak", "Off-Peak"
    start_time: float  # Hour (0-24)
    end_time: float  # Hour (0-24)
    applicable_days: str  # "all", "weekdays", "weekends"
    energy_cost_components: List[EnergyCostComponent] = field(default_factory=list)
    demand_cost_components: List[Any] = field(default_factory=list)


@dataclass
class RateSeason:
    """Utility rate season definition."""
    season_name: str  # e.g., "Winter", "Summer"
    start_month: int
    end_month: int
    tou_periods: List[TouPeriod] = field(default_factory=list)
    fixed_cost_components: List[Any] = field(default_factory=list)
    minimum_bill_amount: Optional[float] = None  # $/day


@dataclass
class UtilityRate:
    """
    Utility rate structure parsed from er.json.

    This represents a complete utility tariff with TOU periods,
    tiered pricing, and demand charges.
    """
    rate_type: str  # "Electric" or "Gas"
    utility: str  # e.g., "Pacific Gas and Electric Company (PG&E)"
    rate_territory: str  # e.g., "CA_PGE_T"
    rate_name: str  # e.g., "Rate E1 Area T Code H"
    public_id: str
    encoded_rate_name: str  # e.g., "CA_PGE_E1_T_H"
    description: str
    metering_type: str  # "Standard", "TOU"
    seasons: List[RateSeason] = field(default_factory=list)

    def get_season(self, month: int) -> Optional[RateSeason]:
        """Get the rate season for a given month (1-12)."""
        for season in self.seasons:
            start = season.start_month
            end = season.end_month
            # Handle wrap-around (e.g., Winter: Nov-Apr)
            if start <= end:
                if start <= month <= end:
                    return season
            else:  # Wrap-around case
                if month >= start or month <= end:
                    return season
        return None


@dataclass
class DwellUnitType:
    """
    Dwelling unit type definition.

    Represents a prototype unit type (e.g., "1BR-500sf") that can be
    instantiated multiple times in the building.
    """
    name: str
    num_bedrooms: int
    cond_floor_area: float  # ft²
    dryer_fuel: Optional[str] = None  # "Electricity", "Gas", "- none -"
    cook_fuel: Optional[str] = None  # "Electricity", "Gas"
    hvac_sys_type: Optional[str] = None
    hvac_heat_pump_ref: Optional[str] = None
    dhw_sys_ref: Optional[str] = None
    iaq_option: Optional[str] = None


@dataclass
class DwellUnitAllocation:
    """
    Per-zone PV and battery allocation.

    Used for VNEM/V-NBT calculations where PV and battery capacity
    is allocated to zones. Zones can be either dwelling units (ResZn)
    or common areas (ResOtherZn).
    """
    zone_name: str
    conditioning_type: str  # "Conditioned", "Unconditioned"
    space_function: str  # e.g., "High-Rise Residential Living Spaces"
    pv_batt_bldg_type: str  # e.g., "Highrise Multifamily"
    floor_area_sqft: float
    multiplier: int = 1
    num_res_dwellings: int = 1

    # Prescriptive requirements
    prescriptive_pv_kwdc: float = 0.0
    prescriptive_batt_kwh: float = 0.0
    prescriptive_batt_kw: float = 0.0

    @property
    def zone_type(self) -> ZoneType:
        """Classify this zone as dwelling unit, common area, or unconditioned."""
        return classify_zone_type(self.space_function, self.conditioning_type)

    @property
    def is_dwelling_unit(self) -> bool:
        """True if this zone is a dwelling unit (ResZn)."""
        return self.zone_type == ZoneType.DWELLING_UNIT

    @property
    def is_common_area(self) -> bool:
        """True if this zone is a common area (ResOtherZn)."""
        return self.zone_type == ZoneType.COMMON_AREA

    @property
    def bedroom_count(self) -> Optional[int]:
        """Extract bedroom count from zone name, if available."""
        return extract_bedroom_count(self.zone_name)


@dataclass
class CuacConfig:
    """
    CUAC configuration from AnalysisResults.xml.

    Contains the CUAC-specific settings for utility allowance calculations
    including utility selection, tariff, and PV/battery allocations.
    """
    name: str = "CalUtilityAllowanceCalc"
    report_option: str = "Draft"  # "Draft" or "Final"
    project_id: Optional[str] = None
    locality: Optional[str] = None
    unit_type: str = "Affordable Housing"

    # Electric utility settings
    elec_utility: Optional[str] = None
    elec_territory: Optional[str] = None
    elec_tariff: Optional[str] = None
    elec_tariff_adj: Optional[str] = None

    # Gas utility settings
    gas_utility: Optional[str] = None
    gas_tariff: Optional[str] = None

    # Water/trash settings (not paid by tenant typically)
    water_rate_type: str = "Not Paid by Tenant"
    water_monthly_cost: float = 0.0
    water_volume_cost: float = 0.0
    trash_rate_type: str = "Not Paid by Tenant"
    trash_monthly_cost: float = 0.0

    # PV settings for affordable housing
    affordable_pv_dc_sys_size: Optional[float] = None  # kWdc
    pct_indiv_unit_pv_by_bedrms: Dict[int, float] = field(default_factory=dict)
    pv_billing_option: str = "PV Offsets Monthly Use"

    # Battery settings for affordable housing
    affordable_batt_max_cap: Optional[float] = None  # kWh
    pct_indiv_unit_batt_by_bedrms: Dict[int, float] = field(default_factory=dict)

    def get_pv_pct_for_bedrooms(self, num_bedrooms: int) -> float:
        """Get PV allocation percentage for a given bedroom count."""
        return self.pct_indiv_unit_pv_by_bedrms.get(num_bedrooms, 0.0)

    def get_batt_pct_for_bedrooms(self, num_bedrooms: int) -> float:
        """Get battery allocation percentage for a given bedroom count."""
        return self.pct_indiv_unit_batt_by_bedrms.get(num_bedrooms, 0.0)

    def allocate_pv_to_unit(self, num_bedrooms: int) -> float:
        """
        Calculate PV capacity (kWdc) allocated to a unit.

        Args:
            num_bedrooms: Number of bedrooms in the unit

        Returns:
            PV capacity in kWdc allocated to this unit
        """
        if self.affordable_pv_dc_sys_size is None:
            return 0.0
        pct = self.get_pv_pct_for_bedrooms(num_bedrooms)
        return self.affordable_pv_dc_sys_size * (pct / 100.0)

    def allocate_battery_to_unit(self, num_bedrooms: int) -> float:
        """
        Calculate battery capacity (kWh) allocated to a unit.

        Args:
            num_bedrooms: Number of bedrooms in the unit

        Returns:
            Battery capacity in kWh allocated to this unit
        """
        if self.affordable_batt_max_cap is None:
            return 0.0
        pct = self.get_batt_pct_for_bedrooms(num_bedrooms)
        return self.affordable_batt_max_cap * (pct / 100.0)
