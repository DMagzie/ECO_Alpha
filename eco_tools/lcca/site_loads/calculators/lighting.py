"""
Lighting Site Load Calculators.

Calculators for:
- Interior lighting (common areas not in CBECC model)
- Parking structure lighting
- Site/exterior lighting

Based on Title 24 2022 LPD (Lighting Power Density) requirements.
"""

from __future__ import annotations
from typing import Dict

from .base import BaseSiteLoadCalculator, CalculationResult
from ...whole_building.schema import LoadCategory


# Title 24 2022 LPD values by space type (W/SF)
# Reference: Table 140.6-C
TITLE24_LPD = {
    # Common Area Space Types
    "corridor": 0.66,
    "corridor_facility_manufacturing": 0.41,
    "corridor_facility_all_other": 0.66,
    "corridor_hospital": 0.99,
    "lobby": 0.90,
    "lobby_hotel": 1.06,
    "lobby_performing_arts_theater": 2.00,
    "lobby_motion_picture_theater": 1.12,
    "stairway": 0.69,
    "stairwell": 0.69,
    "restroom": 0.98,
    "electrical_mechanical": 0.42,
    "elevator_lobby": 0.75,

    # Parking
    "parking_garage_building": 0.19,
    "parking_garage_top": 0.07,  # Open air parking
    "parking_area_open": 0.04,   # Outdoor lot

    # Common areas
    "fitness_exercise": 0.72,
    "lounge_recreation": 0.73,
    "dining_area": 0.65,
    "food_preparation": 1.21,
    "laundry": 0.60,
    "locker_room": 0.75,
    "storage": 0.63,

    # Office types (rarely as site load, usually modeled)
    "office_enclosed": 0.90,
    "office_open": 0.61,
    "conference_meeting": 0.97,
    "copy_room": 0.72,

    # Default for unknown
    "default": 0.50,
}


class InteriorLightingCalculator(BaseSiteLoadCalculator):
    """
    Calculator for interior lighting in common areas.

    Calculates lighting energy for spaces that may not be
    included in the CBECC model (e.g., common corridors, lobbies).

    Formula:
        kWh = (area_sf × LPD × hours_per_year × control_factor × diversity) / 1000
    """

    @property
    def category(self) -> LoadCategory:
        return LoadCategory.INTERIOR_LIGHTING

    def get_default_load_shape(self) -> str:
        return "interior_lighting"

    def calculate_annual(self, inputs: Dict) -> CalculationResult:
        """
        Calculate annual interior lighting energy.

        Required inputs:
            area_sf: Floor area in square feet
            space_type: Type of space (for LPD lookup)

        Optional inputs:
            lpd_override: Override Title 24 LPD (W/SF)
            hours_per_year: Operating hours (default 4380 = 12hr/day)
            control_factor: Lighting controls savings (default 0.8)
            diversity_factor: Not all lights on at once (default 0.9)
        """
        valid, error = self.validate_inputs(inputs, ["area_sf", "space_type"])
        if not valid:
            raise ValueError(error)

        area_sf = float(inputs["area_sf"])
        space_type = inputs["space_type"].lower().replace(" ", "_")

        # Get LPD
        lpd = inputs.get("lpd_override")
        if lpd is None:
            lpd = TITLE24_LPD.get(space_type, TITLE24_LPD["default"])
        lpd = float(lpd)

        # Get factors
        hours = float(inputs.get("hours_per_year", 4380))  # Default 12 hr/day
        control = float(inputs.get("control_factor", 0.8))
        diversity = float(inputs.get("diversity_factor", 0.9))

        # Calculate
        connected_kw = area_sf * lpd / 1000
        annual_kwh = connected_kw * hours * control * diversity
        peak_kw = connected_kw * diversity

        return CalculationResult(
            annual_kwh=annual_kwh,
            annual_therms=0.0,
            peak_kw=peak_kw,
            calculation_method=f"Interior Lighting: {area_sf:,.0f} SF × {lpd} W/SF × {hours} hrs × {control} control × {diversity} diversity",
            inputs_used={
                "area_sf": area_sf,
                "space_type": space_type,
                "lpd_w_sf": lpd,
                "hours_per_year": hours,
                "control_factor": control,
                "diversity_factor": diversity,
            }
        )


