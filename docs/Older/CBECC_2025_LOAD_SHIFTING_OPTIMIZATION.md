# Load Shifting Optimization in CBECC 2025
## Battery Storage & Heat Pump Water Heater Tank Sizing

**Date:** November 20, 2025
**Purpose:** Analysis of optimization strategies for battery storage and HPWH tank sizing under NEM3 and LSC compliance metrics

---

## Executive Summary

California Title 24 2025 introduces two major changes that fundamentally alter building energy system optimization:

1. **NEM3** - Time-varying solar export credits that heavily favor evening discharge
2. **LSC (Long-term System Cost)** - New compliance metric replacing TDV that values load shifting

These changes create **strong financial and compliance incentives** for:
- **Battery storage** to shift solar generation from midday to evening
- **Larger HPWH tanks** to provide thermal energy storage and load shifting capability

This document explores optimization strategies for both systems.

---

## Part 1: Battery Storage Optimization Under NEM3

### Key Finding: Battery Control Strategy Matters

CBECC 2025 implements **three battery control strategies**, with dramatically different performance under NEM3:

| Control Strategy | Code | Best For | NEM3 Benefit |
|------------------|------|----------|--------------|
| Default | 1 | Basic self-consumption | Low |
| Time of Use (TOU) | 10 | Predictable load shifting | **High** |
| Advanced DR Control | 101 | Peak event optimization | **Very High** |

### 1. Time of Use (TOU) Control

**Purpose:** Charge battery during low-value hours, discharge during high-value hours

**Key Parameters:**
- `TDVSummerPkFirstHr` - Hour when evening peak begins (default varies by CZ)
- `StandaloneChgStartHr` - Hour to begin charging (2025 default: 11 = noon)
- `TOUStartMonth` - Start of TOU control season (default: 1 = January)
- `TOUEndMonth` - End of TOU control season (default: 12 = December)

**2025 Control Logic for PV+Battery:**
```
IF hour < TDVSummerPkFirstHr (e.g., before 5pm):
  Charge battery from excess PV (or grid if standalone)
ELSE:
  Discharge to meet building load ONLY (not to grid)
```

**2025 Control Logic for Standalone Battery:**
```
Charging window: StandaloneChgStartHr to TDVSummerPkFirstHr (e.g., noon-5pm)
  -> Charge at max rate (1000 kW = "unlimited")

Discharge window: All other hours
  -> Discharge to meet building load ONLY
```

**Critical 2025 Change:** Batteries now discharge **only to building load**, not to grid. This aligns with NEM3's goal of self-consumption over export.

### 2. Advanced DR Control

**Purpose:** Target the highest TDV/LSC value days for maximum compliance benefit

**Key Parameters:**
- `BattDRNumRankedDays` - Number of top TDV days to target (default: 20)
- Uses weather file's `tdvElecPkRank` to identify peak days

**Control Logic:**
```
On ranked peak days (top 20 by default):
  IF hour is in charging window (StandaloneChgStartHr + 5 hours):
    Charge battery
  ELSE IF hour >= TDVSummerPkFirstHr:
    Discharge to building load

On non-peak days:
  Follow Default control (basic self-consumption)
```

**Advantage:** Focuses battery cycling on days that matter most for compliance, extending battery life while maximizing LSC benefit.

### Battery Sizing Optimization

#### Prescriptive Requirements (2025 Standards)

From Table 140.10-B, battery capacity requirements by building type and climate zone exist but are **prescriptive minimums**. Actual optimal sizing depends on:

1. **Daily load profile shape**
2. **PV generation curve**
3. **Climate zone TDV/LSC patterns**
4. **Desired compliance margin**

#### Key Sizing Parameters

| Parameter | Default | Purpose | 2025 Change |
|-----------|---------|---------|-------------|
| `BattMaxCap` | User input | Battery capacity (kWh) | - |
| `BattDegradePercent` | 15% | Capacity held back | Was 40%, now 15% |
| `BattChgEff` | ~0.95 | Charge efficiency | - |
| `BattDschgEff` | ~0.95 | Discharge efficiency | - |
| `BattMaxChgPwr` | User input | Max charge rate (kW) | - |
| `BattMaxDschgPwr` | User input | Max discharge rate (kW) | - |

**Critical Insight - Degradation:**
The 2025 change from 40% to 15% degradation allowance means:
- **More usable capacity** in compliance calculations
- Battery appears 29% larger than in 2022 (85% vs 60% available)
- **Better compliance performance** from same physical battery

#### Optimization Strategy

**For Maximum NEM3 Benefit:**

1. **Size for evening peak coverage**
   ```
   Optimal kWh ≈ Evening Peak Load (kW) × Duration (hours)

   Example: 8 kW evening load × 5 hours = 40 kWh battery
   ```

