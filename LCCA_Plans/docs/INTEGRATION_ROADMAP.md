# LCCA Integration Roadmap

## Overview

This roadmap outlines the steps to integrate LCCA capabilities with the ECO_Alpha_v7 CBECC translation pipeline.

## Current State

| Component | Status | Location |
|-----------|--------|----------|
| CBECC Model Translation | Production Ready | eco_tools/translators/ |
| Simulation Output Parsing | **NOT STARTED** | - |
| LCCA Calculators | Scaffolded | EM_Projects/v5 Other/lcca_track/ |
| Cost Database | Prototype | SNO/lcca/load_costdb.py |
| ECON-1 Generator | Stub | EM_Projects/v5 Other/lcca_track/econ1/ |

## Sample Data Available

Location: `/Users/DavidM/Dropbox/EM-Tools-Assets/CBECC Models/`

| Project | Type | Size | Status |
|---------|------|------|--------|
| Bressi Ranch | High-Rise Multifamily | 320 units, 310K SF | Has simulation results |
| Del Amo | Commercial | - | Has simulation results |
| Euclid A/B/C | Commercial | - | Has simulation results |
| Freedom | Commercial | - | Has simulation results |
| MPMP3 | Commercial | - | Has simulation results |

---

## Phase 1: Simulation Output Parser

**Goal:** Parse CBECC simulation outputs into a standardized format for LCCA consumption.

### 1.1 CSE Hourly CSV Parser

**Source Files:** `*-CSE.CSV` in run folders

**Format:**
```csv
"Meter","Mon","Day","Hr","Subhr","Tot","Clg","Htg","HPBU","Dhw","DhwBU",...
"MtrElec",1,1,1,"",360.518,0.117,14.222,0.495,0,0,...
"MtrNatGas",1,1,1,"",25.3,0,12.1,0,8.2,5.0,...
```

**Meters:**
- `MtrElec` - Primary electricity (kWh)
- `MtrElec2` - Secondary electricity (kWh)
- `MtrNatGas` - Natural gas (therms)

**End-Use Columns:**
| Column | Description | Units |
|--------|-------------|-------|
| Tot | Total consumption | kWh or therms |
| Clg | Cooling | kWh |
| Htg | Heating | kWh or therms |
| HPBU | Heat pump backup | kWh |
| Dhw | Domestic hot water | kWh or therms |
| DhwBU | DHW backup | kWh or therms |
| DhwMFL | DHW mixed fuel | varies |
| FanC | Cooling fans | kWh |
| FanH | Heating fans | kWh |
| FanV | Ventilation fans | kWh |
| Fan | Other fans | kWh |
| Aux | Auxiliary | kWh |
| Proc | Process | kWh |
| Lit | Lighting | kWh |
| Rcp | Receptacles | kWh |
| Ext | Exterior | kWh |
| Refr | Refrigeration | kWh |
| Dish | Dishwashing | kWh |
| Dry | Clothes drying | kWh or therms |
| Wash | Clothes washing | kWh |
| Cook | Cooking | kWh or therms |
| BT | Battery | kWh |
| PV | PV generation | kWh |

**Tasks:**
- [ ] Create `CseHourlyParser` class
- [ ] Parse MtrElec rows into electricity profile
- [ ] Parse MtrNatGas rows into gas profile
- [ ] Calculate annual totals
- [ ] Calculate peak demand from hourly data
- [ ] Handle proposed vs standard (ap vs ab prefixes)

### 1.2 PVBattery CSV Parser

**Source Files:** `* - PVBattery.csv`

**Key Data:**
- PV array capacity (kWdc)
- Battery capacity (kWh)
- Charge/discharge rates (kW)
- Control type (TOU, etc.)

**Tasks:**
- [ ] Parse PV sizing data
- [ ] Parse battery sizing data
- [ ] Extract prescriptive requirements vs actual design

### 1.3 NRCCPRF XML Parser

**Source Files:** `* - NRCCPRF.xml`

**Key Data:**
- Project info (name, address, climate zone)
- Compliance status (pass/fail)
- TDV margins
- Building characteristics (SF, units, stories)
- PV and battery compliance

**Tasks:**
- [ ] Parse Section_Info for project metadata
- [ ] Parse compliance results
- [ ] Extract TDV values
- [ ] Extract floor areas and unit counts

---

## Phase 2: Standardized Energy Schema

**Goal:** Define a common data structure for energy consumption that bridges simulation outputs to LCCA inputs.

### 2.1 Schema Definition

```python
@dataclass
class HourlyEnergy:
    month: int
    day: int
    hour: int
    elec_total_kwh: float
    gas_total_therm: float
    elec_cooling_kwh: float
    elec_heating_kwh: float
    gas_heating_therm: float
    elec_fans_kwh: float
    elec_lighting_kwh: float
    elec_plugs_kwh: float
    elec_dhw_kwh: float
    gas_dhw_therm: float
    pv_generation_kwh: float
    battery_kwh: float

@dataclass
class AnnualSummary:
    total_elec_kwh: float
    total_gas_therm: float
    peak_demand_kw: float
    pv_generation_kwh: float
    net_elec_kwh: float
    # End-use breakdown
    cooling_kwh: float
    heating_kwh: float
    heating_therm: float
    fans_kwh: float
    lighting_kwh: float
    plugs_kwh: float
    dhw_kwh: float
    dhw_therm: float

@dataclass
class SimulationOutput:
    project_name: str
    climate_zone: str
    building_type: str
    floor_area_sf: float
    proposed: AnnualSummary
    baseline: Optional[AnnualSummary]
    hourly_proposed: List[HourlyEnergy]
    hourly_baseline: Optional[List[HourlyEnergy]]
    pv_capacity_kwdc: float
    battery_capacity_kwh: float
    tdv_proposed: float
    tdv_baseline: float
    compliance_margin: float
```

