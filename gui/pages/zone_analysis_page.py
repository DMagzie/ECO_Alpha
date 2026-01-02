"""
Zone-Level LCCA Analysis Page
==============================

Interactive zone-level cost analysis for multifamily and mixed-use buildings.

Features:
- Per-zone energy and cost breakdown
- Dwelling unit analysis by bedroom count
- Common area categorization
- CUAC utility allowance calculations
- Zone performance ranking
- Excel/PDF export

Author: ECO Tools Team
Version: 7.0.0
Date: December 2024
"""

import streamlit as st
import sys
from pathlib import Path
from typing import Dict, Any, Optional, List
import tempfile

# Add project root to path
ROOT = Path(__file__).resolve().parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Import zone-level LCCA modules with error handling
try:
    from eco_tools.lcca import (
        # Auto-discovery
        discover_simulation_outputs,
        DiscoveredOutputs,
        # Tariffs
        TouTariff,
        get_tariff_by_name,
        list_available_tariffs,
        # Core LCCA
        ScenarioAssumptions,
    )
    from eco_tools.lcca.zone_energy import (
        ZoneEnergySummary,
        ZoneLccaResult,
        BuildingZoneLccaSummary,
        DwellingUnitSummary,
        CommonAreaSummary,
        CuacAllowanceResult,
    )
    from eco_tools.lcca.cuac.models import ZoneType
    from eco_tools.lcca.zone_allocation import (
        ZoneCostAllocator,
        AllocationMethod,
        calculate_zone_lcca,
    )
    from eco_tools.lcca.zone_report import (
        ZoneLccaReport,
        generate_zone_lcca_report,
        format_zone_report,
        format_cuac_allowance_table,
        format_zone_detail_table,
        get_excel_sheets_data,
    )
    from eco_tools.lcca.cuac.models import CuacConfig, DwellUnitAllocation
    from eco_tools.lcca.res_other.models import CommonAreaCategory
    from eco_tools.lcca.ca_hi_helpers import (
        get_region_from_climate_zone,
        get_default_rate_id,
        CZ_TO_REGION,
    )
    ZONE_LCCA_AVAILABLE = True
except ImportError as e:
    ZONE_LCCA_AVAILABLE = False
    ZONE_IMPORT_ERROR = str(e)

# Optional: Plotting
try:
    import plotly.graph_objects as go
    import plotly.express as px
    PLOTLY_AVAILABLE = True
except ImportError:
    PLOTLY_AVAILABLE = False


def handle_zone_analysis():
    """Main zone analysis page handler."""
    st.title("Zone-Level LCCA Analysis")
    st.caption("Per-unit and per-zone cost analysis for multifamily and mixed-use buildings")

    if not ZONE_LCCA_AVAILABLE:
        st.error(f"Zone LCCA module not available: {ZONE_IMPORT_ERROR}")
        return

    # Initialize session state
    if "zone_data" not in st.session_state:
        st.session_state.zone_data = None
    if "zone_report" not in st.session_state:
        st.session_state.zone_report = None

    # Sidebar configuration
    with st.sidebar:
        st.header("Zone Analysis Settings")
        render_zone_sidebar()

    # Main content tabs
    tabs = st.tabs([
        "Zone Setup",
        "Cost Breakdown",
        "Dwelling Units",
        "Common Areas",
        "CUAC Allowances",
        "Performance Ranking",
        "Export"
    ])

    with tabs[0]:
        render_zone_setup_tab()

    with tabs[1]:
        render_cost_breakdown_tab()

    with tabs[2]:
        render_dwelling_units_tab()

    with tabs[3]:
        render_common_areas_tab()

    with tabs[4]:
        render_cuac_tab()

    with tabs[5]:
        render_ranking_tab()

    with tabs[6]:
        render_zone_export_tab()


def render_zone_sidebar():
    """Render sidebar configuration for zone analysis."""

    # Tariff selection
    st.subheader("Utility Rate")

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
        "Rate Schedule",
        tariff_options,
        index=0,
        key="zone_tariff_select"
    )
    st.session_state.zone_tariff_id = selected_tariff

    tariff = get_tariff_by_name(selected_tariff)
    if tariff:
        with st.expander("Rate Details"):
            st.write(f"**Utility:** {tariff.utility}")
            st.write(f"**On-Peak:** ${tariff.energy_rates.summer_on_peak:.4f}/kWh")
            st.write(f"**Off-Peak:** ${tariff.energy_rates.summer_off_peak:.4f}/kWh")
            if tariff.gas_rate:
                st.write(f"**Gas:** ${tariff.gas_rate:.3f}/therm")

    st.divider()

    # Allocation method
    st.subheader("Allocation Method")

    allocation_methods = {
        "By Area": AllocationMethod.BY_AREA,
        "By Consumption": AllocationMethod.BY_CONSUMPTION,
        "By Unit Count": AllocationMethod.BY_UNIT_COUNT,
        "By Bedroom": AllocationMethod.BY_BEDROOM,
    }

    selected_method = st.selectbox(
        "Common Area Allocation",
        list(allocation_methods.keys()),
        index=0,
        help="How to allocate common area costs to dwelling units"
    )
    st.session_state.zone_allocation_method = allocation_methods[selected_method]

    st.divider()

    # CUAC settings
    st.subheader("CUAC Settings")

    enable_cuac = st.checkbox(
        "Enable CUAC Analysis",
        value=False,
        help="Calculate utility allowances for affordable housing"
    )
    st.session_state.zone_enable_cuac = enable_cuac

    if enable_cuac:
        pv_billing = st.selectbox(
            "PV Billing Option",
            ["NEM 2.0", "NEM 3.0", "V-NBT", "None"],
            help="Solar billing arrangement"
        )
        st.session_state.zone_pv_billing = pv_billing

    st.divider()

    # V-NBT mode (for imported data with PV)
    st.subheader("Rate Analysis Mode")

    enable_vnbt = st.checkbox(
        "Enable V-NBT Analysis",
        value=False,
        help="Calculate zone costs with Virtual Net Billing Tariff (requires PV data)"
    )
    st.session_state.zone_enable_vnbt = enable_vnbt

    if enable_vnbt:
        st.info("V-NBT allocates PV generation to zones proportionally")


