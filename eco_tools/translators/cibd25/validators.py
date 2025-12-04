"""
CIBD25 Validators

Validation for CIBD25 text output.

This module provides validation to catch errors before sending to CBECC:
- Commercial catalog presence
- Property type errors
- Invalid properties
- Missing required properties
"""

from typing import Dict, List, Any
import re
import logging

logger = logging.getLogger(__name__)


class CIBD25Validator:
    """Validate CIBD25 files against known issues."""

    def validate_content(self, content: str) -> Dict[str, Any]:
        """
        Comprehensive validation of CIBD25 content.

        Args:
            content: CIBD25 text content

        Returns:
            Dictionary with validation results:
            {
                'has_commercial_catalogs': bool,
                'property_type_errors': [],
                'invalid_properties': [],
                'missing_required': [],
                'warnings': [],
                'error_count': int
            }
        """
        results = {
            'has_commercial_catalogs': self._check_commercial_catalogs(content),
            'property_type_errors': self._check_type_formatting(content),
            'invalid_properties': self._check_invalid_properties(content),
            'missing_required': [],  # TODO: Implement
            'warnings': [],
            'error_count': 0
        }

        # Count total errors
        results['error_count'] = (
            len(results['property_type_errors']) +
            len(results['invalid_properties']) +
            len(results['missing_required'])
        )

        # Add warnings
        if not results['has_commercial_catalogs']:
            results['warnings'].append(
                "Missing commercial catalogs (Mat/ConsAssm/FenCons) - "
                "will cause 101 'Invalid component type' errors"
            )

        return results

    def _check_commercial_catalogs(self, content: str) -> bool:
        """
        Check if commercial catalogs are present.

        Args:
            content: CIBD25 text content

        Returns:
            True if Mat, ConsAssm, and FenCons are all present
        """
        # TODO: Implement
        has_mat = bool(re.search(r'^\s*Mat\s+', content, re.MULTILINE))
        has_cons = bool(re.search(r'^\s*ConsAssm\s+', content, re.MULTILINE))
        has_fen = bool(re.search(r'^\s*FenCons\s+', content, re.MULTILINE))

        return has_mat and has_cons and has_fen

    def _check_type_formatting(self, content: str) -> List[Dict[str, Any]]:
        """
        Check for type formatting errors (e.g., quoted integers).

        Args:
            content: CIBD25 text content

        Returns:
            List of type error dictionaries
        """
        # TODO: Implement
        errors = []

        # Check for quoted integers (BldgEngyModelVersion, ZipCode, etc.)
        quoted_int_pattern = r'(BldgEngyModelVersion|ZipCode|CompReportPDF)\s*=\s*"(\d+)"'
        for match in re.finditer(quoted_int_pattern, content):
            errors.append({
                'type': 'quoted_integer',
                'property': match.group(1),
                'value': match.group(2),
                'message': f'{match.group(1)} should not be quoted'
            })

        return errors

    def _check_invalid_properties(self, content: str) -> List[Dict[str, Any]]:
        """
        Check for properties on wrong element types.

        Args:
            content: CIBD25 text content

        Returns:
            List of invalid property dictionaries
        """
        # TODO: Implement
        errors = []

        # Check for VentSpcFunc on ResZn
        # Pattern: Find ResZn blocks that contain VentSpcFunc
        reszn_blocks = re.finditer(
            r'ResZn\s+"([^"]+)"(.*?)\.\.', content,
            re.DOTALL
        )

        for match in reszn_blocks:
            zone_name = match.group(1)
            block_content = match.group(2)

            if 'VentSpcFunc' in block_content:
                errors.append({
                    'type': 'invalid_property',
                    'element': 'ResZn',
                    'zone': zone_name,
                    'property': 'VentSpcFunc',
                    'message': f'VentSpcFunc should not be on ResZn "{zone_name}"'
                })

        return errors


def validate_file(file_path: str) -> Dict[str, Any]:
    """
    Validate a CIBD25 file.

    Args:
        file_path: Path to .cibd25 file

    Returns:
        Validation results dictionary
    """
    with open(file_path, 'r') as f:
        content = f.read()

    validator = CIBD25Validator()
    return validator.validate_content(content)
