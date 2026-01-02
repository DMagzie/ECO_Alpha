"""
ESG/Carbon Reporting Page
=========================

Environmental, Social, and Governance (ESG) reporting for buildings.

Features:
- Carbon footprint calculation (Scope 1 & 2)
- Energy Use Intensity (EUI) metrics
- Renewable energy percentage
- Baseline vs Proposed comparison
- LEED/sustainability documentation support
- Export to CSV/PDF

Author: ECO Tools Team
Version: 7.0.0
Date: December 2024
"""

import streamlit as st
import sys
from pathlib import Path
from typing import Dict, Any, Optional, List

# Add project root to path
ROOT = Path(__file__).resolve().parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Import ESG modules with error handling
try:
    from eco_tools.lcca import (
        discover_simulation_outputs,
        DiscoveredOutputs,
    )
    from eco_tools.lcca.esg_report import (
        EmissionsSource,
        EmissionFactors,
        CarbonFootprint,
        EsgMetrics,
        EsgReport,
        CA_EMISSION_FACTORS,
        US_AVERAGE_FACTORS,
        calculate_carbon_footprint,
        calculate_eui,
        calculate_renewable_pct,
        generate_esg_metrics,
        generate_esg_report,
        format_esg_report,
        export_esg_csv,
        get_emission_factors,
    )
    from eco_tools.lcca.model import AnnualEnergySummary, SimulationOutput
    ESG_AVAILABLE = True
except ImportError as e:
    ESG_AVAILABLE = False
    ESG_IMPORT_ERROR = str(e)

# Optional: Plotting
try:
    import plotly.graph_objects as go
    import plotly.express as px
    PLOTLY_AVAILABLE = True
except ImportError:
    PLOTLY_AVAILABLE = False


# Regional emission factors
EMISSION_FACTOR_OPTIONS = {
    "California (CAMX)": EmissionFactors(
        elec_kg_per_kwh=0.225,
        gas_kg_per_therm=5.3,
        source="EPA eGRID CAMX 2024",
        region="California"
    ),
    "US Average": EmissionFactors(
        elec_kg_per_kwh=0.386,
        gas_kg_per_therm=5.3,
        source="EPA eGRID 2024",
        region="US Average"
    ),
    "Hawaii": EmissionFactors(
        elec_kg_per_kwh=0.614,
        gas_kg_per_therm=5.3,
        source="EPA eGRID HICC 2024",
        region="Hawaii"
    ),
    "Pacific Northwest": EmissionFactors(
        elec_kg_per_kwh=0.135,
        gas_kg_per_therm=5.3,
        source="EPA eGRID NWPP 2024",
        region="Pacific NW"
    ),
    "Texas (ERCOT)": EmissionFactors(
        elec_kg_per_kwh=0.379,
        gas_kg_per_therm=5.3,
        source="EPA eGRID ERCT 2024",
        region="Texas"
    ),
    "New York": EmissionFactors(
        elec_kg_per_kwh=0.175,
        gas_kg_per_therm=5.3,
        source="EPA eGRID NYUP 2024",
        region="New York"
    ),
}


def handle_esg_report():
    """Main ESG report page handler."""
    st.title("ESG & Carbon Reporting")
    st.caption("Environmental impact analysis and sustainability documentation")

    if not ESG_AVAILABLE:
        st.error(f"ESG module not available: {ESG_IMPORT_ERROR}")
        return

    # Initialize session state
    if "esg_report" not in st.session_state:
        st.session_state.esg_report = None
    if "esg_annual" not in st.session_state:
        st.session_state.esg_annual = None

    # Sidebar configuration
    with st.sidebar:
        st.header("ESG Settings")
        render_esg_sidebar()

    # Main content tabs
    tabs = st.tabs([
        "Input Data",
        "Carbon Footprint",
        "Energy Metrics",
        "Sustainability Score",
        "Export Report"
    ])

    with tabs[0]:
        render_input_tab()

    with tabs[1]:
        render_carbon_tab()

    with tabs[2]:
        render_energy_tab()

    with tabs[3]:
        render_sustainability_tab()

    with tabs[4]:
        render_esg_export_tab()


