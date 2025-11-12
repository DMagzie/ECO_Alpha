"""
Simulation Page
===============

Run and compare energy simulations using CBECC-Com and EnergyPlus.

Features:
- Run CBECC-Com simulations (Title 24 compliance)
- Run EnergyPlus simulations (detailed energy analysis)
- Compare results side-by-side
- View results visualizations
- Export simulation reports

Author: ECO Tools Team
Version: 7.0.0
Date: November 11, 2025
"""

import streamlit as st
import sys
from pathlib import Path
from typing import Dict, Any, Optional
import json

# Add project root to path
ROOT = Path(__file__).resolve().parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Import simulation modules
try:
    from eco_tools.simulation.cbecc_bridge import CBECCBridge
    CBECC_AVAILABLE = True
except ImportError:
    CBECC_AVAILABLE = False

try:
    from eco_tools.simulation.energyplus_runner import EnergyPlusRunner, get_sample_weather_files
    ENERGYPLUS_AVAILABLE = True
except ImportError:
    ENERGYPLUS_AVAILABLE = False

# Import translators
from eco_tools.translators.cibd22x.exporter import CIBD22XExporter
from eco_tools.translators.hbjson.exporter import HBJSONExporter


def handle_simulation():
    """Main simulation page handler."""
    st.title("⚡ Energy Simulation")
    st.caption("Run CBECC-Com and EnergyPlus simulations, compare results")

    # Check if we have an active model
    if "active_model" not in st.session_state or st.session_state.active_model is None:
        st.warning("⚠️ No active model loaded. Please import a model first.")
        st.info("💡 **Tip**: Import a CIBD22X or HBJSON file, or build a model using the wizard.")

        col1, col2 = st.columns(2)
        with col1:
            if st.button("📁 Go to Import Page", use_container_width=True):
                st.session_state.nav_main = "Import"
                st.rerun()
        with col2:
            if st.button("🧙 Go to Wizard", use_container_width=True):
                st.session_state.nav_main = "🧙 Build Model"
                st.rerun()
        return

    model = st.session_state.active_model

    # Show simulation tabs
    tabs = st.tabs(["🏛️ CBECC-Com (Title 24)", "⚡ EnergyPlus", "📊 Compare Results"])

    # ===== TAB 1: CBECC-COM =====
    with tabs[0]:
        show_cbecc_simulation(model)

    # ===== TAB 2: ENERGYPLUS =====
    with tabs[1]:
        show_energyplus_simulation(model)

    # ===== TAB 3: COMPARE =====
    with tabs[2]:
        show_comparison(model)


