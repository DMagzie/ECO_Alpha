# cbecc/export_emjson_v5_to_cibd22x.py
"""
Export EMJSON v5 -> CBECC .cibd22x XML (UTF-8 string).

Coverage:
- Project & Location (fallback from project.address)
- Catalogs (window_types, du_types, construction_types)
- Geometry: Zones + Windows
  * Windows emitted in BOTH forms:
      (a) flat <Surface surfaceType="Window"> under <ResZn>
      (b) nested <ResExtWall><Windows><ResWindow> (import compatibility)
  * Skip only explicit auto_wall==True
- HVAC: under <HVAC><ResHVACSys>..., including <ServedZones><ZoneRef>

Robust, actionable type checks on both container shapes and field types.

Returns: str via ET.tostring(..., encoding="utf-8", xml_declaration=True).decode("utf-8")
"""

from typing import Any, Dict, List, Tuple, Iterable, Set, Optional
import xml.etree.ElementTree as ET


# ------------------------------ helpers ------------------------------

def _maybe(parent: ET.Element, tag: str, value: Any) -> None:
    if value is None:
        return
    if isinstance(value, str) and value.strip() == "":
        return
    el = ET.SubElement(parent, tag)
    el.text = str(value)

def _require_type(obj: Any, name: str, typ: type) -> None:
    if not isinstance(obj, typ):
        raise TypeError(f"em_v5['{name}'] must be {typ.__name__}, got {type(obj).__name__}")

def _require_optional_number(val: Any, path: str) -> None:
    if val is None:
        return
    if not isinstance(val, (int, float)):
        raise TypeError(f"{path} must be a number or null, got {type(val).__name__}")

def _require_optional_str(val: Any, path: str) -> None:
    if val is None:
        return
    if not isinstance(val, str):
        raise TypeError(f"{path} must be a string or null, got {type(val).__name__}")

def _get_project_and_location(em: Dict[str, Any]) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    project = em.get("project") or {}
    _require_type(project, "project", dict)
    location = project.get("location") or project.get("address") or {}
    if not isinstance(location, dict):
        location = {}
    # normalize common aliases
    if "zip" in location and "postal_code" not in location:
        location["postal_code"] = location.get("zip")
    if "state_province" in location and "state" not in location:
        location["state"] = location.get("state_province")
    return project, location

def _iter_scenarios(em: Dict[str, Any]) -> Iterable[Dict[str, Any]]:
    scenarios = em.get("scenarios") or []
    for sc in scenarios:
        if isinstance(sc, dict):
            yield sc

def _iter_zones(em: Dict[str, Any]) -> Iterable[Dict[str, Any]]:
    for sc in _iter_scenarios(em):
        zones = sc.get("zones") or []
        for zn in zones:
            if isinstance(zn, dict):
                yield zn

def _iter_window_surfaces(zone: Dict[str, Any]) -> Iterable[Dict[str, Any]]:
    surfaces = zone.get("surfaces") or []
    for s in surfaces:
        if not isinstance(s, dict):
            continue
        if s.get("auto_wall") is True:
            continue
        kind = (s.get("kind") or s.get("category") or s.get("type") or "").lower()
        if kind in ("window", "skylight"):
            yield s

def _get_catalogs(em: Dict[str, Any]) -> Dict[str, Any]:
    cats = em.get("catalogs") or {}
    if em.get("catalogs") is not None:
        _require_type(cats, "catalogs", dict)
    return cats


# ------------------------------ validation ------------------------------

def _validate_list_of_dict(name: str, value: Any) -> None:
    if not isinstance(value, list):
        raise TypeError(f"{name} must be list, got {type(value).__name__}")
    for i, item in enumerate(value):
        if not isinstance(item, dict):
            raise TypeError(f"{name}[{i}] must be dict, got {type(item).__name__}")

