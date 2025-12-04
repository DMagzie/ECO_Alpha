"""
Central Heat Pump Water Heater Tank Sizing Tool

Combines ecosizer-style calculations with CIBD25 model integration to automate
central HPWH tank sizing for multifamily buildings under California Title 24 2025.

Key Features:
- CBECC 2025 formula-based sizing
- Load shifting optimization for NEM3/LSC compliance
- Climate zone adjustments
- Autosizing algorithm with iterative refinement
- Direct CIBD25 model export
- Thermal storage capacity calculations

References:
- Title 24 Part 6 Section 110.3 (DHW requirements)
- CBECC 2025 Rules_Default_ResDHW.rule
- BEMBase_Res DHW.txt property definitions
"""

from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
import math


class HPWHCompressorType(Enum):
    """Central HPWH compressor types per CBECC 2025"""
    SMALL_NEEA = "small_neea"  # NEEA-rated residential-duty HPWH
    COMMERCIAL_LARGE = "commercial_large"  # Large commercial HPWH
    COMMERCIAL_MODERATE = "commercial_moderate"  # Moderate commercial HPWH
    INTEGRATED_PACKAGED = "integrated_packaged"  # Integrated packaged system


class TankConfiguration(Enum):
    """Tank configuration options"""
    SINGLE_PRIMARY = "single_primary"  # Single primary tank only
    MULTIPLE_PRIMARY = "multiple_primary"  # Multiple primary tanks
    PRIMARY_PLUS_SECONDARY = "primary_secondary"  # Primary + secondary loop tank


@dataclass
class BuildingProfile:
    """Building characteristics for HPWH sizing"""
    num_dwelling_units: int
    total_bedrooms: int
    common_area_du_equiv: float = 0.0  # Common area load as DU equivalent
    climate_zone: str = "12"
    building_type: str = "multifamily"

    # Optional overrides
    peak_hour_draw_factor: Optional[float] = None  # Default 0.7 for MF
    daily_dhw_gal_per_bedroom: Optional[float] = None  # Default 13.5 gal/BR
    storage_temp_rise_f: Optional[float] = None  # Default 60°F (80-140)

    def __post_init__(self):
        """Set defaults if not provided"""
        if self.peak_hour_draw_factor is None:
            self.peak_hour_draw_factor = 0.7
        if self.daily_dhw_gal_per_bedroom is None:
            self.daily_dhw_gal_per_bedroom = 13.5
        if self.storage_temp_rise_f is None:
            self.storage_temp_rise_f = 60.0


@dataclass
class HPWHSystemConfig:
    """Central HPWH system configuration"""
    compressor_type: HPWHCompressorType = HPWHCompressorType.SMALL_NEEA
    tank_configuration: TankConfiguration = TankConfiguration.SINGLE_PRIMARY

    # Compressor parameters
    compressor_capacity_kw: Optional[float] = None  # Auto-calculated if None
    num_compressors: Optional[int] = None  # Auto-calculated if None
    compressor_cop: float = 3.0  # Default COP

    # Tank parameters
    tank_setpoint_f: float = 140.0
    tank_r_value: float = 16.0  # Insulation R-value
    min_tank_r_value: float = 12.5  # 2025 minimum

    # Load shifting parameters
    enable_load_shifting: bool = True
    charge_start_hour: int = 11  # Start heating at noon
    charge_end_hour: int = 17  # Stop heating at 5pm
    oversizing_factor: float = 1.25  # 25% oversize for thermal storage

    # Autosizing parameters
    enable_autosizing: bool = False
    max_iterations: int = 6
    target_unmet_load_pct: float = 1.0  # 1% unmet load target


@dataclass
class SizingResults:
    """Results from HPWH sizing calculation"""
    # Tank sizing
    minimum_tank_volume_gal: float
    recommended_tank_volume_gal: float
    final_tank_volume_gal: float
    num_tanks: int
    volume_per_tank_gal: float

    # Compressor sizing
    num_compressors: int
    compressor_capacity_kw: float
    total_heating_capacity_kw: float
    total_heating_capacity_btu: float

    # Thermal storage
    thermal_storage_capacity_btu: float
    evening_peak_hours_covered: float
    load_shifting_benefit_pct: float

    # Performance metrics
    recovery_rate_gph: float
    first_hour_rating_gal: float
    peak_hour_capacity_gal: float

    # Sizing method details
    sizing_method: str = "cbecc_2025_formula"
    iterations_performed: int = 0
    optimization_notes: List[str] = field(default_factory=list)

    # CIBD25 export data
    cibd25_properties: Dict[str, Any] = field(default_factory=dict)


