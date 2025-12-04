#!/usr/bin/env python3
"""
CIBD Format Translator - Standalone Script

Converts between CBECC XML (CIBD22X) and CBECC Text (CIBD25) formats.

Usage:
    python translate_cibd.py input.cibd22x output.cibd25
    python translate_cibd.py --batch input_dir output_dir

Features:
    - Automatic ruleset conversion (T24N_2022.bin ↔ T24_2025.bin)
    - Nested element extraction to flat structure
    - Window type reference preservation
    - Property defaults for required fields
    - Proper element ordering

Author: ECO Tools Development Team
Date: November 18, 2025
Version: 1.1 (Window Type Fix)
"""

import sys
import os
import argparse
from pathlib import Path
from typing import Optional
from cibd_xml_to_text import CIBDXMLToTextConverter


def convert_single_file(input_path: str, output_path: str, verbose: bool = True) -> bool:
    """
    Convert a single CIBD file.

    Args:
        input_path: Path to input file (.cibd22x or .cibd25)
        output_path: Path to output file (.cibd25 or .cibd22x)
        verbose: Print progress messages

    Returns:
        True if conversion successful, False otherwise
    """
    if verbose:
        print(f"\n{'='*70}")
        print(f"CIBD Format Translator v1.1")
        print(f"{'='*70}")
        print(f"Input:  {input_path}")
        print(f"Output: {output_path}")

    # Detect input format
    input_ext = Path(input_path).suffix.lower()
    output_ext = Path(output_path).suffix.lower()

    if input_ext not in ['.cibd22x', '.cibd25']:
        print(f"ERROR: Unsupported input format: {input_ext}")
        print(f"Supported formats: .cibd22x, .cibd25")
        return False

    if output_ext not in ['.cibd22x', '.cibd25']:
        print(f"ERROR: Unsupported output format: {output_ext}")
        print(f"Supported formats: .cibd22x, .cibd25")
        return False

    # Perform conversion
    try:
        if input_ext == '.cibd22x' and output_ext == '.cibd25':
            # XML to Text conversion
            if verbose:
                print(f"\nConversion: CIBD22X (XML) → CIBD25 (Text)")
                print(f"  - Extracting nested elements to flat structure")
                print(f"  - Converting ruleset: T24N_2022.bin → T24_2025.bin")
                print(f"  - Preserving window type references")

            converter = CIBDXMLToTextConverter()
            converter.convert_file(input_path, output_path)

        elif input_ext == '.cibd25' and output_ext == '.cibd22x':
            # Text to XML conversion
            print(f"ERROR: CIBD25 → CIBD22X conversion not yet implemented")
            print(f"Currently supported: CIBD22X → CIBD25 only")
            return False

        else:
            print(f"ERROR: No conversion needed (same format)")
            return False

        # Verify output file created
        output_size = os.path.getsize(output_path)
        if verbose:
            print(f"\n✓ Conversion successful!")
            print(f"  Output file: {output_path}")
            print(f"  File size: {output_size / 1024:.1f} KB")

        return True

    except FileNotFoundError as e:
        print(f"\nERROR: Input file not found: {input_path}")
        return False
    except Exception as e:
        print(f"\nERROR: Conversion failed: {str(e)}")
        return False


def convert_batch(input_dir: str, output_dir: str, verbose: bool = True) -> dict:
    """
    Convert all CIBD files in a directory.

    Args:
        input_dir: Directory containing input files
        output_dir: Directory for output files
        verbose: Print progress messages

    Returns:
        Dictionary with conversion results
    """
    if verbose:
        print(f"\n{'='*70}")
        print(f"CIBD Batch Conversion")
        print(f"{'='*70}")
        print(f"Input directory:  {input_dir}")
        print(f"Output directory: {output_dir}")

    # Create output directory if it doesn't exist
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    # Find all CIBD files
    input_path = Path(input_dir)
    cibd_files = list(input_path.glob('*.cibd22x')) + list(input_path.glob('*.cibd25'))

    if not cibd_files:
        print(f"\nNo CIBD files found in {input_dir}")
        return {'success': 0, 'failed': 0, 'skipped': 0}

    if verbose:
        print(f"\nFound {len(cibd_files)} CIBD files")
        print(f"\n{'-'*70}")

    # Convert each file
    results = {'success': 0, 'failed': 0, 'skipped': 0}

    for input_file in cibd_files:
        # Determine output format and filename
        input_ext = input_file.suffix.lower()

        if input_ext == '.cibd22x':
            output_ext = '.cibd25'
        elif input_ext == '.cibd25':
            output_ext = '.cibd22x'
        else:
            results['skipped'] += 1
            continue

        output_file = Path(output_dir) / (input_file.stem + output_ext)

        # Convert
        print(f"\n[{results['success'] + results['failed'] + 1}/{len(cibd_files)}] {input_file.name}")

        if convert_single_file(str(input_file), str(output_file), verbose=False):
            results['success'] += 1
            print(f"  ✓ Success → {output_file.name}")
        else:
            results['failed'] += 1
            print(f"  ✗ Failed")

    # Print summary
    if verbose:
        print(f"\n{'='*70}")
        print(f"Batch Conversion Summary")
        print(f"{'='*70}")
        print(f"  Successful: {results['success']}")
        print(f"  Failed:     {results['failed']}")
        print(f"  Skipped:    {results['skipped']}")
        print(f"  Total:      {len(cibd_files)}")

    return results


def main():
    """Main entry point for command-line interface."""
    parser = argparse.ArgumentParser(
        description='Convert between CIBD22X and CIBD25 formats',
        epilog='''
Examples:
  Single file conversion:
    %(prog)s input.cibd22x output.cibd25

  Batch conversion:
    %(prog)s --batch input_dir output_dir

  Quiet mode:
    %(prog)s --quiet input.cibd22x output.cibd25
        ''',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument('input', help='Input file or directory')
    parser.add_argument('output', help='Output file or directory')
    parser.add_argument('--batch', '-b', action='store_true',
                       help='Batch mode: convert all files in directory')
    parser.add_argument('--quiet', '-q', action='store_true',
                       help='Suppress progress messages')
    parser.add_argument('--version', '-v', action='version',
                       version='%(prog)s 1.1 (Window Type Fix)')

    args = parser.parse_args()

    # Perform conversion
    if args.batch:
        results = convert_batch(args.input, args.output, verbose=not args.quiet)
        sys.exit(0 if results['failed'] == 0 else 1)
    else:
        success = convert_single_file(args.input, args.output, verbose=not args.quiet)
        sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
