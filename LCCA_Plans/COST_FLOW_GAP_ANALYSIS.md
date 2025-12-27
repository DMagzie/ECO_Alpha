# LCCA Cost Flow Gap Analysis

**Date:** December 2024 (Updated December 23, 2024)
**Project:** Euclid Building A + Office Large (Reference Case Studies)
**Status:** Analysis Complete - Implementation Pending

## Executive Summary

The LCCA module has complete **operational cost analysis** (energy costs, TOU rates, NPV/IRR/payback) but relies on **user-input CAPEX** rather than auto-calculating incremental costs from baseline vs proposed model differences.

This document identifies gaps between simulation output data and cost database lookups, with recommendations for bridging them.

---

## 1. HVAC Systems Gap

### Current State

| Component | Status |
|-----------|--------|
| CostDB system costs | ✅ Available (heat_pump_air, vrf, dx_packaged, etc.) |
| Regional factors | ✅ Available (23 CA/HI regions) |
| HVAC spec in simulation output | ✅ Available in HVACSecondary.csv |
| Parser for HVACSecondary.csv | ❌ **MISSING** |
| CBECC→CostDB type mapper | ❌ **MISSING** |
| Efficiency-based cost adjustment | ❌ **MISSING** |
| Auto-calculated incremental cost | ❌ **MISSING** |

### Data Available in HVACSecondary.csv

```
AirSystems Section:
- Name, Type (SZHP, VRF, etc.), Status, System Count
- Cooling: Net Capacity (Btu/hr), Design Supply T
- Heating: Net Capacity (Btu/hr), Design Supply T
- Fan/Ventilation: Supply Flow (cfm)

Cooling Coils Section:
- Type (DirectExpansion, ChilledWater)
- Capacity (Total-Net, Total-Gross Btu/hr)
- SEER, EER, SEER2, EER2

Heating Coils Section:
- Type (HeatPump, Furnace, Resistance)
- Capacity (Btu/hr)
- HSPF, COP, HSPF2, AFUE
```

### Euclid Example

| Metric | Baseline | Proposed | Delta |
|--------|----------|----------|-------|
| System Count | 13 SZHP | 13 SZHP | 0 |
| Total Cooling | 261,469 Btu/hr | 468,200 Btu/hr | +79% |
| Total Heating | 284,054 Btu/hr | 456,500 Btu/hr | +61% |
| Cooling Tons | 21.8 tons | 39.0 tons | +17.2 tons |
| Avg SEER | 15.05 | 15.5 (mix) | Higher |
| High-Eff Units | 0 | 2 (SEER 22+) | +2 |

### Cost Impact (Using CostDB)

```
Baseline HVAC Cost:  $37,772 (LA regional factor 1.12)
Proposed HVAC Cost:  $63,776
─────────────────────────────────────────────────────
Incremental Cost:    $26,004

Current workflow uses user-input: $100,000 (estimate)
```

### Required Components

1. **HVACSpecParser** - Parse HVACSecondary.csv sections
2. **CEBCCSystemMapper** - Map CBECC types to CostDB codes:
   - SZHP → heat_pump_air
   - VRF → vrf
   - PTAC → ptac
   - Furnace → furnace_gas
3. **EfficiencyAdder** - Cost multipliers for above-code efficiency:
   - SEER 14.3 (code min): 1.00x
   - SEER 15-17: 1.10x
   - SEER 18-21: 1.25x
   - SEER 22+: 1.40x

---

## 2. DHW Systems Gap

### Current State

| Component | Status |
|-----------|--------|
| CostDB DHW costs | ✅ Available (water_heater_gas, water_heater_heat_pump) |
| DHW spec in simulation output | ⚠️ In HVACPrimary.csv (Residential Water Heater section) |
| Parser for DHW specs | ❌ **MISSING** |
| Cost comparison baseline vs proposed | ❌ **MISSING** |

### Data Available in HVACPrimary.csv

```
Residential Water Heater Section:
- Name, System Type, System Count
- Type (Storage, Instantaneous, Heat Pump)
- Fuel (Electric, Gas)
- Thermal Efficiency
- Storage Capacity (gal)
- Rated Capacity (Btu/h)
- Energy Factor
```

### DHW Data Available in HVACPrimary.csv (Office Large Example)

```
Water Heater Section:
- Name: WaterHeaterElec
- Type: Conventional
- Fuel: Electricity
- Capacity: 179.5 gal storage, 178,509 Btu/h
- Thermal Efficiency: 1.0 (100%)

Central Plant (also in HVACPrimary.csv):
- Boiler: 2x Gas @ 3.35 MBtu/h, 90% efficiency
- Chiller: 2x Centrifugal @ 5.1 MBtu/h, COP 6.01
- Cooling Tower: 2x @ 5.96 MBtu/h
- Pumps: HW, CW, ChW with flow rates and HP
```