def render_zone_setup_tab():
    """Render zone setup and data entry tab."""
    st.header("Zone Configuration")

    # Two options: manual entry or import from file
    setup_mode = st.radio(
        "Setup Mode",
        ["Manual Entry", "Import from Project"],
        horizontal=True
    )

    if setup_mode == "Manual Entry":
        render_manual_zone_entry()
    else:
        render_project_import()


def render_manual_zone_entry():
    """Render manual zone data entry form."""
    st.subheader("Building Information")

    col1, col2 = st.columns(2)

    with col1:
        building_name = st.text_input("Building Name", "Mixed-Use Building")
        building_type = st.selectbox(
            "Building Type",
            ["Multifamily", "Mixed-Use", "Single-Family Attached"]
        )

    with col2:
        climate_zone = st.selectbox(
            "Climate Zone",
            [f"CZ{i}" for i in range(1, 17)],
            index=11  # CZ12 default
        )
        total_units = st.number_input("Total Dwelling Units", min_value=1, value=10)

    st.divider()
    st.subheader("Zone Data Entry")

    # Show example table for zone entry
    st.info("Enter zone data below. Each row represents one zone type.")

    # Create editable dataframe for zone entry
    default_zones = [
        {"zone_name": "Unit_1BR", "zone_type": "Dwelling", "bedrooms": 1, "area_sqft": 650, "count": 4, "elec_kwh": 4500, "gas_therm": 150},
        {"zone_name": "Unit_2BR", "zone_type": "Dwelling", "bedrooms": 2, "area_sqft": 900, "count": 4, "elec_kwh": 5500, "gas_therm": 180},
        {"zone_name": "Unit_3BR", "zone_type": "Dwelling", "bedrooms": 3, "area_sqft": 1200, "count": 2, "elec_kwh": 6500, "gas_therm": 220},
        {"zone_name": "Corridor", "zone_type": "Common", "bedrooms": 0, "area_sqft": 1500, "count": 1, "elec_kwh": 8000, "gas_therm": 0},
        {"zone_name": "Lobby", "zone_type": "Common", "bedrooms": 0, "area_sqft": 800, "count": 1, "elec_kwh": 5000, "gas_therm": 50},
    ]

    # Use session state to persist edits
    if "zone_table_data" not in st.session_state:
        st.session_state.zone_table_data = default_zones

    edited_data = st.data_editor(
        st.session_state.zone_table_data,
        num_rows="dynamic",
        use_container_width=True,
        column_config={
            "zone_name": st.column_config.TextColumn("Zone Name", width="medium"),
            "zone_type": st.column_config.SelectboxColumn("Type", options=["Dwelling", "Common"], width="small"),
            "bedrooms": st.column_config.NumberColumn("BR", min_value=0, max_value=5, width="small"),
            "area_sqft": st.column_config.NumberColumn("Area (sqft)", min_value=0, format="%d"),
            "count": st.column_config.NumberColumn("Count", min_value=1, width="small"),
            "elec_kwh": st.column_config.NumberColumn("Elec (kWh/yr)", min_value=0, format="%d"),
            "gas_therm": st.column_config.NumberColumn("Gas (therm/yr)", min_value=0, format="%d"),
        },
        key="zone_editor"
    )

    st.session_state.zone_table_data = edited_data

    st.divider()

    # PV/Battery allocations
    st.subheader("PV/Battery System (Optional)")

    col1, col2 = st.columns(2)

    with col1:
        total_pv_kw = st.number_input("Total PV System (kWdc)", min_value=0.0, value=0.0, step=1.0)
        pv_annual_kwh = st.number_input("Annual PV Generation (kWh)", min_value=0.0, value=total_pv_kw * 1500, step=100.0)

    with col2:
        total_battery_kwh = st.number_input("Battery Capacity (kWh)", min_value=0.0, value=0.0, step=1.0)
        battery_kw = st.number_input("Battery Power (kW)", min_value=0.0, value=total_battery_kwh * 0.25, step=0.5)

    st.session_state.zone_pv_kw = total_pv_kw
    st.session_state.zone_pv_kwh = pv_annual_kwh
    st.session_state.zone_battery_kwh = total_battery_kwh
    st.session_state.zone_battery_kw = battery_kw

    st.divider()

    # Calculate button
    if st.button("Calculate Zone LCCA", type="primary", use_container_width=True):
        with st.spinner("Calculating zone costs..."):
            try:
                # Convert table data to zone summaries
                zone_summaries = convert_table_to_summaries(edited_data)

                # Get tariff
                tariff = get_tariff_by_name(st.session_state.get("zone_tariff_id", "PG&E B-20"))

                # Create CUAC config if enabled
                cuac_config = None
                if st.session_state.get("zone_enable_cuac", False):
                    cuac_config = CuacConfig(
                        affordable_pv_dc_sys_size=total_pv_kw,
                        affordable_batt_max_cap=total_battery_kwh,
                        pv_billing_option=st.session_state.get("zone_pv_billing", "NEM 2.0"),
                    )

                # Generate report
                report = generate_zone_lcca_report(
                    zone_summaries=zone_summaries,
                    tariff=tariff,
                    building_name=building_name,
                    building_type=building_type,
                    climate_zone=climate_zone,
                    cuac_config=cuac_config,
                )

                st.session_state.zone_report = report
                st.session_state.zone_data = zone_summaries

                st.success("Zone LCCA calculated successfully!")
                st.balloons()

            except Exception as e:
                st.error(f"Calculation failed: {e}")


