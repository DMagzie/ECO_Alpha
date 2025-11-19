#!/usr/bin/env python3
"""
Simple command-line tool to convert CIBD22X files to CIBD25.

Usage:
    python3 convert_cibd22x_to_cibd25.py input.cibd22x output.cibd25

This tool uses the v7 translators with the duplicate WinType bug fix.
"""
import sys
from pathlib import Path

def convert_cibd22x_to_cibd25(input_file: str, output_file: str):
    """Convert CIBD22X to CIBD25."""
    from eco_tools.translators.cibd22x import CIBD22XImporter
    from eco_tools.translators.cibd25 import CIBD25Exporter

    input_path = Path(input_file)
    output_path = Path(output_file)

    if not input_path.exists():
        print(f"❌ Input file not found: {input_file}")
        sys.exit(1)

    print(f"📥 Importing {input_path.name}...")
    importer = CIBD22XImporter()
    model = importer.import_file(str(input_path))

    print(f"   ✓ Imported {len(model.zones)} zones")

    print(f"\n📤 Exporting to CIBD25...")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    exporter = CIBD25Exporter()
    exporter.export(model, str(output_path))

    print(f"   ✓ Exported to {output_path}")
    print(f"   File size: {output_path.stat().st_size:,} bytes")

    print(f"\n✅ Conversion complete!")
    print(f"\n📝 Next step: Open {output_path.name} in CBECC 2025")

if __name__ == '__main__':
    if len(sys.argv) != 3:
        print("Usage: python3 convert_cibd22x_to_cibd25.py <input.cibd22x> <output.cibd25>")
        print("\nExample:")
        print("  python3 convert_cibd22x_to_cibd25.py 'Bressi Ranch Apartments.cibd22x' bressi_ranch.cibd25")
        sys.exit(1)

    convert_cibd22x_to_cibd25(sys.argv[1], sys.argv[2])
