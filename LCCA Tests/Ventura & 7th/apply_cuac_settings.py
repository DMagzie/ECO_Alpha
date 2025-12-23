"""
Apply CUAC Settings to CIBD22 Files
===================================

Updates:
1. Adds CUACReport = 1 to Proj block
2. Sets PVArray DCSysSize to 350
3. Sets AffordablePVDCSysSize to 350
4. Corrects PV allocation percentages to sum to 100%
"""

import re
import sys
from pathlib import Path


def apply_cuac_settings(file_path: Path):
    """Apply CUAC settings to a CIBD22 file."""
    content = file_path.read_text(encoding='utf-8')
    modified = False

    # 1. Add CUACReport = 1 after CompOptLtg = 1
    if 'CUACReport' not in content:
        content = re.sub(
            r'(CompOptLtg\s*=\s*1)',
            r'\1\n   CUACReport = 1',
            content
        )
        print(f"  Added CUACReport = 1")
        modified = True

    # 2. Update PVArray DCSysSize to 350
    old_pv = re.search(r'(PVArray\s+"[^"]+"\s+.*?DCSysSize\s*=\s*)(\d+\.?\d*)', content, re.DOTALL)
    if old_pv and float(old_pv.group(2)) != 350:
        content = re.sub(
            r'(PVArray\s+"[^"]+"\s+.*?DCSysSize\s*=\s*)(\d+\.?\d*)',
            r'\g<1>350',
            content,
            flags=re.DOTALL
        )
        print(f"  Updated PVArray DCSysSize: {old_pv.group(2)} -> 350")
        modified = True

    # 3. Update AffordablePVDCSysSize to 350
    old_cuac_pv = re.search(r'AffordablePVDCSysSize\s*=\s*(\d+\.?\d*)', content)
    if old_cuac_pv and float(old_cuac_pv.group(1)) != 350:
        content = re.sub(
            r'AffordablePVDCSysSize\s*=\s*\d+\.?\d*',
            'AffordablePVDCSysSize = 350',
            content
        )
        print(f"  Updated AffordablePVDCSysSize: {old_cuac_pv.group(1)} -> 350")
        modified = True

    # 4. Update PV allocation percentages
    # Correct values: 1BR=1.154%, 2BR=1.681%, 3BR=2.611%
    # Note: [2]=1BR, [3]=2BR, [4]=3BR in CBECC indexing
    pv_allocations = {
        'PctIndivUnitPVByBedrms[2]': 1.154,  # 1BR
        'PctIndivUnitPVByBedrms[3]': 1.681,  # 2BR
        'PctIndivUnitPVByBedrms[4]': 2.611,  # 3BR
    }

    for key, new_val in pv_allocations.items():
        pattern = rf'{re.escape(key)}\s*=\s*([\d.]+)'
        match = re.search(pattern, content)
        if match and abs(float(match.group(1)) - new_val) > 0.001:
            content = re.sub(
                pattern,
                f'{key} = {new_val}',
                content
            )
            print(f"  Updated {key}: {match.group(1)} -> {new_val}")
            modified = True

    if modified:
        file_path.write_text(content, encoding='utf-8')
        print(f"  Saved changes to {file_path.name}")
    else:
        print(f"  No changes needed")

    return modified


def main():
    base_path = Path("/Users/DavidM/Documents/ECO_Alpha_v7/LCCA Tests/Ventura & 7th")

    files = [
        base_path / "Maestro/Ventura and 7th Updated Maestro_CUAC.cibd22",
        base_path / "Ephoca + Maestros/Ventura and 7th One Ephoca + Maestros_CUAC.cibd22",
        base_path / "Ephoca Min Ventilation/Ventura and 7th Ephoca Min Ventilation_CUAC.cibd22",
    ]

    for f in files:
        print(f"\nProcessing: {f.name}")
        if f.exists():
            apply_cuac_settings(f)
        else:
            print(f"  ERROR: File not found!")


if __name__ == "__main__":
    main()
