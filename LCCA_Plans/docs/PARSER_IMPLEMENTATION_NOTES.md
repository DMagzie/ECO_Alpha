# LCCA Parser Implementation Notes

## Overview

Two parsers have been implemented for CBECC simulation outputs:

1. **HourlyResultsParser** - Parses `* - HourlyResults.csv` files
2. **CseHourlyParser** - Parses `*-CSE.CSV` files

## Building Type Support

The HourlyResultsParser automatically detects and handles different building types:

| Building Type | NonRes Area | Res Area | Separate Data |
|--------------|-------------|----------|---------------|
| Residential | 0 | > 0 | No |
| NonResidential | > 0 | 0 | No |
| MixedUse | > 0 | > 0 | Yes |

### Mixed-Use Buildings

For mixed-use buildings, the parser provides:

- **Combined data**: `annual` and `hourly` contain aggregated totals
- **Separate NonRes data**: `annual_nonres` and `hourly_nonres`
- **Separate Res data**: `annual_res` and `hourly_res`
- **PV/Battery**: Assigned to combined only (building-wide)

### Column Layout Detection

Single-use buildings have 55 columns (0-54):
- Cols 4-16: Electric (13 end-uses)
- Cols 17-29: Gas (13 end-uses)
- Cols 30-42: Propane (13 end-uses)
- Cols 43-51: TDV/Source/CO2 multipliers
- Cols 53-54: PV/Battery

Mixed-use buildings have 108+ columns with two sections:
- Cols 4-54: NonRes section (same as single-use)
- Cols 55-58: PV/Batt weighted avg multipliers
- Cols 59-107: Res section (same structure as NonRes)

## File Format Comparison

### HourlyResults.csv (Recommended for LCCA)

**Source:** CEC Compliance Manager output
**Location:** `{project} - run/{project} - {ap|ab} - HourlyResults.csv`
**File Size:** ~2.3 MB per model (Bressi Ranch)

**Advantages:**
- Aggregated building totals (includes zone multipliers)
- TDV multipliers per hour
- Source energy multipliers per hour
- CO2 emissions multipliers per hour
- PV generation and battery data
- Full 8760 hours

**Data Structure:**
```
Header metadata (lines 1-17):
- Software version, CompMgr version, CSE version
- Run title, date/time
- NonRes and Residential conditioned areas
- Model type (Proposed/Standard)
- Model file path

Column groups:
- Site Electric Use (kWh): Spc Heat, Spc Cool, Indr Fans, Heat Rej, Pump&Misc, Dom HW, Lighting, Recept, Process, Othr Ltg, Proc Mtrs, Tot Comp, TOTAL
- Site Natural Gas Use (kBtu): Same breakdown
- Site Propane Use (kBtu): Same breakdown
- TDV Multipliers: Electric, NatGas, OtherFuel
- Source Energy Multipliers: Electric, NatGas, OtherFuel
- CO2 Emissions Multipliers: Electric, NatGas, OtherFuel
- Elec Demand, PV, Battery
```

### CSE.CSV (Alternative)

**Source:** California Simulation Engine direct output
**Location:** `{project} - run/{PROJECT} - {AP|AB}-CSE.CSV`
**File Size:** ~2.8 MB per model (Bressi Ranch)

**Characteristics:**
- Meter-based rows (MtrElec, MtrElec2, MtrNatGas)
- Raw simulation output
- No TDV/Source/CO2 multipliers
- All energy reported in kBtu (converted by parser)

**Unit Conversions Applied by Parser:**
- Electricity: kBtu → kWh (divide by 3.412)
- Gas: kBtu → therms (divide by 100)

**After Conversion:**
- Electricity values match HourlyResults within 0.02%
- Gas values match HourlyResults within 0.01%

## Tested Sample Projects

| Project | Type | NonRes (SF) | Res (SF) | Hours | Elec (kWh) | Gas (therms) |
|---------|------|------------|----------|-------|------------|--------------|
| Bressi Ranch | Res-only | 0 | 310,100 | 8,760 | 1,518,277 | 36,936 |
| Del Amo | Res-only | 0 | 184,131 | 8,760 | 1,878,455 | 18,174 |
| Euclid A | Res-only | 0 | 86,722 | 8,760 | 529,718 | 8,497 |
| Freedom Circle A | MixedUse | 54,613 | 332,838 | 8,760 | 2,720,487 | 35,757 |

## Usage

```python
from eco_tools.lcca.parsers import parse_hourly_results, parse_cse_csv

# Parse HourlyResults (recommended)
result = parse_hourly_results("/path/to/project - ap - HourlyResults.csv")

# Access combined annual summary
print(f"Total Electricity: {result.annual.total_elec_kwh:,.0f} kWh")
print(f"Total Gas: {result.annual.total_gas_therm:,.1f} therms")
print(f"Peak Demand: {result.annual.peak_demand_kw:,.1f} kW")
print(f"TDV Total: {result.annual.tdv_total:,.0f} kTDV")

# Access hourly data
for h in result.hourly:
    print(f"{h.month}/{h.day} Hr{h.hour}: {h.elec_total_kwh:.1f} kWh")

# For mixed-use buildings, access separate NonRes/Res data
if result.is_mixed_use:
    print(f"NonRes Electricity: {result.annual_nonres.total_elec_kwh:,.0f} kWh")
    print(f"Res Electricity: {result.annual_res.total_elec_kwh:,.0f} kWh")

    # Separate hourly data also available
    for h_nr, h_res in zip(result.hourly_nonres, result.hourly_res):
        print(f"NR: {h_nr.elec_total_kwh:.1f}, Res: {h_res.elec_total_kwh:.1f}")
```

## File Naming Convention

Files use prefixes to indicate model type:
- `ap` = Analysis Proposed (the designed building)
- `ab` = Analysis Baseline/Standard (code baseline)
- `zp` = Zone Proposed (zone-level data)
- `zb` = Zone Baseline

## Recommendation

**Use HourlyResults.csv for LCCA** because:
1. Values include zone multipliers (building totals)
2. TDV data is essential for California Title 24
3. CO2 emissions data supports ESG reporting
4. PV/Battery data is readily available

Use CSE.CSV only if:
- HourlyResults is not available
- You need zone-level (non-aggregated) data
- You're debugging simulation issues
