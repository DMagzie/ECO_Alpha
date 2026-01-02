"""
Whole Building Summary Dashboard
================================

Unified view of all building analysis results including:
- Building geometry and envelope
- Energy simulation results (CBECC, EnergyPlus, CSE)
- LCCA financial metrics
- ESG/Carbon footprint
- Compliance status

This page provides an executive summary of all analyses.

Author: ECO Tools Team
Version: 7.0.0
Date: December 2024
"""

import streamlit as st
import sys
from pathlib import Path
from typing import Dict, Any, Optional, List
import json
from datetime import datetime

# Add project root to path
ROOT = Path(__file__).resolve().parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Import utilities
try:
    from gui.utils.geometry_visualizer import GeometryVisualizer
    GEOMETRY_VIZ_AVAILABLE = True
except ImportError:
    GEOMETRY_VIZ_AVAILABLE = False

# Carbon emission factors (lbs CO2/kWh by region)
CARBON_FACTORS = {
    "CAMX (California)": 0.531,
    "NWPP (Northwest)": 0.679,
    "RMPA (Rockies)": 1.329,
    "AZNM (Southwest)": 0.913,
    "National Average": 0.855,
}


def _set_nav_and_rerun(target: str):
    """Callback to set navigation target. Must be called before widget instantiation."""
    st.session_state["_pending_nav"] = target


def handle_building_summary():
    """Main building summary dashboard handler."""
    st.title("Building Summary Dashboard")
    st.caption("Unified view of building analysis results")

    # Check for active model
    has_model = "active_model" in st.session_state and st.session_state.active_model is not None

    if not has_model:
        st.warning("No active model loaded. Import a model to see building summary.")

        col1, col2 = st.columns(2)
        with col1:
            st.button(
                "Go to Import Page",
                key="nav_import",
                use_container_width=True,
                on_click=_set_nav_and_rerun,
                args=("Import",)
            )
        with col2:
            st.button(
                "Go to Build Wizard",
                key="nav_build",
                use_container_width=True,
                on_click=_set_nav_and_rerun,
                args=("Build Model",)
            )
        return

    model = st.session_state.active_model

    # Main tabs for different summary sections
    tabs = st.tabs([
        "Overview",
        "Energy",
        "Financial",
        "Carbon",
        "Compliance"
    ])

    # ===== TAB 1: OVERVIEW =====
    with tabs[0]:
        render_overview_tab(model)

    # ===== TAB 2: ENERGY =====
    with tabs[1]:
        render_energy_tab(model)

    # ===== TAB 3: FINANCIAL =====
    with tabs[2]:
        render_financial_tab(model)

    # ===== TAB 4: CARBON =====
    with tabs[3]:
        render_carbon_tab(model)

    # ===== TAB 5: COMPLIANCE =====
    with tabs[4]:
        render_compliance_tab(model)

    # Export section
    st.divider()
    render_export_section(model)


