"""
Template Browser Page
Explore and preview available HVAC and DHW system templates.
"""

import streamlit as st
import json
import sys
from pathlib import Path
from typing import Dict, Any, List, Optional

# Add project root to path
ROOT = Path(__file__).resolve().parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

EXPLORER_GUI = ROOT / "gui"
if str(EXPLORER_GUI) not in sys.path:
    sys.path.insert(0, str(EXPLORER_GUI))


def load_templates(template_name: str) -> Dict[str, Any]:
    """Load a template file."""
    try:
        template_path = EXPLORER_GUI / "templates" / template_name
        with open(template_path, 'r') as f:
            return json.load(f)
    except Exception as e:
        st.error(f"Error loading {template_name}: {e}")
        return {}


def show_hvac_template_card(template_key: str, template: Dict[str, Any], category: str):
    """Display an HVAC template as a card."""
    with st.container():
        col1, col2 = st.columns([3, 1])

        with col1:
            st.markdown(f"### {template.get('name', template_key)}")
            st.caption(f"**Category**: {category.replace('_', ' ').title()}")

            description = template.get('description', 'No description available')
            st.markdown(f"_{description}_")

            # Key specifications
            st.markdown("**Key Specifications:**")

            # System type
            system_type = template.get('system_type', 'N/A')
            equipment_type = template.get('equipment_type', 'N/A')
            st.markdown(f"- **Type**: {system_type} / {equipment_type}")

            # Efficiency
            efficiency = template.get('efficiency', {})
            if efficiency:
                eff_items = []
                if 'cooling_seer2' in efficiency:
                    eff_items.append(f"SEER2: {efficiency['cooling_seer2']}")
                if 'heating_hspf2' in efficiency:
                    eff_items.append(f"HSPF2: {efficiency['heating_hspf2']}")
                if 'cooling_eer2' in efficiency:
                    eff_items.append(f"EER2: {efficiency['cooling_eer2']}")
                if eff_items:
                    st.markdown(f"- **Efficiency**: {', '.join(eff_items)}")

            # Capacity ranges
            if 'sizes' in template:
                sizes = template['sizes']
                size_range = []
                for size_key, size_data in sizes.items():
                    cooling_btu = size_data.get('cooling_capacity_btu', 0)
                    cooling_tons = cooling_btu / 12000
                    size_range.append(f"{size_key.title()}: {cooling_tons:.1f} tons")
                if size_range:
                    st.markdown(f"- **Sizes**: {', '.join(size_range)}")
            elif 'capacity' in template:
                capacity = template['capacity']
                cooling_btu = capacity.get('cooling_capacity_btu', 0)
                cooling_tons = cooling_btu / 12000
                st.markdown(f"- **Capacity**: {cooling_tons:.1f} tons")

            # Features
            features = template.get('features', {})
            if features:
                feature_list = [f"{k.replace('_', ' ').title()}: {v}" for k, v in features.items() if k != 'notes']
                if feature_list:
                    st.markdown(f"- **Features**: {', '.join(feature_list[:3])}")

        with col2:
            # Action buttons
            if st.button("📋 Details", key=f"hvac_details_{category}_{template_key}", use_container_width=True):
                st.session_state.template_detail_view = {
                    'type': 'hvac',
                    'category': category,
                    'key': template_key,
                    'template': template
                }
                st.rerun()

            if st.button("✨ Use Template", key=f"hvac_use_{category}_{template_key}", use_container_width=True):
                st.session_state.selected_template = {
                    'type': 'hvac',
                    'category': category,
                    'key': template_key,
                    'template': template
                }
                st.success("Template selected!")


