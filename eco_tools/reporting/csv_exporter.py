"""
CSV Export Utilities
===================

Export simulation results and comparison data to CSV format.

Features:
- Export CBECC results to CSV
- Export EnergyPlus results to CSV
- Export comparison table to CSV
- Include metadata and timestamps

Author: ECO Tools Team
Version: 7.0.0
Date: November 11, 2025
"""

from typing import Dict, List, Any
import csv
from pathlib import Path
from datetime import datetime


def export_cbecc_results_to_csv(results: Dict[str, Any], output_file: str) -> None:
    """
    Export CBECC results to CSV file.

    Args:
        results: CBECC parsed results dict
        output_file: Path to output CSV file
    """
    with open(output_file, 'w', newline='') as f:
        writer = csv.writer(f)

        # Metadata section
        writer.writerow(["CBECC-Com Simulation Results"])
        writer.writerow(["Generated", datetime.now().strftime("%Y-%m-%d %H:%M:%S")])
        writer.writerow([])

        # Project info
        writer.writerow(["Project Information"])
        writer.writerow(["Field", "Value"])
        writer.writerow(["Project Name", results.get("project_name", "N/A")])
        writer.writerow(["Climate Zone", results.get("climate_zone", "N/A")])
        writer.writerow(["Building Area (sqft)", results.get("building_area", "N/A")])
        writer.writerow(["Software Version", results.get("software_version", "N/A")])
        writer.writerow([])

        # Compliance results
        writer.writerow(["Title 24 Compliance"])
        writer.writerow(["Metric", "Value"])
        writer.writerow(["Status", results.get("compliance_status", "Unknown")])
        writer.writerow(["Proposed TDV (kBtu/ft²/yr)", results.get("proposed_tdv", "N/A")])
        writer.writerow(["Standard TDV (kBtu/ft²/yr)", results.get("standard_tdv", "N/A")])
        writer.writerow(["Compliance Margin (%)", results.get("compliance_margin", "N/A")])
        writer.writerow([])

        # End uses
        if results.get("end_uses"):
            writer.writerow(["Energy End Uses (kBtu/ft²/yr)"])
            writer.writerow(["End Use", "Value"])
            for use, value in results["end_uses"].items():
                writer.writerow([use.replace("_", " ").title(), f"{value:.2f}"])

    print(f"✅ CBECC results exported to: {output_file}")


def export_energyplus_results_to_csv(results: Dict[str, Any], output_file: str) -> None:
    """
    Export EnergyPlus results to CSV file.

    Args:
        results: EnergyPlus results dict
        output_file: Path to output CSV file
    """
    with open(output_file, 'w', newline='') as f:
        writer = csv.writer(f)

        # Metadata section
        writer.writerow(["EnergyPlus Simulation Results"])
        writer.writerow(["Generated", datetime.now().strftime("%Y-%m-%d %H:%M:%S")])
        writer.writerow([])

        # Summary metrics
        writer.writerow(["Summary Metrics"])
        writer.writerow(["Metric", "Value", "Units"])
        writer.writerow(["Status", results.get("status", "Unknown"), ""])
        writer.writerow(["EUI", results.get("eui_kbtu_per_sqft_yr", "N/A"), "kBtu/ft²/yr"])
        writer.writerow(["Total Site Energy", results.get("total_site_energy_kwh", "N/A"), "kWh"])
        writer.writerow([])

        # End uses
        if results.get("end_uses"):
            writer.writerow(["Energy End Uses (kBtu/ft²/yr)"])
            writer.writerow(["End Use", "Value"])
            for use, value in results["end_uses"].items():
                writer.writerow([use.replace("_", " ").title(), f"{value:.2f}"])
            writer.writerow([])

        # Errors and warnings
        if results.get("errors"):
            writer.writerow(["Errors"])
            for error in results["errors"]:
                writer.writerow([error])
            writer.writerow([])

        if results.get("warnings"):
            writer.writerow(["Warnings"])
            for warning in results["warnings"][:10]:  # Limit to first 10
                writer.writerow([warning])

    print(f"✅ EnergyPlus results exported to: {output_file}")


