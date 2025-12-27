"""
Cost mappers for CBECC simulation outputs.

Maps CBECC system types to CostDB codes and applies efficiency adders.
Uses Tier 1 (rules of thumb) approach for cost estimation.

Cost Methodology:
- HVAC: Generic capacity-based costs + efficiency adders
- DHW: Generic capacity-based costs + efficiency adders
- Envelope: Generic material costs by performance tier (no manufacturer-specific)
"""

from dataclasses import dataclass
from typing import Optional, List, Dict, Any, Tuple
import logging

from .costdb import CostDatabase, SystemCost
from .parsers.hvac_secondary import (
    HVACSecondaryOutput, AirSystem, CoolingCoil, HeatingCoil
)
from .parsers.hvac_primary import (
    HVACPrimaryOutput, WaterHeater, Boiler, Chiller
)
from .parsers.envelope import (
    EnvelopeOutput, ExteriorWall, Window, ExteriorRoof, ConstructionMaterial
)

logger = logging.getLogger(__name__)


# =============================================================================
# HVAC System Type Mappings
# =============================================================================

# Map CBECC air system types to CostDB system codes
CBECC_TO_COSTDB_HVAC = {
    # Single zone heat pumps
    'SZHP': 'heat_pump_air',
    'SZAC': 'dx_packaged',
    'PSZ-HP': 'heat_pump_air',
    'PSZ-AC': 'dx_packaged',

    # Single zone VAV
    'SZVAVHP': 'heat_pump_air',
    'SZVAVAC': 'dx_packaged',

    # VRF
    'VRF': 'vrf',

    # Packaged terminal
    'PTAC': 'ptac',
    'PTHP': 'pthp',

    # VAV systems
    'PVAV': 'vav_box',
    'VAV': 'vav_box',

    # Fan coil
    'FPFC': 'fan_coil',
    '4PFC': 'fan_coil',
}

# Map CBECC heating coil types to CostDB codes
HEATING_COIL_TO_COSTDB = {
    'HeatPump': 'heat_pump_air',
    'Furnace': 'furnace_gas',
    'Resistance': 'electric_resistance',
    'HotWater': 'boiler_gas',  # Served by central boiler
}

# Map CBECC DHW types to CostDB codes
DHW_TO_COSTDB = {
    ('Conventional', 'Electricity'): 'water_heater_electric',
    ('Conventional', 'Gas'): 'water_heater_gas',
    ('HeatPump', 'Electricity'): 'water_heater_heat_pump',
    ('Instantaneous', 'Electricity'): 'water_heater_tankless_electric',
    ('Instantaneous', 'Gas'): 'water_heater_tankless_gas',
    ('Storage', 'Electricity'): 'water_heater_electric',
    ('Storage', 'Gas'): 'water_heater_gas',
}


# =============================================================================
# Efficiency Adders (Tier 1 - Rules of Thumb)
# =============================================================================

# Cost multipliers based on efficiency above code minimum
EFFICIENCY_ADDERS = {
    'seer': {
        # SEER ranges → cost multiplier
        (0, 14.3): 1.00,       # Code minimum (2023+ residential split)
        (14.3, 15): 1.05,      # +5%
        (15, 17): 1.10,        # +10%
        (17, 19): 1.18,        # +18%
        (19, 21): 1.25,        # +25%
        (21, 24): 1.35,        # +35%
        (24, 30): 1.45,        # +45%
    },
    'eer': {
        # EER ranges → cost multiplier (commercial)
        (0, 11.0): 1.00,       # Code minimum
        (11.0, 12.0): 1.08,    # +8%
        (12.0, 13.0): 1.15,    # +15%
        (13.0, 14.0): 1.22,    # +22%
        (14.0, 20.0): 1.30,    # +30%
    },
    'hspf': {
        # HSPF ranges → cost multiplier
        (0, 8.8): 1.00,        # Code minimum (2023+ residential)
        (8.8, 9.5): 1.05,      # +5%
        (9.5, 10.0): 1.10,     # +10%
        (10.0, 11.0): 1.18,    # +18%
        (11.0, 12.0): 1.25,    # +25%
        (12.0, 14.0): 1.35,    # +35%
    },
    'cop': {
        # COP ranges → cost multiplier (heat pumps)
        (0, 3.0): 1.00,        # Code minimum
        (3.0, 3.5): 1.08,      # +8%
        (3.5, 4.0): 1.15,      # +15%
        (4.0, 4.5): 1.22,      # +22%
        (4.5, 6.0): 1.30,      # +30%
    },
    'afue': {
        # AFUE ranges → cost multiplier (furnaces)
        (0, 80): 1.00,         # Minimum
        (80, 90): 1.05,        # +5%
        (90, 95): 1.15,        # +15% (condensing)
        (95, 100): 1.25,       # +25% (high-efficiency condensing)
    },
    'thermal_efficiency': {
        # Boiler thermal efficiency → cost multiplier
        (0, 0.80): 1.00,
        (0.80, 0.85): 1.05,
        (0.85, 0.90): 1.12,
        (0.90, 0.95): 1.20,
        (0.95, 1.00): 1.30,
    },
    'uef': {
        # Uniform Energy Factor (water heaters) → cost multiplier
        (0, 0.90): 1.00,       # Standard electric
        (0.90, 2.0): 1.05,     # Improved
        (2.0, 3.0): 1.40,      # Heat pump water heater
        (3.0, 4.0): 1.60,      # High-efficiency HPWH
    },
}