### CostDB Gaps for DHW

| Available | Missing |
|-----------|---------|
| water_heater_gas: $3,500/each | water_heater_electric (conventional) |
| water_heater_heat_pump: $4,500/each | water_heater_tankless |
| boiler_gas: $45/MBH | central_hpwh (large) |
| | chiller_centrifugal (capacity-based) |
| | cooling_tower (capacity-based) |

### Required Components for DHW

1. **FluidSystemParser** - Parse HVACPrimary.csv sections
2. **DHW Type Mapper** - Conventional→electric/gas, HeatPump→hpwh
3. **Central Plant Costs** - Boiler, chiller, tower by capacity

---

## 3. Envelope Gap

### Current State

| Component | Status |
|-----------|--------|
| CostDB envelope costs | ⚠️ Limited (insulation $/SF, windows $/SF) |
| Envelope spec in simulation output | ✅ Available in Envelope.csv |
| Parser for Envelope.csv | ❌ **MISSING** |
| R-value/U-factor cost curves | ❌ **MISSING** |
| Cost comparison baseline vs proposed | ❌ **MISSING** |

### Data Available in Envelope.csv (Office Large Example)

```
Building Summary:
- Total Floor Area: 498,589 SF
- 12 Above-Grade Stories
- Climate Zone 12

Wall Area:
- Total Ext Wall: 124,726 SF
- N/S: 37,418 SF each
- E/W: 24,945 SF each
- Wall Type: MetalFrameWallU055

Window Area:
- Total Window: 48,129 SF
- N/S: 14,439 SF each
- E/W: 9,625 SF each
- Window-to-Wall Ratio: 38.59%

Roof:
- Total Area: 38,353 SF
- Type: FlatNonresWoodFramingAndOtherRoofU034

Window Specs (NFRC Rated):
- Product: FixedWindow
- U-Factor: 0.34 Btu/h-°F-ft²
- SHGC: 0.22
- Visual Transmittance: 0.42

Construction Assemblies:
- Wall: Stucco + R-14.60 + R-1.41 insulation + Air + Gypsum
- Roof: Metal Standing Seam + R-28.63 insulation
- Slab: F-factor 0.73

Construction Materials (with R-values):
- Compliance Insulation R28.63: 4.57" board insulation
- Compliance Insulation R14.60: 2.33" board insulation
- Concrete 140 lb/ft³: R-0.30 (4")
- Gypsum Board: R-0.45 (½")
```

### CostDB Gaps for Envelope

| Available | Missing |
|-----------|---------|
| insulation: Generic $/SF | insulation_r15, insulation_r20, insulation_r29 (R-value specific) |
| window: Generic $/SF | window_u040, window_u034, window_u030 (U-factor specific) |
| | window_shgc_025, window_shgc_022 (SHGC adders) |
| | cool_roof premium (aged reflectance based) |
| | metal_frame_wall vs wood_frame_wall |

### Envelope Cost Comparison Example

```
If baseline uses code-minimum envelope:
- Wall: R-13 insulation
- Roof: R-25 insulation
- Window: U-0.46, SHGC 0.25

And proposed uses above-code:
- Wall: R-16.01 (R-14.60 + R-1.41)
- Roof: R-28.63 insulation
- Window: U-0.34, SHGC 0.22

Premium Calculation:
- Wall upgrade: 124,726 SF × $0.15/SF = $18,709
- Roof upgrade: 38,353 SF × $0.25/SF = $9,588
- Window upgrade: 48,129 SF × $2.50/SF = $120,323
─────────────────────────────────────────────────────
Estimated Envelope Premium: $148,620

(Placeholder rates - need R-value/U-factor cost curves)
```

### Required Components for Envelope

**Note:** Envelope uses generic material/layer costs only (no manufacturer-specific pricing). Material substitutions are common during construction, so costs are calculated by material type and performance tier.

1. **EnvelopeParser** - Parse Envelope.csv sections:
   - Wall/Window/Roof areas
   - Construction assemblies by layer
   - Material R-values from material list
   - Window U-factor/SHGC

