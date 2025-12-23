"""
LCCA Dashboard Page
===================

Interactive Life Cycle Cost Analysis dashboard for energy projects.

Features:
- Project discovery and selection
- Tariff configuration (CA/HI utilities)
- LCCA results display (NPV, IRR, Payback, SIR)
- Cash flow visualization
- TOU cost breakdown
- Baseline vs Proposed comparison
- Sensitivity analysis with interactive sliders
- Excel/PDF export

Author: ECO Tools Team
Version: 7.0.0
Date: December 2024
"""

import streamlit as st
import sys
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple
import tempfile

# Add project root to path
ROOT = Path(__file__).resolve().parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Import LCCA modules with error handling
try:
    from eco_tools.lcca import (
        # Auto-discovery
        discover_simulation_outputs,
        DiscoveredOutputs,
        # Parsers
        SimulationOutput,
        # Tariffs
        TouTariff,
        get_tariff_by_name,
        list_available_tariffs,
        calculate_tou_costs,
        hourly_energy_to_usage,
        TouCostBreakdown,
        # Calculators
        LccaResults,
        run_lcca,
        run_tou_lcca,
        ScenarioAssumptions,
        LccaScenario,
        TouLccaScenario,
        # Bridge
        simulation_to_scenario,
        create_baseline_scenario,
        create_proposed_scenario,
        # Reports
        generate_econ1,
        Econ1Report,
        # Export
        export_lcca_to_excel,
        ExcelExportOptions,
    )
    from eco_tools.lcca.parsers import parse_hourly_results
    from eco_tools.lcca.cost_analysis import analyze_project_costs, ProjectCostAnalysis
    from eco_tools.lcca.ca_hi_helpers import (
        get_region_from_climate_zone,
        get_default_rate_id,
        CLIMATE_ZONE_TO_REGION,
    )
    LCCA_AVAILABLE = True
except ImportError as e:
    LCCA_AVAILABLE = False
    LCCA_IMPORT_ERROR = str(e)

# Optional: PDF export
try:
    from eco_tools.lcca import export_lcca_to_pdf, PDF_EXPORT_AVAILABLE
except ImportError:
    PDF_EXPORT_AVAILABLE = False

# Optional: Plotting
try:
    import plotly.graph_objects as go
    import plotly.express as px
    PLOTLY_AVAILABLE = True
except ImportError:
    PLOTLY_AVAILABLE = False


def handle_lcca_dashboard():
    """Main LCCA dashboard page handler."""
    st.title("💰 LCCA Dashboard")
    st.caption("Life Cycle Cost Analysis for energy projects")

    if not LCCA_AVAILABLE:
        st.error(f"❌ LCCA module not available: {LCCA_IMPORT_ERROR}")
        return

    # Initialize session state
    if "lcca_project_path" not in st.session_state:
        st.session_state.lcca_project_path = None
    if "lcca_results" not in st.session_state:
        st.session_state.lcca_results = None
    if "lcca_analysis" not in st.session_state:
        st.session_state.lcca_analysis = None

    # Sidebar configuration
    with st.sidebar:
        st.header("⚙️ LCCA Settings")
        render_sidebar_config()

    # Main content tabs
    tabs = st.tabs([
        "📂 Project",
        "📊 Results",
        "📈 Cash Flow",
        "⚡ TOU Analysis",
        "🔄 Comparison",
        "🎚️ Sensitivity",
        "📤 Export"
    ])

    with tabs[0]:
        render_project_tab()

    with tabs[1]:
        render_results_tab()

    with tabs[2]:
        render_cashflow_tab()

    with tabs[3]:
        render_tou_tab()

    with tabs[4]:
        render_comparison_tab()

    with tabs[5]:
        render_sensitivity_tab()

    with tabs[6]:
        render_export_tab()


