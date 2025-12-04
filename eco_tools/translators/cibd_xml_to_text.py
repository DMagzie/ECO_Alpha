"""
Convert CIBD XML format to text format.

This module converts CBECC XML files to the text-based CIBD format.
The text format is what CBECC uses for .cibd22, .cibd25 files.

Format structure:
- Top-level standalone properties: RulesetFilename "value"
- Objects: ObjectType "name"
  - Properties: PropertyName = value
  - String properties: PropertyName = "value"
  - References: RefProperty = "ObjectName"
  - Array references: RefProperty[1] = "ObjectName"
  - Object ends with ".."
"""

import xml.etree.ElementTree as ET
from typing import TextIO, Any, Dict, Set
import re


class CIBDXMLToTextConverter:
    """Convert CBECC XML to text format."""

    def __init__(self):
        self.namespace = ''
        self.written_objects: Set[str] = set()

    def convert_file(self, xml_path: str, output_path: str):
        """
        Convert XML file to text format.

        Args:
            xml_path: Path to input XML file
            output_path: Path for output text file
        """
        tree = ET.parse(xml_path)
        root = tree.getroot()

        # Fix #33: Use LF line endings (Unix) - working Euclid file uses LF, not CRLF
        with open(output_path, 'w', encoding='utf-8', newline='\n') as f:
            self.convert_element(root, f)

    def convert_element(self, root: ET.Element, output: TextIO):
        """
        Convert XML element tree to text format.

        Args:
            root: Root XML element
            output: Output file handle
        """
        # Detect namespace
        if '}' in root.tag:
            self.namespace = root.tag.split('}')[0] + '}'

        # Store root attributes for property override (e.g., RulesetFilename from root takes precedence)
        self.root_attributes = {k: v for k, v in root.attrib.items() if k != 'xmlns'}

        # Write top-level attributes (e.g., RulesetFilename)
        for attr_name, attr_value in root.attrib.items():
            if attr_name != 'xmlns':
                # Fix #32: Remove trailing spaces
                output.write(f'{attr_name}   "{attr_value}"\n')

        if root.attrib:
            output.write('\n')

        # Initialize deferred siblings list
        self.deferred_siblings = []

        # Check for RulesetFilename child element and write it first
        for child in root:
            child_tag = child.tag.replace(self.namespace, '') if self.namespace else child.tag
            if child_tag == 'RulesetFilename':
                # Extract filename from 'file' attribute
                ruleset_file = child.attrib.get('file', 'T24_2025.bin')
                # Convert CIBD22 ruleset to CIBD25 ruleset for compatibility
                if ruleset_file == 'T24N_2022.bin':
                    ruleset_file = 'T24_2025.bin'
                # Fix #32: Remove trailing spaces
                output.write(f'RulesetFilename   "{ruleset_file}"\n\n')
                break

        # Process child elements
        # Fix #36: ALL root-level elements (except RulesetFilename, Proj) must be deferred
        # for proper sorting. CBECC reference file order:
        # RulesetFilename → Proj → ProjVar → ResProj → SchDay → Bldg → ... → DwellUnitType → HVAC → END
        # Elements written directly (not deferred):
        WRITE_DIRECTLY = {'RulesetFilename', 'Proj'}

        for child in root:
            child_tag = child.tag.replace(self.namespace, '') if self.namespace else child.tag
            # Fix #36: Defer all root elements except RulesetFilename and Proj for proper sorting
            if child_tag in WRITE_DIRECTLY:
                self._write_object(child, output, indent=0)
            else:
                self.deferred_siblings.append(child)

        # Fix #26: Write any deferred siblings (e.g., ResProj, ProjVar) at root level
        # Sort deferred siblings to ensure correct ordering: Building structure objects (Bldg)
        # must come BEFORE type definitions (DwellUnitType). CBECC requires DwellUnit instances
        # to appear in the file BEFORE DwellUnitType definitions, so building hierarchy must be
        # written early to allow DwellUnit instances (immediate siblings of ResZn) to appear
        # before DwellUnitType definitions (deferred siblings of Proj written at end).
        if self.deferred_siblings:
            # Sort deferred siblings by priority (lower number = written first)
            sorted_siblings = sorted(self.deferred_siblings, key=self._get_deferred_sibling_priority)
            for sibling in sorted_siblings:
                self._write_object(sibling, output, indent=0)

        # Fix #40: Remove END_OF_FILE marker - Euclid working file doesn't have it
        # END_OF_FILE may interfere with GUI recognition of DwellUnitType
        # output.write('\n\nEND_OF_FILE\n')

    def _write_object(self, elem: ET.Element, output: TextIO, indent: int = 0):
        """
        Write an object and its properties.

        Args:
            elem: XML element representing object
            output: Output file handle
            indent: Indentation level
        """
        # Get tag name without namespace
        tag = elem.tag.replace(self.namespace, '') if self.namespace else elem.tag

        # Skip RulesetFilename child element (we wrote it as attribute)
        if tag == 'RulesetFilename':
            return

        # Skip results/report objects (generated by CBECC, not needed for file open)
        if tag in ['EUseSummary', 'DwellUnitRpt', 'ResIAQVentRpt', 'ResSCSysRpt', 'ResDHWSysRpt']:
            return

        # Fix #43: Skip Batt element - causes CBECC GUI to stall during file open
        # Battery storage is not properly supported in CIBD25 text format conversion
        if tag == 'Batt':
            return

        # Get object name from 'Name' or 'n' child or text content
        obj_name = None
        properties = []
        child_objects = []

        # Track immediate siblings separately from deferred siblings
        immediate_siblings = []  # Written right after this object

        for child in elem:
            child_tag = child.tag.replace(self.namespace, '') if self.namespace else child.tag

            if child_tag == 'n':
                obj_name = child.text
            elif child_tag == 'Name':
                # Use Name as the object name for all objects
                obj_name = child.text
            elif len(child) > 0:
                # Check if this should be a top-level sibling instead of nested
                if self._is_top_level_sibling(child_tag, tag, child):
                    # CIBD25: When extracting Spc from Story, inject ParentStoryRef
                    if tag == 'Story' and child_tag == 'Spc' and obj_name:
                        # Create ParentStoryRef element and inject into child
                        parent_ref = ET.SubElement(child, 'ParentStoryRef')
                        parent_ref.text = obj_name

                    # Fix #27: DwellUnit objects need WasherZoneRef and DryerZoneRef injected
                    # These properties are REQUIRED for CBECC to associate the DwellUnit with
                    # its parent zone and properly resolve DwellUnitTypeRef references in the GUI.
                    # Without these, CBECC GUI shows "(No DwellUnitType assigned)" even though
                    # the DwellUnitTypeRef value is present in the file.
                    if tag == 'ResZn' and child_tag == 'DwellUnit' and obj_name:
                        # Inject WasherZoneRef pointing to parent zone
                        washer_ref = ET.SubElement(child, 'WasherZoneRef')
                        washer_ref.text = obj_name
                        # Inject DryerZoneRef pointing to parent zone
                        dryer_ref = ET.SubElement(child, 'DryerZoneRef')
                        dryer_ref.text = obj_name

                    # Determine if this should be immediate or deferred
                    # Residential zone children are immediate (written right after zone)
                    # Other extractions (HVAC, schedules, etc.) are deferred (written at end)
                    if self._is_immediate_sibling(child_tag, tag):
                        immediate_siblings.append(child)
                    else:
                        # Store for writing at root level later
                        if not hasattr(self, 'deferred_siblings'):
                            self.deferred_siblings = []
                        self.deferred_siblings.append(child)
                else:
                    # Regular nested object
                    child_objects.append(child)
            else:
                # Leaf node - it's a property
                # CIBD25: Check if element has 'index' attribute (for array properties like DHWHeater[1])
                # XML uses 0-based index attribute, CIBD25 uses 1-based bracket notation
                index_attr = child.get('index')
                if index_attr is not None:
                    # Convert 0-based XML index to 1-based CIBD25 index
                    cibd_index = int(index_attr) + 1
                    prop_name = f'{child_tag}[{cibd_index}]'
                    properties.append((prop_name, child.text))
                else:
                    properties.append((child_tag, child.text))

        # If no name found, check if element has text content
        if obj_name is None and elem.text and elem.text.strip():
            obj_name = elem.text.strip()

        # Clean any XML tags from object name (handles malformed source data)
        if obj_name:
            obj_name = re.sub(r'<[^>]+>', '', obj_name)

        # CIBD25: Generate auto-names for geometry elements that lack names
        if not obj_name:
            if tag == 'PolyLp':
                # Auto-generate PolyLoop name with counter
                if not hasattr(self, 'polylp_counter'):
                    self.polylp_counter = 0
                self.polylp_counter += 1
                obj_name = f"PolyLoop {self.polylp_counter}"
            elif tag == 'CartesianPt':
                # Auto-generate CartesianPoint name with counter
                if not hasattr(self, 'cartesianpt_counter'):
                    self.cartesianpt_counter = 0
                self.cartesianpt_counter += 1
                obj_name = f"CartesianPoint {self.cartesianpt_counter}"

        # CIBD25: Special handling for CartesianPt - combine Coord values into tuple
        if tag == 'CartesianPt':
            coord_values = [value for prop_name, value in properties if prop_name == 'Coord']
            if coord_values:
                # Remove individual Coord properties
                properties = [(p, v) for p, v in properties if p != 'Coord']
                # Add single Coord tuple property
                coord_tuple = '( ' + ', '.join(coord_values) + ' )'
                properties.append(('Coord', coord_tuple))

        # Write object header
        indent_str = '   ' * indent
        if obj_name:
            # Fix #38: NO trailing spaces after object name - matches Euclid working format
            # Euclid hex shows: "DU_B2.4"\n (22 0a = quote then newline, no spaces)
            output.write(f'{indent_str}{tag}   "{obj_name}"\n')
        else:
            # Some objects don't have names
            output.write(f'{indent_str}{tag}\n')

        # CIBD25 Format: Extract ExcptCond* properties from Proj into separate ProjVar element
        projvar_properties = []
        if tag == 'Proj':
            excpt_cond_props = [p for p in properties if p[0].startswith('ExcptCond')]
            if excpt_cond_props:
                # Create ProjVar element
                projvar_name = f"{obj_name} - ProjVar" if obj_name else "ProjVar"
                projvar_properties = excpt_cond_props
                # Remove from Proj properties
                properties = [p for p in properties if not p[0].startswith('ExcptCond')]

            # Fix #39: Update version markers for CIBD25 format (2022 → 2025 conversion)
            updated_properties = []
            for prop_name, prop_value in properties:
                if prop_name == 'RunTitle' and '2022' in str(prop_value):
                    prop_value = 'Title 24 2025 Compliance'
                elif prop_name == 'SoftwareVersion':
                    prop_value = 'CBECC 2025.2.0 (converted from CIBD22X)'
                updated_properties.append((prop_name, prop_value))
            properties = updated_properties

        # Write properties - collect them first to handle terminator correctly
        property_lines = []
        for prop_name, prop_value in properties:
            if prop_value is None:
                continue

            # Skip Name if it was used as object name
            if prop_name == 'Name' and obj_name == prop_value:
                continue

            # Skip properties that are defined as root attributes (they're written at top level)
            if hasattr(self, 'root_attributes') and prop_name in self.root_attributes:
                continue

            # Skip MassThickness for ResConsAssm (CIBD22X property not recognized in CIBD25)
            if tag == 'ResConsAssm' and prop_name == 'MassThickness':
                continue

            # Skip EMJSON metadata properties for ResHVACSys
            if tag == 'ResHVACSys' and prop_name in ['ht_pump_system_refs', 'heat_system_refs', 'cool_system_refs']:
                continue

            # Skip EMJSON metadata properties for ResDHWSys
            if tag == 'ResDHWSys' and prop_name in ['dhw_heater_refs']:
                continue

            # Fix #41: Skip deprecated properties from CIBD22X not recognized in CIBD25
            if tag in ['ResZn', 'ResOtherZn'] and prop_name == 'VentSpcFunc':
                continue

            # Fix #44: Skip battery-related properties deprecated in CIBD25
            # These cause GUI to stall when opening files (not in any CBECC 2025 sample files)
            if prop_name in ['PVBattSizeBldgType', 'BattReq_PartOfLargeTenantArea']:
                continue

            # Detect if this is a reference (array or single)
            array_match = re.match(r'(.+)\[(\d+)\]', prop_name)

            if array_match:
                # Array reference: MatRef[1] = "Material Name" OR HeaterMult[1] = 6
                base_name = array_match.group(1)
                index = array_match.group(2)
                # Check if value is numeric (shouldn't be quoted)
                prop_type = self._get_property_type(base_name, prop_value)
                if prop_type == 'number':
                    property_lines.append(f'{indent_str}   {base_name}[{index}] = {prop_value}')
                else:
                    property_lines.append(f'{indent_str}   {base_name}[{index}] = "{prop_value}"')
            else:
                # Transform property value if needed (e.g., IAQFanType conversion)
                prop_value = self._transform_property_value(prop_name, prop_value)

                # Determine property type
                prop_type = self._get_property_type(prop_name, prop_value)

                # Special case: Coord tuples should NOT be quoted
                if prop_name == 'Coord' and prop_value.startswith('('):
                    # Coordinate tuple: Coord = ( x, y, z )
                    property_lines.append(f'{indent_str}   {prop_name} = {prop_value}')
                elif prop_type == 'number':
                    # Numeric value (no quotes)
                    property_lines.append(f'{indent_str}   {prop_name} = {prop_value}')
                else:
                    # String, reference, or enum (quoted)
                    property_lines.append(f'{indent_str}   {prop_name} = "{prop_value}"')

        # CIBD25 requirement: ResZn/ResOtherZn MUST have Type property
        # This is required even in the flat structure
        if tag in ['ResZn', 'ResOtherZn']:
            has_type = any('Type =' in line for line in property_lines)
            if not has_type:
                # Insert Type as first property - default to "Conditioned"
                # CBECC rules will determine actual conditioning based on HVAC assignments
                property_lines.insert(0, f'{indent_str}   Type = "Conditioned"')

            # Fix #41: REMOVED - VentSpcFunc is deprecated in CIBD25 (was CIBD22X only)
            # Euclid working file doesn't have VentSpcFunc, and CBECC logs "unrecognized property" errors
            # Previous code was adding VentSpcFunc = "NA" but this is wrong for CIBD25 format

        # Fix #43: ResCentralVentSys MUST have Type property or CBECC GUI stalls
        if tag == 'ResCentralVentSys':
            has_type = any('Type =' in line for line in property_lines)
            if not has_type:
                # Insert Type as first property - default to "Balanced"
                property_lines.insert(0, f'{indent_str}   Type = "Balanced"')

        # Write all properties
        for line in property_lines:
            output.write(line + '\n')

        # Write nested objects
        for child_obj in child_objects:
            self._write_object(child_obj, output, indent + 1)

        # Write object terminator
        # Fix #30: Match working file format - terminator '..' with no leading spaces
        # Fix #31: Need blank line after terminator to separate objects
        output.write('..\n\n')

        # Write immediate siblings right after this object (at root level)
        # These are children that were extracted to top level but need to maintain
        # ordering relative to their parent (e.g., zone walls/DwellUnits after zone)
        if immediate_siblings:
            for sibling in immediate_siblings:
                self._write_object(sibling, output, indent=0)

        # CIBD25 Format: Write ProjVar element after Proj if we extracted ExcptCond properties
        if tag == 'Proj' and projvar_properties:
            # Fix #28: Remove trailing spaces
            output.write(f'ProjVar   "{projvar_name}"\n')
            for prop_name, prop_value in projvar_properties:
                if prop_value is None:
                    continue
                # All ExcptCond properties are string enumerations
                output.write(f'   {prop_name} = "{prop_value}"\n')
            # Fix #30/31: Match working file format - terminator '..' with blank line after
            output.write('..\n\n')

    def _transform_property_value(self, prop_name: str, prop_value: str) -> str:
        """
        Transform property values for CIBD25 compatibility.

        Args:
            prop_name: Name of the property
            prop_value: Original value from source

        Returns:
            Transformed value (or original if no transformation needed)
        """
        # No transformations currently needed - property values are preserved as-is
        return prop_value

    def _is_number(self, value: str) -> bool:
        """Check if value is a number (int or float)."""
        if value is None:
            return False
        try:
            float(value)
            return True
        except (ValueError, TypeError):
            return False

    def _is_reference(self, prop_name: str) -> bool:
        """Check if property name indicates a reference."""
        ref_patterns = [
            'Ref', 'Type', 'Schedule', 'System', 'Zone', 'Space',
            'Bldg', 'Story', 'Surface', 'Window', 'Door'
        ]
        return any(pattern in prop_name for pattern in ref_patterns)

    def _is_top_level_sibling(self, child_tag: str, parent_tag: str, child=None) -> bool:
        """
        Check if an element should be written as a top-level sibling instead of nested.

        In CIBD XML, many elements are nested inside Proj for document organization,
        but in CIBD text format they must be top-level siblings (catalog objects).

        Args:
            child_tag: Tag of the child element
            parent_tag: Tag of the parent element
            child: The child XML element (optional, needed for attribute checks)

        Returns:
            True if child should be written as top-level sibling
        """
        # Elements that appear as children of Proj in XML but should be siblings in text
        if parent_tag == 'Proj':
            # Schedule objects (catalog objects)
            if child_tag in ['SchDay', 'SchWeek', 'Sch']:
                return True

            # Project variants (compliance data)
            if child_tag in ['ResProj', 'ProjVar']:
                return True

            # Building object (must be top-level sibling to Proj in CIBD25)
            if child_tag == 'Bldg':
                return True

            # Dwelling unit type definitions
            if child_tag == 'DwellUnitType':
                return True

            # Project-level systems (must be top-level siblings to Proj)
            if child_tag in ['FluidSys', 'PVArray', 'Batt', 'ProjVar']:
                return True

            # Residential HVAC catalog (all systems are top-level library objects)
            if child_tag in [
                'ResHtgSys',           # Heating systems
                'ResClgSys',           # Cooling systems
                'ResHtPumpSys',        # Heat pump systems
                'ResDistSys',          # Distribution systems
                'ResFanSys',           # Fan systems
                'ResIAQFan',           # IAQ fans
                'ResDHWSys',           # DHW systems
                'ResWtrHtr',           # Water heaters
                'ResLpTankHtr',        # Loop tank heaters
                'ResCentralVentSys',   # Central ventilation
            ]:
                return True

            # Residential construction catalog
            if child_tag in [
                'ResConsAssm',         # Construction assemblies
                'ResMat',              # Materials
                'ResWinType',          # Window types
            ]:
                return True

            # HERS/Compliance objects
            if child_tag in [
                'HERSCool',            # HERS cooling
                'HERSHeat',            # HERS heating
                'HERSHtPump',          # HERS heat pump
                'HERSDist',            # HERS distribution
                'HERSFan',             # HERS fan
                'HERSDHWSys',          # HERS DHW
                'HERSOther',           # HERS other
                'SpeclFtr',            # Special features
                # NOTE: ResZnGrp removed - it's a child of Bldg, not Proj
            ]:
                return True

            # Construction library and equipment catalog elements that appear as children
            # of Proj in XML but must be extracted as top-level siblings in CIBD25 text format
            if child_tag in [
                'ConsAssm',            # Construction assemblies
                'Mat',                 # Materials
                'FenCons',             # Fenestration constructions
                'DrCons',              # Door constructions
                'SpcFuncDefaults',     # Space function defaults
                'Lum',                 # Luminaires (lighting fixtures)
                'WtrHtr',              # Water heaters
                'Chiller',             # Chillers
                'Boiler',              # Boilers
                'Pump',                # Pumps
                'ThrmlEngyStor',       # Thermal energy storage
            ]:
                return True

            # Report objects
            if child_tag in [
                'ResDHWSysRpt',        # DHW system reports
                'DwellUnitRpt',        # Dwelling unit reports
                'ResIAQVentRpt',       # IAQ ventilation reports
                'ResSCSysRpt',         # Space conditioning reports
                'EUseSummary',         # End use summary
            ]:
                return True

        # Elements that appear as children of Bldg in XML but should be siblings in text
        if parent_tag == 'Bldg':
            # Story elements must be extracted to top level
            if child_tag == 'Story':
                return True

            # Residential zone groups must be extracted to top level
            if child_tag == 'ResZnGrp':
                return True

            # Commercial thermal zones and zone systems must be extracted to top level
            if child_tag in ['ThrmlZn', 'ZnSys']:
                return True

            # Commercial HVAC systems must be extracted to top level
            if child_tag == 'AirSys':
                return True

            # VRF systems (Variable Refrigerant Flow) must be extracted to top level
            if child_tag == 'VRFSys':
                return True

        # Elements that appear as children of Story in XML but should be siblings in text
        if parent_tag == 'Story':
            # Spaces must be extracted to top level
            if child_tag == 'Spc':
                return True

        # Elements that appear as children of ZnSys in XML but should be siblings in text
        if parent_tag == 'ZnSys':
            # HVAC components nested under ZnSys must be extracted to top level
            if child_tag in ['CoilClg', 'CoilHtg', 'Fan', 'Htg', 'Clg']:
                return True

        # Elements that appear as children of Spc in XML but should be siblings in text
        if parent_tag == 'Spc':
            # Building envelope components, lighting systems, residential DHW features, and geometry must be extracted to top level
            if child_tag in ['ExtWall', 'IntWall', 'UndgrFlr', 'UndgrWall', 'Flr', 'Roof', 'Ceiling', 'IntFlr', 'ExtFlr', 'IntLtgSys', 'PolyLp', 'ResSpcDHWFeatures']:
                return True

        # Elements that appear as children of ExtWall in XML but should be siblings in text
        if parent_tag == 'ExtWall':
            # Windows and doors (commercial) must be extracted to top level
            if child_tag in ['Win', 'Dr']:
                return True

        # Elements that appear as children of Roof in XML but should be siblings in text
        if parent_tag == 'Roof':
            # Skylights (commercial) must be extracted to top level
            if child_tag == 'Skylt':
                return True

        # Elements that appear as children of commercial surface elements in XML but should be siblings in text
        # This includes ALL commercial building envelope surfaces AND fenestration that can have geometry
        if parent_tag in ['ExtWall', 'IntWall', 'UndgrFlr', 'UndgrWall', 'Flr', 'Roof', 'Ceiling', 'IntFlr', 'ExtFlr', 'Dr', 'Win', 'Skylt']:
            # PolyLp geometry must be extracted to top level
            # CIBD25 does NOT allow nested PolyLp inside surface elements OR fenestration elements (Win, Dr, Skylt)
            if child_tag == 'PolyLp':
                return True

        # Elements that appear as children of FluidSys in XML but should be siblings in text
        if parent_tag == 'FluidSys':
            # Fluid segments and water heaters must be extracted to top level
            # They reference each other through FluidSegOutRef/FluidSegMakeupRef properties
            if child_tag in ['FluidSeg', 'WtrHtr']:
                return True

        # Elements that appear as children of AirSys in XML but should be siblings in text
        if parent_tag == 'AirSys':
            # Air segments and HVAC components must be extracted to top level
            # Similar to FluidSys structure - components are top-level siblings
            if child_tag in ['AirSeg', 'CoilClg', 'CoilHtg', 'Fan', 'TrmlUnit', 'OACtrl', 'EvapClr', 'HtRcvry']:
                return True

        # Elements that appear as children of AirSeg in XML but should be siblings in text
        if parent_tag == 'AirSeg':
            # HVAC components nested under AirSeg must also be extracted to top level
            # They are top-level siblings in CIBD25 format, not nested under AirSeg
            if child_tag in ['CoilClg', 'CoilHtg', 'Fan', 'OACtrl', 'EvapClr', 'TrmlUnit']:
                return True

        # Elements that appear as children of PolyLp in XML but should be siblings in text
        if parent_tag == 'PolyLp':
            # CartesianPt (Cartesian Points) must be extracted to top level
            if child_tag == 'CartesianPt':
                return True

        # CRITICAL: In CIBD25 text format, ResZnGrp is an empty container and ALL
        # residential zone elements are top-level siblings (not nested)

        # Elements that appear as children of ResZnGrp in XML but should be siblings in text
        if parent_tag == 'ResZnGrp':
            # All zone types must be extracted to top level in CIBD25
            if child_tag in ['ResZn', 'ResOtherZn', 'ResAttic']:
                return True

        # Elements that appear as children of ResZn in XML but should be siblings in text
        if parent_tag == 'ResZn':
            # ALL children of ResZn must be extracted to top level in CIBD25
            if child_tag in [
                'DwellUnit',           # Dwelling units
                'ResExtWall',          # Exterior walls
                'ResIntWall',          # Interior walls
                'ResUndgrWall',        # Underground walls
                'ResSlabFlr',          # Slab floors
                'ResIntFlr',           # Interior floors
                'ResCathedralCeiling', # Cathedral ceilings
                'ResCeilingBelowAttic',# Ceiling below attic
                'ResOpening',          # Openings (doors)
                'ResExtFlr',           # Exterior floors
                'ResAtticRoof',        # Attic roofs
                'IntLtgSys',           # Interior lighting systems
            ]:
                return True

        # Elements that appear as children of ResOtherZn in XML but should be siblings in text
        if parent_tag == 'ResOtherZn':
            # ALL children of ResOtherZn must be extracted to top level in CIBD25
            if child_tag in [
                'ResExtWall',          # Exterior walls
                'ResIntWall',          # Interior walls
                'ResUndgrWall',        # Underground walls
                'ResSlabFlr',          # Slab floors
                'ResIntFlr',           # Interior floors
                'ResCathedralCeiling', # Cathedral ceilings
                'ResCeilingBelowAttic',# Ceiling below attic
                'ResOpening',          # Openings (doors)
                'ResExtFlr',           # Exterior floors
                'ResAtticRoof',        # Attic roofs
                'IntLtgSys',           # Interior lighting systems
            ]:
                return True

        # Elements that appear as children of ResExtWall in XML but should be siblings in text
        if parent_tag == 'ResExtWall':
            # Windows and doors must be extracted to top level
            if child_tag in ['ResWin', 'ResDr']:
                return True

        # Elements that appear as children of ResAtticRoof in XML but should be siblings in text
        if parent_tag == 'ResAtticRoof':
            # Skylights must be extracted to top level
            if child_tag == 'ResSkylt':
                return True

        return False

    def _get_deferred_sibling_priority(self, elem: ET.Element) -> int:
        """
        Get priority order for deferred siblings (lower number = written earlier).

        Fix #26: CBECC 2025 requires specific ordering where building structure (Bldg)
        must be written BEFORE type definitions like DwellUnitType. This ensures that
        DwellUnit instances (which are immediate siblings of ResZn inside Bldg hierarchy)
        appear in the output file BEFORE DwellUnitType definitions are written.

        Args:
            elem: XML element being ordered

        Returns:
            Priority number (lower = earlier in file)
        """
        tag = elem.tag.replace(self.namespace, '') if self.namespace else elem.tag

        # Priority levels (based on CBECC reference MF8Unit order):
        # Order: ProjVar → ResProj → SchDay → Bldg → ... → DwellUnitType → HVAC systems

        # 1. Fix #36: ResProj and ProjVar must come BEFORE Bldg
        # Fix #37: Match Euclid working file order (NOT CBECC MF8 reference)
        # Euclid order: Proj → Construction → HVAC components → Bldg → ... → DwellUnitType → HVAC systems

        # 1. Project variants
        if tag in ['ResProj', 'ProjVar']:
            return 50

        # 2. Schedule objects
        if tag in ['SchDay', 'SchWeek', 'Sch']:
            return 60

        # 3. Construction catalog - BEFORE Bldg (matches Euclid)
        if tag in ['ResConsAssm', 'ResMat', 'ResWinType', 'ConsAssm', 'Mat',
                   'FenCons', 'DrCons', 'SpcFuncDefaults']:
            return 70

        # 4. HVAC COMPONENTS - BEFORE Bldg (matches Euclid)
        # These are catalog/library objects, not system assignments
        # Fix #42: Specific order within HVAC components based on working Euclid file:
        # ResHtPumpSys → ResFanSys → ResCentralVentSys → ResDistSys → ResIAQFan
        if tag in ['ResHtgSys', 'ResClgSys']:
            return 80
        if tag == 'ResHtPumpSys':
            return 81
        if tag == 'ResFanSys':
            return 82
        if tag == 'ResCentralVentSys':
            return 83
        if tag == 'ResDistSys':
            return 84
        if tag in ['ResIAQFan', 'ResLpTankHtr']:
            return 85

        # 5. Building structure
        if tag == 'Bldg':
            return 100

        # 6. Commercial HVAC system structure
        if tag in ['AirSys', 'FluidSys', 'VRFSys', 'ZnSys']:
            return 200

        # 7. Equipment catalog objects
        if tag in ['Lum', 'WtrHtr', 'Chiller', 'Boiler', 'Pump', 'ThrmlEngyStor',
                   'PVArray', 'Batt']:
            return 600

        # 8. HERS/Compliance objects
        if tag in ['HERSCool', 'HERSHeat', 'HERSHtPump', 'HERSDist', 'HERSFan',
                   'HERSDHWSys', 'HERSOther', 'SpeclFtr']:
            return 700

        # 9. DwellUnitType - AFTER all DwellUnit instances (inside Bldg)
        if tag == 'DwellUnitType':
            return 900

        # 10. HVAC SYSTEMS - AFTER DwellUnitType (matches Euclid end order)
        # These are system assignments that reference DwellUnitType
        if tag in ['ResHVACSys', 'ResDHWSys', 'ResDWHRSys', 'ResWtrHtr']:
            return 950

        # 10. Report objects (always last)
        if tag in ['ResDHWSysRpt', 'DwellUnitRpt', 'ResIAQVentRpt', 'ResSCSysRpt', 'EUseSummary']:
            return 1000

        # Default: middle priority
        return 500

    def _is_immediate_sibling(self, child_tag: str, parent_tag: str) -> bool:
        """
        Determine if extracted child should be written immediately after parent.

        Residential zone children need immediate writing to maintain proper ordering.
        Commercial HVAC children also need immediate writing to maintain hierarchy.
        Other extractions (schedules, etc.) can be deferred to end.
        """
        # CRITICAL: Children of Bldg (ResZnGrp) must be written immediately after Bldg
        # This maintains proper CBECC GUI hierarchy: Bldg → ResZnGrp → ResZn → geometry
        # If deferred, ResProj/schedules get written first, breaking GUI display
        if parent_tag == 'Bldg' and child_tag == 'ResZnGrp':
            return True

        # Children of Story (commercial spaces) must be written immediately after Story
        # CRITICAL: This maintains proper CBECC GUI hierarchy: Story → Spc → envelope
        # If deferred, spaces appear under wrong stories in GUI tree
        if parent_tag == 'Story' and child_tag == 'Spc':
            return True

        # Children of ResZn/ResOtherZn must be written immediately after the zone
        if parent_tag in ['ResZn', 'ResOtherZn']:
            if child_tag in ['DwellUnit', 'ResExtWall', 'ResIntWall', 'ResSlabFlr',
                            'ResIntFlr', 'ResCathedralCeiling', 'ResCeilingBelowAttic',
                            'ResOpening', 'ResExtFlr', 'ResAtticRoof', 'IntLtgSys']:
                return True

        # Children of Spc (commercial) must be written immediately after the space
        # CRITICAL: This maintains proper CBECC GUI hierarchy: Spc → envelope components
        # If deferred, envelope elements appear at end of file, breaking parent-child display
        if parent_tag == 'Spc':
            if child_tag in ['ExtWall', 'IntWall', 'UndgrFlr', 'UndgrWall', 'Flr', 'Roof',
                            'Ceiling', 'IntFlr', 'ExtFlr', 'IntLtgSys']:
                return True

        # Children of ResExtWall must be written immediately
        if parent_tag == 'ResExtWall' and child_tag in ['ResWin', 'ResDr']:
            return True

        # Children of ExtWall (commercial) must be written immediately
        if parent_tag == 'ExtWall' and child_tag in ['Win', 'Dr']:
            return True

        # Children of ResAtticRoof must be written immediately
        if parent_tag == 'ResAtticRoof' and child_tag == 'ResSkylt':
            return True

        # Children of ResZnGrp (ResZn, ResOtherZn) must be written immediately
        if parent_tag == 'ResZnGrp' and child_tag in ['ResZn', 'ResOtherZn', 'ResAttic']:
            return True

        # Children of AirSys must be written immediately after the parent
        if parent_tag == 'AirSys' and child_tag in ['AirSeg', 'TrmlUnit', 'OACtrl']:
            return True

        # Children of AirSeg must be written immediately after the parent
        if parent_tag == 'AirSeg' and child_tag in ['CoilClg', 'CoilHtg', 'Fan']:
            return True

        # Children of FluidSys must be written immediately after the parent
        if parent_tag == 'FluidSys' and child_tag == 'FluidSeg':
            return True

        # All other extractions are deferred
        return False

    def _requires_quotes(self, prop_name: str) -> bool:
        """
        Check if property should always be quoted (even if numeric-looking).

        This handles properties where CBECC schema defines them as STRING or ENUM type
        even though they may contain digits or look numeric.
        """
        # Properties that must be quoted (STRING or ENUM fields in CBECC schema)
        always_quote = [
            # Author/document metadata (STRING fields)
            'DocAuthZipCode',      # Author ZIP - STRING (can have leading zeros)
            'DocAuthAddress',      # Author address
            'DocAuthCity',         # Author city
            'DocAuthState',        # Author state
            'DocAuthCompany',      # Author company

            # Location/weather (STRING fields)
            'StAddress',           # Street address
            'City',                # City name
            'State',               # State abbreviation
            'WeatherStation',      # Weather station name
            'WeatherFileName',     # Weather file name
            'DDWeatherFile',       # Design day weather file
            'AnnualWeatherFile',   # Annual weather file
            'AnnualWeatherFileNoPath',  # Weather file (no path)

            # Date/time strings (STRING fields)
            'RunDateFmt',          # Formatted date
            'RunDateISO',          # ISO date

            # Enum/choice properties (always quoted in CBECC)
            'Status',              # Component status (New, Existing, etc.)
            'DryerFuel',           # Dryer fuel type
            'CookingApplType',     # Cooking appliance type
            'CliZn',               # Climate zone (e.g., "ClimateZone12")
            'Orientation',         # Orientation (Front, Back, Left, Right)
            'GasType',             # Gas type (NaturalGas, Propane)
            'AnalysisType',        # Analysis type
            'SimSpeedOption',      # Simulation speed option

            # Exception conditions (enum fields)
            'ExcptCondNoClgSys',   # "Yes" or "No"
            'ExcptCondRtdCap',     # "Yes" or "No"
            'ExcptCondNarrative',  # "Yes" or "No"

            # Construction properties (STRING/ENUM fields)
            'Type',                # Component type (generic enum)
            'CanAssignTo',         # Construction assignment type
            'MassLayer',           # Mass layer material name
            'MassThickness',       # Mass thickness (e.g., "8 in.", "- none -")

            # HVAC properties (enum fields)
            'FanCtrlMthd',         # Fan control method
            'FuelType',            # Fuel type

            # Residential properties (enum fields)
            'InsulConsQuality',    # Insulation quality ("No", "Yes")
            'UnitClVentOption',    # Unit ventilation option

            # Special format strings
            'SoftwareVersion',     # Version string (e.g., "CBECC 2025.1.0 (1381)")
            'RunTitle',            # Run title
            'ResultsCurrentMessage',  # Results message

            # NOTE: 'ZipCode' is an INTEGER field - should NOT be quoted
        ]
        return prop_name in always_quote

    def _get_property_type(self, prop_name: str, prop_value: str) -> str:
        """
        Determine property type for quoting decisions.

        Args:
            prop_name: Name of the property
            prop_value: Value of the property

        Returns:
            'string', 'number', 'reference', or 'enum'
        """
        # Force-quoted properties (from _requires_quotes)
        if self._requires_quotes(prop_name):
            return 'string'

        # Numeric properties (never quoted) - CHECK BEFORE REFERENCE PATTERNS
        # This is crucial because some numeric properties like BldgEngyModelVersion
        # contain substrings that match reference patterns (e.g., 'Bldg')
        if self._is_number(prop_value):
            return 'number'

        # Reference properties (always quoted)
        if self._is_reference(prop_name):
            return 'reference'

        # Boolean-like keywords (quoted as enums)
        if prop_value and prop_value.lower() in ['true', 'false', 'yes', 'no']:
            return 'enum'

        # Default to string (quoted)
        return 'string'

    def _is_string_value(self, value: str) -> bool:
        """Check if value should be quoted as string."""
        if value is None:
            return False

        # Check if it's a number
        if self._is_number(value):
            return False

        # Check if it's a boolean-like keyword
        if value.lower() in ['true', 'false', 'yes', 'no']:
            return True

        # Everything else is a string
        return True


def convert_xml_to_text(xml_path: str, text_path: str):
    """
    Convenience function to convert XML to text format.

    Args:
        xml_path: Path to input XML file
        text_path: Path for output text file
    """
    converter = CIBDXMLToTextConverter()
    converter.convert_file(xml_path, text_path)


if __name__ == '__main__':
    import sys
    if len(sys.argv) != 3:
        print("Usage: python cibd_xml_to_text.py <input.xml> <output.cibd25>")
        sys.exit(1)

    convert_xml_to_text(sys.argv[1], sys.argv[2])
    print(f"✅ Converted {sys.argv[1]} → {sys.argv[2]}")
