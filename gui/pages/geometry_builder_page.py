"""
ECO Tools - Geometry Builder Page

Streamlit interface for 3D building geometry creation.
Includes comprehensive error boundaries to prevent crashes.

Features:
- Create zones from polygons or presets
- Push/pull surfaces
- Copy/paste and array operations
- Floor plan tracing
- 3D visualization
- EMJSON export
"""

import streamlit as st
import sys
from pathlib import Path

# Add paths for imports (v7 uses eco_tools)
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Import configuration
try:
    from config import is_feature_enabled, get_feature_config
except ImportError:
    # Fallback if config not available
    def is_feature_enabled(name): return True
    def get_feature_config(name): return {'beta': True, 'show_warning': True}


def geometry_builder_page():
    """
    Main geometry builder page with complete error isolation

    This function wraps all geometry builder functionality with try/except
    to prevent errors from crashing the main application.
    """
    try:
        # Check if feature is enabled
        if not is_feature_enabled('geometry_builder'):
            st.info("🔒 Geometry Builder is currently disabled")
            st.write("This feature can be enabled in the configuration.")
            return

        # Show beta warning if configured
        feature_config = get_feature_config('geometry_builder')
        if feature_config.get('show_warning', False):
            st.warning(
                "🧪 **Beta Feature**: Geometry Builder is experimental. "
                "Always verify exported models using the Import page before further processing."
            )

        # Lazy import - only loads if page is accessed
        try:
            from eco_tools.geometry_builder import (
                GeometryBuilder,
                EMJSONAdapter,
                GeometryBuilderError
            )
        except ImportError as e:
            st.error("⚠️ Geometry Builder module not available")
            st.info(
                "The geometry builder module could not be loaded. "
                "This is an optional feature. Main ECO Tools functionality is unaffected."
            )
            with st.expander("Show technical details"):
                st.exception(e)
            return

        # Import plotly for 3D visualization
        try:
            import plotly.graph_objects as go
            import numpy as np
        except ImportError:
            st.error("⚠️ Required visualization libraries not available")
            st.info("Please install: `pip install plotly numpy`")
            return

        # All imports successful - render the page
        _render_geometry_builder(GeometryBuilder, EMJSONAdapter, go, np)

    except GeometryBuilderError as e:
        # Geometry builder specific error
        st.error(f"⚠️ Geometry Builder Error: {e}")
        st.warning("You can continue working with existing geometry or reset the builder.")
        if st.button("Reset Geometry Builder"):
            _reset_geometry_builder_state()
            st.rerun()

    except Exception as e:
        # Unexpected error - show but don't crash
        st.error("⚠️ An unexpected error occurred in Geometry Builder")
        st.warning(
            "The main ECO Tools application is still functional. "
            "You can use the Import page to continue working."
        )
        with st.expander("Show error details"):
            st.exception(e)

        if st.button("Reset Geometry Builder"):
            _reset_geometry_builder_state()
            st.rerun()


def _init_session_state(GeometryBuilder):
    """Initialize session state variables with unique prefixes"""
    if 'gb_builder' not in st.session_state:
        st.session_state.gb_builder = GeometryBuilder()
    if 'gb_traced_points' not in st.session_state:
        st.session_state.gb_traced_points = []
    if 'gb_floor_plan_image' not in st.session_state:
        st.session_state.gb_floor_plan_image = None
    if 'gb_scale_calibrated' not in st.session_state:
        st.session_state.gb_scale_calibrated = False


def _reset_geometry_builder_state():
    """Reset only geometry builder state, leaving other session state intact"""
    keys_to_reset = [k for k in st.session_state.keys() if k.startswith('gb_')]
    for key in keys_to_reset:
        del st.session_state[key]


