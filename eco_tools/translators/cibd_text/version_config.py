"""
CIBD Text Format Version Configuration

Defines version-specific settings for CIBD22 and CIBD25 text formats.
Both formats share the same structure (property-based with ".." terminators)
but have different rulesets and some element/property name differences.
"""

from typing import Dict, Any, Set
from enum import Enum


class CIBDVersion(Enum):
    """Supported CIBD text format versions."""
    CIBD22 = "2022"
    CIBD25 = "2025"


# Ruleset filenames for each version
RULESET_FILES = {
    CIBDVersion.CIBD22: "T24_2022.bin",
    CIBDVersion.CIBD25: "T24_2025.bin",
}

# Software version strings for output
SOFTWARE_VERSIONS = {
    CIBDVersion.CIBD22: "CBECC 2022.3.0 (ECO Tools)",
    CIBDVersion.CIBD25: "CBECC 2025.2.0 (ECO Tools)",
}

# Run title markers
RUN_TITLES = {
    CIBDVersion.CIBD22: "Title 24 2022 Compliance",
    CIBDVersion.CIBD25: "Title 24 2025 Compliance",
}

# Element type mappings from source format to canonical names
# For CIBD text round-trip fidelity, residential elements preserve original names
# Key: source element name, Value: canonical EMJSON name
ELEMENT_TYPE_MAPPING = {
    # Common to both versions
    "Proj": "Proj",
    "ResProj": "ResProj",
    "ProjVar": "ProjVar",
    "Bldg": "Bldg",
    "Story": "Story",
    "Spc": "Spc",

    # Residential zones and groups - preserve original names for round-trip
    "ResZnGrp": "ResZnGrp",
    "ResZn": "ResZn",  # Preserve for round-trip (was ThrmlZn)
    "ResOtherZn": "ResOtherZn",
    "ResAttic": "ResAttic",

    # Surfaces - residential - preserve original names for round-trip
    "ResExtWall": "ResExtWall",
    "ResIntWall": "ResIntWall",
    "ResCeiling": "ResCeiling",
    "ResFloor": "ResFloor",
    "ResRoof": "ResRoof",
    "ResSlabFlr": "ResSlabFlr",
    "ResCathedralCeiling": "ResCathedralCeiling",
    "ResAtticRoof": "ResAtticRoof",
    "ResOtherFlr": "ResOtherFlr",
    "ResIntFlr": "ResIntFlr",
    "ResUndgrWall": "ResUndgrWall",
    "ResUndgrFlr": "ResUndgrFlr",
    "ResCeilingBelowAttic": "ResCeilingBelowAttic",

    # Surfaces - commercial
    "ExtWall": "ExtWall",
    "IntWall": "IntWall",
    "Roof": "Roof",
    "FlrOnGrade": "FlrOnGrade",
    "Ceiling": "Ceiling",
    "FlrAbvAttic": "FlrAbvAttic",
    "UndgrWall": "UndgrWall",
    "UndgrFlr": "UndgrFlr",
    "ExtFlr": "ExtFlr",
    "IntFlr": "IntFlr",
    "FlrBelowAttic": "FlrBelowAttic",

    # Openings - preserve original names for round-trip
    "ResWin": "ResWin",
    "Win": "Win",
    "ResDr": "ResDr",
    "Dr": "Dr",
    "ResSkylt": "ResSkylt",
    "Skylt": "Skylt",

    # Constructions and materials - preserve original names for round-trip
    "ResWinType": "ResWinType",
    "ResConsAssm": "ResConsAssm",
    "ConsAssm": "ConsAssm",
    "Mat": "Mat",
    "ResMat": "ResMat",
    "FenCons": "FenCons",

    # Dwelling units
    "DwellUnitType": "DwellUnitType",
    "DwellUnit": "DwellUnit",

    # HVAC Systems
    "HVACSys": "HVACSys",
    "ZnSys": "ZnSys",
    "AirSys": "AirSys",
    "AirSeg": "AirSeg",
    "CoilClg": "CoilClg",
    "CoilHtg": "CoilHtg",
    "Fan": "Fan",
    "TrmlUnit": "TrmlUnit",
    "OACtrl": "OACtrl",
    "FluidSys": "FluidSys",
    "FluidSeg": "FluidSeg",
    "Boiler": "Boiler",
    "Chiller": "Chiller",
    "HtRej": "HtRej",
    "Pump": "Pump",
    "VRFSys": "VRFSys",

    # DHW Systems
    "DHWSys": "DHWSys",
    "DHWHeater": "DHWHeater",
    "DHWLoop": "DHWLoop",

    # Other systems
    "PVArray": "PVArray",
    "Battery": "Battery",
    "IAQFan": "IAQFan",
    "IntLtgSys": "IntLtgSys",
    "Luminaire": "Luminaire",

    # Schedules
    "SchDay": "SchDay",
    "SchWeek": "SchWeek",
    "Sch": "Sch",
}

