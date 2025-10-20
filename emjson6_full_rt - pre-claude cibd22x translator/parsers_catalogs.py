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

def parse_location(root: ET.Element, em: Dict[str, Any]) -> Dict[str, Any]:
    info = {}
    proj = (root.find(".//ProjectInfo") or root.find(".//Info") or root.find(".//Project"))
    if proj is not None:
        bldg_az = (_child_text_local(proj, "BldgAz") or _child_text_local(proj, "BuildingAzimuth")
                   or proj.get("BldgAz") or proj.get("BuildingAzimuth"))
        try:
            info["building_azimuth_deg"] = float(bldg_az) if bldg_az else None
        except Exception:
            pass
        site = (proj.find(".//Site") or proj.find(".//Location"))
        if site is not None:
            city = _child_text_local(site, "City") or site.get("City")
            state = _child_text_local(site, "State") or site.get("State")
            climate = _child_text_local(site, "ClimateZone") or site.get("ClimateZone")
            if city: info["city"] = city
            if state: info["state"] = state
            if climate: info["climate_zone"] = climate
    em.setdefault("project", {}).setdefault("location", {}).update({k:v for k,v in info.items() if v is not None})
    return em["project"]["location"]

def parse_du_types(root: ET.Element, em: Dict[str, Any]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for du in root.findall(".//DUType") + root.findall(".//DwellUnitType"):
        name = _child_text_local(du, "Name") or du.get("Name") or du.get("id") or "DU"
        item = {"id": du.get("id") or f"du:{name}", "name": name}
        fa = _child_text_local(du, "FloorArea") or du.get("FloorArea")
        occ = _child_text_local(du, "Occupants") or du.get("Occupants")
        try:
            if fa: item["floor_area"] = float(fa)
        except Exception:
            pass
        try:
            if occ: item["occupants"] = int(float(occ))
        except Exception:
            pass
        out.append(item)
    em["du_types"] = out
    return out

def parse_window_types(root: ET.Element, em: Dict[str, Any]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for wt in root.findall(".//WindowType"):
        name = _child_text_local(wt, "Name") or wt.get("Name") or wt.get("id") or "WindowType"
        item = {"id": wt.get("id") or f"win:{name}", "name": name}
        uf = _child_text_local(wt, "UFactor") or wt.get("UFactor")
        shgc = _child_text_local(wt, "SHGC") or wt.get("SHGC")
        vt = _child_text_local(wt, "VT") or wt.get("VT")
        try:
            if uf: item["u_factor_btu_ft2_f"] = float(uf)
        except Exception: pass
        try:
            if shgc: item["shgc"] = float(shgc)
        except Exception: pass
        try:
            if vt: item["vt"] = float(vt)
        except Exception: pass
        out.append(item)
    em["window_types"] = out
    return out

def parse_construction_types(root: ET.Element, em: Dict[str, Any]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for ct in root.findall(".//ConstructionType"):
        name = _child_text_local(ct, "Name") or ct.get("Name") or ct.get("id") or "Construction"
        apply_to = _child_text_local(ct, "ApplyTo") or ct.get("ApplyTo")
        uval = _child_text_local(ct, "UValue") or ct.get("UValue")
        item = {"id": ct.get("id") or f"const:{name}", "name": name}
        if apply_to: item["apply_to"] = apply_to.lower()
        try:
            if uval: item["u_value_btu_ft2_f"] = float(uval)
        except Exception: pass
        out.append(item)
    em["construction_types"] = out
    return out

def parse_pv(root: ET.Element, em: Dict[str, Any]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for pv in root.findall(".//PV") + root.findall(".//Array") + root.findall(".//PVArray"):
        name = _child_text_local(pv, "Name") or pv.get("Name") or pv.get("id") or "PV"
        cap = _child_text_local(pv, "CapacityKW") or pv.get("CapacityKW")
        tilt = _child_text_local(pv, "Tilt") or pv.get("Tilt")
        az = _child_text_local(pv, "Azimuth") or pv.get("Azimuth")
        item = {"id": pv.get("id") or f"pv:{name}", "name": name}
        try:
            if cap: item["capacity_kw"] = float(cap)
        except Exception: pass
        try:
            if tilt: item["tilt_deg"] = float(tilt)
        except Exception: pass
        try:
            if az: item["azimuth_deg"] = float(az)
        except Exception: pass
        out.append(item)
    em["pv_systems"] = out
    return out
