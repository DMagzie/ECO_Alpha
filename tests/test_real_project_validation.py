"""
Real Project Validation Test Suite for LCCA Module.

This test suite validates the LCCA workflow against real CBECC simulation
outputs to ensure calculations produce reasonable, expected results.

Test projects are located in:
- /reference_data/cbecc/Full Sample Model Sets/
- /LCCA Tests/

Each test validates:
1. Auto-discovery works correctly
2. Parsing produces valid data
3. LCCA calculations complete without error
4. Results are within expected ranges for the building type
"""

import pytest
from pathlib import Path
from dataclasses import dataclass
from typing import Optional, Dict, Any, List
import json

# Import LCCA modules
from eco_tools.lcca import (
    discover_simulation_outputs,
    LccaRunner,
    DiscoveredOutputs,
    format_discovery_summary,
)


# =============================================================================
# Test Configuration
# =============================================================================

# Base paths for test projects
PROJECT_BASE = Path(__file__).parent.parent
REFERENCE_DATA = PROJECT_BASE / "reference_data" / "cbecc"
LCCA_TESTS = PROJECT_BASE / "LCCA Tests"

# Reference project paths
JEFFERSON_MURRIETA = REFERENCE_DATA / "Full Sample Model Sets" / "Jefferson Murrieta B1-B7"
VENTURA_MAESTRO = LCCA_TESTS / "Ventura & 7th" / "Maestro"


@dataclass
class ProjectExpectations:
    """Expected value ranges for a test project."""
    project_name: str
    building_type: str  # commercial, multifamily, residential

    # Expected discovery results
    expect_hourly_proposed: bool = True
    expect_hourly_standard: bool = False
    expect_pv_battery: bool = False
    expect_cuac: bool = False

    # Expected annual energy ranges (kWh)
    min_annual_kwh: float = 0
    max_annual_kwh: float = float('inf')

    # Expected annual cost ranges ($)
    min_annual_cost: float = 0
    max_annual_cost: float = float('inf')

    # Expected savings (if baseline available)
    expect_positive_savings: Optional[bool] = None
    min_annual_savings: Optional[float] = None
    max_annual_savings: Optional[float] = None

    # Expected payback (years)
    min_payback: Optional[float] = None
    max_payback: Optional[float] = None


# =============================================================================
# Expected Values for Reference Projects
# =============================================================================

JEFFERSON_BLDG1B_EXPECTATIONS = ProjectExpectations(
    project_name="Jefferson Murrieta Bldg 1B",
    building_type="commercial",
    expect_hourly_proposed=True,
    expect_hourly_standard=True,
    expect_pv_battery=True,
    min_annual_kwh=100_000,
    max_annual_kwh=2_000_000,
    min_annual_cost=20_000,
    max_annual_cost=200_000,
)

VENTURA_FULLSIM_EXPECTATIONS = ProjectExpectations(
    project_name="Ventura & 7th Maestro Full Sim",
    building_type="multifamily",
    expect_hourly_proposed=True,
    expect_hourly_standard=True,
    expect_pv_battery=True,
    min_annual_kwh=200_000,
    max_annual_kwh=3_000_000,
    min_annual_cost=30_000,
    max_annual_cost=150_000,
    expect_positive_savings=True,
    min_annual_savings=5_000,
    max_annual_savings=100_000,
    min_payback=1,
    max_payback=20,
)


# =============================================================================
# Utility Functions
# =============================================================================

def get_project_run_folder(project_path: Path, subfolder: str = None) -> Optional[Path]:
    """Find the run folder within a project directory."""
    if subfolder:
        project_path = project_path / subfolder

    if not project_path.exists():
        return None

    # Look for a "- run" folder
    for item in project_path.iterdir():
        if item.is_dir() and "- run" in item.name:
            return item

    # Maybe the path is already the run folder
    if "- run" in project_path.name:
        return project_path

    return None


