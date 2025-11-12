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
    from eco_tools.simulation.cbecc_results_parser import CBECCResultsParser
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

        # Parse AnalysisResults.xml if available
        if result.get("xml_file") and Path(result["xml_file"]).exists():
            with st.expander("📊 Parsed Results", expanded=True):
                try:
                    parser = CBECCResultsParser(result["xml_file"])
                    parsed = parser.parse()

                    if parsed["status"] == "success":
                        # Project info
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            st.metric("Project", parsed.get("project_name", "N/A"))
                        with col2:
                            st.metric("Climate Zone", parsed.get("climate_zone", "N/A"))
                        with col3:
                            area = parsed.get("building_area")
                            if area:
                                st.metric("Building Area", f"{area:,.0f} ft²")
                            else:
                                st.metric("Building Area", "N/A")

                        st.divider()

                        # Compliance results
                        st.markdown("**Title 24 Compliance**")
                        comp_status = parsed.get("compliance_status", "Unknown")
                        if comp_status == "Pass":
                            st.success(f"✅ Compliance: {comp_status}")
                        elif comp_status == "Fail":
                            st.error(f"❌ Compliance: {comp_status}")
                        else:
                            st.info(f"ℹ️ Compliance: {comp_status}")

                        # Show TDV metrics if available
                        if "proposed_tdv" in parsed or "standard_tdv" in parsed:
                            col1, col2, col3 = st.columns(3)
                            with col1:
                                if "proposed_tdv" in parsed:
                                    st.metric("Proposed TDV", f"{parsed['proposed_tdv']:.1f} kBtu/ft²/yr")
                            with col2:
                                if "standard_tdv" in parsed:
                                    st.metric("Standard TDV", f"{parsed['standard_tdv']:.1f} kBtu/ft²/yr")
                            with col3:
                                if "compliance_margin" in parsed:
                                    margin = parsed["compliance_margin"]
                                    st.metric("Margin", f"{margin:.1f}%",
                                            delta=f"{margin:.1f}%" if margin > 0 else None)

                        # Show end uses if available
                        if parsed.get("end_uses"):
                            st.divider()
                            st.markdown("**Energy End Uses**")
                            for use, value in parsed["end_uses"].items():
                                st.markdown(f"- {use.replace('_', ' ').title()}: {value:.2f} kBtu/ft²/yr")

                        # Show end use categories (even if no values yet)
                        elif parsed.get("end_use_categories"):
                            st.divider()
                            st.markdown("**Available End Use Categories**")
                            st.markdown(f"*({len(parsed['end_use_categories'])} categories found)*")
                            categories_text = ", ".join(parsed['end_use_categories'][:10])
                            if len(parsed['end_use_categories']) > 10:
                                categories_text += f", ... ({len(parsed['end_use_categories']) - 10} more)"
                            st.caption(categories_text)

                        # Store parsed results for comparison
                        st.session_state.cbecc_parsed = parsed

                    else:
                        st.error(f"Parse error: {parsed.get('message', 'Unknown error')}")

                except Exception as e:
                    st.error(f"Error parsing results: {e}")

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

    cbecc_parsed = st.session_state.get("cbecc_parsed")
    energyplus_result = st.session_state.get("energyplus_result")

    if not cbecc_parsed and not energyplus_result:
        st.info("💡 Run simulations in the CBECC-Com and EnergyPlus tabs to see comparison")
        return

    # Show side-by-side comparison
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("🏛️ CBECC-Com (Title 24)")
        if cbecc_parsed:
            st.success(f"Status: {cbecc_parsed.get('status', 'Unknown')}")

            # Show compliance
            comp_status = cbecc_parsed.get("compliance_status", "Unknown")
            if comp_status == "Pass":
                st.success(f"✅ Compliance: {comp_status}")
            elif comp_status == "Fail":
                st.error(f"❌ Compliance: {comp_status}")
            else:
                st.info(f"ℹ️ Compliance: {comp_status}")

            # Show TDV metrics
            if "proposed_tdv" in cbecc_parsed:
                st.metric("Proposed TDV", f"{cbecc_parsed['proposed_tdv']:.1f} kBtu/ft²/yr")
            if "standard_tdv" in cbecc_parsed:
                st.metric("Standard TDV", f"{cbecc_parsed['standard_tdv']:.1f} kBtu/ft²/yr")
            if "compliance_margin" in cbecc_parsed:
                margin = cbecc_parsed["compliance_margin"]
                st.metric("Margin", f"{margin:.1f}%")

            # Show building area
            if "building_area" in cbecc_parsed:
                st.metric("Building Area", f"{cbecc_parsed['building_area']:,.0f} ft²")

        else:
            st.warning("No CBECC results yet")

    with col2:
        st.subheader("⚡ EnergyPlus (Detailed Energy)")
        if energyplus_result:
            st.success(f"Status: {energyplus_result.get('status', 'Unknown')}")

            eui = energyplus_result.get("eui_kbtu_per_sqft_yr")
            if eui:
                st.metric("EUI", f"{eui:.1f} kBtu/ft²/yr")

            energy = energyplus_result.get("total_site_energy_kwh")
            if energy:
                st.metric("Total Energy", f"{energy:,.0f} kWh")

            # Show end uses summary
            if energyplus_result.get("end_uses"):
                end_uses = energyplus_result["end_uses"]
                heating = end_uses.get("heating", 0)
                cooling = end_uses.get("cooling", 0)
                lighting = end_uses.get("lighting", 0)
                st.markdown(f"""
                **Top End Uses:**
                - Heating: {heating:.1f}
                - Cooling: {cooling:.1f}
                - Lighting: {lighting:.1f}
                """)
        else:
            st.warning("No EnergyPlus results yet")

    # Calculate comparison metrics if both available
    if cbecc_parsed and energyplus_result:
        st.divider()
        st.subheader("🔍 Comparison Analysis")

        # Compare building areas if both have them
        cbecc_area = cbecc_parsed.get("building_area")
        ep_eui = energyplus_result.get("eui_kbtu_per_sqft_yr")

        if cbecc_area and ep_eui:
            col1, col2, col3 = st.columns(3)

            with col1:
                st.metric("CBECC Area", f"{cbecc_area:,.0f} ft²")

            with col2:
                st.metric("EnergyPlus EUI", f"{ep_eui:.1f} kBtu/ft²/yr")

            with col3:
                # Calculate total energy from EnergyPlus
                total_ep = energyplus_result.get("total_site_energy_kwh", 0)
                # Convert to kBtu
                total_ep_kbtu = total_ep * 3.412
                # Calculate EUI
                if cbecc_area > 0:
                    ep_eui_calc = total_ep_kbtu / cbecc_area
                    st.metric("Calculated EUI", f"{ep_eui_calc:.1f} kBtu/ft²/yr")

        # Compare end uses if both have them
        cbecc_end_uses = cbecc_parsed.get("end_uses", {})
        ep_end_uses = energyplus_result.get("end_uses", {})

        if cbecc_end_uses and ep_end_uses:
            st.markdown("**End Use Comparison**")

            # Create comparison table
            comparison_data = []
            for use in set(list(cbecc_end_uses.keys()) + list(ep_end_uses.keys())):
                cbecc_val = cbecc_end_uses.get(use, 0)
                ep_val = ep_end_uses.get(use, 0)

                if cbecc_val > 0 or ep_val > 0:
                    delta = ep_val - cbecc_val
                    if cbecc_val > 0:
                        pct_diff = (delta / cbecc_val) * 100
                    else:
                        pct_diff = None

                    comparison_data.append({
                        "End Use": use.replace("_", " ").title(),
                        "CBECC": f"{cbecc_val:.2f}",
                        "EnergyPlus": f"{ep_val:.2f}",
                        "Delta": f"{delta:+.2f}",
                        "% Diff": f"{pct_diff:+.1f}%" if pct_diff is not None else "N/A"
                    })

            if comparison_data:
                st.table(comparison_data)
            else:
                st.info("No comparable end uses found yet")

        elif not cbecc_end_uses:
            st.info("💡 CBECC end use data not available yet (simulation may still be running or results not parsed)")
        elif not ep_end_uses:
            st.info("💡 EnergyPlus end use data not available yet")

    elif cbecc_parsed or energyplus_result:
        st.info("💡 Run both CBECC-Com and EnergyPlus simulations to see detailed comparison")


if __name__ == "__main__":
    handle_simulation()
