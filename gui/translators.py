# --- file: explorer_gui/translators.py
"""
GUI-facing wrappers for eco_tools translators with proper path resolution.
Updated for v7 unified eco_tools package.
"""

from __future__ import annotations
from typing import Dict, Any, List
import sys
from pathlib import Path

# Ensure eco_tools is on path
HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


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
    CIBD22X XML → EMJSON v6 using eco_tools translator.

    Args:
        xml_file: Path to CIBD22X XML file

    Returns:
        EMJSON v6 dict with diagnostics
    """
    try:
        from eco_tools.translators.cibd22x import translate_cibd22x_to_v6 as _impl
    except ImportError as e:
        return {
            "schema_version": "6.0",
            "diagnostics": [{
                "level": "error",
                "code": "E-TRANSLATOR-MISSING",
                "message": f"Cannot import CIBD22X translator from eco_tools: {e}",
                "stage": "import",
                "ts": "",
                "path": "",
                "context": "Ensure eco_tools package is installed and on Python path",
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


def translate_cibd25_to_v6(file_path: str) -> Dict[str, Any]:
    """
    CIBD25 text format → EMJSON v6 using eco_tools translator.

    CIBD25 is a text-based format (same as CIBD22) for Title 24 2025.

    Args:
        file_path: Path to CIBD25 text file (.cibd25)

    Returns:
        EMJSON v6 dict with diagnostics
    """
    try:
        from eco_tools.translators.cibd25 import translate_cibd25_to_v6 as _impl
    except ImportError as e:
        return {
            "schema_version": "6.0",
            "diagnostics": [{
                "level": "error",
                "code": "E-TRANSLATOR-MISSING",
                "message": f"Cannot import CIBD25 translator from eco_tools: {e}",
                "stage": "import",
                "ts": "",
                "path": "",
                "context": "Ensure eco_tools package is installed and on Python path",
                "source": "explorer_gui"
            }]
        }

    try:
        result = _impl(file_path)
        if not isinstance(result, dict):
            return {
                "schema_version": "6.0",
                "diagnostics": [{
                    "level": "error",
                    "code": "E-INVALID-RESULT",
                    "message": f"CIBD25 translator returned invalid result type: {type(result)}",
                    "stage": "import",
                    "ts": "",
                    "path": file_path,
                    "context": "Expected dict",
                    "source": "cibd25_importer"
                }]
            }
        return result
    except Exception as e:
        import traceback
        return {
            "schema_version": "6.0",
            "diagnostics": [{
                "level": "error",
                "code": "E-CIBD25-IMPORT",
                "message": f"CIBD25 import failed: {str(e)}",
                "stage": "import",
                "ts": "",
                "path": file_path,
                "context": traceback.format_exc(),
                "source": "cibd25_importer"
            }]
        }


def translate_cibd22_to_v6(file_path: str) -> Dict[str, Any]:
    """
    CIBD22 text format → EMJSON v6 using eco_tools translator.

    CIBD22 is a text-based format with indentation (not XML).

    Args:
        file_path: Path to CIBD22 text file (.cibd22)

    Returns:
        EMJSON v6 dict with diagnostics
    """
    try:
        from eco_tools.translators.cibd22 import translate_cibd22_to_v6 as _impl
    except ImportError as e:
        return {
            "schema_version": "6.0",
            "diagnostics": [{
                "level": "error",
                "code": "E-TRANSLATOR-MISSING",
                "message": f"Cannot import CIBD22 translator from eco_tools: {e}",
                "stage": "import",
                "ts": "",
                "path": "",
                "context": "Ensure eco_tools package is installed and on Python path",
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
    HBJSON → EMJSON v6 using eco_tools translator.

    HBJSON is Honeybee JSON format from Ladybug Tools for building energy modeling.

    Args:
        file_path: Path to HBJSON file (.hbjson)

    Returns:
        EMJSON v6 dict with diagnostics
    """
    try:
        from eco_tools.translators.hbjson_importer import translate_hbjson_to_v6 as _impl
    except ImportError as e:
        return {
            "schema_version": "6.0",
            "diagnostics": [{
                "level": "error",
                "code": "E-TRANSLATOR-MISSING",
                "message": f"Cannot import HBJSON translator from eco_tools: {e}",
                "stage": "import",
                "ts": "",
                "path": "",
                "context": "Ensure eco_tools package is installed and on Python path",
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
    Export EMJSON v6 → CIBD22X XML string using eco_tools exporter.

    Args:
        em_json: EMJSON v6 dictionary

    Returns:
        XML string (pretty-printed)
    """
    try:
        from eco_tools.exporters.cibd22x_exporter import emjson6_to_cibd22x as _exporter_func, write_xml
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
<!-- Export failed: Cannot import exporter from eco_tools: {e} -->
<!-- Ensure eco_tools package is installed and on Python path -->
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
    Export EMJSON v6 → HBJSON string using eco_tools exporter.

    Args:
        em_json: EMJSON v6 dictionary

    Returns:
        HBJSON string (pretty-printed JSON)
    """
    try:
        from eco_tools.exporters.hbjson_exporter import emjson6_to_hbjson as _exporter_func
        import json

        # Convert to HBJSON
        hbjson = _exporter_func(em_json)

        # Convert to pretty JSON string
        return json.dumps(hbjson, indent=4)

    except ImportError as e:
        return json.dumps({
            "error": f"Export failed: Cannot import exporter from eco_tools: {e}",
            "note": "Ensure eco_tools package is installed and on Python path"
        }, indent=4)
    except Exception as e:
        import traceback
        return json.dumps({
            "error": f"Export failed: {str(e)}",
            "traceback": traceback.format_exc()
        }, indent=4)


def emjson6_to_cibd25(em_json: Dict[str, Any]) -> str:
    """
    Export EMJSON v6 → CIBD25 text format string for Title 24 2025 simulation.

    CIBD25 uses same structure as CIBD22X but with 2025 rulesets:
    - RulesetFilename: "T24_2025.bin"
    - SoftwareVersion: "CBECC 2025.2.0 (1390)"

    This uses the full export pipeline: EMJSON → CIBD22X → Text conversion

    Args:
        em_json: EMJSON v6 dictionary

    Returns:
        CIBD25 text format string ready for CBECC 2025
    """
    try:
        from eco_tools.translators.cibd_xml_to_text import convert_xml_to_text
        import tempfile
        import os

        # Step 1: Export EMJSON to CIBD22X XML using the universal translator
        # (This already handles full building data)
        cibd22x_xml = emjson6_to_cibd22x_uni(em_json)

        # Create temp XML file
        with tempfile.NamedTemporaryFile(mode='w', suffix='_temp.xml', delete=False) as tmp_xml:
            tmp_xml_path = tmp_xml.name
            tmp_xml.write(cibd22x_xml)
            tmp_xml.flush()

        # Step 2: Update metadata for CIBD25
        import xml.etree.ElementTree as ET
        tree = ET.parse(tmp_xml_path)
        root = tree.getroot()

        # Detect namespace
        namespace = ''
        if '}' in root.tag:
            namespace = root.tag.split('}')[0] + '}'

        # Set root attribute for 2025
        root.set('RulesetFilename', 'T24_2025.bin')

        # Update Proj metadata
        proj = root.find(f".//{namespace}Proj") if namespace else root.find(".//Proj")
        if proj is not None:
            for child in proj:
                tag = child.tag.replace(namespace, '') if namespace else child.tag

                if tag == 'SoftwareVersion':
                    child.text = 'CBECC 2025.2.0 (1390)'
                elif tag == 'RulesetFilename':
                    child.text = 'T24_2025.bin'
                elif tag == 'BldgEngyModelVersion':
                    if child.text != '17':
                        child.text = '17'

        # Write updated XML
        ET.indent(tree, space="  ", level=0)
        tree.write(tmp_xml_path, encoding='utf-8', xml_declaration=True)

        # Step 3: Convert XML to text format
        with tempfile.NamedTemporaryFile(mode='w', suffix='.cibd25', delete=False) as tmp_text:
            tmp_text_path = tmp_text.name

        convert_xml_to_text(tmp_xml_path, tmp_text_path)

        # Step 4: Read text content
        with open(tmp_text_path, 'r', encoding='utf-8') as f:
            text_content = f.read()

        # Clean up temp files
        os.unlink(tmp_xml_path)
        os.unlink(tmp_text_path)

        return text_content

    except ImportError as e:
        return f"""# Export failed: Cannot import CIBD25 exporter from eco_tools: {e}
# Ensure eco_tools package is installed and on Python path
"""
    except Exception as e:
        import traceback
        return f"""# Export failed: {str(e)}
# Traceback:
# {traceback.format_exc()}
"""


def translate_gem_to_v6(gem_file: str) -> Dict[str, Any]:
    """
    GEM (IES VE) → EMJSON v6 using eco_tools GEM importer.

    GEM (Geometry Exchange Model) is IES Virtual Environment's XML-based
    geometry format with full 3D vertex data and constructions.

    Args:
        gem_file: Path to GEM XML file (.gem, .xml)

    Returns:
        EMJSON v6 dict with diagnostics
    """
    try:
        from eco_tools.translators.gem import translate_gem_to_v6 as _impl
    except ImportError as e:
        return {
            "schema_version": "6.0",
            "diagnostics": [{
                "level": "error",
                "code": "E-TRANSLATOR-MISSING",
                "message": f"Cannot import GEM translator from eco_tools: {e}",
                "stage": "import",
                "ts": "",
                "path": "",
                "context": "Ensure eco_tools package is installed with GEM support",
                "source": "explorer_gui"
            }]
        }

    try:
        result = _impl(gem_file)

        # Ensure result has proper structure
        if not isinstance(result, dict):
            return {
                "schema_version": "6.0",
                "diagnostics": [{
                    "level": "error",
                    "code": "E-INVALID-RESULT",
                    "message": "GEM translator returned non-dict result",
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
                "path": gem_file,
                "context": traceback.format_exc(),
                "source": "explorer_gui"
            }]
        }


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

    # Convert zones with field mapping
    for z_dict in emjson.get("geometry", {}).get("zones", []):
        # Map EMJSON fields to Zone fields
        zone_data = {
            "id": z_dict.get("id", ""),
            "name": z_dict.get("name", ""),
            "building_type": z_dict.get("building_type", "NR"),
            "multiplier": z_dict.get("multiplier", 1),
        }

        # Convert floor_area_sqft to floor_area_m2 if present
        if "floor_area_sqft" in z_dict:
            zone_data["floor_area_m2"] = z_dict["floor_area_sqft"] * 0.09290304  # sqft to m²
        elif "floor_area_m2" in z_dict:
            zone_data["floor_area_m2"] = z_dict["floor_area_m2"]

        # Convert volume_cuft to volume_m3 if present
        if "volume_cuft" in z_dict:
            zone_data["volume_m3"] = z_dict["volume_cuft"] * 0.0283168  # cuft to m³
        elif "volume_m3" in z_dict:
            zone_data["volume_m3"] = z_dict["volume_m3"]

        # Optional fields
        if "stories_above" in z_dict:
            zone_data["stories_above"] = z_dict["stories_above"]
        if "du_ref" in z_dict:
            zone_data["du_ref"] = z_dict["du_ref"]
        if "space_function" in z_dict:
            zone_data["space_function"] = z_dict["space_function"]
        if "served_by" in z_dict:
            zone_data["served_by"] = z_dict["served_by"]
        if "surfaces" in z_dict:
            zone_data["surfaces"] = z_dict["surfaces"]
        if "annotation" in z_dict:
            zone_data["annotation"] = z_dict["annotation"]

        internal.zones.append(Zone(**zone_data))
    
    # Convert surfaces
    # Handle both formats: dict organized by zone or flat list
    surfaces_data = emjson.get("geometry", {}).get("surfaces", [])
    if isinstance(surfaces_data, dict):
        # Surfaces organized by zone (GEM format)
        for zone_id, zone_surfaces in surfaces_data.items():
            for s_dict in zone_surfaces:
                # Map EMJSON fields to Surface fields
                surface_data = {
                    "id": s_dict.get("id", ""),
                    "name": s_dict.get("name", s_dict.get("id", "")),
                    "parent_zone_id": s_dict.get("parent_zone_id", zone_id),
                    "surface_type": s_dict.get("surface_type", "wall"),
                }

                # Convert area_sqft to area_m2 if present
                if "area_sqft" in s_dict:
                    surface_data["area_m2"] = s_dict["area_sqft"] * 0.09290304  # sqft to m²
                elif "area_m2" in s_dict:
                    surface_data["area_m2"] = s_dict["area_m2"]

                # Optional fields
                if "tilt_deg" in s_dict:
                    surface_data["tilt_deg"] = s_dict["tilt_deg"]
                if "azimuth_deg" in s_dict:
                    surface_data["azimuth_deg"] = s_dict["azimuth_deg"]
                if "construction_ref" in s_dict:
                    surface_data["construction_ref"] = s_dict["construction_ref"]
                elif "construction_id" in s_dict:
                    surface_data["construction_ref"] = s_dict["construction_id"]
                if "adjacency" in s_dict:
                    surface_data["adjacency"] = s_dict["adjacency"]
                if "ext_solar_abs" in s_dict:
                    surface_data["ext_solar_abs"] = s_dict["ext_solar_abs"]
                if "ext_thermal_abs" in s_dict:
                    surface_data["ext_thermal_abs"] = s_dict["ext_thermal_abs"]
                if "adjacent_space_ref" in s_dict:
                    surface_data["adjacent_space_ref"] = s_dict["adjacent_space_ref"]
                if "vertices_m" in s_dict:
                    surface_data["vertices_m"] = s_dict["vertices_m"]
                if "annotation" in s_dict:
                    surface_data["annotation"] = s_dict["annotation"]

                internal.surfaces.append(Surface(**surface_data))
    else:
        # Flat list of surfaces
        for s_dict in surfaces_data:
            # Map EMJSON fields to Surface fields
            surface_data = {
                "id": s_dict.get("id", ""),
                "name": s_dict.get("name", s_dict.get("id", "")),
                "parent_zone_id": s_dict.get("parent_zone_id", ""),
                "surface_type": s_dict.get("surface_type", "wall"),
            }

            # Convert area_sqft to area_m2 if present
            if "area_sqft" in s_dict:
                surface_data["area_m2"] = s_dict["area_sqft"] * 0.09290304  # sqft to m²
            elif "area_m2" in s_dict:
                surface_data["area_m2"] = s_dict["area_m2"]

            # Optional fields
            if "tilt_deg" in s_dict:
                surface_data["tilt_deg"] = s_dict["tilt_deg"]
            if "azimuth_deg" in s_dict:
                surface_data["azimuth_deg"] = s_dict["azimuth_deg"]
            if "construction_ref" in s_dict:
                surface_data["construction_ref"] = s_dict["construction_ref"]
            elif "construction_id" in s_dict:
                surface_data["construction_ref"] = s_dict["construction_id"]
            if "adjacency" in s_dict:
                surface_data["adjacency"] = s_dict["adjacency"]
            if "ext_solar_abs" in s_dict:
                surface_data["ext_solar_abs"] = s_dict["ext_solar_abs"]
            if "ext_thermal_abs" in s_dict:
                surface_data["ext_thermal_abs"] = s_dict["ext_thermal_abs"]
            if "adjacent_space_ref" in s_dict:
                surface_data["adjacent_space_ref"] = s_dict["adjacent_space_ref"]
            if "vertices_m" in s_dict:
                surface_data["vertices_m"] = s_dict["vertices_m"]

            # Handle annotation
            if "annotation" not in surface_data:
                surface_data["annotation"] = {}
            if "annotation" in s_dict:
                surface_data["annotation"].update(s_dict["annotation"])

            internal.surfaces.append(Surface(**surface_data))
    
    # Convert openings
    # Handle both formats: dict organized by zone or flat list
    openings_data = emjson.get("geometry", {}).get("openings", [])
    if isinstance(openings_data, dict):
        # Openings organized by zone (GEM format)
        for zone_id, zone_openings in openings_data.items():
            for o_dict in zone_openings:
                # Map EMJSON fields to Opening fields
                opening_data = {
                    "id": o_dict.get("id", ""),
                    "parent_surface_id": o_dict.get("parent_surface_id", ""),
                    "type": o_dict.get("type", o_dict.get("opening_type", "window")),
                }

                # Convert area_sqft to area_m2 if present
                if "area_sqft" in o_dict:
                    opening_data["area_m2"] = o_dict["area_sqft"] * 0.09290304  # sqft to m²
                elif "area_m2" in o_dict:
                    opening_data["area_m2"] = o_dict["area_m2"]

                # Optional fields
                if "height_m" in o_dict:
                    opening_data["height_m"] = o_dict["height_m"]
                if "width_m" in o_dict:
                    opening_data["width_m"] = o_dict["width_m"]
                if "window_type_ref" in o_dict:
                    opening_data["window_type_ref"] = o_dict["window_type_ref"]
                elif "window_type_id" in o_dict:
                    opening_data["window_type_ref"] = o_dict["window_type_id"]
                if "fenestration_cons_ref" in o_dict:
                    opening_data["fenestration_cons_ref"] = o_dict["fenestration_cons_ref"]
                if "u_factor_SI" in o_dict:
                    opening_data["u_factor_SI"] = o_dict["u_factor_SI"]
                if "shgc" in o_dict:
                    opening_data["shgc"] = o_dict["shgc"]
                if "vt" in o_dict:
                    opening_data["vt"] = o_dict["vt"]
                if "vertices_m" in o_dict:
                    opening_data["vertices_m"] = o_dict["vertices_m"]
                if "annotation" in o_dict:
                    opening_data["annotation"] = o_dict["annotation"]

                internal.openings.append(Opening(**opening_data))
    else:
        # Flat list of openings
        for o_dict in openings_data:
            # Map EMJSON fields to Opening fields
            opening_data = {
                "id": o_dict.get("id", ""),
                "parent_surface_id": o_dict.get("parent_surface_id", ""),
                "type": o_dict.get("type", o_dict.get("opening_type", "window")),
            }

            # Convert area_sqft to area_m2 if present
            if "area_sqft" in o_dict:
                opening_data["area_m2"] = o_dict["area_sqft"] * 0.09290304  # sqft to m²
            elif "area_m2" in o_dict:
                opening_data["area_m2"] = o_dict["area_m2"]

            # Optional fields
            if "height_m" in o_dict:
                opening_data["height_m"] = o_dict["height_m"]
            if "width_m" in o_dict:
                opening_data["width_m"] = o_dict["width_m"]
            if "window_type_ref" in o_dict:
                opening_data["window_type_ref"] = o_dict["window_type_ref"]
            elif "window_type_id" in o_dict:
                opening_data["window_type_ref"] = o_dict["window_type_id"]
            if "fenestration_cons_ref" in o_dict:
                opening_data["fenestration_cons_ref"] = o_dict["fenestration_cons_ref"]
            if "u_factor_SI" in o_dict:
                opening_data["u_factor_SI"] = o_dict["u_factor_SI"]
            if "shgc" in o_dict:
                opening_data["shgc"] = o_dict["shgc"]
            if "vt" in o_dict:
                opening_data["vt"] = o_dict["vt"]
            if "vertices_m" in o_dict:
                opening_data["vertices_m"] = o_dict["vertices_m"]

            # Handle annotation
            if "annotation" not in opening_data:
                opening_data["annotation"] = {}
            if "annotation" in o_dict:
                opening_data["annotation"].update(o_dict["annotation"])

            internal.openings.append(Opening(**opening_data))
    
    # Convert catalogs
    catalogs = emjson.get("catalogs", {})
    for m_dict in catalogs.get("materials", []):
        # Filter and map material fields to match Material dataclass
        material_data = {
            "id": m_dict.get("id", ""),
            "name": m_dict.get("name", ""),
            "material_type": m_dict.get("material_type", "opaque"),  # Default to opaque
        }

        # Map optional fields with correct names
        if "thickness_m" in m_dict:
            material_data["thickness_m"] = m_dict["thickness_m"]
        if "conductivity_w_mk" in m_dict:
            material_data["conductivity_w_mk"] = m_dict["conductivity_w_mk"]
        if "r_value_SI" in m_dict or "r_value_m2k_w" in m_dict:
            material_data["r_value_SI"] = m_dict.get("r_value_SI", m_dict.get("r_value_m2k_w"))
        if "density_kg_m3" in m_dict:
            material_data["density_kg_m3"] = m_dict["density_kg_m3"]
        # Map specific_heat_j_kgk to specific_heat
        if "specific_heat" in m_dict:
            material_data["specific_heat"] = m_dict["specific_heat"]
        elif "specific_heat_j_kgk" in m_dict:
            material_data["specific_heat"] = m_dict["specific_heat_j_kgk"]
        if "thermal_absorptance" in m_dict:
            material_data["thermal_absorptance"] = m_dict["thermal_absorptance"]
        if "solar_absorptance" in m_dict:
            material_data["solar_absorptance"] = m_dict["solar_absorptance"]
        if "visible_absorptance" in m_dict:
            material_data["visible_absorptance"] = m_dict["visible_absorptance"]
        if "annotation" in m_dict:
            material_data["annotation"] = m_dict["annotation"]

        internal.materials.append(Material(**material_data))
    for c_dict in catalogs.get("constructions", []):
        internal.constructions.append(Construction(**c_dict))
    for w_dict in catalogs.get("window_types", []):
        # Filter out fields not in WindowType dataclass (e.g., 'category', 'description', 't24_compliant', etc.)
        allowed_fields = {'id', 'name', 'fenestration_type', 'area_m2', 'u_factor_SI', 'shgc', 'vt',
                          'frame_type', 'glazing_type', 'num_panes', 'gas_fill', 'annotation'}
        filtered_w_dict = {k: v for k, v in w_dict.items() if k in allowed_fields}

        # Map EMJSON field names to WindowType field names
        if 'u_factor' in w_dict and 'u_factor_SI' not in filtered_w_dict:
            filtered_w_dict['u_factor_SI'] = w_dict['u_factor']

        # Ensure required fields exist
        if 'id' not in filtered_w_dict:
            filtered_w_dict['id'] = w_dict.get('id', f"wt_{len(internal.window_types) + 1}")
        if 'name' not in filtered_w_dict:
            filtered_w_dict['name'] = w_dict.get('name', 'Window Type')
        if 'fenestration_type' not in filtered_w_dict:
            filtered_w_dict['fenestration_type'] = 'window'

        internal.window_types.append(WindowType(**filtered_w_dict))

    # Convert schedules
    for sch_dict in catalogs.get("schedules", []):
        # Create a Schedule object - use SimpleNamespace to make it compatible
        from types import SimpleNamespace
        schedule = SimpleNamespace(
            id=sch_dict.get("id", ""),
            name=sch_dict.get("name", ""),
            type=sch_dict.get("type", "fraction"),
            schedule_type=sch_dict.get("schedule_type", ""),
            building_type=sch_dict.get("building_type", ""),
            weekday=sch_dict.get("weekday", []),
            saturday=sch_dict.get("saturday", []),
            sunday=sch_dict.get("sunday", []),
            holiday=sch_dict.get("holiday", [])
        )
        internal.schedules.append(schedule)

    internal.du_types = catalogs.get("du_types", [])

    # Convert systems
    systems = emjson.get("systems", {})
    for h_dict in systems.get("hvac", []):
        # Map EMJSON HVAC fields to HVACSystem fields
        # Required fields for dataclass: id, name, type
        hvac_id = h_dict.get("id", "")
        hvac_name = h_dict.get("name", "")

        # Map system_type string to type integer if present
        system_type_str = h_dict.get("system_type", "").lower()
        if "heat_pump" in system_type_str or system_type_str == "heat_pump":
            hvac_type = 2
        elif "central" in system_type_str:
            hvac_type = 4
        else:
            hvac_type = 1  # Default heating + cooling

        hvac_data = {
            "id": hvac_id,
            "name": hvac_name,
            "type": hvac_type,
        }

        # Optional fields with defaults in dataclass
        if "fuel" in h_dict:
            hvac_data["fuel"] = h_dict["fuel"]
        if "multiplier" in h_dict:
            hvac_data["multiplier"] = h_dict["multiplier"]

        # Copy equipment-type fields if they exist (CBECC format)
        for field in ["heating_systems", "heating_counts", "cooling_systems", "cooling_counts",
                      "heat_pump_systems", "heat_pump_counts", "central_equipment", "central_counts",
                      "zone_terminals", "distribution_ref", "fan_ref", "zone_refs",
                      "floor_area_served", "heating_source", "cooling_source", "distribution_type"]:
            if field in h_dict:
                hvac_data[field] = h_dict[field]

        # Copy equipment details directly to HVACSystem fields (not annotation)
        equipment_fields = [
            "equipment_type", "manufacturer", "model",
            "cooling_type", "cooling_capacity_tons", "cooling_capacity_kw", "cooling_capacity_mbh",
            "cooling_efficiency_eer", "cooling_efficiency_ieer", "cooling_efficiency_seer2",
            "heating_type", "heating_capacity_kw", "heating_capacity_mbh",
            "heating_efficiency_cop", "heating_efficiency_hspf2",
            "airflow_cfm", "minimum_oa_cfm", "fan_control",
            "economizer_type", "economizer_fdd",
            "cooling_setpoint_f", "heating_setpoint_f", "has_bacnet", "has_dcv", "dcv_minimum_oa_cfm",
            "filter_merv"
        ]
        for field in equipment_fields:
            if field in h_dict:
                hvac_data[field] = h_dict[field]

        # Store remaining fields in annotation for export
        annotation = dict(h_dict.get("annotation", {}))
        remaining_fields = ["system_type", "cooling_capacity_btu", "heating_capacity_btu",
                           "description", "template_source", "sizing_method", "sizing_note"]
        for field in remaining_fields:
            if field in h_dict:
                annotation[field] = h_dict[field]

        if annotation:
            hvac_data["annotation"] = annotation

        internal.hvac_systems.append(HVACSystem(**hvac_data))

    # Convert DHW systems with field mapping
    for d_dict in systems.get("dhw", []):
        # Map EMJSON DHW fields to DHWSystem fields
        dhw_data = {
            "id": d_dict.get("id", ""),
            "name": d_dict.get("name", ""),
            "system_type": d_dict.get("system_type", "Unknown"),
        }

        # Optional fields
        if "is_central" in d_dict:
            dhw_data["is_central"] = d_dict["is_central"]
        if "central_system_type" in d_dict:
            dhw_data["central_system_type"] = d_dict["central_system_type"]
        if "water_heaters" in d_dict:
            dhw_data["water_heaters"] = d_dict["water_heaters"]
        if "water_heater_counts" in d_dict:
            dhw_data["water_heater_counts"] = d_dict["water_heater_counts"]
        if "recirculation_loops" in d_dict:
            dhw_data["recirculation_loops"] = d_dict["recirculation_loops"]
        if "distribution_type" in d_dict:
            dhw_data["distribution_type"] = d_dict["distribution_type"]
        if "pipe_insulation_level" in d_dict:
            dhw_data["pipe_insulation_level"] = d_dict["pipe_insulation_level"]
        if "floor_area_served" in d_dict:
            dhw_data["floor_area_served"] = d_dict["floor_area_served"]
        if "dwelling_units_served" in d_dict:
            dhw_data["dwelling_units_served"] = d_dict["dwelling_units_served"]
        if "recirc_type" in d_dict:
            dhw_data["recirc_type"] = d_dict["recirc_type"]
        if "requirements" in d_dict:
            dhw_data["requirements"] = d_dict["requirements"]

        # Store wizard-created fields in annotation for export
        annotation = d_dict.get("annotation", {})
        if "fuel_type" in d_dict:
            annotation["fuel_type"] = d_dict["fuel_type"]
        if "capacity_liters" in d_dict:
            annotation["capacity_liters"] = d_dict["capacity_liters"]
        if "energy_factor" in d_dict:
            annotation["energy_factor"] = d_dict["energy_factor"]
        if "tank_capacity_gallons" in d_dict:
            annotation["tank_capacity_gallons"] = d_dict["tank_capacity_gallons"]
        if "input_rating_btu" in d_dict:
            annotation["input_rating_btu"] = d_dict["input_rating_btu"]
        if "recovery_rate_gph" in d_dict:
            annotation["recovery_rate_gph"] = d_dict["recovery_rate_gph"]

        if annotation:
            dhw_data["annotation"] = annotation

        internal.dhw_systems.append(DHWSystem(**dhw_data))
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


def emjson6_to_cbecc_sddxml(em_json: Dict[str, Any]) -> str:
    """
    Export EMJSON v6 → CBECC-Com SDDXML format with all fixes:
    - PRIORITY 1: HVAC System Grouping with <Cnt> multiplier
    - PRIORITY 2: Construction Assembly Mapping from catalogs
    - PRIORITY 3: Fenestration Type Creation from catalogs

    Args:
        em_json: EMJSON v6 dictionary

    Returns:
        XML string (pretty-printed SDDXML)
    """
    try:
        from emjson_to_cbecc_sddxml import emjson6_to_cbecc_sddxml as _sddxml_exporter
        return _sddxml_exporter(em_json)
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


def emjson6_to_cibd22x_uni(em_json: Dict[str, Any]) -> str:
    """
    Export EMJSON v6 → CIBD22X XML string using cibd22x_uni_base UniversalTranslator.

    DEPRECATED: Use emjson6_to_cbecc_sddxml for CBECC-Com export.

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
            "label": "CIBD22X (V7 Adapter)",
            "description": "Import CIBD22X XML format using v7 adapter: 99.8% coverage, stable IDs, unit conversions, round-trip capable.",
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
        {
            "id": "cibd22",
            "label": "CIBD22 (Text Format - Modular)",
            "description": "Import CIBD22 text format using text parser + CIBD22X modular parsers: reuses all 22 parser modules for consistency.",
            "fn": translate_cibd22_to_v6,
            "extensions": [".cibd22"],
        },
        {
            "id": "gem",
            "label": "GEM (IES Virtual Environment)",
            "description": "Import GEM (Geometry Exchange Model) from IES VE: full 3D geometry, explicit vertices, construction library via GEM→HBJSON→EMJSON pipeline.",
            "fn": translate_gem_to_v6,
            "extensions": [".gem", ".xml"],
        },
        {
            "id": "cibd25",
            "label": "CIBD25 (Text Format - 2025)",
            "description": "Import CIBD25 text-based format (.cibd25 files) for Title 24 2025 compliance modeling. Same structure as CIBD22 with 2025 rulesets.",
            "fn": lambda file_path: translate_cibd25_to_v6(file_path),
            "extensions": [".cibd25"],
        },
        # Legacy translators disabled for now
        # {
        #     "id": "hbjson",
        #     "label": "HBJSON (Honeybee JSON)",
        #     "description": "Import HBJSON format from Ladybug Tools with 3D geometry support. Converts Face3D to areas, preserves full geometry in annotations for round-trip.",
        #     "fn": translate_hbjson_to_v6,
        #     "extensions": [".hbjson", ".json"],
        # },
    ]
