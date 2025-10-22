"""
Unit tests for Validator
"""

import pytest
from eco_tools.core.validator import Validator, ValidationResult
from eco_tools.core.internal_repr import InternalRepresentation, Zone, Surface


class TestValidator:
    """Test validator"""
    
    def test_init(self):
        """Test validator initialization"""
        validator = Validator()
        assert validator is not None
    
    def test_validate_empty(self):
        """Test validation of empty model"""
        validator = Validator()
        internal = InternalRepresentation()
        
        result = validator.validate(internal)
        
        assert isinstance(result, ValidationResult)
        assert len(result.warnings) > 0  # Should warn about no zones
    
    def test_validate_valid_zone(self):
        """Test validation of valid zone"""
        validator = Validator()
        internal = InternalRepresentation()
        
        zone = Zone(
            id='Z_001',
            name='Living Room',
            building_type='MF',
            floor_area_m2=100.0,
            multiplier=1
        )
        internal.zones.append(zone)
        
        result = validator.validate(internal)
        
        assert result.is_valid
        assert len(result.errors) == 0
    
    def test_validate_invalid_area(self):
        """Test validation catches invalid area"""
        validator = Validator()
        internal = InternalRepresentation()
        
        zone = Zone(
            id='Z_001',
            name='Living Room',
            building_type='MF',
            floor_area_m2=-10.0,  # Invalid
            multiplier=1
        )
        internal.zones.append(zone)
        
        result = validator.validate(internal)
        
        assert not result.is_valid
        assert len(result.errors) > 0
    
    def test_validate_broken_reference(self):
        """Test validation catches broken references"""
        validator = Validator()
        internal = InternalRepresentation()
        
        # Add surface with non-existent zone reference
        surface = Surface(
            id='S_001',
            name='Wall',
            parent_zone_id='Z_NONEXISTENT',
            surface_type='wall'
        )
        internal.surfaces.append(surface)
        
        result = validator.validate(internal)
        
        assert not result.is_valid
        assert any('non-existent' in err.lower() for err in result.errors)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