def validate_discovery(
    outputs: DiscoveredOutputs,
    expectations: ProjectExpectations
) -> List[str]:
    """Validate discovery results against expectations. Returns list of issues."""
    issues = []

    if expectations.expect_hourly_proposed and not outputs.hourly_results_proposed:
        issues.append("Missing expected HourlyResults (proposed)")

    if expectations.expect_hourly_standard and not outputs.hourly_results_standard:
        issues.append("Missing expected HourlyResults (standard)")

    if expectations.expect_pv_battery and not outputs.pv_battery:
        issues.append("Missing expected PV/Battery data")

    if expectations.expect_cuac and not outputs.cuac:
        issues.append("Missing expected CUAC data")

    return issues


def validate_lcca_results(
    results,
    expectations: ProjectExpectations,
    capex: float = 0
) -> List[str]:
    """Validate LCCA results against expectations. Returns list of issues."""
    issues = []

    if not results.lcca_results:
        issues.append("No LCCA results generated")
        return issues

    lr = results.lcca_results

    # Validate annual costs
    if lr.proposed_annual_cost < expectations.min_annual_cost:
        issues.append(
            f"Annual cost ${lr.proposed_annual_cost:,.0f} below minimum "
            f"${expectations.min_annual_cost:,.0f}"
        )

    if lr.proposed_annual_cost > expectations.max_annual_cost:
        issues.append(
            f"Annual cost ${lr.proposed_annual_cost:,.0f} above maximum "
            f"${expectations.max_annual_cost:,.0f}"
        )

    # Validate savings if expected
    if expectations.expect_positive_savings is not None:
        if expectations.expect_positive_savings and lr.annual_savings <= 0:
            issues.append(f"Expected positive savings but got ${lr.annual_savings:,.0f}")
        elif not expectations.expect_positive_savings and lr.annual_savings > 0:
            issues.append(f"Expected negative/zero savings but got ${lr.annual_savings:,.0f}")

    if expectations.min_annual_savings is not None:
        if lr.annual_savings < expectations.min_annual_savings:
            issues.append(
                f"Annual savings ${lr.annual_savings:,.0f} below minimum "
                f"${expectations.min_annual_savings:,.0f}"
            )

    if expectations.max_annual_savings is not None:
        if lr.annual_savings > expectations.max_annual_savings:
            issues.append(
                f"Annual savings ${lr.annual_savings:,.0f} above maximum "
                f"${expectations.max_annual_savings:,.0f}"
            )

    # Validate payback if CAPEX provided
    if capex > 0 and lr.simple_payback_years:
        if expectations.min_payback and lr.simple_payback_years < expectations.min_payback:
            issues.append(
                f"Payback {lr.simple_payback_years:.1f} years below minimum "
                f"{expectations.min_payback:.1f}"
            )
        if expectations.max_payback and lr.simple_payback_years > expectations.max_payback:
            issues.append(
                f"Payback {lr.simple_payback_years:.1f} years above maximum "
                f"{expectations.max_payback:.1f}"
            )

    return issues


def generate_cost_breakdown_report(results, project_name: str) -> Dict[str, Any]:
    """Generate a detailed cost breakdown for review."""
    report = {
        "project_name": project_name,
        "lcca_results": None,
        "econ1_breakdown": None,
        "warnings": [],
    }

    if results.lcca_results:
        lr = results.lcca_results
        report["lcca_results"] = {
            "baseline_annual_cost": lr.baseline_annual_cost,
            "proposed_annual_cost": lr.proposed_annual_cost,
            "annual_savings": lr.annual_savings,
            "lifecycle_savings": lr.lifecycle_savings,
            "npv": lr.npv,
            "irr": lr.irr,
            "sir": lr.sir,
            "simple_payback_years": lr.simple_payback_years,
            "discounted_payback_years": lr.discounted_payback_years,
            "initial_investment": lr.initial_investment,
        }

    if results.econ1_report:
        er = results.econ1_report
        report["econ1_breakdown"] = {
            "proposed": {
                "elec_kwh_gross": er.proposed.elec_kwh_gross,
                "elec_cost_gross": er.proposed.elec_cost_gross,
                "elec_kwh_net": er.proposed.elec_kwh_net,
                "elec_cost_net": er.proposed.elec_cost_net,
                "gas_therm": er.proposed.gas_therm,
                "gas_cost": er.proposed.gas_cost,
                "demand_cost_gross": er.proposed.demand_cost_gross,
                "net_cost": er.proposed.net_cost,
            }
        }
        if er.baseline:
            report["econ1_breakdown"]["baseline"] = {
                "elec_kwh_gross": er.baseline.elec_kwh_gross,
                "elec_cost_gross": er.baseline.elec_cost_gross,
                "gas_therm": er.baseline.gas_therm,
                "gas_cost": er.baseline.gas_cost,
                "demand_cost_gross": er.baseline.demand_cost_gross,
                "net_cost": er.baseline.net_cost,
            }
            report["econ1_breakdown"]["annual_savings"] = er.annual_savings
            report["econ1_breakdown"]["percent_savings"] = er.percent_savings

    return report


