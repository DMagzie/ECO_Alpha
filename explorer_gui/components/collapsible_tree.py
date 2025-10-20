
from __future__ import annotations
from typing import Any, Mapping, Sequence
import streamlit as st

def _is_scalar(x: Any) -> bool:
    return isinstance(x, (str, int, float, bool)) or x is None

def render_collapsible_tree(data: Any, *, label: str = "root", level: int = 0, max_items: int = 500) -> None:
    if level == 0:
        st.caption("Collapsible view · click to expand sections")
    if max_items <= 0:
        st.warning("Tree truncated for display performance.")
        return
    if _is_scalar(data):
        st.write(f"**{label}:**", data)
        return
    if isinstance(data, Mapping):
        with st.expander(f"{label}  (dict · {len(data)})", expanded=(level == 0)):
            for k, v in data.items():
                render_collapsible_tree(v, label=str(k), level=level+1, max_items=max_items-1)
        return
    if isinstance(data, Sequence) and not isinstance(data, (str, bytes, bytearray)):
        with st.expander(f"{label}  (list · {len(data)})", expanded=False):
            for idx, item in enumerate(data):
                render_collapsible_tree(item, label=f"[{idx}]", level=level+1, max_items=max_items-1)
        return
    st.write(f"**{label}:**", repr(data))
