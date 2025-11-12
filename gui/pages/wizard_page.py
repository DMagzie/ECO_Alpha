"""
Model Building Wizard
Assists users in completing models that have geometry but lack systems and catalogs.
Particularly useful for GEM imports from IES VE.
"""

import streamlit as st
import json
import sys
from pathlib import Path
from typing import Dict, Any, List, Optional
import copy

# Add project root to path
ROOT = Path(__file__).resolve().parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

EXPLORER_GUI = ROOT / "gui"
if str(EXPLORER_GUI) not in sys.path:
    sys.path.insert(0, str(EXPLORER_GUI))

# Import autosizing utilities
try:
    from gui.utils.autosizing import AutoSizer, autosize_hvac_for_model, autosize_dhw_for_model
    AUTOSIZING_AVAILABLE = True
except ImportError:
    AUTOSIZING_AVAILABLE = False

# Import zone-first HVAC step
from gui.pages.wizard_hvac_zone_first import show_hvac_step_zone_first


# ===== CONSTRUCTION ASSEMBLY TEMPLATE HELPERS =====

def load_construction_templates() -> Dict[str, Any]:
    """Load construction assembly templates from JSON file."""
    template_path = Path(__file__).resolve().parent.parent / "templates" / "construction_assemblies_t24.json"
    try:
        with open(template_path, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        st.warning(f"⚠️ Construction template file not found at {template_path}")
        return {}
    except json.JSONDecodeError as e:
        st.error(f"❌ Error loading construction templates: {e}")
        return {}


def map_assembly_to_category(assembly_type: str) -> str:
    """Map wizard assembly type to template category."""
    mapping = {
        "Exterior Wall": "exterior_walls",
        "Interior Wall": "interior_walls",
        "Roof": "roofs",
        "Floor": "floors",
        "Foundation": "floors"
    }
    return mapping.get(assembly_type, "exterior_walls")


def find_matching_assembly(category_assemblies: Dict, structure_type: str, climate_zone: str) -> Optional[Dict]:
    """Find assembly matching structure type and climate zone."""
    for assembly_id, assembly in category_assemblies.items():
        if (assembly.get("structure_type") == structure_type and
            climate_zone in assembly.get("climate_zones", [])):
            return assembly
    return None


def find_material_definition(materials_dict: Dict, material_id: str) -> Optional[Dict]:
    """Find material definition by ID across all material categories."""
    for category in materials_dict.values():
        if isinstance(category, dict) and material_id in category:
            return category[material_id]
    return None


def map_to_const_type(assembly_type: str) -> str:
    """Map assembly type to CBECC construction type."""
    mapping = {
        "Exterior Wall": "wall",
        "Interior Wall": "partition",
        "Roof": "roof",
        "Floor": "floor",
        "Foundation": "floor"
    }
    return mapping.get(assembly_type, "wall")


# ===== END CONSTRUCTION HELPERS =====


# ===== SCHEDULE TEMPLATE HELPERS =====

def load_schedule_templates() -> Dict[str, Any]:
    """Load operation schedule templates from JSON file."""
    # Path resolution: wizard_page.py is in gui/pages/, so go up to project root
    template_path = Path(__file__).resolve().parent.parent.parent / "templates" / "schedules_t24.json"
    try:
        with open(template_path, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        st.warning(f"⚠️ Schedule template file not found at {template_path}")
        return {}
    except json.JSONDecodeError as e:
        st.error(f"❌ Error loading schedule templates: {e}")
        return {}


def determine_building_type_for_schedules(building_type: str, space_function: str = None) -> str:
    """Map building/space type to schedule template category."""
    # Map common building types to schedule templates
    building_type_lower = building_type.lower() if building_type else ""
    space_lower = space_function.lower() if space_function else ""

    # Check space function first (more specific)
    if space_lower:
        if "office" in space_lower:
            return "office_small"
        elif "warehouse" in space_lower or "storage" in space_lower:
            return "warehouse"
        elif "retail" in space_lower or "sales" in space_lower:
            return "retail"
        elif "restaurant" in space_lower or "dining" in space_lower or "kitchen" in space_lower:
            return "restaurant"

    # Fall back to building type
    if "office" in building_type_lower:
        return "office_small"
    elif "warehouse" in building_type_lower or "distribution" in building_type_lower:
        return "warehouse"
    elif "retail" in building_type_lower or "store" in building_type_lower:
        return "retail"
    elif "restaurant" in building_type_lower or "food" in building_type_lower:
        return "restaurant"

    # Default to office for unrecognized types
    return "office_small"


def assign_schedules_to_zones(model: Dict[str, Any], building_type: str) -> None:
    """Auto-assign schedules to zones based on building type and space function."""
    templates = load_schedule_templates()
    if not templates:
        st.warning("⚠️ Could not load schedule templates. Schedules will not be assigned.")
        return

    geometry = model.get("geometry", {})
    zones = geometry.get("zones", [])

    # Ensure catalogs.schedules exists
    if "catalogs" not in model:
        model["catalogs"] = {}
    if "schedules" not in model["catalogs"]:
        model["catalogs"]["schedules"] = []

    schedules_catalog = model["catalogs"]["schedules"]
    created_schedules = {}  # Track created schedules to avoid duplicates

    for zone in zones:
        # Determine which schedule set to use
        space_function = zone.get("space_function", "")
        schedule_type = determine_building_type_for_schedules(building_type, space_function)

        if schedule_type not in templates:
            continue

        schedule_set = templates[schedule_type]

        # Create schedules for this zone if not already created
        if schedule_type not in created_schedules:
            created_schedules[schedule_type] = {}

            for schedule_name, schedule_data in schedule_set.items():
                if schedule_name.startswith("_"):  # Skip metadata
                    continue

                schedule_id = schedule_data.get("id", f"sch_{schedule_type}_{schedule_name}")

                # Add to catalog
                schedule_obj = {
                    "id": schedule_id,
                    "name": schedule_data.get("name", f"{schedule_type.title()} {schedule_name.title()}"),
                    "type": schedule_data.get("type", "fraction"),
                    "schedule_type": schedule_name,
                    "building_type": schedule_type,
                    "weekday": schedule_data.get("weekday", []),
                    "saturday": schedule_data.get("saturday", []),
                    "sunday": schedule_data.get("sunday", []),
                    "holiday": schedule_data.get("holiday", [])
                }

                schedules_catalog.append(schedule_obj)
                created_schedules[schedule_type][schedule_name] = schedule_id

        # Assign schedule references to zone (both at top level and in annotation for export)
        if "schedules" not in zone:
            zone["schedules"] = {}

        schedule_refs = created_schedules[schedule_type]
        zone["schedules"]["occupancy"] = schedule_refs.get("occupancy")
        zone["schedules"]["lighting"] = schedule_refs.get("lighting")
        zone["schedules"]["equipment"] = schedule_refs.get("equipment")
        zone["schedules"]["heating_setpoint"] = schedule_refs.get("heating_setpoint")
        zone["schedules"]["cooling_setpoint"] = schedule_refs.get("cooling_setpoint")
        zone["schedules"]["ventilation"] = schedule_refs.get("ventilation")

        # Add kitchen exhaust for restaurant zones if available
        if "kitchen_exhaust" in schedule_refs:
            zone["schedules"]["kitchen_exhaust"] = schedule_refs["kitchen_exhaust"]

        # Also store in annotation for exporter
        if "annotation" not in zone:
            zone["annotation"] = {}
        zone["annotation"]["schedules"] = zone["schedules"]


# ===== END SCHEDULE HELPERS =====


def handle_wizard():
    """Main wizard handler."""
    st.title("🧙 Model Building Wizard")
    st.caption("Build complete models from geometry-only imports (GEM, simplified CIBD22X, etc.)")

    # Check if we have an active model
    if "active_model" not in st.session_state or st.session_state.active_model is None:
        st.warning("⚠️ No active model loaded. Please import a model first.")
        st.info("💡 **Tip**: Import a GEM file from IES VE to use this wizard.")

        col1, col2 = st.columns(2)
        with col1:
            if st.button("📁 Go to Import Page", use_container_width=True):
                st.session_state.nav_main = "Import"
                st.rerun()
        return

    model = st.session_state.active_model

    # Initialize wizard state
    if "wizard_step" not in st.session_state:
        st.session_state.wizard_step = 0

    if "wizard_data" not in st.session_state:
        st.session_state.wizard_data = {}

    # Analyze model completeness
    analysis = analyze_model_completeness(model)

    # Show wizard based on current step
    if st.session_state.wizard_step == 0:
        show_overview_step(model, analysis)
    elif st.session_state.wizard_step == 1:
        show_window_types_step(model, analysis)
    elif st.session_state.wizard_step == 2:
        show_constructions_step(model, analysis)
    elif st.session_state.wizard_step == 3:
        # Step 3 is now HVAC (Materials step removed - moved to constructions)
        show_hvac_step_zone_first(model, analysis)
    elif st.session_state.wizard_step == 4:
        show_dhw_step(model, analysis)
    elif st.session_state.wizard_step == 5:
        show_review_step(model, analysis)


def analyze_model_completeness(model: Dict[str, Any]) -> Dict[str, Any]:
    """Analyze what the model has and what it's missing."""

    geometry = model.get("geometry", {})
    catalogs = model.get("catalogs", {})
    systems = model.get("systems", {})

    # Count geometry elements
    zones = geometry.get("zones", [])

    surfaces_data = geometry.get("surfaces", {})
    if isinstance(surfaces_data, dict):
        surfaces = (surfaces_data.get("walls", []) +
                   surfaces_data.get("roofs", []) +
                   surfaces_data.get("floors", []))
    elif isinstance(surfaces_data, list):
        surfaces = surfaces_data
    else:
        surfaces = []

    openings_data = geometry.get("openings", {})
    if isinstance(openings_data, dict):
        openings = (openings_data.get("windows", []) +
                   openings_data.get("doors", []) +
                   openings_data.get("skylights", []))
    elif isinstance(openings_data, list):
        openings = openings_data
    else:
        openings = []

    # Count catalog elements
    window_types = catalogs.get("window_types", [])
    constructions = catalogs.get("construction_types", catalogs.get("constructions", []))
    materials = catalogs.get("material_types", catalogs.get("materials", []))
    schedules = catalogs.get("schedules", [])

    # Count system elements
    hvac_systems = systems.get("hvac", [])
    dhw_systems = systems.get("dhw", [])
    pv_arrays = systems.get("pv", [])

    # Check if zones have schedule assignments
    zones_with_schedules = sum(1 for z in zones if "schedules" in z and z["schedules"])

    # Determine what's missing
    has_geometry = len(zones) > 0 or len(surfaces) > 0
    has_openings = len(openings) > 0
    has_window_types = len(window_types) > 0
    has_constructions = len(constructions) > 0
    has_materials = len(materials) > 0
    has_schedules = len(schedules) > 0 and zones_with_schedules > 0
    has_hvac = len(hvac_systems) > 0
    has_dhw = len(dhw_systems) > 0

    return {
        "counts": {
            "zones": len(zones),
            "surfaces": len(surfaces),
            "openings": len(openings),
            "window_types": len(window_types),
            "constructions": len(constructions),
            "materials": len(materials),
            "schedules": len(schedules),
            "zones_with_schedules": zones_with_schedules,
            "hvac_systems": len(hvac_systems),
            "dhw_systems": len(dhw_systems),
            "pv_arrays": len(pv_arrays)
        },
        "has": {
            "geometry": has_geometry,
            "openings": has_openings,
            "window_types": has_window_types,
            "constructions": has_constructions,
            "materials": has_materials,
            "schedules": has_schedules,
            "hvac": has_hvac,
            "dhw": has_dhw
        },
        "needs": {
            "window_types": has_openings and not has_window_types,
            "constructions": len(surfaces) > 0 and not has_constructions,
            "materials": not has_materials,
            "schedules": len(zones) > 0 and not has_schedules,
            "hvac": len(zones) > 0 and not has_hvac,
            "dhw": not has_dhw
        }
    }


def show_overview_step(model: Dict[str, Any], analysis: Dict[str, Any]):
    """Step 0: Overview and detection."""
    st.header("📊 Step 1: Model Overview")

    st.markdown("""
    This wizard will help you complete your model by creating the necessary systems and catalog items.
    This is especially useful after importing GEM files from IES VE.
    """)

    # Show what we have
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("✅ What You Have")
        counts = analysis["counts"]

        if counts["zones"] > 0:
            st.success(f"🏢 **{counts['zones']}** Zones")
        if counts["surfaces"] > 0:
            st.success(f"🧱 **{counts['surfaces']}** Surfaces")
        if counts["openings"] > 0:
            st.success(f"🪟 **{counts['openings']}** Openings")
        if counts["window_types"] > 0:
            st.info(f"📐 **{counts['window_types']}** Window Types")
        if counts["constructions"] > 0:
            st.info(f"🏗️ **{counts['constructions']}** Constructions")
        if counts["hvac_systems"] > 0:
            st.info(f"❄️ **{counts['hvac_systems']}** HVAC Systems")
        if counts["dhw_systems"] > 0:
            st.info(f"🚿 **{counts['dhw_systems']}** DHW Systems")

        if not analysis["has"]["geometry"]:
            st.warning("⚠️ No geometry found in model")

    with col2:
        st.subheader("⚠️ What's Missing")
        needs = analysis["needs"]

        missing_items = []
        if needs["window_types"]:
            st.error("📐 Window Types (needed for openings)")
            missing_items.append("window_types")
        if needs["constructions"]:
            st.error("🏗️ Constructions (needed for surfaces)")
            missing_items.append("constructions")
        # Materials step removed - now part of constructions wizard
        if needs["hvac"]:
            st.error("❄️ HVAC Systems (needed for zones)")
            missing_items.append("hvac")
        if needs["dhw"]:
            st.warning("🚿 DHW Systems (recommended)")

        if not any(needs.values()):
            st.success("✅ Your model appears complete!")
            st.info("You can still use this wizard to add more elements.")

    st.divider()

    # Project Information - Building Type and Climate Zone
    st.subheader("🏗️ Project Information")
    st.caption("Establish building type and climate zone for consistent template selection and autosizing")

    col1, col2 = st.columns(2)

    with col1:
        # Get existing values from model
        current_building_type = model.get("project", {}).get("building_type", "")
        current_climate_zone = model.get("project", {}).get("climate_zone", "4")

        # Map current values to display options
        building_type_map = {
            "multifamily": "Multifamily Residential",
            "small_commercial": "Small Commercial",
            "large_commercial": "Large Commercial",
            "warehouse": "Warehouse/Industrial"
        }

        # Reverse map for selection
        display_to_key = {v: k for k, v in building_type_map.items()}

        # Determine default index
        default_type_display = building_type_map.get(current_building_type, "Warehouse/Industrial")
        type_options = list(building_type_map.values())
        default_type_idx = type_options.index(default_type_display) if default_type_display in type_options else 3

        building_type_display = st.selectbox(
            "Building Type",
            options=type_options,
            index=default_type_idx,
            help="Select the building type - affects HVAC templates, load calculations, and compliance requirements",
            key="wizard_building_type"
        )

        # Convert back to key
        building_type = display_to_key.get(building_type_display, "warehouse")

    with col2:
        climate_zones = [str(i) for i in range(1, 17)]
        default_cz_idx = 3  # CZ 4 default (San Francisco Bay Area)

        if current_climate_zone in climate_zones:
            default_cz_idx = climate_zones.index(current_climate_zone)

        climate_zone = st.selectbox(
            "California Climate Zone",
            options=climate_zones,
            index=default_cz_idx,
            help="California Title 24 climate zone (1-16) - affects load calculations and equipment sizing",
            key="wizard_climate_zone"
        )

    # Save to wizard data and model
    if "project" not in model:
        model["project"] = {}

    model["project"]["building_type"] = building_type
    model["project"]["climate_zone"] = climate_zone

    st.session_state.wizard_data["building_type"] = building_type
    st.session_state.wizard_data["climate_zone"] = climate_zone

    st.success(f"✅ Project configured as **{building_type_display}** in **Climate Zone {climate_zone}**")

    st.divider()

    # Wizard mode selection
    st.subheader("🎯 Choose Your Approach")

    wizard_mode = st.radio(
        "How would you like to proceed?",
        [
            "Quick Setup (Recommended)",
            "Step-by-Step (Detailed)",
            "Skip Wizard (Manual Editing)"
        ],
        help="Quick Setup creates basic elements automatically. Step-by-Step lets you configure each element.",
        key="wizard_mode_select"
    )

    st.session_state.wizard_data["mode"] = wizard_mode

    col1, col2, col3 = st.columns([2, 1, 1])

    with col1:
        if wizard_mode == "Quick Setup (Recommended)":
            st.info("💡 Quick Setup will create standard elements based on your geometry and common building practices.")
        elif wizard_mode == "Step-by-Step (Detailed)":
            st.info("💡 Step-by-Step mode lets you customize each element before creating it.")
        else:
            st.info("💡 Skip to manual editing if you prefer full control.")

    with col3:
        if st.button("Next ▶️", type="primary", use_container_width=True):
            if wizard_mode == "Skip Wizard (Manual Editing)":
                # Go directly to edit page
                st.session_state.nav_main = "Edit Model"
                st.rerun()
            else:
                st.session_state.wizard_step = 1
                st.rerun()


def show_window_types_step(model: Dict[str, Any], analysis: Dict[str, Any]):
    """Step 1: Create window types for openings."""
    st.header("📐 Step 2: Window Types")

    counts = analysis["counts"]
    needs = analysis["needs"]

    if not needs["window_types"]:
        st.success(f"✅ Your model already has {counts['window_types']} window types defined.")
        st.info("You can skip this step or add more window types.")
    else:
        st.warning(f"⚠️ You have {counts['openings']} openings but no window types defined.")
        st.markdown("Window types define the thermal properties (U-factor, SHGC) of windows.")

    # Quick setup mode
    if st.session_state.wizard_data.get("mode") == "Quick Setup (Recommended)":
        st.subheader("Quick Setup")

        # Get building type and climate zone from wizard data
        building_type = st.session_state.wizard_data.get("building_type", "warehouse")
        climate_zone = st.session_state.wizard_data.get("climate_zone", "4")

        st.info(f"📋 Building: {building_type.replace('_', ' ').title()} | Climate Zone: {climate_zone}")
        st.caption("Window types will be configured per T-24 2022 prescriptive requirements")

        # Window type selection
        st.markdown("### Add Window Types")
        st.caption("Select specific window types for your project. Each type has T-24 compliant values.")

        # Initialize window type counter in session state if needed
        if 'window_type_counter' not in st.session_state:
            st.session_state.window_type_counter = 0

        # Window type options with T-24 prescriptive values
        window_type_categories = {
            "Manufactured/Punched Window": {
                "description": "Standard manufactured windows, typical for residential and small commercial",
                "u_factor": 0.32,
                "shgc": 0.25,
                "vt": 0.50
            },
            "Storefront": {
                "description": "Commercial storefront system, floor to ceiling glazing",
                "u_factor": 0.46,
                "shgc": 0.25,
                "vt": 0.55
            },
            "Curtain Wall": {
                "description": "Building envelope system, exterior wall non-structural",
                "u_factor": 0.40,
                "shgc": 0.25,
                "vt": 0.60
            },
            "Spandrel Panel": {
                "description": "Opaque glazing panels between vision glass areas",
                "u_factor": 0.50,
                "shgc": 0.15,
                "vt": 0.05
            },
            "Skylight": {
                "description": "Roof-mounted glazing system",
                "u_factor": 0.55,
                "shgc": 0.30,
                "vt": 0.40
            },
            "High Performance": {
                "description": "Triple pane, low-E, exceeds prescriptive",
                "u_factor": 0.21,
                "shgc": 0.21,
                "vt": 0.45
            }
        }

        col1, col2 = st.columns([2, 1])

        with col1:
            selected_window_type = st.selectbox(
                "Window Type Category:",
                list(window_type_categories.keys()),
                key="new_window_type_category",
                help="Select the window type for your project"
            )

        with col2:
            if st.button("➕ Add Window Type", type="primary", use_container_width=True):
                wt_data = window_type_categories[selected_window_type]
                st.session_state.window_type_counter += 1
                add_window_type_from_category(
                    model,
                    selected_window_type,
                    wt_data,
                    building_type,
                    climate_zone
                )
                st.success(f"✅ Added: {selected_window_type}")
                st.rerun()

        # Show selected type details
        wt_info = window_type_categories[selected_window_type]
        with st.expander(f"ℹ️ {selected_window_type} - T24 Prescriptive Values", expanded=True):
            st.caption(wt_info["description"])
            col_a, col_b, col_c = st.columns(3)
            with col_a:
                st.metric("U-Factor", f"{wt_info['u_factor']} BTU/(hr·ft²·°F)")
            with col_b:
                st.metric("SHGC", f"{wt_info['shgc']}")
            with col_c:
                st.metric("VT", f"{wt_info['vt']}")

    else:  # Step-by-step mode
        st.subheader("Create Window Type")

        with st.form("window_type_form"):
            col1, col2 = st.columns(2)

            with col1:
                wt_name = st.text_input("Name", value="Standard Window", key="wt_name")
                wt_u_factor = st.number_input("U-Factor (BTU/hr·ft²·°F)", value=0.35, min_value=0.15, max_value=1.20, format="%.3f", help="Typical range: Single pane 0.90-1.20, Double pane 0.30-0.65, Triple pane 0.15-0.25")
                wt_shgc = st.number_input("SHGC (Solar Heat Gain Coefficient)", value=0.40, min_value=0.0, max_value=1.0, format="%.2f")

            with col2:
                wt_vt = st.number_input("VT (Visible Transmittance)", value=0.60, min_value=0.0, max_value=1.0, format="%.2f")
                wt_frame_type = st.selectbox("Frame Type", ["Metal", "Wood", "Vinyl", "Fiberglass"])
                wt_glazing_type = st.selectbox("Glazing Type", ["Single", "Double", "Triple", "Low-E"])

            submitted = st.form_submit_button("Add Window Type", type="primary")

            if submitted:
                add_window_type(model, wt_name, wt_u_factor, wt_shgc, wt_vt, wt_frame_type, wt_glazing_type)
                st.success(f"✅ Added window type: {wt_name}")
                st.rerun()

    # Show existing window types
    if "catalogs" in model and "window_types" in model["catalogs"]:
        window_types = model["catalogs"]["window_types"]
        if window_types:
            st.divider()
            st.subheader(f"Defined Window Types ({len(window_types)})")
            for wt in window_types:
                with st.expander(f"📐 {wt.get('name', 'Unknown')}"):
                    st.json(wt)

    # Navigation
    st.divider()
    col1, col2, col3 = st.columns([1, 2, 1])
    with col1:
        if st.button("◀️ Back", use_container_width=True):
            st.session_state.wizard_step = 0
            st.rerun()
    with col3:
        if st.button("Next ▶️", type="primary", use_container_width=True):
            st.session_state.wizard_step = 2
            st.rerun()


def show_constructions_step(model: Dict[str, Any], analysis: Dict[str, Any]):
    """Step 2: Create constructions for surfaces."""
    st.header("🏗️ Step 3: Construction Types")

    counts = analysis["counts"]
    needs = analysis["needs"]

    if not needs["constructions"]:
        st.success(f"✅ Your model already has {counts['constructions']} constructions defined.")
    else:
        st.warning(f"⚠️ You have {counts['surfaces']} surfaces but no constructions defined.")
        st.markdown("Constructions define the thermal properties and layer composition of walls, roofs, and floors.")

    # Quick setup mode
    if st.session_state.wizard_data.get("mode") == "Quick Setup (Recommended)":
        st.subheader("Quick Setup")

        # Get building type and climate zone from wizard data
        building_type = st.session_state.wizard_data.get("building_type", "warehouse")
        climate_zone = st.session_state.wizard_data.get("climate_zone", "4")

        st.info(f"📋 Building: {building_type.replace('_', ' ').title()} | Climate Zone: {climate_zone}")
        st.caption("Constructions will be configured per T-24 2022 prescriptive requirements")

        st.markdown("### Construction Assemblies")
        st.caption("Select structure type for each assembly type")

        # Available structure types
        structure_options = [
            "Wood Framed",
            "Metal Framed",
            "Concrete/Masonry",
            "Insulated Concrete Forms (ICF)",
            "Structural Insulated Panels (SIP)"
        ]

        # Structure type descriptions
        structure_info = {
            "Wood Framed": "Standard wood stud framing, 2x4 or 2x6 construction",
            "Metal Framed": "Steel stud framing, requires thermal break or continuous insulation",
            "Concrete/Masonry": "Cast-in-place concrete or CMU walls, requires exterior or interior insulation",
            "Insulated Concrete Forms (ICF)": "High thermal mass, excellent insulation, exceeds prescriptive",
            "Structural Insulated Panels (SIP)": "Prefabricated panels, continuous insulation, exceeds prescriptive"
        }

        # Assembly types available
        assembly_types = ["Exterior Wall", "Interior Wall", "Roof", "Floor", "Foundation"]

        # Initialize session state for assembly selections if not exists
        if "assembly_selections" not in st.session_state:
            st.session_state.assembly_selections = {
                "Exterior Wall": ("Concrete/Masonry", True),
                "Roof": ("Metal Framed", True),
                "Floor": ("Concrete/Masonry", True)
            }

        # Display assembly type selections
        st.markdown("#### Assembly Configurations")

        for assembly_type in assembly_types:
            col1, col2, col3 = st.columns([2, 3, 1])

            # Get current state or default
            current_structure, is_selected = st.session_state.assembly_selections.get(
                assembly_type,
                ("Wood Framed", False)
            )

            with col1:
                include = st.checkbox(
                    assembly_type,
                    value=is_selected,
                    key=f"include_{assembly_type}"
                )

            with col2:
                if include:
                    structure_type = st.selectbox(
                        "Structure Type",
                        structure_options,
                        index=structure_options.index(current_structure) if current_structure in structure_options else 0,
                        key=f"structure_{assembly_type}",
                        label_visibility="collapsed"
                    )

                    # Update session state
                    st.session_state.assembly_selections[assembly_type] = (structure_type, True)
                else:
                    st.caption("Not included")
                    # Update session state
                    if assembly_type in st.session_state.assembly_selections:
                        st.session_state.assembly_selections[assembly_type] = (current_structure, False)

            with col3:
                if include:
                    structure_type = st.session_state.assembly_selections[assembly_type][0]
                    # Show info as tooltip
                    st.markdown(f"<small title='{structure_info[structure_type]}'>ℹ️</small>", unsafe_allow_html=True)

        st.divider()

        if st.button("Generate Constructions", type="primary"):
            # Build structure map from selected assemblies
            selected_assemblies = {
                assembly: structure
                for assembly, (structure, selected) in st.session_state.assembly_selections.items()
                if selected
            }

            if selected_assemblies:
                generate_default_constructions_per_type(
                    model,
                    selected_assemblies,
                    climate_zone,
                    building_type
                )
                st.success(f"✅ Created {len(selected_assemblies)} T-24 compliant constructions!")
                st.rerun()
            else:
                st.warning("⚠️ Please select at least one construction type")

    else:  # Step-by-step mode
        st.subheader("Create Construction")

        with st.form("construction_form"):
            col1, col2 = st.columns(2)

            with col1:
                const_name = st.text_input("Name", value="Exterior Wall", key="const_name")
                const_type = st.selectbox("Type", ["Exterior Wall", "Interior Wall", "Roof", "Floor", "Foundation"])
                const_u_value = st.number_input("U-Value (W/m²·K)", value=0.35, min_value=0.01, max_value=5.0, format="%.3f")

            with col2:
                const_thickness = st.number_input("Total Thickness (m)", value=0.30, min_value=0.01, format="%.3f")
                const_description = st.text_area("Description", value="", height=80)

            submitted = st.form_submit_button("Add Construction", type="primary")

            if submitted:
                add_construction(model, const_name, const_type, const_u_value, const_thickness, const_description)
                st.success(f"✅ Added construction: {const_name}")
                st.rerun()

    # Show existing constructions
    catalogs = model.get("catalogs", {})
    constructions = catalogs.get("construction_types", catalogs.get("constructions", []))
    if constructions:
        st.divider()
        st.subheader(f"Defined Constructions ({len(constructions)})")
        for const in constructions:
            with st.expander(f"🏗️ {const.get('name', 'Unknown')}"):
                st.json(const)

    # Navigation
    st.divider()
    col1, col2, col3 = st.columns([1, 2, 1])
    with col1:
        if st.button("◀️ Back", use_container_width=True):
            st.session_state.wizard_step = 1
            st.rerun()
    with col3:
        if st.button("Next ▶️", type="primary", use_container_width=True):
            st.session_state.wizard_step = 3
            st.rerun()


def show_materials_step(model: Dict[str, Any], analysis: Dict[str, Any]):
    """Step 3: Create materials (optional)."""
    st.header("🧱 Step 4: Materials (Optional)")

    st.info("Materials are optional. They can be added later if you need detailed layer-by-layer construction definitions.")

    counts = analysis["counts"]

    if counts["materials"] > 0:
        st.success(f"✅ Your model has {counts['materials']} materials defined.")

    st.markdown("""
    **Skip this step if:**
    - You're defining constructions with U-values only
    - You don't need detailed layer information

    **Complete this step if:**
    - You need layer-by-layer thermal properties
    - You're modeling for detailed energy analysis
    """)

    # Navigation
    st.divider()
    col1, col2, col3 = st.columns([1, 2, 1])
    with col1:
        if st.button("◀️ Back", use_container_width=True):
            st.session_state.wizard_step = 2
            st.rerun()
    with col2:
        if st.button("Skip Materials", use_container_width=True):
            st.session_state.wizard_step = 4
            st.rerun()
    with col3:
        if st.button("Next ▶️", type="primary", use_container_width=True):
            st.session_state.wizard_step = 4
            st.rerun()


def show_hvac_step(model: Dict[str, Any], analysis: Dict[str, Any]):
    """Step 4: Create HVAC systems."""
    st.header("❄️ Step 5: HVAC Systems")

    counts = analysis["counts"]
    needs = analysis["needs"]

    if not needs["hvac"]:
        st.success(f"✅ Your model already has {counts['hvac_systems']} HVAC systems defined.")
    else:
        st.warning(f"⚠️ You have {counts['zones']} zones but no HVAC systems defined.")
        st.markdown("HVAC systems provide heating, cooling, and ventilation to zones.")

    # Quick setup mode
    if st.session_state.wizard_data.get("mode") == "Quick Setup (Recommended)":
        st.subheader("Quick Setup")
        st.info("💡 **Tip**: Systems are based on real California Title 24 compliance projects with SEER2/HSPF2 ratings.")

        # Get building type and climate zone from wizard data (set in overview step)
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

        # Full list of HVAC system types (industry standard)
        all_system_types = [
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

        # Suggested defaults by building type
        suggested_types = {
            "multifamily": ["Split System Heat Pump", "Variable Refrigerant Flow (VRF)", "Packaged Terminal Heat Pump (PTHP)"],
            "small_commercial": ["Variable Refrigerant Flow (VRF)", "Packaged Rooftop Unit (RTU)", "Split System Heat Pump"],
            "large_commercial": ["Variable Refrigerant Flow (VRF)", "Chilled Water + Boiler", "Dedicated Outdoor Air System (DOAS)"],
            "warehouse": ["Packaged Rooftop Unit (RTU)", "Make-Up Air Unit (MAU)", "Unit Heater"]
        }

        # Show suggested types first
        suggested = suggested_types.get(building_type, all_system_types[:3])
        st.caption(f"💡 **Suggested for {building_type_display}**: {', '.join(suggested)}")

        system_type = st.selectbox(
            "HVAC System Type",
            all_system_types,
            index=all_system_types.index(suggested[0]) if suggested[0] in all_system_types else 0,
            key="hvac_system_type",
            help="Select the HVAC system type for this building. Suggested types are shown above based on building type."
        )

        num_systems = st.number_input(
            "Number of HVAC Systems",
            min_value=1,
            max_value=10,
            value=min(counts["zones"], 3) if counts["zones"] > 0 else 1,
            help="Typically 1 system for residential, multiple for commercial"
        )

        # Autosizing option
        if AUTOSIZING_AVAILABLE and counts["zones"] > 0:
            st.divider()
            use_autosizing = st.checkbox(
                "🔧 Autosize equipment based on zone geometry",
                value=True,
                help="Calculate capacities from floor area and climate zone (CBECC-style sizing)"
            )
        else:
            use_autosizing = False

        if st.button("Generate HVAC Systems", type="primary"):
            if use_autosizing and AUTOSIZING_AVAILABLE:
                generate_default_hvac(model, num_systems, building_type, system_type, autosize=True, climate_zone=climate_zone)
            else:
                generate_default_hvac(model, num_systems, building_type, system_type, autosize=False)
            st.success(f"✅ Created {num_systems} HVAC system(s)!")
            st.rerun()

    else:  # Step-by-step mode
        st.subheader("Create HVAC System")

        with st.form("hvac_form"):
            col1, col2 = st.columns(2)

            with col1:
                hvac_name = st.text_input("System Name", value="Main HVAC", key="hvac_name")
                hvac_type = st.selectbox(
                    "System Type",
                    ["Central Forced Air", "Heat Pump", "VRF", "Package Unit", "Split System"],
                    key="hvac_type_select"
                )
                hvac_cooling_capacity = st.number_input("Cooling Capacity (kW)", value=10.0, min_value=0.0, format="%.1f")

            with col2:
                hvac_heating_capacity = st.number_input("Heating Capacity (kW)", value=12.0, min_value=0.0, format="%.1f")
                hvac_cooling_eff = st.number_input("Cooling Efficiency (SEER)", value=14.0, min_value=8.0, max_value=30.0, format="%.1f")
                hvac_heating_eff = st.number_input("Heating Efficiency (AFUE %)", value=80.0, min_value=50.0, max_value=98.0, format="%.1f")

            submitted = st.form_submit_button("Add HVAC System", type="primary")

            if submitted:
                add_hvac_system(model, hvac_name, hvac_type, hvac_cooling_capacity, hvac_heating_capacity, hvac_cooling_eff, hvac_heating_eff)
                st.success(f"✅ Added HVAC system: {hvac_name}")
                st.rerun()

    # Show existing HVAC systems
    if "systems" in model and "hvac" in model["systems"]:
        hvac_systems = model["systems"]["hvac"]
        if hvac_systems:
            st.divider()
            st.subheader(f"Defined HVAC Systems ({len(hvac_systems)})")
            for hvac in hvac_systems:
                with st.expander(f"❄️ {hvac.get('name', 'Unknown')}"):
                    st.json(hvac)

            # Zone assignment section
            st.divider()
            st.subheader("🏢 Assign Zones to HVAC Systems")
            st.caption("Assign each zone to an HVAC system. Zones can be grouped together.")

            show_zone_assignment_interface(model, hvac_systems, climate_zone if 'climate_zone' in locals() else "4")

    # Navigation
    st.divider()
    col1, col2, col3 = st.columns([1, 2, 1])
    with col1:
        if st.button("◀️ Back", use_container_width=True):
            st.session_state.wizard_step = 3
            st.rerun()
    with col3:
        if st.button("Next ▶️", type="primary", use_container_width=True):
            st.session_state.wizard_step = 5
            st.rerun()


def show_dhw_step(model: Dict[str, Any], analysis: Dict[str, Any]):
    """Step 5: Create DHW systems."""
    st.header("🚿 Step 5: DHW Systems")

    counts = analysis["counts"]

    if counts["dhw_systems"] > 0:
        st.success(f"✅ Your model already has {counts['dhw_systems']} DHW systems defined.")
    else:
        st.info("Domestic Hot Water (DHW) systems provide hot water for sinks, showers, and appliances.")

    # Quick setup mode
    if st.session_state.wizard_data.get("mode") == "Quick Setup (Recommended)":
        st.subheader("Quick Setup")
        st.info("💡 **Tip**: DHW systems are based on real California projects with Title 24 compliant energy factors.")

        # Get building type from wizard data (set in overview step)
        building_type_key = st.session_state.wizard_data.get("building_type", "warehouse")
        climate_zone = st.session_state.wizard_data.get("climate_zone", "4")

        # Map to simplified DHW categories
        building_type_map_dhw = {
            "multifamily": "Multifamily",
            "small_commercial": "Commercial",
            "large_commercial": "Commercial",
            "warehouse": "Warehouse"
        }
        building_type = building_type_map_dhw.get(building_type_key, "Warehouse")

        # Map back for display
        building_type_display_full = {
            "multifamily": "Multifamily Residential",
            "small_commercial": "Small Commercial",
            "large_commercial": "Large Commercial",
            "warehouse": "Warehouse/Industrial"
        }
        display_name = building_type_display_full.get(building_type_key, "Warehouse/Industrial")

        st.success(f"📋 **Building Type**: {display_name} | **Climate Zone**: {climate_zone}")
        st.caption("(Set in Step 1 - Overview)")

        # Full list of water heater types (industry standard)
        all_heater_types = [
            "Storage Tank - Gas",
            "Storage Tank - Electric",
            "Heat Pump Water Heater (HPWH)",
            "Tankless - Gas (Instantaneous)",
            "Tankless - Electric",
            "Solar Thermal + Storage Backup",
            "Solar Thermal + Tankless Backup",
            "Point-of-Use Electric",
            "Boiler with Indirect Tank",
            "Commercial Storage - Gas",
            "Commercial Instantaneous - Gas"
        ]

        # Suggested defaults by building type (aligned with T24 prescriptive)
        suggested_heaters = {
            "Multifamily": ["Heat Pump Water Heater (HPWH)", "Tankless - Gas (Instantaneous)", "Storage Tank - Gas"],
            "Commercial": ["Tankless - Gas (Instantaneous)", "Point-of-Use Electric", "Commercial Storage - Gas"],
            "Warehouse": ["Storage Tank - Electric", "Storage Tank - Gas", "Tankless - Gas (Instantaneous)"]
        }

        # T24 compliance notes
        t24_notes = {
            "Multifamily": "🏆 T24 2022 prescriptive: HPWH required for new construction",
            "Commercial": "💡 T24: Instantaneous or point-of-use generally most efficient",
            "Warehouse": "💡 T24: Electric resistance or gas storage typical for minimal DHW needs"
        }

        # Show T24 compliance note and suggested types
        suggested = suggested_heaters.get(building_type, all_heater_types[:3])
        t24_note = t24_notes.get(building_type, "")
        if t24_note:
            st.info(t24_note)
        st.caption(f"💡 **Suggested for {building_type}**: {', '.join(suggested)}")

        heater_type = st.selectbox(
            "Service Water Heater Type",
            all_heater_types,
            index=all_heater_types.index(suggested[0]) if suggested[0] in all_heater_types else 0,
            key="dhw_heater_type",
            help="Select the water heater type. Solar thermal systems include backup heaters for cloudy days."
        )

        # Autosizing option for DHW
        if AUTOSIZING_AVAILABLE and counts["zones"] > 0:
            st.divider()
            use_dhw_autosizing = st.checkbox(
                "🔧 Autosize DHW based on building parameters",
                value=True,
                help="Calculate tank capacity based on floor area, units, or occupancy"
            )

            if use_dhw_autosizing:
                col1, col2 = st.columns(2)
                with col1:
                    if building_type == "Multifamily":
                        num_units = st.number_input(
                            "Number of Dwelling Units",
                            min_value=1,
                            max_value=1000,
                            value=max(counts["zones"], 20),
                            help="Total dwelling units in building"
                        )
                        bedrooms_per_unit = st.number_input(
                            "Average Bedrooms per Unit",
                            min_value=0,
                            max_value=4,
                            value=2,
                            help="0 = studio, 1-4 = bedrooms"
                        )
                    else:
                        num_units = None
                        bedrooms_per_unit = None
                        num_employees = st.number_input(
                            "Number of Employees",
                            min_value=1,
                            max_value=10000,
                            value=50,
                            help="Total employees/occupants"
                        )
                with col2:
                    # Automatically filled but can be overridden
                    zones = model.get("zones", [])
                    total_floor_area = sum(
                        zone.get("floor_area_sqft", zone.get("floor_area_sf", zone.get("area", 0)))
                        for zone in zones
                    )
                    floor_area_override = st.number_input(
                        "Floor Area (sq ft)",
                        min_value=0,
                        value=int(total_floor_area) if total_floor_area > 0 else 10000,
                        help="Total conditioned floor area"
                    )
        else:
            use_dhw_autosizing = False
            num_units = None
            bedrooms_per_unit = None
            num_employees = None
            floor_area_override = None

        if st.button("Generate DHW System", type="primary"):
            if use_dhw_autosizing and AUTOSIZING_AVAILABLE:
                generate_default_dhw(
                    model, building_type, heater_type,
                    autosize=True,
                    num_units=num_units,
                    bedrooms_per_unit=bedrooms_per_unit,
                    num_employees=num_employees if building_type != "Multifamily" else None,
                    floor_area_sqft=floor_area_override
                )
            else:
                generate_default_dhw(model, building_type, heater_type, autosize=False)
            st.success("✅ Created DHW system!")
            st.rerun()

    else:  # Step-by-step mode
        st.subheader("Create DHW System")

        with st.form("dhw_form"):
            col1, col2 = st.columns(2)

            with col1:
                dhw_name = st.text_input("System Name", value="Main DHW", key="dhw_name")
                dhw_type = st.selectbox("Type", ["Storage", "Tankless", "Heat Pump"], key="dhw_type_select")
                dhw_fuel = st.selectbox("Fuel Type", ["Natural Gas", "Electricity", "Propane"], key="dhw_fuel")

            with col2:
                dhw_capacity = st.number_input("Tank Capacity (Liters)", value=150.0, min_value=0.0, format="%.1f")
                dhw_efficiency = st.number_input("Energy Factor", value=0.62, min_value=0.1, max_value=1.0, format="%.2f")

            submitted = st.form_submit_button("Add DHW System", type="primary")

            if submitted:
                add_dhw_system(model, dhw_name, dhw_type, dhw_fuel, dhw_capacity, dhw_efficiency)
                st.success(f"✅ Added DHW system: {dhw_name}")
                st.rerun()

    # Show existing DHW systems
    if "systems" in model and "dhw" in model["systems"]:
        dhw_systems = model["systems"]["dhw"]
        if dhw_systems:
            st.divider()
            st.subheader(f"Defined DHW Systems ({len(dhw_systems)})")
            for dhw in dhw_systems:
                with st.expander(f"🚿 {dhw.get('name', 'Unknown')}"):
                    st.json(dhw)

    # Navigation
    st.divider()
    col1, col2, col3 = st.columns([1, 2, 1])
    with col1:
        if st.button("◀️ Back", use_container_width=True):
            st.session_state.wizard_step = 3  # Back to HVAC
            st.rerun()
    with col3:
        if st.button("Next ▶️", type="primary", use_container_width=True):
            st.session_state.wizard_step = 5  # Forward to Review
            st.rerun()


def show_review_step(model: Dict[str, Any], analysis: Dict[str, Any]):
    """Step 5: Review and apply changes."""
    st.header("✅ Step 6: Review & Complete")

    st.success("🎉 Great! Let's review what you've created:")

    # Re-analyze to show updated counts
    updated_analysis = analyze_model_completeness(model)
    counts = updated_analysis["counts"]

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("📊 Model Summary")
        st.metric("Zones", counts["zones"])
        st.metric("Surfaces", counts["surfaces"])
        st.metric("Openings", counts["openings"])

    with col2:
        st.subheader("📚 Catalogs & Systems")
        st.metric("Window Types", counts["window_types"])
        st.metric("Constructions", counts["constructions"])
        st.metric("HVAC Systems", counts["hvac_systems"])
        st.metric("DHW Systems", counts["dhw_systems"])

    st.divider()

    # Schedule Generation Section
    st.subheader("📅 Operation Schedules")

    schedules_status = updated_analysis["has"]["schedules"]
    if schedules_status:
        st.success(f"✅ Schedules assigned: {counts['schedules']} schedule(s) for {counts['zones_with_schedules']} zone(s)")
    else:
        st.info("⏱️ No schedules assigned yet")

        # Get building type from metadata or wizard data
        building_type = (
            st.session_state.wizard_data.get("building_type") or
            model.get("metadata", {}).get("building_type", "warehouse")
        )

        st.markdown(f"""
        **Auto-generate T24-compliant schedules for your {building_type} model:**
        - Occupancy schedules
        - Lighting schedules
        - Equipment schedules
        - Heating/Cooling setpoints
        - Ventilation schedules
        """)

        if st.button("🔄 Generate Schedules", type="secondary", use_container_width=True):
            with st.spinner("Generating schedules..."):
                try:
                    assign_schedules_to_zones(model, building_type)
                    st.success("✅ Schedules generated and assigned to zones!")
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ Error generating schedules: {e}")

    st.divider()

    # Completeness check
    all_needed = updated_analysis["needs"]
    critical_missing = [k for k, v in all_needed.items() if v and k in ["window_types", "constructions", "hvac"]]
    recommended_missing = [k for k, v in all_needed.items() if v and k in ["schedules", "dhw"]]

    if critical_missing:
        st.warning(f"⚠️ Still missing critical elements: {', '.join(critical_missing)}")
        st.info("You can go back to add these, or continue to manual editing.")
    elif recommended_missing:
        st.info(f"💡 Recommended: Add {', '.join(recommended_missing)} for more accurate simulations")
        st.success("✅ Your model has all critical elements!")
    else:
        st.success("✅ Your model is complete and ready for export!")

    st.markdown("### 🚀 Next Steps")
    st.markdown("""
    1. **Edit Model** - Fine-tune individual elements
    2. **Active Model** - Review the complete structure
    3. **Export** - Save your model to CIBD22X or EMJSON
    4. **Diagnostics** - Validate your model
    """)

    # Actions
    st.divider()
    col1, col2, col3 = st.columns(3)

    with col1:
        if st.button("◀️ Back", use_container_width=True):
            st.session_state.wizard_step = 4  # Back to DHW
            st.rerun()

    with col2:
        if st.button("🔄 Start Over", use_container_width=True):
            st.session_state.wizard_step = 0
            st.session_state.wizard_data = {}
            st.rerun()

    with col3:
        if st.button("✅ Finish & Edit", type="primary", use_container_width=True):
            st.session_state.wizard_step = 0
            st.session_state.wizard_data = {}
            st.session_state.wizard_complete = True  # Flag for main to handle navigation
            st.success("✅ Wizard complete! Redirecting to Edit Model...")
            st.rerun()


# Helper functions to load templates and create default elements

def load_template(template_name: str) -> Dict[str, Any]:
    """Load a template file from the templates directory."""
    try:
        template_path = EXPLORER_GUI / "templates" / template_name
        with open(template_path, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        st.error(f"Template file not found: {template_name}")
        return {}
    except json.JSONDecodeError:
        st.error(f"Invalid JSON in template file: {template_name}")
        return {}


def generate_default_window_types(model: Dict[str, Any], count: int):
    """Generate default window types."""
    if "catalogs" not in model:
        model["catalogs"] = {}
    if "window_types" not in model["catalogs"]:
        model["catalogs"]["window_types"] = []

    window_types = model["catalogs"]["window_types"]

    # Standard window types by performance level - U-factors in BTU/(hr·ft²·°F) for California Title 24
    defaults = [
        {"name": "Standard Double Pane", "u_factor": 0.49, "shgc": 0.40, "vt": 0.60},
        {"name": "Low-E Double Pane", "u_factor": 0.32, "shgc": 0.30, "vt": 0.65},
        {"name": "High Performance Triple", "u_factor": 0.21, "shgc": 0.25, "vt": 0.55},
        {"name": "Single Pane Clear", "u_factor": 1.02, "shgc": 0.76, "vt": 0.80},
        {"name": "Double Pane Tinted", "u_factor": 0.49, "shgc": 0.35, "vt": 0.45}
    ]

    for i in range(count):
        if i < len(defaults):
            wt_data = defaults[i]
        else:
            wt_data = defaults[0]  # Repeat standard type

        window_type = {
            "id": f"window_type_{len(window_types) + 1}",
            "name": wt_data["name"],
            "u_factor": wt_data["u_factor"],
            "shgc": wt_data["shgc"],
            "vt": wt_data["vt"]
        }
        window_types.append(window_type)


def add_window_type(model: Dict[str, Any], name: str, u_factor: float, shgc: float, vt: float, frame_type: str, glazing_type: str):
    """Add a single window type."""
    if "catalogs" not in model:
        model["catalogs"] = {}
    if "window_types" not in model["catalogs"]:
        model["catalogs"]["window_types"] = []

    window_types = model["catalogs"]["window_types"]

    window_type = {
        "id": f"wt_{len(window_types) + 1}",
        "name": name,
        "u_factor": u_factor,
        "shgc": shgc,
        "vt": vt,
        "frame_type": frame_type,
        "glazing_type": glazing_type
    }
    window_types.append(window_type)


def add_window_type_from_category(model: Dict[str, Any], category: str, wt_data: Dict[str, Any], building_type: str, climate_zone: str):
    """Add a window type from T-24 prescriptive category."""
    if "catalogs" not in model:
        model["catalogs"] = {}
    if "window_types" not in model["catalogs"]:
        model["catalogs"]["window_types"] = []

    window_types = model["catalogs"]["window_types"]

    window_type = {
        "id": f"wt_{len(window_types) + 1}",
        "name": category,
        "category": category,
        "u_factor": wt_data["u_factor"],
        "shgc": wt_data["shgc"],
        "vt": wt_data["vt"],
        "description": wt_data["description"],
        "t24_compliant": True,
        "t24_climate_zone": climate_zone,
        "building_type": building_type
    }
    window_types.append(window_type)


def generate_default_constructions(model: Dict[str, Any], types: List[str], climate_zone: str):
    """Generate default constructions."""
    if "catalogs" not in model:
        model["catalogs"] = {}
    if "construction_types" not in model["catalogs"]:
        model["catalogs"]["construction_types"] = []

    constructions = model["catalogs"]["construction_types"]

    # U-values by climate zone
    u_values = {
        "Climate Zone 1-2 (Hot)": {"wall": 0.50, "roof": 0.30, "floor": 0.40},
        "Climate Zone 3-4 (Moderate)": {"wall": 0.35, "roof": 0.25, "floor": 0.35},
        "Climate Zone 5-8 (Cold)": {"wall": 0.25, "roof": 0.20, "floor": 0.30}
    }

    u_vals = u_values[climate_zone]

    construction_map = {
        "Exterior Wall": {"u_value": u_vals["wall"], "type": "wall"},
        "Interior Wall": {"u_value": 1.5, "type": "partition"},
        "Roof": {"u_value": u_vals["roof"], "type": "roof"},
        "Floor": {"u_value": u_vals["floor"], "type": "floor"},
        "Foundation": {"u_value": 0.50, "type": "floor"}
    }

    for const_type in types:
        const_data = construction_map[const_type]
        construction = {
            "id": f"const_{len(constructions) + 1}",
            "name": const_type,
            "construction_type": const_data["type"],
            "u_value_w_m2k": const_data["u_value"]
        }
        constructions.append(construction)


def generate_default_constructions_with_structure(
    model: Dict[str, Any],
    types: List[str],
    climate_zone: str,
    structure_type: str,
    building_type: str
):
    """Generate T-24 compliant constructions based on structure type."""
    if "catalogs" not in model:
        model["catalogs"] = {}
    if "construction_types" not in model["catalogs"]:
        model["catalogs"]["construction_types"] = []

    constructions = model["catalogs"]["construction_types"]

    # T-24 2022 prescriptive U-values by climate zone and structure type
    # All values in W/m²·K (SI units for internal calculations)
    # Climate zones 1-16 mapped to hot/moderate/cold
    cz_num = int(climate_zone)

    # Determine climate grouping
    if cz_num in [1, 2, 3, 4, 5]:  # Hot climates
        climate_group = "hot"
    elif cz_num in [6, 7, 8, 9, 10, 11, 12]:  # Moderate climates
        climate_group = "moderate"
    else:  # 13, 14, 15, 16 - Cold climates
        climate_group = "cold"

    # T-24 prescriptive U-values by structure type and climate
    wall_u_values = {
        "Wood Framed": {
            "hot": 0.064,  # R-15 cavity + R-0 continuous
            "moderate": 0.051,  # R-19 cavity + R-0 continuous
            "cold": 0.043  # R-21 cavity + R-3.8 continuous
        },
        "Metal Framed": {
            "hot": 0.089,  # R-13 cavity + R-7.5 continuous
            "moderate": 0.064,  # R-13 cavity + R-13 continuous
            "cold": 0.051  # R-13 cavity + R-18.8 continuous
        },
        "Concrete/Masonry": {
            "hot": 0.71,  # R-5.7 continuous insulation
            "moderate": 0.36,  # R-11.4 continuous insulation
            "cold": 0.27  # R-15.2 continuous insulation
        },
        "Insulated Concrete Forms (ICF)": {
            "hot": 0.043,  # R-24 (exceeds prescriptive)
            "moderate": 0.040,  # R-26
            "cold": 0.037  # R-28
        },
        "Structural Insulated Panels (SIP)": {
            "hot": 0.037,  # R-28 (exceeds prescriptive)
            "moderate": 0.034,  # R-30
            "cold": 0.031  # R-33
        }
    }

    # Roof U-values (less dependent on structure)
    roof_u_values = {
        "hot": 0.027,  # R-38
        "moderate": 0.021,  # R-49
        "cold": 0.019  # R-54
    }

    # Floor U-values
    floor_u_values = {
        "hot": 0.33,  # R-13
        "moderate": 0.25,  # R-19
        "cold": 0.21  # R-25
    }

    # Get structure-specific wall U-value
    wall_u_value = wall_u_values.get(structure_type, wall_u_values["Wood Framed"])[climate_group]
    roof_u_value = roof_u_values[climate_group]
    floor_u_value = floor_u_values[climate_group]

    construction_map = {
        "Exterior Wall": {
            "u_value": wall_u_value,
            "type": "wall",
            "description": f"{structure_type} wall per T-24 2022 CZ{climate_zone}"
        },
        "Interior Wall": {
            "u_value": 1.5,
            "type": "partition",
            "description": "Interior partition wall"
        },
        "Roof": {
            "u_value": roof_u_value,
            "type": "roof",
            "description": f"Roof assembly per T-24 2022 CZ{climate_zone}"
        },
        "Floor": {
            "u_value": floor_u_value,
            "type": "floor",
            "description": f"Floor assembly per T-24 2022 CZ{climate_zone}"
        },
        "Foundation": {
            "u_value": 0.50,
            "type": "floor",
            "description": "Foundation/slab assembly"
        }
    }

    for const_type in types:
        const_data = construction_map[const_type]
        construction = {
            "id": f"const_{len(constructions) + 1}",
            "name": f"{const_type} - {structure_type}",
            "construction_type": const_data["type"],
            "u_value_w_m2k": const_data["u_value"],
            "structure_type": structure_type,
            "climate_zone": climate_zone,
            "building_type": building_type,
            "t24_compliant": True,
            "description": const_data["description"]
        }
        constructions.append(construction)


def generate_default_constructions_per_type(
    model: Dict[str, Any],
    selected_assemblies: Dict[str, str],
    climate_zone: str,
    building_type: str
):
    """
    Generate T-24 compliant constructions with different structure types per assembly.

    Args:
        model: The project model
        selected_assemblies: Dict mapping assembly type to structure type
                           e.g., {"Exterior Wall": "Concrete/Masonry", "Roof": "Metal Framed"}
        climate_zone: Climate zone string (e.g., "3")
        building_type: Building type (e.g., "office", "warehouse")
    """
    if "catalogs" not in model:
        model["catalogs"] = {}
    if "construction_types" not in model["catalogs"]:
        model["catalogs"]["construction_types"] = []

    constructions = model["catalogs"]["construction_types"]

    # Determine climate grouping
    cz_num = int(climate_zone)
    if cz_num in [1, 2, 3, 4, 5]:  # Hot climates
        climate_group = "hot"
    elif cz_num in [6, 7, 8, 9, 10, 11, 12]:  # Moderate climates
        climate_group = "moderate"
    else:  # 13, 14, 15, 16 - Cold climates
        climate_group = "cold"

    # T-24 prescriptive U-values by structure type and climate
    wall_u_values = {
        "Wood Framed": {
            "hot": 0.064,  # R-15 cavity + R-0 continuous
            "moderate": 0.051,  # R-19 cavity + R-0 continuous
            "cold": 0.043  # R-21 cavity + R-3.8 continuous
        },
        "Metal Framed": {
            "hot": 0.089,  # R-13 cavity + R-7.5 continuous
            "moderate": 0.064,  # R-13 cavity + R-13 continuous
            "cold": 0.051  # R-13 cavity + R-18.8 continuous
        },
        "Concrete/Masonry": {
            "hot": 0.71,  # R-5.7 continuous insulation
            "moderate": 0.36,  # R-11.4 continuous insulation
            "cold": 0.27  # R-15.2 continuous insulation
        },
        "Insulated Concrete Forms (ICF)": {
            "hot": 0.043,  # R-24 (exceeds prescriptive)
            "moderate": 0.040,  # R-26
            "cold": 0.037  # R-28
        },
        "Structural Insulated Panels (SIP)": {
            "hot": 0.037,  # R-28 (exceeds prescriptive)
            "moderate": 0.034,  # R-30
            "cold": 0.031  # R-33
        }
    }

    # Roof U-values by structure type and climate
    roof_u_values = {
        "Wood Framed": {
            "hot": 0.027,  # R-38
            "moderate": 0.021,  # R-49
            "cold": 0.019  # R-54
        },
        "Metal Framed": {
            "hot": 0.027,  # R-38
            "moderate": 0.021,  # R-49
            "cold": 0.019  # R-54
        },
        "Concrete/Masonry": {
            "hot": 0.027,  # R-38
            "moderate": 0.021,  # R-49
            "cold": 0.019  # R-54
        },
        "Insulated Concrete Forms (ICF)": {
            "hot": 0.027,
            "moderate": 0.021,
            "cold": 0.019
        },
        "Structural Insulated Panels (SIP)": {
            "hot": 0.027,
            "moderate": 0.021,
            "cold": 0.019
        }
    }

    # Floor U-values by structure type and climate
    floor_u_values = {
        "Wood Framed": {
            "hot": 0.33,  # R-13
            "moderate": 0.25,  # R-19
            "cold": 0.21  # R-25
        },
        "Metal Framed": {
            "hot": 0.33,
            "moderate": 0.25,
            "cold": 0.21
        },
        "Concrete/Masonry": {
            "hot": 0.33,
            "moderate": 0.25,
            "cold": 0.21
        },
        "Insulated Concrete Forms (ICF)": {
            "hot": 0.21,
            "moderate": 0.19,
            "cold": 0.17
        },
        "Structural Insulated Panels (SIP)": {
            "hot": 0.21,
            "moderate": 0.19,
            "cold": 0.17
        }
    }

    # Interior walls are not climate-dependent
    interior_wall_u_value = 1.5

    # Load construction templates with layers and materials
    templates = load_construction_templates()

    # Initialize materials catalog if templates are available
    if templates and "materials" not in model.get("catalogs", {}):
        if "catalogs" not in model:
            model["catalogs"] = {}
        model["catalogs"]["materials"] = []

    materials_catalog = model.get("catalogs", {}).get("materials", [])
    materials_added = set(mat.get("id") for mat in materials_catalog)

    # Generate constructions for each selected assembly
    for assembly_type, structure_type in selected_assemblies.items():
        # Map assembly type to construction type
        const_type = map_to_const_type(assembly_type)

        # Try to find matching template assembly
        assembly_template = None
        if templates:
            category = map_assembly_to_category(assembly_type)
            category_assemblies = templates.get("assemblies", {}).get(category, {})
            assembly_template = find_matching_assembly(category_assemblies, structure_type, climate_zone)

        # If template found, use it with layers and materials
        if assembly_template:
            # Add materials used in this assembly to catalog
            for layer in assembly_template.get("layers", []):
                material_id = layer.get("material")

                if material_id and material_id not in materials_added:
                    material_def = find_material_definition(templates.get("materials", {}), material_id)
                    if material_def:
                        materials_catalog.append({
                            "id": material_id,
                            **material_def
                        })
                        materials_added.add(material_id)

            # Create construction with layers from template
            construction = {
                "id": f"const_{len(constructions) + 1}",
                "name": assembly_template.get("name", f"{assembly_type} - {structure_type}"),
                "construction_type": const_type,
                "u_value_w_m2k": assembly_template.get("u_value_w_m2k", 0.5),
                "structure_type": structure_type,
                "climate_zone": climate_zone,
                "building_type": building_type,
                "t24_compliant": True,
                "description": assembly_template.get("description", f"{structure_type} assembly per T-24 2022"),
                "layers": assembly_template.get("layers", [])  # Include layer definitions
            }
        else:
            # Fallback: Use simple U-value approach if no template found
            # Determine U-value based on assembly type and structure type
            if assembly_type == "Exterior Wall":
                u_value = wall_u_values.get(structure_type, wall_u_values["Wood Framed"])[climate_group]
                description = f"{structure_type} exterior wall per T-24 2022 CZ{climate_zone}"

            elif assembly_type == "Interior Wall":
                u_value = interior_wall_u_value
                description = f"{structure_type} interior partition wall"

            elif assembly_type == "Roof":
                u_value = roof_u_values.get(structure_type, roof_u_values["Wood Framed"])[climate_group]
                description = f"{structure_type} roof assembly per T-24 2022 CZ{climate_zone}"

            elif assembly_type == "Floor":
                u_value = floor_u_values.get(structure_type, floor_u_values["Wood Framed"])[climate_group]
                description = f"{structure_type} floor assembly per T-24 2022 CZ{climate_zone}"

            elif assembly_type == "Foundation":
                u_value = 0.50
                description = f"{structure_type} foundation/slab assembly"

            else:
                continue  # Skip unknown assembly types

            # Create simple construction entry without layers
            construction = {
                "id": f"const_{len(constructions) + 1}",
                "name": f"{assembly_type} - {structure_type}",
                "construction_type": const_type,
                "u_value_w_m2k": u_value,
                "structure_type": structure_type,
                "climate_zone": climate_zone,
                "building_type": building_type,
                "t24_compliant": True,
                "description": description
            }

        constructions.append(construction)


def add_construction(model: Dict[str, Any], name: str, const_type: str, u_value: float, thickness: float, description: str):
    """Add a single construction."""
    if "catalogs" not in model:
        model["catalogs"] = {}
    if "construction_types" not in model["catalogs"]:
        model["catalogs"]["construction_types"] = []

    constructions = model["catalogs"]["construction_types"]

    construction = {
        "id": f"const_{len(constructions) + 1}",
        "name": name,
        "construction_type": const_type.lower().replace(" ", "_"),
        "u_value_w_m2k": u_value,
        "thickness_m": thickness,
        "description": description
    }
    constructions.append(construction)


def generate_default_hvac(model: Dict[str, Any], count: int, building_type: str, system_type: str, autosize: bool = False, climate_zone: str = "moderate"):
    """Generate default HVAC systems from templates with optional autosizing."""
    if "systems" not in model:
        model["systems"] = {}
    if "hvac" not in model["systems"]:
        model["systems"]["hvac"] = []

    hvac_systems = model["systems"]["hvac"]

    # Load HVAC templates
    templates = load_template("hvac_templates.json")
    if not templates:
        st.warning("Could not load HVAC templates, using fallback defaults.")
        # Fallback to hardcoded values
        for i in range(count):
            hvac = {
                "id": f"hvac_{len(hvac_systems) + 1}",
                "name": f"HVAC System {len(hvac_systems) + 1}",
                "system_type": system_type,
                "cooling_capacity_kw": 10.0,
                "heating_capacity_kw": 12.0,
                "cooling_efficiency_seer": 14.0,
                "heating_efficiency_afue": 80.0
            }
            hvac_systems.append(hvac)
        return

    # Perform autosizing if requested
    autosized_capacities = []
    if autosize and AUTOSIZING_AVAILABLE:
        # Get zones from model
        zones = model.get("zones", [])
        if not zones:
            zones = model.get("building", {}).get("zones", [])

        if zones:
            # Map building type for autosizer
            building_type_map = {
                "Multifamily Residential": "multifamily_residential",
                "Small Commercial": "commercial_office",
                "Large Commercial": "commercial_office",
                "Warehouse/Industrial": "warehouse_industrial"
            }
            autosize_building_type = building_type_map.get(building_type, "multifamily_residential")

            # Size systems
            system_per_zone = (count > 1)
            sizing_result = AutoSizer.size_from_zones(
                zones=zones,
                building_type=autosize_building_type,
                climate_zone=climate_zone,
                system_per_zone=system_per_zone
            )

            if "error" not in sizing_result:
                autosized_capacities = sizing_result.get("system_capacities", [])
                if autosized_capacities:
                    st.info(f"🔧 Autosized {len(autosized_capacities)} system(s) based on {sizing_result.get('total_floor_area_sqft', 0):.0f} sq ft")
            else:
                st.warning(f"Autosizing failed: {sizing_result['error']}")
                autosize = False  # Fall back to template sizing

    # Map building type to template category
    template_category_map = {
        # Keys from wizard_data (stored values)
        "multifamily": "multifamily_residential",
        "small_commercial": "commercial_office",
        "large_commercial": "commercial_office",
        "warehouse": "warehouse_industrial",
        # Display names (for backward compatibility)
        "Multifamily Residential": "multifamily_residential",
        "Small Commercial": "commercial_office",
        "Large Commercial": "commercial_office",
        "Warehouse/Industrial": "warehouse_industrial"
    }

    # Map system type to template key
    system_type_map = {
        "Packaged Rooftop Unit (RTU)": "packaged_rooftop_unit",
        "Split System Heat Pump": "ducted_heat_pump_large_zone",
        "Variable Refrigerant Flow (VRF)": "mini_split_small_zone",
        "Packaged Terminal AC (PTAC)": "common_area_heat_pump",  # Using closest match
        "Packaged Terminal Heat Pump (PTHP)": "common_area_heat_pump",
        "Water Source Heat Pump (WSHP)": "ducted_heat_pump_large_zone",
        "Ground Source Heat Pump (GSHP)": "ducted_heat_pump_large_zone",
        "Fan Coil Units (FCU)": "mini_split_small_zone",
        "Chilled Water + Boiler": "ducted_heat_pump_large_zone",  # Large systems
        "Dedicated Outdoor Air System (DOAS)": "ducted_heat_pump_large_zone",
        "Make-Up Air Unit (MAU)": "packaged_rooftop_unit",  # Similar to RTU
        "Unit Heater": "packaged_rooftop_unit",
        "Radiant Heating": "common_area_heat_pump",
        "Evaporative Cooling": "packaged_rooftop_unit",
        # Legacy mappings for backward compatibility
        "Heat Pump": "common_area_heat_pump",
        "VRF/Mini-Split": "mini_split_small_zone",
        "Package Unit": "packaged_rooftop_unit",
        "Separate Heating/Cooling": "ducted_heat_pump_large_zone"
    }

    template_category = template_category_map.get(building_type, "multifamily_residential")
    system_key = system_type_map.get(system_type, "common_area_heat_pump")

    # Debug logging
    st.info(f"🔍 Debug: building_type={building_type}, system_type={system_type}")
    st.info(f"🔍 Debug: template_category={template_category}, system_key={system_key}")

    # Get template
    category_templates = templates.get(template_category, {})
    st.info(f"🔍 Debug: Available templates in {template_category}: {list(category_templates.keys())}")

    # Try to get the specified system type, fall back to first available
    if system_key in category_templates:
        template = category_templates[system_key]
        st.info(f"✅ Found exact template: {system_key}")
    else:
        # Use first available template in category
        template = next(iter(category_templates.values()), {})
        st.warning(f"⚠️ System type '{system_key}' not found, using first available template")

    if not template:
        st.error(f"❌ No template found for {building_type} / {system_type}")
        st.info(f"🔍 Available categories: {list(templates.keys())}")
        return

    # Generate systems based on template
    for i in range(count):
        # Use autosized capacity if available, otherwise use template capacity
        if autosize and i < len(autosized_capacities):
            # Use autosized values
            autosized = autosized_capacities[i]
            cooling_capacity_kw = autosized.get("cooling_capacity_kw", 10.0)
            heating_capacity_kw = autosized.get("heating_capacity_kw", 12.0)
            cooling_capacity_btu = autosized.get("cooling_capacity_btu", 36000)
            heating_capacity_btu = autosized.get("heating_capacity_btu", 40000)
            cooling_tons = autosized.get("cooling_tons", 3.0)
            airflow_cfm = autosized.get("airflow_cfm", 1200)
            sizing_note = f"Autosized for {autosized.get('climate_classification', 'moderate')} climate zone"
        else:
            # Extract capacity from template
            if "sizes" in template:
                # Has multiple sizes (small, medium, large)
                size_key = "medium" if "medium" in template["sizes"] else next(iter(template["sizes"].keys()))
                size_data = template["sizes"][size_key]
                cooling_capacity_btu = size_data.get("cooling_capacity_btu", 36000)
                heating_capacity_btu = size_data.get("heating_capacity_btu", 40000)
                airflow_cfm = size_data.get("airflow_cfm", 1200)
            elif "capacity" in template:
                # Single capacity
                cooling_capacity_btu = template["capacity"].get("cooling_capacity_btu", 36000)
                heating_capacity_btu = template["capacity"].get("heating_capacity_btu", 40000)
                airflow_cfm = 1200
            else:
                # Fallback
                cooling_capacity_btu = 36000
                heating_capacity_btu = 40000
                airflow_cfm = 1200

            # Convert BTU to kW (1 BTU/h = 0.000293071 kW)
            cooling_capacity_kw = cooling_capacity_btu * 0.000293071
            heating_capacity_kw = heating_capacity_btu * 0.000293071
            cooling_tons = cooling_capacity_btu / 12000
            sizing_note = "From template"

        # Extract efficiency from template (always from template)
        efficiency = template.get("efficiency", {})
        cooling_seer2 = efficiency.get("cooling_seer2", 14.0)
        heating_hspf2 = efficiency.get("heating_hspf2", 7.5)

        hvac = {
            "id": f"hvac_{len(hvac_systems) + 1}",
            "name": f"{template.get('name', 'HVAC System')} {len(hvac_systems) + 1}",
            "system_type": template.get("system_type", "heat_pump"),
            "equipment_type": template.get("equipment_type", "split_system"),
            "cooling_capacity_kw": round(cooling_capacity_kw, 2),
            "heating_capacity_kw": round(heating_capacity_kw, 2),
            "cooling_capacity_btu": round(cooling_capacity_btu, 0),
            "heating_capacity_btu": round(heating_capacity_btu, 0),
            "cooling_tons": round(cooling_tons, 1),
            "airflow_cfm": round(airflow_cfm, 0),
            "cooling_efficiency_seer2": cooling_seer2,
            "heating_efficiency_hspf2": heating_hspf2,
            "description": template.get("description", ""),
            "template_source": f"{template_category}/{system_key}",
            "sizing_method": "autosized" if autosize else "template",
            "sizing_note": sizing_note
        }
        hvac_systems.append(hvac)


def add_hvac_system(model: Dict[str, Any], name: str, hvac_type: str, cooling_cap: float, heating_cap: float, cooling_eff: float, heating_eff: float):
    """Add a single HVAC system."""
    if "systems" not in model:
        model["systems"] = {}
    if "hvac" not in model["systems"]:
        model["systems"]["hvac"] = []

    hvac_systems = model["systems"]["hvac"]

    hvac = {
        "id": f"hvac_{len(hvac_systems) + 1}",
        "name": name,
        "system_type": hvac_type,
        "cooling_capacity_kw": cooling_cap,
        "heating_capacity_kw": heating_cap,
        "cooling_efficiency_seer": cooling_eff,
        "heating_efficiency_afue": heating_eff
    }
    hvac_systems.append(hvac)


def generate_default_dhw(
    model: Dict[str, Any],
    building_type: str,
    heater_type: str,
    autosize: bool = False,
    num_units: Optional[int] = None,
    bedrooms_per_unit: Optional[int] = None,
    num_employees: Optional[int] = None,
    floor_area_sqft: Optional[float] = None
):
    """Generate default DHW system from templates with optional autosizing."""
    if "systems" not in model:
        model["systems"] = {}
    if "dhw" not in model["systems"]:
        model["systems"]["dhw"] = []

    dhw_systems = model["systems"]["dhw"]

    # Perform autosizing if requested
    autosized_capacity = None
    if autosize and AUTOSIZING_AVAILABLE:
        # Map building type for autosizer
        building_type_map = {
            "Multifamily": "multifamily",
            "Commercial": "commercial_office",
            "Warehouse": "warehouse"
        }
        autosize_building_type = building_type_map.get(building_type, "multifamily")

        sizing_result = AutoSizer.calculate_dhw_capacity(
            building_type=autosize_building_type,
            num_units=num_units,
            num_bedrooms_per_unit=bedrooms_per_unit,
            num_employees=num_employees,
            floor_area_sqft=floor_area_sqft
        )

        if sizing_result and "tank_capacity_gallons" in sizing_result:
            autosized_capacity = sizing_result
            st.info(f"🔧 Autosized DHW: {autosized_capacity['tank_capacity_gallons']:.0f} gal tank, {autosized_capacity['input_rating_btu']:.0f} BTU/h input")

    # Load DHW templates
    templates = load_template("dhw_templates.json")
    if not templates:
        st.warning("Could not load DHW templates, using fallback defaults.")
        # Fallback with autosized capacity if available
        capacity_liters = autosized_capacity["tank_capacity_liters"] if autosized_capacity else 150.0
        dhw = {
            "id": f"dhw_{len(dhw_systems) + 1}",
            "name": "Main DHW System",
            "system_type": heater_type,
            "capacity_liters": capacity_liters,
            "energy_factor": 0.62,
            "fuel_type": "Gas"
        }
        dhw_systems.append(dhw)
        return

    # Map building type to template category
    template_category_map = {
        "Multifamily": "multifamily_residential",
        "Commercial": "commercial_office",
        "Warehouse": "warehouse_industrial"
    }

    # Map heater type to template key and fuel type
    heater_type_map = {
        "Storage Tank - Gas": ("central_dhw_with_recirculation", "gas"),
        "Storage Tank - Electric": ("central_dhw_with_recirculation", "electric"),
        "Heat Pump Water Heater (HPWH)": ("heat_pump_water_heater", "electric"),
        "Tankless - Gas (Instantaneous)": ("central_dhw_instantaneous", "gas"),
        "Tankless - Electric": ("central_dhw_instantaneous", "electric"),
        "Solar Thermal + Storage Backup": ("central_dhw_with_recirculation", "gas"),
        "Solar Thermal + Tankless Backup": ("central_dhw_instantaneous", "gas"),
        "Point-of-Use Electric": ("point_of_use_electric", "electric"),
        "Boiler with Indirect Tank": ("central_dhw_with_recirculation", "gas"),
        "Commercial Storage - Gas": ("central_dhw_with_recirculation", "gas"),
        "Commercial Instantaneous - Gas": ("central_dhw_instantaneous", "gas")
    }

    template_category = template_category_map.get(building_type, "multifamily_residential")
    system_key, fuel_type_override = heater_type_map.get(heater_type, ("central_dhw_with_recirculation", "gas"))

    # Get template
    category_templates = templates.get(template_category, {})

    # Try to get the specified system type, fall back to first available
    if system_key in category_templates:
        template = category_templates[system_key]
    else:
        # Use first available template in category
        template = next(iter(category_templates.values()), {})

    if not template:
        st.warning(f"No DHW template found for {building_type} / {heater_type}")
        return

    # Extract water heater configuration
    water_heater = None
    if "water_heater" in template:
        # Single water heater
        water_heater = template["water_heater"]
    elif "water_heater_options" in template:
        # Multiple options, pick instantaneous if available
        options = template["water_heater_options"]
        if "instantaneous" in options:
            water_heater = options["instantaneous"]
        else:
            water_heater = next(iter(options.values()), None)
    elif "water_heater_configurations" in template:
        # Multi-heater configurations (for large buildings)
        configs = template["water_heater_configurations"]
        # Pick medium size if available
        if "medium_building" in configs:
            config = configs["medium_building"]
            # Use first heater in the array
            if "heaters" in config and len(config["heaters"]) > 0:
                water_heater = config["heaters"][0]

    if not water_heater:
        st.warning("Could not extract water heater configuration from template")
        return

    # Extract properties from template or autosized values
    if autosize and autosized_capacity:
        # Use autosized capacity
        tank_volume_gal = autosized_capacity["tank_capacity_gallons"]
        tank_volume_liters = autosized_capacity["tank_capacity_liters"]
        input_rating_btu = autosized_capacity["input_rating_btu"]
        recovery_rate_gph = autosized_capacity["recovery_rate_gph"]
        sizing_note = f"Autosized: {autosized_capacity.get('sizing_method', 'simplified_capacity_calculation')}"
    else:
        # Use template values
        tank_volume_gal = water_heater.get("tank_volume_gal", water_heater.get("capacity_gal", 119))
        tank_volume_liters = tank_volume_gal * 3.78541  # Convert gallons to liters
        input_rating_btu = water_heater.get("input_rating_btu", 100000)
        recovery_rate_gph = None
        sizing_note = "From template"

    energy_factor = water_heater.get("energy_factor", 0.94)
    # Use fuel type from heater selection, not template (fixes bug where Electric storage tanks get Gas fuel)
    fuel = fuel_type_override if fuel_type_override else water_heater.get("fuel", "gas")
    heater_type_str = water_heater.get("type", "commercial_storage_te_sbl")

    dhw = {
        "id": f"dhw_{len(dhw_systems) + 1}",
        "name": template.get("name", "Main DHW System"),
        "system_type": template.get("system_type", "central_with_recirculation"),
        "water_heater_type": heater_type_str,
        "capacity_liters": round(tank_volume_liters, 1),
        "capacity_gallons": round(tank_volume_gal, 0),
        "input_rating_btu": round(input_rating_btu, 0),
        "energy_factor": energy_factor,
        "fuel_type": fuel.capitalize(),
        "description": template.get("description", ""),
        "template_source": f"{template_category}/{system_key}",
        "sizing_method": "autosized" if autosize else "template",
        "sizing_note": sizing_note
    }

    # Add additional properties if present
    if "recovery_efficiency" in water_heater:
        dhw["recovery_efficiency"] = water_heater["recovery_efficiency"]
    if recovery_rate_gph:
        dhw["recovery_rate_gph"] = recovery_rate_gph

    dhw_systems.append(dhw)


def add_dhw_system(model: Dict[str, Any], name: str, dhw_type: str, fuel: str, capacity: float, efficiency: float):
    """Add a single DHW system."""
    if "systems" not in model:
        model["systems"] = {}
    if "dhw" not in model["systems"]:
        model["systems"]["dhw"] = []

    dhw_systems = model["systems"]["dhw"]

    dhw = {
        "id": f"dhw_{len(dhw_systems) + 1}",
        "name": name,
        "system_type": dhw_type,
        "fuel_type": fuel,
        "capacity_liters": capacity,
        "energy_factor": efficiency
    }
    dhw_systems.append(dhw)


def show_zone_assignment_interface(model: Dict[str, Any], hvac_systems: List[Dict[str, Any]], climate_zone: str):
    """Show interface for assigning zones to HVAC systems."""

    # Get all zones
    zones = model.get("geometry", {}).get("zones", [])

    if not zones:
        st.warning("No zones found in model")
        return

    if not hvac_systems:
        st.warning("No HVAC systems available. Generate systems first.")
        return

    # Initialize zone assignments in session state if not exists
    if "zone_assignments" not in st.session_state:
        st.session_state.zone_assignments = {}

    # Create system options for dropdown
    system_options = ["Unassigned"] + [f"{sys.get('name', f'System {i+1}')} (ID: {sys.get('id', '')})"
                                       for i, sys in enumerate(hvac_systems)]
    system_ids = [None] + [sys.get('id') for sys in hvac_systems]

    # Assignment mode tabs
    tab1, tab2, tab3 = st.tabs(["🎯 Individual Assignment", "📦 Bulk Assignment", "📊 Summary"])

    with tab1:
        st.markdown("### Assign Zones Individually")
        st.caption(f"Total zones: {len(zones)}")

        # Show zones in a scrollable container
        for i, zone in enumerate(zones):
            zone_id = zone.get("id", f"zone_{i}")
            zone_name = zone.get("name", zone_id)
            floor_area = zone.get("floor_area_sqft", 0)

            col1, col2, col3 = st.columns([3, 2, 1])

            with col1:
                st.markdown(f"**{zone_name}**")
                st.caption(f"ID: `{zone_id}` | Area: {floor_area:.0f} sqft")

            with col2:
                # Get current assignment
                current_assignment = st.session_state.zone_assignments.get(zone_id)
                current_idx = 0
                if current_assignment:
                    try:
                        current_idx = system_ids.index(current_assignment)
                    except ValueError:
                        current_idx = 0

                selected = st.selectbox(
                    "Assign to:",
                    options=system_options,
                    index=current_idx,
                    key=f"zone_assign_{zone_id}",
                    label_visibility="collapsed"
                )

                # Update assignment
                selected_idx = system_options.index(selected)
                st.session_state.zone_assignments[zone_id] = system_ids[selected_idx]

            with col3:
                if st.session_state.zone_assignments.get(zone_id):
                    st.markdown("✅")
                else:
                    st.markdown("⚠️")

    with tab2:
        st.markdown("### Bulk Assignment by Pattern")
        st.caption("Assign multiple zones to a system based on name patterns")

        col1, col2 = st.columns(2)

        with col1:
            pattern = st.text_input(
                "Zone name pattern (case-insensitive)",
                placeholder="e.g., IES Flammable, Office, Warehouse",
                help="All zones containing this text will be assigned",
                key="bulk_pattern"
            )

        with col2:
            bulk_system = st.selectbox(
                "Assign to system:",
                options=system_options[1:],  # Exclude "Unassigned"
                key="bulk_system_select"
            )

        if st.button("Apply Bulk Assignment", type="primary"):
            if pattern:
                pattern_lower = pattern.lower()
                matches = []

                for zone in zones:
                    zone_name = zone.get("name", "").lower()
                    zone_id = zone.get("id", "")

                    if pattern_lower in zone_name:
                        # Get system ID from selection
                        bulk_idx = system_options.index(bulk_system)
                        st.session_state.zone_assignments[zone_id] = system_ids[bulk_idx]
                        matches.append(zone.get("name", zone_id))

                if matches:
                    st.success(f"✅ Assigned {len(matches)} zones to {bulk_system}")
                    with st.expander("Show assigned zones"):
                        for match in matches:
                            st.markdown(f"- {match}")
                    st.rerun()
                else:
                    st.warning(f"No zones found matching pattern: '{pattern}'")

        # Quick assignment buttons for common patterns
        st.divider()
        st.markdown("**Quick Patterns** (for Gibraltar warehouse):")

        col1, col2, col3 = st.columns(3)

        with col1:
            if st.button("Warehouse zones → System 1", use_container_width=True):
                warehouse_patterns = ["flammable", "aerosol", "storage", "warehouse"]
                count = 0
                for zone in zones:
                    zone_name = zone.get("name", "").lower()
                    zone_id = zone.get("id", "")
                    if any(p in zone_name for p in warehouse_patterns):
                        st.session_state.zone_assignments[zone_id] = system_ids[1] if len(system_ids) > 1 else None
                        count += 1
                st.success(f"Assigned {count} warehouse zones")
                st.rerun()

        with col2:
            if st.button("Office zones → System 2", use_container_width=True):
                office_patterns = ["office", "conference", "private"]
                count = 0
                for zone in zones:
                    zone_name = zone.get("name", "").lower()
                    zone_id = zone.get("id", "")
                    if any(p in zone_name for p in office_patterns):
                        st.session_state.zone_assignments[zone_id] = system_ids[2] if len(system_ids) > 2 else system_ids[1]
                        count += 1
                st.success(f"Assigned {count} office zones")
                st.rerun()

        with col3:
            if st.button("Amenity zones → System 3", use_container_width=True):
                amenity_patterns = ["restroom", "locker", "wellness", "lactation", "multifaith", "janitor"]
                count = 0
                for zone in zones:
                    zone_name = zone.get("name", "").lower()
                    zone_id = zone.get("id", "")
                    if any(p in zone_name for p in amenity_patterns):
                        st.session_state.zone_assignments[zone_id] = system_ids[3] if len(system_ids) > 3 else system_ids[1]
                        count += 1
                st.success(f"Assigned {count} amenity zones")
                st.rerun()

    with tab3:
        st.markdown("### Assignment Summary")

        # Calculate assignments per system
        assignments_by_system = {}
        unassigned_zones = []

        for zone in zones:
            zone_id = zone.get("id", "")
            zone_name = zone.get("name", zone_id)
            floor_area = zone.get("floor_area_sqft", 0)

            assigned_system = st.session_state.zone_assignments.get(zone_id)

            if assigned_system:
                if assigned_system not in assignments_by_system:
                    assignments_by_system[assigned_system] = {
                        "zones": [],
                        "total_area": 0
                    }
                assignments_by_system[assigned_system]["zones"].append(zone_name)
                assignments_by_system[assigned_system]["total_area"] += floor_area
            else:
                unassigned_zones.append((zone_name, floor_area))

        # Show summary for each system
        for i, hvac_sys in enumerate(hvac_systems):
            sys_id = hvac_sys.get("id")
            sys_name = hvac_sys.get("name", f"System {i+1}")

            if sys_id in assignments_by_system:
                data = assignments_by_system[sys_id]
                zone_count = len(data["zones"])
                total_area = data["total_area"]

                with st.expander(f"✅ {sys_name} - {zone_count} zones ({total_area:,.0f} sqft)", expanded=True):
                    col1, col2 = st.columns(2)

                    with col1:
                        st.metric("Zones", zone_count)
                        st.metric("Total Floor Area", f"{total_area:,.0f} sqft")

                    with col2:
                        # Show autosizing option
                        if AUTOSIZING_AVAILABLE:
                            if st.button(f"🔧 Autosize {sys_name}", key=f"autosize_{sys_id}", use_container_width=True):
                                # Calculate autosizing for this system based on assigned zones
                                building_type = model.get("project", {}).get("building_type", "warehouse")

                                capacity = AutoSizer.calculate_hvac_capacity(
                                    floor_area_sqft=total_area,
                                    building_type=building_type,
                                    climate_zone=climate_zone
                                )

                                # Update system capacities
                                hvac_sys["cooling_capacity_kw"] = capacity["cooling_capacity_kw"]
                                hvac_sys["heating_capacity_kw"] = capacity["heating_capacity_kw"]
                                hvac_sys["cooling_capacity_btu"] = capacity["cooling_capacity_btu"]
                                hvac_sys["heating_capacity_btu"] = capacity["heating_capacity_btu"]
                                hvac_sys["cooling_tons"] = capacity["cooling_tons"]
                                hvac_sys["airflow_cfm"] = capacity["airflow_cfm"]
                                hvac_sys["sizing_method"] = "autosized_from_zones"
                                hvac_sys["served_zones"] = [z for z in data["zones"]]
                                hvac_sys["served_area_sqft"] = total_area

                                st.success(f"✅ Autosized {sys_name}: {capacity['cooling_tons']:.1f} tons cooling, {capacity['heating_capacity_kw']:.1f} kW heating")
                                st.rerun()

                    st.markdown("**Assigned zones:**")
                    for zone_name in data["zones"]:
                        st.markdown(f"- {zone_name}")
            else:
                st.warning(f"⚠️ {sys_name} - No zones assigned")

        # Show unassigned zones
        if unassigned_zones:
            st.divider()
            st.warning(f"⚠️ {len(unassigned_zones)} zones not assigned to any system")
            with st.expander("Show unassigned zones"):
                for zone_name, area in unassigned_zones:
                    st.markdown(f"- {zone_name} ({area:.0f} sqft)")
        else:
            st.success("✅ All zones assigned to HVAC systems!")

        # Save assignments to model
        if st.button("💾 Save Assignments to Model", type="primary", use_container_width=True):
            # Store assignments in model
            if "zone_hvac_assignments" not in model:
                model["zone_hvac_assignments"] = {}

            model["zone_hvac_assignments"] = dict(st.session_state.zone_assignments)

            # Update HVAC systems with served zones
            for hvac_sys in hvac_systems:
                sys_id = hvac_sys.get("id")
                if sys_id in assignments_by_system:
                    data = assignments_by_system[sys_id]
                    hvac_sys["served_zones"] = data["zones"]
                    hvac_sys["served_area_sqft"] = data["total_area"]

            st.success("✅ Zone assignments saved to model!")
            st.rerun()
