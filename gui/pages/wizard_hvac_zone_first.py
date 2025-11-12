"""
Zone-First HVAC Step for Wizard
Redesigned to show zones first, then group them, then generate systems
"""

import streamlit as st
from typing import Dict, Any, List

# This will replace show_hvac_step in wizard_page.py

def show_hvac_step_zone_first(model: Dict[str, Any], analysis: Dict[str, Any]):
    """Step 4: Create HVAC systems - ZONE-FIRST approach."""
    st.header("❄️ Step 4: HVAC Systems - Zone Grouping")

    counts = analysis["counts"]
    needs = analysis["needs"]

    # Get building type and climate zone
    building_type = st.session_state.wizard_data.get("building_type", "warehouse")
    climate_zone = st.session_state.wizard_data.get("climate_zone", "4")

    # Map to display names
    building_type_map = {
        "multifamily": "Multifamily Residential",
        "small_commercial": "Small Commercial",
        "large_commercial": "Large Commercial",
        "warehouse": "Warehouse/Industrial"
    }
    building_type_display = building_type_map.get(building_type, "Warehouse/Industrial")

    st.success(f"📋 **Building Type**: {building_type_display} | **Climate Zone**: {climate_zone}")
    st.caption("(Set in Step 1 - Overview)")

    st.info("💡 **Zone-First Approach**: Group your zones by function/location, then assign HVAC systems to each group.")

    # Initialize zone groups in session state
    if "hvac_zone_groups" not in st.session_state:
        st.session_state.hvac_zone_groups = []

    # Get all zones
    zones = model.get("geometry", {}).get("zones", [])

    if not zones:
        st.warning("⚠️ No zones found in model. Import geometry first.")
        return

    # Tabs for different workflows
    tabs = st.tabs(["🎯 Quick Setup", "📦 Zone Grouping", "⚙️ Groups & Systems", "📊 Review"])

    # ===== TAB 1: QUICK SETUP =====
    with tabs[0]:
        st.markdown("### Quick Setup Options")
        st.caption("Fast zone-to-system assignment for common building configurations")

        # Calculate MF-specific options
        is_multifamily = (building_type == "multifamily")

        if is_multifamily:
            st.info("🏢 **Multifamily Configuration**: Choose between individual dwelling unit systems or central systems")

            mf_option = st.radio(
                "Multifamily System Configuration:",
                [
                    "Individual DU Systems (one system per unit)",
                    "Central System (one/few systems for whole building)",
                    "Mixed (central common areas + individual units)"
                ],
                help="Per Title 24, multifamily can use individual DU systems or central systems"
            )

            if mf_option == "Individual DU Systems (one system per unit)":
                st.caption(f"💡 Will create {len(zones)} systems (one per zone/DU)")

                # DU system type options per Title 24
                du_system_types = [
                    "Split System Heat Pump (Title 24 2022 Standard)",
                    "Packaged Terminal Heat Pump (PTHP)",
                    "Variable Refrigerant Flow (VRF) - Per DU",
                    "Central Forced Air - Individual"
                ]

                du_system_type = st.selectbox(
                    "DU HVAC System Type:",
                    du_system_types,
                    help="Title 24 2022 requires heat pumps for new multifamily construction"
                )

                if st.button("🚀 Create Individual DU Groups", type="primary", use_container_width=True):
                    # Step 1: Create groups
                    create_individual_du_systems(model, zones, du_system_type, climate_zone)

                    # Step 2: Auto-generate systems
                    generate_systems_from_groups(model, st.session_state.hvac_zone_groups, climate_zone)

                    hvac_count = len(model.get("systems", {}).get("hvac", []))
                    st.session_state.hvac_systems_generated = True
                    st.success(f"✅ Successfully created {hvac_count} individual DU HVAC system(s)! View in 'Review' tab or Active Model page.")
                    st.rerun()

            elif mf_option == "Central System (one/few systems for whole building)":
                st.caption(f"💡 Will create central systems serving all {len(zones)} zones")

                num_central_systems = st.number_input(
                    "Number of Central Systems:",
                    min_value=1,
                    max_value=5,
                    value=1,
                    help="Typically 1-2 central systems for multifamily buildings"
                )

                central_system_types = [
                    "Variable Refrigerant Flow (VRF)",
                    "Chilled Water + Boiler",
                    "Central Heat Pump",
                    "Packaged Rooftop Unit (RTU)"
                ]

                central_system_type = st.selectbox(
                    "Central HVAC System Type:",
                    central_system_types
                )

                if st.button("🚀 Create Central System Groups", type="primary", use_container_width=True):
                    # Step 1: Create groups
                    create_central_systems(model, zones, num_central_systems, central_system_type, building_type, climate_zone)

                    # Step 2: Auto-generate systems
                    generate_systems_from_groups(model, st.session_state.hvac_zone_groups, climate_zone)

                    hvac_count = len(model.get("systems", {}).get("hvac", []))
                    st.session_state.hvac_systems_generated = True
                    st.success(f"✅ Successfully created {hvac_count} central HVAC system(s)! View in 'Review' tab or Active Model page.")
                    st.rerun()

        else:
            # Nonresidential (NR) Quick Setup
            st.info("🏭 **Nonresidential Configuration**: Choose zone grouping strategy")

            nr_option = st.radio(
                "Nonresidential System Configuration:",
                [
                    "One system per zone",
                    "Group by space type (auto-detect)",
                    "Group by floor (if floor data available)",
                    "Manual grouping (next tab)"
                ],
                help="Common approaches for commercial/warehouse buildings"
            )

            if nr_option == "One system per zone":
                st.caption(f"💡 Will create {len(zones)} groups (one zone each)")

                # NR system type options per Title 24
                nr_system_types = [
                    "Packaged Rooftop Unit (RTU)",
                    "Split System Heat Pump",
                    "Variable Refrigerant Flow (VRF)",
                    "Make-Up Air Unit (MAU)",
                    "Unit Heater",
                    "Packaged Terminal AC (PTAC)"
                ]

                # Smart defaults by warehouse vs commercial
                if building_type == "warehouse":
                    default_idx = 0  # RTU
                else:
                    default_idx = 2  # VRF for commercial

                nr_system_type = st.selectbox(
                    "HVAC System Type:",
                    nr_system_types,
                    index=default_idx
                )

                if st.button("🚀 Create One Group Per Zone", type="primary", use_container_width=True):
                    # Step 1: Create groups
                    create_one_system_per_zone(model, zones, nr_system_type, building_type, climate_zone)

                    # Step 2: Auto-generate systems
                    generate_systems_from_groups(model, st.session_state.hvac_zone_groups, climate_zone)

                    hvac_count = len(model.get("systems", {}).get("hvac", []))
                    st.session_state.hvac_systems_generated = True
                    st.success(f"✅ Successfully created {hvac_count} HVAC system(s) (one per zone)! View in 'Review' tab or Active Model page.")
                    st.rerun()

            elif nr_option == "Group by space type (auto-detect)":
                st.caption("💡 Automatically groups zones by name patterns (warehouse, office, amenity, etc.)")

                # Show preview of auto-detected groups
                auto_groups = auto_detect_zone_groups(zones, building_type)
                print(f"[DEBUG QUICK_SETUP] Auto-detected {len(auto_groups)} groups")
                print(f"[DEBUG QUICK_SETUP] Group names: {list(auto_groups.keys())}")

                st.markdown("**Detected Groups:**")
                for group_name, group_zones in auto_groups.items():
                    st.markdown(f"- **{group_name}**: {len(group_zones)} zones ({sum(z.get('floor_area_sqft', 0) for z in group_zones):,.0f} sqft)")

                if st.button("🚀 Create Groups from Auto-Detection", type="primary", use_container_width=True):
                    # Step 1: Create groups in session state
                    create_systems_from_auto_groups(model, auto_groups, building_type, climate_zone)

                    # Step 2: Automatically generate HVAC systems from those groups
                    generate_systems_from_groups(model, st.session_state.hvac_zone_groups, climate_zone)

                    hvac_count = len(model.get("systems", {}).get("hvac", []))
                    st.session_state.hvac_systems_generated = True
                    st.success(f"✅ Successfully created {hvac_count} HVAC system(s) from {len(auto_groups)} auto-detected zone groups! View in 'Review' tab or Active Model page.")
                    st.rerun()

            elif nr_option == "Manual grouping (next tab)":
                st.info("👉 Go to the **Zone Grouping** tab to manually group zones")

    # ===== TAB 2: ZONE GROUPING =====
    with tabs[1]:
        st.markdown("### Manual Zone Grouping")
        st.caption("Select zones and create custom groups")

        # Initialize selection state
        if "zone_selection" not in st.session_state:
            st.session_state.zone_selection = set()

        # Show all zones with checkboxes
        st.markdown(f"**All Zones** ({len(zones)} total)")

        # Quick select buttons
        col1, col2, col3 = st.columns(3)
        with col1:
            if st.button("✅ Select All", use_container_width=True):
                st.session_state.zone_selection = {z.get("id", f"zone_{i}") for i, z in enumerate(zones)}
                st.rerun()
        with col2:
            if st.button("❌ Clear Selection", use_container_width=True):
                st.session_state.zone_selection = set()
                st.rerun()
        with col3:
            selected_count = len(st.session_state.zone_selection)
            st.metric("Selected", selected_count)

        st.divider()

        # Show zones in a table-like format
        for i, zone in enumerate(zones):
            zone_id = zone.get("id", f"zone_{i}")
            zone_name = zone.get("name", zone_id)
            floor_area = zone.get("floor_area_sqft", 0)

            col1, col2 = st.columns([1, 4])

            with col1:
                is_selected = st.checkbox(
                    "Select",
                    value=zone_id in st.session_state.zone_selection,
                    key=f"zone_select_{zone_id}",
                    label_visibility="collapsed"
                )

                if is_selected and zone_id not in st.session_state.zone_selection:
                    st.session_state.zone_selection.add(zone_id)
                elif not is_selected and zone_id in st.session_state.zone_selection:
                    st.session_state.zone_selection.remove(zone_id)

            with col2:
                st.markdown(f"**{zone_name}** - `{zone_id}` - {floor_area:,.0f} sqft")

        # Create group from selection
        if st.session_state.zone_selection:
            st.divider()
            st.markdown(f"### Create Group from {len(st.session_state.zone_selection)} Selected Zones")

            total_area = sum(
                zone.get("floor_area_sqft", 0)
                for i, zone in enumerate(zones)
                if zone.get("id", f"zone_{i}") in st.session_state.zone_selection
            )

            st.caption(f"Total floor area: {total_area:,.0f} sqft")

            col1, col2 = st.columns(2)

            with col1:
                group_name = st.text_input(
                    "Group Name:",
                    placeholder="e.g., Warehouse Storage, Office Areas",
                    key="new_group_name"
                )

            with col2:
                # System types (full list)
                all_system_types = get_all_hvac_system_types()
                suggested = get_suggested_hvac_types(building_type)

                group_system_type = st.selectbox(
                    "System Type for this Group:",
                    all_system_types,
                    index=all_system_types.index(suggested[0]) if suggested[0] in all_system_types else 0,
                    key="new_group_system_type"
                )

            if st.button("➕ Create Group", type="primary", use_container_width=True):
                if group_name:
                    # Create group
                    new_group = {
                        "name": group_name,
                        "system_type": group_system_type,
                        "zone_ids": list(st.session_state.zone_selection),
                        "total_area_sqft": total_area
                    }
                    st.session_state.hvac_zone_groups.append(new_group)
                    st.session_state.zone_selection = set()  # Clear selection
                    st.success(f"✅ Created group: {group_name}")
                    st.rerun()
                else:
                    st.error("Please enter a group name")

    # ===== TAB 3: GROUPS & SYSTEMS =====
    with tabs[2]:
        st.markdown("### Groups & Systems")

        # Debug: Show session state
        print(f"[DEBUG TAB3] hvac_zone_groups in session_state: {'hvac_zone_groups' in st.session_state}")
        if "hvac_zone_groups" in st.session_state:
            print(f"[DEBUG TAB3] Number of zone groups: {len(st.session_state.hvac_zone_groups)}")
            for i, grp in enumerate(st.session_state.hvac_zone_groups):
                print(f"[DEBUG TAB3] Group {i}: {grp.get('name', 'Unknown')} - {len(grp.get('zone_ids', []))} zones")

        if not st.session_state.hvac_zone_groups:
            st.warning("⚠️ No groups created yet. Use **Quick Setup** or **Zone Grouping** tab to create groups first.")
            st.info("💡 **Hint**: Go to the 'Quick Setup' tab and click one of the quick setup buttons to automatically group your zones.")
        else:
            st.markdown(f"**{len(st.session_state.hvac_zone_groups)} Group(s) Defined**")

            for idx, group in enumerate(st.session_state.hvac_zone_groups):
                group_name = group["name"]
                system_type = group["system_type"]
                zone_count = len(group["zone_ids"])
                total_area = group["total_area_sqft"]

                # Use container with border instead of expander (tabs cannot contain expanders)
                st.markdown(f"#### 🏢 {group_name}")
                st.caption(f"{zone_count} zones • {total_area:,.0f} sqft")

                col1, col2, col3 = st.columns(3)

                with col1:
                    st.markdown(f"**System Type**: {system_type}")
                    st.markdown(f"**Zones**: {zone_count}")
                    st.markdown(f"**Area**: {total_area:,.0f} sqft")

                with col2:
                    # Autosize option
                    if st.button(f"🔧 Autosize System", key=f"autosize_group_{idx}", use_container_width=True):
                        from gui.utils.autosizing import AutoSizer

                        capacity = AutoSizer.calculate_hvac_capacity(
                            floor_area_sqft=total_area,
                            building_type=building_type,
                            climate_zone=climate_zone
                        )

                        group["autosized_capacity"] = capacity
                        st.success(f"✅ {capacity['cooling_tons']:.1f} tons cooling")
                        st.rerun()

                with col3:
                    if st.button(f"🗑️ Delete Group", key=f"delete_group_{idx}", use_container_width=True):
                        st.session_state.hvac_zone_groups.pop(idx)
                        st.rerun()

                # Show capacity if autosized
                if "autosized_capacity" in group:
                    cap = group["autosized_capacity"]
                    st.markdown(f"**Autosized Capacities**:")
                    st.markdown(f"- Cooling: {cap['cooling_tons']:.1f} tons ({cap['cooling_capacity_kw']:.1f} kW)")
                    st.markdown(f"- Heating: {cap['heating_capacity_kw']:.1f} kW")
                    st.markdown(f"- Airflow: {cap['airflow_cfm']:,.0f} CFM")

                st.divider()  # Separator between groups

            st.divider()

            # Generate systems from groups
            if st.button("🚀 Generate HVAC Systems from Groups", type="primary", use_container_width=True):
                generate_systems_from_groups(model, st.session_state.hvac_zone_groups, climate_zone)
                st.success(f"✅ Created {len(st.session_state.hvac_zone_groups)} HVAC system(s)!")
                st.session_state.hvac_systems_generated = True
                st.rerun()

    # ===== TAB 4: REVIEW =====
    with tabs[3]:
        st.markdown("### Review HVAC Systems")

        # Show existing HVAC systems
        hvac_systems = model.get("systems", {}).get("hvac", [])

        if not hvac_systems:
            st.info("No HVAC systems generated yet. Go to 'Groups & Systems' tab to generate systems from your groups.")
        else:
            st.success(f"✅ {len(hvac_systems)} HVAC system(s) defined")

            # Get all zones for reference
            zones = analysis.get("zones", [])
            zone_names = {z.get("id", f"zone_{i}"): z.get("name", f"Zone {i+1}") for i, z in enumerate(zones)}

            for idx, sys in enumerate(hvac_systems):
                sys_name = sys.get("name", "Unknown")
                sys_type = sys.get("system_type", "Unknown")
                served_zones = sys.get("served_zones", [])
                served_area = sys.get("served_area_sqft", 0)
                cooling_tons = sys.get("cooling_tons", 0)
                heating_kw = sys.get("heating_capacity_kw", 0)
                airflow_cfm = sys.get("airflow_cfm", 0)

                # Get system configuration flags
                is_dedicated = sys.get("is_dedicated_per_zone", False)
                system_multiplier = sys.get("system_multiplier", 1)

                # Use container instead of expander (tabs cannot contain expanders)
                st.markdown(f"#### ❄️ {sys_name}")
                caption_parts = [f"{len(served_zones)} zones", f"{served_area:,.0f} sqft"]
                if system_multiplier > 1:
                    caption_parts.append(f"×{system_multiplier} systems")
                if is_dedicated:
                    caption_parts.append("Dedicated per zone")
                st.caption(" • ".join(caption_parts))

                col1, col2, col3 = st.columns([2, 2, 1])

                with col1:
                    # Editable name
                    new_name = st.text_input(
                        "System Name:",
                        value=sys_name,
                        key=f"review_sys_name_{idx}"
                    )
                    if new_name != sys_name:
                        sys["name"] = new_name

                    # Editable system type
                    all_types = get_all_hvac_system_types()
                    try:
                        current_idx = all_types.index(sys_type)
                    except ValueError:
                        current_idx = 0

                    new_type = st.selectbox(
                        "System Type:",
                        all_types,
                        index=current_idx,
                        key=f"review_sys_type_{idx}"
                    )
                    if new_type != sys_type:
                        sys["system_type"] = new_type

                with col2:
                    st.markdown("**HVAC Configuration:**")

                    # Dedicated vs Shared toggle
                    new_is_dedicated = st.checkbox(
                        "Dedicated system per zone",
                        value=is_dedicated,
                        key=f"review_dedicated_{idx}",
                        help="If checked, each zone gets its own system (autosized separately). If unchecked, all zones share one system."
                    )
                    # Always update (fixes double-click issue)
                    sys["is_dedicated_per_zone"] = new_is_dedicated
                    # Show warning when switching to dedicated mode
                    if new_is_dedicated and not is_dedicated:
                        st.warning("⚠️ Switched to dedicated mode. Click 'Re-Autosize' to update capacities.")

                    # System multiplier
                    new_multiplier = st.number_input(
                        "System multiplier:",
                        min_value=1,
                        max_value=20,
                        value=system_multiplier,
                        key=f"review_multiplier_{idx}",
                        help="Number of identical systems (useful for redundancy or phased installation)"
                    )
                    # Always update (fixes double-click issue)
                    sys["system_multiplier"] = new_multiplier

                with col3:
                    # Re-autosize button
                    if st.button("🔧 Re-Autosize", key=f"review_autosize_{idx}", use_container_width=True):
                        from gui.utils.autosizing import AutoSizer

                        # Get zones for this system
                        system_zones = [z for z in zones if z.get("id") in served_zones]

                        if new_is_dedicated:
                            # Autosize each zone individually and store details
                            total_cooling = 0
                            total_heating = 0
                            total_airflow = 0
                            zone_capacities = []

                            for zone in system_zones:
                                zone_id = zone.get("id")
                                zone_area = zone.get("floor_area_sqft", zone.get("floor_area_sf", 1000))
                                capacity = AutoSizer.calculate_hvac_capacity(
                                    floor_area_sqft=zone_area,
                                    building_type=building_type,
                                    climate_zone=climate_zone
                                )

                                # Store individual zone capacity
                                zone_capacities.append({
                                    "zone_id": zone_id,
                                    "zone_area_sqft": zone_area,
                                    "cooling_tons": capacity["cooling_tons"],
                                    "heating_kw": capacity["heating_capacity_kw"],
                                    "airflow_cfm": capacity["airflow_cfm"]
                                })

                                # Sum up totals
                                total_cooling += capacity["cooling_tons"]
                                total_heating += capacity["heating_capacity_kw"]
                                total_airflow += capacity["airflow_cfm"]

                            # Store both individual and total capacities
                            sys["zone_capacities"] = zone_capacities
                            sys["cooling_tons"] = round(total_cooling, 1)
                            sys["heating_capacity_kw"] = round(total_heating, 1)
                            sys["airflow_cfm"] = round(total_airflow, 0)
                            st.success(f"✅ Re-autosized {len(system_zones)} dedicated systems — Total: {total_cooling:.1f} tons")
                        else:
                            # Autosize as single shared system
                            capacity = AutoSizer.calculate_hvac_capacity(
                                floor_area_sqft=served_area,
                                building_type=building_type,
                                climate_zone=climate_zone
                            )
                            sys["cooling_tons"] = capacity["cooling_tons"]
                            sys["heating_capacity_kw"] = capacity["heating_capacity_kw"]
                            sys["airflow_cfm"] = capacity["airflow_cfm"]
                            # Clear zone_capacities when switching to shared
                            sys.pop("zone_capacities", None)
                            st.success(f"✅ Re-autosized shared system — {capacity['cooling_tons']:.1f} tons")

                        st.rerun()

                    if st.button("🗑️ Delete", key=f"review_delete_{idx}", use_container_width=True):
                        hvac_systems.pop(idx)
                        st.success("System deleted!")
                        st.rerun()

                # Show autosized capacities
                st.markdown("**Autosized Capacities:**")

                # Display differs based on dedicated vs shared mode
                if is_dedicated:
                    # Show individual zone capacities in dedicated mode
                    zone_capacities = sys.get("zone_capacities", [])
                    if zone_capacities:
                        st.markdown(f"**Per-Zone Systems** ({len(zone_capacities)} dedicated systems):")

                        # Show in a compact table format
                        for i, zone_cap in enumerate(zone_capacities):
                            zone_id = zone_cap.get("zone_id", "unknown")
                            zone_name_display = zone_names.get(zone_id, zone_id)
                            zcol1, zcol2, zcol3, zcol4 = st.columns([2, 1, 1, 1])
                            with zcol1:
                                st.markdown(f"**{zone_name_display}**")
                            with zcol2:
                                st.markdown(f"{zone_cap.get('cooling_tons', 0):.1f} tons")
                            with zcol3:
                                st.markdown(f"{zone_cap.get('heating_kw', 0):.1f} kW")
                            with zcol4:
                                st.markdown(f"{zone_cap.get('airflow_cfm', 0):,.0f} CFM")

                        st.divider()
                        st.markdown("**Total for All Zones:**")

                    # Show totals
                    cap_col1, cap_col2, cap_col3, cap_col4 = st.columns(4)
                    with cap_col1:
                        st.metric("Total Cooling", f"{cooling_tons:.1f} tons")
                    with cap_col2:
                        st.metric("Total Heating", f"{heating_kw:.1f} kW")
                    with cap_col3:
                        st.metric("Total Airflow", f"{airflow_cfm:,.0f} CFM")
                    with cap_col4:
                        st.metric("Served Area", f"{served_area:,.0f} sqft")
                else:
                    # Shared mode - show single system capacity
                    cap_col1, cap_col2, cap_col3, cap_col4 = st.columns(4)
                    with cap_col1:
                        st.metric("Cooling", f"{cooling_tons:.1f} tons")
                    with cap_col2:
                        st.metric("Heating", f"{heating_kw:.1f} kW")
                    with cap_col3:
                        st.metric("Airflow", f"{airflow_cfm:,.0f} CFM")
                    with cap_col4:
                        st.metric("Served Area", f"{served_area:,.0f} sqft")

                # Show multiplier effect if applicable
                if system_multiplier > 1:
                    if is_dedicated:
                        st.info(f"ℹ️ **System multiplier: ×{system_multiplier}** — Total: {len(served_zones) * system_multiplier} systems ({len(served_zones)} zones × {system_multiplier} per zone) — Total capacity: {cooling_tons * system_multiplier:.1f} tons cooling, {heating_kw * system_multiplier:.1f} kW heating")
                    else:
                        st.info(f"ℹ️ **Per-system capacity:** {cooling_tons:.1f} tons cooling, {heating_kw:.1f} kW heating — **Total with ×{system_multiplier} multiplier:** {cooling_tons * system_multiplier:.1f} tons cooling, {heating_kw * system_multiplier:.1f} kW heating")

                # Show served zones
                st.markdown(f"**Served Zones** ({len(served_zones)}):")
                zone_list = [zone_names.get(z, z) for z in served_zones]
                if len(zone_list) <= 10:
                    for zone in zone_list:
                        st.markdown(f"- {zone}")
                else:
                    # Show first 5, last 5 if many zones
                    for zone in zone_list[:5]:
                        st.markdown(f"- {zone}")
                    st.markdown(f"... and {len(zone_list) - 10} more zones ...")
                    for zone in zone_list[-5:]:
                        st.markdown(f"- {zone}")

                # Show JSON with checkbox toggle instead of nested expander
                if st.checkbox("🔧 Show JSON", key=f"show_json_{idx}"):
                    st.json(sys)

                st.divider()  # Separator between systems

    # Navigation
    st.divider()
    col1, col2, col3 = st.columns([1, 2, 1])
    with col1:
        if st.button("◀️ Back", use_container_width=True):
            st.session_state.wizard_step = 3
            st.rerun()
    with col3:
        if st.button("Next ▶️", type="primary", use_container_width=True):
            st.session_state.wizard_step = 4  # Go to DHW step
            st.rerun()


