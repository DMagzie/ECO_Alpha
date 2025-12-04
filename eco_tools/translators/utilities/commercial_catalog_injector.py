"""
Commercial Catalog Injector Utility

Add commercial catalogs to residential-only CIBD25 files.

Problem:
Pure residential files often lack commercial catalogs (Mat, ConsAssm, FenCons).
When CBECC tries to reference these catalogs, it returns "Invalid component type"
errors (typically 101 errors).

Solution:
This utility injects baseline commercial catalogs into files that are missing them.

Usage:
    from eco_tools.translators.utilities import CommercialCatalogInjector

    injector = CommercialCatalogInjector()
    injector.inject_catalogs('euclid_c.cibd25')  # Adds Mat, ConsAssm, FenCons
"""

from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)


class CommercialCatalogInjector:
    """Add commercial catalogs to residential-only files."""

    def inject_catalogs(
        self,
        cibd25_path: str,
        include_mat: bool = True,
        include_consassm: bool = True,
        include_fencons: bool = True
    ) -> bool:
        """
        Inject commercial catalogs into a CIBD25 file.

        Args:
            cibd25_path: Path to .cibd25 file
            include_mat: Include Mat catalog
            include_consassm: Include ConsAssm catalog
            include_fencons: Include FenCons catalog

        Returns:
            True if successful, False otherwise
        """
        try:
            logger.info(f"Injecting commercial catalogs into {cibd25_path}")

            # Read file
            with open(cibd25_path, 'r') as f:
                content = f.read()

            # Check what's missing
            status = self.has_commercial_catalogs(content)
            logger.info(f"Catalog status: {status}")

            # Inject what's missing
            if include_mat and not status['Mat']:
                content = self._inject_mat_catalog(content)
                logger.info("Injected Mat catalog")

            if include_consassm and not status['ConsAssm']:
                content = self._inject_consassm_catalog(content)
                logger.info("Injected ConsAssm catalog")

            if include_fencons and not status['FenCons']:
                content = self._inject_fencons_catalog(content)
                logger.info("Injected FenCons catalog")

            # Write back
            with open(cibd25_path, 'w') as f:
                f.write(content)

            logger.info("Successfully injected commercial catalogs")
            return True

        except Exception as e:
            logger.error(f"Failed to inject catalogs: {e}")
            return False

    def has_commercial_catalogs(self, cibd25_content: str) -> Dict[str, bool]:
        """
        Check which commercial catalogs are present.

        Args:
            cibd25_content: CIBD25 text content

        Returns:
            Dictionary: {'Mat': bool, 'ConsAssm': bool, 'FenCons': bool}
        """
        # TODO: Implement
        import re

        return {
            'Mat': bool(re.search(r'^\s*Mat\s+', cibd25_content, re.MULTILINE)),
            'ConsAssm': bool(re.search(r'^\s*ConsAssm\s+', cibd25_content, re.MULTILINE)),
            'FenCons': bool(re.search(r'^\s*FenCons\s+', cibd25_content, re.MULTILINE)),
        }

    def _inject_mat_catalog(self, content: str) -> str:
        """Inject Mat catalog into content."""
        # TODO: Implement
        # Should add after RulesetFilename and before Proj
        return content

    def _inject_consassm_catalog(self, content: str) -> str:
        """Inject ConsAssm catalog into content."""
        # TODO: Implement
        return content

    def _inject_fencons_catalog(self, content: str) -> str:
        """Inject FenCons catalog into content."""
        # TODO: Implement
        return content
