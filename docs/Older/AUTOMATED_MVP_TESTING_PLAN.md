# Automated MVP Testing Plan

**Date:** November 13, 2025
**Purpose:** Define comprehensive automated test suite for ECO Tools MVP validation
**Framework:** pytest with fixtures and mocking
**Goal:** 80%+ automation of MVP validation checklist

---

## 🎯 Overview

This document outlines what MVP testing **can be automated** vs what requires **manual validation**. The goal is to automate 80-90% of the validation work to enable rapid iteration and regression prevention.

**Key Insight:** We have **13 sample CIBD22X files** available for testing - this is a goldmine for automated validation!

---

## ✅ What CAN Be Automated (80-90%)

### 1. Format Import/Export Testing (100% Automatable)

#### Test Coverage
- ✅ Import all 13 CIBD22X sample files
- ✅ Import 10+ CIBD25 sample files
- ✅ Validate internal representation created
- ✅ Count zones, surfaces, openings
- ✅ Export back to same format
- ✅ Verify file created successfully
- ✅ Check file size reasonable
- ✅ Validate XML structure

#### Sample Files Available
```
CIBD22X (13 files):
- Bressi Ranch Apartments.cibd22x (290 zones - LARGE)
- El Paseo Building 2.cibd22x
- El Paseo de Saratoga Building 1.cibd22x
- Mainplace Mall Parcel 3.cibd22x
- 080012-Whse-CECStd.cibd22x
- Freedom Circle Building A.cibd22x
- Freedom Circle Building B.cibd22x
- Del Amo Circle-LEED.cibd22x
- Euclid Building A.cibd22x
- Euclid Building B.cibd22x
- Euclid Building C.cibd22x
- The Scout Hotel.cibd22x
- The Scout Hotel Conference Center.cibd22x

CIBD25 (10+ files):
- Standard Model Test suite (10 building types)
```

#### Test Implementation
```python
# tests/integration/test_format_import_export.py

import pytest
from pathlib import Path
from eco_tools.translators.cibd22x import CIBD22XImporter, CIBD22XExporter
from eco_tools.translators.cibd25 import CIBD25Importer, CIBD25Exporter

SAMPLE_FILES_CIBD22X = [
    "reference_data/cbecc/CBECC Models/Bressi Ranch/Bressi Ranch Apartments.cibd22x",
    "reference_data/cbecc/CBECC Models/cibd22x/El Paseo Building 2_CBECC 2022_2025-08-12.cibd22x",
    # ... all 13 files
]

SAMPLE_FILES_CIBD25 = [
    "reference_data/cbecc/CBECC Models/2025 Sample Models/StandardModelTests/020012-OffSml-CECStd.cibd25",
    # ... all 10+ files
]

@pytest.mark.parametrize("input_file", SAMPLE_FILES_CIBD22X)
def test_cibd22x_import_export_roundtrip(input_file, tmp_path):
    """Test import and export for all CIBD22X sample files"""

    # Import
    importer = CIBD22XImporter()
    model = importer.import_file(input_file)

    # Validate import
    assert model is not None
    assert len(model.zones) > 0

    # Export
    output_file = tmp_path / Path(input_file).name
    exporter = CIBD22XExporter()
    exporter.export_to_file(model, str(output_file))

    # Validate export
    assert output_file.exists()
    assert output_file.stat().st_size > 1000  # Non-trivial file

    # Re-import to verify roundtrip
    model2 = importer.import_file(str(output_file))

    # Compare key metrics
    assert len(model2.zones) == len(model.zones)
    # More detailed comparisons...

@pytest.mark.parametrize("input_file", SAMPLE_FILES_CIBD25)
def test_cibd25_import_export_roundtrip(input_file, tmp_path):
    """Test import and export for all CIBD25 sample files"""
    # Similar implementation...
```

**Automation Level:** 100%
**Estimated Implementation Time:** 2-3 hours
**Value:** HIGH - Prevents regressions, validates all translators

---

### 2. CBECC Simulation Testing (90% Automatable)

#### What Can Be Automated
- ✅ Export model to CIBD22X/CIBD25
- ✅ Run CBECC via subprocess
- ✅ Check exit code
- ✅ Verify log file created
- ✅ Parse log file for errors
- ✅ Check for AnalysisResults.xml
- ✅ Parse results (if simulation succeeded)
- ✅ Validate extracted data structure
- ✅ Performance measurement (execution time)

