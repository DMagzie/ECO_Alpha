"""
Whole-Building Energy Schema.

This module defines the unified data models for combining simulation engine output
with calculated site loads, providing full 8760 hourly profiles for accurate TOU analysis.

Key Principle: No injection of site loads into simulation models.
Parallel calculation with aggregation at the reporting layer.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple, TYPE_CHECKING
from enum import Enum

if TYPE_CHECKING:
    from ..model import HourlyEnergy, SimulationOutput


class EnergySource(Enum):
    """Source of energy data."""
    CBECC = "cbecc"
    ENERGYPLUS = "energyplus"
    CALCULATED = "calculated"


class ReportMode(Enum):
    """Report granularity modes for whole-building reports."""
    FULL = "full"           # Modeled | Site Loads | Combined (3 columns)
    SUMMARY = "summary"     # Site Loads | Combined (2 columns)
    SIMPLE = "simple"       # Combined only (1 column)


class LoadCategory(Enum):
    """Categories of site loads."""
    INTERIOR_LIGHTING = "interior_lighting"
    PARKING = "parking"
    SITE_LIGHTING = "site_lighting"
    POOL_PUMP = "pool_pump"
    POOL_HEATER = "pool_heater"
    SPA = "spa"
    ELEVATOR = "elevator"
    ESCALATOR = "escalator"
    EV_CHARGER = "ev_charger"
    IT_TELECOM = "it_telecom"
    TRASH_COMPACTOR = "trash_compactor"
    COMMERCIAL_KITCHEN = "commercial_kitchen"
    COMMON_LAUNDRY = "common_laundry"
    SECURITY_SYSTEMS = "security_systems"
    FIRE_LIFE_SAFETY = "fire_life_safety"
    IRRIGATION = "irrigation"
    EXHAUST_SYSTEMS = "exhaust_systems"
    WATER_PUMPS = "water_pumps"
    MISCELLANEOUS = "miscellaneous"


@dataclass
class HourlyRecord:
    """
    Single hour of energy data for whole-building calculations.

    This is the unified format used for both modeled and calculated site loads.
    Compatible with the existing HourlyEnergy class but simplified for aggregation.
    """
    month: int                      # 1-12
    day: int                        # 1-31
    hour: int                       # 1-24

    # Primary energy values
    elec_kwh: float = 0.0           # Total electricity consumption
    gas_therms: float = 0.0         # Total gas consumption
    demand_kw: float = 0.0          # Instantaneous demand (kWh for hour = kW)

    # Optional end-use breakdown (typically for modeled data)
    cooling_kwh: float = 0.0
    heating_kwh: float = 0.0
    heating_therms: float = 0.0
    fans_kwh: float = 0.0
    lighting_kwh: float = 0.0
    plugs_kwh: float = 0.0
    dhw_kwh: float = 0.0
    dhw_therms: float = 0.0
    pv_kwh: float = 0.0             # PV generation (positive = generation)

    @property
    def net_elec_kwh(self) -> float:
        """Net electricity after PV generation."""
        return self.elec_kwh - self.pv_kwh

    @classmethod
    def from_hourly_energy(cls, h: "HourlyEnergy") -> "HourlyRecord":
        """Convert from existing HourlyEnergy model."""
        return cls(
            month=h.month,
            day=h.day,
            hour=h.hour,
            elec_kwh=h.elec_total_kwh,
            gas_therms=h.gas_total_therm,
            demand_kw=h.elec_total_kwh,  # Hourly kWh = kW for that hour
            cooling_kwh=h.elec_cooling_kwh,
            heating_kwh=h.elec_heating_kwh,
            heating_therms=h.gas_heating_therm,
            fans_kwh=h.elec_fans_kwh,
            lighting_kwh=h.elec_lighting_kwh,
            plugs_kwh=h.elec_receptacle_kwh,
            dhw_kwh=h.elec_dhw_kwh,
            dhw_therms=h.gas_dhw_therm,
            pv_kwh=h.pv_generation_kwh,
        )


@dataclass
class AnnualSummary:
    """Annual energy totals and peaks."""
    total_elec_kwh: float = 0.0
    total_gas_therms: float = 0.0
    peak_demand_kw: float = 0.0
    peak_demand_month: int = 0
    peak_demand_hour: int = 0

    # Generation
    pv_generation_kwh: float = 0.0
    net_elec_kwh: float = 0.0

    # Monthly peaks for demand charge analysis
    monthly_peaks_kw: List[float] = field(default_factory=lambda: [0.0] * 12)

    # EUI metrics (populated if floor area is known)
    elec_eui_kwh_sf: float = 0.0
    gas_eui_therm_sf: float = 0.0

    @classmethod
    def from_hourly(cls, hourly: List[HourlyRecord], floor_area_sf: float = 0.0) -> "AnnualSummary":
        """Calculate annual summary from hourly data."""
        if not hourly:
            return cls()

        total_elec = sum(h.elec_kwh for h in hourly)
        total_gas = sum(h.gas_therms for h in hourly)
        total_pv = sum(h.pv_kwh for h in hourly)

        # Find peak demand
        peak_kw = 0.0
        peak_month = 0
        peak_hour = 0
        monthly_peaks = [0.0] * 12

        for h in hourly:
            # Track overall peak
            if h.demand_kw > peak_kw:
                peak_kw = h.demand_kw
                peak_month = h.month
                peak_hour = h.hour

            # Track monthly peaks
            month_idx = h.month - 1
            if h.demand_kw > monthly_peaks[month_idx]:
                monthly_peaks[month_idx] = h.demand_kw

        summary = cls(
            total_elec_kwh=total_elec,
            total_gas_therms=total_gas,
            peak_demand_kw=peak_kw,
            peak_demand_month=peak_month,
            peak_demand_hour=peak_hour,
            pv_generation_kwh=total_pv,
            net_elec_kwh=total_elec - total_pv,
            monthly_peaks_kw=monthly_peaks,
        )

        # Calculate EUI if floor area provided
        if floor_area_sf > 0:
            summary.elec_eui_kwh_sf = total_elec / floor_area_sf
            summary.gas_eui_therm_sf = total_gas / floor_area_sf

        return summary


@dataclass
class EnergyStream:
    """
    A stream of energy data (modeled, site loads, or combined).

    This is the core abstraction for parallel energy aggregation.
    Each stream has both annual totals and 8760 hourly records.
    """
    source: EnergySource
    annual: AnnualSummary
    hourly: List[HourlyRecord]  # 8760 records

    @classmethod
    def from_hourly(
        cls,
        source: EnergySource,
        hourly: List[HourlyRecord],
        floor_area_sf: float = 0.0
    ) -> "EnergyStream":
        """Create stream with annual summary calculated from hourly data."""
        annual = AnnualSummary.from_hourly(hourly, floor_area_sf)
        return cls(source=source, annual=annual, hourly=hourly)

    @classmethod
    def from_simulation_output(cls, output: "SimulationOutput") -> "EnergyStream":
        """Create stream from existing SimulationOutput."""
        hourly = [HourlyRecord.from_hourly_energy(h) for h in output.hourly]
        annual = AnnualSummary.from_hourly(hourly, output.conditioned_area_sf)

        # Copy PV generation from simulation
        annual.pv_generation_kwh = output.annual.pv_generation_kwh

        return cls(
            source=EnergySource.CBECC,
            annual=annual,
            hourly=hourly,
        )

    @classmethod
    def empty(cls, source: EnergySource = EnergySource.CALCULATED) -> "EnergyStream":
        """Create an empty stream with zero values for all 8760 hours."""
        hourly = []
        # Generate empty 8760 hourly records
        month_days = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
        for month, days in enumerate(month_days, start=1):
            for day in range(1, days + 1):
                for hour in range(1, 25):
                    hourly.append(HourlyRecord(month=month, day=day, hour=hour))

        return cls(
            source=source,
            annual=AnnualSummary(),
            hourly=hourly,
        )


@dataclass
class SiteLoadDetail:
    """
    Detail for a single site load category.

    Includes calculation inputs for audit trail and transparency.
    """
    category: LoadCategory
    name: str                           # User-provided name
    description: str = ""               # Optional description

    # Energy totals
    annual_kwh: float = 0.0
    annual_therms: float = 0.0
    peak_kw: float = 0.0

    # Hourly profile (8760 records if generated)
    hourly: List[HourlyRecord] = field(default_factory=list)

    # Calculation inputs (for audit trail)
    inputs: Dict = field(default_factory=dict)
    calculation_method: str = ""
    load_shape_profile: str = ""

    # Flag for modeled loads (to prevent double-counting)
    is_modeled_in_simulation: bool = False

    def get_hourly_kwh(self) -> List[float]:
        """Get just the hourly kWh values."""
        return [h.elec_kwh for h in self.hourly]

    def get_hourly_therms(self) -> List[float]:
        """Get just the hourly therm values."""
        return [h.gas_therms for h in self.hourly]


@dataclass
class ProjectInfo:
    """Project metadata for whole-building energy analysis."""
    name: str
    address: Optional[str] = None
    climate_zone: Optional[int] = None
    building_type: Optional[str] = None
    floor_area_sf: Optional[float] = None
    num_stories: Optional[int] = None
    num_units: Optional[int] = None

    # Simulation info
    simulation_engine: Optional[str] = None
    simulation_file: Optional[str] = None
    simulation_date: Optional[str] = None

    @classmethod
    def from_simulation_output(cls, output: "SimulationOutput") -> "ProjectInfo":
        """Create ProjectInfo from SimulationOutput."""
        return cls(
            name=output.project_name,
            building_type=output.building_type,
            floor_area_sf=output.conditioned_area_sf,
            simulation_engine="CBECC",
            simulation_file=output.model_file,
            simulation_date=output.run_date,
        )


@dataclass
class WholeBuildingEnergy:
    """
    Complete whole-building energy data.

    This is the top-level container that combines:
    - Modeled energy from simulation (CBECC or EnergyPlus)
    - Calculated site loads
    - Combined totals for whole-building analysis

    Key principle: No injection - these are parallel streams that
    are aggregated at reporting time.
    """
    project: ProjectInfo
    modeled: EnergyStream
    site_loads: EnergyStream
    combined: EnergyStream

    # Detailed site load breakdown
    site_load_details: List[SiteLoadDetail] = field(default_factory=list)

    # Report configuration
    report_mode: ReportMode = ReportMode.FULL

    @classmethod
    def create(
        cls,
        project: ProjectInfo,
        modeled: EnergyStream,
        site_load_details: List[SiteLoadDetail],
        report_mode: ReportMode = ReportMode.FULL,
        diversity_factor: float = 0.9,
    ) -> "WholeBuildingEnergy":
        """
        Create whole-building energy with auto-calculated combined stream.

        Args:
            project: Project metadata
            modeled: Energy stream from simulation
            site_load_details: List of calculated site loads
            report_mode: Reporting granularity
            diversity_factor: Factor applied to coincident peak (default 0.9)

        Returns:
            WholeBuildingEnergy with combined stream calculated
        """
        # Filter out loads that are already in simulation
        non_modeled_loads = [
            load for load in site_load_details
            if not load.is_modeled_in_simulation
        ]

        # Combine site loads into single stream
        site_loads = cls._combine_site_loads(non_modeled_loads)

        # Merge modeled and site loads into combined stream
        combined = cls._merge_streams(modeled, site_loads, diversity_factor)

        return cls(
            project=project,
            modeled=modeled,
            site_loads=site_loads,
            combined=combined,
            site_load_details=site_load_details,
            report_mode=report_mode,
        )

    @classmethod
    def from_simulation_only(
        cls,
        output: "SimulationOutput",
        report_mode: ReportMode = ReportMode.SIMPLE,
    ) -> "WholeBuildingEnergy":
        """
        Create whole-building energy from simulation only (no site loads).

        Useful for existing workflows that only use modeled data.
        """
        project = ProjectInfo.from_simulation_output(output)
        modeled = EnergyStream.from_simulation_output(output)
        site_loads = EnergyStream.empty()

        return cls(
            project=project,
            modeled=modeled,
            site_loads=site_loads,
            combined=modeled,  # Combined = modeled when no site loads
            site_load_details=[],
            report_mode=report_mode,
        )

    @staticmethod
    def _combine_site_loads(loads: List[SiteLoadDetail]) -> EnergyStream:
        """Combine multiple site loads into single energy stream."""
        if not loads:
            return EnergyStream.empty()

        # Start with empty 8760 structure
        month_days = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
        combined_hourly = []

        hour_idx = 0
        for month, days in enumerate(month_days, start=1):
            for day in range(1, days + 1):
                for hour in range(1, 25):
                    elec_kwh = 0.0
                    gas_therms = 0.0
                    lighting_kwh = 0.0

                    # Sum contributions from each load
                    for load in loads:
                        if load.hourly and hour_idx < len(load.hourly):
                            h = load.hourly[hour_idx]
                            elec_kwh += h.elec_kwh
                            gas_therms += h.gas_therms
                            lighting_kwh += h.lighting_kwh

                    combined_hourly.append(HourlyRecord(
                        month=month,
                        day=day,
                        hour=hour,
                        elec_kwh=elec_kwh,
                        gas_therms=gas_therms,
                        demand_kw=elec_kwh,  # Hourly kWh = kW
                        lighting_kwh=lighting_kwh,
                    ))
                    hour_idx += 1

        return EnergyStream.from_hourly(EnergySource.CALCULATED, combined_hourly)

    @staticmethod
    def _merge_streams(
        modeled: EnergyStream,
        site_loads: EnergyStream,
        diversity_factor: float = 0.9
    ) -> EnergyStream:
        """Merge modeled and site load streams into combined stream."""
        combined_hourly = []

        for i in range(min(len(modeled.hourly), len(site_loads.hourly))):
            m = modeled.hourly[i]
            s = site_loads.hourly[i]

            # Sum energy
            elec_kwh = m.elec_kwh + s.elec_kwh
            gas_therms = m.gas_therms + s.gas_therms

            # For demand, apply diversity factor when combining
            # (loads don't all peak at exactly the same time)
            coincident_demand = (m.demand_kw + s.demand_kw) * diversity_factor

            combined_hourly.append(HourlyRecord(
                month=m.month,
                day=m.day,
                hour=m.hour,
                elec_kwh=elec_kwh,
                gas_therms=gas_therms,
                demand_kw=coincident_demand,
                cooling_kwh=m.cooling_kwh,
                heating_kwh=m.heating_kwh,
                heating_therms=m.heating_therms,
                fans_kwh=m.fans_kwh,
                lighting_kwh=m.lighting_kwh + s.lighting_kwh,
                plugs_kwh=m.plugs_kwh,
                dhw_kwh=m.dhw_kwh,
                dhw_therms=m.dhw_therms,
                pv_kwh=m.pv_kwh,  # PV only from modeled
            ))

        return EnergyStream.from_hourly(EnergySource.CALCULATED, combined_hourly)

    def get_summary_dict(self) -> Dict:
        """Get summary data based on report mode."""
        result = {
            'project': self.project.name,
            'mode': self.report_mode.value,
            'floor_area_sf': self.project.floor_area_sf,
        }

        if self.report_mode == ReportMode.FULL:
            result['modeled'] = self._stream_to_dict(self.modeled, "Modeled")
            result['site_loads'] = self._stream_to_dict(self.site_loads, "Site Loads")
            result['combined'] = self._stream_to_dict(self.combined, "Combined")

        elif self.report_mode == ReportMode.SUMMARY:
            result['site_loads'] = self._stream_to_dict(self.site_loads, "Site Loads")
            result['combined'] = self._stream_to_dict(self.combined, "Combined")

        elif self.report_mode == ReportMode.SIMPLE:
            result['whole_building'] = self._stream_to_dict(self.combined, "Whole Building")

        return result

    def _stream_to_dict(self, stream: EnergyStream, label: str) -> Dict:
        """Convert energy stream to dictionary."""
        return {
            'label': label,
            'source': stream.source.value,
            'annual_kwh': stream.annual.total_elec_kwh,
            'annual_therms': stream.annual.total_gas_therms,
            'peak_demand_kw': stream.annual.peak_demand_kw,
            'pv_generation_kwh': stream.annual.pv_generation_kwh,
            'net_kwh': stream.annual.net_elec_kwh,
            'elec_eui': stream.annual.elec_eui_kwh_sf,
            'gas_eui': stream.annual.gas_eui_therm_sf,
        }

    def get_site_load_breakdown(self) -> List[Dict]:
        """Get detailed breakdown of site loads by category."""
        breakdown = []
        for load in self.site_load_details:
            breakdown.append({
                'category': load.category.value,
                'name': load.name,
                'annual_kwh': load.annual_kwh,
                'annual_therms': load.annual_therms,
                'peak_kw': load.peak_kw,
                'is_modeled': load.is_modeled_in_simulation,
                'calculation_method': load.calculation_method,
            })
        return breakdown
