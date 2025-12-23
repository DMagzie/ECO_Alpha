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
    }

    handler = commands.get(args.command)
    if handler:
        return handler(args)
    else:
        parser.print_help()
        return 1


if __name__ == "__main__":
    sys.exit(main())
