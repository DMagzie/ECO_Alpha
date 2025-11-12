"""
Fan System Catalog Exporter - HVAC Equipment Catalog Exporter
=============================================================

PURPOSE:
Serializes FanSystem catalog objects to CIBD22X XML format.

These are CATALOG elements (ResFanSys) exported to root, NOT instance elements.
Dwelling unit types and HVAC systems reference these via HVACFanRef.

PATTERN: Simple Catalog Exporter
"""

from typing import List
import xml.etree.ElementTree as ET
import logging

from eco_tools.core.internal_repr import FanSystem
from .base_exporter import BaseExporter

logger = logging.getLogger('eco_tools.exporters')


class FanSystemCatalogExporter(BaseExporter):
    """Exporter for CIBD22X fan system catalog elements"""

    def __init__(self):
        super().__init__()

    def export_fan_systems(self, parent: ET.Element, fan_systems: List[FanSystem]) -> None:
        """Export all fan system catalog elements."""
        if not fan_systems:
            logger.info("No fan systems to export")
            return

        exported_count = 0
        for fs in fan_systems:
            if self._export_single_fan_system(parent, fs):
                exported_count += 1

        logger.info(f"Exported {exported_count} fan system catalog elements")

    def _export_single_fan_system(self, parent: ET.Element, fs: FanSystem) -> bool:
        """Export a single fan system catalog element."""
        if not fs.name:
            return False

        # Determine XML tag from annotation (ResFanSys or ResCentralVentSys)
        xml_tag = self.get_annotation(fs.annotation, 'xml_tag', 'ResFanSys')

        # Create element
        fs_elem = self.create_element(parent, xml_tag)

        # Add name
        self.add_text_element(fs_elem, 'Name', fs.name)

        # Export all annotation properties for round-trip fidelity
        if fs.annotation:
            for prop, value in fs.annotation.items():
                if prop != 'xml_tag' and value is not None:
                    self.add_text_element(fs_elem, prop, str(value))

        # Fallback: export from internal representation
        if not fs.annotation:
            if fs.fan_type:
                self.add_text_element(fs_elem, 'FanType', fs.fan_type)
            if fs.airflow_cfm is not None:
                self.add_numeric_element(fs_elem, 'FlowCap', fs.airflow_cfm, precision=0)
            if fs.power_w is not None:
                self.add_numeric_element(fs_elem, 'TotPwr', fs.power_w, precision=1)

        return True