#### What Requires Manual Review
- ❌ **Accuracy validation** - Need expert review of compliance results
- ❌ **CBECC installation** - One-time manual setup
- ❌ **First-run verification** - Manual inspection of first successful run

#### Test Implementation
```python
# tests/integration/test_cbecc_simulation.py

import pytest
import subprocess
import time
from pathlib import Path
from eco_tools.translators.cibd22x import CIBD22XExporter
from eco_tools.simulation.cbecc_results_parser import CBECCResultsParser

# Mark as slow (these tests take 1-5 minutes each)
pytestmark = pytest.mark.slow

# Skip if CBECC not installed
CBECC_2022_PATH = "/Applications/CBECC 2022.app/Contents/MacOS/CBECC 2022"
CBECC_2025_PATH = "/Applications/CBECC 2025.app/Contents/MacOS/CBECC 2025"

def cbecc_installed(path):
    """Check if CBECC is installed"""
    return Path(path).exists()

@pytest.fixture
def sample_model_small():
    """Load a small sample model for faster testing"""
    from eco_tools.translators.cibd22x import CIBD22XImporter
    input_file = "reference_data/cbecc/CBECC Models/cibd22x/020012-OffSml-CECStd.cibd22x"
    importer = CIBD22XImporter()
    return importer.import_file(input_file)

@pytest.mark.skipif(not cbecc_installed(CBECC_2022_PATH), reason="CBECC 2022 not installed")
def test_cbecc_2022_simulation_workflow(sample_model_small, tmp_path):
    """Test complete CBECC 2022 simulation workflow"""

    # Step 1: Export to CIBD22X
    output_file = tmp_path / "test_model.cibd22x"
    exporter = CIBD22XExporter()
    exporter.export_to_file(sample_model_small, str(output_file))

    assert output_file.exists()

    # Step 2: Run CBECC simulation
    start_time = time.time()
    result = subprocess.run(
        [CBECC_2022_PATH, "-nrp", "-b", str(output_file)],
        capture_output=True,
        text=True,
        timeout=300  # 5 minute timeout
    )
    duration = time.time() - start_time

    # Step 3: Verify execution
    assert result.returncode == 0, f"CBECC failed with exit code {result.returncode}"

    # Step 4: Check log file
    log_file = output_file.with_suffix('.log')
    assert log_file.exists(), "Log file not created"

    log_content = log_file.read_text()
    assert "error" not in log_content.lower() or "0 error" in log_content.lower()

    # Step 5: Check for results file (may not exist if simulation failed)
    # Note: AnalysisResults.xml location may vary
    results_file = output_file.parent / "AnalysisResults.xml"

    if results_file.exists():
        # Step 6: Parse results
        parser = CBECCResultsParser(str(results_file))
        results = parser.parse()

        # Step 7: Validate results structure
        assert results["status"] == "success"
        assert "project_name" in results
        assert "compliance_status" in results
        assert "end_uses" in results

    # Step 8: Record performance
    print(f"\n✅ CBECC simulation completed in {duration:.1f}s")

    # Performance assertion (should complete in reasonable time)
    assert duration < 180, f"Simulation took too long: {duration:.1f}s"

@pytest.mark.skipif(not cbecc_installed(CBECC_2025_PATH), reason="CBECC 2025 not installed")
def test_cbecc_2025_simulation_workflow(sample_model_small, tmp_path):
    """Test complete CBECC 2025 simulation workflow"""
    # Similar implementation for CBECC 2025...

@pytest.mark.parametrize("sample_file", [
    "reference_data/cbecc/CBECC Models/cibd22x/020012-OffSml-CECStd.cibd22x",
    "reference_data/cbecc/CBECC Models/cibd22x/080012-Whse-CECStd.cibd22x",
])
@pytest.mark.skipif(not cbecc_installed(CBECC_2022_PATH), reason="CBECC 2022 not installed")
def test_cbecc_multiple_building_types(sample_file, tmp_path):
    """Test CBECC with different building types"""
    # Import existing file and run simulation
    from eco_tools.translators.cibd22x import CIBD22XImporter

    importer = CIBD22XImporter()
    model = importer.import_file(sample_file)

    # Run simulation
    # ... (similar to above)
```

