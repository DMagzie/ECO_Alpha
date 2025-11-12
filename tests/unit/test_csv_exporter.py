"""
Unit Tests for CSV Exporter
===========================

Tests for eco_tools.reporting.csv_exporter module
"""

import pytest
import csv
from pathlib import Path
from datetime import datetime
from eco_tools.reporting.csv_exporter import (
    export_cbecc_results_to_csv,
    export_energyplus_results_to_csv,
    export_comparison_to_csv
)


# Fixtures

@pytest.fixture
def sample_cbecc_results():
    """Sample CBECC results dictionary"""
    return {
        "status": "Success",
        "project_name": "Test Building",
        "climate_zone": "CZ12",
        "building_area": 50000.0,
        "compliance_status": "Pass",
        "proposed_tdv": 250000.0,
        "standard_tdv": 280000.0,
        "tdv_margin": 10.71,
        "end_uses": {
            "space_heating": 8.5,
            "space_cooling": 18.2,
            "indoor_fans": 4.3,
            "indoor_lighting": 10.5,
            "equipment": 15.0,
            "dhw": 2.1
        }
    }


@pytest.fixture
def sample_energyplus_results():
    """Sample EnergyPlus results dictionary"""
    return {
        "status": "Success",
        "eui": 59.2,
        "total_energy_kwh": 2960000.0,
        "building_area_m2": 4645.15,
        "end_uses": {
            "space_heating": 9.1,
            "space_cooling": 17.8,
            "indoor_fans": 4.5,
            "indoor_lighting": 10.8,
            "equipment": 14.8,
            "dhw": 2.3
        },
        "errors": [],
        "warnings": ["Minor warning example"]
    }


@pytest.fixture
def incomplete_cbecc_results():
    """Incomplete CBECC results (simulation not run)"""
    return {
        "status": "Success",
        "project_name": "Incomplete Building",
        "climate_zone": "CZ06",
        "building_area": 25000.0,
        "compliance_status": "Unknown",
        "end_uses": {}
    }


# Test CBECC Export

class TestExportCBECCResults:
    """Test suite for export_cbecc_results_to_csv()"""

    def test_export_complete_results(self, tmp_path, sample_cbecc_results):
        """Test exporting complete CBECC results"""
        output_file = tmp_path / "cbecc_test.csv"

        export_cbecc_results_to_csv(sample_cbecc_results, str(output_file))

        assert output_file.exists()
        assert output_file.stat().st_size > 0

    def test_csv_structure(self, tmp_path, sample_cbecc_results):
        """Test CSV file structure"""
        output_file = tmp_path / "cbecc_structure.csv"

        export_cbecc_results_to_csv(sample_cbecc_results, str(output_file))

        with open(output_file, 'r') as f:
            content = f.read()

        # Check for main sections
        assert "CBECC-Com Results" in content
        assert "Project Information" in content
        assert "Title 24 Compliance" in content
        assert "Energy End Uses" in content

    def test_csv_metadata(self, tmp_path, sample_cbecc_results):
        """Test CSV contains metadata"""
        output_file = tmp_path / "cbecc_metadata.csv"

        export_cbecc_results_to_csv(sample_cbecc_results, str(output_file))

        with open(output_file, 'r') as f:
            lines = f.readlines()

        # First line should be title
        assert "CBECC-Com Results" in lines[0]

        # Should have timestamp
        content = ''.join(lines)
        assert "Generated" in content

    def test_csv_project_info(self, tmp_path, sample_cbecc_results):
        """Test CSV contains project information"""
        output_file = tmp_path / "cbecc_project.csv"

        export_cbecc_results_to_csv(sample_cbecc_results, str(output_file))

        with open(output_file, 'r') as f:
            content = f.read()

        assert sample_cbecc_results["project_name"] in content
        assert sample_cbecc_results["climate_zone"] in content
        assert str(sample_cbecc_results["building_area"]) in content

    def test_csv_compliance_data(self, tmp_path, sample_cbecc_results):
        """Test CSV contains compliance data"""
        output_file = tmp_path / "cbecc_compliance.csv"

        export_cbecc_results_to_csv(sample_cbecc_results, str(output_file))

        with open(output_file, 'r') as f:
            content = f.read()

        assert sample_cbecc_results["compliance_status"] in content
        assert str(sample_cbecc_results["proposed_tdv"]) in content
        assert str(sample_cbecc_results["standard_tdv"]) in content

    def test_csv_end_uses(self, tmp_path, sample_cbecc_results):
        """Test CSV contains end use data"""
        output_file = tmp_path / "cbecc_end_uses.csv"

        export_cbecc_results_to_csv(sample_cbecc_results, str(output_file))

        with open(output_file, 'r') as f:
            content = f.read()

        for end_use, value in sample_cbecc_results["end_uses"].items():
            # Check that end use name appears (formatted)
            formatted_name = end_use.replace("_", " ").title()
            assert formatted_name in content

    def test_export_incomplete_results(self, tmp_path, incomplete_cbecc_results):
        """Test exporting incomplete CBECC results"""
        output_file = tmp_path / "cbecc_incomplete.csv"

        export_cbecc_results_to_csv(incomplete_cbecc_results, str(output_file))

        assert output_file.exists()

        with open(output_file, 'r') as f:
            content = f.read()

        assert "Unknown" in content  # Compliance status

    def test_export_to_nonexistent_directory(self, tmp_path, sample_cbecc_results):
        """Test exporting to nonexistent directory creates it"""
        output_file = tmp_path / "subdir" / "cbecc.csv"

        # Directory doesn't exist yet
        assert not output_file.parent.exists()

        export_cbecc_results_to_csv(sample_cbecc_results, str(output_file))

        # Directory should be created
        assert output_file.parent.exists()
        assert output_file.exists()

    def test_csv_is_valid_format(self, tmp_path, sample_cbecc_results):
        """Test that exported CSV is valid and parseable"""
        output_file = tmp_path / "cbecc_valid.csv"

        export_cbecc_results_to_csv(sample_cbecc_results, str(output_file))

        # Should be able to read as CSV without errors
        with open(output_file, 'r') as f:
            reader = csv.reader(f)
            rows = list(reader)

        assert len(rows) > 0


