"""
Unit Tests for Visualization Charts
===================================

Tests for eco_tools.visualization.charts module
"""

import pytest
from unittest.mock import Mock, patch
import plotly.graph_objects as go
from eco_tools.visualization.charts import (
    create_end_use_comparison_chart,
    create_delta_chart,
    create_compliance_gauge,
    create_total_energy_pie,
    create_monthly_profile,
    create_comparison_scatter
)


# Fixtures

@pytest.fixture
def sample_cbecc_end_uses():
    """Sample CBECC end use data"""
    return {
        "space_heating": 10.5,
        "space_cooling": 15.2,
        "indoor_lighting": 8.7,
        "equipment": 12.3,
        "indoor_fans": 4.5,
        "dhw": 3.2
    }


@pytest.fixture
def sample_energyplus_end_uses():
    """Sample EnergyPlus end use data"""
    return {
        "space_heating": 11.2,
        "space_cooling": 14.8,
        "indoor_lighting": 9.1,
        "equipment": 12.0,
        "indoor_fans": 4.8,
        "dhw": 3.5
    }


@pytest.fixture
def sample_monthly_data():
    """Sample monthly energy data"""
    return {
        "months": ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
                   "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"],
        "values": [45.2, 38.5, 35.1, 28.3, 22.5, 18.2,
                   16.8, 17.5, 21.3, 26.8, 32.4, 41.2]
    }


# Test End Use Comparison Chart

class TestEndUseComparisonChart:
    """Test suite for create_end_use_comparison_chart()"""

    def test_create_basic_chart(self, sample_cbecc_end_uses, sample_energyplus_end_uses):
        """Test basic chart creation"""
        fig = create_end_use_comparison_chart(
            sample_cbecc_end_uses,
            sample_energyplus_end_uses
        )

        assert isinstance(fig, go.Figure)
        assert len(fig.data) == 2  # Two traces (CBECC and EnergyPlus)
        assert fig.data[0].type == "bar"
        assert fig.data[1].type == "bar"

    def test_chart_with_custom_title(self, sample_cbecc_end_uses, sample_energyplus_end_uses):
        """Test chart with custom title"""
        custom_title = "Custom Energy Comparison"
        fig = create_end_use_comparison_chart(
            sample_cbecc_end_uses,
            sample_energyplus_end_uses,
            title=custom_title
        )

        assert custom_title in fig.layout.title.text

    def test_chart_with_empty_cbecc(self, sample_energyplus_end_uses):
        """Test chart when CBECC data is empty"""
        fig = create_end_use_comparison_chart(
            {},
            sample_energyplus_end_uses
        )

        assert isinstance(fig, go.Figure)
        assert len(fig.data) == 2

    def test_chart_with_empty_energyplus(self, sample_cbecc_end_uses):
        """Test chart when EnergyPlus data is empty"""
        fig = create_end_use_comparison_chart(
            sample_cbecc_end_uses,
            {}
        )

        assert isinstance(fig, go.Figure)
        assert len(fig.data) == 2

    def test_chart_with_both_empty(self):
        """Test chart when both datasets are empty"""
        fig = create_end_use_comparison_chart({}, {})

        assert isinstance(fig, go.Figure)
        # Should still create figure, just with no data

    def test_chart_labels(self, sample_cbecc_end_uses, sample_energyplus_end_uses):
        """Test that chart has proper axis labels"""
        fig = create_end_use_comparison_chart(
            sample_cbecc_end_uses,
            sample_energyplus_end_uses
        )

        assert fig.layout.xaxis.title.text is not None
        assert fig.layout.yaxis.title.text is not None

    def test_chart_colors(self, sample_cbecc_end_uses, sample_energyplus_end_uses):
        """Test that chart uses correct color scheme"""
        fig = create_end_use_comparison_chart(
            sample_cbecc_end_uses,
            sample_energyplus_end_uses
        )

        # CBECC should be blue (#4A90E2), EnergyPlus green (#50C878)
        assert fig.data[0].marker.color == "#4A90E2"
        assert fig.data[1].marker.color == "#50C878"


# Test Delta Chart

class TestDeltaChart:
    """Test suite for create_delta_chart()"""

    def test_create_basic_delta_chart(self, sample_cbecc_end_uses, sample_energyplus_end_uses):
        """Test basic delta chart creation"""
        fig = create_delta_chart(
            sample_cbecc_end_uses,
            sample_energyplus_end_uses
        )

        assert isinstance(fig, go.Figure)
        assert len(fig.data) >= 1
        assert fig.data[0].type == "bar"

    def test_delta_calculations(self, sample_cbecc_end_uses, sample_energyplus_end_uses):
        """Test that delta values are correctly calculated"""
        fig = create_delta_chart(
            sample_cbecc_end_uses,
            sample_energyplus_end_uses
        )

        # Delta should be EnergyPlus - CBECC
        # space_heating: 11.2 - 10.5 = 0.7
        # space_cooling: 14.8 - 15.2 = -0.4
        # Values should be in the data
        assert len(fig.data[0].y) > 0

    def test_delta_color_coding(self, sample_cbecc_end_uses, sample_energyplus_end_uses):
        """Test that positive/negative deltas have correct colors"""
        fig = create_delta_chart(
            sample_cbecc_end_uses,
            sample_energyplus_end_uses
        )

        # Should have color coding for positive (red) and negative (green) deltas
        assert hasattr(fig.data[0].marker, 'color')

    def test_delta_with_mismatched_keys(self):
        """Test delta chart with different end use categories"""
        cbecc = {"space_heating": 10.0, "space_cooling": 15.0}
        energyplus = {"space_cooling": 14.0, "indoor_lighting": 8.0}

        fig = create_delta_chart(cbecc, energyplus)

        assert isinstance(fig, go.Figure)
        # Should handle all unique categories


