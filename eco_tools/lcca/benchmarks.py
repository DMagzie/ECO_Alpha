"""
Zone Benchmarking Module
========================

Provides benchmark data and comparison tools for zone-level LCCA:
- EUI benchmarks by building type, zone type, and climate zone
- Cost benchmarks for typical energy costs per sqft
- Performance ratings (Poor, Below Average, Average, Good, Excellent)
- California Title 24 and ENERGY STAR benchmark integration

Phase 5 of LCCA module development.

Sources:
- California Energy Commission Building Energy Benchmarking data
- ENERGY STAR Portfolio Manager technical reference
- ASHRAE 90.1 Appendix G baseline values
- California Title 24 residential and nonresidential standards
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any
from enum import Enum

from .zone_energy import ZoneEnergySummary, ZoneLccaResult
from .cuac.models import ZoneType
from .res_other.models import CommonAreaCategory


# =============================================================================
# PERFORMANCE RATINGS
# =============================================================================

class PerformanceRating(Enum):
    """Performance rating relative to benchmark."""
    EXCELLENT = "excellent"    # Top 10% - significantly better than benchmark
    GOOD = "good"              # Top 25% - better than benchmark
    AVERAGE = "average"        # 25-75% - near benchmark median
    BELOW_AVERAGE = "below_average"  # 75-90% - worse than benchmark
    POOR = "poor"              # Bottom 10% - significantly worse than benchmark

    @classmethod
    def from_percentile(cls, percentile: float) -> "PerformanceRating":
        """Get rating from percentile (0-100, lower is better for EUI)."""
        if percentile <= 10:
            return cls.EXCELLENT
        elif percentile <= 25:
            return cls.GOOD
        elif percentile <= 75:
            return cls.AVERAGE
        elif percentile <= 90:
            return cls.BELOW_AVERAGE
        else:
            return cls.POOR


class BuildingVintage(Enum):
    """Building vintage for benchmark selection."""
    PRE_1978 = "pre_1978"
    V1978_1991 = "1978_1991"
    V1992_2005 = "1992_2005"
    V2006_2013 = "2006_2013"
    V2014_2019 = "2014_2019"
    V2020_PLUS = "2020_plus"
    T24_2022 = "t24_2022"
    T24_2025 = "t24_2025"


# =============================================================================
# ZONE BENCHMARK
# =============================================================================

@dataclass
class ZoneBenchmark:
    """
    Benchmark data for a specific zone type.

    Provides EUI and cost benchmarks with percentile ranges for comparison.
    """
    zone_type: ZoneType
    category: Optional[CommonAreaCategory] = None
    building_type: str = "multifamily"
    climate_zone: str = "CZ12"  # California climate zone
    vintage: BuildingVintage = BuildingVintage.T24_2022

    # EUI benchmarks (kBtu/sqft/year)
    eui_p10: float = 0.0      # 10th percentile (excellent)
    eui_p25: float = 0.0      # 25th percentile (good)
    eui_median: float = 0.0   # 50th percentile (average)
    eui_p75: float = 0.0      # 75th percentile (below average)
    eui_p90: float = 0.0      # 90th percentile (poor)

    # Electric intensity benchmarks (kWh/sqft/year)
    elec_p10: float = 0.0
    elec_p25: float = 0.0
    elec_median: float = 0.0
    elec_p75: float = 0.0
    elec_p90: float = 0.0

    # Cost benchmarks ($/sqft/year)
    cost_p10: float = 0.0
    cost_p25: float = 0.0
    cost_median: float = 0.0
    cost_p75: float = 0.0
    cost_p90: float = 0.0

    # Source attribution
    source: str = "California Energy Commission"
    year: int = 2024

    @property
    def eui_low(self) -> float:
        """Alias for p10 (best performance)."""
        return self.eui_p10

    @property
    def eui_high(self) -> float:
        """Alias for p90 (worst performance)."""
        return self.eui_p90

    def get_eui_percentile(self, eui: float) -> float:
        """
        Estimate percentile for a given EUI value.

        Uses linear interpolation between benchmark percentiles.
        Lower percentile = better performance.

        Args:
            eui: EUI value in kBtu/sqft/year

        Returns:
            Estimated percentile (0-100)
        """
        if eui <= self.eui_p10:
            return 5.0  # Better than 95%
        elif eui <= self.eui_p25:
            # Interpolate between 10-25
            frac = (eui - self.eui_p10) / max(0.01, self.eui_p25 - self.eui_p10)
            return 10.0 + frac * 15.0
        elif eui <= self.eui_median:
            # Interpolate between 25-50
            frac = (eui - self.eui_p25) / max(0.01, self.eui_median - self.eui_p25)
            return 25.0 + frac * 25.0
        elif eui <= self.eui_p75:
            # Interpolate between 50-75
            frac = (eui - self.eui_median) / max(0.01, self.eui_p75 - self.eui_median)
            return 50.0 + frac * 25.0
        elif eui <= self.eui_p90:
            # Interpolate between 75-90
            frac = (eui - self.eui_p75) / max(0.01, self.eui_p90 - self.eui_p75)
            return 75.0 + frac * 15.0
        else:
            return 95.0  # Worse than 95%

    def get_eui_rating(self, eui: float) -> PerformanceRating:
        """Get performance rating for a given EUI."""
        percentile = self.get_eui_percentile(eui)
        return PerformanceRating.from_percentile(percentile)

    def get_cost_percentile(self, cost_per_sqft: float) -> float:
        """Estimate percentile for a given cost per sqft."""
        if cost_per_sqft <= self.cost_p10:
            return 5.0
        elif cost_per_sqft <= self.cost_p25:
            frac = (cost_per_sqft - self.cost_p10) / max(0.01, self.cost_p25 - self.cost_p10)
            return 10.0 + frac * 15.0
        elif cost_per_sqft <= self.cost_median:
            frac = (cost_per_sqft - self.cost_p25) / max(0.01, self.cost_median - self.cost_p25)
            return 25.0 + frac * 25.0
        elif cost_per_sqft <= self.cost_p75:
            frac = (cost_per_sqft - self.cost_median) / max(0.01, self.cost_p75 - self.cost_median)
            return 50.0 + frac * 25.0
        elif cost_per_sqft <= self.cost_p90:
            frac = (cost_per_sqft - self.cost_p75) / max(0.01, self.cost_p90 - self.cost_p75)
            return 75.0 + frac * 15.0
        else:
            return 95.0

    def get_cost_rating(self, cost_per_sqft: float) -> PerformanceRating:
        """Get performance rating for a given cost per sqft."""
        percentile = self.get_cost_percentile(cost_per_sqft)
        return PerformanceRating.from_percentile(percentile)


# =============================================================================
# BENCHMARK COMPARISON RESULT
# =============================================================================

@dataclass
class BenchmarkComparison:
    """
    Result of comparing a zone to its benchmark.

    Contains performance metrics and ratings.
    """
    zone_name: str
    zone_type: ZoneType
    category: Optional[CommonAreaCategory] = None

    # Actual values
    actual_eui: float = 0.0
    actual_elec_intensity: float = 0.0
    actual_cost_per_sqft: float = 0.0

    # Benchmark values
    benchmark_eui_median: float = 0.0
    benchmark_elec_median: float = 0.0
    benchmark_cost_median: float = 0.0

    # Percentiles (lower = better)
    eui_percentile: float = 50.0
    elec_percentile: float = 50.0
    cost_percentile: float = 50.0

    # Performance ratings
    eui_rating: PerformanceRating = PerformanceRating.AVERAGE
    cost_rating: PerformanceRating = PerformanceRating.AVERAGE

    # Comparison to median
    eui_vs_median_pct: float = 0.0  # Negative = better than median
    cost_vs_median_pct: float = 0.0

    # Potential savings
    potential_eui_savings: float = 0.0  # kBtu/sqft if matched p25
    potential_cost_savings: float = 0.0  # $/sqft if matched p25

    @property
    def is_above_average(self) -> bool:
        """True if both EUI and cost are better than median."""
        return self.eui_percentile <= 50 and self.cost_percentile <= 50

    @property
    def needs_attention(self) -> bool:
        """True if performance is below average in either metric."""
        return self.eui_rating in [PerformanceRating.BELOW_AVERAGE, PerformanceRating.POOR] or \
               self.cost_rating in [PerformanceRating.BELOW_AVERAGE, PerformanceRating.POOR]

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'zone_name': self.zone_name,
            'zone_type': self.zone_type.value,
            'category': self.category.value if self.category else None,
            'actual_eui': self.actual_eui,
            'actual_cost_per_sqft': self.actual_cost_per_sqft,
            'benchmark_eui_median': self.benchmark_eui_median,
            'benchmark_cost_median': self.benchmark_cost_median,
            'eui_percentile': self.eui_percentile,
            'cost_percentile': self.cost_percentile,
            'eui_rating': self.eui_rating.value,
            'cost_rating': self.cost_rating.value,
            'eui_vs_median_pct': self.eui_vs_median_pct,
            'cost_vs_median_pct': self.cost_vs_median_pct,
            'potential_cost_savings': self.potential_cost_savings,
        }


# =============================================================================
# BENCHMARK LIBRARY
# =============================================================================

# Default EUI benchmarks for California multifamily by climate zone
# Based on CEC CEUS data, ENERGY STAR, and Title 24 standards

# Dwelling unit benchmarks (site EUI in kBtu/sqft/year)
DWELLING_UNIT_BENCHMARKS: Dict[str, Dict[str, float]] = {
    # Climate Zone: {p10, p25, median, p75, p90}
    "CZ01": {"p10": 18, "p25": 24, "median": 32, "p75": 42, "p90": 55},  # Arcata
    "CZ02": {"p10": 20, "p25": 26, "median": 35, "p75": 46, "p90": 60},  # Santa Rosa
    "CZ03": {"p10": 16, "p25": 22, "median": 28, "p75": 38, "p90": 50},  # Oakland
    "CZ04": {"p10": 17, "p25": 23, "median": 30, "p75": 40, "p90": 52},  # San Jose
    "CZ05": {"p10": 18, "p25": 24, "median": 32, "p75": 42, "p90": 55},  # Santa Maria
    "CZ06": {"p10": 15, "p25": 20, "median": 26, "p75": 34, "p90": 45},  # LA Coast
    "CZ07": {"p10": 16, "p25": 21, "median": 28, "p75": 36, "p90": 48},  # San Diego
    "CZ08": {"p10": 18, "p25": 24, "median": 32, "p75": 42, "p90": 55},  # LA Basin
    "CZ09": {"p10": 19, "p25": 25, "median": 34, "p75": 44, "p90": 58},  # LA Inland
    "CZ10": {"p10": 22, "p25": 30, "median": 40, "p75": 52, "p90": 68},  # Riverside
    "CZ11": {"p10": 24, "p25": 32, "median": 42, "p75": 55, "p90": 72},  # Red Bluff
    "CZ12": {"p10": 22, "p25": 29, "median": 38, "p75": 50, "p90": 65},  # Sacramento
    "CZ13": {"p10": 25, "p25": 33, "median": 44, "p75": 58, "p90": 75},  # Fresno
    "CZ14": {"p10": 28, "p25": 37, "median": 50, "p75": 65, "p90": 85},  # China Lake
    "CZ15": {"p10": 32, "p25": 42, "median": 56, "p75": 73, "p90": 95},  # Palm Springs
    "CZ16": {"p10": 30, "p25": 40, "median": 52, "p75": 68, "p90": 88},  # Blue Canyon
}

# Common area benchmarks by category (site EUI in kBtu/sqft/year)
COMMON_AREA_BENCHMARKS: Dict[str, Dict[str, float]] = {
    "lobby": {"p10": 25, "p25": 35, "median": 48, "p75": 65, "p90": 85},
    "corridor": {"p10": 12, "p25": 18, "median": 25, "p75": 35, "p90": 48},
    "parking": {"p10": 3, "p25": 5, "median": 8, "p75": 12, "p90": 18},
    "fitness": {"p10": 45, "p25": 60, "median": 80, "p75": 105, "p90": 135},
    "office": {"p10": 30, "p25": 40, "median": 55, "p75": 72, "p90": 95},
    "storage": {"p10": 2, "p25": 4, "median": 6, "p75": 10, "p90": 15},
    "mechanical": {"p10": 15, "p25": 22, "median": 32, "p75": 45, "p90": 60},
    "laundry": {"p10": 35, "p25": 48, "median": 65, "p75": 85, "p90": 110},
    "restroom": {"p10": 18, "p25": 26, "median": 36, "p75": 48, "p90": 65},
    "conference": {"p10": 28, "p25": 38, "median": 52, "p75": 68, "p90": 90},
    "stairwell": {"p10": 3, "p25": 5, "median": 8, "p75": 12, "p90": 18},
    "elevator": {"p10": 5, "p25": 8, "median": 12, "p75": 18, "p90": 25},
}

# Cost benchmarks ($/sqft/year at $0.25/kWh, $1.50/therm typical CA rates)
COST_MULTIPLIER = 0.10  # Rough $/sqft per kBtu/sqft @ CA rates


class BenchmarkLibrary:
    """
    Library of zone benchmarks for California multifamily buildings.

    Provides benchmarks by:
    - Climate zone (CZ01-CZ16)
    - Zone type (dwelling unit, common area)
    - Common area category (lobby, corridor, parking, etc.)
    - Building vintage (T24-2022, T24-2025)

    Example:
        >>> lib = BenchmarkLibrary()
        >>> benchmark = lib.get_benchmark(
        ...     zone_type=ZoneType.DWELLING_UNIT,
        ...     climate_zone="CZ12"
        ... )
        >>> rating = benchmark.get_eui_rating(35.5)  # kBtu/sqft
        >>> print(rating)  # PerformanceRating.AVERAGE
    """

    def __init__(self):
        self._dwelling_benchmarks: Dict[str, ZoneBenchmark] = {}
        self._common_area_benchmarks: Dict[Tuple[str, CommonAreaCategory], ZoneBenchmark] = {}
        self._load_default_benchmarks()

    def _load_default_benchmarks(self) -> None:
        """Load default California multifamily benchmarks."""
        # Load dwelling unit benchmarks for each climate zone
        for cz, values in DWELLING_UNIT_BENCHMARKS.items():
            self._dwelling_benchmarks[cz] = ZoneBenchmark(
                zone_type=ZoneType.DWELLING_UNIT,
                climate_zone=cz,
                building_type="multifamily",
                eui_p10=values["p10"],
                eui_p25=values["p25"],
                eui_median=values["median"],
                eui_p75=values["p75"],
                eui_p90=values["p90"],
                cost_p10=values["p10"] * COST_MULTIPLIER,
                cost_p25=values["p25"] * COST_MULTIPLIER,
                cost_median=values["median"] * COST_MULTIPLIER,
                cost_p75=values["p75"] * COST_MULTIPLIER,
                cost_p90=values["p90"] * COST_MULTIPLIER,
                source="CEC CEUS / Title 24",
                year=2024,
            )

        # Load common area benchmarks for each category
        for cat_name, values in COMMON_AREA_BENCHMARKS.items():
            try:
                category = CommonAreaCategory(cat_name)
            except ValueError:
                continue

            # Create benchmarks for all climate zones (common areas less climate-sensitive)
            for cz in DWELLING_UNIT_BENCHMARKS.keys():
                # Adjust for climate (hot climates have higher cooling)
                cz_num = int(cz.replace("CZ", "").replace("0", ""))
                climate_factor = 1.0
                if cz_num in [10, 13, 14, 15]:  # Hot climates
                    climate_factor = 1.15
                elif cz_num in [1, 16]:  # Cold climates
                    climate_factor = 1.10

                self._common_area_benchmarks[(cz, category)] = ZoneBenchmark(
                    zone_type=ZoneType.COMMON_AREA,
                    category=category,
                    climate_zone=cz,
                    building_type="multifamily",
                    eui_p10=values["p10"] * climate_factor,
                    eui_p25=values["p25"] * climate_factor,
                    eui_median=values["median"] * climate_factor,
                    eui_p75=values["p75"] * climate_factor,
                    eui_p90=values["p90"] * climate_factor,
                    cost_p10=values["p10"] * COST_MULTIPLIER * climate_factor,
                    cost_p25=values["p25"] * COST_MULTIPLIER * climate_factor,
                    cost_median=values["median"] * COST_MULTIPLIER * climate_factor,
                    cost_p75=values["p75"] * COST_MULTIPLIER * climate_factor,
                    cost_p90=values["p90"] * COST_MULTIPLIER * climate_factor,
                    source="CEC CEUS / Title 24",
                    year=2024,
                )

    def get_benchmark(
        self,
        zone_type: ZoneType,
        climate_zone: str = "CZ12",
        category: Optional[CommonAreaCategory] = None,
    ) -> Optional[ZoneBenchmark]:
        """
        Get benchmark for a specific zone type.

        Args:
            zone_type: Type of zone
            climate_zone: California climate zone (CZ01-CZ16)
            category: Common area category (required for common areas)

        Returns:
            ZoneBenchmark or None if not found
        """
        cz = climate_zone.upper()
        if not cz.startswith("CZ"):
            cz = f"CZ{cz.zfill(2)}"

        if zone_type == ZoneType.DWELLING_UNIT:
            return self._dwelling_benchmarks.get(cz)
        elif zone_type == ZoneType.COMMON_AREA and category:
            return self._common_area_benchmarks.get((cz, category))

        return None

    def get_dwelling_benchmark(self, climate_zone: str = "CZ12") -> Optional[ZoneBenchmark]:
        """Get benchmark for dwelling units."""
        return self.get_benchmark(ZoneType.DWELLING_UNIT, climate_zone)

    def get_common_area_benchmark(
        self,
        category: CommonAreaCategory,
        climate_zone: str = "CZ12"
    ) -> Optional[ZoneBenchmark]:
        """Get benchmark for a common area category."""
        return self.get_benchmark(ZoneType.COMMON_AREA, climate_zone, category)

    def list_climate_zones(self) -> List[str]:
        """List available climate zones."""
        return sorted(self._dwelling_benchmarks.keys())

    def list_common_area_categories(self) -> List[CommonAreaCategory]:
        """List common area categories with benchmarks."""
        categories = set()
        for (cz, cat) in self._common_area_benchmarks.keys():
            categories.add(cat)
        return sorted(categories, key=lambda c: c.value)


# Global library instance
_benchmark_library: Optional[BenchmarkLibrary] = None


def get_benchmark_library() -> BenchmarkLibrary:
    """Get the global benchmark library instance."""
    global _benchmark_library
    if _benchmark_library is None:
        _benchmark_library = BenchmarkLibrary()
    return _benchmark_library


# =============================================================================
# COMPARISON FUNCTIONS
# =============================================================================

def compare_zone_to_benchmark(
    zone: ZoneEnergySummary,
    climate_zone: str = "CZ12",
    benchmark: Optional[ZoneBenchmark] = None,
) -> BenchmarkComparison:
    """
    Compare a zone's performance to its benchmark.

    Args:
        zone: Zone energy summary to compare
        climate_zone: California climate zone
        benchmark: Optional specific benchmark (auto-selected if None)

    Returns:
        BenchmarkComparison with ratings and metrics
    """
    # Get benchmark
    if benchmark is None:
        library = get_benchmark_library()
        benchmark = library.get_benchmark(
            zone.zone_type,
            climate_zone,
            zone.category
        )

    if benchmark is None:
        # Return neutral comparison if no benchmark
        return BenchmarkComparison(
            zone_name=zone.zone_name,
            zone_type=zone.zone_type,
            category=zone.category,
            actual_eui=zone.eui_kbtu_sqft,
        )

    # Calculate actuals
    actual_eui = zone.eui_kbtu_sqft
    actual_elec = zone.elec_eui_kbtu_sqft / 3.412 if zone.area_sqft > 0 else 0  # Convert to kWh/sqft

    # Calculate percentiles
    eui_pct = benchmark.get_eui_percentile(actual_eui)
    eui_rating = PerformanceRating.from_percentile(eui_pct)

    # Calculate vs median
    eui_vs_median = 0.0
    if benchmark.eui_median > 0:
        eui_vs_median = ((actual_eui - benchmark.eui_median) / benchmark.eui_median) * 100

    # Calculate potential savings (to reach p25)
    potential_eui_savings = max(0, actual_eui - benchmark.eui_p25)
    potential_cost_savings = potential_eui_savings * COST_MULTIPLIER

    return BenchmarkComparison(
        zone_name=zone.zone_name,
        zone_type=zone.zone_type,
        category=zone.category,
        actual_eui=actual_eui,
        actual_elec_intensity=actual_elec,
        actual_cost_per_sqft=actual_eui * COST_MULTIPLIER,
        benchmark_eui_median=benchmark.eui_median,
        benchmark_elec_median=benchmark.elec_median,
        benchmark_cost_median=benchmark.cost_median,
        eui_percentile=eui_pct,
        eui_rating=eui_rating,
        cost_rating=eui_rating,  # Assume cost tracks EUI
        eui_vs_median_pct=eui_vs_median,
        cost_vs_median_pct=eui_vs_median,  # Same for cost
        potential_eui_savings=potential_eui_savings,
        potential_cost_savings=potential_cost_savings,
    )


def compare_zones_to_benchmarks(
    zones: List[ZoneEnergySummary],
    climate_zone: str = "CZ12",
) -> List[BenchmarkComparison]:
    """
    Compare multiple zones to their benchmarks.

    Args:
        zones: List of zone energy summaries
        climate_zone: California climate zone

    Returns:
        List of BenchmarkComparison results
    """
    return [compare_zone_to_benchmark(z, climate_zone) for z in zones]


def identify_high_impact_zones(
    comparisons: List[BenchmarkComparison],
    threshold_percentile: float = 75.0,
) -> List[BenchmarkComparison]:
    """
    Identify zones with below-average performance.

    These zones represent the best opportunities for efficiency improvements.

    Args:
        comparisons: List of benchmark comparisons
        threshold_percentile: Percentile threshold for "high impact"

    Returns:
        List of comparisons for zones above threshold
    """
    return [c for c in comparisons if c.eui_percentile > threshold_percentile]


def calculate_portfolio_rating(
    comparisons: List[BenchmarkComparison],
) -> Dict[str, Any]:
    """
    Calculate overall portfolio performance rating.

    Args:
        comparisons: List of benchmark comparisons

    Returns:
        Dictionary with portfolio-level metrics
    """
    if not comparisons:
        return {
            'zone_count': 0,
            'average_percentile': 50.0,
            'rating': PerformanceRating.AVERAGE.value,
        }

    # Calculate weighted average by count (could weight by area)
    avg_eui_pct = sum(c.eui_percentile for c in comparisons) / len(comparisons)
    avg_cost_pct = sum(c.cost_percentile for c in comparisons) / len(comparisons)

    # Count by rating
    rating_counts = {}
    for rating in PerformanceRating:
        rating_counts[rating.value] = sum(1 for c in comparisons if c.eui_rating == rating)

    # Overall rating
    overall_rating = PerformanceRating.from_percentile(avg_eui_pct)

    # Zones needing attention
    needs_attention = [c for c in comparisons if c.needs_attention]

    # Total potential savings
    total_potential_savings = sum(c.potential_cost_savings for c in comparisons)

    return {
        'zone_count': len(comparisons),
        'average_eui_percentile': avg_eui_pct,
        'average_cost_percentile': avg_cost_pct,
        'overall_rating': overall_rating.value,
        'rating_counts': rating_counts,
        'excellent_count': rating_counts.get('excellent', 0),
        'good_count': rating_counts.get('good', 0),
        'average_count': rating_counts.get('average', 0),
        'below_average_count': rating_counts.get('below_average', 0),
        'poor_count': rating_counts.get('poor', 0),
        'zones_needing_attention': len(needs_attention),
        'total_potential_savings_per_sqft': total_potential_savings,
    }


# =============================================================================
# FORMATTING
# =============================================================================

def format_benchmark_comparison(comparison: BenchmarkComparison) -> str:
    """Format a single benchmark comparison as text."""
    rating_symbol = {
        PerformanceRating.EXCELLENT: "★★★",
        PerformanceRating.GOOD: "★★☆",
        PerformanceRating.AVERAGE: "★☆☆",
        PerformanceRating.BELOW_AVERAGE: "⚠️",
        PerformanceRating.POOR: "❌",
    }

    lines = [
        f"Zone: {comparison.zone_name}",
        f"  Type: {comparison.zone_type.value}",
    ]

    if comparison.category:
        lines.append(f"  Category: {comparison.category.value}")

    lines.extend([
        f"  EUI: {comparison.actual_eui:.1f} kBtu/sqft ({comparison.eui_percentile:.0f}th percentile)",
        f"  Rating: {rating_symbol.get(comparison.eui_rating, '')} {comparison.eui_rating.value.upper()}",
        f"  vs Median: {comparison.eui_vs_median_pct:+.1f}%",
    ])

    if comparison.potential_cost_savings > 0:
        lines.append(f"  Potential Savings: ${comparison.potential_cost_savings:.2f}/sqft/year")

    return "\n".join(lines)


def format_benchmark_summary_table(
    comparisons: List[BenchmarkComparison]
) -> str:
    """Format benchmark comparisons as a summary table."""
    lines = [
        "=" * 100,
        "ZONE BENCHMARK COMPARISON",
        "=" * 100,
        "",
        f"{'Zone Name':<25} {'Type':<12} {'EUI':>8} {'Pctl':>6} {'Rating':<15} {'vs Median':>10}",
        "-" * 100,
    ]

    for c in sorted(comparisons, key=lambda x: x.eui_percentile, reverse=True):
        zone_type = c.zone_type.value[:10]
        if c.category:
            zone_type = c.category.value[:10]

        lines.append(
            f"{c.zone_name:<25} {zone_type:<12} "
            f"{c.actual_eui:>7.1f} {c.eui_percentile:>5.0f}% "
            f"{c.eui_rating.value:<15} {c.eui_vs_median_pct:>+9.1f}%"
        )

    lines.extend(["-" * 100, ""])

    # Add portfolio summary
    portfolio = calculate_portfolio_rating(comparisons)
    lines.extend([
        f"Portfolio Summary: {portfolio['zone_count']} zones",
        f"  Overall Rating: {portfolio['overall_rating'].upper()}",
        f"  Average Percentile: {portfolio['average_eui_percentile']:.0f}%",
        f"  Zones Needing Attention: {portfolio['zones_needing_attention']}",
        "=" * 100,
    ])

    return "\n".join(lines)


def format_rating_distribution(comparisons: List[BenchmarkComparison]) -> str:
    """Format rating distribution as a bar chart."""
    portfolio = calculate_portfolio_rating(comparisons)

    lines = [
        "Rating Distribution:",
        "",
    ]

    max_count = max(portfolio['rating_counts'].values()) if portfolio['rating_counts'] else 1
    bar_width = 30

    for rating in PerformanceRating:
        count = portfolio['rating_counts'].get(rating.value, 0)
        bar_len = int((count / max_count) * bar_width) if max_count > 0 else 0
        bar = "█" * bar_len + "░" * (bar_width - bar_len)
        lines.append(f"  {rating.value:<14} {bar} {count}")

    return "\n".join(lines)
