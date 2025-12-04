"""
Unified CIBD Text Format Parser

Parses both CIBD22 and CIBD25 proprietary text-based formats and converts
to an XML-like structure that can be processed by modular parsers.

Both formats use identical structure:
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
import logging

from .version_config import (
    CIBDVersion,
    ELEMENT_TYPE_MAPPING,
    SURFACE_TYPES,
    ZONE_TYPES,
    OPENING_TYPES,
    WALL_SURFACE_TYPES,
    ROOT_METADATA_PROPERTIES,
    PROJECT_NESTED_ELEMENTS,
    detect_version,
)

logger = logging.getLogger(__name__)


class CIBDTextParser:
    """
    Unified parser for CIBD text-based formats (CIBD22 and CIBD25).

    Converts text format to XML ElementTree structure that can be processed
    by the modular CIBD22X parsers.
    """

    def __init__(self, version: CIBDVersion = None):
        """
        Initialize parser.

        Args:
            version: Target version (auto-detected if None)
        """
        self.version = version
        self.objects: List[Dict[str, Any]] = []
        self.current_stack: List[Dict[str, Any]] = []
        self.root_metadata: Dict[str, str] = {}

    def parse(self, text: str) -> ET.Element:
        """
        Parse CIBD text format into XML ElementTree.

        Args:
            text: Raw CIBD file content

        Returns:
            XML Element root compatible with CIBD22X parsers
        """
        # Auto-detect version if not specified
        if self.version is None:
            self.version = detect_version(text)
            logger.info(f"Auto-detected CIBD version: {self.version.value}")

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
            standalone_prop_match = re.match(
                r'^(' + '|'.join(ROOT_METADATA_PROPERTIES) + r')\s+"([^"]+)"',
                line
            )
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

                # Map type name using version-aware mapping
                xml_type = ELEMENT_TYPE_MAPPING.get(obj_type, obj_type)

                new_obj = {
                    "_type": xml_type,
                    "_original_type": obj_type,  # Preserve original for export
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

        # Add root metadata as attributes
        for key, value in self.root_metadata.items():
            root.set(key, value)

        # Add version info
        root.set("_cibd_version", self.version.value)

        for obj in self.objects:
            self._obj_to_xml(obj, root)

        # Post-process: Move zones from root level to parent zone groups
        # CRITICAL: Must run BEFORE _reorganize_surfaces because surfaces
        # need to be moved inside zones, which first need to be inside zone groups
        self._reorganize_zones(root)

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
        # Create element with mapped type
        elem = ET.SubElement(parent, obj["_type"])

        # Store original type for export
        if obj["_original_type"] != obj["_type"]:
            elem.set("_original_type", obj["_original_type"])

        # Add name as <n> child element
        if obj["_name"]:
            name_elem = ET.SubElement(elem, "n")
            name_elem.text = obj["_name"]

        # Add properties as child elements
        for key, value in obj["_properties"].items():
            if isinstance(value, list):
                # Array property - create multiple child elements with index attribute
                # CIBD22 text uses 1-based indexing, XML uses 0-based
                xml_index = 0
                for item in value:
                    if item is not None:
                        prop_elem = ET.SubElement(elem, key)
                        prop_elem.set('index', str(xml_index))
                        prop_elem.text = str(item)
                        xml_index += 1
            elif value is not None:
                prop_elem = ET.SubElement(elem, key)
                prop_elem.text = str(value)

        # Add child objects
        for child in obj["_children"]:
            self._obj_to_xml(child, elem)

        return elem

    def _reorganize_zones(self, root: ET.Element):
        """
        Post-process XML to move zones from root level to parent zone groups.

        In CIBD text format, ResZnGrp and ResZn are both at root level:
            ResZnGrp   "Floor 1"
               TreeState = 254
               ..
            ResZn   "Zone1"
               FloorArea = 3660
               ..
            ResZn   "Zone2"
               FloorArea = 4000
               ..
            ResZnGrp   "Floor 2"
               ..
            ResZn   "Zone3"
               ...

        Zones following a ResZnGrp belong to that group until the next ResZnGrp.
        This method moves each zone inside its parent zone group.
        """
        # Collect zone groups in order
        zone_groups = []
        for elem in list(root):
            if elem.tag == 'ResZnGrp':
                zone_groups.append(elem)

        if not zone_groups:
            return  # No zone groups to organize

        # Find zones at root level and map to their parent zone group
        zones_to_move = []
        current_zone_group = None

        for elem in list(root):
            if elem.tag == 'ResZnGrp':
                current_zone_group = elem
                continue

            # Check if this is a zone element
            if elem.tag in ZONE_TYPES and current_zone_group is not None:
                zones_to_move.append((elem, current_zone_group))

        # Move zones inside their parent zone group
        for zone_elem, parent_zg in zones_to_move:
            root.remove(zone_elem)
            parent_zg.append(zone_elem)

        logger.debug(f"Reorganized {len(zones_to_move)} zones into zone groups")

    def _reorganize_surfaces(self, root: ET.Element):
        """
        Post-process XML to move surfaces from root level to parent zones.

        Uses two strategies:
        1. Name-based matching (residential - surface names contain zone)
        2. Sequential ordering (commercial - surfaces follow their parent zone)
        """
        # Build zone name → element mapping
        zone_map = {}
        for zone_elem in root.iter():
            if zone_elem.tag in ZONE_TYPES:
                name_elem = zone_elem.find('n')
                if name_elem is not None and name_elem.text:
                    zone_map[name_elem.text] = zone_elem

        # Find surfaces at root level that need to be moved
        surfaces_to_move = []
        current_zone = None

        for elem in list(root):
            # Track zones for sequential ordering
            if elem.tag in ZONE_TYPES:
                name_elem = elem.find('n')
                if name_elem is not None and name_elem.text:
                    current_zone = zone_map.get(name_elem.text)
                continue

            if elem.tag in SURFACE_TYPES:
                name_elem = elem.find('n')
                if name_elem is not None and name_elem.text:
                    surface_name = name_elem.text

                    # Strategy 1: Try to find parent zone name in surface name
                    parent_zone_elem = None
                    for zone_name in zone_map:
                        if zone_name in surface_name:
                            parent_zone_elem = zone_map[zone_name]
                            break

                    # Strategy 2: Fall back to sequential ordering
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

        Uses orientation and zone matching from opening/surface names.
        Falls back to sequential ordering for commercial buildings.
        """
        # Build surface mapping
        surface_map = {}  # (orientation, zone) → element
        surface_by_name = {}  # surface_name → element

        for surf_elem in root.iter():
            if surf_elem.tag in SURFACE_TYPES:
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

        # Find openings that need to be moved
        openings_to_move = []
        current_surface = None

        def find_openings(parent_elem):
            nonlocal current_surface

            for elem in list(parent_elem):
                # Track WALL surfaces for sequential ordering
                if elem.tag in WALL_SURFACE_TYPES:
                    name_elem = elem.find('n')
                    if name_elem is not None and name_elem.text:
                        current_surface = elem

                if elem.tag in OPENING_TYPES:
                    name_elem = elem.find('n')
                    if name_elem is not None and name_elem.text:
                        opening_name = name_elem.text
                        parent_surface = None

                        # Strategy 1: Parse opening name
                        match = re.match(r'.*?\(([^)]+)\)\s*:\s*(.+)', opening_name)
                        if match:
                            orientation = match.group(1).strip()
                            zone_name = match.group(2).strip()
                            key = (orientation, zone_name)

                            if key in surface_map:
                                parent_surface = surface_map[key]
                            else:
                                # Fallback: find any surface with matching zone and orientation
                                for surf_name, surf_elem in surface_by_name.items():
                                    if zone_name in surf_name and orientation in surf_name:
                                        parent_surface = surf_elem
                                        break

                        # Strategy 2: Fall back to sequential ordering
                        if not parent_surface and current_surface is not None:
                            parent_surface = current_surface

                        if parent_surface:
                            openings_to_move.append((elem, parent_elem, parent_surface))
                else:
                    find_openings(elem)

        find_openings(root)

        # Move openings under parent surfaces
        for open_elem, old_parent, new_parent_surf in openings_to_move:
            if old_parent is not None:
                try:
                    old_parent.remove(open_elem)
                except ValueError:
                    pass
            new_parent_surf.append(open_elem)


def parse_cibd_file(file_path: str, version: CIBDVersion = None) -> ET.Element:
    """
    Parse CIBD text file to XML ElementTree.

    Args:
        file_path: Path to CIBD text file
        version: Target version (auto-detected if None)

    Returns:
        XML Element root compatible with modular parsers
    """
    # CBECC files use latin-1 encoding
    for encoding in ['latin-1', 'windows-1252', 'utf-8']:
        try:
            with open(file_path, 'r', encoding=encoding) as f:
                text = f.read()
            break
        except (UnicodeDecodeError, LookupError):
            if encoding == 'utf-8':
                with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                    text = f.read()

    parser = CIBDTextParser(version)
    return parser.parse(text)
