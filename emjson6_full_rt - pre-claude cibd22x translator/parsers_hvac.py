from __future__ import annotations
from typing import Dict, Any, List, Optional
from xml.etree import ElementTree as ET

def _lt(tag: str) -> str:
    return tag.split('}', 1)[-1] if '}' in (tag or '') else (tag or '')

def _child_text_local(node: ET.Element | None, *names: str) -> str | None:
    if node is None:
        return None
    wanted = {n.lower() for n in names}
    for ch in list(node):
        if _lt(getattr(ch, "tag", "")).lower() in wanted:
            txt = (ch.text or "").strip()
            if txt:
                return txt
    return None

def parse_hvac(root: ET.Element, em: Dict[str, Any]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    hvac_parent = (root.find(".//HVAC") or root)
    for sys in hvac_parent.findall(".//System"):
        sid = sys.get("id") or None
        name = _child_text_local(sys, "Name") or sys.get("Name") or sid or "HVAC"
        typ = _child_text_local(sys, "Type") or sys.get("Type")
        fuel = _child_text_local(sys, "Fuel") or sys.get("Fuel")
        mult = _child_text_local(sys, "Multiplier") or sys.get("Multiplier") or "1"
        try:
            mult_i = int(float(mult))
        except Exception:
            mult_i = 1
        zones = []
        zparent = (sys.find(".//Zones") or sys)
        for zr in zparent.findall(".//ZoneRef"):
            zname = (zr.text or "").strip()
            if zname:
                zones.append(zname)
        out.append({
            "id": sid or f"hvac:{name}",
            "name": name,
            "type": typ,
            "fuel": fuel,
            "zone_refs": zones,
            "multiplier": {"effective": mult_i, "factors":[{"name":"system_multiplier","value":mult_i}], "base_quantity":1, "applies_to":["counts"]}
        })
    em["hvac_systems"] = out
    return out
