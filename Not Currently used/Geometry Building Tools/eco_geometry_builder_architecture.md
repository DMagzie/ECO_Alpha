# ECO Tools - Interactive Geometry Builder
## SketchUp-Style Modeling for Building Energy Models

---

## Core Features

### 1. **Floor Plan Tracing**
- Import PNG/JPG/PDF floor plans
- Scale calibration (set known dimension)
- Trace walls over image overlay
- Lock/unlock trace layer

### 2. **Push/Pull Operations**
- Click face and drag to extrude
- Push walls up to create 3D
- Pull to create overhangs/insets
- Numerical input for exact distances

### 3. **Custom Angles**
- Not limited to 90° corners
- Angled walls for non-rectilinear plans
- Rotation gizmo for surfaces
- Snap to common angles (15°, 30°, 45°, etc.)

### 4. **Copy/Paste Zones**
- Select zone → Copy → Paste
- Array/linear pattern (multiple copies)
- Mirror operations
- Maintain all properties

### 5. **Edge/Face Manipulation**
- Select edges to move/rotate
- Select faces to edit
- Split faces
- Merge faces

---

## Technology Stack

```python
# Core 3D Engine
pyvista          # 3D visualization and mesh operations
vtk              # Under the hood (comes with PyVista)
numpy            # Math operations
shapely          # 2D geometry operations

# UI Framework
streamlit        # Web interface (already using)
streamlit-drawable-canvas  # For 2D tracing
stpyvista        # PyVista in Streamlit

# Image Processing
pillow           # Floor plan image handling
opencv-python    # Image calibration/scaling

# Geometry Processing
trimesh          # Advanced mesh operations
scipy            # Spatial operations
```

---

## Architecture

### Module Structure

```
emtools/
├── geometry_builder/
│   ├── __init__.py
│   ├── builder.py              # Main builder class
│   ├── operations.py           # Push/pull, extrude, etc.
│   ├── trace_manager.py        # Floor plan tracing
│   ├── selection.py            # Face/edge selection
│   ├── transform.py            # Move, rotate, scale, copy
│   ├── validator.py            # Geometry validation
│   └── emjson_export.py        # Export to EMJSON
│
├── geometry_builder_gui/
│   ├── __init__.py
│   ├── app.py                  # Main Streamlit app
│   ├── viewport.py             # 3D viewport widget
│   ├── toolbar.py              # Tool selection
│   ├── properties_panel.py     # Edit properties
│   └── trace_overlay.py        # Floor plan overlay
```

---

## Core Classes

### 1. GeometryBuilder

```python
class GeometryBuilder:
    """
    Main geometry building engine
    Manages the 3D model and operations
    """
    
    def __init__(self):
        self.zones = []
        self.surfaces = []
        self.trace_image = None
        self.trace_scale = None  # pixels per meter
        self.selected_entities = []
        self.history = []  # Undo/redo
        
    # Creation Operations
    def trace_polygon(self, points_2d: List[Tuple[float, float]]) -> Zone
    def extrude_polygon(self, polygon: Polygon, height: float) -> Zone
    def create_zone_from_points(self, points: List[Point]) -> Zone
    
    # Manipulation Operations
    def push_pull_face(self, face_id: str, distance: float)
    def rotate_entity(self, entity_id: str, angle_deg: float, axis: str)
    def move_edge(self, edge_id: str, delta: Vector3)
    def split_face(self, face_id: str, split_line: Line)
    
    # Copy/Paste Operations
    def copy_zone(self, zone_id: str) -> Zone
    def paste_zone(self, zone: Zone, position: Vector3) -> Zone
    def array_zone(self, zone_id: str, count: int, spacing: Vector3)
    def mirror_zone(self, zone_id: str, plane: Plane) -> Zone
    
    # Selection
    def select_face(self, face_id: str)
    def select_edge(self, edge_id: str)
    def select_zone(self, zone_id: str)
    def clear_selection()
    
    # Validation
    def validate_geometry(self) -> List[ValidationError]
    def check_intersections(self) -> List[Intersection]
    
    # Export
    def to_emjson(self) -> dict
```

