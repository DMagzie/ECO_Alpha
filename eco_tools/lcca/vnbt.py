"""
Virtual Net Billing Tariff (V-NBT) Models for California.

V-NBT replaced VNEM (Virtual Net Energy Metering) on February 14, 2024.
Key differences from NEM 2.0:
- Export compensation at Avoided Cost Calculator (ACC) rates, not retail
- Instantaneous netting (no monthly true-up banking)
- Non-Bypassable Charges (NBCs) on all grid consumption
- Different export values by time of day and season

This module extends the existing TOU tariff structure to support:
- Export credit rates (ACC values)
- Hourly import/export tracking
- NBC calculations
- Virtual meter allocation for multifamily

Usage:
    from eco_tools.lcca.vnbt import (
        VnbtTariff,
        create_pge_e_elec_vnbt,
        calculate_vnbt_costs,
    )

    tariff = create_pge_e_elec_vnbt()
    costs = calculate_vnbt_costs(hourly_data, tariff)
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from enum import Enum

from .tariffs import (
    TouPeriod,
    Season,
    TouSchedule,
    TouRates,
    DemandRates,
    TouTariff,
    HourlyUsage,
)


class NettingMode(Enum):
    """Net metering netting period."""
    INSTANTANEOUS = "instantaneous"  # V-NBT: hourly netting
    MONTHLY = "monthly"              # NEM 2.0: monthly true-up
    ANNUAL = "annual"                # NEM 1.0: annual true-up


@dataclass
class ExportRates:
    """
    Export compensation rates ($/kWh) by TOU period.

    Under V-NBT, export rates are based on the CPUC Avoided Cost
    Calculator (ACC) values, which are significantly lower than
    retail rates, especially during mid-day solar hours.

    Typical ACC values (2024):
    - Summer on-peak (4-9pm):  $0.08-0.12/kWh
    - Summer off-peak:         $0.03-0.05/kWh
    - Winter on-peak:          $0.06-0.09/kWh
    - Winter off-peak:         $0.02-0.04/kWh
    """
    # Summer export rates
    summer_on_peak: float = 0.10
    summer_mid_peak: float = 0.06
    summer_off_peak: float = 0.04

    # Winter export rates
    winter_on_peak: float = 0.08
    winter_mid_peak: float = 0.05
    winter_off_peak: float = 0.03

    # Super off-peak (if applicable)
    summer_super_off_peak: float = 0.02
    winter_super_off_peak: float = 0.02

    def get_rate(self, period: TouPeriod, season: Season) -> float:
        """Get export rate for period and season."""
        if season == Season.SUMMER:
            if period == TouPeriod.ON_PEAK:
                return self.summer_on_peak
            elif period == TouPeriod.MID_PEAK:
                return self.summer_mid_peak
            elif period == TouPeriod.SUPER_OFF_PEAK:
                return self.summer_super_off_peak
            else:
                return self.summer_off_peak
        else:
            if period == TouPeriod.ON_PEAK:
                return self.winter_on_peak
            elif period == TouPeriod.MID_PEAK:
                return self.winter_mid_peak
            elif period == TouPeriod.SUPER_OFF_PEAK:
                return self.winter_super_off_peak
            else:
                return self.winter_off_peak


@dataclass
class NonBypassableCharges:
    """
    Non-Bypassable Charges (NBCs) that apply to all grid consumption.

    Under V-NBT, these charges apply even when exports offset imports
    within a billing period. They cover:
    - Public Purpose Programs (PPP)
    - Nuclear Decommissioning
    - Competition Transition Charge (CTC)
    - Wildfire Fund Charge

    Total NBC is typically $0.02-0.04/kWh.
    """
    public_purpose_programs: float = 0.01167  # PPP
    nuclear_decommissioning: float = 0.00063  # ND
    competition_transition: float = 0.00000   # CTC (varies)
    wildfire_fund: float = 0.00580           # DWR-WFC

    @property
    def total(self) -> float:
        """Total NBC rate per kWh."""
        return (
            self.public_purpose_programs +
            self.nuclear_decommissioning +
            self.competition_transition +
            self.wildfire_fund
        )


@dataclass
class VnbtTariff:
    """
    Complete V-NBT tariff with import rates, export credits, and NBCs.

    Extends TouTariff with V-NBT specific features:
    - Export compensation rates (ACC-based)
    - Non-Bypassable Charges
    - Netting mode (instantaneous for V-NBT)
    - Virtual meter support for multifamily
    """
    name: str
    utility: str
    schedule: TouSchedule

    # Import (consumption) rates
    import_rates: TouRates

    # Export (generation credit) rates
    export_rates: ExportRates

    # Non-bypassable charges
    nbc: NonBypassableCharges

    # Demand charges (typically waived for residential V-NBT)
    demand_rates: DemandRates = field(default_factory=DemandRates)

    # Gas rate ($/therm) for dual-fuel buildings
    gas_rate: float = 1.80

    # Fixed charges
    monthly_customer_charge: float = 0.0
    monthly_meter_charge: float = 0.0
    minimum_daily_charge: float = 0.40317  # From er.json

    # Netting configuration
    netting_mode: NettingMode = NettingMode.INSTANTANEOUS

    # For virtual metering (multifamily)
    virtual_metering: bool = False
    common_area_allocation_pct: float = 0.0  # % of generation to common area

    @property
    def total_nbc_rate(self) -> float:
        """Total non-bypassable charge rate."""
        return self.nbc.total


@dataclass
class HourlyNetUsage:
    """
    Hourly energy data with import/export separation.

    For V-NBT calculations, we need to track:
    - Gross load (consumption before PV)
    - PV generation
    - Net usage (positive = import, negative = export)
    - Self-consumption (PV used on-site)
    """
    month: int
    day: int
    hour: int

    # Gross consumption (kWh)
    gross_load_kwh: float

    # Generation (kWh)
    pv_generation_kwh: float = 0.0
    battery_discharge_kwh: float = 0.0
    battery_charge_kwh: float = 0.0

    # Day type
    is_weekend: bool = False

    @property
    def net_kwh(self) -> float:
        """Net electricity (positive = import, negative = export)."""
        return (
            self.gross_load_kwh -
            self.pv_generation_kwh +
            self.battery_charge_kwh -
            self.battery_discharge_kwh
        )

    @property
    def import_kwh(self) -> float:
        """Grid import (always >= 0)."""
        return max(0.0, self.net_kwh)

    @property
    def export_kwh(self) -> float:
        """Grid export (always >= 0)."""
        return max(0.0, -self.net_kwh)

    @property
    def self_consumption_kwh(self) -> float:
        """PV used directly on-site (not exported)."""
        return min(self.pv_generation_kwh, self.gross_load_kwh)


@dataclass
class VnbtCostBreakdown:
    """
    Detailed V-NBT cost breakdown with import, export, and NBC tracking.
    """
    # Import costs by TOU period
    summer_on_peak_import_kwh: float = 0.0
    summer_on_peak_import_cost: float = 0.0
    summer_mid_peak_import_kwh: float = 0.0
    summer_mid_peak_import_cost: float = 0.0
    summer_off_peak_import_kwh: float = 0.0
    summer_off_peak_import_cost: float = 0.0

    winter_on_peak_import_kwh: float = 0.0
    winter_on_peak_import_cost: float = 0.0
    winter_mid_peak_import_kwh: float = 0.0
    winter_mid_peak_import_cost: float = 0.0
    winter_off_peak_import_kwh: float = 0.0
    winter_off_peak_import_cost: float = 0.0

    # Export credits by TOU period
    summer_on_peak_export_kwh: float = 0.0
    summer_on_peak_export_credit: float = 0.0
    summer_mid_peak_export_kwh: float = 0.0
    summer_mid_peak_export_credit: float = 0.0
    summer_off_peak_export_kwh: float = 0.0
    summer_off_peak_export_credit: float = 0.0

    winter_on_peak_export_kwh: float = 0.0
    winter_on_peak_export_credit: float = 0.0
    winter_mid_peak_export_kwh: float = 0.0
    winter_mid_peak_export_credit: float = 0.0
    winter_off_peak_export_kwh: float = 0.0
    winter_off_peak_export_credit: float = 0.0

    # Non-Bypassable Charges (on all grid imports)
    nbc_kwh: float = 0.0  # = total imports
    nbc_cost: float = 0.0

    # Fixed charges
    customer_charges: float = 0.0
    meter_charges: float = 0.0
    minimum_bill_charges: float = 0.0

    # Self-consumption (value of avoided import)
    self_consumption_kwh: float = 0.0
    self_consumption_value: float = 0.0  # At import rates

    # Totals
    total_import_cost: float = 0.0
    total_export_credit: float = 0.0
    total_nbc_cost: float = 0.0
    total_fixed_cost: float = 0.0
    net_electricity_cost: float = 0.0  # Import - Export + NBC + Fixed

    # Generation and load totals
    total_pv_kwh: float = 0.0
    total_load_kwh: float = 0.0
    total_import_kwh: float = 0.0
    total_export_kwh: float = 0.0

    @property
    def effective_rate_import(self) -> float:
        """Effective $/kWh for imports."""
        if self.total_import_kwh > 0:
            return self.total_import_cost / self.total_import_kwh
        return 0.0

    @property
    def effective_rate_export(self) -> float:
        """Effective $/kWh credit for exports."""
        if self.total_export_kwh > 0:
            return self.total_export_credit / self.total_export_kwh
        return 0.0

    @property
    def export_value_ratio(self) -> float:
        """Export credit as % of import cost (NEM 2.0 ~100%, V-NBT ~25%)."""
        if self.effective_rate_import > 0:
            return self.effective_rate_export / self.effective_rate_import
        return 0.0


def calculate_vnbt_costs(
    hourly_data: List[HourlyNetUsage],
    tariff: VnbtTariff
) -> VnbtCostBreakdown:
    """
    Calculate annual energy costs under V-NBT tariff.

    Args:
        hourly_data: List of hourly usage with gross load and PV generation
        tariff: V-NBT tariff with import rates, export rates, and NBCs

    Returns:
        VnbtCostBreakdown with detailed cost/credit breakdown
    """
    breakdown = VnbtCostBreakdown()
    schedule = tariff.schedule
    import_rates = tariff.import_rates
    export_rates = tariff.export_rates

    for h in hourly_data:
        # Determine TOU period
        is_summer = h.month in schedule.summer_months
        season = Season.SUMMER if is_summer else Season.WINTER
        period = schedule.get_period(h.month, h.hour, h.is_weekend)

        # Get rates for this period
        import_rate = import_rates.get_rate(period, season)
        export_rate = export_rates.get_rate(period, season)

        # Calculate import cost
        import_kwh = h.import_kwh
        import_cost = import_kwh * import_rate

        # Calculate export credit
        export_kwh = h.export_kwh
        export_credit = export_kwh * export_rate

        # Accumulate by period
        if is_summer:
            if period == TouPeriod.ON_PEAK:
                breakdown.summer_on_peak_import_kwh += import_kwh
                breakdown.summer_on_peak_import_cost += import_cost
                breakdown.summer_on_peak_export_kwh += export_kwh
                breakdown.summer_on_peak_export_credit += export_credit
            elif period == TouPeriod.MID_PEAK:
                breakdown.summer_mid_peak_import_kwh += import_kwh
                breakdown.summer_mid_peak_import_cost += import_cost
                breakdown.summer_mid_peak_export_kwh += export_kwh
                breakdown.summer_mid_peak_export_credit += export_credit
            else:  # OFF_PEAK or SUPER_OFF_PEAK
                breakdown.summer_off_peak_import_kwh += import_kwh
                breakdown.summer_off_peak_import_cost += import_cost
                breakdown.summer_off_peak_export_kwh += export_kwh
                breakdown.summer_off_peak_export_credit += export_credit
        else:
            if period == TouPeriod.ON_PEAK:
                breakdown.winter_on_peak_import_kwh += import_kwh
                breakdown.winter_on_peak_import_cost += import_cost
                breakdown.winter_on_peak_export_kwh += export_kwh
                breakdown.winter_on_peak_export_credit += export_credit
            elif period == TouPeriod.MID_PEAK:
                breakdown.winter_mid_peak_import_kwh += import_kwh
                breakdown.winter_mid_peak_import_cost += import_cost
                breakdown.winter_mid_peak_export_kwh += export_kwh
                breakdown.winter_mid_peak_export_credit += export_credit
            else:  # OFF_PEAK
                breakdown.winter_off_peak_import_kwh += import_kwh
                breakdown.winter_off_peak_import_cost += import_cost
                breakdown.winter_off_peak_export_kwh += export_kwh
                breakdown.winter_off_peak_export_credit += export_credit

        # Track self-consumption
        breakdown.self_consumption_kwh += h.self_consumption_kwh
        breakdown.self_consumption_value += h.self_consumption_kwh * import_rate

        # Track totals
        breakdown.total_pv_kwh += h.pv_generation_kwh
        breakdown.total_load_kwh += h.gross_load_kwh

    # Calculate totals
    breakdown.total_import_kwh = (
        breakdown.summer_on_peak_import_kwh +
        breakdown.summer_mid_peak_import_kwh +
        breakdown.summer_off_peak_import_kwh +
        breakdown.winter_on_peak_import_kwh +
        breakdown.winter_mid_peak_import_kwh +
        breakdown.winter_off_peak_import_kwh
    )

    breakdown.total_export_kwh = (
        breakdown.summer_on_peak_export_kwh +
        breakdown.summer_mid_peak_export_kwh +
        breakdown.summer_off_peak_export_kwh +
        breakdown.winter_on_peak_export_kwh +
        breakdown.winter_mid_peak_export_kwh +
        breakdown.winter_off_peak_export_kwh
    )

    breakdown.total_import_cost = (
        breakdown.summer_on_peak_import_cost +
        breakdown.summer_mid_peak_import_cost +
        breakdown.summer_off_peak_import_cost +
        breakdown.winter_on_peak_import_cost +
        breakdown.winter_mid_peak_import_cost +
        breakdown.winter_off_peak_import_cost
    )

    breakdown.total_export_credit = (
        breakdown.summer_on_peak_export_credit +
        breakdown.summer_mid_peak_export_credit +
        breakdown.summer_off_peak_export_credit +
        breakdown.winter_on_peak_export_credit +
        breakdown.winter_mid_peak_export_credit +
        breakdown.winter_off_peak_export_credit
    )

    # Non-Bypassable Charges on all imports
    breakdown.nbc_kwh = breakdown.total_import_kwh
    breakdown.nbc_cost = breakdown.nbc_kwh * tariff.total_nbc_rate
    breakdown.total_nbc_cost = breakdown.nbc_cost

    # Fixed charges (365 days * daily minimum)
    breakdown.customer_charges = tariff.monthly_customer_charge * 12
    breakdown.meter_charges = tariff.monthly_meter_charge * 12
    breakdown.minimum_bill_charges = tariff.minimum_daily_charge * 365
    breakdown.total_fixed_cost = (
        breakdown.customer_charges +
        breakdown.meter_charges +
        breakdown.minimum_bill_charges
    )

    # Net electricity cost
    breakdown.net_electricity_cost = (
        breakdown.total_import_cost -
        breakdown.total_export_credit +
        breakdown.total_nbc_cost +
        breakdown.total_fixed_cost
    )

    return breakdown


# ---- Factory Functions for Common California V-NBT Tariffs ----

def create_pge_e_elec_vnbt(
    acc_year: int = 2024,
    rate_code: str = "E-ELEC"
) -> VnbtTariff:
    """
    Create PG&E E-ELEC residential electrification rate with V-NBT export credits.

    E-ELEC is PG&E's TOU rate designed for all-electric homes with:
    - Lower off-peak rates to incentivize electrification
    - 4-9pm on-peak (when grid is stressed)
    - V-NBT export credits based on ACC values

    Args:
        acc_year: ACC vintage year (affects export credit values)
        rate_code: Rate code variant

    Returns:
        VnbtTariff configured for PG&E E-ELEC with V-NBT
    """
    schedule = TouSchedule(
        name="PG&E E-ELEC",
        summer_months=[6, 7, 8, 9],  # June-September
        # Summer: 4pm-9pm on-peak
        summer_on_peak=[(16, 21)],
        summer_off_peak=[(0, 16), (21, 24)],
        # Winter: 4pm-9pm on-peak
        winter_on_peak=[(16, 21)],
        winter_off_peak=[(0, 16), (21, 24)],
        weekend_all_off_peak=True,
    )

    # Import rates (2024 E-ELEC effective rates)
    import_rates = TouRates(
        summer_on_peak=0.54,     # Peak: $0.54/kWh
        summer_mid_peak=0.42,   # Not used in E-ELEC
        summer_off_peak=0.36,   # Off-peak: $0.36/kWh
        winter_on_peak=0.43,    # Peak: $0.43/kWh
        winter_mid_peak=0.35,   # Not used in E-ELEC
        winter_off_peak=0.35,   # Off-peak: $0.35/kWh
    )

    # ACC-based export rates (2024 ACC values, simplified)
    export_rates = ExportRates(
        summer_on_peak=0.08,     # Evening peak has modest value
        summer_mid_peak=0.05,
        summer_off_peak=0.03,    # Midday solar glut = low value
        winter_on_peak=0.07,
        winter_mid_peak=0.04,
        winter_off_peak=0.03,
    )

    # PG&E NBCs (2024)
    nbc = NonBypassableCharges(
        public_purpose_programs=0.01167,
        nuclear_decommissioning=0.00063,
        competition_transition=0.0,
        wildfire_fund=0.00580,
    )

    return VnbtTariff(
        name=f"PG&E {rate_code} V-NBT",
        utility="Pacific Gas & Electric",
        schedule=schedule,
        import_rates=import_rates,
        export_rates=export_rates,
        nbc=nbc,
        gas_rate=0.0,  # Electric-only rate
        minimum_daily_charge=0.40,
        netting_mode=NettingMode.INSTANTANEOUS,
    )


def create_sce_tou_d_prime_vnbt() -> VnbtTariff:
    """
    Create SCE TOU-D-PRIME residential TOU rate with V-NBT export credits.

    TOU-D-PRIME is SCE's electrification rate with:
    - Lower baseline credits
    - 4-9pm on-peak year-round
    - Designed for EVs and heat pumps

    Returns:
        VnbtTariff configured for SCE TOU-D-PRIME with V-NBT
    """
    schedule = TouSchedule(
        name="SCE TOU-D-PRIME",
        summer_months=[6, 7, 8, 9],
        summer_on_peak=[(16, 21)],
        summer_off_peak=[(0, 16), (21, 24)],
        winter_on_peak=[(16, 21)],
        winter_off_peak=[(0, 16), (21, 24)],
        weekend_all_off_peak=False,  # SCE has weekend on-peak
    )

    import_rates = TouRates(
        summer_on_peak=0.61,
        summer_mid_peak=0.45,
        summer_off_peak=0.32,
        winter_on_peak=0.48,
        winter_mid_peak=0.40,
        winter_off_peak=0.32,
    )

    export_rates = ExportRates(
        summer_on_peak=0.09,
        summer_mid_peak=0.05,
        summer_off_peak=0.03,
        winter_on_peak=0.07,
        winter_mid_peak=0.04,
        winter_off_peak=0.03,
    )

    nbc = NonBypassableCharges(
        public_purpose_programs=0.00900,
        nuclear_decommissioning=0.00050,
        competition_transition=0.00100,
        wildfire_fund=0.00500,
    )

    return VnbtTariff(
        name="SCE TOU-D-PRIME V-NBT",
        utility="Southern California Edison",
        schedule=schedule,
        import_rates=import_rates,
        export_rates=export_rates,
        nbc=nbc,
        gas_rate=0.0,
        minimum_daily_charge=0.39,
        netting_mode=NettingMode.INSTANTANEOUS,
    )


def create_sdge_tou_dr_vnbt() -> VnbtTariff:
    """
    Create SDG&E TOU-DR residential TOU rate with V-NBT export credits.

    TOU-DR is SDG&E's default TOU rate with:
    - Higher on-peak rates than other IOUs
    - 4-9pm on-peak year-round
    - Super off-peak 12am-6am March-April

    Returns:
        VnbtTariff configured for SDG&E TOU-DR with V-NBT
    """
    schedule = TouSchedule(
        name="SDG&E TOU-DR",
        summer_months=[6, 7, 8, 9, 10],  # SDG&E: June-October
        summer_on_peak=[(16, 21)],
        summer_off_peak=[(0, 16), (21, 24)],
        winter_on_peak=[(16, 21)],
        winter_off_peak=[(0, 16), (21, 24)],
        weekend_all_off_peak=True,
    )

    import_rates = TouRates(
        summer_on_peak=0.68,    # SDG&E has highest rates
        summer_mid_peak=0.50,
        summer_off_peak=0.38,
        winter_on_peak=0.52,
        winter_mid_peak=0.42,
        winter_off_peak=0.38,
    )

    export_rates = ExportRates(
        summer_on_peak=0.10,
        summer_mid_peak=0.06,
        summer_off_peak=0.04,
        winter_on_peak=0.08,
        winter_mid_peak=0.05,
        winter_off_peak=0.04,
    )

    nbc = NonBypassableCharges(
        public_purpose_programs=0.01100,
        nuclear_decommissioning=0.00040,
        competition_transition=0.00000,
        wildfire_fund=0.00600,
    )

    return VnbtTariff(
        name="SDG&E TOU-DR V-NBT",
        utility="San Diego Gas & Electric",
        schedule=schedule,
        import_rates=import_rates,
        export_rates=export_rates,
        nbc=nbc,
        gas_rate=2.20,  # SDG&E gas is expensive
        minimum_daily_charge=0.42,
        netting_mode=NettingMode.INSTANTANEOUS,
    )


# ---- Virtual Meter Allocation for Multifamily ----

@dataclass
class VirtualMeterAllocation:
    """
    Virtual meter allocation for multifamily V-NBT.

    In VNEM/V-NBT, a central PV system allocates generation to
    individual tenant meters based on allocation percentages.
    Allocations must sum to 100%.
    """
    unit_name: str
    num_bedrooms: int
    allocation_pct: float  # 0-100
    meter_id: Optional[str] = None

    @property
    def allocation_fraction(self) -> float:
        """Allocation as decimal (0-1)."""
        return self.allocation_pct / 100.0


def calculate_vnbt_multifamily(
    common_area_hourly: List[HourlyNetUsage],
    unit_hourly_data: Dict[str, List[HourlyNetUsage]],
    pv_hourly_generation: List[float],
    allocations: List[VirtualMeterAllocation],
    tariff: VnbtTariff,
) -> Dict[str, VnbtCostBreakdown]:
    """
    Calculate V-NBT costs for multifamily building with virtual metering.

    PV generation is allocated to individual unit meters based on
    allocation percentages. Each unit then calculates its V-NBT
    costs independently with its allocated share of generation.

    Args:
        common_area_hourly: Common area load (if any on central meter)
        unit_hourly_data: Dict of unit_name -> hourly usage data
        pv_hourly_generation: 8760 hours of PV generation (kWh)
        allocations: Virtual meter allocation for each unit
        tariff: V-NBT tariff to apply

    Returns:
        Dict of unit_name -> VnbtCostBreakdown
    """
    results = {}

    # Create allocation lookup
    alloc_by_unit = {a.unit_name: a for a in allocations}

    # Calculate for each unit
    for unit_name, hourly_data in unit_hourly_data.items():
        alloc = alloc_by_unit.get(unit_name)
        if alloc is None:
            continue

        # Apply PV allocation to unit hourly data
        allocated_hourly = []
        for i, h in enumerate(hourly_data):
            pv_alloc = pv_hourly_generation[i] * alloc.allocation_fraction

            allocated_hourly.append(HourlyNetUsage(
                month=h.month,
                day=h.day,
                hour=h.hour,
                gross_load_kwh=h.gross_load_kwh,
                pv_generation_kwh=pv_alloc,
                battery_discharge_kwh=h.battery_discharge_kwh,
                battery_charge_kwh=h.battery_charge_kwh,
                is_weekend=h.is_weekend,
            ))

        # Calculate V-NBT costs for this unit
        results[unit_name] = calculate_vnbt_costs(allocated_hourly, tariff)

    return results