def _render_geometry_builder(GeometryBuilder, EMJSONAdapter, go, np):
    """Actual page implementation - isolated from error handler"""

    _init_session_state(GeometryBuilder)

    st.title("🏗️ Geometry Builder")
    st.markdown("**SketchUp-style 3D modeling for building energy models**")

    # Sidebar - Tools
    with st.sidebar:
        st.header("🛠️ Tools")

        tool = st.radio(
            "Select Tool",
            [
                "📐 Quick Create",
                "✏️ Draw Polygon",
                "⬆️ Push/Pull",
                "📋 Copy Zone",
                "📏 Array Zones",
                "🗑️ Delete Zone",
                "💾 Export EMJSON"
            ]
        )

        st.divider()

        # Model Stats
        st.subheader("📊 Model Stats")
        try:
            stats = st.session_state.gb_builder.get_stats()
            st.metric("Zones", stats['zone_count'])
            st.metric("Surfaces", stats['surface_count'])
            st.metric("Floor Area", f"{stats['total_floor_area_m2']:.1f} m²")

            # Clear button
            if stats['zone_count'] > 0:
                if st.button("🗑️ Clear All", use_container_width=True):
                    st.session_state.gb_builder.clear()
                    st.success("Cleared all geometry")
                    st.rerun()
        except Exception as e:
            st.error(f"Error getting stats: {e}")

    # Main content area - route to appropriate tool
    try:
        if tool == "📐 Quick Create":
            _show_quick_create_tool()
        elif tool == "✏️ Draw Polygon":
            _show_draw_polygon_tool()
        elif tool == "⬆️ Push/Pull":
            _show_push_pull_tool()
        elif tool == "📋 Copy Zone":
            _show_copy_zone_tool()
        elif tool == "📏 Array Zones":
            _show_array_zones_tool()
        elif tool == "🗑️ Delete Zone":
            _show_delete_zone_tool()
        elif tool == "💾 Export EMJSON":
            _show_export_tool(EMJSONAdapter)
    except Exception as e:
        st.error(f"Error in tool '{tool}': {e}")
        with st.expander("Show details"):
            st.exception(e)

    # Always show 3D view at bottom
    st.divider()
    try:
        _show_3d_view(go, np)
    except Exception as e:
        st.error(f"Error rendering 3D view: {e}")
        import traceback
        with st.expander("Show full error"):
            st.code(traceback.format_exc())


def _show_quick_create_tool():
    """Quick create rectangular rooms"""
    st.header("📐 Quick Create")
    st.info("💡 Create simple rectangular zones quickly")

    col1, col2 = st.columns(2)
    with col1:
        width = st.number_input("Width (m)", value=5.0, min_value=0.1, max_value=50.0, step=0.5)
        height = st.number_input("Height (m)", value=2.7, min_value=2.0, max_value=5.0, step=0.1)
    with col2:
        depth = st.number_input("Depth (m)", value=4.0, min_value=0.1, max_value=50.0, step=0.5)
        zone_name = st.text_input("Zone Name", value=f"Zone {len(st.session_state.gb_builder.zones) + 1}")

    col1, col2 = st.columns(2)
    with col1:
        origin_x = st.number_input("Origin X (m)", value=0.0, step=1.0)
    with col2:
        origin_y = st.number_input("Origin Y (m)", value=0.0, step=1.0)

    if st.button("Create Rectangular Zone", type="primary", use_container_width=True):
        try:
            zone = st.session_state.gb_builder.create_rectangular_zone(
                width=width,
                depth=depth,
                height=height,
                origin=(origin_x, origin_y),
                zone_name=zone_name
            )
            st.success(f"✅ Created {zone.name}!")
            st.rerun()
        except Exception as e:
            st.error(f"Error creating zone: {e}")


