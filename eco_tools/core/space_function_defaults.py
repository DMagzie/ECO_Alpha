"""
Title 24 2022 Space Function Defaults
Default internal loads for common nonresidential space types

Sources:
- Title 24 2022 Building Energy Efficiency Standards
- CEC-400-2022-009-CMF-REV2 Appendix 5.4A (Space Function Defaults)
- California Energy Commission Official Reference Tables

Units:
- Occupancy: people per 1000 ft² (people/1000 ft²)
- Equipment: W/ft²
- Lighting: W/ft² (used as fallback if no IntLtgSys)

Note: CBECC models use space function references like "Office Defaults",
"Warehouse Defaults", etc. This library maps those to Title 24 standard values.

Important: These are Title 24-specific values, which differ from ASHRAE 90.1-2019.
Title 24 values are generally more stringent (lower lighting power densities).
"""

from typing import Dict, Optional
from dataclasses import dataclass


@dataclass
class SpaceFunctionDefaults:
    """Default internal loads for a space function type"""
    space_function: str
    occupancy_people_per_1000_ft2: float
    equipment_power_density_w_ft2: float
    lighting_power_density_w_ft2: float  # Fallback if no IntLtgSys
    description: str = ""


# Title 24 2022 Space Function Defaults
# Based on CEC-400-2022-009-CMF-REV2 Appendix 5.4A
SPACE_FUNCTION_DEFAULTS: Dict[str, SpaceFunctionDefaults] = {

    # OFFICE SPACES
    "Office Defaults": SpaceFunctionDefaults(
        space_function="Office Defaults",
        occupancy_people_per_1000_ft2=5.0,  # Title 24 2022
        equipment_power_density_w_ft2=0.75,  # Title 24 2022
        lighting_power_density_w_ft2=0.60,  # Title 24 2022 (lower than ASHRAE 90.1)
        description="General office space"
    ),

    "Office Area (>250 square feet)": SpaceFunctionDefaults(
        space_function="Office Area (>250 square feet)",
        occupancy_people_per_1000_ft2=5.0,  # Title 24 2022
        equipment_power_density_w_ft2=0.75,  # Title 24 2022
        lighting_power_density_w_ft2=0.60,  # Title 24 2022 (lower than ASHRAE 90.1)
        description="Open plan office space"
    ),

    "Office Area (<=250 square feet)": SpaceFunctionDefaults(
        space_function="Office Area (<=250 square feet)",
        occupancy_people_per_1000_ft2=5.0,  # Title 24 2022
        equipment_power_density_w_ft2=0.75,  # Title 24 2022
        lighting_power_density_w_ft2=0.65,  # Title 24 2022 (lower than ASHRAE 90.1)
        description="Enclosed office space"
    ),

    # WAREHOUSE / STORAGE
    "Warehouse Defaults": SpaceFunctionDefaults(
        space_function="Warehouse Defaults",
        occupancy_people_per_1000_ft2=0.0,  # Title 24 2022 - warehouses typically unoccupied
        equipment_power_density_w_ft2=0.00,  # Title 24 2022
        lighting_power_density_w_ft2=0.40,  # Title 24 2022 (lower than ASHRAE 90.1)
        description="General warehouse/storage"
    ),

    "Storage, Commercial/Industrial (Warehouse)": SpaceFunctionDefaults(
        space_function="Storage, Commercial/Industrial (Warehouse)",
        occupancy_people_per_1000_ft2=0.0,  # Title 24 2022
        equipment_power_density_w_ft2=0.00,  # Title 24 2022
        lighting_power_density_w_ft2=0.40,  # Title 24 2022 (lower than ASHRAE 90.1)
        description="Commercial/industrial warehouse"
    ),

    "Storage": SpaceFunctionDefaults(
        space_function="Storage",
        occupancy_people_per_1000_ft2=0.0,  # Title 24 2022 - unoccupied
        equipment_power_density_w_ft2=0.00,  # Title 24 2022
        lighting_power_density_w_ft2=0.45,  # Title 24 2022
        description="Storage room"
    ),

    # CONFERENCE / MEETING
    "Conference, Multipurpose and Meeting Area": SpaceFunctionDefaults(
        space_function="Conference, Multipurpose and Meeting Area",
        occupancy_people_per_1000_ft2=50.0,  # Title 24 2022 (same as ASHRAE)
        equipment_power_density_w_ft2=1.00,  # Title 24 2022 (higher - AV equipment)
        lighting_power_density_w_ft2=0.75,  # Title 24 2022 (lower than ASHRAE 90.1)
        description="Conference and meeting rooms"
    ),

    # CORRIDORS / CIRCULATION
    "Corridor Area": SpaceFunctionDefaults(
        space_function="Corridor Area",
        occupancy_people_per_1000_ft2=0.0,  # Title 24 2022 - transient occupancy
        equipment_power_density_w_ft2=0.0,  # Title 24 2022
        lighting_power_density_w_ft2=0.40,  # Title 24 2022 (nearly same as ASHRAE)
        description="Corridor and hallway"
    ),

    # LOBBIES / ENTRIES
    "Lobby, Main Entry": SpaceFunctionDefaults(
        space_function="Lobby, Main Entry",
        occupancy_people_per_1000_ft2=0.0,  # Title 24 2022 - transient (no design occupancy)
        equipment_power_density_w_ft2=0.00,  # Title 24 2022
        lighting_power_density_w_ft2=0.70,  # Title 24 2022 (lower than ASHRAE 90.1)
        description="Main entry lobby"
    ),

    # BREAKROOMS / LOUNGES
    "Lounge, Breakroom, or Waiting Area": SpaceFunctionDefaults(
        space_function="Lounge, Breakroom, or Waiting Area",
        occupancy_people_per_1000_ft2=0.0,  # Title 24 2022 (no design occupancy specified)
        equipment_power_density_w_ft2=0.50,  # Title 24 2022 (refrigerators, microwaves)
        lighting_power_density_w_ft2=0.55,  # Title 24 2022 (lower than ASHRAE 90.1)
        description="Breakroom, lounge, waiting area"
    ),

    # MECHANICAL / ELECTRICAL
    "Electrical, Mechanical, Telephone Rooms": SpaceFunctionDefaults(
        space_function="Electrical, Mechanical, Telephone Rooms",
        occupancy_people_per_1000_ft2=0.0,  # Title 24 2022 - unoccupied
        equipment_power_density_w_ft2=0.00,  # Title 24 2022 (HVAC equipment not plug loads)
        lighting_power_density_w_ft2=0.40,  # Title 24 2022 (much lower than ASHRAE 90.1)
        description="Electrical and mechanical rooms"
    ),

    # STAIRWELLS
    "Stairwell": SpaceFunctionDefaults(
        space_function="Stairwell",
        occupancy_people_per_1000_ft2=0.0,  # Title 24 2022 - transient
        equipment_power_density_w_ft2=0.0,  # Title 24 2022
        lighting_power_density_w_ft2=0.60,  # Title 24 2022 (lower than ASHRAE 90.1)
        description="Stairwell"
    ),

    # FITNESS / EXERCISE
    "Exercise/Fitness Center and Gymnasium Areas": SpaceFunctionDefaults(
        space_function="Exercise/Fitness Center and Gymnasium Areas",
        occupancy_people_per_1000_ft2=20.0,  # Title 24 2022 (higher than ASHRAE)
        equipment_power_density_w_ft2=0.25,  # Title 24 2022 (exercise equipment)
        lighting_power_density_w_ft2=0.50,  # Title 24 2022 (lower than ASHRAE 90.1)
        description="Fitness center and gymnasium"
    ),

    # UNOCCUPIED
    "Unoccupied-Include in Gross Floor Area": SpaceFunctionDefaults(
        space_function="Unoccupied-Include in Gross Floor Area",
        occupancy_people_per_1000_ft2=0.0,  # Title 24 2022
        equipment_power_density_w_ft2=0.0,  # Title 24 2022
        lighting_power_density_w_ft2=0.40,  # Title 24 2022 (higher than before)
        description="Unoccupied space"
    ),

    # GENERAL / FALLBACK
    "All other": SpaceFunctionDefaults(
        space_function="All other",
        occupancy_people_per_1000_ft2=5.0,  # Conservative default
        equipment_power_density_w_ft2=0.50,  # Conservative default
        lighting_power_density_w_ft2=0.60,  # Title 24 2022 conservative default
        description="General building area (fallback)"
    ),
}


