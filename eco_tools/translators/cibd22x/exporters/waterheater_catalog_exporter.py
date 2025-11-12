"""
Water Heater Catalog Exporter - DHW Equipment Catalog Exporter
==============================================================

PURPOSE:
Serializes WaterHeater catalog objects to CIBD22X XML format.

These are CATALOG elements (ResWtrHtr) exported to root, NOT instance elements.
DHW systems reference these via DHWHeaterRef or heater name.

PATTERN: Simple Catalog Exporter
"""

from typing import List
import xml.etree.ElementTree as ET
import logging

from eco_tools.core.internal_repr import WaterHeater
from .base_exporter import BaseExporter

logger = logging.getLogger('eco_tools.exporters')


class WaterHeaterCatalogExporter(BaseExporter):
    """Exporter for CIBD22X water heater catalog elements"""

    def __init__(self):
        super().__init__()

    def export_water_heaters(self, parent: ET.Element, water_heaters: List[WaterHeater]) -> None:
        """Export water heater catalog elements (ResWtrHtr only, not instance elements)."""
        if not water_heaters:
            logger.info("No water heaters to export")
            return

        # Only export catalog water heaters (ones with xml_tag='ResWtrHtr' annotation)
        # Instance water heaters nested in DHW systems are exported by DHWExporter
        catalog_heaters = [wh for wh in water_heaters
                          if wh.annotation and wh.annotation.get('xml_tag') == 'ResWtrHtr']

        if not catalog_heaters:
            logger.info("No water heater catalog elements to export")
            return

        exported_count = 0
        for wh in catalog_heaters:
            if self._export_single_water_heater(parent, wh):
                exported_count += 1

        logger.info(f"Exported {exported_count} water heater catalog elements")

    def _export_single_water_heater(self, parent: ET.Element, wh: WaterHeater) -> bool:
        """Export a single water heater catalog element."""
        if not wh.name:
            return False

        # Create ResWtrHtr element
        wh_elem = self.create_element(parent, 'ResWtrHtr')

        # Add name
        self.add_text_element(wh_elem, 'Name', wh.name)

        # Export all annotation properties for round-trip fidelity
        if wh.annotation:
            for prop, value in wh.annotation.items():
                if prop != 'xml_tag' and value is not None:
                    self.add_text_element(wh_elem, prop, str(value))

        # Fallback: export from internal representation if no annotation
        if not wh.annotation:
            if wh.heater_type:
                self.add_text_element(wh_elem, 'HeaterElementType', wh.heater_type)
            if wh.tank_type:
                self.add_text_element(wh_elem, 'TankType', wh.tank_type)
            if wh.input_capacity_btu_hr is not None:
                self.add_numeric_element(wh_elem, 'InputRating', wh.input_capacity_btu_hr, precision=0)
            if wh.energy_factor is not None:
                self.add_numeric_element(wh_elem, 'EnergyFactor', wh.energy_factor, precision=2)
            if wh.storage_volume_gal is not None:
                self.add_numeric_element(wh_elem, 'TankVolume', wh.storage_volume_gal, precision=0)
            if wh.recovery_efficiency is not None:
                self.add_numeric_element(wh_elem, 'RecovEff', wh.recovery_efficiency, precision=0)

        return True
