"""
Material Parser - Construction Material Catalog Parser
======================================================

PURPOSE:
Extracts building material specifications from CIBD22X XML catalogs and converts
them to the universal InternalRepresentation format.

MATERIAL TYPES IN CBECC:
CBECC uses two catalog types for different building code contexts:
1. <ResMat> - Residential materials (Title 24 Residential)
2. <Mat>    - Commercial materials (Title 24 Nonresidential)

Both types are parsed identically - the distinction is preserved in annotations
for round-trip fidelity.

KEY RESPONSIBILITIES:
1. Parse material catalogs from XML (not construction references!)
2. Convert Imperial (IP) units to SI units for internal representation
3. Extract thermal properties (R-value, conductivity, density, specific heat)
4. Extract surface properties (absorptance, emittance, roughness)
5. Preserve format-specific properties in annotations for round-trip export

UNIT CONVERSIONS:
CBECC uses Imperial units, InternalRepresentation uses SI units:
- Thickness: inches → meters (× 0.0254)
- R-value: ft²·°F·h/Btu → m²·K/W (× 0.1761)
- Density: lb/ft³ → kg/m³ (× 16.0185)
- Specific Heat: Btu/(lb·°F) → J/(kg·K) (× 4186.8)

CATALOG vs REFERENCE:
IMPORTANT: This parser extracts catalog DEFINITIONS (<Mat>, <ResMat>).
It does NOT parse <MatRef> elements, which are references used inside
construction assemblies. Those are handled by ConstructionParser.

DESIGN PATTERN:
This is a "Simple Catalog Parser" - no dependencies on other parsers,
no hierarchical relationships, pure data extraction with unit conversion.
"""

from typing import List, Optional, Dict, Any
import xml.etree.ElementTree as ET
import logging

from eco_tools.core.internal_repr import Material
from eco_tools.core.id_registry import IDRegistry
from .base_parser import BaseParser

# Get module logger
logger = logging.getLogger('eco_tools.parsers')


