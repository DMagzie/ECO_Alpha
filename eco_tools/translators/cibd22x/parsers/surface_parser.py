"""
Surface Parser - Hierarchical Parser (Middle of Spatial Hierarchy)
==================================================================

PURPOSE: Extracts surface definitions (walls, roofs, floors, ceilings) from CIBD22X XML.
Surfaces are the MIDDLE of spatial hierarchy: ZoneGroups → Zones → Surfaces → Openings.

PATTERN: Hierarchical Parser - See zone_parser.py for detailed documentation.

KEY OPERATIONS:
- Parse surface geometry (area, perimeter, orientation, tilt)
- Convert units: ft² → m², ft → m
- Link surfaces to parent zones
- Reference construction assemblies
- Parse PolyLp (polygon coordinates) using Shoelace formula for area

DEPENDENCIES:
- Requires Zones to be parsed first (surfaces reference parent zones)
- Openings will reference these surfaces as parents

SPATIAL HIERARCHY:
ZoneGroups → Zones → Surfaces (this parser) → Openings
Parse order: Must parse Zones BEFORE Surfaces, Surfaces BEFORE Openings.
"""

from typing import List, Optional, Dict, Any
import xml.etree.ElementTree as ET
import logging

from eco_tools.core.internal_repr import Surface, Zone
from eco_tools.core.id_registry import IDRegistry
from .base_parser import BaseParser

# Get module logger
logger = logging.getLogger('eco_tools.parsers')


