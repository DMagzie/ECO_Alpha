"""
Phase 6 Integration Tests.

Tests for:
- Auto-discovery of simulation outputs
- LCCA workflow runner
- CLI functionality
- End-to-end workflow integration
"""

import pytest
import tempfile
import os
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

# Import Phase 6 components
from eco_tools.lcca.auto_discovery import (
    SimulationFileType,
    SimulationFile,
    DiscoveredOutputs,
    discover_simulation_outputs,
    discover_multiple_projects,
    format_discovery_summary,
    discover_and_validate,
    _match_file,
)

from eco_tools.lcca.lcca_runner import (
    OutputFormat,
    AnalysisMode,
    RunnerConfig,
    RunnerResults,
    LccaRunner,
    run_lcca_workflow,
    batch_lcca,
)


class TestSimulationFileType:
    """Tests for SimulationFileType enum."""

    def test_all_types_defined(self):
        """Verify all file types are defined."""
        expected = [
            "HOURLY_RESULTS",
            "CSE_HOURLY",
            "PV_BATTERY",
            "NRCCPRF",
            "CUAC",
            "CIBD_MODEL",
        ]
        for name in expected:
            assert hasattr(SimulationFileType, name)

    def test_values(self):
        """Test enum values."""
        assert SimulationFileType.HOURLY_RESULTS.value == "hourly_results"
        assert SimulationFileType.CSE_HOURLY.value == "cse_hourly"


class TestFilePatternMatching:
    """Tests for file pattern matching."""

    def test_match_hourly_results_proposed(self):
        """Match proposed HourlyResults file."""
        result = _match_file("ProjectName - ap - HourlyResults.csv")
        assert result is not None
        file_type, project_name, scenario = result
        assert file_type == SimulationFileType.HOURLY_RESULTS
        assert project_name == "ProjectName"
        assert scenario == "proposed"

    def test_match_hourly_results_standard(self):
        """Match standard HourlyResults file."""
        result = _match_file("My Project - ab - HourlyResults.csv")
        assert result is not None
        file_type, project_name, scenario = result
        assert file_type == SimulationFileType.HOURLY_RESULTS
        assert project_name == "My Project"
        assert scenario == "standard"

    def test_match_cse_csv(self):
        """Match CSE CSV file."""
        result = _match_file("Project - CSE.CSV")
        assert result is not None
        file_type, project_name, scenario = result
        assert file_type == SimulationFileType.CSE_HOURLY
        assert project_name == "Project"

    def test_match_pv_battery(self):
        """Match PVBattery file."""
        result = _match_file("Building - PVBattery.csv")
        assert result is not None
        file_type, project_name, scenario = result
        assert file_type == SimulationFileType.PV_BATTERY

    def test_match_nrccprf(self):
        """Match NRCCPRF XML file."""
        result = _match_file("Project - NRCCPRF.xml")
        assert result is not None
        file_type, project_name, scenario = result
        assert file_type == SimulationFileType.NRCCPRF

    def test_match_cuac(self):
        """Match CUAC CSV file."""
        result = _match_file("Project_CUAC.csv")
        assert result is not None
        file_type, project_name, scenario = result
        assert file_type == SimulationFileType.CUAC

    def test_match_cibd_model(self):
        """Match CIBD model file."""
        result = _match_file("Project.cibd25")
        assert result is not None
        file_type, project_name, scenario = result
        assert file_type == SimulationFileType.CIBD_MODEL

    def test_no_match_random_file(self):
        """No match for random file."""
        result = _match_file("random_file.txt")
        assert result is None

    def test_no_match_similar_but_wrong(self):
        """No match for similar but incorrect pattern."""
        result = _match_file("Project-HourlyResults.csv")  # Missing scenario prefix
        assert result is None