### 2. TraceManager

```python
class TraceManager:
    """
    Handles floor plan image overlay and tracing
    """
    
    def __init__(self):
        self.image = None
        self.scale_factor = None  # meters per pixel
        self.origin = (0, 0)
        self.rotation = 0
        
    def load_floor_plan(self, image_path: str):
        """Load floor plan image"""
        self.image = Image.open(image_path)
    
    def calibrate_scale(self, pixel_distance: float, real_distance_m: float):
        """Set scale using known dimension"""
        self.scale_factor = real_distance_m / pixel_distance
    
    def pixel_to_world(self, pixel_coords: Tuple[int, int]) -> Tuple[float, float]:
        """Convert pixel coordinates to world coordinates (meters)"""
        x_px, y_px = pixel_coords
        x_m = (x_px - self.origin[0]) * self.scale_factor
        y_m = (y_px - self.origin[1]) * self.scale_factor
        return (x_m, y_m)
    
    def world_to_pixel(self, world_coords: Tuple[float, float]) -> Tuple[int, int]:
        """Convert world coordinates to pixel coordinates"""
        x_m, y_m = world_coords
        x_px = int(x_m / self.scale_factor + self.origin[0])
        y_px = int(y_m / self.scale_factor + self.origin[1])
        return (x_px, y_px)
```

### 3. PushPullOperation

```python
class PushPullOperation:
    """
    SketchUp-style push/pull for faces
    """
    
    @staticmethod
    def push_pull(surface: Surface, distance: float) -> Surface:
        """
        Extrude or intrude a face
        Positive distance = extrude out
        Negative distance = intrude in
        """
        # Get face normal
        normal = surface.calculate_normal()
        
        # Move vertices along normal
        new_vertices = []
        for vertex in surface.vertices:
            new_vertex = vertex + (normal * distance)
            new_vertices.append(new_vertex)
        
        # Create new surface
        new_surface = Surface(
            id=surface.id,
            vertices=new_vertices,
            type=surface.type
        )
        
        # Calculate new area
        new_surface.area = new_surface.calculate_area()
        
        return new_surface
    
    @staticmethod
    def extrude_with_sides(polygon_2d: Polygon, height: float) -> List[Surface]:
        """
        Extrude a 2D polygon to 3D, creating walls
        Returns list of surfaces (walls + top face)
        """
        surfaces = []
        vertices = polygon_2d.vertices
        
        # Create walls
        for i in range(len(vertices)):
            v1_bottom = vertices[i]
            v2_bottom = vertices[(i + 1) % len(vertices)]
            v1_top = (v1_bottom[0], v1_bottom[1], height)
            v2_top = (v2_bottom[0], v2_bottom[1], height)
            
            wall = Surface(
                id=f"wall_{i}",
                vertices=[v1_bottom, v2_bottom, v2_top, v1_top],
                type="exterior_wall"
            )
            surfaces.append(wall)
        
        # Create top face (roof/ceiling)
        top_vertices = [(v[0], v[1], height) for v in vertices]
        top = Surface(
            id="roof",
            vertices=top_vertices,
            type="roof"
        )
        surfaces.append(top)
        
        return surfaces
```

---

## User Interface Design

### Layout

