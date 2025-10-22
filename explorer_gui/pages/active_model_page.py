import streamlit as st
import json
import sys
from pathlib import Path

# Add project root to path
ROOT = Path(__file__).resolve().parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Add explorer_gui to path
EXPLORER_GUI = ROOT / "explorer_gui"
if str(EXPLORER_GUI) not in sys.path:
    sys.path.insert(0, str(EXPLORER_GUI))

from import_export import emjson6_to_cibd22x


def render_tree_node(label: str, data: any, level: int = 0, expanded: bool = False):
    """Render a tree node with collapsible children."""
    indent = "    " * level
    
    if isinstance(data, dict):
        with st.expander(f"{indent}📁 {label} ({len(data)} items)", expanded=expanded):
            for key, value in data.items():
                render_tree_node(key, value, level + 1)
    elif isinstance(data, list):
        with st.expander(f"{indent}📋 {label} ({len(data)} items)", expanded=expanded):
            for i, item in enumerate(data):
                if isinstance(item, dict):
                    item_name = item.get("name", item.get("id", f"Item {i+1}"))
                    render_tree_node(item_name, item, level + 1)
                else:
                    st.write(f"{indent}    • {item}")
    else:
        st.write(f"{indent}    🔹 **{label}:** {data}")


def show_tree_navigator(model: dict):
    """Display a tree-style navigator for the EMJSON model."""
    st.subheader("🌲 Model Tree Navigator")
    
    # Project level
    if "project" in model:
        with st.expander("📦 Project", expanded=True):
            project = model["project"]
            for key, value in project.items():
                if key == "location":
                    with st.expander("📍 Location", expanded=False):
                        st.json(value)
                else:
                    render_tree_node(key, value, level=1)
    
    # Geometry level
    if "geometry" in model:
        with st.expander("🏗️ Geometry", expanded=True):
            geom = model["geometry"]
            
            # Zones
            zones = geom.get("zones", [])
            if zones:
                with st.expander(f"🏢 Zones ({len(zones)})", expanded=True):
                    for zone in zones:
                        zone_name = zone.get("name", zone.get("id", "Unknown"))
                        zone_type = zone.get("type", "")
                        area = zone.get("floor_area_m2", zone.get("area"))
                        area_str = f"{area:.1f} m²" if area is not None else "N/A"
                        
                        with st.expander(f"🏠 {zone_name} ({zone_type}) - {area_str}", expanded=False):
                            # Show zone details
                            for key, value in zone.items():
                                if key not in ["name", "id", "surfaces", "openings"]:
                                    if isinstance(value, (dict, list)):
                                        render_tree_node(key, value, level=3)
                                    else:
                                        st.write(f"        🔹 **{key}:** {value}")
                            
                            # Show surfaces under this zone
                            zone_surfaces = zone.get("surfaces", [])
                            if zone_surfaces:
                                with st.expander(f"    🧱 Surfaces ({len(zone_surfaces)})", expanded=False):
                                    for surf in zone_surfaces:
                                        surf_name = surf.get("name", surf.get("id", "Unknown"))
                                        surf_type = surf.get("type", "")
                                        st.write(f"        • {surf_name} ({surf_type})")
            
            # Surfaces (if not nested under zones)
            surfaces = geom.get("surfaces", {})
            if surfaces and not zones:
                if isinstance(surfaces, dict):
                    total = sum(len(v) for v in surfaces.values() if isinstance(v, list))
                    with st.expander(f"🧱 Surfaces ({total})", expanded=False):
                        for category, surf_list in surfaces.items():
                            if isinstance(surf_list, list):
                                render_tree_node(category, surf_list, level=2)
                elif isinstance(surfaces, list):
                    with st.expander(f"🧱 Surfaces ({len(surfaces)})", expanded=False):
                        for surf in surfaces:
                            surf_name = surf.get("name", surf.get("id", "Unknown"))
                            st.write(f"    • {surf_name}")
            
            # Openings
            openings = geom.get("openings", {})
            if openings:
                if isinstance(openings, dict):
                    total = sum(len(v) for v in openings.values() if isinstance(v, list))
                    with st.expander(f"🪟 Openings ({total})", expanded=False):
                        for category, open_list in openings.items():
                            if isinstance(open_list, list):
                                render_tree_node(category, open_list, level=2)
    
    # Catalogs level
    if "catalogs" in model:
        with st.expander("📚 Catalogs", expanded=False):
            catalogs = model["catalogs"]
            for cat_name, cat_items in catalogs.items():
                if isinstance(cat_items, list):
                    with st.expander(f"📖 {cat_name.replace('_', ' ').title()} ({len(cat_items)})", expanded=False):
                        for item in cat_items:
                            if isinstance(item, dict):
                                item_name = item.get("name", item.get("id", "Unknown"))
                                with st.expander(f"    • {item_name}", expanded=False):
                                    st.json(item)
                            else:
                                st.write(f"    • {item}")
    
    # Systems level
    if "systems" in model:
        with st.expander("🔧 Systems", expanded=False):
            systems = model["systems"]
            
            hvac = systems.get("hvac", [])
            if hvac:
                with st.expander(f"❄️ HVAC Systems ({len(hvac)})", expanded=False):
                    for sys in hvac:
                        sys_name = sys.get("name", sys.get("id", "Unknown"))
                        st.write(f"    • {sys_name}")
                        st.json(sys)
            
            dhw = systems.get("dhw", [])
            if dhw:
                with st.expander(f"🚿 DHW Systems ({len(dhw)})", expanded=False):
                    for sys in dhw:
                        sys_name = sys.get("name", sys.get("id", "Unknown"))
                        st.write(f"    • {sys_name}")
                        st.json(sys)
            
            pv = systems.get("pv", [])
            if pv:
                with st.expander(f"☀️ PV Arrays ({len(pv)})", expanded=False):
                    for sys in pv:
                        sys_name = sys.get("name", sys.get("id", "Unknown"))
                        st.write(f"    • {sys_name}")
                        st.json(sys)


