import streamlit as st
import json
import tempfile
import shutil
import os
import sys
from pathlib import Path
from typing import Dict, Any, Optional

# Add project root to path
ROOT = Path(__file__).resolve().parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Add gui to path
EXPLORER_GUI = ROOT / "gui"
if str(EXPLORER_GUI) not in sys.path:
    sys.path.insert(0, str(EXPLORER_GUI))

from import_export import import_file, get_importers
from components.coverage_quickstats import render_quickstats
from components.collapsible_tree import render_collapsible_tree

# Import 3D visualizer
try:
    from utils.geometry_visualizer import GeometryVisualizer
    VISUALIZER_AVAILABLE = True
except ImportError:
    VISUALIZER_AVAILABLE = False


def load_model_section(model_key: str, label: str):
    """Display file uploader and model loading UI for one model."""

    st.subheader(f"{label}")

    # File uploader
    uploaded_file = st.file_uploader(
        f"Choose a file for {label}",
        type=["xml", "cibd22x", "cibd22", "cibd25", "json", "gem"],
        help="Upload CIBD22X XML, CIBD22, CIBD25, EMJSON v6, or GEM file",
        key=f"comparison_uploader_{model_key}"
    )

    if uploaded_file is not None:
        file_extension = uploaded_file.name.split('.')[-1].lower()

        # Determine importer
        if file_extension in ["xml", "cibd22x"]:
            importer_id = "cibd22x"
            file_type_label = "CIBD22X XML"
        elif file_extension == "cibd22":
            importer_id = "cibd22"
            file_type_label = "CIBD22 Text"
        elif file_extension == "cibd25":
            importer_id = "cibd25"
            file_type_label = "CIBD25 Text"
        elif file_extension == "gem":
            importer_id = "gem"
            file_type_label = "IES GEM"
        elif file_extension == "json":
            importer_id = "json"
            file_type_label = "EMJSON"
        else:
            st.error(f"Unsupported file type: {file_extension}")
            return

        st.info(f"File type: {file_type_label}")

        if st.button(f"Load {label}", type="primary", key=f"load_btn_{model_key}"):
            with st.spinner(f"Loading {label}..."):
                _load_model(uploaded_file, importer_id, model_key, uploaded_file.name)

    # Show loaded model info if exists
    if model_key in st.session_state:
        model = st.session_state[model_key]
        filename = st.session_state.get(f"{model_key}_filename", "unknown")

        st.success(f"✅ Loaded: **{filename}**")

        # Quick stats
        if VISUALIZER_AVAILABLE:
            try:
                visualizer = GeometryVisualizer()
                stats = visualizer.get_geometry_stats(model)

                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Zones", stats['zones'])
                with col2:
                    st.metric("Surfaces", stats['surfaces'])
                with col3:
                    st.metric("Floor Area", f"{stats['total_floor_area_m2']:.1f} m²")
            except:
                pass

        # Clear button
        if st.button(f"Clear {label}", key=f"clear_btn_{model_key}"):
            _clear_model(model_key)
            st.rerun()


def _load_model(file_path, importer_id: str, model_key: str, filename: str):
    """Load a model into session state."""
    try:
        if importer_id == "json":
            # Direct JSON load
            em_json = json.loads(file_path.read().decode('utf-8'))
            schema_version = em_json.get("schema_version", "unknown")
            st.success(f"✅ Loaded EMJSON {schema_version}")
        else:
            # Use importer
            result = import_file(importer_id, file_path)

            # Check for errors
            diagnostics = result.get("diagnostics", [])
            errors = [d for d in diagnostics if d.get("level") == "error"]

            if errors:
                st.error(f"❌ Import failed with {len(errors)} error(s)")
                for err in errors[:3]:
                    st.error(f"**{err.get('code', 'ERROR')}**: {err.get('message', 'Unknown error')}")
                return

            em_json = result

        # Store in session state
        st.session_state[model_key] = em_json
        st.session_state[f"{model_key}_filename"] = filename

    except Exception as e:
        st.error(f"❌ Failed to load: {str(e)}")
        import traceback
        with st.expander("Error Details"):
            st.code(traceback.format_exc())


def _clear_model(model_key: str):
    """Clear a model from session state."""
    if model_key in st.session_state:
        del st.session_state[model_key]
    if f"{model_key}_filename" in st.session_state:
        del st.session_state[f"{model_key}_filename"]


