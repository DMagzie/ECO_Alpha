# explorer_gui/streamlit_app.py
from __future__ import annotations
import os, sys, io, csv, json, zipfile, hashlib
from typing import Any, Dict, List, Tuple, Optional, Iterable
import xml.etree.ElementTree as ET
import streamlit as st

# ---------------- Path bootstrap ----------------
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# ---------------- Translator (v6) ----------------
try:
    from cbecc.translate_cibd22x_to_v6 import translate_cibd22x_to_v6
except Exception:
    # Allow running from repo root or when package import path differs
    sys.path.insert(0, os.path.abspath(os.path.join(PROJECT_ROOT, "cbecc")))
    from translate_cibd22x_to_v6 import translate_cibd22x_to_v6  # type: ignore

# ---------------- Utils ----------------
def _safe_stem(name: Optional[str]) -> str:
    s = (name or "").strip() or "model"
    # Keep alnum, dash, underscore, dot
    return "".join(ch for ch in s if ch.isalnum() or ch in ("-","_",".")) or "model"

def _nget(d: dict, dotted: str, default=None):
    cur = d
    for part in dotted.split("."):
        if not isinstance(cur, dict) or part not in cur:
            return default
        cur = cur[part]
    return cur

def _len_safe(v) -> int:
    try:
        return len(v or [])
    except Exception:
        return 0

def hr() -> None:
    # Prefer Streamlit's divider if available; fallback to markdown rule
    try:
        import streamlit as st
        st.divider()
    except Exception:
        st.markdown("---")

# ---------------- Basic counts ----------------
def counts_from_em(em: dict) -> Dict[str, int]:
    return {
        "zones": _len_safe(_nget(em, "geometry.zones", [])),
        "walls": _len_safe(_nget(em, "geometry.surfaces.walls", [])),
        "roofs": _len_safe(_nget(em, "geometry.surfaces.roofs", [])),
        "floors": _len_safe(_nget(em, "geometry.surfaces.floors", [])),
        "windows": _len_safe(_nget(em, "geometry.openings.windows", [])),
        "doors": _len_safe(_nget(em, "geometry.openings.doors", [])),
        "skylights": _len_safe(_nget(em, "geometry.openings.skylights", [])),
        "hvac_systems": _len_safe(_nget(em, "energy.hvac_systems", [])),
        "iaq_fans": _len_safe(_nget(em, "energy.iaq_fans", [])),
        "dhw_systems": _len_safe(_nget(em, "energy.dhw_systems", [])),
    }

def counts_from_xml(xml_text: str) -> Dict[str, int]:
    try:
        root = ET.fromstring(xml_text)
    except Exception:
        return {}

    def _num(s: Optional[str]) -> float:
        try:
            return float((s or "").strip())
        except Exception:
            return 0.0

    def _area_gt0(node) -> bool:
        area = 0.0
        for t in ("Area", "GrossArea", "NetArea"):
            try:
                area = max(area, _num(node.findtext(t)))
            except Exception:
                pass
        if area > 0:
            return True
        w = _num(node.findtext("Width"))
        h = _num(node.findtext("Height"))
        return (w > 0 and h > 0)

    # Zones (expanded by DwellUnit.Count if present)
    zones = 0
    for rz in root.findall(".//ResZn"):
        du_counts: List[int] = []
        for du in rz.findall("./DwellUnit"):
            try:
                du_counts.append(int(float((du.findtext("Count") or "").strip())))
            except Exception:
                pass
        zones += (sum(du_counts) if du_counts else 1)

    # Walls
    walls = 0
    for tag in (".//ResExtWall", ".//ComExtWall", ".//Wall", ".//ExtWall"):
        for el in root.findall(tag):
            if _area_gt0(el): walls += 1
    if walls == 0:
        for el in root.iter():
            if "wall" in el.tag.lower() and _area_gt0(el): walls += 1

    # Roofs
    roofs = 0
    for tag in (".//ResRoof", ".//ComRoof", ".//Roof", ".//AtticRoof", ".//RoofCeiling", ".//Ceiling"):
        for el in root.findall(tag):
            if _area_gt0(el): roofs += 1
    if roofs == 0:
        for el in root.iter():
            if "roof" in el.tag.lower() and _area_gt0(el): roofs += 1

    # Floors
    floors = 0
    for tag in (".//ResFlr", ".//ComFlr", ".//Flr", ".//Floor", ".//RaisedFloor", ".//ExposedFlr", ".//SlabFlr", ".//Slab", ".//ExtFlr"):
        for el in root.findall(tag):
            if _area_gt0(el): floors += 1
    if floors == 0:
        for el in root.iter():
            if "flr" in el.tag.lower() and _area_gt0(el): floors += 1

    # Windows
    wins = 0
    for tag in ("ResWin", "ComWin", "Window"):
        for el in root.findall(f".//{tag}"):
            def _aval(e: ET.Element) -> float:
                area = 0.0
                for t in ("Area","GrossArea","NetArea"): area = max(area, _num(e.findtext(t)))
                if area > 0: return area
                w = _num(e.findtext("Width")); h = _num(e.findtext("Height"))
                return (w*h) if (w > 0 and h > 0) else 0.0
            if _aval(el) > 0 or (el.findtext("SpecMethod") or "").strip():
                wins += 1

    doors = 0
    for tag in (".//ResDoor", ".//ComDoor", ".//Door"):
        doors += len(root.findall(tag))
    skys = 0
    for tag in (".//ResSky", ".//ComSky", ".//Skylight"):
        skys += len(root.findall(tag))

    # DHW: unique refs
    dhw_refs = set()
    for el in root.findall(".//DHWSysRef"):
        t = (el.text or "").strip()
        if t: dhw_refs.add(t)
    dhw = len(dhw_refs)

    return {
        "zones": zones,
        "walls": walls, "roofs": roofs, "floors": floors,
        "windows": wins, "doors": doors, "skylights": skys,
        "hvac_systems": 0, "iaq_fans": 0, "dhw_systems": dhw,
    }

