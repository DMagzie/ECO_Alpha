"""
Site Loads Calculator Page
==========================

Calculate non-modeled site energy loads including:
- Interior lighting (common areas)
- Parking (lighting and ventilation)
- Pool and spa equipment
- Elevators and escalators
- EV charging
- Miscellaneous loads

Features:
- Title 24 LPD values for lighting calculations
- Load shape profiles for TOU analysis
- Modeled load detection to prevent double-counting
- Summary totals and hourly profiles

Author: ECO Tools Team
Version: 7.0.0
Date: December 2024
"""

import streamlit as st
import sys
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass

# Add project root to path
ROOT = Path(__file__).resolve().parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Import site loads modules with error handling
try:
    from eco_tools.lcca.site_loads import (
        # Load shapes
        LoadShapeProfile,
        LoadShapeLibrary,
        # Calculators
        BaseSiteLoadCalculator,
        CalculationResult,
        InteriorLightingCalculator,
        ParkingLightingCalculator,
        ParkingVentilationCalculator,
        SiteLightingCalculator,
        get_title24_lpd,
        TITLE24_LPD,
        PoolPumpCalculator,
        PoolHeaterCalculator,
        SpaCalculator,
        ElevatorCalculator,
        EscalatorCalculator,
        EVChargerCalculator,
        ITTelecomCalculator,
        WaterPumpCalculator,
        TrashCompactorCalculator,
        GenericLoadCalculator,
        # Detectors
        detect_modeled_loads,
    )
    SITE_LOADS_AVAILABLE = True
except ImportError as e:
    SITE_LOADS_AVAILABLE = False
    SITE_LOADS_ERROR = str(e)

# Optional: Plotting
try:
    import plotly.graph_objects as go
    import plotly.express as px
    PLOTLY_AVAILABLE = True
except ImportError:
    PLOTLY_AVAILABLE = False


@dataclass
class LoadEntry:
    """A calculated site load entry."""
    name: str
    category: str
    annual_kwh: float
    annual_therms: float
    peak_kw: float
    method: str
    inputs: Dict


def handle_site_loads():
    """Main site loads calculator page handler."""
    st.title("Site Loads Calculator")
    st.caption("Calculate non-modeled energy loads for complete LCCA analysis")

    if not SITE_LOADS_AVAILABLE:
        st.error(f"Site loads module not available: {SITE_LOADS_ERROR}")
        return

    # Initialize session state
    if "site_loads" not in st.session_state:
        st.session_state.site_loads = []

    # Sidebar
    with st.sidebar:
        st.header("Quick Add")
        render_quick_add_sidebar()

    # Main content tabs
    tabs = st.tabs([
        "Calculator",
        "Lighting",
        "Parking",
        "Pools & Spas",
        "Vertical Transport",
        "Miscellaneous",
        "Summary"
    ])

    with tabs[0]:
        render_overview_tab()

    with tabs[1]:
        render_lighting_tab()

    with tabs[2]:
        render_parking_tab()

    with tabs[3]:
        render_pools_tab()

    with tabs[4]:
        render_transport_tab()

    with tabs[5]:
        render_misc_tab()

    with tabs[6]:
        render_summary_tab()


def render_quick_add_sidebar():
    """Render sidebar for quick load addition."""
    st.subheader("Common Loads")

    # Quick entry for common loads
    quick_loads = {
        "Office Lighting": ("Interior Lighting", 0.75, 10000),
        "Parking Garage": ("Parking", 0.30, 50000),
        "Elevator (6 story)": ("Vertical Transport", None, 6),
        "EV Chargers (10)": ("EV Charging", None, 10),
    }

    for name, (category, lpd, size) in quick_loads.items():
        if st.button(name, use_container_width=True):
            st.info(f"Go to {category} tab to configure {name}")


