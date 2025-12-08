# LCCA Module Architecture Report

**Version:** 1.0
**Date:** December 2024
**Status:** Feature Complete (Phases 1-5)

---

## Executive Summary

The LCCA (Life Cycle Cost Analysis) module for ECO Tools provides a complete end-to-end workflow for energy cost analysis, financial evaluation, and sustainability reporting. The module consists of **6,065 lines of Python code** across **13 source files**, with **60 automated tests** providing comprehensive coverage.

---

## 1. Architecture Overview

### 1.1 Module Structure

```
eco_tools/lcca/
├── __init__.py              (228 lines)  - Public API exports
├── model.py                 (262 lines)  - Core data models
├── parsers/
│   ├── __init__.py          (13 lines)   - Parser exports
│   ├── hourly_results.py    (639 lines)  - CBECC HourlyResults CSV parser
│   └── cse_hourly.py        (297 lines)  - CSE hourly CSV parser
├── econ1.py                 (634 lines)  - ECON-1 report generator
├── calculators.py           (589 lines)  - NPV, IRR, payback calculators
├── bridge.py                (333 lines)  - Simulation → LCCA connectors
├── tariffs.py               (690 lines)  - TOU rate engine
├── costdb.py                (654 lines)  - Cost database
├── excel_export.py          (705 lines)  - Excel dashboard export
├── pdf_export.py            (537 lines)  - PDF report generation
└── esg_report.py            (484 lines)  - Carbon/sustainability metrics
```

### 1.2 Data Flow Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         LCCA MODULE DATA FLOW                            │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  SIMULATION OUTPUTS                                                      │
│  ┌──────────────────┐    ┌──────────────────┐                           │
│  │ *-HourlyResults  │    │ *-CSE.CSV        │                           │
│  │ CSV (CBECC)      │    │ (CSE Engine)     │                           │
│  └────────┬─────────┘    └────────┬─────────┘                           │
│           │                       │                                      │
│           ▼                       ▼                                      │
│  ┌─────────────────────────────────────────┐                            │
│  │           PARSERS LAYER                  │                            │
│  │  hourly_results.py  │  cse_hourly.py    │                            │
│  └─────────────────────┬───────────────────┘                            │
│                        │                                                 │
│                        ▼                                                 │
│  ┌─────────────────────────────────────────┐                            │
│  │         CORE DATA MODELS                 │                            │
│  │  SimulationOutput, AnnualEnergySummary   │                            │
│  │  HourlyEnergy (8760 records)            │                            │
│  └─────────────────────┬───────────────────┘                            │
│                        │                                                 │
│           ┌────────────┼────────────┐                                   │
│           ▼            ▼            ▼                                   │
│  ┌────────────┐ ┌────────────┐ ┌────────────┐                          │
│  │  ECON-1    │ │  TOU RATE  │ │   BRIDGE   │                          │
│  │  Reports   │ │  Engine    │ │  Functions │                          │
│  └─────┬──────┘ └─────┬──────┘ └─────┬──────┘                          │
│        │              │              │                                   │
│        │              │              ▼                                   │
│        │              │     ┌────────────────┐                          │
│        │              │     │ LccaScenario   │◄──── CostDB              │
│        │              │     │ + Tariff       │◄──── Incentives          │
│        │              │     └───────┬────────┘                          │
│        │              │             │                                    │
│        │              │             ▼                                    │
│        │              │     ┌────────────────┐                          │
│        │              │     │  CALCULATORS   │                          │
│        │              │     │  NPV, IRR, SIR │                          │
│        │              │     │  Payback       │                          │
│        │              │     └───────┬────────┘                          │
│        │              │             │                                    │
│        ▼              ▼             ▼                                    │
│  ┌───────────────────────────────────────────┐                          │
│  │              OUTPUT LAYER                  │                          │
│  │  ┌─────────┐ ┌─────────┐ ┌─────────┐     │                          │
│  │  │  Excel  │ │   PDF   │ │   ESG   │     │                          │
│  │  │Dashboard│ │ Reports │ │ Reports │     │                          │
│  │  └─────────┘ └─────────┘ └─────────┘     │                          │
│  └───────────────────────────────────────────┘                          │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Component Details

### 2.1 Data Models (`model.py`)