def render_overview_tab(model: Dict[str, Any]):
    """Render building overview tab."""
    st.header("Building Overview")

    # Project info
    filename = st.session_state.get("active_model_filename", "Unknown")
    source = st.session_state.get("active_model_source", "Unknown")
    schema = model.get("schema_version", "Unknown")
    import_time = st.session_state.get("import_timestamp", "N/A")

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("### Project Information")
        st.markdown(f"**File:** {filename}")
        st.markdown(f"**Source:** {source}")
        st.markdown(f"**Schema:** {schema}")
        st.markdown(f"**Imported:** {import_time}")

    with col2:
        st.markdown("### Building Metadata")
        metadata = model.get("metadata", {})
        project = metadata.get("project", {})

        name = project.get("name", metadata.get("name", "N/A"))
        location = project.get("location", metadata.get("location", "N/A"))
        climate_zone = project.get("climate_zone", metadata.get("climate_zone", "N/A"))

        st.markdown(f"**Project Name:** {name}")
        st.markdown(f"**Location:** {location}")
        st.markdown(f"**Climate Zone:** {climate_zone}")

    st.divider()

    # Geometry stats
    st.markdown("### Geometry Summary")

    if GEOMETRY_VIZ_AVAILABLE:
        try:
            visualizer = GeometryVisualizer()
            stats = visualizer.get_geometry_stats(model)

            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Zones", stats["zones"])
            with col2:
                st.metric("Surfaces", stats["surfaces"])
            with col3:
                st.metric("Openings", stats["openings"])
            with col4:
                floor_area = stats["total_floor_area_m2"]
                floor_area_sf = floor_area * 10.764  # Convert to sq ft
                st.metric("Floor Area", f"{floor_area_sf:,.0f} ft²")

            # Additional geometry details
            col1, col2 = st.columns(2)
            with col1:
                if stats["total_volume_m3"] > 0:
                    vol_cf = stats["total_volume_m3"] * 35.315  # Convert to cubic ft
                    st.metric("Building Volume", f"{vol_cf:,.0f} ft³")
            with col2:
                if stats["zones"] > 0 and floor_area > 0:
                    avg_zone = floor_area_sf / stats["zones"]
                    st.metric("Avg Zone Size", f"{avg_zone:,.0f} ft²")

        except Exception as e:
            st.warning(f"Could not calculate geometry stats: {e}")
            _fallback_geometry_stats(model)
    else:
        _fallback_geometry_stats(model)

    # Zone breakdown
    st.divider()
    st.markdown("### Zone Breakdown")

    zones = model.get("geometry", {}).get("zones", [])
    if zones:
        # Group zones by type
        zone_types = {}
        for zone in zones:
            ztype = zone.get("zone_type", zone.get("type", "Unknown"))
            if ztype not in zone_types:
                zone_types[ztype] = []
            zone_types[ztype].append(zone)

        # Display as columns
        cols = st.columns(min(len(zone_types), 4))
        for i, (ztype, zone_list) in enumerate(zone_types.items()):
            with cols[i % 4]:
                st.markdown(f"**{ztype}**")
                st.metric("Count", len(zone_list))
    else:
        st.info("No zones found in model")


def _fallback_geometry_stats(model: Dict[str, Any]):
    """Fallback geometry stats when visualizer not available."""
    zones = model.get("geometry", {}).get("zones", [])
    surfaces = model.get("geometry", {}).get("surfaces", [])
    openings = model.get("geometry", {}).get("openings", [])

    # Handle different formats
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


def render_energy_tab(model: Dict[str, Any]):
    """Render energy analysis summary tab."""
    st.header("Energy Analysis Summary")

    # Collect all available energy results
    cbecc_result = st.session_state.get("cbecc_parsed")
    ep_result = st.session_state.get("energyplus_result")
    cse_result = st.session_state.get("cse_result")
    cuac_result = st.session_state.get("cuac_results")

    has_any = cbecc_result or ep_result or cse_result or cuac_result

    if not has_any:
        st.info("No energy simulation results available. Run simulations in the Simulation page.")
        st.button(
            "Go to Simulation Page",
            key="nav_sim_energy",
            on_click=_set_nav_and_rerun,
            args=("Simulation",)
        )
        return

    # Summary metrics row
    st.markdown("### Key Metrics")
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        if cbecc_result and "proposed_tdv" in cbecc_result:
            st.metric("CBECC TDV", f"{cbecc_result['proposed_tdv']:.1f}", "kBtu/ft²/yr")
        else:
            st.metric("CBECC TDV", "N/A")

    with col2:
        if ep_result and "eui_kbtu_per_sqft_yr" in ep_result:
            st.metric("EnergyPlus EUI", f"{ep_result['eui_kbtu_per_sqft_yr']:.1f}", "kBtu/ft²/yr")
        else:
            st.metric("EnergyPlus EUI", "N/A")

    with col3:
        if cse_result and cse_result.success:
            st.metric("CSE Status", "Completed")
        else:
            st.metric("CSE Status", "N/A")

    with col4:
        if cuac_result:
            st.metric("CUAC kWh", f"{cuac_result.building_total_kwh:,.0f}")
        else:
            st.metric("CUAC kWh", "N/A")

    st.divider()

    # Detailed results by simulation type
    if cbecc_result:
        with st.expander("CBECC-Com Results", expanded=True):
            col1, col2, col3 = st.columns(3)
            with col1:
                st.markdown("**Compliance Status**")
                status = cbecc_result.get("compliance_status", "Unknown")
                if status == "Pass":
                    st.success(f"PASS")
                elif status == "Fail":
                    st.error(f"FAIL")
                else:
                    st.info(status)

            with col2:
                if "compliance_margin" in cbecc_result:
                    margin = cbecc_result["compliance_margin"]
                    st.metric("Compliance Margin", f"{margin:.1f}%")

            with col3:
                if "building_area" in cbecc_result:
                    st.metric("Building Area", f"{cbecc_result['building_area']:,.0f} ft²")

            # End uses
            if cbecc_result.get("end_uses"):
                st.markdown("**End Use Breakdown (kBtu/ft²/yr)**")
                for use, val in cbecc_result["end_uses"].items():
                    st.markdown(f"- {use.replace('_', ' ').title()}: {val:.2f}")

    if ep_result:
        with st.expander("EnergyPlus Results", expanded=False):
            col1, col2 = st.columns(2)
            with col1:
                if "total_site_energy_kwh" in ep_result:
                    st.metric("Total Site Energy", f"{ep_result['total_site_energy_kwh']:,.0f} kWh")
            with col2:
                if "eui_kbtu_per_sqft_yr" in ep_result:
                    st.metric("EUI", f"{ep_result['eui_kbtu_per_sqft_yr']:.1f} kBtu/ft²/yr")

            if ep_result.get("end_uses"):
                st.markdown("**End Use Breakdown**")
                for use, val in ep_result["end_uses"].items():
                    st.markdown(f"- {use.replace('_', ' ').title()}: {val:.2f}")

    if cuac_result:
        with st.expander("CUAC Results", expanded=False):
            st.markdown(f"**Project:** {cuac_result.project_name}")
            st.metric("Total Building kWh", f"{cuac_result.building_total_kwh:,.0f}")

            if cuac_result.consumption_by_unit_type:
                st.markdown("**By Unit Type:**")
                for ut, data in cuac_result.consumption_by_unit_type.items():
                    st.markdown(f"- {ut}: {data.total_kwh:,.0f} kWh/yr")


