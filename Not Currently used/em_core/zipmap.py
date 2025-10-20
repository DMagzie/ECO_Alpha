# em_core/zipmap.py
from __future__ import annotations
from pathlib import Path
from typing import Dict, Tuple, Optional
import csv, os, re
from .cz import canon_cz

# Search order (earlier wins). You can add more paths here if needed.
_DEFAULT_SEARCH: Tuple[Path, ...] = (
    Path("explorer_gui/assets/zip_to_cz.csv"),
    Path("explorer_gui/assets/zip_climate_zone.csv"),
    Path("explorer_gui/assets/zip_to_cz.csv"),
    Path("assets/zip_climate_zone.csv"),
)

# Environment override (use an absolute or relative path)
_ENV_KEY = "EM_ZIP_CZ_PATH"

_cache_map: Optional[Dict[str, str]] = None
_cache_path: Optional[Path] = None

def _normalize_zip(s: str | None) -> Optional[str]:
    if not isinstance(s, str): return None
    m = re.search(r"\b(\d{5})(?:-\d{4})?\b", s)
    return m.group(1) if m else None

def pick_zip_map_file() -> Optional[Path]:
    # Env override first
    env = os.environ.get(_ENV_KEY)
    if env:
        p = Path(env).expanduser()
        if p.exists():
            return p
    # Then search defaults in order
    for p in _DEFAULT_SEARCH:
        if p.exists():
            return p
    return None

def load_zip_cz_map(path: Optional[Path] = None) -> Tuple[Dict[str, str], Optional[Path]]:
    """Return (map, path). Caches the first successful load."""
    global _cache_map, _cache_path
    if _cache_map is not None and _cache_path is not None:
        return _cache_map, _cache_path

    src = path or pick_zip_map_file()
    if not src or not src.exists():
        _cache_map, _cache_path = {}, None
        return _cache_map, _cache_path

    zmap: Dict[str, str] = {}
    with src.open("r", encoding="utf-8") as f:
        rdr = csv.DictReader(f)
        for row in rdr:
            z = _normalize_zip(row.get("zip") or row.get("zipcode") or row.get("postal"))
            cz = (row.get("climate_zone") or row.get("cz") or "").strip()
            if z and cz:
                zmap[z] = canon_cz(cz) or cz
    _cache_map, _cache_path = zmap, src
    return zmap, src

def lookup_cz_for_zip(zip_str: str | None) -> Optional[str]:
    """Return canonical CZ for a ZIP (e.g., 'CZ03') or None."""
    z = _normalize_zip(zip_str)
    if not z:
        return None
    mp, _ = load_zip_cz_map()
    return mp.get(z)
