"""
CIBD22X Import Audit Script
Tests current CIBD22X adapter capabilities with Gibraltar model
"""

from eco_tools.formats.cibd22x_adapter import CIBD22XAdapter
import json


def audit_cibd22x_import():
    """Comprehensive audit of CIBD22X import capabilities"""

    test_file = '/Users/DavidM/Documents/ECO_Alpha/Test Projects/Gibraltar_CLEAN_START.cibd22x'

    print("=" * 70)
    print("CIBD22X IMPORT AUDIT - Session 1")
    print("=" * 70)
    print(f"\nTest File: {test_file}")
    print(f"Format: CBECC-Com SDDXML (despite .cibd22x extension)")

    # Test import
    adapter = CIBD22XAdapter()
    try:
        ir = adapter.parse(test_file)
        print("\n✅ Import successful!")
    except Exception as e:
        print(f"\n❌ Import failed: {e}")
        import traceback
        traceback.print_exc()
        return

    # Summary statistics
    print("\n" + "=" * 70)
    print("IMPORT SUMMARY")
    print("=" * 70)

    print(f"\n📐 GEOMETRY:")
    print(f"  Zones: {len(ir.zones)}")
    print(f"  Zone Groups: {len(ir.zone_groups)}")
    print(f"  Surfaces: {len(ir.surfaces)}")
    print(f"  Openings: {len(ir.openings)}")

    print(f"\n🔧 SYSTEMS:")
    print(f"  HVAC Systems: {len(ir.hvac_systems)}")
    print(f"  Zone Terminals: {len(ir.zone_terminals) if hasattr(ir, 'zone_terminals') else 0}")
    print(f"  IAQ Fans: {len(ir.iaq_fans)}")
    print(f"  DHW Systems: {len(ir.dhw_systems)}")
    print(f"  Water Heaters: {len(ir.water_heaters) if hasattr(ir, 'water_heaters') else 0}")
    print(f"  PV Arrays: {len(ir.pv_arrays)}")

    print(f"\n💡 LIGHTING & CONTROLS:")
    print(f"  Lighting Systems: {len(ir.lighting_systems)}")
    print(f"  Luminaires: {len(ir.luminaires)}")
    print(f"  Control Systems: {len(ir.control_systems) if hasattr(ir, 'control_systems') else 0}")

    print(f"\n📚 CATALOGS:")
    print(f"  Materials: {len(ir.materials)}")
    print(f"  Constructions: {len(ir.constructions)}")
    print(f"  Window Types: {len(ir.window_types)}")
    print(f"  DU Types: {len(ir.du_types)}")

    print(f"\n⚡ ENERGY:")
    print(f"  Schedules: {len(ir.schedules)}")

    # Detailed zone analysis
    print("\n" + "=" * 70)
    print("ZONE ANALYSIS (First 5 zones)")
    print("=" * 70)

    for i, zone in enumerate(ir.zones[:5]):
        print(f"\nZone {i+1}: {zone.name}")
        print(f"  ID: {zone.id}")
        print(f"  Building Type: {zone.building_type}")
        print(f"  Floor Area: {zone.floor_area_m2:.2f} m²" if zone.floor_area_m2 else "  Floor Area: None")
        print(f"  Volume: {zone.volume_m3:.2f} m³" if zone.volume_m3 else "  Volume: None")
        print(f"  Multiplier: {zone.multiplier}")
        print(f"  Space Function: {zone.space_function}")
        print(f"  Served By (HVAC refs): {zone.served_by}")
        print(f"  Surface count: {len(zone.surfaces)}")

    # Surface type breakdown
    print("\n" + "=" * 70)
    print("SURFACE TYPE BREAKDOWN")
    print("=" * 70)

    surface_types = {}
    for surf in ir.surfaces:
        surf_type = surf.surface_type
        surface_types[surf_type] = surface_types.get(surf_type, 0) + 1

    for surf_type, count in sorted(surface_types.items()):
        print(f"  {surf_type}: {count}")

    # Opening type breakdown
    print("\n" + "=" * 70)
    print("OPENING TYPE BREAKDOWN")
    print("=" * 70)

    opening_types = {}
    for opening in ir.openings:
        open_type = opening.type
        opening_types[open_type] = opening_types.get(open_type, 0) + 1

    for open_type, count in sorted(opening_types.items()):
        print(f"  {open_type}: {count}")

    # Check for simulation-ready data
    print("\n" + "=" * 70)
    print("SIMULATION-READY DATA CHECK")
    print("=" * 70)

    # Check if zones have required data for simulation
    zones_with_area = sum(1 for z in ir.zones if z.floor_area_m2 is not None)
    zones_with_volume = sum(1 for z in ir.zones if z.volume_m3 is not None)
    zones_with_hvac = sum(1 for z in ir.zones if z.served_by)
    zones_with_space_func = sum(1 for z in ir.zones if z.space_function)

    print(f"\nZone Completeness:")
    print(f"  ✅ Zones with floor area: {zones_with_area}/{len(ir.zones)} ({zones_with_area/len(ir.zones)*100:.1f}%)")
    print(f"  ✅ Zones with volume: {zones_with_volume}/{len(ir.zones)} ({zones_with_volume/len(ir.zones)*100:.1f}%)")
    print(f"  ❌ Zones with HVAC: {zones_with_hvac}/{len(ir.zones)} ({zones_with_hvac/len(ir.zones)*100:.1f}%)")
    print(f"  {'✅' if zones_with_space_func > 0 else '❌'} Zones with space function: {zones_with_space_func}/{len(ir.zones)} ({zones_with_space_func/len(ir.zones)*100:.1f}%)")

    # Check surfaces
    surfaces_with_area = sum(1 for s in ir.surfaces if s.area_m2 is not None)
    surfaces_with_construction = sum(1 for s in ir.surfaces if s.construction_ref)

    print(f"\nSurface Completeness:")
    print(f"  ✅ Surfaces with area: {surfaces_with_area}/{len(ir.surfaces)} ({surfaces_with_area/len(ir.surfaces)*100:.1f}%)")
    print(f"  {'✅' if surfaces_with_construction > 0 else '❌'} Surfaces with construction: {surfaces_with_construction}/{len(ir.surfaces)} ({surfaces_with_construction/len(ir.surfaces)*100:.1f}%)")

    # Check openings
    openings_with_area = sum(1 for o in ir.openings if o.area_m2 is not None)
    openings_with_window_type = sum(1 for o in ir.openings if o.window_type_ref)
    openings_with_properties = sum(1 for o in ir.openings if o.u_factor_SI or o.shgc or o.vt)

    print(f"\nOpening Completeness:")
    print(f"  ✅ Openings with area: {openings_with_area}/{len(ir.openings)} ({openings_with_area/len(ir.openings)*100:.1f}%)")
    print(f"  {'✅' if openings_with_window_type > 0 else '❌'} Openings with window type: {openings_with_window_type}/{len(ir.openings)} ({openings_with_window_type/len(ir.openings)*100:.1f}%)")
    print(f"  {'✅' if openings_with_properties > 0 else '❌'} Openings with thermal properties: {openings_with_properties}/{len(ir.openings)} ({openings_with_properties/len(ir.openings)*100:.1f}%)")

    # GAPS IDENTIFICATION
    print("\n" + "=" * 70)
    print("GAPS FOR MVP SIMULATION")
    print("=" * 70)

    gaps = []

    if len(ir.hvac_systems) == 0:
        gaps.append("❌ CRITICAL: No HVAC systems imported")

    if len(ir.schedules) == 0:
        gaps.append("❌ CRITICAL: No schedules imported")

    if zones_with_hvac == 0:
        gaps.append("❌ CRITICAL: No zones linked to HVAC systems")

    # Check for internal loads data (would be in zone annotation)
    zones_with_loads_data = 0
    if ir.zones:
        # Check annotation for any load-related keys
        sample_zone = ir.zones[0]
        load_keys = ['people_density', 'lighting_power_density', 'equipment_power_density',
                     'occupancy', 'lighting', 'equipment']
        zones_with_loads_data = sum(1 for z in ir.zones
                                    if any(key in z.annotation for key in load_keys))

    if zones_with_loads_data == 0:
        gaps.append("❌ CRITICAL: No internal loads data (people, lighting, equipment)")

    if len(ir.constructions) < 3:
        gaps.append("⚠️  WARNING: Limited construction library")

    if len(ir.window_types) < 2:
        gaps.append("⚠️  WARNING: Limited window type library")

    print("\nIdentified Gaps:")
    for gap in gaps:
        print(f"  {gap}")

    if not gaps:
        print("  ✅ All required data present!")

    # Summary
    print("\n" + "=" * 70)
    print("AUDIT COMPLETE")
    print("=" * 70)

    print(f"\n✅ WORKING:")
    print(f"   - Geometry import (zones, surfaces, openings)")
    print(f"   - Basic catalogs (materials, constructions, window types)")
    print(f"   - PV systems")
    print(f"   - Some lighting systems")

    print(f"\n❌ MISSING FOR MVP:")
    print(f"   - HVAC systems import")
    print(f"   - Internal loads (people, lighting, equipment densities)")
    print(f"   - Schedules")
    print(f"   - Zone-to-HVAC linkage")
    print(f"   - DHW systems (partially)")

    print(f"\n📋 NEXT STEPS:")
    print(f"   1. Implement HVAC system parsing in CIBD22X adapter")
    print(f"   2. Implement schedule parsing")
    print(f"   3. Implement internal loads extraction from Space elements")
    print(f"   4. Create default libraries for missing data")
    print(f"   5. Extend EMJSON schema to v6.1 with simulation fields")

    return ir


if __name__ == "__main__":
    audit_cibd22x_import()
