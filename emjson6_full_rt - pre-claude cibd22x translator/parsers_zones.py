from __future__ import annotations
from typing import Dict, Any, List, Optional, Tuple
from xml.etree import ElementTree as ET
from mapping_cleanup import SURFACE_BUCKETS

# -------------------- helpers (namespace-agnostic) --------------------
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

def _first_child_local(node: ET.Element | None, *names: str) -> ET.Element | None:
    if node is None:
        return None
    wanted = {n.lower() for n in names}
    for ch in list(node):
        if _lt(getattr(ch, "tag", "")).lower() in wanted:
            return ch
    return None

def _zone_key(zn: ET.Element) -> str:
    # prefer element text children first, then attributes
    name = (_child_text_local(zn, "Name", "ZnName", "ZoneName", "ID", "Id")
            or zn.get("Name") or zn.get("id") or "")
    return name.strip()

def _slug(s: str) -> str:
    import re
    s = (s or "").strip().lower()
    s = re.sub(r"[^a-z0-9]+","-", s).strip("-")
    return s or "zone"

def _diag(em: Dict[str, Any], level: str, code: str, message: str, context: Dict[str, Any] | None = None):
    em.setdefault("diagnostics", []).append({
        "level": level, "code": code, "message": message, "context": context or {}
    })

# -------------------- zones (ResZn + ComZn) --------------------
def parse_zones(
    root: ET.Element,
    em: Dict[str, Any],
    du_index: Dict[str, Dict[str, Any]] | None = None,
    zone_to_group: Dict[str, str] | None = None
) -> List[Dict[str, Any]]:
    """
    Build em['geometry']['zones'] from both ResZn and ComZn.
    - Namespace agnostic element/field reads
    - Records zone_multiplier, du_count_in_zone, and effective_multiplier
    - Multiplier metadata includes flat_path for round-tripping
    """
    du_index = du_index or {}
    zone_to_group = zone_to_group or {}
    zones: List[Dict[str, Any]] = []
    geom = em.setdefault("geometry", {})
    geom["zones"] = zones

    def _to_float(s: str | None) -> float | None:
        if not s: return None
        try: return float(str(s).replace(",","").strip())
        except Exception: return None

    def _read_zone_multiplier(zn: ET.Element) -> int:
        raw = (_child_text_local(zn, "ZnMult") or _child_text_local(zn, "Mult") or _child_text_local(zn,"Count")
               or zn.get("ZnMult") or zn.get("Mult") or zn.get("Count"))
        try: return int(float(raw)) if raw not in (None,"") else 1
        except Exception: return 1

    def _read_du_count(zn: ET.Element) -> int:
        du = _first_child_local(zn, "DwellUnit","DU","Unit")
        raw = (_child_text_local(du, "Count") or (du.get("Count") if du is not None else None) or "1")
        try: return int(float(raw))
        except Exception: return 1

    def _du_ref_from_zone(zn: ET.Element) -> str | None:
        ref = (_child_text_local(zn, "DUTypeRef")
               or _child_text_local(_first_child_local(zn,"DwellUnit"), "DwellUnitTypeRef")
               or zn.get("DUTypeRef"))
        if ref:
            key = ref.strip().lower()
            if key in du_index: return du_index[key]["name"]
        # heuristic fallback by zone name
        zname = _zone_key(zn)
        if zname:
            token = zname.split("_",1)[0].strip()
            guess = f"unit {token}".lower()
            if guess in du_index: return du_index[guess]["name"]
        return None

    have_area = 0
    for zn in (el for el in root.iter() if _lt(el.tag) in ("ResZn","ComZn")):
        zname = _zone_key(zn)
        if not zname:
            continue
        zid = (zn.get("id") or None) or f"zone:{_slug(zname)}"
        # areas (if present)
        zfa = _to_float(_child_text_local(zn,"FloorArea") or _child_text_local(zn,"ZnFlrArea")
                        or _child_text_local(zn,"Area") or _child_text_local(zn,"GrossArea")
                        or zn.get("FloorArea") or zn.get("ZnFlrArea") or zn.get("Area") or zn.get("GrossArea"))
        if zfa is not None: have_area += 1
        z_mult = _read_zone_multiplier(zn)
        du_cnt = _read_du_count(zn) if _lt(zn.tag) == "ResZn" else 1
        eff_mult = int(z_mult) * int(du_cnt)
        du_ref = _du_ref_from_zone(zn) if _lt(zn.tag) == "ResZn" else None
        level_ref = (zone_to_group or {}).get(zname) or None

        tag_prefix = "ResZn" if _lt(zn.tag) == "ResZn" else "ComZn"
        mult_meta = {
            "effective": eff_mult,
            "factors": [
                {"name":"du_count_in_zone","value":du_cnt,"flat_path":f"{tag_prefix}/DwellUnit/Count"} if tag_prefix=="ResZn" else None,
                {"name":"zone_multiplier","value":z_mult,"flat_path":f"{tag_prefix}/ZnMult|Mult|Count"},
            ],
            "base_quantity": 1,
            "applies_to": ["counts","areas"],
        }
        mult_meta["factors"] = [f for f in mult_meta["factors"] if f is not None]

        zones.append({
            "id": zid,
            "name": zname,
            "type": "conditioned",
            "level_ref": level_ref,
            "floor_area": zfa,
            "du_type_ref": du_ref,
            "zone_multiplier": int(z_mult),
            "du_count_in_zone": int(du_cnt),
            "effective_multiplier": int(eff_mult),
            "multiplier": mult_meta,
        })

    _diag(em, "info", "I-ZONES-AREA-COVERAGE", f"{have_area}/{len(zones)} zones have floor_area")
    return zones

