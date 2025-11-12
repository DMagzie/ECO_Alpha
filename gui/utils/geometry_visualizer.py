"""
3D Geometry Visualizer for EMJSON Models

Uses plotly to create interactive 3D visualizations of building geometry.
Integrates with the geometry_builder module for consistent data structures.
"""

import plotly.graph_objects as go
import numpy as np
from typing import Dict, List, Tuple, Any, Optional
import sys
from pathlib import Path

# Add eco_tools_parser to path
ECO_TOOLS = Path(__file__).resolve().parent.parent.parent / "eco_tools_parser"
if str(ECO_TOOLS) not in sys.path:
    sys.path.insert(0, str(ECO_TOOLS))

try:
    from eco_tools.geometry_builder import Point3D, Surface, Zone
except ImportError:
    # Fallback if geometry_builder not available
    Point3D = None
    Surface = None
    Zone = None


class GeometryVisualizer:
    """
    Create interactive 3D visualizations of building geometry
    """

    # Color schemes for different surface types
    SURFACE_COLORS = {
        'exterior_wall': 'rgba(200, 200, 200, 0.7)',  # Light gray
        'interior_wall': 'rgba(180, 180, 180, 0.6)',  # Lighter gray
        'roof': 'rgba(139, 69, 19, 0.7)',            # Brown
        'floor': 'rgba(210, 180, 140, 0.7)',          # Tan
        'ceiling': 'rgba(245, 245, 245, 0.6)',        # Off-white
        'window': 'rgba(173, 216, 230, 0.5)',         # Light blue (transparent)
        'door': 'rgba(139, 90, 43, 0.8)',             # Dark brown
        'underground_floor': 'rgba(101, 67, 33, 0.7)', # Dark tan
        'exterior_floor': 'rgba(192, 192, 192, 0.7)', # Silver
        'default': 'rgba(150, 150, 150, 0.6)'         # Medium gray
    }

    # Line colors for edges
    EDGE_COLORS = {
        'exterior_wall': 'rgb(100, 100, 100)',
        'interior_wall': 'rgb(120, 120, 120)',
        'roof': 'rgb(80, 40, 10)',
        'floor': 'rgb(140, 120, 90)',
        'window': 'rgb(100, 150, 200)',
        'door': 'rgb(100, 60, 30)',
        'default': 'rgb(80, 80, 80)'
    }

    def __init__(self):
        """Initialize visualizer"""
        self.traces = []

    def emjson_to_traces(self, emjson: Dict[str, Any], selected_surface: Optional[str] = None) -> List[go.Mesh3d]:
        """
        Convert EMJSON geometry to Plotly traces

        Args:
            emjson: EMJSON model dictionary
            selected_surface: ID of currently selected surface for highlighting

        Returns:
            List of Plotly traces (Mesh3d objects)
        """
        traces = []

        geometry = emjson.get('geometry', {})

        # Handle different EMJSON structures
        if 'zones' in geometry:
            # Process zones with nested surfaces
            for zone in geometry['zones']:
                zone_traces = self._process_zone(zone, selected_surface)
                traces.extend(zone_traces)

        # Handle surfaces organized by category
        surfaces = geometry.get('surfaces', {})
        if isinstance(surfaces, dict):
            for category, surf_list in surfaces.items():
                if isinstance(surf_list, list):
                    for surf in surf_list:
                        trace = self._surface_to_trace(surf, category, selected_surface=selected_surface)
                        if trace:
                            traces.append(trace)
        elif isinstance(surfaces, list):
            for surf in surfaces:
                surf_type = surf.get('type', 'default')
                trace = self._surface_to_trace(surf, surf_type, selected_surface=selected_surface)
                if trace:
                    traces.append(trace)

        # Handle openings
        openings = geometry.get('openings', {})
        if isinstance(openings, dict):
            for category, open_list in openings.items():
                if isinstance(open_list, list):
                    for opening in open_list:
                        trace = self._surface_to_trace(opening, category, selected_surface=selected_surface)
                        if trace:
                            traces.append(trace)
        elif isinstance(openings, list):
            for opening in openings:
                opening_type = opening.get('type', 'window')
                trace = self._surface_to_trace(opening, opening_type, selected_surface=selected_surface)
                if trace:
                    traces.append(trace)

        return traces

    def _process_zone(self, zone: Dict[str, Any], selected_surface: Optional[str] = None) -> List[go.Mesh3d]:
        """Process a single zone and its surfaces"""
        traces = []

        # Get zone surfaces
        surfaces = zone.get('surfaces', [])
        zone_name = zone.get('name', 'Unknown Zone')

        for surf in surfaces:
            trace = self._surface_to_trace(surf, surf.get('type', 'default'), zone_name, selected_surface)
            if trace:
                traces.append(trace)

        return traces

    def _surface_to_trace(self, surface: Dict[str, Any], surf_type: str,
                          zone_name: Optional[str] = None,
                          selected_surface: Optional[str] = None) -> Optional[go.Mesh3d]:
        """
        Convert a single surface to a Plotly Mesh3d trace

        Args:
            surface: Surface dictionary from EMJSON
            surf_type: Surface type (wall, roof, floor, etc.)
            zone_name: Optional zone name for hover text
            selected_surface: ID of currently selected surface for highlighting

        Returns:
            Plotly Mesh3d trace or None if invalid
        """
        # Get vertices
        vertices = surface.get('vertices_m', surface.get('vertices', []))
        if not vertices or len(vertices) < 3:
            return None

        # Extract coordinates
        try:
            x = [v[0] for v in vertices]
            y = [v[1] for v in vertices]
            z = [v[2] for v in vertices]
        except (IndexError, TypeError):
            return None

        # Triangulate polygon (simple fan triangulation from first vertex)
        # For n vertices: (0,1,2), (0,2,3), (0,3,4), ..., (0,n-2,n-1)
        n = len(vertices)
        i_indices = []
        j_indices = []
        k_indices = []

        for idx in range(1, n - 1):
            i_indices.append(0)
            j_indices.append(idx)
            k_indices.append(idx + 1)

        # Get surface info for hover text
        surf_name = surface.get('name', surface.get('id', 'Unknown'))
        area = surface.get('area_m2', surface.get('area'))
        area_str = f"{area:.1f} m²" if area is not None else "N/A"

        hover_text = f"<b>{surf_name}</b><br>"
        hover_text += f"Type: {surf_type}<br>"
        hover_text += f"Area: {area_str}"
        if zone_name:
            hover_text += f"<br>Zone: {zone_name}"
        hover_text += f"<br><br><i>Click to select</i>"

        # Get surface ID for selection tracking
        surf_id = surface.get('id', surface.get('name', 'unknown'))
        zone_id = surface.get('zone_id', zone_name if zone_name else 'unknown')

        # Check if this surface is selected
        is_selected = (selected_surface is not None and surf_id == selected_surface)

        # Get color - highlight if selected
        if is_selected:
            color = 'rgba(255, 165, 0, 0.9)'  # Orange highlight
            opacity = 0.9
            edge_color = 'rgb(255, 140, 0)'  # Darker orange edge
            edge_width = 4  # Thicker edge for selected
        else:
            color = self.SURFACE_COLORS.get(surf_type, self.SURFACE_COLORS['default'])
            opacity = 0.7
            edge_color = self.EDGE_COLORS.get(surf_type, self.EDGE_COLORS['default'])
            edge_width = 2

        # Create custom data for selection (one entry per vertex)
        n_vertices = len(x)
        customdata = [[zone_id, surf_id] for _ in range(n_vertices)]

        # Create mesh
        trace = go.Mesh3d(
            x=x,
            y=y,
            z=z,
            i=i_indices,
            j=j_indices,
            k=k_indices,
            color=color,
            opacity=opacity,
            hovertext=hover_text,
            hoverinfo='text',
            name=surf_type,
            showlegend=False,
            flatshading=True,
            customdata=customdata,  # Add custom data for selection
            # Add edges
            contour=dict(
                show=True,
                color=edge_color,
                width=edge_width
            )
        )

        return trace

    def create_figure(self, traces: List[go.Mesh3d], title: str = "Building Geometry") -> go.Figure:
        """
        Create a Plotly figure with all traces

        Args:
            traces: List of Mesh3d traces
            title: Figure title

        Returns:
            Plotly Figure object
        """
        fig = go.Figure(data=traces)

        # Calculate bounds for aspect ratio
        all_x, all_y, all_z = [], [], []
        for trace in traces:
            all_x.extend(trace.x)
            all_y.extend(trace.y)
            all_z.extend(trace.z)

        if all_x and all_y and all_z:
            x_range = max(all_x) - min(all_x)
            y_range = max(all_y) - min(all_y)
            z_range = max(all_z) - min(all_z)
            max_range = max(x_range, y_range, z_range)

            # Center points
            x_center = (max(all_x) + min(all_x)) / 2
            y_center = (max(all_y) + min(all_y)) / 2
            z_center = (max(all_z) + min(all_z)) / 2
        else:
            max_range = 10
            x_center = y_center = z_center = 0

        # Update layout for better 3D viewing
        fig.update_layout(
            title=title,
            scene=dict(
                xaxis=dict(
                    title='X (m)',
                    backgroundcolor="rgb(230, 230,230)",
                    gridcolor="white",
                    showbackground=True,
                    range=[x_center - max_range/2, x_center + max_range/2]
                ),
                yaxis=dict(
                    title='Y (m)',
                    backgroundcolor="rgb(230, 230,230)",
                    gridcolor="white",
                    showbackground=True,
                    range=[y_center - max_range/2, y_center + max_range/2]
                ),
                zaxis=dict(
                    title='Z (m)',
                    backgroundcolor="rgb(230, 230,230)",
                    gridcolor="white",
                    showbackground=True,
                    range=[z_center - max_range/2, z_center + max_range/2]
                ),
                aspectmode='cube',
                camera=dict(
                    eye=dict(x=1.5, y=1.5, z=1.2),
                    center=dict(x=0, y=0, z=0)
                )
            ),
            margin=dict(l=0, r=0, b=0, t=40),
            height=700
        )

        return fig

    def visualize_emjson(self, emjson: Dict[str, Any], title: str = "Building Geometry",
                        selected_surface: Optional[str] = None) -> go.Figure:
        """
        One-step method to visualize an EMJSON model

        Args:
            emjson: EMJSON model dictionary
            title: Figure title
            selected_surface: ID of currently selected surface for highlighting

        Returns:
            Plotly Figure ready to display
        """
        traces = self.emjson_to_traces(emjson, selected_surface)

        if not traces:
            # Create empty figure with message
            fig = go.Figure()
            fig.add_annotation(
                text="No geometry data available for visualization",
                xref="paper", yref="paper",
                x=0.5, y=0.5, showarrow=False,
                font=dict(size=16)
            )
            return fig

        return self.create_figure(traces, title)

    def get_geometry_stats(self, emjson: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract geometry statistics from EMJSON

        Args:
            emjson: EMJSON model dictionary

        Returns:
            Dictionary with statistics
        """
        geometry = emjson.get('geometry', {})

        stats = {
            'zones': 0,
            'surfaces': 0,
            'openings': 0,
            'total_floor_area_m2': 0.0,
            'total_volume_m3': 0.0,
            'surface_types': {}
        }

        # Count zones
        zones = geometry.get('zones', [])
        stats['zones'] = len(zones)

        # Calculate totals from zones
        for zone in zones:
            area = zone.get('floor_area_m2', zone.get('area', 0))
            volume = zone.get('volume_m3', zone.get('volume', 0))
            stats['total_floor_area_m2'] += area
            stats['total_volume_m3'] += volume

        # Count surfaces
        surfaces = geometry.get('surfaces', {})
        if isinstance(surfaces, dict):
            for category, surf_list in surfaces.items():
                if isinstance(surf_list, list):
                    count = len(surf_list)
                    stats['surfaces'] += count
                    stats['surface_types'][category] = count
        elif isinstance(surfaces, list):
            stats['surfaces'] = len(surfaces)

        # Count openings
        openings = geometry.get('openings', {})
        if isinstance(openings, dict):
            for category, open_list in openings.items():
                if isinstance(open_list, list):
                    stats['openings'] += len(open_list)
        elif isinstance(openings, list):
            stats['openings'] = len(openings)

        return stats


# Convenience function for easy import
def visualize_model(emjson: Dict[str, Any], title: str = "Building Geometry") -> go.Figure:
    """
    Quick function to visualize an EMJSON model

    Args:
        emjson: EMJSON model dictionary
        title: Figure title

    Returns:
        Plotly Figure ready to display in Streamlit
    """
    visualizer = GeometryVisualizer()
    return visualizer.visualize_emjson(emjson, title)
