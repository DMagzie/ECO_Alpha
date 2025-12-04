"""
CIBD25 Property Rules - Single source of truth for all CIBD25 export logic.

This module captures ALL lessons learned from V7 translator development.
Both DirectWriter and any legacy code paths should use these rules.

Fixes incorporated:
- Fix #39: Version markers for 2025
- Fix #40: No END_OF_FILE marker
- Fix #41: VentSpcFunc deprecated on ResZn/ResOtherZn
- Fix #42: HVAC component ordering
- Fix #43: ResCentralVentSys Type default, skip Batt element
- Fix #44: PVBattSizeBldgType and BattReq_PartOfLargeTenantArea cause GUI stall

Reference: CIBD25_ORDERING_LESSONS.md

Created: December 2, 2025
Version: 1.0
"""

from typing import Dict, List, Set, Any, Optional
import logging

logger = logging.getLogger(__name__)


# =============================================================================
# DEPRECATED PROPERTIES
# =============================================================================
# These properties exist in CIBD22X but are NOT valid in CIBD25.
# They MUST be filtered during conversion or they cause:
# - GUI display failures
# - Application stalls/hangs
# - Cascading errors that break element associations
#
# IMPORTANT: Command-line validation success does NOT guarantee GUI functionality.
# A file can return "button returned:OK" but still stall the GUI.

# Global deprecated properties (filter on ALL element types)
DEPRECATED_PROPERTIES_GLOBAL: Set[str] = {
    'MassThickness',  # Validation warnings on ResConsAssm
}

# Properties deprecated on specific element types only
DEPRECATED_PROPERTIES_BY_ELEMENT: Dict[str, Set[str]] = {
    'ResZn': {
        'VentSpcFunc',                    # Fix #41 - DwellUnitType not recognized
        'PVBattSizeBldgType',             # Fix #44 - GUI stalls/hangs
        'BattReq_PartOfLargeTenantArea',  # Fix #44 - GUI stalls/hangs
    },
    'ResOtherZn': {
        'VentSpcFunc',                    # Fix #41 - DwellUnitType not recognized
        'PVBattSizeBldgType',             # Fix #44 - GUI stalls/hangs
        'BattReq_PartOfLargeTenantArea',  # Fix #44 - GUI stalls/hangs
    },
    'DwellUnit': {
        'PVBattSizeBldgType',             # Fix #44 - GUI stalls/hangs
        'BattReq_PartOfLargeTenantArea',  # Fix #44 - GUI stalls/hangs
    },
    'ResConsAssm': {
        'MassThickness',                  # Validation warnings
    },
}


# =============================================================================
# ELEMENTS TO SKIP
# =============================================================================
# These elements should be completely skipped during conversion.

SKIP_ELEMENTS: Set[str] = {
    'Batt',  # Fix #43 - Battery storage not properly supported in CIBD25 text format
}


# =============================================================================
# REQUIRED PROPERTY DEFAULTS
# =============================================================================
# Some elements require specific properties that may be missing from source files.
# These defaults are added if the property is not present.

REQUIRED_DEFAULTS: Dict[str, Dict[str, Any]] = {
    'ResCentralVentSys': {
        'Type': 'Balanced',  # Fix #43 - Required or GUI stalls
    },
    'ResZn': {
        'Type': 'Conditioned',  # Default if missing
    },
    'ResOtherZn': {
        'Type': 'Unconditioned',  # Default if missing
    },
}


# =============================================================================
# ELEMENT ORDERING PRIORITIES
# =============================================================================
# CIBD25 text format requires elements in specific order.
# Lower priority = earlier in file.
#
# Critical ordering rules:
# 1. DwellUnitType AFTER all DwellUnit instances (Fix #26)
# 2. HVAC Systems (ResHVACSys, ResDHWSys) AFTER DwellUnitType (Fix #34)
# 3. HVAC Components BEFORE Bldg (Fix #42)
# 4. Bldg hierarchy must be contiguous

