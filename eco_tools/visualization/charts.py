"""
Energy Analysis Visualization Charts
====================================

Create interactive charts for CBECC-Com and EnergyPlus results comparison.

Features:
- End use comparison bar charts
- Compliance gauge charts
- Monthly energy profiles
- Interactive Plotly visualizations

Author: ECO Tools Team
Version: 7.0.0
Date: November 11, 2025
"""

from typing import Dict, List, Optional, Any
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots


# Color scheme
CBECC_COLOR = "#4A90E2"  # Blue
ENERGYPLUS_COLOR = "#50C878"  # Green
DELTA_POSITIVE_COLOR = "#E74C3C"  # Red (worse)
DELTA_NEGATIVE_COLOR = "#2ECC71"  # Green (better)


def create_end_use_comparison_chart(
    cbecc_end_uses: Dict[str, float],
    energyplus_end_uses: Dict[str, float],
    title: str = "Energy End Use Comparison"
) -> go.Figure:
    """
    Create side-by-side bar chart comparing CBECC and EnergyPlus end uses.

    Args:
        cbecc_end_uses: Dict with CBECC end uses (kBtu/ft²/yr)
        energyplus_end_uses: Dict with EnergyPlus end uses
        title: Chart title

    Returns:
        Plotly Figure object
    """
    # Get all unique end use categories
    categories = sorted(set(list(cbecc_end_uses.keys()) + list(energyplus_end_uses.keys())))

    # Prepare data
    cbecc_values = [cbecc_end_uses.get(cat, 0) for cat in categories]
    ep_values = [energyplus_end_uses.get(cat, 0) for cat in categories]

    # Format category names
    category_labels = [cat.replace("_", " ").title() for cat in categories]

    # Create figure
    fig = go.Figure()

    # Add CBECC bars
    fig.add_trace(go.Bar(
        name='CBECC-Com',
        x=category_labels,
        y=cbecc_values,
        marker_color=CBECC_COLOR,
        text=[f"{v:.2f}" for v in cbecc_values],
        textposition='outside',
        hovertemplate='<b>%{x}</b><br>CBECC: %{y:.2f} kBtu/ft²/yr<extra></extra>'
    ))

    # Add EnergyPlus bars
    fig.add_trace(go.Bar(
        name='EnergyPlus',
        x=category_labels,
        y=ep_values,
        marker_color=ENERGYPLUS_COLOR,
        text=[f"{v:.2f}" for v in ep_values],
        textposition='outside',
        hovertemplate='<b>%{x}</b><br>EnergyPlus: %{y:.2f} kBtu/ft²/yr<extra></extra>'
    ))

    # Update layout
    fig.update_layout(
        title=title,
        xaxis_title="End Use Category",
        yaxis_title="Energy Use Intensity (kBtu/ft²/yr)",
        barmode='group',
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        ),
        hovermode='x unified',
        height=500,
        template="plotly_white"
    )

    return fig


def create_delta_chart(
    cbecc_end_uses: Dict[str, float],
    energyplus_end_uses: Dict[str, float],
    title: str = "Energy End Use Delta (EnergyPlus - CBECC)"
) -> go.Figure:
    """
    Create bar chart showing difference between EnergyPlus and CBECC.

    Args:
        cbecc_end_uses: Dict with CBECC end uses
        energyplus_end_uses: Dict with EnergyPlus end uses
        title: Chart title

    Returns:
        Plotly Figure object
    """
    # Get all unique end use categories
    categories = sorted(set(list(cbecc_end_uses.keys()) + list(energyplus_end_uses.keys())))

    # Calculate deltas
    deltas = []
    colors = []
    for cat in categories:
        cbecc_val = cbecc_end_uses.get(cat, 0)
        ep_val = energyplus_end_uses.get(cat, 0)
        delta = ep_val - cbecc_val
        deltas.append(delta)

        # Color based on sign (positive = worse, negative = better)
        colors.append(DELTA_POSITIVE_COLOR if delta > 0 else DELTA_NEGATIVE_COLOR)

    # Format category names
    category_labels = [cat.replace("_", " ").title() for cat in categories]

    # Create figure
    fig = go.Figure()

    fig.add_trace(go.Bar(
        x=category_labels,
        y=deltas,
        marker_color=colors,
        text=[f"{d:+.2f}" for d in deltas],
        textposition='outside',
        hovertemplate='<b>%{x}</b><br>Delta: %{y:+.2f} kBtu/ft²/yr<extra></extra>'
    ))

    # Update layout
    fig.update_layout(
        title=title,
        xaxis_title="End Use Category",
        yaxis_title="Difference (kBtu/ft²/yr)",
        hovermode='x',
        height=400,
        template="plotly_white",
        shapes=[
            # Add zero line
            dict(
                type='line',
                x0=-0.5,
                y0=0,
                x1=len(categories) - 0.5,
                y1=0,
                line=dict(color='gray', dash='dash', width=1)
            )
        ]
    )

    return fig


