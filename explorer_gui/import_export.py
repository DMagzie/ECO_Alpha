# --- file: explorer_gui/import_export.py
"""
Import/export routers for the GUI with enhanced error handling.
"""

from __future__ import annotations
from typing import Dict, Any, List
import os
import tempfile

# Import from local translators module
from .translators import (
    list_importers,
    translate_cibd22_to_v6 as _translate_cibd22_to_v6,
    translate_cibd22x_to_v6 as _translate_cibd22x_to_v6,
    emjson6_to_cibd22x as _emjson6_to_cibd22x,
)


def get_importers() -> List[Dict[str, Any]]:
    """Return metadata for all available importers (for menus/dialogs)."""
    return list_importers()


def import_file(importer_id: str, file_path: str) -> Dict[str, Any]:
    """
    Dispatch to the selected importer and return EMJSON v6 dict with diagnostics.

    Args:
        importer_id: one of {"cibd22", "cibd22x"} from translators.list_importers()
        file_path: path to a source file on disk (or uploaded file object)

    Returns:
        EMJSON v6 dictionary with diagnostics
    """
    if not isinstance(importer_id, str) or not importer_id.strip():
        return {
            "schema_version": "6.0",
            "diagnostics": [{
                "level": "error",
                "code": "E-IMPORTER",
                "message": "No importer specified.",
                "stage": "import",
                "ts": "",
                "path": "",
                "context": "",
                "source": "import_export"
            }]
        }

    if not file_path:
        return {
            "schema_version": "6.0",
            "diagnostics": [{
                "level": "error",
                "code": "E-PATH",
                "message": "No file path provided.",
                "stage": "import",
                "ts": "",
                "path": "",
                "context": "",
                "source": "import_export"
            }]
        }

    # Handle file-like objects (Streamlit uploaded files)
    actual_path = file_path
    temp_file = None

    try:
        # Check if it's a file-like object (has .read method)
        if hasattr(file_path, 'read'):
            # Create temporary file
            temp_file = tempfile.NamedTemporaryFile(mode='wb', delete=False, suffix='.xml')
            temp_file.write(file_path.read())
            temp_file.close()
            actual_path = temp_file.name

        if not os.path.isfile(actual_path):
            return {
                "schema_version": "6.0",
                "diagnostics": [{
                    "level": "error",
                    "code": "E-PATH",
                    "message": f"File not found: {file_path}",
                    "stage": "import",
                    "ts": "",
                    "path": str(file_path),
                    "context": "",
                    "source": "import_export"
                }]
            }

        imp = importer_id.strip().lower()

        if imp == "cibd22":
            result = _translate_cibd22_to_v6(actual_path)
        elif imp == "cibd22x":
            result = _translate_cibd22x_to_v6(actual_path)
        else:
            result = {
                "schema_version": "6.0",
                "diagnostics": [{
                    "level": "error",
                    "code": "E-IMPORTER",
                    "message": f"Unknown importer: {importer_id}",
                    "stage": "import",
                    "ts": "",
                    "path": "",
                    "context": f"Available: cibd22, cibd22x",
                    "source": "import_export"
                }]
            }

        return result

    finally:
        # Clean up temp file
        if temp_file:
            try:
                os.unlink(temp_file.name)
            except:
                pass


# ---- Legacy wrappers (kept for compatibility) ----

def translate_cibd22_to_v6(xml_file: str) -> Dict[str, Any]:
    """Legacy entrypoint for cibd22 (XML)."""
    return import_file("cibd22", xml_file)


def translate_cibd22x_to_v6(xml_file: str) -> Dict[str, Any]:
    """Legacy entrypoint for cibd22x."""
    return import_file("cibd22x", xml_file)


# ---- Export helper ----

def export_emjson6_to_cibd22x(em_json: Dict[str, Any], out_path: str) -> Dict[str, Any]:
    """
    Export EMJSON v6 -> CIBD22x XML and write to file.

    Args:
        em_json: EMJSON v6 dictionary
        out_path: Output file path

    Returns:
        Diagnostics dict with success/error info
    """
    try:
        xml_text = _emjson6_to_cibd22x(em_json)
    except Exception as e:
        import traceback
        return {
            "diagnostics": [{
                "level": "error",
                "code": "E-EXPORT",
                "message": str(e),
                "stage": "export",
                "ts": "",
                "path": out_path,
                "context": traceback.format_exc(),
                "source": "import_export"
            }]
        }

    try:
        parent = os.path.dirname(out_path)
        if parent and not os.path.isdir(parent):
            os.makedirs(parent, exist_ok=True)

        with open(out_path, "w", encoding="utf-8") as f:
            f.write(xml_text)

        return {
            "diagnostics": [{
                "level": "info",
                "code": "I-EXPORT-SUCCESS",
                "message": f"Successfully exported to {out_path}",
                "stage": "export",
                "ts": "",
                "path": out_path,
                "context": f"File size: {len(xml_text)} bytes",
                "source": "import_export"
            }]
        }
    except Exception as e:
        import traceback
        return {
            "diagnostics": [{
                "level": "error",
                "code": "E-IO",
                "message": str(e),
                "stage": "export",
                "ts": "",
                "path": out_path,
                "context": traceback.format_exc(),
                "source": "import_export"
            }]
        }