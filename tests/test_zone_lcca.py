"""
Zone-Level LCCA Tests
=====================

Tests for zone_energy.py and zone_allocation.py modules including:
- Zone energy data models
- Zone LCCA result calculations
- Cost allocation engine
- CUAC utility allowance integration
- Dwelling unit and common area aggregation

Run with:
    pytest tests/test_zone_lcca.py -v
"""

import pytest
from typing import List


# =============================================================================
# ZONE ENERGY SUMMARY TESTS
# =============================================================================

class TestZoneEnergySummary:
    """Tests for ZoneEnergySummary data model."""

    def test_basic_construction(self):
        """Test basic ZoneEnergySummary construction."""
        from eco_tools.lcca.zone_energy import ZoneEnergySummary
        from eco_tools.lcca.cuac.models import ZoneType

        summary = ZoneEnergySummary(
            zone_name="Unit 101",
            zone_type=ZoneType.DWELLING_UNIT,
            elec_kwh=5000.0,
            gas_therm=200.0,
            area_sqft=800.0,
            num_bedrooms=2
        )

        assert summary.zone_name == "Unit 101"
        assert summary.zone_type == ZoneType.DWELLING_UNIT
        assert summary.elec_kwh == 5000.0
        assert summary.gas_therm == 200.0
        assert summary.area_sqft == 800.0
        assert summary.num_bedrooms == 2

    def test_eui_calculation(self):
        """Test EUI calculation."""
        from eco_tools.lcca.zone_energy import ZoneEnergySummary
        from eco_tools.lcca.cuac.models import ZoneType

        summary = ZoneEnergySummary(
            zone_name="Unit 101",
            zone_type=ZoneType.DWELLING_UNIT,
            elec_kwh=1000.0,  # 3412 kBtu
            gas_therm=100.0,  # 10000 kBtu
            area_sqft=1000.0,
        )

        # Total: 13412 kBtu / 1000 sqft = 13.412 kBtu/sqft
        assert abs(summary.eui_kbtu_sqft - 13.412) < 0.01
        assert abs(summary.elec_eui_kbtu_sqft - 3.412) < 0.01
        assert abs(summary.gas_eui_kbtu_sqft - 10.0) < 0.01

    def test_eui_zero_area(self):
        """Test EUI with zero area returns 0."""
        from eco_tools.lcca.zone_energy import ZoneEnergySummary
        from eco_tools.lcca.cuac.models import ZoneType

        summary = ZoneEnergySummary(
            zone_name="Zero Area",
            zone_type=ZoneType.DWELLING_UNIT,
            elec_kwh=1000.0,
            area_sqft=0.0,
        )

        assert summary.eui_kbtu_sqft == 0.0
        assert summary.elec_eui_kbtu_sqft == 0.0

    def test_total_area_with_multiplier(self):
        """Test total area includes multiplier."""
        from eco_tools.lcca.zone_energy import ZoneEnergySummary
        from eco_tools.lcca.cuac.models import ZoneType

        summary = ZoneEnergySummary(
            zone_name="Unit Type A",
            zone_type=ZoneType.DWELLING_UNIT,
            area_sqft=600.0,
            multiplier=5
        )

        assert summary.total_area == 3000.0

    def test_pv_offset_calculation(self):
        """Test PV offset percentage calculation."""
        from eco_tools.lcca.zone_energy import ZoneEnergySummary
        from eco_tools.lcca.cuac.models import ZoneType

        summary = ZoneEnergySummary(
            zone_name="Unit 101",
            zone_type=ZoneType.DWELLING_UNIT,
            elec_kwh=10000.0,
            pv_generation_kwh=4000.0,
        )

        assert summary.pv_offset_pct == 40.0
        assert summary.net_elec_kwh == 6000.0

    def test_pv_offset_max_100_percent(self):
        """Test PV offset caps at 100%."""
        from eco_tools.lcca.zone_energy import ZoneEnergySummary
        from eco_tools.lcca.cuac.models import ZoneType

        summary = ZoneEnergySummary(
            zone_name="Net Zero Unit",
            zone_type=ZoneType.DWELLING_UNIT,
            elec_kwh=5000.0,
            pv_generation_kwh=10000.0,
        )

        assert summary.pv_offset_pct == 100.0
        assert summary.net_elec_kwh == 0.0

    def test_is_dwelling_unit(self):
        """Test is_dwelling_unit property."""
        from eco_tools.lcca.zone_energy import ZoneEnergySummary
        from eco_tools.lcca.cuac.models import ZoneType

        dwelling = ZoneEnergySummary(
            zone_name="Unit 101",
            zone_type=ZoneType.DWELLING_UNIT,
        )
        common = ZoneEnergySummary(
            zone_name="Lobby",
            zone_type=ZoneType.COMMON_AREA,
        )

        assert dwelling.is_dwelling_unit is True
        assert dwelling.is_common_area is False
        assert common.is_dwelling_unit is False
        assert common.is_common_area is True

    def test_to_dict(self):
        """Test serialization to dictionary."""
        from eco_tools.lcca.zone_energy import ZoneEnergySummary
        from eco_tools.lcca.cuac.models import ZoneType

        summary = ZoneEnergySummary(
            zone_name="Unit 101",
            zone_type=ZoneType.DWELLING_UNIT,
            elec_kwh=5000.0,
            gas_therm=200.0,
            area_sqft=800.0,
        )

        d = summary.to_dict()
        assert d['zone_name'] == "Unit 101"
        assert d['zone_type'] == "dwelling_unit"
        assert d['elec_kwh'] == 5000.0
        assert 'eui_kbtu_sqft' in d