def render_overview_tab():
    """Render overview and instructions tab."""
    st.header("Site Loads Overview")

    st.markdown("""
    **Site Loads** are energy consumers not typically captured in energy simulation models.
    This calculator helps you account for these loads to ensure accurate LCCA analysis.

    ### Common Site Loads by Building Type

    | Building Type | Typical Site Loads |
    |---------------|-------------------|
    | **Office** | Parking lighting/ventilation, elevators, IT equipment |
    | **Multifamily** | Common area lighting, elevators, pool/spa, EV charging |
    | **Retail** | Site lighting, escalators, refrigeration (display) |
    | **Hotel** | Pool/spa, elevators, laundry, site lighting |
    | **Industrial** | Cranes, process equipment, site lighting |

    ### Workflow

    1. **Add loads** using the category tabs (Lighting, Parking, etc.)
    2. **Review** your load list in the Summary tab
    3. **Export** annual totals and hourly profiles for LCCA integration
    """)

    st.divider()

    # Current loads summary
    st.subheader("Current Load List")

    loads = st.session_state.get("site_loads", [])
    if loads:
        total_kwh = sum(l.annual_kwh for l in loads)
        total_therms = sum(l.annual_therms for l in loads)

        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Loads", len(loads))
        with col2:
            st.metric("Total Electric", f"{total_kwh:,.0f} kWh/yr")
        with col3:
            st.metric("Total Gas", f"{total_therms:,.0f} therms/yr")

        # Quick list
        for load in loads:
            col1, col2, col3 = st.columns([3, 2, 1])
            with col1:
                st.write(f"**{load.name}** ({load.category})")
            with col2:
                st.write(f"{load.annual_kwh:,.0f} kWh")
            with col3:
                if st.button("X", key=f"del_{load.name}"):
                    st.session_state.site_loads.remove(load)
                    st.rerun()
    else:
        st.info("No site loads added yet. Use the category tabs to add loads.")


def render_lighting_tab():
    """Render interior and site lighting calculator tab."""
    st.header("Lighting Loads")

    st.markdown("""
    Calculate lighting loads for areas **not included** in your energy model.
    This typically includes common areas, back-of-house, and site lighting.
    """)

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Interior Lighting")

        space_type = st.selectbox(
            "Space Type",
            list(TITLE24_LPD.keys()),
            help="Select space type for Title 24 LPD lookup"
        )

        lpd = TITLE24_LPD.get(space_type, 0.6)
        st.write(f"**Title 24 LPD:** {lpd} W/SF")

        lpd_override = st.number_input(
            "LPD Override (W/SF)",
            min_value=0.0,
            max_value=5.0,
            value=float(lpd),
            step=0.1,
            help="Override the Title 24 LPD if needed"
        )

        area = st.number_input(
            "Floor Area (SF)",
            min_value=0,
            value=5000,
            step=100
        )

        operating_hours = st.number_input(
            "Annual Operating Hours",
            min_value=0,
            max_value=8760,
            value=4000,
            help="Typical: Office 3000-4000, Retail 4000-5000, 24/7 8760"
        )

        if st.button("Add Interior Lighting", type="primary"):
            # Calculate
            watts = lpd_override * area
            kwh = watts * operating_hours / 1000

            load = LoadEntry(
                name=f"Interior Lighting - {space_type}",
                category="Interior Lighting",
                annual_kwh=kwh,
                annual_therms=0,
                peak_kw=watts / 1000,
                method=f"LPD ({lpd_override} W/SF) x Area ({area:,} SF) x Hours ({operating_hours:,})",
                inputs={"space_type": space_type, "lpd": lpd_override, "area": area, "hours": operating_hours}
            )
            st.session_state.site_loads.append(load)
            st.success(f"Added {load.name}: {kwh:,.0f} kWh/yr")

    with col2:
        st.subheader("Site/Exterior Lighting")

        fixture_count = st.number_input(
            "Number of Fixtures",
            min_value=0,
            value=20
        )

        watts_per_fixture = st.number_input(
            "Watts per Fixture",
            min_value=0,
            value=100,
            help="LED pole lights: 50-100W, HID: 150-400W"
        )

        site_hours = st.number_input(
            "Annual Operating Hours",
            min_value=0,
            max_value=8760,
            value=4380,
            help="Dusk to dawn: ~4380 hrs/yr",
            key="site_hours"
        )

        if st.button("Add Site Lighting", type="primary"):
            watts = fixture_count * watts_per_fixture
            kwh = watts * site_hours / 1000

            load = LoadEntry(
                name="Site/Exterior Lighting",
                category="Site Lighting",
                annual_kwh=kwh,
                annual_therms=0,
                peak_kw=watts / 1000,
                method=f"{fixture_count} fixtures x {watts_per_fixture}W x {site_hours:,} hrs",
                inputs={"fixtures": fixture_count, "watts": watts_per_fixture, "hours": site_hours}
            )
            st.session_state.site_loads.append(load)
            st.success(f"Added {load.name}: {kwh:,.0f} kWh/yr")


