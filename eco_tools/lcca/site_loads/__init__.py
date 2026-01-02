"""
Site Loads Module.

Calculators and utilities for non-modeled site energy loads including:
- Interior lighting (common areas)
- Parking (lighting and ventilation)
- Pool and spa equipment
- Elevators and escalators
- EV charging infrastructure
- IT/Telecom loads
- Water system pumps
- And more

Key Features:
- Load shape profiles for 8760 hourly distribution
- Title 24 2022 LPD values for lighting calculations
- Modeled load detection to prevent double-counting
- ENERGY STAR and DOE baselines for equipment

Each calculator produces annual energy totals that are then distributed
across 8760 hours using load shape profiles for accurate TOU analysis.
"""

from .load_shapes import (
    LoadShapeProfile,
    LoadShapeGenerator,
    LoadShapeLibrary,
)

from .calculators import (
    # Base
    BaseSiteLoadCalculator,
    CalculationResult,
    # Lighting & Parking
    InteriorLightingCalculator,
    ParkingLightingCalculator,
    ParkingVentilationCalculator,
    SiteLightingCalculator,
    get_title24_lpd,
    TITLE24_LPD,
    # Pools
    PoolPumpCalculator,
    PoolHeaterCalculator,
    SpaCalculator,
    # Transport
    ElevatorCalculator,
    EscalatorCalculator,
    # Misc
    EVChargerCalculator,
    ITTelecomCalculator,
    WaterPumpCalculator,
    TrashCompactorCalculator,
    GenericLoadCalculator,
)

from .detectors import (
    CbeccModeledLoadDetector,
    ModeledLoadReport,
    LoadDetectionResult,
    detect_modeled_loads,
)

__all__ = [
    # Load shapes
    'LoadShapeProfile',
    'LoadShapeGenerator',
    'LoadShapeLibrary',
    # Calculators
    'BaseSiteLoadCalculator',
    'CalculationResult',
    'InteriorLightingCalculator',
    'ParkingLightingCalculator',
    'ParkingVentilationCalculator',
    'SiteLightingCalculator',
    'get_title24_lpd',
    'TITLE24_LPD',
    'PoolPumpCalculator',
    'PoolHeaterCalculator',
    'SpaCalculator',
    'ElevatorCalculator',
    'EscalatorCalculator',
    'EVChargerCalculator',
    'ITTelecomCalculator',
    'WaterPumpCalculator',
    'TrashCompactorCalculator',
    'GenericLoadCalculator',
    # Detectors
    'CbeccModeledLoadDetector',
    'ModeledLoadReport',
    'LoadDetectionResult',
    'detect_modeled_loads',
]
