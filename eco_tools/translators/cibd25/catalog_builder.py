"""
CIBD25 Catalog Builder

Build commercial material/assembly/fenestration catalogs for CIBD25 files.

This module solves the "101 Invalid component type" error problem by ensuring
commercial catalogs (Mat, ConsAssm, FenCons) are always present in exported files.

Usage:
    from eco_tools.translators.cibd25.catalog_builder import build_default_commercial_catalogs

    catalogs = build_default_commercial_catalogs()
    # Returns: {'Mat': [...], 'ConsAssm': [...], 'FenCons': [...]}
"""

from typing import Dict, List, Any
import logging

logger = logging.getLogger(__name__)


def build_default_commercial_catalogs() -> Dict[str, List[Dict[str, Any]]]:
    """
    Build baseline commercial catalogs required by CBECC 2025.

    These are minimal catalogs that prevent the "Invalid component type" errors
    that occur when commercial catalog elements are referenced but not defined.

    Returns:
        Dictionary with:
        - 'Mat': List of standard materials
        - 'ConsAssm': List of standard assemblies
        - 'FenCons': List of standard fenestration constructions

    Note:
        These defaults are based on CBECC 2025 requirements and should be
        sufficient for most residential buildings.
    """
    # TODO: Implement default catalogs
    # For now, return empty structure
    return {
        'Mat': _build_default_materials(),
        'ConsAssm': _build_default_assemblies(),
        'FenCons': _build_default_fenestration(),
    }


def _build_default_materials() -> List[Dict[str, Any]]:
    """
    Build default material catalog.

    Returns minimal set of materials required for commercial catalog validation.
    Based on CBECC 2025 standard materials library.
    """
    return [
        # Air cavities
        {
            'name': 'Air Cavity 4in or more',
            'CodeCat': 'Air',
            'CodeItem': 'Air - Cavity - Wall Roof Ceiling - 4 in. or more',
        },
        {
            'name': 'Air Cavity 1/2in to 4in',
            'CodeCat': 'Air',
            'CodeItem': 'Air - Cavity - Wall Roof Ceiling - 1/2 in. to 4 in.',
        },

        # Building boards and siding
        {
            'name': 'Board_5/8in Gypsum',
            'CodeCat': 'Bldg Board and Siding',
            'CodeItem': 'Gypsum Board - 5/8 in.',
        },
        {
            'name': 'Board_1/2in Plywood',
            'CodeCat': 'Bldg Board and Siding',
            'CodeItem': 'Plywood - 1/2 in.',
        },

        # Insulation
        {
            'name': 'Wall_Wood Frame R-19',
            'CodeCat': 'Insulation',
            'CodeItem': 'Wall - Wood Framed - Batt Insulation - R-19',
        },
        {
            'name': 'Roof_Attic Batt R-38',
            'CodeCat': 'Insulation',
            'CodeItem': 'Attic - Batt Insulation - R-38',
        },
        {
            'name': 'Floor_Carpet',
            'CodeCat': 'Finish Flooring',
            'CodeItem': 'Carpet - Fibrous Pad',
        },

        # Finishes
        {
            'name': 'Finishes_Stucco',
            'CodeCat': 'Finishes',
            'CodeItem': 'Stucco - 7/8 in.',
        },

        # Concrete/masonry
        {
            'name': 'Concrete_6in LW',
            'CodeCat': 'Concrete',
            'CodeItem': 'Concrete - Lightweight - 6 in.',
        },
        {
            'name': 'Concrete_4in Slab',
            'CodeCat': 'Concrete',
            'CodeItem': 'Concrete - Normal Weight - 4 in.',
        },
    ]


def _build_default_assemblies() -> List[Dict[str, Any]]:
    """
    Build default assembly catalog.

    Returns minimal set of construction assemblies for commercial catalog validation.
    Based on CBECC 2025 standard assemblies library.
    """
    return [
        # Exterior walls
        {
            'name': 'Standard Exterior Wall',
            'CompatibleSurfType': 'ExteriorWall',
            'MatRef': [
                'Finishes_Stucco',
                'Board_1/2in Plywood',
                'Wall_Wood Frame R-19',
                'Board_5/8in Gypsum',
            ],
        },
        {
            'name': 'Concrete Exterior Wall',
            'CompatibleSurfType': 'ExteriorWall',
            'MatRef': [
                'Concrete_6in LW',
            ],
        },

        # Interior walls
        {
            'name': 'Standard Interior Wall',
            'CompatibleSurfType': 'InteriorWall',
            'MatRef': [
                'Board_5/8in Gypsum',
                'Air Cavity 4in or more',
                'Board_5/8in Gypsum',
            ],
        },

        # Roofs
        {
            'name': 'Standard Roof',
            'CompatibleSurfType': 'Roof',
            'MatRef': [
                'Roof_Attic Batt R-38',
                'Board_5/8in Gypsum',
            ],
        },

        # Floors
        {
            'name': 'Standard Floor',
            'CompatibleSurfType': 'Floor',
            'MatRef': [
                'Floor_Carpet',
                'Concrete_4in Slab',
            ],
        },
    ]


def _build_default_fenestration() -> List[Dict[str, Any]]:
    """
    Build default fenestration catalog.

    Returns minimal set of fenestration constructions for commercial catalog validation.
    Based on CBECC 2025 standard fenestration library.
    """
    return [
        # Windows
        {
            'name': 'Standard Fixed Window',
            'FenProdType': 'FixedWindow',
            'CertificationMthd': 'NFRCRated',
            'SHGC': 0.25,
            'UFactor': 0.36,
            'VT': 0.42,
        },
        {
            'name': 'Standard Operable Window',
            'FenProdType': 'OperableWindow',
            'CertificationMthd': 'NFRCRated',
            'SHGC': 0.22,
            'UFactor': 0.46,
            'VT': 0.32,
        },
        {
            'name': 'High Performance Window',
            'FenProdType': 'OperableWindow',
            'CertificationMthd': 'NFRCRated',
            'SHGC': 0.20,
            'UFactor': 0.28,
            'VT': 0.45,
        },

        # Doors
        {
            'name': 'Standard Glazed Door',
            'FenProdType': 'GlazedDoor',
            'CertificationMthd': 'NFRCRated',
            'SHGC': 0.23,
            'UFactor': 0.45,
            'VT': 0.17,
        },

        # Note: Skylights are not included in commercial FenCons catalog
        # Skylights are residential-only (ResWinType), not valid for commercial FenCons
    ]


def extract_materials_from_emjson(emjson: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Extract materials already defined in EMJSON.

    Args:
        emjson: EMJSON v6 data

    Returns:
        List of material dictionaries
    """
    # TODO: Implement
    catalogs = emjson.get('catalogs', {})
    return catalogs.get('materials', [])


def merge_catalogs(existing: Dict[str, List], defaults: Dict[str, List]) -> Dict[str, List]:
    """
    Merge existing catalogs with defaults, avoiding duplicates.

    Args:
        existing: Catalogs from EMJSON
        defaults: Default catalogs

    Returns:
        Merged catalog dictionary

    Note:
        Existing entries take precedence over defaults (no overwrite).
        Duplicates detected by 'name' field.
    """
    # TODO: Implement
    merged = {}

    for catalog_type in ['Mat', 'ConsAssm', 'FenCons']:
        merged[catalog_type] = existing.get(catalog_type, [])

        # Add defaults that don't exist
        existing_names = {item.get('name') for item in merged[catalog_type]}
        for default_item in defaults.get(catalog_type, []):
            if default_item.get('name') not in existing_names:
                merged[catalog_type].append(default_item)

    return merged