def show_side_by_side_comparison(model_a: dict, model_b: dict):
    """Display side-by-side comparison of key metrics."""

    st.subheader("📊 Side-by-Side Comparison")

    if not VISUALIZER_AVAILABLE:
        st.warning("⚠️ Install visualization module for detailed comparison")
        return

    try:
        visualizer = GeometryVisualizer()
        stats_a = visualizer.get_geometry_stats(model_a)
        stats_b = visualizer.get_geometry_stats(model_b)

        # DEBUG: Show what's in each model
        with st.expander("🔍 Debug: Model Structure"):
            col1, col2 = st.columns(2)

            with col1:
                st.markdown("**Model A Structure:**")
                geom_a = model_a.get('geometry', {})
                st.json({
                    'zones_count': len(geom_a.get('zones', [])),
                    'surfaces_type': str(type(geom_a.get('surfaces', {}))),
                    'surfaces_keys': list(geom_a.get('surfaces', {}).keys()) if isinstance(geom_a.get('surfaces', {}), dict) else 'list',
                    'openings_type': str(type(geom_a.get('openings', {}))),
                    'stats': stats_a
                })

            with col2:
                st.markdown("**Model B Structure:**")
                geom_b = model_b.get('geometry', {})
                st.json({
                    'zones_count': len(geom_b.get('zones', [])),
                    'surfaces_type': str(type(geom_b.get('surfaces', {}))),
                    'surfaces_keys': list(geom_b.get('surfaces', {}).keys()) if isinstance(geom_b.get('surfaces', {}), dict) else 'list',
                    'openings_type': str(type(geom_b.get('openings', {}))),
                    'stats': stats_b
                })

        # Create comparison table
        col1, col2, col3 = st.columns([2, 1, 1])

        with col1:
            st.markdown("**Metric**")
        with col2:
            st.markdown(f"**Model A**")
        with col3:
            st.markdown(f"**Model B**")

        st.divider()

        # Compare metrics
        metrics = [
            ("Zones", 'zones', ''),
            ("Surfaces", 'surfaces', ''),
            ("Openings", 'openings', ''),
            ("Floor Area", 'total_floor_area_m2', 'm²'),
            ("Volume", 'total_volume_m3', 'm³'),
        ]

        for label, key, unit in metrics:
            col1, col2, col3 = st.columns([2, 1, 1])

            value_a = stats_a.get(key, 0) or 0
            value_b = stats_b.get(key, 0) or 0

            with col1:
                st.text(label)

            with col2:
                if unit:
                    st.text(f"{value_a:.1f} {unit}")
                else:
                    st.text(f"{value_a}")

            with col3:
                # Show difference indicator
                if value_a != value_b:
                    diff = value_b - value_a
                    pct_diff = ((value_b - value_a) / value_a * 100) if value_a > 0 else 0

                    if unit:
                        diff_str = f"{value_b:.1f} {unit}"
                    else:
                        diff_str = f"{value_b}"

                    if diff > 0:
                        st.text(f"{diff_str} ▲")
                    elif diff < 0:
                        st.text(f"{diff_str} ▼")
                    else:
                        st.text(diff_str)
                else:
                    if unit:
                        st.text(f"{value_b:.1f} {unit}")
                    else:
                        st.text(f"{value_b}")

        # Surface type breakdown comparison
        st.divider()
        st.subheader("🧱 Surface Type Breakdown")

        surface_types_a = stats_a.get('surface_types', {})
        surface_types_b = stats_b.get('surface_types', {})

        # Get all unique surface types
        all_types = set(list(surface_types_a.keys()) + list(surface_types_b.keys()))

        if all_types:
            col1, col2, col3 = st.columns([2, 1, 1])

            with col1:
                st.markdown("**Surface Type**")
            with col2:
                st.markdown("**Model A**")
            with col3:
                st.markdown("**Model B**")

            st.divider()

            for surf_type in sorted(all_types):
                col1, col2, col3 = st.columns([2, 1, 1])

                count_a = surface_types_a.get(surf_type, 0)
                count_b = surface_types_b.get(surf_type, 0)

                with col1:
                    st.text(surf_type.replace('_', ' ').title())
                with col2:
                    st.text(f"{count_a}")
                with col3:
                    if count_a != count_b:
                        diff = count_b - count_a
                        if diff > 0:
                            st.text(f"{count_b} ▲")
                        else:
                            st.text(f"{count_b} ▼")
                    else:
                        st.text(f"{count_b}")

    except Exception as e:
        st.error(f"❌ Comparison error: {str(e)}")
        import traceback
        with st.expander("Error Details"):
            st.code(traceback.format_exc())


