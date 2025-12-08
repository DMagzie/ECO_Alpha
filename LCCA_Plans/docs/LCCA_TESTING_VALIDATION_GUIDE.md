# LCCA Testing and Validation Guide

**For Future Claude Code Sessions**

This document provides detailed guidance for completing testing and validation of the LCCA module.

---

## Current State (December 2024)

### What Has Been Completed
- **60 unit tests** in `tests/test_lcca_parsers.py` - all passing
- Basic mathematical validation of NPV, IRR, payback calculations
- Parser cross-validation (HourlyResults vs CSE parsers match)
- Mixed-use building data separation validated
- Real-world data tested with Bressi Ranch and Freedom Circle projects

### What Has NOT Been Completed
- End-to-end integration tests with real CBECC output files
- Validation against external tools (Excel, NIST BLCC)
- TOU rate accuracy validation against actual utility bills
- Cost database validation against RS Means / market data
- Edge case handling (corrupted files, missing data, etc.)

---

## Priority 1: End-to-End Integration Tests

### Test Files Available

**Location:** `/Users/DavidM/Dropbox/EM-Tools-Assets/CBECC Models/`

| Project | Type | Files Available |
|---------|------|-----------------|
| Bressi Ranch | High-Rise Residential (320 units, 310K SF) | HourlyResults, CSE CSV |
| Freedom Circle Building A | Mixed-Use Commercial | HourlyResults |
| Del Amo Circle | Commercial | HourlyResults |
| Euclid A/B/C | Commercial (3 buildings) | Full run folders |

### Suggested Integration Test

```python
# tests/test_lcca_integration.py

import pytest
from pathlib import Path

# Test data locations
DROPBOX_MODELS = Path("/Users/DavidM/Dropbox/EM-Tools-Assets/CBECC Models")
BRESSI_RANCH = DROPBOX_MODELS / "Bressi Ranch"
FREEDOM_CIRCLE = DROPBOX_MODELS / "Freedom/Freedom Circle A"


class TestLccaIntegration:
    """End-to-end integration tests with real project data."""

    @pytest.fixture
    def bressi_hourly_results(self):
        """Load Bressi Ranch HourlyResults file."""
        # Find the HourlyResults CSV in the run folder
        run_folder = BRESSI_RANCH / "Bressi Ranch PFA_2024-05-23 - run"
        csv_path = run_folder / "Bressi Ranch PFA_2024-05-23 - ap - HourlyResults.csv"
        return csv_path

    def test_full_workflow_bressi_ranch(self, bressi_hourly_results):
        """Parse Bressi Ranch → ECON-1 → LCCA → Excel + ESG."""
        from eco_tools.lcca.parsers import parse_hourly_results
        from eco_tools.lcca import (
            generate_econ1, Tariff, run_simulation_lcca,
            export_lcca_to_excel, generate_esg_report
        )

        # 1. Parse simulation output
        proposed = parse_hourly_results(str(bressi_hourly_results))

        assert proposed.project_name != ""
        assert proposed.annual.total_elec_kwh > 0
        assert len(proposed.hourly) == 8760

        # 2. Generate ECON-1
        tariff = Tariff(
            name="SCE TOU-GS-3",
            elec_rate_per_kwh=0.22,
            gas_rate_per_therm=1.85,
            demand_rate_per_kw=22.50
        )
        econ1 = generate_econ1(proposed, tariff)

        assert econ1.proposed.gross_cost > 0

        # 3. Generate ESG report
        esg = generate_esg_report(proposed)

        assert esg.proposed.carbon.total_kg > 0
        assert esg.proposed.energy_use_intensity_kbtu_sf > 0

        # 4. Export to Excel (to temp file)
        import tempfile
        with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as f:
            export_lcca_to_excel(
                # Would need LccaResults - create mock baseline
                pass
            )

    def test_mixed_use_separation(self):
        """Verify NonRes and Res data separate correctly for Freedom Circle."""
        # Freedom Circle is a mixed-use building
        pass

    def test_baseline_vs_proposed_comparison(self):
        """Compare standard (ab) vs proposed (ap) runs."""
        # Need both -ab- and -ap- HourlyResults files
        pass
```

### Key Validation Points

1. **Parser produces expected annual totals**
   - Compare `annual.total_elec_kwh` to values in CBECC compliance report
   - Verify peak demand matches what CBECC reports

2. **TOU calculations are reasonable**
   - Summer costs should be higher than winter (for CA buildings)
   - On-peak should be ~2-3x off-peak rates

3. **LCCA metrics pass sanity checks**
   - NPV should be positive for cost-effective measures
   - IRR should be between 0% and 50% for typical projects
   - Simple payback should be less than analysis period

---

## Priority 2: Financial Formula Validation

### Excel Verification Script

```python
# scripts/validate_npv_irr.py
"""
Validate LCCA NPV and IRR calculations against Excel formulas.

Run this script and compare output to Excel =NPV() and =IRR() results.
"""

from eco_tools.lcca import calculate_npv, calculate_irr

# Test case: $10,000 investment, $3,000/year for 5 years
investment = 10000
cash_flows = [3000, 3000, 3000, 3000, 3000]
discount_rate = 0.05

# Our calculations
our_npv = calculate_npv(cash_flows, discount_rate, investment)
our_irr = calculate_irr(cash_flows, investment)

print("Test Case: $10K investment, $3K/year x 5 years, 5% discount")
print(f"Our NPV: ${our_npv:,.2f}")
print(f"Our IRR: {our_irr*100:.2f}%")
print()
print("Excel formulas to verify:")
print("  =NPV(0.05, 3000,3000,3000,3000,3000) - 10000")
print("  =IRR({-10000,3000,3000,3000,3000,3000})")
print()
print("Expected results:")
print("  NPV ≈ $2,989")
print("  IRR ≈ 15.24%")
```

