"""
Auto-discovery of CBECC simulation outputs.

This module provides utilities to automatically find and identify
CBECC simulation output files in project directories.

Supported file types:
- HourlyResults CSV (combined hourly energy data)
- CSE CSV (detailed end-use hourly data)
- PVBattery CSV (PV and battery allocation data)
- NRCCPRF XML (compliance report data)
- CUAC CSV (utility allowance calculations)

Usage:
    from eco_tools.lcca.auto_discovery import discover_simulation_outputs

    outputs = discover_simulation_outputs("/path/to/project")
    if outputs.is_complete:
        print(f"Found complete simulation for: {outputs.project_name}")
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, List, Dict, Any
from enum import Enum
import re
import logging

logger = logging.getLogger(__name__)


class SimulationFileType(Enum):
    """Types of CBECC simulation output files."""
    HOURLY_RESULTS = "hourly_results"
    CSE_HOURLY = "cse_hourly"
    PV_BATTERY = "pv_battery"
    NRCCPRF = "nrccprf"
    CUAC = "cuac"
    CIBD_MODEL = "cibd_model"


@dataclass
class SimulationFile:
    """Represents a discovered simulation output file."""
    path: Path
    file_type: SimulationFileType
    scenario: str  # "proposed" (ap) or "standard" (ab)
    project_name: str

    @property
    def exists(self) -> bool:
        """Check if file still exists."""
        return self.path.exists()

    @property
    def size_kb(self) -> float:
        """File size in kilobytes."""
        if self.exists:
            return self.path.stat().st_size / 1024
        return 0.0


@dataclass
class DiscoveredOutputs:
    """Collection of discovered simulation outputs for a project."""
    project_name: str
    project_dir: Path

    # Required files
    hourly_results_proposed: Optional[SimulationFile] = None
    hourly_results_standard: Optional[SimulationFile] = None

    # Optional but valuable files
    cse_proposed: Optional[SimulationFile] = None
    cse_standard: Optional[SimulationFile] = None
    pv_battery: Optional[SimulationFile] = None
    nrccprf: Optional[SimulationFile] = None
    cuac: Optional[SimulationFile] = None
    cibd_model: Optional[SimulationFile] = None

    # All discovered files
    all_files: List[SimulationFile] = field(default_factory=list)

    # Discovery metadata
    run_folder: Optional[Path] = None
    discovery_errors: List[str] = field(default_factory=list)

    @property
    def is_complete(self) -> bool:
        """Check if minimum required files are present."""
        return self.hourly_results_proposed is not None

    @property
    def has_comparison(self) -> bool:
        """Check if both proposed and standard are available."""
        return (self.hourly_results_proposed is not None and
                self.hourly_results_standard is not None)

    @property
    def has_tou_data(self) -> bool:
        """Check if hourly data is available for TOU calculations."""
        return self.cse_proposed is not None or self.hourly_results_proposed is not None

    @property
    def has_pv_battery(self) -> bool:
        """Check if PV/Battery allocation data is available."""
        return self.pv_battery is not None

    @property
    def has_cuac(self) -> bool:
        """Check if CUAC utility allowance data is available."""
        return self.cuac is not None

    @property
    def has_compliance_data(self) -> bool:
        """Check if NRCCPRF compliance data is available."""
        return self.nrccprf is not None

    def summary(self) -> Dict[str, Any]:
        """Get summary of discovered outputs."""
        return {
            "project_name": self.project_name,
            "project_dir": str(self.project_dir),
            "is_complete": self.is_complete,
            "has_comparison": self.has_comparison,
            "has_tou_data": self.has_tou_data,
            "has_pv_battery": self.has_pv_battery,
            "has_cuac": self.has_cuac,
            "has_compliance_data": self.has_compliance_data,
            "file_count": len(self.all_files),
            "errors": self.discovery_errors,
        }


# File pattern matchers
FILE_PATTERNS = {
    SimulationFileType.HOURLY_RESULTS: [
        # Pattern: ProjectName - ap - HourlyResults.csv (proposed)
        # Pattern: ProjectName - ab - HourlyResults.csv (standard)
        re.compile(r"(.+?)\s*-\s*(ap|ab)\s*-\s*HourlyResults\.csv$", re.IGNORECASE),
    ],
    SimulationFileType.CSE_HOURLY: [
        # Pattern: ProjectName - CSE.CSV
        re.compile(r"(.+?)\s*-\s*CSE\.CSV$", re.IGNORECASE),
        # Pattern with ap/ab prefix
        re.compile(r"(.+?)\s*-\s*(ap|ab)\s*-\s*CSE\.CSV$", re.IGNORECASE),
    ],
    SimulationFileType.PV_BATTERY: [
        # Pattern: ProjectName - PVBattery.csv
        re.compile(r"(.+?)\s*-\s*PVBattery\.csv$", re.IGNORECASE),
        # Pattern with ap/ab prefix
        re.compile(r"(.+?)\s*-\s*(ap|ab)\s*-\s*PVBattery\.csv$", re.IGNORECASE),
    ],
    SimulationFileType.NRCCPRF: [
        # Pattern: ProjectName - NRCCPRF.xml
        re.compile(r"(.+?)\s*-\s*NRCCPRF\.xml$", re.IGNORECASE),
    ],
    SimulationFileType.CUAC: [
        # Pattern: ProjectName_CUAC.csv or ProjectName - CUAC.csv
        re.compile(r"(.+?)[-_]\s*CUAC\.csv$", re.IGNORECASE),
    ],
    SimulationFileType.CIBD_MODEL: [
        # Pattern: ProjectName.cibd22 or ProjectName.cibd25
        re.compile(r"(.+?)\.cibd(22|25|22x)$", re.IGNORECASE),
    ],
}


def _match_file(filename: str) -> Optional[tuple]:
    """
    Match a filename against known patterns.

    Returns:
        Tuple of (file_type, project_name, scenario) or None
    """
    for file_type, patterns in FILE_PATTERNS.items():
        for pattern in patterns:
            match = pattern.match(filename)
            if match:
                groups = match.groups()
                project_name = groups[0].strip()

                # Determine scenario from match groups
                scenario = "proposed"  # default
                if len(groups) > 1 and groups[1] in ("ap", "ab"):
                    scenario = "proposed" if groups[1] == "ap" else "standard"

                return (file_type, project_name, scenario)

    return None


def discover_simulation_outputs(
    project_dir: str | Path,
    recursive: bool = True,
    include_run_folders: bool = True,
) -> DiscoveredOutputs:
    """
    Discover CBECC simulation outputs in a project directory.

    Args:
        project_dir: Path to project directory
        recursive: Search subdirectories
        include_run_folders: Look for "run" subfolders (CBECC convention)

    Returns:
        DiscoveredOutputs with all found simulation files
    """
    project_path = Path(project_dir)

    if not project_path.exists():
        raise FileNotFoundError(f"Project directory not found: {project_dir}")

    if not project_path.is_dir():
        raise ValueError(f"Path is not a directory: {project_dir}")

    # Initialize outputs
    outputs = DiscoveredOutputs(
        project_name=project_path.name,
        project_dir=project_path,
    )

    # Find all potential files
    search_dirs = [project_path]

    # Look for run folders (CBECC creates "run" subfolder with outputs)
    if include_run_folders:
        run_folders = list(project_path.glob("**/run"))
        for run_folder in run_folders:
            if run_folder.is_dir():
                search_dirs.append(run_folder)
                if outputs.run_folder is None:
                    outputs.run_folder = run_folder

    # Collect all candidate files
    candidate_files: List[Path] = []

    for search_dir in search_dirs:
        if recursive:
            candidate_files.extend(search_dir.rglob("*.csv"))
            candidate_files.extend(search_dir.rglob("*.CSV"))
            candidate_files.extend(search_dir.rglob("*.xml"))
            candidate_files.extend(search_dir.rglob("*.XML"))
            candidate_files.extend(search_dir.rglob("*.cibd*"))
        else:
            candidate_files.extend(search_dir.glob("*.csv"))
            candidate_files.extend(search_dir.glob("*.CSV"))
            candidate_files.extend(search_dir.glob("*.xml"))
            candidate_files.extend(search_dir.glob("*.XML"))
            candidate_files.extend(search_dir.glob("*.cibd*"))

    # Remove duplicates while preserving order
    seen = set()
    unique_files = []
    for f in candidate_files:
        if f not in seen:
            seen.add(f)
            unique_files.append(f)

    # Match files against patterns
    for file_path in unique_files:
        try:
            match_result = _match_file(file_path.name)
            if match_result:
                file_type, project_name, scenario = match_result

                sim_file = SimulationFile(
                    path=file_path,
                    file_type=file_type,
                    scenario=scenario,
                    project_name=project_name,
                )

                outputs.all_files.append(sim_file)

                # Update project name if not set
                if outputs.project_name == project_path.name:
                    outputs.project_name = project_name

                # Assign to specific slots
                _assign_file_to_slot(outputs, sim_file)

        except Exception as e:
            outputs.discovery_errors.append(f"Error processing {file_path.name}: {e}")
            logger.warning(f"Error processing file {file_path}: {e}")

    return outputs


def _assign_file_to_slot(outputs: DiscoveredOutputs, sim_file: SimulationFile) -> None:
    """Assign a simulation file to the appropriate slot in DiscoveredOutputs."""

    if sim_file.file_type == SimulationFileType.HOURLY_RESULTS:
        if sim_file.scenario == "proposed":
            if outputs.hourly_results_proposed is None:
                outputs.hourly_results_proposed = sim_file
        else:
            if outputs.hourly_results_standard is None:
                outputs.hourly_results_standard = sim_file

    elif sim_file.file_type == SimulationFileType.CSE_HOURLY:
        if sim_file.scenario == "proposed":
            if outputs.cse_proposed is None:
                outputs.cse_proposed = sim_file
        else:
            if outputs.cse_standard is None:
                outputs.cse_standard = sim_file

    elif sim_file.file_type == SimulationFileType.PV_BATTERY:
        if outputs.pv_battery is None:
            outputs.pv_battery = sim_file

    elif sim_file.file_type == SimulationFileType.NRCCPRF:
        if outputs.nrccprf is None:
            outputs.nrccprf = sim_file

    elif sim_file.file_type == SimulationFileType.CUAC:
        if outputs.cuac is None:
            outputs.cuac = sim_file

    elif sim_file.file_type == SimulationFileType.CIBD_MODEL:
        if outputs.cibd_model is None:
            outputs.cibd_model = sim_file


def discover_multiple_projects(
    base_dir: str | Path,
    max_depth: int = 2,
) -> List[DiscoveredOutputs]:
    """
    Discover simulation outputs for multiple projects in a base directory.

    Args:
        base_dir: Base directory containing project folders
        max_depth: Maximum directory depth to search

    Returns:
        List of DiscoveredOutputs for each project found
    """
    base_path = Path(base_dir)

    if not base_path.exists():
        raise FileNotFoundError(f"Base directory not found: {base_dir}")

    results: List[DiscoveredOutputs] = []

    # Try to discover at base level first
    base_outputs = discover_simulation_outputs(base_path, recursive=False)
    if base_outputs.is_complete:
        results.append(base_outputs)

    # Search subdirectories
    for subdir in base_path.iterdir():
        if subdir.is_dir() and not subdir.name.startswith('.'):
            try:
                outputs = discover_simulation_outputs(subdir, recursive=True)
                if outputs.is_complete:
                    results.append(outputs)
            except Exception as e:
                logger.warning(f"Error discovering in {subdir}: {e}")

    return results


def format_discovery_summary(outputs: DiscoveredOutputs) -> str:
    """
    Format a human-readable summary of discovered outputs.

    Args:
        outputs: DiscoveredOutputs to summarize

    Returns:
        Formatted string summary
    """
    lines = [
        f"Project: {outputs.project_name}",
        f"Directory: {outputs.project_dir}",
        "",
        "Discovered Files:",
        "-" * 40,
    ]

    # Required files
    if outputs.hourly_results_proposed:
        lines.append(f"  [✓] HourlyResults (proposed): {outputs.hourly_results_proposed.path.name}")
    else:
        lines.append("  [✗] HourlyResults (proposed): NOT FOUND")

    if outputs.hourly_results_standard:
        lines.append(f"  [✓] HourlyResults (standard): {outputs.hourly_results_standard.path.name}")
    else:
        lines.append("  [ ] HourlyResults (standard): not found")

    # Optional files
    if outputs.cse_proposed:
        lines.append(f"  [✓] CSE Hourly (proposed): {outputs.cse_proposed.path.name}")

    if outputs.pv_battery:
        lines.append(f"  [✓] PV/Battery: {outputs.pv_battery.path.name}")

    if outputs.cuac:
        lines.append(f"  [✓] CUAC: {outputs.cuac.path.name}")

    if outputs.nrccprf:
        lines.append(f"  [✓] NRCCPRF: {outputs.nrccprf.path.name}")

    if outputs.cibd_model:
        lines.append(f"  [✓] CIBD Model: {outputs.cibd_model.path.name}")

    lines.extend([
        "",
        "Status:",
        "-" * 40,
        f"  Complete: {'Yes' if outputs.is_complete else 'No'}",
        f"  Has Comparison: {'Yes' if outputs.has_comparison else 'No'}",
        f"  Has TOU Data: {'Yes' if outputs.has_tou_data else 'No'}",
        f"  Has PV/Battery: {'Yes' if outputs.has_pv_battery else 'No'}",
        f"  Has CUAC: {'Yes' if outputs.has_cuac else 'No'}",
    ])

    if outputs.discovery_errors:
        lines.extend([
            "",
            "Errors:",
            "-" * 40,
        ])
        for error in outputs.discovery_errors:
            lines.append(f"  - {error}")

    return "\n".join(lines)


# Convenience function for CLI
def discover_and_validate(
    project_dir: str | Path,
    require_comparison: bool = False,
    require_cuac: bool = False,
) -> DiscoveredOutputs:
    """
    Discover outputs and validate requirements.

    Args:
        project_dir: Path to project directory
        require_comparison: Require both proposed and standard
        require_cuac: Require CUAC data

    Returns:
        DiscoveredOutputs if validation passes

    Raises:
        ValueError: If validation fails
    """
    outputs = discover_simulation_outputs(project_dir)

    if not outputs.is_complete:
        raise ValueError(
            f"Incomplete simulation outputs for {outputs.project_name}. "
            f"Missing: HourlyResults (proposed)"
        )

    if require_comparison and not outputs.has_comparison:
        raise ValueError(
            f"Comparison requires both proposed and standard HourlyResults. "
            f"Missing: HourlyResults (standard)"
        )

    if require_cuac and not outputs.has_cuac:
        raise ValueError(
            f"CUAC analysis requires CUAC output file. "
            f"Missing: CUAC CSV"
        )

    return outputs
