#!/usr/bin/env python3
"""
Final Validation Test Suite
Tests all available CIBD models (CIBD22X and CIBD25)
"""

import sys
import os
sys.path.insert(0, '/Users/DavidM/Documents/ECO_Alpha/eco_tools_parser')

from eco_tools.formats.cibd25_adapter import CIBD25Adapter
from eco_tools.formats.cibd22x_adapter import CIBD22XAdapter
from eco_tools.core.format_detector import FormatDetector
import traceback


def test_file(file_path: str) -> dict:
    """Test a single file - detect format, parse, and validate"""
    result = {
        'file': os.path.basename(file_path),
        'path': file_path,
        'size_kb': os.path.getsize(file_path) / 1024,
        'format': None,
        'version': None,
        'parse_success': False,
        'ir_success': False,
        'error': None,
        'objects': 0,
        'zones': 0,
        'surfaces': 0,
        'materials': 0
    }

    try:
        # Detect format
        detector = FormatDetector()
        format_info = detector.detect(file_path)
        result['format'] = format_info.format_type
        result['version'] = format_info.version

        # Select adapter
        if format_info.format_type == 'CIBD25':
            adapter = CIBD25Adapter()
        elif format_info.format_type in ('CIBD22', 'CIBD22X'):
            adapter = CIBD22XAdapter()
        else:
            result['error'] = f"Unsupported format: {format_info.format_type}"
            return result

        # Parse to objects (low-level)
        if format_info.format_type == 'CIBD25':
            objects = adapter.parse_to_objects(file_path)
        else:
            # CIBD22X doesn't have parse_to_objects, skip this
            objects = []

        result['objects'] = len(objects)
        result['parse_success'] = True

        # Parse to IR (high-level)
        internal = adapter.parse(file_path)
        result['ir_success'] = True
        result['zones'] = len(internal.zones)
        result['surfaces'] = len(internal.surfaces)
        result['materials'] = len(internal.materials)

    except Exception as e:
        result['error'] = str(e)
        # traceback.print_exc()  # Uncomment for debugging

    return result


def main():
    """Run validation on all available CIBD models"""

    print("=" * 80)
    print("FINAL VALIDATION TEST SUITE")
    print("=" * 80)
    print()

    # Define test file locations
    test_sets = {
        'CIBD25 Testing Samples': [
            '/Users/DavidM/Documents/ECO_Alpha/cibd25_testing/originals/01_SmallOffice.cibd25',
            '/Users/DavidM/Documents/ECO_Alpha/cibd25_testing/originals/02_SmallRestaurant.cibd25',
            '/Users/DavidM/Documents/ECO_Alpha/cibd25_testing/originals/03_Warehouse.cibd25',
            '/Users/DavidM/Documents/ECO_Alpha/cibd25_testing/originals/04_MediumOffice.cibd25',
            '/Users/DavidM/Documents/ECO_Alpha/cibd25_testing/originals/05_LargeRetail.cibd25',
        ],
        'CIBD25 Standard Tests': [
            '/Users/DavidM/Dropbox/EM-Tools-Assets/CBECC Models/2025 Sample Models/StandardModelTests/010012-SchSml-CECStd.cibd25',
            '/Users/DavidM/Dropbox/EM-Tools-Assets/CBECC Models/2025 Sample Models/StandardModelTests/020012-OffSml-CECStd.cibd25',
            '/Users/DavidM/Dropbox/EM-Tools-Assets/CBECC Models/2025 Sample Models/StandardModelTests/030012-OffMed-CECStd.cibd25',
            '/Users/DavidM/Dropbox/EM-Tools-Assets/CBECC Models/2025 Sample Models/StandardModelTests/060012-RstntSml-CECStd.cibd25',
        ],
        'CIBD22X Roundtrips': [
            '/Users/DavidM/Documents/ECO_Alpha/roundtrip_validation/originals/01_Bressi_Ranch.cibd22x',
            '/Users/DavidM/Documents/ECO_Alpha/roundtrip_validation/originals/02_Mainplace_Mall.cibd22x',
            '/Users/DavidM/Documents/ECO_Alpha/roundtrip_validation/originals/03_Del_Amo_Circle.cibd22x',
        ],
    }

    all_results = []

    for set_name, files in test_sets.items():
        print(f"\n{set_name}")
        print("-" * 80)

        for file_path in files:
            if not os.path.exists(file_path):
                print(f"  ⚠️  SKIP: {os.path.basename(file_path)} (not found)")
                continue

            result = test_file(file_path)
            all_results.append(result)

            # Display result
            status = "✅" if result['ir_success'] else "❌"
            print(f"  {status} {result['file']}")
            print(f"     Format: {result['format']} v{result['version']}")
            print(f"     Size: {result['size_kb']:.1f} KB")

            if result['ir_success']:
                print(f"     Objects: {result['objects']}")
                print(f"     Zones: {result['zones']}, Surfaces: {result['surfaces']}, Materials: {result['materials']}")
            elif result['parse_success']:
                print(f"     Parsed: {result['objects']} objects (IR mapping failed)")

            if result['error']:
                print(f"     Error: {result['error'][:100]}")

    # Summary
    print()
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)

    total = len(all_results)
    parse_success = sum(1 for r in all_results if r['parse_success'])
    ir_success = sum(1 for r in all_results if r['ir_success'])

    cibd25_count = sum(1 for r in all_results if r['format'] == 'CIBD25')
    cibd22x_count = sum(1 for r in all_results if r['format'] in ('CIBD22', 'CIBD22X'))

    print(f"\nTotal Files Tested: {total}")
    print(f"  CIBD25: {cibd25_count}")
    print(f"  CIBD22X: {cibd22x_count}")
    print()
    print(f"Parse Success: {parse_success}/{total} ({parse_success/total*100:.1f}%)")
    print(f"IR Success: {ir_success}/{total} ({ir_success/total*100:.1f}%)")

    if ir_success == total:
        print("\n🎉 ALL TESTS PASSED! All models parse and convert to IR successfully!")
        return 0
    else:
        print(f"\n⚠️  {total - ir_success} file(s) failed")

        # Show failures
        failures = [r for r in all_results if not r['ir_success']]
        if failures:
            print("\nFailed Files:")
            for r in failures:
                print(f"  - {r['file']}: {r['error'][:100] if r['error'] else 'Unknown error'}")

        return 1


if __name__ == '__main__':
    sys.exit(main())
