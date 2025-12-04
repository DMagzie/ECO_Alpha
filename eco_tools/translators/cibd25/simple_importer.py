"""
Simplified CIBD25 Importer - Focuses on Essential Elements

Converts CIBD25 text files to EMJSON v6 with focus on geometry elements
needed for model comparison.
"""

from typing import Dict, Any, List
from .text_reader import parse_cibd25_text


def convert_cibd25_to_emjson(file_path: str) -> Dict[str, Any]:
    """
    Convert CIBD25 text file to EMJSON v6.

    Args:
        file_path: Path to CIBD25 file

    Returns:
        EMJSON v6 dictionary

    Example:
        >>> emjson = convert_cibd25_to_emjson("model.cibd25")
        >>> print(f"Zones: {len(emjson['geometry']['zones'])}")
    """
    # Parse the text file
    reader = parse_cibd25_text(file_path)

    # Initialize EMJSON structure
    emjson = {
        "schema_version": "6.0",
        "project": _extract_project(reader),
        "geometry": _extract_geometry(reader),
        "catalogs": _extract_catalogs(reader),
        "systems": _extract_systems(reader),
        "diagnostics": []
    }

    return emjson


def _extract_project(reader) -> Dict[str, Any]:
    """Extract project metadata."""
    proj_objs = reader.find_objects("Proj")

    project = {
        "name": "Unknown Project",
        "description": "",
        "location": {}
    }

    if proj_objs:
        proj = proj_objs[0]
        project["name"] = proj.get("_name", "Unknown Project")

        props = proj.get("_properties", {})
        if props.get("City"):
            project["location"]["city"] = props["City"]
        if props.get("ZipCode"):
            project["location"]["zip_code"] = str(props["ZipCode"])

    return project


def _extract_geometry(reader) -> Dict[str, Any]:
    """Extract geometry elements (zones, surfaces, openings)."""
    zones = _extract_zones(reader)
    surfaces = _extract_surfaces(reader)

    # Nest surfaces into their parent zones
    _nest_surfaces_into_zones(zones, surfaces)

    geometry = {
        "zones": zones,
        "zone_groups": _extract_zone_groups(reader),
        "surfaces": surfaces,
        "openings": _extract_openings(reader)
    }

    return geometry


def _extract_zones(reader) -> List[Dict[str, Any]]:
    """Extract zones."""
    zones = []

    res_zones = reader.find_objects("ResZn")
    com_zones = reader.find_objects("ComZn")

    for zone_obj in res_zones + com_zones:
        props = zone_obj.get("_properties", {})

        zone = {
            "id": zone_obj.get("_name"),
            "name": zone_obj.get("_name"),
            "type": props.get("Type", "unknown"),
            "floor_area_m2": _convert_area(props.get("FloorArea")),
            "volume_m3": None,  # Not typically in CIBD25 text
            "surfaces": []  # Will be populated by surface-zone linking
        }

        zones.append(zone)

    return zones


def _extract_zone_groups(reader) -> List[Dict[str, Any]]:
    """Extract zone groups."""
    groups = []

    res_groups = reader.find_objects("ResZnGrp")

    for grp_obj in res_groups:
        props = grp_obj.get("_properties", {})

        group = {
            "id": grp_obj.get("_name"),
            "name": grp_obj.get("_name"),
            "floor_to_floor_height_m": _convert_length(props.get("FlrToFlrHgt")),
            "floor_to_ceiling_height_m": _convert_length(props.get("FlrToCeilingHgt")),
            "z_m": _convert_length(props.get("Z", 0))
        }

        groups.append(group)

    return groups


def _extract_surfaces(reader) -> List[Dict[str, Any]]:
    """Extract surfaces."""
    surfaces = []

    # Get all surface types
    surface_types = [
        "ResExtWall", "ResIntWall", "ResIntFlr", "ResSlabFlr",
        "ResCathedralCeiling", "ResAtticRoof"
    ]

    for surf_type in surface_types:
        surf_objs = reader.find_objects(surf_type)

        for surf_obj in surf_objs:
            props = surf_obj.get("_properties", {})

            surface = {
                "id": surf_obj.get("_name"),
                "name": surf_obj.get("_name"),
                "type": _map_surface_type(surf_type),
                "area_m2": _convert_area(props.get("Area")),
                "construction_ref": props.get("Construction"),
                "orientation": props.get("Orientation"),
                "zone_ref": _extract_zone_from_name(surf_obj.get("_name"))
            }

            surfaces.append(surface)

    return surfaces


def _extract_openings(reader) -> List[Dict[str, Any]]:
    """Extract openings (windows, doors)."""
    openings = []

    opening_types = ["ResWin", "ResDr"]

    for open_type in opening_types:
        open_objs = reader.find_objects(open_type)

        for open_obj in open_objs:
            props = open_obj.get("_properties", {})

            opening = {
                "id": open_obj.get("_name"),
                "name": open_obj.get("_name"),
                "type": "window" if open_type == "ResWin" else "door",
                "area_m2": _convert_area(props.get("Area")),
                "window_type_ref": props.get("WinType"),
                "spec_method": props.get("SpecMethod")
            }

            openings.append(opening)

    return openings


