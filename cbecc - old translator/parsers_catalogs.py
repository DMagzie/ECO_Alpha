from __future__ import annotations
from typing import Any, Dict, List, Tuple, Optional
from xml.etree import ElementTree as ET

try:
    from .mapping_cleanup import diag, mark_used
except ImportError:
    from cbecc.mapping_cleanup import diag, mark_used

def _txt(n):
    return (n.text or "").strip() if n is not None and n.text is not None else ""

def _child(p, tag: str):
    return p.find(tag) if p is not None else None

def _child_txt(p, tag: str) -> str:
    return _txt(_child(p, tag))

def _float(s: str | None):
    if not s:
        return None
    s = s.strip()
    if not s:
        return None
    try:
        return float(s.replace(",", ""))
    except Exception:
        return None

def _pc_safe_txt(node: Optional[ET.Element], tag: str, default: Optional[str] = None) -> Optional[str]:
    if node is None:
        return default
    found = node.find(tag)
    return (found.text.strip() if (found is not None and found.text is not None) else default)

def _pc_attr(node: Optional[ET.Element], name: str, default: Optional[str] = None) -> Optional[str]:
    return node.get(name) if (node is not None and name in node.attrib) else default

def _pc_make_id(prefix: str, *parts: str) -> str:
    norm = "-".join([str(p).strip().replace(" ", "_") for p in parts if p is not None and str(p).strip() != ""])
    return f"{prefix}:{norm}" if norm else prefix

# ---------------- Detailed constructions & materials ----------------
def parse_constructions_detailed(root: ET.Element, em: Dict[str, Any], diags: Optional[List[Dict[str, Any]]] = None) -> None:
    if diags is None:
        diags = em.setdefault("diagnostics", [])
    catalogs = em.setdefault("catalogs", {})
    cons_out: List[Dict[str, Any]] = catalogs.setdefault("constructions_detailed", [])
    mats_out: List[Dict[str, Any]] = catalogs.setdefault("materials", [])
    material_index: Dict[str, Dict[str, Any]] = { m.get("id"): m for m in mats_out if isinstance(m, dict) and m.get("id") }

    added_cons = 0; added_mats = 0
    for assm in root.findall(".//ResConsAssm"):
        cname = _pc_safe_txt(assm, "Name") or _pc_attr(assm, "name") or "Construction"
        cid = _pc_make_id("construction", cname)
        u_val = _pc_safe_txt(assm, "UValue")
        r_val = _pc_safe_txt(assm, "RValue")
        layers_out: List[Dict[str, Any]] = []
        for i, lay in enumerate(assm.findall(".//ResLay")):
            order = _pc_safe_txt(lay, "Order") or str(i + 1)
            thick = _pc_safe_txt(lay, "Thickness")
            r_lay = _pc_safe_txt(lay, "RValue")
            mnode = lay.find("ResMat")
            mref = None if mnode is not None else (_pc_safe_txt(lay, "ResMatRef") or _pc_attr(lay, "ResMatRef"))
            mat_id = None
            if mnode is not None:
                mname = _pc_safe_txt(mnode, "Name") or _pc_attr(mnode, "name") or f"Material_{cid}_{order}"
                mat_id = _pc_make_id("material", mname)
                if mat_id not in material_index:
                    props_raw = {}
                    for c in list(mnode):
                        if c.tag and c.text:
                            props_raw[c.tag] = c.text.strip()
                    material = {"id": mat_id, "name": mname, "props": {}, "raw": props_raw}
                    for k in ("Conductivity", "Density", "SpecHeat", "Emissivity"):
                        val = props_raw.get(k)
                        if val:
                            try:
                                material["props"][k] = float(val)
                            except ValueError:
                                material["props"][f"{k}_raw"] = val
                    mats_out.append(material)
                    material_index[mat_id] = material
                    added_mats += 1
            elif mref:
                mat_id = _pc_make_id("materialref", mref)

            layer_entry: Dict[str, Any] = {
                "order": int(order) if str(order).isdigit() else order,
                "thickness_m": None,
                "r_value_m2K_W": None,
                "material_ref": mat_id,
                "raw": {}
            }
            if thick:
                try: layer_entry["thickness_m"] = float(thick)
                except ValueError: layer_entry["raw"]["Thickness"] = thick
            if r_lay:
                try: layer_entry["r_value_m2K_W"] = float(r_lay)
                except ValueError: layer_entry["raw"]["RValue"] = r_lay
            for c in list(lay):
                if c.tag and c.text:
                    layer_entry["raw"][c.tag] = c.text.strip()
            layers_out.append(layer_entry)

        cons_entry: Dict[str, Any] = {"id": cid, "name": cname, "layers": layers_out, "raw": {}}
        if u_val:
            try: cons_entry["u_value_W_m2K"] = float(u_val)
            except ValueError: cons_entry["raw"]["UValue"] = u_val
        if r_val:
            try: cons_entry["r_value_m2K_W"] = float(r_val)
            except ValueError: cons_entry["raw"]["RValue"] = r_val
        for c in list(assm):
            if c.tag and c.text:
                cons_entry["raw"][c.tag] = c.text.strip()
        cons_out.append(cons_entry); added_cons += 1

    diags.append({"level": "info","code": "I-CONSTRUCTIONS-DETAIL",
                  "message": f"Parsed detailed constructions: {added_cons}, materials added: {added_mats}",
                  "context": {"constructions_added": added_cons, "materials_added": added_mats}})

