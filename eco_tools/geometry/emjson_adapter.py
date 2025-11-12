"""
Geometry Builder - EMJSON Adapter

ONLY integration point with existing ECO Tools code.
Converts GeometryBuilder output to standard EMJSON v6 format.

This adapter ensures geometry_builder remains isolated while
producing output compatible with existing import/export workflow.
"""

from typing import Dict, Any, List
from datetime import datetime
from .builder import GeometryBuilder
from .models import Zone, Surface
from .exceptions import ExportError


class EMJSONAdapter:
    """
    Adapter to convert GeometryBuilder geometry to EMJSON v6 format

    This is the ONLY way geometry_builder communicates with existing ECO Tools.
    All output conforms to EMJSON v6 specification for seamless integration.
    """

    @staticmethod
    def to_emjson(builder: GeometryBuilder, project_name: str = "Geometry Builder Model") -> Dict[str, Any]:
        """
        Export GeometryBuilder model to EMJSON v6 format

        Args:
            builder: GeometryBuilder instance to export
            project_name: Project name for EMJSON metadata

        Returns:
            Dictionary in EMJSON v6 format

        Raises:
            ExportError: If export fails
        """
        try:
            emjson = {
                "emjson_version": "6.0",
                "project": {
                    "name": project_name,
                    "created": datetime.now().isoformat(),
                    "source_format": "ECO_GeometryBuilder",
                    "generator": "emtools.geometry_builder v0.1.0"
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
            for zone in builder.zones:
                emjson_zone = EMJSONAdapter._export_zone(zone)
                emjson["geometry"]["zones"].append(emjson_zone)

            # Export surfaces (organized by type)
            for surface in builder.surfaces:
                emjson_surface = EMJSONAdapter._export_surface(surface)
                category = EMJSONAdapter._get_surface_category(surface.type)
                emjson["geometry"]["surfaces"][category].append(emjson_surface)

            # Validate output
            if not EMJSONAdapter.validate_emjson(emjson):
                raise ExportError("Generated EMJSON failed validation")

            return emjson

        except Exception as e:
            raise ExportError(f"EMJSON export failed: {e}")

    @staticmethod
    def _export_zone(zone: Zone) -> Dict[str, Any]:
        """Export single zone to EMJSON format"""
        return {
            "id": zone.id,
            "name": zone.name,
            "floor_area_m2": round(zone.calculate_floor_area(), 2),
            "volume_m3": round(zone.calculate_volume(), 2),
            "zone_type": zone.zone_type,
            "multiplier": zone.multiplier
        }

    @staticmethod
    def _export_surface(surface: Surface) -> Dict[str, Any]:
        """Export single surface to EMJSON format"""
        return {
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

    @staticmethod
    def _get_surface_category(surface_type: str) -> str:
        """
        Map surface type to EMJSON category

        Args:
            surface_type: Surface type from geometry_builder

        Returns:
            EMJSON category name
        """
        if "wall" in surface_type:
            return "walls"
        elif surface_type == "roof":
            return "roofs"
        elif surface_type == "floor":
            return "floors"
        elif surface_type == "window":
            return "windows"
        elif surface_type == "door":
            return "doors"
        else:
            return "walls"  # Default fallback

    @staticmethod
    def validate_emjson(emjson: Dict[str, Any]) -> bool:
        """
        Validate that output conforms to EMJSON v6 structure

        Args:
            emjson: Dictionary to validate

        Returns:
            True if valid
        """
        try:
            # Check required top-level keys
            required_keys = ['emjson_version', 'project', 'geometry']
            if not all(key in emjson for key in required_keys):
                return False

            # Check version
            if emjson['emjson_version'] != "6.0":
                return False

            # Check project structure
            project_required = ['name', 'created', 'source_format']
            if not all(key in emjson['project'] for key in project_required):
                return False

            # Check geometry structure
            geometry = emjson['geometry']
            if 'zones' not in geometry or 'surfaces' not in geometry:
                return False

            # Check surface categories
            surface_categories = ['walls', 'roofs', 'floors', 'windows', 'doors']
            if not all(cat in geometry['surfaces'] for cat in surface_categories):
                return False

            # Validate zone format
            for zone in geometry['zones']:
                zone_required = ['id', 'name', 'floor_area_m2', 'volume_m3']
                if not all(key in zone for key in zone_required):
                    return False

            # Validate surface format
            for category in surface_categories:
                for surface in geometry['surfaces'][category]:
                    surface_required = ['id', 'zone_id', 'type', 'geometry_mode', 'vertices_m']
                    if not all(key in surface for key in surface_required):
                        return False

                    # Check vertices format
                    if not isinstance(surface['vertices_m'], list):
                        return False

                    if len(surface['vertices_m']) < 3:
                        return False

                    # Check each vertex is a 3-tuple
                    for vertex in surface['vertices_m']:
                        if not isinstance(vertex, (list, tuple)) or len(vertex) != 3:
                            return False

            return True

        except Exception:
            return False

    @staticmethod
    def export_to_file(builder: GeometryBuilder, file_path: str, project_name: str = "Geometry Builder Model"):
        """
        Export GeometryBuilder model directly to EMJSON file

        Args:
            builder: GeometryBuilder instance
            file_path: Output file path
            project_name: Project name for metadata

        Raises:
            ExportError: If export or file write fails
        """
        import json

        try:
            emjson = EMJSONAdapter.to_emjson(builder, project_name)

            with open(file_path, 'w') as f:
                json.dump(emjson, f, indent=2)

        except Exception as e:
            raise ExportError(f"Failed to write EMJSON file: {e}")

    @staticmethod
    def get_export_summary(builder: GeometryBuilder) -> Dict[str, Any]:
        """
        Get summary of what will be exported (without actually exporting)

        Args:
            builder: GeometryBuilder instance

        Returns:
            Dictionary with export preview information
        """
        surface_counts = {}
        for surface in builder.surfaces:
            category = EMJSONAdapter._get_surface_category(surface.type)
            surface_counts[category] = surface_counts.get(category, 0) + 1

        return {
            "zone_count": len(builder.zones),
            "total_surfaces": len(builder.surfaces),
            "surface_breakdown": surface_counts,
            "total_floor_area_m2": round(builder.get_total_floor_area(), 2),
            "total_volume_m3": round(builder.get_total_volume(), 2),
            "emjson_version": "6.0",
            "source_format": "ECO_GeometryBuilder"
        }
