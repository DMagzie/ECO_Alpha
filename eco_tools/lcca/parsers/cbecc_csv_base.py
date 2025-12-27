"""
Base parser for multi-section CBECC CSV files.

CBECC simulation outputs use a non-standard CSV format with:
- Multiple sections per file
- Multi-line headers (section name, subheader categories, column names, units)
- Missing value indicator: -99996
- Blank lines between sections

This base class provides shared utilities for parsing these files.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple
import csv
import re
import logging

logger = logging.getLogger(__name__)


# CBECC uses -99996 to indicate missing/undefined values
MISSING_VALUE_INDICATOR = -99996


@dataclass
class CebeccSection:
    """Represents a parsed section from a CBECC CSV file."""
    name: str
    subheader: List[str] = field(default_factory=list)  # Category groupings
    columns: List[str] = field(default_factory=list)    # Column names
    units: List[str] = field(default_factory=list)      # Unit strings
    data: List[Dict[str, Any]] = field(default_factory=list)  # Parsed rows

    @property
    def row_count(self) -> int:
        """Number of data rows in this section."""
        return len(self.data)

    def get_column_index(self, column_name: str) -> Optional[int]:
        """Get index of a column by name (case-insensitive)."""
        column_lower = column_name.lower()
        for i, col in enumerate(self.columns):
            if col.lower() == column_lower:
                return i
        return None


class CebeccCsvParser:
    """
    Base class for multi-section CBECC CSV parsing.

    Subclasses should implement specific parsing logic for their file type
    (HVACSecondary, HVACPrimary, Envelope).
    """

    MISSING_VALUE = MISSING_VALUE_INDICATOR

    def __init__(self):
        self.sections: Dict[str, CebeccSection] = {}
        self.parse_errors: List[str] = []
        self.parse_warnings: List[str] = []

    def parse_file(self, filepath: Path) -> Dict[str, CebeccSection]:
        """
        Parse a CBECC CSV file into sections.

        Args:
            filepath: Path to the CSV file

        Returns:
            Dictionary of section name -> CebeccSection
        """
        filepath = Path(filepath)
        if not filepath.exists():
            raise FileNotFoundError(f"File not found: {filepath}")

        # Reset state
        self.sections = {}
        self.parse_errors = []
        self.parse_warnings = []

        # Read all lines
        lines = self._read_csv_lines(filepath)

        # Detect section boundaries
        section_boundaries = self._detect_sections(lines)

        # Parse each section
        for section_name, start_line, end_line in section_boundaries:
            try:
                section = self._parse_section(lines, section_name, start_line, end_line)
                if section:
                    self.sections[section_name] = section
            except Exception as e:
                self.parse_errors.append(f"Error parsing section '{section_name}': {e}")
                logger.warning(f"Error parsing section '{section_name}' in {filepath}: {e}")

        return self.sections

    def _read_csv_lines(self, filepath: Path) -> List[List[str]]:
        """Read CSV file and return list of rows (each row is a list of cells)."""
        lines = []
        with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
            reader = csv.reader(f)
            for row in reader:
                lines.append(row)
        return lines

    def _detect_sections(self, lines: List[List[str]]) -> List[Tuple[str, int, int]]:
        """
        Detect section boundaries in the CSV.

        Returns:
            List of (section_name, start_line_index, end_line_index)
        """
        sections = []
        current_section_name = None
        current_section_start = None

        for i, row in enumerate(lines):
            if self._is_section_header(row):
                # Save previous section if exists
                if current_section_name is not None:
                    sections.append((current_section_name, current_section_start, i - 1))

                # Start new section
                current_section_name = self._clean_string(row[0])
                current_section_start = i

        # Don't forget the last section
        if current_section_name is not None:
            sections.append((current_section_name, current_section_start, len(lines) - 1))

        return sections

    def _is_section_header(self, row: List[str]) -> bool:
        """
        Determine if a row is a section header.

        Section headers typically have:
        - Single non-empty cell in first column
        - Remaining cells are empty
        - Text is a known section name or follows naming pattern
        """
        if not row or not row[0]:
            return False

        # First cell must have content
        first_cell = self._clean_string(row[0])
        if not first_cell:
            return False

        # Check if remaining cells are mostly empty
        non_empty_count = sum(1 for cell in row[1:] if self._clean_string(cell))

        # Section header: first cell non-empty, most others empty
        # Allow some non-empty cells for subheader rows that might be misdetected
        if non_empty_count <= 1:
            # Verify it looks like a section name (not a data value)
            if not self._looks_like_data_value(first_cell):
                return True

        return False

    def _looks_like_data_value(self, value: str) -> bool:
        """Check if a value looks like data rather than a section name."""
        # Numbers are data
        try:
            float(value.replace(',', ''))
            return True
        except ValueError:
            pass

        # Quoted strings with specific patterns are data
        if value.startswith('"') and value.endswith('"'):
            return True

        # Values containing specific data patterns
        data_patterns = [
            r'^\d+\.?\d*$',  # Plain numbers
            r'^-?\d+\.?\d*$',  # Negative numbers
            r'^\(.+\)$',  # Parenthetical (units)
        ]
        for pattern in data_patterns:
            if re.match(pattern, value):
                return True

        return False

    def _parse_section(self, lines: List[List[str]], section_name: str,
                       start_line: int, end_line: int) -> Optional[CebeccSection]:
        """
        Parse a single section from the CSV.

        Args:
            lines: All CSV lines
            section_name: Name of the section
            start_line: Starting line index
            end_line: Ending line index

        Returns:
            Parsed CebeccSection or None if parsing fails
        """
        section = CebeccSection(name=section_name)

        # Find header structure (subheader, columns, units)
        header_end, subheader, columns, units = self._parse_header_structure(
            lines, start_line, end_line
        )

        section.subheader = subheader
        section.columns = columns
        section.units = units

        # Parse data rows
        for i in range(header_end + 1, end_line + 1):
            if i >= len(lines):
                break

            row = lines[i]

            # Skip blank rows
            if self._is_blank_row(row):
                continue

            # Parse data row
            row_data = self._parse_data_row(row, columns)
            if row_data:
                section.data.append(row_data)

        return section

    def _parse_header_structure(self, lines: List[List[str]],
                                 start_line: int, end_line: int
                                 ) -> Tuple[int, List[str], List[str], List[str]]:
        """
        Parse the header structure of a section.

        Returns:
            (header_end_line, subheader, columns, units)
        """
        subheader = []
        columns = []
        units = []
        header_end = start_line

        # Start after section name
        for i in range(start_line + 1, min(start_line + 5, end_line + 1)):
            if i >= len(lines):
                break

            row = lines[i]

            if self._is_blank_row(row):
                continue

            row_type = self._classify_header_row(row)

            if row_type == 'subheader':
                subheader = [self._clean_string(cell) for cell in row]
                header_end = i
            elif row_type == 'columns':
                columns = [self._clean_string(cell) for cell in row]
                header_end = i
            elif row_type == 'units':
                units = [self._clean_string(cell) for cell in row]
                header_end = i
            elif row_type == 'data':
                # Hit data, stop parsing header
                break

        return header_end, subheader, columns, units

    def _classify_header_row(self, row: List[str]) -> str:
        """
        Classify a row as subheader, columns, units, or data.

        Returns:
            'subheader', 'columns', 'units', or 'data'
        """
        non_empty_cells = [self._clean_string(cell) for cell in row if self._clean_string(cell)]

        if not non_empty_cells:
            return 'blank'

        # Units row: most cells contain parenthesized text or are blank
        paren_count = sum(1 for cell in non_empty_cells if cell.startswith('(') or cell.endswith(')'))
        if paren_count > len(non_empty_cells) * 0.4:
            return 'units'

        # Check if this looks like a subheader (category groupings with many blanks)
        if len(non_empty_cells) < len(row) * 0.3:
            # Sparse row - likely subheader
            return 'subheader'

        # Check if this looks like column headers (text, no numbers, no quotes)
        numeric_count = 0
        quoted_count = 0
        for cell in non_empty_cells:
            if self._is_numeric(cell):
                numeric_count += 1
            if cell.startswith('"'):
                quoted_count += 1

        if numeric_count == 0 and quoted_count == 0:
            return 'columns'

        # Default to data if we see numbers or quoted values
        if numeric_count > 0 or quoted_count > 0:
            return 'data'

        return 'columns'

    def _parse_data_row(self, row: List[str], columns: List[str]) -> Optional[Dict[str, Any]]:
        """
        Parse a data row into a dictionary.

        Args:
            row: CSV row cells
            columns: Column names from header

        Returns:
            Dictionary of column_name -> value
        """
        if not columns:
            # No column headers, use indices
            columns = [f"col_{i}" for i in range(len(row))]

        data = {}
        for i, cell in enumerate(row):
            if i < len(columns):
                col_name = columns[i] if columns[i] else f"col_{i}"
            else:
                col_name = f"col_{i}"

            value = self._clean_value(cell)
            data[col_name] = value

        return data if data else None

    def _clean_value(self, value: Any) -> Any:
        """
        Clean a cell value and handle missing value indicator.

        Args:
            value: Raw cell value

        Returns:
            Cleaned value (number, string, or None for missing)
        """
        if value is None:
            return None

        # Clean string
        cleaned = self._clean_string(str(value))

        if not cleaned:
            return None

        # Try to parse as number
        numeric = self._safe_float(cleaned)
        if numeric is not None:
            # Check for missing value indicator
            if numeric == self.MISSING_VALUE:
                return None
            return numeric

        # Return as string
        return cleaned

    def _clean_string(self, value: str) -> str:
        """Strip whitespace and quotes from a string."""
        if not value:
            return ""

        # Strip whitespace
        cleaned = value.strip()

        # Strip surrounding quotes
        if len(cleaned) >= 2:
            if (cleaned.startswith('"') and cleaned.endswith('"')) or \
               (cleaned.startswith("'") and cleaned.endswith("'")):
                cleaned = cleaned[1:-1]

        return cleaned.strip()

    def _safe_float(self, value: str) -> Optional[float]:
        """Safely convert a string to float."""
        if not value:
            return None

        try:
            # Handle comma-separated numbers
            cleaned = value.replace(',', '')
            return float(cleaned)
        except (ValueError, TypeError):
            return None

    def _safe_int(self, value: str) -> Optional[int]:
        """Safely convert a string to int."""
        float_val = self._safe_float(value)
        if float_val is not None:
            return int(float_val)
        return None

    def _is_blank_row(self, row: List[str]) -> bool:
        """Check if a row is blank (all cells empty or whitespace)."""
        return all(not self._clean_string(cell) for cell in row)

    def _is_numeric(self, value: str) -> bool:
        """Check if a string is numeric."""
        return self._safe_float(value) is not None

    def get_section(self, name: str) -> Optional[CebeccSection]:
        """Get a section by name (case-insensitive)."""
        name_lower = name.lower()
        for section_name, section in self.sections.items():
            if section_name.lower() == name_lower:
                return section
        return None

    def get_section_data(self, name: str) -> List[Dict[str, Any]]:
        """Get data rows for a section by name."""
        section = self.get_section(name)
        return section.data if section else []


def parse_cbecc_csv(filepath: Path) -> Dict[str, CebeccSection]:
    """
    Parse a CBECC multi-section CSV file.

    Args:
        filepath: Path to the CSV file

    Returns:
        Dictionary of section name -> CebeccSection
    """
    parser = CebeccCsvParser()
    return parser.parse_file(filepath)
