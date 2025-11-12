import streamlit as st
import json
import sys
from pathlib import Path

# Add project root to path
ROOT = Path(__file__).resolve().parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Add explorer_gui to path
EXPLORER_GUI = ROOT / "explorer_gui"
if str(EXPLORER_GUI) not in sys.path:
    sys.path.insert(0, str(EXPLORER_GUI))

from import_export import emjson6_to_cibd22x

# Import 3D visualizer
try:
    from utils.geometry_visualizer import visualize_model, GeometryVisualizer
    VISUALIZER_AVAILABLE = True
except ImportError:
    VISUALIZER_AVAILABLE = False

# Import plotly events for selection
try:
    from streamlit_plotly_events import plotly_events
    PLOTLY_EVENTS_AVAILABLE = True
except ImportError:
    PLOTLY_EVENTS_AVAILABLE = False


def render_tree_node(label: str, data: any, level: int = 0, in_expander: bool = False):
    """Render a tree node without nesting expanders."""
    indent = "  " * level

    if isinstance(data, dict):
        # Don't create nested expanders - just show as collapsible JSON or formatted text
        if in_expander:
            st.markdown(f"{indent}**📁 {label}** ({len(data)} items)")
            for key, value in data.items():
                render_tree_node(key, value, level + 1, in_expander=True)
        else:
            # Only create expander at top level
            st.markdown(f"{indent}**📁 {label}** ({len(data)} items)")
            for key, value in data.items():
                render_tree_node(key, value, level + 1, in_expander=False)
    elif isinstance(data, list):
        if in_expander:
            st.markdown(f"{indent}**📋 {label}** ({len(data)} items)")
            for i, item in enumerate(data[:5]):  # Limit display to first 5 items
                if isinstance(item, dict):
                    item_name = item.get("name", item.get("id", f"Item {i+1}"))
                    st.markdown(f"{indent}  • {item_name}")
                else:
                    st.markdown(f"{indent}  • {item}")
            if len(data) > 5:
                st.markdown(f"{indent}  • ... and {len(data) - 5} more items")
        else:
            st.markdown(f"{indent}**📋 {label}** ({len(data)} items)")
            for i, item in enumerate(data[:5]):  # Limit display to first 5 items
                if isinstance(item, dict):
                    item_name = item.get("name", item.get("id", f"Item {i+1}"))
                    st.markdown(f"{indent}  • {item_name}")
                else:
                    st.markdown(f"{indent}  • {item}")
            if len(data) > 5:
                st.markdown(f"{indent}  • ... and {len(data) - 5} more items")
    else:
        st.markdown(f"{indent}🔹 **{label}:** `{data}`")