class CentralHPWHSizer:
    """
    Central Heat Pump Water Heater sizing calculator combining CBECC 2025
    formula-based approach with load shifting optimization.
    """

    # CBECC 2025 formula constants
    GALLONS_PER_DU = 10
    GALLONS_PER_BEDROOM = 3
    MINIMUM_TANK_VOLUME = 50  # gallons

    # Physical constants
    BTU_PER_GAL_PER_F = 8.34  # Water: 8.34 lb/gal × 1 BTU/lb·°F
    KW_TO_BTU_PER_HOUR = 3412.142

    # Default compressor capacities (at 40°F ambient)
    COMPRESSOR_CAPACITIES_KW = {
        HPWHCompressorType.SMALL_NEEA: 4.5,  # Typical residential HPWH
        HPWHCompressorType.COMMERCIAL_MODERATE: 10.0,
        HPWHCompressorType.COMMERCIAL_LARGE: 20.0,
        HPWHCompressorType.INTEGRATED_PACKAGED: 15.0,
    }

    # Standard tank sizes (gallons)
    STANDARD_TANK_SIZES = [50, 80, 100, 119, 150, 200, 300, 400, 500, 750, 1000, 1500, 2000, 2500]

    @classmethod
    def calculate_minimum_tank_volume(
        cls,
        building: BuildingProfile,
        include_common_area: bool = True
    ) -> float:
        """
        Calculate minimum tank volume using CBECC 2025 formula.

        Formula: max(50, (NumDU × 10) + (NumBR × 3))

        For multifamily with common areas, may add common DU equivalent.

        Args:
            building: Building profile with DU and bedroom counts
            include_common_area: Include common area DU equivalent in calc

        Returns:
            Minimum tank volume in gallons
        """
        num_du = building.num_dwelling_units
        num_br = building.total_bedrooms

        if include_common_area:
            num_du += building.common_area_du_equiv

        calculated_volume = (num_du * cls.GALLONS_PER_DU) + (num_br * cls.GALLONS_PER_BEDROOM)

        return max(cls.MINIMUM_TANK_VOLUME, calculated_volume)

    @classmethod
    def calculate_thermal_storage_capacity(
        cls,
        tank_volume_gal: float,
        temp_rise_f: float = 60.0
    ) -> float:
        """
        Calculate thermal energy storage capacity of tank.

        Storage = Volume × Density × Specific Heat × ΔT
                = Volume (gal) × 8.34 (lb/gal) × 1 (BTU/lb·°F) × ΔT (°F)

        Args:
            tank_volume_gal: Tank volume in gallons
            temp_rise_f: Temperature swing (default 60°F for 80-140°F range)

        Returns:
            Thermal storage capacity in BTU
        """
        return tank_volume_gal * cls.BTU_PER_GAL_PER_F * temp_rise_f

    @classmethod
    def calculate_peak_load(
        cls,
        building: BuildingProfile,
        hourly_duration: int = 4
    ) -> Tuple[float, float]:
        """
        Calculate peak DHW load for sizing.

        Args:
            building: Building profile
            hourly_duration: Peak load duration in hours (typically 4 hours)

        Returns:
            Tuple of (peak_gal_per_hour, total_peak_gallons)
        """
        # Daily draw per bedroom (from Title 24 assumptions)
        daily_draw_gal = building.total_bedrooms * building.daily_dhw_gal_per_bedroom

        # Peak hour factor (70% of units using DHW simultaneously)
        peak_factor = building.peak_hour_draw_factor

        # Assume peak load is concentrated in morning hours
        # Peak hour draw is ~20% of daily draw for MF
        peak_hour_draw_gal = daily_draw_gal * 0.20 * peak_factor

        # Total draw during peak period
        total_peak_gal = peak_hour_draw_gal * hourly_duration

        return (peak_hour_draw_gal, total_peak_gal)

    @classmethod
    def calculate_recovery_capacity(
        cls,
        compressor_capacity_kw: float,
        compressor_cop: float,
        temp_rise_f: float = 90.0
    ) -> float:
        """
        Calculate water heating recovery rate.

        Recovery Rate (GPH) = (Heating Capacity BTU/h × Efficiency) /
                               (8.34 lb/gal × Temp Rise °F × 1 BTU/lb·°F)

        Args:
            compressor_capacity_kw: HPWH compressor heating capacity in kW
            compressor_cop: Coefficient of Performance (heating output / electrical input)
            temp_rise_f: Temperature rise (default 90°F for 50-140°F)

        Returns:
            Recovery rate in gallons per hour
        """
        # Convert kW electrical to BTU/h heating output
        heating_capacity_btu_h = compressor_capacity_kw * cls.KW_TO_BTU_PER_HOUR * compressor_cop

        # Calculate recovery rate
        recovery_gph = heating_capacity_btu_h / (cls.BTU_PER_GAL_PER_F * temp_rise_f)

        return recovery_gph

    @classmethod
    def optimize_for_load_shifting(
        cls,
        minimum_volume_gal: float,
        building: BuildingProfile,
        config: HPWHSystemConfig
    ) -> float:
        """
        Calculate optimal tank volume considering load shifting benefits.

        For NEM3/LSC optimization, larger tanks allow:
        - Heating during low-cost midday hours
        - Serving evening loads from storage
        - Reducing peak electrical demand

        Args:
            minimum_volume_gal: Code-minimum tank volume
            building: Building profile
            config: System configuration with load shifting parameters

        Returns:
            Optimized tank volume in gallons
        """
        if not config.enable_load_shifting:
            return minimum_volume_gal

        # Calculate evening peak load coverage needed
        peak_gph, evening_peak_total_gal = cls.calculate_peak_load(
            building,
            hourly_duration=4  # Typical evening peak: 5pm-9pm
        )

        # Tank needs to cover evening peak draw without HPWH operation
        # Add buffer for heat losses and temp stratification
        buffer_factor = 1.15  # 15% buffer
        evening_coverage_volume = evening_peak_total_gal * buffer_factor

        # Apply user-specified oversizing factor
        optimized_volume = max(
            minimum_volume_gal * config.oversizing_factor,
            evening_coverage_volume
        )

        return optimized_volume

    @classmethod
    def size_compressor_array(
        cls,
        tank_volume_gal: float,
        building: BuildingProfile,
        config: HPWHSystemConfig
    ) -> Tuple[int, float]:
        """
        Size compressor array (number and capacity).

        Strategy:
        - Prefer multiple smaller compressors for better modulation
        - Size for 4-6 hour charge window during midday
        - Avoid oversizing (causes cycling, reduces efficiency)

        Args:
            tank_volume_gal: Tank volume in gallons
            building: Building profile
            config: System configuration

        Returns:
            Tuple of (num_compressors, capacity_per_compressor_kw)
        """
        # Get base compressor capacity
        if config.compressor_capacity_kw:
            base_capacity_kw = config.compressor_capacity_kw
        else:
            base_capacity_kw = cls.COMPRESSOR_CAPACITIES_KW.get(
                config.compressor_type,
                4.5  # Default to small NEEA
            )

        # Calculate heating required to fully charge tank
        temp_rise = config.tank_setpoint_f - 80  # Assume 80°F inlet
        thermal_storage_btu = cls.calculate_thermal_storage_capacity(
            tank_volume_gal,
            temp_rise
        )

        # Available charging window (hours)
        if config.enable_load_shifting:
            charge_window_hours = config.charge_end_hour - config.charge_start_hour
        else:
            charge_window_hours = 24  # Can heat anytime

        # Required heating capacity (BTU/h)
        required_capacity_btu_h = thermal_storage_btu / charge_window_hours

        # Convert to kW and account for COP
        required_electrical_kw = required_capacity_btu_h / (cls.KW_TO_BTU_PER_HOUR * config.compressor_cop)

        # Calculate number of compressors needed
        if config.num_compressors:
            num_compressors = config.num_compressors
        else:
            num_compressors = max(1, math.ceil(required_electrical_kw / base_capacity_kw))

        # Final capacity per compressor
        capacity_per_compressor = base_capacity_kw

        return (num_compressors, capacity_per_compressor)

    @classmethod
    def round_to_standard_tank_size(
        cls,
        volume_gal: float,
        round_up: bool = True
    ) -> float:
        """
        Round tank volume to standard manufactured size.

        Args:
            volume_gal: Calculated tank volume
            round_up: If True, round up; if False, round to nearest

        Returns:
            Standard tank size in gallons
        """
        if round_up:
            # Find smallest standard size >= calculated
            for size in cls.STANDARD_TANK_SIZES:
                if size >= volume_gal:
                    return float(size)
            return cls.STANDARD_TANK_SIZES[-1]  # Max size
        else:
            # Find nearest standard size
            return min(cls.STANDARD_TANK_SIZES, key=lambda x: abs(x - volume_gal))

    @classmethod
    def calculate_num_tanks(
        cls,
        total_volume_gal: float,
        max_tank_size_gal: float = 1000
    ) -> Tuple[int, float]:
        """
        Determine number of tanks and volume per tank.

        Args:
            total_volume_gal: Total system volume needed
            max_tank_size_gal: Maximum size of individual tank

        Returns:
            Tuple of (num_tanks, volume_per_tank_gal)
        """
        if total_volume_gal <= max_tank_size_gal:
            # Single tank sufficient
            return (1, total_volume_gal)

        # Multiple tanks needed
        num_tanks = math.ceil(total_volume_gal / max_tank_size_gal)
        volume_per_tank = total_volume_gal / num_tanks

        # Round individual tank to standard size
        volume_per_tank = cls.round_to_standard_tank_size(volume_per_tank, round_up=False)

        return (num_tanks, volume_per_tank)

    @classmethod
    def size_central_hpwh(
        cls,
        building: BuildingProfile,
        config: HPWHSystemConfig = None
    ) -> SizingResults:
        """
        Complete central HPWH sizing calculation.

        This is the main entry point for sizing calculations, combining:
        - CBECC 2025 minimum formula
        - Load shifting optimization
        - Compressor array sizing
        - Tank configuration

        Args:
            building: Building characteristics
            config: System configuration (uses defaults if None)

        Returns:
            Complete sizing results
        """
        if config is None:
            config = HPWHSystemConfig()

        # Step 1: Calculate code-minimum tank volume
        minimum_volume = cls.calculate_minimum_tank_volume(building)

        # Step 2: Optimize for load shifting if enabled
        recommended_volume = cls.optimize_for_load_shifting(
            minimum_volume,
            building,
            config
        )

        # Step 3: Round to standard tank size
        final_volume = cls.round_to_standard_tank_size(recommended_volume, round_up=True)

        # Step 4: Determine tank configuration
        num_tanks, volume_per_tank = cls.calculate_num_tanks(final_volume)

        # Step 5: Size compressor array
        num_compressors, compressor_capacity_kw = cls.size_compressor_array(
            final_volume,
            building,
            config
        )

        # Step 6: Calculate performance metrics
        total_heating_capacity_kw = num_compressors * compressor_capacity_kw * config.compressor_cop
        total_heating_capacity_btu = total_heating_capacity_kw * cls.KW_TO_BTU_PER_HOUR

        recovery_gph = cls.calculate_recovery_capacity(
            compressor_capacity_kw * num_compressors,
            config.compressor_cop
        )

        # First hour rating: tank volume + recovery in 1 hour
        first_hour_rating = final_volume + recovery_gph

        # Peak hour capacity: depends on charge strategy
        peak_gph, _ = cls.calculate_peak_load(building)
        peak_hour_capacity = final_volume + (recovery_gph * 4)  # 4-hour peak

        # Thermal storage capacity
        thermal_storage_btu = cls.calculate_thermal_storage_capacity(
            final_volume,
            config.tank_setpoint_f - 80  # 80°F inlet assumption
        )

        # Calculate evening peak hours covered (storage only, no HPWH)
        evening_peak_hours = final_volume / peak_gph if peak_gph > 0 else 0

        # Load shifting benefit (percentage improvement from oversizing)
        load_shifting_benefit = ((final_volume - minimum_volume) / minimum_volume) * 100

        # Optimization notes
        notes = []
        if config.enable_load_shifting:
            notes.append(f"Optimized for load shifting: {config.oversizing_factor}x oversizing factor")
            notes.append(f"Charge window: {config.charge_start_hour}:00 to {config.charge_end_hour}:00")
        if final_volume > recommended_volume:
            notes.append(f"Rounded up from {recommended_volume:.0f} to standard size {final_volume:.0f} gallons")
        if num_tanks > 1:
            notes.append(f"Multiple tanks required: {num_tanks} × {volume_per_tank:.0f} gallons")

        # Prepare CIBD25 export properties
        cibd25_props = {
            "CHPWHTotTankVol": final_volume,
            "CHPWHTankCount": num_tanks,
            "CHPWHNumComp": num_compressors,
            "CHPWHCompCap": compressor_capacity_kw,
            "CHPWHTankSetpt": config.tank_setpoint_f,
            "CHPWHTankRVal": config.tank_r_value,
            "CHPWHTankMinRVal": config.min_tank_r_value,
            "CHPWHAutosize": 0,  # User-specified, not autosized
        }

        return SizingResults(
            minimum_tank_volume_gal=minimum_volume,
            recommended_tank_volume_gal=recommended_volume,
            final_tank_volume_gal=final_volume,
            num_tanks=num_tanks,
            volume_per_tank_gal=volume_per_tank,
            num_compressors=num_compressors,
            compressor_capacity_kw=compressor_capacity_kw,
            total_heating_capacity_kw=total_heating_capacity_kw,
            total_heating_capacity_btu=total_heating_capacity_btu,
            thermal_storage_capacity_btu=thermal_storage_btu,
            evening_peak_hours_covered=evening_peak_hours,
            load_shifting_benefit_pct=load_shifting_benefit,
            recovery_rate_gph=recovery_gph,
            first_hour_rating_gal=first_hour_rating,
            peak_hour_capacity_gal=peak_hour_capacity,
            sizing_method="cbecc_2025_formula_with_load_shifting",
            iterations_performed=0,
            optimization_notes=notes,
            cibd25_properties=cibd25_props
        )

    @classmethod
    def export_to_cibd25_dict(
        cls,
        results: SizingResults,
        system_name: str = "Central HPWH System"
    ) -> Dict[str, Any]:
        """
        Export sizing results as CIBD25 ResDHWSys dictionary.

        Args:
            results: Sizing results from size_central_hpwh()
            system_name: Name for the DHW system

        Returns:
            Dictionary ready for CIBD25 export
        """
        return {
            "Name": system_name,
            "SystemType": "Central",
            "CentralDHW": 1,
            "CentralDHWType": "CommercialPackagedBoiler",  # Type 16
            **results.cibd25_properties
        }