**Automation Level:** 90%
**Estimated Implementation Time:** 4-6 hours
**Value:** VERY HIGH - Validates critical simulation workflow

---

### 3. EnergyPlus Simulation Testing (85% Automatable)

#### What Can Be Automated
- ✅ Export to HBJSON
- ✅ Validate HBJSON structure
- ✅ Run EnergyPlus (if installed)
- ✅ Check for SQL results
- ✅ Parse EUI and end uses
- ✅ Validate data ranges (reasonable values)
- ✅ Performance measurement

#### What Requires Manual Review
- ❌ **Honeybee installation** - One-time setup
- ❌ **Weather file availability** - May need manual download
- ❌ **Results accuracy** - Expert validation

#### Test Implementation
```python
# tests/integration/test_energyplus_simulation.py

import pytest
from eco_tools.translators.hbjson import HBJSONExporter
from eco_tools.simulation.energyplus_runner import EnergyPlusRunner

pytestmark = pytest.mark.slow

@pytest.fixture
def sample_model():
    """Load sample model"""
    from eco_tools.translators.cibd22x import CIBD22XImporter
    input_file = "reference_data/cbecc/CBECC Models/cibd22x/020012-OffSml-CECStd.cibd22x"
    importer = CIBD22XImporter()
    return importer.import_file(input_file)

@pytest.mark.skipif(not energyplus_installed(), reason="EnergyPlus not installed")
def test_energyplus_workflow(sample_model, tmp_path):
    """Test complete EnergyPlus simulation workflow"""

    # Step 1: Export to HBJSON
    output_file = tmp_path / "test_model.hbjson"
    exporter = HBJSONExporter()
    exporter.export_to_file(sample_model, str(output_file))

    assert output_file.exists()

    # Step 2: Run EnergyPlus
    runner = EnergyPlusRunner()
    results = runner.run_simulation(
        str(output_file),
        weather_file="path/to/weather.epw"
    )

    # Step 3: Validate results
    assert results["success"] is True
    assert "eui" in results
    assert "end_uses" in results

    # Step 4: Validate reasonable values
    assert 0 < results["eui"] < 500  # kBtu/ft²/yr
    assert results["end_uses"]["heating"] >= 0
    assert results["end_uses"]["cooling"] >= 0

def energyplus_installed():
    """Check if EnergyPlus is installed"""
    try:
        from honeybee_energy.run import run_idf
        return True
    except ImportError:
        return False
```

**Automation Level:** 85%
**Estimated Implementation Time:** 3-4 hours
**Value:** HIGH - Validates EnergyPlus integration

---

### 4. Results Comparison Testing (100% Automatable)

#### What Can Be Automated
- ✅ Mock CBECC and EnergyPlus results
- ✅ Test comparison logic
- ✅ Validate delta calculations
- ✅ Test percentage differences
- ✅ Validate unit conversions
- ✅ Test edge cases (zeros, negatives, missing data)

#### Test Implementation
```python
# tests/unit/test_results_comparison.py

import pytest
from eco_tools.simulation.comparison import compare_results

def test_basic_comparison():
    """Test basic results comparison"""
    cbecc_results = {
        "eui": 45.5,
        "end_uses": {
            "heating": 15.0,
            "cooling": 12.0,
            "lighting": 8.0,
            "equipment": 10.5
        }
    }

    energyplus_results = {
        "eui": 48.2,
        "end_uses": {
            "heating": 16.5,
            "cooling": 13.0,
            "lighting": 8.5,
            "equipment": 10.2
        }
    }

    comparison = compare_results(cbecc_results, energyplus_results)

    # Validate structure
    assert "eui_delta" in comparison
    assert "eui_percent_diff" in comparison
    assert "end_use_deltas" in comparison

    # Validate calculations
    assert comparison["eui_delta"] == pytest.approx(2.7, abs=0.1)
    assert comparison["eui_percent_diff"] == pytest.approx(5.9, abs=0.1)

def test_comparison_with_missing_end_uses():
    """Test comparison when some end uses are missing"""
    # Test edge cases...

def test_comparison_with_zero_values():
    """Test comparison with zero energy values"""
    # Test edge cases...
```

