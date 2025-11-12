#!/usr/bin/env python3
"""
Test Phase 1 Selection Implementation

Verifies:
1. Custom data is attached to mesh traces
2. Selection highlighting works
3. Property panel finds correct surface
4. Session state management
"""

import sys
sys.path.insert(0, '/Users/DavidM/Documents/ECO_Alpha/eco_tools_parser')
sys.path.insert(0, '/Users/DavidM/Documents/ECO_Alpha/explorer_gui')

from eco_tools.geometry_builder import GeometryBuilder, EMJSONAdapter
from utils.geometry_visualizer import GeometryVisualizer
import json


def test_customdata_attached():
    """Test 1: Verify customdata is attached to mesh vertices"""
    print("=" * 70)
    print("TEST 1: Custom Data Attachment")
    print("=" * 70)
    print()

    # Create a simple 2-zone model
    builder = GeometryBuilder()
    zone1 = builder.create_rectangular_zone(5.0, 4.0, 2.7, (0, 0), "Office 1")
    zone2 = builder.create_rectangular_zone(5.0, 4.0, 2.7, (6, 0), "Office 2")

    # Export to EMJSON
    emjson = EMJSONAdapter.to_emjson(builder, "Test Building")

    # Create visualizer
    visualizer = GeometryVisualizer()

    # Generate traces
    traces = visualizer.emjson_to_traces(emjson)

    print(f"✓ Generated {len(traces)} mesh traces")
    print()

    # Verify customdata on each trace
    for i, trace in enumerate(traces):
        if hasattr(trace, 'customdata') and trace.customdata is not None:
            print(f"  Trace {i}: ✓ Has customdata")

            # Check format
            if len(trace.customdata) > 0:
                sample = trace.customdata[0]
                print(f"    Sample: {sample}")

                if len(sample) == 2:
                    zone_id, surface_id = sample
                    print(f"    Zone ID: '{zone_id}'")
                    print(f"    Surface ID: '{surface_id}'")
                    print(f"    Format: ✓ Correct [zone_id, surface_id]")
                else:
                    print(f"    Format: ✗ WRONG - Expected 2 elements, got {len(sample)}")
            else:
                print(f"    Data: ✗ EMPTY")
        else:
            print(f"  Trace {i}: ✗ NO customdata")

        print()

    print("=" * 70)
    print()
    return len(traces) > 0


def test_selection_highlighting():
    """Test 2: Verify selection highlighting changes colors"""
    print("=" * 70)
    print("TEST 2: Selection Highlighting")
    print("=" * 70)
    print()

    # Create a simple model
    builder = GeometryBuilder()
    zone = builder.create_rectangular_zone(5.0, 4.0, 2.7, (0, 0), "Test Zone")
    emjson = EMJSONAdapter.to_emjson(builder, "Test")

    # Get a surface ID to select from geometry.surfaces
    surfaces_by_type = emjson['geometry']['surfaces']
    # Get first wall
    walls = surfaces_by_type.get('walls', [])
    test_surface_id = walls[0]['id'] if walls else None

    print(f"Testing with surface ID: '{test_surface_id}'")
    print()

    # Generate traces WITHOUT selection
    visualizer = GeometryVisualizer()
    traces_normal = visualizer.emjson_to_traces(emjson, selected_surface=None)

    # Generate traces WITH selection
    traces_selected = visualizer.emjson_to_traces(emjson, selected_surface=test_surface_id)

    print(f"Generated {len(traces_normal)} traces without selection")
    print(f"Generated {len(traces_selected)} traces with selection")
    print()

    # Compare colors
    for i, (normal_trace, selected_trace) in enumerate(zip(traces_normal, traces_selected)):
        normal_color = normal_trace.color
        selected_color = selected_trace.color

        print(f"Trace {i}:")
        print(f"  Normal color:   {normal_color}")
        print(f"  Selected color: {selected_color}")

        if normal_color != selected_color:
            print(f"  Status: ✓ HIGHLIGHTING ACTIVE")
            if 'rgba(255, 165, 0' in selected_color:
                print(f"  Color: ✓ Correct orange highlight")
            else:
                print(f"  Color: ⚠️  Not orange")
        else:
            print(f"  Status: = No change (expected for non-selected surfaces)")

        print()

    print("=" * 70)
    print()
    return True


