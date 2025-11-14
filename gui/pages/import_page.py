import streamlit as st
import json
import tempfile
import os
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List

# Add project root to path
ROOT = Path(__file__).resolve().parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Add gui to path
EXPLORER_GUI = ROOT / "gui"
if str(EXPLORER_GUI) not in sys.path:
    sys.path.insert(0, str(EXPLORER_GUI))

# Now import directly
from import_export import import_file, get_importers
from components.diagnostics_panel_v6 import render_diagnostics_panel_v6
from components.collapsible_tree import render_collapsible_tree
from components.coverage_quickstats import render_quickstats


def handle_import():
    st.title("Import Model File")
    st.caption("Import CIBD22X XML or EMJSON v6 files")

    # Get available importers
    importers = get_importers()

    # Create tabs for different import types
    tab1, tab2 = st.tabs(["📁 Upload File", "📋 Paste XML"])

    with tab1:
        st.subheader("Upload Model File")

        # File uploader
        uploaded_file = st.file_uploader(
            "Choose a file",
            type=["xml", "cibd22x", "cibd22", "cibd25", "json", "gem"],
            help="Upload CIBD22X XML (.xml, .cibd22x), CIBD22 text (.cibd22), CIBD25 text (.cibd25), EMJSON v6 JSON, or IES GEM (.gem) file",
            key="model_file_uploader"
        )

        if uploaded_file is not None:
            file_extension = uploaded_file.name.split('.')[-1].lower()

            # Determine importer
            if file_extension in ["xml", "cibd22x"]:
                # CIBD22X XML format - let user choose translator
                st.markdown("### Select Translator")
                
                # Create translator options from available importers
                cibd_importers = [imp for imp in importers if imp["id"].startswith("cibd22x")]
                
                if len(cibd_importers) > 1:
                    # Multiple translators available - show selection
                    translator_labels = {
                        "cibd22x": "em-tools (Modular Parser)",
                        "cibd22x_uni": "Universal Translator (Adapter-based)"
                    }
                    
                    selected_label = st.radio(
                        "Choose translator:",
                        options=[translator_labels.get(imp["id"], imp["label"]) for imp in cibd_importers],
                        help="Select which translator to use for importing CIBD22X XML",
                        horizontal=True
                    )
                    
                    # Find selected importer ID
                    importer_id = next(
                        (imp["id"] for imp in cibd_importers 
                         if translator_labels.get(imp["id"], imp["label"]) == selected_label),
                        "cibd22x"
                    )
                else:
                    # Only one translator available
                    importer_id = cibd_importers[0]["id"] if cibd_importers else "cibd22x"

                # Show importer description
                selected_importer = next((imp for imp in importers if imp["id"] == importer_id), None)
                if selected_importer:
                    st.info(f"ℹ️ {selected_importer['description']}")

                if st.button("Import CIBD22X XML", type="primary"):
                    with st.spinner(f"Importing CIBD22X XML using {importer_id}..."):
                        _process_import(uploaded_file, importer_id)

            elif file_extension == "cibd22":
                # CIBD22 text format
                st.markdown("### CIBD22 Text Format Import")
                st.info("ℹ️ CIBD22 text format will be parsed and converted using the modular CIBD22X parser architecture")

                if st.button("Import CIBD22 Text File", type="primary"):
                    with st.spinner("Importing CIBD22 text file..."):
                        _process_import(uploaded_file, "cibd22")

            elif file_extension == "cibd25":
                # CIBD25 text format
                st.markdown("### CIBD25 Text Format Import")
                st.info("ℹ️ CIBD25 text format (Title 24 2025) will be parsed using the same architecture as CIBD22")

                if st.button("Import CIBD25 Text File", type="primary"):
                    with st.spinner("Importing CIBD25 text file..."):
                        _process_import(uploaded_file, "cibd25")

            elif file_extension == "gem":
                # IES GEM format
                st.markdown("### IES GEM Import")
                st.info("ℹ️ GEM (Geometry Exchange Model) files from IES Virtual Environment contain 3D geometry and will be converted to EMJSON v6")

                if st.button("Import GEM File", type="primary"):
                    with st.spinner("Importing GEM file..."):
                        _process_import(uploaded_file, "gem")

            elif file_extension == "json":
                if st.button("Import JSON", type="primary"):
                    with st.spinner("Loading JSON..."):
                        try:
                            em_json = json.loads(uploaded_file.read().decode('utf-8'))

                            # Validate it's EMJSON v6
                            schema_version = em_json.get("schema_version", "unknown")
                            st.success(f"✅ Loaded EMJSON {schema_version}")

                            # Store in session state
                            st.session_state['active_model'] = em_json
                            st.session_state['active_model_source'] = 'uploaded_json'
                            st.session_state['active_model_filename'] = uploaded_file.name

                            # Show preview
                            _show_import_results(em_json, uploaded_file.name)

                        except json.JSONDecodeError as e:
                            st.error(f"❌ Invalid JSON: {str(e)}")
                        except Exception as e:
                            st.error(f"❌ Failed to load: {str(e)}")

            else:
                st.error(f"❌ Unsupported file type: {file_extension}")

    with tab2:
        st.subheader("Paste Content")

        xml_text = st.text_area(
            "Paste CIBD22X XML content here",
            height=200,
            help="Paste the contents of a CIBD22X XML file",
            key="xml_paste_area"
        )

        if xml_text.strip():
            # Only CIBD22X supported
            importer_id = "cibd22x"
            st.info("ℹ️ Will import as CIBD22X XML format")

            if st.button("Import Pasted XML", type="primary"):
                with st.spinner("Importing..."):
                    # Create temporary file
                    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.xml', encoding='utf-8') as tf:
                        tf.write(xml_text)
                        temp_path = tf.name

                    try:
                        _process_import(temp_path, importer_id, is_temp=True, filename="pasted.xml")
                    finally:
                        try:
                            os.unlink(temp_path)
                        except:
                            pass

    # Show active model if exists
    if 'active_model' in st.session_state:
        st.divider()
        st.subheader("📊 Active Model")
        _show_quick_summary(st.session_state['active_model'])


