"""
Parser for CBECC CSE (California Simulation Engine) hourly output CSV files.

These files (*-CSE.CSV) contain meter-based hourly energy data with end-use breakdown.
Each row represents one hour for one meter type (MtrElec, MtrElec2, MtrNatGas).

Provides both:
- Standard output (SimulationOutput) for LCCA energy calculations
- Detailed output (CSEDetailedOutput) with 25+ individual end-use breakdowns
"""

from __future__ import annotations
import csv
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, field

from ..model import HourlyEnergy, AnnualEnergySummary, SimulationOutput


# Column indices for CSE CSV format
CSE_COL = {
    'meter': 0, 'month': 1, 'day': 2, 'hour': 3, 'subhr': 4,
    'total': 5, 'cooling': 6, 'heating': 7, 'hp_backup': 8,
    'dhw': 9, 'dhw_backup': 10, 'dhw_mfl': 11,
    'fan_cooling': 12, 'fan_heating': 13, 'fan_vent': 14, 'fan_other': 15,
    'aux': 16, 'process': 17, 'lighting': 18, 'receptacle': 19,
    'exterior': 20, 'refrigerator': 21, 'dishwasher': 22, 'dryer': 23,
    'washer': 24, 'cooking': 25, 'user1': 26, 'user2': 27,
    'battery': 28, 'pv': 29
}

# Conversion factors
KBTU_TO_KWH = 1.0 / 3.412
KBTU_TO_THERM = 1.0 / 100.0


@dataclass
class CSEDetailedHourly:
    """Detailed hourly energy data with all 25+ end uses separated."""
    month: int
    day: int
    hour: int

    # Electric end uses (kWh)
    elec_total: float = 0.0
    elec_cooling: float = 0.0
    elec_heating: float = 0.0
    elec_hp_backup: float = 0.0
    elec_dhw: float = 0.0
    elec_dhw_backup: float = 0.0
    elec_dhw_mfl: float = 0.0  # Makeup/Flow Losses
    elec_fan_cooling: float = 0.0
    elec_fan_heating: float = 0.0
    elec_fan_vent: float = 0.0
    elec_fan_other: float = 0.0
    elec_aux: float = 0.0  # Pumps, etc.
    elec_process: float = 0.0
    elec_lighting: float = 0.0
    elec_receptacle: float = 0.0
    elec_exterior: float = 0.0

    # Residential appliances (kWh)
    elec_refrigerator: float = 0.0
    elec_dishwasher: float = 0.0
    elec_dryer: float = 0.0
    elec_washer: float = 0.0
    elec_cooking: float = 0.0

    # User-defined (kWh)
    elec_user1: float = 0.0
    elec_user2: float = 0.0

    # PV and battery (kWh)
    battery: float = 0.0
    pv: float = 0.0

    # Gas end uses (therms)
    gas_total: float = 0.0
    gas_heating: float = 0.0
    gas_dhw: float = 0.0
    gas_dhw_backup: float = 0.0
    gas_dhw_mfl: float = 0.0
    gas_process: float = 0.0
    gas_cooking: float = 0.0
    gas_dryer: float = 0.0

    @property
    def elec_fans_total(self) -> float:
        """Total fan energy."""
        return self.elec_fan_cooling + self.elec_fan_heating + self.elec_fan_vent + self.elec_fan_other

    @property
    def elec_dhw_total(self) -> float:
        """Total electric DHW energy."""
        return self.elec_dhw + self.elec_dhw_backup + self.elec_dhw_mfl

    @property
    def elec_appliances_total(self) -> float:
        """Total residential appliance energy."""
        return (self.elec_refrigerator + self.elec_dishwasher +
                self.elec_dryer + self.elec_washer + self.elec_cooking)

    @property
    def net_elec(self) -> float:
        """Net electricity after PV."""
        return self.elec_total - self.pv + self.battery