class TestSimulationFile:
    """Tests for SimulationFile dataclass."""

    def test_create_simulation_file(self):
        """Test creating SimulationFile."""
        with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as f:
            f.write(b"test data")
            temp_path = Path(f.name)

        try:
            sf = SimulationFile(
                path=temp_path,
                file_type=SimulationFileType.HOURLY_RESULTS,
                scenario="proposed",
                project_name="Test Project",
            )

            assert sf.exists
            assert sf.size_kb > 0
            assert sf.project_name == "Test Project"
        finally:
            temp_path.unlink()

    def test_nonexistent_file(self):
        """Test handling nonexistent file."""
        sf = SimulationFile(
            path=Path("/nonexistent/path.csv"),
            file_type=SimulationFileType.HOURLY_RESULTS,
            scenario="proposed",
            project_name="Test",
        )

        assert not sf.exists
        assert sf.size_kb == 0.0


class TestDiscoveredOutputs:
    """Tests for DiscoveredOutputs dataclass."""

    def test_empty_outputs(self):
        """Test empty outputs."""
        outputs = DiscoveredOutputs(
            project_name="Test",
            project_dir=Path("/test"),
        )

        assert not outputs.is_complete
        assert not outputs.has_comparison
        assert not outputs.has_tou_data
        assert not outputs.has_pv_battery
        assert not outputs.has_cuac
        assert outputs.all_files == []

    def test_complete_outputs(self):
        """Test complete outputs."""
        mock_file = SimulationFile(
            path=Path("/test/file.csv"),
            file_type=SimulationFileType.HOURLY_RESULTS,
            scenario="proposed",
            project_name="Test",
        )

        outputs = DiscoveredOutputs(
            project_name="Test",
            project_dir=Path("/test"),
            hourly_results_proposed=mock_file,
        )

        assert outputs.is_complete

    def test_has_comparison(self):
        """Test comparison detection."""
        mock_proposed = SimulationFile(
            path=Path("/test/ap.csv"),
            file_type=SimulationFileType.HOURLY_RESULTS,
            scenario="proposed",
            project_name="Test",
        )
        mock_standard = SimulationFile(
            path=Path("/test/ab.csv"),
            file_type=SimulationFileType.HOURLY_RESULTS,
            scenario="standard",
            project_name="Test",
        )

        outputs = DiscoveredOutputs(
            project_name="Test",
            project_dir=Path("/test"),
            hourly_results_proposed=mock_proposed,
            hourly_results_standard=mock_standard,
        )

        assert outputs.has_comparison

    def test_summary(self):
        """Test summary generation."""
        outputs = DiscoveredOutputs(
            project_name="Test Project",
            project_dir=Path("/test/dir"),
        )

        summary = outputs.summary()
        assert summary["project_name"] == "Test Project"
        assert "is_complete" in summary
        assert "file_count" in summary


class TestDiscoverSimulationOutputs:
    """Tests for discover_simulation_outputs function."""

    def test_discover_empty_directory(self):
        """Test discovery in empty directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            outputs = discover_simulation_outputs(tmpdir)
            assert outputs.project_name == Path(tmpdir).name
            assert not outputs.is_complete
            assert len(outputs.all_files) == 0

    def test_discover_with_hourly_results(self):
        """Test discovery with HourlyResults file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a mock HourlyResults file
            hr_file = Path(tmpdir) / "TestProject - ap - HourlyResults.csv"
            hr_file.write_text("Mon,Day,Hr,Total\n1,1,1,100.0")

            outputs = discover_simulation_outputs(tmpdir)

            assert outputs.is_complete
            assert outputs.hourly_results_proposed is not None
            assert outputs.project_name == "TestProject"

    def test_discover_with_multiple_files(self):
        """Test discovery with multiple file types."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create mock files
            (Path(tmpdir) / "Project - ap - HourlyResults.csv").write_text("data")
            (Path(tmpdir) / "Project - ab - HourlyResults.csv").write_text("data")
            (Path(tmpdir) / "Project - CSE.CSV").write_text("data")
            (Path(tmpdir) / "Project - PVBattery.csv").write_text("data")

            outputs = discover_simulation_outputs(tmpdir)

            assert outputs.is_complete
            assert outputs.has_comparison
            assert outputs.cse_proposed is not None
            assert outputs.pv_battery is not None
            assert len(outputs.all_files) == 4

    def test_discover_in_run_folder(self):
        """Test discovery in run subfolder."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create run folder structure
            run_folder = Path(tmpdir) / "run"
            run_folder.mkdir()
            (run_folder / "Project - ap - HourlyResults.csv").write_text("data")

            outputs = discover_simulation_outputs(tmpdir)

            assert outputs.is_complete
            assert outputs.run_folder == run_folder

    def test_discover_nonexistent_directory(self):
        """Test discovery in nonexistent directory."""
        with pytest.raises(FileNotFoundError):
            discover_simulation_outputs("/nonexistent/path")

    def test_discover_file_instead_of_directory(self):
        """Test discovery with file path instead of directory."""
        with tempfile.NamedTemporaryFile() as f:
            with pytest.raises(ValueError):
                discover_simulation_outputs(f.name)


