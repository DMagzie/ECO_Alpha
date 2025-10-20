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

# Add explorer_gui to path
EXPLORER_GUI = ROOT / "explorer_gui"
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
            type=["xml", "cibd22x", "json"],
            help="Upload CIBD22X XML or EMJSON v6 JSON file",
            key="model_file_uploader"
        )

        if uploaded_file is not None:
            file_extension = uploaded_file.name.split('.')[-1].lower()

            # Determine importer
            if file_extension in ["xml", "cibd22x"]:
                importer_id = st.selectbox(
                    "Select Translator",
                    options=[imp["id"] for imp in importers if file_extension in imp.get("extensions", [])],
                    format_func=lambda x: next((imp["label"] for imp in importers if imp["id"] == x), x),
                    key="importer_select"
                )

                # Show importer description
                selected_importer = next((imp for imp in importers if imp["id"] == importer_id), None)
                if selected_importer:
                    st.info(f"ℹ️ {selected_importer['description']}")

                if st.button("Import XML", type="primary"):
                    with st.spinner("Importing..."):
                        _process_import(uploaded_file, importer_id)

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
        st.subheader("Paste XML Content")

        xml_text = st.text_area(
            "Paste CIBD22X XML here",
            height=200,
            help="Paste the contents of a CIBD22X XML file",
            key="xml_paste_area"
        )

        if xml_text.strip():
            importer_id = st.selectbox(
                "Select Translator",
                options=[imp["id"] for imp in importers],
                format_func=lambda x: next((imp["label"] for imp in importers if imp["id"] == x), x),
                key="importer_select_paste"
            )

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

    # Quick stats
    zones = em_json.get("geometry", {}).get("zones", [])
    surfaces = em_json.get("geometry", {}).get("surfaces", {})
    openings = em_json.get("geometry", {}).get("openings", {})

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Zones", len(zones))
    with col2:
        total_surfaces = sum(len(v) for v in surfaces.values() if isinstance(v, list))
        st.metric("Surfaces", total_surfaces)
    with col3:
        total_openings = sum(len(v) for v in openings.values() if isinstance(v, list))
        st.metric("Openings", total_openings)
    with col4:
        hvac_count = len(em_json.get("systems", {}).get("hvac", []))
        st.metric("HVAC Systems", hvac_count)