# ===== HELPER FUNCTIONS =====

def get_all_hvac_system_types() -> List[str]:
    """Get full list of HVAC system types."""
    return [
        "Packaged Rooftop Unit (RTU)",
        "Split System Heat Pump",
        "Variable Refrigerant Flow (VRF)",
        "Packaged Terminal AC (PTAC)",
        "Packaged Terminal Heat Pump (PTHP)",
        "Water Source Heat Pump (WSHP)",
        "Ground Source Heat Pump (GSHP)",
        "Fan Coil Units (FCU)",
        "Chilled Water + Boiler",
        "Dedicated Outdoor Air System (DOAS)",
        "Make-Up Air Unit (MAU)",
        "Unit Heater",
        "Radiant Heating",
        "Evaporative Cooling"
    ]


def get_suggested_hvac_types(building_type: str) -> List[str]:
    """Get suggested HVAC types by building type per Title 24."""
    suggestions = {
        "multifamily": ["Split System Heat Pump", "Variable Refrigerant Flow (VRF)", "Packaged Terminal Heat Pump (PTHP)"],
        "small_commercial": ["Variable Refrigerant Flow (VRF)", "Packaged Rooftop Unit (RTU)", "Split System Heat Pump"],
        "large_commercial": ["Variable Refrigerant Flow (VRF)", "Chilled Water + Boiler", "Dedicated Outdoor Air System (DOAS)"],
        "warehouse": ["Packaged Rooftop Unit (RTU)", "Make-Up Air Unit (MAU)", "Unit Heater"]
    }
    return suggestions.get(building_type, ["Packaged Rooftop Unit (RTU)"])