**Automation Level:** 100%
**Estimated Implementation Time:** 2 hours
**Value:** MEDIUM - Validates comparison logic

---

### 5. Visualization Testing (95% Automatable)

#### What Can Be Automated
- ✅ Chart generation with mock data
- ✅ Validate chart objects created
- ✅ Check chart has correct data series
- ✅ Verify labels and titles
- ✅ Test with edge cases (empty data, single point)
- ✅ Export chart to PNG/HTML

#### What Requires Manual Review
- ❌ **Visual appearance** - One-time manual inspection

#### Test Implementation
```python
# tests/unit/test_charts.py (ALREADY EXISTS - EXPAND)

import pytest
from eco_tools.visualization.charts import (
    create_end_use_comparison_chart,
    create_compliance_gauge,
    create_monthly_energy_chart
)

def test_end_use_chart_generation():
    """Test end use comparison chart creation"""
    cbecc_data = {"heating": 15.0, "cooling": 12.0}
    ep_data = {"heating": 16.5, "cooling": 13.0}

    chart = create_end_use_comparison_chart(cbecc_data, ep_data)

    # Validate chart object
    assert chart is not None
    assert hasattr(chart, 'data')
    assert len(chart.data) == 2  # Two series

    # Validate data
    assert chart.data[0].name == "CBECC"
    assert chart.data[1].name == "EnergyPlus"

def test_compliance_gauge():
    """Test compliance gauge chart"""
    margin = 11.8  # 11.8% better than standard

    chart = create_compliance_gauge(margin)

    assert chart is not None
    # Validate chart properties...

# EXISTING TESTS (from test_charts.py):
# - test_create_basic_chart
# - test_chart_with_custom_title
# - test_chart_with_empty_cbecc
# - test_chart_with_empty_energyplus
# - test_chart_with_both_empty
# - test_chart_labels
# - test_chart_colors
```

**Automation Level:** 95%
**Estimated Implementation Time:** 1 hour (expand existing tests)
**Value:** MEDIUM - Validates visualization layer

---

### 6. CSV Export Testing (100% Automatable)

#### Test Implementation
```python
# tests/unit/test_csv_exporter.py (ALREADY EXISTS)

# Current tests already cover:
# - CSV structure validation
# - Data integrity
# - Edge cases
```

**Automation Level:** 100% ✅
**Estimated Implementation Time:** Already complete
**Value:** MEDIUM - Already validated

---

### 7. Error Handling Testing (100% Automatable)

#### What Can Be Automated
- ✅ Test invalid file imports
- ✅ Test corrupted XML
- ✅ Test missing files
- ✅ Test permission errors
- ✅ Test simulation failures
- ✅ Validate error messages are user-friendly

#### Test Implementation
```python
# tests/integration/test_error_handling.py

import pytest
from eco_tools.translators.cibd22x import CIBD22XImporter

def test_import_nonexistent_file():
    """Test importing non-existent file"""
    importer = CIBD22XImporter()

    with pytest.raises(FileNotFoundError) as exc_info:
        importer.import_file("/nonexistent/file.cibd22x")

    # Validate error message is helpful
    assert "not found" in str(exc_info.value).lower()

def test_import_invalid_xml():
    """Test importing corrupted XML file"""
    # Create invalid XML file
    # Test error handling...

def test_simulation_with_missing_cbecc():
    """Test simulation when CBECC not installed"""
    # Mock CBECC not found
    # Validate helpful error message...
```

**Automation Level:** 100%
**Estimated Implementation Time:** 2-3 hours
**Value:** HIGH - Ensures good user experience

---

### 8. Performance Testing (90% Automatable)

#### What Can Be Automated
- ✅ Measure import time for large models
- ✅ Measure export time
- ✅ Measure simulation time
- ✅ Monitor memory usage
- ✅ Test with progressively larger models
- ✅ Generate performance report

