"""
Ventura & 7th Scenario Analysis
===============================

LCCA scenario comparison for Ventura & 7th affordable housing project.

Scenarios:
1. Baseline (Maestro): Central ventilation + Maestro minisplit heat pumps
2. Ephoca + Maestros: Individual ERVs with heat recovery + Ephoca + Maestro units
3. Ephoca Min Ventilation: Individual ERVs + Ephoca only (minimum equipment)

ECM Categories:
- HVAC: Ephoca integrated heat pump units vs Maestro minisplits
- Ventilation: Central supply vs individual ERVs with heat recovery
- Heat Recovery: 67% SRE / 72% ASRE on ventilation air

Project Details:
- Location: Fresno, CA (Climate Zone 13)
- Building: 4-story multifamily, 40 dwelling units
- DU Mix: 12x1BR, 14x2BR, 14x3BR
- PV: 302 kWdc
- DHW: Central HPWH (tenants don't pay)
- Utility: PG&E Rate EM with VNEM2

Usage:
    python ventura_7th_analysis.py

Requirements:
    - Run CBECC simulations for all three scenarios first
    - Place HourlyResults CSVs in respective - run/ folders
"""

import sys
from pathlib import Path
from dataclasses import dataclass
from typing import Dict, Optional

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from eco_tools.lcca import (
    ScenarioManager,
    ECMBundle,
    ECM,
    ECMCategory,
    TouTariff,
    TouSchedule,
    TouRates,
    DemandRates,
)


# ============================================================================
# Project Configuration
# ============================================================================

PROJECT_NAME = "Ventura & 7th Apartments"
LOCATION = "Fresno, CA"
CLIMATE_ZONE = 13

# Building parameters
BUILDING_AREA_SF = 51_281  # Total building area (DU + common)
DWELLING_UNIT_AREA_SF = 48_023  # DU area only (from CBECC model)
COMMON_AREA_SF = 3_258
NUM_UNITS = 54
NUM_STORIES = 4

# Unit mix (from CBECC model with zone multipliers)
# L01: 4+4+4=12, L02-03: (4+5+5)*2=28, L04: 4+5+5=14 = 54 total
UNIT_MIX = {
    1: {"count": 16, "area_sf": 554},   # 1BR (4+4*2+4=16)
    2: {"count": 19, "area_sf": 807},   # 2BR (4+5*2+5=19)
    3: {"count": 19, "area_sf": 1254},  # 3BR (4+5*2+5=19)
}

# PV system
PV_CAPACITY_KW = 350  # kWdc (same across all scenarios)
PV_COST_PER_WATT = 2.50  # Estimated installed cost

# Analysis parameters
ANALYSIS_YEARS = 25
DISCOUNT_RATE = 0.03
INFLATION_RATE = 0.025
UTILITY_ESCALATION = 0.04


# ============================================================================
# Scenario File Paths
# ============================================================================

BASE_PATH = Path(__file__).parent

SCENARIOS = {
    "baseline": {
        "name": "Baseline (Maestro)",
        "description": "Central ventilation + Maestro minisplit heat pumps",
        "cibd_file": BASE_PATH / "Maestro" / "Ventura and 7th Updated Maestro.cibd22",
        "run_folder": None,  # Set after simulation
        "hvac_system": "Maestro Olimpia Pro12",
        "ventilation": "Central Supply",
        "heat_recovery": False,
    },
    "ephoca_maestro": {
        "name": "Ephoca + Maestros",
        "description": "Individual ERVs with heat recovery + Ephoca + Maestro units",
        "cibd_file": BASE_PATH / "Ephoca + Maestros" / "Ventura and 7th One Ephoca + Maestros.cibd22",
        "run_folder": None,
        "hvac_system": "Ephoca + Maestro",
        "ventilation": "Individual ERV",
        "heat_recovery": True,
    },
    "ephoca_min": {
        "name": "Ephoca Min Ventilation",
        "description": "Individual ERVs + Ephoca only (minimum ventilation)",
        "cibd_file": BASE_PATH / "Ephoca Min Ventilation" / "Ventura and 7th Ephoca Min Ventilation.cibd22",
        "run_folder": None,
        "hvac_system": "Ephoca Only",
        "ventilation": "Individual ERV",
        "heat_recovery": True,
    },
}


