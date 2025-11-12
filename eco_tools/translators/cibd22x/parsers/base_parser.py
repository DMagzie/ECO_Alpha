"""
Base Parser Class - Shared XML Parsing Utilities
================================================

PURPOSE:
All parser modules inherit from this class to access common functionality
for reading XML elements and converting data types safely.

DESIGN RATIONALE:
- Centralizes XML parsing logic to avoid code duplication across 22 parsers
- Provides safe type conversions that return None on failure (never crash)
- Matches the behavior of the original monolithic CIBD22XAdapter
- Enables consistent error handling across all parsers

CRITICAL NAMESPACE HANDLING:
CIBD22X uses XML namespaces (http://www.lmonte.com/CBECC22). This class provides
namespace-aware methods that work correctly regardless of namespace presence.

NEVER use elem.findall('.//TagName') - it fails with namespaces!
ALWAYS use root.iter() + _local_tag() pattern.

CRITICAL DESCENDANT vs DIRECT CHILD:
- get_property(): Searches ALL descendants (can grab child surface properties)
- _find_direct_child(): Searches ONLY immediate children (safe for zone properties)

Use _find_direct_child() for zone-level properties (FloorArea, Area) to avoid
grabbing values from child surfaces.

USAGE:
    class MyParser(BaseParser):
        def parse_elements(self, root):
            # Namespace-aware iteration
            for elem in root.iter():
                if self._local_tag(elem.tag) == 'ResZn':
                    # Get any descendant property
                    value = self.get_property(elem, 'PropertyName')

                    # Get DIRECT child only (critical for zone properties!)
                    floor_area = self._find_direct_child(elem, 'FloorArea')

                    number = self._to_float(value)

INHERITANCE HIERARCHY:
    BaseParser (this file)
      └─ MaterialParser
      └─ ZoneParser
      └─ HVACSystemParser
      └─ ... (19 more parsers)
"""

from typing import Optional, Any, List
import xml.etree.ElementTree as ET
import logging

# Get module logger
logger = logging.getLogger('eco_tools.parsers')