def convert_table_to_summaries(table_data: List[Dict]) -> List[ZoneEnergySummary]:
    """Convert table data to ZoneEnergySummary objects."""
    summaries = []

    for row in table_data:
        zone_type = ZoneType.DWELLING_UNIT if row.get("zone_type") == "Dwelling" else ZoneType.COMMON_AREA

        # Determine common area category
        category = None
        if zone_type == ZoneType.COMMON_AREA:
            zone_name_lower = row.get("zone_name", "").lower()
            if "corridor" in zone_name_lower or "hallway" in zone_name_lower:
                category = CommonAreaCategory.CORRIDOR
            elif "lobby" in zone_name_lower:
                category = CommonAreaCategory.LOBBY
            elif "parking" in zone_name_lower or "garage" in zone_name_lower:
                category = CommonAreaCategory.PARKING
            elif "laundry" in zone_name_lower:
                category = CommonAreaCategory.LAUNDRY
            elif "office" in zone_name_lower or "leasing" in zone_name_lower:
                category = CommonAreaCategory.OFFICE
            else:
                category = CommonAreaCategory.OTHER

        # Create summary for each unit (respecting count/multiplier)
        count = row.get("count", 1)
        for i in range(count):
            suffix = f"_{i+1}" if count > 1 else ""
            summary = ZoneEnergySummary(
                zone_name=f"{row.get('zone_name', 'Zone')}{suffix}",
                zone_type=zone_type,
                category=category,
                area_sqft=row.get("area_sqft", 0),
                num_bedrooms=row.get("bedrooms", 0) if zone_type == ZoneType.DWELLING_UNIT else 0,
                multiplier=1,  # Already expanded
                elec_kwh=row.get("elec_kwh", 0),
                gas_therm=row.get("gas_therm", 0),
            )
            summaries.append(summary)

    return summaries


