"""
Geometry Builder - Custom Exception Hierarchy

Provides specific exceptions for geometry builder operations,
allowing fine-grained error handling and isolation from other modules.
"""


class GeometryBuilderError(Exception):
    """Base exception for all geometry builder errors"""
    pass


class ValidationError(GeometryBuilderError):
    """Raised when geometry validation fails"""
    pass


class OperationError(GeometryBuilderError):
    """Raised when a geometry operation fails"""
    pass


class ExportError(GeometryBuilderError):
    """Raised when EMJSON export fails"""
    pass


class InvalidGeometryError(GeometryBuilderError):
    """Raised when geometry is invalid (degenerate, self-intersecting, etc.)"""
    pass


class SurfaceNotFoundError(GeometryBuilderError):
    """Raised when a surface ID is not found"""
    pass


class ZoneNotFoundError(GeometryBuilderError):
    """Raised when a zone ID is not found"""
    pass


class CalibrationError(GeometryBuilderError):
    """Raised when floor plan calibration fails"""
    pass