def show_project_metadata_comparison(model_a: dict, model_b: dict):
    """Compare project metadata between two models."""

    st.subheader("📋 Project Metadata Comparison")

    project_a = model_a.get('project', {})
    project_b = model_b.get('project', {})

    # Compare key project fields
    fields = [
        ('name', 'Project Name'),
        ('description', 'Description'),
        ('climate_zone', 'Climate Zone'),
        ('building_type', 'Building Type'),
    ]

    col1, col2, col3 = st.columns([2, 1, 1])

    with col1:
        st.markdown("**Field**")
    with col2:
        st.markdown("**Model A**")
    with col3:
        st.markdown("**Model B**")

    st.divider()

    for field_key, field_label in fields:
        col1, col2, col3 = st.columns([2, 1, 1])

        value_a = project_a.get(field_key, 'N/A')
        value_b = project_b.get(field_key, 'N/A')

        with col1:
            st.text(field_label)
        with col2:
            st.text(str(value_a))
        with col3:
            # Highlight if different
            if value_a != value_b:
                st.markdown(f"**{value_b}** ⚠️")
            else:
                st.text(str(value_b))


def show_zone_by_zone_comparison(model_a: dict, model_b: dict):
    """Compare zones between models."""

    st.subheader("🏢 Zone-by-Zone Comparison")

    geometry_a = model_a.get('geometry', {})
    geometry_b = model_b.get('geometry', {})

    zones_a = geometry_a.get('zones', [])
    zones_b = geometry_b.get('zones', [])

    if not zones_a and not zones_b:
        st.info("ℹ️ No zones found in either model")
        return

    # Create zone name mapping
    zone_names_a = {z.get('name', z.get('id', f'Zone_{i}')): z for i, z in enumerate(zones_a)}
    zone_names_b = {z.get('name', z.get('id', f'Zone_{i}')): z for i, z in enumerate(zones_b)}

    all_zone_names = sorted(set(list(zone_names_a.keys()) + list(zone_names_b.keys())))

    # Select zone to compare
    selected_zone = st.selectbox(
        "Select zone to compare:",
        options=all_zone_names,
        key="zone_comparison_select"
    )

    if selected_zone:
        zone_a = zone_names_a.get(selected_zone)
        zone_b = zone_names_b.get(selected_zone)

        col1, col2 = st.columns(2)

        with col1:
            st.markdown("### Model A")
            if zone_a:
                area_a = zone_a.get('floor_area_m2', zone_a.get('area', 0)) or 0
                volume_a = zone_a.get('volume_m3', zone_a.get('volume', 0)) or 0
                surfaces_a = len(zone_a.get('surfaces', []))

                st.metric("Floor Area", f"{area_a:.2f} m²")
                st.metric("Volume", f"{volume_a:.2f} m³")
                st.metric("Surfaces", surfaces_a)
                st.metric("Type", zone_a.get('type', zone_a.get('zone_type', 'N/A')))
            else:
                st.warning("⚠️ Zone not found in Model A")

        with col2:
            st.markdown("### Model B")
            if zone_b:
                area_b = zone_b.get('floor_area_m2', zone_b.get('area', 0)) or 0
                volume_b = zone_b.get('volume_m3', zone_b.get('volume', 0)) or 0
                surfaces_b = len(zone_b.get('surfaces', []))

                # Show with difference indicators
                if zone_a:
                    area_a_val = zone_a.get('floor_area_m2', zone_a.get('area', 0)) or 0
                    volume_a_val = zone_a.get('volume_m3', zone_a.get('volume', 0)) or 0
                    area_diff = area_b - area_a_val
                    volume_diff = volume_b - volume_a_val

                    st.metric("Floor Area", f"{area_b:.2f} m²", delta=f"{area_diff:.2f} m²")
                    st.metric("Volume", f"{volume_b:.2f} m³", delta=f"{volume_diff:.2f} m³")
                    st.metric("Surfaces", surfaces_b, delta=surfaces_b - surfaces_a)
                else:
                    st.metric("Floor Area", f"{area_b:.2f} m²")
                    st.metric("Volume", f"{volume_b:.2f} m³")
                    st.metric("Surfaces", surfaces_b)

                st.metric("Type", zone_b.get('type', zone_b.get('zone_type', 'N/A')))
            else:
                st.warning("⚠️ Zone not found in Model B")


