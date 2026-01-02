# EM Tools Explorer - GUI User Test Plan

**Version:** 7.0.0
**Date:** December 2024
**Test Scope:** New GUI Features (Phase 1-4 Implementation)

---

## 1. Overview

This test plan covers user acceptance testing (UAT) for the new GUI features implemented in the EM Tools Explorer. The goal is to validate that all new pages and enhancements function correctly from an end-user perspective.

### 1.1 Features Under Test

| ID | Feature | Type | Priority |
|----|---------|------|----------|
| F1 | Zone-Level LCCA Dashboard | New Page | P0 |
| F2 | ESG/Carbon Reporting | New Page | P0 |
| F3 | Site Loads Calculator | New Page | P0 |
| F4 | Building Summary Dashboard | New Page | P1 |
| F5 | CUAC CSV Import | Enhancement | P0 |
| F6 | CSE Integration | New Tab | P1 |
| F7 | Tariff Management | New Tab | P0 |
| F8 | Scenario Manager | New Tab | P1 |
| F9 | Enhanced Sensitivity Analysis | Enhancement | P1 |
| F10 | Navigation Updates | Enhancement | P2 |

### 1.2 Out of Scope

- Backend calculation accuracy (covered by unit tests)
- Performance/load testing
- Security testing
- Mobile responsiveness

---

## 2. Test Environment

### 2.1 Requirements

| Component | Requirement |
|-----------|-------------|
| Python | 3.11 or higher |
| OS | macOS, Windows, or Linux |
| Browser | Chrome 90+, Firefox 88+, Safari 14+ |
| RAM | 8GB minimum |
| Disk | 500MB free space |

### 2.2 Dependencies

```bash
# Install all dependencies
pip install -r requirements.txt

# Key packages
streamlit>=1.28.0
plotly>=5.0.0
pandas>=2.0.0
numpy>=1.24.0
```

### 2.3 Optional Components

- **CBECC-Com 2025**: Required for CSE simulation tests
- **Sample Project Files**: `.cibd22x`, `.cibd25`, CUAC CSV files

---

## 3. Test Cases

### TC-001: Application Launch & Navigation

**Objective:** Verify application starts and navigation works correctly

**Preconditions:** Dependencies installed, no other Streamlit instance running

| Step | Action | Expected Result | Status |
|------|--------|-----------------|--------|
| 1 | Run `streamlit run gui/main.py` | Terminal shows "You can view your Streamlit app" | |
| 2 | Open browser to http://localhost:8501 | App loads with "EM Tools Explorer" title | |
| 3 | Check page subtitle | Shows "Energy Modeling & Life Cycle Cost Analysis Toolkit" | |
| 4 | Verify sidebar | Navigation shows emoji icons for all pages | |
| 5 | Check "No model loaded" indicator | Blue info box in sidebar | |
| 6 | Expand "Module Status" | Shows checkmarks for available modules | |
| 7 | Click each navigation item | Each page loads without error | |

**Notes:**
- Navigation should show ~15 pages
- Module status should show 5+ modules

---

### TC-002: Import Page - CUAC CSV Support

**Objective:** Verify CUAC CSV file import functionality

**Preconditions:** Sample CUAC CSV file available

| Step | Action | Expected Result | Status |
|------|--------|-----------------|--------|
| 1 | Navigate to "Import" page | Page loads with file uploader | |
| 2 | Observe file type options | Shows "xml, cibd22x, cibd22, cibd25, json, gem, csv" | |
| 3 | Upload a CUAC CSV file | File is accepted | |
| 4 | Observe CUAC detection | Shows "CUAC CSV Import" section | |
| 5 | Click "Import CUAC CSV" | Spinner shows "Parsing CUAC data..." | |
| 6 | Verify success message | Shows project name | |
| 7 | Check metrics display | Shows Unit Types, Total kWh, Tariff Date | |
| 8 | Verify unit breakdown | Lists consumption by unit type | |

**Test Data:** Use `sample_data/sample_cuac.csv`

---

### TC-003: Zone Analysis Page

**Objective:** Verify zone-level LCCA dashboard functionality

**Preconditions:** None (can use manual entry)

| Step | Action | Expected Result | Status |
|------|--------|-----------------|--------|
| 1 | Navigate to "Zone Analysis" | Page loads with header "Zone-Level LCCA" | |
| 2 | Verify tabs | 7 tabs visible: Setup, Breakdown, Dwelling, Common, CUAC, Ranking, Export | |
| 3 | In Setup, enter project name | Text input accepts entry | |
| 4 | Select building type | Dropdown shows: Multifamily, Mixed-Use, etc. | |
| 5 | Set climate zone | Dropdown with CA climate zones | |
| 6 | Add a zone manually | Form with zone name, type, area, kWh | |
| 7 | Click "Add Zone" | Zone appears in zone list | |
| 8 | Navigate to Cost Breakdown | Tab shows cost analysis | |
| 9 | View Dwelling Units tab | Unit type summary displays | |
| 10 | View Common Areas tab | Common area categories list | |
| 11 | View CUAC Allowances tab | Allowance calculations shown | |
| 12 | View Performance Ranking | Ranking table with EUI | |
| 13 | Export tab - Download JSON | File downloads | |
| 14 | Export tab - Download CSV | File downloads | |

