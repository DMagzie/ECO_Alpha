"""
WindowType Parser - Simple Catalog Parser
=========================================

PURPOSE:
Extracts fenestration type definitions (windows, doors, skylights) from CIBD22X
XML catalogs. Parses thermal and optical properties for glazing assemblies.

PATTERN: Simple Catalog Parser (no dependencies on other parsers)
See material_parser.py for detailed documentation of this pattern.

KEY OPERATIONS:
- Parse thermal properties: U-factor, SHGC (Solar Heat Gain Coefficient), VT (Visible Transmittance)
- Extract frame and glazing specifications
- Parse area (CBECC quirk: area can be in catalog OR opening - see OpeningParser)
- Store NFRC ratings and certification data in annotations

FENESTRATION TYPES:
- ResWinType, WinType (windows)
- DrType (doors)
- SkylType (skylights)
- FenCons (generic fenestration constructions)

DEPENDENCY NOTE: OpeningParser depends on this parser for area inheritance
(windows can get area from WindowType catalog when not specified inline).
"""

from typing import List, Optional, Dict, Any
import xml.etree.ElementTree as ET
import logging

from eco_tools.core.internal_repr import WindowType
from eco_tools.core.id_registry import IDRegistry
from .base_parser import BaseParser

# Get module logger
logger = logging.getLogger('eco_tools.parsers')