def show_3d_comparison(model_a: dict, model_b: dict):
    """Show 3D visualization comparison."""

    st.subheader("🏗️ 3D Visualization Comparison")

    if not VISUALIZER_AVAILABLE:
        st.warning("⚠️ 3D visualization not available. Install plotly.")
        return

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("### Model A")
        _render_3d_model(model_a, "model_a")

    with col2:
        st.markdown("### Model B")
        _render_3d_model(model_b, "model_b")


def _render_3d_model(model: dict, key: str):
    """Render a single 3D model visualization."""

    geometry = model.get('geometry', {})
    if not geometry:
        st.info("ℹ️ No geometry data available")
        return

    try:
        visualizer = GeometryVisualizer()
        project_name = model.get('project', {}).get('name', 'Model')

        fig = visualizer.visualize_emjson(
            model,
            title=f"{project_name}",
        )

        # Smaller height for side-by-side
        fig.update_layout(height=400)

        st.plotly_chart(fig, use_container_width=True, key=f"3d_viz_{key}")

    except Exception as e:
        st.error(f"❌ Visualization error: {str(e)}")


def handle_comparison():
    """Main comparison page handler."""

    st.title("🔄 Model Comparison")
    st.caption("Load and compare two energy models side-by-side")

    # Show format info
    st.info("ℹ️ **Supported formats**: CIBD22X XML, CIBD25 text, CIBD22 text, EMJSON, and IES GEM files")

    # Model loading section
    st.divider()
    st.header("📁 Load Models")

    col1, col2 = st.columns(2)

    with col1:
        load_model_section("comparison_model_a", "Model A")

    with col2:
        load_model_section("comparison_model_b", "Model B")

    # Check if both models are loaded
    model_a = st.session_state.get('comparison_model_a')
    model_b = st.session_state.get('comparison_model_b')

    if not model_a or not model_b:
        st.divider()
        st.info("ℹ️ Load both models to start comparison")
        return

    # Comparison section
    st.divider()
    st.header("📊 Comparison Results")

    # Create tabs for different comparison views
    tab1, tab2, tab3, tab4 = st.tabs([
        "📊 Side-by-Side Metrics",
        "📋 Project Metadata",
        "🏢 Zone Comparison",
        "🏗️ 3D Comparison"
    ])

    with tab1:
        show_side_by_side_comparison(model_a, model_b)

    with tab2:
        show_project_metadata_comparison(model_a, model_b)

    with tab3:
        show_zone_by_zone_comparison(model_a, model_b)

    with tab4:
        show_3d_comparison(model_a, model_b)

    # Export comparison report
    st.divider()
    st.header("💾 Export Comparison Report")

    if st.button("Generate Comparison Report", type="primary"):
        report = _generate_comparison_report(model_a, model_b)

        st.download_button(
            label="📥 Download Comparison Report (JSON)",
            data=json.dumps(report, indent=2, ensure_ascii=False).encode('utf-8'),
            file_name="model_comparison_report.json",
            mime="application/json"
        )


def _generate_comparison_report(model_a: dict, model_b: dict) -> dict:
    """Generate a structured comparison report."""

    report = {
        "comparison_date": st.session_state.get('import_timestamp', 'unknown'),
        "model_a": {
            "filename": st.session_state.get('comparison_model_a_filename', 'unknown'),
            "project_name": model_a.get('project', {}).get('name', 'N/A'),
        },
        "model_b": {
            "filename": st.session_state.get('comparison_model_b_filename', 'unknown'),
            "project_name": model_b.get('project', {}).get('name', 'N/A'),
        },
        "differences": {}
    }

    if VISUALIZER_AVAILABLE:
        try:
            visualizer = GeometryVisualizer()
            stats_a = visualizer.get_geometry_stats(model_a)
            stats_b = visualizer.get_geometry_stats(model_b)

            report["model_a"]["stats"] = stats_a
            report["model_b"]["stats"] = stats_b

            # Calculate differences
            report["differences"]["zones"] = stats_b['zones'] - stats_a['zones']
            report["differences"]["surfaces"] = stats_b['surfaces'] - stats_a['surfaces']
            report["differences"]["openings"] = stats_b['openings'] - stats_a['openings']
            report["differences"]["floor_area_m2"] = stats_b['total_floor_area_m2'] - stats_a['total_floor_area_m2']
            report["differences"]["volume_m3"] = stats_b['total_volume_m3'] - stats_a['total_volume_m3']
        except:
            pass

    return report
