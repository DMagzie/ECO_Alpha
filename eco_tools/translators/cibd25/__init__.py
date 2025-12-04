"""
CIBD25 Translator Module - Text format for Title 24 2025

CIBD25 uses the same text format as CIBD22 but with 2025 rulesets:
- T24_2025.bin ruleset (vs T24N_2022.bin for CIBD22)
- CBECC 2025.1.0 software version
- Additional 2025-specific properties

New Direct Writer (Recommended):
- direct_writer: EMJSON → CIBD25 direct conversion (no XML intermediate)
- Fixes: commercial catalogs, property formatting, window types
- Zero errors on exported files

Legacy Converter (Deprecated):
- See eco_tools.translators.cibd25_legacy for old XML-based converter
"""

from .importer import CIBD25Importer
from .exporter import CIBD25Exporter, export_cibd25

# New direct writer (recommended)
from .direct_writer import CIBD25DirectWriter, convert_emjson_to_cibd25
from .element_writer import ElementWriter, ResidentialElementWriter, CommercialElementWriter, PropertyFormatter
from .catalog_builder import build_default_commercial_catalogs
from .property_mapper import PropertyMapper
from .validators import CIBD25Validator as CIBD25OutputValidator

# Property rules - single source of truth for V7 lessons learned
from .property_rules import (
    should_skip_element,
    should_skip_property,
    get_required_defaults,
    apply_required_defaults,
    get_element_priority,
    should_defer_root_element,
    filter_properties,
    sort_elements_by_priority,
    DEPRECATED_PROPERTIES_GLOBAL,
    DEPRECATED_PROPERTIES_BY_ELEMENT,
    SKIP_ELEMENTS,
    REQUIRED_DEFAULTS,
    ELEMENT_PRIORITIES,
    DEFER_ROOT_ELEMENTS,
    VERSION_MARKERS,
)

__all__ = [
    # Import/Export
    'CIBD25Importer',
    'CIBD25Exporter',
    'export_cibd25',
    'translate_cibd25_to_v6',
    # Direct Writer (New - Recommended)
    'CIBD25DirectWriter',
    'convert_emjson_to_cibd25',
    # Element Writers
    'ElementWriter',
    'ResidentialElementWriter',
    'CommercialElementWriter',
    'PropertyFormatter',
    # Utilities
    'build_default_commercial_catalogs',
    'PropertyMapper',
    'CIBD25OutputValidator',
    # Property Rules (V7 lessons learned)
    'should_skip_element',
    'should_skip_property',
    'get_required_defaults',
    'apply_required_defaults',
    'get_element_priority',
    'should_defer_root_element',
    'filter_properties',
    'sort_elements_by_priority',
    'DEPRECATED_PROPERTIES_GLOBAL',
    'DEPRECATED_PROPERTIES_BY_ELEMENT',
    'SKIP_ELEMENTS',
    'REQUIRED_DEFAULTS',
    'ELEMENT_PRIORITIES',
    'DEFER_ROOT_ELEMENTS',
    'VERSION_MARKERS',
]


def translate_cibd25_to_v6(text_file: str):
    """
    Translate CIBD25 text file to EMJSON v6 format.

    Uses modular architecture:
    1. Text parser converts CIBD25 text → XML structure (reuses CIBD22 parser)
    2. CIBD22X modular parsers process XML → InternalRepresentation
    3. Convert to EMJSON v6 format

    Args:
        text_file: Path to CIBD25 text file

    Returns:
        dict: EMJSON v6 dictionary with diagnostics
    """
    # Use the simplified importer (works with text reader)
    from .simple_importer import convert_cibd25_to_emjson
    return convert_cibd25_to_emjson(text_file)
