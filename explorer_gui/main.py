import streamlit as st
import sys
from pathlib import Path

# Add project root to path
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Now use absolute imports
from explorer_gui.pages.import_page import handle_import
from explorer_gui.pages.export_page import handle_export
from explorer_gui.pages.diagnostics_page import show_diagnostics
from explorer_gui.pages.round_trip_page import handle_round_trip
from explorer_gui.pages.active_model_page import show_active_model
from explorer_gui.pages.cibd_mods_page import handle_cibd_mods

def main():
    st.set_page_config(page_title="EM Tools Explorer", layout="wide")
    st.title("EM Tools Explorer")

    page = st.sidebar.radio(
        "Navigate",
        ("Import", "Export", "Active Model", "Diagnostics", "Round-Trip Check", "CIBD Mods", "Developers"),
        index=0,
        key="nav_main",
    )

    if page == "Import":
        handle_import()
    elif page == "Export":
        handle_export()
    elif page == "Active Model":
        show_active_model()
    elif page == "Diagnostics":
        show_diagnostics()
    elif page == "Round-Trip Check":
        handle_round_trip()
    elif page == "CIBD Mods":
        handle_cibd_mods()
    elif page == "Developers":
        st.write("Developer Tools Placeholder")

if __name__ == "__main__":
    main()