def _show_draw_polygon_tool():
    """Draw custom polygon zones"""
    st.header("✏️ Draw Polygon")
    st.info("💡 Create zones from custom polygon footprints")

    # Preset shapes
    shape = st.selectbox("Preset Shape", ["Custom", "Rectangle", "L-Shape", "T-Shape"])

    vertices_2d = None

    if shape == "Rectangle":
        col1, col2 = st.columns(2)
        w = col1.number_input("Width (m)", value=5.0, min_value=0.1, key="poly_w")
        d = col2.number_input("Depth (m)", value=4.0, min_value=0.1, key="poly_d")
        vertices_2d = [(0, 0), (w, 0), (w, d), (0, d)]

    elif shape == "L-Shape":
        st.write("**L-Shape Parameters**")
        col1, col2 = st.columns(2)
        w1 = col1.number_input("Width 1 (m)", value=6.0, min_value=0.1, key="l_w1")
        w2 = col1.number_input("Width 2 (m)", value=3.0, min_value=0.1, key="l_w2")
        d1 = col2.number_input("Depth 1 (m)", value=3.0, min_value=0.1, key="l_d1")
        d2 = col2.number_input("Depth 2 (m)", value=5.0, min_value=0.1, key="l_d2")
        vertices_2d = [(0, 0), (w1, 0), (w1, d1), (w2, d1), (w2, d2), (0, d2)]

    elif shape == "T-Shape":
        st.info("T-Shape coming soon!")
        return

    else:  # Custom
        coord_text = st.text_area(
            "Vertices (x,y pairs, one per line)",
            value="0,0\n5,0\n5,4\n0,4",
            help="Enter coordinates as x,y (one pair per line)"
        )
        try:
            lines = [line.strip() for line in coord_text.split('\n') if line.strip()]
            vertices_2d = []
            for line in lines:
                x, y = map(float, line.split(','))
                vertices_2d.append((x, y))
        except:
            st.error("Invalid coordinates")
            return

    if vertices_2d:
        # Calculate and show footprint area
        area_2d = 0
        for i in range(len(vertices_2d)):
            x1, y1 = vertices_2d[i]
            x2, y2 = vertices_2d[(i + 1) % len(vertices_2d)]
            area_2d += x1 * y2 - x2 * y1
        area_2d = abs(area_2d) / 2

        col1, col2 = st.columns(2)
        col1.metric("Footprint Area", f"{area_2d:.2f} m²")
        height = col2.number_input("Height (m)", value=2.7, min_value=0.1, key="poly_height")

        zone_name = st.text_input("Zone Name", value=f"Zone {len(st.session_state.gb_builder.zones) + 1}", key="poly_name")

        if st.button("Create Zone", type="primary", use_container_width=True):
            try:
                zone = st.session_state.gb_builder.create_zone_from_polygon(
                    vertices_2d, height, zone_name=zone_name
                )
                st.success(f"✅ Created {zone.name}")
                st.balloons()
                st.rerun()
            except Exception as e:
                st.error(f"Error: {e}")


def _show_push_pull_tool():
    """Push/pull surface modification"""
    st.header("⬆️ Push/Pull Surfaces")
    st.info("💡 Modify surfaces by pushing or pulling along their normal")

    if not st.session_state.gb_builder.surfaces:
        st.warning("No surfaces available. Create a zone first!")
        return

    # Select surface
    surface_options = {s.id: s for s in st.session_state.gb_builder.surfaces}
    selected_id = st.selectbox(
        "Select Surface",
        options=list(surface_options.keys()),
        format_func=lambda x: f"{x} ({surface_options[x].type})"
    )

    if selected_id:
        surface = surface_options[selected_id]

        # Show surface info
        col1, col2, col3 = st.columns(3)
        col1.metric("Type", surface.type)
        col2.metric("Area", f"{surface.calculate_area():.2f} m²")
        col3.metric("Tilt", f"{surface.calculate_tilt():.1f}°")

        distance = st.slider(
            "Push/Pull Distance (m)",
            min_value=-5.0,
            max_value=5.0,
            value=0.0,
            step=0.1,
            help="Positive = push out, Negative = pull in"
        )

        if st.button("Apply Push/Pull", type="primary", disabled=(distance == 0)):
            try:
                st.session_state.gb_builder.push_pull_surface(selected_id, distance)
                st.success(f"✅ Applied push/pull: {distance:+.2f} m")
                st.rerun()
            except Exception as e:
                st.error(f"Error: {e}")


def _show_copy_zone_tool():
    """Copy zone with offset"""
    st.header("📋 Copy Zone")
    st.info("💡 Duplicate a zone and place it at a new location")

    if not st.session_state.gb_builder.zones:
        st.warning("No zones available. Create a zone first!")
        return

    zone_options = {z.id: z for z in st.session_state.gb_builder.zones}
    selected_id = st.selectbox(
        "Select Zone to Copy",
        options=list(zone_options.keys()),
        format_func=lambda x: f"{zone_options[x].name}"
    )

    if selected_id:
        zone = zone_options[selected_id]

        col1, col2 = st.columns(2)
        col1.metric("Floor Area", f"{zone.calculate_floor_area():.2f} m²")
        col2.metric("Surfaces", len(zone.surfaces))

        st.subheader("Copy Offset")
        col1, col2, col3 = st.columns(3)
        offset_x = col1.number_input("X Offset (m)", value=5.0, step=0.5)
        offset_y = col2.number_input("Y Offset (m)", value=0.0, step=0.5)
        offset_z = col3.number_input("Z Offset (m)", value=0.0, step=0.5)

        if st.button("Copy Zone", type="primary", use_container_width=True):
            try:
                new_zone = st.session_state.gb_builder.copy_zone(
                    selected_id,
                    offset=(offset_x, offset_y, offset_z)
                )
                st.success(f"✅ Created {new_zone.name}")
                st.rerun()
            except Exception as e:
                st.error(f"Error: {e}")


