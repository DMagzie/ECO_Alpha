
from __future__ import annotations
import json
import streamlit as st

def render_raw_json(obj, title="Raw JSON"):
    with st.expander(title, expanded=False):
        try:
            st.code(json.dumps(obj, indent=2), language="json")
        except Exception:
            st.write(obj)

def render_raw_text(text: str, title="Raw Text / XML", language: str | None = None):
    with st.expander(title, expanded=False):
        if language:
            st.code(text or "", language=language)
        else:
            st.text(text or "")