def get_space_function_defaults(space_function: str) -> Optional[SpaceFunctionDefaults]:
    """
    Get default internal loads for a space function

    Args:
        space_function: Space function string from CBECC (e.g., "Office Defaults")

    Returns:
        SpaceFunctionDefaults object or None if not found
    """
    return SPACE_FUNCTION_DEFAULTS.get(space_function)


def get_occupancy_density_si(space_function: str) -> Optional[float]:
    """
    Get occupancy density in people/m²

    Args:
        space_function: Space function string

    Returns:
        Occupancy density in people/m² or None
    """
    defaults = get_space_function_defaults(space_function)
    if defaults:
        # Convert people/1000 ft² to people/m²
        # 1000 ft² = 92.903 m²
        return defaults.occupancy_people_per_1000_ft2 / 92.903
    return None


def get_equipment_density_si(space_function: str) -> Optional[float]:
    """
    Get equipment power density in W/m²

    Args:
        space_function: Space function string

    Returns:
        Equipment power density in W/m² or None
    """
    defaults = get_space_function_defaults(space_function)
    if defaults:
        # Convert W/ft² to W/m²
        # 1 W/ft² = 10.764 W/m²
        return defaults.equipment_power_density_w_ft2 * 10.764
    return None


def get_lighting_density_si(space_function: str) -> Optional[float]:
    """
    Get lighting power density in W/m² (fallback if no IntLtgSys)

    Args:
        space_function: Space function string

    Returns:
        Lighting power density in W/m² or None
    """
    defaults = get_space_function_defaults(space_function)
    if defaults:
        # Convert W/ft² to W/m²
        return defaults.lighting_power_density_w_ft2 * 10.764
    return None


