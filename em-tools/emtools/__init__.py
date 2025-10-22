# FILE 3: em-tools/emtools/__init__.py
# ============================================================================
"""
EM-Tools: Energy Modeling Translation Hub
EMJSON v6 - Universal building energy model format
"""

__version__ = "0.6.0"

# Main API imports
from emtools.translators.cibd22x_importer import translate_cibd22x_to_v6
from emtools.translators.cibd22_importer import translate_cibd22_to_v6
from emtools.translators.cibd25_importer import translate_cibd25_to_v6
from emtools.translators.hbjson_importer import translate_hbjson_to_v6
from emtools.exporters.cibd22x_exporter import emjson6_to_cibd22x, write_xml
from emtools.exporters.hbjson_exporter import emjson6_to_hbjson, write_hbjson
from emtools.utils.id_registry import IDRegistry

__all__ = [
    'translate_cibd22x_to_v6',
    'translate_cibd22_to_v6',
    'translate_cibd25_to_v6',
    'translate_hbjson_to_v6',
    'emjson6_to_cibd22x',
    'emjson6_to_hbjson',
    'write_xml',
    'write_hbjson',
    'IDRegistry',
]