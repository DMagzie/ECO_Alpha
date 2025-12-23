"""
Tests for Phase 5: Advanced Analytics (Benchmarks & Zone Sensitivity)

Tests the benchmarks module and zone-level sensitivity analysis.
"""

import pytest
from typing import List, Dict

from eco_tools.lcca.benchmarks import (
    PerformanceRating,
    BuildingVintage,
    ZoneBenchmark,
    BenchmarkComparison,
    BenchmarkLibrary,
    get_benchmark_library,
    compare_zone_to_benchmark,
    compare_zones_to_benchmarks,
    identify_high_impact_zones as identify_benchmark_outliers,
    calculate_portfolio_rating,
    format_benchmark_comparison,
    format_benchmark_summary_table,
    format_rating_distribution,
    DWELLING_UNIT_BENCHMARKS,
    COMMON_AREA_BENCHMARKS,
)
from eco_tools.lcca.sensitivity import (
    SensitivityParameter,
    ZoneSensitivityResult,
    ZoneImpactResult,
    zone_sensitivity_analysis,
    identify_high_impact_zones,
    format_zone_impact_table,
    zone_tornado_analysis,
)
from eco_tools.lcca.zone_energy import ZoneEnergySummary
from eco_tools.lcca.cuac.models import ZoneType
from eco_tools.lcca.res_other.models import CommonAreaCategory


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def sample_zones() -> List[ZoneEnergySummary]:
    """Create sample zones for benchmarking tests."""
    return [
        ZoneEnergySummary(
            zone_name="Unit-1BR-A",
            zone_type=ZoneType.DWELLING_UNIT,
            elec_kwh=4500,  # ~18 kWh/sqft/yr for 750 sqft = ~61 kBtu/sqft
            gas_therm=200,  # ~27 kBtu/sqft
            area_sqft=750,
            num_bedrooms=1,
            multiplier=1,
        ),
        ZoneEnergySummary(
            zone_name="Unit-2BR-A",
            zone_type=ZoneType.DWELLING_UNIT,
            elec_kwh=3500,  # Lower per sqft
            gas_therm=150,
            area_sqft=1050,
            num_bedrooms=2,
            multiplier=1,
        ),
        ZoneEnergySummary(
            zone_name="Lobby-L01",
            zone_type=ZoneType.COMMON_AREA,
            category=CommonAreaCategory.LOBBY,
            elec_kwh=8000,
            gas_therm=0,
            area_sqft=2000,
            multiplier=1,
        ),
        ZoneEnergySummary(
            zone_name="Corridor-L01",
            zone_type=ZoneType.COMMON_AREA,
            category=CommonAreaCategory.CORRIDOR,
            elec_kwh=2000,
            gas_therm=0,
            area_sqft=1500,
            multiplier=1,
        ),
    ]


@pytest.fixture
def zone_results_dict() -> Dict[str, Dict]:
    """Create zone results as dictionary for sensitivity tests."""
    return {
        "Unit-1BR": {
            "annual_elec_kwh": 4500,
            "annual_gas_therm": 200,
            "area_sqft": 750,
            "annual_cost": 1425,
            "zone_type": "dwelling_unit",
        },
        "Unit-2BR": {
            "annual_elec_kwh": 6000,
            "annual_gas_therm": 280,
            "area_sqft": 1050,
            "annual_cost": 1920,
            "zone_type": "dwelling_unit",
        },
        "Corridor": {
            "annual_elec_kwh": 8000,
            "annual_gas_therm": 0,
            "area_sqft": 1500,
            "annual_cost": 2000,
            "zone_type": "common_area",
        },
    }


# =============================================================================
# PERFORMANCE RATING TESTS
# =============================================================================

