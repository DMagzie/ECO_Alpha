"""
Utilities Page for ECO Tools GUI

Provides various utility tools for building energy modeling:
- Central HPWH Tank Sizing
- HVAC Autosizing (future)
- Unit Conversions (future)
- Code Compliance Checks (future)
"""

import streamlit as st

# Import utility widgets
from gui.components.hpwh_sizer_widget import render_hpwh_sizer


def render_utilities_page():
    """Main utilities page renderer."""

    st.title("🛠️ ECO Tools Utilities")

    st.markdown("""
    Equipment sizing tools and utilities for preliminary building energy modeling.
    Use these tools **before** full CBECC modeling when system sizes are not yet known.
    """)

    # Create tool selector
    tool_options = [
        "Central HPWH Tank Sizing",
        # Future tools can be added here:
        # "HVAC Equipment Sizing",
        # "Unit Conversions",
        # "Code Compliance Checker",
    ]

    selected_tool = st.selectbox(
        "Select Utility Tool",
        options=tool_options,
        index=0,
        help="Choose which utility tool to use"
    )

    st.divider()

    # Render selected tool
    if selected_tool == "Central HPWH Tank Sizing":
        render_hpwh_sizer()

    elif selected_tool == "HVAC Equipment Sizing":
        st.info("🚧 HVAC sizing tool coming soon!")
        st.markdown("""
        **Planned Features:**
        - Cooling/heating load calculations
        - Equipment capacity sizing
        - Duct sizing
        - Climate zone adjustments
        """)

    elif selected_tool == "Unit Conversions":
        st.info("🚧 Unit conversion tool coming soon!")

    elif selected_tool == "Code Compliance Checker":
        st.info("🚧 Compliance checker coming soon!")

    # Help section
    with st.sidebar:
        st.markdown("---")
        st.subheader("📚 Tool Documentation")

        if selected_tool == "Central HPWH Tank Sizing":
            st.markdown("""
            **Central HPWH Sizing Tool**

            Sizes central heat pump water heater systems per Title 24 2025.

            **Quick Guide:**
            1. Enter building parameters (DUs, bedrooms)
            2. Select optimization strategy
            3. Click "Calculate"
            4. Review results and export

            **Key Features:**
            - Code-minimum sizing formula
            - Load shifting optimization
            - CIBD25 model export
            - Thermal storage calculations

            [Full Documentation →](#)
            """)


if __name__ == "__main__":
    # For standalone page testing
    st.set_page_config(
        page_title="ECO Tools - Utilities",
        page_icon="🛠️",
        layout="wide"
    )
    render_utilities_page()
