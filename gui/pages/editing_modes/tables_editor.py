"""
Tables/Forms Editor Mode
Form-based editing with expandable tables for each model component.
"""

import streamlit as st
import json
import sys
from pathlib import Path
from typing import Dict, Any, List, Optional
import copy

# Add project root to path
ROOT = Path(__file__).resolve().parent.parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Add explorer_gui to path
EXPLORER_GUI = ROOT / "explorer_gui"
if str(EXPLORER_GUI) not in sys.path:
    sys.path.insert(0, str(EXPLORER_GUI))

# Import autosizing utilities
try:
    from explorer_gui.utils.autosizing import AutoSizer, autosize_hvac_for_model, autosize_dhw_for_model
    AUTOSIZING_AVAILABLE = True
except ImportError:
    AUTOSIZING_AVAILABLE = False


def handle_tables_editor(model: Dict[str, Any]):
    """Tables/Forms editing mode handler."""
    st.header("📊 Tables/Forms Editor Mode")
    st.caption("Edit zones, surfaces, openings, systems, and catalogs using forms and tables")

    # Create tabs for different editing sections
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "📦 Project Info",
        "🏢 Zones",
        "🧱 Surfaces",
        "🪟 Openings",
        "⚙️ Systems",
        "📚 Catalogs"
    ])

    with tab1:
        edit_project_info(model)

    with tab2:
        edit_zones(model)

    with tab3:
        edit_surfaces(model)

    with tab4:
        edit_openings(model)

    with tab5:
        edit_systems(model)

    with tab6:
        edit_catalogs(model)

    # Global actions
    st.divider()
    col1, col2, col3 = st.columns([1, 1, 3])

    with col1:
        if st.button("💾 Save Changes", type="primary", use_container_width=True):
            # Changes are saved in real-time to session_state.active_model
            st.success("✅ Changes saved to active model!")
            st.info("Export your model to save to file.")

    with col2:
        if st.button("🔄 Reload Original", use_container_width=True):
            if "original_model" in st.session_state:
                st.session_state.active_model = copy.deepcopy(st.session_state.original_model)
                st.success("✅ Model reloaded from original!")
                st.rerun()
            else:
                st.error("No original model found in session.")


def edit_project_info(model: Dict[str, Any]):
    """Edit project-level information."""
    st.subheader("Project Information")

    if "project" not in model:
        model["project"] = {}

    project = model["project"]

    # Edit project name
    col1, col2 = st.columns(2)

    with col1:
        name = st.text_input(
            "Project Name",
            value=project.get("name", ""),
            key="edit_project_name"
        )
        if name != project.get("name"):
            project["name"] = name

    with col2:
        description = st.text_area(
            "Description",
            value=project.get("description", ""),
            key="edit_project_desc",
            height=100
        )
        if description != project.get("description"):
            project["description"] = description

    # Location info
    st.subheader("Location")
    if "location" not in project:
        project["location"] = {}

    location = project["location"]

    col1, col2, col3 = st.columns(3)

    with col1:
        city = st.text_input(
            "City",
            value=location.get("city", ""),
            key="edit_location_city"
        )
        location["city"] = city

    with col2:
        latitude = st.number_input(
            "Latitude",
            value=float(location.get("latitude", 0.0)),
            format="%.6f",
            key="edit_location_lat"
        )
        location["latitude"] = latitude

    with col3:
        longitude = st.number_input(
            "Longitude",
            value=float(location.get("longitude", 0.0)),
            format="%.6f",
            key="edit_location_lon"
        )
        location["longitude"] = longitude