### NIST BLCC Comparison

NIST Building Life-Cycle Cost (BLCC) software is the standard for federal LCCA. Consider:

1. Create a matching scenario in BLCC
2. Compare NPV, SIR, and payback results
3. Document any methodology differences

---

## Priority 3: TOU Rate Validation

### Current TOU Tariffs Implemented

| Tariff | Utility | Rates (approximate) |
|--------|---------|---------------------|
| TOU-GS-3 | SCE | On: $0.38, Off: $0.14 |
| B-20 | PG&E | On: $0.42, Off: $0.16 |
| AL-TOU | SDG&E | On: $0.45, Off: $0.18 |

### Validation Tasks

1. **Get current rate schedules** from utility websites
2. **Update rates** in `tariffs.py` if significantly different
3. **Test against actual utility bill** if sample bill is available

### Utility Rate Sources

- SCE: https://www.sce.com/business/rates
- PG&E: https://www.pge.com/tariffs/
- SDG&E: https://www.sdge.com/businesses/pricing-plans

---

## Priority 4: Cost Database Validation

### Current Cost Values (2024 estimates)

| System | Base Cost | Unit | Source |
|--------|-----------|------|--------|
| Air-cooled chiller | $800 | per ton | RS Means 2024 |
| Water-cooled chiller | $650 | per ton | RS Means 2024 |
| Gas boiler | $45 | per MBH | RS Means 2024 |
| VRF | $1,200 | per ton | RS Means 2024 |
| Rooftop PV | $2.00 | per Wdc | NREL ATB 2024 |
| Battery storage | $400 | per kWh | NREL ATB 2024 |

### Validation Tasks

1. **Check RS Means current costs** - values may have changed
2. **Verify PV costs** against recent project proposals
3. **Validate regional factors** - SF 1.20x, LA 1.12x, SD 1.08x

### Cost Update Script

```python
# Update cost database with current values
from eco_tools.lcca import create_default_costdb

db = create_default_costdb()

# Example: Update PV cost to current market rate
db.system_costs["pv_rooftop"].base_cost = 2.25  # Updated $/W
db.system_costs["pv_rooftop"].year = 2025

# Save updated database
from eco_tools.lcca import save_costdb_to_json
save_costdb_to_json(db, "costdb_2025.json")
```

---

## Priority 5: Edge Case Testing

### Test Cases to Add

```python
class TestEdgeCases:
    """Edge case and error handling tests."""

    def test_empty_csv_file(self, tmp_path):
        """Test handling of empty CSV file."""
        empty_file = tmp_path / "empty.csv"
        empty_file.write_text("")

        from eco_tools.lcca.parsers import parse_hourly_results
        with pytest.raises(ValueError):
            parse_hourly_results(str(empty_file))

    def test_missing_columns(self, tmp_path):
        """Test handling of CSV with missing required columns."""
        pass

    def test_zero_energy_building(self):
        """Test LCCA with net-zero energy (100% PV offset)."""
        pass

    def test_negative_energy_cost(self):
        """Test when PV generation exceeds consumption."""
        pass

    def test_very_long_analysis_period(self):
        """Test 50-year analysis period."""
        pass

    def test_high_discount_rate(self):
        """Test with 15% discount rate."""
        pass

    def test_leap_year_hourly_data(self):
        """Test with 8784-hour dataset (leap year)."""
        pass
```

---

## Test Data Locations Quick Reference

### In Repository
```
/Users/DavidM/Documents/ECO_Alpha_v7/
├── tests/test_lcca_parsers.py      # Main test file
├── reference_data/cbecc/           # Some sample models
└── docs/reference_data/cbecc/      # Euclid project run folders
```

### External (Dropbox)
```
/Users/DavidM/Dropbox/EM-Tools-Assets/CBECC Models/
├── Bressi Ranch/                   # High-rise residential
├── Freedom/Freedom Circle A/       # Mixed-use
├── Del Amo/                        # Commercial
└── Euclid/                         # Commercial (3 buildings)
```

### HourlyResults File Pattern
```
{ProjectName} - {ap|ab} - HourlyResults.csv
  ap = Proposed
  ab = Baseline (Standard)
```

---

## Running Tests

```bash
# All LCCA tests
python3 -m pytest tests/test_lcca_parsers.py -v

# Specific test class
python3 -m pytest tests/test_lcca_parsers.py::TestLccaCalculators -v

# With coverage
python3 -m pytest tests/test_lcca_parsers.py --cov=eco_tools.lcca --cov-report=html
```

---

## Checklist for Future Session

- [ ] Create `tests/test_lcca_integration.py` with real data tests
- [ ] Validate NPV/IRR against Excel formulas
- [ ] Update TOU rates from current utility schedules
- [ ] Validate cost database against RS Means 2025
- [ ] Add edge case tests for error handling
- [ ] Test PDF export with reportlab installed
- [ ] Validate ESG emission factors against EPA eGRID 2024
- [ ] Create comparison test against NIST BLCC (if accessible)
