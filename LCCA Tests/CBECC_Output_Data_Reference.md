# CBECC Output Data Reference

This document describes the location and structure of CBECC 2025 output files for extracting proposed vs baseline comparison data for LCCA analysis.

## Output File Locations

All output files are generated in the project's `- run/` folder after a compliance analysis.

---

## 1. Energy Results

### AnalysisResults.xml
**Location:** `[ProjectName] - AnalysisResults.xml` (in project folder, not run folder)

**Contains:** Complete energy comparison between Proposed and Standard models

**Key Structure:**
```xml
<Model Name="User Input">    <!-- Original input model -->
<Model Name="Proposed">      <!-- Proposed model for compliance -->
<Model Name="Standard">      <!-- Baseline/Standard model -->
```

**EnergyUse Elements (in Standard model section):**
| Field | Description | Units |
|-------|-------------|-------|
| `EnduseName` | End use category | - |
| `PropElecEnergy` | Proposed electric consumption | kBtu |
| `PropNatGasEnergy` | Proposed gas consumption | kBtu |
| `StdElecEnergy` | Baseline electric consumption | kBtu |
| `StdNatGasEnergy` | Baseline gas consumption | kBtu |
| `ProposedTDV` | Proposed TDV | kTDV/ft² |
| `StandardTDV` | Standard TDV | kTDV/ft² |
| `CompMarginTDV` | Compliance margin | kTDV/ft² |
| `ProposedSrc` | Proposed source energy | kBtu/ft² |
| `StandardSrc` | Standard source energy | kBtu/ft² |

**End Use Categories:**
- Space Heating
- Space Cooling
- IAQ Ventilation
- Water Heating
- Indoor Lighting
- Receptacle
- Process
- Refrigeration
- PV (negative = generation)
- Battery
- TOTAL

---

## 2. Hourly Results

### HourlyResults.csv
**Location:** `[ProjectName] - run/[ProjectName] - ap - HourlyResults.csv` (Proposed)
**Location:** `[ProjectName] - run/[ProjectName] - ab - HourlyResults.csv` (Baseline)

**Contains:** 8760 hourly energy values by end use

**Columns:** Date, Hour, then energy by end use category (kBtu)

---

## 3. HVAC Sizing Data

### Residential HVAC Capacities
**Location:** `[ProjectName] - run/[ProjectName] - AP-HVACCAPS.CSV` (Proposed)
**Location:** `[ProjectName] - run/[ProjectName] - AB-HVACCAPS.CSV` (Baseline)

**Contains:** Heating and cooling capacities for residential HVAC systems

**Format:**
```csv
"runDateTime","SysName","HtgCap","ClgCap","SysName","HtgCap","ClgCap",...
```

**Units:** kBtu/h

### Non-Residential HVAC Sizing
**Location:** `[ProjectName] - run/[ProjectName] - ap - HVACSecondarySizing.csv` (Proposed)
**Location:** `[ProjectName] - run/[ProjectName] - ab - HVACSecondarySizing.csv` (Baseline)

**Contains:** Detailed equipment specifications in TABLE format

**Tables:**
| Table Name | Contents |
|------------|----------|
| `CoilClg` | Cooling coil: CapTotNetRtd, CapTotGrossRtd, DXSEER, DXEER |
| `CoilHtg` | Heating coil: CapTotNetRtd, CapTotGrossRtd, FurnAFUE |
| `Fan` | Fan: FlowCap, TotStaticPress, MtrBHP, MtrHP, PwrIdx |
| `TrmlUnit` | Terminal units: PriAirFlowMax, PriAirFlowMin |
| `OACtrl` | Economizer: EconoCtrlMthd, EconoIntegration |

---

## 4. DHW System Data

### CSE Input Files
**Location:** `[ProjectName] - run/[ProjectName] - ap-cse.cse` (Proposed)
**Location:** `[ProjectName] - run/[ProjectName] - ab-cse.cse` (Baseline)

**Contains:** California Simulation Engine input with DHW system definitions

