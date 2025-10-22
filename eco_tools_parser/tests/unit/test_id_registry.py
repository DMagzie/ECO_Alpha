"""
Unit tests for IDRegistry
"""

import pytest
from eco_tools.core.id_registry import IDRegistry


class TestIDRegistry:
    """Test ID registry"""
    
    def test_init(self):
        """Test registry initialization"""
        registry = IDRegistry()
        assert len(registry.used_ids) == 0
    
    def test_generate_id_stable(self):
        """Test stable ID generation"""
        registry = IDRegistry()
        
        id1 = registry.generate_id('Z', 'Living Room', '', 'CIBD22X')
        id2 = registry.generate_id('Z', 'Living Room', '', 'CIBD22X')
        
        assert id1 == id2
    
    def test_generate_id_unique(self):
        """Test unique ID generation"""
        registry = IDRegistry()
        
        id1 = registry.generate_id('Z', 'Living Room', '', 'CIBD22X')
        id2 = registry.generate_id('Z', 'Kitchen', '', 'CIBD22X')
        
        assert id1 != id2
    
    def test_generate_id_with_context(self):
        """Test ID with context"""
        registry = IDRegistry()
        
        id1 = registry.generate_id('S', 'Wall1', 'Living Room', 'CIBD22X')
        id2 = registry.generate_id('S', 'Wall1', 'Kitchen', 'CIBD22X')
        
        assert id1 != id2
    
    def test_slugify(self):
        """Test text slugification"""
        registry = IDRegistry()
        
        slug = registry._slugify("Living Room #1")
        assert slug == "living_room_1"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
