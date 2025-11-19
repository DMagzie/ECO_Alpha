"""
Integration Tests: Format Roundtrip Validation
==============================================

Tests that verify we can import files, convert to internal representation,
and export back to the same format with data integrity preserved.

Uses all available sample files for comprehensive coverage.
"""

import pytest
from pathlib import Path


@pytest.mark.integration
class TestCIBD22XRoundtrips:
    """Test CIBD22X import/export roundtrips"""

    @pytest.mark.parametrize("sample_file", [
        "reference_data/cbecc/CBECC Models/Bressi Ranch/Bressi Ranch Apartments.cibd22x",
        "reference_data/cbecc/CBECC Models/cibd22x/El Paseo Building 2_CBECC 2022_2025-08-12.cibd22x",
        "reference_data/cbecc/CBECC Models/cibd22x/El Paseo de Saratoga - Building 1 2025.08-12.cibd22x",
        "reference_data/cbecc/CBECC Models/cibd22x/60-21191-ACM-Mainplace Mall Parcel 3_ResHVAC.cibd22x",
        "reference_data/cbecc/CBECC Models/cibd22x/080012-Whse-CECStd.cibd22x",
        "reference_data/cbecc/CBECC Models/cibd22x/Freedom Circle_Building A - LEED.cibd22x",
        "reference_data/cbecc/CBECC Models/cibd22x/Del Amo Circle-LEED_CBECC2022_2024-12-11.cibd22x",
        "reference_data/cbecc/CBECC Models/cibd22x/Euclid_Bldg B_2024-04-29.cibd22x",
        "reference_data/cbecc/CBECC Models/cibd22x/The Scout Hotel_CBECC 2022.cibd22x",
        "reference_data/cbecc/CBECC Models/cibd22x/Euclid Building A_v3_2024-04-29.cibd22x",
        "reference_data/cbecc/CBECC Models/cibd22x/Freedom Circle Building B - LEED.cibd22x",
        "reference_data/cbecc/CBECC Models/cibd22x/The Scout Hotel_Conference Center.cibd22x",
        "reference_data/cbecc/CBECC Models/cibd22x/Euclid_Building C_2025-01-06.cibd22x",
    ])
    def test_cibd22x_roundtrip(self, sample_file, tmp_path, project_root):
        """Test CIBD22X import and export roundtrip"""
        from eco_tools.translators.cibd22x import CIBD22XImporter, CIBD22XExporter

        input_path = project_root / sample_file

        # Skip if file doesn't exist (may not be in all test environments)
        if not input_path.exists():
            pytest.skip(f"Sample file not found: {sample_file}")

        print(f"\n  Testing: {input_path.name}")

        # Step 1: Import
        importer = CIBD22XImporter()
        model = importer.import_file(str(input_path))

        # Step 2: Validate import
        assert model is not None, "Import failed - model is None"
        assert hasattr(model, 'zones'), "Model missing zones attribute"
        assert len(model.zones) > 0, "Model has no zones"

        zone_count = len(model.zones)
        surface_count = sum(len(z.surfaces) for z in model.zones)

        print(f"    ✓ Imported {zone_count} zones, {surface_count} surfaces")

        # Step 3: Export
        output_file = tmp_path / input_path.name
        exporter = CIBD22XExporter()
        exporter.export_to_file(model, str(output_file))

        # Step 4: Validate export
        assert output_file.exists(), "Export failed - file not created"
        file_size = output_file.stat().st_size
        assert file_size > 1000, f"Export file too small: {file_size} bytes"

        print(f"    ✓ Exported to {file_size:,} bytes")

        # Step 5: Re-import to verify roundtrip
        model2 = importer.import_file(str(output_file))

        assert model2 is not None, "Roundtrip import failed"
        assert len(model2.zones) == zone_count, \
            f"Zone count mismatch: {len(model2.zones)} != {zone_count}"

        print(f"    ✓ Roundtrip verified ({zone_count} zones preserved)")


