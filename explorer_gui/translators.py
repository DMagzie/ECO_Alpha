# --- file: explorer_gui/translators.py
"""
GUI-facing wrappers for em-tools translators with proper path resolution.
Updated to use production em-tools package.
"""

from __future__ import annotations
from typing import Dict, Any, List
import sys
from pathlib import Path

# Ensure em-tools is on path
HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
EM_TOOLS = ROOT / "em-tools"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(EM_TOOLS) not in sys.path:
    sys.path.insert(0, str(EM_TOOLS))


def detect_cibd_format(file_path: str) -> str:
    """
    Auto-detect whether a file is CIBD22 (text) or CIBD22X (XML).
    
    Args:
        file_path: Path to file
        
    Returns:
        "cibd22" if text format, "cibd22x" if XML format
        
    Detection Strategy:
        - Read first 1KB of file
        - If starts with "<?xml" or "<" → CIBD22X (XML)
        - Otherwise → CIBD22 (text format)
    """
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            first_chunk = f.read(1024).strip()
            
        if first_chunk.startswith('<?xml') or first_chunk.startswith('<'):
            return "cibd22x"
        else:
            return "cibd22"
            
    except Exception:
        # Default to cibd22x for .xml files, cibd22 otherwise
        if file_path.endswith('.xml') or file_path.endswith('.cibd22x'):
            return "cibd22x"
        return "cibd22"


def translate_cibd22x_to_v6(xml_file: str) -> Dict[str, Any]:
    """
    CIBD22X XML → EMJSON v6 using em-tools translator.

    Args:
        xml_file: Path to CIBD22X XML file

    Returns:
        EMJSON v6 dict with diagnostics
    """
    try:
        from emtools.translators.cibd22x_importer import translate_cibd22x_to_v6 as _impl
    except ImportError as e:
        return {
            "schema_version": "6.0",
            "diagnostics": [{
                "level": "error",
                "code": "E-TRANSLATOR-MISSING",
                "message": f"Cannot import CIBD22X translator from em-tools: {e}",
                "stage": "import",
                "ts": "",
                "path": "",
                "context": "Ensure em-tools package is installed and on Python path",
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


def translate_cibd22_to_v6(file_path: str) -> Dict[str, Any]:
    """
    CIBD22 text format → EMJSON v6 using em-tools translator.
    
    CIBD22 is a text-based format with indentation (not XML).

    Args:
        file_path: Path to CIBD22 text file (.cibd22)

    Returns:
        EMJSON v6 dict with diagnostics
    """
    try:
        from emtools.translators.cibd22_importer import translate_cibd22_to_v6 as _impl
    except ImportError as e:
        return {
            "schema_version": "6.0",
            "diagnostics": [{
                "level": "error",
                "code": "E-TRANSLATOR-MISSING",
                "message": f"Cannot import CIBD22 translator from em-tools: {e}",
                "stage": "import",
                "ts": "",
                "path": "",
                "context": "Ensure em-tools package is installed and on Python path",
                "source": "explorer_gui"
            }]
        }

    try:
        result = _impl(file_path)

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
                "path": file_path,
                "context": traceback.format_exc(),
                "source": "explorer_gui"
            }]
        }


def translate_cibd25_to_v6(file_path: str) -> Dict[str, Any]:
    """
    CIBD25 text format → EMJSON v6 using em-tools translator.
    
    CIBD25 is the 2025 version of the text-based CIBD format (same structure as CIBD22).

    Args:
        file_path: Path to CIBD25 text file (.cibd25)

    Returns:
        EMJSON v6 dict with diagnostics
    """
    try:
        from emtools.translators.cibd25_importer import translate_cibd25_to_v6 as _impl
    except ImportError as e:
        return {
            "schema_version": "6.0",
            "diagnostics": [{
                "level": "error",
                "code": "E-TRANSLATOR-MISSING",
                "message": f"Cannot import CIBD25 translator from em-tools: {e}",
                "stage": "import",
                "ts": "",
                "path": "",
                "context": "Ensure em-tools package is installed and on Python path",
                "source": "explorer_gui"
            }]
        }

    try:
        result = _impl(file_path)

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
                "path": file_path,
                "context": traceback.format_exc(),
                "source": "explorer_gui"
            }]
        }


