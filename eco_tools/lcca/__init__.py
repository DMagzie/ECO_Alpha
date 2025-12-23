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
    TouLccaScenario,
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
    # TOU-native LCCA
    TouLccaResults,
    generate_tou_cash_flows,
    run_tou_lcca,
    format_tou_lcca_summary,
)

from .bridge import (
    simulation_to_energy_streams,
    simulation_to_scenario,
    create_baseline_scenario,
    create_proposed_scenario,
    run_simulation_lcca,
    quick_lcca_from_annual,
    estimate_pv_incentives,
    # Mixed-use building support (Phase 4)
    create_mixed_use_scenarios,
    create_section_lcca_scenario,
    run_mixed_use_lcca,
    allocate_capex_by_section,
)

from .meter_aggregation import (
    # Building section types
    BuildingSectionType,
    # Aggregation classes
    MeterCategoryAggregate,
    BuildingSection,
    MeterAggregator,
    MixedUseLccaResults,
    # Convenience functions
    aggregate_zones_by_meter_category,
    create_mixed_use_lcca,
    format_meter_aggregation_table,
    format_building_sections_table,
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

from .vnbt import (
    NettingMode,
    ExportRates,
    NonBypassableCharges,
    VnbtTariff,
    HourlyNetUsage,
    VnbtCostBreakdown,
    VirtualMeterAllocation,
    calculate_vnbt_costs,
    calculate_vnbt_multifamily,
    create_pge_e_elec_vnbt,
    create_sce_tou_d_prime_vnbt,
    create_sdge_tou_dr_vnbt,
)

from .excel_export import (
    ExcelExportOptions,
    export_lcca_to_excel,
    export_econ1_to_excel,
    export_comparison_to_excel,
)

from .scenario_manager import (
    ScenarioManager,
    ScenarioComparison,
    TariffComparison,
    ComparisonMatrix,
    format_tariff_comparison,
)

from .ecm_bundle import (
    # Enums
    ECMCategory,
    ECMSubcategory,
    BuildingType,
    CodeBaseline,
    InteractionType,
    ClimateZoneType,
    # Data classes
    ECM,
    ECMAnalysisResult,
    ECMBundle,
    ECMTemplate,
    MeasureInteraction,
    ClimateAdaptiveFactors,
    # Library
    ECMLibrary,
    get_ecm_library,
    # Interaction Matrix
    MeasureInteractionMatrix,
    get_interaction_matrix,
    # Climate Adaptive Defaults
    ClimateAdaptiveDefaults,
    get_climate_defaults,
    CLIMATE_ZONE_CLASSIFICATION,
    # Parametric ECM Support
    ParametricRange,
    ParametricECMDefinition,
    ParametricOptimizationResult,
    ParametricECMOptimizer,
    create_parametric_pv,
    create_parametric_battery,
    create_parametric_hvac,
    format_optimization_result,
    # Analysis functions
    analyze_ecm_marginal_value,
    format_ecm_analysis,
    # ECM template factories
    create_pv_ecm,
    create_electrification_ecm,
    create_efficiency_ecm,
    # Residential HVAC ECMs
    create_erv_ecm,
    create_central_vent_ecm,
    create_minisplit_ecm,
    create_hpwh_ecm,
    create_ecm_from_cuac_comparison,
)

from .sensitivity import (
    SensitivityParameter,
    ParameterRange,
    SweepResult,
    ParameterSweep,
    TornadoItem,
    TornadoAnalysis,
    MonteCarloResult,
    ParameterDistribution,
    SensitivityAnalyzer,
    format_sensitivity_summary,
    # Zone-level sensitivity (Phase 5)
    ZoneSensitivityResult,
    ZoneImpactResult,
    zone_sensitivity_analysis,
    identify_high_impact_zones,
    format_zone_impact_table,
    zone_tornado_analysis,
)

from .benchmarks import (
    # Enums
    PerformanceRating,
    BuildingVintage,
    # Data classes
    ZoneBenchmark,
    BenchmarkComparison,
    # Library
    BenchmarkLibrary,
    get_benchmark_library,
    # Comparison functions
    compare_zone_to_benchmark,
    compare_zones_to_benchmarks,
    identify_high_impact_zones as identify_benchmark_outliers,
    calculate_portfolio_rating,
    # Formatting
    format_benchmark_comparison,
    format_benchmark_summary_table,
    format_rating_distribution,
)

from .project_context import (
    SimulationEngine,
    BuildingUseType,
    CompliancePathway,
    GeoLocation,
    ClimateData,
    BuildingGeometry,
    LcaMetadata,
    ComplianceInfo,
    ProjectMetadata,
    SourceFiles,
    AnalysisState,
    ProjectContext,
    ProjectContextBuilder,
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

# Phase 6: Production Integration & Workflow
from .auto_discovery import (
    SimulationFileType,
    SimulationFile,
    DiscoveredOutputs,
    discover_simulation_outputs,
    discover_multiple_projects,
    format_discovery_summary,
    discover_and_validate,
)

from .lcca_runner import (
    OutputFormat,
    AnalysisMode,
    RunnerConfig,
    RunnerResults,
    LccaRunner,
    run_lcca_workflow,
    batch_lcca,
)

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
    "TouLccaScenario",
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
    # TOU-native LCCA
    "TouLccaResults",
    "generate_tou_cash_flows",
    "run_tou_lcca",
    "format_tou_lcca_summary",
    # Bridge functions
    "simulation_to_energy_streams",
    "simulation_to_scenario",
    "create_baseline_scenario",
    "create_proposed_scenario",
    "run_simulation_lcca",
    "quick_lcca_from_annual",
    "estimate_pv_incentives",
    # Mixed-use building support (Phase 4)
    "create_mixed_use_scenarios",
    "create_section_lcca_scenario",
    "run_mixed_use_lcca",
    "allocate_capex_by_section",
    # Meter Aggregation (Phase 4)
    "BuildingSectionType",
    "MeterCategoryAggregate",
    "BuildingSection",
    "MeterAggregator",
    "MixedUseLccaResults",
    "aggregate_zones_by_meter_category",
    "create_mixed_use_lcca",
    "format_meter_aggregation_table",
    "format_building_sections_table",
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
    # V-NBT (Virtual Net Billing Tariff)
    "NettingMode",
    "ExportRates",
    "NonBypassableCharges",
    "VnbtTariff",
    "HourlyNetUsage",
    "VnbtCostBreakdown",
    "VirtualMeterAllocation",
    "calculate_vnbt_costs",
    "calculate_vnbt_multifamily",
    "create_pge_e_elec_vnbt",
    "create_sce_tou_d_prime_vnbt",
    "create_sdge_tou_dr_vnbt",
    # Excel Export
    "ExcelExportOptions",
    "export_lcca_to_excel",
    "export_econ1_to_excel",
    "export_comparison_to_excel",
    # Scenario Manager
    "ScenarioManager",
    "ScenarioComparison",
    "TariffComparison",
    "ComparisonMatrix",
    "format_tariff_comparison",
    # ECM Bundle - Enums
    "ECMCategory",
    "ECMSubcategory",
    "BuildingType",
    "CodeBaseline",
    "InteractionType",
    "ClimateZoneType",
    # ECM Bundle - Data classes
    "ECM",
    "ECMAnalysisResult",
    "ECMBundle",
    "ECMTemplate",
    "MeasureInteraction",
    "ClimateAdaptiveFactors",
    # ECM Bundle - Library
    "ECMLibrary",
    "get_ecm_library",
    # ECM Bundle - Interaction Matrix
    "MeasureInteractionMatrix",
    "get_interaction_matrix",
    # ECM Bundle - Climate Adaptive Defaults
    "ClimateAdaptiveDefaults",
    "get_climate_defaults",
    "CLIMATE_ZONE_CLASSIFICATION",
    # ECM Bundle - Parametric ECM Support
    "ParametricRange",
    "ParametricECMDefinition",
    "ParametricOptimizationResult",
    "ParametricECMOptimizer",
    "create_parametric_pv",
    "create_parametric_battery",
    "create_parametric_hvac",
    "format_optimization_result",
    # ECM Bundle - Analysis
    "analyze_ecm_marginal_value",
    "format_ecm_analysis",
    # ECM Bundle - Template factories
    "create_pv_ecm",
    "create_electrification_ecm",
    "create_efficiency_ecm",
    "create_erv_ecm",
    "create_central_vent_ecm",
    "create_minisplit_ecm",
    "create_hpwh_ecm",
    "create_ecm_from_cuac_comparison",
    # Sensitivity Analysis
    "SensitivityParameter",
    "ParameterRange",
    "SweepResult",
    "ParameterSweep",
    "TornadoItem",
    "TornadoAnalysis",
    "MonteCarloResult",
    "ParameterDistribution",
    "SensitivityAnalyzer",
    "format_sensitivity_summary",
    # Zone-level sensitivity (Phase 5)
    "ZoneSensitivityResult",
    "ZoneImpactResult",
    "zone_sensitivity_analysis",
    "identify_high_impact_zones",
    "format_zone_impact_table",
    "zone_tornado_analysis",
    # Benchmarking (Phase 5)
    "PerformanceRating",
    "BuildingVintage",
    "ZoneBenchmark",
    "BenchmarkComparison",
    "BenchmarkLibrary",
    "get_benchmark_library",
    "compare_zone_to_benchmark",
    "compare_zones_to_benchmarks",
    "identify_benchmark_outliers",
    "calculate_portfolio_rating",
    "format_benchmark_comparison",
    "format_benchmark_summary_table",
    "format_rating_distribution",
    # Project Context
    "SimulationEngine",
    "BuildingUseType",
    "CompliancePathway",
    "GeoLocation",
    "ClimateData",
    "BuildingGeometry",
    "LcaMetadata",
    "ComplianceInfo",
    "ProjectMetadata",
    "SourceFiles",
    "AnalysisState",
    "ProjectContext",
    "ProjectContextBuilder",
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
    # Auto-discovery (Phase 6)
    "SimulationFileType",
    "SimulationFile",
    "DiscoveredOutputs",
    "discover_simulation_outputs",
    "discover_multiple_projects",
    "format_discovery_summary",
    "discover_and_validate",
    # LCCA Runner (Phase 6)
    "OutputFormat",
    "AnalysisMode",
    "RunnerConfig",
    "RunnerResults",
    "LccaRunner",
    "run_lcca_workflow",
    "batch_lcca",
]
