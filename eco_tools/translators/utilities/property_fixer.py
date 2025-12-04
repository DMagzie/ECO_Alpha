"""
Property Fixer Utility

Fix incorrectly placed properties in CIBD25 files.

Problem:
Properties sometimes get added to wrong element types. For example:
- VentSpcFunc on ResZn (should only be on Spc - commercial spaces)
- Type missing on ThrmlZn
- Invalid property values

Solution:
This utility reads CIBD25 files and fixes property issues according to rules.

Usage:
    from eco_tools.translators.utilities import PropertyFixer

    fixer = PropertyFixer()
    report = fixer.fix_properties('el_paseo.cibd25')
    print(f"Fixed {report['fixes_applied']} issues")
"""

from typing import Dict, Any, List
import logging

logger = logging.getLogger(__name__)


class PropertyFixer:
    """Fix incorrectly placed properties in CIBD25 files."""

    # Rules for property placement
    PROPERTY_RULES = {
        'VentSpcFunc': {
            'valid_on': ['Spc'],  # Commercial spaces only
            'invalid_on': ['ResZn', 'ResOtherZn', 'ResLivingZn'],  # NOT residential
            'action': 'remove'  # Remove if on wrong element
        },
        'Type': {
            'valid_on': ['ResZn', 'ThrmlZn', 'ResOtherZn', 'ResLivingZn'],
            'required': True,
            'action': 'add_default'  # Add with default if missing
        },
        # TODO: Add more property rules
    }

    def fix_properties(self, cibd25_path: str) -> Dict[str, Any]:
        """
        Fix properties in a CIBD25 file.

        Args:
            cibd25_path: Path to .cibd25 file

        Returns:
            Report dictionary:
            {
                'fixes_applied': int,
                'properties_removed': List[str],
                'properties_added': List[str],
                'errors': List[str]
            }
        """
        try:
            logger.info(f"Fixing properties in {cibd25_path}")

            # Read file
            with open(cibd25_path, 'r') as f:
                content = f.read()

            # Apply fixes
            fixed_content, report = self._apply_fixes(content)

            # Write back
            with open(cibd25_path, 'w') as f:
                f.write(fixed_content)

            logger.info(f"Applied {report['fixes_applied']} fixes")
            return report

        except Exception as e:
            logger.error(f"Failed to fix properties: {e}")
            return {
                'fixes_applied': 0,
                'properties_removed': [],
                'properties_added': [],
                'errors': [str(e)]
            }

    def _apply_fixes(self, content: str) -> tuple[str, Dict[str, Any]]:
        """Apply property fixes to content."""
        # TODO: Implement
        report = {
            'fixes_applied': 0,
            'properties_removed': [],
            'properties_added': [],
            'errors': []
        }

        # Fix VentSpcFunc on ResZn
        content, ventspc_fixes = self._remove_ventspcfunc_from_reszn(content)
        report['fixes_applied'] += ventspc_fixes
        if ventspc_fixes > 0:
            report['properties_removed'].append(f'VentSpcFunc from ResZn ({ventspc_fixes} instances)')

        # TODO: Add more fixes

        return content, report

    def _remove_ventspcfunc_from_reszn(self, content: str) -> tuple[str, int]:
        """Remove VentSpcFunc from ResZn elements."""
        # TODO: Implement
        # Should find ResZn blocks with VentSpcFunc and remove the property
        return content, 0

    def remove_invalid_properties(
        self,
        element_type: str,
        properties: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Remove properties that shouldn't be on this element type.

        Args:
            element_type: Element type (e.g., 'ResZn', 'Spc')
            properties: Property dictionary

        Returns:
            Cleaned property dictionary
        """
        cleaned = properties.copy()

        for prop_name, rule in self.PROPERTY_RULES.items():
            if prop_name in cleaned:
                invalid_on = rule.get('invalid_on', [])
                if element_type in invalid_on:
                    logger.info(f"Removing {prop_name} from {element_type}")
                    del cleaned[prop_name]

        return cleaned
