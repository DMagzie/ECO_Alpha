"""
Geometry Builder - Core Data Models

Defines the fundamental data structures for 3D building geometry:
- Point3D: 3D point in space
- Surface: Building surface (wall, floor, roof, window, door)
- Zone: Building zone containing multiple surfaces
"""

import numpy as np
from typing import List, Tuple, Optional
from dataclasses import dataclass, field
from .exceptions import InvalidGeometryError


@dataclass
class Point3D:
    """
    3D point in space (meters)

    Attributes:
        x: X coordinate (meters)
        y: Y coordinate (meters)
        z: Z coordinate (meters, default 0.0)
    """
    x: float
    y: float
    z: float = 0.0

    def to_array(self) -> np.ndarray:
        """Convert to numpy array"""
        return np.array([self.x, self.y, self.z])

    def to_tuple(self) -> Tuple[float, float, float]:
        """Convert to tuple (for JSON serialization)"""
        return (self.x, self.y, self.z)

    def __add__(self, other):
        """Add two points (vector addition)"""
        return Point3D(self.x + other.x, self.y + other.y, self.z + other.z)

    def __sub__(self, other):
        """Subtract two points (vector subtraction)"""
        return Point3D(self.x - other.x, self.y - other.y, self.z - other.z)

    def distance_to(self, other: 'Point3D') -> float:
        """Calculate distance to another point"""
        dx = self.x - other.x
        dy = self.y - other.y
        dz = self.z - other.z
        return np.sqrt(dx*dx + dy*dy + dz*dz)

    def __repr__(self) -> str:
        return f"Point3D(x={self.x:.2f}, y={self.y:.2f}, z={self.z:.2f})"


@dataclass
class Surface:
    """
    Building surface (wall, floor, roof, window, door)

    Attributes:
        id: Unique identifier
        vertices: List of vertices defining the surface (counter-clockwise)
        type: Surface type (exterior_wall, interior_wall, roof, floor, window, door)
        zone_id: ID of parent zone
        construction_id: ID of construction assembly
    """
    id: str
    vertices: List[Point3D]
    type: str  # "exterior_wall", "interior_wall", "roof", "floor", "window", "door"
    zone_id: Optional[str] = None
    construction_id: str = "default"

    def calculate_area(self) -> float:
        """
        Calculate surface area using cross product method
        Works for any planar polygon (convex or concave)

        Returns:
            Area in square meters
        """
        if len(self.vertices) < 3:
            return 0.0

        # Convert to numpy arrays
        points = np.array([v.to_array() for v in self.vertices])

        # Calculate area using cross product (Shoelace formula in 3D)
        total = np.zeros(3)
        for i in range(len(points)):
            v1 = points[i]
            v2 = points[(i + 1) % len(points)]
            total += np.cross(v1, v2)

        area = 0.5 * np.linalg.norm(total)
        return abs(area)

    def calculate_normal(self) -> np.ndarray:
        """
        Calculate surface normal vector (outward facing)

        Returns:
            Unit normal vector as numpy array
        """
        if len(self.vertices) < 3:
            return np.array([0, 0, 1])

        v0 = self.vertices[0].to_array()
        v1 = self.vertices[1].to_array()
        v2 = self.vertices[2].to_array()

        edge1 = v1 - v0
        edge2 = v2 - v0

        normal = np.cross(edge1, edge2)
        norm = np.linalg.norm(normal)

        if norm < 1e-10:
            return np.array([0, 0, 1])

        return normal / norm

    def calculate_tilt(self) -> float:
        """
        Calculate tilt from horizontal

        Returns:
            Tilt in degrees (0=flat/horizontal, 90=vertical, 180=upside-down)
        """
        normal = self.calculate_normal()
        tilt_rad = np.arccos(np.clip(normal[2], -1, 1))
        return np.degrees(tilt_rad)

    def calculate_azimuth(self) -> float:
        """
        Calculate azimuth (compass direction surface faces)

        Returns:
            Azimuth in degrees (0=N, 90=E, 180=S, 270=W)
        """
        normal = self.calculate_normal()
        azimuth_rad = np.arctan2(normal[0], normal[1])
        azimuth_deg = np.degrees(azimuth_rad)
        return (azimuth_deg + 360) % 360

    def get_centroid(self) -> Point3D:
        """
        Get geometric center of surface

        Returns:
            Center point
        """
        if not self.vertices:
            return Point3D(0, 0, 0)

        x = sum(v.x for v in self.vertices) / len(self.vertices)
        y = sum(v.y for v in self.vertices) / len(self.vertices)
        z = sum(v.z for v in self.vertices) / len(self.vertices)
        return Point3D(x, y, z)

    def get_bounds(self) -> Tuple[Point3D, Point3D]:
        """
        Get bounding box of surface

        Returns:
            (min_point, max_point) tuple
        """
        if not self.vertices:
            return (Point3D(0, 0, 0), Point3D(0, 0, 0))

        min_x = min(v.x for v in self.vertices)
        max_x = max(v.x for v in self.vertices)
        min_y = min(v.y for v in self.vertices)
        max_y = max(v.y for v in self.vertices)
        min_z = min(v.z for v in self.vertices)
        max_z = max(v.z for v in self.vertices)

        return (Point3D(min_x, min_y, min_z), Point3D(max_x, max_y, max_z))

    def is_planar(self, tolerance: float = 0.01) -> bool:
        """
        Check if all vertices lie on the same plane

        Args:
            tolerance: Maximum deviation from plane (meters)

        Returns:
            True if planar within tolerance
        """
        if len(self.vertices) < 4:
            return True  # 3 points always planar

        normal = self.calculate_normal()
        centroid = self.get_centroid()

        for vertex in self.vertices:
            # Vector from centroid to vertex
            vec = vertex - centroid
            # Distance from plane = dot product with normal
            distance = abs(np.dot(vec.to_array(), normal))
            if distance > tolerance:
                return False

        return True

    def __repr__(self) -> str:
        return f"Surface(id='{self.id}', type='{self.type}', vertices={len(self.vertices)}, area={self.calculate_area():.2f}m²)"


