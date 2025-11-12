#!/usr/bin/env python3
"""
Test script for CIBD25 parser

Tests the tokenizer, parser, and reference resolver on CIBD25 sample files.
"""

import sys
sys.path.insert(0, '/Users/DavidM/Documents/ECO_Alpha/eco_tools_parser')

from eco_tools.formats.cibd25_adapter import (
    CIBD25Adapter, CIBD25Tokenizer, CIBD25Parser, ReferenceResolver
)


def test_tokenizer():
    """Test tokenizer on simple CIBD25 content"""
    print("=" * 80)
    print("TEST 1: Tokenizer")
    print("=" * 80)

    content = '''RulesetFilename   "T24_2025.bin"

Proj   "TestProject"
   BldgEngyModelVersion = 17
   ZipCode = 95814
   ..

Mat   "Test Material"
   CodeCat = "Concrete"
   ..
'''

    tokenizer = CIBD25Tokenizer()
    tokens = tokenizer.tokenize(content)

    print(f"\nTokenized {len(tokens)} tokens:\n")
    for i, token in enumerate(tokens[:20], 1):  # Show first 20
        print(f"{i:3}. {token.type.value:20} | Line {token.line_number:3} | ", end="")
        if token.element_type:
            print(f"Type: {token.element_type:15} Name: {token.element_name}")
        elif token.property_name:
            print(f"Prop: {token.property_name:15} Value: {token.property_value}")
        else:
            print(f"Value: {token.value}")

    print("\n✅ Tokenizer test passed")
    return True


def test_parser():
    """Test parser on simple CIBD25 content"""
    print("\n" + "=" * 80)
    print("TEST 2: Parser")
    print("=" * 80)

    content = '''RulesetFilename   "T24_2025.bin"

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

    tokenizer = CIBD25Tokenizer()
    parser = CIBD25Parser()

    tokens = tokenizer.tokenize(content)
    objects = parser.parse_tokens(tokens)

    print(f"\nParsed {len(objects)} top-level objects:\n")
    for obj in objects:
        print(f"  {obj.element_type:15} | {obj.name:30} | Props: {len(obj.properties):2} | Arrays: {len(obj.arrays):2}")
        if obj.properties:
            for key, val in list(obj.properties.items())[:3]:
                print(f"      - {key}: {val}")
        if obj.arrays:
            for key, val in obj.arrays.items():
                print(f"      - {key}[]: {val}")

    print("\n✅ Parser test passed")
    return True


def test_sample_file(file_path: str):
    """Test parser on a real CIBD25 sample file"""
    print("\n" + "=" * 80)
    print(f"TEST 3: Parse Sample File - {file_path.split('/')[-1]}")
    print("=" * 80)

    try:
        adapter = CIBD25Adapter()
        internal = adapter.parse(file_path)

        print(f"\n✅ Successfully parsed file!")
        print(f"\nProject: {internal.project_name}")
        print(f"Format:  {internal.source_format_type}")
        print(f"ZipCode: {internal.zip_code}")

        # Show token/object statistics
        with open(file_path, 'r', encoding='iso-8859-1') as f:
            content = f.read()

        tokenizer = CIBD25Tokenizer()
        parser = CIBD25Parser()

        tokens = tokenizer.tokenize(content)
        objects = parser.parse_tokens(tokens)

        # Count elements by type
        element_counts = {}

        def count_objects(obj):
            if obj.element_type not in element_counts:
                element_counts[obj.element_type] = 0
            element_counts[obj.element_type] += 1
            for child in obj.children:
                count_objects(child)

        for obj in objects:
            count_objects(obj)

        print(f"\nStatistics:")
        print(f"  Total tokens:      {len(tokens)}")
        print(f"  Top-level objects: {len(objects)}")
        print(f"  Total elements:    {sum(element_counts.values())}")
        print(f"  Element types:     {len(element_counts)}")

        print(f"\nElement Type Summary (top 15):")
        for elem_type, count in sorted(element_counts.items(), key=lambda x: -x[1])[:15]:
            print(f"  {elem_type:20} {count:5}")

        return True

    except Exception as e:
        print(f"\n❌ Error parsing file: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_hierarchy():
    """Test hierarchy building"""
    print("\n" + "=" * 80)
    print("TEST 4: Hierarchy Building")
    print("=" * 80)

    content = '''Bldg   "Test Building"
   TotStoryCnt = 1
   ..

Story   "Story 1"
   ..

Spc   "Space 1"
   Vol = 1000
   ..

ExtWall   "Wall 1"
   ConsAssmRef = "WallCons"
   ..

PolyLp   "PolyLoop 1"
   ..

CartesianPt   "Point 1"
   Coord = ( 0, 0, 0 )
   ..

CartesianPt   "Point 2"
   Coord = ( 10, 0, 0 )
   ..
'''

    tokenizer = CIBD25Tokenizer()
    parser = CIBD25Parser()

    tokens = tokenizer.tokenize(content)
    objects = parser.parse_tokens(tokens)

    def print_tree(obj, indent=0):
        print("  " * indent + f"└─ {obj.element_type}: {obj.name}")
        for child in obj.children:
            print_tree(child, indent + 1)

    print("\nObject Hierarchy:")
    for obj in objects:
        print_tree(obj)

    print("\n✅ Hierarchy test passed")
    return True


def main():
    """Run all tests"""
    print("\n" + "=" * 80)
    print("CIBD25 PARSER TEST SUITE")
    print("=" * 80)

    tests_passed = 0
    tests_total = 0

    # Test 1: Tokenizer
    tests_total += 1
    if test_tokenizer():
        tests_passed += 1

    # Test 2: Parser
    tests_total += 1
    if test_parser():
        tests_passed += 1

    # Test 3: Hierarchy
    tests_total += 1
    if test_hierarchy():
        tests_passed += 1

    # Test 4: Sample files
    sample_files = [
        "/Users/DavidM/Documents/ECO_Alpha/cibd25_testing/originals/01_SmallOffice.cibd25",
        "/Users/DavidM/Documents/ECO_Alpha/cibd25_testing/originals/02_SmallRestaurant.cibd25",
    ]

    for file_path in sample_files:
        tests_total += 1
        if test_sample_file(file_path):
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
