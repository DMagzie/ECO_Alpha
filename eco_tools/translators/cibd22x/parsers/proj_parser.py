"""
Proj Parser - Project Metadata Parser
=====================================

PURPOSE:
Extracts CBECC project metadata from CIBD22X XML.
This metadata is REQUIRED for CBECC-Com simulation.

CRITICAL PROPERTIES:
- Name: Project name
- BldgEngyModelVersion: CBECC version
- CreateDate, ModDate, RunDate: Timestamps
- GeometryInpType: Simplified vs Detailed
- StAddress, City, State, ZipCode: Project location
- ClimateZone, WeatherStation: Climate data
- ComplianceType, AnalysisType: Simulation parameters

PATTERN: Simple metadata extractor (no dependencies)
"""

from typing import Dict, Any, Optional
import xml.etree.ElementTree as ET
import logging

from .base_parser import BaseParser

# Get module logger
logger = logging.getLogger('eco_tools.parsers')


class ProjParser(BaseParser):
    """Parser for CBECC22X Proj (project metadata) element"""

    def parse_proj_metadata(self, root: ET.Element) -> Dict[str, Any]:
        """
        Parse all Proj metadata properties including nested elements.

        CBECC requires the Proj element for simulation. It contains:
        - Project identification (name, dates)
        - Location information (address, climate zone)
        - Analysis settings (compliance type, analysis type)
        - Software version information
        - Nested objects: ResProj (residential compliance)

        Args:
            root: Root XML element

        Returns:
            Dictionary of all Proj properties (preserves all for round-trip)
        """
        metadata = {}

        # Find Proj element (namespace-aware)
        proj_elem = None
        for elem in root.iter():
            if self._local_tag(elem.tag) == 'Proj':
                proj_elem = elem
                break

        if proj_elem is None:
            logger.warning("No Proj element found - file may not simulate in CBECC")
            return metadata

        # Extract ALL child properties for complete round-trip fidelity
        # CBECC has dozens of Proj properties, we preserve them all
        for child in proj_elem:
            tag = self._local_tag(child.tag)

            # Handle nested elements (ResProj, ProjVar, etc.)
            if tag in ['ResProj', 'ProjVar', 'DwellUnitType']:
                metadata[tag] = self._parse_nested_element(child)
            # Handle simple properties
            elif child.text and child.text.strip():
                metadata[tag] = child.text.strip()
            # Handle empty child markers (child elements present but not parsed yet)
            else:
                metadata[tag] = ""

        logger.info(f"Parsed {len(metadata)} project metadata properties")
        return metadata

    def _parse_nested_element(self, elem: ET.Element) -> Dict[str, Any]:
        """
        Parse a nested element like ResProj into a dictionary.

        Args:
            elem: XML element to parse

        Returns:
            Dictionary of all properties in the nested element
        """
        result = {}

        # Extract all child properties
        for child in elem:
            tag = self._local_tag(child.tag)
            if child.text and child.text.strip():
                result[tag] = child.text.strip()
            else:
                result[tag] = ""

        return result
