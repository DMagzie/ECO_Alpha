"""
Format Utility - Property Name Mapping for CIBD22 vs CIBD22X
=============================================================

PURPOSE:
Handles property name differences between CIBD22 and CIBD22X formats.
CBECC accepts both formats, and files often mix both depending on context:
- Elements nested in Proj → Bldg typically use CIBD22 format
- Elements at root level typically use CIBD22X format

KEY DIFFERENCES:
CIBD22X Format (newer):
  - Name: <n>
  - Construction reference: <ConsAssmRef>
  - Window type reference: <FenConsRef>
  - Adjacent space: <AdjacentSpcRef>
  - Type: <Type>

CIBD22 Format (older):
  - Name: <Name>
  - Construction reference: <Construction>
  - Window type reference: <WinType>
  - Adjacent space: <AdjacentSpace>
  - Type: <Type> (same)
"""

from enum import Enum
from typing import Dict


class Format(Enum):
    """Format enum for CIBD22 vs CIBD22X"""
    CIBD22 = "CIBD22"
    CIBD22X = "CIBD22X"


# Property name mappings: {CIBD22X_name: CIBD22_name}
PROPERTY_MAPPINGS = {
    # Name field
    'n': 'Name',

    # References
    'ConsAssmRef': 'Construction',      # Construction assembly reference
    'FenConsRef': 'WinType',            # Fenestration/window type reference
    'AdjacentSpcRef': 'AdjacentSpace',  # Adjacent space reference

    # Note: Many properties are the same in both formats
    # (Area, Orientation, FloorArea, etc.)
}


def get_property_name(cibd22x_name: str, format_type: Format) -> str:
    """
    Get the correct property name for the specified format.

    Args:
        cibd22x_name: Property name in CIBD22X format
        format_type: Target format (CIBD22 or CIBD22X)

    Returns:
        Property name in the target format

    Examples:
        >>> get_property_name('n', Format.CIBD22)
        'Name'
        >>> get_property_name('n', Format.CIBD22X)
        'n'
        >>> get_property_name('ConsAssmRef', Format.CIBD22)
        'Construction'
    """
    if format_type == Format.CIBD22X:
        return cibd22x_name

    # Convert to CIBD22 if there's a mapping
    return PROPERTY_MAPPINGS.get(cibd22x_name, cibd22x_name)


def get_name_tag(format_type: Format) -> str:
    """
    Get the name tag for the specified format.

    Args:
        format_type: Format (CIBD22 or CIBD22X)

    Returns:
        'Name' for CIBD22, 'n' for CIBD22X
    """
    return 'Name' if format_type == Format.CIBD22 else 'n'


def get_construction_ref_tag(format_type: Format) -> str:
    """
    Get the construction reference tag for the specified format.

    Args:
        format_type: Format (CIBD22 or CIBD22X)

    Returns:
        'Construction' for CIBD22, 'ConsAssmRef' for CIBD22X
    """
    return 'Construction' if format_type == Format.CIBD22 else 'ConsAssmRef'


def get_window_type_ref_tag(format_type: Format) -> str:
    """
    Get the window type reference tag for the specified format.

    Args:
        format_type: Format (CIBD22 or CIBD22X)

    Returns:
        'WinType' for CIBD22, 'FenConsRef' for CIBD22X
    """
    return 'WinType' if format_type == Format.CIBD22 else 'FenConsRef'


def get_adjacent_space_ref_tag(format_type: Format) -> str:
    """
    Get the adjacent space reference tag for the specified format.

    Args:
        format_type: Format (CIBD22 or CIBD22X)

    Returns:
        'AdjacentSpace' for CIBD22, 'AdjacentSpcRef' for CIBD22X
    """
    return 'AdjacentSpace' if format_type == Format.CIBD22 else 'AdjacentSpcRef'


# Context-based format determination
def get_format_for_context(parent_context: str) -> Format:
    """
    Determine which format to use based on XML context.

    CBECC uses different formats in different contexts:
    - Elements nested in Proj → Bldg: CIBD22 format
    - Elements at root level: CIBD22X format

    Args:
        parent_context: Parent element context ('Bldg', 'SDDXML', etc.)

    Returns:
        Format to use (CIBD22 or CIBD22X)
    """
    # Elements nested inside Bldg use CIBD22 format
    if parent_context in ['Bldg', 'Story', 'Spc']:
        return Format.CIBD22

    # Root-level elements use CIBD22X format
    return Format.CIBD22X
