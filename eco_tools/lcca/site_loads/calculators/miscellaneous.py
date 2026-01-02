"""
Miscellaneous Site Load Calculators.

Calculators for:
- EV charging infrastructure
- IT/Telecom rooms
- Water system pumps
- Trash compactors
- Other miscellaneous loads
"""

from __future__ import annotations
from typing import Dict

from .base import BaseSiteLoadCalculator, CalculationResult
from ...whole_building.schema import LoadCategory


class EVChargerCalculator(BaseSiteLoadCalculator):
    """
    Calculator for EV charging infrastructure.

    Supports Level 1, Level 2, and DC fast charging with:
    - CALGreen 2025 requirement auto-calculation
    - ALMS (Automatic Load Management System) modeling
    - Multifamily-specific utilization profiles
    - Seasonal/climate zone adjustments

    CALGreen 2025 Requirements (effective Jan 1, 2026):
    - 1 Level 2 receptacle per dwelling unit at assigned parking
    - 25% of common parking spaces need actual Level 2 chargers
    - Minimum 3.3 kW per station with ALMS
    - Branch circuits rated for 40 amps, chargers at 30 amps minimum
    """

    # Charger power by level (kW)
    CHARGER_POWER = {
        "level_1": 1.4,           # 120V/12A
        "level_2_low": 3.3,       # 208-240V/16A (ALMS minimum)
        "level_2": 7.2,           # 208-240V/32A (standard)
        "level_2_standard": 7.2,  # Alias
        "level_2_high": 11.5,     # 208-240V/48A
        "dc_fast": 50,            # DC fast charger
        "dc_supercharger": 150,
    }

    # Typical utilization by location (hours per port per day)
    # Enhanced for multifamily specifics
    UTILIZATION = {
        # Original categories
        "workplace": 4.0,
        "residential": 3.0,
        "retail": 2.0,
        "public": 1.5,
        # Multifamily-specific (more realistic)
        "mf_assigned": 2.5,    # Dedicated parking - overnight charging
        "mf_shared": 1.5,      # Shared parking - higher turnover, less usage
        "mf_visitor": 0.5,     # Guest parking - infrequent use
    }

    # Seasonal adjustment factors by California climate zone
    # Winter: EV cabin heating increases consumption
    # Summer: A/C increases consumption (less than heating)
    # Values are annual average multipliers
    CLIMATE_ZONE_FACTORS = {
        1: 1.12,   # Arcata - cold, foggy
        2: 1.10,   # Santa Rosa - cool
        3: 1.05,   # Oakland - mild
        4: 1.08,   # San Jose - moderate
        5: 1.06,   # Santa Maria - mild coastal
        6: 1.04,   # Torrance - mild
        7: 1.03,   # San Diego - very mild
        8: 1.05,   # Fullerton - warm
        9: 1.07,   # Burbank - warm, some cold
        10: 1.10,  # Riverside - hot/cold extremes
        11: 1.12,  # Red Bluff - hot/cold extremes
        12: 1.10,  # Sacramento - hot/cold
        13: 1.08,  # Fresno - hot
        14: 1.12,  # Palmdale - hot/cold desert
        15: 1.10,  # Palm Springs - very hot
        16: 1.15,  # Blue Canyon - mountain, cold
    }

    # ALMS (Automatic Load Management System) defaults
    # ALMS reduces simultaneity by dynamically managing charging
    DEFAULT_ALMS_FACTOR = 0.4  # With ALMS, effective simultaneous use drops

    @property
    def category(self) -> LoadCategory:
        return LoadCategory.EV_CHARGER

    def get_default_load_shape(self) -> str:
        return "ev_residential"

    @staticmethod
    def calculate_calgreen_2025_requirements(
        dwelling_units: int,
        common_parking_spaces: int = 0,
    ) -> Dict:
        """
        Calculate CALGreen 2025 EV infrastructure requirements.

        CALGreen 2025 (effective Jan 1, 2026) requires:
        - 1 Level 2-capable receptacle per dwelling unit (assigned parking)
        - 25% of common parking spaces with actual Level 2 chargers
        - Minimum 3.3 kW per station with ALMS

        Args:
            dwelling_units: Number of dwelling units in building
            common_parking_spaces: Number of common/shared parking spaces

        Returns:
            Dict with:
                - dwelling_receptacles: Required unit receptacles
                - common_chargers: Required common area chargers (25%)
                - total_ports: Total charging infrastructure
                - minimum_kw_per_port: CALGreen minimum (3.3 kW)
        """
        import math

        dwelling_receptacles = dwelling_units
        common_chargers = math.ceil(common_parking_spaces * 0.25)

        return {
            "dwelling_receptacles": dwelling_receptacles,
            "common_chargers": common_chargers,
            "total_ports": dwelling_receptacles + common_chargers,
            "minimum_kw_per_port": 3.3,
            "calgreen_version": "2025",
            "effective_date": "2026-01-01",
        }

    def calculate_annual(self, inputs: Dict) -> CalculationResult:
        """
        Calculate annual EV charger energy.

        Standard inputs:
            num_ports: Number of charging ports (required unless calgreen_2025=True)

        CALGreen 2025 auto-calculation:
            calgreen_2025: bool - Enable CALGreen 2025 requirement calculation
            dwelling_units: int - Number of dwelling units
            common_parking_spaces: int - Common area parking spaces (optional)

        Charger configuration:
            charger_level: str - "level_1", "level_2_low", "level_2", "level_2_high",
                                 "dc_fast", "dc_supercharger"
            kw_per_port: float - Override power per port

        Location and utilization:
            location_type: str - "workplace", "residential", "retail", "public",
                                 "mf_assigned", "mf_shared", "mf_visitor"
            hours_per_day: float - Override utilization hours

        ALMS (Automatic Load Management):
            alms_enabled: bool - Enable ALMS (reduces peak demand)
            alms_factor: float - Simultaneity factor with ALMS (default 0.4)

        Climate adjustment:
            climate_zone: int - California climate zone (1-16)

        Other:
            days_per_year: int - Operating days (default 365)
            simultaneity_factor: float - For non-ALMS systems (default 0.5)
        """
        # CALGreen 2025 auto-calculation
        if inputs.get("calgreen_2025"):
            dwelling_units = inputs.get("dwelling_units", 0)
            common_spaces = inputs.get("common_parking_spaces", 0)

            if dwelling_units == 0:
                raise ValueError("calgreen_2025=True requires 'dwelling_units'")

            calgreen_req = self.calculate_calgreen_2025_requirements(
                dwelling_units, common_spaces
            )

            # Use CALGreen calculated ports if num_ports not explicitly set
            if "num_ports" not in inputs:
                inputs["num_ports"] = calgreen_req["total_ports"]

            # Default to ALMS-minimum power if not specified
            if "charger_level" not in inputs and "kw_per_port" not in inputs:
                inputs["charger_level"] = "level_2_low"  # 3.3 kW minimum

            # Enable ALMS by default for CALGreen 2025 compliance
            if "alms_enabled" not in inputs:
                inputs["alms_enabled"] = True

            # Default location for MF CALGreen
            if "location_type" not in inputs:
                inputs["location_type"] = "mf_assigned"

        # Validate required inputs
        valid, error = self.validate_inputs(inputs, ["num_ports"])
        if not valid:
            raise ValueError(error)

        num_ports = int(inputs["num_ports"])
        charger_level = inputs.get("charger_level", "level_2")
        location_type = inputs.get("location_type", "residential")

        # Get power per port
        kw_per_port = inputs.get("kw_per_port")
        if kw_per_port is None:
            kw_per_port = self.CHARGER_POWER.get(charger_level, self.CHARGER_POWER["level_2"])
        kw_per_port = float(kw_per_port)

        # Get utilization
        hours_per_day = inputs.get("hours_per_day")
        if hours_per_day is None:
            hours_per_day = self.UTILIZATION.get(location_type, 3.0)
        hours_per_day = float(hours_per_day)

        # Calculate base annual energy
        days_per_year = float(inputs.get("days_per_year", 365))
        annual_kwh = num_ports * kw_per_port * hours_per_day * days_per_year

        # Apply climate zone adjustment
        climate_zone = inputs.get("climate_zone")
        climate_factor = 1.0
        if climate_zone is not None:
            climate_factor = self.CLIMATE_ZONE_FACTORS.get(int(climate_zone), 1.0)
            annual_kwh *= climate_factor

        # Peak demand calculation
        alms_enabled = inputs.get("alms_enabled", False)
        if alms_enabled:
            # ALMS significantly reduces simultaneity
            simultaneity = float(inputs.get("alms_factor", self.DEFAULT_ALMS_FACTOR))
        else:
            # Standard simultaneity assumption
            simultaneity = float(inputs.get("simultaneity_factor", 0.5))

        peak_kw = num_ports * kw_per_port * simultaneity

        # Load shape based on location
        if location_type == "workplace":
            self._default_load_shape = "ev_workplace"
        else:
            self._default_load_shape = "ev_residential"

        # Build method description
        method_parts = [
            f"EV Chargers ({charger_level}, {location_type}): "
            f"{num_ports} ports × {kw_per_port} kW × {hours_per_day} hrs/day"
        ]
        if climate_zone:
            method_parts.append(f" × {climate_factor:.2f} climate factor (CZ{climate_zone})")
        if alms_enabled:
            method_parts.append(f" [ALMS enabled, {simultaneity:.0%} simultaneity]")
        if inputs.get("calgreen_2025"):
            method_parts.append(" [CALGreen 2025 compliant]")

        return CalculationResult(
            annual_kwh=annual_kwh,
            annual_therms=0.0,
            peak_kw=peak_kw,
            calculation_method="".join(method_parts),
            inputs_used={
                "num_ports": num_ports,
                "charger_level": charger_level,
                "location_type": location_type,
                "kw_per_port": kw_per_port,
                "hours_per_day": hours_per_day,
                "climate_zone": climate_zone,
                "climate_factor": climate_factor,
                "alms_enabled": alms_enabled,
                "simultaneity": simultaneity,
                "calgreen_2025": inputs.get("calgreen_2025", False),
            }
        )


