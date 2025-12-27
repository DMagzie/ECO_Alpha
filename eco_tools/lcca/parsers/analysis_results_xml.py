"""
Parser for CBECC AnalysisResults.xml files.

Extracts envelope data that may be missing from CSV outputs:
- Roof areas and solar reflectance
- Window U-factors and SHGC
- Wall areas and constructions
- Construction layer details

This parser supplements the Envelope CSV parser for residential
buildings where detailed component data isn't exported to CSV.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, List, Dict, Any
import xml.etree.ElementTree as ET
import logging
import re

logger = logging.getLogger(__name__)


@dataclass
class RoofElement:
    """Individual roof/ceiling element from XML."""
    name: str
    area_sf: float
    orientation: str = ''
    construction: str = ''
    solar_reflectance: float = 0.0
    roof_rise: float = 0.0
    element_type: str = ''  # ResCathedralCeiling, ExtRoof, etc.


@dataclass
class WallElement:
    """Individual wall element from XML."""
    name: str
    area_sf: float
    orientation: str = ''
    construction: str = ''
    element_type: str = ''  # ResExtWall, ExtWall, etc.


@dataclass
class WindowElement:
    """Individual window element from XML."""
    name: str
    area_sf: float = 0.0
    parent_wall: str = ''
    window_type: str = ''
    spec_method: str = ''


@dataclass
class WindowType:
    """Window type definition with performance specs."""
    name: str
    u_factor: Optional[float] = None
    shgc: Optional[float] = None
    vt: Optional[float] = None  # Visual transmittance


@dataclass
class ConstructionLayer:
    """Construction assembly definition."""
    name: str
    surface_type: str = ''  # Roof, Wall, Floor
    layers: List[str] = field(default_factory=list)
    u_factor: Optional[float] = None
    r_value: Optional[float] = None


@dataclass
class DHWHeater:
    """Water heater equipment from XML."""
    name: str
    fuel: str = ''  # Gas, Electricity
    tank_type: str = ''  # Commercial Storage, Heat Pump, Instantaneous
    input_rating_btuh: float = 0.0
    thermal_efficiency: float = 0.0
    tank_volume_gal: float = 0.0
    standby_loss_frac: float = 0.0
    count: int = 1


@dataclass
class DHWSystem:
    """Residential DHW system from XML."""
    name: str
    system_type: str = ''
    central_recirc_type: str = ''
    heaters: List[DHWHeater] = field(default_factory=list)


@dataclass
class ConstructionTypeBreakdown:
    """Area breakdown by construction type."""
    construction_name: str
    area_sf: float
    count: int = 0
    u_factor: Optional[float] = None  # Extracted from name if available


@dataclass
class EnergyEndUse:
    """Energy consumption by end use with Proposed vs Standard comparison."""
    name: str                              # "Space Heating", "Space Cooling", etc.
    proposed_elec_kbtu: float = 0.0        # PropElecEnergy
    proposed_gas_kbtu: float = 0.0         # PropNatGasEnergy
    proposed_tdv: float = 0.0              # ProposedTDV (kTDV/ft²)
    proposed_demand_kw: float = 0.0        # PropElecDemand
    standard_elec_kbtu: float = 0.0        # StdElecEnergy
    standard_gas_kbtu: float = 0.0         # StdNatGasEnergy (if present)
    standard_tdv: float = 0.0              # StandardTDV
    standard_demand_kw: float = 0.0        # StdElecDemand
    margin_tdv: float = 0.0                # CompMarginTDV


@dataclass
class EnergyComparison:
    """Complete energy comparison between Proposed and Standard models."""
    end_uses: List[EnergyEndUse] = field(default_factory=list)

    # Aggregated totals
    total_proposed_elec_kbtu: float = 0.0
    total_proposed_gas_kbtu: float = 0.0
    total_proposed_tdv: float = 0.0
    total_standard_elec_kbtu: float = 0.0
    total_standard_gas_kbtu: float = 0.0
    total_standard_tdv: float = 0.0

    # Compliance
    total_margin_tdv: float = 0.0
    compliance_passes: bool = False

    def calculate_totals(self):
        """Calculate aggregate totals from end uses."""
        self.total_proposed_elec_kbtu = sum(e.proposed_elec_kbtu for e in self.end_uses)
        self.total_proposed_gas_kbtu = sum(e.proposed_gas_kbtu for e in self.end_uses)
        self.total_proposed_tdv = sum(e.proposed_tdv for e in self.end_uses)
        self.total_standard_elec_kbtu = sum(e.standard_elec_kbtu for e in self.end_uses)
        self.total_standard_gas_kbtu = sum(e.standard_gas_kbtu for e in self.end_uses)
        self.total_standard_tdv = sum(e.standard_tdv for e in self.end_uses)
        self.total_margin_tdv = sum(e.margin_tdv for e in self.end_uses)
        self.compliance_passes = self.total_margin_tdv >= 0


@dataclass
class AnalysisResultsOutput:
    """Complete parsed output from AnalysisResults.xml."""
    project_name: str = ''
    climate_zone: str = ''

    # Roof data
    roof_elements: List[RoofElement] = field(default_factory=list)
    total_roof_area_sf: float = 0.0
    avg_roof_solar_reflectance: float = 0.0

    # Wall data
    wall_elements: List[WallElement] = field(default_factory=list)
    total_wall_area_sf: float = 0.0

    # Window data
    window_elements: List[WindowElement] = field(default_factory=list)
    window_types: List[WindowType] = field(default_factory=list)
    total_window_area_sf: float = 0.0
    avg_window_u_factor: Optional[float] = None
    avg_window_shgc: Optional[float] = None

    # Construction data
    constructions: List[ConstructionLayer] = field(default_factory=list)

    # Raw performance values found
    fenestration_u_factors: List[float] = field(default_factory=list)
    fenestration_shgc_values: List[float] = field(default_factory=list)

    # DHW data
    dhw_systems: List[DHWSystem] = field(default_factory=list)
    dhw_heaters: List[DHWHeater] = field(default_factory=list)
    total_dhw_capacity_btuh: float = 0.0
    total_dhw_storage_gal: float = 0.0

    # Construction type breakdowns
    wall_type_breakdown: List[ConstructionTypeBreakdown] = field(default_factory=list)
    roof_type_breakdown: List[ConstructionTypeBreakdown] = field(default_factory=list)
    window_type_breakdown: List[ConstructionTypeBreakdown] = field(default_factory=list)

    # Energy comparison (Proposed vs Standard)
    energy_comparison: Optional[EnergyComparison] = None

    def calculate_summaries(self):
        """Calculate summary values from parsed elements."""
        # Total roof area
        self.total_roof_area_sf = sum(r.area_sf for r in self.roof_elements)

        # Average roof solar reflectance (area-weighted)
        if self.roof_elements and self.total_roof_area_sf > 0:
            weighted_refl = sum(
                r.solar_reflectance * r.area_sf
                for r in self.roof_elements
                if r.solar_reflectance > 0
            )
            total_with_refl = sum(
                r.area_sf for r in self.roof_elements
                if r.solar_reflectance > 0
            )
            if total_with_refl > 0:
                self.avg_roof_solar_reflectance = weighted_refl / total_with_refl

        # Total wall area
        self.total_wall_area_sf = sum(w.area_sf for w in self.wall_elements)

        # Total window area
        self.total_window_area_sf = sum(w.area_sf for w in self.window_elements)

        # Average window U-factor (from fenestration values found)
        if self.fenestration_u_factors:
            self.avg_window_u_factor = sum(self.fenestration_u_factors) / len(self.fenestration_u_factors)

        # Average window SHGC
        if self.fenestration_shgc_values:
            self.avg_window_shgc = sum(self.fenestration_shgc_values) / len(self.fenestration_shgc_values)

        # DHW summaries
        self.total_dhw_capacity_btuh = sum(h.input_rating_btuh * h.count for h in self.dhw_heaters)
        self.total_dhw_storage_gal = sum(h.tank_volume_gal * h.count for h in self.dhw_heaters)

        # Construction type breakdowns (aggregate from elements)
        self._calculate_wall_breakdown()
        self._calculate_roof_breakdown()
        self._calculate_window_breakdown()

    def _calculate_wall_breakdown(self):
        """Calculate wall area breakdown by construction type."""
        construction_areas: Dict[str, float] = {}
        construction_counts: Dict[str, int] = {}
        for wall in self.wall_elements:
            cons = wall.construction or 'Unknown'
            construction_areas[cons] = construction_areas.get(cons, 0) + wall.area_sf
            construction_counts[cons] = construction_counts.get(cons, 0) + 1

        self.wall_type_breakdown = [
            ConstructionTypeBreakdown(
                construction_name=name,
                area_sf=area,
                count=construction_counts[name],
                u_factor=self._extract_u_factor_from_name(name),
            )
            for name, area in sorted(construction_areas.items(), key=lambda x: -x[1])
        ]

    def _calculate_roof_breakdown(self):
        """Calculate roof area breakdown by construction type."""
        construction_areas: Dict[str, float] = {}
        construction_counts: Dict[str, int] = {}
        for roof in self.roof_elements:
            cons = roof.construction or 'Unknown'
            construction_areas[cons] = construction_areas.get(cons, 0) + roof.area_sf
            construction_counts[cons] = construction_counts.get(cons, 0) + 1

        self.roof_type_breakdown = [
            ConstructionTypeBreakdown(
                construction_name=name,
                area_sf=area,
                count=construction_counts[name],
                u_factor=self._extract_u_factor_from_name(name),
            )
            for name, area in sorted(construction_areas.items(), key=lambda x: -x[1])
        ]

    def _calculate_window_breakdown(self):
        """Calculate window area breakdown by window type."""
        type_areas: Dict[str, float] = {}
        type_counts: Dict[str, int] = {}
        for win in self.window_elements:
            wtype = win.window_type or 'Unknown'
            type_areas[wtype] = type_areas.get(wtype, 0) + win.area_sf
            type_counts[wtype] = type_counts.get(wtype, 0) + 1

        self.window_type_breakdown = [
            ConstructionTypeBreakdown(
                construction_name=name,
                area_sf=area,
                count=type_counts[name],
                u_factor=None,  # Window U-factor from window types, not name
            )
            for name, area in sorted(type_areas.items(), key=lambda x: -x[1])
        ]

    @staticmethod
    def _extract_u_factor_from_name(name: str) -> Optional[float]:
        """Extract U-factor from construction name if present (e.g., 'U=0.065')."""
        match = re.search(r'U\s*=\s*([\d.]+)', name)
        if match:
            try:
                return float(match.group(1))
            except ValueError:
                pass
        return None


class AnalysisResultsParser:
    """Parser for CBECC AnalysisResults.xml files."""

    # Element tags for different building types
    ROOF_TAGS = [
        'ResCathedralCeiling',  # Residential cathedral ceiling/roof
        'ExtRoof',               # Commercial exterior roof
        'Roof',                  # Generic roof
        'CathedralCeiling',      # Cathedral ceiling
    ]

    WALL_TAGS = [
        'ResExtWall',            # Residential exterior wall
        'ExtWall',               # Commercial exterior wall
    ]

    WINDOW_TAGS = [
        'ResWin',                # Residential window
        'Win',                   # Commercial window
        'Skylight',              # Skylight
    ]

    def __init__(self):
        self.output = AnalysisResultsOutput()
        self.parse_errors: List[str] = []
        self.parse_warnings: List[str] = []

    def parse_file(self, filepath: Path) -> AnalysisResultsOutput:
        """
        Parse AnalysisResults.xml and return structured output.

        Args:
            filepath: Path to AnalysisResults.xml

        Returns:
            AnalysisResultsOutput with all parsed components
        """
        filepath = Path(filepath)
        if not filepath.exists():
            raise FileNotFoundError(f"File not found: {filepath}")

        # Reset state
        self.output = AnalysisResultsOutput()
        self.parse_errors = []
        self.parse_warnings = []

        try:
            tree = ET.parse(filepath)
            root = tree.getroot()
        except ET.ParseError as e:
            raise ValueError(f"Failed to parse XML: {e}")

        # Extract project info
        self._parse_project_info(root)

        # Parse envelope elements
        self._parse_roof_elements(root)
        self._parse_wall_elements(root)
        self._parse_window_elements(root)

        # Parse performance values
        self._parse_fenestration_performance(root)

        # Parse constructions
        self._parse_constructions(root)

        # Parse DHW systems
        self._parse_dhw_systems(root)

        # Parse energy comparison (Proposed vs Standard)
        self._parse_energy_comparison(root)

        # Calculate summaries
        self.output.calculate_summaries()

        return self.output

    def _parse_project_info(self, root: ET.Element) -> None:
        """Extract project-level information."""
        # Try to find project name
        for tag in ['ProjName', 'Name', 'ProjectName']:
            elem = root.find(f'.//{tag}')
            if elem is not None and elem.text:
                self.output.project_name = elem.text.strip()
                break

        # Climate zone
        for tag in ['ClimateZone', 'CliZone']:
            elem = root.find(f'.//{tag}')
            if elem is not None and elem.text:
                self.output.climate_zone = elem.text.strip()
                break

    def _parse_roof_elements(self, root: ET.Element) -> None:
        """Parse all roof/ceiling elements."""
        for tag in self.ROOF_TAGS:
            for elem in root.iter(tag):
                try:
                    roof = self._parse_single_roof(elem, tag)
                    if roof and roof.area_sf > 0:
                        self.output.roof_elements.append(roof)
                except Exception as e:
                    self.parse_warnings.append(f"Error parsing roof element: {e}")

    def _parse_single_roof(self, elem: ET.Element, element_type: str) -> Optional[RoofElement]:
        """Parse a single roof element."""
        name_elem = elem.find('Name')
        area_elem = elem.find('Area')

        if name_elem is None or area_elem is None:
            return None

        try:
            area = float(area_elem.text) if area_elem.text else 0.0
        except ValueError:
            return None

        roof = RoofElement(
            name=name_elem.text.strip() if name_elem.text else '',
            area_sf=area,
            element_type=element_type,
        )

        # Optional fields
        orient_elem = elem.find('Orientation')
        if orient_elem is not None and orient_elem.text:
            roof.orientation = orient_elem.text.strip()

        cons_elem = elem.find('Construction')
        if cons_elem is not None and cons_elem.text:
            roof.construction = cons_elem.text.strip()

        refl_elem = elem.find('RoofSolReflect')
        if refl_elem is not None and refl_elem.text:
            try:
                roof.solar_reflectance = float(refl_elem.text)
            except ValueError:
                pass

        rise_elem = elem.find('RoofRise')
        if rise_elem is not None and rise_elem.text:
            try:
                roof.roof_rise = float(rise_elem.text)
            except ValueError:
                pass

        return roof

    def _parse_wall_elements(self, root: ET.Element) -> None:
        """Parse all wall elements."""
        for tag in self.WALL_TAGS:
            for elem in root.iter(tag):
                try:
                    wall = self._parse_single_wall(elem, tag)
                    if wall and wall.area_sf > 0:
                        self.output.wall_elements.append(wall)
                except Exception as e:
                    self.parse_warnings.append(f"Error parsing wall element: {e}")

    def _parse_single_wall(self, elem: ET.Element, element_type: str) -> Optional[WallElement]:
        """Parse a single wall element."""
        name_elem = elem.find('Name')
        area_elem = elem.find('Area')

        if name_elem is None or area_elem is None:
            return None

        try:
            area = float(area_elem.text) if area_elem.text else 0.0
        except ValueError:
            return None

        wall = WallElement(
            name=name_elem.text.strip() if name_elem.text else '',
            area_sf=area,
            element_type=element_type,
        )

        # Optional fields
        orient_elem = elem.find('Orientation')
        if orient_elem is not None and orient_elem.text:
            wall.orientation = orient_elem.text.strip()

        cons_elem = elem.find('Construction')
        if cons_elem is not None and cons_elem.text:
            wall.construction = cons_elem.text.strip()

        return wall

    def _parse_window_elements(self, root: ET.Element) -> None:
        """Parse all window elements."""
        for tag in self.WINDOW_TAGS:
            for elem in root.iter(tag):
                try:
                    window = self._parse_single_window(elem, tag)
                    if window:
                        self.output.window_elements.append(window)
                except Exception as e:
                    self.parse_warnings.append(f"Error parsing window element: {e}")

    def _parse_single_window(self, elem: ET.Element, element_type: str) -> Optional[WindowElement]:
        """Parse a single window element."""
        name_elem = elem.find('Name')
        if name_elem is None:
            return None

        window = WindowElement(
            name=name_elem.text.strip() if name_elem.text else '',
        )

        # Area (may not always be present for residential)
        area_elem = elem.find('Area')
        if area_elem is not None and area_elem.text:
            try:
                window.area_sf = float(area_elem.text)
            except ValueError:
                pass

        # Window type reference
        type_elem = elem.find('WinType')
        if type_elem is not None and type_elem.text:
            window.window_type = type_elem.text.strip()

        # Spec method
        spec_elem = elem.find('SpecMethod')
        if spec_elem is not None and spec_elem.text:
            window.spec_method = spec_elem.text.strip()

        return window

    def _parse_fenestration_performance(self, root: ET.Element) -> None:
        """
        Parse fenestration performance values from various XML elements.

        CBECC stores these in different places depending on the report section.
        """
        # U-factor patterns (non-namespaced tags)
        u_factor_tags = [
            'NFRCUfactor',                          # NFRC rated U-factor (most common)
            'exNFRCUfactor',                        # Existing NFRC U-factor
            'FenAssemblyUFactor',
            'WindowUFactor',
            'GlazingUFactor',
        ]

        for tag in u_factor_tags:
            for elem in root.iter(tag):
                if elem.text:
                    try:
                        val = float(elem.text)
                        # Filter out unreasonable values (U-factor typically 0.1-1.2)
                        if 0.1 <= val <= 1.5:
                            self.output.fenestration_u_factors.append(val)
                    except ValueError:
                        pass

        # SHGC patterns
        shgc_tags = [
            'NFRCSHGC',                             # NFRC rated SHGC (most common)
            'exNFRCSHGC',                           # Existing NFRC SHGC
            'SHGC',
            'SolarHeatGainCoeff',
            'GlazingSHGC',
        ]

        for tag in shgc_tags:
            for elem in root.iter(tag):
                if elem.text:
                    try:
                        val = float(elem.text)
                        # Filter out unreasonable values (SHGC typically 0.1-0.9)
                        if 0.05 <= val <= 0.95:
                            self.output.fenestration_shgc_values.append(val)
                    except ValueError:
                        pass

        # Remove duplicates while preserving order
        self.output.fenestration_u_factors = list(dict.fromkeys(self.output.fenestration_u_factors))
        self.output.fenestration_shgc_values = list(dict.fromkeys(self.output.fenestration_shgc_values))

    def _parse_constructions(self, root: ET.Element) -> None:
        """Parse construction assembly definitions."""
        # Look for construction definitions
        for tag in ['ConsAssm', 'Construction', 'RoofCons', 'WallCons']:
            for elem in root.iter(tag):
                try:
                    cons = self._parse_single_construction(elem)
                    if cons:
                        self.output.constructions.append(cons)
                except Exception as e:
                    self.parse_warnings.append(f"Error parsing construction: {e}")

    def _parse_single_construction(self, elem: ET.Element) -> Optional[ConstructionLayer]:
        """Parse a single construction assembly."""
        name_elem = elem.find('Name')
        if name_elem is None or not name_elem.text:
            return None

        cons = ConstructionLayer(
            name=name_elem.text.strip(),
        )

        # Surface type
        type_elem = elem.find('Type') or elem.find('SurfaceType')
        if type_elem is not None and type_elem.text:
            cons.surface_type = type_elem.text.strip()

        # U-factor
        u_elem = elem.find('UFactor') or elem.find('OverallUFactor')
        if u_elem is not None and u_elem.text:
            try:
                cons.u_factor = float(u_elem.text)
            except ValueError:
                pass

        # R-value
        r_elem = elem.find('RValue') or elem.find('OverallRValue')
        if r_elem is not None and r_elem.text:
            try:
                cons.r_value = float(r_elem.text)
            except ValueError:
                pass

        # Material layers
        for i in range(1, 11):
            layer_elem = elem.find(f'Layer{i}') or elem.find(f'MatLayer{i}')
            if layer_elem is not None and layer_elem.text:
                cons.layers.append(layer_elem.text.strip())

        return cons

    def _parse_dhw_systems(self, root: ET.Element) -> None:
        """Parse DHW systems and water heaters from XML."""
        # DHW system tags to look for
        dhw_system_tags = [
            'ResDHWSysRpt',   # Residential DHW system report
            'ResDHWSys',      # Residential DHW system input
            'FluidSys',       # Commercial fluid system (filter for ServiceHotWater)
        ]

        # Parse residential DHW systems
        for tag in ['ResDHWSysRpt', 'ResDHWSys']:
            for elem in root.iter(tag):
                try:
                    system = self._parse_dhw_system(elem)
                    if system:
                        self.output.dhw_systems.append(system)
                except Exception as e:
                    self.parse_warnings.append(f"Error parsing DHW system: {e}")

        # Also parse individual water heaters directly
        for tag in ['ResWtrHtr', 'WtrHtr', 'ResWtrHtrRpt']:
            for elem in root.iter(tag):
                try:
                    heater = self._parse_water_heater(elem)
                    if heater:
                        # Avoid duplicates (heaters may be in both systems and standalone)
                        if not any(h.name == heater.name for h in self.output.dhw_heaters):
                            self.output.dhw_heaters.append(heater)
                except Exception as e:
                    self.parse_warnings.append(f"Error parsing water heater: {e}")

    def _parse_dhw_system(self, elem: ET.Element) -> Optional[DHWSystem]:
        """Parse a single DHW system."""
        name_elem = elem.find('Name')
        if name_elem is None:
            return None

        system = DHWSystem(
            name=name_elem.text.strip() if name_elem.text else '',
        )

        # System type
        type_elem = elem.find('Type') or elem.find('SysType')
        if type_elem is not None and type_elem.text:
            system.system_type = type_elem.text.strip()

        # Central recirculation type
        recirc_elem = elem.find('CentralRecircType') or elem.find('CentDHWType')
        if recirc_elem is not None and recirc_elem.text:
            system.central_recirc_type = recirc_elem.text.strip()

        # Parse child water heaters
        for tag in ['ResWtrHtr', 'WtrHtr', 'ResWtrHtrRpt']:
            for htr_elem in elem.iter(tag):
                heater = self._parse_water_heater(htr_elem)
                if heater:
                    system.heaters.append(heater)
                    # Also add to global list
                    if not any(h.name == heater.name for h in self.output.dhw_heaters):
                        self.output.dhw_heaters.append(heater)

        return system

    def _parse_water_heater(self, elem: ET.Element) -> Optional[DHWHeater]:
        """Parse a single water heater element."""
        name_elem = elem.find('Name')
        if name_elem is None:
            return None

        heater = DHWHeater(
            name=name_elem.text.strip() if name_elem.text else '',
        )

        # Fuel type (HeaterElementType in residential XML)
        for tag in ['HeaterElementType', 'Fuel', 'FuelSrc', 'FuelType']:
            fuel_elem = elem.find(tag)
            if fuel_elem is not None and fuel_elem.text:
                heater.fuel = fuel_elem.text.strip()
                break

        # Tank type / heater type
        for tag in ['TankType', 'Type', 'WtrHtrType']:
            type_elem = elem.find(tag)
            if type_elem is not None and type_elem.text:
                heater.tank_type = type_elem.text.strip()
                break

        # Input rating (Btu/h)
        for tag in ['InputRating', 'InpRating', 'RatedInputPwr', 'InputPwr']:
            rating_elem = elem.find(tag)
            if rating_elem is not None and rating_elem.text:
                try:
                    heater.input_rating_btuh = float(rating_elem.text)
                    break
                except ValueError:
                    pass

        # Thermal efficiency (EnergyFactor or RecovEff in residential)
        for tag in ['EnergyFactor', 'RecovEff', 'ThrmlEff', 'ThermalEff', 'Efficiency']:
            eff_elem = elem.find(tag)
            if eff_elem is not None and eff_elem.text:
                try:
                    val = float(eff_elem.text)
                    # RecovEff is a percentage (94 = 0.94), EnergyFactor is decimal
                    if val > 1:
                        val = val / 100.0
                    heater.thermal_efficiency = val
                    break
                except ValueError:
                    pass

        # Tank volume (gallons) - TankVolume in residential XML
        for tag in ['TankVolume', 'TankVol', 'StorageCap', 'Volume', 'StorageVol']:
            vol_elem = elem.find(tag)
            if vol_elem is not None and vol_elem.text:
                try:
                    heater.tank_volume_gal = float(vol_elem.text)
                    break
                except ValueError:
                    pass

        # Standby loss fraction
        for tag in ['StbyLossFrac', 'StandbyLossFrac', 'StbyLoss']:
            loss_elem = elem.find(tag)
            if loss_elem is not None and loss_elem.text:
                try:
                    heater.standby_loss_frac = float(loss_elem.text)
                    break
                except ValueError:
                    pass

        # Count (default 1)
        count_elem = elem.find('Cnt') or elem.find('Count')
        if count_elem is not None and count_elem.text:
            try:
                heater.count = int(float(count_elem.text))
            except ValueError:
                pass

        return heater

    def _parse_energy_comparison(self, root: ET.Element) -> None:
        """Parse energy comparison between Proposed and Standard models.

        Only parses EnergyUse elements that have BOTH Proposed and Standard data,
        which are found in the Model Name="Standard" section of the XML.
        """
        comparison = EnergyComparison()

        # Find all EnergyUse elements that have Standard data
        # (only these have both Proposed and Standard values)
        for elem in root.iter('EnergyUse'):
            # Check if this element has Standard data
            std_elec = elem.find('StdElecEnergy')
            std_tdv = elem.find('StandardTDV')

            # Only parse elements that have Standard data
            if std_elec is None and std_tdv is None:
                continue

            try:
                end_use = self._parse_energy_end_use(elem)
                if end_use:
                    comparison.end_uses.append(end_use)
            except Exception as e:
                self.parse_warnings.append(f"Error parsing energy end use: {e}")

        # Calculate totals
        if comparison.end_uses:
            comparison.calculate_totals()
            self.output.energy_comparison = comparison

    def _parse_energy_end_use(self, elem: ET.Element) -> Optional[EnergyEndUse]:
        """Parse a single EnergyUse element."""
        # Get end use name
        name_elem = elem.find('EnduseName') or elem.find('Name')
        if name_elem is None or not name_elem.text:
            return None

        name = name_elem.text.strip()

        # Skip unnamed or utility end uses
        if not name or name in ('Total', 'Utility'):
            return None

        end_use = EnergyEndUse(name=name)

        # Proposed electric energy (kBtu)
        prop_elec = elem.find('PropElecEnergy')
        if prop_elec is not None and prop_elec.text:
            try:
                end_use.proposed_elec_kbtu = float(prop_elec.text)
            except ValueError:
                pass

        # Proposed gas energy (kBtu)
        prop_gas = elem.find('PropNatGasEnergy')
        if prop_gas is not None and prop_gas.text:
            try:
                end_use.proposed_gas_kbtu = float(prop_gas.text)
            except ValueError:
                pass

        # Proposed TDV (may have index attribute)
        prop_tdv = elem.find('ProposedTDV')
        if prop_tdv is not None and prop_tdv.text:
            try:
                end_use.proposed_tdv = float(prop_tdv.text)
            except ValueError:
                pass

        # Proposed demand (kW)
        prop_demand = elem.find('PropElecDemand')
        if prop_demand is not None and prop_demand.text:
            try:
                end_use.proposed_demand_kw = float(prop_demand.text)
            except ValueError:
                pass

        # Standard electric energy (kBtu)
        std_elec = elem.find('StdElecEnergy')
        if std_elec is not None and std_elec.text:
            try:
                end_use.standard_elec_kbtu = float(std_elec.text)
            except ValueError:
                pass

        # Standard gas energy (kBtu) - may not always be present
        std_gas = elem.find('StdNatGasEnergy')
        if std_gas is not None and std_gas.text:
            try:
                end_use.standard_gas_kbtu = float(std_gas.text)
            except ValueError:
                pass

        # Standard TDV
        std_tdv = elem.find('StandardTDV')
        if std_tdv is not None and std_tdv.text:
            try:
                end_use.standard_tdv = float(std_tdv.text)
            except ValueError:
                pass

        # Standard demand (kW)
        std_demand = elem.find('StdElecDemand')
        if std_demand is not None and std_demand.text:
            try:
                end_use.standard_demand_kw = float(std_demand.text)
            except ValueError:
                pass

        # Compliance margin TDV
        margin = elem.find('CompMarginTDV')
        if margin is not None and margin.text:
            try:
                end_use.margin_tdv = float(margin.text)
            except ValueError:
                pass

        return end_use


def parse_analysis_results(filepath: Path) -> AnalysisResultsOutput:
    """
    Parse an AnalysisResults.xml file.

    Args:
        filepath: Path to the XML file

    Returns:
        AnalysisResultsOutput with all parsed components
    """
    parser = AnalysisResultsParser()
    return parser.parse_file(filepath)