---

### TC-004: ESG Report Page

**Objective:** Verify carbon/ESG reporting functionality

**Preconditions:** None (can use manual entry)

| Step | Action | Expected Result | Status |
|------|--------|-----------------|--------|
| 1 | Navigate to "ESG Report" | Page loads with tabs | |
| 2 | Verify tabs | 4 tabs: Carbon Calculator, Benchmarks, Sustainability, Export | |
| 3 | In Calculator, select region | Dropdown with CA, Hawaii, National | |
| 4 | Observe emission factor | Value updates based on region | |
| 5 | Enter annual kWh | Number input accepts value | |
| 6 | Enter annual therms | Number input accepts value | |
| 7 | View Scope 1 emissions | Shows calculated CO2 tons | |
| 8 | View Scope 2 emissions | Shows calculated CO2 tons | |
| 9 | View total emissions | Sum of Scope 1 + 2 | |
| 10 | Navigate to Benchmarks | EUI comparison options | |
| 11 | Navigate to Sustainability | Score calculation | |
| 12 | View Sustainability Score | 0-100 score with color coding | |
| 13 | Navigate to Export | Download options | |
| 14 | Download JSON report | File downloads | |

---

### TC-005: Site Loads Calculator Page

**Objective:** Verify non-modeled loads calculator functionality

**Preconditions:** None

| Step | Action | Expected Result | Status |
|------|--------|-----------------|--------|
| 1 | Navigate to "Site Loads" | Page loads with tabs | |
| 2 | Verify tabs | 7 tabs: Calculator, Lighting, Parking, Pools, Vertical, Misc, Summary | |
| 3 | In Lighting tab, add fixture | Form with type, wattage, quantity, hours | |
| 4 | Calculate lighting load | kWh/yr calculates | |
| 5 | In Parking tab, set spaces | Number input for spaces | |
| 6 | Select parking type | Surface, Covered, Garage | |
| 7 | Calculate parking load | kWh/yr based on LPD | |
| 8 | In Pools tab, add pool | Size, pump HP, hours | |
| 9 | Calculate pool load | Annual pump energy | |
| 10 | In Vertical tab, add elevator | Type, floors, trips | |
| 11 | Calculate elevator load | Annual energy | |
| 12 | In Misc tab, add load | Custom load entry | |
| 13 | View Summary tab | All loads aggregated | |
| 14 | Verify total site load | Sum matches components | |
| 15 | Download CSV | File downloads | |

---

### TC-006: Building Summary Dashboard

**Objective:** Verify unified building summary view

**Preconditions:** Model imported (recommended)

| Step | Action | Expected Result | Status |
|------|--------|-----------------|--------|
| 1 | Navigate to "Building Summary" | Page loads | |
| 2 | If no model, verify warning | "No active model loaded" message | |
| 3 | Import a model first | Return to Building Summary | |
| 4 | Check Overview tab | Project info, geometry stats | |
| 5 | Verify zone count | Matches imported model | |
| 6 | Check Energy tab | Available simulation results | |
| 7 | Check Financial tab | LCCA metrics if available | |
| 8 | Check Carbon tab | Emission calculations | |
| 9 | Check Compliance tab | Title 24 status if available | |
| 10 | Export as JSON | File downloads | |
| 11 | Export as CSV | File downloads | |

---

### TC-007: Simulation Page - CSE Tab

**Objective:** Verify CSE integration in simulation page

**Preconditions:** CBECC-Com installed (for full test)

| Step | Action | Expected Result | Status |
|------|--------|-----------------|--------|
| 1 | Navigate to "Simulate" | Page loads with tabs | |
| 2 | Verify CSE tab exists | "CSE (Zone-Level)" tab visible | |
| 3 | Click CSE tab | CSE interface loads | |
| 4 | Expand "Check CSE Installation" | Verification section | |
| 5 | Click "Verify CSE Installation" | Shows found/not found status | |
| 6 | Upload a .cse file | File accepted | |
| 7 | Or enter file path | Path input works | |
| 8 | Enable zone transformation | Checkbox works | |
| 9 | Set output filename | Text input works | |
| 10 | Click "Transform CSE File" | Transformation runs | |
| 11 | Verify transform stats | Meters, exports, GAINs updated | |
| 12 | Set timeout slider | 60-600 seconds range | |
| 13 | Click "Run CSE Simulation" | Simulation starts (if CSE available) | |
| 14 | View results | Execution time, output files | |

---

### TC-008: LCCA Dashboard - Tariff Management Tab

**Objective:** Verify enhanced tariff management functionality

**Preconditions:** None

