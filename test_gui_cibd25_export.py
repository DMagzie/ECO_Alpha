"""
Test GUI CIBD25 Export Function

Tests the complete workflow that the GUI uses:
1. Import CIBD22X to EMJSON
2. Use GUI translator function to export EMJSON → CIBD25 text
3. Save the output
4. Verify it can be opened in CBECC 2025
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from eco_tools.translators.cibd22x import translate_cibd22x_to_v6
from gui.translators import emjson6_to_cibd25


def test_gui_cibd25_export():
    print("="*70)
    print("GUI CIBD25 Export Test")
    print("="*70)

    # Step 1: Import CIBD22X to EMJSON (what GUI does)
    print("\n[1/4] Importing Bressi Ranch to EMJSON...")
    bressi_path = "/Users/DavidM/Documents/ECO_Alpha/Bressi_FINAL.cibd22x"

    try:
        emjson = translate_cibd22x_to_v6(bressi_path)
        print(f"  ✓ Import successful")
        print(f"  EMJSON keys: {list(emjson.keys())}")
    except Exception as e:
        print(f"  ❌ Import failed: {e}")
        import traceback
        traceback.print_exc()
        return False

    # Step 2: Use GUI translator to export EMJSON → CIBD25 text
    print("\n[2/4] Exporting EMJSON → CIBD25 using GUI translator...")
    try:
        cibd25_text = emjson6_to_cibd25(emjson)
        print(f"  ✓ Export successful")
        print(f"  Output size: {len(cibd25_text):,} characters")

        # Check if it's an error message
        if cibd25_text.startswith('# Export failed'):
            print(f"  ❌ Export returned error:")
            print(cibd25_text[:500])
            return False

    except Exception as e:
        print(f"  ❌ Export failed: {e}")
        import traceback
        traceback.print_exc()
        return False

    # Step 3: Save the output
    print("\n[3/4] Saving CIBD25 text file...")
    output_path = ROOT / "test_output" / "Bressi_Ranch_GUI_Export.cibd25"
    output_path.parent.mkdir(exist_ok=True)

    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(cibd25_text)

        file_size = output_path.stat().st_size
        print(f"  ✓ Saved to: {output_path}")
        print(f"  ✓ File size: {file_size:,} bytes")

    except Exception as e:
        print(f"  ❌ Save failed: {e}")
        return False

    # Step 4: Verify format
    print("\n[4/4] Verifying CIBD25 format...")
    try:
        with open(output_path, 'r', encoding='utf-8') as f:
            first_line = f.readline().strip()
            lines = [first_line]
            for i in range(30):
                lines.append(f.readline().strip())

        print(f"  First line: {first_line}")

        if 'RulesetFilename' in first_line and 'T24_2025.bin' in first_line:
            print(f"  ✓ Correct ruleset detected")
        else:
            print(f"  ❌ Wrong format or ruleset")
            print(f"  First 5 lines:")
            for line in lines[:5]:
                print(f"    {line}")
            return False

        # Check for building data
        has_bldg = any('Bldg' in line for line in lines)
        has_zones = any('ResZn' in line or 'Zone' in line for line in lines)

        if has_bldg:
            print(f"  ✓ Building data detected")
        if has_zones:
            print(f"  ✓ Zone data detected")

        if not (has_bldg or has_zones):
            print(f"  ⚠️  Warning: No building/zone data found in first 30 lines")

    except Exception as e:
        print(f"  ❌ Verification failed: {e}")
        return False

    print("\n" + "="*70)
    print("✅ GUI CIBD25 EXPORT TEST PASSED")
    print("="*70)
    print(f"\nOutput file: {output_path}")
    print(f"\nYou can open this file in CBECC 2025:")
    print(f"  open -a 'CBECC 2025' '{output_path}'")

    return True


if __name__ == "__main__":
    success = test_gui_cibd25_export()
    sys.exit(0 if success else 1)