def _validate_surface_fields(s: Dict[str, Any], si: int, zi: int, si_path_prefix: str) -> None:
    # Only validate fields we might emit
    _require_optional_str(s.get("name"), f"{si_path_prefix}[{zi}]['surfaces'][{si}]['name']")
    _require_optional_number(s.get("area"), f"{si_path_prefix}[{zi}]['surfaces'][{si}]['area']")
    _require_optional_number(s.get("width"), f"{si_path_prefix}[{zi}]['surfaces'][{si}]['width']")
    _require_optional_number(s.get("height"), f"{si_path_prefix}[{zi}]['surfaces'][{si}]['height']")
    _require_optional_str(s.get("window_type_ref"), f"{si_path_prefix}[{zi}]['surfaces'][{si}]['window_type_ref']")

def _validate_zone_fields(zn: Dict[str, Any], zi: int, si_path_prefix: str) -> None:
    _require_optional_str(zn.get("id"), f"{si_path_prefix}[{zi}]['id']")
    _require_optional_str(zn.get("name"), f"{si_path_prefix}[{zi}]['name']")
    _require_optional_str(zn.get("type"), f"{si_path_prefix}[{zi}]['type']")
    _require_optional_number(zn.get("floor_area"), f"{si_path_prefix}[{zi}]['floor_area']")
    _require_optional_number(zn.get("volume"), f"{si_path_prefix}[{zi}]['volume']")

def _validate_hvac_fields(hv: Dict[str, Any], hi: int, where: str) -> None:
    _require_optional_str(hv.get("name"), f"{where}[{hi}]['name']")
    _require_optional_str(hv.get("system_type"), f"{where}[{hi}]['system_type']")
    _require_optional_str(hv.get("type"), f"{where}[{hi}]['type']")
    _require_optional_str(hv.get("fuel"), f"{where}[{hi}]['fuel']")
    _require_optional_str(hv.get("fuel_type"), f"{where}[{hi}]['fuel_type']")
    _require_optional_number(hv.get("heating_eff"), f"{where}[{hi}]['heating_eff']")
    _require_optional_number(hv.get("hspf"), f"{where}[{hi}]['hspf']")
    _require_optional_number(hv.get("afue"), f"{where}[{hi}]['afue']")
    _require_optional_number(hv.get("cooling_eff"), f"{where}[{hi}]['cooling_eff']")
    _require_optional_number(hv.get("seer"), f"{where}[{hi}]['seer']")
    _require_optional_number(hv.get("eer"), f"{where}[{hi}]['eer']")
    if "served_zones" in hv:
        if not isinstance(hv["served_zones"], list):
            raise TypeError(f"{where}[{hi}]['served_zones'] must be list, got {type(hv['served_zones']).__name__}")
        for zi, zref in enumerate(hv["served_zones"]):
            if not (isinstance(zref, str) or isinstance(zref, dict)):
                raise TypeError(
                    f"{where}[{hi}]['served_zones'][{zi}] must be str or dict, got {type(zref).__name__}"
                )
            if isinstance(zref, dict):
                _require_optional_str(zref.get("id"), f"{where}[{hi}]['served_zones'][{zi}]['id']")
                _require_optional_str(zref.get("name"), f"{where}[{hi}]['served_zones'][{zi}]['name']")