# Reverse mapping for export (canonical name to output format)
def get_export_element_name(canonical: str, version: CIBDVersion) -> str:
    """
    Get the output element name for a given canonical name and version.

    For now, both versions use the same element names.
    Future versions may require different mappings.
    """
    # Most elements use the same name in both versions
    return canonical


# Surface element types (for reorganization during import)
SURFACE_TYPES: Set[str] = {
    # Residential surfaces
    'ResExtWall', 'ResIntWall', 'ResSlabFlr', 'ResCathedralCeiling',
    'ResAtticRoof', 'ResOtherFlr', 'ResIntFlr', 'ResUndgrWall', 'ResUndgrFlr',
    'ResCeilingBelowAttic', 'ResRoof', 'ResCeiling',
    # Commercial surfaces
    'ExtWall', 'IntWall', 'Roof', 'FlrOnGrade', 'Ceiling', 'FlrAbvAttic',
    'UndgrWall', 'UndgrFlr', 'ExtFlr', 'IntFlr', 'FlrBelowAttic',
}

# Zone element types
ZONE_TYPES: Set[str] = {'ThrmlZn', 'ResZn', 'ComZn', 'Spc', 'ResOtherZn', 'ResAttic'}

# Opening element types
OPENING_TYPES: Set[str] = {
    'ResWin', 'Win', 'ResDr', 'Dr', 'ResSkylt', 'Skylt',
    'Window', 'Door', 'Skylight'
}

# Wall-only surface types (for sequential opening assignment)
WALL_SURFACE_TYPES: Set[str] = {'ResExtWall', 'ResIntWall', 'ExtWall', 'IntWall'}

# Root-level metadata elements (parsed separately)
ROOT_METADATA_PROPERTIES: Set[str] = {'RulesetFilename', 'AnalysisType', 'ComplianceReportPDF'}

# Project-level nested elements (may appear at root or inside Proj)
PROJECT_NESTED_ELEMENTS: Set[str] = {'ResProj', 'ProjVar'}


def detect_version(content: str) -> CIBDVersion:
    """
    Detect CIBD version from file content.

    Args:
        content: File content as string

    Returns:
        Detected CIBDVersion
    """
    if 'T24_2025.bin' in content:
        return CIBDVersion.CIBD25
    elif 'T24_2022.bin' in content:
        return CIBDVersion.CIBD22
    else:
        # Default to 2025 if unknown
        return CIBDVersion.CIBD25


def detect_version_from_file(file_path: str) -> CIBDVersion:
    """
    Detect CIBD version from file.

    Args:
        file_path: Path to CIBD file

    Returns:
        Detected CIBDVersion
    """
    # Try multiple encodings
    for encoding in ['latin-1', 'windows-1252', 'utf-8']:
        try:
            with open(file_path, 'r', encoding=encoding) as f:
                content = f.read(1000)  # Read first 1000 chars
            return detect_version(content)
        except (UnicodeDecodeError, LookupError):
            continue

    # Default to 2025
    return CIBDVersion.CIBD25
