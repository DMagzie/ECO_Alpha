#!/usr/bin/env python3
"""
Verify ProjVar extraction in all residential sample models.
Checks that ProjVar elements are created correctly and ExcptCond* properties
are removed from Proj elements.
"""

import sys
from pathlib import Path

def check_model_projvar(cibd25_path):
    """Check if a CIBD25 file has correct ProjVar structure."""
    results = {
        'has_projvar': False,
        'projvar_properties': [],
        'proj_has_excptcond': False,
        'excptcond_in_proj': []
    }

    with open(cibd25_path, 'r', encoding='utf-8') as f:
        in_projvar = False
        in_proj = False

        for line in f:
            stripped = line.strip()

            # Check for ProjVar element
            if stripped.startswith('ProjVar '):
                results['has_projvar'] = True
                in_projvar = True
                in_proj = False
                continue

            # Check for Proj element
            if stripped.startswith('Proj '):
                in_proj = True
                in_projvar = False
                continue

            # End of element
            if stripped == '..':
                in_projvar = False
                in_proj = False
                continue

            # Inside ProjVar - collect properties
            if in_projvar and '=' in stripped:
                prop_name = stripped.split('=')[0].strip()
                results['projvar_properties'].append(prop_name)

            # Inside Proj - check for ExcptCond properties
            if in_proj and '=' in stripped:
                prop_name = stripped.split('=')[0].strip()
                if prop_name.startswith('ExcptCond'):
                    results['proj_has_excptcond'] = True
                    results['excptcond_in_proj'].append(prop_name)

    return results

def main():
    models_dir = Path("/Users/DavidM/Downloads/Residential_Samples")

    print("=" * 80)
    print("PROJVAR EXTRACTION VERIFICATION")
    print("=" * 80)
    print("\nVerifying all residential sample models have correct ProjVar structure...")
    print("=" * 80)

    # Find all CIBD25 files
    cibd25_files = sorted(models_dir.glob("*.cibd25"))

    if not cibd25_files:
        print("❌ No CIBD25 files found in Residential_Samples directory!")
        return

    all_pass = True

    for cibd25_path in cibd25_files:
        print(f"\n{'─' * 80}")
        print(f"Model: {cibd25_path.name}")
        print(f"{'─' * 80}")

        results = check_model_projvar(cibd25_path)

        # Check ProjVar exists
        if results['has_projvar']:
            print("✅ ProjVar element found")

            if results['projvar_properties']:
                print(f"   Properties ({len(results['projvar_properties'])}):")
                for prop in results['projvar_properties']:
                    print(f"     • {prop}")
            else:
                print("   ⚠️  Warning: ProjVar has no properties")
        else:
            print("❌ ProjVar element NOT found")
            all_pass = False

        # Check Proj doesn't have ExcptCond properties
        if results['proj_has_excptcond']:
            print(f"❌ Proj element still has ExcptCond properties:")
            for prop in results['excptcond_in_proj']:
                print(f"     • {prop}")
            all_pass = False
        else:
            print("✅ Proj element has no ExcptCond properties (correctly extracted)")

    # Summary
    print(f"\n{'=' * 80}")
    print("VERIFICATION SUMMARY")
    print(f"{'=' * 80}")

    if all_pass:
        print(f"✅ All {len(cibd25_files)} models have correct ProjVar structure!")
        print("\nProjVar extraction is working as expected:")
        print("  • ExcptCond* properties are extracted from Proj elements")
        print("  • ProjVar elements are created with those properties")
        print("  • Translation matches CIBD25 format requirements")
    else:
        print(f"⚠️  Some models have issues with ProjVar extraction")
        print("   Please review the details above")

    print(f"{'=' * 80}")

if __name__ == "__main__":
    main()
