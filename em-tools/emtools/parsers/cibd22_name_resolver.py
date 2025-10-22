# FILE: em-tools/emtools/parsers/cibd22_name_resolver.py
# ============================================================================
"""
CIBD22 Name-Based Relationship Resolution

This module contains all heuristic logic for resolving parent-child relationships
in CIBD22 format. Since CIBD22 uses a flat structure with relationships encoded
only in object names, heuristics are unavoidable.

All functions explicitly document their heuristic assumptions and include
confidence scoring and validation.

CIBD22 Format Limitation:
    The CIBD22 format stores all objects (zones, surfaces, openings) at the
    same indentation level with no explicit reference fields. Parent-child
    relationships are encoded only through naming conventions.
    
Common Patterns:
    - Surface: "ExtWall (Front 1) : ZoneName"
    - Opening: "Window (Front 1) : ZoneName"
    - Separator: " : " (standard convention)
"""

from __future__ import annotations
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass


@dataclass
class ResolutionResult:
    """Result of heuristic name resolution."""
    resolved_id: Optional[str]
    confidence: float  # 0.0 to 1.0
    strategy_used: str
    warnings: List[str]


class CIBD22NameResolver:
    """
    Heuristic resolver for CIBD22 name-based relationships.
    
    CIBD22 Format Limitation:
        The CIBD22 format stores all objects (zones, surfaces, openings) at the
        same indentation level with no explicit reference fields. Parent-child
        relationships are encoded only through naming conventions.
        
    Common Patterns:
        - Surface: "ExtWall (Front 1) : ZoneName"
        - Opening: "Window (Front 1) : ZoneName"  
        - Separator: " : " (standard convention)
        
    Heuristic Nature:
        All resolution methods in this class use heuristics because CIBD22
        provides no explicit reference fields. The methods attempt to match
        objects by parsing their names according to observed conventions.
    """
    
    def __init__(self, diagnostics: List[Dict[str, Any]]):
        """
        Initialize resolver with diagnostic list.
        
        Args:
            diagnostics: List to append diagnostic messages
        """
        self.diagnostics = diagnostics
        self.zone_separator = " : "
        
    def resolve_zone_from_name(
        self,
        name: str,
        zone_name_to_id: Dict[str, str]
    ) -> ResolutionResult:
        """
        Resolve zone ID from object name using naming convention with multiple fallback strategies.
        
        Heuristic Assumption:
            Zone name appears after " : " separator in the object name.
            Example: "ExtWall (Front 1) : B2.6_127" → zone name is "B2.6_127"
            
        Strategies (in order of execution):
            1. Exact match after separator
            2. Case-insensitive match
            3. Space-normalized match (handles spacing variations)
            4. Pattern-based suffix match (handles name prefix changes like Corridor→Breezeway)
            5. Segment number stripping (handles "Zone_L01 2" → "Zone_L01")
            
        Args:
            name: Object name (surface or opening)
            zone_name_to_id: Mapping of zone names to zone IDs
            
        Returns:
            ResolutionResult with resolved ID, confidence, and warnings
            
        Confidence Levels:
            1.0 = Exact separator match with zone found
            0.9 = Segment number stripped
            0.8 = Case-insensitive match
            0.75 = Space-normalized match
            0.65 = Pattern-based suffix match (single candidate)
            0.5 = Pattern-based suffix match (ambiguous, first selected)
            0.0 = No match found
        """
        warnings = []
        
        # Strategy 1: Standard separator with exact match
        if self.zone_separator in name:
            zone_name = name.split(self.zone_separator)[-1].strip()
            zone_id = zone_name_to_id.get(zone_name)
            
            if zone_id:
                return ResolutionResult(
                    resolved_id=zone_id,
                    confidence=1.0,
                    strategy_used="exact_separator_match",
                    warnings=[]
                )
            else:
                warnings.append(f"Zone name '{zone_name}' not found in zone registry")
        else:
            warnings.append(f"Name pattern doesn't contain standard separator '{self.zone_separator}'")
        
        # Strategy 2: Case-insensitive fallback
        if self.zone_separator in name:
            zone_name = name.split(self.zone_separator)[-1].strip().lower()
            for zn, zid in zone_name_to_id.items():
                if zn.lower() == zone_name:
                    warnings.append("Used case-insensitive matching")
                    self._add_diagnostic(
                        "info",
                        "I-RESOLVER-CASE-INSENSITIVE",
                        f"Case-insensitive zone match for: {name}",
                        {"object_name": name, "zone_matched": zn}
                    )
                    return ResolutionResult(
                        resolved_id=zid,
                        confidence=0.8,
                        strategy_used="case_insensitive_match",
                        warnings=warnings
                    )
        
        # Strategy 3: Space-normalized matching
        # Handle naming inconsistencies like "B2.0MTL_B 13" vs "B2.0 MTL_B 13"
        if self.zone_separator in name:
            zone_name_raw = name.split(self.zone_separator)[-1].strip()
            # Normalize by removing all spaces for comparison
            zone_name_normalized = zone_name_raw.replace(" ", "").lower()
            for zn, zid in zone_name_to_id.items():
                zn_normalized = zn.replace(" ", "").lower()
                if zn_normalized == zone_name_normalized:
                    warnings.append("Used space-normalized matching")
                    self._add_diagnostic(
                        "info",
                        "I-RESOLVER-SPACE-NORMALIZED",
                        f"Space-normalized zone match for: {name}",
                        {"object_name": name, "zone_matched": zn, "surface_ref": zone_name_raw}
                    )
                    return ResolutionResult(
                        resolved_id=zid,
                        confidence=0.75,
                        strategy_used="space_normalized_match",
                        warnings=warnings
                    )
        
        # Strategy 4: Pattern-based suffix matching
        # Handle data inconsistencies like "Corridor-1_L01" → "Breezeway-1_L01"
        # Match by suffix pattern (number + level indicator)
        if self.zone_separator in name:
            zone_name_raw = name.split(self.zone_separator)[-1].strip()
            
            # Extract suffix pattern: "-N_LNN" or similar
            # Common patterns: "-1_L01", "-2_L02", "_127", etc.
            import re
            suffix_match = re.search(r'[-_](\d+)(_L\d+)?$', zone_name_raw, re.IGNORECASE)
            
            if suffix_match:
                suffix_pattern = suffix_match.group(0)  # e.g., "-1_L01"
                
                # Find zones with matching suffix
                candidates = []
                for zn, zid in zone_name_to_id.items():
                    if zn.endswith(suffix_pattern) or zn.lower().endswith(suffix_pattern.lower()):
                        candidates.append((zn, zid))
                
                if len(candidates) == 1:
                    # Single match found - likely correct despite name prefix difference
                    warnings.append(f"Used pattern-based suffix matching: {suffix_pattern}")
                    self._add_diagnostic(
                        "info",
                        "I-RESOLVER-PATTERN-SUFFIX",
                        f"Pattern-based zone match for: {name}",
                        {
                            "object_name": name,
                            "surface_ref": zone_name_raw,
                            "zone_matched": candidates[0][0],
                            "suffix_pattern": suffix_pattern
                        }
                    )
                    return ResolutionResult(
                        resolved_id=candidates[0][1],
                        confidence=0.65,
                        strategy_used="pattern_suffix_match",
                        warnings=warnings
                    )
                elif len(candidates) > 1:
                    # Multiple matches - pick first but warn
                    warnings.append(f"Multiple zones match suffix pattern {suffix_pattern}: {[c[0] for c in candidates]}")
                    self._add_diagnostic(
                        "warning",
                        "W-RESOLVER-AMBIGUOUS-SUFFIX",
                        f"Ambiguous pattern-based zone match for: {name}",
                        {
                            "object_name": name,
                            "surface_ref": zone_name_raw,
                            "zones_matched": [c[0] for c in candidates],
                            "suffix_pattern": suffix_pattern,
                            "selected": candidates[0][0]
                        }
                    )
                    return ResolutionResult(
                        resolved_id=candidates[0][1],
                        confidence=0.5,
                        strategy_used="pattern_suffix_ambiguous",
                        warnings=warnings
                    )
        
        # Strategy 5: Strip trailing segment numbers
        # Handle interior wall segments like "Res_West Facing_L01 2" → "Res_West Facing_L01"
        # Surfaces may have segment numbers appended with space
        if self.zone_separator in name:
            zone_name_raw = name.split(self.zone_separator)[-1].strip()
            
            # Check if ends with space + digit(s)
            import re
            segment_match = re.search(r'^(.+?)\s+\d+$', zone_name_raw)
            
            if segment_match:
                zone_name_base = segment_match.group(1)  # Zone name without segment number
                zone_id = zone_name_to_id.get(zone_name_base)
                
                if zone_id:
                    warnings.append(f"Stripped segment number from zone reference")
                    self._add_diagnostic(
                        "info",
                        "I-RESOLVER-SEGMENT-STRIPPED",
                        f"Stripped segment number for zone match: {name}",
                        {
                            "object_name": name,
                            "surface_ref": zone_name_raw,
                            "zone_matched": zone_name_base
                        }
                    )
                    return ResolutionResult(
                        resolved_id=zone_id,
                        confidence=0.9,
                        strategy_used="segment_number_stripped",
                        warnings=warnings
                    )
        
        # No match found
        warnings.append(f"No zone found for name pattern: {name}")
        return ResolutionResult(
            resolved_id=None,
            confidence=0.0,
            strategy_used="no_match",
            warnings=warnings
        )
    
    def resolve_surface_from_opening(
        self,
        opening_name: str,
        surfaces_by_name: Dict[str, str],
        zone_id: Optional[str] = None
    ) -> ResolutionResult:
        """
        Resolve parent surface from opening name.
        
        Heuristic Assumptions:
            1. Opening and surface share zone suffix after " : "
            2. Orientation keyword (Front, Back, Left, Right) appears in both names
            3. If multiple matches, first one is correct
            
        Args:
            opening_name: Opening object name
            surfaces_by_name: Mapping of surface names to surface IDs
            zone_id: Optional zone ID to filter candidates
            
        Returns:
            ResolutionResult with resolved ID, confidence, and warnings
            
        Confidence Levels:
            1.0 = Single orientation match found
            0.8 = Zone suffix match with orientation
            0.5 = Zone suffix match only (fallback)
            0.0 = No match found
        """
        warnings = []
        
        # Extract zone suffix
        zone_suffix = None
        if self.zone_separator in opening_name:
            zone_suffix = opening_name.split(self.zone_separator)[-1].strip()
        else:
            warnings.append("Opening name doesn't contain zone separator")
            return ResolutionResult(None, 0.0, "no_separator", warnings)
        
        # Extract orientation keyword (Front, Back, Left, Right, etc.)
        orientation = self._extract_orientation(opening_name)
        
        # Filter surfaces by zone suffix
        candidates = []
        for surf_name, surf_id in surfaces_by_name.items():
            if zone_suffix and surf_name.endswith(self.zone_separator + zone_suffix):
                candidates.append((surf_name, surf_id))
        
        if not candidates:
            warnings.append(f"No surfaces found with zone suffix: {zone_suffix}")
            return ResolutionResult(None, 0.0, "no_candidates", warnings)
        
        # Match by orientation
        if orientation:
            oriented = [
                (sname, sid) for sname, sid in candidates
                if orientation.lower() in sname.lower()
            ]
            
            if len(oriented) == 1:
                return ResolutionResult(
                    oriented[0][1], 1.0, "orientation_match", []
                )
            elif len(oriented) > 1:
                warnings.append(f"Multiple surfaces match orientation '{orientation}'")
                self._add_diagnostic(
                    "warning",
                    "W-RESOLVER-AMBIGUOUS-SURFACE",
                    f"Ambiguous surface match for opening: {opening_name}",
                    {
                        "opening_name": opening_name,
                        "orientation": orientation,
                        "candidate_count": len(oriented)
                    }
                )
                return ResolutionResult(
                    oriented[0][1], 0.8, "ambiguous_orientation", warnings
                )
            else:
                warnings.append(f"No surfaces match orientation '{orientation}'")
        
        # Fallback: first candidate with matching zone
        warnings.append("Using first candidate surface (no orientation match)")
        self._add_diagnostic(
            "info",
            "I-RESOLVER-FALLBACK",
            f"Fallback surface match for opening: {opening_name}",
            {"opening_name": opening_name, "strategy": "first_candidate"}
        )
        return ResolutionResult(
            candidates[0][1], 0.5, "fallback_first", warnings
        )
    
    def _extract_orientation(self, name: str) -> Optional[str]:
        """
        Extract orientation keyword from name.
        
        Heuristic Assumption:
            Orientation appears in parentheses: "(Front 1)" or "(Right Side)"
            
        Args:
            name: Object name
            
        Returns:
            Orientation keyword or None
        """
        if "(" not in name:
            return None
        
        try:
            # Extract text between first ( and )
            paren_content = name.split("(")[1].split(")")[0]
            # First word is usually orientation
            parts = paren_content.split()
            if parts:
                return parts[0]  # "Front", "Back", "Left", "Right", etc.
        except (IndexError, AttributeError):
            pass
        
        return None
    
    def _add_diagnostic(
        self,
        level: str,
        code: str,
        message: str,
        context: Dict[str, Any]
    ) -> None:
        """Add diagnostic message to list."""
        self.diagnostics.append({
            "level": level,
            "code": code,
            "message": message,
            "context": context
        })


def resolve_zone_with_confidence(
    name: str,
    zone_name_to_id: Dict[str, str],
    diagnostics: List[Dict[str, Any]]
) -> Tuple[Optional[str], float]:
    """
    Convenience function to resolve zone and return (id, confidence).
    
    Args:
        name: Object name
        zone_name_to_id: Zone name mapping
        diagnostics: Diagnostic list
        
    Returns:
        Tuple of (zone_id, confidence_score)
    """
    resolver = CIBD22NameResolver(diagnostics)
    result = resolver.resolve_zone_from_name(name, zone_name_to_id)
    return result.resolved_id, result.confidence


def resolve_surface_with_confidence(
    opening_name: str,
    surfaces_by_name: Dict[str, str],
    diagnostics: List[Dict[str, Any]]
) -> Tuple[Optional[str], float]:
    """
    Convenience function to resolve parent surface and return (id, confidence).
    
    Args:
        opening_name: Opening name
        surfaces_by_name: Surface name mapping
        diagnostics: Diagnostic list
        
    Returns:
        Tuple of (surface_id, confidence_score)
    """
    resolver = CIBD22NameResolver(diagnostics)
    result = resolver.resolve_surface_from_opening(opening_name, surfaces_by_name)
    return result.resolved_id, result.confidence
