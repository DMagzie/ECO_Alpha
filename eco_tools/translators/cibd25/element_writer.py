"""
CIBD25 Element Writers

Element-specific writing logic for CIBD25 text format.

This module handles:
- Element-specific writing logic
- Property formatting (quotes vs no quotes)
- Nested property handling
- Reference resolution
- Property filtering per V7 rules
"""

from typing import Dict, Any, List
import logging

from .property_rules import (
    should_skip_element,
    should_skip_property,
    filter_properties,
    apply_required_defaults,
)

logger = logging.getLogger(__name__)


class PropertyFormatter:
    """
    Format properties correctly for CIBD25 text format.

    Handles:
    - Integer formatting (no quotes): BldgEngyModelVersion, CompReportPDF, ZipCode
    - String formatting (with quotes): City, State, DocAuthZipCode
    - Float formatting (no quotes): Area, Height, UFactor, SHGC
    - Enumeration formatting (varies): Type, VentSpcFunc
    """

    # Properties that must ALWAYS be quoted (STRING or ENUM fields in CBECC schema)
    # Even if they look numeric or contain only digits
    ALWAYS_QUOTE = {
        # Author/document metadata (STRING fields)
        'DocAuthZipCode',      # Author ZIP - STRING (can have leading zeros)
        'DocAuthAddress',      # Author address
        'DocAuthCity',         # Author city
        'DocAuthState',        # Author state
        'DocAuthCompany',      # Author company
        'DocAuthor',           # Author name
        'DocAuthPhone',        # Author phone
        'DocTitle',            # Document title
        'StAddress',           # Street address
        'City',                # City name
        'State',               # State code

        # Enum/choice properties (always quoted in CBECC)
        'Status',              # Component status (New, Existing, etc.)
        'Type',                # Zone/space type
        'DryerFuel',           # Dryer fuel type
        'CookingApplType',     # Cooking appliance type
        'CliZn',               # Climate zone
        'Orientation',         # Orientation (Front, Back, etc.)
        'GeometryInpType',     # Geometry input type
        'WeatherStation',      # Weather station name
        'ExcptCondNoClgSys',   # Exception conditions (Yes/No)
        'ExcptCondRtdCap',
        'ExcptCondNarrative',
        'ReducedPVReqExcpt',
        'RunTitle',            # Run title
        'SoftwareVersion',     # Software version string
        'ResultsCurrentMessage',
        'VentSpcFunc',         # Ventilation space function
        'SpcFunc',             # Space function
        'CanAssignTo',         # Assembly assignable types
        'CavityLayer',         # Construction layer names
        'FrameLayer',
        'SheathInsulLayer',
        'WallExtFinishLayer',
        'MassThickness',       # Mass thickness (quoted even after stripping units)
    }

    @classmethod
    def format_value(cls, field_name: str, value: Any) -> str:
        """
        Return correctly formatted value for CIBD25 text.

        Rules:
        1. If value is None, return empty string ""
        2. If field_name is in ALWAYS_QUOTE, quote it
        3. If field_name ends with "Lbl" (label), quote it (display strings)
        4. If value is numeric (int or float), no quotes
        5. Otherwise, quote it

        Args:
            field_name: Property name
            value: Property value

        Returns:
            Formatted string ready for CIBD25 output
        """
        # Handle None/empty
        if value is None or value == '':
            return '""'

        # Convert value to string
        str_value = str(value)

        # Fields that must always be quoted
        if field_name in cls.ALWAYS_QUOTE:
            return f'"{str_value}"'

        # Properties ending in "Lbl" are labels (display strings) - always quote
        if field_name.endswith('Lbl'):
            return f'"{str_value}"'

        # Check if it's a number
        if cls._is_number(str_value):
            # Numeric fields - no quotes
            return str_value

        # Everything else - quote it
        return f'"{str_value}"'

    @classmethod
    def _is_number(cls, value: str) -> bool:
        """
        Check if value is a number (int or float).

        Args:
            value: String value to check

        Returns:
            True if value is numeric
        """
        if not value:
            return False

        try:
            float(value)
            return True
        except (ValueError, TypeError):
            return False


class ElementWriter:
    """Base class for element writing."""

    def __init__(self, formatter: PropertyFormatter = None):
        """
        Initialize element writer.

        Args:
            formatter: Property formatter instance
        """
        self.formatter = formatter or PropertyFormatter()

    def write_element(self, element_type: str, element_data: Dict[str, Any],
                     indent: int = 0) -> List[str]:
        """
        Write an element and its properties.

        Args:
            element_type: Element type (e.g., 'Proj', 'ResZn', 'Mat')
            element_data: Element data dictionary
            indent: Indentation level

        Returns:
            List of formatted output lines
        """
        lines = []
        indent_str = '   ' * indent
        prop_indent = '   ' * (indent + 1)

        # Opening line with element name
        name = element_data.get('name', element_data.get('Name', ''))
        lines.append(f'{indent_str}{element_type}   "{name}"')

        # Write properties
        for key, value in element_data.items():
            # Skip 'name' and 'Name' - already written
            if key in ('name', 'Name'):
                continue

            # Skip None values
            if value is None:
                continue

            # Handle list properties (e.g., MatRef)
            # CRITICAL: CIBD25 arrays use 1-based indexing: MatRef[1], MatRef[2], etc.
            if isinstance(value, list):
                for i, item in enumerate(value, start=1):
                    formatted_value = self.formatter.format_value(key, item)
                    lines.append(f'{prop_indent}{key}[{i}] = {formatted_value}')
            # Handle dict properties (nested elements) - TODO: implement if needed
            elif isinstance(value, dict):
                logger.warning(f"Nested dict properties not yet supported: {key}")
                continue
            # Handle simple properties
            else:
                formatted_value = self.formatter.format_value(key, value)
                lines.append(f'{prop_indent}{key} = {formatted_value}')

        # Closing
        lines.append(f'{indent_str}..')

        return lines


class ResidentialElementWriter(ElementWriter):
    """Writer for residential elements (ResZn, ResExtWall, etc.)."""

    def write_element(self, element_type: str, element_data: Dict[str, Any],
                     indent: int = 0) -> List[str]:
        """
        Write residential element with V7 property filtering.

        Uses property_rules to:
        - Filter deprecated properties (VentSpcFunc, PVBattSizeBldgType, etc.)
        - Apply required defaults (Type for ResCentralVentSys, ResZn, etc.)
        - Skip elements that aren't supported (Batt)
        """
        # Check if element should be skipped entirely (e.g., Batt)
        if should_skip_element(element_type):
            logger.debug(f"Skipping element {element_type} (per property_rules)")
            return []

        # Filter properties and apply defaults per V7 rules
        filtered_data = filter_properties(element_type, element_data.copy())

        return super().write_element(element_type, filtered_data, indent)


class CommercialElementWriter(ElementWriter):
    """Writer for commercial elements (Spc, Mat, ConsAssm, etc.)."""

    def write_element(self, element_type: str, element_data: Dict[str, Any],
                     indent: int = 0) -> List[str]:
        """
        Write commercial element with property filtering.

        Commercial elements have fewer deprecated properties than residential,
        but still use property_rules for consistency.
        """
        # Check if element should be skipped
        if should_skip_element(element_type):
            logger.debug(f"Skipping element {element_type} (per property_rules)")
            return []

        # Filter properties per V7 rules
        filtered_data = filter_properties(element_type, element_data.copy())

        return super().write_element(element_type, filtered_data, indent)