def edit_zones(model: Dict[str, Any]):
    """Edit zones."""
    st.subheader("Zones")

    if "geometry" not in model:
        model["geometry"] = {}
    if "zones" not in model["geometry"]:
        model["geometry"]["zones"] = []

    zones = model["geometry"]["zones"]

    if not zones:
        st.info("No zones found in model. Import a model with zones to edit them.")
        return

    # Zone selector
    zone_names = [f"{z.get('name', z.get('id', f'Zone {i}'))}" for i, z in enumerate(zones)]

    col1, col2 = st.columns([3, 1])
    with col1:
        selected_zone_idx = st.selectbox(
            "Select Zone to Edit",
            range(len(zones)),
            format_func=lambda i: zone_names[i],
            key="edit_zone_selector"
        )

    with col2:
        if st.button("➕ Add Zone", use_container_width=True):
            new_zone = {
                "id": f"zone_{len(zones) + 1}",
                "name": f"New Zone {len(zones) + 1}",
                "zone_type": "conditioned",
                "floor_area_m2": 0.0,
                "volume_m3": 0.0,
                "multiplier": 1
            }
            zones.append(new_zone)
            st.success(f"✅ Added new zone: {new_zone['name']}")
            st.rerun()

    if selected_zone_idx is not None and selected_zone_idx < len(zones):
        zone = zones[selected_zone_idx]

        st.divider()
        st.markdown(f"### Editing: {zone.get('name', 'Unknown Zone')}")

        col1, col2 = st.columns(2)

        with col1:
            zone["id"] = st.text_input("Zone ID", value=zone.get("id", ""), key=f"zone_id_{selected_zone_idx}")
            zone["name"] = st.text_input("Zone Name", value=zone.get("name", ""), key=f"zone_name_{selected_zone_idx}")
            zone["zone_type"] = st.selectbox(
                "Zone Type",
                ["conditioned", "unconditioned", "plenum", "attic", "crawlspace", "garage"],
                index=["conditioned", "unconditioned", "plenum", "attic", "crawlspace", "garage"].index(
                    zone.get("zone_type", "conditioned")
                ) if zone.get("zone_type") in ["conditioned", "unconditioned", "plenum", "attic", "crawlspace", "garage"] else 0,
                key=f"zone_type_{selected_zone_idx}"
            )

        with col2:
            zone["floor_area_m2"] = st.number_input(
                "Floor Area (m²)",
                value=float(zone.get("floor_area_m2") or 0.0),
                min_value=0.0,
                format="%.2f",
                key=f"zone_area_{selected_zone_idx}"
            )
            zone["volume_m3"] = st.number_input(
                "Volume (m³)",
                value=float(zone.get("volume_m3") or 0.0),
                min_value=0.0,
                format="%.2f",
                key=f"zone_volume_{selected_zone_idx}"
            )
            zone["multiplier"] = st.number_input(
                "Multiplier",
                value=int(zone.get("multiplier") or 1),
                min_value=1,
                key=f"zone_mult_{selected_zone_idx}"
            )

        # Delete zone button
        if st.button(f"🗑️ Delete Zone: {zone.get('name')}", type="secondary", use_container_width=True):
            zones.pop(selected_zone_idx)
            st.success(f"✅ Deleted zone")
            st.rerun()


def edit_surfaces(model: Dict[str, Any]):
    """Edit surfaces."""
    st.subheader("Surfaces")

    if "geometry" not in model or "surfaces" not in model["geometry"]:
        st.info("No surfaces found in model.")
        return

    surfaces_data = model["geometry"]["surfaces"]

    # Handle both dict format (walls/roofs/floors) and list format
    if isinstance(surfaces_data, dict):
        surface_type = st.selectbox(
            "Surface Category",
            ["walls", "roofs", "floors"],
            key="surface_category_selector"
        )

        if surface_type not in surfaces_data:
            surfaces_data[surface_type] = []

        surfaces = surfaces_data[surface_type]

    elif isinstance(surfaces_data, list):
        surfaces = surfaces_data
        surface_type = "all"
    else:
        st.error("Invalid surfaces data format")
        return

    if not surfaces:
        st.info(f"No {surface_type} found in model.")
        return

    # Surface selector
    surface_names = [f"{s.get('name', s.get('id', f'Surface {i}'))}" for i, s in enumerate(surfaces)]

    selected_surface_idx = st.selectbox(
        "Select Surface to Edit",
        range(len(surfaces)),
        format_func=lambda i: surface_names[i],
        key="edit_surface_selector"
    )

    if selected_surface_idx is not None and selected_surface_idx < len(surfaces):
        surface = surfaces[selected_surface_idx]

        st.divider()
        st.markdown(f"### Editing: {surface.get('name', 'Unknown Surface')}")

        col1, col2 = st.columns(2)

        with col1:
            surface["id"] = st.text_input("Surface ID", value=surface.get("id", ""), key=f"surf_id_{selected_surface_idx}")
            surface["name"] = st.text_input("Surface Name", value=surface.get("name", ""), key=f"surf_name_{selected_surface_idx}")
            surface["surface_type"] = st.selectbox(
                "Surface Type",
                ["wall", "roof", "floor", "ceiling", "partition", "exposed_floor"],
                index=["wall", "roof", "floor", "ceiling", "partition", "exposed_floor"].index(
                    surface.get("surface_type", "wall")
                ) if surface.get("surface_type") in ["wall", "roof", "floor", "ceiling", "partition", "exposed_floor"] else 0,
                key=f"surf_type_{selected_surface_idx}"
            )

        with col2:
            surface["area_m2"] = st.number_input(
                "Area (m²)",
                value=float(surface.get("area_m2") or 0.0),
                min_value=0.0,
                format="%.2f",
                key=f"surf_area_{selected_surface_idx}"
            )
            surface["tilt_deg"] = st.number_input(
                "Tilt (degrees)",
                value=float(surface.get("tilt_deg") or 0.0),
                min_value=0.0,
                max_value=180.0,
                format="%.1f",
                key=f"surf_tilt_{selected_surface_idx}"
            )
            surface["azimuth_deg"] = st.number_input(
                "Azimuth (degrees)",
                value=float(surface.get("azimuth_deg") or 0.0),
                min_value=0.0,
                max_value=360.0,
                format="%.1f",
                key=f"surf_azimuth_{selected_surface_idx}"
            )

        # Construction reference
        surface["construction_id"] = st.text_input(
            "Construction ID",
            value=surface.get("construction_id", ""),
            key=f"surf_const_{selected_surface_idx}"
        )


