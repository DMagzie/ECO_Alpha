"""
CIBD25 Direct Writer - EMJSON → CIBD25 (no XML intermediate)

This module provides a direct conversion from EMJSON v6 to CIBD25 text format,
bypassing the problematic XML intermediate step.

Key Features:
- Direct EMJSON → CIBD25 conversion (no XML intermediate)
- Always includes commercial catalogs (fixes 101 errors)
- Correct property formatting (int vs string)
- No VentSpcFunc on ResZn (fixes 14 errors)
- Window types mapped to instances
- Single conversion step (faster)

Usage:
    from eco_tools.translators.cibd25 import CIBD25DirectWriter

    writer = CIBD25DirectWriter(emjson_data)
    writer.write_file('output.cibd25')
"""

from typing import Dict, Any, List, Optional
import logging
import re

from .element_writer import ElementWriter
from .catalog_builder import build_default_commercial_catalogs
from .property_rules import (
    should_skip_element,
    should_skip_property,
    filter_properties,
    get_required_defaults,
    apply_required_defaults,
    VERSION_MARKERS,
    WRITE_END_OF_FILE_MARKER,
)

logger = logging.getLogger(__name__)


class CIBD25DirectWriter:
    """
    Direct EMJSON v6 → CIBD25 text writer.

    This writer converts EMJSON v6 data directly to CIBD25 text format
    without going through an XML intermediate step.
    """

    def __init__(self, emjson_data: Dict[str, Any]):
        """
        Initialize writer with EMJSON v6 data.

        Args:
            emjson_data: EMJSON v6 formatted dictionary
        """
        self.emjson = emjson_data
        self.output_lines: List[str] = []
        self.element_writer = ElementWriter()
        self.catalogs: Dict[str, List[Dict[str, Any]]] = {}
        self.construction_name_map: Dict[str, str] = {}  # Maps construction IDs/refs to names
        self.window_type_name_map: Dict[str, str] = {}  # Maps window type IDs/refs to names
        self.polylp_counter: int = 0  # Counter for unique PolyLoop naming

    def write_file(self, output_path: str) -> bool:
        """
        Write CIBD25 file.

        Args:
            output_path: Path to output .cibd25 file

        Returns:
            True if successful, False otherwise
        """
        try:
            # TODO: Implement conversion
            logger.info(f"Writing CIBD25 file to {output_path}")

            # Build output in correct CIBD25 structure order:
            # Per validated CBECC 2025 format (MF88Unit reference):
            #
            # Structure:
            # RulesetFilename   "T24_2025.bin"
            # Proj   "name"
            #    [Proj properties]
            # ..  (Proj closes!)
            # Bldg   "Building"  (root level with name!)
            #    BldgAz = 0
            # ..
            # DwellUnitType   "name"  (root level)
            # ..
            # Mat   "name"  (root level)
            # ..
            # ResZnGrp   "Floor 1"  (root level - NOT inside Bldg!)
            #    Z = 0
            #    ...
            #    ResZn   "Zone"  (inside ResZnGrp)
            #       ...
            #    ..
            # ..

            # CRITICAL: Build catalogs and mappings FIRST (before writing surfaces)
            # This ensures construction/window type ID→name mappings are available
            self._ensure_commercial_catalogs()

            self._write_ruleset()
            self._write_proj()  # Writes Proj and CLOSES it with ..
            self._write_res_proj()  # ResProj for residential models (critical for CBECC validation)

            # CRITICAL ORDER: Catalog → Building → HVAC
            # Reference files show: Proj → ConsAssm/Mat → Bldg → Story/Spc → AirSys/Coils/Fans
            self._write_catalog()  # Mat, ConsAssm, FenCons catalogs at root level (BEFORE building!)

            self._write_building()  # Writes Bldg at root level, then Story/Spc with surfaces

            # HVAC and other systems come AFTER building elements
            self._write_dwelling_unit_types()  # DU Types at root level
            self._write_commercial_hvac()  # Commercial HVAC (AirSys, Fan, Coils, etc.) at root level
            self._write_hvac_systems()  # Residential HVAC systems at root level
            self._write_pv_arrays()  # Renewable energy systems at root level
            self._write_batteries()  # Batteries at root level
            self._write_lighting_systems()  # Lighting at root level

            # Write to file with Windows line endings (CRLF)
            # CIBD25 format requires Windows-style \r\n line endings for CBECC compatibility
            with open(output_path, 'w', newline='') as f:
                f.write('\r\n'.join(self.output_lines))

            logger.info(f"Successfully wrote {len(self.output_lines)} lines")
            return True

        except Exception as e:
            logger.error(f"Failed to write CIBD25: {e}")
            return False

    def _write_ruleset(self) -> None:
        """Write RulesetFilename (always T24_2025.bin)."""
        # TODO: Implement
        self.output_lines.append('RulesetFilename   "T24_2025.bin"')
        self.output_lines.append('')

    def _detect_geometry_type(self) -> str:
        """
        Detect whether the model uses detailed PolyLp geometry or simplified Area-based geometry.

        Returns:
            'Detailed' if model has PolyLp vertices, 'Simplified' if using explicit areas
        """
        geometry = self.emjson.get('geometry', {})

        # Check if any zones have vertices (floor polygons)
        zones = geometry.get('zones', [])
        for zone in zones:
            if zone.get('vertices') and len(zone.get('vertices', [])) >= 3:
                return 'Detailed'

        # Check if any surfaces have vertices (surface polygons)
        surfaces = geometry.get('surfaces', [])
        for surface in surfaces:
            if surface.get('vertices') and len(surface.get('vertices', [])) >= 3:
                return 'Detailed'

        # No PolyLp geometry found - using simplified geometry
        return 'Simplified'

    def _write_proj(self) -> None:
        """
        Write Proj element with project metadata.

        Per validated CBECC 2025 format (MF88Unit reference):
        - Proj opens, has properties, and CLOSES with ..
        - Bldg is at ROOT LEVEL (not inside Proj)
        - ResZnGrp is at ROOT LEVEL (not inside Bldg)
        """
        import time

        project = self.emjson.get('project', {})
        location = project.get('location', {})

        # Build project data
        current_timestamp = int(time.time())

        proj_name = project.get('name', 'Building')

        # Write Proj header
        self.output_lines.append(f'Proj   "{proj_name}"')

        # Write Proj properties (with 3-space indent)
        self.output_lines.append(f'   BldgEngyModelVersion = 17')
        self.output_lines.append(f'   CreateDate = {current_timestamp}')
        self.output_lines.append(f'   ModDate = {current_timestamp}')

        # Detect geometry type and write GeometryInpType only if using simplified geometry
        # CRITICAL: GeometryInpType = "Simplified" tells CBECC to ignore PolyLp geometry!
        # Only write this property when the source model actually uses simplified geometry (Area properties).
        # When providing PolyLp geometry, OMIT this property (defaults to detailed geometry mode).
        geometry_type = self._detect_geometry_type()
        if geometry_type == 'Simplified':
            self.output_lines.append(f'   GeometryInpType = "Simplified"')
            logger.info("Using simplified geometry (Area-based, no PolyLp)")
        else:
            logger.info("Using detailed geometry (PolyLp-based)")

        self.output_lines.append(f'   City = "{location.get("city", "City")}"')

        # ZipCode is an integer (no quotes)
        zip_code = location.get('zip_code', 94102)
        self.output_lines.append(f'   ZipCode = {zip_code}')

        # Use VERSION_MARKERS from property_rules (Fix #39)
        self.output_lines.append(f'   RunTitle = "{VERSION_MARKERS["RunTitle"]}"')
        self.output_lines.append(f'   SoftwareVersion = "{VERSION_MARKERS["SoftwareVersion"]}"')
        self.output_lines.append(f'   CompReportPDF = 1')
        self.output_lines.append(f'   CompReportXML = 1')
        self.output_lines.append(f'   ResultsCurrentMessage = "(not current)"')

        # Close Proj element
        self.output_lines.append('   ..')
        self.output_lines.append('')

        logger.info(f"Proj element written and closed: {proj_name}")

    def _write_res_proj(self) -> None:
        """
        Write ResProj element for residential models.

        ResProj is CRITICAL for residential models to pass CBECC validation.
        Without it, CBECC will stall/hang when trying to process the file.

        ResProj contains residential-specific compliance settings:
        - Standard design fuel types
        - IAQ fan power settings
        - Surface model methods
        """
        proj_metadata = self.emjson.get('proj_metadata', {})
        res_proj = proj_metadata.get('ResProj', {})

        # Skip if no ResProj data (commercial model)
        if not res_proj:
            logger.debug("No ResProj data - skipping (likely commercial model)")
            return

        # Get ResProj name from 'n' property or generate default
        res_proj_name = res_proj.get('n', 'Residential Project')

        # Write ResProj header
        self.output_lines.append(f'ResProj   "{res_proj_name}"')

        # Write ResProj properties
        # These are residential compliance-specific settings
        for key, value in res_proj.items():
            if key == 'n':
                continue  # Already used for name

            # Format value based on type
            if isinstance(value, str):
                # Check if it looks like a number
                try:
                    float(value)
                    self.output_lines.append(f'   {key} = {value}')
                except ValueError:
                    self.output_lines.append(f'   {key} = "{value}"')
            elif isinstance(value, (int, float)):
                self.output_lines.append(f'   {key} = {value}')
            elif value == '':
                continue  # Skip empty values
            else:
                self.output_lines.append(f'   {key} = "{value}"')

        # Close ResProj element
        self.output_lines.append('   ..')
        self.output_lines.append('')

        logger.info(f"ResProj element written: {res_proj_name}")

    def _clean_catalog_item(self, item: Dict[str, Any], catalog_type: str) -> Dict[str, Any]:
        """
        Clean catalog item by removing EMJSON-specific properties.

        Preserves CIBD25-specific properties from annotation:
        - Mat: CodeCat, CodeItem
        - ConsAssm (Commercial): CompatibleSurfType, MatRef
        - ResConsAssm (Residential): CanAssignTo, Type, Layer properties

        Args:
            item: Catalog item dict (material, construction, etc.)
            catalog_type: Type of catalog ('Mat', 'ConsAssm', etc.)

        Returns:
            Cleaned dict with CIBD25-compatible properties
        """
        # EMJSON properties to exclude
        emjson_props = {
            'id', 'material_type', 'thickness_m', 'r_value_SI', 'density_kg_m3', 'specific_heat',
            'construction_type', 'u_factor_SI', 'material_layers', 'framing_config',
            'framing_depth_m', 'framing_spacing_m', 'fenestration_type', 'area_m2',
            'shgc', 'vt', 'frame_type', 'glazing_type', 'num_panes', 'gas_fill'
        }

        # Start with name
        cleaned = {}
        if 'name' in item:
            cleaned['name'] = item['name']

        # Get annotation (contains original CIBD25 properties)
        annotation = item.get('annotation', {})
        if annotation and isinstance(annotation, dict):
            # Check if this is ResConsAssm (residential) or ConsAssm (commercial)
            xml_tag = annotation.get('xml_tag', '')

            if xml_tag == 'ResConsAssm':
                # Residential construction - has layer properties
                res_props = ['CanAssignTo', 'Type', 'CavityLayer', 'FrameLayer', 'SheathInsulLayer',
                            'SheathInsulLayerRVal', 'WallExtFinishLayer', 'RoofingLayer', 'AbvDeckInsulLayer',
                            'RoofDeckLayer', 'InsideFinishLayer', 'AtticFloorLayer', 'FloorSurfaceLayer',
                            'FlrConcreteFillLayer', 'FloorDeckLayer', 'SheathInsul2Layer', 'MassLayer',
                            'FurringInsul2Layer', 'FurringInsulLayer', 'Furring2Layer',
                            'FurringLayer']
                # Note: MassThickness removed - not recognized in CIBD25 (was valid in CIBD22X)
                for prop in res_props:
                    if prop in annotation:
                        cleaned[prop] = annotation[prop]

            elif xml_tag == 'ConsAssm' or catalog_type == 'ConsAssm':
                # Commercial construction - has CompatibleSurfType, MatRef
                comm_props = ['CompatibleSurfType', 'MatRef']
                for prop in comm_props:
                    if prop in annotation:
                        cleaned[prop] = annotation[prop]

            elif catalog_type == 'Mat':
                # Check if commercial (Mat) or residential (ResMat)
                if xml_tag == 'ResMat':
                    # Residential material - write all annotation properties except EMJSON metadata
                    # This preserves all CIBD25-specific ResMat properties like:
                    # - Physical: Density, SpecHeat, Conductivity, Thickness, RValPerInch
                    # - Thermal: ConductivityCT, ConductivityQII
                    # - Catalog: CodeCat, CodeItem

                    # Write all annotation properties (they're already in CIBD25 format)
                    for prop, value in annotation.items():
                        # Skip EMJSON metadata properties
                        if prop not in ['xml_tag']:
                            cleaned[prop] = value
                else:
                    # Commercial material - has CodeCat, CodeItem, and framing properties
                    # Framing properties (FrmMat, FrmConfig, FrmDepth) are CRITICAL for
                    # composite materials (wood frame, metal frame) used in construction assemblies.
                    # CavityIns and CavityInsOpt are CRITICAL for MetalInsFrameLayers table lookups.
                    # Without these, CBECC defaults to CavityIns=0 causing table lookup failures.
                    mat_props = ['CodeCat', 'CodeItem', 'FrmMat', 'FrmConfig', 'FrmDepth',
                                 'FrmCfg', 'FrmDpth', 'FrmSpc', 'CavityIns', 'CavityInsOpt']
                    for prop in mat_props:
                        if prop in annotation:
                            cleaned[prop] = annotation[prop]

            elif catalog_type == 'FenCons':
                # Fenestration construction - write all annotation properties
                # CIBD25 FenCons properties: FenProdType, CertificationMthd, SHGC, UFactor, VT, etc.
                for prop, value in annotation.items():
                    # Skip EMJSON metadata properties
                    if prop not in ['xml_tag']:
                        cleaned[prop] = value

        # For FenCons, also check for properties at root level (from catalog_builder defaults)
        if catalog_type == 'FenCons':
            fen_props = ['FenProdType', 'CertificationMthd', 'SHGC', 'UFactor', 'VT',
                        'AssemblyType', 'ProductType', 'FrameType', 'GlazingType']
            for prop in fen_props:
                if prop in item and prop not in cleaned:
                    cleaned[prop] = item[prop]

        return cleaned

    def _write_catalog(self) -> None:
        """
        Write all catalog elements (Mat, ConsAssm, FenCons, etc.).

        Note: Catalogs are now ensured in write_file() before surfaces are written.
        This allows construction/window type ID→name mappings to be available.
        """
        # Catalogs already ensured and loaded in write_file()
        # No need to call _ensure_commercial_catalogs() here

        # Write Mat catalog (both commercial Mat and residential ResMat)
        # Note: Residential and commercial materials use different element types and properties
        if 'Mat' in self.catalogs:
            logger.info(f"Writing {len(self.catalogs['Mat'])} material elements")
            for mat in self.catalogs['Mat']:
                # Determine if this is residential or commercial based on xml_tag in annotation
                annotation = mat.get('annotation', {})
                xml_tag = annotation.get('xml_tag', 'Mat') if annotation else 'Mat'

                # Use the appropriate element type
                element_type = 'ResMat' if xml_tag == 'ResMat' else 'Mat'

                cleaned_mat = self._clean_catalog_item(mat, 'Mat')
                lines = self.element_writer.write_element(element_type, cleaned_mat, indent=0)
                self.output_lines.extend(lines)
                self.output_lines.append('')  # Blank line after element

        # Write ConsAssm catalog (both commercial ConsAssm and residential ResConsAssm)
        # Note: Residential and commercial constructions use different element types and properties
        if 'ConsAssm' in self.catalogs:
            logger.info(f"Writing {len(self.catalogs['ConsAssm'])} construction assembly elements")
            for assm in self.catalogs['ConsAssm']:
                # Determine if this is residential or commercial based on xml_tag in annotation
                annotation = assm.get('annotation', {})
                xml_tag = annotation.get('xml_tag', 'ConsAssm') if annotation else 'ConsAssm'

                # Use the appropriate element type
                element_type = 'ResConsAssm' if xml_tag == 'ResConsAssm' else 'ConsAssm'

                cleaned_assm = self._clean_catalog_item(assm, 'ConsAssm')
                lines = self.element_writer.write_element(element_type, cleaned_assm, indent=0)
                self.output_lines.extend(lines)
                self.output_lines.append('')

        # Write FenCons catalog
        # Note: Name-only items are written and CBECC will look them up in its internal catalog
        if 'FenCons' in self.catalogs:
            logger.info(f"Writing {len(self.catalogs['FenCons'])} FenCons elements")
            for fen in self.catalogs['FenCons']:
                cleaned_fen = self._clean_catalog_item(fen, 'FenCons')
                lines = self.element_writer.write_element('FenCons', cleaned_fen, indent=0)
                self.output_lines.extend(lines)
                self.output_lines.append('')

        # Write ResWinType catalog (window type definitions)
        self._write_window_types()

        # Write HVAC component catalogs (must come before HVAC systems)
        self._write_heat_pump_systems()
        self._write_fan_systems()
        self._write_distribution_systems()

        # Write IAQ fan catalog (indoor air quality fans)
        self._write_iaq_fans()

        # Write SpcFuncDefaults catalog (space function defaults for commercial spaces)
        self._write_spc_func_defaults()

        # Note: Water heaters (ResWtrHtr) are now written in _write_hvac_systems()
        # before DHW systems, to maintain proper ordering

        logger.info("Catalog writing complete")

    @staticmethod
    def _clean_xml_tags(text: str) -> str:
        """
        Remove XML/HTML tags from text.

        Handles malformed source data where XML tags are embedded in values.
        Example: "<Name>Freedom Circle - Building A</Name>" → "Freedom Circle - Building A"

        Args:
            text: Text that may contain XML tags

        Returns:
            Text with XML tags removed
        """
        if not text:
            return text
        # Remove XML/HTML tags using regex
        return re.sub(r'<[^>]+>', '', text)

    def _generate_spc_func_defaults_name(self, spc_func: str) -> str:
        """
        Generate a simplified catalog name from a Title 24 space function string.

        Args:
            spc_func: Full Title 24 space function (e.g., "Office Area (<250 square feet)")

        Returns:
            Simplified catalog name (e.g., "Office Defaults")
        """
        # Common simplifications
        simplifications = {
            'Office Area (<250 square feet)': 'Office Defaults',
            'Office Area (>250 square feet)': 'Office Defaults',
            'Storage, Commercial/Industrial (Warehouse)': 'Warehouse Defaults',
            'Storage, Commercial/Industrial (Shipping & Handling)': 'Warehouse Defaults',
            'Corridor Area': 'Corridor Defaults',
            'Stairwell': 'Stairwell Defaults',
            'Electrical, Mechanical, Telephone Rooms': 'Elec/Mech Room Defaults',
            'Hotel/Motel Guest Room': 'Hotel Guest Room Defaults',
            'Dining Area (Bar/Lounge and Fine Dining)': 'Dining Area Defaults',
            'Kitchen/Food Preparation Area': 'Kitchen Defaults',
            'Lounge, Breakroom, or Waiting Area': 'Lounge/Breakroom Defaults',
            'Exercise/Fitness Center and Gymnasium Areas': 'Fitness/Gymnasium Defaults',
            'Laundry Area': 'Laundry Defaults',
            'Locker Room': 'Locker Room Defaults',
            'Unoccupied-Include in Gross Floor Area': 'Unoccupied Defaults',
            'All other': 'All Other Defaults',
        }

        # Check if we have a predefined simplification
        if spc_func in simplifications:
            return simplifications[spc_func]

        # Otherwise, generate a name by taking first significant words + "Defaults"
        # Remove parenthetical content and special characters
        import re
        name = re.sub(r'\([^)]*\)', '', spc_func)  # Remove (...)
        name = re.sub(r'[/,]', ' ', name)  # Replace / and , with space
        name = ' '.join(name.split())  # Normalize whitespace

        # Take first 3-4 words max
        words = name.split()[:3]
        if words:
            return ' '.join(words) + ' Defaults'

        return 'Space Function Defaults'

    def _write_spc_func_defaults(self) -> None:
        """
        Write SpcFuncDefaults catalog elements for commercial space functions.

        Collects unique space functions from zones and creates catalog entries
        with simplified names that can be referenced from Spc elements.
        """
        geometry = self.emjson.get('geometry', {})
        zones = geometry.get('zones', [])

        # Collect unique space functions from commercial zones
        space_functions = set()
        for zone in zones:
            annotation = zone.get('annotation', {})
            # Only process commercial Spc zones
            if annotation.get('xml_tag') == 'Spc':
                # Check for SpcFunc in annotation or space_function field
                spc_func = annotation.get('SpcFunc') or zone.get('space_function')
                if spc_func:
                    space_functions.add(spc_func)

        if not space_functions:
            logger.debug("No space functions found - skipping SpcFuncDefaults catalog")
            return

        logger.info(f"Writing {len(space_functions)} SpcFuncDefaults catalog entries")

        # Write each unique space function as a SpcFuncDefaults catalog entry
        for spc_func in sorted(space_functions):
            # Generate simplified catalog name
            defaults_name = self._generate_spc_func_defaults_name(spc_func)

            # Write SpcFuncDefaults element
            self.output_lines.append(f'SpcFuncDefaults   "{defaults_name}"')
            self.output_lines.append(f'   SpcFunc = "{spc_func}"')
            self.output_lines.append('   ..')
            self.output_lines.append('')

            logger.debug(f"  Wrote SpcFuncDefaults: '{defaults_name}' -> '{spc_func}'")

    def _write_building(self) -> None:
        """
        Write building hierarchy at root level.

        Per validated CBECC 2025 format (MF88Unit reference):
        - Bldg is at ROOT LEVEL with a name: Bldg   "Building"
        - Bldg has properties (BldgAz, TotStoryCnt, etc.) and closes
        - ResZnGrp is at ROOT LEVEL (not inside Bldg)
        - Each ResZn is inside its ResZnGrp

        Structure:
        Bldg   "Building"
           [Bldg properties]
        ..
        ResZnGrp   "Floor 1"
           Z = 0
           ...
           ResZn   "Zone1"
              ...
           ..
        ..
        """
        logger.info("Writing building hierarchy")

        geometry = self.emjson.get('geometry', {})

        # Calculate story counts for Bldg element
        tot_story_cnt, above_grd_story_cnt = self._calculate_story_counts(geometry)

        # Write Bldg element at root level with name
        bldg_name = self.emjson.get('project', {}).get('name', 'Building')
        # Clean any XML tags from building name (handles malformed source data)
        bldg_name = self._clean_xml_tags(bldg_name)
        self.output_lines.append(f'Bldg   "{bldg_name}"')

        # Write Bldg properties
        self.output_lines.append('   BldgAz = 0')

        # CRITICAL: When Story elements are present, Bldg MUST have story counts
        # Without these properties, CBECC freezes when processing Story elements
        if tot_story_cnt > 0:
            self.output_lines.append(f'   TotStoryCnt = {tot_story_cnt}')
            self.output_lines.append(f'   AboveGrdStoryCnt = {above_grd_story_cnt}')

        # Close Bldg element
        self.output_lines.append('   ..')
        self.output_lines.append('')

        # Write ResZnGrp elements at root level (not inside Bldg!)
        if geometry and 'zone_groups' in geometry:
            self._write_from_emjson_geometry(geometry)
        else:
            self._write_minimal_test_building()

        # Write Story elements followed immediately by their Spc children
        # CRITICAL: Story and Spc must be interleaved, not separate sections
        # Each Story is followed immediately by all Spc for that story
        if geometry and 'zones' in geometry:
            self._write_story_elements(geometry)

        # Write ThrmlZn (Thermal Zone) zones at root level (if any)
        # ThrmlZn zones are HVAC groupings referenced by Spc elements
        # NOTE: ThrmlZn is now written from commercial_hvac_components (has full HVAC references)
        # Do NOT write from geometry side to avoid duplicates
        # if geometry and 'zones' in geometry:
        #     self._write_thermal_zones(geometry)

        # Write FluidSeg (Fluid Segment) elements for service hot water (if any)
        # FluidSeg elements are referenced by Spc elements via SHWFluidSegRef
        if geometry and 'zones' in geometry:
            self._write_fluid_segments(geometry)

        logger.info("Building hierarchy complete")

    def _write_from_emjson_geometry(self, geometry: Dict[str, Any]) -> None:
        """
        Write building hierarchy from EMJSON geometry data.

        Args:
            geometry: EMJSON geometry section
        """
        zones_by_id = {z['id']: z for z in geometry.get('zones', [])}
        surfaces_by_zone = {}

        # Group surfaces by zone
        # EMJSON uses 'parent_zone_id' (not 'zone_id')
        for surface in geometry.get('surfaces', []):
            zone_id = surface.get('parent_zone_id')
            if zone_id:
                if zone_id not in surfaces_by_zone:
                    surfaces_by_zone[zone_id] = []
                surfaces_by_zone[zone_id].append(surface)

        # Write zone groups (floors) followed immediately by their zones
        # Per MF88Unit reference: ResZnGrp at ROOT LEVEL, followed immediately by its ResZn elements
        # CRITICAL: CBECC associates zones with the most recent ResZnGrp in the file!
        # So we MUST write: ResZnGrp → all its zones → next ResZnGrp → all its zones
        for zone_group in geometry.get('zone_groups', []):
            group_data = {
                'name': zone_group.get('name', 'Floor'),
                'Z': zone_group.get('z_height', 0),
                'FlrToFlrHgt': zone_group.get('floor_to_floor_height', 10),
                'FlrToCeilingHgt': zone_group.get('floor_to_ceiling_height', 9),
            }

            # Write ResZnGrp header at ROOT LEVEL (no indentation)
            self.output_lines.append(f'ResZnGrp   "{group_data["name"]}"')
            self.output_lines.append(f'   TreeState = 254')  # Standard property
            # Note: Z, FlrToFlrHgt, etc. are NOT properties of ResZnGrp in CBECC
            # They would be on the actual zones

            # Close the ResZnGrp immediately - it's just a grouping definition
            self.output_lines.append('   ..')
            self.output_lines.append('')

            # IMMEDIATELY write all zones for this zone group (at ROOT LEVEL)
            # Support both 'zone_ids' (test data) and 'zone_refs' (GUI imports)
            zone_references = zone_group.get('zone_ids', zone_group.get('zone_refs', []))
            for zone_id in zone_references:
                if zone_id in zones_by_id:
                    zone = zones_by_id[zone_id]
                    # ResZn is at ROOT LEVEL, so indent_level=0
                    self._write_zone_with_surfaces(zone, surfaces_by_zone.get(zone_id, []), indent_level=0)

    def _write_commercial_spaces(self, geometry: Dict[str, Any]) -> None:
        """
        Write commercial Spc (Space) zones at root level.

        Spc zones are used in commercial buildings and don't belong to ResZnGrp.
        They're written directly at root level with their child surfaces nested inside.

        Args:
            geometry: EMJSON geometry section
        """
        zones_by_id = {z['id']: z for z in geometry.get('zones', [])}
        surfaces_by_zone = {}

        # Group surfaces by zone
        for surface in geometry.get('surfaces', []):
            zone_id = surface.get('parent_zone_id')
            if zone_id:
                if zone_id not in surfaces_by_zone:
                    surfaces_by_zone[zone_id] = []
                surfaces_by_zone[zone_id].append(surface)

        # Find Spc zones (commercial spaces)
        spc_zones = []
        for zone in geometry.get('zones', []):
            annotation = zone.get('annotation', {})
            if annotation.get('xml_tag') == 'Spc':
                spc_zones.append(zone)

        if not spc_zones:
            logger.debug("No Spc (commercial space) zones found")
            return

        logger.info(f"Writing {len(spc_zones)} Spc (commercial space) zones")

        # Write each Spc zone at root level
        for zone in spc_zones:
            zone_id = zone.get('id')
            surfaces = surfaces_by_zone.get(zone_id, [])
            # Spc is at ROOT LEVEL, so indent_level=0
            self._write_zone_with_surfaces(zone, surfaces, indent_level=0)

    def _write_thermal_zones(self, geometry: Dict[str, Any]) -> None:
        """
        Write ThrmlZn (Thermal Zone) elements at root level.

        ThrmlZn zones are HVAC zone groupings in commercial buildings.
        Multiple Spc elements can reference the same ThrmlZn.

        Args:
            geometry: EMJSON geometry section
        """
        # Find ThrmlZn zones
        thrmlzn_zones = []
        for zone in geometry.get('zones', []):
            annotation = zone.get('annotation', {})
            if annotation.get('xml_tag') == 'ThrmlZn':
                thrmlzn_zones.append(zone)

        if not thrmlzn_zones:
            logger.debug("No ThrmlZn (thermal zone) zones found")
            return

        logger.info(f"Writing {len(thrmlzn_zones)} ThrmlZn (thermal zone) zones")

        # Write each ThrmlZn zone at root level
        for zone in thrmlzn_zones:
            zone_name = zone.get('name', 'ThermalZone')
            annotation = zone.get('annotation', {})

            # Build ThrmlZn data (minimal for now)
            thrmlzn_data = {
                'name': zone_name,
                'Type': 'Conditioned',  # Default to conditioned
            }

            # Write ThrmlZn element at root level (indent_level=0)
            lines = self.element_writer.write_element('ThrmlZn', thrmlzn_data, indent=0)
            self.output_lines.extend(lines)
            self.output_lines.append('')

    def _write_fluid_segments(self, geometry: Dict[str, Any]) -> None:
        """
        Write FluidSeg (Fluid Segment) elements for service hot water.

        FluidSeg elements are referenced by Spc elements via SHWFluidSegRef.
        For now, we write standard SHW segments that cover most commercial buildings.

        NOTE: This is a fallback for models without full FluidSys definitions.
        If commercial FluidSys/FluidSegs are present in metadata, skip this.

        Args:
            geometry: EMJSON geometry section
        """
        # Check if commercial FluidSys/FluidSegs already exist
        metadata = self.emjson.get('metadata', {})
        commercial_hvac = metadata.get('commercial_hvac_components', {})
        if commercial_hvac.get('FluidSys') or commercial_hvac.get('FluidSeg'):
            logger.debug("Skipping hardcoded FluidSegs - commercial FluidSys/FluidSegs exist")
            return

        # Check if any Spc zones reference FluidSeg elements
        needs_shw = False
        for zone in geometry.get('zones', []):
            annotation = zone.get('annotation', {})
            if annotation.get('xml_tag') == 'Spc':
                if 'SHWFluidSegRef' in annotation:
                    needs_shw = True
                    break

        if not needs_shw:
            logger.debug("No FluidSeg elements needed (no SHW references)")
            return

        logger.info("Writing FluidSeg (fluid segment) elements for SHW")

        # Write SHW Supply FluidSeg
        shw_supply_data = {
            'name': 'SHWSupply',
            'Type': 'PrimarySupply',
        }
        lines = self.element_writer.write_element('FluidSeg', shw_supply_data, indent=0)
        self.output_lines.extend(lines)
        self.output_lines.append('')

        # Write SHW Makeup FluidSeg
        shw_makeup_data = {
            'name': 'SHWMakeup',
            'Type': 'MakeupFluid',
            'Src': 'MunicipalWater',
        }
        lines = self.element_writer.write_element('FluidSeg', shw_makeup_data, indent=0)
        self.output_lines.extend(lines)
        self.output_lines.append('')

    def _calculate_story_counts(self, geometry: Dict[str, Any]) -> tuple:
        """
        Calculate total and above-grade story counts from Spc elements.

        CRITICAL: Bldg element MUST include TotStoryCnt and AboveGrdStoryCnt
        when Story elements are present. Without these, CBECC freezes.

        Story naming convention:
        - B## (e.g., B01, B02): Basement/below-grade stories
        - L## (e.g., L01, L02): Level/above-grade stories
        - Other patterns: Assumed above-grade

        Args:
            geometry: EMJSON geometry section

        Returns:
            tuple: (tot_story_cnt, above_grd_story_cnt)
        """
        if not geometry:
            return (0, 0)

        # Collect unique Story names from Spc elements
        story_names = set()
        for zone in geometry.get('zones', []):
            annotation = zone.get('annotation', {})
            if annotation.get('xml_tag') == 'Spc':
                parent_story = annotation.get('ParentStoryRef')
                if parent_story:
                    story_names.add(parent_story)

        if not story_names:
            return (0, 0)

        # Total story count
        tot_story_cnt = len(story_names)

        # Count above-grade stories
        # Basement stories typically named: B01, B02, Basement, etc.
        # Check for basement pattern: "B" followed by digit (B01, B02)
        # or starts with "Basement"
        above_grd_story_cnt = 0
        for name in story_names:
            # Check if it's a basement story
            is_basement = (
                (len(name) >= 2 and name[0] == 'B' and name[1].isdigit()) or  # B01, B02, etc.
                name.lower().startswith('basement')  # Basement, basement, etc.
            )
            if not is_basement:
                above_grd_story_cnt += 1

        logger.debug(f"Story counts: Total={tot_story_cnt}, AboveGrade={above_grd_story_cnt}")
        logger.debug(f"Story names: {sorted(story_names)}")

        return (tot_story_cnt, above_grd_story_cnt)

    def _write_story_elements(self, geometry: Dict[str, Any]) -> None:
        """
        Write Story elements followed immediately by their Spc children.

        CRITICAL: In CIBD25, each Story must be followed IMMEDIATELY by all Spc
        elements for that story. This ordering allows CBECC to:
        1. Associate Spc with their parent Story
        2. Calculate story-level totals (square footage)
        3. Display proper tree hierarchy in GUI

        Reference file structure:
            Story   "Building Story 1"
            ..
            Spc   "Room_101"
                ParentStoryRef = "Building Story 1"
            ..
            Spc   "Room_102"
                ParentStoryRef = "Building Story 1"
            ..
            Story   "Building Story 2"
            ..
            Spc   "Room_201"
                ParentStoryRef = "Building Story 2"
            ..

        Args:
            geometry: EMJSON geometry section
        """
        # Group surfaces by zone for Spc writing
        surfaces_by_zone = {}
        for surface in geometry.get('surfaces', []):
            zone_id = surface.get('parent_zone_id')
            if zone_id:
                if zone_id not in surfaces_by_zone:
                    surfaces_by_zone[zone_id] = []
                surfaces_by_zone[zone_id].append(surface)

        # Group Spc zones by their ParentStoryRef
        spaces_by_story = {}
        for zone in geometry.get('zones', []):
            annotation = zone.get('annotation', {})
            if annotation.get('xml_tag') == 'Spc':
                parent_story = annotation.get('ParentStoryRef')
                if parent_story:
                    if parent_story not in spaces_by_story:
                        spaces_by_story[parent_story] = []
                    spaces_by_story[parent_story].append(zone)

        if not spaces_by_story:
            logger.debug("No Story elements needed (no Spc with ParentStoryRef)")
            return

        logger.info(f"Writing {len(spaces_by_story)} Story elements with their Spc children")

        # Write each Story followed immediately by all its Spc elements
        # Sort for deterministic output
        sorted_stories = sorted(spaces_by_story.keys())
        for i, story_name in enumerate(sorted_stories):
            # Write Story element at root level
            story_data = {
                'name': story_name,
            }
            # TreeState = 254 for all stories except the first
            # This tells CBECC GUI to properly organize the tree hierarchy
            if i > 0:
                story_data['TreeState'] = 254

            lines = self.element_writer.write_element('Story', story_data, indent=0)
            self.output_lines.extend(lines)
            self.output_lines.append('')

            # Immediately write all Spc elements for this Story
            spc_zones = spaces_by_story[story_name]
            logger.info(f"  Writing {len(spc_zones)} Spc elements for Story '{story_name}'")

            for zone in spc_zones:
                zone_id = zone.get('id')
                surfaces = surfaces_by_zone.get(zone_id, [])
                # Spc is at ROOT LEVEL, so indent_level=0
                self._write_zone_with_surfaces(zone, surfaces, indent_level=0)

    def _get_openings_for_surface(self, surface_id: str) -> List[Dict[str, Any]]:
        """Get all openings (windows/doors) for a given surface."""
        # Openings are stored in geometry.openings, not at top level
        geometry = self.emjson.get('geometry', {})
        openings = geometry.get('openings', [])

        logger.debug(f"Total openings in EMJSON: {len(openings)}")
        matching_openings = [o for o in openings if o.get('parent_surface_id') == surface_id]
        if matching_openings:
            logger.debug(f"Found {len(matching_openings)} openings for surface_id={surface_id}")
        return matching_openings

    def _write_commercial_surface(self, surface: Dict[str, Any], xml_tag: str, surf_name: str, indent_level: int = 0) -> None:
        """
        Write a commercial surface element with PolyLp geometry.

        Commercial surfaces (ExtWall, IntWall, Roof, UndgrFlr, Win, Dr, Skylt)
        use PolyLp for geometry. CBECC calculates area from PolyLp vertices.

        Required properties:
        - Name
        - ConsAssmRef (or FenConsRef for Win/Dr/Skylt)
        - PolyLp with CartesianPt vertices

        Args:
            surface: Surface data from EMJSON
            xml_tag: Original XML tag name (ExtWall, IntWall, etc.)
            surf_name: Surface name
            indent_level: Indentation level
        """
        # Get construction reference
        construction_ref = surface.get('construction_ref', surface.get('construction', ''))

        # Resolve construction reference to actual catalog name
        if xml_tag in ['Win', 'Dr', 'Skylt']:
            # Fenestration - needs FenConsRef
            # For now, use a default or skip if no reference
            construction_name = self._resolve_construction_ref(construction_ref, 'Default Window')
            surf_data = {
                'name': surf_name,
                'TreeState': 254,  # Required for CBECC GUI tree organization
            }
            # Add construction reference if available
            if construction_ref:
                surf_data['FenConsRef'] = construction_name
        else:
            # Opaque surface - needs ConsAssmRef
            construction_name = self._resolve_construction_ref(construction_ref, 'Default Construction')
            surf_data = {
                'name': surf_name,
                'TreeState': 254,  # Required for CBECC GUI tree organization
            }
            # Add construction reference if available
            if construction_ref:
                surf_data['ConsAssmRef'] = construction_name

        # Write the element using xml_tag directly
        lines = self.element_writer.write_element(xml_tag, surf_data, indent=indent_level)
        self.output_lines.extend(lines)
        self.output_lines.append('')

        # Write PolyLp geometry if vertices are available
        vertices = surface.get('vertices')
        if vertices and len(vertices) >= 3:
            self.polylp_counter += 1
            self._write_polylp_geometry(vertices, self.polylp_counter, indent_level)
            logger.debug(f"Wrote commercial surface {xml_tag}: {surf_name} with {len(vertices)} vertices")
        else:
            logger.warning(f"Commercial surface {xml_tag}: {surf_name} has no vertices - CBECC may fail geometry validation")
            logger.debug(f"Wrote commercial surface {xml_tag}: {surf_name} without geometry")

    def _write_polylp_geometry(self, vertices: List[Dict[str, float]], polylp_index: int, indent_level: int = 0) -> None:
        """
        Write PolyLp and CartesianPt geometry elements for commercial surfaces.

        Args:
            vertices: List of vertices [{'x': float, 'y': float, 'z': float}, ...]
            polylp_index: Index for PolyLp element name
            indent_level: Base indentation level
        """
        if not vertices or len(vertices) < 3:
            return

        indent_str = '   ' * indent_level

        # Write PolyLp element at root level
        self.output_lines.append(f'PolyLp   "PolyLoop {polylp_index}"')
        self.output_lines.append('   ..')  # Indented close - tells CBECC that following CartesianPt belong to this PolyLp
        self.output_lines.append('')

        # Write CartesianPt elements for each vertex at root level
        # Even though they appear at root level, the indented PolyLp close associates them
        for i, vertex in enumerate(vertices):
            x = vertex['x']
            y = vertex['y']
            z = vertex['z']
            self.output_lines.append(f'CartesianPt   "CartesianPoint {polylp_index}_{i}"')
            self.output_lines.append(f'   Coord = ( {x}, {y}, {z} )')
            self.output_lines.append('   ..')  # Indented close
            self.output_lines.append('')

    def _write_opening(self, opening: Dict[str, Any], indent_level: int = 0, is_commercial: bool = False) -> None:
        """
        Write a window or door opening.

        Args:
            opening: Opening data from EMJSON
            indent_level: Indentation level
            is_commercial: True for commercial openings (Win, Dr), False for residential (ResWin, ResDr)
        """
        opening_type = opening.get('type', 'window')

        if opening_type == 'window':
            # Convert area from m² to ft²
            area_m2 = opening.get('area_m2')
            area_ft2 = area_m2 * 10.7639 if area_m2 else None

            # Skip windows with invalid (near-zero or negative) areas
            # Minimum reasonable window area is 0.01 ft² (~1 square inch)
            MIN_OPENING_AREA = 0.01
            if area_ft2 is not None and area_ft2 < MIN_OPENING_AREA:
                logger.warning(f"Skipping window '{opening.get('id')}' with invalid area {area_ft2:.2e} ft² (< {MIN_OPENING_AREA} ft²)")
                return  # Skip this opening entirely

            if is_commercial:
                # Commercial windows (Win) - use FenConsRef, NOT WinType/SpecMethod
                opening_data = {
                    'name': opening.get('id', 'Window'),
                }
                # Add area if present and valid
                if area_ft2:
                    opening_data['Area'] = area_ft2
                # TODO: Add FenConsRef if available from opening data
                element_name = 'Win'
            else:
                # Residential windows (ResWin) - use WinType, SpecMethod, NFRC properties
                win_type = opening.get('window_type_ref', 'Standard Window')
                opening_data = {
                    'name': opening.get('id', 'Window'),
                    'WinType': win_type,
                    'SpecMethod': 'Overall Window Area',
                }

                # Add area if present
                if area_ft2:
                    opening_data['Area'] = area_ft2

                # Look up window type and copy performance values to instance
                # CBECC requires NFRCUfactor and NFRCSHGC on each ResWin instance
                catalogs = self.emjson.get('catalogs', {})
                window_types = catalogs.get('window_types', [])
                for wt_obj in window_types:
                    wt = self._to_dict(wt_obj)
                    if wt.get('name') == win_type or wt.get('id') == win_type:
                        annotation = wt.get('annotation', {})
                        # Copy NFRC U-factor if present
                        if 'NFRCUfactor' in annotation:
                            opening_data['NFRCUfactor'] = float(annotation['NFRCUfactor'])
                        # Copy NFRC SHGC if present
                        if 'NFRCSHGC' in annotation:
                            opening_data['NFRCSHGC'] = float(annotation['NFRCSHGC'])
                        break
                element_name = 'ResWin'

            lines = self.element_writer.write_element(element_name, opening_data, indent=indent_level)

        elif opening_type == 'door':
            # Convert area from m² to ft²
            area_m2 = opening.get('area_m2', 20.0)
            if area_m2 is None:
                area_m2 = 20.0  # Default door area
            area_ft2 = area_m2 * 10.7639

            opening_data = {
                'name': opening.get('id', 'Door'),
                'Area': area_ft2,
            }

            # Add fenestration reference if present
            if opening.get('fenestration_cons_ref'):
                opening_data['FenConsRef'] = opening['fenestration_cons_ref']

            # Use Dr for commercial, ResDr for residential
            element_name = 'Dr' if is_commercial else 'ResDr'
            lines = self.element_writer.write_element(element_name, opening_data, indent=indent_level)

        else:
            logger.warning(f"Unknown opening type: {opening_type}")
            return

        self.output_lines.extend(lines)

        # Write PolyLp geometry for commercial openings (Win, Dr)
        # Commercial openings require geometry in CIBD25, just like surfaces
        if is_commercial:
            vertices = opening.get('vertices')
            if vertices and len(vertices) >= 3:
                self.polylp_counter += 1
                self._write_polylp_geometry(vertices, self.polylp_counter, indent_level)
                logger.debug(f"Wrote commercial opening '{opening.get('id')}' with {len(vertices)} vertices")
            else:
                logger.debug(f"Commercial opening '{opening.get('id')}' has no vertices - skipping PolyLp geometry")

    def _write_dwelling_unit(self, dwelling_unit: Dict[str, Any], zone_name: str, zone_data: Dict[str, Any] = None, indent_level: int = 0) -> None:
        """
        Write a DwellUnit instance.

        Args:
            dwelling_unit: DwellUnit data from zone annotation
            zone_name: Parent zone name for generating DU name
            zone_data: Full zone data (to extract system references)
        """
        # Generate name if not provided
        du_name = dwelling_unit.get('name', f'{zone_name} DU')

        # DwellUnit data
        du_data = {
            'name': du_name,
        }

        # Add DwellUnitTypeRef if available
        du_type_ref = dwelling_unit.get('dwelling_unit_type_ref') or dwelling_unit.get('du_ref')
        if du_type_ref:
            du_data['DwellUnitTypeRef'] = du_type_ref

        # Add Count if specified (defaults to 1)
        count = dwelling_unit.get('count', 1)
        if count > 1:
            du_data['Count'] = count

        # Add zone references (required for CBECC to associate DU with zone)
        # WasherZoneRef and DryerZoneRef point to the parent zone
        du_data['WasherZoneRef'] = zone_name
        du_data['DryerZoneRef'] = zone_name

        # Add system references from dwelling_unit data
        if dwelling_unit.get('hvac_system_ref'):
            du_data['ResHVACSysRef'] = dwelling_unit['hvac_system_ref']

        if dwelling_unit.get('dhw_system_ref'):
            du_data['ResDHWSysRef'] = dwelling_unit['dhw_system_ref']

        if dwelling_unit.get('iaq_fan_ref'):
            du_data['ResIAQFanRef'] = dwelling_unit['iaq_fan_ref']

        # If zone_data provided, check for served_by references
        if zone_data:
            served_by = zone_data.get('served_by', [])
            if served_by:
                # First system in served_by is typically HVAC
                # Look up if it's HVAC or DHW based on system ID prefix or type
                systems = self.emjson.get('systems', {})
                hvac_systems = systems.get('hvac', [])
                dhw_systems = systems.get('dhw', [])

                # Map system IDs to references
                hvac_ids = {s.get('id'): s.get('id') for s in hvac_systems}
                dhw_ids = {s.get('id'): s.get('id') for s in dhw_systems}

                for sys_id in served_by:
                    if sys_id in hvac_ids and 'ResHVACSysRef' not in du_data:
                        du_data['ResHVACSysRef'] = sys_id
                    elif sys_id in dhw_ids and 'ResDHWSysRef' not in du_data:
                        du_data['ResDHWSysRef'] = sys_id

        # Filter properties per V7 rules before writing
        # This removes deprecated properties like PVBattSizeBldgType, BattReq_PartOfLargeTenantArea
        du_data = filter_properties('DwellUnit', du_data)

        # Write DwellUnit element
        lines = self.element_writer.write_element('DwellUnit', du_data, indent=indent_level)
        self.output_lines.extend(lines)

        logger.debug(f"Wrote DwellUnit: {du_name} -> {du_data.get('DwellUnitTypeRef')}")

    def _write_window_types(self) -> None:
        """
        Write ResWinType (residential) and FenCons (non-residential) catalog elements.

        Distinguishes between:
        - FenCons: Commercial/non-residential windows (has UFactor/SHGC/VT, FenProdType)
        - ResWinType: Residential window instances (has Area, NFRCUfactor/NFRCSHGC)

        Units: area (m² → ft²), U-factor (W/m²·K → Btu/h·ft²·°F)
        """
        # Window types are in catalogs.window_types
        catalogs = self.emjson.get('catalogs', {})
        window_types = catalogs.get('window_types', [])

        if not window_types:
            logger.debug("No window_types in EMJSON")
            return

        logger.info(f"Processing {len(window_types)} window catalog elements")

        fencons_count = 0
        reswintype_count = 0

        for wt_obj in window_types:
            wt = self._to_dict(wt_obj)
            name = wt.get('name', 'Window Type')

            # Get key properties to determine catalog type
            area_m2 = wt.get('area_m2')
            u_factor_SI = wt.get('u_factor_SI')
            u_factor_ip = wt.get('u_factor_ip')
            shgc = wt.get('shgc')
            vt = wt.get('vt')
            annotation = wt.get('annotation', {})
            nfrc_ufactor = annotation.get('NFRCUfactor')
            nfrc_shgc = annotation.get('NFRCSHGC')

            # Determine if this should be FenCons (commercial) or ResWinType (residential)
            # FenCons: has UFactor/SHGC/VT but no Area, no NFRC values (commercial catalog)
            # ResWinType: has Area or NFRC values (residential window instance)
            is_fencons = (
                (u_factor_SI or u_factor_ip or shgc or vt) and  # Has glazing properties
                not area_m2 and  # No area specified
                not nfrc_ufactor and  # No NFRC U-factor
                not nfrc_shgc  # No NFRC SHGC
            )

            if is_fencons:
                # Write as FenCons (commercial/non-residential catalog)
                fencons_data = {
                    'name': name,
                }

                # Map product type from name if it contains common window type keywords
                # Note: Skylight is NOT a valid FenProdType for commercial (FenCons)
                # Skylights are residential-only and should use different element types
                name_lower = name.lower()

                # Skip skylights for FenCons - they're residential-only
                if 'skylight' in name_lower:
                    logger.debug(f"Skipping skylight '{name}' - not valid for FenCons (commercial)")
                    fencons_count += 1  # Still count it to avoid confusion in logs
                    continue

                if 'fixed' in name_lower:
                    fencons_data['FenProdType'] = 'FixedWindow'
                elif 'operable' in name_lower or 'casement' in name_lower or 'hung' in name_lower:
                    fencons_data['FenProdType'] = 'OperableWindow'
                elif 'door' in name_lower or 'glazed' in name_lower:
                    fencons_data['FenProdType'] = 'GlazedDoor'
                elif 'storefront' in name_lower or 'curtain' in name_lower:
                    fencons_data['FenProdType'] = 'CurtainWall'
                else:
                    fencons_data['FenProdType'] = 'FixedWindow'  # Default

                # Add certification method
                fencons_data['CertificationMthd'] = 'NFRCRated'

                # Convert U-factor if in SI units, otherwise use IP
                if u_factor_SI:
                    fencons_data['UFactor'] = u_factor_SI / 5.678
                elif u_factor_ip:
                    fencons_data['UFactor'] = u_factor_ip

                # SHGC and VT are dimensionless
                if shgc:
                    fencons_data['SHGC'] = shgc
                if vt:
                    fencons_data['VT'] = vt

                # Write FenCons element
                lines = self.element_writer.write_element('FenCons', fencons_data, indent=0)
                self.output_lines.extend(lines)
                self.output_lines.append('')
                fencons_count += 1
                logger.debug(f"Wrote FenCons: {name}")

            else:
                # Write as ResWinType (residential window instance)
                wt_data = {
                    'name': name,
                }

                # Convert area: m² → ft² (multiply by 10.7639)
                if area_m2:
                    wt_data['Area'] = area_m2 * 10.7639

                # Spec method
                if 'SpecMethod' in annotation:
                    wt_data['SpecMethod'] = annotation['SpecMethod']
                elif area_m2:
                    wt_data['SpecMethod'] = 'Overall Window Area'

                # NFRC U-factor (already in IP units) - NOTE: Not UFactor!
                if nfrc_ufactor:
                    wt_data['NFRCUfactor'] = float(nfrc_ufactor)

                # NFRC SHGC - NOTE: Not SHGC!
                if nfrc_shgc:
                    wt_data['NFRCSHGC'] = float(nfrc_shgc)

                # Frame and glazing properties
                frame_type = wt.get('frame_type')
                if frame_type:
                    wt_data['FrmType'] = frame_type

                glazing_type = wt.get('glazing_type')
                if glazing_type:
                    wt_data['GlzgType'] = glazing_type

                num_panes = wt.get('num_panes')
                if num_panes:
                    wt_data['NumPanes'] = num_panes

                gas_fill = wt.get('gas_fill')
                if gas_fill:
                    wt_data['GasFill'] = gas_fill

                # Write ResWinType element
                lines = self.element_writer.write_element('ResWinType', wt_data, indent=0)
                self.output_lines.extend(lines)
                self.output_lines.append('')
                reswintype_count += 1
                logger.debug(f"Wrote ResWinType: {name}")

        logger.info(f"Wrote {fencons_count} FenCons and {reswintype_count} ResWinType catalog elements")

    def _to_dict(self, obj):
        """Convert object to dict if needed."""
        if isinstance(obj, dict):
            return obj
        return vars(obj)

    def _resolve_construction_ref(self, construction_ref: str, default: str = 'Standard Exterior Wall') -> str:
        """
        Resolve construction reference to actual construction name.

        Args:
            construction_ref: Construction ID or reference from surface
            default: Default construction name if reference not found

        Returns:
            Actual construction name from catalog
        """
        if not construction_ref:
            logger.debug(f"Empty construction_ref, using default: {default}")
            return default

        # Try to find the construction name in our mapping
        if construction_ref in self.construction_name_map:
            resolved = self.construction_name_map[construction_ref]
            logger.debug(f"Resolved construction '{construction_ref}' → '{resolved}'")
            return resolved

        # If not found, return the ref as-is and log a warning
        logger.warning(f"Construction reference '{construction_ref}' NOT FOUND in map (keys: {list(self.construction_name_map.keys())}), using as-is")
        return construction_ref

    def _write_heat_pump_systems(self) -> None:
        """
        Write ResHtPumpSys catalog elements from heat_pumps in EMJSON.

        Converts heat pump definitions to CIBD25 ResHtPumpSys format.
        """
        # Check both root level and nested locations for heat_pumps
        heat_pumps = self.emjson.get('heat_pumps', [])
        if not heat_pumps:
            # Try nested location (from GUI/v6 structure)
            heat_pumps = self.emjson.get('systems', {}).get('heat_pumps', [])

        if not heat_pumps:
            logger.debug("No heat_pumps in EMJSON")
            return

        logger.info(f"Writing {len(heat_pumps)} ResHtPumpSys elements")

        for hp_obj in heat_pumps:
            hp = self._to_dict(hp_obj)
            # Build ResHtPumpSys data
            hp_data = {
                'name': hp.get('name', 'Heat Pump'),
            }

            # Add properties from annotation
            annotation = hp.get('annotation', {})

            # Type (pump_type from main properties)
            pump_type = hp.get('pump_type')
            if pump_type:
                hp_data['Type'] = pump_type
            elif 'Type' in annotation:
                hp_data['Type'] = annotation['Type']

            # AutoSize flag
            if 'AutoSize' in annotation:
                hp_data['AutoSize'] = int(annotation['AutoSize'])

            # Efficiency ratings
            if 'HSPF2' in annotation:
                hp_data['HSPF2'] = float(annotation['HSPF2'])

            if 'SEER2' in annotation:
                hp_data['SEER2'] = float(annotation['SEER2'])

            # Capacity ratings (Cap47, Cap17 already in IP units - Btu/h)
            if 'Cap47' in annotation:
                hp_data['Cap47'] = float(annotation['Cap47'])

            if 'Cap17' in annotation:
                hp_data['Cap17'] = float(annotation['Cap17'])

            # AC charge verification
            if 'ACCharge' in annotation:
                hp_data['ACCharge'] = annotation['ACCharge']

            # Use EER in analysis flag
            if 'UseEERinAnalysis' in annotation:
                hp_data['UseEERinAnalysis'] = int(annotation['UseEERinAnalysis'])

            # Write ResHtPumpSys element
            lines = self.element_writer.write_element('ResHtPumpSys', hp_data, indent=0)
            self.output_lines.extend(lines)
            self.output_lines.append('')  # Blank line after element

            logger.debug(f"Wrote ResHtPumpSys: {hp_data['name']}")

        logger.info(f"Wrote {len(heat_pumps)} ResHtPumpSys catalog elements")

    def _write_fan_systems(self) -> None:
        """
        Write ResFanSys catalog elements from fan_systems in EMJSON.

        Converts fan system definitions to CIBD25 ResFanSys format.
        """
        # Check both root level and nested locations for fan_systems
        fan_systems = self.emjson.get('fan_systems', [])
        if not fan_systems:
            # Try nested location (from GUI/v6 structure)
            fan_systems = self.emjson.get('systems', {}).get('fan_systems', [])

        if not fan_systems:
            logger.debug("No fan_systems in EMJSON")
            return

        logger.info(f"Writing {len(fan_systems)} ResFanSys elements")

        for fan_obj in fan_systems:
            fan = self._to_dict(fan_obj)

            # Add properties from annotation
            annotation = fan.get('annotation', {})

            # Check xml_tag to determine element type (ResFanSys vs ResCentralVentSys)
            xml_tag = annotation.get('xml_tag', 'ResFanSys')

            # Build fan system data
            fan_data = {
                'name': fan.get('name', 'Fan System'),
            }

            if xml_tag == 'ResCentralVentSys':
                # ResCentralVentSys: Balanced ventilation system (ERV/HRV)
                # Valid properties: Type, SupFanPwrIdx, ExhFanPwrIdx
                valid_props = {'Type', 'SupFanPwrIdx', 'ExhFanPwrIdx'}

                for prop, value in annotation.items():
                    if prop in valid_props:
                        fan_data[prop] = value

                # Set defaults if not specified
                if 'Type' not in fan_data:
                    fan_data['Type'] = 'Balanced'

                element_type = 'ResCentralVentSys'

            else:
                # ResFanSys: Single speed supply/exhaust fan
                # Valid CIBD25 ResFanSys properties (based on CBECC 2025 schema)
                # CIBD22 properties like ModelingMthd, FlowEff, TotStaticPress, MtrHP, MtrEff, FlowCap, Pwr are NOT valid
                valid_props = {'Type', 'DefaultSystem', 'WperCFMCool'}

                for prop, value in annotation.items():
                    # Only write valid CIBD25 properties
                    if prop in valid_props:
                        fan_data[prop] = value

                # Map fan_type from EMJSON if not already set
                # CIBD25 only supports "Single Speed Fan" for ResFanSys Type
                fan_type = fan.get('fan_type') or annotation.get('Type')
                if 'Type' not in fan_data:
                    # All ResFanSys elements must use "Single Speed Fan"
                    fan_data['Type'] = 'Single Speed Fan'

                # Set default values if missing
                if 'DefaultSystem' not in fan_data:
                    fan_data['DefaultSystem'] = 0

                if 'WperCFMCool' not in fan_data:
                    # Default to 0.45 W/CFM if not specified
                    fan_data['WperCFMCool'] = 0.45

                element_type = 'ResFanSys'

            # Write fan system element (ResFanSys or ResCentralVentSys)
            lines = self.element_writer.write_element(element_type, fan_data, indent=0)
            self.output_lines.extend(lines)
            self.output_lines.append('')  # Blank line after element

            logger.debug(f"Wrote {element_type}: {fan_data['name']}")

        logger.info(f"Wrote {len(fan_systems)} ResFanSys catalog elements")

    def _write_distribution_systems(self) -> None:
        """
        Write ResDistSys catalog elements from distribution_systems in EMJSON.

        Converts distribution system definitions to CIBD25 ResDistSys format.
        """
        # Check both root level and nested locations for distribution_systems
        distribution_systems = self.emjson.get('distribution_systems', [])
        if not distribution_systems:
            # Try nested location (from GUI/v6 structure)
            distribution_systems = self.emjson.get('systems', {}).get('distribution_systems', [])

        if not distribution_systems:
            logger.debug("No distribution_systems in EMJSON")
            return

        logger.info(f"Writing {len(distribution_systems)} ResDistSys elements")

        for dist_obj in distribution_systems:
            dist = self._to_dict(dist_obj)
            # Build ResDistSys data
            dist_data = {
                'name': dist.get('name', 'Distribution System'),
            }

            # Distribution type
            dist_type = dist.get('distribution_type')
            if dist_type:
                dist_data['Type'] = dist_type

            # Duct location (if specified)
            duct_location = dist.get('duct_location')
            if duct_location:
                dist_data['DuctLoc'] = duct_location

            # Duct insulation R-value (if specified)
            r_value = dist.get('duct_insulation_r_value_SI')
            if r_value:
                # Convert SI to IP (multiply by 5.678)
                dist_data['DuctInsul'] = r_value * 5.678

            # Duct leakage percentage (if specified)
            leakage = dist.get('duct_leakage_pct')
            if leakage:
                dist_data['DuctLeakage'] = leakage

            # Write ResDistSys element
            lines = self.element_writer.write_element('ResDistSys', dist_data, indent=0)
            self.output_lines.extend(lines)
            self.output_lines.append('')  # Blank line after element

            logger.debug(f"Wrote ResDistSys: {dist_data['name']}")

        logger.info(f"Wrote {len(distribution_systems)} ResDistSys catalog elements")

    def _write_iaq_fans(self) -> None:
        """
        Write ResIAQFan catalog elements from iaq_fans in EMJSON.

        Converts IAQ fan definitions to CIBD25 ResIAQFan format.
        """
        # Check both root level and nested locations for iaq_fans
        iaq_fans = self.emjson.get('iaq_fans', [])
        if not iaq_fans:
            # Try nested location (from GUI/v6 structure)
            iaq_fans = self.emjson.get('systems', {}).get('iaq_fans', [])

        if not iaq_fans:
            logger.debug("No iaq_fans in EMJSON")
            return

        logger.info(f"Writing {len(iaq_fans)} ResIAQFan elements")

        for fan_obj in iaq_fans:
            fan = self._to_dict(fan_obj)
            # Build ResIAQFan data
            fan_data = {
                'name': fan.get('name', 'IAQ Fan'),
            }

            # Add properties from annotation and main properties
            annotation = fan.get('annotation', {})

            # IAQCFM (airflow in CFM)
            airflow = fan.get('airflow_cfm')
            if airflow:
                fan_data['IAQCFM'] = int(airflow)
            elif 'IAQCFM' in annotation:
                fan_data['IAQCFM'] = int(annotation['IAQCFM'])

            # WperCFMIAQ (power per CFM)
            power_per_cfm = fan.get('power_w')
            if power_per_cfm:
                fan_data['WperCFMIAQ'] = power_per_cfm
            elif 'WperCFMIAQ' in annotation:
                fan_data['WperCFMIAQ'] = float(annotation['WperCFMIAQ'])

            # IAQFanType (Exhaust, Supply, Balanced)
            # Only write if valid value exists (skip 'Unknown' default from parser)
            fan_type = fan.get('fan_type')
            if fan_type and fan_type != 'Unknown':
                fan_data['IAQFanType'] = fan_type
            elif 'IAQFanType' in annotation and annotation['IAQFanType'] != 'Unknown':
                fan_data['IAQFanType'] = annotation['IAQFanType']

            # IncludesRecov (heat recovery, 0 or 1)
            if 'IncludesRecov' in annotation:
                includes_recov = annotation['IncludesRecov']
                # Convert to int if string
                if isinstance(includes_recov, str):
                    fan_data['IncludesRecov'] = int(includes_recov)
                else:
                    fan_data['IncludesRecov'] = includes_recov

            # Write ResIAQFan element
            lines = self.element_writer.write_element('ResIAQFan', fan_data, indent=0)
            self.output_lines.extend(lines)
            self.output_lines.append('')  # Blank line after element

            logger.debug(f"Wrote ResIAQFan: {fan_data['name']}")

        logger.info(f"Wrote {len(iaq_fans)} ResIAQFan catalog elements")

    def _write_pv_arrays(self) -> None:
        """
        Write PVArray catalog elements from pv_arrays in EMJSON.

        Converts photovoltaic array definitions to CIBD25 PVArray format.
        """
        pv_arrays = self.emjson.get('pv_arrays', [])

        if not pv_arrays:
            logger.debug("No pv_arrays in EMJSON")
            return

        logger.info(f"Writing {len(pv_arrays)} PVArray elements")

        for pv_obj in pv_arrays:
            pv = self._to_dict(pv_obj)
            # Build PVArray data
            pv_data = {
                'name': pv.get('name', 'Photovoltaic Array'),
            }

            # Add properties from annotation
            annotation = pv.get('annotation', {})

            # DCSysSize (DC system size in kW)
            dc_sys_size = annotation.get('DCSysSize')
            if dc_sys_size:
                pv_data['DCSysSize'] = float(dc_sys_size)

            # ModuleType (Premium, Standard, etc.)
            module_type = pv.get('module_type')
            if module_type:
                pv_data['ModuleType'] = module_type
            elif 'ModuleType' in annotation:
                pv_data['ModuleType'] = annotation['ModuleType']

            # PwrElec (power electronics: Microinverters, String Inverters, etc.)
            if 'PwrElec' in annotation:
                pv_data['PwrElec'] = annotation['PwrElec']

            # Write PVArray element
            lines = self.element_writer.write_element('PVArray', pv_data, indent=0)
            self.output_lines.extend(lines)
            self.output_lines.append('')  # Blank line after element

            logger.debug(f"Wrote PVArray: {pv_data['name']}")

        logger.info(f"Wrote {len(pv_arrays)} PVArray catalog elements")

    def _write_batteries(self) -> None:
        """
        Write Batt catalog elements from batteries in EMJSON.

        Converts battery storage definitions to CIBD25 Batt format.

        Note: Fix #43 - Batt elements are skipped per property_rules because
        battery storage is not properly supported in CIBD25 text format.
        """
        # Check if Batt elements should be skipped (Fix #43)
        if should_skip_element('Batt'):
            logger.info("Skipping Batt elements (not supported in CIBD25 text format - Fix #43)")
            return

        batteries = self.emjson.get('batteries', [])

        if not batteries:
            logger.debug("No batteries in EMJSON")
            return

        logger.info(f"Writing {len(batteries)} Batt elements")

        for batt_obj in batteries:
            batt = self._to_dict(batt_obj)
            # Build Batt data
            batt_data = {
                'name': batt.get('name', 'Battery'),
            }

            # Add properties from annotation
            annotation = batt.get('annotation', {})

            # MaxCap (maximum capacity in kWh)
            max_cap = annotation.get('MaxCap')
            if max_cap:
                batt_data['MaxCap'] = float(max_cap)

            # Ctrl (control strategy: "Time of Use", "Load Following", etc.)
            ctrl = annotation.get('Ctrl')
            if ctrl:
                batt_data['Ctrl'] = ctrl

            # Write Batt element
            lines = self.element_writer.write_element('Batt', batt_data, indent=0)
            self.output_lines.extend(lines)
            self.output_lines.append('')  # Blank line after element

            logger.debug(f"Wrote Batt: {batt_data['name']}")

        logger.info(f"Wrote {len(batteries)} Batt catalog elements")

    def _write_zone_with_surfaces(self, zone: Dict[str, Any], surfaces: List[Dict[str, Any]], indent_level: int = 1) -> None:
        """
        Write a zone and its surfaces.

        Handles:
        - ResZn: Regular residential dwelling unit zones
        - ResOtherZn: Utility/common area zones with commercial HVAC linkages

        Args:
            zone: Zone data from EMJSON
            surfaces: List of surfaces for this zone
            indent_level: Indentation level (1 when inside ResZnGrp, 0 for standalone)
        """
        zone_type = zone.get('type', 'Conditioned')
        zone_name = zone.get('name', 'Zone')
        annotation = zone.get('annotation', {})

        # Determine element type from annotation xml_tag (most reliable)
        # Falls back to conditioning type if xml_tag not present
        xml_tag = annotation.get('xml_tag', '')
        if xml_tag == 'Spc':
            element_type = 'Spc'
        elif xml_tag == 'ResAttic':
            element_type = 'ResAttic'
        elif xml_tag == 'ResOtherZn':
            element_type = 'ResOtherZn'
        elif zone_type in ('Conditioned', 'Indirectly Conditioned'):
            element_type = 'ResZn'
        else:
            # Unconditioned spaces without explicit tag
            element_type = 'ResOtherZn'

        # Build basic zone data (different properties for Spc, ResAttic, vs ResZn/ResOtherZn)
        zone_data = {
            'name': zone_name,
        }

        # Add standard zone properties for ResZn and ResOtherZn (but not Spc or ResAttic)
        if element_type not in ('Spc', 'ResAttic'):
            zone_data['Type'] = zone_type
            zone_data['CeilingHeight'] = zone.get('floor_to_ceiling_height', 9)
            zone_data['FloorHeight'] = zone.get('floor_height', 9)
            zone_data['Bottom'] = zone.get('bottom_height', 0)

        # Add ResOtherZn-specific properties
        if element_type == 'ResOtherZn':
            # SpcFunc: Space function for code compliance (e.g., "Electrical, Mechanical, Telephone Rooms")
            if 'space_function' in zone and zone['space_function']:
                zone_data['SpcFunc'] = zone['space_function']

            # VentSpcFunc: DEPRECATED on ResOtherZn per Fix #41
            # This property causes DwellUnitType to not be recognized in CBECC 2025 GUI
            # Skipping per property_rules - do NOT add VentSpcFunc to ResOtherZn

            # ozHVACSystem: Commercial HVAC system reference (now safe - AirSys written before zones)
            if 'oz_hvac_sys' in annotation and annotation['oz_hvac_sys']:
                zone_data['ozHVACSystem'] = annotation['oz_hvac_sys']

            # ozDHWSys: Service hot water system reference
            if 'oz_dhw_sys' in annotation and annotation['oz_dhw_sys']:
                zone_data['ozDHWSys'] = annotation['oz_dhw_sys']

            # Area: Explicit floor area in ft² (ResOtherZn uses 'Area' not 'FloorArea')
            if 'original_area_ft' in annotation:
                zone_data['Area'] = annotation['original_area_ft']
            elif zone.get('floor_area_m2'):
                # Convert from m² to ft²
                zone_data['Area'] = zone['floor_area_m2'] * 10.7639

            # IAQ/Ventilation properties (from iaq_config in annotation)
            if 'iaq_option' in annotation and annotation['iaq_option']:
                zone_data['IAQOption'] = annotation['iaq_option']
            if 'iaq_fan_ref' in annotation and annotation['iaq_fan_ref']:
                zone_data['IAQFanRef[1]'] = annotation['iaq_fan_ref']
            if 'central_vent_sys_ref' in annotation and annotation['central_vent_sys_ref']:
                zone_data['CentralVentSysRef'] = annotation['central_vent_sys_ref']
            if 'central_supply_cfm' in annotation and annotation['central_supply_cfm']:
                zone_data['CentralSupplyCFM'] = annotation['central_supply_cfm']
            if 'central_exhaust_cfm' in annotation and annotation['central_exhaust_cfm']:
                zone_data['CentralExhaustCFM'] = annotation['central_exhaust_cfm']

        # Add ResAttic-specific properties
        elif element_type == 'ResAttic':
            # ResAttic zones have unique roof properties
            if 'RoofRise' in annotation:
                zone_data['RoofRise'] = annotation['RoofRise']

            if 'Construction' in annotation:
                zone_data['Construction'] = annotation['Construction']

            if 'RoofSolReflect' in annotation:
                zone_data['RoofSolReflect'] = annotation['RoofSolReflect']

        # Add Spc-specific properties (commercial spaces)
        elif element_type == 'Spc':
            # CondgType: Conditioning type (e.g., "DirectlyConditioned", "Unconditioned")
            if 'conditioning_type' in annotation:
                zone_data['CondgType'] = annotation['conditioning_type']

            # ThrmlZnRef: Reference to thermal zone (HVAC grouping)
            if 'ThrmlZnRef' in annotation:
                zone_data['ThrmlZnRef'] = annotation['ThrmlZnRef']

            # Area: Floor area in ft² (explicit area, NOT calculated from geometry)
            # IMPORTANT: Area must be numeric (not quoted string) in CIBD25
            # Some source files define Area instead of Vol - we need to export both when present
            if 'original_area_ft' in annotation:
                # Use original area for round-trip fidelity
                area_val = annotation['original_area_ft']
                if isinstance(area_val, str):
                    try:
                        zone_data['Area'] = float(area_val)
                    except (ValueError, TypeError):
                        logger.warning(f"Could not convert Area '{area_val}' to float")
                else:
                    zone_data['Area'] = area_val
            elif zone.get('floor_area_m2'):
                # Convert from m² to ft²: 1 m² = 10.7639 ft²
                zone_data['Area'] = zone['floor_area_m2'] * 10.7639

            # Vol: Volume in ft³ (use original value for round-trip fidelity)
            # IMPORTANT: Vol must be numeric (not quoted string) in CIBD25
            if 'original_vol_ft3' in annotation:
                # Convert to float if it's a string
                vol_val = annotation['original_vol_ft3']
                if isinstance(vol_val, str):
                    try:
                        zone_data['Vol'] = float(vol_val)
                    except (ValueError, TypeError):
                        logger.warning(f"Could not convert Vol '{vol_val}' to float")
                else:
                    zone_data['Vol'] = vol_val
            elif zone.get('volume_m3') is not None:
                # Convert m³ to ft³: 1 m³ = 35.3147 ft³
                zone_data['Vol'] = zone['volume_m3'] * 35.3147

            # SpcFuncDefaultsRef: Space function defaults reference
            # Generate reference to SpcFuncDefaults catalog entry
            # The catalog entry maps simplified names to full Title 24 space function strings
            spc_func = annotation.get('SpcFunc') or zone.get('space_function')
            if spc_func:
                # Generate the same simplified name we used in the catalog
                defaults_name = self._generate_spc_func_defaults_name(spc_func)
                zone_data['SpcFuncDefaultsRef'] = defaults_name

            # SpcFunc: Specific space function (can be empty)
            # Skip for now (related to SpcFuncDefaultsRef)
            # if 'space_function' in zone and zone['space_function']:
            #     defaults_ref = zone_data.get('SpcFuncDefaultsRef', '')
            #     if zone['space_function'] != defaults_ref:
            #         zone_data['SpcFunc'] = zone['space_function']

            # SHWFluidSegRef: Service hot water fluid segment reference
            if 'SHWFluidSegRef' in annotation:
                zone_data['SHWFluidSegRef'] = annotation['SHWFluidSegRef']

            # ParentStoryRef: Story parent reference
            # CRITICAL: Spc elements MUST reference their parent Story
            # Without this, CBECC will fail with ParentStoryRef errors
            if 'ParentStoryRef' in annotation:
                zone_data['ParentStoryRef'] = annotation['ParentStoryRef']

            # OccSensorCtrl: Occupancy sensor control (0 or 1)
            # IMPORTANT: Must be numeric (not quoted string) in CIBD25
            if 'OccSensorCtrl' in annotation:
                occ_val = annotation['OccSensorCtrl']
                if isinstance(occ_val, str):
                    try:
                        zone_data['OccSensorCtrl'] = int(occ_val)
                    except (ValueError, TypeError):
                        logger.warning(f"Could not convert OccSensorCtrl '{occ_val}' to int")
                else:
                    zone_data['OccSensorCtrl'] = occ_val

        logger.debug(f"Writing {element_type} zone: {zone_name} at indent level {indent_level}")

        # CIBD25 Structure:
        # - Spc zones: Write Spc element, close it, then write surfaces at ROOT LEVEL
        # - ResZn zones: Write ResZn element, close it, then write surfaces at ROOT LEVEL
        # Surfaces are NEVER nested inside zone elements in CIBD25!

        if element_type == 'Spc':
            # Commercial space - write Spc with properties only, then close it
            indent_str = '   ' * indent_level
            prop_indent = '   ' * (indent_level + 1)

            # Write Spc header
            self.output_lines.append(f'{indent_str}Spc   "{zone_name}"')

            # Write Spc properties
            for key, value in zone_data.items():
                if key == 'name' or value is None:
                    continue
                # Format value (quote strings, leave numbers as-is)
                if isinstance(value, str):
                    formatted_value = f'"{value}"'
                else:
                    formatted_value = str(value)
                self.output_lines.append(f'{prop_indent}{key} = {formatted_value}')

            # Close Spc element immediately (no nested surfaces)
            self.output_lines.append(f'{indent_str}..')
            self.output_lines.append('')

            # Write zone floor polygon PolyLp geometry at root level
            # CONFIRMED: Reference files DO have floor PolyLp for EVERY Spc element
            # Example from 080012-Whse-CECStd.cibd25: All 3 Spc elements have floor polygons
            vertices = zone.get('vertices')
            if vertices and len(vertices) >= 3:
                self.polylp_counter += 1
                self._write_polylp_geometry(vertices, self.polylp_counter, indent_level=0)
                logger.debug(f"Wrote floor polygon PolyLp {self.polylp_counter} for Spc '{zone_name}' with {len(vertices)} vertices")

            # Write commercial surfaces at root level with PolyLp geometry
            # Commercial surfaces are written at root level (indent_level=0) in CIBD25
            logger.info(f"Writing {len(surfaces)} commercial surfaces for Spc '{zone_name}' with PolyLp geometry")

            for surface in surfaces:
                self._write_surface(surface, indent_level=0)

                # Write openings for this surface
                surface_id = surface.get('id')
                if surface_id:
                    openings = self._get_openings_for_surface(surface_id)
                    for opening in openings:
                        self._write_opening(opening, indent_level=0, is_commercial=True)

            return  # Done with Spc

        # For residential zones: filter properties per V7 rules before writing
        # This ensures deprecated properties like VentSpcFunc, PVBattSizeBldgType, etc.
        # are removed even if they were in the source data
        zone_data = filter_properties(element_type, zone_data)

        # Use standard element_writer (auto-closes)
        lines = self.element_writer.write_element(element_type, zone_data, indent=indent_level)
        self.output_lines.extend(lines)

        # Close residential zone element
        self.output_lines.append('')

        # Per MF88Unit reference: ResExtWall, ResWin, DwellUnit are ALL at ROOT LEVEL
        # (not nested inside ResZn!)
        # So we write them all at indent_level=0 regardless of zone indent

        # IMPORTANT: Ordering matters for CBECC GUI display!
        # Correct order (from MF88Unit reference):
        # 1. ResZn
        # 2. Exterior surfaces (ResExtWall with windows)
        # 3. DwellUnit (with zone refs so CBECC associates it with the zone)
        # 4. Interior surfaces (ResIntWall, ResIntFlr, etc.)

        # Separate surfaces by type
        exterior_surfaces = []
        interior_surfaces = []
        for surface in surfaces:
            surf_type = surface.get('type', surface.get('surface_subtype', ''))
            # Map CBECC subtype names
            type_mapping = {
                'res_ext_wall': 'ExteriorWall',
                'res_int_wall': 'InteriorWall',
                'res_slab_floor': 'SlabFloor',
                'res_int_floor': 'InteriorFloor',
                'res_roof': 'Roof',
            }
            surf_type = type_mapping.get(surf_type, surf_type)

            if surf_type in ('ExteriorWall', 'Roof', 'SlabFloor'):
                exterior_surfaces.append(surface)
            else:
                interior_surfaces.append(surface)

        # Write exterior surfaces first
        for surface in exterior_surfaces:
            self._write_surface(surface, indent_level=0)
            surface_id = surface.get('id')
            if surface_id:
                openings = self._get_openings_for_surface(surface_id)
                for opening in openings:
                    self._write_opening(opening, indent_level=0)

        # Write DwellUnit AFTER exterior surfaces, BEFORE interior surfaces
        annotation = zone.get('annotation', {})
        dwelling_unit = annotation.get('dwelling_unit')
        if dwelling_unit:
            self._write_dwelling_unit(dwelling_unit, zone_name, zone, indent_level=0)
            logger.debug(f"Wrote DwellUnit for zone: {zone_name}")

        # Write interior surfaces last
        for surface in interior_surfaces:
            self._write_surface(surface, indent_level=0)
            surface_id = surface.get('id')
            if surface_id:
                openings = self._get_openings_for_surface(surface_id)
                for opening in openings:
                    self._write_opening(opening, indent_level=0)

    def _write_surface(self, surface: Dict[str, Any], indent_level: int = 0) -> None:
        """
        Write a surface element (wall, window, floor, roof, door, etc.).

        Handles both residential and commercial surfaces:

        RESIDENTIAL:
        - ExteriorWall / res_ext_wall → ResExtWall
        - InteriorWall / res_int_wall → ResIntWall
        - Window → ResWin
        - Door → ResDr
        - SlabFloor / res_slab_floor → ResSlabFlr
        - Roof / res_roof → ResRoof
        - CathedralCeiling / res_cathedral_ceiling → ResCathedralCeiling

        COMMERCIAL:
        - ExtWall → ExtWall (uses PolyLp, no explicit area)
        - IntWall → IntWall
        - Roof → Roof
        - UndgrFlr → UndgrFlr
        - Win → Win
        - Dr → Dr
        - Skylt → Skylt

        Args:
            surface: Surface data from EMJSON
        """
        surf_name = surface.get('name', 'Surface')
        annotation = surface.get('annotation', {})

        # Determine if this is a commercial or residential surface
        # Commercial surfaces have xml_tag like 'ExtWall', 'IntWall', etc.
        # Residential surfaces have xml_tag like 'ResExtWall', 'ResIntWall', etc.
        xml_tag = annotation.get('xml_tag', '')

        # Commercial surface tags (no 'Res' prefix)
        commercial_tags = ['ExtWall', 'IntWall', 'Roof', 'ExtFlr', 'IntFlr',
                          'UndgrWall', 'UndgrFlr', 'Win', 'Dr', 'Skylt']

        if xml_tag in commercial_tags:
            # Commercial surface - write using xml_tag directly
            self._write_commercial_surface(surface, xml_tag, surf_name, indent_level)
            return

        # Residential surface - use existing logic
        # Check both 'type' (old format) and 'surface_subtype' (EMJSON from importer)
        surf_type = surface.get('type', surface.get('surface_subtype', ''))

        # Map CBECC subtype names to standard types
        type_mapping = {
            'res_ext_wall': 'ExteriorWall',
            'res_int_wall': 'InteriorWall',
            'res_undergr_wall': 'UndergroundWall',
            'res_slab_floor': 'SlabFloor',
            'res_int_floor': 'InteriorFloor',
            'res_roof': 'Roof',
            'res_cathedral_ceiling': 'CathedralCeiling',
            'res_ceiling_below_attic': 'CeilingBelowAttic',
        }
        surf_type = type_mapping.get(surf_type, surf_type)

        if surf_type == 'ExteriorWall':
            # Get area - check both area_m2 (EMJSON) and area (old format)
            # Convert m² to ft² if needed (× 10.7639)
            area_m2 = surface.get('area_m2', surface.get('area', 100))
            area_ft2 = area_m2 * 10.7639 if area_m2 else 100

            # Get orientation from annotation or direct field
            orientation = surface.get('annotation', {}).get('orientation',
                         surface.get('orientation', 'Front'))

            # Resolve construction reference to actual catalog name
            construction_ref = surface.get('construction_ref', surface.get('construction', ''))
            construction_name = self._resolve_construction_ref(construction_ref, 'Standard Exterior Wall')

            surf_data = {
                'name': surf_name,
                'Orientation': orientation,
                'Area': area_ft2,
                'Construction': construction_name,
            }
            lines = self.element_writer.write_element('ResExtWall', surf_data, indent=indent_level)

        elif surf_type == 'InteriorWall':
            # Get area - convert m² to ft² if needed
            area_m2 = surface.get('area_m2', surface.get('area', 100))
            area_ft2 = area_m2 * 10.7639 if area_m2 else 100

            # Resolve construction reference to actual catalog name
            construction_ref = surface.get('construction_ref', surface.get('construction', ''))
            construction_name = self._resolve_construction_ref(construction_ref, 'Standard Interior Wall')

            surf_data = {
                'name': surf_name,
                'Area': area_ft2,
                'Construction': construction_name,
            }
            # Add optional properties
            if 'is_party_surface' in surface:
                surf_data['IsPartySurface'] = 1 if surface['is_party_surface'] else 0
            if surface.get('adjacent_space_ref'):  # EMJSON field name
                surf_data['Outside'] = surface['adjacent_space_ref']
            elif 'adjacent_zone' in surface:  # Old format
                surf_data['Outside'] = surface['adjacent_zone']
            lines = self.element_writer.write_element('ResIntWall', surf_data, indent=indent_level)

        elif surf_type == 'UndergroundWall':
            # Underground wall (below grade)
            # Get area - convert m² to ft² if needed
            area_m2 = surface.get('area_m2', surface.get('area', 100))
            area_ft2 = area_m2 * 10.7639 if area_m2 else 100

            # Resolve construction reference to actual catalog name
            construction_ref = surface.get('construction_ref', surface.get('construction', ''))
            construction_name = self._resolve_construction_ref(construction_ref, 'Undergrd Wall Cons')

            surf_data = {
                'name': surf_name,
                'Area': area_ft2,
                'Construction': construction_name,
            }
            # Add optional properties
            if 'depth_below_grade' in surface:
                surf_data['DepthBelowGrade'] = surface['depth_below_grade']
            elif 'annotation' in surface and 'DepthBelowGrade' in surface['annotation']:
                surf_data['DepthBelowGrade'] = surface['annotation']['DepthBelowGrade']
            lines = self.element_writer.write_element('ResUndgrWall', surf_data, indent=indent_level)

        elif surf_type == 'Window':
            surf_data = {
                'name': surf_name,
                'Area': surface.get('area', 10),
                'FenConsRef': surface.get('fenestration', 'Standard Fixed Window'),
            }
            lines = self.element_writer.write_element('ResWin', surf_data, indent=indent_level)

        elif surf_type == 'Door':
            surf_data = {
                'name': surf_name,
                'Area': surface.get('area', 20),
                'FenConsRef': surface.get('fenestration', 'Standard Glazed Door'),
            }
            lines = self.element_writer.write_element('ResDr', surf_data, indent=indent_level)

        elif surf_type == 'SlabFloor':
            # Get area and perimeter - convert m to ft if needed
            area_m2 = surface.get('area_m2', surface.get('area', 100))
            area_ft2 = area_m2 * 10.7639 if area_m2 else 100

            perimeter_m = surface.get('perimeter_m', surface.get('perimeter', 40))
            perimeter_ft = perimeter_m * 3.28084 if perimeter_m else 40

            surf_data = {
                'name': surf_name,
                'Area': area_ft2,
                'Perimeter': perimeter_ft,
            }
            lines = self.element_writer.write_element('ResSlabFlr', surf_data, indent=indent_level)

        elif surf_type == 'InteriorFloor':
            # Get area - convert m² to ft² if needed
            area_m2 = surface.get('area_m2', surface.get('area', 100))
            area_ft2 = area_m2 * 10.7639 if area_m2 else 100

            # Resolve construction reference to actual catalog name
            construction_ref = surface.get('construction_ref', surface.get('construction', ''))
            construction_name = self._resolve_construction_ref(construction_ref, 'Standard Interior Floor')

            surf_data = {
                'name': surf_name,
                'Area': area_ft2,
                'Construction': construction_name,
            }
            # Add optional properties
            # Note: ResIntFlr uses 'Outside' property (not 'AdjacentZone') to reference adjacent zone
            if surface.get('adjacent_space_ref'):  # EMJSON field name
                surf_data['Outside'] = surface['adjacent_space_ref']
            elif 'adjacent_zone' in surface:  # Old format
                surf_data['Outside'] = surface['adjacent_zone']
            lines = self.element_writer.write_element('ResIntFlr', surf_data, indent=indent_level)

        elif surf_type == 'Roof':
            # Get area - convert m² to ft² if needed
            area_m2 = surface.get('area_m2', surface.get('area', 100))
            area_ft2 = area_m2 * 10.7639 if area_m2 else 100

            # Get orientation from annotation or direct field
            orientation = surface.get('annotation', {}).get('orientation',
                         surface.get('orientation'))

            # Resolve construction reference to actual catalog name
            construction_ref = surface.get('construction_ref', surface.get('construction', ''))
            construction_name = self._resolve_construction_ref(construction_ref, 'Standard Roof')

            surf_data = {
                'name': surf_name,
                'Area': area_ft2,
                'Construction': construction_name,
            }
            # Add optional properties
            if 'orientation' in surface:
                surf_data['Orientation'] = surface['orientation']
            if 'roof_rise' in surface:
                surf_data['RoofRise'] = surface['roof_rise']
            if 'solar_reflectance' in surface:
                surf_data['RoofSolReflect'] = surface['solar_reflectance']
            lines = self.element_writer.write_element('ResRoof', surf_data, indent=indent_level)

        elif surf_type == 'CathedralCeiling':
            # Resolve construction reference to actual catalog name
            construction_ref = surface.get('construction_ref', surface.get('construction', ''))
            construction_name = self._resolve_construction_ref(construction_ref, 'Standard Roof')

            surf_data = {
                'name': surf_name,
                'Area': surface.get('area', 100),
                'Construction': construction_name,
            }
            # Add optional properties
            if 'orientation' in surface:
                surf_data['Orientation'] = surface['orientation']
            if 'roof_rise' in surface:
                surf_data['RoofRise'] = surface['roof_rise']
            if 'solar_reflectance' in surface:
                surf_data['RoofSolReflect'] = surface['solar_reflectance']
            lines = self.element_writer.write_element('ResCathedralCeiling', surf_data, indent=indent_level)

        elif surf_type == 'CeilingBelowAttic':
            # Ceiling surface separating conditioned space from unconditioned attic
            # Get area - convert m² to ft² if needed
            area_m2 = surface.get('area_m2', surface.get('area', 100))
            area_ft2 = area_m2 * 10.7639 if area_m2 else 100

            # Resolve construction reference to actual catalog name
            construction_ref = surface.get('construction_ref', surface.get('construction', ''))
            construction_name = self._resolve_construction_ref(construction_ref, 'Ceiling Below Attic Cons')

            surf_data = {
                'name': surf_name,
                'Area': area_ft2,
                'Construction': construction_name,
            }
            lines = self.element_writer.write_element('ResCeilingBelowAttic', surf_data, indent=indent_level)

        else:
            logger.warning(f"Unknown surface type: {surf_type}")
            return

        self.output_lines.extend(lines)
        self.output_lines.append('')

    def _write_minimal_test_building(self) -> None:
        """Write minimal test building structure (used when no geometry data available)."""
        # ResZnGrp (floor)
        floor_data = {
            'name': 'First Floor',
            'Z': 0,
            'FlrToFlrHgt': 10,
            'FlrToCeilingHgt': 9,
        }
        lines = self.element_writer.write_element('ResZnGrp', floor_data, indent=0)
        self.output_lines.extend(lines)
        self.output_lines.append('')

        # ResZn (zone)
        zone_data = {
            'name': 'Living Space',
            'Type': 'Conditioned',
            'CeilingHeight': 9,
            'FloorHeight': 9,
            'Bottom': 0,
        }
        lines = self.element_writer.write_element('ResZn', zone_data, indent=0)
        self.output_lines.extend(lines)
        self.output_lines.append('')

        # ResExtWall (exterior wall)
        wall_data = {
            'name': 'ExtWall (Front 1) : Living Space',
            'Orientation': 'Front',
            'Area': 100,
            'Construction': 'Standard Exterior Wall',
        }
        lines = self.element_writer.write_element('ResExtWall', wall_data, indent=0)
        self.output_lines.extend(lines)
        self.output_lines.append('')

        # ResWin (window)
        window_data = {
            'name': 'Window (Front 1) : Living Space',
            'Area': 15,
            'FenConsRef': 'Standard Fixed Window',
        }
        lines = self.element_writer.write_element('ResWin', window_data, indent=0)
        self.output_lines.extend(lines)
        self.output_lines.append('')

        # ResSlabFlr (slab floor)
        floor_slab_data = {
            'name': 'SlabFlr : Living Space',
            'Area': 500,
            'Perimeter': 90,
        }
        lines = self.element_writer.write_element('ResSlabFlr', floor_slab_data, indent=0)
        self.output_lines.extend(lines)
        self.output_lines.append('')

    def _ensure_commercial_catalogs(self) -> None:
        """
        Ensure commercial catalogs are present.

        This fixes the 101 "Invalid component type" errors by ensuring
        Mat, ConsAssm, and FenCons catalogs are always included.

        Strategy:
        1. Get default commercial catalogs from catalog_builder
        2. Merge with any catalogs from EMJSON (EMJSON takes precedence)
        3. Store in self.catalogs for writing
        """
        logger.info("Ensuring commercial catalogs are present")

        # Get default catalogs
        default_catalogs = build_default_commercial_catalogs()

        # Merge with EMJSON catalogs (EMJSON takes precedence)
        emjson_catalogs = self.emjson.get('catalogs', {})

        # DEBUG: Write to file at the very beginning
        try:
            with open('/Users/DavidM/Downloads/construction_debug.txt', 'w') as f:
                f.write("=== CATALOG MERGE DEBUG ===\n\n")
                f.write(f"EMJSON catalog keys: {list(emjson_catalogs.keys())}\n")
                f.write(f"Default catalog keys: {list(default_catalogs.keys())}\n\n")
                for cat_name in emjson_catalogs.keys():
                    cat_items = emjson_catalogs[cat_name]
                    f.write(f"\nCatalog '{cat_name}': {len(cat_items) if cat_items else 0} items\n")
                    if cat_items and len(cat_items) > 0:
                        first_item = cat_items[0]
                        item_dict = self._to_dict(first_item)
                        f.write(f"  First item keys: {list(item_dict.keys())}\n")
                        f.write(f"  First item id: {item_dict.get('id', 'NO ID')}\n")
                        f.write(f"  First item name: {item_dict.get('name', 'NO NAME')}\n")
                f.write(f"\nDefault ConsAssm count: {len(default_catalogs.get('ConsAssm', []))}\n")
                if default_catalogs.get('ConsAssm'):
                    f.write(f"Default ConsAssm names: {[c.get('name', 'NO NAME') for c in default_catalogs['ConsAssm'][:3]]}\n")
        except Exception as e:
            logger.error(f"Failed to write debug file: {e}")

        # Start with defaults
        self.catalogs = default_catalogs.copy()

        # Override with EMJSON catalogs if they exist
        # For ConsAssm and Mat: if EMJSON has these, REPLACE defaults (don't append)
        # This prevents mixing default constructions with project-specific ones
        logger.warning(f"EMJSON catalog keys: {list(emjson_catalogs.keys())}")
        for cat_name, cat_items in emjson_catalogs.items():
            if not cat_items:  # Skip empty lists
                logger.warning(f"Skipping empty catalog: {cat_name}")
                continue

            logger.warning(f"Processing catalog {cat_name} with {len(cat_items)} items")

            # Map EMJSON catalog names to CIBD25 catalog names
            # EMJSON uses 'constructions', 'materials', CIBD25 uses 'ConsAssm', 'Mat'
            target_catalog = cat_name
            if cat_name == 'constructions':
                target_catalog = 'ConsAssm'
            elif cat_name == 'materials':
                target_catalog = 'Mat'

            # For constructions and materials: replace defaults if EMJSON has them
            if cat_name in ('ConsAssm', 'Mat', 'constructions', 'materials') and len(cat_items) > 0:
                logger.warning(f"REPLACING defaults for {target_catalog} (from EMJSON '{cat_name}') with {len(cat_items)} items")
                # DEBUG: Record what we're replacing
                try:
                    with open('/Users/DavidM/Downloads/construction_debug.txt', 'a') as f:
                        f.write(f"\n>>> REPLACEMENT for catalog '{cat_name}' → '{target_catalog}'\n")
                        f.write(f"    Before clear: {len(self.catalogs.get(target_catalog, []))} items\n")
                        if self.catalogs.get(target_catalog):
                            f.write(f"    Before names: {[c.get('name', 'NO NAME') for c in self.catalogs[target_catalog][:3]]}\n")
                except:
                    pass
                self.catalogs[target_catalog] = []  # Clear defaults, use EMJSON only
                # DEBUG: Confirm clear
                try:
                    with open('/Users/DavidM/Downloads/construction_debug.txt', 'a') as f:
                        f.write(f"    After clear: {len(self.catalogs[target_catalog])} items\n")
                except:
                    pass

            if target_catalog not in self.catalogs:
                self.catalogs[target_catalog] = []

            # Convert items to dicts and add them
            for item in cat_items:
                item_dict = self._to_dict(item)
                self.catalogs[target_catalog].append(item_dict)

                # Build ID/ref → name mappings for round-trip fidelity
                if cat_name == 'ConsAssm' or cat_name == 'constructions':
                    # Map both id and name to name (for various reference formats)
                    cons_id = item_dict.get('id', '')
                    cons_name = item_dict.get('name', '')

                    # Also check annotation for alternate references
                    annotation = item_dict.get('annotation', {})
                    cons_ref = annotation.get('original_name', annotation.get('construction_ref', ''))

                    # DEBUG: Print first construction to understand structure
                    if len(self.construction_name_map) == 0:
                        logger.warning(f"FIRST CONSTRUCTION: id='{cons_id}', name='{cons_name}', annotation={annotation}")
                        # Also write to a debug file
                        try:
                            with open('/Users/DavidM/Downloads/construction_debug.txt', 'a') as f:
                                f.write(f"\n\nConstruction from catalog '{cat_name}':\n")
                                f.write(f"id: {cons_id}\n")
                                f.write(f"name: {cons_name}\n")
                                f.write(f"annotation: {annotation}\n")
                                f.write(f"Full item_dict: {item_dict}\n")
                        except:
                            pass

                    if cons_id and cons_name:
                        self.construction_name_map[cons_id] = cons_name
                        self.construction_name_map[cons_name] = cons_name  # identity mapping
                        if cons_ref and cons_ref != cons_id and cons_ref != cons_name:
                            self.construction_name_map[cons_ref] = cons_name  # map original ref too
                            logger.debug(f"Added alternate mapping: '{cons_ref}' → '{cons_name}'")

                elif cat_name == 'window_types' or cat_name == 'FenCons':
                    # Map window type IDs to names
                    wt_id = item_dict.get('id', '')
                    wt_name = item_dict.get('name', '')
                    if wt_id and wt_name:
                        self.window_type_name_map[wt_id] = wt_name
                        self.window_type_name_map[wt_name] = wt_name  # identity mapping

        logger.info(f"Commercial catalogs ready: {len(self.catalogs['Mat'])} Mat, "
                   f"{len(self.catalogs['ConsAssm'])} ConsAssm, "
                   f"{len(self.catalogs['FenCons'])} FenCons")
        logger.debug(f"Built construction name map with {len(self.construction_name_map)} entries")
        logger.debug(f"Construction map keys: {list(self.construction_name_map.keys())}")
        logger.debug(f"Built window type name map with {len(self.window_type_name_map)} entries")

        # DEBUG: Write final catalog state to debug file
        try:
            with open('/Users/DavidM/Downloads/construction_debug.txt', 'a') as f:
                f.write("\n\n=== FINAL CATALOG STATE ===\n")
                f.write(f"Final ConsAssm count: {len(self.catalogs['ConsAssm'])}\n")
                f.write("Final ConsAssm names:\n")
                for cons in self.catalogs['ConsAssm']:
                    cons_name = cons.get('name', 'NO NAME')
                    cons_id = cons.get('id', 'NO ID')
                    f.write(f"  - '{cons_name}' (id: {cons_id})\n")
                f.write(f"\nConstruction name map ({len(self.construction_name_map)} entries):\n")
                for key, value in list(self.construction_name_map.items())[:10]:
                    f.write(f"  '{key}' → '{value}'\n")
        except Exception as e:
            logger.error(f"Failed to append to debug file: {e}")

    def _write_hvac_systems(self) -> None:
        """
        Write HVAC and DHW systems from EMJSON.

        Systems in EMJSON v6 are in the 'systems' section:
        - systems.hvac: HVAC system instances
        - systems.dhw: DHW system instances
        - systems.water_heaters: Water heater catalog

        Equipment catalogs may be at root level:
        - heat_pumps: Heat pump equipment
        - fan_systems: Fan equipment
        - distribution_systems: Distribution systems
        - iaq_fans: IAQ fans

        This method writes:
        1. Equipment catalogs (if present)
        2. ResWtrHtr catalog (water heaters)
        3. ResHVACSys instances
        4. ResDHWSys instances
        """
        systems = self.emjson.get('systems', {})

        # Write water heater catalog (must come before DHW systems that reference them)
        self._write_water_heaters(systems.get('water_heaters', []))

        # Write ResHVACSys instances
        hvac_systems = systems.get('hvac', [])

        if not hvac_systems:
            logger.debug("No hvac_systems in EMJSON")
        else:
            logger.info(f"Writing {len(hvac_systems)} ResHVACSys elements")

            for hvac_obj in hvac_systems:
                hvac = self._to_dict(hvac_obj)
                # Build ResHVACSys data
                hvac_data = {
                    'name': hvac.get('name', 'HVAC System'),
                }

                # Get annotation for additional properties
                annotation = hvac.get('annotation', {})

                # System type (required)
                system_type = hvac.get('type')
                if system_type:
                    # Check if we have text representation
                    if 'system_type_text' in annotation:
                        hvac_data['Type'] = annotation['system_type_text']
                    else:
                        # Map integer type to text
                        type_map = {
                            1: 'Heating System',
                            2: 'Heat Pump Heating and Cooling System',
                            3: 'Cooling System',
                            4: 'Other Heating and Cooling System'
                        }
                        hvac_data['Type'] = type_map.get(system_type, 'Other Heating and Cooling System')

                # Status (required)
                status = hvac.get('status')
                if status:
                    # Check if we have text representation
                    if 'status_text' in annotation:
                        hvac_data['Status'] = annotation['status_text']
                    else:
                        # Map integer status to text
                        status_map = {
                            1: 'Existing',
                            2: 'Altered',
                            3: 'New'
                        }
                        hvac_data['Status'] = status_map.get(status, 'New')

                # Write all annotation properties except metadata
                # This preserves CIBD25-specific HVAC properties like:
                # - CFIClVentOption, CFIClVentFlow, CFIClVentPwr
                # - NumHeatSystemTypes, HeatSystemCount[n], HeatSystem[n], HeatDucted
                # - NumCoolSystemTypes, CoolSystemCount[n], CoolSystem[n], CoolDucted
                # - NumHtPumpSystemTypes, HtPumpSystemCount[n], HtPumpSystem[n], HtPumpDucted
                # - Fan, DistribSystem, etc.
                for prop, value in annotation.items():
                    # Skip EMJSON metadata and EMJSON-specific properties
                    if prop not in ['xml_tag', 'system_type_text', 'status_text',
                                    'segment_type', 'has_heating_coil', 'has_cooling_coil',
                                    'heating_coils', 'cooling_coils', 'fans',
                                    'ht_pump_system_refs', 'heat_system_refs', 'cool_system_refs']:
                        hvac_data[prop] = value

                # Also check for direct references if not in annotation
                # Heat pump systems (if present)
                heat_pump_systems = hvac.get('heat_pump_systems', [])
                heat_pump_counts = hvac.get('heat_pump_counts', [])

                # Write heat pump system references
                if heat_pump_systems and 'HtPumpSystem' not in hvac_data:
                    for i, hp_name in enumerate(heat_pump_systems):
                        hvac_data[f'HtPumpSystem[{i+1}]'] = hp_name
                        if i < len(heat_pump_counts):
                            hvac_data[f'HtPumpSystemCount[{i+1}]'] = heat_pump_counts[i]

                # Fan system reference
                fan_ref = hvac.get('fan_ref')
                if fan_ref and 'Fan' not in hvac_data:
                    hvac_data['Fan'] = fan_ref

                # Distribution system reference
                dist_ref = hvac.get('distribution_ref')
                if dist_ref and 'DistribSystem' not in hvac_data:
                    hvac_data['DistribSystem'] = dist_ref

                # Write ResHVACSys element
                lines = self.element_writer.write_element('ResHVACSys', hvac_data, indent=0)
                self.output_lines.extend(lines)
                self.output_lines.append('')  # Blank line after element

                logger.debug(f"Wrote ResHVACSys: {hvac_data['name']}")

            logger.info(f"Wrote {len(hvac_systems)} ResHVACSys elements")

        # Write ResDHWSys instances
        dhw_systems = systems.get('dhw', [])

        if not dhw_systems:
            logger.debug("No dhw_systems in EMJSON")
        else:
            logger.info(f"Writing {len(dhw_systems)} ResDHWSys elements")

            for dhw_obj in dhw_systems:
                dhw = self._to_dict(dhw_obj)
                # Build ResDHWSys data
                dhw_data = {
                    'name': dhw.get('name', 'DHW System'),
                }

                # Get annotation for additional properties
                annotation = dhw.get('annotation', {})

                # Write all annotation properties except EMJSON metadata
                # This preserves CIBD25-specific DHW properties like:
                # - CentralDHWType, CentralRecircType, CHPWHLoopTankConfig
                # - CHPWHSysDescrip, CHPWHCompType, CHPWHSrcAirLoc, etc.
                for prop, value in annotation.items():
                    # Skip EMJSON metadata
                    if prop not in ['xml_tag']:
                        dhw_data[prop] = value

                # Water heater references (CBECC 2025 uses DHWHeater[n] format, not WtrHtr)
                water_heaters = dhw.get('water_heaters', [])
                water_heater_counts = dhw.get('water_heater_counts', [])

                # Write water heater references using CBECC 2025 format: DHWHeater[1], DHWHeater[2], etc.
                if water_heaters and 'DHWHeater' not in dhw_data:
                    for i, wh_name in enumerate(water_heaters):
                        # CBECC uses 1-based indexing: DHWHeater[1], DHWHeater[2], etc.
                        dhw_data[f'DHWHeater[{i+1}]'] = wh_name

                        # Add count if available (HeaterMult[n] format)
                        if i < len(water_heater_counts):
                            dhw_data[f'HeaterMult[{i+1}]'] = water_heater_counts[i]
                        else:
                            dhw_data[f'HeaterMult[{i+1}]'] = 1  # Default to 1

                # Write ResDHWSys element
                lines = self.element_writer.write_element('ResDHWSys', dhw_data, indent=0)
                self.output_lines.extend(lines)
                self.output_lines.append('')  # Blank line after element

                logger.debug(f"Wrote ResDHWSys: {dhw_data['name']}")

            logger.info(f"Wrote {len(dhw_systems)} ResDHWSys elements")

    def _write_water_heaters(self, water_heaters: List[Dict[str, Any]]) -> None:
        """
        Write all ResWtrHtr (water heater) catalog elements.

        Args:
            water_heaters: List of water heater data from systems.water_heaters

        EMJSON v6 properties:
        - id: unique identifier
        - name: descriptive name
        - heater_type: "Gas", "Electric", "HeatPump", "Solar"
        - tank_type: storage type
        - storage_volume_gal: tank capacity in gallons
        - input_capacity_btu_hr: input rating
        - uniform_energy_factor: UEF efficiency rating
        - fuel_type: "NaturalGas", "Electricity", "Propane"
        """
        if not water_heaters:
            logger.debug("No water heaters in EMJSON")
            return

        logger.info(f"Writing {len(water_heaters)} ResWtrHtr catalog elements")

        for wh in water_heaters:
            self._write_water_heater(wh)

    def _write_water_heater(self, wh: Dict[str, Any]) -> None:
        """
        Write a single ResWtrHtr (water heater) catalog element.

        Args:
            wh: Water heater data from EMJSON systems.water_heaters
        """
        wh_data = {
            'name': wh.get('name', wh.get('id', 'Water Heater')),
        }

        # Heater element type mapping (CBECC 2025 uses HeaterElementType, not Type)
        heater_type = wh.get('heater_type', 'Gas')
        if heater_type == 'Gas':
            wh_data['HeaterElementType'] = 'Gas'
        elif heater_type == 'Electric':
            wh_data['HeaterElementType'] = 'Electric Resistance'
        elif heater_type == 'HeatPump':
            wh_data['HeaterElementType'] = 'Heat Pump'
        else:
            wh_data['HeaterElementType'] = 'Gas'

        # Tank type (required property in CBECC 2025)
        tank_type = wh.get('tank_type', 'Small Storage')
        wh_data['TankType'] = tank_type

        # HPWH Category (required for CBECC 2025)
        wh_data['HPWHCategory'] = wh.get('hpwh_category', 'Non-UEF Rated (existing only)')

        # HPWH Brand/Model (required, use n/a if not specified)
        wh_data['HPWHBrand'] = wh.get('hpwh_brand', 'n/a')
        wh_data['HPWHModel'] = wh.get('hpwh_model', 'n/a')
        wh_data['HPWHComModel'] = wh.get('hpwh_com_model', 'n/a')

        # Tank volume (CBECC uses TankVolume, not Capacity)
        if 'storage_volume_gal' in wh:
            wh_data['TankVolume'] = wh['storage_volume_gal']
        else:
            wh_data['TankVolume'] = 0  # Default for instantaneous

        # Energy Factor (EnergyFactor, not UniformEnergyFactor for older models)
        if 'energy_factor' in wh:
            wh_data['EnergyFactor'] = wh['energy_factor']
        elif 'uniform_energy_factor' in wh:
            # UEF can be converted to EF, or just use as-is
            wh_data['EnergyFactor'] = wh['uniform_energy_factor']
        else:
            wh_data['EnergyFactor'] = 0.9  # Default

        # Insulation R-values
        wh_data['IntInsulRVal'] = wh.get('interior_insulation_r', 0)
        wh_data['ExtInsulRVal'] = wh.get('exterior_insulation_r', 0)

        # Note: RecoveryEff and InputRating are NOT standard CBECC 2025 properties
        # Removing them to avoid errors

        lines = self.element_writer.write_element('ResWtrHtr', wh_data, indent=0)
        self.output_lines.extend(lines)
        self.output_lines.append('')

        logger.debug(f"Wrote ResWtrHtr: {wh_data['name']}")

    def _write_hvac_dist_sys(self, dist_sys: Dict[str, Any]) -> None:
        """
        Write a ResHVACDistSys (HVAC distribution system) element.

        Args:
            dist_sys: Distribution system data from EMJSON
        """
        dist_data = {
            'name': dist_sys.get('name', 'HVAC Distribution'),
            'Type': dist_sys.get('type', 'DirectHeating'),
        }

        # Add optional properties
        if 'duct_location' in dist_sys:
            dist_data['DuctLocation'] = dist_sys['duct_location']
        if 'duct_insulation' in dist_sys:
            dist_data['DuctInsulation'] = dist_sys['duct_insulation']
        if 'duct_sealing' in dist_sys:
            dist_data['DuctSealing'] = dist_sys['duct_sealing']

        lines = self.element_writer.write_element('ResHVACDistSys', dist_data, indent=0)
        self.output_lines.extend(lines)
        self.output_lines.append('')

    def _prepare_nested_components_for_adjacent_writing(self, commercial_hvac: Dict[str, List[Dict[str, Any]]]) -> None:
        """
        Prepare nested components for adjacent writing (AirSys, ZnSys, AirSeg).

        CIBD25 format does NOT support indented nested components. All elements must be
        top-level, written immediately after their parent in hierarchical order.

        Examples:
            AirSys "Name"         ZnSys "Name"
               ...                   ...
            ..                    ..
            AirSeg "SegName"      CoilClg "CoilName"
               ...                   ...
            ..                    ..
            CoilClg "CoilName"    CoilHtg "HtgName"
               ...                   ...
            ..                    ..

        This method removes nested components from top-level lists and keeps them
        in parent's nested_components array for hierarchical writing.

        Handles multi-level nesting: AirSys → AirSeg → CoilClg/CoilHtg/Fan
        """
        parent_types = ['AirSys', 'ZnSys', 'AirSeg']
        removed_count = 0

        for parent_type in parent_types:
            parent_list = commercial_hvac.get(parent_type, [])
            if not parent_list:
                continue

            for parent in parent_list:
                # Recursively remove nested components
                removed_count += self._remove_nested_components_recursive(parent, commercial_hvac, parent_type)

        if removed_count > 0:
            logger.info(f"Removed {removed_count} duplicate components from top-level lists (will write adjacent to parents)")

    def _remove_nested_components_recursive(self, parent: Dict[str, Any], commercial_hvac: Dict[str, List[Dict[str, Any]]], parent_type: str) -> int:
        """
        Recursively remove nested components from top-level lists.

        Handles multi-level nesting like AirSys → AirSeg → CoilClg/CoilHtg/Fan.
        """
        removed_count = 0
        nested_components = parent.get('nested_components', [])

        if not nested_components:
            return 0

        for nested in nested_components:
            nested_type = nested.get('_type')
            nested_name = nested.get('name')
            if not nested_type or not nested_name:
                continue

            # Remove from top-level list if present
            if nested_type in commercial_hvac:
                top_level_list = commercial_hvac[nested_type]
                # Filter out this component
                filtered = [comp for comp in top_level_list if comp.get('name') != nested_name]
                if len(filtered) < len(top_level_list):
                    commercial_hvac[nested_type] = filtered
                    removed_count += 1
                    logger.debug(f"Removed {nested_type} '{nested_name}' from top-level (will write adjacent to {parent_type})")

            # Recursively remove nested components of this component (e.g., CoilClg inside AirSeg)
            removed_count += self._remove_nested_components_recursive(nested, commercial_hvac, nested_type)

        return removed_count

    def _write_commercial_hvac(self) -> None:
        """
        Write commercial HVAC components (fluid systems and air systems).

        These components are stored as raw dictionaries in metadata['commercial_hvac_components']
        and written in hierarchical order:
        - Fluid systems: FluidSys → FluidSeg → WtrHtr → Chlr/Blr/Pump
        - Air systems: AirSys → AirSeg → CoilClg/CoilHtg/Fan → TrmlUnit → OACtrl
        """
        # Debug: check what metadata we have
        metadata = self.emjson.get('metadata', {})
        logger.info(f"DEBUG: metadata keys = {list(metadata.keys())}")

        commercial_hvac = metadata.get('commercial_hvac_components')
        if not commercial_hvac:
            logger.warning("No commercial HVAC components found in metadata")
            logger.info(f"DEBUG: metadata = {metadata}")
            return

        # CRITICAL FIX: Prepare nested components for adjacent writing
        # CIBD25 format does NOT support indented nested components - all elements must be top-level
        # Components must be written immediately after their parent (AirSys -> AirSeg -> CoilClg, etc.)
        self._prepare_nested_components_for_adjacent_writing(commercial_hvac)

        # Count total components
        total = sum(len(components) for components in commercial_hvac.values())
        if total == 0:
            return

        logger.info(f"Writing {total} commercial HVAC components")

        # Write in hierarchical order: project, geometry, HVAC, lighting, summary
        # Project: ProjVar (project variables)
        # Geometry: Ceiling, ExtFlr (ceiling/floor constructions)
        # Fluid systems: FluidSys (parent) → FluidSeg → WtrHtr → Chlr/Blr/Pump → HtRej/HtRcvry
        # Air systems: AirSys (parent) → AirSeg/CoilClg/CoilHtg/Fan → TrmlUnit → OACtrl
        # Zone systems: VRFSys (catalog) → ZnSys (with nested components)
        # Lighting: Lum (catalog) → IntLtgSys
        # Summary: EUseSummary (energy use summary)
        write_order = [
            # Project-level
            'ProjVar',
            # Geometry elements
            'Ceiling', 'ExtFlr',
            # Fluid/hydronic systems
            'FluidSys', 'FluidSeg', 'WtrHtr', 'Chlr', 'Blr', 'Pump', 'HtRej', 'HtRcvry',
            # Air systems
            'AirSys', 'AirSeg', 'CoilClg', 'CoilHtg', 'Fan', 'TrmlUnit', 'OACtrl',
            # Thermal zones (must come before ZnSys)
            'ThrmlZn',
            # Zone HVAC systems
            'VRFSys', 'ZnSys',
            # Lighting systems
            'Lum', 'IntLtgSys',
            # Summary
            'EUseSummary'
        ]

        # Track which components have been written as part of parent hierarchies
        written_components = set()

        # Parent element types that can have nested components
        parent_types = {'AirSys', 'ZnSys', 'AirSeg'}

        for element_type in write_order:
            components = commercial_hvac.get(element_type, [])
            for component in components:
                # Skip components that were already written as part of parent hierarchy
                comp_name = component.get('name')
                if comp_name in written_components:
                    continue

                # Write the component
                self._write_commercial_hvac_component(component, element_type)

                # If this element can have nested components, write them immediately after
                if element_type in parent_types:
                    self._write_nested_components_recursively(component, written_components)

        logger.info("Commercial HVAC components complete")

    def _write_nested_components_recursively(self, parent: Dict[str, Any], written_components: set) -> None:
        """
        Write nested components immediately after their parent, recursively.

        Handles multi-level nesting like AirSys → AirSeg → CoilClg/CoilHtg/Fan.

        Args:
            parent: Parent component dictionary with nested_components
            written_components: Set of component names already written
        """
        nested = parent.get('nested_components', [])
        for nested_comp in nested:
            nested_type = nested_comp.get('_type')
            nested_name = nested_comp.get('name')
            if not nested_type or not nested_name:
                continue

            # Write this nested component
            self._write_commercial_hvac_component(nested_comp, nested_type)
            written_components.add(nested_name)

            # Recursively write its nested components (e.g., AirSeg → CoilClg)
            self._write_nested_components_recursively(nested_comp, written_components)

    def _write_commercial_hvac_component(self, component: Dict[str, Any], element_type: str) -> None:
        """Write a single commercial HVAC component (AirSys, Fan, Coil, etc.).

        For elements with indexed properties (like IntLtgSys), handles indexed arrays properly.
        Nested components are no longer supported - they are extracted and written as top-level.
        """
        component_data = {
            'name': component.get('name', 'Component'),
        }

        # Separate indexed and regular properties
        indexed_properties = {}
        properties = component.get('properties', {})
        for key, value in properties.items():
            # Skip empty string values - these are XML hierarchy artifacts
            if value == '':
                continue

            # Check if this is an indexed property (list of tuples)
            if isinstance(value, list) and value and isinstance(value[0], tuple):
                indexed_properties[key] = value
            else:
                component_data[key] = value

        # Check if this component has indexed properties (e.g., IntLtgSys, EUseSummary)
        if indexed_properties:
            # Write parent element first
            lines = self.element_writer.write_element(element_type, component_data, indent=0)
            # Remove the closing ".." line (will add after indexed properties)
            if lines and lines[-1].strip() == '..':
                lines = lines[:-1]
            self.output_lines.extend(lines)

            # Write indexed properties (e.g., LumRef[1] = "E", LumRef[2] = "G")
            # NOTE: Convert from XML 0-indexed to CIBD25 1-indexed
            for prop_name, indexed_values in indexed_properties.items():
                for index, value in indexed_values:
                    # Convert from XML 0-indexed to CIBD25 1-indexed
                    cibd25_index = int(index) + 1

                    # Special case: EUseSummary arrays
                    # Most contain display values (strings, numbers with commas, "--", etc.) and must be quoted
                    # BUT some properties like ZoneUMLHsLoaded are integers and must NOT be quoted
                    if element_type == 'EUseSummary':
                        # Properties that should remain as integers (not quoted)
                        integer_properties = ['ZoneUMLHsLoaded', 'AnalysisValid', 'HideCompSmrySrc', 'HideCompSmryTot', 'PVBattResultsValid']

                        if prop_name in integer_properties:
                            # Keep as integer (no quotes)
                            formatted_value = str(value)
                        else:
                            # Force string quoting for display values
                            formatted_value = f'"{value}"'
                    else:
                        # Format value with proper quoting
                        formatted_value = self.element_writer.formatter.format_value(prop_name, value)

                    # CIBD25 array syntax: PropertyName[1] = value
                    self.output_lines.append(f'   {prop_name}[{cibd25_index}] = {formatted_value}')

            # Add closing ".." for parent element
            self.output_lines.append('..')
            self.output_lines.append('')
        else:
            # No indexed properties - write normally
            lines = self.element_writer.write_element(element_type, component_data, indent=0)
            self.output_lines.extend(lines)
            self.output_lines.append('')

        logger.debug(f"Wrote {element_type}: {component_data['name']}")

    def _write_dwelling_unit_types(self) -> None:
        """
        Write all DwellUnitType catalog elements.

        DwellUnitTypes are in catalogs.du_types in EMJSON v6.
        """
        # Get du_types from catalogs
        catalogs = self.emjson.get('catalogs', {})
        du_types = catalogs.get('du_types', [])

        if not du_types:
            logger.debug("No dwelling unit types in EMJSON catalogs")
            return

        logger.info(f"Writing {len(du_types)} DwellUnitType catalog elements")

        for du_type in du_types:
            self._write_dwelling_unit_type(du_type)

    def _write_dwelling_unit_type(self, du_type: Dict[str, Any]) -> None:
        """
        Write a DwellUnitType catalog element.

        DwellUnitType defines a type of dwelling unit with common properties and HVAC/IAQ/DHW system references.

        Args:
            du_type: Dwelling unit type data from EMJSON catalogs.du_types

        Properties from CIBD22X parser (dutype_parser.py):
        - cond_floor_area: floor area in ft² (already in IP units)
        - num_bedrooms: number of bedrooms
        - dryer_fuel, cook_fuel: appliance fuel types
        - hvac_sys_type, hvac_ht_pump_ref, hvac_fan_ref, hvac_dist_ref: HVAC system references
        - iaq_option, iaq_fan_ref, iaq_fan_cnt: IAQ system references
        - dhw_sys_ref: DHW system reference
        """
        # Start with basic properties
        du_data = {
            'name': du_type.get('name', du_type.get('id', 'Unit Type')),
        }

        # Add all parsed CIBD-specific properties
        # These are already in CIBD format from the parser
        property_map = {
            # Geometry
            'cond_floor_area': 'CondFlrArea',  # ft² (already IP)
            'num_bedrooms': 'NumBedrooms',

            # Appliances
            'dryer_fuel': 'DryerFuel',
            'cook_fuel': 'CookFuel',

            # HVAC system references
            'hvac_sys_type': 'HVACSysType',
            'hvac_fan_ref': 'HVACFanRef',
            'hvac_dist_ref': 'HVACDistRef',

            # IAQ system references
            'iaq_option': 'IAQOption',
            'iaq_fan_cnt': 'IAQFanCnt',
        }

        # Add simple properties
        for src_key, dst_key in property_map.items():
            if src_key in du_type and du_type[src_key] is not None:
                du_data[dst_key] = du_type[src_key]

        # Handle array properties (need [1] notation in CIBD25)
        # These may be strings (single value) or lists (multiple values)
        array_properties = {
            'hvac_ht_pump_ref': 'HVACHtPumpRef',
            'ht_pump_equip_count': 'HtPumpEquipCount',  # Number of heat pump units
            'iaq_fan_ref': 'IAQFanRef',
            'dhw_sys_ref': 'DHWSysRef',
        }

        for src_key, dst_key in array_properties.items():
            value = du_type.get(src_key)
            if value is not None:
                if isinstance(value, list):
                    # Array format: write with [1], [2], etc.
                    for i, item in enumerate(value):
                        if item is not None:
                            du_data[f'{dst_key}[{i+1}]'] = item
                else:
                    # Single value: write with [1] notation
                    du_data[f'{dst_key}[1]'] = value

        lines = self.element_writer.write_element('DwellUnitType', du_data, indent=0)
        self.output_lines.extend(lines)
        self.output_lines.append('')

        logger.debug(f"Wrote DwellUnitType: {du_data['name']}")

    def _write_lighting_systems(self) -> None:
        """
        Write lighting system elements.

        Extracts lighting systems from EMJSON if available, including:
        - ResLtgSys (residential lighting systems)
        """
        logger.info("Writing lighting systems")

        systems = self.emjson.get('systems', {})
        lighting_systems = systems.get('lighting', {})

        # Write lighting systems (if present)
        ltg_systems = lighting_systems.get('systems', [])
        if ltg_systems:
            logger.info(f"Writing {len(ltg_systems)} lighting systems")
            for ltg_sys in ltg_systems:
                self._write_lighting_system(ltg_sys)
        else:
            logger.info("No lighting systems to write (using defaults)")

        logger.info("Lighting systems complete")

    def _write_lighting_system(self, ltg_sys: Dict[str, Any]) -> None:
        """
        Write a ResLtgSys (residential lighting system) element.

        Args:
            ltg_sys: Lighting system data from EMJSON
        """
        ltg_data = {
            'name': ltg_sys.get('name', 'Lighting System'),
            'Type': ltg_sys.get('type', 'Hardwired'),
        }

        # Add optional properties
        if 'power_density' in ltg_sys:
            ltg_data['LPD'] = ltg_sys['power_density']  # Lighting Power Density (W/sf)
        if 'control_type' in ltg_sys:
            ltg_data['ControlType'] = ltg_sys['control_type']
        if 'high_efficacy_percentage' in ltg_sys:
            ltg_data['HighEfficacyPct'] = ltg_sys['high_efficacy_percentage']
        if 'dimming_capable' in ltg_sys:
            ltg_data['DimmingCapable'] = 1 if ltg_sys['dimming_capable'] else 0

        lines = self.element_writer.write_element('ResLtgSys', ltg_data, indent=0)
        self.output_lines.extend(lines)
        self.output_lines.append('')


def convert_emjson_to_cibd25(emjson_data: Dict[str, Any], output_path: str) -> bool:
    """
    Convenience function to convert EMJSON to CIBD25.

    Args:
        emjson_data: EMJSON v6 formatted dictionary
        output_path: Path to output .cibd25 file

    Returns:
        True if successful, False otherwise
    """
    writer = CIBD25DirectWriter(emjson_data)
    return writer.write_file(output_path)