| Class | Purpose | Key Fields |
|-------|---------|------------|
| `HourlyEnergy` | Single hour of consumption | month, day, hour, elec_total_kwh, gas_total_therm, pv_generation_kwh |
| `AnnualEnergySummary` | Annual rollup | total_elec_kwh, total_gas_therm, peak_demand_kw, monthly_peaks_kw |
| `SimulationOutput` | Complete simulation package | project_name, building_type, annual, hourly (8760), pv_capacity_kwdc |
| `EnergyStreams` | LCCA energy inputs | electricity_kwh, gas_therms, demand_kw, pv_generation_kwh |
| `Tariff` | Simple utility rates | elec_rate_per_kwh, gas_rate_per_therm, demand_rate_per_kw |
| `LccaScenario` | Complete LCCA scenario | name, capex_upfront, energy, tariff, incentives, assumptions |
| `ScenarioAssumptions` | Financial parameters | analysis_years, discount_rate_real, elec_escalation |
| `Incentive` | Rebates/credits | name, amount, pays_in_year, type |
| `CashFlow` | Annual cash flow entry | year, amount, label, category |

### 2.2 Parsers (`parsers/`)

#### HourlyResults Parser
- Parses CBECC `*-HourlyResults.csv` files
- **Mixed-use building support**: Separates NonRes and Res data streams
- Extracts: electricity, gas, TDV, source energy, CO2 emissions
- Handles proposed ("ap" prefix) and baseline ("ab" prefix) runs

#### CSE Hourly Parser
- Parses CSE engine `*-CSE.CSV` output
- Handles MtrElec, MtrElec2, MtrNatGas meters
- Converts gas from kBtu to therms
- End-use breakdown: Clg, Htg, Fan, Lit, Rcp, DHW, etc.

### 2.3 ECON-1 Reports (`econ1.py`)

| Feature | Description |
|---------|-------------|
| `ReportMode.GROSS` | Consumption only (no PV/battery credits) |
| `ReportMode.NET` | Net consumption (with PV/battery) |
| `ReportMode.DETAILED` | Shows both gross and net with full breakdown |
| `ReportOptions` | Toggle PV, battery, end-use breakdown, mixed-use |
| Export formats | Text (`.txt`), CSV (`.csv`) |

### 2.4 Financial Calculators (`calculators.py`)

| Function | Algorithm | Notes |
|----------|-----------|-------|
| `calculate_npv()` | Standard DCF | NPV = -I₀ + Σ(CFₜ / (1+r)ᵗ) |
| `calculate_irr()` | Newton-Raphson + bisection fallback | Rate where NPV=0 |
| `calculate_simple_payback()` | Investment / Annual Savings | Years to recoup |
| `calculate_discounted_payback()` | Cumulative PV of cash flows | With time value |
| `calculate_sir()` | PV(Savings) / Net Investment | FEMP standard metric |
| `run_lcca()` | Complete analysis | Returns `LccaResults` |

### 2.5 TOU Rate Engine (`tariffs.py`)

| Component | Purpose |
|-----------|---------|
| `TouSchedule` | Define peak periods by hour/month |
| `TouRates` | Energy rates by period ($/kWh) |
| `DemandRates` | Demand charges by period ($/kW) |
| `calculate_tou_costs()` | Process 8760 hourly data |
| Pre-built tariffs | SCE TOU-GS-3, PG&E B-20, SDG&E AL-TOU |

### 2.6 Cost Database (`costdb.py`)

| Category | Systems Included |
|----------|------------------|
| Cooling | Chillers (air/water), DX, VRF, PTAC/PTHP |
| Heating | Boilers (gas/electric), furnaces, heat pumps |
| Distribution | VAV boxes, fan coils, ductwork |
| DHW | Gas, electric, heat pump water heaters |
| Renewables | PV (rooftop/carport), battery storage |
| Controls | BMS, thermostats |
| Regional factors | Los Angeles, San Francisco, San Diego, Sacramento |

### 2.7 Export Modules

| Module | Output | Requirements |
|--------|--------|--------------|
| `excel_export.py` | `.xlsx` with charts | openpyxl (included) |
| `pdf_export.py` | Formatted PDF | reportlab (optional) |
| `esg_report.py` | Carbon footprint, EUI | None |

---

## 3. Testing Summary

### 3.1 Test Coverage

