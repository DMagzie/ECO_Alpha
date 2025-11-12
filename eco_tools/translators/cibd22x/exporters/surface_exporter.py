"""
Surface Exporter - Hierarchical Exporter (Middle of Spatial Hierarchy)
======================================================================

PURPOSE:
Serializes Surface objects (walls, roofs, floors) to CIBD22X XML format.
Surfaces are the MIDDLE of spatial hierarchy: ZoneGroups → Zones → Surfaces → Openings.

EXPORT STRATEGY:
1. Determine XML tag from annotation ('xml_tag') or surface_subtype
2. Convert SI units back to Imperial (area, perimeter, heights)
3. Export geometry properties (orientation, tilt, azimuth)
4. Export construction reference
5. Delegate to OpeningExporter for nested openings
6. Restore format-specific properties from annotations

HIERARCHICAL EXPORT:
Surfaces are exported as CHILDREN of zone elements, not as top-level elements.
The parent ZoneExporter calls this exporter to add surfaces within each zone.

UNIT CONVERSIONS (SI → Imperial):
- Area: m² → ft² (÷ 0.092903)
- Perimeter: m → ft (÷ 0.3048)
- Heights/depths: m → ft (÷ 0.3048)

ANNOTATION RESTORATION:
- 'xml_tag': Original tag (ResExtWall, ExtWall, Roof, etc.)
- 'original_area_ft2', 'original_perimeter_ft': Original IP values
- Orientation, roof properties, party surface flags

COMPOSITION:
Uses OpeningExporter to handle nested openings within surfaces.

PATTERN: Hierarchical Exporter - Called by parent (ZoneExporter)
"""

from typing import List, Optional
import xml.etree.ElementTree as ET
import logging

from eco_tools.core.internal_repr import Surface, Opening
from .base_exporter import BaseExporter
from .opening_exporter import OpeningExporter
from .format_utils import Format, get_name_tag, get_construction_ref_tag, get_adjacent_space_ref_tag

# Get module logger
logger = logging.getLogger('eco_tools.exporters')


