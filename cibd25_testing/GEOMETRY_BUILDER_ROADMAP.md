# Geometry Builder Roadmap - Full-Featured 3D Modeling Tool

## Vision

Transform the Geometry Builder into a **SketchUp-style 3D modeling tool** integrated into the Explorer GUI, capable of:
- Creating and editing building geometry for CBECC models
- Handling large models (50+ zones like Bressi Ranch)
- Providing intuitive push-pull, face division, and vertex editing
- Seamless integration with CIBD22X/CIBD25 workflow

---

## Current State

### ✅ What Works Now

1. **Basic Geometry Creation**
   - Create rectangular zones programmatically
   - Automatic surface generation (walls, floor, roof)
   - Zone positioning in 3D space
   - EMJSON export with full geometry

2. **3D Visualization**
   - Interactive viewing (rotate, zoom, pan via Plotly)
   - Color-coded surfaces by type
   - Hover tooltips with surface info
   - Lazy loading for performance
   - Export to HTML

3. **Integration**
   - Translation to CIBD22X/CIBD25
   - Internal Representation mapping
   - GUI integration (Active Model tab)

### ⚠️ Current Limitations

1. **Scale:** Designed for 1-10 zones max
2. **Interactivity:** Read-only visualization (no editing)
3. **Interface:** Programmatic API only (no GUI tools)
4. **Editing:** No push-pull, face division, or vertex editing
5. **Performance:** Not optimized for large models (50+ zones)

---

## Phased Implementation Plan

### **Phase 1: Enhanced 3D Controls** (2-3 weeks)
**Goal:** Add interactive selection and basic editing

#### 1.1 Interactive Controls
- [x] Zoom, pan, orbit (already working via Plotly)
- [ ] Click-to-select zones
- [ ] Click-to-select faces
- [ ] Highlight selected elements
- [ ] Selection state management

#### 1.2 Zone Selection
**Requirements:**
- Click on any surface → select parent zone
- Highlight all zone surfaces
- Show zone properties in sidebar
- Multi-select with Ctrl/Cmd

**Technical Approach:**
```python
# Add click event handler to Plotly figure
fig.update_traces(
    hoverinfo='text',
    customdata=zone_ids,
    clickmode='event+select'
)

# Handle click events via Streamlit
selected_zones = st.plotly_events(fig, click_event=True)
```

#### 1.3 Face Selection
**Requirements:**
- Click on specific face → select that surface
- Show surface properties (area, type, orientation)
- Highlight selected face with different color
- Display normal vector

**Technical Approach:**
```python
# Track clicked face
clicked_face = st.session_state.get('selected_face', None)

# Color selected face differently
if face.id == clicked_face:
    color = 'rgba(255, 200, 0, 0.9)'  # Highlight color
else:
    color = SURFACE_COLORS[face.type]
```

---

### **Phase 2: Push-Pull Editing** (3-4 weeks)
**Goal:** Add SketchUp-style push-pull for faces

#### 2.1 Face Push-Pull
**Requirements:**
- Select face → enter push-pull mode
- Drag face perpendicular to surface
- Type distance value for precision
- Live preview during drag
- Update adjacent faces automatically

**Technical Approach:**
```python
class PushPullOperation:
    def __init__(self, surface: Surface, distance: float):
        self.surface = surface
        self.distance = distance
        self.original_vertices = surface.vertices.copy()

    def execute(self):
        """Move surface vertices along normal vector"""
        normal = self.surface.calculate_normal()

        for vertex in self.surface.vertices:
            vertex.x += normal[0] * self.distance
            vertex.y += normal[1] * self.distance
            vertex.z += normal[2] * self.distance

        # Update adjacent faces
        self._update_adjacent_faces()

    def _update_adjacent_faces(self):
        """Stretch adjacent wall faces to match new vertices"""
        # Find faces sharing edges with pushed face
        # Update their vertices to maintain continuity
        pass
```

**UI Components:**
- Slider for push-pull distance (-5m to +5m)
- Number input for precise values
- Preview mode (show ghost outline)
- Confirm/Cancel buttons

#### 2.2 Vertex Push-Pull
**Requirements:**
- Select individual vertex
- Drag in any direction (not just normal)
- Constrain to axis (X, Y, or Z only)
- Update all adjacent faces

