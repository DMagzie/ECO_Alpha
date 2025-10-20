from __future__ import annotations
from typing import Dict, Optional
from pathlib import Path
import csv
import re
import xml.etree.ElementTree as ET

# Where to look for the ZIP→CZ CSV
CANDIDATE_FILES = [
    Path(__file__).resolve().parents[1] / "explorer_gui" / "assets" / "zip_to_cz.csv",
    Path(__file__).resolve().parents[1] / "assets" / "zip_to_cz.csv",
]

# Accept a few different header pairs
CANDIDATE_COLUMNS = [
    ("zip", "cz"),
    ("zipcode", "cz"),
    ("postal_code", "cz"),
    ("zip", "climate_zone"),
    ("zipcode", "climate_zone"),
    ("postal_code", "climate_zone"),
]

_CACHE: Optional[Dict[str, str]] = None


def _norm_zip(z: str) -> str:
    """Return 5-digit zero-padded ZIP from any input like '94102-1234' -> '94102'."""
    digits = "".join(re.findall(r"\d", str(z)))[:5]
    return digits.zfill(5) if digits else ""


def normalize_cz(cz: str) -> str:
    """
    Normalize any CZ-ish input into 'CZ##':
      '3' -> 'CZ03', '03' -> 'CZ03', 'cz-3' -> 'CZ03', 'Climate Zone 3' -> 'CZ03'
      Already-normalized values ('CZ03') are returned as-is.
    """
    s = str(cz).strip().upper()
    if re.fullmatch(r"CZ\d{2}", s):
        return s
    digits = "".join(re.findall(r"\d", s))
    return f"CZ{digits.zfill(2)}" if digits else ""


def _load_table() -> Dict[str, str]:
    """Load the ZIP→CZ table from CSV (first file that matches, flexible headers)."""
    table: Dict[str, str] = {}
    for p in CANDIDATE_FILES:
        if not p.exists():
            continue
        with p.open("r", encoding="utf-8") as f:
            r = csv.DictReader(f)
            headers = [h.lower().strip() for h in (r.fieldnames or [])]
            zip_col = cz_col = None
            for a, b in CANDIDATE_COLUMNS:
                if a in headers and b in headers:
                    zip_col, cz_col = a, b
                    break
            if not zip_col:
                continue
            for row in r:
                z = _norm_zip(row.get(zip_col, ""))
                c = normalize_cz(row.get(cz_col, ""))
                if z and c:
                    table[z] = c
        if table:
            break
    return table


def get_table() -> Dict[str, str]:
    global _CACHE
    if _CACHE is None:
        _CACHE = _load_table()
    return _CACHE


def cz_for_zip(zip_code: str) -> Optional[str]:
    z = _norm_zip(zip_code)
    if not z:
        return None
    return get_table().get(z)


# -------- XML helpers (so panels can read ZIP/CZ straight from cibd22x) --------

def find_zip_in_xml(xml_text: str) -> Optional[str]:
    """
    Search for ZIP/postal code in common attributes/elements within the XML.
    Returns a normalized 5-digit ZIP or None.
    """
    try:
        root = ET.fromstring(xml_text)
    except Exception:
        return None

    # Attributes first
    for el in root.iter():
        for k, v in el.attrib.items():
            lk = k.lower()
            if ("zip" in lk) or ("postal" in lk):
                z = _norm_zip(v)
                if z:
                    return z

    # Elements with text
    for el in root.iter():
        tag = el.tag.lower()
        if ("zip" in tag) or ("postal" in tag):
            z = _norm_zip(el.text or "")
            if z:
                return z

    return None


def find_cz_in_xml(xml_text: str) -> Optional[str]:
    """
    Read climate zone directly from <Building ClimateZone="..."> or a <ClimateZone> element.
    Returns normalized 'CZ##' or None.
    """
    try:
        root = ET.fromstring(xml_text)
    except Exception:
        return None

    b = root.find(".//Building")
    if b is not None:
        cz_attr = b.attrib.get("ClimateZone")
        if cz_attr:
            cz = normalize_cz(cz_attr)
            if cz:
                return cz

    for el in root.iter():
        if el.tag.lower() == "climatezone":
            cz = normalize_cz(el.text or "")
            if cz:
                return cz

    return None
