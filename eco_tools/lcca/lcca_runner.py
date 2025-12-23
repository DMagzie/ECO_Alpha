"""
LCCA Workflow Runner.

This module provides a high-level workflow orchestrator for running
complete LCCA analyses from CBECC simulation outputs.

The runner handles:
- Auto-discovery of simulation outputs
- Parsing simulation data
- Tariff selection and rate calculations
- LCCA calculations (NPV, IRR, payback)
- Report generation (Excel, PDF, text)

Usage:
    from eco_tools.lcca.lcca_runner import LccaRunner

    runner = LccaRunner("/path/to/project")
    runner.configure(
        rate_id="PGE-E-ELEC",
        region="US-CA-SF",
        analysis_period=30,
    )
    results = runner.run()
    runner.export_excel("lcca_report.xlsx")
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, List, Dict, Any, Union
from enum import Enum
import logging
from datetime import datetime

from .auto_discovery import (
    discover_simulation_outputs,
    DiscoveredOutputs,
    format_discovery_summary,
)
from .model import (
    SimulationOutput,
    AnnualEnergySummary,
    LccaScenario,
    ScenarioAssumptions,
    EnergyStreams,
    Tariff,
)
from .parsers import parse_hourly_results
from .tariffs import (
    TouTariff,
    get_tariff_by_name,
    list_available_tariffs,
    calculate_tou_costs,
    hourly_energy_to_usage,
    get_default_tariff_for_region,
)
from .calculators import (
    LccaResults,
    run_lcca,
    run_tou_lcca,
    format_lcca_summary,
)
from .bridge import (
    simulation_to_scenario,
    create_baseline_scenario,
    create_proposed_scenario,
)
from .ca_hi_helpers import (
    get_region_from_climate_zone,
    get_regional_factor,
)
from .econ1 import generate_econ1, Econ1Report, export_econ1_text
from .excel_export import export_lcca_to_excel, ExcelExportOptions

logger = logging.getLogger(__name__)


class OutputFormat(Enum):
    """Supported output formats."""
    EXCEL = "excel"
    PDF = "pdf"
    TEXT = "text"
    JSON = "json"
    CSV = "csv"


class AnalysisMode(Enum):
    """LCCA analysis modes."""
    SIMPLE = "simple"  # Annual flat rates
    TOU = "tou"  # Time-of-use rates
    VNBT = "vnbt"  # Virtual net billing tariff


@dataclass
class RunnerConfig:
    """Configuration for LCCA runner."""
    # Rate selection
    rate_id: Optional[str] = None
    region: Optional[str] = None
    gas_rate: float = 1.50  # $/therm default

    # Analysis parameters
    analysis_period: int = 30
    discount_rate: float = 0.05
    electricity_escalation: float = 0.025
    gas_escalation: float = 0.02
    inflation_rate: float = 0.023

    # Capital costs
    capex: float = 0.0
    incentives: float = 0.0

    # Analysis mode
    mode: AnalysisMode = AnalysisMode.TOU

    # Output options
    output_dir: Optional[Path] = None
    output_formats: List[OutputFormat] = field(
        default_factory=lambda: [OutputFormat.EXCEL]
    )

    # Optional overrides
    custom_tariff: Optional[TouTariff] = None


@dataclass
class RunnerResults:
    """Results from LCCA runner."""
    # Core results
    lcca_results: Optional[LccaResults] = None
    econ1_report: Optional[Econ1Report] = None

    # Comparison results (if baseline available)
    baseline_lcca: Optional[LccaResults] = None
    savings_vs_baseline: Optional[float] = None

    # Metadata
    project_name: str = ""
    climate_zone: str = ""
    region: str = ""
    rate_id: str = ""
    analysis_date: str = field(
        default_factory=lambda: datetime.now().isoformat()
    )

    # Output files generated
    output_files: List[Path] = field(default_factory=list)

    # Any warnings or notes
    warnings: List[str] = field(default_factory=list)

    def summary(self) -> Dict[str, Any]:
        """Get summary of results."""
        result = {
            "project_name": self.project_name,
            "climate_zone": self.climate_zone,
            "region": self.region,
            "rate_id": self.rate_id,
            "analysis_date": self.analysis_date,
            "output_files": [str(f) for f in self.output_files],
            "warnings": self.warnings,
        }

        if self.lcca_results:
            result["npv"] = self.lcca_results.npv
            result["irr"] = self.lcca_results.irr
            result["simple_payback"] = self.lcca_results.simple_payback
            result["annual_savings"] = self.lcca_results.annual_savings

        if self.savings_vs_baseline is not None:
            result["savings_vs_baseline"] = self.savings_vs_baseline

        return result


class LccaRunner:
    """
    High-level LCCA workflow runner.

    Example:
        runner = LccaRunner("/path/to/project")
        runner.configure(rate_id="PGE-E-ELEC", region="US-CA-SF")
        results = runner.run()
        print(results.lcca_results.npv)
    """

    def __init__(
        self,
        project_dir: Union[str, Path],
        auto_discover: bool = True,
    ):
        """
        Initialize LCCA runner.

        Args:
            project_dir: Path to project directory with simulation outputs
            auto_discover: Automatically discover simulation files
        """
        self.project_dir = Path(project_dir)
        self.config = RunnerConfig()
        self.outputs: Optional[DiscoveredOutputs] = None
        self.simulation: Optional[SimulationOutput] = None
        self._tariff: Optional[TouTariff] = None

        if auto_discover:
            self.discover()

    def discover(self) -> DiscoveredOutputs:
        """
        Discover simulation outputs in project directory.

        Returns:
            DiscoveredOutputs with found files
        """
        self.outputs = discover_simulation_outputs(self.project_dir)
        logger.info(f"Discovered {len(self.outputs.all_files)} simulation files")

        if not self.outputs.is_complete:
            logger.warning(
                f"Incomplete simulation outputs for {self.outputs.project_name}"
            )

        return self.outputs

    def configure(
        self,
        rate_id: Optional[str] = None,
        region: Optional[str] = None,
        gas_rate: Optional[float] = None,
        analysis_period: Optional[int] = None,
        discount_rate: Optional[float] = None,
        capex: Optional[float] = None,
        incentives: Optional[float] = None,
        mode: Optional[AnalysisMode] = None,
        output_dir: Optional[Union[str, Path]] = None,
        output_formats: Optional[List[OutputFormat]] = None,
    ) -> "LccaRunner":
        """
        Configure runner parameters.

        Args:
            rate_id: Utility rate identifier (e.g., "PGE-E-ELEC")
            region: Regional cost factor code (e.g., "US-CA-SF")
            gas_rate: Natural gas rate ($/therm)
            analysis_period: LCCA period in years
            discount_rate: Discount rate for NPV
            capex: Capital expenditure ($)
            incentives: Incentive amount ($)
            mode: Analysis mode (SIMPLE, TOU, VNBT)
            output_dir: Directory for output files
            output_formats: List of output formats to generate

        Returns:
            Self for method chaining
        """
        if rate_id is not None:
            self.config.rate_id = rate_id
        if region is not None:
            self.config.region = region
        if gas_rate is not None:
            self.config.gas_rate = gas_rate
        if analysis_period is not None:
            self.config.analysis_period = analysis_period
        if discount_rate is not None:
            self.config.discount_rate = discount_rate
        if capex is not None:
            self.config.capex = capex
        if incentives is not None:
            self.config.incentives = incentives
        if mode is not None:
            self.config.mode = mode
        if output_dir is not None:
            self.config.output_dir = Path(output_dir)
        if output_formats is not None:
            self.config.output_formats = output_formats

        return self

    def parse_simulation(self) -> SimulationOutput:
        """
        Parse simulation outputs into structured data.

        Returns:
            SimulationOutput with parsed data
        """
        if self.outputs is None:
            self.discover()

        if not self.outputs.is_complete:
            raise ValueError(
                f"Cannot parse incomplete simulation outputs. "
                f"Missing required files."
            )

        # Parse HourlyResults
        proposed_path = self.outputs.hourly_results_proposed.path
        self.simulation = parse_hourly_results(str(proposed_path))

        # Parse standard if available
        if self.outputs.hourly_results_standard:
            standard_path = self.outputs.hourly_results_standard.path
            standard_sim = parse_hourly_results(str(standard_path))
            self.simulation.baseline = standard_sim  # Store entire standard simulation

        logger.info(f"Parsed simulation: {self.simulation.project_name}")

        return self.simulation

    def get_tariff(self) -> TouTariff:
        """
        Get the configured tariff.

        Returns:
            TouTariff for rate calculations
        """
        if self._tariff is not None:
            return self._tariff

        if self.config.custom_tariff is not None:
            self._tariff = self.config.custom_tariff
            return self._tariff

        # Determine region from climate zone if not specified
        region = self.config.region
        if region is None and self.simulation:
            climate_zone = self.simulation.climate_zone
            if climate_zone:
                region = get_region_from_climate_zone(climate_zone)
                self.config.region = region
                logger.info(f"Auto-detected region: {region} from CZ {climate_zone}")

        # Get tariff by rate_id or default for region
        if self.config.rate_id:
            self._tariff = get_tariff_by_name(self.config.rate_id)
        elif region:
            self._tariff = get_default_tariff_for_region(region)
        else:
            # Use PG&E E-ELEC as fallback
            self._tariff = get_tariff_by_name("PGE-E-ELEC")

        return self._tariff

    def run(self) -> RunnerResults:
        """
        Run complete LCCA analysis.

        Returns:
            RunnerResults with all analysis results
        """
        results = RunnerResults()

        # Ensure simulation is parsed
        if self.simulation is None:
            self.parse_simulation()

        results.project_name = self.simulation.project_name
        results.climate_zone = self.simulation.climate_zone
        results.region = self.config.region or ""
        results.rate_id = self.config.rate_id or ""

        # Get tariff
        tariff = self.get_tariff()

        # Create scenario
        assumptions = ScenarioAssumptions(
            analysis_years=self.config.analysis_period,
            discount_rate_real=self.config.discount_rate,
            elec_escalation=self.config.electricity_escalation,
            gas_escalation=self.config.gas_escalation,
            inflation_rate=self.config.inflation_rate,
        )

        # Run LCCA based on mode
        has_baseline = hasattr(self.simulation, 'baseline') and self.simulation.baseline

        if self.config.mode == AnalysisMode.TOU and self.simulation.hourly and has_baseline:
            # TOU-native LCCA with hourly data (requires baseline for comparison)
            results.lcca_results = self._run_tou_lcca(tariff, assumptions)
        else:
            # Simple annual LCCA (single scenario or no hourly data)
            results.lcca_results = self._run_simple_lcca(tariff, assumptions)

        # Generate ECON-1 report (needs simple Tariff, not TouTariff)
        # Use summer rates as representative blended rates
        simple_tariff = Tariff(
            name=tariff.name if hasattr(tariff, 'name') else "TOU Rate",
            utility=tariff.utility if hasattr(tariff, 'utility') else "",
            elec_rate_per_kwh=tariff.energy_rates.summer_off_peak if tariff.energy_rates else 0.20,
            gas_rate_per_therm=self.config.gas_rate,
            demand_rate_per_kw=tariff.demand_rates.summer_on_peak if tariff.demand_rates else 0,
            tou_enabled=True,
            on_peak_rate=tariff.energy_rates.summer_on_peak if tariff.energy_rates else 0.35,
            mid_peak_rate=tariff.energy_rates.summer_mid_peak if tariff.energy_rates else 0.25,
            off_peak_rate=tariff.energy_rates.summer_off_peak if tariff.energy_rates else 0.15,
        )
        # Include baseline if available for ECON-1 comparison
        baseline_sim = self.simulation.baseline if hasattr(self.simulation, 'baseline') else None
        results.econ1_report = generate_econ1(
            proposed=self.simulation,
            tariff=simple_tariff,
            baseline=baseline_sim,
            incremental_cost=self.config.capex,
        )

        # Calculate savings vs baseline if available (from LCCA results)
        if has_baseline and results.lcca_results:
            # TOU LCCA already calculated savings - extract from results
            results.savings_vs_baseline = results.lcca_results.lifecycle_savings

        # Generate outputs
        if self.config.output_formats:
            results.output_files = self._generate_outputs(results)

        return results

    def _run_simple_lcca(
        self,
        tariff: TouTariff,
        assumptions: ScenarioAssumptions,
    ) -> LccaResults:
        """Run simple annual LCCA."""
        scenario = simulation_to_scenario(
            self.simulation,
            Tariff(
                electricity_rate=tariff.rates.peak_rate,
                gas_rate=self.config.gas_rate,
                demand_rate=tariff.demand_rates.peak_rate if tariff.demand_rates else 0,
            ),
            self.config.capex,
            self.config.incentives,
            assumptions,
        )

        return run_lcca(scenario)

    def _run_tou_lcca(
        self,
        tariff: TouTariff,
        assumptions: ScenarioAssumptions,
    ) -> LccaResults:
        """Run TOU-native LCCA with hourly data comparing proposed vs baseline."""
        from .model import TouLccaScenario

        # Create baseline scenario
        baseline = self.simulation.baseline
        baseline_scenario = TouLccaScenario(
            name=f"{baseline.project_name} (Baseline)",
            hourly_data=baseline.hourly,
            tou_tariff=tariff,
            capex_upfront=0,  # Baseline has no incremental cost
            annual_gas_therms=baseline.annual.total_gas_therm,
            assumptions=assumptions,
        )

        # Create proposed scenario
        proposed_scenario = TouLccaScenario(
            name=self.simulation.project_name,
            hourly_data=self.simulation.hourly,
            tou_tariff=tariff,
            capex_upfront=self.config.capex - self.config.incentives,
            annual_gas_therms=self.simulation.annual.total_gas_therm,
            assumptions=assumptions,
        )

        # Run TOU LCCA comparison - returns TouLccaResults which extends LccaResults
        return run_tou_lcca(baseline_scenario, proposed_scenario, assumptions)

    def _generate_outputs(self, results: RunnerResults) -> List[Path]:
        """Generate output files."""
        output_files = []

        output_dir = self.config.output_dir or self.project_dir

        for fmt in self.config.output_formats:
            try:
                if fmt == OutputFormat.EXCEL:
                    path = output_dir / f"{results.project_name}_LCCA.xlsx"
                    export_lcca_to_excel(
                        results.lcca_results,
                        str(path),
                        ExcelExportOptions(
                            include_charts=True,
                            include_sensitivity=True,
                        ),
                    )
                    output_files.append(path)

                elif fmt == OutputFormat.TEXT:
                    path = output_dir / f"{results.project_name}_LCCA.txt"
                    with open(path, "w") as f:
                        f.write(format_lcca_summary(results.lcca_results))
                        f.write("\n\n")
                        if results.econ1_report:
                            f.write(export_econ1_text(results.econ1_report))
                    output_files.append(path)

                elif fmt == OutputFormat.JSON:
                    import json
                    path = output_dir / f"{results.project_name}_LCCA.json"
                    with open(path, "w") as f:
                        json.dump(results.summary(), f, indent=2)
                    output_files.append(path)

            except Exception as e:
                results.warnings.append(f"Failed to generate {fmt.value}: {e}")
                logger.warning(f"Failed to generate {fmt.value}: {e}")

        return output_files

    def export_excel(
        self,
        output_path: Optional[str] = None,
        include_charts: bool = True,
        include_sensitivity: bool = True,
    ) -> Path:
        """
        Export LCCA results to Excel.

        Args:
            output_path: Output file path (optional)
            include_charts: Include charts in export
            include_sensitivity: Include sensitivity analysis

        Returns:
            Path to generated Excel file
        """
        if output_path is None:
            output_dir = self.config.output_dir or self.project_dir
            project_name = self.simulation.project_name if self.simulation else "LCCA"
            output_path = str(output_dir / f"{project_name}_LCCA.xlsx")

        results = self.run() if self.simulation is None else None

        export_lcca_to_excel(
            results.lcca_results if results else self._last_results.lcca_results,
            output_path,
            ExcelExportOptions(
                include_charts=include_charts,
                include_sensitivity=include_sensitivity,
            ),
        )

        return Path(output_path)

    def print_summary(self) -> None:
        """Print summary to console."""
        if self.outputs:
            print(format_discovery_summary(self.outputs))
            print()

        if hasattr(self, "_last_results") and self._last_results:
            print(format_lcca_summary(self._last_results.lcca_results))


def run_lcca_workflow(
    project_dir: Union[str, Path],
    rate_id: Optional[str] = None,
    region: Optional[str] = None,
    capex: float = 0.0,
    output_excel: bool = True,
) -> RunnerResults:
    """
    Convenience function to run complete LCCA workflow.

    Args:
        project_dir: Path to project with simulation outputs
        rate_id: Utility rate identifier
        region: Regional cost factor code
        capex: Capital expenditure
        output_excel: Generate Excel output

    Returns:
        RunnerResults with analysis results
    """
    runner = LccaRunner(project_dir)

    runner.configure(
        rate_id=rate_id,
        region=region,
        capex=capex,
        output_formats=[OutputFormat.EXCEL] if output_excel else [],
    )

    return runner.run()


def batch_lcca(
    base_dir: Union[str, Path],
    rate_id: Optional[str] = None,
    region: Optional[str] = None,
) -> List[RunnerResults]:
    """
    Run LCCA on multiple projects in a directory.

    Args:
        base_dir: Directory containing project folders
        rate_id: Common rate ID for all projects
        region: Common region for all projects

    Returns:
        List of RunnerResults for each project
    """
    from .auto_discovery import discover_multiple_projects

    base_path = Path(base_dir)
    all_outputs = discover_multiple_projects(base_path)

    results = []
    for outputs in all_outputs:
        try:
            runner = LccaRunner(outputs.project_dir, auto_discover=False)
            runner.outputs = outputs
            runner.configure(rate_id=rate_id, region=region)
            result = runner.run()
            results.append(result)
            logger.info(f"Completed LCCA for {outputs.project_name}")
        except Exception as e:
            logger.error(f"Failed LCCA for {outputs.project_name}: {e}")

    return results
