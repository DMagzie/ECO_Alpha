# NEM3 in CBECC 2025: Comprehensive Analysis

**Date:** November 20, 2025
**Purpose:** Understanding Net Energy Metering 3.0 (NEM3) implementation in CBECC 2025

## Executive Summary

NEM3 (Net Energy Metering 3.0) is California's updated net metering policy that fundamentally changes how solar photovoltaic (PV) system exports to the grid are valued in Title 24 compliance calculations. Instead of crediting solar exports at the full retail rate (as in NEM2), NEM3 uses hourly export factors based on Long-term System Cost (LSC) or Avoided Cost Calculator (ACC) methodologies.

## What is NEM3?

### Background
- **NEM2** (prior policy): Solar exports valued at ~98.5% of retail electricity rate
- **NEM3** (new policy): Solar exports valued at hourly LSC/ACC factors that vary by:
  - Time of day
  - Climate zone
  - Grid conditions

### Policy Context
NEM3 reflects California's shift from simple retail net metering to time-varying export compensation that better aligns with actual grid value and encourages:
- Battery storage adoption
- Load shifting to match solar generation
- Better grid integration of distributed solar

## NEM Options in CBECC 2025

The `NetEnergyMeteringType` property on the `Proj` object controls which NEM method is used:

| Value | Type | Description | Status |
|-------|------|-------------|--------|
| 0 | none | No net metering adjustment | Available |
| 2 | NEM2 | Legacy net metering (2.0) | **Not allowed for 2025+ code** |
| 3 | NEM3-LSC | Long-term System Cost factors | **Default for 2025** |
| 4 | NEM3-ACC | Avoided Cost Calculator factors | Available for 2025 |

### Key Finding
**NEM2 is blocked for 2025+ compliance** per this rule:
```
if (EnergyCodeYearNum >= 2025 .AND. NetEnergyMeteringType == 2)
then  PostError("Net Energy Metering 2 (NEM2) adjusters not yet compatible with Long-term System Cost metric.")
```

## NEM3-LSC (Type 3) - Default Method

### Data Source
- **File:** `T24 2025 NEM3-LSC Factors by CZ.csv`
- **Source:** E3 via CEC (April 2023)
- **Original:** `PV_Export_Factors_20221209.xlsx`

### LSC Factor Characteristics
- **Units:** 30-year Present Value $/kWh
- **Resolution:** 8,760 hourly values per climate zone
- **Climate Zones:** 16 zones (CZ1-CZ16)
- **Value Range:** Approximately $0.57 to $21.16 per kWh (30-yr PV)

### Example Values (January 1st, Hour 1):
| Climate Zone | LSC Factor ($/kWh) |
|--------------|-------------------|
| CZ1-CZ13 | $6.56 |
| CZ6-CZ10,CZ14-CZ16 | $9.24 |

**Note:** Higher factors during evening/night hours when solar isn't generating reflects the value of stored or shifted energy.

## NEM3-ACC (Type 4) - Alternative Method

### Data Source
- **File:** `T24 2025 NEM3-ACC Factors by CZ.csv`
- **Source:** CEC/RJW (July 2024)
- **Original:** `2025_LSCHourlyExportValuesACC.xlsx`

### ACC Factor Characteristics
- **Units:** Export LSC (30-year PV$/kWh)
- **Resolution:** 8,760 hourly values per climate zone
- **Climate Zones:** 16 zones
- **Value Range:** Approximately $0.58 to $1.57 per kWh

### Example Values (January 1st, Hour 1):
| Climate Zone | ACC Factor ($/kWh) |
|--------------|-------------------|
| CZ1-CZ16 | $1.336 (all zones similar) |

**Key Difference:** ACC factors show much less time-of-use variation than LSC factors, and generally lower peak values.

## How NEM3 Works in Compliance Calculations

### 1. Project Settings

When `NetEnergyMeteringType > 2` (NEM3), the ruleset automatically sets:

```
HrlyNEMTableName = "HrlyNEMTable"        // or "HrlyNEMACCTable" for Type 4
HrlyNEMTableCol  = ClimateZone           // Column index (1-16)
NEMGrossUpPctInp = 6.6                   // Default gross-up %
NEMGrossUpFactor = 0.066                 // Calculated from %
```

### 2. Calculation Function

PV and Battery exports are processed through `ApplyHourlyResultMultipliers_NEM()`:

**Function signature:**
```
ApplyHourlyResultMultipliers_NEM(
  table1, table2, table2col,     // Primary/secondary tables
  multiplier1, table3, table3col, // Multipliers
  multiplier2,                    // Secondary multiplier
  runID,                          // Simulation run
  meterName, endUseName,          // Meter & end use
  endUse2Name,                    // Second end use
  NEMAdjustment,                  // NEM adjustment factor
  HrlyNEMTableName,              // "HrlyNEMTable" or "HrlyNEMACCTable"
  HrlyNEMTableCol,               // Climate zone column
  NEMGrossUpFactor,              // 0.066 default
  excludeFlag,                   // Optional: exclude certain components
  excludeEndUse                  // Optional: which end use to exclude
)
```

### 3. Where Applied

NEM3 adjustments are applied to:

1. **PV Generation** (RunResults[13])
   - Electricity source energy calculations
   - TDV (Time-Dependent Valuation) calculations
   - Only when `NetEnergyMeteringSrcAdj != 0` or `NetEnergyMeteringTDVAdj != 0`

2. **Battery Storage** (RunResults[14])
   - When battery exports to grid
   - Coordinated with PV to avoid double-counting

### 4. Source Energy Calculation Example

From `Rules_Results_SrcEnergy.rule`:

```
"Calculate Src - Elec - PV"  Proj:RunResults[13]:PropElecSrc[1] =
  { if (IfValidAnd(NetEnergyMeteringSrcAdj != 0))
    then int((100 * ApplyHourlyResultMultipliers_NEM(
                "none", EDR1TableName, ((ClimateZone-1) * 3) + 1,
                SrcMult_Elec, SrcSecTbl_Elec, ClimateZone, SrcSecMult_Elec,
                RunID, "MtrElec", "PV", "Tot",
                NetEnergyMeteringSrcAdj,
                HrlyNEMTableName, HrlyNEMTableCol, NEMGrossUpFactor
              ) / CondFloorArea) + 0.5) / 100
    else ... endif }
```

## NEM Gross-Up Factor

### Purpose
The **6.6% gross-up factor** accounts for system losses and adjustments in the export valuation:

- **Input:** `NEMGrossUpPctInp = 6.6%`
- **Applied:** `NEMGrossUpFactor = 0.066`
- **Effect:** Increases the credit value of exports by 6.6%

### Rationale
This factor accounts for:
1. Transmission/distribution losses avoided by local generation
2. Line loss credits
3. Other system benefits not captured in base export rates

## Key Properties Summary

### Project-Level Properties

| Property | Type | Units | Purpose |
|----------|------|-------|---------|
| `NetEnergyMeteringType` | Symbol | - | Selects NEM version (0/2/3/4) |
| `HrlyNEMTableName` | String | - | Name of hourly factor table |
| `HrlyNEMTableCol` | Integer | - | Climate zone column (1-16) |
| `NEMGrossUpPctInp` | Float | % | User-visible gross-up % |
| `NEMGrossUpFactor` | Float | - | Calculated factor (0.066) |
| `NetEnergyMeteringTDVAdj` | Float | TDV/Btu | TDV adjustment (0 for NEM3) |
| `NetEnergyMeteringNSCAdj` | Float | TDV/kWh | Net surplus compensation |
| `NetEnergyMeteringSrcAdj` | Float | Btu/Btu | Source energy adjustment |
| `NetEnergyMeteringNSCSrcAdj` | Float | Btu/kWh | NSC source adjustment |

## Impact on Compliance

### Compared to NEM2

**NEM2 Behavior (2022 and earlier):**
- Single adjustment factor: 0.985 (98.5% retail credit)
- Applied uniformly to all hours
- Simple calculation: `export_value = generation × 0.985 × TDV_multiplier`

