"""
ResOther Zone Metering Module
=============================

This module provides parsers and models for granular energy metering of
residential "other" zones (common areas) in multifamily buildings.

Similar to how CUAC meters energy by bedroom count for dwelling units,
this module enables metering by space function type for common areas.

Meter Categories:
- Lobby: Main entry, elevator lobbies
- Corridor: Hallways, common corridors
- Mechanical: Electrical/mechanical rooms, telecom
- Parking: Garage areas, ramps
- Fitness: Gym, exercise areas
- Office: Leasing office, management
- Storage: Bike storage, general storage
- Stairwell: Stair towers
- Restroom: Common restrooms
- Conference: Meeting rooms, multipurpose
- Laundry: Common laundry facilities

Usage:
    from eco_tools.lcca.res_other import (
        CommonAreaCategory,
        ResOtherZone,
        parse_res_other_zones,
        classify_space_function,
        aggregate_by_category,
    )

    # Parse ResOther zones from CBECC file
    zones = parse_res_other_zones(cbecc_file_path)

    # Aggregate by space category
    totals = aggregate_by_category(zones)
"""

from .models import (
    CommonAreaCategory,
    ResOtherZone,
    CommonAreaMeterAllocation,
    classify_space_function,
    SPACE_FUNCTION_MAPPING,
)
from .parser import (
    parse_res_other_zones,
    parse_res_other_from_xml,
    aggregate_by_category,
    create_meter_allocations,
    summarize_common_areas,
)

__all__ = [
    # Models
    'CommonAreaCategory',
    'ResOtherZone',
    'CommonAreaMeterAllocation',
    'classify_space_function',
    'SPACE_FUNCTION_MAPPING',
    # Parsers
    'parse_res_other_zones',
    'parse_res_other_from_xml',
    'aggregate_by_category',
    'create_meter_allocations',
    'summarize_common_areas',
]
