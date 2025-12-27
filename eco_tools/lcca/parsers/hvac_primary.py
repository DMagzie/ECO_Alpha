"""
Parser for CBECC HVACPrimary.csv output files.

Extracts central plant and DHW specifications including:
- Fluid Systems (HotWater, ChilledWater, CondenserWater, ServiceHotWater)
- Boilers
- Chillers
- Cooling Towers
- Pumps
- Water Heaters (DHW)
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, List, Dict, Any
import logging

from .cbecc_csv_base import CebeccCsvParser, CebeccSection

logger = logging.getLogger(__name__)


@dataclass
class FluidSystem:
    """Fluid system specification (hot water, chilled water, etc.)."""
    name: str
    system_type: str  # ServiceHotWater, HotWater, ChilledWater, CondenserWater
    status: str  # New, Existing, Altered
    design_supply_temp_f: Optional[float] = None
    design_delta_t_f: Optional[float] = None
    temp_control: Optional[str] = None
    supply_component_count: int = 0
    supply_capacity_btuh: float = 0
    supply_flow_gpm: float = 0
    demand_component_count: int = 0
    demand_capacity_btuh: float = 0


@dataclass
class Boiler:
    """Boiler specification."""
    name: str
    fluid_system: str
    status: str
    boiler_type: str  # HotWater, Steam
    fuel: str  # Gas, Electric, Oil
    draft_type: Optional[str] = None  # Condensing, Non-condensing
    rated_capacity_btuh: float = 0
    afue: Optional[float] = None
    thermal_efficiency: Optional[float] = None
    forced_draft_power_hp: Optional[float] = None
    min_unload_ratio: Optional[float] = None


@dataclass
class Chiller:
    """Chiller specification."""
    name: str
    fluid_system: str
    status: str
    chiller_type: str  # Centrifugal, Screw, Scroll, Reciprocating
    fuel: str  # Electric
    condenser_type: str  # Air, Fluid (water-cooled)
    rated_capacity_btuh: float = 0
    eer: Optional[float] = None
    cop: Optional[float] = None
    kw_per_ton: Optional[float] = None
    iplv: Optional[float] = None
    unloading_ratio: Optional[float] = None
    min_part_load_ratio: Optional[float] = None


@dataclass
class CoolingTower:
    """Cooling tower specification."""
    name: str
    fluid_system: str
    status: str
    tower_type: str  # OpenTower, ClosedTower
    rated_capacity_btuh: float = 0
    num_cells: int = 1
    airflow_cfm: float = 0
    fan_type: Optional[str] = None  # Axial, Centrifugal
    total_fan_hp: float = 0
    condenser_water_flow_gpm: float = 0
    capacity_control: Optional[str] = None  # VariableSpeedDrive, TwoSpeed, etc.


@dataclass
class Pump:
    """Pump specification."""
    name: str
    serving_equipment: str
    status: str
    count: int = 1
    operation: str = 'OnDemand'  # OnDemand, Continuous
    speed_type: str = 'ConstantSpeed'  # ConstantSpeed, VariableSpeed
    design_flow_gpm: float = 0
    nameplate_hp: float = 0
    power_kw: Optional[float] = None
    head_ft: Optional[float] = None
    motor_efficiency: Optional[float] = None
    impeller_efficiency: Optional[float] = None


@dataclass
class WaterHeater:
    """Water heater (DHW) specification."""
    name: str
    system_name: str
    system_type: str  # ServiceHotWater
    system_count: int = 1
    status: str = 'New'
    heater_type: str = 'Conventional'  # Conventional, HeatPump, Instantaneous
    fuel: str = 'Electricity'  # Electricity, Gas
    count: int = 1
    thermal_efficiency: float = 1.0
    standby_loss_fraction: Optional[float] = None
    storage_capacity_gal: float = 0
    rated_capacity_btuh: float = 0
    energy_factor: Optional[float] = None
    uniform_energy_factor: Optional[float] = None  # UEF for newer models


@dataclass
class HVACPrimaryOutput:
    """Complete parsed output from HVACPrimary.csv."""
    fluid_systems: List[FluidSystem] = field(default_factory=list)
    boilers: List[Boiler] = field(default_factory=list)
    chillers: List[Chiller] = field(default_factory=list)
    cooling_towers: List[CoolingTower] = field(default_factory=list)
    pumps: List[Pump] = field(default_factory=list)
    water_heaters: List[WaterHeater] = field(default_factory=list)

    # Summary metrics
    @property
    def total_boiler_capacity_btuh(self) -> float:
        """Total boiler capacity."""
        return sum(b.rated_capacity_btuh for b in self.boilers)

    @property
    def total_boiler_capacity_mbh(self) -> float:
        """Total boiler capacity in MBH (thousands BTU/hr)."""
        return self.total_boiler_capacity_btuh / 1000

    @property
    def total_chiller_capacity_btuh(self) -> float:
        """Total chiller capacity."""
        return sum(c.rated_capacity_btuh for c in self.chillers)

    @property
    def total_chiller_capacity_tons(self) -> float:
        """Total chiller capacity in tons."""
        return self.total_chiller_capacity_btuh / 12000

    @property
    def total_dhw_capacity_btuh(self) -> float:
        """Total DHW capacity."""
        return sum(w.rated_capacity_btuh for w in self.water_heaters)

    @property
    def total_dhw_storage_gal(self) -> float:
        """Total DHW storage capacity."""
        return sum(w.storage_capacity_gal for w in self.water_heaters)

    @property
    def has_central_plant(self) -> bool:
        """Check if building has central plant (chillers/boilers)."""
        return len(self.boilers) > 0 or len(self.chillers) > 0


class HVACPrimaryParser(CebeccCsvParser):
    """Parser for HVACPrimary.csv files."""

    # Section name mappings
    SECTION_ALIASES = {
        'fluidsystems': 'FluidSystems',
        'fluid systems': 'FluidSystems',
        'boiler': 'Boiler',
        'boilers': 'Boiler',
        'chiller': 'Chiller',
        'chillers': 'Chiller',
        'cooling tower': 'CoolingTower',
        'coolingtower': 'CoolingTower',
        'cooling towers': 'CoolingTower',
        'pump': 'Pump',
        'pumps': 'Pump',
        'water heater': 'WaterHeater',
        'waterheater': 'WaterHeater',
        'water heaters': 'WaterHeater',
    }

    def parse_file(self, filepath: Path) -> HVACPrimaryOutput:
        """
        Parse HVACPrimary.csv and return structured output.

        Args:
            filepath: Path to HVACPrimary.csv

        Returns:
            HVACPrimaryOutput with all parsed components
        """
        # Parse sections using base class
        sections = super().parse_file(filepath)

        # Create output
        output = HVACPrimaryOutput()

        # Parse each section
        output.fluid_systems = self._parse_fluid_systems(sections)
        output.boilers = self._parse_boilers(sections)
        output.chillers = self._parse_chillers(sections)
        output.cooling_towers = self._parse_cooling_towers(sections)
        output.pumps = self._parse_pumps(sections)
        output.water_heaters = self._parse_water_heaters(sections)

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

    def _parse_fluid_systems(self, sections: Dict[str, CebeccSection]) -> List[FluidSystem]:
        """Parse FluidSystems section."""
        section = self._get_section(sections, 'FluidSystems')
        if not section:
            return []

        systems = []
        for row in section.data:
            try:
                system = FluidSystem(
                    name=self._get_str(row, 'Name', ''),
                    system_type=self._get_str(row, 'Type', ''),
                    status=self._get_str(row, 'Status', 'New'),
                    design_supply_temp_f=self._get_float(row, 'Design SupplyT'),
                    design_delta_t_f=self._get_float(row, 'Design DelT'),
                    temp_control=self._get_str(row, 'TempCtrl'),
                    supply_component_count=self._get_int(row, 'Num Comps', 0),
                    supply_capacity_btuh=self._get_float(row, 'Total Capacity', 0),
                    supply_flow_gpm=self._get_float(row, 'Flow Rate', 0),
                )
                if system.name:
                    systems.append(system)
            except Exception as e:
                logger.warning(f"Error parsing fluid system row: {e}")

        return systems

    def _parse_boilers(self, sections: Dict[str, CebeccSection]) -> List[Boiler]:
        """Parse Boiler section."""
        section = self._get_section(sections, 'Boiler')
        if not section:
            return []

        boilers = []
        for row in section.data:
            try:
                boiler = Boiler(
                    name=self._get_str(row, 'Name', ''),
                    fluid_system=self._get_str(row, 'Fluid System Name', ''),
                    status=self._get_str(row, 'Status', 'New'),
                    boiler_type=self._get_str(row, 'Type', 'HotWater'),
                    fuel=self._get_str(row, 'Fuel', 'Gas'),
                    draft_type=self._get_str(row, 'Draft Type'),
                    rated_capacity_btuh=self._get_float(row, 'Rated Capacity', 0),
                    afue=self._get_float(row, 'AFUE'),
                    thermal_efficiency=self._get_float(row, 'Thermal Efficiency'),
                    forced_draft_power_hp=self._get_float(row, 'Forced Draft Power'),
                    min_unload_ratio=self._get_float(row, 'Minimum Unload Ratio'),
                )
                if boiler.name:
                    boilers.append(boiler)
            except Exception as e:
                logger.warning(f"Error parsing boiler row: {e}")

        return boilers

    def _parse_chillers(self, sections: Dict[str, CebeccSection]) -> List[Chiller]:
        """Parse Chiller section."""
        section = self._get_section(sections, 'Chiller')
        if not section:
            return []

        chillers = []
        for row in section.data:
            try:
                chiller = Chiller(
                    name=self._get_str(row, 'Name', ''),
                    fluid_system=self._get_str(row, 'Fluid System Name', ''),
                    status=self._get_str(row, 'Status', 'New'),
                    chiller_type=self._get_str(row, 'Type', 'Centrifugal'),
                    fuel=self._get_str(row, 'Fuel', 'Electric'),
                    condenser_type=self._get_str(row, 'Condenser Type', 'Air'),
                    rated_capacity_btuh=self._get_float(row, 'Rated Capacity', 0),
                    eer=self._get_float(row, 'EER'),
                    cop=self._get_float(row, 'COP'),
                    kw_per_ton=self._get_float(row, 'KW/ton'),
                    iplv=self._get_float(row, 'IPLV'),
                    unloading_ratio=self._get_float(row, 'Unloading Ratio'),
                    min_part_load_ratio=self._get_float(row, 'Min. Part-Load Ratio'),
                )
                if chiller.name:
                    chillers.append(chiller)
            except Exception as e:
                logger.warning(f"Error parsing chiller row: {e}")

        return chillers

    def _parse_cooling_towers(self, sections: Dict[str, CebeccSection]) -> List[CoolingTower]:
        """Parse Cooling Tower section."""
        section = self._get_section(sections, 'Cooling Tower')
        if not section:
            return []

        towers = []
        for row in section.data:
            try:
                tower = CoolingTower(
                    name=self._get_str(row, 'Name', ''),
                    fluid_system=self._get_str(row, 'Fluid System Name', ''),
                    status=self._get_str(row, 'Status', 'New'),
                    tower_type=self._get_str(row, 'Type', 'OpenTower'),
                    rated_capacity_btuh=self._get_float(row, 'Rated Capacity', 0),
                    num_cells=self._get_int(row, 'Number of Cells', 1),
                    airflow_cfm=self._get_float(row, 'Tower Air flow', 0),
                    fan_type=self._get_str(row, 'Fan Type'),
                    total_fan_hp=self._get_float(row, 'Total Fan HP', 0),
                    condenser_water_flow_gpm=self._get_float(row, 'Condenser Water Flow Rate', 0),
                    capacity_control=self._get_str(row, 'Capacity Control'),
                )
                if tower.name:
                    towers.append(tower)
            except Exception as e:
                logger.warning(f"Error parsing cooling tower row: {e}")

        return towers

    def _parse_pumps(self, sections: Dict[str, CebeccSection]) -> List[Pump]:
        """Parse Pump section."""
        section = self._get_section(sections, 'Pump')
        if not section:
            return []

        pumps = []
        for row in section.data:
            try:
                pump = Pump(
                    name=self._get_str(row, 'Name', ''),
                    serving_equipment=self._get_str(row, 'Serving Equipment', ''),
                    status=self._get_str(row, 'Status', 'New'),
                    count=self._get_int(row, 'Count', 1),
                    operation=self._get_str(row, 'Operation', 'OnDemand'),
                    speed_type=self._get_str(row, 'Speed Type', 'ConstantSpeed'),
                    design_flow_gpm=self._get_float(row, 'Design Flow Rate', 0),
                    nameplate_hp=self._get_float(row, 'Nameplate HP', 0),
                    power_kw=self._get_float(row, 'Power'),
                    head_ft=self._get_float(row, 'Head'),
                    motor_efficiency=self._get_float(row, 'Motor Efficiency'),
                    impeller_efficiency=self._get_float(row, 'Impeller Efficiency'),
                )
                if pump.name:
                    pumps.append(pump)
            except Exception as e:
                logger.warning(f"Error parsing pump row: {e}")

        return pumps

    def _parse_water_heaters(self, sections: Dict[str, CebeccSection]) -> List[WaterHeater]:
        """Parse Water Heater section."""
        section = self._get_section(sections, 'Water Heater')
        if not section:
            return []

        heaters = []
        for row in section.data:
            try:
                heater = WaterHeater(
                    name=self._get_str(row, 'Name', ''),
                    system_name=self._get_str(row, 'System Name', ''),
                    system_type=self._get_str(row, 'System Type', 'ServiceHotWater'),
                    system_count=self._get_int(row, 'System Count', 1),
                    status=self._get_str(row, 'Status', 'New'),
                    heater_type=self._get_str(row, 'Type', 'Conventional'),
                    fuel=self._get_str(row, 'Fuel', 'Electricity'),
                    count=self._get_int(row, 'Count', 1),
                    thermal_efficiency=self._get_float(row, 'Thermal Efficiency', 1.0),
                    standby_loss_fraction=self._get_float(row, 'StandbyLoss Fraction'),
                    storage_capacity_gal=self._get_float(row, 'Storage Capacity', 0),
                    rated_capacity_btuh=self._get_float(row, 'Rated Capacity', 0),
                    energy_factor=self._get_float(row, 'Energy Factor'),
                )
                if heater.name:
                    heaters.append(heater)
            except Exception as e:
                logger.warning(f"Error parsing water heater row: {e}")

        return heaters

    # Helper methods (same as HVACSecondaryParser)
    def _get_str(self, row: Dict[str, Any], key: str, default: str = None) -> Optional[str]:
        """Get string value from row."""
        val = row.get(key)
        if val is None:
            for k, v in row.items():
                if k.lower() == key.lower():
                    val = v
                    break
        if val is None or val == '' or val == 'NONE':
            return default
        return str(val)

    def _get_float(self, row: Dict[str, Any], key: str, default: float = None) -> Optional[float]:
        """Get float value from row."""
        val = row.get(key)
        if val is None:
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
        """Clean a numeric value."""
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


def parse_hvac_primary(filepath: Path) -> HVACPrimaryOutput:
    """
    Parse a HVACPrimary.csv file.

    Args:
        filepath: Path to the CSV file

    Returns:
        HVACPrimaryOutput with all parsed components
    """
    parser = HVACPrimaryParser()
    return parser.parse_file(filepath)
