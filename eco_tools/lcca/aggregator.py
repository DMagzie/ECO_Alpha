"""
Unified LCCA Data Aggregator.

Aggregates data from all CBECC simulation output parsers into a single
unified data structure for LCCA analysis.

This module provides:
- LCCADataAggregator: Main class for parsing all simulation outputs
- LCCAInputData: Unified data container with all parsed information

Usage:
    from eco_tools.lcca.aggregator import LCCADataAggregator

    aggregator = LCCADataAggregator("/path/to/project")
    data = aggregator.parse_all()

    # Access unified data
    print(data.project_info.project_name)
    print(data.energy.proposed_total_kwh)
    print(len(data.hvac.air_systems_proposed))
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, List, Dict, Any
import logging

from .auto_discovery import (
    discover_simulation_outputs,
    DiscoveredOutputs,
    SimulationFile,
)
from .model import SimulationOutput  # HourlyResults returns SimulationOutput
from .parsers import (
    # Hourly Results parser (returns SimulationOutput)
    parse_hourly_results,
    # CSE Hourly (detailed end-use)
    parse_cse_detailed,
    CSEDetailedOutput,
    # Analysis Results XML
    parse_analysis_results,
    AnalysisResultsOutput,
    # HVAC Secondary
    parse_hvac_secondary,
    HVACSecondaryOutput,
    # HVAC Capacities
    parse_hvac_caps,
    HVACCapsOutput,
    # HVAC Primary (DHW/Central Plant)
    parse_hvac_primary,
    HVACPrimaryOutput,
    # Envelope
    parse_envelope,
    EnvelopeOutput,
    # CSE Input (DHW specs)
    parse_cse_input,
    CSEInputOutput,
    # NRCCPRF (Compliance Report)
    parse_nrccprf,
    NRCCPRFOutput,
)

logger = logging.getLogger(__name__)


@dataclass
class ProjectInfo:
    """Basic project information from compliance report."""
    project_name: str = ''
    street_address: str = ''
    city: str = ''
    zipcode: str = ''
    climate_zone: int = 0
    occupancy_type: str = ''  # HighRiseResidential, Office, etc.
    project_scope: str = ''  # NewComplete, ExistingAddition, etc.
    dwelling_units: int = 0
    conditioned_floor_area_sf: float = 0.0
    above_grade_stories: int = 0
    standards_version: str = ''
    software_version: str = ''
    run_datetime: str = ''

    @classmethod
    def from_nrccprf(cls, nrccprf: NRCCPRFOutput) -> 'ProjectInfo':
        """Create ProjectInfo from NRCCPRF data."""
        info = nrccprf.project
        return cls(
            project_name=info.project_name,
            street_address=info.street_address,
            city=info.city,
            zipcode=info.zipcode,
            climate_zone=info.climate_zone,
            occupancy_type=info.occupancy_type,
            project_scope=info.project_scope,
            dwelling_units=info.dwelling_units,
            conditioned_floor_area_sf=info.conditioned_floor_area_sf,
            above_grade_stories=info.above_grade_stories,
            standards_version=info.standards_version,
            software_version=info.software_version,
            run_datetime=info.run_datetime,
        )


@dataclass
class ComplianceInfo:
    """Compliance results from NRCCPRF."""
    passes_compliance: bool = False
    compliance_result: str = ''

    # Efficiency metrics (kTDV/ft2)
    standard_efficiency: float = 0.0
    proposed_efficiency: float = 0.0
    margin_efficiency: float = 0.0
    pass_fail_efficiency: str = ''

    # Total metrics (including PV/Battery)
    standard_total: float = 0.0
    proposed_total: float = 0.0
    margin_total: float = 0.0
    pass_fail_total: str = ''

    @classmethod
    def from_nrccprf(cls, nrccprf: NRCCPRFOutput) -> 'ComplianceInfo':
        """Create ComplianceInfo from NRCCPRF data."""
        result = nrccprf.compliance
        return cls(
            passes_compliance=result.passes_compliance,
            compliance_result=result.compliance_result,
            standard_efficiency=result.standard_efficiency,
            proposed_efficiency=result.proposed_efficiency,
            margin_efficiency=result.margin_efficiency,
            pass_fail_efficiency=result.pass_fail_efficiency,
            standard_total=result.standard_total,
            proposed_total=result.proposed_total,
            margin_total=result.margin_total,
            pass_fail_total=result.pass_fail_total,
        )


@dataclass
class EnergyData:
    """Aggregated energy data from simulation outputs."""
    # Annual totals (kWh/therms)
    proposed_elec_kwh: float = 0.0
    proposed_gas_therms: float = 0.0
    standard_elec_kwh: float = 0.0
    standard_gas_therms: float = 0.0

    # PV/Battery
    pv_generation_kwh: float = 0.0
    battery_discharge_kwh: float = 0.0

    # End-use breakdown (proposed, kWh)
    cooling_kwh: float = 0.0
    heating_kwh: float = 0.0
    heating_backup_kwh: float = 0.0
    dhw_kwh: float = 0.0
    dhw_backup_kwh: float = 0.0
    fans_kwh: float = 0.0
    lighting_kwh: float = 0.0
    receptacle_kwh: float = 0.0
    appliances_kwh: float = 0.0  # Sum of cooking, dryer, washer, dishwasher, refrigerator

    # Detailed hourly data available
    hourly_proposed: Optional[SimulationOutput] = None
    hourly_standard: Optional[SimulationOutput] = None
    detailed_proposed: Optional[CSEDetailedOutput] = None
    detailed_standard: Optional[CSEDetailedOutput] = None


@dataclass
class HVACData:
    """Aggregated HVAC data from simulation outputs."""
    # Air systems
    air_systems_proposed: List[Any] = field(default_factory=list)
    air_systems_standard: List[Any] = field(default_factory=list)

    # Zone systems
    zone_systems_proposed: List[Any] = field(default_factory=list)
    zone_systems_standard: List[Any] = field(default_factory=list)

    # Cooling coils
    cooling_coils_proposed: List[Any] = field(default_factory=list)
    cooling_coils_standard: List[Any] = field(default_factory=list)

    # Heating coils
    heating_coils_proposed: List[Any] = field(default_factory=list)
    heating_coils_standard: List[Any] = field(default_factory=list)

    # Fans
    fans_proposed: List[Any] = field(default_factory=list)
    fans_standard: List[Any] = field(default_factory=list)

    # HVAC Capacities (residential auto-sizing)
    capacities_proposed: Optional[HVACCapsOutput] = None
    capacities_standard: Optional[HVACCapsOutput] = None

    # Full parsed outputs for detailed access
    secondary_proposed: Optional[HVACSecondaryOutput] = None
    secondary_standard: Optional[HVACSecondaryOutput] = None

    # Summary metrics
    total_cooling_capacity_proposed_btuh: float = 0.0
    total_cooling_capacity_standard_btuh: float = 0.0
    total_heating_capacity_proposed_btuh: float = 0.0
    total_heating_capacity_standard_btuh: float = 0.0


@dataclass
class DHWData:
    """Aggregated DHW data from simulation outputs."""
    # Water heaters
    water_heaters_proposed: List[Any] = field(default_factory=list)
    water_heaters_standard: List[Any] = field(default_factory=list)

    # Boilers
    boilers_proposed: List[Any] = field(default_factory=list)
    boilers_standard: List[Any] = field(default_factory=list)

    # Fluid systems
    fluid_systems_proposed: List[Any] = field(default_factory=list)
    fluid_systems_standard: List[Any] = field(default_factory=list)

    # CSE Input DHW specs (detailed equipment specs)
    cse_heaters_proposed: List[Any] = field(default_factory=list)
    cse_heaters_standard: List[Any] = field(default_factory=list)
    cse_systems_proposed: List[Any] = field(default_factory=list)
    cse_systems_standard: List[Any] = field(default_factory=list)

    # Full parsed outputs
    primary_proposed: Optional[HVACPrimaryOutput] = None
    primary_standard: Optional[HVACPrimaryOutput] = None
    cse_input_proposed: Optional[CSEInputOutput] = None
    cse_input_standard: Optional[CSEInputOutput] = None

    # Summary metrics
    total_heater_count_proposed: int = 0
    total_heater_count_standard: int = 0
    total_tank_volume_proposed_gal: float = 0.0
    total_tank_volume_standard_gal: float = 0.0
    heat_pump_count_proposed: int = 0
    heat_pump_count_standard: int = 0


@dataclass
class EnvelopeData:
    """Aggregated envelope data from simulation outputs."""
    # Building areas
    total_wall_area_sf: float = 0.0
    total_window_area_sf: float = 0.0
    window_to_wall_ratio: float = 0.0
    total_roof_area_sf: float = 0.0
    conditioned_floor_area_sf: float = 0.0

    # Exterior walls
    walls_proposed: List[Any] = field(default_factory=list)
    walls_standard: List[Any] = field(default_factory=list)

    # Windows
    windows_proposed: List[Any] = field(default_factory=list)
    windows_standard: List[Any] = field(default_factory=list)

    # Roofs
    roofs_proposed: List[Any] = field(default_factory=list)
    roofs_standard: List[Any] = field(default_factory=list)

    # Full parsed outputs
    envelope_proposed: Optional[EnvelopeOutput] = None
    envelope_standard: Optional[EnvelopeOutput] = None
    analysis_results: Optional[AnalysisResultsOutput] = None


@dataclass
class LCCAInputData:
    """
    Unified LCCA input data aggregated from all simulation outputs.

    This is the primary data container for LCCA analysis, containing:
    - Project information and compliance results
    - Energy consumption data (annual and hourly)
    - HVAC equipment specifications
    - DHW equipment specifications
    - Envelope specifications

    All data is organized by scenario (proposed vs standard) where available.
    """
    # Discovery results
    discovery: Optional[DiscoveredOutputs] = None

    # Project and compliance
    project_info: ProjectInfo = field(default_factory=ProjectInfo)
    compliance: ComplianceInfo = field(default_factory=ComplianceInfo)

    # Energy data
    energy: EnergyData = field(default_factory=EnergyData)

    # HVAC data
    hvac: HVACData = field(default_factory=HVACData)

    # DHW data
    dhw: DHWData = field(default_factory=DHWData)

    # Envelope data
    envelope: EnvelopeData = field(default_factory=EnvelopeData)

    # Parsing metadata
    parse_errors: List[str] = field(default_factory=list)
    parse_warnings: List[str] = field(default_factory=list)
    files_parsed: List[str] = field(default_factory=list)

    @property
    def project_name(self) -> str:
        """Get project name from available sources."""
        if self.project_info.project_name:
            return self.project_info.project_name
        if self.discovery:
            return self.discovery.project_name
        return ''

    @property
    def is_complete(self) -> bool:
        """Check if minimum data is available for LCCA."""
        return self.energy.proposed_elec_kwh > 0 or self.energy.proposed_gas_therms > 0

    @property
    def has_comparison_data(self) -> bool:
        """Check if both proposed and standard data available."""
        return (self.energy.standard_elec_kwh > 0 or
                self.energy.standard_gas_therms > 0)

    @property
    def has_hvac_data(self) -> bool:
        """Check if HVAC data is available."""
        return (len(self.hvac.air_systems_proposed) > 0 or
                len(self.hvac.zone_systems_proposed) > 0 or
                self.hvac.capacities_proposed is not None)

    @property
    def has_dhw_data(self) -> bool:
        """Check if DHW data is available."""
        return (len(self.dhw.water_heaters_proposed) > 0 or
                len(self.dhw.cse_heaters_proposed) > 0)

    @property
    def has_envelope_data(self) -> bool:
        """Check if envelope data is available."""
        return (self.envelope.envelope_proposed is not None or
                self.envelope.analysis_results is not None)

    def summary(self) -> Dict[str, Any]:
        """Get summary of aggregated data."""
        return {
            'project_name': self.project_name,
            'is_complete': self.is_complete,
            'has_comparison_data': self.has_comparison_data,
            'has_hvac_data': self.has_hvac_data,
            'has_dhw_data': self.has_dhw_data,
            'has_envelope_data': self.has_envelope_data,
            'files_parsed': len(self.files_parsed),
            'errors': len(self.parse_errors),
            'warnings': len(self.parse_warnings),
            'energy': {
                'proposed_elec_kwh': self.energy.proposed_elec_kwh,
                'proposed_gas_therms': self.energy.proposed_gas_therms,
                'standard_elec_kwh': self.energy.standard_elec_kwh,
                'standard_gas_therms': self.energy.standard_gas_therms,
                'pv_generation_kwh': self.energy.pv_generation_kwh,
            },
            'compliance': {
                'passes': self.compliance.passes_compliance,
                'margin_efficiency': self.compliance.margin_efficiency,
            },
        }


class LCCADataAggregator:
    """
    Aggregates data from all CBECC simulation output parsers.

    This class provides a single entry point for parsing all available
    simulation outputs and aggregating them into a unified data structure.

    Usage:
        aggregator = LCCADataAggregator("/path/to/project")
        data = aggregator.parse_all()

        # Or parse specific file types
        aggregator.parse_energy()
        aggregator.parse_hvac()
        data = aggregator.data
    """

    def __init__(self, project_dir: str | Path):
        """
        Initialize aggregator for a project directory.

        Args:
            project_dir: Path to project directory containing simulation outputs
        """
        self.project_dir = Path(project_dir)
        self.data = LCCAInputData()
        self._discovery: Optional[DiscoveredOutputs] = None

    def discover_files(self) -> DiscoveredOutputs:
        """Discover all simulation output files."""
        if self._discovery is None:
            self._discovery = discover_simulation_outputs(self.project_dir)
            self.data.discovery = self._discovery
        return self._discovery

    def parse_all(self) -> LCCAInputData:
        """
        Parse all available simulation outputs.

        Returns:
            LCCAInputData with all aggregated data
        """
        self.discover_files()

        # Parse in order of priority/dependency
        self.parse_compliance()
        self.parse_energy()
        self.parse_hvac()
        self.parse_dhw()
        self.parse_envelope()

        return self.data

    def parse_compliance(self) -> None:
        """Parse NRCCPRF compliance report."""
        if self._discovery is None:
            self.discover_files()

        if self._discovery.nrccprf:
            try:
                nrccprf = parse_nrccprf(self._discovery.nrccprf.path)
                self.data.project_info = ProjectInfo.from_nrccprf(nrccprf)
                self.data.compliance = ComplianceInfo.from_nrccprf(nrccprf)
                self.data.files_parsed.append(str(self._discovery.nrccprf.path.name))
                logger.debug(f"Parsed NRCCPRF: {self._discovery.nrccprf.path.name}")
            except Exception as e:
                self.data.parse_errors.append(f"NRCCPRF parse error: {e}")
                logger.warning(f"Error parsing NRCCPRF: {e}")

    def parse_energy(self) -> None:
        """Parse energy data from hourly results and CSE files."""
        if self._discovery is None:
            self.discover_files()

        energy = self.data.energy

        # Parse HourlyResults
        if self._discovery.hourly_results_proposed:
            try:
                sim_output = parse_hourly_results(self._discovery.hourly_results_proposed.path)
                energy.hourly_proposed = sim_output
                energy.proposed_elec_kwh = sim_output.annual.total_elec_kwh
                energy.proposed_gas_therms = sim_output.annual.total_gas_therm
                energy.pv_generation_kwh = sim_output.annual.pv_generation_kwh
                # Battery discharge is in HourlyEnergy, sum it up
                energy.battery_discharge_kwh = sum(
                    h.battery_kwh for h in sim_output.hourly if h.battery_kwh > 0
                )
                self.data.files_parsed.append(str(self._discovery.hourly_results_proposed.path.name))
                logger.debug(f"Parsed HourlyResults (proposed)")
            except Exception as e:
                self.data.parse_errors.append(f"HourlyResults (proposed) parse error: {e}")
                logger.warning(f"Error parsing HourlyResults (proposed): {e}")

        if self._discovery.hourly_results_standard:
            try:
                sim_output = parse_hourly_results(self._discovery.hourly_results_standard.path)
                energy.hourly_standard = sim_output
                energy.standard_elec_kwh = sim_output.annual.total_elec_kwh
                energy.standard_gas_therms = sim_output.annual.total_gas_therm
                self.data.files_parsed.append(str(self._discovery.hourly_results_standard.path.name))
                logger.debug(f"Parsed HourlyResults (standard)")
            except Exception as e:
                self.data.parse_errors.append(f"HourlyResults (standard) parse error: {e}")
                logger.warning(f"Error parsing HourlyResults (standard): {e}")

        # Parse CSE detailed (for end-use breakdown)
        if self._discovery.cse_proposed:
            try:
                detailed = parse_cse_detailed(self._discovery.cse_proposed.path)
                energy.detailed_proposed = detailed

                # Extract end-use breakdown from annual totals
                if detailed.annual:
                    ann = detailed.annual
                    energy.cooling_kwh = ann.elec_cooling
                    energy.heating_kwh = ann.elec_heating
                    energy.heating_backup_kwh = ann.elec_hp_backup
                    energy.dhw_kwh = ann.elec_dhw
                    energy.dhw_backup_kwh = ann.elec_dhw_backup
                    energy.fans_kwh = (
                        ann.elec_fan_cooling + ann.elec_fan_heating +
                        ann.elec_fan_vent + ann.elec_fan_other
                    )
                    energy.lighting_kwh = ann.elec_lighting
                    energy.receptacle_kwh = ann.elec_receptacle
                    energy.appliances_kwh = (
                        ann.elec_refrigerator + ann.elec_dishwasher +
                        ann.elec_dryer + ann.elec_washer + ann.elec_cooking
                    )

                self.data.files_parsed.append(str(self._discovery.cse_proposed.path.name))
                logger.debug(f"Parsed CSE detailed (proposed)")
            except Exception as e:
                self.data.parse_warnings.append(f"CSE detailed (proposed) parse error: {e}")
                logger.warning(f"Error parsing CSE detailed (proposed): {e}")

        if self._discovery.cse_standard:
            try:
                detailed = parse_cse_detailed(self._discovery.cse_standard.path)
                energy.detailed_standard = detailed
                self.data.files_parsed.append(str(self._discovery.cse_standard.path.name))
                logger.debug(f"Parsed CSE detailed (standard)")
            except Exception as e:
                self.data.parse_warnings.append(f"CSE detailed (standard) parse error: {e}")
                logger.warning(f"Error parsing CSE detailed (standard): {e}")

    def parse_hvac(self) -> None:
        """Parse HVAC data from secondary CSV and capacity files."""
        if self._discovery is None:
            self.discover_files()

        hvac = self.data.hvac

        # Parse HVAC Secondary
        if self._discovery.hvac_secondary_proposed:
            try:
                secondary = parse_hvac_secondary(self._discovery.hvac_secondary_proposed.path)
                hvac.secondary_proposed = secondary
                hvac.air_systems_proposed = secondary.air_systems
                hvac.zone_systems_proposed = secondary.zone_systems
                hvac.cooling_coils_proposed = secondary.cooling_coils
                hvac.heating_coils_proposed = secondary.heating_coils
                hvac.fans_proposed = secondary.fans

                # Calculate totals
                hvac.total_cooling_capacity_proposed_btuh = sum(
                    c.capacity_btuh for c in secondary.cooling_coils
                    if hasattr(c, 'capacity_btuh') and c.capacity_btuh
                )
                hvac.total_heating_capacity_proposed_btuh = sum(
                    c.capacity_btuh for c in secondary.heating_coils
                    if hasattr(c, 'capacity_btuh') and c.capacity_btuh
                )

                self.data.files_parsed.append(str(self._discovery.hvac_secondary_proposed.path.name))
                logger.debug(f"Parsed HVAC Secondary (proposed)")
            except Exception as e:
                self.data.parse_warnings.append(f"HVAC Secondary (proposed) parse error: {e}")
                logger.warning(f"Error parsing HVAC Secondary (proposed): {e}")

        if self._discovery.hvac_secondary_standard:
            try:
                secondary = parse_hvac_secondary(self._discovery.hvac_secondary_standard.path)
                hvac.secondary_standard = secondary
                hvac.air_systems_standard = secondary.air_systems
                hvac.zone_systems_standard = secondary.zone_systems
                hvac.cooling_coils_standard = secondary.cooling_coils
                hvac.heating_coils_standard = secondary.heating_coils
                hvac.fans_standard = secondary.fans

                hvac.total_cooling_capacity_standard_btuh = sum(
                    c.capacity_btuh for c in secondary.cooling_coils
                    if hasattr(c, 'capacity_btuh') and c.capacity_btuh
                )
                hvac.total_heating_capacity_standard_btuh = sum(
                    c.capacity_btuh for c in secondary.heating_coils
                    if hasattr(c, 'capacity_btuh') and c.capacity_btuh
                )

                self.data.files_parsed.append(str(self._discovery.hvac_secondary_standard.path.name))
                logger.debug(f"Parsed HVAC Secondary (standard)")
            except Exception as e:
                self.data.parse_warnings.append(f"HVAC Secondary (standard) parse error: {e}")
                logger.warning(f"Error parsing HVAC Secondary (standard): {e}")

        # Parse HVAC Capacities (residential)
        if self._discovery.hvac_caps_proposed:
            try:
                caps = parse_hvac_caps(self._discovery.hvac_caps_proposed.path)
                hvac.capacities_proposed = caps

                # Update capacity totals if not already set
                # Use the aggregate totals from the parsed output
                if hvac.total_cooling_capacity_proposed_btuh == 0:
                    hvac.total_cooling_capacity_proposed_btuh = caps.total_cooling_cap_kbtuh * 1000
                if hvac.total_heating_capacity_proposed_btuh == 0:
                    hvac.total_heating_capacity_proposed_btuh = caps.total_heating_cap_kbtuh * 1000

                self.data.files_parsed.append(str(self._discovery.hvac_caps_proposed.path.name))
                logger.debug(f"Parsed HVAC Caps (proposed)")
            except Exception as e:
                self.data.parse_warnings.append(f"HVAC Caps (proposed) parse error: {e}")
                logger.warning(f"Error parsing HVAC Caps (proposed): {e}")

        if self._discovery.hvac_caps_standard:
            try:
                caps = parse_hvac_caps(self._discovery.hvac_caps_standard.path)
                hvac.capacities_standard = caps

                # Use the aggregate totals from the parsed output
                if hvac.total_cooling_capacity_standard_btuh == 0:
                    hvac.total_cooling_capacity_standard_btuh = caps.total_cooling_cap_kbtuh * 1000
                if hvac.total_heating_capacity_standard_btuh == 0:
                    hvac.total_heating_capacity_standard_btuh = caps.total_heating_cap_kbtuh * 1000

                self.data.files_parsed.append(str(self._discovery.hvac_caps_standard.path.name))
                logger.debug(f"Parsed HVAC Caps (standard)")
            except Exception as e:
                self.data.parse_warnings.append(f"HVAC Caps (standard) parse error: {e}")
                logger.warning(f"Error parsing HVAC Caps (standard): {e}")

    def parse_dhw(self) -> None:
        """Parse DHW data from primary CSV and CSE input files."""
        if self._discovery is None:
            self.discover_files()

        dhw = self.data.dhw

        # Parse HVAC Primary (water heaters, boilers)
        if self._discovery.hvac_primary_proposed:
            try:
                primary = parse_hvac_primary(self._discovery.hvac_primary_proposed.path)
                dhw.primary_proposed = primary
                dhw.water_heaters_proposed = primary.water_heaters
                dhw.boilers_proposed = primary.boilers
                dhw.fluid_systems_proposed = primary.fluid_systems
                self.data.files_parsed.append(str(self._discovery.hvac_primary_proposed.path.name))
                logger.debug(f"Parsed HVAC Primary (proposed)")
            except Exception as e:
                self.data.parse_warnings.append(f"HVAC Primary (proposed) parse error: {e}")
                logger.warning(f"Error parsing HVAC Primary (proposed): {e}")

        if self._discovery.hvac_primary_standard:
            try:
                primary = parse_hvac_primary(self._discovery.hvac_primary_standard.path)
                dhw.primary_standard = primary
                dhw.water_heaters_standard = primary.water_heaters
                dhw.boilers_standard = primary.boilers
                dhw.fluid_systems_standard = primary.fluid_systems
                self.data.files_parsed.append(str(self._discovery.hvac_primary_standard.path.name))
                logger.debug(f"Parsed HVAC Primary (standard)")
            except Exception as e:
                self.data.parse_warnings.append(f"HVAC Primary (standard) parse error: {e}")
                logger.warning(f"Error parsing HVAC Primary (standard): {e}")

        # Parse CSE Input (detailed DHW specs)
        if self._discovery.cse_input_proposed:
            try:
                cse_input = parse_cse_input(self._discovery.cse_input_proposed.path)
                dhw.cse_input_proposed = cse_input
                dhw.cse_heaters_proposed = cse_input.dhw_heaters
                dhw.cse_systems_proposed = cse_input.dhw_systems

                dhw.total_heater_count_proposed = cse_input.total_heater_count
                dhw.total_tank_volume_proposed_gal = cse_input.total_tank_volume_gal
                dhw.heat_pump_count_proposed = cse_input.heat_pump_count

                self.data.files_parsed.append(str(self._discovery.cse_input_proposed.path.name))
                logger.debug(f"Parsed CSE Input (proposed)")
            except Exception as e:
                self.data.parse_warnings.append(f"CSE Input (proposed) parse error: {e}")
                logger.warning(f"Error parsing CSE Input (proposed): {e}")

        if self._discovery.cse_input_standard:
            try:
                cse_input = parse_cse_input(self._discovery.cse_input_standard.path)
                dhw.cse_input_standard = cse_input
                dhw.cse_heaters_standard = cse_input.dhw_heaters
                dhw.cse_systems_standard = cse_input.dhw_systems

                dhw.total_heater_count_standard = cse_input.total_heater_count
                dhw.total_tank_volume_standard_gal = cse_input.total_tank_volume_gal
                dhw.heat_pump_count_standard = cse_input.heat_pump_count

                self.data.files_parsed.append(str(self._discovery.cse_input_standard.path.name))
                logger.debug(f"Parsed CSE Input (standard)")
            except Exception as e:
                self.data.parse_warnings.append(f"CSE Input (standard) parse error: {e}")
                logger.warning(f"Error parsing CSE Input (standard): {e}")

    def parse_envelope(self) -> None:
        """Parse envelope data from CSV and XML files."""
        if self._discovery is None:
            self.discover_files()

        env = self.data.envelope

        # Parse Envelope CSV
        if self._discovery.envelope_proposed:
            try:
                envelope = parse_envelope(self._discovery.envelope_proposed.path)
                env.envelope_proposed = envelope
                env.walls_proposed = envelope.exterior_walls
                env.windows_proposed = envelope.windows
                env.roofs_proposed = envelope.exterior_roofs

                # Set building areas
                if envelope.building_areas:
                    areas = envelope.building_areas
                    env.total_wall_area_sf = areas.total_wall_area_sf
                    env.total_window_area_sf = areas.total_window_area_sf
                    env.window_to_wall_ratio = areas.window_to_wall_ratio
                    env.total_roof_area_sf = areas.total_roof_area_sf
                    env.conditioned_floor_area_sf = areas.conditioned_floor_area_sf

                self.data.files_parsed.append(str(self._discovery.envelope_proposed.path.name))
                logger.debug(f"Parsed Envelope (proposed)")
            except Exception as e:
                self.data.parse_warnings.append(f"Envelope (proposed) parse error: {e}")
                logger.warning(f"Error parsing Envelope (proposed): {e}")

        if self._discovery.envelope_standard:
            try:
                envelope = parse_envelope(self._discovery.envelope_standard.path)
                env.envelope_standard = envelope
                env.walls_standard = envelope.exterior_walls
                env.windows_standard = envelope.windows
                env.roofs_standard = envelope.exterior_roofs
                self.data.files_parsed.append(str(self._discovery.envelope_standard.path.name))
                logger.debug(f"Parsed Envelope (standard)")
            except Exception as e:
                self.data.parse_warnings.append(f"Envelope (standard) parse error: {e}")
                logger.warning(f"Error parsing Envelope (standard): {e}")

        # Parse Analysis Results XML (supplementary envelope data)
        if self._discovery.analysis_results:
            try:
                analysis = parse_analysis_results(self._discovery.analysis_results.path)
                env.analysis_results = analysis
                self.data.files_parsed.append(str(self._discovery.analysis_results.path.name))
                logger.debug(f"Parsed AnalysisResults XML")
            except Exception as e:
                self.data.parse_warnings.append(f"AnalysisResults parse error: {e}")
                logger.warning(f"Error parsing AnalysisResults: {e}")


def aggregate_lcca_data(project_dir: str | Path) -> LCCAInputData:
    """
    Convenience function to aggregate all LCCA data from a project directory.

    Args:
        project_dir: Path to project directory

    Returns:
        LCCAInputData with all aggregated simulation data
    """
    aggregator = LCCADataAggregator(project_dir)
    return aggregator.parse_all()


def format_lcca_summary(data: LCCAInputData) -> str:
    """
    Format a human-readable summary of aggregated LCCA data.

    Args:
        data: LCCAInputData to summarize

    Returns:
        Formatted string summary
    """
    lines = [
        f"LCCA Data Summary: {data.project_name}",
        "=" * 60,
        "",
        "Project Information:",
        "-" * 40,
    ]

    if data.project_info.project_name:
        lines.extend([
            f"  Name: {data.project_info.project_name}",
            f"  Location: {data.project_info.city}, CZ{data.project_info.climate_zone}",
            f"  Type: {data.project_info.occupancy_type}",
            f"  Area: {data.project_info.conditioned_floor_area_sf:,.0f} SF",
        ])
        if data.project_info.dwelling_units:
            lines.append(f"  Dwelling Units: {data.project_info.dwelling_units}")
    else:
        lines.append("  (No project info available)")

    lines.extend([
        "",
        "Compliance:",
        "-" * 40,
    ])

    if data.compliance.compliance_result:
        status = "PASS" if data.compliance.passes_compliance else "FAIL"
        lines.extend([
            f"  Status: {status}",
            f"  Efficiency Margin: {data.compliance.margin_efficiency:.2f} kTDV/ft2",
            f"  Total Margin: {data.compliance.margin_total:.2f} kTDV/ft2",
        ])
    else:
        lines.append("  (No compliance data available)")

    lines.extend([
        "",
        "Energy Consumption:",
        "-" * 40,
    ])

    if data.energy.proposed_elec_kwh > 0 or data.energy.proposed_gas_therms > 0:
        lines.extend([
            f"  Proposed:",
            f"    Electricity: {data.energy.proposed_elec_kwh:,.0f} kWh",
            f"    Natural Gas: {data.energy.proposed_gas_therms:,.0f} therms",
        ])
        if data.energy.pv_generation_kwh > 0:
            lines.append(f"    PV Generation: {data.energy.pv_generation_kwh:,.0f} kWh")

        if data.has_comparison_data:
            lines.extend([
                f"  Standard:",
                f"    Electricity: {data.energy.standard_elec_kwh:,.0f} kWh",
                f"    Natural Gas: {data.energy.standard_gas_therms:,.0f} therms",
            ])
    else:
        lines.append("  (No energy data available)")

    if data.energy.detailed_proposed:
        lines.extend([
            "",
            "End-Use Breakdown (Proposed):",
            "-" * 40,
            f"  Cooling: {data.energy.cooling_kwh:,.0f} kWh",
            f"  Heating: {data.energy.heating_kwh:,.0f} kWh",
            f"  DHW: {data.energy.dhw_kwh:,.0f} kWh",
            f"  Fans: {data.energy.fans_kwh:,.0f} kWh",
            f"  Lighting: {data.energy.lighting_kwh:,.0f} kWh",
            f"  Receptacle: {data.energy.receptacle_kwh:,.0f} kWh",
            f"  Appliances: {data.energy.appliances_kwh:,.0f} kWh",
        ])

    if data.has_hvac_data:
        lines.extend([
            "",
            "HVAC Equipment:",
            "-" * 40,
            f"  Air Systems: {len(data.hvac.air_systems_proposed)}",
            f"  Zone Systems: {len(data.hvac.zone_systems_proposed)}",
            f"  Cooling Capacity: {data.hvac.total_cooling_capacity_proposed_btuh/1000:,.0f} kBtu/h",
            f"  Heating Capacity: {data.hvac.total_heating_capacity_proposed_btuh/1000:,.0f} kBtu/h",
        ])

    if data.has_dhw_data:
        lines.extend([
            "",
            "DHW Equipment:",
            "-" * 40,
            f"  Water Heaters: {data.dhw.total_heater_count_proposed}",
            f"  Heat Pump Units: {data.dhw.heat_pump_count_proposed}",
            f"  Tank Volume: {data.dhw.total_tank_volume_proposed_gal:,.0f} gal",
        ])

    if data.has_envelope_data:
        lines.extend([
            "",
            "Envelope:",
            "-" * 40,
            f"  Wall Area: {data.envelope.total_wall_area_sf:,.0f} SF",
            f"  Window Area: {data.envelope.total_window_area_sf:,.0f} SF",
            f"  WWR: {data.envelope.window_to_wall_ratio:.1%}",
            f"  Roof Area: {data.envelope.total_roof_area_sf:,.0f} SF",
        ])

    lines.extend([
        "",
        "Parsing Summary:",
        "-" * 40,
        f"  Files Parsed: {len(data.files_parsed)}",
        f"  Errors: {len(data.parse_errors)}",
        f"  Warnings: {len(data.parse_warnings)}",
    ])

    if data.parse_errors:
        lines.extend([
            "",
            "Parse Errors:",
        ])
        for error in data.parse_errors:
            lines.append(f"  - {error}")

    return "\n".join(lines)