def render_parking_tab():
    """Render parking lighting and ventilation calculator tab."""
    st.header("Parking Loads")

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Parking Lighting")

        parking_sf = st.number_input(
            "Parking Area (SF)",
            min_value=0,
            value=50000,
            step=1000
        )

        parking_lpd = st.number_input(
            "Lighting Power Density (W/SF)",
            min_value=0.0,
            max_value=2.0,
            value=0.30,
            step=0.05,
            help="Title 24 max: 0.30 W/SF for parking garages"
        )

        parking_hours = st.number_input(
            "Annual Operating Hours",
            min_value=0,
            max_value=8760,
            value=8760,
            help="Underground parking typically 24/7",
            key="parking_hours"
        )

        if st.button("Add Parking Lighting", type="primary"):
            watts = parking_lpd * parking_sf
            kwh = watts * parking_hours / 1000

            load = LoadEntry(
                name="Parking Garage Lighting",
                category="Parking",
                annual_kwh=kwh,
                annual_therms=0,
                peak_kw=watts / 1000,
                method=f"LPD ({parking_lpd} W/SF) x Area ({parking_sf:,} SF) x Hours ({parking_hours:,})",
                inputs={"area": parking_sf, "lpd": parking_lpd, "hours": parking_hours}
            )
            st.session_state.site_loads.append(load)
            st.success(f"Added {load.name}: {kwh:,.0f} kWh/yr")

    with col2:
        st.subheader("Parking Ventilation")

        vent_parking_sf = st.number_input(
            "Ventilated Parking Area (SF)",
            min_value=0,
            value=50000,
            step=1000,
            key="vent_sf"
        )

        cfm_per_sf = st.number_input(
            "Ventilation Rate (CFM/SF)",
            min_value=0.0,
            max_value=1.0,
            value=0.75,
            step=0.05,
            help="Code minimum: 0.75 CFM/SF for enclosed parking"
        )

        fan_efficacy = st.number_input(
            "Fan Efficacy (W/CFM)",
            min_value=0.0,
            max_value=1.0,
            value=0.25,
            step=0.05,
            help="Good: 0.20, Average: 0.30"
        )

        vent_hours = st.number_input(
            "Annual Operating Hours",
            min_value=0,
            max_value=8760,
            value=8760,
            key="vent_hours"
        )

        if st.button("Add Parking Ventilation", type="primary"):
            cfm = cfm_per_sf * vent_parking_sf
            watts = cfm * fan_efficacy
            kwh = watts * vent_hours / 1000

            load = LoadEntry(
                name="Parking Garage Ventilation",
                category="Parking",
                annual_kwh=kwh,
                annual_therms=0,
                peak_kw=watts / 1000,
                method=f"{cfm:,.0f} CFM x {fan_efficacy} W/CFM x {vent_hours:,} hrs",
                inputs={"area": vent_parking_sf, "cfm_per_sf": cfm_per_sf, "efficacy": fan_efficacy, "hours": vent_hours}
            )
            st.session_state.site_loads.append(load)
            st.success(f"Added {load.name}: {kwh:,.0f} kWh/yr")


