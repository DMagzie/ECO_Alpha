"""
CA/HI Regional Helpers Tests
============================

Tests for the ca_hi_helpers module including:
- Regional cost factors
- Climate zone to region mapping
- Region to utility mapping
- Tariff selection by region
- Integration with tariffs.py

Run with:
    pytest tests/test_ca_hi_helpers.py -v
"""

import pytest


class TestRegionalFactors:
    """Tests for regional cost factors."""

    def test_ca_regional_factors_exist(self):
        """Verify California regional factors are defined."""
        from eco_tools.lcca.ca_hi_helpers import CA_REGIONAL_FACTORS

        assert len(CA_REGIONAL_FACTORS) >= 18
        assert 'US-CA-SF' in CA_REGIONAL_FACTORS
        assert 'US-CA-LA' in CA_REGIONAL_FACTORS
        assert 'US-CA-SD' in CA_REGIONAL_FACTORS

    def test_hi_regional_factors_exist(self):
        """Verify Hawaii regional factors are defined."""
        from eco_tools.lcca.ca_hi_helpers import HI_REGIONAL_FACTORS

        assert len(HI_REGIONAL_FACTORS) >= 4
        assert 'US-HI-HON' in HI_REGIONAL_FACTORS
        assert 'US-HI-MAU' in HI_REGIONAL_FACTORS
        assert 'US-HI-BIG' in HI_REGIONAL_FACTORS

    def test_combined_regional_factors(self):
        """Verify combined regional factors include CA, HI, and national."""
        from eco_tools.lcca.ca_hi_helpers import REGIONAL_FACTORS

        assert len(REGIONAL_FACTORS) >= 22
        assert 'US-CA-SF' in REGIONAL_FACTORS
        assert 'US-HI-MAU' in REGIONAL_FACTORS
        assert 'US-NATIONAL' in REGIONAL_FACTORS

    def test_get_regional_factor_sf(self):
        """Test San Francisco has high regional factor."""
        from eco_tools.lcca.ca_hi_helpers import get_regional_factor

        sf_factor = get_regional_factor('US-CA-SF')
        assert sf_factor >= 1.35
        assert sf_factor <= 1.45

    def test_get_regional_factor_maui(self):
        """Test Maui has highest factor."""
        from eco_tools.lcca.ca_hi_helpers import get_regional_factor

        maui_factor = get_regional_factor('US-HI-MAU')
        assert maui_factor >= 1.48

    def test_get_regional_factor_unknown(self):
        """Test unknown region returns 1.0."""
        from eco_tools.lcca.ca_hi_helpers import get_regional_factor

        unknown = get_regional_factor('UNKNOWN-REGION')
        assert unknown == 1.0

    def test_get_regional_factor_national(self):
        """Test national baseline is 1.0."""
        from eco_tools.lcca.ca_hi_helpers import get_regional_factor

        national = get_regional_factor('US-NATIONAL')
        assert national == 1.0

    def test_regional_factors_reasonable_range(self):
        """Verify all factors are in reasonable range."""
        from eco_tools.lcca.ca_hi_helpers import REGIONAL_FACTORS

        for region, factor in REGIONAL_FACTORS.items():
            assert 0.8 <= factor <= 2.0, f"Factor for {region} out of range: {factor}"


class TestClimateZoneMapping:
    """Tests for climate zone to region mapping."""

    def test_cz_to_region_mapping_exists(self):
        """Verify climate zone mapping is defined."""
        from eco_tools.lcca.ca_hi_helpers import CZ_TO_REGION

        assert len(CZ_TO_REGION) >= 16

    def test_get_region_from_climate_zone_cz12(self):
        """Test CZ12 maps to Sacramento."""
        from eco_tools.lcca.ca_hi_helpers import get_region_from_climate_zone

        region = get_region_from_climate_zone('CZ12')
        assert region == 'US-CA-SAC'

    def test_get_region_from_climate_zone_numeric(self):
        """Test numeric climate zone input."""
        from eco_tools.lcca.ca_hi_helpers import get_region_from_climate_zone

        region = get_region_from_climate_zone('12')
        assert region == 'US-CA-SAC'

    def test_get_region_from_climate_zone_cz03(self):
        """Test CZ03 maps to Oakland."""
        from eco_tools.lcca.ca_hi_helpers import get_region_from_climate_zone

        region = get_region_from_climate_zone('CZ03')
        assert region == 'US-CA-OAK'

    def test_get_region_from_climate_zone_cz07(self):
        """Test CZ07 maps to San Diego."""
        from eco_tools.lcca.ca_hi_helpers import get_region_from_climate_zone

        region = get_region_from_climate_zone('CZ07')
        assert region == 'US-CA-SD'

    def test_get_region_from_climate_zone_hawaii(self):
        """Test Hawaii climate zones."""
        from eco_tools.lcca.ca_hi_helpers import get_region_from_climate_zone

        region1 = get_region_from_climate_zone('HI01')
        assert region1 == 'US-HI-HON'

        region3 = get_region_from_climate_zone('HI03')
        assert region3 == 'US-HI-MAU'

    def test_get_region_from_climate_zone_unknown(self):
        """Test unknown climate zone returns CA default."""
        from eco_tools.lcca.ca_hi_helpers import get_region_from_climate_zone

        region = get_region_from_climate_zone('XYZ99')
        assert region == 'US-CA'

    def test_get_region_from_climate_zone_case_insensitive(self):
        """Test case insensitive input."""
        from eco_tools.lcca.ca_hi_helpers import get_region_from_climate_zone

        region1 = get_region_from_climate_zone('cz12')
        region2 = get_region_from_climate_zone('CZ12')
        assert region1 == region2


