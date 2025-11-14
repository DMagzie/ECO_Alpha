"""
GEM Translator Module - IES VE GEM to EMJSON v6

Converts IES VE GEM files to EMJSON v6 format using Honeybee as an intermediate.
The GEM parser creates Honeybee Room objects which are then converted to EMJSON v6.
"""

from .importer import GEMParser

__all__ = ['GEMParser', 'translate_gem_to_v6']


def translate_gem_to_v6(gem_file: str):
    """
    Translate GEM file to EMJSON v6 format.

    Direct conversion: GEM -> Honeybee Rooms -> EMJSON v6

    Args:
        gem_file: Path to GEM file

    Returns:
        dict: EMJSON v6 dictionary with diagnostics
    """
    from pathlib import Path

    try:
        from .importer import GEMParser
    except ImportError as e:
        return {
            "schema_version": "6.0",
            "diagnostics": [{
                "level": "error",
                "code": "E-IMPORT-FAILED",
                "message": f"Failed to import GEM parser: {e}",
                "stage": "import",
                "source": "gem_translator"
            }]
        }

    try:
        # Parse GEM file to dictionary
        parser = GEMParser(gem_file)
        gem_data = parser.parse()

        if not gem_data or not gem_data.get('spaces'):
            return {
                "schema_version": "6.0",
                "diagnostics": [{
                    "level": "error",
                    "code": "E-GEM-PARSE",
                    "message": "Failed to parse GEM file - no spaces found. The file may be empty or corrupted.",
                    "stage": "import",
                    "source": "gem_translator"
                }]
            }

        # Convert GEM data to EMJSON v6
        emjson = _gem_dict_to_emjson_v6(gem_data, Path(gem_file).stem)

        # Add success diagnostic
        emjson["diagnostics"] = emjson.get("diagnostics", []) + [{
            "level": "info",
            "code": "I-GEM-IMPORT",
            "message": f"Imported GEM file: {len(gem_data.get('spaces', []))} spaces",
            "stage": "import",
            "source": "gem_translator"
        }]

        return emjson

    except Exception as e:
        import traceback
        return {
            "schema_version": "6.0",
            "diagnostics": [{
                "level": "error",
                "code": "E-GEM-IMPORT-FAILED",
                "message": f"GEM import failed: {str(e)}",
                "stage": "import",
                "context": traceback.format_exc(),
                "source": "gem_translator"
            }]
        }


def _calculate_polygon_area(vertices):
    """
    Calculate area of a 3D polygon using cross product method.

    Args:
        vertices: List of (x, y, z) tuples

    Returns:
        float: Area in square meters, or None if calculation fails
    """
    if not vertices or len(vertices) < 3:
        return None

    try:
        # Use cross product method for 3D polygon
        # This works for non-planar polygons too
        area = 0.0
        n = len(vertices)

        for i in range(n):
            v1 = vertices[i]
            v2 = vertices[(i + 1) % n]

            # Cross product contribution
            area += (v1[1] * v2[2] - v1[2] * v2[1])  # x component
            area += (v1[2] * v2[0] - v1[0] * v2[2])  # y component
            area += (v1[0] * v2[1] - v1[1] * v2[0])  # z component

        area = abs(area) / 2.0
        return area if area > 0 else None

    except (TypeError, IndexError, ValueError):
        return None


