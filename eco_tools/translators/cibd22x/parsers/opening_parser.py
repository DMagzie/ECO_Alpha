"""
Opening Parser - Hierarchical Parser (Bottom of Spatial Hierarchy)
==================================================================

PURPOSE: Extracts opening definitions (windows, doors, skylights) from CIBD22X XML.
Openings are the BOTTOM of spatial hierarchy: ZoneGroups → Zones → Surfaces → Openings.

PATTERN: Hierarchical Parser - See zone_parser.py for detailed documentation.

KEY OPERATIONS:
- Parse opening geometry (area, height, width)
- Link openings to parent surfaces
- Reference window types
- Area inheritance: CBECC quirk allows area from WindowType catalog OR inline
- Parse PolyLp (polygon coordinates) for complex opening shapes

DEPENDENCIES:
- Requires Surfaces to be parsed first (openings reference parent surfaces)
- Requires WindowTypes for area inheritance (window_type_area_map parameter)

SPATIAL HIERARCHY:
ZoneGroups → Zones → Surfaces → Openings (this parser - bottom of hierarchy)
Parse order: Must parse Surfaces AND WindowTypes BEFORE Openings.
"""

from typing import List, Optional, Dict
import xml.etree.ElementTree as ET
import logging

from eco_tools.core.internal_repr import Opening, Surface
from eco_tools.core.id_registry import IDRegistry
from .base_parser import BaseParser

# Get module logger
logger = logging.getLogger('eco_tools.parsers')


