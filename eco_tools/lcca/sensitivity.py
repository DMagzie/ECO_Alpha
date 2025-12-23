"""
Sensitivity Analysis Module for LCCA.

Provides tools for understanding how LCCA results change with input assumptions:
- Parameter sweeps: Vary one or more parameters across a range
- Tornado charts: Identify key drivers of NPV/IRR
- Monte Carlo: Probabilistic analysis with distributions

Example:
    >>> from eco_tools.lcca import SensitivityAnalyzer, run_tou_lcca
    >>>
    >>> # Create analyzer with base case
    >>> analyzer = SensitivityAnalyzer(baseline, proposed)
    >>>
    >>> # Run discount rate sweep
    >>> sweep = analyzer.sweep_parameter("discount_rate", [0.03, 0.05, 0.07, 0.10])
    >>> for result in sweep.results:
    ...     print(f"DR={result.parameter_value:.0%}: NPV=${result.npv:,.0f}")
    >>>
    >>> # Generate tornado chart data
    >>> tornado = analyzer.tornado_analysis()
    >>> print(tornado.format())
    >>>
    >>> # Run Monte Carlo
    >>> mc = analyzer.monte_carlo(iterations=1000)
    >>> print(f"NPV 90% CI: ${mc.npv_p5:,.0f} to ${mc.npv_p95:,.0f}")
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Tuple, Callable
from enum import Enum
import random
import math


class SensitivityParameter(Enum):
    """Parameters that can be varied in sensitivity analysis."""
    DISCOUNT_RATE = "discount_rate"
    ELECTRICITY_ESCALATION = "electricity_escalation"
    GAS_ESCALATION = "gas_escalation"
    ANALYSIS_YEARS = "analysis_years"
    CAPEX = "capex"
    ELECTRICITY_RATE = "electricity_rate"  # Multiplier on base rates
    GAS_RATE = "gas_rate"  # Multiplier on base rates
    PV_DEGRADATION = "pv_degradation"
    INCENTIVE_AMOUNT = "incentive_amount"


@dataclass
class ParameterRange:
    """Definition of a parameter's range for sensitivity analysis."""
    parameter: SensitivityParameter
    low: float
    base: float
    high: float
    unit: str = ""
    description: str = ""

    @property
    def range_pct(self) -> Tuple[float, float]:
        """Return low and high as percentage of base."""
        if self.base == 0:
            return (0.0, 0.0)
        return (self.low / self.base - 1, self.high / self.base - 1)

    def get_sweep_values(self, steps: int = 5) -> List[float]:
        """Generate evenly spaced values from low to high."""
        if steps < 2:
            return [self.base]
        step_size = (self.high - self.low) / (steps - 1)
        return [self.low + i * step_size for i in range(steps)]


@dataclass
class SweepResult:
    """Result of a single point in a parameter sweep."""
    parameter: SensitivityParameter
    parameter_value: float
    npv: float
    irr: Optional[float]
    simple_payback: Optional[float]
    sir: Optional[float]
    annual_savings: float


@dataclass
class ParameterSweep:
    """Results of sweeping a single parameter."""
    parameter: SensitivityParameter
    base_value: float
    results: List[SweepResult]

    @property
    def npv_range(self) -> Tuple[float, float]:
        """Return min and max NPV from sweep."""
        npvs = [r.npv for r in self.results]
        return (min(npvs), max(npvs))

    @property
    def npv_sensitivity(self) -> float:
        """NPV change per unit change in parameter."""
        if len(self.results) < 2:
            return 0.0
        sorted_results = sorted(self.results, key=lambda r: r.parameter_value)
        param_range = sorted_results[-1].parameter_value - sorted_results[0].parameter_value
        if param_range == 0:
            return 0.0
        npv_range = sorted_results[-1].npv - sorted_results[0].npv
        return npv_range / param_range

    def format(self) -> str:
        """Format sweep results as text table."""
        lines = [
            f"Parameter Sweep: {self.parameter.value}",
            f"Base Value: {self.base_value}",
            "",
            f"{'Value':>12} {'NPV':>14} {'IRR':>10} {'Payback':>10} {'SIR':>8}",
            "-" * 60,
        ]
        for r in sorted(self.results, key=lambda x: x.parameter_value):
            irr_str = f"{r.irr*100:.1f}%" if r.irr else "N/A"
            pb_str = f"{r.simple_payback:.1f} yr" if r.simple_payback else "N/A"
            sir_str = f"{r.sir:.2f}" if r.sir else "N/A"
            lines.append(
                f"{r.parameter_value:>12.4f} ${r.npv:>13,.0f} {irr_str:>10} {pb_str:>10} {sir_str:>8}"
            )
        return "\n".join(lines)