**Technical Approach:**
```python
class VertexDragOperation:
    def __init__(self, vertex: Point3D, new_position: Point3D):
        self.vertex = vertex
        self.new_position = new_position
        self.affected_faces = []

    def execute(self):
        """Move vertex and update all faces using it"""
        # Find all surfaces using this vertex
        for surface in self.affected_faces:
            # Update vertex reference
            for i, v in enumerate(surface.vertices):
                if v is self.vertex:
                    surface.vertices[i] = self.new_position

        # Recalculate face normals
        for surface in self.affected_faces:
            surface.recalculate_normal()
```

---

### **Phase 3: Face Division & Advanced Editing** (3-4 weeks)
**Goal:** Split faces and create windows/doors

#### 3.1 Face Division
**Requirements:**
- Split face into 2+ faces
- Draw division line interactively
- Maintain planarity
- Update zone topology

**Use Cases:**
- Split wall for different materials
- Create horizontal band for windows
- Divide roof into sections

**Technical Approach:**
```python
class FaceDivisionOperation:
    def __init__(self, surface: Surface, division_line: List[Point3D]):
        self.surface = surface
        self.division_line = division_line

    def execute(self):
        """Split face along division line"""
        # Project division line onto surface plane
        projected_line = self._project_to_plane(self.division_line)

        # Find intersection points with face edges
        intersections = self._find_intersections(projected_line)

        # Create two new faces from split
        face1, face2 = self._split_polygon(self.surface.vertices, intersections)

        return [face1, face2]

    def _project_to_plane(self, line):
        """Project 3D line onto surface plane"""
        pass

    def _split_polygon(self, vertices, split_line):
        """Split polygon into two sub-polygons"""
        pass
```

**UI Components:**
- Draw mode: click two points to define split line
- Grid mode: split into equal sections (e.g., 3x3 grid)
- Preview of resulting faces

#### 3.2 Window/Door Creation
**Requirements:**
- Select face → draw rectangle for opening
- Specify dimensions (width × height)
- Automatic frame creation
- Opening becomes child surface

**Technical Approach:**
```python
class WindowCreationOperation:
    def __init__(self, parent_wall: Surface, bounds: Rectangle):
        self.parent_wall = parent_wall
        self.bounds = bounds

    def execute(self):
        """Create window opening in wall"""
        # Create window surface
        window = self._create_window_surface()

        # Subtract window from parent wall
        self.parent_wall.add_opening(window)

        # Update wall geometry (create frame around window)
        self._create_wall_frame()

        return window

    def _create_window_surface(self):
        """Generate window surface geometry"""
        # Calculate vertices on wall plane
        # Create Surface object with type='window'
        pass

    def _create_wall_frame(self):
        """Split parent wall into frame sections"""
        # Create 4 wall sections around window
        # (top, bottom, left, right)
        pass
```

---

### **Phase 4: Large Model Optimization** (2-3 weeks)
**Goal:** Handle 50+ zones efficiently (e.g., Bressi Ranch)

#### 4.1 Performance Optimizations

**4.1.1 Level of Detail (LOD)**
```python
class LODManager:
    """Manage level of detail based on zoom level"""

    def get_lod_for_zoom(self, zoom_level: float) -> int:
        """
        LOD 0 (far):  Simple boxes, no surface detail
        LOD 1 (mid):  Full surfaces, simplified windows
        LOD 2 (near): Full detail with all openings
        """
        if zoom_level < 0.5:
            return 0  # Far view
        elif zoom_level < 2.0:
            return 1  # Mid view
        else:
            return 2  # Close view

    def simplify_geometry(self, zones: List[Zone], lod: int):
        """Reduce geometry complexity based on LOD"""
        if lod == 0:
            # Show only zone bounding boxes
            return [self._create_bounding_box(z) for z in zones]
        elif lod == 1:
            # Show surfaces but omit small details
            return [self._simplify_zone(z) for z in zones]
        else:
            # Full detail
            return zones
```

**4.1.2 Spatial Indexing**
```python
class SpatialIndex:
    """Octree-based spatial index for fast lookups"""

    def __init__(self, bounds: BoundingBox, max_depth: int = 8):
        self.root = OctreeNode(bounds, max_depth)

    def insert(self, zone: Zone):
        """Insert zone into octree"""
        self.root.insert(zone, zone.get_bounding_box())

    def query_visible(self, camera_frustum: Frustum) -> List[Zone]:
        """Get only zones visible to camera (frustum culling)"""
        return self.root.query(camera_frustum)
```