def auto_detect_zone_groups(zones: List[Dict], building_type: str) -> Dict[str, List[Dict]]:
    """Auto-detect zone groups by name patterns."""
    groups = {}

    # Common patterns
    patterns = {
        "Warehouse/Storage": ["warehouse", "storage", "flammable", "aerosol", "receiving", "shipping"],
        "Office Areas": ["office", "conference", "private", "cubicle", "admin"],
        "Amenities": ["restroom", "locker", "wellness", "lactation", "multifaith", "janitor", "break room"],
        "Mechanical/Support": ["electrical", "mechanical", "pump", "mech", "elec"],
        "Other": []
    }

    for zone in zones:
        zone_name = zone.get("name", "").lower()
        matched = False

        for group_name, keywords in patterns.items():
            if group_name == "Other":
                continue
            if any(keyword in zone_name for keyword in keywords):
                if group_name not in groups:
                    groups[group_name] = []
                groups[group_name].append(zone)
                matched = True
                break

        if not matched:
            if "Other" not in groups:
                groups["Other"] = []
            groups["Other"].append(zone)

    return groups


def create_individual_du_systems(model: Dict, zones: List[Dict], system_type: str, climate_zone: str):
    """Create individual groups (one per zone) for DU systems."""
    from gui.utils.autosizing import AutoSizer

    # Initialize session state groups if needed
    if "hvac_zone_groups" not in st.session_state:
        st.session_state.hvac_zone_groups = []

    # Clear existing groups
    st.session_state.hvac_zone_groups = []

    for i, zone in enumerate(zones):
        zone_id = zone.get("id", f"zone_{i}")
        zone_name = zone.get("name", f"Zone {i+1}")
        floor_area = zone.get("floor_area_sqft", 1000)

        # Autosize for this specific zone
        capacity = AutoSizer.calculate_hvac_capacity(
            floor_area_sqft=floor_area,
            building_type="multifamily",
            climate_zone=climate_zone
        )

        # Create group (one zone per group)
        group = {
            "name": f"{zone_name} - Individual DU",
            "system_type": system_type,
            "zone_ids": [zone_id],
            "total_area_sqft": floor_area,
            "autosized_capacity": capacity
        }

        st.session_state.hvac_zone_groups.append(group)


