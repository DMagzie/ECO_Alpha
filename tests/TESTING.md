# LCCA Module Testing Guide

## Test Structure

The LCCA module has comprehensive test coverage organized into several categories:

### Test Files

| File | Tests | Purpose |
|------|-------|---------|
| `test_lcca_validation.py` | 34 | Hand-calculated value validation |
| `test_lcca_performance.py` | 16 | Performance benchmarks |
| `test_lcca_parsers.py` | 60 | Parser unit tests |
| `test_lcca_edge_cases.py` | 31 | Edge cases and error handling |
| `test_lcca_integration.py` | 29 | End-to-end integration |
| `test_tou_lcca.py` | 18 | TOU-native LCCA |
| `test_tou_validation.py` | 27 | TOU tariff validation |
| `test_sensitivity.py` | 32 | Sensitivity analysis |
| `test_project_context.py` | 48 | Project container |
| `test_ecm_bundle.py` | 29 | ECM bundle analysis |
| `test_scenario_manager.py` | 25 | Scenario management |
| `test_esg_report.py` | 35 | ESG/carbon calculations |
| `test_excel_econ1_export.py` | 27 | Excel and ECON-1 export |
| `test_gibraltar_regression.py` | 11 | Real project regression tests |
| `test_user_errors.py` | 29 | User error handling |

**Total: 451 tests**

### Shared Fixtures

Common test fixtures are in `tests/fixtures/lcca/conftest.py`:

```python
# Hourly data fixtures
minimal_hourly_data       # 8760 hours, constant load
realistic_office_hourly_data  # Realistic office profile
hourly_data_with_pv       # With PV generation
all_electric_hourly_data  # No gas
net_zero_hourly_data      # Net-zero building

# Scenario fixtures
baseline_scenario         # Standard baseline
proposed_scenario         # With PV
electrification_scenario  # All-electric

# Assumption fixtures
default_assumptions       # Standard LCCA assumptions
aggressive_assumptions    # Favorable to projects
conservative_assumptions  # Unfavorable to projects

# Known value fixtures (for validation)
known_npv_inputs         # Hand-calculated NPV
known_irr_inputs         # Hand-calculated IRR
known_payback_inputs     # Hand-calculated payback
```

## Running Tests

```bash
# All LCCA tests
pytest tests/test_lcca*.py tests/test_tou*.py tests/test_sensitivity.py \
       tests/test_project_context.py tests/test_ecm*.py tests/test_scenario*.py -v

# Specific category
pytest tests/test_lcca_validation.py -v     # Validation tests
pytest tests/test_lcca_performance.py -v    # Performance benchmarks

# With coverage
pytest tests/test_lcca*.py --cov=eco_tools.lcca --cov-report=html

# Skip slow tests
pytest tests/ -m "not slow"

# Performance benchmarks with timing
pytest tests/test_lcca_performance.py -v --durations=10
```

## Writing New Tests

### Calculator Tests

```python
from eco_tools.lcca import calculate_npv, calculate_irr

class TestMyCalculation:
    def test_known_value(self):
        """Document the expected value with calculation."""
        # NPV formula: NPV = -I + sum(CF_t / (1+r)^t)
        # For: $100k investment, $15k/yr for 10 years at 5%
        # Expected: $15,826.07
        cash_flows = [15_000] * 10
        result = calculate_npv(
            cash_flows,
            discount_rate=0.05,
            initial_investment=100_000
        )
        assert result == pytest.approx(15_826.07, rel=0.01)
```

### TOU Cost Tests

```python
from eco_tools.lcca import (
    HourlyEnergy,
    create_sce_tou_gs3,
    calculate_tou_costs,
    hourly_energy_to_usage,
)

def test_tou_period(self):
    """Test specific TOU period cost."""
    tariff = create_sce_tou_gs3()

    # Summer on-peak: 4pm-9pm, June-Sept
    hourly = [HourlyEnergy(
        month=8,       # August
        day=1,
        hour=17,       # 5pm
        elec_total_kwh=100.0,
    )]

    usage = hourly_energy_to_usage(hourly)
    breakdown = calculate_tou_costs(usage, tariff)

    # SCE TOU-GS-3 summer on-peak rate = $0.38/kWh
    assert breakdown.summer_on_peak_cost == pytest.approx(38.0, rel=0.1)
```

### Scenario Tests

```python
from eco_tools.lcca import TouLccaScenario, run_tou_lcca

def test_lcca_scenario(self):
    """Test full LCCA workflow."""
    tariff = create_sce_tou_gs3()

    baseline = TouLccaScenario(
        name="Baseline",
        hourly_data=hourly_data,
        tou_tariff=tariff,
        capex_upfront=0,
    )

    proposed = TouLccaScenario(
        name="Proposed",
        hourly_data=proposed_hourly,
        tou_tariff=tariff,
        capex_upfront=100_000,
    )

    results = run_tou_lcca(baseline, proposed)

    # Verify internal consistency
    assert results.annual_savings == pytest.approx(
        results.baseline_annual_cost - results.proposed_annual_cost,
        rel=0.001
    )
```

### Performance Tests

```python
import time

def test_operation_under_threshold(self):
    """Performance test with explicit threshold."""
    start = time.perf_counter()

    # ... perform operation ...

    elapsed = time.perf_counter() - start
    assert elapsed < 1.0, f"Operation took {elapsed:.2f}s"
```

## API Notes

### Calculator Functions

The `calculate_npv` and `calculate_irr` functions expect:
- `cash_flows`: List of annual cash flows for years 1-N (NOT including year 0)
- `initial_investment`: Year 0 cost as a positive value

```python
# Correct usage:
npv = calculate_npv(
    cash_flows=[15_000, 15_000, 15_000],  # Years 1-3
    discount_rate=0.05,
    initial_investment=50_000  # Year 0
)

# Formula: NPV = -initial_investment + sum(CF_t / (1+r)^t)
```

### TouCostBreakdown Attributes

```python
breakdown = calculate_tou_costs(usage, tariff)

# Energy costs
breakdown.summer_on_peak_cost
breakdown.summer_mid_peak_cost
breakdown.summer_off_peak_cost
breakdown.winter_on_peak_cost
breakdown.winter_mid_peak_cost
breakdown.winter_off_peak_cost
breakdown.total_energy_cost

# Demand costs
breakdown.facility_demand_cost
breakdown.summer_on_peak_demand_cost
breakdown.total_demand_cost

# Fixed costs
breakdown.customer_charges
breakdown.meter_charges
breakdown.total_fixed_cost

# Total
breakdown.total_cost
```

## Performance Benchmarks

Current benchmark targets:

| Operation | Target | Typical |
|-----------|--------|---------|
| Hourly data generation (8760) | < 1s | ~0.05s |
| TOU calculation (full year) | < 500ms | ~10ms |
| Single LCCA | < 3s | ~60ms |
| Parameter sweep (5 values) | < 5s | ~300ms |
| Tornado analysis (4 params) | < 15s | ~500ms |
| Monte Carlo (100 iterations) | < 30s | ~6s |
| Monte Carlo (500 iterations) | < 120s | ~28s |
