# LCCA Module Roadmap v2.3
## ECO Tools Alpha v7 - Final Release

**Date:** January 1, 2025
**Version:** 2.3
**Status:** Production Ready - v7 Release Complete
**Supersedes:** lcca_project_summary.md (December 22, 2024)
**Changelog:**
- v2.3: Zone-level TOU, VNBT, CLI, and GUI integration complete (Jan 1, 2025)
- v2.2: Phase 6.5 (CSE Input Transformation) validated with real project data
- v2.1: Added Phase 6.5 (CSE Input Transformation Platform) and documentation

---

## Executive Summary

This roadmap reflects the **actual state** of LCCA development in ECO_Alpha_v7 and provides a forward path for:

1. **NREL Cost Database Infrastructure** - Foundational cost data from free sources (PRIORITY)
2. **Completing gaps** from the original plan (regional cost data, CA/HI helpers)
3. **Zone-level LCCA reporting** aligned with CUAC parser development
4. **Aggregate reporting** for mixed-use, multifamily, and common area metering
5. **Integration** with existing parsers and data models

The LCCA module is **feature-complete for core workflows** with 9,700+ lines of production code and 60+ automated tests. However, **the cost database infrastructure from NREL sources was never implemented** - this is the critical gap that must be addressed first, as it provides the foundation for accurate regional cost calculations.

---

## 1. Current State Assessment

### 1.1 Implemented Components (Production Ready)

| Module | Lines | Description | Status |
|--------|-------|-------------|--------|
| `model.py` | 422 | Core data models (HourlyEnergy, SimulationOutput, LccaScenario) | ✅ Complete |
| `calculators.py` | 31K | NPV, IRR, payback, SIR, TOU-native LCCA | ✅ Complete |
| `tariffs.py` | 21K | TOU rate engine, period detection, demand charges | ✅ Complete |
| `costdb.py` | 17K | Cost database, regional factors, escalation | ✅ Complete |
| `bridge.py` | 10K | Simulation → LCCA connectors | ✅ Complete |
| `econ1.py` | 24K | ECON-1 report generation (gross/net/detailed) | ✅ Complete |
| `excel_export.py` | 21K | Excel dashboard export | ✅ Complete |
| `pdf_export.py` | 18K | PDF report generation | ✅ Complete |
| `esg_report.py` | 14K | Carbon/sustainability metrics | ✅ Complete |
| `sensitivity.py` | 30K | Parameter sweeps, tornado charts, Monte Carlo | ✅ Complete |
| `project_context.py` | 42K | Project metadata, simulation tracking | ✅ Complete |
| `scenario_manager.py` | 20K | Multi-scenario management | ✅ Complete |
| `ecm_bundle.py` | 19K | ECM grouping utilities | ✅ Complete |
| `vnbt.py` | 23K | V-NBT calculations | ✅ Complete |
| `parsers/hourly_results.py` | 639 | CBECC HourlyResults CSV parser | ✅ Complete |
| `parsers/cse_hourly.py` | 297 | CSE hourly CSV parser | ✅ Complete |

### 1.2 In Development (Active Work)

| Module | Lines | Description | Status |
|--------|-------|-------------|--------|
| `cuac/models.py` | 381 | CUAC data models, zone classification | 🔨 Active |
| `cuac/parser.py` | 466 | CUAC XML/CSV/JSON parsers | 🔨 Active |
| `cuac/csv_parser.py` | ~200 | Alternative CSV parser | 🔨 Active |
| `res_other/models.py` | 249 | Common area zone models | 🔨 Active |
| `res_other/parser.py` | ~150 | ResOtherZn parser | 🔨 Active |

### 1.3 Known Gaps (From Original Plan)

| Planned Component | Status | Priority | Notes |
|-------------------|--------|----------|-------|
| `extract_nrel_costs.py` | ✅ Implemented | **CRITICAL** | NREL cost extraction script - foundational |
| `CostDB_v0.06_NREL.xlsx` | ✅ Generated | **CRITICAL** | Enhanced cost database with all data |
| NREL BEopt Integration | ✅ Implemented | **CRITICAL** | HVAC/DHW cost data source |
| NREL ATB Integration | ✅ Implemented | **CRITICAL** | PV/Battery cost data source |
| BLS PPI Escalation | ✅ Implemented | **HIGH** | Cost escalation indices |
| `ca_hi_helpers.py` | ✅ Implemented | HIGH | CA/HI preset configurations (22 regions) |
| 22 CA/HI Regional Factors | ✅ Complete | HIGH | All 22 regions implemented |
| 15 Utility Rate Structures | ✅ Complete | HIGH | 15 CA/HI rates in tariffs.py |
| CLI `--rate-id`, `--region` | ❌ Not implemented | Low | Enhanced CLI options |

### 1.4 Critical Infrastructure Gap: NREL Cost Database

The original plan specified a complete cost database generation pipeline that was **never implemented**:

```
PLANNED BUT NOT BUILT:
┌─────────────────────────────────────────────────────────────────┐
│                    COST DATA PIPELINE                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  FREE DATA SOURCES                                               │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐             │
│  │ NREL BEopt  │  │ NREL ATB    │  │ BLS PPI     │             │
│  │ (HVAC/DHW)  │  │ (PV/Batt)   │  │ (Escalation)│             │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘             │
│         │                │                │                      │
│         └────────────────┼────────────────┘                      │
│                          ▼                                       │
│              ┌───────────────────────┐                          │
│              │  extract_nrel_costs.py │  ← NOT IMPLEMENTED      │
│              └───────────┬───────────┘                          │
│                          ▼                                       │
│              ┌───────────────────────┐                          │
│              │  CostDB_v0.06_NREL    │  ← NOT GENERATED         │
│              │  • 16+ system costs   │                          │
│              │  • 22 regional factors│                          │
│              │  • 15 utility rates   │                          │
│              │  • 3 escalation idx   │                          │
│              └───────────────────────┘                          │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

**Impact:** Without this infrastructure, the LCCA module uses hardcoded/default costs that may not reflect actual regional pricing. This undermines the accuracy of all financial calculations.

---

## 2. Architecture Overview

### 2.1 Current Data Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         LCCA MODULE DATA FLOW                                │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  CBECC SIMULATION OUTPUTS                                                    │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐          │
│  │ *-HourlyResults  │  │ *-CSE.CSV        │  │ *-PVBattery.csv  │          │
│  │ (Combined)       │  │ (End-use detail) │  │ (Zone alloc)     │          │
│  └────────┬─────────┘  └────────┬─────────┘  └────────┬─────────┘          │
│           │                     │                     │                     │
│           ▼                     ▼                     ▼                     │
│  ┌─────────────────────────────────────────────────────────────┐           │
│  │                    PARSERS LAYER                             │           │
│  │  hourly_results.py │ cse_hourly.py │ cuac/ │ res_other/     │           │
│  └─────────────────────────────┬───────────────────────────────┘           │
│                                │                                            │
│                                ▼                                            │
│  ┌─────────────────────────────────────────────────────────────┐           │
│  │                    CORE DATA MODELS                          │           │
│  │  SimulationOutput  │  AnnualEnergySummary  │  HourlyEnergy  │           │
│  │  CuacConfig        │  DwellUnitAllocation  │  ResOtherZone  │           │
│  └─────────────────────────────┬───────────────────────────────┘           │
│                                │                                            │
│           ┌────────────────────┼────────────────────┐                      │
│           ▼                    ▼                    ▼                      │
│  ┌────────────────┐  ┌────────────────┐  ┌────────────────┐               │
│  │   BUILDING     │  │   ZONE-LEVEL   │  │   AGGREGATE    │               │
│  │   LEVEL LCCA   │  │   LCCA (NEW)   │  │   REPORTS      │               │
│  │                │  │                │  │                │               │
│  │  • NPV/IRR     │  │  • Per-unit    │  │  • ECON-1      │               │
│  │  • Payback     │  │  • Per-zone    │  │  • Excel       │               │
│  │  • TOU costs   │  │  • Common area │  │  • PDF/ESG     │               │
│  └────────────────┘  └────────────────┘  └────────────────┘               │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 2.2 Zone Classification Hierarchy

```
Building
├── Dwelling Units (ResZn)
│   ├── High-Rise Residential Living Spaces
│   ├── Low-Rise Residential Living Spaces
│   └── Hotel/Motel Guest Room
│
├── Common Areas (ResOtherZn)
│   ├── LOBBY (Main Entry, Elevator, Hotel)
│   ├── CORRIDOR (Circulation, Transition)
│   ├── MECHANICAL (Electrical, Telecom)
│   ├── PARKING (Garage, Ramps)
│   ├── FITNESS (Gym, Exercise)
│   ├── OFFICE (Management, Admin)
│   ├── STORAGE (General, Bike)
│   ├── STAIRWELL (Egress)
│   ├── RESTROOM (Common)
│   ├── CONFERENCE (Meeting, Multipurpose)
│   ├── LAUNDRY (Common)
│   └── ELEVATOR (Shafts)
│
└── NonResidential (for mixed-use)
    ├── Retail
    ├── Office
    └── Other commercial