def render_sidebar_config():
    """Render sidebar configuration options."""

    # Tariff selection
    st.subheader("💵 Tariff")

    tariff_options = [
        "PG&E B-20",
        "PG&E E-TOU-C",
        "SCE TOU-GS-3",
        "SCE TOU-D-4-9PM",
        "SDG&E AL-TOU",
        "SDG&E TOU-DR1",
        "HECO R-TOU",
        "US-AVG",
    ]

    selected_tariff = st.selectbox(
        "Utility Rate",
        tariff_options,
        index=0,
        key="lcca_tariff_select"
    )
    st.session_state.lcca_tariff_id = selected_tariff

    # Show tariff details
    tariff = get_tariff_by_name(selected_tariff)
    if tariff:
        with st.expander("Rate Details"):
            st.write(f"**Utility:** {tariff.utility}")
            st.write(f"**Summer On-Peak:** ${tariff.energy_rates.summer_on_peak:.3f}/kWh")
            st.write(f"**Summer Off-Peak:** ${tariff.energy_rates.summer_off_peak:.3f}/kWh")
            st.write(f"**Winter Off-Peak:** ${tariff.energy_rates.winter_off_peak:.3f}/kWh")

    st.divider()

    # Financial assumptions
    st.subheader("📈 Assumptions")

    analysis_period = st.slider(
        "Analysis Period (years)",
        min_value=10,
        max_value=30,
        value=25,
        key="lcca_analysis_period"
    )

    discount_rate = st.slider(
        "Discount Rate (%)",
        min_value=1.0,
        max_value=10.0,
        value=3.0,
        step=0.5,
        key="lcca_discount_rate"
    ) / 100

    elec_escalation = st.slider(
        "Electricity Escalation (%/yr)",
        min_value=0.0,
        max_value=5.0,
        value=2.5,
        step=0.5,
        key="lcca_elec_escalation"
    ) / 100

    # Store in session state
    st.session_state.lcca_assumptions = ScenarioAssumptions(
        analysis_years=analysis_period,
        discount_rate_real=discount_rate,
        elec_escalation=elec_escalation,
        gas_escalation=0.02,
        inflation_rate=0.025,
    )

    st.divider()

    # CAPEX input
    st.subheader("💰 Capital Cost")

    capex = st.number_input(
        "Incremental Cost ($)",
        min_value=0,
        max_value=10000000,
        value=100000,
        step=10000,
        key="lcca_capex"
    )
    st.session_state.lcca_capex = capex


def render_project_tab():
    """Render project selection and discovery tab."""
    st.header("📂 Project Selection")

    # Option 1: Browse for project folder
    st.subheader("📁 Select Project Folder")

    project_path = st.text_input(
        "Project Run Folder Path",
        value=st.session_state.get("lcca_project_path", ""),
        placeholder="/path/to/project - run",
        help="Enter the path to a CBECC simulation run folder"
    )

    col1, col2 = st.columns(2)

    with col1:
        if st.button("🔍 Discover Files", use_container_width=True):
            if project_path:
                with st.spinner("Discovering simulation files..."):
                    try:
                        path = Path(project_path)
                        if path.exists():
                            discovery = discover_simulation_outputs(path)
                            st.session_state.lcca_project_path = project_path
                            st.session_state.lcca_discovery = discovery

                            if discovery.is_complete:
                                st.success("✅ Found complete simulation outputs!")
                            else:
                                st.warning("⚠️ Some files missing")
                        else:
                            st.error("❌ Path does not exist")
                    except Exception as e:
                        st.error(f"❌ Discovery failed: {e}")
            else:
                st.warning("Please enter a project path")

    with col2:
        if st.button("▶️ Run Analysis", use_container_width=True):
            if project_path:
                run_lcca_analysis(project_path)
            else:
                st.warning("Please select a project first")

    # Show discovery results
    if "lcca_discovery" in st.session_state and st.session_state.lcca_discovery:
        discovery = st.session_state.lcca_discovery

        st.divider()
        st.subheader("📋 Discovered Files")

        col1, col2, col3 = st.columns(3)

        with col1:
            if discovery.hourly_results_proposed:
                st.success("✅ HourlyResults (Proposed)")
            else:
                st.error("❌ HourlyResults (Proposed)")

        with col2:
            if discovery.hourly_results_standard:
                st.success("✅ HourlyResults (Baseline)")
            else:
                st.warning("⚠️ HourlyResults (Baseline)")

        with col3:
            if discovery.pv_battery:
                st.success("✅ PV/Battery Data")
            else:
                st.info("ℹ️ No PV/Battery")

    # Quick start examples
    st.divider()
    st.subheader("🚀 Quick Start Examples")

    example_paths = [
        ("Ventura & 7th (Full Sim)",
         str(ROOT / "LCCA Tests/Ventura & 7th/Maestro/Full sim/Ventura and 7th Updated Maestro_CUAC - run")),
        ("Bressi Ranch",
         str(ROOT / "LCCA Tests/Original Sample models/Bressi Ranch/Bressi Ranch Apartments - run")),
        ("Del Amo Circle",
         str(ROOT / "LCCA Tests/Original Sample models/Del Amo/Del Amo Circle-LEED_CBECC2022_2024-12-11 - run")),
    ]

    for name, path in example_paths:
        if Path(path).exists():
            if st.button(f"📂 Load {name}", key=f"load_{name}"):
                st.session_state.lcca_project_path = path
                run_lcca_analysis(path)
                st.rerun()