def render_project_import():
    """Render project import section."""
    st.subheader("Import from Simulation Project")

    project_path = st.text_input(
        "Project Run Folder",
        placeholder="/path/to/project - run",
        help="Path to a CBECC simulation run folder with zone-level outputs"
    )

    if st.button("Discover & Import Zone Data", type="primary"):
        if project_path:
            with st.spinner("Parsing zone data from CSE output..."):
                try:
                    import csv
                    from eco_tools.lcca.zone_energy import create_zone_energy_from_hourly

                    run_dir = Path(project_path)
                    if not run_dir.exists():
                        st.error("Path does not exist")
                        return

                    # Find CSE output file
                    cse_csv = None
                    for pattern in ["*-AP-CSE.CSV", "*- AP-CSE.CSV", "*AP-CSE.csv"]:
                        matches = list(run_dir.glob(pattern))
                        if matches:
                            cse_csv = matches[0]
                            break

                    if not cse_csv:
                        # Try run subdirectory
                        run_subdir = list(run_dir.glob("* - run"))
                        if run_subdir:
                            for pattern in ["*-AP-CSE.CSV", "*- AP-CSE.CSV", "*AP-CSE.csv"]:
                                matches = list(run_subdir[0].glob(pattern))
                                if matches:
                                    cse_csv = matches[0]
                                    break

                    if not cse_csv:
                        st.error("CSE output file (*-AP-CSE.CSV) not found in project folder")
                        return

                    st.info(f"Parsing: {cse_csv.name}")

                    # Parse CSE output - electric and gas meters
                    meters = {}
                    gas_meters = {}
                    building_pv_hourly = []

                    with open(cse_csv, 'r', encoding='latin-1') as f:
                        reader = csv.reader(f)
                        for _ in range(4):
                            next(reader)

                        for row in reader:
                            if len(row) < 6:
                                continue
                            meter_name = row[0].strip('"')
                            if not meter_name or meter_name in ('Meter', ''):
                                continue

                            # Detect gas meters
                            is_gas_meter = meter_name.startswith('MtrGas') or meter_name.startswith('MtrNatGas')

                            try:
                                if is_gas_meter:
                                    # Gas meter: Tot column in kBtu, convert to therms
                                    total_kbtu = float(row[5]) if row[5] else 0.0
                                    total_therm = total_kbtu / 100.0  # 100 kBtu = 1 therm

                                    if meter_name not in gas_meters:
                                        gas_meters[meter_name] = {'hourly_therm': []}
                                    gas_meters[meter_name]['hourly_therm'].append(total_therm)
                                else:
                                    # Electric meter
                                    total_kwh = float(row[5]) if row[5] else 0.0
                                    pv_kwh = abs(float(row[29])) if len(row) > 29 and row[29] else 0.0

                                    if meter_name not in meters:
                                        meters[meter_name] = {'hourly_kwh': [], 'hourly_pv': []}
                                    meters[meter_name]['hourly_kwh'].append(total_kwh)
                                    meters[meter_name]['hourly_pv'].append(pv_kwh)

                                    if meter_name == 'MtrElec':
                                        building_pv_hourly.append(pv_kwh)
                            except (ValueError, IndexError):
                                continue

                    # Map electric meters to zones
                    meter_to_zone = {
                        'MtrElec_1bedrm': ('1BR Dwelling Units', ZoneType.DWELLING_UNIT, 1),
                        'MtrElec_2bedrm': ('2BR Dwelling Units', ZoneType.DWELLING_UNIT, 2),
                        'MtrElec_3bedrm': ('3BR Dwelling Units', ZoneType.DWELLING_UNIT, 3),
                        'MtrElec2': ('Common Areas', ZoneType.COMMON_AREA, 0),
                    }

                    # Map gas meters to zones (parallel naming)
                    gas_meter_to_zone = {
                        'MtrGas_1bedrm': '1BR Dwelling Units',
                        'MtrGas_2bedrm': '2BR Dwelling Units',
                        'MtrGas_3bedrm': '3BR Dwelling Units',
                        'MtrGas2': 'Common Areas',
                        'MtrNatGas': 'Building Total',
                    }

                    # Collect gas data by zone name
                    zone_gas_data = {}
                    for gas_meter_name, gas_data in gas_meters.items():
                        zone_name = gas_meter_to_zone.get(gas_meter_name)
                        if zone_name and len(gas_data['hourly_therm']) == 8760:
                            zone_gas_data[zone_name] = gas_data['hourly_therm']

                    zone_summaries = []
                    for meter_name, data in meters.items():
                        if meter_name not in meter_to_zone:
                            continue
                        zone_name, zone_type, bedrooms = meter_to_zone[meter_name]
                        if len(data['hourly_kwh']) != 8760:
                            st.warning(f"{meter_name} has {len(data['hourly_kwh'])} hours, expected 8760")
                            continue

                        # Get corresponding gas data if available
                        hourly_gas = zone_gas_data.get(zone_name)

                        summary = create_zone_energy_from_hourly(
                            zone_name=zone_name,
                            zone_type=zone_type,
                            hourly_elec=data['hourly_kwh'],
                            hourly_gas=hourly_gas,
                            num_bedrooms=bedrooms,
                        )
                        zone_summaries.append(summary)

                    if not zone_summaries:
                        st.error("No zone data found in CSE output")
                        return

                    # Calculate total gas for building
                    building_gas_therm = 0.0
                    if 'MtrNatGas' in gas_meters and len(gas_meters['MtrNatGas']['hourly_therm']) == 8760:
                        building_gas_therm = sum(gas_meters['MtrNatGas']['hourly_therm'])
                    elif gas_meters:
                        for gas_data in gas_meters.values():
                            if len(gas_data['hourly_therm']) == 8760:
                                building_gas_therm += sum(gas_data['hourly_therm'])

                    has_gas_data = building_gas_therm > 0 or any(z.gas_therm > 0 for z in zone_summaries)

                    # Store data in session state
                    st.session_state.zone_data = zone_summaries
                    st.session_state.zone_pv_hourly = building_pv_hourly
                    st.session_state.zone_project_path = str(run_dir)
                    st.session_state.zone_has_gas = has_gas_data
                    st.session_state.zone_building_gas = building_gas_therm

                    st.success(f"Imported {len(zone_summaries)} zones with 8760 hourly data!")

                    # Show summary
                    for zone in zone_summaries:
                        if zone.gas_therm and zone.gas_therm > 0:
                            st.write(f"  - **{zone.zone_name}**: {zone.elec_kwh:,.0f} kWh, {zone.gas_therm:,.0f} therm/yr")
                        else:
                            st.write(f"  - **{zone.zone_name}**: {zone.elec_kwh:,.0f} kWh/yr")

                    if building_pv_hourly and sum(building_pv_hourly) > 0:
                        total_pv = sum(building_pv_hourly)
                        st.write(f"  - **Building PV**: {total_pv:,.0f} kWh/yr")

                    if has_gas_data:
                        st.write(f"  - **Building Gas**: {building_gas_therm:,.0f} therm/yr")

                except Exception as e:
                    st.error(f"Import failed: {e}")
                    import traceback
                    st.code(traceback.format_exc())
        else:
            st.warning("Please enter a project path")

    # Show imported data status
    if st.session_state.get("zone_data"):
        st.divider()
        st.success(f"Zones loaded: {len(st.session_state.zone_data)}")
        if st.button("Calculate TOU/VNBT Costs", use_container_width=True):
            _calculate_imported_zone_costs()


