# tests/test_exporter_v5_roundtrip.py
"""
Drop-in pytest suite for the EMJSON v5 → .cibd22x exporter.

How to run:
  pip install pytest
  pytest -q

These tests assume your exporter is at:
  cbecc/export_emjson_v5_to_cibd22x.py
and exposes:
  export_emjson_v5_to_cibd22x(em_v5: dict) -> str
"""
from __future__ import annotations
from typing import Any, Dict
import xml.etree.ElementTree as ET

import pytest

# Import the exporter under test
from cbecc.export_emjson_v5_to_cibd22x import export_emjson_v5_to_cibd22x


# --------------------------- Helpers ---------------------------

def _xml(xml_str: str) -> ET.Element:
    assert isinstance(xml_str, str), "Exporter must return a string"
    return ET.fromstring(xml_str)


def _count(elem: ET.Element, xpath: str) -> int:
    return len(elem.findall(xpath))


def _text(elem: ET.Element, xpath: str) -> str | None:
    node = elem.find(xpath)
    return node.text if node is not None else None


# --------------------------- Fixtures ---------------------------

@pytest.fixture
def minimal_em() -> Dict[str, Any]:
    """Minimal but representative EM v5 model aligned with exporter logic."""
    return {
        "project": {
            "name": "TestProj",
            "location": {"city": "Carlsbad", "state": "CA", "postal_code": "92009", "climate_zone": "7"},
        },
        "catalogs": {
            "construction_types": [{"name": "Ext Wall Cons", "u": 0.07}],
            "window_types": [{"name": "ResidentialWindowType 1", "u": 0.30, "shgc": 0.25, "vt": 0.55}],
        },
        "scenarios": [
            {
                "name": "Default",
                "zones": [
                    {
                        "id": "Z1",
                        "name": "Zone 1",
                        "floor_area": 1234.5,
                        "surfaces": [
                            {"kind": "wall", "name": "W1", "area": 100.0, "construction_ref": "Ext Wall Cons"},
                            {"kind": "window", "name": "WIN1", "area": 12.0, "window_type_ref": "ResidentialWindowType 1"},
                        ],
                    }
                ],
            }
        ],
        "libraries": {"hvac_systems": [{"name": "HP-1", "system_type": "heat_pump", "zones": ["Z1"]}]},
    }


@pytest.fixture
def with_autowall(minimal_em) -> Dict[str, Any]:
    """Same as minimal_em but add an auto wall that should be skipped."""
    em = dict(minimal_em)
    zones = em["scenarios"][0]["zones"]
    zones[0] = dict(zones[0])  # copy zone
    zones[0]["surfaces"] = list(zones[0]["surfaces"]) + [
        {"kind": "wall", "name": "AUTO_WALL", "area": 999, "auto_wall": True}
    ]
    return em


# --------------------------- Tests ---------------------------

def test_returns_str_and_contains_core_sections(minimal_em):
    xml = export_emjson_v5_to_cibd22x(minimal_em)
    root = _xml(xml)

    # Project & Location
    assert root.tag == "CBECCProject"
    assert _text(root, "./Project/Name") == "TestProj"
    assert _text(root, "./Project/Location/City") == "Carlsbad"
    assert _text(root, "./Project/Location/State") == "CA"
    assert _text(root, "./Project/Location/PostalCode") == "92009"
    assert _text(root, "./Project/Location/ClimateZone") == "7"

    # Geometry and HVAC present
    assert _count(root, ".//ResZn") >= 1, "Expected at least one <ResZn>"
    assert _count(root, ".//ResHVACSys") >= 1, "Expected at least one <ResHVACSys>"


def test_writes_window_types_with_canonical_fields(minimal_em):
    xml = export_emjson_v5_to_cibd22x(minimal_em)
    root = _xml(xml)

    # WindowTypes catalog present
    assert _count(root, ".//Catalogs/WindowTypes/WindowType") >= 1

    # Canonical cibd22x names per crosswalk
    assert _text(root, ".//Catalogs/WindowTypes/WindowType/Name") == "ResidentialWindowType 1"
    assert _text(root, ".//Catalogs/WindowTypes/WindowType/uFactor") in {"0.3", "0.30"}
    assert _text(root, ".//Catalogs/WindowTypes/WindowType/solarHeatGainCoeff") in {"0.25", "0.250"}
    assert _text(root, ".//Catalogs/WindowTypes/WindowType/visibleTrans") in {"0.55", "0.550"}


def test_windows_emitted_in_both_forms_for_import_compat(minimal_em):
    xml = export_emjson_v5_to_cibd22x(minimal_em)
    root = _xml(xml)

    # Nested under wall: ResExtWall/Windows/ResWindow
    nested_count = _count(root, ".//ResExtWall/Windows/ResWindow")
    assert nested_count >= 1, "Expected nested <ResWindow> under a wall"

    # Generic surfaces: Surface surfaceType="Window"
    generic_count = _count(root, './/Geometry//Surface[@surfaceType="Window"]')
    assert generic_count >= 1, "Expected generic <Surface surfaceType='Window'>"


def test_hvac_from_libraries_hvac_systems(minimal_em):
    xml = export_emjson_v5_to_cibd22x(minimal_em)
    root = _xml(xml)

    assert _count(root, ".//HVAC/ResHVACSys") == 1
    assert _text(root, ".//HVAC/ResHVACSys/Name") == "HP-1"
    # ServedZones present and references Z1
    assert _count(root, ".//HVAC/ResHVACSys/ServedZones/ZoneRef") >= 1
    assert _text(root, ".//HVAC/ResHVACSys/ServedZones/ZoneRef") == "Z1"


def test_skip_only_explicit_auto_wall(with_autowall):
    xml = export_emjson_v5_to_cibd22x(with_autowall)
    root = _xml(xml)

    # AUTO_WALL should not appear
    names = [n.text for n in root.findall(".//ResExtWall/Name") if n.text]
    assert "AUTO_WALL" not in names, "Exporter must skip auto walls only when explicitly marked"


def test_type_errors_are_actionable():
    with pytest.raises(TypeError):
        export_emjson_v5_to_cibd22x(None)  # type: ignore[arg-type]
    with pytest.raises(TypeError):
        export_emjson_v5_to_cibd22x({"zones": "not-a-list"})  # bad shape caught during write
