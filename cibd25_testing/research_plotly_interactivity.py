#!/usr/bin/env python3
"""
Research: Plotly Interactivity for Selection

Test Plotly's capabilities for:
1. Click events
2. Hover events
3. Selection tracking
4. Dynamic updates
"""

import sys
sys.path.insert(0, '/Users/DavidM/Documents/ECO_Alpha/eco_tools_parser')

from eco_tools.geometry_builder import GeometryBuilder, EMJSONAdapter
import plotly.graph_objects as go
import plotly.express as px


def test_basic_click_events():
    """Test if we can capture click events on 3D meshes"""
    print("=" * 70)
    print("TEST 1: Basic Click Events")
    print("=" * 70)
    print()

    # Create simple geometry
    builder = GeometryBuilder()
    zone1 = builder.create_rectangular_zone(5.0, 4.0, 2.7, (0, 0), "Zone 1")
    zone2 = builder.create_rectangular_zone(5.0, 4.0, 2.7, (6, 0), "Zone 2")

    # Export to EMJSON
    emjson = EMJSONAdapter.to_emjson(builder, "Click Test")

    # Create figure with clickable surfaces
    fig = go.Figure()

    zone_id = 0
    for zone in emjson['geometry']['zones']:
        zone_name = zone['name']

        # Add zone bounding box for clickability
        # In real implementation, we'd add individual surfaces
        x = [0, 5, 5, 0, 0, 5, 5, 0]
        y = [0, 0, 4, 4, 0, 0, 4, 4]
        z = [0, 0, 0, 0, 2.7, 2.7, 2.7, 2.7]

        # Shift zone 2
        if zone_id == 1:
            x = [xi + 6 for xi in x]

        # Create mesh with custom data
        mesh = go.Mesh3d(
            x=x,
            y=y,
            z=z,
            i=[0, 0, 0, 0, 4, 4, 4, 4, 0, 0, 1, 1],
            j=[1, 2, 3, 4, 5, 6, 7, 0, 1, 2, 5, 6],
            k=[2, 3, 4, 5, 6, 7, 0, 1, 5, 6, 2, 3],
            color='lightblue',
            opacity=0.5,
            name=zone_name,
            hovertext=f"<b>{zone_name}</b><br>Click to select",
            hoverinfo='text',
            # Custom data for identification
            customdata=[[zone_id]] * 8,
        )

        fig.add_trace(mesh)
        zone_id += 1

    fig.update_layout(
        title="Click Test - Hover over zones",
        scene=dict(
            xaxis_title='X (m)',
            yaxis_title='Y (m)',
            zaxis_title='Z (m)',
            aspectmode='cube'
        ),
        height=600
    )

    # Save as HTML
    output_file = '/tmp/plotly_click_test.html'
    fig.write_html(output_file)

    print(f"✅ Created interactive test file: {output_file}")
    print()
    print("Features demonstrated:")
    print("  • Hover tooltips on each zone")
    print("  • Custom data attached to meshes")
    print("  • Named traces for identification")
    print()
    print("Limitations:")
    print("  ⚠️  Plotly doesn't support direct click events in HTML")
    print("  ⚠️  Would need Streamlit or Dash for click handling")
    print()

    return True


def test_selection_with_dash():
    """Research: How Dash handles selection"""
    print("=" * 70)
    print("TEST 2: Selection Approaches")
    print("=" * 70)
    print()

    print("Option 1: Dash (Plotly's framework)")
    print("  ✅ Full click event support")
    print("  ✅ Callback system for interactivity")
    print("  ✅ State management built-in")
    print("  ❌ Requires separate Dash app (not Streamlit)")
    print()

    print("Option 2: Streamlit with plotly_events")
    print("  ✅ Works with existing Streamlit GUI")
    print("  ✅ Click events via streamlit-plotly-events package")
    print("  ⚠️  Limited to certain event types")
    print("  Code example:")
    print("    from streamlit_plotly_events import plotly_events")
    print("    selected = plotly_events(fig, click_event=True)")
    print()

    print("Option 3: Plotly + Custom JavaScript")
    print("  ✅ Full control over events")
    print("  ✅ Can embed in Streamlit")
    print("  ❌ Requires custom component development")
    print()

    print("Option 4: Three.js (via streamlit-plotly-events or custom)")
    print("  ✅ Full 3D capabilities")
    print("  ✅ Better performance for large models")
    print("  ❌ More complex integration")
    print()

    print("RECOMMENDATION: Start with Option 2 (Streamlit + plotly_events)")
    print("  • Easiest to integrate")
    print("  • Works with current GUI")
    print("  • Can upgrade to Three.js later if needed")
    print()

    return True


def test_dynamic_color_update():
    """Test changing mesh colors dynamically"""
    print("=" * 70)
    print("TEST 3: Dynamic Color Updates")
    print("=" * 70)
    print()

    # Create two zones with different colors
    fig = go.Figure()

    # Zone 1 - Normal color
    fig.add_trace(go.Mesh3d(
        x=[0, 5, 5, 0, 0, 5, 5, 0],
        y=[0, 0, 4, 4, 0, 0, 4, 4],
        z=[0, 0, 0, 0, 2.7, 2.7, 2.7, 2.7],
        i=[0, 0, 0, 0],
        j=[1, 2, 3, 4],
        k=[2, 3, 4, 5],
        color='lightblue',
        opacity=0.7,
        name='Zone 1 - Normal'
    ))

    # Zone 2 - Selected (highlighted)
    fig.add_trace(go.Mesh3d(
        x=[6, 11, 11, 6, 6, 11, 11, 6],
        y=[0, 0, 4, 4, 0, 0, 4, 4],
        z=[0, 0, 0, 0, 2.7, 2.7, 2.7, 2.7],
        i=[0, 0, 0, 0],
        j=[1, 2, 3, 4],
        k=[2, 3, 4, 5],
        color='orange',  # Highlight color
        opacity=0.9,
        name='Zone 2 - SELECTED'
    ))

    fig.update_layout(
        title="Selection Highlighting Demo",
        scene=dict(aspectmode='cube'),
        height=600
    )

    output_file = '/tmp/plotly_highlight_test.html'
    fig.write_html(output_file)

    print(f"✅ Created highlight demo: {output_file}")
    print()
    print("Demonstrated:")
    print("  • Different colors for selected vs unselected")
    print("  • Orange highlight for selected element")
    print("  • Higher opacity for selected (0.9 vs 0.7)")
    print()
    print("Implementation strategy:")
    print("  1. Store selection state in st.session_state")
    print("  2. Re-render figure with updated colors")
    print("  3. Selected elements get highlight color")
    print()

    return True