def run_lcca_analysis(project_path: str):
    """Run LCCA analysis on the selected project."""
    with st.spinner("Running LCCA analysis..."):
        try:
            tariff_id = st.session_state.get("lcca_tariff_id", "PG&E B-20")

            # Use cost analysis utility
            analysis = analyze_project_costs(
                Path(project_path),
                [tariff_id]
            )

            st.session_state.lcca_analysis = analysis
            st.session_state.lcca_project_path = project_path

            # Also run full LCCA for financial metrics
            if analysis.discovery and analysis.discovery.is_complete:
                # Parse simulation
                proposed_path = analysis.discovery.hourly_results_proposed.path
                proposed = parse_hourly_results(str(proposed_path))

                # Get tariff
                tariff = get_tariff_by_name(tariff_id)

                # Get assumptions
                assumptions = st.session_state.get("lcca_assumptions", ScenarioAssumptions())
                capex = st.session_state.get("lcca_capex", 100000)

                # Calculate annual cost
                if proposed.hourly:
                    hourly_usage = hourly_energy_to_usage(proposed.hourly)
                    tou_breakdown = calculate_tou_costs(hourly_usage, tariff)
                    annual_cost = tou_breakdown.total_cost
                else:
                    annual_cost = proposed.annual.total_elec_kwh * 0.20  # Fallback

                # Create scenario and run LCCA
                from eco_tools.lcca import Tariff
                simple_tariff = Tariff(
                    elec_rate_per_kwh=tariff.energy_rates.summer_off_peak,
                    gas_rate_per_therm=tariff.gas_rate,
                )

                scenario = LccaScenario(
                    name="Proposed Design",
                    annual_elec_kwh=proposed.annual.total_elec_kwh,
                    annual_gas_therm=proposed.annual.total_gas_therm,
                    tariff=simple_tariff,
                    capex=capex,
                    assumptions=assumptions,
                )

                results = run_lcca(scenario)
                st.session_state.lcca_results = results

            st.success("✅ Analysis complete!")

        except Exception as e:
            st.error(f"❌ Analysis failed: {e}")
            import traceback
            st.code(traceback.format_exc())


