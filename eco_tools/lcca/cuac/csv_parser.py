"""
CUAC CSV Parser
===============

Parser for CBECC CUAC.csv output files containing detailed energy consumption
data by bedroom type and end-use category.

The CUAC.csv file structure includes:
- Analysis inputs and metadata
- Monthly utility allowances by bedroom type
- Energy consumption summaries (cooling, heating, PV)
- Detailed electric kWh usage by end-use and bedroom type
- Detailed gas kBtu usage by end-use and bedroom type (usually zeros for all-electric)
- Hourly data by bedroom type

Usage:
    from eco_tools.lcca.cuac.csv_parser import parse_cuac_csv, CuacResults

    results = parse_cuac_csv('/path/to/CUAC.csv')

    # Access consumption by bedroom type
    for ut, data in results.consumption_by_unit_type.items():
        print(f"{ut}: {data.total_kwh} kWh/year")

    # Get building totals
    print(f"Building total: {results.building_total_kwh} kWh/year")
"""

import csv
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger('eco_tools.lcca.cuac.csv_parser')


@dataclass
class EndUseConsumption:
    """Annual consumption for a single end-use."""
    end_use: str
    daily_avg_kwh: float = 0.0
    annual_total_kwh: float = 0.0
    monthly_kwh: List[float] = field(default_factory=list)  # 12 values


@dataclass
class UnitTypeConsumption:
    """Consumption data for a single unit type (e.g., "1 Bedroom")."""
    unit_type: str
    num_bedrooms: int = 0
    end_uses: Dict[str, EndUseConsumption] = field(default_factory=dict)

    # Summary values
    cooling_kwh: float = 0.0
    heating_kwh: float = 0.0
    pv_generation_kwh: float = 0.0

    @property
    def total_kwh(self) -> float:
        """Total annual consumption across all end-uses."""
        return sum(eu.annual_total_kwh for eu in self.end_uses.values())

    def get_end_use(self, name: str) -> Optional[EndUseConsumption]:
        """Get consumption for a specific end-use."""
        return self.end_uses.get(name)


@dataclass
class MonthlyAllowance:
    """Monthly utility allowance for a unit type."""
    unit_type: str
    electric_allowance: float = 0.0
    gas_allowance: float = 0.0
    water_allowance: float = 0.0
    trash_allowance: float = 0.0
    total_allowance: float = 0.0


@dataclass
class CuacResults:
    """
    Complete parsed results from a CUAC.csv file.

    Contains all consumption data organized by bedroom type,
    monthly allowances, and building-wide totals.
    """
    # Metadata
    software_version: str = ""
    ruleset_version: str = ""
    tariff_date: str = ""
    run_date: str = ""
    model_file: str = ""
    analysis_status: str = ""

    # Project info
    project_name: str = ""
    site_address: str = ""
    locality: str = ""

    # Unit counts
    unit_counts: Dict[str, int] = field(default_factory=dict)  # e.g., {"1 Bedroom": 16}

    # Utility info
    electric_utility: str = ""
    electric_territory: str = ""
    electric_tariff: str = ""
    tariff_adjustment: str = ""
    gas_utility: str = ""

    # Consumption by unit type
    consumption_by_unit_type: Dict[str, UnitTypeConsumption] = field(default_factory=dict)

    # Monthly allowances
    allowances: Dict[str, MonthlyAllowance] = field(default_factory=dict)

    @property
    def building_total_kwh(self) -> float:
        """Total building consumption accounting for unit counts."""
        total = 0.0
        for ut, data in self.consumption_by_unit_type.items():
            count = self.unit_counts.get(ut, 1)
            total += data.total_kwh * count
        return total

    @property
    def building_cooling_kwh(self) -> float:
        """Total building cooling consumption."""
        total = 0.0
        for ut, data in self.consumption_by_unit_type.items():
            count = self.unit_counts.get(ut, 1)
            total += data.cooling_kwh * count
        return total

    @property
    def building_pv_kwh(self) -> float:
        """Total building PV generation."""
        total = 0.0
        for ut, data in self.consumption_by_unit_type.items():
            count = self.unit_counts.get(ut, 1)
            total += data.pv_generation_kwh * count
        return total

    def get_unit_type(self, name: str) -> Optional[UnitTypeConsumption]:
        """Get consumption data for a specific unit type."""
        return self.consumption_by_unit_type.get(name)

    def compare_to(self, other: 'CuacResults') -> Dict[str, Dict[str, float]]:
        """
        Compare this result to another, returning differences.

        Returns dict of {unit_type: {end_use: difference_kwh}}
        """
        comparison = {}
        for ut in self.consumption_by_unit_type:
            if ut in other.consumption_by_unit_type:
                comparison[ut] = {}
                self_data = self.consumption_by_unit_type[ut]
                other_data = other.consumption_by_unit_type[ut]

                for eu_name, self_eu in self_data.end_uses.items():
                    other_eu = other_data.end_uses.get(eu_name)
                    if other_eu:
                        diff = self_eu.annual_total_kwh - other_eu.annual_total_kwh
                        comparison[ut][eu_name] = diff

        return comparison