# ---------------- Project / Run / Standard Design / PV ----------------
def parse_project_extras(root: ET.Element, em: Dict[str, Any]) -> List[Dict[str, Any]]:
    diags: List[Dict[str, Any]] = []
    model_info = {}
    for tag in ("BldgEngyModelVersion", "GeometryInpType"):
        node = root.find(f".//{tag}")
        if node is not None and _txt(node):
            model_info[tag] = _txt(node); mark_used(tag)
    if model_info:
        em["project"].setdefault("model_info", {}).update(model_info)
        diags.append(diag("info", "I-MAP-PROJ-INFO", f"project.model_info keys={list(model_info.keys())}"))

    run_fields = {}
    for tag in ("RunTitle", "RunDate", "SoftwareVersion", "ResultsCurrentMessage", "SimSummary", "StdPVBatteryMsg"):
        node = root.find(f".//{tag}")
        if node is not None and _txt(node):
            run_fields[tag] = _txt(node); mark_used(tag)
    if run_fields:
        em["project"]["run"] = run_fields
        diags.append(diag("info", "I-MAP-RUN", f"project.run fields={list(run_fields.keys())}"))

    std = {}
    std_tags = [
        "StdDesignCompactDistrib", "StdDesignDrnWtrHtRecov", "StdDesignFuel_Ckg",
        "StdDesignFuel_DHW", "StdDesignFuel_Dry", "StdDesignHPWHLocOverride",
        "StdDesignIAQFanPwr", "StdDesignWinPerfAdjust", "StdPV_Export",
        "StdPV_PctExport", "StdPV_Total",
    ]
    for tag in std_tags:
        node = root.find(f".//{tag}")
        if node is not None and _txt(node):
            std[tag] = _txt(node); mark_used(tag)
    if std:
        em["project"]["standard_design"] = std
        diags.append(diag("info", "I-MAP-STD", f"project.standard_design fields={list(std.keys())}"))

    pv = {}
    for tag in ["PropPV_Export", "PropPV_PctExport", "PropPV_Total"]:
        node = root.find(f".//{tag}")
        if node is not None and _txt(node):
            pv[tag] = _txt(node); mark_used(tag)
    if pv:
        em.setdefault("energy", {}).setdefault("pv_battery", {})["fields"] = pv
        diags.append(diag("info", "I-MAP-PV", "energy.pv_battery keys=['fields']"))
    return diags

