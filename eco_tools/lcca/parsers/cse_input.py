"""
Parser for CBECC CSE input files (.cse).

Extracts DHW equipment specifications from CSE simulation input files:
- DHWHEATER: Water heater specifications (type, fuel, capacity, efficiency)
- DHWTANK: Separate storage tank specifications
- DHWSYS: DHW system configuration
- DHWLOOP: Recirculation loop details

These files provide detailed equipment specs that may not be fully
represented in the HVACPrimary.csv output files.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Dict, Optional, Any
import logging
import re

logger = logging.getLogger(__name__)


@dataclass
class CSEDHWHeater:
    """DHW heater from CSE input file."""
    name: str
    heater_type: str = ''  # BuiltUp, SmallStorage, LargeStorage, LargeInstantaneous, SmallInstantaneous
    heat_source: str = ''  # ASHPX, Fuel, Electricity, ResistanceX
    ashp_type: Optional[str] = None  # GE2012, Rheem2020Prem65, Scalable_SP, SandenGS3
    multiplier: int = 1  # Number of units
    efficiency: Optional[float] = None  # whEff - thermal efficiency
    volume_gal: Optional[float] = None  # Tank volume
    insulation_r: Optional[float] = None  # Tank insulation R-value
    heating_cap_btuh: Optional[float] = None  # Compressor output capacity
    tank_count: Optional[float] = None  # Number of tanks per compressor
    resistance_power_w: Optional[float] = None  # Resistance backup power
    resistance_power_lower_w: Optional[float] = None  # Lower element power
    fuel_meter: Optional[str] = None  # MtrNatGas, etc.

    @property
    def is_heat_pump(self) -> bool:
        """Check if this is a heat pump water heater."""
        return self.heat_source == 'ASHPX'

    @property
    def is_gas(self) -> bool:
        """Check if this is a gas water heater."""
        return self.heat_source == 'Fuel'

    @property
    def is_electric_resistance(self) -> bool:
        """Check if this is an electric resistance water heater."""
        return self.heat_source in ('Electricity', 'ResistanceX')

    @property
    def total_volume_gal(self) -> float:
        """Calculate total tank volume including multiplier."""
        vol = self.volume_gal or 0.0
        return vol * self.multiplier


@dataclass
class CSEDHWTank:
    """Separate DHW storage tank from CSE input file."""
    name: str
    multiplier: int = 1
    volume_gal: float = 0.0
    insulation_r: Optional[float] = None
    tank_temp_f: Optional[float] = None  # Average tank temperature
    extra_loss_btuh: Optional[float] = None  # Additional heat loss

    @property
    def total_volume_gal(self) -> float:
        """Calculate total tank volume including multiplier."""
        return self.volume_gal * self.multiplier


@dataclass
class CSEDHWLoop:
    """DHW recirculation loop from CSE input file."""
    name: str
    multiplier: int = 1
    flow_gpm: Optional[float] = None  # Loop flow rate
    run_fraction: Optional[float] = None  # Fraction of time running
    pump_power_w: Optional[float] = None  # Loop pump power


@dataclass
class CSEDHWSystem:
    """DHW system from CSE input file."""
    name: str
    use_temp_f: Optional[float] = None  # Water use temperature
    setpoint_temp_f: Optional[float] = None  # Tank setpoint
    loop_heater_setpoint_f: Optional[float] = None  # Loop heater setpoint
    distribution_loss_mult: Optional[float] = None  # SDLM
    branch_model: Optional[str] = None  # DayWaste, etc.
    heaters: List[CSEDHWHeater] = field(default_factory=list)  # Child heaters
    tanks: List[CSEDHWTank] = field(default_factory=list)  # Child tanks
    loops: List[CSEDHWLoop] = field(default_factory=list)  # Child loops


@dataclass
class CSEInputOutput:
    """Complete output from CSE input file parsing."""
    filepath: str = ''

    # DHW Components
    dhw_heaters: List[CSEDHWHeater] = field(default_factory=list)
    dhw_tanks: List[CSEDHWTank] = field(default_factory=list)
    dhw_systems: List[CSEDHWSystem] = field(default_factory=list)
    dhw_loops: List[CSEDHWLoop] = field(default_factory=list)

    # Aggregated DHW metrics
    total_heater_count: int = 0
    total_tank_volume_gal: float = 0.0
    total_heating_capacity_btuh: float = 0.0

    # DHW type breakdown
    heat_pump_count: int = 0
    gas_heater_count: int = 0
    electric_resistance_count: int = 0

    # ASHP types found
    ashp_types: List[str] = field(default_factory=list)

    def calculate_totals(self):
        """Calculate aggregate totals from parsed data."""
        self.total_heater_count = sum(h.multiplier for h in self.dhw_heaters)
        self.total_tank_volume_gal = sum(h.total_volume_gal for h in self.dhw_heaters)
        self.total_tank_volume_gal += sum(t.total_volume_gal for t in self.dhw_tanks)

        self.total_heating_capacity_btuh = sum(
            (h.heating_cap_btuh or 0.0) * h.multiplier
            for h in self.dhw_heaters
        )

        # Type breakdown
        self.heat_pump_count = sum(h.multiplier for h in self.dhw_heaters if h.is_heat_pump)
        self.gas_heater_count = sum(h.multiplier for h in self.dhw_heaters if h.is_gas)
        self.electric_resistance_count = sum(
            h.multiplier for h in self.dhw_heaters if h.is_electric_resistance
        )

        # Collect ASHP types
        self.ashp_types = list(set(
            h.ashp_type for h in self.dhw_heaters
            if h.ashp_type is not None
        ))


class CSEInputParser:
    """Parser for CBECC CSE input files (.cse)."""

    # Block types to parse
    DHW_BLOCK_TYPES = {
        'DHWHEATER', 'DHWTANK', 'DHWSYS', 'DHWLOOP',
        'DHWLOOPHEATER', 'DHWLOOPPUMP', 'DHWLOOPSEG', 'DHWLOOPBRANCH'
    }

    # Parameter mappings for each block type
    HEATER_PARAMS = {
        'whType': 'heater_type',
        'whHeatSrc': 'heat_source',
        'whASHPType': 'ashp_type',
        'whMult': 'multiplier',
        'whEff': 'efficiency',
        'whVol': 'volume_gal',
        'whInsulR': 'insulation_r',
        'whHeatingCap': 'heating_cap_btuh',
        'whTankCount': 'tank_count',
        'whResHtPwr': 'resistance_power_w',
        'whResHtPwr2': 'resistance_power_lower_w',
        'whFuelMtr': 'fuel_meter',
    }

    TANK_PARAMS = {
        'wtMult': 'multiplier',
        'wtVol': 'volume_gal',
        'wtInsulR': 'insulation_r',
        'wtTTank': 'tank_temp_f',
        'wtXLoss': 'extra_loss_btuh',
    }

    SYSTEM_PARAMS = {
        'wsTUse': 'use_temp_f',
        'wsTSetpoint': 'setpoint_temp_f',
        'wsTSetPointLH': 'loop_heater_setpoint_f',
        'wsSDLM': 'distribution_loss_mult',
        'wsBranchModel': 'branch_model',
    }

    LOOP_PARAMS = {
        'wlMult': 'multiplier',
        'wlFlow': 'flow_gpm',
        'wlRunF': 'run_fraction',
    }

    def __init__(self):
        self.output = CSEInputOutput()
        self.parse_errors: List[str] = []
        self.parse_warnings: List[str] = []

        # Regex patterns
        self._block_pattern = re.compile(
            r'^\s*(DHWHEATER|DHWTANK|DHWSYS|DHWLOOP|DHWLOOPHEATER|DHWLOOPPUMP)\s+"([^"]+)"',
            re.MULTILINE
        )
        self._param_pattern = re.compile(
            r'^\s+(\w+)\s*=\s*(.+?)\s*(?://.*)?$'
        )

    def parse_file(self, filepath: Path) -> CSEInputOutput:
        """
        Parse CSE input file and return structured output.

        Args:
            filepath: Path to .cse file

        Returns:
            CSEInputOutput with all parsed DHW components
        """
        filepath = Path(filepath)
        if not filepath.exists():
            raise FileNotFoundError(f"File not found: {filepath}")

        # Reset state
        self.output = CSEInputOutput(filepath=str(filepath))
        self.parse_errors = []
        self.parse_warnings = []

        try:
            # Read file with encoding fallback
            content = self._read_file(filepath)
            self._parse_content(content)
            self.output.calculate_totals()

        except Exception as e:
            self.parse_errors.append(f"Failed to parse file: {e}")
            logger.error(f"Error parsing CSE file {filepath}: {e}")

        return self.output

    def _read_file(self, filepath: Path) -> str:
        """Read file with encoding fallback."""
        encodings = ['utf-8', 'latin-1', 'cp1252']
        for encoding in encodings:
            try:
                with open(filepath, 'r', encoding=encoding, errors='replace') as f:
                    return f.read()
            except UnicodeDecodeError:
                continue

        # Last resort - binary read
        with open(filepath, 'rb') as f:
            return f.read().decode('utf-8', errors='replace')

    def _parse_content(self, content: str) -> None:
        """Parse file content to extract DHW blocks."""
        lines = content.split('\n')

        i = 0
        current_system: Optional[CSEDHWSystem] = None

        while i < len(lines):
            line = lines[i]

            # Check for block start
            block_match = self._block_pattern.match(line)
            if block_match:
                block_type = block_match.group(1)
                block_name = block_match.group(2)

                # Collect parameters for this block
                params = {}
                i += 1
                while i < len(lines):
                    param_line = lines[i]

                    # Check if we've reached end of block (new block or empty line with no indent)
                    if self._block_pattern.match(param_line):
                        i -= 1  # Back up so main loop can process this block
                        break

                    # Check for parameter
                    param_match = self._param_pattern.match(param_line)
                    if param_match:
                        param_name = param_match.group(1)
                        param_value = param_match.group(2).strip()
                        params[param_name] = self._parse_value(param_value)

                    i += 1

                # Create appropriate object
                obj = self._create_object(block_type, block_name, params)
                if obj:
                    self._add_object(obj, block_type, current_system)
                    if block_type == 'DHWSYS':
                        current_system = obj

            i += 1

    def _parse_value(self, value_str: str) -> Any:
        """Parse a parameter value string."""
        value_str = value_str.strip()

        # Remove trailing comment if present
        if '//' in value_str:
            value_str = value_str.split('//')[0].strip()

        # Handle quoted strings
        if value_str.startswith('"') and value_str.endswith('"'):
            return value_str[1:-1]

        # Handle numeric values
        try:
            if '.' in value_str:
                return float(value_str)
            return int(value_str)
        except ValueError:
            pass

        # Handle expressions (return as string for now)
        return value_str

    def _create_object(self, block_type: str, name: str, params: Dict) -> Optional[Any]:
        """Create appropriate dataclass object from parsed block."""
        try:
            if block_type == 'DHWHEATER' or block_type == 'DHWLOOPHEATER':
                return self._create_heater(name, params)
            elif block_type == 'DHWTANK':
                return self._create_tank(name, params)
            elif block_type == 'DHWSYS':
                return self._create_system(name, params)
            elif block_type == 'DHWLOOP':
                return self._create_loop(name, params)
            elif block_type == 'DHWLOOPPUMP':
                return self._create_loop_pump(name, params)
        except Exception as e:
            self.parse_warnings.append(f"Error creating {block_type} '{name}': {e}")

        return None

    def _create_heater(self, name: str, params: Dict) -> CSEDHWHeater:
        """Create DHW heater from parameters."""
        heater = CSEDHWHeater(name=name)

        for cse_param, attr_name in self.HEATER_PARAMS.items():
            if cse_param in params:
                value = params[cse_param]
                # Handle type conversions
                if attr_name == 'multiplier':
                    value = int(value) if isinstance(value, (int, float)) else 1
                elif attr_name in ('efficiency', 'volume_gal', 'insulation_r',
                                   'heating_cap_btuh', 'tank_count'):
                    value = float(value) if isinstance(value, (int, float)) else None
                elif attr_name in ('resistance_power_w', 'resistance_power_lower_w'):
                    value = float(value) if isinstance(value, (int, float)) else None

                setattr(heater, attr_name, value)

        return heater

    def _create_tank(self, name: str, params: Dict) -> CSEDHWTank:
        """Create DHW tank from parameters."""
        tank = CSEDHWTank(name=name)

        for cse_param, attr_name in self.TANK_PARAMS.items():
            if cse_param in params:
                value = params[cse_param]
                if attr_name == 'multiplier':
                    value = int(value) if isinstance(value, (int, float)) else 1
                elif attr_name in ('volume_gal', 'insulation_r', 'tank_temp_f', 'extra_loss_btuh'):
                    value = float(value) if isinstance(value, (int, float)) else 0.0

                setattr(tank, attr_name, value)

        return tank

    def _create_system(self, name: str, params: Dict) -> CSEDHWSystem:
        """Create DHW system from parameters."""
        system = CSEDHWSystem(name=name)

        for cse_param, attr_name in self.SYSTEM_PARAMS.items():
            if cse_param in params:
                value = params[cse_param]
                if attr_name in ('use_temp_f', 'setpoint_temp_f', 'loop_heater_setpoint_f',
                                 'distribution_loss_mult'):
                    value = float(value) if isinstance(value, (int, float)) else None

                setattr(system, attr_name, value)

        return system

    def _create_loop(self, name: str, params: Dict) -> CSEDHWLoop:
        """Create DHW loop from parameters."""
        loop = CSEDHWLoop(name=name)

        for cse_param, attr_name in self.LOOP_PARAMS.items():
            if cse_param in params:
                value = params[cse_param]
                if attr_name == 'multiplier':
                    value = int(value) if isinstance(value, (int, float)) else 1
                elif attr_name in ('flow_gpm', 'run_fraction'):
                    value = float(value) if isinstance(value, (int, float)) else None

                setattr(loop, attr_name, value)

        return loop

    def _create_loop_pump(self, name: str, params: Dict) -> CSEDHWLoop:
        """Create DHW loop pump (store as loop with pump power)."""
        loop = CSEDHWLoop(name=name)

        if 'wlpPwr' in params:
            value = params['wlpPwr']
            loop.pump_power_w = float(value) if isinstance(value, (int, float)) else None

        return loop

    def _add_object(self, obj: Any, block_type: str, current_system: Optional[CSEDHWSystem]) -> None:
        """Add parsed object to appropriate output list."""
        if block_type in ('DHWHEATER', 'DHWLOOPHEATER'):
            self.output.dhw_heaters.append(obj)
            if current_system:
                current_system.heaters.append(obj)
        elif block_type == 'DHWTANK':
            self.output.dhw_tanks.append(obj)
            if current_system:
                current_system.tanks.append(obj)
        elif block_type == 'DHWSYS':
            self.output.dhw_systems.append(obj)
        elif block_type in ('DHWLOOP', 'DHWLOOPPUMP'):
            self.output.dhw_loops.append(obj)
            if current_system:
                current_system.loops.append(obj)


def parse_cse_input(filepath: Path) -> CSEInputOutput:
    """
    Parse a CSE input file (.cse).

    Args:
        filepath: Path to the CSE file

    Returns:
        CSEInputOutput with all parsed DHW components
    """
    parser = CSEInputParser()
    return parser.parse_file(filepath)
