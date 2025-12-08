"""
LCCA (Life Cycle Cost Analysis) module for ECO Tools.

This module provides:
- Simulation output parsers (HourlyResults, CSE CSV)
- Energy data schemas
- Financial calculators (NPV, IRR, payback)
- Cost database integration
- Report generators (ECON-1, Excel dashboard)
"""

from .model import (
    HourlyEnergy,
    AnnualEnergySummary,
    SimulationOutput,
    EnergyStreams,
    Tariff,
    LccaScenario,
    ScenarioAssumptions,
    Incentive,
    CashFlow,
)

from .econ1 import (
    Econ1Report,
    EnergyCostBreakdown,
    GenerationBreakdown,
    ReportOptions,
    ReportMode,
    generate_econ1,
    generate_econ1_gross,
    generate_econ1_net,
    calculate_energy_costs,
    export_econ1_text,
    export_econ1_csv,
)

from .calculators import (
    LccaResults,
    calculate_npv,
    calculate_irr,
    calculate_simple_payback,
    calculate_discounted_payback,
    calculate_sir,
    calculate_annual_energy_cost,
    generate_cash_flows,
    run_lcca,
    format_lcca_summary,
)

from .bridge import (
    simulation_to_energy_streams,
    simulation_to_scenario,
    create_baseline_scenario,
    create_proposed_scenario,
    run_simulation_lcca,
    quick_lcca_from_annual,
    estimate_pv_incentives,
)

from .tariffs import (
    TouPeriod,
    Season,
    TouSchedule,
    TouRates,
    DemandRates,
    TouTariff,
    HourlyUsage,
    TouCostBreakdown,
    calculate_tou_costs,
    calculate_demand_charges,
    hourly_energy_to_usage,
    create_sce_tou_gs3,
    create_pge_b20,
    create_sdge_al_tou,
    get_tariff_by_name,
    list_available_tariffs,
    format_tou_breakdown,
)

from .costdb import (
    SystemType,
    SystemCost,
    MaterialCost,
    RegionalFactor,
    EscalationRate,
    CostDatabase,
    create_default_costdb,
    load_costdb_from_json,
    save_costdb_to_json,
    estimate_hvac_cost,
    estimate_pv_cost,
    estimate_battery_cost,
)

from .excel_export import (
    ExcelExportOptions,
    export_lcca_to_excel,
    export_econ1_to_excel,
    export_comparison_to_excel,
)

from .esg_report import (
    EmissionsSource,
    EmissionFactors,
    CarbonFootprint,
    EsgMetrics,
    EsgReport,
    CA_EMISSION_FACTORS,
    US_AVERAGE_FACTORS,
    calculate_carbon_footprint,
    calculate_eui,
    calculate_renewable_pct,
    generate_esg_metrics,
    generate_esg_report,
    format_esg_report,
    export_esg_csv,
    get_emission_factors,
)

# PDF export is optional (requires reportlab)
try:
    from .pdf_export import (
        PdfExportOptions,
        export_econ1_to_pdf,
        export_lcca_to_pdf,
        REPORTLAB_AVAILABLE as PDF_EXPORT_AVAILABLE,
    )
except ImportError:
    PDF_EXPORT_AVAILABLE = False

__all__ = [
    # Data models
    "HourlyEnergy",
    "AnnualEnergySummary",
    "SimulationOutput",
    "EnergyStreams",
    "Tariff",
    "LccaScenario",
    "ScenarioAssumptions",
    "Incentive",
    "CashFlow",
    # ECON-1
    "Econ1Report",
    "EnergyCostBreakdown",
    "GenerationBreakdown",
    "ReportOptions",
    "ReportMode",
    "generate_econ1",
    "generate_econ1_gross",
    "generate_econ1_net",
    "calculate_energy_costs",
    "export_econ1_text",
    "export_econ1_csv",
    # Calculators
    "LccaResults",
    "calculate_npv",
    "calculate_irr",
    "calculate_simple_payback",
    "calculate_discounted_payback",
    "calculate_sir",
    "calculate_annual_energy_cost",
    "generate_cash_flows",
    "run_lcca",
    "format_lcca_summary",
    # Bridge functions
    "simulation_to_energy_streams",
    "simulation_to_scenario",
    "create_baseline_scenario",
    "create_proposed_scenario",
    "run_simulation_lcca",
    "quick_lcca_from_annual",
    "estimate_pv_incentives",
    # TOU Tariffs
    "TouPeriod",
    "Season",
    "TouSchedule",
    "TouRates",
    "DemandRates",
    "TouTariff",
    "HourlyUsage",
    "TouCostBreakdown",
    "calculate_tou_costs",
    "calculate_demand_charges",
    "hourly_energy_to_usage",
    "create_sce_tou_gs3",
    "create_pge_b20",
    "create_sdge_al_tou",
    "get_tariff_by_name",
    "list_available_tariffs",
    "format_tou_breakdown",
    # Cost Database
    "SystemType",
    "SystemCost",
    "MaterialCost",
    "RegionalFactor",
    "EscalationRate",
    "CostDatabase",
    "create_default_costdb",
    "load_costdb_from_json",
    "save_costdb_to_json",
    "estimate_hvac_cost",
    "estimate_pv_cost",
    "estimate_battery_cost",
    # Excel Export
    "ExcelExportOptions",
    "export_lcca_to_excel",
    "export_econ1_to_excel",
    "export_comparison_to_excel",
    # ESG Report
    "EmissionsSource",
    "EmissionFactors",
    "CarbonFootprint",
    "EsgMetrics",
    "EsgReport",
    "CA_EMISSION_FACTORS",
    "US_AVERAGE_FACTORS",
    "calculate_carbon_footprint",
    "calculate_eui",
    "calculate_renewable_pct",
    "generate_esg_metrics",
    "generate_esg_report",
    "format_esg_report",
    "export_esg_csv",
    "get_emission_factors",
    # PDF Export (optional)
    "PDF_EXPORT_AVAILABLE",
]
