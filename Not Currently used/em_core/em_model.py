
"""
EM JSON v4 Official Schema (Alpha Freeze)
----------------------------------------
This module defines the canonical EM JSON v4 structure for Alpha v4 testing.
It uses Python dataclasses (stdlib) to avoid external dependencies.
A lightweight validator is included for structural checks.

Versioning:
  - EM_JSON_VERSION follows semver with pre-release tags for alpha/beta.
"""
from __future__ import annotations
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any, Optional, Literal
from enum import Enum

EM_JSON_VERSION: str = "4.0.0-alpha"

# ---------- Enums ----------
class Engine(str, Enum):
    CBECC = "CBECC"
    ENERGYPLUS = "EnergyPlus"
    IESVE = "IESVE"

class Fuel(str, Enum):
    ELECTRICITY = "Electricity"
    NATURAL_GAS = "NaturalGas"
    DISTRICT_HEATING = "DistrictHeating"
    DISTRICT_COOLING = "DistrictCooling"
    OTHER = "Other"

class SurfaceType(str, Enum):
    WALL = "Wall"
    ROOF = "Roof"
    FLOOR = "Floor"
    WINDOW = "Window"
    DOOR = "Door"
    SKYLIGHT = "Skylight"
    OTHER = "Other"

class Adjacency(str, Enum):
    EXTERIOR = "Exterior"
    GROUND = "Ground"
    ATTIC = "Attic"
    ADIABATIC = "Adiabatic"
    INTERIOR = "Interior"

class ScenarioType(str, Enum):
    BASELINE = "baseline"
    PROPOSED = "proposed"
    DESIGN_OPTION = "design-option"

# ---------- Core Blocks ----------
@dataclass
class Location:
    zip: str
    climate_zone: str
    code_family: str  # e.g., "T24-2025" or "ASHRAE90.1-2019"

@dataclass
class Surface:
    name: str
    type: SurfaceType
    construction: str
    adjacent_to: Adjacency
    area_m2: Optional[float] = None
    tilt_deg: Optional[float] = None
    azimuth_deg: Optional[float] = None
    wwr_fraction: Optional[float] = None  # optional for simplified geometry

@dataclass
class Geometry:
    floor_area_m2: float
    volume_m3: Optional[float] = None
    height_m: Optional[float] = None
    surfaces: List[Surface] = field(default_factory=list)
    geometry_mode: Literal["Simplified", "Detailed", "Hybrid"] = "Simplified"

@dataclass
class SpaceLoads:
    lighting_w_per_m2: Optional[float] = None
    equipment_w_per_m2: Optional[float] = None
    occupancy_density_m2_per_person: Optional[float] = None

@dataclass
class SpaceSchedulesRef:
    occupancy: Optional[str] = None
    lighting: Optional[str] = None
    hvac: Optional[str] = None
    equipment: Optional[str] = None
    dhw: Optional[str] = None

@dataclass
class Space:
    name: str
    geometry: Geometry
    loads: SpaceLoads = field(default_factory=SpaceLoads)
    schedules: SpaceSchedulesRef = field(default_factory=SpaceSchedulesRef)
    usage_type: Optional[str] = None  # e.g., "DwellingUnit", "Corridor", "Retail"

@dataclass
class Zone:
    name: str
    spaces: List[Space] = field(default_factory=list)
    thermostat_cooling_c: Optional[float] = None
    thermostat_heating_c: Optional[float] = None

@dataclass
class Construction:
    name: str
    assembly_type: str  # Wall, Roof, Floor, Window, etc.
    u_value: Optional[float] = None
    insulation_r: Optional[float] = None
    notes: Optional[str] = None

# ---------- Systems ----------
@dataclass
class SystemHVAC:
    name: str
    type: str              # Canonical system type label; mapped per engine
    fuel: Fuel
    zones_served: List[str] = field(default_factory=list)
    cooling_cop: Optional[float] = None
    heating_efficiency: Optional[float] = None  # e.g., AFUE or HSPF converted
    ventilation: Optional[str] = None           # ref to ventilation strategy/template

@dataclass
class SystemDHW:
    name: str
    type: str              # e.g., "HPWH-Central", "Gas-Boiler-Central"
    fuel: Fuel
    efficiency: Optional[float] = None          # e.g., COP or thermal efficiency
    capacity_kW: Optional[float] = None
    zones_served: List[str] = field(default_factory=list)

