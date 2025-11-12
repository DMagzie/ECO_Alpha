"""
Construction Parser - Simple Catalog Parser
==========================================

PURPOSE:
Extracts construction assembly definitions (walls, roofs, floors, ceilings, slabs)
from CIBD22X XML catalogs. Parses thermal properties and material layer references.

PATTERN: Simple Catalog Parser (no dependencies on other parsers)
See material_parser.py for detailed documentation of this pattern.

KEY OPERATIONS:
- Parse U-factor and R-value (with IP → SI unit conversion)
- Extract material layer references (MaterialRef elements)
- Parse framing configuration (wood/metal, depth, spacing)
- Store CBECC-specific properties in annotations for round-trip

CONSTRUCTION TYPES:
- ResConsAssm, ConsAssm (generic assemblies)
- ExtWallCons, RoofCons, FloorCons, SlabCons, CeilingCons (specific types)

NOTE: This parser extracts catalog DEFINITIONS, not references. Construction
references in surfaces are handled by SurfaceParser.
"""

from typing import List, Optional, Dict, Any
import xml.etree.ElementTree as ET
import logging

from eco_tools.core.internal_repr import Construction
from eco_tools.core.id_registry import IDRegistry
from .base_parser import BaseParser

# Get module logger
logger = logging.getLogger('eco_tools.parsers')