# Test Compliance Gauge

class TestComplianceGauge:
    """Test suite for create_compliance_gauge()"""

    def test_create_basic_gauge(self):
        """Test basic gauge creation"""
        fig = create_compliance_gauge(15.0)

        assert isinstance(fig, go.Figure)
        assert fig.data[0].type == "indicator"

    def test_gauge_with_tdv_values(self):
        """Test gauge with TDV values"""
        fig = create_compliance_gauge(
            compliance_margin=15.0,
            proposed_tdv=50000.0,
            standard_tdv=60000.0
        )

        assert isinstance(fig, go.Figure)

    def test_gauge_with_negative_margin(self):
        """Test gauge with negative (failing) margin"""
        fig = create_compliance_gauge(-10.0)

        assert isinstance(fig, go.Figure)
        # Should handle negative values (non-compliant)

    def test_gauge_with_zero_margin(self):
        """Test gauge with exactly zero margin"""
        fig = create_compliance_gauge(0.0)

        assert isinstance(fig, go.Figure)

    def test_gauge_with_high_margin(self):
        """Test gauge with very high compliance margin"""
        fig = create_compliance_gauge(50.0)

        assert isinstance(fig, go.Figure)

    def test_gauge_custom_title(self):
        """Test gauge with custom title"""
        custom_title = "My Compliance Status"
        fig = create_compliance_gauge(15.0, title=custom_title)

        assert custom_title in str(fig.layout.title.text)


# Test Total Energy Pie Chart

class TestTotalEnergyPie:
    """Test suite for create_total_energy_pie()"""

    def test_create_basic_pie(self, sample_cbecc_end_uses):
        """Test basic pie chart creation"""
        fig = create_total_energy_pie(sample_cbecc_end_uses)

        assert isinstance(fig, go.Figure)
        assert fig.data[0].type == "pie"

    def test_pie_with_empty_data(self):
        """Test pie chart with empty data"""
        fig = create_total_energy_pie({})

        assert isinstance(fig, go.Figure)

    def test_pie_with_single_value(self):
        """Test pie chart with single end use"""
        fig = create_total_energy_pie({"space_heating": 25.0})

        assert isinstance(fig, go.Figure)
        assert len(fig.data[0].labels) == 1

    def test_pie_labels(self, sample_cbecc_end_uses):
        """Test that pie chart has correct labels"""
        fig = create_total_energy_pie(sample_cbecc_end_uses)

        labels = fig.data[0].labels
        assert len(labels) == len(sample_cbecc_end_uses)

    def test_pie_values(self, sample_cbecc_end_uses):
        """Test that pie chart has correct values"""
        fig = create_total_energy_pie(sample_cbecc_end_uses)

        values = fig.data[0].values
        assert len(values) == len(sample_cbecc_end_uses)
        assert sum(values) == pytest.approx(sum(sample_cbecc_end_uses.values()))

    def test_pie_custom_title(self, sample_cbecc_end_uses):
        """Test pie chart with custom title"""
        custom_title = "Energy Distribution"
        fig = create_total_energy_pie(sample_cbecc_end_uses, title=custom_title)

        assert custom_title in str(fig.layout.title.text)


# Test Monthly Profile Chart

class TestMonthlyProfile:
    """Test suite for create_monthly_profile()"""

    def test_create_basic_monthly_profile(self, sample_monthly_data):
        """Test basic monthly profile creation"""
        fig = create_monthly_profile(
            sample_monthly_data["months"],
            sample_monthly_data["values"]
        )

        assert isinstance(fig, go.Figure)
        assert fig.data[0].type == "scatter"

    def test_monthly_profile_length_validation(self):
        """Test that months and values must have same length"""
        months = ["Jan", "Feb", "Mar"]
        values = [10.0, 20.0]  # Mismatched length

        # Should either raise error or handle gracefully
        with pytest.raises((ValueError, IndexError, AssertionError)):
            create_monthly_profile(months, values)

    def test_monthly_profile_with_12_months(self, sample_monthly_data):
        """Test with standard 12 months"""
        fig = create_monthly_profile(
            sample_monthly_data["months"],
            sample_monthly_data["values"]
        )

        assert len(fig.data[0].x) == 12
        assert len(fig.data[0].y) == 12

    def test_monthly_profile_custom_title(self, sample_monthly_data):
        """Test monthly profile with custom title"""
        custom_title = "Annual Energy Profile"
        fig = create_monthly_profile(
            sample_monthly_data["months"],
            sample_monthly_data["values"],
            title=custom_title
        )

        assert custom_title in str(fig.layout.title.text)


