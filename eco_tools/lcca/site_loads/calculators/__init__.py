"""
Site Load Calculators.

Provides calculators for various non-modeled site energy loads.
Each calculator produces annual totals that can be distributed
across 8760 hours using load shape profiles.
"""

from .base import (
    BaseSiteLoadCalculator,
    CalculationResult,
)

from .lighting import (
    InteriorLightingCalculator,
    ParkingLightingCalculator,
    ParkingVentilationCalculator,
    SiteLightingCalculator,
    get_title24_lpd,
    list_space_types,
    TITLE24_LPD,
)

from .pools import (
    PoolPumpCalculator,
    PoolHeaterCalculator,
    SpaCalculator,
)

from .vertical_transport import (
    ElevatorCalculator,
    EscalatorCalculator,
)

from .miscellaneous import (
    EVChargerCalculator,
    ITTelecomCalculator,
    WaterPumpCalculator,
    TrashCompactorCalculator,
    GenericLoadCalculator,
)


__all__ = [
    # Base
    'BaseSiteLoadCalculator',
    'CalculationResult',

    # Lighting & Parking
    'InteriorLightingCalculator',
    'ParkingLightingCalculator',
    'ParkingVentilationCalculator',
    'SiteLightingCalculator',
    'get_title24_lpd',
    'list_space_types',
    'TITLE24_LPD',

    # Pools
    'PoolPumpCalculator',
    'PoolHeaterCalculator',
    'SpaCalculator',

    # Vertical Transport
    'ElevatorCalculator',
    'EscalatorCalculator',

    # Miscellaneous
    'EVChargerCalculator',
    'ITTelecomCalculator',
    'WaterPumpCalculator',
    'TrashCompactorCalculator',
    'GenericLoadCalculator',
]
