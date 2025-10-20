
## File 5: `parsers_systems.py` (STUB - will expand later)
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


def parse_dhw(root: ET.Element, em: Dict[str, Any], id_registry: Any) -> List[Dict[str, Any]]:
    """
    Parse DHW systems - STUB for now, will be expanded later.
    TODO: Full implementation with HPWH, recirculation loops, etc.
    """
    dhw_list: List[Dict[str, Any]] = []

    for sys in root.iter():
        tag = _lt(sys.tag)
        if tag not in ("ResDHWSys", "ResWtrHtr", "DHWSystem", "WaterHeater", "WtrHtr"):
            continue

        name = _child_text_local(sys, "Name") or sys.get("Name") or sys.get("id") or "DHW"

        # Generate stable ID
        dhw_id = id_registry.generate_id("DHW", name, context="", source_format="CIBD22X")

        system_type = _child_text_local(sys, "SystemType") or _child_text_local(sys, "Type") or sys.get(
            "SystemType") or sys.get("Type")

        rec: Dict[str, Any] = {
            "id": dhw_id,
            "name": name,
            "type": system_type or "unknown",
            "plant": {},
            "distribution": {},
            "served_zones": [],
            "annotation": {
                "xml_tag": tag,
                "source_id": sys.get("id")
            }
        }

        dhw_list.append(rec)

    em.setdefault("systems", {})["dhw"] = dhw_list

    if dhw_list:
        _diag(em, "info", "I-DHW-PARSED", f"Parsed {len(dhw_list)} DHW systems (basic stub)")
    else:
        _diag(em, "info", "I-DHW-NONE", "No DHW systems found")

    return dhw_list
