"""
Whole-Building Energy Aggregator.

Combines simulation engine output with calculated site loads to produce
complete whole-building energy data for LCCA analysis.

Key Principle: No injection of site loads into simulation files.
Parallel calculation with aggregation at the reporting layer.

This module provides:
- SiteLoadAggregator: Calculate and combine all site loads
- WholeBuildingAggregator: Combine simulation + site loads
- Convenience functions for common workflows
"""

from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Dict, Optional, Any, TYPE_CHECKING

from .schema import (
    WholeBuildingEnergy,
    EnergyStream,
    ProjectInfo,
    SiteLoadDetail,
    ReportMode,
    LoadCategory,
)
# Note: site_loads imports are done lazily in __post_init__ to avoid circular imports
from ..parsers.base import SimulationParser, CbeccSimulationParser, get_parser_for_file

if TYPE_CHECKING:
    from ..model import SimulationOutput


@dataclass
class SiteLoadAggregator:
    """
    Aggregates multiple site load calculations into a unified energy stream.

    Provides:
    - Calculator routing based on load category
    - Batch calculation from structured input
    - 8760 hourly profile generation for all loads
    """

    # Calculator instances
    _calculators: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """Initialize calculators with lazy imports to avoid circular dependencies."""
        # Lazy imports to avoid circular import with site_loads -> whole_building -> site_loads
        from ..site_loads.calculators import (
            InteriorLightingCalculator,
            ParkingLightingCalculator,
            SiteLightingCalculator,
            PoolPumpCalculator,
            PoolHeaterCalculator,
            SpaCalculator,
            ElevatorCalculator,
            EscalatorCalculator,
            EVChargerCalculator,
            ITTelecomCalculator,
            WaterPumpCalculator,
            TrashCompactorCalculator,
        )
        self._calculators = {
            LoadCategory.INTERIOR_LIGHTING: InteriorLightingCalculator(),
            LoadCategory.PARKING: ParkingLightingCalculator(),
            LoadCategory.SITE_LIGHTING: SiteLightingCalculator(),
            LoadCategory.POOL_PUMP: PoolPumpCalculator(),
            LoadCategory.POOL_HEATER: PoolHeaterCalculator(),
            LoadCategory.SPA: SpaCalculator(),
            LoadCategory.ELEVATOR: ElevatorCalculator(),
            LoadCategory.ESCALATOR: EscalatorCalculator(),
            LoadCategory.EV_CHARGER: EVChargerCalculator(),
            LoadCategory.IT_TELECOM: ITTelecomCalculator(),
            LoadCategory.WATER_PUMPS: WaterPumpCalculator(),
            LoadCategory.TRASH_COMPACTOR: TrashCompactorCalculator(),
        }

    def calculate_load(
        self,
        category: LoadCategory,
        inputs: Dict,
        name: Optional[str] = None,
        load_shape: Optional[str] = None,
    ) -> SiteLoadDetail:
        """
        Calculate a single site load.

        Args:
            category: Load category (determines which calculator to use)
            inputs: Calculation inputs specific to the category
            name: Optional name for this load
            load_shape: Optional override for load shape profile

        Returns:
            SiteLoadDetail with annual totals and 8760 hourly data
        """
        calculator = self._calculators.get(category)

        if calculator is None:
            # Fall back to generic calculator (lazy import)
            from ..site_loads.calculators import GenericLoadCalculator
            calculator = GenericLoadCalculator(category)

        return calculator.calculate(inputs, load_shape_name=load_shape, name=name)

    def calculate_all(
        self,
        site_loads_input: Dict[str, List[Dict]]
    ) -> List[SiteLoadDetail]:
        """
        Calculate all site loads from structured input.

        Args:
            site_loads_input: Dictionary mapping category names to list of inputs
                Example:
                {
                    "interior_lighting": [
                        {"area_sf": 5000, "space_type": "corridor"},
                        {"area_sf": 1000, "space_type": "lobby"},
                    ],
                    "elevator": [
                        {"num_elevators": 2, "elevator_type": "hydraulic_low_rise"},
                    ],
                }

        Returns:
            List of SiteLoadDetail for all calculated loads
        """
        results = []

        for category_str, load_list in site_loads_input.items():
            # Convert string to LoadCategory
            try:
                category = LoadCategory(category_str.lower())
            except ValueError:
                category = LoadCategory.MISCELLANEOUS

            for i, inputs in enumerate(load_list):
                name = inputs.get("name") or f"{category_str}_{i+1}"
                load_shape = inputs.get("load_shape")

                try:
                    detail = self.calculate_load(
                        category=category,
                        inputs=inputs,
                        name=name,
                        load_shape=load_shape,
                    )
                    results.append(detail)
                except Exception as e:
                    # Log error but continue with other loads
                    print(f"Warning: Failed to calculate {name}: {e}")

        return results

    def get_available_categories(self) -> List[str]:
        """Get list of available load categories."""
        return [cat.value for cat in LoadCategory]