def show_tree_navigator(model: dict):
    """Display a tree-style navigator for the EMJSON model."""
    st.subheader("🌲 Model Tree Navigator")

    # Project level
    if "project" in model:
        with st.expander("📦 Project", expanded=True):
            project = model["project"]
            for key, value in project.items():
                if key == "location":
                    st.markdown("**📍 Location**")
                    st.json(value)
                else:
                    render_tree_node(key, value, level=1, in_expander=True)
    
    # Geometry level
    if "geometry" in model:
        with st.expander("🏗️ Geometry", expanded=True):
            geom = model["geometry"]
            
            # Zones
            zones = geom.get("zones", [])
            if zones:
                st.markdown(f"**🏢 Zones** ({len(zones)} zones)")
                for zone in zones:
                    zone_name = zone.get("name", zone.get("id", "Unknown"))
                    zone_type = zone.get("type", "")
                    area = zone.get("floor_area_m2", zone.get("area"))
                    area_str = f"{area:.1f} m²" if area is not None else "N/A"

                    st.markdown(f"  • **{zone_name}** ({zone_type}) - {area_str}")

                    # Show surfaces under this zone
                    zone_surfaces = zone.get("surfaces", [])
                    if zone_surfaces:
                        st.markdown(f"    🧱 Surfaces: {len(zone_surfaces)}")
            
            # Surfaces (if not nested under zones)
            surfaces = geom.get("surfaces", {})
            if surfaces and not zones:
                if isinstance(surfaces, dict):
                    total = sum(len(v) for v in surfaces.values() if isinstance(v, list))
                    st.markdown(f"**🧱 Surfaces** ({total} total)")
                    for category, surf_list in surfaces.items():
                        if isinstance(surf_list, list):
                                render_tree_node(category, surf_list, level=2)
                elif isinstance(surfaces, list):
                    st.markdown(f"**🧱 Surfaces** ({len(surfaces)} surfaces)")
                    for surf in surfaces[:10]:  # Show first 10
                        surf_name = surf.get("name", surf.get("id", "Unknown"))
                        st.markdown(f"  • {surf_name}")
                    if len(surfaces) > 10:
                        st.markdown(f"  • ... and {len(surfaces) - 10} more")
            
            # Openings
            openings = geom.get("openings", {})
            if openings:
                if isinstance(openings, dict):
                    total = sum(len(v) for v in openings.values() if isinstance(v, list))
                    st.markdown(f"**🪟 Openings** ({total} total)")
                    for category, open_list in openings.items():
                        if isinstance(open_list, list):
                            st.markdown(f"  • {category}: {len(open_list)} items")
    
    # Catalogs level
    if "catalogs" in model:
        with st.expander("📚 Catalogs", expanded=False):
            catalogs = model["catalogs"]
            for cat_name, cat_items in catalogs.items():
                if isinstance(cat_items, list):
                    st.markdown(f"**📖 {cat_name.replace('_', ' ').title()}** ({len(cat_items)} items)")
                    for item in cat_items[:5]:  # Show first 5
                        if isinstance(item, dict):
                            item_name = item.get("name", item.get("id", "Unknown"))
                            st.markdown(f"  • {item_name}")
                        else:
                            st.markdown(f"  • {item}")
                    if len(cat_items) > 5:
                        st.markdown(f"  • ... and {len(cat_items) - 5} more")
    
    # Systems level
    if "systems" in model:
        with st.expander("🔧 Systems", expanded=False):
            systems = model["systems"]

            hvac = systems.get("hvac", [])
            if hvac:
                st.markdown(f"**❄️ HVAC Systems** ({len(hvac)} systems)")
                for sys in hvac:
                    sys_name = sys.get("name", sys.get("id", "Unknown"))
                    st.markdown(f"  • {sys_name}")

            dhw = systems.get("dhw", [])
            if dhw:
                st.markdown(f"**🚿 DHW Systems** ({len(dhw)} systems)")
                for sys in dhw:
                    sys_name = sys.get("name", sys.get("id", "Unknown"))
                    st.markdown(f"  • {sys_name}")

            pv = systems.get("pv", [])
            if pv:
                st.markdown(f"**☀️ PV Arrays** ({len(pv)} arrays)")
                for sys in pv:
                    sys_name = sys.get("name", sys.get("id", "Unknown"))
                    st.markdown(f"  • {sys_name}")


