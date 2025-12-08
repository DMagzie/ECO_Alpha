"""
Time-of-Use (TOU) Rate Engine for LCCA.

Provides:
- TOU schedule definitions for California utilities
- Hourly energy cost calculations by TOU period
- Demand charge calculations from monthly peaks
- Common utility tariff templates
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from enum import Enum
from datetime import datetime


class TouPeriod(Enum):
    """Time-of-use period types."""
    ON_PEAK = "on_peak"
    MID_PEAK = "mid_peak"
    OFF_PEAK = "off_peak"
    SUPER_OFF_PEAK = "super_off_peak"


class Season(Enum):
    """Rate seasons."""
    SUMMER = "summer"
    WINTER = "winter"


@dataclass
class TouSchedule:
    """
    Time-of-use schedule defining peak periods by hour and month.

    Hours are 0-23 (midnight to 11pm).
    Months are 1-12.
    """
    name: str = ""

    # Summer months (typically June-September for CA)
    summer_months: List[int] = field(default_factory=lambda: [6, 7, 8, 9])

    # Hour ranges for each period (start_hour, end_hour) - end is exclusive
    # Summer schedule
    summer_on_peak: List[Tuple[int, int]] = field(default_factory=list)
    summer_mid_peak: List[Tuple[int, int]] = field(default_factory=list)
    summer_off_peak: List[Tuple[int, int]] = field(default_factory=list)

    # Winter schedule
    winter_on_peak: List[Tuple[int, int]] = field(default_factory=list)
    winter_mid_peak: List[Tuple[int, int]] = field(default_factory=list)
    winter_off_peak: List[Tuple[int, int]] = field(default_factory=list)

    # Weekend/holiday treatment
    weekend_all_off_peak: bool = True

    def get_period(self, month: int, hour: int, is_weekend: bool = False) -> TouPeriod:
        """
        Determine TOU period for a given month, hour, and day type.

        Args:
            month: Month (1-12)
            hour: Hour (0-23)
            is_weekend: True if weekend or holiday

        Returns:
            TouPeriod enum value
        """
        if is_weekend and self.weekend_all_off_peak:
            return TouPeriod.OFF_PEAK

        is_summer = month in self.summer_months

        if is_summer:
            if self._hour_in_ranges(hour, self.summer_on_peak):
                return TouPeriod.ON_PEAK
            elif self._hour_in_ranges(hour, self.summer_mid_peak):
                return TouPeriod.MID_PEAK
            else:
                return TouPeriod.OFF_PEAK
        else:
            if self._hour_in_ranges(hour, self.winter_on_peak):
                return TouPeriod.ON_PEAK
            elif self._hour_in_ranges(hour, self.winter_mid_peak):
                return TouPeriod.MID_PEAK
            else:
                return TouPeriod.OFF_PEAK

    def _hour_in_ranges(self, hour: int, ranges: List[Tuple[int, int]]) -> bool:
        """Check if hour falls within any of the given ranges."""
        for start, end in ranges:
            if start <= hour < end:
                return True
        return False


@dataclass
class TouRates:
    """Energy rates by TOU period ($/kWh)."""
    # Summer rates
    summer_on_peak: float = 0.40
    summer_mid_peak: float = 0.28
    summer_off_peak: float = 0.15

    # Winter rates
    winter_on_peak: float = 0.30
    winter_mid_peak: float = 0.22
    winter_off_peak: float = 0.12

    def get_rate(self, period: TouPeriod, season: Season) -> float:
        """Get rate for period and season."""
        if season == Season.SUMMER:
            if period == TouPeriod.ON_PEAK:
                return self.summer_on_peak
            elif period == TouPeriod.MID_PEAK:
                return self.summer_mid_peak
            else:
                return self.summer_off_peak
        else:
            if period == TouPeriod.ON_PEAK:
                return self.winter_on_peak
            elif period == TouPeriod.MID_PEAK:
                return self.winter_mid_peak
            else:
                return self.winter_off_peak


@dataclass
class DemandRates:
    """Demand charge rates ($/kW)."""
    # Facility demand (all hours)
    facility_charge: float = 0.0

    # Time-related demand charges
    summer_on_peak: float = 20.0
    summer_mid_peak: float = 5.0
    winter_on_peak: float = 0.0
    winter_mid_peak: float = 0.0

    # Non-coincident peak (highest of any hour)
    non_coincident: float = 0.0


@dataclass
class TouTariff:
    """
    Complete TOU tariff with schedule, rates, and charges.
    """
    name: str
    utility: str
    schedule: TouSchedule
    energy_rates: TouRates
    demand_rates: DemandRates

    # Gas rate ($/therm)
    gas_rate: float = 1.80

    # Fixed charges
    monthly_customer_charge: float = 0.0
    monthly_meter_charge: float = 0.0

    # Minimum bill
    minimum_charge: float = 0.0


@dataclass
class HourlyUsage:
    """Hourly energy usage for TOU calculations."""
    month: int
    day: int
    hour: int
    kwh: float
    is_weekend: bool = False


@dataclass
class TouCostBreakdown:
    """Detailed TOU cost breakdown."""
    # Energy costs by period
    summer_on_peak_kwh: float = 0.0
    summer_on_peak_cost: float = 0.0
    summer_mid_peak_kwh: float = 0.0
    summer_mid_peak_cost: float = 0.0
    summer_off_peak_kwh: float = 0.0
    summer_off_peak_cost: float = 0.0

    winter_on_peak_kwh: float = 0.0
    winter_on_peak_cost: float = 0.0
    winter_mid_peak_kwh: float = 0.0
    winter_mid_peak_cost: float = 0.0
    winter_off_peak_kwh: float = 0.0
    winter_off_peak_cost: float = 0.0

    # Demand charges
    facility_demand_kw: float = 0.0
    facility_demand_cost: float = 0.0
    summer_on_peak_demand_kw: float = 0.0
    summer_on_peak_demand_cost: float = 0.0
    summer_mid_peak_demand_kw: float = 0.0
    summer_mid_peak_demand_cost: float = 0.0
    winter_on_peak_demand_kw: float = 0.0
    winter_on_peak_demand_cost: float = 0.0

    # Fixed charges
    customer_charges: float = 0.0
    meter_charges: float = 0.0

    # Totals
    total_energy_cost: float = 0.0
    total_demand_cost: float = 0.0
    total_fixed_cost: float = 0.0
    total_cost: float = 0.0

    @property
    def total_kwh(self) -> float:
        """Total kWh consumed."""
        return (
            self.summer_on_peak_kwh + self.summer_mid_peak_kwh + self.summer_off_peak_kwh +
            self.winter_on_peak_kwh + self.winter_mid_peak_kwh + self.winter_off_peak_kwh
        )


def calculate_tou_costs(
    hourly_data: List[HourlyUsage],
    tariff: TouTariff
) -> TouCostBreakdown:
    """
    Calculate annual energy costs from hourly data using TOU rates.

    Args:
        hourly_data: List of hourly usage records (8760 for full year)
        tariff: TOU tariff with schedule and rates

    Returns:
        TouCostBreakdown with detailed cost breakdown
    """
    breakdown = TouCostBreakdown()
    schedule = tariff.schedule
    rates = tariff.energy_rates

    # Track monthly peaks for demand charges
    monthly_peaks: Dict[int, Dict[str, float]] = {
        m: {
            'facility': 0.0,
            'summer_on_peak': 0.0,
            'summer_mid_peak': 0.0,
            'winter_on_peak': 0.0,
            'winter_mid_peak': 0.0
        }
        for m in range(1, 13)
    }

    # Process each hour
    for hour_data in hourly_data:
        month = hour_data.month
        hour = hour_data.hour
        kwh = hour_data.kwh
        is_weekend = hour_data.is_weekend

        # Determine period and season
        period = schedule.get_period(month, hour, is_weekend)
        is_summer = month in schedule.summer_months
        season = Season.SUMMER if is_summer else Season.WINTER

        # Get rate and accumulate
        rate = rates.get_rate(period, season)
        cost = kwh * rate

        # Accumulate by period
        if is_summer:
            if period == TouPeriod.ON_PEAK:
                breakdown.summer_on_peak_kwh += kwh
                breakdown.summer_on_peak_cost += cost
            elif period == TouPeriod.MID_PEAK:
                breakdown.summer_mid_peak_kwh += kwh
                breakdown.summer_mid_peak_cost += cost
            else:
                breakdown.summer_off_peak_kwh += kwh
                breakdown.summer_off_peak_cost += cost
        else:
            if period == TouPeriod.ON_PEAK:
                breakdown.winter_on_peak_kwh += kwh
                breakdown.winter_on_peak_cost += cost
            elif period == TouPeriod.MID_PEAK:
                breakdown.winter_mid_peak_kwh += kwh
                breakdown.winter_mid_peak_cost += cost
            else:
                breakdown.winter_off_peak_kwh += kwh
                breakdown.winter_off_peak_cost += cost

        # Track peaks for demand charges
        monthly_peaks[month]['facility'] = max(monthly_peaks[month]['facility'], kwh)

        if is_summer:
            if period == TouPeriod.ON_PEAK:
                monthly_peaks[month]['summer_on_peak'] = max(
                    monthly_peaks[month]['summer_on_peak'], kwh
                )
            elif period == TouPeriod.MID_PEAK:
                monthly_peaks[month]['summer_mid_peak'] = max(
                    monthly_peaks[month]['summer_mid_peak'], kwh
                )
        else:
            if period == TouPeriod.ON_PEAK:
                monthly_peaks[month]['winter_on_peak'] = max(
                    monthly_peaks[month]['winter_on_peak'], kwh
                )
            elif period == TouPeriod.MID_PEAK:
                monthly_peaks[month]['winter_mid_peak'] = max(
                    monthly_peaks[month]['winter_mid_peak'], kwh
                )

    # Calculate demand charges
    demand = tariff.demand_rates

    for month, peaks in monthly_peaks.items():
        # Facility demand (all months)
        if demand.facility_charge > 0:
            breakdown.facility_demand_kw = max(breakdown.facility_demand_kw, peaks['facility'])
            breakdown.facility_demand_cost += peaks['facility'] * demand.facility_charge

        is_summer = month in schedule.summer_months
        if is_summer:
            # Summer demand charges
            if peaks['summer_on_peak'] > 0 and demand.summer_on_peak > 0:
                breakdown.summer_on_peak_demand_kw = max(
                    breakdown.summer_on_peak_demand_kw, peaks['summer_on_peak']
                )
                breakdown.summer_on_peak_demand_cost += peaks['summer_on_peak'] * demand.summer_on_peak

            if peaks['summer_mid_peak'] > 0 and demand.summer_mid_peak > 0:
                breakdown.summer_mid_peak_demand_kw = max(
                    breakdown.summer_mid_peak_demand_kw, peaks['summer_mid_peak']
                )
                breakdown.summer_mid_peak_demand_cost += peaks['summer_mid_peak'] * demand.summer_mid_peak
        else:
            # Winter demand charges
            if peaks['winter_on_peak'] > 0 and demand.winter_on_peak > 0:
                breakdown.winter_on_peak_demand_kw = max(
                    breakdown.winter_on_peak_demand_kw, peaks['winter_on_peak']
                )
                breakdown.winter_on_peak_demand_cost += peaks['winter_on_peak'] * demand.winter_on_peak

    # Fixed charges (12 months)
    breakdown.customer_charges = tariff.monthly_customer_charge * 12
    breakdown.meter_charges = tariff.monthly_meter_charge * 12

    # Calculate totals
    breakdown.total_energy_cost = (
        breakdown.summer_on_peak_cost + breakdown.summer_mid_peak_cost + breakdown.summer_off_peak_cost +
        breakdown.winter_on_peak_cost + breakdown.winter_mid_peak_cost + breakdown.winter_off_peak_cost
    )

    breakdown.total_demand_cost = (
        breakdown.facility_demand_cost +
        breakdown.summer_on_peak_demand_cost + breakdown.summer_mid_peak_demand_cost +
        breakdown.winter_on_peak_demand_cost
    )

    breakdown.total_fixed_cost = breakdown.customer_charges + breakdown.meter_charges

    breakdown.total_cost = (
        breakdown.total_energy_cost + breakdown.total_demand_cost + breakdown.total_fixed_cost
    )

    return breakdown


def calculate_demand_charges(
    monthly_peaks: Dict[int, float],
    tariff: TouTariff
) -> Tuple[float, Dict[str, float]]:
    """
    Calculate annual demand charges from monthly peak data.

    Args:
        monthly_peaks: Dictionary of {month: peak_kw}
        tariff: TOU tariff with demand rates

    Returns:
        Tuple of (total_demand_cost, breakdown_dict)
    """
    demand = tariff.demand_rates
    schedule = tariff.schedule

    breakdown = {
        'facility': 0.0,
        'summer_on_peak': 0.0,
        'winter_on_peak': 0.0
    }

    for month, peak_kw in monthly_peaks.items():
        # Facility demand (all months)
        breakdown['facility'] += peak_kw * demand.facility_charge

        # TOU demand
        is_summer = month in schedule.summer_months
        if is_summer:
            breakdown['summer_on_peak'] += peak_kw * demand.summer_on_peak
        else:
            breakdown['winter_on_peak'] += peak_kw * demand.winter_on_peak

    total = sum(breakdown.values())
    return total, breakdown


def hourly_energy_to_usage(
    hourly_data: list,
    year: int = 2024
) -> List[HourlyUsage]:
    """
    Convert HourlyEnergy objects to HourlyUsage for TOU calculations.

    Args:
        hourly_data: List of HourlyEnergy objects from parser
        year: Year for weekend determination

    Returns:
        List of HourlyUsage objects
    """
    from datetime import date

    usage_list = []

    for h in hourly_data:
        # Determine if weekend
        try:
            d = date(year, h.month, h.day)
            is_weekend = d.weekday() >= 5  # Saturday = 5, Sunday = 6
        except ValueError:
            is_weekend = False

        usage_list.append(HourlyUsage(
            month=h.month,
            day=h.day,
            hour=h.hour,
            kwh=h.elec_total_kwh,
            is_weekend=is_weekend
        ))

    return usage_list


# ---- Common Utility Tariff Templates ----

def create_sce_tou_gs3() -> TouTariff:
    """
    Create SCE TOU-GS-3 tariff template.

    Southern California Edison General Service - Large
    Typical for commercial buildings > 200 kW demand.
    """
    schedule = TouSchedule(
        name="SCE TOU-GS-3",
        summer_months=[6, 7, 8, 9],
        # Summer: On-peak 4pm-9pm, Mid-peak 2pm-4pm & 9pm-10pm
        summer_on_peak=[(16, 21)],
        summer_mid_peak=[(14, 16), (21, 22)],
        summer_off_peak=[],  # All other hours
        # Winter: Mid-peak 4pm-9pm
        winter_on_peak=[],
        winter_mid_peak=[(16, 21)],
        winter_off_peak=[],
        weekend_all_off_peak=True
    )

    energy_rates = TouRates(
        summer_on_peak=0.38,
        summer_mid_peak=0.26,
        summer_off_peak=0.14,
        winter_on_peak=0.28,
        winter_mid_peak=0.24,
        winter_off_peak=0.12
    )

    demand_rates = DemandRates(
        facility_charge=19.50,
        summer_on_peak=22.00,
        summer_mid_peak=6.50,
        winter_on_peak=0.0,
        winter_mid_peak=0.0
    )

    return TouTariff(
        name="TOU-GS-3",
        utility="Southern California Edison",
        schedule=schedule,
        energy_rates=energy_rates,
        demand_rates=demand_rates,
        gas_rate=1.85,
        monthly_customer_charge=450.0
    )


def create_pge_b20() -> TouTariff:
    """
    Create PG&E B-20 tariff template.

    Pacific Gas & Electric - Medium General Demand-Metered TOU
    Typical for commercial buildings 75-500 kW demand.
    """
    schedule = TouSchedule(
        name="PG&E B-20",
        summer_months=[5, 6, 7, 8, 9, 10],  # May-October
        # Summer: On-peak 4pm-9pm
        summer_on_peak=[(16, 21)],
        summer_mid_peak=[],
        summer_off_peak=[],
        # Winter: Mid-peak 4pm-9pm
        winter_on_peak=[],
        winter_mid_peak=[(16, 21)],
        winter_off_peak=[],
        weekend_all_off_peak=True
    )

    energy_rates = TouRates(
        summer_on_peak=0.42,
        summer_mid_peak=0.28,
        summer_off_peak=0.16,
        winter_on_peak=0.30,
        winter_mid_peak=0.26,
        winter_off_peak=0.14
    )

    demand_rates = DemandRates(
        facility_charge=0.0,
        summer_on_peak=25.00,
        summer_mid_peak=0.0,
        winter_on_peak=0.0,
        winter_mid_peak=0.0,
        non_coincident=12.00
    )

    return TouTariff(
        name="B-20",
        utility="Pacific Gas & Electric",
        schedule=schedule,
        energy_rates=energy_rates,
        demand_rates=demand_rates,
        gas_rate=1.75,
        monthly_customer_charge=350.0
    )


def create_sdge_al_tou() -> TouTariff:
    """
    Create SDG&E AL-TOU tariff template.

    San Diego Gas & Electric - General Service - Large TOU
    Typical for commercial buildings > 500 kW demand.
    """
    schedule = TouSchedule(
        name="SDG&E AL-TOU",
        summer_months=[6, 7, 8, 9, 10],  # June-October
        # Summer: On-peak 4pm-9pm
        summer_on_peak=[(16, 21)],
        summer_mid_peak=[],
        summer_off_peak=[],
        # Winter: On-peak 4pm-9pm
        winter_on_peak=[(16, 21)],
        winter_mid_peak=[],
        winter_off_peak=[],
        weekend_all_off_peak=True
    )

    energy_rates = TouRates(
        summer_on_peak=0.45,
        summer_mid_peak=0.30,
        summer_off_peak=0.18,
        winter_on_peak=0.35,
        winter_mid_peak=0.28,
        winter_off_peak=0.15
    )

    demand_rates = DemandRates(
        facility_charge=18.00,
        summer_on_peak=28.00,
        summer_mid_peak=0.0,
        winter_on_peak=15.00,
        winter_mid_peak=0.0
    )

    return TouTariff(
        name="AL-TOU",
        utility="San Diego Gas & Electric",
        schedule=schedule,
        energy_rates=energy_rates,
        demand_rates=demand_rates,
        gas_rate=2.00,
        monthly_customer_charge=500.0
    )


def get_tariff_by_name(name: str) -> Optional[TouTariff]:
    """
    Get a predefined tariff by name.

    Args:
        name: Tariff identifier (e.g., "SCE TOU-GS-3", "PG&E B-20")

    Returns:
        TouTariff or None if not found
    """
    tariffs = {
        "SCE TOU-GS-3": create_sce_tou_gs3,
        "TOU-GS-3": create_sce_tou_gs3,
        "PG&E B-20": create_pge_b20,
        "B-20": create_pge_b20,
        "SDG&E AL-TOU": create_sdge_al_tou,
        "AL-TOU": create_sdge_al_tou,
    }

    factory = tariffs.get(name)
    if factory:
        return factory()
    return None


def list_available_tariffs() -> List[str]:
    """Return list of available predefined tariffs."""
    return [
        "SCE TOU-GS-3 (Southern California Edison)",
        "PG&E B-20 (Pacific Gas & Electric)",
        "SDG&E AL-TOU (San Diego Gas & Electric)",
    ]


def format_tou_breakdown(breakdown: TouCostBreakdown, tariff_name: str = "") -> str:
    """
    Format TOU cost breakdown as text report.

    Args:
        breakdown: TouCostBreakdown from calculate_tou_costs
        tariff_name: Optional tariff name for header

    Returns:
        Formatted text report
    """
    lines = [
        "=" * 60,
        "TIME-OF-USE ENERGY COST BREAKDOWN",
        f"Tariff: {tariff_name}" if tariff_name else "",
        "=" * 60,
        "",
        "Summer Energy Charges",
        "-" * 40,
        f"  On-Peak:   {breakdown.summer_on_peak_kwh:>12,.0f} kWh  ${breakdown.summer_on_peak_cost:>12,.2f}",
        f"  Mid-Peak:  {breakdown.summer_mid_peak_kwh:>12,.0f} kWh  ${breakdown.summer_mid_peak_cost:>12,.2f}",
        f"  Off-Peak:  {breakdown.summer_off_peak_kwh:>12,.0f} kWh  ${breakdown.summer_off_peak_cost:>12,.2f}",
        "",
        "Winter Energy Charges",
        "-" * 40,
        f"  On-Peak:   {breakdown.winter_on_peak_kwh:>12,.0f} kWh  ${breakdown.winter_on_peak_cost:>12,.2f}",
        f"  Mid-Peak:  {breakdown.winter_mid_peak_kwh:>12,.0f} kWh  ${breakdown.winter_mid_peak_cost:>12,.2f}",
        f"  Off-Peak:  {breakdown.winter_off_peak_kwh:>12,.0f} kWh  ${breakdown.winter_off_peak_cost:>12,.2f}",
        "",
        "Demand Charges",
        "-" * 40,
    ]

    if breakdown.facility_demand_cost > 0:
        lines.append(f"  Facility:  {breakdown.facility_demand_kw:>12,.1f} kW   ${breakdown.facility_demand_cost:>12,.2f}")
    if breakdown.summer_on_peak_demand_cost > 0:
        lines.append(f"  Summer On-Peak: {breakdown.summer_on_peak_demand_kw:>7,.1f} kW   ${breakdown.summer_on_peak_demand_cost:>12,.2f}")
    if breakdown.summer_mid_peak_demand_cost > 0:
        lines.append(f"  Summer Mid-Peak: {breakdown.summer_mid_peak_demand_kw:>6,.1f} kW   ${breakdown.summer_mid_peak_demand_cost:>12,.2f}")
    if breakdown.winter_on_peak_demand_cost > 0:
        lines.append(f"  Winter On-Peak: {breakdown.winter_on_peak_demand_kw:>7,.1f} kW   ${breakdown.winter_on_peak_demand_cost:>12,.2f}")

    lines.extend([
        "",
        "Fixed Charges",
        "-" * 40,
        f"  Customer Charges:               ${breakdown.customer_charges:>12,.2f}",
        f"  Meter Charges:                  ${breakdown.meter_charges:>12,.2f}",
        "",
        "Summary",
        "-" * 40,
        f"  Total Energy:   {breakdown.total_kwh:>12,.0f} kWh  ${breakdown.total_energy_cost:>12,.2f}",
        f"  Total Demand:                        ${breakdown.total_demand_cost:>12,.2f}",
        f"  Total Fixed:                         ${breakdown.total_fixed_cost:>12,.2f}",
        f"  ----------------------------------------",
        f"  ANNUAL TOTAL:                        ${breakdown.total_cost:>12,.2f}",
        "",
        "=" * 60,
    ])

    return "\n".join(lines)
