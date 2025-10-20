# em_core/cz.py
from __future__ import annotations
from pathlib import Path
from typing import Tuple, Dict, List, Optional
import functools, re, csv
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
HERE = Path(__file__).resolve().parent

# Where we’ll search for a ZIP→CZ CSV
ZIP_MAP_PREFS: List[Path] = [
    ROOT / "explorer_gui" / "assets" / "zip_to_cz.csv",
    ROOT / "assets" / "zip_to_cz.csv",
    HERE / "assets" / "zip_to_cz.csv",
    ROOT / "explorer_gui" / "assets" / "zip_climate_zone.csv",
    ROOT / "assets" / "zip_climate_zone.csv",
    HERE / "assets" / "zip_climate_zone.csv",
]

def canon_cz(v) -> Optional[str]:
    """Normalize '3', 'CZ3', 'cz03' -> 'CZ03'. Leave other labels (e.g., 'T24-CZ03') unchanged."""
    if v is None: return None
    s = str(v).strip()
    if not s: return None
    m = re.match(r'^(?:cz\s*)?(\d{1,2})$', s, re.IGNORECASE)
    if m:
        return f"CZ{int(m.group(1)):02d}"
    return s

def apply_cz_to_model(m: dict, cz_raw) -> None:
    """Write CZ to all canonical slots in-place."""
    cz = canon_cz(cz_raw) or ""
    proj = dict(m.get("project") or {})
    loc  = dict(proj.get("location") or {})
    m["climate_zone"] = cz
    m["climate"] = cz
    proj["climate_zone"] = cz
    loc["climate_zone"] = cz
    proj["location"] = loc
    m["project"] = proj

def ensure_cz_canonical(m: dict) -> dict:
    """Mirror any CZ found to canonical slots."""
    proj = m.get("project") or {}
    loc  = isinstance(proj, dict) and (proj.get("location") or {}) or {}
    cz = m.get("climate_zone") or m.get("climate") \
        or (isinstance(proj, dict) and proj.get("climate_zone")) \
        or (isinstance(loc, dict) and loc.get("climate_zone"))
    if cz:
        apply_cz_to_model(m, cz)
    return m

def _normalize_zip(s: Optional[str]) -> Optional[str]:
    if not isinstance(s, str): return None
    m = re.search(r"\b(\d{5})(?:-\d{4})?\b", s)
    return m.group(1) if m else None

def extract_zip_from_xml(xml_text: str) -> Optional[str]:
    try:
        root = ET.fromstring(xml_text)
    except Exception:
        return _normalize_zip(xml_text)
    # attributes on common nodes
    for p in ("./Building", ".//Building", ".//Site", ".//Location", ".//Address"):
        el = root.find(p)
        if el is None: continue
        for attr in ("Zip", "ZIP", "PostalCode", "Postal", "PostCode", "postcode", "zip", "postalCode"):
            z = _normalize_zip(el.attrib.get(attr))
            if z: return z
    # element text
    for p in (".//ZIP", ".//Zip", ".//PostalCode", ".//PostCode", ".//AddressPostalCode"):
        el = root.find(p)
        if el is not None and el.text:
            z = _normalize_zip(el.text)
            if z: return z
    return _normalize_zip(xml_text)

def extract_climate_zone_from_xml(xml_text: str) -> Tuple[Optional[str], Optional[str]]:
    try:
        root = ET.fromstring(xml_text)
        # Building attributes
        for path in ("./Building", ".//Building"):
            b = root.find(path)
            if b is not None:
                for attr in ("ClimateZone", "climateZone", "Zone", "CZ"):
                    v = b.attrib.get(attr)
                    if isinstance(v, str) and v.strip():
                        return v.strip(), f"{path}[@{attr}]"
        # Dedicated elements
        for p in (".//ClimateZone", ".//Climate", ".//Weather", ".//Location"):
            el = root.find(p)
            if el is not None:
                for attr in ("Zone", "ClimateZone", "ID", "Name", "Value"):
                    v = el.attrib.get(attr)
                    if isinstance(v, str) and v.strip():
                        return v.strip(), f"{p}[@{attr}]"
                if isinstance(el.text, str) and el.text.strip():
                    return el.text.strip(), f"{p}[text()]"
    except Exception:
        pass
    m = re.search(r'ClimateZone\s*=\s*"([^"]+)"', xml_text, re.IGNORECASE)
    return (m.group(1).strip(), 'regex: ClimateZone="..."') if m else (None, None)

def _zip_map_candidates() -> List[Path]:
    pats = [
        "**/*zip*climate*zone*.csv",
        "**/*zip*cz*.csv",
        "**/*to*cz*.csv",
        "**/*climate*zone*.csv",
    ]
    extras: List[Path] = []
    for pat in pats:
        extras.extend(ROOT.glob(pat))
    seen, ordered = set(), []
    for p in [*ZIP_MAP_PREFS, *extras]:
        p = Path(p)
        if str(p) in seen: continue
        seen.add(str(p))
        if p.exists() and p.is_file():
            ordered.append(p)
    return ordered

def pick_zip_map_file() -> Tuple[str, float, int]:
    """Return (path, mtime, size) for cache key; ('',0,0) if none."""
    for p in _zip_map_candidates():
        try:
            st = p.stat()
            return str(p), st.st_mtime, st.st_size
        except Exception:
            return str(p), 0.0, 0
    return "", 0.0, 0

@functools.lru_cache(maxsize=8)
def load_zip_cz_map(cache_key: Tuple[str, float, int]) -> Tuple[Dict[str, str], str]:
    """Load map keyed by (path, mtime, size). Returns (map, path_str)."""
    path_str, _, _ = cache_key
    p = Path(path_str)
    out: Dict[str, str] = {}
    if p.exists():
        with p.open("r", encoding="utf-8") as f:
            rdr = csv.DictReader(f)
            for row in rdr:
                z = _normalize_zip(row.get("zip") or row.get("zipcode") or row.get("postal"))
                cz = (row.get("climate_zone") or row.get("cz") or "").strip()
                if z and cz:
                    out[z] = canon_cz(cz) or cz
    return out, str(p)

def clear_zip_map_cache() -> None:
    load_zip_cz_map.cache_clear()