# ============================================================================
# Utility Tariff Configuration
# ============================================================================

def create_pge_rate_em_vnem() -> TouTariff:
    """
    Create PG&E Rate EM (Master-Metered Multifamily) with VNEM2.

    Territory R (Fresno area)
    Applicable to affordable housing with virtual net metering.
    """
    schedule = TouSchedule(
        name="PG&E Rate EM (VNEM2)",
        summer_months=[6, 7, 8, 9],  # June-September
        # Peak: 4pm-9pm weekdays
        summer_on_peak=[(16, 21)],
        summer_mid_peak=[],
        summer_off_peak=[],
        winter_on_peak=[],
        winter_mid_peak=[(16, 21)],
        winter_off_peak=[],
        weekend_all_off_peak=True,
    )

    # CARE/VNEM rates (estimated based on E-TOU-C CARE structure)
    # These are approximate - should be updated with actual Rate EM values
    energy_rates = TouRates(
        summer_on_peak=0.35,      # Peak (4-9pm)
        summer_mid_peak=0.25,     # Partial-peak
        summer_off_peak=0.18,     # Off-peak
        winter_on_peak=0.28,      # Winter peak
        winter_mid_peak=0.22,     # Winter partial-peak
        winter_off_peak=0.16,     # Winter off-peak
    )

    # Master-metered buildings typically have lower demand charges
    demand_rates = DemandRates(
        facility_charge=0.0,
        summer_on_peak=8.00,
        summer_mid_peak=0.0,
        winter_on_peak=0.0,
        winter_mid_peak=0.0,
    )

    return TouTariff(
        name="Rate EM Code B (VNEM2)",
        utility="Pacific Gas & Electric",
        schedule=schedule,
        energy_rates=energy_rates,
        demand_rates=demand_rates,
        gas_rate=0.0,  # All-electric
        monthly_customer_charge=15.00,
    )


# ============================================================================
# Equipment Cost Constants (Researched Dec 2024)
# See equipment_cost_analysis.md for sources and details
# ============================================================================

MAESTRO_UNIT_COST = 4_799          # Olimpia Splendid Maestro Pro 12 HP
EPHOCA_WITH_ERV_COST = 6_605       # Ephoca AIO Wall Mount Pro with ERV
EPHOCA_BASE_COST = 4_188           # Ephoca without ERV module
ERV_MODULE_COST = 2_417            # ERV module premium
CENTRAL_VENT_SYSTEM_COST = 30_000  # Total central supply ventilation system
CENTRAL_VENT_PER_UNIT = 750        # Allocated per dwelling unit
INSTALLATION_PER_UNIT = 875        # Average installation labor per packaged unit


# ============================================================================
# ECM Definitions
# ============================================================================