**NEM3 Behavior (2025+):**
- 8,760 unique hourly factors per climate zone
- Time-varying valuation reflects grid conditions
- More complex: `export_value = ∑(hourly_generation × hourly_LSC_factor × gross_up)`

### Financial Impact

The shift from NEM2 to NEM3 generally results in:
- **Lower overall export credits** (especially for basic solar-only systems)
- **Higher incentive for batteries** (shift export to high-value hours)
- **Greater value from self-consumption** (using solar on-site vs. exporting)

### Example Scenario

**Climate Zone 12, typical residential PV system:**

| Time | Solar Generation | NEM2 Value | NEM3-LSC Value | NEM3-ACC Value |
|------|------------------|------------|----------------|----------------|
| Noon (high sun) | 5 kW | High | Low (surplus) | Low |
| 6pm (peak demand) | 0 kW | N/A | High (if battery) | Medium |
| Midnight | 0 kW | N/A | Low | Low |

**Result:** Systems with battery storage get significantly better credits under NEM3 because they can shift exports to high-value evening hours.

## Implementation Notes

### For Compliance Calculations

1. **NEM3-LSC is the default** for 2025 Title 24 compliance
2. **NEM2 is blocked** - software will error if attempted for 2025+
3. **Both LSC and ACC options** are available, user can select
4. **Climate zone matters** - factors vary significantly by CZ
5. **Hourly resolution required** - cannot use simplified monthly averages

### For Software Developers

When implementing NEM3 support:

1. Load the appropriate hourly factor table (LSC or ACC)
2. Match hourly PV/battery output to corresponding LSC/ACC factors
3. Apply climate-zone-specific column
4. Apply 6.6% gross-up factor
5. Integrate with TDV and source energy calculations
6. Ensure NEM2 is disabled for 2025+ code year

## Data Files Location

```
/CBECC 2025 Data/Documents/RulesetSource/T24N/shared/Tables/
  ├── T24 2025 NEM3-LSC Factors by CZ.csv  (LSC method)
  └── T24 2025 NEM3-ACC Factors by CZ.csv  (ACC method)
```

## Regulatory References

### Source Documents
- **LSC Factors:** E3 via CEC, April 2023
  - Original: `PV_Export_Factors_20221209.xlsx`
- **ACC Factors:** CEC/RJW, July 2024
  - Original: `2025_LSCHourlyExportValuesACC.xlsx`

### Policy Context
- CPUC Decision D.22-12-056 (NEM3 decision)
- Title 24 Part 6, Section 140.10 (2025 Standards)
- California Energy Commission TN 240481 and related TNs

## Questions & Answers

### Q: Why are NEM3 values so time-variable?
A: They reflect actual grid conditions. Evening hours have high value because that's when demand peaks but solar isn't generating. Midday exports have lower value because there's abundant solar generation.

### Q: Should I use LSC or ACC factors?
A: **LSC is the default** and most commonly used. ACC factors may be used for specific utility programs or analyses, but LSC is the standard for Title 24 compliance.

### Q: What happened to NEM2?
A: NEM2 is blocked for 2025+ analysis. The California Energy Commission transitioned to NEM3 to better reflect grid value and encourage battery storage adoption.

### Q: How does this affect battery sizing?
A: NEM3 makes batteries much more valuable because they can shift exports from low-value (midday) to high-value (evening) hours. This typically justifies larger battery systems.

### Q: Can users override the 6.6% gross-up?
A: The current ruleset allows the input `NEMGrossUpPctInp`, but changing it may require research mode depending on implementation. Default is 6.6%.

## Summary

NEM3 represents a fundamental shift in how California values distributed solar generation:

✓ **Time-of-use export valuation** replaces flat-rate crediting
✓ **Encourages battery storage** through higher evening export values
✓ **Promotes self-consumption** over grid export
✓ **Climate-zone-specific** hourly factors for accuracy
✓ **Two methodologies available:** LSC (default) and ACC

The implementation in CBECC 2025 is comprehensive, using 8,760 hourly factors per climate zone to accurately model the value of solar exports under California's new net metering paradigm.
