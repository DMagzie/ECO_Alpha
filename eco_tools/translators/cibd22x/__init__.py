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
            "surfaces": [asdict(s) for s in internal.surfaces],
            "openings": [asdict(o) for o in internal.openings],
            "hvac_systems": [asdict(h) for h in internal.hvac_systems],
            "zone_terminals": [asdict(t) for t in internal.zone_terminals],
            "constructions": [asdict(c) for c in internal.constructions],
            "construction_layers": [asdict(l) for l in internal.construction_layers],
            "materials": [asdict(m) for m in internal.materials],
            "schedules": [asdict(s) for s in internal.schedules],
            "window_types": [asdict(w) for w in internal.window_types],
            "project": asdict(internal.project) if internal.project else {},
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
