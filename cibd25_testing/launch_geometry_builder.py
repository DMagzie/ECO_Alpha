#!/usr/bin/env python3
"""
Interactive Geometry Builder Test
Launch this to experiment with creating building geometry
"""

import sys
sys.path.insert(0, '/Users/DavidM/Documents/ECO_Alpha/eco_tools_parser')

from eco_tools.geometry_builder import GeometryBuilder, EMJSONAdapter
from eco_tools.formats.cibd22x_adapter import CIBD22XAdapter
from eco_tools.formats.cibd25_adapter import CIBD25Adapter
from eco_tools.core.internal_repr import InternalRepresentation, Zone, Material, Construction
import xml.etree.ElementTree as ET
import json


def print_header(title):
    """Print section header"""
    print()
    print("=" * 70)
    print(title.center(70))
    print("=" * 70)
    print()


def create_sample_building():
    """Create a sample building with multiple zones"""
    print_header("CREATING SAMPLE BUILDING")

    builder = GeometryBuilder()

    # Create reception area
    print("Creating Reception Area (6m x 5m x 3m)...")
    reception = builder.create_rectangular_zone(
        width=6.0,
        depth=5.0,
        height=3.0,
        origin=(0, 0),
        zone_name="Reception"
    )
    print(f"  ✅ {reception.name}: {reception.calculate_floor_area():.1f} m²")

    # Create office 1
    print("Creating Office 1 (4m x 4m x 2.7m)...")
    office1 = builder.create_rectangular_zone(
        width=4.0,
        depth=4.0,
        height=2.7,
        origin=(6, 0),
        zone_name="Office 1"
    )
    print(f"  ✅ {office1.name}: {office1.calculate_floor_area():.1f} m²")

    # Create office 2
    print("Creating Office 2 (4m x 4m x 2.7m)...")
    office2 = builder.create_rectangular_zone(
        width=4.0,
        depth=4.0,
        height=2.7,
        origin=(10, 0),
        zone_name="Office 2"
    )
    print(f"  ✅ {office2.name}: {office2.calculate_floor_area():.1f} m²")

    # Create conference room
    print("Creating Conference Room (6m x 4m x 2.7m)...")
    conference = builder.create_rectangular_zone(
        width=6.0,
        depth=4.0,
        height=2.7,
        origin=(6, 4),
        zone_name="Conference Room"
    )
    print(f"  ✅ {conference.name}: {conference.calculate_floor_area():.1f} m²")

    # Show statistics
    stats = builder.get_stats()
    print()
    print("Building Statistics:")
    print(f"  Total Zones: {stats['zone_count']}")
    print(f"  Total Surfaces: {stats['surface_count']}")
    print(f"  Total Floor Area: {stats['total_floor_area_m2']:.1f} m²")
    print(f"  Total Volume: {stats.get('total_volume_m3', 0):.1f} m³")

    return builder


def export_to_emjson(builder):
    """Export to EMJSON format"""
    print_header("EXPORTING TO EMJSON")

    emjson = EMJSONAdapter.to_emjson(builder, "Test Building")

    output_path = '/tmp/geometry_builder_test.emjson'
    with open(output_path, 'w') as f:
        json.dump(emjson, f, indent=2)

    print(f"✅ EMJSON exported to: {output_path}")
    print(f"   Version: {emjson['emjson_version']}")
    print(f"   Zones: {len(emjson['geometry']['zones'])}")
    print(f"   Surfaces: {sum(len(v) for v in emjson['geometry']['surfaces'].values())}")

    return emjson


def export_to_cibd22x(emjson):
    """Export to CIBD22X format"""
    print_header("EXPORTING TO CIBD22X")

    # Create Internal Representation
    internal = InternalRepresentation()
    internal.project_name = "Geometry Builder Test"
    internal.zip_code = 95814

    # Add zones
    for zone_data in emjson['geometry']['zones']:
        zone = Zone(
            id=zone_data['id'],
            name=zone_data['name'],
            building_type='NR',
            volume_m3=zone_data.get('volume_m3', 0)
        )
        internal.zones.append(zone)

    # Add required materials
    material = Material(
        id='Concrete_6in',
        name='Concrete - 6 inch',
        material_type='Concrete'
    )
    internal.materials.append(material)

    # Add required constructions
    wall_construction = Construction(
        id='Exterior_Wall',
        name='Exterior Wall Construction',
        construction_type='ExteriorWall'
    )
    internal.constructions.append(wall_construction)

    # Serialize to CIBD22X
    adapter = CIBD22XAdapter()
    root_element = adapter.serialize(internal)

    # Write to file
    tree = ET.ElementTree(root_element)
    ET.indent(tree, space='  ')

    output_path = '/tmp/geometry_builder_test.cibd22x'
    tree.write(output_path, encoding='utf-8', xml_declaration=True)

    # Get file size
    import os
    file_size = os.path.getsize(output_path)

    print(f"✅ CIBD22X exported to: {output_path}")
    print(f"   File size: {file_size} bytes")
    print(f"   Zones: {len(internal.zones)}")

    # Validate by parsing back
    internal2 = adapter.parse(output_path)
    print(f"   Validation: ✅ {len(internal2.zones)} zones parsed successfully")

    return output_path