def show_selected_element_properties(model: dict):
    """Display properties of the currently selected element"""

    selected_surface = st.session_state.get('selected_surface')
    selected_zone = st.session_state.get('selected_zone')

    if not selected_surface and not selected_zone:
        st.info("🖱️ Click on a surface in the 3D view to see its properties")
        return

    # Find the selected element in the model
    geometry = model.get('geometry', {})
    zones = geometry.get('zones', [])

    # Try to find the selected surface
    if selected_surface:
        st.subheader("🧱 Selected Surface")

        # Search for the surface
        found_surface = None
        parent_zone = None

        for zone in zones:
            for surface in zone.get('surfaces', []):
                surf_id = surface.get('id', surface.get('name'))
                if surf_id == selected_surface:
                    found_surface = surface
                    parent_zone = zone
                    break
            if found_surface:
                break

        if found_surface:
            # Display surface properties
            col1, col2 = st.columns(2)

            with col1:
                st.metric("Name", found_surface.get('name', 'Unknown'))
                st.metric("Type", found_surface.get('type', 'N/A'))
                area = found_surface.get('area_m2', found_surface.get('area'))
                if area is not None:
                    st.metric("Area", f"{area:.2f} m²")

            with col2:
                if parent_zone:
                    st.metric("Zone", parent_zone.get('name', 'Unknown'))

                tilt = found_surface.get('tilt_deg')
                if tilt is not None:
                    st.metric("Tilt", f"{tilt:.0f}°")

                azimuth = found_surface.get('azimuth_deg')
                if azimuth is not None:
                    st.metric("Azimuth", f"{azimuth:.0f}°")

            # Additional properties
            st.divider()
            construction = found_surface.get('construction_id', found_surface.get('construction'))
            if construction:
                st.text(f"Construction: {construction}")

            vertices = found_surface.get('vertices_m', found_surface.get('vertices', []))
            st.text(f"Vertices: {len(vertices)}")

            # Clear selection button
            if st.button("❌ Clear Selection", key="clear_surface_selection"):
                st.session_state.selected_surface = None
                st.session_state.selected_zone = None
                st.rerun()
        else:
            st.warning(f"⚠️ Surface '{selected_surface}' not found in model")

    elif selected_zone:
        st.subheader("🏢 Selected Zone")

        # Find the zone
        found_zone = None
        for zone in zones:
            zone_id = zone.get('id', zone.get('name'))
            if zone_id == selected_zone:
                found_zone = zone
                break

        if found_zone:
            # Display zone properties
            col1, col2 = st.columns(2)

            with col1:
                st.metric("Name", found_zone.get('name', 'Unknown'))
                st.metric("Type", found_zone.get('type', found_zone.get('zone_type', 'N/A')))

            with col2:
                area = found_zone.get('floor_area_m2', found_zone.get('area'))
                if area is not None:
                    st.metric("Floor Area", f"{area:.2f} m²")

                volume = found_zone.get('volume_m3', found_zone.get('volume'))
                if volume is not None:
                    st.metric("Volume", f"{volume:.2f} m³")

            # Surface count
            st.divider()
            surfaces = found_zone.get('surfaces', [])
            st.text(f"Surfaces: {len(surfaces)}")

            # Clear selection button
            if st.button("❌ Clear Selection", key="clear_zone_selection"):
                st.session_state.selected_zone = None
                st.session_state.selected_surface = None
                st.rerun()
        else:
            st.warning(f"⚠️ Zone '{selected_zone}' not found in model")


