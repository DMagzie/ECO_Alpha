"""
Parser for CBECC HourlyResults.csv files.

These files are produced by the CEC Compliance Manager and contain:
- Hourly electricity, gas, and propane consumption by end-use
- TDV multipliers for each hour
- Source energy multipliers
- CO2 emissions multipliers
- PV generation and battery data

Supports both single-use (Res-only or NR-only) and mixed-use buildings.
Mixed-use buildings have separate NonRes and Res sections in the CSV.
"""

from __future__ import annotations
import csv
import re
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field

from ..model import HourlyEnergy, AnnualEnergySummary, SimulationOutput


# Column layout constants for HourlyResults.csv
# Single-use buildings: 55 columns (0-54)
# Mixed-use buildings: 108+ columns with NonRes (4-54) and Res (59-109) sections

# Base column indices (0-indexed)
COL_MONTH = 0
COL_DAY = 1
COL_HOUR = 2
COL_DST = 3

# Electric end-use columns (relative to section start)
# Section has 13 end-use columns + TOTAL = 14 columns
ELEC_SPC_HEAT = 0      # Space heating
ELEC_SPC_COOL = 1      # Space cooling
ELEC_INDR_FANS = 2     # Indoor fans
ELEC_HEAT_REJ = 3      # Heat rejection
ELEC_PUMP_MISC = 4     # Pumps & misc
ELEC_DOM_HW = 5        # Domestic hot water
ELEC_LIGHTING = 6      # Interior lighting
ELEC_RECEPT = 7        # Receptacle
ELEC_PROCESS = 8       # Process
ELEC_OTHR_LTG = 9      # Exterior/other lighting
ELEC_PROC_MTRS = 10    # Process motors
ELEC_TOT_COMP = 11     # Total compliance
ELEC_TOTAL = 12        # TOTAL

# Gas end-use columns (relative to gas section start)
# Same layout as electric, 13 columns total
GAS_SPC_HEAT = 0
GAS_SPC_COOL = 1       # Usually 0 for gas
GAS_INDR_FANS = 2      # Usually 0 for gas
GAS_HEAT_REJ = 3       # Usually 0 for gas
GAS_PUMP_MISC = 4      # Usually 0 for gas
GAS_DOM_HW = 5
GAS_LIGHTING = 6       # Usually 0 for gas
GAS_RECEPT = 7         # Usually 0 for gas
GAS_PROCESS = 8
GAS_OTHR_LTG = 9       # Usually 0 for gas
GAS_PROC_MTRS = 10     # Usually 0 for gas
GAS_TOT_COMP = 11
GAS_TOTAL = 12

# Section sizes
ELEC_SECTION_SIZE = 13   # 13 columns for electric
GAS_SECTION_SIZE = 13    # 13 columns for gas
PROPANE_SECTION_SIZE = 13  # 13 columns for propane
TDV_SECTION_SIZE = 3     # Electric, NatGas, OtherFuel
SOURCE_SECTION_SIZE = 3
CO2_SECTION_SIZE = 3

# Single-use building column layout (0-indexed):
# 0-3: Mo, Da, Hr, DST
# 4-16: Electric (13 cols)
# 17-29: Gas (13 cols)
# 30-42: Propane (13 cols)
# 43-45: TDV multipliers
# 46-48: Source multipliers
# 49-51: CO2 multipliers
# 52: Elec demand frac
# 53: PV
# 54: Battery

SINGLE_USE_ELEC_START = 4
SINGLE_USE_GAS_START = 17
SINGLE_USE_PROPANE_START = 30
SINGLE_USE_TDV_START = 43
SINGLE_USE_SOURCE_START = 46
SINGLE_USE_CO2_START = 49
SINGLE_USE_DEMAND_FRAC = 52
SINGLE_USE_PV = 53
SINGLE_USE_BATTERY = 54

