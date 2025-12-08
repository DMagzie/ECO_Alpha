# Existing LCCA Code Inventory

This document catalogs all existing LCCA-related code that can be reused or consolidated.

## Primary Scaffold: EM_Projects/v5 Other/lcca_track/

**Status:** Most complete implementation, ready for porting

### Core Model (`lcca_model.py`)
```python
@dataclass
class CashFlow:
    year: int
    amount: float
    label: str = ""

@dataclass
class ScenarioAssumptions:
    analysis_years: int = 20
    discount_rate_real: float = 0.03
    inflation_rate: float = 0.025
    tax_rate: float = 0.0
    salvage_value: float = 0.0
    include_carbon_costs: bool = False
    carbon_price_per_ton: float = 0.0

@dataclass
class EnergyStreams:
    electricity_kwh: float = 0.0
    gas_therms: float = 0.0
    demand_kw: float = 0.0

@dataclass
class Tariff:
    elec_rate_per_kwh: float = 0.25
    gas_rate_per_therm: float = 1.80
    demand_rate_per_kw: float = 18.0

@dataclass
class Incentive:
    name: str
    amount: float
    pays_in_year: int = 0

@dataclass
class LccaScenario:
    name: str
    capex_upfront: float
    opex_annual_delta: float = 0.0
    maintenance_annual_delta: float = 0.0
    energy: EnergyStreams
    tariff: Tariff
    incentives: List[Incentive]
    extra_cashflows: List[CashFlow]
    assumptions: ScenarioAssumptions

    def annual_energy_cost_delta(self) -> float:
        e = self.energy; t = self.tariff
        return (e.electricity_kwh * t.elec_rate_per_kwh) + \
               (e.gas_therms * t.gas_rate_per_therm) + \
               (e.demand_kw * t.demand_rate_per_kw)
```

### Calculators

**`calculators/npv.py`**
```python
def npv(rate: float, cashflows: List[float]) -> float:
    total = 0.0
    for t, cf in enumerate(cashflows):
        total += cf / ((1 + rate) ** t)
    return total
```

**`calculators/irr.py`**
```python
def irr(cashflows: List[float], guess: float = 0.1,
        tol: float = 1e-6, max_iter: int = 100) -> float:
    # Newton-Raphson iteration
    r = guess
    for _ in range(max_iter):
        f = sum(cf / (1 + r) ** t for t, cf in enumerate(cashflows))
        df = sum(-t * cf / (1 + r) ** (t + 1) for t, cf in enumerate(cashflows) if t > 0)
        if abs(df) < 1e-12:
            break
        step = f / df
        r -= step
        if abs(step) < tol:
            return r
    return r
```

**`calculators/simple_payback.py`**
- Simple payback period calculation

### CLI (`cli/lcca_cli.py`)
```bash
python -m lcca.cli.lcca_cli \
    --capex 1000000 \
    --elec-kwh -250000 \
    --gas-therms 5000 \
    --demand-kw 100 \
    --discount 0.03 \
    --years 20 \
    --incentive "Utility:100000:1"
```

### Incentives Engine (`incentives/rules_engine.py`)
```python
@dataclass
class Context:
    climate_zone: str = ""
    zipcode: str = ""
    building_type: str = ""
    floor_area_sf: float = 0.0
    carbon_reduction_tons: float = 0.0
    energy_savings_kwh: float = 0.0

def evaluate_all(ctx: Context) -> List[Dict[str, Any]]:
    # Evaluates NYSERDA, C-PACE providers
```

### ECON-1 PDF (`econ1/econ1_pdf.py`)
- Uses reportlab for PDF generation
- Basic template structure

### Config Files
- `config/discount_rates.yaml` - Federal, commercial, municipal rates
- `config/inflation.yaml` - Inflation rate
- `config/tariffs_tou.yaml` - TOU rate structures

---

## SNO LCCA: Documents/SNO/lcca/

**Status:** Working prototypes for CostDB and ECON-1

### `load_costdb.py`
```python
def load_cost_database(file_path="Reference_Documents/CostDB_v0.05.xlsx"):
    xls = pd.ExcelFile(file_path)
    return {
        "system_costs": pd.read_excel(xls, 'System Costs'),
        "material_costs": pd.read_excel(xls, 'Material Costs'),
        "labor_markups": pd.read_excel(xls, 'Labor Markups'),
        "escalation": pd.read_excel(xls, 'Escalation')
    }
```

### `generate_econ1.py`
```python
def generate_econ1(em_json_path, cost_db_path, output_path):
    # Reads EMJSON model
    # Loads CostDB
    # Outputs basic ECON-1 summary to Excel
```

### `summarize_material_impact.py`
- Material impact calculations (790 LOC)

---

## Config Files Available

### discount_rates.yaml
```yaml
federal: 0.03
commercial: 0.08
municipal: 0.04
```

### inflation.yaml
```yaml
general: 0.025
```

### tariffs_tou.yaml
```yaml
on_peak_rate: 0.35
off_peak_rate: 0.15
demand_rate: 18.0
```

---

## Sample Data Files

### sample_scenarios.json
```json
{
  "scenarios": [
    {
      "name": "HPWH Central Plant",
      "capex_upfront": 1200000,
      "elec_kwh": -350000,
      "gas_therms": 20000,
      "demand_kw": -40,
      "incentives": [{"name": "Utility Rebate", "amount": 150000, "pays_in_year": 1}]
    },
    {
      "name": "Baseline Gas Boiler",
      "capex_upfront": 600000,
      "elec_kwh": 20000,
      "gas_therms": -25000,
      "demand_kw": 5,
      "incentives": []
    }
  ]
}
```

---

## Files to Port to eco_tools/lcca/

| Source | Target | Priority |
|--------|--------|----------|
| `lcca_track/lcca_model.py` | `eco_tools/lcca/model.py` | High |
| `lcca_track/calculators/npv.py` | `eco_tools/lcca/calculators/npv.py` | High |
| `lcca_track/calculators/irr.py` | `eco_tools/lcca/calculators/irr.py` | High |
| `lcca_track/calculators/simple_payback.py` | `eco_tools/lcca/calculators/payback.py` | High |
| `SNO/lcca/load_costdb.py` | `eco_tools/lcca/costs/costdb.py` | Medium |
| `lcca_track/incentives/rules_engine.py` | `eco_tools/lcca/incentives/engine.py` | Medium |
| `lcca_track/econ1/econ1_pdf.py` | `eco_tools/lcca/reports/econ1.py` | Low |
| `lcca_track/cli/lcca_cli.py` | Reference only | Low |

---

## Dependencies Required

```
# Core
pandas
openpyxl
pyyaml

# PDF generation
reportlab

# Optional
numpy  # For array operations
```