def _diags_to_csv_bytes(diags: List[dict]) -> bytes:
    mem = io.StringIO()
    wr = csv.writer(mem)
    wr.writerow(["level", "code", "message"])
    for d in (diags or []):
        wr.writerow([d.get("level"), d.get("code"), d.get("message")])
    return mem.getvalue().encode("utf-8")

def _diags_to_ndjson_bytes(diags: List[dict]) -> bytes:
    lines = [json.dumps(d, ensure_ascii=False) for d in (diags or [])]
    return ("\n".join(lines) + ("\n" if lines else "")).encode("utf-8")

def _bundle_zip(diags: List[dict], em: Optional[dict], stem: str, include_em: bool = True) -> bytes:
    mem = io.BytesIO()
    with zipfile.ZipFile(mem, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr(f"{stem}.diagnostics.json", json.dumps(diags or [], ensure_ascii=False, indent=2))
        z.writestr(f"{stem}.diagnostics.csv", _diags_to_csv_bytes(diags))
        z.writestr(f"{stem}.diagnostics.ndjson", _diags_to_ndjson_bytes(diags))
        if include_em and isinstance(em, dict):
            z.writestr(f"{stem}.em.json", json.dumps(em, ensure_ascii=False, indent=2))
    return mem.getvalue()

# ---------------- NEW: CIBD aggregation helpers ----------------
# Normalize tag names → surface category
_SURF_MAP = {
    "rextwall":"wall","comextwall":"wall","wall":"wall","extwall":"wall",
    "resroof":"roof","comroof":"roof","roof":"roof","atticroof":"roof","roofceiling":"roof","ceiling":"roof",
    "resflr":"floor","comflr":"floor","flr":"floor","floor":"floor","raisedfloor":"floor","exposedflr":"floor","slabflr":"floor","slab":"floor","extflr":"floor"
}
_WINDOW_TAGS = {"reswin","comwin","win","window"}
_DOOR_TAGS = {"resdoor","comdoor","door"}
_SKY_TAGS = {"ressky","comsky","skylight"}

def _tagcat(tag: str) -> Optional[str]:
    return _SURF_MAP.get(tag.lower())

def _area_of(node: ET.Element) -> float:
    def _num(s: Optional[str]) -> float:
        try: return float((s or "").strip())
        except Exception: return 0.0
    for t in ("Area", "GrossArea", "NetArea"):
        v = node.findtext(t)
        if v and _num(v) > 0: return _num(v)
    w = _num(node.findtext("Width")); h = _num(node.findtext("Height"))
    return (w*h) if (w>0 and h>0) else 0.0

def _window_area(node: ET.Element) -> float:
    a = _area_of(node)
    if a > 0: return a
    return 0.0

def _text(node: ET.Element, name: str) -> Optional[str]:
    el = node.find(name)
    return (el.text.strip() if (el is not None and el.text) else None)

def _guess_zone_ref(node: ET.Element) -> Optional[str]:
    # Look for common zone-ref child tags
    for k in ("ZnRef","ZoneRef","ResZnRef","ComZnRef","Zone","ZnName"):
        t = _text(node, k)
        if t: return t
    # Sometimes surfaces carry a ZoneRef attribute-like child
    for child in node:
        if child.tag.lower().endswith("znref") and child.text:
            return child.text.strip()
    return None

def _guess_id(node: ET.Element) -> Optional[str]:
    # Prefer Name/ID/UniqueID-ish children
    for k in ("Name","ID","Id","UniqueID","WallID","SurfID"):
        t = _text(node, k)
        if t: return t
    return None

def _attrs_dict(node: ET.Element, exclude: Iterable[str]=()) -> Dict[str, str]:
    ex = {e.lower() for e in exclude}
    out: Dict[str,str] = {}
    for ch in node:
        key = ch.tag
        if key.lower() in ex: continue
        val = (ch.text or "").strip()
        if val != "":
            out[key] = val
    return out

def _freeze_attrs(d: Dict[str,str]) -> str:
    # Build a stable hash key for grouping; skip obvious vars like Name/ID/Area/Width/Height
    filt = {k:v for (k,v) in d.items() if k.lower() not in {"name","id","uniqueid","area","grossarea","netarea","width","height"}}
    items = sorted(filt.items())
    data = json.dumps(items, ensure_ascii=False, separators=(",",":"))
    return hashlib.md5(data.encode("utf-8")).hexdigest()

def aggregate_surfaces_and_windows(xml_text: str) -> Tuple[Dict[str, Any], str]:
    """
    Returns (summary, aggregated_xml_text)
    summary = {
      "zones": {
        "<zone>": {
           "surfaces": [{"category":"wall","attrs":{...},"area":123.4,"count":N,"windows":[{"attrs":{...},"area":45.6,"count":M}, ...]}, ...],
        }, ...
      }
    }
    aggregated_xml_text: original XML + <AggregatedSurfaces>...</AggregatedSurfaces> appended at root
    """
    root = ET.fromstring(xml_text)
    surfaces: List[Tuple[str, str, ET.Element, float, Dict[str,str], str]] = []  # (zone, cat, el, area, attrs, group-id)
    wall_id_to_group: Dict[str,str] = {}

    # 1) Collect surfaces + group by attributes (except Name/ID/Area/Width/Height)
    for el in root.iter():
        cat = _tagcat(el.tag)
        if not cat: continue
        zone = _guess_zone_ref(el) or "UNASSIGNED"
        area = _area_of(el)
        attrs = _attrs_dict(el, exclude=("Area","GrossArea","NetArea","Width","Height"))
        gid = _freeze_attrs(attrs)
        surfaces.append((zone, cat, el, area, attrs, gid))
        if cat == "wall":
            wid = _guess_id(el)
            if wid:
                wall_id_to_group[wid] = gid

    # 2) Collect windows, associate to wall group via WallRef (or best-effort to same zone)
    windows: List[Tuple[str, ET.Element, float, Dict[str,str], str]] = []
    for el in root.iter():
        t = el.tag.lower()
        if t not in _WINDOW_TAGS: continue
        area = _window_area(el)
        attrs = _attrs_dict(el, exclude=("Area","GrossArea","NetArea","Width","Height","WallRef"))
        # Find a wall reference
        wallref = _text(el, "WallRef") or _text(el, "Parent") or _text(el, "WallID")
        gid = None
        if wallref and wallref in wall_id_to_group:
            gid = wall_id_to_group[wallref]
        # fallback: zone guess (less precise)
        zone = _guess_zone_ref(el) or "UNASSIGNED"
        windows.append((zone, el, area, attrs, gid or ""))

    # 3) Aggregate per zone → per surface group key
    zones: Dict[str, Dict[str, Any]] = {}
    # seed zones
    for zname, cat, el, area, attrs, gid in surfaces:
        z = zones.setdefault(zname, {"surfaces": []})
        z["surfaces"].append({"category": cat, "attrs": attrs, "area": area, "count": 1, "windows": []})
    # windows: try to attach to best matching surface group in that zone
    for zname, win, area, attrs, gid in windows:
        z = zones.setdefault(zname, {"surfaces": []})
        # if gid is known, attach to the first matching group in that zone; else keep as loose window entry
        if gid:
            for s in z["surfaces"]:
                if _freeze_attrs(s["attrs"]) == gid:
                    s["windows"].append({"attrs": attrs, "area": area, "count": 1})
                    break

    # 4) Compose <AggregatedSurfaces> XML
    agg = ET.Element("AggregatedSurfaces")
    for zname, zdata in zones.items():
        znode = ET.SubElement(agg, "Zone", attrib={"Name": zname})
        for s in zdata["surfaces"]:
            snode = ET.SubElement(znode, s["category"].capitalize())
            for k, v in (s["attrs"] or {}).items():
                ET.SubElement(snode, k).text = str(v)
            ET.SubElement(snode, "Area").text = str(s.get("area", 0))
            ET.SubElement(snode, "Count").text = str(s.get("count", 1))
            for w in s.get("windows") or []:
                wnode = ET.SubElement(snode, "Window")
                for k, v in (w["attrs"] or {}).items():
                    ET.SubElement(wnode, k).text = str(v)
                ET.SubElement(wnode, "Area").text = str(w.get("area", 0))
                ET.SubElement(wnode, "Count").text = str(w.get("count", 1))
    # Append to original root
    root.append(agg)
    aggregated_xml_text = ET.tostring(root, encoding="unicode")
    return summary, aggregated_xml_text

# ---- Detailed counts helpers (raw vs expanded, per tag/bucket) ----
_TAG_BUCKETS_SURF = {
    "ResExtWall":"wall","ComExtWall":"wall","Wall":"wall","ExtWall":"wall",
    "ResRoof":"roof","ComRoof":"roof","Roof":"roof","AtticRoof":"roof","RoofCeiling":"roof","Ceiling":"roof",
    "ResFlr":"floor","ComFlr":"floor","Flr":"floor","Floor":"floor","RaisedFloor":"floor","ExposedFlr":"floor","SlabFlr":"floor","Slab":"floor","ExtFlr":"floor",
}
_TAG_BUCKETS_OPEN = {
    "ResWin":"window","ComWin":"window","Window":"window",
    "ResDoor":"door","ComDoor":"door","Door":"door",
    "ResSky":"skylight","ComSky":"skylight","Skylight":"skylight",
}

def _xml_zone_multipliers(root: ET.Element) -> Dict[str, int]:
    """Map zone key → effective_multiplier (zone_mult * sum(DwellUnit.Count or 1))."""
    mults: Dict[str,int] = {}
    for rz in root.findall(".//ResZn"):
        key = (_text(rz, "Name") or rz.get("Name") or rz.get("id") or "").strip()
        if not key:
            continue
        try:
            zm = int(float((_text(rz, "ZnMult") or _text(rz, "Mult") or rz.get("Mult") or _text(rz, "Count") or rz.get("Count") or "1").strip()))
        except Exception:
            zm = 1
        du_counts = 0
        for du in rz.findall("./DwellUnit"):
            try:
                du_counts += int(float((_text(du, "Count") or du.get("Count") or "1").strip()))
            except Exception:
                du_counts += 1
        if du_counts == 0:
            du_counts = 1
        mults[key] = max(1, zm * du_counts)
    return mults

def counts_from_xml_detailed(xml_text: str) -> Dict[str, Any]:
    """Return per-tag raw/expanded counts grouped by buckets + totals."""
    try:
        root = ET.fromstring(xml_text)
    except Exception:
        return {}
    zone_mults = _xml_zone_multipliers(root)

    # helper to add
    def add(d, k, raw_inc, exp_inc):
        if k not in d:
            d[k] = {"raw":0, "expanded":0}
        d[k]["raw"] += raw_inc
        d[k]["expanded"] += exp_inc

    buckets: Dict[str, Dict[str, Dict[str,int]]] = {"wall":{}, "roof":{}, "floor":{}}
    openings: Dict[str, Dict[str, Dict[str,int]]] = {"window":{}, "door":{}, "skylight":{}}
    free_floating = 0

    # Surfaces
    for el in root.iter():
        tag = el.tag.split("}",1)[-1]
        bucket = _TAG_BUCKETS_SURF.get(tag)
        if not bucket:
            continue
        zref = _guess_zone_ref(el) or ""
        zm = 1
        if zref:
            zm = zone_mults.get(zref) or zone_mults.get(zref.strip()) or 1
        else:
            free_floating += 1
        add(buckets[bucket], tag, 1, zm)

    # Openings
    for el in root.iter():
        tag = el.tag.split("}",1)[-1]
        b = _TAG_BUCKETS_OPEN.get(tag)
        if not b:
            continue
        zref = _guess_zone_ref(el) or ""
        zm = 1
        if zref:
            zm = zone_mults.get(zref) or zone_mults.get(zref.strip()) or 1
        add(openings[b], tag, 1, zm)

    # Totals per bucket
    bucket_totals = {b: {"raw": sum(v["raw"] for v in tags.values()),
                         "expanded": sum(v["expanded"] for v in tags.values())}
                     for b, tags in buckets.items()}

    return {
        "zones": {
            "raw": len(root.findall(".//ResZn")),
            "expanded": sum(zone_mults.values()) or len(root.findall(".//ResZn")),
        },
        "buckets": buckets,
        "bucket_totals": bucket_totals,
        "openings": openings,
        "free_floating_surfaces": free_floating,
    }

def counts_from_em_detailed(em: dict) -> Dict[str, Any]:
    """Compute raw vs expanded counts per bucket from EM surfaces/openings using zone effective_multiplier."""
    g = em.get("geometry") or {}
    zones = g.get("zones") or []
    z_mult = {}
    for z in zones:
        name = (z.get("name") or z.get("id") or "").strip()
        if not name:
            continue
        eff = int(z.get("effective_multiplier") or 1)
        if eff < 1: eff = 1
        z_mult[name] = eff

    def agg(items: List[dict]) -> Tuple[int,int,int]:
        raw = len(items or [])
        expanded = 0
        free = 0
        for it in (items or []):
            zref = (it.get("parent_zone_ref") or "").strip()
            if not zref:
                free += 1
                zm = 1
            else:
                zm = z_mult.get(zref) or 1
            expanded += zm
        return raw, expanded, free

    walls = (g.get("surfaces") or {}).get("walls") or []
    roofs = (g.get("surfaces") or {}).get("roofs") or []
    floors = (g.get("surfaces") or {}).get("floors") or []
    wins = (g.get("openings") or {}).get("windows") or []
    doors = (g.get("openings") or {}).get("doors") or []
    skys = (g.get("openings") or {}).get("skylights") or []

    w_raw, w_exp, w_free = agg(walls)
    r_raw, r_exp, r_free = agg(roofs)
    f_raw, f_exp, f_free = agg(floors)
    win_raw, win_exp, _ = agg(wins)
    door_raw, door_exp, _ = agg(doors)
    sky_raw, sky_exp, _ = agg(skys)

    return {
        "zones": {
            "raw": len(zones),
            "expanded": sum(z_mult.values()) or len(zones),
        },
        "buckets": {
            "wall": {"raw": w_raw, "expanded": w_exp},
            "roof": {"raw": r_raw, "expanded": r_exp},
            "floor": {"raw": f_raw, "expanded": f_exp},
        },
        "openings": {
            "window": {"raw": win_raw, "expanded": win_exp},
            "door": {"raw": door_raw, "expanded": door_exp},
            "skylight": {"raw": sky_raw, "expanded": sky_exp},
        },
        "free_floating_surfaces": (w_free + r_free + f_free),
    }

# ---------------- Session defaults ----------------
ss = st.session_state
ss.setdefault("em_v6", None)
ss.setdefault("diagnostics", [])
ss.setdefault("active_model_name", None)
ss.setdefault("last_import_xml", None)
ss.setdefault("dev_include_em_zip", True)

# ---------------- Page config ----------------
try:
    st.set_page_config(page_title="EM Tools Explorer", layout="wide")
except Exception:
    pass
st.title("EM Tools Explorer")

# ---------------- Sidebar nav ----------------
page = st.sidebar.radio(
    "Navigate",
    ("Import", "Active Model", "Export", "CIBD Mods", "Developers"),
    index=0,
    key="nav_main",
)

# ========================= IMPORT =========================

# Add button for v6_rt Import
st.subheader('Import EMJSON 6 (Round-Trip)')

v6_rt_file = st.file_uploader('Upload EMJSON 6 Round-Trip File', type=['json'], key='import_v6_rt')

if v6_rt_file:
    with st.spinner('Processing EMJSON 6 import...'):
        em_v6_rt = json.load(v6_rt_file)
    ss['em_v6'] = em_v6_rt
    ss['diagnostics'] = em_v6_rt.get('diagnostics', [])
    st.success('EMJSON 6 imported and active model updated.')


    # ========================= EXPORT =========================
    # Add button for v6_rt Export
    st.subheader('Export EMJSON 6 (Round-Trip)')
    if ss.get('em_v6'):
        export_v6_button = st.download_button(
            label='⬇️ Export EMJSON 6',
            data=json.dumps(ss['em_v6'], ensure_ascii=False, indent=2),
            file_name='exported_v6_rt.em.json',
            mime='application/json'
        )

if page == "Import":
    st.subheader("Import CBECC SDDXML (.xml / .cibd22x / .zip)")

    col1, col2 = st.columns([2, 1])
    with col1:
        up = st.file_uploader("Upload a single file", type=["xml","cibd22x","zip"], accept_multiple_files=False)
    with col2:
        # default is already set via ss.setdefault("dev_include_em_zip", True)
        st.checkbox("Include EM JSON in Zip bundle", key="dev_include_em_zip")
        st.caption("Developers: ZIP will contain diagnostics JSON/CSV/NDJSON; optionally the EM JSON too.")

    if not up:
        st.info("Upload a CBECC SDDXML (.xml / .cibd22x) or a .zip that contains one.")
        st.stop()

    name_stem = os.path.splitext(up.name)[0]

    # Read XML text (direct or zipped)
    xml_text: Optional[str] = None
    if up.type == "application/zip" or up.name.lower().endswith(".zip"):
        try:
            with zipfile.ZipFile(up) as z:
                # pick first file that looks like xml/cibd22x
                for info in z.infolist():
                    if info.filename.lower().endswith((".xml",".cibd22x")):
                        with z.open(info, "r") as f:
                            xml_text = f.read().decode("utf-8", errors="ignore")
                            name_stem = os.path.splitext(os.path.basename(info.filename))[0]
                            break
        except Exception as e:
            st.error(f"Failed to open ZIP: {e}")
            st.stop()
    else:
        try:
            xml_text = up.read().decode("utf-8", errors="ignore")
        except Exception as e:
            st.error(f"Failed to read XML: {e}")
            st.stop()

    if not xml_text:
        st.error("No XML text found in upload.")
        st.stop()

    # Translate to EM v6
    with st.spinner("Translating to EM v6…"):
        em_v6 = translate_cibd22x_to_v6(xml_text)

    # Sticky active model & metadata
    ss["em_v6"] = em_v6 if isinstance(em_v6, dict) else {}
    ss["diagnostics"] = (em_v6.get("diagnostics") if isinstance(em_v6, dict) else []) or []
    ss["active_model_name"] = name_stem
    ss["last_import_xml"] = xml_text
    st.success("Imported with v6 translator. Active model updated.")

    # Quick summary + counts compare
    hr()
    em_counts = counts_from_em(ss["em_v6"])
    xml_counts = counts_from_xml(xml_text)
    st.markdown("**Counts: EM vs XML (quick check)**")
    rows = [
        ("zones", em_counts.get("zones", 0), xml_counts.get("zones", 0)),
        ("walls", em_counts.get("walls", 0), xml_counts.get("walls", 0)),
        ("roofs", em_counts.get("roofs", 0), xml_counts.get("roofs", 0)),
        ("floors", em_counts.get("floors", 0), xml_counts.get("floors", 0)),
        ("windows", em_counts.get("windows", 0), xml_counts.get("windows", 0)),
        ("doors", em_counts.get("doors", 0), xml_counts.get("doors", 0)),
        ("skylights", em_counts.get("skylights", 0), xml_counts.get("skylights", 0)),
        ("dhw_systems", em_counts.get("dhw_systems", 0), xml_counts.get("dhw_systems", 0)),
    ]
    st.table([{"metric": m, "em": a, "xml": b, "delta": a - b} for (m, a, b) in rows])

    # Detailed breakdown
    with st.expander("Per-tag breakdown (raw vs expanded) — unified buckets"):
        xml_det = counts_from_xml_detailed(xml_text)
        em_det = counts_from_em_detailed(ss["em_v6"])
        tabs = st.tabs(["XML tags", "EM buckets"])

        with tabs[0]:
            st.caption("All parsed XML tags grouped into buckets (wall/roof/floor + openings).")
            # Build a combined table of tag rows
            table_rows = []
            # surfaces
            for bucket, tags in (xml_det.get("buckets") or {}).items():
                for tag, vals in (tags or {}).items():
                    table_rows.append({
                        "bucket": bucket, "tag": tag,
                        "xml_raw": vals.get("raw", 0),
                        "xml_expanded": vals.get("expanded", 0),
                    })
            # openings
            for bucket, tags in (xml_det.get("openings") or {}).items():
                for tag, vals in (tags or {}).items():
                    table_rows.append({
                        "bucket": bucket, "tag": tag,
                        "xml_raw": vals.get("raw", 0),
                        "xml_expanded": vals.get("expanded", 0),
                    })
            if table_rows:
                st.dataframe(table_rows, use_container_width=True)
            st.write({
                "zones_raw": (xml_det.get("zones") or {}).get("raw", 0),
                "zones_expanded": (xml_det.get("zones") or {}).get("expanded", 0),
            })
            if xml_det.get("free_floating_surfaces"):
                st.warning(f"Free-floating surfaces found in XML (no resolvable zone): {xml_det['free_floating_surfaces']}")

        with tabs[1]:
            st.caption("EM counts by bucket (raw entries vs multiplied by effective zone multipliers).")
            em_rows = []
            for bucket, vals in (em_det.get("buckets") or {}).items():
                em_rows.append({"bucket": bucket, "em_raw": vals.get("raw",0), "em_expanded": vals.get("expanded",0)})
            # openings
            for bucket, vals in (em_det.get("openings") or {}).items():
                em_rows.append({"bucket": bucket, "em_raw": vals.get("raw",0), "em_expanded": vals.get("expanded",0)})
            if em_rows:
                st.table(em_rows)
            st.write({
                "zones_raw": (em_det.get("zones") or {}).get("raw", 0),
                "zones_expanded": (em_det.get("zones") or {}).get("expanded", 0),
            })
            if em_det.get("free_floating_surfaces"):
                st.error(f"EM contains {em_det['free_floating_surfaces']} surfaces without parent_zone_ref. Surfaces must always be in a zone.")

    with st.expander("Diagnostics"):
        try:
            st.code(json.dumps(ss.get("diagnostics", []), indent=2), language="json")
        except Exception:
            st.write("(diagnostics unavailable)")

# ========================= ACTIVE MODEL =========================
elif page == "Active Model":
    st.subheader("Active Model")
    em = ss.get("em_v6")
    if not isinstance(em, dict) or not em:
        st.info("No active model yet — go to **Import** and load a file.")
        st.stop()

    ct = counts_from_em(em)
    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric("Zones", ct.get("zones", 0))
        st.metric("DHW Systems", ct.get("dhw_systems", 0))
    with c2:
        st.metric("Openings", ct.get("windows", 0) + ct.get("doors", 0) + ct.get("skylights", 0))
        st.metric("Walls", ct.get("walls", 0))
    with c3:
        st.metric("Roofs", ct.get("roofs", 0))
        st.metric("Floors", ct.get("floors", 0))

    hr()
    with st.expander("Download EMJSON"):
        em_bytes = json.dumps(em, ensure_ascii=False, indent=2).encode("utf-8")
        st.download_button(
            f"⬇️ {_safe_stem(ss.get('active_model_name'))}.em.json",
            data=em_bytes,
            file_name=f"{_safe_stem(ss.get('active_model_name'))}.em.json",
            mime="application/json",
        )

    with st.expander("Show EMJSON (pretty)"):
        try:
            st.json(em, expanded=False)
        except Exception:
            st.code(json.dumps(em, ensure_ascii=False, indent=2))

# ========================= EXPORT =========================
elif page == "Export":
    st.subheader("Export")
    em = ss.get("em_v6")
    if not isinstance(em, dict) or not em:
        st.info("No active model yet — go to **Import** and load a file.")
        st.stop()

    stem = _safe_stem(ss.get("active_model_name"))
    diags = ss.get("diagnostics") or []

    # EM JSON
    em_bytes = json.dumps(em, ensure_ascii=False, indent=2).encode("utf-8")
    st.download_button(f"⬇️ {stem}.em.json", data=em_bytes, file_name=f"{stem}.em.json", mime="application/json")

    # Diagnostics JSON/CSV/NDJSON & Bundle
    json_bytes   = json.dumps(diags, ensure_ascii=False, indent=2).encode("utf-8")
    csv_bytes    = _diags_to_csv_bytes(diags)
    ndjson_bytes = _diags_to_ndjson_bytes(diags)
    zip_bytes    = _bundle_zip(diags, em if ss.get("dev_include_em_zip", True) else None, stem, include_em=ss.get("dev_include_em_zip", True))

    cA, cB, cC, cD = st.columns(4)
    with cA:
        st.download_button("⬇️ diagnostics.json", data=json_bytes, file_name=f"{stem}.diagnostics.json", mime="application/json")
    with cB:
        st.download_button("⬇️ diagnostics.csv", data=csv_bytes, file_name=f"{stem}.diagnostics.csv", mime="text/csv")
    with cC:
        st.download_button("⬇️ diagnostics.ndjson", data=ndjson_bytes, file_name=f"{stem}.diagnostics.ndjson", mime="application/x-ndjson")
    with cD:
        st.download_button("⬇️ bundle.zip", data=zip_bytes, file_name=f"{stem}.zip", mime="application/zip")

    hr()
    st.subheader("XML tools")

    xml_text = ss.get("last_import_xml")
    if not xml_text:
        st.info("No source XML stored from Import step.")
        st.stop()

    with st.expander("Preview source XML (lazy)"):
        if not isinstance(xml_text, str):
            st.write("(missing xml text)")
        else:
            total_kb = max(1, len(xml_text) // 1024)
            default_kb = min(256, total_kb)  # 256 KB default preview
            max_kb = min(4096, total_kb)  # hard-cap 4 MB
            colA, colB = st.columns([2, 1])
            with colA:
                offset_kb = st.slider("Start offset (KB)", 0, total_kb, 0, step=64, key="cibd_xml_offset_kb")
            with colB:
                size_kb = st.slider("Preview size (KB)", 16, max_kb, default_kb, step=16, key="cibd_xml_size_kb")
            start = offset_kb * 1024
            end = min(len(xml_text), start + size_kb * 1024)
            st.caption(f"Showing {size_kb} KB at offset {offset_kb} KB (bytes {start:,}–{end:,} of {len(xml_text):,})")
            st.code(xml_text[start:end], language="xml")

        st.markdown("---")

    # --- section browser (collapsible) ---
    st.markdown("**Browse by section (collapsible groups)**")
    browse_on = st.checkbox("Enable section browser (parses XML lazily)", key="cibd_xml_sections_on")
    if browse_on:
        import xml.etree.ElementTree as ET

        # helpers local to this viewer (to keep scope tidy)
        def _local_tag(tag: str) -> str:
            return tag.split("}", 1)[-1] if "}" in tag else tag

        def _label_for(el: ET.Element) -> str:
            # choose something human-readable
            for k in ("Name", "ID", "Id", "UniqueID", "WallID", "SurfID"):
                child = el.find(k)
                if child is not None and child.text:
                    return f"[{_local_tag(el.tag)}] {k}={child.text.strip()}"
            return f"[{_local_tag(el.tag)}]"

        # listing toggles
        cols = st.columns([1,1,1,1,1,1])
        enabled = {
            "ResZn": cols[0].checkbox("ResZn", value=True),
            "ResOtherZn": cols[1].checkbox("ResOtherZn", value=False),
            "ResExtWall": cols[2].checkbox("ResExtWall", value=True),
            "ResRoof": cols[3].checkbox("ResRoof", value=True),
            "ResSlabFlr": cols[4].checkbox("ResSlabFlr", value=False),
            "ResRaisedFlr": cols[5].checkbox("ResRaisedFlr", value=False),
        }
        child_filter = st.text_input("Filter by text inside child elements (optional)")

        # parse root lazily
        try:
            _root = ET.fromstring(xml_text)
        except Exception as e:
            st.error(f"XML parse failed: {e}")
            st.stop()

        shown = 0
        for tag, on in enabled.items():
            if not on:
                continue
            with st.expander(f"{tag}"):
                idx = 0
                for el in _root.findall(f".//{tag}"):
                    idx += 1
                    # produce a short snippet
                    txt = ET.tostring(el, encoding="unicode")
                    if child_filter and child_filter.lower() not in txt.lower():
                        continue
                    # PER-ITEM toggle (NO nested expander)
                    show = st.checkbox(
                        f"Show {_label_for(el)}",
                        key=f"cibd_xml_show_{tag}_{idx}",
                        help="Toggle to reveal this item's XML snippet"
                    )
                    if show:
                        st.code(txt, language="xml")
                    shown += 1

    # --- Zone contents (collapsible; drop-in, no nested expanders) ---
    st.markdown("**Zone contents (collapsible)**")
    if st.checkbox("Enable zone contents viewer (parses XML lazily)", key="cibd_zone_view_on"):
        try:
            _root = ET.fromstring(xml_text)
        except Exception as e:
            st.error(f"XML parse failed: {e}")
        else:
            # local helpers (scoped)
            from typing import Optional, Dict, Any, List

            def _lt(tag: str) -> str:
                return tag.split("}", 1)[-1] if "}" in tag else tag

            def _txt(el: ET.Element, name: str) -> Optional[str]:
                c = el.find(name)
                if c is not None and c.text:
                    return c.text.strip()
                return None

            def _norm(s: str) -> str:
                return (s or "").strip().lower()

            def _zone_from_ancestors(node: ET.Element) -> Optional[str]:
                p = node
                # Walk up few levels to find a zone-ish element
                for _ in range(4):
                    p = p.getparent() if hasattr(p, "getparent") else None  # type: ignore
                    if p is None:
                        break
                    t = _lt(p.tag).lower()
                    if t in {"reszn", "comzn", "zone"}:
                        return _txt(p, "Name") or p.get("Name") or p.get("id")
                return None

            # 1) Build index mapping (normalized) names → canonical key
            names = set()
            for el in _root.findall(".//ResZn"):
                n = _txt(el, "Name") or el.get("Name") or el.get("id")
                if n: names.add(n)
            norm_to_key = {_norm(n): n for n in names}

            # 2) Collect zones + seed structure
            zmap: Dict[str, Dict[str, Any]] = {}
            for k in sorted(names):
                zmap[k] = {"surfaces": [], "windows": [], "doors": [], "skylights": []}

            # 3) First pass: bind surfaces to zones and index walls
            wall_to_zone: Dict[str, str] = {}
            for el in _root.iter():
                lt = _lt(el.tag).lower()
                cat = _tagcat(_lt(el.tag))
                if not cat:
                    continue
                zref = _guess_zone_ref(el) or _zone_from_ancestors(el) or ""
                zmatch = norm_to_key.get(_norm(zref))
                if not zmatch:
                    # fuzzy contains
                    nz = _norm(zref)
                    for n, k in norm_to_key.items():
                        if nz in n or n in nz:
                            zmatch = k; break
                if not zmatch:
                    continue
                rec = {
                    "id": (_txt(el, "Name") or _txt(el, "ID") or _txt(el, "UniqueID") or _txt(el, "WallID") or _txt(el, "SurfID") or "").strip(),
                    "tag": _lt(el.tag),
                    "area": round(_area_of(el), 3),
                }
                zmap[zmatch]["surfaces"].append(rec)

                if cat == "wall":
                    for wid in filter(None, [rec["id"], _txt(el, "Name"), _txt(el, "ID"), _txt(el, "UniqueID"),
                                             _txt(el, "WallID"), _txt(el, "SurfID")]):
                        wall_to_zone[wid.strip()] = zmatch
                        wall_to_zone[_norm(wid)] = zmatch  # normalized fallback

            # pass 2: map windows/doors/skylights to zones
            for el in _root.iter():
                lt = _lt(el.tag).lower()
                if lt in _WINDOW_TAGS:
                    wallref = (_txt(el, "WallRef") or _txt(el, "Parent") or _txt(el, "WallID") or "").strip()
                    zmatch = wall_to_zone.get(wallref) or wall_to_zone.get(_norm(wallref))
                    if not zmatch:
                        zref = _guess_zone_ref(el) or _zone_from_ancestors(el) or ""
                        nz = _norm(zref)
                        zmatch = norm_to_key.get(nz)
                        if not zmatch:
                            for n, k in norm_to_key.items():
                                if nz in n or n in nz:
                                    zmatch = k;
                                    break
                    if zmatch:
                        zmap[zmatch]["windows"].append({
                            "area": round(_window_area(el), 3),
                            "tag": _lt(el.tag),
                        })
                elif lt in {"resdoor","comdoor","door"}:
                    zref = _guess_zone_ref(el) or _zone_from_ancestors(el) or ""
                    nz = _norm(zref)
                    zmatch = norm_to_key.get(nz)
                    if zmatch:
                        zmap[zmatch]["doors"].append({"tag": _lt(el.tag)})
                elif lt in {"ressky","comsky","skylight"}:
                    zref = _guess_zone_ref(el) or _zone_from_ancestors(el) or ""
                    nz = _norm(zref)
                    zmatch = norm_to_key.get(nz)
                    if zmatch:
                        zmap[zmatch]["skylights"].append({"tag": _lt(el.tag)})

            # render
            zsel = st.selectbox("Select a zone", sorted(zmap.keys()))
            if zsel:
                zdata = zmap[zsel]
                a,b,c = st.columns(3)
                with a:
                    st.caption("Surfaces")
                    st.table(zdata["surfaces"] or [])
                with b:
                    st.caption("Windows")
                    st.table(zdata["windows"] or [])
                with c:
                    st.caption("Doors")
                    st.table(zdata["doors"] or [])
                cb = st.container()
                with cb:
                    st.caption("Skylights");
                    st.table(zdata["skylights"] or [])

            # optional raw XML slice for the selected zone (lazy + truncated)
            if st.checkbox("Show raw XML for selected zone (lazy)", value=False, key="zv_show_raw"):
                max_chars = st.slider("Max chars", 1000, 20000, 6000, step=500, key="zv_raw_max")
                snippets: List[str] = []
                sel_norm = _norm(zsel)
                for el in _root.iter():
                    lt = _lt(el.tag).lower()
                    if (_tagcat(_lt(el.tag)) or lt in _WINDOW_TAGS or lt in _DOOR_TAGS or lt in _SKY_TAGS):
                        zref = _guess_zone_ref(el) or _zone_from_ancestors(el) or ""
                        nz = _norm(zref)
                        if nz and (nz == sel_norm or sel_norm in nz or nz in sel_norm):
                            try:
                                s = ET.tostring(el, encoding="unicode")
                            except Exception:
                                s = "<failed>"
                            snippets.append(s)
                blob = "\n".join(snippets)
                if len(blob) > max_chars:
                    blob = blob[:max_chars] + "\n<!-- …truncated… -->"
                st.code(blob, language="xml")

    # b) Aggregate button
    if st.button("Aggregate surfaces + windows (per zone)"):
        try:
            summary, agg_xml = aggregate_surfaces_and_windows(xml_text)
            st.success("Aggregated surfaces/windows by zone.")
        except Exception as e:
            st.error(f"Aggregation failed: {e}")
            agg_xml = None
            summary = {}

        if agg_xml:
            st.download_button(
                "⬇️ aggregated.xml",
                data=agg_xml.encode("utf-8"),
                file_name=f"{stem}.aggregated.xml",
                mime="application/xml",
            )

    st.caption("Note: current write mode is non-destructive; aggregator appends. We can flip to replacement once we lock reference rules (IDs/refs).")

# ========================= DEVELOPERS (blank scaffold) =========================
else:
    st.subheader("Developers")
    st.info("This tab is intentionally blank for future dev tooling (schema coverage, audits, etc.).")
    st.write({
        "active_model_name": ss.get("active_model_name"),
        "diagnostics_count": len(ss.get("diagnostics") or []),
        "xml_loaded": bool(ss.get("last_import_xml")),
    })
