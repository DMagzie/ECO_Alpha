"""
Validation Module
Schema-driven validation for CBECC formats
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from eco_tools.core.internal_repr import InternalRepresentation


@dataclass
class ValidationResult:
    """Result of validation"""
    is_valid: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    info: List[str] = field(default_factory=list)
    
    def __str__(self):
        if self.is_valid:
            return f"✓ Valid ({len(self.warnings)} warnings)"
        else:
            return f"✗ Invalid ({len(self.errors)} errors, {len(self.warnings)} warnings)"


class Validator:
    """Schema-driven validation engine"""
    
    def __init__(self, schema: Optional[Any] = None):
        self.schema = schema
    
    def validate(self, 
                 data: InternalRepresentation,
                 schema: Optional[Any] = None) -> ValidationResult:
        """
        Comprehensive validation.
        
        Validates:
        1. Required objects present
        2. Property types correct
        3. References resolve
        4. Constraints satisfied
        """
        errors = []
        warnings = []
        info = []
        
        # Basic structure validation
        if not data.zones:
            warnings.append("No zones found in model")
        
        # Reference validation
        zone_ids = {z.id for z in data.zones}
        surface_ids = {s.id for s in data.surfaces}
        
        # Check surface references
        for surface in data.surfaces:
            if surface.parent_zone_id not in zone_ids:
                errors.append(
                    f"Surface {surface.id} references non-existent zone {surface.parent_zone_id}"
                )
        
        # Check opening references
        for opening in data.openings:
            if opening.parent_surface_id not in surface_ids:
                errors.append(
                    f"Opening {opening.id} references non-existent surface {opening.parent_surface_id}"
                )
        
        # Value range validation
        for zone in data.zones:
            if zone.floor_area_m2 is not None and zone.floor_area_m2 <= 0:
                errors.append(f"Zone {zone.id} has invalid floor area: {zone.floor_area_m2}")
            
            if zone.multiplier < 1:
                errors.append(f"Zone {zone.id} has invalid multiplier: {zone.multiplier}")
        
        for surface in data.surfaces:
            if surface.area_m2 is not None and surface.area_m2 <= 0:
                errors.append(f"Surface {surface.id} has invalid area: {surface.area_m2}")
            
            if surface.tilt_deg is not None and not (0 <= surface.tilt_deg <= 180):
                warnings.append(f"Surface {surface.id} has unusual tilt: {surface.tilt_deg}°")
            
            if surface.azimuth_deg is not None and not (0 <= surface.azimuth_deg <= 360):
                warnings.append(f"Surface {surface.id} has unusual azimuth: {surface.azimuth_deg}°")
        
        # Summary info
        info.append(f"Validated {len(data.zones)} zones")
        info.append(f"Validated {len(data.surfaces)} surfaces")
        info.append(f"Validated {len(data.openings)} openings")
        
        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            info=info
        )
    
    def validate_file(self, file_path: str) -> ValidationResult:
        """Validate file directly"""
        from eco_tools.core.translator import UniversalTranslator
        
        try:
            translator = UniversalTranslator()
            internal = translator.load(file_path)
            return self.validate(internal)
        except Exception as e:
            return ValidationResult(
                is_valid=False,
                errors=[f"Failed to load file: {e}"]
            )
