"""
DHW System Exporter - Composite System Exporter
===============================================

PURPOSE:
Serializes DHWSystem, WaterHeater, and RecirculationLoop objects to CIBD22X XML.

COMPOSITE EXPORT:
This exporter handles THREE element types from a single system definition:
1. DHWSystem (the system itself)
2. WaterHeater (nested equipment - can be array with counts)
3. RecirculationLoop (nested piping loops)

EXPORT STRATEGY:
1. Export DHW system with basic properties
2. Export nested water heater elements (DHWHeater) with counts
3. Export nested recirculation loop elements (DHWLoopSeg)
4. Handle central vs individual system classification
5. Restore format-specific properties from annotations

NESTED EXPORT:
Water heaters and recirc loops are exported as CHILDREN of DHW system elements,
not as separate top-level elements.

ANNOTATION RESTORATION:
- System type (central vs individual)
- Distribution properties
- Water heater arrays with counts
- Recirculation loop configuration

PATTERN: Composite exporter (mirrors DHWSystemParser)
"""

from typing import List
import xml.etree.ElementTree as ET
import logging

from eco_tools.core.internal_repr import DHWSystem, WaterHeater, RecirculationLoop
from .base_exporter import BaseExporter

# Get module logger
logger = logging.getLogger('eco_tools.exporters')


class DHWExporter(BaseExporter):
    """Exporter for CIBD22X DHW system elements"""

    def __init__(self):
        super().__init__()

    def export_dhw_systems(
        self,
        parent: ET.Element,
        dhw_systems: List[DHWSystem],
        water_heaters: List[WaterHeater],
        recirc_loops: List[RecirculationLoop]
    ) -> None:
        """
        Export all DHW systems with nested water heaters and recirc loops.

        Args:
            parent: Parent XML element (typically <Building>)
            dhw_systems: List of DHWSystem objects
            water_heaters: List of WaterHeater objects
            recirc_loops: List of RecirculationLoop objects
        """
        if not dhw_systems:
            logger.info("No DHW systems to export")
            return

        exported_systems = 0
        exported_heaters = 0
        exported_loops = 0

        # Build lookup maps for water heaters and recirc loops
        heater_map = {wh.id: wh for wh in water_heaters}
        loop_map = {rl.id: rl for rl in recirc_loops}

        for dhw_system in dhw_systems:
            dhw_elem = self._export_dhw_system(parent, dhw_system)
            if dhw_elem:
                exported_systems += 1

                # Export water heaters referenced by this system
                for heater_id in dhw_system.water_heaters:
                    heater = heater_map.get(heater_id)
                    if heater and self._export_water_heater(dhw_elem, heater):
                        exported_heaters += 1

                # Export recirc loops referenced by this system
                for loop_id in dhw_system.recirculation_loops:
                    loop = loop_map.get(loop_id)
                    if loop and self._export_recirc_loop(dhw_elem, loop):
                        exported_loops += 1

        logger.info(f"Exported {exported_systems} DHW systems, {exported_heaters} water heaters, {exported_loops} recirc loops")

    def _export_dhw_system(self, parent: ET.Element, dhw: DHWSystem) -> ET.Element:
        """Export a single DHW system."""
        if not dhw.name:
            logger.warning(f"Skipping DHW system with missing name (id: {dhw.id})")
            return None

        # Determine XML tag from annotation
        xml_tag = self.get_annotation(dhw.annotation, 'xml_tag', 'ResDHWSys')

        # Create DHW system element
        dhw_elem = self.create_element(parent, xml_tag)

        # Add name (required)
        self.add_text_element(dhw_elem, 'Name', dhw.name)

        # System type - property name is SystemType for ResDHWSys, Type for commercial
        # CRITICAL: ResDHWSys uses 'SystemType' not 'Type'
        if dhw.system_type:
            type_property = 'SystemType' if xml_tag == 'ResDHWSys' else 'Type'
            self.add_text_element(dhw_elem, type_property, dhw.system_type)

        # Restore format-specific properties from annotations
        # These include many properties not in InternalRepresentation base model
        if dhw.annotation:
            annotation_props = [
                'CentralRecircType', 'CHPWHLoopTankConfig',
                'FloorAreaServed', 'DwellUnitsServed',
                'RecircCtrlType', 'RecircLoopCount',
                'RecircPipingConfig', 'RecircTankType'
            ]
            for prop in annotation_props:
                value = self.get_annotation(dhw.annotation, prop)
                if value:
                    self.add_text_element(dhw_elem, prop, str(value))

            # Export water heater references and counts from annotation
            # These are stored as 'dhw_heater_refs' in annotation
            heater_refs = self.get_annotation(dhw.annotation, 'dhw_heater_refs')
            if heater_refs and isinstance(heater_refs, list):
                for heater_data in heater_refs:
                    if isinstance(heater_data, dict):
                        heater_name = heater_data.get('name')
                        if heater_name:
                            heater_elem = ET.SubElement(dhw_elem, 'DHWHeater')
                            heater_elem.text = heater_name

                            # Add index if specified
                            index = heater_data.get('index')
                            if index is not None:
                                heater_elem.set('index', str(index))

                        # Export heater multiplier/count
                        count = heater_data.get('count')
                        if count and count > 1:
                            mult_elem = ET.SubElement(dhw_elem, 'HeaterMult')
                            mult_index = heater_data.get('index')
                            if mult_index is not None:
                                mult_elem.set('index', str(mult_index))
                            mult_elem.text = str(count)

        return dhw_elem

    def _export_water_heater(self, parent: ET.Element, heater: WaterHeater) -> bool:
        """Export a water heater as nested DHWHeater element."""
        # Create DHWHeater element
        heater_elem = ET.SubElement(parent, 'DHWHeater')
        
        # CBECC uses text content for heater name/reference
        heater_elem.text = heater.name if heater.name else heater.id

        # Heater count (for arrays of identical heaters)
        if hasattr(heater, 'count') and heater.count and heater.count > 1:
            count_elem = ET.SubElement(parent, 'DHWHeaterCount')
            count_elem.text = str(heater.count)

        return True

    def _export_recirc_loop(self, parent: ET.Element, loop: RecirculationLoop) -> bool:
        """Export a recirculation loop as nested DHWLoopSeg element."""
        # Create DHWLoopSeg element
        loop_elem = ET.SubElement(parent, 'DHWLoopSeg')

        # Loop name
        if loop.name:
            self.add_text_element(loop_elem, 'Name', loop.name)

        # Loop type
        if loop.loop_type:
            self.add_text_element(loop_elem, 'Type', loop.loop_type)

        # Pipe configuration (lengths in ft, diameters in inches)
        if loop.pipe_length_ft is not None:
            self.add_numeric_element(loop_elem, 'PipeLength', loop.pipe_length_ft, precision=1)

        if loop.pipe_diameter_in is not None:
            self.add_numeric_element(loop_elem, 'PipeDiameter', loop.pipe_diameter_in, precision=2)

        if loop.pipe_insulation_r_value is not None:
            self.add_numeric_element(loop_elem, 'PipeInsulRValue', loop.pipe_insulation_r_value, precision=2)

        # Pump properties
        if loop.pump_power_w is not None:
            self.add_numeric_element(loop_elem, 'PumpPower', loop.pump_power_w, precision=1)

        if loop.flow_rate_gpm is not None:
            self.add_numeric_element(loop_elem, 'FlowRate', loop.flow_rate_gpm, precision=2)

        # Control type
        if loop.control_type:
            self.add_text_element(loop_elem, 'ControlType', loop.control_type)

        return True