def render_esg_sidebar():
    """Render sidebar configuration."""

    # Region selection
    st.subheader("Grid Region")

    region = st.selectbox(
        "Emission Factor Region",
        list(EMISSION_FACTOR_OPTIONS.keys()),
        index=0,
        help="Select grid region for electricity emission factors"
    )
    st.session_state.esg_region = region

    factors = EMISSION_FACTOR_OPTIONS[region]

    with st.expander("Emission Factors"):
        st.write(f"**Source:** {factors.source}")
        st.write(f"**Electricity:** {factors.elec_kg_per_kwh:.3f} kg CO2e/kWh")
        st.write(f"**Natural Gas:** {factors.gas_kg_per_therm:.3f} kg CO2e/therm")

    st.divider()

    # Building info
    st.subheader("Building Info")

    area = st.number_input(
        "Conditioned Area (SF)",
        min_value=1000,
        max_value=10000000,
        value=st.session_state.get("esg_area", 50000),
        step=1000,
        key="esg_area"
    )

    units = st.number_input(
        "Dwelling Units (if residential)",
        min_value=0,
        max_value=1000,
        value=st.session_state.get("esg_units", 0),
        help="Enter 0 for non-residential buildings",
        key="esg_units"
    )


def render_input_tab():
    """Render data input tab."""
    st.header("Energy Data Input")

    input_mode = st.radio(
        "Input Mode",
        ["Manual Entry", "Import from Project"],
        horizontal=True
    )

    if input_mode == "Manual Entry":
        render_manual_entry()
    else:
        render_project_import()


def render_manual_entry():
    """Render manual energy data entry."""
    st.subheader("Annual Energy Consumption")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("**Proposed Building**")

        prop_elec = st.number_input(
            "Electricity (kWh/year)",
            min_value=0,
            value=500000,
            step=10000,
            key="prop_elec"
        )

        prop_gas = st.number_input(
            "Natural Gas (therms/year)",
            min_value=0,
            value=5000,
            step=100,
            key="prop_gas"
        )

        prop_pv = st.number_input(
            "PV Generation (kWh/year)",
            min_value=0,
            value=0,
            step=1000,
            key="prop_pv"
        )

    with col2:
        st.markdown("**Baseline Building** (Optional)")

        base_elec = st.number_input(
            "Electricity (kWh/year)",
            min_value=0,
            value=600000,
            step=10000,
            key="base_elec"
        )

        base_gas = st.number_input(
            "Natural Gas (therms/year)",
            min_value=0,
            value=8000,
            step=100,
            key="base_gas"
        )

        include_baseline = st.checkbox("Include baseline comparison", value=True)

    st.divider()

    # Project info
    st.subheader("Project Information")

    col1, col2 = st.columns(2)

    with col1:
        project_name = st.text_input("Project Name", "My Building")
        building_type = st.selectbox(
            "Building Type",
            ["Office", "Multifamily", "Retail", "Hotel", "Mixed-Use", "Warehouse", "School"]
        )

    with col2:
        compliance_margin = st.number_input(
            "Title 24 Compliance Margin (%)",
            min_value=-50.0,
            max_value=100.0,
            value=15.0,
            step=1.0,
            help="Positive = better than code"
        )
        leed_target = st.selectbox(
            "LEED Target (if applicable)",
            ["None", "Certified", "Silver", "Gold", "Platinum"]
        )

    st.divider()

    # Calculate button
    if st.button("Calculate ESG Metrics", type="primary", use_container_width=True):
        with st.spinner("Calculating environmental impact..."):
            try:
                # Get settings
                region = st.session_state.get("esg_region", "California (CAMX)")
                factors = EMISSION_FACTOR_OPTIONS[region]
                area = st.session_state.get("esg_area", 50000)
                units = st.session_state.get("esg_units", 0)

                # Create annual summaries
                proposed_annual = AnnualEnergySummary(
                    total_elec_kwh=prop_elec,
                    total_gas_therm=prop_gas,
                    pv_generation_kwh=prop_pv,
                )

                # Calculate proposed metrics
                proposed_carbon = calculate_carbon_footprint(
                    annual=proposed_annual,
                    factors=factors,
                    area_sf=area,
                    units=units
                )

                proposed_eui = calculate_eui(proposed_annual, area)
                proposed_renewable = calculate_renewable_pct(proposed_annual)

                proposed_metrics = EsgMetrics(
                    carbon=proposed_carbon,
                    energy_use_intensity_kbtu_sf=proposed_eui,
                    renewable_energy_pct=proposed_renewable,
                    title24_margin_pct=compliance_margin,
                    leed_target=leed_target if leed_target != "None" else ""
                )

                # Create baseline if requested
                baseline_metrics = None
                if include_baseline:
                    baseline_annual = AnnualEnergySummary(
                        total_elec_kwh=base_elec,
                        total_gas_therm=base_gas,
                        pv_generation_kwh=0,
                    )

                    baseline_carbon = calculate_carbon_footprint(
                        annual=baseline_annual,
                        factors=factors,
                        area_sf=area,
                        units=units
                    )

                    baseline_eui = calculate_eui(baseline_annual, area)

                    baseline_metrics = EsgMetrics(
                        carbon=baseline_carbon,
                        energy_use_intensity_kbtu_sf=baseline_eui,
                        renewable_energy_pct=0.0,
                    )

                # Create report
                report = EsgReport(
                    project_name=project_name,
                    building_type=building_type,
                    conditioned_area_sf=area,
                    proposed=proposed_metrics,
                    baseline=baseline_metrics,
                )

                # Calculate reductions
                if baseline_metrics:
                    if baseline_metrics.carbon.total_kg > 0:
                        reduction = baseline_metrics.carbon.total_kg - proposed_metrics.carbon.net_kg
                        report.carbon_reduction_pct = (reduction / baseline_metrics.carbon.total_kg) * 100

                    if baseline_metrics.energy_use_intensity_kbtu_sf > 0:
                        reduction = baseline_metrics.energy_use_intensity_kbtu_sf - proposed_metrics.energy_use_intensity_kbtu_sf
                        report.energy_reduction_pct = (reduction / baseline_metrics.energy_use_intensity_kbtu_sf) * 100

                st.session_state.esg_report = report
                st.session_state.esg_annual = proposed_annual

                st.success("ESG metrics calculated successfully!")
                st.balloons()

            except Exception as e:
                st.error(f"Calculation failed: {e}")


