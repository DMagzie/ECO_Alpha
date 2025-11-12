"""
Autosizing Module for HVAC and DHW Systems

Implements simplified sizing calculations based on:
- California Title 24 standards
- ASHRAE guidelines
- Industry rules of thumb
- Climate zone adjustments

This provides CBECC-like autosizing without requiring simulation first.
"""

from typing import Dict, Any, List, Optional, Tuple
import math


class AutoSizer:
    """Automatic equipment sizing based on building geometry and parameters."""

    # HVAC Sizing Factors (BTU/h per sq ft of conditioned floor area)
    # Based on California climate zones and building types
    HVAC_COOLING_FACTORS = {
        "climate_zone": {
            # Hot climates (CZ 1-2, 8-16)
            "hot": {
                "multifamily_residential": 30,  # BTU/h/sqft
                "commercial_office": 35,
                "warehouse_industrial": 20,
            },
            # Moderate climates (CZ 3-4, 6-7)
            "moderate": {
                "multifamily_residential": 25,
                "commercial_office": 30,
                "warehouse_industrial": 18,
            },
            # Cool/Cold climates (CZ 5, 16)
            "cool": {
                "multifamily_residential": 20,
                "commercial_office": 25,
                "warehouse_industrial": 15,
            }
        }
    }

    HVAC_HEATING_FACTORS = {
        "climate_zone": {
            # Hot climates (minimal heating)
            "hot": {
                "multifamily_residential": 25,
                "commercial_office": 30,
                "warehouse_industrial": 20,
            },
            # Moderate climates
            "moderate": {
                "multifamily_residential": 35,
                "commercial_office": 40,
                "warehouse_industrial": 25,
            },
            # Cool/Cold climates (maximum heating)
            "cool": {
                "multifamily_residential": 45,
                "commercial_office": 50,
                "warehouse_industrial": 30,
            }
        }
    }

    # DHW Sizing Factors
    DHW_SIZING = {
        "multifamily": {
            "gallons_per_unit": {
                "studio": 30,
                "1_bedroom": 40,
                "2_bedroom": 50,
                "3_bedroom": 60,
                "4_bedroom": 70,
            },
            "recovery_capacity_btu": {
                "studio": 3000,
                "1_bedroom": 4000,
                "2_bedroom": 5000,
                "3_bedroom": 6000,
                "4_bedroom": 7000,
            },
            "peak_factor": 0.7,  # 70% of units during morning peak
        },
        "commercial_office": {
            "gallons_per_employee": 2,
            "gallons_per_1000_sqft": 5,  # Alternate method
            "peak_factor": 0.3,  # 30% simultaneous use
            "recovery_capacity_btu_per_gal": 4000,
        },
        "warehouse": {
            "gallons_per_employee": 1,
            "gallons_per_1000_sqft": 2,
            "peak_factor": 0.25,
            "recovery_capacity_btu_per_gal": 3000,
        }
    }

    # California Climate Zone Classification
    CLIMATE_ZONE_MAP = {
        "1": "hot", "2": "hot",
        "3": "moderate", "4": "moderate",
        "5": "cool",
        "6": "moderate", "7": "moderate",
        "8": "hot", "9": "hot", "10": "hot",
        "11": "hot", "12": "hot", "13": "hot",
        "14": "hot", "15": "hot",
        "16": "cool"
    }

    @classmethod
    def classify_climate(cls, climate_zone: str) -> str:
        """
        Classify California climate zone as hot, moderate, or cool.

        Args:
            climate_zone: CA climate zone (1-16)

        Returns:
            "hot", "moderate", or "cool"
        """
        # Extract numeric zone
        zone_num = "".join(filter(str.isdigit, str(climate_zone)))
        return cls.CLIMATE_ZONE_MAP.get(zone_num, "moderate")

    @classmethod
    def calculate_hvac_capacity(
        cls,
        floor_area_sqft: float,
        building_type: str,
        climate_zone: str = "moderate",
        ceiling_height_ft: float = 9.0,
        occupancy: Optional[int] = None,
        internal_loads_w_sqft: float = 1.0
    ) -> Dict[str, float]:
        """
        Calculate HVAC cooling and heating capacities.

        Args:
            floor_area_sqft: Conditioned floor area in sq ft
            building_type: "multifamily_residential", "commercial_office", "warehouse_industrial"
            climate_zone: CA climate zone (1-16) or classification (hot/moderate/cool)
            ceiling_height_ft: Average ceiling height for volume calculations
            occupancy: Number of occupants (optional, for internal load adjustment)
            internal_loads_w_sqft: Internal loads in W/sq ft (lighting, equipment, people)

        Returns:
            Dict with cooling_capacity_btu, heating_capacity_btu, cooling_capacity_kw, heating_capacity_kw, airflow_cfm
        """
        # Classify climate if numeric zone provided
        if climate_zone.isdigit():
            climate = cls.classify_climate(climate_zone)
        else:
            climate = climate_zone

        # Get sizing factors
        cooling_factor = cls.HVAC_COOLING_FACTORS["climate_zone"][climate].get(building_type, 25)
        heating_factor = cls.HVAC_HEATING_FACTORS["climate_zone"][climate].get(building_type, 35)

        # Base capacity calculations
        cooling_capacity_btu = floor_area_sqft * cooling_factor
        heating_capacity_btu = floor_area_sqft * heating_factor

        # Adjust for internal loads (W/sqft → BTU/h/sqft: multiply by 3.412)
        internal_load_btu_sqft = internal_loads_w_sqft * 3.412
        cooling_capacity_btu += floor_area_sqft * internal_load_btu_sqft * 0.5  # 50% of internal loads

        # Adjust for occupancy if provided (100 BTU/h per person for sensible + latent)
        if occupancy:
            cooling_capacity_btu += occupancy * 300  # Person sensible + latent load
            heating_capacity_btu += occupancy * 100  # Person sensible heating offset

        # Volume ventilation load (if high ceilings)
        if ceiling_height_ft > 10:
            volume_factor = ceiling_height_ft / 9.0
            cooling_capacity_btu *= (1 + (volume_factor - 1) * 0.3)  # 30% volume adjustment
            heating_capacity_btu *= (1 + (volume_factor - 1) * 0.3)

        # Safety factor: 10-15% oversizing for design conditions
        safety_factor = 1.1
        cooling_capacity_btu *= safety_factor
        heating_capacity_btu *= safety_factor

        # Round to nearest 1000 BTU
        cooling_capacity_btu = round(cooling_capacity_btu / 1000) * 1000
        heating_capacity_btu = round(heating_capacity_btu / 1000) * 1000

        # Convert to kW (1 BTU/h = 0.000293071 kW)
        cooling_capacity_kw = cooling_capacity_btu * 0.000293071
        heating_capacity_kw = heating_capacity_btu * 0.000293071

        # Calculate airflow (CFM)
        # Rule of thumb: 400 CFM per ton of cooling (1 ton = 12000 BTU/h)
        cooling_tons = cooling_capacity_btu / 12000
        airflow_cfm = cooling_tons * 400

        return {
            "cooling_capacity_btu": cooling_capacity_btu,
            "heating_capacity_btu": heating_capacity_btu,
            "cooling_capacity_kw": round(cooling_capacity_kw, 2),
            "heating_capacity_kw": round(heating_capacity_kw, 2),
            "cooling_tons": round(cooling_tons, 1),
            "airflow_cfm": round(airflow_cfm, 0),
            "sizing_method": "simplified_load_calculation",
            "climate_classification": climate,
            "cooling_factor_btu_sqft": cooling_factor,
            "heating_factor_btu_sqft": heating_factor,
        }

    @classmethod
    def calculate_dhw_capacity(
        cls,
        building_type: str,
        num_units: Optional[int] = None,
        num_bedrooms_per_unit: Optional[int] = None,
        num_employees: Optional[int] = None,
        floor_area_sqft: Optional[float] = None,
    ) -> Dict[str, float]:
        """
        Calculate DHW system capacity.

        Args:
            building_type: "multifamily", "commercial_office", "warehouse"
            num_units: Number of dwelling units (for multifamily)
            num_bedrooms_per_unit: Average bedrooms per unit (for multifamily)
            num_employees: Number of employees (for commercial/warehouse)
            floor_area_sqft: Floor area (alternate sizing method)

        Returns:
            Dict with tank_capacity_gallons, tank_capacity_liters, input_rating_btu, recovery_rate_gph
        """
        sizing = cls.DHW_SIZING.get(building_type, {})

        if building_type == "multifamily":
            if num_units and num_bedrooms_per_unit:
                # Size by unit count and bedroom count
                bedroom_key = f"{num_bedrooms_per_unit}_bedroom"
                if num_bedrooms_per_unit == 0:
                    bedroom_key = "studio"
                elif num_bedrooms_per_unit >= 4:
                    bedroom_key = "4_bedroom"

                gal_per_unit = sizing["gallons_per_unit"].get(bedroom_key, 50)
                recovery_btu_per_unit = sizing["recovery_capacity_btu"].get(bedroom_key, 5000)

                # Total capacity for peak demand (70% of units)
                peak_units = num_units * sizing["peak_factor"]
                tank_capacity_gal = peak_units * gal_per_unit
                input_rating_btu = peak_units * recovery_btu_per_unit

            elif floor_area_sqft:
                # Fallback: size by floor area
                # Assume 800 sqft per unit average
                estimated_units = floor_area_sqft / 800
                tank_capacity_gal = estimated_units * 50  # 50 gal per unit
                input_rating_btu = estimated_units * 5000  # 5000 BTU/h per unit

            else:
                # Minimum sizing
                tank_capacity_gal = 200
                input_rating_btu = 100000

        elif building_type in ["commercial_office", "warehouse"]:
            if num_employees:
                # Size by employee count
                gal_per_employee = sizing.get("gallons_per_employee", 2)
                peak_factor = sizing.get("peak_factor", 0.3)
                recovery_btu_per_gal = sizing.get("recovery_capacity_btu_per_gal", 4000)

                peak_employees = num_employees * peak_factor
                tank_capacity_gal = peak_employees * gal_per_employee
                input_rating_btu = tank_capacity_gal * recovery_btu_per_gal

            elif floor_area_sqft:
                # Size by floor area
                gal_per_1000_sqft = sizing.get("gallons_per_1000_sqft", 5)
                tank_capacity_gal = (floor_area_sqft / 1000) * gal_per_1000_sqft
                input_rating_btu = tank_capacity_gal * 4000

            else:
                # Minimum sizing
                tank_capacity_gal = 80
                input_rating_btu = 75000

        else:
            # Unknown building type fallback
            tank_capacity_gal = 150
            input_rating_btu = 100000

        # Minimum standards
        tank_capacity_gal = max(tank_capacity_gal, 40)
        input_rating_btu = max(input_rating_btu, 40000)

        # Round to standard tank sizes (40, 50, 80, 100, 119, 150, 200, 300, 500 gallons)
        standard_sizes = [40, 50, 80, 100, 119, 150, 200, 300, 500, 1000]
        tank_capacity_gal = min(standard_sizes, key=lambda x: abs(x - tank_capacity_gal) if x >= tank_capacity_gal else float('inf'))

        # Convert to liters
        tank_capacity_liters = tank_capacity_gal * 3.78541

        # Calculate recovery rate (gallons per hour at 90°F rise)
        # Recovery = (Input BTU * Efficiency) / (8.33 lb/gal * 90°F rise * 1 BTU/lb/°F)
        # Assume 0.8 efficiency for gas, 0.95 for electric
        efficiency = 0.8
        recovery_rate_gph = (input_rating_btu * efficiency) / (8.33 * 90)

        return {
            "tank_capacity_gallons": round(tank_capacity_gal, 0),
            "tank_capacity_liters": round(tank_capacity_liters, 1),
            "input_rating_btu": round(input_rating_btu, 0),
            "recovery_rate_gph": round(recovery_rate_gph, 1),
            "sizing_method": "simplified_capacity_calculation",
            "building_type": building_type,
        }

    @classmethod
    def size_from_zones(
        cls,
        zones: List[Dict[str, Any]],
        building_type: str,
        climate_zone: str = "moderate",
        system_per_zone: bool = False,
    ) -> Dict[str, Any]:
        """
        Size HVAC system(s) from zone geometry.

        Args:
            zones: List of zone objects with floor_area_sqft or geometry
            building_type: Building type classification
            climate_zone: CA climate zone
            system_per_zone: If True, size one system per zone; if False, size one system for all zones

        Returns:
            Dict with system_capacities (list) and total_capacity
        """
        if not zones:
            return {"error": "No zones provided"}

        # Calculate total floor area
        total_floor_area = 0
        zone_areas = []

        for zone in zones:
            # Try to get floor area from zone
            if "floor_area_sqft" in zone:
                area = zone["floor_area_sqft"]
            elif "floor_area_sf" in zone:
                area = zone["floor_area_sf"]
            elif "area" in zone:
                area = zone["area"]
            else:
                # Try to calculate from geometry
                area = cls._calculate_zone_floor_area(zone)

            zone_areas.append({"zone_id": zone.get("id", "unknown"), "area": area})
            total_floor_area += area

        if total_floor_area == 0:
            return {"error": "No floor area found in zones"}

        if system_per_zone:
            # Size individual systems for each zone
            system_capacities = []
            for i, zone_info in enumerate(zone_areas):
                capacity = cls.calculate_hvac_capacity(
                    floor_area_sqft=zone_info["area"],
                    building_type=building_type,
                    climate_zone=climate_zone,
                )
                capacity["zone_id"] = zone_info["zone_id"]
                capacity["zone_number"] = i + 1
                system_capacities.append(capacity)

            return {
                "system_per_zone": True,
                "num_systems": len(system_capacities),
                "system_capacities": system_capacities,
                "total_floor_area_sqft": total_floor_area,
            }

        else:
            # Size one central system for all zones
            capacity = cls.calculate_hvac_capacity(
                floor_area_sqft=total_floor_area,
                building_type=building_type,
                climate_zone=climate_zone,
            )

            return {
                "system_per_zone": False,
                "num_systems": 1,
                "system_capacities": [capacity],
                "total_floor_area_sqft": total_floor_area,
                "num_zones_served": len(zones),
            }

    @classmethod
    def _calculate_zone_floor_area(cls, zone: Dict[str, Any]) -> float:
        """
        Calculate floor area from zone geometry if not directly specified.

        Args:
            zone: Zone object with potential geometry data

        Returns:
            Floor area in sq ft
        """
        # Try various geometry representations
        if "volume" in zone and "ceiling_height" in zone:
            return zone["volume"] / zone["ceiling_height"]

        if "geometry" in zone:
            geom = zone["geometry"]
            if "floor_area" in geom:
                return geom["floor_area"]

        # Default fallback
        return 1000.0  # Assume 1000 sqft if no geometry found