def _show_array_zones_tool():
    """Create zone arrays"""
    st.header("📏 Array Zones")
    st.info("💡 Create multiple copies in a linear pattern")

    if not st.session_state.gb_builder.zones:
        st.warning("No zones available. Create a zone first!")
        return

    zone_options = {z.id: z for z in st.session_state.gb_builder.zones}
    selected_id = st.selectbox(
        "Select Zone to Array",
        options=list(zone_options.keys()),
        format_func=lambda x: f"{zone_options[x].name}"
    )

    if selected_id:
        count = st.number_input("Number of Copies", value=3, min_value=1, max_value=20)

        col1, col2 = st.columns(2)
        spacing_x = col1.number_input("X Spacing (m)", value=6.0, step=0.5)
        spacing_y = col2.number_input("Y Spacing (m)", value=0.0, step=0.5)

        st.info(f"This will create {count} new zones")

        if st.button("Create Array", type="primary", use_container_width=True):
            try:
                new_zones = st.session_state.gb_builder.array_zones(
                    selected_id, count, spacing_x, spacing_y
                )
                st.success(f"✅ Created {len(new_zones)} zones")
                st.balloons()
                st.rerun()
            except Exception as e:
                st.error(f"Error: {e}")


def _show_delete_zone_tool():
    """Delete zones"""
    st.header("🗑️ Delete Zone")
    st.warning("⚠️ This will permanently delete the zone and all its surfaces")

    if not st.session_state.gb_builder.zones:
        st.info("No zones to delete")
        return

    zone_options = {z.id: z for z in st.session_state.gb_builder.zones}
    selected_id = st.selectbox(
        "Select Zone to Delete",
        options=list(zone_options.keys()),
        format_func=lambda x: f"{zone_options[x].name}"
    )

    if selected_id:
        zone = zone_options[selected_id]
        st.write(f"**{zone.name}**")
        st.write(f"- Surfaces: {len(zone.surfaces)}")
        st.write(f"- Floor Area: {zone.calculate_floor_area():.2f} m²")

        if st.button("⚠️ Delete Zone", type="secondary"):
            try:
                st.session_state.gb_builder.delete_zone(selected_id)
                st.success(f"Deleted {zone.name}")
                st.rerun()
            except Exception as e:
                st.error(f"Error: {e}")


def _show_export_tool(EMJSONAdapter):
    """Export to EMJSON"""
    st.header("💾 Export to EMJSON")

    if not st.session_state.gb_builder.zones:
        st.warning("No geometry to export. Create some zones first!")
        return

    # Validation
    st.subheader("Geometry Validation")
    try:
        result = st.session_state.gb_builder.validate_geometry()
        summary = st.session_state.gb_builder.get_validation_summary()

        if result['valid']:
            st.success(summary)
        else:
            st.warning(summary)

            # Show issues
            if result['issues']:
                with st.expander(f"Show {len(result['issues'])} issues"):
                    for issue in result['issues'][:20]:
                        level_icon = "⚠️" if issue['level'] == 'warning' else "❌"
                        st.write(f"{level_icon} {issue.get('surface_id', issue.get('zone_id', 'Model'))}: {issue['message']}")
    except Exception as e:
        st.error(f"Validation error: {e}")

    # Export preview
    st.subheader("Export Preview")
    try:
        summary = EMJSONAdapter.get_export_summary(st.session_state.gb_builder)

        col1, col2, col3 = st.columns(3)
        col1.metric("Zones", summary['zone_count'])
        col2.metric("Surfaces", summary['total_surfaces'])
        col3.metric("Floor Area", f"{summary['total_floor_area_m2']:.1f} m²")
    except Exception as e:
        st.error(f"Error generating summary: {e}")
        return

    # Export button
    project_name = st.text_input("Project Name", value="Geometry Builder Model")

    if st.button("Generate EMJSON", type="primary", use_container_width=True):
        try:
            import json
            emjson = EMJSONAdapter.to_emjson(st.session_state.gb_builder, project_name)

            # Download button
            st.download_button(
                label="📥 Download EMJSON",
                data=json.dumps(emjson, indent=2),
                file_name="geometry_model.emjson",
                mime="application/json",
                use_container_width=True
            )

            # Preview
            with st.expander("Preview EMJSON"):
                st.json(emjson)

            st.success("✅ EMJSON generated! Click download button above.")

        except Exception as e:
            st.error(f"Export failed: {e}")