def show_dhw_template_card(template_key: str, template: Dict[str, Any], category: str):
    """Display a DHW template as a card."""
    with st.container():
        col1, col2 = st.columns([3, 1])

        with col1:
            st.markdown(f"### {template.get('name', template_key)}")
            st.caption(f"**Category**: {category.replace('_', ' ').title()}")

            description = template.get('description', 'No description available')
            st.markdown(f"_{description}_")

            # Key specifications
            st.markdown("**Key Specifications:**")

            # System type
            system_type = template.get('system_type', 'N/A')
            st.markdown(f"- **Type**: {system_type}")

            # Water heater configuration
            if 'water_heater' in template:
                wh = template['water_heater']
                fuel = wh.get('fuel', 'N/A')
                ef = wh.get('energy_factor', 'N/A')
                tank_gal = wh.get('tank_volume_gal', 'N/A')
                st.markdown(f"- **Configuration**: {fuel.title()}, EF: {ef}, Tank: {tank_gal} gal")

            elif 'water_heater_configurations' in template:
                configs = template['water_heater_configurations']
                num_configs = len(configs)
                st.markdown(f"- **Configurations**: {num_configs} sizes available")

                # Show range
                if configs:
                    first_config = next(iter(configs.values()))
                    if 'total_capacity_btu' in first_config:
                        st.markdown(f"- **Capacity Range**: {first_config.get('total_capacity_btu', 0):,} BTU/h+")

            elif 'water_heater_options' in template:
                options = template['water_heater_options']
                st.markdown(f"- **Options**: {len(options)} types available")

            # Compliance features
            if 'california_compliance' in template:
                compliance = template['california_compliance']
                if 'efficiency_minimum' in compliance:
                    st.markdown(f"- **CA Compliance**: {compliance['efficiency_minimum']}")

        with col2:
            # Action buttons
            if st.button("📋 Details", key=f"dhw_details_{category}_{template_key}", use_container_width=True):
                st.session_state.template_detail_view = {
                    'type': 'dhw',
                    'category': category,
                    'key': template_key,
                    'template': template
                }
                st.rerun()

            if st.button("✨ Use Template", key=f"dhw_use_{category}_{template_key}", use_container_width=True):
                st.session_state.selected_template = {
                    'type': 'dhw',
                    'category': category,
                    'key': template_key,
                    'template': template
                }
                st.success("Template selected!")


def show_template_detail_modal():
    """Show detailed view of a template in a modal-like layout."""
    if 'template_detail_view' not in st.session_state:
        return

    detail = st.session_state.template_detail_view
    template = detail['template']
    template_type = detail['type']

    with st.container():
        col1, col2 = st.columns([4, 1])
        with col1:
            st.markdown(f"## 📋 {template.get('name', 'Template Details')}")
            st.caption(f"**{template_type.upper()}** | {detail['category'].replace('_', ' ').title()}")
        with col2:
            if st.button("✖ Close", use_container_width=True):
                del st.session_state.template_detail_view
                st.rerun()

        st.divider()

        # Full description
        description = template.get('description', 'No description available')
        st.markdown(f"**Description**: {description}")

        # Show full JSON
        with st.expander("📄 Full Template Data", expanded=False):
            st.json(template)

        # Specific details based on type
        if template_type == 'hvac':
            show_hvac_details(template)
        else:
            show_dhw_details(template)

        # Use button at bottom
        st.divider()
        if st.button("✨ Use This Template", type="primary", use_container_width=True):
            st.session_state.selected_template = {
                'type': template_type,
                'category': detail['category'],
                'key': detail['key'],
                'template': template
            }
            del st.session_state.template_detail_view
            st.success("Template selected! Go to the wizard to apply it.")
            st.rerun()


def show_hvac_details(template: Dict[str, Any]):
    """Show detailed HVAC template information."""
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("### System Configuration")
        st.markdown(f"**System Type**: {template.get('system_type', 'N/A')}")
        st.markdown(f"**Equipment Type**: {template.get('equipment_type', 'N/A')}")
        st.markdown(f"**Distribution**: {template.get('distribution', 'N/A')}")

        # Sizes
        if 'sizes' in template:
            st.markdown("### Available Sizes")
            for size_key, size_data in template['sizes'].items():
                with st.expander(f"{size_key.title()} Size"):
                    st.json(size_data)
        elif 'capacity' in template:
            st.markdown("### Capacity")
            st.json(template['capacity'])

    with col2:
        # Efficiency
        if 'efficiency' in template:
            st.markdown("### Efficiency Ratings")
            efficiency = template['efficiency']
            for key, value in efficiency.items():
                st.markdown(f"**{key.replace('_', ' ').title()}**: {value}")

        # Features
        if 'features' in template:
            st.markdown("### Features")
            features = template['features']
            for key, value in features.items():
                st.markdown(f"**{key.replace('_', ' ').title()}**: {value}")

        # Typical zones
        if 'typical_zones' in template:
            st.markdown("### Typical Applications")
            for zone in template['typical_zones']:
                st.markdown(f"- {zone}")


def show_dhw_details(template: Dict[str, Any]):
    """Show detailed DHW template information."""
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("### System Configuration")
        st.markdown(f"**System Type**: {template.get('system_type', 'N/A')}")

        if 'central_dhw_type' in template:
            st.markdown(f"**Central DHW Type**: {template.get('central_dhw_type', 'N/A')}")

        if 'tank_configuration' in template:
            st.markdown(f"**Tank Configuration**: {template.get('tank_configuration', 'N/A')}")

        # Recirculation
        if 'recirculation' in template:
            st.markdown("### Recirculation")
            st.json(template['recirculation'])

        # Water heater configurations
        if 'water_heater_configurations' in template:
            st.markdown("### Building Size Configurations")
            for config_key, config_data in template['water_heater_configurations'].items():
                with st.expander(f"{config_key.replace('_', ' ').title()}"):
                    st.json(config_data)

    with col2:
        # Water heater options
        if 'water_heater_options' in template:
            st.markdown("### Water Heater Options")
            for option_key, option_data in template['water_heater_options'].items():
                with st.expander(f"{option_key.title()}"):
                    st.json(option_data)

        # Single water heater
        if 'water_heater' in template:
            st.markdown("### Water Heater")
            st.json(template['water_heater'])

        # California compliance
        if 'california_compliance' in template:
            st.markdown("### California Title 24 Compliance")
            compliance = template['california_compliance']
            for key, value in compliance.items():
                st.markdown(f"**{key.replace('_', ' ').title()}**: {value}")