| Step | Action | Expected Result | Status |
|------|--------|-----------------|--------|
| 1 | Navigate to "LCCA Dashboard" | Page loads | |
| 2 | Click "Tariffs" tab | Tariff Management opens | |
| 3 | Verify sub-tabs | Library, Customize, Comparison, Schedule | |
| 4 | In Library, expand PG&E | Shows B-20, E-TOU-C, EV2-A | |
| 5 | Expand SCE | Shows TOU-GS-3, TOU-D-4-9PM, TOU-D-PRIME | |
| 6 | Expand SDG&E | Shows AL-TOU, TOU-DR1, EV-TOU-5 | |
| 7 | Expand Hawaii | Shows HECO, MECO, HELCO tariffs | |
| 8 | Click "Select" on a tariff | Tariff selected, details show | |
| 9 | Navigate to Customize | Rate inputs appear | |
| 10 | Modify a rate | Value updates | |
| 11 | Click "Apply Inflation" | All rates increase 3% | |
| 12 | Click "Reset to Base" | Rates reset | |
| 13 | Navigate to Comparison | Multi-select appears | |
| 14 | Select 3+ tariffs | Comparison table shows | |
| 15 | View rate chart | Bar chart renders | |
| 16 | View cost estimate chart | Annual cost comparison | |
| 17 | Navigate to Schedule | TOU schedule visual | |
| 18 | View summer schedule | 24-hour bar chart | |
| 19 | View winter schedule | 24-hour bar chart | |

---

### TC-009: LCCA Dashboard - Scenario Manager

**Objective:** Verify scenario comparison functionality

**Preconditions:** LCCA analysis completed

| Step | Action | Expected Result | Status |
|------|--------|-----------------|--------|
| 1 | In LCCA Dashboard, run analysis | Results display | |
| 2 | Click "Scenarios" tab | Scenario manager opens | |
| 3 | Enter scenario name | Text input accepts name | |
| 4 | Enter description | Text area accepts description | |
| 5 | Click "Save Current Analysis" | Success message | |
| 6 | Verify scenario in list | Name, NPV, timestamp shown | |
| 7 | Modify LCCA parameters | Change rates or costs | |
| 8 | Run analysis again | New results | |
| 9 | Save as second scenario | Two scenarios in list | |
| 10 | View comparison table | Both scenarios compared | |
| 11 | View NPV chart | Bar chart with both scenarios | |
| 12 | Click "Export Scenarios" | CSV downloads | |
| 13 | Click delete on a scenario | Scenario removed | |
| 14 | Click "Clear All" | All scenarios removed | |

---

### TC-010: LCCA Dashboard - Enhanced Sensitivity

**Objective:** Verify enhanced sensitivity analysis features

**Preconditions:** LCCA analysis completed

| Step | Action | Expected Result | Status |
|------|--------|-----------------|--------|
| 1 | In LCCA Dashboard, run analysis | Results available | |
| 2 | Click "Sensitivity" tab | Sensitivity options show | |
| 3 | Verify sub-tabs | Interactive, Tornado, Monte Carlo, Sweeps | |
| 4 | In Interactive, move slider | NPV updates real-time | |
| 5 | Change multiple parameters | Combined effect shown | |
| 6 | Navigate to Tornado | Tornado chart setup | |
| 7 | Click "Generate Tornado" | Horizontal bar chart | |
| 8 | Verify parameter ranking | Sorted by impact | |
| 9 | Navigate to Monte Carlo | Simulation settings | |
| 10 | Set iterations (e.g., 500) | Number input works | |
| 11 | Click "Run Monte Carlo" | Progress shown | |
| 12 | View histogram | Distribution of NPV | |
| 13 | View percentiles | P10, P50, P90 values | |
| 14 | Navigate to Sweeps | Parameter sweep setup | |
| 15 | Select parameter | Dropdown works | |
| 16 | Set range (min, max, steps) | Inputs work | |
| 17 | Click "Run Sweep" | Results table shows | |

---

## 4. Test Data

### 4.1 Sample CUAC CSV Format

```csv
CUAC Utility Allowance Report
Project: Sample Multifamily
Date: 2024-12-01

Unit Type,Annual kWh,Monthly Allowance
1BR,4500,45.00
2BR,5500,55.00
3BR,6800,68.00
```

### 4.2 Sample Zone Configuration

```json
{
  "zones": [
    {
      "name": "Unit 101",
      "type": "dwelling",
      "area_sqft": 850,
      "annual_kwh": 4500
    },
    {
      "name": "Corridor L1",
      "type": "common",
      "category": "corridor",
      "area_sqft": 500,
      "annual_kwh": 1200
    }
  ]
}
```

---

## 5. Defect Classification

| Severity | Description | Example |
|----------|-------------|---------|
| Critical | App crashes or data loss | Page fails to load |
| High | Feature unusable | Button doesn't work |
| Medium | Feature impaired | Chart doesn't render |
| Low | Cosmetic issue | Alignment off |

---

## 6. Exit Criteria

Testing is complete when:

1. All P0 test cases pass
2. All P1 test cases pass or have documented workarounds
3. No Critical or High severity defects remain open
4. Test coverage report reviewed and approved

---

## 7. Sign-off

| Role | Name | Signature | Date |
|------|------|-----------|------|
| Developer | | | |
| QA Tester | | | |
| Product Owner | | | |

---

*Generated: December 2024*
