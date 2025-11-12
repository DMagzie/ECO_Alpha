"""
Control System Catalog Exporter - HVAC Equipment Catalog Exporter
=================================================================

PURPOSE:
Serializes ControlSystem catalog objects to CIBD22X XML format.

These are CATALOG elements (OACtrl, EconoCtrl) that can be exported to root
or nested in HVAC systems depending on context.

PATTERN: Simple Catalog Exporter
"""

from typing import List
import xml.etree.ElementTree as ET
import logging

from eco_tools.core.internal_repr import ControlSystem
from .base_exporter import BaseExporter

logger = logging.getLogger('eco_tools.exporters')


class ControlSystemCatalogExporter(BaseExporter):
    """Exporter for CIBD22X control system catalog elements"""

    def __init__(self):
        super().__init__()

    def export_control_systems(self, parent: ET.Element, control_systems: List[ControlSystem]) -> None:
        """
        Export control system catalog elements.

        CRITICAL: OACtrl elements that reference AirSeg elements (via AirSegSupRef/AirSegRetRef)
        MUST be nested inside AirSys parent elements in the XML. Since we don't export the
        full HVAC hierarchy (AirSys → AirSeg → OACtrl), we cannot export these OACtrl
        elements as standalone items - they would reference non-existent AirSeg elements
        and cause "component not found" errors.

        Therefore, we skip OACtrl elements with AirSeg references entirely.
        """
        if not control_systems:
            logger.info("No control systems to export")
            return

        # Filter out OACtrl elements that reference AirSeg (they need to be nested in AirSys)
        standalone_controls = [
            ctrl for ctrl in control_systems
            if not (ctrl.annotation and
                   ('AirSegSupRef' in ctrl.annotation or 'AirSegRetRef' in ctrl.annotation))
        ]

        if not standalone_controls:
            logger.info("No standalone control systems to export (all require AirSys parent - skipped)")
            return

        exported_count = 0
        for ctrl in standalone_controls:
            if self._export_single_control_system(parent, ctrl):
                exported_count += 1

        skipped = len(control_systems) - len(standalone_controls)
        if skipped > 0:
            logger.info(f"Skipped {skipped} OACtrl elements that require AirSys parent (not yet supported)")

        logger.info(f"Exported {exported_count} control system elements")

    def _export_single_control_system(self, parent: ET.Element, ctrl: ControlSystem) -> bool:
        """Export a single control system catalog element."""
        if not ctrl.name:
            return False

        # Determine XML tag from control type (OACtrl, EconoCtrl)
        xml_tag = 'OACtrl' if 'outdoor' in ctrl.control_type.lower() or 'oa' in ctrl.control_type.lower() else 'EconoCtrl'

        # Create element
        ctrl_elem = self.create_element(parent, xml_tag)

        # Add name
        self.add_text_element(ctrl_elem, 'Name', ctrl.name)

        # Export all annotation properties for round-trip fidelity
        # Skip internal-only annotation keys (xml_tag, parent_airsys_name, etc.)
        skip_props = {'xml_tag', 'parent_airsys_name'}
        if ctrl.annotation:
            for prop, value in ctrl.annotation.items():
                if prop not in skip_props and value is not None:
                    self.add_text_element(ctrl_elem, prop, str(value))

        # Fallback: export from internal representation
        if not ctrl.annotation:
            if ctrl.control_method:
                self.add_text_element(ctrl_elem, 'CtrlMthd', ctrl.control_method)
            if ctrl.setpoint_high is not None:
                self.add_numeric_element(ctrl_elem, 'HiTempLockout', ctrl.setpoint_high, precision=1)
            if ctrl.setpoint_low is not None:
                self.add_numeric_element(ctrl_elem, 'LoTempLockout', ctrl.setpoint_low, precision=1)

        return True