def render_pools_tab():
    """Render pool and spa calculator tab."""
    st.header("Pool & Spa Loads")

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Swimming Pool")

        pool_gallons = st.number_input(
            "Pool Volume (gallons)",
            min_value=0,
            value=50000,
            step=5000,
            help="Typical residential: 15,000-25,000 gal, Commercial: 50,000+ gal"
        )

        pump_hp = st.number_input(
            "Pump Horsepower",
            min_value=0.0,
            value=3.0,
            step=0.5,
            help="Typical: 1-3 HP"
        )

        pump_hours = st.number_input(
            "Pump Operating Hours/Day",
            min_value=0,
            max_value=24,
            value=8,
            help="Typical: 6-12 hours/day"
        )

        is_heated = st.checkbox("Pool is heated", value=True)

        if is_heated:
            heating_fuel = st.selectbox(
                "Heating Fuel",
                ["Natural Gas", "Electric Heat Pump", "Electric Resistance"]
            )

            heating_months = st.slider(
                "Heating Season (months)",
                min_value=0,
                max_value=12,
                value=8
            )

        if st.button("Add Pool", type="primary"):
            # Pump energy
            pump_kw = pump_hp * 0.746  # HP to kW
            pump_kwh = pump_kw * pump_hours * 365

            # Heating energy (simplified estimation)
            heating_kwh = 0
            heating_therms = 0
            if is_heated:
                # Estimate based on pool size and heating season
                heating_load_mmbtu = pool_gallons * 8.34 * 20 / 1e6 * heating_months  # ~20F temp rise
                if heating_fuel == "Natural Gas":
                    heating_therms = heating_load_mmbtu * 10 / 0.8  # 80% efficiency
                elif heating_fuel == "Electric Heat Pump":
                    heating_kwh = heating_load_mmbtu * 293 / 4.0  # COP 4.0
                else:
                    heating_kwh = heating_load_mmbtu * 293  # 100% efficiency

            total_kwh = pump_kwh + heating_kwh

            load = LoadEntry(
                name="Swimming Pool",
                category="Pool/Spa",
                annual_kwh=total_kwh,
                annual_therms=heating_therms,
                peak_kw=pump_kw,
                method=f"Pump: {pump_hp} HP x {pump_hours} hrs/day, Heating: {heating_fuel if is_heated else 'None'}",
                inputs={"volume": pool_gallons, "pump_hp": pump_hp, "heated": is_heated}
            )
            st.session_state.site_loads.append(load)
            st.success(f"Added {load.name}: {total_kwh:,.0f} kWh + {heating_therms:,.0f} therms")

    with col2:
        st.subheader("Hot Tub / Spa")

        spa_gallons = st.number_input(
            "Spa Volume (gallons)",
            min_value=0,
            value=500,
            step=100,
            help="Typical: 300-700 gallons"
        )

        spa_fuel = st.selectbox(
            "Heating Fuel",
            ["Natural Gas", "Electric"],
            key="spa_fuel"
        )

        spa_temp = st.slider(
            "Set Temperature (F)",
            min_value=90,
            max_value=104,
            value=102
        )

        if st.button("Add Spa", type="primary"):
            # Simplified spa energy (based on typical ENERGY STAR data)
            # About 2,500-3,500 kWh/yr for typical spa
            if spa_fuel == "Electric":
                spa_kwh = spa_gallons * 5  # ~5 kWh/gal/yr typical
                spa_therms = 0
            else:
                spa_kwh = 500  # Pumps/controls
                spa_therms = spa_gallons * 0.05  # ~0.05 therms/gal/yr typical

            load = LoadEntry(
                name="Hot Tub / Spa",
                category="Pool/Spa",
                annual_kwh=spa_kwh,
                annual_therms=spa_therms,
                peak_kw=6.0 if spa_fuel == "Electric" else 0.5,
                method=f"{spa_gallons} gal spa, {spa_fuel} heated at {spa_temp}F",
                inputs={"volume": spa_gallons, "fuel": spa_fuel, "temp": spa_temp}
            )
            st.session_state.site_loads.append(load)
            st.success(f"Added {load.name}: {spa_kwh:,.0f} kWh + {spa_therms:,.0f} therms")