def create_central_systems(model: Dict, zones: List[Dict], num_systems: int, system_type: str, building_type: str, climate_zone: str):
    """Create central system groups serving all zones."""
    from gui.utils.autosizing import AutoSizer

    # Initialize session state groups if needed
    if "hvac_zone_groups" not in st.session_state:
        st.session_state.hvac_zone_groups = []

    # Clear existing groups
    st.session_state.hvac_zone_groups = []

    # Calculate total area
    total_area = sum(z.get("floor_area_sqft", 0) for z in zones)
    area_per_system = total_area / num_systems

    # Divide zones among systems
    zones_per_system = len(zones) // num_systems
    extra_zones = len(zones) % num_systems

    start_idx = 0
    for i in range(num_systems):
        # Distribute extra zones to first systems
        num_zones = zones_per_system + (1 if i < extra_zones else 0)
        system_zones = zones[start_idx:start_idx + num_zones]
        start_idx += num_zones

        system_area = sum(z.get("floor_area_sqft", 0) for z in system_zones)

        capacity = AutoSizer.calculate_hvac_capacity(
            floor_area_sqft=system_area,
            building_type=building_type,
            climate_zone=climate_zone
        )

        # Create group
        group = {
            "name": f"Central System {i+1}",
            "system_type": system_type,
            "zone_ids": [z.get("id", f"zone_{j}") for j, z in enumerate(system_zones)],
            "total_area_sqft": system_area,
            "autosized_capacity": capacity
        }

        st.session_state.hvac_zone_groups.append(group)


