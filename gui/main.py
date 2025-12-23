import streamlit as st
import sys
import os
import shutil
from pathlib import Path

# Clear Python cache before imports to ensure latest code is loaded
def clear_pycache():
    """Clear all __pycache__ directories and .pyc files in eco_tools."""
    ROOT = Path(__file__).resolve().parent.parent
    eco_tools_path = ROOT / "eco_tools"

    if eco_tools_path.exists():
        # Remove all __pycache__ directories
        for pycache_dir in eco_tools_path.rglob("__pycache__"):
            try:
                shutil.rmtree(pycache_dir)
            except Exception:
                pass

        # Remove all .pyc files
        for pyc_file in eco_tools_path.rglob("*.pyc"):
            try:
                pyc_file.unlink()
            except Exception:
                pass

# Clear cache on startup
clear_pycache()

# Add project root to path
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Now use absolute imports (gui instead of explorer_gui in v7)
from gui.pages.import_page import handle_import
from gui.pages.wizard_page import handle_wizard
from gui.pages.template_browser_page import handle_template_browser
from gui.pages.export_page import handle_export
from gui.pages.simulation_page import handle_simulation
from gui.pages.diagnostics_page import show_diagnostics
from gui.pages.round_trip_page import handle_round_trip
from gui.pages.active_model_page import show_active_model
from gui.pages.editing_page import handle_editing
from gui.pages.comparison_page import handle_comparison

# LCCA Dashboard - optional
try:
    from gui.pages.lcca_dashboard_page import handle_lcca_dashboard
    LCCA_AVAILABLE = True
except ImportError:
    LCCA_AVAILABLE = False

# Optional features - imported with error handling
try:
    from gui.config import should_show_in_nav
    from gui.pages.geometry_builder_page import geometry_builder_page
    GEOMETRY_BUILDER_AVAILABLE = True
except ImportError:
    GEOMETRY_BUILDER_AVAILABLE = False
    def should_show_in_nav(name): return False

def main():
    st.set_page_config(page_title="EM Tools Explorer", layout="wide")
    st.title("EM Tools Explorer")

    # Check for wizard completion flag
    if st.session_state.get("wizard_complete", False):
        default_page_index = 4  # "Edit Model"
        st.session_state.wizard_complete = False  # Clear flag
    else:
        default_page_index = 0

    # Build navigation pages list
    pages = [
        "Import",
        "🧙 Build Model",
        "📚 Template Browser",
        "Active Model",
        "Edit Model",
        "🔄 Compare Models",
        "Export",
        "⚡ Simulate",
        "💰 LCCA Dashboard",
        "Diagnostics",
        "Round-Trip Check"
    ]

    # Optionally add Geometry Builder
    if GEOMETRY_BUILDER_AVAILABLE and should_show_in_nav('geometry_builder'):
        # Insert after Template Browser
        pages.insert(3, "🏗️ Geometry Builder")

    # Remove LCCA if not available
    if not LCCA_AVAILABLE:
        pages.remove("💰 LCCA Dashboard")

    # Simple sidebar navigation
    st.sidebar.title("Navigation")
    page = st.sidebar.radio(
        "Pages",
        pages,
        index=default_page_index,
        key="nav_main",
    )

    # Route to pages
    if page == "Import":
        handle_import()
    elif page == "🧙 Build Model":
        handle_wizard()
    elif page == "📚 Template Browser":
        handle_template_browser()
    elif page == "🏗️ Geometry Builder":
        if GEOMETRY_BUILDER_AVAILABLE:
            geometry_builder_page()
        else:
            st.error("Geometry Builder is not available")
    elif page == "Active Model":
        show_active_model()
    elif page == "Edit Model":
        handle_editing()
    elif page == "🔄 Compare Models":
        handle_comparison()
    elif page == "Export":
        handle_export()
    elif page == "⚡ Simulate":
        handle_simulation()
    elif page == "💰 LCCA Dashboard":
        if LCCA_AVAILABLE:
            handle_lcca_dashboard()
        else:
            st.error("LCCA Dashboard is not available")
    elif page == "Diagnostics":
        show_diagnostics()
    elif page == "Round-Trip Check":
        handle_round_trip()

if __name__ == "__main__":
    main()