def edit_openings(model: Dict[str, Any]):
    """Edit openings (windows, doors, skylights)."""
    st.subheader("Openings")

    if "geometry" not in model or "openings" not in model["geometry"]:
        st.info("No openings found in model.")
        return

    openings_data = model["geometry"]["openings"]

    # Handle dict format (windows/doors/skylights)
    if isinstance(openings_data, dict):
        opening_type = st.selectbox(
            "Opening Category",
            ["windows", "doors", "skylights"],
            key="opening_category_selector"
        )

        if opening_type not in openings_data:
            openings_data[opening_type] = []

        openings = openings_data[opening_type]

    elif isinstance(openings_data, list):
        openings = openings_data
        opening_type = "all"
    else:
        st.error("Invalid openings data format")
        return

    if not openings:
        st.info(f"No {opening_type} found in model.")
        return

    # Opening selector
    opening_names = [f"{o.get('name', o.get('id', f'Opening {i}'))}" for i, o in enumerate(openings)]

    selected_opening_idx = st.selectbox(
        "Select Opening to Edit",
        range(len(openings)),
        format_func=lambda i: opening_names[i],
        key="edit_opening_selector"
    )

    if selected_opening_idx is not None and selected_opening_idx < len(openings):
        opening = openings[selected_opening_idx]

        st.divider()
        st.markdown(f"### Editing: {opening.get('name', 'Unknown Opening')}")

        col1, col2 = st.columns(2)

        with col1:
            opening["id"] = st.text_input("Opening ID", value=opening.get("id", ""), key=f"open_id_{selected_opening_idx}")
            opening["name"] = st.text_input("Opening Name", value=opening.get("name", ""), key=f"open_name_{selected_opening_idx}")
            opening["opening_type"] = st.selectbox(
                "Opening Type",
                ["window", "door", "skylight"],
                index=["window", "door", "skylight"].index(
                    opening.get("opening_type", "window")
                ) if opening.get("opening_type") in ["window", "door", "skylight"] else 0,
                key=f"open_type_{selected_opening_idx}"
            )

        with col2:
            opening["area_m2"] = st.number_input(
                "Area (m²)",
                value=float(opening.get("area_m2") or 0.0),
                min_value=0.0,
                format="%.2f",
                key=f"open_area_{selected_opening_idx}"
            )
            opening["parent_surface_id"] = st.text_input(
                "Parent Surface ID",
                value=opening.get("parent_surface_id", ""),
                key=f"open_parent_{selected_opening_idx}"
            )
            opening["window_type_id"] = st.text_input(
                "Window Type ID",
                value=opening.get("window_type_id", ""),
                key=f"open_wintype_{selected_opening_idx}"
            )