#### Test Implementation
```python
# tests/performance/test_performance.py

import pytest
import time
import tracemalloc

@pytest.mark.performance
def test_import_performance_large_model():
    """Test import performance with large model (290 zones)"""
    from eco_tools.translators.cibd22x import CIBD22XImporter

    # Start memory tracking
    tracemalloc.start()

    # Measure time
    start_time = time.time()

    importer = CIBD22XImporter()
    model = importer.import_file(
        "reference_data/cbecc/CBECC Models/Bressi Ranch/Bressi Ranch Apartments.cibd22x"
    )

    duration = time.time() - start_time
    current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    # Validate import succeeded
    assert len(model.zones) == 290

    # Performance assertions
    assert duration < 10.0, f"Import took {duration:.2f}s (should be < 10s)"
    assert peak < 500 * 1024 * 1024, f"Peak memory {peak / 1024 / 1024:.1f}MB (should be < 500MB)"

    print(f"\n📊 Performance: {duration:.2f}s, Peak memory: {peak / 1024 / 1024:.1f}MB")
```

**Automation Level:** 90%
**Estimated Implementation Time:** 2-3 hours
**Value:** MEDIUM - Identifies performance bottlenecks

---

## ❌ What CANNOT Be Automated (10-20%)

### 1. Manual Validation Required

#### CBECC Results Accuracy (Expert Review)
- ❌ Validate compliance status is correct
- ❌ Verify TDV calculations match expectations
- ❌ Compare with known-good results
- ❌ Check edge cases with modeling experts

**Why Not Automatable:** Requires domain expertise and baseline comparisons

**Workaround:** Create "golden reference" outputs from validated simulations, then automate comparison

#### EnergyPlus Results Accuracy
- ❌ Validate EUI is reasonable for building type
- ❌ Compare end use ratios with benchmarks
- ❌ Verify HVAC sizing is appropriate

**Why Not Automatable:** Requires engineering judgment

**Workaround:** Automated range checks (is EUI between X and Y for this building type?)

#### Visual Quality Assurance
- ❌ Charts look professional
- ❌ Colors are appropriate
- ❌ Layout is user-friendly

**Why Not Automatable:** Subjective aesthetic judgment

**Workaround:** Generate sample charts, manual one-time review, then lock down with screenshot tests

### 2. One-Time Manual Setup

#### Environment Setup
- ❌ Install CBECC 2022/2025
- ❌ Install EnergyPlus
- ❌ Install Honeybee-Energy
- ❌ Download weather files

**Why Not Automatable:** External dependencies

**Workaround:** Document setup thoroughly, use Docker/containers if possible

#### Test Data Curation
- ❌ Select representative test models
- ❌ Validate test models are correct
- ❌ Create test fixtures

**Why Not Automatable:** Requires initial manual selection

**Workaround:** One-time effort, then automated tests use curated set

---

## 📊 Automation Summary

| Test Category | Automation % | Implementation Time | Priority | Status |
|--------------|--------------|---------------------|----------|--------|
| **Format Import/Export** | 100% | 2-3 hours | HIGH | ⏳ Not started |
| **CBECC Simulation** | 90% | 4-6 hours | CRITICAL | ⏳ Not started |
| **EnergyPlus Simulation** | 85% | 3-4 hours | HIGH | ⏳ Not started |
| **Results Comparison** | 100% | 2 hours | MEDIUM | ⏳ Not started |
| **Visualization** | 95% | 1 hour | MEDIUM | ✅ Partial (tests exist) |
| **CSV Export** | 100% | - | MEDIUM | ✅ Complete |
| **Error Handling** | 100% | 2-3 hours | HIGH | ⏳ Not started |
| **Performance** | 90% | 2-3 hours | MEDIUM | ⏳ Not started |
| **CBECC Parser** | 100% | - | HIGH | ✅ Complete (18 tests) |

**Overall Automation Potential: 85-90%**

**Total Implementation Time: 16-24 hours** (2-3 days)

**Value: VERY HIGH** - Enables continuous validation and prevents regressions

---

## 🚀 Implementation Plan

### Phase 1: Critical Automation (Day 1-2)
**Goal:** Automate most critical workflows

**Priority 1: CBECC Simulation Tests** (4-6 hours)
- Set up test framework
- Implement basic simulation test
- Test with 2-3 sample files
- Validate parser integration

**Priority 2: Format Roundtrip Tests** (2-3 hours)
- Parametrize tests for all 13 CIBD22X files
- Parametrize tests for all 10 CIBD25 files
- Add data integrity checks

**Priority 3: Error Handling Tests** (2-3 hours)
- Test invalid inputs
- Test missing dependencies
- Validate error messages

**Deliverable:** Core automated test suite (40-50 tests)

