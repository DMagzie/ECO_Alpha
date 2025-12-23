"""
Shared pytest fixtures for LCCA tests.

This module provides standardized test data and mock objects
for consistent testing across all LCCA modules.
"""

import pytest
from typing import List
from datetime import datetime

from eco_tools.lcca import (
    HourlyEnergy,
    AnnualEnergySummary,
    TouLccaScenario,
    ScenarioAssumptions,
    LccaResults,
    TouLccaResults,
    create_sce_tou_gs3,
    create_pge_b20,
    ECMBundle,
    ECM,
    ECMCategory,
)


# =============================================================================
# Hourly Data Fixtures
# =============================================================================

@pytest.fixture
def minimal_hourly_data() -> List[HourlyEnergy]:
    """Minimal 8760-hour dataset with constant load."""
    return [
        HourlyEnergy(
            month=(i // 730) % 12 + 1,
            day=((i % 730) // 24) + 1,
            hour=i % 24,
            elec_total_kwh=100.0,  # 100 kWh/hour constant
            gas_total_therm=0.1,   # 0.1 therm/hour constant
        )
        for i in range(8760)
    ]


@pytest.fixture
def realistic_office_hourly_data() -> List[HourlyEnergy]:
    """Realistic office building load profile (8760 hours)."""
    hourly = []
    for i in range(8760):
        month = (i // 730) % 12 + 1
        if month > 12:
            month = 12
        day = ((i % 730) // 24) + 1
        hour = i % 24

        # Base load (always on)
        base_kwh = 50.0

        # Occupancy schedule (M-F 6am-8pm)
        day_of_week = (i // 24) % 7
        is_weekday = day_of_week < 5
        is_occupied = is_weekday and 6 <= hour <= 20

        # HVAC load (seasonal)
        is_summer = 5 <= month <= 9
        if is_summer:
            hvac_kwh = 80.0 if is_occupied else 30.0
        else:
            hvac_kwh = 40.0 if is_occupied else 15.0

        # Lighting and plug loads
        if is_occupied:
            lighting_kwh = 30.0
            plugs_kwh = 25.0
        else:
            lighting_kwh = 5.0
            plugs_kwh = 10.0

        # Gas heating (winter only, occupied hours)
        if month in [1, 2, 3, 11, 12] and is_occupied:
            gas_therm = 2.0
        else:
            gas_therm = 0.1  # Pilot/DHW

        hourly.append(HourlyEnergy(
            month=month,
            day=day,
            hour=hour,
            elec_total_kwh=base_kwh + hvac_kwh + lighting_kwh + plugs_kwh,
            elec_cooling_kwh=hvac_kwh * 0.6 if is_summer else 0,
            elec_heating_kwh=hvac_kwh * 0.4 if not is_summer else 0,
            elec_lighting_kwh=lighting_kwh,
            elec_receptacle_kwh=plugs_kwh,
            gas_total_therm=gas_therm,
            gas_heating_therm=gas_therm * 0.9,
            gas_dhw_therm=gas_therm * 0.1,
        ))

    return hourly


@pytest.fixture
def hourly_data_with_pv() -> List[HourlyEnergy]:
    """Hourly data with PV generation (8760 hours)."""
    hourly = []
    for i in range(8760):
        month = (i // 730) % 12 + 1
        if month > 12:
            month = 12
        day = ((i % 730) // 24) + 1
        hour = i % 24

        # Base load
        load_kwh = 100.0

        # PV generation (bell curve during daylight)
        pv_kwh = 0.0
        if 6 <= hour <= 18:
            # Peak at noon
            hour_factor = 1.0 - abs(hour - 12) / 6.0
            # Seasonal variation
            if 4 <= month <= 9:
                seasonal_factor = 1.0
            else:
                seasonal_factor = 0.7
            pv_kwh = 50.0 * hour_factor * seasonal_factor

        hourly.append(HourlyEnergy(
            month=month,
            day=day,
            hour=hour,
            elec_total_kwh=load_kwh,
            pv_generation_kwh=pv_kwh,
        ))

    return hourly


@pytest.fixture
def all_electric_hourly_data() -> List[HourlyEnergy]:
    """All-electric building (no gas)."""
    return [
        HourlyEnergy(
            month=(i // 730) % 12 + 1,
            day=((i % 730) // 24) + 1,
            hour=i % 24,
            elec_total_kwh=150.0,
            gas_total_therm=0.0,
        )
        for i in range(8760)
    ]


@pytest.fixture
def net_zero_hourly_data() -> List[HourlyEnergy]:
    """Net-zero building (PV matches load annually)."""
    hourly = []
    for i in range(8760):
        month = (i // 730) % 12 + 1
        if month > 12:
            month = 12
        hour = i % 24

        # Load
        load_kwh = 100.0

        # PV sized to match annual load
        if 6 <= hour <= 18:
            hour_factor = 1.0 - abs(hour - 12) / 6.0
            pv_kwh = 150.0 * hour_factor  # Oversized for daylight hours
        else:
            pv_kwh = 0.0

        hourly.append(HourlyEnergy(
            month=month,
            day=((i % 730) // 24) + 1,
            hour=hour,
            elec_total_kwh=load_kwh,
            pv_generation_kwh=pv_kwh,
        ))

    return hourly


# =============================================================================
# Annual Summary Fixtures
# =============================================================================

@pytest.fixture
def typical_annual_summary() -> AnnualEnergySummary:
    """Typical commercial building annual summary."""
    return AnnualEnergySummary(
        total_elec_kwh=1_000_000,
        total_gas_therm=20_000,
        peak_demand_kw=400,
        peak_demand_month=7,
        peak_demand_hour=15,
        pv_generation_kwh=0,
        net_elec_kwh=1_000_000,
        cooling_kwh=300_000,
        heating_kwh=50_000,
        fans_kwh=150_000,
        lighting_kwh=200_000,
        receptacle_kwh=250_000,
        heating_therm=18_000,
        dhw_therm=2_000,
    )


@pytest.fixture
def annual_summary_with_pv() -> AnnualEnergySummary:
    """Annual summary with significant PV generation."""
    return AnnualEnergySummary(
        total_elec_kwh=1_000_000,
        total_gas_therm=0,
        peak_demand_kw=400,
        pv_generation_kwh=500_000,
        net_elec_kwh=500_000,
    )


# =============================================================================
# Scenario Fixtures
# =============================================================================

@pytest.fixture
def baseline_scenario(minimal_hourly_data) -> TouLccaScenario:
    """Standard baseline scenario."""
    tariff = create_sce_tou_gs3()
    return TouLccaScenario(
        name="Baseline",
        hourly_data=minimal_hourly_data,
        tou_tariff=tariff,
        capex_upfront=0,
    )


@pytest.fixture
def proposed_scenario(hourly_data_with_pv) -> TouLccaScenario:
    """Proposed scenario with PV."""
    tariff = create_sce_tou_gs3()
    return TouLccaScenario(
        name="Proposed",
        hourly_data=hourly_data_with_pv,
        tou_tariff=tariff,
        capex_upfront=100_000,
    )


@pytest.fixture
def electrification_scenario(all_electric_hourly_data) -> TouLccaScenario:
    """All-electric proposed scenario."""
    tariff = create_sce_tou_gs3()
    return TouLccaScenario(
        name="Electrification",
        hourly_data=all_electric_hourly_data,
        tou_tariff=tariff,
        capex_upfront=150_000,
    )


# =============================================================================
# Assumptions Fixtures
# =============================================================================

@pytest.fixture
def default_assumptions() -> ScenarioAssumptions:
    """Default LCCA assumptions."""
    return ScenarioAssumptions()


@pytest.fixture
def aggressive_assumptions() -> ScenarioAssumptions:
    """Aggressive assumptions (favorable to projects)."""
    return ScenarioAssumptions(
        analysis_years=30,
        discount_rate_real=0.02,
        elec_escalation=0.04,
        gas_escalation=0.03,
    )


@pytest.fixture
def conservative_assumptions() -> ScenarioAssumptions:
    """Conservative assumptions (unfavorable to projects)."""
    return ScenarioAssumptions(
        analysis_years=15,
        discount_rate_real=0.07,
        elec_escalation=0.01,
        gas_escalation=0.01,
    )


# =============================================================================
# Tariff Fixtures
# =============================================================================

@pytest.fixture
def sce_tariff():
    """SCE TOU-GS-3 tariff."""
    return create_sce_tou_gs3()


@pytest.fixture
def pge_tariff():
    """PG&E B-20 tariff."""
    return create_pge_b20()


# =============================================================================
# ECM Fixtures
# =============================================================================

@pytest.fixture
def pv_ecm() -> ECM:
    """100 kW PV system ECM."""
    return ECM(
        name="100 kW PV",
        category=ECMCategory.GENERATION,
        capex=250_000,
        annual_kwh_generation=150_000,
        incentives=[{
            'name': 'Federal ITC (30%)',
            'amount': 75_000,
            'pays_in_year': 0,
        }],
    )


@pytest.fixture
def led_ecm() -> ECM:
    """LED lighting retrofit ECM."""
    return ECM(
        name="LED Retrofit",
        category=ECMCategory.LIGHTING,
        capex=50_000,
        annual_kwh_delta=-30_000,
    )


@pytest.fixture
def hvac_ecm() -> ECM:
    """High-efficiency HVAC ECM."""
    return ECM(
        name="High-Eff HVAC",
        category=ECMCategory.HVAC,
        capex=200_000,
        annual_kwh_delta=-50_000,
        annual_therm_delta=-5_000,
    )


@pytest.fixture
def sample_ecm_bundle(pv_ecm, led_ecm, hvac_ecm) -> ECMBundle:
    """Sample bundle with multiple ECMs."""
    bundle = ECMBundle(name="Sample Bundle")
    bundle.add_ecm(pv_ecm)
    bundle.add_ecm(led_ecm)
    bundle.add_ecm(hvac_ecm)
    return bundle


# =============================================================================
# Results Fixtures
# =============================================================================

@pytest.fixture
def positive_lcca_results() -> LccaResults:
    """LCCA results with positive NPV."""
    return LccaResults(
        baseline_annual_cost=100_000,
        proposed_annual_cost=80_000,
        annual_savings=20_000,
        upfront_cost=100_000,
        incentives_total=20_000,
        net_investment=80_000,
        npv=150_000,
        irr=0.18,
        simple_payback_years=4.0,
        discounted_payback_years=5.5,
        sir=2.5,
        analysis_years=20,
        discount_rate=0.03,
        cash_flows=[],
    )


@pytest.fixture
def negative_lcca_results() -> LccaResults:
    """LCCA results with negative NPV."""
    return LccaResults(
        baseline_annual_cost=100_000,
        proposed_annual_cost=95_000,
        annual_savings=5_000,
        upfront_cost=200_000,
        incentives_total=0,
        net_investment=200_000,
        npv=-50_000,
        irr=None,
        simple_payback_years=40.0,
        discounted_payback_years=None,
        sir=0.75,
        analysis_years=20,
        discount_rate=0.03,
        cash_flows=[],
    )


# =============================================================================
# Known Value Fixtures (for validation tests)
# =============================================================================

@pytest.fixture
def known_npv_inputs():
    """Known inputs for NPV validation."""
    return {
        'cash_flows': [-100_000, 15_000, 15_000, 15_000, 15_000, 15_000,
                       15_000, 15_000, 15_000, 15_000, 15_000],
        'discount_rate': 0.05,
        'expected_npv': 15_826.07,  # Hand-calculated
    }


@pytest.fixture
def known_irr_inputs():
    """Known inputs for IRR validation."""
    return {
        'cash_flows': [-50_000, 15_000, 15_000, 15_000, 15_000, 15_000],
        'expected_irr': 0.1524,  # ~15.24%
    }


@pytest.fixture
def known_payback_inputs():
    """Known inputs for payback validation."""
    return {
        'investment': 100_000,
        'annual_savings': 20_000,
        'expected_simple_payback': 5.0,
    }