def show_3d_visualization(model: dict):
    """Display 3D visualization of the model geometry (lazy loaded)"""

    if not VISUALIZER_AVAILABLE:
        st.warning("⚠️ 3D visualization not available. Install required dependencies.")
        st.code("pip install plotly", language="bash")
        return

    # Check if model has geometry data
    geometry = model.get('geometry', {})
    if not geometry:
        st.info("ℹ️ No geometry data available in this model")
        return

    # Show quick preview info before loading
    zones = geometry.get('zones', [])
    surfaces = geometry.get('surfaces', {})

    # Calculate surface count
    if isinstance(surfaces, dict):
        total_surfaces = sum(len(v) for v in surfaces.values() if isinstance(v, list))
    elif isinstance(surfaces, list):
        total_surfaces = len(surfaces)
    else:
        total_surfaces = 0

    # Preview info
    st.info(f"📊 Model contains **{len(zones)} zones** and **{total_surfaces} surfaces**")

    # Lazy loading using expander
    with st.expander("🏗️ **Load 3D Visualization**", expanded=False):
        st.caption("⏳ Visualization will generate when you expand this section")

        if PLOTLY_EVENTS_AVAILABLE:
            st.caption("✨ **Click on surfaces to select them and view properties**")
        else:
            st.caption("⚠️ Install `streamlit-plotly-events` for interactive selection")

        # Settings controls (shown before visualization)
        with st.expander("🎨 Visualization Settings", expanded=False):
            col1, col2 = st.columns(2)

            with col1:
                show_edges = st.checkbox("Show Edges", value=True, key="viz_edges")
                show_grid = st.checkbox("Show Grid", value=True, key="viz_grid")

            with col2:
                opacity = st.slider("Opacity", 0.0, 1.0, 0.7, 0.1, key="viz_opacity")
                height = st.slider("Height (px)", 400, 1000, 700, 50, key="viz_height")

        try:
            # This code only runs when expander is opened
            with st.spinner("🔄 Generating 3D visualization..."):
                visualizer = GeometryVisualizer()

                # Get project name for title
                project_name = model.get('project', {}).get('name', 'Building Model')

                # Get selected surface from session state (if any)
                selected_surface = st.session_state.get('selected_surface')

                # Generate figure with selection highlighting
                fig = visualizer.visualize_emjson(
                    model,
                    title=f"3D View: {project_name}",
                    selected_surface=selected_surface
                )

                # Update figure height
                fig.update_layout(height=height)

                # Display the figure with click events if available
                if PLOTLY_EVENTS_AVAILABLE:
                    # Use plotly_events to capture click events
                    selected_points = plotly_events(
                        fig,
                        click_event=True,
                        override_height=height,
                        key="geometry_viewer"
                    )

                    # Handle selection
                    if selected_points and len(selected_points) > 0:
                        point_data = selected_points[0]

                        # Extract custom data if available
                        if 'customdata' in point_data and point_data['customdata']:
                            customdata = point_data['customdata']

                            # customdata format: [zone_id, surface_id]
                            if len(customdata) >= 2:
                                zone_id = customdata[0]
                                surface_id = customdata[1]

                                # Update selection state
                                st.session_state.selected_zone = zone_id
                                st.session_state.selected_surface = surface_id

                                # Rerun to update visualization with highlight
                                st.rerun()
                else:
                    # Fallback: regular plotly chart without click handling
                    st.plotly_chart(fig, use_container_width=True)

                # Show quick stats and tips
                st.success("✅ Visualization loaded successfully!")
                if PLOTLY_EVENTS_AVAILABLE:
                    st.caption("💡 **Tip:** Click on any surface to select it. Use mouse to rotate (drag), zoom (scroll), and pan (right-click + drag)")
                else:
                    st.caption("💡 **Tip:** Use mouse to rotate (drag), zoom (scroll), and pan (right-click + drag)")

                # Option to download as HTML
                html_str = fig.to_html(include_plotlyjs='cdn')
                st.download_button(
                    label="📥 Download 3D Visualization (HTML)",
                    data=html_str,
                    file_name=f"{project_name.replace(' ', '_')}_3d_view.html",
                    mime="text/html",
                    key="download_3d_viz"
                )

                # Show selected element properties in expander
                if PLOTLY_EVENTS_AVAILABLE:
                    st.divider()
                    with st.expander("🔍 Selected Element Properties", expanded=True):
                        show_selected_element_properties(model)

        except Exception as e:
            st.error(f"❌ Visualization error: {str(e)}")
            with st.expander("Show error details"):
                import traceback
                st.code(traceback.format_exc())


