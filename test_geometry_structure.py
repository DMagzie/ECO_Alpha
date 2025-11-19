#!/usr/bin/env python3
"""
Test CIBD25 geometry structure against source CIBD22X.

This script validates that all geometry objects are properly extracted
and compares counts between source and export.
"""

import xml.etree.ElementTree as ET
from collections import Counter


def analyze_source_structure(xml_path):
    """Analyze source CIBD22X structure."""
    print(f"\n{'='*80}")
    print(f"SOURCE ANALYSIS: {xml_path}")
    print(f"{'='*80}\n")

    tree = ET.parse(xml_path)
    root = tree.getroot()

    # Count objects by type
    object_counts = Counter()

    # Find all elements
    for elem in root.iter():
        tag = elem.tag.split('}')[-1]  # Remove namespace
        object_counts[tag] += 1

    print("Top-level object counts in source XML:")
    relevant_objects = [
        'Proj', 'Bldg', 'ResZnGrp', 'ResZn', 'ResOtherZn', 'DwellUnit',
        'AirSys', 'ResExtWall', 'ResIntWall', 'ResWin', 'ResSlabFlr',
        'ResIntFlr', 'ResCathedralCeiling', 'ResOpening', 'ResExtFlr'
    ]

    for obj_type in relevant_objects:
        count = object_counts.get(obj_type, 0)
        print(f"  {obj_type:25} {count:4}")

    # Analyze Bldg children
    print("\nBldg children in source XML:")
    for bldg in root.findall('.//{*}Bldg'):
        child_counts = Counter()
        for child in bldg:
            tag = child.tag.split('}')[-1]
            child_counts[tag] += 1

        for tag, count in sorted(child_counts.items()):
            print(f"  {tag:25} {count:4}")

    # Analyze AirSys structure
    print("\nAirSys systems in source XML:")
    for airsys in root.findall('.//{*}AirSys'):
        name_elem = airsys.find('{*}Name')
        name = name_elem.text if name_elem is not None else "Unnamed"

        # Count children
        child_count = len(list(airsys))
        print(f"  {name:30} ({child_count} children)")

    return object_counts


def analyze_export_structure(cibd25_path):
    """Analyze exported CIBD25 structure."""
    print(f"\n{'='*80}")
    print(f"EXPORT ANALYSIS: {cibd25_path}")
    print(f"{'='*80}\n")

    with open(cibd25_path, 'r') as f:
        lines = f.readlines()

    # Count top-level objects (lines that start with capital letter and have quotes)
    object_counts = Counter()
    current_obj = None
    indent_level = 0

    for line in lines:
        stripped = line.lstrip()
        if not stripped or stripped.startswith('RulesetFilename'):
            continue

        # Calculate indent
        indent = len(line) - len(stripped)

        # Check if this is an object definition (has quotes or is bare type)
        if indent == 0 and not '=' in line and stripped[0].isupper():
            # Extract object type
            parts = stripped.split('"')
            obj_type = parts[0].strip()
            object_counts[obj_type] += 1

    print("Top-level object counts in export:")
    relevant_objects = [
        'Proj', 'Bldg', 'ResZnGrp', 'ResZn', 'ResOtherZn', 'DwellUnit',
        'AirSys', 'ResExtWall', 'ResIntWall', 'ResWin', 'ResSlabFlr',
        'ResIntFlr', 'ResCathedralCeiling', 'ResOpening', 'ResExtFlr',
        'AirSeg', 'CoilHtg', 'CoilClg', 'Fan', 'TrmlUnit', 'OACtrl'
    ]

    for obj_type in relevant_objects:
        count = object_counts.get(obj_type, 0)
        status = "✓" if count > 0 else "✗"
        print(f"  {status} {obj_type:25} {count:4}")

    return object_counts


def compare_structures(source_counts, export_counts):
    """Compare source and export structures."""
    print(f"\n{'='*80}")
    print("COMPARISON: Source vs Export")
    print(f"{'='*80}\n")

    # Objects that should be at top level in export
    top_level_objects = [
        'ResZnGrp', 'ResZn', 'ResOtherZn', 'DwellUnit',
        'AirSys', 'ResExtWall', 'ResIntWall', 'ResWin', 'ResSlabFlr',
        'ResIntFlr', 'ResCathedralCeiling', 'ResOpening', 'ResExtFlr'
    ]

    issues = []

    for obj_type in top_level_objects:
        source_count = source_counts.get(obj_type, 0)
        export_count = export_counts.get(obj_type, 0)

        if source_count > 0:
            if export_count == 0:
                status = "✗ MISSING"
                issues.append(f"{obj_type}: {source_count} in source, 0 in export")
            elif export_count == source_count:
                status = "✓ MATCH"
            else:
                status = f"⚠ COUNT DIFF"
                issues.append(f"{obj_type}: {source_count} in source, {export_count} in export")
        else:
            status = "- N/A"

        print(f"  {status:15} {obj_type:25} Source: {source_count:4}  Export: {export_count:4}")

    # Check for objects that should NOT be at top level
    print("\nObjects that should be NESTED (not at top level):")
    nested_objects = ['Proj', 'Bldg']

    for obj_type in nested_objects:
        export_count = export_counts.get(obj_type, 0)
        if export_count > 1:
            status = "✗ EXTRACTED"
            issues.append(f"{obj_type} should have 1 instance but has {export_count}")
        else:
            status = "✓ CORRECT"

        print(f"  {status:15} {obj_type:25} Export: {export_count:4}")

    # Summary
    print(f"\n{'='*80}")
    if issues:
        print(f"❌ ISSUES FOUND: {len(issues)}")
        for issue in issues:
            print(f"  - {issue}")
    else:
        print("✅ ALL CHECKS PASSED")
    print(f"{'='*80}\n")

    return len(issues) == 0


def main():
    source_path = "/Users/DavidM/Dropbox/EM-Tools-Assets/CBECC Models/Bressi Ranch/Bressi Ranch Apartments.cibd22x"
    export_path = "/Users/DavidM/Downloads/Bressi_Ranch_FINAL_GEOMETRY_EXTRACTED.cibd25"

    # Analyze both files
    source_counts = analyze_source_structure(source_path)
    export_counts = analyze_export_structure(export_path)

    # Compare
    success = compare_structures(source_counts, export_counts)

    return 0 if success else 1


if __name__ == '__main__':
    import sys
    sys.exit(main())
