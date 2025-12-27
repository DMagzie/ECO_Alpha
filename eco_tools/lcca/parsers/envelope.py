"""
Parser for CBECC Envelope.csv output files.

Extracts building envelope specifications including:
- Building areas (wall, window, roof, floor)
- Window-to-wall ratios
- Exterior walls with construction types and U-factors
- Windows with U-factor and SHGC
- Exterior roofs with solar reflectance
- Underground floors with F-factors
- Construction assemblies and material layers
- Construction materials with R-values
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, List, Dict, Any
import logging

from .cbecc_csv_base import CebeccCsvParser, CebeccSection

logger = logging.getLogger(__name__)


@dataclass
class BuildingAreas:
    """Building area summary."""
    conditioned_floor_area_sf: float = 0
    total_floor_area_sf: float = 0
    num_stories_total: int = 0
    num_stories_above_grade: int = 0
    num_thermal_zones: int = 0
    climate_zone: str = ''

    # Wall areas
    total_wall_area_sf: float = 0
    wall_area_north_sf: float = 0
    wall_area_east_sf: float = 0
    wall_area_south_sf: float = 0
    wall_area_west_sf: float = 0

    # Window areas
    total_window_area_sf: float = 0
    window_area_north_sf: float = 0
    window_area_east_sf: float = 0
    window_area_south_sf: float = 0
    window_area_west_sf: float = 0

    # Ratios
    window_to_wall_ratio: float = 0
    wwr_north: float = 0
    wwr_east: float = 0
    wwr_south: float = 0
    wwr_west: float = 0

    # Roof
    total_roof_area_sf: float = 0
    skylight_to_roof_ratio: float = 0


@dataclass
class ExteriorWall:
    """Exterior wall specification."""
    name: str
    status: str  # New, Existing, Altered
    space_name: str
    occupancy_class: str
    conditioning_status: str  # DirectlyConditioned, IndirectlyConditioned, Plenum, Unconditioned
    area_sf: float
    azimuth_deg: Optional[float] = None
    construction_name: str = ''
    construction_type: str = ''  # MetalFrameWall, WoodFrameWall, MassWall, etc.
    u_factor: Optional[float] = None
    window_area_sf: float = 0


@dataclass
class Window:
    """Window/fenestration specification."""
    name: str
    status: str
    occupancy_class: str
    conditioning_status: str
    exterior_wall_name: str
    area_sf: float
    azimuth_deg: float
    product_type: str  # FixedWindow, OperableWindow, CurtainWall
    certification_method: str  # NFRCRated, DefaultPerformance
    construction_name: str
    frame_type: Optional[str] = None
    glazing_type: Optional[str] = None
    u_factor: float = 0
    shgc: float = 0
    visual_transmittance: float = 0


@dataclass
class ExteriorRoof:
    """Exterior roof specification."""
    name: str
    status: str
    space_name: str
    occupancy_class: str
    conditioning_status: str
    area_sf: float
    tilt_deg: float = 0
    slope_category: str = 'Low'  # Low, Medium, Steep
    construction_name: str = ''
    construction_type: str = ''  # WoodFramingAndOtherRoof, MetalBuildingRoof, etc.
    u_factor: Optional[float] = None
    aged_thermal_emittance: float = 0.85
    aged_solar_reflectance: float = 0


@dataclass
class UndergroundFloor:
    """Underground/slab floor specification."""
    name: str
    status: str
    space_name: str
    occupancy_class: str
    conditioning_status: str
    slab_type: str  # Heated, Unheated
    area_sf: float
    exposed_perimeter_ft: float
    construction_name: str = ''
    insulation_orientation: Optional[str] = None
    f_factor: Optional[float] = None


@dataclass
class ConstructionAssembly:
    """Construction assembly with material layers."""
    name: str
    surface_type: str  # ExteriorWall, Roof, InteriorWall, InteriorFloor, UndergroundFloor
    material_layers: List[str] = field(default_factory=list)


@dataclass
class ConstructionMaterial:
    """Construction material with properties."""
    name: str
    code_item: str
    material_type: str  # Insulation Board, Masonry Units, Plastering Materials, etc.
    r_value: float = 0
    thickness_in: float = 0
    frame_type: Optional[str] = None
    frame_configuration: Optional[str] = None


@dataclass
class EnvelopeOutput:
    """Complete parsed output from Envelope.csv."""
    building_areas: BuildingAreas = field(default_factory=BuildingAreas)
    exterior_walls: List[ExteriorWall] = field(default_factory=list)
    windows: List[Window] = field(default_factory=list)
    exterior_roofs: List[ExteriorRoof] = field(default_factory=list)
    underground_floors: List[UndergroundFloor] = field(default_factory=list)
    construction_assemblies: List[ConstructionAssembly] = field(default_factory=list)
    construction_materials: List[ConstructionMaterial] = field(default_factory=list)

    # XML-supplemented values (set by supplement_envelope_with_xml)
    _xml_roof_solar_reflectance: Optional[float] = field(default=None, repr=False)
    _xml_window_u_factor: Optional[float] = field(default=None, repr=False)
    _xml_window_shgc: Optional[float] = field(default=None, repr=False)

    # Summary properties
    @property
    def total_wall_r_value(self) -> Optional[float]:
        """Get effective R-value for walls from construction materials."""
        for assembly in self.construction_assemblies:
            if assembly.surface_type == 'ExteriorWall':
                return self._get_assembly_r_value(assembly)
        return None

    @property
    def total_roof_r_value(self) -> Optional[float]:
        """Get effective R-value for roof from construction materials."""
        for assembly in self.construction_assemblies:
            if assembly.surface_type == 'Roof':
                return self._get_assembly_r_value(assembly)
        return None

    @property
    def average_window_u_factor(self) -> Optional[float]:
        """Area-weighted average window U-factor (CSV or XML fallback)."""
        # Try CSV data first
        if self.windows:
            total_area = sum(w.area_sf for w in self.windows if w.area_sf)
            if total_area > 0:
                weighted = sum(w.u_factor * w.area_sf for w in self.windows if w.u_factor and w.area_sf)
                if weighted > 0:
                    return weighted / total_area
        # Fall back to XML data
        return self._xml_window_u_factor

    @property
    def average_window_shgc(self) -> Optional[float]:
        """Area-weighted average window SHGC (CSV or XML fallback)."""
        # Try CSV data first
        if self.windows:
            total_area = sum(w.area_sf for w in self.windows if w.area_sf)
            if total_area > 0:
                weighted = sum(w.shgc * w.area_sf for w in self.windows if w.shgc and w.area_sf)
                if weighted > 0:
                    return weighted / total_area
        # Fall back to XML data
        return self._xml_window_shgc

    @property
    def average_roof_reflectance(self) -> Optional[float]:
        """Area-weighted average roof solar reflectance (CSV or XML fallback)."""
        # Try CSV data first
        if self.exterior_roofs:
            total_area = sum(r.area_sf for r in self.exterior_roofs if r.area_sf)
            if total_area > 0:
                weighted = sum(r.aged_solar_reflectance * r.area_sf for r in self.exterior_roofs
                               if r.aged_solar_reflectance and r.area_sf)
                if weighted > 0:
                    return weighted / total_area
        # Fall back to XML data
        return self._xml_roof_solar_reflectance

    def _get_assembly_r_value(self, assembly: ConstructionAssembly) -> float:
        """Calculate total R-value for an assembly from its materials."""
        total_r = 0
        for layer_name in assembly.material_layers:
            for mat in self.construction_materials:
                if mat.name == layer_name:
                    total_r += mat.r_value
                    break
        return total_r

    def get_material_by_name(self, name: str) -> Optional[ConstructionMaterial]:
        """Find a material by name."""
        for mat in self.construction_materials:
            if mat.name == name:
                return mat
        return None


class EnvelopeParser(CebeccCsvParser):
    """Parser for Envelope.csv files."""

    SECTION_ALIASES = {
        'general information': 'General Information',
        'generalinformation': 'General Information',
        'building wall area': 'Building Wall Area',
        'buildingwallarea': 'Building Wall Area',
        'building window area': 'Building Window Area',
        'buildingwindowarea': 'Building Window Area',
        'window to wall ratio': 'Window to Wall Ratio',
        'windowtowallratio': 'Window to Wall Ratio',
        'exterior roofs': 'Exterior Roofs',
        'exterior roof': 'Exterior Roofs',
        'exterior wall': 'Exterior Wall',
        'exterior walls': 'Exterior Wall',
        'window': 'Window',
        'windows': 'Window',
        'underground floor': 'Underground Floor',
        'underground floors': 'Underground Floor',
        'interior wall': 'Interior Wall',
        'interior floor': 'Interior Floor',
        'construction assembly': 'Construction Assembly',
        'constructionassembly': 'Construction Assembly',
        'construction materials': 'Construction Materials',
        'constructionmaterials': 'Construction Materials',
    }

    def parse_file(self, filepath: Path) -> EnvelopeOutput:
        """
        Parse Envelope.csv and return structured output.

        Args:
            filepath: Path to Envelope.csv

        Returns:
            EnvelopeOutput with all parsed components
        """
        # Parse sections using base class
        sections = super().parse_file(filepath)

        # Create output
        output = EnvelopeOutput()

        # Parse building areas from metadata sections
        output.building_areas = self._parse_building_areas(sections)

        # Parse component sections
        output.exterior_walls = self._parse_exterior_walls(sections)
        output.windows = self._parse_windows(sections)
        output.exterior_roofs = self._parse_exterior_roofs(sections)
        output.underground_floors = self._parse_underground_floors(sections)
        output.construction_assemblies = self._parse_construction_assemblies(sections)
        output.construction_materials = self._parse_construction_materials(sections)

        return output

    def _get_section(self, sections: Dict[str, CebeccSection], name: str) -> Optional[CebeccSection]:
        """Get a section by name, handling aliases."""
        if name in sections:
            return sections[name]

        name_lower = name.lower()
        if name_lower in self.SECTION_ALIASES:
            canonical = self.SECTION_ALIASES[name_lower]
            if canonical in sections:
                return sections[canonical]

        for section_name, section in sections.items():
            if section_name.lower() == name_lower:
                return section

        return None

    def _parse_building_areas(self, sections: Dict[str, CebeccSection]) -> BuildingAreas:
        """Parse building area information from multiple sections."""
        areas = BuildingAreas()

        # Try to find general information
        for section_name, section in sections.items():
            if 'general' in section_name.lower():
                # Parse key-value pairs from general info
                for row in section.data:
                    self._extract_general_info(row, areas)

        # Parse wall areas
        wall_section = self._get_section(sections, 'Building Wall Area')
        if wall_section and wall_section.data:
            row = wall_section.data[0]
            areas.total_wall_area_sf = self._get_float(row, 'Total ExtWall', 0)
            areas.wall_area_north_sf = self._get_float(row, 'N ExtWall', 0)
            areas.wall_area_east_sf = self._get_float(row, 'E ExtWall', 0)
            areas.wall_area_south_sf = self._get_float(row, 'S ExtWall', 0)
            areas.wall_area_west_sf = self._get_float(row, 'W ExtWall', 0)

        # Parse window areas - specifically get "Building Window Area" (not "New" or "Existing" variants)
        window_section = self._get_section(sections, 'Building Window Area')
        if window_section and window_section.data:
            row = window_section.data[0]
            areas.total_window_area_sf = self._get_float(row, 'Total Window Area', 0)
            areas.window_area_north_sf = self._get_float(row, 'North Window', 0)
            areas.window_area_east_sf = self._get_float(row, 'E Window', 0)
            areas.window_area_south_sf = self._get_float(row, 'S Window', 0)
            areas.window_area_west_sf = self._get_float(row, 'W Window', 0)

        # Parse WWR - specifically get "Window to Wall Ratio" (not "New" or "Existing" variants)
        wwr_section = self._get_section(sections, 'Window to Wall Ratio')
        if wwr_section and wwr_section.data:
            row = wwr_section.data[0]
            areas.window_to_wall_ratio = self._get_float(row, 'Bldg. WWR', 0)
            areas.wwr_north = self._get_float(row, 'North WWR', 0)
            areas.wwr_east = self._get_float(row, 'East WWR', 0)
            areas.wwr_south = self._get_float(row, 'South WWR', 0)
            areas.wwr_west = self._get_float(row, 'West WWR', 0)

        return areas

    def _extract_general_info(self, row: Dict[str, Any], areas: BuildingAreas) -> None:
        """Extract general info from a row into BuildingAreas."""
        # Look for climate zone
        for key, val in row.items():
            if val and 'climatezone' in str(key).lower().replace(' ', ''):
                areas.climate_zone = str(val)
            elif val and 'zone' in str(key).lower() and isinstance(val, str) and val.startswith('ClimateZone'):
                areas.climate_zone = val

        # Look for floor area
        if 'Total Floor Area' in row:
            areas.total_floor_area_sf = self._get_float(row, 'Total Floor Area', 0)
        if 'Conditioned Floor Area' in row:
            areas.conditioned_floor_area_sf = self._get_float(row, 'Conditioned Floor Area', 0)

        # Stories
        if 'No. of Stories' in str(row) or 'Total' in row:
            areas.num_stories_total = self._get_int(row, 'Total', 0)

        # Thermal zones
        if 'No. of Thermal Zones' in str(row):
            areas.num_thermal_zones = self._get_int(row, 'No. of Thermal Zones', 0)

    def _parse_exterior_walls(self, sections: Dict[str, CebeccSection]) -> List[ExteriorWall]:
        """Parse Exterior Wall section."""
        section = self._get_section(sections, 'Exterior Wall')
        if not section:
            return []

        walls = []
        for row in section.data:
            try:
                wall = ExteriorWall(
                    name=self._get_str(row, 'Name', ''),
                    status=self._get_str(row, 'Status', 'New'),
                    space_name=self._get_str(row, 'Name', ''),  # Space Name column
                    occupancy_class=self._get_str(row, 'Occupancy Classification', ''),
                    conditioning_status=self._get_str(row, 'Conditioning Status', ''),
                    area_sf=self._get_float(row, 'Area', 0),
                    azimuth_deg=self._get_float(row, 'Azimuth'),
                    construction_name=self._get_str(row, 'Cons Name', ''),
                    construction_type=self._get_str(row, 'Construction Type', ''),
                    u_factor=self._get_float(row, 'U Factor'),
                    window_area_sf=self._get_float(row, 'Window Area', 0),
                )
                if wall.name:
                    walls.append(wall)
            except Exception as e:
                logger.warning(f"Error parsing exterior wall row: {e}")

        return walls

    def _parse_windows(self, sections: Dict[str, CebeccSection]) -> List[Window]:
        """Parse Window section."""
        section = self._get_section(sections, 'Window')
        if not section:
            return []

        windows = []
        for row in section.data:
            try:
                window = Window(
                    name=self._get_str(row, 'Name', ''),
                    status=self._get_str(row, 'Status', 'New'),
                    occupancy_class=self._get_str(row, 'Occupancy Classification', ''),
                    conditioning_status=self._get_str(row, 'Conditioning Status', ''),
                    exterior_wall_name=self._get_str(row, 'Exterior Wall', ''),
                    area_sf=self._get_float(row, 'Area', 0),
                    azimuth_deg=self._get_float(row, 'Azimuth', 0),
                    product_type=self._get_str(row, 'Product Type', 'FixedWindow'),
                    certification_method=self._get_str(row, 'Cert Method', ''),
                    construction_name=self._get_str(row, 'Cons Name', ''),
                    frame_type=self._get_str(row, 'Frame Type'),
                    glazing_type=self._get_str(row, 'Glazing Type'),
                    u_factor=self._get_float(row, 'U Factor', 0),
                    shgc=self._get_float(row, 'SHGC', 0),
                    visual_transmittance=self._get_float(row, 'Visual Transmittance', 0),
                )
                if window.name:
                    windows.append(window)
            except Exception as e:
                logger.warning(f"Error parsing window row: {e}")

        return windows

    def _parse_exterior_roofs(self, sections: Dict[str, CebeccSection]) -> List[ExteriorRoof]:
        """Parse Exterior Roofs section."""
        section = self._get_section(sections, 'Exterior Roofs')
        if not section:
            return []

        roofs = []
        for row in section.data:
            try:
                roof = ExteriorRoof(
                    name=self._get_str(row, 'Name', ''),
                    status=self._get_str(row, 'Status', 'New'),
                    space_name=self._get_str(row, 'Name', ''),  # Second Name column is space
                    occupancy_class=self._get_str(row, 'Occupancy Classification', ''),
                    conditioning_status=self._get_str(row, 'Conditioning Status', ''),
                    area_sf=self._get_float(row, 'Area', 0),
                    tilt_deg=self._get_float(row, 'Tilt', 0),
                    slope_category=self._get_str(row, 'Slope Category', 'Low'),
                    construction_name=self._get_str(row, 'Cons Name', ''),
                    construction_type=self._get_str(row, 'Construction Type', ''),
                    u_factor=self._get_float(row, 'U-Factor'),
                    aged_thermal_emittance=self._get_float(row, 'Aged Thermal Emittance', 0.85),
                    aged_solar_reflectance=self._get_float(row, 'Aged Solar Reflectance', 0),
                )
                if roof.name:
                    roofs.append(roof)
            except Exception as e:
                logger.warning(f"Error parsing exterior roof row: {e}")

        return roofs

    def _parse_underground_floors(self, sections: Dict[str, CebeccSection]) -> List[UndergroundFloor]:
        """Parse Underground Floor section."""
        section = self._get_section(sections, 'Underground Floor')
        if not section:
            return []

        floors = []
        for row in section.data:
            try:
                floor = UndergroundFloor(
                    name=self._get_str(row, 'Name', ''),
                    status=self._get_str(row, 'Status', 'New'),
                    space_name=self._get_str(row, 'Name', ''),
                    occupancy_class=self._get_str(row, 'Occupancy Classification', ''),
                    conditioning_status=self._get_str(row, 'Conditioning Status', ''),
                    slab_type=self._get_str(row, 'Slab Type', 'Unheated'),
                    area_sf=self._get_float(row, 'Area', 0),
                    exposed_perimeter_ft=self._get_float(row, 'Exposed Perimeter', 0),
                    construction_name=self._get_str(row, 'Cons Name', ''),
                    insulation_orientation=self._get_str(row, 'Slab Insulation Orientation'),
                    f_factor=self._get_float(row, "Overall 'F' Factor"),
                )
                if floor.name:
                    floors.append(floor)
            except Exception as e:
                logger.warning(f"Error parsing underground floor row: {e}")

        return floors

    def _parse_construction_assemblies(self, sections: Dict[str, CebeccSection]) -> List[ConstructionAssembly]:
        """Parse Construction Assembly section."""
        section = self._get_section(sections, 'Construction Assembly')
        if not section:
            return []

        assemblies = []
        for row in section.data:
            try:
                # Extract material layers (columns Material Layer 1-10)
                layers = []
                for i in range(1, 11):
                    layer = self._get_str(row, f'Material Layer {i}')
                    if layer:
                        layers.append(layer)

                assembly = ConstructionAssembly(
                    name=self._get_str(row, 'Name', ''),
                    surface_type=self._get_str(row, 'Surface Type', ''),
                    material_layers=layers,
                )
                if assembly.name:
                    assemblies.append(assembly)
            except Exception as e:
                logger.warning(f"Error parsing construction assembly row: {e}")

        return assemblies

    def _parse_construction_materials(self, sections: Dict[str, CebeccSection]) -> List[ConstructionMaterial]:
        """Parse Construction Materials section."""
        section = self._get_section(sections, 'Construction Materials')
        if not section:
            return []

        materials = []
        for row in section.data:
            try:
                material = ConstructionMaterial(
                    name=self._get_str(row, 'Name', ''),
                    code_item=self._get_str(row, 'Code Item', ''),
                    material_type=self._get_str(row, 'Type', ''),
                    r_value=self._get_float(row, 'R-value', 0),
                    thickness_in=self._get_float(row, 'Thickness', 0),
                    frame_type=self._get_str(row, 'Frame Type'),
                    frame_configuration=self._get_str(row, 'Frame Configuration'),
                )
                if material.name:
                    materials.append(material)
            except Exception as e:
                logger.warning(f"Error parsing construction material row: {e}")

        return materials

    # Helper methods
    def _get_str(self, row: Dict[str, Any], key: str, default: str = None) -> Optional[str]:
        """Get string value from row."""
        val = row.get(key)
        if val is None:
            for k, v in row.items():
                if k.lower() == key.lower():
                    val = v
                    break
        if val is None or val == '' or val == 'NONE' or val == '- specify -':
            return default
        return str(val)

    def _get_float(self, row: Dict[str, Any], key: str, default: float = None) -> Optional[float]:
        """Get float value from row."""
        val = row.get(key)
        if val is None:
            for k, v in row.items():
                if k.lower() == key.lower():
                    val = v
                    break
        return self._clean_numeric(val) if val is not None else default

    def _get_int(self, row: Dict[str, Any], key: str, default: int = None) -> Optional[int]:
        """Get int value from row."""
        val = self._get_float(row, key)
        return int(val) if val is not None else default

    def _clean_numeric(self, val: Any) -> Optional[float]:
        """Clean a numeric value."""
        if val is None:
            return None
        if isinstance(val, (int, float)):
            if val == self.MISSING_VALUE:
                return None
            return float(val)
        try:
            num = float(str(val).replace(',', ''))
            if num == self.MISSING_VALUE:
                return None
            return num
        except (ValueError, TypeError):
            return None


def parse_envelope(filepath: Path) -> EnvelopeOutput:
    """
    Parse an Envelope.csv file.

    Args:
        filepath: Path to the CSV file

    Returns:
        EnvelopeOutput with all parsed components
    """
    parser = EnvelopeParser()
    return parser.parse_file(filepath)


def supplement_envelope_with_xml(
    envelope: EnvelopeOutput,
    xml_path: Path,
) -> EnvelopeOutput:
    """
    Supplement envelope CSV data with XML AnalysisResults data.

    For residential buildings, the Envelope CSV may be missing detailed
    component data (roof areas, window U-factors, SHGC). This function
    fills in missing values from the XML AnalysisResults file.

    Args:
        envelope: EnvelopeOutput from parse_envelope()
        xml_path: Path to AnalysisResults.xml

    Returns:
        EnvelopeOutput with XML data merged in
    """
    from .analysis_results_xml import parse_analysis_results

    try:
        xml_data = parse_analysis_results(xml_path)
    except Exception as e:
        logger.warning(f"Failed to parse XML for envelope supplement: {e}")
        return envelope

    # Supplement building areas
    areas = envelope.building_areas

    # Roof area (if missing in CSV)
    if areas.total_roof_area_sf == 0 and xml_data.total_roof_area_sf > 0:
        areas.total_roof_area_sf = xml_data.total_roof_area_sf
        logger.debug(f"Supplemented roof area from XML: {xml_data.total_roof_area_sf:,.0f} SF")

    # Store XML-derived values in envelope for cost calculations
    # These are stored as properties that the cost mappers can use
    envelope._xml_roof_solar_reflectance = xml_data.avg_roof_solar_reflectance
    envelope._xml_window_u_factor = xml_data.avg_window_u_factor
    envelope._xml_window_shgc = xml_data.avg_window_shgc

    return envelope


def parse_envelope_with_xml(
    csv_path: Path,
    xml_path: Optional[Path] = None,
) -> EnvelopeOutput:
    """
    Parse envelope data from CSV and optionally supplement with XML.

    Args:
        csv_path: Path to Envelope.csv
        xml_path: Optional path to AnalysisResults.xml

    Returns:
        EnvelopeOutput with all available data
    """
    envelope = parse_envelope(csv_path)

    if xml_path and xml_path.exists():
        envelope = supplement_envelope_with_xml(envelope, xml_path)

    return envelope
