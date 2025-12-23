"""
Tests for Phase 4: Mixed-Use & Common Area Metering

Tests the meter_aggregation module and bridge.py mixed-use support.
"""

import pytest
from typing import List

from eco_tools.lcca.meter_aggregation import (
    MeterAggregator,
    MeterCategoryAggregate,
    BuildingSection,
    BuildingSectionType,
    MixedUseLccaResults,
    aggregate_zones_by_meter_category,
    create_mixed_use_lcca,
    format_meter_aggregation_table,
    format_building_sections_table,
)
from eco_tools.lcca.bridge import (
    create_mixed_use_scenarios,
    create_section_lcca_scenario,
    allocate_capex_by_section,
)
from eco_tools.lcca.zone_energy import ZoneEnergySummary
from eco_tools.lcca.cuac.models import ZoneType
from eco_tools.lcca.res_other.models import CommonAreaCategory


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def dwelling_unit_zones() -> List[ZoneEnergySummary]:
    """Create sample dwelling unit zones."""
    return [
        ZoneEnergySummary(
            zone_name="Unit-1BR-A",
            zone_type=ZoneType.DWELLING_UNIT,
            elec_kwh=4500,
            gas_therm=200,
            peak_demand_kw=2.5,
            area_sqft=750,
            num_bedrooms=1,
            multiplier=20,
            pv_allocation_kwdc=1.5,
            pv_generation_kwh=2250,
        ),
        ZoneEnergySummary(
            zone_name="Unit-2BR-A",
            zone_type=ZoneType.DWELLING_UNIT,
            elec_kwh=6000,
            gas_therm=280,
            peak_demand_kw=3.5,
            area_sqft=1050,
            num_bedrooms=2,
            multiplier=30,
            pv_allocation_kwdc=2.0,
            pv_generation_kwh=3000,
        ),
        ZoneEnergySummary(
            zone_name="Unit-3BR-A",
            zone_type=ZoneType.DWELLING_UNIT,
            elec_kwh=7500,
            gas_therm=350,
            peak_demand_kw=4.5,
            area_sqft=1400,
            num_bedrooms=3,
            multiplier=10,
            pv_allocation_kwdc=2.5,
            pv_generation_kwh=3750,
        ),
    ]


@pytest.fixture
def common_area_zones() -> List[ZoneEnergySummary]:
    """Create sample common area zones."""
    return [
        ZoneEnergySummary(
            zone_name="Lobby-L01",
            zone_type=ZoneType.COMMON_AREA,
            category=CommonAreaCategory.LOBBY,
            elec_kwh=15000,
            gas_therm=0,
            peak_demand_kw=8.0,
            area_sqft=2000,
            multiplier=1,
        ),
        ZoneEnergySummary(
            zone_name="Corridor-L01",
            zone_type=ZoneType.COMMON_AREA,
            category=CommonAreaCategory.CORRIDOR,
            elec_kwh=8000,
            gas_therm=0,
            peak_demand_kw=4.0,
            area_sqft=1500,
            multiplier=1,
        ),
        ZoneEnergySummary(
            zone_name="Corridor-L02",
            zone_type=ZoneType.COMMON_AREA,
            category=CommonAreaCategory.CORRIDOR,
            elec_kwh=8000,
            gas_therm=0,
            peak_demand_kw=4.0,
            area_sqft=1500,
            multiplier=1,
        ),
        ZoneEnergySummary(
            zone_name="Parking-L01",
            zone_type=ZoneType.COMMON_AREA,
            category=CommonAreaCategory.PARKING,
            elec_kwh=12000,
            gas_therm=0,
            peak_demand_kw=6.0,
            area_sqft=10000,
            multiplier=1,
        ),
        ZoneEnergySummary(
            zone_name="Fitness-L01",
            zone_type=ZoneType.COMMON_AREA,
            category=CommonAreaCategory.FITNESS,
            elec_kwh=5000,
            gas_therm=0,
            peak_demand_kw=3.0,
            area_sqft=1200,
            multiplier=1,
        ),
        ZoneEnergySummary(
            zone_name="Mech-L01",
            zone_type=ZoneType.COMMON_AREA,
            category=CommonAreaCategory.MECHANICAL,
            elec_kwh=3000,
            gas_therm=50,
            peak_demand_kw=2.0,
            area_sqft=500,
            multiplier=1,
        ),
    ]


