"""
Unified CIBD Text Format Writer

Writes EMJSON to both CIBD22 and CIBD25 text formats.

Both formats use identical structure:
- Objects: ObjectType "name"
- Properties: key = value
- Arrays: key[index] = value
- Terminators: ".."

The main differences are:
- RulesetFilename version
- Software version strings
- Some element/property name mappings
"""

from typing import Dict, Any, List, Optional
import logging
import time

from .version_config import (
    CIBDVersion,
    RULESET_FILES,
    SOFTWARE_VERSIONS,
    RUN_TITLES,
    get_export_element_name,
)

# Import the existing DirectWriter for CIBD25 export
from ..cibd25.direct_writer import CIBD25DirectWriter
from ..cibd25.property_rules import VERSION_MARKERS

logger = logging.getLogger(__name__)


class CIBDTextWriter:
    """
    Unified writer for CIBD text formats (CIBD22 and CIBD25).

    Uses the existing DirectWriter infrastructure but adds version-specific
    configuration for CIBD22 output.
    """

    def __init__(self, emjson_data: Dict[str, Any], version: CIBDVersion = CIBDVersion.CIBD25):
        """
        Initialize writer with EMJSON data.

        Args:
            emjson_data: EMJSON v6 formatted dictionary
            version: Target output version (default: CIBD25)
        """
        self.emjson = emjson_data
        self.version = version
        self.output_lines: List[str] = []

        # Version-specific settings
        self.ruleset_file = RULESET_FILES[version]
        self.software_version = SOFTWARE_VERSIONS[version]
        self.run_title = RUN_TITLES[version]

    def write_file(self, output_path: str) -> bool:
        """
        Write CIBD file.

        Args:
            output_path: Path to output file

        Returns:
            True if successful, False otherwise
        """
        try:
            if self.version == CIBDVersion.CIBD25:
                # Use existing DirectWriter for CIBD25
                return self._write_cibd25(output_path)
            else:
                # Use modified writer for CIBD22
                return self._write_cibd22(output_path)

        except Exception as e:
            logger.error(f"Failed to write CIBD file: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return False

    def _write_cibd25(self, output_path: str) -> bool:
        """
        Write CIBD25 format using existing DirectWriter.

        Args:
            output_path: Path to output file

        Returns:
            True if successful
        """
        writer = CIBD25DirectWriter(self.emjson)
        return writer.write_file(output_path)

    def _write_cibd22(self, output_path: str) -> bool:
        """
        Write CIBD22 format.

        Uses the DirectWriter infrastructure but with CIBD22-specific
        version markers and ruleset.

        Args:
            output_path: Path to output file

        Returns:
            True if successful
        """
        # Create a modified EMJSON with CIBD22 version markers
        emjson_22 = self._prepare_emjson_for_cibd22()

        # Use DirectWriter but intercept and modify the output
        writer = CIBD25DirectWriter(emjson_22)

        # Build output
        writer._ensure_commercial_catalogs()
        writer._write_ruleset_custom(self.ruleset_file)
        writer._write_proj_custom(self.run_title, self.software_version)
        writer._write_res_proj()

        # The rest is the same as CIBD25
        writer._write_catalog()
        writer._write_building()
        writer._write_dwelling_unit_types()
        writer._write_commercial_hvac()
        writer._write_hvac_systems()
        writer._write_pv_arrays()
        writer._write_batteries()
        writer._write_lighting_systems()

        # Write to file with Windows line endings
        with open(output_path, 'w', newline='') as f:
            f.write('\r\n'.join(writer.output_lines))

        logger.info(f"Successfully wrote CIBD22 file: {output_path}")
        return True

    def _prepare_emjson_for_cibd22(self) -> Dict[str, Any]:
        """
        Prepare EMJSON for CIBD22 export.

        Modifies version markers and any properties that differ between versions.

        Returns:
            Modified EMJSON dictionary
        """
        # Deep copy to avoid modifying original
        import copy
        emjson = copy.deepcopy(self.emjson)

        # Update proj_metadata with CIBD22 version info
        proj_metadata = emjson.get('proj_metadata', {})
        proj_metadata['_target_version'] = '2022'

        emjson['proj_metadata'] = proj_metadata

        return emjson


def _patch_direct_writer():
    """
    Add custom methods to DirectWriter for version flexibility.

    This patches the DirectWriter class to add methods that allow
    custom version markers without modifying the original file.
    """
    def _write_ruleset_custom(self, ruleset_file: str) -> None:
        """Write RulesetFilename with custom ruleset."""
        self.output_lines.append(f'RulesetFilename   "{ruleset_file}"')
        self.output_lines.append('')

    def _write_proj_custom(self, run_title: str, software_version: str) -> None:
        """Write Proj element with custom version markers."""
        import time

        project = self.emjson.get('project', {})
        location = project.get('location', {})

        current_timestamp = int(time.time())
        proj_name = project.get('name', 'Building')

        self.output_lines.append(f'Proj   "{proj_name}"')
        self.output_lines.append(f'   BldgEngyModelVersion = 17')
        self.output_lines.append(f'   CreateDate = {current_timestamp}')
        self.output_lines.append(f'   ModDate = {current_timestamp}')

        # Detect geometry type
        geometry_type = self._detect_geometry_type()
        if geometry_type == 'Simplified':
            self.output_lines.append(f'   GeometryInpType = "Simplified"')

        self.output_lines.append(f'   City = "{location.get("city", "City")}"')

        zip_code = location.get('zip_code', 94102)
        self.output_lines.append(f'   ZipCode = {zip_code}')

        self.output_lines.append(f'   RunTitle = "{run_title}"')
        self.output_lines.append(f'   SoftwareVersion = "{software_version}"')
        self.output_lines.append(f'   CompReportPDF = 1')
        self.output_lines.append(f'   CompReportXML = 1')
        self.output_lines.append(f'   ResultsCurrentMessage = "(not current)"')

        self.output_lines.append('   ..')
        self.output_lines.append('')

    # Patch the DirectWriter class
    CIBD25DirectWriter._write_ruleset_custom = _write_ruleset_custom
    CIBD25DirectWriter._write_proj_custom = _write_proj_custom


# Apply patches on module load
_patch_direct_writer()


def write_cibd_file(
    emjson: Dict[str, Any],
    output_path: str,
    version: CIBDVersion = CIBDVersion.CIBD25
) -> bool:
    """
    Write EMJSON to CIBD text file.

    Args:
        emjson: EMJSON v6 data
        output_path: Path to output file
        version: Target version (CIBD22 or CIBD25)

    Returns:
        True if successful, False otherwise
    """
    writer = CIBDTextWriter(emjson, version)
    return writer.write_file(output_path)
