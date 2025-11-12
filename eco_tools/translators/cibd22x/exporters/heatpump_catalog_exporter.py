"""
Heat Pump Catalog Exporter - HVAC Equipment Catalog Exporter
============================================================

PURPOSE:
Serializes HeatPump catalog objects to CIBD22X XML format.

These are CATALOG elements (ResHtPumpSys) exported to root, NOT instance elements.
HVAC systems (ResHVACSys) reference these catalogs via HVACHtPumpRef.

PATTERN: Simple Catalog Exporter - mirrors HeatPumpParser logic
"""

from typing import List
import xml.etree.ElementTree as ET
import logging

from eco_tools.core.internal_repr import HeatPump
from .base_exporter import BaseExporter

logger = logging.getLogger('eco_tools.exporters')


class HeatPumpCatalogExporter(BaseExporter):
    """Exporter for CIBD22X heat pump catalog elements"""

    def __init__(self):
        super().__init__()

    def export_heat_pumps(self, parent: ET.Element, heat_pumps: List[HeatPump]) -> None:
        """
        Export all heat pump catalog elements to CIBD22X XML.

        Args:
            parent: Parent XML element (typically root/SDDXML)
            heat_pumps: List of HeatPump catalog objects
        """
        if not heat_pumps:
            logger.info("No heat pumps to export")
            return

        exported_count = 0
        for hp in heat_pumps:
            if self._export_single_heat_pump(parent, hp):
                exported_count += 1

        logger.info(f"Exported {exported_count} heat pump catalog elements")

    def _export_single_heat_pump(self, parent: ET.Element, hp: HeatPump) -> bool:
        """Export a single heat pump catalog element."""
        if not hp.name:
            return False

        # Create ResHtPumpSys element
        hp_elem = self.create_element(parent, 'ResHtPumpSys')

        # Add name (required)
        self.add_text_element(hp_elem, 'Name', hp.name)

        # Export all properties from annotation for round-trip fidelity
        # Parsers store all CBECC-specific properties here
        if hp.annotation:
            # Export all annotation properties
            for prop, value in hp.annotation.items():
                if prop != 'xml_tag' and value is not None:
                    self.add_text_element(hp_elem, prop, str(value))

        # Fallback: export from internal representation if no annotation
        if not hp.annotation:
            # Type
            if hp.pump_type:
                self.add_text_element(hp_elem, 'Type', hp.pump_type)

            # Capacities (convert W to Btu/h: × 3.412142)
            if hp.heating_capacity_w is not None:
                heating_btuh = hp.heating_capacity_w * 3.412142
                self.add_numeric_element(hp_elem, 'CapHeat', heating_btuh, precision=0)

            if hp.cooling_capacity_w is not None:
                cooling_btuh = hp.cooling_capacity_w * 3.412142
                self.add_numeric_element(hp_elem, 'CapCool', cooling_btuh, precision=0)

            # Efficiency
            if hp.heating_cop is not None:
                self.add_numeric_element(hp_elem, 'COPHP', hp.heating_cop, precision=2)

            if hp.cooling_eer is not None:
                self.add_numeric_element(hp_elem, 'EER', hp.cooling_eer, precision=2)

        return True