ELEMENT_PRIORITIES: Dict[str, int] = {
    # File header (implicit - always first)
    # RulesetFilename = priority 0

    # Project definition
    'Proj': 10,
    'ProjVar': 15,
    'ResProj': 20,

    # Schedules
    'SchDay': 30,
    'SchWeek': 31,
    'Sch': 32,

    # Construction catalog
    'FenCons': 50,
    'ConsAssm': 51,
    'DrCons': 52,
    'Mat': 53,
    'ResConsAssm': 54,
    'ResMat': 55,
    'ResWinType': 56,

    # HVAC Components (BEFORE Bldg) - Fix #42
    'ResHtgSys': 80,
    'ResClgSys': 80,
    'ResHtPumpSys': 81,
    'ResFanSys': 82,
    'ResCentralVentSys': 83,
    'ResDistSys': 84,
    'ResIAQFan': 85,
    'ResLpTankHtr': 85,

    # Building structure
    'Bldg': 100,
    # Building children (ResZnGrp, ResZn, DwellUnit, geometry) are written
    # as part of the Bldg hierarchy, not as separate root elements

    # Attic and PV (after building hierarchy)
    'ResAttic': 150,
    'PVArray': 160,

    # Commercial HVAC structure
    'AirSys': 200,
    'FluidSys': 201,
    'VRFSys': 202,
    'ZnSys': 203,

    # Equipment catalog
    'Lum': 600,
    'WtrHtr': 601,
    'Chiller': 602,
    'Boiler': 603,
    'Pump': 604,
    'ThrmlEngyStor': 605,

    # HERS/Compliance
    'HERSCool': 700,
    'HERSHeat': 701,
    'HERSHtPump': 702,

    # Type definitions (MUST come AFTER all instances) - Fix #26
    'DwellUnitType': 900,

    # HVAC Systems (AFTER DwellUnitType) - Fix #34
    'ResWtrHtr': 950,
    'ResHVACSys': 951,
    'ResDHWSys': 952,

    # Report objects (always last)
    'ResDHWSysRpt': 1000,
    'DwellUnitRpt': 1001,
    'ResZnRpt': 1002,
}

# Default priority for unlisted elements
DEFAULT_PRIORITY: int = 500


# =============================================================================
# ROOT-LEVEL DEFERRED ELEMENTS
# =============================================================================
# These elements, when at XML root level, must be deferred for proper ordering.
# They are collected during parsing and written at the end in priority order.

DEFER_ROOT_ELEMENTS: Set[str] = {
    'DwellUnitType',    # Type definitions (must come after DwellUnit instances)
    'ResHVACSys',       # HVAC systems (must come after DwellUnitType)
    'ResDHWSys',        # DHW systems (must come after DwellUnitType)
    'ResWtrHtr',        # Water heaters (must come after DwellUnitType)
}


# =============================================================================
# VERSION MARKERS
# =============================================================================
# Fix #39: Converted files must have 2025 version markers

VERSION_MARKERS: Dict[str, str] = {
    'RunTitle': 'Title 24 2025 Compliance',
    'SoftwareVersion': 'CBECC 2025.2.0 (ECO Tools)',
}

# Fix #40: Working CBECC files do NOT have an END_OF_FILE marker
WRITE_END_OF_FILE_MARKER: bool = False


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def should_skip_element(element_type: str) -> bool:
    """
    Check if element should be completely skipped during conversion.

    Args:
        element_type: The CIBD element type (e.g., 'Batt', 'ResZn')

    Returns:
        True if element should be skipped entirely
    """
    return element_type in SKIP_ELEMENTS


def should_skip_property(element_type: str, prop_name: str) -> bool:
    """
    Check if property should be filtered for this element type.

    Args:
        element_type: The CIBD element type (e.g., 'ResZn', 'DwellUnit')
        prop_name: The property name to check

    Returns:
        True if property should be filtered out
    """
    # Check global deprecated properties
    if prop_name in DEPRECATED_PROPERTIES_GLOBAL:
        logger.debug(f"Filtering global deprecated property: {prop_name}")
        return True

    # Check element-specific deprecated properties
    element_deprecated = DEPRECATED_PROPERTIES_BY_ELEMENT.get(element_type, set())
    if prop_name in element_deprecated:
        logger.debug(f"Filtering deprecated property {prop_name} on {element_type}")
        return True

    return False


def get_required_defaults(element_type: str) -> Dict[str, Any]:
    """
    Get required default properties for element type.

    Args:
        element_type: The CIBD element type

    Returns:
        Dictionary of property name → default value
    """
    return REQUIRED_DEFAULTS.get(element_type, {}).copy()


def apply_required_defaults(element_type: str, properties: Dict[str, Any]) -> Dict[str, Any]:
    """
    Apply required defaults to properties if not already present.

    Args:
        element_type: The CIBD element type
        properties: Existing property dictionary

    Returns:
        Properties with defaults applied (modifies in place and returns)
    """
    defaults = get_required_defaults(element_type)
    for prop_name, default_value in defaults.items():
        if prop_name not in properties:
            logger.debug(f"Adding required default {prop_name}={default_value} to {element_type}")
            properties[prop_name] = default_value
    return properties


