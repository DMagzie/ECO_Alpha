"""
Vertical Transport Site Load Calculators.

Calculators for:
- Elevators (passenger and freight)
- Escalators

Based on ASHRAE equipment power data and industry standards.
Elevator motor energy is never modeled in CBECC, always calculated separately.
"""

from __future__ import annotations
from typing import Dict

from .base import BaseSiteLoadCalculator, CalculationResult
from ...whole_building.schema import LoadCategory


# Default annual energy by elevator type (kWh/year per elevator)
# Based on ASHRAE and industry data
ELEVATOR_DEFAULTS = {
    "hydraulic_low_rise": 5000,      # 2-6 floors, low traffic
    "hydraulic_mid_rise": 7000,      # 4-8 floors, moderate traffic
    "traction_mid_rise": 8000,       # 6-15 floors
    "traction_high_rise": 12000,     # 15+ floors
    "machine_room_less": 6000,       # MRL elevators (more efficient)
    "freight": 4000,                 # Freight/service (less frequent use)
}

# Escalator power consumption (W per step width foot)
ESCALATOR_POWER = {
    "32_inch": 4500,    # 32" wide commercial
    "40_inch": 6000,    # 40" wide commercial
    "48_inch": 8000,    # 48" wide commercial (transit)
}


class ElevatorCalculator(BaseSiteLoadCalculator):
    """
    Calculator for elevator energy consumption.

    Elevators are NOT modeled in CBECC/CSE simulations.
    Only the elevator machine room HVAC (if any) is modeled.
    The elevator motor energy must always be calculated separately.

    Formula options:
    1. Default by type: annual_kwh = default_kwh × num_elevators × adjustment
    2. Motor-based: annual_kwh = motor_kw × hours × load_factor
    """

    @property
    def category(self) -> LoadCategory:
        return LoadCategory.ELEVATOR

    def get_default_load_shape(self) -> str:
        return "elevator"

    def calculate_annual(self, inputs: Dict) -> CalculationResult:
        """
        Calculate annual elevator energy.

        Required inputs:
            num_elevators: Number of elevators

        Optional inputs:
            elevator_type: Type for default lookup (default "hydraulic_low_rise")
            num_floors: Number of floors served
            motor_hp: Motor horsepower (if known)
            trips_per_day: Average trips per day (if known)
            building_type: "residential", "commercial", "hospital"
            annual_kwh_override: Direct annual kWh input
        """
        valid, error = self.validate_inputs(inputs, ["num_elevators"])
        if not valid:
            raise ValueError(error)

        num_elevators = int(inputs["num_elevators"])
        elevator_type = inputs.get("elevator_type", "hydraulic_low_rise")
        building_type = inputs.get("building_type", "residential")

        # Check for override
        if "annual_kwh_override" in inputs:
            base_kwh = float(inputs["annual_kwh_override"])
            method = f"Elevator (override): {num_elevators} × {base_kwh:,.0f} kWh"
        elif "motor_hp" in inputs:
            # Motor-based calculation
            motor_hp = float(inputs["motor_hp"])
            trips = float(inputs.get("trips_per_day", 100))
            trip_duration_min = float(inputs.get("trip_duration_min", 0.5))
            motor_efficiency = float(inputs.get("motor_efficiency", 0.85))

            # Daily operating hours from trips
            daily_hours = trips * trip_duration_min / 60
            annual_hours = daily_hours * 365

            # kWh = HP × 0.746 / efficiency × hours × load factor
            load_factor = 0.5  # Average loading is less than peak
            motor_kw = motor_hp * 0.746 / motor_efficiency
            base_kwh = motor_kw * annual_hours * load_factor

            method = f"Elevator (motor): {motor_hp} HP × {annual_hours:.0f} hrs × {load_factor} LF"
        else:
            # Use defaults
            base_kwh = ELEVATOR_DEFAULTS.get(elevator_type, ELEVATOR_DEFAULTS["hydraulic_low_rise"])

            # Adjust for building type
            type_factors = {
                "residential": 0.8,   # Lower traffic
                "commercial": 1.0,    # Baseline
                "hotel": 1.1,         # Higher traffic
                "hospital": 1.4,      # Much higher traffic
            }
            type_factor = type_factors.get(building_type, 1.0)

            # Adjust for number of floors
            num_floors = int(inputs.get("num_floors", 5))
            if num_floors > 15:
                floor_factor = 1.3
            elif num_floors > 8:
                floor_factor = 1.1
            else:
                floor_factor = 1.0

            base_kwh = base_kwh * type_factor * floor_factor
            method = f"Elevator ({elevator_type}, {building_type}): {base_kwh:,.0f} kWh/unit"

        # Calculate totals
        annual_kwh = base_kwh * num_elevators

        # Peak demand - assume 30% of connected load running at once
        if "motor_hp" in inputs:
            motor_hp = float(inputs["motor_hp"])
            connected_kw = motor_hp * 0.746
        else:
            # Estimate motor size from annual energy
            # Typical elevator: 10-25 HP
            connected_kw = 15 * 0.746  # Assume 15 HP average

        peak_kw = connected_kw * num_elevators * 0.3

        return CalculationResult(
            annual_kwh=annual_kwh,
            annual_therms=0.0,
            peak_kw=peak_kw,
            calculation_method=f"{method} × {num_elevators} units",
            inputs_used={
                "num_elevators": num_elevators,
                "elevator_type": elevator_type,
                "building_type": building_type,
                "annual_kwh_per_elevator": base_kwh,
            }
        )