class TestPerformanceRating:
    """Tests for PerformanceRating enum."""

    def test_from_percentile_excellent(self):
        """Test excellent rating for low percentiles."""
        assert PerformanceRating.from_percentile(5) == PerformanceRating.EXCELLENT
        assert PerformanceRating.from_percentile(10) == PerformanceRating.EXCELLENT

    def test_from_percentile_good(self):
        """Test good rating."""
        assert PerformanceRating.from_percentile(15) == PerformanceRating.GOOD
        assert PerformanceRating.from_percentile(25) == PerformanceRating.GOOD

    def test_from_percentile_average(self):
        """Test average rating."""
        assert PerformanceRating.from_percentile(50) == PerformanceRating.AVERAGE
        assert PerformanceRating.from_percentile(75) == PerformanceRating.AVERAGE

    def test_from_percentile_below_average(self):
        """Test below average rating."""
        assert PerformanceRating.from_percentile(80) == PerformanceRating.BELOW_AVERAGE
        assert PerformanceRating.from_percentile(90) == PerformanceRating.BELOW_AVERAGE

    def test_from_percentile_poor(self):
        """Test poor rating for high percentiles."""
        assert PerformanceRating.from_percentile(95) == PerformanceRating.POOR
        assert PerformanceRating.from_percentile(100) == PerformanceRating.POOR


# =============================================================================
# ZONE BENCHMARK TESTS
# =============================================================================

class TestZoneBenchmark:
    """Tests for ZoneBenchmark class."""

    def test_create_benchmark(self):
        """Test creating a benchmark."""
        benchmark = ZoneBenchmark(
            zone_type=ZoneType.DWELLING_UNIT,
            climate_zone="CZ12",
            eui_p10=22,
            eui_p25=29,
            eui_median=38,
            eui_p75=50,
            eui_p90=65,
        )
        assert benchmark.eui_median == 38
        assert benchmark.eui_low == 22  # p10
        assert benchmark.eui_high == 65  # p90

    def test_get_eui_percentile_excellent(self):
        """Test percentile calculation for excellent EUI."""
        benchmark = ZoneBenchmark(
            zone_type=ZoneType.DWELLING_UNIT,
            eui_p10=22,
            eui_p25=29,
            eui_median=38,
            eui_p75=50,
            eui_p90=65,
        )
        # Very low EUI should be excellent
        percentile = benchmark.get_eui_percentile(18)
        assert percentile < 10

    def test_get_eui_percentile_median(self):
        """Test percentile calculation at median."""
        benchmark = ZoneBenchmark(
            zone_type=ZoneType.DWELLING_UNIT,
            eui_p10=22,
            eui_p25=29,
            eui_median=38,
            eui_p75=50,
            eui_p90=65,
        )
        percentile = benchmark.get_eui_percentile(38)
        assert 45 < percentile < 55  # Around 50th

    def test_get_eui_percentile_poor(self):
        """Test percentile calculation for poor EUI."""
        benchmark = ZoneBenchmark(
            zone_type=ZoneType.DWELLING_UNIT,
            eui_p10=22,
            eui_p25=29,
            eui_median=38,
            eui_p75=50,
            eui_p90=65,
        )
        # Very high EUI should be poor
        percentile = benchmark.get_eui_percentile(80)
        assert percentile > 90

    def test_get_eui_rating(self):
        """Test EUI rating based on value."""
        benchmark = ZoneBenchmark(
            zone_type=ZoneType.DWELLING_UNIT,
            eui_p10=22,
            eui_p25=29,
            eui_median=38,
            eui_p75=50,
            eui_p90=65,
        )
        assert benchmark.get_eui_rating(18) == PerformanceRating.EXCELLENT
        assert benchmark.get_eui_rating(38) == PerformanceRating.AVERAGE
        assert benchmark.get_eui_rating(80) == PerformanceRating.POOR


# =============================================================================
# BENCHMARK LIBRARY TESTS
# =============================================================================

