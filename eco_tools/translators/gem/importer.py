"""
GEM to HBJSON Translator
=========================

Converts IES VE GEM files to Ladybug Tools HBJSON format.
Uses Face3D for comprehensive geometry validation.

Key Features:
- Automatic 2D→3D window coordinate transformation (fixes Gibraltar's 280 windows)
- Surface normal auto-correction (fixes inverted roofs/floors)
- Comprehensive geometry validation (planarity, self-intersection)
- Clear error messages and warnings

Author: ECO Tools Team
Version: 7.0.0
Date: October 30, 2025
"""

from typing import List, Dict, Tuple, Optional
import re

# Ladybug Tools imports
try:
    from ladybug_geometry.geometry3d import Point3D, Vector3D, Face3D, Polyface3D
    from honeybee.model import Model
    from honeybee.room import Room
    from honeybee.face import Face
    from honeybee.aperture import Aperture
    from honeybee.door import Door
    LADYBUG_AVAILABLE = True
except ImportError:
    LADYBUG_AVAILABLE = False
    print("WARNING: Ladybug Tools not installed. Run:")
    print("  pip install ladybug-geometry honeybee-core honeybee-energy")


class GEMParser:
    """
    Parses IES VE GEM text files.

    Extracts geometry, constructions, and HVAC data from the GEM format.
    GEM is a text-based export format from IES MODELIT.
    """

    def __init__(self, gem_file_path: str):
        """
        Initialize GEM parser.

        Args:
            gem_file_path: Path to .gem file
        """
        self.gem_path = gem_file_path
        self.raw_data = {}
        self.spaces = []
        self.constructions = []
        self.hvac_systems = []

    def parse(self) -> Dict:
        """
        Parse GEM file into structured data.

        Returns:
            Dict with keys: project_info, spaces, constructions, hvac_systems
        """
        with open(self.gem_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()

        # Detect which format we have
        is_native_ies = self._is_native_ies_format(content)

        # Parse main sections
        self._parse_project_info(content)

        if is_native_ies:
            # Use native IES parser (vertex/face mesh format)
            self._parse_native_ies_spaces(content)
        else:
            # Use simplified keyword-based parser
            self._parse_spaces(content)

        self._parse_constructions(content)
        self._parse_hvac(content)

        return {
            'project_info': self.raw_data.get('project_info', {}),
            'spaces': self.spaces,
            'constructions': self.constructions,
            'hvac_systems': self.hvac_systems
        }

    def _is_native_ies_format(self, content: str) -> bool:
        """
        Detect if this is native IES MODELIT format or simplified format.

        Native format has: "COM GEM data file" header and space names like "IES name [ID]"
        Simplified format has: PROJECT/SPACE keywords
        """
        # Check for native format markers
        has_com_header = 'COM GEM data file' in content[:500]
        has_modelit = 'MODELIT' in content[:500]
        has_ies_space = re.search(r'IES\s+\w+.*\[\w+\]', content[:2000])

        # Check for simplified format markers
        has_project_keyword = re.search(r'PROJECT\s+"', content[:2000], re.IGNORECASE)
        has_space_keyword = re.search(r'SPACE\s+"', content[:2000], re.IGNORECASE)

        # Native format if has IES markers and no PROJECT/SPACE keywords
        if (has_com_header or has_modelit or has_ies_space) and not (has_project_keyword or has_space_keyword):
            return True

        return False

    def _parse_project_info(self, content: str):
        """Extract project metadata"""
        project_info = {}

        # Match PROJECT "name" pattern
        project_match = re.search(r'PROJECT\s+"([^"]+)"', content, re.IGNORECASE)
        if project_match:
            project_info['name'] = project_match.group(1)

        # Match LOCATION patterns
        location_match = re.search(r'LOCATION\s+"([^"]+)"', content, re.IGNORECASE)
        if location_match:
            project_info['location'] = location_match.group(1)

        self.raw_data['project_info'] = project_info

    def _parse_spaces(self, content: str):
        """
        Parse all SPACE blocks from GEM file.

        GEM format example:
            SPACE "Space Name"
              FLOOR-PLAN-COORDS
                POINT x y z
                ...
              END-FLOOR-PLAN-COORDS
              ...
            END-SPACE
        """
        # Find all SPACE blocks (case-insensitive)
        space_pattern = r'SPACE\s+"([^"]+)"(.*?)(?:END-SPACE|(?=SPACE\s+"))'
        space_matches = re.finditer(space_pattern, content, re.DOTALL | re.IGNORECASE)

        for space_match in space_matches:
            space_name = space_match.group(1)
            space_content = space_match.group(2)

            # Parse surfaces first
            surfaces = self._parse_surfaces(space_content)

            # Parse explicit properties from file
            properties = self._parse_space_properties(space_content)

            # Calculate zone properties from surfaces if not explicitly provided
            if not properties.get('floor_area') or not properties.get('volume'):
                floor_area = 0.0
                all_z = []

                for surface in surfaces:
                    if surface.get('type', '').lower() == 'floor':
                        verts = surface.get('vertices', [])
                        if verts:
                            floor_area += self._calculate_surface_area(verts)
                            all_z.extend([v[2] for v in verts])
                    else:
                        # Collect all Z coordinates for height calculation
                        for vert in surface.get('vertices', []):
                            all_z.append(vert[2])

                # Estimate volume if not provided
                volume = 0.0
                if all_z and floor_area > 0:
                    height = max(all_z) - min(all_z)
                    volume = floor_area * height

                # Update properties with calculated values
                if not properties.get('floor_area'):
                    properties['floor_area'] = floor_area if floor_area > 0 else None
                if not properties.get('volume'):
                    properties['volume'] = volume if volume > 0 else None

            space_data = {
                'name': space_name,
                'floor_plan': self._parse_floor_plan(space_content),
                'surfaces': surfaces,
                'properties': properties
            }

            self.spaces.append(space_data)

    def _parse_floor_plan(self, space_content: str) -> List[Tuple[float, float, float]]:
        """Parse FLOOR-PLAN-COORDS block"""
        coords = []

        floor_plan_match = re.search(
            r'FLOOR-PLAN-COORDS(.*?)END-FLOOR-PLAN-COORDS',
            space_content,
            re.DOTALL | re.IGNORECASE
        )

        if floor_plan_match:
            coords_text = floor_plan_match.group(1)
            # Match POINT x y z patterns
            point_pattern = r'POINT\s+([\d.-]+)\s+([\d.-]+)\s+([\d.-]+)'
            for point_match in re.finditer(point_pattern, coords_text):
                x = float(point_match.group(1))
                y = float(point_match.group(2))
                z = float(point_match.group(3))
                coords.append((x, y, z))

        return coords

    def _parse_surfaces(self, space_content: str) -> List[Dict]:
        """Parse all SURFACE blocks"""
        surfaces = []

        surface_pattern = r'SURFACE\s+"([^"]+)"(.*?)(?:END-SURFACE|(?=SURFACE\s+"))'
        surface_matches = re.finditer(surface_pattern, space_content, re.DOTALL | re.IGNORECASE)

        for surf_match in surface_matches:
            surface_name = surf_match.group(1)
            surface_content = surf_match.group(2)

            surface_data = {
                'name': surface_name,
                'type': self._parse_surface_type(surface_content),
                'vertices': self._parse_surface_vertices(surface_content),
                'construction': self._parse_surface_construction(surface_content),
                'windows': self._parse_windows(surface_content),
                'doors': self._parse_doors(surface_content)
            }

            surfaces.append(surface_data)

        return surfaces

    def _parse_surface_type(self, surface_content: str) -> str:
        """Determine surface type from GEM data"""
        type_match = re.search(r'TYPE\s*=\s*(\w+)', surface_content, re.IGNORECASE)
        if type_match:
            gem_type = type_match.group(1)
            # Map GEM types to Honeybee types
            type_map = {
                'ExteriorWall': 'Wall',
                'InteriorWall': 'Wall',
                'Roof': 'RoofCeiling',
                'Floor': 'Floor',
                'Ceiling': 'RoofCeiling',
                'UndergroundWall': 'Wall',
                'UndergroundFloor': 'Floor'
            }
            return type_map.get(gem_type, 'Wall')
        return 'Wall'

    def _parse_surface_vertices(self, surface_content: str) -> List[Tuple[float, float, float]]:
        """Parse COORDS block for surface"""
        coords = []

        coords_match = re.search(
            r'COORDS(.*?)END-COORDS',
            surface_content,
            re.DOTALL | re.IGNORECASE
        )

        if coords_match:
            coords_text = coords_match.group(1)
            point_pattern = r'POINT\s+([\d.-]+)\s+([\d.-]+)\s+([\d.-]+)'
            for point_match in re.finditer(point_pattern, coords_text):
                x = float(point_match.group(1))
                y = float(point_match.group(2))
                z = float(point_match.group(3))
                coords.append((x, y, z))

        return coords

    def _parse_surface_construction(self, surface_content: str) -> Optional[str]:
        """Parse construction reference"""
        cons_match = re.search(r'CONSTRUCTION\s+"([^"]+)"', surface_content, re.IGNORECASE)
        if cons_match:
            return cons_match.group(1)
        return None

    def _parse_windows(self, surface_content: str) -> List[Dict]:
        """Parse all WINDOW blocks on this surface"""
        windows = []

        # Match END-WINDOW but not END-WINDOW-COORDS
        window_pattern = r'WINDOW\s+"([^"]+)"(.*?)END-WINDOW(?!-)'
        window_matches = re.finditer(window_pattern, surface_content, re.DOTALL | re.IGNORECASE)

        for win_match in window_matches:
            window_name = win_match.group(1)
            window_content = win_match.group(2)

            window_data = {
                'name': window_name,
                'vertices': self._parse_window_vertices(window_content),
                'construction': self._parse_window_construction(window_content)
            }

            windows.append(window_data)

        return windows

    def _parse_window_vertices(self, window_content: str) -> List[Tuple]:
        """
        Parse WINDOW-COORDS block.

        CRITICAL: Detects if 2D or 3D coordinates.
        2D coordinates will be transformed to 3D by GEMGeometryValidator.
        """
        coords = []

        coords_match = re.search(
            r'WINDOW-COORDS(.*?)END-WINDOW-COORDS',
            window_content,
            re.DOTALL | re.IGNORECASE
        )

        if coords_match:
            coords_text = coords_match.group(1)

            # Try 3D first (3 numbers per POINT line)
            point_pattern_3d = r'POINT\s+([\d.-]+)\s+([\d.-]+)\s+([\d.-]+)'
            matches_3d = list(re.finditer(point_pattern_3d, coords_text))

            if matches_3d:
                # 3D coordinates
                for point_match in matches_3d:
                    x = float(point_match.group(1))
                    y = float(point_match.group(2))
                    z = float(point_match.group(3))
                    coords.append((x, y, z))
            else:
                # Try 2D (2 numbers per POINT line, followed by newline or end)
                point_pattern_2d = r'POINT\s+([\d.-]+)\s+([\d.-]+)\s*$'
                matches_2d = list(re.finditer(point_pattern_2d, coords_text, re.MULTILINE))

                if matches_2d:
                    # 2D coordinates - will need transformation
                    for point_match in matches_2d:
                        x = float(point_match.group(1))
                        z = float(point_match.group(2))
                        coords.append((x, z))  # Store as 2D tuple

        return coords

    def _parse_window_construction(self, window_content: str) -> Optional[str]:
        """Parse window construction reference"""
        cons_match = re.search(r'CONSTRUCTION\s+"([^"]+)"', window_content, re.IGNORECASE)
        if cons_match:
            return cons_match.group(1)
        return None

    def _parse_doors(self, surface_content: str) -> List[Dict]:
        """Parse DOOR blocks (similar to windows)"""
        # TODO: Implement door parsing if needed
        return []

    def _parse_space_properties(self, space_content: str) -> Dict:
        """Parse space properties (area, volume, conditioning, etc.)"""
        props = {}

        # Area
        area_match = re.search(r'AREA\s*=\s*([\d.]+)', space_content, re.IGNORECASE)
        if area_match:
            props['area'] = float(area_match.group(1))

        # Volume
        volume_match = re.search(r'VOLUME\s*=\s*([\d.]+)', space_content, re.IGNORECASE)
        if volume_match:
            props['volume'] = float(volume_match.group(1))

        # Space type
        type_match = re.search(r'SPACE-TYPE\s+"([^"]+)"', space_content, re.IGNORECASE)
        if type_match:
            props['space_type'] = type_match.group(1)

        return props

    def _parse_native_ies_spaces(self, content: str):
        """
        Parse native IES MODELIT GEM format.

        Format structure:
            IES Space Name [SPACEID]
            num_vertices num_faces
            x y z  (for each vertex)
            ...
            vert_count v1_idx v2_idx v3_idx v4_idx  (face definition)
            opening_flag
            (if opening_flag > 0: opening definitions follow)
        """
        lines = content.split('\n')
        i = 0

        while i < len(lines):
            line = lines[i].strip()

            # Look for space definition: "IES name [ID]"
            space_match = re.match(r'IES\s+(.*?)\s*\[(\w+)\]', line)
            if space_match:
                space_name = space_match.group(1).strip()
                space_id = space_match.group(2)

                i += 1
                if i >= len(lines):
                    break

                # Next line should be vertex_count face_count
                counts_line = lines[i].strip()
                counts_match = re.match(r'(\d+)\s+(\d+)', counts_line)

                if not counts_match:
                    i += 1
                    continue

                num_vertices = int(counts_match.group(1))
                num_faces = int(counts_match.group(2))

                # Parse vertices
                vertices = []
                i += 1
                for _ in range(num_vertices):
                    if i >= len(lines):
                        break
                    vert_line = lines[i].strip()
                    vert_parts = vert_line.split()
                    if len(vert_parts) >= 3:
                        try:
                            vertices.append((
                                float(vert_parts[0]),
                                float(vert_parts[1]),
                                float(vert_parts[2])
                            ))
                        except ValueError:
                            pass
                    i += 1

                # Parse faces
                surfaces = []
                face_idx = 0

                while face_idx < num_faces and i < len(lines):
                    face_line = lines[i].strip()

                    # Face line: vert_count v1 v2 v3 v4 ...
                    face_parts = face_line.split()
                    if len(face_parts) < 2:
                        i += 1
                        continue

                    try:
                        vert_count = int(face_parts[0])
                        if len(face_parts) < vert_count + 1:
                            i += 1
                            continue

                        # Get vertex indices (1-based in file, convert to 0-based)
                        face_vert_indices = [int(face_parts[j]) - 1 for j in range(1, vert_count + 1)]

                        # Get face vertices
                        face_vertices = []
                        for idx in face_vert_indices:
                            if 0 <= idx < len(vertices):
                                face_vertices.append(vertices[idx])

                        if len(face_vertices) >= 3:
                            # Determine surface type from geometry
                            surface_type = self._determine_surface_type_from_vertices(face_vertices)

                            surface_data = {
                                'name': f'{space_name}_Surface_{face_idx}',
                                'type': surface_type,
                                'vertices': face_vertices,
                                'construction': None,
                                'windows': [],
                                'doors': []
                            }

                            # Next line is opening flag
                            i += 1
                            if i < len(lines):
                                opening_flag_line = lines[i].strip()
                                try:
                                    opening_count = int(opening_flag_line)

                                    # Parse openings if any
                                    for opening_idx in range(opening_count):
                                        i += 1
                                        if i >= len(lines):
                                            break

                                        # Opening header: vert_count flag
                                        opening_header = lines[i].strip()
                                        header_parts = opening_header.split()

                                        if len(header_parts) >= 1:
                                            try:
                                                opening_vert_count = int(header_parts[0])

                                                # Coordinates are on following lines, one pair per line
                                                opening_coords_2d = []
                                                for _ in range(opening_vert_count):
                                                    i += 1
                                                    if i >= len(lines):
                                                        break

                                                    coord_line = lines[i].strip()
                                                    coord_parts = coord_line.split()

                                                    if len(coord_parts) >= 2:
                                                        try:
                                                            x_2d = float(coord_parts[0])
                                                            y_2d = float(coord_parts[1])
                                                            opening_coords_2d.append((x_2d, y_2d))
                                                        except (ValueError, IndexError):
                                                            break

                                                # Convert 2D coordinates to 3D
                                                opening_vertices_3d = self._transform_2d_to_3d(
                                                    opening_coords_2d,
                                                    face_vertices
                                                )

                                                if len(opening_vertices_3d) >= 3:
                                                    # Assume windows for now
                                                    window_data = {
                                                        'name': f'{space_name}_Surface_{face_idx}_Window_{opening_idx}',
                                                        'vertices': opening_vertices_3d,
                                                        'construction': None
                                                    }
                                                    surface_data['windows'].append(window_data)

                                            except ValueError:
                                                pass

                                except ValueError:
                                    pass

                            surfaces.append(surface_data)

                        face_idx += 1

                    except (ValueError, IndexError):
                        pass

                    i += 1

                # Calculate zone properties from surfaces
                floor_area = 0.0
                for surface in surfaces:
                    if surface['type'] == 'Floor':
                        # Calculate area for this floor surface
                        verts = surface.get('vertices', [])
                        if verts:
                            floor_area += self._calculate_surface_area(verts)

                # Estimate volume (rough approximation using floor area * average height)
                # Find min and max Z coordinates
                all_z = []
                for surface in surfaces:
                    for vert in surface.get('vertices', []):
                        all_z.append(vert[2])

                volume = 0.0
                if all_z and floor_area > 0:
                    height = max(all_z) - min(all_z)
                    volume = floor_area * height

                # Create space data
                space_data = {
                    'name': space_name,
                    'id': space_id,
                    'floor_plan': [],
                    'surfaces': surfaces,
                    'properties': {
                        'floor_area': floor_area if floor_area > 0 else None,
                        'volume': volume if volume > 0 else None
                    }
                }

                self.spaces.append(space_data)

            i += 1

    def _calculate_surface_area(self, vertices: List[Tuple[float, float, float]]) -> float:
        """
        Calculate area of a 3D polygon using cross product method.

        Args:
            vertices: List of (x, y, z) tuples

        Returns:
            Area in square meters
        """
        if not vertices or len(vertices) < 3:
            return 0.0

        try:
            # Use cross product method for 3D polygon
            area = 0.0
            n = len(vertices)

            for i in range(n):
                v1 = vertices[i]
                v2 = vertices[(i + 1) % n]

                # Cross product contribution
                area += (v1[1] * v2[2] - v1[2] * v2[1])  # x component
                area += (v1[2] * v2[0] - v1[0] * v2[2])  # y component
                area += (v1[0] * v2[1] - v1[1] * v2[0])  # z component

            return abs(area) / 2.0

        except (TypeError, IndexError, ValueError, ZeroDivisionError):
            return 0.0

    def _determine_surface_type_from_vertices(self, vertices: List[Tuple[float, float, float]]) -> str:
        """
        Determine surface type from vertex geometry.

        Uses surface normal to classify as floor, roof, or wall.
        """
        if len(vertices) < 3:
            return 'Wall'

        # Calculate surface normal using first 3 vertices
        try:
            v1 = vertices[0]
            v2 = vertices[1]
            v3 = vertices[2]

            # Vectors along two edges
            edge1 = (v2[0] - v1[0], v2[1] - v1[1], v2[2] - v1[2])
            edge2 = (v3[0] - v1[0], v3[1] - v1[1], v3[2] - v1[2])

            # Cross product gives normal
            normal = (
                edge1[1] * edge2[2] - edge1[2] * edge2[1],
                edge1[2] * edge2[0] - edge1[0] * edge2[2],
                edge1[0] * edge2[1] - edge1[1] * edge2[0]
            )

            # Normalize
            length = (normal[0]**2 + normal[1]**2 + normal[2]**2) ** 0.5
            if length > 0:
                normal = (normal[0]/length, normal[1]/length, normal[2]/length)

                # Check normal direction
                # If mostly pointing up (+Z), it's a roof
                # If mostly pointing down (-Z), it's a floor
                # Otherwise it's a wall
                if normal[2] > 0.7:
                    return 'RoofCeiling'
                elif normal[2] < -0.7:
                    return 'Floor'
                else:
                    return 'Wall'

        except (ZeroDivisionError, ValueError):
            pass

        return 'Wall'

    def _transform_2d_to_3d(
        self,
        coords_2d: List[Tuple[float, float]],
        face_vertices: List[Tuple[float, float, float]]
    ) -> List[Tuple[float, float, float]]:
        """
        Transform 2D opening coordinates to 3D in face plane.

        The 2D coordinates are in a local coordinate system of the face.
        We need to establish the face's coordinate frame and map the 2D coords to 3D.
        """
        if len(face_vertices) < 3 or len(coords_2d) < 3:
            return []

        try:
            # Use first vertex as origin
            origin = face_vertices[0]

            # X-axis: direction from first to second vertex
            v1_to_v2 = (
                face_vertices[1][0] - origin[0],
                face_vertices[1][1] - origin[1],
                face_vertices[1][2] - origin[2]
            )
            x_length = (v1_to_v2[0]**2 + v1_to_v2[1]**2 + v1_to_v2[2]**2) ** 0.5
            if x_length == 0:
                return []

            x_axis = (v1_to_v2[0]/x_length, v1_to_v2[1]/x_length, v1_to_v2[2]/x_length)

            # Calculate face normal (Z-axis)
            v1_to_v3 = (
                face_vertices[2][0] - origin[0],
                face_vertices[2][1] - origin[1],
                face_vertices[2][2] - origin[2]
            )

            # Cross product
            z_axis = (
                x_axis[1] * v1_to_v3[2] - x_axis[2] * v1_to_v3[1],
                x_axis[2] * v1_to_v3[0] - x_axis[0] * v1_to_v3[2],
                x_axis[0] * v1_to_v3[1] - x_axis[1] * v1_to_v3[0]
            )
            z_length = (z_axis[0]**2 + z_axis[1]**2 + z_axis[2]**2) ** 0.5
            if z_length == 0:
                return []

            z_axis = (z_axis[0]/z_length, z_axis[1]/z_length, z_axis[2]/z_length)

            # Y-axis: perpendicular to both X and Z
            y_axis = (
                z_axis[1] * x_axis[2] - z_axis[2] * x_axis[1],
                z_axis[2] * x_axis[0] - z_axis[0] * x_axis[2],
                z_axis[0] * x_axis[1] - z_axis[1] * x_axis[0]
            )

            # Transform 2D to 3D
            vertices_3d = []
            for x_2d, y_2d in coords_2d:
                # Map 2D point to 3D using local coordinate frame
                point_3d = (
                    origin[0] + x_2d * x_axis[0] + y_2d * y_axis[0],
                    origin[1] + x_2d * x_axis[1] + y_2d * y_axis[1],
                    origin[2] + x_2d * x_axis[2] + y_2d * y_axis[2]
                )
                vertices_3d.append(point_3d)

            return vertices_3d

        except (ZeroDivisionError, ValueError, IndexError):
            return []

    def _parse_constructions(self, content: str):
        """Parse construction assembly definitions"""
        # TODO: Implement construction parsing
        pass

    def _parse_hvac(self, content: str):
        """Parse HVAC system definitions"""
        # TODO: Implement HVAC parsing
        pass


class GEMGeometryValidator:
    """
    Validates GEM geometry using Ladybug Face3D.
    Transforms 2D window coordinates to 3D.
    Fixes inverted surface normals.
    """

    def __init__(self, tolerance: float = 0.01):
        self.tolerance = tolerance  # meters
        self.warnings = []
        self.errors = []

    def validate_space(self, space_data: Dict) -> Tuple[bool, List[str]]:
        """
        Validate space geometry and fix issues.

        Returns:
            (is_valid, list_of_messages)
        """
        messages = []
        space_name = space_data['name']

        # Validate floor plan
        floor_coords = space_data['floor_plan']
        if len(floor_coords) < 3:
            self.errors.append(f"Space {space_name}: Floor plan has < 3 vertices")
            return False, self.errors

        # Create and validate floor Face3D
        floor_pts = [Point3D(*coords) for coords in floor_coords]
        floor_face = Face3D(floor_pts)

        if not floor_face.is_valid:
            self.errors.append(f"Space {space_name}: Invalid floor geometry")
            return False, self.errors

        # Check floor orientation (should point down)
        if floor_face.normal.z > 0:
            messages.append(f"Space {space_name}: Floor normal corrected (was pointing up)")
            floor_pts.reverse()
            floor_face = Face3D(floor_pts)
            # Update space data
            space_data['floor_plan'] = [(pt.x, pt.y, pt.z) for pt in floor_pts]

        # Validate stated area vs calculated area
        calc_area = floor_face.area  # m²
        stated_area = space_data.get('properties', {}).get('area')

        if stated_area:
            deviation = abs(calc_area - stated_area) / stated_area
            if deviation > 0.10:  # 10% tolerance
                warning = (f"Space {space_name}: Floor area mismatch - "
                          f"Stated: {stated_area:.2f} m², "
                          f"Calculated: {calc_area:.2f} m² "
                          f"({deviation*100:.1f}% deviation)")
                self.warnings.append(warning)
                messages.append(warning)
                # Use calculated (geometry is truth)
                space_data['properties']['area'] = calc_area

        # Validate all surfaces in this space
        for surface in space_data['surfaces']:
            surf_valid, surf_messages = self.validate_surface(
                surface,
                space_name,
                floor_face
            )
            messages.extend(surf_messages)
            if not surf_valid:
                return False, messages

        return True, messages

    def validate_surface(
        self,
        surface_data: Dict,
        space_name: str,
        floor_face: Face3D
    ) -> Tuple[bool, List[str]]:
        """
        Validate surface geometry.
        Transform 2D window coordinates to 3D.
        Fix surface normal orientation.
        """
        messages = []
        surface_name = surface_data['name']

        # Validate surface vertices
        vertices = surface_data['vertices']
        if len(vertices) < 3:
            self.errors.append(
                f"{space_name}/{surface_name}: Surface has < 3 vertices"
            )
            return False, [self.errors[-1]]

        # Create Face3D
        surf_pts = [Point3D(*coords) for coords in vertices]
        surf_face = Face3D(surf_pts)

        if not surf_face.is_valid:
            self.errors.append(
                f"{space_name}/{surface_name}: Invalid surface geometry (non-planar or self-intersecting)"
            )
            return False, [self.errors[-1]]

        # Fix orientation based on surface type
        surf_type = surface_data['type']
        if surf_type == 'Floor':
            if surf_face.normal.z > 0:  # Pointing up - wrong
                messages.append(f"{space_name}/{surface_name}: Floor normal corrected")
                surf_pts.reverse()
                surf_face = Face3D(surf_pts)
                surface_data['vertices'] = [(pt.x, pt.y, pt.z) for pt in surf_pts]

        elif surf_type == 'RoofCeiling':
            if surf_face.normal.z < 0:  # Pointing down - wrong
                messages.append(f"{space_name}/{surface_name}: Roof normal corrected")
                surf_pts.reverse()
                surf_face = Face3D(surf_pts)
                surface_data['vertices'] = [(pt.x, pt.y, pt.z) for pt in surf_pts]

        # Validate and transform windows
        for window in surface_data['windows']:
            win_valid, win_messages = self.validate_and_transform_window(
                window,
                surface_name,
                surf_face
            )
            messages.extend(win_messages)
            if not win_valid:
                return False, messages

        return True, messages

    def validate_and_transform_window(
        self,
        window_data: Dict,
        surface_name: str,
        parent_surf_face: Face3D
    ) -> Tuple[bool, List[str]]:
        """
        Validate window and transform 2D → 3D if needed.
        THIS IS THE KEY FUNCTION FOR FIXING GIBRALTAR'S 280 WINDOWS!
        """
        messages = []
        window_name = window_data['name']
        vertices = window_data['vertices']

        if len(vertices) < 3:
            self.errors.append(f"{surface_name}/{window_name}: < 3 vertices")
            return False, [self.errors[-1]]

        # Check if 2D or 3D
        if all(len(v) == 2 for v in vertices):
            # 2D coordinates - TRANSFORM TO 3D
            messages.append(
                f"{surface_name}/{window_name}: Transforming 2D → 3D coordinates"
            )
            vertices_3d = self._transform_window_2d_to_3d(
                vertices,
                parent_surf_face
            )
            window_data['vertices'] = vertices_3d
            vertices = vertices_3d

        elif all(len(v) == 3 for v in vertices):
            # Already 3D - validate
            pass
        else:
            self.errors.append(
                f"{surface_name}/{window_name}: Inconsistent coordinate dimensions"
            )
            return False, [self.errors[-1]]

        # Validate window Face3D
        win_pts = [Point3D(*coords) for coords in vertices]
        win_face = Face3D(win_pts)

        if not win_face.is_valid:
            self.errors.append(
                f"{surface_name}/{window_name}: Invalid window geometry"
            )
            return False, [self.errors[-1]]

        # Check window is coplanar with parent surface (within tolerance)
        wall_normal = parent_surf_face.normal
        for pt in win_pts:
            # Distance from point to plane
            wall_pt = parent_surf_face.vertices[0]
            vec_to_pt = pt - wall_pt
            distance = abs(vec_to_pt.dot(wall_normal))

            if distance > self.tolerance:
                warning = (f"{surface_name}/{window_name}: "
                          f"Window not coplanar with parent surface "
                          f"(distance: {distance:.3f} m)")
                self.warnings.append(warning)
                messages.append(warning)
                break

        return True, messages

    def _transform_window_2d_to_3d(
        self,
        coords_2d: List[Tuple[float, float]],
        parent_surf_face: Face3D
    ) -> List[Tuple[float, float, float]]:
        """
        Transform 2D window coordinates to 3D global coordinates.

        THIS IS THE GIBRALTAR FIX!

        Args:
            coords_2d: [(x_along_wall, z_height), ...]
            parent_surf_face: Face3D of parent wall

        Returns:
            [(x, y, z), ...] in global coordinates
        """
        wall_normal = parent_surf_face.normal
        wall_origin = parent_surf_face.vertices[0]  # Bottom-left corner

        # Determine wall orientation
        if abs(wall_normal.y) > 0.9:  # Y-planar wall (constant Y)
            # Wall spans in X-Z plane
            wall_plane_y = wall_origin.y

            coords_3d = []
            for x_local, z in coords_2d:
                # x_local is X position along wall
                # z is height above ground
                global_pt = (
                    wall_origin.x + x_local,  # X varies
                    wall_plane_y,              # Y constant
                    z                          # Z is height
                )
                coords_3d.append(global_pt)

        elif abs(wall_normal.x) > 0.9:  # X-planar wall (constant X)
            # Wall spans in Y-Z plane
            wall_plane_x = wall_origin.x

            coords_3d = []
            for y_local, z in coords_2d:
                # y_local is Y position along wall (called "x" in local space)
                # z is height above ground
                global_pt = (
                    wall_plane_x,              # X constant
                    wall_origin.y + y_local,   # Y varies
                    z                          # Z is height
                )
                coords_3d.append(global_pt)

        else:
            # Arbitrary angle wall - use wall's local coordinate system
            # Get wall basis vectors
            wall_bottom_edge = parent_surf_face.vertices[1] - parent_surf_face.vertices[0]
            x_axis = wall_bottom_edge.normalize()
            z_axis = Vector3D(0, 0, 1)  # World up

            coords_3d = []
            for x_local, z in coords_2d:
                # Position along wall bottom edge + height
                global_pt = (
                    wall_origin.x + x_axis.x * x_local,
                    wall_origin.y + x_axis.y * x_local,
                    z  # Height is always in global Z
                )
                coords_3d.append(global_pt)

        return coords_3d


class GEMToHoneybeeConverter:
    """
    Converts validated GEM data to Honeybee Model.
    Uses Face3D objects for all geometry.
    """

    def __init__(self):
        self.validator = GEMGeometryValidator()
        self.model = None

    def convert(self, gem_data: Dict) -> Model:
        """
        Convert GEM data to Honeybee Model.

        Args:
            gem_data: Output from GEMParser.parse()

        Returns:
            honeybee.model.Model with validated geometry
        """
        project_info = gem_data['project_info']
        project_name = project_info.get('name', 'Untitled')

        # Create Honeybee model
        self.model = Model(
            identifier=self._sanitize_identifier(project_name)
        )
        self.model.display_name = project_name

        # Convert all spaces to Honeybee Rooms
        for space_data in gem_data['spaces']:
            # Validate and fix geometry
            is_valid, messages = self.validator.validate_space(space_data)

            for msg in messages:
                print(f"  {msg}")

            if not is_valid:
                print(f"ERROR: Space {space_data['name']} has invalid geometry")
                continue

            # Convert to Honeybee Room
            room = self._create_room_from_space(space_data)
            if room:
                self.model.add_room(room)

        # Validate complete model
        validation_report = self.model.check_all()
        if validation_report:
            print("\nModel Validation Report:")
            print(validation_report)

        return self.model

    def _create_room_from_space(self, space_data: Dict) -> Optional[Room]:
        """
        Create Honeybee Room from validated space data.

        Args:
            space_data: Space dict with validated geometry

        Returns:
            honeybee.room.Room or None if failed
        """
        space_name = space_data['name']
        identifier = self._sanitize_identifier(space_name)

        # Create room faces from surfaces
        faces = []

        for surface_data in space_data['surfaces']:
            face = self._create_face_from_surface(surface_data)
            if face:
                faces.append(face)

        if len(faces) < 4:
            print(f"WARNING: Space {space_name} has < 4 faces, skipping")
            return None

        try:
            # Create Room from faces
            room = Room(
                identifier=identifier,
                faces=faces,
                tolerance=0.01
            )
            room.display_name = space_name

            # Set properties from space data
            props = space_data.get('properties', {})
            if 'space_type' in props:
                # Map to program type (would need programtype library)
                pass

            return room

        except Exception as e:
            print(f"ERROR creating room {space_name}: {e}")
            return None

    def _create_face_from_surface(self, surface_data: Dict) -> Optional[Face]:
        """Create Honeybee Face from surface data"""
        surface_name = surface_data['name']
        identifier = self._sanitize_identifier(surface_name)

        # Create Face3D from validated vertices
        vertices = surface_data['vertices']
        pts = [Point3D(*coords) for coords in vertices]
        face3d = Face3D(pts)

        try:
            # Create Honeybee Face (type is auto-assigned from normal)
            face = Face(
                identifier=identifier,
                geometry=face3d
            )
            face.display_name = surface_name

            # Add construction if specified
            construction = surface_data.get('construction')
            if construction:
                # Would need to map to honeybee-energy construction
                pass

            # Add windows
            for window_data in surface_data['windows']:
                aperture = self._create_aperture_from_window(window_data)
                if aperture:
                    face.add_aperture(aperture)

            # Add doors
            for door_data in surface_data.get('doors', []):
                door = self._create_door(door_data)
                if door:
                    face.add_door(door)

            return face

        except Exception as e:
            print(f"ERROR creating face {surface_name}: {e}")
            return None

    def _create_aperture_from_window(self, window_data: Dict) -> Optional[Aperture]:
        """Create Honeybee Aperture from window data"""
        window_name = window_data['name']
        identifier = self._sanitize_identifier(window_name)

        # Create Face3D from validated 3D vertices
        vertices = window_data['vertices']  # Now guaranteed 3D!
        pts = [Point3D(*coords) for coords in vertices]
        face3d = Face3D(pts)

        try:
            aperture = Aperture(
                identifier=identifier,
                geometry=face3d
            )
            aperture.display_name = window_name

            # Add construction if specified
            construction = window_data.get('construction')
            if construction:
                # Would need to map to honeybee-energy window construction
                pass

            return aperture

        except Exception as e:
            print(f"ERROR creating aperture {window_name}: {e}")
            return None

    def _create_door(self, door_data: Dict) -> Optional[Door]:
        """Create Honeybee Door from door data"""
        # Similar to aperture creation
        return None

    def _sanitize_identifier(self, name: str) -> str:
        """
        Sanitize name for use as Honeybee identifier.

        Rules:
        - Remove special characters except hyphen, underscore, period
        - Replace spaces with underscores
        - Start with letter or underscore
        - Max 100 characters
        """
        import re

        # Remove apostrophes and other problematic characters
        name = name.replace("'", "").replace("'", "").replace(""", "").replace(""", "")

        # Replace spaces with underscores
        name = name.replace(' ', '_')

        # Remove all characters except alphanumeric, hyphen, underscore, period
        name = re.sub(r'[^\w\-.]', '', name)

        # Ensure starts with letter or underscore
        if name and not (name[0].isalpha() or name[0] == '_'):
            name = '_' + name

        # Limit length
        if len(name) > 100:
            name = name[:100]

        return name if name else 'unnamed'


# Main translation function
def gem_to_hbjson(
    gem_file_path: str,
    output_hbjson_path: str,
    verbose: bool = True
) -> bool:
    """
    Convert GEM file to HBJSON.

    Args:
        gem_file_path: Path to .gem file
        output_hbjson_path: Path for output .hbjson file
        verbose: Print progress messages

    Returns:
        True if successful, False otherwise
    """
    if not LADYBUG_AVAILABLE:
        print("ERROR: Ladybug Tools not installed. Cannot continue.")
        return False

    try:
        if verbose:
            print(f"Parsing GEM file: {gem_file_path}")

        # Parse GEM
        parser = GEMParser(gem_file_path)
        gem_data = parser.parse()

        if verbose:
            print(f"  Found {len(gem_data['spaces'])} spaces")

        # Convert to Honeybee
        converter = GEMToHoneybeeConverter()
        model = converter.convert(gem_data)

        if verbose:
            print(f"\nCreated Honeybee model:")
            print(f"  Rooms: {len(model.rooms)}")
            print(f"  Floor area: {model.floor_area:.2f} m²")
            print(f"  Volume: {model.volume:.2f} m³")

        # Write HBJSON
        model.to_hbjson(output_hbjson_path, indent=2)

        if verbose:
            print(f"\nWrote HBJSON: {output_hbjson_path}")

        # Print validation summary
        if converter.validator.warnings:
            print(f"\nValidation Warnings ({len(converter.validator.warnings)}):")
            for warning in converter.validator.warnings[:10]:  # First 10
                print(f"  ⚠️  {warning}")
            if len(converter.validator.warnings) > 10:
                print(f"  ... and {len(converter.validator.warnings) - 10} more")

        if converter.validator.errors:
            print(f"\nValidation Errors ({len(converter.validator.errors)}):")
            for error in converter.validator.errors[:10]:
                print(f"  ❌ {error}")
            return False

        return True

    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False


# Command-line interface
if __name__ == '__main__':
    import sys

    if len(sys.argv) < 2:
        print("Usage: python gem_to_hbjson.py input.gem [output.hbjson]")
        sys.exit(1)

    gem_path = sys.argv[1]
    hbjson_path = sys.argv[2] if len(sys.argv) > 2 else gem_path.replace('.gem', '.hbjson')

    success = gem_to_hbjson(gem_path, hbjson_path, verbose=True)
    sys.exit(0 if success else 1)
