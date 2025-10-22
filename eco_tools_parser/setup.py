"""
ECO Tools - Universal CBECC Parser and Translator
Setup configuration for package installation
"""

from setuptools import setup, find_packages

setup(
    name="eco-tools",
    version="1.0.0",
    author="ECO Tools Development Team",
    description="Universal parser and translator for CBECC file formats",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    packages=find_packages(),
    python_requires=">=3.8",
    install_requires=[
        "openpyxl>=3.0.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-cov>=3.0.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "eco-translate=eco_tools.cli.translate:main",
            "eco-validate=eco_tools.cli.validate:main",
            "eco-info=eco_tools.cli.info:main",
        ],
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
)
