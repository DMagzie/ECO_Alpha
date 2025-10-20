from __future__ import annotations
from typing import Dict, Any
from xml.etree import ElementTree as ET
import json, sys
from parsers_zones import parse_zones, parse_surfaces, parse_openings
from parsers_systems import parse_dhw
from parsers_catalogs import parse_location, parse_du_types, parse_window_types, parse_construction_types, parse_pv
from parsers_hvac import parse_hvac

VERSION = "6"

def translate_cibd22x_to_v6(xml_path: str) -> Dict[str, Any]:
    root = ET.parse(xml_path).getroot()
    em: Dict[str, Any] = {"version": VERSION, "diagnostics": []}
    # Catalogs / metadata first
    parse_location(root, em)
    parse_du_types(root, em)
    parse_window_types(root, em)
    parse_construction_types(root, em)
    parse_pv(root, em)
    # Geometry + systems
    parse_zones(root, em, du_index={}, zone_to_group={})
    parse_surfaces(root, em)
    parse_openings(root, em)
    parse_hvac(root, em)
    parse_dhw(root, em)
    return em

def main(argv=None):
    argv = argv or sys.argv[1:]
    if not argv:
        print("Usage: python translate_cibd22x_to_v6.py <input.xml> [output.em_v6.json]")
        return 2
    out = argv[1] if len(argv) > 1 else argv[0].rsplit('.',1)[0] + ".em_v6.json"
    em = translate_cibd22x_to_v6(argv[0])
    with open(out, "w", encoding="utf-8") as f:
        json.dump(em, f, indent=2)
    print("Wrote", out)
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
