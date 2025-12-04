"""
Fan Parser - Simple Catalog Parser (HVAC Component)
===================================================

PURPOSE: Extracts fan system catalog definitions from CIBD22X XML.
Fans are HVAC components referenced by HVAC systems.

PATTERN: Simple Catalog Parser - See material_parser.py for pattern details.

KEY OPERATIONS: Parse airflow (CFM), power (W), efficiency, control method.
"""

from typing import List, Optional
import xml.etree.ElementTree as ET
import logging

from eco_tools.core.internal_repr import FanSystem
from eco_tools.core.id_registry import IDRegistry
from .base_parser import BaseParser

# Get module logger
logger = logging.getLogger('eco_tools.parsers')


class FanParser(BaseParser):
    """Parser for CIBD22X fan system elements"""

    # CIBD22X fan system catalog tags
    # NOTE: Includes both residential fan systems and generic Fan catalog elements
    FAN_CATALOG_TAGS = [
        'Fan',                 # Generic fan catalog elements (commercial/residential)
        'ResFanSys',           # Residential fan systems
        'ResCentralVentSys'    # Central ventilation systems
    ]

    def __init__(self, id_registry: IDRegistry):
        """
        Initialize the fan parser.

        Args:
            id_registry: ID registry for generating unique fan system IDs
        """
        super().__init__()
        self.id_registry = id_registry

    def parse_fan_systems(self, root: ET.Element) -> List[FanSystem]:
        """
        Parse all fan systems from CIBD22X catalog.

        IMPORTANT: Only parses catalog-level fan systems (ResFanSys, ResCentralVentSys),
        NOT embedded <Fan> elements within HVAC systems. Embedded fans are
        components of HVAC systems, not standalone catalog items.

        Args:
            root: Root XML element

        Returns:
            List of FanSystem objects
        """
        fan_systems = []

        # Use namespace-aware iteration
        for elem in root.iter():
            local_tag = self._local_tag(elem.tag)

            # Parse generic Fan catalog elements
            if local_tag == 'Fan':
                fan_system = self._parse_fan(elem)
                if fan_system:
                    fan_systems.append(fan_system)
                else:
                    name = self._get_name(elem) or "unnamed"
                    logger.warning(f"Failed to parse Fan '{name}'")

            # Parse residential fan systems
            elif local_tag == 'ResFanSys':
                fan_system = self._parse_res_fan_system(elem)
                if fan_system:
                    fan_systems.append(fan_system)
                else:
                    name = self._get_name(elem) or "unnamed"
                    logger.warning(f"Failed to parse ResFanSys '{name}'")

            # Parse central ventilation systems
            elif local_tag == 'ResCentralVentSys':
                fan_system = self._parse_central_vent_system(elem)
                if fan_system:
                    fan_systems.append(fan_system)
                else:
                    name = self._get_name(elem) or "unnamed"
                    logger.warning(f"Failed to parse ResCentralVentSys '{name}'")

        logger.info(f"Parsed {len(fan_systems)} fan systems")
        return fan_systems

    def _parse_fan(self, fan_elem: ET.Element) -> Optional[FanSystem]:
        """
        Parse a generic Fan catalog element.

        Args:
            fan_elem: Fan XML element

        Returns:
            FanSystem object
        """
        # Get name
        name = self._get_name(fan_elem)
        if not name:
            name = "Fan"

        # Generate fan ID
        fan_id = self.id_registry.generate_id('FAN', name, '', 'CIBD22X')

        # Modeling method
        modeling_method = self.get_property(fan_elem, 'ModelingMthd')

        # Airflow capacity (FlowCap in CFM)
        airflow_cfm = self._to_float(self.get_property(fan_elem, 'FlowCap'))

        # Flow efficiency
        flow_eff = self._to_float(self.get_property(fan_elem, 'FlowEff'))

        # Total static pressure
        total_static_press = self._to_float(self.get_property(fan_elem, 'TotStaticPress'))

        # Motor horsepower
        motor_hp = self._to_float(self.get_property(fan_elem, 'MtrHP'))

        # Motor efficiency
        motor_eff = self._to_float(self.get_property(fan_elem, 'MtrEff'))

        # Calculate power from motor HP if available
        power_w = None
        if motor_hp:
            # Convert HP to Watts: 1 HP = 745.7 W
            power_w = motor_hp * 745.7

        # Build annotation with additional properties
        annotation = {'xml_tag': 'Fan'}
        if modeling_method:
            annotation['ModelingMthd'] = modeling_method
        if flow_eff:
            annotation['FlowEff'] = flow_eff
        if total_static_press:
            annotation['TotStaticPress'] = total_static_press
        if motor_hp:
            annotation['MtrHP'] = motor_hp
        if motor_eff:
            annotation['MtrEff'] = motor_eff

        # Fan type (default to 'supply' if not specified)
        fan_type = self.get_property(fan_elem, 'Type') or 'supply'

        # Create FanSystem object
        fan_system = FanSystem(
            id=fan_id,
            name=name,
            fan_type=fan_type,
            airflow_cfm=airflow_cfm,
            power_w=power_w,
            efficiency=flow_eff,
            control_method=modeling_method,
            zone_served=None,
            annotation=annotation
        )

        return fan_system

    def _parse_res_fan_system(self, fan_elem: ET.Element) -> Optional[FanSystem]:
        """
        Parse a residential fan system (ResFanSys).

        Args:
            fan_elem: ResFanSys XML element

        Returns:
            FanSystem object
        """
        # Get name
        name = self._get_name(fan_elem)
        if not name:
            name = "Fan System"

        # Generate fan ID
        fan_id = self.id_registry.generate_id('FAN', name, '', 'CIBD22X')

        # Fan type
        fan_type = self.get_property(fan_elem, 'Type') or 'supply'

        # Airflow (CFM - cubic feet per minute)
        airflow_cfm = self._to_float(self.get_property(fan_elem, 'FlowCap'))

        # Power (W - watts)
        power_w = self._to_float(self.get_property(fan_elem, 'Pwr'))

        # Efficiency (dimensionless)
        efficiency = self._to_float(self.get_property(fan_elem, 'Eff'))

        # Control method
        control_method = self.get_property(fan_elem, 'CtrlMthd')

        # Zone served
        zone_served = self.get_property(fan_elem, 'ZnServedRef')

        # Build annotation with additional properties
        annotation = {'xml_tag': 'ResFanSys'}
        motor_eff = self._to_float(self.get_property(fan_elem, 'MotorEff'))
        if motor_eff:
            annotation['motor_efficiency'] = motor_eff

        # Additional CBECC properties
        wpercfm_cool = self.get_property(fan_elem, 'WperCFMCool')
        if wpercfm_cool:
            annotation['WperCFMCool'] = wpercfm_cool

        # Create FanSystem object
        fan_system = FanSystem(
            id=fan_id,
            name=name,
            fan_type=fan_type,
            airflow_cfm=airflow_cfm,
            power_w=power_w,
            efficiency=efficiency,
            control_method=control_method,
            zone_served=zone_served,
            annotation=annotation
        )

        return fan_system

    def _parse_central_vent_system(self, vent_elem: ET.Element) -> Optional[FanSystem]:
        """
        Parse a central ventilation system (ResCentralVentSys).

        Central ventilation systems are treated as fan systems with
        limited property specification.

        Args:
            vent_elem: ResCentralVentSys XML element

        Returns:
            FanSystem object
        """
        # Get name
        name = self._get_name(vent_elem)
        if not name:
            name = "Central Ventilation System"

        # Generate ventilation system ID
        vent_id = self.id_registry.generate_id('VENT', name, '', 'CIBD22X')

        # Type (may be empty)
        vent_type = self.get_property(vent_elem, 'Type') or 'central_ventilation'

        # Build annotation with xml_tag
        annotation = {'xml_tag': 'ResCentralVentSys'}

        # Extract CBECC-specific properties for ResCentralVentSys
        # Type: Balanced, Supply Only, Exhaust Only, etc.
        type_prop = self.get_property(vent_elem, 'Type')
        if type_prop:
            annotation['Type'] = type_prop

        # SupFanPwrIdx: Supply fan power index (W/CFM)
        sup_fan_pwr = self.get_property(vent_elem, 'SupFanPwrIdx')
        if sup_fan_pwr:
            annotation['SupFanPwrIdx'] = sup_fan_pwr

        # ExhFanPwrIdx: Exhaust fan power index (W/CFM)
        exh_fan_pwr = self.get_property(vent_elem, 'ExhFanPwrIdx')
        if exh_fan_pwr:
            annotation['ExhFanPwrIdx'] = exh_fan_pwr

        # Create FanSystem object
        # Note: Central ventilation systems typically don't have detailed specs in internal repr
        fan_system = FanSystem(
            id=vent_id,
            name=name,
            fan_type=vent_type,
            airflow_cfm=None,
            power_w=None,
            efficiency=None,
            control_method=None,
            zone_served=None,
            annotation=annotation
        )

        return fan_system

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