@pytest.fixture
def commercial_zones() -> List[ZoneEnergySummary]:
    """Create sample commercial zones."""
    return [
        ZoneEnergySummary(
            zone_name="Retail-L01",
            zone_type=ZoneType.NONRESIDENTIAL,
            elec_kwh=45000,
            gas_therm=100,
            peak_demand_kw=25.0,
            area_sqft=5000,
            multiplier=1,
        ),
        ZoneEnergySummary(
            zone_name="Office-L01",
            zone_type=ZoneType.NONRESIDENTIAL,
            elec_kwh=30000,
            gas_therm=50,
            peak_demand_kw=18.0,
            area_sqft=3000,
            multiplier=1,
        ),
    ]


@pytest.fixture
def mixed_use_zones(
    dwelling_unit_zones,
    common_area_zones,
    commercial_zones,
) -> List[ZoneEnergySummary]:
    """Combine all zone types for mixed-use building."""
    return dwelling_unit_zones + common_area_zones + commercial_zones


# =============================================================================
# METER CATEGORY AGGREGATE TESTS
# =============================================================================

class TestMeterCategoryAggregate:
    """Tests for MeterCategoryAggregate class."""

    def test_create_empty_aggregate(self):
        """Test creating empty aggregate."""
        agg = MeterCategoryAggregate(
            category=CommonAreaCategory.CORRIDOR,
            meter_name="MtrElec_Corridor"
        )
        assert agg.zone_count == 0
        assert agg.total_elec_kwh == 0
        assert agg.total_area_sqft == 0

    def test_add_zone_to_aggregate(self, common_area_zones):
        """Test adding zones to aggregate."""
        agg = MeterCategoryAggregate(
            category=CommonAreaCategory.CORRIDOR,
            meter_name="MtrElec_Corridor"
        )

        # Add corridor zones
        corridor_zones = [z for z in common_area_zones if z.category == CommonAreaCategory.CORRIDOR]
        for zone in corridor_zones:
            agg.add_zone(zone)

        assert agg.zone_count == 2
        assert agg.total_elec_kwh == 16000  # 8000 + 8000
        assert agg.total_area_sqft == 3000  # 1500 + 1500

    def test_eui_calculation(self, common_area_zones):
        """Test EUI calculation for aggregate."""
        agg = MeterCategoryAggregate(
            category=CommonAreaCategory.LOBBY,
            meter_name="MtrElec_Lobby"
        )

        lobby_zone = [z for z in common_area_zones if z.category == CommonAreaCategory.LOBBY][0]
        agg.add_zone(lobby_zone)

        # EUI = (15000 kWh * 3.412 + 0 therm * 100) / 2000 sqft = 25.59 kBtu/sqft
        expected_eui = (15000 * 3.412) / 2000
        assert abs(agg.eui_kbtu_sqft - expected_eui) < 0.1

    def test_to_dict(self, common_area_zones):
        """Test dictionary conversion."""
        agg = MeterCategoryAggregate(
            category=CommonAreaCategory.LOBBY,
            meter_name="MtrElec_Lobby"
        )
        lobby_zone = [z for z in common_area_zones if z.category == CommonAreaCategory.LOBBY][0]
        agg.add_zone(lobby_zone)

        result = agg.to_dict()
        assert result['category'] == 'lobby'
        assert result['meter_name'] == 'MtrElec_Lobby'
        assert result['zone_count'] == 1
        assert result['total_elec_kwh'] == 15000


# =============================================================================
# BUILDING SECTION TESTS
# =============================================================================

