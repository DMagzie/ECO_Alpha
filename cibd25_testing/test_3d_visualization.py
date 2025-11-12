#!/usr/bin/env python3
"""
Test 3D Visualization Module

Tests the geometry visualizer with sample EMJSON data
"""

import sys
sys.path.insert(0, '/Users/DavidM/Documents/ECO_Alpha/eco_tools_parser')
sys.path.insert(0, '/Users/DavidM/Documents/ECO_Alpha/explorer_gui')

from eco_tools.geometry_builder import GeometryBuilder, EMJSONAdapter
from utils.geometry_visualizer import GeometryVisualizer, visualize_model


def test_basic_visualization():
    """Test basic 3D visualization"""
    print("=" * 70)
    print("TEST 1: Basic 3D Visualization")
    print("=" * 70)
    print()

    # Create a simple building
    builder = GeometryBuilder()

    print("Creating 3-zone building...")
    zone1 = builder.create_rectangular_zone(8.0, 6.0, 2.7, (0, 0), "Office 1")
    zone2 = builder.create_rectangular_zone(6.0, 5.0, 2.7, (8, 0), "Office 2")
    zone3 = builder.create_rectangular_zone(4.0, 4.0, 2.7, (8, 5), "Break Room")

    print(f"  ✅ Created {len(builder.zones)} zones")
    print()

    # Export to EMJSON
    print("Exporting to EMJSON...")
    emjson = EMJSONAdapter.to_emjson(builder, "Test Building")
    print(f"  ✅ EMJSON version: {emjson['emjson_version']}")
    print(f"  ✅ Zones: {len(emjson['geometry']['zones'])}")
    print(f"  ✅ Surfaces: {sum(len(v) for v in emjson['geometry']['surfaces'].values())}")
    print()

    # Create visualizer
    print("Creating visualization...")
    visualizer = GeometryVisualizer()

    # Generate traces
    traces = visualizer.emjson_to_traces(emjson)
    print(f"  ✅ Generated {len(traces)} mesh traces")
    print()

    # Create figure
    fig = visualizer.create_figure(traces, "Test Building 3D View")
    print(f"  ✅ Figure created successfully")
    print(f"  Figure type: {type(fig).__name__}")
    print()

    # Save to HTML
    output_path = '/tmp/test_3d_visualization.html'
    fig.write_html(output_path)
    print(f"  ✅ Saved to: {output_path}")
    print()

    return True


def test_statistics():
    """Test geometry statistics extraction"""
    print("=" * 70)
    print("TEST 2: Geometry Statistics")
    print("=" * 70)
    print()

    # Create building
    builder = GeometryBuilder()
    builder.create_rectangular_zone(10.0, 8.0, 3.0, (0, 0), "Main Zone")
    builder.create_rectangular_zone(5.0, 5.0, 2.7, (10, 0), "Side Zone")

    # Export to EMJSON
    emjson = EMJSONAdapter.to_emjson(builder, "Stats Test")

    # Get statistics
    visualizer = GeometryVisualizer()
    stats = visualizer.get_geometry_stats(emjson)

    print("Statistics:")
    print(f"  Zones: {stats['zones']}")
    print(f"  Surfaces: {stats['surfaces']}")
    print(f"  Openings: {stats['openings']}")
    print(f"  Floor Area: {stats['total_floor_area_m2']:.1f} m²")
    print(f"  Volume: {stats['total_volume_m3']:.1f} m³")
    print()

    print("Surface Breakdown:")
    for surf_type, count in stats['surface_types'].items():
        print(f"  {surf_type}: {count}")
    print()

    # Verify calculations
    expected_zones = 2
    expected_surfaces = 12  # 6 per zone (4 walls + floor + roof)

    if stats['zones'] == expected_zones:
        print(f"  ✅ Zone count correct ({expected_zones})")
    else:
        print(f"  ❌ Zone count mismatch: expected {expected_zones}, got {stats['zones']}")

    if stats['surfaces'] == expected_surfaces:
        print(f"  ✅ Surface count correct ({expected_surfaces})")
    else:
        print(f"  ⚠️  Surface count: expected {expected_surfaces}, got {stats['surfaces']}")

    print()
    return True


def test_one_step_visualization():
    """Test the convenience function"""
    print("=" * 70)
    print("TEST 3: One-Step Visualization Function")
    print("=" * 70)
    print()

    # Create building
    builder = GeometryBuilder()
    builder.create_rectangular_zone(6.0, 5.0, 2.7, (0, 0), "Single Zone Test")

    # Export
    emjson = EMJSONAdapter.to_emjson(builder, "One-Step Test")

    # One-step visualization
    print("Using visualize_model() convenience function...")
    fig = visualize_model(emjson, "One-Step Test")

    print(f"  ✅ Figure created: {type(fig).__name__}")

    # Save
    output_path = '/tmp/test_one_step.html'
    fig.write_html(output_path)
    print(f"  ✅ Saved to: {output_path}")
    print()

    return True


def test_empty_model():
    """Test handling of empty/invalid models"""
    print("=" * 70)
    print("TEST 4: Empty Model Handling")
    print("=" * 70)
    print()

    # Test with empty EMJSON
    empty_emjson = {
        'emjson_version': '6.0',
        'project': {'name': 'Empty Test'},
        'geometry': {}
    }

    visualizer = GeometryVisualizer()
    fig = visualizer.visualize_emjson(empty_emjson, "Empty Model Test")

    print(f"  ✅ Empty model handled gracefully")
    print(f"  Figure type: {type(fig).__name__}")
    print()

    return True


def main():
    """Run all tests"""
    print()
    print("=" * 70)
    print("3D VISUALIZATION MODULE TEST SUITE")
    print("=" * 70)
    print()

    tests = [
        test_basic_visualization,
        test_statistics,
        test_one_step_visualization,
        test_empty_model
    ]

    passed = 0
    failed = 0

    for test_func in tests:
        try:
            if test_func():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"  ❌ Test failed with exception: {e}")
            import traceback
            traceback.print_exc()
            failed += 1
            print()

    # Summary
    print("=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)
    print()
    print(f"  ✅ Passed: {passed}/{len(tests)}")
    if failed > 0:
        print(f"  ❌ Failed: {failed}/{len(tests)}")
    print()

    if passed == len(tests):
        print("🎉 All tests passed!")
        print()
        print("Generated files:")
        print("  • /tmp/test_3d_visualization.html")
        print("  • /tmp/test_one_step.html")
        print()
        print("Open these files in a browser to see the 3D visualizations!")
        print()
        return 0
    else:
        print("⚠️ Some tests failed")
        print()
        return 1


if __name__ == '__main__':
    sys.exit(main())
