# Site Load Integration Plan for LCCA

**Version:** 1.0
**Date:** December 2024
**Status:** Planning

---

## Executive Summary

The current LCCA workflow only processes modeled energy from CBECC simulations. However, real building energy consumption includes significant non-modeled site loads that must be captured for accurate whole-building LCCA. This plan outlines the integration of existing ad-hoc site load calculators into a formalized LCCA workflow.

---

## 1. The Gap: Modeled vs. Whole-Building Energy

### Current State (Modeled Only)

```
┌─────────────────────────────────────────────────────────────┐
│                    CBECC SIMULATION                          │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐         │
│  │   HVAC      │  │  Lighting   │  │    DHW      │         │
│  │  (Zones)    │  │  (Interior) │  │  (Modeled)  │         │
│  └─────────────┘  └─────────────┘  └─────────────┘         │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐         │
│  │ Receptacles │  │    Fans     │  │     PV      │         │
│  │   (Plug)    │  │(Ventilation)│  │  (Battery)  │         │
│  └─────────────┘  └─────────────┘  └─────────────┘         │
└─────────────────────────────────────────────────────────────┘
                           ↓
                   Current LCCA Workflow
```

### Target State (Whole-Building)

```
┌─────────────────────────────────────────────────────────────┐
│                    CBECC SIMULATION                          │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐         │
│  │   HVAC      │  │  Lighting   │  │    DHW      │         │
│  │  (Zones)    │  │  (Interior) │  │  (Modeled)  │         │
│  └─────────────┘  └─────────────┘  └─────────────┘         │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐         │
│  │ Receptacles │  │    Fans     │  │     PV      │         │
│  │   (Plug)    │  │(Ventilation)│  │  (Battery)  │         │
│  └─────────────┘  └─────────────┘  └─────────────┘         │
└─────────────────────────────────────────────────────────────┘
                           +
┌─────────────────────────────────────────────────────────────┐
│                NON-MODELED SITE LOADS                        │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐         │
│  │  Common     │  │  Parking    │  │    Site     │         │
│  │  Area Ltg   │  │  Garage     │  │  Lighting   │         │
│  └─────────────┘  └─────────────┘  └─────────────┘         │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐         │
│  │   Pools     │  │     EV      │  │  Elevators  │         │
│  │   & Spas    │  │  Chargers   │  │             │         │
│  └─────────────┘  └─────────────┘  └─────────────┘         │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐         │
│  │  Fire       │  │  Booster    │  │  HW Circ    │         │
│  │   Pump      │  │   Pump      │  │   Pump      │         │
│  └─────────────┘  └─────────────┘  └─────────────┘         │
└─────────────────────────────────────────────────────────────┘
                           ↓
                Whole-Building LCCA Workflow
```

---

## 2. Existing Work Analysis

### Source Files

Location: `/Users/DavidM/Documents/ECO_Alpha_v7/LCCA Tests/Site Load Calculators/`

| File | Purpose | Status |
|------|---------|--------|
| `NonRes Common Area Energy Calculator.xlsx` | Baseline template | Production |
| `Nonres_Common_Area_Energy_Calculator_2025-10-30.xlsx` | Latest with pumps | Production |
| `GBCI Pool Energy Calculator_v01 DRAFT.xlsx` | Pool-specific | Draft |
| `Project Name_House Meter Calculation Summary.xlsx` | Integration template | Production |
| `Project Name_House Meter Calculations.docx` | Documentation | Reference |

### Load Categories Identified

#### Original Categories (from Excel calculators)

| Category | Sub-Categories | Energy Type | Source Standard |
|----------|----------------|-------------|-----------------|
| Interior Lighting | 14 space types (corridors, stairs, lobbies, offices, restrooms, etc.) | Electric | Title 24 2022 Table 140.6-C |
| Parking Garage | Lighting, Mechanical Ventilation | Electric | NRCC-LTO, ASHRAE 62.1 |
| Site Lighting | Hardscape, Parking | Electric | NRCC-LTO |
| Pool/Spa | Pump, Heater | Electric + Gas | ENERGY STAR, DOE |
| EV Chargers | Level 2 ports | Electric | Usage assumptions |
| Elevators | Fixed empirical | Electric | Industry data |
| Water Pumps | Fire pump, Booster, HW circulator | Electric | Equipment specs |

#### Additional Categories (from research - December 2024)

