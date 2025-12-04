"""
Internal Representation Module
Unified data structures for all format translations
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional


@dataclass
class Zone:
    """Universal zone representation"""
    id: str
    name: str
    building_type: str  # 'MF' or 'NR'
    zone_type: str = "commercial"  # 'residential', 'commercial', 'other_residential' (CBECC zone type)
    multiplier: int = 1
    floor_area_m2: Optional[float] = None
    volume_m3: Optional[float] = None
    stories_above: Optional[int] = None
    du_ref: Optional[str] = None
    space_function: Optional[str] = None  # Space function type (Phase 1 enhancement)
    conditioned: Optional[bool] = None  # True=conditioned, False=unconditioned, None=unknown
    served_by: List[str] = field(default_factory=list)
    surfaces: List[str] = field(default_factory=list)
    vertices: Optional[List[Dict[str, float]]] = None  # PolyLp floor polygon vertices [{x, y, z}, ...]
    annotation: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Surface:
    """Universal surface representation"""
    id: str
    name: str
    parent_zone_id: str
    surface_type: str  # 'wall', 'roof', 'floor'
    surface_subtype: Optional[str] = None  # CBECC subtype: 'res_ext_wall', 'res_int_wall', 'res_slab_floor', etc.
    tilt_deg: Optional[float] = None
    azimuth_deg: Optional[float] = None
    area_m2: Optional[float] = None
    perimeter_m: Optional[float] = None  # Perimeter (for slab-on-grade floors)
    vertices: Optional[List[Dict[str, float]]] = None  # PolyLp vertices for CIBD25 export: [{'x': float, 'y': float, 'z': float}, ...]
    construction_ref: Optional[str] = None
    adjacency: str = 'exterior'
    is_party_surface: bool = False  # CBECC party wall designation (ResIntWall)
    openings: List[str] = field(default_factory=list)
    # Thermal properties (Phase 1 enhancement)
    ext_solar_abs: Optional[float] = None  # Exterior solar absorptance (0-1)
    ext_thermal_abs: Optional[float] = None  # Exterior thermal absorptance (0-1)
    adjacent_space_ref: Optional[str] = None  # Adjacent space for interior surfaces (CBECC Outside field)
    annotation: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Opening:
    """Universal opening representation"""
    id: str
    parent_surface_id: str
    type: str  # 'window', 'door', 'skylight'
    area_m2: Optional[float] = None
    height_m: Optional[float] = None
    width_m: Optional[float] = None
    window_type_ref: Optional[str] = None
    fenestration_cons_ref: Optional[str] = None  # Fenestration construction reference (Phase 1 enhancement)
    u_factor_SI: Optional[float] = None
    shgc: Optional[float] = None
    vt: Optional[float] = None
    vertices: Optional[List[Dict[str, float]]] = None  # PolyLp geometry vertices [{x, y, z}, ...]
    annotation: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ZoneTerminal:
    """Zone terminal unit for central HVAC systems (CBECC ZnSys)"""
    id: str
    name: str
    parent_hvac_system_id: str
    zone_served_ref: str  # References Zone object (CRITICAL)
    terminal_type: str  # VAVR, FC, PTAC, PTHP, etc

    # Optional fields come after required fields
    floor_area_served: Optional[float] = None

    # Type-specific properties (VAVR - VAV with Reheat)
    min_cfm: Optional[float] = None
    reheat_type: Optional[str] = None
    reheat_source: Optional[str] = None

    # Type-specific properties (Fan Coil)
    coil_type: Optional[str] = None
    has_heating: bool = False
    has_cooling: bool = False

    # Type-specific properties (PTAC/PTHP)
    capacity_btuh: Optional[float] = None
    eer: Optional[float] = None
    hspf: Optional[float] = None

    annotation: Dict[str, Any] = field(default_factory=dict)


@dataclass
class HVACSystem:
    """Universal HVAC system representation (CBECC-compliant)"""
    id: str
    name: str

    # CBECC system classification (Phase 1.5)
    type: int  # 1=Heat+Cool, 2=HeatPump, 4=Central
    status: int = 3  # 1=Existing, 2=Altered, 3=New, 4=Mixed

    fuel: Optional[str] = None
    zone_refs: List[str] = field(default_factory=list)
    multiplier: int = 1

    # Equipment arrays with counts (CBECC Phase 1.5)
    heating_systems: List[str] = field(default_factory=list)
    heating_counts: List[int] = field(default_factory=list)

    cooling_systems: List[str] = field(default_factory=list)
    cooling_counts: List[int] = field(default_factory=list)

    heat_pump_systems: List[str] = field(default_factory=list)
    heat_pump_counts: List[int] = field(default_factory=list)

    central_equipment: List[str] = field(default_factory=list)
    central_counts: List[int] = field(default_factory=list)

    # Distribution & fan (single references)
    distribution_ref: Optional[str] = None
    fan_ref: Optional[str] = None

    # Zone terminal units for central systems (CBECC Phase 1.5)
    zone_terminals: List[str] = field(default_factory=list)  # References to ZoneTerminal IDs

    # Service tracking
    floor_area_served: Optional[float] = None

    # Legacy equipment properties (for backward compatibility)
    heating_source: Optional[str] = None
    cooling_source: Optional[str] = None
    distribution_type: Optional[str] = None

    annotation: Dict[str, Any] = field(default_factory=dict)

    @property
    def is_heat_pump(self) -> bool:
        """Check if system is heat pump type"""
        return self.type == 2

    @property
    def is_central(self) -> bool:
        """Check if system is central type"""
        return self.type == 4

    @property
    def has_separate_equipment(self) -> bool:
        """Check if system has separate heating/cooling equipment"""
        return self.type == 1


@dataclass
class WaterHeater:
    """Water heater equipment (CBECC Phase 2)"""
    id: str
    name: str
    heater_type: str  # 'Electric', 'Gas', 'HeatPump', 'Hybrid', 'Solar', 'Instantaneous'

    # Tank classification
    tank_type: Optional[str] = None  # 'Storage', 'Tankless', 'SmallStorage', 'LargeStorage'

    # Capacity
    storage_volume_gal: Optional[float] = None
    input_capacity_btu_hr: Optional[float] = None

    # Efficiency metrics (CBECC Phase 2)
    energy_factor: Optional[float] = None  # EF (legacy)
    uniform_energy_factor: Optional[float] = None  # UEF (current standard)
    thermal_efficiency: Optional[float] = None  # TE (instantaneous)
    first_hour_rating: Optional[float] = None  # FHR (gal/hr)
    recovery_efficiency: Optional[float] = None  # RE

    # Heat pump specific
    cop: Optional[float] = None  # Coefficient of performance
    compressor_location: Optional[str] = None  # 'Integral', 'External'

    # Installation
    fuel_type: Optional[str] = None  # 'Electric', 'NaturalGas', 'Propane', 'FuelOil'
    location: Optional[str] = None  # 'Conditioned', 'Unconditioned', 'Exterior'

    annotation: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RecirculationLoop:
    """DHW recirculation loop for central systems (CBECC Phase 2)"""
    id: str
    name: str
    parent_dhw_system_id: str

    # Loop configuration
    loop_type: str  # 'Central', 'Demand', 'Timer', 'TempSensor'
    pipe_length_ft: Optional[float] = None
    pipe_diameter_in: Optional[float] = None
    pipe_insulation_r_value: Optional[float] = None

    # Pump properties
    pump_power_w: Optional[float] = None
    flow_rate_gpm: Optional[float] = None

    # Control
    control_type: Optional[str] = None  # 'Continuous', 'Timer', 'Demand', 'Temperature'
    operating_hours_per_day: Optional[float] = None

    # Loss calculation
    heat_loss_btu_hr: Optional[float] = None

    annotation: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DHWSystem:
    """Universal DHW system representation (CBECC Phase 2 enhanced)"""
    id: str
    name: str
    system_type: str

    # Central DHW classification (CBECC Phase 2)
    is_central: bool = False
    central_system_type: Optional[str] = None  # 'Multifamily', 'Commercial', 'Residential'

    # Water heater arrays with counts (CBECC Phase 2)
    water_heaters: List[str] = field(default_factory=list)  # References to WaterHeater IDs
    water_heater_counts: List[int] = field(default_factory=list)  # Counts for each heater type

    # Recirculation loops (CBECC Phase 2)
    recirculation_loops: List[str] = field(default_factory=list)  # References to RecirculationLoop IDs

    # Distribution properties
    distribution_type: Optional[str] = None  # 'Compact', 'Standard', 'Recirculating'
    pipe_insulation_level: Optional[str] = None  # 'None', 'R2', 'R4', 'R6', 'R8'

    # Service tracking
    floor_area_served: Optional[float] = None
    dwelling_units_served: Optional[int] = None

    # Legacy properties (backward compatibility)
    recirc_type: Optional[str] = None
    requirements: List[str] = field(default_factory=list)

    annotation: Dict[str, Any] = field(default_factory=dict)

    @property
    def has_recirculation(self) -> bool:
        """Check if system has recirculation loops"""
        return len(self.recirculation_loops) > 0

    @property
    def total_heater_count(self) -> int:
        """Calculate total number of water heaters"""
        return sum(self.water_heater_counts) if self.water_heater_counts else 0


@dataclass
class ZoneGroup:
    """Zone group representation (floor, wing, etc.)"""
    id: str
    name: str
    group_type: str  # 'floor', 'wing', 'building'
    floor_number: Optional[int] = None
    floor_to_floor_height_m: Optional[float] = None
    floor_to_ceiling_height_m: Optional[float] = None
    z_coordinate_m: Optional[float] = None
    zone_refs: List[str] = field(default_factory=list)
    annotation: Dict[str, Any] = field(default_factory=dict)


@dataclass
class IAQFan:
    """Indoor Air Quality fan system"""
    id: str
    name: str
    fan_type: str
    airflow_cfm: Optional[float] = None
    power_w: Optional[float] = None
    zone_refs: List[str] = field(default_factory=list)
    annotation: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Material:
    """Construction material layer"""
    id: str
    name: str
    material_type: str
    thickness_m: Optional[float] = None
    r_value_SI: Optional[float] = None
    density_kg_m3: Optional[float] = None
    specific_heat: Optional[float] = None
    annotation: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Construction:
    """Construction assembly definition"""
    id: str
    name: str
    construction_type: str  # 'wall', 'roof', 'floor', 'ceiling'
    u_factor_SI: Optional[float] = None
    r_value_SI: Optional[float] = None
    material_layers: List[str] = field(default_factory=list)
    framing_config: Optional[str] = None
    framing_depth_m: Optional[float] = None
    framing_spacing_m: Optional[float] = None
    annotation: Dict[str, Any] = field(default_factory=dict)


@dataclass
class WindowType:
    """Window/fenestration type definition"""
    id: str
    name: str
    fenestration_type: str  # 'window', 'door', 'skylight'
    area_m2: Optional[float] = None  # Overall window area (for "Overall Window Area" spec method)
    u_factor_SI: Optional[float] = None
    shgc: Optional[float] = None
    vt: Optional[float] = None
    frame_type: Optional[str] = None
    glazing_type: Optional[str] = None
    num_panes: Optional[int] = None
    gas_fill: Optional[str] = None
    annotation: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PVArray:
    """Photovoltaic array system (CBECC Phase 3 enhanced)"""
    id: str
    name: str
    array_type: str  # 'FixedRoof', 'FixedGround', 'Tracking', 'BuildingIntegrated'

    # Module specification
    module_ref: Optional[str] = None
    module_type: Optional[str] = None  # 'Standard', 'Premium', 'ThinFilm'

    # System sizing
    rated_capacity_w: Optional[float] = None  # DC rating (Watts)
    rated_capacity_kw: Optional[float] = None  # DC rating (kW)
    num_modules: Optional[int] = None
    module_power_w: Optional[float] = None  # Individual module power

    # Array orientation
    tilt_deg: Optional[float] = None
    azimuth_deg: Optional[float] = None
    tracking_type: Optional[str] = None  # 'Fixed', '1-Axis', '2-Axis'

    # Inverter
    inverter_efficiency: Optional[float] = None
    inverter_type: Optional[str] = None  # 'String', 'Micro', 'Central', 'Hybrid'
    inverter_ref: Optional[str] = None

    # Installation
    location: Optional[str] = None  # 'Roof', 'Ground', 'Carport', 'Canopy'
    mounting_type: Optional[str] = None  # 'Flush', 'Standoff', 'Ballasted'

    # SARA (Solar Access Roof Area) - Title 24 specific
    sara_zone_ref: Optional[str] = None
    sara_area_m2: Optional[float] = None

    # Performance
    performance_ratio: Optional[float] = None  # Overall system efficiency
    dc_to_ac_ratio: Optional[float] = None
    annual_production_kwh: Optional[float] = None

    annotation: Dict[str, Any] = field(default_factory=dict)


@dataclass
class BatterySystem:
    """Battery energy storage system (CBECC Phase 3)"""
    id: str
    name: str
    battery_type: str  # 'LithiumIon', 'LeadAcid', 'Flow', 'Other'

    # Capacity
    usable_capacity_kwh: Optional[float] = None  # Usable energy capacity
    rated_capacity_kwh: Optional[float] = None  # Total capacity
    rated_power_kw: Optional[float] = None  # Maximum discharge rate

    # Efficiency
    round_trip_efficiency: Optional[float] = None  # Charge-discharge efficiency
    charge_efficiency: Optional[float] = None
    discharge_efficiency: Optional[float] = None

    # Control and operation
    control_strategy: Optional[str] = None  # 'SelfConsumption', 'TOU', 'Backup', 'GridServices'
    max_charge_rate_kw: Optional[float] = None
    max_discharge_rate_kw: Optional[float] = None

    # Depth of discharge
    min_state_of_charge: Optional[float] = None  # Minimum SOC (0-1)
    max_state_of_charge: Optional[float] = None  # Maximum SOC (0-1)

    # Integration
    coupled_pv_array_ref: Optional[str] = None  # Reference to PV array if DC-coupled
    coupling_type: Optional[str] = None  # 'DC', 'AC'

    # Installation
    location: Optional[str] = None  # 'Indoor', 'Outdoor', 'Garage'

    annotation: Dict[str, Any] = field(default_factory=dict)


@dataclass
class LightingSystem:
    """Interior lighting system"""
    id: str
    name: str
    system_type: str  # 'interior', 'exterior'
    space_ref: Optional[str] = None
    power_density_w_m2: Optional[float] = None
    total_power_w: Optional[float] = None
    control_type: Optional[str] = None
    luminaire_refs: List[str] = field(default_factory=list)
    schedule_ref: Optional[str] = None
    annotation: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Luminaire:
    """Individual luminaire/light fixture"""
    id: str
    name: str
    luminaire_type: str
    power_w: Optional[float] = None
    count: Optional[int] = None
    efficiency: Optional[float] = None
    lighting_system_ref: Optional[str] = None
    annotation: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Schedule:
    """Time-based schedule"""
    id: str
    name: str
    schedule_type: str  # 'day', 'week', 'year'
    data_type: Optional[str] = None  # 'fraction', 'temperature', 'on/off'
    values: List[float] = field(default_factory=list)
    hours: List[int] = field(default_factory=list)
    day_schedules: List[str] = field(default_factory=list)  # For week schedules
    annotation: Dict[str, Any] = field(default_factory=dict)


@dataclass
class FanSystem:
    """Residential fan system"""
    id: str
    name: str
    fan_type: str
    airflow_cfm: Optional[float] = None
    power_w: Optional[float] = None
    efficiency: Optional[float] = None
    control_method: Optional[str] = None
    zone_served: Optional[str] = None
    annotation: Dict[str, Any] = field(default_factory=dict)


@dataclass
class HeatPump:
    """Heat pump system"""
    id: str
    name: str
    pump_type: str  # 'air-source', 'ground-source', 'water-source'
    heating_capacity_w: Optional[float] = None
    cooling_capacity_w: Optional[float] = None
    heating_cop: Optional[float] = None
    cooling_eer: Optional[float] = None
    backup_fuel: Optional[str] = None
    zone_refs: List[str] = field(default_factory=list)
    annotation: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DistributionSystem:
    """HVAC distribution system"""
    id: str
    name: str
    distribution_type: str  # 'ducted', 'hydronic', 'ductless'
    duct_location: Optional[str] = None
    duct_insulation_r_value_SI: Optional[float] = None
    duct_leakage_pct: Optional[float] = None
    hvac_system_ref: Optional[str] = None
    annotation: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ControlSystem:
    """Control system (ventilation, economizer, etc.)"""
    id: str
    name: str
    control_type: str  # 'outdoor_air', 'economizer', 'demand', 'occupancy'
    control_method: Optional[str] = None
    setpoint_high: Optional[float] = None
    setpoint_low: Optional[float] = None
    system_ref: Optional[str] = None
    annotation: Dict[str, Any] = field(default_factory=dict)


@dataclass
class InternalRepresentation:
    """Complete internal representation of building model"""
    format_info: Optional[Any] = None
    proj_metadata: Dict[str, Any] = field(default_factory=dict)  # CBECC project metadata
    zones: List[Zone] = field(default_factory=list)
    zone_groups: List[ZoneGroup] = field(default_factory=list)
    surfaces: List[Surface] = field(default_factory=list)
    openings: List[Opening] = field(default_factory=list)
    hvac_systems: List[HVACSystem] = field(default_factory=list)
    zone_terminals: List[ZoneTerminal] = field(default_factory=list)  # CBECC Phase 1.5
    iaq_fans: List[IAQFan] = field(default_factory=list)
    dhw_systems: List[DHWSystem] = field(default_factory=list)
    water_heaters: List[WaterHeater] = field(default_factory=list)  # CBECC Phase 2
    recirculation_loops: List[RecirculationLoop] = field(default_factory=list)  # CBECC Phase 2
    materials: List[Material] = field(default_factory=list)
    constructions: List[Construction] = field(default_factory=list)
    window_types: List[WindowType] = field(default_factory=list)
    pv_arrays: List[PVArray] = field(default_factory=list)
    battery_systems: List[BatterySystem] = field(default_factory=list)  # CBECC Phase 3
    lighting_systems: List[LightingSystem] = field(default_factory=list)
    luminaires: List[Luminaire] = field(default_factory=list)
    schedules: List[Schedule] = field(default_factory=list)
    fan_systems: List[FanSystem] = field(default_factory=list)
    heat_pumps: List[HeatPump] = field(default_factory=list)
    distribution_systems: List[DistributionSystem] = field(default_factory=list)
    control_systems: List[ControlSystem] = field(default_factory=list)
    du_types: List[Dict] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    diagnostics: List[Dict] = field(default_factory=list)
    
    def all_objects(self):
        """Iterator over all objects"""
        for zone in self.zones:
            yield zone
        for surface in self.surfaces:
            yield surface
        for opening in self.openings:
            yield opening
        for hvac in self.hvac_systems:
            yield hvac
        for dhw in self.dhw_systems:
            yield dhw
    
    def all_references(self):
        """Get all reference fields"""
        refs = []
        for zone in self.zones:
            if zone.du_ref:
                refs.append(('Zone', zone.id, 'du_ref', zone.du_ref))
            refs.extend([('Zone', zone.id, 'served_by', ref) for ref in zone.served_by])
        for surface in self.surfaces:
            refs.append(('Surface', surface.id, 'parent_zone_id', surface.parent_zone_id))
            if surface.construction_ref:
                refs.append(('Surface', surface.id, 'construction_ref', surface.construction_ref))
        for opening in self.openings:
            refs.append(('Opening', opening.id, 'parent_surface_id', opening.parent_surface_id))
            if opening.window_type_ref:
                refs.append(('Opening', opening.id, 'window_type_ref', opening.window_type_ref))
        return refs
