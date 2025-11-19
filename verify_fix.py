#!/usr/bin/env python3
"""
Verify that the ResZnGrp fix is present in the code.
Run this before restarting Streamlit to confirm the fix is there.
"""

# Check if the fix is in the file
fix_file = "eco_tools/translators/cibd_xml_to_text.py"

with open(fix_file, 'r') as f:
    content = f.read()

# Look for the fix
if "if parent_tag == 'Bldg':" in content and "if child_tag == 'ResZnGrp':" in content:
    print("✅ ResZnGrp fix is PRESENT in cibd_xml_to_text.py")

    # Show the actual code
    print("\nFix code found:")
    print("-" * 60)
    lines = content.split('\n')
    for i, line in enumerate(lines):
        if "if parent_tag == 'Bldg':" in line:
            # Print context (5 lines before and after)
            for j in range(max(0, i-2), min(len(lines), i+6)):
                print(f"{j+1:4d}: {lines[j]}")
            break
    print("-" * 60)
else:
    print("❌ ResZnGrp fix is MISSING from cibd_xml_to_text.py")
    print("   The fix should include:")
    print("   - if parent_tag == 'Bldg':")
    print("   - if child_tag == 'ResZnGrp':")

print("\n" + "=" * 60)
print("Next steps:")
print("=" * 60)
print("1. Kill Streamlit (press Ctrl+C in the terminal running it)")
print("2. Clear cache: rm -rf ~/.streamlit/cache")
print("3. Restart: streamlit run gui/main.py")
print("4. Re-import the CIBD22X file in the GUI")
print("5. Export to CIBD25")
print("=" * 60)
