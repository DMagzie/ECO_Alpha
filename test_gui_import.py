#!/usr/bin/env python3
"""
Quick test script to verify GUI translator integration works.
Run before launching Streamlit app.
"""

from pathlib import Path
import sys

# Add project root to path
ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))


def test_translator_import():
    """Test that translator can be imported."""
    print("Testing translator imports...")
    try:
        from explorer_gui.translators import (
            translate_cibd22x_to_v6,
            emjson6_to_cibd22x,
            list_importers
        )
        print("✅ Translators imported successfully")

        # Test list_importers
        importers = list_importers()
        print(f"✅ Found {len(importers)} importers:")
        for imp in importers:
            print(f"   - {imp['id']}: {imp['label']}")

        return True
    except Exception as e:
        print(f"❌ Failed to import translators: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_id_registry():
    """Test ID registry."""
    print("\nTesting ID registry...")
    try:
        from utils.id_registry import IDRegistry
        registry = IDRegistry()

        # Test stable ID generation
        id1 = registry.generate_id("Z", "Living Room", context="Floor1", source_format="CIBD22X")
        id2 = registry.generate_id("Z", "Living Room", context="Floor1", source_format="CIBD22X")

        assert id1 == id2, "IDs should be stable"
        assert id1.startswith("Z-"), "ID should have correct prefix"

        print(f"✅ ID Registry working: {id1}")
        return True
    except Exception as e:
        print(f"❌ ID Registry failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    print("=" * 60)
    print("EM-Tools GUI Integration Test")
    print("=" * 60)

    results = []

    results.append(("Translator Import", test_translator_import()))
    results.append(("ID Registry", test_id_registry()))

    print("\n" + "=" * 60)
    print("Test Summary:")
    print("=" * 60)

    for name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status}: {name}")

    all_passed = all(passed for _, passed in results)

    if all_passed:
        print("\n✅ All tests passed! GUI should work correctly.")
        return 0
    else:
        print("\n❌ Some tests failed. Fix errors before running GUI.")
        return 1


if __name__ == "__main__":
    sys.exit(main())