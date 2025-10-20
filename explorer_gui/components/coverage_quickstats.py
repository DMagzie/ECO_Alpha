
"""Quick coverage/metric widgets reused across Import/Active Model panels."""
from __future__ import annotations
from typing import Any, Dict
import streamlit as st

def _safe_sum(vals):
    try:
        return float(sum(v for v in vals if isinstance(v, (int, float))))
    except Exception:
        return 0.0

def _iter_surfaces(em: Dict[str, Any]):
    # Try typical EM schema locations
    # Expected: em['geometry']['surfaces'] or em['surfaces'] (v4 carryover)
    paths = [
        ("geometry", "surfaces"),
        ("surfaces",),
    ]
    for p in paths:
        node = em
        ok = True
        for k in p:
            if isinstance(node, dict) and k in node:
                node = node[k]
            else:
                ok = False
                break
        if ok and isinstance(node, list):
            for s in node:
                if isinstance(s, dict):
                    yield s

def _surface_area(s: Dict[str, Any]) -> float:
    # prefer explicit area, fallback to meta; keep robust
    for key in ("area", "net_area", "gross_area"):
        v = s.get(key)
        if isinstance(v, (int, float)):
            return float(v)
    return 0.0

def _is_exterior(s: Dict[str, Any]) -> bool:
    b = s.get("boundary", s.get("boundary_condition", "")) or ""
    return str(b).lower() in {"exterior", "outdoors", "ground"}

def _surf_type(s: Dict[str, Any]) -> str:
    t = s.get("type", s.get("surface_type", "")) or ""
    return str(t).lower()

def render_quickstats(em: Dict[str, Any]) -> None:
    if not isinstance(em, dict):
        st.info("No active model.")
        return

    ext_wall_area = 0.0
    roof_area = 0.0
    floor_area = 0.0
    total_surfaces = 0

    for s in _iter_surfaces(em):
        total_surfaces += 1
        if not _is_exterior(s):
            continue
        a = _surface_area(s)
        t = _surf_type(s)
        if "wall" in t:
            ext_wall_area += a
        elif "roof" in t or "ceiling" in t:
            roof_area += a
        elif "floor" in t or "slab" in t:
            floor_area += a

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Surfaces", f"{total_surfaces:,}")
    c2.metric("Ext. Wall Area (sf)", f"{ext_wall_area:,.1f}")
    c3.metric("Roof Area (sf)", f"{roof_area:,.1f}")
    c4.metric("Floor Area (sf)", f"{floor_area:,.1f}")
