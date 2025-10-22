"""
CLI Info Tool
"""

import sys
import argparse
from eco_tools.core.format_detector import FormatDetector
from eco_tools.core.translator import UniversalTranslator


def main(argv=None):
    """Main CLI entry point for file info"""
    parser = argparse.ArgumentParser(
        description='ECO Tools - File Information'
    )
    
    parser.add_argument('input', help='Input file path')
    parser.add_argument('--detailed', '-d', action='store_true',
                       help='Show detailed information')
    
    args = parser.parse_args(argv)
    
    try:
        # Detect format
        detector = FormatDetector()
        format_info = detector.detect(args.input)
        
        print(f"\nFile Information")
        print(f"{'='*60}")
        print(f"Format:        {format_info.format_type}")
        print(f"Version:       {format_info.version}")
        print(f"Building Type: {format_info.building_type}")
        if format_info.ruleset:
            print(f"Ruleset:       {format_info.ruleset}")
        print(f"Confidence:    {format_info.confidence:.1%}")
        
        # Load and show counts if detailed
        if args.detailed:
            translator = UniversalTranslator()
            internal = translator.load(args.input, format_info)
            
            print(f"\nContent Summary")
            print(f"{'='*60}")
            print(f"Zones:         {len(internal.zones)}")
            print(f"Surfaces:      {len(internal.surfaces)}")
            print(f"Openings:      {len(internal.openings)}")
            print(f"HVAC Systems:  {len(internal.hvac_systems)}")
            print(f"DHW Systems:   {len(internal.dhw_systems)}")
            
            if internal.zones:
                total_area = sum(z.floor_area_m2 or 0 for z in internal.zones)
                print(f"Total Area:    {total_area:.1f} m²")
        
        return 0
    
    except Exception as e:
        print(f"\nError: {e}", file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