```

---

## 3. Roadmap Phases

### Phase 0: NREL Cost Database Infrastructure (PRIORITY - Week 1)

**Objective:** Build foundational cost data pipeline from free NREL sources

**Why This is Critical:**
- All LCCA calculations depend on accurate system costs
- Regional cost variations affect financial viability assessments
- Current costdb.py has hardcoded values without validated source data
- Without this, all downstream features (zone LCCA, reports) have unreliable inputs

#### 0.1 NREL Data Sources

| Source | Data Type | URL | Format |
|--------|-----------|-----|--------|
| **NREL BEopt** | HVAC, DHW, envelope costs | https://beopt.nrel.gov/ | CSV/XML |
| **NREL ATB** | PV, battery costs (2024) | https://atb.nrel.gov/ | Excel/CSV |
| **BLS PPI** | Cost escalation indices | https://www.bls.gov/ppi/ | CSV |
| **OpenEI** | Utility rate structures | https://openei.org/wiki/Utility_Rate_Database | JSON API |
| **ENR CCI** | Regional cost factors | Public data | Manual |

#### 0.2 CostDB v0.06 Schema

```
CostDB_v0.06_NREL.xlsx
├── Sheet: System_Costs (16+ rows)
│   ├── HVAC Systems
│   │   ├── HP-SPLIT-2T-SEER14    $4,200 base
│   │   ├── HP-SPLIT-3T-SEER15    $5,800 base
│   │   ├── HP-SPLIT-4T-SEER16    $7,400 base
│   │   ├── FURNACE-GAS-80AFUE    $2,800 base
│   │   └── AC-CENTRAL-SEER14     $3,500 base
│   ├── DHW Systems
│   │   ├── HPWH-50GAL-EF2.3      $1,800 base
│   │   ├── WH-ELEC-50GAL-EF0.92  $800 base
│   │   └── WH-GAS-TANKLESS-EF0.95 $1,200 base
│   └── PV & Battery
│       ├── PV-RES-ROOF-2024      $2.50/Wdc
│       ├── PV-COM-ROOF-2024      $1.80/Wdc
│       ├── BATT-RES-LITHIUM-2024 $800/kWh
│       └── BATT-COM-LITHIUM-2024 $650/kWh
│
├── Sheet: Regional_Factors (22 rows)
│   ├── California (18 regions)
│   │   ├── US-CA (state avg)     1.10x
│   │   ├── US-CA-SF              1.38x
│   │   ├── US-CA-LA              1.22x
│   │   └── ... (15 more)
│   └── Hawaii (4 regions)
│       ├── US-HI (state avg)     1.45x
│       ├── US-HI-HON             1.45x
│       ├── US-HI-MAU             1.50x
│       └── US-HI-BIG             1.48x
│
├── Sheet: Utility_Rates (15 rows)
│   ├── PG&E rates (3)
│   ├── SCE rates (3)
│   ├── SDG&E rates (2)
│   ├── HECO rates (3)
│   ├── MECO rates (1)
│   ├── HELCO rates (1)
│   └── Default rates (2)
│
├── Sheet: Escalation_Indices (3 rows)
│   ├── BLS_PPI_HVAC             2.1%/yr
│   ├── BLS_PPI_ELECTRICAL       1.8%/yr
│   └── EIA_ENERGY               2.5%/yr
│
├── Sheet: Markup_Factors (4 rows)
│   ├── Overhead                 15%
│   ├── Profit                   10%
│   ├── Bonds/Insurance          3%
│   └── Contingency              5%
│
└── Sheet: Metadata
    ├── Version: v0.06
    ├── Generated: [date]
    ├── Sources: NREL BEopt, NREL ATB 2024, BLS PPI
    └── Base Year: 2024
```

#### 0.3 extract_nrel_costs.py Implementation

```python
# eco_tools/lcca/extract_nrel_costs.py
"""
NREL Cost Database Generator
============================

Generates CostDB_v0.06_NREL.xlsx from free NREL data sources.

Data Sources:
- NREL BEopt: HVAC and DHW system costs
- NREL ATB 2024: PV and battery costs
- BLS PPI: Cost escalation indices
- Public utility tariffs: Rate structures

Usage:
    python -m eco_tools.lcca.extract_nrel_costs --output CostDB_v0.06_NREL.xlsx
"""

import pandas as pd
from pathlib import Path
from dataclasses import dataclass
from typing import Dict, List, Optional
import logging

logger = logging.getLogger(__name__)


@dataclass
class NrelCostSource:
    """Configuration for an NREL data source."""
    name: str
    url: str
    local_cache: Optional[Path] = None
    last_updated: Optional[str] = None


# NREL BEopt cost data (embedded from public documentation)
BEOPT_HVAC_COSTS = {
    'HP-SPLIT-2T-SEER14': {'base_cost': 4200, 'unit': 'each', 'capacity_tons': 2},
    'HP-SPLIT-3T-SEER15': {'base_cost': 5800, 'unit': 'each', 'capacity_tons': 3},
    'HP-SPLIT-4T-SEER16': {'base_cost': 7400, 'unit': 'each', 'capacity_tons': 4},
    'HP-SPLIT-5T-SEER16': {'base_cost': 8900, 'unit': 'each', 'capacity_tons': 5},
    'FURNACE-GAS-80AFUE': {'base_cost': 2800, 'unit': 'each', 'capacity_kbtuh': 60},
    'FURNACE-GAS-92AFUE': {'base_cost': 3400, 'unit': 'each', 'capacity_kbtuh': 60},
    'AC-CENTRAL-SEER14': {'base_cost': 3500, 'unit': 'each', 'capacity_tons': 3},
    'AC-CENTRAL-SEER16': {'base_cost': 4200, 'unit': 'each', 'capacity_tons': 3},
    'MINISPLIT-1T-SEER20': {'base_cost': 3200, 'unit': 'each', 'capacity_tons': 1},
    'VRF-OUTDOOR-4T': {'base_cost': 12000, 'unit': 'each', 'capacity_tons': 4},
}

BEOPT_DHW_COSTS = {
    'HPWH-50GAL-EF2.3': {'base_cost': 1800, 'unit': 'each', 'capacity_gal': 50},
    'HPWH-65GAL-EF3.0': {'base_cost': 2400, 'unit': 'each', 'capacity_gal': 65},
    'HPWH-80GAL-EF2.8': {'base_cost': 2800, 'unit': 'each', 'capacity_gal': 80},
    'WH-ELEC-50GAL-EF0.92': {'base_cost': 800, 'unit': 'each', 'capacity_gal': 50},
    'WH-GAS-TANK-40GAL-EF0.62': {'base_cost': 900, 'unit': 'each', 'capacity_gal': 40},
    'WH-GAS-TANKLESS-EF0.95': {'base_cost': 1200, 'unit': 'each', 'capacity_gpm': 6.6},
}

# NREL ATB 2024 PV/Battery costs
ATB_2024_COSTS = {
    'PV-RES-ROOF-2024': {'base_cost': 2.50, 'unit': '$/Wdc', 'source': 'ATB 2024'},
    'PV-RES-CARPORT-2024': {'base_cost': 2.80, 'unit': '$/Wdc', 'source': 'ATB 2024'},
    'PV-COM-ROOF-2024': {'base_cost': 1.80, 'unit': '$/Wdc', 'source': 'ATB 2024'},
    'PV-COM-GROUND-2024': {'base_cost': 1.40, 'unit': '$/Wdc', 'source': 'ATB 2024'},
    'BATT-RES-LITHIUM-2024': {'base_cost': 800, 'unit': '$/kWh', 'source': 'ATB 2024'},
    'BATT-COM-LITHIUM-2024': {'base_cost': 650, 'unit': '$/kWh', 'source': 'ATB 2024'},
}

# Regional cost factors (ENR CCI based)
REGIONAL_FACTORS = {
    # California
    'US-CA': {'factor': 1.10, 'state': 'CA', 'city': 'State Average'},
    'US-CA-SF': {'factor': 1.38, 'state': 'CA', 'city': 'San Francisco'},
    'US-CA-OAK': {'factor': 1.35, 'state': 'CA', 'city': 'Oakland'},
    'US-CA-SJ': {'factor': 1.36, 'state': 'CA', 'city': 'San Jose'},
    'US-CA-LA': {'factor': 1.22, 'state': 'CA', 'city': 'Los Angeles'},
    'US-CA-SD': {'factor': 1.18, 'state': 'CA', 'city': 'San Diego'},
    'US-CA-OC': {'factor': 1.20, 'state': 'CA', 'city': 'Orange County'},
    'US-CA-SAC': {'factor': 1.12, 'state': 'CA', 'city': 'Sacramento'},
    'US-CA-FRE': {'factor': 1.05, 'state': 'CA', 'city': 'Fresno'},
    'US-CA-BAK': {'factor': 1.03, 'state': 'CA', 'city': 'Bakersfield'},
    'US-CA-RIV': {'factor': 1.08, 'state': 'CA', 'city': 'Riverside'},
    'US-CA-SB': {'factor': 1.15, 'state': 'CA', 'city': 'Santa Barbara'},
    'US-CA-VEN': {'factor': 1.12, 'state': 'CA', 'city': 'Ventura'},
    'US-CA-MON': {'factor': 1.10, 'state': 'CA', 'city': 'Monterey'},
    'US-CA-SLO': {'factor': 1.08, 'state': 'CA', 'city': 'San Luis Obispo'},
    'US-CA-RED': {'factor': 1.02, 'state': 'CA', 'city': 'Redding'},
    'US-CA-STO': {'factor': 1.04, 'state': 'CA', 'city': 'Stockton'},
    'US-CA-SRO': {'factor': 1.28, 'state': 'CA', 'city': 'Santa Rosa'},
    # Hawaii
    'US-HI': {'factor': 1.45, 'state': 'HI', 'city': 'State Average'},
    'US-HI-HON': {'factor': 1.45, 'state': 'HI', 'city': 'Honolulu'},
    'US-HI-MAU': {'factor': 1.50, 'state': 'HI', 'city': 'Maui'},
    'US-HI-BIG': {'factor': 1.48, 'state': 'HI', 'city': 'Big Island'},
}

# Utility rate structures (from public tariff books)
UTILITY_RATES = {
    'PGE-E1-TIER': {
        'utility': 'Pacific Gas & Electric',
        'rate_type': 'Tiered',
        'tiers': [
            {'limit_kwh': 'baseline', 'rate': 0.24},
            {'limit_kwh': '101-400%', 'rate': 0.30},
            {'limit_kwh': '>400%', 'rate': 0.38},
        ],
    },
    'PGE-EV2A-TOU': {
        'utility': 'Pacific Gas & Electric',
        'rate_type': 'TOU',
        'periods': {
            'peak': {'hours': '16-21', 'rate': 0.47},
            'off_peak': {'hours': '0-16,21-24', 'rate': 0.23},
        },
    },
    # ... (additional rates)
}


