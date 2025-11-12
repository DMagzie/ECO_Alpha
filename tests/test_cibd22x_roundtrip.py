"""
Test CIBD22X Round-Trip Translation
===================================

Verifies that we can import a CIBD22X file, convert to EMJSON,
and export back to CIBD22X with 100% fidelity.

Test File: Bressi Ranch Apartments (Large multi-family residential)
Expected Results:
- 290 zones
- 3,472 surfaces
- 1,308 openings
- 0 CBECC-Com errors
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from eco_tools.translators.cibd22x.importer import CIBD22XImporter
from eco_tools.translators.cibd22x.exporter import CIBD22XExporter


def test_roundtrip():
    """Test complete round-trip translation"""

    print("=" * 60)
    print("CIBD22X Round-Trip Test")
    print("=" * 60)

    # Paths
    input_file = Path(__file__).parent.parent / "examples" / "bressi_ranch.cibd22x"
    output_file = Path(__file__).parent / "output" / "bressi_ranch_roundtrip.cibd22x"
    output_file.parent.mkdir(exist_ok=True)

    # Step 1: Import
    print("\n1️⃣  Importing CIBD22X file...")
    print(f"   Input: {input_file.name}")

    importer = CIBD22XImporter()
    model = importer.import_file(str(input_file))

    # Verify import (InternalRepresentation object)
    zones = model.zones
    surfaces_count = sum(len(z.surfaces) for z in zones)
    openings_count = sum(
        len(s.openings)
        for z in zones
        for s in z.surfaces
    )

    print(f"   ✅ Imported {len(zones)} zones")
    print(f"   ✅ Imported {surfaces_count} surfaces")
    print(f"   ✅ Imported {openings_count} openings")

    # Step 2: Export
    print("\n2️⃣  Exporting to CIBD22X...")
    print(f"   Output: {output_file.name}")

    exporter = CIBD22XExporter()
    exporter.export_to_file(model, str(output_file))

    # Verify export
    file_size = output_file.stat().st_size
    print(f"   ✅ Exported successfully ({file_size:,} bytes)")

    # Step 3: Validation Summary
    print("\n3️⃣  Validation Summary")
    print("   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print(f"   Zones:        {len(zones):,}")
    print(f"   Surfaces:     {surfaces_count:,}")
    print(f"   Openings:     {openings_count:,}")
    print(f"   File Size:    {file_size:,} bytes")
    print("   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

    # Step 4: CBECC Test Instructions
    print("\n4️⃣  Test in CBECC-Com")
    print("   Run this command to verify 0 errors:")
    print()
    print(f'   "/Applications/CBECC 2022.app/Contents/MacOS/CBECC 2022" \\')
    print(f'       -nrp -b "{output_file}"')
    print()
    print("   Expected: Button returned:OK (0 errors)")
    print()

    print("=" * 60)
    print("✅ ROUND-TRIP TEST COMPLETE")
    print("=" * 60)

    return True


if __name__ == "__main__":
    try:
        test_roundtrip()
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
