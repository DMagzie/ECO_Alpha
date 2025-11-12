"""
CIBD22 Translator Module - Text format adaptation of CIBD22X parser
"""

from .importer import CIBD22Importer

__all__ = ['CIBD22Importer', 'translate_cibd22_to_v6']


def translate_cibd22_to_v6(text_file: str):
    """
    Translate CIBD22 text file to EMJSON v6 format.

    Uses modular architecture:
    1. Text parser converts CIBD22 text → XML structure
    2. CIBD22X modular parsers process XML → InternalRepresentation
    3. Convert to EMJSON v6 format

    Args:
        text_file: Path to CIBD22 text file

    Returns:
        dict: EMJSON v6 dictionary with diagnostics
    """
    try:
        from dataclasses import asdict

        importer = CIBD22Importer()
        internal = importer.import_file(text_file)

        # Convert InternalRepresentation to EMJSON v6 with nested structure
        emjson = {
            "schema_version": "6.0",
            "project": {
                "name": internal.metadata.get("name", internal.proj_metadata.get("name", "Unnamed Project")),
                "description": internal.metadata.get("description", ""),
                "location": internal.metadata.get("location", {}),
            },
            "geometry": {
                "zones": [asdict(z) for z in internal.zones],
                "zone_groups": [asdict(zg) for zg in internal.zone_groups],
                "surfaces": [asdict(s) for z in internal.surfaces],
                "openings": [asdict(o) for o in internal.openings],
            },
            "catalogs": {
                "materials": [asdict(m) for m in internal.materials],
                "constructions": [asdict(c) for c in internal.constructions],
                "window_types": [asdict(w) for w in internal.window_types],
                "schedules": [asdict(s) for s in internal.schedules],
                "du_types": internal.du_types,
            },
            "systems": {
                "hvac": [asdict(h) for h in internal.hvac_systems],
                "zone_terminals": [asdict(t) for t in internal.zone_terminals],
                "dhw": [asdict(d) for d in internal.dhw_systems],
                "water_heaters": [asdict(wh) for wh in internal.water_heaters],
                "recirculation_loops": [asdict(r) for r in internal.recirculation_loops],
                "iaq_fans": [asdict(f) for f in internal.iaq_fans],
                "pv_arrays": [asdict(p) for p in internal.pv_arrays],
                "battery_systems": [asdict(b) for b in internal.battery_systems],
                "lighting_systems": [asdict(ls) for ls in internal.lighting_systems],
                "luminaires": [asdict(l) for l in internal.luminaires],
                "fan_systems": [asdict(fs) for fs in internal.fan_systems],
                "heat_pumps": [asdict(hp) for hp in internal.heat_pumps],
                "distribution_systems": [asdict(ds) for ds in internal.distribution_systems],
                "control_systems": [asdict(cs) for cs in internal.control_systems],
            },
            "proj_metadata": internal.proj_metadata,
            "diagnostics": internal.diagnostics
        }

        return emjson
    except Exception as e:
        import traceback
        # Return error in EMJSON format
        return {
            "schema_version": "6.0",
            "diagnostics": [{
                "level": "error",
                "code": "E-IMPORT-FAILED",
                "message": f"CIBD22 import failed: {str(e)}",
                "stage": "import",
                "ts": "",
                "path": text_file,
                "context": traceback.format_exc(),
                "source": "cibd22_importer"
            }]
        }