def test_hover_info():
    """Test rich hover information"""
    print("=" * 70)
    print("TEST 4: Rich Hover Information")
    print("=" * 70)
    print()

    fig = go.Figure()

    # Create surface with detailed hover info
    hover_text = """
<b>Exterior Wall</b><br>
<br>
<b>Properties:</b><br>
• Zone: Office 1<br>
• Area: 24.5 m²<br>
• Type: Exterior Wall<br>
• Azimuth: 180° (South)<br>
• Construction: Default<br>
<br>
<i>Click to select</i>
"""

    fig.add_trace(go.Mesh3d(
        x=[0, 5, 5, 0],
        y=[0, 0, 0, 0],
        z=[0, 0, 2.7, 2.7],
        i=[0],
        j=[1],
        k=[2],
        color='lightgray',
        opacity=0.7,
        name='South Wall',
        hovertext=hover_text,
        hoverinfo='text'
    ))

    fig.update_layout(
        title="Rich Hover Info Demo - Hover over the wall",
        scene=dict(aspectmode='cube'),
        height=600
    )

    output_file = '/tmp/plotly_hover_test.html'
    fig.write_html(output_file)

    print(f"✅ Created hover demo: {output_file}")
    print()
    print("Demonstrated:")
    print("  • Rich HTML hover tooltips")
    print("  • Surface properties displayed on hover")
    print("  • Formatted with bold, bullets, etc.")
    print()

    return True


def create_selection_prototype():
    """Create a prototype showing how selection would work"""
    print("=" * 70)
    print("TEST 5: Selection Workflow Prototype")
    print("=" * 70)
    print()

    print("Proposed Workflow:")
    print()
    print("1. User clicks on surface in 3D view")
    print("   ↓")
    print("   plotly_events captures click")
    print("   ↓")
    print("2. Extract clicked surface ID from event data")
    print("   ↓")
    print("   event = {'points': [{'customdata': ['zone_1', 'surface_3']}]}")
    print("   ↓")
    print("3. Update st.session_state.selected_surface = 'surface_3'")
    print("   ↓")
    print("4. Re-render figure with updated colors")
    print("   ↓")
    print("   if surface.id == selected_surface:")
    print("       color = 'orange'  # Highlight")
    print("   ↓")
    print("5. Display properties in sidebar")
    print("   ↓")
    print("   st.sidebar.header('Selected Surface')")
    print("   st.sidebar.text(f'ID: {selected_surface}')")
    print("   st.sidebar.text(f'Area: {surface.area} m²')")
    print()

    print("Code Example:")
    print()
    print("```python")
    print("import streamlit as st")
    print("from streamlit_plotly_events import plotly_events")
    print()
    print("# Create figure with custom data")
    print("fig = create_geometry_figure(emjson)")
    print()
    print("# Capture click events")
    print("selected_points = plotly_events(fig, click_event=True)")
    print()
    print("# Update selection state")
    print("if selected_points:")
    print("    surface_id = selected_points[0]['customdata'][1]")
    print("    st.session_state.selected_surface = surface_id")
    print("    st.rerun()  # Re-render with highlight")
    print()
    print("# Display properties")
    print("if 'selected_surface' in st.session_state:")
    print("    surface = get_surface(st.session_state.selected_surface)")
    print("    st.sidebar.header('Selected Surface')")
    print("    st.sidebar.text(f'Area: {surface.area} m²')")
    print("```")
    print()

    print("✅ Workflow defined!")
    print()

    return True


def main():
    """Run all research tests"""
    print()
    print("=" * 70)
    print("PLOTLY INTERACTIVITY RESEARCH")
    print("=" * 70)
    print()

    tests = [
        test_basic_click_events,
        test_selection_with_dash,
        test_dynamic_color_update,
        test_hover_info,
        create_selection_prototype
    ]

    for test in tests:
        test()

    print("=" * 70)
    print("RESEARCH COMPLETE")
    print("=" * 70)
    print()
    print("Key Findings:")
    print()
    print("✅ Hover tooltips work perfectly (already using)")
    print("✅ Custom data can be attached to each surface")
    print("✅ Dynamic color updates possible (re-render)")
    print("✅ streamlit-plotly-events enables click handling")
    print()
    print("⚠️  Requires: pip install streamlit-plotly-events")
    print()
    print("Next Steps:")
    print("1. Install streamlit-plotly-events")
    print("2. Add custom data to each surface (zone_id, surface_id)")
    print("3. Implement click handler with plotly_events")
    print("4. Add selection state to session_state")
    print("5. Re-render figure with highlight colors")
    print("6. Display selected element properties")
    print()
    print("Generated test files:")
    print("  • /tmp/plotly_click_test.html")
    print("  • /tmp/plotly_highlight_test.html")
    print("  • /tmp/plotly_hover_test.html")
    print()


if __name__ == '__main__':
    main()
