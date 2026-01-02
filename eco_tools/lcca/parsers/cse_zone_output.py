"""
CSE Zone Output Parser
======================

Parse CSE simulation output CSV files with zone-level meter data.

This module extracts:
- Hourly energy consumption by meter
- End-use breakdown (cooling, heating, lighting, etc.)
- Annual totals and peak demand
- Zone-specific energy data from transformed CSE runs

The parser handles the standard CSE MTR export format with columns:
Meter, Mon, Day, Hr, Subhr, Tot, Clg, Htg, HPBU, Dhw, etc.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
import csv
import logging
import re

logger = logging.getLogger(__name__)


# =============================================================================
# CONSTANTS
# =============================================================================

# Expected columns in CSE MTR export
CSE_MTR_COLUMNS = [
    "Meter", "Mon", "Day", "Hr", "Subhr",
    "Tot",      # Total
    "Clg",      # Cooling
    "Htg",      # Heating
    "HPBU",     # Heat pump backup
    "Dhw",      # Domestic hot water
    "DhwBU",    # DHW backup
    "DhwMFL",   # DHW main fuel loss
    "FanC",     # Cooling fan
    "FanH",     # Heating fan
    "FanV",     # Ventilation fan
    "Fan",      # Other fans
    "Aux",      # Auxiliary
    "Proc",     # Process
    "Lit",      # Lighting
    "Rcp",      # Receptacles
    "Ext",      # Exterior
    "Refr",     # Refrigeration
    "Dish",     # Dishwasher
    "Dry",      # Dryer
    "Wash",     # Washing machine
    "Cook",     # Cooking
    "User1",    # User-defined 1
    "User2",    # User-defined 2
    "BT",       # Battery
    "PV",       # Photovoltaic
]

# End-use categories for aggregation
END_USE_CATEGORIES = {
    "hvac": ["Clg", "Htg", "HPBU", "FanC", "FanH", "FanV", "Fan", "Aux"],
    "dhw": ["Dhw", "DhwBU", "DhwMFL"],
    "lighting": ["Lit", "Ext"],
    "plug_loads": ["Rcp", "Proc", "Refr"],
    "appliances": ["Dish", "Dry", "Wash", "Cook"],
    "renewables": ["PV", "BT"],
}


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class ZoneHourlyData:
    """
    Hourly energy data for a single zone/meter.

    Contains 8760 hourly values for total and end-use breakdown.
    """
    zone_name: str
    meter_name: str

    # Hourly data arrays (8760 values each)
    total_kwh: List[float] = field(default_factory=list)
    cooling_kwh: List[float] = field(default_factory=list)
    heating_kwh: List[float] = field(default_factory=list)
    heating_backup_kwh: List[float] = field(default_factory=list)
    dhw_kwh: List[float] = field(default_factory=list)
    lighting_kwh: List[float] = field(default_factory=list)
    receptacle_kwh: List[float] = field(default_factory=list)
    ventilation_kwh: List[float] = field(default_factory=list)
    pv_kwh: List[float] = field(default_factory=list)
    battery_kwh: List[float] = field(default_factory=list)

    # Other end uses combined
    other_kwh: List[float] = field(default_factory=list)

    @property
    def annual_total_kwh(self) -> float:
        """Annual total energy consumption."""
        return sum(self.total_kwh)

    @property
    def annual_cooling_kwh(self) -> float:
        """Annual cooling energy."""
        return sum(self.cooling_kwh)

    @property
    def annual_heating_kwh(self) -> float:
        """Annual heating energy (including backup)."""
        return sum(self.heating_kwh) + sum(self.heating_backup_kwh)

    @property
    def annual_dhw_kwh(self) -> float:
        """Annual DHW energy."""
        return sum(self.dhw_kwh)

    @property
    def annual_lighting_kwh(self) -> float:
        """Annual lighting energy."""
        return sum(self.lighting_kwh)

    @property
    def annual_receptacle_kwh(self) -> float:
        """Annual receptacle energy."""
        return sum(self.receptacle_kwh)

    @property
    def annual_pv_kwh(self) -> float:
        """Annual PV generation (negative = generation)."""
        return sum(self.pv_kwh)

    @property
    def peak_demand_kw(self) -> float:
        """Peak hourly demand."""
        return max(self.total_kwh) if self.total_kwh else 0.0

    @property
    def hours_count(self) -> int:
        """Number of hourly data points."""
        return len(self.total_kwh)

    @property
    def is_complete(self) -> bool:
        """Check if data has full 8760 hours."""
        return len(self.total_kwh) == 8760

    def get_end_use_breakdown(self) -> Dict[str, float]:
        """Get annual end-use breakdown."""
        return {
            "cooling": self.annual_cooling_kwh,
            "heating": self.annual_heating_kwh,
            "dhw": self.annual_dhw_kwh,
            "lighting": self.annual_lighting_kwh,
            "receptacle": self.annual_receptacle_kwh,
            "ventilation": sum(self.ventilation_kwh),
            "pv": self.annual_pv_kwh,
            "battery": sum(self.battery_kwh),
            "other": sum(self.other_kwh),
        }

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "zone_name": self.zone_name,
            "meter_name": self.meter_name,
            "annual_total_kwh": self.annual_total_kwh,
            "peak_demand_kw": self.peak_demand_kw,
            "end_uses": self.get_end_use_breakdown(),
            "hours_count": self.hours_count,
        }


@dataclass
class ZoneGasHourlyData:
    """
    Hourly gas energy data for a single zone/meter.

    Contains 8760 hourly values in therms for gas end-uses.
    Gas has fewer end-uses than electric: heating, DHW, cooking.
    """
    zone_name: str
    meter_name: str

    # Hourly data arrays (8760 values each, in therms)
    total_therm: List[float] = field(default_factory=list)
    heating_therm: List[float] = field(default_factory=list)
    dhw_therm: List[float] = field(default_factory=list)
    cooking_therm: List[float] = field(default_factory=list)

    # Other gas uses combined
    other_therm: List[float] = field(default_factory=list)

    @property
    def annual_total_therm(self) -> float:
        """Annual total gas consumption in therms."""
        return sum(self.total_therm)

    @property
    def annual_heating_therm(self) -> float:
        """Annual heating gas in therms."""
        return sum(self.heating_therm)

    @property
    def annual_dhw_therm(self) -> float:
        """Annual DHW gas in therms."""
        return sum(self.dhw_therm)

    @property
    def annual_cooking_therm(self) -> float:
        """Annual cooking gas in therms."""
        return sum(self.cooking_therm)

    @property
    def peak_demand_therm(self) -> float:
        """Peak hourly gas demand in therms."""
        return max(self.total_therm) if self.total_therm else 0.0

    @property
    def hours_count(self) -> int:
        """Number of hourly data points."""
        return len(self.total_therm)

    @property
    def is_complete(self) -> bool:
        """Check if data has full 8760 hours."""
        return len(self.total_therm) == 8760

    def get_end_use_breakdown(self) -> Dict[str, float]:
        """Get annual end-use breakdown in therms."""
        return {
            "heating": self.annual_heating_therm,
            "dhw": self.annual_dhw_therm,
            "cooking": self.annual_cooking_therm,
            "other": sum(self.other_therm),
        }

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "zone_name": self.zone_name,
            "meter_name": self.meter_name,
            "annual_total_therm": self.annual_total_therm,
            "peak_demand_therm": self.peak_demand_therm,
            "end_uses": self.get_end_use_breakdown(),
            "hours_count": self.hours_count,
        }


@dataclass
class CSEZoneOutputModel:
    """
    Complete parsed output from CSE simulation.

    Contains hourly data for all electric and gas meters in the simulation.
    """
    filepath: str = ""
    project_name: str = ""
    run_datetime: str = ""

    # Electric meter data by meter name
    meters: Dict[str, ZoneHourlyData] = field(default_factory=dict)

    # Gas meter data by meter name
    gas_meters: Dict[str, ZoneGasHourlyData] = field(default_factory=dict)

    # Parsing statistics
    total_rows: int = 0
    parse_errors: List[str] = field(default_factory=list)
    parse_warnings: List[str] = field(default_factory=list)

    @property
    def meter_count(self) -> int:
        """Number of electric meters parsed."""
        return len(self.meters)

    @property
    def gas_meter_count(self) -> int:
        """Number of gas meters parsed."""
        return len(self.gas_meters)

    @property
    def total_annual_kwh(self) -> float:
        """Total annual electric energy across all meters."""
        return sum(m.annual_total_kwh for m in self.meters.values())

    @property
    def total_annual_therm(self) -> float:
        """Total annual gas energy across all meters."""
        return sum(m.annual_total_therm for m in self.gas_meters.values())

    def get_meter(self, meter_name: str) -> Optional[ZoneHourlyData]:
        """Get data for a specific electric meter."""
        return self.meters.get(meter_name)

    def get_gas_meter(self, meter_name: str) -> Optional[ZoneGasHourlyData]:
        """Get data for a specific gas meter."""
        return self.gas_meters.get(meter_name)

    def get_zone_meters(self, zone_prefix: str = "MtrElec_") -> Dict[str, ZoneHourlyData]:
        """Get all zone-level electric meters (matching prefix)."""
        return {
            name: data for name, data in self.meters.items()
            if name.startswith(zone_prefix)
        }

    def get_zone_gas_meters(self, zone_prefix: str = "MtrGas_") -> Dict[str, ZoneGasHourlyData]:
        """Get all zone-level gas meters (matching prefix)."""
        return {
            name: data for name, data in self.gas_meters.items()
            if name.startswith(zone_prefix)
        }

    def summary(self) -> Dict[str, Any]:
        """Get summary statistics."""
        return {
            "project_name": self.project_name,
            "meter_count": self.meter_count,
            "gas_meter_count": self.gas_meter_count,
            "total_rows": self.total_rows,
            "total_annual_kwh": self.total_annual_kwh,
            "total_annual_therm": self.total_annual_therm,
            "meters": [
                {
                    "name": name,
                    "annual_kwh": data.annual_total_kwh,
                    "peak_kw": data.peak_demand_kw,
                }
                for name, data in sorted(self.meters.items())
            ],
            "gas_meters": [
                {
                    "name": name,
                    "annual_therm": data.annual_total_therm,
                    "peak_therm": data.peak_demand_therm,
                }
                for name, data in sorted(self.gas_meters.items())
            ],
        }


# =============================================================================
# PARSER
# =============================================================================

class CSEZoneOutputParser:
    """
    Parser for CSE simulation output CSV files.

    Extracts hourly energy data for each meter in the simulation.

    Example usage:
        >>> parser = CSEZoneOutputParser()
        >>> result = parser.parse_file("simulation-AP-CSE.CSV")
        >>> for meter_name, data in result.meters.items():
        ...     print(f"{meter_name}: {data.annual_total_kwh:.0f} kWh")
    """

    # Regex for header detection
    HEADER_PATTERN = re.compile(r'^"Meter","Mon","Day","Hr"')

    def __init__(self):
        """Initialize the parser."""
        self.output = CSEZoneOutputModel()
        self._column_indices: Dict[str, int] = {}

    def parse_file(self, filepath: Path) -> CSEZoneOutputModel:
        """
        Parse a CSE output CSV file.

        Args:
            filepath: Path to CSE CSV output file

        Returns:
            CSEZoneOutputModel with parsed data
        """
        filepath = Path(filepath)
        if not filepath.exists():
            raise FileNotFoundError(f"File not found: {filepath}")

        # Reset state
        self.output = CSEZoneOutputModel(filepath=str(filepath))
        self._column_indices = {}

        try:
            self._parse_csv(filepath)
            self._validate_results()

        except Exception as e:
            self.output.parse_errors.append(f"Parse error: {e}")
            logger.error(f"Error parsing {filepath}: {e}")

        return self.output

    def _parse_csv(self, filepath: Path) -> None:
        """Parse the CSV file content."""
        encodings = ['utf-8', 'latin-1', 'cp1252']

        for encoding in encodings:
            try:
                with open(filepath, 'r', encoding=encoding, newline='') as f:
                    self._process_csv_content(f)
                break
            except UnicodeDecodeError:
                continue

    def _process_csv_content(self, file_obj) -> None:
        """Process the CSV file content."""
        reader = csv.reader(file_obj)
        header_found = False

        for row_num, row in enumerate(reader, 1):
            if not row:
                continue

            # Skip initial metadata rows
            if row_num <= 2:
                if row_num == 1 and len(row) > 0:
                    # Extract project name from first line
                    self.output.project_name = row[0].strip('"')
                elif row_num == 2 and len(row) > 0:
                    self.output.run_datetime = row[0].strip('"')
                continue

            # Look for header row
            if not header_found:
                if len(row) > 0 and row[0].strip('"') == "Meter":
                    self._parse_header(row)
                    header_found = True
                continue

            # Parse data row
            try:
                self._parse_data_row(row)
                self.output.total_rows += 1
            except Exception as e:
                self.output.parse_warnings.append(
                    f"Row {row_num}: {e}"
                )

    def _parse_header(self, row: List[str]) -> None:
        """Parse the header row and build column index map."""
        for i, col in enumerate(row):
            col_name = col.strip('"').strip()
            self._column_indices[col_name] = i

        logger.debug(f"Parsed header with {len(self._column_indices)} columns")

    def _parse_data_row(self, row: List[str]) -> None:
        """Parse a single data row (electric or gas)."""
        if len(row) < 5:
            return

        # Get meter name
        meter_idx = self._column_indices.get("Meter", 0)
        meter_name = row[meter_idx].strip('"').strip()

        if not meter_name:
            return

        # Check if this is a gas meter
        if meter_name.startswith("MtrGas") or meter_name.startswith("MtrNatGas"):
            self._parse_gas_data_row(row, meter_name)
        else:
            self._parse_elec_data_row(row, meter_name)

    def _parse_elec_data_row(self, row: List[str], meter_name: str) -> None:
        """Parse an electric meter data row."""
        # Get or create meter data
        if meter_name not in self.output.meters:
            self.output.meters[meter_name] = ZoneHourlyData(
                zone_name=self._meter_to_zone_name(meter_name),
                meter_name=meter_name,
            )

        meter_data = self.output.meters[meter_name]

        # Parse energy values
        meter_data.total_kwh.append(self._get_value(row, "Tot"))
        meter_data.cooling_kwh.append(self._get_value(row, "Clg"))
        meter_data.heating_kwh.append(self._get_value(row, "Htg"))
        meter_data.heating_backup_kwh.append(self._get_value(row, "HPBU"))
        meter_data.dhw_kwh.append(self._get_value(row, "Dhw") + self._get_value(row, "DhwBU"))
        meter_data.lighting_kwh.append(self._get_value(row, "Lit"))
        meter_data.receptacle_kwh.append(self._get_value(row, "Rcp"))
        meter_data.ventilation_kwh.append(
            self._get_value(row, "FanV") + self._get_value(row, "Fan")
        )
        meter_data.pv_kwh.append(self._get_value(row, "PV"))
        meter_data.battery_kwh.append(self._get_value(row, "BT"))

        # Other end uses
        other_cols = ["FanC", "FanH", "Aux", "Proc", "Ext", "Refr",
                      "Dish", "Dry", "Wash", "Cook", "User1", "User2"]
        other_total = sum(self._get_value(row, col) for col in other_cols)
        meter_data.other_kwh.append(other_total)

    def _parse_gas_data_row(self, row: List[str], meter_name: str) -> None:
        """Parse a gas meter data row."""
        # Get or create gas meter data
        if meter_name not in self.output.gas_meters:
            self.output.gas_meters[meter_name] = ZoneGasHourlyData(
                zone_name=self._meter_to_zone_name(meter_name, is_gas=True),
                meter_name=meter_name,
            )

        meter_data = self.output.gas_meters[meter_name]

        # Parse gas energy values (in therms)
        # Gas meters have fewer end-uses: Tot, Htg, Dhw, Cook
        meter_data.total_therm.append(self._get_value(row, "Tot"))
        meter_data.heating_therm.append(
            self._get_value(row, "Htg") + self._get_value(row, "HPBU")
        )
        meter_data.dhw_therm.append(
            self._get_value(row, "Dhw") + self._get_value(row, "DhwBU")
        )
        meter_data.cooking_therm.append(self._get_value(row, "Cook"))

        # Other gas uses (less common)
        other_cols = ["Aux", "Proc", "User1", "User2"]
        other_total = sum(self._get_value(row, col) for col in other_cols)
        meter_data.other_therm.append(other_total)

    def _get_value(self, row: List[str], column: str) -> float:
        """Get a float value from a column."""
        idx = self._column_indices.get(column)
        if idx is None or idx >= len(row):
            return 0.0

        try:
            val_str = row[idx].strip('"').strip()
            if not val_str:
                return 0.0
            return float(val_str)
        except ValueError:
            return 0.0

    def _meter_to_zone_name(self, meter_name: str, is_gas: bool = False) -> str:
        """Convert meter name to zone name."""
        zone_name = meter_name

        # Remove meter prefix
        if zone_name.startswith("MtrElec_"):
            zone_name = zone_name[8:]
        elif zone_name.startswith("MtrGas_"):
            zone_name = zone_name[7:]
        elif zone_name.startswith("MtrNatGas_"):
            zone_name = zone_name[10:]
        elif zone_name.startswith("MtrNatGas"):  # No underscore
            zone_name = zone_name[9:]

        # Add -zn suffix if not present
        if not zone_name.endswith("-zn"):
            zone_name = zone_name + "-zn"

        return zone_name

    def _validate_results(self) -> None:
        """Validate parsed results (electric and gas)."""
        # Validate electric meters
        for meter_name, data in self.output.meters.items():
            if not data.is_complete:
                self.output.parse_warnings.append(
                    f"Electric meter {meter_name} has incomplete data ({data.hours_count} hours)"
                )

        # Validate gas meters
        for meter_name, data in self.output.gas_meters.items():
            if not data.is_complete:
                self.output.parse_warnings.append(
                    f"Gas meter {meter_name} has incomplete data ({data.hours_count} hours)"
                )


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def parse_cse_zone_output(filepath: Path) -> CSEZoneOutputModel:
    """
    Parse a CSE zone output CSV file.

    Args:
        filepath: Path to CSE CSV output file

    Returns:
        CSEZoneOutputModel with parsed data
    """
    parser = CSEZoneOutputParser()
    return parser.parse_file(filepath)


def format_zone_output_summary(model: CSEZoneOutputModel) -> str:
    """
    Format zone output model as summary text.

    Args:
        model: Parsed CSE zone output model

    Returns:
        Formatted summary string
    """
    lines = [
        "=" * 70,
        "CSE ZONE OUTPUT SUMMARY",
        "=" * 70,
        "",
        f"Project: {model.project_name}",
        f"Run: {model.run_datetime}",
        f"Electric Meters: {model.meter_count}",
        f"Gas Meters: {model.gas_meter_count}",
        f"Total Rows: {model.total_rows}",
        "",
        "Electric Meters:",
        "-" * 70,
        f"{'Meter':<40} {'Annual kWh':>12} {'Peak kW':>10}",
        "-" * 70,
    ]

    for name, data in sorted(model.meters.items()):
        lines.append(
            f"{name:<40} {data.annual_total_kwh:>12,.0f} {data.peak_demand_kw:>10.1f}"
        )

    if model.gas_meters:
        lines.extend([
            "",
            "Gas Meters:",
            "-" * 70,
            f"{'Meter':<40} {'Annual therm':>12} {'Peak therm':>10}",
            "-" * 70,
        ])
        for name, data in sorted(model.gas_meters.items()):
            lines.append(
                f"{name:<40} {data.annual_total_therm:>12,.1f} {data.peak_demand_therm:>10.2f}"
            )

    if model.parse_warnings:
        lines.extend([
            "",
            "Warnings:",
        ])
        for w in model.parse_warnings[:10]:
            lines.append(f"  - {w}")

    lines.append("=" * 70)

    return "\n".join(lines)


def get_zone_energy_summaries(
    model: CSEZoneOutputModel,
    zone_prefix: str = "MtrElec_",
) -> List[Dict[str, Any]]:
    """
    Get zone energy summaries from parsed output.

    Args:
        model: Parsed CSE zone output model
        zone_prefix: Prefix for zone-level meters

    Returns:
        List of zone energy summary dictionaries
    """
    summaries = []

    for name, data in model.meters.items():
        if not name.startswith(zone_prefix):
            continue

        summary = {
            "zone_name": data.zone_name,
            "meter_name": data.meter_name,
            "annual_elec_kwh": data.annual_total_kwh,
            "peak_demand_kw": data.peak_demand_kw,
            "hourly_elec_kwh": data.total_kwh.copy(),
            "end_uses": data.get_end_use_breakdown(),
            "is_complete": data.is_complete,
        }
        summaries.append(summary)

    return summaries