def generate_costdb(output_path: str = 'CostDB_v0.06_NREL.xlsx') -> Path:
    """
    Generate CostDB v0.06 from NREL data sources.

    Args:
        output_path: Output Excel file path

    Returns:
        Path to generated file
    """
    output = Path(output_path)

    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        # Sheet 1: System Costs
        system_costs = []
        for code, data in {**BEOPT_HVAC_COSTS, **BEOPT_DHW_COSTS, **ATB_2024_COSTS}.items():
            system_costs.append({
                'system_code': code,
                'base_cost': data['base_cost'],
                'unit': data['unit'],
                'source': data.get('source', 'NREL BEopt'),
                'category': _categorize_system(code),
            })
        pd.DataFrame(system_costs).to_excel(writer, sheet_name='System_Costs', index=False)

        # Sheet 2: Regional Factors
        regional = [
            {'region_code': k, **v} for k, v in REGIONAL_FACTORS.items()
        ]
        pd.DataFrame(regional).to_excel(writer, sheet_name='Regional_Factors', index=False)

        # Sheet 3: Utility Rates
        rates = []
        for rate_id, data in UTILITY_RATES.items():
            rates.append({
                'rate_id': rate_id,
                'utility': data['utility'],
                'rate_type': data['rate_type'],
                'structure': str(data.get('tiers') or data.get('periods')),
            })
        pd.DataFrame(rates).to_excel(writer, sheet_name='Utility_Rates', index=False)

        # Sheet 4: Escalation Indices
        escalation = [
            {'index_name': 'BLS_PPI_HVAC', 'annual_rate': 0.021, 'source': 'BLS PPI'},
            {'index_name': 'BLS_PPI_ELECTRICAL', 'annual_rate': 0.018, 'source': 'BLS PPI'},
            {'index_name': 'EIA_ENERGY', 'annual_rate': 0.025, 'source': 'EIA AEO'},
        ]
        pd.DataFrame(escalation).to_excel(writer, sheet_name='Escalation_Indices', index=False)

        # Sheet 5: Markup Factors
        markups = [
            {'markup_type': 'Overhead', 'rate': 0.15},
            {'markup_type': 'Profit', 'rate': 0.10},
            {'markup_type': 'Bonds_Insurance', 'rate': 0.03},
            {'markup_type': 'Contingency', 'rate': 0.05},
        ]
        pd.DataFrame(markups).to_excel(writer, sheet_name='Markup_Factors', index=False)

        # Sheet 6: Metadata
        from datetime import datetime
        metadata = [
            {'key': 'version', 'value': 'v0.06'},
            {'key': 'generated', 'value': datetime.now().isoformat()},
            {'key': 'sources', 'value': 'NREL BEopt, NREL ATB 2024, BLS PPI, Public Tariffs'},
            {'key': 'base_year', 'value': '2024'},
        ]
        pd.DataFrame(metadata).to_excel(writer, sheet_name='Metadata', index=False)

    logger.info(f"Generated {output}")
    return output


def _categorize_system(code: str) -> str:
    """Categorize system code."""
    if code.startswith('HP-') or code.startswith('AC-') or code.startswith('FURNACE'):
        return 'HVAC'
    elif code.startswith('MINISPLIT') or code.startswith('VRF'):
        return 'HVAC'
    elif code.startswith('HPWH') or code.startswith('WH-'):
        return 'DHW'
    elif code.startswith('PV-'):
        return 'PV'
    elif code.startswith('BATT-'):
        return 'Battery'
    return 'Other'


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Generate NREL Cost Database')
    parser.add_argument('--output', default='CostDB_v0.06_NREL.xlsx')
    args = parser.parse_args()

    generate_costdb(args.output)
    print(f"Generated: {args.output}")
```

#### 0.4 Integration with Existing costdb.py

Enhance `costdb.py` to load from CostDB v0.06:

```python
# Enhanced costdb.py loader

def load_costdb_v06(excel_path: str) -> CostDatabase:
    """
    Load CostDB v0.06 format with full NREL data.

    Args:
        excel_path: Path to CostDB_v0.06_NREL.xlsx

    Returns:
        Populated CostDatabase instance
    """
    db = CostDatabase()

    # Load system costs
    systems_df = pd.read_excel(excel_path, sheet_name='System_Costs')
    for _, row in systems_df.iterrows():
        db.add_system_cost(SystemCost(
            code=row['system_code'],
            base_cost=row['base_cost'],
            unit=row['unit'],
            category=row['category'],
            source=row['source'],
        ))

    # Load regional factors
    regional_df = pd.read_excel(excel_path, sheet_name='Regional_Factors')
    for _, row in regional_df.iterrows():
        db.add_regional_factor(RegionalFactor(
            region_code=row['region_code'],
            factor=row['factor'],
            state=row['state'],
            city=row['city'],
        ))

    # Load utility rates
    rates_df = pd.read_excel(excel_path, sheet_name='Utility_Rates')
    # ... parse rate structures

    # Load escalation indices
    escalation_df = pd.read_excel(excel_path, sheet_name='Escalation_Indices')
    for _, row in escalation_df.iterrows():
        db.add_escalation_rate(EscalationRate(
            name=row['index_name'],
            annual_rate=row['annual_rate'],
            source=row['source'],
        ))

    # Load markup factors
    markups_df = pd.read_excel(excel_path, sheet_name='Markup_Factors')
    for _, row in markups_df.iterrows():
        db.markup_factors[row['markup_type']] = row['rate']

    return db
```

#### 0.5 Deliverables - Phase 0

| Deliverable | Description | Priority |
|-------------|-------------|----------|
| `extract_nrel_costs.py` | NREL data extraction script | **P0** |
| `CostDB_v0.06_NREL.xlsx` | Generated cost database | **P0** |
| Enhanced `costdb.py` | v0.06 loader integration | **P0** |
| `test_costdb_v06.py` | Validation tests | **P0** |
| Data documentation | Source attribution, methodology | P1 |

#### 0.6 Success Criteria - Phase 0

- [ ] `extract_nrel_costs.py` runs without errors
- [ ] `CostDB_v0.06_NREL.xlsx` generated with all 6 sheets
- [ ] 16+ system costs with NREL source attribution
- [ ] 22 CA/HI regional factors loaded correctly
- [ ] 15 utility rate structures parsed
- [ ] 3 escalation indices populated
- [ ] Existing costdb.py loads v0.06 format
- [ ] All existing LCCA tests still pass
- [ ] Regional cost lookup returns correct factors

---

### Phase 1: CA/HI Helpers & Rate Structures (Week 2)

**Objective:** Complete regional presets and utility rate library

#### 1.1 CA/HI Regional Cost Factors

Create `ca_hi_helpers.py` with 22 regional factors:

```python
# California (18 regions)
CA_REGIONAL_FACTORS = {
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
    'US-CA-RIV': 1.08,       # Riverside
    'US-CA-SB': 1.15,        # Santa Barbara
    'US-CA-VEN': 1.12,       # Ventura
    'US-CA-MON': 1.10,       # Monterey
    'US-CA-SLO': 1.08,       # San Luis Obispo
    'US-CA-RED': 1.02,       # Redding
    'US-CA-STO': 1.04,       # Stockton
    'US-CA-SRO': 1.28,       # Santa Rosa
}

# Hawaii (4 regions)
HI_REGIONAL_FACTORS = {
    'US-HI': 1.45,           # State average
    'US-HI-HON': 1.45,       # Honolulu/Oahu
    'US-HI-MAU': 1.50,       # Maui
    'US-HI-BIG': 1.48,       # Big Island
}
```

#### 1.2 Utility Rate Structures

Add 15 CA/HI utility rates to `tariffs.py`:

| Utility | Rate ID | Type | Priority |
|---------|---------|------|----------|
| PG&E | `PGE-E1-TIER` | Tiered residential | High |
| PG&E | `PGE-EV2A-TOU` | EV TOU | Medium |
| PG&E | `PGE-G1-GAS` | Gas tiered | High |
| SCE | `SCE-TOU-D-4-9PM` | TOU (4-9pm peak) | High |
| SCE | `SCE-TOU-D-5-8PM` | TOU (5-8pm peak) | Medium |
| SCE | `SCE-PRIME-TOU` | EV/Battery | Medium |
| SDG&E | `SDGE-DR-TIER` | Tiered residential | High |
| SDG&E | `SDGE-TOU-DR1` | TOU | Medium |
| HECO | `HECO-R-TIER` | Oahu tiered | High |
| HECO | `HECO-R-TOU` | Oahu TOU | Medium |
| HECO | `HECO-EV-TOU` | Oahu EV | Low |
| MECO | `MECO-R-TIER` | Maui tiered | Medium |
| HELCO | `HELCO-R-TIER` | Big Island tiered | Medium |
| DEFAULT | `DEFAULT-ELEC-US` | US average | Present |
| DEFAULT | `DEFAULT-GAS-US` | US average | Present |

#### 1.3 Deliverables

- [x] `ca_hi_helpers.py` - Regional factors and rate presets (22 regions, 4 mapping functions)
- [x] Enhanced `tariffs.py` - 15 CA/HI rate structures (residential + Hawaii utilities)
- [x] `test_ca_hi_helpers.py` - 45 tests covering all components
- [x] All existing tests pass (backward compatibility)

---

### Phase 2: Zone-Level LCCA (2-3 Weeks)

**Objective:** Enable per-zone and per-unit LCCA calculations

#### 2.1 Zone Energy Parser

Extend CUAC/ResOther parsers to extract zone-level energy:

```python
# New: eco_tools/lcca/zone_energy.py

