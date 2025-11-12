"""
EMJSON to HBJSON Exporter
===========================

Converts ECO Alpha EMJSON v6.1 format to Ladybug Tools Honeybee JSON format.

This enables:
- EnergyPlus simulation via Ladybug Tools
- Radiance daylighting analysis
- Export to Rhino/Grasshopper
- Round-trip: CIBD22X → EMJSON → HBJSON → EnergyPlus

HBJSON enables access to:
✅ EnergyPlus detailed simulation
✅ Radiance daylighting
✅ OpenStudio compatibility
✅ Rhino/Grasshopper integration

Author: ECO Tools Team
Version: 7.0.0
Date: November 11, 2025
"""

from typing import Dict, List, Optional
import json
from pathlib import Path

# Ladybug Tools imports (optional - graceful degradation)
try:
    from ladybug_geometry.geometry3d import Point3D, Vector3D, Face3D
    from honeybee.model import Model as HBModel
    from honeybee.room import Room as HBRoom
    from honeybee.face import Face as HBFace
    from honeybee.aperture import Aperture as HBAperture
    from honeybee.door import Door as HBDoor
    from honeybee.facetype import face_types
    from honeybee_energy.material.opaque import EnergyMaterial
    from honeybee_energy.construction.opaque import OpaqueConstruction
    from honeybee_energy.construction.window import WindowConstruction
    from honeybee_energy.schedule.fixedinterval import ScheduleFixedInterval
    HONEYBEE_AVAILABLE = True
except ImportError:
    HONEYBEE_AVAILABLE = False

from eco_tools.core.internal_repr import InternalRepresentation