def _validate_shapes(em_v5: Dict[str, Any]) -> None:
    """Deeper shape + field checks so TypeErrors are actionable (matches tests’ expectations)."""
    # top-level types
    if "project" in em_v5 and not isinstance(em_v5["project"], dict):
        raise TypeError(f"em_v5['project'] must be dict, got {type(em_v5['project']).__name__}")
    if "catalogs" in em_v5 and not isinstance(em_v5["catalogs"], dict):
        raise TypeError(f"em_v5['catalogs'] must be dict, got {type(em_v5['catalogs']).__name__}")

    # scenarios: must exist, be non-empty list, and contain at least one dict zone
    if "scenarios" not in em_v5:
        raise TypeError("em_v5['scenarios'] must be present and be a list with at least one scenario containing zones.")
    if not isinstance(em_v5["scenarios"], list):
        raise TypeError(f"em_v5['scenarios'] must be list, got {type(em_v5['scenarios']).__name__}")
    if len(em_v5["scenarios"]) == 0:
        raise TypeError("em_v5['scenarios'] must not be empty.")

    has_any_zone = False
    for si, sc in enumerate(em_v5["scenarios"]):
        if not isinstance(sc, dict):
            raise TypeError(f"em_v5['scenarios'][{si}] must be dict, got {type(sc).__name__}")
        if "zones" in sc:
            if not isinstance(sc["zones"], list):
                raise TypeError(f"em_v5['scenarios'][{si}]['zones'] must be list, got {type(sc['zones']).__name__}")
            for zi, zn in enumerate(sc["zones"]):
                if not isinstance(zn, dict):
                    raise TypeError(
                        f"em_v5['scenarios'][{si}]['zones'][{zi}] must be dict, got {type(zn).__name__}"
                    )
                has_any_zone = True
                # zone field checks
                _require_optional_str(zn.get("id"), f"em_v5['scenarios'][{si}]['zones'][{zi}]['id']")
                _require_optional_str(zn.get("name"), f"em_v5['scenarios'][{si}]['zones'][{zi}]['name']")
                _require_optional_str(zn.get("type"), f"em_v5['scenarios'][{si}]['zones'][{zi}]['type']")
                _require_optional_number(zn.get("floor_area"), f"em_v5['scenarios'][{si}]['zones'][{zi}]['floor_area']")
                _require_optional_number(zn.get("volume"), f"em_v5['scenarios'][{si}]['zones'][{zi}]['volume']")
                # surfaces must be list[dict] if present
                if "surfaces" in zn:
                    if not isinstance(zn["surfaces"], list):
                        raise TypeError(
                            f"em_v5['scenarios'][{si}]['zones'][{zi}]['surfaces'] must be list, got {type(zn['surfaces']).__name__}"
                        )
                    for ui, surf in enumerate(zn["surfaces"]):
                        if not isinstance(surf, dict):
                            raise TypeError(
                                f"em_v5['scenarios'][{si}]['zones'][{zi}]['surfaces'][{ui}] must be dict, got {type(surf).__name__}"
                            )
                        _validate_surface_fields(surf, ui, zi, f"em_v5['scenarios'][{si}]['zones']")

    if not has_any_zone:
        # Match the spirit of the test expecting a TypeError when nothing exportable is present.
        raise TypeError("[export] No zones found (searched scenarios[].zones).")

    # libraries
    if "libraries" in em_v5:
        if not isinstance(em_v5["libraries"], dict):
            raise TypeError(f"em_v5['libraries'] must be dict, got {type(em_v5['libraries']).__name__}")
        libs = em_v5["libraries"]
        if "hvac_systems" in libs:
            _validate_list_of_dict("em_v5['libraries']['hvac_systems']", libs["hvac_systems"])
            for hi, hv in enumerate(libs["hvac_systems"]):
                _validate_hvac_fields(hv, hi, "em_v5['libraries']['hvac_systems']")

    # optional catalogs sublists: if present, they must be list of dicts
    cats = em_v5.get("catalogs")
    if isinstance(cats, dict):
        for key in ("window_types", "du_types", "construction_types"):
            if key in cats:
                _validate_list_of_dict(f"em_v5['catalogs']['{key}']", cats[key])


# ------------------------------ writers ------------------------------

def _write_project(root: ET.Element, em: Dict[str, Any]) -> None:
    proj, loc = _get_project_and_location(em)
    project_el = ET.SubElement(root, "Project")
    _maybe(project_el, "Name", proj.get("name"))
    _maybe(project_el, "Id", proj.get("id"))
    _maybe(project_el, "Description", proj.get("description"))
    _maybe(project_el, "City", loc.get("city"))
    _maybe(project_el, "State", loc.get("state"))
    _maybe(project_el, "PostalCode", loc.get("postal_code"))
    _maybe(project_el, "ClimateZone", loc.get("climate_zone"))
    loc_el = ET.SubElement(project_el, "Location")
    _maybe(loc_el, "City", loc.get("city"))
    _maybe(loc_el, "State", loc.get("state"))
    _maybe(loc_el, "PostalCode", loc.get("postal_code"))
    _maybe(loc_el, "ClimateZone", loc.get("climate_zone"))

