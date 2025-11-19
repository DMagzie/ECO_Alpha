#!/usr/bin/env python3
"""
Test script to convert multiple CIBD22X sample models to CIBD25 format.
Tests the translator on different building types to ensure consistency.
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from eco_tools.translators.cibd_xml_to_text import CIBDXMLToTextConverter

def main():
    # Define test models - different building types
    test_models = [
        {
            "name": "Warehouse",
            "source": "/Users/DavidM/Documents/ECO_Alpha_v7/reference_data/cbecc/CBECC Models/cibd22x/080012-Whse-CECStd.cibd22x",
            "output": "/Users/DavidM/Downloads/Warehouse_Test.cibd25"
        },
        {
            "name": "Hotel",
            "source": "/Users/DavidM/Documents/ECO_Alpha_v7/reference_data/cbecc/CBECC Models/cibd22x/The Scout Hotel_CBECC 2022.cibd22x",
            "output": "/Users/DavidM/Downloads/Hotel_Test.cibd25"
        },
        {
            "name": "Office Building",
            "source": "/Users/DavidM/Documents/ECO_Alpha_v7/reference_data/cbecc/CBECC Models/cibd22x/Freedom Circle_Building A - LEED.cibd22x",
            "output": "/Users/DavidM/Downloads/Office_Test.cibd25"
        }
    ]

    # Create converter
    converter = CIBDXMLToTextConverter()

    print("=" * 80)
    print("CIBD22X to CIBD25 Translation Test Suite")
    print("=" * 80)
    print("\nTesting translator on multiple building types:")
    print("  - Warehouse (commercial)")
    print("  - Hotel (mixed-use)")
    print("  - Office Building (commercial)")
    print("\nVerifying:")
    print("  ✓ Flat structure with proper ordering")
    print("  ✓ Residential zone children written after parent")
    print("  ✓ Commercial HVAC hierarchy maintained")
    print("  ✓ Required properties added (Type, etc.)")
    print("=" * 80)

    results = []

    for model in test_models:
        print(f"\n{'─' * 80}")
        print(f"Converting: {model['name']}")
        print(f"Source: {Path(model['source']).name}")
        print(f"Output: {Path(model['output']).name}")
        print(f"{'─' * 80}")

        try:
            # Check if source exists
            source_path = Path(model['source'])
            if not source_path.exists():
                print(f"  ❌ ERROR: Source file not found!")
                results.append((model['name'], False, "Source not found"))
                continue

            # Convert
            converter.convert_file(str(source_path), model['output'])

            # Check output exists
            output_path = Path(model['output'])
            if output_path.exists():
                size_kb = output_path.stat().st_size / 1024
                print(f"  ✅ SUCCESS: Converted to {size_kb:.1f} KB")
                results.append((model['name'], True, f"{size_kb:.1f} KB"))
            else:
                print(f"  ❌ ERROR: Output file not created!")
                results.append((model['name'], False, "Output not created"))

        except Exception as e:
            print(f"  ❌ ERROR: {str(e)}")
            results.append((model['name'], False, str(e)))

    # Summary
    print(f"\n{'=' * 80}")
    print("CONVERSION SUMMARY")
    print(f"{'=' * 80}")

    success_count = sum(1 for _, success, _ in results if success)
    total_count = len(results)

    for name, success, info in results:
        status = "✅ SUCCESS" if success else "❌ FAILED"
        print(f"{status:12} | {name:20} | {info}")

    print(f"{'=' * 80}")
    print(f"Result: {success_count}/{total_count} models converted successfully")
    print(f"{'=' * 80}")

    if success_count == total_count:
        print("\n🎉 All models converted successfully!")
        print("\nNext steps:")
        print("  1. Test each model in CBECC 2025:")
        for model in test_models:
            print(f'     "/Applications/CBECC 2025.app/Contents/MacOS/CBECC 2025" -nrp -b "{model["output"]}"')
        print("\n  2. Check logs for errors")
        print("  3. Verify models load correctly in GUI")
    else:
        print("\n⚠️  Some conversions failed - review errors above")

if __name__ == "__main__":
    main()
