# FILE 1: em-tools/setup.py
# ============================================================================
"""Setup configuration for EM-Tools package."""

from setuptools import setup, find_packages
from pathlib import Path

readme = Path(__file__).parent / "README.md"
long_description = readme.read_text() if readme.exists() else ""

setup(
    name="emtools",
    version="0.6.0",
    description="Energy Modeling Translation Hub - EMJSON v6",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="Your Name",
    packages=find_packages(),
    install_requires=[
        "lxml>=4.9.0",
    ],
    extras_require={
        'gui': [
            "streamlit>=1.28.0",
        ],
        'dev': [
            "pytest>=7.4.0",
            "pytest-cov>=4.1.0",
        ],
    },
    python_requires=">=3.10",
    entry_points={
        'console_scripts': [
            'emtools-translate=emtools.cli:translate',
            'emtools-roundtrip=emtools.cli:roundtrip',
        ],
    },
)