# =============================================================================
# Test Classes
# =============================================================================

class TestProjectDiscovery:
    """Test auto-discovery on real project folders."""

    @pytest.mark.skipif(
        not JEFFERSON_MURRIETA.exists(),
        reason="Jefferson Murrieta reference data not available"
    )
    def test_discover_jefferson_bldg1b(self):
        """Test discovery on Jefferson Murrieta Bldg 1B."""
        run_folder = get_project_run_folder(JEFFERSON_MURRIETA / "Bldg 1B")
        assert run_folder is not None, "Could not find run folder"

        outputs = discover_simulation_outputs(run_folder)

        # Validate against expectations
        issues = validate_discovery(outputs, JEFFERSON_BLDG1B_EXPECTATIONS)
        assert len(issues) == 0, f"Discovery issues: {issues}"

        # Additional checks
        assert outputs.is_complete
        assert outputs.has_tou_data

    @pytest.mark.skipif(
        not (VENTURA_MAESTRO / "Full sim").exists(),
        reason="Ventura Full Sim reference data not available"
    )
    def test_discover_ventura_fullsim(self):
        """Test discovery on Ventura & 7th Full Sim."""
        run_folder = get_project_run_folder(VENTURA_MAESTRO / "Full sim")
        assert run_folder is not None, "Could not find run folder"

        outputs = discover_simulation_outputs(run_folder)

        # Validate against expectations
        issues = validate_discovery(outputs, VENTURA_FULLSIM_EXPECTATIONS)
        assert len(issues) == 0, f"Discovery issues: {issues}"

        assert outputs.is_complete
        assert outputs.has_comparison  # Has both proposed and standard


class TestLccaWorkflow:
    """Test complete LCCA workflow on real projects."""

    @pytest.mark.skipif(
        not JEFFERSON_MURRIETA.exists(),
        reason="Jefferson Murrieta reference data not available"
    )
    def test_lcca_jefferson_bldg1b(self):
        """Run LCCA on Jefferson Murrieta Bldg 1B."""
        run_folder = get_project_run_folder(JEFFERSON_MURRIETA / "Bldg 1B")
        assert run_folder is not None

        # Configure and run
        runner = LccaRunner(run_folder)
        runner.configure(
            rate_id="SCE TOU-GS-3",
            analysis_period=30,
            discount_rate=0.05,
            capex=50000,
        )
        runner.config.output_formats = []  # No file output for tests

        results = runner.run()

        # Validate results
        assert results.lcca_results is not None, "LCCA failed to produce results"

        issues = validate_lcca_results(
            results,
            JEFFERSON_BLDG1B_EXPECTATIONS,
            capex=50000
        )
        assert len(issues) == 0, f"Validation issues: {issues}"

    @pytest.mark.skipif(
        not (VENTURA_MAESTRO / "Full sim").exists(),
        reason="Ventura Full Sim reference data not available"
    )
    def test_lcca_ventura_fullsim(self):
        """Run LCCA on Ventura & 7th Full Sim."""
        run_folder = get_project_run_folder(VENTURA_MAESTRO / "Full sim")
        assert run_folder is not None

        # Configure and run
        runner = LccaRunner(run_folder)
        runner.configure(
            rate_id="PG&E B-20",
            analysis_period=30,
            discount_rate=0.05,
            capex=100000,
        )
        runner.config.output_formats = []

        results = runner.run()

        # Validate results
        assert results.lcca_results is not None, "LCCA failed to produce results"

        issues = validate_lcca_results(
            results,
            VENTURA_FULLSIM_EXPECTATIONS,
            capex=100000
        )
        assert len(issues) == 0, f"Validation issues: {issues}"

        # Specific checks for this project
        lr = results.lcca_results
        assert lr.annual_savings > 0, "Expected positive annual savings"
        assert lr.simple_payback_years is not None, "Expected valid payback"
        assert lr.simple_payback_years < 15, "Payback seems too long"


