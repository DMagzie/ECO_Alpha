import pytest
import json
from cbecc.export_emjson_v5_to_cibd22x import export_emjson_v5_to_cibd22x

def test_export_emjson_v5_to_cibd22x():
    # Example EMJSON v5 model
    em_v5 = {
        "project": {
            "name": "Test Project",
            "location": {
                "city": "Test City",
                "state": "Test State"
            }
        },
        "scenarios": [
            {"name": "Test Scenario", "zones": [{"name": "Zone 1"}]}
        ]
    }

    # Perform the export
    xml_output = export_emjson_v5_to_cibd22x(em_v5)

    # Check that the output is a valid XML string
    assert isinstance(xml_output, str)
    assert "<CBECCProject>" in xml_output
    assert "<Project>" in xml_output
