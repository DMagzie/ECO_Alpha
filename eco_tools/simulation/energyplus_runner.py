"""
EnergyPlus Simulation Runner
=============================

Runs EnergyPlus simulations using Honeybee-Energy and parses results.

This module provides:
- EnergyPlus simulation execution via Honeybee
- Results parsing (SQL, ESO, HTML files)
- Comparison with CBECC results
- Async execution support
- Progress monitoring

Workflow:
1. EMJSON → HBJSON export
2. Load Honeybee model from HBJSON
3. Run EnergyPlus simulation
4. Parse results from SQL/ESO files
5. Compare with CBECC (if available)

Author: ECO Tools Team
Version: 7.0.0
Date: November 11, 2025
"""

from typing import Dict, List, Optional, Tuple, Any
from pathlib import Path
import json
import subprocess
import asyncio
import sqlite3
from datetime import datetime
import shutil

# Honeybee imports (optional - graceful degradation)
try:
    from honeybee.model import Model as HBModel
    from honeybee_energy.run import run_idf
    from honeybee_energy.result.sql import SQLiteResult
    from honeybee_energy.result.err import Err
    HONEYBEE_ENERGY_AVAILABLE = True
except ImportError:
    HONEYBEE_ENERGY_AVAILABLE = False


class EnergyPlusRunner:
    """
    Run EnergyPlus simulations via Honeybee and parse results.

    Example:
        >>> runner = EnergyPlusRunner()
        >>> if runner.verify_installation():
        ...     result = runner.run_simulation("model.hbjson")
        ...     print(f"EUI: {result['eui_kbtu_per_sqft_yr']}")
    """

    def __init__(self, energyplus_path: Optional[str] = None,
                 epw_file: Optional[str] = None):
        """
        Initialize EnergyPlus runner.

        Args:
            energyplus_path: Path to EnergyPlus executable (optional, auto-detect)
            epw_file: Path to EPW weather file (optional, can be specified per simulation)
        """
        self.energyplus_path = energyplus_path
        self.epw_file = epw_file
        self.last_sim_folder = None

    def verify_installation(self) -> bool:
        """
        Verify that Honeybee-Energy and EnergyPlus are installed.

        Returns:
            bool: True if EnergyPlus can be run
        """
        if not HONEYBEE_ENERGY_AVAILABLE:
            print("❌ Honeybee-Energy not installed")
            print("   Install with: pip install honeybee-energy")
            return False

        # Try to get EnergyPlus version
        try:
            from honeybee_energy.config import folders
            ep_path = folders.energyplus_path
            if ep_path and Path(ep_path).exists():
                print(f"✅ EnergyPlus found at: {ep_path}")
                return True
            else:
                print("❌ EnergyPlus not found")
                print("   Download from: https://energyplus.net/downloads")
                return False
        except Exception as e:
            print(f"❌ Error checking EnergyPlus: {e}")
            return False

    def run_simulation(
        self,
        hbjson_file: str,
        epw_file: Optional[str] = None,
        output_directory: Optional[str] = None,
        silent: bool = False
    ) -> Dict[str, Any]:
        """
        Run EnergyPlus simulation from HBJSON file.

        Args:
            hbjson_file: Path to Honeybee JSON file
            epw_file: Path to EPW weather file (overrides default)
            output_directory: Where to store results (default: next to HBJSON)
            silent: If True, suppress console output

        Returns:
            Dict with simulation results:
                - status: "success" or "error"
                - sql_file: Path to results SQL file
                - html_file: Path to results HTML file
                - eui_kbtu_per_sqft_yr: Energy Use Intensity
                - total_site_energy_kwh: Total site energy
                - errors: List of errors from ERR file
                - warnings: List of warnings
        """
        if not HONEYBEE_ENERGY_AVAILABLE:
            return {
                "status": "error",
                "message": "Honeybee-Energy not installed"
            }

        hbjson_path = Path(hbjson_file)
        if not hbjson_path.exists():
            return {
                "status": "error",
                "message": f"HBJSON file not found: {hbjson_file}"
            }

        # Use provided EPW or default
        weather_file = epw_file or self.epw_file
        if not weather_file:
            return {
                "status": "error",
                "message": "No EPW weather file specified"
            }

        if not Path(weather_file).exists():
            return {
                "status": "error",
                "message": f"EPW file not found: {weather_file}"
            }

        # Determine output directory
        if output_directory:
            output_dir = Path(output_directory)
        else:
            output_dir = hbjson_path.parent / f"{hbjson_path.stem}_ep_results"

        output_dir.mkdir(parents=True, exist_ok=True)

        try:
            # Load Honeybee model
            if not silent:
                print(f"📂 Loading model from: {hbjson_file}")

            hb_model = HBModel.from_hbjson(str(hbjson_path))

            # Generate IDF file
            if not silent:
                print(f"🔧 Generating IDF file...")

            idf_file = output_dir / f"{hbjson_path.stem}.idf"
            hb_model.to.idf(hb_model, str(idf_file))

            # Run EnergyPlus
            if not silent:
                print(f"⚡ Running EnergyPlus simulation...")
                print(f"   Weather: {weather_file}")
                print(f"   Output: {output_dir}")

            sql, zsz, rdd, html, err = run_idf(
                str(idf_file),
                str(weather_file),
                silent=silent
            )

            self.last_sim_folder = Path(sql).parent if sql else output_dir

            # Parse results
            if not silent:
                print(f"📊 Parsing results...")

            result = self._parse_results(sql, err, html)
            result["output_directory"] = str(output_dir)
            result["idf_file"] = str(idf_file)

            if not silent:
                if result["status"] == "success":
                    print(f"✅ Simulation complete!")
                    print(f"   EUI: {result.get('eui_kbtu_per_sqft_yr', 'N/A'):.1f} kBtu/ft²/yr")
                    print(f"   Total Energy: {result.get('total_site_energy_kwh', 'N/A'):,.0f} kWh")
                else:
                    print(f"❌ Simulation failed!")
                    if result.get("errors"):
                        print(f"   Errors: {len(result['errors'])}")

            return result

        except Exception as e:
            return {
                "status": "error",
                "message": f"Simulation error: {str(e)}",
                "output_directory": str(output_dir) if output_dir else None
            }

    async def run_simulation_async(
        self,
        hbjson_file: str,
        epw_file: Optional[str] = None,
        output_directory: Optional[str] = None,
        progress_callback: Optional[callable] = None
    ) -> Dict[str, Any]:
        """
        Run EnergyPlus simulation asynchronously.

        Args:
            hbjson_file: Path to Honeybee JSON file
            epw_file: Path to EPW weather file
            output_directory: Where to store results
            progress_callback: Function to call with progress updates

        Returns:
            Dict with simulation results
        """
        # Run in executor to avoid blocking
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            self.run_simulation,
            hbjson_file,
            epw_file,
            output_directory,
            True  # silent=True for async
        )

        if progress_callback:
            progress_callback(100, "Simulation complete")

        return result

    def _parse_results(
        self,
        sql_file: Optional[str],
        err_file: Optional[str],
        html_file: Optional[str]
    ) -> Dict[str, Any]:
        """
        Parse EnergyPlus results from SQL, ERR, and HTML files.

        Args:
            sql_file: Path to results SQL database
            err_file: Path to ERR file
            html_file: Path to HTML summary

        Returns:
            Dict with parsed results
        """
        result = {
            "status": "unknown",
            "sql_file": sql_file,
            "html_file": html_file,
            "err_file": err_file
        }

        # Parse ERR file for errors/warnings
        if err_file and Path(err_file).exists():
            err_result = Err(err_file)
            result["errors"] = err_result.severe_errors if hasattr(err_result, 'severe_errors') else []
            result["warnings"] = err_result.warnings if hasattr(err_result, 'warnings') else []

            # Check if simulation completed
            if err_result.file_contents and 'EnergyPlus Completed Successfully' in err_result.file_contents:
                result["status"] = "success"
            else:
                result["status"] = "error"
        else:
            result["status"] = "error"
            result["errors"] = ["ERR file not found"]

        # Parse SQL file for energy results
        if sql_file and Path(sql_file).exists() and result["status"] == "success":
            try:
                sql_result = SQLiteResult(sql_file)

                # Get key energy metrics
                result["eui_kbtu_per_sqft_yr"] = sql_result.eui if hasattr(sql_result, 'eui') else None
                result["total_site_energy_kwh"] = sql_result.total_energy if hasattr(sql_result, 'total_energy') else None

                # Get end use breakdown
                if hasattr(sql_result, 'energy_use_intensity_end_uses'):
                    result["end_uses"] = {
                        "heating": sql_result.energy_use_intensity_end_uses.get("Heating", 0),
                        "cooling": sql_result.energy_use_intensity_end_uses.get("Cooling", 0),
                        "lighting": sql_result.energy_use_intensity_end_uses.get("Interior Lighting", 0),
                        "equipment": sql_result.energy_use_intensity_end_uses.get("Interior Equipment", 0),
                        "fans": sql_result.energy_use_intensity_end_uses.get("Fans", 0),
                        "pumps": sql_result.energy_use_intensity_end_uses.get("Pumps", 0),
                        "heat_rejection": sql_result.energy_use_intensity_end_uses.get("Heat Rejection", 0),
                        "dhw": sql_result.energy_use_intensity_end_uses.get("Water Systems", 0),
                    }

                # Get monthly data if available
                if hasattr(sql_result, 'monthly_values'):
                    result["monthly_energy"] = sql_result.monthly_values

            except Exception as e:
                result["sql_parse_error"] = str(e)

        return result

    def compare_with_cbecc(
        self,
        energyplus_result: Dict[str, Any],
        cbecc_analysis_results_xml: str
    ) -> Dict[str, Any]:
        """
        Compare EnergyPlus results with CBECC-Com results.

        Args:
            energyplus_result: Dict from run_simulation()
            cbecc_analysis_results_xml: Path to CBECC AnalysisResults.xml

        Returns:
            Dict with comparison metrics
        """
        comparison = {
            "energyplus_eui": energyplus_result.get("eui_kbtu_per_sqft_yr"),
            "cbecc_eui": None,
            "difference_percent": None,
            "end_use_comparison": {}
        }

        # TODO: Parse CBECC AnalysisResults.xml
        # This will be implemented when CBECC integration is enhanced

        return comparison

    def get_weather_file_for_climate_zone(self, climate_zone: str) -> Optional[str]:
        """
        Get appropriate EPW file for California climate zone.

        Args:
            climate_zone: California climate zone (e.g., "CZ12")

        Returns:
            Path to EPW file, or None if not found
        """
        # Mapping of California climate zones to EPW files
        # These are typical cities for each climate zone
        cz_to_city = {
            "CZ01": "Arcata",
            "CZ02": "Santa Rosa",
            "CZ03": "Oakland",
            "CZ04": "San Jose",
            "CZ05": "Santa Maria",
            "CZ06": "Los Angeles",
            "CZ07": "San Diego",
            "CZ08": "El Toro",
            "CZ09": "Pasadena",
            "CZ10": "Riverside",
            "CZ11": "Red Bluff",
            "CZ12": "Sacramento",
            "CZ13": "Fresno",
            "CZ14": "China Lake",
            "CZ15": "El Centro",
            "CZ16": "Mount Shasta"
        }

        city = cz_to_city.get(climate_zone)
        if not city:
            return None

        # TODO: Look up EPW files in standard locations
        # For now, return None - users must provide EPW file
        return None


def get_sample_weather_files() -> List[Dict[str, str]]:
    """
    Get list of sample weather files included with EnergyPlus.

    Returns:
        List of dicts with 'name', 'path', 'location', 'climate' keys
    """
    weather_files = []

    try:
        from honeybee_energy.config import folders
        weather_dir = Path(folders.energyplus_path).parent / "WeatherData"

        if weather_dir.exists():
            for epw_file in weather_dir.glob("*.epw"):
                weather_files.append({
                    "name": epw_file.stem,
                    "path": str(epw_file),
                    "location": epw_file.stem.split("_")[0] if "_" in epw_file.stem else "Unknown",
                    "climate": "Unknown"
                })
    except Exception:
        pass

    return weather_files


if __name__ == "__main__":
    # Test runner
    runner = EnergyPlusRunner()

    print("🔍 Checking EnergyPlus installation...")
    if runner.verify_installation():
        print("\n✅ EnergyPlus is ready to use!")
        print("\nSample weather files:")
        for epw in get_sample_weather_files()[:5]:
            print(f"  - {epw['name']}")
    else:
        print("\n❌ EnergyPlus not ready")