def define_ecms() -> ECMBundle:
    """
    Define ECMs for the Ventura & 7th project scenarios.

    ECMs represent the delta between scenarios:
    - Baseline -> Ephoca+Maestro: ERV + heat recovery + Ephoca (both units per DU)
    - Baseline -> Ephoca Min: ERV + heat recovery + Ephoca (replaces Maestro + central vent)

    See equipment_cost_analysis.md for sources and details.
    """
    bundle = ECMBundle(name="Ventura & 7th ECMs")

    # Baseline cost per unit: Maestro + Central Vent
    baseline_per_unit = MAESTRO_UNIT_COST + CENTRAL_VENT_PER_UNIT + INSTALLATION_PER_UNIT
    # = $4,799 + $750 + $875 = $6,424/unit

    # Ephoca Min cost per unit: Ephoca with ERV (replaces both Maestro AND central vent)
    ephoca_min_per_unit = EPHOCA_WITH_ERV_COST + INSTALLATION_PER_UNIT
    # = $6,605 + $875 = $7,480/unit

    # ECM 1: Ephoca Min Ventilation (vs Baseline)
    # Delta: $7,480 - $6,424 = $1,056/unit
    ephoca_min_delta = ephoca_min_per_unit - baseline_per_unit
    ephoca_min_total = ephoca_min_delta * NUM_UNITS  # $1,056 * 40 = $42,240

    bundle.add_ecm(ECM(
        name="Ephoca Min (ERV + Heat Pump)",
        category=ECMCategory.HVAC,
        capex=ephoca_min_total,
        description="Ephoca AIO replaces Maestro + central ventilation",
        useful_life_years=15,
        notes=f"Premium: ${ephoca_min_delta:,.0f}/unit. 67% SRE heat recovery on ventilation.",
    ))

    # ECM 2: Ephoca + Maestros (both units per DU)
    # This scenario has BOTH Ephoca and Maestro in each unit
    ephoca_maestro_per_unit = (EPHOCA_WITH_ERV_COST + MAESTRO_UNIT_COST +
                               (2 * INSTALLATION_PER_UNIT))
    # = $6,605 + $4,799 + $1,750 = $13,154/unit

    # Delta vs baseline: $13,154 - $6,424 = $6,730/unit
    ephoca_maestro_delta = ephoca_maestro_per_unit - baseline_per_unit
    ephoca_maestro_total = ephoca_maestro_delta * NUM_UNITS  # $6,730 * 40 = $269,200

    bundle.add_ecm(ECM(
        name="Ephoca + Maestros (Dual System)",
        category=ECMCategory.HVAC,
        capex=ephoca_maestro_total,
        description="Ephoca ERV + Maestro heat pump per dwelling unit",
        useful_life_years=15,
        notes=f"Premium: ${ephoca_maestro_delta:,.0f}/unit. Maximum capacity and redundancy.",
    ))

    # PV System (already installed in all scenarios)
    pv_capex = PV_CAPACITY_KW * 1000 * PV_COST_PER_WATT

    bundle.add_ecm(ECM(
        name=f"{PV_CAPACITY_KW} kW PV System",
        category=ECMCategory.GENERATION,
        capex=pv_capex,
        annual_kwh_generation=PV_CAPACITY_KW * 1500,  # ~1500 kWh/kW in CZ13
        incentives=[
            {
                "name": "Federal ITC (30%)",
                "amount": pv_capex * 0.30,
                "pays_in_year": 0,
            }
        ],
        description="Rooftop PV system for VNEM allocation",
        useful_life_years=25,
    ))

    return bundle


# ============================================================================
# Cost Breakdown Functions
# ============================================================================

def calculate_scenario_costs() -> Dict[str, dict]:
    """
    Calculate full capital costs for each scenario.

    Returns dict with scenario keys and cost breakdowns.
    """
    costs = {}

    # Baseline (Maestro + Central Ventilation)
    baseline_equipment = MAESTRO_UNIT_COST * NUM_UNITS
    baseline_installation = INSTALLATION_PER_UNIT * NUM_UNITS
    baseline_central_vent = CENTRAL_VENT_SYSTEM_COST
    baseline_total = baseline_equipment + baseline_installation + baseline_central_vent

    costs["baseline"] = {
        "name": "Baseline (Maestro)",
        "maestro_units": NUM_UNITS,
        "maestro_cost": baseline_equipment,
        "ephoca_units": 0,
        "ephoca_cost": 0,
        "central_vent": baseline_central_vent,
        "installation": baseline_installation,
        "total": baseline_total,
        "per_unit": baseline_total / NUM_UNITS,
        "delta_vs_baseline": 0,
    }

    # Ephoca + Maestros (Dual system, no central vent)
    em_maestro_cost = MAESTRO_UNIT_COST * NUM_UNITS
    em_ephoca_cost = EPHOCA_WITH_ERV_COST * NUM_UNITS
    em_installation = INSTALLATION_PER_UNIT * NUM_UNITS * 2  # Two units per DU
    em_total = em_maestro_cost + em_ephoca_cost + em_installation

    costs["ephoca_maestro"] = {
        "name": "Ephoca + Maestros",
        "maestro_units": NUM_UNITS,
        "maestro_cost": em_maestro_cost,
        "ephoca_units": NUM_UNITS,
        "ephoca_cost": em_ephoca_cost,
        "central_vent": 0,
        "installation": em_installation,
        "total": em_total,
        "per_unit": em_total / NUM_UNITS,
        "delta_vs_baseline": em_total - baseline_total,
    }

    # Ephoca Min (Single system, no central vent)
    emin_ephoca_cost = EPHOCA_WITH_ERV_COST * NUM_UNITS
    emin_installation = INSTALLATION_PER_UNIT * NUM_UNITS
    emin_total = emin_ephoca_cost + emin_installation

    costs["ephoca_min"] = {
        "name": "Ephoca Min",
        "maestro_units": 0,
        "maestro_cost": 0,
        "ephoca_units": NUM_UNITS,
        "ephoca_cost": emin_ephoca_cost,
        "central_vent": 0,
        "installation": emin_installation,
        "total": emin_total,
        "per_unit": emin_total / NUM_UNITS,
        "delta_vs_baseline": emin_total - baseline_total,
    }

    return costs