class HBJSONExporter:
    """
    Export EMJSON v6.1 InternalRepresentation to Honeybee JSON

    Workflow:
    1. Take InternalRepresentation
    2. Create Honeybee Model
    3. Convert zones → rooms
    4. Convert surfaces → faces
    5. Convert openings → apertures/doors
    6. Convert materials, constructions, schedules
    7. Export to HBJSON file
    """

    def __init__(self):
        """Initialize HBJSON exporter"""
        if not HONEYBEE_AVAILABLE:
            raise ImportError(
                "Honeybee Tools not installed. Install with:\n"
                "  pip install honeybee-core honeybee-energy ladybug-geometry"
            )

        self.hb_model: Optional[HBModel] = None

    def export_to_file(self, internal_repr: InternalRepresentation, output_path: str):
        """
        Export InternalRepresentation to HBJSON file

        Args:
            internal_repr: EMJSON v6.1 InternalRepresentation
            output_path: Path to save .hbjson file
        """
        # Create Honeybee model
        self.hb_model = self._create_honeybee_model(internal_repr)

        # Write to file
        self.hb_model.to_hbjson(output_path)

    def _create_honeybee_model(self, internal_repr: InternalRepresentation) -> HBModel:
        """Create Honeybee Model from InternalRepresentation"""

        # Convert zones to rooms
        hb_rooms = []
        for zone in internal_repr.zones:
            try:
                hb_room = self._convert_zone_to_room(zone)
                if hb_room:
                    hb_rooms.append(hb_room)
            except Exception as e:
                print(f"Warning: Failed to convert zone '{zone.name}': {e}")
                continue

        # Create model
        model_name = internal_repr.project_name or "EMJSON Export"
        hb_model = HBModel(
            identifier=model_name.replace(" ", "_"),
            rooms=hb_rooms,
            display_name=model_name
        )

        # Add materials and constructions if available
        self._add_materials_and_constructions(hb_model, internal_repr)

        return hb_model

    def _convert_zone_to_room(self, zone) -> Optional[HBRoom]:
        """Convert EMJSON zone to Honeybee room"""

        # Convert surfaces to faces
        hb_faces = []
        for surface in zone.surfaces:
            try:
                hb_face = self._convert_surface_to_face(surface)
                if hb_face:
                    hb_faces.append(hb_face)
            except Exception as e:
                print(f"Warning: Failed to convert surface '{surface.name}': {e}")
                continue

        if not hb_faces:
            print(f"Warning: Zone '{zone.name}' has no valid faces")
            return None

        # Create room from faces
        try:
            hb_room = HBRoom(
                identifier=zone.name.replace(" ", "_"),
                faces=hb_faces,
                display_name=zone.name
            )
            return hb_room
        except Exception as e:
            print(f"Warning: Failed to create room from faces: {e}")
            return None

    def _convert_surface_to_face(self, surface) -> Optional[HBFace]:
        """Convert EMJSON surface to Honeybee face"""

        # Extract vertices
        if not hasattr(surface, 'vertices') or not surface.vertices:
            print(f"Warning: Surface '{surface.name}' has no vertices")
            return None

        # Convert to Point3D
        try:
            pts = [Point3D(v['x'], v['y'], v['z']) for v in surface.vertices]
        except (KeyError, TypeError) as e:
            print(f"Warning: Invalid vertex format in surface '{surface.name}': {e}")
            return None

        # Create Face3D geometry
        try:
            face_geo = Face3D(pts)
        except Exception as e:
            print(f"Warning: Failed to create Face3D for '{surface.name}': {e}")
            return None

        # Map surface type to Honeybee face type
        hb_face_type = self._map_surface_type(surface.surface_type)

        # Create Honeybee face
        hb_face = HBFace(
            identifier=surface.name.replace(" ", "_"),
            geometry=face_geo,
            type=hb_face_type,
            display_name=surface.name
        )

        # Add openings (apertures and doors)
        if hasattr(surface, 'openings'):
            for opening in surface.openings:
                try:
                    if opening.opening_type == "window":
                        hb_aperture = self._convert_opening_to_aperture(opening)
                        if hb_aperture:
                            hb_face.add_aperture(hb_aperture)
                    elif opening.opening_type == "door":
                        hb_door = self._convert_opening_to_door(opening)
                        if hb_door:
                            hb_face.add_door(hb_door)
                except Exception as e:
                    print(f"Warning: Failed to add opening '{opening.name}': {e}")
                    continue

        return hb_face

    def _convert_opening_to_aperture(self, opening) -> Optional[HBAperture]:
        """Convert EMJSON window to Honeybee aperture"""

        if not hasattr(opening, 'vertices') or not opening.vertices:
            return None

        try:
            # Convert vertices to Point3D
            pts = [Point3D(v['x'], v['y'], v['z']) for v in opening.vertices]

            # Create Face3D geometry
            aperture_geo = Face3D(pts)

            # Create aperture
            hb_aperture = HBAperture(
                identifier=opening.name.replace(" ", "_"),
                geometry=aperture_geo,
                display_name=opening.name
            )

            return hb_aperture

        except Exception as e:
            print(f"Warning: Failed to create aperture '{opening.name}': {e}")
            return None

    def _convert_opening_to_door(self, opening) -> Optional[HBDoor]:
        """Convert EMJSON door to Honeybee door"""

        if not hasattr(opening, 'vertices') or not opening.vertices:
            return None

        try:
            # Convert vertices to Point3D
            pts = [Point3D(v['x'], v['y'], v['z']) for v in opening.vertices]

            # Create Face3D geometry
            door_geo = Face3D(pts)

            # Create door
            hb_door = HBDoor(
                identifier=opening.name.replace(" ", "_"),
                geometry=door_geo,
                display_name=opening.name
            )

            return hb_door

        except Exception as e:
            print(f"Warning: Failed to create door '{opening.name}': {e}")
            return None

    def _map_surface_type(self, emjson_type: str):
        """
        Map EMJSON surface type to Honeybee face type

        EMJSON types: exterior_wall, interior_wall, floor, roof, ceiling
        Honeybee types: Wall, Floor, RoofCeiling, AirBoundary
        """
        from honeybee.facetype import face_types

        mapping = {
            'exterior_wall': face_types.wall,
            'interior_wall': face_types.wall,
            'floor': face_types.floor,
            'roof': face_types.roof_ceiling,
            'ceiling': face_types.roof_ceiling,
            'slab': face_types.floor
        }

        return mapping.get(emjson_type.lower(), face_types.wall)

    def _add_materials_and_constructions(self, hb_model: HBModel, internal_repr: InternalRepresentation):
        """Add materials and constructions to Honeybee model"""

        # Add materials
        if hasattr(internal_repr, 'materials') and internal_repr.materials:
            for material in internal_repr.materials:
                try:
                    hb_material = EnergyMaterial(
                        identifier=material.name.replace(" ", "_"),
                        thickness=material.thickness_m,
                        conductivity=material.conductivity,
                        density=material.density,
                        specific_heat=material.specific_heat,
                        display_name=material.name
                    )
                    hb_model.properties.energy.add_material(hb_material)
                except Exception as e:
                    print(f"Warning: Failed to add material '{material.name}': {e}")
                    continue

        # Add constructions
        if hasattr(internal_repr, 'constructions') and internal_repr.constructions:
            for construction in internal_repr.constructions:
                try:
                    # Get material references
                    materials = []
                    if hasattr(construction, 'material_refs'):
                        for mat_ref in construction.material_refs:
                            # Find material in model
                            hb_mat = hb_model.properties.energy.material_by_identifier(
                                mat_ref.replace(" ", "_")
                            )
                            if hb_mat:
                                materials.append(hb_mat)

                    if materials:
                        hb_construction = OpaqueConstruction(
                            identifier=construction.name.replace(" ", "_"),
                            materials=materials,
                            display_name=construction.name
                        )
                        hb_model.properties.energy.add_construction(hb_construction)
                except Exception as e:
                    print(f"Warning: Failed to add construction '{construction.name}': {e}")
                    continue


# Convenience function
def export_to_hbjson(internal_repr: InternalRepresentation, output_path: str):
    """
    Export InternalRepresentation to HBJSON file

    Args:
        internal_repr: EMJSON v6.1 InternalRepresentation
        output_path: Path to save .hbjson file
    """
    exporter = HBJSONExporter()
    exporter.export_to_file(internal_repr, output_path)