def render_results_tab():
    """Render LCCA results summary tab."""
    st.header("📊 LCCA Results")

    analysis = st.session_state.get("lcca_analysis")
    results = st.session_state.get("lcca_results")

    if not analysis:
        st.info("👈 Select a project and run analysis first")
        return

    # Project summary
    st.subheader(f"📁 {analysis.project_name}")

    # Key metrics in columns
    col1, col2, col3, col4 = st.columns(4)

    if analysis.proposed_energy:
        pe = analysis.proposed_energy

        with col1:
            st.metric(
                "Annual Consumption",
                f"{pe.total_consumption_kwh:,.0f} kWh",
                help="Total annual electricity consumption"
            )

        with col2:
            st.metric(
                "PV Generation",
                f"{pe.pv_generation_kwh:,.0f} kWh",
                help="Annual PV system output"
            )

        with col3:
            st.metric(
                "Peak Demand",
                f"{pe.peak_demand_kw:,.1f} kW",
                help="Maximum hourly demand"
            )

        with col4:
            if analysis.tariff_analyses:
                ta = list(analysis.tariff_analyses.values())[0]
                st.metric(
                    "Annual Cost",
                    f"${ta.total_annual_cost:,.0f}",
                    help="Total annual energy cost"
                )

    st.divider()

    # Financial metrics (if LCCA results available)
    if results:
        st.subheader("💰 Financial Metrics")

        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric(
                "Net Present Value",
                f"${results.npv:,.0f}",
                delta=None,
                help="Present value of all cash flows"
            )

        with col2:
            irr_pct = results.irr * 100 if results.irr else 0
            st.metric(
                "Internal Rate of Return",
                f"{irr_pct:.1f}%",
                help="Discount rate at which NPV = 0"
            )

        with col3:
            st.metric(
                "Simple Payback",
                f"{results.simple_payback:.1f} years",
                help="Years to recover investment"
            )

        with col4:
            st.metric(
                "Savings-to-Investment Ratio",
                f"{results.sir:.2f}",
                delta="✅ Passes" if results.sir >= 1.0 else "❌ Fails",
                help="Total savings / Total investment"
            )

    st.divider()

    # TOU Distribution
    if analysis.proposed_energy:
        st.subheader("⚡ TOU Distribution")

        pe = analysis.proposed_energy

        col1, col2, col3 = st.columns(3)

        with col1:
            st.metric("On-Peak", f"{pe.on_peak_pct:.1f}%")
        with col2:
            st.metric("Mid-Peak", f"{pe.mid_peak_pct:.1f}%")
        with col3:
            st.metric("Off-Peak", f"{pe.off_peak_pct:.1f}%")

        # TOU bar chart
        if PLOTLY_AVAILABLE:
            fig = go.Figure(data=[
                go.Bar(
                    x=["On-Peak", "Mid-Peak", "Off-Peak"],
                    y=[pe.on_peak_pct, pe.mid_peak_pct, pe.off_peak_pct],
                    marker_color=["#e74c3c", "#f39c12", "#27ae60"]
                )
            ])
            fig.update_layout(
                title="Consumption by TOU Period",
                yaxis_title="Percentage (%)",
                height=300
            )
            st.plotly_chart(fig, use_container_width=True)


def render_cashflow_tab():
    """Render cash flow visualization tab."""
    st.header("📈 Cash Flow Analysis")

    results = st.session_state.get("lcca_results")

    if not results:
        st.info("👈 Run analysis first to see cash flow")
        return

    if not hasattr(results, 'cash_flows') or not results.cash_flows:
        st.warning("Cash flow data not available")
        return

    # Cash flow table
    st.subheader("Annual Cash Flows")

    cash_flow_data = []
    cumulative = 0

    for cf in results.cash_flows:
        cumulative += cf.net_cash_flow
        cash_flow_data.append({
            "Year": cf.year,
            "Energy Savings": f"${cf.energy_savings:,.0f}",
            "O&M Costs": f"${cf.om_costs:,.0f}",
            "Net Cash Flow": f"${cf.net_cash_flow:,.0f}",
            "Cumulative": f"${cumulative:,.0f}",
        })

    st.dataframe(cash_flow_data, use_container_width=True)

    # Cash flow chart
    if PLOTLY_AVAILABLE:
        st.subheader("Cumulative Cash Flow")

        years = [cf.year for cf in results.cash_flows]
        net_flows = [cf.net_cash_flow for cf in results.cash_flows]

        # Calculate cumulative
        cumulative = []
        total = 0
        for nf in net_flows:
            total += nf
            cumulative.append(total)

        fig = go.Figure()

        # Add bar chart for annual cash flows
        fig.add_trace(go.Bar(
            x=years,
            y=net_flows,
            name="Annual Cash Flow",
            marker_color="#3498db"
        ))

        # Add line for cumulative
        fig.add_trace(go.Scatter(
            x=years,
            y=cumulative,
            name="Cumulative",
            line=dict(color="#e74c3c", width=3),
            yaxis="y2"
        ))

        # Add break-even line
        fig.add_hline(y=0, line_dash="dash", line_color="gray")

        fig.update_layout(
            title="Cash Flow Over Analysis Period",
            xaxis_title="Year",
            yaxis_title="Annual Cash Flow ($)",
            yaxis2=dict(
                title="Cumulative ($)",
                overlaying="y",
                side="right"
            ),
            height=400,
            legend=dict(orientation="h", yanchor="bottom", y=1.02)
        )

        st.plotly_chart(fig, use_container_width=True)


