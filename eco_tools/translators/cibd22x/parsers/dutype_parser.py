"""
DUType Parser - Simple Catalog Parser (Residential)
===================================================

PURPOSE: Extracts dwelling unit type catalog definitions from CIBD22X XML.
DU types define characteristics of residential unit types (studio, 1BR, 2BR, etc.).

PATTERN: Simple Catalog Parser - See material_parser.py for pattern details.

KEY OPERATIONS: Parse unit area, bedroom count, appliance fuels, HVAC system references.
- IAQ system references
- DHW system references
"""

from typing import List, Dict, Any, Optional
import xml.etree.ElementTree as ET
import logging

from eco_tools.core.id_registry import IDRegistry
from .base_parser import BaseParser

# Get module logger
logger = logging.getLogger('eco_tools.parsers')


class DUTypeParser(BaseParser):
    """Parser for CIBD22X dwelling unit type elements"""

    DU_TYPE_CATALOG_TAGS = [
        'DwellUnitType'  # Dwelling unit types
    ]

    def __init__(self, id_registry: IDRegistry):
        super().__init__()
        self.id_registry = id_registry

    def parse_du_types(self, root: ET.Element) -> List[Dict]:
        """
        Parse all dwelling unit types from CIBD22X catalog.

        DwellUnitType defines characteristics of a unit type that can be
        referenced by multiple DwellUnit instances within ResZn zones.

        Args:
            root: Root XML element

        Returns:
            List of dwelling unit type dictionaries
        """
        types = []

        # Use namespace-aware iteration (same pattern as material_parser)
        for du_elem in root.iter():
            if self._local_tag(du_elem.tag) == 'DwellUnitType':
                du_type = self._parse_single_du_type(du_elem)
                if du_type:
                    types.append(du_type)
                else:
                    name = self._get_name(du_elem) or "unnamed"
                    logger.warning(f"Failed to parse DwellUnitType '{name}'")

        logger.info(f"Parsed {len(types)} dwelling unit types")
        return types

    def _parse_single_du_type(self, du_elem: ET.Element) -> Optional[Dict[str, Any]]:
        """Parse a single dwelling unit type element."""
        name = self._get_name(du_elem)
        if not name:
            return None

        # Capture all DwellUnitType properties for complete round-trip
        return {
            'id': self.id_registry.generate_id('DU', name, '', 'CIBD22X'),
            'name': name,
            # Geometry
            'cond_floor_area': self._to_float(self.get_property(du_elem, 'CondFlrArea')),  # ft² (IP units)
            'num_bedrooms': self._to_int(self.get_property(du_elem, 'NumBedrooms')),
            # Appliances
            'dryer_fuel': self.get_property(du_elem, 'DryerFuel'),
            'cook_fuel': self.get_property(du_elem, 'CookFuel'),
            # HVAC system references
            'hvac_sys_type': self.get_property(du_elem, 'HVACSysType'),
            'hvac_ht_pump_ref': self.get_property(du_elem, 'HVACHtPumpRef'),
            'hvac_fan_ref': self.get_property(du_elem, 'HVACFanRef'),
            'hvac_dist_ref': self.get_property(du_elem, 'HVACDistRef'),
            # IAQ system references
            'iaq_option': self.get_property(du_elem, 'IAQOption'),
            'iaq_fan_ref': self.get_property(du_elem, 'IAQFanRef'),
            'iaq_fan_cnt': self._to_int(self.get_property(du_elem, 'IAQFanCnt')),
            # DHW system reference
            'dhw_sys_ref': self.get_property(du_elem, 'DHWSysRef'),
        }

    def _get_name(self, element: ET.Element) -> Optional[str]:
        """Extract name from element using namespace-aware get_property."""
        # Try 'n' tag first (short form in CIBD format)
        name = self.get_property(element, 'n')
        if name:
            return name
        # Try 'Name' tag
        name = self.get_property(element, 'Name')
        if name:
            return name
        # Try 'id' attribute
        name = element.get('id')
        return name if name else None
