"""
Luminaire Parser - Simple Catalog Parser
========================================

PURPOSE:
Extracts luminaire (light fixture) catalog definitions from CIBD22X XML.
Luminaires define fixture types that are referenced by lighting systems.

PATTERN: Simple Catalog Parser (no dependencies on other parsers)
See material_parser.py for detailed documentation of this pattern.

KEY OPERATIONS:
- Parse power per luminaire (watts)
- Extract luminaire type and efficiency
- Store catalog entries for reference by LightingSystemParser

CROSS-REFERENCE NOTE:
LightingSystems reference Luminaires by name and specify counts.
Post-processing calculates: total_power = luminaire.power_w × count
See cibd22x_importer.py _calculate_lighting_power() for details.
"""

from typing import List, Optional
import xml.etree.ElementTree as ET
import logging

from eco_tools.core.internal_repr import Luminaire
from eco_tools.core.id_registry import IDRegistry
from .base_parser import BaseParser

# Get module logger
logger = logging.getLogger('eco_tools.parsers')


class LuminaireParser(BaseParser):
    """Parser for CIBD22X luminaire elements"""

    # CIBD22X luminaire catalog tags
    LUMINAIRE_CATALOG_TAGS = [
        'Lum'  # Luminaire definitions
    ]

    def __init__(self, id_registry: IDRegistry):
        """
        Initialize the luminaire parser.

        Args:
            id_registry: ID registry for generating unique luminaire IDs
        """
        super().__init__()
        self.id_registry = id_registry

    def parse_luminaires(self, root: ET.Element) -> List[Luminaire]:
        """
        Parse all luminaires from CIBD22X catalog.

        Luminaires define individual light fixtures with power consumption,
        count, and efficiency. In CIBD22X, Lum elements define fixtures that
        are referenced by lighting systems.

        Args:
            root: Root XML element

        Returns:
            List of Luminaire objects
        """
        luminaires = []

        for lum_elem in root.findall('.//Lum'):
            luminaire = self._parse_single_luminaire(lum_elem)
            if luminaire:
                luminaires.append(luminaire)
            else:
                # Luminaire parsing failed - likely missing required properties
                name = self._get_name(lum_elem) or "unnamed"
                logger.warning(f"Failed to parse Lum luminaire '{name}'")

        logger.info(f"Parsed {len(luminaires)} luminaires")
        return luminaires

    def _parse_single_luminaire(self, lum_elem: ET.Element) -> Optional[Luminaire]:
        """
        Parse a single luminaire element (Lum).

        Args:
            lum_elem: Lum XML element

        Returns:
            Luminaire object (always returns, uses default name if needed)
        """
        # Get name (default to "Luminaire" if not found)
        name = self._get_name(lum_elem)
        if not name:
            name = "Luminaire"

        # Generate luminaire ID
        lum_id = self.id_registry.generate_id('LUM', name, '', 'CIBD22X')

        # Extract luminaire type
        lum_type = self.get_property(lum_elem, 'Type')
        if not lum_type:
            lum_type = 'unknown'

        # Extract power per luminaire
        power_w = self._to_float(self.get_property(lum_elem, 'Pwr'))

        # Extract count of luminaires
        count = self._to_int(self.get_property(lum_elem, 'Cnt'))

        # Extract efficiency
        efficiency = self._to_float(self.get_property(lum_elem, 'Eff'))

        # Extract lighting system reference
        ltg_sys_ref = self.get_property(lum_elem, 'LtgSysRef')

        # Build annotation (currently empty, but ready for future properties)
        annotation = {}

        luminaire = Luminaire(
            id=lum_id,
            name=name,
            luminaire_type=lum_type,
            power_w=power_w,
            count=count,
            efficiency=efficiency,
            lighting_system_ref=ltg_sys_ref,
            annotation=annotation
        )

        return luminaire

    def _get_name(self, element: ET.Element) -> Optional[str]:
        """
        Extract name from element (CIBD22X format).

        Tries: <n>, <Name>, id attribute

        Args:
            element: XML element

        Returns:
            Element name or None
        """
        # Try <n> child (CIBD22X format)
        name_elem = element.find('.//n')
        if name_elem is not None and name_elem.text:
            return name_elem.text.strip()

        # Try <Name> child
        name_elem = element.find('.//Name')
        if name_elem is not None and name_elem.text:
            return name_elem.text.strip()

        # Try id attribute
        name = element.get('id')
        if name:
            return name

        return None