def edit_systems(model: Dict[str, Any]):
    """Edit HVAC, DHW, PV, and battery systems."""
    st.subheader("Systems")

    if "systems" not in model:
        model["systems"] = {}

    systems = model["systems"]

    # System type selector
    system_type = st.selectbox(
        "System Type",
        ["hvac", "dhw", "pv", "battery"],
        format_func=lambda x: {
            "hvac": "HVAC Systems",
            "dhw": "Domestic Hot Water",
            "pv": "PV Arrays",
            "battery": "Battery Systems"
        }[x],
        key="system_type_selector"
    )

    if system_type not in systems:
        systems[system_type] = []

    system_list = systems[system_type]

    if not system_list:
        st.info(f"No {system_type.upper()} systems found in model.")

        if st.button(f"➕ Add {system_type.upper()} System"):
            new_system = {
                "id": f"{system_type}_{len(system_list) + 1}",
                "name": f"New {system_type.upper()} System {len(system_list) + 1}",
                "system_type": system_type
            }
            system_list.append(new_system)
            st.success(f"✅ Added new {system_type} system")
            st.rerun()
        return

    # System selector
    system_names = [f"{s.get('name', s.get('id', f'System {i}'))}" for i, s in enumerate(system_list)]

    selected_system_idx = st.selectbox(
        "Select System to Edit",
        range(len(system_list)),
        format_func=lambda i: system_names[i],
        key="edit_system_selector"
    )

    if selected_system_idx is not None and selected_system_idx < len(system_list):
        system = system_list[selected_system_idx]

        st.divider()
        st.markdown(f"### Editing: {system.get('name', 'Unknown System')}")

        # Common fields
        system["id"] = st.text_input("System ID", value=system.get("id", ""), key=f"sys_id_{selected_system_idx}")
        system["name"] = st.text_input("System Name", value=system.get("name", ""), key=f"sys_name_{selected_system_idx}")

        # Type-specific editing
        if system_type == "hvac":
            edit_hvac_system(model, system, selected_system_idx)
        elif system_type == "dhw":
            edit_dhw_system(model, system, selected_system_idx)
        else:
            # For PV and battery, show JSON editor
            st.markdown("**System Properties (JSON)**")
            edited_json = st.text_area(
                "Edit JSON",
                value=json.dumps(system, indent=2),
                height=300,
                key=f"sys_json_{selected_system_idx}"
            )

            if st.button("💾 Update from JSON"):
                try:
                    updated_system = json.loads(edited_json)
                    system_list[selected_system_idx] = updated_system
                    st.success("✅ System updated from JSON")
                    st.rerun()
                except json.JSONDecodeError as e:
                    st.error(f"❌ Invalid JSON: {e}")


def edit_hvac_system(model: Dict[str, Any], system: Dict[str, Any], idx: int):
    """Edit HVAC system with autosizing option."""
    st.markdown("#### HVAC System Properties")

    col1, col2 = st.columns(2)

    with col1:
        system["system_type"] = st.text_input(
            "System Type (e.g., heat_pump, split_system)",
            value=system.get("system_type", ""),
            key=f"hvac_systype_{idx}"
        )

        cooling_capacity = st.number_input(
            "Cooling Capacity (kW)",
            value=float(system.get("cooling_capacity_kw") or 0.0),
            min_value=0.0,
            format="%.2f",
            key=f"hvac_cooling_kw_{idx}"
        )
        system["cooling_capacity_kw"] = cooling_capacity

        heating_capacity = st.number_input(
            "Heating Capacity (kW)",
            value=float(system.get("heating_capacity_kw") or 0.0),
            min_value=0.0,
            format="%.2f",
            key=f"hvac_heating_kw_{idx}"
        )
        system["heating_capacity_kw"] = heating_capacity

    with col2:
        cooling_seer2 = st.number_input(
            "Cooling SEER2",
            value=float(system.get("cooling_efficiency_seer2") or system.get("cooling_efficiency_seer") or 14.0),
            min_value=0.0,
            format="%.1f",
            key=f"hvac_seer2_{idx}"
        )
        system["cooling_efficiency_seer2"] = cooling_seer2

        heating_hspf2 = st.number_input(
            "Heating HSPF2",
            value=float(system.get("heating_efficiency_hspf2") or system.get("heating_efficiency_hspf") or 7.5),
            min_value=0.0,
            format="%.1f",
            key=f"hvac_hspf2_{idx}"
        )
        system["heating_efficiency_hspf2"] = heating_hspf2

    # Autosizing section
    if AUTOSIZING_AVAILABLE:
        st.divider()
        st.markdown("#### 🔧 Autosizing")

        zones = model.get('zones', [])
        if not zones:
            zones = model.get('building', {}).get('zones', [])

        if zones:
            with st.expander("Calculate Capacities from Zone Geometry", expanded=False):
                col_a, col_b = st.columns(2)

                with col_a:
                    building_type = st.selectbox(
                        "Building Type",
                        ["multifamily_residential", "commercial_office", "warehouse_industrial"],
                        key=f"hvac_autosize_bldg_{idx}"
                    )

                    climate_zone = st.selectbox(
                        "California Climate Zone",
                        ["1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11", "12", "13", "14", "15", "16"],
                        index=3,
                        key=f"hvac_autosize_cz_{idx}"
                    )

                with col_b:
                    # Calculate total floor area
                    total_floor_area = sum(
                        zone.get("floor_area_sqft", zone.get("floor_area_sf", zone.get("area", 0)))
                        for zone in zones
                    )
                    st.metric("Total Floor Area", f"{total_floor_area:,.0f} sq ft")

                if st.button("🔧 Calculate & Apply", key=f"hvac_autosize_btn_{idx}", type="primary"):
                    # Calculate capacity
                    capacity = AutoSizer.calculate_hvac_capacity(
                        floor_area_sqft=total_floor_area,
                        building_type=building_type,
                        climate_zone=climate_zone
                    )

                    # Apply to system
                    system["cooling_capacity_kw"] = capacity["cooling_capacity_kw"]
                    system["heating_capacity_kw"] = capacity["heating_capacity_kw"]
                    system["cooling_capacity_btu"] = capacity["cooling_capacity_btu"]
                    system["heating_capacity_btu"] = capacity["heating_capacity_btu"]
                    system["cooling_tons"] = capacity["cooling_tons"]
                    system["airflow_cfm"] = capacity["airflow_cfm"]
                    system["sizing_method"] = "autosized"
                    system["sizing_note"] = f"Autosized for {capacity['climate_classification']} climate zone"

                    st.success(f"✅ Autosized: {capacity['cooling_capacity_kw']:.2f} kW cooling, {capacity['heating_capacity_kw']:.2f} kW heating")
                    st.rerun()
        else:
            st.info("No zones found in model - cannot autosize without geometry")

    # Advanced properties
    with st.expander("🔧 Advanced Properties"):
        st.json(system)