class ParkingLightingCalculator(BaseSiteLoadCalculator):
    """
    Calculator for parking structure lighting.

    Handles both enclosed garages and open parking areas.

    Formula:
        kWh = (area_sf × LPD × hours_per_year × control_factor) / 1000
    """

    @property
    def category(self) -> LoadCategory:
        return LoadCategory.PARKING

    def get_default_load_shape(self) -> str:
        return "parking_lighting"

    def calculate_annual(self, inputs: Dict) -> CalculationResult:
        """
        Calculate annual parking lighting energy.

        Required inputs:
            area_sf: Parking area in square feet
            parking_type: "enclosed", "rooftop", or "open"

        Optional inputs:
            lpd_override: Override Title 24 LPD
            hours_per_year: Operating hours (default 4380 for 24/7 with daylight)
            control_factor: Lighting controls savings (default 0.7 for occupancy sensors)
        """
        valid, error = self.validate_inputs(inputs, ["area_sf", "parking_type"])
        if not valid:
            raise ValueError(error)

        area_sf = float(inputs["area_sf"])
        parking_type = inputs["parking_type"].lower()

        # Map parking type to LPD
        lpd_map = {
            "enclosed": TITLE24_LPD["parking_garage_building"],
            "rooftop": TITLE24_LPD["parking_garage_top"],
            "open": TITLE24_LPD["parking_area_open"],
        }

        lpd = inputs.get("lpd_override")
        if lpd is None:
            lpd = lpd_map.get(parking_type, TITLE24_LPD["parking_garage_building"])
        lpd = float(lpd)

        # Hours - parking lighting varies by type
        default_hours = {
            "enclosed": 4380,  # 24/7 but with daylight sensing
            "rooftop": 2190,   # Primarily night hours
            "open": 2920,      # Dusk to dawn (~8 hrs/night)
        }
        hours = float(inputs.get("hours_per_year", default_hours.get(parking_type, 4380)))

        # Control factor - typically have occupancy sensors
        control = float(inputs.get("control_factor", 0.7))

        # Calculate
        connected_kw = area_sf * lpd / 1000
        annual_kwh = connected_kw * hours * control
        peak_kw = connected_kw * control

        return CalculationResult(
            annual_kwh=annual_kwh,
            annual_therms=0.0,
            peak_kw=peak_kw,
            calculation_method=f"Parking Lighting ({parking_type}): {area_sf:,.0f} SF × {lpd} W/SF × {hours} hrs × {control} control",
            inputs_used={
                "area_sf": area_sf,
                "parking_type": parking_type,
                "lpd_w_sf": lpd,
                "hours_per_year": hours,
                "control_factor": control,
            }
        )


class SiteLightingCalculator(BaseSiteLoadCalculator):
    """
    Calculator for exterior/site lighting.

    Covers walkways, landscaping, signage, and facade lighting.

    Two calculation methods:
    1. Area-based: area_sf × LPD
    2. Fixture-based: num_fixtures × watts_per_fixture
    """

    @property
    def category(self) -> LoadCategory:
        return LoadCategory.SITE_LIGHTING

    def get_default_load_shape(self) -> str:
        return "site_lighting"

    def calculate_annual(self, inputs: Dict) -> CalculationResult:
        """
        Calculate annual site lighting energy.

        Method 1 - Area-based:
            area_sf: Site lighting area
            lpd: Lighting power density (default 0.05 W/SF)

        Method 2 - Fixture-based:
            num_fixtures: Number of light fixtures
            watts_per_fixture: Watts per fixture

        Common inputs:
            hours_per_year: Operating hours (default 4380 for dusk-dawn)
            control_factor: Controls savings (default 1.0 - typically no controls)
        """
        # Determine calculation method
        if "num_fixtures" in inputs:
            method = "fixture"
            num_fixtures = int(inputs["num_fixtures"])
            watts = float(inputs.get("watts_per_fixture", 100))
            connected_kw = num_fixtures * watts / 1000
        elif "area_sf" in inputs:
            method = "area"
            area_sf = float(inputs["area_sf"])
            lpd = float(inputs.get("lpd", 0.05))
            connected_kw = area_sf * lpd / 1000
        else:
            raise ValueError("Must provide either 'num_fixtures' or 'area_sf'")

        # Common factors
        hours = float(inputs.get("hours_per_year", 4380))  # ~12 hr/night
        control = float(inputs.get("control_factor", 1.0))

        # Calculate
        annual_kwh = connected_kw * hours * control
        peak_kw = connected_kw

        # Build method description
        if method == "fixture":
            method_desc = f"Site Lighting: {num_fixtures} fixtures × {watts}W × {hours} hrs"
        else:
            method_desc = f"Site Lighting: {area_sf:,.0f} SF × {lpd} W/SF × {hours} hrs"

        return CalculationResult(
            annual_kwh=annual_kwh,
            annual_therms=0.0,
            peak_kw=peak_kw,
            calculation_method=method_desc,
            inputs_used=inputs.copy(),
        )


