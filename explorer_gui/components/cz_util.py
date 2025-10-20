
from __future__ import annotations
from typing import Dict, Any, Optional
from em_core.prescriptive.climate_zones import lookup_climate_zone

def _ensure_path(d: Dict[str, Any], *keys: str) -> Dict[str, Any]:
    cur = d
    for k in keys:
        if k not in cur or not isinstance(cur[k], dict):
            cur[k] = {}
        cur = cur[k]
    return cur

def compute_and_apply_climate_zone(model: Dict[str, Any], *, default_zip: Optional[str] = None) -> Dict[str, Any]:
    project = model.get("project", {})
    loc = project.get("location", {})
    cz = loc.get("climate_zone")

    if not cz:
        zip_code = loc.get("zip") or default_zip
        cz = lookup_climate_zone(zip_code) if zip_code else None

    target_loc = _ensure_path(model, "project", "location")
    target_loc["climate_zone"] = cz

    meta = _ensure_path(model, "metadata")
    meta["climate_zone"] = cz

    return model
