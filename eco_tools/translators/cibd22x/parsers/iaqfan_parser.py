"""
IAQFan Parser - Simple Catalog Parser (HVAC Component)
======================================================

PURPOSE: Extracts Indoor Air Quality fan catalog definitions from CIBD22X XML.
IAQ fans provide ventilation (exhaust, supply, balanced/ERV).

PATTERN: Simple Catalog Parser - See material_parser.py for pattern details.

KEY OPERATIONS: Parse airflow (CFM), power (W/CFM), ventilation recovery efficiency.
"""

from typing import List, Optional, Dict, Any
import xml.etree.ElementTree as ET
import logging

from eco_tools.core.internal_repr import IAQFan
from eco_tools.core.id_registry import IDRegistry
from .base_parser import BaseParser

# Get module logger
logger = logging.getLogger('eco_tools.parsers')


class IAQFanParser(BaseParser):
    """Parser for CIBD22X IAQ fan system elements"""

    # CIBD22X IAQ fan catalog tags
    IAQ_FAN_CATALOG_TAGS = [
        'ResIAQFan'  # Residential IAQ fan systems
    ]

    def __init__(self, id_registry: IDRegistry):
        """
        Initialize the IAQ fan parser.

        Args:
            id_registry: ID registry for generating unique IAQ fan IDs
        """
        super().__init__()
        self.id_registry = id_registry

    def parse_iaq_fans(self, root: ET.Element) -> List[IAQFan]:
        """
        Parse all IAQ fan systems from CIBD22X catalog.

        IAQ fans provide ventilation for indoor air quality. In CIBD22X,
        ResIAQFan elements define fans with airflow rates, power consumption,
        and ventilation control properties.

        Args:
            root: Root XML element

        Returns:
            List of IAQFan objects
        """
        iaq_fans = []

        # Use namespace-aware iteration
        for fan_elem in root.iter():
            if self._local_tag(fan_elem.tag) == 'ResIAQFan':
                iaq_fan = self._parse_single_iaq_fan(fan_elem)
                if iaq_fan:
                    iaq_fans.append(iaq_fan)
                else:
                    name = self._get_name(fan_elem) or "unnamed"
                    logger.warning(f"Failed to parse ResIAQFan '{name}'")

        logger.info(f"Parsed {len(iaq_fans)} IAQ fans")
        return iaq_fans

    def _parse_single_iaq_fan(self, fan_elem: ET.Element) -> Optional[IAQFan]:
        """
        Parse a single IAQ fan element (ResIAQFan).

        Args:
            fan_elem: ResIAQFan XML element

        Returns:
            IAQFan object (always returns, uses default name if needed)
        """
        # Get name (default to "IAQ Fan" if not found)
        name = self._get_name(fan_elem)
        if not name:
            name = "IAQ Fan"

        # Generate IAQ fan ID
        fan_id = self.id_registry.generate_id('IAQ', name, '', 'CIBD22X')

        # Extract fan type (CBECC uses IAQFanType: Exhaust, Supply, Balanced)
        fan_type = self._extract_fan_type(fan_elem)

        # Extract airflow (CBECC uses IAQCFM)
        airflow_cfm = self._extract_airflow(fan_elem)

        # Extract power (CBECC uses WperCFMIAQ - watts per CFM, not total watts)
        power_w = self._extract_power(fan_elem)

        # Build annotation with all available properties FOR ROUND-TRIP FIDELITY
        annotation = self._build_annotation(fan_elem)

        iaq_fan = IAQFan(
            id=fan_id,
            name=name,
            fan_type=fan_type,
            airflow_cfm=airflow_cfm,
            power_w=power_w,
            annotation=annotation
        )

        return iaq_fan

    def _extract_fan_type(self, fan_elem: ET.Element) -> str:
        """
        Extract IAQ fan type from element.

        Tries multiple property names in priority order:
        1. IAQFanType (CBECC standard)
        2. FanType
        3. Type

        Args:
            fan_elem: ResIAQFan XML element

        Returns:
            Fan type string (defaults to 'Unknown' if not found)
        """
        fan_type = self.get_property(fan_elem, 'IAQFanType')
        if not fan_type:
            fan_type = self.get_property(fan_elem, 'FanType')
        if not fan_type:
            fan_type = self.get_property(fan_elem, 'Type')
        if not fan_type:
            fan_type = 'Unknown'

        return fan_type

    def _extract_airflow(self, fan_elem: ET.Element) -> Optional[float]:
        """
        Extract airflow rate from element.

        Tries multiple property names in priority order:
        1. IAQCFM (CBECC standard)
        2. FlowRate
        3. Airflow

        Args:
            fan_elem: ResIAQFan XML element

        Returns:
            Airflow in CFM or None if not found
        """
        airflow_cfm = self._to_float(self.get_property(fan_elem, 'IAQCFM'))
        if not airflow_cfm:
            airflow_cfm = self._to_float(self.get_property(fan_elem, 'FlowRate'))
        if not airflow_cfm:
            airflow_cfm = self._to_float(self.get_property(fan_elem, 'Airflow'))

        return airflow_cfm

    def _extract_power(self, fan_elem: ET.Element) -> Optional[float]:
        """
        Extract power consumption from element.

        Tries multiple property names in priority order:
        1. WperCFMIAQ (CBECC standard - watts per CFM, not total watts)
        2. FanPwr
        3. Power

        Args:
            fan_elem: ResIAQFan XML element

        Returns:
            Power in watts or None if not found
        """
        power_w = self._to_float(self.get_property(fan_elem, 'WperCFMIAQ'))
        if not power_w:
            power_w = self._to_float(self.get_property(fan_elem, 'FanPwr'))
        if not power_w:
            power_w = self._to_float(self.get_property(fan_elem, 'Power'))

        return power_w

    def _build_annotation(self, fan_elem: ET.Element) -> Dict[str, Any]:
        """
        Build annotation dictionary with all CIBD22X-specific properties.

        Stores original string values for exact round-trip export.
        CRITICAL: CBECC needs these exact properties.

        Args:
            fan_elem: ResIAQFan XML element

        Returns:
            Annotation dictionary with all available properties
        """
        annotation = {'xml_tag': 'ResIAQFan'}

        # Store original string values for exact round-trip
        # CRITICAL: CBECC needs these exact properties
        iaqcfm = self.get_property(fan_elem, 'IAQCFM')
        if iaqcfm:
            annotation['IAQCFM'] = iaqcfm

        wper_cfm = self.get_property(fan_elem, 'WperCFMIAQ')
        if wper_cfm:
            annotation['WperCFMIAQ'] = wper_cfm

        iaq_fan_type = self.get_property(fan_elem, 'IAQFanType')
        if iaq_fan_type:
            annotation['IAQFanType'] = iaq_fan_type

        includes_recov = self.get_property(fan_elem, 'IncludesRecov')
        if includes_recov is not None:
            annotation['IncludesRecov'] = includes_recov

        # Capture additional optional properties
        additional_props = [
            'FanCtrl', 'FanCtrlMethod', 'VentSysType', 'FanLoc',
            'DuctLoc', 'DuctInsul', 'DuctSurfArea', 'VentPreHtSrc',
            'VentPreCoolSrc', 'RecoveryEff'
        ]

        for prop in additional_props:
            value = self.get_property(fan_elem, prop)
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