@dataclass
class CSEDetailedAnnual:
    """Annual totals with detailed end-use breakdown."""

    # Electric totals (kWh)
    elec_total: float = 0.0
    elec_cooling: float = 0.0
    elec_heating: float = 0.0
    elec_hp_backup: float = 0.0
    elec_dhw: float = 0.0
    elec_dhw_backup: float = 0.0
    elec_dhw_mfl: float = 0.0
    elec_fan_cooling: float = 0.0
    elec_fan_heating: float = 0.0
    elec_fan_vent: float = 0.0
    elec_fan_other: float = 0.0
    elec_aux: float = 0.0
    elec_process: float = 0.0
    elec_lighting: float = 0.0
    elec_receptacle: float = 0.0
    elec_exterior: float = 0.0

    # Residential appliances (kWh)
    elec_refrigerator: float = 0.0
    elec_dishwasher: float = 0.0
    elec_dryer: float = 0.0
    elec_washer: float = 0.0
    elec_cooking: float = 0.0

    # User-defined (kWh)
    elec_user1: float = 0.0
    elec_user2: float = 0.0

    # PV and battery (kWh)
    battery_net: float = 0.0
    pv_generation: float = 0.0

    # Gas totals (therms)
    gas_total: float = 0.0
    gas_heating: float = 0.0
    gas_dhw: float = 0.0
    gas_dhw_backup: float = 0.0
    gas_dhw_mfl: float = 0.0
    gas_process: float = 0.0
    gas_cooking: float = 0.0
    gas_dryer: float = 0.0

    # Peak demand
    peak_demand_kw: float = 0.0
    peak_demand_month: int = 0
    peak_demand_day: int = 0
    peak_demand_hour: int = 0

    # Monthly peaks
    monthly_peaks_kw: Dict[int, float] = field(default_factory=dict)

    @property
    def elec_fans_total(self) -> float:
        return self.elec_fan_cooling + self.elec_fan_heating + self.elec_fan_vent + self.elec_fan_other

    @property
    def elec_dhw_total(self) -> float:
        return self.elec_dhw + self.elec_dhw_backup + self.elec_dhw_mfl

    @property
    def elec_appliances_total(self) -> float:
        return (self.elec_refrigerator + self.elec_dishwasher +
                self.elec_dryer + self.elec_washer + self.elec_cooking)

    @property
    def net_elec(self) -> float:
        return self.elec_total - self.pv_generation + self.battery_net

    @property
    def gas_dhw_total(self) -> float:
        return self.gas_dhw + self.gas_dhw_backup + self.gas_dhw_mfl


@dataclass
class CSEDetailedOutput:
    """Complete detailed output from CSE hourly CSV parsing."""

    # Metadata
    project_name: str = ''
    model_file: str = ''
    model_type: str = ''  # Proposed, Standard
    run_datetime: str = ''

    # Annual summary
    annual: CSEDetailedAnnual = field(default_factory=CSEDetailedAnnual)

    # Hourly data (8760 records)
    hourly: List[CSEDetailedHourly] = field(default_factory=list)

    # End-use dictionary for easy access
    annual_by_enduse: Dict[str, float] = field(default_factory=dict)

    def build_enduse_dict(self) -> None:
        """Build dictionary mapping end-use names to annual totals."""
        self.annual_by_enduse = {
            # Electric
            'elec_cooling': self.annual.elec_cooling,
            'elec_heating': self.annual.elec_heating,
            'elec_hp_backup': self.annual.elec_hp_backup,
            'elec_dhw': self.annual.elec_dhw,
            'elec_dhw_backup': self.annual.elec_dhw_backup,
            'elec_dhw_mfl': self.annual.elec_dhw_mfl,
            'elec_fan_cooling': self.annual.elec_fan_cooling,
            'elec_fan_heating': self.annual.elec_fan_heating,
            'elec_fan_vent': self.annual.elec_fan_vent,
            'elec_fan_other': self.annual.elec_fan_other,
            'elec_aux': self.annual.elec_aux,
            'elec_process': self.annual.elec_process,
            'elec_lighting': self.annual.elec_lighting,
            'elec_receptacle': self.annual.elec_receptacle,
            'elec_exterior': self.annual.elec_exterior,
            'elec_refrigerator': self.annual.elec_refrigerator,
            'elec_dishwasher': self.annual.elec_dishwasher,
            'elec_dryer': self.annual.elec_dryer,
            'elec_washer': self.annual.elec_washer,
            'elec_cooking': self.annual.elec_cooking,
            'elec_user1': self.annual.elec_user1,
            'elec_user2': self.annual.elec_user2,
            'pv_generation': self.annual.pv_generation,
            'battery_net': self.annual.battery_net,
            # Gas
            'gas_heating': self.annual.gas_heating,
            'gas_dhw': self.annual.gas_dhw,
            'gas_dhw_backup': self.annual.gas_dhw_backup,
            'gas_dhw_mfl': self.annual.gas_dhw_mfl,
            'gas_process': self.annual.gas_process,
            'gas_cooking': self.annual.gas_cooking,
            'gas_dryer': self.annual.gas_dryer,
        }