### Phase 2: Extended Coverage (Day 3)
**Goal:** Add remaining automated tests

**Priority 4: EnergyPlus Tests** (3-4 hours)
- Set up EnergyPlus integration tests
- Test with small model
- Validate results parsing

**Priority 5: Performance Tests** (2-3 hours)
- Add performance monitoring
- Test with large model
- Generate performance baseline

**Priority 6: Comparison Tests** (2 hours)
- Expand unit tests
- Test edge cases

**Deliverable:** Comprehensive test suite (70-80 tests)

### Phase 3: CI/CD Integration (Optional)
**Goal:** Run tests automatically

- Configure pytest
- Create test runner script
- Add GitHub Actions workflow (if using)
- Generate coverage reports

**Deliverable:** Automated test pipeline

---

## 🛠️ Test Infrastructure Setup

### Required Packages
```bash
pip install pytest pytest-cov pytest-mock pytest-timeout
```

### pytest.ini Configuration
```ini
[pytest]
# Test discovery
python_files = test_*.py
python_classes = Test*
python_functions = test_*

# Test markers
markers =
    slow: marks tests as slow (deselect with '-m "not slow"')
    cbecc: marks tests requiring CBECC installation
    energyplus: marks tests requiring EnergyPlus
    performance: marks performance tests
    integration: marks integration tests
    unit: marks unit tests

# Coverage
addopts =
    --verbose
    --strict-markers
    --tb=short
    --cov=eco_tools
    --cov-report=html
    --cov-report=term-missing

# Timeouts
timeout = 300

# Test output
console_output_style = progress
```

### Directory Structure
```
tests/
├── __init__.py
├── conftest.py                    # Shared fixtures
├── unit/                          # Fast, isolated tests
│   ├── __init__.py
│   ├── test_cbecc_results_parser.py    ✅ EXISTS (18 tests)
│   ├── test_charts.py                   ✅ EXISTS (7 tests)
│   ├── test_csv_exporter.py             ✅ EXISTS
│   ├── test_comparison.py               ⏳ NEW
│   └── test_translators.py              ⏳ NEW
├── integration/                   # End-to-end tests
│   ├── __init__.py
│   ├── test_format_roundtrips.py        ⏳ NEW
│   ├── test_cbecc_simulation.py         ⏳ NEW
│   ├── test_energyplus_simulation.py    ⏳ NEW
│   ├── test_error_handling.py           ⏳ NEW
│   └── test_workflows.py                ⏳ NEW
├── performance/                   # Performance tests
│   ├── __init__.py
│   └── test_performance.py              ⏳ NEW
└── fixtures/                      # Test data
    ├── __init__.py
    ├── sample_models/
    └── expected_outputs/
```

### Shared Fixtures (conftest.py)
```python
# tests/conftest.py

import pytest
from pathlib import Path

@pytest.fixture
def sample_files_dir():
    """Path to sample files directory"""
    return Path(__file__).parent.parent / "reference_data" / "cbecc" / "CBECC Models"

@pytest.fixture
def all_cibd22x_files(sample_files_dir):
    """List of all CIBD22X sample files"""
    return list((sample_files_dir / "cibd22x").glob("*.cibd22x"))

@pytest.fixture
def all_cibd25_files(sample_files_dir):
    """List of all CIBD25 sample files"""
    return list((sample_files_dir / "2025 Sample Models" / "StandardModelTests").glob("*.cibd25"))

@pytest.fixture
def small_sample_model():
    """Small model for fast testing"""
    from eco_tools.translators.cibd22x import CIBD22XImporter
    input_file = "reference_data/cbecc/CBECC Models/cibd22x/020012-OffSml-CECStd.cibd22x"
    importer = CIBD22XImporter()
    return importer.import_file(input_file)

@pytest.fixture
def large_sample_model():
    """Large model (290 zones) for stress testing"""
    from eco_tools.translators.cibd22x import CIBD22XImporter
    input_file = "reference_data/cbecc/CBECC Models/Bressi Ranch/Bressi Ranch Apartments.cibd22x"
    importer = CIBD22XImporter()
    return importer.import_file(input_file)
```

---

## 📈 Test Execution Strategy

