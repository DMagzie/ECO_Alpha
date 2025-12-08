# Simulation Output Requirements for LCCA

This document defines what simulation outputs the LCCA track needs to consume.

## Overview

LCCA calculations require energy consumption data from building simulations. The CBECC compliance run produces several output files that contain this data.

## Required Data Categories

### 1. Annual Energy Summary

| Metric | Units | Source | LCCA Use |
|--------|-------|--------|----------|
| Total Electricity | kWh/yr | CBECC results | Annual energy cost |
| Total Natural Gas | therms/yr | CBECC results | Annual energy cost |
| Peak Demand | kW | CBECC results | Demand charges |
| PV Generation | kWh/yr | CBECC results | Net energy calculation |

### 2. Hourly Energy Profiles (8760 Data)

Required for TOU rate calculations and demand analysis:

| Column | Units | Description |
|--------|-------|-------------|
| `datetime` | ISO 8601 | Hour timestamp |
| `elec_consumption` | kWh | Hourly electricity use |
| `gas_consumption` | therms | Hourly gas use |
| `elec_demand` | kW | Peak demand in hour |
| `pv_generation` | kWh | Hourly PV output |
| `battery_charge` | kWh | Battery state (if applicable) |

### 3. End-Use Breakdown

Required for identifying savings opportunities:

| End Use | Typical Categories |
|---------|-------------------|
| Heating | Gas furnace, heat pump, electric resistance |
| Cooling | DX, chiller, evaporative |
| Fans | Supply, return, exhaust |
| Pumps | CHW, HW, condenser |
| Lighting | Interior, exterior |
| Plug Loads | Equipment, receptacles |
| DHW | Water heating |
| Process | Special equipment |

### 4. TDV Data (California Specific)

Time Dependent Valuation for Title 24 compliance:

| Field | Units | Description |
|-------|-------|-------------|
| `tdv_elec` | TDV kBtu | Electricity TDV by hour |
| `tdv_gas` | TDV kBtu | Gas TDV by hour |
| `source_energy` | kBtu | Source energy by hour |

---

## CBECC Output Files

When CBECC runs a compliance analysis, it produces these relevant outputs:

### Primary Results Files

| File Pattern | Contents |
|--------------|----------|
| `*_Proposed.csv` | Proposed building hourly results |
| `*_Standard.csv` | Standard/baseline hourly results |
| `*_Results.xml` | Compliance summary (pass/fail, margins) |
| `*_Report.pdf` | Human-readable compliance report |

### Hourly CSV Structure (Typical)

```csv
Mo,Da,Hr,TotElecKwh,TotGasThm,ClgKwh,HtgThm,FanKwh,LtgKwh,DHWThm,...
1,1,1,125.5,2.3,0,1.8,45.2,30.1,0.5,...
1,1,2,118.2,2.1,0,1.6,42.1,30.1,0.5,...
...
```

### Key Columns to Extract

| CBECC Column | Maps To | Units |
|--------------|---------|-------|
| `TotElecKwh` | Total electricity | kWh |
| `TotGasThm` | Total gas | therms |
| `ClgKwh` | Cooling electricity | kWh |
| `HtgThm` or `HtgKwh` | Heating | therms or kWh |
| `FanKwh` | Fan electricity | kWh |
| `PumpKwh` | Pump electricity | kWh |
| `LtgKwh` | Lighting | kWh |
| `DHWThm` or `DHWKwh` | DHW | therms or kWh |
| `PVKwh` | PV generation | kWh |

---

## Standardized LCCA Energy Schema

Proposed schema for simulation outputs consumed by LCCA:

```python
@dataclass
class HourlyEnergyRecord:
    """Single hour of energy data."""
    month: int           # 1-12
    day: int             # 1-31
    hour: int            # 1-24
    elec_total_kwh: float
    gas_total_therm: float
    elec_cooling_kwh: float
    elec_heating_kwh: float
    gas_heating_therm: float
    elec_fans_kwh: float
    elec_pumps_kwh: float
    elec_lighting_kwh: float
    elec_plugs_kwh: float
    gas_dhw_therm: float
    elec_dhw_kwh: float
    pv_generation_kwh: float
    battery_discharge_kwh: float

@dataclass
class AnnualEnergySummary:
    """Annual rollup for quick LCCA calculations."""
    total_elec_kwh: float
    total_gas_therm: float
    peak_demand_kw: float
    pv_generation_kwh: float
    net_elec_kwh: float      # total - pv

    # End-use breakdown
    cooling_kwh: float
    heating_kwh: float
    heating_therm: float
    fans_kwh: float
    pumps_kwh: float
    lighting_kwh: float
    plugs_kwh: float
    dhw_kwh: float
    dhw_therm: float

@dataclass
class SimulationResults:
    """Complete simulation output package for LCCA."""
    project_name: str
    climate_zone: str
    building_type: str
    floor_area_sf: float

    # Annual summary
    proposed: AnnualEnergySummary
    baseline: AnnualEnergySummary  # Optional, for savings calc

    # Hourly data
    hourly_proposed: List[HourlyEnergyRecord]
    hourly_baseline: List[HourlyEnergyRecord]  # Optional

    # TDV (California)
    tdv_proposed: float  # Total TDV kBtu
    tdv_baseline: float
    tdv_margin: float    # Compliance margin
```

---

## Implementation Tasks

### Phase 1: CBECC Output Parser
- [ ] Parse `*_Proposed.csv` hourly files
- [ ] Parse `*_Standard.csv` baseline files
- [ ] Extract annual summaries
- [ ] Handle different CBECC versions (2022, 2025)

### Phase 2: Standardized Schema
- [ ] Define `SimulationResults` dataclass
- [ ] Create JSON schema for interchange
- [ ] Add to EMJSON v6 as optional extension

### Phase 3: LCCA Integration
- [ ] Connect parser output to `LccaScenario.energy`
- [ ] Implement TOU rate calculations from hourly data
- [ ] Calculate demand charges from peak analysis

---

## Sample Data Locations

To be populated with paths to sample CBECC simulation outputs for testing.
