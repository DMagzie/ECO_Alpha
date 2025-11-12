"""
Distribution System Catalog Exporter - HVAC Equipment Catalog Exporter
======================================================================

PURPOSE:
Serializes DistributionSystem catalog objects to CIBD22X XML format.

These are CATALOG elements (ResDistSys) exported to root, NOT instance elements.
Dwelling unit types and HVAC systems reference these via HVACDistRef.

PATTERN: Simple Catalog Exporter
"""

from typing import List
import xml.etree.ElementTree as ET
import logging

from eco_tools.core.internal_repr import DistributionSystem
from .base_exporter import BaseExporter

logger = logging.getLogger('eco_tools.exporters')


class DistributionSystemCatalogExporter(BaseExporter):
    """Exporter for CIBD22X distribution system catalog elements"""

    def __init__(self):
        super().__init__()

    def export_distribution_systems(self, parent: ET.Element, dist_systems: List[DistributionSystem]) -> None:
        """Export all distribution system catalog elements."""
        if not dist_systems:
            logger.info("No distribution systems to export")
            return

        exported_count = 0
        for ds in dist_systems:
            if self._export_single_distribution_system(parent, ds):
                exported_count += 1

        logger.info(f"Exported {exported_count} distribution system catalog elements")

    def _export_single_distribution_system(self, parent: ET.Element, ds: DistributionSystem) -> bool:
        """Export a single distribution system catalog element."""
        if not ds.name:
            return False

        # Create ResDistSys element
        ds_elem = self.create_element(parent, 'ResDistSys')

        # Add name
        self.add_text_element(ds_elem, 'Name', ds.name)

        # Export all annotation properties for round-trip fidelity
        if ds.annotation:
            for prop, value in ds.annotation.items():
                if prop != 'xml_tag' and value is not None:
                    self.add_text_element(ds_elem, prop, str(value))

        # Fallback: export from internal representation
        if not ds.annotation:
            if ds.distribution_type:
                self.add_text_element(ds_elem, 'Type', ds.distribution_type)
            if ds.duct_location:
                self.add_text_element(ds_elem, 'DuctLoc', ds.duct_location)

            # R-value: SI to IP (m²·K/W to h·ft²·°F/Btu: ÷0.1761)
            if ds.duct_insulation_r_value_SI is not None:
                r_ip = ds.duct_insulation_r_value_SI / 0.1761
                self.add_numeric_element(ds_elem, 'DuctInsRVal', r_ip, precision=2)

            if ds.duct_leakage_pct is not None:
                self.add_numeric_element(ds_elem, 'DuctLkg', ds.duct_leakage_pct, precision=1)

        return True
