# cbecc/translate_cibd22x_to_v6.py
# Alpha v6 Translator – robust/compatible (patched to add detailed counts comparison)

from __future__ import annotations
from typing import Any, Dict, List, Tuple, Optional
from xml.etree import ElementTree as ET
from collections import defaultdict
import json

WRITE_ALIAS_DU_MULTIPLIER = False
WRITE_METRICS_MIRROR = False

# ---------------- Detailed counts (shared taxonomy) ----------------
try:
    from cbecc.mapping_cleanup import compare_counts_detailed, SURFACE_BUCKETS  # unified mapping + comparer
except Exception as _e:
    compare_counts_detailed = None  # type: ignore
    SURFACE_BUCKETS = None  # type: ignore

# ---------- Catalogs ----------
try:
    from .parsers_catalogs import (
        parse_du_types,
        parse_window_types,
        parse_construction_types,
        parse_project_extras,
    )
except ImportError:
    from cbecc.parsers_catalogs import (  # type: ignore
        parse_du_types,
        parse_window_types,
        parse_construction_types,
        parse_project_extras,
    )

# ---------- Zones / geometry ----------
try:
    from .parsers_zones import (
        parse_zone_groups_and_levels,
        parse_zones,
        parse_surfaces,
        parse_geometry_metrics_annotations,
        parse_openings,
        parse_story_levels,
    )
except ImportError:
    from cbecc.parsers_zones import (  # type: ignore
        parse_zone_groups_and_levels,
        parse_zones,
        parse_surfaces,
        parse_geometry_metrics_annotations,
        parse_openings,
        parse_story_levels,
    )

# ---------- Systems (module + flexible callables) ----------
try:
    from . import parsers_systems as _sys
except ImportError:
    import cbecc.parsers_systems as _sys  # type: ignore

def _missing_factory(mod_name: str, names: Tuple[str, ...]):
    def _missing(*_a, **_kw):
        return [{
            "level": "warning",
            "code": "W-MISSING-FN",
            "message": f"Missing parser function; expected one of {names} in {mod_name}",
        }]
    return _missing

def _pick_callable(mod, *names: str):
    for n in names:
        fn = getattr(mod, n, None)
        if callable(fn):
            return fn
    return _missing_factory(getattr(mod, "__name__", "parsers_systems"), names)

parse_hvac_systems = _pick_callable(_sys, "parse_hvac_systems", "parse_hvac", "parse_hvac_catalog", "parse_systems")
parse_iaq_catalog = _pick_callable(_sys, "parse_iaq_catalog", "parse_iaq", "parse_ventilation_catalog")
parse_dhw_catalog = _pick_callable(_sys, "parse_dhw_catalog", "parse_dhw", "parse_water_heating_catalog")
build_simplified_catalogs_from_full_systems = _pick_callable(
    _sys,
    "build_simplified_catalogs_from_full_systems",
    "build_simplified_catalogs",
    "build_simplified",
)
enrich_dhw_systems = getattr(_sys, "enrich_dhw_systems", lambda em, diags: None)

# ---------- Cleanup / summarization ----------
try:
    from .mapping_cleanup import (
        ensure_shell_v6,
        collect_all_tags,
        mark_used,
        hvac_dedupe_raw_fields,
        hvac_finalize_cleanup,
        summarize_counts,
        summarize_unused_tags,
        diag,
    )
except ImportError:
    from cbecc.mapping_cleanup import (  # type: ignore
        ensure_shell_v6,
        collect_all_tags,
        mark_used,
        hvac_dedupe_raw_fields,
        hvac_finalize_cleanup,
        summarize_counts,
        summarize_unused_tags,
        diag,
    )

# ---------- Detailed counts comparison (XML vs EM) ----------
try:
    from .mapping_cleanup import compare_counts_detailed
except ImportError:
    from cbecc.mapping_cleanup import compare_counts_detailed  # type: ignore

__all__ = ["translate_cibd22x_to_v6"]

# ---------- Local helpers ----------
def _txt(node: ET.Element, tag: str) -> Optional[str]:
    el = node.find(tag)
    return (el.text or "").strip() if el is not None and el.text is not None else None

def _to_int(val: Any, default: int = 1) -> int:
    try:
        s = str(val).strip()
        if s == "":
            return default
        return int(float(s))
    except Exception:
        return default