def render_financial_tab(model: Dict[str, Any]):
    """Render financial/LCCA summary tab."""
    st.header("Financial Summary")

    # Check for LCCA results
    lcca_result = st.session_state.get("lcca_result")
    scenarios = st.session_state.get("lcca_scenarios", {})

    if not lcca_result and not scenarios:
        st.info("No LCCA results available. Run analysis in the LCCA Dashboard page.")
        st.button(
            "Go to LCCA Dashboard",
            key="nav_lcca",
            on_click=_set_nav_and_rerun,
            args=("LCCA",)
        )
        return

    # Current analysis summary
    if lcca_result:
        st.markdown("### Current Analysis")

        col1, col2, col3, col4 = st.columns(4)
        with col1:
            npv = lcca_result.get("npv", 0)
            st.metric("NPV", f"${npv:,.0f}")
        with col2:
            irr = lcca_result.get("irr", 0)
            st.metric("IRR", f"{irr:.1%}" if irr else "N/A")
        with col3:
            payback = lcca_result.get("simple_payback", 0)
            st.metric("Simple Payback", f"{payback:.1f} yrs" if payback else "N/A")
        with col4:
            first_cost = lcca_result.get("first_cost", 0)
            st.metric("First Cost", f"${first_cost:,.0f}")

        # Annual costs
        st.divider()
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("**Annual Energy Cost**")
            annual_energy = lcca_result.get("annual_energy_cost", 0)
            st.metric("Year 1", f"${annual_energy:,.0f}")

        with col2:
            st.markdown("**Annual O&M Cost**")
            annual_om = lcca_result.get("annual_om_cost", 0)
            st.metric("Year 1", f"${annual_om:,.0f}")

    # Scenario comparison
    if scenarios:
        st.divider()
        st.markdown("### Scenario Comparison")

        scenario_data = []
        for name, data in scenarios.items():
            scenario_data.append({
                "Scenario": name,
                "NPV": f"${data.get('npv', 0):,.0f}",
                "IRR": f"{data.get('irr', 0):.1%}" if data.get('irr') else "N/A",
                "First Cost": f"${data.get('first_cost', 0):,.0f}",
            })

        if scenario_data:
            st.table(scenario_data)


