from __future__ import annotations
from typing import Any, Dict, Iterable, Tuple

EnvelopeTotals = Dict[str, float]

def _iter_surfaces(em: Dict[str, Any]) -> Iterable[Dict[str, Any]]:
    if not isinstance(em, dict):
        return
    scenarios = em.get("scenarios") or []
    if scenarios and isinstance(scenarios[0], dict):
        zones = scenarios[0].get("zones") or []
        for z in zones or []:
            for s in (z or {}).get("surfaces") or []:
                if isinstance(s, dict):
                    yield s
    for s in em.get("surfaces") or []:
        if isinstance(s, dict):
            yield s

def _kind(s: Dict[str, Any]) -> str:
    for k in ("type", "surface_type", "category", "kind"):
        v = (s.get(k) or "").lower()
        if not v: continue
        if "wall" in v: return "wall"
        if "roof" in v or "ceiling" in v: return "roof"
        if "floor" in v or "slab" in v: return "floor"
    return ""

def _is_exterior(s: Dict[str, Any]) -> bool:
    if str(s.get("is_exterior", "")).lower() in ("true", "1", "yes"):
        return True
    for k in ("type", "surface_type", "category", "boundary"):
        v = (s.get(k) or "").lower()
        if "exterior" in v or "outdoor" in v or v in ("outdoors", "ambient"):
            return True
    return False

def _area(s: Dict[str, Any]) -> float:
    try:
        a = float(s.get("area", 0.0) or 0.0)
        if a > 0: return a
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
    ext = {"wall": 0.0, "roof": 0.0, "floor": 0.0, "total": 0.0}
    all_ = {"wall": 0.0, "roof": 0.0, "floor": 0.0, "total": 0.0}
    for s in _iter_surfaces(em):
        k = _kind(s)
        a = _area(s)
        if k in all_:
            all_[k] += a
            all_["total"] += a
            if _is_exterior(s):
                ext[k] += a
                ext["total"] += a
    for d in (ext, all_):
        for k in d:
            d[k] = round(float(d[k]), 3)
    return ext, all_