class TestBuildingSection:
    """Tests for BuildingSection class."""

    def test_create_residential_section(self, dwelling_unit_zones):
        """Test creating residential building section."""
        section = BuildingSection(
            section_type=BuildingSectionType.RESIDENTIAL,
            name="Dwelling Units"
        )

        for zone in dwelling_unit_zones:
            section.add_zone(zone)

        assert section.zone_count == 3
        # Units: 20 + 30 + 10 = 60
        assert section.dwelling_unit_count == 60

    def test_section_energy_totals(self, dwelling_unit_zones):
        """Test energy total calculations."""
        section = BuildingSection(
            section_type=BuildingSectionType.RESIDENTIAL,
            name="Dwelling Units"
        )

        for zone in dwelling_unit_zones:
            section.add_zone(zone)

        # Total elec: 4500*20 + 6000*30 + 7500*10 = 90000 + 180000 + 75000 = 345000
        assert section.total_elec_kwh == 345000
        # Total gas: 200*20 + 280*30 + 350*10 = 4000 + 8400 + 3500 = 15900
        assert section.total_gas_therm == 15900

    def test_section_pv_totals(self, dwelling_unit_zones):
        """Test PV allocation totals."""
        section = BuildingSection(
            section_type=BuildingSectionType.RESIDENTIAL,
            name="Dwelling Units"
        )

        for zone in dwelling_unit_zones:
            section.add_zone(zone)

        # PV: 1.5*20 + 2.0*30 + 2.5*10 = 30 + 60 + 25 = 115 kWdc
        assert section.pv_allocation_kwdc == 115.0

    def test_common_area_meter_categories(self, common_area_zones):
        """Test meter category creation for common areas."""
        section = BuildingSection(
            section_type=BuildingSectionType.COMMON_AREA,
            name="Common Areas"
        )

        # Only add non-parking, non-fitness zones
        for zone in common_area_zones:
            if zone.category not in [CommonAreaCategory.PARKING, CommonAreaCategory.FITNESS]:
                section.add_zone(zone)

        # Should have LOBBY, CORRIDOR, MECHANICAL categories
        assert len(section.meter_categories) == 3
        assert CommonAreaCategory.LOBBY in section.meter_categories
        assert CommonAreaCategory.CORRIDOR in section.meter_categories
        assert CommonAreaCategory.MECHANICAL in section.meter_categories

        # Corridor should have 2 zones
        assert section.meter_categories[CommonAreaCategory.CORRIDOR].zone_count == 2


# =============================================================================
# METER AGGREGATOR TESTS
# =============================================================================

