
"""Explorer GUI shared session-state utilities for EM Tools (Alpha v5).
Zero-arg safe and side-effect light. Import in panels as:
    from explorer_gui.state import get_state, set_active_model, get_active_model, get_diagnostics
"""
from __future__ import annotations
from typing import Any, Dict, Tuple, Optional
import streamlit as st

# ---- canonical keys (avoid typos across modules) ----
K_ACTIVE_MODEL = "active_model"     # dict (EM v5 or v6)
K_ACTIVE_MODEL_VERSION = "active_model_version"  # "v5" or "v6"
K_DIAGNOSTICS = "diagnostics"       # list[dict]
K_RAW_XML = "raw_xml"               # str
K_WRITER_PREVIEW = "writer_preview" # dict|str
K_LAST_FILE_NAME = "last_file_name" # str
K_LAST_FILE_SIZE = "last_file_size" # int

def get_state() -> Dict[str, Any]:
    ss = st.session_state
    # Initialize keys if missing to keep modules zero-arg-safe
    ss.setdefault(K_ACTIVE_MODEL, None)
    ss.setdefault(K_ACTIVE_MODEL_VERSION, None)
    ss.setdefault(K_DIAGNOSTICS, [])
    ss.setdefault(K_RAW_XML, "")
    ss.setdefault(K_WRITER_PREVIEW, None)
    ss.setdefault(K_LAST_FILE_NAME, "")
    ss.setdefault(K_LAST_FILE_SIZE, 0)
    return ss

def set_active_model(model: dict | None, version: Optional[str] = None) -> None:
    ss = get_state()
    ss[K_ACTIVE_MODEL] = model
    if version in {"v5", "v6"}:
        ss[K_ACTIVE_MODEL_VERSION] = version

def get_active_model() -> Tuple[Optional[dict], Optional[str]]:
    ss = get_state()
    return ss[K_ACTIVE_MODEL], ss[K_ACTIVE_MODEL_VERSION]

def set_diagnostics(diags: list[dict]) -> None:
    get_state()[K_DIAGNOSTICS] = diags or []

def get_diagnostics() -> list[dict]:
    return get_state()[K_DIAGNOSTICS]

def set_raw_xml(text: str) -> None:
    get_state()[K_RAW_XML] = text or ""

def get_raw_xml() -> str:
    return get_state()[K_RAW_XML]

def set_writer_preview(preview: dict | str | None) -> None:
    get_state()[K_WRITER_PREVIEW] = preview

def get_writer_preview() -> dict | str | None:
    return get_state()[K_WRITER_PREVIEW]
