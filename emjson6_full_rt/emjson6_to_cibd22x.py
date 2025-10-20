from __future__ import annotations
from typing import Dict, Any, List
from xml.etree import ElementTree as ET

def _elt(tag: str, text: str | None = None, **attrs) -> ET.Element:
    e = ET.Element(tag, {k:str(v) for k,v in attrs.items() if v is not None})
    if text is not None:
        e.text = str(text)
    return e

def _add(parent: ET.Element, tag: str, text: str | None = None, **attrs) -> ET.Element:
    e = _elt(tag, text, **attrs); parent.append(e); return e

def emjson6_to_cibd22x(em: Dict[str, Any]) -> ET.Element:
    root = _elt("Project")
    # ProjectInfo / Location
    info = _add(root, "ProjectInfo")
    loc = em.get("project", {}).get("location", {}) or {}
    if "building_azimuth_deg" in loc: _add(info, "BldgAz", str(loc["building_azimuth_deg"]))
    site = _add(info, "Site")
    if loc.get("city"): _add(site, "City", loc["city"])
    if loc.get("state"): _add(site, "State", loc["state"])
    if loc.get("climate_zone"): _add(site, "ClimateZone", loc["climate_zone"])

    # Catalogs
    cats = _add(root, "Catalogs")
    for du in em.get("du_types", []) or []:
        x = _add(cats, "DUType", id=du.get("id"))
        _add(x, "Name", du.get("name"))
        if du.get("floor_area") is not None: _add(x, "FloorArea", du["floor_area"])
        if du.get("occupants") is not None: _add(x, "Occupants", du["occupants"])
    for wt in em.get("window_types", []) or []:
        x = _add(cats, "WindowType", id=wt.get("id"))
        _add(x, "Name", wt.get("name"))
        if wt.get("u_factor_btu_ft2_f") is not None: _add(x, "UFactor", wt["u_factor_btu_ft2_f"])
        if wt.get("shgc") is not None: _add(x, "SHGC", wt["shgc"])
        if wt.get("vt") is not None: _add(x, "VT", wt["vt"])
    for ct in em.get("construction_types", []) or []:
        x = _add(cats, "ConstructionType", id=ct.get("id"))
        _add(x, "Name", ct.get("name"))
        if ct.get("apply_to"): _add(x, "ApplyTo", ct["apply_to"])
        if ct.get("u_value_btu_ft2_f") is not None: _add(x, "UValue", ct["u_value_btu_ft2_f"])

    # Building
    bldg = _add(root, "Building")

    # PV
    if em.get("pv_systems"):
        pvroot = _add(bldg, "PV")
        for p in em["pv_systems"]:
            x = _add(pvroot, "Array", id=p.get("id"))
            _add(x, "Name", p.get("name"))
            if p.get("capacity_kw") is not None: _add(x, "CapacityKW", p["capacity_kw"])
            if p.get("tilt_deg") is not None: _add(x, "Tilt", p["tilt_deg"])
            if p.get("azimuth_deg") is not None: _add(x, "Azimuth", p["azimuth_deg"])

    # Zones + Surfaces + Openings
    zones = em.get("geometry", {}).get("zones", []) or []
    surfs = em.get("geometry", {}).get("surfaces", {}) or {}
    opens = em.get("geometry", {}).get("openings", {}) or {}

    for z in zones:
        is_res = bool(z.get("du_count_in_zone",1) != 1 or z.get("du_type_ref"))
        zn = _add(bldg, "ResZn" if is_res else "ComZn", id=z.get("id"))
        _add(zn, "Name", z.get("name") or z.get("id"))
        if z.get("floor_area") is not None: _add(zn, "FloorArea", z["floor_area"])
        if is_res:
            du = _add(zn, "DwellUnit")
            _add(du, "Count", str(int(z.get("du_count_in_zone") or 1)))
        _add(zn, "ZnMult", str(int(z.get("zone_multiplier") or 1)))

        s_node = _add(zn, "Surfaces")
        for bucket, arr in (("walls", surfs.get("walls", [])),
                            ("roofs", surfs.get("roofs", [])),
                            ("floors", surfs.get("floors", []))):
            tag = {"walls":"ExtWall","roofs":"Roof","floors":"ExtFlr"}[bucket]
            for s in arr or []:
                if (s.get("parent_zone_ref") or "") != (z.get("name") or z.get("id") or ""):
                    continue
                se = _add(s_node, tag)
                _add(se, "Name", s.get("name") or s.get("id"))
                if s.get("area_ft2") is not None: _add(se, "Area", s["area_ft2"])

                # Openings under surface
                for win in (opens.get("windows", []) or []):
                    if win.get("parent_surface_ref") == s.get("id"):
                        we = _add(se, "Window"); _add(we, "Name", win.get("name") or win.get("id"))
                        if win.get("area_m2") is not None: _add(we, "Area", win["area_m2"])
                        if win.get("height_m") is not None: _add(we, "Height", win["height_m"])
                        if win.get("width_m") is not None: _add(we, "Width", win["width_m"])
                for dr in (opens.get("doors", []) or []):
                    if dr.get("parent_surface_ref") == s.get("id"):
                        de = _add(se, "Door"); _add(de, "Name", dr.get("name") or dr.get("id"))
                for sk in (opens.get("skylights", []) or []):
                    if sk.get("parent_surface_ref") == s.get("id"):
                        ke = _add(se, "Skylight"); _add(ke, "Name", sk.get("name") or sk.get("id"))

    # HVAC
    hvac_list = em.get("hvac_systems", []) or []
    if hvac_list:
        hvac_root = _add(bldg, "HVAC")
        for h in hvac_list:
            sys = _add(hvac_root, "System", id=h.get("id"))
            _add(sys, "Name", h.get("name"))
            if h.get("type"): _add(sys, "Type", h["type"])
            if h.get("fuel"): _add(sys, "Fuel", h["fuel"])
            if h.get("multiplier", {}).get("effective"):
                _add(sys, "Multiplier", h["multiplier"]["effective"])
            zr = _add(sys, "Zones")
            for zref in (h.get("zone_refs") or []):
                _add(zr, "ZoneRef", zref)

    # DHW
    for d in em.get("dhw_systems", []) or []:
        sys = _add(bldg, "ResidentialDHWSystem", id=d.get("id"))
        _add(sys, "Name", d.get("name") or d.get("id"))
        if d.get("system_type_norm"): _add(sys, "SystemType", d["system_type_norm"])
        if d.get("recirc_type"): _add(sys, "RecircType", d["recirc_type"])
        if d.get("requirements"):
            for req in d["requirements"]:
                _add(sys, "Note", req)

    return root

def write_xml(em: Dict[str, Any], out_path: str) -> None:
    root = emjson6_to_cibd22x(em)
    from xml.dom import minidom
    xml_str = ET.tostring(root, encoding="utf-8")
    pretty = minidom.parseString(xml_str).toprettyxml(indent="  ")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(pretty)