def list_all_space_functions() -> list:
    """Return list of all defined space functions"""
    return sorted(SPACE_FUNCTION_DEFAULTS.keys())


def get_defaults_summary() -> str:
    """Get a formatted summary of all space function defaults"""
    output = []
    output.append("=" * 80)
    output.append("SPACE FUNCTION DEFAULTS LIBRARY")
    output.append("=" * 80)
    output.append("")
    output.append(f"Total space functions defined: {len(SPACE_FUNCTION_DEFAULTS)}")
    output.append("")

    for func_name in sorted(SPACE_FUNCTION_DEFAULTS.keys()):
        defaults = SPACE_FUNCTION_DEFAULTS[func_name]
        output.append(f"\n{func_name}")
        output.append(f"  Description: {defaults.description}")
        output.append(f"  Occupancy: {defaults.occupancy_people_per_1000_ft2:.1f} people/1000 ft² "
                     f"({defaults.occupancy_people_per_1000_ft2/92.903:.4f} people/m²)")
        output.append(f"  Equipment: {defaults.equipment_power_density_w_ft2:.2f} W/ft² "
                     f"({defaults.equipment_power_density_w_ft2*10.764:.2f} W/m²)")
        output.append(f"  Lighting: {defaults.lighting_power_density_w_ft2:.2f} W/ft² "
                     f"({defaults.lighting_power_density_w_ft2*10.764:.2f} W/m²)")

    return "\n".join(output)


if __name__ == "__main__":
    # Print summary when run directly
    print(get_defaults_summary())
