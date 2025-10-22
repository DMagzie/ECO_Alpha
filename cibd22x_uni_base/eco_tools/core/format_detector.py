"""
Format Detection Module
Automatically identifies CBECC file format, version, and building type
"""

from dataclasses import dataclass
from typing import Optional
import xml.etree.ElementTree as ET
import re


@dataclass
class FormatInfo:
    """Information about detected file format"""
    format_type: str  # 'CIBD22', 'CIBD22X', 'EMJSON'
    version: str  # '2016', '2019', '2022', '2025'
    building_type: str  # 'NR', 'MF', 'MIXED'
    ruleset: Optional[str] = None
    confidence: float = 1.0
    
    def __str__(self):
        return f"{self.format_type} v{self.version} ({self.building_type})"


class FormatDetector:
    """
    Automatically detect CBECC file format and version.
    
    Detection logic:
    - CIBD22: name attributes, CartesianPt elements
    - CIBD22X: <n> child elements, typed references
    - EMJSON: JSON format with schema_version
    """
    
    def detect(self, file_path: str) -> FormatInfo:
        """
        Detect format from file.
        
        Args:
            file_path: Path to file to analyze
            
        Returns:
            FormatInfo with detected format details
        """
        # Check if JSON (EMJSON)
        if file_path.endswith('.json') or file_path.endswith('.emjson'):
            return self._detect_json(file_path)
        
        # Parse as XML
        try:
            tree = ET.parse(file_path)
            root = tree.getroot()
        except Exception as e:
            raise ValueError(f"Cannot parse file as XML or JSON: {e}")
        
        # Extract ruleset
        ruleset = self._extract_ruleset(root)
        version = self._parse_version(ruleset)
        building_type = self._parse_building_type(ruleset, root)
        
        # Detect format type
        format_type = self._detect_format_type(root)
        
        # Calculate confidence
        confidence = self._calculate_confidence(root, format_type)
        
        return FormatInfo(
            format_type=format_type,
            version=version,
            building_type=building_type,
            ruleset=ruleset,
            confidence=confidence
        )
    
    def _detect_json(self, file_path: str) -> FormatInfo:
        """Detect EMJSON format"""
        import json
        with open(file_path) as f:
            data = json.load(f)
        
        schema_version = data.get('schema_version', '6.0')
        
        # Infer building type from content
        building_type = 'MIXED'
        if 'geometry' in data and 'zones' in data['geometry']:
            zones = data['geometry']['zones']
            if zones:
                if any(z.get('building_type') == 'MF' for z in zones):
                    building_type = 'MF'
                elif any(z.get('building_type') == 'NR' for z in zones):
                    building_type = 'NR'
        
        return FormatInfo(
            format_type='EMJSON',
            version=schema_version,
            building_type=building_type,
            confidence=1.0
        )
    
    def _extract_ruleset(self, root: ET.Element) -> Optional[str]:
        """Extract ruleset filename from XML"""
        # Try standard location
        ruleset_elem = root.find('.//RulesetFilename')
        if ruleset_elem is not None:
            return ruleset_elem.get('file') or ruleset_elem.text
        
        # Try alternate locations
        for elem in root.iter():
            if 'ruleset' in elem.tag.lower():
                return elem.get('file') or elem.text
        
        return None
    
    def _parse_version(self, ruleset: Optional[str]) -> str:
        """Extract version from ruleset filename"""
        if not ruleset:
            return 'unknown'
        
        # Look for year patterns
        patterns = [
            r'202[0-9]',  # 2020-2029
            r'201[6-9]',  # 2016-2019
        ]
        
        for pattern in patterns:
            match = re.search(pattern, ruleset)
            if match:
                return match.group()
        
        # Default to 2022 if can't determine
        return '2022'
    
    def _parse_building_type(self, ruleset: Optional[str], root: ET.Element) -> str:
        """Determine building type from ruleset or content"""
        if ruleset:
            ruleset_lower = ruleset.lower()
            if 'multifamily' in ruleset_lower or 'res' in ruleset_lower:
                return 'MF'
            elif 'nonresidential' in ruleset_lower or 'commercial' in ruleset_lower:
                return 'NR'
        
        # Check content
        has_res = root.find('.//ResZn') is not None or root.find('.//DwellUnit') is not None
        has_com = root.find('.//ComZn') is not None
        
        if has_res and has_com:
            return 'MIXED'
        elif has_res:
            return 'MF'
        elif has_com:
            return 'NR'
        
        return 'UNKNOWN'
    
    def _detect_format_type(self, root: ET.Element) -> str:
        """
        Detect CIBD22 vs CIBD22X format.
        
        CIBD22 indicators:
        - name attribute on objects: <ResZn name="Zone1">
        - CartesianPt elements present
        - Geometry as vertices
        
        CIBD22X indicators:
        - <n>Zone1</n> child elements
        - Typed references: ConsAssmRef, MatRef
        - Simplified geometry (area + orientation)
        """
        # Check for CIBD22 patterns
        cibd22_score = 0
        cibd22x_score = 0
        
        # Name attributes (CIBD22)
        for elem in root.iter():
            if elem.get('name') is not None:
                cibd22_score += 1
                if cibd22_score >= 5:  # Found enough evidence
                    break
        
        # CartesianPt (CIBD22 only)
        if root.find('.//CartesianPt') is not None:
            cibd22_score += 10
        
        # <n> elements (CIBD22X)
        n_elements = root.findall('.//n')
        if n_elements:
            cibd22x_score += len(n_elements[:5])  # Count first 5
        
        # Typed references (CIBD22X)
        typed_refs = ['ConsAssmRef', 'MatRef', 'WinTypeRef', 'DwellUnitTypeRef']
        for ref in typed_refs:
            if root.find(f'.//{ref}') is not None:
                cibd22x_score += 5
        
        # Property elements (CIBD22X has many)
        property_elements = ['Area', 'Az', 'Construction', 'Type']
        for prop in property_elements:
            elements = root.findall(f'.//{prop}')
            if len(elements) > 10:  # Many instances indicate CIBD22X
                cibd22x_score += 3
        
        # Decide based on scores
        if cibd22_score > cibd22x_score:
            return 'CIBD22'
        elif cibd22x_score > cibd22_score:
            return 'CIBD22X'
        else:
            # Default to CIBD22X if unclear
            return 'CIBD22X'
    
    def _calculate_confidence(self, root: ET.Element, format_type: str) -> float:
        """Calculate confidence in detection (0.0 to 1.0)"""
        indicators = 0
        matches = 0
        
        if format_type == 'CIBD22':
            indicators = 2
            if root.find('.//*[@name]') is not None:
                matches += 1
            if root.find('.//CartesianPt') is not None:
                matches += 1
        elif format_type == 'CIBD22X':
            indicators = 2
            if root.find('.//n') is not None:
                matches += 1
            if root.find('.//ConsAssmRef') is not None or root.find('.//MatRef') is not None:
                matches += 1
        
        return matches / indicators if indicators > 0 else 0.5


if __name__ == '__main__':
    # Test
    detector = FormatDetector()
    print("FormatDetector module loaded successfully")