# =============================================================================
# Envelope Material Costs (Generic, $/SF)
# =============================================================================

# Generic material costs - NOT manufacturer-specific
ENVELOPE_MATERIAL_COSTS = {
    # Insulation by R-value tier ($/SF installed)
    'insulation_batt_r11': 0.40,
    'insulation_batt_r13': 0.45,
    'insulation_batt_r15': 0.50,
    'insulation_batt_r19': 0.55,
    'insulation_batt_r21': 0.62,
    'insulation_batt_r30': 0.85,
    'insulation_batt_r38': 1.10,

    'insulation_rigid_r5': 0.80,
    'insulation_rigid_r10': 1.40,
    'insulation_rigid_r15': 2.00,
    'insulation_rigid_r20': 2.60,
    'insulation_rigid_r25': 3.20,
    'insulation_rigid_r30': 3.80,

    'insulation_spray_r20': 1.50,
    'insulation_spray_r30': 2.25,
    'insulation_spray_r40': 3.00,

    # Window by U-factor tier ($/SF installed)
    'window_u055': 40.00,      # Single pane (existing)
    'window_u046': 45.00,      # Standard double
    'window_u040': 52.00,      # Code minimum
    'window_u036': 58.00,      # Better
    'window_u034': 62.00,      # Good
    'window_u032': 68.00,      # Very good
    'window_u030': 72.00,      # Excellent
    'window_u028': 78.00,      # Best
    'window_u025': 85.00,      # Premium

    # SHGC adders ($/SF)
    'shgc_040': 0.00,          # Standard
    'shgc_035': 1.00,          # Low
    'shgc_030': 2.00,          # Lower
    'shgc_025': 3.00,          # Low-E
    'shgc_022': 4.00,          # Very Low
    'shgc_018': 6.00,          # Ultra Low

    # Roof assembly by R-value ($/SF installed)
    'roof_r19': 10.00,
    'roof_r25': 12.00,
    'roof_r30': 13.50,
    'roof_r38': 16.00,
    'roof_r49': 20.00,

    # Cool roof adder ($/SF)
    'cool_roof_063': 0.75,     # Aged reflectance 0.63+
    'cool_roof_070': 1.00,     # Aged reflectance 0.70+

    # Wall framing ($/SF)
    'framing_wood_2x4': 3.50,
    'framing_wood_2x6': 4.25,
    'framing_metal_35': 4.00,
    'framing_metal_6': 5.00,

    # Cladding ($/SF)
    'cladding_stucco': 8.50,
    'cladding_fiber_cement': 7.00,
    'cladding_metal_panel': 12.00,
    'cladding_brick': 18.00,
}


# =============================================================================
# Helper Functions
# =============================================================================

def get_efficiency_adder(metric: str, value: Optional[float]) -> float:
    """
    Get cost multiplier based on efficiency metric value.

    Args:
        metric: Efficiency metric name (seer, hspf, cop, afue, uef)
        value: Efficiency value

    Returns:
        Cost multiplier (1.0 = no adder)
    """
    if value is None:
        return 1.0

    metric_lower = metric.lower()
    if metric_lower not in EFFICIENCY_ADDERS:
        return 1.0

    ranges = EFFICIENCY_ADDERS[metric_lower]
    for (low, high), multiplier in ranges.items():
        if low <= value < high:
            return multiplier

    # If above all ranges, use highest multiplier
    return max(ranges.values())


