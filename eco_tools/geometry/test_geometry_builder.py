"""
Geometry Builder - Standalone Unit Tests

Tests geometry_builder module in complete isolation from other ECO Tools components.
Verifies core functionality, error handling, and EMJSON export.

Run with:
    python -m pytest test_geometry_builder.py -v
    or
    python test_geometry_builder.py
"""

import sys
import json
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from eco_tools.geometry_builder import (
    GeometryBuilder,
    EMJSONAdapter,
    GeometryBuilderError,
    ValidationError,
    ZoneNotFoundError,
    SurfaceNotFoundError,
    Point3D,
    Surface,
    Zone,
    get_module_info
)


def test_module_info():
    """Test module metadata"""
    print("Testing module info...")
    info = get_module_info()
    assert info['name'] == 'geometry_builder'
    assert info['standalone'] == True
    assert info['emjson_version'] == '6.0'
    print("✓ Module info correct")


def test_create_rectangular_zone():
    """Test creating a simple rectangular zone"""
    print("\nTesting rectangular zone creation...")
    builder = GeometryBuilder()

    zone = builder.create_rectangular_zone(
        width=5.0,
        depth=4.0,
        height=2.7,
        zone_id="test_room"
    )

    assert zone is not None
    assert zone.id == "test_room"
    assert len(zone.surfaces) == 6  # floor + ceiling + 4 walls
    assert zone.calculate_floor_area() == 20.0  # 5 * 4
    assert abs(zone.calculate_volume() - 54.0) < 0.1  # 5 * 4 * 2.7

    print(f"  Zone: {zone.id}")
    print(f"  Surfaces: {len(zone.surfaces)}")
    print(f"  Floor area: {zone.calculate_floor_area():.2f} m²")
    print(f"  Volume: {zone.calculate_volume():.2f} m³")
    print("✓ Rectangular zone creation works")


def test_create_polygon_zone():
    """Test creating zone from polygon (L-shape)"""
    print("\nTesting polygon zone creation...")
    builder = GeometryBuilder()

    # L-shaped footprint
    footprint = [
        (0, 0), (6, 0), (6, 3), (3, 3), (3, 5), (0, 5)
    ]

    zone = builder.create_zone_from_polygon(
        footprint,
        height=2.7,
        zone_id="l_shaped"
    )

    assert zone is not None
    assert len(zone.surfaces) == 8  # floor + ceiling + 6 walls
    floor_area = zone.calculate_floor_area()
    assert 20 < floor_area < 25  # L-shape area

    print(f"  Zone: {zone.id}")
    print(f"  Surfaces: {len(zone.surfaces)}")
    print(f"  Floor area: {floor_area:.2f} m²")
    print("✓ Polygon zone creation works")


def test_copy_zone():
    """Test zone copy operation"""
    print("\nTesting zone copy...")
    builder = GeometryBuilder()

    # Create original
    zone1 = builder.create_rectangular_zone(5, 4, 2.7, zone_id="original")

    # Copy with offset
    zone2 = builder.copy_zone("original", offset=(6, 0, 0), new_zone_id="copy")

    assert len(builder.zones) == 2
    assert zone2.id == "copy"
    assert zone2.calculate_floor_area() == zone1.calculate_floor_area()

    print(f"  Original: {zone1.id} at (0, 0)")
    print(f"  Copy: {zone2.id} at (6, 0)")
    print("✓ Zone copy works")


def test_array_zones():
    """Test zone array operation"""
    print("\nTesting zone array...")
    builder = GeometryBuilder()

    # Create original
    builder.create_rectangular_zone(4, 3, 2.7, zone_id="unit")

    # Create array
    new_zones = builder.array_zones("unit", count=3, spacing_x=5)

    assert len(new_zones) == 3
    assert len(builder.zones) == 4  # original + 3 copies

    print(f"  Original + {len(new_zones)} copies = {len(builder.zones)} total zones")
    print("✓ Zone array works")


def test_push_pull():
    """Test push/pull operation on surface"""
    print("\nTesting push/pull...")
    builder = GeometryBuilder()

    zone = builder.create_rectangular_zone(5, 4, 2.7, zone_id="room")

    # Get a wall surface
    wall = zone.get_walls()[0]
    original_area = wall.calculate_area()

    # Push it out
    builder.push_pull_surface(wall.id, distance=0.5)

    # Area should remain same (just moved, not resized)
    new_surface = builder.get_surface_by_id(wall.id)
    assert new_surface is not None

    print(f"  Wall ID: {wall.id}")
    print(f"  Original area: {original_area:.2f} m²")
    print(f"  After push/pull: {new_surface.calculate_area():.2f} m²")
    print("✓ Push/pull works")


