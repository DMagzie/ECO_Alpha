#!/usr/bin/env python3
"""
Gas Metering Integration Tests
==============================

Validates the gas metering extension for zone-level LCCA.

Tests:
1. Gas meter generation in zone_meter_mapper
2. Gas meter transformation in cse_transformer
3. Gas meter parsing in cse_zone_output
4. Gas data population in zone_simulation
5. Gas cost calculation in CLI

Author: ECO Tools Team
Version: 7.0.0
Date: January 2026
"""

import pytest
import sys
from pathlib import Path
from typing import List, Dict, Any

# Add project root to path
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


class TestZoneMeterMapperGas:
    """Test gas meter generation in zone_meter_mapper."""

    def test_gas_meter_assignment_fields(self):
        """Test that ZoneMeterAssignment has gas meter fields."""
        from eco_tools.lcca.zone_meter_mapper import (
            ZoneMeterAssignment,
            ZoneClassification,
            BuildingSectionType,
        )

        # Create assignment with gas - meter names are auto-generated from zone_name
        assignment = ZoneMeterAssignment(
            zone_name="TestZone",
            zone_classification=ZoneClassification.DWELLING_UNIT,
            section_type=BuildingSectionType.RESIDENTIAL,
            has_gas=True,
        )

        # Gas meter names are generated from zone name
        assert assignment.gas_zone_meter == "MtrGas_TestZone"
        assert assignment.gas_building_meter == "MtrGas"
        assert assignment.has_gas == True

    def test_meter_hierarchy_gas_fields(self):
        """Test that MeterHierarchy has gas meter collections."""
        from eco_tools.lcca.zone_meter_mapper import MeterHierarchy

        # Create hierarchy
        hierarchy = MeterHierarchy()

        # Check gas fields exist
        assert hasattr(hierarchy, 'gas_building_meter')
        assert hasattr(hierarchy, 'gas_section_meters')
        assert hasattr(hierarchy, 'gas_zone_meters')
        assert hasattr(hierarchy, 'gas_submeter_map')
        assert hierarchy.gas_building_meter == "MtrGas"


class TestCSETransformerGas:
    """Test gas meter transformation in cse_transformer."""

    def test_gas_constants(self):
        """Test gas-related constants are defined."""
        from eco_tools.lcca.cse_transformer import (
            EXPORT_BTU_SF_GAS,
            FUEL_GAS,
        )

        assert EXPORT_BTU_SF_GAS == 100  # therms = kBtu / 100
        assert FUEL_GAS == "GAS"

    def test_transform_result_gas_fields(self):
        """Test TransformResult has gas statistics fields."""
        from eco_tools.lcca.cse_transformer import TransformResult

        result = TransformResult(
            success=True,
            original_file="test.cse",
            transformed_content="METER test",
            gas_meters_added=5,
            gas_exports_added=5,
        )

        assert result.gas_meters_added == 5
        assert result.gas_exports_added == 5

    def test_cse_export_definition_fuel_type(self):
        """Test CSEExportDefinition supports fuel_type."""
        from eco_tools.lcca.cse_transformer import CSEExportDefinition

        export_def = CSEExportDefinition(
            name="Export_Gas_Test",
            meter="MtrGas_Test",
            exportfile="gas_test.csv",
            fuel_type="GAS",
        )

        assert export_def.fuel_type == "GAS"