def create_compliance_gauge(
    compliance_margin: float,
    proposed_tdv: Optional[float] = None,
    standard_tdv: Optional[float] = None,
    title: str = "Title 24 Compliance Margin"
) -> go.Figure:
    """
    Create gauge chart showing compliance margin.

    Args:
        compliance_margin: Percentage better than standard (positive = better)
        proposed_tdv: Proposed design TDV (kBtu/ft²/yr)
        standard_tdv: Standard design TDV (kBtu/ft²/yr)
        title: Chart title

    Returns:
        Plotly Figure object
    """
    fig = go.Figure(go.Indicator(
        mode="gauge+number+delta",
        value=compliance_margin,
        domain={'x': [0, 1], 'y': [0, 1]},
        title={'text': title, 'font': {'size': 24}},
        delta={'reference': 0, 'suffix': '%'},
        gauge={
            'axis': {'range': [-20, 30], 'ticksuffix': '%'},
            'bar': {'color': "darkblue"},
            'steps': [
                {'range': [-20, 0], 'color': "#FFCCCC"},  # Red zone (failing)
                {'range': [0, 10], 'color': "#FFFFCC"},   # Yellow zone (marginal)
                {'range': [10, 30], 'color': "#CCFFCC"}   # Green zone (good)
            ],
            'threshold': {
                'line': {'color': "red", 'width': 4},
                'thickness': 0.75,
                'value': 0
            }
        }
    ))

    # Add TDV values as annotation if available
    if proposed_tdv is not None and standard_tdv is not None:
        fig.add_annotation(
            text=f"Proposed TDV: {proposed_tdv:.1f} kBtu/ft²/yr<br>"
                 f"Standard TDV: {standard_tdv:.1f} kBtu/ft²/yr",
            xref="paper",
            yref="paper",
            x=0.5,
            y=-0.15,
            showarrow=False,
            font=dict(size=12)
        )

    fig.update_layout(
        height=350,
        margin=dict(l=20, r=20, t=60, b=80)
    )

    return fig


def create_total_energy_pie(
    end_uses: Dict[str, float],
    title: str = "Energy End Use Breakdown"
) -> go.Figure:
    """
    Create pie chart showing energy end use breakdown.

    Args:
        end_uses: Dict with end use categories and values
        title: Chart title

    Returns:
        Plotly Figure object
    """
    # Filter out zero values
    filtered_uses = {k: v for k, v in end_uses.items() if v > 0}

    if not filtered_uses:
        # Return empty figure if no data
        fig = go.Figure()
        fig.add_annotation(
            text="No end use data available",
            xref="paper",
            yref="paper",
            x=0.5,
            y=0.5,
            showarrow=False,
            font=dict(size=16)
        )
        return fig

    # Prepare data
    labels = [k.replace("_", " ").title() for k in filtered_uses.keys()]
    values = list(filtered_uses.values())

    # Create figure
    fig = go.Figure(data=[go.Pie(
        labels=labels,
        values=values,
        hole=0.3,
        hovertemplate='<b>%{label}</b><br>%{value:.2f} kBtu/ft²/yr<br>%{percent}<extra></extra>'
    )])

    fig.update_layout(
        title=title,
        height=400,
        showlegend=True,
        legend=dict(
            orientation="v",
            yanchor="middle",
            y=0.5,
            xanchor="left",
            x=1.02
        )
    )

    return fig


