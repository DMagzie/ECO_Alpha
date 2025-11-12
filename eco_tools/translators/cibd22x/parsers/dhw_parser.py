"""
DHWSystem Parser - Composite Domestic Hot Water System Parser
============================================================

PURPOSE:
Extracts domestic hot water (DHW) system configurations from CIBD22X XML.
This is a COMPOSITE PARSER that creates THREE element types from single XML sections:
1. DHWSystem (the system itself)
2. WaterHeater (nested equipment - can be multiple per system)
3. RecirculationLoop (nested piping loops - can be multiple per system)

DHW SYSTEM TYPES IN CBECC:
CBECC supports multiple DHW system contexts:

1. ResDHWSys (Residential DHW System)
   - Individual dwelling unit systems (tankless, tank, heat pump)
   - Central multifamily systems serving multiple units
   - Service water heating for residential buildings

2. ComDHWSys (Commercial DHW System)
   - Commercial building service water heating
   - Restaurants, hotels, hospitals, etc.
   - Typically larger capacities than residential

3. DHWSys (Generic DHW System)
   - Generic format for either context
   - Used in some CBECC variants

COMPOSITE PARSER PATTERN:
Unlike simple parsers that create ONE element type from ONE XML tag,
this parser creates MULTIPLE element types from a SINGLE XML section:

<ResDHWSys>                        → DHWSystem
  <DHWHeater>...</DHWHeater>       → WaterHeater (can be array with counts)
  <DHWHeater>...</DHWHeater>       → WaterHeater
  <RecircLoop>...</RecircLoop>     → RecirculationLoop
</ResDHWSys>

This requires DELEGATING to sub-parsers:
- WaterHeaterParser: Extracts water heater equipment
- RecirculationLoopParser: Extracts recirculation piping loops

CENTRAL vs INDIVIDUAL SYSTEMS:
- Central: Serves multiple dwelling units or zones (one system, many endpoints)
- Individual: Serves single dwelling unit or zone (one-to-one)

Classification affects:
- Equipment sizing (central systems are larger)
- Distribution losses (central systems have longer pipe runs)
- Code compliance calculations (different standards)

WATER HEATER ARRAYS:
CBECC allows specifying multiple identical water heaters with counts:
<DHWHeater>Tank_50gal</DHWHeater>  Count=3  → 3 identical 50-gal tanks

This enables compact representation of large installations
(e.g., hotel with 10 identical water heaters).

RECIRCULATION LOOPS:
Hot water recirculation systems maintain hot water at fixtures to reduce
wait time. They add distribution losses but improve user convenience.

Loop types:
- Demand-controlled (pump runs only when needed)
- Continuous (pump runs 24/7)
- Timer-controlled (pump runs on schedule)

KEY RESPONSIBILITIES:
1. Parse DHW system classification (residential vs commercial, central vs individual)
2. Delegate to WaterHeaterParser to extract nested water heaters
3. Delegate to RecirculationLoopParser to extract nested recirc loops
4. Parse distribution properties (pipe insulation, distribution type)
5. Track service area (floor area served, dwelling units served)
6. Extract central heat pump water heater (CHPWH) properties
7. Return THREE lists: (DHWSystems, WaterHeaters, RecirculationLoops)

DESIGN PATTERN:
This is a "Composite Parser" that uses the Composition pattern to delegate
sub-element parsing to specialized parsers. It coordinates three parsers
to extract a complete DHW system hierarchy from nested XML.
"""

from typing import List, Tuple, Optional
import xml.etree.ElementTree as ET
import logging

from eco_tools.core.internal_repr import DHWSystem, WaterHeater, RecirculationLoop
from eco_tools.core.id_registry import IDRegistry
from .base_parser import BaseParser
from .waterheater_parser import WaterHeaterParser
from .recirculationloop_parser import RecirculationLoopParser

# Get module logger
logger = logging.getLogger('eco_tools.parsers')


