#!/usr/bin/env python3
"""
Test script to convert CIBD22X models that have matching CIBD22 versions.
Compares the converted CIBD25 structure to the original CIBD22 to verify consistency.
"""

import sys
from pathlib import Path
import xml.etree.ElementTree as ET

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from eco_tools.translators.cibd_xml_to_text import CIBDXMLToTextConverter

def extract_element_structure(file_path):
    """Extract top-level element structure from a CIBD file."""
    structure = []

    # Try different encodings
    for encoding in ['utf-8', 'latin-1', 'cp1252']:
        try:
            with open(file_path, 'r', encoding=encoding) as f:
                for line in f:
                    stripped = line.strip()
                    if not stripped:
                        continue

                    # Count leading spaces to determine nesting
                    leading_spaces = len(line) - len(line.lstrip())

                    # Check if this is an element declaration (starts with element name)
                    # Format: "ElementType   "Name""
                    parts = stripped.split()
                    if len(parts) >= 1 and parts[0] and parts[0][0].isupper():
                        element_type = parts[0]
                        if leading_spaces == 0:
                            # Top-level element
                            structure.append(element_type)

            # Successfully read file, break out of encoding loop
            break
        except (UnicodeDecodeError, Exception):
            # Try next encoding
            continue

    return structure

def compare_structures(cibd22_path, cibd25_path, model_name):
    """Compare element structures between CIBD22 and converted CIBD25."""
    print(f"\n{'─' * 80}")
    print(f"Comparing: {model_name}")
    print(f"{'─' * 80}")

    # Extract structures
    cibd22_structure = extract_element_structure(cibd22_path)
    cibd25_structure = extract_element_structure(cibd25_path)

    # Count elements
    from collections import Counter
    cibd22_counts = Counter(cibd22_structure)
    cibd25_counts = Counter(cibd25_structure)

    # Find all unique element types
    all_types = set(cibd22_counts.keys()) | set(cibd25_counts.keys())

    print(f"\n{'Element Type':<25} | {'CIBD22':<8} | {'CIBD25':<8} | Status")
    print("─" * 80)

    differences = []
    for elem_type in sorted(all_types):
        cibd22_count = cibd22_counts.get(elem_type, 0)
        cibd25_count = cibd25_counts.get(elem_type, 0)

        if cibd22_count == cibd25_count:
            status = "✓ Match"
        else:
            status = f"✗ Diff ({cibd25_count - cibd22_count:+d})"
            differences.append((elem_type, cibd22_count, cibd25_count))

        print(f"{elem_type:<25} | {cibd22_count:<8} | {cibd25_count:<8} | {status}")

    # Summary
    if not differences:
        print("\n✅ All element counts match!")
        return True
    else:
        print(f"\n⚠️  Found {len(differences)} element type(s) with different counts")
        return False

def main():
    # Define matching models to test - focus on variety
    test_models = [
        {
            "name": "Mainplace Mall (Residential HVAC)",
            "cibd22x": "/Users/DavidM/Documents/ECO_Alpha_v7/reference_data/cbecc/Matching/60-21191-ACM-Mainplace Mall Parcel 3_ResHVAC.cibd22x",
            "cibd22": "/Users/DavidM/Documents/ECO_Alpha_v7/reference_data/cbecc/Matching/60-21191-ACM-Mainplace Mall Parcel 3_ResHVAC.cibd22",
            "output": "/Users/DavidM/Downloads/Mainplace_Mall_Test.cibd25"
        },
        {
            "name": "El Paseo Building 2",
            "cibd22x": "/Users/DavidM/Documents/ECO_Alpha_v7/reference_data/cbecc/Matching/El Paseo Building 2_CBECC 2022_2025-08-12.cibd22x",
            "cibd22": "/Users/DavidM/Documents/ECO_Alpha_v7/reference_data/cbecc/Matching/El Paseo Building 2_CBECC 2022_2025-08-12.cibd22",
            "output": "/Users/DavidM/Downloads/El_Paseo_Bldg2_Test.cibd25"
        },
        {
            "name": "Euclid Building A",
            "cibd22x": "/Users/DavidM/Documents/ECO_Alpha_v7/reference_data/cbecc/Matching/Euclid Building A_v3_2024-04-29.cibd22x",
            "cibd22": "/Users/DavidM/Documents/ECO_Alpha_v7/reference_data/cbecc/Matching/Euclid Building A_v3_2024-04-29.cibd22",
            "output": "/Users/DavidM/Downloads/Euclid_BldgA_Test.cibd25"
        },
    ]

    # Create converter
    converter = CIBDXMLToTextConverter()

    print("=" * 80)
    print("CIBD22X to CIBD25 Translation Validation")
    print("=" * 80)
    print("\nConverting CIBD22X models and comparing to CIBD22 structure...")
    print("This verifies the translator produces correct top-level element ordering.")
    print("=" * 80)

    results = []
    comparison_results = []

    for model in test_models:
        print(f"\n{'═' * 80}")
        print(f"Processing: {model['name']}")
        print(f"{'═' * 80}")

        try:
            # Check if source exists
            source_path = Path(model['cibd22x'])
            cibd22_path = Path(model['cibd22'])

            if not source_path.exists():
                print(f"  ❌ ERROR: CIBD22X source file not found!")
                results.append((model['name'], False, "Source not found"))
                continue

            if not cibd22_path.exists():
                print(f"  ❌ ERROR: CIBD22 reference file not found!")
                results.append((model['name'], False, "Reference not found"))
                continue

            # Convert
            print(f"\n📝 Converting CIBD22X to CIBD25...")
            converter.convert_file(str(source_path), model['output'])

            # Check output exists
            output_path = Path(model['output'])
            if output_path.exists():
                size_kb = output_path.stat().st_size / 1024
                print(f"  ✅ Conversion successful: {size_kb:.1f} KB")
                results.append((model['name'], True, f"{size_kb:.1f} KB"))

                # Compare structures
                print(f"\n📊 Comparing element structure with CIBD22 reference...")
                match = compare_structures(str(cibd22_path), model['output'], model['name'])
                comparison_results.append((model['name'], match))
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
        print(f"{status:12} | {name:30} | {info}")

    print(f"{'=' * 80}")
    print(f"Conversions: {success_count}/{total_count} successful")

    # Comparison summary
    if comparison_results:
        print(f"\n{'=' * 80}")
        print("STRUCTURE COMPARISON SUMMARY")
        print(f"{'=' * 80}")

        match_count = sum(1 for _, match in comparison_results if match)
        for name, match in comparison_results:
            status = "✅ Match" if match else "⚠️  Differences"
            print(f"{status:12} | {name}")

        print(f"{'=' * 80}")
        print(f"Matches: {match_count}/{len(comparison_results)}")

    print(f"{'=' * 80}")

if __name__ == "__main__":
    main()