def create_one_system_per_zone(model: Dict, zones: List[Dict], system_type: str, building_type: str, climate_zone: str):
    """Create one system per zone (NR)."""
    create_individual_du_systems(model, zones, system_type, climate_zone)  # Same logic


def create_systems_from_auto_groups(model: Dict, auto_groups: Dict[str, List[Dict]], building_type: str, climate_zone: str):
    """Create groups in session state from auto-detected groups."""
    from gui.utils.autosizing import AutoSizer

    print(f"\n[DEBUG] create_systems_from_auto_groups called")
    print(f"[DEBUG] Building type: {building_type}, Climate zone: {climate_zone}")
    print(f"[DEBUG] Number of auto-detected groups: {len(auto_groups)}")

    # Initialize session state groups if needed
    if "hvac_zone_groups" not in st.session_state:
        st.session_state.hvac_zone_groups = []
        print(f"[DEBUG] Initialized hvac_zone_groups in session state")

    # Get suggested system types
    suggested_types = get_suggested_hvac_types(building_type)
    print(f"[DEBUG] Suggested system types: {suggested_types}")

    # Clear existing groups
    st.session_state.hvac_zone_groups = []
    print(f"[DEBUG] Cleared existing groups")

    for group_name, group_zones in auto_groups.items():
        print(f"\n[DEBUG] Processing group: {group_name}")
        print(f"[DEBUG]   Zones in group: {len(group_zones)}")

        total_area = sum(z.get("floor_area_sqft", 0) for z in group_zones)
        print(f"[DEBUG]   Total area: {total_area:,.0f} sqft")

        # Calculate capacity
        capacity = AutoSizer.calculate_hvac_capacity(
            floor_area_sqft=total_area,
            building_type=building_type,
            climate_zone=climate_zone
        )
        print(f"[DEBUG]   Calculated capacity: {capacity['cooling_tons']:.1f} tons")

        # Extract zone IDs properly
        zone_ids = [z.get("id", f"zone_{idx}") for idx, z in enumerate(group_zones)]
        print(f"[DEBUG]   Zone IDs: {zone_ids[:3]}..." if len(zone_ids) > 3 else f"[DEBUG]   Zone IDs: {zone_ids}")

        # Create group in session state (for Tab 3 display)
        group = {
            "name": group_name,
            "system_type": suggested_types[0],
            "zone_ids": zone_ids,
            "total_area_sqft": total_area,
            "autosized_capacity": capacity
        }

        st.session_state.hvac_zone_groups.append(group)
        print(f"[DEBUG]   Added group to session state")

    print(f"\n[DEBUG] Final count: {len(st.session_state.hvac_zone_groups)} groups in session state")
    print(f"[DEBUG] Session state groups: {[g['name'] for g in st.session_state.hvac_zone_groups]}")


