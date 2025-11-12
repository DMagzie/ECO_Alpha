"""
Zone Parser - Spatial Hierarchy Foundation Parser
================================================

PURPOSE:
Extracts thermal zone definitions from CIBD22X XML, forming the foundation
of the spatial hierarchy: ZoneGroups → Zones → Surfaces → Openings.

ZONE TYPES IN CBECC:
CBECC supports multiple zone element types for different building contexts:

1. ResZn (Residential Zone)
   - Dwelling unit zones in residential buildings
   - Contains bedroom, bathroom, living room, etc.
   - Typically has DU (Dwelling Unit) parent reference

2. ResOtherZn (Residential Other Zone)
   - Common areas in residential buildings
   - Lobby, corridors, laundry rooms, etc.
   - Does NOT belong to a specific dwelling unit

3. ComZn (Commercial Zone)
   - Zones in commercial/nonresidential buildings
   - Office spaces, retail, warehouse, etc.
   - Uses space function types from Title 24

4. Spc (Space) - CBECC SDDXML format
   - Generic space type in detailed energy models
   - Can be residential or commercial

5. ThrmlZn (Thermal Zone) - CBECC SDDXML format
   - Grouped spaces with similar HVAC characteristics
   - Multiple Spc elements can reference same ThrmlZn

All types are parsed into the universal Zone model, with type preserved
in annotations for round-trip fidelity.

KEY RESPONSIBILITIES:
1. Parse zone geometry (area, volume, heights, multiplier)
2. Extract space function and apply Title 24 defaults (occupancy, equipment, lighting)
3. Parse conditioning type (conditioned, unconditioned, indirectly conditioned)
4. Link zones to parent zone groups (hierarchical relationship)
5. Extract HVAC and DHW system references
6. Parse IAQ/ventilation configuration
7. Parse daylighting control properties
8. Handle dwelling unit associations (for residential zones)

DEPENDENCY: Requires ZoneGroups
Zones must be parsed AFTER zone groups because each zone has a parent
zone group reference. The zone_group_map parameter enables this linking.

TITLE 24 DEFAULT LOOKUPS:
For commercial zones with space function types (e.g., "Office - Open"),
this parser queries the Title 24 defaults library to populate:
- Occupancy density (people/m²)
- Equipment power density (W/m²)
- Lighting power density (W/m²)

These defaults are critical for energy code compliance calculations.

PARENT NAVIGATION WORKAROUND:
ElementTree doesn't provide parent navigation, so we build a parent_map
(child→parent) to find the zone's containing zone group element.

DESIGN PATTERN:
This is a "Hierarchical Parser" with dependencies on ZoneGroupParser.
It performs extensive property extraction and default value lookups.
"""

from typing import List, Optional, Dict, Any
import xml.etree.ElementTree as ET
import logging

from .base_parser import BaseParser
from eco_tools.core.internal_repr import Zone, ZoneGroup
from eco_tools.core.id_registry import IDRegistry
from eco_tools.core.space_function_defaults import (
    get_space_function_defaults,
    get_occupancy_density_si,
    get_equipment_density_si,
    get_lighting_density_si,
)

# Get module logger
logger = logging.getLogger('eco_tools.parsers')


