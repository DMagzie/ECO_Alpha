"""
HBJSON to EMJSON Importer
===========================

Converts Ladybug Tools Honeybee JSON format to ECO Alpha EMJSON v6.1 format.

This enables:
- Import from Rhino/Grasshopper via Ladybug Tools
- Import from OpenStudio via Honeybee
- Round-trip with EnergyPlus simulations
- GEM → HBJSON → EMJSON → CIBD22X workflow

HBJSON provides:
✅ Detailed 3D geometry (vertices, face normal)
✅ Materials and constructions
✅ Schedules (detailed hourly)
✅ HVAC system templates
✅ Load definitions

Author: ECO Tools Team
Version: 7.0.0
Date: November 11, 2025
"""

from typing import Dict, List, Optional, Any
import json
from pathlib import Path

# Ladybug Tools imports (optional - graceful degradation)
try:
    from honeybee.model import Model as HBModel
    from honeybee.room import Room as HBRoom
    from honeybee.face import Face as HBFace
    from honeybee.aperture import Aperture as HBAperture
    from honeybee.door import Door as HBDoor
    from honeybee_energy.construction.opaque import OpaqueConstruction
    from honeybee_energy.construction.window import WindowConstruction
    from honeybee_energy.schedule.ruleset import ScheduleRuleset
    from honeybee_energy.programtype import ProgramType
    HONEYBEE_AVAILABLE = True
except ImportError:
    HONEYBEE_AVAILABLE = False
    HBModel = None

from eco_tools.core.internal_repr import (
    InternalRepresentation,
    Zone,
    Surface,
    Opening,
    Material,
    Construction,
    Schedule
)