def translate_hbjson_to_v6(file_path: str) -> Dict[str, Any]:
    """
    HBJSON → EMJSON v6 using em-tools translator.
    
    HBJSON is Honeybee JSON format from Ladybug Tools for building energy modeling.

    Args:
        file_path: Path to HBJSON file (.hbjson)

    Returns:
        EMJSON v6 dict with diagnostics
    """
    try:
        from emtools.translators.hbjson_importer import translate_hbjson_to_v6 as _impl
    except ImportError as e:
        return {
            "schema_version": "6.0",
            "diagnostics": [{
                "level": "error",
                "code": "E-TRANSLATOR-MISSING",
                "message": f"Cannot import HBJSON translator from em-tools: {e}",
                "stage": "import",
                "ts": "",
                "path": "",
                "context": "Ensure em-tools package is installed and on Python path",
                "source": "explorer_gui"
            }]
        }

    try:
        result = _impl(file_path)

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
                "path": file_path,
                "context": traceback.format_exc(),
                "source": "explorer_gui"
            }]
        }


def emjson6_to_cibd22x(em_json: Dict[str, Any]) -> str:
    """
    Export EMJSON v6 → CIBD22X XML string using em-tools exporter.

    Args:
        em_json: EMJSON v6 dictionary

    Returns:
        XML string (pretty-printed)
    """
    try:
        from emtools.exporters.cibd22x_exporter import emjson6_to_cibd22x as _exporter_func, write_xml
        from xml.etree import ElementTree as ET
        from xml.dom import minidom
        
        # Convert to XML element tree
        root = _exporter_func(em_json)
        
        # Convert to pretty XML string
        xml_str = ET.tostring(root, encoding="utf-8")
        pretty = minidom.parseString(xml_str).toprettyxml(indent="  ")
        
        return pretty
        
    except ImportError as e:
        return f"""<?xml version="1.0" encoding="UTF-8"?>
<!-- Export failed: Cannot import exporter from em-tools: {e} -->
<!-- Ensure em-tools package is installed and on Python path -->
<Error>
    <Message>Exporter not found</Message>
</Error>
"""
    except Exception as e:
        import traceback
        return f"""<?xml version="1.0" encoding="UTF-8"?>
<!-- Export failed: {str(e)} -->
<!-- Traceback:
{traceback.format_exc()}
-->
<Error>
    <Message>{str(e)}</Message>
</Error>
"""


def emjson6_to_hbjson(em_json: Dict[str, Any]) -> str:
    """
    Export EMJSON v6 → HBJSON string using em-tools exporter.

    Args:
        em_json: EMJSON v6 dictionary

    Returns:
        HBJSON string (pretty-printed JSON)
    """
    try:
        from emtools.exporters.hbjson_exporter import emjson6_to_hbjson as _exporter_func
        import json
        
        # Convert to HBJSON
        hbjson = _exporter_func(em_json)
        
        # Convert to pretty JSON string
        return json.dumps(hbjson, indent=4)
        
    except ImportError as e:
        return json.dumps({
            "error": f"Export failed: Cannot import exporter from em-tools: {e}",
            "note": "Ensure em-tools package is installed and on Python path"
        }, indent=4)
    except Exception as e:
        import traceback
        return json.dumps({
            "error": f"Export failed: {str(e)}",
            "traceback": traceback.format_exc()
        }, indent=4)


# ========================================
# CIBD22X_UNI_BASE TRANSLATOR INTEGRATION
# ========================================

