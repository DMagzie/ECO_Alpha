"""
Bridge functions connecting simulation outputs to LCCA scenarios.

This module provides the critical connection between:
- SimulationOutput (parsed from CBECC/CSE results)
- LccaScenario (input to financial calculators)
"""

from __future__ import annotations
from typing import Optional, Tuple

from .model import (
    SimulationOutput,
    AnnualEnergySummary,
    LccaScenario,
    EnergyStreams,
    Tariff,
    ScenarioAssumptions,
    Incentive,
)
from .calculators import run_lcca, LccaResults


def simulation_to_energy_streams(
    sim: SimulationOutput,
    use_net: bool = True
) -> EnergyStreams:
    """
    Convert SimulationOutput annual data to EnergyStreams.

    Args:
        sim: Parsed simulation output
        use_net: If True, use net electricity (after PV/battery)

    Returns:
        EnergyStreams for LCCA calculations
    """
    annual = sim.annual

    if use_net:
        elec_kwh = annual.net_elec_kwh if annual.net_elec_kwh > 0 else annual.total_elec_kwh
    else:
        elec_kwh = annual.total_elec_kwh

    return EnergyStreams(
        electricity_kwh=annual.total_elec_kwh,
        gas_therms=annual.total_gas_therm,
        demand_kw=annual.peak_demand_kw,
        cooling_kwh=annual.cooling_kwh,
        heating_kwh=annual.heating_kwh,
        heating_therm=annual.heating_therm,
        dhw_kwh=annual.dhw_elec_kwh,
        dhw_therm=annual.dhw_therm,
        pv_generation_kwh=annual.pv_generation_kwh,
        net_electricity_kwh=elec_kwh
    )


def simulation_to_scenario(
    sim: SimulationOutput,
    tariff: Tariff,
    name: Optional[str] = None,
    capex: float = 0.0,
    assumptions: Optional[ScenarioAssumptions] = None,
    incentives: Optional[list] = None,
    use_net_electricity: bool = True
) -> LccaScenario:
    """
    Convert SimulationOutput to LccaScenario for financial analysis.

    Args:
        sim: Parsed simulation output (proposed or baseline)
        tariff: Utility rate structure
        name: Scenario name (defaults to sim.project_name)
        capex: Capital expenditure for this scenario
        assumptions: Financial parameters (uses defaults if None)
        incentives: List of Incentive objects
        use_net_electricity: If True, use net electricity (after PV)

    Returns:
        LccaScenario ready for financial calculations
    """
    energy = simulation_to_energy_streams(sim, use_net=use_net_electricity)

    return LccaScenario(
        name=name or sim.project_name or "Unnamed Scenario",
        capex_upfront=capex,
        energy=energy,
        tariff=tariff,
        assumptions=assumptions or ScenarioAssumptions(),
        incentives=incentives or []
    )


def create_baseline_scenario(
    sim_baseline: SimulationOutput,
    tariff: Tariff,
    name: str = "Baseline",
    assumptions: Optional[ScenarioAssumptions] = None
) -> LccaScenario:
    """
    Create baseline scenario from simulation output.

    Baseline typically has zero capital cost (existing or code-minimum).

    Args:
        sim_baseline: Baseline simulation output
        tariff: Utility rate structure
        name: Scenario name
        assumptions: Financial parameters

    Returns:
        LccaScenario for baseline case
    """
    return simulation_to_scenario(
        sim=sim_baseline,
        tariff=tariff,
        name=name,
        capex=0.0,
        assumptions=assumptions,
        use_net_electricity=False  # Baseline typically doesn't have PV
    )


def create_proposed_scenario(
    sim_proposed: SimulationOutput,
    tariff: Tariff,
    incremental_cost: float,
    name: str = "Proposed",
    assumptions: Optional[ScenarioAssumptions] = None,
    incentives: Optional[list] = None,
    include_pv_cost: bool = True,
    pv_cost_per_watt: float = 2.50,
    include_battery_cost: bool = True,
    battery_cost_per_kwh: float = 500.0
) -> LccaScenario:
    """
    Create proposed scenario from simulation output.

    Automatically calculates PV and battery costs if present.

    Args:
        sim_proposed: Proposed simulation output
        tariff: Utility rate structure
        incremental_cost: Additional capital cost (efficiency measures)
        name: Scenario name
        assumptions: Financial parameters
        incentives: List of incentives
        include_pv_cost: Add PV system cost to CAPEX
        pv_cost_per_watt: Installed PV cost ($/Wdc)
        include_battery_cost: Add battery cost to CAPEX
        battery_cost_per_kwh: Installed battery cost ($/kWh)

    Returns:
        LccaScenario for proposed case
    """
    total_capex = incremental_cost

    # Add PV cost if present
    if include_pv_cost and sim_proposed.pv_capacity_kwdc > 0:
        pv_cost = sim_proposed.pv_capacity_kwdc * 1000 * pv_cost_per_watt
        total_capex += pv_cost

    # Add battery cost if present
    if include_battery_cost and sim_proposed.battery_capacity_kwh > 0:
        battery_cost = sim_proposed.battery_capacity_kwh * battery_cost_per_kwh
        total_capex += battery_cost

    return simulation_to_scenario(
        sim=sim_proposed,
        tariff=tariff,
        name=name,
        capex=total_capex,
        assumptions=assumptions,
        incentives=incentives,
        use_net_electricity=True  # Use net (with PV/battery)
    )


