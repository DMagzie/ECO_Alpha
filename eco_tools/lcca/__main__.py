"""
LCCA module entry point for CLI execution.

Usage:
    python -m eco_tools.lcca --help
    python -m eco_tools.lcca discover /path/to/project
    python -m eco_tools.lcca analyze /path/to/project --rate-id PGE-E-ELEC
"""

from .cli import main
import sys

if __name__ == "__main__":
    sys.exit(main())