def _extend_diags_if(diags: List[Dict[str, Any]], ret: Any) -> None:
    if not isinstance(ret, list) or not ret:
        return
    sample = ret[0]
    if isinstance(sample, dict) and {"level", "code", "message"} <= set(sample.keys()):
        diags.extend(ret)

# ---------- DU-per-zone usage ----------
def _collect_du_zone_usage(root: ET.Element) -> Dict[str, Dict[str, int]]:
    usage: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for rz in root.findall(".//ResZn"):
        zname = _txt(rz, "Name") or rz.get("Name") or _txt(rz, "ZnName") or rz.get("id")
        if not zname:
            continue
        zkey = zname.lower()
        for du in rz.findall("./DwellUnit"):
            du_type = _txt(du, "DwellUnitTypeRef") or du.get("DwellUnitTypeRef")
            if not du_type:
                continue
            cnt = _to_int(_txt(du, "Count") or du.get("Count") or 1, 1)
            usage[zkey][du_type] += cnt
            try:
                mark_used("ResZn", "DwellUnit", "DwellUnitTypeRef", "Count")
            except Exception:
                pass
    return usage

def _inject_zone_multipliers(root: ET.Element, em: Dict[str, Any]) -> Tuple[int, int, int]:
    """
    Namespace-agnostic zone multiplier injection supporting ResZn and ComZn.
    """
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

    du_usage = _collect_du_zone_usage(root)
    zones: List[Dict[str, Any]] = (em.get("geometry") or {}).setdefault("zones", [])

    # Build xml_by_name mapping from both ResZn and ComZn (and synonyms)
    xml_by_name: Dict[str, ET.Element] = {}
    for zn in (el for el in root.iter() if _lt(el.tag) in ("ResZn","ComZn","Zone","Space","Zn")):
        nm = (_child_text_local(zn, "Name","ZnName","ZoneName","ID","Id") or zn.get("Name") or zn.get("id"))
        if nm:
            xml_by_name[nm] = zn
            xml_by_name.setdefault(str(nm).lower(), zn)

    n_zm = n_dcz = n_eff = 0
    for z in zones:
        name = str(z.get("name") or z.get("id") or "")
        if not name:
            continue
        zn_node = xml_by_name.get(name) or xml_by_name.get(name.lower())
        if zn_node is None:
            continue

        # zone multiplier from (ZnMult|Mult|Count) text or attributes
        z_mult_txt = (_child_text_local(zn_node, "ZnMult","Mult","Count") or
                      zn_node.get("ZnMult") or zn_node.get("Mult") or zn_node.get("Count"))
        try:
            z_mult = int(str(z_mult_txt).strip()) if z_mult_txt is not None else 1
        except Exception:
            z_mult = 1

        # DU count (if residential); otherwise 1
        dcz = z.get("du_count_in_zone")
        if dcz is None:
            # try XML
            du_xml = du_usage.get(name) or du_usage.get(name.lower())
            dcz = int(du_xml) if isinstance(du_xml, int) else 1
        else:
            try:
                dcz = int(dcz)
            except Exception:
                dcz = 1

        eff = max(1, int(z_mult) * int(dcz))
        if z.get("zone_multiplier") != z_mult:
            z["zone_multiplier"] = z_mult
            n_zm += 1
        if z.get("du_count_in_zone") != dcz:
            z["du_count_in_zone"] = dcz
            n_dcz += 1
        if z.get("effective_multiplier") != eff:
            z["effective_multiplier"] = eff
            n_eff += 1

        # Provenance block
        z["multiplier"] = {
            "effective": int(eff),
            "factors": [
                {"name": "du_count_in_zone", "value": int(dcz), "flat_path": "ResZn/DwellUnit/Count"},
                {"name": "zone_multiplier", "value": int(z_mult), "flat_path": "ResZn/ZnMult|Mult|Count"}
            ],
            "base_quantity": 1,
            "applies_to": ["counts","areas"]
        }

        if WRITE_METRICS_MIRROR:
            mm = z.setdefault("metrics", {}).setdefault("multipliers", {})
            mm["du_type_ref"] = z.get("du_type_ref")
            mm["du_count_in_zone"] = int(dcz)
            mm["zone_multiplier"] = int(z_mult)
            mm["effective_multiplier"] = int(eff)

    return n_zm, n_dcz, n_eff