class TestZoneEnergySummaryBuilder:
    """Tests for ZoneEnergySummaryBuilder."""

    def test_from_allocation(self):
        """Test building from DwellUnitAllocation."""
        from eco_tools.lcca.zone_energy import ZoneEnergySummaryBuilder
        from eco_tools.lcca.cuac.models import DwellUnitAllocation

        allocation = DwellUnitAllocation(
            zone_name="S-1-2-BD-699",
            conditioning_type="Conditioned",
            space_function="High-Rise Residential Living Spaces",
            pv_batt_bldg_type="Highrise Multifamily",
            floor_area_sqft=699.0,
            multiplier=1,
            prescriptive_pv_kwdc=2.5,
            prescriptive_batt_kwh=5.0,
        )

        summary = ZoneEnergySummaryBuilder.from_allocation(
            allocation,
            elec_kwh=4500.0,
            gas_therm=150.0,
        )

        assert summary.zone_name == "S-1-2-BD-699"
        assert summary.area_sqft == 699.0
        assert summary.elec_kwh == 4500.0
        assert summary.gas_therm == 150.0
        assert summary.pv_allocation_kwdc == 2.5
        assert summary.battery_allocation_kwh == 5.0


# =============================================================================
# ZONE LCCA RESULT TESTS
# =============================================================================

class TestZoneLccaResult:
    """Tests for ZoneLccaResult data model."""

    def test_basic_construction(self):
        """Test basic ZoneLccaResult construction."""
        from eco_tools.lcca.zone_energy import ZoneLccaResult
        from eco_tools.lcca.cuac.models import ZoneType

        result = ZoneLccaResult(
            zone_name="Unit 101",
            zone_type=ZoneType.DWELLING_UNIT,
            annual_elec_kwh=5000.0,
            annual_gas_therm=200.0,
            gross_elec_cost=1250.0,
            gross_gas_cost=300.0,
        )

        assert result.zone_name == "Unit 101"
        assert result.gross_total_cost == 1550.0

    def test_gross_total_cost(self):
        """Test gross total cost calculation."""
        from eco_tools.lcca.zone_energy import ZoneLccaResult
        from eco_tools.lcca.cuac.models import ZoneType

        result = ZoneLccaResult(
            zone_name="Unit 101",
            zone_type=ZoneType.DWELLING_UNIT,
            gross_elec_cost=1000.0,
            gross_gas_cost=200.0,
            gross_demand_cost=50.0,
            gross_fixed_cost=120.0,
        )

        assert result.gross_total_cost == 1370.0

    def test_total_credits(self):
        """Test total credits calculation."""
        from eco_tools.lcca.zone_energy import ZoneLccaResult
        from eco_tools.lcca.cuac.models import ZoneType

        result = ZoneLccaResult(
            zone_name="Unit 101",
            zone_type=ZoneType.DWELLING_UNIT,
            pv_credit=300.0,
            battery_credit=50.0,
            nem_credit=100.0,
        )

        assert result.total_credits == 450.0

    def test_to_dict(self):
        """Test serialization to dictionary."""
        from eco_tools.lcca.zone_energy import ZoneLccaResult
        from eco_tools.lcca.cuac.models import ZoneType
        from eco_tools.lcca.res_other.models import CommonAreaCategory

        result = ZoneLccaResult(
            zone_name="Lobby",
            zone_type=ZoneType.COMMON_AREA,
            category=CommonAreaCategory.LOBBY,
            annual_elec_kwh=3000.0,
            gross_elec_cost=750.0,
        )

        d = result.to_dict()
        assert d['zone_name'] == "Lobby"
        assert d['zone_type'] == "common_area"
        assert d['category'] == "lobby"


# =============================================================================
# DWELLING UNIT SUMMARY TESTS
# =============================================================================

class TestDwellingUnitSummary:
    """Tests for DwellingUnitSummary aggregation."""

    def test_add_unit(self):
        """Test adding units to summary."""
        from eco_tools.lcca.zone_energy import DwellingUnitSummary, ZoneLccaResult
        from eco_tools.lcca.cuac.models import ZoneType

        summary = DwellingUnitSummary(num_bedrooms=2)

        # Add first unit
        result1 = ZoneLccaResult(
            zone_name="Unit 101",
            zone_type=ZoneType.DWELLING_UNIT,
            annual_elec_kwh=5000.0,
            annual_gas_therm=200.0,
            net_total_cost=1500.0,
            area_sqft=800.0,
        )
        summary.add_unit(result1)

        assert summary.unit_count == 1
        assert summary.avg_annual_cost == 1500.0
        assert summary.total_elec_kwh == 5000.0

        # Add second unit
        result2 = ZoneLccaResult(
            zone_name="Unit 102",
            zone_type=ZoneType.DWELLING_UNIT,
            annual_elec_kwh=4500.0,
            annual_gas_therm=180.0,
            net_total_cost=1400.0,
            area_sqft=750.0,
        )
        summary.add_unit(result2)

        assert summary.unit_count == 2
        assert summary.total_elec_kwh == 9500.0
        assert summary.avg_annual_cost == 1450.0
        assert summary.avg_area_sqft == 775.0


# =============================================================================
# COMMON AREA SUMMARY TESTS
# =============================================================================