```
┌─────────────────────────────────────────────────────────┐
│  ECO Tools - Geometry Builder                     [Save]│
├──────────┬──────────────────────────────────┬───────────┤
│  Tools   │                                  │Properties │
│          │                                  │           │
│ ✏️ Trace  │                                  │ Selected: │
│ 📐 Rect   │          3D Viewport            │  Wall #3  │
│ ⬡ Poly   │                                  │           │
│ ⬆️ Push   │                                  │ Type:     │
│ 🔄 Rotate │                                  │ Ext Wall  │
│ 📋 Copy   │                                  │           │
│ 📌 Paste  │                                  │ Height:   │
│ 🔍 Select │                                  │ 2.7 m     │
│          │                                  │           │
│ 🖼️ Trace  │                                  │ Area:     │
│   [Load] │                                  │ 12.5 m²   │
│          │                                  │           │
│ Floor    │                                  │ [Delete]  │
│ Plan:    │                                  │           │
│ [Show]   │                                  │           │
│          │                                  │           │
└──────────┴──────────────────────────────────┴───────────┘
```

### Workflow Steps

**Step 1: Load Floor Plan**
1. Upload image (PNG/JPG/PDF)
2. Set scale (draw line, enter known length)
3. Confirm calibration

**Step 2: Trace Outline**
1. Select "Trace" tool
2. Click points on floor plan
3. Close polygon (double-click or click first point)
4. Creates 2D zone footprint

**Step 3: Push/Pull to 3D**
1. Select traced outline
2. Click "Push/Pull" tool
3. Enter height (e.g., 2.7m for standard ceiling)
4. Walls automatically created

**Step 4: Add Features**
1. Select wall face
2. Draw window/door outline
3. Push/pull inward to create opening
4. Set properties (U-value, SHGC, etc.)

**Step 5: Duplicate Zones**
1. Select zone
2. Copy (Ctrl+C)
3. Paste (Ctrl+V)
4. Position new zone

**Step 6: Export**
1. Validate geometry
2. Export to EMJSON
3. Load in main ECO Tools workflow

---

## Key Operations in Detail

### Custom Angle Walls

```python
class AngleOperation:
    """Handle non-orthogonal walls"""
    
    @staticmethod
    def create_angled_wall(start_point: Point, angle_deg: float, length: float) -> Line:
        """
        Create wall at custom angle
        angle_deg: 0° = East, 90° = North, etc.
        """
        angle_rad = np.radians(angle_deg)
        end_point = Point(
            x=start_point.x + length * np.cos(angle_rad),
            y=start_point.y + length * np.sin(angle_rad),
            z=start_point.z
        )
        return Line(start_point, end_point)
    
    @staticmethod
    def snap_to_angle(angle_deg: float, snap_increment: float = 15.0) -> float:
        """
        Snap angle to nearest increment
        Useful for common angles: 15°, 30°, 45°, 90°
        """
        snapped = round(angle_deg / snap_increment) * snap_increment
        return snapped % 360
```

### Copy/Paste with Properties

```python
class ZoneCopyOperation:
    """Copy zones with all properties"""
    
    @staticmethod
    def copy_zone(zone: Zone) -> Zone:
        """Deep copy zone with all surfaces and properties"""
        new_zone = Zone(
            id=f"{zone.id}_copy",
            name=f"{zone.name} (Copy)",
            floor_area=zone.floor_area,
            volume=zone.volume,
            zone_type=zone.zone_type
        )
        
        # Copy all surfaces
        for surface in zone.surfaces:
            new_surface = surface.deep_copy()
            new_zone.add_surface(new_surface)
        
        # Copy thermal properties
        new_zone.hvac_template = zone.hvac_template
        new_zone.occupancy = zone.occupancy
        new_zone.lighting = zone.lighting
        
        return new_zone
    
    @staticmethod
    def array_zones(zone: Zone, count: int, spacing_x: float, spacing_y: float) -> List[Zone]:
        """
        Create array of zones (like apartment units)
        """
        zones = []
        
        for i in range(count):
            new_zone = ZoneCopyOperation.copy_zone(zone)
            new_zone.id = f"{zone.id}_array_{i}"
            
            # Translate position
            offset = Vector3(spacing_x * i, spacing_y * i, 0)
            new_zone.translate(offset)
            
            zones.append(new_zone)
        
        return zones
```

---

## Integration with EMJSON

### Export Process

