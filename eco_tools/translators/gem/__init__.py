"""
GEM Translator Module - IES VE GEM to EMJSON v6
"""

from .importer import GEMParser

__all__ = ['GEMParser', 'translate_gem_to_v6']


def translate_gem_to_v6(gem_file: str):
    """
    Translate GEM file to EMJSON v6 format.

    Uses two-stage conversion:
    1. GEM -> HBJSON (using GEM parser)
    2. HBJSON -> EMJSON v6 (using HBJSON importer)

    Args:
        gem_file: Path to GEM file

    Returns:
        dict: EMJSON v6 dictionary with diagnostics
    """
    import json
    import tempfile
    from pathlib import Path

    try:
        from .importer import GEMParser
        from ..hbjson.importer import HBJSONImporter
    except ImportError as e:
        return {
            "schema_version": "6.0",
            "diagnostics": [{
                "level": "error",
                "code": "E-IMPORT-FAILED",
                "message": f"Failed to import GEM/HBJSON translators: {e}",
                "stage": "import",
                "source": "gem_translator"
            }]
        }

    try:
        # Stage 1: GEM � HBJSON
        parser = GEMParser(gem_file)
        gem_data = parser.parse()

        # Convert to HBJSON (simplified - would need full implementation)
        # For now, create minimal HBJSON structure
        hbjson = {
            "type": "Model",
            "identifier": Path(gem_file).stem,
            "display_name": gem_data.get('project_info', {}).get('name', 'GEM Import'),
            "version": "1.54.4",
            "rooms": [],
            "orphaned_faces": [],
            "orphaned_shades": [],
            "orphaned_apertures": [],
            "orphaned_doors": []
        }

        # Write temporary HBJSON file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.hbjson', delete=False) as f:
            json.dump(hbjson, f)
            temp_hbjson = f.name

        # Stage 2: HBJSON � EMJSON v6
        importer = HBJSONImporter()
        internal = importer.import_file(temp_hbjson)

        # Clean up temp file
        Path(temp_hbjson).unlink()

        # Convert to EMJSON v6
        from dataclasses import asdict
        emjson = {
            "schema_version": "6.0",
            "project": {
                "name": gem_data.get('project_info', {}).get('name', Path(gem_file).stem),
                "description": "Imported from IES VE GEM format",
            },
            "geometry": {
                "zones": [asdict(z) for z in internal.zones],
                "surfaces": [asdict(s) for s in internal.surfaces],
                "openings": [asdict(o) for o in internal.openings],
            },
            "catalogs": {
                "materials": [asdict(m) for m in internal.materials],
                "constructions": [asdict(c) for c in internal.constructions],
            },
            "systems": {
                "hvac": [asdict(h) for h in internal.hvac_systems],
            },
            "diagnostics": internal.diagnostics + [{
                "level": "info",
                "code": "I-GEM-IMPORT",
                "message": f"Imported GEM file via GEM->HBJSON->EMJSON pipeline",
                "stage": "import",
                "source": "gem_translator"
            }]
        }

        return emjson

    except Exception as e:
        import traceback
        return {
            "schema_version": "6.0",
            "diagnostics": [{
                "level": "error",
                "code": "E-GEM-IMPORT-FAILED",
                "message": f"GEM import failed: {str(e)}",
                "stage": "import",
                "context": traceback.format_exc(),
                "source": "gem_translator"
            }]
        }