2. **Match discharge rate to load**
   ```
   BattMaxDschgPwr ≥ Peak Evening Load

   Example: 8 kW peak → 8-10 kW discharge rate
   ```

3. **Charge rate for midday window**
   ```
   BattMaxChgPwr = Battery Capacity / Available Charge Hours

   Example: 40 kWh / 5 hours = 8 kW charge rate minimum
   ```

4. **Consider "Grid Harmonization Credit"**
   - `BattGridHarmCredit` = 1 (enabled by default for 2025+)
   - Provides additional compliance credit for grid-friendly operation
   - **Cannot be disabled** in 2025+ without research mode

### Battery Location & Thermal Considerations

**WARNING from ruleset:**
> "The battery model doesn't currently include extra energy consumption for cooling the battery during charging in environments above 77°F or to keep the battery from freezing in winter if outdoors."

**Implication:** Battery sizing should account for:
- Indoor placement preferred in extreme climates
- Climate zone thermal considerations not captured by model
- Real-world performance may differ from simulation in CZ1, CZ15, CZ16

---

## Part 2: Central Heat Pump Water Heater Tank Sizing

### Load Shifting Through Thermal Storage

Central HPWHs offer **thermal energy storage** capability that complements electrical battery storage:

- **Battery** stores electrical energy (kWh)
- **HPWH Tank** stores thermal energy (BTU)
- Both shift load from high-cost to low-cost hours

### Tank Sizing for Load Shifting

#### Automatic Sizing Formula (2025 Standards)

For **Commercial Packaged Boiler** systems (HeaterType = 16), tank volume is automatically sized:

```
TankVolume (gallons) = max(50,
                           (NumDwellingUnits × 10) +
                           (NumBedrooms × 3)
                           )
```

**Example Calculations:**

| Building | DUs | Total BR | Calc | Min Tank |
|----------|-----|----------|------|----------|
| 10-unit MF (2BR avg) | 10 | 20 | (10×10)+(20×3) = 160 gal | 160 gal |
| 30-unit MF (2BR avg) | 30 | 60 | (30×10)+(60×3) = 480 gal | 480 gal |
| 50-unit MF (1.5BR avg) | 50 | 75 | (50×10)+(75×3) = 725 gal | 725 gal |

**Note:** This formula applies to **central systems only** (serving multiple dwelling units).

### Central HPWH System Configuration

#### Primary Tank Configuration

**Key Properties:**

| Property | Type | Purpose |
|----------|------|---------|
| `CHPWHTotTankVol` | Float (gal) | **Total primary tank volume** |
| `CHPWHTankCount` | Integer | Number of storage tanks |
| `CHPWHTankSetpt` | Float (°F) | Tank setpoint temperature |
| `CHPWHTankRVal` | Float (°F-ft²-h/BTU) | Tank insulation R-value |
| `CHPWHNumComp` | Integer | Number of HPWH compressors |

#### Autosizing Central HPWHs

**Critical Feature:** Central HPWH systems can be autosized

```
CHPWHAutosize = 1  → Enables autosizing of:
  - Number of compressors (CHPWHNumComp)
  - Primary tank volume (CHPWHTotTankVol)
  - Via iterative simulation
```

**Sizing Parameters:**
- `HPWHSizingReqd` = 1 triggers sizing simulation runs
- `HPWHSizeMultGuess` - Initial multiplier guess based on DUs served
- `StdHPWHSzRunMlts[1-6]` - Multipliers for each sizing iteration
- `HPWHSizeMult` - Final calculated multiplier

**Sizing Run Strategy:**
1. Initial guess based on number of dwelling units
2. Run up to 6 sizing simulations with different multipliers
3. Find minimum that meets load without excessive unmet hours
4. Apply final multiplier to determine equipment count and tank volume

### Load Shifting Capability

#### Thermal Storage Value

**Why Larger Tanks Matter:**

1. **Decouples heating from demand**
   - Heat water during low-LSC hours (midday with cheap solar)
   - Serve load during high-LSC hours (evening) from storage

2. **Enables HPWH operation during optimal hours**
   - HPWHs most efficient at warmer ambient temperatures
   - Warm ambient air = daytime = cheap solar hours under NEM3

3. **Reduces peak electrical demand**
   - Smaller, slower compressors can run longer
   - Avoids high-demand, high-LSC evening operation

#### Tank Volume vs. Load Shifting Capacity

**Thermal Storage Capacity:**
```
Stored Energy (BTU) = Tank Volume (gal) × 8.34 (lb/gal) ×
                      ΔT (°F) × 1 BTU/(lb·°F)

For 60°F temperature swing (80°F to 140°F):
  100 gallons = 50,000 BTU stored
  200 gallons = 100,000 BTU stored
  500 gallons = 250,000 BTU stored
```

