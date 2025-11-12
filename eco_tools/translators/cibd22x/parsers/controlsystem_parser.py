"""
ControlSystem Parser - Simple Catalog Parser (HVAC Component)
=============================================================

PURPOSE: Extracts HVAC control system catalog definitions from CIBD22X XML.
Controls manage outdoor air, economizers, and HVAC sequencing.

PATTERN: Simple Catalog Parser - See material_parser.py for pattern details.

KEY OPERATIONS: Parse control type, setpoints, economizer settings, outdoor air control.
- Air system references
"""

from typing import List, Optional
import xml.etree.ElementTree as ET
import logging

from eco_tools.core.internal_repr import ControlSystem
from eco_tools.core.id_registry import IDRegistry
from .base_parser import BaseParser

# Get module logger
logger = logging.getLogger('eco_tools.parsers')


class ControlSystemParser(BaseParser):
    """Parser for CIBD22X control system elements"""

    CONTROL_SYSTEM_CATALOG_TAGS = [
        'OACtrl',       # Outdoor air controls
        'EconoCtrl'     # Economizer controls
    ]

    def __init__(self, id_registry: IDRegistry):
        super().__init__()
        self.id_registry = id_registry

    def parse_control_systems(self, root: ET.Element) -> List[ControlSystem]:
        """Parse all control systems from CIBD22X catalog."""
        control_systems = []

        # Use namespace-aware iteration
        for ctrl_elem in root.iter():
            local_tag = self._local_tag(ctrl_elem.tag)

            # Parse outdoor air controls
            if local_tag == 'OACtrl':
                ctrl_sys = self._parse_outdoor_air_control(ctrl_elem)
                if ctrl_sys:
                    control_systems.append(ctrl_sys)
                else:
                    name = self._get_name(ctrl_elem) or "unnamed"
                    logger.warning(f"Failed to parse OACtrl '{name}'")

            # Parse economizer controls
            elif local_tag == 'EconoCtrl':
                ctrl_sys = self._parse_economizer_control(ctrl_elem)
                if ctrl_sys:
                    control_systems.append(ctrl_sys)
                else:
                    name = self._get_name(ctrl_elem) or "unnamed"
                    logger.warning(f"Failed to parse EconoCtrl '{name}'")

        logger.info(f"Parsed {len(control_systems)} control systems")
        return control_systems

    def _parse_outdoor_air_control(self, ctrl_elem: ET.Element) -> Optional[ControlSystem]:
        """Parse outdoor air control element."""
        name = self._get_name(ctrl_elem) or "Outdoor Air Control"
        ctrl_id = self.id_registry.generate_id('CTRL', name, '', 'CIBD22X')

        control_method = self.get_property(ctrl_elem, 'CtrlMthd')
        setpoint_high = self._to_float(self.get_property(ctrl_elem, 'HiTempLockout'))
        setpoint_low = self._to_float(self.get_property(ctrl_elem, 'LoTempLockout'))
        system_ref = self.get_property(ctrl_elem, 'AirSysRef')

        # Build annotation with ALL CBECC properties for round-trip fidelity
        annotation = {}
        cbecc_properties = [
            'CtrlMthd', 'EconoCtrlMthd', 'AirSegSupRef', 'AirSegRetRef',
            'HiTempLockout', 'LoTempLockout', 'AirSysRef',
            'MinOASchRef', 'OAFlowRat', 'OAFlowRatSchRef'
        ]
        for prop in cbecc_properties:
            value = self.get_property(ctrl_elem, prop)
            if value:
                annotation[prop] = value

        # CRITICAL: Store parent AirSys name for export
        # OACtrl is nested in AirSys, derive parent name from control name
        # Pattern: "SFC-7_Leasing_L01 OACtrl" → "SFC-7_Leasing_L01 AirSys"
        if name and ' OACtrl' in name:
            parent_airsys_name = name.replace(' OACtrl', ' AirSys')
            annotation['parent_airsys_name'] = parent_airsys_name

        return ControlSystem(
            id=ctrl_id,
            name=name,
            control_type='outdoor_air',
            control_method=control_method,
            setpoint_high=setpoint_high,
            setpoint_low=setpoint_low,
            system_ref=system_ref,
            annotation=annotation
        )

    def _parse_economizer_control(self, ctrl_elem: ET.Element) -> Optional[ControlSystem]:
        """Parse economizer control element."""
        name = self._get_name(ctrl_elem) or "Economizer Control"
        ctrl_id = self.id_registry.generate_id('CTRL', name, '', 'CIBD22X')

        control_method = self.get_property(ctrl_elem, 'CtrlMthd')
        system_ref = self.get_property(ctrl_elem, 'AirSysRef')

        return ControlSystem(
            id=ctrl_id,
            name=name,
            control_type='economizer',
            control_method=control_method,
            setpoint_high=None,
            setpoint_low=None,
            system_ref=system_ref,
            annotation={}
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
