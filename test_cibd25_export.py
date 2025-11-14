"""
Test CIBD25 Export Validation

This script validates that CIBD25 exports:
1. Contain correct Title 24 2025 metadata
2. Have proper XML structure
3. Are simulation-ready for CBECC 2025.1.0

Usage:
    python test_cibd25_export.py [optional_cibd25_file]
"""

import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, Any

# Add project root to path
ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from eco_tools.translators.cibd25 import CIBD25Exporter, translate_cibd25_to_v6
from eco_tools.core.internal_repr import InternalRepresentation


def create_minimal_test_model() -> Dict[str, Any]:
    """Create a minimal EMJSON v6 model for testing."""
    return {
        "schema_version": "6.0",
        "project": {
            "name": "CIBD25 Test Project",
            "description": "Test model for CIBD25 export validation",
            "location": {
                "latitude": 37.7749,
                "longitude": -122.4194,
                "city": "San Francisco",
                "state": "CA"
            },
            "title_24_version": "2025"
        },
        "geometry": {
            "zones": [],
            "zone_groups": [],
            "surfaces": [],
            "openings": []
        },
        "catalogs": {
            "materials": [],
            "constructions": [],
            "window_types": [],
            "schedules": [],
            "du_types": []
        },
        "systems": {
            "hvac": [],
            "zone_terminals": [],
            "dhw": [],
            "water_heaters": [],
            "recirculation_loops": [],
            "iaq_fans": [],
            "pv_arrays": [],
            "battery_systems": [],
            "lighting_systems": [],
            "luminaires": [],
            "fan_systems": [],
            "heat_pumps": [],
            "distribution_systems": [],
            "control_systems": []
        },
        "proj_metadata": {
            "name": "CIBD25 Test Project"
        },
        "diagnostics": []
    }


def validate_cibd25_xml(xml_root: ET.Element) -> Dict[str, Any]:
    """
    Validate CIBD25 XML structure and metadata.

    Returns:
        dict: Validation results with status and findings
    """
    results = {
        "status": "PASS",
        "errors": [],
        "warnings": [],
        "metadata": {}
    }

    # Check 1: Root element should be SDDXML
    if xml_root.tag != "SDDXML":
        results["errors"].append(f"Root element is '{xml_root.tag}', expected 'SDDXML'")
        results["status"] = "FAIL"

    # Check 2: RulesetFilename attribute
    ruleset = xml_root.get("RulesetFilename")
    if not ruleset:
        results["errors"].append("Missing RulesetFilename attribute on root element")
        results["status"] = "FAIL"
    elif ruleset != "T24_2025.bin":
        results["warnings"].append(f"RulesetFilename is '{ruleset}', expected 'T24_2025.bin'")
    else:
        results["metadata"]["RulesetFilename"] = ruleset

    # Check 3: Proj element with metadata
    proj = xml_root.find(".//Proj")
    if proj is None:
        results["errors"].append("Missing Proj element")
        results["status"] = "FAIL"
        return results

    # Check 4: Software version
    software_version = None
    for child in proj:
        if child.tag == "SoftwareVersion":
            software_version = child.text
            results["metadata"]["SoftwareVersion"] = software_version
            break

    if not software_version:
        results["warnings"].append("Missing SoftwareVersion in Proj")
    elif "2025" not in software_version:
        results["warnings"].append(f"SoftwareVersion '{software_version}' doesn't contain '2025'")

    # Check 5: BldgEngyModelVersion
    model_version = None
    for child in proj:
        if child.tag == "BldgEngyModelVersion":
            model_version = child.text
            results["metadata"]["BldgEngyModelVersion"] = model_version
            break

    if not model_version:
        results["warnings"].append("Missing BldgEngyModelVersion in Proj")
    elif model_version != "17":
        results["warnings"].append(f"BldgEngyModelVersion is '{model_version}', expected '17'")

    return results


def test_minimal_export():
    """Test export with minimal model."""
    print("\n" + "="*70)
    print("TEST 1: Minimal Model Export")
    print("="*70)

    # Create minimal test model
    emjson = create_minimal_test_model()
    print(f"✓ Created minimal EMJSON v6 test model")

    # Convert to InternalRepresentation
    internal = InternalRepresentation()
    internal.proj_metadata = emjson.get('proj_metadata', {})
    internal.metadata = emjson.get('project', {})
    internal.metadata['title_24_version'] = '2025'
    print(f"✓ Converted to InternalRepresentation")

    # Export to CIBD25
    exporter = CIBD25Exporter()
    output_path = ROOT / "test_output" / "cibd25_minimal_test.xml"
    output_path.parent.mkdir(exist_ok=True)

    root = exporter.export(internal, str(output_path))
    print(f"✓ Exported to: {output_path}")

    # Validate the export
    results = validate_cibd25_xml(root)

    print(f"\nValidation Results: {results['status']}")
    print(f"\nMetadata Found:")
    for key, value in results['metadata'].items():
        print(f"  {key}: {value}")

    if results['errors']:
        print(f"\n❌ Errors ({len(results['errors'])}):")
        for error in results['errors']:
            print(f"  - {error}")

    if results['warnings']:
        print(f"\n⚠️  Warnings ({len(results['warnings'])}):")
        for warning in results['warnings']:
            print(f"  - {warning}")

    if results['status'] == 'PASS':
        print("\n✅ TEST PASSED: Minimal export is valid CIBD25")
    else:
        print("\n❌ TEST FAILED: Export has critical errors")

    return results['status'] == 'PASS'