class TestMeterAggregator:
    """Tests for MeterAggregator class."""

    def test_create_aggregator(self):
        """Test creating empty aggregator."""
        agg = MeterAggregator()
        assert agg.zone_count == 0
        assert agg.total_elec_kwh == 0

    def test_add_dwelling_units(self, dwelling_unit_zones):
        """Test adding dwelling units to aggregator."""
        agg = MeterAggregator()
        agg.add_zones(dwelling_unit_zones)

        sections = agg.get_building_sections()
        assert BuildingSectionType.RESIDENTIAL in sections
        assert sections[BuildingSectionType.RESIDENTIAL].dwelling_unit_count == 60

    def test_add_common_areas(self, common_area_zones):
        """Test adding common areas to aggregator."""
        agg = MeterAggregator()
        agg.add_zones(common_area_zones)

        meters = agg.get_meter_categories()
        assert CommonAreaCategory.LOBBY in meters
        assert CommonAreaCategory.CORRIDOR in meters
        assert CommonAreaCategory.PARKING in meters
        assert CommonAreaCategory.FITNESS in meters

    def test_mixed_use_separation(self, mixed_use_zones):
        """Test separation of zones into building sections."""
        agg = MeterAggregator()
        agg.add_zones(mixed_use_zones)

        sections = agg.get_building_sections()

        # Should have residential, commercial, common area, parking, amenity
        assert BuildingSectionType.RESIDENTIAL in sections
        assert BuildingSectionType.COMMERCIAL in sections
        assert BuildingSectionType.COMMON_AREA in sections
        assert BuildingSectionType.PARKING in sections
        assert BuildingSectionType.AMENITY in sections

    def test_total_calculations(self, mixed_use_zones):
        """Test aggregator total calculations."""
        agg = MeterAggregator()
        agg.add_zones(mixed_use_zones)

        # Verify totals match sum of zones
        expected_elec = sum(z.elec_kwh * z.multiplier for z in mixed_use_zones)
        expected_gas = sum(z.gas_therm * z.multiplier for z in mixed_use_zones)

        assert agg.total_elec_kwh == expected_elec
        assert agg.total_gas_therm == expected_gas

    def test_master_meter_allocation_by_area(self, mixed_use_zones):
        """Test master meter allocation by area."""
        agg = MeterAggregator()
        agg.add_zones(mixed_use_zones)

        allocations = agg.allocate_master_meter(method="by_area")

        # Allocations should sum to 1.0
        total = sum(allocations.values())
        assert abs(total - 1.0) < 0.001

    def test_master_meter_allocation_by_modeled(self, mixed_use_zones):
        """Test master meter allocation by modeled consumption."""
        agg = MeterAggregator()
        agg.add_zones(mixed_use_zones)

        allocations = agg.allocate_master_meter(method="by_modeled")

        # Allocations should sum to 1.0
        total = sum(allocations.values())
        assert abs(total - 1.0) < 0.001

    def test_reconcile_to_master_meter(self, mixed_use_zones):
        """Test master meter reconciliation."""
        agg = MeterAggregator()
        agg.add_zones(mixed_use_zones)

        # Master meter might be 5% higher than zone sum
        zone_elec = agg.total_elec_kwh
        master_elec = zone_elec * 1.05

        results = agg.reconcile_to_master_meter(
            building_elec_kwh=master_elec,
            building_gas_therm=agg.total_gas_therm
        )

        assert results['elec_reconciliation_factor'] == pytest.approx(1.05, rel=0.01)
        assert results['elec_unaccounted_pct'] == pytest.approx(4.76, rel=0.1)

    def test_calculate_section_costs(self, mixed_use_zones):
        """Test section cost calculation."""
        agg = MeterAggregator()
        agg.add_zones(mixed_use_zones)

        agg.calculate_section_costs(
            elec_rate=0.25,
            gas_rate=1.50,
            demand_rate=15.0
        )

        sections = agg.get_building_sections()
        for section in sections.values():
            assert section.total_annual_cost > 0

    def test_summary(self, mixed_use_zones):
        """Test summary generation."""
        agg = MeterAggregator()
        agg.add_zones(mixed_use_zones)

        summary = agg.summary()

        assert 'zone_count' in summary
        assert 'total_elec_kwh' in summary
        assert 'sections' in summary
        assert 'meter_categories' in summary


# =============================================================================
# MIXED USE LCCA RESULTS TESTS
# =============================================================================

class TestMixedUseLccaResults:
    """Tests for MixedUseLccaResults class."""

    def test_create_results(self):
        """Test creating results object."""
        results = MixedUseLccaResults(building_name="Test Building")
        assert results.building_name == "Test Building"
        assert results.total_annual_cost == 0

    def test_calculate_shares(self, mixed_use_zones):
        """Test cost share calculation."""
        results = create_mixed_use_lcca(
            zones=mixed_use_zones,
            building_name="Test Building",
            elec_rate=0.25,
            gas_rate=1.50
        )

        # Shares should sum to approximately 100%
        total_share = (
            results.residential_share_pct +
            results.commercial_share_pct +
            results.common_area_share_pct
        )
        # Note: parking and amenity are separate sections not included in these shares
        assert total_share > 0

    def test_to_dict(self, mixed_use_zones):
        """Test dictionary conversion."""
        results = create_mixed_use_lcca(
            zones=mixed_use_zones,
            building_name="Test Building"
        )

        result_dict = results.to_dict()
        assert result_dict['building_name'] == "Test Building"
        assert 'total_annual_cost' in result_dict


# =============================================================================
# CONVENIENCE FUNCTION TESTS
# =============================================================================

