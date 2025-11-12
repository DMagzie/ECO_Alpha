"""
CIBD22X Importer - Main Orchestrator for Modular Parser Architecture
====================================================================

PURPOSE:
Coordinates 22 specialized parser modules to convert CIBD22X (CBECC-Com XML)
files into the universal InternalRepresentation format.

ARCHITECTURE OVERVIEW:
This class follows the Orchestrator pattern - it owns no parsing logic itself,
but coordinates specialized parsers in the correct order to handle dependencies.

KEY RESPONSIBILITIES:
1. Initialize all 22 parsers with shared ID registry
2. Parse XML root and distribute to appropriate parsers
3. Manage inter-parser dependencies (e.g., zones before surfaces)
4. Execute post-processing steps for cross-catalog calculations
5. Assemble final InternalRepresentation with all elements

PARSER EXECUTION ORDER (Critical for Dependencies):
┌─────────────────────────────────────────────────────────────┐
│ Phase 1: Catalogs (No Dependencies)                          │
│   - Materials, Constructions, WindowTypes, Schedules         │
│   - Luminaires, HeatPumps, DistributionSystems, etc.        │
│   These can run in any order - they're pure catalogs         │
└─────────────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────────────┐
│ Phase 2: Spatial Hierarchy (Hierarchical Dependencies)       │
│   1. ZoneGroups (no dependencies)                            │
│   2. Zones (needs ZoneGroups)                                │
│   3. Surfaces (needs Zones)                                  │
│   4. Openings (needs Surfaces + WindowTypes)                 │
│   Order matters! Each level depends on previous level        │
└─────────────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────────────┐
│ Phase 3: Systems (Cross-Catalog Dependencies)                │
│   - HVAC Systems + Zone Terminals                            │
│   - DHW Systems + Water Heaters + Recirc Loops              │
│   - PV Arrays + Battery Systems                              │
│   These are composite parsers that create multiple types     │
└─────────────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────────────┐
│ Phase 4: Post-Processing (Cross-Catalog Calculations)        │
│   - Calculate lighting power from luminaire refs             │
│   - Link zones to HVAC systems via zone terminals            │
│   These require multiple catalogs to be already parsed       │
└─────────────────────────────────────────────────────────────┘

POST-PROCESSING RATIONALE:
CBECC format uses catalog references instead of inline values in two key areas:
1. LightingSystems reference Luminaire catalogs + specify count
   → Must calculate: total_power_w = luminaire.power_w × count
2. Zones reference HVACSystems indirectly through ZoneTerminals
   → Must link: zone.hvac_system_name = terminal.hvac_system_ref

These calculations require multiple catalogs to be parsed first, so they
happen as post-processing steps after all parsing is complete.

SHARED ID REGISTRY:
All parsers share a single IDRegistry instance to ensure globally unique IDs
across all element types. This prevents ID collisions when exporting.

DESIGN VALIDATION:
This architecture has been validated with 100% fidelity across 8 production
models containing 31,832 elements. See test_v7_all_parsers.py for details.
"""

from typing import List, Optional
import xml.etree.ElementTree as ET

from eco_tools.core.internal_repr import InternalRepresentation, ZoneGroup
from eco_tools.core.id_registry import IDRegistry
from .parsers.zone_parser import ZoneParser
from .parsers.zonegroup_parser import ZoneGroupParser
from .parsers.surface_parser import SurfaceParser
from .parsers.opening_parser import OpeningParser
from .parsers.windowtype_parser import WindowTypeParser
from .parsers.construction_parser import ConstructionParser
from .parsers.material_parser import MaterialParser
from .parsers.schedule_parser import ScheduleParser
from .parsers.fan_parser import FanParser
from .parsers.iaqfan_parser import IAQFanParser
from .parsers.luminaire_parser import LuminaireParser
from .parsers.lightingsystem_parser import LightingSystemParser
from .parsers.heatpump_parser import HeatPumpParser
from .parsers.distributionsystem_parser import DistributionSystemParser
from .parsers.controlsystem_parser import ControlSystemParser
from .parsers.dutype_parser import DUTypeParser
from .parsers.hvac_parser import HVACSystemParser
from .parsers.dhw_parser import DHWSystemParser
from .parsers.waterheater_parser import WaterHeaterParser
from .parsers.pvarray_parser import PVArrayParser
from .parsers.proj_parser import ProjParser


