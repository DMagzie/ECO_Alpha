"""
ECO Alpha v7 - Energy Compliance and Optimization Tools
========================================================

A clean, production-ready building energy modeling platform supporting:
- CIBD22X (CBECC-Com) round-trip translation
- 3D Geometry Builder
- Streamlit GUI for model creation and editing
- Future: GEM, HBJSON, EnergyPlus, and CBECC simulation
"""

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="eco-alpha-v7",
    version="7.0.0-alpha",
    author="Energy Modeling Team",
    description="Building energy modeling and Title 24 compliance tools",
    long_description=long_description,
    long_description_content_type="text/markdown",
    packages=find_packages(),
    python_requires=">=3.9",
    install_requires=[
        "dataclasses-json>=0.6.0",
        "pydantic>=2.0.0",
        "numpy>=1.24.0",
        "plotly>=5.17.0",
        "streamlit>=1.28.0",
        "pandas>=2.0.0",
        "lxml>=4.9.0",
        "xmltodict>=0.13.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.4.0",
            "black>=23.7.0",
            "mypy>=1.5.0",
        ],
        "ladybug": [
            "ladybug-core>=0.41.0",
            "ladybug-geometry>=1.26.0",
            "honeybee-core>=1.56.0",
            "honeybee-energy>=1.106.0",
            "honeybee-radiance>=1.66.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "eco-gui=gui.main:main",
        ],
    },
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Science/Research",
        "Topic :: Scientific/Engineering",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
)