class BaseParser:
    """Base class for all parser modules with shared XML utilities"""

    def __init__(self):
        """Initialize the base parser"""
        pass

    def get_property(self, elem: ET.Element, tag: str) -> Optional[str]:
        """
        Get the text value of a child element.

        **WARNING**: Uses './/{tag}' to find ANY descendant (not just direct children).
        This can grab properties from child elements unintentionally!

        **EXAMPLE OF PROBLEM**:
        If parsing a ResZn (zone) that contains ResExtWall (walls):
        - Zone has no direct <FloorArea> child
        - First wall has <Area>243.748</Area>
        - get_property(zone_elem, 'Area') returns '243.748' (WRONG - wall area, not zone!)

        **SOLUTION**: For zone-level properties, use _find_direct_child() instead.

        This matches CIBD22XAdapter behavior and is namespace-aware.

        Args:
            elem: Parent XML element
            tag: Tag name of child element to find

        Returns:
            Text content of child element, or None if not found
        """
        if elem is None:
            return None

        # Search through all descendants, stripping namespaces
        for child in elem.iter():
            local_tag = self._local_tag(child.tag)
            if local_tag == tag and child.text:
                return child.text.strip()

        return None

    def get_child_text(self, elem: ET.Element, tag: str, default: str = None) -> Optional[str]:
        """
        Get the text value of a child element with optional default.

        Args:
            elem: Parent XML element
            tag: Tag name of child element to find
            default: Default value if not found

        Returns:
            Text content of child element, or default if not found
        """
        value = self.get_property(elem, tag)
        return value if value is not None else default

    def find_child(self, elem: ET.Element, tag: str) -> Optional[ET.Element]:
        """
        Find first descendant element with given tag (namespace-aware).

        Args:
            elem: Parent XML element
            tag: Tag name to find

        Returns:
            First matching element, or None if not found
        """
        if elem is None:
            return None

        for child in elem.iter():
            if self._local_tag(child.tag) == tag:
                return child
        return None

    def find_children(self, elem: ET.Element, tag: str) -> List[ET.Element]:
        """
        Find all descendant elements with given tag (namespace-aware).

        Args:
            elem: Parent XML element
            tag: Tag name to find

        Returns:
            List of matching elements (empty if none found)
        """
        if elem is None:
            return []

        return [child for child in elem.iter() if self._local_tag(child.tag) == tag]

    def _to_float(self, value: Any, context: str = '') -> Optional[float]:
        """
        Convert value to float, returning None on failure.

        Args:
            value: Value to convert (string, number, or None)
            context: Optional context for logging (e.g., property name)

        Returns:
            Float value or None if conversion fails
        """
        if value is None:
            return None
        if isinstance(value, (int, float)):
            return float(value)
        if isinstance(value, str):
            try:
                return float(value)
            except ValueError:
                logger.debug(f"Failed to convert '{value}' to float{f' ({context})' if context else ''}")
                return None
        logger.debug(f"Cannot convert type {type(value).__name__} to float{f' ({context})' if context else ''}")
        return None

    def _to_int(self, value: Any, context: str = '') -> Optional[int]:
        """
        Convert value to integer, returning None on failure.

        Args:
            value: Value to convert (string, number, or None)
            context: Optional context for logging (e.g., property name)

        Returns:
            Integer value or None if conversion fails
        """
        if value is None:
            return None
        if isinstance(value, int):
            return value
        if isinstance(value, (str, float)):
            try:
                return int(float(value))
            except ValueError:
                logger.debug(f"Failed to convert '{value}' to int{f' ({context})' if context else ''}")
                return None
        logger.debug(f"Cannot convert type {type(value).__name__} to int{f' ({context})' if context else ''}")
        return None

    def _to_bool(self, value: Any, context: str = '') -> Optional[bool]:
        """
        Convert value to boolean.

        Handles common CBECC boolean representations:
        - "1", "true", "True", "yes" → True
        - "0", "false", "False", "no" → False

        Args:
            value: Value to convert
            context: Optional context for logging (e.g., property name)

        Returns:
            Boolean value or None if conversion fails
        """
        if value is None:
            return None
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            value_lower = value.lower().strip()
            if value_lower in ('1', 'true', 'yes'):
                return True
            elif value_lower in ('0', 'false', 'no'):
                return False
            logger.debug(f"Cannot convert '{value}' to bool{f' ({context})' if context else ''}")
            return None
        if isinstance(value, (int, float)):
            return bool(value)
        logger.debug(f"Cannot convert type {type(value).__name__} to bool{f' ({context})' if context else ''}")
        return None

    def get_attrib(self, elem: ET.Element, name: str) -> Optional[str]:
        """
        Get an XML attribute value.

        Args:
            elem: XML element
            name: Attribute name

        Returns:
            Attribute value or None if not found
        """
        if elem is None:
            return None
        return elem.get(name)

    def find_all(self, elem: ET.Element, tag: str) -> list:
        """
        Find all child elements with given tag.

        Args:
            elem: Parent XML element
            tag: Tag name to search for

        Returns:
            List of matching elements (empty list if none found)
        """
        if elem is None:
            return []
        return elem.findall(tag)

    def get_text(self, elem: ET.Element) -> Optional[str]:
        """
        Get the text content of an element.

        Args:
            elem: XML element

        Returns:
            Text content or None if element is None or has no text
        """
        if elem is None:
            return None
        if elem.text:
            return elem.text.strip()
        return None

    def _get_element_context(self, elem: ET.Element) -> str:
        """
        Get logging context for an element (tag + line number if available).

        Args:
            elem: XML element

        Returns:
            String describing element location (e.g., "ResZn at line 142")
        """
        if elem is None:
            return "unknown element"

        tag = self._local_tag(elem.tag) if hasattr(self, '_local_tag') else elem.tag

        # Try to get line number (not all XML parsers provide this)
        line_num = getattr(elem, 'sourceline', None)
        if line_num:
            return f"{tag} at line {line_num}"
        return f"{tag}"

    def _local_tag(self, tag: str) -> str:
        """
        Extract local tag name, stripping namespace if present.

        Args:
            tag: Full tag name (may include namespace)

        Returns:
            Local tag name without namespace
        """
        # Handle {namespace}tag format
        if '}' in tag:
            return tag.split('}')[1]
        return tag

    def _calculate_area_from_polylp(self, element: ET.Element) -> Optional[float]:
        """
        Calculate area from PolyLp (polygon loop) using Shoelace formula.

        This is used by zones, surfaces, and openings that specify geometry
        via CartesianPt coordinates instead of explicit area values.

        Args:
            element: XML element that may contain a PolyLp child

        Returns:
            Area in ft² (CBECC units) or None if no PolyLp found
        """
        polylp = self.find_child(element, 'PolyLp')
        if polylp is None:
            return None

        # Extract coordinates from CartesianPt elements
        # In CBECC, each CartesianPt has 3 <Coord> siblings (X, Y, Z)
        points = []
        for pt in self.find_children(polylp, 'CartesianPt'):
            coords = self.find_children(pt, 'Coord')
            if len(coords) >= 2:
                x = self._to_float(coords[0].text)
                y = self._to_float(coords[1].text)
                if x is not None and y is not None:
                    points.append((x, y))

        if len(points) < 3:
            return None

        # Shoelace formula for polygon area
        area = 0.0
        n = len(points)
        for i in range(n):
            j = (i + 1) % n
            area += points[i][0] * points[j][1]
            area -= points[j][0] * points[i][1]

        return abs(area) / 2.0