class TestCommonAreaSummary:
    """Tests for CommonAreaSummary aggregation."""

    def test_add_zone(self):
        """Test adding zones to summary."""
        from eco_tools.lcca.zone_energy import CommonAreaSummary, ZoneLccaResult
        from eco_tools.lcca.cuac.models import ZoneType
        from eco_tools.lcca.res_other.models import CommonAreaCategory

        summary = CommonAreaSummary(category=CommonAreaCategory.CORRIDOR)

        result = ZoneLccaResult(
            zone_name="Corridor L1",
            zone_type=ZoneType.COMMON_AREA,
            category=CommonAreaCategory.CORRIDOR,
            annual_elec_kwh=1000.0,
            net_total_cost=250.0,
            area_sqft=500.0,
        )
        summary.add_zone(result)

        assert summary.zone_count == 1
        assert summary.total_elec_kwh == 1000.0
        assert summary.total_annual_cost == 250.0
        assert "Corridor L1" in summary.zone_names

    def test_eui_calculation(self):
        """Test EUI calculation for common area."""
        from eco_tools.lcca.zone_energy import CommonAreaSummary, ZoneLccaResult
        from eco_tools.lcca.cuac.models import ZoneType
        from eco_tools.lcca.res_other.models import CommonAreaCategory

        summary = CommonAreaSummary(category=CommonAreaCategory.LOBBY)

        result = ZoneLccaResult(
            zone_name="Lobby",
            zone_type=ZoneType.COMMON_AREA,
            category=CommonAreaCategory.LOBBY,
            annual_elec_kwh=1000.0,  # 3412 kBtu
            annual_gas_therm=0.0,
            area_sqft=1000.0,
        )
        summary.add_zone(result)

        # EUI = 3412 kBtu / 1000 sqft = 3.412
        assert abs(summary.eui_kbtu_sqft - 3.412) < 0.01


# =============================================================================
# BUILDING ZONE LCCA SUMMARY TESTS
# =============================================================================

class TestBuildingZoneLccaSummary:
    """Tests for BuildingZoneLccaSummary."""

    def test_add_dwelling_unit(self):
        """Test adding dwelling unit to summary."""
        from eco_tools.lcca.zone_energy import BuildingZoneLccaSummary, ZoneLccaResult
        from eco_tools.lcca.cuac.models import ZoneType

        summary = BuildingZoneLccaSummary(building_name="Test Building")

        result = ZoneLccaResult(
            zone_name="Unit 101",
            zone_type=ZoneType.DWELLING_UNIT,
            annual_elec_kwh=5000.0,
            net_total_cost=1500.0,
            area_sqft=800.0,
            num_bedrooms=2,
        )
        summary.add_result(result)

        assert summary.dwelling_unit_count == 1
        assert summary.common_area_count == 0
        assert 2 in summary.dwelling_summaries

    def test_add_common_area(self):
        """Test adding common area to summary."""
        from eco_tools.lcca.zone_energy import BuildingZoneLccaSummary, ZoneLccaResult
        from eco_tools.lcca.cuac.models import ZoneType
        from eco_tools.lcca.res_other.models import CommonAreaCategory

        summary = BuildingZoneLccaSummary()

        result = ZoneLccaResult(
            zone_name="Lobby",
            zone_type=ZoneType.COMMON_AREA,
            category=CommonAreaCategory.LOBBY,
            annual_elec_kwh=2000.0,
            net_total_cost=500.0,
            area_sqft=400.0,
        )
        summary.add_result(result)

        assert summary.dwelling_unit_count == 0
        assert summary.common_area_count == 1
        assert CommonAreaCategory.LOBBY in summary.common_summaries

    def test_aggregated_totals(self):
        """Test aggregated totals across zones."""
        from eco_tools.lcca.zone_energy import BuildingZoneLccaSummary, ZoneLccaResult
        from eco_tools.lcca.cuac.models import ZoneType
        from eco_tools.lcca.res_other.models import CommonAreaCategory

        summary = BuildingZoneLccaSummary()

        # Add 2 dwelling units
        for i, cost in enumerate([1500, 1400]):
            result = ZoneLccaResult(
                zone_name=f"Unit {101 + i}",
                zone_type=ZoneType.DWELLING_UNIT,
                annual_elec_kwh=5000.0,
                annual_gas_therm=200.0,
                net_total_cost=float(cost),
                area_sqft=800.0,
                num_bedrooms=2,
            )
            summary.add_result(result)

        # Add common area
        result = ZoneLccaResult(
            zone_name="Lobby",
            zone_type=ZoneType.COMMON_AREA,
            category=CommonAreaCategory.LOBBY,
            annual_elec_kwh=2000.0,
            net_total_cost=500.0,
            area_sqft=400.0,
        )
        summary.add_result(result)

        assert summary.total_annual_cost == 3400.0
        assert summary.dwelling_unit_cost == 2900.0
        assert summary.common_area_cost == 500.0
        assert summary.total_elec_kwh == 12000.0

    def test_to_dict(self):
        """Test serialization to dictionary."""
        from eco_tools.lcca.zone_energy import BuildingZoneLccaSummary, ZoneLccaResult
        from eco_tools.lcca.cuac.models import ZoneType

        summary = BuildingZoneLccaSummary(building_name="Test Building")
        result = ZoneLccaResult(
            zone_name="Unit 101",
            zone_type=ZoneType.DWELLING_UNIT,
            net_total_cost=1500.0,
            area_sqft=800.0,
            num_bedrooms=2,
        )
        summary.add_result(result)

        d = summary.to_dict()
        assert d['building_name'] == "Test Building"
        assert d['dwelling_unit_count'] == 1
        assert '2' in str(d['dwelling_summaries']) or 2 in d['dwelling_summaries']


