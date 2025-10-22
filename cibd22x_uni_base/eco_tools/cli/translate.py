"""
CLI Translation Tool
"""

import sys
import argparse
from pathlib import Path
from eco_tools.core.translator import UniversalTranslator


def main(argv=None):
    """Main CLI entry point for translation"""
    parser = argparse.ArgumentParser(
        description='ECO Tools - Universal CBECC File Translator'
    )
    
    parser.add_argument('input', help='Input file path')
    parser.add_argument('--to', dest='target_format', required=True,
                       choices=['CIBD22', 'CIBD22X', 'EMJSON'],
                       help='Target format')
    parser.add_argument('--output', '-o', help='Output file path')
    parser.add_argument('--validate', action='store_true',
                       help='Validate before and after translation')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Verbose output')
    
    args = parser.parse_args(argv)
    
    # Determine output path
    output_path = args.output
    if not output_path:
        input_path = Path(args.input)
        extensions = {
            'CIBD22': '.cibd22',
            'CIBD22X': '.cibd22x',
            'EMJSON': '.emjson'
        }
        ext = extensions[args.target_format]
        output_path = input_path.stem + ext
    
    # Translate
    translator = UniversalTranslator()
    
    try:
        result = translator.translate(args.input, args.target_format, output_path)
        
        print(f"\n{'='*60}")
        print(f"Translation: {result}")
        print(f"{'='*60}")
        
        if args.validate:
            print(f"\nSource Validation:")
            print(f"  {result.source_validation}")
            if result.source_validation.errors:
                for err in result.source_validation.errors:
                    print(f"    ERROR: {err}")
            
            print(f"\nTarget Validation:")
            print(f"  {result.target_validation}")
            if result.target_validation.errors:
                for err in result.target_validation.errors:
                    print(f"    ERROR: {err}")
        
        if result.target_validation.is_valid:
            print(f"\n✓ Translation successful: {output_path}")
            return 0
        else:
            print(f"\n✗ Translation failed with {len(result.target_validation.errors)} errors")
            return 1
    
    except Exception as e:
        print(f"\nError: {e}", file=sys.stderr)
        if args.verbose:
            import traceback
            traceback.print_exc()
        return 2


if __name__ == '__main__':
    sys.exit(main())