def _process_import(file_path, importer_id: str, is_temp: bool = False, filename: str = None):
    """Process file import and update session state."""
    try:
        # Import the file
        result = import_file(importer_id, file_path)

        # Extract filename
        if filename is None:
            if hasattr(file_path, 'name'):
                filename = file_path.name
            else:
                filename = os.path.basename(str(file_path))

        # Check for errors
        diagnostics = result.get("diagnostics", [])
        errors = [d for d in diagnostics if d.get("level") == "error"]

        if errors:
            st.error(f"❌ Import failed with {len(errors)} error(s)")
            for err in errors[:5]:  # Show first 5 errors
                st.error(f"**{err.get('code', 'ERROR')}**: {err.get('message', 'Unknown error')}")

            # Show full diagnostics
            with st.expander("📋 Full Diagnostics"):
                render_diagnostics_panel_v6(diagnostics, em_v6=result, title="Import Diagnostics")
        else:
            st.success(f"✅ Successfully imported {filename}")

            # Store in session state
            st.session_state['active_model'] = result
            st.session_state['active_model_source'] = importer_id
            st.session_state['active_model_filename'] = filename
            st.session_state['import_timestamp'] = datetime.now().isoformat()

            # Show results
            _show_import_results(result, filename)

    except Exception as e:
        import traceback
        st.error(f"❌ Unexpected error during import: {str(e)}")
        with st.expander("🔍 Error Details"):
            st.code(traceback.format_exc())


def _show_import_results(em_json: dict, filename: str):
    """Display import results with summary and diagnostics."""

    # Quick metrics
    st.markdown("### 📊 Import Summary")
    render_quickstats(em_json)

    # Diagnostics
    diagnostics = em_json.get("diagnostics", [])
    if diagnostics:
        st.divider()
        render_diagnostics_panel_v6(
            diagnostics,
            em_v6=em_json,
            title="Import Diagnostics",
            default_filename_stem=filename.rsplit('.', 1)[0]
        )

    # Download options
    st.divider()
    st.markdown("### 💾 Download")

    col1, col2 = st.columns(2)

    with col1:
        # Download as EMJSON
        json_str = json.dumps(em_json, indent=2, ensure_ascii=False)
        st.download_button(
            label="📥 Download EMJSON v6",
            data=json_str.encode('utf-8'),
            file_name=f"{filename.rsplit('.', 1)[0]}.emjson.json",
            mime="application/json",
            help="Download the imported model in EMJSON v6 format"
        )

    with col2:
        # View full model
        if st.button("🔍 View Full Model"):
            st.session_state['show_full_model'] = True

    # Show full model if requested
    if st.session_state.get('show_full_model', False):
        st.divider()
        st.markdown("### 🗂️ Full Model Structure")
        render_collapsible_tree(em_json, label="EMJSON v6", level=0)

        if st.button("Hide Full Model"):
            st.session_state['show_full_model'] = False


def _show_quick_summary(em_json: dict):
    """Show quick summary of active model."""

    schema_version = em_json.get("schema_version", "unknown")
    filename = st.session_state.get('active_model_filename', 'unknown')
    source = st.session_state.get('active_model_source', 'unknown')

    st.info(f"📄 **{filename}** (Schema: {schema_version}, Source: {source})")

    # Try to use GeometryVisualizer for consistent stats
    try:
        sys.path.insert(0, str(Path(__file__).parent.parent / "utils"))
        from geometry_visualizer import GeometryVisualizer

        visualizer = GeometryVisualizer()
        stats = visualizer.get_geometry_stats(em_json)

        # Display comprehensive metrics
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

        # Show volume if available
        if stats['total_volume_m3'] > 0:
            st.metric("📦 Total Volume", f"{stats['total_volume_m3']:.1f} m³")

    except ImportError:
        # Fallback to basic stats if visualizer not available
        zones = em_json.get("geometry", {}).get("zones", [])
        surfaces = em_json.get("geometry", {}).get("surfaces", [])
        openings = em_json.get("geometry", {}).get("openings", [])

        # Handle list format (default for GEM imports)
        if isinstance(surfaces, list):
            total_surfaces = len(surfaces)
        elif isinstance(surfaces, dict):
            total_surfaces = sum(len(v) for v in surfaces.values() if isinstance(v, list))
        else:
            total_surfaces = 0

        if isinstance(openings, list):
            total_openings = len(openings)
        elif isinstance(openings, dict):
            total_openings = sum(len(v) for v in openings.values() if isinstance(v, list))
        else:
            total_openings = 0

        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Zones", len(zones))
        with col2:
            st.metric("Surfaces", total_surfaces)
        with col3:
            st.metric("Openings", total_openings)