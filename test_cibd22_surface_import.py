#!/usr/bin/env python3
"""
Test CIBD22 import to verify surfaces are now parsed correctly.
"""

import sys
from pathlib import Path

# Add project root to path
ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from eco_tools.translators.cibd22 import translate_cibd22_to_v6

if __name__ == "__main__":
    # Test file
    test_file = "/Users/DavidM/Documents/ECO_Alpha/Test Projects/ICD/Cesar_Chavez_FinalV9.cibd22"

    print("Importing CIBD22 file...")
    result = translate_cibd22_to_v6(test_file)

    # Check for errors
    diagnostics = result.get("diagnostics", [])
    errors = [d for d in diagnostics if d.get("level") == "error"]

    if errors:
        print(f"\n❌ Import failed with {len(errors)} error(s):")
        for err in errors[:10]:
            print(f"  - {err.get('code', 'ERROR')}: {err.get('message', 'Unknown error')}")
    else:
        print("\n✅ Import successful!")

    # Show statistics
    geometry = result.get("geometry", {})
    zones = geometry.get("zones", [])
    surfaces = geometry.get("surfaces", [])
    openings = geometry.get("openings", [])

    print(f"\n{'='*60}")
    print("IMPORT STATISTICS")
    print(f"{'='*60}")
    print(f"Zones:     {len(zones)}")
    print(f"Surfaces:  {len(surfaces)}")
    print(f"Openings:  {len(openings)}")

    # Show surface breakdown
    if surfaces:
        surface_types = {}
        for surf in surfaces:
            surf_type = surf.get("surface_type", "unknown")
            surface_types[surf_type] = surface_types.get(surf_type, 0) + 1

        print(f"\nSurface breakdown:")
        for surf_type, count in sorted(surface_types.items()):
            print(f"  - {count} {surf_type}")

    # Show opening breakdown
    if openings:
        opening_types = {}
        for opening in openings:
            opening_type = opening.get("type", "unknown")
            opening_types[opening_type] = opening_types.get(opening_type, 0) + 1

        print(f"\nOpening breakdown:")
        for opening_type, count in sorted(opening_types.items()):
            print(f"  - {count} {opening_type}")

    # Show first zone with surfaces
    if zones and surfaces:
        print(f"\n{'='*60}")
        print("SAMPLE ZONE WITH SURFACES")
        print(f"{'='*60}")

        for zone in zones[:1]:  # Just first zone
            zone_name = zone.get("name", "unknown")
            zone_id = zone.get("id", "unknown")

            # Find surfaces for this zone
            zone_surfaces = [s for s in surfaces if s.get("parent_zone_id") == zone_id]

            print(f"\nZone: {zone_name}")
            print(f"  ID: {zone_id}")
            print(f"  Surfaces: {len(zone_surfaces)}")

            if zone_surfaces:
                for surf in zone_surfaces[:3]:  # First 3 surfaces
                    surf_name = surf.get("name", "unknown")
                    surf_type = surf.get("surface_type", "unknown")
                    surf_area = surf.get("area_m2", 0)
                    print(f"    - {surf_type}: {surf_name} ({surf_area:.2f} m²)")
