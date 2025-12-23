"""
CUAC (California Utility Allowance Calculator) Module
=====================================================

This module provides parsers and data models for CBECC's CUAC output,
used for affordable housing utility allowance calculations per HCD requirements.

Key Features:
- Parse CUAC configuration from AnalysisResults.xml
- Extract PV/battery allocations per dwelling unit
- Parse utility rate structures (er.json)
- Support for per-bedroom energy metering

Data Sources:
- AnalysisResults.xml: CUAC config, DwellUnitType definitions
- PVBattery.csv: Per-zone PV/battery requirements
- er.json: Utility rate structure

Usage:
    from eco_tools.lcca.cuac import (
        CuacConfig,
        DwellUnitAllocation,
        parse_cuac_config,
        parse_pv_battery_csv,
        parse_utility_rate,
    )

    # Parse CUAC data from run folder
    cuac = parse_cuac_config(analysis_results_path)
    allocations = parse_pv_battery_csv(pv_battery_csv_path)
    rate = parse_utility_rate(er_json_path)
"""

from .models import (
    CuacConfig,
    DwellUnitAllocation,
    DwellUnitType,
    UtilityRate,
    RateSeason,
    TouPeriod,
    EnergyCostComponent,
    Tier,
    # Zone classification
    ZoneType,
    classify_zone_type,
    extract_bedroom_count,
    DWELLING_UNIT_SPACE_FUNCTIONS,
    COMMON_AREA_SPACE_FUNCTIONS,
)
from .parser import (
    parse_cuac_config,
    parse_pv_battery_csv,
    parse_utility_rate,
    parse_dwelling_unit_types,
)
from .csv_parser import (
    parse_cuac_csv,
    compare_cuac_results,
    CuacResults,
    UnitTypeConsumption,
    EndUseConsumption,
    MonthlyAllowance,
)

__all__ = [
    # Data models
    'CuacConfig',
    'DwellUnitAllocation',
    'DwellUnitType',
    'UtilityRate',
    'RateSeason',
    'TouPeriod',
    'EnergyCostComponent',
    'Tier',
    # Zone classification
    'ZoneType',
    'classify_zone_type',
    'extract_bedroom_count',
    'DWELLING_UNIT_SPACE_FUNCTIONS',
    'COMMON_AREA_SPACE_FUNCTIONS',
    # Parsers
    'parse_cuac_config',
    'parse_pv_battery_csv',
    'parse_utility_rate',
    'parse_dwelling_unit_types',
    # CUAC CSV parser
    'parse_cuac_csv',
    'compare_cuac_results',
    'CuacResults',
    'UnitTypeConsumption',
    'EndUseConsumption',
    'MonthlyAllowance',
]