def _calculate_imported_zone_costs():
    """Calculate costs for imported zone data."""
    from datetime import date
    from eco_tools.lcca.tariffs import calculate_tou_costs, create_pge_e_tou_c, HourlyUsage

    zone_summaries = st.session_state.get("zone_data", [])
    if not zone_summaries:
        st.error("No zone data loaded")
        return

    enable_vnbt = st.session_state.get("zone_enable_vnbt", False)

    if enable_vnbt and st.session_state.get("zone_pv_hourly"):
        # V-NBT mode
        try:
            from eco_tools.lcca.vnbt import (
                calculate_zone_vnbt,
                format_zone_vnbt_results,
                create_pge_e_elec_vnbt,
            )

            tariff = create_pge_e_elec_vnbt()
            pv_hourly = st.session_state.get("zone_pv_hourly", [])

            vnbt_results = calculate_zone_vnbt(
                zones=zone_summaries,
                pv_hourly_generation=pv_hourly,
                tariff=tariff,
                allocation_method="by_consumption",
            )

            st.session_state.zone_vnbt_results = vnbt_results

            st.subheader("V-NBT Results")
            st.code(format_zone_vnbt_results(vnbt_results))

        except Exception as e:
            st.error(f"V-NBT calculation failed: {e}")
    else:
        # TOU mode
        tariff = create_pge_e_tou_c()
        total_elec_cost = 0.0
        total_gas_cost = 0.0
        gas_rate = 1.80  # Default $/therm for California

        has_gas_data = st.session_state.get("zone_has_gas", False)

        results = []
        for zone in zone_summaries:
            hourly_usage = []
            hour_of_year = 0
            days_per_month = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]

            for month in range(1, 13):
                for day in range(1, days_per_month[month - 1] + 1):
                    for hour in range(24):
                        if hour_of_year < len(zone.hourly_elec_kwh):
                            is_weekend = date(2024, month, day).weekday() >= 5
                            hourly_usage.append(HourlyUsage(
                                month=month,
                                day=day,
                                hour=hour,
                                kwh=zone.hourly_elec_kwh[hour_of_year],
                                is_weekend=is_weekend,
                            ))
                        hour_of_year += 1

            breakdown = calculate_tou_costs(hourly_usage, tariff)
            elec_cost = breakdown.total_cost
            total_elec_cost += elec_cost

            # Calculate gas cost (flat rate)
            zone_gas_therm = zone.gas_therm if zone.gas_therm else 0.0
            gas_cost = zone_gas_therm * gas_rate
            total_gas_cost += gas_cost

            zone_total_cost = elec_cost + gas_cost

            results.append({
                'zone': zone.zone_name,
                'kwh': zone.elec_kwh,
                'therm': zone_gas_therm,
                'elec_cost': elec_cost,
                'gas_cost': gas_cost,
                'total_cost': zone_total_cost,
            })

        st.session_state.zone_tou_results = results

        if has_gas_data:
            st.subheader("TOU Cost Results (Electric + Gas)")
        else:
            st.subheader("TOU Cost Results")

        for r in results:
            if r['therm'] > 0:
                st.write(f"**{r['zone']}**: {r['kwh']:,.0f} kWh (${r['elec_cost']:,.2f}) + {r['therm']:,.0f} therm (${r['gas_cost']:,.2f}) = **${r['total_cost']:,.2f}/yr**")
            else:
                st.write(f"**{r['zone']}**: {r['kwh']:,.0f} kWh → ${r['elec_cost']:,.2f}/yr")

        total_cost = total_elec_cost + total_gas_cost
        if has_gas_data:
            st.write(f"**ELECTRIC TOTAL**: ${total_elec_cost:,.2f}/yr")
            st.write(f"**GAS TOTAL**: ${total_gas_cost:,.2f}/yr (@ ${gas_rate:.2f}/therm)")
            st.write(f"**GRAND TOTAL**: ${total_cost:,.2f}/yr")
        else:
            st.write(f"**TOTAL**: ${total_elec_cost:,.2f}/yr")


