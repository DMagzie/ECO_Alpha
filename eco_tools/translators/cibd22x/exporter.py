"""
CIBD22X Exporter - Main Orchestrator for Modular Exporter Architecture
======================================================================

PURPOSE:
Coordinates 10 specialized exporter modules to convert InternalRepresentation
back to CIBD22X (CBECC-Com XML) format.

ARCHITECTURE OVERVIEW:
This class follows the Orchestrator pattern - it owns no export logic itself,
but coordinates specialized exporters in the correct order for proper XML structure.

KEY RESPONSIBILITIES:
1. Initialize all 10 exporters
2. Create XML root structure (<Project>, <Building>)
3. Call exporters in optimal order for XML generation
4. Assemble final XML ElementTree with proper namespace
5. Provide serialization method for writing to file

EXPORTER EXECUTION ORDER (Optimized for XML Structure):
┌─────────────────────────────────────────────────────────────┐
│ Phase 1: Catalogs (Referenced by Other Elements)             │
│   - Materials, Constructions, WindowTypes                    │
│   - Schedules (three-tier: SchDay → SchWeek → Sch)          │
│   These should be exported first so they exist when          │
│   referenced by spatial/system elements                      │
└─────────────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────────────┐
│ Phase 2: Spatial Hierarchy (Nested XML Structure)            │
│   - ZoneGroups → Zones → Surfaces → Openings                │
│   ZoneExporter handles the entire nested hierarchy           │
│   Order matters for proper XML nesting!                      │
└─────────────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────────────┐
│ Phase 3: Systems (Composite Elements)                        │
│   - HVAC Systems + Zone Terminals                            │
│   - DHW Systems + Water Heaters + Recirc Loops              │
│   - PV Arrays + Battery Systems                              │
│   These are composite exporters that create nested elements  │
└─────────────────────────────────────────────────────────────┘

SYMMETRY WITH IMPORTER:
The exporter mirrors the importer architecture but in reverse:
  CIBD22X XML → InternalRepresentation (Importer)
  InternalRepresentation → CIBD22X XML (Exporter)

UNIT CONVERSIONS:
Exporters reverse the importer's unit conversions (SI → Imperial):
- Area: m² → ft²
- Volume: m³ → ft³  
- R-value: m²·K/W → ft²·°F·h/Btu
- U-factor: W/(m²·K) → Btu/(h·ft²·°F)
- Length: m → ft
- Thickness: m → in
- Density: kg/m³ → lb/ft³
- Specific Heat: J/(kg·K) → Btu/(lb·°F)

ANNOTATION RESTORATION:
Exporters rely on annotations stored during import:
- 'xml_tag': Original XML tag name (Mat vs ResMat, ResZn vs ComZn)
- 'original_*': Original IP unit values for perfect round-trip
- Format-specific properties not in universal InternalRepresentation

ROUND-TRIP FIDELITY:
The goal is perfect round-trip: Import → Export → Import = Identical
This requires:
1. Symmetric unit conversions (SI ↔ Imperial)
2. Annotation restoration (format-specific properties)
3. Proper XML structure (element ordering, nesting)
"""

from typing import Optional
import xml.etree.ElementTree as ET
import logging

from eco_tools.core.internal_repr import InternalRepresentation
from .exporters.material_exporter import MaterialExporter
from .exporters.construction_exporter import ConstructionExporter
from .exporters.windowtype_exporter import WindowTypeExporter
from .exporters.schedule_exporter import ScheduleExporter
from .exporters.zone_exporter import ZoneExporter
from .exporters.hvac_exporter import HVACExporter
from .exporters.dhw_exporter import DHWExporter
from .exporters.pv_exporter import PVExporter
from .exporters.proj_exporter import ProjExporter
from .exporters.dutype_exporter import DUTypeExporter
from .exporters.heatpump_catalog_exporter import HeatPumpCatalogExporter
from .exporters.fansystem_catalog_exporter import FanSystemCatalogExporter
from .exporters.distributionsystem_catalog_exporter import DistributionSystemCatalogExporter
from .exporters.iaqfan_catalog_exporter import IAQFanCatalogExporter
from .exporters.controlsystem_catalog_exporter import ControlSystemCatalogExporter
from .exporters.waterheater_catalog_exporter import WaterHeaterCatalogExporter

