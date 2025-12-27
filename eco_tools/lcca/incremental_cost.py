"""
Incremental Cost Calculator for LCCA.

Calculates the incremental first cost between baseline (standard) and
proposed designs by comparing HVAC, DHW, and envelope component costs.

Approach:
- Parse simulation output CSVs (HVACSecondary, HVACPrimary, Envelope)
- Map component specs to CostDB costs with efficiency adders
- Calculate: Incremental Cost = Σ(Proposed Costs) - Σ(Baseline Costs)

Usage:
    from eco_tools.lcca.incremental_cost import IncrementalCostCalculator

    calculator = IncrementalCostCalculator()
    result = calculator.calculate(
        baseline_dir="/path/to/baseline/run",
        proposed_dir="/path/to/proposed/run"
    )
    print(f"Total incremental cost: ${result.total_incremental:,.0f}")
"""

from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
import logging

from .costdb import CostDatabase, create_default_costdb
from .cost_mappers import HVACCostMapper, DHWCostMapper, EnvelopeCostMapper
from .parsers.hvac_secondary import parse_hvac_secondary, HVACSecondaryOutput
from .parsers.hvac_primary import parse_hvac_primary, HVACPrimaryOutput
from .parsers.envelope import parse_envelope, EnvelopeOutput
from .auto_discovery import discover_simulation_outputs, DiscoveredOutputs

logger = logging.getLogger(__name__)


@dataclass
class ComponentCost:
    """Cost breakdown for a single component type."""
    component_type: str  # 'hvac_secondary', 'hvac_primary', 'envelope_wall', etc.
    baseline_cost: float
    proposed_cost: float
    incremental_cost: float
    details: Dict[str, Any] = field(default_factory=dict)

    @property
    def is_savings(self) -> bool:
        """True if proposed is cheaper than baseline."""
        return self.incremental_cost < 0


@dataclass
class IncrementalCostResult:
    """Complete incremental cost calculation result."""
    project_name: str
    region: str

    # Component breakdowns
    hvac_secondary: Optional[ComponentCost] = None
    hvac_primary: Optional[ComponentCost] = None
    envelope_walls: Optional[ComponentCost] = None
    envelope_windows: Optional[ComponentCost] = None
    envelope_roof: Optional[ComponentCost] = None

    # Totals
    total_baseline: float = 0.0
    total_proposed: float = 0.0
    total_incremental: float = 0.0

    # Metadata
    calculation_date: datetime = field(default_factory=datetime.now)
    warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        result = {
            "project_name": self.project_name,
            "region": self.region,
            "total_baseline": self.total_baseline,
            "total_proposed": self.total_proposed,
            "total_incremental": self.total_incremental,
            "calculation_date": self.calculation_date.isoformat(),
            "warnings": self.warnings,
            "components": {}
        }

        if self.hvac_secondary:
            result["components"]["hvac_secondary"] = {
                "baseline": self.hvac_secondary.baseline_cost,
                "proposed": self.hvac_secondary.proposed_cost,
                "incremental": self.hvac_secondary.incremental_cost,
                "details": self.hvac_secondary.details
            }

        if self.hvac_primary:
            result["components"]["hvac_primary"] = {
                "baseline": self.hvac_primary.baseline_cost,
                "proposed": self.hvac_primary.proposed_cost,
                "incremental": self.hvac_primary.incremental_cost,
                "details": self.hvac_primary.details
            }

        if self.envelope_walls:
            result["components"]["envelope_walls"] = {
                "baseline": self.envelope_walls.baseline_cost,
                "proposed": self.envelope_walls.proposed_cost,
                "incremental": self.envelope_walls.incremental_cost,
                "details": self.envelope_walls.details
            }

        if self.envelope_windows:
            result["components"]["envelope_windows"] = {
                "baseline": self.envelope_windows.baseline_cost,
                "proposed": self.envelope_windows.proposed_cost,
                "incremental": self.envelope_windows.incremental_cost,
                "details": self.envelope_windows.details
            }

        if self.envelope_roof:
            result["components"]["envelope_roof"] = {
                "baseline": self.envelope_roof.baseline_cost,
                "proposed": self.envelope_roof.proposed_cost,
                "incremental": self.envelope_roof.incremental_cost,
                "details": self.envelope_roof.details
            }

        return result

    def format_summary(self) -> str:
        """Format a human-readable summary."""
        lines = [
            f"Incremental Cost Analysis: {self.project_name}",
            f"Region: {self.region}",
            "=" * 60,
            "",
            "Component Breakdown:",
            "-" * 60,
            f"{'Component':<25} {'Baseline':>12} {'Proposed':>12} {'Incremental':>12}",
            "-" * 60,
        ]

        components = [
            ("HVAC Secondary", self.hvac_secondary),
            ("HVAC Primary (DHW)", self.hvac_primary),
            ("Envelope - Walls", self.envelope_walls),
            ("Envelope - Windows", self.envelope_windows),
            ("Envelope - Roof", self.envelope_roof),
        ]

        for name, comp in components:
            if comp:
                lines.append(
                    f"{name:<25} ${comp.baseline_cost:>10,.0f} ${comp.proposed_cost:>10,.0f} ${comp.incremental_cost:>10,.0f}"
                )

        lines.extend([
            "-" * 60,
            f"{'TOTAL':<25} ${self.total_baseline:>10,.0f} ${self.total_proposed:>10,.0f} ${self.total_incremental:>10,.0f}",
            "",
        ])

        if self.total_incremental > 0:
            lines.append(f"Net incremental cost: ${self.total_incremental:,.0f} (proposed is more expensive)")
        elif self.total_incremental < 0:
            lines.append(f"Net incremental savings: ${abs(self.total_incremental):,.0f} (proposed is cheaper)")
        else:
            lines.append("No incremental cost difference.")

        if self.warnings:
            lines.extend([
                "",
                "Warnings:",
                "-" * 60,
            ])
            for warning in self.warnings:
                lines.append(f"  - {warning}")

        return "\n".join(lines)