def generate_systems_from_groups(model: Dict, groups: List[Dict], climate_zone: str):
    """Generate HVAC systems from manually created groups."""
    from gui.utils.autosizing import AutoSizer

    print(f"[DEBUG] generate_systems_from_groups called with {len(groups)} groups")

    if "systems" not in model:
        model["systems"] = {}
    if "hvac" not in model["systems"]:
        model["systems"]["hvac"] = []

    hvac_systems = model["systems"]["hvac"]
    initial_count = len(hvac_systems)
    print(f"[DEBUG] Initial HVAC systems count: {initial_count}")

    for group in groups:
        print(f"[DEBUG] Processing group: {group['name']}")

        # Use autosized capacity if available, otherwise calculate
        if "autosized_capacity" in group:
            capacity = group["autosized_capacity"]
            print(f"[DEBUG] Using autosized capacity: {capacity['cooling_tons']:.1f} tons")
        else:
            capacity = AutoSizer.calculate_hvac_capacity(
                floor_area_sqft=group["total_area_sqft"],
                building_type="warehouse",  # Default, should get from model
                climate_zone=climate_zone
            )
            print(f"[DEBUG] Calculated capacity: {capacity['cooling_tons']:.1f} tons")

        system = {
            "id": f"hvac_{group['name'].lower().replace(' ', '_')}",
            "name": f"{group['name']} HVAC",
            "system_type": group["system_type"],
            "zone_refs": group["zone_ids"],  # Used by exporter for zone linkages
            "served_zones": group["zone_ids"],  # Keep for backward compatibility
            "served_area_sqft": group["total_area_sqft"],
            "cooling_capacity_kw": capacity["cooling_capacity_kw"],
            "heating_capacity_kw": capacity["heating_capacity_kw"],
            "cooling_tons": capacity["cooling_tons"],
            "airflow_cfm": capacity["airflow_cfm"],
            "sizing_method": "autosized_manual_group"
        }

        hvac_systems.append(system)
        print(f"[DEBUG] Added system: {system['id']}")

    final_count = len(hvac_systems)
    print(f"[DEBUG] Final HVAC systems count: {final_count} (added {final_count - initial_count})")

    # Explicitly update session state
    if "active_model" in st.session_state:
        st.session_state.active_model["systems"]["hvac"] = hvac_systems
        print(f"[DEBUG] Updated st.session_state.active_model with {len(hvac_systems)} HVAC systems")
