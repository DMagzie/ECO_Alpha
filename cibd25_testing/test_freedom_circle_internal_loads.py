"""
Test Internal Loads with CBECC Sample: Freedom Circle Building B
Proper CBECC-created office building model
"""

from eco_tools.formats.cibd22x_adapter import CIBD22XAdapter


def test_freedom_circle():
    """Test internal loads with Freedom Circle office building"""

    test_file = '/Users/DavidM/Documents/ECO_Alpha/reference_data/cbecc/CBECC Models/cibd22x/Freedom Circle Building B - LEED.cibd22x'

    print("=" * 70)
    print("CBECC OFFICIAL SAMPLE - FREEDOM CIRCLE BUILDING B")
    print("=" * 70)
    print(f"\nTest File: Freedom Circle Building B - LEED.cibd22x")
    print(f"Source: Real CBECC project file")
    print(f"Building Type: Office Building\n")

    # Import
    adapter = CIBD22XAdapter()
    ir = adapter.parse(test_file)
    print("✅ Import successful!\n")

    # Summary
    print("=" * 70)
    print("MODEL SUMMARY")
    print("=" * 70)
    print(f"\n📐 GEOMETRY:")
    print(f"  Zones: {len(ir.zones)}")
    print(f"  Surfaces: {len(ir.surfaces)}")
    print(f"  Openings: {len(ir.openings)}")

    print(f"\n🔧 SYSTEMS:")
    print(f"  HVAC Systems: {len(ir.hvac_systems)}")
    print(f"  Lighting Systems: {len(ir.lighting_systems)}")
    print(f"  Luminaires: {len(ir.luminaires)}")

    # Lighting extraction
    print("\n" + "=" * 70)
    print("LIGHTING SYSTEMS ANALYSIS")
    print("=" * 70)

    total_ltg_power = 0
    systems_with_power = 0
    systems_calculated = 0

    for ltg_sys in ir.lighting_systems:
        if ltg_sys.total_power_w:
            total_ltg_power += ltg_sys.total_power_w
            systems_with_power += 1
            if ltg_sys.annotation.get('calculated_from_luminaires'):
                systems_calculated += 1

    print(f"\nLighting systems: {len(ir.lighting_systems)}")
    print(f"Systems with power: {systems_with_power}/{len(ir.lighting_systems)} ({systems_with_power/len(ir.lighting_systems)*100:.1f}%)")
    print(f"Power calculated from luminaires: {systems_calculated}/{systems_with_power} ({systems_calculated/systems_with_power*100:.1f}%)" if systems_with_power > 0 else "Power calculated: N/A")
    print(f"\nTotal lighting power: {total_ltg_power:,.0f} W ({total_ltg_power/1000:.1f} kW)")

    # Sample lighting systems
    print(f"\nSample Lighting Systems (first 10):")
    for ltg_sys in ir.lighting_systems[:10]:
        pwr = ltg_sys.total_power_w or 0
        lum_count = ltg_sys.annotation.get('luminaire_count', 'N/A')
        calc = " ✓" if ltg_sys.annotation.get('calculated_from_luminaires') else ""
        print(f"  {ltg_sys.name}: {pwr:,.0f} W (luminaires: {lum_count}){calc}")

    # Luminaires
    print(f"\n" + "=" * 70)
    print("LUMINAIRE DEFINITIONS")
    print("=" * 70)

    print(f"\nTotal luminaires: {len(ir.luminaires)}")
    print(f"\nSample Luminaires (first 10):")
    for lum in ir.luminaires[:10]:
        pwr = lum.power_w or 0
        print(f"  {lum.name}: {pwr:.0f} W")

    # Calculate LPD
    print(f"\n" + "=" * 70)
    print("LIGHTING POWER DENSITY")
    print("=" * 70)

    zones_with_area = [z for z in ir.zones if z.floor_area_m2]
    total_floor_area = sum(z.floor_area_m2 for z in zones_with_area)

    print(f"\nZones with area: {len(zones_with_area)}/{len(ir.zones)}")
    print(f"Total floor area: {total_floor_area:,.1f} m² ({total_floor_area * 10.764:,.1f} ft²)")

    if total_floor_area > 0 and total_ltg_power > 0:
        avg_lpd_si = total_ltg_power / total_floor_area
        avg_lpd_ip = avg_lpd_si * 0.092903
        print(f"\nAverage LPD: {avg_lpd_si:.2f} W/m²")
        print(f"Average LPD: {avg_lpd_ip:.2f} W/ft²")
        print(f"\n(ASHRAE 90.1-2022 Office LPD allowance: ~0.82-0.98 W/ft²)")

    # Daylighting control power
    print(f"\n" + "=" * 70)
    print("DAYLIGHTING CONTROL POWER")
    print("=" * 70)

    zones_with_daylt = []
    for zone in ir.zones:
        pri = zone.annotation.get('primary_sidelit_lighting_power_w')
        sec = zone.annotation.get('secondary_sidelit_lighting_power_w')
        if pri or sec:
            zones_with_daylt.append((zone.name, pri, sec))

    print(f"\nZones with daylighting control power: {len(zones_with_daylt)}/{len(ir.zones)}")
    if zones_with_daylt:
        print(f"\nSample zones (first 5):")
        for name, pri, sec in zones_with_daylt[:5]:
            print(f"  {name}:")
            if pri:
                print(f"    Primary sidelit: {pri} W")
            if sec:
                print(f"    Secondary sidelit: {sec} W")

    # Space functions
    print(f"\n" + "=" * 70)
    print("SPACE FUNCTIONS")
    print("=" * 70)

    space_funcs = {}
    for zone in ir.zones:
        func = zone.space_function
        if func:
            if func not in space_funcs:
                space_funcs[func] = 0
            space_funcs[func] += 1

    print(f"\nUnique space functions: {len(space_funcs)}")
    for func, count in sorted(space_funcs.items(), key=lambda x: -x[1]):
        print(f"  '{func}': {count} zones")

    # Check for explicit internal loads
    print(f"\n" + "=" * 70)
    print("OCCUPANCY & EQUIPMENT LOADS")
    print("=" * 70)

    print(f"\nSearching for explicit densities in zone annotations...")

    zones_with_occ = 0
    zones_with_equip = 0

    for zone in ir.zones:
        for key in zone.annotation.keys():
            if any(kw in key.lower() for kw in ['occ', 'people']) and 'lighting' not in key.lower():
                zones_with_occ += 1
                break

    for zone in ir.zones:
        for key in zone.annotation.keys():
            if any(kw in key.lower() for kw in ['equip', 'receptacle']):
                zones_with_equip += 1
                break

    print(f"\n  Zones with occupancy data: {zones_with_occ}/{len(ir.zones)}")
    print(f"  Zones with equipment data: {zones_with_equip}/{len(ir.zones)}")

    if zones_with_occ == 0:
        print(f"\n  ❌ No explicit occupancy density in CBECC XML")
    if zones_with_equip == 0:
        print(f"  ❌ No explicit equipment density in CBECC XML")

    # Final summary
    print(f"\n" + "=" * 70)
    print("VALIDATION SUMMARY - FREEDOM CIRCLE BUILDING B")
    print("=" * 70)

    print(f"\n✅ SUCCESSFULLY EXTRACTED:")
    print(f"   - {len(ir.lighting_systems)} lighting systems")
    print(f"   - {total_ltg_power/1000:.1f} kW total lighting power")
    print(f"   - {avg_lpd_ip:.2f} W/ft² average LPD" if total_floor_area > 0 else "   - LPD: N/A (no area data)")
    print(f"   - {len(ir.luminaires)} luminaire definitions")
    print(f"   - {len(zones_with_daylt)} zones with daylighting control")
    print(f"   - {len(space_funcs)} unique space functions")

    print(f"\n❌ NOT IN CBECC SDDXML:")
    print(f"   - Occupancy density (people/ft²)")
    print(f"   - Equipment power density (W/ft²)")

    print(f"\n📋 CONCLUSION:")
    print(f"   - CBECC stores lighting via IntLtgSys + Lum references ✓")
    print(f"   - Lighting power calculation successful ({systems_calculated}/{systems_with_power} systems)")
    print(f"   - Internal loads (occ/equip) implied by space function")
    print(f"   - Will need Title 24 defaults for simulation")

    print("\n" + "=" * 70)
    print("TEST COMPLETE")
    print("=" * 70)

    return ir


if __name__ == "__main__":
    test_freedom_circle()
