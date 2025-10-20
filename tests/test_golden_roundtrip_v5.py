# tests/test_golden_roundtrip_v5.py
import xml.etree.ElementTree as ET

from cbecc.export_emjson_v5_to_cibd22x import export_emjson_v5_to_cibd22x

def _xml(s: str) -> ET.Element:
    return ET.fromstring(s)

def _count(root: ET.Element, path: str) -> int:
    return len(root.findall(path))

def _text(root: ET.Element, path: str) -> str | None:
    el = root.find(path)
    return el.text.strip() if el is not None and el.text else None

def test_golden_minimal_roundtrip_signature():
    em = {
        "project": {"name": "GoldenProj", "location": {"city":"Santa Rosa","state":"CA","postal_code":"95401","climate_zone":"2"}},
        "catalogs": {
            "window_types": [{"name":"WT-Golden","u":0.29,"shgc":0.22,"vt":0.44}],
            "construction_types": [{"name":"Cons-Golden","u":0.07}],
        },
        "libraries": {
            "hvac_systems": [{"name":"HP-Golden","system_type":"HeatPump","fuel":"electric","heating_eff":9.5,"cooling_eff":16.0,"served_zones":["GZ1"]}]
        },
        "scenarios": [{
            "name": "Default",
            "zones": [{
                "id":"GZ1","name":"Golden Zone","floor_area":999.0,
                "surfaces":[{"kind":"window","name":"GW-1","area":10.0,"width":2.5,"height":4.0,"window_type_ref":"WT-Golden"}]
            }]
        }]
    }

    xml = export_emjson_v5_to_cibd22x(em)
    assert isinstance(xml, str)

    root = _xml(xml)
    assert root.tag == "CBECCProject"

    # Project location round-trips to both top-level and nested Location
    assert _text(root, "./Project/Name") == "GoldenProj"
    assert _text(root, "./Project/Location/City") == "Santa Rosa"
    assert _text(root, "./Project/Location/State") == "CA"
    assert _text(root, "./Project/Location/PostalCode") == "95401"
    assert _text(root, "./Project/Location/ClimateZone") == "2"

    # Windows present in both forms
    assert _count(root, ".//ResZn/Surface[@surfaceType='Window']") >= 1
    assert _count(root, ".//ResExtWall/Windows/ResWindow") >= 1

    # HVAC present with served zone reference
    assert _count(root, ".//HVAC/ResHVACSys") == 1
    assert _text(root, ".//HVAC/ResHVACSys/Name") == "HP-Golden"
    assert _text(root, ".//HVAC/ResHVACSys/ServedZones/ZoneRef") == "GZ1"