# =============================================================================
# CUAC ALLOWANCE RESULT TESTS
# =============================================================================

class TestCuacAllowanceResult:
    """Tests for CuacAllowanceResult."""

    def test_gross_allowance_calculation(self):
        """Test gross allowance calculation."""
        from eco_tools.lcca.zone_energy import CuacAllowanceResult

        allowance = CuacAllowanceResult(
            num_bedrooms=2,
            elec_heating_allowance=15.0,
            elec_cooling_allowance=25.0,
            elec_water_heating_allowance=20.0,
            elec_lighting_allowance=15.0,
            elec_other_allowance=25.0,
            gas_heating_allowance=40.0,
            gas_water_heating_allowance=30.0,
            gas_cooking_allowance=5.0,
        )

        assert allowance.gross_elec_allowance == 100.0
        assert allowance.gross_gas_allowance == 75.0
        assert allowance.gross_total_allowance == 175.0

    def test_net_allowance_with_pv_credit(self):
        """Test net allowance with PV credit."""
        from eco_tools.lcca.zone_energy import CuacAllowanceResult

        allowance = CuacAllowanceResult(
            num_bedrooms=2,
            elec_cooling_allowance=50.0,
            elec_other_allowance=50.0,
            pv_credit_monthly=30.0,
        )

        assert allowance.gross_total_allowance == 100.0
        assert allowance.net_total_allowance == 70.0

    def test_net_allowance_minimum_zero(self):
        """Test net allowance doesn't go negative."""
        from eco_tools.lcca.zone_energy import CuacAllowanceResult

        allowance = CuacAllowanceResult(
            num_bedrooms=2,
            elec_cooling_allowance=50.0,
            pv_credit_monthly=100.0,
        )

        assert allowance.net_total_allowance == 0.0


# =============================================================================
# HELPER FUNCTION TESTS
# =============================================================================

class TestZoneEnergyHelpers:
    """Tests for zone energy helper functions."""

    def test_create_zone_energy_from_hourly(self):
        """Test creating zone energy from hourly data."""
        from eco_tools.lcca.zone_energy import create_zone_energy_from_hourly
        from eco_tools.lcca.cuac.models import ZoneType

        # Create 8760 hours of 1 kWh each
        hourly_elec = [1.0] * 8760

        summary = create_zone_energy_from_hourly(
            zone_name="Unit 101",
            zone_type=ZoneType.DWELLING_UNIT,
            hourly_elec=hourly_elec,
            area_sqft=800.0,
        )

        assert summary.elec_kwh == 8760.0
        assert summary.peak_demand_kw == 1.0
        assert summary.hourly_elec_kwh is not None
        assert len(summary.hourly_elec_kwh) == 8760

    def test_aggregate_zone_energies(self):
        """Test aggregating zone energies."""
        from eco_tools.lcca.zone_energy import (
            ZoneEnergySummary, aggregate_zone_energies
        )
        from eco_tools.lcca.cuac.models import ZoneType

        summaries = [
            ZoneEnergySummary(
                zone_name=f"Unit {i}",
                zone_type=ZoneType.DWELLING_UNIT,
                elec_kwh=1000.0,
                gas_therm=100.0,
                area_sqft=500.0,
            )
            for i in range(10)
        ]

        total_elec, total_gas, total_area = aggregate_zone_energies(summaries)

        assert total_elec == 10000.0
        assert total_gas == 1000.0
        assert total_area == 5000.0

    def test_filter_zones_by_type(self):
        """Test filtering zones by type."""
        from eco_tools.lcca.zone_energy import (
            ZoneEnergySummary, filter_zones_by_type
        )
        from eco_tools.lcca.cuac.models import ZoneType

        summaries = [
            ZoneEnergySummary(zone_name="Unit 1", zone_type=ZoneType.DWELLING_UNIT),
            ZoneEnergySummary(zone_name="Unit 2", zone_type=ZoneType.DWELLING_UNIT),
            ZoneEnergySummary(zone_name="Lobby", zone_type=ZoneType.COMMON_AREA),
        ]

        dwelling = filter_zones_by_type(summaries, ZoneType.DWELLING_UNIT)
        common = filter_zones_by_type(summaries, ZoneType.COMMON_AREA)

        assert len(dwelling) == 2
        assert len(common) == 1

    def test_group_zones_by_bedroom_count(self):
        """Test grouping zones by bedroom count."""
        from eco_tools.lcca.zone_energy import (
            ZoneEnergySummary, group_zones_by_bedroom_count
        )
        from eco_tools.lcca.cuac.models import ZoneType

        summaries = [
            ZoneEnergySummary(zone_name="1BR-A", zone_type=ZoneType.DWELLING_UNIT, num_bedrooms=1),
            ZoneEnergySummary(zone_name="1BR-B", zone_type=ZoneType.DWELLING_UNIT, num_bedrooms=1),
            ZoneEnergySummary(zone_name="2BR-A", zone_type=ZoneType.DWELLING_UNIT, num_bedrooms=2),
            ZoneEnergySummary(zone_name="Lobby", zone_type=ZoneType.COMMON_AREA),  # Should be excluded
        ]

        groups = group_zones_by_bedroom_count(summaries)

        assert 1 in groups
        assert 2 in groups
        assert len(groups[1]) == 2
        assert len(groups[2]) == 1

    def test_group_zones_by_category(self):
        """Test grouping zones by common area category."""
        from eco_tools.lcca.zone_energy import (
            ZoneEnergySummary, group_zones_by_category
        )
        from eco_tools.lcca.cuac.models import ZoneType
        from eco_tools.lcca.res_other.models import CommonAreaCategory

        summaries = [
            ZoneEnergySummary(
                zone_name="Lobby Main",
                zone_type=ZoneType.COMMON_AREA,
                category=CommonAreaCategory.LOBBY
            ),
            ZoneEnergySummary(
                zone_name="Corridor L1",
                zone_type=ZoneType.COMMON_AREA,
                category=CommonAreaCategory.CORRIDOR
            ),
            ZoneEnergySummary(
                zone_name="Corridor L2",
                zone_type=ZoneType.COMMON_AREA,
                category=CommonAreaCategory.CORRIDOR
            ),
            ZoneEnergySummary(zone_name="Unit 1", zone_type=ZoneType.DWELLING_UNIT),  # Excluded
        ]

        groups = group_zones_by_category(summaries)

        assert CommonAreaCategory.LOBBY in groups
        assert CommonAreaCategory.CORRIDOR in groups
        assert len(groups[CommonAreaCategory.LOBBY]) == 1
        assert len(groups[CommonAreaCategory.CORRIDOR]) == 2


