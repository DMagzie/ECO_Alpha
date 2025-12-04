"""
CIBD25 Text Format Reader

Parses CIBD25 text files into structured dictionaries for easy querying.
CIBD25 uses the same indentation-based text format as CIBD22.

Format:
    ElementType   "Name"
       Property = Value
       NestedElement   "Child Name"
          Property = Value
       ..
    ..

This reader provides a find_objects() API compatible with the CIBD25 importer.
"""

from typing import Dict, List, Any, Optional
import re
from dataclasses import dataclass, field


@dataclass
class ParsedObject:
    """Represents a parsed CIBD element."""
    obj_type: str
    name: str
    properties: Dict[str, Any] = field(default_factory=dict)
    children: List['ParsedObject'] = field(default_factory=list)
    parent: Optional['ParsedObject'] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format expected by importer."""
        return {
            "_type": self.obj_type,
            "_name": self.name,
            "_properties": self.properties,
            "_children": [child.to_dict() for child in self.children]
        }


class CIBD25TextReader:
    """
    Reader for CIBD25 text format files.

    Provides find_objects() method for querying parsed elements.
    """

    def __init__(self):
        self.objects: List[ParsedObject] = []
        self.all_objects: Dict[str, List[ParsedObject]] = {}

    def parse_file(self, file_path: str) -> None:
        """
        Parse a CIBD25 text file.

        Args:
            file_path: Path to CIBD25 file
        """
        # Try multiple encodings (CBECC files often use latin-1)
        for encoding in ['latin-1', 'windows-1252', 'utf-8']:
            try:
                with open(file_path, 'r', encoding=encoding) as f:
                    text = f.read()
                break
            except (UnicodeDecodeError, LookupError):
                if encoding == 'utf-8':
                    # Last resort
                    with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                        text = f.read()

        self._parse_text(text)

    def _parse_text(self, text: str) -> None:
        """Parse CIBD25 text into structured objects."""
        lines = text.split('\n')

        # Stack to track nesting: [(object, indent_level)]
        stack: List[tuple[ParsedObject, int]] = []
        current_obj: Optional[ParsedObject] = None

        i = 0
        while i < len(lines):
            line = lines[i]

            # Skip empty lines
            if not line.strip():
                i += 1
                continue

            # Check for element end marker
            if line.strip() == '..':
                # Pop from stack
                if stack:
                    stack.pop()
                    if stack:
                        current_obj = stack[-1][0]
                    else:
                        current_obj = None
                i += 1
                continue

            # Calculate indentation
            indent = len(line) - len(line.lstrip())

            # Check if this is an element definition
            elem_match = re.match(r'^(\s*)(\w+)\s+"([^"]+)"', line)
            if elem_match:
                indent_str, elem_type, name = elem_match.groups()
                indent = len(indent_str)

                # Create new object
                new_obj = ParsedObject(obj_type=elem_type, name=name)

                # Determine parent based on indentation
                while stack and stack[-1][1] >= indent:
                    stack.pop()

                if stack:
                    # This is a child of the current stack top
                    parent = stack[-1][0]
                    parent.children.append(new_obj)
                    new_obj.parent = parent
                else:
                    # Top-level object
                    self.objects.append(new_obj)

                # Add to type index
                if elem_type not in self.all_objects:
                    self.all_objects[elem_type] = []
                self.all_objects[elem_type].append(new_obj)

                # Push to stack
                stack.append((new_obj, indent))
                current_obj = new_obj

            # Check if this is a property assignment
            elif current_obj is not None:
                prop_match = re.match(r'^\s*(\w+)\s*=\s*(.+)$', line)
                if prop_match:
                    prop_name, prop_value = prop_match.groups()

                    # Parse value (remove quotes if present, try to convert numbers)
                    prop_value = prop_value.strip()
                    if prop_value.startswith('"') and prop_value.endswith('"'):
                        prop_value = prop_value[1:-1]
                    else:
                        # Try to convert to number
                        try:
                            if '.' in prop_value:
                                prop_value = float(prop_value)
                            else:
                                prop_value = int(prop_value)
                        except ValueError:
                            pass  # Keep as string

                    # Handle multiple values with same property name (e.g., MatRef)
                    if prop_name in current_obj.properties:
                        # Convert to list if not already
                        existing = current_obj.properties[prop_name]
                        if not isinstance(existing, list):
                            current_obj.properties[prop_name] = [existing]
                        current_obj.properties[prop_name].append(prop_value)
                    else:
                        current_obj.properties[prop_name] = prop_value

            i += 1

    def find_objects(self, obj_type: str) -> List[Dict[str, Any]]:
        """
        Find all objects of a given type.

        Args:
            obj_type: Element type to find (e.g., "ResZn", "ResExtWall")

        Returns:
            List of dictionaries in importer format (_type, _name, _properties, _children)
        """
        objects = self.all_objects.get(obj_type, [])
        return [obj.to_dict() for obj in objects]

    def get_all_types(self) -> List[str]:
        """Get list of all element types found in the file."""
        return list(self.all_objects.keys())

    def get_stats(self) -> Dict[str, int]:
        """Get count of each element type."""
        return {obj_type: len(objs) for obj_type, objs in self.all_objects.items()}


def parse_cibd25_text(file_path: str) -> CIBD25TextReader:
    """
    Parse a CIBD25 text file and return a reader object.

    Args:
        file_path: Path to CIBD25 file

    Returns:
        CIBD25TextReader with parsed data

    Example:
        >>> reader = parse_cibd25_text("model.cibd25")
        >>> zones = reader.find_objects("ResZn")
        >>> print(f"Found {len(zones)} zones")
    """
    reader = CIBD25TextReader()
    reader.parse_file(file_path)
    return reader