def _show_3d_view(go, np):
    """3D visualization of model"""
    st.header("🔮 3D View")

    if not st.session_state.gb_builder.zones:
        st.info("Create some geometry to see the 3D view")
        return

    try:
        fig = _create_zone_visualization(st.session_state.gb_builder.zones, go, np)
        st.plotly_chart(fig, use_container_width=True)
        st.caption("💡 Click and drag to rotate • Scroll to zoom • Hold shift and drag to pan")
    except Exception as e:
        st.error(f"Error rendering 3D view: {e}")
        import traceback
        st.code(traceback.format_exc())


def _create_zone_visualization(zones, go, np):
    """Create Plotly 3D visualization with wireframe edges"""
    fig = go.Figure()

    color_map = {
        'exterior_wall': 'tan',
        'interior_wall': 'lightgray',
        'roof': 'darkred',
        'floor': 'lightgreen',
        'window': 'lightblue',
        'door': 'brown'
    }

    # Collect all vertices to compute bounds
    all_x, all_y, all_z = [], [], []

    for zone in zones:
        for surface in zone.surfaces:
            vertices = np.array([v.to_array() for v in surface.vertices])

            # Track bounds
            all_x.extend(vertices[:, 0])
            all_y.extend(vertices[:, 1])
            all_z.extend(vertices[:, 2])

            # Add surface as mesh
            if len(vertices) == 4:
                i = [0, 0]
                j = [1, 2]
                k = [2, 3]
            else:
                i = [0] * (len(vertices) - 2)
                j = list(range(1, len(vertices) - 1))
                k = list(range(2, len(vertices)))

            color = color_map.get(surface.type, 'gray')
            opacity = 0.5 if surface.type == 'window' else 0.7

            fig.add_trace(go.Mesh3d(
                x=vertices[:, 0],
                y=vertices[:, 1],
                z=vertices[:, 2],
                i=i, j=j, k=k,
                color=color,
                opacity=opacity,
                name=surface.id,
                hovertext=f"{surface.type}<br>Area: {surface.calculate_area():.2f} m²",
                hoverinfo='text',
                showlegend=False
            ))

            # Add wireframe edges for better visibility
            edge_x, edge_y, edge_z = [], [], []
            for i in range(len(vertices)):
                next_i = (i + 1) % len(vertices)
                edge_x.extend([vertices[i, 0], vertices[next_i, 0], None])
                edge_y.extend([vertices[i, 1], vertices[next_i, 1], None])
                edge_z.extend([vertices[i, 2], vertices[next_i, 2], None])

            fig.add_trace(go.Scatter3d(
                x=edge_x, y=edge_y, z=edge_z,
                mode='lines',
                line=dict(color='black', width=3),
                hoverinfo='skip',
                showlegend=False
            ))

    # Calculate scene bounds
    if all_x and all_y and all_z:
        x_range = max(all_x) - min(all_x) or 1
        y_range = max(all_y) - min(all_y) or 1
        z_range = max(all_z) - min(all_z) or 1
        max_range = max(x_range, y_range, z_range)

        fig.update_layout(
            scene=dict(
                xaxis=dict(
                    title='X (m)',
                    range=[min(all_x) - max_range*0.1, max(all_x) + max_range*0.1]
                ),
                yaxis=dict(
                    title='Y (m)',
                    range=[min(all_y) - max_range*0.1, max(all_y) + max_range*0.1]
                ),
                zaxis=dict(
                    title='Z (m)',
                    range=[min(all_z) - z_range*0.1, max(all_z) + z_range*0.2]
                ),
                aspectmode='data'
            ),
            title='3D Building Model',
            showlegend=False,
            height=600,
            margin=dict(l=0, r=0, t=40, b=0)
        )

    return fig


# Main entry point
if __name__ == "__main__":
    geometry_builder_page()
