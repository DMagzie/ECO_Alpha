"""ECO Tools - eco_tools module"""

from eco_tools.core.format_detector import FormatDetector, FormatInfo
from eco_tools.core.translator import UniversalTranslator, TranslationResult
from eco_tools.core.validator import Validator, ValidationResult
from eco_tools.core.id_registry import IDRegistry
from eco_tools.core.internal_repr import InternalRepresentation

__version__ = '1.0.0'

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