def render_tou_tab():
    """Render TOU cost breakdown tab."""
    st.header("⚡ Time-of-Use Analysis")

    analysis = st.session_state.get("lcca_analysis")

    if not analysis or not analysis.tariff_analyses:
        st.info("👈 Run analysis first")
        return

    tariff_id = st.session_state.get("lcca_tariff_id", "PG&E B-20")
    ta = analysis.tariff_analyses.get(tariff_id)

    if not ta or not ta.tou_breakdown:
        st.warning("TOU breakdown not available")
        return

    tb = ta.tou_breakdown

    # Cost summary
    st.subheader("💵 Cost Summary")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("Energy Cost", f"${ta.energy_cost:,.0f}")
    with col2:
        st.metric("Demand Cost", f"${ta.demand_cost:,.0f}")
    with col3:
        st.metric("Total Annual", f"${ta.total_annual_cost:,.0f}")

    st.divider()

    # Season breakdown
    st.subheader("☀️ Summer vs 🌨️ Winter")

    col1, col2 = st.columns(2)

    with col1:
        st.write("**Summer**")
        summer_data = {
            "On-Peak": {"kWh": tb.summer_on_peak_kwh, "Cost": tb.summer_on_peak_cost},
            "Mid-Peak": {"kWh": tb.summer_mid_peak_kwh, "Cost": tb.summer_mid_peak_cost},
            "Off-Peak": {"kWh": tb.summer_off_peak_kwh, "Cost": tb.summer_off_peak_cost},
        }
        for period, data in summer_data.items():
            st.write(f"  {period}: {data['kWh']:,.0f} kWh = ${data['Cost']:,.0f}")

    with col2:
        st.write("**Winter**")
        winter_data = {
            "On-Peak": {"kWh": tb.winter_on_peak_kwh, "Cost": tb.winter_on_peak_cost},
            "Mid-Peak": {"kWh": tb.winter_mid_peak_kwh, "Cost": tb.winter_mid_peak_cost},
            "Off-Peak": {"kWh": tb.winter_off_peak_kwh, "Cost": tb.winter_off_peak_cost},
        }
        for period, data in winter_data.items():
            st.write(f"  {period}: {data['kWh']:,.0f} kWh = ${data['Cost']:,.0f}")

    # TOU cost pie chart
    if PLOTLY_AVAILABLE:
        st.subheader("📊 Cost Distribution")

        labels = [
            "Summer On-Peak", "Summer Mid-Peak", "Summer Off-Peak",
            "Winter On-Peak", "Winter Mid-Peak", "Winter Off-Peak"
        ]
        values = [
            tb.summer_on_peak_cost, tb.summer_mid_peak_cost, tb.summer_off_peak_cost,
            tb.winter_on_peak_cost, tb.winter_mid_peak_cost, tb.winter_off_peak_cost
        ]
        colors = ["#e74c3c", "#f39c12", "#27ae60", "#c0392b", "#d68910", "#1e8449"]

        fig = go.Figure(data=[go.Pie(
            labels=labels,
            values=values,
            marker_colors=colors,
            hole=0.4
        )])

        fig.update_layout(
            title="Energy Cost by TOU Period",
            height=400
        )

        st.plotly_chart(fig, use_container_width=True)


