"""
ECO Tools - Geometry Builder GUI
Streamlit prototype with 3D visualization

Install requirements:
pip install streamlit plotly pandas pillow

To run:
streamlit run geometry_builder_gui.py
"""

import streamlit as st
import plotly.graph_objects as go
import numpy as np
import json
from typing import List, Tuple, Optional
from PIL import Image
import io

# Import the geometry builder classes
# In production, this would be: from emtools.geometry_builder import GeometryBuilder, Point3D, etc.
from geometry_builder_prototype import (
    GeometryBuilder, 
    Point3D, 
    Surface, 
    Zone, 
    PushPullOperation,
    TraceManager
)


# ==================== Plotly 3D Visualization ====================

def create_surface_mesh(surface: Surface, color: str = 'tan', opacity: float = 0.8):
    """Create Plotly mesh for a surface"""
    vertices = np.array([v.to_array() for v in surface.vertices])
    
    # For simple quad surfaces, create two triangles
    if len(vertices) == 4:
        i = [0, 0]
        j = [1, 2]
        k = [2, 3]
    else:
        # Triangulate polygon (simple fan triangulation)
        i = [0] * (len(vertices) - 2)
        j = list(range(1, len(vertices) - 1))
        k = list(range(2, len(vertices)))
    
    mesh = go.Mesh3d(
        x=vertices[:, 0],
        y=vertices[:, 1],
        z=vertices[:, 2],
        i=i,
        j=j,
        k=k,
        color=color,
        opacity=opacity,
        name=surface.id,
        hovertext=f"{surface.type}<br>Area: {surface.calculate_area():.2f} m²",
        hoverinfo='text'
    )
    
    return mesh


def create_zone_visualization(zones: List[Zone]):
    """Create 3D visualization of zones"""
    fig = go.Figure()
    
    color_map = {
        'exterior_wall': 'tan',
        'interior_wall': 'lightgray',
        'roof': 'darkred',
        'floor': 'lightgreen',
        'window': 'lightblue',
        'door': 'brown'
    }
    
    for zone in zones:
        for surface in zone.surfaces:
            color = color_map.get(surface.type, 'gray')
            opacity = 0.6 if surface.type == 'window' else 0.8
            
            mesh = create_surface_mesh(surface, color=color, opacity=opacity)
            fig.add_trace(mesh)
    
    # Update layout
    fig.update_layout(
        scene=dict(
            xaxis_title='X (m)',
            yaxis_title='Y (m)',
            zaxis_title='Z (m)',
            aspectmode='data',
            camera=dict(
                eye=dict(x=1.5, y=1.5, z=1.2)
            )
        ),
        title='3D Building Model',
        showlegend=False,
        height=600
    )
    
    return fig


# ==================== Streamlit App ====================

def init_session_state():
    """Initialize session state variables"""
    if 'builder' not in st.session_state:
        st.session_state.builder = GeometryBuilder()
    if 'traced_points' not in st.session_state:
        st.session_state.traced_points = []
    if 'floor_plan_image' not in st.session_state:
        st.session_state.floor_plan_image = None
    if 'scale_calibrated' not in st.session_state:
        st.session_state.scale_calibrated = False


