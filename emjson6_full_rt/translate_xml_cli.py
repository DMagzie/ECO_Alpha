from __future__ import annotations
from translate_cibd22x_to_v6 import translate_cibd22x_to_v6
import sys, json

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python translate_xml_cli.py <input.xml> [output.em_v6.json]")
        raise SystemExit(2)

    out = sys.argv[2] if len(sys.argv) > 2 else sys.argv[1].rsplit('.', 1)[0] + ".em_v6.json"

    print(f"Translating {sys.argv[1]} → {out}")
    em = translate_cibd22x_to_v6(sys.argv[1])

    with open(out, "w", encoding="utf-8") as f:
        json.dump(em, f, indent=2)

    print(f"✓ Translation complete")
    print(f"  Zones: {len(em['geometry']['zones'])}")
    print(f"  Surfaces: {sum(len(v) for v in em['geometry']['surfaces'].values())}")
    print(f"  Openings: {sum(len(v) for v in em['geometry']['openings'].values())}")
    print(f"  HVAC: {len(em['systems']['hvac'])}")
    print(f"  DHW: {len(em['systems']['dhw'])}")
    print(f"  DU Types: {len(em['catalogs']['du_types'])}")
    print(f"  Window Types: {len(em['catalogs']['window_types'])}")
    print(f"  Diagnostics: {len(em['diagnostics'])}")