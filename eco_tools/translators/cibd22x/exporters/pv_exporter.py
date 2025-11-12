"""
PV Array Exporter - Composite System Exporter
=============================================

PURPOSE:
Serializes PVArray and BatterySystem objects to CIBD22X XML format.

COMPOSITE EXPORT:
This exporter handles TWO element types:
1. PVArray (solar array itself)
2. BatterySystem (nested battery storage)

EXPORT STRATEGY:
1. Export PV array with module specs and orientation
2. Export nested battery system if present
3. Handle residential vs commercial PV variants
4. Restore format-specific properties from annotations

NESTED EXPORT:
Battery systems can be exported as CHILDREN of PV arrays (coupled)
or as standalone elements (standalone battery storage).

ANNOTATION RESTORATION:
- Array type, tracking mode
- Module specifications
- Inverter configuration
- Battery coupling type

PATTERN: Composite exporter
"""

from typing import List
import xml.etree.ElementTree as ET
import logging

from eco_tools.core.internal_repr import PVArray, BatterySystem
from .base_exporter import BaseExporter

# Get module logger
logger = logging.getLogger('eco_tools.exporters')


class PVExporter(BaseExporter):
    """Exporter for CIBD22X PV array and battery system elements"""

    def __init__(self):
        super().__init__()

    def export_pv_systems(
        self,
        parent: ET.Element,
        pv_arrays: List[PVArray],
        battery_systems: List[BatterySystem]
    ) -> None:
        """
        Export all PV arrays with associated battery systems.

        Args:
            parent: Parent XML element (typically <Building>)
            pv_arrays: List of PVArray objects
            battery_systems: List of BatterySystem objects
        """
        if not pv_arrays and not battery_systems:
            logger.info("No PV/battery systems to export")
            return

        exported_arrays = 0
        exported_batteries = 0

        for pv_array in pv_arrays:
            pv_elem = self._export_pv_array(parent, pv_array)
            if pv_elem:
                exported_arrays += 1

                # Export battery systems coupled to this PV array
                coupled_batteries = [b for b in battery_systems if b.coupled_pv_array_ref == pv_array.id]
                for battery in coupled_batteries:
                    if self._export_battery_system(pv_elem, battery):
                        exported_batteries += 1

        # Export standalone battery systems (not coupled to PV)
        standalone_batteries = [b for b in battery_systems if not b.coupled_pv_array_ref]
        for battery in standalone_batteries:
            if self._export_battery_system(parent, battery):
                exported_batteries += 1

        logger.info(f"Exported {exported_arrays} PV arrays and {exported_batteries} battery systems")

    def _export_pv_array(self, parent: ET.Element, pv: PVArray) -> ET.Element:
        """Export a single PV array."""
        if not pv.name:
            logger.warning(f"Skipping PV array with missing name (id: {pv.id})")
            return None

        # Determine XML tag from annotation
        xml_tag = self.get_annotation(pv.annotation, 'xml_tag', 'ResPVSys')

        # Create PV array element
        pv_elem = self.create_element(parent, xml_tag)

        # Add name (required)
        self.add_text_element(pv_elem, 'Name', pv.name)

        # CRITICAL: Export CBECC-specific properties from annotations, not internal representation
        # The internal representation uses generic fields, but CBECC has specific property names
        # For round-trip fidelity, we must export the original CBECC properties

        if pv.annotation:
            # CBECC PV properties (varies by PV system type)
            annotation_props = [
                # System sizing
                'DCSysSize',           # DC system size (kW)
                'ACSysSize',           # AC system size (kW)
                'SysSize',             # Generic system size

                # Module specifications
                'ModuleType',          # Premium, Standard, etc.
                'Module',              # Module name/reference
                'PVModRef',            # Module reference

                # Inverter specifications
                'PwrElec',             # Microinverters, String Inverter, etc.
                'InverterType',        # Inverter type
                'InverterRef',         # Inverter reference

                # Array configuration
                'ArrayType',           # Array type (if present in CBECC file)
                'Orientation',         # Fixed, Tracking, etc.
                'Tracking',            # Tracking type
                'Tilt',                # Tilt angle
                'Az',                  # Azimuth angle

                # Module details
                'NumModules',          # Number of modules
                'ModulePower',         # Module power (W)

                # Performance
                'DCtoACRatio',         # DC to AC ratio
                'InverterEff',         # Inverter efficiency
                'SysLoss',             # System losses

                # Mounting
                'ArrayMount',          # Roof, ground, carport, etc.
                'RoofCondition'        # Roof condition
            ]

            for prop in annotation_props:
                value = self.get_annotation(pv.annotation, prop)
                if value:
                    self.add_text_element(pv_elem, prop, str(value))

        # Only export from internal representation if no annotation properties
        # This provides fallback for programmatically created PV arrays
        if not pv.annotation or not any(self.get_annotation(pv.annotation, p) for p in ['DCSysSize', 'ACSysSize', 'SysSize']):
            # System capacity (W → kW)
            if pv.rated_capacity_w is not None:
                capacity_kw = pv.rated_capacity_w / 1000.0
                self.add_numeric_element(pv_elem, 'RatedCap', capacity_kw, precision=2)

            # Module count
            if pv.num_modules:
                self.add_text_element(pv_elem, 'NumModules', str(pv.num_modules))

            # Module power (W)
            if pv.module_power_w is not None:
                self.add_numeric_element(pv_elem, 'ModulePower', pv.module_power_w, precision=1)

            # Array orientation
            if pv.tilt_deg is not None:
                self.add_numeric_element(pv_elem, 'Tilt', pv.tilt_deg, precision=1)

            if pv.azimuth_deg is not None:
                self.add_numeric_element(pv_elem, 'Az', pv.azimuth_deg, precision=1)

        return pv_elem

    def _export_battery_system(self, parent: ET.Element, battery: BatterySystem) -> bool:
        """Export a battery system (nested or standalone)."""
        if not battery.name:
            logger.warning(f"Skipping battery with missing name (id: {battery.id})")
            return False

        # Determine XML tag from annotation (Batt, ResBatt, etc.)
        xml_tag = self.get_annotation(battery.annotation, 'xml_tag', 'Batt')

        # Create battery element
        bat_elem = ET.SubElement(parent, xml_tag)

        # Add name
        self.add_text_element(bat_elem, 'Name', battery.name)

        # CRITICAL: Export CBECC-specific properties from annotations
        if battery.annotation:
            annotation_props = [
                # Capacity properties (CBECC uses different names)
                'MaxCap',              # Maximum capacity (kWh) - CBECC residential
                'UsableCapacity',      # Usable capacity (kWh) - CBECC commercial
                'RatedCapacity',       # Rated capacity (kWh)
                'NominalCap',          # Nominal capacity

                # Power properties
                'MaxPwr',              # Maximum power (kW)
                'RatedPower',          # Rated power (kW)

                # Control and operation
                'Ctrl',                # Control strategy (Time of Use, Self Consumption, etc.)
                'ControlStrategy',     # Alternative control property
                'DispatchStrategy',    # Dispatch strategy

                # Efficiency and performance
                'RoundTripEff',        # Round-trip efficiency
                'ChargingEff',         # Charging efficiency
                'DischargingEff',      # Discharging efficiency

                # Battery chemistry and type
                'BatteryType',         # Lithium-ion, Lead-acid, etc.
                'Chemistry',           # Battery chemistry

                # Installation
                'Location',            # Indoor, outdoor, etc.
                'Mounting'             # Wall-mounted, floor-mounted, etc.
            ]

            for prop in annotation_props:
                value = self.get_annotation(battery.annotation, prop)
                if value:
                    self.add_text_element(bat_elem, prop, str(value))

        # Only export from internal representation if no annotation properties
        # This provides fallback for programmatically created batteries
        if not battery.annotation or not any(self.get_annotation(battery.annotation, p) for p in ['MaxCap', 'UsableCapacity', 'RatedCapacity']):
            # Capacity (kWh)
            if battery.usable_capacity_kwh is not None:
                self.add_numeric_element(bat_elem, 'UsableCapacity', battery.usable_capacity_kwh, precision=2)

            if battery.rated_capacity_kwh is not None:
                self.add_numeric_element(bat_elem, 'RatedCapacity', battery.rated_capacity_kwh, precision=2)

            # Power (kW)
            if battery.rated_power_kw is not None:
                self.add_numeric_element(bat_elem, 'RatedPower', battery.rated_power_kw, precision=2)

            # Efficiency
            if battery.round_trip_efficiency is not None:
                self.add_numeric_element(bat_elem, 'RoundTripEfficiency', battery.round_trip_efficiency, precision=3)

        return True
