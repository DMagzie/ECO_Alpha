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
        Parse all Proj metadata properties.

        CBECC requires the Proj element for simulation. It contains:
        - Project identification (name, dates)
        - Location information (address, climate zone)
        - Analysis settings (compliance type, analysis type)
        - Software version information

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
            if child.text:
                metadata[tag] = child.text.strip()

        logger.info(f"Parsed {len(metadata)} project metadata properties")
        return metadata