def edit_dhw_system(model: Dict[str, Any], system: Dict[str, Any], idx: int):
    """Edit DHW system with autosizing option."""
    st.markdown("#### DHW System Properties")

    col1, col2 = st.columns(2)

    with col1:
        system["system_type"] = st.text_input(
            "System Type (e.g., central_with_recirculation)",
            value=system.get("system_type", ""),
            key=f"dhw_systype_{idx}"
        )

        capacity_gal = st.number_input(
            "Tank Capacity (gallons)",
            value=float(system.get("capacity_gallons") or (system.get("capacity_liters") or 150) / 3.78541),
            min_value=0.0,
            format="%.1f",
            key=f"dhw_cap_gal_{idx}"
        )
        system["capacity_gallons"] = capacity_gal
        system["capacity_liters"] = round(capacity_gal * 3.78541, 1)

        input_rating = st.number_input(
            "Input Rating (BTU/h)",
            value=float(system.get("input_rating_btu") or 100000),
            min_value=0.0,
            format="%.0f",
            key=f"dhw_input_btu_{idx}"
        )
        system["input_rating_btu"] = input_rating

    with col2:
        energy_factor = st.number_input(
            "Energy Factor",
            value=float(system.get("energy_factor") or 0.62),
            min_value=0.0,
            max_value=5.0,
            format="%.2f",
            key=f"dhw_ef_{idx}"
        )
        system["energy_factor"] = energy_factor

        fuel_type = st.selectbox(
            "Fuel Type",
            ["Gas", "Electric", "Propane"],
            index=["Gas", "Electric", "Propane"].index(system.get("fuel_type", "Gas")) if system.get("fuel_type") in ["Gas", "Electric", "Propane"] else 0,
            key=f"dhw_fuel_{idx}"
        )
        system["fuel_type"] = fuel_type

    # Autosizing section
    if AUTOSIZING_AVAILABLE:
        st.divider()
        st.markdown("#### 🔧 Autosizing")

        zones = model.get('zones', [])
        if not zones:
            zones = model.get('building', {}).get('zones', [])

        if zones:
            with st.expander("Calculate DHW Capacity from Building Parameters", expanded=False):
                building_type = st.selectbox(
                    "Building Type",
                    ["multifamily", "commercial_office", "warehouse"],
                    key=f"dhw_autosize_bldg_{idx}"
                )

                col_a, col_b = st.columns(2)

                with col_a:
                    if building_type == "multifamily":
                        num_units = st.number_input(
                            "Number of Dwelling Units",
                            min_value=1,
                            max_value=1000,
                            value=20,
                            key=f"dhw_autosize_units_{idx}"
                        )
                        bedrooms_per_unit = st.number_input(
                            "Average Bedrooms per Unit",
                            min_value=0,
                            max_value=4,
                            value=2,
                            key=f"dhw_autosize_br_{idx}"
                        )
                    else:
                        num_units = None
                        bedrooms_per_unit = None
                        num_employees = st.number_input(
                            "Number of Employees",
                            min_value=1,
                            max_value=10000,
                            value=50,
                            key=f"dhw_autosize_emp_{idx}"
                        )

                with col_b:
                    total_floor_area = sum(
                        zone.get("floor_area_sqft", zone.get("floor_area_sf", zone.get("area", 0)))
                        for zone in zones
                    )
                    st.metric("Total Floor Area", f"{total_floor_area:,.0f} sq ft")

                if st.button("🔧 Calculate & Apply", key=f"dhw_autosize_btn_{idx}", type="primary"):
                    # Calculate capacity
                    capacity = AutoSizer.calculate_dhw_capacity(
                        building_type=building_type,
                        num_units=num_units if building_type == "multifamily" else None,
                        num_bedrooms_per_unit=bedrooms_per_unit if building_type == "multifamily" else None,
                        num_employees=num_employees if building_type != "multifamily" else None,
                        floor_area_sqft=total_floor_area if total_floor_area > 0 else None
                    )

                    # Apply to system
                    system["capacity_gallons"] = capacity["tank_capacity_gallons"]
                    system["capacity_liters"] = capacity["tank_capacity_liters"]
                    system["input_rating_btu"] = capacity["input_rating_btu"]
                    system["recovery_rate_gph"] = capacity["recovery_rate_gph"]
                    system["sizing_method"] = "autosized"
                    system["sizing_note"] = capacity["sizing_method"]

                    st.success(f"✅ Autosized: {capacity['tank_capacity_gallons']:.0f} gal tank, {capacity['input_rating_btu']:,.0f} BTU/h input")
                    st.rerun()
        else:
            st.info("No zones found in model - cannot autosize without geometry")

    # Advanced properties
    with st.expander("🔧 Advanced Properties"):
        st.json(system)


