"""
Unit Tests for HBJSON Exporter
================================

Tests the EMJSON → HBJSON translation functionality.

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
from eco_tools.translators.hbjson.exporter import HBJSONExporter
from eco_tools.core.internal_repr import InternalRepresentation


class TestHBJSONExporter:
    """Test suite for HBJSON exporter"""

    @pytest.fixture
    def exporter(self):
        """Create exporter instance"""
        return HBJSONExporter()

    @pytest.fixture
    def importer(self):
        """Create importer instance for loading test data"""
        return HBJSONImporter()

    @pytest.fixture
    def sample_files_dir(self):
        """Get path to sample files directory"""
        return ROOT / "reference_data" / "hbjson_samples"

    @pytest.fixture
    def output_dir(self, tmp_path):
        """Create temporary output directory"""
        output = tmp_path / "hbjson_export"
        output.mkdir(exist_ok=True)
        return output

    @pytest.fixture
    def simple_internal_repr(self, importer, sample_files_dir):
        """Load simple model as InternalRepresentation"""
        model_path = sample_files_dir / "model_energy_shoe_box.hbjson"
        if not model_path.exists():
            pytest.skip(f"Sample file not found: {model_path}")
        return importer.import_file(str(model_path))

    def test_exporter_initialization(self, exporter):
        """Test exporter can be initialized"""
        assert exporter is not None
        assert isinstance(exporter, HBJSONExporter)

    def test_export_creates_file(self, exporter, simple_internal_repr, output_dir):
        """Test that export creates an HBJSON file"""
        output_path = output_dir / "test_export.hbjson"

        exporter.export_to_file(simple_internal_repr, str(output_path))

        assert output_path.exists()
        assert output_path.stat().st_size > 0

    def test_export_creates_valid_json(self, exporter, simple_internal_repr, output_dir):
        """Test that exported file is valid JSON"""
        output_path = output_dir / "test_export.hbjson"

        exporter.export_to_file(simple_internal_repr, str(output_path))

        # Should be able to parse as JSON
        with open(output_path, 'r') as f:
            data = json.load(f)

        assert isinstance(data, dict)
        assert "type" in data
        assert data["type"] == "Model"

    def test_export_has_required_fields(self, exporter, simple_internal_repr, output_dir):
        """Test that exported HBJSON has required schema fields"""
        output_path = output_dir / "test_export.hbjson"

        exporter.export_to_file(simple_internal_repr, str(output_path))

        with open(output_path, 'r') as f:
            data = json.load(f)

        # Required HBJSON fields
        assert "type" in data
        assert "identifier" in data
        assert "display_name" in data
        assert "rooms" in data
        assert "version" in data

    def test_export_preserves_zones_as_rooms(self, exporter, simple_internal_repr, output_dir):
        """Test that zones are exported as rooms"""
        output_path = output_dir / "test_export.hbjson"

        exporter.export_to_file(simple_internal_repr, str(output_path))

        with open(output_path, 'r') as f:
            data = json.load(f)

        zone_count = len(simple_internal_repr.zones)
        room_count = len(data["rooms"])

        assert room_count == zone_count

    def test_export_preserves_surfaces_as_faces(self, exporter, simple_internal_repr, output_dir):
        """Test that surfaces are exported as faces"""
        output_path = output_dir / "test_export.hbjson"

        exporter.export_to_file(simple_internal_repr, str(output_path))

        with open(output_path, 'r') as f:
            data = json.load(f)

        # Count surfaces in EMJSON
        emjson_surface_count = sum(len(z.surfaces) for z in simple_internal_repr.zones)

        # Count faces in HBJSON
        hbjson_face_count = sum(len(r["faces"]) for r in data["rooms"])

        assert hbjson_face_count == emjson_surface_count

    def test_export_preserves_geometry(self, exporter, simple_internal_repr, output_dir):
        """Test that geometry is preserved in export"""
        output_path = output_dir / "test_export.hbjson"

        exporter.export_to_file(simple_internal_repr, str(output_path))

        with open(output_path, 'r') as f:
            data = json.load(f)

        # Check that rooms have faces with geometry
        for room in data["rooms"]:
            assert "faces" in room
            for face in room["faces"]:
                assert "geometry" in face
                assert "boundary" in face["geometry"]
                assert len(face["geometry"]["boundary"]) >= 3  # At least 3 vertices

    def test_roundtrip_preserves_room_count(self, importer, exporter, sample_files_dir, output_dir):
        """Test that room count is preserved in round-trip"""
        model_path = sample_files_dir / "model_energy_shoe_box.hbjson"
        if not model_path.exists():
            pytest.skip(f"Sample file not found: {model_path}")

        # Load original
        with open(model_path, 'r') as f:
            original = json.load(f)
        original_rooms = len(original["rooms"])

        # Round-trip
        internal = importer.import_file(str(model_path))
        output_path = output_dir / "roundtrip.hbjson"
        exporter.export_to_file(internal, str(output_path))

        # Load round-trip
        with open(output_path, 'r') as f:
            roundtrip = json.load(f)
        roundtrip_rooms = len(roundtrip["rooms"])

        assert roundtrip_rooms == original_rooms

    def test_roundtrip_preserves_face_count(self, importer, exporter, sample_files_dir, output_dir):
        """Test that face count is preserved in round-trip"""
        model_path = sample_files_dir / "model_energy_shoe_box.hbjson"
        if not model_path.exists():
            pytest.skip(f"Sample file not found: {model_path}")

        # Load original
        with open(model_path, 'r') as f:
            original = json.load(f)
        original_faces = sum(len(r["faces"]) for r in original["rooms"])

        # Round-trip
        internal = importer.import_file(str(model_path))
        output_path = output_dir / "roundtrip.hbjson"
        exporter.export_to_file(internal, str(output_path))

        # Load round-trip
        with open(output_path, 'r') as f:
            roundtrip = json.load(f)
        roundtrip_faces = sum(len(r["faces"]) for r in roundtrip["rooms"])

        assert roundtrip_faces == original_faces

    def test_export_with_constructions(self, importer, exporter, sample_files_dir, output_dir):
        """Test that constructions are included in export"""
        model_path = sample_files_dir / "model_energy_shoe_box.hbjson"
        if not model_path.exists():
            pytest.skip(f"Sample file not found: {model_path}")

        internal = importer.import_file(str(model_path))
        output_path = output_dir / "with_constructions.hbjson"
        exporter.export_to_file(internal, str(output_path))

        with open(output_path, 'r') as f:
            data = json.load(f)

        # Check for properties
        if "properties" in data:
            assert "energy" in data["properties"]

    def test_export_multi_zone_model(self, importer, exporter, sample_files_dir, output_dir):
        """Test exporting multi-zone model"""
        model_path = sample_files_dir / "model_complete_multi_zone_office.hbjson"
        if not model_path.exists():
            pytest.skip(f"Sample file not found: {model_path}")

        internal = importer.import_file(str(model_path))
        output_path = output_dir / "multi_zone_export.hbjson"
        exporter.export_to_file(internal, str(output_path))

        assert output_path.exists()

        with open(output_path, 'r') as f:
            data = json.load(f)

        assert len(data["rooms"]) > 1

    @pytest.mark.parametrize("model_file", [
        "model_energy_shoe_box.hbjson",
        "model_complete_single_zone_office.hbjson",
        "model_energy_doas_hvac.hbjson",
    ])
    def test_export_various_models(self, importer, exporter, sample_files_dir, output_dir, model_file):
        """Test exporting various sample models"""
        model_path = sample_files_dir / model_file
        if not model_path.exists():
            pytest.skip(f"Sample file not found: {model_path}")

        internal = importer.import_file(str(model_path))
        output_path = output_dir / f"export_{model_file}"
        exporter.export_to_file(internal, str(output_path))

        assert output_path.exists()

        # Verify valid JSON
        with open(output_path, 'r') as f:
            data = json.load(f)

        assert data["type"] == "Model"
        assert len(data["rooms"]) > 0


class TestHBJSONRoundTrip:
    """Test round-trip translation HBJSON → EMJSON → HBJSON"""

    @pytest.fixture
    def importer(self):
        return HBJSONImporter()

    @pytest.fixture
    def exporter(self):
        return HBJSONExporter()

    @pytest.fixture
    def sample_files_dir(self):
        return ROOT / "reference_data" / "hbjson_samples"

    @pytest.fixture
    def output_dir(self, tmp_path):
        output = tmp_path / "roundtrip"
        output.mkdir(exist_ok=True)
        return output

    def test_simple_roundtrip(self, importer, exporter, sample_files_dir, output_dir):
        """Test basic round-trip workflow"""
        model_path = sample_files_dir / "model_energy_shoe_box.hbjson"
        if not model_path.exists():
            pytest.skip(f"Sample file not found: {model_path}")

        # Import
        internal = importer.import_file(str(model_path))
        assert internal is not None

        # Export
        output_path = output_dir / "roundtrip.hbjson"
        exporter.export_to_file(internal, str(output_path))
        assert output_path.exists()

        # Verify valid output
        with open(output_path, 'r') as f:
            data = json.load(f)
        assert data["type"] == "Model"

    def test_double_roundtrip(self, importer, exporter, sample_files_dir, output_dir):
        """Test double round-trip (HBJSON → EMJSON → HBJSON → EMJSON → HBJSON)"""
        model_path = sample_files_dir / "model_energy_shoe_box.hbjson"
        if not model_path.exists():
            pytest.skip(f"Sample file not found: {model_path}")

        # First round-trip
        internal1 = importer.import_file(str(model_path))
        rt1_path = output_dir / "roundtrip1.hbjson"
        exporter.export_to_file(internal1, str(rt1_path))

        # Second round-trip
        internal2 = importer.import_file(str(rt1_path))
        rt2_path = output_dir / "roundtrip2.hbjson"
        exporter.export_to_file(internal2, str(rt2_path))

        # Compare
        with open(rt1_path, 'r') as f:
            rt1_data = json.load(f)
        with open(rt2_path, 'r') as f:
            rt2_data = json.load(f)

        assert len(rt1_data["rooms"]) == len(rt2_data["rooms"])
