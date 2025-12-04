"""
CIBD25 Validator Utility

Validate CIBD25 files against known issues before sending to CBECC.

This is the user-facing validator utility. For internal validation during
export, see eco_tools.translators.cibd25.validators

Usage:
    from eco_tools.translators.utilities import CIBD25Validator

    validator = CIBD25Validator()
    issues = validator.validate_file('building.cibd25')

    if issues['error_count'] == 0:
        print("✓ File is clean!")
    else:
        print(f"Found {issues['error_count']} issues")
"""

from typing import Dict, Any
import logging

# Import the core validator
from eco_tools.translators.cibd25.validators import CIBD25Validator as CoreValidator

logger = logging.getLogger(__name__)


class CIBD25Validator:
    """
    User-facing validator for CIBD25 files.

    This wraps the core validator and adds convenience methods for
    command-line use and reporting.
    """

    def __init__(self):
        """Initialize the validator."""
        self.core_validator = CoreValidator()

    def validate_file(self, cibd25_path: str) -> Dict[str, Any]:
        """
        Validate a CIBD25 file.

        Args:
            cibd25_path: Path to .cibd25 file

        Returns:
            Validation results dictionary:
            {
                'has_commercial_catalogs': bool,
                'property_type_errors': List[Dict],
                'invalid_properties': List[Dict],
                'missing_required': List[Dict],
                'warnings': List[str],
                'error_count': int
            }
        """
        logger.info(f"Validating {cibd25_path}")

        try:
            with open(cibd25_path, 'r') as f:
                content = f.read()

            results = self.core_validator.validate_content(content)
            logger.info(f"Validation complete: {results['error_count']} errors")

            return results

        except Exception as e:
            logger.error(f"Validation failed: {e}")
            return {
                'has_commercial_catalogs': False,
                'property_type_errors': [],
                'invalid_properties': [],
                'missing_required': [],
                'warnings': [],
                'error_count': -1,
                'validation_error': str(e)
            }

    def print_report(self, results: Dict[str, Any]) -> None:
        """
        Print a formatted validation report.

        Args:
            results: Validation results dictionary
        """
        print("\n" + "=" * 70)
        print("CIBD25 VALIDATION REPORT")
        print("=" * 70)

        if results['error_count'] == 0:
            print("✅ File is clean! No errors found.")
        else:
            print(f"❌ Found {results['error_count']} error(s)")

        # Commercial catalogs
        if results['has_commercial_catalogs']:
            print("\n✅ Commercial catalogs present")
        else:
            print("\n❌ Missing commercial catalogs (will cause 101 errors)")

        # Property type errors
        if results['property_type_errors']:
            print(f"\n❌ Property type errors: {len(results['property_type_errors'])}")
            for error in results['property_type_errors'][:5]:  # Show first 5
                print(f"   - {error.get('message', 'Unknown error')}")

        # Invalid properties
        if results['invalid_properties']:
            print(f"\n❌ Invalid properties: {len(results['invalid_properties'])}")
            for error in results['invalid_properties'][:5]:  # Show first 5
                print(f"   - {error.get('message', 'Unknown error')}")

        # Warnings
        if results['warnings']:
            print(f"\n⚠️  Warnings:")
            for warning in results['warnings']:
                print(f"   - {warning}")

        print("=" * 70 + "\n")


def validate_and_report(cibd25_path: str) -> int:
    """
    Validate a file and print a report.

    Args:
        cibd25_path: Path to .cibd25 file

    Returns:
        Exit code (0 = clean, 1 = errors found)
    """
    validator = CIBD25Validator()
    results = validator.validate_file(cibd25_path)
    validator.print_report(results)

    return 0 if results['error_count'] == 0 else 1
