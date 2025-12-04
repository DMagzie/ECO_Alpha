"""
Central HPWH Tank Sizing Widget for ECO Tools GUI

Streamlit component for sizing central heat pump water heater systems
integrated into the Utilities page.
"""

import streamlit as st
import json
from typing import Optional

from eco_tools.sizing import (
    CentralHPWHSizer,
    BuildingProfile,
    HPWHSystemConfig,
    HPWHCompressorType,
    TankConfiguration,
    size_from_dwelling_units,
    create_sizing_report,
)


def render_hpwh_sizer():
    """Render the Central HPWH sizing widget."""

    st.header("🌡️ Central HPWH Tank Sizing Tool")

    st.markdown("""
    Size central heat pump water heater systems for multifamily buildings per **Title 24 2025** standards.

    - ✅ Code-compliant minimum sizing
    - ✅ Load shifting optimization for NEM3/LSC
    - ✅ Thermal storage calculations
    - ✅ CIBD25 model export
    """)

    # Create tabs for different input methods
    input_tab, advanced_tab, results_tab = st.tabs(["Basic Inputs", "Advanced Options", "Results"])

    with input_tab:
        st.subheader("Building Parameters")

        col1, col2 = st.columns(2)

        with col1:
            num_units = st.number_input(
                "Number of Dwelling Units",
                min_value=1,
                max_value=500,
                value=30,
                step=1,
                help="Total number of dwelling units in the building"
            )

            avg_bedrooms = st.number_input(
                "Average Bedrooms per Unit",
                min_value=0.0,
                max_value=5.0,
                value=2.0,
                step=0.5,
                help="Average number of bedrooms per dwelling unit"
            )

            total_bedrooms = int(num_units * avg_bedrooms)
            st.info(f"📊 Total Bedrooms: **{total_bedrooms}**")

        with col2:
            climate_zone = st.selectbox(
                "California Climate Zone",
                options=[str(i) for i in range(1, 17)],
                index=11,  # Default to CZ12
                help="California Title 24 climate zone (1-16)"
            )

            common_area_equiv = st.number_input(
                "Common Area DU Equivalent",
                min_value=0.0,
                max_value=50.0,
                value=0.0,
                step=0.5,
                help="Common area DHW load expressed as equivalent dwelling units"
            )

        st.divider()

        st.subheader("Optimization Strategy")

        optimization_preset = st.radio(
            "Optimization Preset",
            options=["Code Minimum Only", "Moderate Load Shifting", "Aggressive Optimization"],
            index=1,
            horizontal=True,
            help="Select sizing strategy"
        )

        if optimization_preset == "Code Minimum Only":
            enable_load_shift = False
            oversize_factor = 1.0
            st.info("💡 Using Title 24 code-minimum sizing formula only")

        elif optimization_preset == "Moderate Load Shifting":
            enable_load_shift = True
            oversize_factor = 1.25
            st.success("✨ Optimizing for load shifting with 25% tank oversizing")

        else:  # Aggressive
            enable_load_shift = True
            oversize_factor = 1.5
            st.success("🚀 Aggressive optimization with 50% tank oversizing")

    with advanced_tab:
        st.subheader("Advanced Configuration")

        col1, col2 = st.columns(2)

        with col1:
            st.markdown("**Load Shifting Parameters**")

            charge_start = st.slider(
                "Charge Start Hour",
                min_value=0,
                max_value=23,
                value=11,
                help="Hour to begin heating (24-hour format). Default: 11 = noon"
            )

            charge_end = st.slider(
                "Charge End Hour",
                min_value=0,
                max_value=23,
                value=17,
                help="Hour to stop heating (24-hour format). Default: 17 = 5pm"
            )

            charge_window = charge_end - charge_start if charge_end > charge_start else 0
            st.caption(f"⏱️ Charge Window: {charge_window} hours")

        with col2:
            st.markdown("**System Configuration**")

            compressor_type = st.selectbox(
                "Compressor Type",
                options=[
                    "Small NEEA (4.5 kW)",
                    "Commercial Moderate (10 kW)",
                    "Commercial Large (20 kW)",
                    "Integrated Packaged (15 kW)"
                ],
                index=0,
                help="HPWH compressor type and capacity"
            )

            tank_setpoint = st.number_input(
                "Tank Setpoint (°F)",
                min_value=120.0,
                max_value=180.0,
                value=140.0,
                step=5.0,
                help="Storage tank setpoint temperature. Higher = more thermal storage"
            )

            tank_r_value = st.number_input(
                "Tank R-Value",
                min_value=10.0,
                max_value=30.0,
                value=16.0,
                step=1.0,
                help="Tank insulation R-value. Minimum: 12.5 (2025 code)"
            )

            compressor_cop = st.number_input(
                "Compressor COP",
                min_value=2.0,
                max_value=4.5,
                value=3.0,
                step=0.1,
                help="Heat pump coefficient of performance"
            )

    # Map compressor type selection
    compressor_type_map = {
        "Small NEEA (4.5 kW)": HPWHCompressorType.SMALL_NEEA,
        "Commercial Moderate (10 kW)": HPWHCompressorType.COMMERCIAL_MODERATE,
        "Commercial Large (20 kW)": HPWHCompressorType.COMMERCIAL_LARGE,
        "Integrated Packaged (15 kW)": HPWHCompressorType.INTEGRATED_PACKAGED,
    }
    selected_compressor = compressor_type_map[compressor_type]

    # Calculate button
    if st.button("🔢 Calculate Tank Sizing", type="primary", use_container_width=True):
        with st.spinner("Calculating optimal HPWH system size..."):
            # Create building profile
            building = BuildingProfile(
                num_dwelling_units=num_units,
                total_bedrooms=total_bedrooms,
                common_area_du_equiv=common_area_equiv,
                climate_zone=climate_zone
            )

            # Create system configuration
            config = HPWHSystemConfig(
                compressor_type=selected_compressor,
                enable_load_shifting=enable_load_shift,
                oversizing_factor=oversize_factor,
                charge_start_hour=charge_start,
                charge_end_hour=charge_end,
                tank_setpoint_f=tank_setpoint,
                tank_r_value=tank_r_value,
                compressor_cop=compressor_cop
            )

            # Perform sizing
            results = CentralHPWHSizer.size_central_hpwh(building, config)

            # Store results in session state
            st.session_state['hpwh_results'] = results
            st.session_state['hpwh_building'] = building
            st.session_state['hpwh_config'] = config

            st.success("✅ Sizing calculation complete!")

    # Display results if available
    if 'hpwh_results' in st.session_state:
        with results_tab:
            results = st.session_state['hpwh_results']

            st.subheader("📊 Sizing Results")

            # Key metrics in columns
            col1, col2, col3, col4 = st.columns(4)

            with col1:
                st.metric(
                    "Final Tank Volume",
                    f"{results.final_tank_volume_gal:,.0f} gal",
                    delta=f"+{results.load_shifting_benefit_pct:.0f}% vs minimum"
                )

            with col2:
                st.metric(
                    "Number of Tanks",
                    results.num_tanks,
                    delta=f"{results.volume_per_tank_gal:,.0f} gal each" if results.num_tanks > 1 else None
                )

            with col3:
                st.metric(
                    "Compressors",
                    results.num_compressors,
                    delta=f"{results.compressor_capacity_kw:.1f} kW each"
                )

            with col4:
                st.metric(
                    "Evening Coverage",
                    f"{results.evening_peak_hours_covered:.1f} hrs",
                    delta="No HPWH operation"
                )

            st.divider()

            # Detailed results in expanders
            with st.expander("🏗️ Tank Sizing Details", expanded=True):
                col1, col2 = st.columns(2)

                with col1:
                    st.markdown("**Sizing Progression:**")
                    st.write(f"• Code Minimum: {results.minimum_tank_volume_gal:,.0f} gallons")
                    st.write(f"• Recommended: {results.recommended_tank_volume_gal:,.0f} gallons")
                    st.write(f"• Final (Rounded): {results.final_tank_volume_gal:,.0f} gallons")

                with col2:
                    st.markdown("**Configuration:**")
                    st.write(f"• Number of Tanks: {results.num_tanks}")
                    st.write(f"• Volume per Tank: {results.volume_per_tank_gal:,.0f} gallons")
                    st.write(f"• Tank R-Value: {tank_r_value:.1f}")

            with st.expander("⚡ Compressor & Performance"):
                col1, col2 = st.columns(2)

                with col1:
                    st.markdown("**Compressor Array:**")
                    st.write(f"• Number: {results.num_compressors}")
                    st.write(f"• Capacity Each: {results.compressor_capacity_kw:.1f} kW")
                    st.write(f"• Total Heating: {results.total_heating_capacity_kw:.1f} kW")
                    st.write(f"  ({results.total_heating_capacity_btu:,.0f} BTU/h)")

                with col2:
                    st.markdown("**Performance Metrics:**")
                    st.write(f"• Recovery Rate: {results.recovery_rate_gph:.1f} gal/hour")
                    st.write(f"• First Hour Rating: {results.first_hour_rating_gal:,.0f} gal")
                    st.write(f"• Peak Hour Capacity: {results.peak_hour_capacity_gal:,.0f} gal")

            with st.expander("🔋 Thermal Storage & Load Shifting"):
                col1, col2 = st.columns(2)

                with col1:
                    st.markdown("**Thermal Storage:**")
                    st.write(f"• Storage Capacity: {results.thermal_storage_capacity_btu:,.0f} BTU")
                    st.write(f"• Temperature Rise: {tank_setpoint - 80:.0f}°F")
                    st.write(f"• Storage Efficiency: High (R-{tank_r_value:.1f})")

                with col2:
                    st.markdown("**Load Shifting Benefit:**")
                    st.write(f"• Evening Peak Coverage: {results.evening_peak_hours_covered:.1f} hours")
                    st.write(f"• Benefit vs Minimum: {results.load_shifting_benefit_pct:.1f}%")
                    st.write(f"• Charge Window: {charge_start}:00 - {charge_end}:00")

            # Optimization notes
            if results.optimization_notes:
                with st.expander("📝 Optimization Notes"):
                    for note in results.optimization_notes:
                        st.info(note)

            st.divider()

            # Export options
            st.subheader("💾 Export Results")

            col1, col2, col3 = st.columns(3)

            with col1:
                # Text report export
                report = create_sizing_report(results)
                st.download_button(
                    label="📄 Download Report (Text)",
                    data=report,
                    file_name=f"hpwh_sizing_{num_units}units.txt",
                    mime="text/plain",
                    use_container_width=True
                )

            with col2:
                # JSON export
                json_data = {
                    "building": {
                        "num_dwelling_units": num_units,
                        "total_bedrooms": total_bedrooms,
                        "climate_zone": climate_zone,
                    },
                    "results": {
                        "final_tank_volume_gal": results.final_tank_volume_gal,
                        "num_tanks": results.num_tanks,
                        "num_compressors": results.num_compressors,
                        "compressor_capacity_kw": results.compressor_capacity_kw,
                        "thermal_storage_btu": results.thermal_storage_capacity_btu,
                        "evening_coverage_hours": results.evening_peak_hours_covered,
                    }
                }
                st.download_button(
                    label="📦 Download JSON",
                    data=json.dumps(json_data, indent=2),
                    file_name=f"hpwh_sizing_{num_units}units.json",
                    mime="application/json",
                    use_container_width=True
                )

            with col3:
                # CIBD25 export
                cibd25_dict = CentralHPWHSizer.export_to_cibd25_dict(results)
                st.download_button(
                    label="🏗️ CIBD25 Properties",
                    data=json.dumps(cibd25_dict, indent=2),
                    file_name=f"hpwh_cibd25_{num_units}units.json",
                    mime="application/json",
                    use_container_width=True
                )

            # Display CIBD25 properties
            with st.expander("🏗️ CIBD25 Properties Preview"):
                st.json(cibd25_dict)


if __name__ == "__main__":
    # For standalone testing
    st.set_page_config(
        page_title="Central HPWH Sizer",
        page_icon="🌡️",
        layout="wide"
    )
    render_hpwh_sizer()