def main():
    st.set_page_config(page_title="ECO Geometry Builder", layout="wide")
    init_session_state()
    
    st.title("🏗️ ECO Tools - Geometry Builder")
    st.markdown("**SketchUp-style modeling for building energy models**")
    
    # Sidebar - Tools
    with st.sidebar:
        st.header("🛠️ Tools")
        
        tool = st.radio(
            "Select Tool",
            [
                "📐 Draw Polygon",
                "⬆️ Push/Pull",
                "📋 Copy Zone",
                "📏 Array Zones",
                "🖼️ Floor Plan Trace",
                "💾 Export EMJSON"
            ]
        )
        
        st.divider()
        
        # Quick Create Section
        st.subheader("Quick Create")
        
        col1, col2 = st.columns(2)
        with col1:
            width = st.number_input("Width (m)", value=5.0, min_value=1.0, max_value=50.0, step=0.5)
        with col2:
            depth = st.number_input("Depth (m)", value=4.0, min_value=1.0, max_value=50.0, step=0.5)
        
        height = st.number_input("Height (m)", value=2.7, min_value=2.0, max_value=5.0, step=0.1)
        
        if st.button("Create Rectangular Room", use_container_width=True):
            footprint = [(0, 0), (width, 0), (width, depth), (0, depth)]
            zone = st.session_state.builder.create_zone_from_polygon(
                footprint, 
                height, 
                zone_id=f"room_{len(st.session_state.builder.zones)}"
            )
            st.success(f"Created {zone.name}!")
            st.rerun()
        
        st.divider()
        
        # Model Stats
        st.subheader("📊 Model Stats")
        st.metric("Zones", len(st.session_state.builder.zones))
        st.metric("Surfaces", len(st.session_state.builder.surfaces))
        
        total_floor_area = sum(z.calculate_floor_area() for z in st.session_state.builder.zones)
        st.metric("Total Floor Area", f"{total_floor_area:.1f} m²")
    
    # Main content area
    if tool == "📐 Draw Polygon":
        show_draw_polygon_tool()
    
    elif tool == "⬆️ Push/Pull":
        show_push_pull_tool()
    
    elif tool == "📋 Copy Zone":
        show_copy_zone_tool()
    
    elif tool == "📏 Array Zones":
        show_array_zones_tool()
    
    elif tool == "🖼️ Floor Plan Trace":
        show_floor_plan_trace_tool()
    
    elif tool == "💾 Export EMJSON":
        show_export_tool()
    
    # Always show 3D view at bottom
    st.divider()
    show_3d_view()


def show_draw_polygon_tool():
    """Draw polygon tool interface"""
    st.header("📐 Draw Polygon")
    
    st.info("💡 Enter polygon vertices to create a zone footprint, then extrude to 3D")
    
    # Input method selection
    input_method = st.radio(
        "Input Method",
        ["Enter Coordinates", "Use Preset Shapes", "Custom Points"]
    )
    
    vertices_2d = None
    
    if input_method == "Enter Coordinates":
        st.write("Enter vertices as comma-separated pairs (x,y)")
        coord_text = st.text_area(
            "Vertices",
            value="0,0\n5,0\n5,4\n0,4",
            help="One coordinate pair per line: x,y"
        )
        
        try:
            lines = [line.strip() for line in coord_text.split('\n') if line.strip()]
            vertices_2d = []
            for line in lines:
                x, y = map(float, line.split(','))
                vertices_2d.append((x, y))
        except Exception as e:
            st.error(f"Invalid coordinates: {e}")
            return
    
    elif input_method == "Use Preset Shapes":
        shape = st.selectbox("Shape", ["Rectangle", "L-Shape", "T-Shape", "U-Shape"])
        
        if shape == "Rectangle":
            w = st.number_input("Width (m)", value=5.0, min_value=1.0)
            d = st.number_input("Depth (m)", value=4.0, min_value=1.0)
            vertices_2d = [(0, 0), (w, 0), (w, d), (0, d)]
        
        elif shape == "L-Shape":
            w1 = st.number_input("Width 1 (m)", value=6.0, min_value=1.0)
            w2 = st.number_input("Width 2 (m)", value=3.0, min_value=1.0)
            d1 = st.number_input("Depth 1 (m)", value=3.0, min_value=1.0)
            d2 = st.number_input("Depth 2 (m)", value=5.0, min_value=1.0)
            vertices_2d = [
                (0, 0), (w1, 0), (w1, d1), (w2, d1), (w2, d2), (0, d2)
            ]
        
        elif shape == "T-Shape":
            st.info("T-Shape: Coming soon!")
            return
        
        elif shape == "U-Shape":
            st.info("U-Shape: Coming soon!")
            return
    
    if vertices_2d:
        # Show preview
        st.write(f"**Vertices:** {len(vertices_2d)} points")
        
        # Calculate area
        area_2d = 0
        for i in range(len(vertices_2d)):
            x1, y1 = vertices_2d[i]
            x2, y2 = vertices_2d[(i + 1) % len(vertices_2d)]
            area_2d += x1 * y2 - x2 * y1
        area_2d = abs(area_2d) / 2
        
        st.metric("Footprint Area", f"{area_2d:.2f} m²")
        
        # Extrusion height
        height = st.number_input("Extrusion Height (m)", value=2.7, min_value=0.5, max_value=10.0, step=0.1)
        
        # Zone name
        zone_id = st.text_input("Zone ID", value=f"zone_{len(st.session_state.builder.zones)}")
        
        # Create button
        if st.button("Create Zone", type="primary", use_container_width=True):
            try:
                zone = st.session_state.builder.create_zone_from_polygon(
                    vertices_2d,
                    height,
                    zone_id=zone_id
                )
                st.success(f"✅ Created zone: {zone.name}")
                st.balloons()
                st.rerun()
            except Exception as e:
                st.error(f"Error creating zone: {e}")


