"""
Project Context Container for ECO Tools.

Provides a unified data layer for energy modeling projects that:
- Holds all project metadata, simulation outputs, and analysis results
- Supports multiple simulation engines (CBECC, EnergyPlus, CSE)
- Enables LCA integration (OneClickLCA compatibility)
- Provides Builder pattern API for flexible construction
- Supports persistence (save/load) for interactive analysis

Example:
    >>> from eco_tools.lcca import ProjectContextBuilder, create_sce_tou_gs3
    >>>
    >>> # Build project from CBECC results
    >>> project = (ProjectContextBuilder()
    ...     .with_name("Gibraltar Office")
    ...     .with_location(city="Irvine", state="CA", climate_zone="CZ8")
    ...     .from_cbecc_results(baseline_csv, proposed_csv)
    ...     .with_tariff(create_sce_tou_gs3())
    ...     .with_pv_system(capacity_kw=343, cost_per_watt=2.50)
    ...     .build())
    >>>
    >>> # Run analyses
    >>> project.run_lcca()
    >>> project.run_sensitivity()
    >>>
    >>> # Save for later
    >>> project.save("gibraltar.eco")
    >>>
    >>> # Load and continue
    >>> project = ProjectContext.load("gibraltar.eco")
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Union
from pathlib import Path
from enum import Enum
from datetime import datetime
import json
import zipfile
import tempfile
import shutil


class SimulationEngine(Enum):
    """Supported simulation engines."""
    CBECC = "cbecc"
    ENERGYPLUS = "energyplus"
    CSE = "cse"
    OPENSTUDIO = "openstudio"
    OTHER = "other"


class BuildingUseType(Enum):
    """Standard building use types (compatible across tools)."""
    OFFICE = "office"
    RETAIL = "retail"
    WAREHOUSE = "warehouse"
    SCHOOL = "school"
    HOTEL = "hotel"
    HOSPITAL = "hospital"
    RESTAURANT = "restaurant"
    RESIDENTIAL_SINGLE = "residential_single"
    RESIDENTIAL_MULTI = "residential_multi"
    MIXED_USE = "mixed_use"
    INDUSTRIAL = "industrial"
    OTHER = "other"


class CompliancePathway(Enum):
    """Code compliance pathways."""
    TITLE24_PRESCRIPTIVE = "title24_prescriptive"
    TITLE24_PERFORMANCE = "title24_performance"
    ASHRAE_901 = "ashrae_90.1"
    IECC = "iecc"
    LEED = "leed"
    ZEROEMISSIONS = "zero_emissions"
    OTHER = "other"


@dataclass
class GeoLocation:
    """Geographic location with coordinates and address."""
    city: str = ""
    state: str = ""
    country: str = "USA"
    zip_code: str = ""
    address: str = ""
    latitude: Optional[float] = None
    longitude: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "city": self.city,
            "state": self.state,
            "country": self.country,
            "zip_code": self.zip_code,
            "address": self.address,
            "latitude": self.latitude,
            "longitude": self.longitude,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "GeoLocation":
        return cls(**data)


@dataclass
class ClimateData:
    """Climate zone information (multi-standard support)."""
    # California Title 24
    cec_climate_zone: Optional[str] = None  # CZ1-CZ16

    # ASHRAE
    ashrae_climate_zone: Optional[str] = None  # 1A-8
    ashrae_climate_name: Optional[str] = None  # "Hot-Humid", etc.

    # Weather file info
    weather_file: Optional[str] = None  # EPW or CTZ2 file
    weather_station: Optional[str] = None
    heating_degree_days: Optional[float] = None
    cooling_degree_days: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "cec_climate_zone": self.cec_climate_zone,
            "ashrae_climate_zone": self.ashrae_climate_zone,
            "ashrae_climate_name": self.ashrae_climate_name,
            "weather_file": self.weather_file,
            "weather_station": self.weather_station,
            "heating_degree_days": self.heating_degree_days,
            "cooling_degree_days": self.cooling_degree_days,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ClimateData":
        return cls(**data)


@dataclass
class BuildingGeometry:
    """Building geometry and area breakdown."""
    # Total areas
    gross_floor_area_sf: float = 0.0
    conditioned_area_sf: float = 0.0
    unconditioned_area_sf: float = 0.0

    # Envelope
    above_grade_wall_area_sf: float = 0.0
    below_grade_wall_area_sf: float = 0.0
    roof_area_sf: float = 0.0
    window_area_sf: float = 0.0
    skylight_area_sf: float = 0.0

    # Building form
    number_of_floors: int = 1
    floor_to_floor_height_ft: float = 12.0
    building_footprint_sf: float = 0.0

    # Ratios (calculated)
    window_to_wall_ratio: float = 0.0
    skylight_to_roof_ratio: float = 0.0

    def calculate_ratios(self) -> None:
        """Calculate WWR and SRR from areas."""
        if self.above_grade_wall_area_sf > 0:
            self.window_to_wall_ratio = self.window_area_sf / self.above_grade_wall_area_sf
        if self.roof_area_sf > 0:
            self.skylight_to_roof_ratio = self.skylight_area_sf / self.roof_area_sf

    def to_dict(self) -> Dict[str, Any]:
        return {
            "gross_floor_area_sf": self.gross_floor_area_sf,
            "conditioned_area_sf": self.conditioned_area_sf,
            "unconditioned_area_sf": self.unconditioned_area_sf,
            "above_grade_wall_area_sf": self.above_grade_wall_area_sf,
            "below_grade_wall_area_sf": self.below_grade_wall_area_sf,
            "roof_area_sf": self.roof_area_sf,
            "window_area_sf": self.window_area_sf,
            "skylight_area_sf": self.skylight_area_sf,
            "number_of_floors": self.number_of_floors,
            "floor_to_floor_height_ft": self.floor_to_floor_height_ft,
            "building_footprint_sf": self.building_footprint_sf,
            "window_to_wall_ratio": self.window_to_wall_ratio,
            "skylight_to_roof_ratio": self.skylight_to_roof_ratio,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "BuildingGeometry":
        return cls(**data)


@dataclass
class LcaMetadata:
    """Life Cycle Assessment metadata (OneClickLCA compatible)."""
    # Building lifespan
    reference_study_period_years: int = 60
    building_lifespan_years: int = 60

    # LCA scope
    lca_stages: List[str] = field(default_factory=lambda: ["A1-A3", "B4", "B6", "C1-C4"])

    # Structural system (impacts embodied carbon)
    structural_system: str = ""  # "steel", "concrete", "wood", "mass_timber"
    foundation_type: str = ""  # "slab", "crawl", "basement", "piles"

    # OneClickLCA project reference
    oneclicklca_project_id: Optional[str] = None
    oneclicklca_building_id: Optional[str] = None

    # Embodied carbon results (from OneClickLCA or other)
    embodied_carbon_kgco2e: Optional[float] = None
    embodied_carbon_per_sf: Optional[float] = None

    # Material quantities (for LCA)
    material_quantities: Dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "reference_study_period_years": self.reference_study_period_years,
            "building_lifespan_years": self.building_lifespan_years,
            "lca_stages": self.lca_stages,
            "structural_system": self.structural_system,
            "foundation_type": self.foundation_type,
            "oneclicklca_project_id": self.oneclicklca_project_id,
            "oneclicklca_building_id": self.oneclicklca_building_id,
            "embodied_carbon_kgco2e": self.embodied_carbon_kgco2e,
            "embodied_carbon_per_sf": self.embodied_carbon_per_sf,
            "material_quantities": self.material_quantities,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "LcaMetadata":
        return cls(**data)


@dataclass
class ComplianceInfo:
    """Code compliance information."""
    pathway: CompliancePathway = CompliancePathway.OTHER
    code_year: str = ""  # "2022", "2025"
    code_version: str = ""  # "Title 24-2022"

    # Compliance results
    is_compliant: Optional[bool] = None
    compliance_margin_pct: Optional[float] = None
    compliance_margin_tdv: Optional[float] = None

    # Energy targets
    target_eui: Optional[float] = None  # kBtu/sf/yr
    baseline_eui: Optional[float] = None
    proposed_eui: Optional[float] = None

    # Certifications
    certifications: List[str] = field(default_factory=list)  # ["LEED Gold", "WELL"]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "pathway": self.pathway.value,
            "code_year": self.code_year,
            "code_version": self.code_version,
            "is_compliant": self.is_compliant,
            "compliance_margin_pct": self.compliance_margin_pct,
            "compliance_margin_tdv": self.compliance_margin_tdv,
            "target_eui": self.target_eui,
            "baseline_eui": self.baseline_eui,
            "proposed_eui": self.proposed_eui,
            "certifications": self.certifications,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ComplianceInfo":
        data["pathway"] = CompliancePathway(data.get("pathway", "other"))
        return cls(**data)


@dataclass
class ProjectMetadata:
    """
    Comprehensive project metadata supporting CBECC, EnergyPlus, and OneClickLCA.

    This class aggregates all project information needed across different
    simulation and analysis tools.
    """
    # Core identification
    project_name: str = ""
    project_id: str = ""  # Internal ID
    client_name: str = ""
    project_phase: str = ""  # "Schematic", "DD", "CD", "As-Built"

    # Building info
    building_name: str = ""
    building_use_type: BuildingUseType = BuildingUseType.OTHER
    building_use_detail: str = ""  # More specific use description

    # Location and climate
    location: GeoLocation = field(default_factory=GeoLocation)
    climate: ClimateData = field(default_factory=ClimateData)

    # Geometry
    geometry: BuildingGeometry = field(default_factory=BuildingGeometry)

    # Compliance
    compliance: ComplianceInfo = field(default_factory=ComplianceInfo)

    # LCA (OneClickLCA)
    lca: LcaMetadata = field(default_factory=LcaMetadata)

    # Simulation info
    simulation_engine: SimulationEngine = SimulationEngine.OTHER
    simulation_version: str = ""
    simulation_date: Optional[datetime] = None

    # Project timestamps
    created_date: datetime = field(default_factory=datetime.now)
    modified_date: datetime = field(default_factory=datetime.now)

    # Custom fields (extensibility)
    custom_fields: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "project_name": self.project_name,
            "project_id": self.project_id,
            "client_name": self.client_name,
            "project_phase": self.project_phase,
            "building_name": self.building_name,
            "building_use_type": self.building_use_type.value,
            "building_use_detail": self.building_use_detail,
            "location": self.location.to_dict(),
            "climate": self.climate.to_dict(),
            "geometry": self.geometry.to_dict(),
            "compliance": self.compliance.to_dict(),
            "lca": self.lca.to_dict(),
            "simulation_engine": self.simulation_engine.value,
            "simulation_version": self.simulation_version,
            "simulation_date": self.simulation_date.isoformat() if self.simulation_date else None,
            "created_date": self.created_date.isoformat(),
            "modified_date": self.modified_date.isoformat(),
            "custom_fields": self.custom_fields,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ProjectMetadata":
        """Deserialize from dictionary."""
        return cls(
            project_name=data.get("project_name", ""),
            project_id=data.get("project_id", ""),
            client_name=data.get("client_name", ""),
            project_phase=data.get("project_phase", ""),
            building_name=data.get("building_name", ""),
            building_use_type=BuildingUseType(data.get("building_use_type", "other")),
            building_use_detail=data.get("building_use_detail", ""),
            location=GeoLocation.from_dict(data.get("location", {})),
            climate=ClimateData.from_dict(data.get("climate", {})),
            geometry=BuildingGeometry.from_dict(data.get("geometry", {})),
            compliance=ComplianceInfo.from_dict(data.get("compliance", {})),
            lca=LcaMetadata.from_dict(data.get("lca", {})),
            simulation_engine=SimulationEngine(data.get("simulation_engine", "other")),
            simulation_version=data.get("simulation_version", ""),
            simulation_date=datetime.fromisoformat(data["simulation_date"]) if data.get("simulation_date") else None,
            created_date=datetime.fromisoformat(data["created_date"]) if data.get("created_date") else datetime.now(),
            modified_date=datetime.fromisoformat(data["modified_date"]) if data.get("modified_date") else datetime.now(),
            custom_fields=data.get("custom_fields", {}),
        )


@dataclass
class SourceFiles:
    """Tracks source files for the project."""
    # Primary model files
    model_file: Optional[str] = None  # .cibd25, .idf, .osm
    model_file_hash: Optional[str] = None  # For change detection

    # Simulation results
    baseline_hourly_csv: Optional[str] = None
    proposed_hourly_csv: Optional[str] = None

    # Additional files
    weather_file: Optional[str] = None
    geometry_file: Optional[str] = None  # .hbjson, .gbxml
    schedule_file: Optional[str] = None

    # Run directory
    run_directory: Optional[str] = None

    # LCA files
    oneclicklca_export: Optional[str] = None
    material_takeoff: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "model_file": self.model_file,
            "model_file_hash": self.model_file_hash,
            "baseline_hourly_csv": self.baseline_hourly_csv,
            "proposed_hourly_csv": self.proposed_hourly_csv,
            "weather_file": self.weather_file,
            "geometry_file": self.geometry_file,
            "schedule_file": self.schedule_file,
            "run_directory": self.run_directory,
            "oneclicklca_export": self.oneclicklca_export,
            "material_takeoff": self.material_takeoff,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SourceFiles":
        return cls(**data)


@dataclass
class AnalysisState:
    """Tracks which analyses have been run and their results."""
    # Analysis flags
    lcca_completed: bool = False
    sensitivity_completed: bool = False
    esg_completed: bool = False
    econ1_completed: bool = False

    # Result references (stored separately)
    lcca_result_ids: List[str] = field(default_factory=list)
    sensitivity_result_id: Optional[str] = None
    esg_result_ids: List[str] = field(default_factory=list)

    # Analysis timestamps
    lcca_timestamp: Optional[datetime] = None
    sensitivity_timestamp: Optional[datetime] = None
    esg_timestamp: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "lcca_completed": self.lcca_completed,
            "sensitivity_completed": self.sensitivity_completed,
            "esg_completed": self.esg_completed,
            "econ1_completed": self.econ1_completed,
            "lcca_result_ids": self.lcca_result_ids,
            "sensitivity_result_id": self.sensitivity_result_id,
            "esg_result_ids": self.esg_result_ids,
            "lcca_timestamp": self.lcca_timestamp.isoformat() if self.lcca_timestamp else None,
            "sensitivity_timestamp": self.sensitivity_timestamp.isoformat() if self.sensitivity_timestamp else None,
            "esg_timestamp": self.esg_timestamp.isoformat() if self.esg_timestamp else None,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AnalysisState":
        return cls(
            lcca_completed=data.get("lcca_completed", False),
            sensitivity_completed=data.get("sensitivity_completed", False),
            esg_completed=data.get("esg_completed", False),
            econ1_completed=data.get("econ1_completed", False),
            lcca_result_ids=data.get("lcca_result_ids", []),
            sensitivity_result_id=data.get("sensitivity_result_id"),
            esg_result_ids=data.get("esg_result_ids", []),
            lcca_timestamp=datetime.fromisoformat(data["lcca_timestamp"]) if data.get("lcca_timestamp") else None,
            sensitivity_timestamp=datetime.fromisoformat(data["sensitivity_timestamp"]) if data.get("sensitivity_timestamp") else None,
            esg_timestamp=datetime.fromisoformat(data["esg_timestamp"]) if data.get("esg_timestamp") else None,
        )


class ProjectContext:
    """
    Unified project container for energy modeling and LCCA analysis.

    Holds all project data, manages simulations, and coordinates analyses.
    Designed for interactive analysis workflows.

    Use ProjectContextBuilder for construction.

    Attributes:
        metadata: Project identification and building information
        source_files: Paths to model and result files
        scenario_manager: ScenarioManager instance for LCCA scenarios
        ecm_bundle: ECMBundle for tracking energy conservation measures
        tariff: TOU tariff for cost calculations
        analysis_state: Tracks completed analyses
    """

    def __init__(self):
        """Initialize empty project context. Use Builder for construction."""
        self.metadata = ProjectMetadata()
        self.source_files = SourceFiles()
        self.analysis_state = AnalysisState()

        # Lazy-loaded components
        self._scenario_manager: Optional[Any] = None  # ScenarioManager
        self._ecm_bundle: Optional[Any] = None  # ECMBundle
        self._tariff: Optional[Any] = None  # TouTariff
        self._assumptions: Optional[Any] = None  # ScenarioAssumptions

        # Cached simulation outputs
        self._baseline_output: Optional[Any] = None  # SimulationOutput
        self._proposed_output: Optional[Any] = None  # SimulationOutput

        # Analysis results cache
        self._lcca_results: Dict[str, Any] = {}  # TouLccaResults
        self._sensitivity_analyzer: Optional[Any] = None
        self._esg_reports: Dict[str, Any] = {}

        # Project file path (if saved/loaded)
        self._project_file: Optional[str] = None

    @property
    def scenario_manager(self) -> Any:
        """Get or create ScenarioManager."""
        if self._scenario_manager is None:
            from .scenario_manager import ScenarioManager
            self._scenario_manager = ScenarioManager(self.metadata.project_name)
        return self._scenario_manager

    @property
    def ecm_bundle(self) -> Any:
        """Get or create ECMBundle."""
        if self._ecm_bundle is None:
            from .ecm_bundle import ECMBundle
            self._ecm_bundle = ECMBundle(name=f"{self.metadata.project_name} ECMs")
        return self._ecm_bundle

    @property
    def tariff(self) -> Optional[Any]:
        """Get configured tariff."""
        return self._tariff

    @property
    def assumptions(self) -> Any:
        """Get or create default assumptions."""
        if self._assumptions is None:
            from .model import ScenarioAssumptions
            self._assumptions = ScenarioAssumptions()
        return self._assumptions

    @property
    def baseline_output(self) -> Optional[Any]:
        """Get cached baseline SimulationOutput."""
        return self._baseline_output

    @property
    def proposed_output(self) -> Optional[Any]:
        """Get cached proposed SimulationOutput."""
        return self._proposed_output

    def load_simulations(self) -> None:
        """Load simulation outputs from source files."""
        from .parsers import parse_hourly_results

        if self.source_files.baseline_hourly_csv:
            self._baseline_output = parse_hourly_results(
                self.source_files.baseline_hourly_csv
            )

        if self.source_files.proposed_hourly_csv:
            self._proposed_output = parse_hourly_results(
                self.source_files.proposed_hourly_csv
            )

        # Update metadata from simulation if available
        if self._proposed_output:
            self._update_metadata_from_simulation(self._proposed_output)

    def _update_metadata_from_simulation(self, output: Any) -> None:
        """Update project metadata from simulation output."""
        if hasattr(output, 'project_name') and output.project_name:
            if not self.metadata.project_name:
                self.metadata.project_name = output.project_name

        if hasattr(output, 'conditioned_area_sf') and output.conditioned_area_sf:
            self.metadata.geometry.conditioned_area_sf = output.conditioned_area_sf

        if hasattr(output, 'climate_zone') and output.climate_zone:
            self.metadata.climate.cec_climate_zone = output.climate_zone

        if hasattr(output, 'building_type') and output.building_type:
            self.metadata.building_use_detail = output.building_type

    def setup_scenarios(self, pv_capex: float = 0) -> None:
        """
        Set up LCCA scenarios from loaded simulations.

        Args:
            pv_capex: PV system capital cost
        """
        if not self._tariff:
            raise ValueError("Tariff must be set before creating scenarios")

        if not self._baseline_output or not self._proposed_output:
            self.load_simulations()

        if not self._baseline_output or not self._proposed_output:
            raise ValueError("Could not load simulation outputs")

        # Use scenario manager to create scenarios
        self.scenario_manager.load_from_cbecc(
            baseline_path=self.source_files.baseline_hourly_csv,
            proposed_path=self.source_files.proposed_hourly_csv,
            tariff=self._tariff,
            pv_capex=pv_capex,
        )

    def run_lcca(
        self,
        baseline_name: str = "baseline",
        proposed_name: str = "proposed",
        result_id: Optional[str] = None,
    ) -> Any:
        """
        Run LCCA analysis on scenarios.

        Args:
            baseline_name: Name of baseline scenario
            proposed_name: Name of proposed scenario
            result_id: Optional ID for storing result

        Returns:
            TouLccaResults
        """
        from .calculators import run_tou_lcca

        baseline = self.scenario_manager.get_scenario(baseline_name)
        proposed = self.scenario_manager.get_scenario(proposed_name)

        results = run_tou_lcca(baseline, proposed, assumptions=self._assumptions)

        # Cache results
        if result_id is None:
            result_id = f"{baseline_name}_vs_{proposed_name}"
        self._lcca_results[result_id] = results

        # Update state
        self.analysis_state.lcca_completed = True
        self.analysis_state.lcca_timestamp = datetime.now()
        if result_id not in self.analysis_state.lcca_result_ids:
            self.analysis_state.lcca_result_ids.append(result_id)

        self.metadata.modified_date = datetime.now()

        return results

    def get_lcca_results(self, result_id: str = "baseline_vs_proposed") -> Optional[Any]:
        """Get cached LCCA results."""
        return self._lcca_results.get(result_id)

    def run_sensitivity(
        self,
        baseline_name: str = "baseline",
        proposed_name: str = "proposed",
    ) -> Any:
        """
        Run sensitivity analysis.

        Returns:
            SensitivityAnalyzer configured for this project
        """
        from .sensitivity import SensitivityAnalyzer

        baseline = self.scenario_manager.get_scenario(baseline_name)
        proposed = self.scenario_manager.get_scenario(proposed_name)

        self._sensitivity_analyzer = SensitivityAnalyzer(
            baseline, proposed, self._assumptions
        )

        self.analysis_state.sensitivity_completed = True
        self.analysis_state.sensitivity_timestamp = datetime.now()
        self.metadata.modified_date = datetime.now()

        return self._sensitivity_analyzer

    def get_sensitivity_analyzer(self) -> Optional[Any]:
        """Get sensitivity analyzer instance."""
        return self._sensitivity_analyzer

    def run_esg(self, result_id: str = "default") -> Any:
        """
        Run ESG/carbon analysis.

        Returns:
            EsgReport
        """
        from .esg_report import generate_esg_report

        if not self._proposed_output:
            self.load_simulations()

        if not self._proposed_output:
            raise ValueError("Could not load simulation output")

        report = generate_esg_report(
            annual_summary=self._proposed_output.annual,
            building_area_sf=self.metadata.geometry.conditioned_area_sf or 1.0,
            project_name=self.metadata.project_name,
        )

        self._esg_reports[result_id] = report

        self.analysis_state.esg_completed = True
        self.analysis_state.esg_timestamp = datetime.now()
        if result_id not in self.analysis_state.esg_result_ids:
            self.analysis_state.esg_result_ids.append(result_id)

        self.metadata.modified_date = datetime.now()

        return report

    def summary(self) -> str:
        """Generate project summary text."""
        lines = [
            "=" * 70,
            f"PROJECT: {self.metadata.project_name}",
            "=" * 70,
            "",
            "METADATA",
            "-" * 40,
            f"  Building:        {self.metadata.building_name or 'N/A'}",
            f"  Use Type:        {self.metadata.building_use_type.value}",
            f"  Location:        {self.metadata.location.city}, {self.metadata.location.state}",
            f"  Climate Zone:    {self.metadata.climate.cec_climate_zone or 'N/A'}",
            f"  Conditioned SF:  {self.metadata.geometry.conditioned_area_sf:,.0f}",
            "",
            "SOURCE FILES",
            "-" * 40,
            f"  Model:           {Path(self.source_files.model_file).name if self.source_files.model_file else 'N/A'}",
            f"  Baseline:        {Path(self.source_files.baseline_hourly_csv).name if self.source_files.baseline_hourly_csv else 'N/A'}",
            f"  Proposed:        {Path(self.source_files.proposed_hourly_csv).name if self.source_files.proposed_hourly_csv else 'N/A'}",
            "",
            "ANALYSIS STATUS",
            "-" * 40,
            f"  Scenarios:       {len(self.scenario_manager.scenario_names)} loaded",
            f"  ECMs:            {self.ecm_bundle.ecm_count} defined",
            f"  LCCA:            {'Complete' if self.analysis_state.lcca_completed else 'Not run'}",
            f"  Sensitivity:     {'Complete' if self.analysis_state.sensitivity_completed else 'Not run'}",
            f"  ESG:             {'Complete' if self.analysis_state.esg_completed else 'Not run'}",
            "=" * 70,
        ]
        return "\n".join(lines)

    def save(self, filepath: str) -> None:
        """
        Save project to .eco file (ZIP bundle).

        Args:
            filepath: Path for output file
        """
        filepath = Path(filepath)
        if not filepath.suffix:
            filepath = filepath.with_suffix(".eco")

        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)

            # Save project.json
            project_data = {
                "version": "1.0",
                "metadata": self.metadata.to_dict(),
                "source_files": self.source_files.to_dict(),
                "analysis_state": self.analysis_state.to_dict(),
                "tariff_name": self._tariff.name if self._tariff else None,
                "assumptions": {
                    "analysis_years": self._assumptions.analysis_years,
                    "discount_rate_real": self._assumptions.discount_rate_real,
                    "elec_escalation": self._assumptions.elec_escalation,
                    "gas_escalation": self._assumptions.gas_escalation,
                } if self._assumptions else None,
            }

            with open(tmpdir / "project.json", "w") as f:
                json.dump(project_data, f, indent=2)

            # Save ECM bundle if present
            if self._ecm_bundle and self._ecm_bundle.ecm_count > 0:
                ecm_data = {
                    "name": self._ecm_bundle.name,
                    "ecms": [
                        {
                            "name": ecm.name,
                            "category": ecm.category.value,
                            "capex": ecm.capex,
                            "annual_kwh_delta": ecm.annual_kwh_delta,
                            "annual_kwh_generation": ecm.annual_kwh_generation,
                            "annual_therm_delta": ecm.annual_therm_delta,
                            "incentives": ecm.incentives,
                        }
                        for ecm in self._ecm_bundle._ecms.values()
                    ],
                }
                with open(tmpdir / "ecm_bundle.json", "w") as f:
                    json.dump(ecm_data, f, indent=2)

            # Save LCCA results
            if self._lcca_results:
                lcca_data = {}
                for result_id, result in self._lcca_results.items():
                    lcca_data[result_id] = {
                        "npv": result.npv,
                        "irr": result.irr,
                        "simple_payback_years": result.simple_payback_years,
                        "sir": result.sir,
                        "annual_savings": result.annual_savings,
                        "baseline_annual_cost": result.baseline_annual_cost,
                        "proposed_annual_cost": result.proposed_annual_cost,
                    }
                with open(tmpdir / "lcca_results.json", "w") as f:
                    json.dump(lcca_data, f, indent=2)

            # Create ZIP
            with zipfile.ZipFile(filepath, "w", zipfile.ZIP_DEFLATED) as zf:
                for file in tmpdir.iterdir():
                    zf.write(file, file.name)

        self._project_file = str(filepath)

    @classmethod
    def load(cls, filepath: str) -> "ProjectContext":
        """
        Load project from .eco file.

        Args:
            filepath: Path to .eco file

        Returns:
            ProjectContext instance
        """
        filepath = Path(filepath)

        project = cls()
        project._project_file = str(filepath)

        with zipfile.ZipFile(filepath, "r") as zf:
            # Load project.json
            with zf.open("project.json") as f:
                project_data = json.load(f)

            project.metadata = ProjectMetadata.from_dict(project_data.get("metadata", {}))
            project.source_files = SourceFiles.from_dict(project_data.get("source_files", {}))
            project.analysis_state = AnalysisState.from_dict(project_data.get("analysis_state", {}))

            # Restore tariff
            tariff_name = project_data.get("tariff_name")
            if tariff_name:
                from .tariffs import get_tariff_by_name
                project._tariff = get_tariff_by_name(tariff_name)

            # Restore assumptions
            if project_data.get("assumptions"):
                from .model import ScenarioAssumptions
                project._assumptions = ScenarioAssumptions(**project_data["assumptions"])

            # Load ECM bundle if present
            if "ecm_bundle.json" in zf.namelist():
                with zf.open("ecm_bundle.json") as f:
                    ecm_data = json.load(f)
                from .ecm_bundle import ECMBundle, ECM, ECMCategory
                project._ecm_bundle = ECMBundle(name=ecm_data.get("name", "ECMs"))
                for ecm_dict in ecm_data.get("ecms", []):
                    ecm = ECM(
                        name=ecm_dict["name"],
                        category=ECMCategory(ecm_dict["category"]),
                        capex=ecm_dict.get("capex", 0),
                        annual_kwh_delta=ecm_dict.get("annual_kwh_delta", 0),
                        annual_kwh_generation=ecm_dict.get("annual_kwh_generation", 0),
                        annual_therm_delta=ecm_dict.get("annual_therm_delta", 0),
                        incentives=ecm_dict.get("incentives", []),
                    )
                    project._ecm_bundle.add_ecm(ecm)

            # Load LCCA results if present
            if "lcca_results.json" in zf.namelist():
                with zf.open("lcca_results.json") as f:
                    lcca_data = json.load(f)
                # Store as dicts for now (full reconstruction would need scenarios)
                project._lcca_results = lcca_data

        return project


class ProjectContextBuilder:
    """
    Builder for constructing ProjectContext with fluent API.

    Example:
        >>> project = (ProjectContextBuilder()
        ...     .with_name("My Building")
        ...     .with_location(city="Los Angeles", state="CA")
        ...     .from_cbecc_results(baseline_csv, proposed_csv)
        ...     .with_tariff(create_sce_tou_gs3())
        ...     .build())
    """

    def __init__(self):
        self._context = ProjectContext()

    def with_name(self, name: str) -> "ProjectContextBuilder":
        """Set project name."""
        self._context.metadata.project_name = name
        return self

    def with_project_id(self, project_id: str) -> "ProjectContextBuilder":
        """Set project ID."""
        self._context.metadata.project_id = project_id
        return self

    def with_client(self, client_name: str) -> "ProjectContextBuilder":
        """Set client name."""
        self._context.metadata.client_name = client_name
        return self

    def with_building_name(self, name: str) -> "ProjectContextBuilder":
        """Set building name."""
        self._context.metadata.building_name = name
        return self

    def with_building_type(
        self,
        use_type: Union[BuildingUseType, str],
        detail: str = "",
    ) -> "ProjectContextBuilder":
        """Set building use type."""
        if isinstance(use_type, str):
            use_type = BuildingUseType(use_type.lower())
        self._context.metadata.building_use_type = use_type
        self._context.metadata.building_use_detail = detail
        return self

    def with_location(
        self,
        city: str = "",
        state: str = "",
        zip_code: str = "",
        address: str = "",
        latitude: Optional[float] = None,
        longitude: Optional[float] = None,
        country: str = "USA",
    ) -> "ProjectContextBuilder":
        """Set project location."""
        self._context.metadata.location = GeoLocation(
            city=city,
            state=state,
            country=country,
            zip_code=zip_code,
            address=address,
            latitude=latitude,
            longitude=longitude,
        )
        return self

    def with_climate(
        self,
        cec_zone: Optional[str] = None,
        ashrae_zone: Optional[str] = None,
        weather_file: Optional[str] = None,
    ) -> "ProjectContextBuilder":
        """Set climate information."""
        self._context.metadata.climate.cec_climate_zone = cec_zone
        self._context.metadata.climate.ashrae_climate_zone = ashrae_zone
        self._context.metadata.climate.weather_file = weather_file
        return self

    def with_geometry(
        self,
        conditioned_area_sf: float = 0,
        gross_floor_area_sf: float = 0,
        number_of_floors: int = 1,
        window_to_wall_ratio: float = 0,
    ) -> "ProjectContextBuilder":
        """Set building geometry."""
        self._context.metadata.geometry.conditioned_area_sf = conditioned_area_sf
        self._context.metadata.geometry.gross_floor_area_sf = gross_floor_area_sf or conditioned_area_sf
        self._context.metadata.geometry.number_of_floors = number_of_floors
        self._context.metadata.geometry.window_to_wall_ratio = window_to_wall_ratio
        return self

    def with_compliance(
        self,
        pathway: Union[CompliancePathway, str] = CompliancePathway.OTHER,
        code_year: str = "",
        is_compliant: Optional[bool] = None,
    ) -> "ProjectContextBuilder":
        """Set compliance information."""
        if isinstance(pathway, str):
            pathway = CompliancePathway(pathway.lower())
        self._context.metadata.compliance.pathway = pathway
        self._context.metadata.compliance.code_year = code_year
        self._context.metadata.compliance.is_compliant = is_compliant
        return self

    def with_lca(
        self,
        study_period_years: int = 60,
        structural_system: str = "",
        oneclicklca_project_id: Optional[str] = None,
    ) -> "ProjectContextBuilder":
        """Set LCA metadata."""
        self._context.metadata.lca.reference_study_period_years = study_period_years
        self._context.metadata.lca.building_lifespan_years = study_period_years
        self._context.metadata.lca.structural_system = structural_system
        self._context.metadata.lca.oneclicklca_project_id = oneclicklca_project_id
        return self

    def from_cbecc_results(
        self,
        baseline_csv: str,
        proposed_csv: str,
        model_file: Optional[str] = None,
    ) -> "ProjectContextBuilder":
        """Load from CBECC HourlyResults files."""
        self._context.source_files.baseline_hourly_csv = str(baseline_csv)
        self._context.source_files.proposed_hourly_csv = str(proposed_csv)
        self._context.source_files.model_file = str(model_file) if model_file else None
        self._context.metadata.simulation_engine = SimulationEngine.CBECC

        # Extract run directory
        baseline_path = Path(baseline_csv)
        if baseline_path.exists():
            self._context.source_files.run_directory = str(baseline_path.parent)

        return self

    def from_energyplus_results(
        self,
        baseline_csv: str,
        proposed_csv: str,
        idf_file: Optional[str] = None,
        weather_file: Optional[str] = None,
    ) -> "ProjectContextBuilder":
        """Load from EnergyPlus results."""
        self._context.source_files.baseline_hourly_csv = str(baseline_csv)
        self._context.source_files.proposed_hourly_csv = str(proposed_csv)
        self._context.source_files.model_file = str(idf_file) if idf_file else None
        self._context.source_files.weather_file = str(weather_file) if weather_file else None
        self._context.metadata.simulation_engine = SimulationEngine.ENERGYPLUS
        return self

    def with_tariff(self, tariff: Any) -> "ProjectContextBuilder":
        """Set TOU tariff for cost calculations."""
        self._context._tariff = tariff
        return self

    def with_assumptions(
        self,
        analysis_years: int = 20,
        discount_rate: float = 0.03,
        elec_escalation: float = 0.02,
        gas_escalation: float = 0.015,
    ) -> "ProjectContextBuilder":
        """Set LCCA assumptions."""
        from .model import ScenarioAssumptions
        self._context._assumptions = ScenarioAssumptions(
            analysis_years=analysis_years,
            discount_rate_real=discount_rate,
            elec_escalation=elec_escalation,
            gas_escalation=gas_escalation,
        )
        return self

    def with_pv_system(
        self,
        capacity_kw: float,
        cost_per_watt: float = 2.50,
        itc_pct: float = 0.30,
    ) -> "ProjectContextBuilder":
        """Add PV system ECM."""
        from .ecm_bundle import create_pv_ecm
        pv_ecm = create_pv_ecm(
            capacity_kw=capacity_kw,
            cost_per_watt=cost_per_watt,
            itc_pct=itc_pct,
        )
        self._context.ecm_bundle.add_ecm(pv_ecm)
        return self

    def with_ecm(self, ecm: Any) -> "ProjectContextBuilder":
        """Add an ECM to the project."""
        self._context.ecm_bundle.add_ecm(ecm)
        return self

    def with_custom_field(self, key: str, value: Any) -> "ProjectContextBuilder":
        """Add custom metadata field."""
        self._context.metadata.custom_fields[key] = value
        return self

    def build(self) -> ProjectContext:
        """
        Build the ProjectContext.

        Returns:
            Configured ProjectContext instance
        """
        # Auto-load simulations if paths provided
        if (self._context.source_files.baseline_hourly_csv and
                self._context.source_files.proposed_hourly_csv):
            try:
                self._context.load_simulations()
            except Exception:
                pass  # Allow building without valid simulation files

        # Set up scenarios if tariff provided
        if self._context._tariff and self._context._baseline_output:
            try:
                pv_capex = self._context.ecm_bundle.total_capex if self._context._ecm_bundle else 0
                self._context.setup_scenarios(pv_capex=pv_capex)
            except Exception:
                pass  # Allow building without scenarios

        return self._context
