# LCCA Integration Roadmap

## Overview

This roadmap outlines the steps to integrate LCCA capabilities with the ECO_Alpha_v7 CBECC translation pipeline.

## Current State (Updated December 2024)

| Component | Status | Location |
|-----------|--------|----------|
| CBECC Model Translation | Production Ready | eco_tools/translators/ |
| Simulation Output Parsing | **COMPLETE** | eco_tools/lcca/parsers/ |
| LCCA Calculators | **COMPLETE** | eco_tools/lcca/calculators.py |
| Cost Database | **COMPLETE** | eco_tools/lcca/costdb.py |
| ECON-1 Generator | **COMPLETE** | eco_tools/lcca/econ1.py |
| TOU Rate Engine | **COMPLETE** | eco_tools/lcca/tariffs.py |
| Excel Export | **COMPLETE** | eco_tools/lcca/excel_export.py |
| ESG Reports | **COMPLETE** | eco_tools/lcca/esg_report.py |
| PDF Export | **COMPLETE** | eco_tools/lcca/pdf_export.py |

**See `LCCA_ARCHITECTURE.md` for full module documentation.**

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

| Milestone | Description | Dependencies | Status |
|-----------|-------------|--------------|--------|
| M1 | CSE hourly parser working | Sample data | Complete |
| M2 | Annual summary calculations | M1 | Complete |
| M3 | LCCA calculators ported | - | Complete |
| M4 | Simulation → LCCA bridge | M1, M2, M3 | Complete |
| M5 | TOU rate calculations | M1 | Complete |
| M6 | ECON-1 PDF generation | M4 | Complete |
| M7 | Excel dashboard export | M4 | Complete |
| M8 | Site load calculators | - | **Complete** |
| M9 | Whole-building LCCA schema | M4, M8 | **Complete** |
| M10 | Site load hourly profiles | M8, M5 | **Complete** |
| M11 | Whole-building aggregator | M9, M10 | **Complete** |
| M12 | Abstract SimulationParser | M1 | **Complete** |
| M13 | Configurable reporting modes | M9 | Planned |
| M14 | EnergyPlus parser | M12 | Planned (2026) |

---

---

## Phase 6: Non-Modeled Site Loads Integration

**Goal:** Extend LCCA to include non-modeled site energy loads for whole-building analysis.

**Documentation:** See `SITE_LOAD_INTEGRATION_PLAN.md` for full details.

### 6.1 Problem Statement

CBECC simulations model only zone-level loads (HVAC, interior lighting, DHW, plug loads). Real buildings have significant additional energy consumption from:
- Common area lighting (corridors, stairs, lobbies)
- Parking garage (lighting + ventilation)
- Site/exterior lighting
- Pool and spa systems (pumps + heaters)
- EV charging infrastructure
- Elevators and escalators
- Water system pumps (fire, booster, HW circulator)

### 6.2 Existing Work

Location: `/Users/DavidM/Documents/ECO_Alpha_v7/LCCA Tests/Site Load Calculators/`

| File | Content |
|------|---------|
| `NonRes Common Area Energy Calculator.xlsx` | 14 space types, Title 24 LPD |
| `GBCI Pool Energy Calculator_v01 DRAFT.xlsx` | ENERGY STAR pump curves, DOE heater baselines |
| `Project Name_House Meter Calculation Summary.xlsx` | Integration template |

### 6.3 Implemented Module Structure

```
eco_tools/lcca/
├── whole_building/                     # NEW - Core schema and aggregation
│   ├── __init__.py
│   ├── schema.py                       # WholeBuildingEnergy, EnergyStream, etc.
│   └── aggregator.py                   # Combine modeled + site loads
│
├── site_loads/                         # NEW - Site load calculators
│   ├── __init__.py
│   ├── load_shapes/
│   │   ├── __init__.py
│   │   └── library.py                  # 8760 hourly profile generation
│   ├── calculators/
│   │   ├── __init__.py
│   │   ├── base.py                     # BaseSiteLoadCalculator ABC
│   │   ├── lighting.py                 # Interior, parking, site lighting
│   │   ├── pools.py                    # Pool pump, heater, spa
│   │   ├── vertical_transport.py       # Elevator, escalator
│   │   └── miscellaneous.py            # EV, IT, pumps, trash, generic
│   └── reference_data/                 # For future JSON data files
│
├── parsers/
│   ├── base.py                         # NEW - Abstract SimulationParser
│   └── ... (existing parsers)
```

