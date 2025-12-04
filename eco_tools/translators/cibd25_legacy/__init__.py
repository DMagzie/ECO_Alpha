"""
Legacy CIBD22X → CIBD25 translator.

This module contains the original XML-based translator that has been preserved
for reference and cross-validation purposes. It is not recommended for production use.

Use the new direct writer instead: eco_tools.translators.cibd25.direct_writer

Legacy Components:
- cibd_xml_to_text_legacy.py - Original XML→Text converter (has known issues)
- translate_cibd_legacy.py - Original CLI wrapper script

Known Issues:
- Missing commercial catalogs (causes 101 errors)
- VentSpcFunc on wrong element types (ResZn instead of Spc)
- Window type data not mapped to instances
- Intermediate XML step loses information

Migration Path:
OLD: EMJSON → CIBD22X → cibd_xml_to_text_legacy.py → CIBD25 (buggy)
NEW: EMJSON → cibd25/direct_writer.py → CIBD25 (clean)
"""

__version__ = "1.0.0-legacy"
__status__ = "deprecated"
