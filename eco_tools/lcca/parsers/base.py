"""
Abstract Simulation Parser Base Class.

Defines the interface for simulation output parsers that convert
engine-specific output formats to the unified WholeBuildingEnergy schema.

This abstraction enables:
- CBECC parser (current)
- EnergyPlus parser (future, planned for 2026)
- Other simulation engines as needed

Each parser must implement methods to:
1. Parse simulation output to EnergyStream format
2. Extract project metadata
3. Validate simulation results
"""

from __future__ import annotations
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional, List, TYPE_CHECKING

if TYPE_CHECKING:
    from ..whole_building.schema import EnergyStream, ProjectInfo
    from ..model import SimulationOutput


class SimulationParser(ABC):
    """
    Abstract base class for simulation output parsers.

    Subclasses implement engine-specific parsing logic while
    producing unified EnergyStream and ProjectInfo outputs
    that work with the whole-building energy aggregation system.
    """

    @property
    @abstractmethod
    def engine_name(self) -> str:
        """Return the simulation engine name (e.g., 'CBECC', 'EnergyPlus')."""
        pass

    @abstractmethod
    def parse_to_stream(self, file_path: str | Path) -> "EnergyStream":
        """
        Parse simulation output to unified EnergyStream format.

        Args:
            file_path: Path to simulation output file(s)

        Returns:
            EnergyStream with 8760 hourly records

        Raises:
            FileNotFoundError: If simulation output not found
            ValueError: If output format is invalid
        """
        pass

    @abstractmethod
    def get_project_info(self, file_path: str | Path) -> "ProjectInfo":
        """
        Extract project metadata from simulation output.

        Args:
            file_path: Path to simulation output file(s)

        Returns:
            ProjectInfo with project name, building type, floor area, etc.
        """
        pass

    def parse(self, file_path: str | Path) -> tuple["EnergyStream", "ProjectInfo"]:
        """
        Convenience method to parse both stream and project info.

        Args:
            file_path: Path to simulation output file(s)

        Returns:
            Tuple of (EnergyStream, ProjectInfo)
        """
        stream = self.parse_to_stream(file_path)
        info = self.get_project_info(file_path)
        return stream, info

    def validate_output(self, file_path: str | Path) -> tuple[bool, List[str]]:
        """
        Validate simulation output file(s).

        Args:
            file_path: Path to simulation output file(s)

        Returns:
            Tuple of (is_valid, list of error messages)
        """
        errors = []
        file_path = Path(file_path)

        if not file_path.exists():
            errors.append(f"File not found: {file_path}")
            return False, errors

        return True, errors


class CbeccSimulationParser(SimulationParser):
    """
    Parser for CBECC simulation output.

    Wraps the existing HourlyResultsParser to provide the
    unified SimulationParser interface. Supports:
    - Single-use buildings (residential or nonresidential)
    - Mixed-use buildings
    - Both proposed and baseline models
    """

    @property
    def engine_name(self) -> str:
        return "CBECC"

    def parse_to_stream(self, file_path: str | Path) -> "EnergyStream":
        """
        Parse CBECC HourlyResults.csv to EnergyStream.

        Args:
            file_path: Path to HourlyResults.csv file

        Returns:
            EnergyStream with 8760 hourly records
        """
        from ..whole_building.schema import EnergyStream
        from .hourly_results import parse_hourly_results

        # Use existing parser
        output = parse_hourly_results(file_path)

        # Convert to EnergyStream
        return EnergyStream.from_simulation_output(output)

    def get_project_info(self, file_path: str | Path) -> "ProjectInfo":
        """
        Extract project info from CBECC HourlyResults.csv.

        Args:
            file_path: Path to HourlyResults.csv file

        Returns:
            ProjectInfo with CBECC-specific metadata
        """
        from ..whole_building.schema import ProjectInfo
        from .hourly_results import parse_hourly_results

        output = parse_hourly_results(file_path)

        return ProjectInfo.from_simulation_output(output)

    def parse_simulation_output(self, file_path: str | Path) -> "SimulationOutput":
        """
        Parse to the existing SimulationOutput format for backwards compatibility.

        This allows existing LCCA code to work unchanged while
        new code can use the EnergyStream format.
        """
        from .hourly_results import parse_hourly_results
        return parse_hourly_results(file_path)

    def validate_output(self, file_path: str | Path) -> tuple[bool, List[str]]:
        """Validate CBECC HourlyResults.csv file."""
        errors = []
        file_path = Path(file_path)

        # Base validation
        is_valid, base_errors = super().validate_output(file_path)
        errors.extend(base_errors)

        if not is_valid:
            return False, errors

        # CBECC-specific validation
        if not file_path.name.endswith('HourlyResults.csv'):
            errors.append(f"Expected HourlyResults.csv, got: {file_path.name}")

        # Try to parse and check for data
        try:
            from .hourly_results import parse_hourly_results
            output = parse_hourly_results(file_path)

            if len(output.hourly) != 8760:
                errors.append(f"Expected 8760 hourly records, got: {len(output.hourly)}")

            if output.annual.total_elec_kwh == 0 and output.annual.total_gas_therm == 0:
                errors.append("No energy consumption found in output")

        except Exception as e:
            errors.append(f"Parse error: {str(e)}")

        return len(errors) == 0, errors


class EnergyPlusParser(SimulationParser):
    """
    Parser for EnergyPlus simulation output.

    PLACEHOLDER for future implementation (2026).

    EnergyPlus outputs include:
    - eplusout.sql: SQLite database with all results
    - eplusout.csv: Tabular output
    - Zone and meter data

    This parser will map E+ output to the unified EnergyStream
    format, enabling whole-building analysis with ASHRAE 90.1 models.
    """

    @property
    def engine_name(self) -> str:
        return "EnergyPlus"

    def parse_to_stream(self, file_path: str | Path) -> "EnergyStream":
        """Parse EnergyPlus output to EnergyStream."""
        raise NotImplementedError(
            "EnergyPlus parser is planned for 2026. "
            "This will support ASHRAE 90.1 2019 and later models."
        )

    def get_project_info(self, file_path: str | Path) -> "ProjectInfo":
        """Extract project info from EnergyPlus output."""
        raise NotImplementedError(
            "EnergyPlus parser is planned for 2026."
        )


def get_parser_for_file(file_path: str | Path) -> SimulationParser:
    """
    Factory function to get appropriate parser for a file.

    Args:
        file_path: Path to simulation output file

    Returns:
        SimulationParser instance appropriate for the file type

    Raises:
        ValueError: If file type is not supported
    """
    file_path = Path(file_path)
    name = file_path.name.lower()

    if 'hourlyresults.csv' in name or name.endswith('.cibd22') or name.endswith('.cibd25'):
        return CbeccSimulationParser()

    elif name.endswith('.sql') or name.endswith('.eso'):
        return EnergyPlusParser()

    else:
        raise ValueError(
            f"Unknown simulation output format: {file_path.name}. "
            f"Supported: HourlyResults.csv (CBECC)"
        )