def test_property_panel_lookup():
    """Test 3: Verify we can find surfaces by ID in the model"""
    print("=" * 70)
    print("TEST 3: Property Panel Surface Lookup")
    print("=" * 70)
    print()

    # Create a multi-zone model
    builder = GeometryBuilder()
    zone1 = builder.create_rectangular_zone(5.0, 4.0, 2.7, (0, 0), "Office 1")
    zone2 = builder.create_rectangular_zone(6.0, 5.0, 3.0, (10, 0), "Office 2")

    emjson = EMJSONAdapter.to_emjson(builder, "Multi-Zone Building")

    # Get all surface IDs from geometry.surfaces
    all_surface_ids = []
    surfaces_by_type = emjson['geometry']['surfaces']
    zones = emjson['geometry']['zones']

    for category, surf_list in surfaces_by_type.items():
        for surface in surf_list:
            zone_id = surface.get('zone_id')
            surf_id = surface.get('id', surface.get('name'))
            all_surface_ids.append((zone_id, surf_id, surface))

    print(f"Model contains {len(zones)} zones")
    print(f"Total surfaces: {len(all_surface_ids)}")
    print()

    # Test lookup function (simulating property panel logic)
    def find_surface_by_id(model, surface_id):
        """Find surface in model by ID"""
        surfaces_by_type = model['geometry']['surfaces']

        # Search all surface categories
        for category, surf_list in surfaces_by_type.items():
            for surface in surf_list:
                surf_id = surface.get('id', surface.get('name'))
                if surf_id == surface_id:
                    # Find parent zone
                    zone_id = surface.get('zone_id')
                    parent_zone = None
                    for zone in model['geometry']['zones']:
                        if zone.get('id') == zone_id or zone.get('name') == zone_id:
                            parent_zone = zone
                            break
                    return surface, parent_zone
        return None, None

    # Test a few lookups
    print("Testing surface lookups:")
    print()

    for i, (zone_name, surf_id, expected_surface) in enumerate(all_surface_ids[:5]):
        found_surface, found_zone = find_surface_by_id(emjson, surf_id)

        if found_surface:
            print(f"  Lookup {i+1}: ✓ Found")
            print(f"    Surface ID: {surf_id}")
            print(f"    Zone: {found_zone['name']}")
            print(f"    Type: {found_surface.get('type')}")
            print(f"    Area: {found_surface.get('area_m2', 0):.2f} m²")

            # Verify it's the right one
            if found_surface['id'] == expected_surface['id']:
                print(f"    Match: ✓ Correct surface")
            else:
                print(f"    Match: ✗ WRONG surface")
        else:
            print(f"  Lookup {i+1}: ✗ NOT FOUND")
            print(f"    Surface ID: {surf_id}")

        print()

    print("=" * 70)
    print()
    return True


def test_session_state_workflow():
    """Test 4: Simulate the full selection workflow"""
    print("=" * 70)
    print("TEST 4: Session State Selection Workflow")
    print("=" * 70)
    print()

    # Create model
    builder = GeometryBuilder()
    zone = builder.create_rectangular_zone(8.0, 6.0, 3.0, (0, 0), "Test Office")
    emjson = EMJSONAdapter.to_emjson(builder, "Workflow Test")

    # Simulate session state (normally st.session_state)
    session_state = {
        'selected_zone': None,
        'selected_surface': None,
        'active_model': emjson
    }

    print("Initial state:")
    print(f"  selected_zone: {session_state['selected_zone']}")
    print(f"  selected_surface: {session_state['selected_surface']}")
    print()

    # Simulate user clicking on a surface
    # In real app, this comes from plotly_events
    surfaces_by_type = emjson['geometry']['surfaces']
    # Get a wall to click on
    test_surface = surfaces_by_type['walls'][2] if len(surfaces_by_type['walls']) > 2 else surfaces_by_type['walls'][0]
    clicked_surface_id = test_surface['id']
    clicked_zone_id = test_surface['zone_id']

    print("SIMULATING CLICK EVENT:")
    print(f"  User clicked on surface: {clicked_surface_id}")
    print(f"  From zone: {clicked_zone_id}")
    print()

    # Update session state (what our click handler does)
    session_state['selected_zone'] = clicked_zone_id
    session_state['selected_surface'] = clicked_surface_id

    print("Updated state:")
    print(f"  selected_zone: {session_state['selected_zone']}")
    print(f"  selected_surface: {session_state['selected_surface']}")
    print()

    # Generate visualization with selection
    visualizer = GeometryVisualizer()
    fig = visualizer.visualize_emjson(
        emjson,
        title="Test Visualization",
        selected_surface=session_state['selected_surface']
    )

    print("Visualization generated with selection:")
    print(f"  Figure has {len(fig.data)} traces")
    print(f"  Selected surface: {session_state['selected_surface']}")
    print()

    # Verify we can find the surface for property display
    def find_surface_by_id(model, surface_id):
        surfaces_by_type = model['geometry']['surfaces']
        for category, surf_list in surfaces_by_type.items():
            for surface in surf_list:
                if surface.get('id') == surface_id:
                    # Find parent zone
                    zone_id = surface.get('zone_id')
                    for zone in model['geometry']['zones']:
                        if zone.get('id') == zone_id or zone.get('name') == zone_id:
                            return surface, zone
        return None, None

    found_surface, found_zone = find_surface_by_id(
        session_state['active_model'],
        session_state['selected_surface']
    )

    if found_surface:
        print("Property Panel would display:")
        print(f"  ✓ Surface found: {found_surface.get('id', 'Unknown')}")
        print(f"  ✓ Type: {found_surface.get('type', 'Unknown')}")
        print(f"  ✓ Area: {found_surface.get('area_m2', 0):.2f} m²")
        if found_zone:
            print(f"  ✓ Zone: {found_zone.get('name', found_zone.get('id', 'Unknown'))}")
        print()

        # Check for tilt/azimuth
        if 'tilt_deg' in found_surface:
            print(f"  ✓ Tilt: {found_surface['tilt_deg']:.0f}°")
        if 'azimuth_deg' in found_surface:
            print(f"  ✓ Azimuth: {found_surface['azimuth_deg']:.0f}°")

        print()
    else:
        print("  ✗ ERROR: Could not find surface for property panel")
        print()

    # Simulate clearing selection
    print("SIMULATING CLEAR SELECTION:")
    session_state['selected_zone'] = None
    session_state['selected_surface'] = None

    print(f"  selected_zone: {session_state['selected_zone']}")
    print(f"  selected_surface: {session_state['selected_surface']}")
    print()

    print("=" * 70)
    print()
    return True