def render_cost_breakdown_tab():
    """Render overall cost breakdown tab."""
    st.header("Cost Breakdown")

    report = st.session_state.get("zone_report")
    if not report:
        st.info("Configure zones in the Setup tab and click 'Calculate Zone LCCA' to see results.")
        return

    # Summary metrics
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            "Total Annual Cost",
            f"${report.total_annual_cost:,.0f}",
            help="Total annual energy cost for all zones"
        )

    with col2:
        st.metric(
            "Total Area",
            f"{report.total_area_sqft:,.0f} sqft",
        )

    with col3:
        st.metric(
            "Site EUI",
            f"{report.total_eui_kbtu_sqft:.1f} kBtu/sqft",
        )

    with col4:
        cost_per_sqft = report.total_annual_cost / report.total_area_sqft if report.total_area_sqft > 0 else 0
        st.metric(
            "Cost/sqft",
            f"${cost_per_sqft:.2f}/sqft/yr",
        )

    st.divider()

    # Category breakdown
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Cost by Category")

        # Pie chart
        if PLOTLY_AVAILABLE and report.category_summaries:
            labels = [cs.category_name for cs in report.category_summaries]
            values = [cs.total_annual_cost for cs in report.category_summaries]

            fig = go.Figure(data=[go.Pie(
                labels=labels,
                values=values,
                hole=0.4,
                textinfo='label+percent',
                marker=dict(colors=['#2ecc71', '#3498db'])
            )])
            fig.update_layout(
                showlegend=True,
                height=350,
                margin=dict(t=20, b=20, l=20, r=20)
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            # Fallback text display
            for cs in report.category_summaries:
                pct = cs.pct_of_building_cost
                st.write(f"**{cs.category_name}:** ${cs.total_annual_cost:,.0f} ({pct:.1f}%)")

    with col2:
        st.subheader("Category Details")

        for cs in report.category_summaries:
            with st.expander(f"{cs.category_name} - ${cs.total_annual_cost:,.0f}/yr"):
                st.write(f"**Zones:** {cs.zone_count}")
                st.write(f"**Area:** {cs.total_area_sqft:,.0f} sqft")
                st.write(f"**Electricity:** {cs.total_elec_kwh:,.0f} kWh")
                st.write(f"**Gas:** {cs.total_gas_therm:,.0f} therms")
                st.write(f"**EUI:** {cs.avg_eui_kbtu_sqft:.1f} kBtu/sqft")
                st.write(f"**Cost/sqft:** ${cs.avg_cost_per_sqft:.2f}/sqft/yr")

    st.divider()

    # Energy breakdown
    st.subheader("Energy Summary")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("Total Electricity", f"{report.total_elec_kwh:,.0f} kWh")

    with col2:
        st.metric("Total Gas", f"{report.total_gas_therm:,.0f} therms")

    with col3:
        total_kbtu = (report.total_elec_kwh * 3.412) + (report.total_gas_therm * 100)
        st.metric("Total Energy", f"{total_kbtu:,.0f} kBtu")


def render_dwelling_units_tab():
    """Render dwelling unit analysis tab."""
    st.header("Dwelling Unit Analysis")

    report = st.session_state.get("zone_report")
    if not report or not report.bedroom_summaries:
        st.info("No dwelling unit data available. Configure zones in the Setup tab.")
        return

    # Summary
    st.subheader("By Bedroom Count")

    # Bar chart of costs by bedroom type
    if PLOTLY_AVAILABLE:
        bedrooms = [f"{bs.num_bedrooms}-BR" for bs in report.bedroom_summaries]
        costs = [bs.avg_annual_cost for bs in report.bedroom_summaries]
        counts = [bs.unit_count for bs in report.bedroom_summaries]

        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=bedrooms,
            y=costs,
            text=[f"${c:,.0f}" for c in costs],
            textposition='auto',
            marker_color='#3498db',
            name='Avg Annual Cost'
        ))
        fig.update_layout(
            title="Average Annual Cost by Unit Type",
            xaxis_title="Unit Type",
            yaxis_title="Annual Cost ($)",
            height=350,
        )
        st.plotly_chart(fig, use_container_width=True)

    # Detailed table
    st.subheader("Unit Type Details")

    table_data = []
    for bs in report.bedroom_summaries:
        table_data.append({
            "Unit Type": f"{bs.num_bedrooms}-Bedroom",
            "Count": bs.unit_count,
            "Avg Area (sqft)": f"{bs.avg_area_sqft:,.0f}",
            "Avg Elec (kWh)": f"{bs.avg_elec_kwh:,.0f}",
            "Avg Gas (therm)": f"{bs.avg_gas_therm:,.0f}",
            "Avg Cost ($/yr)": f"${bs.avg_annual_cost:,.0f}",
            "Avg Cost ($/mo)": f"${bs.avg_annual_cost/12:,.0f}",
        })

    st.dataframe(table_data, use_container_width=True, hide_index=True)

    # Per-unit breakdown
    st.divider()
    st.subheader("Individual Dwelling Units")

    dwelling_zones = [z for z in report.zone_results if z.is_dwelling_unit]

    if dwelling_zones:
        zone_data = []
        for z in dwelling_zones:
            zone_data.append({
                "Zone": z.zone_name,
                "Bedrooms": z.num_bedrooms,
                "Area (sqft)": f"{z.area_sqft:,.0f}",
                "Elec Cost ($)": f"${z.gross_elec_cost:,.0f}",
                "Gas Cost ($)": f"${z.gross_gas_cost:,.0f}",
                "PV Credit ($)": f"${z.pv_credit:,.0f}",
                "Net Cost ($)": f"${z.net_total_cost:,.0f}",
            })

        st.dataframe(zone_data, use_container_width=True, hide_index=True)


