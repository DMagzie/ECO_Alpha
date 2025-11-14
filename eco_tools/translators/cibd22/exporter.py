"""
CIBD22 Text Format Exporter

Exports InternalRepresentation to CIBD22 text format using:
1. CIBD22X exporter to generate XML structure
2. XML-to-text converter to create CIBD22 text format

This approach reuses the robust CIBD22X exporter modules rather than duplicating logic.
"""

import tempfile
import os
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Optional
import logging

from eco_tools.core.internal_repr import InternalRepresentation
from ..cibd22x.exporter import CIBD22XExporter
from ..cibd_xml_to_text import convert_xml_to_text

logger = logging.getLogger(__name__)


class CIBD22Exporter:
    """
    Exporter for CIBD22 text format (Title 24 2022).

    Uses modular architecture:
    - Delegates to CIBD22X exporter for XML generation
    - Converts XML to CIBD22 text format
    - Ensures Title 24 2022 metadata
    """

    def __init__(self):
        """Initialize CIBD22 exporter."""
        self.cibd22x_exporter = CIBD22XExporter()

    def export(self, internal: InternalRepresentation, output_path: Optional[str] = None) -> ET.Element:
        """
        Export InternalRepresentation to CIBD22 text format.

        Args:
            internal: InternalRepresentation to export
            output_path: Optional path to write CIBD22 text file

        Returns:
            ET.Element: XML root element (for intermediate processing)

        Side Effects:
            If output_path provided, writes CIBD22 text file
        """
        # Ensure Title 24 2022 metadata
        self._ensure_2022_metadata(internal)

        # Generate XML using CIBD22X exporter
        root = self.cibd22x_exporter.export_to_element(internal)

        # Set root attribute for Title 24 2022
        ruleset = internal.proj_metadata.get('RulesetFilename', 'T24N_2022.bin')
        if '2025' in ruleset:
            ruleset = 'T24N_2022.bin'  # Force 2022 ruleset for CIBD22
        root.set('RulesetFilename', ruleset)

        # Write to file if path provided
        if output_path:
            path_obj = Path(output_path)

            # Create temp XML file for conversion
            with tempfile.NamedTemporaryFile(mode='w', suffix='.xml', delete=False) as tmp:
                tmp_path = tmp.name

            try:
                # Write XML to temp file
                tree = ET.ElementTree(root)
                ET.indent(tree, space="  ", level=0)
                tree.write(tmp_path, encoding='utf-8', xml_declaration=True)

                # Convert XML to CIBD22 text format
                convert_xml_to_text(tmp_path, output_path)

                logger.info(f"Exported CIBD22 text format to {output_path}")

            finally:
                # Clean up temp file
                if os.path.exists(tmp_path):
                    os.unlink(tmp_path)

        return root

    def export_to_element(self, internal: InternalRepresentation) -> ET.Element:
        """
        Export to XML Element without writing to file.

        Args:
            internal: InternalRepresentation to export

        Returns:
            ET.Element: XML root element
        """
        return self.export(internal, output_path=None)

    def _ensure_2022_metadata(self, internal: InternalRepresentation):
        """
        Ensure InternalRepresentation has Title 24 2022 metadata.

        Args:
            internal: InternalRepresentation to update
        """
        # Set RulesetFilename for Title 24 2022
        if 'RulesetFilename' not in internal.proj_metadata:
            internal.proj_metadata['RulesetFilename'] = 'T24N_2022.bin'
        elif '2025' in str(internal.proj_metadata.get('RulesetFilename', '')):
            internal.proj_metadata['RulesetFilename'] = 'T24N_2022.bin'

        # Set SoftwareVersion for CBECC 2022
        if 'SoftwareVersion' not in internal.proj_metadata or \
           '2025' in str(internal.proj_metadata.get('SoftwareVersion', '')):
            internal.proj_metadata['SoftwareVersion'] = 'CBECC 2022.2.0 (1148)'

        # Set BldgEngyModelVersion for 2022 format
        if 'BldgEngyModelVersion' not in internal.proj_metadata:
            internal.proj_metadata['BldgEngyModelVersion'] = '16'  # v16 for Title 24 2022


def export_cibd22(internal: InternalRepresentation, output_path: str):
    """
    Convenience function to export InternalRepresentation to CIBD22 text file.

    Args:
        internal: InternalRepresentation to export
        output_path: Path to write CIBD22 text file
    """
    exporter = CIBD22Exporter()
    exporter.export(internal, output_path)
    logger.info(f"Exported CIBD22 to {output_path}")
