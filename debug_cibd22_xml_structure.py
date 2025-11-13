#!/usr/bin/env python3
"""
Debug script to examine XML structure created by CIBD22 text parser.
Shows the hierarchy of zones and their children to verify surface nesting.
"""

import sys
from pathlib import Path

# Add project root to path
ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from eco_tools.translators.cibd22.text_parser import parse_cibd22_file

def show_element_tree(elem, indent=0, max_depth=4):
    """Recursively show element tree structure."""
    if indent > max_depth:
        return

    prefix = "  " * indent

    # Get name if present
    name_elem = elem.find('n')
    name = name_elem.text if name_elem is not None else elem.get('Name', 'NO_NAME')

    # Count children by type
    child_counts = {}
    for child in elem:
        tag = child.tag
        child_counts[tag] = child_counts.get(tag, 0) + 1

    # Show element info
    children_info = ", ".join(f"{count} {tag}" for tag, count in sorted(child_counts.items()) if tag != 'n')
    print(f"{prefix}{elem.tag} '{name}' [{children_info if children_info else 'no children'}]")

    # Recurse for important elements only
    if elem.tag in ['SDDXML', 'Proj', 'Bldg', 'ThrmlZn', 'Spc']:
        for child in elem:
            if child.tag != 'n':  # Skip name elements
                show_element_tree(child, indent + 1, max_depth)


if __name__ == "__main__":
    # Test file
    test_file = "/Users/DavidM/Documents/ECO_Alpha/Test Projects/ICD/Cesar_Chavez_FinalV9.cibd22"

    print("Parsing CIBD22 text file...")
    root = parse_cibd22_file(test_file)

    print(f"\n{'='*80}")
    print("XML STRUCTURE")
    print(f"{'='*80}\n")

    show_element_tree(root, max_depth=5)

    # Now specifically look for ThrmlZn elements and their children
    print(f"\n{'='*80}")
    print("THERMAL ZONES AND THEIR SURFACE CHILDREN")
    print(f"{'='*80}\n")

    zone_count = 0
    for zone_elem in root.iter('ThrmlZn'):
        zone_count += 1
        name_elem = zone_elem.find('n')
        zone_name = name_elem.text if name_elem is not None else 'NO_NAME'

        # Count surfaces by type
        surface_counts = {}
        surface_tags = ['ExtWall', 'IntWall', 'Win', 'Roof', 'FlrOnGrade', 'Ceiling',
                       'ResSlabFlr', 'ResExtWall', 'ResIntWall', 'ResWin']

        for surf_tag in surface_tags:
            count = len(list(zone_elem.iter(surf_tag)))
            if count > 0:
                surface_counts[surf_tag] = count

        total_surfaces = sum(surface_counts.values())

        if surface_counts:
            print(f"Zone '{zone_name}': {total_surfaces} surfaces")
            for surf_tag, count in sorted(surface_counts.items()):
                print(f"  - {count} {surf_tag}")
        else:
            print(f"Zone '{zone_name}': NO SURFACES")

    print(f"\nTotal zones found: {zone_count}")

    # Also check for surfaces at root level (shouldn't be there)
    print(f"\n{'='*80}")
    print("SURFACES AT ROOT LEVEL (SHOULD BE ZERO)")
    print(f"{'='*80}\n")

    root_surface_tags = ['ExtWall', 'IntWall', 'Win', 'Roof', 'FlrOnGrade',
                         'ResSlabFlr', 'ResExtWall', 'ResIntWall', 'ResWin']

    for surf_tag in root_surface_tags:
        # Find surfaces that are direct children of root (not nested in zones)
        direct_children = [elem for elem in root if elem.tag == surf_tag]
        if direct_children:
            print(f"{len(direct_children)} {surf_tag} elements at root level (PROBLEM!)")