def show_push_pull_tool():
    """Push/pull tool interface"""
    st.header("⬆️ Push/Pull Surfaces")
    
    st.info("💡 Select a surface and push/pull it along its normal")
    
    if not st.session_state.builder.surfaces:
        st.warning("No surfaces available. Create a zone first!")
        return
    
    # Select surface
    surface_options = {s.id: s for s in st.session_state.builder.surfaces}
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
        
        # Push/pull distance
        distance = st.slider(
            "Push/Pull Distance (m)",
            min_value=-5.0,
            max_value=5.0,
            value=0.0,
            step=0.1,
            help="Positive = push out, Negative = pull in"
        )
        
        # Preview normal direction
        st.write(f"**Normal Vector:** {surface.calculate_normal()}")
        st.write(f"**Azimuth:** {surface.calculate_azimuth():.1f}° (0°=N, 90°=E, 180°=S, 270°=W)")
        
        # Apply button
        if st.button("Apply Push/Pull", type="primary", disabled=(distance == 0)):
            try:
                st.session_state.builder.push_pull_surface(selected_id, distance)
                st.success(f"✅ Applied push/pull: {distance:+.2f} m")
                st.rerun()
            except Exception as e:
                st.error(f"Error: {e}")


def show_copy_zone_tool():
    """Copy zone tool interface"""
    st.header("📋 Copy Zone")
    
    st.info("💡 Copy a zone and place it at a new location")
    
    if not st.session_state.builder.zones:
        st.warning("No zones available. Create a zone first!")
        return
    
    # Select zone
    zone_options = {z.id: z for z in st.session_state.builder.zones}
    selected_id = st.selectbox(
        "Select Zone to Copy",
        options=list(zone_options.keys()),
        format_func=lambda x: f"{zone_options[x].name}"
    )
    
    if selected_id:
        zone = zone_options[selected_id]
        
        # Show zone info
        col1, col2 = st.columns(2)
        col1.metric("Floor Area", f"{zone.calculate_floor_area():.2f} m²")
        col2.metric("Volume", f"{zone.calculate_volume():.2f} m³")
        
        st.write(f"**Surfaces:** {len(zone.surfaces)}")
        
        # Offset
        st.subheader("Copy Offset")
        col1, col2, col3 = st.columns(3)
        offset_x = col1.number_input("X Offset (m)", value=5.0, step=0.5)
        offset_y = col2.number_input("Y Offset (m)", value=0.0, step=0.5)
        offset_z = col3.number_input("Z Offset (m)", value=0.0, step=0.5)
        
        # Copy button
        if st.button("Copy Zone", type="primary", use_container_width=True):
            try:
                new_zone = st.session_state.builder.copy_zone(
                    selected_id,
                    offset=(offset_x, offset_y, offset_z)
                )
                st.success(f"✅ Created copy: {new_zone.name}")
                st.rerun()
            except Exception as e:
                st.error(f"Error: {e}")


def show_array_zones_tool():
    """Array zones tool interface"""
    st.header("📏 Array Zones")
    
    st.info("💡 Create multiple copies in a linear pattern (like apartment units)")
    
    if not st.session_state.builder.zones:
        st.warning("No zones available. Create a zone first!")
        return
    
    # Select zone
    zone_options = {z.id: z for z in st.session_state.builder.zones}
    selected_id = st.selectbox(
        "Select Zone to Array",
        options=list(zone_options.keys()),
        format_func=lambda x: f"{zone_options[x].name}"
    )
    
    if selected_id:
        # Array parameters
        st.subheader("Array Parameters")
        
        count = st.number_input("Number of Copies", value=3, min_value=1, max_value=20)
        
        col1, col2 = st.columns(2)
        spacing_x = col1.number_input("X Spacing (m)", value=6.0, step=0.5)
        spacing_y = col2.number_input("Y Spacing (m)", value=0.0, step=0.5)
        
        st.info(f"This will create {count} new zones")
        
        # Array button
        if st.button("Create Array", type="primary", use_container_width=True):
            try:
                new_zones = st.session_state.builder.array_zones(
                    selected_id,
                    count=count,
                    spacing_x=spacing_x,
                    spacing_y=spacing_y
                )
                st.success(f"✅ Created {len(new_zones)} zones in array")
                st.balloons()
                st.rerun()
            except Exception as e:
                st.error(f"Error: {e}")


