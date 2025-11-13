#!/usr/bin/env python3
"""
Verify that CIBD22X (XML format) parsing still works after CIBD22 changes.
"""

import sys
from pathlib import Path

# Add project root to path
ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from eco_tools.translators.cibd22x import translate_cibd22x_to_v6

if __name__ == "__main__":
    # Test with known good CIBD22X file
    test_file = "/Users/DavidM/Documents/ECO_Alpha/test_output/sample_tests/Freedom Circle Building B - LEED_exported.cibd22x"

    print("Testing CIBD22X (XML format) parsing...")
    print(f"File: {Path(test_file).name}")
    print("="*80)

    result = translate_cibd22x_to_v6(test_file)

    # Check for errors
    diagnostics = result.get("diagnostics", [])
    errors = [d for d in diagnostics if d.get("level") == "error"]

    if errors:
        print(f"\n❌ CIBD22X import FAILED with {len(errors)} error(s):")
        for err in errors[:10]:
            print(f"  - {err.get('code', 'ERROR')}: {err.get('message', 'Unknown error')}")
        sys.exit(1)
    else:
        print("\n✅ CIBD22X import successful!")

    # Show statistics
    geometry = result.get("geometry", {})
    zones = geometry.get("zones", [])
    surfaces = geometry.get("surfaces", [])
    openings = geometry.get("openings", [])
    systems = result.get("systems", {})
    hvac = systems.get("hvac", [])

    print(f"\n{'='*80}")
    print("IMPORT STATISTICS")
    print(f"{'='*80}")
    print(f"Zones:        {len(zones)}")
    print(f"Surfaces:     {len(surfaces)}")
    print(f"Openings:     {len(openings)}")
    print(f"HVAC Systems: {len(hvac)}")

    # Check surface areas are parsed
    if surfaces:
        surfaces_with_area = [s for s in surfaces if s.get("area_m2") and s.get("area_m2") > 0]
        print(f"\nSurfaces with area: {len(surfaces_with_area)} / {len(surfaces)}")

        if surfaces_with_area:
            sample = surfaces_with_area[0]
            print(f"\nSample surface:")
            print(f"  Name: {sample.get('name', 'unknown')}")
            print(f"  Type: {sample.get('surface_type', 'unknown')}")
            print(f"  Area: {sample.get('area_m2', 0):.2f} m²")
            print(f"  Parent Zone: {sample.get('parent_zone_id', 'unknown')}")

    # Surface breakdown
    if surfaces:
        surface_types = {}
        for surf in surfaces:
            surf_type = surf.get("surface_type", "unknown")
            surface_types[surf_type] = surface_types.get(surf_type, 0) + 1

        print(f"\nSurface breakdown:")
        for surf_type, count in sorted(surface_types.items()):
            print(f"  - {count} {surf_type}")

    print(f"\n{'='*80}")
    print("✅ CIBD22X parsing is working correctly!")
    print(f"{'='*80}")
