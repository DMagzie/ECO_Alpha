"""
Material Exporter - Construction Material Catalog Exporter
==========================================================

PURPOSE:
Serializes Material objects from InternalRepresentation to CIBD22X XML format.

EXPORT STRATEGY:
1. Retrieve original XML tag from annotation ('xml_tag': 'Mat' or 'ResMat')
2. Convert SI units back to Imperial units (m → in, m²·K/W → ft²·°F·h/Btu)
3. Restore format-specific properties from annotations
4. Create XML elements with proper structure

UNIT CONVERSIONS (SI → Imperial):
- Thickness: meters → inches (÷ 0.0254)
- R-value: m²·K/W → ft²·°F·h/Btu (× 5.678263)
- Density: kg/m³ → lb/ft³ (÷ 16.0185)
- Specific Heat: J/(kg·K) → Btu/(lb·°F) (÷ 4186.8)

ANNOTATION RESTORATION:
Materials have format-specific properties stored in annotations:
- Conductivity (alternative to R-value)
- Absorptance, Emittance, Roughness (surface properties)
- CodeCat, CodeItem (Title 24 compliance)
- FrmAsm, FrmCfg, FrmDpth, FrmSpc (framing properties)
- CavityInsOpt (insulation options)

PATTERN: Simple Catalog Exporter - mirrors MaterialParser logic
"""

from typing import List, Optional
import xml.etree.ElementTree as ET
import logging

from eco_tools.core.internal_repr import Material
from .base_exporter import BaseExporter

# Get module logger
logger = logging.getLogger('eco_tools.exporters')


class MaterialExporter(BaseExporter):
    """Exporter for CIBD22X construction material elements"""

    def __init__(self):
        """Initialize the material exporter"""
        super().__init__()

    def export_materials(self, parent: ET.Element, materials: List[Material]) -> None:
        """
        Export all materials to CIBD22X XML.

        Creates catalog-level material elements (<Mat> or <ResMat>) with
        proper unit conversions and annotation restoration.

        Args:
            parent: Parent XML element (typically <Building>)
            materials: List of Material objects to export
        """
        if not materials:
            logger.info("No materials to export")
            return

        exported_count = 0

        for material in materials:
            if self._export_single_material(parent, material):
                exported_count += 1
            else:
                logger.warning(f"Failed to export material '{material.name}': missing required properties")

        logger.info(f"Exported {exported_count} materials")

    def _export_single_material(self, parent: ET.Element, material: Material) -> bool:
        """
        Export a single material element.

        Args:
            parent: Parent XML element
            material: Material object to export

        Returns:
            True if export succeeded, False if critical properties missing
        """
        # Validate required properties
        if not material.name:
            return False

        # Determine XML tag from annotation (Mat vs ResMat)
        xml_tag = self.get_annotation(material.annotation, 'xml_tag', 'Mat')

        # Create material element
        mat_elem = self.create_element(parent, xml_tag)

        # Add name (required) - CIBD22X files use CIBD22 format property names
        self.add_text_element(mat_elem, 'Name', material.name)

        # MatType is NOT used in CIBD22X files - skip it

        # ================================================================
        # THERMAL PROPERTIES (with unit conversion)
        # ================================================================

        # Thickness: m → inches
        if material.thickness_m is not None:
            thickness_in = self.si_to_ip_thickness(material.thickness_m)
            self.add_numeric_element(mat_elem, 'Thickness', thickness_in, precision=4)

        # R-value: m²·K/W → ft²·°F·h/Btu
        if material.r_value_SI is not None:
            r_value_ip = self.si_to_ip_r_value(material.r_value_SI)
            self.add_numeric_element(mat_elem, 'RValue', r_value_ip, precision=4)

        # Density: kg/m³ → lb/ft³
        if material.density_kg_m3 is not None:
            density_ip = self.si_to_ip_density(material.density_kg_m3)
            self.add_numeric_element(mat_elem, 'Density', density_ip, precision=4)

        # Specific Heat: J/(kg·K) → Btu/(lb·°F)
        if material.specific_heat is not None:
            spec_heat_ip = self.si_to_ip_specific_heat(material.specific_heat)
            self.add_numeric_element(mat_elem, 'SpecHeat', spec_heat_ip, precision=4)

        # ================================================================
        # ANNOTATION RESTORATION (format-specific properties)
        # ================================================================

        if material.annotation:
            # Conductivity (alternative to R-value)
            conductivity = self.get_annotation(material.annotation, 'Conductivity')
            if conductivity:
                self.add_text_element(mat_elem, 'Conductivity', conductivity)

            # Surface radiative properties
            for prop in ['Absorptance', 'Emittance', 'Roughness']:
                value = self.get_annotation(material.annotation, prop)
                if value:
                    self.add_text_element(mat_elem, prop, value)

            # Title 24 code compliance
            for prop in ['CodeCat', 'CodeItem']:
                value = self.get_annotation(material.annotation, prop)
                if value:
                    self.add_text_element(mat_elem, prop, value)

            # Framing assembly properties
            for prop in ['FrmAsm', 'FrmCfg', 'FrmDpth', 'FrmSpc']:
                value = self.get_annotation(material.annotation, prop)
                if value:
                    self.add_text_element(mat_elem, prop, value)

            # Insulation options
            cavity_ins_opt = self.get_annotation(material.annotation, 'CavityInsOpt')
            if cavity_ins_opt:
                self.add_text_element(mat_elem, 'CavityInsOpt', cavity_ins_opt)

        return True