class ZoneParser(BaseParser):
    """
    Parser for zone elements in CIBD22X files.

    Handles multiple zone types:
    - ResZn: Residential dwelling unit zones
    - ResOtherZn: Residential common area zones
    - ComZn: Commercial zones
    - Spc: Generic space (CBECC SDDXML)
    - ThrmlZn: Thermal zone (CBECC SDDXML)
    """

    def __init__(self, id_registry: IDRegistry = None):
        """
        Initialize the zone parser.

        Args:
            id_registry: ID registry for generating unique zone IDs.
                        If None, a new registry will be created.
        """
        super().__init__()
        self.id_registry = id_registry or IDRegistry()

    def parse_zones(self, root: ET.Element, zone_groups: List[ZoneGroup]) -> List[Zone]:
        """
        Parse all zones from CIBD22X XML and link them to parent zone groups.

        PARSING STRATEGY:
        1. Build zone_group_map for fast parent lookup (name → ID)
        2. Build parent_map for ElementTree parent navigation workaround
        3. Iterate through ALL elements looking for zone tags
        4. Parse each zone and link to parent zone group
        5. Return flat list of zones

        ZONE GROUP DEPENDENCY:
        This method REQUIRES zone_groups to be parsed first because each zone
        needs to reference its parent zone group by ID. The zone_group_map
        enables O(1) lookup: zone_group_name → zone_group_id.

        PARENT MAP WORKAROUND:
        ElementTree doesn't provide parent navigation (can't do elem.parent).
        We build parent_map = {child: parent} for the entire tree to enable
        finding the zone group that contains each zone element.

        WHY ITERATE ALL ELEMENTS:
        Zones can appear at different depths in the XML tree:
        - Residential: Project → Building → Story → ResZn
        - Commercial: Project → Building → ComZn
        Using root.iter() finds zones at any depth without hardcoding paths.

        ZONE TYPE FILTERING:
        We only process elements with tags: ResZn, ComZn, ResOtherZn, Spc, ThrmlZn.
        All other elements are skipped (e.g., Surface, Opening, System elements).

        Args:
            root: Root XML element
            zone_groups: List of parsed zone groups (from ZoneGroupParser)

        Returns:
            List of Zone objects with parent zone group references
        """
        zones = []

        # ================================================================
        # STEP 1: Build Zone Group Lookup Map
        # ================================================================
        # Create fast lookup: zone_group_name → zone_group_id
        # This enables O(1) parent linking when parsing each zone
        zone_group_map = {zg.name: zg.id for zg in zone_groups}

        # ================================================================
        # STEP 2: Build Parent Navigation Map
        # ================================================================
        # ElementTree limitation: no built-in parent navigation
        # Build map: child_element → parent_element for entire tree
        # This allows us to traverse UP from zone to find its zone group
        parent_map = {c: p for p in root.iter() for c in p}

        # ================================================================
        # STEP 3: Iterate and Parse All Zone Elements
        # ================================================================
        for zone_elem in root.iter():
            # Extract local tag name (strip namespace if present)
            tag = self._local_tag(zone_elem.tag)

            # Filter: only process zone element types
            if tag not in ('ResZn', 'ComZn', 'ResOtherZn', 'Spc', 'ThrmlZn'):
                continue

            # Extract zone name (required for identification)
            name = self.get_name(zone_elem)
            if not name:
                # Skip zones without names (rare, indicates malformed XML)
                logger.warning(f"Skipping {self._get_element_context(zone_elem)}: missing required 'name' property")
                continue

            # Parse this zone element
            zone = self._parse_single_zone(
                zone_elem, tag, name, parent_map, zone_group_map
            )
            if zone:
                zones.append(zone)
            else:
                logger.warning(f"Failed to parse {tag} '{name}'")

        return zones

    def _parse_single_zone(
        self,
        zone_elem: ET.Element,
        tag: str,
        name: str,
        parent_map: Dict,
        zone_group_map: Dict[str, str]
    ) -> Optional[Zone]:
        """
        Parse a single zone element - MOST COMPLEX PARSER METHOD.

        This method orchestrates 10+ sub-parsers to extract all zone properties.
        Zones are the foundation of the spatial hierarchy and contain extensive
        properties for energy modeling and code compliance.

        PARSING FLOW:
        1. Generate unique ID
        2. Link to parent zone group (hierarchical relationship)
        3. Parse geometry (area, volume, heights, multiplier)
        4. Parse space function and apply Title 24 defaults
        5. Parse conditioning type (determines HVAC requirements)
        6. Extract system references (HVAC, DHW)
        7. Parse IAQ/ventilation configuration
        8. Parse daylighting control properties
        9. Build annotation with format-specific properties
        10. Create Zone object

        GEOMETRY PARSING:
        - Area: Zone floor area in ft² (converted to m²)
        - Volume: Zone volume in ft³ (converted to m³)
        - Multiplier: Number of identical zones (for repeated floors)
        - Heights: Floor-to-ceiling, floor-to-floor, Z coordinates

        TITLE 24 DEFAULT LOOKUPS:
        For commercial zones with space functions (e.g., "Office - Open"),
        we query the Title 24 defaults library to populate:
        - Occupancy density (people/m²)
        - Equipment power density (W/m²)
        - Lighting power density (W/m²)
        These are stored in the zone's annotation for code compliance.

        CONDITIONING TYPES:
        - Conditioned: Mechanically heated/cooled (requires HVAC system)
        - Unconditioned: No mechanical conditioning
        - Indirectly Conditioned: Adjacent to conditioned space (heat transfer)

        SYSTEM REFERENCES:
        Zones reference HVAC and DHW systems by name:
        - ozHVACSystem: Name of HVAC system serving this zone
        - ozDHWSys: Name of DHW system serving this zone
        These references are resolved in post-processing.

        Args:
            zone_elem: XML element for the zone
            tag: Tag name (ResZn, ComZn, ResOtherZn, Spc, ThrmlZn)
            name: Zone name (already extracted)
            parent_map: Map of child→parent elements (for finding zone group)
            zone_group_map: Map of zone group name→ID (for parent linking)

        Returns:
            Zone object with all properties populated, or None if parsing fails
        """
        # ================================================================
        # STEP 1: Generate Unique ID
        # ================================================================
        zone_id = self.id_registry.generate_id('Z', name, '', 'CIBD22X')

        # ================================================================
        # STEP 2: Find and Link Parent Zone Group
        # ================================================================
        # Zones exist within zone groups (building stories in residential,
        # building itself in commercial). We traverse UP the tree to find
        # the containing zone group element, extract its name, then resolve
        # to zone group ID via zone_group_map.
        parent_zg_name = self._find_parent_zone_group(zone_elem, parent_map)

        # ================================================================
        # STEP 3: Parse Geometry Properties
        # ================================================================
        # AREA: Zone floor area in ft² → m² (× 0.092903)
        # Used for: Internal load calculations, code compliance
        area_m2, area_annotation = self._parse_area(zone_elem, tag)

        # VOLUME: Zone volume in ft³ → m³ (× 0.0283168)
        # Used for: Ventilation calculations, infiltration
        vol_m3 = self._parse_volume(zone_elem)

        # MULTIPLIER: Number of identical zones (e.g., repeated floors)
        # Used for: Reducing model size by representing N identical zones as 1
        mult = self._to_int(self.get_property(zone_elem, 'ZnMult')) or 1

        # HEIGHTS: Floor-to-ceiling, floor-to-floor, Z coordinates
        # Used for: Surface positioning, daylighting calculations
        heights = self._parse_heights(zone_elem)

        # ================================================================
        # STEP 4: Parse Zone Type and Dwelling Unit Association
        # ================================================================
        # Zone type: Additional classification (e.g., "Attic", "Plenum")
        zone_type = self.get_property(zone_elem, 'Type')

        # Dwelling unit: For residential zones, extract DU association
        # Contains: DU type reference, DU count, DU characteristics
        dwelling_unit = self._parse_dwelling_unit(zone_elem)
        du_ref = dwelling_unit['dwelling_unit_type_ref'] if dwelling_unit else None

        # ================================================================
        # STEP 5: Parse Space Function and Apply Title 24 Defaults
        # ================================================================
        # Space function: Title 24 space type (e.g., "Office - Open")
        # Triggers automatic lookup of occupancy, equipment, lighting defaults
        space_function = self._parse_space_function(zone_elem)

        # Ventilation space function: Alternative space type for IAQ calcs
        # Sometimes different from main space function
        vent_spc_func = self.get_property(zone_elem, 'VentSpcFunc')

        # ================================================================
        # STEP 6: Parse Conditioning Type
        # ================================================================
        # Determines whether zone requires HVAC system
        # Returns: (condg_type_string, conditioned_boolean)
        condg_type, conditioned = self._parse_conditioning(zone_elem)

        # ================================================================
        # STEP 7: Extract System References
        # ================================================================
        # Zones reference systems by NAME (not ID)
        # These are resolved to system IDs in post-processing
        oz_dhw_sys = self.get_property(zone_elem, 'ozDHWSys')      # DHW system name
        oz_hvac_sys = self.get_property(zone_elem, 'ozHVACSystem')  # HVAC system name

        # ================================================================
        # STEP 8: Parse IAQ/Ventilation Configuration
        # ================================================================
        # Extract indoor air quality and ventilation requirements
        # Includes: outdoor air flow rates, ventilation effectiveness, etc.
        iaq_config = self._parse_iaq_configuration(zone_elem)

        # ================================================================
        # STEP 9: Parse Daylighting Control Properties
        # ================================================================
        # Extract daylighting sensor configuration for lighting control
        # Includes: sensor positions, illuminance setpoints, control zones
        daylight = self._parse_daylighting(zone_elem)

        # ================================================================
        # STEP 10: Determine Building Type and CBECC Zone Type
        # ================================================================
        # Map XML tag to building type (Residential vs Commercial)
        building_type = self._determine_building_type(tag)

        # Map XML tag to CBECC zone type (for export round-trip)
        cbecc_zone_type = self._determine_cbecc_zone_type(tag)

        # ================================================================
        # STEP 11: Build Annotation Dictionary
        # ================================================================
        # Collect all format-specific properties for round-trip fidelity
        annotation = self._build_annotation(
            tag=tag,
            zone_type=zone_type,
            heights=heights,
            parent_zg_name=parent_zg_name,
            zone_group_map=zone_group_map,
            condg_type=condg_type,
            dwelling_unit=dwelling_unit,
            oz_dhw_sys=oz_dhw_sys,
            oz_hvac_sys=oz_hvac_sys,
            iaq_config=iaq_config,
            vent_spc_func=vent_spc_func,
            daylight=daylight,
            space_function=space_function,
        )

        # Merge area annotation (floor area round-trip info)
        annotation.update(area_annotation)

        # ================================================================
        # STEP 12: Create Zone Object
        # ================================================================
        # Assemble all parsed data into universal Zone model
        zone = Zone(
            id=zone_id,
            name=name,
            building_type=building_type,         # "Residential" or "Commercial"
            zone_type=cbecc_zone_type,           # "ResZn", "ComZn", etc.
            multiplier=mult,                      # Number of identical zones
            floor_area_m2=area_m2,                # Floor area (SI units)
            volume_m3=vol_m3,                     # Volume (SI units)
            du_ref=du_ref,                        # Dwelling unit reference (residential only)
            space_function=space_function,        # Title 24 space type
            conditioned=conditioned,              # Boolean: requires HVAC?
            annotation=annotation                 # Format-specific extras
        )

        return zone

    def _find_parent_zone_group(self, zone_elem: ET.Element, parent_map: Dict) -> Optional[str]:
        """Find parent zone group name from parent map."""
        parent_elem = parent_map.get(zone_elem)
        if parent_elem is not None:
            parent_tag = self._local_tag(parent_elem.tag)
            if parent_tag == 'ResZnGrp':
                return self.get_name(parent_elem)
        return None

    def _find_direct_child(self, parent: ET.Element, tag_name: str) -> Optional[ET.Element]:
        """
        Find a direct child element by tag name (namespace-aware).

        Unlike get_property() which searches all descendants, this only checks
        immediate children. Critical for zone properties like Area that can appear
        in both zones and their child surfaces.

        Args:
            parent: Parent XML element
            tag_name: Tag name to find (without namespace)

        Returns:
            Direct child element or None if not found
        """
        for child in parent:
            # Strip namespace from child tag
            child_tag = child.tag.split('}')[-1] if '}' in child.tag else child.tag
            if child_tag == tag_name:
                return child
        return None

    def _parse_area(self, zone_elem: ET.Element, tag: str) -> tuple[Optional[float], dict]:
        """
        Parse zone floor area and convert from ft² to m².

        ResZn uses 'FloorArea', others may use 'Area'.
        SDDXML (Spc, ThrmlZn) may calculate from PolyLp.

        CRITICAL: Must check DIRECT children only, not descendants!
        get_property() searches descendants, but zones have surface children
        with Area elements that should NOT be confused with zone area.

        Returns:
            tuple: (area_m2, area_annotation) where area_annotation contains:
                - 'original_floor_area_ft': original FloorArea string (for round-trip)
                - 'original_area_ft': original Area string (for round-trip)
                - 'had_explicit_floor_area': whether FloorArea/Area was explicitly in XML
        """
        area_annotation = {}

        # Try FloorArea first (ResZn) - DIRECT children only
        floor_area_elem = self._find_direct_child(zone_elem, 'FloorArea')
        if floor_area_elem is not None and floor_area_elem.text:
            floor_area_str = floor_area_elem.text.strip()
            area_ft2 = self._to_float(floor_area_str)
            area_annotation['original_floor_area_ft'] = floor_area_str
            area_annotation['had_explicit_floor_area'] = True
        else:
            area_ft2 = None

        # Try Area (other zones) - DIRECT children only
        if not area_ft2:
            area_elem = self._find_direct_child(zone_elem, 'Area')
            if area_elem is not None and area_elem.text:
                area_str = area_elem.text.strip()
                area_ft2 = self._to_float(area_str)
                area_annotation['original_area_ft'] = area_str
                area_annotation['had_explicit_floor_area'] = True  # Area is explicit too!

        # Calculate from PolyLp for SDDXML
        if not area_ft2 and tag in ('Spc', 'ThrmlZn'):
            area_ft2 = self._calculate_area_from_polylp(zone_elem)
            area_annotation['had_explicit_floor_area'] = False  # Calculated, not explicit

        # Convert ft² to m²
        area_m2 = (area_ft2 * 0.092903) if area_ft2 else None
        return (area_m2, area_annotation)

    def _parse_volume(self, zone_elem: ET.Element) -> Optional[float]:
        """Parse zone volume and convert from ft³ to m³."""
        # CBECC uses 'Vol' not 'Volume'
        vol_ft3 = self._to_float(self.get_property(zone_elem, 'Vol'))
        if not vol_ft3:
            vol_ft3 = self._to_float(self.get_property(zone_elem, 'Volume'))

        # Convert ft³ to m³
        return (vol_ft3 * 0.0283168) if vol_ft3 else None

    def _parse_heights(self, zone_elem: ET.Element) -> Dict[str, Any]:
        """
        Parse all height-related properties (ceiling, floor, bottom).

        Returns dict with both SI and IP values, plus original strings for
        round-trip fidelity.
        """
        heights = {}

        # Ceiling height
        ceiling_height_str = self.get_property(zone_elem, 'CeilingHeight')
        if ceiling_height_str:
            ceiling_height_ft = self._to_float(ceiling_height_str)
            heights['ceiling_height_m'] = (ceiling_height_ft * 0.3048) if ceiling_height_ft else None
            heights['original_ceiling_height_ft'] = ceiling_height_str

        # Floor height
        floor_height_str = self.get_property(zone_elem, 'FloorHeight')
        if floor_height_str:
            floor_height_ft = self._to_float(floor_height_str)
            heights['floor_height_m'] = (floor_height_ft * 0.3048) if floor_height_ft else None
            heights['original_floor_height_ft'] = floor_height_str

        # Floor Z coordinate
        floor_z_str = self.get_property(zone_elem, 'FloorZ')
        if floor_z_str:
            floor_z_ft = self._to_float(floor_z_str)
            heights['floor_z_m'] = (floor_z_ft * 0.3048) if floor_z_ft else None
            heights['original_floor_z_ft'] = floor_z_str

        # Bottom Z coordinate (ResOtherZn)
        bottom_str = self.get_property(zone_elem, 'Bottom')
        if bottom_str:
            bottom_ft = self._to_float(bottom_str)
            heights['bottom_m'] = (bottom_ft * 0.3048) if bottom_ft else None
            heights['original_bottom_ft'] = bottom_str

        return heights

    def _parse_dwelling_unit(self, zone_elem: ET.Element) -> Optional[Dict[str, Any]]:
        """
        Parse DwellUnit child element (for ResZn zones).

        DwellUnit references DwellUnitType and includes count.
        """
        du_elem = zone_elem.find('DwellUnit')
        if du_elem is not None:
            return {
                'name': self.get_name(du_elem),
                'dwelling_unit_type_ref': self.get_property(du_elem, 'DwellUnitTypeRef'),
                'count': self._to_int(self.get_property(du_elem, 'Count')) or 1,
            }
        return None

    def _parse_space_function(self, zone_elem: ET.Element) -> Optional[str]:
        """
        Parse space function type.

        CBECC: Try SpcFunc first, then SpcFuncDefaultsRef.
        """
        space_function = self.get_property(zone_elem, 'SpcFunc')
        if not space_function:
            space_function = self.get_property(zone_elem, 'SpcFuncDefaultsRef')
        return space_function

    def _parse_conditioning(self, zone_elem: ET.Element) -> tuple:
        """
        Parse conditioning type.

        Returns: (condg_type_str, conditioned_bool)
        """
        condg_type = self.get_property(zone_elem, 'CondgType')
        conditioned = None

        if condg_type:
            # DirectlyConditioned, IndirectlyConditioned = conditioned
            # Unconditioned, Plenum = not conditioned
            if condg_type in ('DirectlyConditioned', 'IndirectlyConditioned'):
                conditioned = True
            elif condg_type in ('Unconditioned', 'Plenum'):
                conditioned = False

        return condg_type, conditioned

    def _parse_iaq_configuration(self, zone_elem: ET.Element) -> Dict[str, str]:
        """
        Parse IAQ/ventilation configuration for ResOtherZn zones.

        Returns dict with IAQ option and related properties.
        """
        config = {}

        # IAQ Option (e.g., "Individual IAQ Fans", "Central Supply / Central Exhaust")
        iaq_option = self.get_property(zone_elem, 'IAQOption')
        if iaq_option:
            config['iaq_option'] = iaq_option

        # Central ventilation system properties
        central_vent_sys_ref = self.get_property(zone_elem, 'CentralVentSysRef')
        if central_vent_sys_ref:
            config['central_vent_sys_ref'] = central_vent_sys_ref

        central_supply_cfm = self.get_property(zone_elem, 'CentralSupplyCFM')
        if central_supply_cfm:
            config['central_supply_cfm'] = central_supply_cfm

        central_exhaust_cfm = self.get_property(zone_elem, 'CentralExhaustCFM')
        if central_exhaust_cfm:
            config['central_exhaust_cfm'] = central_exhaust_cfm

        # IAQ fan reference (for "Individual IAQ Fans" option)
        iaq_fan_ref = self.get_property(zone_elem, 'IAQFanRef')
        if iaq_fan_ref:
            config['iaq_fan_ref'] = iaq_fan_ref

        return config

    def _parse_daylighting(self, zone_elem: ET.Element) -> Dict[str, float]:
        """Parse daylighting control lighting power (CBECC-Com SDDXML)."""
        daylight = {}

        pri_daylt_pwr = self._to_float(self.get_property(zone_elem, 'PriSideDayltgCtrlLtgPwr'))
        if pri_daylt_pwr:
            daylight['primary_sidelit_lighting_power_w'] = pri_daylt_pwr

        sec_daylt_pwr = self._to_float(self.get_property(zone_elem, 'SecSideDayltgCtrlLtgPwr'))
        if sec_daylt_pwr:
            daylight['secondary_sidelit_lighting_power_w'] = sec_daylt_pwr

        return daylight

    def _determine_building_type(self, tag: str) -> str:
        """Determine building type from zone tag."""
        if tag == 'ResZn':
            return 'MF'  # Multifamily
        elif tag == 'ComZn':
            return 'NR'  # Nonresidential
        else:
            return 'OTHER'

    def _determine_cbecc_zone_type(self, tag: str) -> str:
        """Determine CBECC zone type for export."""
        if tag == 'ResZn':
            return 'residential'
        elif tag == 'ResOtherZn':
            return 'other_residential'
        elif tag in ('Spc', 'ComZn'):
            return 'commercial'
        else:  # ThrmlZn or other
            return 'commercial'  # Default to commercial

    def _build_annotation(
        self,
        tag: str,
        zone_type: Optional[str],
        heights: Dict,
        parent_zg_name: Optional[str],
        zone_group_map: Dict[str, str],
        condg_type: Optional[str],
        dwelling_unit: Optional[Dict],
        oz_dhw_sys: Optional[str],
        oz_hvac_sys: Optional[str],
        iaq_config: Dict,
        vent_spc_func: Optional[str],
        daylight: Dict,
        space_function: Optional[str],
    ) -> Dict[str, Any]:
        """
        Build annotation dictionary with all CBECC-specific properties.

        This preserves all round-trip fidelity data and applies Title 24 defaults.
        """
        annotation = {
            'xml_tag': tag,
            'zone_type': zone_type,
        }

        # Add heights (both SI and original IP values)
        annotation.update(heights)

        # Add parent zone group
        if parent_zg_name:
            annotation['zone_group'] = parent_zg_name
            annotation['parent_zone_group_id'] = zone_group_map.get(parent_zg_name)

        # Add conditioning type
        if condg_type:
            annotation['conditioning_type'] = condg_type

        # Add dwelling unit
        if dwelling_unit:
            annotation['dwelling_unit'] = dwelling_unit

        # Add system references
        if oz_dhw_sys:
            annotation['oz_dhw_sys'] = oz_dhw_sys
        if oz_hvac_sys:
            annotation['oz_hvac_sys'] = oz_hvac_sys

        # Add IAQ configuration
        annotation.update(iaq_config)

        # Add ventilation space function
        if vent_spc_func:
            annotation['vent_spc_func'] = vent_spc_func

        # Add daylighting
        annotation.update(daylight)

        # Apply Title 24 space function defaults
        if space_function:
            self._apply_space_function_defaults(annotation, space_function)

        return annotation

    def _apply_space_function_defaults(self, annotation: Dict, space_function: str) -> None:
        """
        Apply Title 24/ASHRAE defaults for space function.

        Adds occupancy, equipment, and lighting power densities to annotation.
        """
        defaults = get_space_function_defaults(space_function)
        if not defaults:
            return

        # Occupancy density
        occ_density_si = get_occupancy_density_si(space_function)
        if occ_density_si is not None:
            annotation['occupancy_density_people_m2'] = occ_density_si
            annotation['occupancy_density_people_1000ft2'] = defaults.occupancy_people_per_1000_ft2
            annotation['occupancy_source'] = 'Title 24/ASHRAE defaults'

        # Equipment power density
        equip_density_si = get_equipment_density_si(space_function)
        if equip_density_si is not None:
            annotation['equipment_power_density_w_m2'] = equip_density_si
            annotation['equipment_power_density_w_ft2'] = defaults.equipment_power_density_w_ft2
            annotation['equipment_source'] = 'Title 24/ASHRAE defaults'

        # Lighting power density (fallback if no IntLtgSys)
        ltg_density_si = get_lighting_density_si(space_function)
        if ltg_density_si is not None:
            annotation['lighting_power_density_w_m2_default'] = ltg_density_si
            annotation['lighting_power_density_w_ft2_default'] = defaults.lighting_power_density_w_ft2
            annotation['lighting_density_source'] = 'Title 24/ASHRAE defaults (fallback)'

    def _calculate_area_from_polylp(self, element: ET.Element) -> Optional[float]:
        """
        Calculate floor area from PolyLp (polygon loop) using Shoelace formula.

        Used by CBECC SDDXML format when explicit area not provided.

        Returns:
            Area in ft² (CBECC units), or None if PolyLp not found
        """
        polylp = element.find('.//PolyLp')
        if polylp is None:
            return None

        # Extract coordinates from CartesianPt elements
        # In CBECC, each CartesianPt has 3 <Coord> siblings (X, Y, Z)
        points = []
        for pt in polylp.findall('CartesianPt'):
            coords = pt.findall('Coord')
            if len(coords) >= 2:
                x = self._to_float(coords[0].text)
                y = self._to_float(coords[1].text)
                if x is not None and y is not None:
                    points.append((x, y))

        if len(points) < 3:
            return None

        # Shoelace formula for polygon area
        area = 0.0
        n = len(points)
        for i in range(n):
            j = (i + 1) % n
            area += points[i][0] * points[j][1]
            area -= points[j][0] * points[i][1]

        return abs(area) / 2.0

    def get_name(self, element: ET.Element) -> str:
        """
        Extract name from CIBD22X element.

        CIBD22X format uses <n> child element for names (legacy format).
        Falls back to <Name> child, then id attribute.

        Args:
            element: XML element

        Returns:
            Name string, or empty string if not found
        """
        # Primary: <n> child element (CIBD22X legacy format)
        # Handle both with and without namespace
        for child in element:
            tag = self._local_tag(child.tag)
            if tag == 'n' and child.text:
                return child.text.strip()

        # Fallback: <Name> child
        for child in element:
            tag = self._local_tag(child.tag)
            if tag == 'Name' and child.text:
                return child.text.strip()

        # Last resort: id attribute
        return element.get('id', '')

    def _local_tag(self, tag: str) -> str:
        """
        Strip XML namespace from tag.

        Args:
            tag: Tag with possible namespace (e.g., "{http://...}ResZn")

        Returns:
            Tag without namespace (e.g., "ResZn")
        """
        return tag.split('}', 1)[-1] if '}' in tag else tag
