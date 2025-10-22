"""
Unit tests for FormatDetector
"""

import pytest
from eco_tools.core.format_detector import FormatDetector, FormatInfo


class TestFormatDetector:
    """Test format detection"""
    
    def test_init(self):
        """Test detector initialization"""
        detector = FormatDetector()
        assert detector is not None
    
    def test_parse_version_2022(self):
        """Test version parsing"""
        detector = FormatDetector()
        version = detector._parse_version("CA Title 24 2022 Multifamily.bin")
        assert version == "2022"
    
    def test_parse_version_2019(self):
        """Test version parsing 2019"""
        detector = FormatDetector()
        version = detector._parse_version("T24_2019_Nonresidential.bin")
        assert version == "2019"
    
    def test_parse_building_type_mf(self):
        """Test building type detection"""
        detector = FormatDetector()
        import xml.etree.ElementTree as ET
        
        root = ET.fromstring("<root><ResZn></ResZn></root>")
        building_type = detector._parse_building_type("Multifamily", root)
        assert building_type == "MF"
    
    def test_parse_building_type_nr(self):
        """Test NR building type detection"""
        detector = FormatDetector()
        import xml.etree.ElementTree as ET
        
        root = ET.fromstring("<root><ComZn></ComZn></root>")
        building_type = detector._parse_building_type("Nonresidential", root)
        assert building_type == "NR"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
