# Site Load Modeling Guide

## Overview

This document describes which loads can be modeled in CBECC vs calculated separately,
and the standardized workflow for ensuring accurate whole-building energy analysis.

## CBECC Modeling Capabilities

### Elevator and Escalator Loads

**Status: CAN BE MODELED in CBECC**

CBECC has properties for elevator and escalator loads at the space/zone level:

| Property | Element | Description |
|----------|---------|-------------|
| `ElevCnt` | Spc / ResOtherZn | Number of elevators |
| `ElevPwr` | Spc / ResOtherZn | Elevator power (kW) |
| `ElevLostFrac` | Spc / ResOtherZn | Fraction of energy as heat to space |
| `EscalCnt` | Spc | Number of escalators |
| `EscalPwr` | Spc | Escalator power (kW) |
| `EscalLostFrac` | Spc | Fraction of energy as heat to space |

**Rule File:** `Space-ElevatorEscalator.rule`

**CEC Standard Values:**
- CBECC uses CEC-defined process load values that may not reflect actual installed equipment
- Consider overriding with manufacturer data or ASHRAE 90.1 Appendix G values for better accuracy

**Recommendation:**
- For compliance models: Use CEC standard checkbox
- For LCCA models: Override with actual equipment data if available

### Parking Garage Exhaust

**Status: CAN BE MODELED in CBECC**

CBECC has properties for parking garage ventilation:

| Property | Element | Description |
|----------|---------|-------------|
| `PrkgGarExhFlow` | ResOtherZn | Exhaust airflow (CFM) |
| `PrkgGarExhFanPwr` | ResOtherZn | Fan power (W/CFM) |
| `PrkgGarExhCtrlMthd` | ResOtherZn | Control method (NoCOControl, etc.) |
| `PrkgGarArea` | ResOtherZn | Parking area (SF) |
| `PrkgGarVentFlow` | ResOtherZn | Ventilation flow (CFM) |

**Typical Compliance Models:**
- These properties default to 0 (not modeled)
- Garage lighting and HVAC are modeled, but exhaust fans often omitted

**Recommendation:**
- ALWAYS model garage exhaust in CBECC for accurate whole-building analysis
- Use templatized inputs from intake form if not in original model

### Central Ventilation (Common Areas)

**Status: MODELED in CBECC**

| Property | Element | Description |
|----------|---------|-------------|
| `IAQOption` | ResOtherZn | Ventilation type ("Central Supply / Central Exhaust") |
| `CentralVentSysRef` | ResOtherZn | Reference to central system |
| `CentralExhaustCFM` | ResOtherZn | Central exhaust airflow |
| `CentralSupplyCFM` | ResOtherZn | Central supply airflow |

**Status:** Usually modeled for corridors, lobbies. Energy included in HVAC fan energy.

### EV Charging

**Status: NOT FULLY MODELED in CBECC (as of 2022/2025)**

CBECC has limited EV infrastructure properties:

| Property | Element | Description |
|----------|---------|-------------|
| `CALGreen` | ResProj | CALGreen compliance flag (0/1) |

**2025 CALGreen Requirements (Effective Jan 1, 2026):**

For multifamily:
- ONE Level 2 receptacle per dwelling unit at assigned parking
- 25% of common parking spaces need actual Level 2 chargers (not just receptacles)
- Minimum 3.3 kW per station with ALMS (Automatic Load Management System)
- Branch circuits rated for 40 amps, chargers at 30 amps minimum

**Scale of Impact:**
| Building Type | Units | Min EV Stations | kWh/year (est.) |
|---------------|-------|-----------------|-----------------|
| 50-unit MF | 50 | 50 + 12 chargers | 40,000-80,000 |
| 200-unit MF | 200 | 200 + 50 chargers | 160,000-320,000 |
| 500-unit MF | 500 | 500 + 125 chargers | 400,000-800,000 |

**Critical Note:** EV is a MASSIVE load that significantly impacts whole-building energy.
Current site load calculator methods are crude and need refinement.

**Recommendation:**
- Develop EV load calculator based on:
  - CALGreen 2025 requirements
  - ALMS load management (3.3 kW minimum per station)
  - Actual utilization data (varies by location, demographics)
- Integrate with utility rate analysis for TOU optimization

---

## Load Categories Summary

| Load Type | CBECC Status | Modeling Approach |
|-----------|--------------|-------------------|
| Interior Lighting | ALWAYS modeled | Zone loads (LPD × Area) |
| HVAC | ALWAYS modeled | System simulation |
| DHW | ALWAYS modeled | System simulation |
| Elevators | CAN model | Use ElevCnt property or override |
| Escalators | CAN model | Use EscalCnt property or override |
| Garage Exhaust | CAN model | Use PrkgGarExh properties |
| Central Ventilation | USUALLY modeled | Part of IAQOption |
| EV Charging | LIMITED | Calculate separately with 2025 CALGreen |
| Pool/Spa | NOT modeled | Calculate separately |
| Site Lighting | NOT modeled | Calculate separately |
| IT/Telecom | NOT modeled | Calculate separately |
| Water Pumps | NOT modeled | Calculate separately |

---

## CbeccModeledLoadDetector Module

The `CbeccModeledLoadDetector` class (`eco_tools.lcca.site_loads.detectors`) analyzes CBECC
input files to determine which loads are already modeled vs need site load calculation.

### Usage Example