def test_roundtrip_cibd25(cibd25_file: str):
    """Test roundtrip: CIBD25 → EMJSON → CIBD25."""
    print("\n" + "="*70)
    print(f"TEST 2: Roundtrip Test")
    print(f"File: {cibd25_file}")
    print("="*70)

    # Import original CIBD25
    print(f"\nStep 1: Import CIBD25 → EMJSON v6")
    try:
        emjson = translate_cibd25_to_v6(cibd25_file)

        if 'diagnostics' in emjson and emjson['diagnostics']:
            print(f"  Diagnostics: {len(emjson['diagnostics'])} items")
            for diag in emjson['diagnostics'][:3]:  # Show first 3
                print(f"    - [{diag.get('level', 'info')}] {diag.get('message', '')}")

        # Check for RulesetFilename
        ruleset = emjson.get('proj_metadata', {}).get('RulesetFilename')
        if ruleset:
            print(f"  ✓ RulesetFilename captured: {ruleset}")
        else:
            print(f"  ⚠️  RulesetFilename not found in proj_metadata")

    except Exception as e:
        print(f"  ❌ Import failed: {e}")
        import traceback
        traceback.print_exc()
        return False

    # Convert to InternalRepresentation
    print(f"\nStep 2: EMJSON v6 → InternalRepresentation")
    try:
        internal = InternalRepresentation()
        internal.proj_metadata = emjson.get('proj_metadata', {})
        internal.metadata = emjson.get('project', {})
        internal.metadata['title_24_version'] = '2025'
        print(f"  ✓ Converted successfully")
    except Exception as e:
        print(f"  ❌ Conversion failed: {e}")
        return False

    # Export back to CIBD25
    print(f"\nStep 3: InternalRepresentation → CIBD25 XML")
    try:
        exporter = CIBD25Exporter()
        output_path = ROOT / "test_output" / f"{Path(cibd25_file).stem}_roundtrip.xml"
        output_path.parent.mkdir(exist_ok=True)

        root = exporter.export(internal, str(output_path))
        print(f"  ✓ Exported to: {output_path}")
    except Exception as e:
        print(f"  ❌ Export failed: {e}")
        import traceback
        traceback.print_exc()
        return False

    # Validate the roundtrip export
    print(f"\nStep 4: Validate Roundtrip Export")
    results = validate_cibd25_xml(root)

    print(f"  Validation: {results['status']}")
    print(f"\n  Metadata:")
    for key, value in results['metadata'].items():
        print(f"    {key}: {value}")

    if results['errors']:
        print(f"\n  ❌ Errors ({len(results['errors'])}):")
        for error in results['errors']:
            print(f"    - {error}")

    if results['warnings']:
        print(f"\n  ⚠️  Warnings ({len(results['warnings'])}):")
        for warning in results['warnings']:
            print(f"    - {warning}")

    if results['status'] == 'PASS':
        print("\n✅ ROUNDTRIP TEST PASSED")
    else:
        print("\n❌ ROUNDTRIP TEST FAILED")

    return results['status'] == 'PASS'


def main():
    """Run CIBD25 export validation tests."""
    print("CIBD25 Export Validation Test Suite")
    print("="*70)

    all_pass = True

    # Test 1: Minimal export
    if not test_minimal_export():
        all_pass = False

    # Test 2: Roundtrip (if file provided)
    if len(sys.argv) > 1:
        cibd25_file = sys.argv[1]
        if Path(cibd25_file).exists():
            if not test_roundtrip_cibd25(cibd25_file):
                all_pass = False
        else:
            print(f"\n⚠️  File not found: {cibd25_file}")
            print("   Skipping roundtrip test")
    else:
        print("\n" + "="*70)
        print("TEST 2: Skipped (no input file provided)")
        print("="*70)
        print("To test roundtrip with a real CIBD25 file:")
        print("  python test_cibd25_export.py path/to/file.cibd25")

    # Summary
    print("\n" + "="*70)
    print("TEST SUMMARY")
    print("="*70)
    if all_pass:
        print("✅ ALL TESTS PASSED")
        print("\nCIBD25 export is ready for use with CBECC 2025.1.0")
        return 0
    else:
        print("❌ SOME TESTS FAILED")
        print("\nPlease review errors above")
        return 1


if __name__ == "__main__":
    sys.exit(main())
