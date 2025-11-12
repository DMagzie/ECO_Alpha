"""
Geometry Builder Module - Standalone 3D Modeling for Building Geometry

SketchUp-style geometry modeling tool for creating building energy models.
Can be used independently or integrated with ECO Tools workflow via EMJSON export.

Quick Start:
-----------
    from eco_tools.geometry_builder import GeometryBuilder

    # Create builder
    builder = GeometryBuilder()

    # Create rectangular room
    zone = builder.create_rectangular_zone(
        width=5.0,      # meters
        depth=4.0,      # meters
        height=2.7      # meters
    )

    # Export to EMJSON
    from eco_tools.geometry_builder import EMJSONAdapter
    emjson = EMJSONAdapter.to_emjson(builder)

Features:
--------
- SketchUp-style push/pull operations
- Create zones from 2D polygons (any shape, any angle)
- Copy/paste and array operations
- Floor plan tracing with calibration
- Geometry validation
- EMJSON v6 export

Module Information:
------------------
Version: 0.1.0
Status: Beta
Standalone: Yes (no dependencies on other emtools modules)
"""

__version__ = "0.1.0"
__status__ = "beta"
__standalone__ = True

# Minimal exports - only what's needed externally
from .builder import GeometryBuilder
from .emjson_adapter import EMJSONAdapter
from .exceptions import (
    GeometryBuilderError,
    ValidationError,
    OperationError,
    ExportError,
    InvalidGeometryError,
    SurfaceNotFoundError,
    ZoneNotFoundError,
    CalibrationError
)

# Models available for type hints if needed
from .models import Point3D, Surface, Zone

__all__ = [
    # Main classes
    'GeometryBuilder',
    'EMJSONAdapter',

    # Exceptions
    'GeometryBuilderError',
    'ValidationError',
    'OperationError',
    'ExportError',
    'InvalidGeometryError',
    'SurfaceNotFoundError',
    'ZoneNotFoundError',
    'CalibrationError',

    # Data models (for type hints)
    'Point3D',
    'Surface',
    'Zone',

    # Module metadata
    '__version__',
    '__status__',
    '__standalone__',
]


def get_module_info() -> dict:
    """
    Get information about this module

    Returns:
        Dictionary with module metadata
    """
    return {
        'name': 'geometry_builder',
        'version': __version__,
        'status': __status__,
        'standalone': __standalone__,
        'description': 'SketchUp-style 3D modeling for building energy models',
        'emjson_version': '6.0',
        'dependencies': ['numpy'],  # Only external dependency
        'optional_dependencies': ['streamlit', 'plotly'],  # For GUI
    }


def create_quick_example() -> GeometryBuilder:
    """
    Create a simple example building for testing

    Returns:
        GeometryBuilder with sample geometry
    """
    builder = GeometryBuilder()

    # Create main room
    builder.create_rectangular_zone(
        width=5.0,
        depth=4.0,
        height=2.7,
        origin=(0, 0),
        zone_id="living_room",
        zone_name="Living Room"
    )

    # Create adjacent bedroom
    builder.create_rectangular_zone(
        width=4.0,
        depth=3.5,
        height=2.7,
        origin=(5, 0),
        zone_id="bedroom",
        zone_name="Bedroom"
    )

    return builder
