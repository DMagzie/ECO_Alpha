"""
Visual Editor Mode
Scratch/Blockly-style visual programming interface for building model editing.

This mode provides a drag-and-drop visual interface where building components
(zones, surfaces, systems) are represented as visual blocks that can be configured
by clicking and editing properties in a side panel.

Based on Google Blockly (https://developers.google.com/blockly) and MIT Scratch concepts.
"""

import streamlit as st
import json
import sys
from pathlib import Path
from typing import Dict, Any, List, Optional
import streamlit.components.v1 as components

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
    from explorer_gui.utils.autosizing import AutoSizer
    AUTOSIZING_AVAILABLE = True
except ImportError:
    AUTOSIZING_AVAILABLE = False


def handle_visual_editor(model: Dict[str, Any]):
    """Handle visual coding style editor mode."""
    st.header("🎨 Visual Editor Mode (Beta)")
    st.caption("Drag-and-drop visual editing inspired by Scratch and Blockly")

    # Show development status
    st.info("""
    🚧 **Under Development**: This mode is in early development.

    **Vision**: A visual programming interface where you can:
    - Drag building components from a palette
    - Connect components visually (zones → surfaces → openings)
    - Configure properties by clicking on blocks
    - See the building structure as a visual flowchart
    - Export to EMJSON when done

    **Technology Stack**:
    - **Google Blockly** for visual block programming
    - **Streamlit Components** for embedding Blockly workspace
    - **Custom block definitions** for building elements
    """)

    # Show current implementation status
    with st.expander("📋 Implementation Roadmap", expanded=True):
        st.markdown("""
        ### Phase 1: Block Definition (Current Phase)
        - [ ] Define block types for each model element:
          - Zone block
          - Surface block (wall, roof, floor)
          - Opening block (window, door)
          - HVAC system block
          - DHW system block
          - Material/Construction blocks

        ### Phase 2: Blockly Integration
        - [ ] Create custom Blockly workspace
        - [ ] Embed Blockly in Streamlit using `components.html()`
        - [ ] Define custom block shapes and connections
        - [ ] Implement property editing panel

        ### Phase 3: Model Conversion
        - [ ] Convert visual blocks → EMJSON
        - [ ] Convert EMJSON → visual blocks (for editing existing models)
        - [ ] Validation of block connections

        ### Phase 4: Advanced Features
        - [ ] Templates as reusable block groups
        - [ ] Copy/paste blocks
        - [ ] Undo/redo
        - [ ] Auto-layout
        - [ ] 3D preview integration
        """)

    # Show concept mockup
    with st.expander("💡 Concept Mockup", expanded=False):
        st.markdown("""
        ### Visual Block Structure

        ```
        ┌─────────────────────────────────────┐
        │  🏢 Zone: "Living Room"             │
        │  ├─ Floor Area: 400 sq ft           │
        │  ├─ Ceiling Height: 9 ft            │
        │  └─ Type: Living Space              │
        └──┬──────────────────────────────────┘
           │
           ├─► ┌────────────────────────────┐
           │   │  🧱 Surface: "North Wall"   │
           │   │  ├─ Type: ExteriorWall     │
           │   │  ├─ Area: 120 sq ft        │
           │   │  └─ Construction: Wall-R19 │
           │   └──┬─────────────────────────┘
           │      │
           │      └─► ┌─────────────────────┐
           │          │  🪟 Window: "Win-1"  │
           │          │  ├─ Area: 20 sq ft  │
           │          │  └─ Type: DblPane   │
           │          └─────────────────────┘
           │
           └─► ┌────────────────────────────┐
               │  🧱 Surface: "South Wall"   │
               │  ├─ Type: ExteriorWall     │
               │  └─ Area: 120 sq ft        │
               └────────────────────────────┘
        ```

        ### Drag-and-Drop Workflow
        1. **Palette** (left): Drag components
        2. **Workspace** (center): Drop and connect
        3. **Properties** (right): Click to edit
        4. **Export** (bottom): Generate EMJSON
        """)

    # Technical details for developers
    with st.expander("🛠️ Technical Implementation Details"):
        st.markdown("""
        ### Blockly Integration with Streamlit

        **Option 1: Streamlit Components (Recommended)**
        ```python
        import streamlit.components.v1 as components

        # Create custom HTML with Blockly
        blockly_html = '''
        <html>
        <head>
            <script src="https://unpkg.com/blockly/blockly.min.js"></script>
        </head>
        <body>
            <div id="blocklyDiv" style="height: 600px; width: 100%;"></div>
            <script>
                var workspace = Blockly.inject('blocklyDiv', {
                    toolbox: /* Custom toolbox XML */
                });
            </script>
        </body>
        </html>
        '''

        components.html(blockly_html, height=600)
        ```

        **Option 2: Custom Streamlit Component**
        Create a React-based Streamlit component with Blockly integrated.

        ### Block Definitions (Example: Zone Block)

        ```javascript
        Blockly.Blocks['zone'] = {
          init: function() {
            this.appendDummyInput()
                .appendField("🏢 Zone")
                .appendField(new Blockly.FieldTextInput("Zone Name"), "NAME");
            this.appendDummyInput()
                .appendField("Floor Area")
                .appendField(new Blockly.FieldNumber(0), "AREA")
                .appendField("sq ft");
            this.appendDummyInput()
                .appendField("Ceiling Height")
                .appendField(new Blockly.FieldNumber(9), "HEIGHT")
                .appendField("ft");
            this.appendStatementInput("SURFACES")
                .setCheck("Surface")
                .appendField("Surfaces");
            this.setColour(230);
            this.setPreviousStatement(true, "Zone");
            this.setNextStatement(true, "Zone");
          }
        };
        ```

        ### Data Conversion

        **Blocks → EMJSON:**
        1. Traverse workspace block tree
        2. Extract properties from each block
        3. Build hierarchical EMJSON structure
        4. Validate references (IDs, types)

        **EMJSON → Blocks:**
        1. Parse EMJSON zones/surfaces/openings
        2. Create corresponding blocks
        3. Set block properties from model
        4. Connect blocks hierarchically
        5. Layout blocks in workspace

        ### Open Source Resources
        - **Blockly**: https://github.com/google/blockly
        - **Blockly Samples**: https://github.com/google/blockly-samples
        - **Scratch Blocks**: https://github.com/scratchfoundation/scratch-blocks
        - **Streamlit Components**: https://docs.streamlit.io/library/components
        """)

    # Prototype/Demo section
    st.divider()
    st.subheader("🎮 Interactive Prototype")

    # Temporary placeholder UI to demonstrate concept
    show_prototype_ui(model)


