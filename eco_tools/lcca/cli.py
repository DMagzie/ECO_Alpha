#!/usr/bin/env python3
"""
LCCA Command Line Interface.

Provides command-line access to LCCA functionality including:
- Auto-discovery of simulation outputs
- LCCA analysis with configurable rates and regions
- Report generation (Excel, PDF, text)
- Batch processing of multiple projects

Usage:
    python -m eco_tools.lcca.cli discover /path/to/project
    python -m eco_tools.lcca.cli analyze /path/to/project --rate-id PGE-E-ELEC
    python -m eco_tools.lcca.cli batch /path/to/projects --region US-CA-SF
    python -m eco_tools.lcca.cli list-rates
    python -m eco_tools.lcca.cli list-regions
"""

import argparse
import sys
import json
import logging
from pathlib import Path
from typing import Optional, List

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s: %(message)s"
)
logger = logging.getLogger(__name__)


def cmd_discover(args: argparse.Namespace) -> int:
    """Handle discover command."""
    from .auto_discovery import (
        discover_simulation_outputs,
        format_discovery_summary,
    )

    try:
        outputs = discover_simulation_outputs(
            args.project_dir,
            recursive=not args.no_recursive,
        )

        if args.json:
            print(json.dumps(outputs.summary(), indent=2))
        else:
            print(format_discovery_summary(outputs))

        if not outputs.is_complete:
            return 1

        return 0

    except FileNotFoundError as e:
        logger.error(str(e))
        return 1
    except Exception as e:
        logger.error(f"Discovery failed: {e}")
        return 1


def cmd_analyze(args: argparse.Namespace) -> int:
    """Handle analyze command."""
    from .lcca_runner import LccaRunner, OutputFormat, AnalysisMode

    try:
        runner = LccaRunner(args.project_dir)

        # Configure from arguments
        output_formats = []
        if args.excel or args.output:
            output_formats.append(OutputFormat.EXCEL)
        if args.text:
            output_formats.append(OutputFormat.TEXT)
        if args.json_output:
            output_formats.append(OutputFormat.JSON)

        mode = AnalysisMode.TOU
        if args.simple:
            mode = AnalysisMode.SIMPLE

        runner.configure(
            rate_id=args.rate_id,
            region=args.region,
            gas_rate=args.gas_rate,
            analysis_period=args.period,
            discount_rate=args.discount_rate,
            capex=args.capex,
            incentives=args.incentives,
            mode=mode,
            output_dir=Path(args.output) if args.output else None,
            output_formats=output_formats,
        )

        results = runner.run()

        # Print summary
        if args.verbose:
            runner.print_summary()
        else:
            _print_results_summary(results)

        # Print warnings
        for warning in results.warnings:
            logger.warning(warning)

        # Print output files
        if results.output_files:
            print("\nOutput files generated:")
            for f in results.output_files:
                print(f"  - {f}")

        return 0

    except Exception as e:
        logger.error(f"Analysis failed: {e}")
        if args.debug:
            import traceback
            traceback.print_exc()
        return 1


def cmd_batch(args: argparse.Namespace) -> int:
    """Handle batch command."""
    from .lcca_runner import batch_lcca

    try:
        results = batch_lcca(
            args.base_dir,
            rate_id=args.rate_id,
            region=args.region,
        )

        print(f"\nProcessed {len(results)} projects:")
        print("-" * 50)

        for result in results:
            status = "OK" if result.lcca_results else "FAILED"
            npv = f"${result.lcca_results.npv:,.0f}" if result.lcca_results else "N/A"
            print(f"  {result.project_name}: {status} (NPV: {npv})")

        return 0

    except Exception as e:
        logger.error(f"Batch processing failed: {e}")
        return 1


def cmd_list_rates(args: argparse.Namespace) -> int:
    """Handle list-rates command."""
    from .tariffs import list_available_tariffs

    tariffs = list_available_tariffs()

    if args.json:
        print(json.dumps(tariffs, indent=2))
    else:
        print("Available Utility Rates:")
        print("-" * 50)
        for rate_id in sorted(tariffs):
            print(f"  {rate_id}")
        print(f"\nTotal: {len(tariffs)} rates available")

    return 0