2. **Generic Material Cost Database** - By material type:
   ```
   Insulation ($/SF):
   - Batt R-13: $0.45     - Batt R-19: $0.55     - Batt R-21: $0.62
   - Rigid R-5: $0.80     - Rigid R-10: $1.40    - Rigid R-15: $2.00
   - Spray Foam R-20: $1.50  - Spray Foam R-30: $2.25

   Framing ($/SF of wall):
   - Wood Frame 2x4: $3.50   - Wood Frame 2x6: $4.25
   - Metal Frame 3.5": $4.00 - Metal Frame 6": $5.00

   Cladding ($/SF):
   - Stucco: $8.50       - Fiber Cement: $7.00
   - Metal Panel: $12.00  - Brick Veneer: $18.00
   ```

3. **Window Performance Cost Tiers** (Generic, not manufacturer-specific):
   ```
   U-Factor Tier ($/SF):
   - Standard (U-0.46): $45    - Code (U-0.40): $52
   - Better (U-0.34): $62      - Best (U-0.28): $78

   SHGC Tier ($/SF adder):
   - Standard (0.25): +$0      - Low-E (0.22): +$3
   - Very Low (0.18): +$6
   ```

4. **Roof Assembly Costs** ($/SF):
   - Built-up R-25: $12.00    - Built-up R-30: $13.50
   - Metal + R-25: $15.00     - Metal + R-30: $16.50
   - Cool roof adder (0.63+ reflectance): +$0.75

---

## Recommendations

### Phase 1: HVAC Cost Bridge (Priority: High)
- Create HVACSpecParser for HVACSecondary.csv
- Implement CBECC→CostDB mapper
- Add efficiency cost multipliers
- Auto-calculate HVAC incremental cost

### Phase 2: DHW Cost Bridge (Priority: Medium)
- Create DHWSpecParser for HVACPrimary.csv
- Map DHW types to CostDB codes
- Account for heat pump vs gas vs electric

### Phase 3: Envelope Cost Bridge (Priority: Medium)
- Create EnvelopeSpecParser for Envelope.csv
- Add R-value cost curves to CostDB
- Add window U-factor cost curves
- Calculate envelope premium costs

### Phase 4: Integration
- Combine all incremental costs
- Display breakdown in LCCA Dashboard
- Allow user override with manual CAPEX

### Phase 5: AHRI Certification Lookup - HVAC & DHW (Priority: Medium-High)

**Purpose:** Enable accurate equipment-specific cost lookups for permit-ready models.

**Applies To:** HVAC Systems AND DHW Systems (same methodology)

**Two-Tier Approach:**

| Tier | Model Phase | Data Source | Accuracy |
|------|-------------|-------------|----------|
| Tier 1 | Early Design | Rules of thumb (efficiency adders) | ±20-30% |
| Tier 2 | Permit Ready | AHRI certified equipment lookup | ±5-10% |

**Current Gap:**
- CBECC captures efficiency specs (SEER, HSPF, EER, COP, UEF)
- CBECC does NOT capture: Manufacturer, Model, AHRI Certificate Number
- Cost estimates rely on generic efficiency adders

**Tier 2 Enhancement - AHRI Integration:**

```
HVAC Equipment (NEW fields):
├── Indoor Unit
│   ├── Manufacturer
│   ├── Model Number
│   └── AHRI Cert Number (links indoor/outdoor combo)
│
├── Outdoor Unit
│   ├── Manufacturer
│   ├── Model Number
│   └── Capacity (MBH)
│
└── AHRI Lookup
    ├── Certified Ratings (SEER2, HSPF2, EER2)
    ├── Validated Combo
    └── Equipment-specific cost lookup

DHW Equipment (NEW fields):
├── Water Heater
│   ├── Manufacturer
│   ├── Model Number
│   └── AHRI Cert Number
│
└── AHRI Lookup
    ├── Certified UEF (Uniform Energy Factor)
    ├── First Hour Rating
    └── Equipment-specific cost lookup
```

**Benefits:**
- Accurate equipment costs (vs generic capacity-based)
- Validated indoor/outdoor pairings (HVAC)
- Support for manufacturer rebate programs
- Enables AHRI directory API integration

**Required Components:**

1. **CBECC Model Extension** - Add AHRI fields to equipment objects:
   - HVACSys.AHRICertNum, IndoorMfr, IndoorModel, OutdoorMfr, OutdoorModel
   - WtrHtr.AHRICertNum, Manufacturer, Model

2. **AHRI Directory Connector** - API integration:
   - Lookup by cert number → get ratings
   - Lookup by model numbers → find valid combos
   - Cache results locally

3. **Equipment Cost Database** - Manufacturer pricing:
   - Distributor pricing by model
   - Regional availability
   - Lead time factors

4. **Fallback Logic** - Graceful degradation:
   - If AHRI data present → use Tier 2 (equipment-specific)
   - If AHRI data missing → use Tier 1 (efficiency adders)
   - Always allow user override

