"""
Bridge functions connecting simulation outputs to LCCA scenarios.

This module provides the critical connection between:
- SimulationOutput (parsed from CBECC/CSE results)
- LccaScenario (input to financial calculators)
- Mixed-use building section LCCA (Phase 4)
"""

from __future__ import annotations
from typing import Optional, Tuple, Dict, List, Any

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
from .zone_energy import ZoneEnergySummary
from .cuac.models import ZoneType
from .tariffs import TouTariff


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


# =============================================================================
# MIXED-USE BUILDING SUPPORT (Phase 4)
# =============================================================================

def create_mixed_use_scenarios(
    zones: List[ZoneEnergySummary],
    tariff_residential: Optional[TouTariff] = None,
    tariff_commercial: Optional[TouTariff] = None,
    common_area_tariff: Optional[TouTariff] = None,
    default_elec_rate: float = 0.25,
    default_gas_rate: float = 1.50,
) -> Dict[str, Any]:
    """
    Create separate LCCA scenarios for each building section.

    For mixed-use buildings, separates zones into:
    - Residential (dwelling units)
    - Commercial (retail, office)
    - Common areas (corridors, lobby, parking)

    Each section can have its own utility tariff.

    Args:
        zones: List of zone energy summaries
        tariff_residential: TOU tariff for dwelling units
        tariff_commercial: TOU tariff for commercial spaces
        common_area_tariff: TOU tariff for common areas
        default_elec_rate: Default electricity rate ($/kWh)
        default_gas_rate: Default gas rate ($/therm)

    Returns:
        Dictionary with keys:
        - 'residential': Results for dwelling units
        - 'commercial': Results for nonres spaces
        - 'common_area': Results for shared spaces
        - 'combined': Results for whole building
        - 'sections': BuildingSection objects
        - 'aggregator': MeterAggregator instance
    """
    # Import here to avoid circular imports
    from .meter_aggregation import (
        MeterAggregator,
        BuildingSectionType,
        create_mixed_use_lcca,
    )

    # Create aggregator
    aggregator = MeterAggregator(
        residential_tariff=tariff_residential,
        commercial_tariff=tariff_commercial,
        common_area_tariff=common_area_tariff,
    )
    aggregator.add_zones(zones)

    # Calculate costs
    aggregator.calculate_section_costs(
        elec_rate=default_elec_rate,
        gas_rate=default_gas_rate,
    )

    # Get sections
    sections = aggregator.get_building_sections()

    # Build result dictionary
    result = {
        'aggregator': aggregator,
        'sections': sections,
        'combined': {
            'total_elec_kwh': aggregator.total_elec_kwh,
            'total_gas_therm': aggregator.total_gas_therm,
            'total_area_sqft': aggregator.total_area_sqft,
            'dwelling_unit_count': aggregator.dwelling_unit_count,
            'zone_count': aggregator.zone_count,
        },
    }

    # Add section-specific results
    if BuildingSectionType.RESIDENTIAL in sections:
        res_section = sections[BuildingSectionType.RESIDENTIAL]
        result['residential'] = {
            'zone_count': res_section.zone_count,
            'dwelling_unit_count': res_section.dwelling_unit_count,
            'total_elec_kwh': res_section.total_elec_kwh,
            'total_gas_therm': res_section.total_gas_therm,
            'total_area_sqft': res_section.total_area_sqft,
            'annual_cost': res_section.total_annual_cost,
            'cost_per_unit': res_section.cost_per_unit,
            'eui_kbtu_sqft': res_section.eui_kbtu_sqft,
            'pv_allocation_kwdc': res_section.pv_allocation_kwdc,
        }

    if BuildingSectionType.COMMERCIAL in sections:
        com_section = sections[BuildingSectionType.COMMERCIAL]
        result['commercial'] = {
            'zone_count': com_section.zone_count,
            'total_elec_kwh': com_section.total_elec_kwh,
            'total_gas_therm': com_section.total_gas_therm,
            'total_area_sqft': com_section.total_area_sqft,
            'annual_cost': com_section.total_annual_cost,
            'cost_per_sqft': com_section.cost_per_sqft,
            'eui_kbtu_sqft': com_section.eui_kbtu_sqft,
        }

    if BuildingSectionType.COMMON_AREA in sections:
        ca_section = sections[BuildingSectionType.COMMON_AREA]
        result['common_area'] = {
            'zone_count': ca_section.zone_count,
            'total_elec_kwh': ca_section.total_elec_kwh,
            'total_gas_therm': ca_section.total_gas_therm,
            'total_area_sqft': ca_section.total_area_sqft,
            'annual_cost': ca_section.total_annual_cost,
            'cost_per_sqft': ca_section.cost_per_sqft,
            'eui_kbtu_sqft': ca_section.eui_kbtu_sqft,
            'meter_categories': {
                cat.value: {
                    'zone_count': agg.zone_count,
                    'total_elec_kwh': agg.total_elec_kwh,
                    'total_area_sqft': agg.total_area_sqft,
                }
                for cat, agg in ca_section.meter_categories.items()
            },
        }

    return result


