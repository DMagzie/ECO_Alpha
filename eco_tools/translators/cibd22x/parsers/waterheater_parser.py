"""
WaterHeater Parser - Sub-Parser (Used by DHWSystemParser)
=========================================================

PURPOSE: Extracts water heater equipment nested within DHW systems.
This is a SUB-PARSER called by DHWSystemParser (composite parser).

PATTERN: Sub-Parser - Called by composite parent, not directly by importer.

KEY OPERATIONS:
- Parse water heater arrays (multiple heaters with counts)
- Extract heater specs (capacity, efficiency, fuel type)
- Link to parent DHW system

USAGE: Only called by DHWSystemParser.parse_dhw_systems()
"""

from typing import List, Tuple, Optional
import xml.etree.ElementTree as ET
import logging

from eco_tools.core.internal_repr import WaterHeater
from eco_tools.core.id_registry import IDRegistry
from .base_parser import BaseParser

# Get module logger
logger = logging.getLogger('eco_tools.parsers')


class WaterHeaterParser(BaseParser):
    """Parser for CIBD22X water heater elements"""

    WATER_HEATER_CATALOG_TAGS = [
        'ResWtrHtr',    # Residential water heater catalog
    ]

    def __init__(self, id_registry: IDRegistry):
        super().__init__()
        self.id_registry = id_registry

    def parse_water_heater_catalog(self, root: ET.Element) -> List[WaterHeater]:
        """
        Parse ResWtrHtr catalog (water heater equipment library).

        ResWtrHtr entries are catalog definitions with complete properties.
        DHWHeater elements in ResDHWSys reference these by name.
        """
        heaters = []
        seen_names = set()  # Track duplicate names

        # Use namespace-aware iteration
        for wh_elem in root.iter():
            if self._local_tag(wh_elem.tag) != 'ResWtrHtr':
                continue

            name = self._get_name(wh_elem)
            if not name:
                continue

            # Skip duplicates (shouldn't happen, but just in case)
            if name in seen_names:
                logger.warning(f"Duplicate ResWtrHtr found: {name}, skipping")
                continue
            seen_names.add(name)

            wh_id = self.id_registry.generate_id('WH', name, '', 'CIBD22X')

            # Parse CBECC-specific properties
            fuel_type = self.get_property(wh_elem, 'HeaterElementType')
            tank_type = self.get_property(wh_elem, 'TankType')
            input_rating = self._to_float(self.get_property(wh_elem, 'InputRating'))
            energy_factor = self._to_float(self.get_property(wh_elem, 'EnergyFactor'))
            tank_volume = self._to_float(self.get_property(wh_elem, 'TankVolume'))
            recovery_eff = self._to_float(self.get_property(wh_elem, 'RecovEff'))

            # Build annotation with ALL CBECC properties for round-trip fidelity
            annotation = {}
            annotation['xml_tag'] = 'ResWtrHtr'  # Mark as catalog element
            cbecc_properties = [
                'HeaterElementType', 'TankType', 'InputRating', 'EnergyFactor',
                'TankVolume', 'RecovEff', 'UEF', 'FirstHrRating', 'Location',
                'Insulation', 'TempSetpoint', 'FuelType'
            ]
            for prop in cbecc_properties:
                value = self.get_property(wh_elem, prop)
                if value:
                    annotation[prop] = value

            heater = WaterHeater(
                id=wh_id,
                name=name,
                heater_type=fuel_type,  # Gas, Electric, etc.
                tank_type=tank_type,
                storage_volume_gal=tank_volume,
                input_capacity_btu_hr=input_rating,
                energy_factor=energy_factor,
                recovery_efficiency=recovery_eff,
                fuel_type=fuel_type,
                annotation=annotation
            )

            heaters.append(heater)

        logger.info(f"Parsed {len(heaters)} water heater catalog elements")
        return heaters

    def parse_water_heater_array(self, sys_elem: ET.Element, dhw_system_id: str) -> Tuple[List[WaterHeater], List[int]]:
        """
        Parse water heater equipment array from DHW system element.

        Returns:
            tuple: (List[WaterHeater], List[int]) - heaters and their counts
        """
        water_heaters = []
        counts = []

        # Parse DHWHeater elements (indexed or non-indexed)
        # CRITICAL: CBECC uses index="0" as first heater, not index="1"
        for i in range(0, 10):  # CBECC supports up to 10 heaters (0-9)
            heater_elem = sys_elem.find(f'.//DHWHeater[@index="{i}"]')
            if heater_elem is None:
                heater_elem = sys_elem.find(f'DHWHeater[@index="{i}"]')

            if heater_elem is not None:
                # CRITICAL: DHWHeater element has text content (heater name), not <Name> child
                # <DHWHeater index="0">94 percent 499000 119-gal</DHWHeater>
                heater_name = heater_elem.text.strip() if heater_elem.text else None
                if not heater_name or heater_name == "- none -":
                    heater_name = f"Heater_{i}"

                heater_id = self.id_registry.generate_id('WH', heater_name, dhw_system_id, 'CIBD22X')

                # Parse heater type
                heater_type = self.get_property(heater_elem, 'Type')
                if not heater_type:
                    heater_type = self.get_property(heater_elem, 'DHWHeaterType') or 'Unknown'

                # Tank classification
                tank_type = self.get_property(heater_elem, 'TankType')

                # Capacity
                storage_volume = self._to_float(self.get_property(heater_elem, 'StorageVol'))
                if storage_volume is None:
                    storage_volume = self._to_float(self.get_property(heater_elem, 'DHWStorageVol'))

                input_capacity = self._to_float(self.get_property(heater_elem, 'InputCapacity'))

                # Efficiency metrics
                energy_factor = self._to_float(self.get_property(heater_elem, 'EnergyFactor'))
                if energy_factor is None:
                    energy_factor = self._to_float(self.get_property(heater_elem, 'DHWHeaterEF'))

                uniform_energy_factor = self._to_float(self.get_property(heater_elem, 'UniformEnergyFactor'))
                thermal_efficiency = self._to_float(self.get_property(heater_elem, 'ThermalEfficiency'))
                first_hour_rating = self._to_float(self.get_property(heater_elem, 'FirstHourRating'))
                recovery_efficiency = self._to_float(self.get_property(heater_elem, 'RecoveryEfficiency'))

                # Heat pump specific
                cop = self._to_float(self.get_property(heater_elem, 'COP'))
                compressor_location = self.get_property(heater_elem, 'CompressorLocation')

                # Installation
                fuel_type = self.get_property(heater_elem, 'FuelType')
                if not fuel_type:
                    fuel_type = self.get_property(heater_elem, 'DHWHeaterFuel')

                location = self.get_property(heater_elem, 'Location')

                heater = WaterHeater(
                    id=heater_id,
                    name=heater_name,
                    heater_type=heater_type,
                    tank_type=tank_type,
                    storage_volume_gal=storage_volume,
                    input_capacity_btu_hr=input_capacity,
                    energy_factor=energy_factor,
                    uniform_energy_factor=uniform_energy_factor,
                    thermal_efficiency=thermal_efficiency,
                    first_hour_rating=first_hour_rating,
                    recovery_efficiency=recovery_efficiency,
                    cop=cop,
                    compressor_location=compressor_location,
                    fuel_type=fuel_type,
                    location=location
                )

                water_heaters.append(heater)

                # Get count for this heater
                # CRITICAL: CBECC uses <HeaterMult> tag, not <DHWHeaterCount>
                count_elem = sys_elem.find(f'.//HeaterMult[@index="{i}"]')
                if count_elem is None:
                    count_elem = sys_elem.find(f'HeaterMult[@index="{i}"]')
                if count_elem is None:
                    # Fallback to DHWHeaterCount for backward compatibility
                    count_elem = sys_elem.find(f'.//DHWHeaterCount[@index="{i}"]')
                if count_elem is None:
                    count_elem = sys_elem.find(f'DHWHeaterCount[@index="{i}"]')

                count = self._to_int(count_elem.text) if count_elem is not None and count_elem.text else 1
                counts.append(count)

        # Handle non-indexed heaters (simple reference)
        if not water_heaters:
            heater_elem = sys_elem.find('.//DHWHeater')
            if heater_elem is None:
                heater_elem = sys_elem.find('DHWHeater')

            if heater_elem is not None:
                heater_name = self._get_name(heater_elem) or "WaterHeater"
                heater_id = self.id_registry.generate_id('WH', heater_name, dhw_system_id, 'CIBD22X')

                # Parse properties (same as above)
                heater_type = self.get_property(heater_elem, 'Type') or self.get_property(heater_elem, 'DHWHeaterType') or 'Unknown'
                tank_type = self.get_property(heater_elem, 'TankType')
                storage_volume = self._to_float(self.get_property(heater_elem, 'StorageVol') or self.get_property(heater_elem, 'DHWStorageVol'))
                input_capacity = self._to_float(self.get_property(heater_elem, 'InputCapacity'))
                energy_factor = self._to_float(self.get_property(heater_elem, 'EnergyFactor') or self.get_property(heater_elem, 'DHWHeaterEF'))
                uniform_energy_factor = self._to_float(self.get_property(heater_elem, 'UniformEnergyFactor'))
                thermal_efficiency = self._to_float(self.get_property(heater_elem, 'ThermalEfficiency'))
                first_hour_rating = self._to_float(self.get_property(heater_elem, 'FirstHourRating'))
                recovery_efficiency = self._to_float(self.get_property(heater_elem, 'RecoveryEfficiency'))
                cop = self._to_float(self.get_property(heater_elem, 'COP'))
                compressor_location = self.get_property(heater_elem, 'CompressorLocation')
                fuel_type = self.get_property(heater_elem, 'FuelType') or self.get_property(heater_elem, 'DHWHeaterFuel')
                location = self.get_property(heater_elem, 'Location')

                heater = WaterHeater(
                    id=heater_id,
                    name=heater_name,
                    heater_type=heater_type,
                    tank_type=tank_type,
                    storage_volume_gal=storage_volume,
                    input_capacity_btu_hr=input_capacity,
                    energy_factor=energy_factor,
                    uniform_energy_factor=uniform_energy_factor,
                    thermal_efficiency=thermal_efficiency,
                    first_hour_rating=first_hour_rating,
                    recovery_efficiency=recovery_efficiency,
                    cop=cop,
                    compressor_location=compressor_location,
                    fuel_type=fuel_type,
                    location=location
                )

                water_heaters.append(heater)
                counts.append(1)

        return water_heaters, counts

    def _get_name(self, element: ET.Element) -> Optional[str]:
        """Extract name from element (namespace-aware)."""
        # Try <n> first (CIBD22X short form)
        name = self.get_property(element, 'n')
        if name:
            return name
        # Try <Name> (standard form)
        name = self.get_property(element, 'Name')
        if name:
            return name
        # Try id attribute
        name = element.get('id')
        return name if name else None