class TestUtilityMapping:
    """Tests for region to utility mapping."""

    def test_region_to_utility_mapping_exists(self):
        """Verify utility mapping is defined."""
        from eco_tools.lcca.ca_hi_helpers import REGION_TO_UTILITY

        assert len(REGION_TO_UTILITY) >= 18

    def test_get_utility_for_region_pge(self):
        """Test PG&E territory mapping."""
        from eco_tools.lcca.ca_hi_helpers import get_utility_for_region

        assert get_utility_for_region('US-CA-SF') == 'PGE'
        assert get_utility_for_region('US-CA-OAK') == 'PGE'
        assert get_utility_for_region('US-CA-SJ') == 'PGE'
        assert get_utility_for_region('US-CA-SAC') == 'PGE'

    def test_get_utility_for_region_sce(self):
        """Test SCE territory mapping."""
        from eco_tools.lcca.ca_hi_helpers import get_utility_for_region

        assert get_utility_for_region('US-CA-LA') == 'SCE'
        assert get_utility_for_region('US-CA-OC') == 'SCE'
        assert get_utility_for_region('US-CA-RIV') == 'SCE'

    def test_get_utility_for_region_sdge(self):
        """Test SDG&E territory mapping."""
        from eco_tools.lcca.ca_hi_helpers import get_utility_for_region

        assert get_utility_for_region('US-CA-SD') == 'SDGE'

    def test_get_utility_for_region_hawaii(self):
        """Test Hawaii utility mapping."""
        from eco_tools.lcca.ca_hi_helpers import get_utility_for_region

        assert get_utility_for_region('US-HI-HON') == 'HECO'
        assert get_utility_for_region('US-HI-MAU') == 'MECO'
        assert get_utility_for_region('US-HI-BIG') == 'HELCO'

    def test_get_gas_utility_for_region(self):
        """Test gas utility mapping."""
        from eco_tools.lcca.ca_hi_helpers import get_utility_for_region

        assert get_utility_for_region('US-CA-LA', 'gas') == 'SOCALGAS'
        assert get_utility_for_region('US-CA-SF', 'gas') == 'PGE'
        assert get_utility_for_region('US-HI-HON', 'gas') == 'PROPANE'


class TestDefaultRates:
    """Tests for default rate selection."""

    def test_get_default_rate_residential_pge(self):
        """Test residential rate selection for PG&E territory."""
        from eco_tools.lcca.ca_hi_helpers import get_default_rate_id

        rate = get_default_rate_id('US-CA-SF', 'residential')
        assert 'PGE' in rate or 'E-TOU' in rate

    def test_get_default_rate_commercial_sce(self):
        """Test commercial rate selection for SCE territory."""
        from eco_tools.lcca.ca_hi_helpers import get_default_rate_id

        rate = get_default_rate_id('US-CA-LA', 'commercial')
        assert 'SCE' in rate or 'TOU-GS' in rate

    def test_get_default_rate_hawaii(self):
        """Test rate selection for Hawaii."""
        from eco_tools.lcca.ca_hi_helpers import get_default_rate_id

        rate_hon = get_default_rate_id('US-HI-HON', 'residential')
        assert 'HECO' in rate_hon

        rate_maui = get_default_rate_id('US-HI-MAU', 'residential')
        assert 'MECO' in rate_maui