def _write_catalogs(root: ET.Element, em: Dict[str, Any]) -> None:
    cats = _get_catalogs(em)
    if not cats:
        return
    cats_el = ET.SubElement(root, "Catalogs")

    # Window Types
    wtypes = cats.get("window_types") or []
    if isinstance(wtypes, list) and wtypes:
        w_el = ET.SubElement(cats_el, "WindowTypes")
        for wt in wtypes:
            if not isinstance(wt, dict):
                continue
            el = ET.SubElement(w_el, "WindowType")
            _maybe(el, "Name", wt.get("name"))
            _maybe(el, "uFactor", wt.get("u") or wt.get("u_factor"))
            _maybe(el, "solarHeatGainCoeff", wt.get("shgc") or wt.get("solarHeatGainCoeff"))
            _maybe(el, "visibleTrans", wt.get("vt") or wt.get("visibleTrans"))

    # Dwelling Unit Types
    du_types = cats.get("du_types") or []
    if isinstance(du_types, list) and du_types:
        du_el = ET.SubElement(cats_el, "DUTypes")
        for du in du_types:
            if not isinstance(du, dict):
                continue
            el = ET.SubElement(du_el, "DUType")
            _maybe(el, "Name", du.get("name"))
            _maybe(el, "FloorArea", du.get("floor_area"))

    # Construction Types
    c_types = cats.get("construction_types") or []
    if isinstance(c_types, list) and c_types:
        c_el = ET.SubElement(cats_el, "ConstructionTypes")
        for ct in c_types:
            if not isinstance(ct, dict):
                continue
            el = ET.SubElement(c_el, "ConstructionType")
            _maybe(el, "Name", ct.get("name"))
            _maybe(el, "uFactor", ct.get("u") or ct.get("u_factor"))

def _write_geometry(root: ET.Element, em: Dict[str, Any]) -> None:
    geom_el = ET.SubElement(root, "Geometry")
    for zn in _iter_zones(em):
        zn_el = ET.SubElement(geom_el, "ResZn")
        _maybe(zn_el, "Name", zn.get("name") or zn.get("id"))
        _maybe(zn_el, "Id", zn.get("id"))
        _maybe(zn_el, "Type", zn.get("type"))
        _maybe(zn_el, "FloorArea", zn.get("floor_area"))
        _maybe(zn_el, "Volume", zn.get("volume"))

        # Collect windows then emit both forms
        windows: List[Dict[str, Any]] = []
        for win in _iter_window_surfaces(zn):
            windows.append(win)
            # flat form
            surf_el = ET.SubElement(zn_el, "Surface", {"surfaceType": "Window"})
            _maybe(surf_el, "Name", win.get("name"))
            _maybe(surf_el, "Area", win.get("area"))
            _maybe(surf_el, "Width", win.get("width"))
            _maybe(surf_el, "Height", win.get("height"))
            _maybe(surf_el, "WindowTypeRef", win.get("window_type_ref"))

        # nested form for import compat
        if windows:
            wall_el = ET.SubElement(zn_el, "ResExtWall")
            _maybe(wall_el, "Name", "Auto Wall for Windows")
            wins_el = ET.SubElement(wall_el, "Windows")
            for win in windows:
                rw = ET.SubElement(wins_el, "ResWindow")
                _maybe(rw, "Name", win.get("name"))
                _maybe(rw, "Area", win.get("area"))
                _maybe(rw, "Width", win.get("width"))
                _maybe(rw, "Height", win.get("height"))
                _maybe(rw, "WindowTypeRef", win.get("window_type_ref"))