# -------------------- surfaces --------------------
def _extract_surface(n: ET.Element, category: str, subtype: str,
                     parent_zone_ref: Optional[str], zone_mults: Dict[str, int]) -> Dict[str, Any]:
    name = (_child_text_local(n, "Name") or n.get("Name") or n.get("id") or f"{category}:{subtype}")
    ar = (_child_text_local(n,"Area") or n.get("Area"))
    try:
        area = float(ar) if ar else None
    except Exception:
        area = None
    bc = "outdoor"
    if subtype.lower().startswith("party"):
        bc = "party"
    elif subtype.lower().startswith(("int","interior")):
        bc = "interior_or_adiabatic"

    eff_mult = int(zone_mults.get(parent_zone_ref or "", 1))
    payload: Dict[str, Any] = {
        "id": f"surf:{subtype}:{name}".lower().replace(" ","_"),
        "name": name,
        "category": category,
        "subtype": subtype,
        "boundary_condition": bc,
        "parent_zone_ref": parent_zone_ref,
        "area_ft2": area,
        "multiplier": {
            "effective": eff_mult,
            "factors": [{"name":"zone_multiplier","value":eff_mult,"flat_path":"ResZn/ZnMult|Mult|Count"}],
            "base_quantity": 1,
            "applies_to": ["areas"]
        }
    }
    if area is not None and eff_mult > 1:
        payload["effective_area_ft2"] = area * eff_mult
    return payload

def parse_surfaces(root: ET.Element, em: Dict[str, Any]) -> List[Dict[str, Any]]:
    zones = em.get("geometry", {}).get("zones", [])
    zone_mults = { (z.get("name") or z.get("id") or ""): int(z.get("effective_multiplier") or 1) for z in zones }
    walls: List[Dict[str, Any]] = []
    roofs: List[Dict[str, Any]] = []
    floors: List[Dict[str, Any]] = []

    # include both residential and commercial zones; search descendants to allow wrappers
    for zn in (el for el in root.iter() if _lt(el.tag) in ("ResZn","ComZn")):
        zkey = _zone_key(zn)

        for tag in SURFACE_BUCKETS["walls"]:
            for n in zn.iterfind(f".//{tag}"):
                walls.append(_extract_surface(n,"wall",tag,zkey,zone_mults))

        for tag in SURFACE_BUCKETS["roofs"]:
            for n in zn.iterfind(f".//{tag}"):
                roofs.append(_extract_surface(n,"roof",tag,zkey,zone_mults))

        for tag in SURFACE_BUCKETS["floors"]:
            for n in zn.iterfind(f".//{tag}"):
                floors.append(_extract_surface(n,"floor",tag,zkey,zone_mults))

    em.setdefault("geometry", {}).setdefault("surfaces", {})["walls"] = walls
    em["geometry"]["surfaces"]["roofs"] = roofs
    em["geometry"]["surfaces"]["floors"] = floors
    em.setdefault("diagnostics", []).append({"level":"info","code":"I-SURF-COUNTS","message":f"walls={len(walls)}, roofs={len(roofs)}, floors={len(floors)}"})
    return walls + roofs + floors