def render_project_import():
    """Render project import section."""
    st.subheader("Import from Simulation Project")

    project_path = st.text_input(
        "Project Run Folder",
        placeholder="/path/to/project - run",
    )

    if st.button("Import Project Data"):
        if project_path:
            with st.spinner("Importing..."):
                try:
                    path = Path(project_path)
                    if path.exists():
                        discovery = discover_simulation_outputs(path)
                        if discovery.is_complete:
                            st.success("Project imported successfully!")
                            st.info("Project import integration coming in next update")
                        else:
                            st.warning("Incomplete simulation outputs")
                    else:
                        st.error("Path does not exist")
                except Exception as e:
                    st.error(f"Import failed: {e}")
        else:
            st.warning("Please enter a project path")


def render_carbon_tab():
    """Render carbon footprint analysis tab."""
    st.header("Carbon Footprint Analysis")

    report = st.session_state.get("esg_report")
    if not report:
        st.info("Enter energy data in the Input tab and click 'Calculate ESG Metrics' to see results.")
        return

    carbon = report.proposed.carbon

    # Summary metrics
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            "Total Carbon",
            f"{carbon.total_tonnes:,.1f} tonnes",
            help="Annual CO2 equivalent emissions"
        )

    with col2:
        st.metric(
            "Carbon Intensity",
            f"{carbon.kg_per_sf:.2f} kg/SF",
        )

    with col3:
        if carbon.avoided_kg > 0:
            st.metric(
                "Avoided (PV)",
                f"{carbon.avoided_kg/1000:,.1f} tonnes",
            )
        else:
            st.metric("Avoided (PV)", "0 tonnes")

    with col4:
        st.metric(
            "Net Carbon",
            f"{carbon.net_kg/1000:,.1f} tonnes",
        )

    st.divider()

    # Scope breakdown
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Emissions by Scope")

        if PLOTLY_AVAILABLE:
            fig = go.Figure(data=[go.Pie(
                labels=["Scope 1 (Direct)", "Scope 2 (Indirect)"],
                values=[carbon.scope_1_kg, carbon.scope_2_kg],
                hole=0.4,
                marker=dict(colors=['#e74c3c', '#3498db']),
                textinfo='label+percent',
            )])
            fig.update_layout(
                showlegend=True,
                height=350,
                margin=dict(t=20, b=20, l=20, r=20)
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.write(f"**Scope 1 (Direct):** {carbon.scope_1_kg:,.0f} kg CO2e")
            st.write(f"**Scope 2 (Indirect):** {carbon.scope_2_kg:,.0f} kg CO2e")

    with col2:
        st.subheader("Scope Details")

        with st.expander("Scope 1 - Direct Emissions"):
            st.write("On-site fuel combustion:")
            for source, value in carbon.scope_1_breakdown.items():
                st.write(f"  - {source.replace('_', ' ').title()}: {value:,.0f} kg CO2e")

        with st.expander("Scope 2 - Indirect Emissions"):
            st.write("Purchased electricity:")
            for source, value in carbon.scope_2_breakdown.items():
                st.write(f"  - {source.replace('_', ' ').title()}: {value:,.0f} kg CO2e")

        # Emission factors used
        region = st.session_state.get("esg_region", "California (CAMX)")
        factors = EMISSION_FACTOR_OPTIONS[region]

        with st.expander("Emission Factors Used"):
            st.write(f"**Region:** {factors.region}")
            st.write(f"**Source:** {factors.source}")
            st.write(f"**Electricity:** {factors.elec_kg_per_kwh:.3f} kg CO2e/kWh")
            st.write(f"**Natural Gas:** {factors.gas_kg_per_therm:.3f} kg CO2e/therm")

    # Baseline comparison
    if report.baseline:
        st.divider()
        st.subheader("Baseline Comparison")

        col1, col2, col3 = st.columns(3)

        with col1:
            st.metric(
                "Baseline Carbon",
                f"{report.baseline.carbon.total_tonnes:,.1f} tonnes"
            )

        with col2:
            st.metric(
                "Proposed Carbon",
                f"{carbon.net_kg/1000:,.1f} tonnes"
            )

        with col3:
            st.metric(
                "Carbon Reduction",
                f"{report.carbon_reduction_pct:.1f}%",
                delta=f"{(report.baseline.carbon.total_kg - carbon.net_kg)/1000:,.1f} tonnes"
            )

        # Comparison chart
        if PLOTLY_AVAILABLE:
            fig = go.Figure()
            fig.add_trace(go.Bar(
                x=["Baseline", "Proposed (Gross)", "Proposed (Net)"],
                y=[
                    report.baseline.carbon.total_tonnes,
                    carbon.total_tonnes,
                    carbon.net_kg / 1000
                ],
                marker_color=['#e74c3c', '#f39c12', '#27ae60'],
                text=[
                    f"{report.baseline.carbon.total_tonnes:,.1f}",
                    f"{carbon.total_tonnes:,.1f}",
                    f"{carbon.net_kg/1000:,.1f}"
                ],
                textposition='auto',
            ))
            fig.update_layout(
                title="Carbon Emissions Comparison (tonnes CO2e)",
                yaxis_title="Tonnes CO2e",
                height=350,
            )
            st.plotly_chart(fig, use_container_width=True)


def render_energy_tab():
    """Render energy metrics tab."""
    st.header("Energy Metrics")

    report = st.session_state.get("esg_report")
    if not report:
        st.info("Enter energy data in the Input tab and click 'Calculate ESG Metrics' to see results.")
        return

    # Key metrics
    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric(
            "Site EUI",
            f"{report.proposed.energy_use_intensity_kbtu_sf:.1f} kBtu/SF/yr",
            help="Energy Use Intensity"
        )

    with col2:
        st.metric(
            "Renewable Energy",
            f"{report.proposed.renewable_energy_pct:.1f}%",
        )

    with col3:
        if report.proposed.title24_margin_pct:
            margin = report.proposed.title24_margin_pct
            delta_text = "better than code" if margin > 0 else "worse than code"
            st.metric(
                "Title 24 Margin",
                f"{margin:+.1f}%",
                delta=delta_text
            )

    st.divider()

    # EUI benchmarking
    st.subheader("EUI Benchmarking")

    # Define benchmarks by building type
    eui_benchmarks = {
        "Office": {"typical": 95, "efficient": 65, "best": 45},
        "Multifamily": {"typical": 60, "efficient": 45, "best": 30},
        "Retail": {"typical": 85, "efficient": 60, "best": 40},
        "Hotel": {"typical": 110, "efficient": 80, "best": 55},
        "Mixed-Use": {"typical": 75, "efficient": 55, "best": 40},
        "Warehouse": {"typical": 35, "efficient": 25, "best": 18},
        "School": {"typical": 75, "efficient": 55, "best": 40},
    }

    building_type = report.building_type
    benchmarks = eui_benchmarks.get(building_type, eui_benchmarks["Office"])
    current_eui = report.proposed.energy_use_intensity_kbtu_sf

    if PLOTLY_AVAILABLE:
        # Gauge chart for EUI
        fig = go.Figure(go.Indicator(
            mode="gauge+number",
            value=current_eui,
            title={"text": f"Site EUI ({report.building_type})"},
            gauge={
                "axis": {"range": [0, benchmarks["typical"] * 1.5]},
                "bar": {"color": "#3498db"},
                "steps": [
                    {"range": [0, benchmarks["best"]], "color": "#27ae60"},
                    {"range": [benchmarks["best"], benchmarks["efficient"]], "color": "#f1c40f"},
                    {"range": [benchmarks["efficient"], benchmarks["typical"]], "color": "#e67e22"},
                    {"range": [benchmarks["typical"], benchmarks["typical"] * 1.5], "color": "#e74c3c"},
                ],
                "threshold": {
                    "line": {"color": "black", "width": 4},
                    "thickness": 0.75,
                    "value": current_eui
                }
            }
        ))
        fig.update_layout(height=300)
        st.plotly_chart(fig, use_container_width=True)

    # Benchmark comparison table
    col1, col2 = st.columns([2, 1])

    with col1:
        benchmark_data = [
            {"Category": "Best-in-Class", "EUI (kBtu/SF)": benchmarks["best"], "Your Building": "Better" if current_eui <= benchmarks["best"] else ""},
            {"Category": "Efficient", "EUI (kBtu/SF)": benchmarks["efficient"], "Your Building": "Better" if benchmarks["best"] < current_eui <= benchmarks["efficient"] else ""},
            {"Category": "Typical", "EUI (kBtu/SF)": benchmarks["typical"], "Your Building": "Better" if benchmarks["efficient"] < current_eui <= benchmarks["typical"] else ""},
            {"Category": "Below Average", "EUI (kBtu/SF)": f">{benchmarks['typical']}", "Your Building": "Current" if current_eui > benchmarks["typical"] else ""},
        ]
        st.dataframe(benchmark_data, use_container_width=True, hide_index=True)

    with col2:
        # Performance rating
        if current_eui <= benchmarks["best"]:
            rating = "Excellent"
            color = "#27ae60"
        elif current_eui <= benchmarks["efficient"]:
            rating = "Good"
            color = "#f1c40f"
        elif current_eui <= benchmarks["typical"]:
            rating = "Average"
            color = "#e67e22"
        else:
            rating = "Below Average"
            color = "#e74c3c"

        st.markdown(f"""
        <div style="text-align: center; padding: 20px; background-color: {color}20; border-radius: 10px; border: 2px solid {color};">
            <h3 style="color: {color}; margin: 0;">{rating}</h3>
            <p style="margin: 10px 0 0 0;">Performance Rating</p>
        </div>
        """, unsafe_allow_html=True)


def render_sustainability_tab():
    """Render sustainability score and certifications tab."""
    st.header("Sustainability Assessment")

    report = st.session_state.get("esg_report")
    if not report:
        st.info("Enter energy data in the Input tab and click 'Calculate ESG Metrics' to see results.")
        return

    # Calculate sustainability score (simplified)
    score_components = []

    # Carbon score (0-25 points)
    carbon_intensity = report.proposed.carbon.kg_per_sf
    if carbon_intensity <= 5:
        carbon_score = 25
    elif carbon_intensity <= 10:
        carbon_score = 20
    elif carbon_intensity <= 15:
        carbon_score = 15
    elif carbon_intensity <= 20:
        carbon_score = 10
    else:
        carbon_score = 5
    score_components.append(("Carbon Intensity", carbon_score, 25))

    # EUI score (0-25 points)
    eui = report.proposed.energy_use_intensity_kbtu_sf
    if eui <= 40:
        eui_score = 25
    elif eui <= 60:
        eui_score = 20
    elif eui <= 80:
        eui_score = 15
    elif eui <= 100:
        eui_score = 10
    else:
        eui_score = 5
    score_components.append(("Energy Efficiency", eui_score, 25))

    # Renewable score (0-25 points)
    renewable_pct = report.proposed.renewable_energy_pct
    renewable_score = min(25, int(renewable_pct / 4))
    score_components.append(("Renewable Energy", renewable_score, 25))

    # Code margin score (0-25 points)
    margin = report.proposed.title24_margin_pct or 0
    if margin >= 30:
        margin_score = 25
    elif margin >= 20:
        margin_score = 20
    elif margin >= 10:
        margin_score = 15
    elif margin >= 0:
        margin_score = 10
    else:
        margin_score = 5
    score_components.append(("Code Performance", margin_score, 25))

    total_score = sum(s[1] for s in score_components)
    max_score = sum(s[2] for s in score_components)

    # Overall score
    col1, col2 = st.columns([1, 2])

    with col1:
        if PLOTLY_AVAILABLE:
            fig = go.Figure(go.Indicator(
                mode="gauge+number",
                value=total_score,
                title={"text": "Sustainability Score"},
                gauge={
                    "axis": {"range": [0, 100]},
                    "bar": {"color": "#3498db"},
                    "steps": [
                        {"range": [0, 40], "color": "#e74c3c"},
                        {"range": [40, 60], "color": "#f39c12"},
                        {"range": [60, 80], "color": "#f1c40f"},
                        {"range": [80, 100], "color": "#27ae60"},
                    ],
                }
            ))
            fig.update_layout(height=250)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.metric("Sustainability Score", f"{total_score}/100")

    with col2:
        st.subheader("Score Breakdown")

        for name, score, max_val in score_components:
            pct = score / max_val * 100
            st.progress(pct / 100, text=f"{name}: {score}/{max_val}")

    st.divider()

    # Certification readiness
    st.subheader("Certification Readiness")

    certifications = []

    # LEED readiness
    if report.carbon_reduction_pct >= 20 and renewable_pct >= 10:
        certifications.append(("LEED Gold", "Ready", "#27ae60"))
    elif report.carbon_reduction_pct >= 10:
        certifications.append(("LEED Silver", "Ready", "#27ae60"))
    else:
        certifications.append(("LEED Certified", "Potential", "#f39c12"))

    # Energy Star readiness
    if eui <= 60:
        certifications.append(("ENERGY STAR", "Likely Eligible", "#27ae60"))
    else:
        certifications.append(("ENERGY STAR", "May Need Improvement", "#f39c12"))

    # Zero Energy readiness
    if renewable_pct >= 100:
        certifications.append(("Zero Net Energy", "Achieved", "#27ae60"))
    elif renewable_pct >= 50:
        certifications.append(("Zero Net Energy", "On Track", "#f39c12"))
    else:
        certifications.append(("Zero Net Energy", "Gap to Close", "#e74c3c"))

    col1, col2, col3 = st.columns(3)

    for i, (cert, status, color) in enumerate(certifications):
        with [col1, col2, col3][i]:
            st.markdown(f"""
            <div style="text-align: center; padding: 15px; background-color: {color}20; border-radius: 8px; border: 1px solid {color};">
                <h4 style="margin: 0;">{cert}</h4>
                <p style="color: {color}; margin: 5px 0 0 0; font-weight: bold;">{status}</p>
            </div>
            """, unsafe_allow_html=True)

    st.divider()

    # Recommendations
    st.subheader("Recommendations")

    recommendations = []

    if renewable_pct < 50:
        recommendations.append("Consider adding or expanding on-site solar PV to increase renewable energy percentage")

    if eui > 60:
        recommendations.append("Evaluate building envelope improvements to reduce energy consumption")

    if carbon_intensity > 10:
        recommendations.append("Explore electrification of heating systems to reduce Scope 1 emissions")

    if margin < 15:
        recommendations.append("Review HVAC and lighting systems for efficiency improvements beyond code")

    if not recommendations:
        recommendations.append("Building is performing well. Continue monitoring and maintenance.")

    for rec in recommendations:
        st.write(f"- {rec}")


def render_esg_export_tab():
    """Render ESG report export tab."""
    st.header("Export ESG Report")

    report = st.session_state.get("esg_report")
    if not report:
        st.info("Calculate ESG metrics first to export a report.")
        return

    # Text report
    st.subheader("Text Report")

    text_report = format_esg_report(report)
    st.text_area(
        "Report Preview",
        value=text_report,
        height=400,
        disabled=True
    )

    st.download_button(
        "Download Text Report",
        data=text_report,
        file_name=f"{report.project_name.replace(' ', '_')}_ESG_Report.txt",
        mime="text/plain"
    )

    st.divider()

    # CSV export
    st.subheader("CSV Export")

    if st.button("Generate CSV", use_container_width=True):
        try:
            import csv
            import io

            output = io.StringIO()
            writer = csv.writer(output)

            # Header
            writer.writerow(["ESG Report", report.project_name])
            writer.writerow(["Building Type", report.building_type])
            writer.writerow(["Conditioned Area (SF)", report.conditioned_area_sf])
            writer.writerow([])

            # Carbon metrics
            carbon = report.proposed.carbon
            writer.writerow(["Carbon Metrics", "Value", "Unit"])
            writer.writerow(["Scope 1 Emissions", carbon.scope_1_kg, "kg CO2e"])
            writer.writerow(["Scope 2 Emissions", carbon.scope_2_kg, "kg CO2e"])
            writer.writerow(["Total Emissions", carbon.total_kg, "kg CO2e"])
            writer.writerow(["Carbon Intensity", carbon.kg_per_sf, "kg CO2e/SF"])
            writer.writerow(["Avoided Emissions", carbon.avoided_kg, "kg CO2e"])
            writer.writerow(["Net Emissions", carbon.net_kg, "kg CO2e"])
            writer.writerow([])

            # Energy metrics
            writer.writerow(["Energy Metrics", "Value", "Unit"])
            writer.writerow(["Site EUI", report.proposed.energy_use_intensity_kbtu_sf, "kBtu/SF/yr"])
            writer.writerow(["Renewable Energy", report.proposed.renewable_energy_pct, "%"])
            writer.writerow(["Title 24 Margin", report.proposed.title24_margin_pct, "%"])

            # Reductions
            if report.baseline:
                writer.writerow([])
                writer.writerow(["Reductions vs Baseline", "Value", "Unit"])
                writer.writerow(["Carbon Reduction", report.carbon_reduction_pct, "%"])
                writer.writerow(["Energy Reduction", report.energy_reduction_pct, "%"])

            csv_data = output.getvalue()

            st.download_button(
                "Download CSV",
                data=csv_data,
                file_name=f"{report.project_name.replace(' ', '_')}_ESG_Data.csv",
                mime="text/csv"
            )

            st.success("CSV generated!")

        except Exception as e:
            st.error(f"Export failed: {e}")


# Entry point for navigation
if __name__ == "__main__":
    handle_esg_report()