def show_cbecc_simulation(model: Dict[str, Any]):
    """Show CBECC-Com simulation interface."""
    st.header("🏛️ CBECC-Com Simulation (Title 24 Compliance)")

    if not CBECC_AVAILABLE:
        st.error("❌ CBECC Bridge not available")
        st.info("CBECC simulation requires the CBECC-Com software and Wine (on Mac)")
        return

    # Initialize bridge
    bridge = CBECCBridge()

    # Check installation
    with st.expander("🔍 Check CBECC Installation", expanded=False):
        if st.button("Verify CBECC-Com Installation", use_container_width=True):
            with st.spinner("Checking installation..."):
                if bridge.verify_installation():
                    st.success("✅ CBECC-Com is installed and ready!")
                    version = bridge.get_cbecc_version()
                    if version:
                        st.info(f"Version: {version}")
                else:
                    st.error("❌ CBECC-Com not found")
                    st.markdown("""
                    **Installation Steps**:
                    1. Install Wine: `brew install --cask wine-stable`
                    2. Download CBECC-Com from energy.ca.gov
                    3. Install: `wine ~/Downloads/CBECCcom_2022_Setup.exe`
                    """)

    st.divider()

    # Export to CIBD22X first
    st.subheader("📤 Step 1: Export to CIBD22X")

    output_file = st.text_input(
        "Output file name:",
        value="model_for_cbecc.cibd22x",
        help="File will be saved in test_output/"
    )

    if st.button("Export Model to CIBD22X", type="primary", use_container_width=True):
        with st.spinner("Exporting to CIBD22X..."):
            try:
                exporter = CIBD22XExporter()
                output_path = ROOT / "test_output" / output_file
                output_path.parent.mkdir(parents=True, exist_ok=True)

                exporter.export_to_file(model, str(output_path))
                st.session_state.cbecc_file = str(output_path)
                st.success(f"✅ Exported to: {output_path}")
                st.info("Ready for simulation!")

            except Exception as e:
                st.error(f"❌ Export failed: {e}")
                return

    st.divider()

    # Run simulation
    if "cbecc_file" in st.session_state:
        st.subheader("⚡ Step 2: Run CBECC Simulation")

        st.info(f"📁 File: {st.session_state.cbecc_file}")

        if st.button("🚀 Run CBECC-Com Simulation", type="primary", use_container_width=True):
            with st.spinner("Running CBECC-Com simulation... This may take several minutes."):
                try:
                    result = bridge.run_simulation(st.session_state.cbecc_file)

                    if result["status"] == "success":
                        st.success("✅ Simulation completed successfully!")

                        # Store results
                        st.session_state.cbecc_result = result

                        # Show key results
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            st.metric("Status", "Success")
                        with col2:
                            st.metric("Exit Code", result.get("exit_code", "N/A"))
                        with col3:
                            st.metric("Log File", "Available")

                        # Show output files
                        st.markdown("**Output Files**:")
                        if result.get("log_file"):
                            st.markdown(f"- Log: `{result['log_file']}`")
                        if result.get("xml_file"):
                            st.markdown(f"- Results XML: `{result['xml_file']}`")

                    else:
                        st.error("❌ Simulation failed!")
                        st.error(result.get("message", "Unknown error"))

                        if result.get("stderr"):
                            with st.expander("Show error output"):
                                st.code(result["stderr"])

                except Exception as e:
                    st.error(f"❌ Simulation error: {e}")

    # Show previous results
    if "cbecc_result" in st.session_state:
        st.divider()
        st.subheader("📊 Latest Results")

        result = st.session_state.cbecc_result

        # Show log file
        if result.get("log_file") and Path(result["log_file"]).exists():
            with st.expander("📄 View Log File"):
                try:
                    with open(result["log_file"], 'r') as f:
                        log_content = f.read()
                    st.code(log_content, language="text")
                except Exception as e:
                    st.error(f"Error reading log: {e}")


