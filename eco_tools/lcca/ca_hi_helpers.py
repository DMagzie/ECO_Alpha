"""
California & Hawaii Regional Helpers for LCCA.

Provides:
- Regional cost adjustment factors (ENR CCI based)
- Climate zone to region code mapping
- Region to utility service territory mapping
- Default tariff selection by region
- Utility rate presets for CA/HI

This module integrates with CostDB v0.06 and tariffs.py
to provide region-specific defaults for LCCA calculations.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, Optional, List, Tuple
from enum import Enum


# =============================================================================
# REGIONAL COST FACTORS (ENR Construction Cost Index based)
# =============================================================================

# California regional cost factors (relative to US national average = 1.0)
CA_REGIONAL_FACTORS: Dict[str, float] = {
    'US-CA': 1.10,           # State average
    'US-CA-SF': 1.38,        # San Francisco
    'US-CA-OAK': 1.35,       # Oakland
    'US-CA-SJ': 1.36,        # San Jose
    'US-CA-LA': 1.22,        # Los Angeles
    'US-CA-SD': 1.18,        # San Diego
    'US-CA-OC': 1.20,        # Orange County
    'US-CA-SAC': 1.12,       # Sacramento
    'US-CA-FRE': 1.05,       # Fresno
    'US-CA-BAK': 1.03,       # Bakersfield
    'US-CA-RIV': 1.08,       # Riverside/San Bernardino
    'US-CA-SB': 1.15,        # Santa Barbara
    'US-CA-VEN': 1.12,       # Ventura
    'US-CA-MON': 1.10,       # Monterey
    'US-CA-SLO': 1.08,       # San Luis Obispo
    'US-CA-RED': 1.02,       # Redding
    'US-CA-STO': 1.04,       # Stockton
    'US-CA-SRO': 1.28,       # Santa Rosa
}

# Hawaii regional cost factors
HI_REGIONAL_FACTORS: Dict[str, float] = {
    'US-HI': 1.45,           # State average
    'US-HI-HON': 1.45,       # Honolulu/Oahu
    'US-HI-MAU': 1.50,       # Maui
    'US-HI-BIG': 1.48,       # Big Island (Hawaii)
    'US-HI-KAU': 1.52,       # Kauai
}

# Combined regional factors
REGIONAL_FACTORS: Dict[str, float] = {
    **CA_REGIONAL_FACTORS,
    **HI_REGIONAL_FACTORS,
    'US-NATIONAL': 1.00,     # National baseline
}


# =============================================================================
# CLIMATE ZONE TO REGION MAPPING
# =============================================================================

# CBECC Climate Zone to Region Code mapping
# Based on geographic proximity to major metro areas
CZ_TO_REGION: Dict[str, str] = {
    # Northern California
    'CZ01': 'US-CA-RED',     # Arcata (North Coast) → Redding region
    'CZ02': 'US-CA-SRO',     # Santa Rosa → Santa Rosa
    'CZ03': 'US-CA-OAK',     # Oakland → Oakland
    'CZ04': 'US-CA-SJ',      # Sunnyvale (South Bay) → San Jose
    'CZ05': 'US-CA-SLO',     # Santa Maria → San Luis Obispo

    # Southern California Coastal
    'CZ06': 'US-CA-LA',      # Los Angeles (Torrance) → LA
    'CZ07': 'US-CA-SD',      # San Diego → San Diego
    'CZ08': 'US-CA-LA',      # El Toro → LA (south Orange County)
    'CZ09': 'US-CA-LA',      # Pasadena → LA

    # Southern California Inland
    'CZ10': 'US-CA-RIV',     # Riverside → Riverside
    'CZ11': 'US-CA-RED',     # Red Bluff → Redding
    'CZ12': 'US-CA-SAC',     # Sacramento → Sacramento
    'CZ13': 'US-CA-FRE',     # Fresno → Fresno
    'CZ14': 'US-CA-BAK',     # Palmdale → Bakersfield region
    'CZ15': 'US-CA-RIV',     # Palm Springs → Riverside
    'CZ16': 'US-CA-RED',     # Mt. Shasta → Redding

    # Hawaii Climate Zones
    'HI01': 'US-HI-HON',     # Hawaii CZ1 → Honolulu
    'HI02': 'US-HI-HON',     # Hawaii CZ2 → Honolulu
    'HI03': 'US-HI-MAU',     # Hawaii CZ3 → Maui
    'HI04': 'US-HI-BIG',     # Hawaii CZ4 → Big Island
}

# Alternative numeric-only format
CZ_NUM_TO_REGION: Dict[int, str] = {
    1: 'US-CA-RED', 2: 'US-CA-SRO', 3: 'US-CA-OAK', 4: 'US-CA-SJ',
    5: 'US-CA-SLO', 6: 'US-CA-LA', 7: 'US-CA-SD', 8: 'US-CA-LA',
    9: 'US-CA-LA', 10: 'US-CA-RIV', 11: 'US-CA-RED', 12: 'US-CA-SAC',
    13: 'US-CA-FRE', 14: 'US-CA-BAK', 15: 'US-CA-RIV', 16: 'US-CA-RED',
}


# =============================================================================
# REGION TO UTILITY MAPPING
# =============================================================================

class UtilityCode(Enum):
    """California and Hawaii utility codes."""
    # California IOUs
    PGE = "PGE"       # Pacific Gas & Electric
    SCE = "SCE"       # Southern California Edison
    SDGE = "SDGE"     # San Diego Gas & Electric

    # California POUs
    SMUD = "SMUD"     # Sacramento Municipal Utility District
    LADWP = "LADWP"   # Los Angeles Dept of Water & Power

    # Hawaii utilities
    HECO = "HECO"     # Hawaiian Electric (Oahu)
    MECO = "MECO"     # Maui Electric Company
    HELCO = "HELCO"   # Hawaii Electric Light (Big Island)
    KIUC = "KIUC"     # Kauai Island Utility Cooperative


# Region to primary electric utility mapping
REGION_TO_UTILITY: Dict[str, str] = {
    # PG&E territory (Northern & Central California)
    'US-CA-SF': 'PGE',
    'US-CA-OAK': 'PGE',
    'US-CA-SJ': 'PGE',
    'US-CA-SAC': 'PGE',  # Note: SMUD serves Sacramento city proper
    'US-CA-FRE': 'PGE',
    'US-CA-BAK': 'PGE',
    'US-CA-STO': 'PGE',
    'US-CA-SRO': 'PGE',
    'US-CA-RED': 'PGE',
    'US-CA-MON': 'PGE',
    'US-CA-SLO': 'PGE',

    # SCE territory (Southern California)
    'US-CA-LA': 'SCE',
    'US-CA-OC': 'SCE',
    'US-CA-RIV': 'SCE',
    'US-CA-SB': 'SCE',
    'US-CA-VEN': 'SCE',

    # SDG&E territory
    'US-CA-SD': 'SDGE',

    # Hawaii utilities
    'US-HI': 'HECO',
    'US-HI-HON': 'HECO',
    'US-HI-MAU': 'MECO',
    'US-HI-BIG': 'HELCO',
    'US-HI-KAU': 'KIUC',
}

# Region to gas utility mapping
REGION_TO_GAS_UTILITY: Dict[str, str] = {
    # SoCalGas territory
    'US-CA-LA': 'SOCALGAS',
    'US-CA-OC': 'SOCALGAS',
    'US-CA-RIV': 'SOCALGAS',
    'US-CA-SB': 'SOCALGAS',
    'US-CA-VEN': 'SOCALGAS',
    'US-CA-BAK': 'SOCALGAS',
    'US-CA-FRE': 'SOCALGAS',

    # PG&E gas territory
    'US-CA-SF': 'PGE',
    'US-CA-OAK': 'PGE',
    'US-CA-SJ': 'PGE',
    'US-CA-SAC': 'PGE',
    'US-CA-STO': 'PGE',
    'US-CA-SRO': 'PGE',
    'US-CA-RED': 'PGE',
    'US-CA-MON': 'PGE',
    'US-CA-SLO': 'PGE',

    # SDG&E gas
    'US-CA-SD': 'SDGE',

    # Hawaii (no piped natural gas)
    'US-HI': 'PROPANE',
    'US-HI-HON': 'PROPANE',
    'US-HI-MAU': 'PROPANE',
    'US-HI-BIG': 'PROPANE',
    'US-HI-KAU': 'PROPANE',
}


# =============================================================================
# DEFAULT RATE SELECTION
# =============================================================================

# Residential default rates by utility
RESIDENTIAL_RATES: Dict[str, str] = {
    'PGE': 'PGE-E-TOU-C',       # PG&E Time-of-Use (Peak Pricing 4-9pm)
    'SCE': 'SCE-TOU-D-4-9PM',   # SCE TOU-D (4-9pm peak)
    'SDGE': 'SDGE-TOU-DR1',     # SDG&E TOU-DR1
    'SMUD': 'SMUD-R-TOU',       # SMUD Residential TOU
    'LADWP': 'LADWP-R-1A',      # LADWP Residential
    'HECO': 'HECO-R-TOU',       # HECO Residential TOU
    'MECO': 'MECO-R-TIER',      # MECO Residential Tiered
    'HELCO': 'HELCO-R-TIER',    # HELCO Residential Tiered
    'KIUC': 'KIUC-D-TIER',      # KIUC Schedule D
}

# Commercial default rates by utility
COMMERCIAL_RATES: Dict[str, str] = {
    'PGE': 'PGE-B-20',          # PG&E Medium General Demand TOU
    'SCE': 'SCE-TOU-GS-3',      # SCE TOU-GS-3 Large
    'SDGE': 'SDGE-AL-TOU',      # SDG&E AL-TOU Large
    'SMUD': 'SMUD-GS-TOU',      # SMUD General Service TOU
    'LADWP': 'LADWP-A-2',       # LADWP Commercial A-2
    'HECO': 'HECO-G-TOU',       # HECO General Service TOU
    'MECO': 'MECO-J-TIER',      # MECO General Service
    'HELCO': 'HELCO-J-TIER',    # HELCO General Service
    'KIUC': 'KIUC-G-TIER',      # KIUC Schedule G
}


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def get_regional_factor(region_code: str) -> float:
    """
    Get construction cost adjustment factor for a region.

    Args:
        region_code: Region code (e.g., 'US-CA-SF', 'US-HI-MAU')

    Returns:
        Cost factor relative to national average (1.0)
    """
    return REGIONAL_FACTORS.get(region_code, 1.0)


def get_region_from_climate_zone(climate_zone: str) -> str:
    """
    Map CBECC climate zone to region code.

    Args:
        climate_zone: Climate zone string (e.g., 'CZ12', 'CZ03', '12', 'HI01')

    Returns:
        Region code (e.g., 'US-CA-SAC')
    """
    # Normalize input
    cz = climate_zone.upper().strip()

    # Try direct lookup
    if cz in CZ_TO_REGION:
        return CZ_TO_REGION[cz]

    # Try with 'CZ' prefix
    if not cz.startswith('CZ') and not cz.startswith('HI'):
        cz_prefixed = f'CZ{cz.zfill(2)}'
        if cz_prefixed in CZ_TO_REGION:
            return CZ_TO_REGION[cz_prefixed]

    # Try numeric lookup
    try:
        cz_num = int(cz.replace('CZ', ''))
        if cz_num in CZ_NUM_TO_REGION:
            return CZ_NUM_TO_REGION[cz_num]
    except ValueError:
        pass

    # Default to California state average
    return 'US-CA'


def get_utility_for_region(region_code: str, fuel_type: str = 'electric') -> str:
    """
    Get primary utility for a region.

    Args:
        region_code: Region code (e.g., 'US-CA-SF')
        fuel_type: 'electric' or 'gas'

    Returns:
        Utility code (e.g., 'PGE', 'SCE')
    """
    if fuel_type == 'gas':
        return REGION_TO_GAS_UTILITY.get(region_code, 'DEFAULT')
    return REGION_TO_UTILITY.get(region_code, 'DEFAULT')


def get_default_rate_id(
    region_code: str,
    building_type: str = 'residential'
) -> str:
    """
    Get default rate ID for a region and building type.

    Args:
        region_code: Region code (e.g., 'US-CA-SF')
        building_type: 'residential' or 'commercial'

    Returns:
        Rate ID (e.g., 'PGE-E-TOU-C', 'SCE-TOU-GS-3')
    """
    utility = get_utility_for_region(region_code, 'electric')

    if building_type.lower() in ('residential', 'multifamily', 'dwelling'):
        return RESIDENTIAL_RATES.get(utility, 'DEFAULT-ELEC-US')
    else:
        return COMMERCIAL_RATES.get(utility, 'DEFAULT-ELEC-US')


def list_regions_by_state(state: str = 'CA') -> List[str]:
    """
    List all region codes for a state.

    Args:
        state: State abbreviation ('CA' or 'HI')

    Returns:
        List of region codes
    """
    prefix = f'US-{state.upper()}'
    return [code for code in REGIONAL_FACTORS if code.startswith(prefix)]


def get_region_info(region_code: str) -> Dict[str, any]:
    """
    Get comprehensive info for a region.

    Args:
        region_code: Region code (e.g., 'US-CA-SF')

    Returns:
        Dict with factor, utility, rates, etc.
    """
    return {
        'region_code': region_code,
        'cost_factor': get_regional_factor(region_code),
        'electric_utility': get_utility_for_region(region_code, 'electric'),
        'gas_utility': get_utility_for_region(region_code, 'gas'),
        'default_residential_rate': get_default_rate_id(region_code, 'residential'),
        'default_commercial_rate': get_default_rate_id(region_code, 'commercial'),
    }


def get_climate_zone_info(climate_zone: str) -> Dict[str, any]:
    """
    Get region info from climate zone.

    Args:
        climate_zone: Climate zone (e.g., 'CZ12', '12')

    Returns:
        Dict with region info including mappings
    """
    region = get_region_from_climate_zone(climate_zone)
    info = get_region_info(region)
    info['climate_zone'] = climate_zone
    return info


# =============================================================================
# REGION METADATA
# =============================================================================

@dataclass
class RegionMetadata:
    """Metadata for a region."""
    code: str
    name: str
    state: str
    cost_factor: float
    electric_utility: str
    gas_utility: str
    climate_zones: List[str] = field(default_factory=list)


REGION_METADATA: Dict[str, RegionMetadata] = {
    'US-CA-SF': RegionMetadata(
        code='US-CA-SF', name='San Francisco', state='CA',
        cost_factor=1.38, electric_utility='PGE', gas_utility='PGE',
        climate_zones=['CZ03']
    ),
    'US-CA-OAK': RegionMetadata(
        code='US-CA-OAK', name='Oakland', state='CA',
        cost_factor=1.35, electric_utility='PGE', gas_utility='PGE',
        climate_zones=['CZ03']
    ),
    'US-CA-SJ': RegionMetadata(
        code='US-CA-SJ', name='San Jose', state='CA',
        cost_factor=1.36, electric_utility='PGE', gas_utility='PGE',
        climate_zones=['CZ04']
    ),
    'US-CA-LA': RegionMetadata(
        code='US-CA-LA', name='Los Angeles', state='CA',
        cost_factor=1.22, electric_utility='SCE', gas_utility='SOCALGAS',
        climate_zones=['CZ06', 'CZ08', 'CZ09']
    ),
    'US-CA-SD': RegionMetadata(
        code='US-CA-SD', name='San Diego', state='CA',
        cost_factor=1.18, electric_utility='SDGE', gas_utility='SDGE',
        climate_zones=['CZ07']
    ),
    'US-CA-OC': RegionMetadata(
        code='US-CA-OC', name='Orange County', state='CA',
        cost_factor=1.20, electric_utility='SCE', gas_utility='SOCALGAS',
        climate_zones=['CZ08']
    ),
    'US-CA-SAC': RegionMetadata(
        code='US-CA-SAC', name='Sacramento', state='CA',
        cost_factor=1.12, electric_utility='PGE', gas_utility='PGE',
        climate_zones=['CZ12']
    ),
    'US-CA-FRE': RegionMetadata(
        code='US-CA-FRE', name='Fresno', state='CA',
        cost_factor=1.05, electric_utility='PGE', gas_utility='SOCALGAS',
        climate_zones=['CZ13']
    ),
    'US-CA-BAK': RegionMetadata(
        code='US-CA-BAK', name='Bakersfield', state='CA',
        cost_factor=1.03, electric_utility='PGE', gas_utility='SOCALGAS',
        climate_zones=['CZ14']
    ),
    'US-CA-RIV': RegionMetadata(
        code='US-CA-RIV', name='Riverside', state='CA',
        cost_factor=1.08, electric_utility='SCE', gas_utility='SOCALGAS',
        climate_zones=['CZ10', 'CZ15']
    ),
    'US-CA-SB': RegionMetadata(
        code='US-CA-SB', name='Santa Barbara', state='CA',
        cost_factor=1.15, electric_utility='SCE', gas_utility='SOCALGAS',
        climate_zones=['CZ05']
    ),
    'US-CA-VEN': RegionMetadata(
        code='US-CA-VEN', name='Ventura', state='CA',
        cost_factor=1.12, electric_utility='SCE', gas_utility='SOCALGAS',
        climate_zones=['CZ06']
    ),
    'US-CA-MON': RegionMetadata(
        code='US-CA-MON', name='Monterey', state='CA',
        cost_factor=1.10, electric_utility='PGE', gas_utility='PGE',
        climate_zones=['CZ04', 'CZ05']
    ),
    'US-CA-SLO': RegionMetadata(
        code='US-CA-SLO', name='San Luis Obispo', state='CA',
        cost_factor=1.08, electric_utility='PGE', gas_utility='SOCALGAS',
        climate_zones=['CZ05']
    ),
    'US-CA-RED': RegionMetadata(
        code='US-CA-RED', name='Redding', state='CA',
        cost_factor=1.02, electric_utility='PGE', gas_utility='PGE',
        climate_zones=['CZ01', 'CZ11', 'CZ16']
    ),
    'US-CA-STO': RegionMetadata(
        code='US-CA-STO', name='Stockton', state='CA',
        cost_factor=1.04, electric_utility='PGE', gas_utility='PGE',
        climate_zones=['CZ12']
    ),
    'US-CA-SRO': RegionMetadata(
        code='US-CA-SRO', name='Santa Rosa', state='CA',
        cost_factor=1.28, electric_utility='PGE', gas_utility='PGE',
        climate_zones=['CZ02']
    ),
    # Hawaii regions
    'US-HI-HON': RegionMetadata(
        code='US-HI-HON', name='Honolulu (Oahu)', state='HI',
        cost_factor=1.45, electric_utility='HECO', gas_utility='PROPANE',
        climate_zones=['HI01', 'HI02']
    ),
    'US-HI-MAU': RegionMetadata(
        code='US-HI-MAU', name='Maui', state='HI',
        cost_factor=1.50, electric_utility='MECO', gas_utility='PROPANE',
        climate_zones=['HI03']
    ),
    'US-HI-BIG': RegionMetadata(
        code='US-HI-BIG', name='Big Island', state='HI',
        cost_factor=1.48, electric_utility='HELCO', gas_utility='PROPANE',
        climate_zones=['HI04']
    ),
    'US-HI-KAU': RegionMetadata(
        code='US-HI-KAU', name='Kauai', state='HI',
        cost_factor=1.52, electric_utility='KIUC', gas_utility='PROPANE',
        climate_zones=[]
    ),
}


def get_region_metadata(region_code: str) -> Optional[RegionMetadata]:
    """Get metadata for a region."""
    return REGION_METADATA.get(region_code)


def find_region_by_climate_zone(climate_zone: str) -> Optional[RegionMetadata]:
    """Find region metadata by climate zone."""
    region_code = get_region_from_climate_zone(climate_zone)
    return get_region_metadata(region_code)


# =============================================================================
# COST CALCULATION HELPERS
# =============================================================================

def apply_regional_factor(
    base_cost: float,
    region_code: str
) -> float:
    """
    Apply regional cost factor to a base cost.

    Args:
        base_cost: National average cost
        region_code: Region code

    Returns:
        Regionally adjusted cost
    """
    factor = get_regional_factor(region_code)
    return base_cost * factor


def get_regional_system_cost(
    system_code: str,
    region_code: str,
    quantity: float = 1.0,
    costdb: Optional[any] = None
) -> Tuple[Optional[float], float]:
    """
    Get system cost adjusted for region.

    Args:
        system_code: System code from CostDB (e.g., 'HP-SPLIT-3T-SEER15')
        region_code: Region code (e.g., 'US-CA-SF')
        quantity: Quantity/size multiplier
        costdb: Optional CostDBv06 instance

    Returns:
        Tuple of (adjusted_cost, regional_factor)
    """
    factor = get_regional_factor(region_code)

    if costdb is not None:
        cost = costdb.get_system_cost(system_code, quantity, region_code)
        return cost, factor

    # Without costdb, return just the factor
    return None, factor


def estimate_utility_costs(
    annual_kwh: float,
    annual_therm: float,
    region_code: str,
    building_type: str = 'residential'
) -> Dict[str, float]:
    """
    Estimate annual utility costs for a region.

    Uses average rates - for detailed TOU analysis use tariffs.py.

    Args:
        annual_kwh: Annual electricity consumption
        annual_therm: Annual gas consumption
        region_code: Region code
        building_type: 'residential' or 'commercial'

    Returns:
        Dict with elec_cost, gas_cost, total_cost
    """
    # Average blended rates by utility (residential, $/kWh)
    ELEC_RATES = {
        'PGE': 0.28, 'SCE': 0.26, 'SDGE': 0.35,
        'SMUD': 0.18, 'LADWP': 0.16,
        'HECO': 0.40, 'MECO': 0.42, 'HELCO': 0.44, 'KIUC': 0.43,
        'DEFAULT': 0.25
    }

    # Gas rates ($/therm)
    GAS_RATES = {
        'PGE': 1.80, 'SOCALGAS': 1.65, 'SDGE': 1.90,
        'PROPANE': 3.50,  # Hawaii propane equivalent
        'DEFAULT': 1.75
    }

    utility = get_utility_for_region(region_code, 'electric')
    gas_utility = get_utility_for_region(region_code, 'gas')

    elec_rate = ELEC_RATES.get(utility, ELEC_RATES['DEFAULT'])
    gas_rate = GAS_RATES.get(gas_utility, GAS_RATES['DEFAULT'])

    # Commercial rates are typically lower per kWh
    if building_type.lower() == 'commercial':
        elec_rate *= 0.85
        gas_rate *= 0.90

    elec_cost = annual_kwh * elec_rate
    gas_cost = annual_therm * gas_rate

    return {
        'elec_cost': elec_cost,
        'gas_cost': gas_cost,
        'total_cost': elec_cost + gas_cost,
        'elec_rate': elec_rate,
        'gas_rate': gas_rate,
        'utility': utility,
        'gas_utility': gas_utility,
    }