class ConstructionParser(BaseParser):
    """Parser for CIBD22X construction assembly elements"""

    # CIBD22X construction assembly catalog tags
    # NOTE: These are catalog-level elements (direct children of root),
    # NOT references inside geometry elements
    CONSTRUCTION_CATALOG_TAGS = [
        'ResConsAssm',   # Residential construction assemblies
        'ConsAssm',      # Commercial construction assemblies
        'ExtWallCons',   # Exterior wall constructions
        'RoofCons',      # Roof constructions
        'FloorCons',     # Floor constructions
        'SlabCons',      # Slab constructions
        'CeilingCons'    # Ceiling constructions
    ]

    def __init__(self, id_registry: IDRegistry):
        """
        Initialize the construction parser.

        Args:
            id_registry: ID registry for generating unique construction IDs
        """
        super().__init__()
        self.id_registry = id_registry

    def parse_constructions(self, root: ET.Element) -> List[Construction]:
        """
        Parse all construction assemblies from CIBD22X catalog.

        IMPORTANT: Only parses catalog-level elements (direct children of root),
        NOT ConsAssmRef references inside surface elements.

        Args:
            root: Root XML element

        Returns:
            List of Construction objects
        """
        constructions = []

        for tag in self.CONSTRUCTION_CATALOG_TAGS:
            # Use namespace-aware iteration
            for cons_elem in root.iter():
                if self._local_tag(cons_elem.tag) == tag:
                    construction = self._parse_single_construction(cons_elem, tag, len(constructions))
                    if construction:
                        constructions.append(construction)
                    else:
                        # Construction parsing failed - likely missing required properties
                        name = self._get_name(cons_elem) or "unnamed"
                        logger.warning(f"Failed to parse {tag} construction '{name}'")

        logger.info(f"Parsed {len(constructions)} constructions")
        return constructions

    def _parse_single_construction(
        self,
        cons_elem: ET.Element,
        tag: str,
        index: int
    ) -> Optional[Construction]:
        """
        Parse a single construction assembly element.

        Args:
            cons_elem: Construction XML element
            tag: Element tag name (ResConsAssm, ConsAssm, etc.)
            index: Current count of constructions (for default naming)

        Returns:
            Construction object
        """
        # Get name (required, but generate default if missing)
        name = self._get_name(cons_elem)
        if not name:
            name = f"Construction {index + 1}"

        # Generate construction ID
        cons_id = self.id_registry.generate_id('CONS', name, '', 'CIBD22X')

        # Determine construction type from tag
        cons_type = self._determine_construction_type(tag)

        # Parse U-factor (Btu/h·ft²·°F → W/m²·K: multiply by 5.678)
        u_factor_ip = self._to_float(self.get_property(cons_elem, 'UFactor'))
        if not u_factor_ip:
            u_factor_ip = self._to_float(self.get_property(cons_elem, 'UValue'))
        u_factor_SI = (u_factor_ip * 5.678) if u_factor_ip else None

        # Parse R-value (ft²·°F·h/Btu → m²·K/W: multiply by 0.1761)
        r_value_ip = self._to_float(self.get_property(cons_elem, 'RValue'))
        if not r_value_ip:
            r_value_ip = self._to_float(self.get_property(cons_elem, 'RVal'))
        r_value_SI = (r_value_ip * 0.1761) if r_value_ip else None

        # Parse material layer references
        material_layers = self._parse_material_layers(cons_elem)

        # Parse framing configuration
        framing_config = self.get_property(cons_elem, 'FrmCfg')
        if not framing_config:
            framing_config = self.get_property(cons_elem, 'FrmAsm')

        # Parse framing depth (inches → meters: multiply by 0.0254)
        framing_depth_in = self._to_float(self.get_property(cons_elem, 'FrmDpth'))
        if not framing_depth_in:
            framing_depth_in = self._to_float(self.get_property(cons_elem, 'FrmDepth'))
        framing_depth_m = (framing_depth_in * 0.0254) if framing_depth_in else None

        # Parse framing spacing (inches → meters: multiply by 0.0254)
        framing_spacing_in = self._to_float(self.get_property(cons_elem, 'FrmSpc'))
        if not framing_spacing_in:
            framing_spacing_in = self._to_float(self.get_property(cons_elem, 'FrmSpacing'))
        framing_spacing_m = (framing_spacing_in * 0.0254) if framing_spacing_in else None

        # Build annotation with all additional properties
        annotation = self._build_annotation(cons_elem, tag)

        # Create Construction object
        construction = Construction(
            id=cons_id,
            name=name,
            construction_type=cons_type,
            u_factor_SI=u_factor_SI,
            r_value_SI=r_value_SI,
            material_layers=material_layers,
            framing_config=framing_config,
            framing_depth_m=framing_depth_m,
            framing_spacing_m=framing_spacing_m,
            annotation=annotation
        )

        return construction

    def _determine_construction_type(self, tag: str) -> str:
        """
        Determine construction type from tag.

        Args:
            tag: Element tag name

        Returns:
            Construction type: 'wall', 'roof', 'floor', or 'unknown'
        """
        if 'Wall' in tag:
            return 'wall'
        elif 'Roof' in tag or 'Ceiling' in tag:
            return 'roof'
        elif 'Floor' in tag or 'Slab' in tag:
            return 'floor'
        else:
            return 'unknown'

    def _parse_material_layers(self, cons_elem: ET.Element) -> List[str]:
        """
        Parse material layer references from construction element.

        Material layers are specified as MatRef child elements that reference
        material catalog entries by name.

        Args:
            cons_elem: Construction XML element

        Returns:
            List of material reference names
        """
        material_layers = []

        for mat_ref_elem in cons_elem.findall('.//MatRef'):
            if mat_ref_elem.text:
                material_layers.append(mat_ref_elem.text.strip())

        return material_layers

    def _build_annotation(self, cons_elem: ET.Element, tag: str) -> Dict[str, Any]:
        """
        Build annotation dictionary with all additional properties.

        CRITICAL - CanAssignTo Property:
        ================================
        The CanAssignTo property is ESSENTIAL for construction validation in CBECC-Com.
        It specifies which surface types can reference this construction.

        WHY THIS MATTERS:
        When a surface (IntWall, InteriorFloor, etc.) references a construction by name,
        CBECC-Com validates that the construction's CanAssignTo matches the surface type.

        EXAMPLE ERROR (when CanAssignTo is missing or wrong):
        "IntWall 'IntWall : A1_L01' references incompatible construction object
         'Interior Wall Cons' (CanAssignTo = 'Exterior Walls')"

        HOW THE ERROR OCCURRED:
        1. Parser did NOT capture CanAssignTo property in annotations
        2. Exporter created <CanAssignTo/> (empty element)
        3. CBECC-Com defaulted empty CanAssignTo to "Exterior Walls"
        4. Interior walls/floors using this construction failed validation
        5. Result: 1,130 simulation errors!

        VALID VALUES:
        - "Exterior Walls"
        - "Interior Walls"
        - "Interior Floors"
        - "Ceilings (below attic)"
        - "Attic Roofs"
        - "Cathedral Ceilings"
        - "Underground Walls"

        ResConsAssm Layer Properties:
        =============================
        ResConsAssm (Residential Construction Assembly) uses a layered specification
        system different from commercial constructions. Instead of U-factors, they
        specify layers like:
        - CavityLayer: Insulation in wall cavity (e.g., "R 19")
        - FrameLayer: Framing specification (e.g., "2x4 @ 16 in. O.C.")
        - WallExtFinishLayer: Exterior finish (e.g., "Synthetic Stucco")
        - MassLayer: Thermal mass material (e.g., "Concrete")

        ALL of these must be preserved for correct round-trip fidelity.

        Args:
            cons_elem: Construction XML element
            tag: Element tag name

        Returns:
            Annotation dictionary with ALL format-specific properties
        """
        annotation = {'xml_tag': tag}

        # List of additional properties to capture for round-trip fidelity
        additional_props = [
            # CRITICAL: CanAssignTo specifies which surface types this construction can be assigned to
            # MUST be captured or CBECC validation fails with "incompatible construction" errors!
            'CanAssignTo',

            # Surface properties (commercial constructions)
            'CompatibleSurfType', 'ConsType', 'ExtRoughness',
            'ExtSolAbs', 'ExtThmAbs', 'ExtVisAbs',
            'IntSolAbs', 'IntThmAbs', 'IntVisAbs',

            # Insulation properties (commercial constructions)
            'CavityInsOpt', 'CavityInsDepth', 'CavityInsRVal',
            'ContInsOpt', 'ContInsDepth', 'ContInsRVal',

            # ResConsAssm layer properties (residential constructions)
            'CavityLayer',           # Insulation layer (e.g., "R 19", "R 38")
            'FrameLayer',            # Framing spec (e.g., "2x4 @ 16 in. O.C.")
            'SheathInsulLayer',      # Sheathing/insulation layer
            'SheathInsulLayerRVal',  # Sheathing R-value
            'WallExtFinishLayer',    # Exterior finish (e.g., "Synthetic Stucco")
            'InsideFinishLayer',     # Interior finish

            # Mass/concrete properties (concrete/ICF/brick constructions)
            'Type',                  # Construction type (e.g., "Concrete / ICF / Brick")
            'MassLayer',             # Thermal mass material
            'MassThickness',         # Mass thickness (e.g., " 8 in.")

            # Additional features
            'RadiantBarrier',        # Radiant barrier present (1/0)

            # Framing properties (detailed framing specifications)
            'StudWidth', 'StudSpacing', 'NumLayers'
        ]

        for prop in additional_props:
            value = self.get_property(cons_elem, prop)
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
