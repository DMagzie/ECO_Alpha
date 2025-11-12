# explorer_gui/model_state.py
from __future__ import annotations
from pathlib import Path
from typing import Any
import json, re

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]

# Disk cache for the active model
CACHE_DIR = ROOT / ".cache"
CACHE_DIR.mkdir(parents=True, exist_ok=True)
CACHE_ACTIVE = CACHE_DIR / "active_model.json"

def _norm_cz(v: Any) -> str:
    if v is None: return ""
    s = str(v).strip()
    m = re.match(r'^(?:cz\s*)?(\d{1,2})$', s, re.IGNORECASE)
    return f"CZ{int(m.group(1)):02d}" if m else s

def ensure_cz_canonical(model: dict) -> dict:
    """Mirror any climate zone value into all canonical slots; mutate+return."""
    proj = dict(model.get("project") or {})
    loc  = dict(proj.get("location") or {})
    cz = (
        model.get("climate_zone") or model.get("climate") or
        proj.get("climate_zone") or loc.get("climate_zone")
    )
    if not cz:
        return model
    cz = _norm_cz(cz)
    model["climate_zone"] = cz
    model["climate"] = cz
    proj["climate_zone"] = cz
    loc["climate_zone"] = cz
    proj["location"] = loc
    model["project"] = proj
    return model

def _sample_path() -> Path:
    cands = [
        ROOT / "explorer_gui" / "assets" / "sample_models" / "normalized_model_sample.json",
        ROOT / "explorer_gui" / "assets" / "sample_models" / "em_minimal.json",
        ROOT / "assets" / "em_minimal.json",
        ROOT / "prelim_json_sample" / "m.json",
    ]
    for p in cands:
        if p.exists():
            return p
    return Path()

def default_model() -> dict:
    # Minimal but valid shell
    return {
        "project": {
            "name": "Sample Project",
            "location": {"city": "", "state": "", "country": "USA", "climate_zone": "CZ01"},
            "climate_zone": "CZ01",
        },
        "climate_zone": "CZ01",
        "climate": "CZ01",
        "scenarios": [
            {
                "name": "Proposed",
                "type": "proposed",
                "zones": [
                    {"name": "Zone 1", "spaces": [{"name": "Space 1", "geometry": {"floor_area_m2": 50.0}}]}
                ],
            }
        ],
    }

def save_active_model(m: dict, source: str | None = None, path: str | None = None) -> None:
    # session (best-effort)
    try:
        import streamlit as st  # type: ignore
        st.session_state["em_model"] = m
        if source is not None: st.session_state["em_model_source"] = source
        if path is not None:   st.session_state["em_model_path"] = path
    except Exception:
        pass
    # disk
    try:
        CACHE_ACTIVE.write_text(json.dumps(m, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        pass

def _load_cached_model() -> dict | None:
    try:
        if CACHE_ACTIVE.exists():
            return json.loads(CACHE_ACTIVE.read_text(encoding="utf-8"))
    except Exception:
        return None
    return None

def get_active_model() -> dict:
    """Order: session → disk cache → bundled sample → default; always CZ-canonical."""
    # session
    try:
        import streamlit as st  # type: ignore
        m = st.session_state.get("em_model")
        if isinstance(m, dict):
            return ensure_cz_canonical(m)
    except Exception:
        pass
    # disk cache
    m = _load_cached_model()
    if isinstance(m, dict):
        return ensure_cz_canonical(m)
    # bundled sample
    sp = _sample_path()
    if sp and sp.exists():
        try:
            m = json.loads(sp.read_text(encoding="utf-8"))
            m = ensure_cz_canonical(m)
            save_active_model(m, source="sample", path=str(sp))
            return m
        except Exception:
            pass
    # fallback
    m = default_model()
    m = ensure_cz_canonical(m)
    save_active_model(m, source="default", path=None)
    return m