class ITTelecomCalculator(BaseSiteLoadCalculator):
    """
    Calculator for IT/Telecom room energy.

    IT loads are typically constant 24/7 and include:
    - Servers, switches, routers
    - UPS systems (with efficiency losses)
    - Dedicated cooling (if not in CBECC model)

    PUE (Power Usage Effectiveness) accounts for cooling overhead.
    """

    @property
    def category(self) -> LoadCategory:
        return LoadCategory.IT_TELECOM

    def get_default_load_shape(self) -> str:
        return "it_telecom"

    def calculate_annual(self, inputs: Dict) -> CalculationResult:
        """
        Calculate annual IT/Telecom room energy.

        Method 1 - Direct power:
            it_load_kw: Known IT equipment load

        Method 2 - Area-based:
            area_sf: IT room area
            watts_per_sf: Power density (default 50 W/SF)

        Common inputs:
            pue: Power Usage Effectiveness (default 1.5)
            uptime_pct: Percent of year operational (default 100)
        """
        pue = float(inputs.get("pue", 1.5))
        uptime_pct = float(inputs.get("uptime_pct", 100))

        if "it_load_kw" in inputs:
            it_kw = float(inputs["it_load_kw"])
            method = f"IT/Telecom: {it_kw} kW IT load × PUE {pue}"
        elif "area_sf" in inputs:
            area_sf = float(inputs["area_sf"])
            watts_per_sf = float(inputs.get("watts_per_sf", 50))
            it_kw = area_sf * watts_per_sf / 1000
            method = f"IT/Telecom: {area_sf:.0f} SF × {watts_per_sf} W/SF × PUE {pue}"
        else:
            raise ValueError("Must provide either 'it_load_kw' or 'area_sf'")

        # Total load with PUE (includes cooling)
        total_kw = it_kw * pue

        # Annual energy
        hours_per_year = 8760 * uptime_pct / 100
        annual_kwh = total_kw * hours_per_year

        return CalculationResult(
            annual_kwh=annual_kwh,
            annual_therms=0.0,
            peak_kw=total_kw,
            calculation_method=method,
            inputs_used={
                "it_load_kw": it_kw,
                "pue": pue,
                "total_kw": total_kw,
                "uptime_pct": uptime_pct,
            }
        )