class ParkingVentilationCalculator(BaseSiteLoadCalculator):
    """
    Calculator for parking garage ventilation/exhaust fans.

    This is a key "sometimes modeled" load - it CAN be modeled in CBECC
    via PrkgGarExhFlow and PrkgGarExhFanPwr properties on parking zones,
    but is often omitted in compliance-only models.

    Use the CbeccModeledLoadDetector to determine if this load is
    already in the simulation before calculating as a site load.

    Design Guidelines (Title 24, IMC, ASHRAE 62.1):
    - Minimum 0.75 CFM/SF OR CO-based demand control
    - Fan power: 0.3-0.5 W/CFM for typical systems
    - CO control reduces runtime to ~30-50% of continuous

    Formula:
        kWh = (exhaust_cfm × W_per_CFM × hours_per_year) / 1000
    """

    # Fan power defaults by system type (W/CFM)
    FAN_POWER_DEFAULTS = {
        "constant_volume": 0.35,      # Simple continuous exhaust
        "variable_speed": 0.25,       # VFD with CO control
        "energy_star": 0.20,          # High-efficiency
        "jet_fan": 0.15,              # Jet fan system
    }

    @property
    def category(self) -> LoadCategory:
        return LoadCategory.PARKING

    def get_default_load_shape(self) -> str:
        return "parking_ventilation"

    def calculate_annual(self, inputs: Dict) -> CalculationResult:
        """
        Calculate annual parking garage ventilation energy.

        Required inputs (one of these):
            exhaust_cfm: Total exhaust airflow in CFM
            OR
            parking_area_sf: Parking area (will use 0.75 CFM/SF)

        Optional inputs:
            fan_power_w_per_cfm: Fan power (default 0.35 W/CFM)
            fan_type: "constant_volume", "variable_speed", "energy_star", "jet_fan"
            co_control: True if CO-based demand control (default True for new)
            hours_per_year: Operating hours (default calculated from control type)
            efficiency: Motor efficiency (default 0.85)
        """
        # Determine exhaust CFM
        if "exhaust_cfm" in inputs:
            exhaust_cfm = float(inputs["exhaust_cfm"])
        elif "parking_area_sf" in inputs:
            parking_area_sf = float(inputs["parking_area_sf"])
            cfm_per_sf = float(inputs.get("cfm_per_sf", 0.75))
            exhaust_cfm = parking_area_sf * cfm_per_sf
        else:
            raise ValueError("Must provide either 'exhaust_cfm' or 'parking_area_sf'")

        # Get fan power
        fan_type = inputs.get("fan_type", "constant_volume")
        fan_power = inputs.get("fan_power_w_per_cfm")
        if fan_power is None:
            fan_power = self.FAN_POWER_DEFAULTS.get(fan_type, 0.35)
        fan_power = float(fan_power)

        # Determine operating hours
        co_control = inputs.get("co_control", False)
        if "hours_per_year" in inputs:
            hours = float(inputs["hours_per_year"])
        elif co_control:
            # CO control typically reduces runtime to ~35% of 24/7
            hours = 8760 * 0.35
        else:
            # Continuous operation
            hours = 8760

        # Motor efficiency
        efficiency = float(inputs.get("efficiency", 0.85))

        # Calculate
        connected_kw = exhaust_cfm * fan_power / 1000 / efficiency
        annual_kwh = connected_kw * hours
        peak_kw = connected_kw

        # Build method description
        control_desc = "CO demand control" if co_control else "continuous"
        method_desc = (
            f"Parking Ventilation: {exhaust_cfm:,.0f} CFM × {fan_power} W/CFM × "
            f"{hours:,.0f} hrs ({control_desc}) / {efficiency} eff"
        )

        return CalculationResult(
            annual_kwh=annual_kwh,
            annual_therms=0.0,
            peak_kw=peak_kw,
            calculation_method=method_desc,
            inputs_used={
                "exhaust_cfm": exhaust_cfm,
                "fan_type": fan_type,
                "fan_power_w_per_cfm": fan_power,
                "hours_per_year": hours,
                "co_control": co_control,
                "efficiency": efficiency,
            }
        )


# Convenience function to get LPD for a space type
def get_title24_lpd(space_type: str) -> float:
    """Get Title 24 2022 LPD for a space type."""
    key = space_type.lower().replace(" ", "_")
    return TITLE24_LPD.get(key, TITLE24_LPD["default"])


# List all available space types
def list_space_types() -> list:
    """List all available space types for LPD lookup."""
    return list(TITLE24_LPD.keys())