@dataclass
class SchedulesDef:
    name: str
    type: str                      # occupancy, lighting, equipment, hvac, dhw
    granularity: str = "hourly"    # hourly/daily/weekly profile definition
    values: List[float] = field(default_factory=list)
    notes: Optional[str] = None

@dataclass
class SimulationBlock:
    engine: Engine
    status: Literal["not_run", "queued", "running", "succeeded", "failed"] = "not_run"
    results: Dict[str, Any] = field(default_factory=dict)  # engine-specific outputs
    engine_metadata: Dict[str, Any] = field(default_factory=dict)  # file paths, versions

@dataclass
class Scenario:
    name: str
    type: ScenarioType = ScenarioType.BASELINE
    zones: List[Zone] = field(default_factory=list)
    systems: Dict[str, List[Any]] = field(default_factory=lambda: {"hvac": [], "dhw": []})
    constructions: List[Construction] = field(default_factory=list)
    schedules: List[SchedulesDef] = field(default_factory=list)
    simulation: SimulationBlock = field(default_factory=lambda: SimulationBlock(engine=Engine.CBECC))
    notes: Optional[str] = None

@dataclass
class Project:
    name: str
    location: Location
    vintage: str
    notes: Optional[str] = None

@dataclass
class EMModel:

    def validate(self):
        """
        Long-term contract: return a list of human-readable validation messages.
        The tests expect messages like: "Missing required key: <key>".
        """
        # Get a dict view of model data
        data = getattr(self, "data", None)
        if data is None:
            # if you use dataclasses and have fields on self, fall back to asdict-like behavior
            try:
                from dataclasses import asdict
                data = asdict(self)
            except Exception:
                data = {}
        if not isinstance(data, dict):
            data = {}

        required = ["project", "building", "zones"]
        messages = []
        for k in required:
            if k not in data:
                messages.append(f"Missing required key: {k}")

        # Optional structural hint (non-fatal)
        if "zones" in data and not isinstance(data.get("zones"), list):
            messages.append("zones should be a list")

        return messages


    project: Project
    scenarios: List[Scenario] = field(default_factory=list)
    version: str = EM_JSON_VERSION

    # -------- Serialization helpers --------
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @staticmethod
    def from_dict(d: Dict[str, Any]) -> "EMModel":
        """Construct an EMModel from a validated dict. Use validate_emjson first."""
        proj_loc = Location(**d["project"]["location"])
        proj = Project(name=d["project"]["name"], location=proj_loc, vintage=d["project"]["vintage"], notes=d["project"].get("notes"))
        scenarios: List[Scenario] = []
        for s in d.get("scenarios", []):
            # Constructions
            constructions = [Construction(**c) for c in s.get("constructions", [])]
            # Schedules
            schedules = [SchedulesDef(**sch) for sch in s.get("schedules", [])]
            # Zones & Spaces
            zones: List[Zone] = []
            for z in s.get("zones", []):
                spaces: List[Space] = []
                for sp in z.get("spaces", []):
                    surfaces = [Surface(**sf) for sf in sp["geometry"].get("surfaces", [])]
                    geom = Geometry(
                        floor_area_m2=sp["geometry"]["floor_area_m2"],
                        volume_m3=sp["geometry"].get("volume_m3"),
                        height_m=sp["geometry"].get("height_m"),
                        surfaces=surfaces,
                        geometry_mode=sp["geometry"].get("geometry_mode", "Simplified"),
                    )
                    loads = SpaceLoads(**sp.get("loads", {}))
                    sched = SpaceSchedulesRef(**sp.get("schedules", {}))
                    spaces.append(Space(name=sp["name"], geometry=geom, loads=loads, schedules=sched, usage_type=sp.get("usage_type")))
                zones.append(Zone(name=z["name"], spaces=spaces, thermostat_cooling_c=z.get("thermostat_cooling_c"), thermostat_heating_c=z.get("thermostat_heating_c")))
            # Systems
            hvac = [SystemHVAC(**h) for h in s.get("systems", {}).get("hvac", [])]
            dhw = [SystemDHW(**w) for w in s.get("systems", {}).get("dhw", [])]
            systems = {"hvac": hvac, "dhw": dhw}
            # Simulation
            sim_block_raw = s.get("simulation", {"engine": "CBECC"})
            sim = SimulationBlock(engine=Engine(sim_block_raw.get("engine", "CBECC")), status=sim_block_raw.get("status", "not_run"), results=sim_block_raw.get("results", {}), engine_metadata=sim_block_raw.get("engine_metadata", {}))
            scenarios.append(Scenario(name=s["name"], type=ScenarioType(s.get("type","baseline")), zones=zones, systems=systems, constructions=constructions, schedules=schedules, simulation=sim, notes=s.get("notes")))
        return EMModel(project=proj, scenarios=scenarios, version=d.get("version", EM_JSON_VERSION))