# Test EnergyPlus Export

class TestExportEnergyPlusResults:
    """Test suite for export_energyplus_results_to_csv()"""

    def test_export_complete_results(self, tmp_path, sample_energyplus_results):
        """Test exporting complete EnergyPlus results"""
        output_file = tmp_path / "energyplus_test.csv"

        export_energyplus_results_to_csv(sample_energyplus_results, str(output_file))

        assert output_file.exists()
        assert output_file.stat().st_size > 0

    def test_csv_structure(self, tmp_path, sample_energyplus_results):
        """Test CSV file structure"""
        output_file = tmp_path / "energyplus_structure.csv"

        export_energyplus_results_to_csv(sample_energyplus_results, str(output_file))

        with open(output_file, 'r') as f:
            content = f.read()

        assert "EnergyPlus Results" in content
        assert "Summary Metrics" in content
        assert "Energy End Uses" in content

    def test_csv_summary_metrics(self, tmp_path, sample_energyplus_results):
        """Test CSV contains summary metrics"""
        output_file = tmp_path / "energyplus_metrics.csv"

        export_energyplus_results_to_csv(sample_energyplus_results, str(output_file))

        with open(output_file, 'r') as f:
            content = f.read()

        assert str(sample_energyplus_results["eui"]) in content
        assert str(sample_energyplus_results["total_energy_kwh"]) in content

    def test_csv_end_uses(self, tmp_path, sample_energyplus_results):
        """Test CSV contains end use data"""
        output_file = tmp_path / "energyplus_end_uses.csv"

        export_energyplus_results_to_csv(sample_energyplus_results, str(output_file))

        with open(output_file, 'r') as f:
            content = f.read()

        for end_use in sample_energyplus_results["end_uses"].keys():
            formatted_name = end_use.replace("_", " ").title()
            assert formatted_name in content

    def test_csv_warnings(self, tmp_path, sample_energyplus_results):
        """Test CSV includes warnings"""
        output_file = tmp_path / "energyplus_warnings.csv"

        export_energyplus_results_to_csv(sample_energyplus_results, str(output_file))

        with open(output_file, 'r') as f:
            content = f.read()

        if sample_energyplus_results.get("warnings"):
            assert "Warnings" in content


# Test Comparison Export

