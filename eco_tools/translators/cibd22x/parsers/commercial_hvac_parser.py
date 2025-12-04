"""
Commercial HVAC Parser - Extracts Commercial HVAC System Components
====================================================================

PURPOSE: Extracts commercial HVAC components (air systems and fluid/hydronic systems)
from CIBD22X as dictionaries for round-trip export.

AIR SYSTEMS: AirSys, AirSeg, Fan, CoilClg, CoilHtg, TrmlUnit, OACtrl
ZONE SYSTEMS: ZnSys (with nested CoilClg, CoilHtg, Fan), VRFSys (catalog)
FLUID SYSTEMS: FluidSys, FluidSeg, WtrHtr, Chlr, Blr, Pump, HtRej, HtRcvry
LIGHTING: IntLtgSys (interior lighting systems), Lum (luminaire catalog)
GEOMETRY: Ceiling (ceiling constructions), ExtFlr (exterior floors)
PROJECT: ProjVar (project variables), EUseSummary (energy use summary)

STRUCTURE IN CIBD22:
AirSys   "MFC-1 AirSys"  (parent system)
   Type = "SZHP"
   CtrlZnRef = "IDF_L01"
   ..
AirSeg   "MFC-1 SupAirSeg"  (child - supply air segment)
   Type = "Supply"
   ..
CoilClg   "MFC-1 ClgCoil"  (child - cooling coil)
   Type = "DirectExpansion"
   ..
CoilHtg   "MFC-1 HtgCoil"  (child - heating coil)
   Type = "HeatPump"
   ..
Fan   "MFC-1 SupFan"  (child - supply fan)
   ModelingMthd = "StaticPressure"
   ..
AirSeg   "MFC-1 RetAirSeg"  (child - return air segment)
   Type = "Return"
   ..
TrmlUnit   "MFC-1 TrmlUnit"  (child - terminal unit)
   Type = "Uncontrolled"
   ZnServedRef = "IDF_L01"
   ..
OACtrl   "MFC-1 OACtrl"  (child - outside air control)
   EconoCtrlMthd = "NoEconomizer"
   ..

These components are written as siblings at root level but logically belong to
the AirSys parent. This parser extracts them as raw dictionaries for export.
"""

from typing import List, Dict, Any, Optional
import xml.etree.ElementTree as ET
import logging

from .base_parser import BaseParser

# Get module logger
logger = logging.getLogger('eco_tools.parsers')


class CommercialHVACParser(BaseParser):
    """Parser for commercial HVAC system components (AirSys, Fan, Coils, etc.)"""

    COMMERCIAL_HVAC_TAGS = [
        # Thermal zones (connect spaces to HVAC systems)
        'ThrmlZn',     # Thermal zone - links to ZnSys via indexed PriAirCondgSysRef
        # Air systems
        'AirSys',      # Commercial air system (parent)
        'AirSeg',      # Air segment (supply/return)
        'Fan',         # Supply/return fans
        'CoilClg',     # Cooling coil
        'CoilHtg',     # Heating coil
        'TrmlUnit',    # Terminal unit
        'OACtrl',      # Outside air control / economizer
        # Zone systems
        'ZnSys',       # Zone HVAC system (VRF, PTAC, Unitary, etc.) - can contain nested CoilClg, CoilHtg, Fan
        'VRFSys',      # VRF system catalog element
        # Fluid/hydronic systems
        'FluidSys',    # Fluid system (chilled water, hot water, service hot water)
        'FluidSeg',    # Fluid segment (supply, return, makeup)
        'WtrHtr',      # Commercial water heater
        'Chlr',        # Chiller
        'Blr',         # Boiler
        'Pump',        # Pump
        'HtRej',       # Heat rejection (cooling towers, condensers)
        'HtRcvry',     # Heat recovery (ERV, heat wheels)
        # Lighting systems
        'IntLtgSys',   # Interior lighting system
        'Lum',         # Luminaire catalog element
        # Geometry elements
        'Ceiling',     # Ceiling constructions (for plenum spaces)
        'ExtFlr',      # Exterior floors (e.g., attic soffits)
        # Project-level elements
        'ProjVar',     # Project variables
        'EUseSummary', # Energy use summary
    ]

    # Elements that can contain nested HVAC components
    NESTED_COMPONENT_PARENTS = ['ZnSys', 'AirSys', 'AirSeg']

    # Nested component tags that should be extracted when inside a parent
    NESTED_COMPONENT_TAGS = ['CoilClg', 'CoilHtg', 'Fan', 'AirSeg', 'TrmlUnit', 'OACtrl']

    def parse_commercial_hvac(self, root: ET.Element) -> Dict[str, List[Dict[str, Any]]]:
        """
        Parse all commercial HVAC components from CIBD22X.

        Returns:
            Dict mapping element type to list of component dictionaries:
            {
                'AirSys': [{name, properties}, ...],
                'AirSeg': [{name, properties}, ...],
                'Fan': [{name, properties}, ...],
                ...
            }
        """
        components = {tag: [] for tag in self.COMMERCIAL_HVAC_TAGS}

        for tag in self.COMMERCIAL_HVAC_TAGS:
            for elem in root.iter():
                if self._local_tag(elem.tag) == tag:
                    component = self._parse_component(elem, tag)
                    if component:
                        components[tag].append(component)

        total = sum(len(v) for v in components.values())
        logger.info(f"Parsed {total} commercial HVAC components")
        return components

    def _parse_component(self, elem: ET.Element, tag: str) -> Optional[Dict[str, Any]]:
        """
        Parse a single commercial HVAC component element.

        Extracts all properties as-is (no unit conversion) for round-trip export.
        For elements that can contain nested components (like ZnSys), extracts
        nested components separately.
        """
        name = self._get_name(elem)
        if not name:
            return None

        component = {
            '_type': tag,
            'name': name,
            'properties': {},
            'nested_components': []  # For nested CoilClg, CoilHtg, Fan within ZnSys
        }

        # Check if this element can contain nested components
        can_have_nested = tag in self.NESTED_COMPONENT_PARENTS

        # Extract all child elements as properties or nested components
        for child in elem:
            child_tag = self._local_tag(child.tag)

            if child_tag == 'n' or child_tag == 'Name':
                # Skip name element (already extracted)
                continue

            # Check if this is a nested component (e.g., CoilClg inside ZnSys)
            if can_have_nested and child_tag in self.NESTED_COMPONENT_TAGS:
                # Recursively parse the nested component
                nested = self._parse_component(child, child_tag)
                if nested:
                    component['nested_components'].append(nested)
                continue

            # Extract simple property value
            if child.text:
                value = child.text.strip()
                # Try to convert to number if possible
                try:
                    if '.' in value:
                        value = float(value)
                    else:
                        value = int(value)
                except ValueError:
                    pass  # Keep as string

                # Check for indexed properties (e.g., LumRef index="0")
                index_attr = child.get('index')
                if index_attr is not None:
                    # Store indexed property as a list of tuples: [(index, value), ...]
                    if child_tag not in component['properties']:
                        component['properties'][child_tag] = []
                    component['properties'][child_tag].append((index_attr, value))
                else:
                    component['properties'][child_tag] = value

        return component

    def _get_name(self, element: ET.Element) -> Optional[str]:
        """Extract name from element."""
        # Try <n> child
        for child in element:
            tag = self._local_tag(child.tag)
            if tag == 'n' and child.text:
                return child.text.strip()

        # Try <Name> child
        for child in element:
            tag = self._local_tag(child.tag)
            if tag == 'Name' and child.text:
                return child.text.strip()

        # Try id attribute
        name = element.get('id')
        if name:
            return name

        return None
