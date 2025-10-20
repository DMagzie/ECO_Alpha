# Lossless systems parsing with signature-flexible entrypoints.
# Authoritative container: em['energy'].*  (later mirrored to em['hvac'].*)

from __future__ import annotations
from typing import Any, Dict, Iterable, List, Optional, Tuple
from xml.etree.ElementTree import Element
import re

# ----------------------------- Diagnostics fallback ---------------------------
try:
    from mapping_cleanup import diag as _mkdiag, mirror_energy_to_legacy_hvac
except Exception:
    def _mkdiag(level: str, code: str, message: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        d = {"level": level, "code": code, "message": message}
        if context: d["context"] = context
        return d
    def mirror_energy_to_legacy_hvac(em: Dict[str, Any]) -> None:
        hv = em.setdefault("hvac", {})
        en = em.setdefault("energy", {})
        hv["systems"] = list(en.get("hvac_systems", []))
        hv["iaq_fans"] = list(en.get("iaq_fans", []))
        hv["dhw_systems"] = list(en.get("dhw_systems", []))

# ----------------------------- Common helpers --------------------------------
def _resolve_em_root(*args, **kwargs) -> Tuple[Optional[Dict[str, Any]], Optional[Element], Optional[List[dict]]]:
    em = kwargs.get("em") or kwargs.get("em_v6") or kwargs.get("emjson")
    root = kwargs.get("root") or kwargs.get("xml") or kwargs.get("xml_root")
    diags = kwargs.get("diags")
    for a in args:
        if isinstance(a, dict) and em is None:
            em = a
        elif isinstance(a, Element) and root is None:
            root = a
        elif isinstance(a, list) and diags is None and (not a or isinstance(a[0], dict)):
            diags = a
    if len(args) >= 2:
        if isinstance(args[0], Element) and isinstance(args[1], dict):
            root = root or args[0]; em = em or args[1]
        if isinstance(args[0], dict) and isinstance(args[1], Element):
            em = em or args[0]; root = root or args[1]
    return em, root, diags

def _ensure_energy(em: Dict[str, Any]) -> Dict[str, Any]:
    if "energy" not in em or not isinstance(em["energy"], dict):
        em["energy"] = {}
    return em["energy"]

def _get_du_types(em: Dict[str, Any]) -> List[Dict[str, Any]]:
    return (em.get("catalogs", {}) or {}).get("du_types", []) or []

def _tag_local(tag: str) -> str:
    return tag.split("}", 1)[-1] if "}" in tag else tag

def _text(el: Optional[Element]) -> str:
    try:
        return (el.text or "").strip()
    except Exception:
        return ""

def _child_text(node: Optional[Element], tag: str) -> str:
    if node is None:
        return ""
    for ch in list(node):
        if _tag_local(ch.tag) == tag:
            return _text(ch)
    return ""

def _len_safe(x) -> int:
    try:
        return len(x) if x is not None else 0
    except Exception:
        return 0

def _unique(seq: Iterable[Any]) -> List[Any]:
    s, out = set(), []
    for x in seq:
        if x not in s:
            s.add(x)
            out.append(x)
    return out

# =============================== HVAC =========================================
def parse_hvac_systems(*args, **kwargs) -> List[Dict[str, Any]]:
    """Flexible entrypoint. Updates em['energy']['hvac_systems'] and returns diagnostics."""
    em, root, caller_diags = _resolve_em_root(*args, **kwargs)
    diags: List[Dict[str, Any]] = []
    if not isinstance(em, dict):
        return diags
    energy = _ensure_energy(em)

    # DU-driven grouping
    hvac_by_key: Dict[Tuple[Any, Any, Any, Any], Dict[str, Any]] = {}
    for du in _get_du_types(em):
        du_name = du.get("name")
        attrs = (du.get("attributes") or {})
        sys_type = attrs.get("HVACSysType")
        hp_ref  = attrs.get("HVACHtPumpRef")
        fan_ref = attrs.get("HVACFanRef")
        dist_ref= attrs.get("HVACDistRef")
        key = (sys_type, hp_ref, fan_ref, dist_ref)
        rec = hvac_by_key.setdefault(key, {
            "name": f"{sys_type or 'HVAC'} — {(hp_ref or fan_ref or dist_ref) or 'Unspecified'}",
            "type": sys_type or "HVAC",
            "raw_fields": {k: v for k, v in attrs.items() if k in ("HVACSysType","HVACHtPumpRef","HVACFanRef","HVACDistRef")},
            "du_types_served": []
        })
        if du_name:
            rec["du_types_served"].append(du_name)

    systems = list(hvac_by_key.values())

    # XML fallback: AirSys blocks
    if not systems and isinstance(root, Element):
        by_name: Dict[str, Dict[str, Any]] = {}
        for asys in root.findall(".//AirSys"):
            nm = _child_text(asys, "Name") or _child_text(asys, "AirSys_NameRoot") or "AirSys"
            nm = nm.strip() or "AirSys"
            rec = by_name.setdefault(nm, {"name": nm, "type": "AirSys", "raw_fields": {}, "du_types_served": []})
            for ch in list(asys):
                t = _tag_local(ch.tag)
                v = _text(ch)
                if v:
                    rec["raw_fields"][t] = v
        systems = list(by_name.values())

    energy["hvac_systems"] = systems
    mirror_energy_to_legacy_hvac(em)

    diags.append(_mkdiag("info", "I-HVAC-SUMMARY", f"hvac_systems={_len_safe(systems)} (DU+AirSys)"))
    if caller_diags is not None and isinstance(caller_diags, list):
        caller_diags.extend(diags)
    return diags

# ================================ IAQ =========================================
def parse_iaq_catalog(*args, **kwargs) -> List[Dict[str, Any]]:
    """Flexible entrypoint. Updates em['energy']['iaq_fans'] and returns diagnostics."""
    em, root, caller_diags = _resolve_em_root(*args, **kwargs)
    diags: List[Dict[str, Any]] = []
    if not isinstance(em, dict):
        return diags
    energy = _ensure_energy(em)

    fans_by_ref: Dict[str, Dict[str, Any]] = {}

    # DU-driven
    for du in _get_du_types(em):
        du_name = du.get("name")
        attrs = (du.get("attributes") or {})
        ref = attrs.get("IAQFanRef")
        if not ref:
            continue
        rec = fans_by_ref.setdefault(ref, {
            "name": ref,
            "type": attrs.get("IAQFanType") or attrs.get("IAQOption") or "IAQFan",
            "raw_fields": {k: v for k, v in attrs.items() if k.upper().startswith("IAQ")},
            "du_types_served": []
        })
        if du_name:
            rec["du_types_served"].append(du_name)

    # XML fallback
    if not fans_by_ref and isinstance(root, Element):
        by_ref: Dict[str, Dict[str, Any]] = {}
        for n in root.findall(".//IAQFanRef/.."):
            ref = _child_text(n, "IAQFanRef")
            if not ref:
                continue
            rec = by_ref.setdefault(ref, {"name": ref, "type": "IAQFan", "raw_fields": {}, "du_types_served": []})
            for ch in list(n):
                t = _tag_local(ch.tag)
                v = _text(ch)
                if v and t.upper().startswith("IAQ"):
                    rec["raw_fields"][t] = v
        if not by_ref:
            for n in (list(root.iter()) if isinstance(root, Element) else []):
                tname = _tag_local(n.tag)
                if "IAQ" in tname.upper():
                    nm = _child_text(n, "Name") or _child_text(n, "IAQFanRef") or tname
                    nm = nm.strip() or "IAQFan"
                    rec = by_ref.setdefault(nm, {"name": nm, "type": "IAQFan", "raw_fields": {}, "du_types_served": []})
                    for ch in list(n):
                        t = _tag_local(ch.tag)
                        v = _text(ch)
                        if v:
                            rec["raw_fields"][t] = v
        fans_by_ref = by_ref or fans_by_ref

    fans = list(fans_by_ref.values())
    energy["iaq_fans"] = fans
    mirror_energy_to_legacy_hvac(em)

    diags.append(_mkdiag("info", "I-IAQ-SUMMARY", f"iaq_fans={_len_safe(fans)} (DU+XML)"))
    if caller_diags is not None and isinstance(caller_diags, list):
        caller_diags.extend(diags)
    return diags

# ================================ DHW =========================================
_NUM_RX = re.compile(r"[-+]?\d+(?:\.\d+)?")
def _num_from_str(s: Optional[str]) -> Optional[float]:
    if not s:
        return None
    m = _NUM_RX.search(str(s).replace(",", ""))
    if not m:
        return None
    try:
        return float(m.group(0))
    except Exception:
        return None

_DHW_RECIRC_MAP = {
    "Central with Recirculation": "central_recirc",
    "Central without Recirculation": "central_no_recirc",
    "Central w/Recirc": "central_recirc",
    "None": "none",
}
_DHW_TYPE_MAP = {
    "HPWH": "central_hpwh",
    "Heat Pump": "central_hpwh",
    "Gas Boiler": "central_boiler",
    "Gas": "central_gas",
    "Gas Storage": "central_storage",
    "Electric": "central_electric",
    "Electric Resistance": "central_er",
}
_TANK_LOC_MAP = {
    "Inside": "inside",
    "Outside": "outside",
    "Garage": "garage",
    "Mechanical Room": "mechanical_room",
}
_SRC_AIR_LOC_MAP = {
    "Inside": "inside",
    "Outside": "outside",
    "Garage": "garage",
    "Return Air": "return_air",
}
_LOOP_TANK_MAP = {
    "None (return to Primary)": "none",
    "Primary/Secondary": "primary_secondary",
    "Decoupled/Buffer": "decoupled_buffer",
    "Series (Swing)": "series_swing",
    "Series": "series",
    "Parallel": "parallel",
}

def _gather_text_children(node: Element) -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    for ch in list(node):
        t = _tag_local(ch.tag)
        v = _text(ch)
        if v != "":
            out[t] = v
    return out

def _normalize_fuel(s: Optional[str]) -> Optional[str]:
    if not s: return None
    t = s.lower()
    if "elec" in t: return "electric"
    if "gas" in t or "natural" in t or "ng" in t: return "gas"
    return s

def _is_hpwh_from_heater(hraw: Dict[str, Any]) -> bool:
    txt = " ".join([str(hraw.get("HeaterType","")), str(hraw.get("Model","")), str(hraw.get("Notes",""))]).lower()
    if "hpwh" in txt or "heat pump" in txt:
        return True
    if _normalize_fuel(hraw.get("HeaterElementType") or hraw.get("FuelSrc")) == "electric" and ("heat pump" in txt or "comp" in txt):
        return True
    return False

def parse_dhw_catalog(*args, **kwargs) -> List[Dict[str, Any]]:
    """Flexible entrypoint. Updates em['energy']['dhw_systems'] and returns diagnostics."""
    em, root, caller_diags = _resolve_em_root(*args, **kwargs)
    diags: List[Dict[str, Any]] = []
    if not isinstance(em, dict):
        return diags
    energy = _ensure_energy(em)

    systems_by_name: Dict[str, Dict[str, Any]] = {}
    heaters_by_name: Dict[str, Dict[str, Any]] = {}

    if isinstance(root, Element):
        sys_tags = {"ResDHWsys","ResDHWSys","ComDHWsys","ComDHWSys","DHWsys","DHWSys"}
        for n in root.iter():
            if _tag_local(n.tag) in sys_tags:
                nm = (_child_text(n, "Name") or "DHWSystem").strip()
                rec = systems_by_name.setdefault(nm, {
                    "name": nm, "type": "DHWSystem",
                    "raw_fields": {}, "du_types_served": [], "water_heaters": []
                })
                rec["raw_fields"].update(_gather_text_children(n))

        ht_tags = {"ResWrHtTr","ResWtrHtr","ComWrHtTr","ComWtrHtr","WrHtTr","WtrHtr","WaterHeater"}
        for h in root.iter():
            if _tag_local(h.tag) in ht_tags:
                hname = (_child_text(h, "Name") or "WaterHeater").strip()
                raw = _gather_text_children(h)
                hrec = {
                    "name": hname,
                    "fuel": raw.get("HeaterElementType") or raw.get("FuelSrc"),
                    "tank_type": raw.get("TankType"),
                    "input_rating": _num_from_str(raw.get("InputRating")),
                    "energy_factor": _num_from_str(raw.get("EnergyFactor")),
                    "tank_volume_gal": _num_from_str(raw.get("TankVolume")) or _num_from_str(raw.get("TankVol")),
                    "recovery_efficiency": _num_from_str(raw.get("RecovEff")),
                    "raw": raw,
                }
                heaters_by_name[hname] = hrec

        # Attach heaters by <DHWHeater> refs
        for nm, rec in systems_by_name.items():
            rf = rec.get("raw_fields") or {}
            refs: List[str] = []
            for k, v in rf.items():
                if k.lower() == "dhwheater" and v:
                    refs.append(str(v).strip())
            for n in root.iter():
                if _tag_local(n.tag) in sys_tags and (_child_text(n, "Name") or "").strip() == nm:
                    for ch in list(n):
                        if _tag_local(ch.tag).lower() == "dhwheater":
                            val = _text(ch)
                            if val:
                                refs.append(val.strip())
                    break
            for r in refs:
                hobj = heaters_by_name.get(r)
                if hobj:
                    rec["water_heaters"].append(hobj)
            if not rec["water_heaters"] and len(heaters_by_name) == 1 and len(systems_by_name) == 1:
                rec["water_heaters"].append(next(iter(heaters_by_name.values())))

    for du in _get_du_types(em):
        du_name = du.get("name")
        ref = (du.get("attributes") or {}).get("DHWSysRef")
        if ref and ref in systems_by_name and du_name:
            systems_by_name[ref]["du_types_served"].append(du_name)

    dhw_list: List[Dict[str, Any]] = []
    for nm, rec in systems_by_name.items():
        raw = rec.get("raw_fields") or {}
        central_type_raw = raw.get("CentralDHWType") or raw.get("CentralDHWSType") or raw.get("SystemType")
        recirc_raw = raw.get("CentralRecircType")
        system_type = _DHW_TYPE_MAP.get(central_type_raw, central_type_raw) if central_type_raw else None
        recirc_type = _DHW_RECIRC_MAP.get(recirc_raw, recirc_raw) if recirc_raw else None

        if not system_type:
            hpwh_inference = any(k in raw for k in ("CHPWHCompType","CHPWHNumComp","CHPWHTankCount","CHPWHTankLoc","CHPWHSrcAirLoc","CHPWHLoopTankConfig","CHPWHSysDescrip"))
            if hpwh_inference:
                system_type = "central_hpwh"

        hpwh: Dict[str, Any] = {}
        if raw.get("CHPWHCompType"): hpwh["compressor_type"] = raw.get("CHPWHCompType")
        if raw.get("CHPWHNumComp"):  hpwh["num_compressors"] = _num_from_str(raw.get("CHPWHNumComp"))
        if raw.get("CHPWHSrcAirLoc"): hpwh["source_air_location"] = _SRC_AIR_LOC_MAP.get(raw.get("CHPWHSrcAirLoc"), raw.get("CHPWHSrcAirLoc"))
        if raw.get("CHPWHSysDescrip"): hpwh["description"] = raw.get("CHPWHSysDescrip")
        if hpwh: rec["hpwh"] = hpwh

        storage: Dict[str, Any] = {}
        if raw.get("CHPWHTankCount"): storage["tank_count"] = _num_from_str(raw.get("CHPWHTankCount"))
        if raw.get("CHPWHTankLoc"):   storage["tank_location"] = _TANK_LOC_MAP.get(raw.get("CHPWHTankLoc"), raw.get("CHPWHTankLoc"))
        if storage: rec["storage"] = storage

        hydraulics: Dict[str, Any] = {}
        if raw.get("CHPWHLoopTankConfig"): hydraulics["loop_tank_config"] = _LOOP_TANK_MAP.get(raw.get("CHPWHLoopTankConfig"), raw.get("CHPWHLoopTankConfig"))
        if hydraulics: rec["hydraulics"] = hydraulics

        if system_type: rec["system_type"] = system_type
        if recirc_type: rec["recirc_type"] = recirc_type

        for h in rec.get("water_heaters", []):
            f = h.get("fuel")
            h["fuel_norm"] = _normalize_fuel(f) if f else None
            if _is_hpwh_from_heater(h.get("raw") or {}):
                rec.setdefault("hpwh", {}).setdefault("heuristics", True)

        dhw_list.append(rec)
        diags.append(_mkdiag("info", "I-DHW-MAP-SUMMARY",
                             f"{rec.get('name')}: system_type={rec.get('system_type')} recirc={rec.get('recirc_type')} heaters={_len_safe(rec.get('water_heaters'))}"))

    if dhw_list:
        types = {}
        for x in dhw_list:
            t = x.get("system_type") or "unknown"
            types[t] = types.get(t, 0) + 1
        diags.append(_mkdiag("info", "I-DHW-MAP", f"dhw_systems mapped: {types}"))

    energy["dhw_systems"] = dhw_list
    mirror_energy_to_legacy_hvac(em)

    if caller_diags is not None and isinstance(caller_diags, list):
        caller_diags.extend(diags)
    return diags

# ===================== Simplified catalogs for UI =============================
def build_simplified_catalogs_from_full_systems(*args, **kwargs) -> List[dict]:
    em, _, _ = _resolve_em_root(*args, **kwargs)
    if not isinstance(em, dict):
        return []
    catalogs = em.setdefault("catalogs", {})
    energy = _ensure_energy(em)

    hvac_types = _unique([(s.get("type") or "HVAC") for s in energy.get("hvac_systems", [])])
    iaq_types  = _unique([(s.get("type") or "IAQFan") for s in energy.get("iaq_fans", [])])
    dhw_types  = _unique([(s.get("type") or "DHWSystem") for s in energy.get("dhw_systems", [])])

    catalogs["hvac_types"] = [{"name": t} for t in hvac_types]
    catalogs["iaq_fan_types"] = [{"name": t} for t in iaq_types]
    catalogs["dhw_types"] = [{"name": t} for t in dhw_types]
    return []

# ===================== Components harvester (for future writer) ===============
def parse_hvac_components(root: Element, em: Dict[str, Any], diags: Optional[List[Dict[str, Any]]] = None) -> None:
    if diags is None:
        diags = em.setdefault("diagnostics", [])
    energy = _ensure_energy(em)
    comps: List[Dict[str, Any]] = energy.setdefault("hvac_components", [])

    component_tags = [
        "Fan", "FanSupp", "FanRet", "FanExh",
        "CoilClg", "CoilHtg", "DXCoil", "Furnace",
        "Boiler", "Chiller", "HeatPump", "ElecHeater",
        "VAVTerm", "ReheatCoil", "ERV", "HRV"
    ]
    system_tags = ["ResHVACSys", "ComHVACSys", "AirSys", "PlantSys", "ResHtPumpSys", "ResFurnaceSys"]

    def _safe_txt(node: Optional[Element], tag: str) -> Optional[str]:
        if node is None: return None
        ch = node.find(tag)
        return (ch.text.strip() if (ch is not None and ch.text is not None) else None)

    def _make_id(prefix: str, *parts: str) -> str:
        norm = "-".join([str(p).strip().replace(" ", "_") for p in parts if p is not None and str(p).strip() != ""])
        return f"{prefix}:{norm}" if norm else prefix

    added = 0
    for tag in component_tags:
        for node in root.findall(f".//{tag}"):
            name = _safe_txt(node, "Name") or node.get("name") or tag
            cid = _make_id("hvaccomp", tag, name)
            system_ref = None
            # containment search
            for st in system_tags:
                for sysnode in root.findall(f".//{st}"):
                    for candidate in sysnode.findall(f".//{tag}"):
                        if candidate is node:
                            system_ref = _make_id("system", st, _safe_txt(sysnode, "Name") or st)
                            break
                    if system_ref:
                        break
                if system_ref:
                    break
            raw = {}
            for c in list(node):
                if c.tag and c.text:
                    raw[c.tag] = c.text.strip()
                elif c.tag and len(list(c)) > 0:
                    raw[c.tag] = "has_children"
            entry: Dict[str, Any] = {"id": cid, "name": name, "type": tag, "raw": raw}
            if system_ref:
                entry["system_ref"] = system_ref
            comps.append(entry); added += 1

    diags.append(_mkdiag("info", "I-HVAC-COMPONENTS", f"Harvested HVAC components: {added}", {"components_added": added}))

# Back-compat aliases
parse_hvac = parse_hvac_systems
parse_systems = parse_hvac_systems
parse_iaq = parse_iaq_catalog
parse_dhw = parse_dhw_catalog
build_simplified = build_simplified_catalogs_from_full_systems
build_simplified_catalogs = build_simplified_catalogs_from_full_systems
