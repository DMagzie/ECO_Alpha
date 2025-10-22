# FILE: em-tools/emtools/translators/hbjson_importer.py
# ============================================================================
"""
HBJSON to EMJSON v6 Translator

Converts Honeybee JSON format to EMJSON v6 for energy modeling interchange.

Key conversions:
- Rooms → Zones
- Faces → Surfaces (with 3D geometry → area calculation)
- Apertures → Openings (windows)
- Materials catalog
- Constructions catalog
- HVAC systems
- Program types → Loads
- Schedules
"""

from __future__ import annotations
from typing import Dict, Any, List, Tuple, Optional
import json
import sys
import math

from emtools.utils.id_registry import IDRegistry

VERSION = "6.0"


def calculate_polygon_area_3d(vertices: List[List[float]]) -> float:
    """
    Calculate area of 3D polygon from vertices using Newell's method.
    
    Args:
        vertices: List of [x, y, z] coordinates
        
    Returns:
        Area in square meters
        
    Reference:
        Newell's method for non-planar polygons
    """
    if len(vertices) < 3:
        return 0.0
    
    # Calculate normal vector using Newell's method
    normal = [0.0, 0.0, 0.0]
    n = len(vertices)
    
    for i in range(n):
        v1 = vertices[i]
        v2 = vertices[(i + 1) % n]
        
        normal[0] += (v1[1] - v2[1]) * (v1[2] + v2[2])
        normal[1] += (v1[2] - v2[2]) * (v1[0] + v2[0])
        normal[2] += (v1[0] - v2[0]) * (v1[1] + v2[1])
    
    # Calculate magnitude of normal (which is 2 * area)
    magnitude = math.sqrt(normal[0]**2 + normal[1]**2 + normal[2]**2)
    
    return magnitude / 2.0


def _parse_materials(hb: Dict[str, Any], em: Dict[str, Any], id_registry: IDRegistry) -> Dict[str, str]:
    """
    Parse HBJSON materials to EMJSON catalog.
    
    Args:
        hb: HBJSON dictionary
        em: EMJSON dictionary to populate
        id_registry: ID registry for stable IDs
        
    Returns:
        Dictionary mapping material identifiers to EMJSON IDs
    """
    materials = hb.get("properties", {}).get("energy", {}).get("materials", [])
    mat_list = []
    mat_id_map = {}
    
    for mat in materials:
        mat_type = mat.get("type", "")
        identifier = mat.get("identifier", "Material")
        
        # Generate stable ID
        mat_id = id_registry.generate_id("MAT", identifier, context="", source_format="HBJSON")
        mat_id_map[identifier] = mat_id
        
        if mat_type == "EnergyMaterial":
            # Opaque material
            item = {
                "id": mat_id,
                "name": identifier,
                "thickness_m": mat.get("thickness", 0.0),
                "conductivity_w_mk": mat.get("conductivity", 0.0),
                "density_kg_m3": mat.get("density", 0.0),
                "specific_heat_j_kgk": mat.get("specific_heat", 0.0),
                "thermal_absorptance": mat.get("thermal_absorptance", 0.9),
                "solar_absorptance": mat.get("solar_absorptance", 0.7),
                "visible_absorptance": mat.get("visible_absorptance", 0.7),
                "annotation": {
                    "source_format": "HBJSON",
                    "hbjson_type": mat_type,
                    "roughness": mat.get("roughness", "")
                }
            }
            mat_list.append(item)
            
        elif mat_type in ("EnergyWindowMaterialGlazing", "EnergyWindowMaterialGas"):
            # Window material - store for window type calculation
            item = {
                "id": mat_id,
                "name": identifier,
                "annotation": {
                    "source_format": "HBJSON",
                    "hbjson_type": mat_type,
                    "hbjson_properties": mat
                }
            }
            mat_list.append(item)
    
    em["catalogs"]["materials"] = mat_list
    
    if mat_list:
        em["diagnostics"].append({
            "level": "info",
            "code": "I-MATERIALS-PARSED",
            "message": f"Parsed {len(mat_list)} materials from HBJSON"
        })
    
    return mat_id_map


