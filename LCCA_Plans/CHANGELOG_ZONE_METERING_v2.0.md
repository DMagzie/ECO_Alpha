# Zone-Level Metering Milestone - v2.0

**Release Date:** December 31, 2024
**Status:** VALIDATED - Production Ready

---

## Summary

The CSE Zone-Level Metering solution has been fully validated and is ready for production use. This milestone represents a significant achievement in enabling granular energy analysis for LCCA calculations.

---

## Key Accomplishments

### 1. Exact Validation (0.0000% Difference)

Tested on MF8Unit_2Story_NGAS-CZ12 (no story multipliers):
- Zone meters sum to building total with **zero difference**
- All end-uses verified (Htg, Clg, Lit, Rcp, Dhw, Refr)
- Proves core transformation logic is mathematically exact

### 2. Multiplier Compatibility Confirmed

Tested on Ventura & 7th (real-world project with story multipliers):
- Transformation correctly preserves existing meter hierarchy
- Observed 3% ratio difference explained by unequal DU distribution per floor
- NOT an error - reflects actual building design

### 3. Model Survey Completed

Surveyed 7 CBECC models (standard samples + real-world projects):
- 6 of 7 models do NOT use story multipliers
- Ventura & 7th is an outlier in using `mtrSubMeterMults`
- Solution works correctly for both approaches

---

## Technical Learnings

### Critical Implementation Details

| Learning | Description |
|----------|-------------|
| Export Scaling | Must include `exBtuSf = 1000` for kWh output |
| Export Location | Insert before RUN statement, not after existing exports |
| Meter Independence | Zone meters and building meters coexist without conflict |

### Multiplier Behavior

| Energy Type | Multiplier Applied? | Mechanism |
|-------------|---------------------|-----------|
| Internal Gains (gnMeter) | Yes | Via submeter rollup |
| HVAC (rsElecMtr) | Yes | Via submeter rollup |
| DHW (wsElecMtr) | No | Direct to meter (explicit per-DU) |

---

## Capabilities Unlocked

1. **Per-Zone TOU Analysis** - 8760 hourly data per zone
2. **VNBT Allocation** - Solar credits to specific zones
3. **Common Area Attribution** - Corridor, fitness, lobby costs separated
4. **Mixed-Use Separation** - Residential vs. commercial metering
5. **DU Type Analysis** - Energy by bedroom count

---

## Files Updated/Created

| File | Action |
|------|--------|
| `LCCA_Plans/reference/cse_lcca_architecture.md` | Updated to v2.0 |
| `LCCA_Plans/CHANGELOG_ZONE_METERING_v2.0.md` | Created (this file) |

---

## Validation Data

### Primary Test: MF8Unit_2Story_NGAS-CZ12

```
Zone1:     38,965.03 kWh
Zone2:     42,059.08 kWh
═══════════════════════════
Total:     81,024.12 kWh
Original:  81,024.12 kWh
Difference: 0.00 kWh (0.0000%)
```

### Secondary Test: Ventura & 7th

```
Floor Distribution:
  L01:     12 DUs (4+4+4)
  L02-03:  14 DUs/floor × 2 = 28 DUs (4+5+5 per floor)
  L04:     14 DUs (4+5+5)
  Total:   54 DUs

Meter Multipliers: mtrSubMeterMults = 1, 2, 1

Result: Zone transformation correctly preserves hierarchy
        and produces results matching building design
```

---

## Next Steps

1. ~~**TOU Integration**~~ - Connect zone hourly data to tariff calculations ✅ **COMPLETE (Jan 1, 2025)**
2. ~~**VNBT Allocation**~~ - Connect zone meters to per-zone PV credits ✅ **COMPLETE (Jan 1, 2025)**
3. ~~**CLI Integration**~~ - Add `zone-analyze` command ✅ **COMPLETE (Jan 1, 2025)**
4. ~~**GUI Integration**~~ - Zone analysis in ECO Tools Streamlit interface ✅ **COMPLETE (Jan 1, 2025)**
5. ~~**Gas Metering**~~ - Extend to natural gas meters ✅ **COMPLETE (Jan 1, 2026)**

