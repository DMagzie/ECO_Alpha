# em_core/em_coverage.py
from __future__ import annotations
from typing import Dict, Any

def compute_coverage_v41(model: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(model, dict):
        return {}
    zones = 0
    surfaces_total = 0
    for sc in (model.get("scenarios") or []):
        zlist = sc.get("zones") or []
        zones += len(zlist)
        for z in zlist:
            surfaces_total += len(z.get("surfaces") or [])
            # if someone stores walls under envelope.walls, count those too
            env = z.get("envelope") or {}
            for w in (env.get("walls") or []):
                surfaces_total += 1
                surfaces_total += len((w or {}).get("windows") or [])

    cats = model.get("catalogs") or {}
    libs = model.get("libraries") or {}  # mirror, if present
    der  = model.get("site_der") or {}
    # accept both catalogs and libraries
    def _count(k):
        v = (cats.get(k) or libs.get(k) or [])
        return len(v) if isinstance(v, list) else 0

    out = {
        "project": bool(model.get("project")),
        "climate_zone": model.get("climate_zone") or (model.get("project") or {}).get("climate_zone"),
        "zones": zones,
        "surfaces_total": surfaces_total,
        "window_types": _count("window_types"),
        "du_types": _count("du_types"),
        "res_heat_pumps": _count("res_heat_pumps"),
        "pv_arrays": len(der.get("pv_arrays") or []),
        "inverters": len(der.get("inverters") or []),
        "batteries": len(der.get("batteries") or []),
        "gross_floor_area_m2": (model.get("building") or {}).get("gross_floor_area_m2"),
    }
    return out
