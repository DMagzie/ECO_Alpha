# LCCA Scenario Schema Documentation

## Overview

This document defines the data schema for LCCA scenarios, bridging building simulation outputs to financial calculations.

## Core Data Model

### LccaScenario

The top-level container for an LCCA analysis scenario.

```python
@dataclass
class LccaScenario:
    # Identity
    name: str                           # Scenario name (e.g., "Proposed HPWH")
    description: str = ""               # Optional description

    # Capital costs
    capex_upfront: float               # Initial capital expenditure ($)
    capex_breakdown: Dict[str, float]  # Optional breakdown by category

    # Operating costs (annual deltas from baseline)
    opex_annual_delta: float = 0.0     # Operating cost change ($/yr)
    maintenance_annual_delta: float = 0.0  # Maintenance cost change ($/yr)

    # Energy consumption
    energy: EnergyStreams              # Annual energy consumption

    # Rate structure
    tariff: Tariff                     # Utility rates

    # Financial inputs
    incentives: List[Incentive]        # Available incentives
    extra_cashflows: List[CashFlow]    # Additional cash flows

    # Analysis parameters
    assumptions: ScenarioAssumptions   # Financial assumptions
```

### EnergyStreams

Annual energy consumption by fuel type.

```python
@dataclass
class EnergyStreams:
    # Total consumption
    electricity_kwh: float = 0.0       # Annual electricity (kWh)
    gas_therms: float = 0.0            # Annual natural gas (therms)

    # Demand
    demand_kw: float = 0.0             # Peak demand (kW)

    # Optional breakdown
    cooling_kwh: float = 0.0           # Cooling electricity
    heating_kwh: float = 0.0           # Heating electricity
    heating_therm: float = 0.0         # Heating gas
    fans_kwh: float = 0.0              # Fan electricity
    pumps_kwh: float = 0.0             # Pump electricity
    lighting_kwh: float = 0.0          # Lighting
    plugs_kwh: float = 0.0             # Plug loads
    dhw_kwh: float = 0.0               # DHW electricity
    dhw_therm: float = 0.0             # DHW gas

    # Generation
    pv_generation_kwh: float = 0.0     # PV generation
    net_electricity_kwh: float = 0.0   # Net after PV
```

### Tariff

Utility rate structure for cost calculations.

```python
@dataclass
class Tariff:
    name: str = ""                     # Rate schedule name
    utility: str = ""                  # Utility company

    # Simple rates
    elec_rate_per_kwh: float = 0.25    # $/kWh (blended)
    gas_rate_per_therm: float = 1.80   # $/therm
    demand_rate_per_kw: float = 18.0   # $/kW-month

    # TOU rates (optional)
    tou_enabled: bool = False
    on_peak_rate: float = 0.35         # $/kWh on-peak
    mid_peak_rate: float = 0.25        # $/kWh mid-peak
    off_peak_rate: float = 0.15        # $/kWh off-peak

    # TOU schedule
    on_peak_hours: List[int] = None    # Hours 0-23 for on-peak
    mid_peak_hours: List[int] = None   # Hours 0-23 for mid-peak
    weekend_off_peak: bool = True      # All weekend hours off-peak

    # Demand tiers
    demand_tiers: List[DemandTier] = None
```

### ScenarioAssumptions

Financial parameters for LCCA calculations.

```python
@dataclass
class ScenarioAssumptions:
    # Analysis period
    analysis_years: int = 20           # Study period (years)

    # Discount rates
    discount_rate_real: float = 0.03   # Real discount rate
    discount_rate_nominal: float = 0.055  # Nominal (includes inflation)

    # Inflation
    inflation_rate: float = 0.025      # General inflation
    elec_escalation: float = 0.02      # Electricity price escalation
    gas_escalation: float = 0.015      # Gas price escalation

    # Tax
    tax_rate: float = 0.0              # Marginal tax rate
    depreciation_years: int = 0        # MACRS depreciation period

    # End of study
    salvage_value: float = 0.0         # Residual value at end
    salvage_percentage: float = 0.0    # Or as % of CAPEX

    # Carbon pricing (optional)
    include_carbon_costs: bool = False
    carbon_price_per_ton: float = 0.0  # $/ton CO2
    elec_carbon_intensity: float = 0.0 # tons CO2/MWh
    gas_carbon_intensity: float = 0.0  # tons CO2/therm
```

### Incentive

Financial incentives (rebates, tax credits, etc.).

