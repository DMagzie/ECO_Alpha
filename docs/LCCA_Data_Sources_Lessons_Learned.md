# LCCA Data Sources: Lessons Learned

This document summarizes where different pieces of information defining LCCA inputs can be sourced from CBECC simulation outputs.

## Overview

CBECC generates multiple output files after a simulation run. Different data types are available in different files, and some data is duplicated across files with varying levels of detail. Understanding which file to use for each data type is critical for accurate LCCA calculations.

## File Types and Their Contents

### 1. HourlyResults CSV (`*- ap - HourlyResults.csv`)

**Best for:** Annual energy consumption by end-use

| Data Type | Available | Notes |
|-----------|-----------|-------|
| Electricity by end-use (hourly) | Yes | Space heating, cooling, fans, DHW, etc. |
| Natural gas by end-use (hourly) | Yes | Space heating, DHW, cooking |
| Total energy consumption | Yes | Calculated from hourly data |
| Peak demand | Yes | Derivable from hourly data |

**Example columns:**
- `Electricity:SpaceHeat (kWh)`
- `NaturalGas:DHW (therms)`
- `Electricity:Cooling (kWh)`

---

### 2. CSE Hourly CSV (`*CSE*.csv`)

**Best for:** Detailed end-use breakdown for residential buildings

| Data Type | Available | Notes |
|-----------|-----------|-------|
| Detailed zone-level energy | Yes | More granular than HourlyResults |
| Equipment-level consumption | Sometimes | Depends on model complexity |

---

### 3. HVACSecondary CSV (`*- ap - HVACSecondary.csv`)

**Best for:** HVAC equipment specifications

| Data Type | Available | Notes |
|-----------|-----------|-------|
| Air System types (SZHP, VRF, etc.) | Yes | `SystemType` column |
| Cooling capacity (Btu/h) | Yes | May show -99996 for residential |
| Heating capacity (Btu/h) | Yes | May show -99996 for residential |
| SEER/EER ratings | Yes | For DX cooling coils |
| HSPF/COP ratings | Yes | For heat pump heating |
| Fan power (W/CFM) | Yes | Supply and return fans |
| Zone system details | Yes | Terminal units, reheat coils |

**Known Issues:**
- Residential buildings often show `-99996` (missing value) for capacities
- Efficiency ratings may be missing for some system types

---

### 4. HVACPrimary CSV (`*- ap - HVACPrimary.csv`)

**Best for:** Central plant and DHW equipment

| Data Type | Available | Notes |
|-----------|-----------|-------|
| Fluid system types | Yes | HotWater, ChilledWater, ServiceHotWater |
| Water heater specs | Partial | Often shows -99996 for residential |
| Boiler capacity/efficiency | Yes | For commercial buildings |
| Chiller capacity/COP | Yes | For commercial buildings |
| Pump power | Yes | Primary and secondary loops |

**Known Issues:**
- Residential DHW data is unreliable (often -99996)
- Use AnalysisResults.xml for residential DHW instead

---

### 5. Envelope CSV (`*- ap - Envelope.csv`)

**Best for:** Building envelope specifications

| Data Type | Available | Notes |
|-----------|-----------|-------|
| Total wall area (SF) | Yes | By orientation (N, E, S, W) |
| Total window area (SF) | Yes | By orientation |
| Window-to-wall ratio | Yes | `WWR` column |
| Roof area (SF) | Limited | Often 0 for residential |
| Construction U-factors | Sometimes | Depends on model |
| Window U-factor | Limited | May show -99996 |
| Window SHGC | Limited | May show -99996 |

**Known Issues:**
- Roof data often missing for residential buildings
- Window performance values often show -99996
- Use AnalysisResults.xml to supplement missing envelope data

---

### 6. AnalysisResults XML (`*- AnalysisResults.xml` or `*AnalysisResults.xml`)

**Best for:** Complete envelope and DHW data, especially for residential

