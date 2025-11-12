"""
Geometry Builder - Operations Module

Implements core geometry operations:
- Push/Pull: SketchUp-style face extrusion
- Extrude: Create 3D geometry from 2D polygons
- Copy/Paste: Duplicate zones with offset
- Array: Create linear patterns of zones
- Transform: Move, rotate, scale operations
"""

import numpy as np
from typing import List, Tuple, Optional
from .models import Point3D, Surface, Zone
from .exceptions import OperationError, InvalidGeometryError


class PushPullOperation:
    """SketchUp-style push/pull operations for surfaces"""

    @staticmethod
    def push_pull(surface: Surface, distance: float) -> Surface:
        """
        Push or pull a face along its normal

        Args:
            surface: Surface to modify
            distance: Distance to push (positive) or pull (negative) in meters

        Returns:
            New surface with modified vertices

        Raises:
            OperationError: If operation fails
        """
        try:
            normal = surface.calculate_normal()
            offset = normal * distance

            new_vertices = [
                Point3D(
                    v.x + offset[0],
                    v.y + offset[1],
                    v.z + offset[2]
                )
                for v in surface.vertices
            ]

            new_surface = Surface(
                id=surface.id,
                vertices=new_vertices,
                type=surface.type,
                zone_id=surface.zone_id,
                construction_id=surface.construction_id
            )

            return new_surface

        except Exception as e:
            raise OperationError(f"Push/pull operation failed: {e}")

    @staticmethod
    def extrude_2d_polygon(
        vertices_2d: List[Tuple[float, float]],
        height: float,
        base_id: str = "zone"
    ) -> Tuple[Zone, List[Surface]]:
        """
        Extrude 2D polygon to create 3D zone with walls, floor, and ceiling

        Args:
            vertices_2d: List of (x, y) tuples defining footprint
            height: Height to extrude (meters)
            base_id: Base ID for zone and surfaces

        Returns:
            Tuple of (Zone, List[Surface])

        Raises:
            InvalidGeometryError: If polygon is invalid
        """
        if len(vertices_2d) < 3:
            raise InvalidGeometryError(f"Polygon must have at least 3 vertices, got {len(vertices_2d)}")

        if height <= 0:
            raise InvalidGeometryError(f"Height must be positive, got {height}")

        try:
            # Create floor
            floor_vertices = [Point3D(x, y, 0.0) for x, y in vertices_2d]
            floor = Surface(
                id=f"{base_id}_floor",
                vertices=floor_vertices,
                type="floor"
            )

            # Create ceiling/roof (reverse order for correct normal)
            ceiling_vertices = [Point3D(x, y, height) for x, y in reversed(vertices_2d)]
            ceiling = Surface(
                id=f"{base_id}_roof",
                vertices=ceiling_vertices,
                type="roof"
            )

            # Create walls (counter-clockwise when viewed from outside)
            walls = []
            for i in range(len(vertices_2d)):
                v1_x, v1_y = vertices_2d[i]
                v2_x, v2_y = vertices_2d[(i + 1) % len(vertices_2d)]

                wall_vertices = [
                    Point3D(v1_x, v1_y, 0.0),
                    Point3D(v2_x, v2_y, 0.0),
                    Point3D(v2_x, v2_y, height),
                    Point3D(v1_x, v1_y, height)
                ]

                wall = Surface(
                    id=f"{base_id}_wall_{i}",
                    vertices=wall_vertices,
                    type="exterior_wall"
                )
                walls.append(wall)

            # Create zone
            zone = Zone(
                id=base_id,
                name=f"Zone {base_id}",
                surfaces=[floor, ceiling] + walls
            )

            # Set zone_id for all surfaces
            for surface in zone.surfaces:
                surface.zone_id = zone.id

            return zone, [floor, ceiling] + walls

        except Exception as e:
            raise OperationError(f"Extrusion failed: {e}")


