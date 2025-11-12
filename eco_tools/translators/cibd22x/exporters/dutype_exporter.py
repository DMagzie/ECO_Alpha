"""
Dwelling Unit Type Exporter - Residential Unit Type Catalog Exporter
====================================================================

PURPOSE:
Serializes dwelling unit type definitions from InternalRepresentation to CIBD22X XML format.

EXPORT STRATEGY:
1. Export dwelling unit type catalog elements (<DwellUnitType>)
2. Preserve all properties (geometry, appliances, system references)
3. Maintain exact property names for CBECC-Com compatibility

DWELLING UNIT TYPE PROPERTIES:
- Geometry: CondFlrArea (ft²), NumBedrooms
- Appliances: DryerFuel, CookFuel
- HVAC System References: HVACSysType, HVACHtPumpRef, HVACFanRef, HVACDistRef
- IAQ System References: IAQOption, IAQFanRef, IAQFanCnt
- DHW System References: DHWSysRef

CRITICAL FOR CBECC-COM:
DwellUnitType definitions MUST be present in the file for zones that reference them
via DwellUnitTypeRef. Missing dwelling unit types will cause component reference
errors and prevent the file from loading.

PATTERN: Simple Catalog Exporter - mirrors DUTypeParser logic
"""

from typing import List, Dict, Any
import xml.etree.ElementTree as ET
import logging

from .base_exporter import BaseExporter

# Get module logger
logger = logging.getLogger('eco_tools.exporters')


class DUTypeExporter(BaseExporter):
    """Exporter for CIBD22X dwelling unit type catalog elements"""

    def __init__(self):
        """Initialize the dwelling unit type exporter"""
        super().__init__()

    def export_du_types(self, parent: ET.Element, du_types: List[Dict[str, Any]]) -> None:
        """
        Export all dwelling unit types to CIBD22X XML.

        Creates catalog-level dwelling unit type elements (<DwellUnitType>) with
        all properties preserved for round-trip fidelity.

        Args:
            parent: Parent XML element (typically <Building>)
            du_types: List of dwelling unit type dictionaries to export
        """
        if not du_types:
            logger.info("No dwelling unit types to export")
            return

        exported_count = 0

        for du_type in du_types:
            if self._export_single_du_type(parent, du_type):
                exported_count += 1
            else:
                name = du_type.get('name', 'unknown')
                logger.warning(f"Failed to export dwelling unit type '{name}': missing name")

        logger.info(f"Exported {exported_count} dwelling unit types")

    def _export_single_du_type(self, parent: ET.Element, du_type: Dict[str, Any]) -> bool:
        """
        Export a single dwelling unit type element.

        Args:
            parent: Parent XML element
            du_type: Dwelling unit type dictionary to export

        Returns:
            True if export succeeded, False if name missing
        """
        # Validate required properties
        name = du_type.get('name')
        if not name:
            return False

        # Create dwelling unit type element
        du_elem = self.create_element(parent, 'DwellUnitType')

        # Add name (required)
        self.add_text_element(du_elem, 'Name', name)

        # ================================================================
        # GEOMETRY PROPERTIES
        # ================================================================

        # Conditioned floor area (ft²) - Imperial units
        cond_floor_area = du_type.get('cond_floor_area')
        if cond_floor_area is not None:
            self.add_numeric_element(du_elem, 'CondFlrArea', cond_floor_area, precision=2)

        # Number of bedrooms
        num_bedrooms = du_type.get('num_bedrooms')
        if num_bedrooms is not None:
            self.add_text_element(du_elem, 'NumBedrooms', str(num_bedrooms))

        # ================================================================
        # APPLIANCE FUEL TYPES
        # ================================================================

        # Dryer fuel (Electric, Gas)
        dryer_fuel = du_type.get('dryer_fuel')
        if dryer_fuel:
            self.add_text_element(du_elem, 'DryerFuel', dryer_fuel)

        # Cooking fuel (Electric, Gas)
        cook_fuel = du_type.get('cook_fuel')
        if cook_fuel:
            self.add_text_element(du_elem, 'CookFuel', cook_fuel)

        # ================================================================
        # HVAC SYSTEM REFERENCES
        # ================================================================

        # HVAC system type
        hvac_sys_type = du_type.get('hvac_sys_type')
        if hvac_sys_type:
            self.add_text_element(du_elem, 'HVACSysType', hvac_sys_type)

        # HVAC heat pump reference
        hvac_ht_pump_ref = du_type.get('hvac_ht_pump_ref')
        if hvac_ht_pump_ref:
            self.add_text_element(du_elem, 'HVACHtPumpRef', hvac_ht_pump_ref)

        # HVAC fan reference
        hvac_fan_ref = du_type.get('hvac_fan_ref')
        if hvac_fan_ref:
            self.add_text_element(du_elem, 'HVACFanRef', hvac_fan_ref)

        # HVAC distribution reference
        hvac_dist_ref = du_type.get('hvac_dist_ref')
        if hvac_dist_ref:
            self.add_text_element(du_elem, 'HVACDistRef', hvac_dist_ref)

        # ================================================================
        # IAQ SYSTEM REFERENCES
        # ================================================================

        # IAQ option
        iaq_option = du_type.get('iaq_option')
        if iaq_option:
            self.add_text_element(du_elem, 'IAQOption', iaq_option)

        # IAQ fan reference
        iaq_fan_ref = du_type.get('iaq_fan_ref')
        if iaq_fan_ref:
            self.add_text_element(du_elem, 'IAQFanRef', iaq_fan_ref)

        # IAQ fan count
        iaq_fan_cnt = du_type.get('iaq_fan_cnt')
        if iaq_fan_cnt is not None:
            self.add_text_element(du_elem, 'IAQFanCnt', str(iaq_fan_cnt))

        # ================================================================
        # DHW SYSTEM REFERENCES
        # ================================================================

        # DHW system reference
        dhw_sys_ref = du_type.get('dhw_sys_ref')
        if dhw_sys_ref:
            self.add_text_element(du_elem, 'DHWSysRef', dhw_sys_ref)

        return True
