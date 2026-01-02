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

## 🐛 Bug Fixes (Critical)

### POLY-001: Polyloop Parser Duplicate Surface Bug

**Priority**: High
**Documentation**: `docs/knowledge_base/BUG_POLYLOOP_DUPLICATE_SURFACES.md`

**Problem**: The surface parser in `surface_parser.py` (lines 87-96) uses nested loops that cause slab-on-grade floors to be parsed twice, resulting in:
- Doubled floor area for affected zones
- Halved ceiling height calculations
- Incorrect HVAC sizing (2x oversized)
- Incorrect LCCA normalized metrics (kWh/SF)

**Affected Project**: Gibralter Distribution Center (break room)

**Root Cause**: `zone_elem.iter()` traverses ALL descendants instead of direct children, combined with floor elements matching multiple surface tags (`ExtFlr` and `UndgrFlr`).

**Fix Tasks**:
- [ ] Replace `zone_elem.iter()` with direct child iteration in `parse_surfaces()`
- [ ] Add unit test for single-floor-per-zone validation
- [ ] Add regression test for Gibralter break room area
- [ ] Verify fix doesn't break existing translations
- [ ] Update `GIBRALTAR_LESSONS_LEARNED.md` with resolution

**Acceptance Criteria**:
- Gibralter break room floor appears exactly once in parsed output
- Break room area matches CBECC GUI value
- All existing tests pass
- No new regressions in other sample projects

---

## 📅 Tagging Milestones

| Tag | Description |
|-----|-------------|
| `v0.9-MVP` | Initial testable release |
| `v0.10-beta` | Post-MVP feature integration |
| `v1.0` | Public-ready stable release |

---

