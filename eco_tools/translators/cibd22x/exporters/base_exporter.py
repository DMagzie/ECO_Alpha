"""
Base Exporter Class - Shared XML Export Utilities
==================================================

PURPOSE:
All exporter modules inherit from this class to access common functionality
for writing XML elements and converting data types safely.

DESIGN RATIONALE:
- Centralizes XML creation logic to avoid code duplication across exporters
- Provides safe unit conversions (SI → Imperial)
- Matches the behavior of the original monolithic CIBD22XAdapter
- Enables consistent element creation across all exporters

USAGE:
    class MyExporter(BaseExporter):
        def export_elements(self, parent, elements):
            for elem in elements:
                xml_elem = self.create_element(parent, 'ElementTag', elem.id)
                self.add_text_element(xml_elem, 'Name', elem.name)
                self.add_numeric_element(xml_elem, 'Value', elem.value)

KEY RESPONSIBILITIES:
1. Create XML elements with proper attributes
2. Add child text elements
3. Convert SI units back to Imperial units
4. Read annotations for format-specific restoration
5. Safe numeric to string conversions
"""

from typing import Optional, Any, Dict
import xml.etree.ElementTree as ET
import logging

# Get module logger
logger = logging.getLogger('eco_tools.exporters')


class BaseExporter:
    """Base class for all exporter modules with shared XML utilities"""

    def __init__(self):
        """Initialize the base exporter"""
        pass

    def create_element(
        self,
        parent: ET.Element,
        tag: str,
        element_id: Optional[str] = None,
        **attribs
    ) -> ET.Element:
        """
        Create an XML element with optional attributes.

        Args:
            parent: Parent XML element
            tag: Tag name for new element
            element_id: Optional id attribute
            **attribs: Additional attributes to set

        Returns:
            Created XML element
        """
        if element_id:
            attribs['id'] = element_id

        return ET.SubElement(parent, tag, **attribs)

    def add_text_element(
        self,
        parent: ET.Element,
        tag: str,
        text: Optional[str],
        skip_if_none: bool = True
    ) -> Optional[ET.Element]:
        """
        Add a text child element to parent.

        Args:
            parent: Parent XML element
            tag: Tag name for child element
            text: Text content
            skip_if_none: If True, don't create element when text is None

        Returns:
            Created element or None if skipped
        """
        if text is None and skip_if_none:
            return None

        elem = ET.SubElement(parent, tag)
        elem.text = str(text) if text is not None else ''
        return elem

    def add_numeric_element(
        self,
        parent: ET.Element,
        tag: str,
        value: Optional[float],
        precision: int = 6,
        skip_if_none: bool = True
    ) -> Optional[ET.Element]:
        """
        Add a numeric child element to parent with controlled precision.

        Args:
            parent: Parent XML element
            tag: Tag name for child element
            value: Numeric value
            precision: Number of decimal places
            skip_if_none: If True, don't create element when value is None

        Returns:
            Created element or None if skipped
        """
        if value is None and skip_if_none:
            return None

        elem = ET.SubElement(parent, tag)
        if value is not None:
            # Format with precision, stripping unnecessary trailing zeros
            elem.text = f"{value:.{precision}f}".rstrip('0').rstrip('.')
        return elem

    def get_annotation(
        self,
        annotation: Optional[Dict[str, Any]],
        key: str,
        default: Any = None
    ) -> Any:
        """
        Safely get annotation value.

        Args:
            annotation: Annotation dictionary
            key: Key to retrieve
            default: Default value if key not found

        Returns:
            Annotation value or default
        """
        if annotation is None:
            return default
        return annotation.get(key, default)

    # ===================================================================
    # UNIT CONVERSION METHODS (SI → Imperial)
    # ===================================================================
    # These reverse the parser conversions to restore original CBECC units

    def si_to_ip_area(self, area_m2: Optional[float]) -> Optional[float]:
        """Convert area from m² to ft² (÷ 0.092903)"""
        return (area_m2 / 0.092903) if area_m2 is not None else None

    def si_to_ip_volume(self, volume_m3: Optional[float]) -> Optional[float]:
        """Convert volume from m³ to ft³ (× 35.3147)"""
        return (volume_m3 * 35.3147) if volume_m3 is not None else None

    def si_to_ip_length(self, length_m: Optional[float]) -> Optional[float]:
        """Convert length from m to ft (÷ 0.3048)"""
        return (length_m / 0.3048) if length_m is not None else None

    def si_to_ip_r_value(self, r_value_si: Optional[float]) -> Optional[float]:
        """Convert R-value from m²·K/W to ft²·°F·h/Btu (× 5.678263)"""
        return (r_value_si * 5.678263) if r_value_si is not None else None

    def si_to_ip_u_factor(self, u_factor_si: Optional[float]) -> Optional[float]:
        """Convert U-factor from W/(m²·K) to Btu/(h·ft²·°F) (× 0.176110)"""
        return (u_factor_si * 0.176110) if u_factor_si is not None else None

    def si_to_ip_thickness(self, thickness_m: Optional[float]) -> Optional[float]:
        """Convert thickness from m to inches (÷ 0.0254)"""
        return (thickness_m / 0.0254) if thickness_m is not None else None

    def si_to_ip_density(self, density_kg_m3: Optional[float]) -> Optional[float]:
        """Convert density from kg/m³ to lb/ft³ (÷ 16.0185)"""
        return (density_kg_m3 / 16.0185) if density_kg_m3 is not None else None

    def si_to_ip_specific_heat(self, specific_heat_si: Optional[float]) -> Optional[float]:
        """Convert specific heat from J/(kg·K) to Btu/(lb·°F) (÷ 4186.8)"""
        return (specific_heat_si / 4186.8) if specific_heat_si is not None else None