class TestExportComparison:
    """Test suite for export_comparison_to_csv()"""

    def test_export_comparison(self, tmp_path, sample_cbecc_results, sample_energyplus_results):
        """Test exporting comparison results"""
        output_file = tmp_path / "comparison_test.csv"

        export_comparison_to_csv(
            sample_cbecc_results,
            sample_energyplus_results,
            str(output_file)
        )

        assert output_file.exists()
        assert output_file.stat().st_size > 0

    def test_comparison_structure(self, tmp_path, sample_cbecc_results, sample_energyplus_results):
        """Test comparison CSV structure"""
        output_file = tmp_path / "comparison_structure.csv"

        export_comparison_to_csv(
            sample_cbecc_results,
            sample_energyplus_results,
            str(output_file)
        )

        with open(output_file, 'r') as f:
            content = f.read()

        assert "Simulation Comparison" in content
        assert "Summary" in content
        assert "End Use Comparison" in content

    def test_comparison_headers(self, tmp_path, sample_cbecc_results, sample_energyplus_results):
        """Test comparison CSV has correct headers"""
        output_file = tmp_path / "comparison_headers.csv"

        export_comparison_to_csv(
            sample_cbecc_results,
            sample_energyplus_results,
            str(output_file)
        )

        with open(output_file, 'r') as f:
            content = f.read()

        # Should have columns for both engines
        assert "CBECC" in content
        assert "EnergyPlus" in content
        assert "Delta" in content

    def test_comparison_delta_calculations(self, tmp_path, sample_cbecc_results, sample_energyplus_results):
        """Test that comparison includes delta calculations"""
        output_file = tmp_path / "comparison_deltas.csv"

        export_comparison_to_csv(
            sample_cbecc_results,
            sample_energyplus_results,
            str(output_file)
        )

        with open(output_file, 'r') as f:
            content = f.read()

        # Delta should be present
        assert "Delta" in content or "Difference" in content

    def test_comparison_percentage_difference(self, tmp_path, sample_cbecc_results, sample_energyplus_results):
        """Test that comparison includes percentage differences"""
        output_file = tmp_path / "comparison_percent.csv"

        export_comparison_to_csv(
            sample_cbecc_results,
            sample_energyplus_results,
            str(output_file)
        )

        with open(output_file, 'r') as f:
            content = f.read()

        # Should have percentage values
        assert "%" in content

    def test_comparison_all_end_uses(self, tmp_path, sample_cbecc_results, sample_energyplus_results):
        """Test that comparison includes all end uses from both sources"""
        output_file = tmp_path / "comparison_all_uses.csv"

        export_comparison_to_csv(
            sample_cbecc_results,
            sample_energyplus_results,
            str(output_file)
        )

        with open(output_file, 'r') as f:
            content = f.read()

        # Check for end uses from both sources
        all_end_uses = set(
            list(sample_cbecc_results["end_uses"].keys()) +
            list(sample_energyplus_results["end_uses"].keys())
        )

        for end_use in all_end_uses:
            formatted_name = end_use.replace("_", " ").title()
            assert formatted_name in content


# Integration Tests

class TestCSVExporterIntegration:
    """Integration tests for CSV export functionality"""

    def test_export_all_types(self, tmp_path, sample_cbecc_results, sample_energyplus_results):
        """Test exporting all three CSV types"""
        cbecc_file = tmp_path / "cbecc.csv"
        ep_file = tmp_path / "energyplus.csv"
        comp_file = tmp_path / "comparison.csv"

        export_cbecc_results_to_csv(sample_cbecc_results, str(cbecc_file))
        export_energyplus_results_to_csv(sample_energyplus_results, str(ep_file))
        export_comparison_to_csv(sample_cbecc_results, sample_energyplus_results, str(comp_file))

        assert cbecc_file.exists()
        assert ep_file.exists()
        assert comp_file.exists()

        # All files should have content
        assert cbecc_file.stat().st_size > 0
        assert ep_file.stat().st_size > 0
        assert comp_file.stat().st_size > 0

    def test_realistic_workflow(self, tmp_path):
        """Test realistic export workflow with typical building"""
        # Typical office building results
        cbecc = {
            "status": "Success",
            "project_name": "Typical Office Building",
            "climate_zone": "CZ12",
            "building_area": 50000.0,
            "compliance_status": "Pass",
            "proposed_tdv": 250000.0,
            "standard_tdv": 280000.0,
            "tdv_margin": 10.71,
            "end_uses": {
                "space_heating": 8.5,
                "space_cooling": 18.2,
                "indoor_fans": 4.3,
                "indoor_lighting": 10.5,
                "equipment": 15.0,
                "dhw": 2.1,
                "pumps": 1.8,
                "heat_rejection": 0.9
            }
        }

        energyplus = {
            "status": "Success",
            "eui": 61.3,
            "total_energy_kwh": 3065000.0,
            "building_area_m2": 4645.15,
            "end_uses": {
                "space_heating": 9.1,
                "space_cooling": 17.8,
                "indoor_fans": 4.5,
                "indoor_lighting": 10.8,
                "equipment": 14.8,
                "dhw": 2.3,
                "pumps": 1.9,
                "heat_rejection": 1.0
            },
            "errors": [],
            "warnings": []
        }

        output_file = tmp_path / "realistic_comparison.csv"

        export_comparison_to_csv(cbecc, energyplus, str(output_file))

        assert output_file.exists()

        # Verify all end uses are present
        with open(output_file, 'r') as f:
            content = f.read()

        assert "Space Heating" in content
        assert "Space Cooling" in content
        assert "Equipment" in content