class TestFormatDiscoverySummary:
    """Tests for format_discovery_summary function."""

    def test_format_empty_outputs(self):
        """Test formatting empty outputs."""
        outputs = DiscoveredOutputs(
            project_name="Test",
            project_dir=Path("/test"),
        )

        summary = format_discovery_summary(outputs)
        assert "Test" in summary
        assert "NOT FOUND" in summary
        assert "Complete: No" in summary

    def test_format_complete_outputs(self):
        """Test formatting complete outputs."""
        mock_file = SimulationFile(
            path=Path("/test/file.csv"),
            file_type=SimulationFileType.HOURLY_RESULTS,
            scenario="proposed",
            project_name="Test",
        )

        outputs = DiscoveredOutputs(
            project_name="Test Project",
            project_dir=Path("/test"),
            hourly_results_proposed=mock_file,
        )

        summary = format_discovery_summary(outputs)
        assert "Test Project" in summary
        assert "[✓]" in summary
        assert "Complete: Yes" in summary


class TestDiscoverAndValidate:
    """Tests for discover_and_validate function."""

    def test_validate_complete_outputs(self):
        """Test validation of complete outputs."""
        with tempfile.TemporaryDirectory() as tmpdir:
            (Path(tmpdir) / "Test - ap - HourlyResults.csv").write_text("data")

            outputs = discover_and_validate(tmpdir)
            assert outputs.is_complete

    def test_validate_incomplete_outputs(self):
        """Test validation fails for incomplete outputs."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with pytest.raises(ValueError, match="Incomplete"):
                discover_and_validate(tmpdir)

    def test_validate_require_comparison(self):
        """Test validation with require_comparison flag."""
        with tempfile.TemporaryDirectory() as tmpdir:
            (Path(tmpdir) / "Test - ap - HourlyResults.csv").write_text("data")

            with pytest.raises(ValueError, match="standard"):
                discover_and_validate(tmpdir, require_comparison=True)


class TestRunnerConfig:
    """Tests for RunnerConfig dataclass."""

    def test_default_config(self):
        """Test default configuration values."""
        config = RunnerConfig()

        assert config.analysis_period == 30
        assert config.discount_rate == 0.05
        assert config.gas_rate == 1.50
        assert config.mode == AnalysisMode.TOU
        assert config.capex == 0.0

    def test_custom_config(self):
        """Test custom configuration."""
        config = RunnerConfig(
            rate_id="PGE-E-ELEC",
            region="US-CA-SF",
            analysis_period=25,
            discount_rate=0.06,
        )

        assert config.rate_id == "PGE-E-ELEC"
        assert config.region == "US-CA-SF"
        assert config.analysis_period == 25
        assert config.discount_rate == 0.06


class TestRunnerResults:
    """Tests for RunnerResults dataclass."""

    def test_empty_results(self):
        """Test empty results."""
        results = RunnerResults()

        assert results.project_name == ""
        assert results.lcca_results is None
        assert results.output_files == []
        assert results.warnings == []

    def test_results_summary(self):
        """Test results summary generation."""
        results = RunnerResults(
            project_name="Test",
            climate_zone="CZ12",
            region="US-CA-SAC",
            rate_id="PGE-E-ELEC",
        )

        summary = results.summary()
        assert summary["project_name"] == "Test"
        assert summary["climate_zone"] == "CZ12"
        assert summary["region"] == "US-CA-SAC"


class TestLccaRunner:
    """Tests for LccaRunner class."""

    def test_create_runner(self):
        """Test creating runner."""
        with tempfile.TemporaryDirectory() as tmpdir:
            runner = LccaRunner(tmpdir, auto_discover=False)

            assert runner.project_dir == Path(tmpdir)
            assert runner.outputs is None
            assert runner.simulation is None

    def test_runner_discover(self):
        """Test runner discovery."""
        with tempfile.TemporaryDirectory() as tmpdir:
            (Path(tmpdir) / "Test - ap - HourlyResults.csv").write_text("data")

            runner = LccaRunner(tmpdir)

            assert runner.outputs is not None
            assert runner.outputs.is_complete

    def test_runner_configure(self):
        """Test runner configuration."""
        with tempfile.TemporaryDirectory() as tmpdir:
            runner = LccaRunner(tmpdir, auto_discover=False)

            runner.configure(
                rate_id="SCE-TOU-GS3",
                region="US-CA-LA",
                capex=50000,
            )

            assert runner.config.rate_id == "SCE-TOU-GS3"
            assert runner.config.region == "US-CA-LA"
            assert runner.config.capex == 50000

    def test_runner_configure_chaining(self):
        """Test configuration method chaining."""
        with tempfile.TemporaryDirectory() as tmpdir:
            runner = LccaRunner(tmpdir, auto_discover=False)

            result = runner.configure(rate_id="PGE-E-ELEC").configure(capex=1000)

            assert result is runner
            assert runner.config.rate_id == "PGE-E-ELEC"
            assert runner.config.capex == 1000


class TestOutputFormat:
    """Tests for OutputFormat enum."""

    def test_all_formats_defined(self):
        """Verify all output formats are defined."""
        expected = ["EXCEL", "PDF", "TEXT", "JSON", "CSV"]
        for name in expected:
            assert hasattr(OutputFormat, name)


class TestAnalysisMode:
    """Tests for AnalysisMode enum."""

    def test_all_modes_defined(self):
        """Verify all analysis modes are defined."""
        expected = ["SIMPLE", "TOU", "VNBT"]
        for name in expected:
            assert hasattr(AnalysisMode, name)


class TestCLIFunctions:
    """Tests for CLI functions."""

    def test_import_cli(self):
        """Test CLI module imports."""
        from eco_tools.lcca import cli
        assert hasattr(cli, "main")
        assert hasattr(cli, "create_parser")

    def test_create_parser(self):
        """Test parser creation."""
        from eco_tools.lcca.cli import create_parser

        parser = create_parser()
        assert parser is not None

        # Test that subcommands exist
        args = parser.parse_args(["list-rates"])
        assert args.command == "list-rates"

        args = parser.parse_args(["list-regions"])
        assert args.command == "list-regions"

    def test_parser_discover_command(self):
        """Test discover command parsing."""
        from eco_tools.lcca.cli import create_parser

        parser = create_parser()
        args = parser.parse_args(["discover", "/path/to/project"])

        assert args.command == "discover"
        assert args.project_dir == "/path/to/project"

    def test_parser_analyze_command(self):
        """Test analyze command parsing."""
        from eco_tools.lcca.cli import create_parser

        parser = create_parser()
        args = parser.parse_args([
            "analyze", "/path/to/project",
            "--rate-id", "PGE-E-ELEC",
            "--region", "US-CA-SF",
            "--capex", "50000",
        ])

        assert args.command == "analyze"
        assert args.rate_id == "PGE-E-ELEC"
        assert args.region == "US-CA-SF"
        assert args.capex == 50000


class TestDiscoverMultipleProjects:
    """Tests for discover_multiple_projects function."""

    def test_discover_multiple_empty(self):
        """Test discovering in empty base directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            results = discover_multiple_projects(tmpdir)
            assert len(results) == 0

    def test_discover_multiple_projects(self):
        """Test discovering multiple projects."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create two project directories
            proj1 = Path(tmpdir) / "Project1"
            proj2 = Path(tmpdir) / "Project2"
            proj1.mkdir()
            proj2.mkdir()

            (proj1 / "Project1 - ap - HourlyResults.csv").write_text("data")
            (proj2 / "Project2 - ap - HourlyResults.csv").write_text("data")

            results = discover_multiple_projects(tmpdir)

            assert len(results) == 2
            project_names = {r.project_name for r in results}
            assert "Project1" in project_names
            assert "Project2" in project_names


class TestPhase6Integration:
    """Integration tests for Phase 6 workflow."""

    def test_complete_discovery_workflow(self):
        """Test complete discovery workflow."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create complete project structure
            (Path(tmpdir) / "Building - ap - HourlyResults.csv").write_text("Mon,Day,Hr,Tot\n1,1,1,100")
            (Path(tmpdir) / "Building - ab - HourlyResults.csv").write_text("Mon,Day,Hr,Tot\n1,1,1,120")
            (Path(tmpdir) / "Building - CSE.CSV").write_text("Meter,Mon,Day,Hr\n")
            (Path(tmpdir) / "Building - PVBattery.csv").write_text("Zone,PV\n")
            (Path(tmpdir) / "Building.cibd25").write_text("model data")

            outputs = discover_simulation_outputs(tmpdir)

            assert outputs.is_complete
            assert outputs.has_comparison
            assert outputs.has_pv_battery
            assert outputs.cibd_model is not None
            assert len(outputs.all_files) == 5

    def test_runner_initialization_workflow(self):
        """Test runner initialization with discovered files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            (Path(tmpdir) / "Test - ap - HourlyResults.csv").write_text("data")

            runner = LccaRunner(tmpdir)
            runner.configure(
                rate_id="PGE-E-ELEC",
                region="US-CA-SF",
                capex=25000,
                incentives=5000,
            )

            assert runner.outputs.is_complete
            assert runner.config.rate_id == "PGE-E-ELEC"
            assert runner.config.capex == 25000
            assert runner.config.incentives == 5000

    def test_module_exports(self):
        """Test that Phase 6 exports are available from main module."""
        from eco_tools.lcca import (
            # Auto-discovery
            SimulationFileType,
            SimulationFile,
            DiscoveredOutputs,
            discover_simulation_outputs,
            discover_multiple_projects,
            format_discovery_summary,
            discover_and_validate,
            # LCCA Runner
            OutputFormat,
            AnalysisMode,
            RunnerConfig,
            RunnerResults,
            LccaRunner,
            run_lcca_workflow,
            batch_lcca,
        )

        # Verify all imports work
        assert SimulationFileType is not None
        assert LccaRunner is not None
        assert discover_simulation_outputs is not None


class TestEdgeCases:
    """Edge case tests."""

    def test_unicode_project_names(self):
        """Test handling of unicode in project names."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create file with unicode characters in name
            filename = "Café Building - ap - HourlyResults.csv"
            (Path(tmpdir) / filename).write_text("data")

            outputs = discover_simulation_outputs(tmpdir)
            assert outputs.is_complete
            assert "Café" in outputs.project_name

    def test_spaces_in_paths(self):
        """Test handling of spaces in paths."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir) / "My Project Folder"
            project_dir.mkdir()
            (project_dir / "Test - ap - HourlyResults.csv").write_text("data")

            outputs = discover_simulation_outputs(str(project_dir))
            assert outputs.is_complete

    def test_case_insensitive_matching(self):
        """Test case-insensitive file matching."""
        # Test various case combinations
        test_cases = [
            "Project - ap - hourlyresults.csv",
            "Project - ap - HOURLYRESULTS.CSV",
            "Project - CSE.csv",
            "Project - cse.CSV",
        ]

        for filename in test_cases:
            result = _match_file(filename)
            assert result is not None, f"Failed to match: {filename}"