def get_window_cost_tier(u_factor: float) -> str:
    """Get window cost tier key based on U-factor."""
    if u_factor >= 0.50:
        return 'window_u055'
    elif u_factor >= 0.43:
        return 'window_u046'
    elif u_factor >= 0.38:
        return 'window_u040'
    elif u_factor >= 0.35:
        return 'window_u036'
    elif u_factor >= 0.33:
        return 'window_u034'
    elif u_factor >= 0.31:
        return 'window_u032'
    elif u_factor >= 0.29:
        return 'window_u030'
    elif u_factor >= 0.27:
        return 'window_u028'
    else:
        return 'window_u025'


def get_shgc_adder_tier(shgc: float) -> str:
    """Get SHGC adder tier key."""
    if shgc >= 0.38:
        return 'shgc_040'
    elif shgc >= 0.33:
        return 'shgc_035'
    elif shgc >= 0.28:
        return 'shgc_030'
    elif shgc >= 0.24:
        return 'shgc_025'
    elif shgc >= 0.20:
        return 'shgc_022'
    else:
        return 'shgc_018'


def get_insulation_cost_tier(r_value: float, insulation_type: str = 'batt') -> str:
    """Get insulation cost tier key based on R-value."""
    prefix = f'insulation_{insulation_type}_'

    if insulation_type == 'batt':
        if r_value < 12:
            return f'{prefix}r11'
        elif r_value < 14:
            return f'{prefix}r13'
        elif r_value < 17:
            return f'{prefix}r15'
        elif r_value < 20:
            return f'{prefix}r19'
        elif r_value < 25:
            return f'{prefix}r21'
        elif r_value < 35:
            return f'{prefix}r30'
        else:
            return f'{prefix}r38'

    elif insulation_type == 'rigid':
        if r_value < 8:
            return f'{prefix}r5'
        elif r_value < 12:
            return f'{prefix}r10'
        elif r_value < 18:
            return f'{prefix}r15'
        elif r_value < 22:
            return f'{prefix}r20'
        elif r_value < 28:
            return f'{prefix}r25'
        else:
            return f'{prefix}r30'

    return f'{prefix}r15'  # Default


# =============================================================================
# Cost Mapper Classes
# =============================================================================

@dataclass
class CostBreakdown:
    """Detailed cost breakdown for a component."""
    component_name: str
    base_cost: float
    efficiency_adder: float = 1.0
    regional_factor: float = 1.0
    final_cost: float = 0.0
    notes: str = ''

    def __post_init__(self):
        if self.final_cost == 0:
            self.final_cost = self.base_cost * self.efficiency_adder * self.regional_factor