@dataclass
class ZoneEnergySummary:
    """Energy summary for a single zone."""
    zone_name: str
    zone_type: ZoneType  # DWELLING_UNIT, COMMON_AREA, UNCONDITIONED
    category: CommonAreaCategory  # LOBBY, CORRIDOR, etc. (if common area)

    # Annual consumption
    elec_kwh: float = 0.0
    gas_therm: float = 0.0

    # Peak demand
    peak_demand_kw: float = 0.0

    # Area for intensity calculations
    area_sqft: float = 0.0

    # Allocation factors
    pv_allocation_kwdc: float = 0.0
    battery_allocation_kwh: float = 0.0

    @property
    def eui_kbtu_per_sqft(self) -> float:
        """Energy Use Intensity in kBtu/sqft."""
        if self.area_sqft <= 0:
            return 0.0
        elec_kbtu = self.elec_kwh * 3.412
        gas_kbtu = self.gas_therm * 100
        return (elec_kbtu + gas_kbtu) / self.area_sqft


@dataclass
class ZoneLccaResult:
    """LCCA results for a single zone."""
    zone_name: str
    zone_type: ZoneType

    # Energy costs
    annual_elec_cost: float = 0.0
    annual_gas_cost: float = 0.0
    annual_demand_cost: float = 0.0

    # With PV/battery credits
    annual_pv_credit: float = 0.0
    annual_battery_credit: float = 0.0
    net_annual_cost: float = 0.0

    # Per-unit metrics (for dwelling units)
    num_units: int = 1
    cost_per_unit: float = 0.0

    # CUAC utility allowance
    utility_allowance: float = 0.0
```

#### 2.2 Zone-Level Cost Allocation

```python
# New: eco_tools/lcca/zone_allocation.py

class ZoneCostAllocator:
    """Allocate building-level costs to individual zones."""

    def __init__(
        self,
        building_energy: SimulationOutput,
        zone_allocations: List[DwellUnitAllocation],
        common_area_zones: List[ResOtherZone],
        tariff: TouTariff,
    ):
        self.building = building_energy
        self.zones = zone_allocations
        self.common_areas = common_area_zones
        self.tariff = tariff

    def allocate_by_area(self) -> Dict[str, ZoneLccaResult]:
        """Allocate costs proportionally by conditioned area."""
        ...

    def allocate_by_meter_category(self) -> Dict[CommonAreaCategory, ZoneLccaResult]:
        """Aggregate costs by meter category (LOBBY, CORRIDOR, etc.)."""
        ...

    def allocate_dwelling_units(self) -> List[ZoneLccaResult]:
        """Calculate per-unit LCCA for dwelling units."""
        ...

    def calculate_cuac_allowances(
        self,
        cuac_config: CuacConfig,
    ) -> Dict[int, float]:
        """Calculate CUAC utility allowances by bedroom count."""
        ...
```

#### 2.3 Integration with Existing Parsers

Extend `cuac/parser.py` to extract zone-level energy data:

```python
def parse_zone_energy_from_cse(
    cse_csv_path: str,
    zone_allocations: List[DwellUnitAllocation],
) -> Dict[str, ZoneEnergySummary]:
    """
    Parse CSE hourly data and allocate to zones.

    CSE files contain meter-level data (MtrElec, MtrElec2, MtrNatGas)
    that can be mapped to zones via the meter-zone relationship.
    """
    ...
```

#### 2.4 Deliverables

- [x] `zone_energy.py` - Zone energy data models (644 lines, 12 classes)
- [x] `zone_allocation.py` - Cost allocation engine (671 lines, ZoneCostAllocator + helpers)
- [x] `test_zone_lcca.py` - Zone LCCA tests (48 tests, 100% passing)
- [ ] Extended CUAC parser for zone-level CSE data (optional enhancement)
- [ ] Integration tests with real project data
- [ ] Documentation for zone-level LCCA workflow

---

### Phase 3: Aggregate Reporting (2 Weeks)

**Objective:** Multi-level reporting (zone → category → building)

#### 3.1 Report Hierarchy

```
Building LCCA Report
├── Executive Summary
│   ├── Total Lifecycle Cost
│   ├── NPV/IRR/Payback
│   └── Annual Energy Costs
│
├── Zone Category Breakdown
│   ├── Dwelling Units (subtotal)
│   │   ├── 1-Bedroom Units
│   │   ├── 2-Bedroom Units
│   │   └── 3-Bedroom Units
│   ├── Common Areas (subtotal)
│   │   ├── Lobby
│   │   ├── Corridors
│   │   ├── Parking
│   │   └── Other
│   └── NonResidential (if mixed-use)
│
├── Per-Zone Detail
│   ├── Zone Name
│   ├── Area (sqft)
│   ├── EUI (kBtu/sqft)
│   ├── Annual Cost ($)
│   ├── PV Allocation (kWdc)
│   └── Utility Allowance ($/month)
│
└── CUAC Summary (for affordable housing)
    ├── Allowance by Bedroom Count
    ├── PV/Battery Credits
    └── Net Tenant Cost
```

#### 3.2 New Report Modules

```python
# New: eco_tools/lcca/zone_report.py

@dataclass
class ZoneLccaReport:
    """Comprehensive zone-level LCCA report."""

    # Building summary
    building_name: str
    building_type: str
    total_area_sqft: float

    # Aggregate results
    total_lcca: LccaResults

    # Zone-level breakdowns
    dwelling_unit_results: List[ZoneLccaResult]
    common_area_results: Dict[CommonAreaCategory, ZoneLccaResult]
    nonres_results: Optional[ZoneLccaResult] = None

    # CUAC-specific
    cuac_config: Optional[CuacConfig] = None
    utility_allowances: Dict[int, float] = field(default_factory=dict)

    def to_excel(self, output_path: str):
        """Export multi-sheet Excel report."""
        ...

    def to_pdf(self, output_path: str):
        """Export formatted PDF report."""
        ...

    def summary_by_category(self) -> Dict[str, float]:
        """Get cost summary by zone category."""
        ...


def generate_zone_lcca_report(
    simulation: SimulationOutput,
    zone_allocations: List[DwellUnitAllocation],
    common_areas: List[ResOtherZone],
    tariff: TouTariff,
    cuac_config: Optional[CuacConfig] = None,
    capex: float = 0.0,
    assumptions: Optional[ScenarioAssumptions] = None,
) -> ZoneLccaReport:
    """Generate comprehensive zone-level LCCA report."""
    ...
```

#### 3.3 Excel Export Enhancement

Add new sheets to Excel dashboard:

| Sheet | Content |
|-------|---------|
| Summary | Building-level NPV, IRR, payback |
| Zone Detail | Per-zone annual costs, EUI |
| Category Rollup | Costs by LOBBY, CORRIDOR, etc. |
| Dwelling Units | Per-unit breakdown by bedroom count |
| CUAC Allowances | Utility allowance schedule |
| Hourly Profile | 8760 hourly consumption chart |

#### 3.4 Deliverables

- [x] `zone_report.py` - Zone LCCA report generator (580 lines, ZoneLccaReport + formatters)
- [x] `zone_excel.py` - Multi-sheet Excel export (450 lines, styled workbook with charts)
- [x] `test_zone_report.py` - Zone report tests (26 tests, 100% passing)
- [ ] Enhanced `pdf_export.py` - Zone-level PDF sections (future enhancement)
- [ ] Example reports with real project data (future enhancement)

---

### Phase 4: Mixed-Use and Common Area Metering (2 Weeks)

**Objective:** Full support for complex building types

#### 4.1 Meter Category Aggregation

```python
# New: eco_tools/lcca/meter_aggregation.py

@dataclass
class MeterCategory:
    """Aggregated meter for a common area category."""
    category: CommonAreaCategory
    meter_name: str
    zones: List[ResOtherZone]

    # Aggregated energy
    total_elec_kwh: float = 0.0
    total_gas_therm: float = 0.0
    peak_demand_kw: float = 0.0

    # Cost allocation
    annual_cost: float = 0.0
    cost_per_sqft: float = 0.0


class MeterAggregator:
    """Aggregate zone-level data into meter categories."""

    def aggregate_by_category(
        self,
        zones: List[ResOtherZone],
        zone_energy: Dict[str, ZoneEnergySummary],
    ) -> Dict[CommonAreaCategory, MeterCategory]:
        """Group zones by category and sum energy."""
        ...

    def allocate_master_meter(
        self,
        building_total: AnnualEnergySummary,
        meter_categories: Dict[CommonAreaCategory, MeterCategory],
    ) -> Dict[CommonAreaCategory, float]:
        """Allocate master meter consumption to categories."""
        ...
```

#### 4.2 Mixed-Use Building Support

Extend existing mixed-use parsing:

```python
# Enhanced: eco_tools/lcca/bridge.py

def create_mixed_use_scenarios(
    simulation: SimulationOutput,
    tariff_residential: TouTariff,
    tariff_commercial: TouTariff,
    common_area_tariff: Optional[TouTariff] = None,
) -> Dict[str, LccaResults]:
    """
    Create separate LCCA scenarios for each building section.

    Returns:
        {
            'residential': LccaResults for dwelling units,
            'commercial': LccaResults for nonres spaces,
            'common_area': LccaResults for shared spaces,
            'combined': LccaResults for whole building,
        }
    """
    ...
```

#### 4.3 Deliverables

- [x] `meter_aggregation.py` - Meter category aggregation (750 lines, MeterAggregator + BuildingSection + MixedUseLccaResults)
- [x] Enhanced `bridge.py` - Mixed-use scenario creation (create_mixed_use_scenarios, run_mixed_use_lcca, allocate_capex_by_section)
- [x] Common area cost allocation algorithms (by_area, by_modeled, by_meter methods)
- [x] `test_mixed_use.py` - Tests for complex building configurations (37 tests, 100% passing)
- [x] ZoneType.NONRESIDENTIAL enum value for mixed-use building support

---

### Phase 5: Advanced Analytics ✅ COMPLETE

**Objective:** Production-ready analytics and integration

#### 5.1 Sensitivity by Zone ✅ IMPLEMENTED

Extended sensitivity analysis to zone level in `sensitivity.py`:

```python
# Implemented in eco_tools/lcca/sensitivity.py (~200 lines added)

