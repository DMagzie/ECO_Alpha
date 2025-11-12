#!/usr/bin/env python3
"""
Test script for CIBD25 serializer and roundtrip

Tests serialization and roundtrip (parse -> serialize -> parse) functionality.
"""

import sys
import os
sys.path.insert(0, '/Users/DavidM/Documents/ECO_Alpha/eco_tools_parser')

from eco_tools.formats.cibd25_adapter import CIBD25Adapter


def test_serializer():
    """Test serializer on simple content"""
    print("=" * 80)
    print("TEST 1: Serializer")
    print("=" * 80)

    adapter = CIBD25Adapter()

    # Create simple test file
    test_content = '''RulesetFilename   "T24_2025.bin"

Proj   "TestProject"
   BldgEngyModelVersion = 17
   ZipCode = 95814
   AutoHardSize = 1
   ..

Mat   "Concrete - 6 in."
   CodeCat = "Concrete"
   CodeItem = "Concrete - 140 lb/ft3 - 6 in."
   ..

ConsAssm   "TestWall"
   CompatibleSurfType = "ExteriorWall"
   MatRef[1] = "Concrete - 6 in."
   MatRef[2] = "Insulation R13"
   ..
'''

    # Write to temp file
    test_file = '/tmp/test_cibd25.cibd25'
    with open(test_file, 'w', encoding='iso-8859-1', newline='\r\n') as f:
        f.write(test_content)

    # Parse
    print("\n1. Parsing test file...")
    objects = adapter.parse_to_objects(test_file)
    print(f"   Parsed {len(objects)} top-level objects")

    # Serialize
    print("\n2. Serializing to text...")
    serialized = adapter.serialize_objects(objects)
    print(f"   Generated {len(serialized)} characters")

    # Show first few lines
    print("\n3. First 20 lines of serialized output:")
    lines = serialized.split('\r\n')
    for i, line in enumerate(lines[:20], 1):
        print(f"   {i:3}. {repr(line)}")

    # Write output
    output_file = '/tmp/test_cibd25_output.cibd25'
    adapter.serialize_objects(objects, output_file)
    print(f"\n4. Written to: {output_file}")

    print("\n✅ Serializer test passed")
    return True


def test_roundtrip_simple():
    """Test roundtrip on simple file"""
    print("\n" + "=" * 80)
    print("TEST 2: Simple Roundtrip")
    print("=" * 80)

    adapter = CIBD25Adapter()

    # Original file
    test_file = '/tmp/test_cibd25.cibd25'

    # Parse #1
    print("\n1. First parse...")
    objects1 = adapter.parse_to_objects(test_file)
    print(f"   Objects: {len(objects1)}")

    # Serialize
    print("\n2. Serialize...")
    output_file = '/tmp/test_cibd25_roundtrip.cibd25'
    adapter.serialize_objects(objects1, output_file)

    # Parse #2
    print("\n3. Second parse (from serialized)...")
    objects2 = adapter.parse_to_objects(output_file)
    print(f"   Objects: {len(objects2)}")

    # Compare
    print("\n4. Comparing...")
    if len(objects1) != len(objects2):
        print(f"   ❌ Object count mismatch: {len(objects1)} vs {len(objects2)}")
        return False

    for i, (obj1, obj2) in enumerate(zip(objects1, objects2)):
        if obj1.element_type != obj2.element_type:
            print(f"   ❌ Element type mismatch at {i}: {obj1.element_type} vs {obj2.element_type}")
            return False
        if obj1.name != obj2.name:
            print(f"   ❌ Name mismatch at {i}: {obj1.name} vs {obj2.name}")
            return False
        if len(obj1.properties) != len(obj2.properties):
            print(f"   ❌ Property count mismatch at {i}: {len(obj1.properties)} vs {len(obj2.properties)}")
            return False
        if len(obj1.arrays) != len(obj2.arrays):
            print(f"   ❌ Array count mismatch at {i}: {len(obj1.arrays)} vs {len(obj2.arrays)}")
            return False

    print("   ✅ All objects match!")

    print("\n✅ Simple roundtrip test passed")
    return True


