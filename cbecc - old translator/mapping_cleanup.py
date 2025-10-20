from __future__ import annotations
from typing import Any, Dict, List, Tuple, Optional
from xml.etree import ElementTree as ET
import json

# ---------- Diagnostics & tag tracking ----------
USED_TAGS: set[str] = set()
SEEN_TAGS: set[str] = set()

def diag(level: str, code: str, msg: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    d = {"level": level, "code": code, "message": msg}
    if context:
        d["context"] = context
    return d

def mark_used(*tags: str) -> None:
    for t in tags:
        if t:
            USED_TAGS.add(t)

def collect_all_tags(root: ET.Element) -> None:
    stack = [root]
    while stack:
        el = stack.pop()
        try:
            SEEN_TAGS.add(el.tag)
        except Exception:
            pass
        stack.extend(list(el))

def summarize_unused_tags(max_list: int = 150) -> Dict[str, Any]:
    unused = sorted(t for t in SEEN_TAGS if t not in USED_TAGS)
    msg = f"unused={len(unused)}" + (f": {', '.join(unused[:max_list])}" if unused else "")
    return diag("info", "I-UNUSED-TAGS", msg, {"unused_sample": unused[:max_list]})

# ---------- EM shell (authoritative=energy.*; mirror legacy hvac.*) ----------
def ensure_shell_v6() -> Dict[str, Any]:
    return {
        "project": {"location": {}},
        "catalogs": {
            "window_types": [],
            "construction_types": [],
            "constructions_detailed": [],
            "materials": [],
            "du_types": [],
            # simplified catalogs for UI
            "hvac_types": [],
            "iaq_fan_types": [],
            "dhw_types": [],
        },
        "geometry": {
            "levels": [],
            "zone_groups": [],
            "zones": [],
            "surfaces": {"walls": [], "roofs": [], "floors": []},
            "openings": {"windows": [], "doors": [], "skylights": []},
            "metrics": {},
        },
        # Authoritative containers:
        "energy": {
            "hvac_systems": [],
            "iaq_fans": [],
            "dhw_systems": [],
            "hvac_components": [],
            "pv_battery": {},
        },
        # Legacy mirror for back-compat with older code paths:
        "hvac": {"systems": [], "simplified_systems": {}, "iaq_fans": [], "dhw_systems": []},
        "diagnostics": [],
        "version": "6",
    }

def _len_safe(x) -> int:
    try:
        return len(x) if x is not None else 0
    except Exception:
        return 0

def mirror_energy_to_legacy_hvac(em: Dict[str, Any]) -> None:
    """Mirror authoritative energy collections to legacy hvac.* for back-compat."""
    energy = em.get("energy", {})
    hvac = em.setdefault("hvac", {})
    hvac["systems"] = list(energy.get("hvac_systems", []))
    hvac["iaq_fans"] = list(energy.get("iaq_fans", []))
    hvac["dhw_systems"] = list(energy.get("dhw_systems", []))

def summarize_counts(em: Dict[str, Any]) -> Dict[str, Any]:
    g = em.get("geometry", {})
    s = g.get("surfaces", {})
    o = g.get("openings", {})
    energy = em.get("energy", {})
    counts = {
        "zones": _len_safe(g.get("zones")),
        "walls": _len_safe(s.get("walls")),
        "roofs": _len_safe(s.get("roofs")),
        "floors": _len_safe(s.get("floors")),
        "windows": _len_safe(o.get("windows")),
        "doors": _len_safe(o.get("doors")),
        "skylights": _len_safe(o.get("skylights")),
        "hvac_systems": _len_safe(energy.get("hvac_systems")),
        "iaq_fans": _len_safe(energy.get("iaq_fans")),
        "dhw_systems": _len_safe(energy.get("dhw_systems")),
        "win_types": _len_safe(em.get("catalogs", {}).get("window_types")),
        "cons_types": _len_safe(em.get("catalogs", {}).get("construction_types")),
        "du_types": _len_safe(em.get("catalogs", {}).get("du_types")),
    }
    msg = ("zones={zones} "
           "surfaces(walls={walls}, roofs={roofs}, floors={floors}) "
           "openings(windows={windows}, doors={doors}, skylights={skylights}) "
           "energy(hvac={hvac_systems}, iaq={iaq_fans}, dhw={dhw_systems}) "
           "catalogs(win_types={win_types}, cons_types={cons_types}, du_types={du_types})").format(**counts)
    return diag("info", "I-COUNTS", msg, counts)

# ---------- Raw-field de-dupe (works on authoritative energy.*) ----------
def _norm_key(x: str) -> str:
    return str(x).strip().lower().replace(" ", "").replace("-", "").replace(".", "").replace("_", "")

def _norm_val(x) -> str:
    try:
        return str(x).strip().lower()
    except Exception:
        return ""

_SYSTEM_RAW_DROP = {"name","type","status","systemref","system_type","htpumpsystem","distribsystem","fan"}
_HP_RAW_DROP     = {"name","type","status","systemref","htpumpsystem","distribsystem","fan"}
_FAN_RAW_DROP    = {"name","type","status","fan"}
_DIST_RAW_DROP   = {"name","type","status","systemref","distribsystem"}

def _gather_mapped_pairs_full(obj: dict) -> Tuple[set, set, Dict[str, Any]]:
    mapped_vals = set()
    mapped_kv = set()
    flat_map: Dict[str, Any] = {}

    def add_leafs(d: dict, prefix: str = ""):
        for k, v in d.items():
            if k in ("raw_fields","export_hints") or isinstance(v, (dict, list)):
                continue
            flat_key = f"{prefix}{k}" if not prefix else f"{prefix}.{k}"
            flat_map[flat_key] = v
            nk, nv = _norm_key(flat_key), _norm_val(v)
            if nv:
                mapped_vals.add(nv)
                mapped_kv.add((nk, nv))

    add_leafs(obj)
    for subkey in ("heating","cooling","heat_pump","distribution","controls","fans","iaq_fans"):
        sub = obj.get(subkey)
        if isinstance(sub, dict):
            add_leafs(sub, prefix=subkey)
        elif isinstance(sub, list):
            for idx, it in enumerate(sub):
                if isinstance(it, dict):
                    add_leafs(it, prefix=f"{subkey}[{idx}]")
    return mapped_vals, mapped_kv, flat_map

def _build_export_reverse(obj: dict) -> Dict[str,str]:
    rev: Dict[str,str] = {}
    def add_hints(prefix, hints):
        if not isinstance(hints, dict):
            return
        for skey, raw in hints.items():
            if not raw:
                continue
            leaf = skey
            if prefix and not leaf.startswith(prefix):
                leaf = f"{prefix}.{leaf}"
            rev[str(raw)] = leaf
    add_hints("", obj.get("export_hints"))
    for subkey in ("heating","cooling","heat_pump","distribution","controls","fans","iaq_fans"):
        sub = obj.get(subkey)
        if isinstance(sub, dict):
            add_hints(subkey, sub.get("export_hints"))
        elif isinstance(sub, list):
            for it in sub:
                if isinstance(it, dict):
                    add_hints(subkey, it.get("export_hints"))
    return rev

def _dedupe_raw_fields_on(obj: dict, scope: str):
    rf = obj.get("raw_fields")
    if not isinstance(rf, dict) or not rf:
        return

    scope_key = scope.lower()
    if scope_key == "system":
        drop = _SYSTEM_RAW_DROP
    elif scope_key == "heat_pump":
        drop = _HP_RAW_DROP
    elif scope_key == "distribution":
        drop = _DIST_RAW_DROP
    elif scope_key == "fan":
        drop = _FAN_RAW_DROP
    else:
        drop = {"name","type","status"}

    mapped_vals, mapped_kv, flat_map = _gather_mapped_pairs_full(obj)
    rev = _build_export_reverse(obj)

    to_del = []
    for k, v in list(rf.items()):
        nk = _norm_key(k); nv = _norm_val(v)
        if nk in drop:
            to_del.append(k); continue
        if k in rev:
            flat_key = rev[k]
            if flat_key in flat_map and _norm_val(flat_map[flat_key]) == nv:
                to_del.append(k); continue
        if (nk, nv) in mapped_kv or nv in mapped_vals:
            to_del.append(k); continue
        for sk, sv in flat_map.items():
            if _norm_val(sv) == nv and (_norm_key(sk).endswith(nk) or nk.endswith(_norm_key(sk))):
                to_del.append(k); break

    for k in to_del:
        rf.pop(k, None)
    if not rf:
        obj.pop("raw_fields", None)

def hvac_dedupe_raw_fields(em: Dict[str, Any], diags: List[Dict[str, Any]]):
    """Run raw field de-dup on authoritative energy systems, then mirror."""
    energy = em.get("energy") or {}
    for sys in energy.get("hvac_systems", []) or []:
        if isinstance(sys, dict):
            _dedupe_raw_fields_on(sys, "system")
            for subname, scope in [("heat_pump","heat_pump"),("distribution","distribution"),
                                   ("heating","heating"),("cooling","cooling"),("controls","controls")]:
                sub = sys.get(subname)
                if isinstance(sub, dict):
                    _dedupe_raw_fields_on(sub, scope)
            fans = sys.get("fans")
            if isinstance(fans, dict):
                _dedupe_raw_fields_on(fans, "fan")
            elif isinstance(fans, list):
                for f in fans:
                    if isinstance(f, dict):
                        _dedupe_raw_fields_on(f, "fan")
    diags.append(diag("info","I-HVAC-CLEAN","hvac raw_fields de-duplicated on energy.*"))
    mirror_energy_to_legacy_hvac(em)

def hvac_finalize_cleanup(em: Dict[str, Any], diags: List[Dict[str, Any]]):
    """Top-level cleanups and final mirroring."""
    energy = em.get("energy") or {}
    iaq = energy.get("iaq_fans") or []
    seen, uniq = set(), []
    for f in iaq:
        nm = (f.get("name") or "").strip().lower()
        key = nm or json.dumps(f, sort_keys=True)
        if key in seen:
            continue
        seen.add(key)
        if isinstance(f.get("raw_fields"), dict) and not f["raw_fields"]:
            f.pop("raw_fields", None)
        uniq.append(f)
    energy["iaq_fans"] = uniq

    # Drop empty raw_fields placeholders
    for s in energy.get("hvac_systems", []) or []:
        if "raw_fields" in s and not s["raw_fields"]:
            s.pop("raw_fields", None)
        for part in ("heating","cooling","heat_pump","distribution","controls","fans"):
            p = s.get(part)
            if isinstance(p, dict) and "raw_fields" in p and not p["raw_fields"]:
                p.pop("raw_fields", None)
            elif isinstance(p, list):
                for it in p:
                    if isinstance(it, dict) and "raw_fields" in it and not it["raw_fields"]:
                        it.pop("raw_fields", None)

    diags.append(diag("info","I-IAQ-DEDUPE", f"iaq_fans unique={len(energy.get('iaq_fans', []))} (catalog+simplified merged)"))
    mirror_energy_to_legacy_hvac(em)

# ---------- lightweight helper used inside parsers_* ----------
def dedupe_raw_fields_basic(mapped: Dict[str, Any], raw_fields: Dict[str, Any], export_hints: Dict[str,str] | None=None) -> Dict[str, Any]:
    if not raw_fields:
        return {}
    mapped_vals = set()

    def _add(v):
        if isinstance(v, (int,float,str,bool)) and v not in ("", None):
            mapped_vals.add(str(v).strip())

    for k,v in mapped.items():
        if k in ("raw_fields","export_hints"):
            continue
        if isinstance(v, dict):
            for vv in v.values(): _add(vv)
        elif isinstance(v, list):
            for it in v:
                if isinstance(it, dict):
                    for vv in it.values(): _add(vv)
                else:
                    _add(it)
        else:
            _add(v)

    drop_by_tag = set()
    if export_hints:
        for field, tag in export_hints.items():
            if tag: drop_by_tag.add(tag)

    filtered: Dict[str, Any] = {}
    for tag, val in raw_fields.items():
        if tag in drop_by_tag:
            continue
        if str(val).strip() in mapped_vals:
            continue
        filtered[tag] = val
    return filtered

# ===============================================================
# Unified taxonomy + counts comparison (XML vs EM)

# ---- Unified tag→bucket mapping used by BOTH translator and quick-check ----
SURFACE_BUCKETS: Dict[str, set] = {
    "walls": {
        # standard
        "ResExtWall", "ComExtWall", "ResIntWall", "ComIntWall",
        # requested wall variants
        "FoundationWall", "BelowGradeWall", "StemWall", "KneeWall", "PartyWall",
        # sometimes variants appear with Res/Com prefixes – include both forms
        "ResFoundationWall", "ComFoundationWall", "ResBelowGradeWall", "ComBelowGradeWall",
        "ResStemWall", "ComStemWall", "ResKneeWall", "ComKneeWall", "ResPartyWall", "ComPartyWall",
    },
    "roofs": {
        # group ceilings with roofs
        "ResRoof", "ComRoof", "ResCathedralCeiling", "ResCeiling", "ComCeiling",
    },
    "floors": {
        "ResSlabFlr", "ComSlabFlr", "ResRaisedFlr", "ComRaisedFlr",
        "ResIntFlr", "ComIntFlr",
        # requested: ExtFlr variants count as floors
        "ExtFlr", "ResExtFlr", "ComExtFlr",
    },
}

OPENING_TAGS: set = {
    "ResWin", "ComWin", "Window", "Door", "Skylight",
}

ZONE_TAGS: set = {
    "ResZn", "ResOtherZn",  # we scope surfaces to ResZn; ResOtherZn is for totals/coverage
}

# ---- XML utils (reused) ----
def _x_txt(n: Optional[ET.Element], tag: str) -> Optional[str]:
    if n is None:
        return None
    el = n.find(tag)
    return (el.text or "").strip() if el is not None and el.text is not None else None

def _x_to_int(val: Any, default: int = 1) -> int:
    try:
        s = str(val).strip()
        if s == "":
            return default
        return int(float(s))
    except Exception:
        return default

# ---- Effective multiplier from XML (zone multiplier × DU count in zone) ----
def xml_zone_effective_multiplier_map(root: ET.Element) -> Dict[str, int]:
    """Return {zone_name_lower: effective_multiplier} based on:
       - DU counts (sum of <DwellUnit><Count> by type) and
       - zone multiplier tags (<ZnMult>/<Mult>/<Count>)
       Only for ResZn zones (surfaces live here).
    """
    eff: Dict[str, int] = {}
    for rz in root.findall(".//ResZn"):
        zname = _x_txt(rz, "Name") or rz.get("Name") or rz.get("id")
        if not zname:
            continue
        zkey = zname.strip().lower()
        du_total = 0
        for du in rz.findall("./DwellUnit"):
            du_total += _x_to_int(_x_txt(du, "Count") or du.get("Count") or 1, 1)
        if du_total < 1:
            du_total = 1
        z_mult = _x_to_int(
            _x_txt(rz, "ZnMult") or _x_txt(rz, "Mult") or rz.get("Mult")
            or _x_txt(rz, "Count") or rz.get("Count") or 1,
            1,
        )
        eff[zkey] = du_total * z_mult
    return eff

# ---- Per-tag counter under ResZn (no free-floating surfaces) ----
def xml_per_tag_counts(root: ET.Element) -> Dict[str, int]:
    """Return raw per-tag counts of all tags we care about, scoped under ResZn."""
    counts: Dict[str, int] = {}
    for rz in root.findall(".//ResZn"):
        for bucket, tagset in SURFACE_BUCKETS.items():
            for t in tagset:
                for _ in rz.findall(f"./{t}"):
                    counts[t] = counts.get(t, 0) + 1
        for t in OPENING_TAGS:
            for _ in rz.findall(f".//{t}"):
                counts[t] = counts.get(t, 0) + 1
    # zones
    counts["ResZn"] = len(root.findall(".//ResZn"))
    counts["ResOtherZn"] = len(root.findall(".//ResOtherZn"))
    return counts

# ---- EM per-tag counts (we count from parsed EM structures) ----
def em_per_tag_counts(em: Dict[str, Any]) -> Dict[str, int]:
    """Map back EM structures into equivalent per-tag counts using the same taxonomy.
       We don’t have original XML tags on the EM side, so we count by EM buckets and
       attribute the count to one representative tag per family where needed.
    """
    counts: Dict[str, int] = {}

    # Zones
    zones = (em.get("geometry", {}) or {}).get("zones", []) or []
    counts["ResZn"] = len([z for z in zones if (z.get("source") or "").lower() != "resotherzn"])
    counts["ResOtherZn"] = len([z for z in zones if (z.get("source") or "").lower() == "resotherzn"])

    # Surfaces
    surfs = (em.get("geometry", {}) or {}).get("surfaces", {}) or {}
    # We cannot reconstruct exact XML subtype tags from EM, but we can output per-bucket counts
    counts["__EM_BUCKET__walls"]  = len(surfs.get("walls", []) or [])
    counts["__EM_BUCKET__roofs"]  = len(surfs.get("roofs", []) or [])
    counts["__EM_BUCKET__floors"] = len(surfs.get("floors", []) or [])

    # Openings
    openings = (em.get("geometry", {}) or {}).get("openings", {}) or {}
    counts["Window"]   = len(openings.get("windows", []) or [])
    counts["Door"]     = len(openings.get("doors", []) or [])
    counts["Skylight"] = len(openings.get("skylights", []) or [])

    # DHW systems (example parity metric)
    dhw = (em.get("systems", {}) or {}).get("dhw", em.get("dhw_systems", [])) or []
    counts["DHW_SYSTEMS"] = len(dhw)

    return counts

# ---- Apply multipliers on EM side (effective_multiplier at zone level) ----
def em_zone_effective_multiplier_map(em: Dict[str, Any]) -> Dict[str, int]:
    eff: Dict[str, int] = {}
    for z in (em.get("geometry", {}) or {}).get("zones", []) or []:
        name = (z.get("name") or z.get("id") or "").strip()
        if not name:
            continue
        eff[name.lower()] = int(z.get("effective_multiplier") or 1)
    return eff

def _sum_multiplied_surfaces_em(em: Dict[str, Any]) -> Dict[str, int]:
    """Return multiplied counts per bucket for EM: we multiply each surface instance
       by its parent zone effective_multiplier. Buckets only (walls/roofs/floors)."""
    eff = em_zone_effective_multiplier_map(em)
    res = {"walls": 0, "roofs": 0, "floors": 0}
    surfs = (em.get("geometry", {}) or {}).get("surfaces", {}) or {}
    for bucket in ("walls", "roofs", "floors"):
        for s in surfs.get(bucket, []) or []:
            zref = (s.get("parent_zone_ref") or "").strip().lower()
            res[bucket] += eff.get(zref, 1)
    return res

def _sum_multiplied_openings_em(em: Dict[str, Any]) -> Dict[str, int]:
    eff = em_zone_effective_multiplier_map(em)
    res = {"windows": 0, "doors": 0, "skylights": 0}
    openings = (em.get("geometry", {}) or {}).get("openings", {}) or {}
    for k in ("windows", "doors", "skylights"):
        for o in openings.get(k, []) or []:
            # try to read parent surface -> zone; if not available, default to 1
            zref = (o.get("parent_zone_ref") or "").strip().lower()
            res[k] += eff.get(zref, 1)
    return res

# ---- Main “quick check” comparer ------------------------------------------------
def compare_counts_detailed(root: ET.Element, em: Dict[str, Any]) -> Dict[str, Any]:
    """
    Returns a nested dict with:
      - per_tag: raw XML counts by tag; EM “bucket” counts + per-tag openings, zones
      - per_bucket: XML & EM raw + multiplied (using the same SURFACE_BUCKETS)
      - summary: a compact summary matching the old quick table but now consistent
    """
    # XML raw per-tag
    xml_tags_raw = xml_per_tag_counts(root)
    # XML multiplied per-bucket (zones only under ResZn)
    xml_eff = xml_zone_effective_multiplier_map(root)
    xml_multiplied = {"walls": 0, "roofs": 0, "floors": 0}
    # XML multiplied per-bucket (surfaces)
    xml_eff = xml_zone_effective_multiplier_map(root)
    xml_multiplied = {"walls": 0, "roofs": 0, "floors": 0}
    for rz in root.findall(".//ResZn"):
        zname = _x_txt(rz, "Name") or rz.get("Name") or rz.get("id")
        if not zname: continue
        zkey = zname.strip().lower()
        mul = xml_eff.get(zkey, 1)
        for bucket, tagset in SURFACE_BUCKETS.items():
            for t in tagset:
                cnt = len(rz.findall(f"./{t}"))
                if cnt: xml_multiplied[bucket] += cnt * mul

    # ---------- NEW: XML multiplied openings ----------
    xml_openings_multiplied = {"windows": 0, "doors": 0, "skylights": 0}
    _OPEN_WIN = ("ResWin", "ComWin", "Window")
    _OPEN_DOR = ("Door",)
    _OPEN_SKY = ("Skylight",)

    _SURF_FOR_OPENINGS = (
        list(SURFACE_BUCKETS["walls"]) +
        ["ResRoof", "ComRoof", "ResCeiling", "ComCeiling", "ResCathedralCeiling"]
    )
    for rz in root.findall(".//ResZn"):
        zname = _x_txt(rz, "Name") or rz.get("Name") or rz.get("id")
        if not zname: continue
        zkey = zname.strip().lower()
        mul = xml_eff.get(zkey, 1)

        for surf_tag in _SURF_FOR_OPENINGS:
            for surf in rz.findall(f"./{surf_tag}"):
                # windows
                for t in _OPEN_WIN:
                    xml_openings_multiplied["windows"] += len(surf.findall(f".//{t}")) * mul
                # doors
                for t in _OPEN_DOR:
                    xml_openings_multiplied["doors"] += len(surf.findall(f".//{t}")) * mul
                # skylights
                for t in _OPEN_SKY:
                    xml_openings_multiplied["skylights"] += len(surf.findall(f".//{t}")) * mul


    # EM side (raw + multiplied)
    em_tags_raw = em_per_tag_counts(em)
    em_multiplied = _sum_multiplied_surfaces_em(em)
    em_openings_mult = _sum_multiplied_openings_em(em)

    # Build bucket raw (XML) by grouping per-tag counts
    xml_bucket_raw = { "walls": 0, "roofs": 0, "floors": 0 }
    for bucket, tagset in SURFACE_BUCKETS.items():
        xml_bucket_raw[bucket] = sum(xml_tags_raw.get(t, 0) for t in tagset)

    # Build EM raw by buckets (we already computed as __EM_BUCKET__*)
    em_bucket_raw = {
        "walls": em_tags_raw.get("__EM_BUCKET__walls", 0),
        "roofs": em_tags_raw.get("__EM_BUCKET__roofs", 0),
        "floors": em_tags_raw.get("__EM_BUCKET__floors", 0),
    }

    # Summary rows (match your table and extend)
    summary_rows = [
        {"metric": "zones",
         "em_raw": em_tags_raw.get("ResZn", 0) + em_tags_raw.get("ResOtherZn", 0),
         "xml_raw": xml_tags_raw.get("ResZn", 0) + xml_tags_raw.get("ResOtherZn", 0)},
        {"metric": "walls", "em_raw": em_bucket_raw["walls"], "xml_raw": xml_bucket_raw["walls"],
         "em_mult": em_multiplied["walls"], "xml_mult": xml_multiplied["walls"]},
        {"metric": "roofs", "em_raw": em_bucket_raw["roofs"], "xml_raw": xml_bucket_raw["roofs"],
         "em_mult": em_multiplied["roofs"], "xml_mult": xml_multiplied["roofs"]},
        {"metric": "floors", "em_raw": em_bucket_raw["floors"], "xml_raw": xml_bucket_raw["floors"],
         "em_mult": em_multiplied["floors"], "xml_mult": xml_multiplied["floors"]},
        {"metric": "windows", "em_raw": em_tags_raw.get("Window", 0),
         "xml_raw": xml_tags_raw.get("ResWin", 0) + xml_tags_raw.get("ComWin", 0) + xml_tags_raw.get("Window", 0),
         "em_mult": em_openings_mult["windows"], "xml_mult": xml_openings_multiplied["windows"]},
        {"metric": "doors", "em_raw": em_tags_raw.get("Door", 0), "xml_raw": xml_tags_raw.get("Door", 0),
         "em_mult": em_openings_mult["doors"], "xml_mult": xml_openings_multiplied["doors"]},
        {"metric": "skylights", "em_raw": em_tags_raw.get("Skylight", 0), "xml_raw": xml_tags_raw.get("Skylight", 0),
         "em_mult": em_openings_mult["skylights"], "xml_mult": xml_openings_multiplied["skylights"]},
        {"metric": "dhw_systems", "em_raw": em_tags_raw.get("DHW_SYSTEMS", 0), "xml_raw": None},
    ]

    return {
        "per_tag": {
            "xml_raw": xml_tags_raw,
            "em_raw_proxy": em_tags_raw,   # EM doesn’t preserve exact XML tags for surfaces
        },
        "per_bucket": {
            "xml_raw": xml_bucket_raw,
            "xml_multiplied": xml_multiplied,
            "em_raw": em_bucket_raw,
            "em_multiplied": em_multiplied,
        },
        "summary": summary_rows,
        "taxonomy": {
            "SURFACE_BUCKETS": {k: sorted(list(v)) for k, v in SURFACE_BUCKETS.items()},
            "OPENING_TAGS": sorted(list(OPENING_TAGS)),
            "ZONE_TAGS": sorted(list(ZONE_TAGS)),
        }
    }