---

## Update: Gas Metering Extension Complete (January 1, 2026)

The zone-level metering infrastructure has been extended to support natural gas metering in parallel to electric:

### Gas Meter Architecture

```
MtrGas (Building Total)
├── MtrGas_Residential (All DUs)
│   ├── MtrGas_DU_1BR
│   ├── MtrGas_DU_2BR
│   └── MtrGas_DU_3BR
├── MtrGas_CommonArea
│   ├── MtrGas_CA_MECHANICAL
│   └── MtrGas_CA_LAUNDRY
└── MtrGas_NonResidential
```

### Key Implementation Details

| Component | File | Changes |
|-----------|------|---------|
| Zone Meter Mapper | `zone_meter_mapper.py` | Added gas meter fields and hierarchy generation |
| CSE Transformer | `cse_transformer.py` | Added gas meter injection and RSYS fuel meter updates |
| Output Parser | `parsers/cse_zone_output.py` | Added `ZoneGasHourlyData` and gas meter parsing |
| Zone Simulation | `zone_simulation.py` | Added gas data population to `ZoneEnergySummary` |
| CLI | `cli.py` | Extended `zone-analyze` with gas cost display |
| GUI | `zone_analysis_page.py` | Extended zone import and cost display for gas |

### Gas vs Electric Differences

| Aspect | Electric | Gas |
|--------|----------|-----|
| Rate structure | TOU (hourly varying) | Flat ($/therm) |
| Peak demand | kW (important for charges) | N/A |
| End-uses | 9+ categories | 3 categories (Htg, Dhw, Cook) |
| Zone coverage | All zones | Subset (not all have gas) |
| Units | kWh | therms (1 therm = 100 kBtu) |
| CSE BTU scaling | exBtuSf = 1000 | exBtuSf = 100 |

### CLI Usage

```bash
# Zone analysis with gas
python -m eco_tools.lcca zone-analyze /path/to/project --gas-rate 1.80

# Output shows both electric and gas:
# 1BR Dwelling Units:
#   Electric: 42,500 kWh → $12,750/yr
#   Gas:      850 therm  → $1,530/yr
#   TOTAL:    $14,280/yr
```

### Validation

13 unit tests pass covering:
- Gas meter assignment fields
- Gas meter hierarchy generation
- CSE transformation for gas
- Gas output parsing
- Zone energy summary gas fields
- CLI gas rate argument

### Files Created/Modified

| File | Action |
|------|--------|
| `eco_tools/lcca/zone_meter_mapper.py` | Extended with gas fields |
| `eco_tools/lcca/cse_transformer.py` | Extended with gas transformation |
| `eco_tools/lcca/parsers/cse_zone_output.py` | Extended with gas parsing |
| `eco_tools/lcca/zone_simulation.py` | Extended to populate gas data |
| `eco_tools/lcca/cli.py` | Extended zone-analyze for gas |
| `gui/pages/zone_analysis_page.py` | Extended for gas display |
| `tests/test_gas_metering.py` | Created (13 tests) |

---

## Update: TOU Integration Complete (January 1, 2025)

The zone-level hourly data (8760 values per zone) is now fully integrated with the TOU rate engine:

### Data Flow
```
CSE Zone Meters → ZoneEnergySummary.hourly_elec_kwh → ZoneCostAllocator → TouCostBreakdown
```

### Key Code Paths
| Component | File:Line | Function |
|-----------|-----------|----------|
| Hourly data population | `zone_simulation.py:346-353` | `create_zone_energy_from_hourly()` |
| TOU cost check | `zone_allocation.py:145-146` | Checks `hourly_elec_kwh` exists |
| TOU calculation | `zone_allocation.py:168-212` | `_calculate_tou_costs()` |
| Rate engine | `tariffs.py:225-368` | `calculate_tou_costs()` |