def _parse_row(line: str) -> List[str]:
    """Parse a CSV line handling quoted fields."""
    reader = csv.reader([line])
    try:
        return next(reader)
    except StopIteration:
        return []


def _safe_float(value: str) -> float:
    """Safely convert string to float."""
    try:
        return float(value.strip()) if value.strip() else 0.0
    except ValueError:
        return 0.0


def _safe_int(value: str) -> int:
    """Safely convert string to int."""
    try:
        return int(float(value.strip())) if value.strip() else 0
    except ValueError:
        return 0


def _extract_bedroom_count(unit_type: str) -> int:
    """Extract bedroom count from unit type string."""
    unit_type = unit_type.lower()
    if 'studio' in unit_type or '0 bedroom' in unit_type:
        return 0
    for i in range(1, 7):
        if f'{i} bedroom' in unit_type:
            return i
    return 0


def parse_cuac_csv(csv_path: str) -> CuacResults:
    """
    Parse a CUAC.csv file and return structured results.

    Args:
        csv_path: Path to the CUAC.csv file

    Returns:
        CuacResults object with all parsed data
    """
    csv_path = Path(csv_path)
    results = CuacResults()
    results.model_file = str(csv_path)

    with open(csv_path, 'r', encoding='utf-8-sig') as f:
        lines = f.readlines()

    # Parse metadata from header section
    _parse_header(lines, results)

    # Parse unit counts from dwelling units section
    _parse_unit_counts(lines, results)

    # Parse electric consumption by end-use
    _parse_electric_end_uses(lines, results)

    # Parse summary values (cooling, heating, PV)
    _parse_summary_values(lines, results)

    logger.info(f"Parsed CUAC results: {len(results.consumption_by_unit_type)} unit types, "
                f"building total {results.building_total_kwh:,.0f} kWh/year")

    return results


def _parse_header(lines: List[str], results: CuacResults) -> None:
    """Parse metadata from the header section."""
    for line in lines[:30]:
        if 'Software:' in line:
            row = _parse_row(line)
            for i, cell in enumerate(row):
                if 'Software:' in cell and i + 2 < len(row):
                    results.software_version = row[i + 2].strip().strip('"')
                    break

        if 'Ruleset:' in line:
            row = _parse_row(line)
            for i, cell in enumerate(row):
                if 'Ruleset:' in cell and i + 2 < len(row):
                    results.ruleset_version = row[i + 2].strip().strip('"')
                    break

        if 'Run Date/Time:' in line:
            row = _parse_row(line)
            for i, cell in enumerate(row):
                if 'Run Date/Time:' in cell and i + 2 < len(row):
                    results.run_date = row[i + 2].strip().strip('"')
                    break

        if 'Analysis Status:' in line:
            row = _parse_row(line)
            for i, cell in enumerate(row):
                if 'Analysis Status:' in cell and i + 2 < len(row):
                    results.analysis_status = row[i + 2].strip().strip('"')
                    break

        if 'Electric Utility:' in line:
            row = _parse_row(line)
            for i, cell in enumerate(row):
                if 'Electric Utility:' in cell and i + 2 < len(row):
                    results.electric_utility = row[i + 2].strip().strip('"')
                    break

        if 'Territory:' in line:
            row = _parse_row(line)
            for i, cell in enumerate(row):
                if 'Territory:' in cell and i + 1 < len(row):
                    results.electric_territory = row[i + 1].strip().strip('"')
                    break

        if 'Tariff:' in line and 'Adjustment' not in line:
            row = _parse_row(line)
            for i, cell in enumerate(row):
                if 'Tariff:' in cell and i + 1 < len(row):
                    results.electric_tariff = row[i + 1].strip().strip('"')
                    break

        if 'Adjustment:' in line:
            row = _parse_row(line)
            for i, cell in enumerate(row):
                if 'Adjustment:' in cell and i + 1 < len(row):
                    results.tariff_adjustment = row[i + 1].strip().strip('"')
                    break

        if 'Gas Utility:' in line:
            row = _parse_row(line)
            for i, cell in enumerate(row):
                if 'Gas Utility:' in cell and i + 2 < len(row):
                    results.gas_utility = row[i + 2].strip().strip('"')
                    break

        if 'Project Name:' in line:
            row = _parse_row(line)
            for i, cell in enumerate(row):
                if 'Project Name:' in cell and i + 1 < len(row):
                    results.project_name = row[i + 1].strip().strip('"')
                    break