def render_transport_tab():
    """Render elevator and escalator calculator tab."""
    st.header("Vertical Transport")

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Elevators")

        num_elevators = st.number_input(
            "Number of Elevators",
            min_value=1,
            value=2
        )

        floors = st.number_input(
            "Number of Floors",
            min_value=2,
            value=6
        )

        elevator_type = st.selectbox(
            "Elevator Type",
            ["Hydraulic", "Traction (Geared)", "Traction (Gearless)", "Machine Room-Less (MRL)"]
        )

        building_type = st.selectbox(
            "Building Type",
            ["Office", "Residential", "Hotel", "Retail", "Hospital"],
            key="elev_bldg_type"
        )

        # Elevator energy factors (kWh/floor/year per elevator)
        elev_factors = {
            "Hydraulic": {"Office": 3500, "Residential": 2500, "Hotel": 3000, "Retail": 4000, "Hospital": 5000},
            "Traction (Geared)": {"Office": 2500, "Residential": 1800, "Hotel": 2200, "Retail": 3000, "Hospital": 4000},
            "Traction (Gearless)": {"Office": 2000, "Residential": 1400, "Hotel": 1800, "Retail": 2500, "Hospital": 3500},
            "Machine Room-Less (MRL)": {"Office": 1800, "Residential": 1200, "Hotel": 1600, "Retail": 2200, "Hospital": 3000},
        }

        factor = elev_factors.get(elevator_type, {}).get(building_type, 2500)
        st.write(f"**Energy Factor:** {factor:,} kWh/floor/year")

        if st.button("Add Elevators", type="primary"):
            kwh = num_elevators * floors * factor

            load = LoadEntry(
                name=f"Elevators ({num_elevators}x {floors}-floor)",
                category="Vertical Transport",
                annual_kwh=kwh,
                annual_therms=0,
                peak_kw=num_elevators * 15,  # ~15 kW peak per elevator
                method=f"{num_elevators} x {floors} floors x {factor:,} kWh/floor",
                inputs={"count": num_elevators, "floors": floors, "type": elevator_type}
            )
            st.session_state.site_loads.append(load)
            st.success(f"Added {load.name}: {kwh:,.0f} kWh/yr")

    with col2:
        st.subheader("Escalators")

        num_escalators = st.number_input(
            "Number of Escalators",
            min_value=0,
            value=0
        )

        escalator_length = st.selectbox(
            "Escalator Length",
            ["Short (< 15 ft)", "Standard (15-30 ft)", "Long (> 30 ft)"]
        )

        if num_escalators > 0:
            # Escalator energy (kWh/year per escalator)
            esc_factors = {
                "Short (< 15 ft)": 15000,
                "Standard (15-30 ft)": 25000,
                "Long (> 30 ft)": 40000,
            }

            factor = esc_factors.get(escalator_length, 25000)
            st.write(f"**Energy Factor:** {factor:,} kWh/year each")

            if st.button("Add Escalators", type="primary"):
                kwh = num_escalators * factor

                load = LoadEntry(
                    name=f"Escalators ({num_escalators}x {escalator_length})",
                    category="Vertical Transport",
                    annual_kwh=kwh,
                    annual_therms=0,
                    peak_kw=num_escalators * 8,  # ~8 kW peak per escalator
                    method=f"{num_escalators} x {factor:,} kWh/year",
                    inputs={"count": num_escalators, "length": escalator_length}
                )
                st.session_state.site_loads.append(load)
                st.success(f"Added {load.name}: {kwh:,.0f} kWh/yr")


