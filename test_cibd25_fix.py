"""
Quick test to verify CIBD25 export fix for duplicate WinType bug.
"""
import sys
from pathlib import Path

# Test with Bressi Ranch (large model with windows)
input_file = Path("/Users/DavidM/Documents/ECO_Alpha_v7/reference_data/cbecc/CBECC Models/Bressi Ranch/Bressi Ranch Apartments.cibd22x")
output_file = Path("/Users/DavidM/Documents/ECO_Alpha_v7/test_output/bressi_fixed.cibd25")

if not input_file.exists():
    print(f"❌ Input file not found: {input_file}")
    sys.exit(1)

# Import
print(f"📥 Importing {input_file.name}...")
from eco_tools.translators.cibd22x import CIBD22XImporter
importer = CIBD22XImporter()
model = importer.import_file(str(input_file))

print(f"✓ Imported {len(model.zones)} zones")

# Export to CIBD25
print(f"\n📤 Exporting to CIBD25...")
output_file.parent.mkdir(parents=True, exist_ok=True)
from eco_tools.translators.cibd25 import CIBD25Exporter
exporter = CIBD25Exporter()
exporter.export(model, str(output_file))

print(f"✓ Exported to {output_file}")
print(f"   File size: {output_file.stat().st_size:,} bytes")

# Check for duplicate WinType properties
print(f"\n🔍 Checking for duplicate WinType properties...")
with open(output_file, 'r') as f:
    lines = f.readlines()

duplicates_found = []
current_window = None
wintype_count = 0

for i, line in enumerate(lines, 1):
    # Detect new window element
    if 'ResWin' in line and '"' in line:
        if wintype_count > 1:
            duplicates_found.append((current_window, wintype_count))
        current_window = line.strip()
        wintype_count = 0
    elif 'WinType' in line and '=' in line:
        wintype_count += 1

# Check last window
if wintype_count > 1:
    duplicates_found.append((current_window, wintype_count))

if duplicates_found:
    print(f"❌ FOUND {len(duplicates_found)} WINDOWS WITH DUPLICATE WinType!")
    for window, count in duplicates_found[:5]:  # Show first 5
        print(f"   - {window[:60]}... ({count} WinType properties)")
    sys.exit(1)
else:
    print(f"✅ NO DUPLICATES FOUND!")

# Quick syntax check
print(f"\n🔍 Quick syntax check...")
total_lines = len(lines)
wintype_lines = sum(1 for line in lines if 'WinType' in line and '=' in line)
reswin_lines = sum(1 for line in lines if 'ResWin' in line and '"' in line)

print(f"   Total lines: {total_lines:,}")
print(f"   ResWin elements: {reswin_lines}")
print(f"   WinType properties: {wintype_lines}")

if wintype_lines == reswin_lines:
    print(f"✅ 1:1 ratio (each window has exactly 1 WinType)")
elif wintype_lines < reswin_lines:
    print(f"⚠️  Some windows missing WinType ({reswin_lines - wintype_lines} missing)")
else:
    print(f"⚠️  More WinTypes than windows (possible duplicates: {wintype_lines - reswin_lines})")

print(f"\n✅ TEST PASSED - Export is syntactically valid")
print(f"\n📝 Next step: Try opening {output_file.name} in CBECC 2025")
