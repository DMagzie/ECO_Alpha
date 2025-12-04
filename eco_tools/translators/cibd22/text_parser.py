"""
CIBD22 Text Format Parser

Parses CIBD22's proprietary text-based format with indentation and converts
to an XML-like structure that can be processed by CIBD22X parsers.

CIBD22 uses text format with:
- Objects: ObjectType "name"
- Properties: key = value
- Arrays: key[index] = value
- Terminators: ".."
- Nested objects through indentation

Example:
    ResZn "Living Room"
       FloorArea = 500
       ..
"""

from typing import Dict, Any, List, Optional
import re
import xml.etree.ElementTree as ET


class CIBD22TextParser:
    """
    Parser for CIBD22 text-based format.

    Converts text format to XML ElementTree structure that matches CIBD22X,
    allowing reuse of CIBD22X modular parsers.
    """

    # Mapping from CIBD22 (text) names to CIBD22X (XML) names
    TYPE_MAPPING = {
        "Proj": "Proj",
        "ResProj": "ResProj",  # Residential project properties (critical for CBECC validation)
        "ProjVar": "ProjVar",  # Project variables
        "Bldg": "Bldg",
        "Story": "Story",
        "Spc": "Spc",
        "ResZn": "ThrmlZn",  # Residential Zone → Thermal Zone
        "ResWin": "Win",     # Residential Window → Window
        "ResExtWall": "ExtWall",  # Residential External Wall
        "ResIntWall": "IntWall",
        "ResCeiling": "Ceiling",
        "ResFloor": "FlrOnGrade",
        "ResRoof": "Roof",
        "ResWinType": "FenCons",  # Window Type → Fenestration Construction
        "ResConsAssm": "ConsAssm",  # Construction Assembly
        "DwellUnitType": "DwellUnitType",
        "DwellUnit": "DwellUnit",
        "HVACSys": "HVACSys",
        "ZnSys": "ZnSys",
        "AirSeg": "AirSeg",
    }

    def __init__(self):
        self.objects: List[Dict[str, Any]] = []
        self.current_stack: List[Dict[str, Any]] = []
        self.root_metadata: Dict[str, str] = {}  # For RulesetFilename and other top-level properties

    def parse(self, text: str) -> ET.Element:
        """
        Parse CIBD22 text format into XML ElementTree.

        Args:
            text: Raw CIBD22 file content

        Returns:
            XML Element root compatible with CIBD22X parsers
        """
        self.objects = []
        self.current_stack = []
        self.root_metadata = {}

        lines = text.split('\n')

        for line_num, line in enumerate(lines, 1):
            # Skip empty lines and comments
            if not line.strip() or line.strip().startswith('//'):
                continue

            # Check for object terminator
            if line.strip() == "..":
                if self.current_stack:
                    self.current_stack.pop()
                continue

            # Parse top-level standalone properties (e.g., RulesetFilename "T24_2025.bin")
            # These appear at the root level before any objects
            # Only match known metadata properties, NOT object types
            standalone_prop_match = re.match(r'^(RulesetFilename|AnalysisType|ComplianceReportPDF)\s+"([^"]+)"', line)
            if standalone_prop_match and not self.current_stack:
                prop_name = standalone_prop_match.group(1)
                prop_value = standalone_prop_match.group(2)
                self.root_metadata[prop_name] = prop_value
                continue

            # Parse object definition: ObjectType "name"
            obj_match = re.match(r'^(\s*)([A-Z][a-zA-Z0-9]+)\s+"([^"]+)"', line)
            if obj_match:
                indent_level = len(obj_match.group(1)) // 3  # Assume 3-space indent
                obj_type = obj_match.group(2)
                obj_name = obj_match.group(3)

                # Map type name
                xml_type = self.TYPE_MAPPING.get(obj_type, obj_type)

                new_obj = {
                    "_type": xml_type,
                    "_name": obj_name,
                    "_children": [],
                    "_properties": {},
                    "_line": line_num,
                    "_indent": indent_level
                }

                # Adjust stack to match indent level
                while len(self.current_stack) > indent_level:
                    self.current_stack.pop()

                # Add to parent or root
                if self.current_stack:
                    self.current_stack[-1]["_children"].append(new_obj)
                else:
                    self.objects.append(new_obj)

                self.current_stack.append(new_obj)
                continue

            # Parse property: key = value or key[index] = value
            prop_match = re.match(r'^(\s*)([A-Za-z][A-Za-z0-9_]*)\s*(?:\[(\d+)\])?\s*=\s*(.+)', line)
            if prop_match and self.current_stack:
                key = prop_match.group(2)
                index = prop_match.group(3)
                value = prop_match.group(4).strip()

                # Remove quotes from string values
                if value.startswith('"') and value.endswith('"'):
                    value = value[1:-1]
                else:
                    # Try to convert to number
                    try:
                        if '.' in value:
                            value = float(value)
                        else:
                            value = int(value)
                    except ValueError:
                        pass  # Keep as string

                # Handle array properties
                if index:
                    if key not in self.current_stack[-1]["_properties"]:
                        self.current_stack[-1]["_properties"][key] = []
                    # Ensure list is large enough
                    idx = int(index)
                    arr = self.current_stack[-1]["_properties"][key]
                    while len(arr) <= idx:
                        arr.append(None)
                    arr[idx] = value
                else:
                    self.current_stack[-1]["_properties"][key] = value

        # Convert parsed objects to XML
        root = ET.Element("SDDXML")

        # Add root metadata as attributes to preserve them
        for key, value in self.root_metadata.items():
            root.set(key, value)

        for obj in self.objects:
            self._obj_to_xml(obj, root)

        # Post-process: Move surfaces from root level to parent zones
        self._reorganize_surfaces(root)

        # Post-process: Move openings from root level to parent surfaces
        self._reorganize_openings(root)

        return root

    def _obj_to_xml(self, obj: Dict[str, Any], parent: ET.Element) -> ET.Element:
        """
        Convert parsed object dictionary to XML Element.

        Args:
            obj: Parsed object dictionary
            parent: Parent XML element

        Returns:
            Created XML element
        """
        # Create element
        elem = ET.SubElement(parent, obj["_type"])

        # Add name as <n> child element (CIBD22X format expects this)
        if obj["_name"]:
            name_elem = ET.SubElement(elem, "n")
            name_elem.text = obj["_name"]

        # Add properties as child elements or attributes
        for key, value in obj["_properties"].items():
            if isinstance(value, list):
                # Array property - create multiple child elements with index attribute
                # CRITICAL: CIBD22 text uses 1-based indexing (DHWHeater[1])
                # CIBD22X XML uses 0-based indexing (index="0")
                # So we need to convert: text index 1 → XML index 0
                xml_index = 0
                for item in value:
                    if item is not None:
                        prop_elem = ET.SubElement(elem, key)
                        # Use 0-based index for XML (first non-None gets index="0")
                        prop_elem.set('index', str(xml_index))
                        prop_elem.text = str(item)
                        xml_index += 1
            elif value is not None:
                # Single property - create child element
                prop_elem = ET.SubElement(elem, key)
                prop_elem.text = str(value)

        # Add child objects
        for child in obj["_children"]:
            self._obj_to_xml(child, elem)

        return elem

    def _reorganize_surfaces(self, root: ET.Element):
        """
        Post-process XML to move surfaces from root level to parent zones.

        In CIBD22 text format, surfaces are siblings of zones (same indentation).
        But in CIBD22X XML format, surfaces must be children of zones.

        This method reorganizes the tree by:
        1. Finding all zone elements and creating a zone name → element mapping
        2. Finding all surface elements at root level
        3. Extracting parent zone name from surface name
        4. Moving surface to be child of parent zone

        Example: "ExtWall_Front_ResZn_A1_Corner_L01" contains "ResZn_A1_Corner_L01"

        NOTE: Openings (ResWin, Win, ResDr, etc.) are handled separately by _reorganize_openings()
        """
        # Surface tags to reorganize (excludes openings - handled by _reorganize_openings)
        # Includes both residential (Res*) and commercial surface types
        surface_tags = {
            # Residential surfaces
            'ResExtWall', 'ResIntWall', 'ResSlabFlr', 'ResCathedralCeiling',
            'ResAtticRoof', 'ResOtherFlr', 'ResIntFlr', 'ResUndgrWall', 'ResUndgrFlr',
            'ResCeilingBelowAttic', 'ResRoof', 'ResCeiling',  # Additional residential
            # Commercial surfaces
            'ExtWall', 'IntWall', 'Roof', 'FlrOnGrade', 'Ceiling', 'FlrAbvAttic',
            'UndgrWall', 'UndgrFlr', 'ExtFlr', 'IntFlr', 'FlrBelowAttic',
        }

        # Zone tags
        zone_tags = {'ThrmlZn', 'ResZn', 'ComZn', 'Spc', 'ResOtherZn'}

        # Build zone name → element mapping
        zone_map = {}
        for zone_elem in root.iter():
            if zone_elem.tag in zone_tags:
                name_elem = zone_elem.find('n')
                if name_elem is not None and name_elem.text:
                    zone_map[name_elem.text] = zone_elem

        # Find surfaces at root level that need to be moved
        # Strategy 1: Name-based matching (residential - surface names contain zone)
        # Strategy 2: Sequential ordering (commercial - surfaces follow their parent zone)
        surfaces_to_move = []
        current_zone = None  # Track most recent zone for sequential ordering

        for elem in list(root):  # list() to avoid modifying during iteration
            # Track zones for sequential ordering
            if elem.tag in zone_tags:
                name_elem = elem.find('n')
                if name_elem is not None and name_elem.text:
                    current_zone = zone_map.get(name_elem.text)
                continue

            if elem.tag in surface_tags:
                name_elem = elem.find('n')
                if name_elem is not None and name_elem.text:
                    surface_name = name_elem.text

                    # Strategy 1: Try to find parent zone name in surface name (residential)
                    parent_zone_elem = None
                    for zone_name in zone_map:
                        if zone_name in surface_name:
                            parent_zone_elem = zone_map[zone_name]
                            break

                    # Strategy 2: Fall back to sequential ordering (commercial)
                    if not parent_zone_elem and current_zone is not None:
                        parent_zone_elem = current_zone

                    if parent_zone_elem:
                        surfaces_to_move.append((elem, parent_zone_elem))

        # Move surfaces under parent zones
        for surf_elem, parent_zone_elem in surfaces_to_move:
            root.remove(surf_elem)
            parent_zone_elem.append(surf_elem)

    def _reorganize_openings(self, root: ET.Element):
        """
        Post-process XML to move openings from root level to parent surfaces.

        In CIBD22 text format, openings (windows, doors) are siblings of surfaces.
        But in CIBD22X XML format, openings must be children of surfaces.

        Opening names follow the pattern: "Window (Orientation N) : ZoneName"
        Surface names follow the pattern: "ExtWall (Orientation N) : ZoneName"

        The matching is done by:
        1. Extract orientation and zone from opening name
        2. Find surface with matching orientation and zone
        3. Move opening to be child of that surface

        Example:
        - Opening: "Window (Back 1) : Res_West Facing_L01"
        - Surface: "ExtWall (Back 1) : Res_West Facing_L01"
        """
        import re

        # Opening tags to reorganize
        opening_tags = {'ResWin', 'Win', 'ResDr', 'Dr', 'ResSkylt', 'Skylt',
                       'Window', 'Door', 'Skylight'}

        # Surface tags that can contain openings (must be in zones already)
        parent_surface_tags = {'ResExtWall', 'ResIntWall', 'ExtWall', 'IntWall',
                              'ResCathedralCeiling', 'ResAtticRoof', 'Roof', 'Ceiling',
                              'ResCeilingBelowAttic', 'ResRoof', 'ResCeiling'}

        # Wall-type surfaces for sequential ordering fallback
        # Only wall surfaces should be tracked for sequential ordering
        # (windows without exact matches go to preceding wall, not ceiling)
        wall_surface_tags = {'ResExtWall', 'ResIntWall', 'ExtWall', 'IntWall'}

        # Build surface mapping: (orientation, zone_name) → surface element
        # Also build name → element mapping for fallback
        surface_map = {}  # (orientation, zone) → element
        surface_by_name = {}  # surface_name → element

        for surf_elem in root.iter():
            if surf_elem.tag in parent_surface_tags:
                name_elem = surf_elem.find('n')
                if name_elem is not None and name_elem.text:
                    surface_name = name_elem.text
                    surface_by_name[surface_name] = surf_elem

                    # Parse surface name: "ExtWall (Orientation N) : ZoneName"
                    match = re.match(r'.*?\(([^)]+)\)\s*:\s*(.+)', surface_name)
                    if match:
                        orientation = match.group(1).strip()
                        zone_name = match.group(2).strip()
                        key = (orientation, zone_name)
                        surface_map[key] = surf_elem

        # Find openings at any level that need to be moved
        # Strategy 1: Name-based matching (residential - opening names contain orientation and zone)
        # Strategy 2: Sequential ordering (commercial - openings follow their parent surface)
        openings_to_move = []
        current_surface = None  # Track most recent surface for sequential ordering

        def find_openings(parent_elem, track_sequence=True):
            """Recursively find openings in element tree."""
            nonlocal current_surface

            for elem in list(parent_elem):
                # Track WALL surfaces for sequential ordering
                # (only walls can have windows as fallback parents, not ceilings)
                if elem.tag in wall_surface_tags:
                    name_elem = elem.find('n')
                    if name_elem is not None and name_elem.text:
                        current_surface = elem

                if elem.tag in opening_tags:
                    name_elem = elem.find('n')
                    if name_elem is not None and name_elem.text:
                        opening_name = name_elem.text
                        parent_surface = None

                        # Strategy 1: Parse residential opening name: "Window (Orientation N) : ZoneName"
                        match = re.match(r'.*?\(([^)]+)\)\s*:\s*(.+)', opening_name)
                        if match:
                            orientation = match.group(1).strip()
                            zone_name = match.group(2).strip()
                            key = (orientation, zone_name)

                            # Find matching surface
                            if key in surface_map:
                                parent_surface = surface_map[key]
                            else:
                                # Fallback: find any surface containing the zone name and orientation
                                for surf_name, surf_elem in surface_by_name.items():
                                    if zone_name in surf_name and orientation in surf_name:
                                        parent_surface = surf_elem
                                        break

                        # Strategy 2: Fall back to sequential ordering (commercial)
                        if not parent_surface and current_surface is not None:
                            parent_surface = current_surface

                        if parent_surface:
                            openings_to_move.append((elem, parent_elem, parent_surface))
                else:
                    # Recurse into non-opening elements
                    find_openings(elem, track_sequence=False)

        find_openings(root)

        # Move openings under parent surfaces
        for open_elem, old_parent, new_parent_surf in openings_to_move:
            if old_parent is not None:
                try:
                    old_parent.remove(open_elem)
                except ValueError:
                    pass  # Already removed
            new_parent_surf.append(open_elem)


def parse_cibd22_file(file_path: str) -> ET.Element:
    """
    Parse CIBD22 text file to XML ElementTree.

    Args:
        file_path: Path to CIBD22 text file

    Returns:
        XML Element root compatible with CIBD22X parsers
    """
    # CBECC files use latin-1 encoding (contain special chars like superscript 2)
    # Try latin-1 first, fall back to utf-8 with replacement for other files
    for encoding in ['latin-1', 'windows-1252', 'utf-8']:
        try:
            with open(file_path, 'r', encoding=encoding) as f:
                text = f.read()
            break
        except (UnicodeDecodeError, LookupError):
            if encoding == 'utf-8':
                # Last resort - replace invalid chars
                with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                    text = f.read()

    parser = CIBD22TextParser()
    return parser.parse(text)