def _gem_dict_to_emjson_v6(gem_data: dict, project_name: str) -> dict:
    """
    Convert GEM parsed dictionary to EMJSON v6 format.

    Args:
        gem_data: Parsed GEM dictionary with 'spaces', 'constructions', etc.
        project_name: Name for the project

    Returns:
        dict: EMJSON v6 dictionary
    """
    zones = []
    surfaces = []
    openings = []

    # Convert each GEM space to EMJSON zone
    for space_idx, space in enumerate(gem_data.get('spaces', [])):
        space_name = space.get('name', f'Space_{space_idx}')
        zone_id = f"Z_{space_name.lower().replace(' ', '_').replace('/', '_')}"

        # Get space properties
        properties = space.get('properties', {})

        # Track surface IDs for this zone
        zone_surface_ids = []

        zone = {
            "id": zone_id,
            "name": space_name,
            "floor_area_m2": properties.get('floor_area'),
            "volume_m3": properties.get('volume'),
            "surfaces": zone_surface_ids  # Will be populated below
        }
        zones.append(zone)

        # Convert surfaces
        for surf_idx, surface in enumerate(space.get('surfaces', [])):
            surf_name = surface.get('name', f'{space_name}_Surface_{surf_idx}')
            surface_id = f"S_{surf_name.lower().replace(' ', '_').replace('/', '_')}"

            # Get or calculate area
            vertices = surface.get('vertices', [])
            area_m2 = surface.get('area')  # GEM might provide area directly

            # If no area provided, calculate from vertices
            if area_m2 is None and vertices:
                area_m2 = _calculate_polygon_area(vertices)

            # Map surface type for compatibility
            surf_type = surface.get('type', 'wall').lower()

            surface_obj = {
                "id": surface_id,
                "name": surf_name,
                "parent_zone_id": zone_id,
                "surface_type": surf_type,
                "type": surf_type,  # Add for compatibility
                "area_m2": area_m2,
                "area": area_m2,  # Add for render_quickstats compatibility
                "boundary": "Exterior",  # Default to exterior for GEM imports
                "construction_ref": surface.get('construction'),
                "vertices": vertices,  # Add vertices for visualization
            }
            surfaces.append(surface_obj)
            zone_surface_ids.append(surface_id)  # Track surface in zone

            # Convert windows
            for win_idx, window in enumerate(surface.get('windows', [])):
                win_name = window.get('name', f'{surf_name}_Window_{win_idx}')
                opening_id = f"O_{win_name.lower().replace(' ', '_').replace('/', '_')}"

                # Get or calculate window area
                win_area = window.get('area')
                win_vertices = window.get('vertices', [])
                if win_area is None and win_vertices:
                    win_area = _calculate_polygon_area(win_vertices)

                opening_obj = {
                    "id": opening_id,
                    "name": win_name,
                    "parent_surface_id": surface_id,
                    "opening_type": "window",
                    "area_m2": win_area,
                    "construction_ref": window.get('construction'),
                    "vertices": win_vertices,  # Add vertices for visualization
                }
                openings.append(opening_obj)

            # Convert doors
            for door_idx, door in enumerate(surface.get('doors', [])):
                door_name = door.get('name', f'{surf_name}_Door_{door_idx}')
                opening_id = f"O_{door_name.lower().replace(' ', '_').replace('/', '_')}"

                # Get or calculate door area
                door_area = door.get('area')
                door_vertices = door.get('vertices', [])
                if door_area is None and door_vertices:
                    door_area = _calculate_polygon_area(door_vertices)

                opening_obj = {
                    "id": opening_id,
                    "name": door_name,
                    "parent_surface_id": surface_id,
                    "opening_type": "door",
                    "area_m2": door_area,
                    "construction_ref": door.get('construction'),
                    "vertices": door_vertices,  # Add vertices for visualization
                }
                openings.append(opening_obj)

    # Get project info
    project_info = gem_data.get('project_info', {})

    return {
        "schema_version": "6.0",
        "project": {
            "name": project_info.get('name', project_name),
            "description": f"Imported from IES VE GEM format: {project_info.get('description', '')}",
        },
        "geometry": {
            "zones": zones,
            "surfaces": surfaces,
            "openings": openings,
        },
        "catalogs": {
            "materials": [],
            "constructions": [],  # Could add gem_data.get('constructions', [])
        },
        "systems": {
            "hvac": [],  # Could add gem_data.get('hvac', [])
        },
        "diagnostics": []
    }
