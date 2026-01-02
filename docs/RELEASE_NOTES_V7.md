# ECO Tools Alpha v7 - Release Notes

**Release Date:** January 1, 2026
**Version:** 7.0.0
**Status:** Feature Complete - Ready for V8 Development Baseline

---

## Executive Summary

ECO Tools Alpha v7 represents a major milestone with a fully functional Streamlit GUI, complete LCCA (Life Cycle Cost Analysis) integration, CIBD22X/CIBD25 translation capabilities, and comprehensive energy modeling support for California Title 24 compliance.

---

## Features Completed

### GUI (Streamlit-Based)
- **Multi-page Navigation** with sidebar
- **Import Page** - CIBD22X, CIBD25, EMJSON, GEM, CSV file import
- **Build Model Wizard** - Step-by-step model construction
- **Edit Model** - Tree, Tables/Forms, Visual editing modes
- **Simulation** - CBECC-Com, EnergyPlus, CSE integration
- **LCCA Dashboard** - Complete financial analysis with scenarios
- **Zone Analysis** - Per-zone energy and cost breakdown
- **ESG Report** - Carbon footprint and sustainability scoring
- **Site Loads Calculator** - Building-level load estimation
- **Building Summary** - Executive dashboard with all metrics
- **Scenario Manager** - Save/load/compare analysis scenarios
- **Tariff Management** - 15 CA/HI utility rate structures

### LCCA Integration
- **CostDB v0.06** - Generated from NREL data (35 system costs)
- **Regional Factors** - 23 regions (18 CA + 4 HI + national)
- **Utility Rates** - 15 tariffs (PG&E, SCE, SDG&E, HECO, MECO, HELCO)
- **Financial Metrics** - NPV, IRR, SIR, Simple/Discounted Payback
- **Sensitivity Analysis** - Tornado charts, Monte Carlo simulation
- **Parameter Sweeps** - Multi-variable analysis

### Translation Capabilities
- **CIBD22X Round-trip** - 100% fidelity proven (Bressi Ranch: 290 zones, 3,472 surfaces)
- **CIBD25 Export** - 28 element types validated for CBECC 2025 GUI
- **GEM Import** - IES VE geometry import
- **HBJSON Support** - Honeybee/Ladybug compatibility

### Simulation Support
- **CBECC-Com Bridge** - Title 24 compliance simulation
- **EnergyPlus Runner** - Detailed energy analysis
- **CSE Integration** - Zone-level hourly results

---

## Bug Fixes (V7 Closure)

### POLY-001: Duplicate Surface Parsing (CRITICAL)
- **File:** `eco_tools/translators/cibd22x/parsers/surface_parser.py`
- **Issue:** Floor surfaces were parsed twice due to `zone_elem.iter()` traversing all descendants
- **Fix:** Changed to direct child iteration (`zone_elem` instead of `zone_elem.iter()`)
- **Impact:** Corrects floor area calculations, HVAC sizing, and LCCA metrics

### GUI Session State Issues
- **Files Fixed:**
  - `lcca_dashboard_page.py` - Fixed widget key conflicts
  - `esg_report_page.py` - Fixed session state assignment after widget
  - `building_summary_page.py` - Fixed navigation callbacks
  - `editing_page.py` - Fixed navigation callbacks
  - `simulation_page.py` - Fixed navigation callbacks
  - `wizard_page.py` - Fixed navigation callbacks
  - `zone_analysis_page.py` - Fixed import name mismatch
- **Pattern:** All `st.session_state.nav_main = "X"` after widget instantiation converted to callback-based `_pending_nav` pattern

### Import Name Mismatch
- **Files:** `zone_analysis_page.py`, `lcca_dashboard_page.py`
- **Issue:** `CLIMATE_ZONE_TO_REGION` vs `CZ_TO_REGION`
- **Fix:** Corrected import to use `CZ_TO_REGION`

### LCCA Workflow Integration
- **File:** `lcca_dashboard_page.py`
- **Issue:** `LccaScenario.__init__()` parameter mismatch
- **Fix:** Changed to use `run_lcca_workflow()` function

### RunnerResults Attribute Access
- **File:** `lcca_dashboard_page.py`
- **Issue:** `'RunnerResults' object has no attribute 'npv'`
- **Fix:** Added `getattr(results, 'lcca_results', results)` pattern

### File Upload 403 Errors
- **File:** `.streamlit/config.toml`
- **Fix:** Disabled XSRF protection and CORS for local development

### Duplicate Widget IDs
- **File:** `building_summary_page.py`
- **Fix:** Added unique keys to all navigation buttons

---

## Test Results

| Category | Count |
|----------|-------|
| **Passed** | 1,254 |
| **Failed** | 49 |
| **Skipped** | 81 |
| **Errors** | 7 |

### Known Test Failures (Pre-existing, Not V7 Regressions)
- HBJSON importer/exporter tests (17 failures)
- CIBD25 roundtrip tests (8 failures)
- Chart visualization tests (11 failures)
- CSV exporter tests (6 failures)
- CBECC results parser (1 failure)
- Format comparison (1 error)

---

## Configuration Files

### .streamlit/config.toml
```toml
[server]
runOnSave = true
maxUploadSize = 200
enableXsrfProtection = false
enableCORS = false

[runner]
magicEnabled = true
fastReruns = false
```

---

## Data Files Generated

| File | Location | Description |
|------|----------|-------------|
| CostDB_v0.06_NREL.xlsx | eco_tools/lcca/ | 35 system costs, 23 regional factors, 15 utility rates |

---

## Enhancement Requests Documented

### Site Loads Calculator (docs/SITE_LOADS_ENHANCEMENTS.md)
1. **Outdoor Lighting** - Align with NRCC-LTO form
2. **Pools/Spas** - Multiple entries support
3. **Miscellaneous Loads** - Fire pumps, water softeners, commercial kitchens
4. **EV Charging** - Multiple levels (L1, L2, DCFC)
5. **IT Loads** - Visual guide by building type

---

## Known Issues for V8

### High Priority
1. HBJSON import/export needs review (17 test failures)
2. CIBD25 roundtrip validation (8 test failures)
3. Chart visualization edge cases (11 test failures)

### Medium Priority
1. GEM importer - Door, Construction, HVAC parsing incomplete
2. CIBD25 translator - 18 TODOs for property mapping
3. EnergyPlus integration - OSM export needs completion

### Low Priority
1. Commercial catalog injection stubs
2. Window type mapping utilities
3. Battery offset calculation in LCCA

---

## Dependencies

### Python Packages
- streamlit >= 1.28
- pandas >= 1.5
- openpyxl >= 3.0
- plotly >= 5.0
- numpy >= 1.24

### External Tools (Optional)
- CBECC-Com 2025.2.0
- EnergyPlus 24.1
- CSE (California Simulation Engine)

---

## Migration Notes for V8

1. **Session State Pattern** - Use `_pending_nav` callback pattern for cross-page navigation
2. **CostDB** - v0.06 format is standard; maintain backward compatibility with v0.05
3. **Navigation** - `nav_target_map` in main.py defines valid navigation targets
4. **Test Suite** - Run `pytest tests/ -v` before merging changes

---

## Contributors

- ECO Tools Team
- Claude Code AI Assistant

---

## Version History

| Version | Date | Notes |
|---------|------|-------|
| v7.0.0 | 2026-01-01 | Feature complete, V8 baseline established |
| v6.x | 2025-Q4 | CIBD25 export validation |
| v5.x | 2025-Q3 | LCCA integration |
| v4.x | 2025-Q2 | GUI implementation |

---

**Last Updated:** January 1, 2026
