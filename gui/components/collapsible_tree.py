
from __future__ import annotations
from typing import Any, Mapping, Sequence
import streamlit as st

def _is_scalar(x: Any) -> bool:
    """Check if value is a scalar (leaf node in tree)."""
    return isinstance(x, (str, int, float, bool)) or x is None

def _get_node_path(parent_path: str, key: str) -> str:
    """Generate unique path for a tree node."""
    return f"{parent_path}.{key}" if parent_path else str(key)

def _is_expanded(node_path: str) -> bool:
    """Check if a node is expanded in session state."""
    if 'tree_expanded' not in st.session_state:
        st.session_state.tree_expanded = set()
    return node_path in st.session_state.tree_expanded

def _toggle_expand(node_path: str):
    """Toggle expansion state for a node."""
    if 'tree_expanded' not in st.session_state:
        st.session_state.tree_expanded = set()

    if node_path in st.session_state.tree_expanded:
        st.session_state.tree_expanded.remove(node_path)
    else:
        st.session_state.tree_expanded.add(node_path)

def render_collapsible_tree(data: Any, *, label: str = "root", path: str = "", level: int = 0) -> None:
    """
    Render an interactive collapsible tree view with expand/collapse buttons.

    Uses session state to track expansion, avoiding Streamlit's expander nesting limitations.

    Args:
        data: Data to display (dict, list, or scalar)
        label: Display label for this node
        path: Unique path for this node (for tracking expansion state)
        level: Current depth level (for indentation)
    """
    if level == 0:
        st.caption("🌲 Interactive tree · click ▶/▼ to expand/collapse")
        # Add expand/collapse all buttons
        col1, col2, col3 = st.columns([1, 1, 8])
        with col1:
            if st.button("Expand All", key="expand_all", use_container_width=True):
                _expand_all(data, path)
                st.rerun()
        with col2:
            if st.button("Collapse All", key="collapse_all", use_container_width=True):
                st.session_state.tree_expanded = set()
                st.rerun()

    # Generate unique node path
    node_path = _get_node_path(path, label)
    indent = "　" * level

    # Skip None values
    if data is None:
        return

    # Handle scalar values (leaf nodes)
    if _is_scalar(data):
        st.markdown(f"{indent}**{label}:** `{data}`")
        return

    # Handle dictionaries
    if isinstance(data, Mapping):
        # Filter out None values but KEEP empty lists/dicts for geometry section
        is_geometry_section = label == "geometry" or "geometry" in node_path

        if is_geometry_section:
            # For geometry, show even empty collections
            non_null_items = [(k, v) for k, v in data.items() if v is not None]
        else:
            # For other sections, hide empty collections
            non_null_items = [(k, v) for k, v in data.items()
                              if v is not None and (not isinstance(v, (list, dict)) or len(v) > 0)]

        if len(non_null_items) == 0:
            return

        # Create expand/collapse button
        is_expanded = _is_expanded(node_path)
        icon = "▼" if is_expanded else "▶"

        # Use columns for button and label
        col1, col2 = st.columns([0.5, 9.5])
        with col1:
            if st.button(icon, key=f"btn_{node_path}", help="Expand/Collapse"):
                _toggle_expand(node_path)
                st.rerun()
        with col2:
            # Add special highlighting for geometry sections
            if label in ['geometry', 'zones', 'surfaces', 'openings', 'zone_groups']:
                st.markdown(f"{indent}**🏗️ {label}** `dict · {len(non_null_items)} keys`")
            else:
                st.markdown(f"{indent}**{label}** `dict · {len(non_null_items)} keys`")

        # Show children if expanded
        if is_expanded:
            # Prioritize display order for geometry children
            if label == "geometry":
                # Show zones, surfaces, openings first
                priority_keys = ['zones', 'zone_groups', 'surfaces', 'openings']
                priority_items = [(k, v) for k, v in non_null_items if k in priority_keys]
                other_items = [(k, v) for k, v in non_null_items if k not in priority_keys]

                # Show priority items first
                for k, v in priority_items:
                    if _is_scalar(v) and v is not None:
                        st.markdown(f"{indent}　• **{k}:** `{v}`")
                    else:
                        render_collapsible_tree(v, label=k, path=node_path, level=level+1)

                # Then show other items
                for k, v in other_items:
                    if _is_scalar(v) and v is not None:
                        st.markdown(f"{indent}　• **{k}:** `{v}`")
                    else:
                        render_collapsible_tree(v, label=k, path=node_path, level=level+1)
            else:
                # Normal display order
                for k, v in non_null_items:
                    if _is_scalar(v) and v is not None:
                        st.markdown(f"{indent}　• **{k}:** `{v}`")
                    else:
                        render_collapsible_tree(v, label=k, path=node_path, level=level+1)

        return

    # Handle lists
    if isinstance(data, Sequence) and not isinstance(data, (str, bytes, bytearray)):
        # Check if this is a geometry-related list
        is_geometry_list = any(x in node_path for x in ['geometry', 'zones', 'surfaces', 'openings'])

        # Show empty lists if in geometry section, otherwise skip
        if len(data) == 0:
            if is_geometry_list:
                st.markdown(f"{indent}**🏗️ {label}** `list · 0 items (empty)`")
            return

        # Create expand/collapse button
        is_expanded = _is_expanded(node_path)
        icon = "▼" if is_expanded else "▶"

        col1, col2 = st.columns([0.5, 9.5])
        with col1:
            if st.button(icon, key=f"btn_{node_path}", help="Expand/Collapse"):
                _toggle_expand(node_path)
                st.rerun()
        with col2:
            # Highlight geometry-related lists
            if label in ['zones', 'surfaces', 'openings', 'zone_groups']:
                st.markdown(f"{indent}**🏗️ {label}** `list · {len(data)} items`")
            else:
                st.markdown(f"{indent}**{label}** `list · {len(data)} items`")

        # Show children if expanded
        if is_expanded:
            for idx, item in enumerate(data):
                if _is_scalar(item):
                    if item is not None:
                        st.markdown(f"{indent}　• `[{idx}]` {item}")
                elif isinstance(item, Mapping):
                    # Use name/id for list items if available
                    item_name = item.get('name') or item.get('id') or f"Item {idx}"
                    render_collapsible_tree(item, label=f"[{idx}] {item_name}", path=node_path, level=level+1)
                else:
                    render_collapsible_tree(item, label=f"[{idx}]", path=node_path, level=level+1)

        return

    # Fallback for other types
    st.markdown(f"{indent}**{label}:** `{repr(data)[:100]}`")

def _expand_all(data: Any, path: str = "", max_depth: int = 3, current_depth: int = 0):
    """Recursively expand all nodes up to max_depth."""
    if current_depth >= max_depth:
        return

    if 'tree_expanded' not in st.session_state:
        st.session_state.tree_expanded = set()

    if isinstance(data, Mapping):
        for key, value in data.items():
            if value is not None and not _is_scalar(value):
                node_path = _get_node_path(path, str(key))
                st.session_state.tree_expanded.add(node_path)
                _expand_all(value, node_path, max_depth, current_depth + 1)

    elif isinstance(data, Sequence) and not isinstance(data, (str, bytes, bytearray)):
        for idx, item in enumerate(data):
            if not _is_scalar(item):
                item_name = item.get('name') or item.get('id') or f"Item {idx}" if isinstance(item, Mapping) else f"[{idx}]"
                node_path = _get_node_path(path, str(item_name))
                st.session_state.tree_expanded.add(node_path)
                _expand_all(item, node_path, max_depth, current_depth + 1)
