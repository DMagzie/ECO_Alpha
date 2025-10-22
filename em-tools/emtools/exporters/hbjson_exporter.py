# FILE: em-tools/emtools/exporters/hbjson_exporter.py
# ============================================================================
"""
EMJSON v6 to HBJSON Exporter

Converts EMJSON v6 format back to Honeybee JSON for round-trip capability.

Key conversions:
- Zones → Rooms
- Surfaces → Faces (with area → 3D geometry reconstruction)
- Openings → Apertures
- Materials catalog → HBJSON materials
- Constructions catalog → HBJSON constructions
"""

from __future__ import annotations
from typing import Dict, Any, List
import json


def _reconstruct_face3d_from_annotation(annotation: Dict[str, Any], area_m2: float) -> Dict[str, Any]:
    """
    Reconstruct Face3D geometry from annotation or generate simple rectangle.
    
    Args:
        annotation: Surface annotation containing original HBJSON geometry
        area_m2: Surface area in square meters
        
    Returns:
        Face3D geometry dictionary
    """
    # Try to restore original geometry from annotation
    if annotation and "hbjson_geometry" in annotation:
        return annotation["hbjson_geometry"]
    
    # Generate simple rectangular geometry if no original
    # Create a square with given area at origin
    # Handle None or invalid area values
    if area_m2 is None or area_m2 <= 0:
        area_m2 = 10.0  # Default 10 m² for missing area
    side = area_m2 ** 0.5
    return {
        "type": "Face3D",
        "boundary": [
            [0.0, 0.0, 0.0],
            [side, 0.0, 0.0],
            [side, side, 0.0],
            [0.0, side, 0.0]
        ]
    }


