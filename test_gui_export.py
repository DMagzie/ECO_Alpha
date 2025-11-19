#!/usr/bin/env python3
"""
Test CIBD25 export using the same code path as the GUI.
This verifies our fixes are working outside of Streamlit.
"""

from gui.translators import emjson6_to_cibd25, translate_cibd22x_to_v6

# Step 1: Import Bressi Ranch from CIBD22X
print("Importing Bressi Ranch from CIBD22X...")
em_json = translate_cibd22x_to_v6('/Users/DavidM/Dropbox/EM-Tools-Assets/CBECC Models/Bressi Ranch/Bressi Ranch Apartments.cibd22x')

# Check for import errors
if 'diagnostics' in em_json:
    errors = [d for d in em_json['diagnostics'] if d['level'] == 'error']
    if errors:
        print(f"❌ Import failed with {len(errors)} errors")
        for err in errors[:3]:
            print(f"  - {err['message']}")
        exit(1)

print(f"✓ Import successful")

# Step 3: Export to CIBD25 using GUI function
print("Exporting to CIBD25 using GUI function...")
cibd25_text = emjson6_to_cibd25(
    em_json,
    source_cibd22x_file='/Users/DavidM/Dropbox/EM-Tools-Assets/CBECC Models/Bressi Ranch/Bressi Ranch Apartments.cibd22x'
)

# Step 4: Write to file
output_path = 'test_output/bressi_gui_test.cibd25'
print(f"Writing to {output_path}...")
with open(output_path, 'w', encoding='utf-8') as f:
    f.write(cibd25_text)

# Step 5: Quick validation - check for key fixes
print("\n=== Quick Validation ===")
lines = cibd25_text.split('\n')

# Check for RulesetFilename
has_ruleset = any('RulesetFilename' in line and 'T24_2025.bin' in line for line in lines[:10])
print(f"✓ RulesetFilename present: {has_ruleset}")

# Check for ResHtPumpSys as top-level object (not nested)
has_heatpump = any(line.startswith('ResHtPumpSys') for line in lines)
print(f"✓ ResHtPumpSys as top-level: {has_heatpump}")

# Check for MassThickness quoted correctly
mass_thickness_lines = [line for line in lines if 'MassThickness' in line]
if mass_thickness_lines:
    example = mass_thickness_lines[0].strip()
    has_quotes = '"' in example
    print(f"✓ MassThickness quoted: {has_quotes}")
    print(f"  Example: {example}")

# Check for BldgEngyModelVersion unquoted
bldg_version_lines = [line for line in lines if 'BldgEngyModelVersion' in line]
if bldg_version_lines:
    example = bldg_version_lines[0].strip()
    is_unquoted = '= 17' in example and 'BldgEngyModelVersion = 17' in example
    print(f"✓ BldgEngyModelVersion unquoted: {is_unquoted}")
    print(f"  Example: {example}")

print(f"\n✅ Export complete: {output_path}")
print("\nTo validate with CBECC 2025:")
print(f'  "/Applications/CBECC 2025.app/Contents/MacOS/CBECC 2025" -nrp -b {output_path}')