class HVACCostMapper:
    """
    Map HVAC specifications to costs using CostDB.

    Uses Tier 1 (rules of thumb) approach:
    - Base cost from CostDB by system type and capacity
    - Efficiency adders based on SEER/HSPF/EER/COP
    - Regional factors from CostDB
    """

    def __init__(self, costdb: Optional[CostDatabase] = None, region: str = 'National'):
        """
        Initialize mapper.

        Args:
            costdb: Cost database (uses default if None)
            region: Region for cost adjustments
        """
        self.costdb = costdb
        self.region = region
        self._regional_factor = 1.0

        if costdb:
            rf = costdb.get_regional_factor(region)
            if rf:
                self._regional_factor = rf.combined_factor

    def calculate_hvac_cost(self, hvac: HVACSecondaryOutput) -> Tuple[float, List[CostBreakdown]]:
        """
        Calculate total HVAC cost from simulation output.

        Args:
            hvac: Parsed HVACSecondary output

        Returns:
            Tuple of (total_cost, list of breakdowns)
        """
        breakdowns = []
        total = 0.0

        # Process cooling coils (DX systems)
        for coil in hvac.cooling_coils:
            cost, breakdown = self._calculate_cooling_coil_cost(coil)
            total += cost
            breakdowns.append(breakdown)

        # Process heating coils (heat pumps, furnaces)
        for coil in hvac.heating_coils:
            # Skip resistance/supplemental coils - usually included with HP
            if coil.coil_type == 'Resistance':
                continue
            cost, breakdown = self._calculate_heating_coil_cost(coil)
            total += cost
            breakdowns.append(breakdown)

        return total, breakdowns

    def _calculate_cooling_coil_cost(self, coil: CoolingCoil) -> Tuple[float, CostBreakdown]:
        """Calculate cost for a cooling coil."""
        # Get capacity in tons
        capacity_tons = coil.capacity_net_btuh / 12000

        # Base cost per ton (from typical market data)
        base_cost_per_ton = 1500  # $/ton for standard DX

        # Get efficiency adder
        eff_adder = 1.0
        if coil.seer:
            eff_adder = get_efficiency_adder('seer', coil.seer)
        elif coil.eer:
            eff_adder = get_efficiency_adder('eer', coil.eer)

        # Account for system count
        system_count = coil.system_count or 1

        base_cost = base_cost_per_ton * capacity_tons * system_count
        final_cost = base_cost * eff_adder * self._regional_factor

        breakdown = CostBreakdown(
            component_name=coil.name,
            base_cost=base_cost,
            efficiency_adder=eff_adder,
            regional_factor=self._regional_factor,
            final_cost=final_cost,
            notes=f"{capacity_tons:.1f} tons, SEER {coil.seer or 'N/A'}, x{system_count}"
        )

        return final_cost, breakdown

    def _calculate_heating_coil_cost(self, coil: HeatingCoil) -> Tuple[float, CostBreakdown]:
        """Calculate cost for a heating coil."""
        # Get capacity in MBH
        capacity_mbh = coil.capacity_net_btuh / 1000

        # Base cost per MBH (varies by type)
        if coil.coil_type == 'HeatPump':
            base_cost_per_mbh = 50  # Heat pump coil cost
            eff_adder = get_efficiency_adder('hspf', coil.hspf) if coil.hspf else \
                        get_efficiency_adder('cop', coil.cop) if coil.cop else 1.0
        elif coil.coil_type == 'Furnace':
            base_cost_per_mbh = 30  # Gas furnace
            eff_adder = get_efficiency_adder('afue', coil.afue) if coil.afue else 1.0
        else:
            base_cost_per_mbh = 25
            eff_adder = 1.0

        system_count = coil.system_count or 1

        base_cost = base_cost_per_mbh * capacity_mbh * system_count
        final_cost = base_cost * eff_adder * self._regional_factor

        breakdown = CostBreakdown(
            component_name=coil.name,
            base_cost=base_cost,
            efficiency_adder=eff_adder,
            regional_factor=self._regional_factor,
            final_cost=final_cost,
            notes=f"{capacity_mbh:.0f} MBH, Type: {coil.coil_type}, x{system_count}"
        )

        return final_cost, breakdown


