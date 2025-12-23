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


# ---- TOU-Native LCCA Models ----

@dataclass
class TouLccaScenario:
    """
    LCCA scenario using Time-of-Use tariff with hourly data.

    This enables direct TOU cost calculation without converting to flat rates,
    providing more accurate lifecycle cost analysis for buildings with:
    - Solar PV (generation timing matters)
    - Battery storage (arbitrage value)
    - Load shifting potential

    Example:
        >>> scenario = TouLccaScenario(
        ...     name="Proposed with PV",
        ...     hourly_data=parsed_output.hourly,
        ...     tou_tariff=create_sce_tou_gs3(),
        ...     capex_upfront=857500,
        ... )
        >>> annual_cost = scenario.calculate_annual_cost()
    """
    name: str
    hourly_data: List[HourlyEnergy]
    tou_tariff: Any  # TouTariff - forward reference to avoid circular import

    # Capital costs
    capex_upfront: float = 0.0

    # Operating costs (annual deltas vs baseline)
    opex_annual_delta: float = 0.0
    maintenance_annual_delta: float = 0.0

    # Incentives
    incentives: List[Incentive] = field(default_factory=list)

    # Financial assumptions
    assumptions: ScenarioAssumptions = field(default_factory=ScenarioAssumptions)

    # Gas consumption (not in hourly for some models)
    annual_gas_therms: float = 0.0

    # Optional: use net electricity (after PV) vs gross
    use_net_electricity: bool = True

    # Metadata
    building_area_sf: float = 0.0
    building_type: str = ""

    def _convert_hourly_to_usage(self, year: int = 2024) -> List[Any]:
        """Convert HourlyEnergy to HourlyUsage for TOU calculations."""
        from datetime import date
        from .tariffs import HourlyUsage

        usage_list = []
        for h in self.hourly_data:
            # Determine if weekend
            try:
                d = date(year, h.month, h.day)
                is_weekend = d.weekday() >= 5
            except ValueError:
                is_weekend = False

            # Get electricity consumption
            if self.use_net_electricity:
                kwh = h.net_elec_kwh
            else:
                kwh = h.elec_total_kwh

            # Don't count negative (export) as consumption for TOU
            kwh = max(0.0, kwh)

            usage_list.append(HourlyUsage(
                month=h.month,
                day=h.day,
                hour=h.hour,
                kwh=kwh,
                is_weekend=is_weekend
            ))

        return usage_list

    def calculate_tou_breakdown(self) -> Any:
        """
        Calculate detailed TOU cost breakdown.

        Returns:
            TouCostBreakdown with energy, demand, and fixed costs
        """
        from .tariffs import calculate_tou_costs

        usage = self._convert_hourly_to_usage()
        return calculate_tou_costs(usage, self.tou_tariff)

    def calculate_annual_cost(self) -> float:
        """
        Calculate total annual energy cost using TOU rates.

        Returns:
            Annual cost in dollars (electricity TOU + gas)
        """
        breakdown = self.calculate_tou_breakdown()

        # Add gas cost
        gas_cost = self.annual_gas_therms * self.tou_tariff.gas_rate

        return breakdown.total_cost + gas_cost

    def get_annual_kwh(self) -> float:
        """Get total annual kWh consumption."""
        if self.use_net_electricity:
            return sum(max(0, h.net_elec_kwh) for h in self.hourly_data)
        else:
            return sum(h.elec_total_kwh for h in self.hourly_data)

    def get_pv_generation_kwh(self) -> float:
        """Get total annual PV generation."""
        return sum(h.pv_generation_kwh for h in self.hourly_data)

    @classmethod
    def from_simulation_output(
        cls,
        name: str,
        output: "SimulationOutput",
        tou_tariff: Any,
        capex_upfront: float = 0.0,
        use_net_electricity: bool = True,
        assumptions: Optional[ScenarioAssumptions] = None,
        incentives: Optional[List[Incentive]] = None,
    ) -> "TouLccaScenario":
        """
        Create TouLccaScenario from parsed simulation output.

        Args:
            name: Scenario name
            output: Parsed SimulationOutput from HourlyResults
            tou_tariff: TOU tariff to use
            capex_upfront: Capital cost
            use_net_electricity: If True, use net electricity (after PV)
            assumptions: Financial assumptions (uses defaults if None)
            incentives: List of incentives

        Returns:
            Configured TouLccaScenario
        """
        return cls(
            name=name,
            hourly_data=output.hourly,
            tou_tariff=tou_tariff,
            capex_upfront=capex_upfront,
            annual_gas_therms=output.annual.total_gas_therm,
            use_net_electricity=use_net_electricity,
            assumptions=assumptions or ScenarioAssumptions(),
            incentives=incentives or [],
            building_area_sf=output.conditioned_area_sf,
            building_type=output.building_type,
        )
