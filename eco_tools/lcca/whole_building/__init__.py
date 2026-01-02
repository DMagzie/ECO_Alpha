"""
Whole-Building Energy Module.

Provides unified data models and tools for combining simulation engine output
with calculated site loads for complete whole-building energy analysis.

Key Components:
- WholeBuildingEnergy: Top-level container for complete energy data
- EnergyStream: Unified format for modeled and calculated energy
- HourlyRecord: Single hour of energy data
- SiteLoadDetail: Individual site load with calculation audit trail

Example Usage:
    >>> from eco_tools.lcca.whole_building import WholeBuildingEnergy, ReportMode
    >>> from eco_tools.lcca.parsers import parse_hourly_results
    >>>
    >>> # Parse simulation output
    >>> sim_output = parse_hourly_results("project - HourlyResults.csv")
    >>>
    >>> # Create whole-building energy from simulation only
    >>> wbe = WholeBuildingEnergy.from_simulation_only(sim_output)
    >>>
    >>> # Or with site loads
    >>> wbe = WholeBuildingEnergy.create(
    ...     project=project_info,
    ...     modeled=modeled_stream,
    ...     site_load_details=site_loads,
    ...     report_mode=ReportMode.FULL
    ... )
"""

from .schema import (
    # Enums
    EnergySource,
    ReportMode,
    LoadCategory,
    # Data models
    HourlyRecord,
    AnnualSummary,
    EnergyStream,
    SiteLoadDetail,
    ProjectInfo,
    WholeBuildingEnergy,
)
from .aggregator import (
    SiteLoadAggregator,
    WholeBuildingAggregator,
    create_whole_building_energy,
    calculate_site_loads,
    get_total_site_load_energy,
)

__all__ = [
    # Schema
    'EnergySource',
    'ReportMode',
    'LoadCategory',
    'HourlyRecord',
    'AnnualSummary',
    'EnergyStream',
    'SiteLoadDetail',
    'ProjectInfo',
    'WholeBuildingEnergy',
    # Aggregators
    'SiteLoadAggregator',
    'WholeBuildingAggregator',
    'create_whole_building_energy',
    'calculate_site_loads',
    'get_total_site_load_energy',
]
