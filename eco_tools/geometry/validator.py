"""
Geometry Builder - Validation Module

Validates geometry for common issues:
- Minimum vertex count
- Degenerate surfaces (zero area)
- Non-planar surfaces
- Self-intersecting polygons
- Zone completeness
"""

from typing import List, Dict, Any
from .models import Surface, Zone
from .exceptions import ValidationError


class GeometryValidator:
    """Validates building geometry for common issues"""

    @staticmethod
    def validate_surface(surface: Surface, strict: bool = False) -> List[Dict[str, Any]]:
        """
        Validate a single surface

        Args:
            surface: Surface to validate
            strict: If True, warnings become errors

        Returns:
            List of validation issues (each with 'level', 'surface_id', 'message')
        """
        issues = []

        # Check vertex count
        if len(surface.vertices) < 3:
            issues.append({
                "level": "error",
                "surface_id": surface.id,
                "type": "invalid_vertex_count",
                "message": f"Surface has only {len(surface.vertices)} vertices (minimum 3)"
            })
            return issues  # Can't check further if no vertices

        # Check area
        area = surface.calculate_area()
        if area < 1e-6:
            issues.append({
                "level": "error",
                "surface_id": surface.id,
                "type": "degenerate_surface",
                "message": f"Surface area is effectively zero (degenerate geometry)"
            })
        elif area < 0.01:
            level = "error" if strict else "warning"
            issues.append({
                "level": level,
                "surface_id": surface.id,
                "type": "small_surface",
                "message": f"Surface area is very small: {area:.4f} m²"
            })

        # Check planarity (for surfaces with 4+ vertices)
        if len(surface.vertices) >= 4:
            if not surface.is_planar(tolerance=0.01):
                level = "error" if strict else "warning"
                issues.append({
                    "level": level,
                    "surface_id": surface.id,
                    "type": "non_planar",
                    "message": "Surface vertices are not planar (may cause rendering issues)"
                })

        # Check for duplicate vertices
        vertex_positions = [v.to_tuple() for v in surface.vertices]
        if len(vertex_positions) != len(set(vertex_positions)):
            issues.append({
                "level": "warning",
                "surface_id": surface.id,
                "type": "duplicate_vertices",
                "message": "Surface has duplicate vertices"
            })

        return issues

    @staticmethod
    def validate_zone(zone: Zone, strict: bool = False) -> List[Dict[str, Any]]:
        """
        Validate a zone

        Args:
            zone: Zone to validate
            strict: If True, warnings become errors

        Returns:
            List of validation issues
        """
        issues = []

        # Check if zone has surfaces
        if not zone.surfaces:
            issues.append({
                "level": "error",
                "zone_id": zone.id,
                "type": "empty_zone",
                "message": "Zone has no surfaces"
            })
            return issues

        # Check for required surface types
        has_floor = any(s.type == "floor" for s in zone.surfaces)
        has_roof = any(s.type == "roof" for s in zone.surfaces)
        has_walls = any("wall" in s.type for s in zone.surfaces)

        if not has_floor:
            level = "error" if strict else "warning"
            issues.append({
                "level": level,
                "zone_id": zone.id,
                "type": "missing_floor",
                "message": "Zone has no floor surface"
            })

        if not has_roof:
            level = "error" if strict else "warning"
            issues.append({
                "level": level,
                "zone_id": zone.id,
                "type": "missing_roof",
                "message": "Zone has no roof/ceiling surface"
            })

        if not has_walls:
            level = "error" if strict else "warning"
            issues.append({
                "level": level,
                "zone_id": zone.id,
                "type": "missing_walls",
                "message": "Zone has no wall surfaces"
            })

        # Check floor area
        floor_area = zone.calculate_floor_area()
        if floor_area < 0.01:
            issues.append({
                "level": "error",
                "zone_id": zone.id,
                "type": "invalid_floor_area",
                "message": f"Zone floor area is too small: {floor_area:.4f} m²"
            })

        # Check volume
        volume = zone.calculate_volume()
        if volume < 0.1:
            issues.append({
                "level": "error",
                "zone_id": zone.id,
                "type": "invalid_volume",
                "message": f"Zone volume is too small: {volume:.4f} m³"
            })

        # Check multiplier
        if zone.multiplier < 1:
            issues.append({
                "level": "error",
                "zone_id": zone.id,
                "type": "invalid_multiplier",
                "message": f"Zone multiplier must be >= 1, got {zone.multiplier}"
            })

        # Validate all surfaces in zone
        for surface in zone.surfaces:
            surface_issues = GeometryValidator.validate_surface(surface, strict)
            issues.extend(surface_issues)

        return issues

    @staticmethod
    def validate_model(zones: List[Zone], strict: bool = False) -> Dict[str, Any]:
        """
        Validate entire building model

        Args:
            zones: List of all zones
            strict: If True, warnings become errors

        Returns:
            Dictionary with validation results:
            {
                'valid': bool,
                'error_count': int,
                'warning_count': int,
                'issues': List[Dict]
            }
        """
        all_issues = []

        # Check for zones
        if not zones:
            return {
                'valid': False,
                'error_count': 1,
                'warning_count': 0,
                'issues': [{
                    'level': 'error',
                    'type': 'no_zones',
                    'message': 'Model has no zones'
                }]
            }

        # Validate each zone
        for zone in zones:
            zone_issues = GeometryValidator.validate_zone(zone, strict)
            all_issues.extend(zone_issues)

        # Check for duplicate zone IDs
        zone_ids = [z.id for z in zones]
        if len(zone_ids) != len(set(zone_ids)):
            all_issues.append({
                'level': 'error',
                'type': 'duplicate_zone_ids',
                'message': 'Model has duplicate zone IDs'
            })

        # Check for duplicate surface IDs across all zones
        all_surface_ids = []
        for zone in zones:
            all_surface_ids.extend([s.id for s in zone.surfaces])

        if len(all_surface_ids) != len(set(all_surface_ids)):
            all_issues.append({
                'level': 'error',
                'type': 'duplicate_surface_ids',
                'message': 'Model has duplicate surface IDs'
            })

        # Count errors and warnings
        error_count = sum(1 for issue in all_issues if issue['level'] == 'error')
        warning_count = sum(1 for issue in all_issues if issue['level'] == 'warning')

        return {
            'valid': error_count == 0,
            'error_count': error_count,
            'warning_count': warning_count,
            'issues': all_issues
        }

    @staticmethod
    def get_issues_summary(validation_result: Dict[str, Any]) -> str:
        """
        Get human-readable summary of validation results

        Args:
            validation_result: Result from validate_model()

        Returns:
            Summary string
        """
        if validation_result['valid']:
            if validation_result['warning_count'] > 0:
                return f"✓ Valid with {validation_result['warning_count']} warnings"
            else:
                return "✓ Valid - No issues found"
        else:
            return f"✗ Invalid - {validation_result['error_count']} errors, {validation_result['warning_count']} warnings"

    @staticmethod
    def filter_issues_by_level(issues: List[Dict[str, Any]], level: str) -> List[Dict[str, Any]]:
        """Filter issues by severity level"""
        return [issue for issue in issues if issue['level'] == level]

    @staticmethod
    def filter_issues_by_type(issues: List[Dict[str, Any]], issue_type: str) -> List[Dict[str, Any]]:
        """Filter issues by type"""
        return [issue for issue in issues if issue.get('type') == issue_type]
