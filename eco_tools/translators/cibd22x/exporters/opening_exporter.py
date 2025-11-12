"""
Opening Exporter - Hierarchical Exporter (Bottom of Spatial Hierarchy)
======================================================================

PURPOSE:
Serializes Opening objects (windows, doors, skylights) to CIBD22X XML format.
Openings are the BOTTOM of spatial hierarchy: ZoneGroups → Zones → Surfaces → Openings.

EXPORT STRATEGY:
1. Determine XML tag from opening type (window → Win, door → Dr, skylight → Skylt)
2. Or retrieve from annotation if available
3. Convert SI units back to Imperial (area, height, width)
4. Export fenestration properties (U-factor, SHGC, VT)
5. Export window type reference

HIERARCHICAL EXPORT:
Openings are exported as CHILDREN of surface elements, not as top-level elements.
The parent SurfaceExporter calls this exporter to add openings within each surface.

UNIT CONVERSIONS (SI → Imperial):
- Area: m² → ft² (÷ 0.092903)
- Height/Width: m → ft (÷ 0.3048)

ANNOTATION RESTORATION:
- 'xml_tag': Original tag (ResWin, Win, Dr, Skylt, etc.)
- Original IP values for exact round-trip

PATTERN: Hierarchical Exporter - Called by parent (SurfaceExporter)
"""

from typing import List, Optional
import xml.etree.ElementTree as ET
import logging

from eco_tools.core.internal_repr import Opening
from .base_exporter import BaseExporter
from .format_utils import Format, get_name_tag, get_window_type_ref_tag

# Get module logger
logger = logging.getLogger('eco_tools.exporters')


class OpeningExporter(BaseExporter):
    """Exporter for CIBD22X opening elements (windows, doors, skylights)"""

    def __init__(self):
        super().__init__()

    def export_opening(
        self,
        parent: ET.Element,
        opening: Opening,
        format_type: Format = Format.CIBD22
    ) -> Optional[ET.Element]:
        """
        Export a single opening as a child of a surface element.

        Args:
            parent: Parent surface XML element
            opening: Opening object to export
            format_type: Format to use (CIBD22 or CIBD22X)

        Returns:
            Created opening XML element or None if export failed
        """
        if not hasattr(opening, 'name') or not opening.name:
            # Generate name from ID if not present
            name = opening.id if hasattr(opening, 'id') else "Opening"
        else:
            name = opening.name

        # Determine XML tag
        xml_tag = self.get_annotation(opening.annotation, 'xml_tag')
        if not xml_tag:
            # Infer from opening type
            xml_tag = self._determine_tag_from_type(opening.type)

        # Create opening element
        open_elem = self.create_element(parent, xml_tag)

        # Add name - use format-aware name tag
        name_tag = get_name_tag(format_type)
        self.add_text_element(open_elem, name_tag, name)

        # Area: m² → ft²
        if opening.area_m2 is not None:
            area_ft2 = self.si_to_ip_area(opening.area_m2)
            self.add_numeric_element(open_elem, 'Area', area_ft2, precision=2)

        # Height: m → ft
        if opening.height_m is not None:
            height_ft = self.si_to_ip_length(opening.height_m)
            self.add_numeric_element(open_elem, 'Height', height_ft, precision=2)

        # Width: m → ft
        if opening.width_m is not None:
            width_ft = self.si_to_ip_length(opening.width_m)
            self.add_numeric_element(open_elem, 'Width', width_ft, precision=2)

        # Window type reference (for catalog-based windows) - use format-aware tag
        window_type_tag = get_window_type_ref_tag(format_type)
        if opening.window_type_ref:
            self.add_text_element(open_elem, window_type_tag, opening.window_type_ref)

        # Fenestration construction reference - use format-aware tag
        if opening.fenestration_cons_ref:
            self.add_text_element(open_elem, window_type_tag, opening.fenestration_cons_ref)

        # U-factor (if specified inline, not from catalog)
        if opening.u_factor_SI is not None:
            u_factor_ip = self.si_to_ip_u_factor(opening.u_factor_SI)
            self.add_numeric_element(open_elem, 'UFactor', u_factor_ip, precision=3)

        # SHGC (dimensionless)
        if opening.shgc is not None:
            self.add_numeric_element(open_elem, 'SHGC', opening.shgc, precision=3)

        # VT (dimensionless)
        if opening.vt is not None:
            self.add_numeric_element(open_elem, 'VT', opening.vt, precision=3)

        return open_elem

    def _determine_tag_from_type(self, opening_type: str) -> str:
        """
        Determine XML tag from opening type.

        Args:
            opening_type: Opening type ('window', 'door', 'skylight')

        Returns:
            XML tag name
        """
        if opening_type == 'door':
            return 'Dr'
        elif opening_type == 'skylight':
            return 'Skylt'
        else:
            return 'Win'  # Default to window