def render_common_areas_tab():
    """Render common area analysis tab."""
    st.header("Common Area Analysis")

    report = st.session_state.get("zone_report")
    if not report or not report.common_area_summaries:
        st.info("No common area data available. Configure zones in the Setup tab.")
        return

    # Category summary
    st.subheader("By Category")

    if PLOTLY_AVAILABLE:
        categories = [cas.category.value.title() for cas in report.common_area_summaries]
        costs = [cas.total_annual_cost for cas in report.common_area_summaries]

        fig = go.Figure(data=[go.Bar(
            x=categories,
            y=costs,
            text=[f"${c:,.0f}" for c in costs],
            textposition='auto',
            marker_color='#e74c3c'
        )])
        fig.update_layout(
            title="Annual Cost by Common Area Category",
            xaxis_title="Category",
            yaxis_title="Annual Cost ($)",
            height=350,
        )
        st.plotly_chart(fig, use_container_width=True)

    # Category details
    st.subheader("Category Details")

    for cas in report.common_area_summaries:
        with st.expander(f"{cas.category.value.title()} - ${cas.total_annual_cost:,.0f}/yr"):
            col1, col2 = st.columns(2)

            with col1:
                st.write(f"**Zones:** {cas.zone_count}")
                st.write(f"**Total Area:** {cas.total_area_sqft:,.0f} sqft")
                st.write(f"**Electricity:** {cas.total_elec_kwh:,.0f} kWh")

            with col2:
                st.write(f"**Gas:** {cas.total_gas_therm:,.0f} therms")
                st.write(f"**EUI:** {cas.eui_kbtu_sqft:.1f} kBtu/sqft")
                st.write(f"**Cost/sqft:** ${cas.cost_per_sqft:.2f}/sqft/yr")

            if cas.zone_names:
                st.write(f"**Zones:** {', '.join(cas.zone_names)}")

    # Individual zones
    st.divider()
    st.subheader("Individual Common Areas")

    common_zones = [z for z in report.zone_results if not z.is_dwelling_unit]

    if common_zones:
        zone_data = []
        for z in common_zones:
            zone_data.append({
                "Zone": z.zone_name,
                "Category": z.category.value.title() if z.category else "Other",
                "Area (sqft)": f"{z.area_sqft:,.0f}",
                "Elec (kWh)": f"{z.annual_elec_kwh:,.0f}",
                "Gas (therm)": f"{z.annual_gas_therm:,.0f}",
                "Annual Cost ($)": f"${z.net_total_cost:,.0f}",
            })

        st.dataframe(zone_data, use_container_width=True, hide_index=True)


def render_cuac_tab():
    """Render CUAC utility allowance tab."""
    st.header("CUAC Utility Allowances")

    report = st.session_state.get("zone_report")

    if not report or not report.has_cuac:
        st.info("CUAC analysis not enabled. Enable it in the sidebar settings and recalculate.")

        # Show explanation
        with st.expander("What is CUAC?"):
            st.markdown("""
            **CUAC (California Utility Allowance Calculator)** is used for:

            - **Affordable Housing Projects** - Calculating utility allowances for rent determination
            - **HUD Compliance** - Meeting federal requirements for subsidized housing
            - **Energy Modeling** - Per-unit energy and cost projections

            To enable CUAC analysis:
            1. Check "Enable CUAC Analysis" in the sidebar
            2. Recalculate zone costs
            """)
        return

    cuac = report.cuac_summary

    # Summary
    st.subheader("Allowance Summary")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("Total Units", cuac.total_dwelling_units)

    with col2:
        st.metric("Annual Allowance", f"${cuac.total_annual_allowance:,.0f}")

    with col3:
        if cuac.total_pv_kwdc > 0:
            st.metric("PV System", f"{cuac.total_pv_kwdc:.1f} kWdc")

    st.divider()

    # Allowance table
    st.subheader("Monthly Allowances by Bedroom Count")

    allowance_data = []
    for row in cuac.get_allowance_table():
        allowance_data.append({
            "Bedrooms": f"{row['bedrooms']}-BR",
            "Elec ($)": f"${row['gross_elec']:.2f}",
            "Gas ($)": f"${row['gross_gas']:.2f}",
            "Gross Total ($)": f"${row['gross_total']:.2f}",
            "PV Credit ($)": f"${row['pv_credit']:.2f}",
            "Net Allowance ($)": f"${row['net_allowance']:.2f}",
        })

    st.dataframe(allowance_data, use_container_width=True, hide_index=True)

    # Visual comparison
    if PLOTLY_AVAILABLE and cuac.allowances_by_bedroom:
        st.subheader("Allowance Comparison")

        bedrooms = list(cuac.allowances_by_bedroom.keys())
        gross = [cuac.allowances_by_bedroom[b].gross_total_allowance for b in bedrooms]
        net = [cuac.allowances_by_bedroom[b].net_total_allowance for b in bedrooms]

        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=[f"{b}-BR" for b in bedrooms],
            y=gross,
            name='Gross Allowance',
            marker_color='#95a5a6'
        ))
        fig.add_trace(go.Bar(
            x=[f"{b}-BR" for b in bedrooms],
            y=net,
            name='Net Allowance (after PV)',
            marker_color='#27ae60'
        ))
        fig.update_layout(
            title="Monthly Utility Allowance by Unit Type",
            xaxis_title="Unit Type",
            yaxis_title="Monthly Allowance ($)",
            barmode='group',
            height=350,
        )
        st.plotly_chart(fig, use_container_width=True)


