"""
Pool and Spa Site Load Calculators.

Calculators for:
- Pool circulation pumps
- Pool heaters (gas and electric)
- Spa equipment

Based on:
- ENERGY STAR pool pump curves
- DOE pool heater baselines
- GBCI Pool Energy Calculator methodology
"""

from __future__ import annotations
from typing import Dict

from .base import BaseSiteLoadCalculator, CalculationResult
from ...whole_building.schema import LoadCategory


# ENERGY STAR pool pump performance data
# Flow rate (GPM) → Watts for variable speed pumps
PUMP_CURVES = {
    "variable_speed": {
        30: 150,
        40: 220,
        50: 300,
        60: 400,
        70: 520,
        80: 680,
    },
    "single_speed": {
        50: 1500,
        75: 2000,
        100: 2500,
    },
}

# DOE pool heater baselines (kBtu/hr/SF of pool surface)
# Varies by climate and pool type
HEATER_BASELINES = {
    # kBtu per SF per month for different pool types and months
    "outdoor_uncovered": {
        1: 3.5, 2: 3.2, 3: 2.8, 4: 2.3, 5: 1.8,
        6: 1.2, 7: 1.0, 8: 1.2, 9: 1.8, 10: 2.5, 11: 3.0, 12: 3.5
    },
    "outdoor_covered": {
        1: 1.8, 2: 1.6, 3: 1.4, 4: 1.2, 5: 0.9,
        6: 0.6, 7: 0.5, 8: 0.6, 9: 0.9, 10: 1.3, 11: 1.5, 12: 1.8
    },
    "indoor": {
        1: 1.0, 2: 1.0, 3: 0.9, 4: 0.8, 5: 0.7,
        6: 0.6, 7: 0.6, 8: 0.6, 9: 0.7, 10: 0.8, 11: 0.9, 12: 1.0
    },
}


class PoolPumpCalculator(BaseSiteLoadCalculator):
    """
    Calculator for pool circulation pump energy.

    Supports variable-speed and single-speed pumps.
    Variable-speed pumps are significantly more efficient
    and run at lower speeds most of the time.

    Formula:
        kWh = pump_watts × hours_per_day × days_per_year / 1000
    """

    @property
    def category(self) -> LoadCategory:
        return LoadCategory.POOL_PUMP

    def get_default_load_shape(self) -> str:
        return "pool_pump"

    def calculate_annual(self, inputs: Dict) -> CalculationResult:
        """
        Calculate annual pool pump energy.

        Required inputs:
            pool_volume_gal: Pool volume in gallons

        Optional inputs:
            pump_type: "variable_speed" or "single_speed" (default variable)
            turnover_rate: Pool turnovers per day (default 2)
            hours_per_day: Pump hours (default calculated from turnover)
            pump_hp: Pump horsepower (for single-speed)
            pump_efficiency: Motor efficiency (default 0.85)
        """
        valid, error = self.validate_inputs(inputs, ["pool_volume_gal"])
        if not valid:
            raise ValueError(error)

        volume = float(inputs["pool_volume_gal"])
        pump_type = inputs.get("pump_type", "variable_speed")
        turnover_rate = float(inputs.get("turnover_rate", 2))

        # Calculate required flow rate
        # Volume × turnovers / hours = GPM needed
        # Typically run 8-12 hours for 2 turnovers
        default_hours = volume * turnover_rate / 60 / 60  # Approximate hours for flow
        default_hours = max(8, min(default_hours, 16))  # Clamp to 8-16 hours
        hours_per_day = float(inputs.get("hours_per_day", default_hours))

        flow_rate = volume * turnover_rate / hours_per_day / 60  # GPM

        # Get pump power
        if pump_type == "variable_speed":
            # Variable speed pumps can run at lower flow rates
            # Average flow is lower than peak
            avg_flow = flow_rate * 0.6  # Running at ~60% speed much of the time
            watts = self._interpolate_pump_curve(avg_flow, "variable_speed")
        else:
            # Single speed runs at full power
            if "pump_hp" in inputs:
                hp = float(inputs["pump_hp"])
                efficiency = float(inputs.get("pump_efficiency", 0.85))
                watts = hp * 746 / efficiency
            else:
                watts = self._interpolate_pump_curve(flow_rate, "single_speed")

        # Calculate annual energy
        days = float(inputs.get("days_per_year", 365))
        annual_kwh = watts * hours_per_day * days / 1000
        peak_kw = watts / 1000

        return CalculationResult(
            annual_kwh=annual_kwh,
            annual_therms=0.0,
            peak_kw=peak_kw,
            calculation_method=f"Pool Pump ({pump_type}): {watts:.0f}W × {hours_per_day:.1f} hrs/day × {days:.0f} days",
            inputs_used={
                "pool_volume_gal": volume,
                "pump_type": pump_type,
                "flow_rate_gpm": flow_rate,
                "pump_watts": watts,
                "hours_per_day": hours_per_day,
                "days_per_year": days,
            }
        )

    def _interpolate_pump_curve(self, gpm: float, pump_type: str) -> float:
        """Interpolate pump curve to get watts for a given GPM."""
        curve = PUMP_CURVES.get(pump_type, PUMP_CURVES["variable_speed"])
        gpm_values = sorted(curve.keys())

        # Clamp to curve range
        if gpm <= gpm_values[0]:
            return curve[gpm_values[0]]
        if gpm >= gpm_values[-1]:
            return curve[gpm_values[-1]]

        # Linear interpolation
        for i, low_gpm in enumerate(gpm_values[:-1]):
            high_gpm = gpm_values[i + 1]
            if low_gpm <= gpm <= high_gpm:
                ratio = (gpm - low_gpm) / (high_gpm - low_gpm)
                return curve[low_gpm] + ratio * (curve[high_gpm] - curve[low_gpm])

        return curve[gpm_values[-1]]


