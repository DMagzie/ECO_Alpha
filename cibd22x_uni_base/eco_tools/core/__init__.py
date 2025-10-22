"""ECO Tools - core module"""

from eco_tools.core.format_detector import FormatDetector, FormatInfo
from eco_tools.core.translator import UniversalTranslator, TranslationResult
from eco_tools.core.validator import Validator, ValidationResult
from eco_tools.core.id_registry import IDRegistry
from eco_tools.core.internal_repr import InternalRepresentation

__all__ = [
    'FormatDetector',
    'FormatInfo',
    'UniversalTranslator',
    'TranslationResult',
    'Validator',
    'ValidationResult',
    'IDRegistry',
    'InternalRepresentation',
]