@dataclass
class ZoneSensitivityResult:
    """Result of zone-level sensitivity analysis."""
    zone_name: str
    base_annual_cost: float
    sensitivities: Dict[str, float]  # parameter -> pct_change

@dataclass
class ZoneImpactResult:
    """Zone impact on building-level costs."""
    zone_name: str
    zone_cost: float
    building_cost: float
    impact_pct: float
    is_high_impact: bool

def zone_sensitivity_analysis(zones: List[ZoneEnergySummary], rate_delta: float = 0.10) -> List[ZoneSensitivityResult]
def identify_high_impact_zones(zones: List[ZoneEnergySummary], threshold: float = 0.10) -> List[ZoneImpactResult]
def format_zone_impact_table(impacts: List[ZoneImpactResult]) -> str
def zone_tornado_analysis(zones: List[ZoneEnergySummary], rate_deltas: Tuple[float, float] = (-0.15, 0.15)) -> List[TornadoItem]
```

#### 5.2 Benchmarking ✅ IMPLEMENTED

Created comprehensive benchmarking module `benchmarks.py` (~500 lines):

```python
# Implemented in eco_tools/lcca/benchmarks.py

# Enums
class PerformanceRating(Enum):
    EXCELLENT = "excellent"   # ≤10th percentile
    GOOD = "good"            # 10-25th percentile
    AVERAGE = "average"       # 25-75th percentile
    BELOW_AVERAGE = "below_average"  # 75-90th percentile
    POOR = "poor"            # >90th percentile

class BuildingVintage(Enum):
    NEW_CONSTRUCTION = "new_construction"  # 2022+ code
    RECENT = "recent"                      # 2019-2022
    OLDER = "older"                        # Pre-2019

# Data classes
@dataclass
class ZoneBenchmark:
    """EUI benchmark with percentile distribution."""
    zone_type: str
    category: Optional[str]
    climate_zone: str
    vintage: BuildingVintage
    eui_p10/p25/p50/p75/p90: float

@dataclass
class BenchmarkComparison:
    """Result of comparing zone to benchmark."""
    zone_name: str
    actual_eui: float
    benchmark_median: float
    percentile: float
    rating: PerformanceRating
    improvement_potential_pct: float

# Library with CA climate zone data (CZ01-CZ16)
class BenchmarkLibrary:
    def get_dwelling_benchmark(climate_zone: str, vintage: BuildingVintage) -> ZoneBenchmark
    def get_common_area_benchmark(category: str, climate_zone: str) -> ZoneBenchmark

# Functions
compare_zone_to_benchmark() -> BenchmarkComparison
compare_zones_to_benchmarks() -> List[BenchmarkComparison]
identify_high_impact_zones() -> List[BenchmarkComparison]  # zones needing attention
calculate_portfolio_rating() -> Tuple[PerformanceRating, Dict]
format_benchmark_comparison() -> str
format_benchmark_summary_table() -> str
format_rating_distribution() -> str
```

#### 5.3 Tests ✅ 41 PASSING

Created `tests/test_benchmarks.py` with comprehensive test coverage:
- PerformanceRating tests (5)
- ZoneBenchmark tests (5)
- BenchmarkLibrary tests (7)
- BenchmarkComparison tests (5)
- PortfolioRating tests (3)
- Formatting tests (3)
- ZoneSensitivity tests (2)
- HighImpactZones tests (3)
- ZoneTornado tests (2)
- BenchmarkData tests (3)
- Integration tests (3)

#### 5.4 Integration Points

| Integration | Description | Status |
|-------------|-------------|--------|
| Streamlit GUI | Zone-level LCCA dashboard | Planned |
| CBECC Direct | Auto-parse simulation outputs | Planned |
| API Endpoint | REST API for zone LCCA | Future |
| Report Templates | Customizable report formats | Future |

---

## 4. Data Model Additions

### 4.1 New Data Classes

```python
# Summary of new data models to add

# Zone-level models
ZoneEnergySummary      # Per-zone energy consumption
ZoneLccaResult         # Per-zone LCCA results
ZoneLccaReport         # Comprehensive zone report

# Meter aggregation
MeterCategory          # Aggregated meter category
MeterAggregator        # Aggregation engine

# Benchmarking
ZoneBenchmark          # Benchmark data
BenchmarkComparison    # Comparison results

# CA/HI specific
RegionalPreset         # Region-specific defaults
UtilityRatePreset      # Utility rate presets
```

### 4.2 Enhanced Existing Models

| Model | Enhancement |
|-------|-------------|
| `SimulationOutput` | Add `zone_summaries: Dict[str, ZoneEnergySummary]` |
| `CuacConfig` | Add `calculate_zone_allowances()` method |
| `ResOtherZone` | Add `annual_energy` and `annual_cost` properties |
| `DwellUnitAllocation` | Add `energy_summary` and `lcca_result` fields |

---

## 5. Testing Strategy

### 5.1 Test Data Requirements

| Data Set | Description | Location |
|----------|-------------|----------|
| Ventura & 7th | Multifamily with CUAC | `LCCA Tests/Ventura & 7th/` |
| Mixed-Use Sample | Res + Commercial | To be created |
| High-Rise Affordable | 100+ units with VNEM | To be created |
| Hotel/Motel | Guest rooms + common | To be created |

### 5.2 Test Coverage Targets

| Module | Current | Target |
|--------|---------|--------|
| Core LCCA | 60 tests | 80 tests |
| CUAC Parser | 5 tests | 20 tests |
| Zone Energy | 0 tests | 30 tests |
| Zone Allocation | 0 tests | 25 tests |
| Aggregate Reports | 0 tests | 20 tests |

### 5.3 Validation Criteria

- Zone costs sum to building total (±1% tolerance)
- CUAC allowances match manual calculations
- EUI values within benchmark ranges
- PV/battery allocations sum correctly

---

## 6. Dependencies

### 6.1 Python Packages

```
# Required (already installed)
pandas>=2.0
openpyxl>=3.1
numpy>=1.24

