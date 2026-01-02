"""
Base Site Load Calculator.

Provides common functionality for all site load calculators including:
- Load shape application for 8760 generation
- Input validation
- Audit trail generation
"""

from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, List, Tuple, Optional, Any

from ..load_shapes import LoadShapeLibrary, LoadShapeProfile
from ...whole_building.schema import HourlyRecord, SiteLoadDetail, LoadCategory


@dataclass
class CalculationResult:
    """Result of a site load calculation."""
    annual_kwh: float = 0.0
    annual_therms: float = 0.0
    peak_kw: float = 0.0
    calculation_method: str = ""
    inputs_used: Dict = None

    def __post_init__(self):
        if self.inputs_used is None:
            self.inputs_used = {}


class BaseSiteLoadCalculator(ABC):
    """
    Abstract base class for site load calculators.

    Subclasses must implement:
    - calculate_annual(): Calculate annual energy totals
    - get_default_load_shape(): Return appropriate load shape name
    """

    def __init__(self):
        self.load_shapes = LoadShapeLibrary

    @property
    @abstractmethod
    def category(self) -> LoadCategory:
        """Return the load category this calculator handles."""
        pass

    @abstractmethod
    def calculate_annual(self, inputs: Dict) -> CalculationResult:
        """
        Calculate annual energy totals from inputs.

        Args:
            inputs: Dictionary of calculation inputs

        Returns:
            CalculationResult with annual_kwh, annual_therms, peak_kw
        """
        pass

    @abstractmethod
    def get_default_load_shape(self) -> str:
        """Return the default load shape profile name for this category."""
        pass

    def calculate(
        self,
        inputs: Dict,
        load_shape_name: Optional[str] = None,
        name: Optional[str] = None,
    ) -> SiteLoadDetail:
        """
        Calculate site load with full 8760 hourly profile.

        Args:
            inputs: Calculation inputs
            load_shape_name: Optional override for load shape profile
            name: Optional name for this load

        Returns:
            SiteLoadDetail with annual totals and 8760 hourly data
        """
        # Calculate annual totals
        result = self.calculate_annual(inputs)

        # Get load shape profile
        shape_name = load_shape_name or self.get_default_load_shape()
        profile = self.load_shapes.get_profile(shape_name)

        # Generate 8760 hourly records
        hourly = self._generate_hourly(result, profile)

        return SiteLoadDetail(
            category=self.category,
            name=name or self.category.value.replace("_", " ").title(),
            annual_kwh=result.annual_kwh,
            annual_therms=result.annual_therms,
            peak_kw=result.peak_kw,
            hourly=hourly,
            inputs=result.inputs_used,
            calculation_method=result.calculation_method,
            load_shape_profile=shape_name,
            is_modeled_in_simulation=inputs.get("is_modeled_in_simulation", False),
        )

    def _generate_hourly(
        self,
        result: CalculationResult,
        profile: LoadShapeProfile
    ) -> List[HourlyRecord]:
        """Generate 8760 hourly records from annual totals and load shape."""
        hourly_kwh = profile.apply(result.annual_kwh)
        hourly_therms = profile.apply(result.annual_therms) if result.annual_therms > 0 else [0.0] * 8760

        # Month-day-hour structure
        month_days = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
        records = []
        hour_idx = 0

        for month, days in enumerate(month_days, start=1):
            for day in range(1, days + 1):
                for hour in range(1, 25):
                    if hour_idx < len(hourly_kwh):
                        kwh = hourly_kwh[hour_idx]
                        therms = hourly_therms[hour_idx] if hourly_therms else 0.0

                        records.append(HourlyRecord(
                            month=month,
                            day=day,
                            hour=hour,
                            elec_kwh=kwh,
                            gas_therms=therms,
                            demand_kw=kwh,  # Hourly kWh = kW for that hour
                            lighting_kwh=kwh if self.category in [
                                LoadCategory.INTERIOR_LIGHTING,
                                LoadCategory.PARKING,
                                LoadCategory.SITE_LIGHTING,
                            ] else 0.0,
                        ))
                        hour_idx += 1

        return records

    def validate_inputs(self, inputs: Dict, required: List[str]) -> Tuple[bool, str]:
        """
        Validate that required inputs are present.

        Args:
            inputs: Input dictionary
            required: List of required keys

        Returns:
            Tuple of (is_valid, error_message)
        """
        missing = [key for key in required if key not in inputs or inputs[key] is None]
        if missing:
            return False, f"Missing required inputs: {', '.join(missing)}"
        return True, ""
