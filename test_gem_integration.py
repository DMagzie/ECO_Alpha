#!/usr/bin/env python3
"""
GEM Import Integration and Edge Case Testing
Tests the complete GEM import pipeline including edge cases.
"""

import json
import sys
from pathlib import Path

# Add project root to path
ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT))

from eco_tools.translators.gem import translate_gem_to_v6


def test_basic_import(gem_file: str, expected_zones: int, expected_surfaces: int):
    """Test basic import functionality"""
    print(f"\n{'='*80}")
    print(f"Testing: {Path(gem_file).name}")
    print('='*80)

    try:
        result = translate_gem_to_v6(gem_file)

        # Check schema
        schema_version = result.get("schema_version")
        print(f"✓ Schema version: {schema_version}")

        # Check diagnostics
        diagnostics = result.get("diagnostics", [])
        errors = [d for d in diagnostics if d.get("level") == "error"]
        warnings = [d for d in diagnostics if d.get("level") == "warning"]
        infos = [d for d in diagnostics if d.get("level") == "info"]

        if errors:
            print(f"✗ ERRORS ({len(errors)}):")
            for err in errors:
                print(f"  - {err.get('code')}: {err.get('message')}")
            return (False, None)

        if warnings:
            print(f"⚠ Warnings ({len(warnings)}):")
            for warn in warnings:
                print(f"  - {warn.get('message')}")

        print(f"ℹ Info messages: {len(infos)}")

        # Check geometry
        geometry = result.get("geometry", {})
        zones = geometry.get("zones", [])
        surfaces = geometry.get("surfaces", [])
        openings = geometry.get("openings", [])

        print(f"\n📊 Geometry Stats:")
        print(f"  Zones: {len(zones)} (expected: {expected_zones})")
        print(f"  Surfaces: {len(surfaces)} (expected: {expected_surfaces})")
        print(f"  Openings: {len(openings)}")

        # Validate zone counts
        if len(zones) != expected_zones:
            print(f"✗ Zone count mismatch: got {len(zones)}, expected {expected_zones}")
            return (False, None)

        if len(surfaces) != expected_surfaces:
            print(f"✗ Surface count mismatch: got {len(surfaces)}, expected {expected_surfaces}")
            return (False, None)

        print(f"✓ Zone and surface counts match expectations")

        return (True, result)

    except Exception as e:
        print(f"✗ EXCEPTION: {e}")
        import traceback
        traceback.print_exc()
        return (False, None)


def test_vertices_present(result: dict):
    """Test that vertices are present in all geometry"""
    print(f"\n{'='*80}")
    print("Testing: Vertices Presence")
    print('='*80)

    geometry = result.get("geometry", {})
    surfaces = geometry.get("surfaces", [])
    openings = geometry.get("openings", [])

    # Check surfaces
    surfaces_with_vertices = 0
    surfaces_without_vertices = 0

    for surf in surfaces:
        vertices = surf.get("vertices", [])
        if vertices and len(vertices) >= 3:
            surfaces_with_vertices += 1
        else:
            surfaces_without_vertices += 1

    print(f"📐 Surfaces with vertices: {surfaces_with_vertices}/{len(surfaces)}")

    if surfaces_without_vertices > 0:
        print(f"⚠ Surfaces WITHOUT vertices: {surfaces_without_vertices}")

    # Check openings
    openings_with_vertices = 0
    openings_without_vertices = 0

    for opening in openings:
        vertices = opening.get("vertices", [])
        if vertices and len(vertices) >= 3:
            openings_with_vertices += 1
        else:
            openings_without_vertices += 1

    print(f"🪟 Openings with vertices: {openings_with_vertices}/{len(openings)}")

    if openings_without_vertices > 0:
        print(f"⚠ Openings WITHOUT vertices: {openings_without_vertices}")

    # Pass if majority have vertices
    success = (surfaces_with_vertices >= len(surfaces) * 0.9 and
               (len(openings) == 0 or openings_with_vertices >= len(openings) * 0.9))

    if success:
        print("✓ Vertex coverage is good (≥90%)")
    else:
        print("✗ Insufficient vertex coverage")

    return success


def test_zone_properties(result: dict):
    """Test that zones have proper calculated properties"""
    print(f"\n{'='*80}")
    print("Testing: Zone Properties")
    print('='*80)

    geometry = result.get("geometry", {})
    zones = geometry.get("zones", [])

    zones_with_area = 0
    zones_with_volume = 0
    zones_with_surfaces = 0

    total_floor_area = 0.0
    total_volume = 0.0

    for zone in zones:
        floor_area = zone.get("floor_area_m2")
        volume = zone.get("volume_m3")
        surfaces = zone.get("surfaces", [])

        if floor_area and floor_area > 0:
            zones_with_area += 1
            total_floor_area += floor_area

        if volume and volume > 0:
            zones_with_volume += 1
            total_volume += volume

        if surfaces and len(surfaces) > 0:
            zones_with_surfaces += 1

    print(f"🏢 Zones with floor area: {zones_with_area}/{len(zones)}")
    print(f"📦 Zones with volume: {zones_with_volume}/{len(zones)}")
    print(f"🧱 Zones with surface lists: {zones_with_surfaces}/{len(zones)}")
    print(f"📊 Total floor area: {total_floor_area:.2f} m²")
    print(f"📊 Total volume: {total_volume:.2f} m³")

    # Check first zone in detail
    if zones:
        zone = zones[0]
        print(f"\n🔍 Sample Zone: {zone.get('name', 'Unknown')}")
        print(f"  Floor Area: {zone.get('floor_area_m2', 'N/A')} m²")
        print(f"  Volume: {zone.get('volume_m3', 'N/A')} m³")
        print(f"  Surfaces: {len(zone.get('surfaces', []))}")

    success = (zones_with_area >= len(zones) * 0.8 and
               zones_with_surfaces == len(zones))

    if success:
        print("✓ Zone properties look good")
    else:
        print("✗ Some zone properties missing")

    return success


