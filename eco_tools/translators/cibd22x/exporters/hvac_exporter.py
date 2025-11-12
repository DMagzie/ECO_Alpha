"""
HVAC System Exporter - Composite System Exporter
================================================

PURPOSE:
Serializes HVACSystem and ZoneTerminal objects to CIBD22X XML format.

COMPOSITE EXPORT:
This exporter handles TWO element types from a single system definition:
1. HVACSystem (the system itself)
2. ZoneTerminal (zone-to-HVAC linkage)

EXPORT STRATEGY:
1. Export HVAC system with equipment references
2. Export zone terminals showing which zones are served
3. Handle equipment arrays with counts (Phase 1.5 CBECC)
4. Restore format-specific properties from annotations

ANNOTATION RESTORATION:
- System type, status codes
- Equipment arrays (heating/cooling/distribution/fan systems)
- Equipment counts (for multiple identical units)
- Zone terminal configuration

PATTERN: Composite exporter (similar to DHWSystemParser pattern)
"""

from typing import List
import xml.etree.ElementTree as ET
import logging

from eco_tools.core.internal_repr import HVACSystem, ZoneTerminal
from .base_exporter import BaseExporter

# Get module logger
logger = logging.getLogger('eco_tools.exporters')


class HVACExporter(BaseExporter):
    """Exporter for CIBD22X HVAC system elements"""

    def __init__(self):
        super().__init__()

    def export_hvac_systems(
        self,
        parent: ET.Element,
        hvac_systems: List[HVACSystem],
        zone_terminals: List[ZoneTerminal]
    ) -> None:
        """
        Export all HVAC systems with their zone terminals.

        Args:
            parent: Parent XML element (typically <Building>)
            hvac_systems: List of HVACSystem objects
            zone_terminals: List of ZoneTerminal objects
        """
        if not hvac_systems:
            logger.info("No HVAC systems to export")
            return

        exported_systems = 0
        exported_terminals = 0

        for hvac_system in hvac_systems:
            hvac_elem = self._export_hvac_system(parent, hvac_system)
            if hvac_elem:
                exported_systems += 1

                # Export zone terminals for this system
                system_terminals = [zt for zt in zone_terminals if zt.hvac_system_id == hvac_system.id]
                for terminal in system_terminals:
                    if self._export_zone_terminal(hvac_elem, terminal):
                        exported_terminals += 1

        logger.info(f"Exported {exported_systems} HVAC systems and {exported_terminals} zone terminals")

    def _export_hvac_system(self, parent: ET.Element, hvac: HVACSystem) -> ET.Element:
        """Export a single HVAC system."""
        if not hvac.name:
            logger.warning(f"Skipping HVAC system with missing name (id: {hvac.id})")
            return None

        # Determine XML tag from annotation
        xml_tag = self.get_annotation(hvac.annotation, 'xml_tag', 'ResHVACSys')

        # CRITICAL: Skip AirSeg elements - these are commercial-only nested components
        # AirSeg elements should only be exported as children of commercial HVAC systems,
        # never as standalone root-level elements in residential CIBD22X files
        if xml_tag == 'AirSeg':
            logger.debug(f"Skipping AirSeg element '{hvac.name}' - not valid for root-level export")
            return None

        # Create HVAC system element
        hvac_elem = self.create_element(parent, xml_tag)

        # Add name (required)
        self.add_text_element(hvac_elem, 'Name', hvac.name)

        # System type - restore descriptive text from annotation, not numeric code
        # CRITICAL: hvac.type may be numeric code, use annotation for descriptive text
        system_type = self.get_annotation(hvac.annotation, 'system_type_text')
        if system_type:
            self.add_text_element(hvac_elem, 'Type', system_type)
        elif hvac.type:
            # Fallback to hvac.type if no annotation (shouldn't happen for properly imported files)
            self.add_text_element(hvac_elem, 'Type', str(hvac.type))

        # Status (Existing, Altered, New, Mixed)
        if hvac.status:
            status_text = self.get_annotation(hvac.annotation, 'status_text')
            if not status_text:
                status_map = {1: 'Existing', 2: 'Altered', 3: 'New', 4: 'Mixed'}
                status_text = status_map.get(hvac.status, str(hvac.status))
            self.add_text_element(hvac_elem, 'Status', status_text)

        # Restore equipment references from annotations
        # Heat pump systems (for heat pump HVAC systems)
        if hvac.annotation:
            ht_pump_refs = self.get_annotation(hvac.annotation, 'ht_pump_system_refs')
            if ht_pump_refs and isinstance(ht_pump_refs, list):
                for ht_pump_data in ht_pump_refs:
                    if isinstance(ht_pump_data, dict):
                        ht_pump_name = ht_pump_data.get('name')
                        if ht_pump_name:
                            ht_pump_elem = ET.SubElement(hvac_elem, 'HtPumpSystem')
                            ht_pump_elem.text = ht_pump_name
                            # Add index if specified
                            index = ht_pump_data.get('index')
                            if index is not None:
                                ht_pump_elem.set('index', str(index))

        # Equipment arrays with counts (Phase 1.5) - for non-heat pump systems
        if hvac.heating_systems and hvac.heating_counts:
            for i, (heater_ref, count) in enumerate(zip(hvac.heating_systems, hvac.heating_counts), 1):
                self.add_text_element(hvac_elem, 'HeatSystem', heater_ref, skip_if_none=False)
                if count > 1:
                    count_elem = ET.SubElement(hvac_elem, 'HeatSystemCount')
                    count_elem.text = str(count)

        if hvac.cooling_systems and hvac.cooling_counts:
            for i, (cooler_ref, count) in enumerate(zip(hvac.cooling_systems, hvac.cooling_counts), 1):
                self.add_text_element(hvac_elem, 'CoolSystem', cooler_ref, skip_if_none=False)
                if count > 1:
                    count_elem = ET.SubElement(hvac_elem, 'CoolSystemCount')
                    count_elem.text = str(count)

        # Distribution system reference - property name depends on HVAC type
        # CRITICAL: ResHVACSys uses 'DistribSystem', commercial uses 'DistSysRef'
        if hvac.distribution_ref:
            dist_property = 'DistribSystem' if xml_tag == 'ResHVACSys' else 'DistSysRef'
            self.add_text_element(hvac_elem, dist_property, hvac.distribution_ref)

        # Fan system reference - property name depends on HVAC type
        # CRITICAL: ResHVACSys uses 'Fan', commercial uses 'FanSysRef'
        if hvac.fan_ref:
            fan_property = 'Fan' if xml_tag == 'ResHVACSys' else 'FanSysRef'
            self.add_text_element(hvac_elem, fan_property, hvac.fan_ref)

        # Don't export AirSeg elements for residential HVAC systems
        # AirSeg is only for commercial HVAC systems
        # Air segments would be exported separately if needed for commercial systems

        return hvac_elem

    def _export_zone_terminal(self, parent: ET.Element, terminal: ZoneTerminal) -> bool:
        """Export a zone terminal (zone-to-HVAC linkage)."""
        # Create ZnSys element
        zn_sys_elem = ET.SubElement(parent, 'ZnSys')

        # Zone reference
        if terminal.zone_id:
            self.add_text_element(zn_sys_elem, 'ZnRef', terminal.zone_id)

        # Terminal type (if specified)
        if hasattr(terminal, 'terminal_type') and terminal.terminal_type:
            self.add_text_element(zn_sys_elem, 'Type', terminal.terminal_type)

        return True