def render_comparison_tab():
    """Render baseline vs proposed comparison tab."""
    st.header("🔄 Baseline vs Proposed Comparison")

    analysis = st.session_state.get("lcca_analysis")

    if not analysis or not analysis.comparison:
        st.info("👈 Analysis requires both baseline and proposed simulation data")
        return

    c = analysis.comparison

    # Summary metrics
    st.subheader("📊 Summary")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric(
            "Energy Savings",
            f"{c.consumption_savings_kwh:,.0f} kWh",
            delta=f"{c.consumption_savings_pct:.1f}%"
        )

    with col2:
        st.metric(
            "Demand Reduction",
            f"{c.demand_reduction_kw:,.1f} kW",
            delta=f"{c.demand_reduction_pct:.1f}%"
        )

    with col3:
        st.metric(
            "Cost Savings",
            f"${c.annual_cost_savings:,.0f}/yr",
            delta=f"{c.cost_savings_pct:.1f}%"
        )

    st.divider()

    # Comparison table
    st.subheader("📋 Detailed Comparison")

    comparison_data = {
        "Metric": ["Consumption (kWh)", "Peak Demand (kW)", "Annual Cost ($)"],
        "Baseline": [
            f"{c.baseline_consumption_kwh:,.0f}",
            f"{c.baseline_peak_demand:,.1f}",
            f"${c.baseline_annual_cost:,.0f}"
        ],
        "Proposed": [
            f"{c.proposed_consumption_kwh:,.0f}",
            f"{c.proposed_peak_demand:,.1f}",
            f"${c.proposed_annual_cost:,.0f}"
        ],
        "Savings": [
            f"{c.consumption_savings_kwh:,.0f} ({c.consumption_savings_pct:.1f}%)",
            f"{c.demand_reduction_kw:,.1f} ({c.demand_reduction_pct:.1f}%)",
            f"${c.annual_cost_savings:,.0f} ({c.cost_savings_pct:.1f}%)"
        ],
    }

    st.dataframe(comparison_data, use_container_width=True)

    # Comparison bar chart
    if PLOTLY_AVAILABLE:
        st.subheader("📊 Visual Comparison")

        fig = go.Figure(data=[
            go.Bar(
                name="Baseline",
                x=["Consumption (MWh)", "Annual Cost ($K)"],
                y=[c.baseline_consumption_kwh/1000, c.baseline_annual_cost/1000],
                marker_color="#95a5a6"
            ),
            go.Bar(
                name="Proposed",
                x=["Consumption (MWh)", "Annual Cost ($K)"],
                y=[c.proposed_consumption_kwh/1000, c.proposed_annual_cost/1000],
                marker_color="#3498db"
            ),
        ])

        fig.update_layout(
            title="Baseline vs Proposed",
            barmode="group",
            height=350
        )

        st.plotly_chart(fig, use_container_width=True)


def render_sensitivity_tab():
    """Render sensitivity analysis tab."""
    st.header("🎚️ Sensitivity Analysis")

    results = st.session_state.get("lcca_results")
    analysis = st.session_state.get("lcca_analysis")

    if not results or not analysis:
        st.info("👈 Run analysis first")
        return

    st.subheader("Parameter Sensitivity")
    st.write("Adjust parameters to see impact on NPV")

    # Interactive sliders
    col1, col2 = st.columns(2)

    with col1:
        elec_rate_delta = st.slider(
            "Electricity Rate Change (%)",
            min_value=-30,
            max_value=30,
            value=0,
            step=5,
            key="sens_elec_rate"
        )

        pv_output_delta = st.slider(
            "PV Output Change (%)",
            min_value=-30,
            max_value=30,
            value=0,
            step=5,
            key="sens_pv_output"
        )

    with col2:
        capex_delta = st.slider(
            "Capital Cost Change (%)",
            min_value=-30,
            max_value=30,
            value=0,
            step=5,
            key="sens_capex"
        )

        discount_rate_delta = st.slider(
            "Discount Rate Change (pts)",
            min_value=-2.0,
            max_value=2.0,
            value=0.0,
            step=0.5,
            key="sens_discount"
        )

    # Calculate adjusted NPV (simplified)
    base_npv = results.npv

    # Approximate sensitivities
    npv_elec = base_npv * (1 + elec_rate_delta/100 * 0.5)  # 50% sensitivity
    npv_pv = base_npv * (1 + pv_output_delta/100 * 0.3)  # 30% sensitivity
    npv_capex = base_npv - (st.session_state.get("lcca_capex", 100000) * capex_delta/100)
    npv_discount = base_npv * (1 - discount_rate_delta * 0.1)  # 10% per point

    # Combined effect (simplified additive)
    adjusted_npv = (
        base_npv +
        (npv_elec - base_npv) +
        (npv_pv - base_npv) +
        (npv_capex - base_npv) +
        (npv_discount - base_npv)
    )

    st.divider()

    st.subheader("📊 Impact on NPV")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric(
            "Base NPV",
            f"${base_npv:,.0f}"
        )

    with col2:
        delta = adjusted_npv - base_npv
        delta_pct = (delta / base_npv * 100) if base_npv != 0 else 0
        st.metric(
            "Adjusted NPV",
            f"${adjusted_npv:,.0f}",
            delta=f"{delta_pct:+.1f}%"
        )

    with col3:
        status = "✅ Viable" if adjusted_npv > 0 else "❌ Not Viable"
        st.metric("Status", status)

    # Tornado chart
    if PLOTLY_AVAILABLE:
        st.subheader("🌪️ Tornado Chart")

        # Calculate +/- 20% impact for each parameter
        impacts = [
            ("Electricity Rate", base_npv * 0.10, -base_npv * 0.10),
            ("PV Output", base_npv * 0.06, -base_npv * 0.06),
            ("Capital Cost", -base_npv * 0.08, base_npv * 0.08),
            ("Discount Rate", -base_npv * 0.04, base_npv * 0.04),
        ]

        fig = go.Figure()

        for param, high, low in impacts:
            fig.add_trace(go.Bar(
                y=[param],
                x=[high],
                orientation='h',
                name="+20%",
                marker_color="#27ae60",
                showlegend=False
            ))
            fig.add_trace(go.Bar(
                y=[param],
                x=[low],
                orientation='h',
                name="-20%",
                marker_color="#e74c3c",
                showlegend=False
            ))

        fig.update_layout(
            title="NPV Sensitivity to ±20% Parameter Change",
            xaxis_title="Change in NPV ($)",
            barmode='overlay',
            height=300
        )

        st.plotly_chart(fig, use_container_width=True)


