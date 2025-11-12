"""
Multi-Modal EMJSON Model Editing Page
Provides four different editing modes:
1. Tree Editor - Direct JSON editing
2. Tables/Forms - Form-based editing with expandable tables
3. Wizard - Guided model building
4. Visual Editor - Scratch/Blockly-style visual programming
"""

import streamlit as st
import sys
from pathlib import Path
from typing import Dict, Any

# Add project root to path
ROOT = Path(__file__).resolve().parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Add gui to path
EXPLORER_GUI = ROOT / "gui"
if str(EXPLORER_GUI) not in sys.path:
    sys.path.insert(0, str(EXPLORER_GUI))

# Import editing modes
from gui.pages.editing_modes.tree_editor import handle_tree_editor
from gui.pages.editing_modes.tables_editor import handle_tables_editor
from gui.pages.editing_modes.visual_editor import handle_visual_editor


def handle_editing():
    """Main editing page handler with mode selection."""
    st.title("✏️ Edit Model")

    # Check if we have an active model
    if "active_model" not in st.session_state or st.session_state.active_model is None:
        st.warning("⚠️ No active model loaded. Please import a model first.")
        st.info("Go to the **Import** page to load a CIBD22X, GEM, or EMJSON file.")

        col1, col2 = st.columns(2)
        with col1:
            if st.button("📁 Go to Import Page", use_container_width=True):
                st.session_state.nav_main = "Import"
                st.rerun()
        return

    model = st.session_state.active_model

    # Mode selector
    st.divider()

    # Initialize mode if not set
    if 'editing_mode' not in st.session_state:
        st.session_state.editing_mode = "Tables/Forms"

    # Mode selection with visual cards
    st.subheader("📝 Select Editing Mode")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        with st.container():
            st.markdown("### 🌳 Tree Editor")
            st.caption("Direct JSON editing with syntax highlighting and validation")
            st.markdown("**Best for:**")
            st.markdown("- Quick edits")
            st.markdown("- Advanced users")
            st.markdown("- Bulk changes")

            if st.button("Use Tree Editor", use_container_width=True, type="primary" if st.session_state.editing_mode == "Tree" else "secondary"):
                st.session_state.editing_mode = "Tree"
                st.rerun()

    with col2:
        with st.container():
            st.markdown("### 📊 Tables/Forms")
            st.caption("Form-based editing with expandable tables for each component")
            st.markdown("**Best for:**")
            st.markdown("- Detailed editing")
            st.markdown("- Component by component")
            st.markdown("- Property inspection")

            if st.button("Use Tables/Forms", use_container_width=True, type="primary" if st.session_state.editing_mode == "Tables/Forms" else "secondary"):
                st.session_state.editing_mode = "Tables/Forms"
                st.rerun()

    with col3:
        with st.container():
            st.markdown("### 🧙 Wizard")
            st.caption("Guided step-by-step model building with templates")
            st.markdown("**Best for:**")
            st.markdown("- New models")
            st.markdown("- Adding systems")
            st.markdown("- Guided workflow")

            if st.button("Use Wizard", use_container_width=True, type="primary" if st.session_state.editing_mode == "Wizard" else "secondary"):
                st.session_state.editing_mode = "Wizard"
                # Redirect to wizard page
                st.session_state.nav_main = "🧙 Build Model"
                st.rerun()

    with col4:
        with st.container():
            st.markdown("### 🎨 Visual Editor")
            st.caption("Scratch/Blockly-style drag-and-drop visual programming")
            st.markdown("**Best for:**")
            st.markdown("- Visual learners")
            st.markdown("- Component relationships")
            st.markdown("- Interactive building")
            st.caption("🚧 _Beta_")

            if st.button("Use Visual Editor", use_container_width=True, type="primary" if st.session_state.editing_mode == "Visual" else "secondary"):
                st.session_state.editing_mode = "Visual"
                st.rerun()

    st.divider()

    # Show current mode badge
    mode_emoji = {
        "Tree": "🌳",
        "Tables/Forms": "📊",
        "Wizard": "🧙",
        "Visual": "🎨"
    }

    st.markdown(f"## {mode_emoji.get(st.session_state.editing_mode, '✏️')} {st.session_state.editing_mode} Mode")

    # Route to appropriate editor
    if st.session_state.editing_mode == "Tree":
        handle_tree_editor(model)

    elif st.session_state.editing_mode == "Tables/Forms":
        handle_tables_editor(model)

    elif st.session_state.editing_mode == "Visual":
        handle_visual_editor(model)

    elif st.session_state.editing_mode == "Wizard":
        # This shouldn't be reached since we redirect to wizard page
        st.info("Redirecting to Wizard...")
        st.session_state.nav_main = "🧙 Build Model"
        st.rerun()

    else:
        st.error(f"Unknown editing mode: {st.session_state.editing_mode}")

    # Mode switching reminder
    st.divider()
    st.caption("💡 **Tip**: You can switch between editing modes at any time. Your changes are saved to the active model.")
