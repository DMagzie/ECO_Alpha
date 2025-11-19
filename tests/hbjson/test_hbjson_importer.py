"""
Unit Tests for HBJSON Importer
================================

Tests the HBJSON → EMJSON translation functionality.

Author: ECO Tools Team
Date: November 14, 2025
"""

import pytest
import sys
from pathlib import Path
import json

# Add project root to path
ROOT = Path(__file__).resolve().parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from eco_tools.translators.hbjson.importer import HBJSONImporter
from eco_tools.core.internal_repr import InternalRepresentation


class TestHBJSONImporter:
    """Test suite for HBJSON importer"""

    @pytest.fixture
    def importer(self):
        """Create importer instance"""
        return HBJSONImporter()

    @pytest.fixture
    def sample_files_dir(self):
        """Get path to sample files directory"""
        return ROOT / "reference_data" / "hbjson_samples"

    @pytest.fixture
    def simple_model_path(self, sample_files_dir):
        """Get path to simple shoe box model"""
        return sample_files_dir / "model_energy_shoe_box.hbjson"

    @pytest.fixture
    def single_zone_path(self, sample_files_dir):
        """Get path to single zone office model"""
        return sample_files_dir / "model_complete_single_zone_office.hbjson"

    def test_importer_initialization(self, importer):
        """Test importer can be initialized"""
        assert importer is not None
        assert isinstance(importer, HBJSONImporter)

    def test_import_simple_model(self, importer, simple_model_path):
        """Test importing simple shoe box model"""
        if not simple_model_path.exists():
            pytest.skip(f"Sample file not found: {simple_model_path}")

        result = importer.import_file(str(simple_model_path))

        assert result is not None
        assert isinstance(result, InternalRepresentation)
        assert hasattr(result, 'zones')
        assert len(result.zones) > 0

    def test_import_creates_zones(self, importer, simple_model_path):
        """Test that import creates zones from HBJSON rooms"""
        if not simple_model_path.exists():
            pytest.skip(f"Sample file not found: {simple_model_path}")

        result = importer.import_file(str(simple_model_path))

        # Shoe box has 1 room
        assert len(result.zones) == 1
        zone = result.zones[0]
        assert zone.name is not None
        assert len(zone.name) > 0

    def test_import_creates_surfaces(self, importer, simple_model_path):
        """Test that import creates surfaces from HBJSON faces"""
        if not simple_model_path.exists():
            pytest.skip(f"Sample file not found: {simple_model_path}")

        result = importer.import_file(str(simple_model_path))

        # Shoe box has 6 faces (walls, floor, ceiling)
        zone = result.zones[0]
        assert hasattr(zone, 'surfaces')
        assert len(zone.surfaces) == 6

    def test_import_preserves_geometry(self, importer, simple_model_path):
        """Test that geometry is preserved during import"""
        if not simple_model_path.exists():
            pytest.skip(f"Sample file not found: {simple_model_path}")

        result = importer.import_file(str(simple_model_path))

        # Check that surfaces have vertices
        zone = result.zones[0]
        for surface in zone.surfaces:
            assert hasattr(surface, 'vertices')
            assert len(surface.vertices) >= 3  # At least 3 vertices for a surface

    def test_import_creates_materials(self, importer, simple_model_path):
        """Test that materials are imported"""
        if not simple_model_path.exists():
            pytest.skip(f"Sample file not found: {simple_model_path}")

        result = importer.import_file(str(simple_model_path))

        assert hasattr(result, 'materials')
        assert len(result.materials) > 0

    def test_import_creates_constructions(self, importer, simple_model_path):
        """Test that constructions are imported"""
        if not simple_model_path.exists():
            pytest.skip(f"Sample file not found: {simple_model_path}")

        result = importer.import_file(str(simple_model_path))

        assert hasattr(result, 'constructions')
        assert len(result.constructions) > 0

    def test_import_single_zone_office(self, importer, single_zone_path):
        """Test importing single zone office with HVAC"""
        if not single_zone_path.exists():
            pytest.skip(f"Sample file not found: {single_zone_path}")

        result = importer.import_file(str(single_zone_path))

        assert result is not None
        assert len(result.zones) == 1

        # Check for HVAC system
        zone = result.zones[0]
        # HVAC system handling depends on implementation
        # Add specific checks based on your EMJSON schema

    def test_import_preserves_openings(self, importer, simple_model_path):
        """Test that windows/doors are imported as openings"""
        if not simple_model_path.exists():
            pytest.skip(f"Sample file not found: {simple_model_path}")

        result = importer.import_file(str(simple_model_path))

        # Shoe box has 2 windows
        zone = result.zones[0]
        opening_count = 0
        for surface in zone.surfaces:
            if hasattr(surface, 'openings'):
                opening_count += len(surface.openings)

        assert opening_count == 2

    def test_import_invalid_file_path(self, importer):
        """Test error handling for invalid file path"""
        with pytest.raises(Exception):
            importer.import_file("nonexistent_file.hbjson")

    def test_import_invalid_json(self, importer, tmp_path):
        """Test error handling for invalid JSON"""
        bad_file = tmp_path / "bad.hbjson"
        bad_file.write_text("not valid json {")

        with pytest.raises(Exception):
            importer.import_file(str(bad_file))

    def test_import_multi_zone_model(self, importer, sample_files_dir):
        """Test importing multi-zone office model"""
        multi_zone_path = sample_files_dir / "model_complete_multi_zone_office.hbjson"

        if not multi_zone_path.exists():
            pytest.skip(f"Sample file not found: {multi_zone_path}")

        result = importer.import_file(str(multi_zone_path))

        assert result is not None
        assert len(result.zones) > 1  # Should have multiple zones

    def test_import_file_with_hvac(self, importer, sample_files_dir):
        """Test importing model with HVAC systems"""
        hvac_path = sample_files_dir / "model_energy_doas_hvac.hbjson"

        if not hvac_path.exists():
            pytest.skip(f"Sample file not found: {hvac_path}")

        result = importer.import_file(str(hvac_path))

        assert result is not None
        # Check for HVAC-related properties
        # Exact checks depend on EMJSON schema

    @pytest.mark.parametrize("model_file", [
        "model_energy_shoe_box.hbjson",
        "model_complete_single_zone_office.hbjson",
        "model_energy_doas_hvac.hbjson",
        "model_complete_multi_zone_office.hbjson",
    ])
    def test_import_sample_models(self, importer, sample_files_dir, model_file):
        """Test importing various sample models"""
        model_path = sample_files_dir / model_file

        if not model_path.exists():
            pytest.skip(f"Sample file not found: {model_path}")

        result = importer.import_file(str(model_path))

        assert result is not None
        assert isinstance(result, InternalRepresentation)
        assert len(result.zones) > 0