def _parse_unit_counts(lines: List[str], results: CuacResults) -> None:
    """Parse dwelling unit counts by bedroom type."""
    in_unit_section = False

    for line in lines:
        if '# Dwelling Units by Type:' in line:
            in_unit_section = True
            continue

        if in_unit_section:
            row = _parse_row(line)
            if len(row) >= 5:
                # Check for bedroom type patterns
                for bedroom_type in ['Studio', '1 Bedroom', '2 Bedroom', '3 Bedroom',
                                     '4 Bedroom', '5 Bedroom', '6 Bedroom']:
                    if bedroom_type in row[2]:
                        # Affordable count is typically in column 4
                        count = _safe_int(row[4]) if len(row) > 4 else 0
                        if count > 0:
                            results.unit_counts[bedroom_type] = count

            # Stop at Total line
            if 'Total' in line:
                break


def _parse_electric_end_uses(lines: List[str], results: CuacResults) -> None:
    """Parse the 'Electric kWh Usage by End Use' section."""
    # Find section start
    start_idx = None
    for i, line in enumerate(lines):
        if 'Electric kWh Usage by End Use:' in line:
            start_idx = i + 2  # Skip header row
            break

    if start_idx is None:
        logger.warning("Could not find 'Electric kWh Usage by End Use' section")
        return

    current_unit_type = None

    for line in lines[start_idx:]:
        # Stop at gas section
        if 'Gas kBtu Usage by End Use:' in line:
            break

        row = _parse_row(line)
        if len(row) < 6:
            continue

        # Column layout: [0]=empty, [1]=empty, [2]=unit_type, [3]=end_use, [4]=daily_avg, [5]=total
        unit_type_cell = row[2].strip() if len(row) > 2 else ''
        end_use = row[3].strip() if len(row) > 3 else ''
        daily_avg = _safe_float(row[4]) if len(row) > 4 else 0.0
        total = _safe_float(row[5]) if len(row) > 5 else 0.0

        # Update current unit type if specified
        if unit_type_cell in ['1 Bedroom', '2 Bedroom', '3 Bedroom',
                              '4 Bedroom', '5 Bedroom', '6 Bedroom', 'Studio']:
            current_unit_type = unit_type_cell

            # Initialize unit type data if needed
            if current_unit_type not in results.consumption_by_unit_type:
                results.consumption_by_unit_type[current_unit_type] = UnitTypeConsumption(
                    unit_type=current_unit_type,
                    num_bedrooms=_extract_bedroom_count(current_unit_type)
                )

        # Skip non-data rows
        if not end_use or end_use in ['End Use', 'Unit', 'Daily Avg', 'Total']:
            continue

        # Skip if we don't have a current unit type
        if current_unit_type is None:
            continue

        # Parse monthly values (columns 7-18)
        monthly = []
        for i in range(7, min(19, len(row))):
            monthly.append(_safe_float(row[i]))

        # Store end-use consumption
        end_use_data = EndUseConsumption(
            end_use=end_use,
            daily_avg_kwh=daily_avg,
            annual_total_kwh=total,
            monthly_kwh=monthly
        )

        unit_data = results.consumption_by_unit_type[current_unit_type]
        unit_data.end_uses[end_use] = end_use_data