def export_comparison_to_csv(
    cbecc_results: Dict[str, Any],
    energyplus_results: Dict[str, Any],
    output_file: str
) -> None:
    """
    Export side-by-side comparison to CSV file.

    Args:
        cbecc_results: CBECC parsed results
        energyplus_results: EnergyPlus results
        output_file: Path to output CSV file
    """
    with open(output_file, 'w', newline='') as f:
        writer = csv.writer(f)

        # Metadata
        writer.writerow(["CBECC vs EnergyPlus Comparison"])
        writer.writerow(["Generated", datetime.now().strftime("%Y-%m-%d %H:%M:%S")])
        writer.writerow([])

        # Summary comparison
        writer.writerow(["Summary Comparison"])
        writer.writerow(["Metric", "CBECC-Com", "EnergyPlus", "Delta", "% Diff"])

        cbecc_area = cbecc_results.get("building_area", 0)
        ep_eui = energyplus_results.get("eui_kbtu_per_sqft_yr", 0)

        writer.writerow(["Building Area (sqft)", cbecc_area or "N/A", "N/A", "-", "-"])
        writer.writerow(["EUI (kBtu/ft²/yr)", "N/A", ep_eui or "N/A", "-", "-"])
        writer.writerow([])

        # End use comparison
        cbecc_end_uses = cbecc_results.get("end_uses", {})
        ep_end_uses = energyplus_results.get("end_uses", {})

        if cbecc_end_uses and ep_end_uses:
            writer.writerow(["End Use Comparison (kBtu/ft²/yr)"])
            writer.writerow(["End Use", "CBECC-Com", "EnergyPlus", "Delta", "% Diff"])

            all_uses = sorted(set(list(cbecc_end_uses.keys()) + list(ep_end_uses.keys())))

            for use in all_uses:
                cbecc_val = cbecc_end_uses.get(use, 0)
                ep_val = ep_end_uses.get(use, 0)
                delta = ep_val - cbecc_val

                if cbecc_val > 0:
                    pct_diff = (delta / cbecc_val) * 100
                    pct_str = f"{pct_diff:+.1f}%"
                else:
                    pct_str = "N/A"

                writer.writerow([
                    use.replace("_", " ").title(),
                    f"{cbecc_val:.2f}",
                    f"{ep_val:.2f}",
                    f"{delta:+.2f}",
                    pct_str
                ])

    print(f"✅ Comparison exported to: {output_file}")


if __name__ == "__main__":
    # Test exports with sample data
    print("🧪 Testing CSV export...")

    # Sample data
    cbecc_data = {
        "status": "success",
        "project_name": "Test Building",
        "climate_zone": "CZ12",
        "building_area": 50000,
        "compliance_status": "Pass",
        "proposed_tdv": 42.5,
        "standard_tdv": 48.2,
        "compliance_margin": 11.8,
        "end_uses": {
            "space_heating": 12.5,
            "space_cooling": 18.3,
            "indoor_lighting": 8.2,
            "equipment": 5.1,
            "dhw": 4.2
        }
    }

    ep_data = {
        "status": "success",
        "eui_kbtu_per_sqft_yr": 45.2,
        "total_site_energy_kwh": 250000,
        "end_uses": {
            "heating": 13.2,
            "cooling": 17.5,
            "lighting": 9.1,
            "equipment": 5.0,
            "dhw": 4.0
        }
    }

    # Test exports
    export_cbecc_results_to_csv(cbecc_data, "test_cbecc.csv")
    export_energyplus_results_to_csv(ep_data, "test_energyplus.csv")
    export_comparison_to_csv(cbecc_data, ep_data, "test_comparison.csv")

    print("\n✅ All exports completed successfully!")