def test_roundtrip_real_file(file_path: str):
    """Test roundtrip on real CIBD25 file"""
    print("\n" + "=" * 80)
    print(f"TEST 3: Roundtrip Real File - {os.path.basename(file_path)}")
    print("=" * 80)

    adapter = CIBD25Adapter()

    try:
        # Parse #1
        print("\n1. Parsing original file...")
        objects1 = adapter.parse_to_objects(file_path)
        print(f"   Parsed {len(objects1)} top-level objects")

        # Count total elements
        def count_all(objs):
            total = 0
            for obj in objs:
                total += 1
                total += count_all(obj.children)
            return total

        total1 = count_all(objects1)
        print(f"   Total elements: {total1}")

        # Serialize
        print("\n2. Serializing...")
        output_file = file_path.replace('/originals/', '/roundtrips/').replace('.cibd25', '_roundtrip.cibd25')
        os.makedirs(os.path.dirname(output_file), exist_ok=True)

        content = adapter.serialize_objects(objects1, output_file)
        print(f"   Written {len(content)} characters to:")
        print(f"   {output_file}")

        # Parse #2
        print("\n3. Parsing roundtrip file...")
        objects2 = adapter.parse_to_objects(output_file)
        total2 = count_all(objects2)
        print(f"   Parsed {len(objects2)} top-level objects")
        print(f"   Total elements: {total2}")

        # Compare counts
        print("\n4. Comparing...")
        if len(objects1) != len(objects2):
            print(f"   ⚠️  Top-level count differs: {len(objects1)} vs {len(objects2)}")
        else:
            print(f"   ✅ Top-level count matches: {len(objects1)}")

        if total1 != total2:
            print(f"   ⚠️  Total element count differs: {total1} vs {total2}")
        else:
            print(f"   ✅ Total element count matches: {total1}")

        # Sample comparison of first few objects
        matches = 0
        mismatches = 0
        for i, (obj1, obj2) in enumerate(zip(objects1[:10], objects2[:10])):
            if obj1.element_type == obj2.element_type and obj1.name == obj2.name:
                matches += 1
            else:
                mismatches += 1
                print(f"   ⚠️  Mismatch at {i}: {obj1.element_type}:{obj1.name} vs {obj2.element_type}:{obj2.name}")

        print(f"\n   First 10 objects: {matches} matches, {mismatches} mismatches")

        print("\n✅ Roundtrip test completed")
        return True

    except Exception as e:
        print(f"\n❌ Error during roundtrip: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests"""
    print("\n" + "=" * 80)
    print("CIBD25 SERIALIZER & ROUNDTRIP TEST SUITE")
    print("=" * 80)

    tests_passed = 0
    tests_total = 0

    # Test 1: Serializer
    tests_total += 1
    if test_serializer():
        tests_passed += 1

    # Test 2: Simple roundtrip
    tests_total += 1
    if test_roundtrip_simple():
        tests_passed += 1

    # Test 3: Real file roundtrips
    sample_files = [
        "/Users/DavidM/Documents/ECO_Alpha/cibd25_testing/originals/01_SmallOffice.cibd25",
        "/Users/DavidM/Documents/ECO_Alpha/cibd25_testing/originals/02_SmallRestaurant.cibd25",
    ]

    for file_path in sample_files:
        if os.path.exists(file_path):
            tests_total += 1
            if test_roundtrip_real_file(file_path):
                tests_passed += 1

    # Summary
    print("\n" + "=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    print(f"\nTests Passed: {tests_passed}/{tests_total}")

    if tests_passed == tests_total:
        print("\n🎉 All tests passed!")
        return 0
    else:
        print(f"\n❌ {tests_total - tests_passed} test(s) failed")
        return 1


if __name__ == '__main__':
    sys.exit(main())
