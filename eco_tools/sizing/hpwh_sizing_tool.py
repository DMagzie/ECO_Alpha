#!/usr/bin/env python3
"""
Central HPWH Tank Sizing CLI Tool

Command-line interface for sizing central heat pump water heaters
for multifamily buildings per Title 24 2025 standards.

Usage:
    python hpwh_sizing_tool.py --units 30 --bedrooms 60 --climate-zone 12
    python hpwh_sizing_tool.py --units 50 --avg-br 1.5 --load-shift --oversize 1.5
    python hpwh_sizing_tool.py --cibd25 project.cibd25 --optimize
"""

import argparse
import sys
import json
from pathlib import Path
from typing import Optional

from eco_tools.sizing.central_hpwh_sizer import (
    CentralHPWHSizer,
    BuildingProfile,
    HPWHSystemConfig,
    HPWHCompressorType,
    SizingResults,
    size_from_dwelling_units,
    create_sizing_report,
)


def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Central HPWH Tank Sizing Tool for Title 24 2025",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic sizing for 30-unit building
  %(prog)s --units 30 --bedrooms 60

  # With load shifting optimization
  %(prog)s --units 50 --avg-br 2.0 --load-shift --oversize 1.5

  # From CIBD25 file
  %(prog)s --cibd25 project.cibd25 --optimize

  # Export to JSON
  %(prog)s --units 30 --bedrooms 60 --json output.json
        """
    )

    # Input methods (mutually exclusive)
    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument(
        "--units",
        type=int,
        help="Number of dwelling units"
    )
    input_group.add_argument(
        "--cibd25",
        type=str,
        help="Path to CIBD25 file (extract building data)"
    )

    # Building parameters
    parser.add_argument(
        "--bedrooms",
        type=int,
        help="Total number of bedrooms (required if --units specified)"
    )
    parser.add_argument(
        "--avg-br",
        type=float,
        default=2.0,
        help="Average bedrooms per unit (default: 2.0)"
    )
    parser.add_argument(
        "--common-du-equiv",
        type=float,
        default=0.0,
        help="Common area load as DU equivalent (default: 0.0)"
    )
    parser.add_argument(
        "--climate-zone",
        type=str,
        default="12",
        choices=[str(i) for i in range(1, 17)],
        help="California climate zone 1-16 (default: 12)"
    )

    # Optimization options
    parser.add_argument(
        "--load-shift",
        action="store_true",
        help="Enable load shifting optimization for NEM3/LSC"
    )
    parser.add_argument(
        "--oversize",
        type=float,
        default=1.25,
        help="Tank oversizing factor for thermal storage (default: 1.25)"
    )
    parser.add_argument(
        "--no-oversize",
        action="store_true",
        help="Use code minimum only, no optimization"
    )
    parser.add_argument(
        "--charge-start",
        type=int,
        default=11,
        help="Hour to start heating (0-23, default: 11 = noon)"
    )
    parser.add_argument(
        "--charge-end",
        type=int,
        default=17,
        help="Hour to stop heating (0-23, default: 17 = 5pm)"
    )

    # System configuration
    parser.add_argument(
        "--compressor-type",
        type=str,
        default="small_neea",
        choices=["small_neea", "commercial_moderate", "commercial_large", "integrated_packaged"],
        help="HPWH compressor type (default: small_neea)"
    )
    parser.add_argument(
        "--tank-setpoint",
        type=float,
        default=140.0,
        help="Tank setpoint temperature °F (default: 140)"
    )
    parser.add_argument(
        "--tank-r-value",
        type=float,
        default=16.0,
        help="Tank insulation R-value (default: 16.0)"
    )
    parser.add_argument(
        "--compressor-cop",
        type=float,
        default=3.0,
        help="Heat pump COP (default: 3.0)"
    )

    # Output options
    parser.add_argument(
        "--json",
        type=str,
        help="Export results to JSON file"
    )
    parser.add_argument(
        "--cibd25-export",
        type=str,
        help="Export CIBD25 properties to JSON file"
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress detailed report output"
    )
    parser.add_argument(
        "--optimize",
        action="store_true",
        help="Shortcut: enable load shifting with 50% oversizing"
    )

    return parser.parse_args()


def extract_from_cibd25(file_path: str) -> Optional[BuildingProfile]:
    """
    Extract building data from CIBD25 file.

    Args:
        file_path: Path to CIBD25 file

    Returns:
        BuildingProfile if successful, None otherwise
    """
    try:
        # Try to import CIBD25 parser
        from eco_tools.translators.cibd25_importer import CIBD25Importer

        # Parse CIBD25 file
        importer = CIBD25Importer()
        model = importer.import_from_file(file_path)

        # Extract dwelling unit count
        # This is a simplified extraction - full implementation would
        # parse the complete CIBD25 structure
        num_units = 1  # Default
        total_bedrooms = 2  # Default

        # TODO: Implement full CIBD25 parsing to extract:
        # - ResProj:NumDwellingUnits
        # - Sum of DwellUnitType:NumBedrooms × NumDwellingUnits
        # - ResProj:ClimateZone

        print(f"Note: CIBD25 parsing not yet fully implemented.")
        print(f"Using defaults: {num_units} units, {total_bedrooms} bedrooms")

        return BuildingProfile(
            num_dwelling_units=num_units,
            total_bedrooms=total_bedrooms,
            climate_zone="12"
        )

    except Exception as e:
        print(f"Error reading CIBD25 file: {e}", file=sys.stderr)
        return None


def main():
    """Main CLI entry point."""
    args = parse_arguments()

    # Build configuration
    if args.optimize:
        # Optimization shortcut
        enable_load_shift = True
        oversize_factor = 1.5
    elif args.no_oversize:
        enable_load_shift = False
        oversize_factor = 1.0
    else:
        enable_load_shift = args.load_shift
        oversize_factor = args.oversize

    # Create building profile
    if args.units:
        # Manual input
        if not args.bedrooms:
            # Calculate from average
            total_bedrooms = int(args.units * args.avg_br)
        else:
            total_bedrooms = args.bedrooms

        building = BuildingProfile(
            num_dwelling_units=args.units,
            total_bedrooms=total_bedrooms,
            common_area_du_equiv=args.common_du_equiv,
            climate_zone=args.climate_zone
        )

    elif args.cibd25:
        # Extract from CIBD25 file
        building = extract_from_cibd25(args.cibd25)
        if building is None:
            sys.exit(1)

    else:
        print("Error: Must specify either --units or --cibd25", file=sys.stderr)
        sys.exit(1)

    # Create system configuration
    compressor_type_map = {
        "small_neea": HPWHCompressorType.SMALL_NEEA,
        "commercial_moderate": HPWHCompressorType.COMMERCIAL_MODERATE,
        "commercial_large": HPWHCompressorType.COMMERCIAL_LARGE,
        "integrated_packaged": HPWHCompressorType.INTEGRATED_PACKAGED,
    }

    config = HPWHSystemConfig(
        compressor_type=compressor_type_map[args.compressor_type],
        enable_load_shifting=enable_load_shift,
        oversizing_factor=oversize_factor,
        charge_start_hour=args.charge_start,
        charge_end_hour=args.charge_end,
        tank_setpoint_f=args.tank_setpoint,
        tank_r_value=args.tank_r_value,
        compressor_cop=args.compressor_cop,
    )

    # Perform sizing calculation
    results = CentralHPWHSizer.size_central_hpwh(building, config)

    # Generate and display report
    if not args.quiet:
        report = create_sizing_report(results)
        print(report)

    # Export to JSON if requested
    if args.json:
        output_data = {
            "building": {
                "num_dwelling_units": building.num_dwelling_units,
                "total_bedrooms": building.total_bedrooms,
                "common_area_du_equiv": building.common_area_du_equiv,
                "climate_zone": building.climate_zone,
            },
            "configuration": {
                "compressor_type": config.compressor_type.value,
                "enable_load_shifting": config.enable_load_shifting,
                "oversizing_factor": config.oversizing_factor,
                "charge_start_hour": config.charge_start_hour,
                "charge_end_hour": config.charge_end_hour,
                "tank_setpoint_f": config.tank_setpoint_f,
            },
            "results": {
                "minimum_tank_volume_gal": results.minimum_tank_volume_gal,
                "recommended_tank_volume_gal": results.recommended_tank_volume_gal,
                "final_tank_volume_gal": results.final_tank_volume_gal,
                "num_tanks": results.num_tanks,
                "volume_per_tank_gal": results.volume_per_tank_gal,
                "num_compressors": results.num_compressors,
                "compressor_capacity_kw": results.compressor_capacity_kw,
                "total_heating_capacity_kw": results.total_heating_capacity_kw,
                "thermal_storage_capacity_btu": results.thermal_storage_capacity_btu,
                "evening_peak_hours_covered": results.evening_peak_hours_covered,
                "load_shifting_benefit_pct": results.load_shifting_benefit_pct,
                "recovery_rate_gph": results.recovery_rate_gph,
            }
        }

        with open(args.json, 'w') as f:
            json.dump(output_data, f, indent=2)
        print(f"\nResults exported to: {args.json}")

    # Export CIBD25 properties if requested
    if args.cibd25_export:
        cibd25_dict = CentralHPWHSizer.export_to_cibd25_dict(results)
        with open(args.cibd25_export, 'w') as f:
            json.dump(cibd25_dict, f, indent=2)
        print(f"\nCIBD25 properties exported to: {args.cibd25_export}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
