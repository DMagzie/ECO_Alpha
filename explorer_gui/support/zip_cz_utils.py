# explorer_gui/support/zip_cz_utils.py
"""
ZIP → California Title 24 climate zone utilities (UI-agnostic).
- Try to read CZ directly from XML if present.
- Otherwise, map ZIP → CZ via a lightweight fallback or a local JSON file.

If a file named `zip_to_cz_ca.json` is placed next to this module, it will be
loaded and used instead of the small fallback map below. The JSON should look like:
{
  "92009": 7,
  "92868": 8,
  ...
}
"""

from __future__ import annotations
from typing import Optional
import re
from xml.etree import ElementTree as ET

# Minimal fallback map covering current sample models (Carlsbad/Santa Ana area).
_FALLBACK_ZIP_TO_CZ = {
    "92008": 7, "92009": 7, "92010": 7, "92011": 7,
    "92701": 8, "92703": 8, "92705": 8, "92706": 8, "92707": 8,
    "92866": 8, "92867": 8, "92868": 8, "92869": 8,
}

def _load_external_map() -> dict[str, int]:
    try:
        import json, pathlib
        p = pathlib.Path(__file__).with_name("zip_to_cz_ca.json")
        if p.exists():
            raw = json.loads(p.read_text())
            out: dict[str, int] = {}
            for k, v in (raw or {}).items():
                k5 = re.sub(r"\D", "", str(k))
                if len(k5) == 5:
                    out[k5] = int(v)
            return out
    except Exception:
        pass
    return {}

_ZIP_TO_CZ = _load_external_map() or _FALLBACK_ZIP_TO_CZ

_XML_CZ_TAGS = [
    "CZ", "ClimateZone", "CECClimateZone", "CECClimateZone2019",
    "ClimateZoneCEC", "Title24ClimateZone", "CEC_CZ",
]
_XML_ZIP_TAGS = [
    "ZipCode", "ZIP", "PostalCode", "DocZipCode", "BldgZipCode",
    "ProjectPostalCode", "ProjZipCode", "Zip",
]

def _clean_zip(s: str) -> Optional[str]:
    if not s:
        return None
    m = re.search(r"(\d{5})", s)
    return m.group(1) if m else None

def find_zip_in_xml(xml_or_root) -> Optional[str]:
    try:
        root = ET.fromstring(xml_or_root) if isinstance(xml_or_root, (str, bytes)) else xml_or_root
    except Exception:
        return None
    for tag in _XML_ZIP_TAGS:
        el = root.find(f".//{tag}")
        if el is not None and el.text:
            z = _clean_zip(el.text)
            if z:
                return z
    # fallback scan
    for el in root.iter():
        if el.text:
            z = _clean_zip(el.text)
            if z:
                return z
    return None

def find_cz_in_xml(xml_or_root) -> Optional[int]:
    try:
        root = ET.fromstring(xml_or_root) if isinstance(xml_or_root, (str, bytes)) else xml_or_root
    except Exception:
        return None
    for tag in _XML_CZ_TAGS:
        el = root.find(f".//{tag}")
        if el is not None and el.text:
            try:
                val = int(re.sub(r"\D", "", el.text.strip()) or "0") or None
                if val:
                    return val
            except Exception:
                continue
    return None

def cz_for_zip(zip5: str) -> Optional[int]:
    z = _clean_zip(zip5) or ""
    if len(z) != 5:
        return None
    return _ZIP_TO_CZ.get(z)

__all__ = ["cz_for_zip", "find_zip_in_xml", "find_cz_in_xml"]
