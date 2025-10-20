
from __future__ import annotations
import json
import difflib
import streamlit as st

def _to_pretty_json(obj) -> str:
    try:
        return json.dumps(obj, indent=2, sort_keys=True)
    except Exception:
        return json.dumps({"_error": "unserializable"}, indent=2)

def render_diff_viewer(left_obj, right_obj, left_label="Left", right_label="Right"):
    left = _to_pretty_json(left_obj)
    right = _to_pretty_json(right_obj)
    st.caption(f"Comparing **{left_label}** ↔ **{right_label}**")
    diff = difflib.unified_diff(left.splitlines(), right.splitlines(), fromfile=left_label, tofile=right_label, lineterm="")
    st.code("\n".join(diff) or "# No differences found", language="diff")