**4.1.3 Incremental Rendering**
```python
class IncrementalRenderer:
    """Render geometry in chunks to avoid blocking UI"""

    def render_async(self, zones: List[Zone], chunk_size: int = 10):
        """Render zones in batches"""
        for i in range(0, len(zones), chunk_size):
            chunk = zones[i:i + chunk_size]
            yield self._render_chunk(chunk)

            # Let UI update between chunks
            time.sleep(0.01)
```

#### 4.2 Memory Optimization

**4.2.1 Geometry Instancing**
```python
class GeometryInstanceManager:
    """Reuse geometry for repeated elements"""

    def __init__(self):
        self.instances = {}  # type -> base geometry

    def get_or_create(self, zone_type: str):
        """Get shared geometry for zone type"""
        if zone_type not in self.instances:
            self.instances[zone_type] = self._create_base_geometry(zone_type)

        return self.instances[zone_type]
```

**4.2.2 Progressive Loading**
```python
class ProgressiveLoader:
    """Load geometry progressively as needed"""

    def load_visible_zones(self, viewport: Viewport):
        """Only load zones in current view"""
        visible_zone_ids = self._get_visible_zone_ids(viewport)

        for zone_id in visible_zone_ids:
            if not self._is_loaded(zone_id):
                yield self._load_zone(zone_id)
```

#### 4.3 Benchmarks for Bressi Ranch

**Target Performance:**
- Initial load: < 2 seconds
- Zoom/pan response: < 100 ms
- Selection response: < 50 ms
- Push-pull preview: < 200 ms

**Bressi Ranch Stats:**
- Zones: ~50
- Surfaces: ~300
- Vertices: ~1200
- Expected file size: ~2 MB EMJSON

---

### **Phase 5: Dedicated Geometry Builder Tab** (2 weeks)
**Goal:** Create standalone modeling interface

#### 5.1 Tab Structure

```
┌─────────────────────────────────────────────────────────────┐
│                   GEOMETRY BUILDER TAB                      │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────────────┐  ┌──────────────────────────────────┐ │
│  │   TOOLS         │  │                                  │ │
│  │                 │  │                                  │ │
│  │ □ Select        │  │                                  │ │
│  │ □ Zone          │  │       3D VIEWPORT                │ │
│  │ □ Push-Pull     │  │                                  │ │
│  │ □ Divide        │  │    (Interactive 3D View)         │ │
│  │ □ Window/Door   │  │                                  │ │
│  │ □ Vertex Edit   │  │                                  │ │
│  │                 │  │                                  │ │
│  ├─────────────────┤  └──────────────────────────────────┘ │
│  │   PROPERTIES    │                                       │
│  │                 │  ┌──────────────────────────────────┐ │
│  │ Selected: Wall  │  │          PROPERTIES              │ │
│  │ Area: 24.5 m²   │  │                                  │ │
│  │ Type: Exterior  │  │  Selected Element: Exterior Wall │ │
│  │ Azimuth: 180°   │  │  ID: wall_north_1                │ │
│  │                 │  │  Area: 24.5 m²                   │ │
│  │ [Edit]          │  │  Height: 3.0 m                   │ │
│  │                 │  │  Construction: Default           │ │
│  └─────────────────┘  └──────────────────────────────────┘ │
│                                                             │
│  [Undo] [Redo]  [Save]  [Export to CIBD25]                │
└─────────────────────────────────────────────────────────────┘
```

#### 5.2 Tool Palette

**Selection Tool** (Default)
- Click to select zones/faces
- Shift+Click for multi-select
- Box select by dragging

**Zone Creation Tool**
- Draw rectangle on ground plane
- Enter height
- Zone created automatically

**Push-Pull Tool**
- Click face to activate
- Drag to push/pull
- Type distance for precision

**Divide Tool**
- Click face to divide
- Draw division line
- Face splits into multiple faces

**Window/Door Tool**
- Click face to add opening
- Draw rectangle for size
- Window/door created

**Vertex Edit Tool**
- Click vertex to select
- Drag to move
- Constrain to axis (X/Y/Z keys)

#### 5.3 Property Panel

**Zone Properties:**
- Name
- Building type
- Multiplier
- Floor area (calculated)
- Volume (calculated)