def cmd_list_regions(args: argparse.Namespace) -> int:
    """Handle list-regions command."""
    from .ca_hi_helpers import REGIONAL_FACTORS, CZ_TO_REGION

    if args.json:
        output = {
            "regions": REGIONAL_FACTORS,
            "climate_zone_mapping": CZ_TO_REGION,
        }
        print(json.dumps(output, indent=2))
    else:
        print("Available Regions (with cost factors):")
        print("-" * 50)

        # California
        print("\nCalifornia:")
        for code, factor in sorted(REGIONAL_FACTORS.items()):
            if code.startswith("US-CA"):
                print(f"  {code}: {factor:.2f}x")

        # Hawaii
        print("\nHawaii:")
        for code, factor in sorted(REGIONAL_FACTORS.items()):
            if code.startswith("US-HI"):
                print(f"  {code}: {factor:.2f}x")

        # Climate zone mapping
        print("\nClimate Zone to Region Mapping:")
        print("-" * 50)
        for cz, region in sorted(CZ_TO_REGION.items()):
            print(f"  {cz} → {region}")

    return 0


def cmd_zone_analyze(args: argparse.Namespace) -> int:
    """Handle zone-analyze command - analyze zone-level energy and costs."""
    from .zone_energy import ZoneEnergySummary, create_zone_energy_from_hourly
    from .cuac.models import ZoneType
    from .tariffs import calculate_tou_costs, create_pge_e_tou_c, HourlyUsage
    from .vnbt import (
        calculate_zone_vnbt,
        format_zone_vnbt_results,
        create_pge_e_elec_vnbt,
    )
    from datetime import date
    import csv

    try:
        run_dir = Path(args.project_dir)
        if not run_dir.exists():
            logger.error(f"Directory not found: {run_dir}")
            return 1

        # Find CSE output file
        cse_csv = None
        for pattern in ["*-AP-CSE.CSV", "*- AP-CSE.CSV", "*AP-CSE.csv"]:
            matches = list(run_dir.glob(pattern))
            if matches:
                cse_csv = matches[0]
                break

        if not cse_csv:
            # Try run subdirectory
            run_subdir = list(run_dir.glob("* - run"))
            if run_subdir:
                for pattern in ["*-AP-CSE.CSV", "*- AP-CSE.CSV", "*AP-CSE.csv"]:
                    matches = list(run_subdir[0].glob(pattern))
                    if matches:
                        cse_csv = matches[0]
                        break

        if not cse_csv:
            logger.error("CSE output file (*-AP-CSE.CSV) not found")
            return 1

        print(f"Parsing: {cse_csv.name}")

        # Parse CSE output - electric meters
        meters = {}
        building_pv_hourly = []

        # Parse CSE output - gas meters
        gas_meters = {}

        with open(cse_csv, 'r', encoding='latin-1') as f:
            reader = csv.reader(f)
            for _ in range(4):
                next(reader)

            for row in reader:
                if len(row) < 6:
                    continue
                meter_name = row[0].strip('"')
                if not meter_name or meter_name in ('Meter', ''):
                    continue

                # Detect if this is a gas meter (MtrGas or MtrNatGas prefix)
                is_gas_meter = meter_name.startswith('MtrGas') or meter_name.startswith('MtrNatGas')

                try:
                    if is_gas_meter:
                        # Gas meter: Tot column is in kBtu, convert to therms
                        total_kbtu = float(row[5]) if row[5] else 0.0
                        total_therm = total_kbtu / 100.0  # 100 kBtu = 1 therm

                        if meter_name not in gas_meters:
                            gas_meters[meter_name] = {'hourly_therm': []}
                        gas_meters[meter_name]['hourly_therm'].append(total_therm)
                    else:
                        # Electric meter
                        total_kwh = float(row[5]) if row[5] else 0.0
                        pv_kwh = abs(float(row[29])) if len(row) > 29 and row[29] else 0.0

                        if meter_name not in meters:
                            meters[meter_name] = {'hourly_kwh': [], 'hourly_pv': []}
                        meters[meter_name]['hourly_kwh'].append(total_kwh)
                        meters[meter_name]['hourly_pv'].append(pv_kwh)

                        if meter_name == 'MtrElec':
                            building_pv_hourly.append(pv_kwh)
                except (ValueError, IndexError):
                    continue

        print(f"Found {len(meters)} electric meters, {len(gas_meters)} gas meters")

        # Map electric meters to zones
        meter_to_zone = {
            'MtrElec_1bedrm': ('1BR Dwelling Units', ZoneType.DWELLING_UNIT, 1),
            'MtrElec_2bedrm': ('2BR Dwelling Units', ZoneType.DWELLING_UNIT, 2),
            'MtrElec_3bedrm': ('3BR Dwelling Units', ZoneType.DWELLING_UNIT, 3),
            'MtrElec2': ('Common Areas', ZoneType.COMMON_AREA, 0),
        }

        # Map gas meters to zones (parallel naming)
        gas_meter_to_zone = {
            'MtrGas_1bedrm': '1BR Dwelling Units',
            'MtrGas_2bedrm': '2BR Dwelling Units',
            'MtrGas_3bedrm': '3BR Dwelling Units',
            'MtrGas2': 'Common Areas',
            'MtrNatGas': 'Building Total',  # Fallback for building-level gas
        }

        zone_summaries = []
        zone_gas_data = {}  # zone_name -> hourly_therm list

        # First, collect gas data by zone
        for gas_meter_name, gas_data in gas_meters.items():
            zone_name = gas_meter_to_zone.get(gas_meter_name)
            if zone_name and len(gas_data['hourly_therm']) == 8760:
                zone_gas_data[zone_name] = gas_data['hourly_therm']

        # Create zone summaries with both electric and gas
        for meter_name, data in meters.items():
            if meter_name not in meter_to_zone:
                continue
            zone_name, zone_type, bedrooms = meter_to_zone[meter_name]
            if len(data['hourly_kwh']) != 8760:
                logger.warning(f"{meter_name} has {len(data['hourly_kwh'])} hours, expected 8760")
                continue

            # Get corresponding gas data if available
            hourly_gas = zone_gas_data.get(zone_name)

            summary = create_zone_energy_from_hourly(
                zone_name=zone_name,
                zone_type=zone_type,
                hourly_elec=data['hourly_kwh'],
                hourly_gas=hourly_gas,
                num_bedrooms=bedrooms,
            )
            zone_summaries.append(summary)

        if not zone_summaries:
            logger.error("No zone data found in CSE output")
            return 1

        # Calculate building-level gas from MtrNatGas if no zone-level gas
        building_gas_therm = 0.0
        if 'MtrNatGas' in gas_meters and len(gas_meters['MtrNatGas']['hourly_therm']) == 8760:
            building_gas_therm = sum(gas_meters['MtrNatGas']['hourly_therm'])
        elif gas_meters:
            # Sum all gas meters
            for gas_data in gas_meters.values():
                if len(gas_data['hourly_therm']) == 8760:
                    building_gas_therm += sum(gas_data['hourly_therm'])

        has_gas_data = building_gas_therm > 0 or any(z.gas_therm > 0 for z in zone_summaries)
        gas_rate = getattr(args, 'gas_rate', 1.80)  # Default $/therm

        print(f"Created {len(zone_summaries)} zone summaries")
        if has_gas_data:
            print(f"Gas data detected: {building_gas_therm:,.0f} therms (building total)")
        print()

        # Calculate costs based on mode
        if args.vnbt:
            print("=" * 80)
            print("ZONE-LEVEL V-NBT ANALYSIS")
            print("=" * 80)

            tariff = create_pge_e_elec_vnbt()
            vnbt_results = calculate_zone_vnbt(
                zones=zone_summaries,
                pv_hourly_generation=building_pv_hourly,
                tariff=tariff,
                allocation_method="by_consumption",
            )

            print(format_zone_vnbt_results(vnbt_results))

            if args.verbose:
                print("\nDetailed Breakdown:")
                print("-" * 80)
                for name, result in sorted(vnbt_results.items()):
                    print(f"\n  {name}:")
                    print(f"    Gross Load:       {result.gross_load_kwh:>12,.0f} kWh")
                    print(f"    PV Allocated:     {result.pv_allocated_kwh:>12,.0f} kWh ({result.pv_allocation_pct:.1f}%)")
                    print(f"    Self-Consumption: {result.self_consumption_kwh:>12,.0f} kWh")
                    print(f"    Grid Import:      {result.import_kwh:>12,.0f} kWh")
                    print(f"    Grid Export:      {result.export_kwh:>12,.0f} kWh")
                    print(f"    Net Annual Cost:  ${result.net_cost:>11,.2f}")

        else:
            # TOU analysis (default)
            print("=" * 80)
            if has_gas_data:
                print("ZONE-LEVEL TOU ANALYSIS (Electric + Gas)")
            else:
                print("ZONE-LEVEL TOU ANALYSIS")
            print("=" * 80)

            tariff = create_pge_e_tou_c()
            total_elec_cost = 0.0
            total_gas_cost = 0.0
            total_kwh = 0.0
            total_therm = 0.0

            for zone in zone_summaries:
                # Convert hourly to HourlyUsage
                hourly_usage = []
                hour_of_year = 0
                days_per_month = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]

                for month in range(1, 13):
                    for day in range(1, days_per_month[month - 1] + 1):
                        for hour in range(24):
                            if hour_of_year < len(zone.hourly_elec_kwh):
                                is_weekend = date(2024, month, day).weekday() >= 5
                                hourly_usage.append(HourlyUsage(
                                    month=month,
                                    day=day,
                                    hour=hour,
                                    kwh=zone.hourly_elec_kwh[hour_of_year],
                                    is_weekend=is_weekend,
                                ))
                            hour_of_year += 1

                breakdown = calculate_tou_costs(hourly_usage, tariff)
                elec_cost = breakdown.total_cost
                total_elec_cost += elec_cost
                total_kwh += zone.elec_kwh

                # Calculate gas cost (flat rate)
                zone_gas_therm = zone.gas_therm if zone.gas_therm else 0.0
                gas_cost = zone_gas_therm * gas_rate
                total_gas_cost += gas_cost
                total_therm += zone_gas_therm

                zone_total_cost = elec_cost + gas_cost

                print(f"\n{zone.zone_name}:")
                print(f"  Electric:      {zone.elec_kwh:>12,.0f} kWh  →  ${elec_cost:>11,.2f}")
                if zone_gas_therm > 0 or has_gas_data:
                    print(f"  Gas:           {zone_gas_therm:>12,.0f} therm →  ${gas_cost:>11,.2f}")
                    print(f"  TOTAL:                              ${zone_total_cost:>11,.2f}")
                if args.verbose:
                    print(f"    Summer On:   ${breakdown.summer_on_peak_cost:>11,.2f}")
                    print(f"    Summer Mid:  ${breakdown.summer_mid_peak_cost:>11,.2f}")
                    print(f"    Summer Off:  ${breakdown.summer_off_peak_cost:>11,.2f}")
                    print(f"    Winter On:   ${breakdown.winter_on_peak_cost:>11,.2f}")
                    print(f"    Winter Mid:  ${breakdown.winter_mid_peak_cost:>11,.2f}")
                    print(f"    Winter Off:  ${breakdown.winter_off_peak_cost:>11,.2f}")

            print()
            print("-" * 80)
            total_cost = total_elec_cost + total_gas_cost
            if has_gas_data:
                print(f"ELECTRIC: {total_kwh:>12,.0f} kWh   →  ${total_elec_cost:>11,.2f}/year")
                print(f"GAS:      {total_therm:>12,.0f} therm →  ${total_gas_cost:>11,.2f}/year  (@ ${gas_rate:.2f}/therm)")
                print(f"{'=' * 80}")
                print(f"TOTAL:                               ${total_cost:>11,.2f}/year")
            else:
                print(f"TOTAL: {total_kwh:,.0f} kWh  |  ${total_elec_cost:,.2f}/year")

        if args.json:
            # JSON output with both electric and gas
            output_data = {
                'zones': [
                    {
                        'name': z.zone_name,
                        'type': z.zone_type.value if hasattr(z.zone_type, 'value') else str(z.zone_type),
                        'annual_kwh': z.elec_kwh,
                        'annual_therm': z.gas_therm if z.gas_therm else 0.0,
                    }
                    for z in zone_summaries
                ],
                'summary': {
                    'total_elec_kwh': sum(z.elec_kwh for z in zone_summaries),
                    'total_gas_therm': sum(z.gas_therm for z in zone_summaries if z.gas_therm),
                    'gas_rate': gas_rate,
                    'has_gas': has_gas_data,
                }
            }
            print(json.dumps(output_data, indent=2))

        return 0

    except Exception as e:
        logger.error(f"Zone analysis failed: {e}")
        if args.debug:
            import traceback
            traceback.print_exc()
        return 1