def render_carbon_tab(model: Dict[str, Any]):
    """Render carbon/ESG summary tab."""
    st.header("Carbon & Sustainability")

    # Check for ESG results
    esg_result = st.session_state.get("esg_result")

    # Get energy data
    ep_result = st.session_state.get("energyplus_result")
    cuac_result = st.session_state.get("cuac_results")

    # Calculate carbon if we have energy data
    annual_kwh = 0
    if cuac_result:
        annual_kwh = cuac_result.building_total_kwh
    elif ep_result and "total_site_energy_kwh" in ep_result:
        annual_kwh = ep_result["total_site_energy_kwh"]

    if annual_kwh > 0 or esg_result:
        st.markdown("### Carbon Footprint")

        # If no ESG result, calculate basic carbon
        if not esg_result and annual_kwh > 0:
            # Use California factor by default
            carbon_factor = CARBON_FACTORS["CAMX (California)"]
            scope2_lbs = annual_kwh * carbon_factor
            scope2_tons = scope2_lbs / 2000

            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Annual Energy", f"{annual_kwh:,.0f} kWh")
            with col2:
                st.metric("Scope 2 Emissions", f"{scope2_tons:,.1f} tons CO2/yr")
            with col3:
                st.metric("Carbon Factor", f"{carbon_factor:.3f} lbs/kWh")

            st.caption("Based on CAMX (California) emission factor")

        elif esg_result:
            col1, col2, col3 = st.columns(3)
            with col1:
                scope1 = esg_result.get("scope1_tons", 0)
                st.metric("Scope 1", f"{scope1:,.1f} tons CO2/yr")
            with col2:
                scope2 = esg_result.get("scope2_tons", 0)
                st.metric("Scope 2", f"{scope2:,.1f} tons CO2/yr")
            with col3:
                total = esg_result.get("total_tons", scope1 + scope2)
                st.metric("Total", f"{total:,.1f} tons CO2/yr")

            # Intensity metrics
            st.divider()
            st.markdown("### Carbon Intensity")

            col1, col2 = st.columns(2)
            with col1:
                if "carbon_per_sqft" in esg_result:
                    st.metric("Per Square Foot", f"{esg_result['carbon_per_sqft']:.2f} kg CO2/ft²")
            with col2:
                if "carbon_per_occupant" in esg_result:
                    st.metric("Per Occupant", f"{esg_result['carbon_per_occupant']:.1f} kg CO2/person")

    else:
        st.info("No energy data available for carbon calculation. Run simulations first.")

    # Sustainability score (if calculated)
    st.divider()
    st.markdown("### Sustainability Score")

    if esg_result and "sustainability_score" in esg_result:
        score = esg_result["sustainability_score"]

        # Color-coded score
        if score >= 80:
            st.success(f"Excellent: {score}/100")
        elif score >= 60:
            st.info(f"Good: {score}/100")
        elif score >= 40:
            st.warning(f"Fair: {score}/100")
        else:
            st.error(f"Needs Improvement: {score}/100")
    else:
        st.info("Run ESG analysis to calculate sustainability score")
        st.button(
            "Go to ESG Report",
            key="nav_esg",
            on_click=_set_nav_and_rerun,
            args=("ESG Report",)
        )


def render_compliance_tab(model: Dict[str, Any]):
    """Render compliance summary tab."""
    st.header("Compliance Summary")

    cbecc_result = st.session_state.get("cbecc_parsed")

    if cbecc_result:
        st.markdown("### Title 24 Compliance")

        # Main compliance status
        status = cbecc_result.get("compliance_status", "Unknown")

        col1, col2 = st.columns([1, 2])
        with col1:
            if status == "Pass":
                st.success("COMPLIANT")
            elif status == "Fail":
                st.error("NON-COMPLIANT")
            else:
                st.info(f"Status: {status}")

        with col2:
            if "compliance_margin" in cbecc_result:
                margin = cbecc_result["compliance_margin"]
                if margin > 0:
                    st.success(f"Margin: +{margin:.1f}% better than standard")
                else:
                    st.error(f"Margin: {margin:.1f}% worse than standard")

        st.divider()

        # TDV comparison
        st.markdown("### TDV Energy Budget")

        col1, col2, col3 = st.columns(3)
        with col1:
            if "proposed_tdv" in cbecc_result:
                st.metric("Proposed TDV", f"{cbecc_result['proposed_tdv']:.1f} kBtu/ft²/yr")
        with col2:
            if "standard_tdv" in cbecc_result:
                st.metric("Standard TDV", f"{cbecc_result['standard_tdv']:.1f} kBtu/ft²/yr")
        with col3:
            if "proposed_tdv" in cbecc_result and "standard_tdv" in cbecc_result:
                savings = cbecc_result["standard_tdv"] - cbecc_result["proposed_tdv"]
                savings_pct = (savings / cbecc_result["standard_tdv"]) * 100 if cbecc_result["standard_tdv"] > 0 else 0
                st.metric("TDV Savings", f"{savings:.1f}", delta=f"{savings_pct:.1f}%")

        # Climate zone info
        st.divider()
        st.markdown("### Building Details")

        col1, col2, col3 = st.columns(3)
        with col1:
            cz = cbecc_result.get("climate_zone", "N/A")
            st.metric("Climate Zone", cz)
        with col2:
            area = cbecc_result.get("building_area")
            if area:
                st.metric("Conditioned Area", f"{area:,.0f} ft²")
        with col3:
            project = cbecc_result.get("project_name", "N/A")
            st.metric("Project", project)

    else:
        st.info("No CBECC compliance results available. Run CBECC simulation first.")

        # Check CBECC availability
        try:
            from eco_tools.simulation.cbecc_bridge import CBECCBridge
            bridge = CBECCBridge()
            if bridge.verify_installation():
                st.success("CBECC-Com is available on this system")
            else:
                st.warning("CBECC-Com not detected")
        except ImportError:
            st.warning("CBECC bridge module not available")

        st.button(
            "Go to Simulation Page",
            key="nav_sim_compliance",
            on_click=_set_nav_and_rerun,
            args=("Simulation",)
        )


