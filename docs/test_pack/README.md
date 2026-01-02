# GUI User Test Pack

**EM Tools Explorer v7.0.0**
**Test Date:** December 2024

---

## Contents

```
test_pack/
├── README.md                    # This file
├── TEST_PLAN.md                 # Detailed test plan with all test cases
├── QUICK_START.md               # Quick start guide for testers
├── TEST_CHECKLIST.md            # Printable test execution checklist
├── BUG_REPORT_TEMPLATE.md       # Template for reporting issues
├── sample_data/
│   ├── sample_cuac.csv          # Sample CUAC data for import testing
│   ├── sample_zones.json        # Sample zone configuration
│   └── sample_tariff_config.json # Sample tariff settings
└── scripts/
    └── run_gui.sh               # Script to launch the GUI
```

---

## Quick Start

1. **Review the test plan:** Read `TEST_PLAN.md` for full details
2. **Launch the application:** Run `scripts/run_gui.sh` or:
   ```bash
   cd "/Users/DavidM/Documents/Documents - MacBook Air (4)/ECO_Alpha_v7"
   streamlit run gui/main.py
   ```
3. **Execute tests:** Follow `TEST_CHECKLIST.md` step by step
4. **Report issues:** Use `BUG_REPORT_TEMPLATE.md` for any failures

---

## Test Scope

This test pack covers the following new GUI features:

| Feature | Page/Location | Priority |
|---------|---------------|----------|
| Zone-Level LCCA | Zone Analysis page | High |
| ESG/Carbon Reporting | ESG Report page | High |
| Site Loads Calculator | Site Loads page | High |
| Building Summary Dashboard | Building Summary page | Medium |
| CUAC CSV Import | Import page | High |
| CSE Integration | Simulation > CSE tab | Medium |
| Tariff Management | LCCA > Tariffs tab | High |
| Scenario Manager | LCCA > Scenarios tab | Medium |
| Enhanced Sensitivity | LCCA > Sensitivity tab | Medium |
| Updated Navigation | Sidebar | Low |

---

## Prerequisites

- Python 3.11 or higher
- All dependencies installed
- Web browser (Chrome, Firefox, or Safari recommended)
- Optional: CBECC-Com 2025 for CSE testing

---

## Support

For questions or issues during testing, contact the development team.
