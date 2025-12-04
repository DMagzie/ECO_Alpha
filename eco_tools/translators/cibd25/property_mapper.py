"""
CIBD25 Property Mapper

Property mapping and validation logic for CIBD25 elements.

This module handles:
- EMJSON → CIBD25 property name mapping
- Property value transformations
- Unit conversions
- Required vs optional properties
"""

from typing import Dict, Any, Optional, List
import logging

logger = logging.getLogger(__name__)


class PropertyMapper:
    """
    Map EMJSON properties to CIBD25 properties.

    Handles:
    - Property name mapping (EMJSON field → CIBD25 field)
    - Value transformations
    - Unit conversions (SI → Imperial where needed)
    - Required property validation
    """

    # Property name mappings: EMJSON → CIBD25
    PROPERTY_MAPPINGS = {
        'ResZn': {
            'name': 'Name',
            'area': 'Area',
            'ceiling_height': 'CeilingHeight',
            'floor_height': 'FloorHeight',
            'type': 'Type',
            # Note: VentSpcFunc should NOT be mapped for ResZn
        },
        'Spc': {
            'name': 'Name',
            'area': 'Area',
            'ceiling_height': 'CeilingHeight',
            'vent_spc_func': 'VentSpcFunc',  # OK for Spc (commercial)
        },
        # TODO: Add mappings for other element types
    }

    # Required properties by element type
    REQUIRED_PROPERTIES = {
        'ResZn': ['Name', 'Area', 'Type'],
        'Spc': ['Name', 'Area'],
        'Mat': ['Name', 'Density', 'SpecHeat', 'Conductivity'],
        # TODO: Add required properties for other element types
    }

    @classmethod
    def map_properties(cls, element_type: str, emjson_props: Dict[str, Any]) -> Dict[str, Any]:
        """
        Map EMJSON properties to CIBD25 properties.

        Args:
            element_type: Element type (e.g., 'ResZn', 'Spc')
            emjson_props: EMJSON property dictionary

        Returns:
            CIBD25 property dictionary
        """
        # TODO: Implement mapping
        cibd25_props = {}
        mappings = cls.PROPERTY_MAPPINGS.get(element_type, {})

        for emjson_key, cibd25_key in mappings.items():
            if emjson_key in emjson_props:
                value = emjson_props[emjson_key]
                # TODO: Apply value transformations if needed
                cibd25_props[cibd25_key] = value

        return cibd25_props

    @classmethod
    def validate_required_properties(cls, element_type: str, properties: Dict[str, Any]) -> List[str]:
        """
        Validate that required properties are present.

        Args:
            element_type: Element type
            properties: Property dictionary

        Returns:
            List of missing required properties (empty if all present)
        """
        required = cls.REQUIRED_PROPERTIES.get(element_type, [])
        missing = []

        for prop in required:
            if prop not in properties:
                missing.append(prop)

        return missing

    @classmethod
    def should_include_property(cls, element_type: str, property_name: str) -> bool:
        """
        Determine if a property should be included for this element type.

        This prevents errors like VentSpcFunc on ResZn.

        Args:
            element_type: Element type
            property_name: Property name

        Returns:
            True if property is valid for this element type
        """
        # VentSpcFunc should NOT be on residential zones
        if property_name == 'VentSpcFunc' and element_type in ['ResZn', 'ResOtherZn', 'ResLivingZn']:
            return False

        # TODO: Add other property exclusion rules

        return True
