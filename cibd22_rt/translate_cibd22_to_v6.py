# --- file: cibd22_rt/translate_cibd22_to_v6.py
"""
CIBD22 → EMJSON v6 translator (standalone package)

Usage
-----
from cibd22_rt.translate_cibd22_to_v6 import translate_cibd22_to_v6
em = translate_cibd22_to_v6(xml_text, validate_flag=True)

Notes
-----
- Robust to common tag/attribute aliases across CIBD22 inputs.
- Converts units to SI where appropriate (U-value, R-value, areas, lengths, temps, capacities).
- Enriches DHW with HPWH details and PV/Storage with advanced fields if present.
- `validate_flag=True` runs basic referential checks (zones↔surfaces↔openings, constructions, window types).
"""

from __future__ import annotations
from typing import Dict, Any, List, Tuple, Optional, Set
import xml.etree.ElementTree as ET

# ---------------- Candidate paths ----------------
PATHS: Dict[str, List[str]] = {
    "project": ["./Project", "./PROJECT"],
    "run": ["./Project/Run", "./Run", "./RUN"],
    "std_design": ["./Project/StandardDesign", "./StandardDesign", "./STANDARD_DESIGN"],
    "location": ["./Project/Location", "./Location"],

    "zones_res": [".//ResZn", ".//RES_ZN"],
    "zones_com": [".//ComZn", ".//COM_ZN"],

    "surfaces": [
        ".//ResExtWall", ".//ComExtWall",
        ".//ResRoof", ".//ComRoof",
        ".//ResFloor", ".//ComFloor",
    ],

    "openings": [
        ".//ResWindowInstance", ".//ComWindowInstance",
        ".//Opening",  # skylights/doors sometimes presented as generic Opening
    ],

    "window_types": [
        ".//ResWindowType", ".//ComWindowType", ".//WindowType",
    ],

    "construction_types": [
        ".//ResConstruction", ".//ComConstruction", ".//ConstructionType",
    ],

    "schedules": [".//Schedule", ".//Schedules/*"],
    "hvac_systems": [".//ResHVACSys", ".//ComHVACSys", ".//HVACSystem"],
    "dhw_systems": [".//ResDHWSys", ".//ComDHWSys", ".//DHWSystem"],
    "pv_arrays": [".//PVArray", ".//PV/*"],
    "batteries": [".//Battery", ".//Storage/Battery"],

    "infiltration": [".//ResInfiltration", ".//ComInfiltration", ".//Infiltration"],
    "mech_vent": [".//ResMechVent", ".//ComMechVent", ".//MechanicalVentilation", ".//Ventilation"],
    "ducts": [".//Duct", ".//SupplyDuct", ".//ReturnDuct"],
    "dhw_dist": [".//DHWDistribution", ".//DHW/Distribution", ".//DHW/RecircLoop"],
}

# ---------------- Helpers ----------------
def _first(root: ET.Element, candidates: List[str]) -> Optional[ET.Element]:
    for p in candidates:
        node = root.find(p)
        if node is not None:
            return node
    return None

def _all(root: ET.Element, candidates: List[str]) -> List[ET.Element]:
    results: List[ET.Element] = []
    for p in candidates:
        results.extend(root.findall(p))
    # Deduplicate by tag+id (or fallback to xml bytes)
    uniq: List[ET.Element] = []
    seen: Set[str] = set()
    for n in results:
        key = f"{n.tag}:{n.get('id') or n.get('Id') or n.get('ID') or ET.tostring(n, encoding='utf-8')}"
        if key not in seen:
            seen.add(key)
            uniq.append(n)
    return uniq

def _txt(node: Optional[ET.Element], tag: str, default: str = "") -> str:
    if node is None:
        return default
    child = node.find(tag)
    return (child.text or "").strip() if (child is not None and child.text) else default

def _attr(node: Optional[ET.Element], name: str, default: str = "") -> str:
    if node is None:
        return default
    for k in (name, name.capitalize(), name.upper()):
        if k in node.attrib:
            return (node.attrib[k] or "").strip()
    return default

def _units(node: Optional[ET.Element]) -> str:
    if node is None:
        return ""
    for k in ("units","Units","UNITS"):
        if k in node.attrib:
            return (node.attrib[k] or "").strip()
    return ""

def _to_float(s: str, default: float = 0.0) -> float:
    try:
        return float(s)
    except Exception:
        return default

def _as_float(s: str, default: float = 0.0) -> float:
    try:
        return float(s)
    except Exception:
        return default

def _digits(s: str) -> str:
    return "".join(ch for ch in (s or "") if ch.isdigit())

def _cz_to_int(s: str) -> int:
    ds = _digits(s)
    try:
        return int(ds) if ds else 0
    except Exception:
        return 0

def _elev_to_m(node: Optional[ET.Element]) -> float:
    if node is None:
        return 0.0
    txt = (node.text or "").strip()
    val = _as_float(txt, 0.0)
    units = _units(node).lower()
    if units in ("ft", "feet"):
        return val * 0.3048
    return val

def _len_to_m(node: Optional[ET.Element], default: float = 0.0) -> float:
    if node is None:
        return default
    txt = (node.text or "").strip()
    v = _to_float(txt, default)
    u = _units(node).lower()
    if u in ("mm","millimeter","millimeters"):
        return v / 1000.0
    if u in ("in","inch","inches"):
        return v * 0.0254
    if u in ("ft","feet"):
        return v * 0.3048
    return v  # assume meters

