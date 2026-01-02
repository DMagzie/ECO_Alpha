"""
Modeled Load Detection Module.

Detects what loads are already modeled in CBECC simulation files to prevent
double-counting when calculating site loads.

Key concept: "Sometimes modeled" loads are those that:
1. CAN be modeled in CBECC but often aren't for compliance-only models
2. Need detection to determine if they should be calculated as site loads

Examples:
- Parking garage exhaust fans (PrkgGarExhFlow, PrkgGarExhFanPwr properties)
- Central ventilation systems (IAQOption property)
- Common area lighting (depends on modeling approach)
"""

from .cbecc_detector import (
    CbeccModeledLoadDetector,
    ModeledLoadReport,
    LoadDetectionResult,
    detect_modeled_loads,
)

__all__ = [
    'CbeccModeledLoadDetector',
    'ModeledLoadReport',
    'LoadDetectionResult',
    'detect_modeled_loads',
]