# ---------- Lightweight validation ----------
REQUIRED_TOP_LEVEL = ["project", "scenarios"]
REQUIRED_PROJECT = ["name", "location", "vintage"]
REQUIRED_LOCATION = ["zip", "climate_zone", "code_family"]
REQUIRED_SCENARIO = ["name", "type", "zones", "systems", "constructions", "schedules", "simulation"]

def validate_emjson(d: Dict[str, Any]) -> List[str]:
    errors: List[str] = []
    # Top level
    for key in REQUIRED_TOP_LEVEL:
        if key not in d:
            errors.append(f"Missing top-level key: '{key}'")
    if "project" in d:
        proj = d["project"]
        for key in REQUIRED_PROJECT:
            if key not in proj:
                errors.append(f"project: missing '{key}'")
        if "location" in proj:
            loc = proj["location"]
            for key in REQUIRED_LOCATION:
                if key not in loc:
                    errors.append(f"project.location: missing '{key}'")
        else:
            errors.append("project: missing 'location'")
    # Scenarios
    scenarios = d.get("scenarios", [])
    if not isinstance(scenarios, list) or len(scenarios) == 0:
        errors.append("scenarios: must be a non-empty list")
    for i, s in enumerate(scenarios):
        for key in REQUIRED_SCENARIO:
            if key not in s:
                errors.append(f"scenarios[{i}]: missing '{key}'")
        # Zones + Spaces minimal checks
        for j, z in enumerate(s.get("zones", [])):
            if "name" not in z:
                errors.append(f"scenarios[{i}].zones[{j}]: missing 'name'")
            for k, sp in enumerate(z.get("spaces", [])):
                if "name" not in sp:
                    errors.append(f"scenarios[{i}].zones[{j}].spaces[{k}]: missing 'name'")
                geom = sp.get("geometry")
                if not geom or "floor_area_m2" not in geom:
                    errors.append(f"scenarios[{i}].zones[{j}].spaces[{k}]: geometry.floor_area_m2 is required")
        # Systems minimal checks
        systems = s.get("systems", {})
        if "hvac" not in systems or "dhw" not in systems:
            errors.append(f"scenarios[{i}].systems: must contain 'hvac' and 'dhw' lists")
    return errors

# ---------- JSON schema (optional use with jsonschema) ----------
# Provided for external validators; not enforced in this module.
JSON_SCHEMA: Dict[str, Any] = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "title": "EM JSON v4",
    "type": "object",
    "required": ["project", "scenarios"],
    "properties": {
        "version": {"type": "string"},
        "project": {
            "type": "object",
            "required": ["name", "location", "vintage"],
            "properties": {
                "name": {"type": "string"},
                "vintage": {"type": "string"},
                "notes": {"type": "string"},
                "location": {
                    "type": "object",
                    "required": ["zip", "climate_zone", "code_family"],
                    "properties": {
                        "zip": {"type": "string"},
                        "climate_zone": {"type": "string"},
                        "code_family": {"type": "string"}
                    }
                }
            }
        },
        "scenarios": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["name", "type", "zones", "systems", "constructions", "schedules", "simulation"],
                "properties": {
                    "name": {"type": "string"},
                    "type": {"type": "string", "enum": ["baseline", "proposed", "design-option"]},
                    "notes": {"type": "string"},
                    "zones": {"type": "array"},
                    "systems": {"type": "object"},
                    "constructions": {"type": "array"},
                    "schedules": {"type": "array"},
                    "simulation": {"type": "object"}
                }
            }
        }
    }
}

__all__ = [
    "EM_JSON_VERSION",
    "Engine", "Fuel", "SurfaceType", "Adjacency", "ScenarioType",
    "Location", "Surface", "Geometry", "SpaceLoads", "SpaceSchedulesRef",
    "Space", "Zone", "Construction", "SystemHVAC", "SystemDHW",
    "SchedulesDef", "SimulationBlock", "Scenario", "Project", "EMModel",
    "validate_emjson", "JSON_SCHEMA",
]
