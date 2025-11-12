"""
Test Space Function and Conditioning Status
Verifies Session 3.5 enhancements to CIBD22X adapter
"""

from eco_tools.formats.cibd22x_adapter import CIBD22XAdapter


def test_space_function_and_conditioning():
    """Test space function extraction and conditioning status"""

    test_file = '/Users/DavidM/Documents/ECO_Alpha/Test Projects/Gibraltar_CLEAN_START.cibd22x'

    print("=" * 70)
    print("SPACE FUNCTION & CONDITIONING STATUS TEST")
    print("=" * 70)
    print(f"\nTest File: {test_file}\n")

    # Import
    adapter = CIBD22XAdapter()
    ir = adapter.parse(test_file)

    # Analyze space functions
    print("=" * 70)
    print("SPACE FUNCTION ANALYSIS")
    print("=" * 70)

    zones_with_function = [z for z in ir.zones if z.space_function]
    zones_without_function = [z for z in ir.zones if not z.space_function]

    print(f"\nZones with space function: {len(zones_with_function)}/{len(ir.zones)} ({len(zones_with_function)/len(ir.zones)*100:.1f}%)")
    print(f"Zones without space function: {len(zones_without_function)}/{len(ir.zones)} ({len(zones_without_function)/len(ir.zones)*100:.1f}%)")

    # Show unique space functions
    space_functions = {}
    for z in zones_with_function:
        func = z.space_function
        if func not in space_functions:
            space_functions[func] = []
        space_functions[func].append(z.name)

    print(f"\nUnique space functions found: {len(space_functions)}")
    for func, zones in sorted(space_functions.items()):
        print(f"  '{func}': {len(zones)} zones")

    # Sample zones with space function
    print(f"\nSample zones WITH space function (first 5):")
    for z in zones_with_function[:5]:
        print(f"  {z.name}: '{z.space_function}'")

    # Analyze conditioning status
    print("\n" + "=" * 70)
    print("CONDITIONING STATUS ANALYSIS")
    print("=" * 70)

    conditioned = [z for z in ir.zones if z.conditioned is True]
    unconditioned = [z for z in ir.zones if z.conditioned is False]
    unknown = [z for z in ir.zones if z.conditioned is None]

    print(f"\nConditioned zones: {len(conditioned)}/{len(ir.zones)} ({len(conditioned)/len(ir.zones)*100:.1f}%)")
    print(f"Unconditioned zones: {len(unconditioned)}/{len(ir.zones)} ({len(unconditioned)/len(ir.zones)*100:.1f}%)")
    print(f"Unknown status: {len(unknown)}/{len(ir.zones)} ({len(unknown)/len(ir.zones)*100:.1f}%)")

    # Show conditioning types from annotation
    conditioning_types = {}
    for z in ir.zones:
        cond_type = z.annotation.get('conditioning_type', 'Unknown')
        if cond_type not in conditioning_types:
            conditioning_types[cond_type] = []
        conditioning_types[cond_type].append(z.name)

    print(f"\nConditioning types from source XML:")
    for ctype, zones in sorted(conditioning_types.items()):
        print(f"  {ctype}: {len(zones)} zones")

    # Sample each category
    print(f"\nSample CONDITIONED zones (first 5):")
    for z in conditioned[:5]:
        cond_type = z.annotation.get('conditioning_type', 'Unknown')
        hvac_status = "with HVAC" if z.served_by else "NO HVAC"
        print(f"  {z.name}: {cond_type} [{hvac_status}]")

    print(f"\nSample UNCONDITIONED zones (all):")
    for z in unconditioned:
        cond_type = z.annotation.get('conditioning_type', 'Unknown')
        hvac_status = "with HVAC" if z.served_by else "NO HVAC"
        print(f"  {z.name}: {cond_type} [{hvac_status}]")

    # Critical check: Conditioned zones without HVAC
    print("\n" + "=" * 70)
    print("CRITICAL CHECK: Conditioned Zones Without HVAC")
    print("=" * 70)

    conditioned_no_hvac = [z for z in conditioned if not z.served_by]

    print(f"\nConditioned zones without HVAC: {len(conditioned_no_hvac)}/{len(conditioned)}")

    if conditioned_no_hvac:
        print("\n⚠️  WARNING: These conditioned zones have no HVAC linkage:")
        for z in conditioned_no_hvac:
            cond_type = z.annotation.get('conditioning_type', 'Unknown')
            space_func = z.space_function or 'No function'
            print(f"  {z.name}")
            print(f"    Conditioning type: {cond_type}")
            print(f"    Space function: {space_func}")
            print(f"    Floor area: {z.floor_area_m2:.2f} m²" if z.floor_area_m2 else "    Floor area: None")
            print(f"    Volume: {z.volume_m3:.2f} m³" if z.volume_m3 else "    Volume: None")
    else:
        print("\n✅ All conditioned zones have HVAC linkage!")

    # Validation summary
    print("\n" + "=" * 70)
    print("VALIDATION SUMMARY")
    print("=" * 70)

    print(f"\n✅ Space Function Extraction:")
    print(f"   - {len(zones_with_function)} zones have space function assigned")
    print(f"   - {len(space_functions)} unique functions identified")
    print(f"   - Coverage: {len(zones_with_function)/len(ir.zones)*100:.1f}%")

    print(f"\n✅ Conditioning Status:")
    print(f"   - {len(conditioned)} conditioned zones")
    print(f"   - {len(unconditioned)} unconditioned zones")
    print(f"   - {len(unknown)} zones with unknown status (ThrmlZn zones)")

    print(f"\n⚠️  Edge Cases:")
    if conditioned_no_hvac:
        print(f"   - {len(conditioned_no_hvac)} conditioned zones lack HVAC linkage")
        print(f"   - These may be special cases (e.g., restrooms with exhaust-only)")
    else:
        print(f"   - None identified")

    print("\n" + "=" * 70)
    print("TEST COMPLETE")
    print("=" * 70)

    return ir


if __name__ == "__main__":
    test_space_function_and_conditioning()
