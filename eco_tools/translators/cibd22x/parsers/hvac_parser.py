"""
HVACSystem Parser - Composite Parser (Creates Multiple Element Types)
=====================================================================

PURPOSE: Extracts HVAC system configurations from CIBD22X XML.
This is a COMPOSITE PARSER that creates TWO element types:
1. HVACSystem (the system itself)
2. ZoneTerminal (nested zone-level terminals)

PATTERN: Composite Parser - See dhw_parser.py for detailed documentation.

COMPOSITE STRUCTURE:
<HVACSys>                        → HVACSystem
  <ZnSys>...</ZnSys>             → ZoneTerminal (links zone to HVAC)
  <ZnSys>...</ZnSys>             → ZoneTerminal
</HVACSys>

KEY OPERATIONS:
- Parse HVAC system type (split, packaged, VAV, etc.)
- Extract equipment references (heat pumps, fans, distribution, controls)
- Parse nested zone terminals (which zones this system serves)
- POST-PROCESSING: Link zones to HVAC systems (see cibd22x_importer.py)

RETURNS: Tuple[List[HVACSystem], List[ZoneTerminal]]
"""

from typing import List, Optional, Tuple
import xml.etree.ElementTree as ET
import logging

from eco_tools.core.internal_repr import HVACSystem, ZoneTerminal, Zone
from eco_tools.core.id_registry import IDRegistry
from .base_parser import BaseParser

# Get module logger
logger = logging.getLogger('eco_tools.parsers')