```python
from eco_tools.lcca.site_loads.detectors import detect_modeled_loads

# Analyze a CBECC model
report = detect_modeled_loads("building.cibd22x")

# Check what's modeled
print("Modeled loads:", report.get_modeled_loads())
print("Site loads needed:", report.get_site_load_recommendations())

# Get specific detection results
elevator = report.get_detection("elevator")
if elevator.is_modeled:
    print(f"Elevators modeled: {elevator.details['elevator_count']}")
    print(f"Zones served: {elevator.details['zones_served']}")
else:
    print("Need to calculate elevator energy as site load")
```

### Detection Categories

| Category | Status | Detection Logic |
|----------|--------|-----------------|
| `parking_garage_exhaust` | Sometimes | Checks PrkgGarExhFlow > 0 |
| `central_ventilation` | Sometimes | Checks IAQOption = "Central..." |
| `elevator` | Sometimes | Checks ElevCnt > 0 on Spc/ResOtherZn |
| `escalator` | Sometimes | Checks EscalCnt > 0 on Spc |
| `interior_lighting` | Always | Part of zone loads (ResOtherZn) |
| `hvac` | Always | System simulation |
| `pool_pump` | Never | Calculate as site load |
| `pool_heater` | Never | Calculate as site load |
| `spa` | Never | Calculate as site load |
| `ev_charger` | Never | Calculate as site load |
| `site_lighting` | Never | Calculate as site load |

### Important Notes

1. **Elevator/Escalator counts**: CBECC distributes elevator load across multiple zones for
   heat gain calculation. The detector uses MAX count (not SUM) to get the true elevator count.

2. **CEC Standard Values**: When elevators ARE modeled in CBECC, they use CEC standard
   process loads which may differ from actual equipment. Consider overriding for LCCA accuracy.

---

## Standardized Workflow

### Principle: Always Model in CBECC When Possible

Rather than detecting what's modeled and calculating separately, the preferred approach is:

1. **Always include "sometimes modeled" loads in CBECC**
2. **Inputs come from either:**
   - Parsed from existing CBECC model (if present)
   - From intake form (if not in model)
3. **Inject inputs via templatized approach**

### Workflow Steps

#### Step 1: Parse Existing Model
```python
# Check what's already in the CBECC model
detector = CbeccModeledLoadDetector()
report = detector.analyze("building.cibd22x")

# Get elevator count from model
elev_det = report.get_detection("elevator")
if elev_det.is_modeled:
    elevator_count = elev_det.details.get("elevator_count", 0)
else:
    elevator_count = None  # Need from intake form
```

#### Step 2: Collect Missing Inputs from Intake Form
```yaml
# Example intake form structure
garage_ventilation:
  exhaust_fans:
    - cfm: 10000
      count: 5
    - cfm: 9000  # supply
      count: 5
  co_control: true

elevators:
  count: 4
  type: "traction_geared"
  floors_served: 12

ev_charging:
  dwelling_units: 200
  parking_spaces: 250
  alms_system: true
```

#### Step 3: Inject into CBECC Model
```python
# Template-based injection
template = CbeccTemplate()
template.set_elevator_count(elevator_count or intake_data["elevators"]["count"])
template.set_parking_exhaust(
    cfm=intake_data["garage_ventilation"]["exhaust_cfm"],
    fan_power=0.35,  # W/CFM
    co_control=intake_data["garage_ventilation"]["co_control"]
)
template.write("building_updated.cibd25")
```

#### Step 4: Run Simulation
```bash
CBECC 2025 -nrcc -b building_updated.cibd25
```

#### Step 5: Parse Results + Add Remaining Site Loads
```python
# Parse simulation output
wbe = create_whole_building_energy(
    simulation_file="building_updated - HourlyResults.csv",
    site_loads_input={
        # Only loads that CANNOT be in CBECC
        "pool_pump": [...],
        "site_lighting": [...],
        "ev_charger": [...],  # Until CBECC supports it
    }
)
```

---

## CEC Standard Values vs. Better Data

### Elevator Energy (CEC Standards)

CEC uses simplified process load calculations that may not match actual equipment.

**CEC Approach:**
- Fixed kW values based on elevator type
- May not reflect modern regenerative drives

**Better Data Sources:**
- ISO 25745-2 (Elevator energy measurement)
- VDI 4707 (German standard)
- ASHRAE 90.1 Appendix G
- Manufacturer-specific data

**Recommendation:** Override CEC values when actual equipment data is available.

### EV Charging (Developing Standard)

**Current Crude Estimates in Site Load Calculator:**
- Simple utilization factors
- Generic kWh per port

**Better Approach (To Be Developed):**
1. Use CALGreen 2025 infrastructure requirements as baseline
2. Apply location-specific utilization factors
3. Account for ALMS load management
4. Model seasonal variation (heating in EVs during winter)
5. Consider TOU optimization in load profiles

**Research Needed:**
- CEC-developed EV load models (if any)
- Utility smart charging programs
- Real-world multifamily EV utilization data

---

## Next Steps

1. **Update CbeccModeledLoadDetector** to check for ElevCnt, EscalCnt, PrkgGarExh*
2. **Create CbeccTemplate** module for injecting site load inputs
3. **Develop refined EV calculator** based on CALGreen 2025
4. **Research CEC standard values** vs. industry data for elevators
5. **Create intake form specification** for site load inputs

---

## References

- [2025 CALGreen EV Requirements](https://calgreenenergyservices.com/2025/11/18/ev-charging-and-the-2025-calgreen-code/)
- [CALGreen Official Resources](https://calgreeninfo.com/content/resources)
- CBECC Rule Files: `Space-ElevatorEscalator.rule`, `ResOtherZn-ElevatorEscalator.rule`
- Title 24 2022 Nonresidential ACM Reference Manual
