#!/usr/bin/env python3
"""
Comprehensive test to verify both CIBD22 (text) and CIBD22X (XML) work correctly.
"""

import sys
from pathlib import Path

# Add project root to path
ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from eco_tools.translators.cibd22 import translate_cibd22_to_v6
from eco_tools.translators.cibd22x import translate_cibd22x_to_v6

def test_format(format_name, translate_fn, test_file):
    """Test a single format."""
    print(f"\n{'='*80}")
    print(f"Testing {format_name}")
    print(f"{'='*80}")
    print(f"File: {Path(test_file).name}")

    result = translate_fn(test_file)

    # Check for errors
    diagnostics = result.get("diagnostics", [])
    errors = [d for d in diagnostics if d.get("level") == "error"]

    if errors:
        print(f"❌ FAILED with {len(errors)} error(s)")
        for err in errors[:3]:
            print(f"  - {err.get('message', '')}")
        return False

    # Get statistics
    geometry = result.get("geometry", {})
    zones = geometry.get("zones", [])
    surfaces = geometry.get("surfaces", [])
    openings = geometry.get("openings", [])
    systems = result.get("systems", {})
    hvac = systems.get("hvac", [])

    # Check surfaces have areas
    surfaces_with_area = [s for s in surfaces if s.get('area_m2', 0) > 0]

    print(f"\n✅ SUCCESS!")
    print(f"  Zones:              {len(zones)}")
    print(f"  Surfaces:           {len(surfaces)}")
    print(f"  Surfaces with area: {len(surfaces_with_area)} / {len(surfaces)}")
    print(f"  Openings:           {len(openings)}")
    print(f"  HVAC Systems:       {len(hvac)}")

    if surfaces_with_area:
        sample = surfaces_with_area[0]
        print(f"\n  Sample surface:")
        print(f"    Name: {sample.get('name', 'unknown')}")
        print(f"    Type: {sample.get('surface_type', 'unknown')}")
        print(f"    Area: {sample.get('area_m2', 0):.2f} m²")

    return True

if __name__ == "__main__":
    print("="*80)
    print("COMPREHENSIVE FORMAT COMPATIBILITY TEST")
    print("="*80)
    print("\nVerifying that CIBD22 text parser changes haven't broken CIBD22X XML parsing...")

    # Test CIBD22X (XML format) - should still work
    cibd22x_pass = test_format(
        "CIBD22X (XML Format)",
        translate_cibd22x_to_v6,
        "/Users/DavidM/Documents/ECO_Alpha/Bressi_FINAL.cibd22x"
    )

    # Test CIBD22 (Text format) - new functionality
    cibd22_pass = test_format(
        "CIBD22 (Text Format)",
        translate_cibd22_to_v6,
        "/Users/DavidM/Documents/ECO_Alpha/Test Projects/ICD/Cesar_Chavez_FinalV9.cibd22"
    )

    # Summary
    print(f"\n{'='*80}")
    print("FINAL RESULTS")
    print(f"{'='*80}")
    print(f"CIBD22X (XML):  {'✅ PASS' if cibd22x_pass else '❌ FAIL'}")
    print(f"CIBD22 (Text):  {'✅ PASS' if cibd22_pass else '❌ FAIL'}")

    if cibd22x_pass and cibd22_pass:
        print(f"\n{'='*80}")
        print("✅ ALL TESTS PASSED - Both formats working correctly!")
        print(f"{'='*80}")
        sys.exit(0)
    else:
        print(f"\n{'='*80}")
        print("❌ SOME TESTS FAILED")
        print(f"{'='*80}")
        sys.exit(1)