# Mixed-use building column layout (0-indexed):
# 0-3: Mo, Da, Hr, DST
# 4-16: NonRes Electric (13 cols)
# 17-29: NonRes Gas (13 cols)
# 30-42: NonRes Propane (13 cols)
# 43-45: NonRes TDV multipliers
# 46-48: NonRes Source multipliers
# 49-51: NonRes CO2 multipliers
# 52: NonRes Elec demand frac
# 53: PV (Building Wide)
# 54: Battery (Building Wide)
# 55-58: PV/Batt Mults (TDV, Source, CO2, frac) - weighted avg
# 59-71: Res Electric (13 cols)
# 72-84: Res Gas (13 cols)
# 85-97: Res Propane (13 cols)
# 98-100: Res TDV multipliers
# 101-103: Res Source multipliers
# 104-106: Res CO2 multipliers
# 107: Res Elec demand frac

MIXED_NONRES_ELEC_START = 4
MIXED_NONRES_GAS_START = 17
MIXED_NONRES_PROPANE_START = 30
MIXED_NONRES_TDV_START = 43
MIXED_NONRES_SOURCE_START = 46
MIXED_NONRES_CO2_START = 49
MIXED_NONRES_DEMAND_FRAC = 52
MIXED_PV = 53
MIXED_BATTERY = 54
MIXED_PVBATT_MULTS_START = 55

MIXED_RES_ELEC_START = 59
MIXED_RES_GAS_START = 72
MIXED_RES_PROPANE_START = 85
MIXED_RES_TDV_START = 98
MIXED_RES_SOURCE_START = 101
MIXED_RES_CO2_START = 104
MIXED_RES_DEMAND_FRAC = 107


