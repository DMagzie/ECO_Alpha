#!/usr/bin/env python3
"""
Test script to verify GUI changes for CIBD22X-only support.
"""

import sys
from pathlib import Path

# Add project root to path
ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Add explorer_gui to path
EXPLORER_GUI = ROOT / "explorer_gui"
if str(EXPLORER_GUI) not in sys.path:
    sys.path.insert(0, str(EXPLORER_GUI))


def test_list_importers():
    """Test that list_importers only returns CIBD22X."""
    from explorer_gui.translators import list_importers
    
    print("=" * 80)
    print("TEST: list_importers() - Should return ONLY CIBD22X")
    print("=" * 80)
    
    importers = list_importers()
    
    print(f"\nNumber of importers: {len(importers)}")
    print("\nImporters:")
    for imp in importers:
        print(f"  - ID: {imp['id']}")
        print(f"    Label: {imp['label']}")
        print(f"    Extensions: {imp['extensions']}")
        print()
    
    # Verify only CIBD22X
    assert len(importers) == 1, f"Expected 1 importer, got {len(importers)}"
    assert importers[0]['id'] == 'cibd22x', f"Expected cibd22x, got {importers[0]['id']}"
    
    print("✅ PASS: Only CIBD22X importer available\n")


def test_get_importers():
    """Test that get_importers only returns CIBD22X."""
    from explorer_gui.import_export import get_importers
    
    print("=" * 80)
    print("TEST: get_importers() - Should return ONLY CIBD22X")
    print("=" * 80)
    
    importers = get_importers()
    
    print(f"\nNumber of importers: {len(importers)}")
    print("\nImporters:")
    for imp in importers:
        print(f"  - ID: {imp['id']}")
        print(f"    Label: {imp['label']}")
        print()
    
    # Verify only CIBD22X
    assert len(importers) == 1, f"Expected 1 importer, got {len(importers)}"
    assert importers[0]['id'] == 'cibd22x', f"Expected cibd22x, got {importers[0]['id']}"
    
    print("✅ PASS: Only CIBD22X importer available\n")


def test_import_cibd22x():
    """Test that CIBD22X import still works."""
    from explorer_gui.import_export import import_file
    
    print("=" * 80)
    print("TEST: import_file('cibd22x', ...) - Should work")
    print("=" * 80)
    
    # Find a test CIBD22X file
    test_file = ROOT / "Reference_Datasets/cbecc_samples/cibd22x file/SMUD-Office-Bldg-2016-HPWH-Eff-01-E.xml"
    
    if not test_file.exists():
        print(f"⚠️  SKIP: Test file not found: {test_file}")
        return
    
    print(f"\nImporting: {test_file.name}")
    
    result = import_file("cibd22x", str(test_file))
    
    # Check result
    assert isinstance(result, dict), "Result should be a dictionary"
    assert "schema_version" in result, "Result should have schema_version"
    assert result["schema_version"] == "6.0", f"Expected schema_version 6.0, got {result['schema_version']}"
    
    # Check diagnostics
    diagnostics = result.get("diagnostics", [])
    errors = [d for d in diagnostics if d.get("level") == "error"]
    
    print(f"\nDiagnostics: {len(diagnostics)} total, {len(errors)} errors")
    
    if errors:
        print("\nErrors:")
        for err in errors[:5]:
            print(f"  - {err.get('code')}: {err.get('message')}")
    
    assert len(errors) == 0, f"Import should have no errors, got {len(errors)}"
    
    # Check geometry
    zones = result.get("geometry", {}).get("zones", [])
    print(f"\nParsed {len(zones)} zones")
    
    print("✅ PASS: CIBD22X import works correctly\n")


def test_import_legacy_formats_rejected():
    """Test that legacy formats are rejected."""
    from explorer_gui.import_export import import_file
    
    print("=" * 80)
    print("TEST: import_file('cibd22', ...) - Should be REJECTED")
    print("=" * 80)
    
    result = import_file("cibd22", "dummy_path.cibd22")
    
    # Check that it's an error
    assert isinstance(result, dict), "Result should be a dictionary"
    diagnostics = result.get("diagnostics", [])
    errors = [d for d in diagnostics if d.get("level") == "error"]
    
    assert len(errors) > 0, "Should have error for unsupported format"
    assert "cibd22x" in errors[0].get("message", "").lower() or "only" in errors[0].get("context", "").lower(), \
        "Error should mention CIBD22X-only support"
    
    print(f"\nError message: {errors[0].get('message')}")
    print(f"Context: {errors[0].get('context')}")
    
    print("✅ PASS: Legacy format correctly rejected\n")


def test_export_cibd22x():
    """Test that CIBD22X export still works."""
    from explorer_gui.translators import emjson6_to_cibd22x
    
    print("=" * 80)
    print("TEST: emjson6_to_cibd22x(...) - Should work")
    print("=" * 80)
    
    # Sample EMJSON v6
    sample_emjson = {
        "schema_version": "6.0",
        "project": {
            "name": "Test Project"
        },
        "geometry": {
            "zones": []
        }
    }
    
    result = emjson6_to_cibd22x(sample_emjson)
    
    # Check result is XML string
    assert isinstance(result, str), "Result should be a string"
    assert "<?xml" in result, "Result should be XML"
    assert "CBECC" in result or "Project" in result, "Result should contain CIBD elements"
    
    print(f"\nGenerated XML ({len(result)} bytes)")
    print("First 200 chars:")
    print(result[:200])
    
    print("\n✅ PASS: CIBD22X export works correctly\n")


def main():
    """Run all tests."""
    print("\n" + "=" * 80)
    print("GUI CIBD22X-ONLY SUPPORT TESTS")
    print("=" * 80 + "\n")
    
    tests = [
        test_list_importers,
        test_get_importers,
        test_import_cibd22x,
        test_import_legacy_formats_rejected,
        test_export_cibd22x,
    ]
    
    passed = 0
    failed = 0
    skipped = 0
    
    for test in tests:
        try:
            test()
            passed += 1
        except AssertionError as e:
            print(f"❌ FAIL: {e}\n")
            failed += 1
        except Exception as e:
            if "SKIP" in str(e):
                skipped += 1
            else:
                print(f"❌ ERROR: {e}\n")
                import traceback
                traceback.print_exc()
                failed += 1
    
    print("\n" + "=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    print(f"Total: {len(tests)}")
    print(f"✅ Passed: {passed}")
    print(f"❌ Failed: {failed}")
    print(f"⚠️  Skipped: {skipped}")
    print("=" * 80 + "\n")
    
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
