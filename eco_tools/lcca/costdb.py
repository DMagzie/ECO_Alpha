"""
Cost Database for LCCA.

Provides:
- System cost data structures and lookups
- HVAC equipment costs by type and capacity
- Material costs
- Regional labor adjustments
- Cost escalation factors
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from enum import Enum
from pathlib import Path
import json


class SystemType(Enum):
    """HVAC and building system types."""
    # Cooling systems
    CHILLER_AIR_COOLED = "chiller_air_cooled"
    CHILLER_WATER_COOLED = "chiller_water_cooled"
    DX_SPLIT = "dx_split"
    DX_PACKAGED = "dx_packaged"
    VRF = "vrf"
    PTAC = "ptac"
    PTHP = "pthp"

    # Heating systems
    BOILER_GAS = "boiler_gas"
    BOILER_ELECTRIC = "boiler_electric"
    FURNACE_GAS = "furnace_gas"
    HEAT_PUMP_AIR = "heat_pump_air"
    HEAT_PUMP_WATER = "heat_pump_water"

    # Distribution
    FAN_COIL = "fan_coil"
    VAV_BOX = "vav_box"
    DUCTWORK = "ductwork"
    PIPING = "piping"

    # DHW
    WATER_HEATER_GAS = "water_heater_gas"
    WATER_HEATER_ELECTRIC = "water_heater_electric"
    WATER_HEATER_HEAT_PUMP = "water_heater_heat_pump"
    SOLAR_THERMAL = "solar_thermal"

    # Renewables
    PV_ROOFTOP = "pv_rooftop"
    PV_CARPORT = "pv_carport"
    PV_GROUND = "pv_ground"
    BATTERY_STORAGE = "battery_storage"

    # Controls
    BMS = "bms"
    THERMOSTAT_PROGRAMMABLE = "thermostat_programmable"
    THERMOSTAT_SMART = "thermostat_smart"


@dataclass
class SystemCost:
    """Cost data for a building system."""
    system_type: str
    description: str

    # Base cost (equipment only)
    base_cost: float = 0.0
    cost_unit: str = "each"  # each, per_ton, per_kw, per_sf, etc.

    # Capacity scaling
    min_capacity: float = 0.0
    max_capacity: float = 999999.0
    capacity_unit: str = "tons"

    # Installation
    labor_hours: float = 0.0
    labor_rate: float = 85.0  # $/hour
    installation_factor: float = 1.0  # Multiplier for base cost

    # Additional costs
    materials_pct: float = 0.0  # % of base for additional materials
    overhead_pct: float = 0.10  # Overhead %
    profit_pct: float = 0.10  # Profit margin %

    # Data source
    source: str = ""
    year: int = 2024

    def calculate_installed_cost(
        self,
        capacity: float = 1.0,
        regional_factor: float = 1.0
    ) -> float:
        """
        Calculate total installed cost including labor and markups.

        Args:
            capacity: System capacity in capacity_unit
            regional_factor: Regional cost adjustment

        Returns:
            Total installed cost
        """
        # Base equipment cost
        if self.cost_unit == "each":
            equipment = self.base_cost
        else:
            equipment = self.base_cost * capacity

        # Labor cost
        labor = self.labor_hours * self.labor_rate

        # Materials
        materials = equipment * self.materials_pct

        # Subtotal
        subtotal = (equipment + labor + materials) * self.installation_factor

        # Apply regional factor
        subtotal *= regional_factor

        # Apply markups
        subtotal *= (1 + self.overhead_pct)
        subtotal *= (1 + self.profit_pct)

        return subtotal


@dataclass
class MaterialCost:
    """Cost data for building materials."""
    name: str
    description: str
    cost_per_unit: float
    unit: str  # sf, lf, cy, etc.
    labor_hours_per_unit: float = 0.0
    labor_rate: float = 65.0
    source: str = ""
    year: int = 2024

    def calculate_cost(
        self,
        quantity: float,
        regional_factor: float = 1.0
    ) -> float:
        """Calculate total material + labor cost."""
        material = self.cost_per_unit * quantity
        labor = self.labor_hours_per_unit * self.labor_rate * quantity
        return (material + labor) * regional_factor


@dataclass
class RegionalFactor:
    """Regional cost adjustment factors."""
    region: str
    state: str
    city: str = ""
    labor_factor: float = 1.0
    material_factor: float = 1.0
    combined_factor: float = 1.0


@dataclass
class EscalationRate:
    """Cost escalation rates by year and category."""
    year: int
    general: float = 0.03  # General construction
    mechanical: float = 0.035  # HVAC
    electrical: float = 0.03  # Electrical
    labor: float = 0.025  # Labor only


@dataclass
class CostDatabase:
    """
    Complete cost database for LCCA calculations.
    """
    name: str = "Default CostDB"
    version: str = "1.0"
    base_year: int = 2024

    # Cost data
    system_costs: Dict[str, SystemCost] = field(default_factory=dict)
    material_costs: Dict[str, MaterialCost] = field(default_factory=dict)
    regional_factors: Dict[str, RegionalFactor] = field(default_factory=dict)
    escalation_rates: Dict[int, EscalationRate] = field(default_factory=dict)

    def get_system_cost(
        self,
        system_type: str,
        capacity: float = 1.0,
        region: str = "national"
    ) -> Optional[float]:
        """
        Look up system cost by type.

        Args:
            system_type: System type identifier
            capacity: System capacity
            region: Region for adjustment

        Returns:
            Installed cost or None if not found
        """
        cost_data = self.system_costs.get(system_type)
        if not cost_data:
            return None

        regional = self.regional_factors.get(region)
        factor = regional.combined_factor if regional else 1.0

        return cost_data.calculate_installed_cost(capacity, factor)

    def get_material_cost(
        self,
        material: str,
        quantity: float,
        region: str = "national"
    ) -> Optional[float]:
        """Look up material cost."""
        cost_data = self.material_costs.get(material)
        if not cost_data:
            return None

        regional = self.regional_factors.get(region)
        factor = regional.combined_factor if regional else 1.0

        return cost_data.calculate_cost(quantity, factor)

    def escalate_cost(
        self,
        base_cost: float,
        from_year: int,
        to_year: int,
        category: str = "general"
    ) -> float:
        """
        Escalate cost from one year to another.

        Args:
            base_cost: Original cost
            from_year: Base year
            to_year: Target year
            category: Cost category (general, mechanical, electrical, labor)

        Returns:
            Escalated cost
        """
        if from_year == to_year:
            return base_cost

        cost = base_cost
        step = 1 if to_year > from_year else -1

        for year in range(from_year, to_year, step):
            rate_data = self.escalation_rates.get(year)
            if rate_data:
                rate = getattr(rate_data, category, rate_data.general)
            else:
                rate = 0.03  # Default 3%

            if step > 0:
                cost *= (1 + rate)
            else:
                cost /= (1 + rate)

        return cost

    def to_dict(self) -> Dict[str, Any]:
        """Export database to dictionary."""
        return {
            "name": self.name,
            "version": self.version,
            "base_year": self.base_year,
            "system_costs": {
                k: {
                    "system_type": v.system_type,
                    "description": v.description,
                    "base_cost": v.base_cost,
                    "cost_unit": v.cost_unit,
                    "capacity_unit": v.capacity_unit,
                    "labor_hours": v.labor_hours,
                    "source": v.source,
                    "year": v.year
                }
                for k, v in self.system_costs.items()
            },
            "regional_factors": {
                k: {
                    "region": v.region,
                    "state": v.state,
                    "combined_factor": v.combined_factor
                }
                for k, v in self.regional_factors.items()
            }
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CostDatabase":
        """Create database from dictionary."""
        db = cls(
            name=data.get("name", "Imported"),
            version=data.get("version", "1.0"),
            base_year=data.get("base_year", 2024)
        )

        for k, v in data.get("system_costs", {}).items():
            db.system_costs[k] = SystemCost(**v)

        for k, v in data.get("regional_factors", {}).items():
            db.regional_factors[k] = RegionalFactor(**v)

        return db


def create_default_costdb() -> CostDatabase:
    """
    Create default cost database with typical values.

    Costs are approximate 2024 values for budgeting purposes.
    """
    db = CostDatabase(
        name="ECO Default CostDB",
        version="1.0",
        base_year=2024
    )

    # ---- HVAC System Costs ----

    # Chillers
    db.system_costs["chiller_air_cooled"] = SystemCost(
        system_type="chiller_air_cooled",
        description="Air-cooled chiller, scroll/screw",
        base_cost=800,
        cost_unit="per_ton",
        capacity_unit="tons",
        labor_hours=8,
        installation_factor=1.5,
        source="RS Means 2024"
    )

    db.system_costs["chiller_water_cooled"] = SystemCost(
        system_type="chiller_water_cooled",
        description="Water-cooled chiller, centrifugal",
        base_cost=650,
        cost_unit="per_ton",
        capacity_unit="tons",
        labor_hours=12,
        installation_factor=1.8,
        source="RS Means 2024"
    )

    # Boilers
    db.system_costs["boiler_gas"] = SystemCost(
        system_type="boiler_gas",
        description="Gas-fired hot water boiler, condensing",
        base_cost=45,
        cost_unit="per_mbh",
        capacity_unit="MBH",
        labor_hours=16,
        installation_factor=1.4,
        source="RS Means 2024"
    )

    # Packaged Units
    db.system_costs["dx_packaged"] = SystemCost(
        system_type="dx_packaged",
        description="Packaged rooftop unit with gas heat",
        base_cost=450,
        cost_unit="per_ton",
        capacity_unit="tons",
        labor_hours=6,
        installation_factor=1.3,
        source="RS Means 2024"
    )

    # VRF
    db.system_costs["vrf"] = SystemCost(
        system_type="vrf",
        description="VRF heat recovery system",
        base_cost=1200,
        cost_unit="per_ton",
        capacity_unit="tons",
        labor_hours=10,
        installation_factor=1.4,
        source="RS Means 2024"
    )

    # Heat Pumps
    db.system_costs["heat_pump_air"] = SystemCost(
        system_type="heat_pump_air",
        description="Air-source heat pump, split system",
        base_cost=600,
        cost_unit="per_ton",
        capacity_unit="tons",
        labor_hours=8,
        installation_factor=1.3,
        source="RS Means 2024"
    )

    # Terminal Units
    db.system_costs["vav_box"] = SystemCost(
        system_type="vav_box",
        description="VAV box with reheat coil",
        base_cost=1200,
        cost_unit="each",
        labor_hours=4,
        installation_factor=1.2,
        source="RS Means 2024"
    )

    db.system_costs["fan_coil"] = SystemCost(
        system_type="fan_coil",
        description="Fan coil unit, 4-pipe",
        base_cost=1500,
        cost_unit="each",
        labor_hours=6,
        installation_factor=1.2,
        source="RS Means 2024"
    )

    # DHW
    db.system_costs["water_heater_gas"] = SystemCost(
        system_type="water_heater_gas",
        description="Commercial gas water heater",
        base_cost=3500,
        cost_unit="each",
        labor_hours=8,
        installation_factor=1.3,
        source="RS Means 2024"
    )

    db.system_costs["water_heater_heat_pump"] = SystemCost(
        system_type="water_heater_heat_pump",
        description="Heat pump water heater",
        base_cost=4500,
        cost_unit="each",
        labor_hours=10,
        installation_factor=1.4,
        source="RS Means 2024"
    )

    # ---- Renewables ----

    db.system_costs["pv_rooftop"] = SystemCost(
        system_type="pv_rooftop",
        description="Rooftop PV system, commercial",
        base_cost=2.00,
        cost_unit="per_watt",
        capacity_unit="Wdc",
        labor_hours=0.05,  # per watt
        installation_factor=1.0,  # Already included
        source="NREL ATB 2024"
    )

    db.system_costs["pv_carport"] = SystemCost(
        system_type="pv_carport",
        description="Carport PV system with structure",
        base_cost=3.50,
        cost_unit="per_watt",
        capacity_unit="Wdc",
        labor_hours=0.08,
        installation_factor=1.0,
        source="NREL ATB 2024"
    )

    db.system_costs["battery_storage"] = SystemCost(
        system_type="battery_storage",
        description="Lithium-ion battery storage",
        base_cost=400,
        cost_unit="per_kwh",
        capacity_unit="kWh",
        labor_hours=0.5,
        installation_factor=1.2,
        source="NREL ATB 2024"
    )

    # ---- Controls ----

    db.system_costs["bms"] = SystemCost(
        system_type="bms",
        description="Building management system",
        base_cost=3.50,
        cost_unit="per_sf",
        capacity_unit="SF",
        labor_hours=0.01,
        installation_factor=1.3,
        source="RS Means 2024"
    )

    # ---- Regional Factors (California) ----

    db.regional_factors["national"] = RegionalFactor(
        region="national",
        state="US",
        combined_factor=1.0
    )

    db.regional_factors["los_angeles"] = RegionalFactor(
        region="los_angeles",
        state="CA",
        city="Los Angeles",
        labor_factor=1.15,
        material_factor=1.05,
        combined_factor=1.12
    )

    db.regional_factors["san_francisco"] = RegionalFactor(
        region="san_francisco",
        state="CA",
        city="San Francisco",
        labor_factor=1.25,
        material_factor=1.08,
        combined_factor=1.20
    )

    db.regional_factors["san_diego"] = RegionalFactor(
        region="san_diego",
        state="CA",
        city="San Diego",
        labor_factor=1.10,
        material_factor=1.03,
        combined_factor=1.08
    )

    db.regional_factors["sacramento"] = RegionalFactor(
        region="sacramento",
        state="CA",
        city="Sacramento",
        labor_factor=1.12,
        material_factor=1.02,
        combined_factor=1.09
    )

    # ---- Escalation Rates ----

    for year in range(2020, 2035):
        db.escalation_rates[year] = EscalationRate(
            year=year,
            general=0.03,
            mechanical=0.035,
            electrical=0.03,
            labor=0.025
        )

    return db


def load_costdb_from_json(file_path: str) -> CostDatabase:
    """Load cost database from JSON file."""
    with open(file_path, 'r') as f:
        data = json.load(f)
    return CostDatabase.from_dict(data)


def save_costdb_to_json(db: CostDatabase, file_path: str) -> None:
    """Save cost database to JSON file."""
    with open(file_path, 'w') as f:
        json.dump(db.to_dict(), f, indent=2)


def estimate_hvac_cost(
    system_type: str,
    capacity_tons: float,
    region: str = "national",
    db: Optional[CostDatabase] = None
) -> Optional[float]:
    """
    Quick HVAC system cost estimate.

    Args:
        system_type: System type (chiller_air_cooled, vrf, etc.)
        capacity_tons: Cooling capacity in tons
        region: Region for adjustment
        db: Cost database (uses default if None)

    Returns:
        Estimated installed cost
    """
    if db is None:
        db = create_default_costdb()

    return db.get_system_cost(system_type, capacity_tons, region)


def estimate_pv_cost(
    capacity_kwdc: float,
    mount_type: str = "rooftop",
    region: str = "national",
    db: Optional[CostDatabase] = None
) -> float:
    """
    Estimate PV system cost.

    Args:
        capacity_kwdc: PV capacity in kWdc
        mount_type: rooftop, carport, or ground
        region: Region for adjustment
        db: Cost database

    Returns:
        Estimated installed cost
    """
    if db is None:
        db = create_default_costdb()

    system_map = {
        "rooftop": "pv_rooftop",
        "carport": "pv_carport",
        "ground": "pv_rooftop"  # Use rooftop as default
    }

    system_type = system_map.get(mount_type, "pv_rooftop")
    capacity_watts = capacity_kwdc * 1000

    cost = db.get_system_cost(system_type, capacity_watts, region)
    return cost if cost else capacity_kwdc * 2000  # Fallback


def estimate_battery_cost(
    capacity_kwh: float,
    region: str = "national",
    db: Optional[CostDatabase] = None
) -> float:
    """
    Estimate battery storage cost.

    Args:
        capacity_kwh: Battery capacity in kWh
        region: Region for adjustment
        db: Cost database

    Returns:
        Estimated installed cost
    """
    if db is None:
        db = create_default_costdb()

    cost = db.get_system_cost("battery_storage", capacity_kwh, region)
    return cost if cost else capacity_kwh * 400  # Fallback


def format_cost_estimate(
    description: str,
    capacity: float,
    unit: str,
    cost: float,
    region: str = ""
) -> str:
    """Format a cost estimate line."""
    region_str = f" ({region})" if region else ""
    return f"  {description}: {capacity:,.0f} {unit} = ${cost:,.0f}{region_str}"
