# FILE 5: em-tools/emtools/translators/cibd22x_importer.py
# ============================================================================
"""
CIBD22X XML to EMJSON v6 Translator

Main orchestrator that coordinates modular parsers for:
- Project metadata and location
- Catalogs (DU types, window types, constructions, PV)
- Geometry (zones, surfaces, openings)
- Systems (HVAC, DHW)
"""

from __future__ import annotations
from typing import Dict, Any
from xml.etree import ElementTree as ET
import json
import sys

# Fixed imports - use emtools package
from emtools.utils.id_registry import IDRegistry
from emtools.parsers.zones import parse_zones, parse_surfaces, parse_openings
from emtools.parsers.systems import parse_dhw
from emtools.parsers.catalogs import (
    parse_location, parse_du_types, parse_window_types,
    parse_construction_types, parse_pv
)
from emtools.parsers.hvac import parse_hvac

VERSION = "6.0"


def translate_cibd22x_to_v6(xml_path: str) -> Dict[str, Any]:
    """
    Translate CIBD22X XML to EMJSON v6.

    Args:
        xml_path: Path to CIBD22X XML file

    Returns:
        EMJSON v6 dictionary with full schema compliance

    Example:
        >>> emjson = translate_cibd22x_to_v6("project.xml")
        >>> print(f"Zones: {len(emjson['geometry']['zones'])}")
    """
    root = ET.parse(xml_path).getroot()

    # Initialize EMJSON v6 structure
    em: Dict[str, Any] = {
        "schema_version": VERSION,
        "project": {
            "model_info": {
                "source_format": "CIBD22X",
                "source_version": root.get("version") or "unknown",
                "translator_version": VERSION
            },
            "location": {}
        },
        "geometry": {
            "zones": [],
            "surfaces": {
                "walls": [],
                "roofs": [],
                "floors": []
            },
            "openings": {
                "windows": [],
                "doors": [],
                "skylights": []
            }
        },
        "catalogs": {
            "window_types": [],
            "construction_types": [],
            "du_types": []
        },
        "systems": {
            "hvac": [],
            "dhw": [],
            "pv": []
        },
        "energy": {
            "schedules": [],
            "loads": []
        },
        "results": {},
        "diagnostics": []
    }

    # Create ID registry for stable IDs
    id_registry = IDRegistry()

    # Parse catalogs first (they may be referenced by geometry/systems)
    parse_location(root, em)
    parse_du_types(root, em, id_registry)
    parse_window_types(root, em, id_registry)
    parse_construction_types(root, em, id_registry)
    parse_pv(root, em, id_registry)

    # Build DU index for zone parsing
    du_index = {dt["name"].lower(): dt for dt in em["catalogs"]["du_types"]}

    # Parse geometry with ID registry
    parse_zones(root, em, id_registry, du_index=du_index)
    parse_surfaces(root, em, id_registry)
    parse_openings(root, em, id_registry)

    # Parse systems
    parse_hvac(root, em, id_registry)
    parse_dhw(root, em, id_registry)

    # Store ID registry in metadata
    em["_metadata"] = {
        "id_registry": id_registry.export_registry(),
        "translator_version": VERSION,
        "source_format": "CIBD22X",
        "source_file": xml_path
    }

    # Summary diagnostic
    em["diagnostics"].append({
        "level": "info",
        "code": "I-TRANSLATION-COMPLETE",
        "message": f"Translation complete: {len(em['geometry']['zones'])} zones, "
                   f"{len(em['geometry']['surfaces']['walls'])} walls, "
                   f"{len(em['geometry']['openings']['windows'])} windows",
        "context": {
            "zones": len(em['geometry']['zones']),
            "surfaces": sum(len(v) for v in em['geometry']['surfaces'].values()),
            "openings": sum(len(v) for v in em['geometry']['openings'].values()),
            "hvac_systems": len(em['systems']['hvac']),
            "dhw_systems": len(em['systems']['dhw'])
        }
    })

    return em


def main(argv=None):
    """Command-line interface for translator."""
    argv = argv or sys.argv[1:]
    if not argv:
        print("Usage: python -m emtools.translators.cibd22x_importer <input.xml> [output.emjson]")
        return 2

    out = argv[1] if len(argv) > 1 else argv[0].rsplit('.', 1)[0] + ".emjson"
    em = translate_cibd22x_to_v6(argv[0])

    with open(out, "w", encoding="utf-8") as f:
        json.dump(em, f, indent=2)

    print(f"✓ Wrote {out}")
    print(f"  - {len(em['geometry']['zones'])} zones")
    print(f"  - {sum(len(v) for v in em['geometry']['surfaces'].values())} surfaces")
    print(f"  - {sum(len(v) for v in em['geometry']['openings'].values())} openings")
    print(f"  - {len(em['diagnostics'])} diagnostics")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())