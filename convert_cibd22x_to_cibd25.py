"""
Convert CIBD22X file to CIBD25 format

This script takes an existing CIBD22X XML file and converts it to CIBD25 by:
1. Updating SoftwareVersion to "CBECC 2025.2.0 (1390)"
2. Updating RulesetFilename to "T24_2025.bin"
3. Keeping all building data intact
"""

import sys
import xml.etree.ElementTree as ET
from pathlib import Path


def convert_cibd22x_to_cibd25(input_file: str, output_file: str):
    """
    Convert CIBD22X to CIBD25 by updating metadata.

    Args:
        input_file: Path to CIBD22X XML file
        output_file: Path for output CIBD25 XML file
    """
    print(f"Converting: {input_file}")
    print(f"Output to: {output_file}")

    # Parse the XML
    tree = ET.parse(input_file)
    root = tree.getroot()

    # Update root RulesetFilename attribute
    root.set('RulesetFilename', 'T24_2025.bin')

    # Handle XML namespace if present
    namespace = ''
    if '}' in root.tag:
        namespace = root.tag.split('}')[0] + '}'

    # Find and update Proj metadata
    proj = root.find(f".//{namespace}Proj") if namespace else root.find(".//Proj")
    if proj is None:
        print("ERROR: No Proj element found!")
        print(f"Root tag: {root.tag}")
        print(f"Namespace: '{namespace}'")
        return False

    # Update or add SoftwareVersion
    software_version_found = False
    ruleset_found = False
    model_version_found = False

    for child in proj:
        # Strip namespace from tag for comparison
        tag = child.tag.replace(namespace, '') if namespace else child.tag

        if tag == "SoftwareVersion":
            child.text = "CBECC 2025.2.0 (1390)"
            software_version_found = True
            print(f"  ✓ Updated SoftwareVersion: {child.text}")
        elif tag == "RulesetFilename":
            child.text = "T24_2025.bin"
            ruleset_found = True
            print(f"  ✓ Updated RulesetFilename: {child.text}")
        elif tag == "BldgEngyModelVersion":
            # Keep it as is (should be 17)
            model_version_found = True
            print(f"  ✓ BldgEngyModelVersion: {child.text}")

    # Add missing elements
    if not software_version_found:
        elem = ET.SubElement(proj, "SoftwareVersion")
        elem.text = "CBECC 2025.2.0 (1390)"
        print(f"  ✓ Added SoftwareVersion: {elem.text}")

    if not ruleset_found:
        elem = ET.SubElement(proj, "RulesetFilename")
        elem.text = "T24_2025.bin"
        print(f"  ✓ Added RulesetFilename: {elem.text}")

    if not model_version_found:
        elem = ET.SubElement(proj, "BldgEngyModelVersion")
        elem.text = "17"
        print(f"  ✓ Added BldgEngyModelVersion: {elem.text}")

    # Write output
    ET.indent(tree, space="  ", level=0)
    tree.write(output_file, encoding='utf-8', xml_declaration=True)
    print(f"\n✅ Conversion complete!")

    # Validate output
    verify_tree = ET.parse(output_file)
    verify_root = verify_tree.getroot()

    # Handle namespace in validation too
    verify_namespace = ''
    if '}' in verify_root.tag:
        verify_namespace = verify_root.tag.split('}')[0] + '}'

    verify_proj = verify_root.find(f".//{verify_namespace}Proj") if verify_namespace else verify_root.find(".//Proj")

    print(f"\nValidation:")
    print(f"  Root RulesetFilename: {verify_root.get('RulesetFilename')}")

    if verify_proj is not None:
        for child in verify_proj:
            tag = child.tag.replace(verify_namespace, '') if verify_namespace else child.tag
            if tag in ["SoftwareVersion", "RulesetFilename", "BldgEngyModelVersion"]:
                print(f"  {tag}: {child.text}")
    else:
        print("  ⚠️  Could not validate Proj metadata")

    return True


def main():
    if len(sys.argv) < 2:
        print("Usage: python convert_cibd22x_to_cibd25.py <input.cibd22x> [output.cibd25]")
        print("\nExample:")
        print("  python convert_cibd22x_to_cibd25.py Bressi_FINAL.cibd22x Bressi_CIBD25.cibd25")
        return 1

    input_file = sys.argv[1]
    if len(sys.argv) >= 3:
        output_file = sys.argv[2]
    else:
        # Auto-generate output filename with .cibd25 extension
        input_path = Path(input_file)
        output_file = str(input_path.parent / f"{input_path.stem}_CIBD25.cibd25")

    if not Path(input_file).exists():
        print(f"ERROR: Input file not found: {input_file}")
        return 1

    success = convert_cibd22x_to_cibd25(input_file, output_file)

    if success:
        print(f"\nYou can now open this file in CBECC 2025:")
        print(f"  open -a 'CBECC 2025' '{output_file}'")
        return 0
    else:
        return 1


if __name__ == "__main__":
    sys.exit(main())