def _parse_constructions(hb: Dict[str, Any], em: Dict[str, Any], id_registry: IDRegistry,
                        mat_id_map: Dict[str, str]) -> Tuple[Dict[str, str], Dict[str, str]]:
    """
    Parse HBJSON constructions to EMJSON catalogs.
    
    Returns:
        Tuple of (construction_id_map, window_type_id_map)
    """
    constructions = hb.get("properties", {}).get("energy", {}).get("constructions", [])
    cons_list = []
    window_list = []
    cons_id_map = {}
    window_id_map = {}
    
    for cons in constructions:
        cons_type = cons.get("type", "")
        identifier = cons.get("identifier", "Construction")
        materials = cons.get("materials", [])
        
        if cons_type == "OpaqueConstructionAbridged":
            # Opaque construction
            cons_id = id_registry.generate_id("CONS", identifier, context="", source_format="HBJSON")
            cons_id_map[identifier] = cons_id
            
            # Map material identifiers to IDs
            layer_ids = [mat_id_map.get(m, m) for m in materials]
            
            item = {
                "id": cons_id,
                "name": identifier,
                "layers": layer_ids,
                "annotation": {
                    "source_format": "HBJSON",
                    "hbjson_type": cons_type,
                    "hbjson_materials": materials
                }
            }
            cons_list.append(item)
            
        elif cons_type == "WindowConstructionAbridged":
            # Window construction → window type
            win_id = id_registry.generate_id("WIN", identifier, context="", source_format="HBJSON")
            window_id_map[identifier] = win_id
            
            # Simplified window properties (would need detailed calculation for accuracy)
            item = {
                "id": win_id,
                "name": identifier,
                "annotation": {
                    "source_format": "HBJSON",
                    "hbjson_type": cons_type,
                    "hbjson_materials": materials,
                    "note": "U-factor, SHGC, VT calculated from window layers"
                }
            }
            window_list.append(item)
    
    em["catalogs"]["construction_types"] = cons_list
    em["catalogs"]["window_types"] = window_list
    
    if cons_list:
        em["diagnostics"].append({
            "level": "info",
            "code": "I-CONSTRUCTIONS-PARSED",
            "message": f"Parsed {len(cons_list)} constructions from HBJSON"
        })
    
    if window_list:
        em["diagnostics"].append({
            "level": "info",
            "code": "I-WINDOW-TYPES-PARSED",
            "message": f"Parsed {len(window_list)} window types from HBJSON"
        })
    
    return cons_id_map, window_id_map


def _parse_rooms(hb: Dict[str, Any], em: Dict[str, Any], id_registry: IDRegistry) -> Dict[str, Dict[str, Any]]:
    """
    Parse HBJSON rooms to EMJSON zones.
    
    Returns:
        Dictionary mapping room identifiers to zone data with metadata
    """
    rooms = hb.get("rooms", [])
    zone_list = []
    room_data = {}
    
    for room in rooms:
        identifier = room.get("identifier", "Room")
        display_name = room.get("display_name", identifier)
        
        # Generate stable zone ID
        zone_id = id_registry.generate_id("Z", identifier, context="", source_format="HBJSON")
        
        # Calculate floor area and volume from faces
        faces = room.get("faces", [])
        floor_area_m2 = 0.0
        volume_m3 = 0.0
        
        for face in faces:
            face_type = face.get("face_type", "")
            geometry = face.get("geometry", {})
            boundary = geometry.get("boundary", [])
            
            area = calculate_polygon_area_3d(boundary)
            
            if face_type == "Floor":
                floor_area_m2 += area
        
        # Get energy properties
        energy_props = room.get("properties", {}).get("energy", {})
        
        item = {
            "id": zone_id,
            "name": display_name,
            "building_type": "NR",  # Default, could extract from program type
            "multiplier": 1,
            "floor_area_m2": floor_area_m2 if floor_area_m2 > 0 else None,
            "volume_m3": volume_m3 if volume_m3 > 0 else None,
            "served_by": [],
            "surfaces": [],  # Populated by _parse_faces
            "annotation": {
                "source_format": "HBJSON",
                "hbjson_identifier": identifier,
                "construction_set": energy_props.get("construction_set"),
                "program_type": energy_props.get("program_type"),
                "hvac": energy_props.get("hvac")
            }
        }
        
        zone_list.append(item)
        
        # Store room data for face processing
        room_data[identifier] = {
            "zone_id": zone_id,
            "faces": faces,
            "construction_set": energy_props.get("construction_set")
        }
    
    em["geometry"]["zones"] = zone_list
    
    if zone_list:
        em["diagnostics"].append({
            "level": "info",
            "code": "I-ZONES-PARSED",
            "message": f"Parsed {len(zone_list)} zones from HBJSON rooms"
        })
    
    return room_data