def cmd_econ1(args: argparse.Namespace) -> int:
    """Handle econ1 command - generate ECON-1 report."""
    from .lcca_runner import LccaRunner
    from .econ1 import export_econ1_text, export_econ1_csv

    try:
        runner = LccaRunner(args.project_dir)
        runner.configure(
            rate_id=args.rate_id,
            region=args.region,
        )
        results = runner.run()

        if results.econ1_report is None:
            logger.error("Failed to generate ECON-1 report")
            return 1

        if args.output:
            output_path = Path(args.output)
            if output_path.suffix == ".csv":
                export_econ1_csv(results.econ1_report, str(output_path))
            else:
                with open(output_path, "w") as f:
                    f.write(export_econ1_text(results.econ1_report))
            print(f"ECON-1 report written to: {output_path}")
        else:
            print(export_econ1_text(results.econ1_report))

        return 0

    except Exception as e:
        logger.error(f"ECON-1 generation failed: {e}")
        return 1


def _print_results_summary(results) -> None:
    """Print a concise results summary."""
    print(f"\nLCCA Results: {results.project_name}")
    print("=" * 50)

    if results.lcca_results:
        r = results.lcca_results
        print(f"  NPV:                ${r.npv:,.0f}")
        print(f"  IRR:                {r.irr * 100:.1f}%" if r.irr else "  IRR:                N/A")
        print(f"  Simple Payback:     {r.simple_payback:.1f} years" if r.simple_payback else "  Simple Payback:     N/A")
        print(f"  Lifecycle Cost:     ${r.lifecycle_cost:,.0f}")
        print(f"  Annual Energy Cost: ${r.annual_energy_cost:,.0f}")

    if results.savings_vs_baseline is not None:
        print(f"\n  Savings vs Baseline: ${results.savings_vs_baseline:,.0f}")

    print(f"\n  Climate Zone: {results.climate_zone}")
    print(f"  Region:       {results.region}")
    print(f"  Rate ID:      {results.rate_id}")


