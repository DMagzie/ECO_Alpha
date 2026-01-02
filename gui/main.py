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

# Zone Analysis - optional
try:
    from gui.pages.zone_analysis_page import handle_zone_analysis
    ZONE_ANALYSIS_AVAILABLE = True
except ImportError:
    ZONE_ANALYSIS_AVAILABLE = False

# ESG Report - optional
try:
    from gui.pages.esg_report_page import handle_esg_report
    ESG_AVAILABLE = True
except ImportError:
    ESG_AVAILABLE = False

# Site Loads Calculator - optional
try:
    from gui.pages.site_loads_page import handle_site_loads
    SITE_LOADS_AVAILABLE = True
except ImportError:
    SITE_LOADS_AVAILABLE = False

# Building Summary Dashboard - optional
try:
    from gui.pages.building_summary_page import handle_building_summary
    BUILDING_SUMMARY_AVAILABLE = True
except ImportError:
    BUILDING_SUMMARY_AVAILABLE = False

# Optional features - imported with error handling
try:
    from gui.config import should_show_in_nav
    from gui.pages.geometry_builder_page import geometry_builder_page
    GEOMETRY_BUILDER_AVAILABLE = True
except ImportError:
    GEOMETRY_BUILDER_AVAILABLE = False
    def should_show_in_nav(name): return False

def main():
    st.set_page_config(
        page_title="EM Tools Explorer",
        page_icon="🏢",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    st.title("EM Tools Explorer")
    st.caption("Energy Modeling & Life Cycle Cost Analysis Toolkit")

    # Check for wizard completion flag
    if st.session_state.get("wizard_complete", False):
        default_page_index = 4  # "Edit Model"
        st.session_state.wizard_complete = False  # Clear flag
    else:
        default_page_index = 0

    # Build navigation pages list - organized by category
    pages = [
        # --- Model Management ---
        "📁 Import",
        "🧙 Build Model",
        "📚 Template Browser",
        "📄 Active Model",
        "✏️ Edit Model",
        "🔄 Compare Models",
        "📤 Export",
        # --- Simulation ---
        "⚡ Simulate",
        # --- Analysis ---
        "💰 LCCA Dashboard",
        "🏢 Zone Analysis",
        "🌱 ESG Report",
        "🔌 Site Loads",
        "📊 Building Summary",
        # --- Developer Tools ---
        "🔍 Diagnostics",
        "🔁 Round-Trip Check"
    ]

    # Optionally add Geometry Builder
    if GEOMETRY_BUILDER_AVAILABLE and should_show_in_nav('geometry_builder'):
        # Insert after Template Browser
        pages.insert(3, "🏗️ Geometry Builder")

    # Remove pages if modules not available
    if not LCCA_AVAILABLE and "💰 LCCA Dashboard" in pages:
        pages.remove("💰 LCCA Dashboard")

    if not ZONE_ANALYSIS_AVAILABLE and "🏢 Zone Analysis" in pages:
        pages.remove("🏢 Zone Analysis")

    if not ESG_AVAILABLE and "🌱 ESG Report" in pages:
        pages.remove("🌱 ESG Report")

    if not SITE_LOADS_AVAILABLE and "🔌 Site Loads" in pages:
        pages.remove("🔌 Site Loads")

    if not BUILDING_SUMMARY_AVAILABLE and "📊 Building Summary" in pages:
        pages.remove("📊 Building Summary")

    # Sidebar navigation
    st.sidebar.title("Navigation")

    # Show active model status
    if "active_model" in st.session_state and st.session_state.active_model:
        filename = st.session_state.get("active_model_filename", "Model")
        st.sidebar.success(f"📄 {filename[:20]}...")
    else:
        st.sidebar.info("No model loaded")

    # Handle pending navigation from other pages (set via callbacks)
    # Must happen BEFORE the nav widget is created
    nav_target_map = {
        "Import": "📁 Import",
        "Build Model": "🧙 Build Model",
        "Edit Model": "✏️ Edit Model",
        "Simulation": "⚡ Simulate",
        "LCCA": "💰 LCCA Dashboard",
        "ESG Report": "🌱 ESG Report",
        "Site Loads": "🔌 Site Loads",
        "Building Summary": "📊 Building Summary",
    }
    if "_pending_nav" in st.session_state:
        target = st.session_state.pop("_pending_nav")
        mapped_target = nav_target_map.get(target, target)
        if mapped_target in pages:
            # Delete existing nav_main and set to new target
            st.session_state["nav_main"] = mapped_target
            st.rerun()

    page = st.sidebar.radio(
        "Pages",
        pages,
        index=default_page_index,
        key="nav_main",
        label_visibility="collapsed"
    )

    # Module availability status
    with st.sidebar.expander("🔧 Module Status", expanded=False):
        status_items = [
            ("LCCA", LCCA_AVAILABLE),
            ("Zone Analysis", ZONE_ANALYSIS_AVAILABLE),
            ("ESG Report", ESG_AVAILABLE),
            ("Site Loads", SITE_LOADS_AVAILABLE),
            ("Building Summary", BUILDING_SUMMARY_AVAILABLE),
        ]
        for name, available in status_items:
            if available:
                st.markdown(f"✅ {name}")
            else:
                st.markdown(f"❌ {name}")

    # Route to pages
    if page == "📁 Import":
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
    elif page == "📄 Active Model":
        show_active_model()
    elif page == "✏️ Edit Model":
        handle_editing()
    elif page == "🔄 Compare Models":
        handle_comparison()
    elif page == "📤 Export":
        handle_export()
    elif page == "⚡ Simulate":
        handle_simulation()
    elif page == "💰 LCCA Dashboard":
        if LCCA_AVAILABLE:
            handle_lcca_dashboard()
        else:
            st.error("LCCA Dashboard is not available")
    elif page == "🏢 Zone Analysis":
        if ZONE_ANALYSIS_AVAILABLE:
            handle_zone_analysis()
        else:
            st.error("Zone Analysis is not available")
    elif page == "🌱 ESG Report":
        if ESG_AVAILABLE:
            handle_esg_report()
        else:
            st.error("ESG Report is not available")
    elif page == "🔌 Site Loads":
        if SITE_LOADS_AVAILABLE:
            handle_site_loads()
        else:
            st.error("Site Loads Calculator is not available")
    elif page == "📊 Building Summary":
        if BUILDING_SUMMARY_AVAILABLE:
            handle_building_summary()
        else:
            st.error("Building Summary Dashboard is not available")
    elif page == "🔍 Diagnostics":
        show_diagnostics()
    elif page == "🔁 Round-Trip Check":
        handle_round_trip()

if __name__ == "__main__":
    main()