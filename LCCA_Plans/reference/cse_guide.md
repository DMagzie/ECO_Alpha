# CSE (California Simulation Engine) Reference Guide

**Date:** December 30, 2024
**Version:** 1.2 (Validated)
**Module:** `eco_tools.lcca`

---

## Overview

CSE (California Simulation Engine) is the simulation core embedded within CBECC (California Building Energy Code Compliance). This guide covers working with CSE input/output files for zone-level energy analysis in the LCCA module.

---

## 1. CSE File Types

### 1.1 Input Files (`.cse`)

CSE input files are text-based configuration files that define the building model for simulation.

**Location in CBECC workflow:**
```
ProjectName/
├── ProjectName.cibd25          # CBECC project file
└── ProjectName - run/
    ├── ProjectName - ap-cse.cse   # Proposed design CSE input
    ├── ProjectName - ab-cse.cse   # Baseline design CSE input
    └── ... (output files)
```

### 1.2 Output Files

| File Pattern | Description | Use Case |
|--------------|-------------|----------|
| `*-AP-CSE.CSV` | Proposed hourly meter data | Zone-level energy analysis |
| `*-AB-CSE.CSV` | Baseline hourly meter data | Comparison baseline |
| `*-HourlyResults.csv` | Combined hourly results | Building-level analysis |
| `*-rep.txt` | Text report | Debugging |
| `*-err.txt` | Error log | Troubleshooting |

---

## 2. CSE Input File Syntax

### 2.1 Object Block Structure

CSE uses a block-based syntax where each object type is declared with properties:

```cse
OBJECTTYPE "ObjectName"
   property1 = value1
   property2 = "string value"
   property3 = @expression
   ..

// Comments start with //
```

### 2.2 Key Object Types

#### ZONE
Defines a thermal zone in the building:

```cse
ZONE "Fitness-zn"
   znModel = CZM
   znArea = 1200
   znVol = 12000
   znCAir = 500
   znEaveZ = 10
   znCeilingHt = 10
   ..
```

**Key Properties:**
- `znModel`: Zone model type (CZM = Conditioned Zone Model, UZM = Unconditioned)
- `znArea`: Zone floor area (sq ft)
- `znVol`: Zone volume (cu ft)
- `znCAir`: Zone air capacity (Btu/F)

#### GAIN
Defines internal heat gains (lighting, equipment, occupancy):

```cse
GAIN "Fitness-zn gnIntLtg"
   gnZone = "Fitness-zn"
   gnMeter = "sbmtrE1_Res_1st Story"  // Meter assignment
   gnEndUse = Lit                      // End-use category
   gnPower = @hourval("Fitness-zn LtgPwr", $hour)
   ..
```

**Key Properties:**
- `gnZone`: Parent zone name
- `gnMeter`: Electricity meter for this gain (key for zone metering)
- `gnEndUse`: End-use category (Lit, Rcp, Proc, etc.)
- `gnPower`: Power expression (hourly or constant)

#### RSYS (Residential System)
Defines HVAC systems for residential zones:

```cse
RSYS "ResHVAC Sys 1"
   rsType = ASHP
   rsElecMtr = "sbmtrE1_Res_1st Story"
   rsFuelMtr = "sbmtrF1_Res_1st Story"
   rsCap47 = 36000
   rsEER = 11.5
   rsSEER = 15
   ..
```

**Key Properties:**
- `rsType`: System type (ASHP, WSHP, PTAC, etc.)
- `rsElecMtr`: Electric meter assignment
- `rsFuelMtr`: Fuel meter assignment
- `rsCap47`: Cooling capacity at 47F
- `rsEER/rsSEER`: Efficiency ratings

#### METER
Defines energy meters for aggregation:

```cse
METER "MtrElec"
   // Building total meter
   ..

METER "MtrElec_CommonArea"
   mtrSubmeters = "MtrElec_CA_LOBBY", "MtrElec_CA_CORRIDOR", "MtrElec_CA_FITNESS"
   mtrSubmeterMults = 1, 1, 1
   ..
```

