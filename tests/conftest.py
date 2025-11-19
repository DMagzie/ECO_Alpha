"""
Shared pytest fixtures for ECO Tools test suite
"""

import pytest
from pathlib import Path


@pytest.fixture
def project_root():
    """Path to project root directory"""
    return Path(__file__).parent.parent


@pytest.fixture
def sample_files_dir(project_root):
    """Path to sample files directory"""
    return project_root / "reference_data" / "cbecc" / "CBECC Models"


@pytest.fixture
def all_cibd22x_files(sample_files_dir):
    """List of all CIBD22X sample files"""
    cibd22x_dir = sample_files_dir / "cibd22x"
    if not cibd22x_dir.exists():
        return []
    return list(cibd22x_dir.glob("*.cibd22x"))


@pytest.fixture
def all_cibd25_files(sample_files_dir):
    """List of all CIBD25 sample files"""
    cibd25_dir = sample_files_dir / "2025 Sample Models" / "StandardModelTests"
    if not cibd25_dir.exists():
        return []
    return list(cibd25_dir.glob("*.cibd25"))


@pytest.fixture
def bressi_ranch_file(sample_files_dir):
    """Path to Bressi Ranch (large 290-zone model)"""
    return sample_files_dir / "Bressi Ranch" / "Bressi Ranch Apartments.cibd22x"


@pytest.fixture
def small_office_file(sample_files_dir):
    """Path to small office model (fast testing)"""
    return sample_files_dir / "cibd22x" / "080012-Whse-CECStd.cibd22x"


@pytest.fixture
def small_sample_model(small_office_file):
    """
    Small model for fast testing

    Note: Only imports if file exists, otherwise returns None
    """
    if not small_office_file or not small_office_file.exists():
        pytest.skip(f"Sample file not found: {small_office_file}")

    from eco_tools.translators.cibd22x import CIBD22XImporter
    importer = CIBD22XImporter()
    return importer.import_file(str(small_office_file))


@pytest.fixture
def large_sample_model(bressi_ranch_file):
    """
    Large model (290 zones) for stress testing

    Note: Only imports if file exists, otherwise returns None
    """
    if not bressi_ranch_file or not bressi_ranch_file.exists():
        pytest.skip(f"Sample file not found: {bressi_ranch_file}")

    from eco_tools.translators.cibd22x import CIBD22XImporter
    importer = CIBD22XImporter()
    return importer.import_file(str(bressi_ranch_file))
