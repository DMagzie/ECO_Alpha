"""
CSE Runner
==========

Execute CSE (California Simulation Engine) with transformed input files.

This module:
- Locates the CSE executable (macOS and Windows)
- Executes CSE with specified input files
- Captures stdout/stderr output
- Collects output files (CSV, reports)
- Handles timeouts and errors

CSE is embedded in CBECC but can be run standalone for
zone-level meter simulation.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import os
import platform
import subprocess
import tempfile
import shutil
import logging
import time

logger = logging.getLogger(__name__)


# =============================================================================
# CONSTANTS
# =============================================================================

# Default CSE executable locations
# Note: CSE is typically embedded within CBECC on macOS
# On Windows, CSE.exe may be standalone
CSE_PATHS_MACOS = [
    "/Applications/CBECC 2025.2.0.app/Contents/MacOS/CSE",
    "/Applications/CBECC 2025.app/Contents/MacOS/CSE",
    "/Applications/CBECC 2022.app/Contents/MacOS/CSE",
    # Check for standalone CSE
    "/usr/local/bin/CSE",
    "/opt/CSE/CSE",
]

CSE_PATHS_WINDOWS = [
    r"C:\Program Files\CBECC 2025\CSE.exe",
    r"C:\Program Files\CBECC 2022\CSE.exe",
    r"C:\Program Files (x86)\CBECC 2025\CSE.exe",
    r"C:\Program Files (x86)\CBECC 2022\CSE.exe",
    # CSE standalone
    r"C:\CSE\CSE.exe",
]

# CBECC executable paths (for running via CBECC when CSE not available)
CBECC_PATHS_MACOS = [
    "/Applications/CBECC 2025.app/Contents/MacOS/CBECC 2025",
    "/Applications/CBECC 2022.app/Contents/MacOS/CBECC 2022",
]

CBECC_PATHS_WINDOWS = [
    r"C:\Program Files\CBECC 2025\CBECC.exe",
    r"C:\Program Files\CBECC 2022\CBECC.exe",
]

# Default timeout in seconds
DEFAULT_TIMEOUT = 600  # 10 minutes

# Output file patterns to collect
OUTPUT_PATTERNS = [
    "*-CSE.CSV",         # Main meter output
    "*-HourlyResults.csv",
    "*-rep.txt",         # Text report
    "*-err.txt",         # Error log
    "*.err",             # CSE error file
]


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class CSERunConfig:
    """Configuration for CSE execution."""
    input_file: Path
    output_dir: Optional[Path] = None
    cse_path: Optional[Path] = None
    weather_file: Optional[Path] = None
    timeout_seconds: int = DEFAULT_TIMEOUT
    verbose: bool = False

    # CSE command line options
    auto_run: bool = True      # Run simulation automatically
    report_file: bool = True   # Generate report file
    err_file: bool = True      # Generate error file

    def __post_init__(self):
        """Validate and resolve paths."""
        self.input_file = Path(self.input_file)
        if not self.input_file.exists():
            raise FileNotFoundError(f"Input file not found: {self.input_file}")

        if self.output_dir:
            self.output_dir = Path(self.output_dir)
        else:
            # Use same directory as input file
            self.output_dir = self.input_file.parent

        if self.cse_path:
            self.cse_path = Path(self.cse_path)


@dataclass
class CSERunResult:
    """Result of CSE execution."""
    success: bool
    return_code: int
    stdout: str
    stderr: str

    # Timing
    execution_time_seconds: float

    # Output files
    output_files: List[Path] = field(default_factory=list)
    csv_output: Optional[Path] = None  # Main meter CSV

    # Error info
    error_message: str = ""
    warnings: List[str] = field(default_factory=list)

    @property
    def has_errors(self) -> bool:
        """Check if there were any errors."""
        return not self.success or bool(self.error_message)

    @property
    def has_csv_output(self) -> bool:
        """Check if CSV output was generated."""
        return self.csv_output is not None and self.csv_output.exists()


# =============================================================================
# CSE RUNNER
# =============================================================================

class CSERunner:
    """
    Execute CSE simulation engine.

    Example usage:
        >>> runner = CSERunner()
        >>> config = CSERunConfig(input_file=Path("model.cse"))
        >>> result = runner.run(config)
        >>> if result.success:
        ...     print(f"Output: {result.csv_output}")
    """

    def __init__(self, cse_path: Optional[Path] = None):
        """
        Initialize the runner.

        Args:
            cse_path: Optional explicit path to CSE executable
        """
        self._cse_path = cse_path
        if self._cse_path is None:
            self._cse_path = self._find_cse_executable()

    def _find_cse_executable(self) -> Optional[Path]:
        """
        Find the CSE executable on the system.

        Returns:
            Path to CSE executable, or None if not found
        """
        system = platform.system()

        if system == "Darwin":  # macOS
            paths = CSE_PATHS_MACOS
        elif system == "Windows":
            paths = CSE_PATHS_WINDOWS
        else:
            logger.warning(f"Unsupported platform: {system}")
            return None

        for path_str in paths:
            path = Path(path_str)
            if path.exists():
                logger.info(f"Found CSE at: {path}")
                return path

        # Check if CSE is in PATH
        cse_in_path = shutil.which("CSE") or shutil.which("cse")
        if cse_in_path:
            logger.info(f"Found CSE in PATH: {cse_in_path}")
            return Path(cse_in_path)

        logger.warning("CSE executable not found")
        return None

    @property
    def cse_available(self) -> bool:
        """Check if CSE executable is available."""
        return self._cse_path is not None and self._cse_path.exists()

    @property
    def cse_path(self) -> Optional[Path]:
        """Get the CSE executable path."""
        return self._cse_path

    def run(self, config: CSERunConfig) -> CSERunResult:
        """
        Run CSE simulation.

        Args:
            config: CSERunConfig with input file and options

        Returns:
            CSERunResult with execution status and outputs
        """
        start_time = time.time()

        # Use configured path or find default
        cse_path = config.cse_path or self._cse_path
        if cse_path is None or not cse_path.exists():
            return CSERunResult(
                success=False,
                return_code=-1,
                stdout="",
                stderr="",
                execution_time_seconds=0.0,
                error_message="CSE executable not found",
            )

        # Build command line
        cmd = self._build_command(cse_path, config)

        # Run CSE
        try:
            logger.info(f"Running CSE: {' '.join(cmd)}")

            process = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=config.timeout_seconds,
                cwd=str(config.output_dir),
            )

            execution_time = time.time() - start_time

            result = CSERunResult(
                success=process.returncode == 0,
                return_code=process.returncode,
                stdout=process.stdout,
                stderr=process.stderr,
                execution_time_seconds=execution_time,
            )

            # Collect output files
            self._collect_output_files(config, result)

            # Parse any errors from output
            self._parse_errors(result)

            logger.info(
                f"CSE completed in {execution_time:.1f}s "
                f"(return code: {process.returncode})"
            )

        except subprocess.TimeoutExpired:
            execution_time = time.time() - start_time
            result = CSERunResult(
                success=False,
                return_code=-1,
                stdout="",
                stderr="",
                execution_time_seconds=execution_time,
                error_message=f"CSE execution timed out after {config.timeout_seconds}s",
            )
            logger.error(f"CSE timed out after {config.timeout_seconds}s")

        except Exception as e:
            execution_time = time.time() - start_time
            result = CSERunResult(
                success=False,
                return_code=-1,
                stdout="",
                stderr="",
                execution_time_seconds=execution_time,
                error_message=f"Error running CSE: {e}",
            )
            logger.error(f"Error running CSE: {e}")

        return result

    def _build_command(
        self,
        cse_path: Path,
        config: CSERunConfig,
    ) -> List[str]:
        """Build the CSE command line."""
        cmd = [str(cse_path)]

        # Input file
        cmd.append(str(config.input_file))

        # Weather file
        if config.weather_file:
            cmd.extend(["-w", str(config.weather_file)])

        # Report file
        if config.report_file:
            report_name = config.input_file.stem + "-rep.txt"
            cmd.extend(["-r", report_name])

        # Error file
        if config.err_file:
            err_name = config.input_file.stem + "-err.txt"
            cmd.extend(["-e", err_name])

        return cmd

    def _collect_output_files(
        self,
        config: CSERunConfig,
        result: CSERunResult,
    ) -> None:
        """Collect output files generated by CSE."""
        output_dir = config.output_dir

        for pattern in OUTPUT_PATTERNS:
            for file_path in output_dir.glob(pattern):
                if file_path.exists():
                    result.output_files.append(file_path)

                    # Identify main CSV output
                    if file_path.name.endswith("-CSE.CSV"):
                        result.csv_output = file_path

        # Also check for output in input file's directory
        input_dir = config.input_file.parent
        if input_dir != output_dir:
            for pattern in OUTPUT_PATTERNS:
                for file_path in input_dir.glob(pattern):
                    if file_path.exists() and file_path not in result.output_files:
                        result.output_files.append(file_path)

                        if file_path.name.endswith("-CSE.CSV"):
                            result.csv_output = file_path

    def _parse_errors(self, result: CSERunResult) -> None:
        """Parse errors from CSE output."""
        # Check stdout for errors
        if "error" in result.stdout.lower() or "fatal" in result.stdout.lower():
            # Extract error lines
            for line in result.stdout.split('\n'):
                if 'error' in line.lower() or 'fatal' in line.lower():
                    if not result.error_message:
                        result.error_message = line.strip()
                    result.warnings.append(line.strip())

        # Check stderr
        if result.stderr:
            if not result.error_message:
                result.error_message = result.stderr.strip()[:200]

        # Check for error files
        for output_file in result.output_files:
            if output_file.suffix == '.err' or 'err' in output_file.stem.lower():
                try:
                    err_content = output_file.read_text()
                    if err_content.strip():
                        result.warnings.append(f"Error file {output_file.name}: {err_content[:500]}")
                except Exception:
                    pass


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def find_cse_executable() -> Optional[Path]:
    """
    Find CSE executable on the system.

    Returns:
        Path to CSE executable, or None if not found
    """
    runner = CSERunner()
    return runner.cse_path


def run_cse(
    input_file: Path,
    output_dir: Optional[Path] = None,
    timeout_seconds: int = DEFAULT_TIMEOUT,
) -> CSERunResult:
    """
    Run CSE simulation with default settings.

    Args:
        input_file: Path to CSE input file
        output_dir: Optional output directory
        timeout_seconds: Execution timeout

    Returns:
        CSERunResult with execution status
    """
    runner = CSERunner()
    config = CSERunConfig(
        input_file=input_file,
        output_dir=output_dir,
        timeout_seconds=timeout_seconds,
    )
    return runner.run(config)


def check_cse_available() -> Tuple[bool, Optional[str]]:
    """
    Check if CSE is available.

    Returns:
        Tuple of (available, path_string)
    """
    runner = CSERunner()
    if runner.cse_available:
        return True, str(runner.cse_path)
    return False, None


def format_run_result(result: CSERunResult) -> str:
    """
    Format CSE run result as text.

    Args:
        result: CSERunResult from execution

    Returns:
        Formatted text summary
    """
    lines = [
        "=" * 70,
        "CSE EXECUTION RESULT",
        "=" * 70,
        "",
        f"Success: {result.success}",
        f"Return Code: {result.return_code}",
        f"Execution Time: {result.execution_time_seconds:.1f} seconds",
    ]

    if result.csv_output:
        lines.append(f"CSV Output: {result.csv_output}")

    if result.output_files:
        lines.extend([
            "",
            "Output Files:",
        ])
        for f in result.output_files:
            lines.append(f"  - {f.name}")

    if result.error_message:
        lines.extend([
            "",
            f"Error: {result.error_message}",
        ])

    if result.warnings:
        lines.extend([
            "",
            "Warnings:",
        ])
        for w in result.warnings:
            lines.append(f"  - {w[:100]}")

    if result.stdout and len(result.stdout) < 500:
        lines.extend([
            "",
            "Output:",
            result.stdout,
        ])

    lines.append("=" * 70)

    return "\n".join(lines)
