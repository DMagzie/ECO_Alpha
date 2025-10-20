from __future__ import annotations
from typing import Any, Dict, List, Tuple, Optional
from xml.etree import ElementTree as ET

def _lt(tag: str) -> str:
    return tag.split('}', 1)[-1] if '}' in tag else tag

def _child_text_local(node, *names) -> str | None:
    wanted = {n.lower() for n in names}
    for ch in list(node or []):
        try:
            t = _lt(ch.tag).lower()
        except Exception:
            t = str(ch.tag).lower()
        if t in wanted and ch.text and ch.text.strip():
            return ch.text.strip()
    return None


# -------------------------------------------------------------------
# Diagnostics / tag-tracking hooks (provided by mapping_cleanup.py)
# -------------------------------------------------------------------
# at top of file
try:
    from .mapping_cleanup import SURFACE_BUCKETS, diag, mark_used
except ImportError:
    from cbecc.mapping_cleanup import SURFACE_BUCKETS, diag, mark_used  # type: ignore


# -------------------------------------------------------------------
# Basic XML helpers
# -------------------------------------------------------------------
def _txt(n):
    return (n.text or "").strip() if n is not None and n.text is not None else ""

def _child(p, tag: str):
    return p.find(tag) if p is not None else None

def _child_txt(p, tag: str) -> str:
    return _txt(_child(p, tag))

def _first(*vals: str | None):
    for v in vals:
        if v is None:
            continue
        s = v.strip()
        if s:
            return s
    return None

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

# -------------------------------------------------------------------
# ResZnGrp → zone_groups + levels
# -------------------------------------------------------------------
def parse_zone_groups_and_levels(root: ET.Element) -> Tuple[List[Dict[str, Any]], Dict[str, str], List[Dict[str, Any]], List[Dict[str, Any]]]:
    zone_groups: List[Dict[str, Any]] = []
    zone_to_group: Dict[str, str] = {}
    levels: List[Dict[str, Any]] = []
    seen: set[str] = set()

    for grp in root.findall(".//ResZnGrp"):
        gid = (grp.get("id") or _child_txt(grp, "Name") or "").strip() or None
        gname = (_child_txt(grp, "Name") or "").strip() or gid
        if not gname:
            continue
        key = (gid or gname).lower()
        if key in seen:
            continue
        seen.add(key)

        elev = _float(_child_txt(grp, "Z"))
        flr_flr = _float(_child_txt(grp, "FlrToFlrHgt"))
        flr_ceil = _float(_child_txt(grp, "FlrToCeilingHgt"))
        members: List[str] = []

        for rz in grp.findall("./ResZn"):
            zid = (rz.get("id") or "").strip()
            zname = (_child_txt(rz, "Name") or "").strip()
            mk = zid or zname
            if mk:
                members.append(mk)
                zone_to_group[mk] = gid or gname

        for oz in grp.findall("./ResOtherZn"):
            zid = (oz.get("id") or "").strip()
            zname = (_child_txt(oz, "Name") or "").strip()
            mk = zid or zname
            if mk:
                members.append(mk)
                zone_to_group[mk] = gid or gname

        zone_groups.append({
            "id": gid or gname,
            "name": gname,
            "elevation_z": elev,
            "flr_to_flr": flr_flr,
            "flr_to_ceiling": flr_ceil,
            "members": list(dict.fromkeys(members)),
        })
        levels.append({
            "id": gid or gname,
            "name": gname,
            "elevation_z": elev,
            "flr_to_flr": flr_flr,
            "flr_to_ceiling": flr_ceil,
            "source": "ResZnGrp",
        })
        mark_used("ResZnGrp", "Name", "Z", "FlrToFlrHgt", "FlrToCeilingHgt")

    diags = [diag("info", "I-LEVELS", f"zone_groups parsed={len(zone_groups)}; levels mirrored={len(levels)}")]
    return levels, zone_to_group, zone_groups, diags