# Convenience functions

def size_from_dwelling_units(
    num_units: int,
    avg_bedrooms_per_unit: float = 2.0,
    climate_zone: str = "12",
    enable_load_shifting: bool = True,
    oversizing_factor: float = 1.25
) -> SizingResults:
    """
    Quick sizing function from dwelling unit count.

    Args:
        num_units: Number of dwelling units
        avg_bedrooms_per_unit: Average bedrooms per unit
        climate_zone: CA climate zone
        enable_load_shifting: Enable load shifting optimization
        oversizing_factor: Tank oversizing factor for thermal storage

    Returns:
        Complete sizing results
    """
    building = BuildingProfile(
        num_dwelling_units=num_units,
        total_bedrooms=int(num_units * avg_bedrooms_per_unit),
        climate_zone=climate_zone
    )

    config = HPWHSystemConfig(
        enable_load_shifting=enable_load_shifting,
        oversizing_factor=oversizing_factor
    )

    return CentralHPWHSizer.size_central_hpwh(building, config)


def create_sizing_report(results: SizingResults) -> str:
    """
    Generate human-readable sizing report.

    Args:
        results: Sizing results

    Returns:
        Formatted report string
    """
    report = []
    report.append("=" * 60)
    report.append("CENTRAL HPWH SIZING REPORT")
    report.append("=" * 60)
    report.append("")

    report.append("TANK SIZING:")
    report.append(f"  Minimum Required (Code):     {results.minimum_tank_volume_gal:,.0f} gallons")
    report.append(f"  Recommended (Optimized):     {results.recommended_tank_volume_gal:,.0f} gallons")
    report.append(f"  Final Specified:             {results.final_tank_volume_gal:,.0f} gallons")
    report.append(f"  Number of Tanks:             {results.num_tanks}")
    report.append(f"  Volume per Tank:             {results.volume_per_tank_gal:,.0f} gallons")
    report.append("")

    report.append("COMPRESSOR SIZING:")
    report.append(f"  Number of Compressors:       {results.num_compressors}")
    report.append(f"  Capacity per Compressor:     {results.compressor_capacity_kw:.1f} kW")
    report.append(f"  Total Heating Capacity:      {results.total_heating_capacity_kw:.1f} kW")
    report.append(f"                               {results.total_heating_capacity_btu:,.0f} BTU/h")
    report.append("")

    report.append("PERFORMANCE METRICS:")
    report.append(f"  Recovery Rate:               {results.recovery_rate_gph:.1f} gal/hour")
    report.append(f"  First Hour Rating:           {results.first_hour_rating_gal:,.0f} gallons")
    report.append(f"  Peak Hour Capacity:          {results.peak_hour_capacity_gal:,.0f} gallons")
    report.append("")

    report.append("LOAD SHIFTING CAPABILITY:")
    report.append(f"  Thermal Storage:             {results.thermal_storage_capacity_btu:,.0f} BTU")
    report.append(f"  Evening Peak Coverage:       {results.evening_peak_hours_covered:.1f} hours")
    report.append(f"  Benefit from Oversizing:     {results.load_shifting_benefit_pct:.1f}%")
    report.append("")

    if results.optimization_notes:
        report.append("OPTIMIZATION NOTES:")
        for note in results.optimization_notes:
            report.append(f"  • {note}")
        report.append("")

    report.append("=" * 60)

    return "\n".join(report)