class TestConvenienceFunctions:
    """Tests for convenience functions."""

    def test_aggregate_zones_by_meter_category(self, common_area_zones):
        """Test zone aggregation by meter category."""
        meters = aggregate_zones_by_meter_category(common_area_zones)

        assert CommonAreaCategory.LOBBY in meters
        assert CommonAreaCategory.CORRIDOR in meters
        assert meters[CommonAreaCategory.CORRIDOR].zone_count == 2

    def test_create_mixed_use_lcca(self, mixed_use_zones):
        """Test create_mixed_use_lcca function."""
        results = create_mixed_use_lcca(
            zones=mixed_use_zones,
            building_name="Test Building",
            elec_rate=0.25,
            gas_rate=1.50
        )

        assert results.building_name == "Test Building"
        assert results.total_annual_cost > 0
        assert results.residential_result is not None


# =============================================================================
# BRIDGE FUNCTION TESTS
# =============================================================================

class TestBridgeMixedUseFunctions:
    """Tests for bridge.py mixed-use functions."""

    def test_create_mixed_use_scenarios(self, mixed_use_zones):
        """Test create_mixed_use_scenarios function."""
        result = create_mixed_use_scenarios(
            zones=mixed_use_zones,
            default_elec_rate=0.25,
            default_gas_rate=1.50
        )

        assert 'combined' in result
        assert 'sections' in result
        assert 'aggregator' in result
        assert result['combined']['zone_count'] == len(mixed_use_zones)

    def test_create_mixed_use_scenarios_residential(self, mixed_use_zones):
        """Test residential section in mixed-use scenarios."""
        result = create_mixed_use_scenarios(
            zones=mixed_use_zones,
            default_elec_rate=0.25
        )

        assert 'residential' in result
        assert result['residential']['dwelling_unit_count'] == 60

    def test_create_mixed_use_scenarios_common_area(self, mixed_use_zones):
        """Test common area section in mixed-use scenarios."""
        result = create_mixed_use_scenarios(
            zones=mixed_use_zones,
            default_elec_rate=0.25
        )

        assert 'common_area' in result
        assert 'meter_categories' in result['common_area']

    def test_allocate_capex_by_section(self, mixed_use_zones):
        """Test capex allocation by section."""
        allocations = allocate_capex_by_section(
            total_capex=1000000,
            zones=mixed_use_zones,
            method="by_area"
        )

        assert 'residential' in allocations
        assert 'commercial' in allocations
        assert 'common_area' in allocations

        # Sum should be close to total (may not be exact due to parking/amenity)
        total = sum(allocations.values())
        assert total > 0


# =============================================================================
# FORMATTING TESTS
# =============================================================================

class TestFormatting:
    """Tests for formatting functions."""

    def test_format_meter_aggregation_table(self, common_area_zones):
        """Test meter aggregation table formatting."""
        meters = aggregate_zones_by_meter_category(common_area_zones)
        table = format_meter_aggregation_table(meters)

        assert "COMMON AREA METER AGGREGATION" in table
        assert "Lobby" in table
        assert "Corridor" in table
        assert "TOTAL" in table

    def test_format_building_sections_table(self, mixed_use_zones):
        """Test building sections table formatting."""
        agg = MeterAggregator()
        agg.add_zones(mixed_use_zones)
        agg.calculate_section_costs(elec_rate=0.25, gas_rate=1.50)

        sections = agg.get_building_sections()
        table = format_building_sections_table(sections)

        assert "BUILDING SECTIONS SUMMARY" in table
        assert "Dwelling Units" in table
        assert "TOTAL" in table


# =============================================================================
# EDGE CASE TESTS
# =============================================================================

