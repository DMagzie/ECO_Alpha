"""
ECO Tools - Interactive Geometry Builder
Prototype Implementation

Install requirements:
pip install pyvista streamlit stpyvista pillow numpy shapely
"""

import numpy as np
from typing import List, Tuple, Optional, Dict
from dataclasses import dataclass, field
from copy import deepcopy
import json


# ==================== Data Models ====================

@dataclass
class Point3D:
    """3D point in space"""
    x: float
    y: float
    z: float = 0.0
    
    def to_array(self) -> np.ndarray:
        return np.array([self.x, self.y, self.z])
    
    def to_tuple(self) -> Tuple[float, float, float]:
        return (self.x, self.y, self.z)
    
    def __add__(self, other):
        return Point3D(self.x + other.x, self.y + other.y, self.z + other.z)
    
    def __sub__(self, other):
        return Point3D(self.x - other.x, self.y - other.y, self.z - other.z)


@dataclass
class Surface:
    """Building surface (wall, floor, roof, etc.)"""
    id: str
    vertices: List[Point3D]
    type: str  # "exterior_wall", "interior_wall", "roof", "floor", "window", "door"
    zone_id: Optional[str] = None
    construction_id: str = "default"
    
    def calculate_area(self) -> float:
        """Calculate surface area using cross product method"""
        if len(self.vertices) < 3:
            return 0.0
        
        # Convert to numpy arrays
        points = np.array([v.to_array() for v in self.vertices])
        
        # Calculate area using cross product
        total = np.zeros(3)
        for i in range(len(points)):
            v1 = points[i]
            v2 = points[(i + 1) % len(points)]
            total += np.cross(v1, v2)
        
        area = 0.5 * np.linalg.norm(total)
        return abs(area)
    
    def calculate_normal(self) -> np.ndarray:
        """Calculate surface normal vector"""
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
        """Calculate tilt from horizontal (0=flat, 90=vertical, 180=upside-down)"""
        normal = self.calculate_normal()
        tilt_rad = np.arccos(np.clip(normal[2], -1, 1))
        return np.degrees(tilt_rad)
    
    def calculate_azimuth(self) -> float:
        """Calculate azimuth (0=N, 90=E, 180=S, 270=W)"""
        normal = self.calculate_normal()
        azimuth_rad = np.arctan2(normal[0], normal[1])
        azimuth_deg = np.degrees(azimuth_rad)
        return (azimuth_deg + 360) % 360
    
    def get_centroid(self) -> Point3D:
        """Get center point of surface"""
        x = sum(v.x for v in self.vertices) / len(self.vertices)
        y = sum(v.y for v in self.vertices) / len(self.vertices)
        z = sum(v.z for v in self.vertices) / len(self.vertices)
        return Point3D(x, y, z)


@dataclass
class Zone:
    """Building zone"""
    id: str
    name: str
    surfaces: List[Surface] = field(default_factory=list)
    zone_type: str = "conditioned"
    multiplier: int = 1
    
    def calculate_floor_area(self) -> float:
        """Calculate total floor area"""
        floor_surfaces = [s for s in self.surfaces if s.type == "floor"]
        return sum(s.calculate_area() for s in floor_surfaces)
    
    def calculate_volume(self) -> float:
        """Estimate volume from floor area and average height"""
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


# ==================== Operations ====================

class PushPullOperation:
    """SketchUp-style push/pull for faces"""
    
    @staticmethod
    def push_pull(surface: Surface, distance: float) -> Surface:
        """
        Push or pull a face along its normal
        Positive = push out, Negative = pull in
        """
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
    
    @staticmethod
    def extrude_2d_polygon(vertices_2d: List[Tuple[float, float]], 
                          height: float,
                          base_id: str = "zone") -> Tuple[Zone, List[Surface]]:
        """
        Extrude 2D polygon to create 3D zone with walls, floor, and ceiling
        """
        # Create floor
        floor_vertices = [Point3D(x, y, 0.0) for x, y in vertices_2d]
        floor = Surface(
            id=f"{base_id}_floor",
            vertices=floor_vertices,
            type="floor"
        )
        
        # Create ceiling/roof
        ceiling_vertices = [Point3D(x, y, height) for x, y in vertices_2d]
        ceiling = Surface(
            id=f"{base_id}_roof",
            vertices=ceiling_vertices,
            type="roof"
        )
        
        # Create walls
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
        
        return zone, [floor, ceiling] + walls