class DHWCostMapper:
    """
    Map DHW/Central Plant specifications to costs.

    Uses Tier 1 approach with efficiency adders.
    """

    def __init__(self, costdb: Optional[CostDatabase] = None, region: str = 'National'):
        self.costdb = costdb
        self.region = region
        self._regional_factor = 1.0

        if costdb:
            rf = costdb.get_regional_factor(region)
            if rf:
                self._regional_factor = rf.combined_factor

    def calculate_dhw_cost(self, hvac_primary: HVACPrimaryOutput) -> Tuple[float, List[CostBreakdown]]:
        """
        Calculate total DHW/central plant cost.

        Args:
            hvac_primary: Parsed HVACPrimary output

        Returns:
            Tuple of (total_cost, list of breakdowns)
        """
        breakdowns = []
        total = 0.0

        # Water heaters
        for wh in hvac_primary.water_heaters:
            cost, breakdown = self._calculate_water_heater_cost(wh)
            total += cost
            breakdowns.append(breakdown)

        # Boilers
        for boiler in hvac_primary.boilers:
            cost, breakdown = self._calculate_boiler_cost(boiler)
            total += cost
            breakdowns.append(breakdown)

        # Chillers
        for chiller in hvac_primary.chillers:
            cost, breakdown = self._calculate_chiller_cost(chiller)
            total += cost
            breakdowns.append(breakdown)

        return total, breakdowns

    def _calculate_water_heater_cost(self, wh: WaterHeater) -> Tuple[float, CostBreakdown]:
        """Calculate water heater cost."""
        # Base cost by type and size
        if wh.heater_type == 'HeatPump':
            base_cost = 4500  # HPWH premium
            eff_metric = 'uef'
            eff_value = wh.energy_factor if wh.energy_factor and wh.energy_factor > 0 else 2.5
        elif wh.fuel == 'Gas':
            base_cost = 3500
            eff_metric = 'thermal_efficiency'
            eff_value = wh.thermal_efficiency
        else:
            base_cost = 2500
            eff_metric = 'thermal_efficiency'
            eff_value = wh.thermal_efficiency

        # Size adjustment
        if wh.storage_capacity_gal > 80:
            base_cost *= 1.5
        elif wh.storage_capacity_gal > 50:
            base_cost *= 1.2

        eff_adder = get_efficiency_adder(eff_metric, eff_value)
        count = wh.count or 1

        base_cost *= count
        final_cost = base_cost * eff_adder * self._regional_factor

        breakdown = CostBreakdown(
            component_name=wh.name,
            base_cost=base_cost,
            efficiency_adder=eff_adder,
            regional_factor=self._regional_factor,
            final_cost=final_cost,
            notes=f"{wh.storage_capacity_gal:.0f} gal, {wh.heater_type}, x{count}"
        )

        return final_cost, breakdown

    def _calculate_boiler_cost(self, boiler: Boiler) -> Tuple[float, CostBreakdown]:
        """Calculate boiler cost."""
        capacity_mbh = boiler.rated_capacity_btuh / 1000

        # Base cost per MBH
        if boiler.draft_type == 'Condensing':
            base_cost_per_mbh = 55
        else:
            base_cost_per_mbh = 45

        eff_adder = get_efficiency_adder('thermal_efficiency', boiler.thermal_efficiency)

        base_cost = base_cost_per_mbh * capacity_mbh
        final_cost = base_cost * eff_adder * self._regional_factor

        breakdown = CostBreakdown(
            component_name=boiler.name,
            base_cost=base_cost,
            efficiency_adder=eff_adder,
            regional_factor=self._regional_factor,
            final_cost=final_cost,
            notes=f"{capacity_mbh:.0f} MBH, {boiler.draft_type or 'Standard'}"
        )

        return final_cost, breakdown

    def _calculate_chiller_cost(self, chiller: Chiller) -> Tuple[float, CostBreakdown]:
        """Calculate chiller cost."""
        capacity_tons = chiller.rated_capacity_btuh / 12000

        # Base cost per ton (varies by type and size)
        if chiller.chiller_type == 'Centrifugal':
            base_cost_per_ton = 800
        elif chiller.chiller_type == 'Screw':
            base_cost_per_ton = 600
        else:
            base_cost_per_ton = 500

        # Size adjustment (economy of scale)
        if capacity_tons > 500:
            base_cost_per_ton *= 0.85
        elif capacity_tons > 200:
            base_cost_per_ton *= 0.92

        eff_adder = get_efficiency_adder('cop', chiller.cop)

        base_cost = base_cost_per_ton * capacity_tons
        final_cost = base_cost * eff_adder * self._regional_factor

        breakdown = CostBreakdown(
            component_name=chiller.name,
            base_cost=base_cost,
            efficiency_adder=eff_adder,
            regional_factor=self._regional_factor,
            final_cost=final_cost,
            notes=f"{capacity_tons:.0f} tons, COP {chiller.cop or 'N/A'}"
        )

        return final_cost, breakdown


