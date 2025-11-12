"""
DistributionSystem Parser - Simple Catalog Parser (HVAC Component)
==================================================================

PURPOSE: Extracts HVAC distribution system catalog definitions from CIBD22X XML.
Distribution systems handle air/fluid delivery (ducts, hydronic loops, ductless).

PATTERN: Simple Catalog Parser - See material_parser.py for pattern details.

KEY OPERATIONS: Parse distribution type, duct location/insulation/leakage, hydronic properties.
- Unit conversion for R-values (h·ft²·°F/Btu to m²·K/W)
- HVAC system references
"""

from typing import List, Optional
import xml.etree.ElementTree as ET
import logging

from eco_tools.core.internal_repr import DistributionSystem
from eco_tools.core.id_registry import IDRegistry
from .base_parser import BaseParser

# Get module logger
logger = logging.getLogger('eco_tools.parsers')


class DistributionSystemParser(BaseParser):
    """Parser for CIBD22X distribution system elements"""

    DISTRIBUTION_SYSTEM_CATALOG_TAGS = [
        'ResDistSys'  # Residential distribution systems
    ]

    def __init__(self, id_registry: IDRegistry):
        super().__init__()
        self.id_registry = id_registry

    def parse_distribution_systems(self, root: ET.Element) -> List[DistributionSystem]:
        """Parse all distribution systems from CIBD22X catalog."""
        distribution_systems = []

        # Use namespace-aware iteration
        for dist_elem in root.iter():
            if self._local_tag(dist_elem.tag) == 'ResDistSys':
                dist_sys = self._parse_single_distribution_system(dist_elem)
                if dist_sys:
                    distribution_systems.append(dist_sys)
                else:
                    name = self._get_name(dist_elem) or "unnamed"
                    logger.warning(f"Failed to parse ResDistSys '{name}'")

        logger.info(f"Parsed {len(distribution_systems)} distribution systems")
        return distribution_systems

    def _parse_single_distribution_system(self, dist_elem: ET.Element) -> Optional[DistributionSystem]:
        """Parse a single distribution system element."""
        name = self._get_name(dist_elem) or "Distribution System"
        dist_id = self.id_registry.generate_id('DIST', name, '', 'CIBD22X')

        dist_type = self.get_property(dist_elem, 'Type') or 'ducted'
        duct_location = self.get_property(dist_elem, 'DuctLoc')

        # Convert R-value from IP to SI (h·ft²·°F/Btu to m²·K/W: ×0.1761)
        duct_r_ip = self._to_float(self.get_property(dist_elem, 'DuctInsRVal'))
        duct_insulation_r_value_SI = (duct_r_ip * 0.1761) if duct_r_ip else None

        duct_leakage_pct = self._to_float(self.get_property(dist_elem, 'DuctLkg'))
        hvac_system_ref = self.get_property(dist_elem, 'HVACSysRef')

        annotation = {}
        duct_surface_area = self._to_float(self.get_property(dist_elem, 'DuctSurfArea'))
        if duct_surface_area:
            annotation['duct_surface_area_ft2'] = duct_surface_area

        return DistributionSystem(
            id=dist_id,
            name=name,
            distribution_type=dist_type,
            duct_location=duct_location,
            duct_insulation_r_value_SI=duct_insulation_r_value_SI,
            duct_leakage_pct=duct_leakage_pct,
            hvac_system_ref=hvac_system_ref,
            annotation=annotation
        )

    def _get_name(self, element: ET.Element) -> Optional[str]:
        name_elem = element.find('.//n')
        if name_elem is not None and name_elem.text:
            return name_elem.text.strip()
        name_elem = element.find('.//Name')
        if name_elem is not None and name_elem.text:
            return name_elem.text.strip()
        name = element.get('id')
        return name if name else None