class TraceManager:
    """Manage floor plan image tracing"""
    
    def __init__(self):
        self.image = None
        self.scale_factor = None  # meters per pixel
        self.origin = (0, 0)  # Origin in pixel coordinates
    
    def calibrate_scale(self, pixel_distance: float, real_distance_m: float):
        """
        Calibrate the scale using a known dimension
        
        Args:
            pixel_distance: Distance in pixels
            real_distance_m: Actual distance in meters
        """
        self.scale_factor = real_distance_m / pixel_distance
    
    def pixel_to_world(self, pixel_coords: Tuple[int, int]) -> Tuple[float, float]:
        """Convert pixel coordinates to world coordinates (meters)"""
        if self.scale_factor is None:
            raise ValueError("Scale not calibrated. Call calibrate_scale() first.")
        
        x_px, y_px = pixel_coords
        x_m = (x_px - self.origin[0]) * self.scale_factor
        y_m = (y_px - self.origin[1]) * self.scale_factor
        return (x_m, y_m)
    
    def world_to_pixel(self, world_coords: Tuple[float, float]) -> Tuple[int, int]:
        """Convert world coordinates to pixel coordinates"""
        if self.scale_factor is None:
            raise ValueError("Scale not calibrated. Call calibrate_scale() first.")
        
        x_m, y_m = world_coords
        x_px = int(x_m / self.scale_factor + self.origin[0])
        y_px = int(y_m / self.scale_factor + self.origin[1])
        return (x_px, y_px)


class GeometryBuilder:
    """Main geometry building engine"""
    
    def __init__(self):
        self.zones: List[Zone] = []
        self.surfaces: List[Surface] = []
        self.trace_manager = TraceManager()
        self.selected_surface_id: Optional[str] = None
        self.history: List[Dict] = []  # For undo/redo
    
    def create_zone_from_polygon(self, 
                                 vertices_2d: List[Tuple[float, float]], 
                                 height: float,
                                 zone_id: Optional[str] = None) -> Zone:
        """
        Create a zone by extruding a 2D polygon
        
        Args:
            vertices_2d: List of (x, y) tuples defining the footprint
            height: Height to extrude (meters)
            zone_id: Optional custom zone ID
        
        Returns:
            Created zone
        """
        if zone_id is None:
            zone_id = f"zone_{len(self.zones)}"
        
        zone, surfaces = PushPullOperation.extrude_2d_polygon(
            vertices_2d, height, zone_id
        )
        
        # Assign zone_id to all surfaces
        for surface in surfaces:
            surface.zone_id = zone.id
        
        self.zones.append(zone)
        self.surfaces.extend(surfaces)
        
        return zone
    
    def push_pull_surface(self, surface_id: str, distance: float) -> Surface:
        """
        Push or pull a surface
        
        Args:
            surface_id: ID of surface to modify
            distance: Distance to push/pull (positive = out, negative = in)
        
        Returns:
            Modified surface
        """
        # Find surface
        surface = next((s for s in self.surfaces if s.id == surface_id), None)
        if not surface:
            raise ValueError(f"Surface {surface_id} not found")
        
        # Apply push/pull
        new_surface = PushPullOperation.push_pull(surface, distance)
        
        # Replace in surfaces list
        idx = self.surfaces.index(surface)
        self.surfaces[idx] = new_surface
        
        # Update in zone
        for zone in self.zones:
            if surface in zone.surfaces:
                zone_idx = zone.surfaces.index(surface)
                zone.surfaces[zone_idx] = new_surface
                break
        
        return new_surface
    
    def copy_zone(self, zone_id: str, offset: Tuple[float, float, float] = (0, 0, 0)) -> Zone:
        """
        Copy a zone and optionally offset it
        
        Args:
            zone_id: ID of zone to copy
            offset: (x, y, z) offset for the copy
        
        Returns:
            New zone
        """
        # Find original zone
        original = next((z for z in self.zones if z.id == zone_id), None)
        if not original:
            raise ValueError(f"Zone {zone_id} not found")
        
        # Deep copy
        new_zone_id = f"{zone_id}_copy_{len(self.zones)}"
        new_zone = Zone(
            id=new_zone_id,
            name=f"{original.name} (Copy)",
            zone_type=original.zone_type,
            multiplier=original.multiplier
        )
        
        # Copy and offset surfaces
        for surface in original.surfaces:
            new_vertices = [
                Point3D(
                    v.x + offset[0],
                    v.y + offset[1],
                    v.z + offset[2]
                )
                for v in surface.vertices
            ]
            
            new_surface = Surface(
                id=f"{new_zone_id}_{surface.id.split('_', 1)[-1]}",
                vertices=new_vertices,
                type=surface.type,
                zone_id=new_zone_id,
                construction_id=surface.construction_id
            )
            
            new_zone.surfaces.append(new_surface)
            self.surfaces.append(new_surface)
        
        self.zones.append(new_zone)
        return new_zone
    
    def array_zones(self, 
                    zone_id: str, 
                    count: int, 
                    spacing_x: float = 0, 
                    spacing_y: float = 0) -> List[Zone]:
        """
        Create multiple copies in a linear array
        
        Args:
            zone_id: ID of zone to array
            count: Number of copies to create
            spacing_x: Spacing between copies in X direction
            spacing_y: Spacing between copies in Y direction
        
        Returns:
            List of new zones
        """
        new_zones = []
        for i in range(1, count + 1):
            offset = (spacing_x * i, spacing_y * i, 0)
            new_zone = self.copy_zone(zone_id, offset)
            new_zones.append(new_zone)
        
        return new_zones
    
    def to_emjson(self) -> dict:
        """
        Export to EMJSON v6 format
        
        Returns:
            EMJSON dictionary
        """
        from datetime import datetime
        
        emjson = {
            "emjson_version": "6.0",
            "project": {
                "name": "Geometry Builder Model",
                "created": datetime.now().isoformat(),
                "source_format": "ECO_GeometryBuilder"
            },
            "geometry": {
                "zones": [],
                "surfaces": {
                    "walls": [],
                    "roofs": [],
                    "floors": [],
                    "windows": [],
                    "doors": []
                }
            }
        }
        
        # Export zones
        for zone in self.zones:
            emjson_zone = {
                "id": zone.id,
                "name": zone.name,
                "floor_area_m2": round(zone.calculate_floor_area(), 2),
                "volume_m3": round(zone.calculate_volume(), 2),
                "zone_type": zone.zone_type,
                "multiplier": zone.multiplier
            }
            emjson["geometry"]["zones"].append(emjson_zone)
        
        # Export surfaces
        for surface in self.surfaces:
            emjson_surface = {
                "id": surface.id,
                "zone_id": surface.zone_id,
                "type": surface.type,
                "geometry_mode": "explicit",
                "vertices_m": [v.to_tuple() for v in surface.vertices],
                "area_m2": round(surface.calculate_area(), 2),
                "tilt_deg": round(surface.calculate_tilt(), 1),
                "azimuth_deg": round(surface.calculate_azimuth(), 1),
                "construction_id": surface.construction_id
            }
            
            # Categorize surface
            if "wall" in surface.type:
                category = "walls"
            elif surface.type == "roof":
                category = "roofs"
            elif surface.type == "floor":
                category = "floors"
            elif surface.type == "window":
                category = "windows"
            elif surface.type == "door":
                category = "doors"
            else:
                category = "walls"  # Default
            
            emjson["geometry"]["surfaces"][category].append(emjson_surface)
        
        return emjson
    
    def validate_geometry(self) -> List[Dict]:
        """
        Validate geometry for common issues
        
        Returns:
            List of validation errors/warnings
        """
        issues = []
        
        for surface in self.surfaces:
            # Check vertex count
            if len(surface.vertices) < 3:
                issues.append({
                    "level": "error",
                    "surface_id": surface.id,
                    "message": f"Surface has only {len(surface.vertices)} vertices (minimum 3)"
                })
            
            # Check area
            area = surface.calculate_area()
            if area < 0.01:
                issues.append({
                    "level": "warning",
                    "surface_id": surface.id,
                    "message": f"Surface area is very small: {area:.4f} m²"
                })
            
            # Check for degenerate geometry
            if area < 1e-6:
                issues.append({
                    "level": "error",
                    "surface_id": surface.id,
                    "message": "Surface area is effectively zero (degenerate)"
                })
        
        return issues