class CopyOperation:
    """Copy and array operations for zones"""

    @staticmethod
    def copy_zone(zone: Zone, offset: Tuple[float, float, float] = (0, 0, 0), new_id: Optional[str] = None) -> Zone:
        """
        Create a copy of a zone with optional offset

        Args:
            zone: Zone to copy
            offset: (x, y, z) offset for the copy
            new_id: Optional ID for new zone (auto-generated if None)

        Returns:
            New zone

        Raises:
            OperationError: If copy fails
        """
        try:
            if new_id is None:
                new_id = f"{zone.id}_copy"

            new_zone = Zone(
                id=new_id,
                name=f"{zone.name} (Copy)",
                zone_type=zone.zone_type,
                multiplier=zone.multiplier
            )

            # Copy and offset surfaces
            for surface in zone.surfaces:
                new_vertices = [
                    Point3D(
                        v.x + offset[0],
                        v.y + offset[1],
                        v.z + offset[2]
                    )
                    for v in surface.vertices
                ]

                # Generate new surface ID
                surface_suffix = surface.id.split('_', 1)[-1] if '_' in surface.id else surface.id
                new_surface = Surface(
                    id=f"{new_id}_{surface_suffix}",
                    vertices=new_vertices,
                    type=surface.type,
                    zone_id=new_id,
                    construction_id=surface.construction_id
                )

                new_zone.surfaces.append(new_surface)

            return new_zone

        except Exception as e:
            raise OperationError(f"Zone copy failed: {e}")

    @staticmethod
    def array_zones(
        zone: Zone,
        count: int,
        spacing_x: float = 0,
        spacing_y: float = 0,
        base_id: Optional[str] = None
    ) -> List[Zone]:
        """
        Create linear array of zones

        Args:
            zone: Zone to array
            count: Number of copies to create
            spacing_x: Spacing between copies in X direction (meters)
            spacing_y: Spacing between copies in Y direction (meters)
            base_id: Base ID for array zones (auto-generated if None)

        Returns:
            List of new zones

        Raises:
            OperationError: If array operation fails
        """
        if count < 1:
            raise InvalidGeometryError(f"Array count must be at least 1, got {count}")

        try:
            new_zones = []

            for i in range(1, count + 1):
                offset = (spacing_x * i, spacing_y * i, 0)
                new_id = f"{base_id or zone.id}_array_{i}"
                new_zone = CopyOperation.copy_zone(zone, offset, new_id)
                new_zone.name = f"{zone.name} (Array {i})"
                new_zones.append(new_zone)

            return new_zones

        except Exception as e:
            raise OperationError(f"Array operation failed: {e}")


class TransformOperation:
    """Transform operations: move, rotate, scale"""

    @staticmethod
    def translate_zone(zone: Zone, offset: Tuple[float, float, float]) -> Zone:
        """
        Move zone by offset (in-place modification)

        Args:
            zone: Zone to translate
            offset: (x, y, z) offset in meters

        Returns:
            Modified zone (same instance)
        """
        for surface in zone.surfaces:
            surface.vertices = [
                Point3D(
                    v.x + offset[0],
                    v.y + offset[1],
                    v.z + offset[2]
                )
                for v in surface.vertices
            ]

        return zone

    @staticmethod
    def translate_surface(surface: Surface, offset: Tuple[float, float, float]) -> Surface:
        """
        Move surface by offset (in-place modification)

        Args:
            surface: Surface to translate
            offset: (x, y, z) offset in meters

        Returns:
            Modified surface (same instance)
        """
        surface.vertices = [
            Point3D(
                v.x + offset[0],
                v.y + offset[1],
                v.z + offset[2]
            )
            for v in surface.vertices
        ]

        return surface

    @staticmethod
    def rotate_zone_z(zone: Zone, angle_deg: float, center: Optional[Point3D] = None) -> Zone:
        """
        Rotate zone around Z axis (in-place modification)

        Args:
            zone: Zone to rotate
            angle_deg: Rotation angle in degrees (positive = counter-clockwise)
            center: Center of rotation (zone centroid if None)

        Returns:
            Modified zone (same instance)
        """
        if center is None:
            # Calculate zone centroid
            all_vertices = []
            for surface in zone.surfaces:
                all_vertices.extend(surface.vertices)

            if not all_vertices:
                return zone

            cx = sum(v.x for v in all_vertices) / len(all_vertices)
            cy = sum(v.y for v in all_vertices) / len(all_vertices)
            cz = sum(v.z for v in all_vertices) / len(all_vertices)
            center = Point3D(cx, cy, cz)

        angle_rad = np.radians(angle_deg)
        cos_a = np.cos(angle_rad)
        sin_a = np.sin(angle_rad)

        for surface in zone.surfaces:
            new_vertices = []
            for v in surface.vertices:
                # Translate to origin
                x = v.x - center.x
                y = v.y - center.y

                # Rotate
                x_rot = x * cos_a - y * sin_a
                y_rot = x * sin_a + y * cos_a

                # Translate back
                new_vertices.append(Point3D(
                    x_rot + center.x,
                    y_rot + center.y,
                    v.z
                ))

            surface.vertices = new_vertices

        return zone

    @staticmethod
    def scale_zone(zone: Zone, scale_factor: float, center: Optional[Point3D] = None) -> Zone:
        """
        Scale zone uniformly (in-place modification)

        Args:
            zone: Zone to scale
            scale_factor: Scale factor (1.0 = no change, 2.0 = double size)
            center: Center of scaling (zone centroid if None)

        Returns:
            Modified zone (same instance)

        Raises:
            InvalidGeometryError: If scale factor is invalid
        """
        if scale_factor <= 0:
            raise InvalidGeometryError(f"Scale factor must be positive, got {scale_factor}")

        if center is None:
            # Calculate zone centroid
            all_vertices = []
            for surface in zone.surfaces:
                all_vertices.extend(surface.vertices)

            if not all_vertices:
                return zone

            cx = sum(v.x for v in all_vertices) / len(all_vertices)
            cy = sum(v.y for v in all_vertices) / len(all_vertices)
            cz = sum(v.z for v in all_vertices) / len(all_vertices)
            center = Point3D(cx, cy, cz)

        for surface in zone.surfaces:
            new_vertices = []
            for v in surface.vertices:
                # Scale from center
                new_vertices.append(Point3D(
                    center.x + (v.x - center.x) * scale_factor,
                    center.y + (v.y - center.y) * scale_factor,
                    center.z + (v.z - center.z) * scale_factor
                ))

            surface.vertices = new_vertices

        return zone


