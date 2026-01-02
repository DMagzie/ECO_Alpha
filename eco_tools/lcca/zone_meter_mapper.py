"""
Zone-Meter Mapping Engine
=========================

Maps zones to meter categories and generates hierarchical meter names
for CSE input transformation.

This module:
- Classifies CSE zones into building sections (Residential, Common Area, etc.)
- Assigns CommonAreaCategory to common area zones
- Generates hierarchical meter naming (building -> section -> category -> zone)
- Builds submeter relationships for aggregation
- Extracts dwelling unit bedroom counts from zone names

Meter Hierarchy:
    MtrElec (Building Total)
    ├── MtrElec_Residential (All Dwelling Units)
    │   ├── MtrElec_DU_0BR (Studio units)
    │   ├── MtrElec_DU_1BR (1-bedroom units)
    │   └── ...
    ├── MtrElec_CommonArea (All Common Areas)
    │   ├── MtrElec_CA_LOBBY
    │   ├── MtrElec_CA_CORRIDOR
    │   └── ...
    └── MtrElec_NonResidential (Commercial/Retail)
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple
from enum import Enum
import re
import logging

from .cuac.models import ZoneType, classify_zone_type
from .res_other.models import CommonAreaCategory, classify_space_function
from .meter_aggregation import BuildingSectionType
from .parsers.cse_zone_input import CSEZone, CSEZoneInputModel

logger = logging.getLogger(__name__)


# =============================================================================
# CONSTANTS
# =============================================================================

# Meter naming prefixes
METER_PREFIX_ELECTRIC = "MtrElec"
METER_PREFIX_GAS = "MtrGas"

# Section meter names
SECTION_METER_NAMES = {
    BuildingSectionType.RESIDENTIAL: "Residential",
    BuildingSectionType.COMMON_AREA: "CommonArea",
    BuildingSectionType.COMMERCIAL: "NonResidential",
    BuildingSectionType.PARKING: "Parking",
    BuildingSectionType.AMENITY: "Amenity",
}

# Category meter prefixes
CATEGORY_METER_PREFIXES = {
    CommonAreaCategory.LOBBY: "CA_LOBBY",
    CommonAreaCategory.CORRIDOR: "CA_CORRIDOR",
    CommonAreaCategory.MECHANICAL: "CA_MECHANICAL",
    CommonAreaCategory.PARKING: "CA_PARKING",
    CommonAreaCategory.FITNESS: "CA_FITNESS",
    CommonAreaCategory.OFFICE: "CA_OFFICE",
    CommonAreaCategory.STORAGE: "CA_STORAGE",
    CommonAreaCategory.STAIRWELL: "CA_STAIRWELL",
    CommonAreaCategory.RESTROOM: "CA_RESTROOM",
    CommonAreaCategory.CONFERENCE: "CA_CONFERENCE",
    CommonAreaCategory.LAUNDRY: "CA_LAUNDRY",
    CommonAreaCategory.ELEVATOR: "CA_ELEVATOR",
    CommonAreaCategory.UNCONDITIONED: "CA_UNCOND",
    CommonAreaCategory.OTHER: "CA_OTHER",
}


# =============================================================================
# ZONE CLASSIFICATION
# =============================================================================

class ZoneClassification(Enum):
    """Detailed zone classification for meter assignment."""
    DWELLING_UNIT = "dwelling_unit"
    COMMON_AREA = "common_area"
    NONRESIDENTIAL = "nonresidential"
    UNCONDITIONED = "unconditioned"


# Patterns for extracting bedroom counts from zone names
BEDROOM_PATTERNS = [
    # "_1BR", "_2BR", etc.
    re.compile(r'_(\d+)BR', re.IGNORECASE),
    # "1bedrm", "2bedrm"
    re.compile(r'(\d+)bedrm', re.IGNORECASE),
    # "1-bedroom", "2-bedroom"
    re.compile(r'(\d+)[_-]?bedroom', re.IGNORECASE),
    # "0BR" for studios
    re.compile(r'0BR', re.IGNORECASE),
    # "Studio"
    re.compile(r'studio', re.IGNORECASE),
]

# Patterns for classifying zone types from zone names
ZONE_NAME_PATTERNS = {
    ZoneClassification.DWELLING_UNIT: [
        re.compile(r'dwelling[\s_-]?unit', re.IGNORECASE),
        re.compile(r'DU_L\d+', re.IGNORECASE),  # DU_L01, DU_L02
        re.compile(r'_\d+BR', re.IGNORECASE),  # Contains bedroom count
        re.compile(r'\d+bedrm', re.IGNORECASE),
        re.compile(r'ResZn', re.IGNORECASE),
    ],
    ZoneClassification.COMMON_AREA: [
        re.compile(r'corridor', re.IGNORECASE),
        re.compile(r'lobby', re.IGNORECASE),
        re.compile(r'fitness', re.IGNORECASE),
        re.compile(r'community', re.IGNORECASE),
        re.compile(r'bike[\s_-]?storage', re.IGNORECASE),
        re.compile(r'storage', re.IGNORECASE),
        re.compile(r'stair', re.IGNORECASE),
        re.compile(r'restroom', re.IGNORECASE),
        re.compile(r'mechanical', re.IGNORECASE),
        re.compile(r'electrical', re.IGNORECASE),
        re.compile(r'laundry', re.IGNORECASE),
        re.compile(r'mailroom', re.IGNORECASE),
        re.compile(r'trash', re.IGNORECASE),
        re.compile(r'elevator', re.IGNORECASE),
        re.compile(r'ResOtherZn', re.IGNORECASE),
    ],
    ZoneClassification.UNCONDITIONED: [
        re.compile(r'unconditioned', re.IGNORECASE),
        re.compile(r'attic', re.IGNORECASE),
        re.compile(r'parking', re.IGNORECASE),
        re.compile(r'garage', re.IGNORECASE),
    ],
}


def extract_bedroom_count(zone_name: str) -> Optional[int]:
    """
    Extract bedroom count from zone name.

    Args:
        zone_name: Name of the zone (e.g., "Dwelling Unit_L01_1BR-zn")

    Returns:
        Number of bedrooms, or None if not found
    """
    for pattern in BEDROOM_PATTERNS:
        match = pattern.search(zone_name)
        if match:
            if 'studio' in zone_name.lower() or '0BR' in zone_name.upper():
                return 0
            try:
                return int(match.group(1))
            except (ValueError, IndexError):
                continue
    return None


def classify_zone_from_name(zone_name: str) -> ZoneClassification:
    """
    Classify zone type from its name.

    Args:
        zone_name: Name of the zone

    Returns:
        ZoneClassification enum value
    """
    # Check each classification's patterns
    for classification, patterns in ZONE_NAME_PATTERNS.items():
        for pattern in patterns:
            if pattern.search(zone_name):
                return classification

    # Default to common area for unknown zones
    return ZoneClassification.COMMON_AREA


def get_common_area_category_from_name(zone_name: str) -> CommonAreaCategory:
    """
    Determine CommonAreaCategory from zone name.

    Args:
        zone_name: Name of the zone

    Returns:
        CommonAreaCategory enum value
    """
    name_lower = zone_name.lower()

    if 'corridor' in name_lower:
        return CommonAreaCategory.CORRIDOR
    elif 'lobby' in name_lower:
        return CommonAreaCategory.LOBBY
    elif 'fitness' in name_lower or 'gym' in name_lower or 'exercise' in name_lower:
        return CommonAreaCategory.FITNESS
    elif 'community' in name_lower or 'conference' in name_lower or 'meeting' in name_lower:
        return CommonAreaCategory.CONFERENCE
    elif 'bike' in name_lower or 'storage' in name_lower:
        return CommonAreaCategory.STORAGE
    elif 'stair' in name_lower:
        return CommonAreaCategory.STAIRWELL
    elif 'restroom' in name_lower or 'toilet' in name_lower or 'bathroom' in name_lower:
        return CommonAreaCategory.RESTROOM
    elif 'mechanical' in name_lower or 'electrical' in name_lower or 'mech' in name_lower:
        return CommonAreaCategory.MECHANICAL
    elif 'laundry' in name_lower:
        return CommonAreaCategory.LAUNDRY
    elif 'parking' in name_lower or 'garage' in name_lower:
        return CommonAreaCategory.PARKING
    elif 'elevator' in name_lower and 'lobby' not in name_lower:
        return CommonAreaCategory.ELEVATOR
    elif 'office' in name_lower:
        return CommonAreaCategory.OFFICE

    return CommonAreaCategory.OTHER


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class ZoneMeterAssignment:
    """
    Complete meter assignment for a single zone.

    Contains hierarchical meter names at all levels for both electric and gas.
    """
    zone_name: str
    zone_classification: ZoneClassification
    section_type: BuildingSectionType

    # Common area category (if applicable)
    category: Optional[CommonAreaCategory] = None

    # Dwelling unit info (if applicable)
    bedroom_count: Optional[int] = None

    # Zone multiplier (for prototype zones)
    multiplier: int = 1

    # Zone area from CSE
    area_sf: float = 0.0

    # Whether this zone has gas consumption (DHW, heating, cooking)
    has_gas: bool = True  # Default to True, can be refined later

    # Generated ELECTRIC meter names
    zone_meter: str = ""           # "MtrElec_Fitness-zn"
    category_meter: str = ""       # "MtrElec_CA_FITNESS"
    dwelling_type_meter: str = ""  # "MtrElec_DU_1BR" (for dwelling units)
    section_meter: str = ""        # "MtrElec_CommonArea"
    building_meter: str = ""       # "MtrElec"

    # Generated GAS meter names (parallel structure)
    gas_zone_meter: str = ""           # "MtrGas_Fitness-zn"
    gas_category_meter: str = ""       # "MtrGas_CA_FITNESS"
    gas_dwelling_type_meter: str = ""  # "MtrGas_DU_1BR" (for dwelling units)
    gas_section_meter: str = ""        # "MtrGas_CommonArea"
    gas_building_meter: str = ""       # "MtrGas"

    # Original meter from CSE file (for reference)
    original_meter: Optional[str] = None

    def __post_init__(self):
        """Generate meter names after initialization."""
        self._generate_meter_names()

    def _generate_meter_names(self):
        """Generate hierarchical meter names for this zone (electric and gas)."""
        # Sanitize zone name once for both fuels
        safe_zone_name = self._sanitize_meter_name(self.zone_name)
        section_name = SECTION_METER_NAMES.get(self.section_type, "Other")

        # === ELECTRIC METERS ===
        self.building_meter = METER_PREFIX_ELECTRIC
        self.section_meter = f"{METER_PREFIX_ELECTRIC}_{section_name}"
        self.zone_meter = f"{METER_PREFIX_ELECTRIC}_{safe_zone_name}"

        if self.zone_classification == ZoneClassification.DWELLING_UNIT:
            if self.bedroom_count is not None:
                self.dwelling_type_meter = f"{METER_PREFIX_ELECTRIC}_DU_{self.bedroom_count}BR"
            else:
                self.dwelling_type_meter = f"{METER_PREFIX_ELECTRIC}_DU_UNK"
        elif self.zone_classification == ZoneClassification.COMMON_AREA and self.category:
            prefix = CATEGORY_METER_PREFIXES.get(self.category, "CA_OTHER")
            self.category_meter = f"{METER_PREFIX_ELECTRIC}_{prefix}"

        # === GAS METERS (parallel structure) ===
        if self.has_gas:
            self.gas_building_meter = METER_PREFIX_GAS
            self.gas_section_meter = f"{METER_PREFIX_GAS}_{section_name}"
            self.gas_zone_meter = f"{METER_PREFIX_GAS}_{safe_zone_name}"

            if self.zone_classification == ZoneClassification.DWELLING_UNIT:
                if self.bedroom_count is not None:
                    self.gas_dwelling_type_meter = f"{METER_PREFIX_GAS}_DU_{self.bedroom_count}BR"
                else:
                    self.gas_dwelling_type_meter = f"{METER_PREFIX_GAS}_DU_UNK"
            elif self.zone_classification == ZoneClassification.COMMON_AREA and self.category:
                prefix = CATEGORY_METER_PREFIXES.get(self.category, "CA_OTHER")
                self.gas_category_meter = f"{METER_PREFIX_GAS}_{prefix}"

    def _sanitize_meter_name(self, name: str) -> str:
        """
        Sanitize zone name for use as meter name.

        CSE meter names can't have certain characters.
        """
        # Remove -zn suffix
        name = re.sub(r'-zn$', '', name, flags=re.IGNORECASE)
        # Replace spaces with underscores
        name = name.replace(' ', '_')
        # Remove other special characters
        name = re.sub(r'[^a-zA-Z0-9_-]', '', name)
        return name

    @property
    def is_dwelling_unit(self) -> bool:
        """True if this is a dwelling unit zone."""
        return self.zone_classification == ZoneClassification.DWELLING_UNIT

    @property
    def is_common_area(self) -> bool:
        """True if this is a common area zone."""
        return self.zone_classification == ZoneClassification.COMMON_AREA

    @property
    def aggregation_meter(self) -> str:
        """
        Get the appropriate electric aggregation meter for this zone.

        For dwelling units: dwelling_type_meter (MtrElec_DU_1BR)
        For common areas: category_meter (MtrElec_CA_FITNESS)
        """
        if self.is_dwelling_unit:
            return self.dwelling_type_meter
        elif self.is_common_area:
            return self.category_meter
        else:
            return self.section_meter

    @property
    def gas_aggregation_meter(self) -> str:
        """
        Get the appropriate gas aggregation meter for this zone.

        For dwelling units: gas_dwelling_type_meter (MtrGas_DU_1BR)
        For common areas: gas_category_meter (MtrGas_CA_FITNESS)
        Returns empty string if zone has no gas.
        """
        if not self.has_gas:
            return ""
        if self.is_dwelling_unit:
            return self.gas_dwelling_type_meter
        elif self.is_common_area:
            return self.gas_category_meter
        else:
            return self.gas_section_meter


@dataclass
class MeterHierarchy:
    """
    Complete hierarchical meter structure for a building.

    Contains all meter names and their submeter relationships for both
    electric and gas fuels.
    """
    # === ELECTRIC METERS ===
    building_meter: str = METER_PREFIX_ELECTRIC

    # Section-level meters
    section_meters: Dict[BuildingSectionType, str] = field(default_factory=dict)

    # Category-level meters (for common areas)
    category_meters: Dict[CommonAreaCategory, str] = field(default_factory=dict)

    # Dwelling type meters (by bedroom count)
    dwelling_type_meters: Dict[int, str] = field(default_factory=dict)

    # Zone-level meters (keyed by zone name)
    zone_meters: Dict[str, str] = field(default_factory=dict)

    # Submeter relationships: parent_meter -> [child_meters]
    submeter_map: Dict[str, List[str]] = field(default_factory=dict)

    # Multiplier map for submeter aggregation: parent -> {child: multiplier}
    multiplier_map: Dict[str, Dict[str, int]] = field(default_factory=dict)

    # === GAS METERS (parallel structure) ===
    gas_building_meter: str = METER_PREFIX_GAS

    # Section-level gas meters
    gas_section_meters: Dict[BuildingSectionType, str] = field(default_factory=dict)

    # Category-level gas meters (for common areas)
    gas_category_meters: Dict[CommonAreaCategory, str] = field(default_factory=dict)

    # Dwelling type gas meters (by bedroom count)
    gas_dwelling_type_meters: Dict[int, str] = field(default_factory=dict)

    # Zone-level gas meters (keyed by zone name)
    gas_zone_meters: Dict[str, str] = field(default_factory=dict)

    # Gas submeter relationships: parent_meter -> [child_meters]
    gas_submeter_map: Dict[str, List[str]] = field(default_factory=dict)

    # Gas multiplier map: parent -> {child: multiplier}
    gas_multiplier_map: Dict[str, Dict[str, int]] = field(default_factory=dict)

    @property
    def all_meters(self) -> Set[str]:
        """Get all unique electric meter names."""
        meters = {self.building_meter}
        meters.update(self.section_meters.values())
        meters.update(self.category_meters.values())
        meters.update(self.dwelling_type_meters.values())
        meters.update(self.zone_meters.values())
        return meters

    @property
    def all_gas_meters(self) -> Set[str]:
        """Get all unique gas meter names."""
        meters = {self.gas_building_meter}
        meters.update(self.gas_section_meters.values())
        meters.update(self.gas_category_meters.values())
        meters.update(self.gas_dwelling_type_meters.values())
        meters.update(self.gas_zone_meters.values())
        # Filter out empty strings (zones without gas)
        return {m for m in meters if m}

    @property
    def meter_count(self) -> int:
        """Total number of electric meters in hierarchy."""
        return len(self.all_meters)

    @property
    def gas_meter_count(self) -> int:
        """Total number of gas meters in hierarchy."""
        return len(self.all_gas_meters)

    def get_meter_level(self, meter_name: str) -> int:
        """
        Get the hierarchy level of a meter (0=building, 1=section, etc.).
        """
        if meter_name == self.building_meter:
            return 0
        elif meter_name in self.section_meters.values():
            return 1
        elif meter_name in self.category_meters.values() or \
             meter_name in self.dwelling_type_meters.values():
            return 2
        elif meter_name in self.zone_meters.values():
            return 3
        return -1  # Unknown

    def get_parent_meter(self, meter_name: str) -> Optional[str]:
        """Get the parent meter of a given meter."""
        for parent, children in self.submeter_map.items():
            if meter_name in children:
                return parent
        return None

    def get_child_meters(self, meter_name: str) -> List[str]:
        """Get all direct child meters of a given meter."""
        return self.submeter_map.get(meter_name, [])


# =============================================================================
# ZONE METER MAPPER
# =============================================================================

class ZoneMeterMapper:
    """
    Maps CSE zones to meter categories and generates hierarchical meter names.

    Example usage:
        >>> model = parse_cse_zone_input(cse_file)
        >>> mapper = ZoneMeterMapper()
        >>> mapper.map_zones(model.zones)
        >>> hierarchy = mapper.get_meter_hierarchy()
        >>> assignments = mapper.get_zone_assignments()
    """

    def __init__(self):
        """Initialize the mapper."""
        self._assignments: Dict[str, ZoneMeterAssignment] = {}
        self._hierarchy = MeterHierarchy()
        self._mapped = False

    def map_zones(
        self,
        zones: Dict[str, CSEZone],
        space_function_map: Optional[Dict[str, str]] = None,
    ) -> None:
        """
        Map CSE zones to meter categories.

        Args:
            zones: Dictionary of zone name -> CSEZone from parser
            space_function_map: Optional mapping of zone name to space function
                              (for classification override)
        """
        self._assignments.clear()

        for zone_name, zone in zones.items():
            assignment = self._classify_and_assign(zone, space_function_map)
            self._assignments[zone_name] = assignment

        self._build_hierarchy()
        self._mapped = True

        logger.info(f"Mapped {len(self._assignments)} zones to {self._hierarchy.meter_count} meters")

    def _classify_and_assign(
        self,
        zone: CSEZone,
        space_function_map: Optional[Dict[str, str]] = None,
    ) -> ZoneMeterAssignment:
        """
        Classify a zone and create meter assignment.
        """
        zone_name = zone.name

        # Classify zone type from name
        classification = classify_zone_from_name(zone_name)

        # Map to building section
        if classification == ZoneClassification.DWELLING_UNIT:
            section_type = BuildingSectionType.RESIDENTIAL
            bedroom_count = extract_bedroom_count(zone_name)
            category = None
        elif classification == ZoneClassification.COMMON_AREA:
            section_type = BuildingSectionType.COMMON_AREA
            bedroom_count = None
            category = get_common_area_category_from_name(zone_name)

            # Special section assignments
            if category == CommonAreaCategory.PARKING:
                section_type = BuildingSectionType.PARKING
            elif category == CommonAreaCategory.FITNESS:
                section_type = BuildingSectionType.AMENITY
        elif classification == ZoneClassification.UNCONDITIONED:
            section_type = BuildingSectionType.COMMON_AREA
            bedroom_count = None
            category = CommonAreaCategory.UNCONDITIONED
        else:
            section_type = BuildingSectionType.COMMERCIAL
            bedroom_count = None
            category = None

        # Get original meter from first gain (if available)
        original_meter = None
        if zone.gains:
            original_meter = zone.gains[0].meter

        return ZoneMeterAssignment(
            zone_name=zone_name,
            zone_classification=classification,
            section_type=section_type,
            category=category,
            bedroom_count=bedroom_count,
            multiplier=1,  # Could extract from zone model
            area_sf=zone.area_sf or 0.0,
            original_meter=original_meter,
        )

    def _build_hierarchy(self) -> None:
        """Build the meter hierarchy from zone assignments (electric and gas)."""
        self._hierarchy = MeterHierarchy()

        # Collect unique meters at each level
        sections_used: Set[BuildingSectionType] = set()
        categories_used: Set[CommonAreaCategory] = set()
        bedroom_counts_used: Set[int] = set()

        # Track which sections/categories/bedrooms have gas zones
        gas_sections_used: Set[BuildingSectionType] = set()
        gas_categories_used: Set[CommonAreaCategory] = set()
        gas_bedroom_counts_used: Set[int] = set()

        for assignment in self._assignments.values():
            sections_used.add(assignment.section_type)

            if assignment.is_dwelling_unit and assignment.bedroom_count is not None:
                bedroom_counts_used.add(assignment.bedroom_count)

            if assignment.is_common_area and assignment.category:
                categories_used.add(assignment.category)

            # Add electric zone meter
            self._hierarchy.zone_meters[assignment.zone_name] = assignment.zone_meter

            # Add gas zone meter (if zone has gas)
            if assignment.has_gas and assignment.gas_zone_meter:
                self._hierarchy.gas_zone_meters[assignment.zone_name] = assignment.gas_zone_meter
                gas_sections_used.add(assignment.section_type)

                if assignment.is_dwelling_unit and assignment.bedroom_count is not None:
                    gas_bedroom_counts_used.add(assignment.bedroom_count)
                if assignment.is_common_area and assignment.category:
                    gas_categories_used.add(assignment.category)

        # === ELECTRIC METERS ===
        # Create section meters
        for section in sections_used:
            section_name = SECTION_METER_NAMES.get(section, "Other")
            meter_name = f"{METER_PREFIX_ELECTRIC}_{section_name}"
            self._hierarchy.section_meters[section] = meter_name

        # Create category meters
        for category in categories_used:
            prefix = CATEGORY_METER_PREFIXES.get(category, "CA_OTHER")
            meter_name = f"{METER_PREFIX_ELECTRIC}_{prefix}"
            self._hierarchy.category_meters[category] = meter_name

        # Create dwelling type meters
        for bedroom_count in bedroom_counts_used:
            meter_name = f"{METER_PREFIX_ELECTRIC}_DU_{bedroom_count}BR"
            self._hierarchy.dwelling_type_meters[bedroom_count] = meter_name

        # === GAS METERS (parallel structure for zones with gas) ===
        # Create gas section meters
        for section in gas_sections_used:
            section_name = SECTION_METER_NAMES.get(section, "Other")
            meter_name = f"{METER_PREFIX_GAS}_{section_name}"
            self._hierarchy.gas_section_meters[section] = meter_name

        # Create gas category meters
        for category in gas_categories_used:
            prefix = CATEGORY_METER_PREFIXES.get(category, "CA_OTHER")
            meter_name = f"{METER_PREFIX_GAS}_{prefix}"
            self._hierarchy.gas_category_meters[category] = meter_name

        # Create gas dwelling type meters
        for bedroom_count in gas_bedroom_counts_used:
            meter_name = f"{METER_PREFIX_GAS}_DU_{bedroom_count}BR"
            self._hierarchy.gas_dwelling_type_meters[bedroom_count] = meter_name

        # Build submeter relationships (electric and gas)
        self._build_submeter_map()
        self._build_gas_submeter_map()

    def _build_submeter_map(self) -> None:
        """Build submeter relationship map."""
        submeter_map = self._hierarchy.submeter_map
        multiplier_map = self._hierarchy.multiplier_map

        # Building -> Sections
        section_meters = list(self._hierarchy.section_meters.values())
        if section_meters:
            submeter_map[self._hierarchy.building_meter] = section_meters
            multiplier_map[self._hierarchy.building_meter] = {m: 1 for m in section_meters}

        # Sections -> Categories/Dwelling Types/Zones
        for section_type, section_meter in self._hierarchy.section_meters.items():
            child_meters = []
            child_multipliers = {}

            if section_type == BuildingSectionType.RESIDENTIAL:
                # Residential -> Dwelling type meters
                for bedroom_count in sorted(self._hierarchy.dwelling_type_meters.keys()):
                    meter = self._hierarchy.dwelling_type_meters[bedroom_count]
                    child_meters.append(meter)
                    child_multipliers[meter] = 1

            elif section_type == BuildingSectionType.COMMON_AREA:
                # Common Area -> Category meters
                for category, meter in self._hierarchy.category_meters.items():
                    # Only include categories that belong to this section
                    if category not in [CommonAreaCategory.PARKING, CommonAreaCategory.FITNESS]:
                        child_meters.append(meter)
                        child_multipliers[meter] = 1

            elif section_type == BuildingSectionType.AMENITY:
                # Amenity -> Fitness category
                if CommonAreaCategory.FITNESS in self._hierarchy.category_meters:
                    meter = self._hierarchy.category_meters[CommonAreaCategory.FITNESS]
                    child_meters.append(meter)
                    child_multipliers[meter] = 1

            elif section_type == BuildingSectionType.PARKING:
                # Parking -> Parking category
                if CommonAreaCategory.PARKING in self._hierarchy.category_meters:
                    meter = self._hierarchy.category_meters[CommonAreaCategory.PARKING]
                    child_meters.append(meter)
                    child_multipliers[meter] = 1

            if child_meters:
                submeter_map[section_meter] = child_meters
                multiplier_map[section_meter] = child_multipliers

        # Dwelling type meters -> Zone meters
        for bedroom_count, du_meter in self._hierarchy.dwelling_type_meters.items():
            zone_meters = []
            zone_multipliers = {}

            for assignment in self._assignments.values():
                if assignment.is_dwelling_unit and assignment.bedroom_count == bedroom_count:
                    zone_meters.append(assignment.zone_meter)
                    zone_multipliers[assignment.zone_meter] = assignment.multiplier

            if zone_meters:
                submeter_map[du_meter] = zone_meters
                multiplier_map[du_meter] = zone_multipliers

        # Category meters -> Zone meters
        for category, cat_meter in self._hierarchy.category_meters.items():
            zone_meters = []
            zone_multipliers = {}

            for assignment in self._assignments.values():
                if assignment.is_common_area and assignment.category == category:
                    zone_meters.append(assignment.zone_meter)
                    zone_multipliers[assignment.zone_meter] = assignment.multiplier

            if zone_meters:
                submeter_map[cat_meter] = zone_meters
                multiplier_map[cat_meter] = zone_multipliers

    def _build_gas_submeter_map(self) -> None:
        """Build gas submeter relationship map (parallel to electric)."""
        submeter_map = self._hierarchy.gas_submeter_map
        multiplier_map = self._hierarchy.gas_multiplier_map

        # Building -> Sections
        section_meters = list(self._hierarchy.gas_section_meters.values())
        if section_meters:
            submeter_map[self._hierarchy.gas_building_meter] = section_meters
            multiplier_map[self._hierarchy.gas_building_meter] = {m: 1 for m in section_meters}

        # Sections -> Categories/Dwelling Types/Zones
        for section_type, section_meter in self._hierarchy.gas_section_meters.items():
            child_meters = []
            child_multipliers = {}

            if section_type == BuildingSectionType.RESIDENTIAL:
                # Residential -> Dwelling type meters
                for bedroom_count in sorted(self._hierarchy.gas_dwelling_type_meters.keys()):
                    meter = self._hierarchy.gas_dwelling_type_meters[bedroom_count]
                    child_meters.append(meter)
                    child_multipliers[meter] = 1

            elif section_type == BuildingSectionType.COMMON_AREA:
                # Common Area -> Category meters
                for category, meter in self._hierarchy.gas_category_meters.items():
                    # Only include categories that belong to this section
                    if category not in [CommonAreaCategory.PARKING, CommonAreaCategory.FITNESS]:
                        child_meters.append(meter)
                        child_multipliers[meter] = 1

            elif section_type == BuildingSectionType.AMENITY:
                # Amenity -> Fitness category
                if CommonAreaCategory.FITNESS in self._hierarchy.gas_category_meters:
                    meter = self._hierarchy.gas_category_meters[CommonAreaCategory.FITNESS]
                    child_meters.append(meter)
                    child_multipliers[meter] = 1

            elif section_type == BuildingSectionType.PARKING:
                # Parking -> Parking category
                if CommonAreaCategory.PARKING in self._hierarchy.gas_category_meters:
                    meter = self._hierarchy.gas_category_meters[CommonAreaCategory.PARKING]
                    child_meters.append(meter)
                    child_multipliers[meter] = 1

            if child_meters:
                submeter_map[section_meter] = child_meters
                multiplier_map[section_meter] = child_multipliers

        # Dwelling type meters -> Zone meters
        for bedroom_count, du_meter in self._hierarchy.gas_dwelling_type_meters.items():
            zone_meters = []
            zone_multipliers = {}

            for assignment in self._assignments.values():
                if assignment.is_dwelling_unit and assignment.bedroom_count == bedroom_count:
                    if assignment.has_gas and assignment.gas_zone_meter:
                        zone_meters.append(assignment.gas_zone_meter)
                        zone_multipliers[assignment.gas_zone_meter] = assignment.multiplier

            if zone_meters:
                submeter_map[du_meter] = zone_meters
                multiplier_map[du_meter] = zone_multipliers

        # Category meters -> Zone meters
        for category, cat_meter in self._hierarchy.gas_category_meters.items():
            zone_meters = []
            zone_multipliers = {}

            for assignment in self._assignments.values():
                if assignment.is_common_area and assignment.category == category:
                    if assignment.has_gas and assignment.gas_zone_meter:
                        zone_meters.append(assignment.gas_zone_meter)
                        zone_multipliers[assignment.gas_zone_meter] = assignment.multiplier

            if zone_meters:
                submeter_map[cat_meter] = zone_meters
                multiplier_map[cat_meter] = zone_multipliers

    def get_zone_assignments(self) -> Dict[str, ZoneMeterAssignment]:
        """Get all zone meter assignments."""
        return self._assignments.copy()

    def get_assignment(self, zone_name: str) -> Optional[ZoneMeterAssignment]:
        """Get assignment for a specific zone."""
        return self._assignments.get(zone_name)

    def get_meter_hierarchy(self) -> MeterHierarchy:
        """Get the complete meter hierarchy."""
        return self._hierarchy

    def get_zones_for_meter(self, meter_name: str) -> List[str]:
        """
        Get all zone names that roll up to a given meter.

        Includes both direct assignments and transitive through hierarchy.
        """
        zones = []

        # Check for direct zone meter assignment
        for zone_name, assignment in self._assignments.items():
            if assignment.zone_meter == meter_name:
                zones.append(zone_name)

        # Check for aggregation meters (category, dwelling type)
        if not zones:
            for zone_name, assignment in self._assignments.items():
                if assignment.aggregation_meter == meter_name:
                    zones.append(zone_name)

        # Check for section meters
        if not zones:
            for zone_name, assignment in self._assignments.items():
                if assignment.section_meter == meter_name:
                    zones.append(zone_name)

        # Check for building meter
        if not zones and meter_name == self._hierarchy.building_meter:
            zones = list(self._assignments.keys())

        return zones

    def summary(self) -> Dict:
        """Get summary of meter mapping (electric and gas)."""
        # Count by classification
        classification_counts = {}
        for assignment in self._assignments.values():
            key = assignment.zone_classification.value
            classification_counts[key] = classification_counts.get(key, 0) + 1

        # Count by section
        section_counts = {}
        for assignment in self._assignments.values():
            key = assignment.section_type.value
            section_counts[key] = section_counts.get(key, 0) + 1

        # Count by bedroom (dwelling units only)
        bedroom_counts = {}
        for assignment in self._assignments.values():
            if assignment.is_dwelling_unit and assignment.bedroom_count is not None:
                key = f"{assignment.bedroom_count}BR"
                bedroom_counts[key] = bedroom_counts.get(key, 0) + 1

        # Count by category (common areas only)
        category_counts = {}
        for assignment in self._assignments.values():
            if assignment.is_common_area and assignment.category:
                key = assignment.category.value
                category_counts[key] = category_counts.get(key, 0) + 1

        # Count zones with gas
        gas_zone_count = sum(1 for a in self._assignments.values() if a.has_gas)

        return {
            'zone_count': len(self._assignments),
            'meter_count': self._hierarchy.meter_count,
            'gas_meter_count': self._hierarchy.gas_meter_count,
            'gas_zone_count': gas_zone_count,
            'by_classification': classification_counts,
            'by_section': section_counts,
            'by_bedroom_count': bedroom_counts,
            'by_category': category_counts,
        }

    def format_summary(self) -> str:
        """Format summary as text table."""
        summary = self.summary()

        lines = [
            "=" * 70,
            "ZONE-METER MAPPING SUMMARY",
            "=" * 70,
            "",
            f"Total Zones: {summary['zone_count']}",
            f"Electric Meters: {summary['meter_count']}",
            f"Gas Meters: {summary['gas_meter_count']}",
            f"Zones with Gas: {summary['gas_zone_count']}",
            "",
            "By Classification:",
        ]

        for key, count in summary['by_classification'].items():
            lines.append(f"  {key}: {count}")

        lines.append("")
        lines.append("By Building Section:")
        for key, count in summary['by_section'].items():
            lines.append(f"  {key}: {count}")

        if summary['by_bedroom_count']:
            lines.append("")
            lines.append("Dwelling Units by Bedroom Count:")
            for key, count in sorted(summary['by_bedroom_count'].items()):
                lines.append(f"  {key}: {count}")

        if summary['by_category']:
            lines.append("")
            lines.append("Common Areas by Category:")
            for key, count in sorted(summary['by_category'].items()):
                lines.append(f"  {key}: {count}")

        lines.append("=" * 70)

        return "\n".join(lines)


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def map_cse_zones(model: CSEZoneInputModel) -> Tuple[Dict[str, ZoneMeterAssignment], MeterHierarchy]:
    """
    Convenience function to map zones from a parsed CSE model.

    Args:
        model: Parsed CSE input model

    Returns:
        Tuple of (zone assignments dict, meter hierarchy)
    """
    mapper = ZoneMeterMapper()
    mapper.map_zones(model.zones)
    return mapper.get_zone_assignments(), mapper.get_meter_hierarchy()


def format_meter_hierarchy(hierarchy: MeterHierarchy) -> str:
    """
    Format meter hierarchy as text tree.

    Args:
        hierarchy: MeterHierarchy object

    Returns:
        Formatted text tree
    """
    lines = [
        "METER HIERARCHY",
        "=" * 50,
        "",
        hierarchy.building_meter,
    ]

    # Section level
    for section, meter in sorted(hierarchy.section_meters.items(), key=lambda x: x[0].value):
        lines.append(f"├── {meter}")

        # Get children
        children = hierarchy.get_child_meters(meter)
        for i, child in enumerate(sorted(children)):
            is_last = (i == len(children) - 1)
            prefix = "│   └── " if is_last else "│   ├── "
            lines.append(f"{prefix}{child}")

            # Get zone-level children
            zone_children = hierarchy.get_child_meters(child)
            for j, zone_meter in enumerate(sorted(zone_children)):
                z_is_last = (j == len(zone_children) - 1)
                z_prefix = "│   │   └── " if z_is_last else "│   │   ├── "
                if is_last:
                    z_prefix = "│       └── " if z_is_last else "│       ├── "
                lines.append(f"{z_prefix}{zone_meter}")

    return "\n".join(lines)
