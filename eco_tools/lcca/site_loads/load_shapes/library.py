"""
Load Shape Profile Library.

Provides standard load shape profiles for generating 8760 hourly data
from annual energy totals. Each profile represents typical usage patterns
for different site load categories.

Load Shape Concept:
    Annual kWh x Load Shape Profile = 8760 Hourly kWh

The profile is a list of 8760 hourly multipliers that sum to 1.0.
When applied to an annual total, the result is the hourly distribution.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
import json
from pathlib import Path


@dataclass
class LoadShapeProfile:
    """
    8760 hourly multipliers that sum to 1.0.

    When applied to an annual energy total, produces hourly values
    that represent the typical usage pattern for that load type.
    """
    name: str
    category: str
    description: str = ""
    hourly_factors: List[float] = field(default_factory=list)  # 8760 values

    def apply(self, annual_value: float) -> List[float]:
        """
        Apply profile to annual total, returning 8760 hourly values.

        Args:
            annual_value: Annual energy (kWh or therms)

        Returns:
            List of 8760 hourly values
        """
        if not self.hourly_factors:
            return [0.0] * 8760

        return [annual_value * factor for factor in self.hourly_factors]

    def validate(self) -> Tuple[bool, str]:
        """Validate profile integrity."""
        if len(self.hourly_factors) != 8760:
            return False, f"Expected 8760 factors, got {len(self.hourly_factors)}"

        total = sum(self.hourly_factors)
        if abs(total - 1.0) > 0.001:
            return False, f"Factors should sum to 1.0, got {total}"

        if any(f < 0 for f in self.hourly_factors):
            return False, "Negative factors not allowed"

        return True, "Valid"


class LoadShapeGenerator:
    """
    Factory for generating standard load shape profiles.

    Generates profiles based on typical usage patterns for different
    load categories, accounting for:
    - Operating hours (start/end time)
    - Weekend factors
    - Seasonal variation
    - Day/night patterns
    """

    # Month lengths for non-leap year
    MONTH_DAYS = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]

    @classmethod
    def generate_building_hours(
        cls,
        name: str = "Building Hours",
        start_hour: int = 6,
        end_hour: int = 22,
        weekend_factor: float = 0.3,
        overnight_factor: float = 0.1,
    ) -> LoadShapeProfile:
        """
        Generate a typical building operating hours profile.

        Peak during business hours (start_hour to end_hour),
        reduced on weekends, minimal overnight.

        Args:
            name: Profile name
            start_hour: Operating start (0-23)
            end_hour: Operating end (0-23)
            weekend_factor: Multiplier for weekend hours (0-1)
            overnight_factor: Multiplier for overnight hours (0-1)

        Returns:
            LoadShapeProfile with 8760 hourly factors
        """
        factors = []

        day_of_year = 0
        for month, days in enumerate(cls.MONTH_DAYS, start=1):
            for day in range(1, days + 1):
                day_of_year += 1
                # Simplified weekend detection (every 7th and 1st day = weekend)
                # For better accuracy, use actual calendar
                is_weekend = (day_of_year % 7) in [0, 6]

                for hour in range(24):
                    hour_1indexed = hour + 1  # Our format uses 1-24

                    if start_hour <= hour_1indexed < end_hour:
                        # Operating hours
                        factor = 1.0
                        if is_weekend:
                            factor *= weekend_factor
                    else:
                        # Non-operating hours
                        factor = overnight_factor

                    factors.append(factor)

        # Normalize to sum = 1.0
        total = sum(factors)
        factors = [f / total for f in factors]

        return LoadShapeProfile(
            name=name,
            category="building_hours",
            description=f"Building hours {start_hour}:00-{end_hour}:00, weekend factor {weekend_factor}",
            hourly_factors=factors,
        )

    @classmethod
    def generate_flat_24x7(cls, name: str = "Flat 24/7") -> LoadShapeProfile:
        """
        Generate a flat 24/7 profile (constant load all hours).

        Useful for:
        - IT/telecom rooms
        - Security systems
        - Fire life safety
        - Refrigeration
        """
        factor = 1.0 / 8760
        factors = [factor] * 8760

        return LoadShapeProfile(
            name=name,
            category="flat_24x7",
            description="Constant load 24 hours/day, 7 days/week",
            hourly_factors=factors,
        )

    @classmethod
    def generate_daylight_inverse(
        cls,
        name: str = "Daylight Inverse",
        min_daylight_hours: int = 9,
        max_daylight_hours: int = 15,
    ) -> LoadShapeProfile:
        """
        Generate inverse daylight profile (more load at night).

        Useful for:
        - Parking lighting
        - Site lighting
        - Security lighting

        Load is higher when it's dark, lower during daylight.
        Daylight hours vary by month (shorter in winter, longer in summer).

        Args:
            name: Profile name
            min_daylight_hours: Shortest daylight (winter solstice)
            max_daylight_hours: Longest daylight (summer solstice)
        """
        factors = []

        # Approximate daylight hours by month (Northern hemisphere)
        # This is a simplified model - could be enhanced with lat/long
        monthly_daylight = [
            10,  # Jan
            11,  # Feb
            12,  # Mar
            13,  # Apr
            14,  # May
            15,  # Jun
            15,  # Jul
            14,  # Aug
            13,  # Sep
            12,  # Oct
            11,  # Nov
            10,  # Dec
        ]

        for month, days in enumerate(cls.MONTH_DAYS, start=1):
            daylight_hours = monthly_daylight[month - 1]
            sunrise = 12 - daylight_hours // 2  # Approximate sunrise hour
            sunset = sunrise + daylight_hours    # Approximate sunset hour

            for day in range(1, days + 1):
                for hour in range(24):
                    hour_1indexed = hour + 1

                    # Dark hours get full load, daylight hours get reduced
                    if hour_1indexed < sunrise or hour_1indexed >= sunset:
                        factor = 1.0
                    else:
                        factor = 0.1  # Some minimal standby during day

                    factors.append(factor)

        # Normalize
        total = sum(factors)
        factors = [f / total for f in factors]

        return LoadShapeProfile(
            name=name,
            category="daylight_inverse",
            description="Inverse daylight pattern - more load at night",
            hourly_factors=factors,
        )

    @classmethod
    def generate_daytime_peak(
        cls,
        name: str = "Daytime Peak",
        start_hour: int = 8,
        end_hour: int = 18,
        weekend_factor: float = 1.0,
    ) -> LoadShapeProfile:
        """
        Generate daytime peak profile.

        Useful for:
        - Pool pumps
        - EV charging (workplace)
        - Office HVAC supplement

        Args:
            name: Profile name
            start_hour: Peak period start
            end_hour: Peak period end
            weekend_factor: Multiplier for weekends
        """
        factors = []

        day_of_year = 0
        for month, days in enumerate(cls.MONTH_DAYS, start=1):
            for day in range(1, days + 1):
                day_of_year += 1
                is_weekend = (day_of_year % 7) in [0, 6]

                for hour in range(24):
                    hour_1indexed = hour + 1

                    if start_hour <= hour_1indexed < end_hour:
                        factor = 1.0
                        if is_weekend:
                            factor *= weekend_factor
                    else:
                        factor = 0.0

                    factors.append(factor)

        # Normalize
        total = sum(factors)
        if total > 0:
            factors = [f / total for f in factors]
        else:
            factors = [1.0 / 8760] * 8760

        return LoadShapeProfile(
            name=name,
            category="daytime_peak",
            description=f"Daytime peak {start_hour}:00-{end_hour}:00",
            hourly_factors=factors,
        )

    @classmethod
    def generate_evening_peak(
        cls,
        name: str = "Evening Peak",
        start_hour: int = 17,
        end_hour: int = 22,
        weekend_factor: float = 0.8,
    ) -> LoadShapeProfile:
        """
        Generate evening peak profile.

        Useful for:
        - Residential EV charging
        - Common area evening activities
        - Pool heating
        """
        factors = []

        day_of_year = 0
        for month, days in enumerate(cls.MONTH_DAYS, start=1):
            for day in range(1, days + 1):
                day_of_year += 1
                is_weekend = (day_of_year % 7) in [0, 6]

                for hour in range(24):
                    hour_1indexed = hour + 1

                    if start_hour <= hour_1indexed < end_hour:
                        factor = 1.0
                        if is_weekend:
                            factor *= weekend_factor
                    else:
                        factor = 0.1

                    factors.append(factor)

        total = sum(factors)
        factors = [f / total for f in factors]

        return LoadShapeProfile(
            name=name,
            category="evening_peak",
            description=f"Evening peak {start_hour}:00-{end_hour}:00",
            hourly_factors=factors,
        )

    @classmethod
    def generate_morning_peak(
        cls,
        name: str = "Morning Peak",
        start_hour: int = 5,
        end_hour: int = 9,
    ) -> LoadShapeProfile:
        """
        Generate morning peak profile.

        Useful for:
        - Pool/spa heating
        - Morning hot water demand
        """
        factors = []

        for month, days in enumerate(cls.MONTH_DAYS, start=1):
            for day in range(1, days + 1):
                for hour in range(24):
                    hour_1indexed = hour + 1

                    if start_hour <= hour_1indexed < end_hour:
                        factor = 1.0
                    else:
                        factor = 0.05

                    factors.append(factor)

        total = sum(factors)
        factors = [f / total for f in factors]

        return LoadShapeProfile(
            name=name,
            category="morning_peak",
            description=f"Morning peak {start_hour}:00-{end_hour}:00",
            hourly_factors=factors,
        )

    @classmethod
    def generate_elevator(
        cls,
        name: str = "Elevator",
        morning_peak: Tuple[int, int] = (7, 10),
        evening_peak: Tuple[int, int] = (16, 19),
        base_factor: float = 0.3,
        weekend_factor: float = 0.5,
    ) -> LoadShapeProfile:
        """
        Generate elevator usage profile with morning/evening peaks.

        Typical commercial building pattern with commute hour peaks.

        Args:
            name: Profile name
            morning_peak: (start_hour, end_hour) for morning peak
            evening_peak: (start_hour, end_hour) for evening peak
            base_factor: Base load factor outside peaks
            weekend_factor: Multiplier for weekends
        """
        factors = []

        day_of_year = 0
        for month, days in enumerate(cls.MONTH_DAYS, start=1):
            for day in range(1, days + 1):
                day_of_year += 1
                is_weekend = (day_of_year % 7) in [0, 6]

                for hour in range(24):
                    hour_1indexed = hour + 1

                    # Check if in peak periods
                    in_morning = morning_peak[0] <= hour_1indexed < morning_peak[1]
                    in_evening = evening_peak[0] <= hour_1indexed < evening_peak[1]

                    if in_morning or in_evening:
                        factor = 1.0
                    elif 6 <= hour_1indexed <= 22:  # Daytime
                        factor = base_factor
                    else:  # Overnight
                        factor = 0.1

                    if is_weekend:
                        factor *= weekend_factor

                    factors.append(factor)

        total = sum(factors)
        factors = [f / total for f in factors]

        return LoadShapeProfile(
            name=name,
            category="elevator",
            description="Elevator with morning/evening commute peaks",
            hourly_factors=factors,
        )


class LoadShapeLibrary:
    """
    Library of pre-generated load shape profiles.

    Provides standard profiles for common site load categories and
    supports loading custom profiles from JSON files.
    """

    _profiles: Dict[str, LoadShapeProfile] = {}
    _initialized: bool = False

    @classmethod
    def initialize(cls) -> None:
        """Initialize library with standard profiles."""
        if cls._initialized:
            return

        generator = LoadShapeGenerator

        # Generate standard profiles
        cls._profiles = {
            # Flat profiles
            "flat_24x7": generator.generate_flat_24x7(),

            # Building hours variants
            "building_hours": generator.generate_building_hours(),
            "building_hours_extended": generator.generate_building_hours(
                name="Building Hours Extended",
                start_hour=5,
                end_hour=23,
            ),

            # Lighting profiles
            "parking_lighting": generator.generate_daylight_inverse(
                name="Parking Lighting"
            ),
            "site_lighting": generator.generate_daylight_inverse(
                name="Site Lighting"
            ),
            "interior_lighting": generator.generate_building_hours(
                name="Interior Lighting",
                start_hour=6,
                end_hour=22,
                weekend_factor=0.5,
            ),

            # Pool profiles
            "pool_pump": generator.generate_daytime_peak(
                name="Pool Pump",
                start_hour=8,
                end_hour=18,
                weekend_factor=1.0,
            ),
            "pool_heater": generator.generate_morning_peak(
                name="Pool Heater",
                start_hour=5,
                end_hour=9,
            ),
            "spa": generator.generate_evening_peak(
                name="Spa",
                start_hour=16,
                end_hour=22,
            ),

            # Transport
            "elevator": generator.generate_elevator(),
            "escalator": generator.generate_building_hours(
                name="Escalator",
                start_hour=6,
                end_hour=22,
                weekend_factor=0.7,
            ),

            # EV charging
            "ev_workplace": generator.generate_daytime_peak(
                name="EV Workplace Charging",
                start_hour=9,
                end_hour=17,
                weekend_factor=0.2,
            ),
            "ev_residential": generator.generate_evening_peak(
                name="EV Residential Charging",
                start_hour=18,
                end_hour=6,
                weekend_factor=1.0,
            ),

            # IT and continuous
            "it_telecom": generator.generate_flat_24x7(name="IT/Telecom"),
            "security": generator.generate_flat_24x7(name="Security Systems"),
            "fire_safety": generator.generate_flat_24x7(name="Fire Life Safety"),

            # Miscellaneous
            "common_laundry": generator.generate_building_hours(
                name="Common Laundry",
                start_hour=7,
                end_hour=21,
                weekend_factor=1.2,  # Higher on weekends
            ),
            "trash_compactor": generator.generate_building_hours(
                name="Trash Compactor",
                start_hour=10,
                end_hour=20,
                weekend_factor=0.5,
                overnight_factor=0.0,
            ),
        }

        cls._initialized = True

    @classmethod
    def get_profile(cls, name: str) -> LoadShapeProfile:
        """
        Get a load shape profile by name.

        Args:
            name: Profile name (e.g., "building_hours", "flat_24x7")

        Returns:
            LoadShapeProfile, or flat_24x7 if name not found
        """
        cls.initialize()

        profile = cls._profiles.get(name)
        if profile:
            return profile

        # Fall back to flat 24/7 if not found
        return cls._profiles["flat_24x7"]

    @classmethod
    def get_profile_for_category(cls, category: str) -> LoadShapeProfile:
        """
        Get recommended profile for a site load category.

        Args:
            category: LoadCategory value (e.g., "interior_lighting")

        Returns:
            Recommended LoadShapeProfile for that category
        """
        cls.initialize()

        # Category to profile mapping
        category_map = {
            "interior_lighting": "interior_lighting",
            "parking": "parking_lighting",
            "site_lighting": "site_lighting",
            "pool_pump": "pool_pump",
            "pool_heater": "pool_heater",
            "spa": "spa",
            "elevator": "elevator",
            "escalator": "escalator",
            "ev_charger": "ev_residential",  # Default to residential
            "it_telecom": "it_telecom",
            "security_systems": "security",
            "fire_life_safety": "fire_safety",
            "common_laundry": "common_laundry",
            "trash_compactor": "trash_compactor",
            "water_pumps": "flat_24x7",
            "miscellaneous": "building_hours",
        }

        profile_name = category_map.get(category, "flat_24x7")
        return cls.get_profile(profile_name)

    @classmethod
    def list_profiles(cls) -> List[str]:
        """List all available profile names."""
        cls.initialize()
        return list(cls._profiles.keys())

    @classmethod
    def load_profile_from_json(cls, filepath: str | Path) -> LoadShapeProfile:
        """
        Load a custom profile from JSON file.

        JSON format:
        {
            "name": "Custom Profile",
            "category": "custom",
            "description": "Description",
            "hourly_factors": [0.0001, 0.0001, ...]  // 8760 values
        }
        """
        filepath = Path(filepath)
        with open(filepath, 'r') as f:
            data = json.load(f)

        return LoadShapeProfile(
            name=data.get("name", filepath.stem),
            category=data.get("category", "custom"),
            description=data.get("description", ""),
            hourly_factors=data.get("hourly_factors", []),
        )

    @classmethod
    def register_profile(cls, profile: LoadShapeProfile) -> None:
        """Register a custom profile in the library."""
        cls.initialize()
        cls._profiles[profile.name.lower().replace(" ", "_")] = profile