def create_parser() -> argparse.ArgumentParser:
    """Create argument parser."""
    parser = argparse.ArgumentParser(
        prog="lcca",
        description="LCCA Command Line Interface for ECO Tools",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Discover simulation outputs
  lcca discover /path/to/project

  # Run LCCA analysis
  lcca analyze /path/to/project --rate-id PGE-E-ELEC --region US-CA-SF

  # Generate Excel report
  lcca analyze /path/to/project --excel --output ./reports/

  # Batch process multiple projects
  lcca batch /path/to/projects --region US-CA-LA

  # List available utility rates
  lcca list-rates

  # List available regions
  lcca list-regions
        """,
    )

    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug output",
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # discover command
    discover_parser = subparsers.add_parser(
        "discover",
        help="Discover simulation outputs in a project directory",
    )
    discover_parser.add_argument(
        "project_dir",
        help="Path to project directory",
    )
    discover_parser.add_argument(
        "--no-recursive",
        action="store_true",
        help="Don't search subdirectories",
    )
    discover_parser.add_argument(
        "--json",
        action="store_true",
        help="Output as JSON",
    )

    # analyze command
    analyze_parser = subparsers.add_parser(
        "analyze",
        help="Run LCCA analysis on a project",
    )
    analyze_parser.add_argument(
        "project_dir",
        help="Path to project directory",
    )
    analyze_parser.add_argument(
        "--rate-id",
        help="Utility rate identifier (e.g., PGE-E-ELEC)",
    )
    analyze_parser.add_argument(
        "--region",
        help="Regional cost factor code (e.g., US-CA-SF)",
    )
    analyze_parser.add_argument(
        "--gas-rate",
        type=float,
        default=1.50,
        help="Natural gas rate ($/therm)",
    )
    analyze_parser.add_argument(
        "--period",
        type=int,
        default=30,
        help="Analysis period in years (default: 30)",
    )
    analyze_parser.add_argument(
        "--discount-rate",
        type=float,
        default=0.05,
        help="Discount rate (default: 0.05)",
    )
    analyze_parser.add_argument(
        "--capex",
        type=float,
        default=0.0,
        help="Capital expenditure ($)",
    )
    analyze_parser.add_argument(
        "--incentives",
        type=float,
        default=0.0,
        help="Incentive amount ($)",
    )
    analyze_parser.add_argument(
        "--simple",
        action="store_true",
        help="Use simple annual rates instead of TOU",
    )
    analyze_parser.add_argument(
        "--output", "-o",
        help="Output directory for reports",
    )
    analyze_parser.add_argument(
        "--excel",
        action="store_true",
        help="Generate Excel report",
    )
    analyze_parser.add_argument(
        "--text",
        action="store_true",
        help="Generate text report",
    )
    analyze_parser.add_argument(
        "--json-output",
        action="store_true",
        help="Generate JSON output",
    )
    analyze_parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Verbose output",
    )

    # batch command
    batch_parser = subparsers.add_parser(
        "batch",
        help="Batch process multiple projects",
    )
    batch_parser.add_argument(
        "base_dir",
        help="Base directory containing project folders",
    )
    batch_parser.add_argument(
        "--rate-id",
        help="Common rate ID for all projects",
    )
    batch_parser.add_argument(
        "--region",
        help="Common region for all projects",
    )

    # list-rates command
    rates_parser = subparsers.add_parser(
        "list-rates",
        help="List available utility rates",
    )
    rates_parser.add_argument(
        "--json",
        action="store_true",
        help="Output as JSON",
    )

    # list-regions command
    regions_parser = subparsers.add_parser(
        "list-regions",
        help="List available regions and climate zone mappings",
    )
    regions_parser.add_argument(
        "--json",
        action="store_true",
        help="Output as JSON",
    )

    # econ1 command
    econ1_parser = subparsers.add_parser(
        "econ1",
        help="Generate ECON-1 report",
    )
    econ1_parser.add_argument(
        "project_dir",
        help="Path to project directory",
    )
    econ1_parser.add_argument(
        "--rate-id",
        help="Utility rate identifier",
    )
    econ1_parser.add_argument(
        "--region",
        help="Regional cost factor code",
    )
    econ1_parser.add_argument(
        "--output", "-o",
        help="Output file path (.txt or .csv)",
    )

    # zone-analyze command
    zone_parser = subparsers.add_parser(
        "zone-analyze",
        help="Analyze zone-level energy costs (TOU or V-NBT) with electric and gas",
    )
    zone_parser.add_argument(
        "project_dir",
        help="Path to CBECC run directory",
    )
    zone_parser.add_argument(
        "--vnbt",
        action="store_true",
        help="Calculate V-NBT costs with PV allocation (default: TOU)",
    )
    zone_parser.add_argument(
        "--gas-rate",
        type=float,
        default=1.80,
        help="Natural gas rate in $/therm (default: 1.80)",
    )
    zone_parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Show detailed cost breakdown per zone",
    )
    zone_parser.add_argument(
        "--json",
        action="store_true",
        help="Output zone data as JSON",
    )
    zone_parser.add_argument(
        "--debug",
        action="store_true",
        help="Show debug traceback on errors",
    )

    return parser


def main(argv: Optional[List[str]] = None) -> int:
    """Main entry point."""
    parser = create_parser()
    args = parser.parse_args(argv)

    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)

    if args.command is None:
        parser.print_help()
        return 0

    # Dispatch to command handler
    commands = {
        "discover": cmd_discover,
        "analyze": cmd_analyze,
        "batch": cmd_batch,
        "list-rates": cmd_list_rates,
        "list-regions": cmd_list_regions,
        "econ1": cmd_econ1,
        "zone-analyze": cmd_zone_analyze,
    }

    handler = commands.get(args.command)
    if handler:
        return handler(args)
    else:
        parser.print_help()
        return 1


if __name__ == "__main__":
    sys.exit(main())