### 2.2 JSON Schema for Interchange

- [ ] Define JSON schema matching dataclasses
- [ ] Add as optional extension to EMJSON v6
- [ ] Create validation utilities

---

## Phase 3: LCCA Core Integration

**Goal:** Port LCCA calculators into eco_tools and connect to simulation outputs.

### 3.1 Port Existing Calculators

From `EM_Projects/v5 Other/lcca_track/`:
- [ ] `calculators/npv.py` → `eco_tools/lcca/npv.py`
- [ ] `calculators/irr.py` → `eco_tools/lcca/irr.py`
- [ ] `calculators/simple_payback.py` → `eco_tools/lcca/payback.py`
- [ ] `lcca_model.py` → `eco_tools/lcca/model.py`

### 3.2 Connect Simulation to LCCA

```python
def simulation_to_lcca(sim: SimulationOutput, tariff: Tariff) -> LccaScenario:
    """Bridge simulation outputs to LCCA scenario."""
    return LccaScenario(
        name=sim.project_name,
        capex_upfront=0,  # From CostDB
        energy=EnergyStreams(
            electricity_kwh=sim.proposed.net_elec_kwh,
            gas_therms=sim.proposed.total_gas_therm,
            demand_kw=sim.proposed.peak_demand_kw
        ),
        tariff=tariff,
        assumptions=ScenarioAssumptions(...)
    )
```

### 3.3 TOU Rate Calculations

- [ ] Parse TOU schedule (on-peak, mid-peak, off-peak hours)
- [ ] Calculate energy costs by period from hourly data
- [ ] Calculate demand charges from peak analysis

---

## Phase 4: Cost Database Integration

**Goal:** Automate system cost lookups from CostDB.

### 4.1 CostDB Structure

From `SNO/lcca/load_costdb.py`:
```python
{
    "system_costs": DataFrame,      # HVAC system costs by type
    "material_costs": DataFrame,    # Material costs
    "labor_markups": DataFrame,     # Regional labor adjustments
    "escalation": DataFrame         # Cost escalation factors
}
```

### 4.2 Tasks

- [ ] Define CostDB schema
- [ ] Create cost lookup by system type
- [ ] Integrate with EMJSON zone/system data
- [ ] Calculate total CAPEX from model + CostDB

---

## Phase 5: Output Deliverables

### 5.1 ECON-1 PDF

- [ ] Complete ECON-1 form template
- [ ] Populate from LCCA results
- [ ] Generate PDF using reportlab

### 5.2 Excel Dashboard

- [ ] Design dashboard layout
- [ ] Create Excel export with openpyxl
- [ ] Include scenario comparison
- [ ] Add charts for cash flow visualization

### 5.3 ESG Report

- [ ] Define ESG metrics (carbon reduction, etc.)
- [ ] Calculate from simulation data
- [ ] Generate report format

---

## Proposed Module Structure

```
eco_tools/
├── lcca/
│   ├── __init__.py
│   ├── model.py              # LccaScenario, CashFlow, etc.
│   ├── calculators/
│   │   ├── npv.py
│   │   ├── irr.py
│   │   └── payback.py
│   ├── parsers/
│   │   ├── cse_hourly.py     # CSE CSV parser
│   │   ├── pvbattery.py      # PVBattery CSV parser
│   │   └── nrccprf.py        # NRCCPRF XML parser
│   ├── tariffs/
│   │   ├── tou_rates.py      # TOU rate structures
│   │   └── demand.py         # Demand charge calculations
│   ├── costs/
│   │   ├── costdb.py         # CostDB loader
│   │   └── system_costs.py   # System cost lookups
│   ├── reports/
│   │   ├── econ1.py          # ECON-1 PDF generator
│   │   ├── excel.py          # Excel dashboard
│   │   └── esg.py            # ESG report
│   └── bridge.py             # SimulationOutput → LccaScenario
```

---

## Milestones

| Milestone | Description | Dependencies |
|-----------|-------------|--------------|
| M1 | CSE hourly parser working | Sample data |
| M2 | Annual summary calculations | M1 |
| M3 | LCCA calculators ported | - |
| M4 | Simulation → LCCA bridge | M1, M2, M3 |
| M5 | TOU rate calculations | M1 |
| M6 | ECON-1 PDF generation | M4 |
| M7 | Excel dashboard export | M4 |

---

## Next Immediate Steps

1. **Create `eco_tools/lcca/` module structure**
2. **Build CSE hourly parser** with sample Bressi Ranch data
3. **Calculate annual summaries** from parsed hourly data
4. **Port NPV/IRR calculators** from existing scaffold
5. **Create bridge function** connecting simulation to LCCA