# Edge Cases

class TestCSVExporterEdgeCases:
    """Test edge cases and error handling"""

    def test_export_with_missing_end_uses(self, tmp_path):
        """Test export when end uses are missing"""
        results = {
            "status": "Success",
            "project_name": "Test",
            "climate_zone": "CZ12",
            "building_area": 10000.0,
            "compliance_status": "Pass",
            "end_uses": {}
        }

        output_file = tmp_path / "no_end_uses.csv"

        export_cbecc_results_to_csv(results, str(output_file))

        assert output_file.exists()

    def test_export_with_none_values(self, tmp_path):
        """Test export when some values are None"""
        results = {
            "status": "Success",
            "project_name": "Test",
            "climate_zone": None,
            "building_area": None,
            "compliance_status": "Unknown",
            "proposed_tdv": None,
            "standard_tdv": None,
            "tdv_margin": None,
            "end_uses": {}
        }

        output_file = tmp_path / "none_values.csv"

        export_cbecc_results_to_csv(results, str(output_file))

        assert output_file.exists()

    def test_export_with_special_characters(self, tmp_path):
        """Test export with special characters in project name"""
        results = {
            "status": "Success",
            "project_name": "Building & Office, Inc. (2025)",
            "climate_zone": "CZ12",
            "building_area": 10000.0,
            "compliance_status": "Pass",
            "end_uses": {"space_heating": 10.0}
        }

        output_file = tmp_path / "special_chars.csv"

        export_cbecc_results_to_csv(results, str(output_file))

        assert output_file.exists()

        with open(output_file, 'r') as f:
            content = f.read()

        assert "Building & Office, Inc. (2025)" in content

    def test_export_with_very_long_project_name(self, tmp_path):
        """Test export with very long project name"""
        results = {
            "status": "Success",
            "project_name": "A" * 500,  # 500 character name
            "climate_zone": "CZ12",
            "building_area": 10000.0,
            "compliance_status": "Pass",
            "end_uses": {}
        }

        output_file = tmp_path / "long_name.csv"

        export_cbecc_results_to_csv(results, str(output_file))

        assert output_file.exists()

    def test_overwrite_existing_file(self, tmp_path, sample_cbecc_results):
        """Test that export overwrites existing file"""
        output_file = tmp_path / "overwrite.csv"

        # Create initial file
        output_file.write_text("initial content")
        initial_size = output_file.stat().st_size

        # Export should overwrite
        export_cbecc_results_to_csv(sample_cbecc_results, str(output_file))

        # Size should be different
        assert output_file.stat().st_size != initial_size

    def test_export_with_unicode_characters(self, tmp_path):
        """Test export with unicode characters"""
        results = {
            "status": "Success",
            "project_name": "Edificio São Paulo",
            "climate_zone": "CZ06",
            "building_area": 10000.0,
            "compliance_status": "Pass",
            "end_uses": {}
        }

        output_file = tmp_path / "unicode.csv"

        export_cbecc_results_to_csv(results, str(output_file))

        assert output_file.exists()

        # Should be readable
        with open(output_file, 'r', encoding='utf-8') as f:
            content = f.read()

        assert "São Paulo" in content or "Sao Paulo" in content