def edit_catalogs(model: Dict[str, Any]):
    """Edit catalog items (window types, constructions, materials)."""
    st.subheader("Catalogs")

    if "catalogs" not in model:
        model["catalogs"] = {}

    catalogs = model["catalogs"]

    # Catalog type selector
    catalog_type = st.selectbox(
        "Catalog Type",
        ["window_types", "construction_types", "material_types", "du_types"],
        format_func=lambda x: {
            "window_types": "Window Types",
            "construction_types": "Construction Types",
            "material_types": "Material Types",
            "du_types": "Dwelling Unit Types"
        }.get(x, x),
        key="catalog_type_selector"
    )

    if catalog_type not in catalogs:
        catalogs[catalog_type] = []

    catalog_items = catalogs[catalog_type]

    if not catalog_items:
        st.info(f"No {catalog_type.replace('_', ' ')} found in model.")
        return

    # Item selector
    item_names = [f"{item.get('name', item.get('id', f'Item {i}'))}" for i, item in enumerate(catalog_items)]

    selected_item_idx = st.selectbox(
        "Select Item to Edit",
        range(len(catalog_items)),
        format_func=lambda i: item_names[i],
        key="edit_catalog_selector"
    )

    if selected_item_idx is not None and selected_item_idx < len(catalog_items):
        item = catalog_items[selected_item_idx]

        st.divider()
        st.markdown(f"### Editing: {item.get('name', 'Unknown Item')}")

        # Show raw JSON for editing
        st.markdown("**Item Properties (JSON)**")
        edited_json = st.text_area(
            "Edit JSON",
            value=json.dumps(item, indent=2),
            height=300,
            key=f"catalog_json_{selected_item_idx}"
        )

        if st.button("💾 Update from JSON"):
            try:
                updated_item = json.loads(edited_json)
                catalog_items[selected_item_idx] = updated_item
                st.success("✅ Item updated from JSON")
                st.rerun()
            except json.JSONDecodeError as e:
                st.error(f"❌ Invalid JSON: {e}")