class TestCostDataReview:
    """Tests for reviewing cost data inputs and outputs."""

    @pytest.mark.skipif(
        not JEFFERSON_MURRIETA.exists(),
        reason="Jefferson Murrieta reference data not available"
    )
    def test_cost_breakdown_jefferson(self):
        """Generate and review cost breakdown for Jefferson project."""
        run_folder = get_project_run_folder(JEFFERSON_MURRIETA / "Bldg 1B")
        if run_folder is None:
            pytest.skip("Run folder not found")

        runner = LccaRunner(run_folder)
        runner.configure(rate_id="SCE TOU-GS-3", capex=50000)
        runner.config.output_formats = []

        results = runner.run()

        # Generate cost breakdown
        breakdown = generate_cost_breakdown_report(results, "Jefferson Bldg 1B")

        # Verify breakdown structure
        assert breakdown["lcca_results"] is not None
        assert "baseline_annual_cost" in breakdown["lcca_results"]
        assert "proposed_annual_cost" in breakdown["lcca_results"]

        # Print for manual review (visible in pytest -v)
        print("\n" + "=" * 60)
        print("COST BREAKDOWN: Jefferson Murrieta Bldg 1B")
        print("=" * 60)
        print(json.dumps(breakdown, indent=2, default=str))

    @pytest.mark.skipif(
        not (VENTURA_MAESTRO / "Full sim").exists(),
        reason="Ventura Full Sim reference data not available"
    )
    def test_cost_breakdown_ventura(self):
        """Generate and review cost breakdown for Ventura project."""
        run_folder = get_project_run_folder(VENTURA_MAESTRO / "Full sim")
        if run_folder is None:
            pytest.skip("Run folder not found")

        runner = LccaRunner(run_folder)
        runner.configure(rate_id="PG&E B-20", capex=100000)
        runner.config.output_formats = []

        results = runner.run()

        # Generate cost breakdown
        breakdown = generate_cost_breakdown_report(results, "Ventura & 7th Full Sim")

        # Verify breakdown structure
        assert breakdown["lcca_results"] is not None
        assert breakdown["econ1_breakdown"] is not None

        # Print for manual review
        print("\n" + "=" * 60)
        print("COST BREAKDOWN: Ventura & 7th Full Sim")
        print("=" * 60)
        print(json.dumps(breakdown, indent=2, default=str))


class TestTariffComparison:
    """Test LCCA results across different tariffs."""

    TARIFFS_TO_TEST = [
        "PG&E B-20",
        "SCE TOU-GS-3",
        "SDG&E AL-TOU",
    ]

    @pytest.mark.skipif(
        not (VENTURA_MAESTRO / "Full sim").exists(),
        reason="Ventura Full Sim reference data not available"
    )
    @pytest.mark.parametrize("rate_id", TARIFFS_TO_TEST)
    def test_tariff_comparison(self, rate_id):
        """Compare LCCA results across different tariffs."""
        run_folder = get_project_run_folder(VENTURA_MAESTRO / "Full sim")
        if run_folder is None:
            pytest.skip("Run folder not found")

        runner = LccaRunner(run_folder)
        runner.configure(rate_id=rate_id, capex=100000)
        runner.config.output_formats = []

        results = runner.run()

        assert results.lcca_results is not None, f"LCCA failed for {rate_id}"

        lr = results.lcca_results
        print(f"\n{rate_id}:")
        print(f"  Baseline Annual: ${lr.baseline_annual_cost:,.0f}")
        print(f"  Proposed Annual: ${lr.proposed_annual_cost:,.0f}")
        print(f"  Annual Savings: ${lr.annual_savings:,.0f}")
        print(f"  Lifecycle Savings: ${lr.lifecycle_savings:,.0f}")


