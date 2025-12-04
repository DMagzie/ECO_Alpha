"""
Batch Processor Utility

Process multiple CIBD25 files with utilities in batch.

Usage:
    from eco_tools.translators.utilities import BatchProcessor

    processor = BatchProcessor()
    results = processor.process_directory(
        '/path/to/models/',
        operations=['inject_catalogs', 'fix_properties', 'validate']
    )

    print(results['summary'])
"""

from typing import Dict, List, Any
from pathlib import Path
import logging

from .window_type_mapper import WindowTypeMapper
from .commercial_catalog_injector import CommercialCatalogInjector
from .property_fixer import PropertyFixer
from .validator import CIBD25Validator

logger = logging.getLogger(__name__)


class BatchProcessor:
    """Apply utilities to multiple CIBD25 files."""

    def __init__(self):
        """Initialize the batch processor."""
        self.window_mapper = WindowTypeMapper()
        self.catalog_injector = CommercialCatalogInjector()
        self.property_fixer = PropertyFixer()
        self.validator = CIBD25Validator()

    def process_directory(
        self,
        directory: str,
        operations: List[str],
        validate: bool = True,
        recursive: bool = False
    ) -> Dict[str, Any]:
        """
        Process all CIBD25 files in a directory.

        Args:
            directory: Directory containing .cibd25 files
            operations: List of operations to apply:
                - 'inject_catalogs': Add commercial catalogs
                - 'map_window_types': Map window types to instances
                - 'fix_properties': Fix invalid properties
                - 'validate': Validate files
            validate: Run validation after processing
            recursive: Process subdirectories

        Returns:
            Results dictionary:
            {
                'files_processed': int,
                'files_with_errors': int,
                'operations_applied': Dict[str, int],
                'summary': str
            }
        """
        logger.info(f"Processing directory: {directory}")

        # Find all .cibd25 files
        pattern = "**/*.cibd25" if recursive else "*.cibd25"
        files = list(Path(directory).glob(pattern))
        logger.info(f"Found {len(files)} CIBD25 files")

        results = {
            'files_processed': 0,
            'files_with_errors': 0,
            'operations_applied': {},
            'file_results': {},
            'summary': ''
        }

        # Process each file
        for file_path in files:
            file_results = self.process_file(
                str(file_path),
                operations,
                validate
            )
            results['file_results'][str(file_path)] = file_results
            results['files_processed'] += 1

            if file_results.get('errors'):
                results['files_with_errors'] += 1

        # Generate summary
        results['summary'] = self.generate_summary(results)

        return results

    def process_file(
        self,
        file_path: str,
        operations: List[str],
        validate: bool = True
    ) -> Dict[str, Any]:
        """
        Process a single CIBD25 file.

        Args:
            file_path: Path to .cibd25 file
            operations: List of operations to apply
            validate: Run validation after processing

        Returns:
            File processing results
        """
        logger.info(f"Processing file: {file_path}")

        file_results = {
            'operations': [],
            'errors': [],
            'validation': None
        }

        try:
            # Apply operations in order
            if 'inject_catalogs' in operations:
                success = self.catalog_injector.inject_catalogs(file_path)
                file_results['operations'].append({
                    'name': 'inject_catalogs',
                    'success': success
                })

            if 'map_window_types' in operations:
                success = self.window_mapper.process_file(file_path)
                file_results['operations'].append({
                    'name': 'map_window_types',
                    'success': success
                })

            if 'fix_properties' in operations:
                report = self.property_fixer.fix_properties(file_path)
                file_results['operations'].append({
                    'name': 'fix_properties',
                    'success': report['fixes_applied'] >= 0,
                    'fixes_applied': report['fixes_applied']
                })

            # Validate if requested
            if validate or 'validate' in operations:
                validation = self.validator.validate_file(file_path)
                file_results['validation'] = validation

        except Exception as e:
            logger.error(f"Error processing {file_path}: {e}")
            file_results['errors'].append(str(e))

        return file_results

    def generate_summary(self, results: Dict[str, Any]) -> str:
        """Generate a summary report."""
        summary_lines = [
            f"Processed: {results['files_processed']} file(s)",
            f"Files with errors: {results['files_with_errors']}",
            f"Files clean: {results['files_processed'] - results['files_with_errors']}",
        ]

        # TODO: Add more detailed summary statistics

        return "\n".join(summary_lines)

    def generate_report(self, results: Dict[str, Any]) -> str:
        """Generate a detailed processing report."""
        # TODO: Implement detailed report generation
        return self.generate_summary(results)