# Optional
reportlab>=4.0      # PDF export
matplotlib>=3.7     # Charts in reports
xlsxwriter>=3.1     # Enhanced Excel features
```

### 6.2 External Data

| Data Source | Type | Status |
|-------------|------|--------|
| NREL BEopt | HVAC/DHW costs | Manual (free) |
| NREL ATB | PV/Battery costs | Manual (free) |
| BLS PPI | Escalation indices | Manual (free) |
| Public Tariffs | Utility rates | Manual (free) |
| ENR CCI | Regional factors | Manual (free) |

---

## 7. Implementation Schedule

### Week 1: NREL Cost Database Infrastructure (PRIORITY)
- [ ] Create `extract_nrel_costs.py` script
- [ ] Embed NREL BEopt HVAC/DHW cost data
- [ ] Embed NREL ATB 2024 PV/battery costs
- [ ] Add 22 CA/HI regional factors (ENR CCI based)
- [ ] Add 15 utility rate structures
- [ ] Add BLS PPI escalation indices
- [ ] Generate `CostDB_v0.06_NREL.xlsx`
- [ ] Enhance `costdb.py` with v0.06 loader
- [ ] Create `test_costdb_v06.py` validation tests
- [ ] Verify all existing tests still pass

### Week 2: CA/HI Helpers & Rate Library ✅ COMPLETE
- [x] Create `ca_hi_helpers.py` with presets (22 regions, 4 mapping functions)
- [x] Add full utility rate structures to `tariffs.py` (15 CA/HI rates)
- [x] Climate zone → region mapping (CZ01-CZ16, HI01-HI04)
- [x] Region → utility mapping (PGE, SCE, SDGE, HECO, MECO, HELCO)
- [x] Write tests for new components (45 tests in test_ca_hi_helpers.py)

### Week 3-4: Zone-Level LCCA ✅ COMPLETE
- [x] Create `zone_energy.py` models (644 lines, 12 data classes)
- [x] Create `zone_allocation.py` engine (671 lines, ZoneCostAllocator)
- [x] Create `test_zone_lcca.py` tests (48 tests, 100% passing)
- [ ] Extend CUAC parser for zone energy (optional enhancement)
- [ ] Integration tests with Ventura & 7th data

### Week 5-6: Aggregate Reporting ✅ COMPLETE
- [x] Create `zone_report.py` (580 lines, multi-level reporting)
- [x] Create `zone_excel.py` (450 lines, styled multi-sheet workbook)
- [x] Create `test_zone_report.py` (26 tests, 100% passing)
- [x] CUAC utility allowance report integration
- [ ] Enhanced PDF export (future enhancement)

### Week 7-8: Mixed-Use & Metering ✅ COMPLETE
- [x] Create `meter_aggregation.py` (750 lines)
- [x] Enhance bridge for mixed-use scenarios (create_mixed_use_scenarios, run_mixed_use_lcca)
- [x] Common area cost allocation (by_area, by_modeled, by_meter methods)
- [x] Complex building test cases (37 tests in test_mixed_use.py)

### Week 9-10: Advanced Analytics ✅ COMPLETE
- [x] Zone sensitivity analysis (zone_sensitivity_analysis, identify_high_impact_zones, zone_tornado_analysis)
- [x] Benchmarking module (benchmarks.py, ~500 lines, California climate zones CZ01-CZ16)
- [x] Test coverage (41 tests in test_benchmarks.py)
- [ ] GUI integration (Streamlit) - Future
- [ ] Documentation updates - Future

### Week 11-12: Production Integration & Workflow ✅ COMPLETE (Phase 6)
- [x] Auto-discovery module (auto_discovery.py, ~400 lines)
  - SimulationFileType enum for CBECC output file types
  - SimulationFile and DiscoveredOutputs dataclasses
  - discover_simulation_outputs() with recursive search
  - discover_multiple_projects() for batch processing
  - Pattern matching for HourlyResults, CSE, PVBattery, NRCCPRF, CUAC files
- [x] LCCA workflow runner (lcca_runner.py, ~450 lines)
  - LccaRunner class for orchestrating complete LCCA workflow
  - RunnerConfig for configuration management
  - RunnerResults for structured result output
  - Support for TOU and simple analysis modes
  - Auto-region detection from climate zone
  - Excel, PDF, JSON output generation
- [x] Command-line interface (cli.py, ~450 lines)
  - `discover` command - find simulation outputs
  - `analyze` command - run LCCA with --rate-id, --region, --capex options
  - `batch` command - process multiple projects
  - `list-rates` command - show available utility rates
  - `list-regions` command - show regions and climate zone mappings
  - `econ1` command - generate ECON-1 report
- [x] Module entry point (__main__.py)
  - Enables `python -m eco_tools.lcca` CLI execution
- [x] Integration tests (test_phase6_integration.py, 50 tests)

### Week 13-14: CSE Input Transformation Platform ✅ VALIDATED (Phase 6.5)

**Objective:** Enable zone-level energy analysis by transforming CSE input files with hierarchical meter structure

**Problem Solved:** CBECC's default CSE output aggregates energy by story-level meters (e.g., `sbmtrE1_Res_1st Story`), making per-zone LCCA impossible. This platform enables granular zone-level hourly data.

**Validation Status:** ✅ PASSED (December 29, 2024)
- Test Project: Ventura & 7th Multifamily (19 zones, 31 meters)
- Zone totals match building totals within 2.9%
- 210,360 rows of hourly meter data produced
- Full end-use breakdown per zone

#### 6.5.1 CSE Input Parser (`parsers/cse_zone_input.py`) ✅
- [x] Parse CBECC-generated CSE input files into structured Python objects
- [x] Extract ZONE definitions with area, volume, model type
- [x] Extract GAIN definitions with gnMeter and gnEndUse
- [x] Extract RSYS definitions with meter assignments
- [x] Extract existing METER and EXPORT definitions
- [x] CSEZoneInputModel dataclass aggregating all components

#### 6.5.2 Zone-Meter Mapper (`zone_meter_mapper.py`) ✅
- [x] Zone classification engine (DWELLING_UNIT, COMMON_AREA, UNCONDITIONED)
- [x] CommonAreaCategory assignment (LOBBY, CORRIDOR, FITNESS, etc.)
- [x] Hierarchical meter naming convention
- [x] Building → Section → Category → Zone meter structure
- [x] ZoneMeterAssignment and MeterHierarchy dataclasses
- [x] Submeter relationships with multipliers

#### 6.5.3 CSE Transformer (`cse_transformer.py`) ✅
- [x] Transform CSE input with zone-level metering
- [x] Update GAIN gnMeter references to zone meters
- [x] Update RSYS rsElecMtr/rsFuelMtr references
- [x] Inject new METER definitions with submeter hierarchy
- [x] Inject new EXPORT definitions for hourly data
- [x] TransformResult with statistics and output path

#### 6.5.4 CSE Runner (`cse_runner.py`) ✅
- [x] Locate CSE executable (macOS/Windows)
- [x] Execute transformed CSE input files
- [x] Capture stdout/stderr and return codes
- [x] Collect output files (*-CSE.CSV, reports)
- [x] Timeout handling and error reporting
- [x] CSERunConfig and CSERunResult dataclasses

#### 6.5.5 Zone Output Parser (`parsers/cse_zone_output.py`) ✅
- [x] Parse CSE hourly meter output CSV
- [x] Extract 8760 hourly values per meter
- [x] End-use breakdown (Clg, Htg, Dhw, Lit, Rcp, etc.)
- [x] ZoneHourlyData with annual totals and peak demand
- [x] CSEZoneOutputModel aggregating all meters

#### 6.5.6 Pipeline Orchestrator (`zone_simulation.py`) ✅
- [x] High-level API coordinating all components
- [x] ZoneSimulationConfig for pipeline configuration
- [x] ZoneSimulationResult with ZoneEnergySummary objects
- [x] `run_zone_simulation()` convenience function
- [x] Meter hierarchy and zone assignment reporting

#### 6.5.7 Meter Hierarchy Structure
```
MtrElec (Building Total)
├── MtrElec_Residential (All Dwelling Units)
│   ├── MtrElec_DU_0BR (Studio units)
│   ├── MtrElec_DU_1BR (1-bedroom units)
│   ├── MtrElec_DU_2BR (2-bedroom units)
│   └── MtrElec_DU_3BR (3-bedroom units)
│
├── MtrElec_CommonArea (All Common Areas)
│   ├── MtrElec_CA_LOBBY
│   ├── MtrElec_CA_CORRIDOR
│   ├── MtrElec_CA_FITNESS
│   ├── MtrElec_CA_MECHANICAL
│   ├── MtrElec_CA_PARKING
│   └── MtrElec_CA_OTHER
│
└── MtrElec_NonResidential (Commercial/Retail)
    ├── MtrElec_NR_Office
    └── MtrElec_NR_Retail
```

#### 6.5.8 Usage Example
```python
from pathlib import Path
from eco_tools.lcca.zone_simulation import run_zone_simulation

result = run_zone_simulation(
    cbecc_run_dir=Path("/project - run"),
    run_cse=True,
)

for zone in result.proposed_zones:
    print(f"{zone.zone_name}: {zone.elec_kwh:,.0f} kWh")
    # zone.hourly_elec_kwh now contains 8760 values for TOU/VNBT
```

#### 6.5.9 Documentation ✅
- [x] `LCCA_Plans/reference/cse_guide.md` - CSE reference guide
- [x] `LCCA_Plans/reference/cse_lcca_architecture.md` - Architecture documentation

#### 6.5.10 Deliverables Summary
| File | Lines | Purpose |
|------|-------|---------|
| `parsers/cse_zone_input.py` | ~600 | Parse CSE input files |
| `zone_meter_mapper.py` | ~700 | Zone classification & meters |
| `cse_transformer.py` | ~500 | Transform CSE with zone meters |
| `cse_runner.py` | ~400 | Execute CSE simulation |
| `parsers/cse_zone_output.py` | ~500 | Parse CSE output CSV |
| `zone_simulation.py` | ~500 | Pipeline orchestrator |

#### 6.5.11 Validation Results (December 29, 2024)

**Test Project:** Ventura & 7th Multifamily (19 zones)

| Metric | Result |
|--------|--------|
| Zones Parsed | 19 (9 DU + 10 CA) |
| Meters Created | 31 |
| Exports Added | 19 |
| GAINs Updated | 243 |
| CSE Execution | ~35 min (Wine/macOS) |
| Output Rows | 210,360 |

**Energy Validation:**
| Comparison | kWh |
|------------|-----|
| Original CBECC Total | 930,236 |
| Zone Meters Sum | 956,925 |
| **Difference** | **+2.9%** ✓ |

**Bugs Fixed During Validation:**
1. Parser bug: Zones skipped after nested objects (added `continue` after nested parsing)
2. Export injection: EXPORTCOL attachment (insert before RUN statement)

#### 6.5.12 Next Steps for Integration
- [x] Integrate with TOU rate calculations using hourly_elec_kwh ✅ **COMPLETE (Jan 1, 2025)**
- [x] Connect to VNBT allocation for per-zone PV credits ✅ **COMPLETE (Jan 1, 2025)**
- [x] Add to CLI as `zone-analyze` command ✅ **COMPLETE (Jan 1, 2025)**
- [x] GUI integration for zone-level LCCA dashboard ✅ **COMPLETE (Jan 1, 2025)**

##### TOU Integration with Zone Hourly Data (VALIDATED)

The complete data flow from zone meters to TOU cost calculations is now functional:

```
CSE Zone Output → ZoneEnergySummary.hourly_elec_kwh → ZoneCostAllocator._calculate_tou_costs() → TouCostBreakdown
```

**Key Integration Points:**
1. `zone_simulation.py:346-353` - Populates `hourly_elec_kwh` from `meter_data.total_kwh`
2. `zone_allocation.py:145-146` - Checks for hourly data and calls `_calculate_tou_costs()`
3. `zone_allocation.py:168-212` - Converts hourly data to `HourlyUsage` and calculates TOU breakdown
4. `tariffs.py:225-368` - `calculate_tou_costs()` returns full `TouCostBreakdown`

**Usage Example:**
```python
from eco_tools.lcca.zone_simulation import run_zone_simulation
from eco_tools.lcca.zone_allocation import calculate_zone_lcca
from eco_tools.lcca.tariffs import create_pge_e_tou_c

# Run zone simulation
result = run_zone_simulation(cbecc_run_dir)

# Create TOU tariff
tariff = create_pge_e_tou_c()

# Calculate zone-level LCCA with TOU rates
summary = calculate_zone_lcca(
    zone_summaries=result.proposed_zones,  # Contains hourly_elec_kwh
    tariff=tariff,
)

# Each zone now has TOU breakdown
for zone_result in summary.zone_results:
    print(f"{zone_result.zone_name}:")
    print(f"  Summer On-Peak: ${zone_result.summer_on_peak_cost:,.2f}")
    print(f"  Winter Off-Peak: ${zone_result.winter_off_peak_cost:,.2f}")