**Surface Properties:**
- Name
- Type (wall, roof, floor, etc.)
- Construction assignment
- Area (calculated)
- Tilt (calculated)
- Azimuth (calculated)
- Parent zone

**Vertex Properties:**
- X, Y, Z coordinates
- Snap to grid option
- Connected faces count

---

### **Phase 6: Undo/Redo & State Management** (1-2 weeks)
**Goal:** Enable undo/redo for all operations

#### 6.1 Command Pattern

```python
from abc import ABC, abstractmethod
from typing import List

class Command(ABC):
    """Base class for all commands"""

    @abstractmethod
    def execute(self):
        """Execute the command"""
        pass

    @abstractmethod
    def undo(self):
        """Undo the command"""
        pass

    @abstractmethod
    def redo(self):
        """Redo the command"""
        pass


class CommandHistory:
    """Manage undo/redo stack"""

    def __init__(self, max_size: int = 100):
        self.commands: List[Command] = []
        self.current_index: int = -1
        self.max_size = max_size

    def execute(self, command: Command):
        """Execute command and add to history"""
        # Remove any commands after current index (if we're in middle of stack)
        self.commands = self.commands[:self.current_index + 1]

        # Execute command
        command.execute()

        # Add to stack
        self.commands.append(command)
        self.current_index += 1

        # Limit stack size
        if len(self.commands) > self.max_size:
            self.commands.pop(0)
            self.current_index -= 1

    def undo(self):
        """Undo last command"""
        if self.can_undo():
            self.commands[self.current_index].undo()
            self.current_index -= 1

    def redo(self):
        """Redo next command"""
        if self.can_redo():
            self.current_index += 1
            self.commands[self.current_index].redo()

    def can_undo(self) -> bool:
        return self.current_index >= 0

    def can_redo(self) -> bool:
        return self.current_index < len(self.commands) - 1
```

#### 6.2 Command Examples

```python
class PushPullCommand(Command):
    """Command for push-pull operation"""

    def __init__(self, surface: Surface, distance: float):
        self.surface = surface
        self.distance = distance
        self.original_vertices = [v.copy() for v in surface.vertices]
        self.new_vertices = None

    def execute(self):
        # Perform push-pull
        normal = self.surface.calculate_normal()
        for vertex in self.surface.vertices:
            vertex.x += normal[0] * self.distance
            vertex.y += normal[1] * self.distance
            vertex.z += normal[2] * self.distance

        self.new_vertices = [v.copy() for v in self.surface.vertices]

    def undo(self):
        # Restore original vertices
        self.surface.vertices = [v.copy() for v in self.original_vertices]

    def redo(self):
        # Restore pushed vertices
        self.surface.vertices = [v.copy() for v in self.new_vertices]


class FaceDivisionCommand(Command):
    """Command for face division"""

    def __init__(self, parent_face: Surface, division_line: List[Point3D]):
        self.parent_face = parent_face
        self.division_line = division_line
        self.child_faces = None
        self.zone = None

    def execute(self):
        # Perform division
        self.zone = self.parent_face.zone
        self.child_faces = self._split_face()

        # Remove parent, add children
        self.zone.surfaces.remove(self.parent_face)
        self.zone.surfaces.extend(self.child_faces)

    def undo(self):
        # Remove children, restore parent
        for face in self.child_faces:
            self.zone.surfaces.remove(face)
        self.zone.surfaces.append(self.parent_face)

    def redo(self):
        # Re-execute
        self.zone.surfaces.remove(self.parent_face)
        self.zone.surfaces.extend(self.child_faces)
```

#### 6.3 Session State Management

```python
class GeometryBuilderSession:
    """Manage geometry builder session state"""

    def __init__(self):
        self.builder = GeometryBuilder()
        self.command_history = CommandHistory()
        self.selected_elements = []
        self.active_tool = "select"
        self.clipboard = []

    def execute_command(self, command: Command):
        """Execute command with undo support"""
        self.command_history.execute(command)
        self.notify_observers()  # Update UI

    def undo(self):
        self.command_history.undo()
        self.notify_observers()

    def redo(self):
        self.command_history.redo()
        self.notify_observers()

    def save_state(self) -> dict:
        """Save session to JSON"""
        return {
            'geometry': EMJSONAdapter.to_emjson(self.builder),
            'command_history_size': len(self.command_history.commands),
            'selected_elements': [e.id for e in self.selected_elements]
        }

    def load_state(self, state: dict):
        """Restore session from JSON"""
        # Restore geometry
        emjson = state['geometry']
        self.builder = self._emjson_to_builder(emjson)
```