def _area_to_m2(node: Optional[ET.Element], default: float = 0.0) -> float:
    if node is None:
        return default
    txt = (node.text or "").strip()
    v = _to_float(txt, default)
    u = _units(node).lower()
    if u in ("ft2","sqft","sf"):
        return v * 0.092903
    return v  # assume m2

def _u_to_si(val: float, units_hint: str = "") -> float:
    # IP (Btu/hr-ft2-F) → SI (W/m2-K)
    if units_hint.lower() in ("w/m2k","w/m2-k","si","metric"):
        return val
    if units_hint.lower() in ("btu/hr-ft2-f","ip","imperial"):
        return val * 5.678263
    # Heuristic: values > 1.5 are likely IP U-factors
    return val if val <= 1.5 else val * 5.678263

def _ip_r_to_si(r_ip: float) -> float:
    # h·ft²·F/Btu → m²·K/W
    return r_ip * 0.176110

def _norm_op(v: str) -> str:
    m = {
        "fixed": "fixed",
        "singlehung": "single_hung",
        "doublehung": "double_hung",
        "horizontalslider": "horizontal_slider",
        "slider": "horizontal_slider",
        "casement": "casement",
        "awning": "awning",
    }
    key = (v or "").strip().lower().replace(" ", "")
    return m.get(key, v or "")

def _maybe_bool(txt: str) -> Optional[bool]:
    if txt is None or txt == "":
        return None
    t = txt.strip().lower()
    if t in ("1","true","yes","y"):
        return True
    if t in ("0","false","no","n"):
        return False
    return None

def _seer_to_cop(seer: Optional[float]) -> Optional[float]:
    return None if seer is None else seer / 3.412

def _eer_to_cop(eer: Optional[float]) -> Optional[float]:
    return None if eer is None else eer / 3.412

def _hspf_to_cop(hspf: Optional[float]) -> Optional[float]:
    return None if hspf is None else hspf / 3.412

def _percent_to_frac(p: Optional[float]) -> Optional[float]:
    if p is None:
        return None
    return p/100.0 if p > 1.5 else p

def _btu_to_kw(btu_per_hr: Optional[float]) -> Optional[float]:
    return None if btu_per_hr is None else btu_per_hr * 0.00029307107

def _ton_or_btu_to_kw(val: Optional[float]) -> Optional[float]:
    if val is None:
        return None
    # Heuristic: if value < 50, assume tons; else assume Btu/h
    return val * 3.5168525 if val < 50 else _btu_to_kw(val)

def _F_to_C(v: Optional[float]) -> Optional[float]:
    return None if v is None else (v - 32.0) * 5.0 / 9.0

def _gal_to_L(v: Optional[float]) -> Optional[float]:
    return None if v is None else v * 3.78541

def _ft_to_m(v: Optional[float]) -> Optional[float]:
    return None if v is None else v * 0.3048

def _cfm_to_m3ph(v: Optional[float]) -> Optional[float]:
    # 1 CFM ≈ 1.699 m3/h
    return None if v is None else v * 1.699

def _diag(diags: List[Dict[str, Any]], level: str, code: str, message: str) -> None:
    diags.append({"level": level, "code": code, "message": message})

# ---------------- Parsers ----------------
def _parse_location(root: ET.Element, diags: List[Dict[str, Any]]) -> Dict[str, Any]:
    loc_node = _first(root, PATHS["location"])
    city = _txt(loc_node, "City") or _txt(root, "City", "")
    state = _txt(loc_node, "State") or _txt(root, "State", "")
    county = _txt(loc_node, "County") or _txt(root, "County", "")
    zip_raw = _txt(loc_node, "ZipCode") or _txt(root, "ZipCode", "") or _txt(root, "PostalCode", "")
    digits = _digits(zip_raw)
    zip_code = (digits[:5].rjust(5, "0")) if digits else ""

    lat = _txt(loc_node, "Latitude") or _txt(root, "Latitude", "")
    lon = _txt(loc_node, "Longitude") or _txt(root, "Longitude", "")
    elev_node = loc_node.find("Elevation") if loc_node is not None else None
    if elev_node is None:
        elev_node = root.find(".//Elevation")
    elevation_m = _elev_to_m(elev_node)

    tz = _txt(loc_node, "TimeZone") or _txt(root, "TimeZone", "") or _txt(root, "GMTOffset", "")
    cz_raw = _txt(loc_node, "ClimateZone") or _txt(root, "ClimateZone", "") or _txt(root, "CZ", "")
    climate_zone = _cz_to_int(cz_raw)
    cz_ver = _txt(loc_node, "ClimateZoneVersion") or "2022"

    wstat = _txt(loc_node, "WeatherStationId") or _txt(loc_node, "WeatherStationName") or \
            _txt(root, "WeatherStationId", "") or _txt(root, "WeatherStationName", "")
    wfile = _txt(loc_node, "WeatherFile") or _txt(loc_node, "WeatherFileName") or \
            _txt(root, "WeatherFile", "") or _txt(root, "WeatherFileName", "")

    state_norm = (state or "").strip()
    if len(state_norm) > 2 and state_norm.isalpha():
        state_norm = state_norm.upper()[:2]

    loc = {
        "city": city,
        "state": state_norm,
        "county": county,
        "zip_code": zip_code,
        "latitude": _as_float(lat, 0.0),
        "longitude": _as_float(lon, 0.0),
        "elevation_m": elevation_m,
        "timezone": tz,
        "climate_zone": climate_zone,
        "climate_zone_version": cz_ver,
        "weather_station_id": wstat,
        "weather_file": wfile,
        "source": "xml" if climate_zone else "derived",
    }

    if not zip_code:
        _diag(diags, "warning", "W-LOC-NOZIP", "No ZipCode found; consider ZIP→CZ fallback if needed")
    if climate_zone == 0:
        _diag(diags, "warning", "W-LOC-NOCZ", "No ClimateZone found in XML; leaving 0 (derive later if enabled)")
    _diag(diags, "info", "I-MAP-LOC", f"location keys set={[k for k in loc.keys() if loc[k] not in ('', 0, 0.0)]}")
    return loc