class TestBatchValidation:
    """Test batch processing of multiple projects."""

    @pytest.mark.skipif(
        not JEFFERSON_MURRIETA.exists(),
        reason="Jefferson Murrieta reference data not available"
    )
    def test_batch_jefferson_buildings(self):
        """Run LCCA on all Jefferson Murrieta buildings."""
        results_summary = []

        for bldg_folder in sorted(JEFFERSON_MURRIETA.iterdir()):
            if not bldg_folder.is_dir() or bldg_folder.name.startswith('.'):
                continue

            run_folder = get_project_run_folder(bldg_folder)
            if run_folder is None:
                continue

            try:
                runner = LccaRunner(run_folder)
                runner.configure(rate_id="SCE TOU-GS-3", capex=50000)
                runner.config.output_formats = []

                results = runner.run()

                if results.lcca_results:
                    lr = results.lcca_results
                    results_summary.append({
                        "building": bldg_folder.name,
                        "baseline_annual": lr.baseline_annual_cost,
                        "proposed_annual": lr.proposed_annual_cost,
                        "annual_savings": lr.annual_savings,
                        "status": "success"
                    })
                else:
                    results_summary.append({
                        "building": bldg_folder.name,
                        "status": "no_results"
                    })
            except Exception as e:
                results_summary.append({
                    "building": bldg_folder.name,
                    "status": "error",
                    "error": str(e)
                })

        # Print summary
        print("\n" + "=" * 70)
        print("BATCH RESULTS: Jefferson Murrieta Buildings")
        print("=" * 70)
        for r in results_summary:
            if r["status"] == "success":
                print(f"{r['building']:15} | Baseline: ${r['baseline_annual']:>10,.0f} | "
                      f"Proposed: ${r['proposed_annual']:>10,.0f} | "
                      f"Savings: ${r['annual_savings']:>10,.0f}")
            else:
                print(f"{r['building']:15} | Status: {r['status']}")

        # At least some should succeed
        successes = [r for r in results_summary if r["status"] == "success"]
        assert len(successes) > 0, "No buildings processed successfully"


# =============================================================================
# Fixtures for Future Test Projects
# =============================================================================

@pytest.fixture
def project_registry():
    """Registry of available test projects."""
    projects = {}

    # Jefferson Murrieta buildings
    if JEFFERSON_MURRIETA.exists():
        for bldg in JEFFERSON_MURRIETA.iterdir():
            if bldg.is_dir() and not bldg.name.startswith('.'):
                run_folder = get_project_run_folder(bldg)
                if run_folder:
                    projects[f"jefferson_{bldg.name.lower().replace(' ', '_')}"] = {
                        "path": run_folder,
                        "type": "commercial",
                        "source": "Jefferson Murrieta",
                    }

    # Ventura projects
    if VENTURA_MAESTRO.exists():
        fullsim = get_project_run_folder(VENTURA_MAESTRO / "Full sim")
        if fullsim:
            projects["ventura_fullsim"] = {
                "path": fullsim,
                "type": "multifamily",
                "source": "Ventura & 7th",
            }

    return projects


def test_list_available_projects(project_registry):
    """List all available test projects."""
    print("\n" + "=" * 60)
    print("AVAILABLE TEST PROJECTS")
    print("=" * 60)

    for name, info in project_registry.items():
        print(f"  {name}:")
        print(f"    Path: {info['path']}")
        print(f"    Type: {info['type']}")
        print(f"    Source: {info['source']}")

    print(f"\nTotal: {len(project_registry)} projects")