# =============================================================================
# ZONE COST ALLOCATOR TESTS
# =============================================================================

class TestZoneCostAllocator:
    """Tests for ZoneCostAllocator."""

    def _create_sample_zones(self) -> List:
        """Create sample zones for testing."""
        from eco_tools.lcca.zone_energy import ZoneEnergySummary
        from eco_tools.lcca.cuac.models import ZoneType
        from eco_tools.lcca.res_other.models import CommonAreaCategory

        return [
            ZoneEnergySummary(
                zone_name="Unit 101",
                zone_type=ZoneType.DWELLING_UNIT,
                elec_kwh=5000.0,
                gas_therm=200.0,
                area_sqft=800.0,
                num_bedrooms=2,
            ),
            ZoneEnergySummary(
                zone_name="Unit 102",
                zone_type=ZoneType.DWELLING_UNIT,
                elec_kwh=4500.0,
                gas_therm=180.0,
                area_sqft=750.0,
                num_bedrooms=1,
            ),
            ZoneEnergySummary(
                zone_name="Lobby",
                zone_type=ZoneType.COMMON_AREA,
                category=CommonAreaCategory.LOBBY,
                elec_kwh=2000.0,
                gas_therm=0.0,
                area_sqft=400.0,
            ),
            ZoneEnergySummary(
                zone_name="Corridor",
                zone_type=ZoneType.COMMON_AREA,
                category=CommonAreaCategory.CORRIDOR,
                elec_kwh=1500.0,
                gas_therm=0.0,
                area_sqft=300.0,
            ),
        ]

    def test_basic_construction(self):
        """Test ZoneCostAllocator construction."""
        from eco_tools.lcca.zone_allocation import ZoneCostAllocator

        zones = self._create_sample_zones()
        allocator = ZoneCostAllocator(zone_summaries=zones)

        assert len(allocator.zone_summaries) == 4
        assert allocator.building_elec_kwh == 13000.0
        assert allocator.building_gas_therm == 380.0

    def test_total_area_property(self):
        """Test total area calculation."""
        from eco_tools.lcca.zone_allocation import ZoneCostAllocator

        zones = self._create_sample_zones()
        allocator = ZoneCostAllocator(zone_summaries=zones)

        assert allocator.total_area == 2250.0

    def test_dwelling_and_common_area_properties(self):
        """Test dwelling unit and common area separation."""
        from eco_tools.lcca.zone_allocation import ZoneCostAllocator

        zones = self._create_sample_zones()
        allocator = ZoneCostAllocator(zone_summaries=zones)

        assert len(allocator.dwelling_units) == 2
        assert len(allocator.common_areas) == 2
        assert allocator.dwelling_area == 1550.0
        assert allocator.common_area == 700.0

    def test_allocate_zone_simple_costs(self):
        """Test zone allocation with simple costs."""
        from eco_tools.lcca.zone_allocation import ZoneCostAllocator
        from eco_tools.lcca.zone_energy import ZoneEnergySummary
        from eco_tools.lcca.cuac.models import ZoneType

        zone = ZoneEnergySummary(
            zone_name="Unit 101",
            zone_type=ZoneType.DWELLING_UNIT,
            elec_kwh=5000.0,
            gas_therm=200.0,
            area_sqft=800.0,
        )

        allocator = ZoneCostAllocator(zone_summaries=[zone])
        result = allocator.allocate_zone(zone)

        assert result.zone_name == "Unit 101"
        assert result.annual_elec_kwh == 5000.0
        assert result.gross_elec_cost > 0
        assert result.gross_gas_cost > 0
        assert result.net_total_cost > 0

    def test_allocate_all(self):
        """Test allocating all zones."""
        from eco_tools.lcca.zone_allocation import ZoneCostAllocator

        zones = self._create_sample_zones()
        allocator = ZoneCostAllocator(zone_summaries=zones)

        summary = allocator.allocate_all()

        assert summary.dwelling_unit_count == 2
        assert summary.common_area_count == 2
        assert summary.total_annual_cost > 0
        assert 1 in summary.dwelling_summaries
        assert 2 in summary.dwelling_summaries

    def test_allocate_by_area(self):
        """Test area-based cost allocation."""
        from eco_tools.lcca.zone_allocation import ZoneCostAllocator

        zones = self._create_sample_zones()
        allocator = ZoneCostAllocator(zone_summaries=zones)

        allocations = allocator.allocate_by_area(10000.0)

        assert len(allocations) == 4
        assert sum(allocations.values()) == pytest.approx(10000.0, rel=0.01)

        # Unit 101 (800 sqft) should get more than Unit 102 (750 sqft)
        assert allocations["Unit 101"] > allocations["Unit 102"]

    def test_allocate_common_costs_to_units_by_area(self):
        """Test allocating common area costs to dwelling units by area."""
        from eco_tools.lcca.zone_allocation import ZoneCostAllocator, AllocationMethod

        zones = self._create_sample_zones()
        allocator = ZoneCostAllocator(zone_summaries=zones)

        allocations = allocator.allocate_common_costs_to_units(
            common_cost=1000.0,
            method=AllocationMethod.BY_AREA
        )

        assert len(allocations) == 2  # Only dwelling units
        assert sum(allocations.values()) == pytest.approx(1000.0, rel=0.01)

    def test_allocate_common_costs_to_units_by_count(self):
        """Test allocating common area costs equally."""
        from eco_tools.lcca.zone_allocation import ZoneCostAllocator, AllocationMethod

        zones = self._create_sample_zones()
        allocator = ZoneCostAllocator(zone_summaries=zones)

        allocations = allocator.allocate_common_costs_to_units(
            common_cost=1000.0,
            method=AllocationMethod.BY_UNIT_COUNT
        )

        assert len(allocations) == 2
        assert allocations["Unit 101"] == 500.0
        assert allocations["Unit 102"] == 500.0

    def test_allocate_by_meter_category(self):
        """Test allocation by meter category."""
        from eco_tools.lcca.zone_allocation import ZoneCostAllocator
        from eco_tools.lcca.res_other.models import CommonAreaCategory

        zones = self._create_sample_zones()
        allocator = ZoneCostAllocator(zone_summaries=zones)

        category_results = allocator.allocate_by_meter_category()

        assert CommonAreaCategory.LOBBY in category_results
        assert CommonAreaCategory.CORRIDOR in category_results
        assert category_results[CommonAreaCategory.LOBBY].annual_elec_kwh == 2000.0

    def test_allocate_dwelling_units(self):
        """Test dwelling unit allocation."""
        from eco_tools.lcca.zone_allocation import ZoneCostAllocator

        zones = self._create_sample_zones()
        allocator = ZoneCostAllocator(zone_summaries=zones)

        results = allocator.allocate_dwelling_units()

        assert len(results) == 2
        assert all(r.is_dwelling_unit for r in results)

    def test_calculate_cuac_allowances(self):
        """Test CUAC allowance calculation."""
        from eco_tools.lcca.zone_allocation import ZoneCostAllocator

        zones = self._create_sample_zones()
        allocator = ZoneCostAllocator(zone_summaries=zones)

        allowances = allocator.calculate_cuac_allowances()

        assert 1 in allowances  # 1-bedroom
        assert 2 in allowances  # 2-bedroom
        assert allowances[1].gross_total_allowance > 0
        assert allowances[2].gross_total_allowance > 0


