"""
Zone Exporter - Complex Hierarchical Exporter (Top of Spatial Hierarchy)
========================================================================

PURPOSE:
Serializes Zone and ZoneGroup objects to CIBD22X XML format.
Zones are the TOP of spatial hierarchy: ZoneGroups → Zones → Surfaces → Openings.

EXPORT STRATEGY:
1. Export zone groups first (ResZnGrp) as containers
2. Export zones nested within appropriate zone groups
3. Determine XML tag from annotation ('xml_tag': ResZn, ComZn, etc.)
4. Convert SI units back to Imperial (area, volume, heights)
5. Export extensive zone properties (space function, conditioning, multiplier)
6. Delegate to SurfaceExporter for nested surfaces (which delegates to OpeningExporter)
7. Restore format-specific properties from annotations

HIERARCHICAL EXPORT:
This is a COMPOSITE exporter that:
- Exports zone groups as top-level elements
- Exports zones as children of zone groups
- Delegates surface export to SurfaceExporter
- Which delegates opening export to OpeningExporter

UNIT CONVERSIONS (SI → Imperial):
- Area: m² → ft² (÷ 0.092903)
- Volume: m³ → ft³ (× 35.3147)
- Heights: m → ft (÷ 0.3048)

ANNOTATION RESTORATION:
Zones have the most extensive annotations:
- Zone type, conditioning type
- Heights (ceiling, floor, floor-to-floor, Z coordinates)
- Dwelling unit information
- Space function, ventilation space function
- HVAC/DHW system references
- IAQ configuration
- Daylighting controls

COMPOSITION:
Uses SurfaceExporter → OpeningExporter for complete geometry export.

PATTERN: Complex Hierarchical Exporter (top of hierarchy)
"""

from typing import List, Optional, Dict
import xml.etree.ElementTree as ET
import logging

from eco_tools.core.internal_repr import Zone, ZoneGroup, Surface, Opening
from .base_exporter import BaseExporter
from .surface_exporter import SurfaceExporter
from .format_utils import Format, get_name_tag, get_format_for_context

# Get module logger
logger = logging.getLogger('eco_tools.exporters')