class SurfaceExporter(BaseExporter):
    """Exporter for CIBD22X surface elements"""

    def __init__(self):
        super().__init__()
        self.opening_exporter = OpeningExporter()

    def export_surface(
        self,
        parent: ET.Element,
        surface: Surface,
        openings: List[Opening],
        format_type: Format = Format.CIBD22
    ) -> Optional[ET.Element]:
        """
        Export a single surface as a child of a zone element.

        Args:
            parent: Parent zone XML element
            surface: Surface object to export
            openings: All openings (will filter to this surface's openings)
            format_type: Format to use (CIBD22 or CIBD22X)

        Returns:
            Created surface XML element or None if export failed
        """
        if not surface.name:
            logger.warning(f"Skipping surface with missing name (id: {surface.id})")
            return None

        # Determine XML tag from annotation
        xml_tag = self.get_annotation(surface.annotation, 'xml_tag')
        if not xml_tag:
            # Fallback: determine from surface_subtype
            xml_tag = self._determine_tag_from_subtype(surface.surface_subtype, surface.surface_type)

        # Create surface element
        surf_elem = self.create_element(parent, xml_tag)

        # Add name (required) - use format-aware name tag
        name_tag = get_name_tag(format_type)
        self.add_text_element(surf_elem, name_tag, surface.name)

        # Area: m² → ft²
        # Prefer original IP value from annotation for perfect round-trip
        original_area_str = self.get_annotation(surface.annotation, 'original_area_ft2')
        if original_area_str:
            self.add_text_element(surf_elem, 'Area', original_area_str)
        elif surface.area_m2 is not None:
            area_ft2 = self.si_to_ip_area(surface.area_m2)
            self.add_numeric_element(surf_elem, 'Area', area_ft2, precision=2)

        # Perimeter: m → ft
        original_perimeter_str = self.get_annotation(surface.annotation, 'original_perimeter_ft')
        if original_perimeter_str:
            self.add_text_element(surf_elem, 'Perimeter', original_perimeter_str)
        elif surface.perimeter_m is not None:
            perimeter_ft = self.si_to_ip_length(surface.perimeter_m)
            self.add_numeric_element(surf_elem, 'Perimeter', perimeter_ft, precision=2)

        # Orientation and tilt
        if surface.azimuth_deg is not None:
            self.add_numeric_element(surf_elem, 'Az', surface.azimuth_deg, precision=1)

        if surface.tilt_deg is not None:
            self.add_numeric_element(surf_elem, 'Tilt', surface.tilt_deg, precision=1)

        # CBECC Orientation (Front, Back, Left, Right)
        orientation_text = self.get_annotation(surface.annotation, 'orientation')
        if orientation_text:
            self.add_text_element(surf_elem, 'Orientation', orientation_text)

        # Construction reference - use format-aware tag
        if surface.construction_ref:
            construction_tag = get_construction_ref_tag(format_type)
            self.add_text_element(surf_elem, construction_tag, surface.construction_ref)

        # Thermal properties
        if surface.ext_solar_abs is not None:
            self.add_numeric_element(surf_elem, 'ExtSolAbs', surface.ext_solar_abs, precision=3)

        if surface.ext_thermal_abs is not None:
            self.add_numeric_element(surf_elem, 'ExtThrmlAbs', surface.ext_thermal_abs, precision=3)

        # Adjacent space reference - property name depends on surface type
        # Interior walls use 'Outside', other surfaces use format-aware adjacent space tag
        if surface.adjacent_space_ref:
            if 'IntWall' in xml_tag or 'IntFlr' in xml_tag:
                # Interior walls and floors use 'Outside' property
                self.add_text_element(surf_elem, 'Outside', surface.adjacent_space_ref)
            else:
                # Other surfaces use format-aware adjacent space tag
                adjacent_tag = get_adjacent_space_ref_tag(format_type)
                self.add_text_element(surf_elem, adjacent_tag, surface.adjacent_space_ref)

        # Party surface (for interior walls/floors between units)
        if surface.is_party_surface:
            self.add_text_element(surf_elem, 'IsPartySurface', '1')

        # Roof-specific properties
        roof_rise = self.get_annotation(surface.annotation, 'roof_rise')
        if roof_rise:
            self.add_text_element(surf_elem, 'RoofRise', roof_rise)

        roof_sol_reflect = self.get_annotation(surface.annotation, 'roof_sol_reflect')
        if roof_sol_reflect:
            self.add_text_element(surf_elem, 'RoofSolReflect', roof_sol_reflect)

        # Floor Z coordinate (for ResIntFlr)
        original_floor_z = self.get_annotation(surface.annotation, 'original_floor_z_ft')
        if original_floor_z:
            self.add_text_element(surf_elem, 'FloorZ', original_floor_z)

        # Export openings for this surface - pass format_type for format-aware property names
        surf_openings = [o for o in openings if o.parent_surface_id == surface.id]
        for opening in surf_openings:
            self.opening_exporter.export_opening(surf_elem, opening, format_type)

        return surf_elem

    def _determine_tag_from_subtype(self, surface_subtype: Optional[str], surface_type: str) -> str:
        """
        Determine XML tag from surface_subtype or fallback to surface_type.

        Args:
            surface_subtype: Specific subtype (e.g., 'res_ext_wall')
            surface_type: General type ('wall', 'roof', 'floor')

        Returns:
            XML tag name
        """
        # Map from surface_subtype to XML tag
        subtype_map = {
            'res_ext_wall': 'ResExtWall',
            'res_int_wall': 'ResIntWall',
            'res_slab_floor': 'ResSlabFlr',
            'res_undergr_floor': 'ResUndgrFlr',
            'res_int_floor': 'ResIntFlr',
            'res_undergr_wall': 'ResUndgrWall',
            'res_cathedral_ceiling': 'ResCathedralCeiling',
            'res_attic_roof': 'ResAtticRoof',
            'res_other_floor': 'ResOtherFlr'
        }

        if surface_subtype and surface_subtype in subtype_map:
            return subtype_map[surface_subtype]

        # Fallback: generic tags based on surface_type
        if surface_type == 'wall':
            return 'ExtWall'
        elif surface_type == 'roof':
            return 'Roof'
        elif surface_type == 'floor':
            return 'Floor'
        else:
            return 'Surf'  # Generic surface