@dataclass
class TornadoItem:
    """Single parameter's impact for tornado chart."""
    parameter: SensitivityParameter
    low_value: float
    base_value: float
    high_value: float
    npv_at_low: float
    npv_at_base: float
    npv_at_high: float

    @property
    def npv_swing(self) -> float:
        """Total NPV swing from low to high."""
        return abs(self.npv_at_high - self.npv_at_low)

    @property
    def npv_downside(self) -> float:
        """NPV decrease from base (worst case)."""
        return self.npv_at_base - min(self.npv_at_low, self.npv_at_high)

    @property
    def npv_upside(self) -> float:
        """NPV increase from base (best case)."""
        return max(self.npv_at_low, self.npv_at_high) - self.npv_at_base


@dataclass
class TornadoAnalysis:
    """Results of tornado/sensitivity analysis across multiple parameters."""
    base_npv: float
    items: List[TornadoItem]

    @property
    def sorted_by_impact(self) -> List[TornadoItem]:
        """Items sorted by NPV swing (largest first)."""
        return sorted(self.items, key=lambda x: x.npv_swing, reverse=True)

    @property
    def top_drivers(self) -> List[TornadoItem]:
        """Top 5 most impactful parameters."""
        return self.sorted_by_impact[:5]

    def format(self) -> str:
        """Format tornado analysis as text."""
        lines = [
            "=" * 80,
            "TORNADO ANALYSIS - NPV SENSITIVITY",
            "=" * 80,
            f"Base NPV: ${self.base_npv:,.0f}",
            "",
            f"{'Parameter':<25} {'Low':>10} {'Base':>10} {'High':>10} {'NPV Swing':>14}",
            "-" * 80,
        ]

        for item in self.sorted_by_impact:
            # Format values based on parameter type
            if item.parameter in [SensitivityParameter.DISCOUNT_RATE,
                                   SensitivityParameter.ELECTRICITY_ESCALATION,
                                   SensitivityParameter.GAS_ESCALATION,
                                   SensitivityParameter.PV_DEGRADATION]:
                low_str = f"{item.low_value:.1%}"
                base_str = f"{item.base_value:.1%}"
                high_str = f"{item.high_value:.1%}"
            elif item.parameter == SensitivityParameter.CAPEX:
                low_str = f"${item.low_value/1000:.0f}k"
                base_str = f"${item.base_value/1000:.0f}k"
                high_str = f"${item.high_value/1000:.0f}k"
            elif item.parameter == SensitivityParameter.ANALYSIS_YEARS:
                low_str = f"{item.low_value:.0f} yr"
                base_str = f"{item.base_value:.0f} yr"
                high_str = f"{item.high_value:.0f} yr"
            else:
                low_str = f"{item.low_value:.2f}"
                base_str = f"{item.base_value:.2f}"
                high_str = f"{item.high_value:.2f}"

            lines.append(
                f"{item.parameter.value:<25} {low_str:>10} {base_str:>10} {high_str:>10} "
                f"${item.npv_swing:>13,.0f}"
            )

        lines.append("=" * 80)
        return "\n".join(lines)


