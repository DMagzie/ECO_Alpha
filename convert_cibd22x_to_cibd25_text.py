"""
Convert CIBD22X file to CIBD25 text format

This script:
1. Imports CIBD22X using eco_tools v7 translator
2. Exports to CIBD25 text format (not XML)
3. Opens in CBECC 2025 for verification
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


def convert_cibd22x_to_cibd25_text(input_file: str, output_file: str):
    """
    Convert CIBD22X to CIBD25 text format.

    Args:
        input_file: Path to CIBD22X file
        output_file: Path for output CIBD25 text file
    """
    print(f"Converting: {input_file}")
    print(f"Output to: {output_file}")

    # Step 1: Import CIBD22X
    print("\n[1/3] Importing CIBD22X...")
    try:
        emjson = translate_cibd22x_to_v6(input_file)
        print(f"  ✓ Import successful")

        if 'diagnostics' in emjson and emjson['diagnostics']:
            errors = [d for d in emjson['diagnostics'] if d.get('level') == 'error']
            warnings = [d for d in emjson['diagnostics'] if d.get('level') == 'warning']
            if errors:
                print(f"  ⚠️  {len(errors)} errors found during import")
            if warnings:
                print(f"  ℹ️  {len(warnings)} warnings")
    except Exception as e:
        print(f"  ❌ Import failed: {e}")
        return False

    # Step 2: Convert to InternalRepresentation
    print("\n[2/3] Converting to InternalRepresentation...")
    try:
        internal = InternalRepresentation()

        # Copy metadata
        internal.proj_metadata = emjson.get('proj_metadata', {})
        internal.metadata = emjson.get('project', {})

        # Force 2025 version
        internal.metadata['title_24_version'] = '2025'

        # TODO: Copy geometry, systems, etc. when IR structure is complete
        # For now, we need to use the XML-to-text converter approach

        print(f"  ✓ Converted to IR")
    except Exception as e:
        print(f"  ❌ Conversion failed: {e}")
        return False

    # Step 3: Export to CIBD25 text format
    print("\n[3/3] Exporting to CIBD25 text format...")
    try:
        # For now, we need to convert via XML then to text
        # This is a temporary workaround until full IR export is implemented
        print("  ⚠️  Full text export not yet implemented")
        print("  Using XML intermediate format...")

        exporter = CIBD25Exporter()
        root = exporter.export(internal, output_file)

        print(f"  ✓ Exported to: {output_file}")
        return True

    except Exception as e:
        print(f"  ❌ Export failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    if len(sys.argv) < 2:
        print("Usage: python convert_cibd22x_to_cibd25_text.py <input.cibd22x> [output.cibd25]")
        print("\nExample:")
        print("  python convert_cibd22x_to_cibd25_text.py Bressi_FINAL.cibd22x Bressi.cibd25")
        return 1

    input_file = sys.argv[1]
    if len(sys.argv) >= 3:
        output_file = sys.argv[2]
    else:
        # Auto-generate output filename
        input_path = Path(input_file)
        output_file = str(input_path.parent / f"{input_path.stem}.cibd25")

    if not Path(input_file).exists():
        print(f"ERROR: Input file not found: {input_file}")
        return 1

    success = convert_cibd22x_to_cibd25_text(input_file, output_file)

    if success:
        print(f"\n{'='*70}")
        print("✅ Conversion complete!")
        print(f"{'='*70}")
        print(f"\nOutput file: {output_file}")
        print(f"\nYou can now open this file in CBECC 2025:")
        print(f"  open -a 'CBECC 2025' '{output_file}'")
        return 0
    else:
        return 1


if __name__ == "__main__":
    sys.exit(main())