```python
@dataclass
class Incentive:
    name: str                          # Incentive name
    amount: float                      # Value ($)
    pays_in_year: int = 0              # Year received (0 = upfront)

    # Incentive type
    type: str = "rebate"               # rebate, tax_credit, grant, loan

    # Conditions
    requires_permit: bool = False
    requires_inspection: bool = False
    expiration_date: str = ""          # YYYY-MM-DD

    # Calculation method (for variable incentives)
    per_unit: float = 0.0              # $/unit
    unit_type: str = ""                # kW, kWh, ton, SF, etc.
    cap: float = 0.0                   # Maximum incentive
```

### CashFlow

Individual cash flow entry for custom modeling.

```python
@dataclass
class CashFlow:
    year: int                          # Year of cash flow
    amount: float                      # Value (+ = income, - = expense)
    label: str = ""                    # Description
    category: str = ""                 # capital, operating, incentive, etc.
    recurring: bool = False            # Repeats annually if True
```

---

## Calculated Outputs

### LccaResults

Results from LCCA calculation.

```python
@dataclass
class LccaResults:
    # Primary metrics
    npv: float                         # Net Present Value ($)
    irr: float                         # Internal Rate of Return (%)
    simple_payback: float              # Simple payback (years)
    discounted_payback: float          # Discounted payback (years)

    # Additional metrics
    sir: float                         # Savings-to-Investment Ratio
    roi: float                         # Return on Investment (%)
    lcoe: float                        # Levelized Cost of Energy ($/kWh)

    # Annual breakdown
    annual_cashflows: List[float]      # Cash flow by year
    cumulative_cashflows: List[float]  # Cumulative cash flow

    # Cost breakdown
    total_lifecycle_cost: float        # Total LCC ($)
    energy_cost_savings: float         # Energy savings PV ($)
    incentive_value: float             # Incentive PV ($)
    maintenance_savings: float         # Maintenance savings PV ($)

    # Carbon metrics (optional)
    carbon_reduction_tons: float       # Lifetime CO2 reduction
    carbon_value: float                # Carbon value PV ($)
    carbon_payback: float              # Carbon payback (years)
```

---

## JSON Schema

For data interchange, the schema is represented as JSON:

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "LCCA Scenario",
  "type": "object",
  "required": ["name", "capex_upfront", "energy"],
  "properties": {
    "name": {"type": "string"},
    "capex_upfront": {"type": "number", "minimum": 0},
    "opex_annual_delta": {"type": "number", "default": 0},
    "maintenance_annual_delta": {"type": "number", "default": 0},
    "energy": {
      "type": "object",
      "properties": {
        "electricity_kwh": {"type": "number"},
        "gas_therms": {"type": "number"},
        "demand_kw": {"type": "number"}
      }
    },
    "tariff": {
      "type": "object",
      "properties": {
        "elec_rate_per_kwh": {"type": "number", "default": 0.25},
        "gas_rate_per_therm": {"type": "number", "default": 1.80},
        "demand_rate_per_kw": {"type": "number", "default": 18.0}
      }
    },
    "incentives": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["name", "amount"],
        "properties": {
          "name": {"type": "string"},
          "amount": {"type": "number"},
          "pays_in_year": {"type": "integer", "default": 0}
        }
      }
    },
    "assumptions": {
      "type": "object",
      "properties": {
        "analysis_years": {"type": "integer", "default": 20},
        "discount_rate_real": {"type": "number", "default": 0.03},
        "inflation_rate": {"type": "number", "default": 0.025}
      }
    }
  }
}
```

---

## Integration with EMJSON v6

The LCCA schema can extend EMJSON v6 as an optional module:

```json
{
  "emjson_version": "6.1",
  "project": { ... },
  "building": { ... },
  "zones": [ ... ],
  "hvac_systems": [ ... ],

  "lcca": {
    "scenarios": [
      {
        "name": "Proposed",
        "capex_upfront": 1200000,
        "energy": {
          "electricity_kwh": 850000,
          "gas_therms": 15000,
          "demand_kw": 450
        },
        "tariff": { ... },
        "incentives": [ ... ]
      },
      {
        "name": "Baseline",
        "capex_upfront": 600000,
        "energy": { ... }
      }
    ],
    "comparison": {
      "proposed_vs_baseline": {
        "npv": 245000,
        "irr": 0.125,
        "simple_payback": 6.5
      }
    }
  }
}
```
