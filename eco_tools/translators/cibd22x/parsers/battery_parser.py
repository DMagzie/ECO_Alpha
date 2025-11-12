"""
BatterySystem Parser - Sub-Parser (Used by PVArrayParser)
=========================================================

PURPOSE: Extracts battery storage systems nested within PV arrays.
This is a SUB-PARSER called by PVArrayParser (composite parser).

PATTERN: Sub-Parser - Called by composite parent, not directly by importer.

KEY OPERATIONS:
- Parse battery capacity (kWh) and power rating (kW)
- Extract efficiency and control strategy
- Parse state of charge (SOC) limits
- Link to parent PV array

USAGE: Only called by PVArrayParser.parse_pv_arrays()
"""

from typing import Optional
import xml.etree.ElementTree as ET
import logging

from eco_tools.core.internal_repr import BatterySystem
from eco_tools.core.id_registry import IDRegistry
from .base_parser import BaseParser

# Get module logger
logger = logging.getLogger('eco_tools.parsers')


class BatterySystemParser(BaseParser):
    """Parser for CIBD22X battery system elements"""

    BATTERY_SYSTEM_TAGS = [
        'BatterySystem',  # Battery systems within PV arrays
        'BatterySys',     # Standalone battery systems
    ]

    def __init__(self, id_registry: IDRegistry):
        super().__init__()
        self.id_registry = id_registry

    def parse_battery_system(self, battery_elem: ET.Element, pv_array_id: Optional[str] = None) -> Optional[BatterySystem]:
        """
        Parse a single battery energy storage system.

        Args:
            battery_elem: Battery system XML element
            pv_array_id: Optional parent PV array ID for coupled systems

        Returns:
            BatterySystem object or None if parsing fails
        """
        name = self._get_name(battery_elem)
        if not name:
            return None

        battery_id = self.id_registry.generate_id('BAT', name, pv_array_id or '', 'CIBD22X')

        # Battery type
        battery_type = self.get_property(battery_elem, 'BatteryType')
        if not battery_type:
            battery_type = self.get_property(battery_elem, 'Type') or 'LithiumIon'

        # Capacity
        usable_capacity_kwh = self._to_float(self.get_property(battery_elem, 'UsableCapacity'))
        rated_capacity_kwh = self._to_float(self.get_property(battery_elem, 'RatedCapacity'))
        if not rated_capacity_kwh:
            rated_capacity_kwh = self._to_float(self.get_property(battery_elem, 'TotalCapacity'))

        rated_power_kw = self._to_float(self.get_property(battery_elem, 'RatedPower'))
        if not rated_power_kw:
            rated_power_kw = self._to_float(self.get_property(battery_elem, 'MaxDischargePower'))

        # Efficiency
        round_trip_eff = self._to_float(self.get_property(battery_elem, 'RoundTripEfficiency'))
        if not round_trip_eff:
            round_trip_eff = self._to_float(self.get_property(battery_elem, 'Efficiency'))

        charge_eff = self._to_float(self.get_property(battery_elem, 'ChargeEfficiency'))
        discharge_eff = self._to_float(self.get_property(battery_elem, 'DischargeEfficiency'))

        # Control
        control_strategy = self.get_property(battery_elem, 'ControlStrategy')
        max_charge_rate = self._to_float(self.get_property(battery_elem, 'MaxChargeRate'))
        max_discharge_rate = self._to_float(self.get_property(battery_elem, 'MaxDischargeRate'))

        # Depth of discharge
        min_soc = self._to_float(self.get_property(battery_elem, 'MinSOC'))
        max_soc = self._to_float(self.get_property(battery_elem, 'MaxSOC'))

        # Integration
        coupling_type = self.get_property(battery_elem, 'CouplingType')
        coupled_pv_array_ref = pv_array_id if pv_array_id else self.get_property(battery_elem, 'PVArrayRef')

        # Installation
        location = self.get_property(battery_elem, 'Location')

        # Build annotation with CBECC-specific properties
        # Extract XML tag to preserve element name (Batt, ResBatt, etc.)
        tag = self._local_tag(battery_elem.tag)
        annotation = {'xml_tag': tag}

        # CRITICAL: Store ALL CBECC-specific properties for round-trip export
        additional_props = [
            # Capacity (CBECC uses different property names)
            'MaxCap',              # Maximum capacity (kWh) - CBECC residential
            'NominalCap',          # Nominal capacity

            # Power
            'MaxPwr',              # Maximum power (kW)

            # Control (CBECC-specific)
            'Ctrl',                # Control strategy - IMPORTANT for CBECC
            'DispatchStrategy',    # Dispatch strategy

            # Efficiency
            'RoundTripEff',        # Round-trip efficiency
            'ChargingEff',         # Charging efficiency
            'DischargingEff',      # Discharging efficiency

            # Battery specifications
            'Chemistry',           # Battery chemistry
            'Warranty',            # Warranty years
            'CycleLife',           # Cycle life

            # Installation and configuration
            'Mounting',            # Mounting type
            'Enclosure',           # Enclosure type
            'Ventilation'          # Ventilation requirements
        ]

        for prop in additional_props:
            value = self.get_property(battery_elem, prop)
            if value:
                annotation[prop] = value

        battery = BatterySystem(
            id=battery_id,
            name=name,
            battery_type=battery_type,
            usable_capacity_kwh=usable_capacity_kwh,
            rated_capacity_kwh=rated_capacity_kwh,
            rated_power_kw=rated_power_kw,
            round_trip_efficiency=round_trip_eff,
            charge_efficiency=charge_eff,
            discharge_efficiency=discharge_eff,
            control_strategy=control_strategy,
            max_charge_rate_kw=max_charge_rate,
            max_discharge_rate_kw=max_discharge_rate,
            min_state_of_charge=min_soc,
            max_state_of_charge=max_soc,
            coupled_pv_array_ref=coupled_pv_array_ref,
            coupling_type=coupling_type,
            location=location,
            annotation=annotation
        )

        return battery

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