def show_prototype_ui(model: Dict[str, Any]):
    """Show a simplified prototype of the visual editor."""
    st.info("This is a simplified prototype demonstrating the concept. Full Blockly integration coming soon.")

    col1, col2, col3 = st.columns([1, 2, 1])

    with col1:
        st.markdown("### 📦 Component Palette")

        st.markdown("**Zones**")
        if st.button("🏢 Add Zone", use_container_width=True):
            st.session_state.visual_action = "add_zone"

        st.markdown("**Surfaces**")
        if st.button("🧱 Add Wall", use_container_width=True):
            st.session_state.visual_action = "add_wall"
        if st.button("🏠 Add Roof", use_container_width=True):
            st.session_state.visual_action = "add_roof"

        st.markdown("**Openings**")
        if st.button("🪟 Add Window", use_container_width=True):
            st.session_state.visual_action = "add_window"
        if st.button("🚪 Add Door", use_container_width=True):
            st.session_state.visual_action = "add_door"

        st.markdown("**Systems**")
        if st.button("❄️ Add HVAC", use_container_width=True):
            st.session_state.visual_action = "add_hvac"
        if st.button("🚿 Add DHW", use_container_width=True):
            st.session_state.visual_action = "add_dhw"

    with col2:
        st.markdown("### 🎨 Visual Workspace")

        # Show visual representation of model
        zones = model.get('zones', [])
        if not zones:
            zones = model.get('building', {}).get('zones', [])

        if zones:
            for i, zone in enumerate(zones):
                with st.container():
                    col_a, col_b = st.columns([3, 1])
                    with col_a:
                        zone_name = zone.get('name', f'Zone {i+1}')
                        st.markdown(f"### 🏢 {zone_name}")

                        # Show surfaces
                        surfaces = zone.get('surfaces', [])
                        if surfaces:
                            st.caption(f"**Surfaces**: {len(surfaces)}")
                            for j, surface in enumerate(surfaces[:3]):  # Show first 3
                                surf_type = surface.get('type', 'Unknown')
                                st.markdown(f"  └─ 🧱 {surf_type}")

                    with col_b:
                        if st.button("⚙️ Edit", key=f"edit_zone_{i}"):
                            st.session_state.selected_component = ('zone', i)
        else:
            st.info("No zones in model. Add a zone from the palette!")

        # Show action feedback
        if 'visual_action' in st.session_state:
            action = st.session_state.visual_action
            st.success(f"Action: {action} (This would create a new component)")
            del st.session_state.visual_action

    with col3:
        st.markdown("### ⚙️ Properties Panel")

        if 'selected_component' in st.session_state:
            comp_type, comp_idx = st.session_state.selected_component

            if comp_type == 'zone':
                zones = model.get('zones', [])
                if not zones:
                    zones = model.get('building', {}).get('zones', [])

                if comp_idx < len(zones):
                    zone = zones[comp_idx]

                    st.markdown(f"**Editing**: {zone.get('name', 'Zone')}")

                    # Editable properties
                    new_name = st.text_input("Name", value=zone.get('name', ''), key=f"visual_zone_name_{comp_idx}")
                    new_type = st.text_input("Type", value=zone.get('type', ''), key=f"visual_zone_type_{comp_idx}")

                    if st.button("💾 Save Changes", key=f"visual_zone_save_{comp_idx}"):
                        zone['name'] = new_name
                        zone['type'] = new_type
                        st.success("Changes saved!")
                        st.rerun()

                    if st.button("❌ Close", key=f"visual_zone_close_{comp_idx}"):
                        del st.session_state.selected_component
                        st.rerun()

            elif comp_type == 'hvac':
                systems = model.get('systems', {})
                hvac_systems = systems.get('hvac', [])

                if comp_idx < len(hvac_systems):
                    hvac = hvac_systems[comp_idx]

                    st.markdown(f"**Editing HVAC**: {hvac.get('name', 'HVAC System')}")

                    # Editable properties
                    new_name = st.text_input("Name", value=hvac.get('name', ''), key=f"visual_hvac_name_{comp_idx}")

                    cooling_kw = st.number_input(
                        "Cooling Capacity (kW)",
                        value=float(hvac.get('cooling_capacity_kw', 0.0)),
                        min_value=0.0,
                        format="%.2f",
                        key=f"visual_hvac_cool_{comp_idx}"
                    )

                    heating_kw = st.number_input(
                        "Heating Capacity (kW)",
                        value=float(hvac.get('heating_capacity_kw', 0.0)),
                        min_value=0.0,
                        format="%.2f",
                        key=f"visual_hvac_heat_{comp_idx}"
                    )

                    # Autosizing section
                    if AUTOSIZING_AVAILABLE:
                        st.divider()
                        st.markdown("**🔧 Autosize**")

                        zones = model.get('zones', [])
                        if not zones:
                            zones = model.get('building', {}).get('zones', [])

                        if zones:
                            building_type = st.selectbox(
                                "Building Type",
                                ["multifamily_residential", "commercial_office", "warehouse_industrial"],
                                key=f"visual_hvac_bldg_{comp_idx}"
                            )

                            climate_zone = st.selectbox(
                                "Climate Zone",
                                ["3", "4", "10", "13"],
                                key=f"visual_hvac_cz_{comp_idx}"
                            )

                            if st.button("🔧 Calculate", key=f"visual_hvac_calc_{comp_idx}"):
                                total_floor_area = sum(
                                    zone.get("floor_area_sqft", zone.get("floor_area_sf", zone.get("area", 0)))
                                    for zone in zones
                                )

                                capacity = AutoSizer.calculate_hvac_capacity(
                                    floor_area_sqft=total_floor_area,
                                    building_type=building_type,
                                    climate_zone=climate_zone
                                )

                                cooling_kw = capacity["cooling_capacity_kw"]
                                heating_kw = capacity["heating_capacity_kw"]

                                st.success(f"✅ {cooling_kw:.2f} kW cool, {heating_kw:.2f} kW heat")

                    if st.button("💾 Save Changes", key=f"visual_hvac_save_{comp_idx}"):
                        hvac['name'] = new_name
                        hvac['cooling_capacity_kw'] = cooling_kw
                        hvac['heating_capacity_kw'] = heating_kw
                        st.success("Changes saved!")
                        st.rerun()

                    if st.button("❌ Close", key=f"visual_hvac_close_{comp_idx}"):
                        del st.session_state.selected_component
                        st.rerun()

            elif comp_type == 'dhw':
                systems = model.get('systems', {})
                dhw_systems = systems.get('dhw', [])

                if comp_idx < len(dhw_systems):
                    dhw = dhw_systems[comp_idx]

                    st.markdown(f"**Editing DHW**: {dhw.get('name', 'DHW System')}")

                    # Editable properties
                    new_name = st.text_input("Name", value=dhw.get('name', ''), key=f"visual_dhw_name_{comp_idx}")

                    capacity_gal = st.number_input(
                        "Tank Capacity (gal)",
                        value=float(dhw.get('capacity_gallons', 150.0)),
                        min_value=0.0,
                        format="%.1f",
                        key=f"visual_dhw_cap_{comp_idx}"
                    )

                    # Autosizing section
                    if AUTOSIZING_AVAILABLE:
                        st.divider()
                        st.markdown("**🔧 Autosize**")

                        zones = model.get('zones', [])
                        if not zones:
                            zones = model.get('building', {}).get('zones', [])

                        if zones:
                            building_type = st.selectbox(
                                "Building Type",
                                ["multifamily", "commercial_office"],
                                key=f"visual_dhw_bldg_{comp_idx}"
                            )

                            if building_type == "multifamily":
                                num_units = st.number_input(
                                    "Units",
                                    min_value=1,
                                    value=20,
                                    key=f"visual_dhw_units_{comp_idx}"
                                )
                                bedrooms = st.number_input(
                                    "BR/Unit",
                                    min_value=0,
                                    max_value=4,
                                    value=2,
                                    key=f"visual_dhw_br_{comp_idx}"
                                )
                            else:
                                num_employees = st.number_input(
                                    "Employees",
                                    min_value=1,
                                    value=50,
                                    key=f"visual_dhw_emp_{comp_idx}"
                                )

                            if st.button("🔧 Calculate", key=f"visual_dhw_calc_{comp_idx}"):
                                if building_type == "multifamily":
                                    capacity = AutoSizer.calculate_dhw_capacity(
                                        building_type=building_type,
                                        num_units=num_units,
                                        num_bedrooms_per_unit=bedrooms
                                    )
                                else:
                                    capacity = AutoSizer.calculate_dhw_capacity(
                                        building_type=building_type,
                                        num_employees=num_employees
                                    )

                                capacity_gal = capacity["tank_capacity_gallons"]

                                st.success(f"✅ {capacity_gal:.0f} gal tank")

                    if st.button("💾 Save Changes", key=f"visual_dhw_save_{comp_idx}"):
                        dhw['name'] = new_name
                        dhw['capacity_gallons'] = capacity_gal
                        dhw['capacity_liters'] = round(capacity_gal * 3.78541, 1)
                        st.success("Changes saved!")
                        st.rerun()

                    if st.button("❌ Close", key=f"visual_dhw_close_{comp_idx}"):
                        del st.session_state.selected_component
                        st.rerun()

        else:
            st.info("Click '⚙️ Edit' on a component to edit its properties")

    # Development notes
    st.divider()
    st.caption("""
    **Note**: This is a concept prototype. The full implementation will use Google Blockly
    for a true drag-and-drop visual programming experience with proper block connections,
    custom block shapes, and real-time EMJSON generation.
    """)


# Future: Full Blockly implementation
# This will be a separate module when fully developed
def create_blockly_workspace():
    """
    Future function to create full Blockly workspace.
    Will use streamlit.components.html() to embed Blockly.
    """
    pass


def blocks_to_emjson(blocks):
    """
    Future function to convert Blockly blocks to EMJSON.
    """
    pass


def emjson_to_blocks(model):
    """
    Future function to convert EMJSON to Blockly blocks.
    """
    pass
