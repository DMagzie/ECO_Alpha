# LCCA Track - Consolidated Changelog

This document consolidates the development history from all LCCA-related work across the EM-Tools ecosystem.

---

## v0.05 (SNO/lcca - July 2025)

### Working Components
- `generate_econ1.py` - Reads EMJSON model + CostDB Excel, outputs basic ECON-1 summary
- `load_costdb.py` - Loads System Costs, Material Costs, Labor Markups, Escalation from Excel
- `summarize_material_impact.py` - Material impact calculations

### Placeholder Modules
- `cuac_module.py` - CUAC integration stub
- `esg_report_generator.py` - ESG reporting stub
- `financial_metrics_engine.py` - Financial calculations stub
- `write_to_excel.py` - Excel export stub

---

## v0.04 (EM-Tools/v0.4/LCCA_Track - July 2025)

### Planned Features (Not Implemented)
- Full Python-to-Excel integration for LCCA dashboard
- Editable battery dispatch logic (efficiency, capacity, rules)
- Scenario toggle: PV included vs excluded
- SIR, IRR, ROI metrics from processed outputs
- Auto-ingestion of Python CSVs into Excel
- Updated Excel dashboard (LCCA_Tool_v0.04.xlsm)

### Scaffold Created
- Empty folder structure: Scripts/, Inputs/, Outputs/, Reference/, Docs/

---

## v0.03 (EM-Tools/v0.3/LCCA_Track - July 7, 2025)

### Completed
- Created folder structure: `v0.03/` under `LCCA_Track/`
- Added Python scripts:
  - `lcca_main_v0_03.py`
  - `data_parser.py`
  - `battery_dispatch.py`
- Added placeholder scripts for v0.04:
  - `generate_pvwatts_hourly.py`
  - `format_lcca_inputs.py`
- Included input samples and PVWatts outputs in `/Inputs/`
- Exported sample summary output to `/Outputs/`
- Added reference data (cost database, utility rates)
- Deployed file validator script with logging
- Installed Git pre-commit hook for automatic file validation
- Added interim Excel bundle:
  - `LCCA_Tool_v0.03_stub.xlsm`
  - `Battery_Logic_Template.xlsx`
  - `Dashboard_Mockup_v0.03.pdf`

### Deferred to v0.04
- Final Excel dashboard integration and macros
- Dynamic battery override interface
- Scenario comparison logic with savings metrics
- Real-time PVWatts and TDV-linked UI toggles

---

## v0.02 (Deliverables/LCCA - July 2025)

### Added
- Support for additional currencies for cost calculations
- Export reports in PDF format
- Tutorial guide for new users
- Save progress and continue later feature
- Cloud storage integration for backup
- Tooltips for various functions

### Changed
- Improved UI for better navigation
- Updated cost calculation algorithm for accuracy
- Changed default currency to USD
- Revised error messages
- Enhanced performance for faster data processing

### Fixed
- Incorrect cost calculation in certain scenarios
- Login error
- Application crash on large data inputs
- Data loss when switching tabs
- CSV import failures

---

## v0.1 (EM_Projects/v5 Other/lcca_track - August 2025)

### LCCA Automation Starter Package
Core scaffold with runnable components:

**Data Model** (`lcca_model.py`):
- `CashFlow` - year, amount, label
- `ScenarioAssumptions` - analysis_years, discount_rate, inflation, tax, salvage, carbon costs
- `EnergyStreams` - electricity_kwh, gas_therms, demand_kw
- `Tariff` - elec_rate, gas_rate, demand_rate
- `Incentive` - name, amount, pays_in_year
- `LccaScenario` - capex, opex, maintenance, energy, tariff, incentives, assumptions

**Calculators**:
- `npv.py` - Net Present Value calculation
- `irr.py` - Internal Rate of Return (Newton-Raphson)
- `simple_payback.py` - Simple payback period

**CLI** (`lcca_cli.py`):
```bash
python -m lcca.cli.lcca_cli --capex 1000000 --elec-kwh -250000 --discount 0.03 --years 20 --incentive "Utility:100000:1"
```

**Incentives Rules Engine**:
- Context-based evaluation (climate zone, zipcode, building type, area, carbon reduction)
- Provider stubs: NYSERDA, C-PACE

**Outputs**:
- ECON-1 PDF export (reportlab)
- ESG report builder
- CSV export

**Config Presets**:
- `discount_rates.yaml` - federal, commercial, municipal rates
- `inflation.yaml` - general inflation rate
- `tariffs_tou.yaml` - TOU rate structures

---

## Integration Status Summary

| Component | Location | Status |
|-----------|----------|--------|
| LCCA Data Model | v5 Other/lcca_track | Complete |
| NPV/IRR/Payback | v5 Other/lcca_track | Complete |
| CLI Interface | v5 Other/lcca_track | Working |
| Incentives Engine | v5 Other/lcca_track | Stub |
| ECON-1 PDF | v5 Other/lcca_track | Stub |
| Cost Database Loader | SNO/lcca | Working |
| Excel Dashboard | v0.03/v0.04 | Planned |
| Simulation Output Parser | - | **NOT STARTED** |
| EMJSON → LCCA Bridge | - | **NOT STARTED** |