# Convenience functions for wizard integration

def autosize_hvac_for_model(
    model: Dict[str, Any],
    building_type: str,
    climate_zone: str = "moderate",
    system_per_zone: bool = False,
) -> Dict[str, Any]:
    """
    Autosize HVAC system(s) for an entire model.

    Args:
        model: EMJSON model dict
        building_type: Building type classification
        climate_zone: CA climate zone
        system_per_zone: Create one system per zone or one central system

    Returns:
        Sizing results with system capacities
    """
    # Extract zones from model
    zones = model.get("zones", [])
    if not zones:
        zones = model.get("building", {}).get("zones", [])

    if not zones:
        return {"error": "No zones found in model"}

    return AutoSizer.size_from_zones(
        zones=zones,
        building_type=building_type,
        climate_zone=climate_zone,
        system_per_zone=system_per_zone,
    )


def autosize_dhw_for_model(
    model: Dict[str, Any],
    building_type: str,
) -> Dict[str, Any]:
    """
    Autosize DHW system for an entire model.

    Args:
        model: EMJSON model dict
        building_type: "multifamily", "commercial_office", "warehouse"

    Returns:
        DHW sizing results
    """
    # Try to extract building parameters from model
    zones = model.get("zones", [])
    if not zones:
        zones = model.get("building", {}).get("zones", [])

    # Calculate total floor area
    total_floor_area = sum(
        zone.get("floor_area_sqft", zone.get("floor_area_sf", zone.get("area", 0)))
        for zone in zones
    )

    # Try to count units for multifamily
    num_units = len([z for z in zones if "dwelling" in z.get("type", "").lower()])

    # Estimate employees for commercial (1 per 200 sqft)
    num_employees = int(total_floor_area / 200) if total_floor_area > 0 else None

    return AutoSizer.calculate_dhw_capacity(
        building_type=building_type,
        num_units=num_units if num_units > 0 else None,
        num_employees=num_employees,
        floor_area_sqft=total_floor_area if total_floor_area > 0 else None,
    )
