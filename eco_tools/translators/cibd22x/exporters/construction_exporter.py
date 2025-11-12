"""
Construction Exporter - Construction Assembly Catalog Exporter
=============================================================

PURPOSE:
Serializes Construction objects from InternalRepresentation to CIBD22X XML format.

EXPORT STRATEGY:
1. Retrieve original XML tag from annotation ('xml_tag': construction type tag)
2. Convert SI units back to Imperial units (U-factor, R-value, dimensions)
3. Export material layer references (MatRef elements)
4. Restore format-specific properties from annotations

UNIT CONVERSIONS (SI → Imperial):
- U-factor: W/(m²·K) → Btu/(h·ft²·°F) (× 0.176110)
- R-value: m²·K/W → ft²·°F·h/Btu (× 5.678263)
- Framing depth/spacing: m → ft (÷ 0.3048)

ANNOTATION RESTORATION:
Constructions have extensive format-specific properties:
- CompatibleSurfType, ConsType, ExtRoughness
- Absorptance, Emittance properties
- Cavity/continuous insulation options
- Framing configuration (StudWidth, StudSpacing)

PATTERN: Simple Catalog Exporter with material layer references
"""

from typing import List
import xml.etree.ElementTree as ET
import logging

from eco_tools.core.internal_repr import Construction
from .base_exporter import BaseExporter

# Get module logger
logger = logging.getLogger('eco_tools.exporters')


class ConstructionExporter(BaseExporter):
    """Exporter for CIBD22X construction assembly elements"""

    def __init__(self):
        super().__init__()

    def export_constructions(self, parent: ET.Element, constructions: List[Construction]) -> None:
        """Export all constructions to CIBD22X XML."""
        if not constructions:
            logger.info("No constructions to export")
            return

        exported_count = 0
        for construction in constructions:
            if self._export_single_construction(parent, construction):
                exported_count += 1
            else:
                logger.warning(f"Failed to export construction '{construction.name}': missing required properties")

        logger.info(f"Exported {exported_count} constructions")

    def _export_single_construction(self, parent: ET.Element, construction: Construction) -> bool:
        """Export a single construction element."""
        if not construction.name:
            return False

        # Determine XML tag from annotation
        xml_tag = self.get_annotation(construction.annotation, 'xml_tag', 'ConsAsm')

        # Create construction element
        cons_elem = self.create_element(parent, xml_tag)

        # Add name (required)
        self.add_text_element(cons_elem, 'Name', construction.name)

        # Type is NOT used in CIBD22X construction assemblies (ResConsAssm, ConsAsm) - skip it

        # U-factor: W/(m²·K) → Btu/(h·ft²·°F)
        if construction.u_factor_SI is not None:
            u_factor_ip = self.si_to_ip_u_factor(construction.u_factor_SI)
            self.add_numeric_element(cons_elem, 'UFactor', u_factor_ip, precision=4)

        # R-value: m²·K/W → ft²·°F·h/Btu
        if construction.r_value_SI is not None:
            r_value_ip = self.si_to_ip_r_value(construction.r_value_SI)
            self.add_numeric_element(cons_elem, 'RValue', r_value_ip, precision=4)

        # Material layers (MatRef elements)
        if construction.material_layers:
            for mat_ref in construction.material_layers:
                self.add_text_element(cons_elem, 'MatRef', mat_ref)

        # Framing configuration (convert dimensions)
        if construction.framing_config:
            self.add_text_element(cons_elem, 'FrmCfg', construction.framing_config)

        if construction.framing_depth_m is not None:
            framing_depth_ft = self.si_to_ip_length(construction.framing_depth_m)
            self.add_numeric_element(cons_elem, 'FrmDpth', framing_depth_ft, precision=3)

        if construction.framing_spacing_m is not None:
            framing_spacing_ft = self.si_to_ip_length(construction.framing_spacing_m)
            self.add_numeric_element(cons_elem, 'FrmSpc', framing_spacing_ft, precision=3)

        # Restore format-specific properties from annotations
        if construction.annotation:
            annotation_props = [
                # CRITICAL: CanAssignTo specifies which surface types this construction can be assigned to
                'CanAssignTo',
                # Surface properties
                'CompatibleSurfType', 'ConsType', 'ExtRoughness',
                'ExtSolAbs', 'ExtThmAbs', 'ExtVisAbs',
                'IntSolAbs', 'IntThmAbs', 'IntVisAbs',
                # Insulation properties
                'CavityInsOpt', 'CavityInsDepth', 'CavityInsRVal',
                'ContInsOpt', 'ContInsDepth', 'ContInsRVal',
                # ResConsAssm layer properties
                'CavityLayer', 'FrameLayer', 'SheathInsulLayer', 'SheathInsulLayerRVal',
                'WallExtFinishLayer', 'InsideFinishLayer',
                # Mass/concrete properties
                'Type', 'MassLayer', 'MassThickness',
                # Additional features
                'RadiantBarrier',
                # Framing properties
                'StudWidth', 'StudSpacing', 'NumLayers'
            ]
            for prop in annotation_props:
                value = self.get_annotation(construction.annotation, prop)
                if value:
                    self.add_text_element(cons_elem, prop, value)

        return True
