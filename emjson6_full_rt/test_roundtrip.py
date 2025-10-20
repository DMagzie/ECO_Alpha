from __future__ import annotations
import json, tempfile, os
from typing import Dict, Any
from translate_cibd22x_to_v6 import translate_cibd22x_to_v6
from emjson6_to_cibd22x import write_xml

def invariants(em: Dict[str, Any]) -> Dict[str, Any]:
    g = em.get("geometry", {}) or {}
    zones = g.get("zones", []) or []
    surfs = g.get("surfaces", {}) or {}
    opens = g.get("openings", {}) or {}
    return {
        "zone_names": sorted([z.get("name") or z.get("id") for z in zones]),
        "zone_multipliers": sorted([(z.get("name"), int(z.get("effective_multiplier") or 1)) for z in zones]),
        "surf_counts": {k: len(v or []) for k,v in surfs.items()},
        "opening_counts": {k: len(v or []) for k,v in opens.items()},
        "hvac_count": len((em.get("hvac_systems") or [])),
        "du_type_count": len((em.get("du_types") or [])),
        "win_type_count": len((em.get("window_types") or [])),
        "const_type_count": len((em.get("construction_types") or [])),
        "pv_count": len((em.get("pv_systems") or [])),
        "dhw_count": len((em.get("dhw_systems") or [])),
        "location": em.get("project",{}).get("location",{}),
    }

def roundtrip_em_to_xml_to_em(em: Dict[str, Any]) -> Dict[str, Any]:
    with tempfile.TemporaryDirectory() as td:
        xml_path = os.path.join(td, "out.xml")
        write_xml(em, xml_path)
        em2 = translate_cibd22x_to_v6(xml_path)
        return em2

def assert_near(a: int, b: int, tol: int = 0) -> None:
    assert abs(int(a) - int(b)) <= tol, f"{a} != {b}"

def run_one(em_path: str) -> Dict[str, Any]:
    em = json.load(open(em_path, "r", encoding="utf-8"))
    em2 = roundtrip_em_to_xml_to_em(em)

    inv1, inv2 = invariants(em), invariants(em2)

    # Counts
    assert inv1["zone_names"] == inv2["zone_names"], "Zone names mismatch"
    for k in ("walls","roofs","floors"):
        assert_near(inv1["surf_counts"].get(k,0), inv2["surf_counts"].get(k,0))
    for k in ("windows","doors","skylights"):
        assert_near(inv1["opening_counts"].get(k,0), inv2["opening_counts"].get(k,0))
    assert inv1["zone_multipliers"] == inv2["zone_multipliers"], "Zone multipliers mismatch"

    # Catalog/system counts
    for k in ("hvac_count","du_type_count","win_type_count","const_type_count","pv_count","dhw_count"):
        assert_near(inv1[k], inv2[k])

    # Location round-trips (best-effort)
    for key in ("building_azimuth_deg","city","state","climate_zone"):
        if key in inv1["location"]:
            assert str(inv1["location"][key]) == str(inv2["location"].get(key)), f"Location field {key} mismatch"

    return {"before": inv1, "after": inv2}

if __name__ == "__main__":
    import sys, json as _json
    if len(sys.argv) < 2:
        print("Usage: python test_roundtrip.py <path/to/sample.em.json>")
        raise SystemExit(2)
    out = run_one(sys.argv[1])
    print("Round-trip invariants passed.")
    print(_json.dumps(out, indent=2))
