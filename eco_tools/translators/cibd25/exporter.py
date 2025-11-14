"""
CIBD25 Exporter - Title 24 2025 Compliance Export

Exports EMJSON v6 to CIBD25 format (text or XML) for CBECC 2025 2.0 simulation.

CIBD25 = CIBD22X structure + 2025 rulesets + updated metadata

KEY DIFFERENCES FROM CIBD22X:
- RulesetFilename: "T24_2025.bin" (vs T24N_2022.bin)
- SoftwareVersion: "CBECC 2025.2.0 (1390)" (for CBECC 2025 Version 2.0)
- BldgEngyModelVersion: 17 (same as 2022)

This exporter wraps the existing CIBD22X exporter and modifies the metadata
for Title 24 2025 compliance.

CIBD25 FORMAT SUPPORT:
- .cibd25 extension → Text format (CBECC native format)
- .xml extension → XML format (also supported by CBECC)

Note: CBECC 2025 Version 2.0 (build 1390) was released November 12, 2025.
"""

import xml.etree.ElementTree as ET
from typing import Dict, Any
from pathlib import Path
import logging
import tempfile

from eco_tools.core.internal_repr import InternalRepresentation
from ..cibd22x.exporter import CIBD22XExporter
from ..cibd_xml_to_text import convert_xml_to_text

logger = logging.getLogger('eco_tools.exporters')


class CIBD25Exporter:
    """
    Exporter for CIBD25 (Title 24 2025) XML format.

    Reuses CIBD22X architecture but ensures 2025-specific metadata.
    """

    def __init__(self):
        """Initialize CIBD25 exporter with CIBD22X infrastructure."""
        self.cibd22x_exporter = CIBD22XExporter()

    def export(self, internal: InternalRepresentation, output_path: str = None) -> ET.Element:
        """
        Export InternalRepresentation to CIBD25 format (text or XML).

        Args:
            internal: InternalRepresentation with building data
            output_path: Optional path to write file (.cibd25 for text, .xml for XML)

        Returns:
            XML Element root with CIBD25-compliant structure
        """
        # First, ensure proj_metadata has 2025-specific values
        self._ensure_2025_metadata(internal)

        # Use CIBD22X exporter to create XML structure
        root = self.cibd22x_exporter.export_to_element(internal)

        # Add RulesetFilename as root attribute (for text format compatibility)
        ruleset = internal.proj_metadata.get('RulesetFilename', 'T24_2025.bin')
        root.set('RulesetFilename', ruleset)

        # Write to file if path provided
        if output_path:
            path_obj = Path(output_path)

            if path_obj.suffix == '.cibd25':
                # Export as text format
                # First write temporary XML
                with tempfile.NamedTemporaryFile(mode='w', suffix='.xml', delete=False) as tmp:
                    tmp_path = tmp.name

                tree = ET.ElementTree(root)
                ET.indent(tree, space="  ", level=0)
                tree.write(tmp_path, encoding='utf-8', xml_declaration=True)

                # Convert XML to text
                convert_xml_to_text(tmp_path, output_path)

                # Clean up temp file
                import os
                os.unlink(tmp_path)

                logger.info(f"Exported CIBD25 text format to {output_path}")
            else:
                # Export as XML format (.xml)
                tree = ET.ElementTree(root)
                ET.indent(tree, space="  ", level=0)
                tree.write(output_path, encoding='utf-8', xml_declaration=True)
                logger.info(f"Exported CIBD25 XML to {output_path}")

        return root

    def _ensure_2025_metadata(self, internal: InternalRepresentation):
        """
        Ensure proj_metadata has Title 24 2025-specific values.

        This method modifies the InternalRepresentation in-place to ensure
        CBECC 2025.1.0 will recognize and simulate the file correctly.

        Args:
            internal: InternalRepresentation to modify
        """
        # Ensure RulesetFilename is set to 2025 version
        if 'RulesetFilename' not in internal.proj_metadata:
            internal.proj_metadata['RulesetFilename'] = 'T24_2025.bin'

        # Update or set SoftwareVersion to CBECC 2025
        if 'SoftwareVersion' not in internal.proj_metadata or '2022' in str(internal.proj_metadata.get('SoftwareVersion', '')):
            internal.proj_metadata['SoftwareVersion'] = 'CBECC 2025.2.0 (1390)'

        # Ensure BldgEngyModelVersion is set (same for both 2022 and 2025)
        if 'BldgEngyModelVersion' not in internal.proj_metadata:
            internal.proj_metadata['BldgEngyModelVersion'] = '17'

        # Add timestamp if missing
        if 'ModDate' not in internal.proj_metadata:
            import time
            internal.proj_metadata['ModDate'] = str(int(time.time()))

        logger.info("Updated project metadata for Title 24 2025 compliance")
        logger.debug(f"  RulesetFilename: {internal.proj_metadata.get('RulesetFilename')}")
        logger.debug(f"  SoftwareVersion: {internal.proj_metadata.get('SoftwareVersion')}")


def export_cibd25(internal: InternalRepresentation, output_path: str) -> str:
    """
    Export InternalRepresentation to CIBD25 XML file.

    Convenience function for direct file export.

    Args:
        internal: InternalRepresentation with building data
        output_path: Path to write CIBD25 XML file

    Returns:
        Path to written file
    """
    exporter = CIBD25Exporter()
    exporter.export(internal, output_path)
    return output_path