def show_active_model():
    st.subheader("Active Model")

    # Check if there's an active model
    if 'active_model' in st.session_state:
        active_model = st.session_state['active_model']
        filename = st.session_state.get('active_model_filename', 'unknown')
        source = st.session_state.get('active_model_source', 'unknown')

        st.info(f"📄 **{filename}** (Source: {source})")
    else:
        st.warning("⚠️ No active model loaded. Please import a model first.")

        # Simulated active model data (fallback)
        active_model = {
            "location": {"latitude": 34.0522, "longitude": -118.2437},
            "geometry": {
                "zones": [{"name": "Zone 1", "area": 200}, {"name": "Zone 2", "area": 150}],
                "surfaces": [{"type": "wall", "area": 100}, {"type": "roof", "area": 200}],
                "openings": [{"type": "window", "area": 10}, {"type": "door", "area": 5}]
            },
            "catalogs": {
                "window_types": ["Type A", "Type B"],
                "construction_types": ["Concrete", "Wood"],
                "hvac_systems": ["System A", "System B"]
            }
        }

    # Display tree-style navigator
    st.divider()
    show_tree_navigator(active_model)

    # Provide export options for the active model
    st.divider()
    st.subheader("💾 Export Active Model")

    col1, col2 = st.columns(2)

    with col1:
        # Export the model as EMJSON v6
        emjson_data = json.dumps(active_model, indent=2, ensure_ascii=False)
        st.download_button(
            label="Download as EMJSON v6",
            data=emjson_data.encode("utf-8"),
            file_name="active_model_v6.json",
            mime="application/json"
        )

    with col2:
        # Export the model as CIBD22x XML
        try:
            xml_data = emjson6_to_cibd22x(active_model)
            st.download_button(
                label="Download as CIBD22x XML",
                data=xml_data.encode("utf-8") if isinstance(xml_data, str) else xml_data,
                file_name="active_model_v6.xml",
                mime="application/xml"
            )
        except Exception as e:
            st.error(f"Export failed: {str(e)}")