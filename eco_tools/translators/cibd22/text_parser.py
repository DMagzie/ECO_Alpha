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
        for obj in self.objects:
            self._obj_to_xml(obj, root)

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

        # Add Name attribute if present
        if obj["_name"]:
            elem.set("Name", obj["_name"])

        # Add properties as child elements or attributes
        for key, value in obj["_properties"].items():
            if isinstance(value, list):
                # Array property - create multiple child elements
                for item in value:
                    if item is not None:
                        prop_elem = ET.SubElement(elem, key)
                        prop_elem.text = str(item)
            elif value is not None:
                # Single property - create child element
                prop_elem = ET.SubElement(elem, key)
                prop_elem.text = str(value)

        # Add child objects
        for child in obj["_children"]:
            self._obj_to_xml(child, elem)

        return elem


def parse_cibd22_file(file_path: str) -> ET.Element:
    """
    Parse CIBD22 text file to XML ElementTree.

    Args:
        file_path: Path to CIBD22 text file

    Returns:
        XML Element root compatible with CIBD22X parsers
    """
    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
        text = f.read()

    parser = CIBD22TextParser()
    return parser.parse(text)