@dataclass
class WholeBuildingAggregator:
    """
    Creates complete whole-building energy from simulation + site loads.

    This is the main entry point for whole-building energy analysis.
    It combines:
    - Modeled energy from simulation (CBECC, future EnergyPlus)
    - Calculated site loads
    - Into a unified WholeBuildingEnergy object

    Example:
        >>> aggregator = WholeBuildingAggregator()
        >>> wbe = aggregator.create_from_simulation(
        ...     simulation_file="project - HourlyResults.csv",
        ...     site_loads_input={
        ...         "elevator": [{"num_elevators": 2}],
        ...         "interior_lighting": [{"area_sf": 5000, "space_type": "corridor"}],
        ...     }
        ... )
    """

    site_load_aggregator: SiteLoadAggregator = field(default_factory=SiteLoadAggregator)
    report_mode: ReportMode = ReportMode.FULL
    diversity_factor: float = 0.9

    def create_from_simulation(
        self,
        simulation_file: str | Path,
        site_loads_input: Optional[Dict[str, List[Dict]]] = None,
        project_info_override: Optional[Dict] = None,
    ) -> WholeBuildingEnergy:
        """
        Create whole-building energy from simulation file and site loads.

        Args:
            simulation_file: Path to simulation output (e.g., HourlyResults.csv)
            site_loads_input: Dictionary of site load inputs by category
            project_info_override: Optional overrides for project info

        Returns:
            WholeBuildingEnergy with modeled, site loads, and combined data
        """
        # Parse simulation
        parser = get_parser_for_file(simulation_file)
        modeled_stream, project_info = parser.parse(simulation_file)

        # Apply project info overrides
        if project_info_override:
            for key, value in project_info_override.items():
                if hasattr(project_info, key):
                    setattr(project_info, key, value)

        # Calculate site loads
        site_load_details = []
        if site_loads_input:
            site_load_details = self.site_load_aggregator.calculate_all(site_loads_input)

        # Create whole-building energy
        return WholeBuildingEnergy.create(
            project=project_info,
            modeled=modeled_stream,
            site_load_details=site_load_details,
            report_mode=self.report_mode,
            diversity_factor=self.diversity_factor,
        )

    def create_from_simulation_output(
        self,
        simulation_output: "SimulationOutput",
        site_loads_input: Optional[Dict[str, List[Dict]]] = None,
    ) -> WholeBuildingEnergy:
        """
        Create whole-building energy from existing SimulationOutput.

        Useful when simulation has already been parsed.

        Args:
            simulation_output: Parsed SimulationOutput object
            site_loads_input: Dictionary of site load inputs by category

        Returns:
            WholeBuildingEnergy with modeled, site loads, and combined data
        """
        # Convert to new format
        modeled_stream = EnergyStream.from_simulation_output(simulation_output)
        project_info = ProjectInfo.from_simulation_output(simulation_output)

        # Calculate site loads
        site_load_details = []
        if site_loads_input:
            site_load_details = self.site_load_aggregator.calculate_all(site_loads_input)

        return WholeBuildingEnergy.create(
            project=project_info,
            modeled=modeled_stream,
            site_load_details=site_load_details,
            report_mode=self.report_mode,
            diversity_factor=self.diversity_factor,
        )

    def create_site_loads_only(
        self,
        project_name: str,
        site_loads_input: Dict[str, List[Dict]],
        floor_area_sf: Optional[float] = None,
    ) -> WholeBuildingEnergy:
        """
        Create whole-building energy with site loads only (no simulation).

        Useful for site load analysis when simulation isn't available.

        Args:
            project_name: Name for the project
            site_loads_input: Dictionary of site load inputs
            floor_area_sf: Optional floor area for EUI calculations

        Returns:
            WholeBuildingEnergy with empty modeled and calculated site loads
        """
        project_info = ProjectInfo(
            name=project_name,
            floor_area_sf=floor_area_sf,
        )

        # Empty modeled stream
        modeled_stream = EnergyStream.empty()

        # Calculate site loads
        site_load_details = self.site_load_aggregator.calculate_all(site_loads_input)

        return WholeBuildingEnergy.create(
            project=project_info,
            modeled=modeled_stream,
            site_load_details=site_load_details,
            report_mode=self.report_mode,
            diversity_factor=self.diversity_factor,
        )


# Convenience functions

def create_whole_building_energy(
    simulation_file: str | Path,
    site_loads_input: Optional[Dict[str, List[Dict]]] = None,
    report_mode: ReportMode = ReportMode.FULL,
) -> WholeBuildingEnergy:
    """
    Convenience function to create whole-building energy.

    Args:
        simulation_file: Path to simulation output file
        site_loads_input: Optional site load inputs
        report_mode: Reporting granularity

    Returns:
        WholeBuildingEnergy object
    """
    aggregator = WholeBuildingAggregator(report_mode=report_mode)
    return aggregator.create_from_simulation(simulation_file, site_loads_input)


def calculate_site_loads(
    site_loads_input: Dict[str, List[Dict]]
) -> List[SiteLoadDetail]:
    """
    Convenience function to calculate site loads only.

    Args:
        site_loads_input: Site load inputs by category

    Returns:
        List of SiteLoadDetail objects
    """
    aggregator = SiteLoadAggregator()
    return aggregator.calculate_all(site_loads_input)


def get_total_site_load_energy(site_loads: List[SiteLoadDetail]) -> tuple[float, float]:
    """
    Calculate total annual energy from site loads.

    Args:
        site_loads: List of calculated site loads

    Returns:
        Tuple of (total_kwh, total_therms)
    """
    # Filter out loads that are modeled in simulation
    non_modeled = [load for load in site_loads if not load.is_modeled_in_simulation]

    total_kwh = sum(load.annual_kwh for load in non_modeled)
    total_therms = sum(load.annual_therms for load in non_modeled)

    return total_kwh, total_therms