---

### **Phase 7: Integration & Testing** (2 weeks)
**Goal:** Test with real models and integrate fully

#### 7.1 Test with Bressi Ranch

**Test Plan:**
1. Import Bressi Ranch CIBD22X
2. Convert to geometry builder format
3. Verify all 50+ zones load correctly
4. Test performance benchmarks
5. Make sample edits (push-pull, divide)
6. Export back to CIBD25
7. Validate roundtrip fidelity

#### 7.2 Integration Tests

**Test Cases:**
- Create geometry → EMJSON → CIBD22X → Parse back → Verify
- Edit geometry → Save → Reload → Verify edits preserved
- Large model → Lazy load → Select zone → Edit → Verify performance
- Undo/redo → Verify all operations reversible
- Window creation → Export to CIBD25 → Verify openings correct

---

## Technology Stack

### Core Technologies

**3D Visualization:**
- **Plotly** - Interactive 3D graphics (current)
- **Three.js** (future) - More advanced 3D capabilities
- **React-Three-Fiber** (future) - React wrapper for Three.js

**UI Framework:**
- **Streamlit** (current) - Quick prototyping
- **React** (future) - More responsive, better for complex interactions

**State Management:**
- **Session State** (current) - Simple state management
- **Redux** (future) - Complex state management for undo/redo

**Performance:**
- **Numpy** - Fast vector math
- **Numba** (future) - JIT compilation for performance
- **WebGL** (future) - GPU-accelerated rendering

---

## Development Priorities

### Short Term (Next 1-2 months)

1. **Zone Selection** - Enable click-to-select
2. **Face Selection** - Enable face-level selection
3. **Basic Push-Pull** - Simple face extrusion
4. **Property Display** - Show selected element info

### Medium Term (3-6 months)

1. **Advanced Push-Pull** - With preview and constraints
2. **Face Division** - Split faces interactively
3. **Window Creation** - Add openings to walls
4. **Undo/Redo** - Full command history

### Long Term (6-12 months)

1. **Large Model Support** - Optimize for 50+ zones
2. **LOD System** - Level of detail for performance
3. **Dedicated Tab** - Full modeling interface
4. **Advanced Features** - Arrays, components, etc.

---

## Risk Mitigation

### Technical Risks

**Risk 1: Plotly Limitations**
- **Mitigation:** Research Three.js integration early
- **Fallback:** Implement core features in Plotly, migrate to Three.js later

**Risk 2: Performance with Large Models**
- **Mitigation:** Implement LOD and spatial indexing from start
- **Fallback:** Limit to smaller models initially, optimize later

**Risk 3: Streamlit Limitations for Complex Interactions**
- **Mitigation:** Use Streamlit components or custom JS
- **Fallback:** Build separate React app for geometry builder

### UX Risks

**Risk 1: Learning Curve Too Steep**
- **Mitigation:** Add tutorial, tooltips, and defaults
- **Fallback:** Simplify tools, focus on most common operations

**Risk 2: Performance Feels Slow**
- **Mitigation:** Aggressive optimization, lazy loading
- **Fallback:** Progressive enhancement - basic features fast, advanced features slower but acceptable

---

## Success Metrics

### Performance Metrics

- Initial load time: < 2 seconds (50 zones)
- Selection response: < 50 ms
- Push-pull preview: < 200 ms
- Zoom/pan: 60 fps

### Usability Metrics

- User can create simple building: < 5 minutes
- User can edit existing model: < 2 minutes
- Undo/redo works reliably: 100% of time

### Quality Metrics

- Roundtrip fidelity: 100%
- Geometry validation: All outputs valid
- No crashes with valid input: 99.9%

---

## Next Steps

1. **Research Phase (This Week)**
   - Investigate Plotly click events
   - Test selection with current viewer
   - Prototype zone highlighting

2. **Phase 1 Start (Next Week)**
   - Implement zone selection
   - Add selection state to session
   - Create property panel UI

3. **Stakeholder Review (2 Weeks)**
   - Demo zone selection
   - Get feedback on UI/UX
   - Adjust plan based on feedback

---

**This roadmap transforms the Geometry Builder from a simple creation tool into a full-featured SketchUp-style editor integrated into the CBECC workflow.**