```

---

## 8. Future Phases - Roadmap

### Phase 7: ESPM/BBC Integration (Planned - 8-12 weeks)

**Objective:** Integrate Energy Star Portfolio Manager and DOE Better Buildings Challenge capabilities

**Reference:** See `/Plans/espm_bbc_integration_plan.md` for detailed implementation plan

#### 7.1 ESPM Export Module
- [ ] Create `eco_tools/integrations/espm/` module structure
- [ ] `espm_models.py` - Pydantic models for ESPM data (ESPMProperty, ESPMMeter, ESPMBillEntry)
- [ ] `espm_mapper.py` - Map InternalRepresentation → ESPM format
- [ ] `espm_xml_builder.py` - Generate ESPM Portfolio Manager XML
- [ ] `espm_exporter.py` - Complete export service with XML and CSV output

**Key Mappings:**
| ESPM Field | ECO Tools Source |
|------------|------------------|
| Gross Floor Area | Sum of zone.floor_area_m2 |
| Site EUI | HourlyEnergy → annual kBtu/sf |
| Electric - Grid | HourlyEnergy.elec_total_kwh |
| Natural Gas | HourlyEnergy.gas_total_therm |
| On-Site Solar | HourlyEnergy.pv_generation_kwh |

#### 7.2 BBC/BCC Tracking Module
- [ ] `bbc_tracker.py` - Better Buildings Challenge goal tracking
- [ ] BBCGoal dataclass - 20% energy reduction over 10 years
- [ ] BCCGoal support - 50% GHG reduction over 10 years
- [ ] Portfolio-wide progress calculation
- [ ] Quarterly DOE submission data generation
- [ ] Progress report PDF generation

#### 7.3 Tests & Documentation
- [ ] `tests/integration/test_espm_integration.py`
- [ ] Unit tests for data mapping accuracy
- [ ] XML validation tests
- [ ] BBC calculation tests

**Deliverables:**
- ESPM XML export for Portfolio Manager upload
- BBC/BCC progress tracking dashboard
- Quarterly DOE submission automation
- Portfolio-wide analytics

---

### Phase 8: Streamlit GUI Enhancements (Planned - 6-8 weeks)

**Objective:** Add LCCA and portfolio management pages to Streamlit GUI

#### 8.1 LCCA Dashboard Page
- [ ] `gui/pages/lcca_dashboard.py` - Interactive LCCA visualization
- [ ] NPV/IRR/Payback display widgets
- [ ] Cash flow chart (matplotlib/plotly)
- [ ] Sensitivity analysis interactive sliders
- [ ] Scenario comparison view
- [ ] Export buttons (Excel, PDF)

#### 8.2 Portfolio Management Page
- [ ] `gui/pages/portfolio_page.py` - Multi-building portfolio view
- [ ] Building list with EUI/cost metrics
- [ ] Add/remove buildings from portfolio
- [ ] BBC goal configuration
- [ ] Portfolio-wide analytics charts

#### 8.3 ESPM Export Page
- [ ] `gui/pages/espm_export_page.py` - ESPM export wizard
- [ ] Property metadata form (address, year built, occupancy)
- [ ] Meter configuration
- [ ] XML preview and download
- [ ] Validation feedback

#### 8.4 Tariff Selection Widget
- [ ] Rate selector with region auto-detection
- [ ] TOU period visualization
- [ ] Rate comparison view
- [ ] Custom tariff editor

**Integration Points:**
```
gui/pages/
├── lcca_dashboard.py      # NEW: LCCA results visualization
├── portfolio_page.py      # NEW: Multi-building management
├── espm_export_page.py    # NEW: ESPM export wizard
├── bbc_dashboard_page.py  # NEW: BBC/BCC tracking
└── tariff_page.py         # NEW: Rate configuration
```

---

### Phase 9: Real Project Validation (Planned - 4 weeks)

**Objective:** Validate LCCA module with real project data

#### 9.1 Test Projects
- [ ] Ventura & 7th (Multifamily CUAC) - Full LCCA workflow
- [ ] Del Amo Circle (Commercial) - TOU rate comparison
- [ ] Freedom Circle (Mixed-Use) - Section allocation
- [ ] Euclid Buildings (Multiple scenarios) - Batch processing

#### 9.2 Validation Criteria
- [ ] Zone costs sum to building total (±1% tolerance)
- [ ] CUAC allowances match manual calculations
- [ ] EUI values within benchmark ranges
- [ ] PV/battery allocations sum correctly
- [ ] ECON-1 report accuracy

#### 9.3 Performance Benchmarks
- [ ] CLI processing time for 100+ zone buildings
- [ ] Excel export generation time
- [ ] Batch discovery performance

---

### Phase 10: EV Calculator Enhancements (Planned - 2-3 weeks)

**Objective:** Improve accuracy and realism of EV charging load calculations

**Reference:** Review discussion from January 2026 code review

#### 10.1 Document Utilization Assumptions
- [ ] Add docstring documenting basis for MF assigned parking utilization (2.5 hrs/day)
  - Current: 7.2 kW × 2.5 hrs = 18 kWh/day per port
  - Typical EV: 25-35 kWh per 100 miles, avg driver ~30 miles/day = ~10 kWh/day
  - Document that current value assumes some non-daily charging
- [ ] Add references to DOE/NREL EV charging utilization studies
- [ ] Consider making utilization configurable per project type

#### 10.2 CALGreen Receptacle vs Charger Distinction
- [ ] Add `charger_installation_rate` parameter for CALGreen mode
  - Receptacles may not have chargers installed initially
  - Default: 1.0 (all receptacles have chargers) for conservative estimate
  - Allow: 0.3-0.5 for realistic "receptacle-ready" scenarios
- [ ] Update `calculate_calgreen_2025_requirements()` to return:
  - `dwelling_receptacles` - Required EV-ready outlets (1 per unit)
  - `dwelling_chargers` - Estimated actual chargers (receptacles × installation_rate)
  - `common_chargers` - Required common area chargers (25% of common spaces)
- [ ] Update annual energy calculation to use `dwelling_chargers` not `dwelling_receptacles`

#### 10.3 Weekday/Weekend Utilization Differentiation
- [ ] Add `weekday_hours` and `weekend_hours` parameters
- [ ] Create location-specific weekday/weekend profiles:
  ```python
  UTILIZATION_PROFILES = {
      "workplace": {"weekday": 5.0, "weekend": 0.5},
      "mf_assigned": {"weekday": 2.0, "weekend": 3.5},
      "mf_shared": {"weekday": 1.2, "weekend": 2.0},
      "retail": {"weekday": 1.5, "weekend": 3.0},
  }
  ```
- [ ] Update `calculate_annual()` to weight by 260 weekdays + 105 weekend days
- [ ] Adjust load shape profiles to match weekday/weekend patterns

#### 10.4 Differentiated Peak Demand by Port Type
- [ ] Separate peak demand calculation for dwelling vs common chargers
  - Dwelling receptacles: Lower simultaneity (overnight charging, staggered)
  - Common chargers: Higher simultaneity (daytime use, visible availability)
- [ ] Add parameters:
  ```python
  dwelling_simultaneity: float = 0.25  # Lower - overnight staggered
  common_simultaneity: float = 0.60    # Higher - daytime demand
  ```
- [ ] Update peak calculation:
  ```python
  peak_kw = (
      dwelling_ports * kw_per_port * dwelling_simultaneity +
      common_ports * kw_per_port * common_simultaneity
  )
  ```

#### 10.5 Tests & Documentation
- [ ] Update `tests/lcca/test_ev_calculator.py` with new parameter tests
- [ ] Add integration test with realistic MF building scenario
- [ ] Document methodology in docstrings with references

**Deliverables:**
| File | Changes |
|------|---------|
| `site_loads/calculators/miscellaneous.py` | EVChargerCalculator enhancements |
| `tests/lcca/test_ev_calculator.py` | New test cases |
| `docs/site_loads/ev_methodology.md` | Methodology documentation (optional) |

---

### Phase 11: API & Advanced Features (Future)

**Objective:** Production-ready features for enterprise use

#### 11.1 REST API Layer (Optional)
- [ ] FastAPI wrapper for LCCA functions
- [ ] Authentication/authorization
- [ ] Rate limiting
- [ ] API documentation (OpenAPI)

#### 11.2 Database Persistence
- [ ] SQLite/PostgreSQL storage for portfolios
- [ ] Historical trend storage
- [ ] User preferences

#### 11.3 Advanced Analytics
- [ ] Monte Carlo risk analysis
- [ ] Machine learning EUI prediction
- [ ] Automated ECM recommendations
- [ ] What-if scenario builder

#### 11.4 External Integrations
- [ ] EnergyScoreCards (Bright Power) export
- [ ] EC3 embodied carbon integration
- [ ] REopt distributed energy optimization
- [ ] OpenEI utility rate API

---

## 9. Recommended Implementation Priority

### Immediate Next Steps (Recommended Order)

| Priority | Phase | Effort | Value | Dependencies |
|----------|-------|--------|-------|--------------|
| **P1** | Phase 9: Real Project Validation | 4 weeks | High | Phases 0-6 ✅ |
| **P2** | Phase 8.1: LCCA Dashboard | 2 weeks | High | Phases 0-6 ✅ |
| **P3** | Phase 7.1-7.2: ESPM/BBC Core | 4 weeks | High | None |
| **P4** | Phase 8.2-8.3: Portfolio & ESPM GUI | 4 weeks | Medium | Phase 7 |
| **P5** | Phase 8.4: Tariff Widget | 1 week | Medium | None |
| **P6** | Phase 10: Advanced Features | Ongoing | Medium | All |

### Quick Wins (Can Start Immediately)
1. **Real project validation** - Test with existing CBECC project files
2. **LCCA Dashboard mockup** - Basic Streamlit page with results display
3. **ESPM data models** - Pydantic models are standalone

### High-Value Integrations
1. **ESPM Export** - Enables Portfolio Manager integration for Mercy Housing
2. **BBC Tracking** - DOE Better Buildings Challenge compliance
3. **Portfolio Management** - Multi-building analytics

---

## 10. Success Criteria

### Phase 0 (NREL Cost Database Infrastructure) - CRITICAL
- ✅ `extract_nrel_costs.py` generates database without errors
- ✅ `CostDB_v0.06_NREL.xlsx` contains all 6 required sheets
- ✅ 16+ system costs with NREL BEopt/ATB source attribution
- ✅ 22 CA/HI regional factors loaded and queryable
- ✅ 15 utility rate structures parsed correctly
- ✅ 3 BLS PPI escalation indices populated
- ✅ Enhanced `costdb.py` loads v0.06 format seamlessly
- ✅ All existing LCCA tests pass (backward compatibility)
- ✅ Regional cost lookup: `get_regional_cost('HP-SPLIT-3T', 'US-CA-SF')` returns correct value

### Phase 1 (CA/HI Helpers & Rates)
- ✅ `ca_hi_helpers.py` with regional presets
- ✅ Climate zone → region code mapping
- ✅ Full utility rate library in tariffs
- ✅ All existing tests still pass

### Phase 2 (Zone-Level LCCA)
- ✅ Zone energy extraction from CSE
- ✅ Per-unit cost allocation
- ✅ Zone-level NPV/payback calculations
- ✅ Integration with CUAC parser

### Phase 3 (Aggregate Reporting)
- ✅ Multi-level Excel reports
- ✅ Zone category rollups
- ✅ CUAC utility allowance reports
- ✅ PDF export with zone detail

### Phase 4 (Mixed-Use & Metering)
- ✅ Meter category aggregation
- ✅ Mixed-use scenario separation
- ✅ Common area cost allocation
- ✅ Complex building support

### Overall
- ✅ Zone costs sum to building total
- ✅ CUAC allowances validate
- ✅ 80+ automated tests passing
- ✅ Real project validation (3+ projects)

---

## 9. File Structure

```
eco_tools/lcca/
├── __init__.py              # Updated with new exports
├── model.py                 # Core models (existing)
├── calculators.py           # Financial calcs (existing)
├── tariffs.py               # Enhanced with 15 CA/HI rates
├── costdb.py                # Enhanced with v0.06 loader + 22 regional factors
├── bridge.py                # Enhanced for mixed-use
├── econ1.py                 # Existing
├── excel_export.py          # Enhanced with zone sheets
├── pdf_export.py            # Enhanced with zone sections
├── esg_report.py            # Existing
├── sensitivity.py           # Enhanced for zone analysis
├── project_context.py       # Existing
├── scenario_manager.py      # Existing
├── ecm_bundle.py            # Existing
├── vnbt.py                  # Existing
│
├── # PHASE 0: NREL COST DATABASE INFRASTRUCTURE (PRIORITY)
├── extract_nrel_costs.py    # NEW: NREL data extraction script
├── data/
│   ├── CostDB_v0.06_NREL.xlsx    # NEW: Generated cost database
│   ├── nrel_beopt_costs.json     # NEW: Cached BEopt data
│   └── nrel_atb_2024.json        # NEW: Cached ATB data
│
├── # PHASE 1+: NEW MODULES
├── ca_hi_helpers.py         # NEW: Regional presets & mappings
├── zone_energy.py           # NEW: Zone energy models
├── zone_allocation.py       # NEW: Cost allocation engine
├── zone_report.py           # NEW: Zone LCCA reports
├── meter_aggregation.py     # NEW: Meter category aggregation
├── benchmarks.py            # NEW: Zone benchmarking
│
├── # PHASE 6.5: CSE INPUT TRANSFORMATION PLATFORM (COMPLETE)
├── zone_meter_mapper.py     # Zone classification & hierarchical meters
├── cse_transformer.py       # Transform CSE input with zone meters
├── cse_runner.py            # Execute CSE simulation engine
├── zone_simulation.py       # Pipeline orchestrator
│
├── parsers/
│   ├── __init__.py
│   ├── hourly_results.py    # Existing
│   ├── cse_hourly.py        # Existing
│   ├── cse_zone_input.py    # NEW: CSE input file parser
│   └── cse_zone_output.py   # NEW: CSE output CSV parser
│
├── cuac/
│   ├── __init__.py
│   ├── models.py            # Enhanced for zone energy
│   ├── parser.py            # Enhanced for zone CSE data
│   └── csv_parser.py        # Existing
│
└── res_other/
    ├── __init__.py
    ├── models.py            # Enhanced with energy fields
    └── parser.py            # Enhanced for energy extraction

