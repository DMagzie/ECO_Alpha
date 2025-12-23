"""
Cost Analysis Utility for LCCA Project Review.

This module provides tools for analyzing and reviewing the cost data
that feeds into LCCA financial calculations. It helps identify:
- Energy consumption patterns
- Rate/tariff impacts
- Discrepancies between calculation methods
- Data quality issues

Usage:
    from eco_tools.lcca.cost_analysis import analyze_project_costs

    report = analyze_project_costs("/path/to/project/run")
    print(report.format_summary())
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime
import json

from .auto_discovery import discover_simulation_outputs, DiscoveredOutputs
from .parsers import parse_hourly_results
from .model import SimulationOutput, HourlyEnergy, AnnualEnergySummary
from .tariffs import (
    TouTariff,
    get_tariff_by_name,
    calculate_tou_costs,
    hourly_energy_to_usage,
    TouCostBreakdown,
)


@dataclass
class EnergyAnalysis:
    """Detailed energy consumption analysis."""
    # Annual totals
    total_consumption_kwh: float = 0.0
    total_gas_therms: float = 0.0
    pv_generation_kwh: float = 0.0
    net_consumption_kwh: float = 0.0

    # Peak demand
    peak_demand_kw: float = 0.0
    peak_demand_month: int = 0
    peak_demand_hour: int = 0

    # Hourly statistics
    hourly_min_kwh: float = 0.0
    hourly_max_kwh: float = 0.0
    hourly_avg_kwh: float = 0.0

    # TOU distribution (percentage of consumption)
    on_peak_pct: float = 0.0
    mid_peak_pct: float = 0.0
    off_peak_pct: float = 0.0

    # Monthly breakdown
    monthly_consumption: List[float] = field(default_factory=list)
    monthly_peak_demand: List[float] = field(default_factory=list)


@dataclass
class TariffAnalysis:
    """Tariff cost analysis."""
    tariff_name: str = ""
    tariff_utility: str = ""

    # TOU cost breakdown
    tou_breakdown: Optional[TouCostBreakdown] = None

    # Cost components
    energy_cost: float = 0.0
    demand_cost: float = 0.0
    fixed_charges: float = 0.0
    total_annual_cost: float = 0.0

    # Effective rates
    effective_rate_per_kwh: float = 0.0
    blended_energy_rate: float = 0.0


@dataclass
class ComparisonAnalysis:
    """Baseline vs Proposed comparison analysis."""
    # Energy comparison
    baseline_consumption_kwh: float = 0.0
    proposed_consumption_kwh: float = 0.0
    consumption_savings_kwh: float = 0.0
    consumption_savings_pct: float = 0.0

    # Cost comparison
    baseline_annual_cost: float = 0.0
    proposed_annual_cost: float = 0.0
    annual_cost_savings: float = 0.0
    cost_savings_pct: float = 0.0

    # Demand comparison
    baseline_peak_demand: float = 0.0
    proposed_peak_demand: float = 0.0
    demand_reduction_kw: float = 0.0
    demand_reduction_pct: float = 0.0


@dataclass
class DataQualityReport:
    """Data quality assessment."""
    # Completeness
    has_hourly_data: bool = False
    hourly_record_count: int = 0
    expected_records: int = 8760
    missing_hours: int = 0

    # Reasonableness checks
    issues: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    @property
    def is_complete(self) -> bool:
        """Check if data is complete."""
        return self.hourly_record_count >= self.expected_records - 24  # Allow 1 day gap

    @property
    def has_issues(self) -> bool:
        """Check if there are any issues."""
        return len(self.issues) > 0


@dataclass
class ProjectCostAnalysis:
    """Complete cost analysis for a project."""
    project_name: str = ""
    project_path: str = ""
    analysis_date: str = ""

    # Discovery info
    discovery: Optional[DiscoveredOutputs] = None

    # Energy analysis
    proposed_energy: Optional[EnergyAnalysis] = None
    baseline_energy: Optional[EnergyAnalysis] = None

    # Tariff analysis (can have multiple)
    tariff_analyses: Dict[str, TariffAnalysis] = field(default_factory=dict)

    # Comparison (if baseline available)
    comparison: Optional[ComparisonAnalysis] = None

    # Data quality
    data_quality: Optional[DataQualityReport] = None

    def format_summary(self) -> str:
        """Format a human-readable summary."""
        lines = [
            "=" * 70,
            f"PROJECT COST ANALYSIS: {self.project_name}",
            "=" * 70,
            f"Analysis Date: {self.analysis_date}",
            f"Project Path: {self.project_path}",
            "",
        ]

        # Discovery summary
        if self.discovery:
            lines.extend([
                "DISCOVERED FILES:",
                f"  HourlyResults (Proposed): {self.discovery.hourly_results_proposed is not None}",
                f"  HourlyResults (Standard): {self.discovery.hourly_results_standard is not None}",
                f"  PV/Battery: {self.discovery.pv_battery is not None}",
                f"  CUAC: {self.discovery.cuac is not None}",
                "",
            ])

        # Data quality
        if self.data_quality:
            lines.extend([
                "DATA QUALITY:",
                f"  Hourly Records: {self.data_quality.hourly_record_count} / {self.data_quality.expected_records}",
                f"  Complete: {'Yes' if self.data_quality.is_complete else 'No'}",
            ])
            if self.data_quality.issues:
                lines.append("  Issues:")
                for issue in self.data_quality.issues:
                    lines.append(f"    - {issue}")
            if self.data_quality.warnings:
                lines.append("  Warnings:")
                for warning in self.data_quality.warnings:
                    lines.append(f"    - {warning}")
            lines.append("")

        # Proposed energy
        if self.proposed_energy:
            pe = self.proposed_energy
            lines.extend([
                "PROPOSED ENERGY:",
                f"  Total Consumption: {pe.total_consumption_kwh:,.0f} kWh",
                f"  PV Generation: {pe.pv_generation_kwh:,.0f} kWh",
                f"  Net Consumption: {pe.net_consumption_kwh:,.0f} kWh",
                f"  Peak Demand: {pe.peak_demand_kw:,.1f} kW",
                f"  Gas: {pe.total_gas_therms:,.1f} therms",
                "",
                f"  TOU Distribution:",
                f"    On-Peak: {pe.on_peak_pct:.1f}%",
                f"    Mid-Peak: {pe.mid_peak_pct:.1f}%",
                f"    Off-Peak: {pe.off_peak_pct:.1f}%",
                "",
            ])

        # Baseline energy
        if self.baseline_energy:
            be = self.baseline_energy
            lines.extend([
                "BASELINE ENERGY:",
                f"  Total Consumption: {be.total_consumption_kwh:,.0f} kWh",
                f"  Peak Demand: {be.peak_demand_kw:,.1f} kW",
                f"  Gas: {be.total_gas_therms:,.1f} therms",
                "",
            ])

        # Comparison
        if self.comparison:
            c = self.comparison
            lines.extend([
                "BASELINE vs PROPOSED:",
                f"  Consumption Savings: {c.consumption_savings_kwh:,.0f} kWh ({c.consumption_savings_pct:.1f}%)",
                f"  Demand Reduction: {c.demand_reduction_kw:,.1f} kW ({c.demand_reduction_pct:.1f}%)",
                f"  Annual Cost Savings: ${c.annual_cost_savings:,.0f} ({c.cost_savings_pct:.1f}%)",
                "",
            ])

        # Tariff analyses
        if self.tariff_analyses:
            lines.append("TARIFF ANALYSIS:")
            for tariff_name, ta in self.tariff_analyses.items():
                lines.extend([
                    f"  {tariff_name}:",
                    f"    Energy Cost: ${ta.energy_cost:,.0f}",
                    f"    Demand Cost: ${ta.demand_cost:,.0f}",
                    f"    Total Annual: ${ta.total_annual_cost:,.0f}",
                    f"    Effective Rate: ${ta.effective_rate_per_kwh:.4f}/kWh",
                    "",
                ])

        lines.append("=" * 70)
        return "\n".join(lines)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON export."""
        return {
            "project_name": self.project_name,
            "project_path": self.project_path,
            "analysis_date": self.analysis_date,
            "proposed_energy": {
                "total_consumption_kwh": self.proposed_energy.total_consumption_kwh if self.proposed_energy else 0,
                "pv_generation_kwh": self.proposed_energy.pv_generation_kwh if self.proposed_energy else 0,
                "net_consumption_kwh": self.proposed_energy.net_consumption_kwh if self.proposed_energy else 0,
                "peak_demand_kw": self.proposed_energy.peak_demand_kw if self.proposed_energy else 0,
                "total_gas_therms": self.proposed_energy.total_gas_therms if self.proposed_energy else 0,
            } if self.proposed_energy else None,
            "baseline_energy": {
                "total_consumption_kwh": self.baseline_energy.total_consumption_kwh if self.baseline_energy else 0,
                "peak_demand_kw": self.baseline_energy.peak_demand_kw if self.baseline_energy else 0,
            } if self.baseline_energy else None,
            "comparison": {
                "consumption_savings_kwh": self.comparison.consumption_savings_kwh,
                "consumption_savings_pct": self.comparison.consumption_savings_pct,
                "annual_cost_savings": self.comparison.annual_cost_savings,
                "cost_savings_pct": self.comparison.cost_savings_pct,
            } if self.comparison else None,
            "tariff_analyses": {
                name: {
                    "energy_cost": ta.energy_cost,
                    "demand_cost": ta.demand_cost,
                    "total_annual_cost": ta.total_annual_cost,
                    "effective_rate_per_kwh": ta.effective_rate_per_kwh,
                }
                for name, ta in self.tariff_analyses.items()
            },
            "data_quality": {
                "is_complete": self.data_quality.is_complete if self.data_quality else False,
                "issues": self.data_quality.issues if self.data_quality else [],
                "warnings": self.data_quality.warnings if self.data_quality else [],
            } if self.data_quality else None,
        }


