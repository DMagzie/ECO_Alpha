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

def parse_dhw(root: ET.Element, em: Dict[str, Any]) -> List[Dict[str, Any]]:
    dhw_list: List[Dict[str, Any]] = []
    for sys in root.iter():
        if _lt(sys.tag) in ("ResidentialDHWSystem","ResWtrHtr","DHWSystem","WtrHtr"):
            name = _child_text_local(sys,"Name") or sys.get("Name") or sys.get("id") or "DHW"
            system_type = _child_text_local(sys,"SystemType") or sys.get("SystemType")
            recirc_type = _child_text_local(sys,"RecircType") or sys.get("RecircType")
            raw = {}
            for ch in list(sys):
                if ch.tag and (ch.text is not None):
                    raw[_lt(ch.tag)] = ch.text.strip()

            rec: Dict[str, Any] = {"id": f"dhw:{name}", "name": name, "raw": raw}
            if system_type: rec["system_type"] = system_type
            if recirc_type: rec["recirc_type"] = recirc_type
            rec["system_type_norm"] = rec.get("system_type") or None
            requirements = []
            for v in raw.values():
                s = str(v)
                if "HERS" in s or "Pipe Insulation" in s or "All Lines" in s:
                    requirements.append(s)
            if requirements:
                rec["requirements"] = sorted(list(set(requirements)))

            dhw_list.append(rec)

    em["dhw_systems"] = dhw_list
    em.setdefault("diagnostics", []).append({"level":"info","code":"I-DHW-NORM","message": f"systems={len(dhw_list)}"})
    return dhw_list