class TestZoneCostAllocatorWithTariff:
    """Tests for ZoneCostAllocator with tariff."""

    def test_allocate_with_tariff(self):
        """Test allocation with TOU tariff."""
        from eco_tools.lcca.zone_allocation import ZoneCostAllocator
        from eco_tools.lcca.zone_energy import ZoneEnergySummary
        from eco_tools.lcca.cuac.models import ZoneType
        from eco_tools.lcca.tariffs import create_pge_e_tou_c

        zone = ZoneEnergySummary(
            zone_name="Unit 101",
            zone_type=ZoneType.DWELLING_UNIT,
            elec_kwh=5000.0,
            gas_therm=200.0,
            area_sqft=800.0,
        )

        tariff = create_pge_e_tou_c()
        allocator = ZoneCostAllocator(
            zone_summaries=[zone],
            tariff=tariff
        )

        result = allocator.allocate_zone(zone)

        assert result.gross_elec_cost > 0
        assert result.gross_gas_cost > 0
        # With tariff, gas cost should use tariff gas rate
        expected_gas_cost = 200.0 * tariff.gas_rate
        assert abs(result.gross_gas_cost - expected_gas_cost) < 0.01

    def test_allocate_with_hourly_data(self):
        """Test TOU cost calculation with hourly data."""
        from eco_tools.lcca.zone_allocation import ZoneCostAllocator
        from eco_tools.lcca.zone_energy import ZoneEnergySummary
        from eco_tools.lcca.cuac.models import ZoneType
        from eco_tools.lcca.tariffs import create_pge_e_tou_c

        # Create zone with hourly data
        hourly_elec = [1.0] * 8760  # 1 kWh per hour = 8760 kWh total
        zone = ZoneEnergySummary(
            zone_name="Unit 101",
            zone_type=ZoneType.DWELLING_UNIT,
            elec_kwh=8760.0,
            area_sqft=800.0,
            hourly_elec_kwh=hourly_elec,
        )

        tariff = create_pge_e_tou_c()
        allocator = ZoneCostAllocator(
            zone_summaries=[zone],
            tariff=tariff
        )

        result = allocator.allocate_zone(zone)

        assert result.gross_elec_cost > 0
        # TOU breakdown should have values
        total_tou = (result.summer_on_peak_cost + result.summer_mid_peak_cost +
                     result.summer_off_peak_cost + result.winter_on_peak_cost +
                     result.winter_mid_peak_cost + result.winter_off_peak_cost)
        assert total_tou > 0


