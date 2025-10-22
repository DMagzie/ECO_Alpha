# FILE 7: em-tools/emtools/exporters/cibd22x_exporter.py
# ============================================================================
"""
EMJSON v6 to CIBD22X XML Exporter

Converts EMJSON v6 format back to CIBD22X XML for Title 24 compliance modeling.
"""

from __future__ import annotations
from typing import Dict, Any, List
from xml.etree import ElementTree as ET


def _elt(tag: str, text: str | None = None, **attrs) -> ET.Element:
    """Create XML element with optional text and attributes."""
    e = ET.Element(tag, {k: str(v) for k, v in attrs.items() if v is not None})
    if text is not None:
        e.text = str(text)
    return e


def _add(parent: ET.Element, tag: str, text: str | None = None, **attrs) -> ET.Element:
    """Create and append child element."""
    e = _elt(tag, text, **attrs)
    parent.append(e)
    return e


def emjson6_to_cibd22x(em: Dict[str, Any]) -> ET.Element:
    """
    Convert EMJSON v6 to CIBD22X XML structure.

    Args:
        em: EMJSON v6 dictionary

    Returns:
        XML Element tree root

    Example:
        >>> root = emjson6_to_cibd22x(emjson)
        >>> ET.dump(root)
    """
    root = _elt("Project")

    # ProjectInfo / Location
    info = _add(root, "ProjectInfo")
    loc = em.get("project", {}).get("location", {}) or {}

    if "building_azimuth_deg" in loc:
        _add(info, "BldgAz", str(loc["building_azimuth_deg"]))

    site = _add(info, "Site")
    if loc.get("city"):
        _add(site, "City", loc["city"])
    if loc.get("state"):
        _add(site, "State", loc["state"])
    if loc.get("climate_zone"):
        _add(site, "ClimateZone", loc["climate_zone"])

    # Catalogs
    cats = _add(root, "Catalogs")
    catalogs = em.get("catalogs", {})

    for du in catalogs.get("du_types", []) or []:
        x = _add(cats, "DUType", id=du.get("id"))
        _add(x, "Name", du.get("name"))
        if du.get("floor_area_m2") is not None:
            # Convert m² back to ft²
            _add(x, "FloorArea", str(du["floor_area_m2"] / 0.092903))
        if du.get("occupants") is not None:
            _add(x, "Occupants", str(du["occupants"]))
        if du.get("bedrooms") is not None:
            _add(x, "Bedrooms", str(du["bedrooms"]))

    for wt in catalogs.get("window_types", []) or []:
        x = _add(cats, "WindowType", id=wt.get("id"))
        _add(x, "Name", wt.get("name"))
        if wt.get("u_factor_btu_ft2_f") is not None:
            _add(x, "UFactor", str(wt["u_factor_btu_ft2_f"]))
        if wt.get("shgc") is not None:
            _add(x, "SHGC", str(wt["shgc"]))
        if wt.get("vt") is not None:
            _add(x, "VT", str(wt["vt"]))

    for ct in catalogs.get("construction_types", []) or []:
        x = _add(cats, "ConstructionType", id=ct.get("id"))
        _add(x, "Name", ct.get("name"))
        if ct.get("apply_to"):
            _add(x, "ApplyTo", ct["apply_to"])
        if ct.get("u_value_btu_ft2_f") is not None:
            _add(x, "UValue", str(ct["u_value_btu_ft2_f"]))

    # Building
    bldg = _add(root, "Building")

    # PV
    systems = em.get("systems", {})
    pv_systems = systems.get("pv", []) or []
    if pv_systems:
        pvroot = _add(bldg, "PV")
        for p in pv_systems:
            x = _add(pvroot, "Array", id=p.get("id"))
            _add(x, "Name", p.get("name"))
            if p.get("capacity_kw") is not None:
                _add(x, "CapacityKW", str(p["capacity_kw"]))
            if p.get("tilt_deg") is not None:
                _add(x, "Tilt", str(p["tilt_deg"]))
            if p.get("azimuth_deg") is not None:
                _add(x, "Azimuth", str(p["azimuth_deg"]))

    # Zones + Surfaces + Openings
    zones = em.get("geometry", {}).get("zones", []) or []
    surfs = em.get("geometry", {}).get("surfaces", {}) or {}
    opens = em.get("geometry", {}).get("openings", {}) or {}

    for z in zones:
        # Determine if residential based on du_ref or building_type
        is_res = bool(z.get("du_ref") or z.get("building_type") == "MF")
        zn = _add(bldg, "ResZn" if is_res else "ComZn", id=z.get("id"))
        _add(zn, "Name", z.get("name") or z.get("id"))

        # Convert floor area from m² to ft²
        if z.get("floor_area_m2") is not None:
            _add(zn, "FloorArea", str(z["floor_area_m2"] / 0.092903))

        if is_res:
            # Extract du_count from multiplier metadata
            mult_meta = z.get("annotation", {}).get("multiplier_metadata", {})
            du_count = 1
            for factor in mult_meta.get("factors", []):
                if factor.get("name") == "du_count_in_zone":
                    du_count = factor.get("value", 1)
                    break
            
            du = _add(zn, "DwellUnit")
            _add(du, "Count", str(int(du_count)))

        # Use 'multiplier' field (not 'zone_multiplier')
        _add(zn, "ZnMult", str(int(z.get("multiplier", 1))))

        s_node = _add(zn, "Surfaces")

        for bucket, arr in (("walls", surfs.get("walls", [])),
                            ("roofs", surfs.get("roofs", [])),
                            ("floors", surfs.get("floors", []))):
            tag = {"walls": "ExtWall", "roofs": "Roof", "floors": "ExtFlr"}[bucket]

            for s in arr or []:
                # Match by zone_id (not parent_zone_ref)
                if s.get("zone_id") != z.get("id"):
                    continue

                se = _add(s_node, tag)
                # Surfaces may not have 'name', use ID from annotation if needed
                surf_name = (s.get("annotation", {}).get("source_name") or 
                            s.get("id") or "Surface")
                _add(se, "Name", surf_name)

                # Convert area from m² to ft²
                if s.get("area_m2") is not None:
                    _add(se, "Area", str(s["area_m2"] / 0.092903))

                # Openings are stored as ID references; look them up in global collections
                opening_ids = s.get("openings", [])
                
                # Build opening lookup from all opening types
                all_openings = {}
                for win in opens.get("windows", []) or []:
                    all_openings[win.get("id")] = ("window", win)
                for dr in opens.get("doors", []) or []:
                    all_openings[dr.get("id")] = ("door", dr)
                for sk in opens.get("skylights", []) or []:
                    all_openings[sk.get("id")] = ("skylight", sk)
                
                for opening_id in opening_ids:
                    if opening_id not in all_openings:
                        continue
                    
                    opening_type, opening = all_openings[opening_id]
                    
                    if opening_type == "window":
                        we = _add(se, "Window")
                        opening_name = (opening.get("annotation", {}).get("source_name") or
                                      opening.get("id") or "Window")
                        _add(we, "Name", opening_name)
                        # Convert from m² to ft²
                        if opening.get("area_m2") is not None:
                            _add(we, "Area", str(opening["area_m2"] / 0.092903))
                        # Convert from m to ft
                        if opening.get("height_m") is not None:
                            _add(we, "Height", str(opening["height_m"] / 0.3048))
                        if opening.get("width_m") is not None:
                            _add(we, "Width", str(opening["width_m"] / 0.3048))
                    
                    elif opening_type == "door":
                        de = _add(se, "Door")
                        opening_name = (opening.get("annotation", {}).get("source_name") or
                                      opening.get("id") or "Door")
                        _add(de, "Name", opening_name)
                        if opening.get("area_m2") is not None:
                            _add(de, "Area", str(opening["area_m2"] / 0.092903))
                    
                    elif opening_type == "skylight":
                        ke = _add(se, "Skylight")
                        opening_name = (opening.get("annotation", {}).get("source_name") or
                                      opening.get("id") or "Skylight")
                        _add(ke, "Name", opening_name)
                        if opening.get("area_m2") is not None:
                            _add(ke, "Area", str(opening["area_m2"] / 0.092903))

    # HVAC
    hvac_list = systems.get("hvac", []) or []
    if hvac_list:
        hvac_root = _add(bldg, "HVAC")
        for h in hvac_list:
            sys = _add(hvac_root, "System", id=h.get("id"))
            _add(sys, "Name", h.get("name"))
            if h.get("type"):
                _add(sys, "Type", h["type"])
            if h.get("fuel"):
                _add(sys, "Fuel", h["fuel"])
            if h.get("multiplier", {}).get("effective"):
                _add(sys, "Multiplier", str(h["multiplier"]["effective"]))

            zr = _add(sys, "Zones")
            for zref in (h.get("zone_refs") or []):
                _add(zr, "ZoneRef", zref)

    # DHW
    dhw_list = systems.get("dhw", []) or []
    for d in dhw_list:
        sys = _add(bldg, "ResidentialDHWSystem", id=d.get("id"))
        _add(sys, "Name", d.get("name") or d.get("id"))
        if d.get("system_type_norm"):
            _add(sys, "SystemType", d["system_type_norm"])
        if d.get("recirc_type"):
            _add(sys, "RecircType", d["recirc_type"])
        if d.get("requirements"):
            for req in d["requirements"]:
                _add(sys, "Note", req)

    return root


def write_xml(em: Dict[str, Any], out_path: str) -> None:
    """
    Write EMJSON to CIBD22X XML file with pretty formatting.

    Args:
        em: EMJSON v6 dictionary
        out_path: Output XML file path

    Example:
        >>> write_xml(emjson, "output.xml")
    """
    root = emjson6_to_cibd22x(em)

    from xml.dom import minidom

    xml_str = ET.tostring(root, encoding="utf-8")
    pretty = minidom.parseString(xml_str).toprettyxml(indent="  ")

    with open(out_path, "w", encoding="utf-8") as f:
        f.write(pretty)