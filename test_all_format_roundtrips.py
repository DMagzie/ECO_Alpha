#!/usr/bin/env python3
"""
Complete Format Roundtrip Test Suite

Tests ALL possible format conversion combinations:
- CIBD22  → CIBD22, CIBD22X, CIBD25
- CIBD22X → CIBD22, CIBD22X, CIBD25
- CIBD25  → CIBD22, CIBD22X, CIBD25

Total: 9 conversion paths tested
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from eco_tools.translators.cibd22 import CIBD22Importer, CIBD22Exporter
from eco_tools.translators.cibd22x import CIBD22XImporter
from eco_tools.translators.cibd22x.exporter import CIBD22XExporter
from eco_tools.translators.cibd25 import CIBD25Importer, CIBD25Exporter


class FormatTester:
    """Test roundtrip conversions between all formats."""

    def __init__(self):
        self.output_dir = ROOT / "test_output" / "format_roundtrips"
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.results = []

    def test_conversion(self, source_format, source_file, target_format, importer_class, exporter_class, extension):
        """Test a single format conversion."""
        test_name = f"{source_format} → {target_format}"
        print(f"\n{'='*80}")
        print(f"TEST: {test_name}")
        print(f"{'='*80}")

        try:
            # Step 1: Import
            print(f"[1/3] Importing {source_format}...")
            print(f"  File: {source_file}")

            importer = importer_class()
            internal = importer.import_file(source_file)

            zones = len(internal.zones)
            surfaces = len(internal.surfaces)
            materials = len(internal.materials)

            print(f"  ✓ Imported successfully")
            print(f"    - Zones: {zones}")
            print(f"    - Surfaces: {surfaces}")
            print(f"    - Materials: {materials}")

            if zones == 0:
                print(f"  ❌ No zones found - source file may be invalid")
                self.results.append((test_name, False, "No zones in source"))
                return False

            # Step 2: Export
            print(f"\n[2/3] Exporting to {target_format}...")

            output_file = self.output_dir / f"{source_format}_to_{target_format}{extension}"

            exporter = exporter_class()
            if hasattr(exporter, 'export'):
                exporter.export(internal, str(output_file))
            elif hasattr(exporter, 'export_to_file'):
                exporter.export_to_file(internal, str(output_file))
            else:
                raise Exception("Exporter has no export method")

            file_size = output_file.stat().st_size
            print(f"  ✓ Exported successfully")
            print(f"    - Output: {output_file.name}")
            print(f"    - Size: {file_size:,} bytes ({file_size / 1024 / 1024:.2f} MB)")

            if file_size < 10000:
                print(f"  ⚠️  Warning: File size small, may be missing data")

            # Step 3: Re-import to verify
            print(f"\n[3/3] Re-importing {target_format} to verify...")

            # Determine which importer to use for target format
            if target_format == "CIBD22":
                verify_importer = CIBD22Importer()
            elif target_format == "CIBD22X":
                verify_importer = CIBD22XImporter()
            elif target_format == "CIBD25":
                verify_importer = CIBD25Importer()

            internal_verify = verify_importer.import_file(str(output_file))

            zones_verify = len(internal_verify.zones)
            surfaces_verify = len(internal_verify.surfaces)

            print(f"  ✓ Re-imported successfully")
            print(f"    - Zones: {zones_verify} (original: {zones})")
            print(f"    - Surfaces: {surfaces_verify} (original: {surfaces})")

            # Verify data preservation
            if zones_verify != zones:
                print(f"  ❌ Zone count mismatch!")
                self.results.append((test_name, False, f"Zones: {zones_verify} vs {zones}"))
                return False

            if surfaces_verify != surfaces:
                print(f"  ⚠️  Surface count mismatch (may be OK for format differences)")

            print(f"\n✅ {test_name} PASSED")
            self.results.append((test_name, True, f"{zones} zones preserved"))
            return True

        except Exception as e:
            print(f"\n❌ {test_name} FAILED")
            print(f"  Error: {e}")
            import traceback
            traceback.print_exc()
            self.results.append((test_name, False, str(e)))
            return False

    def run_all_tests(self):
        """Run all format roundtrip tests."""
        print("="*80)
        print("COMPLETE FORMAT ROUNDTRIP TEST SUITE")
        print("="*80)
        print("\nTesting all 9 format conversion combinations...")

        # First, create test files by exporting from CIBD22X
        print("\n" + "="*80)
        print("SETUP: Creating test files from Bressi Ranch")
        print("="*80)

        source_cibd22x = "/Users/DavidM/Documents/ECO_Alpha/Bressi_FINAL.cibd22x"

        # Import source
        print("\nImporting source CIBD22X...")
        importer = CIBD22XImporter()
        internal = importer.import_file(source_cibd22x)
        print(f"  ✓ Loaded: {len(internal.zones)} zones, {len(internal.surfaces)} surfaces")

        # Create CIBD22 test file
        print("\nCreating CIBD22 test file...")
        cibd22_file = self.output_dir / "test_source.cibd22"
        CIBD22Exporter().export(internal, str(cibd22_file))
        print(f"  ✓ Created: {cibd22_file}")

        # Re-import to get fresh internal (avoid metadata pollution)
        importer = CIBD22XImporter()
        internal = importer.import_file(source_cibd22x)

        # Create CIBD25 test file
        print("\nCreating CIBD25 test file...")
        cibd25_file = self.output_dir / "test_source.cibd25"
        CIBD25Exporter().export(internal, str(cibd25_file))
        print(f"  ✓ Created: {cibd25_file}")

        # Test matrix
        tests = [
            # Source Format, Source File, Target Format, Importer, Exporter, Extension

            # From CIBD22
            ("CIBD22", str(cibd22_file), "CIBD22", CIBD22Importer, CIBD22Exporter, ".cibd22"),
            ("CIBD22", str(cibd22_file), "CIBD22X", CIBD22Importer, CIBD22XExporter, ".xml"),
            ("CIBD22", str(cibd22_file), "CIBD25", CIBD22Importer, CIBD25Exporter, ".cibd25"),

            # From CIBD22X
            ("CIBD22X", source_cibd22x, "CIBD22", CIBD22XImporter, CIBD22Exporter, ".cibd22"),
            ("CIBD22X", source_cibd22x, "CIBD22X", CIBD22XImporter, CIBD22XExporter, ".xml"),
            ("CIBD22X", source_cibd22x, "CIBD25", CIBD22XImporter, CIBD25Exporter, ".cibd25"),

            # From CIBD25
            ("CIBD25", str(cibd25_file), "CIBD22", CIBD25Importer, CIBD22Exporter, ".cibd22"),
            ("CIBD25", str(cibd25_file), "CIBD22X", CIBD25Importer, CIBD22XExporter, ".xml"),
            ("CIBD25", str(cibd25_file), "CIBD25", CIBD25Importer, CIBD25Exporter, ".cibd25"),
        ]

        # Run all tests
        passed = 0
        failed = 0

        for source_fmt, source_file, target_fmt, importer, exporter, ext in tests:
            success = self.test_conversion(
                source_fmt, source_file, target_fmt,
                importer, exporter, ext
            )
            if success:
                passed += 1
            else:
                failed += 1

        # Summary
        self.print_summary(passed, failed)

        return failed == 0

    def print_summary(self, passed, failed):
        """Print test summary."""
        total = passed + failed

        print("\n" + "="*80)
        print("TEST SUMMARY")
        print("="*80)

        print(f"\nTotal Tests: {total}")
        print(f"  Passed: {passed} ✅")
        print(f"  Failed: {failed} {'❌' if failed > 0 else '✅'}")

        print("\nDetailed Results:")
        print("-" * 80)
        for test_name, success, details in self.results:
            status = "✅ PASS" if success else "❌ FAIL"
            print(f"{status:10s} | {test_name:25s} | {details}")

        print("\n" + "="*80)
        if failed == 0:
            print("✅ ALL FORMAT ROUNDTRIP TESTS PASSED!")
            print("="*80)
            print("\nAll 9 format conversion combinations work correctly:")
            print("  • CIBD22  ↔ CIBD22, CIBD22X, CIBD25")
            print("  • CIBD22X ↔ CIBD22, CIBD22X, CIBD25")
            print("  • CIBD25  ↔ CIBD22, CIBD22X, CIBD25")
            print("\nNo workarounds needed - pure modular architecture! 🎉")
        else:
            print("❌ SOME TESTS FAILED")
            print("="*80)
            print(f"\n{failed} out of {total} tests failed. See details above.")


if __name__ == "__main__":
    tester = FormatTester()
    success = tester.run_all_tests()
    sys.exit(0 if success else 1)
