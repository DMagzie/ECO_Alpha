"""
RecirculationLoop Parser - Sub-Parser (Used by DHWSystemParser)
===============================================================

PURPOSE: Extracts recirculation loop piping nested within DHW systems.
This is a SUB-PARSER called by DHWSystemParser (composite parser).

PATTERN: Sub-Parser - Called by composite parent, not directly by importer.

KEY OPERATIONS:
- Parse loop pipe configuration (length, diameter, insulation)
- Extract pump properties (power, control method)
- Link to parent DHW system

USAGE: Only called by DHWSystemParser.parse_dhw_systems()
"""

from typing import List, Optional
import xml.etree.ElementTree as ET
import logging

from eco_tools.core.internal_repr import RecirculationLoop
from eco_tools.core.id_registry import IDRegistry
from .base_parser import BaseParser

# Get module logger
logger = logging.getLogger('eco_tools.parsers')


class RecirculationLoopParser(BaseParser):
    """Parser for CIBD22X recirculation loop elements"""

    RECIRC_LOOP_TAGS = [
        'DHWLoopSeg',  # DHW loop segments
    ]

    def __init__(self, id_registry: IDRegistry):
        super().__init__()
        self.id_registry = id_registry

    def parse_recirculation_loops(self, sys_elem: ET.Element, dhw_system_id: str) -> List[RecirculationLoop]:
        """
        Parse recirculation loops for central DHW systems.

        Args:
            sys_elem: DHW system XML element
            dhw_system_id: Parent DHW system ID

        Returns:
            List of RecirculationLoop objects
        """
        loops = []

        for loop_elem in sys_elem.findall('.//DHWLoopSeg'):
            loop_name = self._get_name(loop_elem)
            if not loop_name:
                loop_name = f"Loop_{len(loops) + 1}"

            loop_id = self.id_registry.generate_id('RL', loop_name, dhw_system_id, 'CIBD22X')

            # Loop type
            loop_type = self.get_property(loop_elem, 'Type')
            if not loop_type:
                loop_type = self.get_property(loop_elem, 'RecircType') or 'Central'

            # Loop configuration
            pipe_length = self._to_float(self.get_property(loop_elem, 'PipeLength'))
            pipe_diameter = self._to_float(self.get_property(loop_elem, 'PipeDiameter'))
            pipe_insulation_r = self._to_float(self.get_property(loop_elem, 'PipeInsulRValue'))

            # Pump properties
            pump_power = self._to_float(self.get_property(loop_elem, 'PumpPower'))
            if pump_power is None:
                pump_power = self._to_float(self.get_property(loop_elem, 'DHWPumpPower'))

            flow_rate = self._to_float(self.get_property(loop_elem, 'FlowRate'))

            # Control
            control_type = self.get_property(loop_elem, 'ControlType')
            operating_hours = self._to_float(self.get_property(loop_elem, 'OperatingHours'))

            # Loss calculation
            heat_loss = self._to_float(self.get_property(loop_elem, 'HeatLoss'))

            loop = RecirculationLoop(
                id=loop_id,
                name=loop_name,
                parent_dhw_system_id=dhw_system_id,
                loop_type=loop_type,
                pipe_length_ft=pipe_length,
                pipe_diameter_in=pipe_diameter,
                pipe_insulation_r_value=pipe_insulation_r,
                pump_power_w=pump_power,
                flow_rate_gpm=flow_rate,
                control_type=control_type,
                operating_hours_per_day=operating_hours,
                heat_loss_btu_hr=heat_loss
            )

            loops.append(loop)

        return loops

    def _get_name(self, element: ET.Element) -> Optional[str]:
        """Extract name from element."""
        name_elem = element.find('.//n')
        if name_elem is not None and name_elem.text:
            return name_elem.text.strip()
        name_elem = element.find('.//Name')
        if name_elem is not None and name_elem.text:
            return name_elem.text.strip()
        name = element.get('id')
        return name if name else None