def render_export_section(model: Dict[str, Any]):
    """Render export options for summary report."""
    st.markdown("### Export Summary Report")

    col1, col2, col3 = st.columns(3)

    with col1:
        if st.button("Export as JSON", use_container_width=True):
            # Compile summary data
            summary = compile_summary_data(model)

            json_str = json.dumps(summary, indent=2, default=str)
            st.download_button(
                label="Download JSON",
                data=json_str,
                file_name=f"building_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                mime="application/json"
            )

    with col2:
        if st.button("Export as CSV", use_container_width=True):
            # Create flat CSV format
            summary = compile_summary_data(model)

            lines = ["Category,Metric,Value"]
            for category, metrics in summary.items():
                if isinstance(metrics, dict):
                    for key, val in metrics.items():
                        lines.append(f"{category},{key},{val}")
                else:
                    lines.append(f"{category},value,{metrics}")

            csv_str = "\n".join(lines)
            st.download_button(
                label="Download CSV",
                data=csv_str,
                file_name=f"building_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv"
            )

    with col3:
        if st.button("Print Summary", use_container_width=True):
            st.info("Use your browser's Print function (Ctrl+P / Cmd+P) to print this page")


def compile_summary_data(model: Dict[str, Any]) -> Dict[str, Any]:
    """Compile all summary data into a single dictionary."""
    summary = {
        "generated": datetime.now().isoformat(),
        "project": {
            "filename": st.session_state.get("active_model_filename", "Unknown"),
            "source": st.session_state.get("active_model_source", "Unknown"),
            "schema": model.get("schema_version", "Unknown"),
        },
    }

    # Geometry
    zones = model.get("geometry", {}).get("zones", [])
    summary["geometry"] = {
        "zones": len(zones),
    }

    # CBECC results
    cbecc = st.session_state.get("cbecc_parsed")
    if cbecc:
        summary["cbecc"] = {
            "compliance_status": cbecc.get("compliance_status"),
            "proposed_tdv": cbecc.get("proposed_tdv"),
            "standard_tdv": cbecc.get("standard_tdv"),
            "compliance_margin": cbecc.get("compliance_margin"),
            "building_area": cbecc.get("building_area"),
        }

    # EnergyPlus results
    ep = st.session_state.get("energyplus_result")
    if ep:
        summary["energyplus"] = {
            "eui": ep.get("eui_kbtu_per_sqft_yr"),
            "total_energy_kwh": ep.get("total_site_energy_kwh"),
        }

    # LCCA results
    lcca = st.session_state.get("lcca_result")
    if lcca:
        summary["lcca"] = {
            "npv": lcca.get("npv"),
            "irr": lcca.get("irr"),
            "simple_payback": lcca.get("simple_payback"),
            "first_cost": lcca.get("first_cost"),
        }

    # ESG results
    esg = st.session_state.get("esg_result")
    if esg:
        summary["esg"] = {
            "scope1_tons": esg.get("scope1_tons"),
            "scope2_tons": esg.get("scope2_tons"),
            "sustainability_score": esg.get("sustainability_score"),
        }

    return summary


if __name__ == "__main__":
    handle_building_summary()