class IncrementalCostCalculator:
    """
    Calculate incremental costs from baseline vs proposed simulations.

    Uses Tier 1 (rules of thumb) cost estimation:
    - HVAC: System type + capacity + efficiency adder
    - DHW: Water heater type + capacity + efficiency adder
    - Envelope: Generic material costs by performance tier
    """

    def __init__(
        self,
        costdb: Optional[CostDatabase] = None,
        region: str = "national"
    ):
        """
        Initialize the calculator.

        Args:
            costdb: Cost database (uses default if None)
            region: Region code for regional cost adjustment
        """
        self.costdb = costdb or create_default_costdb()
        self.region = region

        # Initialize mappers
        self.hvac_mapper = HVACCostMapper(self.costdb, region)
        self.dhw_mapper = DHWCostMapper(self.costdb, region)
        self.envelope_mapper = EnvelopeCostMapper(self.costdb, region)

    def calculate(
        self,
        baseline_dir: str | Path,
        proposed_dir: str | Path,
        project_name: Optional[str] = None
    ) -> IncrementalCostResult:
        """
        Calculate incremental costs between baseline and proposed designs.

        Args:
            baseline_dir: Directory containing baseline simulation outputs
            proposed_dir: Directory containing proposed simulation outputs
            project_name: Project name (auto-detected if None)

        Returns:
            IncrementalCostResult with full breakdown
        """
        baseline_path = Path(baseline_dir)
        proposed_path = Path(proposed_dir)

        # Initialize result
        result = IncrementalCostResult(
            project_name=project_name or proposed_path.name,
            region=self.region
        )

        # Parse baseline and proposed data
        baseline_hvac_sec, baseline_hvac_pri, baseline_env = self._parse_all(
            baseline_path, result, "baseline"
        )
        proposed_hvac_sec, proposed_hvac_pri, proposed_env = self._parse_all(
            proposed_path, result, "proposed"
        )

        # Calculate HVAC Secondary costs
        if baseline_hvac_sec and proposed_hvac_sec:
            result.hvac_secondary = self._calculate_hvac_secondary_cost(
                baseline_hvac_sec, proposed_hvac_sec
            )

        # Calculate HVAC Primary (DHW/central plant) costs
        if baseline_hvac_pri and proposed_hvac_pri:
            result.hvac_primary = self._calculate_hvac_primary_cost(
                baseline_hvac_pri, proposed_hvac_pri
            )

        # Calculate Envelope costs
        if baseline_env and proposed_env:
            wall_cost, window_cost, roof_cost = self._calculate_envelope_costs(
                baseline_env, proposed_env
            )
            result.envelope_walls = wall_cost
            result.envelope_windows = window_cost
            result.envelope_roof = roof_cost

        # Calculate totals
        result.total_baseline = sum(
            comp.baseline_cost for comp in [
                result.hvac_secondary, result.hvac_primary,
                result.envelope_walls, result.envelope_windows, result.envelope_roof
            ] if comp
        )

        result.total_proposed = sum(
            comp.proposed_cost for comp in [
                result.hvac_secondary, result.hvac_primary,
                result.envelope_walls, result.envelope_windows, result.envelope_roof
            ] if comp
        )

        result.total_incremental = result.total_proposed - result.total_baseline

        return result

    def calculate_from_discovery(
        self,
        outputs: DiscoveredOutputs
    ) -> IncrementalCostResult:
        """
        Calculate incremental costs from discovered simulation outputs.

        Args:
            outputs: DiscoveredOutputs from auto_discovery

        Returns:
            IncrementalCostResult with full breakdown
        """
        result = IncrementalCostResult(
            project_name=outputs.project_name,
            region=self.region
        )

        # Parse HVAC Secondary
        baseline_hvac_sec = None
        proposed_hvac_sec = None
        if outputs.hvac_secondary_standard:
            try:
                baseline_hvac_sec = parse_hvac_secondary(outputs.hvac_secondary_standard.path)
            except Exception as e:
                result.warnings.append(f"Failed to parse baseline HVAC Secondary: {e}")
        if outputs.hvac_secondary_proposed:
            try:
                proposed_hvac_sec = parse_hvac_secondary(outputs.hvac_secondary_proposed.path)
            except Exception as e:
                result.warnings.append(f"Failed to parse proposed HVAC Secondary: {e}")

        # Parse HVAC Primary
        baseline_hvac_pri = None
        proposed_hvac_pri = None
        if outputs.hvac_primary_standard:
            try:
                baseline_hvac_pri = parse_hvac_primary(outputs.hvac_primary_standard.path)
            except Exception as e:
                result.warnings.append(f"Failed to parse baseline HVAC Primary: {e}")
        if outputs.hvac_primary_proposed:
            try:
                proposed_hvac_pri = parse_hvac_primary(outputs.hvac_primary_proposed.path)
            except Exception as e:
                result.warnings.append(f"Failed to parse proposed HVAC Primary: {e}")

        # Parse Envelope
        baseline_env = None
        proposed_env = None
        if outputs.envelope_standard:
            try:
                baseline_env = parse_envelope(outputs.envelope_standard.path)
            except Exception as e:
                result.warnings.append(f"Failed to parse baseline Envelope: {e}")
        if outputs.envelope_proposed:
            try:
                proposed_env = parse_envelope(outputs.envelope_proposed.path)
            except Exception as e:
                result.warnings.append(f"Failed to parse proposed Envelope: {e}")

        # Calculate costs
        if baseline_hvac_sec and proposed_hvac_sec:
            result.hvac_secondary = self._calculate_hvac_secondary_cost(
                baseline_hvac_sec, proposed_hvac_sec
            )

        if baseline_hvac_pri and proposed_hvac_pri:
            result.hvac_primary = self._calculate_hvac_primary_cost(
                baseline_hvac_pri, proposed_hvac_pri
            )

        if baseline_env and proposed_env:
            wall_cost, window_cost, roof_cost = self._calculate_envelope_costs(
                baseline_env, proposed_env
            )
            result.envelope_walls = wall_cost
            result.envelope_windows = window_cost
            result.envelope_roof = roof_cost

        # Calculate totals
        result.total_baseline = sum(
            comp.baseline_cost for comp in [
                result.hvac_secondary, result.hvac_primary,
                result.envelope_walls, result.envelope_windows, result.envelope_roof
            ] if comp
        )

        result.total_proposed = sum(
            comp.proposed_cost for comp in [
                result.hvac_secondary, result.hvac_primary,
                result.envelope_walls, result.envelope_windows, result.envelope_roof
            ] if comp
        )

        result.total_incremental = result.total_proposed - result.total_baseline

        return result

    def _parse_all(
        self,
        run_dir: Path,
        result: IncrementalCostResult,
        scenario: str
    ) -> Tuple[Optional[HVACSecondaryOutput], Optional[HVACPrimaryOutput], Optional[EnvelopeOutput]]:
        """Parse all CSV files from a run directory."""
        hvac_sec = None
        hvac_pri = None
        env = None

        # Try to find files using patterns
        scenario_code = "ap" if scenario == "proposed" else "ab"

        # Look for HVACSecondary
        hvac_sec_files = list(run_dir.glob(f"*- {scenario_code} - HVACSecondary.csv"))
        if not hvac_sec_files:
            hvac_sec_files = list(run_dir.glob(f"*-{scenario_code}-HVACSecondary.csv"))
        if hvac_sec_files:
            try:
                hvac_sec = parse_hvac_secondary(hvac_sec_files[0])
            except Exception as e:
                result.warnings.append(f"Failed to parse {scenario} HVACSecondary: {e}")

        # Look for HVACPrimary
        hvac_pri_files = list(run_dir.glob(f"*- {scenario_code} - HVACPrimary.csv"))
        if not hvac_pri_files:
            hvac_pri_files = list(run_dir.glob(f"*-{scenario_code}-HVACPrimary.csv"))
        if hvac_pri_files:
            try:
                hvac_pri = parse_hvac_primary(hvac_pri_files[0])
            except Exception as e:
                result.warnings.append(f"Failed to parse {scenario} HVACPrimary: {e}")

        # Look for Envelope
        env_files = list(run_dir.glob(f"*- {scenario_code} - Envelope.csv"))
        if not env_files:
            env_files = list(run_dir.glob(f"*-{scenario_code}-Envelope.csv"))
        if env_files:
            try:
                env = parse_envelope(env_files[0])
            except Exception as e:
                result.warnings.append(f"Failed to parse {scenario} Envelope: {e}")

        return hvac_sec, hvac_pri, env

    def _calculate_hvac_secondary_cost(
        self,
        baseline: HVACSecondaryOutput,
        proposed: HVACSecondaryOutput
    ) -> ComponentCost:
        """Calculate HVAC Secondary (air/zone systems) cost difference."""
        baseline_cost = self.hvac_mapper.calculate_total_hvac_cost(baseline)
        proposed_cost = self.hvac_mapper.calculate_total_hvac_cost(proposed)

        details = {
            "baseline_systems": len(baseline.air_systems) + len(baseline.zone_systems),
            "proposed_systems": len(proposed.air_systems) + len(proposed.zone_systems),
            "baseline_capacity_tons": baseline.total_cooling_capacity_tons,
            "proposed_capacity_tons": proposed.total_cooling_capacity_tons,
            "baseline_avg_seer": baseline.average_seer,
            "proposed_avg_seer": proposed.average_seer,
        }

        return ComponentCost(
            component_type="hvac_secondary",
            baseline_cost=baseline_cost,
            proposed_cost=proposed_cost,
            incremental_cost=proposed_cost - baseline_cost,
            details=details
        )

    def _calculate_hvac_primary_cost(
        self,
        baseline: HVACPrimaryOutput,
        proposed: HVACPrimaryOutput
    ) -> ComponentCost:
        """Calculate HVAC Primary (DHW/central plant) cost difference."""
        baseline_cost = self.dhw_mapper.calculate_total_dhw_cost(baseline)
        proposed_cost = self.dhw_mapper.calculate_total_dhw_cost(proposed)

        details = {
            "baseline_water_heaters": len(baseline.water_heaters),
            "proposed_water_heaters": len(proposed.water_heaters),
            "baseline_boilers": len(baseline.boilers),
            "proposed_boilers": len(proposed.boilers),
            "baseline_chillers": len(baseline.chillers),
            "proposed_chillers": len(proposed.chillers),
        }

        return ComponentCost(
            component_type="hvac_primary",
            baseline_cost=baseline_cost,
            proposed_cost=proposed_cost,
            incremental_cost=proposed_cost - baseline_cost,
            details=details
        )

    def _calculate_envelope_costs(
        self,
        baseline: EnvelopeOutput,
        proposed: EnvelopeOutput
    ) -> Tuple[ComponentCost, ComponentCost, ComponentCost]:
        """Calculate envelope component cost differences."""
        # Wall costs
        baseline_wall = self.envelope_mapper.calculate_wall_cost(
            baseline.exterior_walls, baseline.construction_materials
        )
        proposed_wall = self.envelope_mapper.calculate_wall_cost(
            proposed.exterior_walls, proposed.construction_materials
        )
        wall_cost = ComponentCost(
            component_type="envelope_walls",
            baseline_cost=baseline_wall,
            proposed_cost=proposed_wall,
            incremental_cost=proposed_wall - baseline_wall,
            details={
                "baseline_wall_area_sf": baseline.building_areas.total_wall_area_sf if baseline.building_areas else 0,
                "proposed_wall_area_sf": proposed.building_areas.total_wall_area_sf if proposed.building_areas else 0,
            }
        )

        # Window costs
        baseline_window = self.envelope_mapper.calculate_window_cost(baseline.windows)
        proposed_window = self.envelope_mapper.calculate_window_cost(proposed.windows)
        window_cost = ComponentCost(
            component_type="envelope_windows",
            baseline_cost=baseline_window,
            proposed_cost=proposed_window,
            incremental_cost=proposed_window - baseline_window,
            details={
                "baseline_window_area_sf": baseline.building_areas.total_window_area_sf if baseline.building_areas else 0,
                "proposed_window_area_sf": proposed.building_areas.total_window_area_sf if proposed.building_areas else 0,
                "baseline_avg_u_factor": baseline.average_window_u_factor,
                "proposed_avg_u_factor": proposed.average_window_u_factor,
            }
        )

        # Roof costs
        baseline_roof = self.envelope_mapper.calculate_roof_cost(
            baseline.exterior_roofs, baseline.construction_materials
        )
        proposed_roof = self.envelope_mapper.calculate_roof_cost(
            proposed.exterior_roofs, proposed.construction_materials
        )
        roof_cost = ComponentCost(
            component_type="envelope_roof",
            baseline_cost=baseline_roof,
            proposed_cost=proposed_roof,
            incremental_cost=proposed_roof - baseline_roof,
            details={
                "baseline_roof_area_sf": baseline.building_areas.total_roof_area_sf if baseline.building_areas else 0,
                "proposed_roof_area_sf": proposed.building_areas.total_roof_area_sf if proposed.building_areas else 0,
            }
        )

        return wall_cost, window_cost, roof_cost


def calculate_incremental_cost(
    project_dir: str | Path,
    region: str = "national",
    costdb: Optional[CostDatabase] = None
) -> IncrementalCostResult:
    """
    Convenience function to calculate incremental cost for a project.

    Args:
        project_dir: Path to project directory (will auto-discover files)
        region: Region code for cost adjustment
        costdb: Optional cost database

    Returns:
        IncrementalCostResult with full breakdown
    """
    outputs = discover_simulation_outputs(project_dir)

    if not outputs.has_incremental_cost_data:
        raise ValueError(
            f"Insufficient data for incremental cost calculation. "
            f"Need at least one of: HVAC Secondary, HVAC Primary, or Envelope "
            f"comparison files (both -ap- and -ab- versions)."
        )

    calculator = IncrementalCostCalculator(costdb=costdb, region=region)
    return calculator.calculate_from_discovery(outputs)


def format_incremental_cost_report(result: IncrementalCostResult) -> str:
    """Format a detailed incremental cost report."""
    return result.format_summary()