def analyze_energy(
    simulation: SimulationOutput,
    tariff: Optional[TouTariff] = None
) -> EnergyAnalysis:
    """Analyze energy consumption from simulation output."""
    analysis = EnergyAnalysis()

    # Annual totals from summary
    if simulation.annual:
        analysis.total_consumption_kwh = simulation.annual.total_elec_kwh
        analysis.total_gas_therms = simulation.annual.total_gas_therm
        analysis.pv_generation_kwh = simulation.annual.pv_generation_kwh
        analysis.net_consumption_kwh = simulation.annual.net_elec_kwh
        analysis.peak_demand_kw = simulation.annual.peak_demand_kw
        analysis.peak_demand_month = simulation.annual.peak_demand_month

    # Hourly analysis
    if simulation.hourly:
        hourly_values = [h.elec_total_kwh for h in simulation.hourly]
        if hourly_values:
            analysis.hourly_min_kwh = min(hourly_values)
            analysis.hourly_max_kwh = max(hourly_values)
            analysis.hourly_avg_kwh = sum(hourly_values) / len(hourly_values)

        # Calculate TOU distribution if tariff provided
        if tariff and tariff.schedule:
            from datetime import date
            from .tariffs import TouPeriod

            on_peak_kwh = 0.0
            mid_peak_kwh = 0.0
            off_peak_kwh = 0.0
            total_kwh = 0.0

            for h in simulation.hourly:
                # Determine if weekend from date
                try:
                    d = date(2024, h.month, h.day)
                    is_weekend = d.weekday() >= 5  # Saturday=5, Sunday=6
                except ValueError:
                    is_weekend = False

                # get_period(month, hour, is_weekend)
                period = tariff.schedule.get_period(h.month, h.hour, is_weekend)
                kwh = h.elec_total_kwh

                if period == TouPeriod.ON_PEAK:
                    on_peak_kwh += kwh
                elif period == TouPeriod.MID_PEAK:
                    mid_peak_kwh += kwh
                else:
                    off_peak_kwh += kwh
                total_kwh += kwh

            if total_kwh > 0:
                analysis.on_peak_pct = (on_peak_kwh / total_kwh) * 100
                analysis.mid_peak_pct = (mid_peak_kwh / total_kwh) * 100
                analysis.off_peak_pct = (off_peak_kwh / total_kwh) * 100

        # Monthly breakdown
        monthly_consumption = [0.0] * 12
        monthly_peak = [0.0] * 12
        for h in simulation.hourly:
            month_idx = h.month - 1
            monthly_consumption[month_idx] += h.elec_total_kwh
            if h.elec_total_kwh > monthly_peak[month_idx]:
                monthly_peak[month_idx] = h.elec_total_kwh

        analysis.monthly_consumption = monthly_consumption
        analysis.monthly_peak_demand = monthly_peak

    return analysis


