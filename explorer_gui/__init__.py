# explorer_gui/__init__.py
def _shim(name: str):
    def _render():
        import streamlit as st
        st.warning(f"Panel '{name}' is not available or failed to import.")
    return _render

try:
    from .cbecc_import_panel import render_cbecc_v5_import_panel
except Exception:
    render_cbecc_v5_import_panel = _shim("render_cbecc_v5_import_panel")

try:
    from .export_panel import render_export_panel_v5
except Exception:
    render_export_panel_v5 = _shim("render_export_panel_v5")

try:
    from .diff_panel import render_diff_panel_v5, compare_emjson_v5_and_cibd22x
except Exception:
    render_diff_panel_v5 = _shim("render_diff_panel_v5")
    def compare_emjson_v5_and_cibd22x(*_a, **_k): return "diff unavailable"

try:
    from .active_model_panel import render_active_model_panel_v5
except Exception:
    render_active_model_panel_v5 = _shim("render_active_model_panel_v5")

try:
    from .dev_panel import render_dev_panel_v5
except Exception:
    render_dev_panel_v5 = _shim("render_dev_panel_v5")

__all__ = [
    "render_cbecc_v5_import_panel",
    "render_export_panel_v5",
    "render_diff_panel_v5",
    "compare_emjson_v5_and_cibd22x",
    "render_active_model_panel_v5",
    "render_dev_panel_v5",
]
