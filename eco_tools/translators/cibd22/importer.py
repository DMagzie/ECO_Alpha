"""
CIBD22 Text Format Importer

Imports CIBD22 text files using:
1. Text parser to convert to XML structure
2. CIBD22X modular parsers to extract data

This approach reuses the robust CIBD22X parser modules rather than duplicating logic.
"""

from typing import Dict, Any
from pathlib import Path

from .text_parser import parse_cibd22_file
from ..cibd22x.importer import CIBD22XImporter
from eco_tools.core.internal_repr import InternalRepresentation


class CIBD22Importer:
    """
    Importer for CIBD22 text format.

    Uses modular architecture:
    - Parses text format to XML ElementTree
    - Delegates to CIBD22X parsers for data extraction
    """

    def __init__(self):
        """Initialize CIBD22 importer."""
        self.diagnostics = []

    def import_file(self, file_path: str) -> InternalRepresentation:
        """
        Import CIBD22 text file to InternalRepresentation.

        Args:
            file_path: Path to CIBD22 text file

        Returns:
            InternalRepresentation populated with building data

        Raises:
            FileNotFoundError: If file doesn't exist
            Exception: For other import errors
        """
        # Validate file exists
        if not Path(file_path).exists():
            raise FileNotFoundError(f"CIBD22 file not found: {file_path}")

        try:
            # Stage 1: Parse text format to XML
            self.diagnostics.append({
                "level": "info",
                "code": "I-CIBD22-PARSE-START",
                "message": "Parsing CIBD22 text format",
                "stage": "parse",
                "source": "cibd22_importer"
            })

            xml_root = parse_cibd22_file(file_path)

            self.diagnostics.append({
                "level": "info",
                "code": "I-CIBD22-PARSE-COMPLETE",
                "message": f"Parsed CIBD22 text to XML structure ({len(list(xml_root))} top-level elements)",
                "stage": "parse",
                "source": "cibd22_importer"
            })

            # Stage 2: Use CIBD22X importer with the XML tree
            # Create a temporary ElementTree-compatible object
            cibd22x_importer = CIBD22XImporter()

            # Pass the root element directly - CIBD22X importer expects ElementTree root
            internal = cibd22x_importer.import_from_xml_root(xml_root)

            # Merge diagnostics
            internal.diagnostics = self.diagnostics + internal.diagnostics

            # Add metadata about source format
            internal.metadata["source_format"] = "CIBD22"
            internal.metadata["converted_via"] = "text_parser → cibd22x_modular_parser"

            self.diagnostics.append({
                "level": "info",
                "code": "I-CIBD22-IMPORT-COMPLETE",
                "message": f"Imported {len(internal.zones)} zones, {len(internal.surfaces)} surfaces",
                "stage": "import",
                "source": "cibd22_importer"
            })

            return internal

        except Exception as e:
            import traceback
            self.diagnostics.append({
                "level": "error",
                "code": "E-CIBD22-IMPORT-FAILED",
                "message": f"CIBD22 import failed: {str(e)}",
                "stage": "import",
                "context": traceback.format_exc(),
                "source": "cibd22_importer"
            })
            raise
