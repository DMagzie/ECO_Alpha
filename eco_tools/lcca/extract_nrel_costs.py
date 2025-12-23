"""
NREL Cost Database Generator
============================

Generates CostDB_v0.06_NREL.xlsx from free NREL data sources.

Data Sources:
- NREL BEopt: HVAC and DHW system costs (embedded from public documentation)
- NREL ATB 2024: PV and battery costs
- BLS PPI: Cost escalation indices
- Public utility tariffs: Rate structures
- ENR CCI: Regional cost factors

Usage:
    python -m eco_tools.lcca.extract_nrel_costs --output CostDB_v0.06_NREL.xlsx

    # Or from the eco_tools/lcca directory:
    python extract_nrel_costs.py

References:
    - NREL BEopt: https://beopt.nrel.gov/
    - NREL ATB 2024: https://atb.nrel.gov/
    - BLS PPI: https://www.bls.gov/ppi/
    - OpenEI: https://openei.org/wiki/Utility_Rate_Database
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Check for pandas/openpyxl availability
try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False
    logger.warning("pandas not available - Excel generation disabled")


# =============================================================================
# NREL BEopt Cost Data (2020 baseline, publicly available)
# Source: NREL BEopt cost library documentation
# =============================================================================

BEOPT_HVAC_COSTS: Dict[str, Dict[str, Any]] = {
    # Heat Pumps - Split Systems
    'HP-SPLIT-2T-SEER14': {
        'description': 'Air-Source Heat Pump, Split, 2 Ton, SEER 14',
        'base_cost': 4200,
        'unit': 'each',
        'capacity': 2,
        'capacity_unit': 'tons',
        'category': 'HVAC',
        'subcategory': 'Heat Pump',
        'source': 'NREL BEopt 2020',
    },
    'HP-SPLIT-3T-SEER15': {
        'description': 'Air-Source Heat Pump, Split, 3 Ton, SEER 15',
        'base_cost': 5800,
        'unit': 'each',
        'capacity': 3,
        'capacity_unit': 'tons',
        'category': 'HVAC',
        'subcategory': 'Heat Pump',
        'source': 'NREL BEopt 2020',
    },
    'HP-SPLIT-4T-SEER16': {
        'description': 'Air-Source Heat Pump, Split, 4 Ton, SEER 16',
        'base_cost': 7400,
        'unit': 'each',
        'capacity': 4,
        'capacity_unit': 'tons',
        'category': 'HVAC',
        'subcategory': 'Heat Pump',
        'source': 'NREL BEopt 2020',
    },
    'HP-SPLIT-5T-SEER16': {
        'description': 'Air-Source Heat Pump, Split, 5 Ton, SEER 16',
        'base_cost': 8900,
        'unit': 'each',
        'capacity': 5,
        'capacity_unit': 'tons',
        'category': 'HVAC',
        'subcategory': 'Heat Pump',
        'source': 'NREL BEopt 2020',
    },

    # Mini-Split Heat Pumps
    'MINISPLIT-1T-SEER20': {
        'description': 'Mini-Split Heat Pump, 1 Ton, SEER 20',
        'base_cost': 3200,
        'unit': 'each',
        'capacity': 1,
        'capacity_unit': 'tons',
        'category': 'HVAC',
        'subcategory': 'Mini-Split',
        'source': 'NREL BEopt 2020',
    },
    'MINISPLIT-1.5T-SEER22': {
        'description': 'Mini-Split Heat Pump, 1.5 Ton, SEER 22',
        'base_cost': 4100,
        'unit': 'each',
        'capacity': 1.5,
        'capacity_unit': 'tons',
        'category': 'HVAC',
        'subcategory': 'Mini-Split',
        'source': 'NREL BEopt 2020',
    },
    'MINISPLIT-2T-SEER20': {
        'description': 'Mini-Split Heat Pump, 2 Ton, SEER 20',
        'base_cost': 4800,
        'unit': 'each',
        'capacity': 2,
        'capacity_unit': 'tons',
        'category': 'HVAC',
        'subcategory': 'Mini-Split',
        'source': 'NREL BEopt 2020',
    },

    # Gas Furnaces
    'FURNACE-GAS-80AFUE': {
        'description': 'Gas Furnace, 80% AFUE, 60 kBtu',
        'base_cost': 2800,
        'unit': 'each',
        'capacity': 60,
        'capacity_unit': 'kBtu/h',
        'category': 'HVAC',
        'subcategory': 'Furnace',
        'source': 'NREL BEopt 2020',
    },
    'FURNACE-GAS-92AFUE': {
        'description': 'Gas Furnace, 92% AFUE, Condensing, 60 kBtu',
        'base_cost': 3400,
        'unit': 'each',
        'capacity': 60,
        'capacity_unit': 'kBtu/h',
        'category': 'HVAC',
        'subcategory': 'Furnace',
        'source': 'NREL BEopt 2020',
    },
    'FURNACE-GAS-96AFUE': {
        'description': 'Gas Furnace, 96% AFUE, High-Efficiency, 60 kBtu',
        'base_cost': 4200,
        'unit': 'each',
        'capacity': 60,
        'capacity_unit': 'kBtu/h',
        'category': 'HVAC',
        'subcategory': 'Furnace',
        'source': 'NREL BEopt 2020',
    },

    # Central AC
    'AC-CENTRAL-SEER14': {
        'description': 'Central AC, Split, 3 Ton, SEER 14',
        'base_cost': 3500,
        'unit': 'each',
        'capacity': 3,
        'capacity_unit': 'tons',
        'category': 'HVAC',
        'subcategory': 'AC',
        'source': 'NREL BEopt 2020',
    },
    'AC-CENTRAL-SEER16': {
        'description': 'Central AC, Split, 3 Ton, SEER 16',
        'base_cost': 4200,
        'unit': 'each',
        'capacity': 3,
        'capacity_unit': 'tons',
        'category': 'HVAC',
        'subcategory': 'AC',
        'source': 'NREL BEopt 2020',
    },
    'AC-CENTRAL-SEER18': {
        'description': 'Central AC, Split, 3 Ton, SEER 18',
        'base_cost': 5100,
        'unit': 'each',
        'capacity': 3,
        'capacity_unit': 'tons',
        'category': 'HVAC',
        'subcategory': 'AC',
        'source': 'NREL BEopt 2020',
    },

    # VRF Systems (Commercial)
    'VRF-OUTDOOR-4T': {
        'description': 'VRF Outdoor Unit, 4 Ton',
        'base_cost': 12000,
        'unit': 'each',
        'capacity': 4,
        'capacity_unit': 'tons',
        'category': 'HVAC',
        'subcategory': 'VRF',
        'source': 'NREL BEopt 2020',
    },
    'VRF-OUTDOOR-8T': {
        'description': 'VRF Outdoor Unit, 8 Ton',
        'base_cost': 20000,
        'unit': 'each',
        'capacity': 8,
        'capacity_unit': 'tons',
        'category': 'HVAC',
        'subcategory': 'VRF',
        'source': 'NREL BEopt 2020',
    },
    'VRF-INDOOR-WALL': {
        'description': 'VRF Indoor Wall-Mount Unit',
        'base_cost': 1200,
        'unit': 'each',
        'capacity': 1,
        'capacity_unit': 'tons',
        'category': 'HVAC',
        'subcategory': 'VRF',
        'source': 'NREL BEopt 2020',
    },

    # PTAC/PTHP
    'PTAC-9K-EER11': {
        'description': 'PTAC, 9,000 BTU, EER 11',
        'base_cost': 1100,
        'unit': 'each',
        'capacity': 0.75,
        'capacity_unit': 'tons',
        'category': 'HVAC',
        'subcategory': 'PTAC',
        'source': 'NREL BEopt 2020',
    },
    'PTHP-9K-EER11': {
        'description': 'PTHP, 9,000 BTU, EER 11, Heat Pump',
        'base_cost': 1300,
        'unit': 'each',
        'capacity': 0.75,
        'capacity_unit': 'tons',
        'category': 'HVAC',
        'subcategory': 'PTHP',
        'source': 'NREL BEopt 2020',
    },
}

BEOPT_DHW_COSTS: Dict[str, Dict[str, Any]] = {
    # Heat Pump Water Heaters
    'HPWH-50GAL-EF2.3': {
        'description': 'Heat Pump Water Heater, 50 gal, UEF 2.3',
        'base_cost': 1800,
        'unit': 'each',
        'capacity': 50,
        'capacity_unit': 'gallons',
        'category': 'DHW',
        'subcategory': 'HPWH',
        'source': 'NREL BEopt 2020',
    },
    'HPWH-65GAL-EF3.0': {
        'description': 'Heat Pump Water Heater, 65 gal, UEF 3.0',
        'base_cost': 2400,
        'unit': 'each',
        'capacity': 65,
        'capacity_unit': 'gallons',
        'category': 'DHW',
        'subcategory': 'HPWH',
        'source': 'NREL BEopt 2020',
    },
    'HPWH-80GAL-EF2.8': {
        'description': 'Heat Pump Water Heater, 80 gal, UEF 2.8',
        'base_cost': 2800,
        'unit': 'each',
        'capacity': 80,
        'capacity_unit': 'gallons',
        'category': 'DHW',
        'subcategory': 'HPWH',
        'source': 'NREL BEopt 2020',
    },

    # Electric Storage Water Heaters
    'WH-ELEC-50GAL-EF0.92': {
        'description': 'Electric Storage Water Heater, 50 gal, UEF 0.92',
        'base_cost': 800,
        'unit': 'each',
        'capacity': 50,
        'capacity_unit': 'gallons',
        'category': 'DHW',
        'subcategory': 'Electric',
        'source': 'NREL BEopt 2020',
    },
    'WH-ELEC-80GAL-EF0.93': {
        'description': 'Electric Storage Water Heater, 80 gal, UEF 0.93',
        'base_cost': 1100,
        'unit': 'each',
        'capacity': 80,
        'capacity_unit': 'gallons',
        'category': 'DHW',
        'subcategory': 'Electric',
        'source': 'NREL BEopt 2020',
    },

    # Gas Water Heaters
    'WH-GAS-TANK-40GAL-EF0.62': {
        'description': 'Gas Storage Water Heater, 40 gal, UEF 0.62',
        'base_cost': 900,
        'unit': 'each',
        'capacity': 40,
        'capacity_unit': 'gallons',
        'category': 'DHW',
        'subcategory': 'Gas Tank',
        'source': 'NREL BEopt 2020',
    },
    'WH-GAS-TANK-50GAL-EF0.67': {
        'description': 'Gas Storage Water Heater, 50 gal, UEF 0.67',
        'base_cost': 1000,
        'unit': 'each',
        'capacity': 50,
        'capacity_unit': 'gallons',
        'category': 'DHW',
        'subcategory': 'Gas Tank',
        'source': 'NREL BEopt 2020',
    },
    'WH-GAS-TANKLESS-EF0.82': {
        'description': 'Gas Tankless Water Heater, UEF 0.82',
        'base_cost': 1200,
        'unit': 'each',
        'capacity': 6.6,
        'capacity_unit': 'GPM',
        'category': 'DHW',
        'subcategory': 'Gas Tankless',
        'source': 'NREL BEopt 2020',
    },
    'WH-GAS-TANKLESS-EF0.95': {
        'description': 'Gas Tankless Water Heater, Condensing, UEF 0.95',
        'base_cost': 1800,
        'unit': 'each',
        'capacity': 8.0,
        'capacity_unit': 'GPM',
        'category': 'DHW',
        'subcategory': 'Gas Tankless',
        'source': 'NREL BEopt 2020',
    },
}


# =============================================================================
# NREL ATB 2024 PV/Battery Cost Data
# Source: NREL Annual Technology Baseline 2024
# =============================================================================

ATB_2024_COSTS: Dict[str, Dict[str, Any]] = {
    # Residential PV
    'PV-RES-ROOF-2024': {
        'description': 'Residential Rooftop PV System (2024)',
        'base_cost': 2.50,
        'unit': '$/Wdc',
        'capacity': 1,
        'capacity_unit': 'kWdc',
        'category': 'PV',
        'subcategory': 'Residential',
        'source': 'NREL ATB 2024',
    },
    'PV-RES-CARPORT-2024': {
        'description': 'Residential Carport PV System (2024)',
        'base_cost': 2.80,
        'unit': '$/Wdc',
        'capacity': 1,
        'capacity_unit': 'kWdc',
        'category': 'PV',
        'subcategory': 'Residential',
        'source': 'NREL ATB 2024',
    },

    # Commercial PV
    'PV-COM-ROOF-2024': {
        'description': 'Commercial Rooftop PV System (2024)',
        'base_cost': 1.80,
        'unit': '$/Wdc',
        'capacity': 1,
        'capacity_unit': 'kWdc',
        'category': 'PV',
        'subcategory': 'Commercial',
        'source': 'NREL ATB 2024',
    },
    'PV-COM-GROUND-2024': {
        'description': 'Commercial Ground-Mount PV System (2024)',
        'base_cost': 1.40,
        'unit': '$/Wdc',
        'capacity': 1,
        'capacity_unit': 'kWdc',
        'category': 'PV',
        'subcategory': 'Commercial',
        'source': 'NREL ATB 2024',
    },
    'PV-COM-CARPORT-2024': {
        'description': 'Commercial Carport PV System (2024)',
        'base_cost': 2.20,
        'unit': '$/Wdc',
        'capacity': 1,
        'capacity_unit': 'kWdc',
        'category': 'PV',
        'subcategory': 'Commercial',
        'source': 'NREL ATB 2024',
    },

    # Battery Storage
    'BATT-RES-LITHIUM-2024': {
        'description': 'Residential Li-ion Battery Storage (2024)',
        'base_cost': 800,
        'unit': '$/kWh',
        'capacity': 1,
        'capacity_unit': 'kWh',
        'category': 'Battery',
        'subcategory': 'Residential',
        'source': 'NREL ATB 2024',
    },
    'BATT-COM-LITHIUM-2024': {
        'description': 'Commercial Li-ion Battery Storage (2024)',
        'base_cost': 650,
        'unit': '$/kWh',
        'capacity': 1,
        'capacity_unit': 'kWh',
        'category': 'Battery',
        'subcategory': 'Commercial',
        'source': 'NREL ATB 2024',
    },
    'BATT-UTILITY-LITHIUM-2024': {
        'description': 'Utility-Scale Li-ion Battery Storage (2024)',
        'base_cost': 450,
        'unit': '$/kWh',
        'capacity': 1,
        'capacity_unit': 'kWh',
        'category': 'Battery',
        'subcategory': 'Utility',
        'source': 'NREL ATB 2024',
    },
}


# =============================================================================
# Regional Cost Factors (ENR Construction Cost Index based)
# Source: Engineering News-Record Construction Cost Index 2024
# =============================================================================

REGIONAL_FACTORS: Dict[str, Dict[str, Any]] = {
    # National baseline
    'US-NATIONAL': {
        'factor': 1.00,
        'state': 'US',
        'city': 'National Average',
        'notes': 'Baseline reference',
    },

    # California (18 regions)
    'US-CA': {
        'factor': 1.10,
        'state': 'CA',
        'city': 'State Average',
        'notes': 'California statewide average',
    },
    'US-CA-SF': {
        'factor': 1.38,
        'state': 'CA',
        'city': 'San Francisco',
        'notes': 'Bay Area premium market',
    },
    'US-CA-OAK': {
        'factor': 1.35,
        'state': 'CA',
        'city': 'Oakland',
        'notes': 'East Bay',
    },
    'US-CA-SJ': {
        'factor': 1.36,
        'state': 'CA',
        'city': 'San Jose',
        'notes': 'South Bay / Silicon Valley',
    },
    'US-CA-SRO': {
        'factor': 1.28,
        'state': 'CA',
        'city': 'Santa Rosa',
        'notes': 'North Bay / Wine Country',
    },
    'US-CA-LA': {
        'factor': 1.22,
        'state': 'CA',
        'city': 'Los Angeles',
        'notes': 'Greater Los Angeles',
    },
    'US-CA-OC': {
        'factor': 1.20,
        'state': 'CA',
        'city': 'Orange County',
        'notes': 'Orange County',
    },
    'US-CA-SD': {
        'factor': 1.18,
        'state': 'CA',
        'city': 'San Diego',
        'notes': 'San Diego County',
    },
    'US-CA-SB': {
        'factor': 1.15,
        'state': 'CA',
        'city': 'Santa Barbara',
        'notes': 'Central Coast',
    },
    'US-CA-VEN': {
        'factor': 1.12,
        'state': 'CA',
        'city': 'Ventura',
        'notes': 'Ventura County',
    },
    'US-CA-SAC': {
        'factor': 1.12,
        'state': 'CA',
        'city': 'Sacramento',
        'notes': 'State Capital region',
    },
    'US-CA-MON': {
        'factor': 1.10,
        'state': 'CA',
        'city': 'Monterey',
        'notes': 'Central Coast',
    },
    'US-CA-RIV': {
        'factor': 1.08,
        'state': 'CA',
        'city': 'Riverside',
        'notes': 'Inland Empire',
    },
    'US-CA-SLO': {
        'factor': 1.08,
        'state': 'CA',
        'city': 'San Luis Obispo',
        'notes': 'Central Coast',
    },
    'US-CA-FRE': {
        'factor': 1.05,
        'state': 'CA',
        'city': 'Fresno',
        'notes': 'Central Valley',
    },
    'US-CA-STO': {
        'factor': 1.04,
        'state': 'CA',
        'city': 'Stockton',
        'notes': 'Central Valley',
    },
    'US-CA-BAK': {
        'factor': 1.03,
        'state': 'CA',
        'city': 'Bakersfield',
        'notes': 'Southern Central Valley',
    },
    'US-CA-RED': {
        'factor': 1.02,
        'state': 'CA',
        'city': 'Redding',
        'notes': 'Northern California',
    },

    # Hawaii (4 regions)
    'US-HI': {
        'factor': 1.45,
        'state': 'HI',
        'city': 'State Average',
        'notes': 'Hawaii statewide average',
    },
    'US-HI-HON': {
        'factor': 1.45,
        'state': 'HI',
        'city': 'Honolulu',
        'notes': 'Oahu',
    },
    'US-HI-MAU': {
        'factor': 1.50,
        'state': 'HI',
        'city': 'Maui',
        'notes': 'Maui County',
    },
    'US-HI-BIG': {
        'factor': 1.48,
        'state': 'HI',
        'city': 'Big Island',
        'notes': 'Hawaii County',
    },
}


# =============================================================================
# Utility Rate Structures (from public tariff books 2024)
# =============================================================================

UTILITY_RATES: Dict[str, Dict[str, Any]] = {
    # PG&E (Northern California)
    'PGE-E1-TIER': {
        'utility': 'Pacific Gas & Electric',
        'utility_code': 'PGE',
        'rate_name': 'E-1 Residential',
        'rate_type': 'Tiered',
        'fuel_type': 'Electric',
        'tiers': [
            {'tier': 1, 'limit_pct': 100, 'rate': 0.28, 'notes': 'Baseline'},
            {'tier': 2, 'limit_pct': 400, 'rate': 0.36, 'notes': '101-400% baseline'},
            {'tier': 3, 'limit_pct': None, 'rate': 0.44, 'notes': '>400% baseline'},
        ],
        'baseline_kwh': 300,  # Varies by territory
        'source': 'PG&E Tariff Book 2024',
    },
    'PGE-EV2A-TOU': {
        'utility': 'Pacific Gas & Electric',
        'utility_code': 'PGE',
        'rate_name': 'EV2-A Time-of-Use',
        'rate_type': 'TOU',
        'fuel_type': 'Electric',
        'periods': {
            'peak': {'hours': '16-21', 'rate': 0.47, 'season': 'summer'},
            'off_peak': {'hours': '0-16,21-24', 'rate': 0.23, 'season': 'summer'},
        },
        'source': 'PG&E Tariff Book 2024',
    },
    'PGE-G1-GAS': {
        'utility': 'Pacific Gas & Electric',
        'utility_code': 'PGE',
        'rate_name': 'G-1 Residential Gas',
        'rate_type': 'Tiered',
        'fuel_type': 'Gas',
        'tiers': [
            {'tier': 1, 'limit_therm': 'baseline', 'rate': 1.65},
            {'tier': 2, 'limit_therm': None, 'rate': 2.10},
        ],
        'source': 'PG&E Tariff Book 2024',
    },

    # SCE (Southern California)
    'SCE-TOU-D-4-9PM': {
        'utility': 'Southern California Edison',
        'utility_code': 'SCE',
        'rate_name': 'TOU-D 4-9pm',
        'rate_type': 'TOU',
        'fuel_type': 'Electric',
        'periods': {
            'peak': {'hours': '16-21', 'rate': 0.42, 'season': 'summer'},
            'off_peak': {'hours': '0-16,21-24', 'rate': 0.25, 'season': 'summer'},
            'super_off_peak': {'hours': '0-16', 'rate': 0.22, 'season': 'winter'},
        },
        'source': 'SCE Tariff Book 2024',
    },
    'SCE-TOU-D-5-8PM': {
        'utility': 'Southern California Edison',
        'utility_code': 'SCE',
        'rate_name': 'TOU-D 5-8pm',
        'rate_type': 'TOU',
        'fuel_type': 'Electric',
        'periods': {
            'peak': {'hours': '17-20', 'rate': 0.48, 'season': 'summer'},
            'off_peak': {'hours': '0-17,20-24', 'rate': 0.24, 'season': 'summer'},
        },
        'source': 'SCE Tariff Book 2024',
    },
    'SCE-PRIME-TOU': {
        'utility': 'Southern California Edison',
        'utility_code': 'SCE',
        'rate_name': 'TOU-D-PRIME',
        'rate_type': 'TOU',
        'fuel_type': 'Electric',
        'periods': {
            'peak': {'hours': '16-21', 'rate': 0.38, 'season': 'summer'},
            'off_peak': {'hours': '0-16,21-24', 'rate': 0.20, 'season': 'summer'},
        },
        'notes': 'EV/Battery optimized rate',
        'source': 'SCE Tariff Book 2024',
    },

    # SDG&E (San Diego)
    'SDGE-DR-TIER': {
        'utility': 'San Diego Gas & Electric',
        'utility_code': 'SDGE',
        'rate_name': 'DR Residential Tiered',
        'rate_type': 'Tiered',
        'fuel_type': 'Electric',
        'tiers': [
            {'tier': 1, 'limit_pct': 130, 'rate': 0.32},
            {'tier': 2, 'limit_pct': None, 'rate': 0.45},
        ],
        'source': 'SDG&E Tariff Book 2024',
    },
    'SDGE-TOU-DR1': {
        'utility': 'San Diego Gas & Electric',
        'utility_code': 'SDGE',
        'rate_name': 'TOU-DR1',
        'rate_type': 'TOU',
        'fuel_type': 'Electric',
        'periods': {
            'peak': {'hours': '16-21', 'rate': 0.55, 'season': 'summer'},
            'off_peak': {'hours': '0-16,21-24', 'rate': 0.28, 'season': 'summer'},
        },
        'source': 'SDG&E Tariff Book 2024',
    },

    # HECO (Hawaii - Oahu)
    'HECO-R-TIER': {
        'utility': 'Hawaiian Electric Company',
        'utility_code': 'HECO',
        'rate_name': 'Schedule R Residential',
        'rate_type': 'Tiered',
        'fuel_type': 'Electric',
        'tiers': [
            {'tier': 1, 'limit_kwh': 350, 'rate': 0.38},
            {'tier': 2, 'limit_kwh': None, 'rate': 0.42},
        ],
        'notes': 'Oahu',
        'source': 'HECO Tariff Book 2024',
    },
    'HECO-R-TOU': {
        'utility': 'Hawaiian Electric Company',
        'utility_code': 'HECO',
        'rate_name': 'Schedule TOU-R',
        'rate_type': 'TOU',
        'fuel_type': 'Electric',
        'periods': {
            'peak': {'hours': '17-22', 'rate': 0.52, 'season': 'all'},
            'mid_day': {'hours': '9-17', 'rate': 0.28, 'season': 'all'},
            'off_peak': {'hours': '0-9,22-24', 'rate': 0.32, 'season': 'all'},
        },
        'notes': 'Oahu TOU',
        'source': 'HECO Tariff Book 2024',
    },
    'HECO-EV-TOU': {
        'utility': 'Hawaiian Electric Company',
        'utility_code': 'HECO',
        'rate_name': 'Schedule EV-R',
        'rate_type': 'TOU',
        'fuel_type': 'Electric',
        'periods': {
            'peak': {'hours': '17-22', 'rate': 0.48, 'season': 'all'},
            'off_peak': {'hours': '0-17,22-24', 'rate': 0.25, 'season': 'all'},
        },
        'notes': 'Oahu EV rate',
        'source': 'HECO Tariff Book 2024',
    },

    # MECO (Maui)
    'MECO-R-TIER': {
        'utility': 'Maui Electric Company',
        'utility_code': 'MECO',
        'rate_name': 'Schedule R Residential',
        'rate_type': 'Tiered',
        'fuel_type': 'Electric',
        'tiers': [
            {'tier': 1, 'limit_kwh': 350, 'rate': 0.42},
            {'tier': 2, 'limit_kwh': None, 'rate': 0.48},
        ],
        'notes': 'Maui County',
        'source': 'MECO Tariff Book 2024',
    },

    # HELCO (Big Island)
    'HELCO-R-TIER': {
        'utility': 'Hawaii Electric Light Company',
        'utility_code': 'HELCO',
        'rate_name': 'Schedule R Residential',
        'rate_type': 'Tiered',
        'fuel_type': 'Electric',
        'tiers': [
            {'tier': 1, 'limit_kwh': 350, 'rate': 0.40},
            {'tier': 2, 'limit_kwh': None, 'rate': 0.45},
        ],
        'notes': 'Hawaii Island',
        'source': 'HELCO Tariff Book 2024',
    },

    # Default rates (US Average)
    'DEFAULT-ELEC-US': {
        'utility': 'US Average',
        'utility_code': 'DEFAULT',
        'rate_name': 'US Average Electric',
        'rate_type': 'Flat',
        'fuel_type': 'Electric',
        'rate': 0.15,
        'source': 'EIA 2024',
    },
    'DEFAULT-GAS-US': {
        'utility': 'US Average',
        'utility_code': 'DEFAULT',
        'rate_name': 'US Average Gas',
        'rate_type': 'Flat',
        'fuel_type': 'Gas',
        'rate': 1.20,
        'unit': '$/therm',
        'source': 'EIA 2024',
    },
}


# =============================================================================
# BLS PPI Escalation Indices
# Source: Bureau of Labor Statistics Producer Price Index
# =============================================================================

ESCALATION_INDICES: Dict[str, Dict[str, Any]] = {
    'BLS_PPI_HVAC': {
        'name': 'HVAC Equipment',
        'index_series': 'WPU1142',
        'annual_rate': 0.021,
        'base_year': 2024,
        'source': 'BLS PPI',
    },
    'BLS_PPI_ELECTRICAL': {
        'name': 'Electrical Equipment',
        'index_series': 'WPU117',
        'annual_rate': 0.018,
        'base_year': 2024,
        'source': 'BLS PPI',
    },
    'BLS_PPI_CONSTRUCTION': {
        'name': 'General Construction',
        'index_series': 'WPUIP231',
        'annual_rate': 0.030,
        'base_year': 2024,
        'source': 'BLS PPI',
    },
    'EIA_ENERGY_ELEC': {
        'name': 'Electricity Price',
        'annual_rate': 0.025,
        'base_year': 2024,
        'source': 'EIA AEO 2024',
    },
    'EIA_ENERGY_GAS': {
        'name': 'Natural Gas Price',
        'annual_rate': 0.020,
        'base_year': 2024,
        'source': 'EIA AEO 2024',
    },
}


# =============================================================================
# Markup Factors (Industry standard)
# =============================================================================

MARKUP_FACTORS: Dict[str, Dict[str, Any]] = {
    'overhead': {
        'name': 'Overhead',
        'rate': 0.15,
        'description': 'General contractor overhead',
    },
    'profit': {
        'name': 'Profit',
        'rate': 0.10,
        'description': 'General contractor profit margin',
    },
    'bonds_insurance': {
        'name': 'Bonds & Insurance',
        'rate': 0.03,
        'description': 'Performance bond and liability insurance',
    },
    'contingency': {
        'name': 'Contingency',
        'rate': 0.05,
        'description': 'Project contingency reserve',
    },
}


# =============================================================================
# Database Generation Functions
# =============================================================================

def generate_costdb(
    output_path: str = 'CostDB_v0.06_NREL.xlsx',
    include_notes: bool = True,
) -> Path:
    """
    Generate CostDB v0.06 Excel file from NREL data sources.

    Args:
        output_path: Output Excel file path
        include_notes: Include notes/comments in output

    Returns:
        Path to generated file
    """
    if not PANDAS_AVAILABLE:
        raise ImportError("pandas and openpyxl required for Excel generation")

    output = Path(output_path)
    logger.info(f"Generating CostDB v0.06: {output}")

    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        # Sheet 1: System Costs
        _write_system_costs(writer)

        # Sheet 2: Regional Factors
        _write_regional_factors(writer)

        # Sheet 3: Utility Rates
        _write_utility_rates(writer)

        # Sheet 4: Escalation Indices
        _write_escalation_indices(writer)

        # Sheet 5: Markup Factors
        _write_markup_factors(writer)

        # Sheet 6: Metadata
        _write_metadata(writer, output_path)

    logger.info(f"Generated: {output}")
    return output


def _write_system_costs(writer: Any) -> None:
    """Write System_Costs sheet."""
    rows = []

    # Combine all cost data
    all_costs = {**BEOPT_HVAC_COSTS, **BEOPT_DHW_COSTS, **ATB_2024_COSTS}

    for code, data in all_costs.items():
        rows.append({
            'system_code': code,
            'description': data['description'],
            'base_cost': data['base_cost'],
            'unit': data['unit'],
            'capacity': data.get('capacity', 1),
            'capacity_unit': data.get('capacity_unit', ''),
            'category': data['category'],
            'subcategory': data.get('subcategory', ''),
            'source': data['source'],
        })

    df = pd.DataFrame(rows)
    df.to_excel(writer, sheet_name='System_Costs', index=False)


def _write_regional_factors(writer: Any) -> None:
    """Write Regional_Factors sheet."""
    rows = []

    for code, data in REGIONAL_FACTORS.items():
        rows.append({
            'region_code': code,
            'state': data['state'],
            'city': data['city'],
            'factor': data['factor'],
            'notes': data.get('notes', ''),
        })

    df = pd.DataFrame(rows)
    df.to_excel(writer, sheet_name='Regional_Factors', index=False)


def _write_utility_rates(writer: Any) -> None:
    """Write Utility_Rates sheet."""
    rows = []

    for rate_id, data in UTILITY_RATES.items():
        row = {
            'rate_id': rate_id,
            'utility': data['utility'],
            'utility_code': data.get('utility_code', ''),
            'rate_name': data['rate_name'],
            'rate_type': data['rate_type'],
            'fuel_type': data.get('fuel_type', 'Electric'),
        }

        # Add rate structure as JSON string for complex rates
        if 'tiers' in data:
            row['structure'] = str(data['tiers'])
        elif 'periods' in data:
            row['structure'] = str(data['periods'])
        elif 'rate' in data:
            row['structure'] = str(data['rate'])

        row['source'] = data.get('source', '')
        rows.append(row)

    df = pd.DataFrame(rows)
    df.to_excel(writer, sheet_name='Utility_Rates', index=False)


def _write_escalation_indices(writer: Any) -> None:
    """Write Escalation_Indices sheet."""
    rows = []

    for idx_id, data in ESCALATION_INDICES.items():
        rows.append({
            'index_id': idx_id,
            'name': data['name'],
            'annual_rate': data['annual_rate'],
            'base_year': data.get('base_year', 2024),
            'source': data['source'],
        })

    df = pd.DataFrame(rows)
    df.to_excel(writer, sheet_name='Escalation_Indices', index=False)


def _write_markup_factors(writer: Any) -> None:
    """Write Markup_Factors sheet."""
    rows = []

    for markup_id, data in MARKUP_FACTORS.items():
        rows.append({
            'markup_id': markup_id,
            'name': data['name'],
            'rate': data['rate'],
            'description': data.get('description', ''),
        })

    df = pd.DataFrame(rows)
    df.to_excel(writer, sheet_name='Markup_Factors', index=False)


def _write_metadata(writer: Any, output_path: str) -> None:
    """Write Metadata sheet."""
    rows = [
        {'key': 'version', 'value': 'v0.06'},
        {'key': 'generated', 'value': datetime.now().isoformat()},
        {'key': 'generator', 'value': 'extract_nrel_costs.py'},
        {'key': 'sources', 'value': 'NREL BEopt, NREL ATB 2024, BLS PPI, Public Tariffs, ENR CCI'},
        {'key': 'base_year', 'value': '2024'},
        {'key': 'system_costs_count', 'value': str(len(BEOPT_HVAC_COSTS) + len(BEOPT_DHW_COSTS) + len(ATB_2024_COSTS))},
        {'key': 'regional_factors_count', 'value': str(len(REGIONAL_FACTORS))},
        {'key': 'utility_rates_count', 'value': str(len(UTILITY_RATES))},
        {'key': 'escalation_indices_count', 'value': str(len(ESCALATION_INDICES))},
        {'key': 'output_file', 'value': output_path},
    ]

    df = pd.DataFrame(rows)
    df.to_excel(writer, sheet_name='Metadata', index=False)


def get_system_cost(code: str) -> Optional[Dict[str, Any]]:
    """Look up system cost by code."""
    all_costs = {**BEOPT_HVAC_COSTS, **BEOPT_DHW_COSTS, **ATB_2024_COSTS}
    return all_costs.get(code)


def get_regional_factor(region_code: str) -> float:
    """Look up regional cost factor."""
    data = REGIONAL_FACTORS.get(region_code)
    return data['factor'] if data else 1.0


def get_regional_cost(
    system_code: str,
    region_code: str,
    quantity: float = 1.0,
) -> Optional[float]:
    """
    Calculate regional-adjusted cost for a system.

    Args:
        system_code: System code (e.g., 'HP-SPLIT-3T-SEER15')
        region_code: Region code (e.g., 'US-CA-SF')
        quantity: Number of units or capacity

    Returns:
        Adjusted cost or None if not found
    """
    system = get_system_cost(system_code)
    if not system:
        return None

    base = system['base_cost']
    factor = get_regional_factor(region_code)

    # Handle unit-based costs
    if system['unit'] in ('each', '$/Wdc', '$/kWh'):
        return base * quantity * factor
    else:
        return base * factor


def list_systems_by_category(category: str) -> List[str]:
    """List all system codes in a category."""
    all_costs = {**BEOPT_HVAC_COSTS, **BEOPT_DHW_COSTS, **ATB_2024_COSTS}
    return [
        code for code, data in all_costs.items()
        if data['category'] == category
    ]


def list_regions_by_state(state: str) -> List[str]:
    """List all region codes for a state."""
    return [
        code for code, data in REGIONAL_FACTORS.items()
        if data['state'] == state
    ]


def list_utility_rates(utility_code: Optional[str] = None) -> List[str]:
    """List utility rate IDs, optionally filtered by utility."""
    if utility_code:
        return [
            rate_id for rate_id, data in UTILITY_RATES.items()
            if data.get('utility_code') == utility_code
        ]
    return list(UTILITY_RATES.keys())


# =============================================================================
# Main Entry Point
# =============================================================================

if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(
        description='Generate NREL Cost Database v0.06',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python extract_nrel_costs.py
    python extract_nrel_costs.py --output my_costdb.xlsx
    python extract_nrel_costs.py --list-systems
    python extract_nrel_costs.py --list-regions CA

Data Sources:
    - NREL BEopt: HVAC and DHW system costs
    - NREL ATB 2024: PV and battery costs
    - BLS PPI: Cost escalation indices
    - Public Tariff Books: Utility rate structures
    - ENR CCI: Regional cost factors
        """
    )
    parser.add_argument(
        '--output', '-o',
        default='CostDB_v0.06_NREL.xlsx',
        help='Output Excel file path (default: CostDB_v0.06_NREL.xlsx)'
    )
    parser.add_argument(
        '--list-systems',
        action='store_true',
        help='List all system codes and exit'
    )
    parser.add_argument(
        '--list-regions',
        metavar='STATE',
        help='List regions for a state (CA, HI) and exit'
    )
    parser.add_argument(
        '--list-rates',
        action='store_true',
        help='List all utility rate IDs and exit'
    )
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose output'
    )

    args = parser.parse_args()

    if args.verbose:
        logging.basicConfig(level=logging.INFO)

    # Handle list commands
    if args.list_systems:
        print("System Codes:")
        print("-" * 60)
        for cat in ['HVAC', 'DHW', 'PV', 'Battery']:
            codes = list_systems_by_category(cat)
            if codes:
                print(f"\n{cat}:")
                for code in codes:
                    data = get_system_cost(code)
                    print(f"  {code}: ${data['base_cost']:,.2f} {data['unit']}")
        exit(0)

    if args.list_regions:
        state = args.list_regions.upper()
        codes = list_regions_by_state(state)
        print(f"Regions for {state}:")
        print("-" * 40)
        for code in codes:
            data = REGIONAL_FACTORS[code]
            print(f"  {code}: {data['city']} (factor: {data['factor']:.2f})")
        exit(0)

    if args.list_rates:
        print("Utility Rate IDs:")
        print("-" * 60)
        for rate_id, data in UTILITY_RATES.items():
            print(f"  {rate_id}: {data['utility']} - {data['rate_name']}")
        exit(0)

    # Generate database
    try:
        output_path = generate_costdb(args.output)
        print(f"Generated: {output_path}")

        # Print summary
        print(f"\nCostDB v0.06 Summary:")
        print(f"  System Costs: {len(BEOPT_HVAC_COSTS) + len(BEOPT_DHW_COSTS) + len(ATB_2024_COSTS)}")
        print(f"  Regional Factors: {len(REGIONAL_FACTORS)}")
        print(f"  Utility Rates: {len(UTILITY_RATES)}")
        print(f"  Escalation Indices: {len(ESCALATION_INDICES)}")
        print(f"  Markup Factors: {len(MARKUP_FACTORS)}")

    except ImportError as e:
        print(f"Error: {e}")
        print("Install pandas and openpyxl: pip install pandas openpyxl")
        exit(1)