def _export_materials(em: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Export EMJSON materials to HBJSON format."""
    materials = em.get("catalogs", {}).get("materials", [])
    hb_materials = []
    
    for mat in materials:
        annotation = mat.get("annotation", {})
        hbjson_type = annotation.get("hbjson_type", "EnergyMaterial")
        
        if hbjson_type == "EnergyMaterial":
            # Opaque material
            item = {
                "type": "EnergyMaterial",
                "identifier": mat.get("name", mat.get("id", "Material")),
                "thickness": mat.get("thickness_m", 0.0),
                "conductivity": mat.get("conductivity_w_mk", 0.0),
                "density": mat.get("density_kg_m3", 0.0),
                "specific_heat": mat.get("specific_heat_j_kgk", 0.0),
                "thermal_absorptance": mat.get("thermal_absorptance", 0.9),
                "solar_absorptance": mat.get("solar_absorptance", 0.7),
                "visible_absorptance": mat.get("visible_absorptance", 0.7),
                "roughness": annotation.get("roughness", "MediumRough")
            }
            hb_materials.append(item)
        elif "hbjson_properties" in annotation:
            # Window material or other - restore from annotation
            hb_materials.append(annotation["hbjson_properties"])
    
    return hb_materials


def _export_constructions(em: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Export EMJSON constructions to HBJSON format."""
    constructions = em.get("catalogs", {}).get("construction_types", [])
    window_types = em.get("catalogs", {}).get("window_types", [])
    hb_constructions = []
    
    # Opaque constructions
    for cons in constructions:
        annotation = cons.get("annotation", {})
        hbjson_materials = annotation.get("hbjson_materials", cons.get("layers", []))
        
        item = {
            "type": "OpaqueConstructionAbridged",
            "identifier": cons.get("name", cons.get("id", "Construction")),
            "materials": hbjson_materials
        }
        hb_constructions.append(item)
    
    # Window constructions
    for wt in window_types:
        annotation = wt.get("annotation", {})
        hbjson_materials = annotation.get("hbjson_materials", [])
        
        item = {
            "type": "WindowConstructionAbridged",
            "identifier": wt.get("name", wt.get("id", "WindowConstruction")),
            "materials": hbjson_materials if hbjson_materials else ["Generic Clear Glass"]
        }
        hb_constructions.append(item)
    
    return hb_constructions


def _export_rooms(em: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Export EMJSON zones to HBJSON rooms with faces and apertures."""
    zones = em.get("geometry", {}).get("zones", [])
    surfaces = em.get("geometry", {}).get("surfaces", {})
    openings = em.get("geometry", {}).get("openings", {})
    
    # Build surface lookup by ID
    all_surfaces = []
    for bucket in ["walls", "roofs", "floors"]:
        all_surfaces.extend(surfaces.get(bucket, []))
    
    surf_by_id = {s["id"]: s for s in all_surfaces}
    
    # Build opening lookup by ID
    all_openings = []
    for bucket in ["windows", "doors", "skylights"]:
        all_openings.extend(openings.get(bucket, []))
    
    opening_by_id = {o["id"]: o for o in all_openings}
    
    hb_rooms = []
    
    for zone in zones:
        zone_id = zone.get("id", "Zone")
        name = zone.get("name", zone_id)
        annotation = zone.get("annotation", {})
        hbjson_identifier = annotation.get("hbjson_identifier", zone_id)
        
        # Find all surfaces belonging to this zone
        zone_surfaces = [s for s in all_surfaces if s.get("zone_id") == zone_id]
        
        # Convert surfaces to faces
        faces = []
        for surf in zone_surfaces:
            surf_annotation = surf.get("annotation", {})
            
            # Determine face type from annotation or surface location
            hbjson_face_type = surf_annotation.get("hbjson_face_type", "Wall")
            
            # Reconstruct Face3D geometry
            area_m2 = surf.get("area_m2", 0.0)
            geometry = _reconstruct_face3d_from_annotation(surf_annotation, area_m2)
            
            # Get boundary condition
            bc = surf_annotation.get("boundary_condition", {
                "type": "Outdoors",
                "sun_exposure": True,
                "wind_exposure": True,
                "view_factor": {"type": "Autocalculate"}
            })
            
            # Convert surface openings to apertures
            apertures = []
            opening_ids = surf.get("openings", [])
            
            for opening_id in opening_ids:
                opening = opening_by_id.get(opening_id)
                if not opening:
                    continue
                
                opening_annotation = opening.get("annotation", {})
                opening_identifier = opening_annotation.get("hbjson_identifier", opening_id)
                
                # Reconstruct aperture geometry
                opening_area = opening.get("area_m2", 0.0)
                aperture_geometry = _reconstruct_face3d_from_annotation(opening_annotation, opening_area)
                
                aperture = {
                    "type": "Aperture",
                    "identifier": opening_identifier,
                    "display_name": opening.get("name", opening_identifier),
                    "properties": {
                        "type": "AperturePropertiesAbridged",
                        "energy": {
                            "type": "ApertureEnergyPropertiesAbridged"
                        }
                    },
                    "geometry": aperture_geometry,
                    "is_operable": opening_annotation.get("is_operable", False),
                    "boundary_condition": {
                        "type": "Outdoors",
                        "sun_exposure": True,
                        "wind_exposure": True,
                        "view_factor": {"type": "Autocalculate"}
                    }
                }
                
                apertures.append(aperture)
            
            # Create face
            face = {
                "type": "Face",
                "identifier": surf_annotation.get("hbjson_identifier", surf["id"]),
                "display_name": surf.get("name", surf["id"]),
                "properties": {
                    "type": "FacePropertiesAbridged",
                    "energy": {
                        "type": "FaceEnergyPropertiesAbridged"
                    }
                },
                "geometry": geometry,
                "face_type": hbjson_face_type,
                "boundary_condition": bc
            }
            
            if apertures:
                face["apertures"] = apertures
            
            faces.append(face)
        
        # Create room
        room = {
            "type": "Room",
            "identifier": hbjson_identifier,
            "display_name": name,
            "properties": {
                "type": "RoomPropertiesAbridged",
                "energy": {
                    "type": "RoomEnergyPropertiesAbridged"
                }
            },
            "faces": faces
        }
        
        # Add construction set reference if available
        if "construction_set" in annotation:
            room["properties"]["energy"]["construction_set"] = annotation["construction_set"]
        
        hb_rooms.append(room)
    
    return hb_rooms


def emjson6_to_hbjson(em: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convert EMJSON v6 to HBJSON format.
    
    Args:
        em: EMJSON v6 dictionary
        
    Returns:
        HBJSON dictionary
        
    Example:
        >>> hbjson = emjson6_to_hbjson(emjson)
        >>> print(hbjson['type'])
        'Model'
    """
    # Get metadata
    metadata = em.get("_metadata", {})
    hbjson_identifier = metadata.get("hbjson_identifier", "Model")
    
    # Build HBJSON structure
    hbjson = {
        "type": "Model",
        "identifier": hbjson_identifier,
        "display_name": em.get("project", {}).get("model_info", {}).get("project_name", hbjson_identifier),
        "units": metadata.get("hbjson_units", "Meters"),
        "properties": {
            "type": "ModelProperties",
            "energy": {
                "type": "ModelEnergyProperties",
                "construction_sets": [],
                "constructions": _export_constructions(em),
                "materials": _export_materials(em),
                "hvacs": [],  # TODO: Implement HVAC export
                "program_types": [],  # TODO: Implement program types export
                "schedules": [],  # TODO: Implement schedules export
                "schedule_type_limits": []
            }
        },
        "rooms": _export_rooms(em)
    }
    
    return hbjson


def write_hbjson(em: Dict[str, Any], output_path: str) -> None:
    """
    Write EMJSON to HBJSON file.
    
    Args:
        em: EMJSON v6 dictionary
        output_path: Output HBJSON file path
        
    Example:
        >>> write_hbjson(emjson, "output.hbjson")
    """
    hbjson = emjson6_to_hbjson(em)
    
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(hbjson, f, indent=4)


def main():
    """Command-line interface for exporter."""
    import sys
    
    if len(sys.argv) < 3:
        print("Usage: python -m emtools.exporters.hbjson_exporter <input.emjson> <output.hbjson>")
        return 2
    
    input_path = sys.argv[1]
    output_path = sys.argv[2]
    
    # Load EMJSON
    with open(input_path, 'r', encoding='utf-8') as f:
        em = json.load(f)
    
    # Export to HBJSON
    write_hbjson(em, output_path)
    
    print(f"✓ Exported to {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
