"""
Geometry Builder - Main Builder Class

Central class for building geometry operations. Manages zones, surfaces,
and provides high-level interface for geometry creation and manipulation.
"""

from typing import List, Tuple, Optional, Dict, Any
from .models import Point3D, Surface, Zone
from .operations import PushPullOperation, CopyOperation, TransformOperation, TraceManager
from .validator import GeometryValidator
from .exceptions import (
    GeometryBuilderError,
    SurfaceNotFoundError,
    ZoneNotFoundError,
    OperationError
)


class GeometryBuilder:
    """
    Main geometry builder engine

    Provides high-level interface for creating and manipulating 3D building geometry.
    Maintains collections of zones and surfaces with validation and error handling.
    """

    def __init__(self):
        """Initialize empty geometry builder"""
        self.zones: List[Zone] = []
        self.surfaces: List[Surface] = []
        self.trace_manager = TraceManager()
        self.selected_surface_id: Optional[str] = None
        self.selected_zone_id: Optional[str] = None
        self.history: List[Dict[str, Any]] = []  # For undo/redo (future implementation)

    # ==================== Zone Creation ====================

    def create_zone_from_polygon(
        self,
        vertices_2d: List[Tuple[float, float]],
        height: float,
        zone_id: Optional[str] = None,
        zone_name: Optional[str] = None,
        zone_type: str = "conditioned"
    ) -> Zone:
        """
        Create a zone by extruding a 2D polygon

        Args:
            vertices_2d: List of (x, y) tuples defining the footprint
            height: Height to extrude (meters)
            zone_id: Optional custom zone ID (auto-generated if None)
            zone_name: Optional zone name (auto-generated if None)
            zone_type: Zone type (conditioned, unconditioned, plenum, etc.)

        Returns:
            Created zone

        Raises:
            GeometryBuilderError: If zone creation fails
        """
        try:
            if zone_id is None:
                zone_id = f"zone_{len(self.zones)}"

            if zone_name is None:
                zone_name = f"Zone {len(self.zones) + 1}"

            # Use operation to create zone
            zone, surfaces = PushPullOperation.extrude_2d_polygon(
                vertices_2d, height, zone_id
            )

            # Update zone properties
            zone.name = zone_name
            zone.zone_type = zone_type

            # Assign zone_id to all surfaces
            for surface in surfaces:
                surface.zone_id = zone.id

            # Add to builder
            self.zones.append(zone)
            self.surfaces.extend(surfaces)

            return zone

        except Exception as e:
            raise GeometryBuilderError(f"Failed to create zone from polygon: {e}")

    def create_rectangular_zone(
        self,
        width: float,
        depth: float,
        height: float,
        origin: Tuple[float, float] = (0, 0),
        zone_id: Optional[str] = None,
        zone_name: Optional[str] = None
    ) -> Zone:
        """
        Create a simple rectangular zone

        Args:
            width: Width in meters (X dimension)
            depth: Depth in meters (Y dimension)
            height: Height in meters (Z dimension)
            origin: (x, y) origin point
            zone_id: Optional custom zone ID
            zone_name: Optional zone name

        Returns:
            Created zone
        """
        x0, y0 = origin
        footprint = [
            (x0, y0),
            (x0 + width, y0),
            (x0 + width, y0 + depth),
            (x0, y0 + depth)
        ]

        return self.create_zone_from_polygon(
            footprint,
            height,
            zone_id=zone_id,
            zone_name=zone_name
        )

    # ==================== Surface Operations ====================

    def push_pull_surface(self, surface_id: str, distance: float) -> Surface:
        """
        Push or pull a surface along its normal

        Args:
            surface_id: ID of surface to modify
            distance: Distance to push (positive) or pull (negative) in meters

        Returns:
            Modified surface

        Raises:
            SurfaceNotFoundError: If surface not found
        """
        # Find surface
        surface = self.get_surface_by_id(surface_id)
        if not surface:
            raise SurfaceNotFoundError(f"Surface '{surface_id}' not found")

        try:
            # Apply push/pull
            new_surface = PushPullOperation.push_pull(surface, distance)

            # Replace in surfaces list
            idx = self.surfaces.index(surface)
            self.surfaces[idx] = new_surface

            # Update in zone
            zone = self.get_zone_by_id(surface.zone_id)
            if zone:
                zone_idx = zone.surfaces.index(surface)
                zone.surfaces[zone_idx] = new_surface

            return new_surface

        except Exception as e:
            raise OperationError(f"Push/pull failed: {e}")

    # ==================== Zone Operations ====================

    def copy_zone(
        self,
        zone_id: str,
        offset: Tuple[float, float, float] = (0, 0, 0),
        new_zone_id: Optional[str] = None
    ) -> Zone:
        """
        Copy a zone with optional offset

        Args:
            zone_id: ID of zone to copy
            offset: (x, y, z) offset for the copy
            new_zone_id: Optional ID for new zone

        Returns:
            New zone

        Raises:
            ZoneNotFoundError: If zone not found
        """
        original = self.get_zone_by_id(zone_id)
        if not original:
            raise ZoneNotFoundError(f"Zone '{zone_id}' not found")

        try:
            if new_zone_id is None:
                new_zone_id = f"{zone_id}_copy_{len(self.zones)}"

            new_zone = CopyOperation.copy_zone(original, offset, new_zone_id)

            # Add to builder
            self.zones.append(new_zone)
            self.surfaces.extend(new_zone.surfaces)

            return new_zone

        except Exception as e:
            raise GeometryBuilderError(f"Zone copy failed: {e}")

    def array_zones(
        self,
        zone_id: str,
        count: int,
        spacing_x: float = 0,
        spacing_y: float = 0
    ) -> List[Zone]:
        """
        Create linear array of zones

        Args:
            zone_id: ID of zone to array
            count: Number of copies to create
            spacing_x: Spacing in X direction (meters)
            spacing_y: Spacing in Y direction (meters)

        Returns:
            List of new zones

        Raises:
            ZoneNotFoundError: If zone not found
        """
        zone = self.get_zone_by_id(zone_id)
        if not zone:
            raise ZoneNotFoundError(f"Zone '{zone_id}' not found")

        try:
            new_zones = CopyOperation.array_zones(
                zone, count, spacing_x, spacing_y, base_id=zone_id
            )

            # Add to builder
            for new_zone in new_zones:
                self.zones.append(new_zone)
                self.surfaces.extend(new_zone.surfaces)

            return new_zones

        except Exception as e:
            raise GeometryBuilderError(f"Array operation failed: {e}")

    def delete_zone(self, zone_id: str) -> bool:
        """
        Delete a zone and its surfaces

        Args:
            zone_id: ID of zone to delete

        Returns:
            True if deleted, False if not found
        """
        zone = self.get_zone_by_id(zone_id)
        if not zone:
            return False

        # Remove surfaces
        for surface in zone.surfaces:
            if surface in self.surfaces:
                self.surfaces.remove(surface)

        # Remove zone
        self.zones.remove(zone)

        # Clear selection if deleted
        if self.selected_zone_id == zone_id:
            self.selected_zone_id = None

        return True

    # ==================== Transform Operations ====================

    def translate_zone(self, zone_id: str, offset: Tuple[float, float, float]) -> Zone:
        """Move zone by offset"""
        zone = self.get_zone_by_id(zone_id)
        if not zone:
            raise ZoneNotFoundError(f"Zone '{zone_id}' not found")

        return TransformOperation.translate_zone(zone, offset)

    def rotate_zone(
        self,
        zone_id: str,
        angle_deg: float,
        center: Optional[Point3D] = None
    ) -> Zone:
        """Rotate zone around Z axis"""
        zone = self.get_zone_by_id(zone_id)
        if not zone:
            raise ZoneNotFoundError(f"Zone '{zone_id}' not found")

        return TransformOperation.rotate_zone_z(zone, angle_deg, center)

    def scale_zone(
        self,
        zone_id: str,
        scale_factor: float,
        center: Optional[Point3D] = None
    ) -> Zone:
        """Scale zone uniformly"""
        zone = self.get_zone_by_id(zone_id)
        if not zone:
            raise ZoneNotFoundError(f"Zone '{zone_id}' not found")

        return TransformOperation.scale_zone(zone, scale_factor, center)

    # ==================== Query Methods ====================

    def get_zone_by_id(self, zone_id: str) -> Optional[Zone]:
        """Find zone by ID"""
        return next((z for z in self.zones if z.id == zone_id), None)

    def get_surface_by_id(self, surface_id: str) -> Optional[Surface]:
        """Find surface by ID"""
        return next((s for s in self.surfaces if s.id == surface_id), None)

    def get_zones_by_type(self, zone_type: str) -> List[Zone]:
        """Get all zones of a specific type"""
        return [z for z in self.zones if z.zone_type == zone_type]

    def get_surfaces_by_type(self, surface_type: str) -> List[Surface]:
        """Get all surfaces of a specific type"""
        return [s for s in self.surfaces if s.type == surface_type]

    def get_total_floor_area(self) -> float:
        """Calculate total floor area of all zones"""
        return sum(z.calculate_floor_area() for z in self.zones)

    def get_total_volume(self) -> float:
        """Calculate total volume of all zones"""
        return sum(z.calculate_volume() for z in self.zones)

    # ==================== Selection ====================

    def select_surface(self, surface_id: str):
        """Select a surface"""
        if self.get_surface_by_id(surface_id):
            self.selected_surface_id = surface_id

    def select_zone(self, zone_id: str):
        """Select a zone"""
        if self.get_zone_by_id(zone_id):
            self.selected_zone_id = zone_id

    def clear_selection(self):
        """Clear all selections"""
        self.selected_surface_id = None
        self.selected_zone_id = None

    def get_selected_surface(self) -> Optional[Surface]:
        """Get currently selected surface"""
        if self.selected_surface_id:
            return self.get_surface_by_id(self.selected_surface_id)
        return None

    def get_selected_zone(self) -> Optional[Zone]:
        """Get currently selected zone"""
        if self.selected_zone_id:
            return self.get_zone_by_id(self.selected_zone_id)
        return None

    # ==================== Validation ====================

    def validate_geometry(self, strict: bool = False) -> Dict[str, Any]:
        """
        Validate all geometry

        Args:
            strict: If True, warnings become errors

        Returns:
            Validation result dictionary
        """
        return GeometryValidator.validate_model(self.zones, strict)

    def get_validation_summary(self) -> str:
        """Get human-readable validation summary"""
        result = self.validate_geometry()
        return GeometryValidator.get_issues_summary(result)

    # ==================== Model Management ====================

    def clear(self):
        """Clear all geometry"""
        self.zones.clear()
        self.surfaces.clear()
        self.clear_selection()
        self.history.clear()

    def get_stats(self) -> Dict[str, Any]:
        """
        Get model statistics

        Returns:
            Dictionary with model statistics
        """
        return {
            'zone_count': len(self.zones),
            'surface_count': len(self.surfaces),
            'total_floor_area_m2': round(self.get_total_floor_area(), 2),
            'total_volume_m3': round(self.get_total_volume(), 2),
            'wall_count': len(self.get_surfaces_by_type('exterior_wall')) +
                         len(self.get_surfaces_by_type('interior_wall')),
            'window_count': len(self.get_surfaces_by_type('window')),
            'door_count': len(self.get_surfaces_by_type('door'))
        }

    def __repr__(self) -> str:
        stats = self.get_stats()
        return (f"GeometryBuilder("
                f"zones={stats['zone_count']}, "
                f"surfaces={stats['surface_count']}, "
                f"floor_area={stats['total_floor_area_m2']:.1f}m²)")