| Test Class | Tests | Coverage Area |
|------------|-------|---------------|
| `TestHourlyResultsParser` | 5 | Parsing, data structure, TDV, peak demand |
| `TestMixedUseParsing` | 5 | Mixed-use buildings, NonRes/Res separation |
| `TestCseHourlyParser` | 3 | CSE format, gas conversion, meter combination |
| `TestParserComparison` | 3 | Cross-validation between parsers |
| `TestSimulationOutput` | 3 | Data model defaults, net calculations |
| `TestEcon1Report` | 7 | Energy costs, site energy, report generation |
| `TestLccaCalculators` | 8 | NPV, IRR, payback, SIR calculations |
| `TestLccaScenarios` | 2 | Full LCCA runs, incentive handling |
| `TestLccaBridge` | 3 | Simulation→LCCA conversion |
| `TestTouTariffs` | 5 | Schedule detection, tariff creation, TOU costs |
| `TestCostDatabase` | 7 | Cost lookups, regional factors, escalation |
| `TestExcelExport` | 2 | LCCA and ECON-1 Excel generation |
| `TestEsgReport` | 7 | Carbon footprint, EUI, renewable %, formatting |
| **Total** | **60** | |

### 3.2 Test Execution

```bash
$ python3 -m pytest tests/test_lcca_parsers.py -v
============================== 60 passed in 1.77s ==============================
```

---

## 4. Known Limitations

| Limitation | Impact | Mitigation |
|------------|--------|------------|
| No NRCCPRF XML parser | Missing compliance margin details | Use HourlyResults for TDV data |
| No PVBattery CSV parser | Battery sizing from separate source | PV capacity in SimulationOutput |
| Flat demand rates only | TOU demand requires hourly data | Use `calculate_tou_costs()` for TOU |
| Regional factors are estimates | May not match actual local costs | User can override in CostDatabase |
| PDF requires reportlab | Optional dependency | Excel export always available |

---

## 5. API Quick Reference

### Primary Entry Points

```python
# Parse simulation data
from eco_tools.lcca.parsers import parse_hourly_results
sim = parse_hourly_results("/path/to/HourlyResults.csv")

# Generate ECON-1 report
from eco_tools.lcca import generate_econ1, Tariff
tariff = Tariff(elec_rate_per_kwh=0.22, gas_rate_per_therm=1.85)
econ1 = generate_econ1(sim, tariff)

# Run full LCCA
from eco_tools.lcca import run_simulation_lcca, ScenarioAssumptions
results = run_simulation_lcca(proposed, baseline, tariff, capital_cost=100000)

# Calculate TOU costs
from eco_tools.lcca import create_sce_tou_gs3, calculate_tou_costs
tariff = create_sce_tou_gs3()
breakdown = calculate_tou_costs(hourly_usage, tariff)

# Export to Excel
from eco_tools.lcca import export_lcca_to_excel
export_lcca_to_excel(results, "lcca_report.xlsx")

# Generate ESG report
from eco_tools.lcca import generate_esg_report, format_esg_report
esg = generate_esg_report(proposed, baseline)
print(format_esg_report(esg))
```

---

## 6. Phase Completion Status

| Phase | Components | Status |
|-------|------------|--------|
| **Phase 1** | HourlyResults parser, CSE parser, Mixed-use support | ✅ Complete |
| **Phase 2** | Data models (HourlyEnergy, SimulationOutput) | ✅ Complete |
| **Phase 3** | NPV, IRR, Payback, SIR calculators, Bridge functions | ✅ Complete |
| **Phase 4** | TOU rate engine, Cost database, Regional factors | ✅ Complete |
| **Phase 5** | Excel dashboard, PDF export, ESG reports | ✅ Complete |

---

## 7. Dependencies

### Required
- Python 3.9+
- openpyxl (Excel export)

### Optional
- reportlab (PDF export) - `pip install reportlab`

---

## 8. File Locations

| Resource | Path |
|----------|------|
| Source code | `eco_tools/lcca/` |
| Tests | `tests/test_lcca_parsers.py` |
| Planning docs | `LCCA_Plans/` |
| Sample data | `reference_data/cbecc/CBECC Models/` |
| Dropbox data | `/Users/DavidM/Dropbox/EM-Tools-Assets/CBECC Models/` |
