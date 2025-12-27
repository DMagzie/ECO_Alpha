"""
Parser for CBECC HVACCAPS.CSV files.

Extracts auto-sized HVAC capacities for residential buildings:
- System names
- Heating capacity (kBtu/h)
- Cooling capacity (kBtu/h)

This data is essential for residential buildings where the HVACSecondary.csv
shows -99996 (missing values) for capacities.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional
from datetime import datetime
import csv
import logging
import re

logger = logging.getLogger(__name__)


@dataclass
class HVACCapacity:
    """HVAC system capacity from auto-sizing."""
    system_name: str
    heating_cap_kbtuh: float  # kBtu/h
    cooling_cap_kbtuh: float  # kBtu/h


@dataclass
class HVACCapsOutput:
    """Complete output from HVACCAPS.CSV parsing."""
    run_datetime: Optional[datetime] = None
    run_datetime_str: str = ''
    capacities: List[HVACCapacity] = field(default_factory=list)

    # Aggregated totals
    total_heating_cap_kbtuh: float = 0.0
    total_cooling_cap_kbtuh: float = 0.0
    system_count: int = 0

    def calculate_totals(self):
        """Calculate aggregate totals from individual systems."""
        self.total_heating_cap_kbtuh = sum(c.heating_cap_kbtuh for c in self.capacities)
        self.total_cooling_cap_kbtuh = sum(c.cooling_cap_kbtuh for c in self.capacities)
        self.system_count = len(self.capacities)


class HVACCapsParser:
    """Parser for CBECC HVACCAPS.CSV files."""

    def __init__(self):
        self.output = HVACCapsOutput()
        self.parse_errors: List[str] = []
        self.parse_warnings: List[str] = []

    def parse_file(self, filepath: Path) -> HVACCapsOutput:
        """
        Parse HVACCAPS.CSV and return structured output.

        Args:
            filepath: Path to HVACCAPS.CSV file

        Returns:
            HVACCapsOutput with all parsed systems
        """
        filepath = Path(filepath)
        if not filepath.exists():
            raise FileNotFoundError(f"File not found: {filepath}")

        # Reset state
        self.output = HVACCapsOutput()
        self.parse_errors = []
        self.parse_warnings = []

        try:
            with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
                reader = csv.reader(f)
                rows = list(reader)
        except Exception as e:
            raise ValueError(f"Failed to read CSV: {e}")

        if len(rows) < 2:
            raise ValueError("File must have header and data rows")

        # Parse header and data
        header = rows[0]
        data = rows[1]

        self._parse_header_and_data(header, data)
        self.output.calculate_totals()

        return self.output

    def _parse_header_and_data(self, header: List[str], data: List[str]) -> None:
        """Parse the repeating column groups from header and data."""
        # First column is runDateTime
        if data and len(data) > 0:
            self.output.run_datetime_str = data[0]
            self.output.run_datetime = self._parse_datetime(data[0])

        # Remaining columns are in groups of 3: SysName, HtgCap, ClgCap
        # Find the starting index (skip runDateTime)
        col_idx = 1

        while col_idx + 2 < len(header) and col_idx + 2 < len(data):
            # Verify expected column pattern
            if header[col_idx] != 'SysName':
                col_idx += 1
                continue

            try:
                sys_name = data[col_idx].strip() if col_idx < len(data) else ''
                htg_cap_str = data[col_idx + 1] if col_idx + 1 < len(data) else ''
                clg_cap_str = data[col_idx + 2] if col_idx + 2 < len(data) else ''

                # Skip empty system names
                if not sys_name:
                    col_idx += 3
                    continue

                # Parse capacities
                htg_cap = self._safe_float(htg_cap_str, 0.0)
                clg_cap = self._safe_float(clg_cap_str, 0.0)

                capacity = HVACCapacity(
                    system_name=sys_name,
                    heating_cap_kbtuh=htg_cap,
                    cooling_cap_kbtuh=clg_cap,
                )
                self.output.capacities.append(capacity)

            except Exception as e:
                self.parse_warnings.append(f"Error parsing system at column {col_idx}: {e}")

            col_idx += 3

    def _parse_datetime(self, dt_str: str) -> Optional[datetime]:
        """Parse CBECC datetime format (e.g., 'Fri 07-Mar-25   6:1 pm')."""
        if not dt_str:
            return None

        # Try common CBECC formats
        formats = [
            '%a %d-%b-%y %I:%M %p',    # "Fri 07-Mar-25  6:01 pm"
            '%a %d-%b-%y %I:%M%p',     # "Fri 07-Mar-25  6:01pm"
            '%a %d-%b-%y %H:%M',       # "Fri 07-Mar-25  18:01"
        ]

        # Clean up the string - remove extra spaces
        dt_str = ' '.join(dt_str.split())

        # Fix single-digit hour format (e.g., "6:1 pm" -> "6:01 pm")
        dt_str = re.sub(r'(\d+):(\d)\s+(am|pm)', r'\1:0\2 \3', dt_str, flags=re.IGNORECASE)

        for fmt in formats:
            try:
                return datetime.strptime(dt_str, fmt)
            except ValueError:
                continue

        return None

    @staticmethod
    def _safe_float(value: str, default: float = 0.0) -> float:
        """Safely parse a float value."""
        if not value or not value.strip():
            return default
        try:
            return float(value)
        except ValueError:
            return default


def parse_hvac_caps(filepath: Path) -> HVACCapsOutput:
    """
    Parse an HVACCAPS.CSV file.

    Args:
        filepath: Path to the CSV file

    Returns:
        HVACCapsOutput with all parsed systems
    """
    parser = HVACCapsParser()
    return parser.parse_file(filepath)
