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
from .direct_writer import CIBD25DirectWriter

logger = logging.getLogger('eco_tools.exporters')


class CIBD25Exporter:
    """
    Exporter for CIBD25 (Title 24 2025) format.

    Uses DirectWriter for .cibd25 text format (preferred).
    Falls back to CIBD22X wrapper for XML format.
    """

    def __init__(self):
        """Initialize CIBD25 exporter with both direct writer and CIBD22X fallback."""
        self.cibd22x_exporter = CIBD22XExporter()
        self.direct_writer = None  # Created on demand

    def export(self, internal: InternalRepresentation, output_path: str = None) -> ET.Element:
        """
        Export InternalRepresentation to CIBD25 format (text or XML).

        Args:
            internal: InternalRepresentation with building data
            output_path: Optional path to write file (.cibd25 for text, .xml for XML)

        Returns:
            XML Element root with CIBD25-compliant structure (or None if using DirectWriter)
        """
        # First, ensure proj_metadata has 2025-specific values
        self._ensure_2025_metadata(internal)

        # Write to file if path provided
        if output_path:
            path_obj = Path(output_path)

            if path_obj.suffix == '.cibd25':
                # Use DirectWriter for .cibd25 text format (preferred method)
                logger.info(f"Using DirectWriter for CIBD25 export to {output_path}")

                # Convert InternalRepresentation to EMJSON format
                emjson = self._internal_to_emjson(internal)

                # Use DirectWriter
                writer = CIBD25DirectWriter(emjson)
                success = writer.write_file(output_path)

                if success:
                    logger.info(f"Exported CIBD25 text format to {output_path}")
                else:
                    logger.error(f"Failed to export CIBD25 to {output_path}")

                return None  # DirectWriter doesn't return XML Element
            else:
                # Export as XML format (.xml) - use legacy CIBD22X wrapper
                logger.info(f"Using CIBD22X wrapper for XML export to {output_path}")
                root = self.cibd22x_exporter.export_to_element(internal)
                ruleset = internal.proj_metadata.get('RulesetFilename', 'T24_2025.bin')
                root.set('RulesetFilename', ruleset)

                tree = ET.ElementTree(root)
                ET.indent(tree, space="  ", level=0)
                tree.write(output_path, encoding='utf-8', xml_declaration=True)
                logger.info(f"Exported CIBD25 XML to {output_path}")
                return root
        else:
            # No output path - return XML element
            root = self.cibd22x_exporter.export_to_element(internal)
            ruleset = internal.proj_metadata.get('RulesetFilename', 'T24_2025.bin')
            root.set('RulesetFilename', ruleset)
            return root

    def _internal_to_emjson(self, internal: InternalRepresentation) -> Dict[str, Any]:
        """
        Convert InternalRepresentation to EMJSON format for DirectWriter.

        Args:
            internal: InternalRepresentation with building data

        Returns:
            EMJSON dictionary suitable for CIBD25DirectWriter
        """
        def to_dict(obj):
            """Convert object to dict if needed."""
            if isinstance(obj, dict):
                return obj
            return vars(obj)

        # Build EMJSON structure matching what DirectWriter expects
        # Extract project name from various possible fields
        proj_name = (
            internal.proj_metadata.get('name') or
            internal.proj_metadata.get('proj_name') or
            internal.proj_metadata.get('ProjName') or
            internal.proj_metadata.get('title') or
            'Unnamed Project'
        )

        emjson = {
            'project': {
                'name': proj_name,
                'ruleset_filename': internal.proj_metadata.get('RulesetFilename', 'T24_2025.bin'),
                'software_version': internal.proj_metadata.get('SoftwareVersion', 'CBECC 2025.2.0 (1390)'),
                'create_date': internal.proj_metadata.get('CreateDate'),
                'mod_date': internal.proj_metadata.get('ModDate'),
                'run_title': internal.proj_metadata.get('RunTitle'),
                'weather_city': internal.proj_metadata.get('weather_city'),
                'weather_station': internal.proj_metadata.get('weather_station'),
                'climate_zone': internal.proj_metadata.get('climate_zone'),
                'building_type': internal.proj_metadata.get('building_type'),
            },
            'geometry': {
                'zones': [to_dict(z) for z in internal.zones],
                'surfaces': [to_dict(s) for s in internal.surfaces],
                'zone_groups': [to_dict(zg) for zg in internal.zone_groups],
                'openings': [to_dict(o) for o in internal.openings],
            },
            'catalogs': {
                'Mat': [to_dict(m) for m in internal.materials],
                'ConsAssm': [to_dict(c) for c in internal.constructions],
                'FenCons': [],  # Will be populated from window_types
                'window_types': [to_dict(wt) for wt in internal.window_types],
                'du_types': [to_dict(dt) for dt in internal.du_types],
            },
            # HVAC catalog components at root level (DirectWriter expects them there)
            'heat_pumps': [to_dict(hp) for hp in internal.heat_pumps],
            'fan_systems': [to_dict(fs) for fs in internal.fan_systems],
            'distribution_systems': [to_dict(ds) for ds in internal.distribution_systems],
            'iaq_fans': [to_dict(iaq) for iaq in internal.iaq_fans],
            # Systems at root level
            'systems': {
                'hvac': [to_dict(h) for h in internal.hvac_systems],
                'dhw': [to_dict(d) for d in internal.dhw_systems],
                'water_heaters': [to_dict(wh) for wh in internal.water_heaters],
            },
            'pv_arrays': [to_dict(pv) for pv in internal.pv_arrays],
            'batteries': [to_dict(b) for b in internal.battery_systems],
            # Include metadata (contains commercial_hvac_components and other extras)
            'metadata': internal.metadata,
        }

        # Debug: check if commercial HVAC components are in metadata
        logger.info(f"DEBUG: internal.metadata keys = {list(internal.metadata.keys())}")
        if 'commercial_hvac_components' in internal.metadata:
            comp_hvac = internal.metadata['commercial_hvac_components']
            total = sum(len(v) for v in comp_hvac.values())
            logger.info(f"DEBUG: Found {total} commercial HVAC components in metadata")
        else:
            logger.warning("DEBUG: No commercial_hvac_components in internal.metadata")

        return emjson

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