class ZoneExporter(BaseExporter):
    """Exporter for CIBD22X zone and zone group elements"""

    def __init__(self):
        super().__init__()
        self.surface_exporter = SurfaceExporter()

    def export_zones_with_geometry(
        self,
        parent: ET.Element,
        zone_groups: List[ZoneGroup],
        zones: List[Zone],
        surfaces: List[Surface],
        openings: List[Opening]
    ) -> None:
        """
        Export complete spatial hierarchy: zone groups → zones → surfaces → openings.

        This is the main entry point for hierarchical geometry export.

        Args:
            parent: Parent XML element (typically <Building>)
            zone_groups: List of zone groups to export
            zones: List of zones to export
            surfaces: List of surfaces to export
            openings: List of openings to export
        """
        # Build map of zones by parent zone group
        zone_by_zg: Dict[Optional[str], List[Zone]] = {}
        for zone in zones:
            parent_zg_id = self.get_annotation(zone.annotation, 'parent_zone_group_id')
            if parent_zg_id not in zone_by_zg:
                zone_by_zg[parent_zg_id] = []
            zone_by_zg[parent_zg_id].append(zone)

        exported_zone_groups = 0
        exported_zones = 0

        # Export zone groups with their zones
        for zone_group in zone_groups:
            zg_elem = self._export_zone_group(parent, zone_group)
            if zg_elem is not None:
                exported_zone_groups += 1

                # Export zones belonging to this zone group
                zg_zones = zone_by_zg.get(zone_group.id, [])
                for zone in zg_zones:
                    zone_elem = self._export_zone(zg_elem, zone, surfaces, openings)
                    if zone_elem is not None:
                        exported_zones += 1

        # Export zones without zone group (orphaned zones)
        orphaned_zones = zone_by_zg.get(None, [])
        for zone in orphaned_zones:
            zone_elem = self._export_zone(parent, zone, surfaces, openings)
            if zone_elem is not None:
                exported_zones += 1

        logger.info(f"Exported {exported_zone_groups} zone groups and {exported_zones} zones")

    def _export_zone_group(self, parent: ET.Element, zone_group: ZoneGroup) -> Optional[ET.Element]:
        """
        Export a zone group element.

        Args:
            parent: Parent XML element
            zone_group: ZoneGroup object to export

        Returns:
            Created zone group XML element or None if export failed
        """
        if not zone_group.name:
            logger.warning(f"Skipping zone group with missing name (id: {zone_group.id})")
            return None

        # Determine format based on parent context
        # Zone groups nested in Bldg use CIBD22 format, root-level use CIBD22X
        parent_tag = parent.tag.split('}')[-1] if '}' in parent.tag else parent.tag
        format_type = get_format_for_context(parent_tag)

        # Determine XML tag from annotation
        xml_tag = self.get_annotation(zone_group.annotation, 'xml_tag', 'ResZnGrp')

        # Create zone group element
        zg_elem = self.create_element(parent, xml_tag)

        # Add name (required) - use format-aware name tag
        name_tag = get_name_tag(format_type)
        self.add_text_element(zg_elem, name_tag, zone_group.name)

        # Group type: SKIP - ResZnGrp doesn't support Type property in CBECC
        # The 'group_type' was captured during import but shouldn't be exported

        return zg_elem

    def _export_zone(
        self,
        parent: ET.Element,
        zone: Zone,
        surfaces: List[Surface],
        openings: List[Opening]
    ) -> Optional[ET.Element]:
        """
        Export a zone element with nested surfaces and openings.

        Args:
            parent: Parent XML element (zone group or building)
            zone: Zone object to export
            surfaces: All surfaces (will filter to this zone's surfaces)
            openings: All openings (passed to surface exporter)

        Returns:
            Created zone XML element or None if export failed
        """
        if not zone.name:
            logger.warning(f"Skipping zone with missing name (id: {zone.id})")
            return None

        # Determine format based on parent context
        # Zones nested in ResZnGrp (which is in Bldg) use CIBD22 format
        parent_tag = parent.tag.split('}')[-1] if '}' in parent.tag else parent.tag
        # ResZnGrp is inside Bldg, so zones should use CIBD22 format
        format_type = Format.CIBD22 if parent_tag in ['ResZnGrp', 'ComZnGrp', 'Bldg', 'Story'] else Format.CIBD22X

        # Determine XML tag from annotation
        xml_tag = self.get_annotation(zone.annotation, 'xml_tag')
        if not xml_tag:
            # Fallback: determine from zone_type or building_type
            xml_tag = self._determine_tag_from_zone_type(zone.zone_type, zone.building_type)

        # Create zone element
        zn_elem = self.create_element(parent, xml_tag)

        # Add name (required) - use format-aware name tag
        name_tag = get_name_tag(format_type)
        self.add_text_element(zn_elem, name_tag, zone.name)

        # Floor area: m² → ft²
        # Property name depends on zone type: ResOtherZn uses 'Area', ResZn uses 'FloorArea'
        # CRITICAL: Only export FloorArea if it was explicitly present in original XML
        # Otherwise CBECC calculates it from surfaces and can detect mismatches
        if zone.floor_area_m2 is not None:
            # Check if FloorArea/Area was explicit in original file
            had_explicit = zone.annotation.get('had_explicit_floor_area', True)  # Default True for safety

            if had_explicit:
                # Use original value if available for perfect round-trip
                if 'original_floor_area_ft' in zone.annotation:
                    self.add_text_element(zn_elem, 'FloorArea', zone.annotation['original_floor_area_ft'])
                elif 'original_area_ft' in zone.annotation:
                    self.add_text_element(zn_elem, 'Area', zone.annotation['original_area_ft'])
                else:
                    # Fallback: convert from m²
                    area_ft2 = self.si_to_ip_area(zone.floor_area_m2)
                    area_tag = 'Area' if 'OtherZn' in xml_tag else 'FloorArea'
                    self.add_numeric_element(zn_elem, area_tag, area_ft2, precision=2)
            # else: Don't export - let CBECC calculate from surfaces

        # Volume: m³ → ft³
        if zone.volume_m3 is not None:
            vol_ft3 = self.si_to_ip_volume(zone.volume_m3)
            self.add_numeric_element(zn_elem, 'Vol', vol_ft3, precision=1)

        # Multiplier (for repeated zones)
        if zone.multiplier and zone.multiplier > 1:
            self.add_text_element(zn_elem, 'ZnMult', str(zone.multiplier))

        # Space function (Title 24 space type)
        if zone.space_function:
            self.add_text_element(zn_elem, 'SpcFunc', zone.space_function)

        # Restore heights from annotations
        if zone.annotation:
            self._restore_heights(zn_elem, zone.annotation)
            self._restore_conditioning(zn_elem, zone.annotation)
            self._restore_zone_type(zn_elem, zone.annotation)
            self._restore_dwelling_unit(zn_elem, zone.annotation)
            self._restore_system_references(zn_elem, zone.annotation)
            self._restore_iaq_configuration(zn_elem, zone.annotation)
            self._restore_daylighting(zn_elem, zone.annotation)

        # Export surfaces for this zone (with nested openings)
        # Pass format_type to surface exporter for format-aware property names
        zone_surfaces = [s for s in surfaces if s.parent_zone_id == zone.id]
        for surface in zone_surfaces:
            self.surface_exporter.export_surface(zn_elem, surface, openings, format_type)

        return zn_elem

    def _determine_tag_from_zone_type(self, zone_type: Optional[str], building_type: Optional[str]) -> str:
        """Determine XML tag from zone_type or building_type."""
        if zone_type:
            return zone_type
        elif building_type == 'Residential':
            return 'ResZn'
        elif building_type == 'Commercial':
            return 'ComZn'
        else:
            return 'ResZn'  # Default

    def _restore_heights(self, parent: ET.Element, annotation: Dict) -> None:
        """Restore height properties from annotations."""
        # Use original IP values for perfect round-trip
        ceiling_height_ft = self.get_annotation(annotation, 'original_ceiling_height_ft')
        if ceiling_height_ft:
            self.add_text_element(parent, 'CeilingHeight', ceiling_height_ft)

        floor_height_ft = self.get_annotation(annotation, 'original_floor_height_ft')
        if floor_height_ft:
            self.add_text_element(parent, 'FloorHeight', floor_height_ft)

        # FloorZ is NOT a valid CBECC property - skip it
        # CBECC uses 'Bottom' instead for floor elevation

        bottom_ft = self.get_annotation(annotation, 'original_bottom_ft')
        if bottom_ft:
            self.add_text_element(parent, 'Bottom', bottom_ft)

    def _restore_conditioning(self, parent: ET.Element, annotation: Dict) -> None:
        """Restore conditioning type from annotations."""
        condg_type = self.get_annotation(annotation, 'conditioning_type')
        if condg_type:
            self.add_text_element(parent, 'CondgType', condg_type)

    def _restore_zone_type(self, parent: ET.Element, annotation: Dict) -> None:
        """Restore zone type (Attic, Plenum, etc.) from annotations."""
        zone_type = self.get_annotation(annotation, 'zone_type')
        if zone_type:
            self.add_text_element(parent, 'Type', zone_type)

    def _restore_dwelling_unit(self, parent: ET.Element, annotation: Dict) -> None:
        """Restore dwelling unit information from annotations."""
        du_info = self.get_annotation(annotation, 'dwelling_unit')
        if du_info and isinstance(du_info, dict):
            du_elem = ET.SubElement(parent, 'DwellUnit')

            # Determine format based on parent context (DwellUnit is inside zone, which is inside Bldg)
            parent_tag = parent.tag.split('}')[-1] if '}' in parent.tag else parent.tag
            format_type = Format.CIBD22 if parent_tag in ['ResZn', 'ComZn'] else Format.CIBD22X
            name_tag = get_name_tag(format_type)

            du_name = du_info.get('name')
            if du_name:
                self.add_text_element(du_elem, name_tag, du_name)

            du_type_ref = du_info.get('dwelling_unit_type_ref')
            if du_type_ref:
                self.add_text_element(du_elem, 'DwellUnitTypeRef', du_type_ref)

            du_count = du_info.get('count')
            if du_count:
                self.add_text_element(du_elem, 'Count', str(du_count))

    def _restore_system_references(self, parent: ET.Element, annotation: Dict) -> None:
        """Restore HVAC and DHW system references from annotations."""
        oz_hvac_sys = self.get_annotation(annotation, 'oz_hvac_system')
        if oz_hvac_sys:
            self.add_text_element(parent, 'ozHVACSystem', oz_hvac_sys)

        oz_dhw_sys = self.get_annotation(annotation, 'oz_dhw_sys')
        if oz_dhw_sys:
            self.add_text_element(parent, 'ozDHWSys', oz_dhw_sys)

    def _restore_iaq_configuration(self, parent: ET.Element, annotation: Dict) -> None:
        """Restore IAQ/ventilation configuration from annotations."""
        iaq_config = self.get_annotation(annotation, 'iaq_config')
        if iaq_config and isinstance(iaq_config, dict):
            for key, value in iaq_config.items():
                if value:
                    self.add_text_element(parent, key, str(value))

    def _restore_daylighting(self, parent: ET.Element, annotation: Dict) -> None:
        """Restore daylighting control properties from annotations."""
        daylight = self.get_annotation(annotation, 'daylighting')
        if daylight and isinstance(daylight, dict):
            for key, value in daylight.items():
                if value:
                    self.add_text_element(parent, key, str(value))
