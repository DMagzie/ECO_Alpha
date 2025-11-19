"""
HBJSON Round-Trip Validation Script
====================================

Tests bidirectional translation between HBJSON and EMJSON formats.

Workflow:
1. Import HBJSON → EMJSON (via importer)
2. Export EMJSON → HBJSON (via exporter)
3. Compare original vs round-trip HBJSON
4. Validate geometry, materials, systems

Author: ECO Tools Team
Date: November 14, 2025
"""

import sys
import json
from pathlib import Path
from typing import Dict, List, Tuple, Any
import traceback

# Add project root to path
ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from eco_tools.translators.hbjson.importer import HBJSONImporter
from eco_tools.translators.hbjson.exporter import HBJSONExporter
from eco_tools.core.internal_repr import InternalRepresentation


class HBJSONRoundTripValidator:
    """Validate HBJSON → EMJSON → HBJSON round-trip translation"""

    def __init__(self, verbose: bool = True):
        self.verbose = verbose
        self.results: List[Dict[str, Any]] = []

    def validate_file(self, hbjson_path: str, output_dir: str = "test_output/hbjson_roundtrip") -> Dict[str, Any]:
        """
        Validate round-trip for a single HBJSON file

        Args:
            hbjson_path: Path to input HBJSON file
            output_dir: Directory for output files

        Returns:
            Dictionary with validation results
        """
        result = {
            "file": Path(hbjson_path).name,
            "status": "unknown",
            "import_success": False,
            "export_success": False,
            "comparison": {},
            "errors": [],
            "warnings": []
        }

        try:
            if self.verbose:
                print(f"\n{'='*60}")
                print(f"Testing: {Path(hbjson_path).name}")
                print(f"{'='*60}")

            # Step 1: Import HBJSON → EMJSON
            if self.verbose:
                print("Step 1: Importing HBJSON → EMJSON...")

            importer = HBJSONImporter()
            internal_repr = importer.import_file(hbjson_path)

            if internal_repr is None:
                result["status"] = "error"
                result["errors"].append("Import returned None")
                return result

            result["import_success"] = True

            # Collect statistics from EMJSON
            result["emjson_stats"] = {
                "zones": len(internal_repr.zones) if hasattr(internal_repr, 'zones') else 0,
                "surfaces": sum(len(z.surfaces) for z in internal_repr.zones) if hasattr(internal_repr, 'zones') else 0,
                "materials": len(internal_repr.materials) if hasattr(internal_repr, 'materials') else 0,
                "constructions": len(internal_repr.constructions) if hasattr(internal_repr, 'constructions') else 0,
            }

            if self.verbose:
                print(f"  ✓ Import successful")
                print(f"    - Zones: {result['emjson_stats']['zones']}")
                print(f"    - Surfaces: {result['emjson_stats']['surfaces']}")
                print(f"    - Materials: {result['emjson_stats']['materials']}")
                print(f"    - Constructions: {result['emjson_stats']['constructions']}")

            # Step 2: Export EMJSON → HBJSON
            if self.verbose:
                print("\nStep 2: Exporting EMJSON → HBJSON...")

            Path(output_dir).mkdir(parents=True, exist_ok=True)
            output_path = Path(output_dir) / f"{Path(hbjson_path).stem}_roundtrip.hbjson"

            exporter = HBJSONExporter()
            exporter.export_to_file(internal_repr, str(output_path))

            result["export_success"] = True
            result["output_file"] = str(output_path)

            if self.verbose:
                print(f"  ✓ Export successful: {output_path.name}")

            # Step 3: Compare original vs round-trip
            if self.verbose:
                print("\nStep 3: Comparing original vs round-trip...")

            comparison = self._compare_hbjson_files(hbjson_path, str(output_path))
            result["comparison"] = comparison

            # Determine overall status
            if comparison["rooms_match"] and comparison["total_faces_match"]:
                result["status"] = "success"
            elif result["import_success"] and result["export_success"]:
                result["status"] = "partial"
                result["warnings"].append("Round-trip completed but some differences detected")
            else:
                result["status"] = "error"

            if self.verbose:
                print(f"\n  Status: {result['status'].upper()}")
                if comparison.get("differences"):
                    print(f"  Differences: {len(comparison['differences'])}")

        except Exception as e:
            result["status"] = "error"
            result["errors"].append(str(e))
            result["traceback"] = traceback.format_exc()

            if self.verbose:
                print(f"\n  ✗ ERROR: {str(e)}")
                print(f"\n{traceback.format_exc()}")

        return result

    def _compare_hbjson_files(self, original_path: str, roundtrip_path: str) -> Dict[str, Any]:
        """Compare two HBJSON files"""
        comparison = {
            "original_file": Path(original_path).name,
            "roundtrip_file": Path(roundtrip_path).name,
            "rooms_match": False,
            "total_faces_match": False,
            "differences": []
        }

        try:
            # Load both files
            with open(original_path, 'r') as f:
                original = json.load(f)
            with open(roundtrip_path, 'r') as f:
                roundtrip = json.load(f)

            # Compare room counts
            orig_rooms = len(original.get("rooms", []))
            rt_rooms = len(roundtrip.get("rooms", []))
            comparison["original_rooms"] = orig_rooms
            comparison["roundtrip_rooms"] = rt_rooms
            comparison["rooms_match"] = (orig_rooms == rt_rooms)

            if orig_rooms != rt_rooms:
                comparison["differences"].append(
                    f"Room count mismatch: {orig_rooms} → {rt_rooms}"
                )

            # Compare total face counts
            orig_faces = sum(len(r.get("faces", [])) for r in original.get("rooms", []))
            rt_faces = sum(len(r.get("faces", [])) for r in roundtrip.get("rooms", []))
            comparison["original_faces"] = orig_faces
            comparison["roundtrip_faces"] = rt_faces
            comparison["total_faces_match"] = (orig_faces == rt_faces)

            if orig_faces != rt_faces:
                comparison["differences"].append(
                    f"Face count mismatch: {orig_faces} → {rt_faces}"
                )

            # Compare properties
            orig_props = original.get("properties", {})
            rt_props = roundtrip.get("properties", {})

            if "energy" in orig_props and "energy" not in rt_props:
                comparison["differences"].append("Energy properties lost in round-trip")

            # File size comparison
            orig_size = Path(original_path).stat().st_size
            rt_size = Path(roundtrip_path).stat().st_size
            comparison["original_size"] = orig_size
            comparison["roundtrip_size"] = rt_size
            comparison["size_ratio"] = rt_size / orig_size if orig_size > 0 else 0

            if self.verbose:
                print(f"    Rooms: {orig_rooms} → {rt_rooms} {'✓' if comparison['rooms_match'] else '✗'}")
                print(f"    Faces: {orig_faces} → {rt_faces} {'✓' if comparison['total_faces_match'] else '✗'}")
                print(f"    Size: {orig_size:,} → {rt_size:,} bytes ({comparison['size_ratio']:.1%})")

        except Exception as e:
            comparison["error"] = str(e)
            comparison["differences"].append(f"Comparison failed: {str(e)}")

        return comparison

    def validate_all_samples(self, samples_dir: str = "reference_data/hbjson_samples") -> Dict[str, Any]:
        """
        Validate all HBJSON samples in directory

        Returns:
            Dictionary with aggregate results
        """
        samples_path = Path(samples_dir)
        if not samples_path.exists():
            return {
                "status": "error",
                "message": f"Samples directory not found: {samples_dir}"
            }

        hbjson_files = sorted(samples_path.glob("*.hbjson"))

        print(f"\n{'='*60}")
        print(f"HBJSON ROUND-TRIP VALIDATION")
        print(f"{'='*60}")
        print(f"Found {len(hbjson_files)} HBJSON sample files")
        print(f"Output: test_output/hbjson_roundtrip/")
        print(f"{'='*60}\n")

        # Test each file
        for hbjson_file in hbjson_files:
            result = self.validate_file(str(hbjson_file))
            self.results.append(result)

        # Generate summary
        summary = self._generate_summary()

        return summary

    def _generate_summary(self) -> Dict[str, Any]:
        """Generate summary statistics from all results"""
        total = len(self.results)
        success = sum(1 for r in self.results if r["status"] == "success")
        partial = sum(1 for r in self.results if r["status"] == "partial")
        errors = sum(1 for r in self.results if r["status"] == "error")

        import_success = sum(1 for r in self.results if r["import_success"])
        export_success = sum(1 for r in self.results if r["export_success"])

        summary = {
            "total_files": total,
            "success": success,
            "partial": partial,
            "errors": errors,
            "import_success_rate": import_success / total if total > 0 else 0,
            "export_success_rate": export_success / total if total > 0 else 0,
            "full_roundtrip_rate": success / total if total > 0 else 0,
            "results": self.results
        }

        # Print summary
        print(f"\n{'='*60}")
        print(f"VALIDATION SUMMARY")
        print(f"{'='*60}")
        print(f"Total Files:         {total}")
        print(f"Full Success:        {success} ({success/total*100:.1f}%)")
        print(f"Partial Success:     {partial} ({partial/total*100:.1f}%)")
        print(f"Errors:              {errors} ({errors/total*100:.1f}%)")
        print(f"")
        print(f"Import Success Rate: {import_success}/{total} ({summary['import_success_rate']*100:.1f}%)")
        print(f"Export Success Rate: {export_success}/{total} ({summary['export_success_rate']*100:.1f}%)")
        print(f"Round-Trip Success:  {success}/{total} ({summary['full_roundtrip_rate']*100:.1f}%)")
        print(f"{'='*60}\n")

        # Show failures
        failures = [r for r in self.results if r["status"] == "error"]
        if failures:
            print(f"FAILED FILES ({len(failures)}):")
            for r in failures:
                print(f"  ✗ {r['file']}")
                if r["errors"]:
                    print(f"    Error: {r['errors'][0]}")

        partials = [r for r in self.results if r["status"] == "partial"]
        if partials:
            print(f"\nPARTIAL SUCCESS ({len(partials)}):")
            for r in partials:
                print(f"  ⚠ {r['file']}")
                if r["warnings"]:
                    print(f"    Warning: {r['warnings'][0]}")

        successes = [r for r in self.results if r["status"] == "success"]
        if successes:
            print(f"\nFULL SUCCESS ({len(successes)}):")
            for r in successes:
                print(f"  ✓ {r['file']}")

        return summary


def main():
    """Main entry point"""
    validator = HBJSONRoundTripValidator(verbose=True)

    # Run validation on all samples
    summary = validator.validate_all_samples()

    # Save detailed results to JSON
    output_path = Path("test_output/hbjson_roundtrip/validation_results.json")
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, 'w') as f:
        json.dump(summary, f, indent=2)

    print(f"\nDetailed results saved to: {output_path}")

    # Exit with appropriate code
    if summary["errors"] > 0:
        sys.exit(1)
    elif summary["partial"] > 0:
        sys.exit(2)
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()
