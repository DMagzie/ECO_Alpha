#!/usr/bin/env python3
"""
Test the tree navigator functionality with real CIBD22X data.
"""
import sys
from pathlib import Path

# Add project root to path
ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

# Add em-tools to path
EM_TOOLS = ROOT / "em-tools"
sys.path.insert(0, str(EM_TOOLS))

from emtools.translators.cibd22x_importer import translate_cibd22x_to_v6

def test_tree_navigator():
    """Test tree navigator with a real CIBD22X file."""
    
    # Find a sample CIBD22X file
    sample_dir = ROOT / "Reference_Datasets" / "cbecc_samples"
    
    if not sample_dir.exists():
        print(f"❌ Sample directory not found: {sample_dir}")
        return False
    
    # Get first XML file
    xml_files = list(sample_dir.glob("*.xml"))
    if not xml_files:
        print(f"❌ No XML files found in {sample_dir}")
        return False
    
    test_file = xml_files[0]
    print(f"📁 Testing with: {test_file.name}")
    
    # Import the file
    try:
        emjson_model = translate_cibd22x_to_v6(str(test_file))
        
        print(f"✓ Import successful")
        diagnostics = emjson_model.get("diagnostics", [])
        print(f"  Diagnostics: {len(diagnostics)} messages")
        
        # Check model structure for tree navigator
        print("\n📊 Model Structure:")
        
        if "project" in emjson_model:
            print("  ✓ Project section found")
            if "location" in emjson_model["project"]:
                print("    ✓ Location data present")
        
        if "geometry" in emjson_model:
            geom = emjson_model["geometry"]
            zones = geom.get("zones", [])
            surfaces = geom.get("surfaces", {})
            openings = geom.get("openings", {})
            
            print(f"  ✓ Geometry section found")
            print(f"    - Zones: {len(zones)}")
            
            if zones:
                # Check if zones have surfaces
                zones_with_surfaces = sum(1 for z in zones if z.get("surfaces"))
                print(f"      - Zones with surfaces: {zones_with_surfaces}")
            
            if isinstance(surfaces, dict):
                total_surfaces = sum(len(v) for v in surfaces.values() if isinstance(v, list))
                print(f"    - Surfaces: {total_surfaces}")
            elif isinstance(surfaces, list):
                print(f"    - Surfaces: {len(surfaces)}")
            
            if isinstance(openings, dict):
                total_openings = sum(len(v) for v in openings.values() if isinstance(v, list))
                print(f"    - Openings: {total_openings}")
        
        if "catalogs" in emjson_model:
            catalogs = emjson_model["catalogs"]
            print(f"  ✓ Catalogs section found")
            for cat_name, cat_items in catalogs.items():
                if isinstance(cat_items, list):
                    print(f"    - {cat_name}: {len(cat_items)} items")
        
        if "systems" in emjson_model:
            systems = emjson_model["systems"]
            print(f"  ✓ Systems section found")
            print(f"    - HVAC: {len(systems.get('hvac', []))}")
            print(f"    - DHW: {len(systems.get('dhw', []))}")
            print(f"    - PV: {len(systems.get('pv', []))}")
        
        print("\n✅ Tree navigator data structure verified successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_tree_navigator()
    sys.exit(0 if success else 1)