class TestZoneCostAllocatorWithPV:
    """Tests for ZoneCostAllocator with PV credits."""

    def test_pv_credit_calculation(self):
        """Test PV credit calculation."""
        from eco_tools.lcca.zone_allocation import ZoneCostAllocator
        from eco_tools.lcca.zone_energy import ZoneEnergySummary
        from eco_tools.lcca.cuac.models import ZoneType
        from eco_tools.lcca.tariffs import create_pge_e_tou_c

        zone = ZoneEnergySummary(
            zone_name="Unit 101",
            zone_type=ZoneType.DWELLING_UNIT,
            elec_kwh=5000.0,
            pv_generation_kwh=3000.0,  # PV covers 60%
            area_sqft=800.0,
        )

        tariff = create_pge_e_tou_c()
        allocator = ZoneCostAllocator(
            zone_summaries=[zone],
            tariff=tariff
        )

        result = allocator.allocate_zone(zone)

        assert result.pv_credit > 0
        assert result.net_elec_cost < result.gross_elec_cost

    def test_excess_pv_nem_credit(self):
        """Test NEM credit for excess PV generation."""
        from eco_tools.lcca.zone_allocation import ZoneCostAllocator
        from eco_tools.lcca.zone_energy import ZoneEnergySummary
        from eco_tools.lcca.cuac.models import ZoneType
        from eco_tools.lcca.tariffs import create_pge_e_tou_c

        zone = ZoneEnergySummary(
            zone_name="Net Zero Unit",
            zone_type=ZoneType.DWELLING_UNIT,
            elec_kwh=5000.0,
            pv_generation_kwh=8000.0,  # More generation than consumption
            area_sqft=800.0,
        )

        tariff = create_pge_e_tou_c()
        allocator = ZoneCostAllocator(
            zone_summaries=[zone],
            tariff=tariff
        )

        result = allocator.allocate_zone(zone)

        assert result.pv_credit > 0
        assert result.nem_credit > 0  # Has NEM credit for export


# =============================================================================
# HELPER FUNCTION TESTS
# =============================================================================

class TestAllocationHelpers:
    """Tests for allocation helper functions."""

    def test_calculate_zone_lcca(self):
        """Test calculate_zone_lcca convenience function."""
        from eco_tools.lcca.zone_allocation import calculate_zone_lcca
        from eco_tools.lcca.zone_energy import ZoneEnergySummary
        from eco_tools.lcca.cuac.models import ZoneType
        from eco_tools.lcca.tariffs import create_pge_e_tou_c

        zones = [
            ZoneEnergySummary(
                zone_name="Unit 101",
                zone_type=ZoneType.DWELLING_UNIT,
                elec_kwh=5000.0,
                gas_therm=200.0,
                area_sqft=800.0,
                num_bedrooms=2,
            ),
            ZoneEnergySummary(
                zone_name="Unit 102",
                zone_type=ZoneType.DWELLING_UNIT,
                elec_kwh=4500.0,
                gas_therm=180.0,
                area_sqft=750.0,
                num_bedrooms=1,
            ),
        ]

        tariff = create_pge_e_tou_c()
        summary = calculate_zone_lcca(zones, tariff)

        assert summary.dwelling_unit_count == 2
        assert summary.total_annual_cost > 0

    def test_estimate_zone_energy_from_building(self):
        """Test estimating zone energy from building totals."""
        from eco_tools.lcca.zone_allocation import estimate_zone_energy_from_building
        from eco_tools.lcca.cuac.models import DwellUnitAllocation

        allocations = [
            DwellUnitAllocation(
                zone_name="Unit A",
                conditioning_type="Conditioned",
                space_function="High-Rise Residential Living Spaces",
                pv_batt_bldg_type="Highrise Multifamily",
                floor_area_sqft=1000.0,
            ),
            DwellUnitAllocation(
                zone_name="Unit B",
                conditioning_type="Conditioned",
                space_function="High-Rise Residential Living Spaces",
                pv_batt_bldg_type="Highrise Multifamily",
                floor_area_sqft=1000.0,
            ),
        ]

        summaries = estimate_zone_energy_from_building(
            building_elec_kwh=10000.0,
            building_gas_therm=1000.0,
            zone_allocations=allocations,
        )

        assert len(summaries) == 2
        # Equal area -> equal allocation
        assert summaries[0].elec_kwh == 5000.0
        assert summaries[1].elec_kwh == 5000.0
        assert summaries[0].gas_therm == 500.0

    def test_format_zone_lcca_summary(self):
        """Test formatting zone LCCA summary."""
        from eco_tools.lcca.zone_allocation import (
            ZoneCostAllocator, format_zone_lcca_summary
        )
        from eco_tools.lcca.zone_energy import ZoneEnergySummary
        from eco_tools.lcca.cuac.models import ZoneType

        zones = [
            ZoneEnergySummary(
                zone_name="Unit 101",
                zone_type=ZoneType.DWELLING_UNIT,
                elec_kwh=5000.0,
                gas_therm=200.0,
                area_sqft=800.0,
                num_bedrooms=2,
            ),
        ]

        allocator = ZoneCostAllocator(zone_summaries=zones)
        summary = allocator.allocate_all()
        formatted = format_zone_lcca_summary(summary)

        assert "ZONE-LEVEL LCCA SUMMARY" in formatted
        assert "Dwelling Units" in formatted
        assert "2-BR" in formatted