def _internal_repr_to_emjson(internal_repr) -> Dict[str, Any]:
    """
    Convert InternalRepresentation to EMJSON v6 format.
    
    Args:
        internal_repr: InternalRepresentation from cibd22x_uni_base
        
    Returns:
        EMJSON v6 dictionary
    """
    from dataclasses import asdict
    
    emjson = {
        "schema_version": "6.0",
        "project": {
            "name": internal_repr.metadata.get("name", "Unnamed Project"),
            "description": internal_repr.metadata.get("description", ""),
            "location": internal_repr.metadata.get("location", {}),
        },
        "geometry": {
            "zones": [asdict(z) for z in internal_repr.zones],
            "surfaces": [asdict(s) for s in internal_repr.surfaces],
            "openings": [asdict(o) for o in internal_repr.openings],
        },
        "catalogs": {
            "materials": [asdict(m) for m in internal_repr.materials],
            "constructions": [asdict(c) for c in internal_repr.constructions],
            "window_types": [asdict(w) for w in internal_repr.window_types],
            "du_types": internal_repr.du_types,
        },
        "systems": {
            "hvac": [asdict(h) for h in internal_repr.hvac_systems],
            "dhw": [asdict(d) for d in internal_repr.dhw_systems],
            "iaq_fans": [asdict(i) for i in internal_repr.iaq_fans],
            "pv_arrays": [asdict(p) for p in internal_repr.pv_arrays],
        },
        "zone_groups": [asdict(zg) for zg in internal_repr.zone_groups],
        "diagnostics": internal_repr.diagnostics,
    }
    
    return emjson


def _emjson_to_internal_repr(emjson: Dict[str, Any]):
    """
    Convert EMJSON v6 to InternalRepresentation.
    
    Args:
        emjson: EMJSON v6 dictionary
        
    Returns:
        InternalRepresentation for cibd22x_uni_base
    """
    # Import here to avoid circular dependency issues
    UNI_BASE = ROOT / "cibd22x_uni_base"
    if str(UNI_BASE) not in sys.path:
        sys.path.insert(0, str(UNI_BASE))
    
    from eco_tools.core.internal_repr import (
        InternalRepresentation, Zone, Surface, Opening,
        HVACSystem, DHWSystem, IAQFan, Material, Construction,
        WindowType, PVArray, ZoneGroup
    )
    
    internal = InternalRepresentation()
    
    # Convert zones
    for z_dict in emjson.get("geometry", {}).get("zones", []):
        internal.zones.append(Zone(**z_dict))
    
    # Convert surfaces
    for s_dict in emjson.get("geometry", {}).get("surfaces", []):
        internal.surfaces.append(Surface(**s_dict))
    
    # Convert openings
    for o_dict in emjson.get("geometry", {}).get("openings", []):
        internal.openings.append(Opening(**o_dict))
    
    # Convert catalogs
    catalogs = emjson.get("catalogs", {})
    for m_dict in catalogs.get("materials", []):
        internal.materials.append(Material(**m_dict))
    for c_dict in catalogs.get("constructions", []):
        internal.constructions.append(Construction(**c_dict))
    for w_dict in catalogs.get("window_types", []):
        internal.window_types.append(WindowType(**w_dict))
    internal.du_types = catalogs.get("du_types", [])
    
    # Convert systems
    systems = emjson.get("systems", {})
    for h_dict in systems.get("hvac", []):
        internal.hvac_systems.append(HVACSystem(**h_dict))
    for d_dict in systems.get("dhw", []):
        internal.dhw_systems.append(DHWSystem(**d_dict))
    for i_dict in systems.get("iaq_fans", []):
        internal.iaq_fans.append(IAQFan(**i_dict))
    for p_dict in systems.get("pv_arrays", []):
        internal.pv_arrays.append(PVArray(**p_dict))
    
    # Convert zone groups
    for zg_dict in emjson.get("zone_groups", []):
        internal.zone_groups.append(ZoneGroup(**zg_dict))
    
    # Metadata and diagnostics
    internal.metadata = emjson.get("project", {})
    internal.diagnostics = emjson.get("diagnostics", [])
    
    return internal


def translate_cibd22x_uni_to_v6(xml_file: str) -> Dict[str, Any]:
    """
    CIBD22X XML → EMJSON v6 using cibd22x_uni_base UniversalTranslator.
    
    Args:
        xml_file: Path to CIBD22X XML file
        
    Returns:
        EMJSON v6 dict with diagnostics
    """
    try:
        # Add cibd22x_uni_base to path
        UNI_BASE = ROOT / "cibd22x_uni_base"
        if str(UNI_BASE) not in sys.path:
            sys.path.insert(0, str(UNI_BASE))
        
        from eco_tools.core.translator import UniversalTranslator
        
        # Create translator
        translator = UniversalTranslator()
        
        # Load CIBD22X file to internal representation
        internal_repr = translator.load(xml_file)
        
        # Convert to EMJSON
        emjson = _internal_repr_to_emjson(internal_repr)
        
        return emjson
        
    except ImportError as e:
        return {
            "schema_version": "6.0",
            "diagnostics": [{
                "level": "error",
                "code": "E-TRANSLATOR-MISSING",
                "message": f"Cannot import UniversalTranslator from cibd22x_uni_base: {e}",
                "stage": "import",
                "ts": "",
                "path": "",
                "context": "Ensure cibd22x_uni_base package is available",
                "source": "explorer_gui"
            }]
        }
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


