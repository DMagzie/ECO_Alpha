"""
ResOther Zone Data Models
=========================

Data classes for representing residential common area zones and their
energy metering allocations.
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict
from enum import Enum


class CommonAreaCategory(Enum):
    """
    Common area meter categories for granular energy tracking.

    These categories group similar space functions to enable
    meaningful energy analysis and cost allocation.
    """
    LOBBY = "lobby"
    CORRIDOR = "corridor"
    MECHANICAL = "mechanical"
    PARKING = "parking"
    FITNESS = "fitness"
    OFFICE = "office"
    STORAGE = "storage"
    STAIRWELL = "stairwell"
    RESTROOM = "restroom"
    CONFERENCE = "conference"
    LAUNDRY = "laundry"
    ELEVATOR = "elevator"
    UNCONDITIONED = "unconditioned"
    OTHER = "other"


# Mapping from CBECC SpcFunc values to meter categories
SPACE_FUNCTION_MAPPING: Dict[str, CommonAreaCategory] = {
    # Lobby
    "Lobby, Main Entry": CommonAreaCategory.LOBBY,
    "Lobby - Main Entry": CommonAreaCategory.LOBBY,
    "Lobby - Hotel": CommonAreaCategory.LOBBY,
    "Lobby - Elevator": CommonAreaCategory.LOBBY,
    "Lobby Area": CommonAreaCategory.LOBBY,

    # Corridor
    "Corridor Area": CommonAreaCategory.CORRIDOR,
    "Corridor/Transition": CommonAreaCategory.CORRIDOR,
    "Residential - Common corridors": CommonAreaCategory.CORRIDOR,

    # Mechanical/Electrical
    "Electrical, Mechanical, Telephone Rooms": CommonAreaCategory.MECHANICAL,
    "Electrical/Mechanical Room": CommonAreaCategory.MECHANICAL,

    # Parking
    "Parking Garage Area (Parking Zone and Ramps)": CommonAreaCategory.PARKING,
    "Exhaust - Parking garages": CommonAreaCategory.PARKING,
    "Parking Garage Area": CommonAreaCategory.PARKING,

    # Fitness
    "Exercise/Fitness Center and Gymnasium Areas": CommonAreaCategory.FITNESS,
    "Sports/Entertainment - Gym, sports arena (play area)": CommonAreaCategory.FITNESS,

    # Office
    "Office - Office space": CommonAreaCategory.OFFICE,
    "Office Area (>250 square feet)": CommonAreaCategory.OFFICE,
    "Office Area": CommonAreaCategory.OFFICE,
    "Office - Open Plan": CommonAreaCategory.OFFICE,

    # Storage
    "Storage": CommonAreaCategory.STORAGE,
    "Storage, General": CommonAreaCategory.STORAGE,

    # Stairwell
    "Stairwell": CommonAreaCategory.STAIRWELL,
    "Stairway Area": CommonAreaCategory.STAIRWELL,

    # Restroom
    "Restrooms": CommonAreaCategory.RESTROOM,
    "Restroom": CommonAreaCategory.RESTROOM,
    "Restroom Area": CommonAreaCategory.RESTROOM,
    "Exhaust - Toilets, public": CommonAreaCategory.RESTROOM,

    # Conference
    "Conference, Multipurpose and Meeting Area": CommonAreaCategory.CONFERENCE,

    # Laundry
    "Laundry, within a Dwelling Unit or Common Laundry": CommonAreaCategory.LAUNDRY,
    "Laundry - Apartment": CommonAreaCategory.LAUNDRY,

    # Elevator (shafts, not lobbies)
    "Unoccupied-Include in Gross Floor Area": CommonAreaCategory.ELEVATOR,

    # Unconditioned/Unoccupied
    "General - Unoccupied": CommonAreaCategory.UNCONDITIONED,
    "Misc - All others": CommonAreaCategory.UNCONDITIONED,
    "All other": CommonAreaCategory.OTHER,
    "NA": CommonAreaCategory.OTHER,
}


def classify_space_function(space_function: str) -> CommonAreaCategory:
    """
    Classify a CBECC space function into a meter category.

    Args:
        space_function: The SpcFunc value from CBECC

    Returns:
        CommonAreaCategory for this space function
    """
    # Direct mapping
    if space_function in SPACE_FUNCTION_MAPPING:
        return SPACE_FUNCTION_MAPPING[space_function]

    # Fuzzy matching for variations
    lower = space_function.lower()

    if "lobby" in lower:
        return CommonAreaCategory.LOBBY
    if "corridor" in lower:
        return CommonAreaCategory.CORRIDOR
    if "mechanical" in lower or "electrical" in lower or "telecom" in lower:
        return CommonAreaCategory.MECHANICAL
    if "parking" in lower or "garage" in lower:
        return CommonAreaCategory.PARKING
    if "fitness" in lower or "gym" in lower or "exercise" in lower:
        return CommonAreaCategory.FITNESS
    if "office" in lower:
        return CommonAreaCategory.OFFICE
    if "storage" in lower or "bike" in lower:
        return CommonAreaCategory.STORAGE
    if "stair" in lower:
        return CommonAreaCategory.STAIRWELL
    if "restroom" in lower or "toilet" in lower or "bathroom" in lower:
        return CommonAreaCategory.RESTROOM
    if "conference" in lower or "meeting" in lower or "multipurpose" in lower:
        return CommonAreaCategory.CONFERENCE
    if "laundry" in lower:
        return CommonAreaCategory.LAUNDRY
    if "elevator" in lower and "lobby" not in lower:
        return CommonAreaCategory.ELEVATOR
    if "unoccupied" in lower or "unconditioned" in lower:
        return CommonAreaCategory.UNCONDITIONED

    return CommonAreaCategory.OTHER


class ConditioningType(Enum):
    """Zone conditioning type."""
    CONDITIONED = "Conditioned"
    UNCONDITIONED = "Unconditioned"
    SEMIHEATED = "Semiheated"


@dataclass
class ResOtherZone:
    """
    Residential Other Zone (common area) definition.

    Represents a single common area zone from a CBECC model with
    all relevant properties for energy metering.
    """
    name: str
    space_function: str
    conditioning_type: str
    area_sqft: float
    floor_level: Optional[str] = None
    ceiling_height: float = 10.0
    hvac_system_ref: Optional[str] = None
    dhw_system_ref: Optional[str] = None
    iaq_option: Optional[str] = None
    multiplier: int = 1

    @property
    def category(self) -> CommonAreaCategory:
        """Get the meter category for this zone."""
        return classify_space_function(self.space_function)

    @property
    def is_conditioned(self) -> bool:
        """True if zone is conditioned."""
        return self.conditioning_type.lower() == "conditioned"

    @property
    def meter_name(self) -> str:
        """
        Generate a meter name for this zone's category.

        Format: MtrElec_{category} (e.g., MtrElec_Lobby)
        """
        return f"MtrElec_{self.category.value.title()}"

    @property
    def total_area(self) -> float:
        """Total area including multiplier."""
        return self.area_sqft * self.multiplier


@dataclass
class CommonAreaMeterAllocation:
    """
    Aggregated meter allocation for a common area category.

    Represents the total area and zones assigned to a specific
    meter category for energy calculation.
    """
    category: CommonAreaCategory
    meter_name: str
    zones: List[ResOtherZone] = field(default_factory=list)

    @property
    def total_area_sqft(self) -> float:
        """Total area for all zones in this category."""
        return sum(z.total_area for z in self.zones)

    @property
    def conditioned_area_sqft(self) -> float:
        """Total conditioned area for this category."""
        return sum(z.total_area for z in self.zones if z.is_conditioned)

    @property
    def zone_count(self) -> int:
        """Number of zones in this category."""
        return len(self.zones)

    @property
    def zone_names(self) -> List[str]:
        """List of zone names in this category."""
        return [z.name for z in self.zones]

    def add_zone(self, zone: ResOtherZone):
        """Add a zone to this allocation."""
        self.zones.append(zone)

    def get_area_fraction(self, total_common_area: float) -> float:
        """
        Get this category's fraction of total common area.

        Args:
            total_common_area: Total common area in building (sqft)

        Returns:
            Fraction (0.0 to 1.0) of total common area
        """
        if total_common_area <= 0:
            return 0.0
        return self.total_area_sqft / total_common_area
