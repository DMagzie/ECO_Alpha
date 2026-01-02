"""
Zone Simulation Pipeline Orchestrator
=====================================

High-level API for zone-level energy simulation.

This module orchestrates the complete pipeline:
1. Parse CSE input file
2. Map zones to hierarchical meters
3. Transform CSE input with zone meters
4. Run CSE simulation (if available)
5. Parse zone-level output
6. Return ZoneEnergySummary objects

The pipeline enables zone-level LCCA by producing hourly
energy data for each zone, suitable for TOU rate calculations
and mixed-use building cost allocation.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import logging
import tempfile
import shutil

from .parsers.cse_zone_input import (
    parse_cse_zone_input,
    CSEZoneInputModel,
)
from .parsers.cse_zone_output import (
    parse_cse_zone_output,
    CSEZoneOutputModel,
    ZoneHourlyData,
    ZoneGasHourlyData,
)
from .zone_meter_mapper import (
    ZoneMeterMapper,
    ZoneMeterAssignment,
    MeterHierarchy,
    format_meter_hierarchy,
)
from .cse_transformer import (
    CSETransformer,
    TransformResult,
)
from .cse_runner import (
    CSERunner,
    CSERunConfig,
    CSERunResult,
    check_cse_available,
)
from .zone_energy import ZoneEnergySummary, create_zone_energy_from_hourly
from .cuac.models import ZoneType
from .res_other.models import CommonAreaCategory

logger = logging.getLogger(__name__)


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class ZoneSimulationConfig:
    """Configuration for zone simulation pipeline."""
    cbecc_run_dir: Path
    output_dir: Optional[Path] = None

    # Input file selection
    use_proposed: bool = True     # Use proposed design (ap-cse.cse)
    use_baseline: bool = False    # Also process baseline (ab-cse.cse)

    # CSE execution
    run_cse: bool = True          # Attempt to run CSE
    cse_timeout: int = 600        # CSE timeout in seconds

    # Output options
    keep_transformed: bool = True  # Keep transformed CSE files
    export_csv: bool = True        # Export zone summaries to CSV

    def __post_init__(self):
        """Validate and resolve paths."""
        self.cbecc_run_dir = Path(self.cbecc_run_dir)
        if not self.cbecc_run_dir.exists():
            raise FileNotFoundError(f"Directory not found: {self.cbecc_run_dir}")

        if self.output_dir:
            self.output_dir = Path(self.output_dir)
        else:
            self.output_dir = self.cbecc_run_dir / "zone_analysis"


@dataclass
class ZoneSimulationResult:
    """
    Complete result from zone simulation pipeline.

    Contains zone energy summaries, meter hierarchy, and execution status.
    """
    success: bool
    project_name: str = ""

    # Zone energy summaries
    proposed_zones: List[ZoneEnergySummary] = field(default_factory=list)
    baseline_zones: Optional[List[ZoneEnergySummary]] = None

    # Mapping info
    zone_assignments: Dict[str, ZoneMeterAssignment] = field(default_factory=dict)
    meter_hierarchy: Optional[MeterHierarchy] = None

    # CSE execution info
    cse_available: bool = False
    cse_executed: bool = False
    cse_result: Optional[CSERunResult] = None

    # Parsed models (for advanced use)
    input_model: Optional[CSEZoneInputModel] = None
    output_model: Optional[CSEZoneOutputModel] = None
    transform_result: Optional[TransformResult] = None

    # Output files
    transformed_cse_file: Optional[Path] = None
    output_csv_file: Optional[Path] = None

    # Errors and warnings
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    @property
    def zone_count(self) -> int:
        """Number of zones in result."""
        return len(self.proposed_zones)

    @property
    def total_annual_kwh(self) -> float:
        """Total annual electricity across all zones."""
        return sum(z.elec_kwh for z in self.proposed_zones)

    @property
    def has_hourly_data(self) -> bool:
        """Check if hourly data is available."""
        if not self.proposed_zones:
            return False
        return any(z.hourly_elec_kwh is not None for z in self.proposed_zones)

    def get_zones_by_type(self, zone_type: ZoneType) -> List[ZoneEnergySummary]:
        """Get zones of a specific type."""
        return [z for z in self.proposed_zones if z.zone_type == zone_type]

    def get_dwelling_units(self) -> List[ZoneEnergySummary]:
        """Get all dwelling unit zones."""
        return self.get_zones_by_type(ZoneType.DWELLING_UNIT)

    def get_common_areas(self) -> List[ZoneEnergySummary]:
        """Get all common area zones."""
        return self.get_zones_by_type(ZoneType.COMMON_AREA)


# =============================================================================
# PIPELINE ORCHESTRATOR
# =============================================================================

class ZoneSimulationPipeline:
    """
    Orchestrates the complete zone-level simulation pipeline.

    Example usage:
        >>> pipeline = ZoneSimulationPipeline()
        >>> config = ZoneSimulationConfig(cbecc_run_dir=Path("/path/to/run"))
        >>> result = pipeline.run(config)
        >>> for zone in result.proposed_zones:
        ...     print(f"{zone.zone_name}: {zone.elec_kwh:.0f} kWh")
    """

    def __init__(self):
        """Initialize the pipeline."""
        self._mapper = ZoneMeterMapper()
        self._transformer = CSETransformer()
        self._runner = CSERunner()

    def run(self, config: ZoneSimulationConfig) -> ZoneSimulationResult:
        """
        Execute the complete zone simulation pipeline.

        Args:
            config: ZoneSimulationConfig with paths and options

        Returns:
            ZoneSimulationResult with zone energy summaries
        """
        result = ZoneSimulationResult(success=False)

        try:
            # 1. Find CSE input file
            cse_file = self._find_cse_input(config)
            if not cse_file:
                result.errors.append("No CSE input file found in run directory")
                return result

            result.project_name = cse_file.stem

            # 2. Parse CSE input
            logger.info(f"Parsing CSE input: {cse_file}")
            input_model = parse_cse_zone_input(cse_file)
            result.input_model = input_model

            if not input_model.zones:
                result.errors.append("No zones found in CSE input")
                return result

            # 3. Map zones to meters
            logger.info(f"Mapping {len(input_model.zones)} zones to meters")
            self._mapper.map_zones(input_model.zones)
            result.zone_assignments = self._mapper.get_zone_assignments()
            result.meter_hierarchy = self._mapper.get_meter_hierarchy()

            # 4. Transform CSE input with zone meters
            logger.info("Transforming CSE input with zone meters")
            config.output_dir.mkdir(parents=True, exist_ok=True)
            transformed_file = config.output_dir / f"{cse_file.stem}_zoned.cse"

            transform_result = self._transformer.transform_file(cse_file, transformed_file)
            result.transform_result = transform_result
            result.transformed_cse_file = transformed_file

            if not transform_result.success:
                result.errors.extend(transform_result.errors)
                result.warnings.extend(transform_result.warnings)
                # Continue even if transformation has issues

            # 5. Check CSE availability
            cse_available, cse_path = check_cse_available()
            result.cse_available = cse_available

            # 6. Run CSE if available and requested
            if config.run_cse and cse_available:
                logger.info("Running CSE simulation")
                run_config = CSERunConfig(
                    input_file=transformed_file,
                    output_dir=config.output_dir,
                    timeout_seconds=config.cse_timeout,
                )
                cse_result = self._runner.run(run_config)
                result.cse_result = cse_result
                result.cse_executed = True

                if not cse_result.success:
                    result.warnings.append(f"CSE execution failed: {cse_result.error_message}")

            # 7. Parse output (either from CSE run or existing output)
            output_csv = self._find_output_csv(config, result)
            if output_csv:
                logger.info(f"Parsing output: {output_csv}")
                output_model = parse_cse_zone_output(output_csv)
                result.output_model = output_model

                # 8. Create ZoneEnergySummary objects
                result.proposed_zones = self._create_zone_summaries(
                    output_model, result.zone_assignments
                )

            # If no output available, create summaries without hourly data
            if not result.proposed_zones:
                result.proposed_zones = self._create_summaries_from_mapping(
                    result.zone_assignments, input_model
                )
                result.warnings.append("No simulation output available - summaries lack hourly data")

            result.success = True
            logger.info(f"Pipeline complete: {len(result.proposed_zones)} zones processed")

        except Exception as e:
            result.errors.append(f"Pipeline error: {e}")
            logger.error(f"Pipeline error: {e}")

        return result

    def _find_cse_input(self, config: ZoneSimulationConfig) -> Optional[Path]:
        """Find the CSE input file in the run directory."""
        run_dir = config.cbecc_run_dir

        # Look for proposed (ap-cse.cse) file
        if config.use_proposed:
            for pattern in ["*-ap-cse.cse", "*ap-cse.cse", "* - ap-cse.cse"]:
                files = list(run_dir.glob(pattern))
                if files:
                    return files[0]

        # Look for baseline (ab-cse.cse) file
        if config.use_baseline:
            for pattern in ["*-ab-cse.cse", "*ab-cse.cse", "* - ab-cse.cse"]:
                files = list(run_dir.glob(pattern))
                if files:
                    return files[0]

        # Fallback: any .cse file
        cse_files = list(run_dir.glob("*.cse"))
        if cse_files:
            return cse_files[0]

        return None

    def _find_output_csv(
        self,
        config: ZoneSimulationConfig,
        result: ZoneSimulationResult,
    ) -> Optional[Path]:
        """Find the CSE output CSV file."""
        # If CSE was run successfully, use its output
        if result.cse_result and result.cse_result.csv_output:
            return result.cse_result.csv_output

        # Look for existing output in output directory
        for pattern in ["*-CSE.CSV", "*-CSE.csv"]:
            files = list(config.output_dir.glob(pattern))
            if files:
                return files[0]

        # Look in original run directory
        for pattern in ["*-CSE.CSV", "*-CSE.csv", "*AP-CSE.CSV"]:
            files = list(config.cbecc_run_dir.glob(pattern))
            if files:
                return files[0]

        return None

    def _create_zone_summaries(
        self,
        output_model: CSEZoneOutputModel,
        zone_assignments: Dict[str, ZoneMeterAssignment],
    ) -> List[ZoneEnergySummary]:
        """Create ZoneEnergySummary objects from output model (electric and gas)."""
        summaries = []

        for zone_name, assignment in zone_assignments.items():
            meter_name = assignment.zone_meter

            # Find corresponding electric meter data in output
            meter_data = output_model.get_meter(meter_name)

            # Find corresponding gas meter data in output
            gas_meter_name = assignment.gas_zone_meter if assignment.has_gas else None
            gas_meter_data = output_model.get_gas_meter(gas_meter_name) if gas_meter_name else None

            if meter_data and meter_data.is_complete:
                # Create summary with hourly data
                zone_type = self._assignment_to_zone_type(assignment)
                category = assignment.category

                # Get hourly gas data if available
                hourly_gas = None
                if gas_meter_data and gas_meter_data.is_complete:
                    hourly_gas = gas_meter_data.total_therm

                summary = create_zone_energy_from_hourly(
                    zone_name=zone_name,
                    zone_type=zone_type,
                    hourly_elec=meter_data.total_kwh,
                    hourly_gas=hourly_gas,
                    area_sqft=assignment.area_sf,
                    num_bedrooms=assignment.bedroom_count or 0,
                    category=category,
                )

                # Add electric end-use breakdown
                breakdown = meter_data.get_end_use_breakdown()
                summary.cooling_kwh = breakdown["cooling"]
                summary.heating_kwh = breakdown["heating"]
                summary.dhw_kwh = breakdown["dhw"]
                summary.lighting_kwh = breakdown["lighting"]
                summary.receptacle_kwh = breakdown["receptacle"]
                summary.ventilation_kwh = breakdown["ventilation"]

                # Add gas end-use breakdown if available
                if gas_meter_data and gas_meter_data.is_complete:
                    gas_breakdown = gas_meter_data.get_end_use_breakdown()
                    summary.heating_therm = gas_breakdown["heating"]
                    summary.dhw_therm = gas_breakdown["dhw"]

                summaries.append(summary)
            else:
                # No output data - create minimal summary
                summary = self._create_minimal_summary(zone_name, assignment)
                summaries.append(summary)

        return summaries

    def _create_summaries_from_mapping(
        self,
        zone_assignments: Dict[str, ZoneMeterAssignment],
        input_model: CSEZoneInputModel,
    ) -> List[ZoneEnergySummary]:
        """Create minimal ZoneEnergySummary objects from mapping only."""
        summaries = []

        for zone_name, assignment in zone_assignments.items():
            summary = self._create_minimal_summary(zone_name, assignment)
            summaries.append(summary)

        return summaries

    def _create_minimal_summary(
        self,
        zone_name: str,
        assignment: ZoneMeterAssignment,
    ) -> ZoneEnergySummary:
        """Create a minimal ZoneEnergySummary without energy data."""
        zone_type = self._assignment_to_zone_type(assignment)

        return ZoneEnergySummary(
            zone_name=zone_name,
            zone_type=zone_type,
            category=assignment.category,
            area_sqft=assignment.area_sf,
            num_bedrooms=assignment.bedroom_count or 0,
            multiplier=assignment.multiplier,
        )

    def _assignment_to_zone_type(self, assignment: ZoneMeterAssignment) -> ZoneType:
        """Convert ZoneMeterAssignment classification to ZoneType."""
        from .zone_meter_mapper import ZoneClassification

        if assignment.zone_classification == ZoneClassification.DWELLING_UNIT:
            return ZoneType.DWELLING_UNIT
        elif assignment.zone_classification == ZoneClassification.COMMON_AREA:
            return ZoneType.COMMON_AREA
        elif assignment.zone_classification == ZoneClassification.UNCONDITIONED:
            return ZoneType.UNCONDITIONED
        else:
            return ZoneType.COMMON_AREA  # Default


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def run_zone_simulation(
    cbecc_run_dir: Path,
    output_dir: Optional[Path] = None,
    run_cse: bool = True,
) -> ZoneSimulationResult:
    """
    Run zone-level simulation analysis.

    Args:
        cbecc_run_dir: Path to CBECC run directory with CSE files
        output_dir: Optional output directory
        run_cse: Whether to run CSE if available

    Returns:
        ZoneSimulationResult with zone energy summaries
    """
    config = ZoneSimulationConfig(
        cbecc_run_dir=cbecc_run_dir,
        output_dir=output_dir,
        run_cse=run_cse,
    )
    pipeline = ZoneSimulationPipeline()
    return pipeline.run(config)


def format_simulation_result(result: ZoneSimulationResult) -> str:
    """
    Format simulation result as text summary.

    Args:
        result: ZoneSimulationResult

    Returns:
        Formatted summary string
    """
    lines = [
        "=" * 70,
        "ZONE SIMULATION RESULT",
        "=" * 70,
        "",
        f"Project: {result.project_name}",
        f"Success: {result.success}",
        f"CSE Available: {result.cse_available}",
        f"CSE Executed: {result.cse_executed}",
        f"Zone Count: {result.zone_count}",
        f"Has Hourly Data: {result.has_hourly_data}",
    ]

    if result.total_annual_kwh > 0:
        lines.append(f"Total Annual kWh: {result.total_annual_kwh:,.0f}")

    if result.proposed_zones:
        # Dwelling unit summary
        dus = result.get_dwelling_units()
        if dus:
            lines.extend([
                "",
                f"Dwelling Units: {len(dus)}",
            ])

        # Common area summary
        cas = result.get_common_areas()
        if cas:
            lines.extend([
                f"Common Areas: {len(cas)}",
            ])

        # Zone details
        lines.extend([
            "",
            "Zone Summaries:",
            "-" * 70,
            f"{'Zone':<35} {'Type':<12} {'kWh':>12} {'Area':>8}",
            "-" * 70,
        ])

        for zone in sorted(result.proposed_zones, key=lambda z: z.zone_name):
            zone_type = "DU" if zone.is_dwelling_unit else "CA"
            lines.append(
                f"{zone.zone_name:<35} {zone_type:<12} "
                f"{zone.elec_kwh:>12,.0f} {zone.area_sqft:>8,.0f}"
            )

    if result.errors:
        lines.extend([
            "",
            "Errors:",
        ])
        for err in result.errors:
            lines.append(f"  - {err}")

    if result.warnings:
        lines.extend([
            "",
            "Warnings:",
        ])
        for warn in result.warnings[:5]:
            lines.append(f"  - {warn}")

    lines.append("=" * 70)

    return "\n".join(lines)