def emjson6_to_cibd22x_uni(em_json: Dict[str, Any]) -> str:
    """
    Export EMJSON v6 → CIBD22X XML string using cibd22x_uni_base UniversalTranslator.
    
    Args:
        em_json: EMJSON v6 dictionary
        
    Returns:
        XML string (pretty-printed)
    """
    try:
        # Add cibd22x_uni_base to path
        UNI_BASE = ROOT / "cibd22x_uni_base"
        if str(UNI_BASE) not in sys.path:
            sys.path.insert(0, str(UNI_BASE))
        
        from eco_tools.core.translator import UniversalTranslator
        from xml.etree import ElementTree as ET
        from xml.dom import minidom
        import tempfile
        
        # Convert EMJSON to internal representation
        internal_repr = _emjson_to_internal_repr(em_json)
        
        # Create translator
        translator = UniversalTranslator()
        
        # Save to temporary file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.xml', delete=False) as tmp:
            tmp_path = tmp.name
        
        translator.save(internal_repr, tmp_path, 'CIBD22X')
        
        # Read back as string
        with open(tmp_path, 'r') as f:
            xml_content = f.read()
        
        # Clean up temp file
        import os
        os.unlink(tmp_path)
        
        return xml_content
        
    except ImportError as e:
        return f"""<?xml version="1.0" encoding="UTF-8"?>
<!-- Export failed: Cannot import UniversalTranslator from cibd22x_uni_base: {e} -->
<!-- Ensure cibd22x_uni_base package is available -->
<Error>
    <Message>Exporter not found</Message>
</Error>
"""
    except Exception as e:
        import traceback
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
    """
    Return metadata for all available importers.
    
    Returns:
        List of importer metadata dicts with id, label, description, extensions
    """
    return [
        {
            "id": "cibd22x",
            "label": "CIBD22X (em-tools)",
            "description": "Import CIBD22X XML format using em-tools modular parser: stable IDs, unit conversions, round-trip capable.",
            "fn": translate_cibd22x_to_v6,
            "extensions": [".xml", ".cibd22x"],
        },
        {
            "id": "cibd22x_uni",
            "label": "CIBD22X (Universal Translator)",
            "description": "Import CIBD22X XML format using cibd22x_uni_base UniversalTranslator: adapter-based architecture with format detection and validation.",
            "fn": translate_cibd22x_uni_to_v6,
            "extensions": [".xml", ".cibd22x"],
        },
        # Legacy translators disabled for now
        # {
        #     "id": "cibd22",
        #     "label": "CIBD22 (Text Format)",
        #     "description": "Import CIBD22 text-based format (.cibd22 files) with enhanced heuristic resolution, materials library, and interior surface support.",
        #     "fn": translate_cibd22_to_v6,
        #     "extensions": [".cibd22"],
        # },
        # {
        #     "id": "cibd25",
        #     "label": "CIBD25 (Text Format - 2025)",
        #     "description": "Import CIBD25 text-based format (.cibd25 files) for Title 24 2025 compliance modeling. Same structure as CIBD22 with 2025 rulesets.",
        #     "fn": translate_cibd25_to_v6,
        #     "extensions": [".cibd25"],
        # },
        # {
        #     "id": "hbjson",
        #     "label": "HBJSON (Honeybee JSON)",
        #     "description": "Import HBJSON format from Ladybug Tools with 3D geometry support. Converts Face3D to areas, preserves full geometry in annotations for round-trip.",
        #     "fn": translate_hbjson_to_v6,
        #     "extensions": [".hbjson", ".json"],
        # },
    ]