class HBJSONImporter:
    """
    Import Honeybee JSON to EMJSON v6.1 InternalRepresentation

    Workflow:
    1. Load HBJSON file
    2. Parse Honeybee Model
    3. Convert rooms → zones
    4. Convert faces → surfaces
    5. Convert apertures/doors → openings
    6. Convert materials, constructions, schedules
    7. Return InternalRepresentation
    """

    def __init__(self):
        """Initialize HBJSON importer"""
        if not HONEYBEE_AVAILABLE:
            raise ImportError(
                "Honeybee Tools not installed. Install with:\n"
                "  pip install honeybee-core honeybee-energy"
            )

        self.hb_model: Optional[HBModel] = None
        self.materials: Dict[str, Material] = {}
        self.constructions: Dict[str, Construction] = {}
        self.schedules: Dict[str, Schedule] = {}

    def import_file(self, hbjson_path: str) -> InternalRepresentation:
        """
        Import HBJSON file to InternalRepresentation

        Args:
            hbjson_path: Path to .hbjson file

        Returns:
            InternalRepresentation object
        """
        # Load Honeybee model
        self.hb_model = HBModel.from_hbjson(hbjson_path)

        # Convert components
        materials = self._convert_materials()
        constructions = self._convert_constructions()
        schedules = self._convert_schedules()
        zones = self._convert_rooms_to_zones()

        # Create internal representation
        return InternalRepresentation(
            project_name=self.hb_model.display_name or "Imported from HBJSON",
            zones=zones,
            materials=materials,
            constructions=constructions,
            schedules=schedules,
            # Additional properties from HBJSON
            annotation={
                'source_format': 'hbjson',
                'honeybee_version': getattr(self.hb_model, '__version__', 'unknown'),
                'units': 'meters',  # HBJSON always uses meters
            }
        )

    def _convert_materials(self) -> List[Material]:
        """Convert Honeybee materials to EMJSON materials"""
        materials = []

        if not hasattr(self.hb_model.properties, 'energy'):
            return materials

        # Get all materials from constructions
        for construction in self.hb_model.properties.energy.constructions:
            if hasattr(construction, 'materials'):
                for hb_mat in construction.materials:
                    if hb_mat.identifier not in self.materials:
                        material = Material(
                            name=hb_mat.identifier,
                            thickness_m=getattr(hb_mat, 'thickness', 0.0),
                            conductivity=getattr(hb_mat, 'conductivity', 0.0),
                            density=getattr(hb_mat, 'density', 0.0),
                            specific_heat=getattr(hb_mat, 'specific_heat', 0.0),
                            annotation={
                                'source': 'honeybee',
                                'type': hb_mat.__class__.__name__,
                                'display_name': getattr(hb_mat, 'display_name', hb_mat.identifier)
                            }
                        )
                        materials.append(material)
                        self.materials[hb_mat.identifier] = material

        return materials

    def _convert_constructions(self) -> List[Construction]:
        """Convert Honeybee constructions to EMJSON constructions"""
        constructions = []

        if not hasattr(self.hb_model.properties, 'energy'):
            return constructions

        for hb_cons in self.hb_model.properties.energy.constructions:
            # Get material layers
            material_refs = []
            if hasattr(hb_cons, 'materials'):
                material_refs = [mat.identifier for mat in hb_cons.materials]

            construction = Construction(
                name=hb_cons.identifier,
                material_refs=material_refs,
                annotation={
                    'source': 'honeybee',
                    'type': hb_cons.__class__.__name__,
                    'display_name': getattr(hb_cons, 'display_name', hb_cons.identifier),
                    'u_factor': getattr(hb_cons, 'u_factor', None),
                    'r_factor': getattr(hb_cons, 'r_factor', None)
                }
            )
            constructions.append(construction)
            self.constructions[hb_cons.identifier] = construction

        return constructions

    def _convert_schedules(self) -> List[Schedule]:
        """Convert Honeybee schedules to EMJSON schedules"""
        schedules = []

        if not hasattr(self.hb_model.properties, 'energy'):
            return schedules

        for hb_sched in self.hb_model.properties.energy.schedules:
            # Extract hourly values if available
            hourly_values = []
            if isinstance(hb_sched, ScheduleRuleset):
                # Get default day schedule
                if hasattr(hb_sched, 'default_day_schedule'):
                    hourly_values = hb_sched.default_day_schedule.values

            schedule = Schedule(
                name=hb_sched.identifier,
                type='fraction',  # Most common type
                hourly_values=list(hourly_values) if hourly_values else [],
                annotation={
                    'source': 'honeybee',
                    'schedule_type': hb_sched.__class__.__name__,
                    'display_name': getattr(hb_sched, 'display_name', hb_sched.identifier)
                }
            )
            schedules.append(schedule)
            self.schedules[hb_sched.identifier] = schedule

        return schedules

    def _convert_rooms_to_zones(self) -> List[Zone]:
        """Convert Honeybee rooms to EMJSON zones"""
        zones = []

        for hb_room in self.hb_model.rooms:
            zone = self._convert_room(hb_room)
            zones.append(zone)

        return zones

    def _convert_room(self, hb_room: 'HBRoom') -> Zone:
        """Convert single Honeybee room to EMJSON zone"""

        # Convert surfaces (faces)
        surfaces = []
        for hb_face in hb_room.faces:
            surface = self._convert_face(hb_face)
            surfaces.append(surface)

        # Calculate zone properties from geometry
        floor_area_m2 = hb_room.floor_area
        volume_m3 = hb_room.volume

        # Estimate ceiling height
        ceiling_height_m = volume_m3 / floor_area_m2 if floor_area_m2 > 0 else 3.0

        # Get program type if available
        space_function = "Unknown"
        if hasattr(hb_room.properties, 'energy') and hb_room.properties.energy.program_type:
            program = hb_room.properties.energy.program_type
            space_function = program.display_name or program.identifier

        zone = Zone(
            name=hb_room.display_name or hb_room.identifier,
            zone_type="conditioned",  # Default assumption
            floor_area_m2=floor_area_m2,
            ceiling_height_m=ceiling_height_m,
            volume_m3=volume_m3,
            surfaces=surfaces,
            annotation={
                'source': 'honeybee',
                'identifier': hb_room.identifier,
                'space_function': space_function,
                'multiplier': getattr(hb_room, 'multiplier', 1)
            }
        )

        return zone

    def _convert_face(self, hb_face: 'HBFace') -> Surface:
        """Convert Honeybee face to EMJSON surface"""

        # Convert geometry - extract vertices
        vertices = []
        for pt in hb_face.geometry.vertices:
            vertices.append({
                'x': pt.x,
                'y': pt.y,
                'z': pt.z
            })

        # Calculate area
        area_m2 = hb_face.area

        # Determine surface type
        surface_type = self._map_face_type(hb_face.type.name)

        # Get construction reference
        construction_ref = None
        if hasattr(hb_face.properties, 'energy') and hb_face.properties.energy.construction:
            construction_ref = hb_face.properties.energy.construction.identifier

        # Convert openings (apertures and doors)
        openings = []

        # Apertures (windows)
        for hb_aperture in hb_face.apertures:
            opening = self._convert_aperture(hb_aperture)
            openings.append(opening)

        # Doors
        for hb_door in hb_face.doors:
            opening = self._convert_door(hb_door)
            openings.append(opening)

        surface = Surface(
            name=hb_face.display_name or hb_face.identifier,
            surface_type=surface_type,
            area_m2=area_m2,
            construction_ref=construction_ref,
            vertices=vertices,
            openings=openings,
            annotation={
                'source': 'honeybee',
                'identifier': hb_face.identifier,
                'boundary_condition': hb_face.boundary_condition.name
            }
        )

        return surface

    def _convert_aperture(self, hb_aperture: 'HBAperture') -> Opening:
        """Convert Honeybee aperture to EMJSON opening (window)"""

        # Extract vertices
        vertices = []
        for pt in hb_aperture.geometry.vertices:
            vertices.append({
                'x': pt.x,
                'y': pt.y,
                'z': pt.z
            })

        # Get construction
        construction_ref = None
        if hasattr(hb_aperture.properties, 'energy') and hb_aperture.properties.energy.construction:
            construction_ref = hb_aperture.properties.energy.construction.identifier

        opening = Opening(
            name=hb_aperture.display_name or hb_aperture.identifier,
            opening_type="window",
            area_m2=hb_aperture.area,
            construction_ref=construction_ref,
            vertices=vertices,
            annotation={
                'source': 'honeybee',
                'identifier': hb_aperture.identifier,
                'is_operable': getattr(hb_aperture, 'is_operable', False)
            }
        )

        return opening

    def _convert_door(self, hb_door: 'HBDoor') -> Opening:
        """Convert Honeybee door to EMJSON opening (door)"""

        # Extract vertices
        vertices = []
        for pt in hb_door.geometry.vertices:
            vertices.append({
                'x': pt.x,
                'y': pt.y,
                'z': pt.z
            })

        # Get construction
        construction_ref = None
        if hasattr(hb_door.properties, 'energy') and hb_door.properties.energy.construction:
            construction_ref = hb_door.properties.energy.construction.identifier

        opening = Opening(
            name=hb_door.display_name or hb_door.identifier,
            opening_type="door",
            area_m2=hb_door.area,
            construction_ref=construction_ref,
            vertices=vertices,
            annotation={
                'source': 'honeybee',
                'identifier': hb_door.identifier,
                'is_glass': getattr(hb_door, 'is_glass', False)
            }
        )

        return opening

    def _map_face_type(self, hb_face_type: str) -> str:
        """
        Map Honeybee face type to EMJSON surface type

        Honeybee types: Wall, Floor, RoofCeiling, AirBoundary
        EMJSON types: exterior_wall, interior_wall, floor, roof, ceiling
        """
        mapping = {
            'Wall': 'exterior_wall',  # Default to exterior
            'Floor': 'floor',
            'RoofCeiling': 'roof',  # Default to roof
            'AirBoundary': 'interior_wall'
        }

        return mapping.get(hb_face_type, 'exterior_wall')


# Convenience function
def import_hbjson(file_path: str) -> InternalRepresentation:
    """
    Import HBJSON file to EMJSON

    Args:
        file_path: Path to .hbjson file

    Returns:
        InternalRepresentation object
    """
    importer = HBJSONImporter()
    return importer.import_file(file_path)
