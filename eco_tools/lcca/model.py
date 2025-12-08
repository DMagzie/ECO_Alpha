"""
LCCA data models for energy consumption and financial analysis.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any


@dataclass
class HourlyEnergy:
    """Single hour of energy consumption data."""
    month: int                      # 1-12
    day: int                        # 1-31
    hour: int                       # 1-24

    # Site electricity (kWh)
    elec_total_kwh: float = 0.0
    elec_heating_kwh: float = 0.0
    elec_cooling_kwh: float = 0.0
    elec_fans_kwh: float = 0.0
    elec_pumps_kwh: float = 0.0
    elec_dhw_kwh: float = 0.0
    elec_lighting_kwh: float = 0.0
    elec_receptacle_kwh: float = 0.0
    elec_process_kwh: float = 0.0
    elec_exterior_kwh: float = 0.0

    # Site natural gas (therms, converted from kBtu)
    gas_total_therm: float = 0.0
    gas_heating_therm: float = 0.0
    gas_dhw_therm: float = 0.0
    gas_process_therm: float = 0.0

    # Generation/storage (kWh)
    pv_generation_kwh: float = 0.0
    battery_kwh: float = 0.0        # Positive = discharge, negative = charge

    # TDV and source energy
    tdv_elec: float = 0.0           # kTDV/kWh multiplier
    tdv_gas: float = 0.0            # kTDV/MBtu multiplier
    source_elec: float = 0.0        # kBtu/kWh multiplier
    source_gas: float = 0.0         # kBtu/therm multiplier

    # CO2 emissions
    co2_elec: float = 0.0           # tonnes CO2-e/kWh
    co2_gas: float = 0.0            # tonnes CO2-e/therm

    @property
    def net_elec_kwh(self) -> float:
        """Net electricity after PV generation."""
        return self.elec_total_kwh - self.pv_generation_kwh + self.battery_kwh


@dataclass
class AnnualEnergySummary:
    """Annual rollup of energy consumption for LCCA calculations."""

    # Total consumption
    total_elec_kwh: float = 0.0
    total_gas_therm: float = 0.0

    # Peak demand
    peak_demand_kw: float = 0.0
    peak_demand_month: int = 0
    peak_demand_hour: int = 0

    # Generation
    pv_generation_kwh: float = 0.0
    net_elec_kwh: float = 0.0       # After PV

    # Electric end-use breakdown (kWh)
    cooling_kwh: float = 0.0
    heating_kwh: float = 0.0
    fans_kwh: float = 0.0
    pumps_kwh: float = 0.0
    lighting_kwh: float = 0.0
    receptacle_kwh: float = 0.0
    dhw_elec_kwh: float = 0.0
    process_kwh: float = 0.0
    exterior_kwh: float = 0.0

    # Gas end-use breakdown (therms)
    heating_therm: float = 0.0
    dhw_therm: float = 0.0
    process_therm: float = 0.0

    # TDV totals
    tdv_elec_total: float = 0.0     # Total TDV kBtu for electricity
    tdv_gas_total: float = 0.0      # Total TDV kBtu for gas
    tdv_total: float = 0.0          # Combined TDV

    # Source energy totals
    source_elec_total: float = 0.0  # kBtu
    source_gas_total: float = 0.0   # kBtu
    source_total: float = 0.0

    # CO2 emissions totals
    co2_elec_total: float = 0.0     # tonnes CO2-e
    co2_gas_total: float = 0.0      # tonnes CO2-e
    co2_total: float = 0.0

    # Monthly peaks for demand charges
    monthly_peaks_kw: Dict[int, float] = field(default_factory=dict)


@dataclass
class SimulationOutput:
    """Complete simulation output package for LCCA consumption."""

    # Project identification
    project_name: str = ""
    model_file: str = ""
    run_date: str = ""
    software_version: str = ""

    # Building characteristics
    climate_zone: str = ""
    building_type: str = ""         # HighRiseResidential, Office, etc.
    conditioned_area_sf: float = 0.0
    residential_area_sf: float = 0.0
    nonres_area_sf: float = 0.0

    # Model type
    model_type: str = ""            # "Proposed" or "Standard" (baseline)

    # Annual summaries (combined for single-use, or combined total for mixed-use)
    annual: AnnualEnergySummary = field(default_factory=AnnualEnergySummary)

    # Separate NonRes/Res summaries for mixed-use buildings (None if single-use)
    annual_nonres: Optional[AnnualEnergySummary] = None
    annual_res: Optional[AnnualEnergySummary] = None

    # Hourly data (8760 records) - combined
    hourly: List[HourlyEnergy] = field(default_factory=list)

    # Separate hourly data for mixed-use buildings (None if single-use)
    hourly_nonres: Optional[List[HourlyEnergy]] = None
    hourly_res: Optional[List[HourlyEnergy]] = None

    # PV/Battery system info
    pv_capacity_kwdc: float = 0.0
    battery_capacity_kwh: float = 0.0
    battery_power_kw: float = 0.0

    # Compliance results
    compliance_margin: float = 0.0   # TDV margin vs standard

    @property
    def is_mixed_use(self) -> bool:
        """Check if this is a mixed-use building."""
        return self.residential_area_sf > 0 and self.nonres_area_sf > 0

    @property
    def is_residential_only(self) -> bool:
        """Check if this is residential-only."""
        return self.residential_area_sf > 0 and self.nonres_area_sf == 0

    @property
    def is_nonres_only(self) -> bool:
        """Check if this is nonresidential-only."""
        return self.nonres_area_sf > 0 and self.residential_area_sf == 0


# ---- Financial/LCCA Models ----

@dataclass
class EnergyStreams:
    """Energy consumption inputs for LCCA scenario."""
    electricity_kwh: float = 0.0
    gas_therms: float = 0.0
    demand_kw: float = 0.0

    # Optional breakdown
    cooling_kwh: float = 0.0
    heating_kwh: float = 0.0
    heating_therm: float = 0.0
    dhw_kwh: float = 0.0
    dhw_therm: float = 0.0

    # Generation
    pv_generation_kwh: float = 0.0
    net_electricity_kwh: float = 0.0


@dataclass
class Tariff:
    """Utility rate structure for cost calculations."""
    name: str = ""
    utility: str = ""

    # Simple blended rates
    elec_rate_per_kwh: float = 0.25
    gas_rate_per_therm: float = 1.80
    demand_rate_per_kw: float = 18.0

    # TOU rates (optional)
    tou_enabled: bool = False
    on_peak_rate: float = 0.35
    mid_peak_rate: float = 0.25
    off_peak_rate: float = 0.15

    # Customer charges
    monthly_customer_charge: float = 0.0


@dataclass
class Incentive:
    """Financial incentive (rebate, tax credit, grant)."""
    name: str
    amount: float
    pays_in_year: int = 0           # 0 = upfront
    type: str = "rebate"            # rebate, tax_credit, grant


@dataclass
class CashFlow:
    """Individual cash flow entry."""
    year: int
    amount: float
    label: str = ""
    category: str = ""              # capital, operating, incentive


@dataclass
class ScenarioAssumptions:
    """Financial parameters for LCCA calculations."""
    analysis_years: int = 20
    discount_rate_real: float = 0.03
    inflation_rate: float = 0.025
    elec_escalation: float = 0.02
    gas_escalation: float = 0.015
    tax_rate: float = 0.0
    salvage_value: float = 0.0

    # Carbon pricing (optional)
    include_carbon_costs: bool = False
    carbon_price_per_ton: float = 0.0


@dataclass
class LccaScenario:
    """Complete LCCA scenario for financial analysis."""
    name: str
    capex_upfront: float
    opex_annual_delta: float = 0.0
    maintenance_annual_delta: float = 0.0

    energy: EnergyStreams = field(default_factory=EnergyStreams)
    tariff: Tariff = field(default_factory=Tariff)
    incentives: List[Incentive] = field(default_factory=list)
    extra_cashflows: List[CashFlow] = field(default_factory=list)
    assumptions: ScenarioAssumptions = field(default_factory=ScenarioAssumptions)

    def annual_energy_cost(self) -> float:
        """Calculate annual energy cost."""
        e = self.energy
        t = self.tariff
        elec_cost = e.electricity_kwh * t.elec_rate_per_kwh
        gas_cost = e.gas_therms * t.gas_rate_per_therm
        demand_cost = e.demand_kw * t.demand_rate_per_kw * 12  # Annual
        return elec_cost + gas_cost + demand_cost