# Configure logger
logger = logging.getLogger('eco_tools.exporters')


class CIBD22XExporter:
    """
    Orchestrator for exporting InternalRepresentation to CIBD22X files.
    
    Currently implements:
    - Material export (Mat, ResMat catalog)
    - Construction export (construction assemblies)
    - Window type export (fenestration catalogs)
    - Schedule export (three-tier: SchDay → SchWeek → Sch)
    - Spatial hierarchy export (ZoneGroups → Zones → Surfaces → Openings)
    - HVAC system export (systems + zone terminals)
    - DHW system export (systems + water heaters + recirc loops)
    - PV system export (arrays + battery systems)
    """
    
    def __init__(self):
        """
        Initialize the exporter and all 10 specialized exporters.
        
        DESIGN PHILOSOPHY:
        - Each exporter is independent and stateless
        - Exporters are reusable across multiple export operations
        - No shared state between exporters (unlike importer's ID registry)
        - Exporters rely on annotations stored in InternalRepresentation
        
        Exporter Initialization Strategy:
        - Create exporters in logical grouping order (not execution order)
        - Each exporter handles one aspect of the export process
        - Exporters use composition (e.g., ZoneExporter uses SurfaceExporter)
        """
        
        # ============================================
        # PROJECT METADATA EXPORTER
        # ============================================
        self.proj_exporter = ProjExporter()

        # ============================================
        # CATALOG EXPORTERS (Order-Independent)
        # ============================================
        self.material_exporter = MaterialExporter()
        self.construction_exporter = ConstructionExporter()
        self.windowtype_exporter = WindowTypeExporter()
        self.schedule_exporter = ScheduleExporter()
        self.dutype_exporter = DUTypeExporter()

        # HVAC Equipment Catalogs (referenced by dwelling unit types)
        self.heatpump_catalog_exporter = HeatPumpCatalogExporter()
        self.fansystem_catalog_exporter = FanSystemCatalogExporter()
        self.distributionsystem_catalog_exporter = DistributionSystemCatalogExporter()
        self.iaqfan_catalog_exporter = IAQFanCatalogExporter()
        self.controlsystem_catalog_exporter = ControlSystemCatalogExporter()
        self.waterheater_catalog_exporter = WaterHeaterCatalogExporter()
        
        # ============================================
        # SPATIAL HIERARCHY EXPORTER (Nested)
        # ============================================
        # ZoneExporter handles entire hierarchy through composition:
        # ZoneExporter → SurfaceExporter → OpeningExporter
        self.zone_exporter = ZoneExporter()
        
        # ============================================
        # SYSTEM EXPORTERS (Composite)
        # ============================================
        # These exporters handle multiple element types
        self.hvac_exporter = HVACExporter()   # → HVAC + ZoneTerminals
        self.dhw_exporter = DHWExporter()     # → DHW + WaterHeaters + RecircLoops
        self.pv_exporter = PVExporter()       # → PVArrays + BatterySystems
    
    def export_to_element(self, internal: InternalRepresentation) -> ET.Element:
        """
        Export InternalRepresentation to CIBD22X XML ElementTree.
        
        EXECUTION FLOW:
        This method orchestrates exporters in a specific order to build proper XML structure.
        The order ensures referenced elements exist before they are referenced.
        
        XML Structure Created:
        <CBECC-Com xmlns="http://www.lmonte.com/CBECC22">
          <Project>
            <Building>
              <!-- Phase 1: Catalogs -->
              <Mat>...</Mat>
              <ResMat>...</ResMat>
              <Construction>...</Construction>
              <WindowType>...</WindowType>
              <SchDay>...</SchDay>
              <SchWeek>...</SchWeek>
              <Sch>...</Sch>
              
              <!-- Phase 2: Spatial Hierarchy -->
              <ResZnGrp>
                <ResZn>
                  <ResExtWall>
                    <Win>...</Win>
                  </ResExtWall>
                </ResZn>
              </ResZnGrp>
              
              <!-- Phase 3: Systems -->
              <ResHVACSys>...</ResHVACSys>
              <ResDHWSys>...</ResDHWSys>
              <ResPVSys>...</ResPVSys>
            </Building>
          </Project>
        </CBECC-Com>
        
        Args:
            internal: InternalRepresentation with all element types populated
        
        Returns:
            XML Element tree root (typically <CBECC-Com> or <Building>)
        """
        logger.info("Starting CIBD22X export...")
        
        # ================================================================
        # STEP 1: Create XML Root Structure
        # ================================================================
        # CBECC-Com CIBD22X files use SDDXML as root element
        # All elements (Proj, catalogs, zones) are direct children of root
        # This is DIFFERENT from the CBECC-Com namespace structure

        # Create root with namespace
        root = ET.Element('SDDXML')
        root.set('xmlns', 'http://www.lmonte.com/CBECC22')

        # ================================================================
        # STEP 1.2: Add RulesetFilename (REQUIRED - Must be FIRST element)
        # ================================================================
        # CRITICAL: RulesetFilename tells CBECC which Title 24 library to use
        # Without this, CBECC GUI will show blank - it doesn't know which rules to load
        ruleset_elem = ET.SubElement(root, 'RulesetFilename')
        ruleset_elem.set('file', 'T24N_2022.bin')
        logger.info("Added RulesetFilename: T24N_2022.bin")

        # ================================================================
        # STEP 1.5: Export Project Metadata (REQUIRED for CBECC Simulation)
        # ================================================================
        # CRITICAL: Proj must be early in the file (after RulesetFilename if present)
        # Without Proj metadata, CBECC cannot run simulations
        logger.info("Exporting project metadata...")
        proj_elem = self.proj_exporter.export_proj(root, internal.proj_metadata or {})

        # ================================================================
        # STEP 1.7: Create Bldg element INSIDE Proj
        # ================================================================
        # CRITICAL: Zones must be nested inside <Proj><Bldg>, not as direct children!
        # CBECC looks for geometry hierarchy: SDDXML → Proj → Bldg → ResZnGrp → ResZn
        bldg_elem = ET.SubElement(proj_elem, 'Bldg')
        logger.info("Created Bldg element inside Proj for geometry hierarchy")

        # ================================================================
        # STEP 2: Export Catalogs (Referenced by Other Elements)
        # ================================================================
        # These must be exported first so they exist when referenced
        # by spatial elements (surfaces, openings) and systems.
        # Catalogs are direct children of root in CIBD22X format (NOT inside Proj)

        logger.info("Exporting material catalogs...")
        if internal.materials:
            self.material_exporter.export_materials(root, internal.materials)

        logger.info("Exporting construction catalogs...")
        if internal.constructions:
            self.construction_exporter.export_constructions(root, internal.constructions)

        logger.info("Exporting window type catalogs...")
        if internal.window_types:
            self.windowtype_exporter.export_window_types(root, internal.window_types)

        logger.info("Exporting schedule catalogs...")
        if internal.schedules:
            self.schedule_exporter.export_schedules(root, internal.schedules)

        # ================================================================
        # STEP 2.5: Export HVAC Equipment Catalogs (MUST be before DU types)
        # ================================================================
        # CRITICAL: Dwelling unit types reference these catalogs via:
        #   HVACHtPumpRef, HVACFanRef, HVACDistRef, IAQFanRef
        # These catalog elements MUST exist before dwelling unit types reference them

        logger.info("Exporting HVAC equipment catalogs...")
        if internal.heat_pumps:
            self.heatpump_catalog_exporter.export_heat_pumps(root, internal.heat_pumps)

        if internal.fan_systems:
            self.fansystem_catalog_exporter.export_fan_systems(root, internal.fan_systems)

        if internal.distribution_systems:
            self.distributionsystem_catalog_exporter.export_distribution_systems(root, internal.distribution_systems)

        if internal.iaq_fans:
            self.iaqfan_catalog_exporter.export_iaq_fans(root, internal.iaq_fans)

        if internal.control_systems:
            self.controlsystem_catalog_exporter.export_control_systems(root, internal.control_systems)

        if internal.water_heaters:
            self.waterheater_catalog_exporter.export_water_heaters(root, internal.water_heaters)

        logger.info("Exporting dwelling unit type catalogs...")
        if internal.du_types:
            logger.info(f"About to export {len(internal.du_types)} dwelling unit types to root")
            self.dutype_exporter.export_du_types(root, internal.du_types)
            # Verify they were added
            dutypes_in_root = root.findall('.//DwellUnitType')
            logger.info(f"After export, root has {len(dutypes_in_root)} DwellUnitType elements")

        # ================================================================
        # STEP 3: Export Spatial Hierarchy INSIDE Bldg (Nested Structure)
        # ================================================================
        # CRITICAL: Pass bldg_elem, NOT root!
        # ZoneExporter handles the entire nested hierarchy:
        # Bldg → ResZnGrp → ResZn → Surfaces → Openings
        # This ensures proper XML nesting that CBECC expects

        logger.info("Exporting spatial hierarchy inside Bldg...")
        self.zone_exporter.export_zones_with_geometry(
            bldg_elem,  # Changed from root to bldg_elem
            internal.zone_groups or [],
            internal.zones or [],
            internal.surfaces or [],
            internal.openings or []
        )
        
        # ================================================================
        # STEP 4: Export HVAC Systems (Composite Elements)
        # ================================================================
        # HVACExporter handles both HVACSystem and ZoneTerminal elements
        # Zone terminals are exported as children of HVAC systems

        logger.info("Exporting HVAC systems...")
        if internal.hvac_systems or internal.zone_terminals:
            self.hvac_exporter.export_hvac_systems(
                root,
                internal.hvac_systems or [],
                internal.zone_terminals or []
            )

        # ================================================================
        # STEP 5: Export DHW Systems (Composite Elements)
        # ================================================================
        # DHWExporter handles DHWSystem, WaterHeater, and RecirculationLoop
        # Water heaters and recirc loops are exported as children of DHW systems

        logger.info("Exporting DHW systems...")
        if internal.dhw_systems or internal.water_heaters or internal.recirculation_loops:
            self.dhw_exporter.export_dhw_systems(
                root,
                internal.dhw_systems or [],
                internal.water_heaters or [],
                internal.recirculation_loops or []
            )
        
        # ================================================================
        # STEP 6: Export PV + Battery Systems (Composite Elements)
        # ================================================================
        # PVExporter handles PVArray and BatterySystem
        # Batteries can be nested (coupled to PV) or standalone

        logger.info("Exporting PV/battery systems...")
        if internal.pv_arrays or internal.battery_systems:
            self.pv_exporter.export_pv_systems(
                root,
                internal.pv_arrays or [],
                internal.battery_systems or []
            )
        
        logger.info("CIBD22X export complete!")
        return root
    
    def export_to_file(self, internal: InternalRepresentation, output_path: str) -> None:
        """
        Export InternalRepresentation to CIBD22X XML file.
        
        This is a convenience method that calls export_to_element() and writes
        the result to a file with proper XML formatting.
        
        Args:
            internal: InternalRepresentation to export
            output_path: Path where XML file should be written
        """
        logger.info(f"Exporting to file: {output_path}")
        
        # Generate XML tree
        root = self.export_to_element(internal)
        
        # Create ElementTree and write to file
        tree = ET.ElementTree(root)
        
        # Write with XML declaration and UTF-8 encoding
        tree.write(
            output_path,
            encoding='utf-8',
            xml_declaration=True,
            method='xml'
        )
        
        logger.info(f"Export complete: {output_path}")