### TOU Breakdown Per Zone
Each zone now receives a complete TOU cost breakdown:
- Summer on-peak / mid-peak / off-peak costs
- Winter on-peak / mid-peak / off-peak costs
- Demand charges (facility, summer, winter)
- Fixed charges (customer, meter)

### Available Tariffs
15 CA/HI utility rates available in tariffs.py:
- PG&E: E-TOU-C, EV2-A, B-20
- SCE: TOU-D-4-9PM, TOU-D-PRIME, TOU-GS-3
- SDG&E: TOU-DR1, EV-TOU-5, AL-TOU
- Hawaii: HECO R-TOU, HECO R, MECO R, HELCO R
- Defaults: US-AVG, FLAT

---

## Update: VNBT Zone Allocation Complete (January 1, 2025)

Zone-level V-NBT (Virtual Net Billing Tariff) calculations now support per-zone PV allocation:

### Data Flow
```
Building PV Hourly → Zone Allocation → ZoneVnbtResult → Per-Zone Costs
```

### Key Code Paths
| Component | File:Line | Function |
|-----------|-----------|----------|
| Hourly-to-net conversion | `vnbt.py:650-700` | `convert_hourly_to_net_usage()` |
| Zone VNBT calculation | `vnbt.py:750-850` | `calculate_zone_vnbt()` |
| Result formatting | `vnbt.py:880-920` | `format_zone_vnbt_results()` |

### Allocation Methods
| Method | Description |
|--------|-------------|
| `by_consumption` | PV allocated proportionally to zone annual kWh |
| `by_kwdc` | PV allocated by zone DC capacity assignment |

### V-NBT Cost Components Per Zone
Each zone receives:
- Import costs at TOU rates
- Export credits at ACC (Avoided Cost Calculator) rates
- Non-Bypassable Charges (NBC) on imports
- Self-consumption tracking and value calculation

### Validation Results (Ventura & 7th)
```
Total Gross Load:     1,126,339 kWh
Total PV Generation:  1,753,181 kWh
Self-Consumption:       558,582 kWh (31.9% of PV)
Grid Import:            567,757 kWh
Grid Export:          1,194,599 kWh
Net Annual Cost:      $195,783.05
Savings vs No PV:     $142,119 (42.1%)
```

---

## Update: CLI Integration Complete (January 1, 2025)

New `zone-analyze` command added to the LCCA CLI:

### Usage
```bash
# TOU analysis (default)
python -m eco_tools.lcca zone-analyze /path/to/project

# V-NBT analysis with PV allocation
python -m eco_tools.lcca zone-analyze /path/to/project --vnbt

# Verbose output with detailed cost breakdown
python -m eco_tools.lcca zone-analyze /path/to/project --vnbt -v
```

### Features
- Auto-discovers CSE output file in project directory
- Parses zone-level hourly data (MtrElec_1bedrm, MtrElec_2bedrm, etc.)
- Calculates TOU or V-NBT costs per zone
- Shows PV allocation and self-consumption for VNBT mode
- JSON output option for integration

---

## Update: GUI Integration Complete (January 1, 2025)

Zone Analysis page in Streamlit dashboard enhanced with CSE import and V-NBT support:

### New Features
- **Import from Project**: Parse CSE output files directly from run folders
- **V-NBT Analysis Mode**: Toggle in sidebar to enable PV allocation and V-NBT costs
- **TOU/VNBT Cost Display**: Show per-zone costs after calculation

### Location
`gui/pages/zone_analysis_page.py` - Accessible via "Zone Analysis" in main navigation

### Usage
1. Navigate to "Zone Analysis" page
2. Select "Import from Project" mode
3. Enter path to CBECC run folder
4. Click "Discover & Import Zone Data"
5. Enable V-NBT in sidebar if desired
6. Click "Calculate TOU/VNBT Costs"

---

## Contributors

- Analysis and validation performed December 28-31, 2024
- Models tested: MF8Unit, MF36Unit, MF33Unit, Ventura & 7th, Freedom Circle, Euclid, Del Amo

---

*This milestone represents a foundation for advanced LCCA capabilities in ECO Tools.*