class HVACSystemParser(BaseParser):
    """Parser for CIBD22X HVAC system elements"""

    HVAC_SYSTEM_TAGS = [
        'ResHVACSys',   # Residential HVAC systems
        'ComHVACSys',   # Commercial HVAC systems
        'HVACSys',      # Generic HVAC systems
        'AirSeg',       # Air segments (CBECC-Com)
        'TrmlUnit',     # Terminal units (CBECC-Com)
    ]

    def __init__(self, id_registry: IDRegistry):
        super().__init__()
        self.id_registry = id_registry

    def parse_hvac_systems(self, root: ET.Element) -> Tuple[List[HVACSystem], List[ZoneTerminal]]:
        """
        Parse all HVAC systems from CIBD22X.

        Returns:
            tuple: (List[HVACSystem], List[ZoneTerminal])
        """
        systems = []
        all_zone_terminals = []

        # Parse residential, commercial, and generic HVAC systems
        for sys_elem in (root.findall('.//ResHVACSys') +
                         root.findall('.//ComHVACSys') +
                         root.findall('.//HVACSys')):
            hvac_sys, zone_terminals = self._parse_hvac_system(sys_elem)
            if hvac_sys:
                systems.append(hvac_sys)
                all_zone_terminals.extend(zone_terminals)

        # Parse CBECC-Com air segments
        for airseg in root.findall('.//AirSeg'):
            hvac_sys = self._parse_air_segment(airseg)
            if hvac_sys:
                systems.append(hvac_sys)

        # Parse CBECC-Com terminal units
        terminals = self._parse_terminal_units(root, systems)
        all_zone_terminals.extend(terminals)

        logger.info(f"Parsed {len(systems)} HVAC systems and {len(all_zone_terminals)} zone terminals")
        return systems, all_zone_terminals

    def _parse_hvac_system(self, sys_elem: ET.Element) -> Tuple[Optional[HVACSystem], List[ZoneTerminal]]:
        """Parse a single HVAC system element (ResHVACSys, ComHVACSys, HVACSys)."""
        name = self._get_name(sys_elem)
        if not name:
            return None, []

        sys_id = self.id_registry.generate_id('H', name, '', 'CIBD22X')

        # Parse system type (CBECC: 1=Heat+Cool, 2=HeatPump, 4=Central)
        system_type_str = self.get_property(sys_elem, 'Type')
        system_type = self._parse_hvac_type(system_type_str, sys_elem)

        # Parse status (CBECC: 1=Existing, 2=Altered, 3=New, 4=Mixed)
        status_str = self.get_property(sys_elem, 'Status')
        status = self._parse_status(status_str)

        # Parse fuel type
        fuel = self.get_property(sys_elem, 'Fuel')

        # Parse equipment arrays with counts (CBECC Phase 1.5)
        heating_systems, heating_counts = self._parse_equipment_array(sys_elem, 'HeatSystem', 'HeatSystemCount')
        cooling_systems, cooling_counts = self._parse_equipment_array(sys_elem, 'CoolSystem', 'CoolSystemCount')
        heat_pump_systems, heat_pump_counts = self._parse_equipment_array(sys_elem, 'HtPumpSystem', 'HtPumpSystemCount')
        central_equipment, central_counts = self._parse_equipment_array(sys_elem, 'HVACCentralRef', 'CentralEquipCount')

        # Parse distribution & fan (single references)
        distribution_ref = self.get_property(sys_elem, 'DistribSystem')
        fan_ref = self.get_property(sys_elem, 'Fan')

        # Parse floor area served
        floor_area_served = self._to_float(self.get_property(sys_elem, 'FloorAreaServed'))

        # Parse zone terminals for central systems (CBECC Phase 1.5)
        zone_terminals = self._parse_zone_terminals(sys_elem, sys_id)
        zone_terminal_ids = [zt.id for zt in zone_terminals]

        # Build annotation with additional properties
        annotation = {'xml_tag': self._local_tag(sys_elem.tag)}

        # CRITICAL: Store original Type text for round-trip export
        # The parser converts descriptive text to numeric codes, but we need the original text
        if system_type_str:
            annotation['system_type_text'] = system_type_str

        # Store original Status text for round-trip export
        if status_str:
            annotation['status_text'] = status_str

        # Store heat pump system references with indices for export
        if heat_pump_systems:
            ht_pump_refs = []
            for i, (ht_pump_name, count) in enumerate(zip(heat_pump_systems, heat_pump_counts)):
                ht_pump_refs.append({
                    'name': ht_pump_name,
                    'index': i,
                    'count': count
                })
            annotation['ht_pump_system_refs'] = ht_pump_refs

        # Store equipment type counts
        if heating_systems:
            annotation['NumHeatSystemTypes'] = len(heating_systems)
        if cooling_systems:
            annotation['NumCoolSystemTypes'] = len(cooling_systems)
        if heat_pump_systems:
            annotation['NumHtPumpSystemTypes'] = len(heat_pump_systems)
        if central_equipment:
            annotation['NumCentralEquipTypes'] = len(central_equipment)

        # Legacy properties for backward compatibility
        heating_source = annotation.get('HtgSysType')
        cooling_source = annotation.get('ClgSysType')
        distribution_type = distribution_ref if distribution_ref else None

        system = HVACSystem(
            id=sys_id,
            name=name,
            type=system_type,
            status=status,
            fuel=fuel,
            heating_systems=heating_systems,
            heating_counts=heating_counts,
            cooling_systems=cooling_systems,
            cooling_counts=cooling_counts,
            heat_pump_systems=heat_pump_systems,
            heat_pump_counts=heat_pump_counts,
            central_equipment=central_equipment,
            central_counts=central_counts,
            distribution_ref=distribution_ref,
            fan_ref=fan_ref,
            zone_terminals=zone_terminal_ids,
            floor_area_served=floor_area_served,
            heating_source=heating_source,
            cooling_source=cooling_source,
            distribution_type=distribution_type,
            annotation=annotation
        )

        return system, zone_terminals

    def _parse_air_segment(self, airseg: ET.Element) -> Optional[HVACSystem]:
        """Parse CBECC-Com AirSeg element."""
        name = self._get_name(airseg)
        if not name:
            return None

        sys_id = self.id_registry.generate_id('H', name, '', 'CIBD22X')

        # AirSeg Type: Supply, Return, Exhaust, Relief
        seg_type = self.get_property(airseg, 'Type')

        # For CBECC air systems, determine system type based on equipment
        system_type = 4  # Central system (CBECC type 4)
        status = 3  # New (default)

        # Check for coils to determine if it has heating/cooling
        has_heating_coil = airseg.find('.//CoilHtg') is not None
        has_cooling_coil = airseg.find('.//CoilClg') is not None

        # Parse coil references
        heating_coils = []
        for coil_htg in airseg.findall('.//CoilHtg'):
            coil_name = self._get_name(coil_htg)
            if coil_name:
                heating_coils.append(coil_name)

        cooling_coils = []
        for coil_clg in airseg.findall('.//CoilClg'):
            coil_name = self._get_name(coil_clg)
            if coil_name:
                cooling_coils.append(coil_name)

        # Parse fan references
        fan_refs = []
        for fan in airseg.findall('.//Fan'):
            fan_name = self._get_name(fan)
            if fan_name:
                fan_refs.append(fan_name)

        # Build annotation
        annotation = {
            'xml_tag': 'AirSeg',
            'segment_type': seg_type,
            'has_heating_coil': has_heating_coil,
            'has_cooling_coil': has_cooling_coil,
            'heating_coils': heating_coils,
            'cooling_coils': cooling_coils,
            'fans': fan_refs
        }

        system = HVACSystem(
            id=sys_id,
            name=name,
            type=system_type,
            status=status,
            fuel=None,  # Determined by coil fuel types
            heating_systems=heating_coils,
            heating_counts=[1] * len(heating_coils),
            cooling_systems=cooling_coils,
            cooling_counts=[1] * len(cooling_coils),
            central_equipment=[],
            central_counts=[],
            fan_ref=fan_refs[0] if fan_refs else None,
            annotation=annotation
        )

        return system

    def _parse_terminal_units(self, root: ET.Element, systems: List[HVACSystem]) -> List[ZoneTerminal]:
        """Parse CBECC-Com TrmlUnit elements (terminal units / zone systems)."""
        terminals = []

        for trml in root.findall('.//TrmlUnit'):
            name = self._get_name(trml)
            if not name:
                continue

            term_id = self.id_registry.generate_id('ZT', name, '', 'CIBD22X')

            # Terminal type: Uncontrolled, VAV, etc.
            term_type = self.get_property(trml, 'Type')

            # Zone served reference
            zone_served_ref = self.get_property(trml, 'ZnServedRef')

            # Primary air segment reference (links to AirSeg/HVAC system)
            pri_air_seg_ref = self.get_property(trml, 'PriAirSegRef')

            # Find parent HVAC system ID
            parent_hvac_id = None
            if pri_air_seg_ref:
                # Find the HVACSystem we created for this AirSeg
                for sys in systems:
                    if sys.name == pri_air_seg_ref:
                        parent_hvac_id = sys.id
                        break

            # If we found the parent system, create terminal
            if parent_hvac_id and zone_served_ref:
                terminal = ZoneTerminal(
                    id=term_id,
                    name=name,
                    parent_hvac_system_id=parent_hvac_id,
                    zone_served_ref=zone_served_ref,
                    terminal_type=term_type or 'Uncontrolled',
                    annotation={
                        'xml_tag': 'TrmlUnit',
                        'pri_air_seg_ref': pri_air_seg_ref
                    }
                )

                terminals.append(terminal)

                # Add terminal to parent system's zone_terminals list
                for sys in systems:
                    if sys.id == parent_hvac_id:
                        sys.zone_terminals.append(term_id)
                        break

        return terminals

    def _parse_zone_terminals(self, sys_elem: ET.Element, hvac_system_id: str) -> List[ZoneTerminal]:
        """Parse zone terminal units (ZnSys) for central HVAC systems (Phase 1.5)."""
        terminals = []

        for zn_elem in sys_elem.findall('.//ZnSys'):
            name = self._get_name(zn_elem)
            if not name:
                continue

            terminal_id = self.id_registry.generate_id('ZT', name, hvac_system_id, 'CIBD22X')

            # Zone connection (CRITICAL)
            zone_served_ref = self.get_property(zn_elem, 'ZnServedRef')
            if not zone_served_ref:
                continue  # Skip terminals without zone reference

            # Terminal type
            terminal_type = self.get_property(zn_elem, 'Type')
            if not terminal_type:
                terminal_type = 'Unknown'

            # Floor area served (convert ft² to m²)
            floor_area_ft2 = self._to_float(self.get_property(zn_elem, 'FloorAreaServed'))
            floor_area_m2 = (floor_area_ft2 * 0.092903) if floor_area_ft2 else None

            # Type-specific properties - VAVR (VAV with Reheat)
            min_cfm = self._to_float(self.get_property(zn_elem, 'MinCFM'))
            reheat_type = self.get_property(zn_elem, 'ReheatType')
            reheat_source = self.get_property(zn_elem, 'ReheatSource')

            # Type-specific properties - Fan Coil
            coil_type = self.get_property(zn_elem, 'CoilType')
            has_heating = self.get_property(zn_elem, 'Heating') == '1'
            has_cooling = self.get_property(zn_elem, 'Cooling') == '1'

            # Type-specific properties - PTAC/PTHP
            capacity_btuh = self._to_float(self.get_property(zn_elem, 'Capacity'))
            eer = self._to_float(self.get_property(zn_elem, 'EER'))
            hspf = self._to_float(self.get_property(zn_elem, 'HSPF'))

            # Build annotation
            annotation = {'xml_tag': 'ZnSys'}

            terminal = ZoneTerminal(
                id=terminal_id,
                name=name,
                parent_hvac_system_id=hvac_system_id,
                zone_served_ref=zone_served_ref,
                floor_area_served=floor_area_m2,
                terminal_type=terminal_type,
                min_cfm=min_cfm,
                reheat_type=reheat_type,
                reheat_source=reheat_source,
                coil_type=coil_type,
                has_heating=has_heating,
                has_cooling=has_cooling,
                capacity_btuh=capacity_btuh,
                eer=eer,
                hspf=hspf,
                annotation=annotation
            )

            terminals.append(terminal)

        return terminals

    def link_zones_to_hvac(self, root: ET.Element, zones: List[Zone],
                          hvac_systems: List[HVACSystem],
                          zone_terminals: List[ZoneTerminal]):
        """
        Link zones to HVAC systems for CBECC files.

        In CBECC:
        - ThrmlZn has <PriAirCondgSysRef> pointing to an AirSeg or system name
        - Spc has <ThrmlZnRef> pointing to a ThrmlZn name
        - TrmlUnit has <ZnServedRef> pointing to a zone name
        - Zones need their served_by list populated with HVAC system IDs
        """
        # Build lookup maps
        system_by_name = {sys.name: sys.id for sys in hvac_systems}
        zone_by_name = {z.name: z for z in zones}

        # Build ThrmlZn HVAC mapping first
        thrmlzn_to_hvac = {}

        # Method 1: Link via ThrmlZn PriAirCondgSysRef
        for thrml_zn in root.findall('.//ThrmlZn'):
            zone_name = self._get_name(thrml_zn)
            hvac_ref = self.get_property(thrml_zn, 'PriAirCondgSysRef')

            if zone_name and hvac_ref:
                # Direct match first
                hvac_id = system_by_name.get(hvac_ref)

                # If no direct match, try partial match (e.g., RTU_1 matches RTU_1_Supply)
                if not hvac_id:
                    for sys_name, sys_id in system_by_name.items():
                        if sys_name.startswith(hvac_ref + '_') or sys_name.startswith(hvac_ref):
                            hvac_id = sys_id
                            break

                if hvac_id:
                    # Store the mapping
                    thrmlzn_to_hvac[zone_name] = hvac_id

                    # Also link the ThrmlZn zone itself if it exists
                    if zone_name in zone_by_name:
                        zone = zone_by_name[zone_name]
                        if hvac_id not in zone.served_by:
                            zone.served_by.append(hvac_id)

        # Method 2: Link Spc zones via their ThrmlZnRef
        for spc in root.findall('.//Spc'):
            spc_name = self._get_name(spc)
            thrml_zn_ref = self.get_property(spc, 'ThrmlZnRef')

            if spc_name and thrml_zn_ref and spc_name in zone_by_name:
                zone = zone_by_name[spc_name]
                # Look up the HVAC system from the ThrmlZn
                if thrml_zn_ref in thrmlzn_to_hvac:
                    hvac_id = thrmlzn_to_hvac[thrml_zn_ref]
                    if hvac_id not in zone.served_by:
                        zone.served_by.append(hvac_id)

        # Method 3: Link via TrmlUnit ZnServedRef (terminal units know which zones they serve)
        for terminal in zone_terminals:
            zone_name = terminal.zone_served_ref
            if zone_name in zone_by_name:
                zone = zone_by_name[zone_name]
                # Add the parent HVAC system
                hvac_id = terminal.parent_hvac_system_id
                if hvac_id not in zone.served_by:
                    zone.served_by.append(hvac_id)

    def _parse_status(self, status_str: Optional[str]) -> int:
        """Parse status to CBECC integer (1=Existing, 2=Altered, 3=New, 4=Mixed)."""
        if not status_str:
            return 3  # Default to New

        # Try direct integer conversion first
        try:
            status_int = int(status_str)
            if status_int in (1, 2, 3, 4):
                return status_int
        except ValueError:
            pass

        # Convert string to integer
        status_upper = status_str.upper()
        if 'EXIST' in status_upper:
            return 1  # Existing
        elif 'ALTER' in status_upper or 'MODIF' in status_upper:
            return 2  # Altered
        elif 'NEW' in status_upper:
            return 3  # New
        elif 'MIX' in status_upper or 'EXIST+NEW' in status_upper:
            return 4  # Mixed
        else:
            return 3  # Default to New

    def _parse_hvac_type(self, type_str: Optional[str], sys_elem: ET.Element) -> int:
        """Parse HVAC system type to CBECC integer classification."""
        # Try direct integer conversion first
        if type_str:
            try:
                type_int = int(type_str)
                if type_int in (1, 2, 4):
                    return type_int
            except ValueError:
                pass

        # Infer from equipment present
        has_heat_pump = sys_elem.find('.//HtPumpSystem') is not None
        has_central = sys_elem.find('.//HVACCentralRef') is not None
        has_heat = sys_elem.find('.//HeatSystem') is not None
        has_cool = sys_elem.find('.//CoolSystem') is not None

        if has_heat_pump:
            return 2  # Heat Pump system
        elif has_central:
            return 4  # Central system
        elif has_heat or has_cool:
            return 1  # Heat+Cool system
        else:
            return 2  # Default to heat pump (most common residential)

    def _parse_equipment_array(self, sys_elem: ET.Element, equipment_tag: str, count_tag: str) -> Tuple[List[str], List[int]]:
        """Parse CBECC equipment array with indexed elements and counts."""
        equipment_list = []
        count_list = []

        # Find all indexed equipment elements (e.g., HeatSystem[@index="1"], HeatSystem[@index="2"])
        for i in range(1, 11):  # CBECC supports up to 10 equipment types
            # Try to find element with this index
            elem = sys_elem.find(f'.//{equipment_tag}[@index="{i}"]')
            if elem is None:
                # Also try without namespace
                elem = sys_elem.find(f'{equipment_tag}[@index="{i}"]')

            if elem is not None and elem.text:
                equipment_list.append(elem.text.strip())

                # Get corresponding count
                count_elem = sys_elem.find(f'.//{count_tag}[@index="{i}"]')
                if count_elem is None:
                    count_elem = sys_elem.find(f'{count_tag}[@index="{i}"]')

                count = self._to_int(count_elem.text) if count_elem is not None and count_elem.text else 1
                count_list.append(count)

        # Also handle non-indexed equipment (simple reference)
        if not equipment_list:
            elem = sys_elem.find(f'.//{equipment_tag}')
            if elem is None:
                elem = sys_elem.find(f'{equipment_tag}')

            if elem is not None and elem.text:
                equipment_list.append(elem.text.strip())
                count_list.append(1)  # Default count of 1

        return equipment_list, count_list

    def _get_name(self, element: ET.Element) -> Optional[str]:
        """Extract name from element."""
        name_elem = element.find('.//n')
        if name_elem is not None and name_elem.text:
            return name_elem.text.strip()
        name_elem = element.find('.//Name')
        if name_elem is not None and name_elem.text:
            return name_elem.text.strip()
        name = element.get('id')
        return name if name else None

    def _local_tag(self, tag: str) -> str:
        """Strip namespace from tag."""
        if '}' in tag:
            return tag.split('}', 1)[1]
        return tag
