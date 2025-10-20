# em_core/model_state.py
from __future__ import annotations
from pathlib import Path
from typing import Optional
import json

ROOT = Path(__file__).resolve().parents[1]
CACHE_DIR = ROOT / ".cache"
CACHE_DIR.mkdir(parents=True, exist_ok=True)
CACHE_ACTIVE = CACHE_DIR / "active_model.json"
UPLOAD_COPY = CACHE_DIR / "last_upload.json"

def save_active_model(model: dict, source: Optional[str] = None, path: Optional[str] = None) -> None:
    """Save to Streamlit session_state if present + write-through cache on disk."""
    try:
        import streamlit as st  # type: ignore
        st.session_state["em_model"] = model
        if source is not None:
            st.session_state["em_model_source"] = source
        if path is not None:
            st.session_state["em_model_path"] = path
    except Exception:
        pass
    try:
        CACHE_ACTIVE.write_text(json.dumps(model, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        pass

def get_active_model() -> dict:
    """Load from session_state → cache → minimal default."""
    # 1) session
    try:
        import streamlit as st  # type: ignore
        m = st.session_state.get("em_model")
        if isinstance(m, dict):
            return m
    except Exception:
        pass
    # 2) disk
    try:
        if CACHE_ACTIVE.exists():
            return json.loads(CACHE_ACTIVE.read_text(encoding="utf-8"))
    except Exception:
        pass
    # 3) minimal default (valid enough for GUI)
    return {
        "project": {
            "name": "Sample Project",
            "location": {"country": "USA", "climate_zone": "CZ01"},
            "climate_zone": "CZ01",
        },
        "climate_zone": "CZ01",
        "climate": "CZ01",
        "scenarios": [
            {"name": "Proposed", "type": "proposed",
             "zones": [{"name": "Zone 1", "spaces": [{"name": "Space 1", "geometry": {"floor_area_m2": 50.0}}]}]}],
    }