@dataclass
class Zone:
    """
    Building zone (thermal zone containing multiple surfaces)

    Attributes:
        id: Unique identifier
        name: Human-readable name
        surfaces: List of surfaces belonging to this zone
        zone_type: Type of zone (conditioned, unconditioned, plenum, attic, etc.)
        multiplier: Zone multiplier for identical zones
    """
    id: str
    name: str
    surfaces: List[Surface] = field(default_factory=list)
    zone_type: str = "conditioned"
    multiplier: int = 1

    def calculate_floor_area(self) -> float:
        """
        Calculate total floor area of zone

        Returns:
            Floor area in square meters
        """
        floor_surfaces = [s for s in self.surfaces if s.type == "floor"]
        return sum(s.calculate_area() for s in floor_surfaces)

    def calculate_volume(self) -> float:
        """
        Estimate volume from floor area and height

        Returns:
            Volume in cubic meters
        """
        floor_area = self.calculate_floor_area()

        # Find min and max z coordinates
        all_z = []
        for surface in self.surfaces:
            for vertex in surface.vertices:
                all_z.append(vertex.z)

        if not all_z:
            return 0.0

        height = max(all_z) - min(all_z)
        return floor_area * height

    def get_walls(self) -> List[Surface]:
        """Get all walls in zone"""
        return [s for s in self.surfaces if 'wall' in s.type]

    def get_exterior_walls(self) -> List[Surface]:
        """Get exterior walls only"""
        return [s for s in self.surfaces if s.type == 'exterior_wall']

    def get_interior_walls(self) -> List[Surface]:
        """Get interior walls only"""
        return [s for s in self.surfaces if s.type == 'interior_wall']

    def get_windows(self) -> List[Surface]:
        """Get all windows"""
        return [s for s in self.surfaces if s.type == 'window']

    def get_doors(self) -> List[Surface]:
        """Get all doors"""
        return [s for s in self.surfaces if s.type == 'door']

    def get_surface_by_id(self, surface_id: str) -> Optional[Surface]:
        """Find surface by ID"""
        return next((s for s in self.surfaces if s.id == surface_id), None)

    def add_surface(self, surface: Surface):
        """Add a surface to this zone"""
        surface.zone_id = self.id
        self.surfaces.append(surface)

    def remove_surface(self, surface_id: str) -> bool:
        """Remove surface by ID. Returns True if removed."""
        surface = self.get_surface_by_id(surface_id)
        if surface:
            self.surfaces.remove(surface)
            return True
        return False

    def get_bounds(self) -> Tuple[Point3D, Point3D]:
        """
        Get bounding box of entire zone

        Returns:
            (min_point, max_point) tuple
        """
        if not self.surfaces:
            return (Point3D(0, 0, 0), Point3D(0, 0, 0))

        all_vertices = []
        for surface in self.surfaces:
            all_vertices.extend(surface.vertices)

        if not all_vertices:
            return (Point3D(0, 0, 0), Point3D(0, 0, 0))

        min_x = min(v.x for v in all_vertices)
        max_x = max(v.x for v in all_vertices)
        min_y = min(v.y for v in all_vertices)
        max_y = max(v.y for v in all_vertices)
        min_z = min(v.z for v in all_vertices)
        max_z = max(v.z for v in all_vertices)

        return (Point3D(min_x, min_y, min_z), Point3D(max_x, max_y, max_z))

    def __repr__(self) -> str:
        return f"Zone(id='{self.id}', name='{self.name}', surfaces={len(self.surfaces)}, area={self.calculate_floor_area():.2f}m²)"
