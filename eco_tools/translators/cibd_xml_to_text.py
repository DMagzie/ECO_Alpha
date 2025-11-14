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

        with open(output_path, 'w', encoding='utf-8') as f:
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
                output.write(f'{attr_name}   "{attr_value}"  \n')

        if root.attrib:
            output.write('\n')

        # Process child elements
        for child in root:
            self._write_object(child, output, indent=0)

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

        # Get object name from 'Name' or 'n' child or text content
        obj_name = None
        properties = []
        child_objects = []

        for child in elem:
            child_tag = child.tag.replace(self.namespace, '') if self.namespace else child.tag

            if child_tag == 'n':
                obj_name = child.text
            elif child_tag == 'Name':
                # Use Name as the object name for all objects
                obj_name = child.text
            elif len(child) > 0:
                # Has children - it's a nested object
                child_objects.append(child)
            else:
                # Leaf node - it's a property
                properties.append((child_tag, child.text))

        # If no name found, check if element has text content
        if obj_name is None and elem.text and elem.text.strip():
            obj_name = elem.text.strip()

        # Write object header
        indent_str = '   ' * indent
        if obj_name:
            output.write(f'{indent_str}{tag}   "{obj_name}"  \n')
        else:
            # Some objects don't have names
            output.write(f'{indent_str}{tag}\n')

        # Write properties
        for prop_name, prop_value in properties:
            if prop_value is None:
                continue

            # Skip Name if it was used as object name
            if prop_name == 'Name' and obj_name == prop_value:
                continue

            # Skip properties that are defined as root attributes (they're written at top level)
            if hasattr(self, 'root_attributes') and prop_name in self.root_attributes:
                continue

            # Detect if this is a reference (array or single)
            array_match = re.match(r'(.+)\[(\d+)\]', prop_name)

            if array_match:
                # Array reference: MatRef[1] = "Material Name"
                base_name = array_match.group(1)
                index = array_match.group(2)
                output.write(f'{indent_str}   {base_name}[{index}] = "{prop_value}"\n')
            elif self._is_number(prop_value):
                # Numeric value (no quotes)
                output.write(f'{indent_str}   {prop_name} = {prop_value}\n')
            elif self._is_reference(prop_name):
                # Single reference: ConsAssmRef = "Assembly Name"
                output.write(f'{indent_str}   {prop_name} = "{prop_value}"\n')
            elif self._is_string_value(prop_value):
                # String value
                output.write(f'{indent_str}   {prop_name} = "{prop_value}"\n')
            else:
                # Default to numeric (no quotes)
                output.write(f'{indent_str}   {prop_name} = {prop_value}\n')

        # Write nested objects
        for child_obj in child_objects:
            self._write_object(child_obj, output, indent + 1)

        # Write object terminator
        output.write(f'{indent_str}   ..\n\n')

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
