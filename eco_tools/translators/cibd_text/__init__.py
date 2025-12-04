"""
Unified CIBD Text Format Translator

Provides bidirectional translation between CIBD text formats (CIBD22, CIBD25)
and EMJSON v6.

Supported formats:
- CIBD22: Title 24 2022 text format
- CIBD25: Title 24 2025 text format

Usage:
    # Import CIBD text file to EMJSON
    from eco_tools.translators.cibd_text import translate_to_emjson
    emjson = translate_to_emjson('input.cibd22')  # or input.cibd25

    # Export EMJSON to CIBD text file
    from eco_tools.translators.cibd_text import translate_from_emjson, CIBDVersion
    translate_from_emjson(emjson, 'output.cibd25', version=CIBDVersion.CIBD25)
    translate_from_emjson(emjson, 'output.cibd22', version=CIBDVersion.CIBD22)
"""

from typing import Dict, Any, Optional
from pathlib import Path

from .version_config import CIBDVersion, detect_version_from_file
from .parser import CIBDTextParser, parse_cibd_file
from .writer import CIBDTextWriter, write_cibd_file

# Import CIBD22X importer for XML → EMJSON conversion
from ..cibd22x.importer import CIBD22XImporter

__all__ = [
    'CIBDVersion',
    'CIBDTextParser',
    'CIBDTextWriter',
    'translate_to_emjson',
    'translate_from_emjson',
    'detect_version_from_file',
]


def translate_to_emjson(
    file_path: str,
    version: CIBDVersion = None
) -> Dict[str, Any]:
    """
    Translate CIBD text file to EMJSON v6 format.

    Supports both CIBD22 and CIBD25 text formats.
    Version is auto-detected if not specified.

    Args:
        file_path: Path to CIBD text file (.cibd22 or .cibd25)
        version: Target version (auto-detected if None)

    Returns:
        EMJSON v6 dictionary with diagnostics
    """
    try:
        from dataclasses import asdict

        # Auto-detect version from file extension or content
        if version is None:
            suffix = Path(file_path).suffix.lower()
            if suffix == '.cibd22':
                version = CIBDVersion.CIBD22
            elif suffix == '.cibd25':
                version = CIBDVersion.CIBD25
            else:
                version = detect_version_from_file(file_path)

        # Stage 1: Parse text format to XML
        xml_root = parse_cibd_file(file_path, version)

        # Stage 2: Use CIBD22X importer to convert XML → InternalRepresentation
        cibd22x_importer = CIBD22XImporter()
        internal = cibd22x_importer.import_from_xml_root(xml_root)

        # Stage 3: Convert InternalRepresentation to EMJSON v6
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
                "surfaces": [asdict(s) for s in internal.surfaces],
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

        # Add source format info
        emjson['metadata'] = {
            'source_format': f'CIBD{version.value}',
            'source_file': file_path,
        }

        return emjson

    except Exception as e:
        import traceback
        return {
            "schema_version": "6.0",
            "diagnostics": [{
                "level": "error",
                "code": "E-IMPORT-FAILED",
                "message": f"CIBD import failed: {str(e)}",
                "stage": "import",
                "path": file_path,
                "context": traceback.format_exc(),
                "source": "cibd_text_importer"
            }]
        }


def translate_from_emjson(
    emjson: Dict[str, Any],
    output_path: str,
    version: CIBDVersion = CIBDVersion.CIBD25
) -> bool:
    """
    Translate EMJSON v6 to CIBD text format.

    Supports output to both CIBD22 and CIBD25 formats.

    Args:
        emjson: EMJSON v6 dictionary
        output_path: Path to output file
        version: Target version (default: CIBD25)

    Returns:
        True if successful, False otherwise
    """
    return write_cibd_file(emjson, output_path, version)


# Convenience aliases
import_cibd = translate_to_emjson
export_cibd = translate_from_emjson