def render_misc_tab():
    """Render miscellaneous loads calculator tab."""
    st.header("Miscellaneous Loads")

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("EV Charging")

        num_chargers = st.number_input(
            "Number of EV Chargers",
            min_value=0,
            value=10
        )

        charger_kw = st.selectbox(
            "Charger Level",
            ["Level 1 (1.4 kW)", "Level 2 (7.2 kW)", "Level 2 (19.2 kW)", "DC Fast (50 kW)"]
        )

        kw_map = {
            "Level 1 (1.4 kW)": 1.4,
            "Level 2 (7.2 kW)": 7.2,
            "Level 2 (19.2 kW)": 19.2,
            "DC Fast (50 kW)": 50,
        }

        utilization = st.slider(
            "Average Utilization (%)",
            min_value=0,
            max_value=100,
            value=25,
            help="Typical workplace: 15-30%, Public: 10-20%"
        )

        if st.button("Add EV Charging", type="primary") and num_chargers > 0:
            kw = kw_map.get(charger_kw, 7.2)
            kwh = num_chargers * kw * 8760 * (utilization / 100)

            load = LoadEntry(
                name=f"EV Charging ({num_chargers}x {charger_kw.split(' ')[0]})",
                category="EV Charging",
                annual_kwh=kwh,
                annual_therms=0,
                peak_kw=num_chargers * kw,
                method=f"{num_chargers} x {kw} kW x 8760 hrs x {utilization}% utilization",
                inputs={"count": num_chargers, "kw": kw, "utilization": utilization}
            )
            st.session_state.site_loads.append(load)
            st.success(f"Added {load.name}: {kwh:,.0f} kWh/yr")

        st.divider()

        st.subheader("IT/Telecom Equipment")

        it_kw = st.number_input(
            "IT Load (kW)",
            min_value=0.0,
            value=5.0,
            step=0.5,
            help="Server rooms, network equipment, etc."
        )

        if st.button("Add IT/Telecom", type="primary") and it_kw > 0:
            kwh = it_kw * 8760  # 24/7 operation

            load = LoadEntry(
                name="IT/Telecom Equipment",
                category="IT Equipment",
                annual_kwh=kwh,
                annual_therms=0,
                peak_kw=it_kw,
                method=f"{it_kw} kW x 8760 hrs (24/7)",
                inputs={"kw": it_kw}
            )
            st.session_state.site_loads.append(load)
            st.success(f"Added {load.name}: {kwh:,.0f} kWh/yr")

    with col2:
        st.subheader("Domestic Water Pumps")

        pump_hp_water = st.number_input(
            "Total Pump HP",
            min_value=0.0,
            value=5.0,
            step=0.5,
            help="Booster pumps, recirculation pumps",
            key="water_pump_hp"
        )

        pump_hours_water = st.number_input(
            "Operating Hours/Year",
            min_value=0,
            max_value=8760,
            value=4000,
            key="water_pump_hours"
        )

        if st.button("Add Water Pumps", type="primary") and pump_hp_water > 0:
            kw = pump_hp_water * 0.746
            kwh = kw * pump_hours_water

            load = LoadEntry(
                name="Domestic Water Pumps",
                category="Water Systems",
                annual_kwh=kwh,
                annual_therms=0,
                peak_kw=kw,
                method=f"{pump_hp_water} HP x {pump_hours_water:,} hrs/yr",
                inputs={"hp": pump_hp_water, "hours": pump_hours_water}
            )
            st.session_state.site_loads.append(load)
            st.success(f"Added {load.name}: {kwh:,.0f} kWh/yr")

        st.divider()

        st.subheader("Generic Load")

        generic_name = st.text_input("Load Name", "Custom Load")
        generic_kw = st.number_input("Peak Load (kW)", min_value=0.0, value=10.0)
        generic_hours = st.number_input("Operating Hours/Year", min_value=0, max_value=8760, value=3000, key="generic_hours")

        if st.button("Add Generic Load", type="primary") and generic_kw > 0:
            kwh = generic_kw * generic_hours

            load = LoadEntry(
                name=generic_name,
                category="Other",
                annual_kwh=kwh,
                annual_therms=0,
                peak_kw=generic_kw,
                method=f"{generic_kw} kW x {generic_hours:,} hrs/yr",
                inputs={"kw": generic_kw, "hours": generic_hours}
            )
            st.session_state.site_loads.append(load)
            st.success(f"Added {load.name}: {kwh:,.0f} kWh/yr")