**Evening Peak Offset:**
```
Typical MF unit DHW evening load: ~3,000 BTU/hr per bedroom

10-unit building (20 BR): 60,000 BTU/hr × 4 hr evening = 240,000 BTU
  → Requires ~500 gallon tank for full evening coverage
```

### Secondary Loop Configuration

**For larger systems with circulation loops:**

| Property | Purpose |
|----------|---------|
| `CHPWHLoopTankConfig` | Presence/config of secondary tank |
| `CHPWHLoopTankType` | Type of secondary tank |
| `CHPWHLoopTankVol` | Secondary tank volume |

**Secondary tanks:**
- Reduce distribution losses in large systems
- Can provide additional thermal storage
- May have own HPWH for distributed heating

### Compressor Sizing Considerations

#### Capacity vs. Efficiency Trade-off

**Small compressors + Large tank:**
- ✓ Run longer at optimal efficiency
- ✓ Better capacity modulation
- ✓ Lower peak electrical demand
- ✗ Require larger tank for load coverage

**Large compressors + Small tank:**
- ✓ Fast recovery for peak loads
- ✓ Smaller tank footprint
- ✗ More on/off cycling (efficiency loss)
- ✗ Higher peak electrical demand

**NEM3 Optimization:**
- Favor longer run times during midday solar hours
- Size tank to enable 4-6 hour daytime heating window
- Minimize evening compressor operation (high LSC hours)

### Integration with Battery Storage

**Synergistic Strategies:**

#### Combined Load Shifting
```
10am-3pm (Low LSC hours):
  - Battery charges from PV excess
  - HPWH heats water to maximum setpoint
  - Both systems "store" energy

5pm-9pm (High LSC hours):
  - Battery discharges to meet electrical loads
  - Hot water served from storage (no HPWH operation)
  - Minimal grid draw during peak
```

#### Sizing Coordination

**Rule of thumb for multifamily:**
```
Battery (kWh) ≈ 0.5 × Number of Dwelling Units
HPWH Tank (gal) ≈ (10 × DUs) + (3 × Total Bedrooms)

Example: 30-unit building, 60 BR total
  Battery: 15 kWh (can be split across multiple units)
  HPWH: 480 gallons minimum
```

---

## Part 3: Optimization Strategies for Compliance

### Strategy 1: TOU Control + Oversized Tanks

**Best for:** Medium complexity projects, predictable loads

**Configuration:**
```
Battery:
  - BatteryControl = 10 (Time of Use)
  - StandaloneChgStartHr = 11 (noon)
  - TDVSummerPkFirstHr = 17 (5pm) [varies by CZ]
  - BattMaxCap = 1.5× typical sizing
  - BattGridHarmCredit = 1 (enabled)

HPWH:
  - CHPWHTotTankVol = 1.25× formula minimum
  - CHPWHTankSetpt = 140°F (higher for more storage)
  - CHPWHAutosize = 0 (manual control)
  - Tank location: conditioned space preferred
```

**Result:**
- Battery handles electrical load shifting
- HPWH tank provides thermal load shifting
- Simple, predictable control strategy
- Good compliance performance

### Strategy 2: Advanced DR Control + Autosized HPWH

**Best for:** Complex projects, maximum compliance optimization

**Configuration:**
```
Battery:
  - BatteryControl = 101 (Advanced DR Control)
  - BattDRNumRankedDays = 20 (top 20 days)
  - StandaloneChgStartHr = 11
  - BattMaxCap = Based on peak day analysis
  - Degrades less (fewer cycles on non-peak days)

HPWH:
  - CHPWHAutosize = 1 (enable autosizing)
  - HPWHSizingReqd = 1
  - Let simulation optimize tank & compressor count
  - CHPWHTankSetpt = Maximum allowed
```

**Result:**
- Maximum LSC benefit on critical days
- Optimized HPWH sizing via simulation
- Extended battery life (selective cycling)
- Best compliance margin

### Strategy 3: Year-Round Operation

**Best for:** Consistent climate zones, stable loads

**Configuration:**
```
Battery:
  - TOUStartMonth = 1 (January)
  - TOUEndMonth = 12 (December)
  - Consistent control strategy all year
  - Size for average day, not peak

HPWH:
  - Larger tanks for seasonal variation
  - Consider backup heating for peak days
  - Optimize for average LSC benefit
```

### Strategy 4: Seasonal Optimization

**Best for:** Extreme climate zones (CZ1, CZ15, CZ16)

**Configuration:**
```
Battery:
  - TOUStartMonth = 6 (June)
  - TOUEndMonth = 9 (September)
  - Focus on summer peak season
  - Smaller battery possible

HPWH:
  - Size for worst-case (summer) loads
  - May allow auxiliary heat in winter
  - Reduces capital cost
```

---

## Compliance Impact Analysis

### Expected Compliance Improvements