class MaterialParser(BaseParser):
    """Parser for CIBD22X construction material elements"""

    # CIBD22X material catalog tags
    # NOTE: These are catalog-level elements (direct children of root or nested in libraries),
    # NOT MatRef references inside construction elements
    MATERIAL_CATALOG_TAGS = [
        'ResMat',  # Residential materials
        'Mat'      # Commercial materials
    ]

    def __init__(self, id_registry: IDRegistry):
        """
        Initialize the material parser.

        Args:
            id_registry: ID registry for generating unique material IDs
        """
        super().__init__()
        self.id_registry = id_registry

    def parse_materials(self, root: ET.Element) -> List[Material]:
        """
        Parse all construction materials from CIBD22X catalog.

        IMPORTANT: Only parses catalog-level elements (direct children of root or in libraries),
        NOT MatRef references inside construction elements.

        Args:
            root: Root XML element

        Returns:
            List of Material objects
        """
        materials = []

        for tag in self.MATERIAL_CATALOG_TAGS:
            # Search at root level and descendants (catalogs may be nested in libraries)
            # Use namespace-aware iteration
            for mat_elem in root.iter():
                if self._local_tag(mat_elem.tag) == tag:
                    material = self._parse_single_material(mat_elem, tag, len(materials))
                    if material:
                        materials.append(material)
                    else:
                        # Material parsing failed - likely missing required properties
                        name = self._get_name(mat_elem) or "unnamed"
                        logger.warning(f"Failed to parse {tag} material '{name}'")

        logger.info(f"Parsed {len(materials)} materials")
        return materials

    def _parse_single_material(
        self,
        mat_elem: ET.Element,
        tag: str,
        index: int
    ) -> Optional[Material]:
        """
        Parse a single material element and convert to internal representation.

        PARSING STRATEGY:
        1. Extract name (CBECC stores in <n> or id attribute)
        2. Generate globally unique ID via IDRegistry
        3. Extract material type (insulation, concrete, etc.)
        4. Parse thermal properties WITH unit conversion (IP → SI)
        5. Build annotation dict for round-trip fidelity
        6. Create Material object

        Args:
            mat_elem: Material XML element (<Mat> or <ResMat>)
            tag: Element tag name (for annotation preservation)
            index: Current material count (unused, for future default naming)

        Returns:
            Material object with SI units, or None if parsing fails
        """
        # ================================================================
        # STEP 1: Extract Name
        # ================================================================
        # CBECC name location varies: <n>, <Name>, or id attribute
        # Fall back to generic "Material" if none found (rare but possible)
        name = self._get_name(mat_elem)
        if not name:
            name = "Material"

        # ================================================================
        # STEP 2: Generate Unique ID
        # ================================================================
        # IDRegistry ensures globally unique IDs across all element types
        # Pattern: MAT_{name}_{counter}
        mat_id = self.id_registry.generate_id('MAT', name, '', 'CIBD22X')

        # ================================================================
        # STEP 3: Extract Material Type
        # ================================================================
        # Material type classifies thermal behavior: insulation, mass, air gap, etc.
        # CBECC uses 'MatType' or 'Type' - try both
        mat_type = self.get_property(mat_elem, 'MatType')
        if not mat_type:
            mat_type = self.get_property(mat_elem, 'Type')
        if not mat_type:
            mat_type = 'Unknown'  # Fallback for rare cases

        # ================================================================
        # STEP 4: Parse Thermal Properties (WITH UNIT CONVERSION)
        # ================================================================
        # CRITICAL: All unit conversions happen here during import.
        # Exporter will reverse these conversions (SI → IP) during export.

        # THICKNESS: inches → meters
        # Conversion: 1 inch = 0.0254 meters
        # Example: 4" of insulation = 4 × 0.0254 = 0.1016 m
        thickness_in = self._to_float(self.get_property(mat_elem, 'Thickness'))
        thickness_m = (thickness_in * 0.0254) if thickness_in else None

        # R-VALUE: ft²·°F·h/Btu → m²·K/W
        # Conversion factor: 0.1761
        # Example: R-13 insulation (IP) = 13 × 0.1761 = 2.29 m²·K/W (SI)
        # Try 'RValue' first, then 'R' (CBECC uses both)
        r_value_ip = self._to_float(self.get_property(mat_elem, 'RValue'))
        if not r_value_ip:
            r_value_ip = self._to_float(self.get_property(mat_elem, 'R'))
        r_value_SI = (r_value_ip * 0.1761) if r_value_ip else None

        # DENSITY: lb/ft³ → kg/m³
        # Conversion factor: 16.0185
        # Example: Concrete at 150 lb/ft³ = 150 × 16.0185 = 2403 kg/m³
        density_lb_ft3 = self._to_float(self.get_property(mat_elem, 'Density'))
        density_kg_m3 = (density_lb_ft3 * 16.0185) if density_lb_ft3 else None

        # SPECIFIC HEAT: Btu/(lb·°F) → J/(kg·K)
        # Conversion factor: 4186.8
        # Example: Water at 1 Btu/(lb·°F) = 1 × 4186.8 = 4186.8 J/(kg·K)
        # Try 'SpecHeat' first, then 'SpecificHeat' (CBECC uses both)
        spec_heat_ip = self._to_float(self.get_property(mat_elem, 'SpecHeat'))
        if not spec_heat_ip:
            spec_heat_ip = self._to_float(self.get_property(mat_elem, 'SpecificHeat'))
        specific_heat = (spec_heat_ip * 4186.8) if spec_heat_ip else None

        # ================================================================
        # STEP 5: Build Annotation Dictionary
        # ================================================================
        # Annotations store format-specific properties that aren't in Material core fields.
        # This enables perfect round-trip: import → internal → export = original XML
        annotation = self._build_annotation(mat_elem, tag)

        # ================================================================
        # STEP 6: Create Material Object
        # ================================================================
        # All values now in SI units, ready for universal internal representation
        material = Material(
            id=mat_id,
            name=name,
            material_type=mat_type,
            thickness_m=thickness_m,           # SI: meters
            r_value_SI=r_value_SI,              # SI: m²·K/W
            density_kg_m3=density_kg_m3,        # SI: kg/m³
            specific_heat=specific_heat,        # SI: J/(kg·K)
            annotation=annotation               # Format-specific extras
        )

        return material

    def _build_annotation(self, mat_elem: ET.Element, tag: str) -> Dict[str, Any]:
        """
        Build annotation dictionary with format-specific properties.

        ANNOTATION STRATEGY:
        The Material class has fields for the most common properties (thickness,
        R-value, density, specific heat). However, CBECC has MANY additional
        properties that vary by material type:

        - Framing materials: FrmAsm, FrmCfg, FrmDpth, FrmSpc
        - Surface materials: Absorptance, Emittance, Roughness
        - Code compliance: CodeCat, CodeItem
        - Thermal alternatives: Conductivity (instead of R-value)
        - Insulation options: CavityInsOpt

        These don't fit cleanly into the universal Material model, so we store
        them in the annotation dict. This enables:
        1. Round-trip fidelity (export produces identical XML)
        2. Format-specific validation rules
        3. Future format conversions (e.g., CBECC → IDF)

        The 'xml_tag' annotation preserves whether this was <Mat> or <ResMat>,
        so the exporter knows which tag to generate.

        Args:
            mat_elem: Material XML element
            tag: Element tag name (<Mat> or <ResMat>)

        Returns:
            Annotation dictionary with format-specific properties
        """
        # Store the original XML tag for round-trip export
        # Exporter needs this to know whether to write <Mat> or <ResMat>
        annotation = {'xml_tag': tag}

        # List of CBECC-specific properties to preserve
        # These are not in the universal Material model but needed for CBECC
        additional_props = [
            # Thermal properties (alternative to R-value)
            'Conductivity',        # Btu/(h·ft·°F) - used instead of RValue for some materials

            # Surface radiative properties (for exterior materials)
            'Absorptance',         # Solar absorptance (0-1) - affects heat gain
            'Emittance',           # Thermal emittance (0-1) - affects radiant heat transfer
            'Roughness',           # Surface roughness - affects convection

            # Title 24 code compliance tracking
            'CodeCat',             # Code category (e.g., "Insulation", "Mass")
            'CodeItem',            # Specific code item reference

            # Framing assembly properties (for wood/metal framed walls)
            'FrmAsm',              # Framing assembly type
            'FrmCfg',              # Framing configuration (16" OC, 24" OC, etc.)
            'FrmDpth',             # Framing depth (inches)
            'FrmSpc',              # Framing spacing (inches)
            'FrmMat',              # Framing material (Wood, Metal)
            'FrmConfig',           # Framing configuration (alternate name)
            'FrmDepth',            # Framing depth (alternate name)

            # Insulation installation options
            'CavityIns',           # Cavity insulation R-value (numeric) - CRITICAL for MetalInsFrameLayers
            'CavityInsOpt'         # Cavity insulation option (loose fill, batt, spray foam)
        ]

        # Extract each property if present in XML
        # Only store non-null values to keep annotations clean
        for prop in additional_props:
            value = self.get_property(mat_elem, prop)
            if value:
                annotation[prop] = value

        return annotation

    def _get_name(self, element: ET.Element) -> Optional[str]:
        """
        Extract name from element (CIBD22X format).

        Tries: <n>, <Name>, id attribute

        Args:
            element: XML element

        Returns:
            Element name or None
        """
        # Try <n> child (CIBD22X format) - namespace-aware
        for child in element:
            tag = self._local_tag(child.tag)
            if tag == 'n' and child.text:
                return child.text.strip()

        # Try <Name> child - namespace-aware
        for child in element:
            tag = self._local_tag(child.tag)
            if tag == 'Name' and child.text:
                return child.text.strip()

        # Try id attribute
        name = element.get('id')
        if name:
            return name

        return None
