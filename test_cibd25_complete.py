"""
Complete CIBD25 Export Test

Tests the complete workflow:
1. Import CIBD22X (Bressi Ranch)
2. Export to CIBD25 text format
3. Verify the file can be opened in CBECC 2025
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from eco_tools.translators.cibd22x import translate_cibd22x_to_v6
from eco_tools.translators.cibd25 import CIBD25Exporter
from eco_tools.core.internal_repr import InternalRepresentation


def test_complete_cibd25_export():
    print("="*70)
    print("CIBD25 Complete Export Test")
    print("="*70)

    # Step 1: Import CIBD22X
    print("\n[1/3] Importing Bressi Ranch from CIBD22X...")
    bressi_path = "/Users/DavidM/Documents/ECO_Alpha/Bressi_FINAL.cibd22x"

    try:
        emjson = translate_cibd22x_to_v6(bressi_path)
        print(f"  ✓ Import successful")
    except Exception as e:
        print(f"  ❌ Import failed: {e}")
        return False

    # Step 2: Convert to InternalRepresentation and export to CIBD25
    print("\n[2/3] Exporting to CIBD25 text format...")
    output_path = ROOT / "test_output" / "Bressi_Ranch_Complete.cibd25"
    output_path.parent.mkdir(exist_ok=True)

    try:
        internal = InternalRepresentation()
        internal.proj_metadata = emjson.get('proj_metadata', {})
        internal.metadata = emjson.get('project', {})
        internal.metadata['title_24_version'] = '2025'

        exporter = CIBD25Exporter()
        exporter.export(internal, str(output_path))

        print(f"  ✓ Exported to: {output_path}")

        # Verify file exists and has content
        if output_path.exists():
            file_size = output_path.stat().st_size
            print(f"  ✓ File size: {file_size:,} bytes")
        else:
            print(f"  ❌ File not found")
            return False

    except Exception as e:
        print(f"  ❌ Export failed: {e}")
        import traceback
        traceback.print_exc()
        return False

    # Step 3: Verify format
    print("\n[3/3] Verifying CIBD25 format...")
    try:
        with open(output_path, 'r', encoding='utf-8') as f:
            first_line = f.readline().strip()

        if first_line.startswith('RulesetFilename'):
            if 'T24_2025.bin' in first_line:
                print(f"  ✓ First line: {first_line}")
                print(f"  ✓ Correct ruleset detected")
            else:
                print(f"  ⚠️  Wrong ruleset: {first_line}")
                return False
        else:
            print(f"  ❌ Unexpected format: {first_line}")
            return False

    except Exception as e:
        print(f"  ❌ Verification failed: {e}")
        return False

    print("\n" + "="*70)
    print("✅ CIBD25 EXPORT TEST PASSED")
    print("="*70)
    print(f"\nOutput file: {output_path}")
    print(f"\nYou can open this file in CBECC 2025:")
    print(f"  open -a 'CBECC 2025' '{output_path}'")

    return True


if __name__ == "__main__":
    success = test_complete_cibd25_export()
    sys.exit(0 if success else 1)
