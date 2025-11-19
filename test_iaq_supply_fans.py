#!/usr/bin/env python3
"""
Test script to convert Bressi Ranch Apartments with correct CIBD25 flat structure.
CIBD25 uses a FLAT structure where ResZnGrp is an empty container and ALL residential
elements (ResZn, DwellUnit, walls, floors, windows, etc.) are TOP-LEVEL siblings.
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from eco_tools.translators.cibd_xml_to_text import CIBDXMLToTextConverter

def main():
    # Source file
    source = Path("/Users/DavidM/Dropbox/EM-Tools-Assets/CBECC Models/Bressi Ranch/Bressi Ranch Apartments.cibd22x")

    # Output file with correct flat structure, Type properties, and ORDERING
    output = Path("/Users/DavidM/Downloads/Bressi_Ranch_V14_ORDERING_FIX.cibd25")

    print(f"Converting {source.name} to CIBD25 format...")
    print(f"Applying CIBD25 requirements:")
    print(f"  1. FLAT STRUCTURE:")
    print(f"     - ResZnGrp is empty container (properties only)")
    print(f"     - ResZn/ResOtherZn extracted as top-level siblings")
    print(f"     - DwellUnit extracted as top-level siblings")
    print(f"     - ALL geometry (walls, floors, windows, etc.) extracted as top-level siblings")
    print(f"     - HVAC systems and components also extracted as top-level siblings")
    print(f"  2. REQUIRED PROPERTIES:")
    print(f"     - Adding Type='Conditioned' to ResZn/ResOtherZn missing Type")
    print(f"  3. CORRECT ORDERING:")
    print(f"     - Zone children (walls, DwellUnits) written immediately after parent zone")
    print(f"     - This maintains proper parent-child relationships")
    print(f"\nThis matches official CIBD25 format requirements.")

    # Create converter
    converter = CIBDXMLToTextConverter()

    # Convert
    converter.convert_file(str(source), str(output))

    print(f"\nConversion complete!")
    print(f"Output saved to: {output}")
    print(f"\nNext step: Test in CBECC 2025 with:")
    print(f'  "/Applications/CBECC 2025.app/Contents/MacOS/CBECC 2025" -nrp -b "{output}"')

if __name__ == "__main__":
    main()