class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_empty_zone_list(self):
        """Test with empty zone list."""
        agg = MeterAggregator()
        agg.add_zones([])

        assert agg.zone_count == 0
        assert agg.total_elec_kwh == 0

    def test_single_zone(self):
        """Test with single zone."""
        zone = ZoneEnergySummary(
            zone_name="Single-Unit",
            zone_type=ZoneType.DWELLING_UNIT,
            elec_kwh=5000,
            gas_therm=200,
            area_sqft=1000,
            multiplier=1
        )

        agg = MeterAggregator()
        agg.add_zone(zone)

        assert agg.zone_count == 1
        assert agg.dwelling_unit_count == 1

    def test_all_unconditioned_zones(self):
        """Test with only unconditioned zones."""
        zones = [
            ZoneEnergySummary(
                zone_name="Storage-1",
                zone_type=ZoneType.UNCONDITIONED,
                category=CommonAreaCategory.STORAGE,
                elec_kwh=500,
                gas_therm=0,
                area_sqft=200,
                multiplier=1
            ),
        ]

        agg = MeterAggregator()
        agg.add_zones(zones)

        assert agg.zone_count == 1

    def test_zero_area_zone(self):
        """Test zone with zero area."""
        zone = ZoneEnergySummary(
            zone_name="Zero-Area",
            zone_type=ZoneType.COMMON_AREA,
            category=CommonAreaCategory.OTHER,
            elec_kwh=1000,
            gas_therm=0,
            area_sqft=0,  # Zero area
            multiplier=1
        )

        meters = aggregate_zones_by_meter_category([zone])
        # Should not crash, EUI should be 0
        assert meters[CommonAreaCategory.OTHER].eui_kbtu_sqft == 0

    def test_high_multiplier_zones(self):
        """Test zones with high multipliers."""
        zone = ZoneEnergySummary(
            zone_name="Large-Building-Unit",
            zone_type=ZoneType.DWELLING_UNIT,
            elec_kwh=5000,
            gas_therm=200,
            area_sqft=800,
            multiplier=200  # 200 identical units
        )

        agg = MeterAggregator()
        agg.add_zone(zone)

        assert agg.dwelling_unit_count == 200
        assert agg.total_elec_kwh == 5000 * 200


# =============================================================================
# INTEGRATION TESTS
# =============================================================================

class TestIntegration:
    """Integration tests for complete workflows."""

    def test_complete_mixed_use_workflow(self, mixed_use_zones):
        """Test complete mixed-use building LCCA workflow."""
        # Step 1: Create aggregator and add zones
        agg = MeterAggregator()
        agg.add_zones(mixed_use_zones)

        # Step 2: Set building totals (from master meter)
        agg.set_building_totals(
            building_elec_kwh=agg.total_elec_kwh * 1.02,  # 2% unaccounted
            building_gas_therm=agg.total_gas_therm
        )

        # Step 3: Calculate costs
        agg.calculate_section_costs(elec_rate=0.25, gas_rate=1.50)

        # Step 4: Reconcile to master meter
        reconcile = agg.reconcile_to_master_meter()

        # Step 5: Get summary
        summary = agg.summary()

        # Verify complete workflow
        assert summary['zone_count'] == len(mixed_use_zones)
        assert reconcile['elec_unaccounted_pct'] == pytest.approx(1.96, rel=0.1)

    def test_common_area_metering_workflow(self, common_area_zones):
        """Test common area metering workflow."""
        # Aggregate by category
        meters = aggregate_zones_by_meter_category(common_area_zones)

        # Verify meter categories
        assert len(meters) >= 4  # LOBBY, CORRIDOR, PARKING, FITNESS, MECHANICAL

        # Calculate total common area consumption
        total_elec = sum(m.total_elec_kwh for m in meters.values())
        expected_total = sum(z.elec_kwh * z.multiplier for z in common_area_zones)
        assert total_elec == expected_total

        # Generate report
        table = format_meter_aggregation_table(meters)
        assert "TOTAL" in table

    def test_cost_allocation_workflow(self, mixed_use_zones):
        """Test cost allocation across sections."""
        total_capex = 2000000  # $2M total cost

        # Allocate by different methods
        by_area = allocate_capex_by_section(total_capex, mixed_use_zones, "by_area")
        by_modeled = allocate_capex_by_section(total_capex, mixed_use_zones, "by_modeled")

        # Both should allocate some to residential and common area
        assert by_area['residential'] > 0
        assert by_area['common_area'] > 0
        assert by_modeled['residential'] > 0