# -------------------- openings --------------------
def _pz_safe_txt(node: ET.Element, local: str) -> Optional[str]:
    txt = _child_text_local(node, local) or node.get(local)
    return (txt or "").strip() if txt else None

def _pz_attr(node: ET.Element, name: str) -> Optional[str]:
    v = node.get(name)
    return (v or "").strip() if v else None

def _pz_make_id(kind: str, tag: str, name: str, parent: str = "") -> str:
    import re
    slug = re.sub(r"[^a-z0-9]+", "-", (name or "").strip().lower()).strip("-")
    pslug = re.sub(r"[^a-z0-9]+", "-", (parent or "").strip().lower()).strip("-")
    base = f"{kind}:{tag}:{slug}"
    return f"{base}@{pslug}" if pslug else base

_SURF_FOR_OPENINGS = SURFACE_BUCKETS["walls"] + SURFACE_BUCKETS["roofs"] + SURFACE_BUCKETS["floors"]

def _pz_openings_under(surf: ET.Element) -> List[ET.Element]:
    out = []
    for tag in ("ResWin","ComWin","Window","Door","Skylight"):
        out.extend(list(surf.iterfind(f".//{tag}")))
    return out

def parse_openings(root: ET.Element, em: Dict[str, Any], diags: Optional[List[Dict[str, Any]]] = None) -> None:
    openings = em.setdefault("geometry", {}).setdefault("openings", {})
    openings.setdefault("windows", []); openings.setdefault("doors", []); openings.setdefault("skylights", [])
    total_added = {"windows":0,"doors":0,"skylights":0}

    # iterate both ResZn and ComZn
    for zn in (el for el in root.iter() if _lt(el.tag) in ("ResZn","ComZn")):
        zone_name = (_child_text_local(zn, "Name","ZnName","ZoneName","ID","Id") or _pz_attr(zn,"id") or "zone").strip()
        zone_key = zone_name

        for surf_tag in _SURF_FOR_OPENINGS:
            for surf in zn.iterfind(f".//{surf_tag}"):
                surf_name = _pz_safe_txt(surf,"Name") or _pz_attr(surf,"name") or _pz_attr(surf,"id") or "surface"
                surf_id = _pz_make_id("surface", surf_tag, surf_name)

                for o in _pz_openings_under(surf):
                    otag = _lt(getattr(o,"tag",""))
                    oname = _pz_safe_txt(o,"Name") or _pz_attr(o,"name") or _pz_attr(o,"id") or "opening"
                    oid = _pz_make_id("opening", otag, oname, surf_name)

                    raw = {}
                    for child in list(o):
                        if child.tag and (child.text is not None):
                            raw[_lt(child.tag)] = child.text.strip()
                        elif child.tag and len(list(child)) > 0:
                            raw[_lt(child.tag)] = "has_children"

                    h = _pz_safe_txt(o, "Height"); w = _pz_safe_txt(o, "Width"); a = _pz_safe_txt(o, "Area")
                    entry = {
                        "id": oid,
                        "name": oname,
                        "type": otag,
                        "parent_surface_ref": surf_id,
                        "parent_zone_ref": zone_key,
                        "raw": raw,
                        "multiplier": {
                            "effective": 1, "factors": [], "base_quantity": 1, "applies_to": ["counts","areas"]
                        }
                    }
                    if h:
                        try: entry["height_m"] = float(h)
                        except ValueError: entry["height_raw"] = h
                    if w:
                        try: entry["width_m"] = float(w)
                        except ValueError: entry["width_raw"] = w
                    if a:
                        try: entry["area_m2"] = float(a)
                        except ValueError: entry["area_raw"] = a

                    if otag.lower() in ("reswin","comwin","window"):
                        openings["windows"].append(entry); total_added["windows"] += 1
                    elif otag.lower() in ("door",):
                        openings["doors"].append(entry); total_added["doors"] += 1
                    elif otag.lower() in ("skylight",):
                        openings["skylights"].append(entry); total_added["skylights"] += 1
                    else:
                        openings["windows"].append(entry); total_added["windows"] += 1

    em.setdefault("diagnostics", []).append({
        "level":"info","code":"I-OPENINGS-PARSED",
        "message": f"windows={total_added['windows']}, doors={total_added['doors']}, skylights={total_added['skylights']}",
        "context": total_added
    })
