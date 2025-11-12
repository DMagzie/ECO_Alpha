"""
Test Internal Loads Extraction with Official CBECC Sample
Uses Title 24 Standard Model Test: 080012-Whse-CECStd.cibd22x
"""

from eco_tools.formats.cibd22x_adapter import CIBD22XAdapter


def test_cbecc_sample():
    """Test internal loads with official CBECC warehouse sample"""

    test_file = '/Users/DavidM/Documents/ECO_Alpha/reference_data/cbecc/CBECC Models/cibd22x/080012-Whse-CECStd.cibd22x'

    print("=" * 70)
    print("CBECC OFFICIAL SAMPLE - INTERNAL LOADS TEST")
    print("=" * 70)
    print(f"\nTest File: 080012-Whse-CECStd.cibd22x")
    print(f"Source: Title 24 Standard Model Tests")
    print(f"Building Type: Warehouse\n")

    # Import
    adapter = CIBD22XAdapter()
    try:
        ir = adapter.parse(test_file)
        print("✅ Import successful!\n")
    except Exception as e:
        print(f"❌ Import failed: {e}")
        import traceback
        traceback.print_exc()
        return

    # Summary
    print("=" * 70)
    print("IMPORT SUMMARY")
    print("=" * 70)
    print(f"\n📐 GEOMETRY:")
    print(f"  Zones: {len(ir.zones)}")
    print(f"  Surfaces: {len(ir.surfaces)}")
    print(f"  Openings: {len(ir.openings)}")

    print(f"\n🔧 SYSTEMS:")
    print(f"  HVAC Systems: {len(ir.hvac_systems)}")
    print(f"  Lighting Systems: {len(ir.lighting_systems)}")
    print(f"  Luminaires: {len(ir.luminaires)}")

    # Test 1: Daylighting Control Power
    print("\n" + "=" * 70)
    print("TEST 1: DAYLIGHTING CONTROL LIGHTING POWER")
    print("=" * 70)

    zones_with_daylt_pwr = []
    for zone in ir.zones:
        pri_pwr = zone.annotation.get('primary_sidelit_lighting_power_w')
        sec_pwr = zone.annotation.get('secondary_sidelit_lighting_power_w')
        if pri_pwr or sec_pwr:
            zones_with_daylt_pwr.append((zone.name, pri_pwr, sec_pwr))

    print(f"\nZones with daylighting control power: {len(zones_with_daylt_pwr)}/{len(ir.zones)}")
    if zones_with_daylt_pwr:
        for name, pri, sec in zones_with_daylt_pwr:
            print(f"  {name}:")
            if pri:
                print(f"    Primary sidelit: {pri} W")
            if sec:
                print(f"    Secondary sidelit: {sec} W")

    # Test 2: Lighting Systems
    print("\n" + "=" * 70)
    print("TEST 2: INTERNAL LIGHTING SYSTEMS")
    print("=" * 70)

    print(f"\nTotal lighting systems: {len(ir.lighting_systems)}")
    print(f"Total luminaires: {len(ir.luminaires)}")

    systems_with_power = 0
    total_ltg_power = 0

    if ir.lighting_systems:
        print(f"\nLighting Systems Detail:")
        for ltg_sys in ir.lighting_systems:
            print(f"\n  {ltg_sys.name}")
            print(f"    Total power: {ltg_sys.total_power_w} W" if ltg_sys.total_power_w else "    Total power: None")

            lum_count = ltg_sys.annotation.get('luminaire_count')
            daylit_type = ltg_sys.annotation.get('daylighting_area_type')
            calculated = ltg_sys.annotation.get('calculated_from_luminaires', False)

            if lum_count:
                print(f"    Luminaire count: {lum_count}")
            if daylit_type:
                print(f"    Daylit area: {daylit_type}")
            if calculated:
                lum_pwr = ltg_sys.annotation.get('luminaire_power_w')
                print(f"    ✓ Calculated: {lum_pwr} W × {lum_count}")

            if ltg_sys.total_power_w:
                total_ltg_power += ltg_sys.total_power_w
                systems_with_power += 1

    # Test 3: Luminaires
    print("\n" + "=" * 70)
    print("TEST 3: LUMINAIRE DEFINITIONS")
    print("=" * 70)

    if ir.luminaires:
        print(f"\nLuminaire Details:")
        for lum in ir.luminaires:
            print(f"\n  {lum.name}")
            print(f"    Power: {lum.power_w} W" if lum.power_w else "    Power: None")
            print(f"    Type: {lum.luminaire_type}")

    # Test 4: Total Lighting Energy
    print("\n" + "=" * 70)
    print("TEST 4: LIGHTING ENERGY SUMMARY")
    print("=" * 70)

    print(f"\nSystems with power: {systems_with_power}/{len(ir.lighting_systems)}")
    print(f"Total lighting power: {total_ltg_power:,.0f} W ({total_ltg_power/1000:.1f} kW)")

    zones_with_area = [z for z in ir.zones if z.floor_area_m2]
    total_floor_area = sum(z.floor_area_m2 for z in zones_with_area)

    if total_floor_area > 0 and total_ltg_power > 0:
        avg_lpd = total_ltg_power / total_floor_area
        print(f"Total floor area: {total_floor_area:.1f} m²")
        print(f"Average LPD: {avg_lpd:.2f} W/m²")
        print(f"Average LPD: {avg_lpd * 0.092903:.2f} W/ft²")

    # Test 5: Space Functions
    print("\n" + "=" * 70)
    print("TEST 5: SPACE FUNCTIONS")
    print("=" * 70)

    space_functions = {}
    for zone in ir.zones:
        func = zone.space_function
        if func:
            if func not in space_functions:
                space_functions[func] = []
            space_functions[func].append(zone.name)

    print(f"\nUnique space functions: {len(space_functions)}")
    for func, zones in sorted(space_functions.items()):
        print(f"  '{func}': {len(zones)} zones")

    # Test 6: Check for explicit internal loads
    print("\n" + "=" * 70)
    print("TEST 6: EXPLICIT INTERNAL LOADS")
    print("=" * 70)

    print(f"\nSearching for explicit occupancy/equipment densities...")

    zones_with_occ = []
    zones_with_equip = []

    for zone in ir.zones:
        # Check all annotation keys for load-related data
        for key, value in zone.annotation.items():
            if any(kw in key.lower() for kw in ['occ', 'people', 'density']):
                if 'lighting' not in key.lower():  # Exclude lighting density
                    zones_with_occ.append((zone.name, key, value))
                    break
            if any(kw in key.lower() for kw in ['equip', 'receptacle', 'process']):
                zones_with_equip.append((zone.name, key, value))
                break

    print(f"\n  Zones with occupancy data: {len(zones_with_occ)}/{len(ir.zones)}")
    if zones_with_occ:
        for name, key, value in zones_with_occ[:5]:
            print(f"    {name}: {key} = {value}")
    else:
        print(f"    ❌ No explicit occupancy density found")

    print(f"\n  Zones with equipment data: {len(zones_with_equip)}/{len(ir.zones)}")
    if zones_with_equip:
        for name, key, value in zones_with_equip[:5]:
            print(f"    {name}: {key} = {value}")
    else:
        print(f"    ❌ No explicit equipment density found")

    # Summary
    print("\n" + "=" * 70)
    print("VALIDATION SUMMARY")
    print("=" * 70)

    print(f"\n✅ EXTRACTED FROM CBECC SDDXML:")
    print(f"   - Lighting power: {total_ltg_power/1000:.1f} kW")
    if total_floor_area > 0:
        print(f"   - Average LPD: {avg_lpd:.2f} W/m² ({avg_lpd * 0.092903:.2f} W/ft²)")
    print(f"   - Daylighting zones: {len(zones_with_daylt_pwr)}")
    print(f"   - Space functions: {len(space_functions)} unique")

    print(f"\n❌ NOT IN CBECC SDDXML:")
    print(f"   - Occupancy density (implied by space function)")
    print(f"   - Equipment density (implied by space function)")

    print(f"\n📋 SPACE FUNCTION APPROACH:")
    print(f"   - CBECC references space function defaults")
    print(f"   - Internal loads must be derived from space function")
    print(f"   - Title 24 standards define defaults per space type")

    print("\n" + "=" * 70)
    print("TEST COMPLETE")
    print("=" * 70)

    return ir


if __name__ == "__main__":
    test_cbecc_sample()
