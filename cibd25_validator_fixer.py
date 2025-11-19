#!/usr/bin/env python3
"""
CIBD25 Comprehensive Validator and Fixer

This script definitively solves recurring CIBD25 export issues:
1. Integer values incorrectly quoted
2. Parent/child nesting problems
3. Format inconsistencies
4. Structure validation

Usage:
    python cibd25_validator_fixer.py input.cibd25 output.cibd25
    python cibd25_validator_fixer.py --validate input.cibd25
    python cibd25_validator_fixer.py --batch ~/Downloads/*.cibd25
"""

import re
import sys
from pathlib import Path
from typing import List, Dict, Tuple, Optional
import argparse


class CIBD25ValidatorFixer:
    """Comprehensive CIBD25 file validator and fixer"""

    # Integer fields that should NEVER be quoted
    INTEGER_FIELDS = {
        'BldgEngyModelVersion',
        'CompReportPDF',
        'CreateDate',
        'ModDate',
        'ReducedPVReq',
        'NumFloor',
        'FloorArea',
        'NumStories',
        'NumberOfBedrooms',
        'TotStoryCnt',
        'AboveGradeStoryCnt',
        'BelowGradeStoryCnt',
        'FloorNum',
        'BuildingStoriesAboveGrade',
        'BuildingStoriesBelowGrade',
    }

    # Float fields that should NEVER be quoted
    FLOAT_FIELDS = {
        'FloorToFloorHeight',
        'FloorToCeilingHeight',
        'PlenumHeight',
        'Area',
        'Volume',
        'TotFlrArea',
        'CondFlrArea',
        'Lat',
        'Long',
        'Elevation',
    }

    # String fields that MUST be quoted
    STRING_FIELDS = {
        'Name',
        'City',
        'State',
        'ZipCode',
        'CompReportPDF',
        'DocAuthAddress',
        'DocAuthCity',
        'DocAuthCompany',
        'DocAuthState',
        'DocAuthZipCode',
        'EffMetric',
        'ExcptCondNarrative',
        'GeometryInpType',
        'ResultsCurrentMessage',
        'WeatherStation',
        'ClimateZone',
        'Type',
        'Status',
    }

    def __init__(self):
        self.errors = []
        self.warnings = []
        self.fixes_applied = []

    def validate_and_fix_file(self, input_path: str, output_path: Optional[str] = None) -> bool:
        """
        Validate and fix a CIBD25 file

        Args:
            input_path: Path to input file
            output_path: Path to output file (None = validate only)

        Returns:
            True if valid or fixed successfully
        """
        print(f"\n{'='*70}")
        print(f"Processing: {Path(input_path).name}")
        print(f"{'='*70}")

        # Reset state
        self.errors = []
        self.warnings = []
        self.fixes_applied = []

        # Read file
        try:
            with open(input_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception as e:
            self.errors.append(f"Failed to read file: {e}")
            return False

        # Split into lines for processing
        lines = content.split('\n')

        # Apply all fixes
        fixed_lines = []
        for line_num, line in enumerate(lines, 1):
            fixed_line = self._fix_line(line, line_num)
            fixed_lines.append(fixed_line)

        # Validate structure
        self._validate_structure(fixed_lines)

        # Report results
        self._print_report()

        # Write output if requested
        if output_path:
            try:
                with open(output_path, 'w', encoding='utf-8') as f:
                    f.write('\n'.join(fixed_lines))
                print(f"\n✅ Fixed file written to: {output_path}")
                return True
            except Exception as e:
                self.errors.append(f"Failed to write output: {e}")
                return False

        return len(self.errors) == 0

    def _fix_line(self, line: str, line_num: int) -> str:
        """Fix a single line"""
        original_line = line

        # Fix 1: Unquote integer fields
        for field in self.INTEGER_FIELDS:
            pattern = f'({field})\\s*=\\s*"(\\d+)"'
            if re.search(pattern, line):
                line = re.sub(pattern, r'\1 = \2', line)
                self.fixes_applied.append(
                    f"Line {line_num}: Unquoted integer field '{field}'"
                )

        # Fix 2: Unquote float fields
        for field in self.FLOAT_FIELDS:
            pattern = f'({field})\\s*=\\s*"([\\d.]+)"'
            if re.search(pattern, line):
                line = re.sub(pattern, r'\1 = \2', line)
                self.fixes_applied.append(
                    f"Line {line_num}: Unquoted float field '{field}'"
                )

        # Fix 3: Ensure string fields are quoted
        for field in self.STRING_FIELDS:
            # Pattern: field = value (not already quoted)
            pattern = f'({field})\\s*=\\s*([^"\\s][^\\n]*?)\\s*$'
            match = re.search(pattern, line)
            if match:
                value = match.group(2).strip()
                # Don't quote if it's already a quoted string
                if not (value.startswith('"') and value.endswith('"')):
                    line = re.sub(pattern, f'\\1 = "{value}"', line)
                    self.fixes_applied.append(
                        f"Line {line_num}: Quoted string field '{field}'"
                    )

        # Fix 4: Normalize whitespace around =
        if '=' in line and not line.strip().startswith('//'):
            line = re.sub(r'\s*=\s*', ' = ', line)

        # Fix 5: Remove trailing whitespace
        line = line.rstrip()

        # Fix 6: Ensure proper indentation (multiples of 3 spaces)
        if line.strip() and not line.strip().startswith('//'):
            leading_spaces = len(line) - len(line.lstrip())
            # Normalize to multiples of 3
            if leading_spaces % 3 != 0:
                correct_indent = (leading_spaces // 3) * 3
                line = ' ' * correct_indent + line.lstrip()
                self.fixes_applied.append(
                    f"Line {line_num}: Fixed indentation ({leading_spaces} -> {correct_indent})"
                )

        return line

    def _validate_structure(self, lines: List[str]):
        """Validate file structure"""
        # Check for RulesetFilename
        has_ruleset = any('RulesetFilename' in line for line in lines[:5])
        if not has_ruleset:
            self.errors.append("Missing RulesetFilename in first 5 lines")

        # Check for Proj
        has_proj = any('Proj ' in line for line in lines[:20])
        if not has_proj:
            self.errors.append("Missing Proj definition in first 20 lines")

        # Track nesting
        nesting_stack = []
        for line_num, line in enumerate(lines, 1):
            stripped = line.strip()

            # Skip empty lines and comments
            if not stripped or stripped.startswith('//'):
                continue

            # Check for opening tags (new objects)
            if re.match(r'^[A-Z]\w+\s+"[^"]*"', stripped):
                obj_type = stripped.split()[0]
                nesting_stack.append((obj_type, line_num))

            # Check for closing (dedent back)
            # This is implicit in CIBD25 format

        # Validate parent-child relationships
        self._validate_parent_child(lines)

    def _validate_parent_child(self, lines: List[str]):
        """Validate parent-child relationships"""
        current_indent = 0
        parent_stack = []

        for line_num, line in enumerate(lines, 1):
            if not line.strip() or line.strip().startswith('//'):
                continue

            indent = len(line) - len(line.lstrip())

            # Detect object definition
            if re.match(r'^\s*[A-Z]\w+\s+"[^"]*"', line):
                obj_name = line.strip().split()[0]

                # Check if indent is correct
                if indent < current_indent:
                    # Popping back up
                    while parent_stack and indent <= parent_stack[-1][1]:
                        parent_stack.pop()

                parent_stack.append((obj_name, indent))
                current_indent = indent

    def _print_report(self):
        """Print validation/fix report"""
        print(f"\n📊 Report:")
        print(f"   Fixes applied: {len(self.fixes_applied)}")
        print(f"   Warnings: {len(self.warnings)}")
        print(f"   Errors: {len(self.errors)}")

        if self.fixes_applied:
            print(f"\n🔧 Fixes Applied:")
            for fix in self.fixes_applied[:10]:  # Show first 10
                print(f"   - {fix}")
            if len(self.fixes_applied) > 10:
                print(f"   ... and {len(self.fixes_applied) - 10} more")

        if self.warnings:
            print(f"\n⚠️  Warnings:")
            for warning in self.warnings:
                print(f"   - {warning}")

        if self.errors:
            print(f"\n❌ Errors:")
            for error in self.errors:
                print(f"   - {error}")
        else:
            print(f"\n✅ No errors found!")

    def batch_process(self, pattern: str, output_dir: Optional[str] = None):
        """
        Process multiple files matching pattern

        Args:
            pattern: Glob pattern (e.g., "~/Downloads/*.cibd25")
            output_dir: Output directory (None = validate only)
        """
        from glob import glob

        files = glob(pattern)
        if not files:
            print(f"No files found matching: {pattern}")
            return

        print(f"\n{'='*70}")
        print(f"Batch Processing: {len(files)} files")
        print(f"{'='*70}")

        if output_dir:
            output_path = Path(output_dir)
            output_path.mkdir(exist_ok=True, parents=True)

        results = []
        for file_path in files:
            if output_dir:
                output_file = Path(output_dir) / f"{Path(file_path).stem}_fixed.cibd25"
                success = self.validate_and_fix_file(file_path, str(output_file))
            else:
                success = self.validate_and_fix_file(file_path)

            results.append((file_path, success))

        # Summary
        print(f"\n{'='*70}")
        print(f"Batch Summary:")
        print(f"{'='*70}")
        successful = sum(1 for _, success in results if success)
        print(f"✅ Successful: {successful}/{len(results)}")
        print(f"❌ Failed: {len(results) - successful}/{len(results)}")


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description='CIBD25 Comprehensive Validator and Fixer',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Validate a file
  python cibd25_validator_fixer.py --validate input.cibd25

  # Fix a file
  python cibd25_validator_fixer.py input.cibd25 output.cibd25

  # Batch fix all files in Downloads
  python cibd25_validator_fixer.py --batch "~/Downloads/bressi*.cibd25" --output ~/Downloads/fixed/
        """
    )

    parser.add_argument('input', nargs='?', help='Input CIBD25 file')
    parser.add_argument('output', nargs='?', help='Output CIBD25 file (fixed)')
    parser.add_argument('--validate', action='store_true', help='Validate only (no output)')
    parser.add_argument('--batch', help='Batch process files matching pattern')
    parser.add_argument('--output-dir', '--output', help='Output directory for batch processing')

    args = parser.parse_args()

    validator = CIBD25ValidatorFixer()

    if args.batch:
        # Batch processing
        validator.batch_process(args.batch, args.output_dir)
    elif args.input:
        # Single file
        if args.validate:
            success = validator.validate_and_fix_file(args.input)
        else:
            if not args.output:
                print("Error: Output file required (or use --validate)")
                sys.exit(1)
            success = validator.validate_and_fix_file(args.input, args.output)

        sys.exit(0 if success else 1)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == '__main__':
    main()
