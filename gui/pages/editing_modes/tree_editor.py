"""
Tree Editor Mode
Direct JSON/tree editing with syntax highlighting and validation.
"""

import streamlit as st
import json
from typing import Dict, Any


def handle_tree_editor(model: Dict[str, Any]):
    """Handle tree-based JSON editor mode."""
    st.header("🌳 Tree Editor Mode")
    st.caption("Direct JSON editing with validation")

    st.info("💡 **Tip**: Edit the JSON structure directly. Changes are validated before being applied to the model.")

    # Create two columns: editor and info
    col1, col2 = st.columns([3, 1])

    with col2:
        st.markdown("### Quick Actions")

        if st.button("💾 Apply Changes", type="primary", use_container_width=True):
            if 'edited_json' in st.session_state and st.session_state.edited_json:
                try:
                    new_model = json.loads(st.session_state.edited_json)
                    st.session_state.active_model = new_model
                    st.success("✅ Changes applied successfully!")
                    st.rerun()
                except json.JSONDecodeError as e:
                    st.error(f"❌ Invalid JSON: {e}")
            else:
                st.warning("No changes to apply")

        if st.button("🔄 Reload Original", use_container_width=True):
            if 'edited_json' in st.session_state:
                del st.session_state.edited_json
            st.rerun()

        if st.button("📋 Copy JSON", use_container_width=True):
            st.code(json.dumps(model, indent=2), language='json')
            st.success("JSON displayed below - copy from code block")

        st.divider()

        # Model statistics
        st.markdown("### Model Statistics")
        stats = collect_model_stats(model)
        for key, value in stats.items():
            st.metric(key, value)

    with col1:
        # JSON editor (text area with syntax highlighting hint)
        st.markdown("### Edit JSON")

        # Initialize with current model if not already editing
        if 'edited_json' not in st.session_state:
            st.session_state.edited_json = json.dumps(model, indent=2)

        edited_json = st.text_area(
            "Model JSON",
            value=st.session_state.edited_json,
            height=600,
            key="json_editor",
            help="Edit the JSON structure directly. Use proper JSON syntax."
        )

        # Update session state
        st.session_state.edited_json = edited_json

        # Validation status
        st.divider()
        col_val1, col_val2 = st.columns(2)

        with col_val1:
            # Validate JSON syntax
            try:
                parsed = json.loads(edited_json)
                st.success("✅ Valid JSON syntax")

                # Check if it's different from current model
                if parsed != model:
                    st.info("📝 Changes detected - click 'Apply Changes' to save")
                else:
                    st.info("No changes detected")

            except json.JSONDecodeError as e:
                st.error(f"❌ Invalid JSON: {e}")

        with col_val2:
            # Show character count
            char_count = len(edited_json)
            line_count = edited_json.count('\n') + 1
            st.caption(f"📊 {line_count:,} lines | {char_count:,} characters")


def collect_model_stats(model: Dict[str, Any]) -> Dict[str, int]:
    """Collect statistics about the model."""
    stats = {}

    # Count zones
    zones = model.get('zones', [])
    if not zones:
        zones = model.get('building', {}).get('zones', [])
    stats['Zones'] = len(zones)

    # Count surfaces
    surface_count = 0
    for zone in zones:
        surfaces = zone.get('surfaces', [])
        surface_count += len(surfaces)
    stats['Surfaces'] = surface_count

    # Count openings
    opening_count = 0
    for zone in zones:
        for surface in zone.get('surfaces', []):
            openings = surface.get('openings', [])
            opening_count += len(openings)
    stats['Openings'] = opening_count

    # Count systems
    systems = model.get('systems', {})
    hvac_count = len(systems.get('hvac', []))
    dhw_count = len(systems.get('dhw', []))
    stats['HVAC Systems'] = hvac_count
    stats['DHW Systems'] = dhw_count

    # Count catalogs
    catalogs = model.get('catalogs', {})
    window_types = len(catalogs.get('window_types', []))
    constructions = len(catalogs.get('construction_types', []))
    materials = len(catalogs.get('materials', []))
    stats['Window Types'] = window_types
    stats['Constructions'] = constructions
    stats['Materials'] = materials

    return stats