# ---------------- DU / Window / Constructions (minimal types) ----------------
def parse_du_types(root: ET.Element) -> Tuple[Dict[str, Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]]]:
    du_nodes = (root.findall(".//DwellUnitType") or root.findall(".//DUTypes/DUType") or root.findall(".//DUType"))
    idx: Dict[str, Dict[str, Any]] = {}; out: List[Dict[str, Any]] = []; captures: List[str] = []
    for n in du_nodes:
        name = (_child_txt(n, "Name") or n.get("name") or _txt(n)).strip()
        if not name: continue
        leafs: Dict[str, str] = {c.tag: _txt(c) for c in list(n) if len(list(c)) == 0}
        fa = leafs.get("CondFlrArea") or leafs.get("FloorArea") or leafs.get("Area")
        rec = {
            "name": name,
            "floor_area": _float(fa),
            "bedrooms": _float(leafs.get("Bedrooms") or leafs.get("Beds")),
            "bathrooms": _float(leafs.get("Bathrooms") or leafs.get("Baths") or leafs.get("Ba")),
            "occupants": _float(leafs.get("Occupants")),
        }
        rec = {k: v for k, v in rec.items() if v not in (None, "", [], {})}
        attrs = {k: v for k, v in leafs.items() if k not in ("Name","CondFlrArea","FloorArea","Area","Bedrooms","Beds","Bathrooms","Baths","Ba","Occupants")}
        if attrs: rec["attributes"] = attrs
        idx[name.lower()] = rec; out.append(rec); captures.append(f"{name}: fields={len(rec)-1}, sections={{}}")
        mark_used("DUType","DwellUnitType","DUTypes")
    diags = [diag("info","I-DU-INDEX", f"DU types indexed: {len(idx)}")]
    if captures:
        diags.append(diag("info","I-DU-FIELDS", "; ".join(captures)))
        diags.append(diag("info","I-DU-LIST", f"DU types: {', '.join(d['name'] for d in out)}"))
    return idx, out, diags

def parse_window_types(root: ET.Element, em: Dict[str, Any]) -> List[Dict[str, Any]]:
    wt = []
    for n in root.findall(".//ResWinType"):
        rec = {
            "name": _child_txt(n, "Name") or n.get("name"),
            "u": _float(_child_txt(n, "NFRCUfactor") or _child_txt(n, "UFactor") or _child_txt(n, "U")),
            "shgc": _float(_child_txt(n, "SHGC") or _child_txt(n, "SolarHeatGainCoeff")),
            "vt": _float(_child_txt(n, "VT") or _child_txt(n, "VisibleTrans")),
        }
        rec = {k: v for k, v in rec.items() if v not in (None, "", [], {})}
        wt.append(rec)
        mark_used("ResWinType","Name","U","UFactor","NFRCUfactor","SHGC","SolarHeatGainCoeff","VT","VisibleTrans")

    if wt:
        # canonical key by optics tuple to reduce near-duplicates
        seen = set(); deduped: List[Dict[str, Any]] = []
        for w in wt:
            key = (w.get("u"), w.get("shgc"), w.get("vt"))
            if key in seen:
                continue
            seen.add(key); deduped.append(w)
        em["catalogs"]["window_types"] = [w for w in deduped if w.get("name")]
        return []
    # Fallback to WinType flat names
    names = {(_txt(n) or "").strip() for n in root.findall(".//WinType") if (_txt(n) or "").strip()}
    em["catalogs"]["window_types"] = [{"name": nm, "u": None, "shgc": None, "vt": None} for nm in sorted(names)]
    return [diag("info", "I-CAT-WIN-FALLBACK", f"Using dedup of WinType refs ({len(names)} unique).")]

def parse_construction_types(root: ET.Element, em: Dict[str, Any]) -> List[Dict[str, Any]]:
    out = []
    for a in root.findall(".//ResConsAssm"):
        rec = {"name": _child_txt(a, "Name") or "", "raw_fields": {}}
        for c in list(a):
            if len(list(c)) == 0:
                rec["raw_fields"][c.tag] = _txt(c)
        if rec["name"]:
            out.append(rec)
        mark_used("ResConsAssm","Name")
    em["catalogs"]["construction_types"] = out
    return [diag("info", "I-CONS-MIN", f"construction_types parsed={len(out)}")]