# =============================================================================
# INTEGRATION TESTS
# =============================================================================

class TestZoneLccaIntegration:
    """Integration tests for zone-level LCCA."""

    def test_full_building_lcca_workflow(self):
        """Test complete workflow for a small building."""
        from eco_tools.lcca.zone_allocation import ZoneCostAllocator
        from eco_tools.lcca.zone_energy import ZoneEnergySummary
        from eco_tools.lcca.cuac.models import ZoneType, CuacConfig
        from eco_tools.lcca.res_other.models import CommonAreaCategory
        from eco_tools.lcca.tariffs import create_pge_e_tou_c

        # Create a small multifamily building
        zones = [
            # 10 1-bedroom units
            ZoneEnergySummary(
                zone_name="1BR-Type",
                zone_type=ZoneType.DWELLING_UNIT,
                elec_kwh=4000.0,
                gas_therm=150.0,
                area_sqft=600.0,
                num_bedrooms=1,
                multiplier=10,
            ),
            # 5 2-bedroom units
            ZoneEnergySummary(
                zone_name="2BR-Type",
                zone_type=ZoneType.DWELLING_UNIT,
                elec_kwh=5500.0,
                gas_therm=200.0,
                area_sqft=850.0,
                num_bedrooms=2,
                multiplier=5,
            ),
            # Common areas
            ZoneEnergySummary(
                zone_name="Lobby",
                zone_type=ZoneType.COMMON_AREA,
                category=CommonAreaCategory.LOBBY,
                elec_kwh=3000.0,
                area_sqft=500.0,
            ),
            ZoneEnergySummary(
                zone_name="Corridors",
                zone_type=ZoneType.COMMON_AREA,
                category=CommonAreaCategory.CORRIDOR,
                elec_kwh=2500.0,
                area_sqft=1200.0,
            ),
            ZoneEnergySummary(
                zone_name="Fitness Center",
                zone_type=ZoneType.COMMON_AREA,
                category=CommonAreaCategory.FITNESS,
                elec_kwh=4000.0,
                area_sqft=800.0,
            ),
        ]

        # CUAC config for affordable housing
        cuac_config = CuacConfig(
            elec_utility="Pacific Gas and Electric Company (PG&E)",
            affordable_pv_dc_sys_size=30.0,  # 30 kWdc PV system
            pct_indiv_unit_pv_by_bedrms={1: 5.0, 2: 8.0},
        )

        tariff = create_pge_e_tou_c()

        allocator = ZoneCostAllocator(
            zone_summaries=zones,
            tariff=tariff,
            cuac_config=cuac_config,
        )

        summary = allocator.allocate_all()

        # Verify summary
        assert summary.dwelling_unit_count == 2  # 2 zone types
        assert summary.common_area_count == 3
        assert summary.total_annual_cost > 0
        assert summary.dwelling_unit_cost > 0
        assert summary.common_area_cost > 0

        # Verify bedroom summaries
        assert 1 in summary.dwelling_summaries
        assert 2 in summary.dwelling_summaries
        # 1BR should have lower allowance than 2BR
        if summary.dwelling_summaries[1].utility_allowance_monthly > 0:
            assert (summary.dwelling_summaries[1].utility_allowance_monthly <
                    summary.dwelling_summaries[2].utility_allowance_monthly)

        # Verify common area categories
        assert CommonAreaCategory.LOBBY in summary.common_summaries
        assert CommonAreaCategory.CORRIDOR in summary.common_summaries
        assert CommonAreaCategory.FITNESS in summary.common_summaries

    def test_cuac_allowance_with_pv(self):
        """Test CUAC allowance reduction with PV."""
        from eco_tools.lcca.zone_allocation import ZoneCostAllocator
        from eco_tools.lcca.zone_energy import ZoneEnergySummary
        from eco_tools.lcca.cuac.models import ZoneType, CuacConfig
        from eco_tools.lcca.tariffs import create_pge_e_tou_c

        zones = [
            ZoneEnergySummary(
                zone_name="2BR Unit",
                zone_type=ZoneType.DWELLING_UNIT,
                elec_kwh=5000.0,
                gas_therm=200.0,
                area_sqft=800.0,
                num_bedrooms=2,
                pv_allocation_kwdc=2.0,
                pv_generation_kwh=3000.0,
            ),
        ]

        cuac_config = CuacConfig(
            affordable_pv_dc_sys_size=50.0,
            pct_indiv_unit_pv_by_bedrms={2: 4.0},  # 4% = 2 kWdc
        )

        tariff = create_pge_e_tou_c()

        # Without PV
        allocator_no_pv = ZoneCostAllocator(
            zone_summaries=zones,
            tariff=tariff,
        )
        summary_no_pv = allocator_no_pv.allocate_all()

        # With PV/CUAC
        allocator_pv = ZoneCostAllocator(
            zone_summaries=zones,
            tariff=tariff,
            cuac_config=cuac_config,
        )
        summary_pv = allocator_pv.allocate_all()

        # Verify PV reduces costs
        zone_result = summary_pv.zone_results[0]
        assert zone_result.pv_credit > 0
        assert zone_result.net_total_cost < zone_result.gross_total_cost


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