class EnvelopeCostMapper:
    """
    Map envelope specifications to material costs.

    Uses ONLY generic material costs (no manufacturer-specific).
    Costs calculated by material type and performance tier.
    """

    def __init__(self, region: str = 'National', regional_factor: float = 1.0):
        self.region = region
        self._regional_factor = regional_factor

    def calculate_envelope_cost(self, envelope: EnvelopeOutput) -> Tuple[float, List[CostBreakdown]]:
        """
        Calculate total envelope cost.

        Args:
            envelope: Parsed Envelope output

        Returns:
            Tuple of (total_cost, list of breakdowns)
        """
        breakdowns = []
        total = 0.0

        # Windows
        for window in envelope.windows:
            cost, breakdown = self._calculate_window_cost(window)
            total += cost
            breakdowns.append(breakdown)

        # Walls (insulation component only - framing assumed similar)
        wall_insulation_cost = self._calculate_wall_insulation_cost(envelope)
        if wall_insulation_cost > 0:
            total += wall_insulation_cost
            breakdowns.append(CostBreakdown(
                component_name="Wall Insulation",
                base_cost=wall_insulation_cost / self._regional_factor,
                regional_factor=self._regional_factor,
                final_cost=wall_insulation_cost,
                notes=f"Total wall area: {envelope.building_areas.total_wall_area_sf:.0f} SF"
            ))

        # Roofs
        roof_cost = self._calculate_roof_cost(envelope)
        if roof_cost > 0:
            total += roof_cost
            breakdowns.append(CostBreakdown(
                component_name="Roof Assembly",
                base_cost=roof_cost / self._regional_factor,
                regional_factor=self._regional_factor,
                final_cost=roof_cost,
                notes=f"Roof area: {envelope.building_areas.total_roof_area_sf:.0f} SF"
            ))

        return total, breakdowns

    def _calculate_window_cost(self, window: Window) -> Tuple[float, CostBreakdown]:
        """Calculate cost for a window."""
        # Get base cost by U-factor tier
        u_tier = get_window_cost_tier(window.u_factor)
        base_cost_per_sf = ENVELOPE_MATERIAL_COSTS.get(u_tier, 52.0)

        # Add SHGC adder
        shgc_tier = get_shgc_adder_tier(window.shgc)
        shgc_adder = ENVELOPE_MATERIAL_COSTS.get(shgc_tier, 0)

        total_per_sf = base_cost_per_sf + shgc_adder
        base_cost = total_per_sf * window.area_sf
        final_cost = base_cost * self._regional_factor

        breakdown = CostBreakdown(
            component_name=window.name,
            base_cost=base_cost,
            regional_factor=self._regional_factor,
            final_cost=final_cost,
            notes=f"{window.area_sf:.0f} SF, U={window.u_factor:.2f}, SHGC={window.shgc:.2f}"
        )

        return final_cost, breakdown

    def _calculate_wall_insulation_cost(self, envelope: EnvelopeOutput) -> float:
        """Calculate wall insulation cost based on R-value."""
        # Get total wall R-value from materials
        total_r = envelope.total_wall_r_value or 13  # Default R-13

        # Determine insulation type from materials
        insulation_type = 'batt'  # Default
        for mat in envelope.construction_materials:
            if 'rigid' in mat.material_type.lower() or 'board' in mat.material_type.lower():
                if mat.r_value > 5:
                    insulation_type = 'rigid'
                    break

        tier = get_insulation_cost_tier(total_r, insulation_type)
        cost_per_sf = ENVELOPE_MATERIAL_COSTS.get(tier, 0.55)

        total_wall_area = envelope.building_areas.total_wall_area_sf
        return cost_per_sf * total_wall_area * self._regional_factor

    def _calculate_roof_cost(self, envelope: EnvelopeOutput) -> float:
        """Calculate roof assembly cost."""
        # Get roof R-value
        total_r = envelope.total_roof_r_value or 25  # Default R-25

        # Get base cost by R-value tier
        if total_r < 22:
            cost_per_sf = ENVELOPE_MATERIAL_COSTS['roof_r19']
        elif total_r < 28:
            cost_per_sf = ENVELOPE_MATERIAL_COSTS['roof_r25']
        elif total_r < 35:
            cost_per_sf = ENVELOPE_MATERIAL_COSTS['roof_r30']
        elif total_r < 45:
            cost_per_sf = ENVELOPE_MATERIAL_COSTS['roof_r38']
        else:
            cost_per_sf = ENVELOPE_MATERIAL_COSTS['roof_r49']

        # Add cool roof premium if applicable
        avg_reflectance = envelope.average_roof_reflectance or 0
        if avg_reflectance >= 0.70:
            cost_per_sf += ENVELOPE_MATERIAL_COSTS['cool_roof_070']
        elif avg_reflectance >= 0.63:
            cost_per_sf += ENVELOPE_MATERIAL_COSTS['cool_roof_063']

        # Calculate using roof area from exterior roofs
        total_roof_area = sum(r.area_sf for r in envelope.exterior_roofs if r.area_sf)
        if total_roof_area == 0:
            total_roof_area = envelope.building_areas.total_roof_area_sf

        return cost_per_sf * total_roof_area * self._regional_factor