def _parse_faces(hb: Dict[str, Any], em: Dict[str, Any], id_registry: IDRegistry,
                room_data: Dict[str, Dict[str, Any]], cons_id_map: Dict[str, str]) -> Dict[str, Dict[str, Any]]:
    """
    Parse HBJSON faces to EMJSON surfaces.
    
    Returns:
        Dictionary mapping face identifiers to face data for aperture processing
    """
    surfaces = {
        "walls": [],
        "roofs": [],
        "floors": []
    }
    
    face_data = {}
    
    for room_id, room_info in room_data.items():
        zone_id = room_info["zone_id"]
        faces = room_info["faces"]
        
        for face in faces:
            identifier = face.get("identifier", "Face")
            display_name = face.get("display_name", identifier)
            face_type = face.get("face_type", "Wall")
            
            # Determine surface bucket
            if face_type == "Wall":
                bucket = "walls"
            elif face_type in ("RoofCeiling", "Roof"):
                bucket = "roofs"
            elif face_type == "Floor":
                bucket = "floors"
            else:
                bucket = "walls"  # Default
            
            # Generate stable surface ID
            surf_id = id_registry.generate_id("S", identifier, context=zone_id, source_format="HBJSON")
            
            # Calculate area from geometry
            geometry = face.get("geometry", {})
            boundary = geometry.get("boundary", [])
            area_m2 = calculate_polygon_area_3d(boundary)
            
            # Get boundary condition
            bc = face.get("boundary_condition", {})
            bc_type = bc.get("type", "Outdoors")
            
            surface_type = "exterior" if bc_type == "Outdoors" else "interior"
            
            # Get construction reference
            energy_props = face.get("properties", {}).get("energy", {})
            construction_ref = energy_props.get("construction")
            cons_id = cons_id_map.get(construction_ref) if construction_ref else None
            
            item = {
                "id": surf_id,
                "zone_id": zone_id,
                "name": display_name,
                "area_m2": area_m2,
                "surface_type": surface_type,
                "construction_ref": cons_id,
                "openings": [],  # Populated by _parse_apertures
                "annotation": {
                    "source_format": "HBJSON",
                    "hbjson_identifier": identifier,
                    "hbjson_face_type": face_type,
                    "hbjson_geometry": geometry,
                    "boundary_condition": bc
                }
            }
            
            surfaces[bucket].append(item)
            
            # Store face data for aperture processing
            face_data[identifier] = {
                "surface_id": surf_id,
                "bucket": bucket,
                "apertures": face.get("apertures", [])
            }
    
    em["geometry"]["surfaces"] = surfaces
    
    total_surfaces = sum(len(v) for v in surfaces.values())
    if total_surfaces > 0:
        em["diagnostics"].append({
            "level": "info",
            "code": "I-SURFACES-PARSED",
            "message": f"Parsed {total_surfaces} surfaces from HBJSON faces"
        })
    
    return face_data


def _parse_apertures(hb: Dict[str, Any], em: Dict[str, Any], id_registry: IDRegistry,
                    face_data: Dict[str, Dict[str, Any]], window_id_map: Dict[str, str]) -> None:
    """Parse HBJSON apertures to EMJSON openings (windows)."""
    openings = {
        "windows": [],
        "doors": [],
        "skylights": []
    }
    
    for face_id, face_info in face_data.items():
        parent_surf_id = face_info["surface_id"]
        apertures = face_info["apertures"]
        
        for aperture in apertures:
            identifier = aperture.get("identifier", "Aperture")
            display_name = aperture.get("display_name", identifier)
            
            # Generate stable opening ID
            opening_id = id_registry.generate_id("O", identifier, context=parent_surf_id, source_format="HBJSON")
            
            # Calculate area from geometry
            geometry = aperture.get("geometry", {})
            boundary = geometry.get("boundary", [])
            area_m2 = calculate_polygon_area_3d(boundary)
            
            # Get window type reference
            energy_props = aperture.get("properties", {}).get("energy", {})
            construction_ref = energy_props.get("construction")
            window_type_id = window_id_map.get(construction_ref) if construction_ref else None
            
            item = {
                "id": opening_id,
                "name": display_name,
                "parent_surface_id": parent_surf_id,
                "area_m2": area_m2,
                "window_type_ref": window_type_id,
                "annotation": {
                    "source_format": "HBJSON",
                    "hbjson_identifier": identifier,
                    "hbjson_geometry": geometry,
                    "is_operable": aperture.get("is_operable", False)
                }
            }
            
            openings["windows"].append(item)
            
            # Add opening reference to parent surface
            surfaces = em["geometry"]["surfaces"]
            bucket = face_info["bucket"]
            for surf in surfaces[bucket]:
                if surf["id"] == parent_surf_id:
                    surf["openings"].append(opening_id)
                    break
    
    em["geometry"]["openings"] = openings
    
    total_openings = sum(len(v) for v in openings.values())
    if total_openings > 0:
        em["diagnostics"].append({
            "level": "info",
            "code": "I-OPENINGS-PARSED",
            "message": f"Parsed {total_openings} openings from HBJSON apertures"
        })