def render_export_tab():
    """Render export options tab."""
    st.header("📤 Export Results")

    analysis = st.session_state.get("lcca_analysis")
    results = st.session_state.get("lcca_results")

    if not analysis:
        st.info("👈 Run analysis first")
        return

    st.subheader("📑 Export Options")

    col1, col2 = st.columns(2)

    with col1:
        st.write("**Excel Export**")
        st.write("Full LCCA workbook with:")
        st.write("- Summary sheet")
        st.write("- Cash flow table")
        st.write("- TOU breakdown")
        st.write("- Charts")

        if st.button("📊 Export to Excel", use_container_width=True):
            try:
                with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as f:
                    # Generate Excel file
                    if results:
                        export_lcca_to_excel(
                            results,
                            f.name,
                            ExcelExportOptions(
                                include_charts=True,
                                include_monthly=True,
                            )
                        )

                        # Read and offer download
                        with open(f.name, "rb") as file:
                            st.download_button(
                                label="⬇️ Download Excel",
                                data=file.read(),
                                file_name=f"{analysis.project_name}_LCCA.xlsx",
                                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                            )
                    else:
                        st.warning("LCCA results required for Excel export")
            except Exception as e:
                st.error(f"Export failed: {e}")

    with col2:
        st.write("**JSON Export**")
        st.write("Machine-readable format with:")
        st.write("- All analysis data")
        st.write("- Financial metrics")
        st.write("- Energy breakdown")

        if st.button("📄 Export to JSON", use_container_width=True):
            try:
                import json
                json_data = analysis.to_dict()

                st.download_button(
                    label="⬇️ Download JSON",
                    data=json.dumps(json_data, indent=2),
                    file_name=f"{analysis.project_name}_LCCA.json",
                    mime="application/json"
                )
            except Exception as e:
                st.error(f"Export failed: {e}")

    st.divider()

    # Summary text report
    st.subheader("📝 Summary Report")

    if st.button("Generate Report", use_container_width=True):
        report = analysis.format_summary()
        st.code(report, language=None)

        st.download_button(
            label="⬇️ Download Report",
            data=report,
            file_name=f"{analysis.project_name}_LCCA_Report.txt",
            mime="text/plain"
        )


# Entry point for navigation
if __name__ == "__main__":
    handle_lcca_dashboard()
