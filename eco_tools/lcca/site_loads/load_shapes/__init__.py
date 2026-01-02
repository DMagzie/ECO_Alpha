"""
Load Shape Profile Library.

Provides standard profiles for generating 8760 hourly data from annual totals.
"""

from .library import (
    LoadShapeProfile,
    LoadShapeGenerator,
    LoadShapeLibrary,
)

__all__ = [
    'LoadShapeProfile',
    'LoadShapeGenerator',
    'LoadShapeLibrary',
]