class SurfaceParser(BaseParser):
    """Parser for CIBD22X surface elements"""

    # CIBD22X surface tags (residential and commercial)
    SURFACE_TAGS = [
        'ResExtWall', 'ResIntWall', 'ResIntFlr', 'ResSlabFlr', 'ResUndgrWall', 'ResUndgrFlr',
        'ResCathedralCeiling', 'ResCeilingBelowAttic', 'ResAtticRoof', 'ResOtherFlr',
        'ExtWall', 'IntWall', 'Roof', 'ExtFlr', 'IntFlr', 'UndgrWall', 'UndgrFlr'
    ]

    # Zone tags that can contain surfaces
    ZONE_TAGS = ['ResZn', 'ComZn', 'ResOtherZn', 'ResAttic', 'Spc', 'ThrmlZn']

    def __init__(self, id_registry: IDRegistry):
        """
        Initialize the surface parser.

        Args:
            id_registry: ID registry for generating unique surface IDs
        """
        super().__init__()
        self.id_registry = id_registry

    def parse_surfaces(self, root: ET.Element, zones: List[Zone]) -> List[Surface]:
        """
        Parse all surfaces from CIBD22X.

        Args:
            root: Root XML element
            zones: List of zones (for zone ID lookup)

        Returns:
            List of Surface objects
        """
        surfaces = []
        zone_map = {z.name: z.id for z in zones}

        # Iterate through all zone elements
        for zone_elem in root.iter():
            zone_tag = self._local_tag(zone_elem.tag)
            if zone_tag not in self.ZONE_TAGS:
                continue

            # Get zone name and ID
            zone_name = self._get_name(zone_elem)
            zone_id = zone_map.get(zone_name)
            if not zone_id:
                continue

            # Find all surfaces in this zone - direct children only
            # FIX POLY-001: Changed from zone_elem.iter() to zone_elem (direct children)
            # to prevent duplicate surfaces when parsing nested zone structures
            for surf_tag in self.SURFACE_TAGS:
                for surf_elem in zone_elem:  # Direct children only, not all descendants
                    if self._local_tag(surf_elem.tag) == surf_tag:
                        surface = self._parse_single_surface(surf_elem, surf_tag, zone_id, zone_name)
                        if surface:
                            surfaces.append(surface)
                        else:
                            surf_name = self._get_name(surf_elem) or "unnamed"
                            logger.warning(f"Failed to parse {surf_tag} surface '{surf_name}' in zone '{zone_name}': missing required name")

        logger.info(f"Parsed {len(surfaces)} surfaces")
        return surfaces

    def _parse_single_surface(
        self,
        surf_elem: ET.Element,
        surf_tag: str,
        zone_id: str,
        zone_name: str
    ) -> Optional[Surface]:
        """
        Parse a single surface element.

        Args:
            surf_elem: Surface XML element
            surf_tag: Surface tag name (e.g., 'ResExtWall')
            zone_id: Parent zone ID
            zone_name: Parent zone name

        Returns:
            Surface object or None if name is missing
        """
        # Get surface name
        surf_name = self._get_name(surf_elem)
        if not surf_name:
            return None

        # Generate surface ID
        surf_id = self.id_registry.generate_id('S', surf_name, zone_name, 'CIBD22X')

        # Parse area (ft² → m²)
        area_str = self.get_property(surf_elem, 'Area')
        area_ft2 = self._to_float(area_str)

        # Calculate from PolyLp if not provided
        if not area_ft2:
            area_ft2 = self._calculate_area_from_polylp(surf_elem)
            area_str = None  # Calculated, not from original XML

        area_m2 = (area_ft2 * 0.092903) if area_ft2 else None

        # Parse perimeter (ft → m)
        perimeter_str = self.get_property(surf_elem, 'Perimeter')
        perimeter_ft = self._to_float(perimeter_str)
        perimeter_m = (perimeter_ft * 0.3048) if perimeter_ft else None

        # Parse PolyLp vertices for CIBD25 export
        vertices = self._parse_polylp_vertices(surf_elem)

        # Parse orientation and tilt
        azimuth = self._to_float(self.get_property(surf_elem, 'Az'))
        tilt = self._to_float(self.get_property(surf_elem, 'Tilt'))

        # Parse CBECC Orientation (Front, Back, Left, Right)
        orientation_text = self.get_property(surf_elem, 'Orientation')

        # Parse roof-specific properties
        roof_rise = self.get_property(surf_elem, 'RoofRise')
        roof_sol_reflect = self.get_property(surf_elem, 'RoofSolReflect')

        # Parse construction reference
        construction_ref = self.get_property(surf_elem, 'ConsAssmRef')
        if not construction_ref:
            construction_ref = self.get_property(surf_elem, 'Construction')

        # Parse thermal properties
        ext_solar_abs = self._to_float(self.get_property(surf_elem, 'ExtSolAbs'))
        ext_thermal_abs = self._to_float(self.get_property(surf_elem, 'ExtThrmlAbs'))
        adjacent_space_ref = self.get_property(surf_elem, 'AdjacentSpcRef')

        # Determine surface type
        surf_type = self._determine_surface_type(surf_tag)

        # Determine adjacency
        adjacency = self._determine_adjacency(surf_tag)

        # Determine surface subtype
        surf_subtype = self._determine_surface_subtype(surf_tag)

        # Parse party wall/floor properties
        is_party_surface, outside_zone_ref, floor_z_str = self._parse_party_properties(surf_elem, surf_tag)

        # Use Outside as adjacent_space_ref if not already set
        if not adjacent_space_ref and outside_zone_ref:
            adjacent_space_ref = outside_zone_ref

        # Build annotation with original IP values for round-trip fidelity
        annotation = self._build_annotation(
            surf_tag, area_str, perimeter_str, floor_z_str,
            orientation_text, roof_rise, roof_sol_reflect
        )

        # Create Surface object
        surface = Surface(
            id=surf_id,
            name=surf_name,
            parent_zone_id=zone_id,
            surface_type=surf_type,
            surface_subtype=surf_subtype,
            area_m2=area_m2,
            perimeter_m=perimeter_m,
            vertices=vertices,
            tilt_deg=tilt,
            azimuth_deg=azimuth,
            construction_ref=construction_ref,
            adjacency=adjacency,
            is_party_surface=is_party_surface,
            ext_solar_abs=ext_solar_abs,
            ext_thermal_abs=ext_thermal_abs,
            adjacent_space_ref=adjacent_space_ref,
            annotation=annotation
        )

        return surface

    def _calculate_area_from_polylp(self, element: ET.Element) -> Optional[float]:
        """
        Calculate area from PolyLp (polygon loop) using Shoelace formula.

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

    def _parse_polylp_vertices(self, element: ET.Element) -> Optional[List[Dict[str, float]]]:
        """
        Parse PolyLp vertices for CIBD25 export.

        Args:
            element: XML element that may contain a PolyLp child

        Returns:
            List of vertices [{'x': float, 'y': float, 'z': float}, ...] or None if no PolyLp found
        """
        polylp = self.find_child(element, 'PolyLp')
        if polylp is None:
            return None

        # Extract all 3 coordinates (X, Y, Z) from CartesianPt elements
        vertices = []
        for pt in self.find_children(polylp, 'CartesianPt'):
            coords = self.find_children(pt, 'Coord')
            if len(coords) >= 3:
                x = self._to_float(coords[0].text)
                y = self._to_float(coords[1].text)
                z = self._to_float(coords[2].text)
                if x is not None and y is not None and z is not None:
                    vertices.append({'x': x, 'y': y, 'z': z})

        return vertices if len(vertices) >= 3 else None

    def _determine_surface_type(self, surf_tag: str) -> str:
        """
        Determine surface type from tag.

        Args:
            surf_tag: Surface XML tag name

        Returns:
            Surface type: 'wall', 'roof', or 'floor'
        """
        if 'Roof' in surf_tag or 'Ceiling' in surf_tag:
            return 'roof'
        elif 'Flr' in surf_tag or 'Floor' in surf_tag or 'Slab' in surf_tag:
            return 'floor'
        else:
            return 'wall'

    def _determine_adjacency(self, surf_tag: str) -> str:
        """
        Determine adjacency from tag.

        Args:
            surf_tag: Surface XML tag name

        Returns:
            Adjacency: 'exterior', 'interior', or 'attic'
        """
        if 'Int' in surf_tag:
            return 'interior'
        elif 'Ext' in surf_tag:
            return 'exterior'
        elif 'Attic' in surf_tag:
            return 'attic'
        else:
            return 'exterior'

    def _determine_surface_subtype(self, surf_tag: str) -> Optional[str]:
        """
        Determine surface subtype from tag.

        Args:
            surf_tag: Surface XML tag name

        Returns:
            Surface subtype or None
        """
        subtype_map = {
            'ResExtWall': 'res_ext_wall',
            'ResIntWall': 'res_int_wall',
            'ResSlabFlr': 'res_slab_floor',
            'ResUndgrFlr': 'res_undergr_floor',
            'ResIntFlr': 'res_int_floor',
            'ResUndgrWall': 'res_undergr_wall',
            'ResCathedralCeiling': 'res_cathedral_ceiling',
            'ResCeilingBelowAttic': 'res_ceiling_below_attic',
            'ResAtticRoof': 'res_attic_roof',
            'ResOtherFlr': 'res_other_floor'
        }
        return subtype_map.get(surf_tag)

    def _parse_party_properties(self, surf_elem: ET.Element, surf_tag: str) -> tuple:
        """
        Parse party wall/floor properties.

        Args:
            surf_elem: Surface XML element
            surf_tag: Surface tag name

        Returns:
            Tuple of (is_party_surface, outside_zone_ref, floor_z_str)
        """
        is_party_surface = False
        outside_zone_ref = None
        floor_z_str = None

        if surf_tag == 'ResIntWall':
            # Check for IsPartySurface flag
            is_party_text = self.get_property(surf_elem, 'IsPartySurface')
            if is_party_text == '1' or is_party_text == 'true':
                is_party_surface = True
            # Get adjacent zone reference
            outside_zone_ref = self.get_property(surf_elem, 'Outside')

        elif surf_tag == 'ResIntFlr':
            # ResIntFlr (interior floors between zones) properties
            is_party_text = self.get_property(surf_elem, 'IsPartySurface')
            if is_party_text == '1' or is_party_text == 'true':
                is_party_surface = True
            # Get adjacent zone reference (zone below)
            outside_zone_ref = self.get_property(surf_elem, 'Outside')
            # FloorZ is COMPULSORY for ResIntFlr - Z coordinate of floor
            floor_z_str = self.get_property(surf_elem, 'FloorZ')

        return is_party_surface, outside_zone_ref, floor_z_str

    def _build_annotation(
        self,
        surf_tag: str,
        area_str: Optional[str],
        perimeter_str: Optional[str],
        floor_z_str: Optional[str],
        orientation_text: Optional[str],
        roof_rise: Optional[str],
        roof_sol_reflect: Optional[str]
    ) -> Dict[str, Any]:
        """
        Build annotation dictionary with original IP values.

        Args:
            surf_tag: Surface XML tag
            area_str: Original area string
            perimeter_str: Original perimeter string
            floor_z_str: Original FloorZ string
            orientation_text: Orientation text
            roof_rise: Roof rise value
            roof_sol_reflect: Roof solar reflectance

        Returns:
            Annotation dictionary
        """
        annotation = {'xml_tag': surf_tag}

        if area_str:
            annotation['original_area_ft2'] = area_str
        if perimeter_str:
            annotation['original_perimeter_ft'] = perimeter_str
        if floor_z_str:
            annotation['original_floor_z_ft'] = floor_z_str
        if orientation_text:
            annotation['orientation'] = orientation_text
        if roof_rise:
            annotation['roof_rise'] = roof_rise
        if roof_sol_reflect:
            annotation['roof_sol_reflect'] = roof_sol_reflect

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