def show_energyplus_simulation(model: Dict[str, Any]):
    """Show EnergyPlus simulation interface."""
    st.header("⚡ EnergyPlus Simulation (Detailed Energy Analysis)")

    if not ENERGYPLUS_AVAILABLE:
        st.error("❌ EnergyPlus runner not available")
        st.info("""
        **Installation**:
        ```
        pip install honeybee-energy
        ```

        Download EnergyPlus from: https://energyplus.net/downloads
        """)
        return

    # Initialize runner
    runner = EnergyPlusRunner()

    # Check installation
    with st.expander("🔍 Check EnergyPlus Installation", expanded=False):
        if st.button("Verify EnergyPlus Installation", use_container_width=True):
            with st.spinner("Checking installation..."):
                if runner.verify_installation():
                    st.success("✅ EnergyPlus is installed and ready!")
                else:
                    st.error("❌ EnergyPlus not found")

    st.divider()

    # Export to HBJSON first
    st.subheader("📤 Step 1: Export to HBJSON")

    hbjson_file = st.text_input(
        "HBJSON file name:",
        value="model_for_energyplus.hbjson",
        help="File will be saved in test_output/"
    )

    if st.button("Export Model to HBJSON", type="primary", use_container_width=True):
        with st.spinner("Exporting to HBJSON..."):
            try:
                exporter = HBJSONExporter()
                output_path = ROOT / "test_output" / hbjson_file
                output_path.parent.mkdir(parents=True, exist_ok=True)

                exporter.export_to_file(model, str(output_path))
                st.session_state.hbjson_file = str(output_path)
                st.success(f"✅ Exported to: {output_path}")
                st.info("Ready for simulation!")

            except Exception as e:
                st.error(f"❌ Export failed: {e}")
                return

    st.divider()

    # Weather file selection
    st.subheader("🌤️ Step 2: Select Weather File")

    # Get sample weather files
    sample_epw = get_sample_weather_files()

    if sample_epw:
        st.info(f"Found {len(sample_epw)} sample weather files")

        selected_epw = st.selectbox(
            "Select weather file:",
            options=[epw["name"] for epw in sample_epw],
            help="EPW weather file for simulation"
        )

        if selected_epw:
            epw_path = next((epw["path"] for epw in sample_epw if epw["name"] == selected_epw), None)
            if epw_path:
                st.session_state.epw_file = epw_path
                st.success(f"✅ Selected: {selected_epw}")
    else:
        st.warning("⚠️ No sample weather files found")
        custom_epw = st.text_input(
            "Enter path to EPW file:",
            help="Full path to .epw weather file"
        )
        if custom_epw and Path(custom_epw).exists():
            st.session_state.epw_file = custom_epw
            st.success(f"✅ Weather file set")

    st.divider()

    # Run simulation
    if "hbjson_file" in st.session_state and "epw_file" in st.session_state:
        st.subheader("⚡ Step 3: Run EnergyPlus Simulation")

        st.info(f"📁 Model: {st.session_state.hbjson_file}")
        st.info(f"🌤️ Weather: {st.session_state.epw_file}")

        if st.button("🚀 Run EnergyPlus Simulation", type="primary", use_container_width=True):
            with st.spinner("Running EnergyPlus simulation... This may take several minutes."):
                try:
                    result = runner.run_simulation(
                        st.session_state.hbjson_file,
                        st.session_state.epw_file,
                        silent=False
                    )

                    if result["status"] == "success":
                        st.success("✅ Simulation completed successfully!")

                        # Store results
                        st.session_state.energyplus_result = result

                        # Show key results
                        col1, col2 = st.columns(2)
                        with col1:
                            eui = result.get("eui_kbtu_per_sqft_yr", "N/A")
                            st.metric("Energy Use Intensity", f"{eui:.1f}" if isinstance(eui, (int, float)) else eui, "kBtu/ft²/yr")
                        with col2:
                            energy = result.get("total_site_energy_kwh", "N/A")
                            st.metric("Total Site Energy", f"{energy:,.0f}" if isinstance(energy, (int, float)) else energy, "kWh")

                        # Show end uses
                        if result.get("end_uses"):
                            st.markdown("**End Use Breakdown**:")
                            end_uses = result["end_uses"]
                            for use, value in end_uses.items():
                                st.markdown(f"- {use.replace('_', ' ').title()}: {value:.1f} kBtu/ft²/yr")

                    else:
                        st.error("❌ Simulation failed!")
                        st.error(result.get("message", "Unknown error"))

                        if result.get("errors"):
                            with st.expander("Show errors"):
                                for error in result["errors"][:10]:
                                    st.error(error)

                except Exception as e:
                    st.error(f"❌ Simulation error: {e}")

    # Show previous results
    if "energyplus_result" in st.session_state:
        st.divider()
        st.subheader("📊 Latest Results")

        result = st.session_state.energyplus_result

        # Show HTML report
        if result.get("html_file") and Path(result["html_file"]).exists():
            with st.expander("📄 View HTML Report"):
                st.markdown(f"[Open Report]({result['html_file']})")


def show_comparison(model: Dict[str, Any]):
    """Show comparison between CBECC and EnergyPlus results."""
    st.header("📊 Results Comparison")

    cbecc_result = st.session_state.get("cbecc_result")
    energyplus_result = st.session_state.get("energyplus_result")

    if not cbecc_result and not energyplus_result:
        st.info("💡 Run simulations in the CBECC-Com and EnergyPlus tabs to see comparison")
        return

    # Show side-by-side comparison
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("🏛️ CBECC-Com")
        if cbecc_result:
            st.success(f"Status: {cbecc_result.get('status', 'Unknown')}")
            st.info(f"Exit Code: {cbecc_result.get('exit_code', 'N/A')}")
            # TODO: Parse CBECC results for energy metrics
        else:
            st.warning("No CBECC results yet")

    with col2:
        st.subheader("⚡ EnergyPlus")
        if energyplus_result:
            st.success(f"Status: {energyplus_result.get('status', 'Unknown')}")

            eui = energyplus_result.get("eui_kbtu_per_sqft_yr")
            if eui:
                st.metric("EUI", f"{eui:.1f} kBtu/ft²/yr")

            energy = energyplus_result.get("total_site_energy_kwh")
            if energy:
                st.metric("Total Energy", f"{energy:,.0f} kWh")
        else:
            st.warning("No EnergyPlus results yet")

    st.divider()

    # Future: Add charts comparing end uses, monthly energy, etc.
    if cbecc_result and energyplus_result:
        st.info("📊 Detailed comparison charts coming soon!")


if __name__ == "__main__":
    handle_simulation()