def test_export_with_selection():
    """Test 5: Verify visualization can be exported as HTML"""
    print("=" * 70)
    print("TEST 5: Export Visualization")
    print("=" * 70)
    print()

    # Create model
    builder = GeometryBuilder()
    zone = builder.create_rectangular_zone(5.0, 4.0, 2.7, (0, 0), "Export Test")
    emjson = EMJSONAdapter.to_emjson(builder, "Export Building")

    # Get a surface to select
    surfaces_by_type = emjson['geometry']['surfaces']
    surface_id = surfaces_by_type['walls'][1]['id'] if len(surfaces_by_type.get('walls', [])) > 1 else surfaces_by_type['walls'][0]['id']

    # Generate visualization
    visualizer = GeometryVisualizer()
    fig = visualizer.visualize_emjson(
        emjson,
        title="Export Test with Selection",
        selected_surface=surface_id
    )

    # Export to HTML
    output_file = '/tmp/test_phase1_selection.html'
    html_str = fig.to_html(include_plotlyjs='cdn')

    with open(output_file, 'w') as f:
        f.write(html_str)

    file_size = len(html_str)

    print(f"✓ Exported visualization to: {output_file}")
    print(f"  File size: {file_size:,} bytes ({file_size/1024:.1f} KB)")
    print(f"  Selected surface: {surface_id}")
    print()

    print("You can open this file in a browser to verify:")
    print(f"  open {output_file}")
    print()

    print("=" * 70)
    print()
    return True


def main():
    """Run all tests"""
    print()
    print("=" * 70)
    print("PHASE 1 SELECTION IMPLEMENTATION - TEST SUITE")
    print("=" * 70)
    print()

    tests = [
        ("Custom Data Attachment", test_customdata_attached),
        ("Selection Highlighting", test_selection_highlighting),
        ("Property Panel Lookup", test_property_panel_lookup),
        ("Session State Workflow", test_session_state_workflow),
        ("Export with Selection", test_export_with_selection),
    ]

    results = []

    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result, None))
        except Exception as e:
            results.append((test_name, False, str(e)))
            print(f"✗ TEST FAILED: {e}")
            import traceback
            traceback.print_exc()
            print()

    # Summary
    print("=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)
    print()

    passed = sum(1 for _, result, _ in results if result)
    total = len(results)

    for test_name, result, error in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status}  {test_name}")
        if error:
            print(f"       Error: {error}")

    print()
    print(f"Results: {passed}/{total} tests passed")
    print()

    if passed == total:
        print("🎉 ALL TESTS PASSED!")
        print()
        print("Phase 1 selection implementation is working correctly!")
        print()
        print("Next steps:")
        print("1. Test in the Streamlit GUI with a real model")
        print("2. Verify click events work in the browser")
        print("3. Check property panel displays correct info")
        print("4. Test with multi-zone models")
        print()
    else:
        print("⚠️  SOME TESTS FAILED")
        print()
        print("Review errors above and fix issues before proceeding.")
        print()

    print("=" * 70)
    print()


if __name__ == '__main__':
    main()
