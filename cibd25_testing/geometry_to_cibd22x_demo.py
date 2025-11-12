#!/usr/bin/env python3
"""
Geometry Builder → CIBD22X Demo

Demonstrates creating building geometry and exporting to CIBD22X format.
"""

import sys
sys.path.insert(0, '/Users/DavidM/Documents/ECO_Alpha/eco_tools_parser')

from eco_tools.geometry_builder import GeometryBuilder, EMJSONAdapter
from eco_tools.formats.cibd22x_adapter import CIBD22XAdapter
from eco_tools.core.internal_repr import InternalRepresentation, Zone, Material, Construction
import xml.etree.ElementTree as ET


def main():
    print()
    print("=" * 60)
    print("GEOMETRY BUILDER → CIBD22X DEMONSTRATION")
    print("=" * 60)
    print()

    # ========================================
    # Step 1: Create Geometry
    # ========================================
    print("Step 1: Creating Building Geometry")
    print("-" * 60)

    builder = GeometryBuilder()

    # Create main office
    print("  Creating Main Office (8m x 6m x 2.7m)...")
    office1 = builder.create_rectangular_zone(
        width=8.0,
        depth=6.0,
        height=2.7,
        origin=(0, 0),
        zone_name="Main Office"
    )

    # Create conference room
    print("  Creating Conference Room (6m x 5m x 2.7m)...")
    conference = builder.create_rectangular_zone(
        width=6.0,
        depth=5.0,
        height=2.7,
        origin=(8, 0),
        zone_name="Conference Room"
    )

    # Create break room
    print("  Creating Break Room (4m x 4m x 2.7m)...")
    breakroom = builder.create_rectangular_zone(
        width=4.0,
        depth=4.0,
        height=2.7,
        origin=(8, 5),
        zone_name="Break Room"
    )

    stats = builder.get_stats()
    print()
    print(f"  ✅ Created {stats['zone_count']} zones")
    print(f"  Total floor area: {stats['total_floor_area_m2']:.1f} m²")
    print(f"  Total surfaces: {stats['surface_count']}")
    print()

    # ========================================
    # Step 2: Convert to InternalRepresentation
    # ========================================
    print("Step 2: Converting to Internal Representation")
    print("-" * 60)

    # Export to EMJSON first
    emjson = EMJSONAdapter.to_emjson(builder, "Office Building")

    # Create IR
    internal = InternalRepresentation()
    internal.zip_code = 95814

    # Add zones
    for zone_data in emjson['geometry']['zones']:
        zone = Zone(
            id=zone_data['id'],
            name=zone_data['name'],
            building_type='NR',  # Non-residential
            volume_m3=zone_data.get('volume_m3', 0)
        )
        internal.zones.append(zone)

    # Add required materials (CIBD22X requires at least one material)
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

    print(f"  ✅ IR created")
    print(f"  Zones: {len(internal.zones)}")
    print(f"  Materials: {len(internal.materials)}")
    print(f"  Constructions: {len(internal.constructions)}")
    print()

    # ========================================
    # Step 3: Serialize to CIBD22X
    # ========================================
    print("Step 3: Generating CIBD22X File")
    print("-" * 60)

    adapter = CIBD22XAdapter()
    root_element = adapter.serialize(internal)

    # Write to file
    tree = ET.ElementTree(root_element)
    ET.indent(tree, space='  ')

    output_file = '/tmp/office_building.cibd22x'
    tree.write(output_file, encoding='utf-8', xml_declaration=True)

    # Get file size
    with open(output_file, 'r') as f:
        content = f.read()

    print(f"  ✅ CIBD22X file generated")
    print(f"  File: {output_file}")
    print(f"  Size: {len(content)} bytes")
    print()

    # Show excerpt
    print("  File content (first 500 chars):")
    print("  " + "-" * 56)
    for line in content.split('\n')[:15]:
        print(f"  {line}")
    print("  ...")
    print()

    # ========================================
    # Step 4: Validate
    # ========================================
    print("Step 4: Validating CIBD22X Output")
    print("-" * 60)

    # Parse the file back
    internal2 = adapter.parse(output_file)

    print(f"  ✅ File parsed successfully")
    print(f"  Zones found: {len(internal2.zones)}")
    print(f"  Zone names:")
    for zone in internal2.zones:
        print(f"    - {zone.name} (Volume: {zone.volume_m3:.1f} m³)")
    print()

    # ========================================
    # Summary
    # ========================================
    print("=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print()
    print("✅ Successfully created CIBD22X model from Geometry Builder!")
    print()
    print("Workflow:")
    print("  1. Geometry Builder → Created 3-zone building")
    print("  2. EMJSON Export → Converted to EMJSON v6")
    print("  3. Internal Rep → Created IR with zones/materials")
    print("  4. CIBD22X Serialize → Generated valid CIBD22X XML")
    print()
    print(f"Output file: {output_file}")
    print()
    print("🎉 You can now use Geometry Builder to generate CIBD22X models!")
    print()


if __name__ == '__main__':
    main()
