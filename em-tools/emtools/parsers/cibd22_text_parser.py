# FILE: em-tools/emtools/parsers/cibd22_text_parser.py
# ============================================================================
"""
CIBD22 Text Format Parser

Parses CIBD22's proprietary text-based format with indentation:
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

from __future__ import annotations
from typing import Dict, Any, List, Optional, Union
import re


class CIBD22TextParser:
    """Parser for CIBD22 text-based format."""
    
    def __init__(self):
        self.objects: List[Dict[str, Any]] = []
        self.current_stack: List[Dict[str, Any]] = []
        
    def parse(self, text: str) -> List[Dict[str, Any]]:
        """
        Parse CIBD22 text format into structured objects.
        
        Args:
            text: Raw CIBD22 file content
            
        Returns:
            List of parsed objects with hierarchy preserved
        """
        self.objects = []
        self.current_stack = []
        
        lines = text.split('\n')
        
        for line_num, line in enumerate(lines, 1):
            # Skip empty lines
            if not line.strip():
                continue
                
            # Calculate indentation level
            indent = len(line) - len(line.lstrip())
            
            # Check for object terminator
            if line.strip() == "..":
                if self.current_stack:
                    completed = self.current_stack.pop()
                    if not self.current_stack:
                        self.objects.append(completed)
                continue
            
            # Parse object definition: ObjectType "name"
            obj_match = re.match(r'^(\s*)([A-Z][a-zA-Z0-9]+)\s+"([^"]+)"', line)
            if obj_match:
                obj_type = obj_match.group(2)
                obj_name = obj_match.group(3)
                
                new_obj = {
                    "_type": obj_type,
                    "_name": obj_name,
                    "_children": [],
                    "_properties": {},
                    "_line": line_num
                }
                
                # Add to parent or root
                if self.current_stack:
                    self.current_stack[-1]["_children"].append(new_obj)
                
                self.current_stack.append(new_obj)
                continue
            
            # Parse property: key = value or key[index] = value
            prop_match = re.match(r'^(\s*)([A-Za-z][A-Za-z0-9_]*)\s*(?:\[(\d+)\])?\s*=\s*(.+)', line)
            if prop_match:
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
                
                if self.current_stack:
                    if index:
                        # Array property
                        if key not in self.current_stack[-1]["_properties"]:
                            self.current_stack[-1]["_properties"][key] = {}
                        self.current_stack[-1]["_properties"][key][int(index)] = value
                    else:
                        # Regular property
                        self.current_stack[-1]["_properties"][key] = value
        
        # Handle any unclosed objects
        while self.current_stack:
            completed = self.current_stack.pop()
            if not self.current_stack:
                self.objects.append(completed)
        
        return self.objects
    
    def find_objects(self, objects: Optional[List[Dict[str, Any]]] = None, 
                     obj_type: Optional[str] = None, 
                     name: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Find objects by type and/or name.
        
        Args:
            objects: List to search (defaults to parsed objects)
            obj_type: Object type to match (e.g., "ResZn")
            name: Object name to match
            
        Returns:
            List of matching objects
        """
        if objects is None:
            objects = self.objects
        
        results = []
        
        for obj in objects:
            # Check type match
            if obj_type and obj.get("_type") != obj_type:
                # Check children
                results.extend(self.find_objects(obj.get("_children", []), obj_type, name))
                continue
            
            # Check name match
            if name and obj.get("_name") != name:
                # Check children
                results.extend(self.find_objects(obj.get("_children", []), obj_type, name))
                continue
            
            # Match found
            if obj_type or name:
                results.append(obj)
            
            # Also search children
            results.extend(self.find_objects(obj.get("_children", []), obj_type, name))
        
        return results
    
    def get_property(self, obj: Dict[str, Any], key: str, default: Any = None) -> Any:
        """Get property value from object."""
        return obj.get("_properties", {}).get(key, default)
    
    def get_array_property(self, obj: Dict[str, Any], key: str) -> List[Any]:
        """Get array property as ordered list."""
        prop = obj.get("_properties", {}).get(key)
        if isinstance(prop, dict):
            # Convert indexed dict to list
            max_index = max(prop.keys()) if prop else 0
            result = []
            for i in range(1, max_index + 1):
                result.append(prop.get(i))
            return result
        return []


def parse_cibd22_file(file_path: str) -> CIBD22TextParser:
    """
    Parse CIBD22 file and return parser with loaded objects.
    
    Args:
        file_path: Path to CIBD22 file
        
    Returns:
        CIBD22TextParser instance with parsed objects
        
    Example:
        >>> parser = parse_cibd22_file("model.cibd22")
        >>> zones = parser.find_objects(obj_type="ResZn")
    """
    # Try multiple encodings (CIBD22 files often use Windows-1252)
    encodings = ['utf-8', 'windows-1252', 'latin-1', 'cp1252']
    content = None
    
    for encoding in encodings:
        try:
            with open(file_path, 'r', encoding=encoding) as f:
                content = f.read()
            break
        except (UnicodeDecodeError, LookupError):
            continue
    
    if content is None:
        # Fallback: read as binary and decode with error handling
        with open(file_path, 'rb') as f:
            content = f.read().decode('utf-8', errors='replace')
    
    parser = CIBD22TextParser()
    parser.parse(content)
    return parser