# -------------------------------------------------------------------
# Zones (ResZn + ResOtherZn)
# -------------------------------------------------------------------
def parse_zones(root: ET.Element, em: Dict[str, Any], du_index: Dict[str, Dict[str, Any]], zone_to_group: Dict[str, str]) -> List[Dict[str, Any]]:
    zones: List[Dict[str, Any]] = []

    for zn in root.findall(".//ResZn"):
        zid = (zn.get("id") or "").strip() or None
        zname = (_child_txt(zn, "Name") or "").strip() or None

        zfa = _float(_first(_child_txt(zn, "FloorArea"), _child_txt(zn, "FlrArea"), _child_txt(zn, "Area"), _child_txt(zn, "GrossArea")))
        mult = _float(_child_txt(zn, "Multiplier")) or 1.0
        if zfa is not None and mult != 1.0:
            zfa *= mult

        du_ref = _first(_child_txt(zn, "DUTypeRef"), _child_txt(_child(zn, "DwellUnit"), "DwellUnitTypeRef"))
        du_ref_canon = None
        if du_ref and du_index.get(du_ref.strip().lower()):
            du_ref_canon = du_index[du_ref.strip().lower()]["name"]
        if not du_ref_canon and zname:
            token = zname.split("_", 1)[0].strip()
            hit = du_index.get(f"unit {token}".lower())
            if hit:
                du_ref_canon = hit["name"]

        if zfa is None and du_ref_canon:
            du_area = (du_index.get(du_ref_canon.lower()) or {}).get("floor_area")
            du_count = _float(_first(_child_txt(zn, "DUCount"), _child_txt(zn, "Units")))
            if du_area is not None and (du_count or 1.0):
                zfa = du_area * (du_count or 1.0) * mult

        zones.append({
            "id": zid,
            "name": zname,
            "type": (_first(_child_txt(zn, "ZoneType"), _child_txt(zn, "Type")) or "conditioned").lower(),
            "level_ref": zone_to_group.get((zid or zname) or ""),
            "floor_area": zfa,
            "volume": _float(_child_txt(zn, "Volume")),
            "du_type_ref": du_ref_canon,
        })
        mark_used("ResZn", "Name")

    other_seen: set[str] = set()
    for oz in root.findall(".//ResOtherZn"):
        key = (oz.get("id") or _child_txt(oz, "Name") or "").strip().lower()
        if not key or key in other_seen:
            continue
        other_seen.add(key)

        zid = (oz.get("id") or "").strip() or None
        zname = (_child_txt(oz, "Name") or "").strip() or None
        zfa = _float(_first(_child_txt(oz, "FloorArea"), _child_txt(oz, "FlrArea"), _child_txt(oz, "Area"), _child_txt(oz, "GrossArea")))
        mult = _float(_child_txt(oz, "Multiplier")) or 1.0
        if zfa is not None and mult != 1.0:
            zfa *= mult

        zones.append({
            "id": zid,
            "name": zname,
            "type": (_first(_child_txt(oz, "ZoneType"), _child_txt(oz, "Type")) or "other").lower(),
            "level_ref": zone_to_group.get((zid or zname) or ""),
            "floor_area": zfa,
            "volume": _float(_child_txt(oz, "Volume")),
            "du_type_ref": None,
            "source": "ResOtherZn",
        })
        mark_used("ResOtherZn", "Name")

    em["geometry"]["zones"] = zones
    have_area = sum(1 for z in zones if z.get("floor_area") is not None)
    return [diag("info", "I-ZONES-AREA-COVERAGE", f"{have_area}/{len(zones)} zones have floor_area")]

# -------------------------------------------------------------------
# Geometry metrics & surface annotations
# -------------------------------------------------------------------
def parse_geometry_metrics_annotations(root: ET.Element, em: Dict[str, Any]) -> List[Dict[str, Any]]:
    metrics = em["geometry"].setdefault("metrics", {})
    for tag in ("BldgAz", "CeilingHeight", "FloorHeight", "FlrToCeilingHgt", "FlrToFlrHgt", "FloorZ"):
        node = root.find(f".//{tag}")
        if node is not None and _txt(node):
            try:
                metrics[tag] = float(_txt(node))
            except Exception:
                metrics[tag] = _txt(node)
            mark_used(tag)
    annotations: Dict[str, Any] = {}
    for tag in ("IsPartySurface", "IsClerestory", "Outside", "Bottom", "Perimeter", "ModelFinsOverhang",
                "RValPerInch", "Conductivity", "ConductivityCT", "ConductivityQII", "Density"):
        if root.find(f".//{tag}") is not None:
            annotations.setdefault("fields", []).append(tag)
            mark_used(tag)
    if annotations:
        em["geometry"]["surface_annotations_meta"] = annotations
    diags = []
    if metrics:
        diags.append(diag("info", "I-MAP-GEOM", f"geometry.metrics keys={list(metrics.keys())}"))
    if annotations:
        diags.append(diag("info", "I-MAP-SURF", f"geometry.surface_annotations_meta fields={annotations.get('fields')}"))
    return diags

