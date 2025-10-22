"""
CLI Validation Tool
"""

import sys
import argparse
from eco_tools.core.validator import Validator


def main(argv=None):
    """Main CLI entry point for validation"""
    parser = argparse.ArgumentParser(
        description='ECO Tools - File Validator'
    )
    
    parser.add_argument('input', help='Input file path')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Verbose output')
    
    args = parser.parse_args(argv)
    
    # Validate
    validator = Validator()
    
    try:
        result = validator.validate_file(args.input)
        
        print(f"\nValidation Result: {result}")
        print(f"{'='*60}")
        
        if result.errors:
            print(f"\nErrors ({len(result.errors)}):")
            for err in result.errors:
                print(f"  ✗ {err}")
        
        if result.warnings:
            print(f"\nWarnings ({len(result.warnings)}):")
            for warn in result.warnings:
                print(f"  ⚠ {warn}")
        
        if args.verbose and result.info:
            print(f"\nInfo:")
            for info in result.info:
                print(f"  ℹ {info}")
        
        if result.is_valid:
            print(f"\n✓ File is valid")
            return 0
        else:
            print(f"\n✗ File is invalid")
            return 1
    
    except Exception as e:
        print(f"\nError: {e}", file=sys.stderr)
        if args.verbose:
            import traceback
            traceback.print_exc()
        return 2


if __name__ == '__main__':
    sys.exit(main())
