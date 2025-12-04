"""
CIBD25 Utilities Module

Post-processing utilities for CIBD25 files.

These utilities fix common issues in CIBD25 files:
- WindowTypeMapper: Map window type properties to individual instances
- CommercialCatalogInjector: Add missing Mat/ConsAssm/FenCons catalogs
- PropertyFixer: Fix properties on wrong element types (e.g., VentSpcFunc on ResZn)
- CIBD25Validator: Validate files before sending to CBECC
- BatchProcessor: Process multiple files at once

Usage:
    from eco_tools.translators.utilities import CommercialCatalogInjector

    injector = CommercialCatalogInjector()
    injector.inject_catalogs('building.cibd25')
"""

from .window_type_mapper import WindowTypeMapper
from .commercial_catalog_injector import CommercialCatalogInjector
from .property_fixer import PropertyFixer
from .validator import CIBD25Validator
from .batch_processor import BatchProcessor

__all__ = [
    'WindowTypeMapper',
    'CommercialCatalogInjector',
    'PropertyFixer',
    'CIBD25Validator',
    'BatchProcessor',
]

__version__ = '1.0.0'