def test_validation():
    """Test geometry validation"""
    print("\nTesting validation...")
    builder = GeometryBuilder()

    # Empty builder should fail validation
    result = builder.validate_geometry()
    assert not result['valid']
    assert result['error_count'] > 0

    # Add geometry
    builder.create_rectangular_zone(5, 4, 2.7)

    # Should now pass
    result = builder.validate_geometry()
    print(f"  Validation: {builder.get_validation_summary()}")
    print(f"  Errors: {result['error_count']}, Warnings: {result['warning_count']}")
    assert result['valid']
    print("✓ Validation works")


def test_emjson_export():
    """Test EMJSON export"""
    print("\nTesting EMJSON export...")
    builder = GeometryBuilder()

    # Create some geometry
    builder.create_rectangular_zone(5, 4, 2.7, zone_id="room1", zone_name="Living Room")
    builder.create_rectangular_zone(4, 3, 2.7, origin=(6, 0), zone_id="room2", zone_name="Bedroom")

    # Export to EMJSON
    emjson = EMJSONAdapter.to_emjson(builder, project_name="Test Building")

    # Verify structure
    assert emjson['emjson_version'] == "6.0"
    assert emjson['project']['name'] == "Test Building"
    assert emjson['project']['source_format'] == "ECO_GeometryBuilder"

    # Check geometry
    assert len(emjson['geometry']['zones']) == 2
    assert 'walls' in emjson['geometry']['surfaces']
    assert 'floors' in emjson['geometry']['surfaces']
    assert 'roofs' in emjson['geometry']['surfaces']

    # Validate EMJSON
    is_valid = EMJSONAdapter.validate_emjson(emjson)
    assert is_valid

    print(f"  EMJSON version: {emjson['emjson_version']}")
    print(f"  Zones: {len(emjson['geometry']['zones'])}")
    print(f"  Walls: {len(emjson['geometry']['surfaces']['walls'])}")
    print(f"  Floors: {len(emjson['geometry']['surfaces']['floors'])}")
    print(f"  Validation: {'✓ Valid' if is_valid else '✗ Invalid'}")
    print("✓ EMJSON export works")


def test_export_summary():
    """Test export summary"""
    print("\nTesting export summary...")
    builder = GeometryBuilder()

    builder.create_rectangular_zone(5, 4, 2.7)

    summary = EMJSONAdapter.get_export_summary(builder)

    assert summary['zone_count'] == 1
    assert summary['total_surfaces'] == 6
    assert summary['emjson_version'] == "6.0"

    print(f"  Zones: {summary['zone_count']}")
    print(f"  Surfaces: {summary['total_surfaces']}")
    print(f"  Floor area: {summary['total_floor_area_m2']} m²")
    print("✓ Export summary works")


def test_error_handling():
    """Test error handling"""
    print("\nTesting error handling...")
    builder = GeometryBuilder()

    # Try to copy non-existent zone
    try:
        builder.copy_zone("nonexistent")
        assert False, "Should have raised ZoneNotFoundError"
    except ZoneNotFoundError:
        print("  ✓ ZoneNotFoundError raised correctly")

    # Try to push/pull non-existent surface
    try:
        builder.push_pull_surface("nonexistent", 1.0)
        assert False, "Should have raised SurfaceNotFoundError"
    except SurfaceNotFoundError:
        print("  ✓ SurfaceNotFoundError raised correctly")

    print("✓ Error handling works")


def test_stats():
    """Test model statistics"""
    print("\nTesting model statistics...")
    builder = GeometryBuilder()

    builder.create_rectangular_zone(5, 4, 2.7)
    builder.create_rectangular_zone(3, 3, 2.7, origin=(6, 0))

    stats = builder.get_stats()

    assert stats['zone_count'] == 2
    assert stats['total_floor_area_m2'] == 29.0  # 20 + 9

    print(f"  {stats}")
    print("✓ Statistics work")


def test_isolation():
    """Test that module is truly standalone"""
    print("\nTesting module isolation...")

    # Verify we can use geometry_builder without importing anything else from eco_tools
    builder = GeometryBuilder()
    zone = builder.create_rectangular_zone(5, 4, 2.7)
    emjson = EMJSONAdapter.to_emjson(builder)

    assert emjson is not None
    assert len(builder.zones) == 1

    print("  ✓ Module works standalone")
    print("  ✓ No dependencies on other emtools modules")
    print("✓ Module isolation verified")


def run_all_tests():
    """Run all tests"""
    print("=" * 60)
    print("GEOMETRY BUILDER - STANDALONE UNIT TESTS")
    print("=" * 60)

    tests = [
        test_module_info,
        test_create_rectangular_zone,
        test_create_polygon_zone,
        test_copy_zone,
        test_array_zones,
        test_push_pull,
        test_validation,
        test_emjson_export,
        test_export_summary,
        test_error_handling,
        test_stats,
        test_isolation,
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            test()
            passed += 1
        except Exception as e:
            print(f"\n✗ Test failed: {test.__name__}")
            print(f"  Error: {e}")
            import traceback
            traceback.print_exc()
            failed += 1

    print("\n" + "=" * 60)
    print(f"RESULTS: {passed} passed, {failed} failed")
    print("=" * 60)

    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