class TestBenchmarkLibrary:
    """Tests for BenchmarkLibrary class."""

    def test_create_library(self):
        """Test creating benchmark library."""
        library = BenchmarkLibrary()
        assert len(library.list_climate_zones()) == 16

    def test_get_benchmark_library_singleton(self):
        """Test global library singleton."""
        lib1 = get_benchmark_library()
        lib2 = get_benchmark_library()
        assert lib1 is lib2

    def test_get_dwelling_benchmark(self):
        """Test getting dwelling unit benchmark."""
        library = get_benchmark_library()
        benchmark = library.get_dwelling_benchmark("CZ12")
        assert benchmark is not None
        assert benchmark.zone_type == ZoneType.DWELLING_UNIT
        assert benchmark.climate_zone == "CZ12"
        assert benchmark.eui_median > 0

    def test_get_dwelling_benchmark_all_climate_zones(self):
        """Test benchmarks exist for all climate zones."""
        library = get_benchmark_library()
        for cz in library.list_climate_zones():
            benchmark = library.get_dwelling_benchmark(cz)
            assert benchmark is not None, f"No benchmark for {cz}"

    def test_get_common_area_benchmark(self):
        """Test getting common area benchmark."""
        library = get_benchmark_library()
        benchmark = library.get_common_area_benchmark(
            CommonAreaCategory.LOBBY,
            "CZ12"
        )
        assert benchmark is not None
        assert benchmark.zone_type == ZoneType.COMMON_AREA
        assert benchmark.category == CommonAreaCategory.LOBBY

    def test_list_common_area_categories(self):
        """Test listing available common area categories."""
        library = get_benchmark_library()
        categories = library.list_common_area_categories()
        assert len(categories) > 0
        assert CommonAreaCategory.LOBBY in categories
        assert CommonAreaCategory.CORRIDOR in categories

    def test_hot_climate_adjustment(self):
        """Test that hot climates have higher EUI benchmarks."""
        library = get_benchmark_library()
        mild = library.get_dwelling_benchmark("CZ03")  # Oakland - mild
        hot = library.get_dwelling_benchmark("CZ15")  # Palm Springs - hot
        assert hot.eui_median > mild.eui_median


# =============================================================================
# BENCHMARK COMPARISON TESTS
# =============================================================================

class TestBenchmarkComparison:
    """Tests for compare_zone_to_benchmark function."""

    def test_compare_zone_to_benchmark(self, sample_zones):
        """Test comparing a zone to its benchmark."""
        dwelling = sample_zones[0]  # Unit-1BR-A
        comparison = compare_zone_to_benchmark(dwelling, "CZ12")

        assert comparison.zone_name == "Unit-1BR-A"
        assert comparison.zone_type == ZoneType.DWELLING_UNIT
        assert comparison.actual_eui > 0
        assert comparison.benchmark_eui_median > 0

    def test_compare_common_area(self, sample_zones):
        """Test comparing common area to benchmark."""
        lobby = sample_zones[2]  # Lobby-L01
        comparison = compare_zone_to_benchmark(lobby, "CZ12")

        assert comparison.zone_name == "Lobby-L01"
        assert comparison.category == CommonAreaCategory.LOBBY

    def test_compare_zones_to_benchmarks(self, sample_zones):
        """Test comparing multiple zones."""
        comparisons = compare_zones_to_benchmarks(sample_zones, "CZ12")
        assert len(comparisons) == len(sample_zones)

    def test_is_above_average(self, sample_zones):
        """Test above average detection."""
        # Create a very efficient zone
        efficient = ZoneEnergySummary(
            zone_name="Efficient-Unit",
            zone_type=ZoneType.DWELLING_UNIT,
            elec_kwh=1500,
            gas_therm=50,
            area_sqft=1000,
            multiplier=1,
        )
        comparison = compare_zone_to_benchmark(efficient, "CZ12")
        assert comparison.eui_percentile < 50

    def test_needs_attention(self, sample_zones):
        """Test needs attention detection."""
        # Create an inefficient zone
        inefficient = ZoneEnergySummary(
            zone_name="Inefficient-Unit",
            zone_type=ZoneType.DWELLING_UNIT,
            elec_kwh=12000,
            gas_therm=500,
            area_sqft=800,
            multiplier=1,
        )
        comparison = compare_zone_to_benchmark(inefficient, "CZ12")
        assert comparison.needs_attention


# =============================================================================
# PORTFOLIO RATING TESTS
# =============================================================================

