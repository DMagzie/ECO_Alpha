# em_core/validate.py
from __future__ import annotations
from numbers import Number
from typing import Dict, Any, List
from .normalize import normalize_for_ui

def rich_validate(model: dict) -> Dict[str, Any]:
    m = normalize_for_ui(model)
    errors: List[str] = []
    warnings: List[str] = []
    zone_issues: List[Dict[str, Any]] = []

    # project name
    proj = m.get("project") or m.get("metadata") or {}
    name = (isinstance(proj, dict) and (proj.get("name") or proj.get("project_name"))) or m.get("project_name") or m.get("name")
    if not isinstance(name, str) or not name.strip():
        errors.append("Missing project name.")

    # climate zone
    cz = m.get("climate_zone") or (isinstance(proj, dict) and proj.get("climate_zone")) \
         or ((isinstance(proj, dict) and isinstance(proj.get("location"), dict)) and proj["location"].get("climate_zone"))
    if not (isinstance(cz, (str, int)) and (str(cz).strip() if isinstance(cz, str) else True)):
        errors.append("Missing climate zone.")

    zones = m.get("zones") or []
    if not isinstance(zones, list) or not zones:
        errors.append("Missing zones list.")
    else:
        for i, z in enumerate(zones):
            z_err, z_warn = [], []
            if not isinstance(z, dict):
                zone_issues.append({"zone_index": i, "zone_name": None, "errors": ["Zone is not an object"], "warnings": []})
                continue
            zname = z.get("name") or z.get("id")
            if not isinstance(zname, str) or not zname.strip():
                z_err.append("Missing zone.name")
            area = z.get("area") or z.get("floor_area") or z.get("gross_area")
            if not isinstance(area, Number) or float(area) <= 0:
                z_err.append("Missing/invalid zone area (> 0)")
            if z.get("volume") is None:
                z_warn.append("No zone volume")
            if (z.get("surfaces") or z.get("envelope")) is None:
                z_warn.append("No zone surfaces list")
            if (z.get("hvac") or z.get("system")) is None:
                z_warn.append("No zone HVAC/system reference")
            if z_err or z_warn:
                zone_issues.append({"zone_index": i, "zone_name": (zname if isinstance(zname, str) else None),
                                    "errors": z_err, "warnings": z_warn})
    ok = (len(errors) == 0) and all(len(zi["errors"]) == 0 for zi in zone_issues)
    return {"ok": ok, "errors": errors, "warnings": warnings, "zone_issues": zone_issues}