def create_section_lcca_scenario(
    section_zones: List[ZoneEnergySummary],
    tariff: Tariff,
    name: str,
    capex: float = 0.0,
    assumptions: Optional[ScenarioAssumptions] = None,
    incentives: Optional[list] = None,
) -> LccaScenario:
    """
    Create LCCA scenario from a building section's zones.

    Aggregates zone energy data into a single scenario.

    Args:
        section_zones: Zones belonging to this section
        tariff: Utility tariff for this section
        name: Section name
        capex: Capital cost allocated to this section
        assumptions: Financial parameters
        incentives: Incentives allocated to this section

    Returns:
        LccaScenario for this building section
    """
    # Aggregate zone energy
    total_elec = sum(z.elec_kwh * z.multiplier for z in section_zones)
    total_gas = sum(z.gas_therm * z.multiplier for z in section_zones)
    peak_demand = max((z.peak_demand_kw for z in section_zones), default=0.0)

    # Aggregate end-uses
    cooling = sum(z.cooling_kwh * z.multiplier for z in section_zones)
    heating_kwh = sum(z.heating_kwh * z.multiplier for z in section_zones)
    heating_therm = sum(z.heating_therm * z.multiplier for z in section_zones)
    dhw_kwh = sum(z.dhw_kwh * z.multiplier for z in section_zones)
    dhw_therm = sum(z.dhw_therm * z.multiplier for z in section_zones)
    lighting = sum(z.lighting_kwh * z.multiplier for z in section_zones)

    # PV allocation
    pv_gen = sum(z.pv_generation_kwh * z.multiplier for z in section_zones)

    energy = EnergyStreams(
        electricity_kwh=total_elec,
        gas_therms=total_gas,
        demand_kw=peak_demand,
        cooling_kwh=cooling,
        heating_kwh=heating_kwh,
        heating_therm=heating_therm,
        dhw_kwh=dhw_kwh,
        dhw_therm=dhw_therm,
        pv_generation_kwh=pv_gen,
        net_electricity_kwh=max(0, total_elec - pv_gen),
    )

    return LccaScenario(
        name=name,
        capex_upfront=capex,
        energy=energy,
        tariff=tariff,
        assumptions=assumptions or ScenarioAssumptions(),
        incentives=incentives or []
    )