**Key Properties:**
- `mtrSubmeters`: List of child meters to aggregate
- `mtrSubmeterMults`: Multipliers for each submeter

#### EXPORT
Defines hourly data exports:

```cse
EXPORT "MtrElec_Export"
   exFreq = HOUR
   exType = MTR
   exMeter = "MtrElec"
   ..
```

**Export Types:**
- `MTR`: Meter data export
- `UDT`: User-defined table export

---

## 3. End-Use Categories

CSE uses these end-use codes in GAIN definitions and output:

| Code | Description | Typical Sources |
|------|-------------|-----------------|
| `Clg` | Cooling | AC, heat pumps |
| `Htg` | Heating | Furnaces, heat pumps |
| `HPBU` | Heat pump backup | Electric resistance backup |
| `Dhw` | Domestic hot water | Water heaters |
| `DhwBU` | DHW backup | Backup water heating |
| `FanC` | Cooling fan | Supply fan (cooling mode) |
| `FanH` | Heating fan | Supply fan (heating mode) |
| `FanV` | Ventilation fan | OA ventilation |
| `Fan` | Other fans | Exhaust, misc |
| `Aux` | Auxiliary | Pumps, controls |
| `Proc` | Process | Equipment loads |
| `Lit` | Lighting | Interior lighting |
| `Rcp` | Receptacles | Plug loads |
| `Ext` | Exterior | Exterior lighting |
| `Refr` | Refrigeration | Refrigerators, freezers |
| `Dish` | Dishwasher | Dishwashing equipment |
| `Dry` | Dryer | Clothes dryers |
| `Wash` | Washer | Clothes washers |
| `Cook` | Cooking | Ranges, ovens |
| `PV` | Photovoltaic | Solar generation (negative) |
| `BT` | Battery | Battery storage |

---

## 4. Zone-Level Metering Strategy

### 4.1 Problem Statement

CBECC's default CSE output aggregates energy by story-level meters:
```
sbmtrE1_Res_1st Story  → All 1st floor zones combined
sbmtrE1_Res_2nd Story  → All 2nd floor zones combined
```

For zone-level LCCA, we need per-zone hourly data.

### 4.2 Solution: CSE Input Transformation

The `eco_tools.lcca.cse_transformer` module:

1. **Parses** the CSE input file to extract zones and gains
2. **Classifies** zones as dwelling units or common areas
3. **Generates** zone-specific meters with hierarchical aggregation
4. **Updates** GAIN `gnMeter` references to zone meters
5. **Updates** RSYS meter references
6. **Injects** new METER and EXPORT definitions

### 4.3 Meter Hierarchy

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

---

## 5. Using the Zone Simulation Pipeline

### 5.1 Basic Usage

```python
from pathlib import Path
from eco_tools.lcca.zone_simulation import run_zone_simulation

# Run the pipeline
result = run_zone_simulation(
    cbecc_run_dir=Path("/path/to/project - run"),
    run_cse=True,  # Execute CSE if available
)

# Access zone summaries
for zone in result.proposed_zones:
    print(f"{zone.zone_name}: {zone.elec_kwh:,.0f} kWh")
```

### 5.2 Configuration Options

```python
from eco_tools.lcca.zone_simulation import (
    ZoneSimulationConfig,
    ZoneSimulationPipeline,
)

config = ZoneSimulationConfig(
    cbecc_run_dir=Path("/path/to/run"),
    output_dir=Path("/path/to/output"),  # Optional
    use_proposed=True,   # Process proposed design
    use_baseline=False,  # Skip baseline
    run_cse=True,        # Run CSE simulation
    cse_timeout=600,     # Timeout in seconds
    keep_transformed=True,  # Keep modified CSE file
    export_csv=True,     # Export zone summaries
)

pipeline = ZoneSimulationPipeline()
result = pipeline.run(config)
```