| Data Type | Available | Notes |
|-----------|-----------|-------|
| Roof area (SF) | Yes | By individual element |
| Roof solar reflectance | Yes | `RoofSolReflect` tag |
| Wall area (SF) | Yes | By construction type |
| Wall construction names | Yes | With U-factors in names |
| Window U-factor | Yes | `NFRCUfactor` tag |
| Window SHGC | Yes | `NFRCSHGC` tag |
| DHW system details | Yes | `ResWtrHtr` elements |
| Water heater fuel type | Yes | `HeaterElementType` tag |
| Water heater capacity | Yes | `InputRating` tag (Btu/h) |
| Water heater efficiency | Yes | `EnergyFactor` or `RecovEff` |
| Tank volume | Yes | `TankVolume` tag (gallons) |

**This is the primary source for:**
- Residential roof data
- Window performance (U-factor, SHGC)
- Residential DHW equipment specifications
- Construction type breakdowns by area

---

## Data Priority Matrix

Use this matrix to determine which source to use for each data type:

| Data Type | Primary Source | Fallback Source |
|-----------|---------------|-----------------|
| **Annual Energy (kWh, therms)** | HourlyResults CSV | CSE CSV |
| **HVAC System Type** | HVACSecondary CSV | - |
| **HVAC Capacity (Commercial)** | HVACSecondary CSV | - |
| **HVAC Efficiency** | HVACSecondary CSV | - |
| **DHW Equipment (Residential)** | AnalysisResults XML | HVACPrimary CSV |
| **DHW Equipment (Commercial)** | HVACPrimary CSV | AnalysisResults XML |
| **Wall Area** | Envelope CSV | AnalysisResults XML |
| **Wall Construction Types** | AnalysisResults XML | Envelope CSV |
| **Window Area** | Envelope CSV | AnalysisResults XML |
| **Window U-factor** | AnalysisResults XML | Envelope CSV |
| **Window SHGC** | AnalysisResults XML | Envelope CSV |
| **Roof Area** | AnalysisResults XML | Envelope CSV |
| **Roof Solar Reflectance** | AnalysisResults XML | - |

---

## Key Lessons Learned

### 1. Residential vs. Commercial Data Availability