### Fast Feedback Loop (Unit Tests Only)
```bash
# Run only fast unit tests (< 1 second each)
pytest tests/unit/ -v

# Expected: ~30 tests in < 10 seconds
```

### Integration Tests (With Simulations)
```bash
# Run integration tests (may take 5-30 minutes)
pytest tests/integration/ -v -m "not slow"

# Run with CBECC (slow, may take hours)
pytest tests/integration/ -v -m cbecc
```

### Full Test Suite
```bash
# Run everything
pytest -v

# Run with coverage report
pytest --cov=eco_tools --cov-report=html
```

### Continuous Integration
```bash
# Fast CI pipeline (pre-commit)
pytest tests/unit/ -v --maxfail=1

# Full CI pipeline (nightly)
pytest -v --cov=eco_tools
```

---

## ✅ Success Criteria

### Automated Test Suite is "Complete" When:

1. ✅ **80+ automated tests** covering all modules
2. ✅ **>80% code coverage** (pytest-cov)
3. ✅ **All 13 CIBD22X files** tested in roundtrip
4. ✅ **All 10 CIBD25 files** tested in roundtrip
5. ✅ **CBECC simulation** tested with 3+ building types
6. ✅ **EnergyPlus workflow** tested end-to-end
7. ✅ **Error handling** tested for all failure modes
8. ✅ **Performance baseline** established for large models
9. ✅ **All tests pass** on clean repository
10. ✅ **CI/CD pipeline** runs tests automatically

### Manual Validation is "Complete" When:

1. ✅ One CBECC simulation manually reviewed by expert
2. ✅ One EnergyPlus simulation manually reviewed
3. ✅ Charts visually inspected and approved
4. ✅ Error messages verified as user-friendly
5. ✅ Performance acceptable on target hardware

---

## 🎯 ROI of Test Automation

### Time Investment
- **Initial:** 16-24 hours (2-3 days)
- **Maintenance:** ~1 hour/week

### Time Saved
- **Per development cycle:** 4-8 hours of manual testing
- **Per release:** 8-16 hours of regression testing
- **Per year:** 100+ hours

### Benefits
1. **Confidence:** Know immediately if changes break anything
2. **Speed:** Instant feedback vs hours of manual testing
3. **Coverage:** Test all 23 sample files vs manual spot checking
4. **Regression Prevention:** Catch bugs before they reach users
5. **Documentation:** Tests serve as executable specifications

**Break-even Point:** After 3-4 development cycles (~2-3 weeks)

---

## 📋 Recommended Next Steps

### Immediate (This Week)
1. **Set up test infrastructure** (2 hours)
   - Install pytest and plugins
   - Create directory structure
   - Configure pytest.ini

2. **Implement format roundtrip tests** (3 hours)
   - Test all 13 CIBD22X files
   - Test all 10 CIBD25 files
   - Add data integrity checks

3. **Implement CBECC simulation tests** (4-6 hours)
   - Test basic workflow
   - Test with 2-3 building types
   - Validate parser integration

**Deliverable:** 40-50 automated tests covering core functionality

### Short Term (Next Week)
4. **Add EnergyPlus tests** (3-4 hours)
5. **Add error handling tests** (2-3 hours)
6. **Add performance tests** (2-3 hours)

**Deliverable:** 70-80 automated tests with comprehensive coverage

### Long Term
7. **CI/CD integration** - Run tests automatically
8. **Nightly test runs** - Test with CBECC overnight
9. **Performance monitoring** - Track performance over time

---

## 🎉 Conclusion

**Key Insights:**
- **85-90% of MVP testing can be automated**
- **13 CIBD22X sample files** provide excellent test coverage
- **10 CIBD25 sample files** validate Title 24 2025 support
- **Existing unit tests** are a great foundation (25 tests already)
- **2-3 days investment** yields massive long-term efficiency

**Recommended Approach:**
1. Start with format roundtrip tests (easy wins)
2. Add CBECC simulation tests (critical path)
3. Expand coverage incrementally
4. Run automated tests before every commit

**Bottom Line:** With 2-3 days of focused effort, you can automate 85-90% of MVP validation and have confidence that ECO Tools works correctly for all major workflows.

---

**Created:** November 13, 2025
**Author:** ECO Tools Development Team
**Purpose:** Enable rapid, automated MVP validation
**Status:** Ready for implementation
