"""
CIBD25 Text Format Importer

Imports CIBD25 text files using:
1. CIBD22 text parser (same format structure)
2. CIBD22X modular parsers to extract data

CIBD25 uses identical text format to CIBD22 but with Title 24 2025 rulesets.
"""

from typing import Dict, Any
from pathlib import Path

from ..cibd22.text_parser import parse_cibd22_file  # Reuse CIBD22 text parser
from ..cibd22x.importer import CIBD22XImporter
from eco_tools.core.internal_repr import InternalRepresentation


class CIBD25Importer:
    """
    Importer for CIBD25 text format.

    Uses modular architecture:
    - Reuses CIBD22 text parser (identical format)
    - Delegates to CIBD22X parsers for data extraction
    - Adds 2025-specific metadata
    """

    def __init__(self):
        """Initialize CIBD25 importer."""
        self.diagnostics = []

    def import_file(self, file_path: str) -> InternalRepresentation:
        """
        Import CIBD25 text file to InternalRepresentation.

        Args:
            file_path: Path to CIBD25 text file

        Returns:
            InternalRepresentation populated with building data

        Raises:
            FileNotFoundError: If file doesn't exist
            Exception: For other import errors
        """
        # Validate file exists
        if not Path(file_path).exists():
            raise FileNotFoundError(f"CIBD25 file not found: {file_path}")

        try:
            # Stage 1: Parse text format to XML (same as CIBD22)
            self.diagnostics.append({
                "level": "info",
                "code": "I-CIBD25-PARSE-START",
                "message": "Parsing CIBD25 text format (Title 24 2025)",
                "stage": "parse",
                "source": "cibd25_importer"
            })

            xml_root = parse_cibd22_file(file_path)  # Reuse CIBD22 parser

            self.diagnostics.append({
                "level": "info",
                "code": "I-CIBD25-PARSE-COMPLETE",
                "message": f"Parsed CIBD25 text to XML structure ({len(list(xml_root))} top-level elements)",
                "stage": "parse",
                "source": "cibd25_importer"
            })

            # Stage 2: Use CIBD22X importer with the XML tree
            cibd22x_importer = CIBD22XImporter()
            internal = cibd22x_importer.import_from_xml_root(xml_root)

            # Merge diagnostics
            internal.diagnostics = self.diagnostics + internal.diagnostics

            # Add metadata about source format
            internal.metadata["source_format"] = "CIBD25"
            internal.metadata["title_24_version"] = "2025"
            internal.metadata["converted_via"] = "cibd22_text_parser → cibd22x_modular_parser"

            self.diagnostics.append({
                "level": "info",
                "code": "I-CIBD25-IMPORT-COMPLETE",
                "message": f"Imported {len(internal.zones)} zones, {len(internal.surfaces)} surfaces (Title 24 2025)",
                "stage": "import",
                "source": "cibd25_importer"
            })

            return internal

        except Exception as e:
            import traceback
            self.diagnostics.append({
                "level": "error",
                "code": "E-CIBD25-IMPORT-FAILED",
                "message": f"CIBD25 import failed: {str(e)}",
                "stage": "import",
                "context": traceback.format_exc(),
                "source": "cibd25_importer"
            })
            raise