def analyze_tariff(
    simulation: SimulationOutput,
    tariff: TouTariff
) -> TariffAnalysis:
    """Analyze costs under a specific tariff."""
    analysis = TariffAnalysis()
    analysis.tariff_name = tariff.name
    analysis.tariff_utility = tariff.utility

    if simulation.hourly:
        hourly_usage = hourly_energy_to_usage(simulation.hourly)
        tou_breakdown = calculate_tou_costs(hourly_usage, tariff)
        analysis.tou_breakdown = tou_breakdown

        analysis.energy_cost = tou_breakdown.total_energy_cost
        analysis.demand_cost = tou_breakdown.total_demand_cost
        analysis.fixed_charges = (
            tariff.monthly_customer_charge * 12 +
            tariff.monthly_meter_charge * 12
        )
        analysis.total_annual_cost = tou_breakdown.total_cost + analysis.fixed_charges

        # Effective rates
        if simulation.annual.total_elec_kwh > 0:
            analysis.effective_rate_per_kwh = (
                analysis.total_annual_cost / simulation.annual.total_elec_kwh
            )
            analysis.blended_energy_rate = (
                analysis.energy_cost / simulation.annual.total_elec_kwh
            )

    return analysis


def check_data_quality(
    simulation: SimulationOutput,
    discovery: Optional[DiscoveredOutputs] = None
) -> DataQualityReport:
    """Check data quality and reasonableness."""
    report = DataQualityReport()

    # Hourly data completeness
    report.has_hourly_data = len(simulation.hourly) > 0
    report.hourly_record_count = len(simulation.hourly)
    report.missing_hours = report.expected_records - report.hourly_record_count

    if report.missing_hours > 0:
        report.warnings.append(
            f"Missing {report.missing_hours} hourly records "
            f"(expected {report.expected_records})"
        )

    # Reasonableness checks
    if simulation.annual:
        annual = simulation.annual

        # Check for zero consumption
        if annual.total_elec_kwh <= 0:
            report.issues.append("Zero or negative total electricity consumption")

        # Check for unreasonably high consumption (> 10 MW average)
        avg_kw = annual.total_elec_kwh / 8760 if annual.total_elec_kwh > 0 else 0
        if avg_kw > 10000:
            report.warnings.append(
                f"Very high average load: {avg_kw:,.0f} kW - verify data"
            )

        # Check PV vs consumption ratio
        if annual.pv_generation_kwh > annual.total_elec_kwh * 2:
            report.warnings.append(
                "PV generation exceeds 2x consumption - unusual for non-utility projects"
            )

        # Check for negative net consumption (large export)
        if annual.net_elec_kwh < 0:
            report.warnings.append(
                f"Net consumption is negative ({annual.net_elec_kwh:,.0f} kWh) - "
                "building is net exporter"
            )

    return report