class TestRegionInfo:
    """Tests for region info helpers."""

    def test_list_regions_by_state_ca(self):
        """Test listing California regions."""
        from eco_tools.lcca.ca_hi_helpers import list_regions_by_state

        ca_regions = list_regions_by_state('CA')
        assert len(ca_regions) >= 18
        assert 'US-CA-SF' in ca_regions
        assert 'US-CA-LA' in ca_regions

    def test_list_regions_by_state_hi(self):
        """Test listing Hawaii regions."""
        from eco_tools.lcca.ca_hi_helpers import list_regions_by_state

        hi_regions = list_regions_by_state('HI')
        assert len(hi_regions) >= 4
        assert 'US-HI-HON' in hi_regions

    def test_get_region_info(self):
        """Test getting comprehensive region info."""
        from eco_tools.lcca.ca_hi_helpers import get_region_info

        info = get_region_info('US-CA-SF')
        assert info['region_code'] == 'US-CA-SF'
        assert info['cost_factor'] >= 1.35
        assert info['electric_utility'] == 'PGE'
        assert 'default_residential_rate' in info
        assert 'default_commercial_rate' in info

    def test_get_climate_zone_info(self):
        """Test getting info from climate zone."""
        from eco_tools.lcca.ca_hi_helpers import get_climate_zone_info

        info = get_climate_zone_info('CZ12')
        assert 'region_code' in info
        assert info['climate_zone'] == 'CZ12'
        assert info['electric_utility'] == 'PGE'


class TestRegionMetadata:
    """Tests for region metadata."""

    def test_region_metadata_exists(self):
        """Verify region metadata is defined."""
        from eco_tools.lcca.ca_hi_helpers import REGION_METADATA

        assert len(REGION_METADATA) >= 18
        assert 'US-CA-SF' in REGION_METADATA
        assert 'US-HI-MAU' in REGION_METADATA

    def test_get_region_metadata(self):
        """Test getting region metadata."""
        from eco_tools.lcca.ca_hi_helpers import get_region_metadata

        sf = get_region_metadata('US-CA-SF')
        assert sf is not None
        assert sf.code == 'US-CA-SF'
        assert sf.name == 'San Francisco'
        assert sf.state == 'CA'
        assert sf.cost_factor >= 1.35

    def test_find_region_by_climate_zone(self):
        """Test finding region metadata by climate zone."""
        from eco_tools.lcca.ca_hi_helpers import find_region_by_climate_zone

        metadata = find_region_by_climate_zone('CZ12')
        assert metadata is not None
        assert metadata.code == 'US-CA-SAC'
        assert metadata.name == 'Sacramento'


class TestCostCalculations:
    """Tests for cost calculation helpers."""

    def test_apply_regional_factor(self):
        """Test applying regional factor to base cost."""
        from eco_tools.lcca.ca_hi_helpers import apply_regional_factor

        base_cost = 10000
        sf_cost = apply_regional_factor(base_cost, 'US-CA-SF')
        assert sf_cost > base_cost
        assert sf_cost >= 13500  # SF factor ~1.38

        national_cost = apply_regional_factor(base_cost, 'US-NATIONAL')
        assert national_cost == base_cost

    def test_estimate_utility_costs(self):
        """Test utility cost estimation."""
        from eco_tools.lcca.ca_hi_helpers import estimate_utility_costs

        # Typical residential usage
        result = estimate_utility_costs(
            annual_kwh=10000,
            annual_therm=500,
            region_code='US-CA-SF',
            building_type='residential'
        )

        assert 'elec_cost' in result
        assert 'gas_cost' in result
        assert 'total_cost' in result
        assert result['elec_cost'] > 0
        assert result['gas_cost'] > 0
        assert result['total_cost'] == result['elec_cost'] + result['gas_cost']

    def test_estimate_utility_costs_hawaii(self):
        """Test Hawaii utility costs are higher."""
        from eco_tools.lcca.ca_hi_helpers import estimate_utility_costs

        ca_result = estimate_utility_costs(10000, 500, 'US-CA-SF', 'residential')
        hi_result = estimate_utility_costs(10000, 500, 'US-HI-HON', 'residential')

        assert hi_result['elec_cost'] > ca_result['elec_cost']
        assert hi_result['gas_cost'] > ca_result['gas_cost']


