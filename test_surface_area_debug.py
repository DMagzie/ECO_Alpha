#!/usr/bin/env python3
"""
Debug script to trace surface area parsing.
"""

import sys
from pathlib import Path

# Add project root to path
ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from eco_tools.translators.cibd22.text_parser import parse_cibd22_file
from eco_tools.translators.cibd22x.importer import CIBD22XImporter
from eco_tools.core.id_registry import IDRegistry

if __name__ == "__main__":
    # Test file
    test_file = "/Users/DavidM/Documents/ECO_Alpha/Test Projects/ICD/Cesar_Chavez_FinalV9.cibd22"

    print("Parsing CIBD22 file to XML...")
    root = parse_cibd22_file(test_file)

    # Find first ExtWall
    for zone in root.iter('ThrmlZn'):
        zone_name_elem = zone.find('n')
        zone_name = zone_name_elem.text if zone_name_elem is not None else 'NO_NAME'

        for extwall in zone.findall('ExtWall'):
            wall_name_elem = extwall.find('n')
            wall_name = wall_name_elem.text if wall_name_elem is not None else 'NO_NAME'

            print(f"\n{'='*60}")
            print(f"Testing ExtWall: {wall_name}")
            print(f"{'='*60}")

            # Test get_property manually
            from eco_tools.translators.cibd22x.parsers.base_parser import BaseParser
            parser = BaseParser()

            area_str = parser.get_property(extwall, 'Area')
            print(f"\n1. get_property(extwall, 'Area') = '{area_str}'")

            # Test _to_float
            if area_str:
                area_float = parser._to_float(area_str)
                print(f"2. _to_float('{area_str}') = {area_float}")

                if area_float:
                    area_m2 = area_float * 0.092903
                    print(f"3. Convert to m²: {area_float} ft² * 0.092903 = {area_m2} m²")
                else:
                    print(f"2. ERROR: _to_float returned None/0!")
            else:
                print(f"1. ERROR: get_property returned None!")

            # Now test through actual importer
            print(f"\n{'='*60}")
            print("Testing through CIBD22XImporter...")
            print(f"{'='*60}")

            importer = CIBD22XImporter()
            internal = importer.import_from_xml_root(root)

            # Find this surface
            for surf in internal.surfaces:
                if surf.name == wall_name:
                    print(f"\nFound surface: {surf.name}")
                    print(f"  area_m2: {surf.area_m2}")
                    print(f"  surface_type: {surf.surface_type}")
                    break

            # Only test first wall
            exit(0)
        break
