"""
IAQ Fan Catalog Exporter - HVAC Equipment Catalog Exporter
==========================================================

PURPOSE:
Serializes IAQFan catalog objects to CIBD22X XML format.

These are CATALOG elements (ResIAQFan) exported to root, NOT instance elements.
Dwelling unit types reference these via IAQFanRef.

PATTERN: Simple Catalog Exporter
"""

from typing import List
import xml.etree.ElementTree as ET
import logging

from eco_tools.core.internal_repr import IAQFan
from .base_exporter import BaseExporter

logger = logging.getLogger('eco_tools.exporters')


class IAQFanCatalogExporter(BaseExporter):
    """Exporter for CIBD22X IAQ fan catalog elements"""

    def __init__(self):
        super().__init__()

    def export_iaq_fans(self, parent: ET.Element, iaq_fans: List[IAQFan]) -> None:
        """Export all IAQ fan catalog elements."""
        if not iaq_fans:
            logger.info("No IAQ fans to export")
            return

        exported_count = 0
        for iaq in iaq_fans:
            if self._export_single_iaq_fan(parent, iaq):
                exported_count += 1

        logger.info(f"Exported {exported_count} IAQ fan catalog elements")

    def _export_single_iaq_fan(self, parent: ET.Element, iaq: IAQFan) -> bool:
        """Export a single IAQ fan catalog element."""
        if not iaq.name:
            return False

        # Create ResIAQFan element
        iaq_elem = self.create_element(parent, 'ResIAQFan')

        # Add name
        self.add_text_element(iaq_elem, 'Name', iaq.name)

        # Export all annotation properties for round-trip fidelity
        if iaq.annotation:
            for prop, value in iaq.annotation.items():
                if prop != 'xml_tag' and value is not None:
                    self.add_text_element(iaq_elem, prop, str(value))

        # Fallback: export from internal representation
        if not iaq.annotation:
            if iaq.fan_type:
                self.add_text_element(iaq_elem, 'IAQFanType', iaq.fan_type)
            if iaq.airflow_cfm is not None:
                self.add_numeric_element(iaq_elem, 'IAQCFM', iaq.airflow_cfm, precision=0)
            if iaq.power_w is not None:
                # Power per CFM
                if iaq.airflow_cfm and iaq.airflow_cfm > 0:
                    w_per_cfm = iaq.power_w / iaq.airflow_cfm
                    self.add_numeric_element(iaq_elem, 'WperCFMIAQ', w_per_cfm, precision=3)

        return True