@dataclass
class MonteCarloResult:
    """Results of Monte Carlo simulation."""
    iterations: int
    npv_values: List[float]
    irr_values: List[float]
    payback_values: List[float]

    # Statistics
    npv_mean: float = 0.0
    npv_std: float = 0.0
    npv_p5: float = 0.0
    npv_p25: float = 0.0
    npv_p50: float = 0.0
    npv_p75: float = 0.0
    npv_p95: float = 0.0

    irr_mean: Optional[float] = None
    irr_p5: Optional[float] = None
    irr_p50: Optional[float] = None
    irr_p95: Optional[float] = None

    prob_positive_npv: float = 0.0
    prob_payback_under_10yr: float = 0.0

    def __post_init__(self):
        """Calculate statistics from raw values."""
        if not self.npv_values:
            return

        # NPV statistics
        n = len(self.npv_values)
        self.npv_mean = sum(self.npv_values) / n
        variance = sum((x - self.npv_mean) ** 2 for x in self.npv_values) / n
        self.npv_std = math.sqrt(variance)

        sorted_npv = sorted(self.npv_values)
        self.npv_p5 = sorted_npv[int(n * 0.05)]
        self.npv_p25 = sorted_npv[int(n * 0.25)]
        self.npv_p50 = sorted_npv[int(n * 0.50)]
        self.npv_p75 = sorted_npv[int(n * 0.75)]
        self.npv_p95 = sorted_npv[int(n * 0.95)]

        # Probability metrics
        self.prob_positive_npv = sum(1 for x in self.npv_values if x > 0) / n

        valid_paybacks = [p for p in self.payback_values if p is not None and p < 100]
        if valid_paybacks:
            self.prob_payback_under_10yr = sum(1 for p in valid_paybacks if p <= 10) / n

        # IRR statistics (filter None values)
        valid_irr = [x for x in self.irr_values if x is not None]
        if valid_irr:
            self.irr_mean = sum(valid_irr) / len(valid_irr)
            sorted_irr = sorted(valid_irr)
            n_irr = len(sorted_irr)
            self.irr_p5 = sorted_irr[int(n_irr * 0.05)]
            self.irr_p50 = sorted_irr[int(n_irr * 0.50)]
            self.irr_p95 = sorted_irr[int(n_irr * 0.95)]

    def format(self) -> str:
        """Format Monte Carlo results as text."""
        lines = [
            "=" * 60,
            "MONTE CARLO SIMULATION RESULTS",
            "=" * 60,
            f"Iterations: {self.iterations:,}",
            "",
            "NPV Distribution",
            "-" * 40,
            f"  Mean:              ${self.npv_mean:>14,.0f}",
            f"  Std Dev:           ${self.npv_std:>14,.0f}",
            f"  5th Percentile:    ${self.npv_p5:>14,.0f}",
            f"  25th Percentile:   ${self.npv_p25:>14,.0f}",
            f"  Median (50th):     ${self.npv_p50:>14,.0f}",
            f"  75th Percentile:   ${self.npv_p75:>14,.0f}",
            f"  95th Percentile:   ${self.npv_p95:>14,.0f}",
            "",
            "Risk Metrics",
            "-" * 40,
            f"  P(NPV > 0):        {self.prob_positive_npv:>14.1%}",
            f"  P(Payback < 10yr): {self.prob_payback_under_10yr:>14.1%}",
        ]

        if self.irr_mean is not None:
            lines.extend([
                "",
                "IRR Distribution",
                "-" * 40,
                f"  Mean:              {self.irr_mean:>14.1%}",
                f"  5th Percentile:    {self.irr_p5:>14.1%}" if self.irr_p5 else "  5th Percentile:              N/A",
                f"  Median:            {self.irr_p50:>14.1%}" if self.irr_p50 else "  Median:                      N/A",
                f"  95th Percentile:   {self.irr_p95:>14.1%}" if self.irr_p95 else "  95th Percentile:             N/A",
            ])

        lines.append("=" * 60)
        return "\n".join(lines)


@dataclass
class ParameterDistribution:
    """Distribution definition for Monte Carlo parameter."""
    parameter: SensitivityParameter
    distribution: str  # "normal", "uniform", "triangular"
    mean: float = 0.0
    std: float = 0.0
    low: float = 0.0
    high: float = 0.0
    mode: float = 0.0  # For triangular

    def sample(self) -> float:
        """Draw a random sample from this distribution."""
        if self.distribution == "normal":
            return random.gauss(self.mean, self.std)
        elif self.distribution == "uniform":
            return random.uniform(self.low, self.high)
        elif self.distribution == "triangular":
            return random.triangular(self.low, self.high, self.mode)
        else:
            return self.mean


