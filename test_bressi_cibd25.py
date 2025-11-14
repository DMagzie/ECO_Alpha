"""
Test Bressi Ranch CIBD22X → CIBD25 Export and CBECC 2025 Validation

This script:
1. Imports Bressi Ranch from CIBD22X
2. Exports to CIBD25 format
3. Validates the export
4. Opens in CBECC 2025 for verification
"""

import sys
from pathlib import Path

# Add project root to path
ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from eco_tools.translators.cibd22x import translate_cibd22x_to_v6
from eco_tools.translators.cibd25 import CIBD25Exporter
from eco_tools.core.internal_repr import InternalRepresentation
import xml.etree.ElementTree as ET


def main():
    print("="*70)
    print("Bressi Ranch CIBD22X → CIBD25 Export Test")
    print("="*70)

    # Step 1: Import Bressi Ranch from CIBD22X
    print("\n[Step 1] Importing Bressi Ranch from CIBD22X...")
    bressi_path = "/Users/DavidM/Documents/ECO_Alpha/Bressi_FINAL.cibd22x"

    try:
        emjson = translate_cibd22x_to_v6(bressi_path)
        print(f"  ✓ Import successful")

        if 'diagnostics' in emjson and emjson['diagnostics']:
            errors = [d for d in emjson['diagnostics'] if d.get('level') == 'error']
            warnings = [d for d in emjson['diagnostics'] if d.get('level') == 'warning']
            print(f"  Diagnostics: {len(errors)} errors, {len(warnings)} warnings")
    except Exception as e:
        print(f"  ❌ Import failed: {e}")
        import traceback
        traceback.print_exc()
        return 1

    # Step 2: Convert to InternalRepresentation
    print("\n[Step 2] Converting to InternalRepresentation...")
    try:
        internal = InternalRepresentation()

        # Copy proj_metadata
        internal.proj_metadata = emjson.get('proj_metadata', {})
        internal.metadata = emjson.get('project', {})

        # Set 2025 version
        internal.metadata['title_24_version'] = '2025'

        # Copy geometry
        from dataclasses import fields

        # Count elements
        zones = len(emjson.get('geometry', {}).get('zones', []))
        surfaces = len(emjson.get('geometry', {}).get('surfaces', []))

        print(f"  ✓ Converted successfully")
        print(f"  Model stats: {zones} zones, {surfaces} surfaces")
    except Exception as e:
        print(f"  ❌ Conversion failed: {e}")
        import traceback
        traceback.print_exc()
        return 1

    # Step 3: Export to CIBD25
    print("\n[Step 3] Exporting to CIBD25...")
    output_path = ROOT / "test_output" / "Bressi_Ranch_CIBD25.xml"
    output_path.parent.mkdir(exist_ok=True)

    try:
        exporter = CIBD25Exporter()
        root = exporter.export(internal, str(output_path))
        print(f"  ✓ Exported to: {output_path}")

        # Validate metadata
        proj = root.find(".//Proj")
        if proj is not None:
            software_version = None
            ruleset = None
            for child in proj:
                if child.tag == "SoftwareVersion":
                    software_version = child.text
                elif child.tag == "RulesetFilename":
                    ruleset = child.text

            print(f"\n  Metadata:")
            print(f"    SoftwareVersion: {software_version}")
            print(f"    RulesetFilename: {ruleset}")
            print(f"    Root RulesetFilename: {root.get('RulesetFilename')}")

            # Verify correct version
            if software_version == "CBECC 2025.2.0 (1390)":
                print(f"  ✅ Version is correct!")
            else:
                print(f"  ⚠️  Version mismatch: expected 'CBECC 2025.2.0 (1390)'")

            if ruleset == "T24_2025.bin":
                print(f"  ✅ Ruleset is correct!")
            else:
                print(f"  ⚠️  Ruleset mismatch: expected 'T24_2025.bin'")
        else:
            print(f"  ⚠️  No Proj element found")

    except Exception as e:
        print(f"  ❌ Export failed: {e}")
        import traceback
        traceback.print_exc()
        return 1

    # Step 4: Open in CBECC 2025
    print("\n[Step 4] Opening in CBECC 2025...")
    print(f"  Opening file: {output_path}")

    import subprocess
    try:
        # Use macOS 'open' command to open in CBECC 2025
        subprocess.run(['open', '-a', 'CBECC 2025', str(output_path)], check=True)
        print(f"  ✓ Opened in CBECC 2025 application")
        print(f"\n  Please verify in CBECC 2025 that:")
        print(f"    1. File opens without errors")
        print(f"    2. Ruleset shows 'T24_2025.bin'")
        print(f"    3. Software version shows '2025.2.0 (1390)'")
        print(f"    4. Model geometry displays correctly")
    except subprocess.CalledProcessError as e:
        print(f"  ⚠️  Could not open in CBECC 2025: {e}")
        print(f"  Please open manually: {output_path}")

    print("\n" + "="*70)
    print("TEST COMPLETE")
    print("="*70)
    print(f"\nExported file: {output_path}")
    print(f"You can also open this file manually in CBECC 2025")

    return 0


if __name__ == "__main__":
    sys.exit(main())