def _parse_project(root: ET.Element, diags: List[Dict[str, Any]]) -> Dict[str, Any]:
    proj = _first(root, PATHS["project"]) or root
    run = _first(root, PATHS["run"])
    std = _first(root, PATHS["std_design"])

    project = {
        "model_info": {
            "BldgEngyModelVersion": _txt(proj, "BldgEngyModelVersion", ""),
            "GeometryInpType": _txt(proj, "GeometryInpType", ""),
            "SourceFormat": "CIBD22",
        },
        "run": {
            "RunTitle": _txt(run, "RunTitle", ""),
            "RunDate": _txt(run, "RunDate", ""),
            "SoftwareVersion": _txt(run, "SoftwareVersion", ""),
        },
        "standard_design": {
            "StdDesignFuel_DHW": _txt(std, "StdDesignFuel_DHW", ""),
            "StdDesignFuel_Ckg": _txt(std, "StdDesignFuel_Ckg", ""),
        },
        "location": _parse_location(root, diags),
    }
    _diag(diags, "info", "I-MAP-PROJ", f"project keys={list(project.keys())}")
    return project

def _parse_zones(root: ET.Element, diags: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    zs = _all(root, PATHS["zones_res"]) + _all(root, PATHS["zones_com"])
    zones: List[Dict[str, Any]] = []
    for z in zs:
        zones.append({
            "id": _attr(z, "id") or _txt(z, "Id", ""),
            "name": _txt(z, "Name", ""),
            "type": "res" if "Res" in z.tag or "RES" in z.tag else "com",
            "multiplier": float(_txt(z, "Multiplier", "1") or "1"),
        })
    _diag(diags, "info", "I-MAP-ZONES", f"zones parsed={len(zones)}")
    return zones

def _parse_surfaces(root: ET.Element, diags: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    surfs: List[Dict[str, Any]] = []
    for s in _all(root, PATHS["surfaces"]):
        a_node = s.find("Area") or s.find("GrossArea") or s.find("NetArea")
        area_m2 = _area_to_m2(a_node, 0.0)
        surf = {
            "id": _attr(s, "id") or _txt(s, "Id", ""),
            "zone_ref": _txt(s, "ZoneIdRef", "") or _txt(s, "ParentZoneIdRef", ""),
            "type": s.tag,  # keep original tag; normalize later if needed
            "area": area_m2,
            "construction_ref": _txt(s, "ConstructionIdRef", "") or _txt(s, "ConstIdRef", ""),
            "azimuth_deg": _to_float(_txt(s, "Azimuth", "") or _txt(s, "Orientation", ""), 0.0),
            "tilt_deg": _to_float(_txt(s, "Tilt", "") or _txt(s, "Slope", ""), 90.0),
            "boundary": _txt(s, "BoundaryCondition", "") or _txt(s, "Boundary", "") or "Outdoors",
            "ground_contact": _maybe_bool(_txt(s, "GroundContact", "")) if _txt(s, "GroundContact", "") != "" else None,
            "story_index": int(_to_float(_txt(s, "StoryIndex", "") or _txt(s, "Story", "") or _txt(s, "Level", ""), 0.0)) if (_txt(s, "StoryIndex", "") or _txt(s, "Story", "") or _txt(s, "Level", "")) else None,
        }
        surfs.append(surf)
    _diag(diags, "info", "I-MAP-SURF", f"surfaces parsed={len(surfs)}")
    return surfs

def _parse_openings(root: ET.Element, diags: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    ops: List[Dict[str, Any]] = []
    for o in _all(root, PATHS["openings"]):
        w_node = o.find("Width")
        h_node = o.find("Height")
        width_m = _len_to_m(w_node, 0.0)
        height_m = _len_to_m(h_node, 0.0)
        a_node = o.find("Area") or o.find("GlazedArea")
        area_m2 = _area_to_m2(a_node, 0.0)
        if area_m2 <= 0.0 and width_m > 0.0 and height_m > 0.0:
            area_m2 = width_m * height_m

        def _t(name, default=""):
            return _txt(o, name, default)

        ops.append({
            "id": _attr(o, "id") or _t("Id", ""),
            "parent_surface": _t("SurfaceIdRef") or _t("ParentSurfaceIdRef"),
            "window_type_ref": _t("WindowTypeIdRef") or _t("TypeIdRef"),
            "width_m": width_m,
            "height_m": height_m,
            "area_m2": area_m2,
            "azimuth_deg": _to_float(_t("Azimuth") or _t("Orientation"), 0.0),
            "tilt_deg": _to_float(_t("Tilt") or _t("Slope"), 90.0),
            "x_offset_m": _len_to_m(o.find("XOffset"), 0.0),
            "y_offset_m": _len_to_m(o.find("YOffset"), 0.0),
            "z_offset_m": _len_to_m(o.find("ZOffset"), 0.0),
        })

    _diag(diags, "info", "I-MAP-OPEN",
          f"openings parsed={len(ops)} (area_fallback={'yes' if any((op['area_m2']==op['width_m']*op['height_m']) for op in ops if op['width_m'] and op['height_m']) else 'no'})")
    return ops

def _parse_catalogs(root: ET.Element, diags: List[Dict[str, Any]]) -> Dict[str, Any]:
    # Window types (res + com)
    wtypes: List[Dict[str, Any]] = []
    for w in _all(root, PATHS["window_types"]):
        def _t(name, default=""): return _txt(w, name, default)
        def _f(name, default=0.0): return _to_float(_t(name, ""), default)
        def _n(tag_name: str) -> Optional[ET.Element]: return w.find(tag_name)

        u_node = _n("UValue") or _n("U") or _n("Ufactor") or _n("UFactor") or _n("UFactorIP")
        u_raw = _to_float((u_node.text or "").strip(), 0.0) if (u_node is not None and u_node.text) else 0.0
        u_si = _u_to_si(u_raw, _units(u_node))

        base = {
            "id": _attr(w, "id") or _t("Id", ""),
            "name": _t("Name", ""),
            "frame_type": _t("FrameType") or _t("Frame"),
            "glazing_layers": int(_f("GlazingLayers", 0) or _f("Layers", 0) or _f("Panes", 0) or 2),
            "gas_fill": _t("GasFill") or _t("Gas"),
            "coating": (_t("Coating") or _t("GlassCoating") or "LoE").replace("LowE", "LoE"),
            "u_value": u_si,
            "shgc": _f("SHGC", 0.0) or _f("SolarHeatGainCoeff", 0.0),
            "vt": _f("VT", 0.0) or _f("Tvis", 0.0) or _f("VLT", 0.0) or _f("VisibleTransmittance", 0.0),
            "frame_fraction": _f("FrameFraction", 0.12) or _f("FramingFraction", 0.12),
            "divider_fraction": _f("DividerFraction", 0.0) or _f("Dividers", 0.0),
            "notes": _t("Notes") or _t("Description") or _t("ProductID") or _t("NFRC_ID"),
        }

        tag_upper = w.tag.upper()
        if "RESWINDOWTYPE" in tag_upper or "RES" in tag_upper:
            # Residential extras
            oper_raw = _t("OperType") or _t("Operation") or _t("Operable")
            thermal_break_raw = _t("ThermalBreak", "")
            thermal_break = _maybe_bool(thermal_break_raw)
            if thermal_break is None and (base["frame_type"] or "").lower().startswith("alum") and "thermbreak" in (base["frame_type"] or "").lower():
                thermal_break = True
            edge_spacer = _t("EdgeSpacerType") or _t("SpacerType")
            air_leak = _f("AirLeakage", 0.0)  # keep IP (cfm/ft2) as-is

            base.update({
                "operation": _norm_op(oper_raw),
                "thermal_break": thermal_break,
                "edge_spacer": edge_spacer,
                "air_leakage_cfm2": air_leak if air_leak > 0 else None,
            })

        wtypes.append(base)

    # Constructions (with optional U/R + basic layers)
    ctypes: List[Dict[str, Any]] = []
    for c in _all(root, PATHS["construction_types"]):
        u_node = c.find("UValue") or c.find("U") or c.find("Ufactor") or c.find("UFactor")
        r_node = c.find("RValue") or c.find("R") or c.find("Rfactor") or c.find("RFactor")
        u_val = _to_float((u_node.text or "").strip(), 0.0) if u_node is not None and u_node.text else None
        r_val = _to_float((r_node.text or "").strip(), 0.0) if r_node is not None and r_node.text else None
        u_si = _u_to_si(u_val, _units(u_node)) if u_val is not None else None
        r_si = _ip_r_to_si(r_val) if r_val is not None else None

        layers: List[Dict[str, Any]] = []
        for ln in c.findall("Layer") + c.findall("ConstructionLayer"):
            layers.append({
                "material_ref": _txt(ln, "MaterialIdRef", "") or _txt(ln, "MatIdRef", "") or _txt(ln, "LayerMaterialIdRef", ""),
                "thickness_m": _len_to_m(ln.find("Thickness"), 0.0) if ln.find("Thickness") is not None else None,
            })

        ctypes.append({
            "id": _attr(c, "id") or _txt(c, "Id", ""),
            "name": _txt(c, "Name", ""),
            "u_value": u_si,
            "r_value": r_si,
            "layers": layers,
        })

    # Schedules (kept minimal — placeholder)
    schedules: List[Dict[str, Any]] = []
    for s in _all(root, PATHS["schedules"]):
        schedules.append({
            "id": _attr(s, "id") or _txt(s, "Id", ""),
            "name": _txt(s, "Name", ""),
            "type": _txt(s, "Type", ""),
        })

    _diag(diags, "info", "I-MAP-CAT",
          f"window_types={len(wtypes)} construction_types={len(ctypes)} schedules={len(schedules)}")
    if len(wtypes) == 0:
        _diag(diags, "warning", "W-NO-WINTYPES", "No window types found — check library paths/aliases")

    return {
        "window_types": wtypes,
        "construction_types": ctypes,
        "schedules": schedules,
    }

def _parse_systems(root: ET.Element, diags: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    hvac: List[Dict[str, Any]] = []
    for h in _all(root, PATHS["hvac_systems"]):
        def t(n, d=""): return _txt(h, n, d)
        def f(n, d=0.0):
            try: return float(t(n, ""))
            except Exception: return d
        cool_cap_kw = _ton_or_btu_to_kw( f("CoolingCapacity") or f("CoolCap") or None )
        heat_cap_kw = _btu_to_kw( f("HeatingCapacity") or f("HeatCap") or None )
        seer = f("SEER") or f("RatedSEER") or None
        eer = f("EER") or f("RatedEER") or None
        hspf = f("HSPF") or f("RatedHSPF") or None
        afue = _percent_to_frac( f("AFUE") or f("RatedAFUE") or None )

        hvac.append({
            "id": _attr(h, "id") or t("Id", ""),
            "name": t("Name", ""),
            "system_type": t("Type") or t("SystemType") or t("SysType"),
            "heating_type": t("HeatingType") or t("HeatType"),
            "cooling_type": t("CoolingType") or t("CoolType"),
            "heating_fuel": t("HeatingFuel") or t("Fuel") or t("HeatFuel"),
            "cooling_fuel": t("CoolingFuel") or t("CoolFuel") or "Electricity",
            "supply_fan_w_per_cfm": f("SupplyFanPowerPerCFM") or f("FanWPerCFM") or None,
            "supply_air_cfm": f("SupplyAirCFM") or f("SupplyCFM") or None,
            "cooling_capacity_kw": cool_cap_kw,
            "heating_capacity_kw": heat_cap_kw,
            "eer": eer,
            "seer": seer,
            "cop_cooling": _seer_to_cop(seer) or _eer_to_cop(eer),
            "hspf": hspf,
            "cop_heating": _hspf_to_cop(hspf),
            "afue": afue,
            "zones_served": [z.text.strip() for z in (h.findall("ZoneIdRef") + h.findall("ServedZoneIdRef")) if (z is not None and z.text)],
        })

    dhw: List[Dict[str, Any]] = []
    for d in _all(root, PATHS["dhw_systems"]):
        def t(n, dft=""): return _txt(d, n, dft)
        def f(n, dft=0.0):
            try: return float(t(n, ""))
            except Exception: return dft
        dhw.append({
            "id": _attr(d, "id") or t("Id", ""),
            "name": t("Name", ""),
            "system_type": t("Type") or t("SystemType") or t("SysType"),
            "fuel": t("Fuel") or t("EnergySource"),
            "storage_volume_L": _gal_to_L( f("TankVolume") or f("StorageVolume") or None ),
            "setpoint_C": _F_to_C( f("Setpoint") or f("SetPoint") or None ) if (t("Setpoint") or t("SetPoint")) else 49.0,
            "uef": f("UEF") or f("EF") or f("EnergyFactor") or None,
            "recirc": _maybe_bool( t("Recirc") or t("Recirculation") ),
            "recirc_pump_W": f("RecircPumpPower") or f("PumpPower") or None,
        })

    _diag(diags, "info", "I-MAP-SYS", f"hvac={len(hvac)} dhw={len(dhw)}")
    return hvac, dhw

def _parse_pv_storage(root: ET.Element, diags: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    pv: List[Dict[str, Any]] = []
    for p in _all(root, PATHS["pv_arrays"]):
        pv.append({
            "id": _attr(p, "id") or _txt(p, "Id", ""),
            "name": _txt(p, "Name", ""),
            "kw_dc": float(_txt(p, "kWdc", "0") or "0"),
        })
    bat: List[Dict[str, Any]] = []
    for b in _all(root, PATHS["batteries"]):
        bat.append({
            "id": _attr(b, "id") or _txt(b, "Id", ""),
            "name": _txt(b, "Name", ""),
            "kwh": float(_txt(b, "kWh", "0") or "0"),
        })
    _diag(diags, "info", "I-MAP-PV", f"pv={len(pv)} bat={len(bat)}")
    return pv, bat

def _parse_infiltration_ventilation(root: ET.Element, diags: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    infiltrations: List[Dict[str, Any]] = []
    for n in _all(root, PATHS["infiltration"]):
        infiltrations.append({
            "id": _attr(n, "id") or _txt(n, "Id", ""),
            "zone_ref": _txt(n, "ZoneIdRef", "") or _txt(n, "ParentZoneIdRef", ""),
            "ach": _to_float(_txt(n, "ACH") or _txt(n, "InfiltrationACH", ""), 0.0) or None,
            "cfm": _to_float(_txt(n, "CFM") or _txt(n, "InfiltrationCFM", ""), 0.0) or None,
            "schedule_ref": _txt(n, "ScheduleIdRef", "") or _txt(n, "InfiltrationScheduleIdRef", ""),
            "weather_correction": _to_float(_txt(n, "WeatherCorrection") or _txt(n, "ClimateAdj") or _txt(n, "WindAdj"), 0.0) or None,
        })

    vents: List[Dict[str, Any]] = []
    for n in _all(root, PATHS["mech_vent"]):
        vents.append({
            "id": _attr(n, "id") or _txt(n, "Id", ""),
            "system_ref": _txt(n, "SystemIdRef", "") or _txt(n, "HVACSystemIdRef", ""),
            "zone_ref": _txt(n, "ZoneIdRef", "") or _txt(n, "ServedZoneIdRef", ""),
            "min_oa_cfm_per_person": _to_float(_txt(n, "MinOA_CFMPerPerson") or _txt(n, "OACFMPerPerson"), 0.0) or None,
            "min_oa_cfm_per_area": _to_float(_txt(n, "MinOA_CFMPerArea") or _txt(n, "OACFMPerArea"), 0.0) or None,
            "vent_schedule_ref": _txt(n, "VentScheduleIdRef", "") or _txt(n, "ScheduleIdRef", ""),
            "economizer_type": _txt(n, "EconomizerType", "") or _txt(n, "EconType", ""),
            "erv": _maybe_bool(_txt(n, "ERV", "")),
            "hrv": _maybe_bool(_txt(n, "HRV", "")),
            "sens_eff": _to_float(_txt(n, "SensibleEff") or _txt(n, "SensibleRecoveryEff"), 0.0) or None,
            "lat_eff": _to_float(_txt(n, "LatentEff") or _txt(n, "LatentRecoveryEff"), 0.0) or None,
        })

    _diag(diags, "info", "I-MAP-INFV", f"infiltration={len(infiltrations)} mech_vent={len(vents)}")
    return infiltrations, vents

def _parse_distribution(root: ET.Element, diags: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    ducts: List[Dict[str, Any]] = []
    for n in _all(root, PATHS["ducts"]):
        ducts.append({
            "id": _attr(n, "id") or _txt(n, "Id", ""),
            "system_ref": _txt(n, "SystemIdRef", "") or _txt(n, "HVACSystemIdRef", ""),
            "side": _txt(n, "Side", "") or _txt(n, "Type", "") or "supply",   # supply|return
            "location": _txt(n, "Location", ""),
            "area_m2": _area_to_m2(n.find("Area") or n.find("SurfaceArea"), 0.0) or None,
            "r_value_si": _ip_r_to_si(_to_float(_txt(n, "RValue") or _txt(n, "InsulationR"), 0.0)) or None,
            "leakage_cfm25": _to_float(_txt(n, "LeakageCFM25") or _txt(n, "CFM25"), 0.0) or None,
            "leakage_frac_flow": (_to_float(_txt(n, "LeakageFrac") or _txt(n, "LeakagePercentFlow"), 0.0) / 100.0)
                                  if (_txt(n, "LeakagePercentFlow", "") or _txt(n, "LeakageFrac", "")) else None,
        })

    dhw_dists: List[Dict[str, Any]] = []
    for n in _all(root, PATHS["dhw_dist"]):
        dhw_dists.append({
            "id": _attr(n, "id") or _txt(n, "Id", ""),
            "system_ref": _txt(n, "DHWSystemIdRef", "") or _txt(n, "SystemIdRef", ""),
            "recirc": _maybe_bool(_txt(n, "Recirc", "") or _txt(n, "Recirculation", "")),
            "control_type": _txt(n, "ControlType", "") or _txt(n, "RecircControl", ""),
            "pump_power_W": _to_float(_txt(n, "RecircPumpPower") or _txt(n, "PumpPower"), 0.0) or None,
            "loop_length_m": _ft_to_m(_to_float(_txt(n, "LoopLength") or _txt(n, "RecircLoopLength"), 0.0)) or None,
            "branch_length_m": _ft_to_m(_to_float(_txt(n, "BranchLength") or _txt(n, "TrunkBranchLength"), 0.0)) or None,
            "runout_length_m": _ft_to_m(_to_float(_txt(n, "RunoutLength"), 0.0)) or None,
            "pipe_r_si": _ip_r_to_si(_to_float(_txt(n, "PipeR") or _txt(n, "PipeInsulationR"), 0.0)) or None,
        })

    _diag(diags, "info", "I-MAP-DIST", f"ducts={len(ducts)} dhw_dist={len(dhw_dists)}")
    return ducts, dhw_dists

# ---------------- Enrichers ----------------
def _enhance_dhw_with_hpwh(em: Dict[str, Any], root: ET.Element, diags: List[Dict[str, Any]]) -> None:
    # Attach HPWH details to matching DHW systems if present
    hpwh_nodes = root.findall(".//HeatPumpWaterHeater") + root.findall(".//HPWH")
    if not hpwh_nodes:
        return
    dhw_list = em.get("energy", {}).get("dhw", {}).get("systems", [])
    dhw_by_id = {s.get("id"): s for s in dhw_list if s.get("id")}
    for n in hpwh_nodes:
        sys_ref = _txt(n, "DHWSystemIdRef", "") or _txt(n, "SystemIdRef", "")
        target = dhw_by_id.get(sys_ref)
        if not target:
            continue
        hpwh = {
            "ambient_zone_ref": _txt(n, "AmbientZoneIdRef", "") or _txt(n, "AmbientZoneRef", ""),
            "compressor_cop": _to_float(_txt(n, "COP") or _txt(n, "CompressorCOP"), 0.0) or None,
            "backup_type": _txt(n, "BackupType", "") or _txt(n, "SecondaryType", ""),
            "backup_fuel": _txt(n, "BackupFuel", "") or _txt(n, "SecondaryFuel", ""),
            "backup_eff": _to_float(_txt(n, "BackupEff") or _txt(n, "SecondaryEff"), 0.0) or None,
            "min_ambient_C": _F_to_C(_to_float(_txt(n, "MinAmbientF"), 0.0)) if _txt(n, "MinAmbientF", "") else None,
            "max_ambient_C": _F_to_C(_to_float(_txt(n, "MaxAmbientF"), 0.0)) if _txt(n, "MaxAmbientF", "") else None,
            "airflow_m3_per_h": _cfm_to_m3ph(_to_float(_txt(n, "AirflowCFM"), 0.0)) or None,
            "ducted": _maybe_bool(_txt(n, "Ducted", "")),
            "intake_zone_ref": _txt(n, "IntakeZoneIdRef", ""),
            "exhaust_zone_ref": _txt(n, "ExhaustZoneIdRef", ""),
        }
        target["hpwh"] = hpwh
    _diag(diags, "info", "I-HPWH", "HPWH details attached where available")

def _enhance_pv_storage_adv(em: Dict[str, Any], root: ET.Element, diags: List[Dict[str, Any]]) -> None:
    # PV arrays: match by id and augment
    pv_list = em.get("energy", {}).get("pv", {}).get("arrays", [])
    pv_by_id = {p.get("id"): p for p in pv_list if p.get("id")}
    for n in root.findall(".//PVArray") + root.findall(".//PV/*"):
        pid = _attr(n, "id") or _txt(n, "Id", "")
        if not pid or pid not in pv_by_id:
            continue
        pv = pv_by_id[pid]
        def g(name): return _txt(n, name, "")
        az = g("Azimuth") or g("Orientation")
        tl = g("Tilt") or g("Slope")
        if az: pv["azimuth_deg"] = _to_float(az, 0.0)
        if tl: pv["tilt_deg"] = _to_float(tl, 0.0)
        sref = g("SurfaceIdRef") or g("RoofSurfaceRef")
        if sref: pv["surface_ref"] = sref
        inv_eff = g("InverterEff") or g("InverterEfficiency")
        if inv_eff:
            val = _to_float(inv_eff, 0.0)
            pv["inverter_eff"] = val/100.0 if val>1.5 else val
        dcar = g("DCACRatio") or g("DcToAcRatio")
        if dcar: pv["dc_ac_ratio"] = _to_float(dcar, 0.0)
        shade = g("ShadingFactor") or g("ShadeMult")
        if shade: pv["shading_factor"] = _to_float(shade, 0.0)
        mcount = g("ModuleCount") or g("Panels")
        if mcount: pv["module_count"] = int(_to_float(mcount, 0.0))
        mtype = g("ModuleType") or g("PanelType")
        if mtype: pv["module_type"] = mtype

    # Batteries: augment
    bat_list = em.get("energy", {}).get("storage", {}).get("batteries", [])
    bat_by_id = {b.get("id"): b for b in bat_list if b.get("id")}
    for n in root.findall(".//Battery") + root.findall(".//Storage/Battery"):
        bid = _attr(n, "id") or _txt(n, "Id", "")
        if not bid or bid not in bat_by_id:
            continue
        b = bat_by_id[bid]
        def g(name): return _txt(n, name, "")
        rte = g("RoundTripEff") or g("RTEff")
        if rte:
            val = _to_float(rte, 0.0)
            b["round_trip_eff"] = val/100.0 if val>1.5 else val
        mckw = g("MaxChargeKW") or g("ChargePower")
        if mckw: b["max_charge_kw"] = _to_float(mckw, 0.0)
        mdkw = g("MaxDischargeKW") or g("DischargePower")
        if mdkw: b["max_discharge_kw"] = _to_float(mdkw, 0.0)
        socmin = g("MinSOC") or g("SOCmin")
        if socmin: b["soc_min"] = _to_float(socmin, 0.0)
        socmax = g("MaxSOC") or g("SOCmax")
        if socmax: b["soc_max"] = _to_float(socmax, 0.0)

    _diag(diags, "info", "I-PVST-ADV", "PV and battery advanced fields attached where available")

# ---------------- Validation ----------------
def _validate_links(em: Dict[str, Any], diags: List[Dict[str, Any]]) -> None:
    zones = em.get("geometry", {}).get("zones", [])
    surfaces = em.get("geometry", {}).get("surfaces", [])
    openings = em.get("geometry", {}).get("openings", [])
    wtypes = em.get("catalogs", {}).get("window_types", [])
    ctypes = em.get("catalogs", {}).get("construction_types", [])

    zone_ids = {z.get("id") for z in zones if z.get("id")}
    surf_ids = {s.get("id") for s in surfaces if s.get("id")}
    wtype_ids = {w.get("id") for w in wtypes if w.get("id")}
    ctype_ids = {c.get("id") for c in ctypes if c.get("id")}

    # Surfaces without valid zone
    free_surfs = [s for s in surfaces if not s.get("zone_ref") or s.get("zone_ref") not in zone_ids]
    if free_surfs:
        _diag(diags, "warning", "W-SURF-NOZONE",
              f"Free-floating surfaces (no resolvable zone): {len(free_surfs)}")

    # Surfaces referencing missing construction
    bad_const = [s for s in surfaces if s.get("construction_ref") and s.get("construction_ref") not in ctype_ids]
    if bad_const:
        _diag(diags, "warning", "W-SURF-NOCONST",
              f"Surfaces referencing missing constructions: {len(bad_const)}")

    # Openings linked to missing surfaces or window types
    bad_parent = [o for o in openings if o.get("parent_surface") and o["parent_surface"] not in surf_ids]
    if bad_parent:
        _diag(diags, "warning", "W-OPEN-BADPARENT",
              f"Openings referencing missing parent surfaces: {len(bad_parent)}")

    bad_wtype = [o for o in openings if o.get("window_type_ref") and o["window_type_ref"] not in wtype_ids]
    if bad_wtype:
        _diag(diags, "warning", "W-OPEN-BADTYPE",
              f"Openings referencing missing window types: {len(bad_wtype)}")

# ---------------- Public entry ----------------
def translate_cibd22_to_v6(xml_text: str, validate_flag: bool = False) -> Dict[str, Any]:
    diags: List[Dict[str, Any]] = []
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError as e:
        _diag(diags, "error", "E-XML-PARSE", f"{e}")
        return {"diagnostics": diags}

    project = _parse_project(root, diags)
    zones = _parse_zones(root, diags)
    surfaces = _parse_surfaces(root, diags)
    openings = _parse_openings(root, diags)
    catalogs = _parse_catalogs(root, diags)
    hvac, dhw = _parse_systems(root, diags)
    pv, bat = _parse_pv_storage(root, diags)
    ducts, dhw_dists = _parse_distribution(root, diags)
    infil, vents = _parse_infiltration_ventilation(root, diags)

    em: Dict[str, Any] = {
        "project": project,
        "geometry": {"zones": zones, "surfaces": surfaces, "openings": openings},
        "catalogs": catalogs,
        "energy": {
            "hvac": {"systems": hvac, "ducts": ducts},
            "dhw": {"systems": dhw, "distribution": dhw_dists},
            "pv": {"arrays": pv},
            "storage": {"batteries": bat},
        },
        "diagnostics": diags,
    }

    # Attach infiltration to zones
    if infil:
        by_zone = {}
        for i in infil:
            zr = i.get("zone_ref")
            if not zr:
                continue
            by_zone[zr] = {"ach": i.get("ach"), "cfm": i.get("cfm"),
                           "schedule_ref": i.get("schedule_ref"),
                           "weather_correction": i.get("weather_correction")}
        for z in em["geometry"]["zones"]:
            zid = z.get("id")
            if zid and zid in by_zone:
                z["infiltration"] = by_zone[zid]

    # Attach ventilation: prefer system-level; else zone-level
    if vents:
        hvac_by_id = {s.get("id"): s for s in em["energy"]["hvac"]["systems"] if s.get("id")}
        zone_by_id = {z.get("id"): z for z in em["geometry"]["zones"] if z.get("id")}
        for v in vents:
            sref = v.get("system_ref")
            zref = v.get("zone_ref")
            vent = {
                "min_oa_cfm_per_person": v.get("min_oa_cfm_per_person"),
                "min_oa_cfm_per_area": v.get("min_oa_cfm_per_area"),
                "vent_schedule_ref": v.get("vent_schedule_ref"),
                "economizer_type": v.get("economizer_type"),
                "erv": v.get("erv"),
                "hrv": v.get("hrv"),
                "sens_eff": v.get("sens_eff"),
                "lat_eff": v.get("lat_eff"),
            }
            if sref and sref in hvac_by_id:
                hvac_by_id[sref]["ventilation"] = vent
            elif zref and zref in zone_by_id:
                zone_by_id[zref]["mech_ventilation"] = vent

    # Enrich DHW (HPWH) and PV/Storage advanced
    _enhance_dhw_with_hpwh(em, root, diags)
    _enhance_pv_storage_adv(em, root, diags)

    if validate_flag:
        _validate_links(em, diags)
        _diag(diags, "info", "I-VALIDATE", "Validation complete: basic link checks")

    return em


if __name__ == "__main__":
    import sys, json
    if len(sys.argv) < 2:
        print("Usage: python -m cibd22_rt.translate_cibd22_to_v6 <file.xml>")
        sys.exit(1)
    with open(sys.argv[1], "r", encoding="utf-8") as f:
        xml_text = f.read()
    em = translate_cibd22_to_v6(xml_text, validate_flag=True)
    print(json.dumps(em.get("diagnostics", []), indent=2))