def show_geometry_statistics(model: dict):
    """Display geometry statistics and metrics"""
    st.subheader("📊 Geometry Statistics")

    if not VISUALIZER_AVAILABLE:
        st.info("Install visualization module for detailed statistics")
        return

    geometry = model.get('geometry', {})
    if not geometry:
        st.info("ℹ️ No geometry data available")
        return

    try:
        visualizer = GeometryVisualizer()
        stats = visualizer.get_geometry_stats(model)

        # Display summary cards
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric("🏢 Zones", stats['zones'])

        with col2:
            st.metric("🧱 Surfaces", stats['surfaces'])

        with col3:
            st.metric("🪟 Openings", stats['openings'])

        with col4:
            floor_area = stats['total_floor_area_m2']
            st.metric("📐 Floor Area", f"{floor_area:.1f} m²")

        # Volume metric (full width)
        if stats['total_volume_m3'] > 0:
            st.metric("📦 Total Volume", f"{stats['total_volume_m3']:.1f} m³")

        # Surface breakdown
        if stats.get('surface_types'):
            st.divider()
            st.subheader("Surface Breakdown")

            # Create columns for surface types
            surf_types = stats['surface_types']
            cols = st.columns(min(len(surf_types), 4))

            for idx, (surf_type, count) in enumerate(surf_types.items()):
                col_idx = idx % 4
                with cols[col_idx]:
                    # Format surface type name
                    display_name = surf_type.replace('_', ' ').title()
                    st.metric(display_name, count)

        # Detailed zone information
        zones = geometry.get('zones', [])
        if zones:
            st.divider()
            st.subheader("Zone Details")

            # Create a table of zone information
            zone_data = []
            for zone in zones:
                zone_info = {
                    'Name': zone.get('name', 'Unknown'),
                    'Type': zone.get('type', zone.get('zone_type', 'N/A')),
                    'Floor Area (m²)': round(zone.get('floor_area_m2', zone.get('area', 0)), 2),
                    'Volume (m³)': round(zone.get('volume_m3', zone.get('volume', 0)), 2),
                    'Surfaces': len(zone.get('surfaces', []))
                }
                zone_data.append(zone_info)

            # Display as dataframe
            import pandas as pd
            df = pd.DataFrame(zone_data)
            st.dataframe(df, use_container_width=True, hide_index=True)

    except Exception as e:
        st.error(f"❌ Statistics error: {str(e)}")


def show_active_model():
    st.subheader("Active Model")

    # Check if there's an active model
    if 'active_model' in st.session_state:
        active_model = st.session_state['active_model']
        filename = st.session_state.get('active_model_filename', 'unknown')
        source = st.session_state.get('active_model_source', 'unknown')

        st.info(f"📄 **{filename}** (Source: {source})")
    else:
        st.warning("⚠️ No active model loaded. Please import a model first.")

        # Simulated active model data (fallback)
        active_model = {
            "location": {"latitude": 34.0522, "longitude": -118.2437},
            "geometry": {
                "zones": [{"name": "Zone 1", "area": 200}, {"name": "Zone 2", "area": 150}],
                "surfaces": [{"type": "wall", "area": 100}, {"type": "roof", "area": 200}],
                "openings": [{"type": "window", "area": 10}, {"type": "door", "area": 5}]
            },
            "catalogs": {
                "window_types": ["Type A", "Type B"],
                "construction_types": ["Concrete", "Wood"],
                "hvac_systems": ["System A", "System B"]
            }
        }

    # Add tabs for different views
    st.divider()

    # Check if geometry exists for conditional tab labels
    geometry = active_model.get('geometry', {})
    has_geometry = bool(geometry)

    if has_geometry:
        tab1, tab2, tab3 = st.tabs([
            "🔍 Tree Navigator",
            "🏗️ 3D Viewer (Click to Load)",
            "📊 Statistics"
        ])
    else:
        tab1, tab2, tab3 = st.tabs([
            "🔍 Tree Navigator",
            "🏗️ 3D Viewer",
            "📊 Statistics"
        ])

    with tab1:
        show_tree_navigator(active_model)

    with tab2:
        show_3d_visualization(active_model)

    with tab3:
        show_geometry_statistics(active_model)

    # Provide export options for the active model
    st.divider()
    st.subheader("💾 Export Active Model")

    col1, col2 = st.columns(2)

    with col1:
        # Export the model as EMJSON v6
        emjson_data = json.dumps(active_model, indent=2, ensure_ascii=False)
        st.download_button(
            label="Download as EMJSON v6",
            data=emjson_data.encode("utf-8"),
            file_name="active_model_v6.json",
            mime="application/json"
        )

    with col2:
        # Export the model as CIBD22x XML
        try:
            xml_data = emjson6_to_cibd22x(active_model)
            st.download_button(
                label="Download as CIBD22x XML",
                data=xml_data.encode("utf-8") if isinstance(xml_data, str) else xml_data,
                file_name="active_model_v6.xml",
                mime="application/xml"
            )
        except Exception as e:
            st.error(f"Export failed: {str(e)}")