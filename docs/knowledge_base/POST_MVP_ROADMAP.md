# 🚀 EM Tools Post-MVP Development Roadmap

This document outlines the priorities and sequencing of tasks after the MVP release (`v0.9-MVP`).

---

## ✅ Immediate Goals (Week 1)

### 🔍 Manual Validation (You)
- [ ] Push and tag the repo with `v0.9-MVP`
- [ ] Run CLI scripts and GUI (`streamlit_app.py`)
- [ ] Run tests with `pytest` or GitHub Actions
- [ ] Validate:
  - `baseline_generator.py` — generates valid baseline
  - `scenario_manager.py` — manages scenario configs
  - `lcca_main_v0_05.py` — processes financial outputs
  - `write_to_excel.py` — populates `.xlsm` accurately
  - `streamlit_app.py` — launches and toggles UI

---

## 🧪 Core Module Testing + QA (Week 1–2)

| Module | Task | Owner |
|--------|------|-------|
| `tests/` | Expand test coverage | You |
| `validate_openstudio_results.py` | Parse EnergyPlus/OS results and compare to baseline | GPT |
| Sample scenario QA | Add real use-case test runs | You |

---

## ⚙️ Background Module Development (Week 2+)

### 🧰 EnergyPlus Track
- [ ] `export_to_osm.py` — convert EM JSON to `.osm`
- [ ] `batch_run_openstudio.py` — automate simulation runs
- [ ] `validate_openstudio_results.py` — verify result integrity

### 📤 Export Logic
- [ ] Expand `export_to_cbecc_ief.py` — complete baseline toggling
- [ ] Begin `export_to_iesve.py` validation with real samples

---

## 🎛️ Explorer GUI Expansion
- [ ] Add sidebar tabs: “Scenario Overview”, “Energy”, “Cost”
- [ ] Add editable GUI blocks (HVAC + Schedule Editors)
- [ ] Add dashboard page using Plotly
- [ ] Add “Export Scenario” buttons (EnergyPlus, Excel)

---

## 🧱 Structural Additions (Optional)
- [ ] Add `.coveragerc` — ignore tests in Codecov
- [ ] Add `CONTRIBUTING.md` for collaborators
- [ ] Add `__version__.py` across modules
- [ ] Use `setup.py` or `pyproject.toml` for installable CLI tools

---

## 📅 Tagging Milestones

| Tag | Description |
|-----|-------------|
| `v0.9-MVP` | Initial testable release |
| `v0.10-beta` | Post-MVP feature integration |
| `v1.0` | Public-ready stable release |

---