@dataclass
class HourlyResultsParser:
    """Parser for CBECC HourlyResults.csv files."""

    # Metadata extracted from header
    software_version: str = ""
    comp_mgr_version: str = ""
    cse_version: str = ""
    ruleset: str = ""
    run_title: str = ""
    run_datetime: str = ""
    nonres_area: float = 0.0
    res_area: float = 0.0
    model_type: str = ""            # "Proposed" or "Standard"
    model_file: str = ""

    def parse_file(self, filepath: str | Path) -> SimulationOutput:
        """Parse a HourlyResults.csv file and return SimulationOutput."""
        filepath = Path(filepath)

        with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
            lines = f.readlines()

        # Parse header section (first ~18 lines)
        self._parse_header(lines)

        # Find the column header row and data start
        header_row_idx, col_headers = self._find_column_headers(lines)

        # Determine building type and parse accordingly
        is_mixed = self._is_mixed_use()

        if is_mixed:
            hourly_nonres, hourly_res, hourly_combined = self._parse_mixed_use_data(
                lines, header_row_idx + 1
            )
            annual_nonres = self._calculate_annual_summary(hourly_nonres)
            annual_res = self._calculate_annual_summary(hourly_res)
            annual = self._calculate_annual_summary(hourly_combined)
        else:
            hourly_combined = self._parse_single_use_data(lines, header_row_idx + 1)
            hourly_nonres = None
            hourly_res = None
            annual_nonres = None
            annual_res = None
            annual = self._calculate_annual_summary(hourly_combined)

        # Build output
        output = SimulationOutput(
            project_name=self._extract_project_name(),
            model_file=self.model_file,
            run_date=self.run_datetime,
            software_version=self.software_version,
            building_type=self._infer_building_type(),
            conditioned_area_sf=self.nonres_area + self.res_area,
            residential_area_sf=self.res_area,
            nonres_area_sf=self.nonres_area,
            model_type=self.model_type,
            annual=annual,
            annual_nonres=annual_nonres,
            annual_res=annual_res,
            hourly=hourly_combined,
            hourly_nonres=hourly_nonres,
            hourly_res=hourly_res,
        )

        return output

    def _is_mixed_use(self) -> bool:
        """Check if building is mixed-use based on areas."""
        return self.nonres_area > 0 and self.res_area > 0

    def _parse_header(self, lines: List[str]) -> None:
        """Extract metadata from header lines."""
        for i, line in enumerate(lines[:25]):
            line = line.strip()

            # Software version
            if 'Software:' in line:
                match = re.search(r'Software:,+,?"?([^"]+)"?', line)
                if match:
                    self.software_version = match.group(1).strip()

            # Compliance Manager version
            if 'CompMgr:' in line:
                match = re.search(r'CompMgr:,+,?"?([^"]+)"?', line)
                if match:
                    self.comp_mgr_version = match.group(1).strip()

            # CSE version
            if 'CSE:' in line:
                match = re.search(r'CSE:,+,?"?([^"]+)"?', line)
                if match:
                    self.cse_version = match.group(1).strip()

            # Ruleset
            if 'Ruleset:' in line:
                match = re.search(r'Ruleset:,+,?"?([^"]+)"?', line)
                if match:
                    self.ruleset = match.group(1).strip()

            # Run title
            if 'Run Title:' in line:
                match = re.search(r'Run Title:,+,?"?([^"]+)"?', line)
                if match:
                    self.run_title = match.group(1).strip()

            # Run date/time
            if 'Run Date/Time:' in line:
                match = re.search(r'Run Date/Time:,+,?"?([^"]+)"?', line)
                if match:
                    self.run_datetime = match.group(1).strip()

            # Conditioned areas
            if 'NonRes Cond. Area:' in line:
                match = re.search(r'NonRes Cond\. Area:,+,?(\d+\.?\d*)', line)
                if match:
                    self.nonres_area = float(match.group(1))

            if 'Residential Cond. Area:' in line:
                match = re.search(r'Residential Cond\. Area:,+,?(\d+\.?\d*)', line)
                if match:
                    self.res_area = float(match.group(1))

            # Model type
            if 'Model:' in line and 'Model File:' not in line:
                match = re.search(r'Model:,+,?"?([^"]+)"?', line)
                if match:
                    self.model_type = match.group(1).strip()

            # Model file path
            if 'Model File:' in line:
                match = re.search(r'Model File:,+,?"?([^"]+)"?', line)
                if match:
                    self.model_file = match.group(1).strip()

    def _find_column_headers(self, lines: List[str]) -> Tuple[int, List[str]]:
        """Find the column header row and return its index and parsed headers."""
        for i, line in enumerate(lines):
            # The data header row starts with "Mo,Da,Hr"
            if line.strip().startswith('Mo,Da,Hr'):
                # Parse the CSV header row
                reader = csv.reader([line])
                headers = next(reader)
                return i, headers

        raise ValueError("Could not find column headers (Mo,Da,Hr row)")

    def _parse_single_use_data(self, lines: List[str], start_idx: int) -> List[HourlyEnergy]:
        """Parse hourly data for single-use (Res-only or NR-only) building."""
        hourly_data = []

        for line in lines[start_idx:]:
            line = line.strip()
            if not line:
                continue

            # Parse CSV row
            reader = csv.reader([line])
            try:
                row = next(reader)
            except StopIteration:
                continue

            # Skip if not enough columns or not a data row
            if len(row) < 50:
                continue

            try:
                month = int(row[COL_MONTH])
                day = int(row[COL_DAY])
                hour = int(row[COL_HOUR])
            except (ValueError, IndexError):
                continue

            # Skip invalid dates
            if not (1 <= month <= 12 and 1 <= day <= 31 and 1 <= hour <= 24):
                continue

            hourly = self._parse_energy_section(
                row, month, day, hour,
                elec_start=SINGLE_USE_ELEC_START,
                gas_start=SINGLE_USE_GAS_START,
                tdv_start=SINGLE_USE_TDV_START,
                source_start=SINGLE_USE_SOURCE_START,
                co2_start=SINGLE_USE_CO2_START,
                pv_col=SINGLE_USE_PV,
                battery_col=SINGLE_USE_BATTERY,
            )
            hourly_data.append(hourly)

        return hourly_data

    def _parse_mixed_use_data(
        self, lines: List[str], start_idx: int
    ) -> Tuple[List[HourlyEnergy], List[HourlyEnergy], List[HourlyEnergy]]:
        """Parse hourly data for mixed-use building.

        Returns:
            Tuple of (nonres_hourly, res_hourly, combined_hourly)
        """
        nonres_data = []
        res_data = []
        combined_data = []

        for line in lines[start_idx:]:
            line = line.strip()
            if not line:
                continue

            # Parse CSV row
            reader = csv.reader([line])
            try:
                row = next(reader)
            except StopIteration:
                continue

            # Mixed-use needs more columns
            if len(row) < 100:
                continue

            try:
                month = int(row[COL_MONTH])
                day = int(row[COL_DAY])
                hour = int(row[COL_HOUR])
            except (ValueError, IndexError):
                continue

            if not (1 <= month <= 12 and 1 <= day <= 31 and 1 <= hour <= 24):
                continue

            # Parse NonRes section
            nonres = self._parse_energy_section(
                row, month, day, hour,
                elec_start=MIXED_NONRES_ELEC_START,
                gas_start=MIXED_NONRES_GAS_START,
                tdv_start=MIXED_NONRES_TDV_START,
                source_start=MIXED_NONRES_SOURCE_START,
                co2_start=MIXED_NONRES_CO2_START,
                pv_col=None,  # PV/Battery assigned to combined only
                battery_col=None,
            )
            nonres_data.append(nonres)

            # Parse Res section
            res = self._parse_energy_section(
                row, month, day, hour,
                elec_start=MIXED_RES_ELEC_START,
                gas_start=MIXED_RES_GAS_START,
                tdv_start=MIXED_RES_TDV_START,
                source_start=MIXED_RES_SOURCE_START,
                co2_start=MIXED_RES_CO2_START,
                pv_col=None,
                battery_col=None,
            )
            res_data.append(res)

            # Create combined record
            combined = self._combine_hourly_records(nonres, res)
            # Add PV/Battery to combined (building-wide)
            combined.pv_generation_kwh = abs(self._safe_float(row, MIXED_PV))
            combined.battery_kwh = self._safe_float(row, MIXED_BATTERY)
            combined_data.append(combined)

        return nonres_data, res_data, combined_data

    def _parse_energy_section(
        self,
        row: List[str],
        month: int,
        day: int,
        hour: int,
        elec_start: int,
        gas_start: int,
        tdv_start: int,
        source_start: int,
        co2_start: int,
        pv_col: Optional[int],
        battery_col: Optional[int],
    ) -> HourlyEnergy:
        """Parse one energy section (NonRes or Res) from a row."""
        # Electric end-uses (kWh)
        elec_heating = self._safe_float(row, elec_start + ELEC_SPC_HEAT)
        elec_cooling = self._safe_float(row, elec_start + ELEC_SPC_COOL)
        elec_fans = self._safe_float(row, elec_start + ELEC_INDR_FANS)
        elec_heat_rej = self._safe_float(row, elec_start + ELEC_HEAT_REJ)
        elec_pumps = self._safe_float(row, elec_start + ELEC_PUMP_MISC)
        elec_dhw = self._safe_float(row, elec_start + ELEC_DOM_HW)
        elec_lighting = self._safe_float(row, elec_start + ELEC_LIGHTING)
        elec_receptacle = self._safe_float(row, elec_start + ELEC_RECEPT)
        elec_process = self._safe_float(row, elec_start + ELEC_PROCESS)
        elec_exterior = self._safe_float(row, elec_start + ELEC_OTHR_LTG)
        elec_total = self._safe_float(row, elec_start + ELEC_TOTAL)

        # Gas end-uses (kBtu -> therms)
        gas_heating_kbtu = self._safe_float(row, gas_start + GAS_SPC_HEAT)
        gas_dhw_kbtu = self._safe_float(row, gas_start + GAS_DOM_HW)
        gas_process_kbtu = self._safe_float(row, gas_start + GAS_PROCESS)
        gas_total_kbtu = self._safe_float(row, gas_start + GAS_TOTAL)

        # Convert kBtu to therms (1 therm = 100 kBtu)
        gas_heating_therm = gas_heating_kbtu / 100.0
        gas_dhw_therm = gas_dhw_kbtu / 100.0
        gas_process_therm = gas_process_kbtu / 100.0
        gas_total_therm = gas_total_kbtu / 100.0

        # TDV multipliers
        tdv_elec = self._safe_float(row, tdv_start)
        tdv_gas = self._safe_float(row, tdv_start + 1)

        # Source energy multipliers
        source_elec = self._safe_float(row, source_start)
        source_gas = self._safe_float(row, source_start + 1)

        # CO2 multipliers
        co2_elec = self._safe_float(row, co2_start)
        co2_gas = self._safe_float(row, co2_start + 1)

        # PV and Battery
        pv_kwh = abs(self._safe_float(row, pv_col)) if pv_col is not None else 0.0
        battery_kwh = self._safe_float(row, battery_col) if battery_col is not None else 0.0

        return HourlyEnergy(
            month=month,
            day=day,
            hour=hour,
            elec_total_kwh=elec_total,
            elec_heating_kwh=elec_heating,
            elec_cooling_kwh=elec_cooling,
            elec_fans_kwh=elec_fans,
            elec_pumps_kwh=elec_pumps + elec_heat_rej,
            elec_dhw_kwh=elec_dhw,
            elec_lighting_kwh=elec_lighting,
            elec_receptacle_kwh=elec_receptacle,
            elec_process_kwh=elec_process,
            elec_exterior_kwh=elec_exterior,
            gas_total_therm=gas_total_therm,
            gas_heating_therm=gas_heating_therm,
            gas_dhw_therm=gas_dhw_therm,
            gas_process_therm=gas_process_therm,
            pv_generation_kwh=pv_kwh,
            battery_kwh=battery_kwh,
            tdv_elec=tdv_elec,
            tdv_gas=tdv_gas,
            source_elec=source_elec,
            source_gas=source_gas,
            co2_elec=co2_elec,
            co2_gas=co2_gas,
        )

    def _combine_hourly_records(self, nonres: HourlyEnergy, res: HourlyEnergy) -> HourlyEnergy:
        """Combine NonRes and Res hourly records into one."""
        # For TDV/Source/CO2 multipliers, use weighted average or take from one
        # (they should be the same since they're time-dependent, not building-type dependent)
        return HourlyEnergy(
            month=nonres.month,
            day=nonres.day,
            hour=nonres.hour,
            elec_total_kwh=nonres.elec_total_kwh + res.elec_total_kwh,
            elec_heating_kwh=nonres.elec_heating_kwh + res.elec_heating_kwh,
            elec_cooling_kwh=nonres.elec_cooling_kwh + res.elec_cooling_kwh,
            elec_fans_kwh=nonres.elec_fans_kwh + res.elec_fans_kwh,
            elec_pumps_kwh=nonres.elec_pumps_kwh + res.elec_pumps_kwh,
            elec_dhw_kwh=nonres.elec_dhw_kwh + res.elec_dhw_kwh,
            elec_lighting_kwh=nonres.elec_lighting_kwh + res.elec_lighting_kwh,
            elec_receptacle_kwh=nonres.elec_receptacle_kwh + res.elec_receptacle_kwh,
            elec_process_kwh=nonres.elec_process_kwh + res.elec_process_kwh,
            elec_exterior_kwh=nonres.elec_exterior_kwh + res.elec_exterior_kwh,
            gas_total_therm=nonres.gas_total_therm + res.gas_total_therm,
            gas_heating_therm=nonres.gas_heating_therm + res.gas_heating_therm,
            gas_dhw_therm=nonres.gas_dhw_therm + res.gas_dhw_therm,
            gas_process_therm=nonres.gas_process_therm + res.gas_process_therm,
            pv_generation_kwh=0.0,  # Set by caller
            battery_kwh=0.0,        # Set by caller
            # Use NonRes multipliers (they should be similar for same hour)
            tdv_elec=nonres.tdv_elec,
            tdv_gas=nonres.tdv_gas,
            source_elec=nonres.source_elec,
            source_gas=nonres.source_gas,
            co2_elec=nonres.co2_elec,
            co2_gas=nonres.co2_gas,
        )

    def _safe_float(self, row: List[str], idx: Optional[int]) -> float:
        """Safely extract float from row at index."""
        if idx is None:
            return 0.0
        try:
            if idx < 0:
                idx = len(row) + idx
            if 0 <= idx < len(row):
                val = row[idx].strip()
                if val:
                    return float(val)
        except (ValueError, IndexError):
            pass
        return 0.0

    def _calculate_annual_summary(self, hourly: List[HourlyEnergy]) -> AnnualEnergySummary:
        """Calculate annual totals and peaks from hourly data."""
        if not hourly:
            return AnnualEnergySummary()

        summary = AnnualEnergySummary()

        # Track monthly peaks
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

            # PV generation
            summary.pv_generation_kwh += h.pv_generation_kwh

            # TDV totals (multiply usage by multiplier)
            summary.tdv_elec_total += h.elec_total_kwh * h.tdv_elec
            summary.tdv_gas_total += h.gas_total_therm * 100 * h.tdv_gas / 1000  # Convert

            # Source energy
            summary.source_elec_total += h.elec_total_kwh * h.source_elec
            summary.source_gas_total += h.gas_total_therm * h.source_gas

            # CO2 emissions
            summary.co2_elec_total += h.elec_total_kwh * h.co2_elec
            summary.co2_gas_total += h.gas_total_therm * h.co2_gas

            # Track peak demand (hourly kWh = demand for that hour in kW)
            demand_kw = h.elec_total_kwh  # Assuming hourly kWh = kW for that hour
            if demand_kw > summary.peak_demand_kw:
                summary.peak_demand_kw = demand_kw
                summary.peak_demand_month = h.month
                summary.peak_demand_hour = h.hour

            # Monthly peak tracking
            if h.month not in monthly_peaks or demand_kw > monthly_peaks[h.month]:
                monthly_peaks[h.month] = demand_kw

        # Store monthly peaks
        summary.monthly_peaks_kw = monthly_peaks

        # Net electricity
        summary.net_elec_kwh = summary.total_elec_kwh - summary.pv_generation_kwh

        # Combined totals
        summary.tdv_total = summary.tdv_elec_total + summary.tdv_gas_total
        summary.source_total = summary.source_elec_total + summary.source_gas_total
        summary.co2_total = summary.co2_elec_total + summary.co2_gas_total

        return summary

    def _extract_project_name(self) -> str:
        """Extract project name from model file or run title."""
        if self.model_file:
            # Get filename without extension
            path = Path(self.model_file)
            return path.stem
        if self.run_title:
            return self.run_title
        return "Unknown Project"

    def _infer_building_type(self) -> str:
        """Infer building type from areas and ruleset."""
        if self.res_area > 0 and self.nonres_area == 0:
            return "Residential"
        elif self.res_area == 0 and self.nonres_area > 0:
            return "NonResidential"
        elif self.res_area > 0 and self.nonres_area > 0:
            return "MixedUse"
        return "Unknown"


def parse_hourly_results(filepath: str | Path) -> SimulationOutput:
    """
    Parse a CBECC HourlyResults.csv file.

    Args:
        filepath: Path to the HourlyResults.csv file

    Returns:
        SimulationOutput with parsed data including:
        - annual: Combined annual summary
        - hourly: Combined hourly data (8760 records)
        - annual_nonres/annual_res: Separate summaries for mixed-use (None for single-use)
        - hourly_nonres/hourly_res: Separate hourly data for mixed-use (None for single-use)
    """
    parser = HourlyResultsParser()
    return parser.parse_file(filepath)