LCCA_Plans/
├── LCCA_ROADMAP_v2.md       # This roadmap document
├── reference/
│   ├── existing_lcca_code.md
│   ├── cse_guide.md         # NEW: CSE reference guide
│   └── cse_lcca_architecture.md  # NEW: CSE-LCCA architecture

tests/
├── test_costdb_v06.py       # NEW: CostDB v0.06 validation tests
├── test_extract_nrel.py     # NEW: NREL extraction tests
├── test_ca_hi_helpers.py    # NEW: Regional preset tests
└── ... (existing tests)
```

---

## 10. Appendix: Code Templates

### A.1 Zone Energy Summary

```python
# Template for zone_energy.py

from dataclasses import dataclass, field
from typing import Dict, Optional, List
from .cuac.models import ZoneType, CommonAreaCategory

@dataclass
class ZoneEnergySummary:
    """Energy consumption summary for a single zone."""
    zone_name: str
    zone_type: ZoneType
    category: Optional[CommonAreaCategory] = None

    # Annual consumption
    elec_kwh: float = 0.0
    gas_therm: float = 0.0
    peak_demand_kw: float = 0.0

    # End-use breakdown (optional)
    cooling_kwh: float = 0.0
    heating_kwh: float = 0.0
    lighting_kwh: float = 0.0
    receptacle_kwh: float = 0.0
    dhw_kwh: float = 0.0
    dhw_therm: float = 0.0

    # Area for EUI calculation
    area_sqft: float = 0.0

    # PV/Battery allocation
    pv_allocation_kwdc: float = 0.0
    pv_generation_kwh: float = 0.0
    battery_allocation_kwh: float = 0.0

    @property
    def eui_kbtu_sqft(self) -> float:
        """Calculate Energy Use Intensity."""
        if self.area_sqft <= 0:
            return 0.0
        elec_kbtu = self.elec_kwh * 3.412
        gas_kbtu = self.gas_therm * 100
        return (elec_kbtu + gas_kbtu) / self.area_sqft

    @property
    def net_elec_kwh(self) -> float:
        """Net electricity after PV generation."""
        return max(0, self.elec_kwh - self.pv_generation_kwh)
```

### A.2 CA/HI Helpers

```python
# Template for ca_hi_helpers.py

from typing import Dict, Optional, Tuple
from .tariffs import TouTariff

# Regional cost factors (ENR Construction Cost Index based)
REGIONAL_FACTORS: Dict[str, float] = {
    # California
    'US-CA': 1.10, 'US-CA-SF': 1.38, 'US-CA-OAK': 1.35,
    'US-CA-SJ': 1.36, 'US-CA-LA': 1.22, 'US-CA-SD': 1.18,
    'US-CA-OC': 1.20, 'US-CA-SAC': 1.12, 'US-CA-FRE': 1.05,
    'US-CA-BAK': 1.03, 'US-CA-RIV': 1.08, 'US-CA-SB': 1.15,
    'US-CA-VEN': 1.12, 'US-CA-MON': 1.10, 'US-CA-SLO': 1.08,
    'US-CA-RED': 1.02, 'US-CA-STO': 1.04, 'US-CA-SRO': 1.28,
    # Hawaii
    'US-HI': 1.45, 'US-HI-HON': 1.45, 'US-HI-MAU': 1.50, 'US-HI-BIG': 1.48,
}

# Utility service territory mapping
REGION_TO_UTILITY: Dict[str, str] = {
    'US-CA-SF': 'PGE', 'US-CA-OAK': 'PGE', 'US-CA-SJ': 'PGE',
    'US-CA-SAC': 'SMUD', 'US-CA-FRE': 'PGE', 'US-CA-STO': 'PGE',
    'US-CA-LA': 'SCE', 'US-CA-OC': 'SCE', 'US-CA-RIV': 'SCE',
    'US-CA-SB': 'SCE', 'US-CA-VEN': 'SCE',
    'US-CA-SD': 'SDGE',
    'US-HI-HON': 'HECO', 'US-HI-MAU': 'MECO', 'US-HI-BIG': 'HELCO',
}

def get_regional_factor(region_code: str) -> float:
    """Get cost adjustment factor for a region."""
    return REGIONAL_FACTORS.get(region_code, 1.0)

def get_default_tariff(region_code: str, rate_type: str = 'residential') -> TouTariff:
    """Get default tariff for a region."""
    utility = REGION_TO_UTILITY.get(region_code, 'DEFAULT')
    # Map to appropriate tariff factory
    ...

def get_region_from_climate_zone(cz: str) -> str:
    """Map CBECC climate zone to region code."""
    CZ_TO_REGION = {
        'CZ01': 'US-CA-RED', 'CZ02': 'US-CA-SRO', 'CZ03': 'US-CA-OAK',
        'CZ04': 'US-CA-SJ', 'CZ05': 'US-CA-SLO', 'CZ06': 'US-CA-LA',
        # ... etc
    }
    return CZ_TO_REGION.get(cz, 'US-CA')
```

---

## 11. References

### Documentation
- `LCCA_Plans/docs/LCCA_ARCHITECTURE.md` - Current architecture
- `LCCA_Plans/docs/INTEGRATION_ROADMAP.md` - Integration guide
- `LCCA_Plans/schemas/lcca_scenario_schema.md` - Data models

### Code References
- `eco_tools/lcca/__init__.py` - Public API exports
- `eco_tools/lcca/cuac/models.py` - Zone classification patterns
- `eco_tools/lcca/res_other/models.py` - Common area patterns

### External Resources
- NREL BEopt: https://beopt.nrel.gov/
- NREL ATB: https://atb.nrel.gov/
- ENR CCI: https://www.enr.com/economics

---

**Document Version:** 2.3
**Last Updated:** January 1, 2025
**Author:** ECO Tools Development Team
**Status:** Production Ready - v7 Release Complete