def run_simulation_lcca(
    proposed: SimulationOutput,
    baseline: SimulationOutput,
    tariff: Tariff,
    incremental_cost: float = 0.0,
    assumptions: Optional[ScenarioAssumptions] = None,
    incentives: Optional[list] = None,
    pv_cost_per_watt: float = 2.50,
    battery_cost_per_kwh: float = 500.0
) -> LccaResults:
    """
    Run complete LCCA from simulation outputs.

    This is the main entry point for simulation-to-LCCA analysis.

    Args:
        proposed: Proposed simulation output
        baseline: Baseline simulation output
        tariff: Utility rate structure
        incremental_cost: Capital cost of efficiency measures
        assumptions: Financial parameters
        incentives: List of incentives for proposed scenario
        pv_cost_per_watt: PV installed cost ($/Wdc)
        battery_cost_per_kwh: Battery installed cost ($/kWh)

    Returns:
        LccaResults with all financial metrics
    """
    if assumptions is None:
        assumptions = ScenarioAssumptions()

    baseline_scenario = create_baseline_scenario(
        sim_baseline=baseline,
        tariff=tariff,
        assumptions=assumptions
    )

    proposed_scenario = create_proposed_scenario(
        sim_proposed=proposed,
        tariff=tariff,
        incremental_cost=incremental_cost,
        assumptions=assumptions,
        incentives=incentives,
        pv_cost_per_watt=pv_cost_per_watt,
        battery_cost_per_kwh=battery_cost_per_kwh
    )

    return run_lcca(baseline_scenario, proposed_scenario, assumptions)


def quick_lcca_from_annual(
    proposed_annual: AnnualEnergySummary,
    baseline_annual: AnnualEnergySummary,
    tariff: Tariff,
    capital_cost: float,
    analysis_years: int = 20,
    discount_rate: float = 0.03
) -> LccaResults:
    """
    Quick LCCA from annual summaries without full SimulationOutput.

    Useful for simplified analysis or testing.

    Args:
        proposed_annual: Proposed annual energy summary
        baseline_annual: Baseline annual energy summary
        tariff: Utility rate structure
        capital_cost: Total capital investment
        analysis_years: Analysis period
        discount_rate: Real discount rate

    Returns:
        LccaResults
    """
    # Create minimal SimulationOutput wrappers
    proposed_sim = SimulationOutput(
        project_name="Proposed",
        annual=proposed_annual
    )

    baseline_sim = SimulationOutput(
        project_name="Baseline",
        annual=baseline_annual
    )

    assumptions = ScenarioAssumptions(
        analysis_years=analysis_years,
        discount_rate_real=discount_rate
    )

    return run_simulation_lcca(
        proposed=proposed_sim,
        baseline=baseline_sim,
        tariff=tariff,
        incremental_cost=capital_cost,
        assumptions=assumptions
    )


def estimate_pv_incentives(
    pv_capacity_kwdc: float,
    federal_itc_rate: float = 0.30,
    state_rebate_per_watt: float = 0.0,
    utility_rebate_per_watt: float = 0.0,
    pv_cost_per_watt: float = 2.50
) -> list:
    """
    Estimate common PV incentives.

    Args:
        pv_capacity_kwdc: PV system size in kWdc
        federal_itc_rate: Federal Investment Tax Credit rate (0.30 = 30%)
        state_rebate_per_watt: State rebate per watt
        utility_rebate_per_watt: Utility rebate per watt
        pv_cost_per_watt: Installed PV cost (for ITC calculation)

    Returns:
        List of Incentive objects
    """
    incentives = []
    capacity_watts = pv_capacity_kwdc * 1000

    # Federal ITC (typically received in year 1 tax filing)
    if federal_itc_rate > 0:
        pv_cost = capacity_watts * pv_cost_per_watt
        itc_amount = pv_cost * federal_itc_rate
        incentives.append(Incentive(
            name="Federal Investment Tax Credit (ITC)",
            amount=itc_amount,
            pays_in_year=1,
            type="tax_credit"
        ))

    # State rebate (typically upfront)
    if state_rebate_per_watt > 0:
        state_rebate = capacity_watts * state_rebate_per_watt
        incentives.append(Incentive(
            name="State Solar Rebate",
            amount=state_rebate,
            pays_in_year=0,
            type="rebate"
        ))

    # Utility rebate (typically upfront)
    if utility_rebate_per_watt > 0:
        utility_rebate = capacity_watts * utility_rebate_per_watt
        incentives.append(Incentive(
            name="Utility Solar Rebate",
            amount=utility_rebate,
            pays_in_year=0,
            type="rebate"
        ))

    return incentives
