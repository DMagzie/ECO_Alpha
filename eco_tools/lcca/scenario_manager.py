"""
Scenario Manager for LCCA Analysis.

Provides a higher-level interface for managing multiple scenarios and
running flexible comparisons. Supports:
- Named scenario registration and retrieval
- Comparison of any two scenarios (not just baseline vs proposed)
- Multi-tariff comparison (same building against different utility rates)
- Scenario cloning and modification
- Comparison matrix generation

Example:
    >>> from eco_tools.lcca import ScenarioManager, create_sce_tou_gs3
    >>> from eco_tools.lcca.parsers.hourly_results import parse_hourly_results
    >>>
    >>> manager = ScenarioManager("Gibraltar Office Building")
    >>> manager.load_from_cbecc(
    ...     baseline_path="Gibraltar-ab-HourlyResults.csv",
    ...     proposed_path="Gibraltar-ap-HourlyResults.csv",
    ...     tariff=create_sce_tou_gs3(),
    ... )
    >>>
    >>> # Compare any two scenarios
    >>> results = manager.compare("baseline", "proposed_with_pv")
    >>>
    >>> # Compare same building against different utilities
    >>> tariff_comparison = manager.compare_tariffs("proposed_with_pv", tariffs)
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Union, Tuple
from pathlib import Path
import copy

from .model import (
    TouLccaScenario,
    SimulationOutput,
    ScenarioAssumptions,
    Incentive,
    HourlyEnergy,
)
from .tariffs import TouTariff, TouCostBreakdown
from .calculators import (
    TouLccaResults,
    run_tou_lcca,
    format_tou_lcca_summary,
)


@dataclass
class ScenarioComparison:
    """Results from comparing two scenarios."""
    scenario_a: str
    scenario_b: str
    results: TouLccaResults

    @property
    def summary(self) -> str:
        """Generate summary text."""
        return format_tou_lcca_summary(self.results)


@dataclass
class TariffComparison:
    """Results from comparing a scenario against multiple tariffs."""
    scenario_name: str
    tariffs: List[str]
    breakdowns: Dict[str, TouCostBreakdown]
    annual_costs: Dict[str, float]

    def get_cheapest(self) -> Tuple[str, float]:
        """Get the tariff with lowest annual cost."""
        cheapest = min(self.annual_costs.items(), key=lambda x: x[1])
        return cheapest

    def get_most_expensive(self) -> Tuple[str, float]:
        """Get the tariff with highest annual cost."""
        most_expensive = max(self.annual_costs.items(), key=lambda x: x[1])
        return most_expensive

    def get_cost_range(self) -> Tuple[float, float]:
        """Get the range of annual costs (min, max)."""
        costs = list(self.annual_costs.values())
        return (min(costs), max(costs))


@dataclass
class ComparisonMatrix:
    """Matrix of pairwise comparisons between scenarios."""
    scenarios: List[str]
    comparisons: Dict[Tuple[str, str], TouLccaResults]

    def get_comparison(self, scenario_a: str, scenario_b: str) -> Optional[TouLccaResults]:
        """Get comparison results for a pair of scenarios."""
        return self.comparisons.get((scenario_a, scenario_b))

    def to_summary_dict(self) -> Dict[str, Dict[str, float]]:
        """Convert to nested dict of NPV values for easy viewing."""
        result = {}
        for (a, b), comparison in self.comparisons.items():
            if a not in result:
                result[a] = {}
            result[a][b] = comparison.npv
        return result


class ScenarioManager:
    """
    Manages multiple LCCA scenarios for a project.

    Provides a unified interface for:
    - Registering and retrieving named scenarios
    - Comparing any two scenarios
    - Running multi-tariff comparisons
    - Cloning and modifying scenarios

    Example:
        >>> manager = ScenarioManager("My Building")
        >>>
        >>> # Add scenarios
        >>> manager.add_scenario("baseline", baseline_scenario)
        >>> manager.add_scenario("proposed", proposed_scenario)
        >>>
        >>> # Compare
        >>> results = manager.compare("baseline", "proposed")
        >>> print(f"NPV: ${results.results.npv:,.0f}")
    """

    def __init__(
        self,
        project_name: str,
        default_assumptions: Optional[ScenarioAssumptions] = None,
    ):
        """
        Initialize ScenarioManager.

        Args:
            project_name: Name of the project
            default_assumptions: Default financial assumptions for new scenarios
        """
        self.project_name = project_name
        self.default_assumptions = default_assumptions or ScenarioAssumptions()
        self._scenarios: Dict[str, TouLccaScenario] = {}
        self._simulation_outputs: Dict[str, SimulationOutput] = {}
        self._comparison_cache: Dict[Tuple[str, str], TouLccaResults] = {}

    @property
    def scenario_names(self) -> List[str]:
        """Get list of registered scenario names."""
        return list(self._scenarios.keys())

    @property
    def scenario_count(self) -> int:
        """Get number of registered scenarios."""
        return len(self._scenarios)

    def add_scenario(
        self,
        name: str,
        scenario: TouLccaScenario,
        overwrite: bool = False,
    ) -> None:
        """
        Register a named scenario.

        Args:
            name: Unique name for the scenario
            scenario: TouLccaScenario to register
            overwrite: If True, overwrite existing scenario with same name

        Raises:
            ValueError: If name already exists and overwrite=False
        """
        if name in self._scenarios and not overwrite:
            raise ValueError(f"Scenario '{name}' already exists. Use overwrite=True to replace.")

        self._scenarios[name] = scenario
        # Clear comparison cache for this scenario
        self._clear_cache_for_scenario(name)

    def get_scenario(self, name: str) -> TouLccaScenario:
        """
        Get a scenario by name.

        Args:
            name: Scenario name

        Returns:
            The requested TouLccaScenario

        Raises:
            KeyError: If scenario not found
        """
        if name not in self._scenarios:
            raise KeyError(f"Scenario '{name}' not found. Available: {self.scenario_names}")
        return self._scenarios[name]

    def remove_scenario(self, name: str) -> None:
        """
        Remove a scenario.

        Args:
            name: Scenario name to remove
        """
        if name in self._scenarios:
            del self._scenarios[name]
            self._clear_cache_for_scenario(name)

    def clone_scenario(
        self,
        source_name: str,
        new_name: str,
        **modifications,
    ) -> TouLccaScenario:
        """
        Clone a scenario with optional modifications.

        Args:
            source_name: Name of scenario to clone
            new_name: Name for the new scenario
            **modifications: Attributes to modify on the clone

        Returns:
            The cloned and modified scenario

        Example:
            >>> # Clone proposed but without PV
            >>> manager.clone_scenario(
            ...     "proposed_with_pv",
            ...     "proposed_no_pv",
            ...     use_net_electricity=False,
            ...     capex_upfront=0,
            ... )
        """
        source = self.get_scenario(source_name)

        # Deep copy the scenario
        cloned = TouLccaScenario(
            name=modifications.get('name', new_name),
            hourly_data=source.hourly_data,  # Share hourly data (immutable)
            tou_tariff=modifications.get('tou_tariff', source.tou_tariff),
            capex_upfront=modifications.get('capex_upfront', source.capex_upfront),
            opex_annual_delta=modifications.get('opex_annual_delta', source.opex_annual_delta),
            maintenance_annual_delta=modifications.get('maintenance_annual_delta', source.maintenance_annual_delta),
            incentives=modifications.get('incentives', list(source.incentives)),
            assumptions=modifications.get('assumptions', source.assumptions),
            annual_gas_therms=modifications.get('annual_gas_therms', source.annual_gas_therms),
            use_net_electricity=modifications.get('use_net_electricity', source.use_net_electricity),
            building_area_sf=modifications.get('building_area_sf', source.building_area_sf),
            building_type=modifications.get('building_type', source.building_type),
        )

        self.add_scenario(new_name, cloned)
        return cloned

    def load_from_cbecc(
        self,
        baseline_path: Union[str, Path],
        proposed_path: Union[str, Path],
        tariff: TouTariff,
        pv_capex: float = 0.0,
        other_capex: float = 0.0,
        assumptions: Optional[ScenarioAssumptions] = None,
        incentives: Optional[List[Incentive]] = None,
        create_variants: bool = True,
    ) -> Dict[str, TouLccaScenario]:
        """
        Load scenarios from CBECC HourlyResults files.

        Creates standard scenarios:
        - "baseline": Code minimum building
        - "proposed": As-modeled building (with PV if present)
        - "proposed_no_pv": Proposed without PV (if create_variants=True)
        - "proposed_gross": Proposed using gross electricity (if create_variants=True)

        Args:
            baseline_path: Path to baseline (-ab-) HourlyResults CSV
            proposed_path: Path to proposed (-ap-) HourlyResults CSV
            tariff: TOU tariff to use
            pv_capex: Capital cost for PV system
            other_capex: Other capital costs (envelope, HVAC, etc.)
            assumptions: Financial assumptions
            incentives: List of incentives
            create_variants: If True, create additional scenario variants

        Returns:
            Dict of created scenarios
        """
        from .parsers.hourly_results import parse_hourly_results

        assumptions = assumptions or self.default_assumptions
        incentives = incentives or []

        # Parse files
        baseline_output = parse_hourly_results(Path(baseline_path))
        proposed_output = parse_hourly_results(Path(proposed_path))

        # Store outputs for reference
        self._simulation_outputs["baseline"] = baseline_output
        self._simulation_outputs["proposed"] = proposed_output

        # Create baseline scenario
        baseline = TouLccaScenario.from_simulation_output(
            name="Baseline (Code Minimum)",
            output=baseline_output,
            tou_tariff=tariff,
            capex_upfront=0,
            use_net_electricity=True,
            assumptions=assumptions,
        )
        self.add_scenario("baseline", baseline)

        # Create proposed scenario (with PV)
        total_capex = pv_capex + other_capex
        proposed = TouLccaScenario.from_simulation_output(
            name="Proposed",
            output=proposed_output,
            tou_tariff=tariff,
            capex_upfront=total_capex,
            use_net_electricity=True,
            assumptions=assumptions,
            incentives=incentives,
        )
        self.add_scenario("proposed", proposed)

        created = {"baseline": baseline, "proposed": proposed}

        # Create variants if requested
        if create_variants:
            # Proposed without PV offset (gross consumption)
            proposed_no_pv = TouLccaScenario.from_simulation_output(
                name="Proposed (No PV)",
                output=proposed_output,
                tou_tariff=tariff,
                capex_upfront=other_capex,  # Exclude PV cost
                use_net_electricity=False,  # Use gross
                assumptions=assumptions,
            )
            self.add_scenario("proposed_no_pv", proposed_no_pv)
            created["proposed_no_pv"] = proposed_no_pv

            # If there's PV, create PV-only comparison scenario
            if pv_capex > 0:
                pv_only = TouLccaScenario.from_simulation_output(
                    name="Proposed (PV Investment)",
                    output=proposed_output,
                    tou_tariff=tariff,
                    capex_upfront=pv_capex,
                    use_net_electricity=True,
                    assumptions=assumptions,
                    incentives=incentives,
                )
                self.add_scenario("proposed_pv_only", pv_only)
                created["proposed_pv_only"] = pv_only

        return created

    def compare(
        self,
        scenario_a: str,
        scenario_b: str,
        use_cache: bool = True,
    ) -> ScenarioComparison:
        """
        Compare two scenarios.

        The comparison calculates the value of going from scenario_a to scenario_b.
        A positive NPV means scenario_b is more cost-effective than scenario_a.

        Args:
            scenario_a: Name of reference scenario (typically baseline)
            scenario_b: Name of alternative scenario (typically proposed)
            use_cache: If True, return cached results if available

        Returns:
            ScenarioComparison with full LCCA results
        """
        cache_key = (scenario_a, scenario_b)

        if use_cache and cache_key in self._comparison_cache:
            results = self._comparison_cache[cache_key]
        else:
            a = self.get_scenario(scenario_a)
            b = self.get_scenario(scenario_b)
            results = run_tou_lcca(a, b)
            self._comparison_cache[cache_key] = results

        return ScenarioComparison(
            scenario_a=scenario_a,
            scenario_b=scenario_b,
            results=results,
        )

    def compare_all_pairs(
        self,
        scenarios: Optional[List[str]] = None,
    ) -> ComparisonMatrix:
        """
        Generate comparison matrix for multiple scenarios.

        Args:
            scenarios: List of scenario names to compare (default: all)

        Returns:
            ComparisonMatrix with all pairwise comparisons
        """
        if scenarios is None:
            scenarios = self.scenario_names

        comparisons = {}
        for i, a in enumerate(scenarios):
            for b in scenarios[i+1:]:
                result = self.compare(a, b)
                comparisons[(a, b)] = result.results

        return ComparisonMatrix(scenarios=scenarios, comparisons=comparisons)

    def compare_tariffs(
        self,
        scenario_name: str,
        tariffs: List[TouTariff],
    ) -> TariffComparison:
        """
        Compare a scenario against multiple utility tariffs.

        Useful for evaluating which utility rate structure is most favorable.

        Args:
            scenario_name: Name of scenario to analyze
            tariffs: List of TOU tariffs to compare

        Returns:
            TariffComparison with costs under each tariff
        """
        scenario = self.get_scenario(scenario_name)

        tariff_names = []
        breakdowns = {}
        annual_costs = {}

        for tariff in tariffs:
            tariff_key = f"{tariff.utility} {tariff.name}"
            tariff_names.append(tariff_key)

            # Create temporary scenario with this tariff
            temp_scenario = TouLccaScenario(
                name=scenario.name,
                hourly_data=scenario.hourly_data,
                tou_tariff=tariff,
                annual_gas_therms=scenario.annual_gas_therms,
                use_net_electricity=scenario.use_net_electricity,
            )

            breakdown = temp_scenario.calculate_tou_breakdown()
            annual_cost = temp_scenario.calculate_annual_cost()

            breakdowns[tariff_key] = breakdown
            annual_costs[tariff_key] = annual_cost

        return TariffComparison(
            scenario_name=scenario_name,
            tariffs=tariff_names,
            breakdowns=breakdowns,
            annual_costs=annual_costs,
        )

    def get_annual_costs(self) -> Dict[str, float]:
        """
        Get annual costs for all scenarios.

        Returns:
            Dict mapping scenario name to annual cost
        """
        return {
            name: scenario.calculate_annual_cost()
            for name, scenario in self._scenarios.items()
        }

    def get_scenario_summary(self, name: str) -> str:
        """
        Get a text summary of a scenario.

        Args:
            name: Scenario name

        Returns:
            Formatted summary text
        """
        scenario = self.get_scenario(name)
        breakdown = scenario.calculate_tou_breakdown()
        annual_cost = scenario.calculate_annual_cost()

        lines = [
            f"Scenario: {scenario.name}",
            "-" * 50,
            f"Building Area:     {scenario.building_area_sf:,.0f} SF",
            f"Building Type:     {scenario.building_type}",
            f"Tariff:            {scenario.tou_tariff.name}",
            "",
            "Energy Consumption",
            f"  Electricity:     {scenario.get_annual_kwh():,.0f} kWh",
            f"  PV Generation:   {scenario.get_pv_generation_kwh():,.0f} kWh",
            f"  Natural Gas:     {scenario.annual_gas_therms:,.0f} therms",
            "",
            "Annual Costs",
            f"  Energy Cost:     ${breakdown.total_energy_cost:,.0f}",
            f"  Demand Cost:     ${breakdown.total_demand_cost:,.0f}",
            f"  Gas Cost:        ${scenario.annual_gas_therms * scenario.tou_tariff.gas_rate:,.0f}",
            f"  Total Annual:    ${annual_cost:,.0f}",
            "",
            "Investment",
            f"  Capital Cost:    ${scenario.capex_upfront:,.0f}",
            f"  Incentives:      ${sum(i.amount for i in scenario.incentives):,.0f}",
        ]

        return "\n".join(lines)

    def format_comparison_table(
        self,
        scenarios: Optional[List[str]] = None,
    ) -> str:
        """
        Generate a formatted comparison table.

        Args:
            scenarios: Scenarios to include (default: all)

        Returns:
            Formatted text table
        """
        if scenarios is None:
            scenarios = self.scenario_names

        # Get data for each scenario
        data = []
        for name in scenarios:
            scenario = self.get_scenario(name)
            data.append({
                'name': name,
                'kwh': scenario.get_annual_kwh(),
                'pv': scenario.get_pv_generation_kwh(),
                'gas': scenario.annual_gas_therms,
                'cost': scenario.calculate_annual_cost(),
                'capex': scenario.capex_upfront,
            })

        # Format table
        lines = [
            "=" * 90,
            f"SCENARIO COMPARISON - {self.project_name}",
            "=" * 90,
            "",
            f"{'Scenario':<25} {'kWh':>12} {'PV kWh':>12} {'Gas thm':>10} {'Annual $':>12} {'CapEx $':>12}",
            "-" * 90,
        ]

        for d in data:
            lines.append(
                f"{d['name']:<25} {d['kwh']:>12,.0f} {d['pv']:>12,.0f} {d['gas']:>10,.0f} "
                f"{d['cost']:>12,.0f} {d['capex']:>12,.0f}"
            )

        lines.append("=" * 90)

        return "\n".join(lines)

    def _clear_cache_for_scenario(self, name: str) -> None:
        """Clear cached comparisons involving a scenario."""
        keys_to_remove = [
            key for key in self._comparison_cache
            if name in key
        ]
        for key in keys_to_remove:
            del self._comparison_cache[key]


def format_tariff_comparison(comparison: TariffComparison) -> str:
    """
    Format tariff comparison results as text.

    Args:
        comparison: TariffComparison from compare_tariffs()

    Returns:
        Formatted text report
    """
    lines = [
        "=" * 70,
        f"TARIFF COMPARISON - {comparison.scenario_name}",
        "=" * 70,
        "",
        f"{'Utility / Tariff':<35} {'Annual Cost':>15} {'vs Cheapest':>15}",
        "-" * 70,
    ]

    cheapest_name, cheapest_cost = comparison.get_cheapest()

    # Sort by cost
    sorted_costs = sorted(comparison.annual_costs.items(), key=lambda x: x[1])

    for tariff_name, cost in sorted_costs:
        diff = cost - cheapest_cost
        diff_str = f"+${diff:,.0f}" if diff > 0 else "-"
        lines.append(f"{tariff_name:<35} ${cost:>14,.0f} {diff_str:>15}")

    lines.extend([
        "-" * 70,
        f"Cost Range: ${comparison.get_cost_range()[0]:,.0f} - ${comparison.get_cost_range()[1]:,.0f}",
        "=" * 70,
    ])

    return "\n".join(lines)