class PoolHeaterCalculator(BaseSiteLoadCalculator):
    """
    Calculator for pool heater energy.

    Supports both gas and electric heat pump pool heaters.
    Uses DOE baseline methodology for heating load estimation.

    For gas heaters:
        therms = (heat_load_kbtu × months_operated) / (efficiency × 100)

    For heat pumps:
        kWh = (heat_load_kbtu × months_operated) / (COP × 3.412)
    """

    @property
    def category(self) -> LoadCategory:
        return LoadCategory.POOL_HEATER

    def get_default_load_shape(self) -> str:
        return "pool_heater"

    def calculate_annual(self, inputs: Dict) -> CalculationResult:
        """
        Calculate annual pool heater energy.

        Required inputs:
            pool_area_sf: Pool surface area in square feet
            heater_type: "gas" or "electric_heat_pump"

        Optional inputs:
            pool_type: "outdoor_uncovered", "outdoor_covered", or "indoor"
            heater_efficiency: Gas efficiency (default 0.82) or heat pump COP (default 5.5)
            months_operated: Months per year pool is heated (default 12)
            setpoint_f: Pool temperature setpoint (default 82°F)
        """
        valid, error = self.validate_inputs(inputs, ["pool_area_sf", "heater_type"])
        if not valid:
            raise ValueError(error)

        area_sf = float(inputs["pool_area_sf"])
        heater_type = inputs["heater_type"].lower()
        pool_type = inputs.get("pool_type", "outdoor_uncovered")

        # Get monthly heating factors
        monthly_factors = HEATER_BASELINES.get(pool_type, HEATER_BASELINES["outdoor_uncovered"])

        # Calculate annual heat load (kBtu)
        months_operated = int(inputs.get("months_operated", 12))
        active_months = list(range(1, months_operated + 1))

        annual_kbtu = sum(
            monthly_factors.get(month, 2.0) * area_sf
            for month in active_months
        )

        # Calculate energy based on heater type
        if heater_type == "gas":
            efficiency = float(inputs.get("heater_efficiency", 0.82))
            annual_therms = annual_kbtu / (efficiency * 100)
            annual_kwh = 0.0
            peak_kw = 0.0
            method = f"Pool Gas Heater: {area_sf:.0f} SF × {annual_kbtu:.0f} kBtu ÷ {efficiency} eff"
        else:  # electric heat pump
            cop = float(inputs.get("heater_efficiency", 5.5))
            annual_kwh = annual_kbtu / (cop * 3.412)
            annual_therms = 0.0
            # Peak is tricky - heat pump size varies
            # Assume sized for coldest month peak load
            max_monthly = max(monthly_factors.values())
            peak_kbtu_hr = max_monthly * area_sf / (30 * 8)  # Spread over 8 hrs/day
            peak_kw = peak_kbtu_hr / (cop * 3.412)
            method = f"Pool Heat Pump: {area_sf:.0f} SF × {annual_kbtu:.0f} kBtu ÷ COP {cop}"

        return CalculationResult(
            annual_kwh=annual_kwh,
            annual_therms=annual_therms,
            peak_kw=peak_kw,
            calculation_method=method,
            inputs_used={
                "pool_area_sf": area_sf,
                "pool_type": pool_type,
                "heater_type": heater_type,
                "annual_heat_load_kbtu": annual_kbtu,
                "months_operated": months_operated,
            }
        )