def render_summary_tab():
    """Render summary and export tab."""
    st.header("Site Loads Summary")

    loads = st.session_state.get("site_loads", [])

    if not loads:
        st.info("No site loads added. Use the calculator tabs to add loads.")
        return

    # Totals
    total_kwh = sum(l.annual_kwh for l in loads)
    total_therms = sum(l.annual_therms for l in loads)
    total_peak = sum(l.peak_kw for l in loads)

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Total Loads", len(loads))

    with col2:
        st.metric("Annual Electric", f"{total_kwh:,.0f} kWh")

    with col3:
        st.metric("Annual Gas", f"{total_therms:,.0f} therms")

    with col4:
        st.metric("Peak Demand", f"{total_peak:,.1f} kW")

    st.divider()

    # Category breakdown
    if PLOTLY_AVAILABLE:
        col1, col2 = st.columns(2)

        with col1:
            st.subheader("By Category (kWh)")

            categories = {}
            for load in loads:
                cat = load.category
                categories[cat] = categories.get(cat, 0) + load.annual_kwh

            fig = go.Figure(data=[go.Pie(
                labels=list(categories.keys()),
                values=list(categories.values()),
                hole=0.4,
            )])
            fig.update_layout(height=350, margin=dict(t=20, b=20, l=20, r=20))
            st.plotly_chart(fig, use_container_width=True)

        with col2:
            st.subheader("Load Breakdown")

            # Bar chart
            names = [l.name for l in loads]
            kwhs = [l.annual_kwh for l in loads]

            fig = go.Figure(data=[go.Bar(
                x=kwhs,
                y=names,
                orientation='h',
                marker_color='#3498db'
            )])
            fig.update_layout(
                height=350,
                yaxis=dict(autorange="reversed"),
                xaxis_title="Annual kWh",
                margin=dict(t=20, b=50, l=150, r=20)
            )
            st.plotly_chart(fig, use_container_width=True)

    st.divider()

    # Detailed table
    st.subheader("Detailed Load List")

    table_data = []
    for load in loads:
        table_data.append({
            "Name": load.name,
            "Category": load.category,
            "Annual kWh": f"{load.annual_kwh:,.0f}",
            "Annual Therms": f"{load.annual_therms:,.0f}",
            "Peak kW": f"{load.peak_kw:,.1f}",
            "Method": load.method,
        })

    st.dataframe(table_data, use_container_width=True, hide_index=True)

    st.divider()

    # Export options
    st.subheader("Export")

    col1, col2 = st.columns(2)

    with col1:
        if st.button("Export to CSV", use_container_width=True):
            import csv
            import io

            output = io.StringIO()
            writer = csv.writer(output)
            writer.writerow(["Name", "Category", "Annual kWh", "Annual Therms", "Peak kW", "Method"])
            for load in loads:
                writer.writerow([load.name, load.category, load.annual_kwh, load.annual_therms, load.peak_kw, load.method])
            writer.writerow([])
            writer.writerow(["TOTAL", "", total_kwh, total_therms, total_peak, ""])

            st.download_button(
                "Download CSV",
                data=output.getvalue(),
                file_name="site_loads.csv",
                mime="text/csv"
            )

    with col2:
        if st.button("Clear All Loads", use_container_width=True):
            st.session_state.site_loads = []
            st.rerun()


# Entry point for navigation
if __name__ == "__main__":
    handle_site_loads()
