"""
LightingSystem Parser - Simple Catalog Parser (Cross-Catalog Reference)
=======================================================================

PURPOSE: Extracts lighting system catalog definitions from CIBD22X XML.

PATTERN: Simple Catalog Parser - See material_parser.py for pattern details.

KEY OPERATIONS:
- Parse power density (W/ft² → W/m²) or luminaire references
- POST-PROCESSING: Total power calculated from luminaire refs (see cibd22x_importer.py)

CROSS-REFERENCE: LightingSystems reference Luminaires by name.
Post-processing calculates: total_power = luminaire.power_w × count
- Luminaire references (links to luminaire catalog)
- Daylighting properties
"""

from typing import List, Optional, Dict, Any
import xml.etree.ElementTree as ET
import logging

from eco_tools.core.internal_repr import LightingSystem
from eco_tools.core.id_registry import IDRegistry
from .base_parser import BaseParser

# Get module logger
logger = logging.getLogger('eco_tools.parsers')


class LightingSystemParser(BaseParser):
    """Parser for CIBD22X lighting system elements"""

    # CIBD22X lighting system catalog tags
    LIGHTING_SYSTEM_CATALOG_TAGS = [
        'IntLtgSys'  # Interior lighting systems
    ]

    def __init__(self, id_registry: IDRegistry):
        """
        Initialize the lighting system parser.

        Args:
            id_registry: ID registry for generating unique lighting system IDs
        """
        super().__init__()
        self.id_registry = id_registry

    def parse_lighting_systems(self, root: ET.Element) -> List[LightingSystem]:
        """
        Parse all interior lighting systems from CIBD22X catalog.

        Lighting systems define interior lighting for spaces with power density
        or total power, control types, and optional luminaire references.
        In CIBD22X, IntLtgSys elements define lighting that can reference
        luminaire catalogs or specify power directly.

        Args:
            root: Root XML element

        Returns:
            List of LightingSystem objects
        """
        lighting_systems = []

        for ltg_elem in root.findall('.//IntLtgSys'):
            lighting_system = self._parse_single_lighting_system(ltg_elem)
            if lighting_system:
                lighting_systems.append(lighting_system)
            else:
                name = self._get_name(ltg_elem) or "unnamed"
                logger.warning(f"Failed to parse IntLtgSys '{name}'")

        logger.info(f"Parsed {len(lighting_systems)} lighting systems")
        return lighting_systems

    def _parse_single_lighting_system(self, ltg_elem: ET.Element) -> Optional[LightingSystem]:
        """
        Parse a single lighting system element (IntLtgSys).

        Args:
            ltg_elem: IntLtgSys XML element

        Returns:
            LightingSystem object (always returns, uses default name if needed)
        """
        # Get name (default to "Lighting System" if not found)
        name = self._get_name(ltg_elem)
        if not name:
            name = "Lighting System"

        # Generate lighting system ID
        ltg_id = self.id_registry.generate_id('LTG', name, '', 'CIBD22X')

        # Extract space reference
        space_ref = self.get_property(ltg_elem, 'SpcRef')

        # Extract power density (W/ft² to W/m²: multiply by 10.764)
        power_density_w_m2 = self._extract_power_density(ltg_elem)

        # Extract total power
        total_power_w = self._to_float(self.get_property(ltg_elem, 'TotPwr'))

        # Extract control type
        control_type = self.get_property(ltg_elem, 'CtrlType')

        # Extract schedule reference
        schedule_ref = self.get_property(ltg_elem, 'SchRef')

        # Parse luminaire references (CBECC-Com SDDXML)
        luminaire_refs = self._extract_luminaire_refs(ltg_elem)

        # Build annotation with CBECC-specific properties
        annotation = self._build_annotation(ltg_elem)

        lighting_system = LightingSystem(
            id=ltg_id,
            name=name,
            system_type='interior',
            space_ref=space_ref,
            power_density_w_m2=power_density_w_m2,
            total_power_w=total_power_w,
            control_type=control_type,
            luminaire_refs=luminaire_refs,
            schedule_ref=schedule_ref,
            annotation=annotation
        )

        return lighting_system

    def _extract_power_density(self, ltg_elem: ET.Element) -> Optional[float]:
        """
        Extract power density and convert from IP to SI units.

        CIBD22X stores power density in W/ft² (IP units).
        Converts to W/m² (SI units) by multiplying by 10.764.

        Args:
            ltg_elem: IntLtgSys XML element

        Returns:
            Power density in W/m² or None if not found
        """
        power_density_ip = self._to_float(self.get_property(ltg_elem, 'PwrDens'))
        if power_density_ip:
            return power_density_ip * 10.764
        return None

    def _extract_luminaire_refs(self, ltg_elem: ET.Element) -> List[str]:
        """
        Extract luminaire references from lighting system.

        CBECC-Com SDDXML format uses LumRef child elements to reference
        luminaire catalog entries.

        Args:
            ltg_elem: IntLtgSys XML element

        Returns:
            List of luminaire reference strings
        """
        luminaire_refs = []
        for lum_ref_elem in ltg_elem.findall('.//LumRef'):
            if lum_ref_elem.text:
                luminaire_refs.append(lum_ref_elem.text.strip())
        return luminaire_refs

    def _build_annotation(self, ltg_elem: ET.Element) -> Dict[str, Any]:
        """
        Build annotation dictionary with CBECC-specific properties.

        Captures optional properties for round-trip export:
        - Regulated lighting power (RegLtgPwr)
        - Luminaire count (LumCnt)
        - Daylighting area type (DaylitAreaType)

        Args:
            ltg_elem: IntLtgSys XML element

        Returns:
            Annotation dictionary with available properties
        """
        annotation = {}

        # Regulated lighting power (CBECC-Com specific)
        reg_ltg_pwr = self._to_float(self.get_property(ltg_elem, 'RegLtgPwr'))
        if reg_ltg_pwr:
            annotation['regulated_power_w'] = reg_ltg_pwr

        # Luminaire count (CBECC-Com specific)
        lum_count = self._to_int(self.get_property(ltg_elem, 'LumCnt'))
        if lum_count:
            annotation['luminaire_count'] = lum_count

        # Daylighting area type (CBECC-Com specific)
        daylit_area_type = self.get_property(ltg_elem, 'DaylitAreaType')
        if daylit_area_type:
            annotation['daylighting_area_type'] = daylit_area_type

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