def print_cost_breakdown():
    """Print detailed cost breakdown for all scenarios."""
    costs = calculate_scenario_costs()

    print("=" * 90)
    print("SCENARIO COST BREAKDOWN")
    print("=" * 90)
    print()

    # Equipment pricing summary
    print("EQUIPMENT PRICING (Dec 2024)")
    print("-" * 50)
    print(f"  Maestro Olimpia Pro 12 HP:    ${MAESTRO_UNIT_COST:>8,}")
    print(f"  Ephoca AIO w/ERV:             ${EPHOCA_WITH_ERV_COST:>8,}")
    print(f"  Central Ventilation System:   ${CENTRAL_VENT_SYSTEM_COST:>8,} (total)")
    print(f"  Installation per unit:        ${INSTALLATION_PER_UNIT:>8,}")
    print()

    # Detailed breakdown per scenario
    for key in ["baseline", "ephoca_min", "ephoca_maestro"]:
        c = costs[key]
        print(f"{c['name'].upper()}")
        print("-" * 50)
        if c["maestro_cost"] > 0:
            print(f"  Maestro units ({c['maestro_units']}):          ${c['maestro_cost']:>12,}")
        if c["ephoca_cost"] > 0:
            print(f"  Ephoca w/ERV ({c['ephoca_units']}):            ${c['ephoca_cost']:>12,}")
        if c["central_vent"] > 0:
            print(f"  Central Ventilation:           ${c['central_vent']:>12,}")
        print(f"  Installation:                  ${c['installation']:>12,}")
        print(f"  {'─' * 36}")
        print(f"  TOTAL:                         ${c['total']:>12,}")
        print(f"  Per Unit:                      ${c['per_unit']:>12,.0f}")
        if c["delta_vs_baseline"] != 0:
            sign = "+" if c["delta_vs_baseline"] > 0 else ""
            print(f"  Delta vs Baseline:             {sign}${c['delta_vs_baseline']:>11,}")
        print()

    # Summary table
    print("=" * 90)
    print("SUMMARY COMPARISON")
    print("=" * 90)
    print()
    print(f"{'Scenario':<25} {'Total CapEx':>15} {'Per Unit':>12} {'Delta':>15}")
    print("-" * 70)
    for key in ["baseline", "ephoca_min", "ephoca_maestro"]:
        c = costs[key]
        delta_str = "—" if c["delta_vs_baseline"] == 0 else f"+${c['delta_vs_baseline']:,}"
        print(f"{c['name']:<25} ${c['total']:>14,} ${c['per_unit']:>11,.0f} {delta_str:>15}")
    print()

    # Payback analysis
    print("=" * 90)
    print("SIMPLE PAYBACK REQUIREMENTS")
    print("=" * 90)
    print()
    print("For 15-year equipment life payback:")
    for key in ["ephoca_min", "ephoca_maestro"]:
        c = costs[key]
        if c["delta_vs_baseline"] > 0:
            annual_savings_needed = c["delta_vs_baseline"] / 15
            print(f"  {c['name']:<25} Requires ${annual_savings_needed:,.0f}/year savings")
    print()


# ============================================================================
# Analysis Functions
# ============================================================================

def find_hourly_results(scenario_key: str) -> Optional[Path]:
    """Find HourlyResults CSV for a scenario."""
    scenario = SCENARIOS[scenario_key]
    cibd_file = scenario["cibd_file"]

    if not cibd_file.exists():
        print(f"Warning: CIBD file not found: {cibd_file}")
        return None

    # Look for run folder
    run_folder_patterns = [
        cibd_file.parent / f"{cibd_file.stem} - run",
        cibd_file.parent / f"{cibd_file.stem} - ap - HourlyResults.csv",
    ]

    for pattern in run_folder_patterns:
        if pattern.is_dir():
            hourly_results = list(pattern.glob("*ap*HourlyResults*.csv"))
            if hourly_results:
                return hourly_results[0]
        elif pattern.exists():
            return pattern

    return None