class TraceManager:
    """Floor plan image tracing and calibration"""

    def __init__(self):
        self.image = None
        self.scale_factor: Optional[float] = None  # meters per pixel
        self.origin: Tuple[int, int] = (0, 0)  # Origin in pixel coordinates
        self.rotation: float = 0.0  # Rotation in degrees

    def calibrate_scale(self, pixel_distance: float, real_distance_m: float):
        """
        Calibrate scale using a known dimension

        Args:
            pixel_distance: Distance in pixels
            real_distance_m: Actual distance in meters

        Raises:
            InvalidGeometryError: If distances are invalid
        """
        if pixel_distance <= 0:
            raise InvalidGeometryError(f"Pixel distance must be positive, got {pixel_distance}")

        if real_distance_m <= 0:
            raise InvalidGeometryError(f"Real distance must be positive, got {real_distance_m}")

        self.scale_factor = real_distance_m / pixel_distance

    def pixel_to_world(self, pixel_coords: Tuple[int, int]) -> Tuple[float, float]:
        """
        Convert pixel coordinates to world coordinates (meters)

        Args:
            pixel_coords: (x, y) in pixels

        Returns:
            (x, y) in meters

        Raises:
            OperationError: If scale not calibrated
        """
        if self.scale_factor is None:
            raise OperationError("Scale not calibrated. Call calibrate_scale() first.")

        x_px, y_px = pixel_coords
        x_m = (x_px - self.origin[0]) * self.scale_factor
        y_m = (y_px - self.origin[1]) * self.scale_factor
        return (x_m, y_m)

    def world_to_pixel(self, world_coords: Tuple[float, float]) -> Tuple[int, int]:
        """
        Convert world coordinates to pixel coordinates

        Args:
            world_coords: (x, y) in meters

        Returns:
            (x, y) in pixels

        Raises:
            OperationError: If scale not calibrated
        """
        if self.scale_factor is None:
            raise OperationError("Scale not calibrated. Call calibrate_scale() first.")

        x_m, y_m = world_coords
        x_px = int(x_m / self.scale_factor + self.origin[0])
        y_px = int(y_m / self.scale_factor + self.origin[1])
        return (x_px, y_px)

    def set_origin(self, pixel_coords: Tuple[int, int]):
        """Set the origin point in pixel coordinates"""
        self.origin = pixel_coords

    def set_rotation(self, angle_deg: float):
        """Set rotation angle in degrees"""
        self.rotation = angle_deg
