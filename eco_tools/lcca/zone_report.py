"""
Zone-Level LCCA Report Generator
================================

Comprehensive reporting for zone-level LCCA including:
- Building summary with NPV/IRR/payback
- Zone category breakdown (dwelling units, common areas)
- Per-zone detail tables
- CUAC utility allowance summaries
- Multi-format export (text, dict, Excel-ready)
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime

from .zone_energy import (
    ZoneEnergySummary, ZoneLccaResult, BuildingZoneLccaSummary,
    DwellingUnitSummary, CommonAreaSummary, CuacAllowanceResult,
)
from .zone_allocation import ZoneCostAllocator, calculate_zone_lcca
from .cuac.models import ZoneType, CuacConfig, DwellUnitAllocation
from .res_other.models import CommonAreaCategory
from .tariffs import TouTariff
from .calculators import LccaResults


# =============================================================================
# REPORT DATA CLASSES
# =============================================================================

@dataclass
class ZoneCategorySummary:
    """Summary of costs by zone category."""
    category_name: str
    zone_count: int = 0
    total_area_sqft: float = 0.0
    total_elec_kwh: float = 0.0
    total_gas_therm: float = 0.0
    total_annual_cost: float = 0.0
    avg_eui_kbtu_sqft: float = 0.0
    avg_cost_per_sqft: float = 0.0
    pct_of_building_cost: float = 0.0


@dataclass
class BedroomTypeSummary:
    """Summary for a specific bedroom type."""
    num_bedrooms: int
    unit_count: int = 0
    total_area_sqft: float = 0.0
    avg_area_sqft: float = 0.0
    avg_elec_kwh: float = 0.0
    avg_gas_therm: float = 0.0
    avg_annual_cost: float = 0.0
    utility_allowance_monthly: float = 0.0
    pv_per_unit_kwdc: float = 0.0
    battery_per_unit_kwh: float = 0.0


@dataclass
class CommonAreaCategorySummary:
    """Summary for a common area category."""
    category: CommonAreaCategory
    zone_count: int = 0
    total_area_sqft: float = 0.0
    total_elec_kwh: float = 0.0
    total_gas_therm: float = 0.0
    total_annual_cost: float = 0.0
    eui_kbtu_sqft: float = 0.0
    cost_per_sqft: float = 0.0
    zone_names: List[str] = field(default_factory=list)


@dataclass
class CuacSummaryReport:
    """CUAC utility allowance summary."""
    project_name: str = ""
    utility_name: str = ""
    tariff_name: str = ""
    report_date: str = ""

    # Per-bedroom allowances
    allowances_by_bedroom: Dict[int, CuacAllowanceResult] = field(default_factory=dict)

    # PV/Battery system info
    total_pv_kwdc: float = 0.0
    total_battery_kwh: float = 0.0
    pv_billing_option: str = ""

    # Building totals
    total_dwelling_units: int = 0
    total_annual_allowance: float = 0.0

    def get_allowance_table(self) -> List[Dict[str, Any]]:
        """Get allowance data as table rows."""
        rows = []
        for bedrooms in sorted(self.allowances_by_bedroom.keys()):
            allowance = self.allowances_by_bedroom[bedrooms]
            rows.append({
                'bedrooms': bedrooms,
                'gross_elec': allowance.gross_elec_allowance,
                'gross_gas': allowance.gross_gas_allowance,
                'gross_total': allowance.gross_total_allowance,
                'pv_credit': allowance.pv_credit_monthly,
                'battery_credit': allowance.battery_credit_monthly,
                'net_allowance': allowance.net_total_allowance,
            })
        return rows


@dataclass
class ZoneLccaReport:
    """
    Comprehensive zone-level LCCA report.

    Provides multi-level cost breakdown:
    - Building summary (NPV, IRR, payback)
    - Category breakdown (dwelling vs common)
    - Per-zone detail
    - CUAC utility allowances
    """

    # Report metadata
    report_title: str = "Zone-Level LCCA Report"
    report_date: str = field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d"))
    prepared_by: str = ""

    # Building info
    building_name: str = ""
    building_type: str = ""
    building_address: str = ""
    climate_zone: str = ""

    # Building metrics
    total_area_sqft: float = 0.0
    dwelling_unit_count: int = 0
    common_area_count: int = 0

    # Energy totals
    total_elec_kwh: float = 0.0
    total_gas_therm: float = 0.0
    total_eui_kbtu_sqft: float = 0.0

    # Cost totals
    total_annual_cost: float = 0.0
    dwelling_unit_cost: float = 0.0
    common_area_cost: float = 0.0

    # LCCA metrics (if building-level analysis available)
    lcca_results: Optional[LccaResults] = None

    # Zone summaries
    zone_summary: Optional[BuildingZoneLccaSummary] = None

    # Category breakdowns
    category_summaries: List[ZoneCategorySummary] = field(default_factory=list)
    bedroom_summaries: List[BedroomTypeSummary] = field(default_factory=list)
    common_area_summaries: List[CommonAreaCategorySummary] = field(default_factory=list)

    # Individual zone results
    zone_results: List[ZoneLccaResult] = field(default_factory=list)

    # CUAC report (for affordable housing)
    cuac_summary: Optional[CuacSummaryReport] = None

    # Tariff info
    tariff_name: str = ""
    utility_name: str = ""

    def __post_init__(self):
        """Calculate derived values."""
        if self.total_area_sqft > 0:
            elec_kbtu = self.total_elec_kwh * 3.412
            gas_kbtu = self.total_gas_therm * 100
            self.total_eui_kbtu_sqft = (elec_kbtu + gas_kbtu) / self.total_area_sqft

    @property
    def has_lcca(self) -> bool:
        """True if building-level LCCA results are available."""
        return self.lcca_results is not None

    @property
    def has_cuac(self) -> bool:
        """True if CUAC summary is available."""
        return self.cuac_summary is not None

    def get_executive_summary(self) -> Dict[str, Any]:
        """Get executive summary metrics."""
        summary = {
            'building_name': self.building_name,
            'total_area_sqft': self.total_area_sqft,
            'dwelling_units': self.dwelling_unit_count,
            'common_areas': self.common_area_count,
            'total_elec_kwh': self.total_elec_kwh,
            'total_gas_therm': self.total_gas_therm,
            'total_eui': self.total_eui_kbtu_sqft,
            'total_annual_cost': self.total_annual_cost,
        }

        if self.has_lcca:
            summary.update({
                'npv': self.lcca_results.npv,
                'irr': self.lcca_results.irr,
                'simple_payback': self.lcca_results.simple_payback_years,
                'lifecycle_savings': self.lcca_results.lifecycle_savings,
            })

        return summary

    def get_cost_breakdown(self) -> Dict[str, float]:
        """Get cost breakdown by category."""
        breakdown = {
            'dwelling_units': self.dwelling_unit_cost,
            'common_areas': self.common_area_cost,
            'total': self.total_annual_cost,
        }

        # Add common area category breakdown
        for ca_summary in self.common_area_summaries:
            key = f"common_{ca_summary.category.value}"
            breakdown[key] = ca_summary.total_annual_cost

        return breakdown

    def to_dict(self) -> Dict[str, Any]:
        """Convert report to dictionary."""
        return {
            'metadata': {
                'report_title': self.report_title,
                'report_date': self.report_date,
                'prepared_by': self.prepared_by,
            },
            'building': {
                'name': self.building_name,
                'type': self.building_type,
                'address': self.building_address,
                'climate_zone': self.climate_zone,
                'total_area_sqft': self.total_area_sqft,
            },
            'summary': self.get_executive_summary(),
            'cost_breakdown': self.get_cost_breakdown(),
            'bedroom_summaries': [
                {
                    'bedrooms': bs.num_bedrooms,
                    'unit_count': bs.unit_count,
                    'avg_annual_cost': bs.avg_annual_cost,
                    'utility_allowance': bs.utility_allowance_monthly,
                }
                for bs in self.bedroom_summaries
            ],
            'common_area_summaries': [
                {
                    'category': cas.category.value,
                    'zone_count': cas.zone_count,
                    'total_cost': cas.total_annual_cost,
                    'eui': cas.eui_kbtu_sqft,
                }
                for cas in self.common_area_summaries
            ],
            'zones': [z.to_dict() for z in self.zone_results],
        }


# =============================================================================
# REPORT GENERATION
# =============================================================================

def generate_zone_lcca_report(
    zone_summaries: List[ZoneEnergySummary],
    tariff: TouTariff,
    building_name: str = "",
    building_type: str = "Multifamily",
    climate_zone: str = "",
    cuac_config: Optional[CuacConfig] = None,
    lcca_results: Optional[LccaResults] = None,
    prepared_by: str = "",
) -> ZoneLccaReport:
    """
    Generate comprehensive zone-level LCCA report.

    Args:
        zone_summaries: List of zone energy summaries
        tariff: TOU tariff for cost calculations
        building_name: Building name for report
        building_type: Building type (e.g., "Multifamily", "Mixed-Use")
        climate_zone: Climate zone (e.g., "CZ12")
        cuac_config: Optional CUAC configuration
        lcca_results: Optional building-level LCCA results
        prepared_by: Report preparer name

    Returns:
        ZoneLccaReport with all calculations
    """
    # Calculate zone costs
    allocator = ZoneCostAllocator(
        zone_summaries=zone_summaries,
        tariff=tariff,
        cuac_config=cuac_config,
    )
    zone_summary = allocator.allocate_all()

    # Create report
    report = ZoneLccaReport(
        building_name=building_name,
        building_type=building_type,
        climate_zone=climate_zone,
        prepared_by=prepared_by,
        tariff_name=tariff.name,
        utility_name=tariff.utility,
        lcca_results=lcca_results,
        zone_summary=zone_summary,
    )

    # Populate from zone summary
    report.total_area_sqft = zone_summary.total_area_sqft
    report.dwelling_unit_count = zone_summary.dwelling_unit_count
    report.common_area_count = zone_summary.common_area_count
    report.total_elec_kwh = zone_summary.total_elec_kwh
    report.total_gas_therm = zone_summary.total_gas_therm
    report.total_annual_cost = zone_summary.total_annual_cost
    report.dwelling_unit_cost = zone_summary.dwelling_unit_cost
    report.common_area_cost = zone_summary.common_area_cost
    report.zone_results = zone_summary.zone_results

    # Build category summaries
    report.category_summaries = _build_category_summaries(zone_summary)

    # Build bedroom summaries
    report.bedroom_summaries = _build_bedroom_summaries(zone_summary)

    # Build common area summaries
    report.common_area_summaries = _build_common_area_summaries(zone_summary)

    # Build CUAC summary if config provided
    if cuac_config:
        report.cuac_summary = _build_cuac_summary(
            zone_summary, allocator, cuac_config, tariff
        )

    return report


def _build_category_summaries(
    zone_summary: BuildingZoneLccaSummary
) -> List[ZoneCategorySummary]:
    """Build high-level category summaries."""
    summaries = []
    total_cost = zone_summary.total_annual_cost or 1.0  # Avoid division by zero

    # Dwelling units summary
    dwelling_area = zone_summary.dwelling_unit_area
    dwelling_elec = sum(
        ds.total_elec_kwh for ds in zone_summary.dwelling_summaries.values()
    )
    dwelling_gas = sum(
        ds.total_gas_therm for ds in zone_summary.dwelling_summaries.values()
    )
    dwelling_cost = zone_summary.dwelling_unit_cost

    if dwelling_area > 0:
        dwelling_eui = ((dwelling_elec * 3.412) + (dwelling_gas * 100)) / dwelling_area
    else:
        dwelling_eui = 0.0

    summaries.append(ZoneCategorySummary(
        category_name="Dwelling Units",
        zone_count=zone_summary.dwelling_unit_count,
        total_area_sqft=dwelling_area,
        total_elec_kwh=dwelling_elec,
        total_gas_therm=dwelling_gas,
        total_annual_cost=dwelling_cost,
        avg_eui_kbtu_sqft=dwelling_eui,
        avg_cost_per_sqft=dwelling_cost / dwelling_area if dwelling_area > 0 else 0,
        pct_of_building_cost=dwelling_cost / total_cost * 100,
    ))

    # Common areas summary
    common_area = zone_summary.common_area_total
    common_elec = sum(
        cs.total_elec_kwh for cs in zone_summary.common_summaries.values()
    )
    common_gas = sum(
        cs.total_gas_therm for cs in zone_summary.common_summaries.values()
    )
    common_cost = zone_summary.common_area_cost

    if common_area > 0:
        common_eui = ((common_elec * 3.412) + (common_gas * 100)) / common_area
    else:
        common_eui = 0.0

    summaries.append(ZoneCategorySummary(
        category_name="Common Areas",
        zone_count=zone_summary.common_area_count,
        total_area_sqft=common_area,
        total_elec_kwh=common_elec,
        total_gas_therm=common_gas,
        total_annual_cost=common_cost,
        avg_eui_kbtu_sqft=common_eui,
        avg_cost_per_sqft=common_cost / common_area if common_area > 0 else 0,
        pct_of_building_cost=common_cost / total_cost * 100,
    ))

    return summaries


def _build_bedroom_summaries(
    zone_summary: BuildingZoneLccaSummary
) -> List[BedroomTypeSummary]:
    """Build per-bedroom-count summaries."""
    summaries = []

    for bedrooms in sorted(zone_summary.dwelling_summaries.keys()):
        ds = zone_summary.dwelling_summaries[bedrooms]
        summaries.append(BedroomTypeSummary(
            num_bedrooms=bedrooms,
            unit_count=ds.unit_count,
            total_area_sqft=ds.total_area_sqft,
            avg_area_sqft=ds.avg_area_sqft,
            avg_elec_kwh=ds.avg_elec_kwh,
            avg_gas_therm=ds.avg_gas_therm,
            avg_annual_cost=ds.avg_annual_cost,
            utility_allowance_monthly=ds.utility_allowance_monthly,
            pv_per_unit_kwdc=ds.pv_per_unit_kwdc,
            battery_per_unit_kwh=ds.battery_per_unit_kwh,
        ))

    return summaries


def _build_common_area_summaries(
    zone_summary: BuildingZoneLccaSummary
) -> List[CommonAreaCategorySummary]:
    """Build per-category common area summaries."""
    summaries = []

    for category in sorted(zone_summary.common_summaries.keys(), key=lambda x: x.value):
        cs = zone_summary.common_summaries[category]
        summaries.append(CommonAreaCategorySummary(
            category=category,
            zone_count=cs.zone_count,
            total_area_sqft=cs.total_area_sqft,
            total_elec_kwh=cs.total_elec_kwh,
            total_gas_therm=cs.total_gas_therm,
            total_annual_cost=cs.total_annual_cost,
            eui_kbtu_sqft=cs.eui_kbtu_sqft,
            cost_per_sqft=cs.cost_per_sqft,
            zone_names=cs.zone_names.copy(),
        ))

    return summaries


def _build_cuac_summary(
    zone_summary: BuildingZoneLccaSummary,
    allocator: ZoneCostAllocator,
    cuac_config: CuacConfig,
    tariff: TouTariff,
) -> CuacSummaryReport:
    """Build CUAC utility allowance summary."""
    cuac_summary = CuacSummaryReport(
        utility_name=cuac_config.elec_utility or tariff.utility,
        tariff_name=cuac_config.elec_tariff or tariff.name,
        report_date=datetime.now().strftime("%Y-%m-%d"),
        total_pv_kwdc=cuac_config.affordable_pv_dc_sys_size or 0.0,
        total_battery_kwh=cuac_config.affordable_batt_max_cap or 0.0,
        pv_billing_option=cuac_config.pv_billing_option,
    )

    # Calculate allowances by bedroom count
    allowances = allocator.calculate_cuac_allowances()
    cuac_summary.allowances_by_bedroom = allowances

    # Calculate totals
    total_units = sum(ds.unit_count for ds in zone_summary.dwelling_summaries.values())
    cuac_summary.total_dwelling_units = total_units

    total_allowance = 0.0
    for bedrooms, ds in zone_summary.dwelling_summaries.items():
        if bedrooms in allowances:
            total_allowance += ds.unit_count * allowances[bedrooms].net_total_allowance * 12
    cuac_summary.total_annual_allowance = total_allowance

    return cuac_summary


# =============================================================================
# TEXT FORMATTING
# =============================================================================

def format_zone_report(report: ZoneLccaReport) -> str:
    """
    Format zone LCCA report as text.

    Args:
        report: ZoneLccaReport to format

    Returns:
        Formatted text report
    """
    lines = []
    w = 70  # Line width

    # Header
    lines.append("=" * w)
    lines.append(report.report_title.center(w))
    lines.append("=" * w)
    lines.append("")

    # Metadata
    lines.append(f"Building: {report.building_name or 'N/A'}")
    lines.append(f"Type: {report.building_type}")
    if report.climate_zone:
        lines.append(f"Climate Zone: {report.climate_zone}")
    lines.append(f"Report Date: {report.report_date}")
    if report.prepared_by:
        lines.append(f"Prepared By: {report.prepared_by}")
    lines.append("")

    # Executive Summary
    lines.append("-" * w)
    lines.append("EXECUTIVE SUMMARY")
    lines.append("-" * w)
    lines.append(f"  Total Conditioned Area: {report.total_area_sqft:,.0f} sqft")
    lines.append(f"  Dwelling Units: {report.dwelling_unit_count}")
    lines.append(f"  Common Area Zones: {report.common_area_count}")
    lines.append("")
    lines.append(f"  Annual Electricity: {report.total_elec_kwh:,.0f} kWh")
    lines.append(f"  Annual Gas: {report.total_gas_therm:,.0f} therms")
    lines.append(f"  Site EUI: {report.total_eui_kbtu_sqft:.1f} kBtu/sqft")
    lines.append("")
    lines.append(f"  Total Annual Cost: ${report.total_annual_cost:,.2f}")
    lines.append(f"    Dwelling Units: ${report.dwelling_unit_cost:,.2f}")
    lines.append(f"    Common Areas: ${report.common_area_cost:,.2f}")

    if report.has_lcca:
        lines.append("")
        lines.append("  Lifecycle Analysis:")
        lines.append(f"    NPV: ${report.lcca_results.npv:,.0f}")
        if report.lcca_results.irr:
            lines.append(f"    IRR: {report.lcca_results.irr * 100:.1f}%")
        if report.lcca_results.simple_payback_years:
            lines.append(f"    Simple Payback: {report.lcca_results.simple_payback_years:.1f} years")
    lines.append("")

    # Category Breakdown
    lines.append("-" * w)
    lines.append("COST BY CATEGORY")
    lines.append("-" * w)
    for cs in report.category_summaries:
        lines.append(f"  {cs.category_name}:")
        lines.append(f"    Zones: {cs.zone_count}")
        lines.append(f"    Area: {cs.total_area_sqft:,.0f} sqft")
        lines.append(f"    Annual Cost: ${cs.total_annual_cost:,.2f} ({cs.pct_of_building_cost:.1f}%)")
        lines.append(f"    EUI: {cs.avg_eui_kbtu_sqft:.1f} kBtu/sqft")
        lines.append("")

    # Dwelling Units by Bedroom
    if report.bedroom_summaries:
        lines.append("-" * w)
        lines.append("DWELLING UNITS BY BEDROOM COUNT")
        lines.append("-" * w)
        for bs in report.bedroom_summaries:
            lines.append(f"  {bs.num_bedrooms}-Bedroom Units:")
            lines.append(f"    Count: {bs.unit_count}")
            lines.append(f"    Avg Area: {bs.avg_area_sqft:,.0f} sqft")
            lines.append(f"    Avg Annual Cost: ${bs.avg_annual_cost:,.2f}")
            if bs.utility_allowance_monthly > 0:
                lines.append(f"    Utility Allowance: ${bs.utility_allowance_monthly:,.2f}/month")
            if bs.pv_per_unit_kwdc > 0:
                lines.append(f"    PV Allocation: {bs.pv_per_unit_kwdc:.2f} kWdc")
            lines.append("")

    # Common Areas by Category
    if report.common_area_summaries:
        lines.append("-" * w)
        lines.append("COMMON AREAS BY CATEGORY")
        lines.append("-" * w)
        for cas in report.common_area_summaries:
            lines.append(f"  {cas.category.value.title()}:")
            lines.append(f"    Zones: {cas.zone_count}")
            lines.append(f"    Area: {cas.total_area_sqft:,.0f} sqft")
            lines.append(f"    Annual Cost: ${cas.total_annual_cost:,.2f}")
            lines.append(f"    EUI: {cas.eui_kbtu_sqft:.1f} kBtu/sqft")
            lines.append("")

    # CUAC Summary
    if report.has_cuac:
        lines.append("-" * w)
        lines.append("CUAC UTILITY ALLOWANCE SUMMARY")
        lines.append("-" * w)
        cuac = report.cuac_summary
        lines.append(f"  Utility: {cuac.utility_name}")
        lines.append(f"  Tariff: {cuac.tariff_name}")
        if cuac.total_pv_kwdc > 0:
            lines.append(f"  PV System: {cuac.total_pv_kwdc:.1f} kWdc")
            lines.append(f"  Billing Option: {cuac.pv_billing_option}")
        lines.append("")
        lines.append("  Monthly Allowances by Bedroom:")
        for row in cuac.get_allowance_table():
            lines.append(
                f"    {row['bedrooms']}-BR: "
                f"${row['gross_total']:.2f} gross - "
                f"${row['pv_credit']:.2f} PV = "
                f"${row['net_allowance']:.2f} net"
            )
        lines.append("")

    # Tariff Info
    lines.append("-" * w)
    lines.append("UTILITY & TARIFF")
    lines.append("-" * w)
    lines.append(f"  Utility: {report.utility_name}")
    lines.append(f"  Tariff: {report.tariff_name}")
    lines.append("")

    lines.append("=" * w)

    return "\n".join(lines)


def format_cuac_allowance_table(report: ZoneLccaReport) -> str:
    """
    Format CUAC allowance table for HUD reporting.

    Args:
        report: ZoneLccaReport with CUAC summary

    Returns:
        Formatted table string
    """
    if not report.has_cuac:
        return "No CUAC data available."

    cuac = report.cuac_summary
    lines = []

    # Header
    lines.append("CUAC UTILITY ALLOWANCE SCHEDULE")
    lines.append(f"Project: {report.building_name}")
    lines.append(f"Date: {cuac.report_date}")
    lines.append(f"Utility: {cuac.utility_name}")
    lines.append("")

    # Table header
    lines.append("-" * 80)
    lines.append(
        f"{'BR':>4} | {'Elec':>10} | {'Gas':>10} | {'Gross':>10} | "
        f"{'PV Credit':>10} | {'Net Allow':>10}"
    )
    lines.append("-" * 80)

    # Table rows
    for row in cuac.get_allowance_table():
        lines.append(
            f"{row['bedrooms']:>4} | "
            f"${row['gross_elec']:>9.2f} | "
            f"${row['gross_gas']:>9.2f} | "
            f"${row['gross_total']:>9.2f} | "
            f"${row['pv_credit']:>9.2f} | "
            f"${row['net_allowance']:>9.2f}"
        )

    lines.append("-" * 80)
    lines.append("")

    if cuac.total_pv_kwdc > 0:
        lines.append(f"PV System Size: {cuac.total_pv_kwdc:.1f} kWdc")
        lines.append(f"PV Billing: {cuac.pv_billing_option}")

    return "\n".join(lines)


def format_zone_detail_table(report: ZoneLccaReport) -> str:
    """
    Format detailed zone-by-zone table.

    Args:
        report: ZoneLccaReport

    Returns:
        Formatted table string
    """
    lines = []

    lines.append("ZONE DETAIL TABLE")
    lines.append("-" * 100)
    lines.append(
        f"{'Zone Name':<30} | {'Type':<12} | {'Area':>8} | "
        f"{'kWh':>10} | {'Therm':>8} | {'Annual $':>10}"
    )
    lines.append("-" * 100)

    for zone in report.zone_results:
        zone_type = "Dwelling" if zone.is_dwelling_unit else "Common"
        lines.append(
            f"{zone.zone_name[:30]:<30} | "
            f"{zone_type:<12} | "
            f"{zone.area_sqft:>8,.0f} | "
            f"{zone.annual_elec_kwh:>10,.0f} | "
            f"{zone.annual_gas_therm:>8,.0f} | "
            f"${zone.net_total_cost:>9,.2f}"
        )

    lines.append("-" * 100)
    lines.append(
        f"{'TOTAL':<30} | "
        f"{'':12} | "
        f"{report.total_area_sqft:>8,.0f} | "
        f"{report.total_elec_kwh:>10,.0f} | "
        f"{report.total_gas_therm:>8,.0f} | "
        f"${report.total_annual_cost:>9,.2f}"
    )

    return "\n".join(lines)


# =============================================================================
# EXCEL-READY DATA EXPORT
# =============================================================================

def get_excel_sheets_data(report: ZoneLccaReport) -> Dict[str, List[Dict[str, Any]]]:
    """
    Get report data formatted for Excel export.

    Returns dict with sheet names as keys and list of row dicts as values.

    Args:
        report: ZoneLccaReport

    Returns:
        Dict of {sheet_name: [row_dicts]}
    """
    sheets = {}

    # Summary sheet
    sheets['Summary'] = [{
        'Metric': 'Building Name',
        'Value': report.building_name,
    }, {
        'Metric': 'Building Type',
        'Value': report.building_type,
    }, {
        'Metric': 'Climate Zone',
        'Value': report.climate_zone,
    }, {
        'Metric': 'Total Area (sqft)',
        'Value': report.total_area_sqft,
    }, {
        'Metric': 'Dwelling Units',
        'Value': report.dwelling_unit_count,
    }, {
        'Metric': 'Common Area Zones',
        'Value': report.common_area_count,
    }, {
        'Metric': 'Total Electricity (kWh)',
        'Value': report.total_elec_kwh,
    }, {
        'Metric': 'Total Gas (therms)',
        'Value': report.total_gas_therm,
    }, {
        'Metric': 'Site EUI (kBtu/sqft)',
        'Value': report.total_eui_kbtu_sqft,
    }, {
        'Metric': 'Total Annual Cost ($)',
        'Value': report.total_annual_cost,
    }, {
        'Metric': 'Dwelling Unit Cost ($)',
        'Value': report.dwelling_unit_cost,
    }, {
        'Metric': 'Common Area Cost ($)',
        'Value': report.common_area_cost,
    }]

    if report.has_lcca:
        sheets['Summary'].extend([{
            'Metric': 'NPV ($)',
            'Value': report.lcca_results.npv,
        }, {
            'Metric': 'IRR (%)',
            'Value': (report.lcca_results.irr or 0) * 100,
        }, {
            'Metric': 'Simple Payback (years)',
            'Value': report.lcca_results.simple_payback_years or 0,
        }])

    # Zone Detail sheet
    sheets['Zone Detail'] = []
    for zone in report.zone_results:
        sheets['Zone Detail'].append({
            'Zone Name': zone.zone_name,
            'Type': 'Dwelling Unit' if zone.is_dwelling_unit else 'Common Area',
            'Category': zone.category.value if zone.category else '',
            'Area (sqft)': zone.area_sqft,
            'Bedrooms': zone.num_bedrooms if zone.is_dwelling_unit else '',
            'Elec (kWh)': zone.annual_elec_kwh,
            'Gas (therms)': zone.annual_gas_therm,
            'Gross Elec Cost ($)': zone.gross_elec_cost,
            'Gross Gas Cost ($)': zone.gross_gas_cost,
            'PV Credit ($)': zone.pv_credit,
            'Net Annual Cost ($)': zone.net_total_cost,
        })

    # Dwelling Units sheet
    sheets['Dwelling Units'] = []
    for bs in report.bedroom_summaries:
        sheets['Dwelling Units'].append({
            'Bedrooms': bs.num_bedrooms,
            'Unit Count': bs.unit_count,
            'Total Area (sqft)': bs.total_area_sqft,
            'Avg Area (sqft)': bs.avg_area_sqft,
            'Avg Elec (kWh)': bs.avg_elec_kwh,
            'Avg Gas (therms)': bs.avg_gas_therm,
            'Avg Annual Cost ($)': bs.avg_annual_cost,
            'Utility Allowance ($/mo)': bs.utility_allowance_monthly,
            'PV per Unit (kWdc)': bs.pv_per_unit_kwdc,
            'Battery per Unit (kWh)': bs.battery_per_unit_kwh,
        })

    # Common Areas sheet
    sheets['Common Areas'] = []
    for cas in report.common_area_summaries:
        sheets['Common Areas'].append({
            'Category': cas.category.value.title(),
            'Zone Count': cas.zone_count,
            'Total Area (sqft)': cas.total_area_sqft,
            'Elec (kWh)': cas.total_elec_kwh,
            'Gas (therms)': cas.total_gas_therm,
            'Annual Cost ($)': cas.total_annual_cost,
            'EUI (kBtu/sqft)': cas.eui_kbtu_sqft,
            'Cost per sqft ($)': cas.cost_per_sqft,
        })

    # CUAC Allowances sheet
    if report.has_cuac:
        sheets['CUAC Allowances'] = []
        for row in report.cuac_summary.get_allowance_table():
            sheets['CUAC Allowances'].append({
                'Bedrooms': row['bedrooms'],
                'Elec Allowance ($)': row['gross_elec'],
                'Gas Allowance ($)': row['gross_gas'],
                'Gross Allowance ($)': row['gross_total'],
                'PV Credit ($)': row['pv_credit'],
                'Battery Credit ($)': row['battery_credit'],
                'Net Allowance ($)': row['net_allowance'],
            })

    return sheets


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def create_zone_report_from_allocations(
    zone_allocations: List[DwellUnitAllocation],
    building_elec_kwh: float,
    building_gas_therm: float,
    tariff: TouTariff,
    building_name: str = "",
    cuac_config: Optional[CuacConfig] = None,
) -> ZoneLccaReport:
    """
    Create zone report from allocations and building totals.

    Convenience function that estimates zone energy from building totals
    and generates a complete report.

    Args:
        zone_allocations: List of zone allocations
        building_elec_kwh: Building total electricity
        building_gas_therm: Building total gas
        tariff: TOU tariff
        building_name: Building name
        cuac_config: Optional CUAC config

    Returns:
        ZoneLccaReport
    """
    from .zone_allocation import estimate_zone_energy_from_building

    # Estimate zone energy from building totals
    zone_summaries = estimate_zone_energy_from_building(
        building_elec_kwh=building_elec_kwh,
        building_gas_therm=building_gas_therm,
        zone_allocations=zone_allocations,
    )

    return generate_zone_lcca_report(
        zone_summaries=zone_summaries,
        tariff=tariff,
        building_name=building_name,
        cuac_config=cuac_config,
    )