def run_scenario_comparison():
    """
    Run full scenario comparison (requires CBECC simulation results).
    """
    print("=" * 70)
    print(f"VENTURA & 7TH SCENARIO ANALYSIS")
    print(f"Location: {LOCATION} (CZ{CLIMATE_ZONE})")
    print("=" * 70)
    print()

    # Check for simulation results
    results_found = {}
    for key, scenario in SCENARIOS.items():
        hourly_results = find_hourly_results(key)
        results_found[key] = hourly_results
        status = "FOUND" if hourly_results else "NOT FOUND"
        print(f"  {scenario['name']:<30} Results: {status}")

    print()

    if not any(results_found.values()):
        print("ERROR: No simulation results found!")
        print()
        print("Please run CBECC simulations for:")
        for key, scenario in SCENARIOS.items():
            print(f"  - {scenario['cibd_file']}")
        print()
        print("Then re-run this analysis.")
        return

    # Create tariff
    tariff = create_pge_rate_em_vnem()
    print(f"Utility Tariff: {tariff.name}")
    print()

    # Initialize scenario manager
    manager = ScenarioManager(PROJECT_NAME)

    # Load available scenarios
    for key, hourly_path in results_found.items():
        if hourly_path:
            scenario_config = SCENARIOS[key]
            # Load scenario from hourly results
            # (Implementation depends on parse_hourly_results format)
            print(f"Loading: {scenario_config['name']}")

    # Define ECMs
    ecm_bundle = define_ecms()
    print()
    print(ecm_bundle.summary_table())

    # Compare scenarios
    # (Full comparison after loading data)


def print_scenario_summary():
    """Print summary of scenario configurations (no simulation needed)."""
    print("=" * 70)
    print(f"VENTURA & 7TH SCENARIO CONFIGURATION")
    print("=" * 70)
    print()

    print("PROJECT DETAILS")
    print("-" * 40)
    print(f"  Location:        {LOCATION}")
    print(f"  Climate Zone:    {CLIMATE_ZONE}")
    print(f"  Building Area:   {BUILDING_AREA_SF:,} SF")
    print(f"  Dwelling Units:  {NUM_UNITS}")
    print(f"  PV System:       {PV_CAPACITY_KW} kWdc")
    print()

    print("UNIT MIX")
    print("-" * 40)
    for br, info in UNIT_MIX.items():
        print(f"  {br}BR: {info['count']} units @ {info['area_sf']} SF = {info['count']*info['area_sf']:,} SF")
    print(f"  Total: {sum(u['count'] for u in UNIT_MIX.values())} units, {DWELLING_UNIT_AREA_SF:,} SF")
    print()

    print("SCENARIOS")
    print("-" * 40)
    for key, scenario in SCENARIOS.items():
        print(f"\n  [{key}] {scenario['name']}")
        print(f"    {scenario['description']}")
        print(f"    HVAC: {scenario['hvac_system']}")
        print(f"    Ventilation: {scenario['ventilation']}")
        print(f"    Heat Recovery: {'Yes (67% SRE)' if scenario['heat_recovery'] else 'No'}")
        file_exists = "EXISTS" if scenario['cibd_file'].exists() else "NOT FOUND"
        print(f"    File: {file_exists}")

    print()
    print("ECM BUNDLE")
    print("-" * 40)
    ecm_bundle = define_ecms()
    print(ecm_bundle.summary_table())

    print()
    print("NEXT STEPS")
    print("-" * 40)
    print("  1. Run CBECC simulations for all three scenarios")
    print("  2. Ensure HourlyResults CSVs are generated")
    print("  3. Re-run this script for full comparison")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Ventura & 7th Scenario Analysis")
    parser.add_argument("--summary", action="store_true", help="Print scenario summary only")
    parser.add_argument("--costs", action="store_true", help="Print detailed cost breakdown")
    parser.add_argument("--compare", action="store_true", help="Run full comparison (requires simulation results)")

    args = parser.parse_args()

    if args.costs:
        print_cost_breakdown()
    elif args.compare:
        run_scenario_comparison()
    else:
        print_scenario_summary()