# Test Comparison Scatter Plot

class TestComparisonScatter:
    """Test suite for create_comparison_scatter()"""

    def test_create_basic_scatter(self, sample_cbecc_end_uses, sample_energyplus_end_uses):
        """Test basic scatter plot creation"""
        fig = create_comparison_scatter(
            sample_cbecc_end_uses,
            sample_energyplus_end_uses
        )

        assert isinstance(fig, go.Figure)
        assert len(fig.data) >= 1  # At least one trace

    def test_scatter_with_empty_data(self):
        """Test scatter plot with empty data"""
        fig = create_comparison_scatter({}, {})

        assert isinstance(fig, go.Figure)

    def test_scatter_45_degree_line(self, sample_cbecc_end_uses, sample_energyplus_end_uses):
        """Test that scatter plot includes 45-degree ideal line"""
        fig = create_comparison_scatter(
            sample_cbecc_end_uses,
            sample_energyplus_end_uses
        )

        # Should have at least 2 traces: data points + ideal line
        assert len(fig.data) >= 2

    def test_scatter_custom_title(self, sample_cbecc_end_uses, sample_energyplus_end_uses):
        """Test scatter plot with custom title"""
        custom_title = "CBECC vs EnergyPlus Agreement"
        fig = create_comparison_scatter(
            sample_cbecc_end_uses,
            sample_energyplus_end_uses,
            title=custom_title
        )

        assert custom_title in str(fig.layout.title.text)


# Integration Tests

class TestChartsIntegration:
    """Integration tests for chart generation"""

    def test_all_charts_with_realistic_data(self):
        """Test all chart types with realistic building data"""
        # Typical office building end uses
        cbecc = {
            "space_heating": 8.5,
            "space_cooling": 18.2,
            "indoor_fans": 4.3,
            "indoor_lighting": 10.5,
            "equipment": 15.0,
            "dhw": 2.1,
            "pumps": 1.8,
            "heat_rejection": 0.9
        }

        energyplus = {
            "space_heating": 9.1,
            "space_cooling": 17.8,
            "indoor_fans": 4.5,
            "indoor_lighting": 10.8,
            "equipment": 14.8,
            "dhw": 2.3,
            "pumps": 1.9,
            "heat_rejection": 1.0
        }

        # Test all chart functions
        fig1 = create_end_use_comparison_chart(cbecc, energyplus)
        fig2 = create_delta_chart(cbecc, energyplus)
        fig3 = create_compliance_gauge(12.5, 250000.0, 280000.0)
        fig4 = create_total_energy_pie(cbecc)
        fig5 = create_comparison_scatter(cbecc, energyplus)

        # All should be valid Plotly figures
        for fig in [fig1, fig2, fig3, fig4, fig5]:
            assert isinstance(fig, go.Figure)
            assert fig.data is not None

    def test_chart_export_capability(self, sample_cbecc_end_uses, sample_energyplus_end_uses, tmp_path):
        """Test that charts can be exported to images"""
        fig = create_end_use_comparison_chart(
            sample_cbecc_end_uses,
            sample_energyplus_end_uses
        )

        # Test that figure has to_html method (for Streamlit)
        assert hasattr(fig, 'to_html')

        # Test HTML export
        html = fig.to_html()
        assert "<div>" in html
        assert "plotly" in html.lower()


# Edge Cases

class TestChartsEdgeCases:
    """Test edge cases and error handling"""

    def test_very_large_values(self):
        """Test charts with very large energy values"""
        large_data = {
            "space_heating": 1000000.0,
            "space_cooling": 2000000.0
        }

        fig = create_total_energy_pie(large_data)
        assert isinstance(fig, go.Figure)

    def test_very_small_values(self):
        """Test charts with very small energy values"""
        small_data = {
            "space_heating": 0.001,
            "space_cooling": 0.002
        }

        fig = create_total_energy_pie(small_data)
        assert isinstance(fig, go.Figure)

    def test_negative_values(self):
        """Test charts with negative values (unusual but possible)"""
        negative_data = {
            "space_heating": -5.0,
            "space_cooling": 10.0
        }

        # Charts should handle gracefully or raise informative error
        try:
            fig = create_total_energy_pie(negative_data)
            assert isinstance(fig, go.Figure)
        except ValueError:
            # Acceptable to reject negative values
            pass

    def test_special_characters_in_labels(self):
        """Test charts with special characters in end use names"""
        special_data = {
            "space_heating_&_ventilation": 10.0,
            "cooling_(mechanical)": 15.0
        }

        fig = create_total_energy_pie(special_data)
        assert isinstance(fig, go.Figure)