class WaterPumpCalculator(BaseSiteLoadCalculator):
    """
    Calculator for water system pumps.

    Covers:
    - Domestic water booster pumps
    - Fire pumps (testing only)
    - Hot water recirculation pumps
    - Sump pumps
    """

    @property
    def category(self) -> LoadCategory:
        return LoadCategory.WATER_PUMPS

    def get_default_load_shape(self) -> str:
        return "flat_24x7"

    def calculate_annual(self, inputs: Dict) -> CalculationResult:
        """
        Calculate annual water pump energy.

        Required inputs:
            pump_type: "booster", "fire", "recirculation", "sump"
            pump_hp: Pump motor horsepower

        Optional inputs:
            motor_efficiency: Motor efficiency (default 0.85)
            hours_per_day: Operating hours (varies by type)
            days_per_year: Operating days (default 365)
        """
        valid, error = self.validate_inputs(inputs, ["pump_type", "pump_hp"])
        if not valid:
            raise ValueError(error)

        pump_type = inputs["pump_type"].lower()
        pump_hp = float(inputs["pump_hp"])
        motor_efficiency = float(inputs.get("motor_efficiency", 0.85))

        # Default hours by pump type
        default_hours = {
            "booster": 6,           # Runs during peak demand
            "fire": 0.5,            # Testing only (~30 min/week)
            "recirculation": 8,     # Runs during occupied hours
            "sump": 0.5,            # Intermittent
        }
        hours_per_day = float(inputs.get("hours_per_day", default_hours.get(pump_type, 4)))
        days_per_year = float(inputs.get("days_per_year", 365))

        # Calculate
        motor_kw = pump_hp * 0.746 / motor_efficiency
        annual_kwh = motor_kw * hours_per_day * days_per_year

        # Fire pumps have special consideration - mostly standby
        if pump_type == "fire":
            # Include standby power for controller
            standby_kw = 0.1
            annual_kwh += standby_kw * 8760

        return CalculationResult(
            annual_kwh=annual_kwh,
            annual_therms=0.0,
            peak_kw=motor_kw,
            calculation_method=f"Water Pump ({pump_type}): {pump_hp} HP × {hours_per_day} hrs/day × {days_per_year} days",
            inputs_used={
                "pump_type": pump_type,
                "pump_hp": pump_hp,
                "motor_efficiency": motor_efficiency,
                "hours_per_day": hours_per_day,
                "motor_kw": motor_kw,
            }
        )