@dataclass
class CseHourlyParser:
    """Parser for CBECC CSE hourly CSV files."""

    # Metadata from header
    run_title: str = ""
    model_type: str = ""            # "Proposed" or "Standard"
    model_file: str = ""
    run_datetime: str = ""

    def parse_file(self, filepath: str | Path) -> SimulationOutput:
        """Parse a CSE CSV file and return SimulationOutput."""
        filepath = Path(filepath)

        with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
            lines = f.readlines()

        # Parse header (first 2-3 lines)
        self._parse_header(lines)

        # Find data start (after "Meter" header row)
        data_start = self._find_data_start(lines)

        # Parse meter data into hourly records
        hourly_data = self._parse_meter_data(lines, data_start)

        # Calculate annual summary
        annual = self._calculate_annual_summary(hourly_data)

        # Build output
        output = SimulationOutput(
            project_name=self._extract_project_name(),
            model_file=self.model_file,
            run_date=self.run_datetime,
            model_type=self.model_type,
            annual=annual,
            hourly=hourly_data,
        )

        return output

    def _parse_header(self, lines: List[str]) -> None:
        """Extract metadata from first few lines."""
        if len(lines) >= 1:
            # First line: "Title 24 ... / Proposed / filename.cibd22x",002
            first = lines[0].strip().strip('"')
            parts = first.split('/')
            if len(parts) >= 3:
                self.run_title = parts[0].strip()
                self.model_type = parts[1].strip()
                self.model_file = parts[2].strip().split(',')[0].strip('"')

        if len(lines) >= 2:
            # Second line: date/time
            self.run_datetime = lines[1].strip().strip('"')

    def _find_data_start(self, lines: List[str]) -> int:
        """Find where data rows begin (after header row)."""
        for i, line in enumerate(lines):
            if line.strip().startswith('"Meter"'):
                return i + 1
        return 4  # Default if not found

    def _parse_meter_data(self, lines: List[str], start_idx: int) -> List[HourlyEnergy]:
        """
        Parse meter data rows.

        Format:
        "Meter",Mon,Day,Hr,Subhr,Tot,Clg,Htg,HPBU,Dhw,DhwBU,DhwMFL,FanC,FanH,FanV,Fan,Aux,Proc,Lit,Rcp,Ext,Refr,Dish,Dry,Wash,Cook,User1,User2,BT,PV

        There are separate rows for MtrElec, MtrElec2, MtrNatGas for each hour.
        We need to combine them into single HourlyEnergy records.
        """
        # Temporary storage: {(month, day, hour): {meter_type: row_data}}
        hourly_dict: Dict[Tuple[int, int, int], Dict[str, List[str]]] = {}

        for line in lines[start_idx:]:
            line = line.strip()
            if not line:
                continue

            # Parse CSV
            reader = csv.reader([line])
            try:
                row = next(reader)
            except StopIteration:
                continue

            if len(row) < 6:
                continue

            # Get meter type and time
            meter_type = row[0].strip().strip('"')
            if not meter_type.startswith('Mtr'):
                continue

            try:
                month = int(row[1])
                day = int(row[2])
                hour = int(row[3])
            except (ValueError, IndexError):
                continue

            key = (month, day, hour)
            if key not in hourly_dict:
                hourly_dict[key] = {}
            hourly_dict[key][meter_type] = row

        # Convert to HourlyEnergy records
        hourly_data = []
        for (month, day, hour), meters in sorted(hourly_dict.items()):
            hourly = self._combine_meters(month, day, hour, meters)
            hourly_data.append(hourly)

        return hourly_data

    def _combine_meters(
        self,
        month: int,
        day: int,
        hour: int,
        meters: Dict[str, List[str]]
    ) -> HourlyEnergy:
        """Combine electric and gas meter data into single HourlyEnergy."""
        # Column indices for CSE format:
        # 0:Meter, 1:Mon, 2:Day, 3:Hr, 4:Subhr, 5:Tot, 6:Clg, 7:Htg, 8:HPBU,
        # 9:Dhw, 10:DhwBU, 11:DhwMFL, 12:FanC, 13:FanH, 14:FanV, 15:Fan,
        # 16:Aux, 17:Proc, 18:Lit, 19:Rcp, 20:Ext, 21:Refr, 22:Dish, 23:Dry,
        # 24:Wash, 25:Cook, 26:User1, 27:User2, 28:BT, 29:PV

        elec = meters.get('MtrElec', [])
        elec2 = meters.get('MtrElec2', [])
        gas = meters.get('MtrNatGas', [])

        # Electric values (CSE reports in kBtu, convert to kWh: 1 kWh = 3.412 kBtu)
        KBTU_TO_KWH = 1.0 / 3.412

        elec_total = self._safe_float(elec, 5) * KBTU_TO_KWH
        elec_cooling = self._safe_float(elec, 6) * KBTU_TO_KWH
        elec_heating = (self._safe_float(elec, 7) + self._safe_float(elec, 8)) * KBTU_TO_KWH  # Htg + HPBU
        elec_dhw = (self._safe_float(elec, 9) + self._safe_float(elec, 10) + self._safe_float(elec, 11)) * KBTU_TO_KWH
        elec_fans = (self._safe_float(elec, 12) + self._safe_float(elec, 13) +
                     self._safe_float(elec, 14) + self._safe_float(elec, 15)) * KBTU_TO_KWH
        elec_aux = self._safe_float(elec, 16) * KBTU_TO_KWH  # Pumps/Aux
        elec_process = self._safe_float(elec, 17) * KBTU_TO_KWH
        elec_lighting = self._safe_float(elec, 18) * KBTU_TO_KWH
        elec_receptacle = self._safe_float(elec, 19) * KBTU_TO_KWH
        elec_exterior = self._safe_float(elec, 20) * KBTU_TO_KWH

        # Additional electric loads
        elec_refrig = self._safe_float(elec, 21) * KBTU_TO_KWH
        elec_dish = self._safe_float(elec, 22) * KBTU_TO_KWH
        elec_dry = self._safe_float(elec, 23) * KBTU_TO_KWH
        elec_wash = self._safe_float(elec, 24) * KBTU_TO_KWH
        elec_cook = self._safe_float(elec, 25) * KBTU_TO_KWH

        # PV and battery (from electric meter, also in kBtu)
        battery_kwh = self._safe_float(elec, 28) * KBTU_TO_KWH
        pv_kwh = abs(self._safe_float(elec, 29)) * KBTU_TO_KWH

        # Add secondary electric meter if present (also in kBtu)
        if elec2:
            elec_total += self._safe_float(elec2, 5) * KBTU_TO_KWH

        # Gas values (CSE reports in kBtu, convert to therms: 1 therm = 100 kBtu)
        gas_total_kbtu = self._safe_float(gas, 5)
        gas_heating_kbtu = self._safe_float(gas, 7)
        gas_dhw_kbtu = (self._safe_float(gas, 9) + self._safe_float(gas, 10) +
                        self._safe_float(gas, 11))
        gas_process_kbtu = self._safe_float(gas, 17)
        gas_cook_kbtu = self._safe_float(gas, 25)

        # Convert kBtu to therms
        gas_total = gas_total_kbtu / 100.0
        gas_heating = gas_heating_kbtu / 100.0
        gas_dhw = gas_dhw_kbtu / 100.0
        gas_process = gas_process_kbtu / 100.0
        gas_cook = gas_cook_kbtu / 100.0

        # Include residential appliances in totals
        elec_process += elec_refrig + elec_dish + elec_wash
        elec_heating += elec_dry  # Dryer often uses heat

        return HourlyEnergy(
            month=month,
            day=day,
            hour=hour,
            elec_total_kwh=elec_total,
            elec_heating_kwh=elec_heating,
            elec_cooling_kwh=elec_cooling,
            elec_fans_kwh=elec_fans,
            elec_pumps_kwh=elec_aux,
            elec_dhw_kwh=elec_dhw,
            elec_lighting_kwh=elec_lighting,
            elec_receptacle_kwh=elec_receptacle,
            elec_process_kwh=elec_process,
            elec_exterior_kwh=elec_exterior,
            gas_total_therm=gas_total,
            gas_heating_therm=gas_heating,
            gas_dhw_therm=gas_dhw,
            gas_process_therm=gas_process + gas_cook,
            pv_generation_kwh=pv_kwh,
            battery_kwh=battery_kwh,
        )

    def _safe_float(self, row: List[str], idx: int) -> float:
        """Safely extract float from row at index."""
        try:
            if 0 <= idx < len(row):
                val = row[idx].strip().strip('"')
                if val:
                    return float(val)
        except (ValueError, IndexError):
            pass
        return 0.0

    def _calculate_annual_summary(self, hourly: List[HourlyEnergy]) -> AnnualEnergySummary:
        """Calculate annual totals from hourly data."""
        if not hourly:
            return AnnualEnergySummary()

        summary = AnnualEnergySummary()
        monthly_peaks: Dict[int, float] = {}

        for h in hourly:
            # Electric totals
            summary.total_elec_kwh += h.elec_total_kwh
            summary.cooling_kwh += h.elec_cooling_kwh
            summary.heating_kwh += h.elec_heating_kwh
            summary.fans_kwh += h.elec_fans_kwh
            summary.pumps_kwh += h.elec_pumps_kwh
            summary.lighting_kwh += h.elec_lighting_kwh
            summary.receptacle_kwh += h.elec_receptacle_kwh
            summary.dhw_elec_kwh += h.elec_dhw_kwh
            summary.process_kwh += h.elec_process_kwh
            summary.exterior_kwh += h.elec_exterior_kwh

            # Gas totals
            summary.total_gas_therm += h.gas_total_therm
            summary.heating_therm += h.gas_heating_therm
            summary.dhw_therm += h.gas_dhw_therm
            summary.process_therm += h.gas_process_therm

            # PV
            summary.pv_generation_kwh += h.pv_generation_kwh

            # Peak demand
            demand_kw = h.elec_total_kwh
            if demand_kw > summary.peak_demand_kw:
                summary.peak_demand_kw = demand_kw
                summary.peak_demand_month = h.month
                summary.peak_demand_hour = h.hour

            # Monthly peaks
            if h.month not in monthly_peaks or demand_kw > monthly_peaks[h.month]:
                monthly_peaks[h.month] = demand_kw

        summary.monthly_peaks_kw = monthly_peaks
        summary.net_elec_kwh = summary.total_elec_kwh - summary.pv_generation_kwh

        return summary

    def _extract_project_name(self) -> str:
        """Extract project name from model file."""
        if self.model_file:
            return Path(self.model_file).stem
        return self.run_title or "Unknown"