class TestTariffIntegration:
    """Tests for integration with tariffs.py."""

    def test_tariff_registry_expanded(self):
        """Verify tariff registry includes new rates."""
        from eco_tools.lcca.tariffs import TARIFF_REGISTRY

        # Check residential rates
        assert 'PG&E E-TOU-C' in TARIFF_REGISTRY
        assert 'SCE TOU-D-4-9PM' in TARIFF_REGISTRY
        assert 'SDG&E TOU-DR1' in TARIFF_REGISTRY

        # Check Hawaii rates
        assert 'HECO R-TOU' in TARIFF_REGISTRY
        assert 'MECO R' in TARIFF_REGISTRY
        assert 'HELCO R' in TARIFF_REGISTRY

    def test_get_tariff_by_name_residential(self):
        """Test getting residential tariffs by name."""
        from eco_tools.lcca.tariffs import get_tariff_by_name

        pge = get_tariff_by_name('PG&E E-TOU-C')
        assert pge is not None
        assert pge.name == 'E-TOU-C'
        assert 'Pacific Gas' in pge.utility

        sce = get_tariff_by_name('SCE TOU-D-4-9PM')
        assert sce is not None
        assert 'Edison' in sce.utility

    def test_get_tariff_by_name_hawaii(self):
        """Test getting Hawaii tariffs."""
        from eco_tools.lcca.tariffs import get_tariff_by_name

        heco = get_tariff_by_name('HECO R-TOU')
        assert heco is not None
        assert 'Hawaiian Electric' in heco.utility

        meco = get_tariff_by_name('MECO R')
        assert meco is not None
        assert 'Maui' in meco.utility

    def test_list_available_tariffs_expanded(self):
        """Verify list of tariffs includes new rates."""
        from eco_tools.lcca.tariffs import list_available_tariffs

        tariffs = list_available_tariffs()
        assert len(tariffs) >= 15

        # Check residential rates appear
        tariff_str = '\n'.join(tariffs)
        assert 'E-TOU-C' in tariff_str
        assert 'TOU-D-4-9PM' in tariff_str
        assert 'HECO' in tariff_str

    def test_list_tariffs_by_utility(self):
        """Test listing tariffs by utility."""
        from eco_tools.lcca.tariffs import list_tariffs_by_utility

        pge_tariffs = list_tariffs_by_utility('PGE')
        assert len(pge_tariffs) >= 2
        assert any('E-TOU-C' in t for t in pge_tariffs)

        heco_tariffs = list_tariffs_by_utility('HECO')
        assert len(heco_tariffs) >= 1

    def test_get_default_tariff_for_region(self):
        """Test getting default tariff by region."""
        from eco_tools.lcca.tariffs import get_default_tariff_for_region

        sf_tariff = get_default_tariff_for_region('US-CA-SF', 'residential')
        assert sf_tariff is not None
        assert 'Pacific Gas' in sf_tariff.utility

        hi_tariff = get_default_tariff_for_region('US-HI-HON', 'residential')
        assert hi_tariff is not None
        assert 'Hawaiian' in hi_tariff.utility or 'HECO' in hi_tariff.utility

    def test_hawaii_rates_higher_than_ca(self):
        """Verify Hawaii rates are higher than California."""
        from eco_tools.lcca.tariffs import get_tariff_by_name

        pge = get_tariff_by_name('PG&E E-TOU-C')
        heco = get_tariff_by_name('HECO R-TOU')

        assert heco.energy_rates.summer_on_peak >= pge.energy_rates.summer_on_peak
        assert heco.gas_rate > pge.gas_rate  # Propane vs natural gas

    def test_ev_tariffs_have_low_off_peak(self):
        """Verify EV tariffs have low off-peak rates."""
        from eco_tools.lcca.tariffs import get_tariff_by_name

        ev2a = get_tariff_by_name('PG&E EV2-A')
        assert ev2a is not None
        assert ev2a.energy_rates.summer_off_peak < 0.25

        sdge_ev = get_tariff_by_name('SDG&E EV-TOU-5')
        assert sdge_ev is not None
        assert sdge_ev.energy_rates.summer_off_peak < 0.15


class TestBackwardCompatibility:
    """Tests for backward compatibility."""

    def test_existing_tariffs_still_work(self):
        """Verify existing tariffs still function."""
        from eco_tools.lcca.tariffs import (
            create_sce_tou_gs3,
            create_pge_b20,
            create_sdge_al_tou,
            get_tariff_by_name,
        )

        sce = create_sce_tou_gs3()
        assert sce.name == "TOU-GS-3"

        pge = create_pge_b20()
        assert pge.name == "B-20"

        sdge = create_sdge_al_tou()
        assert sdge.name == "AL-TOU"

        # Test via get_tariff_by_name
        sce2 = get_tariff_by_name("SCE TOU-GS-3")
        assert sce2 is not None

    def test_old_tariff_names_still_work(self):
        """Verify old tariff name aliases still work."""
        from eco_tools.lcca.tariffs import get_tariff_by_name

        # These were the original names
        assert get_tariff_by_name("TOU-GS-3") is not None
        assert get_tariff_by_name("B-20") is not None
        assert get_tariff_by_name("AL-TOU") is not None


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