### 5.3 Working with Results

```python
# Check success
if result.success:
    print(f"Processed {result.zone_count} zones")
    print(f"Total annual kWh: {result.total_annual_kwh:,.0f}")

# Get zones by type
dwelling_units = result.get_dwelling_units()
common_areas = result.get_common_areas()

# Access hourly data (if CSE was executed)
if result.has_hourly_data:
    for zone in result.proposed_zones:
        hourly = zone.hourly_elec_kwh  # List[float] with 8760 values

# View meter hierarchy
if result.meter_hierarchy:
    from eco_tools.lcca.zone_meter_mapper import format_meter_hierarchy
    print(format_meter_hierarchy(result.meter_hierarchy))
```

---

## 6. CSE Executable Location

### 6.1 macOS (via Wine)

CBECC 2025 on macOS runs via Wine emulation. The CSE executable is located at:
```
/Users/[username]/.wine/drive_c/Program Files/CBECC 2025/CSE/CSE.exe
```

**Running CSE via Wine:**
```bash
/opt/homebrew/bin/wine "/path/to/.wine/drive_c/Program Files/CBECC 2025/CSE/CSE.exe" input.cse
```

**Notes:**
- CSE via Wine takes ~35 minutes for a 19-zone model
- Weather files must be accessible (copy to working directory if needed)
- Output files are created in the working directory

### 6.2 Windows

```
C:\Program Files\CBECC 2025\CSE.exe
```

### 6.3 Weather File Location

CSE requires weather files (.epw format). Default location:
```
# macOS (Wine)
Z:\Users\[username]\Documents\CBECC 2025 Data\EPW\

# Windows
C:\Users\[username]\Documents\CBECC 2025 Data\EPW\
```

### 6.4 Checking Availability

```python
from eco_tools.lcca.cse_runner import check_cse_available

available, path = check_cse_available()
if available:
    print(f"CSE found at: {path}")
else:
    print("CSE not available - using existing output files")
```

---

## 7. Parsing CSE Output

### 7.1 Output CSV Format

The CSE meter export CSV has this structure:

```csv
"Project Name"
"Run DateTime"
"Meter","Mon","Day","Hr","Subhr","Tot","Clg","Htg","HPBU","Dhw",...
"MtrElec",1,1,1,1,12.5,0,2.1,0,1.2,...
"MtrElec",1,1,2,1,11.8,0,1.9,0,1.1,...
...
```

### 7.2 Parsing with CSEZoneOutputParser

```python
from eco_tools.lcca.parsers.cse_zone_output import (
    parse_cse_zone_output,
    format_zone_output_summary,
)

# Parse output CSV
model = parse_cse_zone_output(Path("project-AP-CSE.CSV"))

# Print summary
print(format_zone_output_summary(model))

# Access specific meter data
meter_data = model.get_meter("MtrElec_Fitness-zn")
if meter_data:
    print(f"Annual kWh: {meter_data.annual_total_kwh:,.0f}")
    print(f"Peak kW: {meter_data.peak_demand_kw:.1f}")

    # End-use breakdown
    breakdown = meter_data.get_end_use_breakdown()
    for enduse, kwh in breakdown.items():
        print(f"  {enduse}: {kwh:,.0f} kWh")
```

---

## 8. Troubleshooting

### 8.1 Common Issues

| Issue | Cause | Solution |
|-------|-------|----------|
| "No CSE input file found" | Wrong directory | Point to `-run` directory |
| "No zones found" | Parsing error | Check CSE file syntax |
| CSE timeout | Large model | Increase `cse_timeout` |
| Empty hourly data | CSE not executed | Set `run_cse=True` or use existing output |
| Zone classification wrong | Name pattern mismatch | Check zone naming conventions |

### 8.2 Zone Classification Patterns

The zone classifier uses these patterns:

**Dwelling Units:**
- Contains bedroom indicators: `_0BR`, `_1BR`, `_2BR`, `_3BR`, `1Bed`, `2Bed`
- Contains: `DwellUnit`, `Dwelling`, `ResZn`, `Apartment`, `Unit`

**Common Areas:**
- Contains: `Corridor`, `Lobby`, `Fitness`, `Mechanical`, `Parking`
- Contains: `Storage`, `Laundry`, `Office`, `Stairwell`

### 8.3 Debugging Transformation

```python
from eco_tools.lcca.cse_transformer import CSETransformer

transformer = CSETransformer()
result = transformer.transform_file(
    Path("input.cse"),
    Path("output_transformed.cse")
)

# Check transformation results
print(f"Gains updated: {result.gains_updated}")
print(f"RSYS updated: {result.rsys_updated}")
print(f"Meters added: {result.meters_added}")
print(f"Exports added: {result.exports_added}")

# Check for errors
for error in result.errors:
    print(f"Error: {error}")
for warning in result.warnings:
    print(f"Warning: {warning}")
```

---

## 9. API Reference

### 9.1 Key Modules

| Module | Purpose |
|--------|---------|
| `parsers/cse_zone_input.py` | Parse CSE input files |
| `zone_meter_mapper.py` | Zone classification & meter naming |
| `cse_transformer.py` | Transform CSE input with zone meters |
| `cse_runner.py` | Execute CSE simulation |
| `parsers/cse_zone_output.py` | Parse CSE output CSV |
| `zone_simulation.py` | Pipeline orchestrator |

### 9.2 Key Classes

```python
# Input parsing
from eco_tools.lcca.parsers.cse_zone_input import (
    CSEZoneInputParser,
    CSEZoneInputModel,
    CSEZone,
    CSEGain,
)

# Zone mapping
from eco_tools.lcca.zone_meter_mapper import (
    ZoneMeterMapper,
    ZoneMeterAssignment,
    MeterHierarchy,
)

# Transformation
from eco_tools.lcca.cse_transformer import (
    CSETransformer,
    TransformResult,
)

# Execution
from eco_tools.lcca.cse_runner import (
    CSERunner,
    CSERunConfig,
    CSERunResult,
)

# Output parsing
from eco_tools.lcca.parsers.cse_zone_output import (
    CSEZoneOutputParser,
    CSEZoneOutputModel,
    ZoneHourlyData,
)

# Pipeline
from eco_tools.lcca.zone_simulation import (
    ZoneSimulationPipeline,
    ZoneSimulationConfig,
    ZoneSimulationResult,
    run_zone_simulation,
)
```

---

## 10. Validation Results

The zone-level metering pipeline was validated on December 30, 2024 using the Ventura & 7th multifamily project.

### Test Summary

| Metric | Value |
|--------|-------|
| Zones Parsed | 19 (9 DU + 10 CA) |
| Meters Created | 31 |
| Exports Added | 19 |
| GAINs Updated | 243 |
| CSE Execution | ~35 min (Wine) |
| Output Rows | 210,360 |

### Understanding CBECC Story Multipliers

CBECC multifamily models use **prototype zones** with **story multipliers** to represent multiple identical floors:

```
Original CBECC Meter Structure:
───────────────────────────────

MtrElec_1bedrm
  ├── sbmtrE1_Res_1st Story_1bedrm           × 1
  ├── sbmtrE1_Res_2nd & 3rd Story_1bedrm     × 2  ◄── L02-03 = 2 floors!
  └── sbmtrE1_Res_4th Story_1bedrm           × 1
      ───────────────────────────────────────────
      mtrSubMeterMults = 1, 2, 1  (total factor: 4)
```

The `L02-03` zone prototype represents 2 floors, so CBECC applies a `×2` multiplier (`mtrSubMeterMults`) when aggregating to bedroom meters.

### Zone-Level Output: Raw Prototype Data

Our zone-level transformation provides **raw prototype energy** without story multipliers:

| Output Type | Energy | Notes |
|-------------|--------|-------|
| Dwelling zones (9) | 677,289 kWh | Raw prototype data |
| Common area zones (10) | 279,636 kWh | Not multiplied |
| **Total zone energy** | **956,925 kWh** | Sum of all zones |

### Energy Validation (Multiplier-Adjusted)

| Comparison | kWh | Notes |
|------------|-----|-------|
| Original CBECC bedroom meters | 930,236 | With multipliers (1+2+1=4) |
| Original ÷ 1.33 | 697,677 | Expected raw prototype |
| Zone-level dwelling output | 677,289 | Actual raw prototype |
| **Difference** | **-2.9%** | ✓ Within tolerance |

**Result:** ✓ PASSED - Zone totals match expected raw prototype energy within 3%

### Why Raw Prototype Data is Desirable

Zone-level output provides unmultiplied prototype energy, which is **ideal for LCCA**:

1. **Hourly shapes preserved** - Each zone's 8760-hour load profile is accurate for TOU
2. **Per-prototype analysis** - Compare energy intensity (kWh/sf) across zone types
3. **VNBT allocation** - Allocate solar credits to specific zone categories
4. **Flexible aggregation** - Apply multipliers downstream when needed

### Understanding the 3% Difference

The ~3% difference between expected (1.33x) and actual (1.37x) ratio is due to **non-identical floor prototypes**:

| Metric | Value |
|--------|-------|
| Original bedroom meters (with 1,2,1 mults) | 930,236 kWh |
| Zone dwelling meters (no mults) | 677,289 kWh |
| Observed ratio | 1.373x |
| Expected ratio (if floors equal) | 1.333x (4/3) |

**Root Cause:** The three floor prototypes (L01, L02-03, L04) have **different energy consumption**:

Solving mathematically: if ratio = (L01 + 2×L02-03 + L04) / (L01 + L02-03 + L04) = 1.373

This implies: **L02-03 has ~19% MORE energy than L01 or L04**

| End-Use Type | Ratio | Interpretation |
|--------------|-------|----------------|
| Plug loads (Rcp, Lit, appliances) | ~1.35x | ✓ Nearly equal across floors |
| Cooling (Clg, FanC) | ~1.48x | L02-03 has higher cooling |
| Heating (Htg, FanH, HPBU) | ~1.24x | L02-03 has lower heating |

**Why L02-03 might differ:** The CBECC model may have different characteristics for the L02-03 prototype (window areas, orientations, adjacent zone temperatures) that result in higher cooling loads despite being a "middle" floor.

### Applying Multipliers for Building Totals

When aggregating zone data to building totals:

```python
# Zone-level dwelling data (raw prototypes)
dwelling_raw_kwh = 677289

# Apply story multipliers for building total
# L01: ×1, L02-03: ×2, L04: ×1 → factor = 4/3 ≈ 1.33
dwelling_building_kwh = dwelling_raw_kwh * (4/3)  # ≈ 900,000 kWh

# Note: Result differs from original 930,236 kWh by ~3% due to
# HVAC load variations across floors (this is expected)
```

### Known Issues Resolved

1. **Zone Parser Bug:** Fixed nested object parsing that skipped zones
2. **Export Injection:** Fixed EXPORTCOL attachment by inserting before RUN statement
3. **Weather File Path:** Resolved by copying EPW to working directory

---

## 11. References

- **CBECC Documentation:** https://www.energy.ca.gov/programs-and-topics/programs/building-energy-efficiency-standards/2025-building-energy-efficiency
- **CSE Source:** https://github.com/cse-sim/cse (CSE open source repository)
- **Title 24 Standards:** California Energy Commission Building Standards
- **Architecture Doc:** [CSE-LCCA Architecture](./cse_lcca_architecture.md)

---

*Last Updated: December 30, 2024 (v1.2 - Added Multiplier Documentation)*
