"""
LCCA Financial Calculators.

Provides NPV, IRR, Simple Payback, and Savings-to-Investment Ratio (SIR)
calculations for life cycle cost analysis.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Optional, Tuple
import math

from .model import (
    LccaScenario,
    ScenarioAssumptions,
    CashFlow,
    Tariff,
    EnergyStreams,
    TouLccaScenario,
)


@dataclass
class LccaResults:
    """Complete LCCA calculation results."""

    # Primary metrics
    npv: float = 0.0                    # Net Present Value ($)
    irr: Optional[float] = None         # Internal Rate of Return (decimal)
    simple_payback_years: Optional[float] = None  # Simple payback (years)
    discounted_payback_years: Optional[float] = None  # Discounted payback
    sir: Optional[float] = None         # Savings-to-Investment Ratio

    # Annual costs
    baseline_annual_cost: float = 0.0   # Baseline annual energy cost
    proposed_annual_cost: float = 0.0   # Proposed annual energy cost
    annual_savings: float = 0.0         # Year 1 savings

    # Lifecycle costs
    baseline_lifecycle_cost: float = 0.0  # Total baseline lifecycle cost (PV)
    proposed_lifecycle_cost: float = 0.0  # Total proposed lifecycle cost (PV)
    lifecycle_savings: float = 0.0      # Net lifecycle savings (PV)

    # Investment
    initial_investment: float = 0.0     # Upfront capital cost
    total_incentives: float = 0.0       # Sum of all incentives (PV)
    net_investment: float = 0.0         # Initial - incentives

    # Cash flow series
    cash_flows: List[CashFlow] = field(default_factory=list)
    cumulative_cash_flows: List[float] = field(default_factory=list)

    # Analysis parameters
    analysis_years: int = 20
    discount_rate: float = 0.03


def calculate_npv(
    cash_flows: List[float],
    discount_rate: float,
    initial_investment: float = 0.0
) -> float:
    """
    Calculate Net Present Value of a series of cash flows.

    Args:
        cash_flows: List of annual cash flows (year 1 to N)
        discount_rate: Real discount rate (decimal, e.g., 0.03 for 3%)
        initial_investment: Upfront cost at year 0 (positive value)

    Returns:
        NPV in present value dollars

    Formula:
        NPV = -I₀ + Σ(CFₜ / (1 + r)ᵗ) for t = 1 to N
    """
    npv = -initial_investment

    for year, cf in enumerate(cash_flows, start=1):
        npv += cf / ((1 + discount_rate) ** year)

    return npv


def calculate_irr(
    cash_flows: List[float],
    initial_investment: float,
    tolerance: float = 1e-6,
    max_iterations: int = 100
) -> Optional[float]:
    """
    Calculate Internal Rate of Return using Newton-Raphson method.

    IRR is the discount rate where NPV = 0.

    Args:
        cash_flows: List of annual cash flows (year 1 to N)
        initial_investment: Upfront cost at year 0 (positive value)
        tolerance: Convergence tolerance
        max_iterations: Maximum iterations

    Returns:
        IRR as decimal (e.g., 0.12 for 12%), or None if no solution
    """
    if initial_investment <= 0:
        return None

    total_cash = sum(cash_flows)
    if total_cash <= initial_investment:
        # No positive return possible
        return None

    # Initial guess based on simple return
    guess = (total_cash / initial_investment - 1) / len(cash_flows)
    guess = max(min(guess, 0.5), -0.5)  # Bound initial guess

    for _ in range(max_iterations):
        # Calculate NPV and derivative at current guess
        npv = -initial_investment
        dnpv = 0.0

        for year, cf in enumerate(cash_flows, start=1):
            discount = (1 + guess) ** year
            npv += cf / discount
            dnpv -= year * cf / (discount * (1 + guess))

        if abs(dnpv) < 1e-10:
            break

        # Newton-Raphson step
        new_guess = guess - npv / dnpv

        # Bound the guess to reasonable range
        new_guess = max(min(new_guess, 1.0), -0.99)

        if abs(new_guess - guess) < tolerance:
            return new_guess

        guess = new_guess

    # If Newton-Raphson fails, try bisection
    return _irr_bisection(cash_flows, initial_investment)


def _irr_bisection(
    cash_flows: List[float],
    initial_investment: float,
    low: float = -0.99,
    high: float = 1.0,
    tolerance: float = 1e-6,
    max_iterations: int = 100
) -> Optional[float]:
    """Bisection fallback for IRR calculation."""

    def npv_at_rate(rate: float) -> float:
        npv = -initial_investment
        for year, cf in enumerate(cash_flows, start=1):
            npv += cf / ((1 + rate) ** year)
        return npv

    npv_low = npv_at_rate(low)
    npv_high = npv_at_rate(high)

    # Check if solution exists in range
    if npv_low * npv_high > 0:
        return None

    for _ in range(max_iterations):
        mid = (low + high) / 2
        npv_mid = npv_at_rate(mid)

        if abs(npv_mid) < tolerance or (high - low) / 2 < tolerance:
            return mid

        if npv_mid * npv_low < 0:
            high = mid
            npv_high = npv_mid
        else:
            low = mid
            npv_low = npv_mid

    return (low + high) / 2


def calculate_simple_payback(
    initial_investment: float,
    annual_savings: float
) -> Optional[float]:
    """
    Calculate simple payback period in years.

    Args:
        initial_investment: Upfront cost
        annual_savings: Annual savings (assumed constant)

    Returns:
        Payback period in years, or None if savings <= 0
    """
    if annual_savings <= 0 or initial_investment <= 0:
        return None

    return initial_investment / annual_savings


def calculate_discounted_payback(
    cash_flows: List[float],
    initial_investment: float,
    discount_rate: float
) -> Optional[float]:
    """
    Calculate discounted payback period.

    Args:
        cash_flows: Annual cash flows
        initial_investment: Upfront cost
        discount_rate: Real discount rate

    Returns:
        Discounted payback in years, or None if never achieved
    """
    cumulative = -initial_investment

    for year, cf in enumerate(cash_flows, start=1):
        pv_cf = cf / ((1 + discount_rate) ** year)
        prev_cumulative = cumulative
        cumulative += pv_cf

        if cumulative >= 0:
            # Interpolate to find exact year
            if pv_cf > 0:
                fraction = -prev_cumulative / pv_cf
                return year - 1 + fraction
            return float(year)

    return None  # Never achieves payback


def calculate_sir(
    total_savings_pv: float,
    initial_investment: float,
    total_incentives_pv: float = 0.0
) -> Optional[float]:
    """
    Calculate Savings-to-Investment Ratio.

    SIR > 1.0 indicates a cost-effective investment.
    Common in FEMP (Federal Energy Management Program) analysis.

    Args:
        total_savings_pv: Present value of all savings
        initial_investment: Upfront capital cost
        total_incentives_pv: Present value of incentives

    Returns:
        SIR ratio, or None if net investment <= 0
    """
    net_investment = initial_investment - total_incentives_pv
    if net_investment <= 0:
        return None

    return total_savings_pv / net_investment


def calculate_annual_energy_cost(
    energy: EnergyStreams,
    tariff: Tariff,
    use_net_electricity: bool = True
) -> float:
    """
    Calculate annual energy cost from energy streams and tariff.

    Args:
        energy: Energy consumption data
        tariff: Utility rate structure
        use_net_electricity: If True, use net electricity (after PV)

    Returns:
        Annual energy cost in dollars
    """
    elec_kwh = energy.net_electricity_kwh if use_net_electricity else energy.electricity_kwh

    elec_cost = elec_kwh * tariff.elec_rate_per_kwh
    gas_cost = energy.gas_therms * tariff.gas_rate_per_therm
    demand_cost = energy.demand_kw * tariff.demand_rate_per_kw * 12
    customer_charges = tariff.monthly_customer_charge * 12

    return elec_cost + gas_cost + demand_cost + customer_charges


def escalate_cost(
    base_cost: float,
    year: int,
    escalation_rate: float
) -> float:
    """
    Escalate a cost to future year.

    Args:
        base_cost: Year 0 cost
        year: Target year
        escalation_rate: Annual escalation (decimal)

    Returns:
        Escalated cost
    """
    return base_cost * ((1 + escalation_rate) ** year)


def generate_cash_flows(
    baseline_scenario: LccaScenario,
    proposed_scenario: LccaScenario,
    assumptions: Optional[ScenarioAssumptions] = None
) -> Tuple[List[CashFlow], List[float]]:
    """
    Generate annual cash flow series from scenario comparison.

    Args:
        baseline_scenario: Reference case (typically code minimum)
        proposed_scenario: Project case (with efficiency measures)
        assumptions: Financial parameters (uses proposed if None)

    Returns:
        Tuple of (list of CashFlow objects, list of cumulative totals)
    """
    if assumptions is None:
        assumptions = proposed_scenario.assumptions

    cash_flows = []
    cumulative = []
    running_total = -proposed_scenario.capex_upfront

    # Year 0: Initial investment
    cash_flows.append(CashFlow(
        year=0,
        amount=-proposed_scenario.capex_upfront,
        label="Initial Investment",
        category="capital"
    ))
    cumulative.append(running_total)

    # Add incentives
    for incentive in proposed_scenario.incentives:
        if incentive.pays_in_year == 0:
            cash_flows.append(CashFlow(
                year=0,
                amount=incentive.amount,
                label=incentive.name,
                category="incentive"
            ))
            running_total += incentive.amount
            cumulative[-1] = running_total

    # Calculate base energy costs
    baseline_energy_cost = baseline_scenario.annual_energy_cost()
    proposed_energy_cost = proposed_scenario.annual_energy_cost()

    # Operating cost deltas
    opex_delta = proposed_scenario.opex_annual_delta
    maint_delta = proposed_scenario.maintenance_annual_delta

    # Generate annual cash flows
    for year in range(1, assumptions.analysis_years + 1):
        # Escalate energy costs
        baseline_year_cost = escalate_cost(
            baseline_energy_cost, year, assumptions.elec_escalation
        )
        proposed_year_cost = escalate_cost(
            proposed_energy_cost, year, assumptions.elec_escalation
        )

        energy_savings = baseline_year_cost - proposed_year_cost

        # Net annual savings
        annual_savings = energy_savings - opex_delta - maint_delta

        cash_flows.append(CashFlow(
            year=year,
            amount=annual_savings,
            label=f"Year {year} Savings",
            category="operating"
        ))

        running_total += annual_savings
        cumulative.append(running_total)

        # Add any delayed incentives
        for incentive in proposed_scenario.incentives:
            if incentive.pays_in_year == year:
                cash_flows.append(CashFlow(
                    year=year,
                    amount=incentive.amount,
                    label=incentive.name,
                    category="incentive"
                ))
                running_total += incentive.amount
                cumulative[-1] = running_total

    # Salvage value at end of analysis period
    if assumptions.salvage_value > 0:
        cash_flows.append(CashFlow(
            year=assumptions.analysis_years,
            amount=assumptions.salvage_value,
            label="Salvage Value",
            category="capital"
        ))
        cumulative[-1] += assumptions.salvage_value

    return cash_flows, cumulative


def run_lcca(
    baseline_scenario: LccaScenario,
    proposed_scenario: LccaScenario,
    assumptions: Optional[ScenarioAssumptions] = None
) -> LccaResults:
    """
    Run complete LCCA analysis comparing baseline to proposed scenario.

    Args:
        baseline_scenario: Reference case (code minimum, existing condition)
        proposed_scenario: Proposed case (with efficiency measures)
        assumptions: Financial parameters (uses proposed.assumptions if None)

    Returns:
        LccaResults with all calculated metrics
    """
    if assumptions is None:
        assumptions = proposed_scenario.assumptions

    # Generate cash flows
    cash_flow_list, cumulative = generate_cash_flows(
        baseline_scenario, proposed_scenario, assumptions
    )

    # Extract annual savings for calculations
    annual_savings_list = [
        cf.amount for cf in cash_flow_list
        if cf.category == "operating"
    ]

    # Calculate annual costs
    baseline_annual = baseline_scenario.annual_energy_cost()
    proposed_annual = proposed_scenario.annual_energy_cost()
    year1_savings = baseline_annual - proposed_annual

    # Initial investment
    initial_investment = proposed_scenario.capex_upfront

    # Total incentives (PV)
    total_incentives = sum(
        inc.amount / ((1 + assumptions.discount_rate_real) ** inc.pays_in_year)
        for inc in proposed_scenario.incentives
    )

    # NPV of savings stream
    npv_savings = calculate_npv(
        annual_savings_list,
        assumptions.discount_rate_real,
        0  # Don't include investment here
    )

    # Full NPV (savings minus investment plus incentives)
    npv = npv_savings - initial_investment + total_incentives

    # IRR
    irr = calculate_irr(
        annual_savings_list,
        initial_investment - total_incentives  # Net investment
    )

    # Simple payback
    simple_payback = calculate_simple_payback(
        initial_investment - total_incentives,
        year1_savings
    )

    # Discounted payback
    discounted_payback = calculate_discounted_payback(
        annual_savings_list,
        initial_investment - total_incentives,
        assumptions.discount_rate_real
    )

    # SIR
    sir = calculate_sir(npv_savings, initial_investment, total_incentives)

    # Lifecycle costs (present value)
    baseline_lifecycle = sum(
        escalate_cost(baseline_annual, y, assumptions.elec_escalation) /
        ((1 + assumptions.discount_rate_real) ** y)
        for y in range(1, assumptions.analysis_years + 1)
    )

    proposed_lifecycle = initial_investment + sum(
        escalate_cost(proposed_annual, y, assumptions.elec_escalation) /
        ((1 + assumptions.discount_rate_real) ** y)
        for y in range(1, assumptions.analysis_years + 1)
    ) - total_incentives

    return LccaResults(
        npv=npv,
        irr=irr,
        simple_payback_years=simple_payback,
        discounted_payback_years=discounted_payback,
        sir=sir,
        baseline_annual_cost=baseline_annual,
        proposed_annual_cost=proposed_annual,
        annual_savings=year1_savings,
        baseline_lifecycle_cost=baseline_lifecycle,
        proposed_lifecycle_cost=proposed_lifecycle,
        lifecycle_savings=baseline_lifecycle - proposed_lifecycle,
        initial_investment=initial_investment,
        total_incentives=total_incentives,
        net_investment=initial_investment - total_incentives,
        cash_flows=cash_flow_list,
        cumulative_cash_flows=cumulative,
        analysis_years=assumptions.analysis_years,
        discount_rate=assumptions.discount_rate_real
    )


def format_lcca_summary(results: LccaResults) -> str:
    """
    Format LCCA results as a text summary.

    Args:
        results: LccaResults from run_lcca()

    Returns:
        Formatted text summary
    """
    lines = [
        "=" * 60,
        "LIFE CYCLE COST ANALYSIS SUMMARY",
        "=" * 60,
        "",
        "Investment",
        "-" * 40,
        f"  Initial Investment.............. ${results.initial_investment:,.0f}",
        f"  Total Incentives (PV)........... ${results.total_incentives:,.0f}",
        f"  Net Investment.................. ${results.net_investment:,.0f}",
        "",
        "Annual Costs (Year 1)",
        "-" * 40,
        f"  Baseline Annual Cost............ ${results.baseline_annual_cost:,.0f}",
        f"  Proposed Annual Cost............ ${results.proposed_annual_cost:,.0f}",
        f"  Annual Savings.................. ${results.annual_savings:,.0f}",
        "",
        "Financial Metrics",
        "-" * 40,
        f"  Net Present Value (NPV)......... ${results.npv:,.0f}",
    ]

    if results.irr is not None:
        lines.append(f"  Internal Rate of Return (IRR)... {results.irr*100:.1f}%")
    else:
        lines.append("  Internal Rate of Return (IRR)... N/A")

    if results.simple_payback_years is not None:
        lines.append(f"  Simple Payback.................. {results.simple_payback_years:.1f} years")
    else:
        lines.append("  Simple Payback.................. N/A")

    if results.discounted_payback_years is not None:
        lines.append(f"  Discounted Payback.............. {results.discounted_payback_years:.1f} years")
    else:
        lines.append("  Discounted Payback.............. N/A")

    if results.sir is not None:
        lines.append(f"  Savings-to-Investment Ratio..... {results.sir:.2f}")
    else:
        lines.append("  Savings-to-Investment Ratio..... N/A")

    lines.extend([
        "",
        "Lifecycle Costs (Present Value)",
        "-" * 40,
        f"  Baseline Lifecycle Cost......... ${results.baseline_lifecycle_cost:,.0f}",
        f"  Proposed Lifecycle Cost......... ${results.proposed_lifecycle_cost:,.0f}",
        f"  Lifecycle Savings............... ${results.lifecycle_savings:,.0f}",
        "",
        "Analysis Parameters",
        "-" * 40,
        f"  Analysis Period................. {results.analysis_years} years",
        f"  Real Discount Rate.............. {results.discount_rate*100:.1f}%",
        "",
        "=" * 60,
    ])

    return "\n".join(lines)


# ---- TOU-Native LCCA Functions ----

@dataclass
class TouLccaResults(LccaResults):
    """
    LCCA results with additional TOU-specific data.

    Extends LccaResults with TOU cost breakdowns for both scenarios.
    """
    # TOU breakdowns
    baseline_tou_breakdown: Optional[any] = None  # TouCostBreakdown
    proposed_tou_breakdown: Optional[any] = None  # TouCostBreakdown

    # Energy summary
    baseline_kwh: float = 0.0
    proposed_kwh: float = 0.0
    kwh_savings: float = 0.0

    # PV contribution
    pv_generation_kwh: float = 0.0
    pv_value: float = 0.0  # Annual $ value of PV

    # Gas summary
    baseline_gas_therms: float = 0.0
    proposed_gas_therms: float = 0.0
    baseline_gas_cost: float = 0.0
    proposed_gas_cost: float = 0.0


def generate_tou_cash_flows(
    baseline_scenario: TouLccaScenario,
    proposed_scenario: TouLccaScenario,
    assumptions: Optional[ScenarioAssumptions] = None
) -> Tuple[List[CashFlow], List[float]]:
    """
    Generate annual cash flow series from TOU scenario comparison.

    Args:
        baseline_scenario: Reference case with TOU tariff
        proposed_scenario: Proposed case with TOU tariff
        assumptions: Financial parameters (uses proposed if None)

    Returns:
        Tuple of (list of CashFlow objects, list of cumulative totals)
    """
    if assumptions is None:
        assumptions = proposed_scenario.assumptions

    cash_flows = []
    cumulative = []
    running_total = -proposed_scenario.capex_upfront

    # Year 0: Initial investment
    cash_flows.append(CashFlow(
        year=0,
        amount=-proposed_scenario.capex_upfront,
        label="Initial Investment",
        category="capital"
    ))
    cumulative.append(running_total)

    # Add upfront incentives
    for incentive in proposed_scenario.incentives:
        if incentive.pays_in_year == 0:
            cash_flows.append(CashFlow(
                year=0,
                amount=incentive.amount,
                label=incentive.name,
                category="incentive"
            ))
            running_total += incentive.amount
            cumulative[-1] = running_total

    # Calculate base energy costs using TOU
    baseline_energy_cost = baseline_scenario.calculate_annual_cost()
    proposed_energy_cost = proposed_scenario.calculate_annual_cost()

    # Operating cost deltas
    opex_delta = proposed_scenario.opex_annual_delta
    maint_delta = proposed_scenario.maintenance_annual_delta

    # Generate annual cash flows
    for year in range(1, assumptions.analysis_years + 1):
        # Escalate energy costs
        baseline_year_cost = escalate_cost(
            baseline_energy_cost, year, assumptions.elec_escalation
        )
        proposed_year_cost = escalate_cost(
            proposed_energy_cost, year, assumptions.elec_escalation
        )

        energy_savings = baseline_year_cost - proposed_year_cost

        # Net annual savings
        annual_savings = energy_savings - opex_delta - maint_delta

        cash_flows.append(CashFlow(
            year=year,
            amount=annual_savings,
            label=f"Year {year} Savings",
            category="operating"
        ))

        running_total += annual_savings
        cumulative.append(running_total)

        # Add delayed incentives
        for incentive in proposed_scenario.incentives:
            if incentive.pays_in_year == year:
                cash_flows.append(CashFlow(
                    year=year,
                    amount=incentive.amount,
                    label=incentive.name,
                    category="incentive"
                ))
                running_total += incentive.amount
                cumulative[-1] = running_total

    # Salvage value at end
    if assumptions.salvage_value > 0:
        cash_flows.append(CashFlow(
            year=assumptions.analysis_years,
            amount=assumptions.salvage_value,
            label="Salvage Value",
            category="capital"
        ))
        cumulative[-1] += assumptions.salvage_value

    return cash_flows, cumulative


def run_tou_lcca(
    baseline_scenario: TouLccaScenario,
    proposed_scenario: TouLccaScenario,
    assumptions: Optional[ScenarioAssumptions] = None
) -> TouLccaResults:
    """
    Run complete LCCA analysis using TOU tariffs.

    This function calculates lifecycle costs using actual TOU rate structures
    rather than flat average rates, providing more accurate analysis for
    buildings with solar PV, battery storage, or load-shifting potential.

    Args:
        baseline_scenario: Reference case (code minimum, existing, or no-ECM)
        proposed_scenario: Proposed case (with efficiency measures, PV, etc.)
        assumptions: Financial parameters (uses proposed.assumptions if None)

    Returns:
        TouLccaResults with all calculated metrics and TOU breakdowns

    Example:
        >>> from eco_tools.lcca import (
        ...     TouLccaScenario, create_sce_tou_gs3, run_tou_lcca
        ... )
        >>> from eco_tools.lcca.parsers.hourly_results import parse_hourly_results
        >>>
        >>> baseline = parse_hourly_results("building-ab-HourlyResults.csv")
        >>> proposed = parse_hourly_results("building-ap-HourlyResults.csv")
        >>> tariff = create_sce_tou_gs3()
        >>>
        >>> baseline_scenario = TouLccaScenario.from_simulation_output(
        ...     "Baseline", baseline, tariff
        ... )
        >>> proposed_scenario = TouLccaScenario.from_simulation_output(
        ...     "Proposed", proposed, tariff, capex_upfront=500000
        ... )
        >>>
        >>> results = run_tou_lcca(baseline_scenario, proposed_scenario)
        >>> print(f"NPV: ${results.npv:,.0f}")
    """
    if assumptions is None:
        assumptions = proposed_scenario.assumptions

    # Get TOU breakdowns
    baseline_tou = baseline_scenario.calculate_tou_breakdown()
    proposed_tou = proposed_scenario.calculate_tou_breakdown()

    # Calculate annual costs (TOU + gas)
    baseline_annual = baseline_scenario.calculate_annual_cost()
    proposed_annual = proposed_scenario.calculate_annual_cost()
    year1_savings = baseline_annual - proposed_annual

    # Gas costs separately
    baseline_gas_cost = baseline_scenario.annual_gas_therms * baseline_scenario.tou_tariff.gas_rate
    proposed_gas_cost = proposed_scenario.annual_gas_therms * proposed_scenario.tou_tariff.gas_rate

    # Energy quantities
    baseline_kwh = baseline_scenario.get_annual_kwh()
    proposed_kwh = proposed_scenario.get_annual_kwh()
    pv_generation = proposed_scenario.get_pv_generation_kwh()

    # Generate cash flows
    cash_flow_list, cumulative = generate_tou_cash_flows(
        baseline_scenario, proposed_scenario, assumptions
    )

    # Extract annual savings for calculations
    annual_savings_list = [
        cf.amount for cf in cash_flow_list
        if cf.category == "operating"
    ]

    # Initial investment
    initial_investment = proposed_scenario.capex_upfront

    # Total incentives (PV)
    total_incentives = sum(
        inc.amount / ((1 + assumptions.discount_rate_real) ** inc.pays_in_year)
        for inc in proposed_scenario.incentives
    )

    # NPV of savings stream
    npv_savings = calculate_npv(
        annual_savings_list,
        assumptions.discount_rate_real,
        0
    )

    # Full NPV
    npv = npv_savings - initial_investment + total_incentives

    # IRR
    net_investment = initial_investment - total_incentives
    irr = calculate_irr(annual_savings_list, net_investment) if net_investment > 0 else None

    # Simple payback
    simple_payback = calculate_simple_payback(net_investment, year1_savings)

    # Discounted payback
    discounted_payback = calculate_discounted_payback(
        annual_savings_list, net_investment, assumptions.discount_rate_real
    )

    # SIR
    sir = calculate_sir(npv_savings, initial_investment, total_incentives)

    # Lifecycle costs (present value)
    baseline_lifecycle = sum(
        escalate_cost(baseline_annual, y, assumptions.elec_escalation) /
        ((1 + assumptions.discount_rate_real) ** y)
        for y in range(1, assumptions.analysis_years + 1)
    )

    proposed_lifecycle = initial_investment + sum(
        escalate_cost(proposed_annual, y, assumptions.elec_escalation) /
        ((1 + assumptions.discount_rate_real) ** y)
        for y in range(1, assumptions.analysis_years + 1)
    ) - total_incentives

    # Calculate PV value (difference in electricity cost due to PV)
    pv_value = baseline_tou.total_cost - proposed_tou.total_cost if pv_generation > 0 else 0.0

    return TouLccaResults(
        # Standard LCCA metrics
        npv=npv,
        irr=irr,
        simple_payback_years=simple_payback,
        discounted_payback_years=discounted_payback,
        sir=sir,
        baseline_annual_cost=baseline_annual,
        proposed_annual_cost=proposed_annual,
        annual_savings=year1_savings,
        baseline_lifecycle_cost=baseline_lifecycle,
        proposed_lifecycle_cost=proposed_lifecycle,
        lifecycle_savings=baseline_lifecycle - proposed_lifecycle,
        initial_investment=initial_investment,
        total_incentives=total_incentives,
        net_investment=net_investment,
        cash_flows=cash_flow_list,
        cumulative_cash_flows=cumulative,
        analysis_years=assumptions.analysis_years,
        discount_rate=assumptions.discount_rate_real,
        # TOU-specific data
        baseline_tou_breakdown=baseline_tou,
        proposed_tou_breakdown=proposed_tou,
        baseline_kwh=baseline_kwh,
        proposed_kwh=proposed_kwh,
        kwh_savings=baseline_kwh - proposed_kwh,
        pv_generation_kwh=pv_generation,
        pv_value=pv_value,
        baseline_gas_therms=baseline_scenario.annual_gas_therms,
        proposed_gas_therms=proposed_scenario.annual_gas_therms,
        baseline_gas_cost=baseline_gas_cost,
        proposed_gas_cost=proposed_gas_cost,
    )


def format_tou_lcca_summary(results: TouLccaResults) -> str:
    """
    Format TOU LCCA results as a text summary.

    Args:
        results: TouLccaResults from run_tou_lcca()

    Returns:
        Formatted text summary with TOU details
    """
    lines = [
        "=" * 70,
        "LIFE CYCLE COST ANALYSIS (TOU RATES)",
        "=" * 70,
        "",
        "Energy Summary",
        "-" * 50,
        f"  Baseline kWh:       {results.baseline_kwh:>15,.0f}",
        f"  Proposed kWh:       {results.proposed_kwh:>15,.0f}",
        f"  kWh Reduction:      {results.kwh_savings:>15,.0f}  ({results.kwh_savings/results.baseline_kwh*100:.1f}%)" if results.baseline_kwh > 0 else "",
    ]

    if results.pv_generation_kwh > 0:
        lines.append(f"  PV Generation:      {results.pv_generation_kwh:>15,.0f}")

    if results.baseline_gas_therms > 0 or results.proposed_gas_therms > 0:
        lines.extend([
            "",
            f"  Baseline Gas:       {results.baseline_gas_therms:>15,.0f} therms",
            f"  Proposed Gas:       {results.proposed_gas_therms:>15,.0f} therms",
        ])

    lines.extend([
        "",
        "Annual Costs (Year 1)",
        "-" * 50,
        f"  Baseline Annual Cost:   ${results.baseline_annual_cost:>12,.0f}",
        f"  Proposed Annual Cost:   ${results.proposed_annual_cost:>12,.0f}",
        f"  Annual Savings:         ${results.annual_savings:>12,.0f}  ({results.annual_savings/results.baseline_annual_cost*100:.1f}%)" if results.baseline_annual_cost > 0 else f"  Annual Savings:         ${results.annual_savings:>12,.0f}",
    ])

    if results.pv_value > 0:
        lines.append(f"  PV Annual Value:        ${results.pv_value:>12,.0f}")

    lines.extend([
        "",
        "Investment",
        "-" * 50,
        f"  Initial Investment:     ${results.initial_investment:>12,.0f}",
        f"  Total Incentives (PV):  ${results.total_incentives:>12,.0f}",
        f"  Net Investment:         ${results.net_investment:>12,.0f}",
        "",
        "Financial Metrics",
        "-" * 50,
        f"  Net Present Value:      ${results.npv:>12,.0f}",
    ])

    if results.irr is not None:
        lines.append(f"  Internal Rate of Return: {results.irr*100:>11.1f}%")
    else:
        lines.append("  Internal Rate of Return:          N/A")

    if results.simple_payback_years is not None:
        lines.append(f"  Simple Payback:         {results.simple_payback_years:>12.1f} years")
    else:
        lines.append("  Simple Payback:                   N/A")

    if results.discounted_payback_years is not None:
        lines.append(f"  Discounted Payback:     {results.discounted_payback_years:>12.1f} years")
    else:
        lines.append("  Discounted Payback:               N/A")

    if results.sir is not None:
        lines.append(f"  Savings-to-Investment:  {results.sir:>12.2f}")
    else:
        lines.append("  Savings-to-Investment:            N/A")

    lines.extend([
        "",
        "Lifecycle Costs (Present Value)",
        "-" * 50,
        f"  Baseline Lifecycle:     ${results.baseline_lifecycle_cost:>12,.0f}",
        f"  Proposed Lifecycle:     ${results.proposed_lifecycle_cost:>12,.0f}",
        f"  Lifecycle Savings:      ${results.lifecycle_savings:>12,.0f}",
        "",
        "Analysis Parameters",
        "-" * 50,
        f"  Analysis Period:        {results.analysis_years:>12} years",
        f"  Real Discount Rate:     {results.discount_rate*100:>11.1f}%",
        "",
        "=" * 70,
    ])

    return "\n".join(lines)