### 6.4 Implementation Status

- [x] Create `eco_tools/lcca/whole_building/` module with unified schema
- [x] Create `eco_tools/lcca/site_loads/` module structure
- [x] Implement WholeBuildingEnergy, EnergyStream, HourlyRecord data models
- [x] Implement LoadShapeLibrary for 8760 hourly profile generation
- [x] Implement lighting calculator (Title 24 2022 LPD)
- [x] Implement pool/spa calculator (ENERGY STAR + DOE methodology)
- [x] Implement elevator/escalator calculators
- [x] Implement EV charger, IT/telecom, water pump, trash compactor calculators
- [x] Create abstract SimulationParser for engine-agnostic design
- [x] Create WholeBuildingAggregator to combine modeled + site loads
- [ ] Add site load sections to Excel/PDF exports
- [ ] Add comprehensive test suite
- [ ] Migrate reference data from code to JSON files

### 6.5 Key Formulas

```python
# Interior Lighting
kwh = area_sf * lpd_w_sf / 1000 * hours_yr * control * diversity

# Motor/Pump
kwh = hp * 0.746 / efficiency * hours_day * days_yr

# EV Charging
kwh = num_ports * kw_per_port * hours_day * 365

# Pool Heater (Gas)
therms = mbtu_per_sqft_lookup * area * months / efficiency / 100
```

### 6.6 Acceptance Criteria

- Site load calculations match Excel templates within 1%
- LCCA reports show clear modeled vs. site load breakdown
- TOU rates can be applied to site loads (Phase 6.5)
- Existing modeled-only LCCA workflow unchanged

---

## Next Immediate Steps

### Phase 1 Complete (December 2024)
The following core infrastructure is now in place:
- ✅ Whole-building energy schema (`WholeBuildingEnergy`, `EnergyStream`, `HourlyRecord`)
- ✅ Site load calculators (lighting, pools, elevators, EV, IT, pumps, etc.)
- ✅ Load shape library for 8760 hourly profile generation
- ✅ Abstract SimulationParser for CBECC (future EnergyPlus)
- ✅ WholeBuildingAggregator for combining modeled + site loads

### Remaining Work
1. **Add site load sections to Excel export** - Extend excel_export.py
2. **Add site load sections to PDF export** - Extend pdf_export.py
3. **Create test suite** for site load calculators
4. **Migrate reference data to JSON** - Title 24 LPD, pool baselines
5. **Implement EnergyPlus parser** (2026) - For ASHRAE 90.1 support

### Usage Example
```python
from eco_tools.lcca.whole_building import create_whole_building_energy, ReportMode

# Create whole-building energy from simulation + site loads
wbe = create_whole_building_energy(
    simulation_file="project - HourlyResults.csv",
    site_loads_input={
        "interior_lighting": [
            {"area_sf": 5000, "space_type": "corridor"},
            {"area_sf": 1200, "space_type": "lobby"},
        ],
        "elevator": [
            {"num_elevators": 2, "elevator_type": "hydraulic_low_rise"},
        ],
        "pool_pump": [
            {"pool_volume_gal": 50000, "pump_type": "variable_speed"},
        ],
    },
    report_mode=ReportMode.FULL,
)

# Get summary
print(f"Modeled: {wbe.modeled.annual.total_elec_kwh:,.0f} kWh")
print(f"Site Loads: {wbe.site_loads.annual.total_elec_kwh:,.0f} kWh")
print(f"Combined: {wbe.combined.annual.total_elec_kwh:,.0f} kWh")
```
