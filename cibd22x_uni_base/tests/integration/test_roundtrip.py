"""
Integration tests for round-trip translation
"""

import pytest
import tempfile
import os
from pathlib import Path
from eco_tools.core.translator import UniversalTranslator


class TestRoundTrip:
    """Test round-trip translations"""
    
    def test_cibd22x_roundtrip(self):
        """Test CIBD22X -> Internal -> CIBD22X"""
        translator = UniversalTranslator()
        
        # Use test fixture
        fixture_path = Path(__file__).parent.parent / 'fixtures' / 'sample.cibd22x'
        
        if not fixture_path.exists():
            pytest.skip("Test fixture not found")
        
        # Load
        internal1 = translator.load(str(fixture_path))
        
        # Save
        with tempfile.NamedTemporaryFile(mode='w', suffix='.cibd22x', delete=False) as f:
            temp_path = f.name
        
        try:
            translator.save(internal1, temp_path, 'CIBD22X')
            
            # Load again
            internal2 = translator.load(temp_path)
            
            # Compare
            assert len(internal1.zones) == len(internal2.zones)
            if internal1.zones:
                assert internal1.zones[0].name == internal2.zones[0].name
        
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