# ==================== Example Usage ====================

if __name__ == "__main__":
    # Create builder
    builder = GeometryBuilder()
    
    # Example 1: Simple rectangular room
    print("Creating simple rectangular room...")
    footprint = [(0, 0), (5, 0), (5, 4), (0, 4)]  # 5m x 4m
    zone1 = builder.create_zone_from_polygon(footprint, height=2.7)
    
    print(f"Zone created: {zone1.id}")
    print(f"Floor area: {zone1.calculate_floor_area():.2f} m²")
    print(f"Volume: {zone1.calculate_volume():.2f} m³")
    print(f"Surfaces: {len(zone1.surfaces)}")
    
    # Example 2: L-shaped room (non-rectangular)
    print("\nCreating L-shaped room...")
    l_footprint = [
        (0, 0), (6, 0), (6, 3), (3, 3), (3, 5), (0, 5)
    ]
    zone2 = builder.create_zone_from_polygon(l_footprint, height=2.7, zone_id="l_shaped")
    
    print(f"Zone created: {zone2.id}")
    print(f"Floor area: {zone2.calculate_floor_area():.2f} m²")
    
    # Example 3: Copy zone to create adjacent room
    print("\nCopying zone...")
    zone3 = builder.copy_zone(zone1.id, offset=(6, 0, 0))
    print(f"Copied zone: {zone3.id}")
    
    # Example 4: Array zones (like apartment units)
    print("\nCreating array of zones...")
    array_zones = builder.array_zones(zone1.id, count=3, spacing_x=7, spacing_y=0)
    print(f"Created {len(array_zones)} additional zones")
    
    # Validate
    print("\nValidating geometry...")
    issues = builder.validate_geometry()
    if issues:
        print(f"Found {len(issues)} issues:")
        for issue in issues[:5]:  # Show first 5
            print(f"  [{issue['level']}] {issue['message']}")
    else:
        print("No geometry issues found!")
    
    # Export to EMJSON
    print("\nExporting to EMJSON...")
    emjson = builder.to_emjson()
    
    with open("/tmp/geometry_builder_output.emjson", "w") as f:
        json.dump(emjson, f, indent=2)
    
    print(f"Exported {len(emjson['geometry']['zones'])} zones")
    print(f"Total surfaces: {sum(len(v) for v in emjson['geometry']['surfaces'].values())}")
    print("\nEMJSON saved to /tmp/geometry_builder_output.emjson")