class TestCSEZoneOutputGas:
    """Test gas meter parsing in cse_zone_output."""

    def test_zone_gas_hourly_data(self):
        """Test ZoneGasHourlyData dataclass."""
        from eco_tools.lcca.parsers.cse_zone_output import ZoneGasHourlyData

        gas_data = ZoneGasHourlyData(
            zone_name="TestZone",
            meter_name="MtrGas_Test",
        )

        assert gas_data.zone_name == "TestZone"
        assert gas_data.meter_name == "MtrGas_Test"
        assert gas_data.total_therm == []
        assert gas_data.heating_therm == []
        assert gas_data.dhw_therm == []

    def test_zone_gas_hourly_data_is_complete(self):
        """Test is_complete property for gas data."""
        from eco_tools.lcca.parsers.cse_zone_output import ZoneGasHourlyData

        # Incomplete data
        gas_data = ZoneGasHourlyData(
            zone_name="TestZone",
            meter_name="MtrGas_Test",
            total_therm=[0.1] * 100,  # Only 100 hours
        )
        assert gas_data.is_complete == False

        # Complete data
        gas_data_complete = ZoneGasHourlyData(
            zone_name="TestZone",
            meter_name="MtrGas_Test",
            total_therm=[0.1] * 8760,
        )
        assert gas_data_complete.is_complete == True

    def test_cse_zone_output_model_gas_meters(self):
        """Test CSEZoneOutputModel has gas meter collection."""
        from eco_tools.lcca.parsers.cse_zone_output import CSEZoneOutputModel

        model = CSEZoneOutputModel()

        assert hasattr(model, 'gas_meters')
        assert model.gas_meters == {}


class TestZoneSimulationGas:
    """Test gas data population in zone_simulation."""

    def test_zone_simulation_imports(self):
        """Test zone_simulation can import gas-related types."""
        from eco_tools.lcca.zone_simulation import ZoneSimulationPipeline
        from eco_tools.lcca.parsers.cse_zone_output import ZoneGasHourlyData

        # Just verify imports work
        assert ZoneSimulationPipeline is not None
        assert ZoneGasHourlyData is not None


class TestZoneEnergySummaryGas:
    """Test gas fields in ZoneEnergySummary."""

    def test_zone_energy_summary_gas_fields(self):
        """Test ZoneEnergySummary has gas fields."""
        from eco_tools.lcca.zone_energy import ZoneEnergySummary
        from eco_tools.lcca.cuac.models import ZoneType

        summary = ZoneEnergySummary(
            zone_name="TestZone",
            zone_type=ZoneType.DWELLING_UNIT,
            elec_kwh=1000,
            gas_therm=50,
            heating_therm=30,
            dhw_therm=20,
            hourly_gas_therm=[0.01] * 8760,
        )

        assert summary.gas_therm == 50
        assert summary.heating_therm == 30
        assert summary.dhw_therm == 20
        assert len(summary.hourly_gas_therm) == 8760

    def test_create_zone_energy_from_hourly_with_gas(self):
        """Test create_zone_energy_from_hourly handles gas data."""
        from eco_tools.lcca.zone_energy import create_zone_energy_from_hourly
        from eco_tools.lcca.cuac.models import ZoneType

        hourly_elec = [1.0] * 8760  # 1 kWh per hour
        hourly_gas = [0.01] * 8760  # 0.01 therm per hour

        summary = create_zone_energy_from_hourly(
            zone_name="TestZone",
            zone_type=ZoneType.DWELLING_UNIT,
            hourly_elec=hourly_elec,
            hourly_gas=hourly_gas,
            num_bedrooms=2,
        )

        assert summary.elec_kwh == 8760  # Sum of hourly
        assert summary.gas_therm == pytest.approx(87.6, rel=0.01)  # Sum of hourly


class TestCLIGas:
    """Test gas support in CLI zone-analyze."""

    def test_cli_gas_rate_argument(self):
        """Test zone-analyze has --gas-rate argument."""
        from eco_tools.lcca.cli import create_parser

        parser = create_parser()

        # Parse with gas-rate
        args = parser.parse_args([
            "zone-analyze",
            "/tmp/test",
            "--gas-rate", "2.50",
        ])

        assert args.gas_rate == 2.50


class TestGasMeterConstants:
    """Test gas meter naming constants."""

    def test_meter_prefix_gas(self):
        """Test METER_PREFIX_GAS constant."""
        from eco_tools.lcca.zone_meter_mapper import METER_PREFIX_GAS

        assert METER_PREFIX_GAS == "MtrGas"


def run_all_gas_tests():
    """Run all gas metering tests and print summary."""
    print("=" * 70)
    print("Gas Metering Integration Test Suite")
    print("=" * 70)

    # Run tests
    exit_code = pytest.main([
        __file__,
        "-v",
        "--tb=short",
    ])

    return exit_code


if __name__ == "__main__":
    sys.exit(run_all_gas_tests())