class TrashCompactorCalculator(BaseSiteLoadCalculator):
    """
    Calculator for trash compactor energy.

    Compactors run intermittently based on trash volume.
    Energy = cycles per day × energy per cycle.
    """

    @property
    def category(self) -> LoadCategory:
        return LoadCategory.TRASH_COMPACTOR

    def get_default_load_shape(self) -> str:
        return "trash_compactor"

    def calculate_annual(self, inputs: Dict) -> CalculationResult:
        """
        Calculate annual trash compactor energy.

        Method 1 - Cycle-based:
            cycles_per_day: Number of compaction cycles
            kwh_per_cycle: Energy per cycle (default 0.5 kWh)

        Method 2 - Motor-based:
            motor_hp: Compactor motor HP
            minutes_per_cycle: Run time per cycle
            cycles_per_day: Number of cycles
        """
        cycles_per_day = float(inputs.get("cycles_per_day", 10))
        days_per_year = float(inputs.get("days_per_year", 365))

        if "motor_hp" in inputs:
            motor_hp = float(inputs["motor_hp"])
            minutes_per_cycle = float(inputs.get("minutes_per_cycle", 2))
            motor_efficiency = float(inputs.get("motor_efficiency", 0.85))

            motor_kw = motor_hp * 0.746 / motor_efficiency
            hours_per_cycle = minutes_per_cycle / 60
            kwh_per_cycle = motor_kw * hours_per_cycle
            method = f"Trash Compactor: {motor_hp} HP × {cycles_per_day} cycles/day"
        else:
            kwh_per_cycle = float(inputs.get("kwh_per_cycle", 0.5))
            motor_kw = kwh_per_cycle / (2/60)  # Assume 2 min cycle
            method = f"Trash Compactor: {cycles_per_day} cycles × {kwh_per_cycle} kWh/cycle"

        annual_kwh = kwh_per_cycle * cycles_per_day * days_per_year

        return CalculationResult(
            annual_kwh=annual_kwh,
            annual_therms=0.0,
            peak_kw=motor_kw,
            calculation_method=method,
            inputs_used={
                "cycles_per_day": cycles_per_day,
                "kwh_per_cycle": kwh_per_cycle,
                "days_per_year": days_per_year,
            }
        )