def test_surface_opening_relationships(result: dict):
    """Test that openings are properly linked to surfaces"""
    print(f"\n{'='*80}")
    print("Testing: Surface-Opening Relationships")
    print('='*80)

    geometry = result.get("geometry", {})
    surfaces = geometry.get("surfaces", [])
    openings = geometry.get("openings", [])

    # Build surface ID set
    surface_ids = {surf.get("id") for surf in surfaces}

    # Check opening parent references
    openings_with_parent = 0
    orphan_openings = 0
    invalid_parent_refs = 0

    for opening in openings:
        parent_id = opening.get("parent_surface_id")
        if parent_id:
            openings_with_parent += 1
            if parent_id not in surface_ids:
                invalid_parent_refs += 1
        else:
            orphan_openings += 1

    print(f"🪟 Openings with parent surface: {openings_with_parent}/{len(openings)}")
    print(f"🪟 Orphan openings: {orphan_openings}")

    if invalid_parent_refs > 0:
        print(f"⚠ Invalid parent references: {invalid_parent_refs}")

    success = (invalid_parent_refs == 0 and openings_with_parent == len(openings))

    if success:
        print("✓ All openings properly linked to surfaces")
    else:
        print("⚠ Some relationship issues found")

    return success


def test_export_roundtrip(result: dict, test_name: str):
    """Test that exported JSON can be re-parsed"""
    print(f"\n{'='*80}")
    print("Testing: Export Roundtrip")
    print('='*80)

    try:
        # Export to JSON
        json_str = json.dumps(result, indent=2)
        print(f"✓ JSON serialization successful ({len(json_str)} bytes)")

        # Re-parse
        reparsed = json.loads(json_str)
        print(f"✓ JSON deserialization successful")

        # Verify structure
        assert reparsed.get("schema_version") == result.get("schema_version")
        assert len(reparsed.get("geometry", {}).get("zones", [])) == len(result.get("geometry", {}).get("zones", []))
        assert len(reparsed.get("geometry", {}).get("surfaces", [])) == len(result.get("geometry", {}).get("surfaces", []))

        print("✓ Roundtrip structure validation passed")

        # Save to file
        output_file = ROOT / "test_output" / f"{test_name}_export.emjson.json"
        output_file.parent.mkdir(exist_ok=True)

        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(json_str)

        print(f"✓ Exported to: {output_file}")

        return True

    except Exception as e:
        print(f"✗ Roundtrip failed: {e}")
        return False


def run_all_tests():
    """Run complete test suite"""
    print("\n" + "="*80)
    print("GEM IMPORT INTEGRATION & EDGE CASE TEST SUITE")
    print("="*80)

    results = []

    # Test 1: Simple box (simplified format)
    test1_passed, test1_result = test_basic_import(
        str(ROOT / "examples" / "simple_box.gem"),
        expected_zones=1,
        expected_surfaces=6
    )
    results.append(("Simple Box Import", test1_passed))

    if test1_passed and test1_result:
        results.append(("Simple Box - Vertices", test_vertices_present(test1_result)))
        results.append(("Simple Box - Properties", test_zone_properties(test1_result)))
        results.append(("Simple Box - Relationships", test_surface_opening_relationships(test1_result)))
        results.append(("Simple Box - Export", test_export_roundtrip(test1_result, "simple_box")))

    # Test 2: Gibraltar (native IES format)
    gibraltar_path = ROOT.parent / "ECO_Alpha" / "Test Projects" / "Gib" / "Gibralter" / "1000 Gibraltar.gem"
    test2_passed, test2_result = test_basic_import(
        str(gibraltar_path),
        expected_zones=35,
        expected_surfaces=247
    )
    results.append(("Gibraltar Import", test2_passed))

    if test2_passed and test2_result:
        results.append(("Gibraltar - Vertices", test_vertices_present(test2_result)))
        results.append(("Gibraltar - Properties", test_zone_properties(test2_result)))
        results.append(("Gibraltar - Relationships", test_surface_opening_relationships(test2_result)))
        results.append(("Gibraltar - Export", test_export_roundtrip(test2_result, "gibraltar")))

    # Print summary
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)

    passed = sum(1 for _, p in results if p)
    total = len(results)

    for test_name, passed_flag in results:
        status = "✓ PASS" if passed_flag else "✗ FAIL"
        print(f"{status:8} {test_name}")

    print("="*80)
    print(f"TOTAL: {passed}/{total} tests passed ({passed/total*100:.1f}%)")
    print("="*80)

    return passed == total


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