# -------------------------------------------------------------------
# Surfaces (Walls, Roofs, Floors) — long-term robust parser
# -------------------------------------------------------------------
def _boolish(s: Optional[str]) -> Optional[bool]:
    if s is None:
        return None
    t = str(s).strip().lower()
    if t in {"1", "true", "yes", "y", "t"}:
        return True
    if t in {"0", "false", "no", "n", "f"}:
        return False
    return None

_ORIENT_TO_AZ = {
    "n": 0.0, "nne": 22.5, "ne": 45.0, "ene": 67.5,
    "e": 90.0, "ese": 112.5, "se": 135.0, "sse": 157.5,
    "s": 180.0, "ssw": 202.5, "sw": 225.0, "wsw": 247.5,
    "w": 270.0, "wnw": 292.5, "nw": 315.0, "nnw": 337.5,
}

def _az_from_orientation(o: Optional[str]) -> Optional[float]:
    if not o:
        return None
    key = o.strip().lower()
    return _ORIENT_TO_AZ.get(key)

def _num(node: ET.Element, tag: str) -> Optional[float]:
    return _float(_child_txt(node, tag))

def _area_with_backfill(n: ET.Element) -> Optional[float]:
    a = _num(n, "Area")
    if a is not None:
        mark_used("Area")
        return a
    w = _num(n, "Width")
    h = _num(n, "Height")
    L = _num(n, "Length")
    if w is not None and h is not None:
        mark_used("Width", "Height")
        return w * h
    if L is not None and w is not None:
        mark_used("Length", "Width")
        return L * w
    per = _num(n, "Perimeter")
    strip = _num(n, "StripWidth")
    if per is not None and strip is not None:
        mark_used("Perimeter", "StripWidth")
        return per * strip
    return None

def _construction_ref(n: ET.Element) -> Optional[str]:
    ref = _first(_child_txt(n, "ConstructionTypeRef"), _child_txt(n, "Construction"))
    if ref:
        mark_used("ConstructionTypeRef", "Construction")
    return ref

def _orientation_payload(n: ET.Element, default_tilt: float) -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    az = _num(n, "Azimuth")
    if az is None:
        ori = _child_txt(n, "Orientation")
        az = _az_from_orientation(ori)
        if ori:
            mark_used("Orientation")
    else:
        mark_used("Azimuth")
    if az is not None:
        out["azimuth_deg"] = az

    tilt = _num(n, "Tilt")
    if tilt is None:
        tilt = default_tilt
    else:
        mark_used("Tilt")
    out["tilt_deg"] = tilt
    return out

def _boundary_payload(n: ET.Element, category: str, subtype: str) -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    is_party = _boolish(_child_txt(n, "IsPartySurface"))
    outside = _boolish(_child_txt(n, "Outside"))
    if _child_txt(n, "IsPartySurface") is not None:
        mark_used("IsPartySurface")
    if _child_txt(n, "Outside") is not None:
        mark_used("Outside")

    if category == "floor" and subtype == "slab":
        bc = "ground"
    elif is_party is True:
        bc = "party"
    elif outside is True or category == "roof":
        bc = "outdoor"
    else:
        bc = "interior_or_adiabatic"

    out["boundary_condition"] = bc
    if is_party is not None:
        out["is_party_surface"] = is_party
    if outside is not None:
        out["outside_flag"] = outside
    if category == "floor":
        out["ground_contact"] = (bc == "ground")
    if category == "wall":
        ug_hint = _boolish(_child_txt(n, "UnderGrd")) or _boolish(_child_txt(n, "BelowGrade"))
        if ug_hint is not None:
            out["below_grade"] = ug_hint
            if ug_hint and bc == "outdoor":
                out["boundary_condition"] = "ground"
            mark_used("UnderGrd", "BelowGrade")
    return out