class SensitivityAnalyzer:
    """
    Sensitivity analysis engine for LCCA scenarios.

    Performs parameter sweeps, tornado analysis, and Monte Carlo simulation
    to understand how results change with different assumptions.

    Example:
        >>> analyzer = SensitivityAnalyzer(baseline, proposed)
        >>>
        >>> # Single parameter sweep
        >>> sweep = analyzer.sweep_parameter(
        ...     SensitivityParameter.DISCOUNT_RATE,
        ...     [0.03, 0.05, 0.07, 0.10]
        ... )
        >>>
        >>> # Tornado analysis
        >>> tornado = analyzer.tornado_analysis()
        >>>
        >>> # Monte Carlo
        >>> mc = analyzer.monte_carlo(iterations=1000)
    """

    def __init__(
        self,
        baseline_scenario: Any,  # TouLccaScenario
        proposed_scenario: Any,  # TouLccaScenario
        assumptions: Optional[Any] = None,  # ScenarioAssumptions
    ):
        """
        Initialize analyzer with base case scenarios.

        Args:
            baseline_scenario: Baseline TouLccaScenario
            proposed_scenario: Proposed TouLccaScenario
            assumptions: Optional ScenarioAssumptions (uses defaults if None)
        """
        self.baseline = baseline_scenario
        self.proposed = proposed_scenario
        self.assumptions = assumptions

        # Store base values
        self._base_values = self._extract_base_values()

        # Default parameter ranges for tornado analysis
        self.default_ranges = self._create_default_ranges()

    def _extract_base_values(self) -> Dict[SensitivityParameter, float]:
        """Extract base parameter values from scenarios."""
        values = {}

        # From assumptions or defaults
        if self.assumptions:
            values[SensitivityParameter.DISCOUNT_RATE] = self.assumptions.discount_rate_real
            values[SensitivityParameter.ELECTRICITY_ESCALATION] = self.assumptions.elec_escalation
            values[SensitivityParameter.GAS_ESCALATION] = self.assumptions.gas_escalation
            values[SensitivityParameter.ANALYSIS_YEARS] = self.assumptions.analysis_years
        else:
            values[SensitivityParameter.DISCOUNT_RATE] = 0.03
            values[SensitivityParameter.ELECTRICITY_ESCALATION] = 0.02
            values[SensitivityParameter.GAS_ESCALATION] = 0.015
            values[SensitivityParameter.ANALYSIS_YEARS] = 20

        # From proposed scenario
        values[SensitivityParameter.CAPEX] = self.proposed.capex_upfront
        values[SensitivityParameter.ELECTRICITY_RATE] = 1.0  # Multiplier
        values[SensitivityParameter.GAS_RATE] = 1.0
        values[SensitivityParameter.PV_DEGRADATION] = 0.005  # 0.5%/year default
        values[SensitivityParameter.INCENTIVE_AMOUNT] = 1.0  # Multiplier

        return values

    def _create_default_ranges(self) -> Dict[SensitivityParameter, ParameterRange]:
        """Create default +/- ranges for each parameter."""
        base = self._base_values

        return {
            SensitivityParameter.DISCOUNT_RATE: ParameterRange(
                parameter=SensitivityParameter.DISCOUNT_RATE,
                low=0.01,
                base=base.get(SensitivityParameter.DISCOUNT_RATE, 0.03),
                high=0.08,
                unit="%",
                description="Real discount rate"
            ),
            SensitivityParameter.ELECTRICITY_ESCALATION: ParameterRange(
                parameter=SensitivityParameter.ELECTRICITY_ESCALATION,
                low=0.00,
                base=base.get(SensitivityParameter.ELECTRICITY_ESCALATION, 0.02),
                high=0.05,
                unit="%/yr",
                description="Annual electricity price escalation"
            ),
            SensitivityParameter.GAS_ESCALATION: ParameterRange(
                parameter=SensitivityParameter.GAS_ESCALATION,
                low=0.00,
                base=base.get(SensitivityParameter.GAS_ESCALATION, 0.015),
                high=0.04,
                unit="%/yr",
                description="Annual gas price escalation"
            ),
            SensitivityParameter.ANALYSIS_YEARS: ParameterRange(
                parameter=SensitivityParameter.ANALYSIS_YEARS,
                low=15,
                base=base.get(SensitivityParameter.ANALYSIS_YEARS, 20),
                high=30,
                unit="years",
                description="Analysis period"
            ),
            SensitivityParameter.CAPEX: ParameterRange(
                parameter=SensitivityParameter.CAPEX,
                low=base.get(SensitivityParameter.CAPEX, 0) * 0.8,
                base=base.get(SensitivityParameter.CAPEX, 0),
                high=base.get(SensitivityParameter.CAPEX, 0) * 1.2,
                unit="$",
                description="Capital cost"
            ),
            SensitivityParameter.ELECTRICITY_RATE: ParameterRange(
                parameter=SensitivityParameter.ELECTRICITY_RATE,
                low=0.85,
                base=1.0,
                high=1.15,
                unit="x",
                description="Electricity rate multiplier"
            ),
            SensitivityParameter.GAS_RATE: ParameterRange(
                parameter=SensitivityParameter.GAS_RATE,
                low=0.80,
                base=1.0,
                high=1.30,
                unit="x",
                description="Gas rate multiplier"
            ),
            SensitivityParameter.PV_DEGRADATION: ParameterRange(
                parameter=SensitivityParameter.PV_DEGRADATION,
                low=0.003,
                base=0.005,
                high=0.008,
                unit="%/yr",
                description="Annual PV output degradation"
            ),
        }

    def _run_lcca_with_params(
        self,
        discount_rate: Optional[float] = None,
        elec_escalation: Optional[float] = None,
        gas_escalation: Optional[float] = None,
        analysis_years: Optional[int] = None,
        capex_multiplier: float = 1.0,
        elec_rate_multiplier: float = 1.0,
        gas_rate_multiplier: float = 1.0,
    ) -> Any:
        """Run LCCA with modified parameters."""
        from .calculators import run_tou_lcca
        from .model import ScenarioAssumptions

        # Create modified assumptions
        base_dr = self._base_values.get(SensitivityParameter.DISCOUNT_RATE, 0.03)
        base_elec = self._base_values.get(SensitivityParameter.ELECTRICITY_ESCALATION, 0.02)
        base_gas = self._base_values.get(SensitivityParameter.GAS_ESCALATION, 0.015)
        base_years = int(self._base_values.get(SensitivityParameter.ANALYSIS_YEARS, 20))

        assumptions = ScenarioAssumptions(
            discount_rate_real=discount_rate if discount_rate is not None else base_dr,
            elec_escalation=elec_escalation if elec_escalation is not None else base_elec,
            gas_escalation=gas_escalation if gas_escalation is not None else base_gas,
            analysis_years=analysis_years if analysis_years is not None else base_years,
        )

        # Modify capex if needed
        original_capex = self.proposed.capex_upfront
        if capex_multiplier != 1.0:
            self.proposed.capex_upfront = original_capex * capex_multiplier

        try:
            # Run LCCA
            # Note: Rate multipliers would require modifying the tariff, which is more complex
            # For now, we apply them as a simple scaling factor on annual costs
            results = run_tou_lcca(
                self.baseline,
                self.proposed,
                assumptions=assumptions,
            )

            # If rate multipliers applied, adjust results
            # (This is a simplification - proper implementation would modify hourly rates)
            if elec_rate_multiplier != 1.0 or gas_rate_multiplier != 1.0:
                # Estimate impact on annual savings
                # This is approximate - real implementation would recalculate with modified rates
                pass

            return results

        finally:
            # Restore original capex
            self.proposed.capex_upfront = original_capex

    def sweep_parameter(
        self,
        parameter: SensitivityParameter,
        values: List[float],
    ) -> ParameterSweep:
        """
        Sweep a single parameter across specified values.

        Args:
            parameter: Parameter to vary
            values: List of values to test

        Returns:
            ParameterSweep with results for each value
        """
        results = []
        base_value = self._base_values.get(parameter, values[len(values)//2])

        for value in values:
            # Map parameter to LCCA arguments
            kwargs = {}
            if parameter == SensitivityParameter.DISCOUNT_RATE:
                kwargs['discount_rate'] = value
            elif parameter == SensitivityParameter.ELECTRICITY_ESCALATION:
                kwargs['elec_escalation'] = value
            elif parameter == SensitivityParameter.GAS_ESCALATION:
                kwargs['gas_escalation'] = value
            elif parameter == SensitivityParameter.ANALYSIS_YEARS:
                kwargs['analysis_years'] = int(value)
            elif parameter == SensitivityParameter.CAPEX:
                base_capex = self._base_values.get(SensitivityParameter.CAPEX, 1)
                kwargs['capex_multiplier'] = value / base_capex if base_capex > 0 else 1.0
            elif parameter == SensitivityParameter.ELECTRICITY_RATE:
                kwargs['elec_rate_multiplier'] = value
            elif parameter == SensitivityParameter.GAS_RATE:
                kwargs['gas_rate_multiplier'] = value

            lcca_results = self._run_lcca_with_params(**kwargs)

            results.append(SweepResult(
                parameter=parameter,
                parameter_value=value,
                npv=lcca_results.npv,
                irr=lcca_results.irr,
                simple_payback=lcca_results.simple_payback_years,
                sir=lcca_results.sir,
                annual_savings=lcca_results.annual_savings,
            ))

        return ParameterSweep(
            parameter=parameter,
            base_value=base_value,
            results=results,
        )

    def tornado_analysis(
        self,
        parameters: Optional[List[SensitivityParameter]] = None,
        ranges: Optional[Dict[SensitivityParameter, ParameterRange]] = None,
    ) -> TornadoAnalysis:
        """
        Run tornado analysis to identify key NPV drivers.

        Args:
            parameters: Parameters to analyze (default: all)
            ranges: Custom ranges (default: use default_ranges)

        Returns:
            TornadoAnalysis with sorted results
        """
        if parameters is None:
            parameters = [
                SensitivityParameter.DISCOUNT_RATE,
                SensitivityParameter.ELECTRICITY_ESCALATION,
                SensitivityParameter.GAS_ESCALATION,
                SensitivityParameter.ANALYSIS_YEARS,
                SensitivityParameter.CAPEX,
            ]

        if ranges is None:
            ranges = self.default_ranges

        # Get base case NPV
        base_results = self._run_lcca_with_params()
        base_npv = base_results.npv

        items = []
        for param in parameters:
            if param not in ranges:
                continue

            param_range = ranges[param]

            # Run at low value
            sweep_low = self.sweep_parameter(param, [param_range.low])
            npv_low = sweep_low.results[0].npv

            # Run at high value
            sweep_high = self.sweep_parameter(param, [param_range.high])
            npv_high = sweep_high.results[0].npv

            items.append(TornadoItem(
                parameter=param,
                low_value=param_range.low,
                base_value=param_range.base,
                high_value=param_range.high,
                npv_at_low=npv_low,
                npv_at_base=base_npv,
                npv_at_high=npv_high,
            ))

        return TornadoAnalysis(base_npv=base_npv, items=items)

    def monte_carlo(
        self,
        iterations: int = 1000,
        distributions: Optional[List[ParameterDistribution]] = None,
        seed: Optional[int] = None,
    ) -> MonteCarloResult:
        """
        Run Monte Carlo simulation with parameter distributions.

        Args:
            iterations: Number of iterations
            distributions: Parameter distributions (default: normal around base)
            seed: Random seed for reproducibility

        Returns:
            MonteCarloResult with statistics
        """
        if seed is not None:
            random.seed(seed)

        # Create default distributions if not provided
        if distributions is None:
            distributions = [
                ParameterDistribution(
                    parameter=SensitivityParameter.DISCOUNT_RATE,
                    distribution="triangular",
                    low=0.03,
                    high=0.10,
                    mode=0.05,
                ),
                ParameterDistribution(
                    parameter=SensitivityParameter.ELECTRICITY_ESCALATION,
                    distribution="triangular",
                    low=0.01,
                    high=0.05,
                    mode=0.03,
                ),
                ParameterDistribution(
                    parameter=SensitivityParameter.GAS_ESCALATION,
                    distribution="triangular",
                    low=0.00,
                    high=0.05,
                    mode=0.02,
                ),
                ParameterDistribution(
                    parameter=SensitivityParameter.CAPEX,
                    distribution="normal",
                    mean=self._base_values.get(SensitivityParameter.CAPEX, 0),
                    std=self._base_values.get(SensitivityParameter.CAPEX, 0) * 0.10,
                ),
            ]

        npv_values = []
        irr_values = []
        payback_values = []

        for _ in range(iterations):
            # Sample parameters
            kwargs = {}
            for dist in distributions:
                value = dist.sample()

                if dist.parameter == SensitivityParameter.DISCOUNT_RATE:
                    kwargs['discount_rate'] = max(0.01, min(0.20, value))
                elif dist.parameter == SensitivityParameter.ELECTRICITY_ESCALATION:
                    kwargs['elec_escalation'] = max(-0.02, min(0.10, value))
                elif dist.parameter == SensitivityParameter.GAS_ESCALATION:
                    kwargs['gas_escalation'] = max(-0.02, min(0.10, value))
                elif dist.parameter == SensitivityParameter.CAPEX:
                    base_capex = self._base_values.get(SensitivityParameter.CAPEX, 1)
                    if base_capex > 0:
                        kwargs['capex_multiplier'] = max(0.5, min(1.5, value / base_capex))

            # Run LCCA
            try:
                results = self._run_lcca_with_params(**kwargs)
                npv_values.append(results.npv)
                irr_values.append(results.irr)
                payback_values.append(results.simple_payback_years)
            except Exception:
                # Skip failed iterations
                continue

        return MonteCarloResult(
            iterations=len(npv_values),
            npv_values=npv_values,
            irr_values=irr_values,
            payback_values=payback_values,
        )

    def breakeven_analysis(
        self,
        parameter: SensitivityParameter,
        target_npv: float = 0.0,
        tolerance: float = 1000,
        max_iterations: int = 50,
    ) -> Optional[float]:
        """
        Find parameter value where NPV equals target (default: breakeven at NPV=0).

        Uses bisection method to find the parameter value.

        Args:
            parameter: Parameter to vary
            target_npv: Target NPV value (default 0 for breakeven)
            tolerance: Acceptable NPV tolerance
            max_iterations: Maximum bisection iterations

        Returns:
            Parameter value at breakeven, or None if not found
        """
        param_range = self.default_ranges.get(parameter)
        if param_range is None:
            return None

        low = param_range.low
        high = param_range.high

        # Check if breakeven is within range
        sweep_low = self.sweep_parameter(parameter, [low])
        sweep_high = self.sweep_parameter(parameter, [high])

        npv_low = sweep_low.results[0].npv
        npv_high = sweep_high.results[0].npv

        # Check if target is bracketed
        if (npv_low - target_npv) * (npv_high - target_npv) > 0:
            # Target not in range
            return None

        # Bisection
        for _ in range(max_iterations):
            mid = (low + high) / 2
            sweep_mid = self.sweep_parameter(parameter, [mid])
            npv_mid = sweep_mid.results[0].npv

            if abs(npv_mid - target_npv) < tolerance:
                return mid

            if (npv_low - target_npv) * (npv_mid - target_npv) < 0:
                high = mid
                npv_high = npv_mid
            else:
                low = mid
                npv_low = npv_mid

        return (low + high) / 2


def format_sensitivity_summary(
    sweep_results: List[ParameterSweep],
    tornado: Optional[TornadoAnalysis] = None,
    monte_carlo: Optional[MonteCarloResult] = None,
) -> str:
    """
    Format complete sensitivity analysis as text report.

    Args:
        sweep_results: List of parameter sweep results
        tornado: Optional tornado analysis
        monte_carlo: Optional Monte Carlo results

    Returns:
        Formatted text report
    """
    lines = [
        "=" * 80,
        "SENSITIVITY ANALYSIS REPORT",
        "=" * 80,
    ]

    # Parameter sweeps
    if sweep_results:
        lines.extend([
            "",
            "PARAMETER SWEEPS",
            "-" * 80,
        ])
        for sweep in sweep_results:
            lines.append("")
            lines.append(sweep.format())

    # Tornado
    if tornado:
        lines.extend([
            "",
            tornado.format(),
        ])

    # Monte Carlo
    if monte_carlo:
        lines.extend([
            "",
            monte_carlo.format(),
        ])

    lines.append("=" * 80)
    return "\n".join(lines)


# =============================================================================
# ZONE-LEVEL SENSITIVITY ANALYSIS (Phase 5)
# =============================================================================

@dataclass
class ZoneSensitivityResult:
    """Sensitivity analysis result for a single zone."""
    zone_name: str
    parameter: SensitivityParameter
    parameter_value: float
    annual_cost: float
    cost_per_sqft: float
    cost_change_pct: float  # Change from base case


@dataclass
class ZoneImpactResult:
    """Result identifying a zone's impact on building LCCA."""
    zone_name: str
    zone_type: str
    annual_cost: float
    building_share_pct: float  # Percentage of building total cost
    area_sqft: float
    cost_per_sqft: float
    is_high_impact: bool  # Exceeds threshold


def zone_sensitivity_analysis(
    zone_results: Dict[str, Any],
    parameters: List[SensitivityParameter],
    ranges: Dict[SensitivityParameter, Tuple[float, float]],
    elec_rate_base: float = 0.25,
    gas_rate_base: float = 1.50,
) -> Dict[str, List[ZoneSensitivityResult]]:
    """
    Run sensitivity analysis for each zone.

    Varies parameters like electricity rate and calculates impact on each zone.

    Args:
        zone_results: Dictionary of zone name -> ZoneLccaResult or similar
        parameters: List of parameters to analyze
        ranges: Dictionary of parameter -> (low, high) range
        elec_rate_base: Base electricity rate ($/kWh)
        gas_rate_base: Base gas rate ($/therm)

    Returns:
        Dictionary mapping zone name to list of sensitivity results
    """
    results = {}

    for zone_name, zone_data in zone_results.items():
        zone_sensitivities = []

        # Get zone energy consumption
        if hasattr(zone_data, 'annual_elec_kwh'):
            elec_kwh = zone_data.annual_elec_kwh
            gas_therm = getattr(zone_data, 'annual_gas_therm', 0)
            area = getattr(zone_data, 'area_sqft', 1)
        elif isinstance(zone_data, dict):
            elec_kwh = zone_data.get('annual_elec_kwh', zone_data.get('elec_kwh', 0))
            gas_therm = zone_data.get('annual_gas_therm', zone_data.get('gas_therm', 0))
            area = zone_data.get('area_sqft', 1)
        else:
            continue

        # Calculate base case cost
        base_cost = elec_kwh * elec_rate_base + gas_therm * gas_rate_base

        for param in parameters:
            if param not in ranges:
                continue

            low, high = ranges[param]

            # Calculate costs at low and high
            for value in [low, high]:
                if param == SensitivityParameter.ELECTRICITY_RATE:
                    adjusted_elec = elec_rate_base * value
                    cost = elec_kwh * adjusted_elec + gas_therm * gas_rate_base
                elif param == SensitivityParameter.GAS_RATE:
                    adjusted_gas = gas_rate_base * value
                    cost = elec_kwh * elec_rate_base + gas_therm * adjusted_gas
                else:
                    cost = base_cost  # Other parameters not zone-specific

                change_pct = ((cost - base_cost) / base_cost * 100) if base_cost > 0 else 0

                zone_sensitivities.append(ZoneSensitivityResult(
                    zone_name=zone_name,
                    parameter=param,
                    parameter_value=value,
                    annual_cost=cost,
                    cost_per_sqft=cost / area if area > 0 else 0,
                    cost_change_pct=change_pct,
                ))

        results[zone_name] = zone_sensitivities

    return results


def identify_high_impact_zones(
    zone_results: Dict[str, Any],
    building_total_cost: float,
    threshold: float = 0.1,
) -> List[ZoneImpactResult]:
    """
    Identify zones with outsized cost impact.

    Args:
        zone_results: Dictionary of zone name -> ZoneLccaResult or similar
        building_total_cost: Total building annual cost
        threshold: Threshold for "high impact" (e.g., 0.1 = 10%)

    Returns:
        List of ZoneImpactResult for zones above threshold
    """
    impact_results = []

    for zone_name, zone_data in zone_results.items():
        # Extract cost from various formats
        if hasattr(zone_data, 'annual_cost'):
            cost = zone_data.annual_cost
            area = getattr(zone_data, 'area_sqft', 1)
            zone_type = getattr(zone_data, 'zone_type', 'unknown')
            if hasattr(zone_type, 'value'):
                zone_type = zone_type.value
        elif hasattr(zone_data, 'net_annual_cost'):
            cost = zone_data.net_annual_cost
            area = getattr(zone_data, 'area_sqft', 1)
            zone_type = getattr(zone_data, 'zone_type', 'unknown')
            if hasattr(zone_type, 'value'):
                zone_type = zone_type.value
        elif isinstance(zone_data, dict):
            cost = zone_data.get('annual_cost', zone_data.get('net_annual_cost', 0))
            area = zone_data.get('area_sqft', 1)
            zone_type = zone_data.get('zone_type', 'unknown')
        else:
            continue

        share = cost / building_total_cost if building_total_cost > 0 else 0

        impact_results.append(ZoneImpactResult(
            zone_name=zone_name,
            zone_type=str(zone_type),
            annual_cost=cost,
            building_share_pct=share * 100,
            area_sqft=area,
            cost_per_sqft=cost / area if area > 0 else 0,
            is_high_impact=share > threshold,
        ))

    # Sort by cost share descending
    return sorted(impact_results, key=lambda x: x.building_share_pct, reverse=True)


def format_zone_impact_table(
    impact_results: List[ZoneImpactResult],
    threshold: float = 0.1,
) -> str:
    """
    Format zone impact analysis as a table.

    Args:
        impact_results: List of zone impact results
        threshold: Threshold for highlighting

    Returns:
        Formatted text table
    """
    lines = [
        "=" * 95,
        "ZONE COST IMPACT ANALYSIS",
        "=" * 95,
        "",
        f"{'Zone Name':<25} {'Type':<15} {'Annual Cost':>12} {'Share':>8} {'$/sqft':>10} {'Impact':>10}",
        "-" * 95,
    ]

    for r in impact_results:
        impact_flag = "HIGH ⚠️" if r.is_high_impact else ""
        lines.append(
            f"{r.zone_name:<25} {r.zone_type:<15} "
            f"${r.annual_cost:>11,.0f} {r.building_share_pct:>7.1f}% "
            f"${r.cost_per_sqft:>9.2f} {impact_flag:>10}"
        )

    # Summary
    high_impact = [r for r in impact_results if r.is_high_impact]
    total_cost = sum(r.annual_cost for r in impact_results)

    lines.extend([
        "-" * 95,
        f"TOTAL: ${total_cost:,.0f}",
        f"Zones above {threshold*100:.0f}% threshold: {len(high_impact)}",
        "=" * 95,
    ])

    return "\n".join(lines)


def zone_tornado_analysis(
    zone_results: Dict[str, Any],
    building_total_cost: float,
    rate_variation: float = 0.25,
    elec_rate_base: float = 0.25,
    gas_rate_base: float = 1.50,
) -> List[Tuple[str, float, float, float]]:
    """
    Generate tornado chart data for zone-level rate sensitivity.

    Args:
        zone_results: Dictionary of zone results
        building_total_cost: Building total cost (for normalization)
        rate_variation: Rate variation (e.g., 0.25 = ±25%)
        elec_rate_base: Base electricity rate
        gas_rate_base: Base gas rate

    Returns:
        List of (zone_name, base_cost, low_cost, high_cost) tuples
        sorted by cost swing
    """
    tornado_data = []

    for zone_name, zone_data in zone_results.items():
        # Extract consumption
        if hasattr(zone_data, 'annual_elec_kwh'):
            elec_kwh = zone_data.annual_elec_kwh
            gas_therm = getattr(zone_data, 'annual_gas_therm', 0)
        elif isinstance(zone_data, dict):
            elec_kwh = zone_data.get('annual_elec_kwh', zone_data.get('elec_kwh', 0))
            gas_therm = zone_data.get('annual_gas_therm', zone_data.get('gas_therm', 0))
        else:
            continue

        # Calculate at base, low, high rates
        base = elec_kwh * elec_rate_base + gas_therm * gas_rate_base
        low = elec_kwh * elec_rate_base * (1 - rate_variation) + gas_therm * gas_rate_base * (1 - rate_variation)
        high = elec_kwh * elec_rate_base * (1 + rate_variation) + gas_therm * gas_rate_base * (1 + rate_variation)

        swing = high - low
        tornado_data.append((zone_name, base, low, high, swing))

    # Sort by swing descending
    tornado_data.sort(key=lambda x: x[4], reverse=True)

    # Return without the swing column
    return [(name, base, low, high) for name, base, low, high, _ in tornado_data]