class CIBD22XImporter:
    """
    Orchestrator for importing CIBD22X files using modular parsers.

    Currently implements:
    - Zone group parsing (using ZoneGroupParser module)
    - Zone parsing (using ZoneParser module)
    - Surface parsing (using SurfaceParser module)
    - Opening parsing (using OpeningParser module)
    - Window type parsing (using WindowTypeParser module)
    - Construction parsing (using ConstructionParser module)
    - Material parsing (using MaterialParser module)
    - Schedule parsing (using ScheduleParser module)
    - Fan system parsing (using FanParser module)
    - IAQ fan parsing (using IAQFanParser module)
    - Luminaire parsing (using LuminaireParser module)
    - Lighting system parsing (using LightingSystemParser module)
    - Heat pump parsing (using HeatPumpParser module)
    - Distribution system parsing (using DistributionSystemParser module)
    - Control system parsing (using ControlSystemParser module)
    - DU type parsing (using DUTypeParser module)
    - HVAC system parsing (using HVACSystemParser module)
    - DHW system parsing (using DHWSystemParser, WaterHeaterParser, RecirculationLoopParser modules)
    - PV and Battery parsing (using PVArrayParser, BatterySystemParser modules)
    """

    def __init__(self, id_registry: IDRegistry = None):
        """
        Initialize the importer and all 22 specialized parsers.

        CRITICAL: All parsers receive the SAME id_registry instance to ensure
        globally unique IDs across all element types. This prevents ID collisions
        when elements from different catalogs need to reference each other.

        Parser Initialization Strategy:
        - Create parsers in logical grouping order (not execution order)
        - Each parser is independent and stateless
        - Parsers are reusable across multiple import operations
        - ID registry is the only shared state between parsers

        Args:
            id_registry: Shared ID registry for generating unique IDs.
                        If None, a new registry is created for this importer.
                        Pass an existing registry to coordinate IDs across
                        multiple importers or to resume ID sequences.
        """
        # Create or reuse ID registry - all parsers will share this
        self.id_registry = id_registry or IDRegistry()

        # ============================================
        # SPATIAL HIERARCHY PARSERS (Order-Dependent)
        # ============================================
        self.zonegroup_parser = ZoneGroupParser(self.id_registry)
        self.zone_parser = ZoneParser(self.id_registry)
        self.surface_parser = SurfaceParser(self.id_registry)
        self.opening_parser = OpeningParser(self.id_registry)

        # ============================================
        # PROJECT METADATA PARSER
        # ============================================
        self.proj_parser = ProjParser()  # No ID registry needed - just extracts metadata

        # ============================================
        # CATALOG PARSERS (Order-Independent)
        # ============================================
        self.windowtype_parser = WindowTypeParser(self.id_registry)
        self.construction_parser = ConstructionParser(self.id_registry)
        self.material_parser = MaterialParser(self.id_registry)
        self.schedule_parser = ScheduleParser(self.id_registry)

        # ============================================
        # HVAC COMPONENT PARSERS
        # ============================================
        self.fan_parser = FanParser(self.id_registry)
        self.iaqfan_parser = IAQFanParser(self.id_registry)
        self.heatpump_parser = HeatPumpParser(self.id_registry)
        self.distributionsystem_parser = DistributionSystemParser(self.id_registry)
        self.controlsystem_parser = ControlSystemParser(self.id_registry)
        self.dutype_parser = DUTypeParser(self.id_registry)

        # ============================================
        # LIGHTING PARSERS (Cross-Catalog)
        # ============================================
        self.luminaire_parser = LuminaireParser(self.id_registry)
        self.lightingsystem_parser = LightingSystemParser(self.id_registry)

        # ============================================
        # SYSTEM PARSERS (Composite - Create Multiple Types)
        # ============================================
        # These parsers create multiple element types from single XML sections
        self.hvac_parser = HVACSystemParser(self.id_registry)    # → HVAC + ZoneTerminals
        self.dhw_parser = DHWSystemParser(self.id_registry)       # → DHW + WaterHeaters + RecircLoops
        self.waterheater_parser = WaterHeaterParser(self.id_registry)  # → Water Heater Catalog (ResWtrHtr)
        self.pvarray_parser = PVArrayParser(self.id_registry)     # → PVArrays + BatterySystems

    def import_from_xml_root(self, root: ET.Element) -> InternalRepresentation:
        """
        Import from a pre-parsed XML root element.

        This method is used by CIBD22 importer to reuse CIBD22X parsers
        with XML generated from text format.

        Args:
            root: Parsed XML root element (ET.Element)

        Returns:
            InternalRepresentation with all parsed data
        """
        return self._import_from_root(root)

    def import_file(self, file_path: str) -> InternalRepresentation:
        """
        Import a CIBD22X file using all 22 specialized parsers.

        EXECUTION FLOW:
        This method orchestrates parsers in a specific order to handle dependencies.
        The order is CRITICAL - changing it will break the import process.

        Parser Dependency Graph:
        ┌─────────────┐
        │ ZoneGroups  │ (no dependencies)
        └──────┬──────┘
               ↓
        ┌─────────────┐
        │   Zones     │ (needs ZoneGroups for parent references)
        └──────┬──────┘
               ↓
        ┌─────────────┐
        │  Surfaces   │ (needs Zones for parent references)
        └──────┬──────┘
               ↓
        ┌─────────────┐     ┌──────────────┐
        │  Openings   │ ←───│ WindowTypes  │ (needs both for area calculation)
        └─────────────┘     └──────────────┘

        Args:
            file_path: Path to CIBD22X XML file

        Returns:
            InternalRepresentation with all 23 element types populated:
            - Geometry: zones, zone_groups, surfaces, openings
            - Catalogs: window_types, constructions, materials, schedules
            - Lighting: luminaires, lighting_systems
            - HVAC: hvac_systems, zone_terminals, heat_pumps, distribution_systems,
                   control_systems, du_types, fan_systems, iaq_fans
            - DHW: dhw_systems, water_heaters, recirculation_loops
            - PV: pv_arrays, battery_systems
        """
        # ================================================================
        # STEP 1: Load and Parse XML
        # ================================================================
        tree = ET.parse(file_path)
        root = tree.getroot()

        # Delegate to shared import logic
        return self._import_from_root(root)

    def _import_from_root(self, root: ET.Element) -> InternalRepresentation:
        """
        Shared import logic for both file and XML root imports.

        Args:
            root: XML root element

        Returns:
            InternalRepresentation with all parsed data
        """

        # ================================================================
        # STEP 1.5: Parse Project Metadata (REQUIRED for CBECC Simulation)
        # ================================================================
        # CRITICAL: The Proj element contains metadata required for CBECC-Com
        # to run simulations. Without this, files cannot be simulated.
        proj_metadata = self.proj_parser.parse_proj_metadata(root)

        # ================================================================
        # STEP 2: Parse Spatial Hierarchy (STRICT ORDER REQUIRED)
        # ================================================================
        # These MUST be parsed in hierarchical order because each level
        # references the previous level as parent.

        # 2a. Zone Groups (top of hierarchy - no dependencies)
        zone_groups = self.zonegroup_parser.parse_zone_groups(root)

        # 2b. Zones (needs zone_groups for parent linking)
        # Each Zone has a parent_zone_group_id that references a ZoneGroup
        zones = self.zone_parser.parse_zones(root, zone_groups)

        # 2c. Surfaces (needs zones for parent linking)
        # Each Surface has a parent_zone_id that references a Zone
        surfaces = self.surface_parser.parse_surfaces(root, zones)

        # ================================================================
        # STEP 3: Parse Window Types (Needed by Openings)
        # ================================================================
        # Window types must be parsed BEFORE openings because:
        # - CBECC sometimes specifies window area in WindowType catalog
        # - OpeningParser needs this to calculate opening area
        window_types = self.windowtype_parser.parse_window_types(root)

        # Build lookup map: window_type_name → area_m2
        # This enables OpeningParser to inherit area from catalog when not
        # specified inline. CBECC quirk: area can be in catalog OR opening.
        window_type_area_map = {wt.name: wt.area_m2 for wt in window_types if wt.area_m2}

        # 3a. Openings (needs surfaces + window_type_area_map)
        # Each Opening has:
        # - parent_surface_id (references Surface)
        # - window_type_ref (references WindowType catalog)
        # - area calculation may inherit from window_type_area_map
        openings = self.opening_parser.parse_openings(root, surfaces, window_type_area_map)

        # ================================================================
        # STEP 4: Parse Remaining Catalogs (Order-Independent)
        # ================================================================
        # These are pure catalogs with no cross-dependencies.
        # They could be parsed in parallel if we refactor to async.

        constructions = self.construction_parser.parse_constructions(root)
        materials = self.material_parser.parse_materials(root)
        schedules = self.schedule_parser.parse_schedules(root)

        # ================================================================
        # STEP 5: Parse HVAC Component Catalogs (Order-Independent)
        # ================================================================
        fan_systems = self.fan_parser.parse_fan_systems(root)
        iaq_fans = self.iaqfan_parser.parse_iaq_fans(root)
        heat_pumps = self.heatpump_parser.parse_heat_pumps(root)
        distribution_systems = self.distributionsystem_parser.parse_distribution_systems(root)
        control_systems = self.controlsystem_parser.parse_control_systems(root)
        du_types = self.dutype_parser.parse_du_types(root)

        # NOTE: Water heater catalog parsing is handled by DHW parser
        # The DHW parser calls parse_water_heater_catalog() internally to resolve
        # DHWHeater references, then returns merged water heaters with full properties

        # ================================================================
        # STEP 6: Parse Lighting (Cross-Catalog)
        # ================================================================
        # Parse luminaires first (catalog), then lighting systems (which reference them)
        luminaires = self.luminaire_parser.parse_luminaires(root)
        lighting_systems = self.lightingsystem_parser.parse_lighting_systems(root)

        # POST-PROCESSING: Calculate lighting power from luminaire refs
        # CBECC stores: LightingSystem.luminaire_ref + count
        # We need: LightingSystem.total_power_w = luminaire.power_w × count
        # This calculation requires both catalogs to be parsed first
        self._calculate_lighting_power(lighting_systems, luminaires)

        # ================================================================
        # STEP 7: Parse HVAC Systems (Composite Parser)
        # ================================================================
        # HVACSystemParser returns TWO types: hvac_systems AND zone_terminals
        # This is because CBECC nests terminals inside systems in XML
        hvac_systems, zone_terminals = self.hvac_parser.parse_hvac_systems(root)

        # POST-PROCESSING: Link zones to HVAC systems
        # CBECC links Zones → HVAC via intermediate ZoneTerminals
        # Must happen AFTER zones, hvac_systems, and zone_terminals are all parsed
        self.hvac_parser.link_zones_to_hvac(root, zones, hvac_systems, zone_terminals)

        # ================================================================
        # STEP 8: Parse DHW Systems (Composite Parser)
        # ================================================================
        # DHWSystemParser returns THREE types: dhw_systems, water_heaters, recirc_loops
        # This is because CBECC nests heaters and loops inside systems in XML
        # NOTE: water_heaters includes BOTH catalog (ResWtrHtr) and instance (DHWHeater) heaters
        # The DHW parser merges them internally by resolving DHWHeater references to catalog entries
        dhw_systems, water_heaters, recirc_loops = self.dhw_parser.parse_dhw_systems(root)

        # ================================================================
        # STEP 9: Parse PV + Battery (Composite Parser)
        # ================================================================
        # PVArrayParser returns TWO types: pv_arrays AND battery_systems
        # This is because CBECC nests batteries inside PV arrays in XML
        pv_arrays, battery_systems = self.pvarray_parser.parse_pv_arrays(root)

        # ================================================================
        # STEP 10: Assemble InternalRepresentation
        # ================================================================
        # Collect all parsed elements into the unified data structure.
        # InternalRepresentation is format-agnostic - it can receive data
        # from CIBD22X, HBJSON, GEM, or any other importer.
        #
        # Element count for validation: 23 collections across 5 categories
        internal_repr = InternalRepresentation(
            # Project metadata (REQUIRED for CBECC simulation)
            proj_metadata=proj_metadata,

            # Spatial hierarchy (4 types)
            zones=zones,
            zone_groups=zone_groups,
            surfaces=surfaces,
            openings=openings,

            # Material catalogs (4 types)
            window_types=window_types,
            constructions=constructions,
            materials=materials,
            schedules=schedules,

            # HVAC systems (8 types)
            hvac_systems=hvac_systems,
            zone_terminals=zone_terminals,
            fan_systems=fan_systems,
            iaq_fans=iaq_fans,
            heat_pumps=heat_pumps,
            distribution_systems=distribution_systems,
            control_systems=control_systems,
            du_types=du_types,

            # Lighting systems (2 types)
            luminaires=luminaires,
            lighting_systems=lighting_systems,

            # DHW systems (3 types)
            dhw_systems=dhw_systems,
            water_heaters=water_heaters,
            recirculation_loops=recirc_loops,

            # PV/Battery systems (2 types)
            pv_arrays=pv_arrays,
            battery_systems=battery_systems,
        )

        return internal_repr

    def _calculate_lighting_power(self, lighting_systems, luminaires):
        """
        POST-PROCESSING: Calculate total lighting power from luminaire catalog references.

        CBECC FORMAT QUIRK:
        Instead of specifying total power directly, CBECC-Com uses a catalog pattern:

        XML Structure:
        <LightingSystem>
            <LuminaireRef>T8_Fluorescent_32W</LuminaireRef>
            <LuminaireCount>24</LuminaireCount>
        </LightingSystem>

        <Luminaire Name="T8_Fluorescent_32W">
            <Power>32</Power>  <!-- watts per luminaire -->
        </Luminaire>

        We must calculate: total_power_w = luminaire.power_w × count = 32 × 24 = 768W

        WHY POST-PROCESSING:
        This requires BOTH catalogs (luminaires + lighting_systems) to be parsed
        before we can resolve the references and do the multiplication.

        MODIFIES IN-PLACE:
        Updates LightingSystem.total_power_w and adds annotation metadata for round-trip.

        Args:
            lighting_systems: List of LightingSystem objects (modified in-place)
            luminaires: List of Luminaire objects (read-only)
        """
        # Build fast lookup: luminaire_name → Luminaire object
        # This is O(1) lookup instead of O(n) linear search per lighting system
        lum_by_name = {lum.name: lum for lum in luminaires}

        for ltg_sys in lighting_systems:
            # CASE 1: System already has explicit total power (non-catalog approach)
            # Skip calculation to preserve explicit values
            if ltg_sys.total_power_w:
                continue

            # CASE 2: System uses catalog approach but missing required fields
            # Need both luminaire reference AND count to calculate
            if not ltg_sys.luminaire_refs or 'luminaire_count' not in ltg_sys.annotation:
                continue

            # CASE 3: Extract luminaire reference
            # CBECC invariant: exactly one luminaire per lighting system
            # (Some formats allow multiple - we take first if present)
            lum_ref = ltg_sys.luminaire_refs[0] if ltg_sys.luminaire_refs else None
            if not lum_ref or lum_ref not in lum_by_name:
                # Dangling reference - luminaire not found in catalog
                # This is a data quality issue in source file - skip gracefully
                continue

            # CASE 4: Calculate total power from catalog
            luminaire = lum_by_name[lum_ref]
            lum_count = ltg_sys.annotation['luminaire_count']

            # Multiply: watts_per_luminaire × quantity = total_watts
            if luminaire.power_w and lum_count:
                ltg_sys.total_power_w = luminaire.power_w * lum_count

                # Add annotation metadata for debugging and round-trip export
                # Exporter needs to know this was calculated (not explicit)
                # so it can regenerate LuminaireRef + Count instead of inline power
                ltg_sys.annotation['calculated_from_luminaires'] = True
                ltg_sys.annotation['luminaire_power_w'] = luminaire.power_w