def analyze_project_costs(
    project_path: Path,
    tariff_ids: Optional[List[str]] = None
) -> ProjectCostAnalysis:
    """
    Perform complete cost analysis on a project.

    Args:
        project_path: Path to project run folder
        tariff_ids: List of tariff IDs to analyze (default: ["PG&E B-20"])

    Returns:
        ProjectCostAnalysis with complete results
    """
    if tariff_ids is None:
        tariff_ids = ["PG&E B-20"]

    project_path = Path(project_path)
    analysis = ProjectCostAnalysis(
        project_name=project_path.parent.name if project_path.name.endswith("- run") else project_path.name,
        project_path=str(project_path),
        analysis_date=datetime.now().isoformat(),
    )

    # Discover files
    discovery = discover_simulation_outputs(project_path)
    analysis.discovery = discovery

    if not discovery.is_complete:
        return analysis

    # Parse simulation
    proposed_path = discovery.hourly_results_proposed.path
    proposed = parse_hourly_results(str(proposed_path))

    # Check data quality
    analysis.data_quality = check_data_quality(proposed, discovery)

    # Get primary tariff for TOU analysis
    primary_tariff = get_tariff_by_name(tariff_ids[0])

    # Analyze proposed energy
    analysis.proposed_energy = analyze_energy(proposed, primary_tariff)

    # Analyze tariffs
    for tariff_id in tariff_ids:
        tariff = get_tariff_by_name(tariff_id)
        if tariff:
            analysis.tariff_analyses[tariff_id] = analyze_tariff(proposed, tariff)

    # Parse and analyze baseline if available
    if discovery.hourly_results_standard:
        baseline_path = discovery.hourly_results_standard.path
        baseline = parse_hourly_results(str(baseline_path))
        analysis.baseline_energy = analyze_energy(baseline, primary_tariff)

        # Comparison analysis
        if analysis.proposed_energy and analysis.baseline_energy:
            pe = analysis.proposed_energy
            be = analysis.baseline_energy

            comparison = ComparisonAnalysis()
            comparison.baseline_consumption_kwh = be.total_consumption_kwh
            comparison.proposed_consumption_kwh = pe.total_consumption_kwh
            comparison.consumption_savings_kwh = be.total_consumption_kwh - pe.total_consumption_kwh

            if be.total_consumption_kwh > 0:
                comparison.consumption_savings_pct = (
                    comparison.consumption_savings_kwh / be.total_consumption_kwh * 100
                )

            comparison.baseline_peak_demand = be.peak_demand_kw
            comparison.proposed_peak_demand = pe.peak_demand_kw
            comparison.demand_reduction_kw = be.peak_demand_kw - pe.peak_demand_kw

            if be.peak_demand_kw > 0:
                comparison.demand_reduction_pct = (
                    comparison.demand_reduction_kw / be.peak_demand_kw * 100
                )

            # Cost comparison using primary tariff
            if tariff_ids[0] in analysis.tariff_analyses:
                proposed_cost = analysis.tariff_analyses[tariff_ids[0]].total_annual_cost

                # Need to calculate baseline cost
                baseline_tariff_analysis = analyze_tariff(baseline, primary_tariff)
                baseline_cost = baseline_tariff_analysis.total_annual_cost

                comparison.baseline_annual_cost = baseline_cost
                comparison.proposed_annual_cost = proposed_cost
                comparison.annual_cost_savings = baseline_cost - proposed_cost

                if baseline_cost > 0:
                    comparison.cost_savings_pct = (
                        comparison.annual_cost_savings / baseline_cost * 100
                    )

            analysis.comparison = comparison

    return analysis