def render_ranking_tab():
    """Render zone performance ranking tab."""
    st.header("Zone Performance Ranking")

    report = st.session_state.get("zone_report")
    if not report or not report.zone_results:
        st.info("No zone data available. Configure zones in the Setup tab.")
        return

    # Ranking by different metrics
    metric = st.radio(
        "Rank By",
        ["Cost/sqft", "EUI", "Total Cost"],
        horizontal=True
    )

    # Calculate rankings
    ranked_zones = []
    for z in report.zone_results:
        eui = 0
        if z.area_sqft > 0:
            eui = ((z.annual_elec_kwh * 3.412) + (z.annual_gas_therm * 100)) / z.area_sqft
        cost_per_sqft = z.net_total_cost / z.area_sqft if z.area_sqft > 0 else 0

        ranked_zones.append({
            "zone": z,
            "cost_per_sqft": cost_per_sqft,
            "eui": eui,
            "total_cost": z.net_total_cost,
        })

    # Sort based on metric
    if metric == "Cost/sqft":
        ranked_zones.sort(key=lambda x: x["cost_per_sqft"], reverse=True)
        value_key = "cost_per_sqft"
        format_str = "${:.2f}/sqft"
    elif metric == "EUI":
        ranked_zones.sort(key=lambda x: x["eui"], reverse=True)
        value_key = "eui"
        format_str = "{:.1f} kBtu/sqft"
    else:
        ranked_zones.sort(key=lambda x: x["total_cost"], reverse=True)
        value_key = "total_cost"
        format_str = "${:,.0f}"

    # Display ranking
    st.subheader(f"Zones Ranked by {metric}")

    # Bar chart
    if PLOTLY_AVAILABLE:
        zones = [rz["zone"].zone_name for rz in ranked_zones[:15]]  # Top 15
        values = [rz[value_key] for rz in ranked_zones[:15]]
        types = ["Dwelling" if rz["zone"].is_dwelling_unit else "Common" for rz in ranked_zones[:15]]

        colors = ['#3498db' if t == "Dwelling" else '#e74c3c' for t in types]

        fig = go.Figure(data=[go.Bar(
            x=values,
            y=zones,
            orientation='h',
            marker_color=colors,
            text=[format_str.format(v) for v in values],
            textposition='outside',
        )])
        fig.update_layout(
            title=f"Top Zones by {metric}",
            xaxis_title=metric,
            height=max(350, len(zones) * 25),
            yaxis=dict(autorange="reversed"),
        )
        st.plotly_chart(fig, use_container_width=True)

    # Table
    table_data = []
    for i, rz in enumerate(ranked_zones, 1):
        z = rz["zone"]
        table_data.append({
            "Rank": i,
            "Zone": z.zone_name,
            "Type": "Dwelling" if z.is_dwelling_unit else "Common",
            "Area (sqft)": f"{z.area_sqft:,.0f}",
            "EUI": f"{rz['eui']:.1f}",
            "Cost/sqft": f"${rz['cost_per_sqft']:.2f}",
            "Total Cost": f"${rz['total_cost']:,.0f}",
        })

    st.dataframe(table_data, use_container_width=True, hide_index=True)


def render_zone_export_tab():
    """Render export options tab."""
    st.header("Export Zone Analysis")

    report = st.session_state.get("zone_report")
    if not report:
        st.info("No analysis results to export. Run the zone analysis first.")
        return

    # Text report
    st.subheader("Text Report")

    text_report = format_zone_report(report)

    st.text_area(
        "Report Preview",
        value=text_report,
        height=400,
        disabled=True
    )

    st.download_button(
        "Download Text Report",
        data=text_report,
        file_name=f"{report.building_name or 'zone_report'}_zone_lcca.txt",
        mime="text/plain"
    )

    st.divider()

    # Excel export
    st.subheader("Excel Export")

    if st.button("Generate Excel Report", use_container_width=True):
        try:
            import pandas as pd
            import io

            # Get Excel-ready data
            sheets_data = get_excel_sheets_data(report)

            # Create Excel file in memory
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                for sheet_name, rows in sheets_data.items():
                    if rows:
                        df = pd.DataFrame(rows)
                        df.to_excel(writer, sheet_name=sheet_name, index=False)

            output.seek(0)

            st.download_button(
                "Download Excel Report",
                data=output.getvalue(),
                file_name=f"{report.building_name or 'zone_report'}_zone_lcca.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

            st.success("Excel report generated!")

        except ImportError:
            st.error("pandas and openpyxl required for Excel export. Install with: pip install pandas openpyxl")
        except Exception as e:
            st.error(f"Excel export failed: {e}")

    st.divider()

    # CUAC table export
    if report.has_cuac:
        st.subheader("CUAC Allowance Table")

        cuac_table = format_cuac_allowance_table(report)

        st.download_button(
            "Download CUAC Table",
            data=cuac_table,
            file_name=f"{report.building_name or 'zone_report'}_cuac_allowances.txt",
            mime="text/plain"
        )


# Entry point for Streamlit page
if __name__ == "__main__":
    handle_zone_analysis()
