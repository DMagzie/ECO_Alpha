"""
Site Load Intake Loader.

Loads and validates site load intake YAML files against the schema.
Provides structured access to intake data for CbeccTemplate and calculators.

Supports scope controls to include/exclude specific load types from analysis.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Any
import yaml


@dataclass
class AnalysisScope:
    """
    Controls which site load components are included in the analysis.

    Set components to False to exclude them from calculations and reports,
    even if data is provided in the intake form.
    """
    elevators: bool = True
    escalators: bool = True
    parking_exhaust: bool = True
    ev_charging: bool = True
    pools: bool = True
    spas: bool = True
    site_lighting: bool = True
    it_telecom: bool = True
    water_pumps: bool = True
    trash_compactor: bool = True
    custom_loads: bool = True

    def is_included(self, component: str) -> bool:
        """Check if a component is included in scope."""
        return getattr(self, component, True)

    def get_excluded(self) -> List[str]:
        """Get list of excluded components."""
        return [k for k, v in self.__dict__.items() if not v]

    def get_included(self) -> List[str]:
        """Get list of included components."""
        return [k for k, v in self.__dict__.items() if v]


@dataclass
class ElevatorIntake:
    """Elevator configuration from intake form."""
    count: int = 0
    type: str = "traction_geared"
    floors_served: int = 0
    override_cec_values: bool = False
    actual_power_kw: Optional[float] = None
    zone_assignment: Optional[str] = None


@dataclass
class EscalatorIntake:
    """Escalator configuration from intake form."""
    count: int = 0
    width: str = "32_inch"
    variable_speed: bool = False
    actual_power_kw: Optional[float] = None
    zone_assignment: Optional[str] = None


@dataclass
class ParkingExhaustIntake:
    """Parking exhaust configuration from intake form."""
    system_type: str = "constant_volume"
    total_cfm: Optional[float] = None
    cfm_per_sf: float = 0.75
    fan_power_w_cfm: float = 0.35
    co_control: bool = True
    zone_assignment: Optional[str] = None


@dataclass
class ParkingGarageIntake:
    """Parking garage configuration from intake form."""
    total_area_sf: float = 0
    parking_spaces: int = 0
    levels: int = 1
    exhaust: ParkingExhaustIntake = field(default_factory=ParkingExhaustIntake)
    lighting_modeled_in_cbecc: bool = True


@dataclass
class EVChargingIntake:
    """EV charging configuration from intake form."""
    calgreen_2025: bool = True
    dwelling_units: int = 0
    common_parking_spaces: int = 0
    num_ports: Optional[int] = None
    charger_level: str = "level_2_low"
    kw_per_port: Optional[float] = None
    location_type: str = "mf_assigned"
    alms_enabled: bool = True
    alms_factor: float = 0.4


@dataclass
class PoolIntake:
    """Pool configuration from intake form."""
    name: str = "Pool"
    surface_area_sf: float = 0
    volume_gallons: Optional[float] = None
    pool_type: str = "commercial"
    heated: bool = True
    heater_type: str = "gas"
    heater_efficiency: Optional[float] = None
    pump_hp: Optional[float] = None
    variable_speed_pump: bool = True


@dataclass
class SpaIntake:
    """Spa configuration from intake form."""
    name: str = "Spa"
    volume_gallons: float = 500
    heater_type: str = "electric"
    jet_pump_hp: float = 2.0


@dataclass
class ProjectIntake:
    """Project information from intake form."""
    name: str = ""
    building_type: str = "multifamily"
    climate_zone: Optional[int] = None
    dwelling_units: int = 0
    floor_area_sf: Optional[float] = None


@dataclass
class SiteLoadIntake:
    """
    Complete site load intake data structure.

    Loaded from YAML intake files and used by:
    - CbeccTemplate for model injection
    - Site load calculators for energy calculations

    The `scope` attribute controls which components are included in the analysis.
    Components can be excluded even if data is provided.
    """
    project: ProjectIntake = field(default_factory=ProjectIntake)
    elevators: ElevatorIntake = field(default_factory=ElevatorIntake)
    escalators: EscalatorIntake = field(default_factory=EscalatorIntake)
    parking_garage: ParkingGarageIntake = field(default_factory=ParkingGarageIntake)
    ev_charging: EVChargingIntake = field(default_factory=EVChargingIntake)
    pools: List[PoolIntake] = field(default_factory=list)
    spas: List[SpaIntake] = field(default_factory=list)

    # Analysis scope controls
    scope: AnalysisScope = field(default_factory=AnalysisScope)

    # Raw data for custom loads and extensions
    raw_data: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_yaml(cls, yaml_path: str | Path) -> "SiteLoadIntake":
        """
        Load intake data from a YAML file.

        Args:
            yaml_path: Path to YAML intake file

        Returns:
            SiteLoadIntake with parsed data
        """
        yaml_path = Path(yaml_path)
        with open(yaml_path, 'r') as f:
            data = yaml.safe_load(f)

        return cls.from_dict(data)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SiteLoadIntake":
        """
        Create intake from dictionary data.

        Args:
            data: Dictionary with intake data

        Returns:
            SiteLoadIntake with parsed data
        """
        intake = cls()
        intake.raw_data = data.copy()

        # Parse analysis scope
        if "scope" in data:
            scope_data = data["scope"]
            intake.scope = AnalysisScope(
                elevators=scope_data.get("elevators", True),
                escalators=scope_data.get("escalators", True),
                parking_exhaust=scope_data.get("parking_exhaust", True),
                ev_charging=scope_data.get("ev_charging", True),
                pools=scope_data.get("pools", True),
                spas=scope_data.get("spas", True),
                site_lighting=scope_data.get("site_lighting", True),
                it_telecom=scope_data.get("it_telecom", True),
                water_pumps=scope_data.get("water_pumps", True),
                trash_compactor=scope_data.get("trash_compactor", True),
                custom_loads=scope_data.get("custom_loads", True),
            )

        # Parse project
        if "project" in data:
            proj = data["project"]
            intake.project = ProjectIntake(
                name=proj.get("name", ""),
                building_type=proj.get("building_type", "multifamily"),
                climate_zone=proj.get("climate_zone"),
                dwelling_units=proj.get("dwelling_units", 0),
                floor_area_sf=proj.get("floor_area_sf"),
            )

        # Parse elevators
        if "elevators" in data:
            elev = data["elevators"]
            intake.elevators = ElevatorIntake(
                count=elev.get("count", 0),
                type=elev.get("type", "traction_geared"),
                floors_served=elev.get("floors_served", 0),
                override_cec_values=elev.get("override_cec_values", False),
                actual_power_kw=elev.get("actual_power_kw"),
                zone_assignment=elev.get("zone_assignment"),
            )

        # Parse escalators
        if "escalators" in data:
            escal = data["escalators"]
            intake.escalators = EscalatorIntake(
                count=escal.get("count", 0),
                width=escal.get("width", "32_inch"),
                variable_speed=escal.get("variable_speed", False),
                actual_power_kw=escal.get("actual_power_kw"),
                zone_assignment=escal.get("zone_assignment"),
            )

        # Parse parking garage
        if "parking_garage" in data:
            pkg = data["parking_garage"]
            exhaust_data = pkg.get("exhaust", {})

            intake.parking_garage = ParkingGarageIntake(
                total_area_sf=pkg.get("total_area_sf", 0),
                parking_spaces=pkg.get("parking_spaces", 0),
                levels=pkg.get("levels", 1),
                exhaust=ParkingExhaustIntake(
                    system_type=exhaust_data.get("system_type", "constant_volume"),
                    total_cfm=exhaust_data.get("total_cfm"),
                    cfm_per_sf=exhaust_data.get("cfm_per_sf", 0.75),
                    fan_power_w_cfm=exhaust_data.get("fan_power_w_cfm", 0.35),
                    co_control=exhaust_data.get("co_control", True),
                    zone_assignment=exhaust_data.get("zone_assignment"),
                ),
                lighting_modeled_in_cbecc=pkg.get("lighting", {}).get("modeled_in_cbecc", True),
            )

        # Parse EV charging
        if "ev_charging" in data:
            ev = data["ev_charging"]
            intake.ev_charging = EVChargingIntake(
                calgreen_2025=ev.get("calgreen_2025", True),
                dwelling_units=ev.get("dwelling_units", 0),
                common_parking_spaces=ev.get("common_parking_spaces", 0),
                num_ports=ev.get("num_ports"),
                charger_level=ev.get("charger_level", "level_2_low"),
                kw_per_port=ev.get("kw_per_port"),
                location_type=ev.get("location_type", "mf_assigned"),
                alms_enabled=ev.get("alms_enabled", True),
                alms_factor=ev.get("alms_factor", 0.4),
            )

        # Parse pools
        if "pools" in data and isinstance(data["pools"], list):
            for pool_data in data["pools"]:
                intake.pools.append(PoolIntake(
                    name=pool_data.get("name", "Pool"),
                    surface_area_sf=pool_data.get("surface_area_sf", 0),
                    volume_gallons=pool_data.get("volume_gallons"),
                    pool_type=pool_data.get("pool_type", "commercial"),
                    heated=pool_data.get("heated", True),
                    heater_type=pool_data.get("heater_type", "gas"),
                    heater_efficiency=pool_data.get("heater_efficiency"),
                    pump_hp=pool_data.get("pump_hp"),
                    variable_speed_pump=pool_data.get("variable_speed_pump", True),
                ))

        # Parse spas
        if "spas" in data and isinstance(data["spas"], list):
            for spa_data in data["spas"]:
                intake.spas.append(SpaIntake(
                    name=spa_data.get("name", "Spa"),
                    volume_gallons=spa_data.get("volume_gallons", 500),
                    heater_type=spa_data.get("heater_type", "electric"),
                    jet_pump_hp=spa_data.get("jet_pump_hp", 2.0),
                ))

        return intake

    def to_calculator_inputs(self, respect_scope: bool = True) -> Dict[str, List[Dict]]:
        """
        Convert intake to site load calculator input format.

        Args:
            respect_scope: If True, exclude components not in scope

        Returns:
            Dictionary mapping load categories to calculator inputs
        """
        inputs = {}

        # EV charging
        if (not respect_scope or self.scope.ev_charging) and \
           (self.ev_charging.calgreen_2025 or self.ev_charging.num_ports):
            ev_input = {
                "calgreen_2025": self.ev_charging.calgreen_2025,
                "dwelling_units": self.ev_charging.dwelling_units or self.project.dwelling_units,
                "common_parking_spaces": self.ev_charging.common_parking_spaces,
                "charger_level": self.ev_charging.charger_level,
                "location_type": self.ev_charging.location_type,
                "alms_enabled": self.ev_charging.alms_enabled,
                "alms_factor": self.ev_charging.alms_factor,
            }
            if self.ev_charging.num_ports:
                ev_input["num_ports"] = self.ev_charging.num_ports
            if self.ev_charging.kw_per_port:
                ev_input["kw_per_port"] = self.ev_charging.kw_per_port
            if self.project.climate_zone:
                ev_input["climate_zone"] = self.project.climate_zone

            inputs["ev_charger"] = [ev_input]

        # Elevators (only if not modeled in CBECC)
        if (not respect_scope or self.scope.elevators) and self.elevators.count > 0:
            elev_input = {
                "num_elevators": self.elevators.count,
                "elevator_type": self.elevators.type,
            }
            if self.elevators.floors_served:
                elev_input["floors_served"] = self.elevators.floors_served
            if self.elevators.actual_power_kw:
                elev_input["motor_kw"] = self.elevators.actual_power_kw

            inputs["elevator"] = [elev_input]

        # Escalators (only if not modeled in CBECC)
        if (not respect_scope or self.scope.escalators) and self.escalators.count > 0:
            escal_input = {
                "num_escalators": self.escalators.count,
                "variable_speed": self.escalators.variable_speed,
            }
            if self.escalators.actual_power_kw:
                escal_input["motor_kw"] = self.escalators.actual_power_kw

            inputs["escalator"] = [escal_input]

        # Parking ventilation (only if not modeled in CBECC)
        if (not respect_scope or self.scope.parking_exhaust) and \
           self.parking_garage.total_area_sf > 0:
            exhaust = self.parking_garage.exhaust
            vent_input = {
                "fan_type": exhaust.system_type,
                "fan_power_w_per_cfm": exhaust.fan_power_w_cfm,
                "co_control": exhaust.co_control,
            }
            if exhaust.total_cfm:
                vent_input["exhaust_cfm"] = exhaust.total_cfm
            else:
                vent_input["parking_area_sf"] = self.parking_garage.total_area_sf
                vent_input["cfm_per_sf"] = exhaust.cfm_per_sf

            inputs["parking"] = [vent_input]

        # Pools
        if not respect_scope or self.scope.pools:
            for pool in self.pools:
                if "pool_pump" not in inputs:
                    inputs["pool_pump"] = []
                inputs["pool_pump"].append({
                    "name": pool.name,
                    "pool_gallons": pool.volume_gallons or pool.surface_area_sf * 5,  # Estimate
                    "pump_type": "variable" if pool.variable_speed_pump else "single",
                    "pump_hp": pool.pump_hp or 3.0,
                })

                if pool.heated:
                    if "pool_heater" not in inputs:
                        inputs["pool_heater"] = []
                    inputs["pool_heater"].append({
                        "name": pool.name,
                        "pool_gallons": pool.volume_gallons or pool.surface_area_sf * 5,
                        "heater_type": pool.heater_type,
                    })

        # Spas
        if not respect_scope or self.scope.spas:
            for spa in self.spas:
                if "spa" not in inputs:
                    inputs["spa"] = []
                inputs["spa"].append({
                    "name": spa.name,
                    "spa_gallons": spa.volume_gallons,
                    "heater_type": spa.heater_type,
                    "jet_pump_hp": spa.jet_pump_hp,
                })

        return inputs

    def get_cbecc_injections(self, respect_scope: bool = True) -> Dict[str, Any]:
        """
        Get data for CBECC model injection.

        Returns fields that should be injected into CBECC model:
        - Elevators (ElevCnt, ElevPwr)
        - Escalators (EscalCnt, EscalPwr)
        - Parking exhaust (PrkgGarExhFlow, PrkgGarExhFanPwr)

        Args:
            respect_scope: If True, exclude components not in scope

        Returns:
            Dictionary with CBECC injection data
        """
        injections = {}

        # Elevators
        if (not respect_scope or self.scope.elevators) and self.elevators.count > 0:
            injections["elevators"] = {
                "count": self.elevators.count,
                "power_kw": self.elevators.actual_power_kw,
                "zone": self.elevators.zone_assignment,
            }

        # Escalators
        if (not respect_scope or self.scope.escalators) and self.escalators.count > 0:
            injections["escalators"] = {
                "count": self.escalators.count,
                "power_kw": self.escalators.actual_power_kw,
                "zone": self.escalators.zone_assignment,
            }

        # Parking exhaust
        if (not respect_scope or self.scope.parking_exhaust) and \
           self.parking_garage.total_area_sf > 0:
            exhaust = self.parking_garage.exhaust
            cfm = exhaust.total_cfm
            if cfm is None:
                cfm = self.parking_garage.total_area_sf * exhaust.cfm_per_sf

            injections["parking_exhaust"] = {
                "exhaust_cfm": cfm,
                "fan_power_w_cfm": exhaust.fan_power_w_cfm,
                "co_control": exhaust.co_control,
                "zone": exhaust.zone_assignment,
            }

        return injections


class IntakeLoader:
    """
    Loader for site load intake files (YAML or Excel).

    Example:
        >>> intake = IntakeLoader.load("project_intake.yaml")
        >>> intake = IntakeLoader.load("Site_Load_Intake_Form.xlsx")
        >>> print(intake.project.name)
        >>> print(intake.ev_charging.dwelling_units)
        >>> calculator_inputs = intake.to_calculator_inputs()
    """

    @staticmethod
    def load(file_path: str | Path) -> SiteLoadIntake:
        """
        Load intake from YAML or Excel file.

        Args:
            file_path: Path to .yaml, .yml, or .xlsx file

        Returns:
            SiteLoadIntake with parsed data
        """
        file_path = Path(file_path)
        suffix = file_path.suffix.lower()

        if suffix in ['.yaml', '.yml']:
            return SiteLoadIntake.from_yaml(file_path)
        elif suffix == '.xlsx':
            return IntakeLoader.from_excel(file_path)
        else:
            raise ValueError(f"Unsupported file format: {suffix}. Use .yaml, .yml, or .xlsx")

    @staticmethod
    def from_excel(excel_path: str | Path) -> SiteLoadIntake:
        """
        Load intake from Excel file.

        Args:
            excel_path: Path to Excel intake form

        Returns:
            SiteLoadIntake with parsed data
        """
        try:
            from openpyxl import load_workbook
        except ImportError:
            raise ImportError("openpyxl is required for Excel loading. Install with: pip install openpyxl")

        excel_path = Path(excel_path)
        wb = load_workbook(excel_path, data_only=True)

        data = {}

        # Parse Analysis Scope sheet
        if "Analysis Scope" in wb.sheetnames:
            ws = wb["Analysis Scope"]
            scope = {}
            # Map Excel component names to scope attribute names
            scope_map = {
                "Elevators": "elevators",
                "Escalators": "escalators",
                "Parking Garage Exhaust": "parking_exhaust",
                "EV Charging": "ev_charging",
                "Pools": "pools",
                "Spas": "spas",
                "Site Lighting": "site_lighting",
                "IT/Telecom": "it_telecom",
                "Water Pumps": "water_pumps",
                "Trash Compactor": "trash_compactor",
                "Custom Loads": "custom_loads",
            }
            for row in range(7, 18):  # Rows 7-17 contain scope items
                component = ws.cell(row=row, column=1).value
                include_value = ws.cell(row=row, column=2).value
                if component in scope_map:
                    key = scope_map[component]
                    # "Include" = True, "Exclude" = False
                    scope[key] = str(include_value).lower() != "exclude"
            if scope:
                data["scope"] = scope

        # Parse Project Info sheet
        if "Project Info" in wb.sheetnames:
            ws = wb["Project Info"]
            project = {}
            field_map = {
                "Project Name": "name",
                "Building Type": "building_type",
                "Climate Zone": "climate_zone",
                "Dwelling Units": "dwelling_units",
                "Floor Area (SF)": "floor_area_sf",
            }
            for row in range(2, 10):
                field = ws.cell(row=row, column=1).value
                value = ws.cell(row=row, column=2).value
                if field in field_map and value:
                    key = field_map[field]
                    if key in ["climate_zone", "dwelling_units"]:
                        project[key] = int(value) if value else None
                    elif key == "floor_area_sf":
                        project[key] = float(value) if value else None
                    else:
                        project[key] = str(value)
            if project:
                data["project"] = project

        # Parse Elevators & Escalators sheet
        if "Elevators & Escalators" in wb.sheetnames:
            ws = wb["Elevators & Escalators"]
            elevators = {}
            elev_map = {
                "Elevator Count": ("count", int),
                "Elevator Type": ("type", str),
                "Floors Served": ("floors_served", int),
                "Override CEC Values": ("override_cec_values", lambda x: str(x).lower() == "yes"),
                "Actual Power (kW)": ("actual_power_kw", float),
                "Zone Assignment": ("zone_assignment", str),
            }
            for row in range(3, 9):
                field = ws.cell(row=row, column=1).value
                value = ws.cell(row=row, column=2).value
                if field in elev_map and value:
                    key, converter = elev_map[field]
                    try:
                        elevators[key] = converter(value)
                    except (ValueError, TypeError):
                        pass
            if elevators:
                data["elevators"] = elevators

            # Escalators
            escalators = {}
            escal_map = {
                "Escalator Count": ("count", int),
                "Step Width": ("width", str),
                "Variable Speed": ("variable_speed", lambda x: str(x).lower() == "yes"),
                "Actual Power (kW)": ("actual_power_kw", float),
                "Zone Assignment": ("zone_assignment", str),
            }
            for row in range(12, 17):
                field = ws.cell(row=row, column=1).value
                value = ws.cell(row=row, column=2).value
                if field in escal_map and value:
                    key, converter = escal_map[field]
                    try:
                        escalators[key] = converter(value)
                    except (ValueError, TypeError):
                        pass
            if escalators:
                data["escalators"] = escalators

        # Parse Parking Garage sheet
        if "Parking Garage" in wb.sheetnames:
            ws = wb["Parking Garage"]
            parking = {"exhaust": {}}
            pkg_map = {
                "Total Area (SF)": ("total_area_sf", float),
                "Parking Spaces": ("parking_spaces", int),
                "Levels": ("levels", int),
            }
            exhaust_map = {
                "System Type": ("system_type", str),
                "Total CFM": ("total_cfm", float),
                "CFM per SF": ("cfm_per_sf", float),
                "Fan Power (W/CFM)": ("fan_power_w_cfm", float),
                "CO Control": ("co_control", lambda x: str(x).lower() == "yes"),
                "Zone Assignment": ("zone_assignment", str),
            }
            for row in range(3, 15):
                field = ws.cell(row=row, column=1).value
                value = ws.cell(row=row, column=2).value
                if field in pkg_map and value:
                    key, converter = pkg_map[field]
                    try:
                        parking[key] = converter(value)
                    except (ValueError, TypeError):
                        pass
                elif field in exhaust_map and value:
                    key, converter = exhaust_map[field]
                    try:
                        parking["exhaust"][key] = converter(value)
                    except (ValueError, TypeError):
                        pass
            if parking.get("total_area_sf") or parking["exhaust"]:
                data["parking_garage"] = parking

        # Parse EV Charging sheet
        if "EV Charging" in wb.sheetnames:
            ws = wb["EV Charging"]
            ev = {}
            ev_map = {
                "CALGreen 2025 Compliant": ("calgreen_2025", lambda x: str(x).lower() == "yes"),
                "Dwelling Units": ("dwelling_units", int),
                "Common Parking Spaces": ("common_parking_spaces", int),
                "Number of Ports": ("num_ports", int),
                "Charger Level": ("charger_level", str),
                "Power per Port (kW)": ("kw_per_port", float),
                "Location Type": ("location_type", str),
                "ALMS Enabled": ("alms_enabled", lambda x: str(x).lower() == "yes"),
                "ALMS Factor": ("alms_factor", float),
            }
            for row in range(4, 15):
                field = ws.cell(row=row, column=1).value
                value = ws.cell(row=row, column=2).value
                if field in ev_map and value:
                    key, converter = ev_map[field]
                    try:
                        ev[key] = converter(value)
                    except (ValueError, TypeError):
                        pass
            if ev:
                data["ev_charging"] = ev

        wb.close()
        return SiteLoadIntake.from_dict(data)

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> SiteLoadIntake:
        """Create intake from dictionary."""
        return SiteLoadIntake.from_dict(data)

    @staticmethod
    def create_example() -> Dict[str, Any]:
        """
        Create an example intake dictionary.

        Returns:
            Example intake data as dictionary
        """
        return {
            "project": {
                "name": "Sunset Apartments",
                "building_type": "multifamily",
                "climate_zone": 9,
                "dwelling_units": 200,
                "floor_area_sf": 180000,
            },
            "elevators": {
                "count": 4,
                "type": "traction_geared",
                "floors_served": 8,
                "zone_assignment": "Elevator_Lobby_L01",
            },
            "parking_garage": {
                "total_area_sf": 50000,
                "parking_spaces": 220,
                "levels": 2,
                "exhaust": {
                    "system_type": "variable_speed",
                    "cfm_per_sf": 0.75,
                    "fan_power_w_cfm": 0.25,
                    "co_control": True,
                    "zone_assignment": "Parking_L01",
                },
            },
            "ev_charging": {
                "calgreen_2025": True,
                "dwelling_units": 200,
                "common_parking_spaces": 20,
                "alms_enabled": True,
            },
            "pools": [
                {
                    "name": "Main Pool",
                    "surface_area_sf": 800,
                    "pool_type": "commercial",
                    "heated": True,
                    "heater_type": "heat_pump",
                    "variable_speed_pump": True,
                }
            ],
        }
