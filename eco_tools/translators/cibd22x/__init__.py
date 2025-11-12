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
    try:
        importer = CIBD22XImporter()
        internal = importer.import_file(xml_file)

        # Convert InternalRepresentation to EMJSON v6
        from eco_tools.translators.adapter_translators import internal_to_emjson_v6
        emjson = internal_to_emjson_v6(internal)

        return emjson
    except Exception as e:
        # Return error in EMJSON format
        return {
            "schema_version": "6.0",
            "diagnostics": [{
                "level": "error",
                "code": "E-IMPORT-FAILED",
                "message": f"Import failed: {str(e)}",
                "stage": "import",
                "ts": "",
                "path": xml_file,
                "context": str(type(e).__name__),
                "source": "cibd22x_importer"
            }]
        }
