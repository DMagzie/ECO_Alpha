"""
CIBD22X Translator Module
"""

from .importer import CIBD22XImporter

__all__ = ['CIBD22XImporter', 'translate_cibd22x_to_v6']


def translate_cibd22x_to_v6(xml_file: str):
    """
    Translate CIBD22X XML file to EMJSON v6 format.

    Args:
        xml_file: Path to CIBD22X XML file

    Returns:
        dict: EMJSON v6 dictionary with diagnostics
    """
    try:
        from dataclasses import asdict

        importer = CIBD22XImporter()
        internal = importer.import_file(xml_file)

        # Convert InternalRepresentation to EMJSON v6
        # Using simple dataclass conversion until proper converter is built
        emjson = {
            "schema_version": "6.0",
            "zones": [asdict(z) for z in internal.zones],
            "zone_groups": [asdict(zg) for zg in internal.zone_groups],
            "surfaces": [asdict(s) for s in internal.surfaces],
            "openings": [asdict(o) for o in internal.openings],
            "hvac_systems": [asdict(h) for h in internal.hvac_systems],
            "zone_terminals": [asdict(t) for t in internal.zone_terminals],
            "iaq_fans": [asdict(f) for f in internal.iaq_fans],
            "dhw_systems": [asdict(d) for d in internal.dhw_systems],
            "water_heaters": [asdict(wh) for wh in internal.water_heaters],
            "recirculation_loops": [asdict(r) for r in internal.recirculation_loops],
            "materials": [asdict(m) for m in internal.materials],
            "constructions": [asdict(c) for c in internal.constructions],
            "window_types": [asdict(w) for w in internal.window_types],
            "pv_arrays": [asdict(p) for p in internal.pv_arrays],
            "battery_systems": [asdict(b) for b in internal.battery_systems],
            "lighting_systems": [asdict(ls) for ls in internal.lighting_systems],
            "luminaires": [asdict(l) for l in internal.luminaires],
            "schedules": [asdict(s) for s in internal.schedules],
            "fan_systems": [asdict(fs) for fs in internal.fan_systems],
            "heat_pumps": [asdict(hp) for hp in internal.heat_pumps],
            "distribution_systems": [asdict(ds) for ds in internal.distribution_systems],
            "control_systems": [asdict(cs) for cs in internal.control_systems],
            "du_types": internal.du_types,
            "proj_metadata": internal.proj_metadata,
            "metadata": internal.metadata,
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
                "message": f"Import failed: {str(e)}",
                "stage": "import",
                "ts": "",
                "path": xml_file,
                "context": traceback.format_exc(),
                "source": "cibd22x_importer"
            }]
        }