**Implementation Notes:**
- AHRI directory is public: https://www.ahridirectory.org/
- API may require registration for bulk access
- Consider caching common equipment combos
- Support both residential (AHRI) and commercial (AHRI/IPLV) ratings

---

### Cost Methodology by Category

| Category | Methodology | Rationale |
|----------|-------------|-----------|
| **HVAC** | Two-tier (Generic → AHRI) | Equipment is specified; manufacturer matters for rebates |
| **DHW** | Two-tier (Generic → AHRI) | Same rationale as HVAC |
| **Envelope** | Generic material/layer costs only | Material substitutions common during construction |
| **PV/Battery** | Two-tier possible | Future: specific panel/inverter combos |

**Envelope Cost Philosophy:**
- Use generic costs per material type and layer
- Cost by assembly component, not manufacturer
- Example: "R-19 batt insulation" not "Owens Corning R-19"
- Supports specification flexibility during construction
- Aligns with typical bid alternates and value engineering

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                    SIMULATION OUTPUTS                        │
├─────────────────┬─────────────────┬─────────────────────────┤
│ HVACSecondary   │ HVACPrimary     │ Envelope.csv            │
│ .csv            │ .csv (DHW)      │                         │
└────────┬────────┴────────┬────────┴────────┬────────────────┘
         │                 │                 │
         ▼                 ▼                 ▼
┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
│ HVACSpecParser  │ │ DHWSpecParser   │ │ EnvelopeParser  │
│ (NEW)           │ │ (NEW)           │ │ (NEW)           │
└────────┬────────┘ └────────┬────────┘ └────────┬────────┘
         │                 │                 │
         ▼                 ▼                 ▼
┌─────────────────────────────────────────────────────────────┐
│                  CBECC → CostDB MAPPER                       │
│  SZHP → heat_pump_air    Storage → water_heater_gas         │
│  VRF → vrf               HPWH → water_heater_heat_pump      │
│  PTAC → ptac             R-19 batt → insulation_batt_r19    │
└────────┬───────────────────┬────────────────┬───────────────┘
         │                   │                │
         ▼                   ▼                ▼
┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
│ TWO-TIER LOOKUP │ │ TWO-TIER LOOKUP │ │ GENERIC ONLY    │
│ (HVAC)          │ │ (DHW)           │ │ (Envelope)      │
├─────────────────┤ ├─────────────────┤ ├─────────────────┤
│ Tier 1: Rules   │ │ Tier 1: Rules   │ │ Material type   │
│ of thumb        │ │ of thumb        │ │ + performance   │
│ (±20-30%)       │ │ (±20-30%)       │ │ tier costs      │
├─────────────────┤ ├─────────────────┤ │ (no mfr-spec)   │
│ Tier 2: AHRI    │ │ Tier 2: AHRI    │ │                 │
│ equipment       │ │ equipment       │ │                 │
│ lookup (±5-10%) │ │ lookup (±5-10%) │ │                 │
└────────┬────────┘ └────────┬────────┘ └────────┬────────┘
         │                   │                   │
         └───────────────────┴───────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────┐
│                        CostDB v0.07+                         │
│  System costs + Regional factors + Efficiency adders         │
│  + AHRI equipment DB + Generic material costs                │
└────────────────────────────┬────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────┐
│              INCREMENTAL COST CALCULATOR                     │
│  = Σ(proposed) - Σ(baseline) for HVAC + DHW + Envelope + PV │
└────────────────────────────┬────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────┐
│                     LCCA WORKFLOW                            │
│  Uses calculated incremental cost (or user override)         │
└─────────────────────────────────────────────────────────────┘
```

---

## Appendix: CostDB System Codes

### Currently Available
```
HVAC:
- chiller_air_cooled, chiller_water_cooled
- dx_split, dx_packaged, vrf, ptac, pthp
- boiler_gas, boiler_electric
- furnace_gas, heat_pump_air, heat_pump_water
- fan_coil, vav_box

DHW:
- water_heater_gas, water_heater_electric
- water_heater_heat_pump, solar_thermal

Renewables:
- pv_rooftop, pv_carport, pv_ground
- battery_storage

Controls:
- bms, thermostat_programmable, thermostat_smart
```

### Needed Additions
```
Envelope:
- insulation_wall_r13, insulation_wall_r19, insulation_wall_r21
- insulation_roof_r30, insulation_roof_r38, insulation_roof_r49
- window_u035, window_u030, window_u025
- window_shgc_025, window_shgc_022
```