@pytest.mark.integration
class TestCIBD25Roundtrips:
    """Test CIBD25 import/export roundtrips"""

    @pytest.mark.parametrize("sample_file", [
        "reference_data/cbecc/CBECC Models/2025 Sample Models/StandardModelTests/020012-OffSml-CECStd.cibd25",
        "reference_data/cbecc/CBECC Models/2025 Sample Models/StandardModelTests/080012-Whse-CECStd.cibd25",
        "reference_data/cbecc/CBECC Models/2025 Sample Models/StandardModelTests/060012-RstntSml-CECStd.cibd25",
        "reference_data/cbecc/CBECC Models/2025 Sample Models/StandardModelTests/070012-HotSml-CECStd.cibd25",
        "reference_data/cbecc/CBECC Models/2025 Sample Models/StandardModelTests/010012-SchSml-CECStd.cibd25",
        "reference_data/cbecc/CBECC Models/2025 Sample Models/StandardModelTests/050012-RetlMed-CECStd.cibd25",
        "reference_data/cbecc/CBECC Models/2025 Sample Models/StandardModelTests/030012-OffMed-CECStd.cibd25",
        "reference_data/cbecc/CBECC Models/2025 Sample Models/StandardModelTests/090012-RetlLrg-CECStd.cibd25",
    ])
    def test_cibd25_roundtrip(self, sample_file, tmp_path, project_root):
        """Test CIBD25 import and export roundtrip"""
        from eco_tools.translators.cibd25 import CIBD25Importer, CIBD25Exporter

        input_path = project_root / sample_file

        # Skip if file doesn't exist
        if not input_path.exists():
            pytest.skip(f"Sample file not found: {sample_file}")

        print(f"\n  Testing: {input_path.name}")

        # Step 1: Import
        importer = CIBD25Importer()
        model = importer.import_file(str(input_path))

        # Step 2: Validate import
        assert model is not None, "Import failed - model is None"
        assert hasattr(model, 'zones'), "Model missing zones attribute"
        assert len(model.zones) > 0, "Model has no zones"

        zone_count = len(model.zones)
        surface_count = sum(len(z.surfaces) for z in model.zones)

        print(f"    ✓ Imported {zone_count} zones, {surface_count} surfaces")

        # Step 3: Export
        output_file = tmp_path / input_path.name
        exporter = CIBD25Exporter()
        exporter.export_to_file(model, str(output_file))

        # Step 4: Validate export
        assert output_file.exists(), "Export failed - file not created"
        file_size = output_file.stat().st_size
        assert file_size > 1000, f"Export file too small: {file_size} bytes"

        print(f"    ✓ Exported to {file_size:,} bytes")

        # Step 5: Re-import to verify roundtrip
        model2 = importer.import_file(str(output_file))

        assert model2 is not None, "Roundtrip import failed"
        assert len(model2.zones) == zone_count, \
            f"Zone count mismatch: {len(model2.zones)} != {zone_count}"

        print(f"    ✓ Roundtrip verified ({zone_count} zones preserved)")


@pytest.mark.integration
class TestCrossFormatConversions:
    """Test converting between different formats"""

    def test_cibd22x_to_cibd25(self, small_office_file, tmp_path):
        """Test CIBD22X → CIBD25 conversion"""
        from eco_tools.translators.cibd22x import CIBD22XImporter
        from eco_tools.translators.cibd25 import CIBD25Exporter

        if not small_office_file or not small_office_file.exists():
            pytest.skip("Sample file not available")

        # Import CIBD22X
        importer = CIBD22XImporter()
        model = importer.import_file(str(small_office_file))

        zone_count = len(model.zones)

        # Export to CIBD25
        output_file = tmp_path / "converted.cibd25"
        exporter = CIBD25Exporter()
        exporter.export(model, str(output_file))  # Changed method name

        # Validate
        assert output_file.exists()
        assert output_file.stat().st_size > 1000

        # Re-import to verify
        from eco_tools.translators.cibd25 import CIBD25Importer
        model2 = CIBD25Importer().import_file(str(output_file))

        assert len(model2.zones) == zone_count

    def test_cibd25_to_cibd22x(self, tmp_path, project_root):
        """Test CIBD25 → CIBD22X conversion"""
        from eco_tools.translators.cibd25 import CIBD25Importer
        from eco_tools.translators.cibd22x import CIBD22XExporter

        sample_file = project_root / "reference_data/cbecc/CBECC Models/2025 Sample Models/StandardModelTests/020012-OffSml-CECStd.cibd25"

        if not sample_file.exists():
            pytest.skip("Sample file not available")

        # Import CIBD25
        importer = CIBD25Importer()
        model = importer.import_file(str(sample_file))

        zone_count = len(model.zones)

        # Export to CIBD22X
        output_file = tmp_path / "converted.cibd22x"
        exporter = CIBD22XExporter()
        exporter.export_to_file(model, str(output_file))

        # Validate
        assert output_file.exists()
        assert output_file.stat().st_size > 1000

        # Re-import to verify
        from eco_tools.translators.cibd22x import CIBD22XImporter
        model2 = CIBD22XImporter().import_file(str(output_file))

        assert len(model2.zones) == zone_count


@pytest.mark.integration
class TestDataIntegrity:
    """Test that data is preserved through roundtrips"""

    def test_zone_names_preserved(self, small_sample_model, tmp_path):
        """Test that zone names are preserved"""
        if small_sample_model is None:
            pytest.skip("Sample model not available")

        from eco_tools.translators.cibd22x import CIBD22XExporter, CIBD22XImporter

        # Get original zone names
        original_names = [z.name for z in small_sample_model.zones]

        # Export and re-import
        output_file = tmp_path / "test.cibd22x"
        exporter = CIBD22XExporter()
        exporter.export_to_file(small_sample_model, str(output_file))

        importer = CIBD22XImporter()
        model2 = importer.import_file(str(output_file))

        # Verify names preserved
        new_names = [z.name for z in model2.zones]
        assert len(new_names) == len(original_names)
        # Note: Order may not be preserved, so check sets
        assert set(new_names) == set(original_names)

    def test_surface_counts_preserved(self, small_sample_model, tmp_path):
        """Test that surface counts are preserved"""
        if small_sample_model is None:
            pytest.skip("Sample model not available")

        from eco_tools.translators.cibd22x import CIBD22XExporter, CIBD22XImporter

        # Count original surfaces
        original_surface_count = sum(len(z.surfaces) for z in small_sample_model.zones)

        # Export and re-import
        output_file = tmp_path / "test.cibd22x"
        exporter = CIBD22XExporter()
        exporter.export_to_file(small_sample_model, str(output_file))

        importer = CIBD22XImporter()
        model2 = importer.import_file(str(output_file))

        # Verify surface count preserved
        new_surface_count = sum(len(z.surfaces) for z in model2.zones)
        assert new_surface_count == original_surface_count
