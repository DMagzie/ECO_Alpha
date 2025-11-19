import streamlit as st
import json
import sys
from pathlib import Path

# Add project root to path
ROOT = Path(__file__).resolve().parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Add gui to path
EXPLORER_GUI = ROOT / "gui"
if str(EXPLORER_GUI) not in sys.path:
    sys.path.insert(0, str(EXPLORER_GUI))

from gui.translators import emjson6_to_cibd22x, emjson6_to_cibd25


def handle_export():
    st.subheader("Export Active Model (EMJSON v6 or CIBD22x XML)")

    # Check if there's an active model
    if 'active_model' in st.session_state:
        active_model = st.session_state['active_model']
        filename = st.session_state.get('active_model_filename', 'model')
    else:
        # Simulated active model data (fallback)
        st.warning("⚠️ No active model loaded. Using sample data.")
        active_model = {
            "schema_version": "6.0",
            "location": {"latitude": 34.0522, "longitude": -118.2437},
            "geometry": {
                "zones": [{"name": "Zone 1", "area": 200}, {"name": "Zone 2", "area": 150}],
                "surfaces": {
                    "walls": [{"type": "wall", "area": 100}],
                    "roofs": [{"type": "roof", "area": 200}],
                    "floors": []
                },
                "openings": {
                    "windows": [{"type": "window", "area": 10}],
                    "doors": [{"type": "door", "area": 5}],
                    "skylights": []
                }
            },
            "catalogs": {
                "window_types": ["Type A", "Type B"],
                "construction_types": ["Concrete", "Wood"],
                "du_types": []
            },
            "systems": {
                "hvac": [{"name": "System A"}, {"name": "System B"}],
                "dhw": [],
                "pv": []
            }
        }
        filename = "sample_model"

    # Provide export options for the active model
    st.subheader("Download Active Model")

    # EMJSON v6 export (left column)
    col1, col2 = st.columns(2)

    with col1:
        # Export the model as EMJSON v6
        emjson_data = json.dumps(active_model, indent=2, ensure_ascii=False)
        st.download_button(
            label="📥 Download as EMJSON v6",
            data=emjson_data.encode("utf-8"),
            file_name=f"{filename.rsplit('.', 1)[0]}_export.emjson.json",
            mime="application/json",
            help="Download as EMJSON v6 JSON format"
        )

    with col2:
        st.write("")  # Spacing

    # CIBD22x XML export
    st.markdown("---")
    st.subheader("Export to CIBD22x XML (v7 Modular)")
    st.info("💡 Uses v7 modular exporters with 99.8% roundtrip accuracy")

    # Export button
    try:
        xml_data = emjson6_to_cibd22x(active_model)

        st.download_button(
            label="📥 Download as CIBD22x XML",
            data=xml_data.encode("utf-8") if isinstance(xml_data, str) else xml_data,
            file_name=f"{filename.rsplit('.', 1)[0]}_export.cibd22x",
            mime="application/xml",
            help="Download as CIBD22x XML format using v7 modular exporter"
        )
    except Exception as e:
        st.error(f"❌ Export to XML failed: {str(e)}")
        with st.expander("Error Details"):
            import traceback
            st.code(traceback.format_exc())

    # CIBD25 export (Title 24 2025)
    st.markdown("---")
    st.subheader("Export to CIBD25 (Title 24 2025)")
    st.info("💡 CIBD25 text format with T24_2025.bin ruleset for CBECC 2025 simulation")

    try:
        # Get source file path for roundtrip (if available)
        source_file = st.session_state.get('source_file_path')

        # DEBUG: Show what we're passing
        st.info(f"🔍 DEBUG: source_file_path from session = {source_file}")
        if source_file:
            import os
            st.info(f"🔍 DEBUG: File exists = {os.path.exists(source_file)}")

        # Export with roundtrip if source is CIBD22X
        xml_data = emjson6_to_cibd25(active_model, source_cibd22x_file=source_file)

        st.download_button(
            label="📥 Download as CIBD25 Text Format",
            data=xml_data.encode("utf-8") if isinstance(xml_data, str) else xml_data,
            file_name=f"{filename.rsplit('.', 1)[0]}_export.cibd25",
            mime="text/plain",
            help="Download as CIBD25 text format for Title 24 2025 compliance simulation in CBECC 2025"
        )
    except Exception as e:
        st.error(f"❌ Export to CIBD25 failed: {str(e)}")
        with st.expander("Error Details"):
            import traceback
            st.code(traceback.format_exc())