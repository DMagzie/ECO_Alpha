"""
Parser for CBECC HVACSecondary.csv output files.

Extracts HVAC system specifications including:
- Air Systems (SZHP, VRF, PVAV, etc.)
- Zone Systems
- Terminal Units
- Cooling Coils (with SEER, EER)
- Heating Coils (with HSPF, COP, AFUE)
- Fans
- Outside Air Control
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, List, Dict, Any
import logging

from .cbecc_csv_base import CebeccCsvParser, CebeccSection

logger = logging.getLogger(__name__)


@dataclass
class AirSystem:
    """HVAC air system specification."""
    name: str
    system_type: str  # SZHP, VRF, PVAV, SZAC, SZVAVHP, etc.
    status: str  # New, Existing, Altered
    system_count: int
    floor_area_served_sf: float
    cooling_capacity_btuh: Optional[float] = None
    cooling_design_supply_temp_f: Optional[float] = None
    heating_capacity_btuh: Optional[float] = None
    heating_design_supply_temp_f: Optional[float] = None
    supply_flow_cfm: Optional[float] = None
    design_oa_cfm: Optional[float] = None
    control_zone_name: Optional[str] = None
    availability_schedule: Optional[str] = None


@dataclass
class ZoneSystem:
    """Zone-level HVAC system specification."""
    name: str
    system_type: str  # Exhaust, etc.
    system_count: int
    floor_area_served_sf: float
    cooling_capacity_btuh: Optional[float] = None
    heating_capacity_btuh: Optional[float] = None
    supply_flow_cfm: Optional[float] = None


@dataclass
class TerminalUnit:
    """Terminal unit specification."""
    name: str
    unit_type: str  # Uncontrolled, VAVNoReheatBox, VAVReheatBox, etc.
    status: str
    quantity: int
    air_system: str
    zone_name: str
    floor_area_sf: float
    primary_max_cfm: Optional[float] = None
    primary_min_cfm: Optional[float] = None


@dataclass
class CoolingCoil:
    """Cooling coil specification."""
    name: str
    coil_type: str  # DirectExpansion, ChilledWater
    status: str
    fuel_source: str  # Electric
    air_system: str
    system_count: int
    capacity_net_btuh: float
    capacity_gross_btuh: Optional[float] = None
    condenser_type: Optional[str] = None  # Air, Water
    num_stages: Optional[int] = None
    seer: Optional[float] = None
    seer_code_min: Optional[float] = None
    eer: Optional[float] = None
    eer_code_min: Optional[float] = None
    ieer: Optional[float] = None
    seer2: Optional[float] = None
    eer2: Optional[float] = None


@dataclass
class HeatingCoil:
    """Heating coil specification."""
    name: str
    coil_type: str  # HeatPump, Furnace, Resistance, HotWater
    status: str
    fuel_source: str  # Electric, Gas
    air_system: str
    system_count: int
    capacity_net_btuh: float
    capacity_gross_btuh: Optional[float] = None
    condenser_type: Optional[str] = None  # Air, Water
    num_stages: Optional[int] = None
    hspf: Optional[float] = None
    hspf_code_min: Optional[float] = None
    cop: Optional[float] = None
    cop_code_min: Optional[float] = None
    afue: Optional[float] = None
    afue_code_min: Optional[float] = None
    thermal_efficiency: Optional[float] = None
    hspf2: Optional[float] = None


@dataclass
class Fan:
    """Fan specification."""
    name: str
    control_method: str  # ConstantVolume, VariableSpeedDrive
    status: str
    fan_class: str  # Centrifugal, Axial
    air_system: str
    system_count: int
    max_flow_cfm: float
    min_flow_cfm: Optional[float] = None
    efficiency: Optional[float] = None
    brake_hp: Optional[float] = None
    nameplate_hp: Optional[float] = None
    motor_efficiency: Optional[float] = None


@dataclass
class OutsideAirControl:
    """Outside air control specification."""
    name: str
    control_type: str  # NoEconomizer, FixedDryBulb, etc.
    status: str
    design_oa_cfm: float
    air_system: str
    system_count: int
    economizer_integration: Optional[str] = None
    max_oa_ratio: Optional[float] = None


@dataclass
class HVACSecondaryOutput:
    """Complete parsed output from HVACSecondary.csv."""
    air_systems: List[AirSystem] = field(default_factory=list)
    zone_systems: List[ZoneSystem] = field(default_factory=list)
    terminal_units: List[TerminalUnit] = field(default_factory=list)
    cooling_coils: List[CoolingCoil] = field(default_factory=list)
    heating_coils: List[HeatingCoil] = field(default_factory=list)
    fans: List[Fan] = field(default_factory=list)
    oa_controls: List[OutsideAirControl] = field(default_factory=list)

    # Summary metrics
    @property
    def total_cooling_capacity_btuh(self) -> float:
        """Total cooling capacity across all coils."""
        return sum(c.capacity_net_btuh for c in self.cooling_coils if c.capacity_net_btuh)

    @property
    def total_cooling_capacity_tons(self) -> float:
        """Total cooling capacity in tons."""
        return self.total_cooling_capacity_btuh / 12000

    @property
    def total_heating_capacity_btuh(self) -> float:
        """Total heating capacity across all coils."""
        return sum(c.capacity_net_btuh for c in self.heating_coils if c.capacity_net_btuh)

    @property
    def total_system_count(self) -> int:
        """Total number of air systems (accounting for multiples)."""
        return sum(s.system_count for s in self.air_systems)

    @property
    def average_seer(self) -> Optional[float]:
        """Capacity-weighted average SEER."""
        seers = [(c.seer, c.capacity_net_btuh) for c in self.cooling_coils
                 if c.seer and c.capacity_net_btuh]
        if not seers:
            return None
        total_cap = sum(cap for _, cap in seers)
        weighted_sum = sum(seer * cap for seer, cap in seers)
        return weighted_sum / total_cap if total_cap > 0 else None

    @property
    def average_hspf(self) -> Optional[float]:
        """Capacity-weighted average HSPF."""
        hspfs = [(c.hspf, c.capacity_net_btuh) for c in self.heating_coils
                 if c.hspf and c.capacity_net_btuh and c.coil_type == 'HeatPump']
        if not hspfs:
            return None
        total_cap = sum(cap for _, cap in hspfs)
        weighted_sum = sum(hspf * cap for hspf, cap in hspfs)
        return weighted_sum / total_cap if total_cap > 0 else None


class HVACSecondaryParser(CebeccCsvParser):
    """Parser for HVACSecondary.csv files."""

    # Section name mappings (handle variations)
    SECTION_ALIASES = {
        'airsystems': 'AirSystems',
        'air systems': 'AirSystems',
        'zonesystems': 'ZoneSystems',
        'zone systems': 'ZoneSystems',
        'terminal units': 'TerminalUnits',
        'terminalunits': 'TerminalUnits',
        'cooling coils': 'CoolingCoils',
        'coolingcoils': 'CoolingCoils',
        'heating coils': 'HeatingCoils',
        'heatingcoils': 'HeatingCoils',
        'fans': 'Fans',
        'outside air control': 'OutsideAirControl',
        'outsideaircontrol': 'OutsideAirControl',
    }

    def parse_file(self, filepath: Path) -> HVACSecondaryOutput:
        """
        Parse HVACSecondary.csv and return structured output.

        Args:
            filepath: Path to HVACSecondary.csv

        Returns:
            HVACSecondaryOutput with all parsed components
        """
        # Parse sections using base class
        sections = super().parse_file(filepath)

        # Create output
        output = HVACSecondaryOutput()

        # Parse each section
        output.air_systems = self._parse_air_systems(sections)
        output.zone_systems = self._parse_zone_systems(sections)
        output.terminal_units = self._parse_terminal_units(sections)
        output.cooling_coils = self._parse_cooling_coils(sections)
        output.heating_coils = self._parse_heating_coils(sections)
        output.fans = self._parse_fans(sections)
        output.oa_controls = self._parse_oa_controls(sections)

        return output

    def _get_section(self, sections: Dict[str, CebeccSection], name: str) -> Optional[CebeccSection]:
        """Get a section by name, handling aliases."""
        # Try exact match first
        if name in sections:
            return sections[name]

        # Try aliases
        name_lower = name.lower()
        if name_lower in self.SECTION_ALIASES:
            canonical = self.SECTION_ALIASES[name_lower]
            if canonical in sections:
                return sections[canonical]

        # Try case-insensitive match
        for section_name, section in sections.items():
            if section_name.lower() == name_lower:
                return section

        return None

    def _parse_air_systems(self, sections: Dict[str, CebeccSection]) -> List[AirSystem]:
        """Parse AirSystems section."""
        section = self._get_section(sections, 'AirSystems')
        if not section:
            return []

        systems = []
        for row in section.data:
            try:
                system = AirSystem(
                    name=self._get_str(row, 'Name', ''),
                    system_type=self._get_str(row, 'Type', ''),
                    status=self._get_str(row, 'Status', 'New'),
                    system_count=self._get_int(row, 'System Count', 1),
                    floor_area_served_sf=self._get_float(row, 'Floor Area Served', 0),
                    cooling_capacity_btuh=self._get_float(row, 'Net Capacity'),  # First one is cooling
                    cooling_design_supply_temp_f=self._get_float(row, 'Design Supply T'),
                    supply_flow_cfm=self._get_float(row, 'Supply Flow'),
                    design_oa_cfm=self._get_float(row, 'Design OA'),
                    control_zone_name=self._get_str(row, 'Control Zone Name'),
                    availability_schedule=self._get_str(row, 'Availability Schedule'),
                )

                # Handle heating capacity (second "Net Capacity" column)
                # The CSV has two "Net Capacity" columns - one for cooling, one for heating
                # We need to look at the raw column positions
                if 'col_9' in row:  # Heating Net Capacity is typically column 9
                    system.heating_capacity_btuh = self._clean_numeric(row.get('col_9'))
                elif 'Capacity' in str(row):
                    # Try to find heating capacity from column name patterns
                    for key, val in row.items():
                        if 'heating' in key.lower() and 'capacity' in key.lower():
                            system.heating_capacity_btuh = self._clean_numeric(val)
                            break

                if system.name:
                    systems.append(system)

            except Exception as e:
                logger.warning(f"Error parsing air system row: {e}")

        return systems

    def _parse_zone_systems(self, sections: Dict[str, CebeccSection]) -> List[ZoneSystem]:
        """Parse ZoneSystems section."""
        section = self._get_section(sections, 'ZoneSystems')
        if not section:
            return []

        systems = []
        for row in section.data:
            try:
                system = ZoneSystem(
                    name=self._get_str(row, 'Name', ''),
                    system_type=self._get_str(row, 'Type', ''),
                    system_count=self._get_int(row, 'System Count', 1),
                    floor_area_served_sf=self._get_float(row, 'Floor Area Served', 0),
                    cooling_capacity_btuh=self._get_float(row, 'Net Capacity'),
                    supply_flow_cfm=self._get_float(row, 'Supply Flow'),
                )
                if system.name:
                    systems.append(system)
            except Exception as e:
                logger.warning(f"Error parsing zone system row: {e}")

        return systems

    def _parse_terminal_units(self, sections: Dict[str, CebeccSection]) -> List[TerminalUnit]:
        """Parse Terminal Units section."""
        section = self._get_section(sections, 'Terminal Units')
        if not section:
            return []

        units = []
        for row in section.data:
            try:
                unit = TerminalUnit(
                    name=self._get_str(row, 'Name', ''),
                    unit_type=self._get_str(row, 'Type', ''),
                    status=self._get_str(row, 'Status', 'New'),
                    quantity=self._get_int(row, 'Qty', 1),
                    air_system=self._get_str(row, 'System', ''),
                    zone_name=self._get_str(row, 'Zone', ''),
                    floor_area_sf=self._get_float(row, 'Floor Area', 0),
                    primary_max_cfm=self._get_float(row, 'Primary Max'),
                    primary_min_cfm=self._get_float(row, 'Primary Min'),
                )
                if unit.name:
                    units.append(unit)
            except Exception as e:
                logger.warning(f"Error parsing terminal unit row: {e}")

        return units

    def _parse_cooling_coils(self, sections: Dict[str, CebeccSection]) -> List[CoolingCoil]:
        """Parse Cooling Coils section."""
        section = self._get_section(sections, 'Cooling Coils')
        if not section:
            return []

        coils = []
        for row in section.data:
            try:
                coil = CoolingCoil(
                    name=self._get_str(row, 'Name', ''),
                    coil_type=self._get_str(row, 'Type', ''),
                    status=self._get_str(row, 'Status', 'New'),
                    fuel_source=self._get_str(row, 'Fuel Src', 'Electric'),
                    air_system=self._get_str(row, 'System', ''),
                    system_count=self._get_int(row, 'System Qty', 1),
                    capacity_net_btuh=self._get_float(row, 'Total-Net', 0),
                    capacity_gross_btuh=self._get_float(row, 'Total-Gross'),
                    condenser_type=self._get_str(row, 'Condenser Type'),
                    num_stages=self._get_int(row, 'Number Stages'),
                    seer=self._get_float(row, 'SEER (rounded)'),
                    seer_code_min=self._get_float(row, 'CodeMin SEER'),
                    eer=self._get_float(row, 'EER (rounded)'),
                    eer_code_min=self._get_float(row, 'CodeMin EER'),
                    ieer=self._get_float(row, 'IEER (roundded)'),  # Note: typo in CBECC
                    seer2=self._get_float(row, 'SEER2 (rounded)'),
                    eer2=self._get_float(row, 'EER2 (rounded)'),
                )
                if coil.name:
                    coils.append(coil)
            except Exception as e:
                logger.warning(f"Error parsing cooling coil row: {e}")

        return coils

    def _parse_heating_coils(self, sections: Dict[str, CebeccSection]) -> List[HeatingCoil]:
        """Parse Heating Coils section."""
        section = self._get_section(sections, 'Heating Coils')
        if not section:
            return []

        coils = []
        for row in section.data:
            try:
                coil = HeatingCoil(
                    name=self._get_str(row, 'Name', ''),
                    coil_type=self._get_str(row, 'Type', ''),
                    status=self._get_str(row, 'Status', 'New'),
                    fuel_source=self._get_str(row, 'Fuel Src', 'Electric'),
                    air_system=self._get_str(row, 'System', ''),
                    system_count=self._get_int(row, 'System Qty', 1),
                    capacity_net_btuh=self._get_float(row, 'Total-Net', 0),
                    capacity_gross_btuh=self._get_float(row, 'Total-Gross'),
                    condenser_type=self._get_str(row, 'Condenser Type'),
                    num_stages=self._get_int(row, 'Number Stages'),
                    hspf=self._get_float(row, 'HSPF (rounded)'),
                    hspf_code_min=self._get_float(row, 'CodeMin HSPF'),
                    cop=self._get_float(row, 'COP (rounded)'),
                    cop_code_min=self._get_float(row, 'CodeMin COP'),
                    afue=self._get_float(row, 'AFUE'),
                    afue_code_min=self._get_float(row, 'CodeMin AFUE'),
                    thermal_efficiency=self._get_float(row, 'Thrml Eff'),
                    hspf2=self._get_float(row, 'HSPF2 (rounded)'),
                )
                if coil.name:
                    coils.append(coil)
            except Exception as e:
                logger.warning(f"Error parsing heating coil row: {e}")

        return coils

    def _parse_fans(self, sections: Dict[str, CebeccSection]) -> List[Fan]:
        """Parse Fans section."""
        section = self._get_section(sections, 'Fans')
        if not section:
            return []

        fans = []
        for row in section.data:
            try:
                fan = Fan(
                    name=self._get_str(row, 'Name', ''),
                    control_method=self._get_str(row, 'Control Method', ''),
                    status=self._get_str(row, 'Status', 'New'),
                    fan_class=self._get_str(row, 'Class', ''),
                    air_system=self._get_str(row, 'System', ''),
                    system_count=self._get_int(row, 'System Qty', 1),
                    max_flow_cfm=self._get_float(row, 'Maximum', 0),
                    min_flow_cfm=self._get_float(row, 'Minimum'),
                    efficiency=self._get_float(row, 'Efficiency'),
                    brake_hp=self._get_float(row, 'Brake HP'),
                    nameplate_hp=self._get_float(row, 'Nameplate HP'),
                    motor_efficiency=self._get_float(row, 'Motor Efficiency') or
                                     self._get_float(row, 'col_17'),  # Fallback to column index
                )
                if fan.name:
                    fans.append(fan)
            except Exception as e:
                logger.warning(f"Error parsing fan row: {e}")

        return fans

    def _parse_oa_controls(self, sections: Dict[str, CebeccSection]) -> List[OutsideAirControl]:
        """Parse Outside Air Control section."""
        section = self._get_section(sections, 'Outside Air Control')
        if not section:
            return []

        controls = []
        for row in section.data:
            try:
                ctrl = OutsideAirControl(
                    name=self._get_str(row, 'Name', ''),
                    control_type=self._get_str(row, 'Control', ''),
                    status=self._get_str(row, 'Status', 'New'),
                    design_oa_cfm=self._get_float(row, 'Design OA', 0),
                    air_system=self._get_str(row, 'Name', ''),  # Uses different column name
                    system_count=self._get_int(row, 'System Count', 1),
                    economizer_integration=self._get_str(row, 'Econo Integration'),
                    max_oa_ratio=self._get_float(row, 'Max OA Ratio'),
                )
                if ctrl.name:
                    controls.append(ctrl)
            except Exception as e:
                logger.warning(f"Error parsing OA control row: {e}")

        return controls

    # Helper methods for safe value extraction
    def _get_str(self, row: Dict[str, Any], key: str, default: str = None) -> Optional[str]:
        """Get string value from row, handling missing values."""
        val = row.get(key)
        if val is None:
            # Try case-insensitive match
            for k, v in row.items():
                if k.lower() == key.lower():
                    val = v
                    break
        if val is None or val == '' or val == 'NONE':
            return default
        return str(val)

    def _get_float(self, row: Dict[str, Any], key: str, default: float = None) -> Optional[float]:
        """Get float value from row, handling missing values."""
        val = row.get(key)
        if val is None:
            # Try case-insensitive match
            for k, v in row.items():
                if k.lower() == key.lower():
                    val = v
                    break
        return self._clean_numeric(val) if val is not None else default

    def _get_int(self, row: Dict[str, Any], key: str, default: int = None) -> Optional[int]:
        """Get int value from row."""
        val = self._get_float(row, key)
        return int(val) if val is not None else default

    def _clean_numeric(self, val: Any) -> Optional[float]:
        """Clean a numeric value, handling CBECC missing indicator."""
        if val is None:
            return None
        if isinstance(val, (int, float)):
            if val == self.MISSING_VALUE:
                return None
            return float(val)
        try:
            num = float(str(val).replace(',', ''))
            if num == self.MISSING_VALUE:
                return None
            return num
        except (ValueError, TypeError):
            return None


def parse_hvac_secondary(filepath: Path) -> HVACSecondaryOutput:
    """
    Parse a HVACSecondary.csv file.

    Args:
        filepath: Path to the CSV file

    Returns:
        HVACSecondaryOutput with all parsed components
    """
    parser = HVACSecondaryParser()
    return parser.parse_file(filepath)