def parse_cse_csv(filepath: str | Path) -> SimulationOutput:
    """
    Parse a CBECC CSE hourly CSV file.

    Args:
        filepath: Path to the *-CSE.CSV file

    Returns:
        SimulationOutput with parsed data
    """
    parser = CseHourlyParser()
    return parser.parse_file(filepath)


def parse_cse_detailed(filepath: str | Path) -> CSEDetailedOutput:
    """
    Parse a CBECC CSE hourly CSV file with detailed end-use breakdown.

    This parser extracts all 25+ individual end uses (cooling, heating,
    hp_backup, dhw, dhw_backup, dhw_mfl, fans x4, aux, process, lighting,
    receptacle, exterior, refrigerator, dishwasher, dryer, washer, cooking,
    user1, user2, battery, pv) for both electricity and gas meters.

    Args:
        filepath: Path to the *-CSE.CSV file

    Returns:
        CSEDetailedOutput with all end uses separated
    """
    parser = CseDetailedParser()
    return parser.parse_file(filepath)


class CseDetailedParser:
    """Parser for detailed CSE hourly output."""

    def __init__(self):
        self.run_title: str = ""
        self.model_type: str = ""
        self.model_file: str = ""
        self.run_datetime: str = ""

    def parse_file(self, filepath: str | Path) -> CSEDetailedOutput:
        """Parse CSE CSV file and return detailed output."""
        filepath = Path(filepath)

        with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
            lines = f.readlines()

        # Parse header
        self._parse_header(lines)

        # Find data start
        data_start = self._find_data_start(lines)

        # Parse meter data
        hourly_dict = self._parse_meter_rows(lines, data_start)

        # Build detailed hourly records
        hourly_data = self._build_detailed_hourly(hourly_dict)

        # Calculate annual totals
        annual = self._calculate_annual(hourly_data)

        # Build output
        output = CSEDetailedOutput(
            project_name=self._extract_project_name(),
            model_file=self.model_file,
            model_type=self.model_type,
            run_datetime=self.run_datetime,
            annual=annual,
            hourly=hourly_data,
        )
        output.build_enduse_dict()

        return output

    def _parse_header(self, lines: List[str]) -> None:
        """Extract metadata from first few lines."""
        if len(lines) >= 1:
            first = lines[0].strip().strip('"')
            parts = first.split('/')
            if len(parts) >= 3:
                self.run_title = parts[0].strip()
                self.model_type = parts[1].strip()
                self.model_file = parts[2].strip().split(',')[0].strip('"')

        if len(lines) >= 2:
            self.run_datetime = lines[1].strip().strip('"')

    def _find_data_start(self, lines: List[str]) -> int:
        """Find where data rows begin."""
        for i, line in enumerate(lines):
            if line.strip().startswith('"Meter"'):
                return i + 1
        return 4

    def _parse_meter_rows(self, lines: List[str], start_idx: int) -> Dict[Tuple[int, int, int], Dict[str, List[str]]]:
        """Parse all meter data rows into dictionary."""
        hourly_dict: Dict[Tuple[int, int, int], Dict[str, List[str]]] = {}

        for line in lines[start_idx:]:
            line = line.strip()
            if not line:
                continue

            reader = csv.reader([line])
            try:
                row = next(reader)
            except StopIteration:
                continue

            if len(row) < 6:
                continue

            meter_type = row[0].strip().strip('"')
            if not meter_type.startswith('Mtr'):
                continue

            try:
                month = int(row[1])
                day = int(row[2])
                hour = int(row[3])
            except (ValueError, IndexError):
                continue

            key = (month, day, hour)
            if key not in hourly_dict:
                hourly_dict[key] = {}
            hourly_dict[key][meter_type] = row

        return hourly_dict

    def _build_detailed_hourly(self, hourly_dict: Dict) -> List[CSEDetailedHourly]:
        """Build detailed hourly records from meter data."""
        hourly_data = []

        for (month, day, hour), meters in sorted(hourly_dict.items()):
            elec = meters.get('MtrElec', [])
            elec2 = meters.get('MtrElec2', [])
            gas = meters.get('MtrNatGas', [])

            hourly = CSEDetailedHourly(
                month=month,
                day=day,
                hour=hour,

                # Electric (kBtu -> kWh)
                elec_total=self._get_val(elec, CSE_COL['total']) * KBTU_TO_KWH,
                elec_cooling=self._get_val(elec, CSE_COL['cooling']) * KBTU_TO_KWH,
                elec_heating=self._get_val(elec, CSE_COL['heating']) * KBTU_TO_KWH,
                elec_hp_backup=self._get_val(elec, CSE_COL['hp_backup']) * KBTU_TO_KWH,
                elec_dhw=self._get_val(elec, CSE_COL['dhw']) * KBTU_TO_KWH,
                elec_dhw_backup=self._get_val(elec, CSE_COL['dhw_backup']) * KBTU_TO_KWH,
                elec_dhw_mfl=self._get_val(elec, CSE_COL['dhw_mfl']) * KBTU_TO_KWH,
                elec_fan_cooling=self._get_val(elec, CSE_COL['fan_cooling']) * KBTU_TO_KWH,
                elec_fan_heating=self._get_val(elec, CSE_COL['fan_heating']) * KBTU_TO_KWH,
                elec_fan_vent=self._get_val(elec, CSE_COL['fan_vent']) * KBTU_TO_KWH,
                elec_fan_other=self._get_val(elec, CSE_COL['fan_other']) * KBTU_TO_KWH,
                elec_aux=self._get_val(elec, CSE_COL['aux']) * KBTU_TO_KWH,
                elec_process=self._get_val(elec, CSE_COL['process']) * KBTU_TO_KWH,
                elec_lighting=self._get_val(elec, CSE_COL['lighting']) * KBTU_TO_KWH,
                elec_receptacle=self._get_val(elec, CSE_COL['receptacle']) * KBTU_TO_KWH,
                elec_exterior=self._get_val(elec, CSE_COL['exterior']) * KBTU_TO_KWH,
                elec_refrigerator=self._get_val(elec, CSE_COL['refrigerator']) * KBTU_TO_KWH,
                elec_dishwasher=self._get_val(elec, CSE_COL['dishwasher']) * KBTU_TO_KWH,
                elec_dryer=self._get_val(elec, CSE_COL['dryer']) * KBTU_TO_KWH,
                elec_washer=self._get_val(elec, CSE_COL['washer']) * KBTU_TO_KWH,
                elec_cooking=self._get_val(elec, CSE_COL['cooking']) * KBTU_TO_KWH,
                elec_user1=self._get_val(elec, CSE_COL['user1']) * KBTU_TO_KWH,
                elec_user2=self._get_val(elec, CSE_COL['user2']) * KBTU_TO_KWH,
                battery=self._get_val(elec, CSE_COL['battery']) * KBTU_TO_KWH,
                pv=abs(self._get_val(elec, CSE_COL['pv'])) * KBTU_TO_KWH,

                # Gas (kBtu -> therms)
                gas_total=self._get_val(gas, CSE_COL['total']) * KBTU_TO_THERM,
                gas_heating=self._get_val(gas, CSE_COL['heating']) * KBTU_TO_THERM,
                gas_dhw=self._get_val(gas, CSE_COL['dhw']) * KBTU_TO_THERM,
                gas_dhw_backup=self._get_val(gas, CSE_COL['dhw_backup']) * KBTU_TO_THERM,
                gas_dhw_mfl=self._get_val(gas, CSE_COL['dhw_mfl']) * KBTU_TO_THERM,
                gas_process=self._get_val(gas, CSE_COL['process']) * KBTU_TO_THERM,
                gas_cooking=self._get_val(gas, CSE_COL['cooking']) * KBTU_TO_THERM,
                gas_dryer=self._get_val(gas, CSE_COL['dryer']) * KBTU_TO_THERM,
            )

            # Add secondary electric meter if present
            if elec2:
                hourly.elec_total += self._get_val(elec2, CSE_COL['total']) * KBTU_TO_KWH

            hourly_data.append(hourly)

        return hourly_data

    def _calculate_annual(self, hourly: List[CSEDetailedHourly]) -> CSEDetailedAnnual:
        """Calculate annual totals from hourly data."""
        annual = CSEDetailedAnnual()
        monthly_peaks: Dict[int, float] = {}

        for h in hourly:
            # Electric
            annual.elec_total += h.elec_total
            annual.elec_cooling += h.elec_cooling
            annual.elec_heating += h.elec_heating
            annual.elec_hp_backup += h.elec_hp_backup
            annual.elec_dhw += h.elec_dhw
            annual.elec_dhw_backup += h.elec_dhw_backup
            annual.elec_dhw_mfl += h.elec_dhw_mfl
            annual.elec_fan_cooling += h.elec_fan_cooling
            annual.elec_fan_heating += h.elec_fan_heating
            annual.elec_fan_vent += h.elec_fan_vent
            annual.elec_fan_other += h.elec_fan_other
            annual.elec_aux += h.elec_aux
            annual.elec_process += h.elec_process
            annual.elec_lighting += h.elec_lighting
            annual.elec_receptacle += h.elec_receptacle
            annual.elec_exterior += h.elec_exterior
            annual.elec_refrigerator += h.elec_refrigerator
            annual.elec_dishwasher += h.elec_dishwasher
            annual.elec_dryer += h.elec_dryer
            annual.elec_washer += h.elec_washer
            annual.elec_cooking += h.elec_cooking
            annual.elec_user1 += h.elec_user1
            annual.elec_user2 += h.elec_user2
            annual.battery_net += h.battery
            annual.pv_generation += h.pv

            # Gas
            annual.gas_total += h.gas_total
            annual.gas_heating += h.gas_heating
            annual.gas_dhw += h.gas_dhw
            annual.gas_dhw_backup += h.gas_dhw_backup
            annual.gas_dhw_mfl += h.gas_dhw_mfl
            annual.gas_process += h.gas_process
            annual.gas_cooking += h.gas_cooking
            annual.gas_dryer += h.gas_dryer

            # Peak demand (hourly kWh ≈ kW for 1-hour interval)
            demand_kw = h.elec_total
            if demand_kw > annual.peak_demand_kw:
                annual.peak_demand_kw = demand_kw
                annual.peak_demand_month = h.month
                annual.peak_demand_day = h.day
                annual.peak_demand_hour = h.hour

            # Monthly peaks
            if h.month not in monthly_peaks or demand_kw > monthly_peaks[h.month]:
                monthly_peaks[h.month] = demand_kw

        annual.monthly_peaks_kw = monthly_peaks
        return annual

    @staticmethod
    def _get_val(row: List[str], idx: int) -> float:
        """Safely extract float from row at index."""
        try:
            if 0 <= idx < len(row):
                val = row[idx].strip().strip('"')
                if val:
                    return float(val)
        except (ValueError, IndexError):
            pass
        return 0.0

    def _extract_project_name(self) -> str:
        """Extract project name from model file."""
        if self.model_file:
            return Path(self.model_file).stem
        return self.run_title or "Unknown"