def create_monthly_profile(
    monthly_data: Dict[str, List[float]],
    title: str = "Monthly Energy Profile"
) -> go.Figure:
    """
    Create line chart showing monthly energy consumption.

    Args:
        monthly_data: Dict with series names and 12-month values
                     e.g., {"Heating": [10, 9, 8, ...], "Cooling": [1, 2, 3, ...]}
        title: Chart title

    Returns:
        Plotly Figure object
    """
    months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
              'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

    fig = go.Figure()

    for series_name, values in monthly_data.items():
        if len(values) != 12:
            continue  # Skip invalid data

        fig.add_trace(go.Scatter(
            x=months,
            y=values,
            mode='lines+markers',
            name=series_name,
            hovertemplate='<b>%{x}</b><br>%{y:.2f} kBtu/ft²<extra></extra>'
        ))

    fig.update_layout(
        title=title,
        xaxis_title="Month",
        yaxis_title="Energy (kBtu/ft²)",
        hovermode='x unified',
        height=400,
        template="plotly_white",
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        )
    )

    return fig


def create_comparison_scatter(
    cbecc_values: List[float],
    energyplus_values: List[float],
    labels: List[str],
    title: str = "CBECC vs EnergyPlus Comparison"
) -> go.Figure:
    """
    Create scatter plot comparing CBECC and EnergyPlus values.

    Args:
        cbecc_values: List of CBECC values
        energyplus_values: List of corresponding EnergyPlus values
        labels: List of labels for each point
        title: Chart title

    Returns:
        Plotly Figure object
    """
    fig = go.Figure()

    # Add scatter points
    fig.add_trace(go.Scatter(
        x=cbecc_values,
        y=energyplus_values,
        mode='markers',
        text=labels,
        marker=dict(size=10, color=CBECC_COLOR),
        hovertemplate='<b>%{text}</b><br>CBECC: %{x:.2f}<br>EnergyPlus: %{y:.2f}<extra></extra>'
    ))

    # Add ideal agreement line (45-degree)
    max_val = max(max(cbecc_values or [0]), max(energyplus_values or [0]))
    fig.add_trace(go.Scatter(
        x=[0, max_val],
        y=[0, max_val],
        mode='lines',
        name='Perfect Agreement',
        line=dict(color='gray', dash='dash'),
        hoverinfo='skip'
    ))

    fig.update_layout(
        title=title,
        xaxis_title="CBECC-Com (kBtu/ft²/yr)",
        yaxis_title="EnergyPlus (kBtu/ft²/yr)",
        height=500,
        template="plotly_white",
        showlegend=True
    )

    # Make axes equal scale
    fig.update_xaxes(scaleanchor="y", scaleratio=1)

    return fig


def export_chart_to_png(fig: go.Figure, filename: str) -> None:
    """
    Export Plotly figure to PNG file.

    Args:
        fig: Plotly Figure object
        filename: Output filename (with .png extension)
    """
    try:
        fig.write_image(filename)
        print(f"✅ Chart exported to: {filename}")
    except Exception as e:
        print(f"❌ Export failed: {e}")
        print("   Note: PNG export requires kaleido: pip install kaleido")


def export_chart_to_html(fig: go.Figure, filename: str) -> None:
    """
    Export Plotly figure to interactive HTML file.

    Args:
        fig: Plotly Figure object
        filename: Output filename (with .html extension)
    """
    fig.write_html(filename)
    print(f"✅ Chart exported to: {filename}")


if __name__ == "__main__":
    # Test charts with sample data
    print("🧪 Testing chart generation...")

    # Sample data
    cbecc_data = {
        "space_heating": 12.5,
        "space_cooling": 18.3,
        "indoor_lighting": 8.2,
        "equipment": 5.1,
        "dhw": 4.2
    }

    ep_data = {
        "heating": 13.2,
        "cooling": 17.5,
        "lighting": 9.1,
        "equipment": 5.0,
        "dhw": 4.0
    }

    # Test end use comparison
    print("\n1. Creating end use comparison chart...")
    fig1 = create_end_use_comparison_chart(cbecc_data, ep_data)
    print("   ✅ End use comparison chart created")

    # Test delta chart
    print("\n2. Creating delta chart...")
    fig2 = create_delta_chart(cbecc_data, ep_data)
    print("   ✅ Delta chart created")

    # Test compliance gauge
    print("\n3. Creating compliance gauge...")
    fig3 = create_compliance_gauge(11.8, 42.5, 48.2)
    print("   ✅ Compliance gauge created")

    # Test pie chart
    print("\n4. Creating pie chart...")
    fig4 = create_total_energy_pie(cbecc_data, "CBECC End Use Breakdown")
    print("   ✅ Pie chart created")

    print("\n✅ All charts generated successfully!")
    print("\nTo view charts, import this module in Streamlit:")
    print("   st.plotly_chart(fig)")
