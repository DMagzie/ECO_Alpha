"""
HeatPump Parser - Simple Catalog Parser (HVAC Component)
========================================================

PURPOSE: Extracts heat pump catalog definitions from CIBD22X XML.
Heat pumps are HVAC equipment referenced by HVAC systems.

PATTERN: Simple Catalog Parser - See material_parser.py for pattern details.

KEY OPERATIONS:
- Parse capacities (Btu/h → W unit conversion)
- Convert performance metrics (HSPF → COP, SEER → EER)
- Handle AHRI 2023 vs legacy rating standards
"""

from typing import List, Optional, Dict, Any
import xml.etree.ElementTree as ET
import logging

from eco_tools.core.internal_repr import HeatPump
from eco_tools.core.id_registry import IDRegistry
from .base_parser import BaseParser

# Get module logger
logger = logging.getLogger('eco_tools.parsers')


class HeatPumpParser(BaseParser):
    """Parser for CIBD22X heat pump system elements"""

    # CIBD22X heat pump catalog tags
    HEAT_PUMP_CATALOG_TAGS = [
        'ResHtPumpSys'  # Residential heat pump systems
    ]

    def __init__(self, id_registry: IDRegistry):
        """
        Initialize the heat pump parser.

        Args:
            id_registry: ID registry for generating unique heat pump IDs
        """
        super().__init__()
        self.id_registry = id_registry

    def parse_heat_pumps(self, root: ET.Element) -> List[HeatPump]:
        """
        Parse all heat pump systems from CIBD22X catalog.

        Heat pumps provide both heating and cooling. In CIBD22X, ResHtPumpSys
        elements define systems with capacities, efficiency ratings, and
        support for both AHRI 2023 and legacy metric naming conventions.

        Args:
            root: Root XML element

        Returns:
            List of HeatPump objects
        """
        heat_pumps = []

        # Use namespace-aware iteration
        for hp_elem in root.iter():
            if self._local_tag(hp_elem.tag) == 'ResHtPumpSys':
                heat_pump = self._parse_single_heat_pump(hp_elem)
                if heat_pump:
                    heat_pumps.append(heat_pump)
                else:
                    name = self._get_name(hp_elem) or "unnamed"
                    logger.warning(f"Failed to parse ResHtPumpSys '{name}'")

        logger.info(f"Parsed {len(heat_pumps)} heat pumps")
        return heat_pumps

    def _parse_single_heat_pump(self, hp_elem: ET.Element) -> Optional[HeatPump]:
        """
        Parse a single heat pump element (ResHtPumpSys).

        Args:
            hp_elem: ResHtPumpSys XML element

        Returns:
            HeatPump object (always returns, uses default name if needed)
        """
        # Get name (default to "Heat Pump" if not found)
        name = self._get_name(hp_elem)
        if not name:
            name = "Heat Pump"

        # Generate heat pump ID
        hp_id = self.id_registry.generate_id('HP', name, '', 'CIBD22X')

        # Extract heat pump type
        pump_type = self.get_property(hp_elem, 'Type')
        if not pump_type:
            pump_type = 'air-source'

        # Extract heating capacity with unit conversion
        heating_capacity_w = self._extract_heating_capacity(hp_elem)

        # Extract cooling capacity with unit conversion
        cooling_capacity_w = self._extract_cooling_capacity(hp_elem)

        # Extract heating COP (with HSPF to COP conversion)
        heating_cop = self._extract_heating_cop(hp_elem)

        # Extract cooling EER (with SEER to EER conversion)
        cooling_eer = self._extract_cooling_eer(hp_elem)

        # Extract backup fuel
        backup_fuel = self.get_property(hp_elem, 'BackupFuel')

        # Parse zone references
        zone_refs = self._extract_zone_refs(hp_elem)

        # Build annotation
        annotation = self._build_annotation(hp_elem)

        heat_pump = HeatPump(
            id=hp_id,
            name=name,
            pump_type=pump_type,
            heating_capacity_w=heating_capacity_w,
            cooling_capacity_w=cooling_capacity_w,
            heating_cop=heating_cop,
            cooling_eer=cooling_eer,
            backup_fuel=backup_fuel,
            zone_refs=zone_refs,
            annotation=annotation
        )

        return heat_pump

    def _extract_heating_capacity(self, hp_elem: ET.Element) -> Optional[float]:
        """
        Extract heating capacity and convert from Btu/h to W.

        Tries AHRI 2023 metrics first (Cap47), then falls back to legacy (HtgCap).
        Converts Btu/h to W by multiplying by 0.293071.

        Args:
            hp_elem: ResHtPumpSys XML element

        Returns:
            Heating capacity in watts or None if not found
        """
        # Try newer AHRI 2023 metric first (Cap47 = Capacity at 47°F)
        heating_cap_btuh = self._to_float(self.get_property(hp_elem, 'Cap47'))

        # Fall back to legacy metric
        if not heating_cap_btuh:
            heating_cap_btuh = self._to_float(self.get_property(hp_elem, 'HtgCap'))

        # Convert Btu/h to W
        if heating_cap_btuh:
            return heating_cap_btuh * 0.293071
        return None

    def _extract_cooling_capacity(self, hp_elem: ET.Element) -> Optional[float]:
        """
        Extract cooling capacity and convert from Btu/h to W.

        Tries AHRI 2023 metrics first (Cap17), then falls back to legacy (ClgCap).
        Converts Btu/h to W by multiplying by 0.293071.

        Args:
            hp_elem: ResHtPumpSys XML element

        Returns:
            Cooling capacity in watts or None if not found
        """
        # Try newer AHRI 2023 metric first (Cap17 = Capacity at 17°F)
        cooling_cap_btuh = self._to_float(self.get_property(hp_elem, 'Cap17'))

        # Fall back to legacy metric
        if not cooling_cap_btuh:
            cooling_cap_btuh = self._to_float(self.get_property(hp_elem, 'ClgCap'))

        # Convert Btu/h to W
        if cooling_cap_btuh:
            return cooling_cap_btuh * 0.293071
        return None

    def _extract_heating_cop(self, hp_elem: ET.Element) -> Optional[float]:
        """
        Extract heating COP (Coefficient of Performance).

        Tries AHRI 2023 metric first (HSPF2), then falls back to legacy (HSPF).
        Converts HSPF to COP by dividing by 3.412.

        Args:
            hp_elem: ResHtPumpSys XML element

        Returns:
            Heating COP or None if not found
        """
        # Try newer AHRI 2023 metric first
        heating_cop = self._to_float(self.get_property(hp_elem, 'HSPF2'))

        # Fall back to legacy metric
        if not heating_cop:
            heating_cop = self._to_float(self.get_property(hp_elem, 'HSPF'))

        # Convert HSPF to COP (divide by 3.412)
        if heating_cop:
            return heating_cop / 3.412
        return None

    def _extract_cooling_eer(self, hp_elem: ET.Element) -> Optional[float]:
        """
        Extract cooling EER (Energy Efficiency Ratio).

        Tries EER2 (AHRI 2023) first, then SEER2, then SEER (legacy).
        Converts SEER to EER by dividing by 1.1 if we got SEER.

        Args:
            hp_elem: ResHtPumpSys XML element

        Returns:
            Cooling EER or None if not found
        """
        # Try newer AHRI 2023 EER2 first
        cooling_eer = self._to_float(self.get_property(hp_elem, 'EER2'))

        # Try SEER2 (also AHRI 2023)
        if not cooling_eer:
            cooling_eer = self._to_float(self.get_property(hp_elem, 'SEER2'))

        # Fall back to legacy SEER
        if not cooling_eer:
            cooling_eer = self._to_float(self.get_property(hp_elem, 'SEER'))

        # Convert SEER to EER (divide by 1.1) - only if we got SEER, not EER2
        if cooling_eer and not self.get_property(hp_elem, 'EER2'):
            return cooling_eer / 1.1
        return cooling_eer

    def _extract_zone_refs(self, hp_elem: ET.Element) -> List[str]:
        """
        Extract zone references from heat pump system.

        Args:
            hp_elem: ResHtPumpSys XML element

        Returns:
            List of zone reference strings
        """
        zone_refs = []
        for zn_ref_elem in hp_elem.findall('.//ZnServedRef'):
            if zn_ref_elem.text:
                zone_refs.append(zn_ref_elem.text.strip())
        return zone_refs

    def _build_annotation(self, hp_elem: ET.Element) -> Dict[str, Any]:
        """
        Build annotation dictionary with ALL CIBD22X-specific properties for round-trip fidelity.

        Args:
            hp_elem: ResHtPumpSys XML element

        Returns:
            Annotation dictionary with all available properties
        """
        annotation = {}

        # CRITICAL: Store ALL CBECC properties for round-trip export
        # The exporter will write these back exactly as they were
        cbecc_properties = [
            # System type and configuration
            'Type', 'CompType', 'BackupFuel', 'AutoSize',

            # AHRI 2023 ratings (newer standard)
            'HSPF2', 'SEER2', 'EER2', 'Cap47', 'Cap17',

            # Legacy ratings (older standard)
            'HSPF', 'SEER', 'EER', 'HtgCap', 'ClgCap',

            # Installation and refrigerant
            'ACCharge', 'RefCharge', 'UseEERinAnalysis',

            # Additional properties
            'IEER', 'CEER', 'COP', 'MinHtgCap', 'MinClgCap',
            'DefrostCtrl', 'FanCtrl', 'DuctLoc'
        ]

        for prop in cbecc_properties:
            value = self.get_property(hp_elem, prop)
            if value:
                annotation[prop] = value

        return annotation

    def _get_name(self, element: ET.Element) -> Optional[str]:
        """
        Extract name from element (CIBD22X format).

        Tries: <n>, <Name>, id attribute

        Args:
            element: XML element

        Returns:
            Element name or None
        """
        # Try <n> child (CIBD22X format)
        name_elem = element.find('.//n')
        if name_elem is not None and name_elem.text:
            return name_elem.text.strip()

        # Try <Name> child
        name_elem = element.find('.//Name')
        if name_elem is not None and name_elem.text:
            return name_elem.text.strip()

        # Try id attribute
        name = element.get('id')
        if name:
            return name

        return None