```python
def export_to_emjson(builder: GeometryBuilder) -> dict:
    """
    Convert builder geometry to EMJSON v6 format
    """
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
    
    # Convert zones
    for zone in builder.zones:
        emjson_zone = {
            "id": zone.id,
            "name": zone.name,
            "floor_area_m2": zone.calculate_floor_area(),
            "volume_m3": zone.calculate_volume(),
            "zone_type": zone.zone_type,
            "multiplier": 1
        }
        emjson["geometry"]["zones"].append(emjson_zone)
    
    # Convert surfaces
    for surface in builder.surfaces:
        emjson_surface = {
            "id": surface.id,
            "zone_id": surface.zone_id,
            "type": surface.type,
            "geometry_mode": "explicit",
            "vertices_m": surface.vertices,
            "area_m2": surface.calculate_area(),
            "tilt_deg": surface.calculate_tilt(),
            "azimuth_deg": surface.calculate_azimuth(),
            "construction_id": surface.construction_id or "default"
        }
        
        # Add to appropriate category
        category = surface.get_category()  # walls, roofs, floors, etc.
        emjson["geometry"]["surfaces"][category].append(emjson_surface)
    
    return emjson
```

---

## Implementation Priority

### Phase 1: Core Functionality (Week 1-2)
- [ ] Basic PyVista 3D viewport in Streamlit
- [ ] Draw 2D polygons (click points)
- [ ] Push/pull to extrude to 3D
- [ ] Basic selection (click faces/edges)
- [ ] Export to EMJSON

### Phase 2: Floor Plan Tracing (Week 3)
- [ ] Image upload and display
- [ ] Scale calibration interface
- [ ] Trace over image overlay
- [ ] Snap to image features

### Phase 3: Advanced Operations (Week 4-5)
- [ ] Custom angle walls (rotation gizmo)
- [ ] Move/rotate/scale operations
- [ ] Copy/paste zones
- [ ] Array operations
- [ ] Mirror operations

### Phase 4: Polish (Week 6)
- [ ] Undo/redo system
- [ ] Keyboard shortcuts
- [ ] Properties panel for editing
- [ ] Geometry validation
- [ ] Measurement tools

---

## Example Usage Code

```python
from emtools.geometry_builder import GeometryBuilder, TraceManager

# Create builder
builder = GeometryBuilder()

# Load and calibrate floor plan
trace_mgr = TraceManager()
trace_mgr.load_floor_plan("house_plan.png")
trace_mgr.calibrate_scale(pixel_distance=100, real_distance_m=5.0)

# Trace building footprint
footprint_pixels = [(100, 100), (300, 100), (300, 200), (100, 200)]
footprint_meters = [trace_mgr.pixel_to_world(p) for p in footprint_pixels]

# Create zone by extruding footprint
zone = builder.create_zone_from_points(footprint_meters)
builder.push_pull_face(zone.top_face.id, 2.7)  # 2.7m ceiling height

# Add window on south wall
south_wall = zone.get_wall_by_azimuth(180)  # South-facing
window_outline = [(1, 1), (2, 1), (2, 2), (1, 2)]  # 1m x 1m
builder.create_opening(south_wall.id, window_outline, "window")

# Copy zone for identical adjacent unit
zone_copy = builder.copy_zone(zone.id)
builder.paste_zone(zone_copy, offset=(10, 0, 0))  # 10m to the east

# Validate and export
errors = builder.validate_geometry()
if not errors:
    emjson = builder.to_emjson()
    with open("model.emjson", "w") as f:
        json.dump(emjson, f, indent=2)
```

---

## Next Steps

1. **Prototype the core viewport** - Get PyVista working in Streamlit
2. **Implement basic push/pull** - Prove the concept works
3. **Add floor plan tracing** - Most critical for user workflow
4. **Build out operations library** - Copy/paste, rotate, etc.
5. **Polish UI** - Make it intuitive and fast

This system will be **geometry-only** as requested, with systems modeling handled separately through visual coding blocks.
