"""
PVArray Parser - Composite Parser (Creates Multiple Element Types)
==================================================================

PURPOSE: Extracts PV array and battery storage configurations from CIBD22X XML.
This is a COMPOSITE PARSER that creates TWO element types:
1. PVArray (the solar array itself)
2. BatterySystem (nested battery storage)

PATTERN: Composite Parser - See dhw_parser.py for detailed documentation.

COMPOSITE STRUCTURE:
<PVArray>                        → PVArray
  <Battery>...</Battery>         → BatterySystem (energy storage)
</PVArray>

KEY OPERATIONS:
- Parse PV array specs (module count, capacity, orientation, tilt, tracking)
- Parse inverter configuration
- Delegate to BatterySystemParser for nested batteries
- Handle residential vs commercial PV system variants

RETURNS: Tuple[List[PVArray], List[BatterySystem]]
"""

from typing import List, Tuple, Optional
import xml.etree.ElementTree as ET
import logging

from eco_tools.core.internal_repr import PVArray, BatterySystem
from eco_tools.core.id_registry import IDRegistry
from .base_parser import BaseParser
from .battery_parser import BatterySystemParser

# Get module logger
logger = logging.getLogger('eco_tools.parsers')


class PVArrayParser(BaseParser):
    """Parser for CIBD22X PV array elements"""

    PV_ARRAY_TAGS = [
        'ResPVSys',  # Residential PV systems
        'PVArray',   # Commercial PV arrays
        'PVSys',     # Generic PV systems
    ]

    def __init__(self, id_registry: IDRegistry):
        super().__init__()
        self.id_registry = id_registry
        self.battery_parser = BatterySystemParser(id_registry)

    def parse_pv_arrays(self, root: ET.Element) -> Tuple[List[PVArray], List[BatterySystem]]:
        """
        Parse all PV arrays and associated battery systems.

        Returns:
            tuple: (List[PVArray], List[BatterySystem])
        """
        pv_arrays = []
        battery_systems = []

        # Parse both residential and commercial PV system tags
        pv_tags = ['ResPVSys', 'PVArray', 'PVSys']

        for tag in pv_tags:
            for pv_elem in root.findall(f'.//{tag}'):
                name = self._get_name(pv_elem)
                if not name:
                    name = f"PV Array {len(pv_arrays) + 1}"

                pv_id = self.id_registry.generate_id('PV', name, '', 'CIBD22X')

                # Extract array type
                array_type = self.get_property(pv_elem, 'ArrayType')
                if not array_type:
                    array_type = self.get_property(pv_elem, 'Type')
                if not array_type:
                    array_type = 'FixedRoof'

                # Module specification
                module_ref = self.get_property(pv_elem, 'PVModRef')
                if not module_ref:
                    module_ref = self.get_property(pv_elem, 'ModuleRef')

                module_type = self.get_property(pv_elem, 'ModuleType')

                # System sizing
                rated_capacity_kw = self._to_float(self.get_property(pv_elem, 'RatedCap'))
                if not rated_capacity_kw:
                    rated_capacity_kw = self._to_float(self.get_property(pv_elem, 'RatedPower'))

                rated_capacity_w = (rated_capacity_kw * 1000) if rated_capacity_kw else None

                num_modules = self._to_int(self.get_property(pv_elem, 'NumModules'))
                if not num_modules:
                    num_modules = self._to_int(self.get_property(pv_elem, 'ModuleCount'))

                module_power_w = self._to_float(self.get_property(pv_elem, 'ModulePower'))

                # Array orientation
                tilt_deg = self._to_float(self.get_property(pv_elem, 'Tilt'))
                if not tilt_deg:
                    tilt_deg = self._to_float(self.get_property(pv_elem, 'TiltAngle'))

                azimuth_deg = self._to_float(self.get_property(pv_elem, 'Azimuth'))
                if not azimuth_deg:
                    azimuth_deg = self._to_float(self.get_property(pv_elem, 'Orientation'))

                tracking_type = self.get_property(pv_elem, 'TrackingType')
                if not tracking_type:
                    tracking_type = self.get_property(pv_elem, 'Tracking')

                # Inverter
                inverter_eff = self._to_float(self.get_property(pv_elem, 'InvEff'))
                if not inverter_eff:
                    inverter_eff = self._to_float(self.get_property(pv_elem, 'InverterEfficiency'))

                inverter_type = self.get_property(pv_elem, 'InverterType')
                inverter_ref = self.get_property(pv_elem, 'InverterRef')

                # Installation
                location = self.get_property(pv_elem, 'Location')
                if not location:
                    location = self.get_property(pv_elem, 'MountingType')

                mounting_type = self.get_property(pv_elem, 'MountingConfig')

                # SARA (Solar Access Roof Area) - Title 24 specific
                sara_zone_ref = self.get_property(pv_elem, 'SARAZoneRef')
                sara_area_ft2 = self._to_float(self.get_property(pv_elem, 'SARAArea'))
                sara_area_m2 = (sara_area_ft2 * 0.092903) if sara_area_ft2 else None

                # Performance
                performance_ratio = self._to_float(self.get_property(pv_elem, 'PerformanceRatio'))
                dc_to_ac_ratio = self._to_float(self.get_property(pv_elem, 'DCtoACRatio'))
                annual_production_kwh = self._to_float(self.get_property(pv_elem, 'AnnualProduction'))

                # Build annotation with additional properties
                annotation = {'xml_tag': tag}

                # CRITICAL: Store ALL CBECC-specific properties for round-trip export
                # The internal representation fields may not cover all CBECC properties
                additional_props = [
                    # System sizing (CBECC-specific)
                    'DCSysSize',           # DC system size (kW) - MOST IMPORTANT
                    'ACSysSize',           # AC system size (kW)
                    'SysSize',             # Generic system size

                    # Module specifications (CBECC-specific)
                    'ModuleType',          # Premium, Standard, etc. - IMPORTANT
                    'Module',              # Module name/reference

                    # Inverter/power electronics (CBECC-specific)
                    'PwrElec',             # Microinverters, String Inverter, etc. - IMPORTANT
                    'InverterType',        # Inverter type
                    'InverterEff',         # Inverter efficiency

                    # Module and array details
                    'CellType', 'ModuleEff', 'TempCoeff',
                    'NOCT', 'ArrayArea', 'ArrayRows', 'ArrayCols',
                    'InverterManufacturer', 'InverterModel',
                    'InverterRatedPower', 'MaxPowerTracker',

                    # Performance and losses
                    'Shading', 'ShadingFactor', 'SoilingLoss', 'SystemLoss',
                    'GroundCoverageRatio', 'InterRowSpacing', 'CollectorWidth',

                    # Array configuration
                    'Orientation', 'Tracking', 'Tilt', 'Az',
                    'ArrayMount', 'RoofCondition',

                    # DC/AC sizing
                    'DCtoACRatio'
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
                    module_type=module_type,
                    rated_capacity_w=rated_capacity_w,
                    rated_capacity_kw=rated_capacity_kw,
                    num_modules=num_modules,
                    module_power_w=module_power_w,
                    tilt_deg=tilt_deg,
                    azimuth_deg=azimuth_deg,
                    tracking_type=tracking_type,
                    inverter_efficiency=inverter_eff,
                    inverter_type=inverter_type,
                    inverter_ref=inverter_ref,
                    location=location,
                    mounting_type=mounting_type,
                    sara_zone_ref=sara_zone_ref,
                    sara_area_m2=sara_area_m2,
                    performance_ratio=performance_ratio,
                    dc_to_ac_ratio=dc_to_ac_ratio,
                    annual_production_kwh=annual_production_kwh,
                    annotation=annotation
                )

                pv_arrays.append(pv_array)

                # Parse associated battery system if present (can be nested in PV element)
                # CBECC uses different tags: Batt (residential), BatterySystem (commercial)
                battery_elem = pv_elem.find('.//Batt')
                if battery_elem is None:
                    battery_elem = pv_elem.find('.//BatterySystem')
                if battery_elem is None:
                    battery_elem = pv_elem.find('.//ResBatt')

                if battery_elem is not None:
                    battery = self.battery_parser.parse_battery_system(battery_elem, pv_id)
                    if battery:
                        battery_systems.append(battery)

        # Also parse standalone battery systems (root-level, not nested in PV)
        # Search for all battery element types
        for battery_tag in ['Batt', 'BatterySystem', 'BatterySys', 'ResBatt']:
            for battery_elem in root.findall(f'.//{battery_tag}'):
                # Make sure this isn't already inside a PV array (would be parsed above)
                # Check if parent is a PV array tag
                parent = battery_elem.find('..')
                if parent is not None and self._local_tag(parent.tag) in ['PVArray', 'ResPVSys', 'PVSys']:
                    continue  # Skip - already parsed as nested battery

                battery = self.battery_parser.parse_battery_system(battery_elem, None)
                if battery:
                    battery_systems.append(battery)

        logger.info(f"Parsed {len(pv_arrays)} PV arrays and {len(battery_systems)} battery systems")
        return pv_arrays, battery_systems

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