def _extract_catalogs(reader) -> Dict[str, Any]:
    """Extract catalog elements."""
    catalogs = {
        "window_types": _extract_window_types(reader),
        "materials": _extract_materials(reader),
        "constructions": _extract_constructions(reader),
        "du_types": _extract_du_types(reader)
    }

    return catalogs


def _extract_window_types(reader) -> List[Dict[str, Any]]:
    """Extract window type catalog."""
    window_types = []

    wt_objs = reader.find_objects("ResWinType")

    for wt_obj in wt_objs:
        props = wt_obj.get("_properties", {})

        wt = {
            "id": wt_obj.get("_name"),
            "name": wt_obj.get("_name"),
            "area_m2": _convert_area(props.get("Area")),
            "u_factor_ip": props.get("NFRCUfactor"),
            "shgc": props.get("NFRCSHGC"),
            "spec_method": props.get("SpecMethod")
        }

        window_types.append(wt)

    return window_types


def _extract_materials(reader) -> List[Dict[str, Any]]:
    """Extract material catalog."""
    materials = []

    mat_objs = reader.find_objects("Mat")

    for mat_obj in mat_objs:
        props = mat_obj.get("_properties", {})

        mat = {
            "id": mat_obj.get("_name"),
            "name": mat_obj.get("_name"),
            "code_category": props.get("CodeCat"),
            "code_item": props.get("CodeItem")
        }

        materials.append(mat)

    return materials


def _extract_constructions(reader) -> List[Dict[str, Any]]:
    """Extract construction assemblies."""
    constructions = []

    cons_objs = reader.find_objects("ConsAssm")

    for cons_obj in cons_objs:
        props = cons_obj.get("_properties", {})

        # MatRef can be a list
        mat_refs = props.get("MatRef", [])
        if not isinstance(mat_refs, list):
            mat_refs = [mat_refs]

        cons = {
            "id": cons_obj.get("_name"),
            "name": cons_obj.get("_name"),
            "compatible_surface_type": props.get("CompatibleSurfType"),
            "material_refs": mat_refs
        }

        constructions.append(cons)

    return constructions


def _extract_du_types(reader) -> List[Dict[str, Any]]:
    """Extract dwelling unit types."""
    du_types = []

    du_objs = reader.find_objects("DwellUnitType")

    for du_obj in du_objs:
        props = du_obj.get("_properties", {})

        du = {
            "id": du_obj.get("_name"),
            "name": du_obj.get("_name"),
            "floor_area_m2": _convert_area(props.get("CondFlrArea")),
            "bedrooms": props.get("NumBedrooms")
        }

        du_types.append(du)

    return du_types


def _extract_systems(reader) -> Dict[str, Any]:
    """Extract system elements (minimal for now)."""
    systems = {
        "hvac": [],
        "dhw": [],
        "pv": []
    }

    return systems


def _convert_area(area_ft2) -> float:
    """Convert area from ft² to m²."""
    if area_ft2 is None:
        return 0.0
    return float(area_ft2) * 0.092903


def _convert_length(length_ft) -> float:
    """Convert length from ft to m."""
    if length_ft is None:
        return 0.0
    return float(length_ft) * 0.3048


def _map_surface_type(cibd_type: str) -> str:
    """Map CIBD surface type to generic type."""
    mapping = {
        "ResExtWall": "exterior_wall",
        "ResIntWall": "interior_wall",
        "ResIntFlr": "interior_floor",
        "ResSlabFlr": "slab_floor",
        "ResCathedralCeiling": "cathedral_ceiling",
        "ResAtticRoof": "attic_roof"
    }
    return mapping.get(cibd_type, "unknown")


def _extract_zone_from_name(surface_name: str) -> str:
    """Extract zone reference from surface name (heuristic)."""
    # Surfaces often named like "ExtWall (Front 1) : B3-R_122"
    # where B3-R_122 is the zone name
    if ":" in surface_name:
        parts = surface_name.split(":")
        if len(parts) >= 2:
            return parts[-1].strip()
    return None


def _nest_surfaces_into_zones(zones: List[Dict[str, Any]], surfaces: List[Dict[str, Any]]) -> None:
    """
    Nest surfaces into their parent zones based on zone_ref.

    This modifies the zones in-place, adding surfaces to each zone's surfaces array.

    Args:
        zones: List of zone dictionaries with 'id' and 'surfaces' fields
        surfaces: List of surface dictionaries with 'zone_ref' field
    """
    # Create zone lookup by ID for fast access
    zone_by_id = {z["id"]: z for z in zones}

    # Iterate through surfaces and add to their parent zone
    for surface in surfaces:
        zone_ref = surface.get("zone_ref")

        if zone_ref and zone_ref in zone_by_id:
            # Add surface to its parent zone
            zone_by_id[zone_ref]["surfaces"].append(surface)