class DHWSystemParser(BaseParser):
    """Parser for CIBD22X DHW system elements"""

    DHW_SYSTEM_TAGS = [
        'ResDHWSys',   # Residential DHW systems
        'ComDHWSys',   # Commercial DHW systems
        'DHWSys',      # Generic DHW systems
    ]

    def __init__(self, id_registry: IDRegistry):
        """
        Initialize the DHW system parser with sub-parsers.

        COMPOSITION PATTERN:
        This parser owns and coordinates two sub-parsers:
        - WaterHeaterParser: Extracts nested water heater equipment
        - RecirculationLoopParser: Extracts nested piping loops

        All three parsers share the SAME id_registry to ensure globally
        unique IDs across DHWSystems, WaterHeaters, and RecirculationLoops.

        Args:
            id_registry: Shared ID registry for unique ID generation
        """
        super().__init__()
        self.id_registry = id_registry

        # Sub-parser for water heater equipment (nested in DHW systems)
        self.waterheater_parser = WaterHeaterParser(id_registry)

        # Sub-parser for recirculation loops (nested in DHW systems)
        self.recirculationloop_parser = RecirculationLoopParser(id_registry)

    def parse_dhw_systems(self, root: ET.Element) -> Tuple[List[DHWSystem], List[WaterHeater], List[RecirculationLoop]]:
        """
        Parse all DHW systems and their nested components - COMPOSITE PARSER.

        COMPOSITE PARSING FLOW:
        For each <ResDHWSys>, <ComDHWSys>, or <DHWSys> element:
        1. Parse DHW system properties (central/individual, distribution, etc.)
        2. DELEGATE to WaterHeaterParser to extract nested <DHWHeater> elements
        3. DELEGATE to RecirculationLoopParser to extract nested <RecircLoop> elements
        4. Link water heaters and recirc loops to parent DHW system
        5. Accumulate all three element types into separate lists
        6. Return THREE lists: (systems, water_heaters, recirc_loops)

        WHY RETURN THREE LISTS:
        The InternalRepresentation stores these as separate top-level collections:
        - internal_repr.dhw_systems
        - internal_repr.water_heaters
        - internal_repr.recirculation_loops

        This flat structure (vs nested hierarchy) simplifies:
        - Cross-references between elements
        - Export logic (each type has its own exporter)
        - Querying and filtering

        ELEMENT RELATIONSHIPS:
        - DHWSystem.water_heaters = [heater_name1, heater_name2, ...]
        - DHWSystem.recirculation_loops = [loop_id1, loop_id2, ...]
        - WaterHeater.parent_dhw_system_id = dhw_system_id
        - RecirculationLoop.parent_dhw_system_id = dhw_system_id

        Args:
            root: Root XML element

        Returns:
            Tuple of three lists:
            - List[DHWSystem]: All DHW system objects
            - List[WaterHeater]: All water heater objects (from all systems)
            - List[RecirculationLoop]: All recirc loop objects (from all systems)
        """
        # ================================================================
        # Initialize Accumulator Lists
        # ================================================================
        # Collect elements from all DHW systems into three separate lists
        systems = []              # DHWSystem objects
        all_water_heaters = []    # WaterHeater objects from ALL systems
        all_recirc_loops = []     # RecirculationLoop objects from ALL systems

        # ================================================================
        # Iterate Through All DHW System Types
        # ================================================================
        # CBECC has 3 DHW system tags, all parsed identically
        # Combine all findall results into single iterator
        for sys_elem in (root.findall('.//ResDHWSys') +
                         root.findall('.//ComDHWSys') +
                         root.findall('.//DHWSys')):

            # Extract system name (required for identification)
            name = self._get_name(sys_elem)
            if not name:
                continue  # Skip systems without names

            # Generate unique ID for this DHW system
            sys_id = self.id_registry.generate_id('D', name, '', 'CIBD22X')

            # ================================================================
            # STEP 1: Build Annotation Dictionary
            # ================================================================
            # Store original XML tag for round-trip export
            annotation = {'xml_tag': self._local_tag(sys_elem.tag)}

            # ================================================================
            # STEP 2: Classify Central vs Individual System
            # ================================================================
            # CENTRAL SYSTEM: Serves multiple dwelling units or zones
            # - Typically larger equipment
            # - Longer distribution piping (more heat loss)
            # - Different code compliance rules

            # Detect central system from CentralDHWType property or name
            central_dhw_type = self.get_property(sys_elem, 'CentralDHWType')
            is_central = central_dhw_type is not None or 'Central' in name

            # Classify type of central system (if central)
            central_system_type = None
            if is_central:
                # Multifamily central systems (apartment buildings, condos)
                if 'Multifamily' in str(central_dhw_type) or 'MF' in name:
                    central_system_type = 'Multifamily'
                # Commercial central systems (hotels, hospitals, etc.)
                elif 'Commercial' in str(central_dhw_type) or self._local_tag(sys_elem.tag) == 'ComDHWSys':
                    central_system_type = 'Commercial'
                # Generic residential central (fallback)
                else:
                    central_system_type = 'Residential'

            # ================================================================
            # STEP 3: DELEGATE to WaterHeaterParser
            # ================================================================
            # Extract nested <DHWHeater> elements and their counts
            # Returns: (List[WaterHeater], List[int]) where counts[i] = quantity of heater[i]
            #
            # WATER HEATER ARRAY PATTERN:
            # CBECC allows: <DHWHeater>Tank_50gal</DHWHeater> with Count=3
            # Meaning: 3 identical 50-gallon tanks in this system
            water_heaters, water_heater_counts = self.waterheater_parser.parse_water_heater_array(sys_elem, sys_id)

            # CRITICAL ROUND-TRIP DECISION:
            # DHWSystem.water_heaters stores NAMES (not IDs) because CBECC references
            # water heaters by name in XML. Using names enables perfect round-trip.
            water_heater_names = [wh.name for wh in water_heaters]

            # Accumulate water heaters into global list
            all_water_heaters.extend(water_heaters)

            # ================================================================
            # STEP 4: DELEGATE to RecirculationLoopParser
            # ================================================================
            # Extract nested <RecircLoop> elements
            # Returns: List[RecirculationLoop]
            recirc_loops = self.recirculationloop_parser.parse_recirculation_loops(sys_elem, sys_id)

            # Extract loop IDs for DHWSystem reference list
            recirc_loop_ids = [rl.id for rl in recirc_loops]

            # Accumulate recirc loops into global list
            all_recirc_loops.extend(recirc_loops)

            # Distribution properties
            distribution_type = self.get_property(sys_elem, 'DHWDistType')
            if not distribution_type:
                if len(recirc_loops) > 0:
                    distribution_type = 'Recirculating'
                else:
                    distribution_type = self.get_property(sys_elem, 'DistType') or 'Standard'

            pipe_insulation_level = self.get_property(sys_elem, 'DHWPipeInsulLevel')

            # Service tracking
            floor_area_served_ft2 = self._to_float(self.get_property(sys_elem, 'FloorAreaServed'))
            floor_area_served = (floor_area_served_ft2 * 0.092903) if floor_area_served_ft2 else None

            dwelling_units_served = self._to_int(self.get_property(sys_elem, 'DwellingUnitsServed'))

            # Legacy properties for backward compatibility
            central_recirc_type = self.get_property(sys_elem, 'CentralRecircType')
            recirc_type = self.get_property(sys_elem, 'RecircType') or central_recirc_type

            # Collect annotation attributes
            annotation_attrs = [
                'CHPWHSysDescrip', 'CHPWHCompType', 'CHPWHNumComp',
                'CHPWHTankCount', 'CHPWHTankLoc', 'CHPWHSrcAirLoc',
                'CHPWHLoopTankConfig', 'CHPWHCompCOP', 'CHPWHTankVol',
                'CHPWHCompCap', 'CHPWHRecoveryEff',
                'DHWHeaterFuel', 'DHWHeaterType', 'DHWHeaterEF',
                'DHWStorageVol', 'DHWStorageTankUA', 'DHWPipeInsulType',
                'DHWPumpPower'
            ]

            for attr in annotation_attrs:
                value = self.get_property(sys_elem, attr)
                if value:
                    annotation[attr] = value

            # Add central type info if present
            if central_dhw_type:
                annotation['CentralDHWType'] = central_dhw_type
            if central_recirc_type:
                annotation['CentralRecircType'] = central_recirc_type

            # Store water heater references with indices for export
            # These need to be exported as <DHWHeater index="0">Name</DHWHeater>
            if water_heaters:
                dhw_heater_refs = []
                for i, (wh, count) in enumerate(zip(water_heaters, water_heater_counts)):
                    dhw_heater_refs.append({
                        'name': wh.name,
                        'index': i,
                        'count': count
                    })
                annotation['dhw_heater_refs'] = dhw_heater_refs

            # Determine system type from available data
            system_type = self.get_property(sys_elem, 'SystemType')
            if not system_type or system_type == 'unknown':
                if central_dhw_type:
                    system_type = central_dhw_type
                elif 'CHPWHCompType' in annotation:
                    system_type = 'Central Heat Pump Water Heater'
                elif water_heaters:
                    system_type = water_heaters[0].heater_type
                else:
                    system_type = 'unknown'

            system = DHWSystem(
                id=sys_id,
                name=name,
                system_type=system_type,
                is_central=is_central,
                central_system_type=central_system_type,
                water_heaters=water_heater_names,  # Use original names for round-trip
                water_heater_counts=water_heater_counts,
                recirculation_loops=recirc_loop_ids,
                distribution_type=distribution_type,
                pipe_insulation_level=pipe_insulation_level,
                floor_area_served=floor_area_served,
                dwelling_units_served=dwelling_units_served,
                recirc_type=recirc_type,
                annotation=annotation
            )

            systems.append(system)

        # Parse ResWtrHtr catalog (water heater equipment library)
        # These are SEPARATE from DHWHeater references in ResDHWSys
        # DHWHeater text content references these catalog entries by name
        catalog_heaters = self.waterheater_parser.parse_water_heater_catalog(root)

        # Merge: REPLACE placeholder heaters from DHWHeater refs with full catalog entries
        # Build map of catalog heaters by name
        catalog_map = {wh.name: wh for wh in catalog_heaters}

        # Replace placeholders with catalog versions (which have complete properties)
        merged_heaters = []
        for wh in all_water_heaters:
            if wh.name in catalog_map:
                # Use catalog version with full properties instead of placeholder
                merged_heaters.append(catalog_map[wh.name])
                del catalog_map[wh.name]  # Remove so we don't add duplicate
            else:
                # Keep original if no catalog entry found
                merged_heaters.append(wh)

        # Add any catalog heaters that weren't referenced in DHW systems
        merged_heaters.extend(catalog_map.values())

        all_water_heaters = merged_heaters

        logger.info(f"Parsed {len(systems)} DHW systems, {len(all_water_heaters)} water heaters, and {len(all_recirc_loops)} recirculation loops")
        return systems, all_water_heaters, all_recirc_loops

    def _get_name(self, element: ET.Element) -> Optional[str]:
        """Extract name from element."""
        name_elem = element.find('.//n')
        if name_elem is not None and name_elem.text:
            return name_elem.text.strip()
        name_elem = element.find('.//Name')
        if name_elem is not None and name_elem.text:
            return name_elem.text.strip()
        name = element.get('id')
        return name if name else None

    def _local_tag(self, tag: str) -> str:
        """Strip namespace from tag."""
        if '}' in tag:
            return tag.split('}', 1)[1]
        return tag
