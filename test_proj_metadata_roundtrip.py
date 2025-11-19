#!/usr/bin/env python3
"""
Test that proj_metadata (including ResProj) survives CIBD22X → EMJSON → CIBD25 roundtrip.
"""
import sys
from pathlib import Path

# Test the roundtrip
cibd22x_file = "/Users/DavidM/Documents/ECO_Alpha_v7/reference_data/cbecc/CBECC Models/Bressi Ranch/Bressi Ranch Apartments.cibd22x"

print("=" * 80)
print("Testing proj_metadata roundtrip")
print("=" * 80)

# Step 1: Import CIBD22X to EMJSON
print("\n1️⃣ Importing CIBD22X to EMJSON...")
from eco_tools.translators.cibd22x import translate_cibd22x_to_v6
emjson = translate_cibd22x_to_v6(cibd22x_file)

# Check if proj_metadata is in EMJSON
if "proj_metadata" in emjson:
    print("   ✓ proj_metadata found in EMJSON")

    # Check for ResProj
    if "ResProj" in emjson["proj_metadata"]:
        print("   ✓ ResProj found in proj_metadata")
        resproj = emjson["proj_metadata"]["ResProj"]
        if isinstance(resproj, dict):
            print(f"   ResProj keys: {list(resproj.keys())[:5]}...")
        else:
            print(f"   ResProj type: {type(resproj).__name__}")
    else:
        print("   ❌ ResProj NOT found in proj_metadata")
        print(f"   proj_metadata keys: {list(emjson['proj_metadata'].keys())}")
        sys.exit(1)
else:
    print("   ❌ proj_metadata NOT found in EMJSON")
    sys.exit(1)

# Step 2: Convert EMJSON back to InternalRepresentation
print("\n2️⃣ Converting EMJSON back to InternalRepresentation...")
sys.path.insert(0, str(Path(__file__).parent / "gui"))
from translators import _emjson_to_internal_repr

internal = _emjson_to_internal_repr(emjson)

# Check if proj_metadata is restored
if hasattr(internal, 'proj_metadata') and internal.proj_metadata:
    print("   ✓ proj_metadata restored in InternalRepresentation")

    # Check for ResProj
    if "ResProj" in internal.proj_metadata:
        print("   ✓ ResProj found in restored proj_metadata")
        resproj = internal.proj_metadata["ResProj"]
        if isinstance(resproj, dict):
            print(f"   ResProj keys: {list(resproj.keys())[:5]}...")
        else:
            print(f"   ResProj type: {type(resproj).__name__}")
    else:
        print("   ❌ ResProj NOT found in restored proj_metadata")
        print(f"   proj_metadata keys: {list(internal.proj_metadata.keys())}")
        sys.exit(1)
else:
    print("   ❌ proj_metadata NOT restored in InternalRepresentation")
    sys.exit(1)

# Step 3: Export to CIBD25
print("\n3️⃣ Exporting to CIBD25...")
from eco_tools.translators.cibd25 import CIBD25Exporter

output_file = "/Users/DavidM/Documents/ECO_Alpha_v7/test_output/bressi_gui_roundtrip.cibd25"
Path(output_file).parent.mkdir(parents=True, exist_ok=True)

exporter = CIBD25Exporter()
exporter.export(internal, output_file)
print(f"   ✓ Exported to {output_file}")

# Step 4: Verify ResProj is in the output file
print("\n4️⃣ Verifying ResProj in CIBD25 output...")
with open(output_file, 'r') as f:
    cibd25_content = f.read()

if 'ResProj' in cibd25_content:
    print("   ✓ ResProj found in CIBD25 output")

    # Find the ResProj block
    import re
    resproj_match = re.search(r'ResProj\s+"([^"]+)"', cibd25_content)
    if resproj_match:
        print(f"   ResProj name: {resproj_match.group(1)}")
else:
    print("   ❌ ResProj NOT found in CIBD25 output")
    sys.exit(1)

# Step 5: Check for proper Proj name
if 'Proj   "Bressi Ranch Apartments"' in cibd25_content:
    print("   ✓ Proj has correct name attribute")
elif 'Proj   "' in cibd25_content:
    proj_match = re.search(r'Proj\s+"([^"]+)"', cibd25_content)
    print(f"   ✓ Proj name: {proj_match.group(1)}")
else:
    print("   ⚠️  Proj name not found (may be using metadata name)")

print("\n" + "=" * 80)
print("✅ SUCCESS: proj_metadata roundtrip working correctly!")
print("=" * 80)
print(f"\nTest file ready: {output_file}")
print("You can now test this file in CBECC 2025")