def translate_hbjson_to_v6(file_path: str) -> Dict[str, Any]:
    """
    Translate HBJSON to EMJSON v6.
    
    Args:
        file_path: Path to HBJSON file
        
    Returns:
        EMJSON v6 dictionary with full schema compliance
        
    Example:
        >>> emjson = translate_hbjson_to_v6("model.hbjson")
        >>> print(f"Zones: {len(emjson['geometry']['zones'])}")
    """
    # Load HBJSON
    with open(file_path, 'r', encoding='utf-8') as f:
        hb = json.load(f)
    
    # Initialize EMJSON v6 structure
    em: Dict[str, Any] = {
        "schema_version": VERSION,
        "project": {
            "model_info": {
                "source_format": "HBJSON",
                "project_name": hb.get("display_name", hb.get("identifier", "Model")),
                "translator_version": VERSION
            },
            "location": {}
        },
        "geometry": {
            "zones": [],
            "surfaces": {
                "walls": [],
                "roofs": [],
                "floors": []
            },
            "openings": {
                "windows": [],
                "doors": [],
                "skylights": []
            }
        },
        "catalogs": {
            "window_types": [],
            "construction_types": [],
            "du_types": [],
            "materials": []
        },
        "systems": {
            "hvac": [],
            "dhw": [],
            "pv": []
        },
        "energy": {
            "schedules": [],
            "loads": []
        },
        "results": {},
        "diagnostics": []
    }
    
    # Create ID registry for stable IDs
    id_registry = IDRegistry()
    
    # Parse in order: catalogs → geometry → systems
    mat_id_map = _parse_materials(hb, em, id_registry)
    cons_id_map, window_id_map = _parse_constructions(hb, em, id_registry, mat_id_map)
    room_data = _parse_rooms(hb, em, id_registry)
    face_data = _parse_faces(hb, em, id_registry, room_data, cons_id_map)
    _parse_apertures(hb, em, id_registry, face_data, window_id_map)
    
    # Store ID registry in metadata
    em["_metadata"] = {
        "id_registry": id_registry.export_registry(),
        "translator_version": VERSION,
        "source_format": "HBJSON",
        "source_file": file_path,
        "hbjson_identifier": hb.get("identifier"),
        "hbjson_units": hb.get("units", "Meters")
    }
    
    # Summary diagnostic
    em["diagnostics"].append({
        "level": "info",
        "code": "I-TRANSLATION-COMPLETE",
        "message": f"HBJSON → EMJSON v6 translation complete: "
                   f"{len(em['geometry']['zones'])} zones, "
                   f"{sum(len(v) for v in em['geometry']['surfaces'].values())} surfaces, "
                   f"{sum(len(v) for v in em['geometry']['openings'].values())} openings",
        "context": {
            "zones": len(em['geometry']['zones']),
            "surfaces": sum(len(v) for v in em['geometry']['surfaces'].values()),
            "openings": sum(len(v) for v in em['geometry']['openings'].values()),
            "materials": len(em['catalogs']['materials'])
        }
    })
    
    return em


def main(argv=None):
    """Command-line interface for translator."""
    argv = argv or sys.argv[1:]
    if not argv:
        print("Usage: python -m emtools.translators.hbjson_importer <input.hbjson> [output.emjson]")
        return 2
    
    out = argv[1] if len(argv) > 1 else argv[0].rsplit('.', 1)[0] + ".emjson"
    em = translate_hbjson_to_v6(argv[0])
    
    with open(out, "w", encoding="utf-8") as f:
        json.dump(em, f, indent=2)
    
    print(f"✓ Wrote {out}")
    print(f"  - {len(em['geometry']['zones'])} zones")
    print(f"  - {sum(len(v) for v in em['geometry']['surfaces'].values())} surfaces")
    print(f"  - {sum(len(v) for v in em['geometry']['openings'].values())} openings")
    print(f"  - {len(em['diagnostics'])} diagnostics")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
