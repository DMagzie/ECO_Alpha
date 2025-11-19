#!/usr/bin/env python3
"""
Export a set of residential sample CIBD25 models for testing.
Converts residential CIBD22X models to CIBD25 format.
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from eco_tools.translators.cibd_xml_to_text import CIBDXMLToTextConverter

def main():
    # Define residential models to convert
    residential_models = [
        {
            "name": "Bressi Ranch Apartments (Multifamily)",
            "source": "/Users/DavidM/Documents/ECO_Alpha_v7/reference_data/cbecc/CBECC Models/Bressi Ranch/Bressi Ranch Apartments.cibd22x",
            "output": "/Users/DavidM/Downloads/Residential_Samples/Bressi_Ranch_Apartments.cibd25"
        },
        {
            "name": "Del Amo Circle (Mixed Commercial/Residential)",
            "source": "/Users/DavidM/Documents/ECO_Alpha_v7/reference_data/cbecc/CBECC Models/cibd22x/Del Amo Circle-LEED_CBECC2022_2024-12-11.cibd22x",
            "output": "/Users/DavidM/Downloads/Residential_Samples/Del_Amo_Circle_Mixed_Use.cibd25"
        },
        {
            "name": "Mainplace Mall Parcel 3 (Residential HVAC)",
            "source": "/Users/DavidM/Documents/ECO_Alpha_v7/reference_data/cbecc/Matching/60-21191-ACM-Mainplace Mall Parcel 3_ResHVAC.cibd22x",
            "output": "/Users/DavidM/Downloads/Residential_Samples/Mainplace_Mall_ResHVAC.cibd25"
        },
        {
            "name": "El Paseo Building 1 (Multifamily)",
            "source": "/Users/DavidM/Documents/ECO_Alpha_v7/reference_data/cbecc/Matching/El Paseo de Saratoga - Building 1 2025.08-12.cibd22x",
            "output": "/Users/DavidM/Downloads/Residential_Samples/El_Paseo_Building_1.cibd25"
        },
        {
            "name": "El Paseo Building 2 (Multifamily)",
            "source": "/Users/DavidM/Documents/ECO_Alpha_v7/reference_data/cbecc/Matching/El Paseo Building 2_CBECC 2022_2025-08-12.cibd22x",
            "output": "/Users/DavidM/Downloads/Residential_Samples/El_Paseo_Building_2.cibd25"
        },
        {
            "name": "Euclid Building A (Multifamily)",
            "source": "/Users/DavidM/Documents/ECO_Alpha_v7/reference_data/cbecc/Matching/Euclid Building A_v3_2024-04-29.cibd22x",
            "output": "/Users/DavidM/Downloads/Residential_Samples/Euclid_Building_A.cibd25"
        },
        {
            "name": "Euclid Building B (Multifamily)",
            "source": "/Users/DavidM/Documents/ECO_Alpha_v7/reference_data/cbecc/Matching/Euclid_Bldg B_2024-04-29.cibd22x",
            "output": "/Users/DavidM/Downloads/Residential_Samples/Euclid_Building_B.cibd25"
        },
        {
            "name": "Euclid Building C (Multifamily)",
            "source": "/Users/DavidM/Documents/ECO_Alpha_v7/reference_data/cbecc/Matching/Euclid_Building C_2025-01-06.cibd22x",
            "output": "/Users/DavidM/Downloads/Residential_Samples/Euclid_Building_C.cibd25"
        },
    ]

    # Create output directory
    output_dir = Path("/Users/DavidM/Downloads/Residential_Samples")
    output_dir.mkdir(exist_ok=True)

    # Create converter
    converter = CIBDXMLToTextConverter()

    print("=" * 80)
    print("RESIDENTIAL SAMPLE MODELS - CIBD25 EXPORT")
    print("=" * 80)
    print(f"\nExporting {len(residential_models)} residential models to:")
    print(f"  {output_dir}")
    print("=" * 80)

    results = []
    total_size = 0

    for model in residential_models:
        print(f"\n{'─' * 80}")
        print(f"Converting: {model['name']}")
        print(f"Source: {Path(model['source']).name}")
        print(f"{'─' * 80}")

        try:
            # Check if source exists
            source_path = Path(model['source'])
            if not source_path.exists():
                print(f"  ⚠️  WARNING: Source file not found, skipping...")
                results.append((model['name'], False, "Source not found"))
                continue

            # Convert
            converter.convert_file(str(source_path), model['output'])

            # Check output exists
            output_path = Path(model['output'])
            if output_path.exists():
                size_kb = output_path.stat().st_size / 1024
                total_size += size_kb
                print(f"  ✅ SUCCESS: {size_kb:.1f} KB")
                results.append((model['name'], True, f"{size_kb:.1f} KB"))
            else:
                print(f"  ❌ ERROR: Output file not created!")
                results.append((model['name'], False, "Output not created"))

        except Exception as e:
            print(f"  ❌ ERROR: {str(e)}")
            results.append((model['name'], False, str(e)))

    # Summary
    print(f"\n{'=' * 80}")
    print("EXPORT SUMMARY")
    print(f"{'=' * 80}")

    success_count = sum(1 for _, success, _ in results if success)
    total_count = len(results)

    for name, success, info in results:
        status = "✅" if success else "❌"
        print(f"{status} {name:45} | {info}")

    print(f"{'=' * 80}")
    print(f"Results: {success_count}/{total_count} models exported successfully")
    print(f"Total size: {total_size:.1f} KB ({total_size/1024:.2f} MB)")
    print(f"\nOutput directory: {output_dir}")
    print(f"{'=' * 80}")

    if success_count == total_count:
        print("\n✅ All residential sample models exported successfully!")
        print("\nThese models can be used for:")
        print("  • Testing the CIBD25 format in CBECC 2025")
        print("  • Validating residential HVAC systems")
        print("  • Reference examples for multifamily buildings")
        print("  • Mixed-use building analysis")
    else:
        print(f"\n⚠️  {total_count - success_count} model(s) failed to export")

    # Create README
    readme_path = output_dir / "README.txt"
    with open(readme_path, 'w') as f:
        f.write("RESIDENTIAL SAMPLE MODELS - CIBD25 FORMAT\n")
        f.write("=" * 80 + "\n\n")
        f.write("This directory contains residential building models in CIBD25 format,\n")
        f.write("converted from CIBD22X reference models.\n\n")
        f.write("MODELS INCLUDED:\n")
        f.write("-" * 80 + "\n")
        for i, model in enumerate(residential_models, 1):
            output_path = Path(model['output'])
            if output_path.exists():
                size_kb = output_path.stat().st_size / 1024
                f.write(f"{i}. {model['name']}\n")
                f.write(f"   File: {output_path.name}\n")
                f.write(f"   Size: {size_kb:.1f} KB\n\n")
        f.write("\n" + "=" * 80 + "\n")
        f.write("TESTING IN CBECC 2025:\n")
        f.write("-" * 80 + "\n")
        f.write('"/Applications/CBECC 2025.app/Contents/MacOS/CBECC 2025" -nrp -b <model_file>\n\n')
        f.write("Or open the GUI and load the model file.\n")

    print(f"\n📝 Created README: {readme_path}")

if __name__ == "__main__":
    main()