**From battery storage optimization:**
- TOU Control: **5-15% improvement** in LSC margin
- Advanced DR: **10-25% improvement** in LSC margin
- Depends heavily on climate zone and load profile

**From HPWH tank upsizing:**
- 25% oversizing: **3-8% improvement** in LSC
- 50% oversizing: **5-12% improvement** in LSC
- Diminishing returns above 50% oversize

**Combined optimization:**
- **15-35% total improvement** in compliance margin
- Enables pass/fail transition in borderline projects
- Provides margin for other design trade-offs

### Cost-Benefit Considerations

#### Battery Storage

**Capital Cost:**
- ~$500-700/kWh installed (residential/small commercial)
- 15 kWh system: $7,500-10,500

**Compliance Value:**
- Can enable code compliance (priceless for project)
- May avoid need for more expensive envelope upgrades
- Provides real energy bill savings under NEM3

**ROI Factors:**
- NEM3 export rates (low) vs. retail rates (high)
- TOU utility rates (if applicable)
- Grid harmonization incentives
- Compliance alternative costs

#### HPWH Tank Oversizing

**Incremental Cost:**
- Modest: 500 gal vs 400 gal: ~$2,000-4,000
- Larger tanks needed anyway for central systems
- Insulation R-value increase: minimal cost

**Compliance Value:**
- Improved LSC performance
- Reduced peak electrical load
- Better integration with PV systems
- Lower operating costs

**ROI Factors:**
- Usually positive from energy savings alone
- Compliance benefit is "free" add-on
- May enable smaller HPWH compressors (cost offset)

---

## Implementation Checklist

### For Battery Systems

- [ ] Select control strategy (TOU vs. Advanced DR)
- [ ] Size battery for evening peak coverage
- [ ] Set charge/discharge rates appropriately
- [ ] Configure TDVSummerPkFirstHr for climate zone
- [ ] Enable BattGridHarmCredit (default for 2025+)
- [ ] Consider seasonal vs. year-round operation
- [ ] Verify minimum 80% roundtrip efficiency
- [ ] Plan for conditioned space installation (if possible)

### For Central HPWH Systems

- [ ] Calculate minimum tank volume per formula
- [ ] Consider 25-50% oversizing for load shifting
- [ ] Enable autosizing if optimization desired
- [ ] Set tank setpoint to maximum allowable
- [ ] Specify adequate tank R-value
- [ ] Plan tank location (conditioned space preferred)
- [ ] Size compressors for extended run times
- [ ] Configure secondary loop if needed (large systems)
- [ ] Verify compliance with JA12 (if applicable)

### For Combined Systems

- [ ] Coordinate battery and HPWH charging windows
- [ ] Size both for synergistic operation
- [ ] Avoid simultaneous peak loads (HPWH + battery charging)
- [ ] Model complete system in CBECC for verification
- [ ] Run sensitivity analysis on key parameters
- [ ] Verify compliance margin adequate for unknowns

---

## Key Takeaways

1. **NEM3 fundamentally changes battery value** - Evening discharge is now far more valuable than midday export

2. **TOU control is minimum viable** - Default control strategy leaves significant compliance benefit on table

3. **Advanced DR control is optimal** - For projects needing maximum compliance benefit

4. **HPWH tanks are thermal batteries** - Sizing 25-50% above minimum provides load shifting value

5. **2025 defaults favor optimization** - 15% degradation (vs 40%) and year-round TOU enable better performance

6. **Combined optimization is synergistic** - Battery + HPWH tank sizing together provides greater benefit than either alone

7. **Climate zone matters significantly** - CZ-specific TDV/LSC patterns should drive sizing decisions

8. **Autosizing is powerful** - Let simulation find optimal HPWH configuration when complexity warrants

9. **Location matters** - Conditioned space installation improves performance for both batteries and HPWH

10. **Model early and often** - CBECC simulation is essential for optimizing complex load-shifting strategies

---

## Additional Resources

### Ruleset Files Referenced
- `Rules_Default_Battery.rule` - Battery defaulting logic
- `Rules_CSE_Simulation_Battery.rule` - Battery simulation setup
- `Rules_Default_ResDHW.rule` - HPWH tank sizing logic
- `BEMBase_Res DHW.txt` - Central HPWH properties

### Key Tables
- `T24_PrescriptivePV-Battery.csv` - Prescriptive battery requirements
- `T24 2025 NEM3-LSC Factors by CZ.csv` - Hourly LSC factors
- `T24 2025 NEM3-ACC Factors by CZ.csv` - Alternative ACC factors

### Regulatory Context
- Title 24 Part 6, Section 140.10 - PV and battery requirements
- Title 24 Part 6, Section 110.3 - DHW system requirements
- JA12 - Battery system certification requirements
- Reference Appendices JA12 and NA12

---

**Document Version:** 1.0
**Last Updated:** November 20, 2025