class EscalatorCalculator(BaseSiteLoadCalculator):
    """
    Calculator for escalator energy consumption.

    Escalators typically run continuously during building hours,
    with some energy savings from variable speed drives and
    standby modes when unoccupied.
    """

    @property
    def category(self) -> LoadCategory:
        return LoadCategory.ESCALATOR

    def get_default_load_shape(self) -> str:
        return "escalator"

    def calculate_annual(self, inputs: Dict) -> CalculationResult:
        """
        Calculate annual escalator energy.

        Required inputs:
            num_escalators: Number of escalators

        Optional inputs:
            step_width: "32_inch", "40_inch", or "48_inch" (default 32)
            rise_ft: Vertical rise in feet (default 15)
            hours_per_day: Operating hours (default 14)
            has_vfd: Variable frequency drive for speed control (default False)
            has_standby: Standby mode when empty (default True)
        """
        valid, error = self.validate_inputs(inputs, ["num_escalators"])
        if not valid:
            raise ValueError(error)

        num_escalators = int(inputs["num_escalators"])
        step_width = inputs.get("step_width", "32_inch")
        rise_ft = float(inputs.get("rise_ft", 15))
        hours_per_day = float(inputs.get("hours_per_day", 14))
        has_vfd = inputs.get("has_vfd", False)
        has_standby = inputs.get("has_standby", True)

        # Base power from step width
        base_watts = ESCALATOR_POWER.get(step_width, ESCALATOR_POWER["32_inch"])

        # Adjust for rise (longer = more power)
        rise_factor = rise_ft / 15  # Normalize to 15 ft baseline
        adjusted_watts = base_watts * rise_factor

        # Apply efficiency factors
        if has_vfd:
            adjusted_watts *= 0.7  # VFD saves ~30%
        if has_standby:
            adjusted_watts *= 0.8  # Standby mode saves ~20%

        # Annual energy
        days_per_year = float(inputs.get("days_per_year", 365))
        annual_hours = hours_per_day * days_per_year
        annual_kwh = adjusted_watts * annual_hours / 1000 * num_escalators

        peak_kw = adjusted_watts * num_escalators / 1000

        return CalculationResult(
            annual_kwh=annual_kwh,
            annual_therms=0.0,
            peak_kw=peak_kw,
            calculation_method=f"Escalator ({step_width}): {adjusted_watts:.0f}W × {annual_hours:.0f} hrs × {num_escalators} units",
            inputs_used={
                "num_escalators": num_escalators,
                "step_width": step_width,
                "rise_ft": rise_ft,
                "hours_per_day": hours_per_day,
                "has_vfd": has_vfd,
                "has_standby": has_standby,
                "watts_per_unit": adjusted_watts,
            }
        )
