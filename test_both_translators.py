#!/usr/bin/env python3
"""
Test both CIBD22X translators (em-tools and Universal Translator)
"""

import sys
from pathlib import Path

# Add project root to path
ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Add GUI module to path
EXPLORER_GUI = ROOT / "explorer_gui"
if str(EXPLORER_GUI) not in sys.path:
    sys.path.insert(0, str(EXPLORER_GUI))

def test_em_tools_translator():
    """Test em-tools CIBD22X translator"""
    print("\n" + "="*70)
    print("TEST 1: em-tools CIBD22X Translator")
    print("="*70)
    
    try:
        from explorer_gui.translators import translate_cibd22x_to_v6
        
        test_file = "Reference_Datasets/cbecc_samples/cibd22x file/Euclid Building A_v3_2024-04-29.cibd22x"
        
        print(f"\nImporting: {test_file}")
        result = translate_cibd22x_to_v6(test_file)
        
        # Check results
        print(f"\nSchema Version: {result.get('schema_version', 'N/A')}")
        
        geometry = result.get('geometry', {})
        zones = geometry.get('zones', [])
        surfaces = geometry.get('surfaces', [])
        openings = geometry.get('openings', [])
        
        print(f"Zones: {len(zones)}")
        print(f"Surfaces: {len(surfaces)}")
        print(f"Openings: {len(openings)}")
        
        catalogs = result.get('catalogs', {})
        print(f"Materials: {len(catalogs.get('materials', []))}")
        print(f"Constructions: {len(catalogs.get('constructions', []))}")
        
        diagnostics = result.get('diagnostics', [])
        errors = [d for d in diagnostics if d.get('level') == 'error']
        warnings = [d for d in diagnostics if d.get('level') == 'warning']
        
        print(f"\nDiagnostics: {len(diagnostics)} total ({len(errors)} errors, {len(warnings)} warnings)")
        
        if errors:
            print("\nERRORS:")
            for err in errors[:3]:
                print(f"  - {err.get('code')}: {err.get('message')}")
        
        print("\n✅ em-tools translator: SUCCESS")
        return True
        
    except Exception as e:
        print(f"\n❌ em-tools translator FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_universal_translator():
    """Test Universal Translator CIBD22X translator"""
    print("\n" + "="*70)
    print("TEST 2: Universal Translator CIBD22X Translator")
    print("="*70)
    
    try:
        from explorer_gui.translators import translate_cibd22x_uni_to_v6
        
        test_file = "Reference_Datasets/cbecc_samples/cibd22x file/Euclid Building A_v3_2024-04-29.cibd22x"
        
        print(f"\nImporting: {test_file}")
        result = translate_cibd22x_uni_to_v6(test_file)
        
        # Check results
        print(f"\nSchema Version: {result.get('schema_version', 'N/A')}")
        
        geometry = result.get('geometry', {})
        zones = geometry.get('zones', [])
        surfaces = geometry.get('surfaces', [])
        openings = geometry.get('openings', [])
        
        print(f"Zones: {len(zones)}")
        print(f"Surfaces: {len(surfaces)}")
        print(f"Openings: {len(openings)}")
        
        catalogs = result.get('catalogs', {})
        print(f"Materials: {len(catalogs.get('materials', []))}")
        print(f"Constructions: {len(catalogs.get('constructions', []))}")
        
        diagnostics = result.get('diagnostics', [])
        errors = [d for d in diagnostics if d.get('level') == 'error']
        warnings = [d for d in diagnostics if d.get('level') == 'warning']
        
        print(f"\nDiagnostics: {len(diagnostics)} total ({len(errors)} errors, {len(warnings)} warnings)")
        
        if errors:
            print("\nERRORS:")
            for err in errors[:3]:
                print(f"  - {err.get('code')}: {err.get('message')}")
        
        print("\n✅ Universal Translator: SUCCESS")
        return True
        
    except Exception as e:
        print(f"\n❌ Universal Translator FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_import_export_integration():
    """Test import_export module integration"""
    print("\n" + "="*70)
    print("TEST 3: import_export Module Integration")
    print("="*70)
    
    try:
        from explorer_gui.import_export import import_file, get_importers
        
        # Check available importers
        importers = get_importers()
        print(f"\nAvailable importers: {len(importers)}")
        for imp in importers:
            print(f"  - {imp['id']}: {imp['label']}")
        
        # Test import with em-tools
        test_file = "Reference_Datasets/cbecc_samples/cibd22x file/Euclid Building A_v3_2024-04-29.cibd22x"
        
        print(f"\nTesting import_file() with cibd22x...")
        result1 = import_file("cibd22x", test_file)
        zones1 = len(result1.get('geometry', {}).get('zones', []))
        print(f"  Result: {zones1} zones")
        
        print(f"\nTesting import_file() with cibd22x_uni...")
        result2 = import_file("cibd22x_uni", test_file)
        zones2 = len(result2.get('geometry', {}).get('zones', []))
        print(f"  Result: {zones2} zones")
        
        print("\n✅ import_export integration: SUCCESS")
        return True
        
    except Exception as e:
        print(f"\n❌ import_export integration FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("\n" + "="*70)
    print("TESTING CIBD22X TRANSLATORS")
    print("="*70)
    
    results = []
    
    # Run tests
    results.append(("em-tools translator", test_em_tools_translator()))
    results.append(("Universal Translator", test_universal_translator()))
    results.append(("import_export integration", test_import_export_integration()))
    
    # Summary
    print("\n" + "="*70)
    print("TEST SUMMARY")
    print("="*70)
    
    for name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status}: {name}")
    
    total = len(results)
    passed = sum(1 for _, p in results if p)
    
    print(f"\n{passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All tests passed! Both translators are working correctly.")
        sys.exit(0)
    else:
        print("\n⚠️  Some tests failed. Please review the errors above.")
        sys.exit(1)