class TestPortfolioRating:
    """Tests for portfolio-level rating functions."""

    def test_calculate_portfolio_rating(self, sample_zones):
        """Test portfolio rating calculation."""
        comparisons = compare_zones_to_benchmarks(sample_zones, "CZ12")
        portfolio = calculate_portfolio_rating(comparisons)

        assert portfolio['zone_count'] == 4
        assert 'average_eui_percentile' in portfolio
        assert 'overall_rating' in portfolio
        assert 'rating_counts' in portfolio

    def test_identify_benchmark_outliers(self, sample_zones):
        """Test identifying benchmark outliers."""
        comparisons = compare_zones_to_benchmarks(sample_zones, "CZ12")
        outliers = identify_benchmark_outliers(comparisons, threshold_percentile=75.0)

        # Outliers are zones above 75th percentile (worse than 75%)
        for outlier in outliers:
            assert outlier.eui_percentile > 75

    def test_empty_portfolio(self):
        """Test empty portfolio rating."""
        portfolio = calculate_portfolio_rating([])
        assert portfolio['zone_count'] == 0
        assert portfolio['average_percentile'] == 50.0


# =============================================================================
# FORMATTING TESTS
# =============================================================================

class TestBenchmarkFormatting:
    """Tests for benchmark formatting functions."""

    def test_format_benchmark_comparison(self, sample_zones):
        """Test formatting single comparison."""
        comparison = compare_zone_to_benchmark(sample_zones[0], "CZ12")
        formatted = format_benchmark_comparison(comparison)

        assert "Unit-1BR-A" in formatted
        assert "EUI" in formatted
        assert "Rating" in formatted

    def test_format_benchmark_summary_table(self, sample_zones):
        """Test formatting summary table."""
        comparisons = compare_zones_to_benchmarks(sample_zones, "CZ12")
        table = format_benchmark_summary_table(comparisons)

        assert "ZONE BENCHMARK COMPARISON" in table
        assert "Unit-1BR-A" in table
        assert "Portfolio Summary" in table

    def test_format_rating_distribution(self, sample_zones):
        """Test formatting rating distribution."""
        comparisons = compare_zones_to_benchmarks(sample_zones, "CZ12")
        dist = format_rating_distribution(comparisons)

        assert "Rating Distribution" in dist
        assert "excellent" in dist or "average" in dist


# =============================================================================
# ZONE SENSITIVITY TESTS
# =============================================================================

class TestZoneSensitivity:
    """Tests for zone-level sensitivity analysis."""

    def test_zone_sensitivity_analysis(self, zone_results_dict):
        """Test zone sensitivity analysis."""
        parameters = [SensitivityParameter.ELECTRICITY_RATE]
        ranges = {SensitivityParameter.ELECTRICITY_RATE: (0.75, 1.25)}

        results = zone_sensitivity_analysis(
            zone_results_dict,
            parameters,
            ranges,
            elec_rate_base=0.25,
            gas_rate_base=1.50,
        )

        assert len(results) == 3
        assert "Unit-1BR" in results
        assert len(results["Unit-1BR"]) == 2  # Low and high

    def test_zone_sensitivity_cost_change(self, zone_results_dict):
        """Test that sensitivity shows cost changes."""
        parameters = [SensitivityParameter.ELECTRICITY_RATE]
        ranges = {SensitivityParameter.ELECTRICITY_RATE: (0.75, 1.25)}

        results = zone_sensitivity_analysis(
            zone_results_dict,
            parameters,
            ranges,
        )

        # Check that costs differ at low and high
        unit_results = results["Unit-1BR"]
        costs = [r.annual_cost for r in unit_results]
        assert len(set(costs)) > 1  # Should have different costs


# =============================================================================
# HIGH IMPACT ZONE TESTS
# =============================================================================

class TestHighImpactZones:
    """Tests for identify_high_impact_zones function."""

    def test_identify_high_impact_zones(self, zone_results_dict):
        """Test identifying high impact zones."""
        total_cost = sum(z['annual_cost'] for z in zone_results_dict.values())
        impacts = identify_high_impact_zones(zone_results_dict, total_cost, threshold=0.3)

        # Should find zones with >30% of total cost
        for impact in impacts:
            if impact.is_high_impact:
                assert impact.building_share_pct > 30

    def test_impact_results_sorted(self, zone_results_dict):
        """Test that impact results are sorted by cost share."""
        total_cost = sum(z['annual_cost'] for z in zone_results_dict.values())
        impacts = identify_high_impact_zones(zone_results_dict, total_cost)

        # Should be sorted descending by share
        shares = [i.building_share_pct for i in impacts]
        assert shares == sorted(shares, reverse=True)

    def test_format_zone_impact_table(self, zone_results_dict):
        """Test formatting zone impact table."""
        total_cost = sum(z['annual_cost'] for z in zone_results_dict.values())
        impacts = identify_high_impact_zones(zone_results_dict, total_cost)
        table = format_zone_impact_table(impacts)

        assert "ZONE COST IMPACT ANALYSIS" in table
        assert "Unit-1BR" in table
        assert "TOTAL" in table