class OpeningParser(BaseParser):
    """Parser for CIBD22X opening elements (windows, doors, skylights)"""

    # CIBD22X opening tags (residential, commercial, and abbreviated forms)
    OPENING_TAGS = [
        'ResWin', 'ResDoor', 'ResDr', 'ResSkylt',
        'Window', 'Door', 'Skylight',
        'ComWin', 'Win', 'Dr', 'Skylt'
    ]

    # Surface tags that can contain openings
    SURFACE_TAGS_WITH_OPENINGS = [
        'ResExtWall', 'ResIntWall', 'ResCathedralCeiling', 'ResAtticRoof',
        'ExtWall', 'IntWall', 'Roof', 'CathedralCeiling'
    ]

    def __init__(self, id_registry: IDRegistry):
        """
        Initialize the opening parser.

        Args:
            id_registry: ID registry for generating unique opening IDs
        """
        super().__init__()
        self.id_registry = id_registry

    def parse_openings(
        self,
        root: ET.Element,
        surfaces: List[Surface],
        window_type_area_map: Optional[Dict[str, float]] = None
    ) -> List[Opening]:
        """
        Parse all openings from CIBD22X.

        Args:
            root: Root XML element
            surfaces: List of surfaces (for surface ID lookup)
            window_type_area_map: Optional map of window type name → area (m²)
                                 Used for "Overall Window Area" spec method

        Returns:
            List of Opening objects
        """
        openings = []
        surface_map = {s.name: s.id for s in surfaces}

        # Use provided window type area map or empty dict
        if window_type_area_map is None:
            window_type_area_map = {}

        # Iterate through all surface elements
        for surf_elem in root.iter():
            surf_tag = self._local_tag(surf_elem.tag)
            if surf_tag not in self.SURFACE_TAGS_WITH_OPENINGS:
                continue

            # Get surface name and ID
            surf_name = self._get_name(surf_elem)
            surf_id = surface_map.get(surf_name)
            if not surf_id:
                continue

            # Find all openings in this surface - namespace-aware
            for open_tag in self.OPENING_TAGS:
                for open_elem in surf_elem.iter():
                    if self._local_tag(open_elem.tag) == open_tag:
                        opening = self._parse_single_opening(
                            open_elem, open_tag, surf_id, surf_name, window_type_area_map
                        )
                        if opening:
                            openings.append(opening)
                        else:
                            open_name = self._get_name(open_elem) or "unnamed"
                            logger.warning(f"Failed to parse {open_tag} opening '{open_name}' on surface '{surf_name}': missing required name")

        logger.info(f"Parsed {len(openings)} openings")
        return openings

    def _parse_single_opening(
        self,
        open_elem: ET.Element,
        open_tag: str,
        surf_id: str,
        surf_name: str,
        window_type_area_map: Dict[str, float]
    ) -> Optional[Opening]:
        """
        Parse a single opening element.

        Args:
            open_elem: Opening XML element
            open_tag: Opening tag name (e.g., 'ResWin', 'Door')
            surf_id: Parent surface ID
            surf_name: Parent surface name
            window_type_area_map: Map of window type name → area (m²)

        Returns:
            Opening object or None if name is missing
        """
        # Get opening name
        open_name = self._get_name(open_elem)
        if not open_name:
            return None

        # Generate opening ID
        # Special case: If the name already looks like a generated ID (starts with 'O_'),
        # use it directly to preserve IDs during round-trip export/import
        if open_name.startswith('O_'):
            open_id = open_name
        else:
            open_id = self.id_registry.generate_id('O', open_name, surf_name, 'CIBD22X')

        # Parse dimensions (convert ft to m)
        area_ft2 = self._to_float(self.get_property(open_elem, 'Area'))

        # Calculate from PolyLp if not provided
        if not area_ft2:
            area_ft2 = self._calculate_area_from_polylp(open_elem)

        area_m2 = (area_ft2 * 0.092903) if area_ft2 else None

        # Parse height and width
        height_ft = self._to_float(self.get_property(open_elem, 'Height'))
        height_m = (height_ft * 0.3048) if height_ft else None

        width_ft = self._to_float(self.get_property(open_elem, 'Width'))
        width_m = (width_ft * 0.3048) if width_ft else None

        # Parse window type reference
        # CBECC uses 'FenConsRef', others may use 'WinType'
        win_type_ref = self.get_property(open_elem, 'FenConsRef')
        if not win_type_ref:
            win_type_ref = self.get_property(open_elem, 'WinType')

        # Parse fenestration construction reference
        fen_cons_ref = self.get_property(open_elem, 'FenConsRef')

        # If no direct area, look up from window type (for "Overall Window Area" spec method)
        if not area_m2 and win_type_ref:
            area_m2 = window_type_area_map.get(win_type_ref)

        # Parse fenestration properties
        u_factor = self._to_float(self.get_property(open_elem, 'UFactor'))
        shgc = self._to_float(self.get_property(open_elem, 'SHGC'))
        vt = self._to_float(self.get_property(open_elem, 'VT'))

        # Determine opening type
        open_type = self._determine_opening_type(open_tag)

        # Create Opening object
        opening = Opening(
            id=open_id,
            parent_surface_id=surf_id,
            type=open_type,
            area_m2=area_m2,
            height_m=height_m,
            width_m=width_m,
            window_type_ref=win_type_ref,
            fenestration_cons_ref=fen_cons_ref,
            u_factor_SI=u_factor,
            shgc=shgc,
            vt=vt,
            annotation={'xml_tag': open_tag}
        )

        return opening

    def _determine_opening_type(self, open_tag: str) -> str:
        """
        Determine opening type from tag.

        Args:
            open_tag: Opening XML tag name

        Returns:
            Opening type: 'window', 'door', or 'skylight'
        """
        if 'Door' in open_tag or open_tag == 'Dr' or open_tag == 'ResDr':
            return 'door'
        elif 'Skylight' in open_tag or 'Skylt' in open_tag:
            return 'skylight'
        else:
            return 'window'

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

    def _local_tag(self, tag: str) -> str:
        """
        Strip namespace from XML tag.

        Args:
            tag: XML tag (may include namespace)

        Returns:
            Local tag name without namespace
        """
        if '}' in tag:
            return tag.split('}')[1]
        return tag