class SpaCalculator(BaseSiteLoadCalculator):
    """
    Calculator for spa/hot tub energy.

    Spas have higher heating requirements than pools due to
    higher temperature setpoint (typically 102-104°F vs 82°F).
    Also includes jet pump energy.

    Based on California Energy Commission spa energy data.
    """

    @property
    def category(self) -> LoadCategory:
        return LoadCategory.SPA

    def get_default_load_shape(self) -> str:
        return "spa"

    def calculate_annual(self, inputs: Dict) -> CalculationResult:
        """
        Calculate annual spa energy.

        Required inputs:
            spa_volume_gal: Spa volume in gallons

        Optional inputs:
            heater_type: "gas" or "electric" (default electric)
            heater_efficiency: Gas efficiency or electric COP
            has_cover: Whether spa has insulating cover (default True)
            hours_per_week: Jet pump usage hours (default 10)
            jet_pump_hp: Jet pump horsepower (default 2)
        """
        valid, error = self.validate_inputs(inputs, ["spa_volume_gal"])
        if not valid:
            raise ValueError(error)

        volume = float(inputs["spa_volume_gal"])
        heater_type = inputs.get("heater_type", "electric")
        has_cover = inputs.get("has_cover", True)

        # Heating energy
        # Base energy: ~3000 kWh/year for 400 gal spa (covered)
        # Uncovered loses ~40% more heat
        base_kwh_per_gal = 7.5 if has_cover else 10.5
        heating_kwh = volume * base_kwh_per_gal

        if heater_type == "gas":
            # Convert to therms
            # At 80% efficiency, about 30 therms/year per 100 gal
            efficiency = float(inputs.get("heater_efficiency", 0.80))
            heating_therms = (volume / 100) * 30 / efficiency
            heating_kwh_final = 0.0
        else:
            efficiency = float(inputs.get("heater_efficiency", 1.0))
            heating_kwh_final = heating_kwh / efficiency
            heating_therms = 0.0

        # Jet pump energy
        hours_per_week = float(inputs.get("hours_per_week", 10))
        jet_hp = float(inputs.get("jet_pump_hp", 2))
        jet_efficiency = 0.85

        jet_watts = jet_hp * 746 / jet_efficiency
        jet_kwh = jet_watts * hours_per_week * 52 / 1000

        # Circulation pump (runs continuously at low power)
        circ_kwh = 300  # Approximately 300 kWh/year for circ pump

        total_kwh = heating_kwh_final + jet_kwh + circ_kwh
        peak_kw = jet_watts / 1000  # Peak is during jet operation

        return CalculationResult(
            annual_kwh=total_kwh,
            annual_therms=heating_therms,
            peak_kw=peak_kw,
            calculation_method=f"Spa ({heater_type}): {volume:.0f} gal, {jet_hp} HP jets, {'covered' if has_cover else 'uncovered'}",
            inputs_used={
                "spa_volume_gal": volume,
                "heater_type": heater_type,
                "has_cover": has_cover,
                "heating_kwh": heating_kwh_final,
                "heating_therms": heating_therms,
                "jet_kwh": jet_kwh,
                "jet_pump_hp": jet_hp,
            }
        )