# =============================================================================
# ZONE TORNADO TESTS
# =============================================================================

class TestZoneTornado:
    """Tests for zone tornado analysis."""

    def test_zone_tornado_analysis(self, zone_results_dict):
        """Test zone tornado analysis."""
        total_cost = sum(z['annual_cost'] for z in zone_results_dict.values())
        tornado = zone_tornado_analysis(zone_results_dict, total_cost, rate_variation=0.25)

        assert len(tornado) == 3
        # Each item should be (name, base, low, high)
        for name, base, low, high in tornado:
            assert isinstance(name, str)
            assert low < base < high

    def test_tornado_sorted_by_swing(self, zone_results_dict):
        """Test that tornado is sorted by cost swing."""
        total_cost = sum(z['annual_cost'] for z in zone_results_dict.values())
        tornado = zone_tornado_analysis(zone_results_dict, total_cost)

        # Calculate swings and verify sorted
        swings = [(high - low) for _, _, low, high in tornado]
        assert swings == sorted(swings, reverse=True)


# =============================================================================
# BENCHMARK DATA TESTS
# =============================================================================

class TestBenchmarkData:
    """Tests for built-in benchmark data."""

    def test_dwelling_benchmarks_exist(self):
        """Test that dwelling benchmarks exist for all CZ."""
        assert len(DWELLING_UNIT_BENCHMARKS) == 16

    def test_common_area_benchmarks_exist(self):
        """Test that common area benchmarks exist."""
        expected_categories = ['lobby', 'corridor', 'parking', 'fitness']
        for cat in expected_categories:
            assert cat in COMMON_AREA_BENCHMARKS

    def test_benchmark_values_reasonable(self):
        """Test that benchmark EUI values are reasonable."""
        for cz, values in DWELLING_UNIT_BENCHMARKS.items():
            # EUI should increase from p10 to p90
            assert values["p10"] < values["p25"] < values["median"]
            assert values["median"] < values["p75"] < values["p90"]
            # EUI should be between 10 and 100 kBtu/sqft for residential
            assert 10 <= values["median"] <= 100


# =============================================================================
# INTEGRATION TESTS
# =============================================================================

class TestPhase5Integration:
    """Integration tests for Phase 5 analytics."""

    def test_complete_benchmark_workflow(self, sample_zones):
        """Test complete benchmarking workflow."""
        # Step 1: Get library
        library = get_benchmark_library()

        # Step 2: Compare zones
        comparisons = compare_zones_to_benchmarks(sample_zones, "CZ12")

        # Step 3: Calculate portfolio rating
        portfolio = calculate_portfolio_rating(comparisons)

        # Step 4: Identify outliers
        outliers = identify_benchmark_outliers(comparisons, threshold_percentile=75)

        # Step 5: Format report
        table = format_benchmark_summary_table(comparisons)

        # Verify complete workflow
        assert len(comparisons) == 4
        assert portfolio['zone_count'] == 4
        assert "ZONE BENCHMARK COMPARISON" in table

    def test_combined_sensitivity_and_benchmark(self, sample_zones, zone_results_dict):
        """Test combining sensitivity and benchmark analysis."""
        # Benchmark analysis
        comparisons = compare_zones_to_benchmarks(sample_zones, "CZ12")

        # Sensitivity analysis
        total_cost = sum(z['annual_cost'] for z in zone_results_dict.values())
        impacts = identify_high_impact_zones(zone_results_dict, total_cost)

        # Both should work together
        assert len(comparisons) > 0
        assert len(impacts) > 0

    def test_portfolio_improvement_potential(self, sample_zones):
        """Test calculating portfolio improvement potential."""
        comparisons = compare_zones_to_benchmarks(sample_zones, "CZ12")

        # Sum potential savings
        total_savings = sum(c.potential_cost_savings for c in comparisons)

        # Should have some improvement potential
        assert total_savings >= 0
