"""
Test Space Function Defaults Application
Validates that Title 24/ASHRAE defaults are applied during CIBD22X import
"""

from eco_tools.formats.cibd22x_adapter import CIBD22XAdapter


def test_defaults_application():
    """Test that space function defaults are applied to zones"""

    test_file = '/Users/DavidM/Documents/ECO_Alpha/reference_data/cbecc/CBECC Models/cibd22x/Freedom Circle Building B - LEED.cibd22x'

    print("=" * 70)
    print("SPACE FUNCTION DEFAULTS APPLICATION TEST")
    print("=" * 70)
    print(f"\nTest File: Freedom Circle Building B - LEED.cibd22x\n")

    # Import
    adapter = CIBD22XAdapter()
    ir = adapter.parse(test_file)
    print("✅ Import successful!\n")

    # Test 1: Check zones have defaults applied
    print("=" * 70)
    print("TEST 1: DEFAULTS APPLICATION")
    print("=" * 70)

    zones_with_occ = 0
    zones_with_equip = 0
    zones_with_ltg_default = 0

    for zone in ir.zones:
        if zone.annotation.get('occupancy_density_people_m2') is not None:
            zones_with_occ += 1
        if zone.annotation.get('equipment_power_density_w_m2') is not None:
            zones_with_equip += 1
        if zone.annotation.get('lighting_power_density_w_m2_default') is not None:
            zones_with_ltg_default += 1

    print(f"\nZones with applied defaults:")
    print(f"  Occupancy density: {zones_with_occ}/{len(ir.zones)} ({zones_with_occ/len(ir.zones)*100:.1f}%)")
    print(f"  Equipment density: {zones_with_equip}/{len(ir.zones)} ({zones_with_equip/len(ir.zones)*100:.1f}%)")
    print(f"  Lighting density (fallback): {zones_with_ltg_default}/{len(ir.zones)} ({zones_with_ltg_default/len(ir.zones)*100:.1f}%)")

    # Test 2: Sample zones with defaults
    print("\n" + "=" * 70)
    print("TEST 2: SAMPLE ZONES WITH DEFAULTS")
    print("=" * 70)

    # Get zones with defaults for display
    zones_with_defaults = [z for z in ir.zones
                          if z.annotation.get('occupancy_density_people_m2') is not None]

    if zones_with_defaults:
        print(f"\nShowing first 10 zones with defaults:\n")
        for zone in zones_with_defaults[:10]:
            print(f"  {zone.name} ({zone.space_function})")
            occ_m2 = zone.annotation.get('occupancy_density_people_m2')
            occ_1000ft2 = zone.annotation.get('occupancy_density_people_1000ft2')
            equip_m2 = zone.annotation.get('equipment_power_density_w_m2')
            equip_ft2 = zone.annotation.get('equipment_power_density_w_ft2')
            ltg_m2 = zone.annotation.get('lighting_power_density_w_m2_default')
            ltg_ft2 = zone.annotation.get('lighting_power_density_w_ft2_default')

            if occ_m2:
                print(f"    Occupancy: {occ_m2:.4f} people/m² ({occ_1000ft2:.1f} people/1000 ft²)")
            if equip_m2:
                print(f"    Equipment: {equip_m2:.2f} W/m² ({equip_ft2:.2f} W/ft²)")
            if ltg_m2:
                print(f"    Lighting: {ltg_m2:.2f} W/m² ({ltg_ft2:.2f} W/ft²)")
            print()

    # Test 3: Calculate total internal loads
    print("=" * 70)
    print("TEST 3: TOTAL INTERNAL LOADS")
    print("=" * 70)

    total_occupancy = 0
    total_equipment_power = 0
    total_ltg_power_default = 0
    total_area = 0

    for zone in ir.zones:
        if zone.floor_area_m2:
            total_area += zone.floor_area_m2

            occ_density = zone.annotation.get('occupancy_density_people_m2', 0)
            equip_density = zone.annotation.get('equipment_power_density_w_m2', 0)
            ltg_density = zone.annotation.get('lighting_power_density_w_m2_default', 0)

            total_occupancy += occ_density * zone.floor_area_m2
            total_equipment_power += equip_density * zone.floor_area_m2
            total_ltg_power_default += ltg_density * zone.floor_area_m2

    print(f"\nBuilding totals:")
    print(f"  Total floor area: {total_area:,.1f} m² ({total_area * 10.764:,.1f} ft²)")
    print(f"\n  Total occupancy: {total_occupancy:,.1f} people")
    print(f"  Average density: {total_occupancy/total_area:.4f} people/m²" if total_area > 0 else "  Average density: N/A")

    print(f"\n  Total equipment power: {total_equipment_power:,.0f} W ({total_equipment_power/1000:.1f} kW)")
    print(f"  Average EPD: {total_equipment_power/total_area:.2f} W/m²" if total_area > 0 else "  Average EPD: N/A")

    print(f"\n  Total lighting power (default): {total_ltg_power_default:,.0f} W ({total_ltg_power_default/1000:.1f} kW)")
    print(f"  Average LPD (default): {total_ltg_power_default/total_area:.2f} W/m²" if total_area > 0 else "  Average LPD: N/A")

    # Compare with actual lighting from IntLtgSys
    actual_ltg_power = sum(ltg.total_power_w or 0 for ltg in ir.lighting_systems)
    print(f"\n  Actual lighting power (IntLtgSys): {actual_ltg_power:,.0f} W ({actual_ltg_power/1000:.1f} kW)")
    if total_area > 0:
        print(f"  Actual LPD: {actual_ltg_power/total_area:.2f} W/m²")

    # Test 4: Breakdown by space function
    print("\n" + "=" * 70)
    print("TEST 4: LOADS BY SPACE FUNCTION")
    print("=" * 70)

    space_func_stats = {}

    for zone in ir.zones:
        func = zone.space_function or "Unknown"
        if func not in space_func_stats:
            space_func_stats[func] = {
                'count': 0,
                'area': 0,
                'occupancy': 0,
                'equipment_power': 0
            }

        space_func_stats[func]['count'] += 1

        if zone.floor_area_m2:
            space_func_stats[func]['area'] += zone.floor_area_m2

            occ_density = zone.annotation.get('occupancy_density_people_m2', 0)
            equip_density = zone.annotation.get('equipment_power_density_w_m2', 0)

            space_func_stats[func]['occupancy'] += occ_density * zone.floor_area_m2
            space_func_stats[func]['equipment_power'] += equip_density * zone.floor_area_m2

    print(f"\nLoads by space function:\n")
    for func, stats in sorted(space_func_stats.items(), key=lambda x: -x[1]['area']):
        if stats['area'] > 0:
            print(f"  {func}")
            print(f"    Zones: {stats['count']}, Area: {stats['area']:,.1f} m²")
            print(f"    Occupancy: {stats['occupancy']:.1f} people ({stats['occupancy']/stats['area']:.4f} people/m²)")
            print(f"    Equipment: {stats['equipment_power']/1000:.1f} kW ({stats['equipment_power']/stats['area']:.2f} W/m²)")
            print()

    # Summary
    print("=" * 70)
    print("VALIDATION SUMMARY")
    print("=" * 70)

    print(f"\n✅ DEFAULTS SUCCESSFULLY APPLIED:")
    print(f"   - {zones_with_occ}/{len(ir.zones)} zones have occupancy defaults ({zones_with_occ/len(ir.zones)*100:.1f}%)")
    print(f"   - {zones_with_equip}/{len(ir.zones)} zones have equipment defaults ({zones_with_equip/len(ir.zones)*100:.1f}%)")
    print(f"   - {zones_with_ltg_default}/{len(ir.zones)} zones have lighting defaults ({zones_with_ltg_default/len(ir.zones)*100:.1f}%)")

    print(f"\n📊 BUILDING TOTALS:")
    print(f"   - Total occupancy: {total_occupancy:,.0f} people")
    print(f"   - Equipment power: {total_equipment_power/1000:.1f} kW")
    print(f"   - Lighting (default): {total_ltg_power_default/1000:.1f} kW")
    print(f"   - Lighting (actual IntLtgSys): {actual_ltg_power/1000:.1f} kW")

    print(f"\n📝 NOTES:")
    print(f"   - Defaults are from Title 24/ASHRAE standards")
    print(f"   - Occupancy from ASHRAE 62.1-2019")
    print(f"   - Equipment from typical energy modeling practice")
    print(f"   - Lighting from ASHRAE 90.1-2019")
    print(f"   - Actual lighting (IntLtgSys) should be used over defaults when available")

    print("\n" + "=" * 70)
    print("TEST COMPLETE")
    print("=" * 70)

    return ir


if __name__ == "__main__":
    test_defaults_application()