def batch_analyze_projects(
    project_paths: List[Path],
    tariff_ids: Optional[List[str]] = None
) -> List[ProjectCostAnalysis]:
    """Analyze multiple projects."""
    results = []
    for path in project_paths:
        try:
            analysis = analyze_project_costs(path, tariff_ids)
            results.append(analysis)
        except Exception as e:
            # Create error placeholder
            analysis = ProjectCostAnalysis(
                project_name=str(path),
                project_path=str(path),
                analysis_date=datetime.now().isoformat(),
            )
            if analysis.data_quality is None:
                analysis.data_quality = DataQualityReport()
            analysis.data_quality.issues.append(f"Analysis failed: {e}")
            results.append(analysis)

    return results


def format_comparison_table(analyses: List[ProjectCostAnalysis]) -> str:
    """Format a comparison table of multiple projects."""
    lines = [
        "=" * 100,
        "PROJECT COMPARISON TABLE",
        "=" * 100,
        f"{'Project':<30} {'Consumption':>12} {'Peak kW':>10} {'Annual Cost':>12} {'Savings':>12} {'Savings %':>10}",
        "-" * 100,
    ]

    for a in analyses:
        if a.comparison:
            c = a.comparison
            lines.append(
                f"{a.project_name[:30]:<30} "
                f"{c.proposed_consumption_kwh:>12,.0f} "
                f"{a.proposed_energy.peak_demand_kw if a.proposed_energy else 0:>10,.1f} "
                f"${c.proposed_annual_cost:>11,.0f} "
                f"${c.annual_cost_savings:>11,.0f} "
                f"{c.cost_savings_pct:>9.1f}%"
            )
        elif a.proposed_energy and a.tariff_analyses:
            pe = a.proposed_energy
            cost = list(a.tariff_analyses.values())[0].total_annual_cost if a.tariff_analyses else 0
            lines.append(
                f"{a.project_name[:30]:<30} "
                f"{pe.total_consumption_kwh:>12,.0f} "
                f"{pe.peak_demand_kw:>10,.1f} "
                f"${cost:>11,.0f} "
                f"{'N/A':>12} "
                f"{'N/A':>10}"
            )
        else:
            lines.append(f"{a.project_name[:30]:<30} {'(incomplete data)':>60}")

    lines.append("=" * 100)
    return "\n".join(lines)