**Key DHW Parameters:**
| Parameter | Description |
|-----------|-------------|
| `whType` | Water heater type (BuiltUp, SmallInstantaneous, etc.) |
| `whVol` | Tank volume (gallons) |
| `whASHPType` | Heat pump type (SandenGS3, Scalable_SP, etc.) |
| `wlFlow` | Loop flow rate (gpm) |
| `wgLength` | Pipe segment length (ft) |
| `wgInsulThk` | Pipe insulation thickness (in) |

---

## 5. Building Model Data (SDD XML)

### Annual Models
**Location:** `[ProjectName] - run/[ProjectName] - ap.xml` (Annual Proposed)
**Location:** `[ProjectName] - run/[ProjectName] - ab.xml` (Annual Baseline)

**Contains:** Full SDD building model definition including:
- Building geometry (zones, surfaces, windows)
- Construction assemblies
- Schedules
- HVAC system topology (but NOT calculated capacities)
- Zone assignments

### Sizing Models
**Location:** `[ProjectName] - run/[ProjectName] - zp.xml` (Sizing Proposed)
**Location:** `[ProjectName] - run/[ProjectName] - zb.xml` (Sizing Baseline)

**Contains:** Models used for HVAC sizing runs

---

## 6. Envelope Data

### Envelope.csv
**Location:** `[ProjectName] - run/[ProjectName] - ap - Envelope.csv` (Proposed)
**Location:** `[ProjectName] - run/[ProjectName] - ab - Envelope.csv` (Baseline)

**Contains:** Envelope component U-factors and areas

---

## 7. CSE Reports

### CSE Report Files
**Location:** `[ProjectName] - run/[ProjectName] - AP-CSE.REP` (Proposed)
**Location:** `[ProjectName] - run/[ProjectName] - AB-CSE.REP` (Baseline)

**Contains:** Detailed simulation reports including:
- Monthly energy summaries
- Zone temperatures
- HVAC operation

### CSE CSV Output
**Location:** `[ProjectName] - run/[ProjectName] - AP-CSE.CSV` (Proposed)
**Location:** `[ProjectName] - run/[ProjectName] - AB-CSE.CSV` (Baseline)

**Contains:** Hourly CSE simulation output

---

## 8. Additional Files

| File Pattern | Description |
|--------------|-------------|
| `- CSE Zone Areas.csv` | Zone floor areas |
| `- FanPowerAdjustment.csv` | Fan power adjustments |
| `- HVACPrimary.csv` | Primary HVAC system data |
| `- HVACSecondary.csv` | Secondary HVAC system data |
| `- PVBattery.csv` | PV and battery system data |
| `- SpcLoadsElec.csv` | Space electric loads |
| `- SpcLoadsFuel.csv` | Space fuel loads |
| `- VentilationExhaust.csv` | Exhaust ventilation data |
| `.ddy` | Design day weather file |
| `.epw` | Full year weather file |

---

## INI Settings to Enable Full Output

In CBECC Program INI Settings, enable these options for complete data:

| Setting | Value | Effect |
|---------|-------|--------|
| Store All Analysis Model Details | On | Stores detailed BEM files |
| Storage of Simulation Output | 7 (ALL) | Retains all E+ files |
| Storage of Analysis Files | 3 (ALL) | Keeps all intermediate files |
| Export E+ Output Variables to CSV | All Models | Exports hourly E+ variables |
| Always generate full (XML) compliance report | On | Full AnalysisResults.xml |
| Export Hourly Results | All Models | Generates HourlyResults.csv |

---

## File Naming Convention

- `ap` = Annual Proposed
- `ab` = Annual Baseline (Standard)
- `zp` = Sizing Proposed
- `zb` = Sizing Baseline
- `cse` = California Simulation Engine (residential)
- `pvb` = PV/Battery simulation

---

## Notes

1. **SDD XML files** (`ap.xml`, `ab.xml`) contain building definitions but NOT calculated equipment capacities
2. **HVACCAPS.CSV** files contain residential HVAC sizing results
3. **HVACSecondarySizing.csv** files contain non-residential equipment specs
4. **CSE files** (`.cse`) contain DHW system specifications
5. The baseline model uses Title 24 standard equipment efficiencies and sizes

---

*Document created: 2025-12-26*
*For use with CBECC 2025.2.0*
