"""
ZoneGroup Parser - Hierarchical Parser (Top of Spatial Hierarchy)
=================================================================

PURPOSE: Extracts zone group definitions from CIBD22X XML.
Zone groups are the TOP of spatial hierarchy: ZoneGroups → Zones → Surfaces → Openings.

PATTERN: Hierarchical Parser - See zone_parser.py for detailed documentation.

KEY OPERATIONS:
- Parse zone group properties (type, multiplier)
- NO dependencies on other parsers (top of hierarchy)
- Zones will reference these zone groups as parents

SPATIAL HIERARCHY:
ZoneGroups (this parser) → Zones → Surfaces → Openings
Parse order: Must parse ZoneGroups BEFORE Zones.
"""

from typing import List, Optional
import xml.etree.ElementTree as ET
import logging

from eco_tools.core.internal_repr import ZoneGroup
from eco_tools.core.id_registry import IDRegistry
from .base_parser import BaseParser

# Get module logger
logger = logging.getLogger('eco_tools.parsers')


class ZoneGroupParser(BaseParser):
    """Parser for CIBD22X zone group elements"""

    # CIBD22X zone group catalog tags
    ZONE_GROUP_CATALOG_TAGS = [
        'ResZnGrp'  # Residential zone groups
    ]

    def __init__(self, id_registry: IDRegistry):
        """
        Initialize the zone group parser.

        Args:
            id_registry: ID registry for generating unique zone group IDs
        """
        super().__init__()
        self.id_registry = id_registry

    def parse_zone_groups(self, root: ET.Element) -> List[ZoneGroup]:
        """
        Parse all zone groups from CIBD22X catalog.

        Zone groups represent collections of zones (typically by floor).
        In CIBD22X, ResZnGrp elements define groups that can have multipliers
        for repeated configurations.

        Args:
            root: Root XML element

        Returns:
            List of ZoneGroup objects
        """
        zone_groups = []

        # Use namespace-aware iteration
        for zg_elem in root.iter():
            if self._local_tag(zg_elem.tag) in ['ResZnGrp', 'ComZnGrp']:
                zone_group = self._parse_single_zone_group(zg_elem)
                if zone_group:
                    zone_groups.append(zone_group)
                else:
                    name = self._get_name(zg_elem) or "unnamed"
                    logger.warning(f"Failed to parse ZoneGroup '{name}': missing required name")

        logger.info(f"Parsed {len(zone_groups)} zone groups")
        return zone_groups

    def _parse_single_zone_group(self, zg_elem: ET.Element) -> Optional[ZoneGroup]:
        """
        Parse a single zone group element (ResZnGrp).

        Args:
            zg_elem: ResZnGrp XML element

        Returns:
            ZoneGroup object or None if name is missing
        """
        # Get name (required)
        name = self._get_name(zg_elem)
        if not name:
            return None

        # Generate zone group ID
        zg_id = self.id_registry.generate_id('ZG', name, '', 'CIBD22X')

        # Build annotation (match current adapter behavior)
        annotation = {'xml_tag': 'ResZnGrp'}

        # Create ZoneGroup object
        zone_group = ZoneGroup(
            id=zg_id,
            name=name,
            group_type='floor',  # Default to floor for ResZnGrp
            annotation=annotation
        )

        return zone_group

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