def handle_template_browser():
    """Main template browser handler."""
    st.title("📚 Template Browser")
    st.caption("Explore available HVAC and DHW system templates from real California Title 24 projects")

    # Show detail modal if active
    if 'template_detail_view' in st.session_state:
        show_template_detail_modal()
        return

    # Main browser interface
    tab1, tab2 = st.tabs(["❄️ HVAC Templates", "🚿 DHW Templates"])

    with tab1:
        show_hvac_browser()

    with tab2:
        show_dhw_browser()


def show_hvac_browser():
    """Show HVAC template browser."""
    st.header("HVAC System Templates")
    st.info("💡 All templates include California Title 24 2022/2025 compliance features (SEER2, HSPF2, EER2)")

    # Load templates
    hvac_templates = load_templates("hvac_templates.json")
    if not hvac_templates or '_metadata' not in hvac_templates:
        st.error("Could not load HVAC templates")
        return

    # Remove metadata
    metadata = hvac_templates.pop('_metadata', {})

    # Show metadata
    with st.expander("ℹ️ Template Source Information"):
        st.json(metadata)

    # Category filter
    categories = list(hvac_templates.keys())
    category_names = {
        'multifamily_residential': 'Multifamily Residential',
        'commercial_office': 'Commercial Office',
        'warehouse_industrial': 'Warehouse / Industrial'
    }

    selected_category = st.selectbox(
        "Filter by Building Type",
        ['All'] + categories,
        format_func=lambda x: category_names.get(x, x.replace('_', ' ').title()) if x != 'All' else 'All Building Types'
    )

    # Display templates
    if selected_category == 'All':
        for category_key, category_templates in hvac_templates.items():
            st.subheader(f"🏢 {category_names.get(category_key, category_key.replace('_', ' ').title())}")

            for template_key, template in category_templates.items():
                show_hvac_template_card(template_key, template, category_key)

            st.divider()
    else:
        category_templates = hvac_templates.get(selected_category, {})
        if not category_templates:
            st.warning(f"No templates found for {selected_category}")
            return

        st.subheader(f"🏢 {category_names.get(selected_category, selected_category.replace('_', ' ').title())}")

        for template_key, template in category_templates.items():
            show_hvac_template_card(template_key, template, selected_category)


def show_dhw_browser():
    """Show DHW template browser."""
    st.header("DHW / SHW System Templates")
    st.info("💡 All templates include California Title 24 compliant energy factors and design criteria")

    # Load templates
    dhw_templates = load_templates("dhw_templates.json")
    if not dhw_templates or '_metadata' not in dhw_templates:
        st.error("Could not load DHW templates")
        return

    # Remove metadata
    metadata = dhw_templates.pop('_metadata', {})

    # Remove sizing rules and requirements sections
    dhw_templates.pop('sizing_rules_of_thumb', None)
    dhw_templates.pop('california_title_24_requirements', None)

    # Show metadata
    with st.expander("ℹ️ Template Source Information"):
        st.json(metadata)

    # Category filter
    categories = list(dhw_templates.keys())
    category_names = {
        'multifamily_residential': 'Multifamily Residential',
        'commercial_office': 'Commercial Office',
        'warehouse_industrial': 'Warehouse / Industrial'
    }

    selected_category = st.selectbox(
        "Filter by Building Type",
        ['All'] + categories,
        format_func=lambda x: category_names.get(x, x.replace('_', ' ').title()) if x != 'All' else 'All Building Types',
        key='dhw_category_filter'
    )

    # Display templates
    if selected_category == 'All':
        for category_key, category_templates in dhw_templates.items():
            st.subheader(f"🏢 {category_names.get(category_key, category_key.replace('_', ' ').title())}")

            for template_key, template in category_templates.items():
                show_dhw_template_card(template_key, template, category_key)

            st.divider()
    else:
        category_templates = dhw_templates.get(selected_category, {})
        if not category_templates:
            st.warning(f"No templates found for {selected_category}")
            return

        st.subheader(f"🏢 {category_names.get(selected_category, selected_category.replace('_', ' ').title())}")

        for template_key, template in category_templates.items():
            show_dhw_template_card(template_key, template, selected_category)