def get_element_priority(element_type: str) -> int:
    """
    Get sorting priority for element type (lower = earlier in file).

    Args:
        element_type: The CIBD element type

    Returns:
        Priority value (lower values are written earlier)
    """
    return ELEMENT_PRIORITIES.get(element_type, DEFAULT_PRIORITY)


def should_defer_root_element(element_type: str) -> bool:
    """
    Check if root-level element should be deferred for later writing.

    Args:
        element_type: The CIBD element type

    Returns:
        True if element should be deferred
    """
    return element_type in DEFER_ROOT_ELEMENTS


def filter_properties(element_type: str, properties: Dict[str, Any]) -> Dict[str, Any]:
    """
    Filter properties for an element, removing deprecated ones and adding defaults.

    This is the main entry point for property processing.

    Args:
        element_type: The CIBD element type
        properties: Raw property dictionary

    Returns:
        Filtered and defaulted property dictionary
    """
    # Filter out deprecated properties
    filtered = {
        k: v for k, v in properties.items()
        if not should_skip_property(element_type, k)
    }

    # Apply required defaults
    apply_required_defaults(element_type, filtered)

    return filtered


def sort_elements_by_priority(elements: List[Dict[str, Any]],
                               type_key: str = 'type') -> List[Dict[str, Any]]:
    """
    Sort a list of elements by their priority.

    Args:
        elements: List of element dictionaries
        type_key: Key in dictionary containing element type

    Returns:
        Sorted list (lower priority = earlier)
    """
    return sorted(elements, key=lambda e: get_element_priority(e.get(type_key, '')))


# =============================================================================
# VALIDATION HELPERS
# =============================================================================

def validate_element(element_type: str, properties: Dict[str, Any]) -> List[str]:
    """
    Validate an element's properties.

    Args:
        element_type: The CIBD element type
        properties: Property dictionary

    Returns:
        List of warning/error messages (empty if valid)
    """
    warnings = []

    # Check for deprecated properties that shouldn't be present
    for prop_name in properties:
        if should_skip_property(element_type, prop_name):
            warnings.append(
                f"Deprecated property '{prop_name}' found on {element_type} - should be filtered"
            )

    # Check for missing required defaults
    defaults = get_required_defaults(element_type)
    for prop_name in defaults:
        if prop_name not in properties:
            warnings.append(
                f"Missing required property '{prop_name}' on {element_type} - default will be applied"
            )

    return warnings


# =============================================================================
# DOCUMENTATION
# =============================================================================

def get_deprecated_properties_doc() -> str:
    """Get documentation of all deprecated properties."""
    lines = ["Deprecated Properties (will be filtered):", ""]

    lines.append("Global (all elements):")
    for prop in sorted(DEPRECATED_PROPERTIES_GLOBAL):
        lines.append(f"  - {prop}")

    lines.append("")
    lines.append("By Element Type:")
    for element_type, props in sorted(DEPRECATED_PROPERTIES_BY_ELEMENT.items()):
        lines.append(f"  {element_type}:")
        for prop in sorted(props):
            lines.append(f"    - {prop}")

    return "\n".join(lines)


def get_element_order_doc() -> str:
    """Get documentation of element ordering."""
    lines = ["Element Ordering (by priority):", ""]

    # Group by priority ranges
    priority_groups = [
        (0, 29, "Project/Header"),
        (30, 49, "Schedules"),
        (50, 79, "Construction Catalog"),
        (80, 99, "HVAC Components"),
        (100, 149, "Building Structure"),
        (150, 199, "Attic/PV"),
        (200, 599, "Commercial HVAC"),
        (600, 699, "Equipment"),
        (700, 899, "HERS/Compliance"),
        (900, 949, "Type Definitions"),
        (950, 999, "HVAC Systems"),
        (1000, 1999, "Reports"),
    ]

    for min_p, max_p, group_name in priority_groups:
        elements = [
            (name, priority) for name, priority in ELEMENT_PRIORITIES.items()
            if min_p <= priority <= max_p
        ]
        if elements:
            lines.append(f"{group_name} (priority {min_p}-{max_p}):")
            for name, priority in sorted(elements, key=lambda x: x[1]):
                lines.append(f"  {priority:4d}: {name}")
            lines.append("")

    return "\n".join(lines)
