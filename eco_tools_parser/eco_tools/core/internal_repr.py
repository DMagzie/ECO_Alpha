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
    multiplier: int = 1
    floor_area_m2: Optional[float] = None
    volume_m3: Optional[float] = None
    stories_above: Optional[int] = None
    du_ref: Optional[str] = None
    served_by: List[str] = field(default_factory=list)
    surfaces: List[str] = field(default_factory=list)
    annotation: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Surface:
    """Universal surface representation"""
    id: str
    name: str
    parent_zone_id: str
    surface_type: str  # 'wall', 'roof', 'floor'
    tilt_deg: Optional[float] = None
    azimuth_deg: Optional[float] = None
    area_m2: Optional[float] = None
    construction_ref: Optional[str] = None
    adjacency: str = 'exterior'
    openings: List[str] = field(default_factory=list)
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
    u_factor_SI: Optional[float] = None
    shgc: Optional[float] = None
    vt: Optional[float] = None
    annotation: Dict[str, Any] = field(default_factory=dict)


@dataclass
class HVACSystem:
    """Universal HVAC system representation"""
    id: str
    name: str
    type: str
    fuel: Optional[str] = None
    zone_refs: List[str] = field(default_factory=list)
    multiplier: int = 1
    annotation: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DHWSystem:
    """Universal DHW system representation"""
    id: str
    name: str
    system_type: str
    recirc_type: Optional[str] = None
    requirements: List[str] = field(default_factory=list)
    annotation: Dict[str, Any] = field(default_factory=dict)


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
    """Photovoltaic array system"""
    id: str
    name: str
    array_type: str
    module_ref: Optional[str] = None
    rated_capacity_w: Optional[float] = None
    num_modules: Optional[int] = None
    tilt_deg: Optional[float] = None
    azimuth_deg: Optional[float] = None
    tracking_type: Optional[str] = None
    inverter_efficiency: Optional[float] = None
    location: Optional[str] = None
    annotation: Dict[str, Any] = field(default_factory=dict)


@dataclass
class InternalRepresentation:
    """Complete internal representation of building model"""
    format_info: Optional[Any] = None
    zones: List[Zone] = field(default_factory=list)
    zone_groups: List[ZoneGroup] = field(default_factory=list)
    surfaces: List[Surface] = field(default_factory=list)
    openings: List[Opening] = field(default_factory=list)
    hvac_systems: List[HVACSystem] = field(default_factory=list)
    iaq_fans: List[IAQFan] = field(default_factory=list)
    dhw_systems: List[DHWSystem] = field(default_factory=list)
    materials: List[Material] = field(default_factory=list)
    constructions: List[Construction] = field(default_factory=list)
    window_types: List[WindowType] = field(default_factory=list)
    pv_arrays: List[PVArray] = field(default_factory=list)
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
