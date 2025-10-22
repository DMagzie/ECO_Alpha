"""
CIBD22X Format Adapter
Handles CIBD22X format parsing and serialization
"""

import xml.etree.ElementTree as ET
from typing import List, Optional
from eco_tools.formats.base_adapter import BaseAdapter
from eco_tools.core.internal_repr import (
    InternalRepresentation, Zone, ZoneGroup, Surface, Opening,
    HVACSystem, IAQFan, DHWSystem, Material, Construction, WindowType, PVArray
)


class CIBD22XAdapter(BaseAdapter):
    """CIBD22X format: name as child <n> element"""
    
    def get_name(self, element: ET.Element) -> str:
        """Extract name from <n> child element"""
        name_elem = element.find('.//n')
        if name_elem is not None and name_elem.text:
            return name_elem.text.strip()
        
        # Fallback to Name child
        name_elem = element.find('.//Name')
        if name_elem is not None and name_elem.text:
            return name_elem.text.strip()
        
        # Last resort: id attribute
        return element.get('id', '')
    
    def get_property(self, element: ET.Element, prop_name: str) -> Optional[str]:
        """Extract property from child element"""
        prop_elem = element.find(f'.//{prop_name}')
        if prop_elem is not None and prop_elem.text:
            return prop_elem.text.strip()
        return None
    
    def parse(self, file_path: str) -> InternalRepresentation:
        """Parse CIBD22X file"""
        tree = ET.parse(file_path)
        root = tree.getroot()

        internal = InternalRepresentation()

        # Parse zone groups first (for hierarchy)
        internal.zone_groups = self._parse_zone_groups(root)

        # Parse zones
        internal.zones = self._parse_zones(root, internal.zone_groups)

        # Link zones back to zone groups
        self._link_zones_to_groups(internal.zones, internal.zone_groups)

        # Parse surfaces
        internal.surfaces = self._parse_surfaces(root, internal.zones)

        # Parse openings
        internal.openings = self._parse_openings(root, internal.surfaces)

        # Parse systems
        internal.hvac_systems = self._parse_hvac(root)
        internal.iaq_fans = self._parse_iaq_fans(root)
        internal.dhw_systems = self._parse_dhw(root)

        # Parse catalogs
        internal.materials = self._parse_materials(root)
        internal.constructions = self._parse_constructions(root)
        internal.window_types = self._parse_window_types(root)
        internal.pv_arrays = self._parse_pv_arrays(root)
        internal.du_types = self._parse_du_types(root)

        return internal
    
    def _parse_zone_groups(self, root: ET.Element) -> List[ZoneGroup]:
        """Parse zone groups (ResZnGrp) from CIBD22X"""
        zone_groups = []

        for zg_elem in root.findall('.//ResZnGrp'):
            name = self.get_name(zg_elem)
            if not name:
                name = "Zone Group"

            zg_id = self.id_registry.generate_id('ZG', name, '', 'CIBD22X')

            # Parse floor properties (convert ft to m)
            floor_to_floor_height_ft = self._to_float(self.get_property(zg_elem, 'FlrToFlrHgt'))
            floor_to_floor_height_m = (floor_to_floor_height_ft * 0.3048) if floor_to_floor_height_ft else None

            floor_to_ceiling_height_ft = self._to_float(self.get_property(zg_elem, 'FlrToCeilingHgt'))
            floor_to_ceiling_height_m = (floor_to_ceiling_height_ft * 0.3048) if floor_to_ceiling_height_ft else None

            z_coordinate_ft = self._to_float(self.get_property(zg_elem, 'Z'))
            z_coordinate_m = (z_coordinate_ft * 0.3048) if z_coordinate_ft else None

            zone_group = ZoneGroup(
                id=zg_id,
                name=name,
                group_type='floor',
                floor_to_floor_height_m=floor_to_floor_height_m,
                floor_to_ceiling_height_m=floor_to_ceiling_height_m,
                z_coordinate_m=z_coordinate_m,
                annotation={'xml_tag': 'ResZnGrp'}
            )

            zone_groups.append(zone_group)

        return zone_groups

    def _link_zones_to_groups(self, zones: List[Zone], zone_groups: List[ZoneGroup]):
        """Link zones back to their parent zone groups"""
        # Build zone group ID map
        zg_map = {zg.id: zg for zg in zone_groups}

        # Link zones to their groups
        for zone in zones:
            zg_id = zone.annotation.get('zone_group_id')
            if zg_id and zg_id in zg_map:
                zg_map[zg_id].zone_refs.append(zone.id)

    def _parse_zones(self, root: ET.Element, zone_groups: List[ZoneGroup]) -> List[Zone]:
        """Parse zones from CIBD22X"""
        zones = []
        zone_group_map = {zg.name: zg.id for zg in zone_groups}

        # Build parent map since ElementTree doesn't have parent navigation
        parent_map = {c: p for p in root.iter() for c in p}

        for zone_elem in root.iter():
            tag = self._local_tag(zone_elem.tag)
            if tag not in ('ResZn', 'ComZn', 'ResOtherZn'):
                continue

            name = self.get_name(zone_elem)
            if not name:
                continue

            zone_id = self.id_registry.generate_id('Z', name, '', 'CIBD22X')

            # Try to find parent zone group using parent map
            parent_zg_name = None
            parent_elem = parent_map.get(zone_elem)
            if parent_elem is not None:
                parent_tag = self._local_tag(parent_elem.tag)
                if parent_tag == 'ResZnGrp':
                    parent_zg_name = self.get_name(parent_elem)

            # Parse area (convert ft² to m²)
            area_ft2 = self._to_float(self.get_property(zone_elem, 'FloorArea'))
            area_m2 = (area_ft2 * 0.092903) if area_ft2 else None

            # Parse volume (convert ft³ to m³)
            vol_ft3 = self._to_float(self.get_property(zone_elem, 'Volume'))
            vol_m3 = (vol_ft3 * 0.0283168) if vol_ft3 else None

            # Parse multiplier
            mult = self._to_int(self.get_property(zone_elem, 'ZnMult')) or 1

            # Parse ceiling and floor heights (convert ft to m)
            ceiling_height_ft = self._to_float(self.get_property(zone_elem, 'CeilingHeight'))
            ceiling_height_m = (ceiling_height_ft * 0.3048) if ceiling_height_ft else None

            floor_height_ft = self._to_float(self.get_property(zone_elem, 'FloorHeight'))
            floor_height_m = (floor_height_ft * 0.3048) if floor_height_ft else None

            floor_z_ft = self._to_float(self.get_property(zone_elem, 'FloorZ'))
            floor_z_m = (floor_z_ft * 0.3048) if floor_z_ft else None

            # Parse zone type and references
            zone_type = self.get_property(zone_elem, 'Type')
            du_ref = self.get_property(zone_elem, 'DwellUnitTypeRef')

            # Determine building type
            building_type = 'MF' if tag == 'ResZn' else 'NR' if tag == 'ComZn' else 'OTHER'

            # Build annotation with additional properties
            annotation = {
                'xml_tag': tag,
                'zone_type': zone_type,
            }

            if ceiling_height_m:
                annotation['ceiling_height_m'] = ceiling_height_m
            if floor_height_m:
                annotation['floor_height_m'] = floor_height_m
            if floor_z_m:
                annotation['floor_z_m'] = floor_z_m
            if parent_zg_name:
                annotation['zone_group'] = parent_zg_name
                annotation['zone_group_id'] = zone_group_map.get(parent_zg_name)

            zone = Zone(
                id=zone_id,
                name=name,
                building_type=building_type,
                multiplier=mult,
                floor_area_m2=area_m2,
                volume_m3=vol_m3,
                du_ref=du_ref,
                annotation=annotation
            )

            zones.append(zone)

        return zones
    
    def _parse_surfaces(self, root: ET.Element, zones: List[Zone]) -> List[Surface]:
        """Parse surfaces from CIBD22X"""
        surfaces = []
        zone_map = {z.name: z.id for z in zones}

        # CIBD22X uses Res-prefixed surface tags
        surface_tags = [
            'ResExtWall', 'ResIntWall', 'ResIntFlr', 'ResSlabFlr',
            'ResCathedralCeiling', 'ResAtticRoof', 'ResOtherFlr',
            'ExtWall', 'IntWall', 'Roof', 'ExtFlr', 'IntFlr'  # Also support generic tags
        ]

        for zone_elem in root.iter():
            zone_tag = self._local_tag(zone_elem.tag)
            if zone_tag not in ('ResZn', 'ComZn', 'ResOtherZn'):
                continue

            zone_name = self.get_name(zone_elem)
            zone_id = zone_map.get(zone_name)
            if not zone_id:
                continue

            # Find surfaces in this zone
            for surf_tag in surface_tags:
                for surf_elem in zone_elem.findall(f'.//{surf_tag}'):
                    surf_name = self.get_name(surf_elem)
                    if not surf_name:
                        continue

                    surf_id = self.id_registry.generate_id('S', surf_name, zone_name, 'CIBD22X')

                    # Parse area (convert ft² to m²)
                    area_ft2 = self._to_float(self.get_property(surf_elem, 'Area'))
                    area_m2 = (area_ft2 * 0.092903) if area_ft2 else None

                    # Parse orientation
                    azimuth = self._to_float(self.get_property(surf_elem, 'Az'))
                    tilt = self._to_float(self.get_property(surf_elem, 'Tilt'))

                    # Parse construction reference
                    construction_ref = self.get_property(surf_elem, 'Construction')

                    # Determine surface type
                    surf_type = 'wall'
                    if 'Roof' in surf_tag or 'Ceiling' in surf_tag:
                        surf_type = 'roof'
                    elif 'Flr' in surf_tag or 'Floor' in surf_tag or 'Slab' in surf_tag:
                        surf_type = 'floor'

                    # Determine adjacency
                    adjacency = 'exterior'
                    if 'Int' in surf_tag:
                        adjacency = 'interior'
                    elif 'Ext' in surf_tag:
                        adjacency = 'exterior'
                    elif 'Attic' in surf_tag:
                        adjacency = 'attic'

                    surface = Surface(
                        id=surf_id,
                        name=surf_name,
                        parent_zone_id=zone_id,
                        surface_type=surf_type,
                        area_m2=area_m2,
                        tilt_deg=tilt,
                        azimuth_deg=azimuth,
                        construction_ref=construction_ref,
                        adjacency=adjacency,
                        annotation={'xml_tag': surf_tag}
                    )

                    surfaces.append(surface)

        return surfaces
    
    def _parse_openings(self, root: ET.Element, surfaces: List[Surface]) -> List[Opening]:
        """Parse openings from CIBD22X"""
        openings = []
        surface_map = {s.name: s.id for s in surfaces}

        # CIBD22X uses Res-prefixed opening tags
        opening_tags = ['ResWin', 'ResDoor', 'ResSkylt', 'Window', 'Door', 'Skylight', 'ComWin']

        # Surface tags that can contain openings
        surface_tags_with_openings = [
            'ResExtWall', 'ResIntWall', 'ResCathedralCeiling', 'ResAtticRoof',
            'ExtWall', 'IntWall', 'Roof', 'CathedralCeiling'
        ]

        # Iterate through surfaces to find openings
        for surf_elem in root.iter():
            surf_tag = self._local_tag(surf_elem.tag)
            if surf_tag not in surface_tags_with_openings:
                continue

            surf_name = self.get_name(surf_elem)
            surf_id = surface_map.get(surf_name)

            if not surf_id:
                continue

            # Find openings in this surface
            for open_tag in opening_tags:
                for open_elem in surf_elem.findall(f'.//{open_tag}'):
                    open_name = self.get_name(open_elem)
                    if not open_name:
                        continue

                    open_id = self.id_registry.generate_id('O', open_name, surf_name, 'CIBD22X')

                    # Parse dimensions (convert ft to m)
                    area_ft2 = self._to_float(self.get_property(open_elem, 'Area'))
                    area_m2 = (area_ft2 * 0.092903) if area_ft2 else None

                    height_ft = self._to_float(self.get_property(open_elem, 'Height'))
                    height_m = (height_ft * 0.3048) if height_ft else None

                    width_ft = self._to_float(self.get_property(open_elem, 'Width'))
                    width_m = (width_ft * 0.3048) if width_ft else None

                    # Parse window type reference
                    win_type_ref = self.get_property(open_elem, 'WinType')

                    # Parse fenestration properties
                    u_factor = self._to_float(self.get_property(open_elem, 'UFactor'))
                    shgc = self._to_float(self.get_property(open_elem, 'SHGC'))
                    vt = self._to_float(self.get_property(open_elem, 'VT'))

                    # Determine type
                    open_type = 'window'
                    if 'Door' in open_tag:
                        open_type = 'door'
                    elif 'Skylight' in open_tag or 'Skylt' in open_tag:
                        open_type = 'skylight'

                    opening = Opening(
                        id=open_id,
                        parent_surface_id=surf_id,
                        type=open_type,
                        area_m2=area_m2,
                        height_m=height_m,
                        width_m=width_m,
                        window_type_ref=win_type_ref,
                        u_factor_SI=u_factor,
                        shgc=shgc,
                        vt=vt,
                        annotation={'xml_tag': open_tag}
                    )

                    openings.append(opening)

        return openings
    
    def _parse_hvac(self, root: ET.Element) -> List[HVACSystem]:
        """Parse HVAC systems with equipment references"""
        systems = []

        for sys_elem in root.findall('.//ResHVACSys') + root.findall('.//ComHVACSys'):
            name = self.get_name(sys_elem)
            if not name:
                continue

            sys_id = self.id_registry.generate_id('H', name, '', 'CIBD22X')

            # Build detailed annotation
            annotation = {'xml_tag': self._local_tag(sys_elem.tag)}

            # Equipment references
            equipment_refs = [
                'HeatingEqpRef', 'CoolingEqpRef', 'DistribSysRef',
                'FanRef', 'CoilRef', 'AirSegRef', 'TrmlUnitRef'
            ]

            for ref in equipment_refs:
                value = self.get_property(sys_elem, ref)
                if value:
                    annotation[ref] = value

            # Heating equipment attributes
            heating_attrs = [
                'HtgSysType', 'HtgFuel', 'HtgCap', 'HtgEff', 'HtgAFUE',
                'HtgHSPF', 'HtgSSEER', 'HtgEIR', 'HtgCapFunTempCrvRef',
                'HtgCapFunFlowCrvRef', 'HtgEIRFunTempCrvRef', 'HtgEIRFunFlowCrvRef'
            ]

            for attr in heating_attrs:
                value = self.get_property(sys_elem, attr)
                if value:
                    annotation[attr] = value

            # Cooling equipment attributes
            cooling_attrs = [
                'ClgSysType', 'ClgCap', 'ClgEff', 'ClgSEER', 'ClgEER',
                'ClgCOP', 'ClgIEER', 'ClgCapFunTempCrvRef', 'ClgCapFunFlowCrvRef',
                'ClgEIRFunTempCrvRef', 'ClgEIRFunFlowCrvRef'
            ]

            for attr in cooling_attrs:
                value = self.get_property(sys_elem, attr)
                if value:
                    annotation[attr] = value

            # Fan and distribution attributes
            fan_attrs = [
                'FanType', 'FanCtrl', 'FanPwr', 'FanFlowCap',
                'DuctLoc', 'DuctInsulRValue', 'DuctLeakage',
                'SupAirflowRate', 'SupAirflowMethod'
            ]

            for attr in fan_attrs:
                value = self.get_property(sys_elem, attr)
                if value:
                    annotation[attr] = value

            # Control and operation attributes
            control_attrs = [
                'CtrlType', 'Thermostat', 'SetptHeat', 'SetptCool',
                'DeadBand', 'NightSetBack', 'EconomizerType'
            ]

            for attr in control_attrs:
                value = self.get_property(sys_elem, attr)
                if value:
                    annotation[attr] = value

            # Determine system type from available data
            system_type = self.get_property(sys_elem, 'Type')
            if not system_type or system_type == 'unknown':
                # Try to infer from heating/cooling system types
                htg_type = annotation.get('HtgSysType')
                clg_type = annotation.get('ClgSysType')
                if htg_type and clg_type:
                    system_type = f"{htg_type} + {clg_type}"
                elif htg_type:
                    system_type = htg_type
                elif clg_type:
                    system_type = clg_type
                else:
                    system_type = 'unknown'

            # Determine fuel from heating fuel if not specified
            fuel = self.get_property(sys_elem, 'Fuel')
            if not fuel:
                fuel = annotation.get('HtgFuel')

            system = HVACSystem(
                id=sys_id,
                name=name,
                type=system_type,
                fuel=fuel,
                annotation=annotation
            )

            systems.append(system)

        return systems
    
    def _parse_dhw(self, root: ET.Element) -> List[DHWSystem]:
        """Parse DHW systems"""
        systems = []

        for sys_elem in root.findall('.//ResDHWSys'):
            name = self.get_name(sys_elem)
            if not name:
                continue

            sys_id = self.id_registry.generate_id('D', name, '', 'CIBD22X')

            # Parse detailed DHW attributes
            annotation = {'xml_tag': 'ResDHWSys'}

            # Central system attributes
            central_dhw_type = self.get_property(sys_elem, 'CentralDHWType')
            central_recirc_type = self.get_property(sys_elem, 'CentralRecircType')

            # Central Heat Pump Water Heater (CHPWH) attributes
            chpwh_attrs = [
                'CHPWHSysDescrip', 'CHPWHCompType', 'CHPWHNumComp',
                'CHPWHTankCount', 'CHPWHTankLoc', 'CHPWHSrcAirLoc',
                'CHPWHLoopTankConfig', 'CHPWHCompCOP', 'CHPWHTankVol',
                'CHPWHCompCap', 'CHPWHRecoveryEff'
            ]

            # General DHW attributes
            general_attrs = [
                'DHWHeaterFuel', 'DHWHeaterType', 'DHWHeaterEF',
                'DHWStorageVol', 'DHWStorageTankUA', 'DHWPipeInsulLevel',
                'DHWPipeInsulType', 'DHWPumpPower'
            ]

            # Collect all attributes
            for attr in chpwh_attrs + general_attrs:
                value = self.get_property(sys_elem, attr)
                if value:
                    annotation[attr] = value

            # Add central type info if present
            if central_dhw_type:
                annotation['CentralDHWType'] = central_dhw_type
            if central_recirc_type:
                annotation['CentralRecircType'] = central_recirc_type

            # Determine system type from available data
            system_type = self.get_property(sys_elem, 'SystemType')
            if not system_type or system_type == 'unknown':
                if central_dhw_type:
                    system_type = central_dhw_type
                elif 'CHPWHCompType' in annotation:
                    system_type = 'Central Heat Pump Water Heater'
                else:
                    system_type = 'unknown'

            system = DHWSystem(
                id=sys_id,
                name=name,
                system_type=system_type,
                recirc_type=self.get_property(sys_elem, 'RecircType') or central_recirc_type,
                annotation=annotation
            )

            systems.append(system)

        return systems
    
    def _parse_window_types(self, root: ET.Element) -> List[WindowType]:
        """Parse window type catalog with full specifications"""
        window_types = []

        # Parse both residential and commercial fenestration types
        fenestration_tags = [
            'ResWinType', 'FenCons', 'WinType', 'DrType', 'SkylType'
        ]

        for tag in fenestration_tags:
            for wt_elem in root.findall(f'.//{tag}'):
                name = self.get_name(wt_elem)
                if not name:
                    name = f"Window Type {len(window_types) + 1}"

                wt_id = self.id_registry.generate_id('WT', name, '', 'CIBD22X')

                # Determine fenestration type from tag
                if 'Win' in tag:
                    fen_type = 'window'
                elif 'Dr' in tag or 'Door' in tag:
                    fen_type = 'door'
                elif 'Skyl' in tag:
                    fen_type = 'skylight'
                else:
                    fen_type = 'window'

                # Extract U-factor (convert Btu/h·ft²·°F to W/m²·K: multiply by 5.678)
                u_factor_ip = self._to_float(self.get_property(wt_elem, 'UFactor'))
                if not u_factor_ip:
                    u_factor_ip = self._to_float(self.get_property(wt_elem, 'UValue'))
                u_factor_SI = (u_factor_ip * 5.678) if u_factor_ip else None

                # Extract SHGC and VT (dimensionless, no conversion)
                shgc = self._to_float(self.get_property(wt_elem, 'SHGC'))
                vt = self._to_float(self.get_property(wt_elem, 'VT'))
                if not vt:
                    vt = self._to_float(self.get_property(wt_elem, 'VLT'))

                # Build annotation with detailed properties
                annotation = {'xml_tag': tag}

                # Frame properties
                frame_type = self.get_property(wt_elem, 'FrmType')
                if not frame_type:
                    frame_type = self.get_property(wt_elem, 'FrameType')

                # Glazing properties
                glazing_type = self.get_property(wt_elem, 'GlzgType')
                if not glazing_type:
                    glazing_type = self.get_property(wt_elem, 'GlazingType')

                # Number of panes
                num_panes = self._to_int(self.get_property(wt_elem, 'NumPanes'))
                if not num_panes:
                    num_panes = self._to_int(self.get_property(wt_elem, 'NumGlzgs'))

                # Gas fill
                gas_fill = self.get_property(wt_elem, 'GasFill')
                if not gas_fill:
                    gas_fill = self.get_property(wt_elem, 'GapFillType')

                # Additional properties
                additional_props = [
                    'Coating', 'LowECoating', 'TintType', 'FilmType',
                    'SpacerType', 'EdgeSeal', 'DividerType',
                    'ExteriorShade', 'InteriorShade', 'BetweenGlzShade',
                    'OperableArea', 'RatedUFactor', 'RatedSHGC', 'RatedVT',
                    'CertOrg', 'CertLabel', 'ProductType'
                ]

                for prop in additional_props:
                    value = self.get_property(wt_elem, prop)
                    if value:
                        annotation[prop] = value

                window_type = WindowType(
                    id=wt_id,
                    name=name,
                    fenestration_type=fen_type,
                    u_factor_SI=u_factor_SI,
                    shgc=shgc,
                    vt=vt,
                    frame_type=frame_type,
                    glazing_type=glazing_type,
                    num_panes=num_panes,
                    gas_fill=gas_fill,
                    annotation=annotation
                )

                window_types.append(window_type)

        return window_types
    
    def _parse_constructions(self, root: ET.Element) -> List[Construction]:
        """Parse construction assemblies with material layers"""
        constructions = []

        # Parse both residential and commercial construction assemblies
        construction_tags = [
            'ResConsAssm', 'ConsAssm', 'ExtWallCons', 'RoofCons',
            'FloorCons', 'SlabCons', 'CeilingCons'
        ]

        for tag in construction_tags:
            for cons_elem in root.findall(f'.//{tag}'):
                name = self.get_name(cons_elem)
                if not name:
                    name = f"Construction {len(constructions) + 1}"

                cons_id = self.id_registry.generate_id('CONS', name, '', 'CIBD22X')

                # Determine construction type from tag
                if 'Wall' in tag:
                    cons_type = 'wall'
                elif 'Roof' in tag or 'Ceiling' in tag:
                    cons_type = 'roof'
                elif 'Floor' in tag or 'Slab' in tag:
                    cons_type = 'floor'
                else:
                    cons_type = 'unknown'

                # Extract U-factor (convert Btu/h·ft²·°F to W/m²·K: multiply by 5.678)
                u_factor_ip = self._to_float(self.get_property(cons_elem, 'UFactor'))
                if not u_factor_ip:
                    u_factor_ip = self._to_float(self.get_property(cons_elem, 'UValue'))
                u_factor_SI = (u_factor_ip * 5.678) if u_factor_ip else None

                # Extract R-value (convert ft²·°F·h/Btu to m²·K/W: multiply by 0.1761)
                r_value_ip = self._to_float(self.get_property(cons_elem, 'RValue'))
                if not r_value_ip:
                    r_value_ip = self._to_float(self.get_property(cons_elem, 'RVal'))
                r_value_SI = (r_value_ip * 0.1761) if r_value_ip else None

                # Parse material layer references
                material_layers = []
                for mat_ref_elem in cons_elem.findall('.//MatRef'):
                    if mat_ref_elem.text:
                        material_layers.append(mat_ref_elem.text.strip())

                # Framing configuration
                framing_config = self.get_property(cons_elem, 'FrmCfg')
                if not framing_config:
                    framing_config = self.get_property(cons_elem, 'FrmAsm')

                # Framing depth (convert inches to meters)
                framing_depth_in = self._to_float(self.get_property(cons_elem, 'FrmDpth'))
                if not framing_depth_in:
                    framing_depth_in = self._to_float(self.get_property(cons_elem, 'FrmDepth'))
                framing_depth_m = (framing_depth_in * 0.0254) if framing_depth_in else None

                # Framing spacing (convert inches to meters)
                framing_spacing_in = self._to_float(self.get_property(cons_elem, 'FrmSpc'))
                if not framing_spacing_in:
                    framing_spacing_in = self._to_float(self.get_property(cons_elem, 'FrmSpacing'))
                framing_spacing_m = (framing_spacing_in * 0.0254) if framing_spacing_in else None

                # Build annotation with additional properties
                annotation = {'xml_tag': tag}

                # Additional construction properties
                additional_props = [
                    'ConsType', 'ExtRoughness', 'ExtSolAbs', 'ExtThmAbs',
                    'ExtVisAbs', 'IntSolAbs', 'IntThmAbs', 'IntVisAbs',
                    'CavityInsOpt', 'CavityInsDepth', 'CavityInsRVal',
                    'ContInsOpt', 'ContInsDepth', 'ContInsRVal',
                    'StudWidth', 'StudSpacing', 'NumLayers'
                ]

                for prop in additional_props:
                    value = self.get_property(cons_elem, prop)
                    if value:
                        annotation[prop] = value

                construction = Construction(
                    id=cons_id,
                    name=name,
                    construction_type=cons_type,
                    u_factor_SI=u_factor_SI,
                    r_value_SI=r_value_SI,
                    material_layers=material_layers,
                    framing_config=framing_config,
                    framing_depth_m=framing_depth_m,
                    framing_spacing_m=framing_spacing_m,
                    annotation=annotation
                )

                constructions.append(construction)

        return constructions
    
    def _parse_du_types(self, root: ET.Element) -> List[dict]:
        """Parse dwelling unit types"""
        types = []

        for du_elem in root.findall('.//DwellUnitType'):
            name = self.get_name(du_elem)
            if not name:
                continue

            types.append({
                'id': self.id_registry.generate_id('DU', name, '', 'CIBD22X'),
                'name': name,
                'floor_area': self._to_float(self.get_property(du_elem, 'FloorArea')),
            })

        return types

    def _parse_iaq_fans(self, root: ET.Element) -> List[IAQFan]:
        """Parse IAQ fan systems (ResIAQFan)"""
        iaq_fans = []

        for fan_elem in root.findall('.//ResIAQFan'):
            name = self.get_name(fan_elem)
            if not name:
                name = "IAQ Fan"

            fan_id = self.id_registry.generate_id('IAQ', name, '', 'CIBD22X')

            # Extract fan type
            fan_type = self.get_property(fan_elem, 'FanType')
            if not fan_type:
                fan_type = self.get_property(fan_elem, 'Type')
            if not fan_type:
                fan_type = 'Unknown'

            # Extract airflow (CFM)
            airflow_cfm = self._to_float(self.get_property(fan_elem, 'FlowRate'))
            if not airflow_cfm:
                airflow_cfm = self._to_float(self.get_property(fan_elem, 'Airflow'))

            # Extract power (W)
            power_w = self._to_float(self.get_property(fan_elem, 'FanPwr'))
            if not power_w:
                power_w = self._to_float(self.get_property(fan_elem, 'Power'))

            # Build annotation with all available properties
            annotation = {'xml_tag': 'ResIAQFan'}

            # Capture additional properties
            additional_props = [
                'FanCtrl', 'FanCtrlMethod', 'VentSysType', 'FanLoc',
                'DuctLoc', 'DuctInsul', 'DuctSurfArea', 'VentPreHtSrc',
                'VentPreCoolSrc', 'RecoveryEff'
            ]

            for prop in additional_props:
                value = self.get_property(fan_elem, prop)
                if value:
                    annotation[prop] = value

            iaq_fan = IAQFan(
                id=fan_id,
                name=name,
                fan_type=fan_type,
                airflow_cfm=airflow_cfm,
                power_w=power_w,
                annotation=annotation
            )

            iaq_fans.append(iaq_fan)

        return iaq_fans

    def _parse_materials(self, root: ET.Element) -> List[Material]:
        """Parse material layers (ResMat, Mat)"""
        materials = []

        # Parse both residential and commercial material tags
        material_tags = ['ResMat', 'Mat']

        for tag in material_tags:
            for mat_elem in root.findall(f'.//{tag}'):
                name = self.get_name(mat_elem)
                if not name:
                    name = "Material"

                mat_id = self.id_registry.generate_id('MAT', name, '', 'CIBD22X')

                # Extract material type
                mat_type = self.get_property(mat_elem, 'MatType')
                if not mat_type:
                    mat_type = self.get_property(mat_elem, 'Type')
                if not mat_type:
                    mat_type = 'Unknown'

                # Extract thickness (convert from inches to meters)
                thickness_in = self._to_float(self.get_property(mat_elem, 'Thickness'))
                thickness_m = (thickness_in * 0.0254) if thickness_in else None

                # Extract R-value (convert from IP to SI: R_SI = R_IP * 0.1761)
                r_value_ip = self._to_float(self.get_property(mat_elem, 'RValue'))
                if not r_value_ip:
                    r_value_ip = self._to_float(self.get_property(mat_elem, 'R'))
                r_value_SI = (r_value_ip * 0.1761) if r_value_ip else None

                # Extract density (lb/ft³ to kg/m³: multiply by 16.0185)
                density_lb_ft3 = self._to_float(self.get_property(mat_elem, 'Density'))
                density_kg_m3 = (density_lb_ft3 * 16.0185) if density_lb_ft3 else None

                # Extract specific heat (Btu/lb·°F to J/kg·K: multiply by 4186.8)
                spec_heat_ip = self._to_float(self.get_property(mat_elem, 'SpecHeat'))
                if not spec_heat_ip:
                    spec_heat_ip = self._to_float(self.get_property(mat_elem, 'SpecificHeat'))
                specific_heat = (spec_heat_ip * 4186.8) if spec_heat_ip else None

                # Build annotation with all available properties
                annotation = {'xml_tag': tag}

                # Capture additional thermal properties
                additional_props = [
                    'Conductivity', 'Absorptance', 'Emittance', 'Roughness',
                    'CodeCat', 'CodeItem', 'FrmAsm', 'FrmCfg', 'FrmDpth',
                    'FrmSpc', 'CavityInsOpt'
                ]

                for prop in additional_props:
                    value = self.get_property(mat_elem, prop)
                    if value:
                        annotation[prop] = value

                material = Material(
                    id=mat_id,
                    name=name,
                    material_type=mat_type,
                    thickness_m=thickness_m,
                    r_value_SI=r_value_SI,
                    density_kg_m3=density_kg_m3,
                    specific_heat=specific_heat,
                    annotation=annotation
                )

                materials.append(material)

        return materials

    def _parse_pv_arrays(self, root: ET.Element) -> List[PVArray]:
        """Parse photovoltaic (PV) array systems"""
        pv_arrays = []

        # Parse both residential and commercial PV system tags
        pv_tags = ['ResPVSys', 'PVArray', 'PVSys']

        for tag in pv_tags:
            for pv_elem in root.findall(f'.//{tag}'):
                name = self.get_name(pv_elem)
                if not name:
                    name = f"PV Array {len(pv_arrays) + 1}"

                pv_id = self.id_registry.generate_id('PV', name, '', 'CIBD22X')

                # Extract array type
                array_type = self.get_property(pv_elem, 'ArrayType')
                if not array_type:
                    array_type = self.get_property(pv_elem, 'Type')
                if not array_type:
                    array_type = 'Fixed'

                # Module reference
                module_ref = self.get_property(pv_elem, 'PVModRef')
                if not module_ref:
                    module_ref = self.get_property(pv_elem, 'ModuleRef')

                # Rated capacity (convert kW to W if needed)
                rated_capacity_kw = self._to_float(self.get_property(pv_elem, 'RatedCap'))
                if not rated_capacity_kw:
                    rated_capacity_kw = self._to_float(self.get_property(pv_elem, 'RatedPower'))
                rated_capacity_w = (rated_capacity_kw * 1000) if rated_capacity_kw else None

                # Number of modules
                num_modules = self._to_int(self.get_property(pv_elem, 'NumModules'))
                if not num_modules:
                    num_modules = self._to_int(self.get_property(pv_elem, 'ModuleCount'))

                # Tilt angle (degrees from horizontal)
                tilt_deg = self._to_float(self.get_property(pv_elem, 'Tilt'))
                if not tilt_deg:
                    tilt_deg = self._to_float(self.get_property(pv_elem, 'TiltAngle'))

                # Azimuth (degrees clockwise from north)
                azimuth_deg = self._to_float(self.get_property(pv_elem, 'Azimuth'))
                if not azimuth_deg:
                    azimuth_deg = self._to_float(self.get_property(pv_elem, 'Orientation'))

                # Tracking type
                tracking_type = self.get_property(pv_elem, 'TrackingType')
                if not tracking_type:
                    tracking_type = self.get_property(pv_elem, 'Tracking')

                # Inverter efficiency (0-1)
                inverter_eff = self._to_float(self.get_property(pv_elem, 'InvEff'))
                if not inverter_eff:
                    inverter_eff = self._to_float(self.get_property(pv_elem, 'InverterEfficiency'))

                # Location/mounting
                location = self.get_property(pv_elem, 'Location')
                if not location:
                    location = self.get_property(pv_elem, 'MountingType')

                # Build annotation with additional properties
                annotation = {'xml_tag': tag}

                # Additional PV system properties
                additional_props = [
                    'ModuleType', 'CellType', 'ModuleEff', 'TempCoeff',
                    'NOCT', 'ArrayArea', 'ArrayRows', 'ArrayCols',
                    'InverterType', 'InverterManufacturer', 'InverterModel',
                    'InverterRatedPower', 'MaxPowerTracker', 'DCtoACRatio',
                    'Shading', 'ShadingFactor', 'SoilingLoss', 'SystemLoss',
                    'GroundCoverageRatio', 'InterRowSpacing', 'CollectorWidth',
                    'BatterySystem', 'BatteryCapacity', 'BatteryRoundTripEff'
                ]

                for prop in additional_props:
                    value = self.get_property(pv_elem, prop)
                    if value:
                        annotation[prop] = value

                pv_array = PVArray(
                    id=pv_id,
                    name=name,
                    array_type=array_type,
                    module_ref=module_ref,
                    rated_capacity_w=rated_capacity_w,
                    num_modules=num_modules,
                    tilt_deg=tilt_deg,
                    azimuth_deg=azimuth_deg,
                    tracking_type=tracking_type,
                    inverter_efficiency=inverter_eff,
                    location=location,
                    annotation=annotation
                )

                pv_arrays.append(pv_array)

        return pv_arrays

    def serialize(self, internal: InternalRepresentation) -> ET.Element:
        """Serialize to CIBD22X XML"""
        root = ET.Element('Project')
        
        # Add project info
        info = ET.SubElement(root, 'ProjectInfo')
        site = ET.SubElement(info, 'Site')
        
        # Add building
        bldg = ET.SubElement(root, 'Building')
        
        # Add zones
        for zone in internal.zones:
            zone_tag = 'ResZn' if zone.building_type == 'MF' else 'ComZn'
            zn_elem = ET.SubElement(bldg, zone_tag, id=zone.id)
            
            n_elem = ET.SubElement(zn_elem, 'n')
            n_elem.text = zone.name
            
            if zone.floor_area_m2:
                area_elem = ET.SubElement(zn_elem, 'FloorArea')
                area_elem.text = str(zone.floor_area_m2 / 0.092903)  # Convert to ft²
            
            if zone.multiplier > 1:
                mult_elem = ET.SubElement(zn_elem, 'ZnMult')
                mult_elem.text = str(zone.multiplier)
        
        return root
    
    def write(self, element: ET.Element, output_path: str):
        """Write XML to file"""
        tree = ET.ElementTree(element)
        ET.indent(tree, space='  ')
        tree.write(output_path, encoding='utf-8', xml_declaration=True)
