# --- file: explorer_gui/translators.py
"""
GUI-facing wrappers for translators with proper path resolution.
"""

from __future__ import annotations
from typing import Dict, Any, List
import sys
from pathlib import Path

# Ensure translator modules are on path
HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _resolve_cibd22x_importer():
    """Import the new CIBD22X translator."""
    try:
        # Try root first
        from translate_cibd22x_to_v6 import translate_cibd22x_to_v6 as _impl
        return _impl
    except ImportError:
        try:
            # Try emjson6_full_rt folder
            from emjson6_full_rt.translate_cibd22x_to_v6 import translate_cibd22x_to_v6 as _impl
            return _impl
        except ImportError as e:
            raise ImportError(f"Missing CIBD22x translator: {e}. Ensure translate_cibd22x_to_v6.py is in project root or emjson6_full_rt/.")

def _resolve_emjson6_exporter():
    """Import the EMJSON6 -> CIBD22X exporter."""
    try:
        from emjson6_to_cibd22x import write_xml

        def _wrapper(em_json: Dict[str, Any]) -> str:
            """Wrapper to return XML string instead of writing to file."""
            from xml.etree import ElementTree as ET
            from xml.dom import minidom

            # Import the conversion function
            from emjson6_to_cibd22x import emjson6_to_cibd22x
            root = emjson6_to_cibd22x(em_json)

            # Convert to pretty XML string
            xml_str = ET.tostring(root, encoding="utf-8")
            pretty = minidom.parseString(xml_str).toprettyxml(indent="  ")
            return pretty

        return _wrapper
    except ImportError as e:
        raise ImportError(f"Missing EMJSON6 exporter: {e}")


def translate_cibd22x_to_v6(xml_file: str) -> Dict[str, Any]:
    """
    CIBD22x XML → EMJSON v6 using the new translator.

    Args:
        xml_file: Path to CIBD22X XML file

    Returns:
        EMJSON v6 dict with diagnostics
    """
    try:
        _impl = _resolve_cibd22x_importer()
    except Exception as e:
        return {
            "schema_version": "6.0",
            "diagnostics": [{
                "level": "error",
                "code": "E-TRANSLATOR-MISSING",
                "message": str(e),
                "stage": "import",
                "ts": "",
                "path": "",
                "context": "",
                "source": "explorer_gui"
            }]
        }

    try:
        result = _impl(xml_file)

        # Ensure result has proper structure
        if not isinstance(result, dict):
            return {
                "schema_version": "6.0",
                "diagnostics": [{
                    "level": "error",
                    "code": "E-INVALID-RESULT",
                    "message": "Translator returned non-dict result",
                    "stage": "import",
                    "ts": "",
                    "path": "",
                    "context": str(type(result)),
                    "source": "explorer_gui"
                }]
            }

        # Add GUI-friendly metadata if missing
        result.setdefault("diagnostics", [])

        return result

    except Exception as e:
        import traceback
        return {
            "schema_version": "6.0",
            "diagnostics": [{
                "level": "error",
                "code": "E-TRANSLATION-FAILED",
                "message": str(e),
                "stage": "import",
                "ts": "",
                "path": xml_file,
                "context": traceback.format_exc(),
                "source": "explorer_gui"
            }]
        }


def translate_cibd22_to_v6(xml_file: str) -> Dict[str, Any]:
    """
    Legacy CIBD22 XML → EMJSON v6 (currently redirects to cibd22x translator).

    Args:
        xml_file: Path to CIBD22 XML file

    Returns:
        EMJSON v6 dict with diagnostics
    """
    # For now, both formats use the same translator
    # Later we can add format detection and route appropriately
    return translate_cibd22x_to_v6(xml_file)


def emjson6_to_cibd22x(em_json: Dict[str, Any]) -> str:
    """
    Export EMJSON v6 → CIBD22X XML string.

    Args:
        em_json: EMJSON v6 dictionary

    Returns:
        XML string (pretty-printed)
    """
    try:
        _exporter = _resolve_emjson6_exporter()
        return _exporter(em_json)
    except Exception as e:
        import traceback
        # Return error as XML comment
        return f"""<?xml version="1.0" encoding="UTF-8"?>
<!-- Export failed: {str(e)} -->
<!-- Traceback:
{traceback.format_exc()}
-->
<Error>
    <Message>{str(e)}</Message>
</Error>
"""


def list_importers() -> List[Dict[str, Any]]:
    """Return metadata for all available importers."""
    return [
        {
            "id": "cibd22x",
            "label": "CIBD22X (New Translator)",
            "description": "Import CIBD22X XML using the new EMJSON v6 translator with stable IDs and full unit conversions.",
            "fn": translate_cibd22x_to_v6,
            "extensions": [".xml", ".cibd22x"],
        },
        {
            "id": "cibd22",
            "label": "CIBD22 (Legacy)",
            "description": "Import CIBD22 XML (currently uses same translator as CIBD22X).",
            "fn": translate_cibd22_to_v6,
            "extensions": [".xml"],
        },
    ]