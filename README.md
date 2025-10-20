# README.md
# AlphaV5 — EMJSON v5 ⟷ CBECC .cibd22x

A minimal, tested toolchain for round-tripping between **EMJSON v5** and **CBECC .cibd22x**:
- Import: `cbecc/translate_cibd22x_to_v5.py`
- Export: `cbecc/export_emjson_v5_to_cibd22x.py`
- Explorer GUI (Streamlit): under `explorer_gui/`

All core tests pass (`pytest`), including HVAC, zones/surfaces, and window dual-form emission for import compatibility.

---

## Quickstart

### 1) Create venv (Python 3.11) & install deps
```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
