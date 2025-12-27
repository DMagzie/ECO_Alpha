"""
Parser for CBECC NRCCPRF.xml files (Compliance Performance Report).

Extracts project summary information and compliance results:
- Project name, address, climate zone
- Building type and occupancy
- Floor areas and dwelling unit counts
- Compliance margin and pass/fail status
- TDV energy by end use
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, Dict
import xml.etree.ElementTree as ET
import logging
import re

logger = logging.getLogger(__name__)


@dataclass
class NRCCPRFProjectInfo:
    """Project summary from NRCCPRF.xml Section_Info."""
    project_name: str = ''
    run_description: str = ''
    street_address: str = ''
    city: str = ''
    zipcode: str = ''
    climate_zone: int = 0
    building_azimuth: float = 0.0
    occupancy_type: str = ''  # HighRiseResidential, Office, etc.
    weather_file: str = ''
    project_scope: str = ''  # NewComplete, ExistingAddition, etc.
    dwelling_units: int = 0
    hotel_guest_rooms: int = 0
    above_grade_stories: int = 0
    conditioned_floor_area_sf: float = 0.0
    unconditioned_floor_area_sf: float = 0.0
    residential_floor_area_sf: float = 0.0
    nonres_floor_area_sf: float = 0.0
    building_volume_cf: float = 0.0
    site_fuel_type: str = ''  # NaturalGas, Electricity
    standards_version: str = ''  # Compliance2022, Compliance2025
    software_version: str = ''
    run_datetime: str = ''


@dataclass
class NRCCPRFComplianceResult:
    """Compliance result from NRCCPRF.xml Section_C22Result1."""
    compliance_result: str = ''  # PerfComplies, PerfDoesNotComply

    # Efficiency TDV (kTDV/ft2)
    standard_efficiency: float = 0.0
    proposed_efficiency: float = 0.0
    margin_efficiency: float = 0.0
    pass_fail_efficiency: str = ''  # Pass, Fail

    # Total TDV (including PV/Battery)
    standard_total: float = 0.0
    proposed_total: float = 0.0
    margin_total: float = 0.0
    pass_fail_total: str = ''

    # Source energy
    standard_source: float = 0.0
    proposed_source: float = 0.0
    margin_source: float = 0.0
    pass_fail_source: str = ''

    # Overall validity
    compliance_validity: str = ''

    @property
    def passes_compliance(self) -> bool:
        """Check if building passes compliance."""
        return self.compliance_result == 'PerfComplies'

    @property
    def efficiency_percent_improvement(self) -> float:
        """Calculate percent improvement in efficiency."""
        if self.standard_efficiency > 0:
            return (self.margin_efficiency / self.standard_efficiency) * 100
        return 0.0


@dataclass
class NRCCPRFEndUseBreakdown:
    """TDV energy breakdown by end use from Section_C22Result2."""
    # Standard design (kTDV/ft2)
    heating_standard: float = 0.0
    cooling_standard: float = 0.0
    fans_standard: float = 0.0
    pumps_standard: float = 0.0
    dhw_standard: float = 0.0
    lighting_standard: float = 0.0
    pv_standard: float = 0.0
    battery_standard: float = 0.0
    total_standard: float = 0.0

    # Proposed design (kTDV/ft2)
    heating_proposed: float = 0.0
    cooling_proposed: float = 0.0
    fans_proposed: float = 0.0
    pumps_proposed: float = 0.0
    dhw_proposed: float = 0.0
    lighting_proposed: float = 0.0
    pv_proposed: float = 0.0
    battery_proposed: float = 0.0
    total_proposed: float = 0.0

    # Margins (kTDV/ft2)
    heating_margin: float = 0.0
    cooling_margin: float = 0.0
    fans_margin: float = 0.0
    pumps_margin: float = 0.0
    dhw_margin: float = 0.0
    lighting_margin: float = 0.0
    pv_margin: float = 0.0
    battery_margin: float = 0.0
    total_margin: float = 0.0


@dataclass
class NRCCPRFOutput:
    """Complete output from NRCCPRF.xml parsing."""
    filepath: str = ''
    project: NRCCPRFProjectInfo = field(default_factory=NRCCPRFProjectInfo)
    compliance: NRCCPRFComplianceResult = field(default_factory=NRCCPRFComplianceResult)
    enduse_breakdown: NRCCPRFEndUseBreakdown = field(default_factory=NRCCPRFEndUseBreakdown)


class NRCCPRFParser:
    """Parser for CBECC NRCCPRF.xml files."""

    # Namespace prefixes used in NRCCPRF files
    NAMESPACES = {
        'comp': 'http://www.lmonte.com/besm/comp',
    }

    def __init__(self):
        self.output = NRCCPRFOutput()
        self.parse_errors: list = []
        self.parse_warnings: list = []

    def parse_file(self, filepath: Path) -> NRCCPRFOutput:
        """
        Parse NRCCPRF.xml and return structured output.

        Args:
            filepath: Path to NRCCPRF.xml file

        Returns:
            NRCCPRFOutput with project info and compliance results
        """
        filepath = Path(filepath)
        if not filepath.exists():
            raise FileNotFoundError(f"File not found: {filepath}")

        self.output = NRCCPRFOutput(filepath=str(filepath))
        self.parse_errors = []
        self.parse_warnings = []

        try:
            tree = ET.parse(filepath)
            root = tree.getroot()

            self._parse_project_info(root)
            self._parse_compliance_result(root)
            self._parse_enduse_breakdown(root)

        except ET.ParseError as e:
            self.parse_errors.append(f"XML parse error: {e}")
            logger.error(f"Error parsing NRCCPRF {filepath}: {e}")

        return self.output

    def _parse_project_info(self, root: ET.Element) -> None:
        """Parse Section_Info for project metadata."""
        info = self.output.project

        # Find Section_Info element (search any namespace)
        section = self._find_section(root, 'Section_Info')
        if section is None:
            return

        # Extract values using suffix matching (handles any namespace prefix)
        info.project_name = self._get_text(section, 'Info01_ProjectName', '')
        info.run_description = self._get_text(section, 'Info02_RunDescription', '')
        info.street_address = self._get_text(section, 'Info03_ProjectStreetAddress', '')
        info.city = self._get_text(section, 'Info04_ProjectCity', '')
        info.standards_version = self._get_text(section, 'Info05_Title24StandardsVersion', '')
        info.zipcode = self._get_text(section, 'Info06_ProjectZipcode', '')
        info.software_version = self._get_text(section, 'Info07_ComplianceSoftwareVersion', '')
        info.climate_zone = self._get_int(section, 'Info08_ClimateZone', 0)
        info.building_azimuth = self._get_float(section, 'Info09_Azimuth', 0.0)
        info.occupancy_type = self._get_text(section, 'Info10_TopLevelOccupancy', '')
        info.weather_file = self._get_text(section, 'Info11_WeatherFile', '')
        info.project_scope = self._get_text(section, 'Info12_ProjectScopeNR', '')
        info.dwelling_units = self._get_int(section, 'Info13_DwellingUnitsCount', 0)
        info.conditioned_floor_area_sf = self._get_float(section, 'Info14_TotalConditionedFloorArea', 0.0)
        info.hotel_guest_rooms = self._get_int(section, 'Info15_HotelMotelGuestRoomCount', 0)
        info.unconditioned_floor_area_sf = self._get_float(section, 'Info16_TotalUnconditionedFloorArea', 0.0)
        info.site_fuel_type = self._get_text(section, 'Info17_SiteFuelType', '')
        info.nonres_floor_area_sf = self._get_float(section, 'Info18_NonResBuildingTotalConditionedFloorArea', 0.0)
        info.above_grade_stories = self._get_int(section, 'Info19_AboveGradeStoryCount', 0)
        info.residential_floor_area_sf = self._get_float(section, 'Info20_ResidentialBuildingTotalConditionedFloorArea', 0.0)
        info.building_volume_cf = self._get_float(section, 'Info21_BuildingTotalVolume', 0.0)

        # Get run datetime from Header
        header = self._find_section(root, 'Header')
        if header is not None:
            info.run_datetime = self._get_text(header, 'header02_RunDateTime', '')

    def _parse_compliance_result(self, root: ET.Element) -> None:
        """Parse Section_C22Result1 for compliance results."""
        result = self.output.compliance

        section = self._find_section(root, 'Section_C22Result1')
        if section is None:
            return

        result.compliance_result = self._get_text(section, 'C22Result1_PerformanceComplianceResult', '')

        # Efficiency
        result.standard_efficiency = self._get_float(section, 'C22Result1_StandardDesignEfficiency', 0.0)
        result.proposed_efficiency = self._get_float(section, 'C22Result1_ProposedDesignEfficiency', 0.0)
        result.margin_efficiency = self._get_float(section, 'C22Result1_ComplianceMarginEfficiency', 0.0)
        result.pass_fail_efficiency = self._get_text(section, 'C22Result1_PassFailEfficiency', '')

        # Total
        result.standard_total = self._get_float(section, 'C22Result1_StandardDesignTotal', 0.0)
        result.proposed_total = self._get_float(section, 'C22Result1_ProposedDesignTotal', 0.0)
        result.margin_total = self._get_float(section, 'C22Result1_ComplianceMarginTotal', 0.0)
        result.pass_fail_total = self._get_text(section, 'C22Result1_PassFailTotal', '')

        # Source
        result.standard_source = self._get_float(section, 'C22Result1_StandardDesignSource', 0.0)
        result.proposed_source = self._get_float(section, 'C22Result1_ProposedDesignSource', 0.0)
        result.margin_source = self._get_float(section, 'C22Result1_ComplianceMarginSource', 0.0)
        result.pass_fail_source = self._get_text(section, 'C22Result1_PassFailSource', '')

        result.compliance_validity = self._get_text(section, 'C22Result1_PerformanceComplianceValidity', '')

    def _parse_enduse_breakdown(self, root: ET.Element) -> None:
        """Parse Section_C22Result2 for end-use breakdown."""
        breakdown = self.output.enduse_breakdown

        section = self._find_section(root, 'Section_C22Result2')
        if section is None:
            return

        # Standard design
        breakdown.heating_standard = self._get_float(section, 'C22Result2Heat1_EnergyUseStandardDesign', 0.0)
        breakdown.cooling_standard = self._get_float(section, 'C22Result2Cool1_EnergyUseStandardDesign', 0.0)
        breakdown.fans_standard = self._get_float(section, 'C22Result2Fan1_EnergyUseStandardDesign', 0.0)
        breakdown.pumps_standard = self._get_float(section, 'C22Result2Pump1_EnergyUseStandardDesign', 0.0)
        breakdown.dhw_standard = self._get_float(section, 'C22Result2DHW1_EnergyUseStandardDesign', 0.0)
        breakdown.lighting_standard = self._get_float(section, 'C22Result2Ltg1_EnergyUseStandardDesign', 0.0)
        breakdown.pv_standard = self._get_float(section, 'C22Result2PV1_EnergyUseStandardDesign', 0.0)
        breakdown.battery_standard = self._get_float(section, 'C22Result2Bat1_EnergyUseStandardDesign', 0.0)
        breakdown.total_standard = self._get_float(section, 'C22Result2TotalComp1_EnergyUseStandardDesign', 0.0)

        # Proposed design
        breakdown.heating_proposed = self._get_float(section, 'C22Result2Heat2_EnergyUseProposedDesign', 0.0)
        breakdown.cooling_proposed = self._get_float(section, 'C22Result2Cool2_EnergyUseProposedDesign', 0.0)
        breakdown.fans_proposed = self._get_float(section, 'C22Result2Fan2_EnergyUseProposedDesign', 0.0)
        breakdown.pumps_proposed = self._get_float(section, 'C22Result2Pump2_EnergyUseProposedDesign', 0.0)
        breakdown.dhw_proposed = self._get_float(section, 'C22Result2DHW2_EnergyUseProposedDesign', 0.0)
        breakdown.lighting_proposed = self._get_float(section, 'C22Result2Ltg2_EnergyUseProposedDesign', 0.0)
        breakdown.pv_proposed = self._get_float(section, 'C22Result2PV2_EnergyUseProposedPhotovoltaic', 0.0)
        breakdown.battery_proposed = self._get_float(section, 'C22Result2Bat2_EnergyUseProposedBattery', 0.0)
        breakdown.total_proposed = self._get_float(section, 'C22Result2TotalComp2_EnergyUseProposedDesign', 0.0)

        # Margins
        breakdown.heating_margin = self._get_float(section, 'C22Result2Heat3_EnergyUseMargin', 0.0)
        breakdown.cooling_margin = self._get_float(section, 'C22Result2Cool3_EnergyUseMargin', 0.0)
        breakdown.fans_margin = self._get_float(section, 'C22Result2Fan3_EnergyUseMargin', 0.0)
        breakdown.pumps_margin = self._get_float(section, 'C22Result2Pump3_EnergyUseMargin', 0.0)
        breakdown.dhw_margin = self._get_float(section, 'C22Result2DHW3_EnergyUseMargin', 0.0)
        breakdown.lighting_margin = self._get_float(section, 'C22Result2Ltg3_EnergyUseMargin', 0.0)
        breakdown.pv_margin = self._get_float(section, 'C22Result2PV3_EnergyUseMargin', 0.0)
        breakdown.battery_margin = self._get_float(section, 'C22Result2Bat3_EnergyUseMargin', 0.0)
        breakdown.total_margin = self._get_float(section, 'C22Result2TotalComp3a_EnergyUseMargin', 0.0)

    def _find_section(self, root: ET.Element, section_name: str) -> Optional[ET.Element]:
        """Find section element by name (handles namespaces)."""
        # Try direct search
        for elem in root.iter():
            tag = elem.tag.split('}')[-1] if '}' in elem.tag else elem.tag
            if tag == section_name:
                return elem
        return None

    def _get_text(self, parent: ET.Element, tag_suffix: str, default: str = '') -> str:
        """Get text from child element matching tag suffix."""
        for elem in parent.iter():
            tag = elem.tag.split('}')[-1] if '}' in elem.tag else elem.tag
            if tag.endswith(tag_suffix) or tag == tag_suffix:
                return elem.text.strip() if elem.text else default
        return default

    def _get_float(self, parent: ET.Element, tag_suffix: str, default: float = 0.0) -> float:
        """Get float from child element matching tag suffix."""
        text = self._get_text(parent, tag_suffix, '')
        if text:
            try:
                return float(text)
            except ValueError:
                pass
        return default

    def _get_int(self, parent: ET.Element, tag_suffix: str, default: int = 0) -> int:
        """Get int from child element matching tag suffix."""
        text = self._get_text(parent, tag_suffix, '')
        if text:
            try:
                return int(float(text))
            except ValueError:
                pass
        return default


def parse_nrccprf(filepath: Path) -> NRCCPRFOutput:
    """
    Parse an NRCCPRF.xml file.

    Args:
        filepath: Path to the NRCCPRF.xml file

    Returns:
        NRCCPRFOutput with project info and compliance results
    """
    parser = NRCCPRFParser()
    return parser.parse_file(filepath)