def run_mixed_use_lcca(
    zones: List[ZoneEnergySummary],
    baseline_zones: Optional[List[ZoneEnergySummary]] = None,
    tariff_residential: Tariff = None,
    tariff_commercial: Tariff = None,
    common_area_tariff: Tariff = None,
    residential_capex: float = 0.0,
    commercial_capex: float = 0.0,
    common_area_capex: float = 0.0,
    assumptions: Optional[ScenarioAssumptions] = None,
    residential_incentives: Optional[list] = None,
    commercial_incentives: Optional[list] = None,
) -> Dict[str, LccaResults]:
    """
    Run complete LCCA for a mixed-use building.

    Creates separate LCCA results for each building section.

    Args:
        zones: Proposed case zone summaries
        baseline_zones: Baseline zone summaries (optional)
        tariff_residential: Tariff for dwelling units
        tariff_commercial: Tariff for commercial spaces
        common_area_tariff: Tariff for common areas
        residential_capex: Capital cost for residential section
        commercial_capex: Capital cost for commercial section
        common_area_capex: Capital cost for common areas
        assumptions: Financial parameters
        residential_incentives: Incentives for residential
        commercial_incentives: Incentives for commercial

    Returns:
        Dictionary with LCCA results per section
    """
    if assumptions is None:
        assumptions = ScenarioAssumptions()

    results = {}

    # Separate zones by type
    residential_zones = [z for z in zones if z.zone_type == ZoneType.DWELLING_UNIT]
    commercial_zones = [z for z in zones if z.zone_type == ZoneType.NONRESIDENTIAL]
    common_area_zones = [z for z in zones if z.zone_type == ZoneType.COMMON_AREA]

    # Handle baseline (if not provided, use proposed as baseline)
    if baseline_zones is None:
        baseline_zones = zones

    baseline_residential = [z for z in baseline_zones if z.zone_type == ZoneType.DWELLING_UNIT]
    baseline_commercial = [z for z in baseline_zones if z.zone_type == ZoneType.NONRESIDENTIAL]
    baseline_common_area = [z for z in baseline_zones if z.zone_type == ZoneType.COMMON_AREA]

    # Use common area tariff for common areas, default to residential if not specified
    if common_area_tariff is None:
        common_area_tariff = tariff_residential

    # Run LCCA for each section
    if residential_zones and tariff_residential:
        proposed_res = create_section_lcca_scenario(
            residential_zones,
            tariff_residential,
            "Residential - Proposed",
            residential_capex,
            assumptions,
            residential_incentives
        )
        baseline_res = create_section_lcca_scenario(
            baseline_residential,
            tariff_residential,
            "Residential - Baseline",
            0.0,
            assumptions
        )
        results['residential'] = run_lcca(baseline_res, proposed_res, assumptions)

    if commercial_zones and tariff_commercial:
        proposed_com = create_section_lcca_scenario(
            commercial_zones,
            tariff_commercial,
            "Commercial - Proposed",
            commercial_capex,
            assumptions,
            commercial_incentives
        )
        baseline_com = create_section_lcca_scenario(
            baseline_commercial,
            tariff_commercial,
            "Commercial - Baseline",
            0.0,
            assumptions
        )
        results['commercial'] = run_lcca(baseline_com, proposed_com, assumptions)

    if common_area_zones and common_area_tariff:
        proposed_ca = create_section_lcca_scenario(
            common_area_zones,
            common_area_tariff,
            "Common Area - Proposed",
            common_area_capex,
            assumptions
        )
        baseline_ca = create_section_lcca_scenario(
            baseline_common_area,
            common_area_tariff,
            "Common Area - Baseline",
            0.0,
            assumptions
        )
        results['common_area'] = run_lcca(baseline_ca, proposed_ca, assumptions)

    return results


def allocate_capex_by_section(
    total_capex: float,
    zones: List[ZoneEnergySummary],
    method: str = "by_area"
) -> Dict[str, float]:
    """
    Allocate total capital cost across building sections.

    Args:
        total_capex: Total capital cost to allocate
        zones: Zone energy summaries
        method: Allocation method ("by_area", "by_consumption", "equal")

    Returns:
        Dictionary with capex per section
    """
    from .meter_aggregation import MeterAggregator, BuildingSectionType

    aggregator = MeterAggregator()
    aggregator.add_zones(zones)

    allocations = aggregator.allocate_master_meter(method=method)

    return {
        'residential': total_capex * allocations.get(BuildingSectionType.RESIDENTIAL, 0),
        'commercial': total_capex * allocations.get(BuildingSectionType.COMMERCIAL, 0),
        'common_area': total_capex * allocations.get(BuildingSectionType.COMMON_AREA, 0),
    }
