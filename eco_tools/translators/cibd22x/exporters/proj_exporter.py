"""
Proj Exporter - Project Metadata Exporter
=========================================

PURPOSE:
Exports CBECC project metadata to CIBD22X XML.
This metadata is REQUIRED for CBECC-Com simulation.

CRITICAL PROPERTIES:
The Proj element must contain ALL properties from the original file
for CBECC to run simulations correctly. We preserve all metadata
from the proj_metadata dictionary for complete round-trip fidelity.

REQUIRED PROPERTIES (minimum for simulation):
- Name: Project name
- BldgEngyModelVersion: CBECC version (e.g., "17")
- GeometryInpType: "Simplified" or "Detailed"
- CreateDate, ModDate: Timestamps
- ClimateZone or WeatherStation: Climate data

EXPORT STRATEGY:
Write ALL properties from proj_metadata dictionary to preserve
complete round-trip fidelity. CBECC has dozens of optional Proj
properties, and we don't want to lose any on export.
"""

import xml.etree.ElementTree as ET
from typing import Dict, Any
import logging

logger = logging.getLogger('eco_tools.exporters')


class ProjExporter:
    """Exporter for CBECC22X Proj (project metadata) element"""

    def export_proj(self, parent: ET.Element, proj_metadata: Dict[str, Any]) -> ET.Element:
        """
        Export project metadata to Proj element.

        CBECC requires the Proj element for simulation. Without it,
        files will open in CBECC but cannot run simulations.

        Args:
            parent: Parent XML element (typically root <SDDXML>)
            proj_metadata: Dictionary of all Proj properties

        Returns:
            The created Proj element (so caller can nest Bldg inside it)
        """
        if not proj_metadata:
            logger.warning("No project metadata - creating minimal Proj element")
            proj_metadata = self._create_minimal_proj_metadata()

        # Create Proj element
        proj_elem = ET.SubElement(parent, 'Proj')

        # List of properties to skip (these are container elements, not metadata)
        # CRITICAL: These properties exist in original files as empty placeholders
        # but are actually nested XML structures that we export separately
        SKIP_PROPERTIES = {
            'Bldg',         # Building geometry - nested structure we create separately
            'Batt',         # Battery systems - empty placeholder
            'PVArray',      # PV arrays - empty placeholder
            'FluidSys',     # Fluid systems - empty placeholder
            'EUseSummary',  # Energy use summary - output only
            'ResProj',      # Residential project - empty placeholder
            'SchDay',       # Schedule day - empty placeholder
        }

        # Export ALL properties EXCEPT containers
        # Properties are written in alphabetical order for consistency
        exported_count = 0
        for key in sorted(proj_metadata.keys()):
            if key in SKIP_PROPERTIES:
                continue  # Skip container/placeholder properties

            value = proj_metadata[key]
            if value is not None:
                prop_elem = ET.SubElement(proj_elem, key)
                prop_elem.text = str(value)
                exported_count += 1

        logger.info(f"Exported Proj with {exported_count} properties (skipped {len(SKIP_PROPERTIES)} containers)")
        return proj_elem

    def _create_minimal_proj_metadata(self) -> Dict[str, Any]:
        """
        Create minimal Proj metadata for files without metadata.

        This provides enough metadata for CBECC to attempt simulation,
        though results may not be accurate without proper climate zone, etc.

        Returns:
            Dictionary with minimal required Proj properties
        """
        import time

        return {
            'Name': 'Untitled Project',
            'BldgEngyModelVersion': '17',  # CBECC 2022 version
            'CreateDate': str(int(time.time())),
            'ModDate': str(int(time.time())),
            'GeometryInpType': 'Simplified',
            'ClimateZone': '6',  # Default to CZ6 (reasonable for CA)
        }