| Category | Sub-Categories | Energy Type | Source/Rationale |
|----------|----------------|-------------|------------------|
| IT/Telecom Rooms | Server closets, Network equipment | Electric | [DOE](https://www.osti.gov/biblio/1172953) - can be 50%+ of building energy |
| Trash Handling | Compactors, Chutes, Balers | Electric | [WM SmartEnergy](https://www.wm.com/us/en/business/business-waste-compactors) |
| Commercial Kitchen | Refrigeration, Cooking, Dishwashing, Hoods | Electric + Gas | [DOE](https://buildingenergyscore.energy.gov) - 5-7x energy intensity |
| Common Laundry | Washers, Dryers | Electric + Gas | Per-machine energy |
| Security Systems | Cameras, Access Control, Monitoring | Electric | 24/7 operation |
| Fire/Life Safety | Alarm Panels, Emergency Lighting | Electric | 24/7 standby |
| Irrigation | Landscape Pumps, Controllers | Electric | Seasonal operation |
| Exhaust Systems | Garage Exhaust, Trash Room, Kitchen Hoods | Electric | Continuous/intermittent |
| Miscellaneous | Vending, Ice Makers, Signage, Escalators, Snowmelt | Electric + Gas | Various |

**Research Sources:**
- [ASHRAE 90.1](https://www.ashrae.org/technical-resources/bookstore/standard-90-1) - Energy efficiency standards
- [DOE Better Buildings - Plug & Process Loads](https://betterbuildingssolutioncenter.energy.gov/plug-process-loads) - PPL consumes ~47% of commercial building energy
- [LEED EAp2](https://leeduser.buildinggreen.com/credit/NC-v4/EAp2) - Unregulated/process load requirements
- [EIA CBECS](https://www.eia.gov/consumption/commercial/) - Commercial building energy benchmarks

### Key Formulas (Extracted)

```python
# Interior Lighting
kwh = area_sf * lpd_w_per_sf / 1000 * hours_per_year * control_factor * diversity_factor

# Motor/Pump Loads
kwh = hp * 0.746 / efficiency * hours_per_day * days_per_year

# EV Charging
kwh = num_ports * kw_per_port * hours_per_day * 365

# Elevator (Empirical)
kwh = num_elevators * 8000  # Fixed annual value

# Pool Heater (Gas)
therms = mbtu_per_sqft_lookup * area * months / efficiency / 100

# Annual Cost
cost = (kwh * rate_per_kwh) + (therms * rate_per_therm) + (kw_peak * rate_per_kw * months)
```

---

## 3. Proposed Architecture

### 3.1 New Module: `eco_tools/lcca/site_loads/`

**Data Collection Specification:** See `SITE_LOAD_DATA_COLLECTION_SPEC.md` for complete input format and Excel template design.

```
eco_tools/lcca/
├── site_loads/
│   ├── __init__.py              - Public API exports
│   ├── model.py                 - Data models (SiteLoad, LoadCategory, etc.)
│   ├── importer.py              - Excel/JSON import functions
│   ├── calculators/
│   │   ├── __init__.py
│   │   ├── lighting.py          - Interior & exterior lighting
│   │   ├── parking.py           - Garage lighting & ventilation
│   │   ├── pools.py             - Pool pump & heater
│   │   ├── ev_charging.py       - EV charger loads
│   │   ├── vertical_transport.py - Elevators & escalators
│   │   ├── pumps.py             - Fire, booster, circulator, irrigation pumps
│   │   ├── it_telecom.py        - Server rooms, IT closets (NEW)
│   │   ├── trash.py             - Compactors, balers (NEW)
│   │   ├── kitchen.py           - Commercial kitchen equipment (NEW)
│   │   ├── laundry.py           - Common laundry facilities (NEW)
│   │   ├── security.py          - Security & life safety systems (NEW)
│   │   └── misc.py              - Vending, signage, exhaust, snowmelt (NEW)
│   ├── reference_data/
│   │   ├── title24_lpd.json     - LPD lookup table
│   │   ├── energy_star_pools.json - Pool pump curves
│   │   ├── doe_pool_heaters.json  - Heater baseline by climate
│   │   ├── elevator_baselines.json - Empirical elevator data
│   │   └── equipment_defaults.json - Default values for all equipment
│   ├── templates/
│   │   └── site_load_template.xlsx - Blank Excel template for data collection
│   └── aggregator.py            - Combine all site loads
```

### 3.2 Data Model

```python
from dataclasses import dataclass, field
from typing import List, Optional, Dict
from enum import Enum

class LoadCategory(Enum):
    INTERIOR_LIGHTING = "interior_lighting"
    PARKING_GARAGE = "parking_garage"
    SITE_LIGHTING = "site_lighting"
    POOL_SPA = "pool_spa"
    EV_CHARGING = "ev_charging"
    ELEVATOR = "elevator"
    WATER_PUMPS = "water_pumps"
    IT_TELECOM = "it_telecom"           # NEW
    TRASH_HANDLING = "trash_handling"   # NEW
    COMMERCIAL_KITCHEN = "kitchen"      # NEW
    COMMON_LAUNDRY = "laundry"          # NEW
    SECURITY_LIFE_SAFETY = "security"   # NEW
    MISCELLANEOUS = "misc"              # NEW (vending, signage, etc.)

@dataclass
class SiteLoad:
    """Individual site load component."""
    name: str
    category: LoadCategory
    annual_kwh: float = 0.0
    annual_therms: float = 0.0
    peak_kw: float = 0.0

    # Calculation inputs (for audit trail)
    area_sf: Optional[float] = None
    quantity: Optional[int] = None
    hours_per_year: Optional[float] = None
    power_density_w_sf: Optional[float] = None
    control_factor: float = 1.0
    diversity_factor: float = 1.0

    # Source reference
    calculation_method: str = ""
    source_standard: str = ""

@dataclass
class SiteLoadProfile:
    """Complete site load profile for a building."""
    project_name: str
    loads: List[SiteLoad] = field(default_factory=list)

    # Optional hourly profiles for TOU analysis
    hourly_kwh: Optional[List[float]] = None  # 8760 values
    hourly_therms: Optional[List[float]] = None

    @property
    def total_annual_kwh(self) -> float:
        return sum(load.annual_kwh for load in self.loads)

    @property
    def total_annual_therms(self) -> float:
        return sum(load.annual_therms for load in self.loads)

    @property
    def total_peak_kw(self) -> float:
        # Note: Not simple sum - needs diversity analysis
        return sum(load.peak_kw * load.diversity_factor for load in self.loads)

    def by_category(self) -> Dict[LoadCategory, List[SiteLoad]]:
        """Group loads by category."""
        result = {}
        for load in self.loads:
            if load.category not in result:
                result[load.category] = []
            result[load.category].append(load)
        return result

@dataclass
class WholeBuildingEnergy:
    """Combined modeled + site load energy."""
    project_name: str

    # From CBECC simulation
    modeled_annual_kwh: float
    modeled_annual_therms: float
    modeled_peak_kw: float

    # From site load calculations
    site_load_profile: SiteLoadProfile

    # PV/Battery (modeled)
    pv_generation_kwh: float = 0.0
    battery_capacity_kwh: float = 0.0

    @property
    def gross_annual_kwh(self) -> float:
        return self.modeled_annual_kwh + self.site_load_profile.total_annual_kwh

    @property
    def gross_annual_therms(self) -> float:
        return self.modeled_annual_therms + self.site_load_profile.total_annual_therms

    @property
    def net_annual_kwh(self) -> float:
        return self.gross_annual_kwh - self.pv_generation_kwh

    @property
    def total_peak_kw(self) -> float:
        # Simplified - actual would require coincident peak analysis
        return self.modeled_peak_kw + self.site_load_profile.total_peak_kw
```

### 3.3 Integration with Existing LCCA

```python
# Updated bridge.py integration

def simulation_to_lcca_with_site_loads(
    sim: SimulationOutput,
    site_loads: SiteLoadProfile,
    tariff: Tariff,
    capital_cost: float = 0.0,
    incentives: List[Incentive] = None
) -> LccaScenario:
    """Bridge simulation + site loads to LCCA scenario."""

    # Combine energy streams
    combined_energy = EnergyStreams(
        electricity_kwh=sim.annual.total_elec_kwh + site_loads.total_annual_kwh,
        gas_therms=sim.annual.total_gas_therm + site_loads.total_annual_therms,
        demand_kw=sim.annual.peak_demand_kw + site_loads.total_peak_kw,
        pv_generation_kwh=sim.pv_generation_kwh
    )

    return LccaScenario(
        name=f"{sim.project_name} (Whole Building)",
        capex_upfront=capital_cost,
        energy=combined_energy,
        tariff=tariff,
        incentives=incentives or [],
        assumptions=ScenarioAssumptions()
    )
```

### 3.4 Updated Data Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    WHOLE-BUILDING LCCA DATA FLOW                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  MODELED ENERGY                        NON-MODELED SITE LOADS               │
│  ┌──────────────────┐                  ┌──────────────────────┐             │
│  │ *-HourlyResults  │                  │ Site Load Inputs     │             │
│  │ CSV (CBECC)      │                  │ (JSON/Excel/Manual)  │             │
│  └────────┬─────────┘                  └──────────┬───────────┘             │
│           │                                       │                          │
│           ▼                                       ▼                          │
│  ┌─────────────────────┐              ┌─────────────────────────┐           │
│  │ PARSERS LAYER       │              │ SITE LOAD CALCULATORS   │           │
│  │ hourly_results.py   │              │ lighting.py, pools.py   │           │
│  │ cse_hourly.py       │              │ ev_charging.py, etc.    │           │
│  └─────────┬───────────┘              └───────────┬─────────────┘           │
│            │                                      │                          │
│            ▼                                      ▼                          │
│  ┌─────────────────────┐              ┌─────────────────────────┐           │
│  │ SimulationOutput    │              │ SiteLoadProfile         │           │
│  │ (8760 hourly)       │              │ (annual or hourly)      │           │
│  └─────────┬───────────┘              └───────────┬─────────────┘           │
│            │                                      │                          │
│            └──────────────┬───────────────────────┘                         │
│                           ▼                                                  │
│              ┌─────────────────────────┐                                    │
│              │ WholeBuildingEnergy     │                                    │
│              │ (Modeled + Site Loads)  │                                    │
│              └───────────┬─────────────┘                                    │
│                          │                                                   │
│           ┌──────────────┼──────────────┐                                   │
│           ▼              ▼              ▼                                   │
│  ┌────────────┐ ┌────────────┐ ┌────────────┐                              │
│  │  ECON-1    │ │  TOU RATE  │ │   BRIDGE   │                              │
│  │  Reports   │ │  Engine    │ │  Functions │                              │
│  └─────┬──────┘ └─────┬──────┘ └─────┬──────┘                              │
│        │              │              │                                       │
│        │              │              ▼                                       │
│        │              │     ┌────────────────┐                              │
│        │              │     │ LccaScenario   │◄──── CostDB                  │
│        │              │     │ (Whole Bldg)   │◄──── Site Load Costs         │
│        │              │     └───────┬────────┘                              │
│        │              │             │                                        │
│        │              │             ▼                                        │
│        │              │     ┌────────────────┐                              │
│        │              │     │  CALCULATORS   │                              │
│        │              │     │  NPV, IRR, SIR │                              │
│        │              │     └───────┬────────┘                              │
│        │              │             │                                        │
│        ▼              ▼             ▼                                        │
│  ┌───────────────────────────────────────────┐                              │
│  │              OUTPUT LAYER                  │                              │
│  │  ┌─────────┐ ┌─────────┐ ┌─────────┐     │                              │
│  │  │  Excel  │ │   PDF   │ │   ESG   │     │                              │
│  │  │Dashboard│ │ Reports │ │ Reports │     │                              │
│  │  └─────────┘ └─────────┘ └─────────┘     │                              │
│  └───────────────────────────────────────────┘                              │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 4. Reference Data Requirements

### 4.1 Title 24 LPD Table (Lighting)

```json
{
  "source": "Title 24 2022 Table 140.6-C",
  "space_types": {
    "corridor": {"lpd_w_sf": 0.40, "default_hours": 4380},
    "stairwell": {"lpd_w_sf": 0.49, "default_hours": 4380},
    "lobby": {"lpd_w_sf": 0.65, "default_hours": 4380},
    "office": {"lpd_w_sf": 0.65, "default_hours": 2600},
    "restroom": {"lpd_w_sf": 0.63, "default_hours": 2600},
    "kitchen": {"lpd_w_sf": 0.95, "default_hours": 2600},
    "laundry": {"lpd_w_sf": 0.53, "default_hours": 2600},
    "mechanical": {"lpd_w_sf": 0.43, "default_hours": 1000},
    "storage": {"lpd_w_sf": 0.42, "default_hours": 1000},
    "fitness": {"lpd_w_sf": 0.72, "default_hours": 4380},
    "conference": {"lpd_w_sf": 0.80, "default_hours": 2600},
    "leasing": {"lpd_w_sf": 0.65, "default_hours": 2600},
    "mail_room": {"lpd_w_sf": 0.53, "default_hours": 2600},
    "trash": {"lpd_w_sf": 0.42, "default_hours": 1000}
  }
}
```

### 4.2 Pool Energy Data (DOE/ENERGY STAR)

```json
{
  "pump_efficiency": {
    "single_speed": {"ef": 3.8, "hours_per_day": 8},
    "two_speed": {"ef": 5.5, "hours_per_day": 10},
    "variable_speed": {"ef": 8.5, "hours_per_day": 12}
  },
  "heater_baseline_mbtu_per_sqft_month": {
    "climate_zone_1": {"78F_no_cover": 12.5, "78F_with_cover": 6.2},
    "climate_zone_2": {"78F_no_cover": 10.8, "78F_with_cover": 5.4},
    "climate_zone_3": {"78F_no_cover": 9.2, "78F_with_cover": 4.6},
    "climate_zone_4": {"78F_no_cover": 7.5, "78F_with_cover": 3.8},
    "climate_zone_5": {"78F_no_cover": 5.8, "78F_with_cover": 2.9},
    "climate_zone_6": {"78F_no_cover": 4.2, "78F_with_cover": 2.1}
  }
}
```

### 4.3 Elevator Baseline Data

```json
{
  "source": "VDI 4707 / ENERGY STAR",
  "elevator_types": {
    "hydraulic_small": {"kwh_per_year": 6000, "capacity_lbs": 2500},
    "hydraulic_standard": {"kwh_per_year": 8000, "capacity_lbs": 3500},
    "traction_geared": {"kwh_per_year": 10000, "capacity_lbs": 4000},
    "traction_gearless": {"kwh_per_year": 7500, "capacity_lbs": 4000},
    "machine_room_less": {"kwh_per_year": 5500, "capacity_lbs": 3500}
  },
  "usage_factors": {
    "low_rise_residential": 0.7,
    "mid_rise_residential": 1.0,
    "high_rise_residential": 1.3,
    "office": 1.2
  }
}
```

---

## 5. Implementation Phases

### Phase 1: Core Infrastructure

**Goal**: Establish data models and basic calculators

**Tasks**:
- [ ] Create `eco_tools/lcca/site_loads/` module structure
- [ ] Implement `model.py` with SiteLoad, SiteLoadProfile, WholeBuildingEnergy
- [ ] Create reference data JSON files from Excel lookups
- [ ] Implement `lighting.py` calculator (interior + site)
- [ ] Add unit tests for lighting calculations

**Acceptance Criteria**:
- Can calculate interior lighting load from space type + area
- Results match existing Excel calculator within 1%

### Phase 2: Additional Calculators

**Goal**: Complete all load category calculators

**Tasks**:
- [ ] Implement `parking.py` (lighting + ventilation)
- [ ] Implement `pools.py` (pump + heater)
- [ ] Implement `ev_charging.py`
- [ ] Implement `vertical_transport.py` (elevators)
- [ ] Implement `pumps.py` (fire, booster, HW circulator)
- [ ] Implement `aggregator.py` to combine all loads
- [ ] Add unit tests for each calculator

**Acceptance Criteria**:
- All calculators produce results matching Excel templates
- Aggregator correctly sums loads by category

### Phase 3: LCCA Integration

**Goal**: Connect site loads to existing LCCA workflow

**Tasks**:
- [ ] Update `bridge.py` with `simulation_to_lcca_with_site_loads()`
- [ ] Update `WholeBuildingEnergy` class to merge modeled + site loads
- [ ] Add site load breakdown to ECON-1 reports
- [ ] Add site load section to Excel export
- [ ] Add site load section to ESG reports
- [ ] Update API exports in `__init__.py`

**Acceptance Criteria**:
- Can run complete LCCA with modeled + site loads
- Reports show clear breakdown of modeled vs. site load energy

### Phase 4: Input/Output Integration

**Goal**: Support multiple input/output formats

**Tasks**:
- [ ] Create JSON input schema for site load parameters
- [ ] Create Excel input template (simplified from current)
- [ ] Add site load importer from Excel
- [ ] Add site load section to PDF export
- [ ] Create CLI command for site load calculations

**Acceptance Criteria**:
- Can import site load inputs from JSON or Excel
- Complete workflow: Input → Calculate → LCCA → Export

### Phase 5: Hourly Profile Generation (Optional)

**Goal**: Enable TOU analysis for site loads

**Tasks**:
- [ ] Create hourly load shape profiles by category
- [ ] Generate 8760 hourly data from annual totals
- [ ] Integrate with TOU rate engine
- [ ] Add coincident peak analysis

**Acceptance Criteria**:
- Can apply TOU rates to site loads
- Accurate demand charge calculation

---

## 6. Migration Path for Existing Work

### Current Excel Files → Python Module

| Excel Component | Python Destination | Migration Notes |
|-----------------|-------------------|-----------------|
| LPD lookup table | `reference_data/title24_lpd.json` | Direct translation |
| Lighting calculation formulas | `calculators/lighting.py` | Parametrize |
| Pool pump curves | `reference_data/energy_star_pools.json` | Include EF ratings |
| DOE heater baselines | `reference_data/doe_pool_heaters.json` | By climate zone |
| Utility rate shells | Existing `tariffs.py` | Already implemented |
| Report_Client format | `excel_export.py` extension | Add site load section |

### Backward Compatibility

The Excel calculators will remain usable for:
- Quick manual calculations
- Client presentations
- Validation of Python results

The Python implementation provides:
- Automation capability
- Integration with CBECC workflow
- Programmatic access for batch processing
- Version control and testing

---

## 7. Testing Strategy

### Unit Tests

```python
class TestInteriorLighting:
    def test_corridor_calculation(self):
        """Verify corridor lighting matches Excel template."""
        result = calculate_interior_lighting(
            space_type="corridor",
            area_sf=36433,
            hours_per_year=4380,
            control_factor=0.8,
            diversity_factor=0.9
        )
        assert abs(result.annual_kwh - 45831) < 100  # Within 100 kWh

class TestPoolCalculator:
    def test_pool_pump_energy(self):
        """Verify pool pump calculation matches ENERGY STAR method."""
        result = calculate_pool_pump(
            pump_hp=1.5,
            pump_type="variable_speed",
            hours_per_day=12
        )
        assert result.annual_kwh > 0

class TestWholeBuildingIntegration:
    def test_combined_energy(self):
        """Verify modeled + site loads combine correctly."""
        sim = parse_hourly_results("test_data/sample.csv")
        site = calculate_all_site_loads(test_inputs)
        whole = WholeBuildingEnergy(sim, site)

        assert whole.gross_annual_kwh == sim.annual.total_elec_kwh + site.total_annual_kwh
```

### Integration Tests

- Load sample project from existing Excel
- Calculate all site loads
- Compare to Excel results
- Verify LCCA output includes site loads

### Regression Tests

- Re-run existing LCCA tests
- Verify no changes to modeled-only calculations
- Verify site loads add correctly when included

---

## 8. Documentation Requirements

### User Documentation

- [ ] Site Load Calculator User Guide
- [ ] Input parameter reference
- [ ] Example workflows

### Technical Documentation

- [ ] API reference for site_loads module
- [ ] Reference data sources and update procedures
- [ ] Validation methodology

### Migration Documentation

- [ ] Guide for converting Excel workflows to Python
- [ ] Comparison of Excel vs. Python results

---

## 9. Success Metrics

| Metric | Target |
|--------|--------|
| Calculator accuracy | Within 1% of Excel templates |
| LCCA runtime | < 5 seconds for whole-building analysis |
| Test coverage | > 90% for site_loads module |
| Documentation | 100% of public API documented |

---

## 10. Dependencies

### Required

- Python 3.9+
- Existing LCCA module (`eco_tools/lcca/`)
- openpyxl (for Excel I/O)

### Optional

- reportlab (for PDF with site load section)

---

## 11. Risks and Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Reference data becomes outdated | Incorrect calculations | Document data sources, create update procedure |
| Hourly profiles inaccurate | TOU costs wrong | Validate against metered data when available |
| Integration breaks existing LCCA | Regression | Comprehensive test suite, backward compatibility |
| Complex Excel formulas hard to replicate | Migration delays | Start with simplest calculators, validate incrementally |

---

## 12. File Locations

| Resource | Path |
|----------|------|
| Existing Excel calculators | `LCCA Tests/Site Load Calculators/` |
| New Python module | `eco_tools/lcca/site_loads/` |
| Reference data | `eco_tools/lcca/site_loads/reference_data/` |
| Tests | `tests/test_site_loads.py` |
| This plan | `LCCA_Plans/docs/SITE_LOAD_INTEGRATION_PLAN.md` |

---

**Last Updated**: December 29, 2024