def _collect_all_zone_ids(em: Dict[str, Any]) -> List[str]:
    out: List[str] = []
    seen: Set[str] = set()
    for zn in _iter_zones(em):
        zid = str(zn.get("id") or zn.get("name") or "").strip()
        if zid and zid not in seen:
            seen.add(zid)
            out.append(zid)
    return out

def _collect_hvac(em: Dict[str, Any]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    seen: Set[Tuple[str, str]] = set()

    libs = em.get("libraries") or {}
    if isinstance(libs, dict):
        lib_hvac = libs.get("hvac_systems") or []
        if isinstance(lib_hvac, list):
            for hv in lib_hvac:
                if not isinstance(hv, dict):
                    continue
                key = (str(hv.get("name") or ""), str(hv.get("id") or ""))
                if key not in seen:
                    seen.add(key); out.append(hv)

    for sc in _iter_scenarios(em):
        sc_hvac = sc.get("hvac_systems") or []
        if isinstance(sc_hvac, list):
            for hv in sc_hvac:
                if not isinstance(hv, dict):
                    continue
                key = (str(hv.get("name") or ""), str(hv.get("id") or ""))
                if key not in seen:
                    seen.add(key); out.append(hv)

    return out

def _served_zone_ids(hv: Dict[str, Any], all_zone_ids: List[str]) -> List[str]:
    cand = hv.get("served_zones") or hv.get("served_zone_ids") or hv.get("zones") \
           or hv.get("zone_refs") or hv.get("served")
    out: List[str] = []
    if isinstance(cand, list):
        for it in cand:
            if isinstance(it, str):
                out.append(it)
            elif isinstance(it, dict):
                z = str(it.get("id") or it.get("name") or "").strip()
                if z: out.append(z)
    if not out and all_zone_ids:
        out = [all_zone_ids[0]]  # graceful fallback
    return out

def _write_hvac(root: ET.Element, em: Dict[str, Any]) -> None:
    hvac_list = _collect_hvac(em)
    if not hvac_list:
        return
    hvac_el = ET.SubElement(root, "HVAC")  # tests expect .//HVAC/ResHVACSys
    all_zone_ids = _collect_all_zone_ids(em)
    for hv in hvac_list:
        el = ET.SubElement(hvac_el, "ResHVACSys")
        _maybe(el, "Name", hv.get("name") or hv.get("id"))
        _maybe(el, "SystemType", hv.get("system_type") or hv.get("type"))
        _maybe(el, "FuelType", hv.get("fuel") or hv.get("fuel_type"))
        _maybe(el, "HeatingEff", hv.get("heating_eff") or hv.get("hspf") or hv.get("afue"))
        _maybe(el, "CoolingEff", hv.get("cooling_eff") or hv.get("seer") or hv.get("eer"))
        sz = _served_zone_ids(hv, all_zone_ids)
        if sz:
            sz_el = ET.SubElement(el, "ServedZones")
            for zid in sz:
                _maybe(sz_el, "ZoneRef", zid)


# ------------------------------ public API ------------------------------

def export_emjson_v5_to_cibd22x(em_v5: Dict[str, Any]) -> str:
    """
    Translate an EMJSON v5 dict → CBECC .cibd22x XML string (UTF-8).
    Raises:
      TypeError on wrong input type / wrong shapes & field types.
    """
    if not isinstance(em_v5, dict):
        raise TypeError(f"em_v5 must be a dict, got {type(em_v5).__name__}")

    _validate_shapes(em_v5)  # <- deep container + field checks

    root = ET.Element("CBECCProject")
    _write_project(root, em_v5)
    _write_catalogs(root, em_v5)
    _write_geometry(root, em_v5)
    _write_hvac(root, em_v5)

    xml_bytes = ET.tostring(root, encoding="utf-8", xml_declaration=True)
    return xml_bytes.decode("utf-8")
