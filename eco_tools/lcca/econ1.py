"""
ECON-1 Energy Cost Analysis Generator.

Generates California ECON-1 style energy cost reports from CBECC simulation outputs.
The ECON-1 form documents annual energy costs for proposed and baseline buildings.

Key feature: Toggle PV and battery impacts to report consumption, generation,
and load shifting independently or combined.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional, Dict, List, Any
from datetime import datetime
from enum import Enum

from .model import SimulationOutput, AnnualEnergySummary, Tariff


class ReportMode(Enum):
    """Report mode for PV/Battery inclusion."""
    GROSS = "gross"          # Consumption only (no PV/battery credits)
    NET = "net"              # Net consumption (with PV/battery)
    DETAILED = "detailed"    # Show both gross and net with breakdown


@dataclass
class ReportOptions:
    """Options for controlling ECON-1 report output."""
    # PV/Battery toggles
    include_pv: bool = True
    include_battery: bool = True
    report_mode: ReportMode = ReportMode.DETAILED

    # Section toggles
    show_enduse_breakdown: bool = True
    show_mixed_use_breakdown: bool = True
    show_monthly_peaks: bool = False
    show_tdv_analysis: bool = False
    show_carbon_analysis: bool = False

    # Formatting
    currency_symbol: str = "$"
    thousands_separator: str = ","


@dataclass
class GenerationBreakdown:
    """Breakdown of on-site generation and storage."""
    # PV System
    pv_generation_kwh: float = 0.0
    pv_capacity_kw: float = 0.0
    pv_value: float = 0.0           # Value at electric rate

    # Battery System
    battery_discharge_kwh: float = 0.0
    battery_charge_kwh: float = 0.0
    battery_net_kwh: float = 0.0    # Discharge - Charge (positive = net export)
    battery_capacity_kwh: float = 0.0
    battery_value: float = 0.0      # Value of load shifting

    # Combined
    total_offset_kwh: float = 0.0   # PV + Battery net
    total_credit: float = 0.0       # Total financial credit

    @property
    def pv_capacity_factor(self) -> float:
        """PV capacity factor (generation / theoretical max)."""
        if self.pv_capacity_kw > 0:
            theoretical_max = self.pv_capacity_kw * 8760
            return self.pv_generation_kwh / theoretical_max
        return 0.0


@dataclass
class EnergyCostBreakdown:
    """Breakdown of annual energy costs by fuel type."""
    # Electricity - Gross (consumption before PV/battery)
    elec_kwh_gross: float = 0.0
    elec_rate: float = 0.0
    elec_cost_gross: float = 0.0

    # Electricity - Net (after PV/battery)
    elec_kwh_net: float = 0.0
    elec_cost_net: float = 0.0

    # Natural Gas
    gas_therm: float = 0.0
    gas_rate: float = 0.0
    gas_cost: float = 0.0

    # Demand charges - Gross
    peak_demand_kw_gross: float = 0.0
    demand_rate: float = 0.0
    demand_cost_gross: float = 0.0

    # Demand charges - Net (with battery peak shaving)
    peak_demand_kw_net: float = 0.0
    demand_cost_net: float = 0.0

    # Customer charges
    customer_charge_monthly: float = 0.0
    customer_charge_annual: float = 0.0

    # Generation/Storage breakdown
    generation: GenerationBreakdown = field(default_factory=GenerationBreakdown)

    # Cost totals
    gross_cost: float = 0.0         # Before PV/battery credits
    net_cost: float = 0.0           # After PV/battery credits
    pv_savings: float = 0.0         # Savings from PV
    battery_savings: float = 0.0    # Savings from battery

    # Legacy properties for compatibility
    @property
    def elec_kwh(self) -> float:
        """Gross electricity consumption."""
        return self.elec_kwh_gross

    @property
    def elec_cost(self) -> float:
        """Gross electricity cost."""
        return self.elec_cost_gross

    @property
    def peak_demand_kw(self) -> float:
        """Gross peak demand."""
        return self.peak_demand_kw_gross

    @property
    def demand_cost(self) -> float:
        """Gross demand cost."""
        return self.demand_cost_gross

    @property
    def pv_generation_kwh(self) -> float:
        """PV generation for compatibility."""
        return self.generation.pv_generation_kwh

    @property
    def pv_credit(self) -> float:
        """PV credit for compatibility."""
        return self.generation.pv_value

    @property
    def total_site_energy_kbtu(self) -> float:
        """Total site energy in kBtu (gross consumption)."""
        elec_kbtu = self.elec_kwh_gross * 3.412
        gas_kbtu = self.gas_therm * 100
        return elec_kbtu + gas_kbtu

    @property
    def net_site_energy_kbtu(self) -> float:
        """Net site energy in kBtu (after PV/battery)."""
        elec_kbtu = self.elec_kwh_net * 3.412
        gas_kbtu = self.gas_therm * 100
        return elec_kbtu + gas_kbtu


@dataclass
class Econ1Report:
    """Complete ECON-1 style energy cost report."""

    # Project info
    project_name: str = ""
    building_type: str = ""
    climate_zone: str = ""
    conditioned_area_sf: float = 0.0
    run_date: str = ""
    software_version: str = ""

    # Tariff info
    tariff_name: str = ""
    utility_name: str = ""

    # Report options
    options: ReportOptions = field(default_factory=ReportOptions)

    # Proposed building costs
    proposed: EnergyCostBreakdown = field(default_factory=EnergyCostBreakdown)

    # Baseline/Standard building costs (optional)
    baseline: Optional[EnergyCostBreakdown] = None

    # Comparison metrics (if baseline provided)
    annual_savings: float = 0.0
    annual_savings_gross: float = 0.0   # Before PV/battery
    percent_savings: float = 0.0
    percent_savings_gross: float = 0.0
    simple_payback_years: float = 0.0
    incremental_cost: float = 0.0

    # End-use breakdown for proposed
    enduse_elec: Dict[str, float] = field(default_factory=dict)
    enduse_gas: Dict[str, float] = field(default_factory=dict)

    # Mixed-use breakdown (optional)
    nonres_costs: Optional[EnergyCostBreakdown] = None
    res_costs: Optional[EnergyCostBreakdown] = None

    def to_dict(self, mode: Optional[ReportMode] = None) -> Dict[str, Any]:
        """Convert report to dictionary for export.

        Args:
            mode: Override report mode (GROSS, NET, or DETAILED)
        """
        mode = mode or self.options.report_mode
        opts = self.options
        data = {}

        # Project Information
        data["Project Information"] = {
            "Project Name": self.project_name,
            "Building Type": self.building_type,
            "Climate Zone": self.climate_zone or "N/A",
            "Conditioned Area (SF)": f"{self.conditioned_area_sf:,.0f}",
            "Analysis Date": self.run_date,
            "Software": self.software_version,
        }

        # Utility Rates
        data["Utility Rates"] = {
            "Tariff": self.tariff_name,
            "Utility": self.utility_name,
            "Electric Rate ($/kWh)": f"${self.proposed.elec_rate:.4f}",
            "Gas Rate ($/therm)": f"${self.proposed.gas_rate:.2f}",
            "Demand Rate ($/kW-mo)": f"${self.proposed.demand_rate:.2f}",
        }

        # Energy section based on mode
        if mode == ReportMode.GROSS:
            data["Proposed Building - Annual Energy (Gross)"] = {
                "Electricity Consumption (kWh)": f"{self.proposed.elec_kwh_gross:,.0f}",
                "Natural Gas (therms)": f"{self.proposed.gas_therm:,.1f}",
                "Peak Demand (kW)": f"{self.proposed.peak_demand_kw_gross:,.1f}",
                "Site Energy (kBtu)": f"{self.proposed.total_site_energy_kbtu:,.0f}",
            }
            data["Proposed Building - Annual Costs (Gross)"] = {
                "Electricity Cost": f"${self.proposed.elec_cost_gross:,.2f}",
                "Natural Gas Cost": f"${self.proposed.gas_cost:,.2f}",
                "Demand Charges": f"${self.proposed.demand_cost_gross:,.2f}",
                "Customer Charges": f"${self.proposed.customer_charge_annual:,.2f}",
                "Total Annual Cost": f"${self.proposed.gross_cost:,.2f}",
            }

        elif mode == ReportMode.NET:
            data["Proposed Building - Annual Energy (Net)"] = {
                "Net Electricity (kWh)": f"{self.proposed.elec_kwh_net:,.0f}",
                "Natural Gas (therms)": f"{self.proposed.gas_therm:,.1f}",
                "Peak Demand (kW)": f"{self.proposed.peak_demand_kw_net:,.1f}",
                "Net Site Energy (kBtu)": f"{self.proposed.net_site_energy_kbtu:,.0f}",
            }
            data["Proposed Building - Annual Costs (Net)"] = {
                "Net Electricity Cost": f"${self.proposed.elec_cost_net:,.2f}",
                "Natural Gas Cost": f"${self.proposed.gas_cost:,.2f}",
                "Net Demand Charges": f"${self.proposed.demand_cost_net:,.2f}",
                "Customer Charges": f"${self.proposed.customer_charge_annual:,.2f}",
                "Net Annual Cost": f"${self.proposed.net_cost:,.2f}",
            }

        else:  # DETAILED
            # Gross consumption
            data["Proposed Building - Gross Consumption"] = {
                "Electricity Consumption (kWh)": f"{self.proposed.elec_kwh_gross:,.0f}",
                "Natural Gas (therms)": f"{self.proposed.gas_therm:,.1f}",
                "Peak Demand (kW)": f"{self.proposed.peak_demand_kw_gross:,.1f}",
                "Site Energy (kBtu)": f"{self.proposed.total_site_energy_kbtu:,.0f}",
            }

            # Generation breakdown
            gen = self.proposed.generation
            if opts.include_pv and gen.pv_generation_kwh > 0:
                data["On-Site Generation - PV System"] = {
                    "PV Generation (kWh)": f"{gen.pv_generation_kwh:,.0f}",
                    "PV Value at Elec Rate": f"${gen.pv_value:,.2f}",
                }

            if opts.include_battery and (gen.battery_discharge_kwh > 0 or gen.battery_charge_kwh > 0):
                data["Load Shifting - Battery System"] = {
                    "Battery Discharge (kWh)": f"{gen.battery_discharge_kwh:,.0f}",
                    "Battery Charge (kWh)": f"{gen.battery_charge_kwh:,.0f}",
                    "Net Battery (kWh)": f"{gen.battery_net_kwh:,.0f}",
                    "Load Shifting Value": f"${gen.battery_value:,.2f}",
                }

            # Net consumption
            data["Proposed Building - Net Consumption"] = {
                "Net Electricity (kWh)": f"{self.proposed.elec_kwh_net:,.0f}",
                "Natural Gas (therms)": f"{self.proposed.gas_therm:,.1f}",
                "Net Peak Demand (kW)": f"{self.proposed.peak_demand_kw_net:,.1f}",
                "Net Site Energy (kBtu)": f"{self.proposed.net_site_energy_kbtu:,.0f}",
            }

            # Cost breakdown
            data["Proposed Building - Cost Analysis"] = {
                "Gross Electricity Cost": f"${self.proposed.elec_cost_gross:,.2f}",
                "Natural Gas Cost": f"${self.proposed.gas_cost:,.2f}",
                "Gross Demand Charges": f"${self.proposed.demand_cost_gross:,.2f}",
                "Customer Charges": f"${self.proposed.customer_charge_annual:,.2f}",
                "GROSS TOTAL": f"${self.proposed.gross_cost:,.2f}",
            }
            if opts.include_pv:
                data["Proposed Building - Cost Analysis"]["PV Credit"] = f"(${self.proposed.pv_savings:,.2f})"
            if opts.include_battery:
                data["Proposed Building - Cost Analysis"]["Battery Savings"] = f"(${self.proposed.battery_savings:,.2f})"
            data["Proposed Building - Cost Analysis"]["NET TOTAL"] = f"${self.proposed.net_cost:,.2f}"

        # Baseline comparison
        if self.baseline:
            if mode == ReportMode.GROSS:
                data["Baseline Building - Annual Energy (Gross)"] = {
                    "Electricity (kWh)": f"{self.baseline.elec_kwh_gross:,.0f}",
                    "Natural Gas (therms)": f"{self.baseline.gas_therm:,.1f}",
                    "Peak Demand (kW)": f"{self.baseline.peak_demand_kw_gross:,.1f}",
                }
                data["Cost Comparison (Gross)"] = {
                    "Proposed Gross Cost": f"${self.proposed.gross_cost:,.2f}",
                    "Baseline Gross Cost": f"${self.baseline.gross_cost:,.2f}",
                    "Annual Savings (Gross)": f"${self.annual_savings_gross:,.2f}",
                    "Percent Savings (Gross)": f"{self.percent_savings_gross:.1f}%",
                }
            elif mode == ReportMode.NET:
                data["Baseline Building - Annual Energy"] = {
                    "Electricity (kWh)": f"{self.baseline.elec_kwh_gross:,.0f}",
                    "Natural Gas (therms)": f"{self.baseline.gas_therm:,.1f}",
                }
                data["Cost Comparison (Net)"] = {
                    "Proposed Net Cost": f"${self.proposed.net_cost:,.2f}",
                    "Baseline Net Cost": f"${self.baseline.net_cost:,.2f}",
                    "Annual Savings": f"${self.annual_savings:,.2f}",
                    "Percent Savings": f"{self.percent_savings:.1f}%",
                }
            else:  # DETAILED
                data["Baseline Building"] = {
                    "Electricity (kWh)": f"{self.baseline.elec_kwh_gross:,.0f}",
                    "Natural Gas (therms)": f"{self.baseline.gas_therm:,.1f}",
                    "Peak Demand (kW)": f"{self.baseline.peak_demand_kw_gross:,.1f}",
                    "Gross Annual Cost": f"${self.baseline.gross_cost:,.2f}",
                    "Net Annual Cost": f"${self.baseline.net_cost:,.2f}",
                }
                data["Cost Comparison"] = {
                    "Annual Savings (Gross)": f"${self.annual_savings_gross:,.2f}",
                    "Percent Savings (Gross)": f"{self.percent_savings_gross:.1f}%",
                    "Annual Savings (Net)": f"${self.annual_savings:,.2f}",
                    "Percent Savings (Net)": f"{self.percent_savings:.1f}%",
                }

        # End-use breakdown
        if opts.show_enduse_breakdown:
            if self.enduse_elec:
                data["Electric End-Use Breakdown (kWh)"] = {
                    k: f"{v:,.0f}" for k, v in self.enduse_elec.items()
                }
            if self.enduse_gas:
                data["Gas End-Use Breakdown (therms)"] = {
                    k: f"{v:,.1f}" for k, v in self.enduse_gas.items()
                }

        # Mixed-use breakdown
        if opts.show_mixed_use_breakdown and self.nonres_costs and self.res_costs:
            data["Mixed-Use Breakdown - NonResidential"] = {
                "Electricity (kWh)": f"{self.nonres_costs.elec_kwh_gross:,.0f}",
                "Gas (therms)": f"{self.nonres_costs.gas_therm:,.1f}",
                "Gross Cost": f"${self.nonres_costs.gross_cost:,.2f}",
            }
            data["Mixed-Use Breakdown - Residential"] = {
                "Electricity (kWh)": f"{self.res_costs.elec_kwh_gross:,.0f}",
                "Gas (therms)": f"{self.res_costs.gas_therm:,.1f}",
                "Gross Cost": f"${self.res_costs.gross_cost:,.2f}",
            }

        return data

    def to_text(self, mode: Optional[ReportMode] = None) -> str:
        """Generate text report."""
        mode = mode or self.options.report_mode
        lines = []
        lines.append("=" * 70)
        title = "ECON-1 ENERGY COST ANALYSIS"
        if mode == ReportMode.GROSS:
            title += " (GROSS - No PV/Battery)"
        elif mode == ReportMode.NET:
            title += " (NET - With PV/Battery)"
        lines.append(title)
        lines.append("=" * 70)
        lines.append("")

        data = self.to_dict(mode)
        for section, items in data.items():
            lines.append(f"\n{section}")
            lines.append("-" * 50)
            for key, value in items.items():
                lines.append(f"  {key:.<40} {value}")

        lines.append("")
        lines.append("=" * 70)
        return "\n".join(lines)


def calculate_energy_costs(
    annual: AnnualEnergySummary,
    tariff: Tariff,
    include_pv: bool = True,
    include_battery: bool = True,
) -> EnergyCostBreakdown:
    """Calculate annual energy costs from energy summary and tariff.

    Args:
        annual: Annual energy summary from simulation
        tariff: Utility rate structure
        include_pv: Include PV generation credits
        include_battery: Include battery load shifting benefits
    """
    breakdown = EnergyCostBreakdown()

    # Gross electricity (consumption before any offsets)
    breakdown.elec_kwh_gross = annual.total_elec_kwh
    breakdown.elec_rate = tariff.elec_rate_per_kwh
    breakdown.elec_cost_gross = breakdown.elec_kwh_gross * breakdown.elec_rate

    # Natural Gas (not affected by PV/battery)
    breakdown.gas_therm = annual.total_gas_therm
    breakdown.gas_rate = tariff.gas_rate_per_therm
    breakdown.gas_cost = breakdown.gas_therm * breakdown.gas_rate

    # Gross demand charges
    breakdown.peak_demand_kw_gross = annual.peak_demand_kw
    breakdown.demand_rate = tariff.demand_rate_per_kw
    breakdown.demand_cost_gross = breakdown.peak_demand_kw_gross * breakdown.demand_rate * 12

    # Customer charges
    breakdown.customer_charge_monthly = tariff.monthly_customer_charge
    breakdown.customer_charge_annual = breakdown.customer_charge_monthly * 12

    # Gross cost (before PV/battery)
    breakdown.gross_cost = (
        breakdown.elec_cost_gross +
        breakdown.gas_cost +
        breakdown.demand_cost_gross +
        breakdown.customer_charge_annual
    )

    # Generation breakdown
    gen = breakdown.generation
    gen.pv_generation_kwh = annual.pv_generation_kwh
    gen.pv_value = gen.pv_generation_kwh * breakdown.elec_rate

    # Calculate net values
    pv_offset = gen.pv_generation_kwh if include_pv else 0.0
    battery_offset = 0.0  # TODO: Calculate from hourly data if available

    gen.total_offset_kwh = pv_offset + battery_offset
    gen.total_credit = gen.total_offset_kwh * breakdown.elec_rate

    # Net electricity
    breakdown.elec_kwh_net = max(0, breakdown.elec_kwh_gross - pv_offset - battery_offset)
    breakdown.elec_cost_net = breakdown.elec_kwh_net * breakdown.elec_rate

    # Net demand (assume no battery peak shaving for now)
    breakdown.peak_demand_kw_net = breakdown.peak_demand_kw_gross
    breakdown.demand_cost_net = breakdown.demand_cost_gross

    # Savings attribution
    breakdown.pv_savings = gen.pv_value if include_pv else 0.0
    breakdown.battery_savings = gen.battery_value if include_battery else 0.0

    # Net cost
    breakdown.net_cost = (
        breakdown.elec_cost_net +
        breakdown.gas_cost +
        breakdown.demand_cost_net +
        breakdown.customer_charge_annual
    )

    return breakdown


def generate_econ1(
    proposed: SimulationOutput,
    tariff: Tariff,
    baseline: Optional[SimulationOutput] = None,
    incremental_cost: float = 0.0,
    options: Optional[ReportOptions] = None,
) -> Econ1Report:
    """
    Generate an ECON-1 style energy cost report.

    Args:
        proposed: Simulation output for the proposed building design
        tariff: Utility rate structure for cost calculations
        baseline: Optional simulation output for baseline/standard building
        incremental_cost: Optional incremental construction cost for payback
        options: Report options for controlling output

    Returns:
        Econ1Report with complete cost analysis
    """
    options = options or ReportOptions()
    report = Econ1Report(options=options)

    # Project info from proposed
    report.project_name = proposed.project_name
    report.building_type = proposed.building_type
    report.climate_zone = proposed.climate_zone
    report.conditioned_area_sf = proposed.conditioned_area_sf
    report.run_date = proposed.run_date or datetime.now().strftime("%Y-%m-%d")
    report.software_version = proposed.software_version

    # Tariff info
    report.tariff_name = tariff.name or "Custom"
    report.utility_name = tariff.utility or "N/A"

    # Calculate proposed costs
    report.proposed = calculate_energy_costs(
        proposed.annual, tariff,
        include_pv=options.include_pv,
        include_battery=options.include_battery,
    )

    # End-use breakdown
    ann = proposed.annual
    report.enduse_elec = {
        "Cooling": ann.cooling_kwh,
        "Heating": ann.heating_kwh,
        "Fans": ann.fans_kwh,
        "Pumps": ann.pumps_kwh,
        "Lighting": ann.lighting_kwh,
        "Receptacle": ann.receptacle_kwh,
        "DHW": ann.dhw_elec_kwh,
        "Process": ann.process_kwh,
        "Exterior": ann.exterior_kwh,
    }
    report.enduse_elec = {k: v for k, v in report.enduse_elec.items() if v > 0}

    report.enduse_gas = {
        "Heating": ann.heating_therm,
        "DHW": ann.dhw_therm,
        "Process": ann.process_therm,
    }
    report.enduse_gas = {k: v for k, v in report.enduse_gas.items() if v > 0}

    # Mixed-use breakdown
    if proposed.is_mixed_use and proposed.annual_nonres and proposed.annual_res:
        report.nonres_costs = calculate_energy_costs(
            proposed.annual_nonres, tariff,
            include_pv=False,  # PV is building-wide
            include_battery=False,
        )
        report.res_costs = calculate_energy_costs(
            proposed.annual_res, tariff,
            include_pv=False,
            include_battery=False,
        )

    # Baseline comparison
    if baseline:
        report.baseline = calculate_energy_costs(
            baseline.annual, tariff,
            include_pv=options.include_pv,
            include_battery=options.include_battery,
        )

        # Net savings (with PV/battery)
        report.annual_savings = report.baseline.net_cost - report.proposed.net_cost
        if report.baseline.net_cost > 0:
            report.percent_savings = (report.annual_savings / report.baseline.net_cost) * 100

        # Gross savings (without PV/battery)
        report.annual_savings_gross = report.baseline.gross_cost - report.proposed.gross_cost
        if report.baseline.gross_cost > 0:
            report.percent_savings_gross = (report.annual_savings_gross / report.baseline.gross_cost) * 100

        report.incremental_cost = incremental_cost
        if report.annual_savings > 0 and incremental_cost > 0:
            report.simple_payback_years = incremental_cost / report.annual_savings

    return report


def export_econ1_text(
    report: Econ1Report,
    filepath: str,
    mode: Optional[ReportMode] = None,
) -> None:
    """Export ECON-1 report to text file."""
    with open(filepath, 'w') as f:
        f.write(report.to_text(mode))


def export_econ1_csv(
    report: Econ1Report,
    filepath: str,
    mode: Optional[ReportMode] = None,
) -> None:
    """Export ECON-1 report to CSV file."""
    import csv

    data = report.to_dict(mode)
    with open(filepath, 'w', newline='') as f:
        writer = csv.writer(f)
        for section, items in data.items():
            writer.writerow([section])
            for key, value in items.items():
                writer.writerow(["", key, value])
            writer.writerow([])


# Convenience functions for different report modes
def generate_econ1_gross(
    proposed: SimulationOutput,
    tariff: Tariff,
    baseline: Optional[SimulationOutput] = None,
) -> Econ1Report:
    """Generate ECON-1 report showing only gross consumption (no PV/battery)."""
    options = ReportOptions(
        include_pv=False,
        include_battery=False,
        report_mode=ReportMode.GROSS,
    )
    return generate_econ1(proposed, tariff, baseline, options=options)


def generate_econ1_net(
    proposed: SimulationOutput,
    tariff: Tariff,
    baseline: Optional[SimulationOutput] = None,
) -> Econ1Report:
    """Generate ECON-1 report showing net consumption (with PV/battery)."""
    options = ReportOptions(
        include_pv=True,
        include_battery=True,
        report_mode=ReportMode.NET,
    )
    return generate_econ1(proposed, tariff, baseline, options=options)