Residential buildings in CBECC export less detail to CSV files than commercial buildings. For residential projects:
- **Always use AnalysisResults XML** for envelope and DHW data
- CSV files will often show `-99996` (CBECC's missing value indicator)
- The XML contains the actual simulation inputs

### 2. Missing Value Handling

CBECC uses `-99996` to indicate missing or not-applicable values:
```python
MISSING_VALUE = -99996

def is_valid(value):
    return value is not None and value > MISSING_VALUE + 1000
```

### 3. Multi-Section CSV Parsing

CBECC CSV files contain multiple sections separated by blank lines:
- Each section has a header row with section name
- May have sub-headers for grouping
- Column names and units follow
- Data rows follow

**Parser approach:**
```python
sections = detect_sections(lines)
for section in sections:
    if matches_desired_type(section.name):
        parse_section(section)
```

### 4. Window/Wall Type Breakdowns

To get area breakdowns by construction type:
- Parse XML `ResExtWall`/`ExtWall` elements with `Construction` child
- Group by construction name
- Extract U-factor from construction name if present (e.g., "U=0.065")

### 5. XML Tag Variations

Different CBECC versions and building types use different XML tags:

| Data Type | Residential Tags | Commercial Tags |
|-----------|-----------------|-----------------|
| Wall elements | `ResExtWall` | `ExtWall` |
| Window elements | `ResWin` | `Win` |
| Roof elements | `ResCathedralCeiling` | `ExtRoof` |
| Water heaters | `ResWtrHtr` | `WtrHtr` |
| DHW systems | `ResDHWSys`, `ResDHWSysRpt` | `FluidSys` |
| Fuel type | `HeaterElementType` | `Fuel` |
| Tank volume | `TankVolume` | `TankVol` |

### 6. Fenestration U-Factor Parsing

For reliable window U-factor extraction:
1. Look for `NFRCUfactor` tag (most reliable)
2. Filter values: 0.1 <= U <= 1.5 (reasonable range)
3. Average across all windows or use area-weighted average
4. Fallback to construction name parsing if XML unavailable

### 7. Construction Type Analysis

To analyze envelope costs by construction type:
1. Parse XML for all wall/roof elements
2. Group by `Construction` reference
3. Calculate total area per construction type
4. Extract performance specs from construction names or definitions

---

## Recommended Parsing Order

For a complete LCCA analysis, parse files in this order:

1. **AnalysisResults XML** - Get envelope specs, DHW, construction breakdowns
2. **Envelope CSV** - Get wall/window areas and WWR
3. **HVACSecondary CSV** - Get HVAC system types and efficiencies
4. **HVACPrimary CSV** - Get central plant specs (commercial)
5. **HourlyResults CSV** - Get annual energy consumption

### Supplement/Fallback Logic

```python
def get_envelope_data(run_dir):
    # Primary: CSV for areas
    envelope = parse_envelope(csv_path)

    # Supplement: XML for performance specs and breakdowns
    if xml_path.exists():
        envelope = supplement_envelope_with_xml(envelope, xml_path)

    return envelope
```

---

## File Discovery Patterns

Standard CBECC output file naming:
- Proposed: `{project} - ap - {type}.csv`
- Baseline: `{project} - ab - {type}.csv`
- XML: `{project} - AnalysisResults.xml` or `{project}AnalysisResults.xml`

Discovery code should:
1. Look in the project run directory (`{project} - run/`)
2. Check both with and without spaces in filenames
3. Handle both 2022 and 2025 CBECC versions

---

## Summary Table

| Component | Best Data Source | Reliability |
|-----------|-----------------|-------------|
| Energy Consumption | HourlyResults CSV | High |
| HVAC Equipment | HVACSecondary CSV | High (Commercial), Medium (Residential) |
| DHW Equipment | AnalysisResults XML | High |
| Envelope Areas | Envelope CSV | High |
| Envelope Performance | AnalysisResults XML | High |
| Construction Breakdowns | AnalysisResults XML | High |
| Window Performance | AnalysisResults XML | High |

---

## Known Gaps and Limitations

### 1. CBECC 2025 DHW Reference Format

CBECC 2025 models may use named references to DHW systems rather than embedded specifications:
```xml
<DHWSysRef index="0">MF0-2-BD Rheem PROPH65 T2 RH31</DHWSysRef>
```

In this format:
- DHW system specs are stored in a separate library/database
- The XML only contains the reference name (e.g., "Rheem PROPH65 T2")
- Model name encodes info: "PROPH65" = ProTerra Heat Pump 65 gallon, "T2" = Tier 2

**Workaround:** Parse the model name for key specs, or maintain a lookup table of common water heater models.

### 2. Corrupted/Incomplete XML Files

Some XML files may have parsing errors (e.g., unclosed tokens). This typically indicates:
- Simulation was interrupted
- File was corrupted during transfer
- Model had issues during simulation

**Example error:** `Failed to parse XML: unclosed token: line 43774, column 24`

**Workaround:** Fall back to CSV files when XML parsing fails.

### 3. Heat Pump Water Heaters

Heat pump water heaters may show `InputRating = 0` because:
- They draw heat from ambient air rather than using fuel/electric element directly
- Capacity is measured differently (COP-based)
- Look for `EnergyFactor` or `UniformEnergyFactor` (UEF) instead

### 4. Models Tested and Data Availability

| Model | Walls | Roofs | Windows | U/SHGC | DHW | Notes |
|-------|-------|-------|---------|--------|-----|-------|
| Bressi Ranch Apartments | 4,245 | 414 | 3,924 | Yes | 8 heaters | Full data |
| Del Amo Circle LEED | 3,174 | 246 | 2,223 | Yes | 5 heaters | HP WH (capacity=0) |
| Freedom Circle A | - | - | - | - | - | XML parse error |
| Euclid Building A | 1,614 | 99 | 1,251 | Yes | 3 heaters | Full data |
| Mainplace Mall P3 | 5,310 | 501 | 3,150 | Yes | 3 heaters | Full data |
| CUAC MF 33-Unit | 146 | 14 | 276 | Yes | 12 refs | 2025 format, refs only |

---

## Additional Lessons (December 2025 Update)

### 8. HVACCAPS.CSV Contains Residential HVAC Sizing

**Finding:** For residential buildings, the SDD XML files (`ap.xml`, `ab.xml`) contain HVAC topology but NOT calculated capacities. The actual auto-sized capacities are in separate CSV files.

**Location:**
- `{project} - run/PROJECTNAME - AP-HVACCAPS.CSV` (Proposed)
- `{project} - run/PROJECTNAME - AB-HVACCAPS.CSV` (Baseline)

**Format:**
```csv
"runDateTime","SysName","HtgCap","ClgCap","SysName","HtgCap","ClgCap",...
"Tue 23-Dec-25  8:5 am","Dwelling Unit_L01_1BR HVACSys",33.8878,34.3957,...
```

**Units:** kBtu/h

**Implication:** Must parse these CSV files for residential HVAC sizing, not the XML.

---

### 9. CSE Files Contain DHW System Specifications

**Finding:** DHW equipment specifications (tank size, heat pump type, efficiency) are defined in CSE (California Simulation Engine) input files, not the SDD XML.

**Location:**
- `{project} - run/{project} - ap-cse.cse` (Proposed)
- `{project} - run/{project} - ab-cse.cse` (Baseline)

**Format:** Custom text format with named parameters:
```
DHWHEATER "dhwhtr1-t24-CHPWH"
   whType = "BuiltUp"                // Type of water heater
   whASHPType = "SandenGS3"          // ASHP type (for new HPWH model)
   whVol = 111.111111                // Tank volume (gallons)
```

**Key Parameters:**
| Parameter | Description |
|-----------|-------------|
| `whType` | Water heater type (BuiltUp, SmallInstantaneous, etc.) |
| `whVol` | Tank volume (gallons) |
| `whASHPType` | Heat pump type (SandenGS3, Scalable_SP, etc.) |
| `whEF` | Energy Factor (older rating) |
| `whUEF` | Uniform Energy Factor (newer rating) |

**Proposed vs Baseline Example:**
| Property | Proposed | Baseline (Standard) |
|----------|----------|---------------------|
| HP Type | SandenGS3 (CO2) | Scalable_SP (Standard) |
| Tank Volume | 200 gal | 120 gal |

---

### 10. Baseline Uses Title 24 Standard Equipment

**Finding:** The baseline model (`ab`, `zb`) uses Title 24 prescriptive/standard equipment, not the user's proposed equipment at code-minimum efficiency.

**Differences observed:**
- Standard efficiency heat pump water heaters vs high-efficiency models
- Standard tank sizes based on load calculations
- Standard SEER/HSPF values per code

**HVAC Sizing Example (Top Floor Units):**
| Unit | Proposed Htg | Baseline Htg | Difference |
|------|--------------|--------------|------------|
| 1BR | 36.6 kBtu | 43.6 kBtu | +19% |
| 2BR | 64.8 kBtu | 78.0 kBtu | +20% |
| 3BR | 92.5 kBtu | 112.9 kBtu | +22% |

**Implication:** Baseline equipment sizes may differ from proposed due to envelope performance differences. Cannot assume identical equipment for LCCA costing.

---

### 11. Full Output Requires INI Settings

**Finding:** Maximum output detail requires specific INI settings enabled before running analysis.

**Recommended Settings (in CBECC Program INI Settings):**

| Setting | Value | Effect |
|---------|-------|--------|
| Store All Analysis Model Details | Enabled | Stores detailed BEM files |
| Storage of Simulation Output | 7 (ALL) | Retains all E+ and CSE files |
| Storage of Analysis Files | 3 (ALL) | Keeps all intermediate files |
| Export E+ Output Variables to CSV | All Models | Exports hourly E+ variables |
| Export Hourly Results | All Models | Generates HourlyResults.csv |

**Location:** `CBECC 2025 Data/CBECC-25.ini` or via GUI: Tools > Program INI Settings

---

### 12. File Prefixes Indicate Run Type

| Prefix | Meaning | Purpose |
|--------|---------|---------|
| `ap` | Annual Proposed | Main proposed results |
| `ab` | Annual Baseline | Main standard/baseline results |
| `zp` | Sizing Proposed | Proposed sizing run |
| `zb` | Sizing Baseline | Baseline sizing run |
| `pvb` | PV/Battery | PV and battery simulation |

---

### 13. Updated Data Source Priority Matrix

Based on new findings, updated priority for residential buildings:

| Data Type | Primary Source | Secondary Source |
|-----------|---------------|------------------|
| Energy by end use | AnalysisResults.xml (Standard model section) | HourlyResults.csv |
| Hourly energy profiles | HourlyResults.csv | CSE.CSV |
| HVAC capacities (res) | **HVACCAPS.CSV** | - |
| HVAC specs (nonres) | HVACSecondarySizing.csv | HVACSecondary.csv |
| DHW equipment | **-cse.cse files** | AnalysisResults.xml |
| Envelope data | Envelope.csv | AnalysisResults.xml |

---

### 14. AnalysisResults.xml Contains Complete Energy Comparison

**Finding:** The `AnalysisResults.xml` file contains both Proposed AND Standard energy data in a single file within the `<Model Name="Standard">` section.

**Structure:**
```xml
<Model Name="Standard">
  <EnergyUse>
    <EnduseName>Space Heating</EnduseName>
    <PropElecEnergy>783.034</PropElecEnergy>    <!-- Proposed kBtu -->
    <StdElecEnergy>760.864</StdElecEnergy>      <!-- Baseline kBtu -->
    <CompMarginTDV>-0.02</CompMarginTDV>        <!-- kTDV/ft² margin -->
    <ProposedTDV>0.901205</ProposedTDV>         <!-- Proposed kTDV/ft² -->
    <StandardTDV>0.878079</StandardTDV>         <!-- Baseline kTDV/ft² -->
  </EnergyUse>
</Model>
```

**Available Fields:**
- `PropElecEnergy` / `StdElecEnergy` - Electric consumption (kBtu)
- `PropNatGasEnergy` / `StdNatGasEnergy` - Gas consumption (kBtu)
- `ProposedTDV` / `StandardTDV` - TDV values (kTDV/ft²)
- `CompMarginTDV` - Compliance margin
- `ProposedSrc` / `StandardSrc` - Source energy (kBtu/ft²)

**Implication:** This is the most reliable source for energy comparison - consolidates proposed and baseline in one location.

---

---

### 15. Full INI Settings Produce Additional Debug Files

**Finding:** Enabling all INI output options (Storage=7, AnalysisStorage=3) produces 23 additional files (94 vs 71) and 26MB more data (44MB vs 18MB).

**New Files Generated:**
| File Pattern | Purpose | Useful for LCCA? |
|--------------|---------|------------------|
| `.ibd-Detail` | BEM detail after rule evaluation | No (debug) |
| `.ibd-Detail-B4Eval` | BEM detail before evaluation | No (debug) |
| `.ibd-Detail-PostSim` | BEM detail after simulation | No (debug) |
| `.ibd-b4Evals` | CSE input before evaluations | No (debug) |
| `SimOutVarsToCSV.rvi` | E+ output variable config | No (config) |

**Conclusion:** The additional files are primarily debugging files. Core LCCA data files are produced with default settings.

---

### 16. CSE.CSV Contains Detailed Hourly Data by End Use

**Finding:** The `CSE.CSV` files contain more granular hourly data than `HourlyResults.csv`.

**Location:** `{project} - run/PROJECTNAME - AP-CSE.CSV`

**Format:**
```csv
"Meter","Mon","Day","Hr","Subhr","Tot","Clg","Htg","HPBU","Dhw","DhwBU","DhwMFL","FanC","FanH","FanV","Fan","Aux","Proc","Lit","Rcp","Ext","Refr","Dish","Dry","Wash","Cook","User1","User2","BT","PV"
"MtrElec",1,1,1,"",80.0593,0,8.36018,0.0960447,0,0,0.129661,0,0.292681,2.09367,5.51408,2.61553,0,3.56252,36.3395,0,9.21371,0,11.1044,0,0.737408,0,0,0,0
```

**End Use Columns:**
- `Clg` - Cooling
- `Htg` - Heating
- `HPBU` - Heat Pump Backup
- `Dhw` - DHW
- `DhwBU` - DHW Backup
- `DhwMFL` - DHW Makeup/Losses
- `FanC`, `FanH`, `FanV`, `Fan` - Fan categories
- `Lit` - Lighting
- `Rcp` - Receptacle
- `Refr`, `Dish`, `Dry`, `Wash`, `Cook` - Appliances
- `BT` - Battery
- `PV` - PV generation

**Implication:** Use CSE.CSV for more detailed appliance-level hourly data.

---

### 17. NRCCPRF.xml Contains Project Summary Data

**Finding:** The compliance report XML (`NRCCPRF.xml`) contains high-level project summary data.

**Location:** `{project} - NRCCPRF.xml` (main project folder)

**Key Data:**
```xml
<Info13_DwellingUnitsCount>54</Info13_DwellingUnitsCount>
<Info14_TotalConditionedFloorArea>50722</Info14_TotalConditionedFloorArea>
<Info16_TotalUnconditionedFloorArea>16595</Info16_TotalUnconditionedFloorArea>
<Info08_ClimateZone>13</Info08_ClimateZone>
<Info19_AboveGradeStoryCount>4</Info19_AboveGradeStoryCount>
```

**Useful for:** Quick project metrics without parsing full AnalysisResults.xml

---

### 18. HourlyResults.csv vs CSE.CSV Comparison

| Feature | HourlyResults.csv | CSE.CSV |
|---------|-------------------|---------|
| Format | CEC format with metadata | Simple CSV |
| End uses | ~10-15 categories | 20+ categories |
| Appliance detail | Grouped | Individual (Dish, Dry, Wash, Cook) |
| Battery/PV | Yes | Yes |
| Easier to parse | No (multi-header) | Yes |
| File size | ~2MB | ~2MB |

**Recommendation:** Use CSE.CSV for detailed appliance breakdown, HourlyResults.csv for standard analysis.

---

## Cross-Reference: CBECC Output Data Reference

For complete file location reference, see: `LCCA Tests/CBECC_Output_Data_Reference.md`

---

## Summary: Files Needed for Complete LCCA Analysis

| Data Category | Primary File | Format |
|---------------|--------------|--------|
| Energy comparison | AnalysisResults.xml | XML |
| Hourly profiles | HourlyResults.csv or CSE.CSV | CSV |
| HVAC capacities (res) | HVACCAPS.CSV | CSV |
| HVAC specs (nonres) | HVACSecondarySizing.csv | CSV |
| DHW equipment | -cse.cse | Text |
| Envelope areas | Envelope.csv | CSV |
| Project summary | NRCCPRF.xml | XML |

---

*Document created: December 2024*
*Updated: December 2025 - Added lessons 8-18 from detailed file analysis and full INI test*
*Based on analysis of CBECC 2022 and 2025 output files*
