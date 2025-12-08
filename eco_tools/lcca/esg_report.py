"""
ESG (Environmental, Social, Governance) Report Generator.

Provides:
- Carbon emissions calculations
- Environmental impact metrics
- ESG-formatted sustainability reports
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional
from enum import Enum

from .model import SimulationOutput, AnnualEnergySummary


class EmissionsSource(Enum):
    """Source categories for emissions."""
    SCOPE_1 = "scope_1"  # Direct emissions (on-site combustion)
    SCOPE_2 = "scope_2"  # Indirect emissions (purchased electricity)
    SCOPE_3 = "scope_3"  # Other indirect (supply chain, etc.)


@dataclass
class EmissionFactors:
    """
    CO2 emission factors by region/grid.

    Default values are approximate US averages (2024).
    Units: kg CO2e per unit
    """
    # Electricity (kg CO2e per kWh)
    elec_kg_per_kwh: float = 0.386  # US average grid

    # Natural gas (kg CO2e per therm)
    gas_kg_per_therm: float = 5.3  # Direct combustion

    # Propane (kg CO2e per gallon)
    propane_kg_per_gallon: float = 5.8

    # Source identification
    source: str = "EPA eGRID 2024"
    region: str = "US Average"


@dataclass
class CarbonFootprint:
    """Carbon footprint calculation results."""

    # Scope 1 - Direct emissions (on-site gas, propane, diesel)
    scope_1_kg: float = 0.0
    scope_1_breakdown: Dict[str, float] = field(default_factory=dict)

    # Scope 2 - Indirect (purchased electricity)
    scope_2_kg: float = 0.0
    scope_2_breakdown: Dict[str, float] = field(default_factory=dict)

    # Totals
    total_kg: float = 0.0
    total_tonnes: float = 0.0

    # Per-area metrics
    kg_per_sf: float = 0.0
    kg_per_unit: float = 0.0  # For residential

    # Reductions
    avoided_kg: float = 0.0  # From PV/renewables
    net_kg: float = 0.0

    @property
    def total_metric_tons(self) -> float:
        """Total in metric tons (tonnes)."""
        return self.total_kg / 1000


@dataclass
class EsgMetrics:
    """Complete ESG metrics for a building/project."""

    # Environmental
    carbon: CarbonFootprint = field(default_factory=CarbonFootprint)
    energy_use_intensity_kbtu_sf: float = 0.0
    renewable_energy_pct: float = 0.0
    water_use_gal: float = 0.0  # If available

    # Social (placeholders for future expansion)
    indoor_air_quality_score: Optional[float] = None
    thermal_comfort_score: Optional[float] = None
    daylight_score: Optional[float] = None

    # Governance/Certifications
    leed_target: str = ""
    energy_star_score: Optional[int] = None
    title24_margin_pct: float = 0.0


@dataclass
class EsgReport:
    """Complete ESG report for a building."""

    project_name: str
    building_type: str
    conditioned_area_sf: float
    analysis_year: int = 2024

    # Proposed building metrics
    proposed: EsgMetrics = field(default_factory=EsgMetrics)

    # Baseline for comparison (optional)
    baseline: Optional[EsgMetrics] = None

    # Reductions vs baseline
    carbon_reduction_pct: float = 0.0
    energy_reduction_pct: float = 0.0
    cost_reduction_pct: float = 0.0


# ---- California-specific emission factors ----

CA_EMISSION_FACTORS = EmissionFactors(
    elec_kg_per_kwh=0.225,  # CAMX grid (cleaner than US average)
    gas_kg_per_therm=5.3,
    source="EPA eGRID CAMX 2024",
    region="California (CAMX)"
)

US_AVERAGE_FACTORS = EmissionFactors(
    elec_kg_per_kwh=0.386,
    gas_kg_per_therm=5.3,
    source="EPA eGRID 2024",
    region="US Average"
)


def calculate_carbon_footprint(
    annual: AnnualEnergySummary,
    factors: Optional[EmissionFactors] = None,
    area_sf: float = 0.0,
    units: int = 0
) -> CarbonFootprint:
    """
    Calculate carbon footprint from annual energy consumption.

    Args:
        annual: Annual energy summary
        factors: Emission factors (defaults to CA)
        area_sf: Building area for intensity calc
        units: Number of dwelling units (for residential)

    Returns:
        CarbonFootprint with all metrics
    """
    if factors is None:
        factors = CA_EMISSION_FACTORS

    result = CarbonFootprint()

    # Scope 1: Direct emissions (natural gas on-site)
    gas_emissions = annual.total_gas_therm * factors.gas_kg_per_therm
    result.scope_1_kg = gas_emissions
    result.scope_1_breakdown = {
        "natural_gas": gas_emissions
    }

    # Scope 2: Indirect (purchased electricity)
    elec_emissions = annual.total_elec_kwh * factors.elec_kg_per_kwh
    result.scope_2_kg = elec_emissions
    result.scope_2_breakdown = {
        "electricity": elec_emissions
    }

    # Totals
    result.total_kg = result.scope_1_kg + result.scope_2_kg
    result.total_tonnes = result.total_kg / 1000

    # Per-area metrics
    if area_sf > 0:
        result.kg_per_sf = result.total_kg / area_sf

    if units > 0:
        result.kg_per_unit = result.total_kg / units

    # Avoided emissions from PV
    if annual.pv_generation_kwh > 0:
        result.avoided_kg = annual.pv_generation_kwh * factors.elec_kg_per_kwh

    result.net_kg = result.total_kg - result.avoided_kg

    return result


def calculate_eui(annual: AnnualEnergySummary, area_sf: float) -> float:
    """
    Calculate Energy Use Intensity (EUI) in kBtu/SF/year.

    Args:
        annual: Annual energy summary
        area_sf: Conditioned floor area

    Returns:
        EUI in kBtu/SF/year
    """
    if area_sf <= 0:
        return 0.0

    # Convert to site kBtu
    elec_kbtu = annual.total_elec_kwh * 3.412  # kWh to kBtu
    gas_kbtu = annual.total_gas_therm * 100     # therms to kBtu

    total_kbtu = elec_kbtu + gas_kbtu
    return total_kbtu / area_sf


def calculate_renewable_pct(annual: AnnualEnergySummary) -> float:
    """
    Calculate renewable energy percentage.

    Args:
        annual: Annual energy summary

    Returns:
        Renewable percentage (0-100)
    """
    if annual.total_elec_kwh <= 0:
        return 0.0

    # Assume PV generation offsets electricity
    renewable_kwh = annual.pv_generation_kwh
    total_kwh = annual.total_elec_kwh

    return min(100.0, (renewable_kwh / total_kwh) * 100)


def generate_esg_metrics(
    sim: SimulationOutput,
    factors: Optional[EmissionFactors] = None
) -> EsgMetrics:
    """
    Generate ESG metrics from simulation output.

    Args:
        sim: Simulation output data
        factors: Emission factors

    Returns:
        EsgMetrics for the building
    """
    if factors is None:
        factors = CA_EMISSION_FACTORS

    annual = sim.annual
    area = sim.conditioned_area_sf or 1  # Avoid division by zero

    # Carbon footprint
    carbon = calculate_carbon_footprint(
        annual=annual,
        factors=factors,
        area_sf=area
    )

    # EUI
    eui = calculate_eui(annual, area)

    # Renewable %
    renewable_pct = calculate_renewable_pct(annual)

    return EsgMetrics(
        carbon=carbon,
        energy_use_intensity_kbtu_sf=eui,
        renewable_energy_pct=renewable_pct,
        title24_margin_pct=sim.compliance_margin
    )


def generate_esg_report(
    proposed: SimulationOutput,
    baseline: Optional[SimulationOutput] = None,
    factors: Optional[EmissionFactors] = None
) -> EsgReport:
    """
    Generate complete ESG report comparing proposed to baseline.

    Args:
        proposed: Proposed building simulation
        baseline: Baseline building simulation (optional)
        factors: Emission factors

    Returns:
        EsgReport with all metrics
    """
    if factors is None:
        factors = CA_EMISSION_FACTORS

    proposed_metrics = generate_esg_metrics(proposed, factors)

    report = EsgReport(
        project_name=proposed.project_name,
        building_type=proposed.building_type,
        conditioned_area_sf=proposed.conditioned_area_sf,
        proposed=proposed_metrics
    )

    if baseline:
        baseline_metrics = generate_esg_metrics(baseline, factors)
        report.baseline = baseline_metrics

        # Calculate reductions
        if baseline_metrics.carbon.total_kg > 0:
            reduction = baseline_metrics.carbon.total_kg - proposed_metrics.carbon.net_kg
            report.carbon_reduction_pct = (reduction / baseline_metrics.carbon.total_kg) * 100

        if baseline_metrics.energy_use_intensity_kbtu_sf > 0:
            reduction = baseline_metrics.energy_use_intensity_kbtu_sf - proposed_metrics.energy_use_intensity_kbtu_sf
            report.energy_reduction_pct = (reduction / baseline_metrics.energy_use_intensity_kbtu_sf) * 100

    return report


def format_esg_report(report: EsgReport) -> str:
    """
    Format ESG report as text.

    Args:
        report: EsgReport object

    Returns:
        Formatted text report
    """
    lines = [
        "=" * 60,
        "ESG SUSTAINABILITY REPORT",
        "=" * 60,
        "",
        "Project Information",
        "-" * 40,
        f"  Project Name.................... {report.project_name}",
        f"  Building Type................... {report.building_type}",
        f"  Conditioned Area................ {report.conditioned_area_sf:,.0f} SF",
        "",
        "Environmental Metrics - Proposed Building",
        "-" * 40,
    ]

    carbon = report.proposed.carbon
    lines.extend([
        f"  Scope 1 Emissions (Direct)...... {carbon.scope_1_kg:,.0f} kg CO2e",
        f"  Scope 2 Emissions (Indirect).... {carbon.scope_2_kg:,.0f} kg CO2e",
        f"  Total Carbon Footprint.......... {carbon.total_tonnes:,.1f} tonnes CO2e",
        f"  Carbon Intensity................ {carbon.kg_per_sf:.2f} kg CO2e/SF",
    ])

    if carbon.avoided_kg > 0:
        lines.append(f"  Avoided Emissions (PV).......... {carbon.avoided_kg:,.0f} kg CO2e")
        lines.append(f"  Net Carbon Footprint............ {carbon.net_kg:,.0f} kg CO2e")

    lines.extend([
        "",
        f"  Energy Use Intensity (EUI)...... {report.proposed.energy_use_intensity_kbtu_sf:.1f} kBtu/SF/year",
        f"  Renewable Energy Percentage..... {report.proposed.renewable_energy_pct:.1f}%",
    ])

    if report.proposed.title24_margin_pct != 0:
        lines.append(f"  Title 24 Compliance Margin...... {report.proposed.title24_margin_pct:.1f}%")

    # Baseline comparison
    if report.baseline:
        lines.extend([
            "",
            "Performance vs Baseline",
            "-" * 40,
            f"  Carbon Reduction................ {report.carbon_reduction_pct:.1f}%",
            f"  Energy Reduction................ {report.energy_reduction_pct:.1f}%",
        ])

        baseline_carbon = report.baseline.carbon
        lines.extend([
            "",
            "Baseline Building",
            "-" * 40,
            f"  Total Carbon Footprint.......... {baseline_carbon.total_tonnes:,.1f} tonnes CO2e",
            f"  Energy Use Intensity............ {report.baseline.energy_use_intensity_kbtu_sf:.1f} kBtu/SF/year",
        ])

    lines.extend([
        "",
        "=" * 60,
    ])

    return "\n".join(lines)


def export_esg_csv(report: EsgReport, file_path: str) -> str:
    """
    Export ESG report to CSV.

    Args:
        report: EsgReport object
        file_path: Output file path

    Returns:
        Path to created file
    """
    lines = [
        "ESG Sustainability Report",
        "",
        "Project Information",
        f",Project Name,{report.project_name}",
        f",Building Type,{report.building_type}",
        f",Conditioned Area (SF),{report.conditioned_area_sf:,.0f}",
        "",
        "Carbon Emissions",
        f",Scope 1 (Direct) kg CO2e,{report.proposed.carbon.scope_1_kg:,.0f}",
        f",Scope 2 (Indirect) kg CO2e,{report.proposed.carbon.scope_2_kg:,.0f}",
        f",Total tonnes CO2e,{report.proposed.carbon.total_tonnes:,.1f}",
        f",Carbon Intensity kg/SF,{report.proposed.carbon.kg_per_sf:.2f}",
    ]

    if report.proposed.carbon.avoided_kg > 0:
        lines.extend([
            f",Avoided (PV) kg CO2e,{report.proposed.carbon.avoided_kg:,.0f}",
            f",Net kg CO2e,{report.proposed.carbon.net_kg:,.0f}",
        ])

    lines.extend([
        "",
        "Energy Performance",
        f",EUI kBtu/SF/year,{report.proposed.energy_use_intensity_kbtu_sf:.1f}",
        f",Renewable Energy %,{report.proposed.renewable_energy_pct:.1f}",
    ])

    if report.baseline:
        lines.extend([
            "",
            "Reductions vs Baseline",
            f",Carbon Reduction %,{report.carbon_reduction_pct:.1f}",
            f",Energy Reduction %,{report.energy_reduction_pct:.1f}",
        ])

    with open(file_path, 'w') as f:
        f.write("\n".join(lines))

    return file_path


# ---- Regional emission factor presets ----

EMISSION_FACTOR_PRESETS = {
    "california": CA_EMISSION_FACTORS,
    "camx": CA_EMISSION_FACTORS,
    "us_average": US_AVERAGE_FACTORS,
    "national": US_AVERAGE_FACTORS,
    "northwest": EmissionFactors(
        elec_kg_per_kwh=0.287,
        gas_kg_per_therm=5.3,
        source="EPA eGRID NWPP 2024",
        region="Northwest (NWPP)"
    ),
    "texas": EmissionFactors(
        elec_kg_per_kwh=0.396,
        gas_kg_per_therm=5.3,
        source="EPA eGRID ERCT 2024",
        region="Texas (ERCOT)"
    ),
    "northeast": EmissionFactors(
        elec_kg_per_kwh=0.254,
        gas_kg_per_therm=5.3,
        source="EPA eGRID NPCC 2024",
        region="Northeast (NPCC)"
    ),
}


def get_emission_factors(region: str = "california") -> EmissionFactors:
    """
    Get emission factors for a region.

    Args:
        region: Region identifier (california, us_average, northwest, etc.)

    Returns:
        EmissionFactors for the region
    """
    return EMISSION_FACTOR_PRESETS.get(region.lower(), CA_EMISSION_FACTORS)