def _parse_summary_values(lines: List[str], results: CuacResults) -> None:
    """Parse cooling, heating, and PV summary values."""
    current_section = None

    for line in lines:
        # Track which section we're in
        if ',Cooling kWh Usage:' in line:
            current_section = 'cooling'
            continue
        elif ',Heating kWh Usage:' in line:
            current_section = 'heating_kwh'
            continue
        elif 'Photovoltaic kWh Generated On-site:' in line:
            current_section = 'pv'
            continue
        elif ',Heating kBtu Usage:' in line or 'Gas kBtu' in line:
            current_section = None  # Stop processing
            continue

        if current_section is None:
            continue

        row = _parse_row(line)
        if len(row) < 6:
            continue

        # Look for bedroom type rows
        unit_type = None
        for cell in row:
            cell = cell.strip()
            if cell in ['1 Bedroom', '2 Bedroom', '3 Bedroom',
                       '4 Bedroom', '5 Bedroom', '6 Bedroom', 'Studio']:
                unit_type = cell
                break

        if unit_type is None:
            continue

        # Find the annual total (look for large-ish number after the monthly values)
        # The annual total is typically the last numeric value before empty cells
        annual_total = 0.0
        for i in range(len(row) - 1, 0, -1):
            val = _safe_float(row[i])
            if val > 0:
                annual_total = val
                break

        # Initialize unit type if needed
        if unit_type not in results.consumption_by_unit_type:
            results.consumption_by_unit_type[unit_type] = UnitTypeConsumption(
                unit_type=unit_type,
                num_bedrooms=_extract_bedroom_count(unit_type)
            )

        unit_data = results.consumption_by_unit_type[unit_type]

        if current_section == 'cooling':
            unit_data.cooling_kwh = annual_total
        elif current_section == 'heating_kwh':
            unit_data.heating_kwh = annual_total
        elif current_section == 'pv':
            unit_data.pv_generation_kwh = annual_total


def compare_cuac_results(
    results1: CuacResults,
    results2: CuacResults,
    name1: str = "Scenario 1",
    name2: str = "Scenario 2"
) -> str:
    """
    Compare two CUAC results and return a formatted comparison string.

    Args:
        results1: First CUAC results
        results2: Second CUAC results
        name1: Display name for first scenario
        name2: Display name for second scenario

    Returns:
        Formatted comparison string
    """
    lines = []
    lines.append("=" * 70)
    lines.append(f"CUAC Comparison: {name1} vs {name2}")
    lines.append("=" * 70)

    # Compare by unit type
    all_unit_types = set(results1.consumption_by_unit_type.keys()) | \
                     set(results2.consumption_by_unit_type.keys())

    for ut in sorted(all_unit_types):
        lines.append(f"\n=== {ut} ===")

        data1 = results1.consumption_by_unit_type.get(ut)
        data2 = results2.consumption_by_unit_type.get(ut)

        if data1 is None or data2 is None:
            lines.append("  (missing in one scenario)")
            continue

        # Get all end-uses
        all_end_uses = set(data1.end_uses.keys()) | set(data2.end_uses.keys())

        lines.append(f"{'End Use':<18} {name1:>15} {name2:>15} {'Difference':>12}")
        lines.append("-" * 62)

        total1, total2 = 0.0, 0.0

        for eu in sorted(all_end_uses):
            val1 = data1.end_uses.get(eu, EndUseConsumption(eu)).annual_total_kwh
            val2 = data2.end_uses.get(eu, EndUseConsumption(eu)).annual_total_kwh
            diff = val1 - val2

            total1 += val1
            total2 += val2

            diff_str = f'{diff:+,.0f}' if diff != 0 else '-'
            lines.append(f"{eu:<18} {val1:>12,.0f} kWh {val2:>12,.0f} kWh {diff_str:>12}")

        lines.append("-" * 62)
        total_diff = total1 - total2
        lines.append(f"{'TOTAL':<18} {total1:>12,.0f} kWh {total2:>12,.0f} kWh {total_diff:+,.0f}")

    # Building summary
    lines.append("\n" + "=" * 70)
    lines.append("Building Summary")
    lines.append("=" * 70)

    lines.append(f"{name1}: {results1.building_total_kwh:,.0f} kWh/year")
    lines.append(f"{name2}: {results2.building_total_kwh:,.0f} kWh/year")

    diff = results1.building_total_kwh - results2.building_total_kwh
    if diff > 0:
        lines.append(f"{name2} uses {abs(diff):,.0f} kWh/year LESS ({abs(diff)/results1.building_total_kwh*100:.1f}%)")
    elif diff < 0:
        lines.append(f"{name1} uses {abs(diff):,.0f} kWh/year LESS ({abs(diff)/results2.building_total_kwh*100:.1f}%)")
    else:
        lines.append("No difference in total consumption")

    return "\n".join(lines)