class WindowTypeParser(BaseParser):
    """Parser for CIBD22X fenestration type catalog elements"""

    # CIBD22X fenestration type catalog tags
    # NOTE: These are catalog-level elements (direct children of root),
    # NOT references inside geometry elements
    FENESTRATION_CATALOG_TAGS = [
        'ResWinType',  # Residential window types
        'FenCons',     # Fenestration constructions
        'WinType',     # Commercial window types
        'DrType',      # Door types
        'SkylType'     # Skylight types
    ]

    def __init__(self, id_registry: IDRegistry):
        """
        Initialize the window type parser.

        Args:
            id_registry: ID registry for generating unique window type IDs
        """
        super().__init__()
        self.id_registry = id_registry

    def parse_window_types(self, root: ET.Element) -> List[WindowType]:
        """
        Parse all fenestration types from CIBD22X catalog.

        IMPORTANT: Only parses catalog-level elements (direct children of root),
        NOT WinType/FenCons references inside opening elements.

        Args:
            root: Root XML element

        Returns:
            List of WindowType objects
        """
        window_types = []

        for tag in self.FENESTRATION_CATALOG_TAGS:
            # Use namespace-aware iteration through all descendants
            for wt_elem in root.iter():
                if self._local_tag(wt_elem.tag) == tag:
                    # CRITICAL: Filter out property references (elements with only text, no children)
                    # Property references look like: <WinType>ResidentialWindowType 1</WinType>
                    # Catalog definitions have child elements: <ResWinType><Name>...</Name><UFactor>...</UFactor></ResWinType>
                    if not self._is_catalog_definition(wt_elem):
                        continue  # Skip property references

                    window_type = self._parse_single_window_type(wt_elem, tag, len(window_types))
                    if window_type:
                        window_types.append(window_type)
                    else:
                        # WindowType parsing failed - likely missing required properties
                        name = self._get_name(wt_elem) or "unnamed"
                        logger.warning(f"Failed to parse {tag} window type '{name}'")

        logger.info(f"Parsed {len(window_types)} window types")
        return window_types

    def _is_catalog_definition(self, element: ET.Element) -> bool:
        """
        Check if element is a catalog definition (has child elements) or a property reference (only text).

        Catalog definition: <ResWinType><Name>...</Name><UFactor>...</UFactor></ResWinType>
        Property reference: <WinType>ResidentialWindowType 1</WinType>

        Args:
            element: XML element to check

        Returns:
            True if catalog definition, False if property reference
        """
        # Catalog definitions have child elements, property references don't
        # Check if element has any child elements (not just text)
        return len(list(element)) > 0

    def _parse_single_window_type(
        self,
        wt_elem: ET.Element,
        tag: str,
        index: int
    ) -> Optional[WindowType]:
        """
        Parse a single fenestration type element.

        Args:
            wt_elem: WindowType XML element
            tag: Element tag name (ResWinType, FenCons, etc.)
            index: Current count of window types (for default naming)

        Returns:
            WindowType object
        """
        # Get name (required, but generate default if missing)
        name = self._get_name(wt_elem)
        if not name:
            name = f"Window Type {index + 1}"

        # Generate window type ID
        wt_id = self.id_registry.generate_id('WT', name, '', 'CIBD22X')

        # Determine fenestration type from tag
        fen_type = self._determine_fenestration_type(tag)

        # Parse area (ft² → m²) - used for "Overall Window Area" specification method
        area_ft2 = self._to_float(self.get_property(wt_elem, 'Area'))
        area_m2 = (area_ft2 * 0.092903) if area_ft2 else None

        # Parse U-factor (Btu/h·ft²·°F → W/m²·K: multiply by 5.678)
        u_factor_ip = self._to_float(self.get_property(wt_elem, 'UFactor'))
        if not u_factor_ip:
            u_factor_ip = self._to_float(self.get_property(wt_elem, 'UValue'))
        u_factor_SI = (u_factor_ip * 5.678) if u_factor_ip else None

        # Parse SHGC and VT (dimensionless, no conversion)
        shgc = self._to_float(self.get_property(wt_elem, 'SHGC'))
        vt = self._to_float(self.get_property(wt_elem, 'VT'))
        if not vt:
            vt = self._to_float(self.get_property(wt_elem, 'VLT'))

        # Parse frame properties
        frame_type = self.get_property(wt_elem, 'FrmType')
        if not frame_type:
            frame_type = self.get_property(wt_elem, 'FrameType')

        # Parse glazing properties
        glazing_type = self.get_property(wt_elem, 'GlzgType')
        if not glazing_type:
            glazing_type = self.get_property(wt_elem, 'GlazingType')

        # Parse number of panes
        num_panes = self._to_int(self.get_property(wt_elem, 'NumPanes'))
        if not num_panes:
            num_panes = self._to_int(self.get_property(wt_elem, 'NumGlzgs'))

        # Parse gas fill
        gas_fill = self.get_property(wt_elem, 'GasFill')
        if not gas_fill:
            gas_fill = self.get_property(wt_elem, 'GapFillType')

        # Build annotation with all additional properties
        annotation = self._build_annotation(wt_elem, tag)

        # Create WindowType object
        window_type = WindowType(
            id=wt_id,
            name=name,
            fenestration_type=fen_type,
            area_m2=area_m2,
            u_factor_SI=u_factor_SI,
            shgc=shgc,
            vt=vt,
            frame_type=frame_type,
            glazing_type=glazing_type,
            num_panes=num_panes,
            gas_fill=gas_fill,
            annotation=annotation
        )

        return window_type

    def _determine_fenestration_type(self, tag: str) -> str:
        """
        Determine fenestration type from tag.

        Args:
            tag: Element tag name

        Returns:
            Fenestration type: 'window', 'door', or 'skylight'
        """
        if 'Win' in tag:
            return 'window'
        elif 'Dr' in tag or 'Door' in tag:
            return 'door'
        elif 'Skyl' in tag:
            return 'skylight'
        else:
            return 'window'

    def _build_annotation(self, wt_elem: ET.Element, tag: str) -> Dict[str, Any]:
        """
        Build annotation dictionary with all additional properties.

        Args:
            wt_elem: WindowType XML element
            tag: Element tag name

        Returns:
            Annotation dictionary
        """
        annotation = {'xml_tag': tag}

        # List of additional properties to capture
        additional_props = [
            'SpecMethod', 'NFRCUfactor', 'NFRCCertified',
            'Coating', 'LowECoating', 'TintType', 'FilmType',
            'SpacerType', 'EdgeSeal', 'DividerType',
            'ExteriorShade', 'InteriorShade', 'BetweenGlzShade',
            'OperableArea', 'RatedUFactor', 'RatedSHGC', 'RatedVT',
            'CertOrg', 'CertLabel', 'ProductType'
        ]

        for prop in additional_props:
            value = self.get_property(wt_elem, prop)
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
