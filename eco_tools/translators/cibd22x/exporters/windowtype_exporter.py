"""
WindowType Exporter - Fenestration Catalog Exporter
==================================================

PURPOSE:
Serializes WindowType objects from InternalRepresentation to CIBD22X XML format.

EXPORT STRATEGY:
1. Retrieve original XML tag from annotation (ResWinType, ComWinType, etc.)
2. Convert SI units back to Imperial units (U-factor, area)
3. Export fenestration properties (SHGC, VT, frame properties)
4. Restore format-specific properties from annotations

UNIT CONVERSIONS (SI → Imperial):
- U-factor: W/(m²·K) → Btu/(h·ft²·°F) (× 0.176110)
- Area: m² → ft² (÷ 0.092903)

ANNOTATION RESTORATION:
WindowTypes have extensive fenestration properties:
- Frame type, frame material, glazing type
- Daylighting properties
- NFRC ratings, CEC ratings
- Glass layers, gas fill type

PATTERN: Simple Catalog Exporter with fenestration-specific properties
"""

from typing import List
import xml.etree.ElementTree as ET
import logging

from eco_tools.core.internal_repr import WindowType
from .base_exporter import BaseExporter

# Get module logger
logger = logging.getLogger('eco_tools.exporters')


class WindowTypeExporter(BaseExporter):
    """Exporter for CIBD22X window type elements"""

    def __init__(self):
        super().__init__()

    def export_window_types(self, parent: ET.Element, window_types: List[WindowType]) -> None:
        """Export all window types to CIBD22X XML."""
        if not window_types:
            logger.info("No window types to export")
            return

        exported_count = 0
        for window_type in window_types:
            if self._export_single_window_type(parent, window_type):
                exported_count += 1
            else:
                logger.warning(f"Failed to export window type '{window_type.name}': missing required properties")

        logger.info(f"Exported {exported_count} window types")

    def _export_single_window_type(self, parent: ET.Element, window_type: WindowType) -> bool:
        """Export a single window type element."""
        if not window_type.name:
            return False

        # Determine XML tag from annotation
        xml_tag = self.get_annotation(window_type.annotation, 'xml_tag', 'ResWinType')

        # Create window type element
        wt_elem = self.create_element(parent, xml_tag)

        # Add name (required)
        self.add_text_element(wt_elem, 'Name', window_type.name)

        # Fenestration type - ONLY valid for WinType, NOT ResWinType
        if window_type.fenestration_type and xml_tag != 'ResWinType':
            self.add_text_element(wt_elem, 'FenType', window_type.fenestration_type)

        # U-factor: W/(m²·K) → Btu/(h·ft²·°F)
        if window_type.u_factor_SI is not None:
            u_factor_ip = self.si_to_ip_u_factor(window_type.u_factor_SI)
            self.add_numeric_element(wt_elem, 'UFactor', u_factor_ip, precision=4)

        # SHGC (dimensionless, 0-1)
        if window_type.shgc is not None:
            self.add_numeric_element(wt_elem, 'SHGC', window_type.shgc, precision=3)

        # VT (dimensionless, 0-1)
        if window_type.vt is not None:
            self.add_numeric_element(wt_elem, 'VT', window_type.vt, precision=3)

        # Area: m² → ft² (if specified in catalog for "Overall Window Area" spec method)
        if window_type.area_m2 is not None:
            area_ft2 = self.si_to_ip_area(window_type.area_m2)
            self.add_numeric_element(wt_elem, 'Area', area_ft2, precision=2)

        # Frame properties
        if window_type.frame_type:
            self.add_text_element(wt_elem, 'FrmType', window_type.frame_type)

        # Glazing properties
        if window_type.glazing_type:
            self.add_text_element(wt_elem, 'GlzType', window_type.glazing_type)

        # Restore format-specific properties from annotations
        if window_type.annotation:
            annotation_props = [
                'SpecMethod', 'NFRCUfactor', 'NFRCCertified',
                'FrmMat', 'NFRCRating', 'CECRating', 'GlzLayers', 'GasFill',
                'CoatingLoc', 'CoatingType', 'EdgeSeal',
                'DaylightGlzArea', 'VenBlindLoc', 'VenBlindSlatAng',
                'OpType', 'Operator', 'Operability'
            ]
            for prop in annotation_props:
                value = self.get_annotation(window_type.annotation, prop)
                if value:
                    self.add_text_element(wt_elem, prop, value)

        return True
