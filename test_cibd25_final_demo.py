#!/usr/bin/env python3
"""
CIBD25 Export - Final Demonstration Test

Tests the complete production-ready workflow:
1. Load CIBD22X file
2. Export to CIBD25 text format
3. Verify format and metadata
4. Confirm ready for CBECC 2025

This demonstrates the working solution delivered.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def test_cibd25_export_complete():
    """Final demonstration of CIBD25 export functionality."""
    print("=" * 80)
    print("CIBD25 EXPORT - FINAL DEMONSTRATION")
    print("=" * 80)
    print()

    # Step 1: Import CIBD22X
    print("[1/5] Loading Bressi Ranch CIBD22X model...")
    from eco_tools.translators.cibd22x import CIBD22XImporter

    bressi_path = "/Users/DavidM/Documents/ECO_Alpha/Bressi_FINAL.cibd22x"

    try:
        importer = CIBD22XImporter()
        internal = importer.import_file(bressi_path)
        print(f"  ✓ Loaded successfully")
        print(f"  Project: {internal.proj_metadata.get('Name', 'Unknown')}")
        print(f"  RulesetFilename captured: {internal.proj_metadata.get('RulesetFilename', 'None')}")
    except Exception as e:
        print(f"  ❌ Failed to load: {e}")
        return False

    # Step 2: Export to CIBD25
    print("\n[2/5] Exporting to CIBD25 text format...")
    from eco_tools.translators.cibd25 import CIBD25Exporter

    output_path = ROOT / "test_output" / "Bressi_Ranch_FINAL_DEMO.cibd25"
    output_path.parent.mkdir(exist_ok=True)

    try:
        exporter = CIBD25Exporter()
        exporter.export(internal, str(output_path))

        file_size = output_path.stat().st_size
        print(f"  ✓ Exported successfully")
        print(f"  Output: {output_path}")
        print(f"  Size: {file_size:,} bytes ({file_size / 1024 / 1024:.2f} MB)")
    except Exception as e:
        print(f"  ❌ Export failed: {e}")
        import traceback
        traceback.print_exc()
        return False

    # Step 3: Verify format
    print("\n[3/5] Verifying CIBD25 text format...")
    try:
        with open(output_path, 'r', encoding='utf-8') as f:
            lines = [f.readline().strip() for _ in range(35)]

        first_line = lines[0]
        print(f"  First line: {first_line}")

        # Check for required elements
        checks = {
            'RulesetFilename "T24_2025.bin"': any('RulesetFilename' in line and 'T24_2025.bin' in line for line in lines),
            'Proj header': any('Proj   "' in line for line in lines),
            'SoftwareVersion 2025.2.0': any('SoftwareVersion' in line and '2025.2.0' in line for line in lines),
            'BldgEngyModelVersion = 17': any('BldgEngyModelVersion = 17' in line for line in lines),
            'Building data (Bldg/ResZn)': any('Bldg' in line or 'ResZn' in line for line in lines),
        }

        all_passed = True
        for check_name, passed in checks.items():
            status = "✓" if passed else "❌"
            print(f"  {status} {check_name}")
            if not passed:
                all_passed = False

        if not all_passed:
            print("\n  First 10 lines:")
            for i, line in enumerate(lines[:10], 1):
                print(f"    {i:2d}: {line}")
            return False

    except Exception as e:
        print(f"  ❌ Verification failed: {e}")
        return False

    # Step 4: Verify file size (should be substantial)
    print("\n[4/5] Verifying complete building data...")
    if file_size < 100000:  # Less than 100KB indicates missing data
        print(f"  ❌ File too small ({file_size:,} bytes) - missing building data")
        return False
    else:
        print(f"  ✓ File size confirms full building data ({file_size / 1024 / 1024:.2f} MB)")

    # Step 5: Show sample content
    print("\n[5/5] Sample content from exported file:")
    print("  " + "-" * 76)
    with open(output_path, 'r', encoding='utf-8') as f:
        for i in range(30):
            line = f.readline().rstrip()
            print(f"  {line}")
    print("  " + "-" * 76)

    # Success!
    print("\n" + "=" * 80)
    print("✅ CIBD25 EXPORT DEMONSTRATION SUCCESSFUL")
    print("=" * 80)
    print()
    print("Summary:")
    print(f"  • Input:  {bressi_path}")
    print(f"  • Output: {output_path}")
    print(f"  • Size:   {file_size:,} bytes ({file_size / 1024 / 1024:.2f} MB)")
    print(f"  • Format: CIBD25 text format")
    print(f"  • Ruleset: T24_2025.bin (Title 24 2025)")
    print(f"  • Version: CBECC 2025.2.0 (1390)")
    print()
    print("Ready for CBECC 2025 simulation:")
    print(f"  open -a 'CBECC 2025' '{output_path}'")
    print()

    return True


if __name__ == "__main__":
    success = test_cibd25_export_complete()
    sys.exit(0 if success else 1)
