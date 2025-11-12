"""
CIBD22X Translator Module
"""

from .importer import CIBD22XImporter

__all__ = ['CIBD22XImporter', 'translate_cibd22x_to_v6']


def translate_cibd22x_to_v6(xml_file: str):
    """
    Translate CIBD22X XML file to EMJSON v6 format.

    Args:
        xml_file: Path to CIBD22X XML file

    Returns:
        dict: EMJSON v6 dictionary with diagnostics
    """
    importer = CIBD22XImporter()
    result = importer.import_file(xml_file)
    return result
