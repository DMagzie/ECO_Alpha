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

    # Lazy loading for Location
    with st.expander("📍 Location"):
        loc = active_model.get("project", {}).get("location", {}) or active_model.get("location", {})
        if loc:
            st.json(loc)
        else:
            st.write("No location data available")

    # Lazy loading for Geometry
    with st.expander("🏗️ Geometry"):
        geom = active_model.get("geometry", {})

        zones = geom.get("zones", [])
        st.write(f"**Zones:** {len(zones)}")
        if zones:
            for zone in zones[:5]:  # Show first 5
                name = zone.get("name", "Unknown")
                area = zone.get("floor_area_m2", zone.get("area", 0))
                st.write(f"  - {name}: {area:.1f} m²")
            if len(zones) > 5:
                st.caption(f"... and {len(zones) - 5} more zones")

        surfaces = geom.get("surfaces", {})
        if isinstance(surfaces, dict):
            total_surfaces = sum(len(v) for v in surfaces.values() if isinstance(v, list))
            st.write(f"**Surfaces:** {total_surfaces}")
            for category, surf_list in surfaces.items():
                if isinstance(surf_list, list) and surf_list:
                    st.write(f"  - {category}: {len(surf_list)}")
        elif isinstance(surfaces, list):
            st.write(f"**Surfaces:** {len(surfaces)}")

        openings = geom.get("openings", {})
        if isinstance(openings, dict):
            total_openings = sum(len(v) for v in openings.values() if isinstance(v, list))
            st.write(f"**Openings:** {total_openings}")
            for category, open_list in openings.items():
                if isinstance(open_list, list) and open_list:
                    st.write(f"  - {category}: {len(open_list)}")

    # Lazy loading for Catalogs
    with st.expander("📚 Catalogs"):
        catalogs = active_model.get("catalogs", {})

        for cat_name, cat_items in catalogs.items():
            if isinstance(cat_items, list) and cat_items:
                st.write(f"**{cat_name.replace('_', ' ').title()}:** {len(cat_items)}")
                for item in cat_items[:3]:  # Show first 3
                    if isinstance(item, dict):
                        name = item.get("name", item.get("id", "Unknown"))
                        st.write(f"  - {name}")
                    else:
                        st.write(f"  - {item}")
                if len(cat_items) > 3:
                    st.caption(f"... and {len(cat_items) - 3} more")

    # Lazy loading for Systems
    with st.expander("🔧 Systems"):
        systems = active_model.get("systems", {})

        hvac = systems.get("hvac", [])
        st.write(f"**HVAC Systems:** {len(hvac)}")

        dhw = systems.get("dhw", [])
        st.write(f"**DHW Systems:** {len(dhw)}")

        pv = systems.get("pv", [])
        st.write(f"**PV Arrays:** {len(pv)}")

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