"""
Analyze Internal Loads Data in CBECC SDDXML
Discover what internal loads properties are available
"""

import xml.etree.ElementTree as ET
from collections import defaultdict


def analyze_internal_loads():
    """Analyze internal loads data structure in CBECC file"""

    test_file = '/Users/DavidM/Documents/ECO_Alpha/Test Projects/Gibraltar_CLEAN_START.cibd22x'

    print("=" * 70)
    print("INTERNAL LOADS XML STRUCTURE ANALYSIS")
    print("=" * 70)
    print(f"\nFile: {test_file}\n")

    tree = ET.parse(test_file)
    root = tree.getroot()

    # Analyze all Spc elements
    spc_elements = root.findall('.//Spc')
    print(f"Total Spc elements: {len(spc_elements)}\n")

    # Collect all unique child element names
    all_properties = defaultdict(int)
    load_related_properties = defaultdict(list)

    keywords = ['Dens', 'Occ', 'Ltg', 'Equip', 'People', 'Load', 'Pwr', 'Heat', 'Cool']

    for spc in spc_elements:
        spc_name = spc.find('Name')
        spc_name = spc_name.text if spc_name is not None else "Unknown"

        for child in spc:
            prop_name = child.tag
            all_properties[prop_name] += 1

            # Track load-related properties
            if any(kw in prop_name for kw in keywords):
                value = child.text if child.text else "(empty)"
                load_related_properties[prop_name].append((spc_name, value))

    # Show all unique properties found in Spc elements
    print("=" * 70)
    print("ALL PROPERTIES IN Spc ELEMENTS")
    print("=" * 70)
    print(f"\nTotal unique properties: {len(all_properties)}\n")

    for prop, count in sorted(all_properties.items(), key=lambda x: -x[1]):
        print(f"  {prop}: {count}/{len(spc_elements)} ({count/len(spc_elements)*100:.1f}%)")

    # Show load-related properties in detail
    print("\n" + "=" * 70)
    print("LOAD-RELATED PROPERTIES (Detailed)")
    print("=" * 70)

    for prop, occurrences in sorted(load_related_properties.items()):
        print(f"\n<{prop}>: Found in {len(occurrences)} spaces")
        print(f"  Sample values:")
        for space_name, value in occurrences[:5]:
            print(f"    {space_name}: {value}")

    # Check SpcFuncDefaults for internal loads data
    print("\n" + "=" * 70)
    print("SPACE FUNCTION DEFAULTS ANALYSIS")
    print("=" * 70)

    spc_func_defaults = root.findall('.//SpcFuncDefaults')
    print(f"\nTotal SpcFuncDefaults elements: {len(spc_func_defaults)}\n")

    for spc_func in spc_func_defaults:
        name_elem = spc_func.find('Name')
        name = name_elem.text if name_elem is not None else "Unknown"
        print(f"\nSpcFuncDefaults: {name}")
        print(f"  Properties:")
        for child in spc_func:
            if child.tag != 'Name':
                value = child.text if child.text else "(empty)"
                print(f"    <{child.tag}>: {value}")

    # Check for inline load properties that might not have been caught
    print("\n" + "=" * 70)
    print("COMPREHENSIVE LOAD SEARCH")
    print("=" * 70)

    # Search entire document for any elements with these exact names
    search_terms = [
        'OccDens', 'OccupancyDensity', 'PeopleDens',
        'LtgPwrDens', 'LightingPowerDensity', 'LPD',
        'EquipPwrDens', 'EquipmentPowerDensity', 'EPD',
        'RecptPwrDens', 'ProcessPwrDens', 'ProcPwrDens'
    ]

    print(f"\nSearching for: {', '.join(search_terms)}\n")

    for term in search_terms:
        elements = root.findall(f'.//{term}')
        if elements:
            print(f"✓ Found {len(elements)} <{term}> elements")
            for elem in elements[:3]:
                print(f"    Value: {elem.text if elem.text else '(empty)'}")
        else:
            print(f"✗ No <{term}> elements found")

    # Look for IntLtgSys (Internal Lighting Systems)
    print("\n" + "=" * 70)
    print("INTERNAL LIGHTING SYSTEMS")
    print("=" * 70)

    int_ltg_sys = root.findall('.//IntLtgSys')
    print(f"\nTotal IntLtgSys elements: {len(int_ltg_sys)}\n")

    for i, ltg_sys in enumerate(int_ltg_sys[:5]):
        name_elem = ltg_sys.find('Name')
        name = name_elem.text if name_elem is not None else "Unknown"
        print(f"\nIntLtgSys #{i+1}: {name}")
        for child in ltg_sys:
            if child.tag != 'Name':
                value = child.text if child.text else "(empty/child elements)"
                print(f"  <{child.tag}>: {value}")

    print("\n" + "=" * 70)
    print("ANALYSIS COMPLETE")
    print("=" * 70)


if __name__ == "__main__":
    analyze_internal_loads()
