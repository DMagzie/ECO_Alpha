"""
Test Internal Loads Extraction from CBECC SDDXML
Tests Session 3 - Priority 3: Internal Loads
"""

from eco_tools.formats.cibd22x_adapter import CIBD22XAdapter


def test_internal_loads():
    """Test internal loads extraction from CBECC file"""

    test_file = '/Users/DavidM/Documents/ECO_Alpha/Test Projects/Gibraltar_CLEAN_START.cibd22x'

    print("=" * 70)
    print("INTERNAL LOADS EXTRACTION TEST")
    print("=" * 70)
    print(f"\nTest File: {test_file}\n")

    # Import
    adapter = CIBD22XAdapter()
    ir = adapter.parse(test_file)

    # Test 1: Daylighting Control Lighting Power
    print("=" * 70)
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
        print(f"\nZones with daylighting power:")
        for name, pri, sec in zones_with_daylt_pwr:
            print(f"  {name}:")
            if pri:
                print(f"    Primary sidelit power: {pri} W")
            if sec:
                print(f"    Secondary sidelit power: {sec} W")
    else:
        print("  No zones have daylighting control power values")

    # Test 2: Internal Lighting Systems
    print("\n" + "=" * 70)
    print("TEST 2: INTERNAL LIGHTING SYSTEMS")
    print("=" * 70)

    print(f"\nTotal lighting systems: {len(ir.lighting_systems)}")
    print(f"Total luminaires: {len(ir.luminaires)}")

    if ir.lighting_systems:
        print(f"\nLighting Systems Details:")
        for i, ltg_sys in enumerate(ir.lighting_systems):
            print(f"\n  #{i+1}: {ltg_sys.name}")
            print(f"    ID: {ltg_sys.id}")
            print(f"    Space ref: {ltg_sys.space_ref or 'None'}")
            print(f"    Power density: {ltg_sys.power_density_w_m2} W/m²" if ltg_sys.power_density_w_m2 else "    Power density: None")
            print(f"    Total power: {ltg_sys.total_power_w} W" if ltg_sys.total_power_w else "    Total power: None")
            print(f"    Luminaire refs: {', '.join(ltg_sys.luminaire_refs)}" if ltg_sys.luminaire_refs else "    Luminaire refs: None")

            # Check annotation for CBECC-specific data
            lum_count = ltg_sys.annotation.get('luminaire_count')
            daylit_type = ltg_sys.annotation.get('daylighting_area_type')
            calculated = ltg_sys.annotation.get('calculated_from_luminaires', False)

            if lum_count:
                print(f"    Luminaire count: {lum_count}")
            if daylit_type:
                print(f"    Daylighting area type: {daylit_type}")
            if calculated:
                lum_pwr = ltg_sys.annotation.get('luminaire_power_w')
                print(f"    ✓ Power calculated from luminaires ({lum_pwr} W × {lum_count})")

    # Test 3: Luminaire Definitions
    print("\n" + "=" * 70)
    print("TEST 3: LUMINAIRE DEFINITIONS")
    print("=" * 70)

    if ir.luminaires:
        print(f"\nLuminaire Details:")
        for i, lum in enumerate(ir.luminaires):
            print(f"\n  #{i+1}: {lum.name}")
            print(f"    ID: {lum.id}")
            print(f"    Type: {lum.luminaire_type}")
            print(f"    Power: {lum.power_w} W" if lum.power_w else "    Power: None")
            print(f"    Count: {lum.count}" if lum.count else "    Count: None")
            print(f"    Efficiency: {lum.efficiency}" if lum.efficiency else "    Efficiency: None")

    # Test 4: Calculate Total Lighting Energy
    print("\n" + "=" * 70)
    print("TEST 4: TOTAL LIGHTING ENERGY")
    print("=" * 70)

    total_ltg_power = 0
    systems_with_power = 0

    for ltg_sys in ir.lighting_systems:
        if ltg_sys.total_power_w:
            total_ltg_power += ltg_sys.total_power_w
            systems_with_power += 1

    print(f"\nSystems with power: {systems_with_power}/{len(ir.lighting_systems)}")
    print(f"Total lighting power: {total_ltg_power:,.0f} W ({total_ltg_power/1000:.1f} kW)")

    # Calculate average LPD if we have zone area data
    zones_with_area = [z for z in ir.zones if z.floor_area_m2]
    total_floor_area = sum(z.floor_area_m2 for z in zones_with_area)

    if total_floor_area > 0 and total_ltg_power > 0:
        avg_lpd = total_ltg_power / total_floor_area
        print(f"Total floor area: {total_floor_area:.1f} m²")
        print(f"Average lighting power density: {avg_lpd:.2f} W/m²")

    # Test 5: Occupancy and Equipment Loads
    print("\n" + "=" * 70)
    print("TEST 5: OCCUPANCY & EQUIPMENT LOADS")
    print("=" * 70)

    print(f"\nSearching zone annotations for occupancy/equipment data...")

    occ_props = ['occupancy_density', 'people_density', 'OccDens']
    equip_props = ['equipment_power_density', 'EquipPwrDens', 'receptacle_power_density']

    zones_with_occ = []
    zones_with_equip = []

    for zone in ir.zones:
        for prop in occ_props:
            if prop in zone.annotation:
                zones_with_occ.append((zone.name, prop, zone.annotation[prop]))
                break

        for prop in equip_props:
            if prop in zone.annotation:
                zones_with_equip.append((zone.name, prop, zone.annotation[prop]))
                break

    print(f"\n  Zones with occupancy data: {len(zones_with_occ)}/{len(ir.zones)}")
    if zones_with_occ:
        for name, prop, value in zones_with_occ[:5]:
            print(f"    {name}: {prop} = {value}")

    print(f"\n  Zones with equipment data: {len(zones_with_equip)}/{len(ir.zones)}")
    if zones_with_equip:
        for name, prop, value in zones_with_equip[:5]:
            print(f"    {name}: {prop} = {value}")

    if not zones_with_occ:
        print("  ❌ No occupancy density data found in zones")
    if not zones_with_equip:
        print("  ❌ No equipment power density data found in zones")

    # Summary
    print("\n" + "=" * 70)
    print("INTERNAL LOADS EXTRACTION SUMMARY")
    print("=" * 70)

    print(f"\n✅ SUCCESSFULLY EXTRACTED:")
    print(f"   - Daylighting control power: {len(zones_with_daylt_pwr)} zones")
    print(f"   - Internal lighting systems: {len(ir.lighting_systems)} systems")
    print(f"   - Luminaire definitions: {len(ir.luminaires)} luminaires")
    print(f"   - Calculated lighting power: {systems_with_power}/{len(ir.lighting_systems)} systems ({total_ltg_power/1000:.1f} kW total)")

    print(f"\n❌ NOT AVAILABLE IN CBECC SDDXML:")
    print(f"   - Occupancy density (people/m² or people/ft²)")
    print(f"   - Equipment power density (W/m² or W/ft²)")
    print(f"   - Process load density")

    print(f"\n📝 NOTES:")
    print(f"   - CBECC uses 'SpcFuncDefaultsRef' to reference space function defaults")
    print(f"   - Internal loads are implied by space function, not explicit in XML")
    print(f"   - Lighting power can be calculated from IntLtgSys + Lum references")
    print(f"   - For simulation, will need to apply defaults based on space function")

    print("\n" + "=" * 70)
    print("TEST COMPLETE")
    print("=" * 70)

    return ir


if __name__ == "__main__":
    test_internal_loads()