def _parent_zone_key(zn: ET.Element) -> str:
    return (_child_txt(zn, "Name") or zn.get("id") or "").strip()

def _extract_surface(n: ET.Element, category: str, subtype: str, parent_zone_ref: Optional[str], zone_mults: Dict[str, int]) -> Dict[str, Any]:
    name = (_child_txt(n, "Name") or "").strip()
    if name:
        mark_used("Name")
    payload: Dict[str, Any] = {
        "name": name,
        "parent_zone_ref": (parent_zone_ref or None),
        "construction_type_ref": _construction_ref(n),
        "category": category,
        "subtype": subtype,
    }

    if category == "wall":
        payload.update(_orientation_payload(n, default_tilt=90.0))
    elif category == "roof":
        payload.update(_orientation_payload(n, default_tilt=0.0))
    else:
        payload.update(_orientation_payload(n, default_tilt=0.0))

    area = _area_with_backfill(n)
    if area is not None:
        payload["area_ft2"] = area

    payload.update(_boundary_payload(n, category, subtype))

    zkey = (parent_zone_ref or "").strip()
    eff_mult = zone_mults.get(zkey, 1)
    if area is not None and eff_mult > 1:
        payload["effective_area_ft2"] = area * eff_mult

    # strip empty
    return {k: v for k, v in payload.items() if v not in (None, "", [], {})}

