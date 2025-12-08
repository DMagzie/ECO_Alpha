"""
Parser for CBECC CSE (California Simulation Engine) hourly output CSV files.

These files (*-CSE.CSV) contain meter-based hourly energy data with end-use breakdown.
Each row represents one hour for one meter type (MtrElec, MtrElec2, MtrNatGas).
"""

from __future__ import annotations
import csv
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, field

from ..model import HourlyEnergy, AnnualEnergySummary, SimulationOutput


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