def translate_cibd22x_to_v6(xml_text: str) -> Dict[str, Any]:
    root = ET.fromstring(xml_text)
    collect_all_tags(root)

    em = ensure_shell_v6()
    diags: List[Dict[str, Any]] = em["diagnostics"]

    # Project basics
    proj = root.find(".//Proj") or root.find(".//Project")
    if proj is not None:
        az = (proj.findtext("BldgAz") or "").strip()
        if az:
            try:
                em["project"]["location"]["building_azimuth_deg"] = float(az)
                mark_used("Proj", "BldgAz")
            except Exception:
                pass
        city = (proj.findtext("City") or "").strip()
        state = (proj.findtext("State") or "").strip()
        if city or state:
            em["project"]["location"]["city"] = city or None
            em["project"]["location"]["state"] = state or None
            mark_used("City", "State")

    _extend_diags_if(diags, parse_project_extras(root, em))

    # Catalogs
    du_index, du_list, du_diag = parse_du_types(root)
    em["catalogs"]["du_types"] = du_list
    _extend_diags_if(diags, du_diag)
    _extend_diags_if(diags, parse_window_types(root, em))
    _extend_diags_if(diags, parse_construction_types(root, em))

    # Geometry skeleton
    levels, zone_to_group, zone_groups, lvl_diag = parse_zone_groups_and_levels(root)
    em["geometry"]["levels"] = levels
    em["geometry"]["zone_groups"] = zone_groups
    _extend_diags_if(diags, lvl_diag)

    _extend_diags_if(diags, parse_zones(root, em, du_index, zone_to_group))
    _extend_diags_if(diags, parse_geometry_metrics_annotations(root, em))

    # --- Multipliers BEFORE surfaces/openings (so effective_area_ft2 is populated) ---
    try:
        n_zm, n_dcz, n_eff = _inject_zone_multipliers(root, em)
        diags.append(diag("info", "I-MULT",
                          f"zone_multiplier>1: {n_zm}; du_count_in_zone>1: {n_dcz}; effective_multiplier>1: {n_eff}"))
    except Exception as e:
        diags.append(diag("warning", "W-MULT", f"Failed to inject multipliers: {e}"))

    # Surfaces & Openings (now see multipliers)
    _extend_diags_if(diags, parse_surfaces(root, em))
    _extend_diags_if(diags, parse_openings(root, em))
    _extend_diags_if(diags, parse_story_levels(root, em))

    # Systems
    _extend_diags_if(diags, parse_hvac_systems(root, em))
    _extend_diags_if(diags, parse_iaq_catalog(root, em))
    _extend_diags_if(diags, parse_dhw_catalog(root, em))

    try:
        enrich_dhw_systems(em, diags)  # no-op if not provided
    except Exception as e:
        diags.append(diag("warning", "W-DHW-ENRICH", f"DHW enrichment skipped: {e}"))

    _extend_diags_if(diags, build_simplified_catalogs_from_full_systems(em))

    # -------- Detailed counts comparison (XML vs EM, raw & multiplied) --------
    try:
        counts_detail = compare_counts_detailed(root, em)
        em.setdefault("summaries", {})["counts_detailed"] = counts_detail
        diags.append(diag("info", "I-COUNTS-COMPARISON", "Detailed counts added to summaries.counts_detailed"))
    except Exception as e:
        diags.append(diag("warning", "W-COUNTS-COMPARISON", f"Counts comparison failed: {e}"))

    # Finalize HVAC & summaries
    hvac_dedupe_raw_fields(em, diags)
    hvac_finalize_cleanup(em, diags)
    diags.append(summarize_counts(em))
    diags.append(summarize_unused_tags())
    return em

if __name__ == "__main__":
    import sys, pathlib
    if len(sys.argv) < 2:
        print("Usage: python translate_cibd22x_to_v6.py <input.cibd22x or .xml>")
        raise SystemExit(2)
    p = pathlib.Path(sys.argv[1])
    xml_text = p.read_text(encoding="utf-8", errors="ignore")
    out = translate_cibd22x_to_v6(xml_text)
    out_path = p.with_suffix(".em_v6.json")
    out_path.write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Wrote {out_path}")