def parse_surfaces(root: ET.Element, em: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Surfaces (walls/roofs/floors) parsed strictly under ResZn.
    Uses unified SURFACE_BUCKETS and computes effective_area_ft2 with zone multipliers.
    """
    # ---- build zone_mults BEFORE use ----
    zone_mults: Dict[str, int] = {}
    try:
        for z in (em.get("geometry", {}).get("zones") or []):
            zname = (z.get("name") or z.get("id") or "").strip()
            if zname:
                zone_mults[zname] = int(z.get("effective_multiplier") or 1)
    except Exception:
        pass

    walls: List[Dict[str, Any]] = []
    roofs: List[Dict[str, Any]] = []
    floors: List[Dict[str, Any]] = []

    def _zone_key(zn: ET.Element) -> str:
        return (_child_txt(zn, "Name") or zn.get("id") or "").strip()

    # ---- single pass: surfaces must live under zones ----
    for zn in root.findall(".//ResZn"):
        zkey = _zone_key(zn)

        # walls
        for tag in SURFACE_BUCKETS["walls"]:
            for n in zn.findall(f"./{tag}"):
                payload = _extract_surface(n, "wall", tag, zkey, zone_mults)
                walls.append(payload)
                mark_used(tag)

        # roofs (ceilings grouped with roofs)
        for tag in SURFACE_BUCKETS["roofs"]:
            for n in zn.findall(f"./{tag}"):
                payload = _extract_surface(n, "roof", tag, zkey, zone_mults)
                roofs.append(payload)
                mark_used(tag)

        # floors (includes ExtFlr variants)
        for tag in SURFACE_BUCKETS["floors"]:
            for n in zn.findall(f"./{tag}"):
                payload = _extract_surface(n, "floor", tag, zkey, zone_mults)
                floors.append(payload)
                mark_used(tag)

    # ---- write & diagnostics ----
    em.setdefault("geometry", {})["surfaces"] = {"walls": walls, "roofs": roofs, "floors": floors}

    all_surfs = walls + roofs + floors
    missing_area = sum(1 for s in all_surfs if "area_ft2" not in s)
    missing_cons = sum(1 for s in all_surfs if "construction_type_ref" not in s)

    # boundary stats
    bc_counts: Dict[str, int] = {}
    for s in all_surfs:
        bc = s.get("boundary_condition", "unknown")
        bc_counts[bc] = bc_counts.get(bc, 0) + 1

    # orientation stats
    def _rose_bucket(az: float) -> str:
        vals = [0, 45, 90, 135, 180, 225, 270, 315]
        names = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]
        diffs = [abs(az - v) for v in vals]
        return names[diffs.index(min(diffs))]

    rose: Dict[str, int] = {}
    for s in all_surfs:
        az = s.get("azimuth_deg")
        if isinstance(az, (int, float)):
            bucket = _rose_bucket(float(az))
            rose[bucket] = rose.get(bucket, 0) + 1

    return [
        diag("info", "I-SURF-COUNTS", f"walls={len(walls)}, roofs={len(roofs)}, floors={len(floors)}"),
        diag("info", "I-SURF-QUALITY", f"missing area={missing_area}, missing construction_type_ref={missing_cons}"),
        diag("info", "I-SURF-BOUNDARY-STATS", f"{bc_counts}"),
        diag("info", "I-SURF-ORIENT-STATS", f"{rose or {'note': 'no azimuths found'}}"),
    ]

# -------------------------------------------------------------------
# Openings (windows, doors, skylights) — bound to parent surfaces
# -------------------------------------------------------------------
# stdlib ET (no getparent support)
import xml.etree.ElementTree as ET  # noqa: E402

def _pz_safe_txt(node: Optional[ET.Element], tag: str, default: Optional[str] = None) -> Optional[str]:
    if node is None:
        return default
    found = node.find(tag)
    return (found.text.strip() if (found is not None and found.text is not None) else default)

def _pz_attr(node: Optional[ET.Element], name: str, default: Optional[str] = None) -> Optional[str]:
    return node.get(name) if (node is not None and name in node.attrib) else default

def _pz_make_id(prefix: str, *parts: str) -> str:
    norm = "-".join([str(p).strip().replace(" ", "_") for p in parts if p is not None and str(p).strip() != ""])
    return f"{prefix}:{norm}" if norm else prefix

def _pz_get_or_init_openings(em: Dict[str, Any]) -> Dict[str, Any]:
    g = em.setdefault("geometry", {})
    o = g.setdefault("openings", {})
    o.setdefault("windows", [])
    o.setdefault("doors", [])
    o.setdefault("skylights", [])
    return o

def _pz_add_diag(diags: List[Dict[str, Any]], level: str, code: str, message: str, ctx: Optional[Dict[str, Any]] = None) -> None:
    item = {"level": level, "code": code, "message": message}
    if ctx:
        item["context"] = ctx
    diags.append(item)

def _pz_surface_iter(root: ET.Element) -> List[ET.Element]:
    tags = ["ResExtWall", "ComExtWall", "ResRoof", "ComRoof", "ResCeiling", "ComCeiling"]
    found = []
    for t in tags:
        found.extend(root.findall(f".//{t}"))
    return found

def _pz_openings_under(node: ET.Element) -> List[ET.Element]:
    tags = ["ResWin", "ComWin", "Window", "Door", "Skylight"]
    out = []
    for t in tags:
        out.extend(node.findall(f".//{t}"))
    return out

def _pz_surface_orientation(surface: ET.Element) -> Dict[str, Any]:
    orientation = _pz_safe_txt(surface, "Orientation")
    azimuth = _pz_safe_txt(surface, "Azimuth")
    tilt = _pz_safe_txt(surface, "Tilt")
    res = {}
    if orientation:
        res["orientation"] = orientation
    if azimuth is not None:
        try:
            res["azimuth_deg"] = float(azimuth)
        except ValueError:
            res["azimuth_raw"] = azimuth
    if tilt is not None:
        try:
            res["tilt_deg"] = float(tilt)
        except ValueError:
            res["tilt_raw"] = tilt
    return res

def parse_story_levels(root: ET.Element, em: Dict[str, Any], diags: Optional[List[Dict[str, Any]]] = None) -> None:
    if diags is None:
        diags = em.setdefault("diagnostics", [])
    g = em.setdefault("geometry", {})
    levels: List[Dict[str, Any]] = g.setdefault("levels", [])
    existing_by_name = {(lvl.get("name") or "").strip().lower(): lvl for lvl in levels if isinstance(lvl, dict)}
    added = merged = 0

    for story in root.findall(".//Story"):
        name = _pz_safe_txt(story, "Name") or _pz_attr(story, "name") or "Story"
        key = name.strip().lower()
        elevation = _pz_safe_txt(story, "Elevation")
        height = _pz_safe_txt(story, "Height") or _pz_safe_txt(story, "FlrToFlr")

        payload: Dict[str, Any] = {"id": _pz_make_id("level", name), "name": name, "source": "Story", "raw": {}}
        if elevation:
            try:
                payload["elevation_m"] = float(elevation)
            except ValueError:
                payload["elevation_raw"] = elevation
        if height:
            try:
                payload["floor_to_floor_m"] = float(height)
            except ValueError:
                payload["floor_to_floor_raw"] = height
        for c in list(story):
            if c.tag and c.text:
                payload["raw"][c.tag] = c.text.strip()

        if key in existing_by_name:
            target = existing_by_name[key]
            for k, v in payload.items():
                if k == "raw":
                    target.setdefault("raw", {})
                    target["raw"].update(payload["raw"])
                else:
                    if k not in target or target[k] in (None, "", []):
                        target[k] = v
            merged += 1
        else:
            levels.append(payload)
            added += 1

    diags.append({"level": "info", "code": "I-STORIES-PARSED",
                  "message": f"Story levels parsed: added={added}, merged={merged}",
                  "context": {"added": added, "merged": merged}})

def parse_openings(root: ET.Element, em: Dict[str, Any], diags: Optional[List[Dict[str, Any]]] = None) -> None:
    if diags is None:
        diags = em.setdefault("diagnostics", [])
    openings = _pz_get_or_init_openings(em)
    total_added = {"windows": 0, "doors": 0, "skylights": 0}

    # surfaces that can host openings (same taxonomy as elsewhere)
    _SURF_FOR_OPENINGS = (
        list(SURFACE_BUCKETS["walls"]) +
        ["ResRoof", "ComRoof", "ResCeiling", "ComCeiling", "ResCathedralCeiling"]
    )

    for zn in root.findall(".//ResZn"):
        zone_name = _pz_safe_txt(zn, "Name") or _pz_attr(zn, "id") or "zone"
        zone_key = zone_name.strip()

        for surf_tag in _SURF_FOR_OPENINGS:
            for surf in zn.findall(f"./{surf_tag}"):
                surf_name = _pz_safe_txt(surf, "Name") or _pz_attr(surf, "name") or _pz_attr(surf, "id") or "surface"
                surf_id = _pz_make_id("surface", surf_tag, surf_name)
                orient = _pz_surface_orientation(surf)

                for o in _pz_openings_under(surf):
                    otag = o.tag
                    oname = _pz_safe_txt(o, "Name") or _pz_attr(o, "name") or _pz_attr(o, "id") or "opening"
                    oid = _pz_make_id("opening", otag, oname, surf_name)

                    raw = {}
                    for child in list(o):
                        if child.tag and (child.text is not None):
                            raw[child.tag] = child.text.strip()
                        elif child.tag and len(list(child)) > 0:
                            raw[child.tag] = "has_children"

                    h = _pz_safe_txt(o, "Height")
                    w = _pz_safe_txt(o, "Width")
                    a = _pz_safe_txt(o, "Area")

                    entry = {
                        "id": oid,
                        "name": oname,
                        "type": otag.lower(),
                        "parent_surface_ref": surf_id,
                        "parent_zone_ref": zone_key,  # <-- critical for multiplied counts
                        **orient,
                        "raw": raw,
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

                    if otag.lower() in ("reswin", "comwin", "window"):
                        openings["windows"].append(entry); total_added["windows"] += 1
                    elif otag.lower() in ("door",):
                        openings["doors"].append(entry); total_added["doors"] += 1
                    elif otag.lower() in ("skylight",):
                        openings["skylights"].append(entry); total_added["skylights"] += 1
                    else:
                        openings["windows"].append(entry); total_added["windows"] += 1

    _pz_add_diag(
        diags, "info", "I-OPENINGS-PARSED",
        f"Bound openings to parent surfaces/zones: windows={total_added['windows']}, doors={total_added['doors']}, skylights={total_added['skylights']}",
        ctx=total_added
    )