class GenericLoadCalculator(BaseSiteLoadCalculator):
    """
    Generic calculator for miscellaneous loads.

    Provides flexible calculation for loads not covered by
    specific calculators. Supports direct kWh input, power-based,
    or area-based calculations.
    """

    def __init__(self, category: LoadCategory = LoadCategory.MISCELLANEOUS):
        super().__init__()
        self._category = category

    @property
    def category(self) -> LoadCategory:
        return self._category

    def get_default_load_shape(self) -> str:
        return "building_hours"

    def calculate_annual(self, inputs: Dict) -> CalculationResult:
        """
        Calculate annual energy for a generic load.

        Method 1 - Direct:
            annual_kwh: Direct annual kWh input
            annual_therms: Direct annual therms input

        Method 2 - Power-based:
            load_kw: Continuous load in kW
            hours_per_day: Operating hours
            days_per_year: Operating days

        Method 3 - Area-based:
            area_sf: Area in square feet
            watts_per_sf: Power density
            hours_per_year: Operating hours
        """
        if "annual_kwh" in inputs:
            annual_kwh = float(inputs["annual_kwh"])
            annual_therms = float(inputs.get("annual_therms", 0))
            peak_kw = float(inputs.get("peak_kw", annual_kwh / 4380))  # Default assume 12hr/day
            method = f"Direct input: {annual_kwh:,.0f} kWh/year"

        elif "load_kw" in inputs:
            load_kw = float(inputs["load_kw"])
            hours_per_day = float(inputs.get("hours_per_day", 12))
            days_per_year = float(inputs.get("days_per_year", 365))
            annual_kwh = load_kw * hours_per_day * days_per_year
            annual_therms = 0.0
            peak_kw = load_kw
            method = f"Power-based: {load_kw} kW × {hours_per_day} hrs/day"

        elif "area_sf" in inputs:
            area_sf = float(inputs["area_sf"])
            watts_per_sf = float(inputs.get("watts_per_sf", 1.0))
            hours_per_year = float(inputs.get("hours_per_year", 4380))
            connected_kw = area_sf * watts_per_sf / 1000
            annual_kwh = connected_kw * hours_per_year
            annual_therms = 0.0
            peak_kw = connected_kw
            method = f"Area-based: {area_sf:.0f} SF × {watts_per_sf} W/SF"

        else:
            raise ValueError("Must provide 'annual_kwh', 'load_kw', or 'area_sf'")

        return CalculationResult(
            annual_kwh=annual_kwh,
            annual_therms=annual_therms,
            peak_kw=peak_kw,
            calculation_method=method,
            inputs_used=inputs.copy(),
        )
