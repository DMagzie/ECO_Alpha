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


def _diag(em: Dict[str, Any], level: str, code: str, message: str, context: Dict[str, Any] | None = None):
    em.setdefault("diagnostics", []).append({
        "level": level, "code": code, "message": message, "context": context or {}
    })


def parse_hvac(root: ET.Element, em: Dict[str, Any], id_registry: Any) -> List[Dict[str, Any]]:
    """
    Parse HVAC systems - STUB for now, will be expanded later.
    TODO: Full implementation with zone systems, air systems, equipment
    """
    out: List[Dict[str, Any]] = []

    # Basic system parsing
    for sys in root.iter():
        tag = _lt(sys.tag)
        if tag not in ("ResHVACSys", "ComHVACSys", "HVACSystem", "System"):
            continue

        sid = sys.get("id") or None
        name = _child_text_local(sys, "Name") or sys.get("Name") or sid or "HVAC"

        # Generate stable ID
        sys_id = id_registry.generate_id("SYS", name, context="", source_format="CIBD22X")

        typ = _child_text_local(sys, "Type") or sys.get("Type")
        fuel = _child_text_local(sys, "Fuel") or sys.get("Fuel")

        # Parse zone references
        zones = []
        for zr in sys.iter():
            if _lt(zr.tag) in ("ZoneRef", "ZoneServed", "ServedZone"):
                zname = (zr.text or "").strip()
                if zname:
                    zones.append(zname)

        out.append({
            "id": sys_id,
            "name": name,
            "type": typ,
            "fuel_heating": fuel,
            "fuel_cooling": fuel,
            "served_zones": zones,  # Will be resolved to zone IDs later
            "components": [],
            "controls": {},
            "annotation": {
                "xml_tag": tag,
                "source_id": sid
            }
        })

    em.setdefault("systems", {})["hvac"] = out

    if out:
        _diag(em, "info", "I-HVAC-PARSED", f"Parsed {len(out)} HVAC systems (basic stub)")
    else:
        _diag(em, "info", "I-HVAC-NONE", "No HVAC systems found")

    return out