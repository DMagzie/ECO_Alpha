#!/usr/bin/env python3
"""
Development File Cleanup Script

Safely removes temporary development and testing files while preserving:
- Production code
- Documentation
- Test framework (tests/ directory)
- Important test files (test_all_format_roundtrips.py, test_complete_roundtrip.py)

Run with --dry-run to see what would be deleted without actually deleting.
"""

import os
import shutil
from pathlib import Path
import argparse

# Root directory
ROOT = Path(__file__).parent

# Files/directories to remove
TO_REMOVE = {
    # Python cache
    '__pycache__': 'directory',
    '*.pyc': 'pattern',
    '*.pyo': 'pattern',

    # Temporary test files (keep important ones)
    'test_both_formats.py': 'file',
    'test_bressi_cibd25.py': 'file',
    'test_cibd22_surface_import.py': 'file',
    'test_cibd22x_still_works.py': 'file',
    'test_cibd25_complete.py': 'file',
    'test_cibd25_export.py': 'file',
    'test_cibd25_final_demo.py': 'file',
    'test_gem_import.py': 'file',
    'test_gem_integration.py': 'file',
    'test_gui_cibd25_export.py': 'file',
    'test_surface_area_debug.py': 'file',

    # Temporary output (but keep test_output/format_roundtrips and test_output/roundtrip)
    'test_output/Bressi_Ranch_2025.xml': 'file',
    'test_output/Bressi_Ranch_CIBD25_Full.xml': 'file',
    'test_output/Bressi_Ranch_CIBD25.cibd25': 'file',
    'test_output/Bressi_Ranch_CIBD25.xml': 'file',
    'test_output/Bressi_Ranch_Complete.cibd25': 'file',
    'test_output/Bressi_Ranch_FINAL_DEMO.cibd25': 'file',
    'test_output/Bressi_Ranch_GUI_Export.cibd25': 'file',
    'test_output/Bressi_Ranch_text_test.cibd25': 'file',
    'test_output/Bressi_Ranch.cibd25': 'file',
    'test_output/cibd25_minimal_test.xml': 'file',
    'test_output/version_test.cibd25': 'file',
    'test_output/version_test.log': 'file',
    'test_output/gibraltar_export.emjson.json': 'file',
    'test_output/simple_box_export.emjson.json': 'file',
    'test_output/020012-OffSml-CECStd_roundtrip.xml': 'file',

    # Roundtrip validation (empty directory)
    'roundtrip_validation': 'directory',
}

# Files/directories to KEEP (important test files)
TO_KEEP = {
    'test_all_format_roundtrips.py',  # Complete format roundtrip tests
    'test_complete_roundtrip.py',     # Core roundtrip test
    'test_output/format_roundtrips',  # Format test results
    'test_output/roundtrip',          # Roundtrip test results
    'tests/',                         # Test framework
}


def find_pycache_dirs(root):
    """Find all __pycache__ directories."""
    pycache_dirs = []
    for dirpath, dirnames, filenames in os.walk(root):
        if '__pycache__' in dirnames:
            pycache_dirs.append(Path(dirpath) / '__pycache__')
    return pycache_dirs


def clean_files(dry_run=True):
    """
    Clean development files.

    Args:
        dry_run: If True, only show what would be deleted without deleting
    """
    deleted_count = 0
    deleted_size = 0
    errors = []

    print("=" * 80)
    print("DEVELOPMENT FILE CLEANUP")
    print("=" * 80)
    print(f"Mode: {'DRY RUN (no files will be deleted)' if dry_run else 'LIVE (files will be deleted)'}")
    print()

    # Remove __pycache__ directories
    print("Scanning for __pycache__ directories...")
    pycache_dirs = find_pycache_dirs(ROOT)

    for pycache_dir in pycache_dirs:
        relative_path = pycache_dir.relative_to(ROOT)
        try:
            size = sum(f.stat().st_size for f in pycache_dir.rglob('*') if f.is_file())

            if dry_run:
                print(f"  [DRY RUN] Would delete: {relative_path} ({size:,} bytes)")
            else:
                shutil.rmtree(pycache_dir)
                print(f"  ✓ Deleted: {relative_path} ({size:,} bytes)")

            deleted_count += 1
            deleted_size += size

        except Exception as e:
            errors.append(f"Error removing {relative_path}: {e}")

    # Remove specific files and directories
    print("\nCleaning development files...")

    for item, item_type in TO_REMOVE.items():
        path = ROOT / item

        if not path.exists():
            continue

        relative_path = path.relative_to(ROOT)

        try:
            if item_type == 'directory':
                size = sum(f.stat().st_size for f in path.rglob('*') if f.is_file())

                if dry_run:
                    print(f"  [DRY RUN] Would delete directory: {relative_path} ({size:,} bytes)")
                else:
                    shutil.rmtree(path)
                    print(f"  ✓ Deleted directory: {relative_path} ({size:,} bytes)")

                deleted_count += 1
                deleted_size += size

            elif item_type == 'file':
                size = path.stat().st_size

                if dry_run:
                    print(f"  [DRY RUN] Would delete: {relative_path} ({size:,} bytes)")
                else:
                    path.unlink()
                    print(f"  ✓ Deleted: {relative_path} ({size:,} bytes)")

                deleted_count += 1
                deleted_size += size

        except Exception as e:
            errors.append(f"Error removing {relative_path}: {e}")

    # Summary
    print("\n" + "=" * 80)
    print("CLEANUP SUMMARY")
    print("=" * 80)

    if dry_run:
        print(f"Files that would be deleted: {deleted_count}")
        print(f"Space that would be freed: {deleted_size:,} bytes ({deleted_size / 1024 / 1024:.2f} MB)")
        print("\nRun without --dry-run to actually delete these files.")
    else:
        print(f"Files deleted: {deleted_count}")
        print(f"Space freed: {deleted_size:,} bytes ({deleted_size / 1024 / 1024:.2f} MB)")

    if errors:
        print(f"\nErrors encountered: {len(errors)}")
        for error in errors:
            print(f"  • {error}")

    # Show what was kept
    print("\n" + "=" * 80)
    print("IMPORTANT FILES PRESERVED")
    print("=" * 80)

    kept_files = []
    for item in TO_KEEP:
        path = ROOT / item
        if path.exists():
            if path.is_file():
                size = path.stat().st_size
                kept_files.append(f"  ✓ {item} ({size:,} bytes)")
            else:
                kept_files.append(f"  ✓ {item}/ (directory)")

    for kept in sorted(kept_files):
        print(kept)

    return deleted_count, deleted_size, errors


def main():
    parser = argparse.ArgumentParser(
        description='Clean up development and testing files from ECO_Alpha_v7',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # See what would be deleted (safe)
  python cleanup_dev_files.py --dry-run

  # Actually delete the files
  python cleanup_dev_files.py

  # Force delete without confirmation
  python cleanup_dev_files.py --force
"""
    )

    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be deleted without actually deleting'
    )

    parser.add_argument(
        '--force',
        action='store_true',
        help='Delete files without confirmation prompt'
    )

    args = parser.parse_args()

    # If not dry run and not forced, ask for confirmation
    if not args.dry_run and not args.force:
        print("=" * 80)
        print("WARNING: This will DELETE development files!")
        print("=" * 80)
        print("\nRun with --dry-run first to see what would be deleted.")
        response = input("\nAre you sure you want to continue? (yes/no): ")

        if response.lower() not in ['yes', 'y']:
            print("Cancelled.")
            return

    # Run cleanup
    clean_files(dry_run=args.dry_run)


if __name__ == '__main__':
    main()