def show_floor_plan_trace_tool():
    """Floor plan tracing tool interface"""
    st.header("🖼️ Floor Plan Trace")
    
    st.info("💡 Upload a floor plan image, calibrate scale, and trace building outline")
    
    # File upload
    uploaded_file = st.file_uploader(
        "Upload Floor Plan",
        type=['png', 'jpg', 'jpeg', 'pdf'],
        help="Upload a floor plan image to trace"
    )
    
    if uploaded_file:
        # Load image
        image = Image.open(uploaded_file)
        st.session_state.floor_plan_image = image
        
        # Display image
        st.image(image, caption="Floor Plan", use_column_width=True)
        
        # Calibration
        st.subheader("Scale Calibration")
        st.write("Draw a line on a known dimension and enter its real-world length")
        
        col1, col2 = st.columns(2)
        pixel_distance = col1.number_input("Distance in Image (pixels)", value=100.0, min_value=1.0)
        real_distance = col2.number_input("Real Distance (m)", value=5.0, min_value=0.1)
        
        if st.button("Calibrate Scale"):
            st.session_state.builder.trace_manager.calibrate_scale(pixel_distance, real_distance)
            st.session_state.scale_calibrated = True
            st.success(f"✅ Scale set: 1 pixel = {real_distance/pixel_distance:.4f} m")
        
        if st.session_state.scale_calibrated:
            st.success(f"Scale: {st.session_state.builder.trace_manager.scale_factor:.4f} m/pixel")
            
            # Tracing interface
            st.subheader("Trace Outline")
            st.write("In a full implementation, you would click points on the image to trace the outline.")
            st.write("For this prototype, enter coordinates manually after measuring from the image.")
    else:
        st.write("Upload a floor plan image to begin tracing")


def show_export_tool():
    """Export tool interface"""
    st.header("💾 Export to EMJSON")
    
    if not st.session_state.builder.zones:
        st.warning("No zones to export. Create some geometry first!")
        return
    
    # Validation
    st.subheader("Geometry Validation")
    issues = st.session_state.builder.validate_geometry()
    
    if issues:
        st.warning(f"Found {len(issues)} geometry issues:")
        for issue in issues[:10]:  # Show first 10
            level_icon = "⚠️" if issue['level'] == 'warning' else "❌"
            st.write(f"{level_icon} **{issue['surface_id']}**: {issue['message']}")
        
        if len(issues) > 10:
            st.write(f"... and {len(issues) - 10} more issues")
    else:
        st.success("✅ No geometry issues found!")
    
    # Export
    st.subheader("Export Options")
    
    export_format = st.radio("Format", ["EMJSON", "JSON (Pretty)", "JSON (Compact)"])
    
    if st.button("Generate Export", type="primary", use_container_width=True):
        emjson = st.session_state.builder.to_emjson()
        
        # Format based on selection
        if export_format == "JSON (Compact)":
            output = json.dumps(emjson)
        else:
            output = json.dumps(emjson, indent=2)
        
        # Display summary
        st.subheader("Export Summary")
        col1, col2, col3 = st.columns(3)
        col1.metric("Zones", len(emjson['geometry']['zones']))
        
        total_surfaces = sum(len(v) for v in emjson['geometry']['surfaces'].values())
        col2.metric("Surfaces", total_surfaces)
        
        col3.metric("Format", "EMJSON v6")
        
        # Download button
        st.download_button(
            label="📥 Download EMJSON",
            data=output,
            file_name="geometry_model.emjson",
            mime="application/json",
            use_container_width=True
        )
        
        # Preview
        with st.expander("Preview EMJSON"):
            st.json(emjson)


def show_3d_view():
    """Display 3D visualization of the model"""
    st.header("🔮 3D View")
    
    if not st.session_state.builder.zones:
        st.info("Create some geometry to see the 3D view")
        return
    
    try:
        fig = create_zone_visualization(st.session_state.builder.zones)
        st.plotly_chart(fig, use_container_width=True)
        
        # View controls hint
        st.caption("💡 Click and drag to rotate • Scroll to zoom • Hold shift and drag to pan")
    except Exception as e:
        st.error(f"Error rendering 3D view: {e}")


if __name__ == "__main__":
    main()
