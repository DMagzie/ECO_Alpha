# explorer_gui/metrics/area_rollups.py
from __future__ import annotations
from typing import Dict, Any, Tuple, Iterable

EnvelopeTotals = Dict[str, float]

def _iter_surfaces_from_em(em: Dict[str, Any]) -> Iterable[Dict[str, Any]]:
    """
    Yield surface-like dicts from EMJSON v5/v6.
    Looks in scenarios[0].zones[*].surfaces and also a flat model["surfaces"] fallback.
    """
    if not isinstance(em, dict):
        return
    # Preferred: scenarios[0].zones[*].surfaces
    scenarios = em.get("scenarios") or []
    if scenarios and isinstance(scenarios[0], dict):
        zones = scenarios[0].get("zones") or []
        for z in zones or []:
            for s in (z or {}).get("surfaces") or []:
                if isinstance(s, dict):
                    yield s
    # Fallback: top-level surfaces (some branches store here)
    for s in em.get("surfaces") or []:
        if isinstance(s, dict):
            yield s

def _surface_kind(s: Dict[str, Any]) -> str:
    """
    Normalize a surface 'kind' (wall/roof/floor) from common fields:
    - s["type"] in {"ExteriorWall","ExteriorRoof","ExteriorFloor",...}
    - s["category"] or s["surface_type"] e.g. "wall"/"roof"/"floor"
    """
    for key in ("type", "surface_type", "category", "kind"):
        v = (s.get(key) or "").lower()
        if not v:
            continue
        if "wall" in v:
            return "wall"
        if "roof" in v or "ceiling" in v:
            return "roof"
        if "floor" in v or "slab" in v:
            return "floor"
    return ""

def _is_exterior(s: Dict[str, Any]) -> bool:
    """
    Heuristics for exterior-ness: explicit flag, or type/category contains 'exterior'.
    """
    if str(s.get("is_exterior", "")).lower() in ("true", "1", "yes"):
        return True
    for key in ("type", "surface_type", "category", "boundary"):
        v = (s.get(key) or "").lower()
        if "exterior" in v or "outdoor" in v or v in ("outdoors", "ambient"):
            return True
    return False

def _area_val(s: Dict[str, Any]) -> float:
    """
    Prefer s["area"], else compute width*height if present; otherwise 0.
    """
    try:
        a = float(s.get("area", 0.0) or 0.0)
        if a > 0:
            return a
    except Exception:
        pass
    try:
        w = float(s.get("width", 0.0) or 0.0)
        h = float(s.get("height", 0.0) or 0.0)
        a = w * h
        return a if a > 0 else 0.0
    except Exception:
        return 0.0

def envelope_area_rollups(em: Dict[str, Any]) -> Tuple[EnvelopeTotals, EnvelopeTotals]:
    """
    Returns:
      (exterior_totals, all_totals) where each dict has keys:
      {'wall': <ft²>, 'roof': <ft²>, 'floor': <ft²>, 'total': <ft²>}
    """
    ext = {"wall": 0.0, "roof": 0.0, "floor": 0.0, "total": 0.0}
    all_ = {"wall": 0.0, "roof": 0.0, "floor": 0.0, "total": 0.0}

    for s in _iter_surfaces_from_em(em):
        kind = _surface_kind(s)
        area = _area_val(s)
        if kind in all_:
            all_[kind] += area
            all_["total"] += area
            if _is_exterior(s):
                ext[kind] += area
                ext["total"] += area

    # round a touch for display
    for d in (ext, all_):
        for k, v in d.items():
            d[k] = round(float(v), 3)
    return ext, all_
