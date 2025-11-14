#!/usr/bin/env python3
"""
Test GEM import to verify IES VE GEM files are parsed correctly.
"""

import sys
from pathlib import Path

# Add project root to path
ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from eco_tools.translators.gem import translate_gem_to_v6

if __name__ == "__main__":
    print("="*80)
    print("GEM IMPORT TEST")
    print("="*80)

    # Test files
    test_files = [
        "/Users/DavidM/Documents/ECO_Alpha_v7/examples/simple_box.gem",
        "/Users/DavidM/Documents/ECO_Alpha/Test Projects/Gib/Gibralter/1000 Gibraltar.gem"
    ]

    for test_file in test_files:
        if not Path(test_file).exists():
            print(f"\n⚠️  Skipping (file not found): {Path(test_file).name}")
            continue

        print(f"\n{'='*80}")
        print(f"Testing: {Path(test_file).name}")
        print(f"{'='*80}")

        result = translate_gem_to_v6(test_file)

        # Check for errors
        diagnostics = result.get("diagnostics", [])
        errors = [d for d in diagnostics if d.get("level") == "error"]

        if errors:
            print(f"\n❌ Import FAILED with {len(errors)} error(s):")
            for err in errors[:5]:
                print(f"  - {err.get('code', 'ERROR')}: {err.get('message', 'Unknown error')}")
            continue

        # Get statistics
        geometry = result.get("geometry", {})
        zones = geometry.get("zones", [])
        surfaces = geometry.get("surfaces", [])
        openings = geometry.get("openings", [])

        print(f"\n✅ Import successful!")
        print(f"\nGeometry Statistics:")
        print(f"  Zones:     {len(zones)}")
        print(f"  Surfaces:  {len(surfaces)}")
        print(f"  Openings:  {len(openings)}")

        # Surface breakdown
        if surfaces:
            surface_types = {}
            surfaces_with_area = 0
            total_area = 0.0

            for surf in surfaces:
                surf_type = surf.get("surface_type", "unknown")
                surface_types[surf_type] = surface_types.get(surf_type, 0) + 1

                area = surf.get("area_m2", 0)
                if area and area > 0:
                    surfaces_with_area += 1
                    total_area += area

            print(f"\nSurface Breakdown:")
            for surf_type, count in sorted(surface_types.items()):
                print(f"  {surf_type}: {count}")

            print(f"\nSurface Areas:")
            print(f"  With area: {surfaces_with_area} / {len(surfaces)}")
            if surfaces_with_area > 0:
                print(f"  Total area: {total_area:.2f} m²")
                print(f"  Average: {total_area/surfaces_with_area:.2f} m²")

        # Opening breakdown
        if openings:
            opening_types = {}
            for opening in openings:
                opening_type = opening.get("opening_type", "unknown")
                opening_types[opening_type] = opening_types.get(opening_type, 0) + 1

            print(f"\nOpening Breakdown:")
            for opening_type, count in sorted(opening_types.items()):
                print(f"  {opening_type}: {count}")

        # Sample zone
        if zones:
            zone = zones[0]
            print(f"\nSample Zone:")
            print(f"  Name: {zone.get('name', 'unknown')}")
            print(f"  ID: {zone.get('id', 'unknown')}")
            if zone.get('floor_area_m2'):
                print(f"  Floor Area: {zone.get('floor_area_m2'):.2f} m²")
            if zone.get('volume_m3'):
                print(f"  Volume: {zone.get('volume_m3'):.2f} m³")

            # Find surfaces for this zone
            zone_surfaces = [s for s in surfaces if s.get("parent_zone_id") == zone.get("id")]
            if zone_surfaces:
                print(f"  Surfaces: {len(zone_surfaces)}")
                sample_surf = zone_surfaces[0]
                print(f"\n  Sample Surface:")
                print(f"    Name: {sample_surf.get('name', 'unknown')}")
                print(f"    Type: {sample_surf.get('surface_type', 'unknown')}")
                if sample_surf.get('area_m2'):
                    print(f"    Area: {sample_surf.get('area_m2'):.2f} m²")

    print(f"\n{'='*80}")
    print("✅ GEM import test complete!")
    print(f"{'='*80}")