def export_to_cibd25(emjson):
    """Export to CIBD25 format"""
    print_header("EXPORTING TO CIBD25")

    # Create Internal Representation
    internal = InternalRepresentation()
    internal.project_name = "Geometry Builder Test"
    internal.zip_code = 95814

    # Add zones
    for zone_data in emjson['geometry']['zones']:
        zone = Zone(
            id=zone_data['id'],
            name=zone_data['name'],
            building_type='NR',
            volume_m3=zone_data.get('volume_m3', 0)
        )
        internal.zones.append(zone)

    # Serialize to CIBD25 (simplified - just showing the structure)
    output_path = '/tmp/geometry_builder_test.cibd25'

    # Create minimal CIBD25 content
    content = f'''RulesetFilename   "T24_2025.bin"

Proj   "{internal.project_name}"
   BldgEngyModelVersion = 17
   ZipCode = {internal.zip_code}
   AutoHardSize = 1
   ..

'''

    # Add zones
    for zone in internal.zones:
        content += f'''Spc   "{zone.name}"
   SpcFuncDefaultsRef = "Office Defaults"
   Volume = {zone.volume_m3:.1f}
   ..

'''

    # Write to file
    with open(output_path, 'w', encoding='iso-8859-1', newline='\r\n') as f:
        f.write(content)

    import os
    file_size = os.path.getsize(output_path)

    print(f"✅ CIBD25 exported to: {output_path}")
    print(f"   File size: {file_size} bytes")
    print(f"   Zones: {len(internal.zones)}")

    # Validate by parsing back
    adapter = CIBD25Adapter()
    internal2 = adapter.parse(output_path)
    print(f"   Validation: ✅ {len(internal2.zones)} zones parsed successfully")

    return output_path


def show_menu():
    """Show interactive menu"""
    print_header("GEOMETRY BUILDER INTERACTIVE TEST")

    print("What would you like to do?")
    print()
    print("  1. Create sample building and export to all formats")
    print("  2. Create sample building only (no export)")
    print("  3. Create custom building (interactive)")
    print("  4. Exit")
    print()

    choice = input("Enter choice (1-4): ").strip()
    return choice


def main():
    """Main interactive loop"""

    while True:
        choice = show_menu()

        if choice == '1':
            # Create and export to all formats
            builder = create_sample_building()
            emjson = export_to_emjson(builder)
            cibd22x_path = export_to_cibd22x(emjson)
            cibd25_path = export_to_cibd25(emjson)

            print_header("COMPLETE!")
            print("All files generated successfully:")
            print(f"  • EMJSON:  /tmp/geometry_builder_test.emjson")
            print(f"  • CIBD22X: /tmp/geometry_builder_test.cibd22x")
            print(f"  • CIBD25:  /tmp/geometry_builder_test.cibd25")
            print()
            input("Press Enter to continue...")

        elif choice == '2':
            # Create only
            builder = create_sample_building()

            print()
            print("Building created! Use the builder object to:")
            print("  • Add more zones: builder.create_rectangular_zone(...)")
            print("  • Get stats: builder.get_stats()")
            print("  • Export: EMJSONAdapter.to_emjson(builder)")
            print()
            input("Press Enter to continue...")

        elif choice == '3':
            # Interactive custom building
            print_header("CUSTOM BUILDING CREATOR")
            print("This feature is coming soon!")
            print("For now, edit the script to customize the building.")
            print()
            input("Press Enter to continue...")

        elif choice == '4':
            print()
            print("Thanks for testing the Geometry Builder!")
            print()
            break

        else:
            print()
            print("Invalid choice. Please enter 1-4.")
            print()
            input("Press Enter to continue...")


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print()
        print()
        print("Exiting...")
        print()
    except Exception as e:
        print()
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
