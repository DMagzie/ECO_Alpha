# CUAC Setup Guide for CBECC Residential Models

## Overview

California Utility Allowance Calculator (CUAC) is used for affordable housing projects to determine tenant utility allowances based on energy modeling results. This guide documents the required setup for CUAC-compliant CBECC models.

---

## Prerequisites

### 1. ResZn Structure - Bedroom Count Separation

**Critical Requirement:** Each ResZn must contain dwelling units with the **same bedroom count**.

CUAC will show error: *"CUAC Error: Dwellings must have same # of bedrooms"* if a ResZn contains mixed bedroom types.

**Incorrect Structure (will fail):**
```
ResZn "Dwelling Unit_L01"
  DwellUnit "A1" → 1BR
  DwellUnit "B1" → 2BR
  DwellUnit "C1" → 3BR
```

**Correct Structure (split by bedroom type):**
```
ResZn "Dwelling Unit_L01_1BR"
  DwellUnit "A1" → 1BR only

ResZn "Dwelling Unit_L01_2BR"
  DwellUnit "B1" → 2BR only

ResZn "Dwelling Unit_L01_3BR"
  DwellUnit "C1" → 3BR only
```

**When splitting zones:**
- Split envelope elements (walls, floors, windows) proportionally by conditioned floor area
- Proportion = (UnitType SF × Count) / Total Zone SF
- DwellUnitType HVAC assignments follow automatically

---

## Required Model Properties

### 1. Project-Level: Enable CUAC Reporting

In the `Proj` block, add:
```
CUACReport = 1
```

This corresponds to the "Enable CUAC Reporting" checkbox in the CBECC GUI.

**Location in file:** After `CompOptLtg = 1` in the Proj block.

---

### 2. ResZn-Level: Affordable Housing Flag

Each residential zone must have:
```
AffordableHousing = 1
```

**Note:** The property is `AffordableHousing`, NOT `IsAffordableHousingUnit` (which is unrecognized).

**Location in file:** Within the ResZn block, before the `..` terminator.

Example:
```
ResZn   "Dwelling Unit_L01_1BR"
   CeilingHeight = 11
   AffordableHousing = 1
   ..
```

---

### 3. CUAC Block Configuration

The CUAC block contains all utility allowance calculation settings:

```
CUAC   "CUAC Inputs"
   RptOption = "Draft"
   ProjectID = 1
   UnitType = "Affordable Housing"
   AffordablePVDCSysSize = 350
   PctIndivUnitPVByBedrms[2] = 1.154
   PctIndivUnitPVByBedrms[3] = 1.681
   PctIndivUnitPVByBedrms[4] = 2.611
   PVBillingOption = "PV Offsets Monthly Use"
   G2ElecTerritory = "R"
   G2ElecTariff = "Rate EM Code B"
   ElecTariffAdj = "VNEM2"
   GasUtility = "no gas service"
   WaterRateType = "Not Paid by Tenant"
   TrashRateType = "Not Paid by Tenant"
   OwnerName = "Owner Name"
   OwnerAddress = "123 Main St"
   OwnerCity = "City"
   OwnerState = "CA"
   OwnerZIPCode = "12345"
   ContactName = "Contact Name"
   ContactPhone = "555-123-4567"
   ContactEMail = "email@example.com"
   ..
```

---

## PV Allocation Settings

### AffordablePVDCSysSize

Must equal or be less than the `DCSysSize` in the `PVArray` element.

```
PVArray   "PhotovoltaicArray 1"
   DCSysSize = 350          ← Building PV size
   ...

CUAC   "CUAC Inputs"
   AffordablePVDCSysSize = 350   ← Must match or be less
```

### PctIndivUnitPVByBedrms - Per-Unit PV Allocation

**Critical:** The sum of (% per unit × number of units) must equal **100%**.

Array indices:
- `[1]` = Studio
- `[2]` = 1 Bedroom
- `[3]` = 2 Bedroom
- `[4]` = 3 Bedroom
- `[5]` = 4 Bedroom
- `[6]` = 5 Bedroom
- `[7]` = 6 Bedroom

**Calculation Method (SF-based allocation):**

```
Per-unit % = (Unit SF) / (Total DU SF) × 100

Example for 54-unit building (48,023 total DU SF):
- 1BR (554 SF): 554 / 48,023 = 1.154% per unit
- 2BR (807 SF): 807 / 48,023 = 1.681% per unit
- 3BR (1,254 SF): 1,254 / 48,023 = 2.611% per unit

Verification:
- 16 × 1.154% = 18.46%
- 19 × 1.681% = 31.94%
- 19 × 2.611% = 49.61%
- Total: 100.01% ✓
```

---

## Utility Rate Settings

### PG&E Territory Codes
- `"R"` = Fresno area (San Joaquin Valley)
- `"M"` = Other territories

### Common Tariffs for Affordable Housing
- `"Rate EM Code B"` = Master-Metered Multifamily
- `"E1 Code H"` = Single-family / Individual meters

### Tariff Adjustments
- `"VNEM2"` = Virtual Net Energy Metering 2.0
- `"CARE"` = California Alternate Rates for Energy

### Utility Payment Options
- `"Not Paid by Tenant"` - Owner pays (excluded from allowance)
- `"Paid by Tenant"` - Included in utility allowance

---

## DwellUnitType IAQ/Ventilation Settings

The `IAQOption` property determines ventilation system:

**Central Supply Ventilation:**
```
DwellUnitType   "A1"
   IAQOption = "Central Supply"
   CentralVentSysRef = "Central DU OA"
```

**Individual ERV (e.g., Ephoca):**
```
DwellUnitType   "A1"
   IAQOption = "Individual IAQ Fans"
   IAQFanRef[1] = "Ephoca ERV (35 CFM)"
   CentralVentSysRef = "Central DU OA"   ← Ignored when IAQOption = Individual
```

**Note:** When `IAQOption = "Individual IAQ Fans"`, the `IAQFanRef` is used and `CentralVentSysRef` is ignored even if present.

---

## Common Errors and Solutions

| Error | Cause | Solution |
|-------|-------|----------|
| "No Res Zones with Affordable Housing selected" | Missing `AffordableHousing = 1` on ResZn | Add flag to each ResZn |
| "Dwellings must have same # of bedrooms" | Mixed bedroom types in one ResZn | Split ResZn by bedroom count |
| "% Tenant PV must equal 100%" | PV allocation percentages don't sum to 100 | Recalculate per-unit percentages |
| "includes unrecognized property 'IsAffordableHousingUnit'" | Wrong property name | Use `AffordableHousing = 1` |
| PV size error | CUAC PV > Building PV | Set `AffordablePVDCSysSize` ≤ `DCSysSize` |
| "Window area greater than or equal to total wall area" | Zone split incorrectly split envelope | See Zone Splitting section |
| "Error resolving project component references" | Interior walls reference old zone names | Update `Outside` references to new zone names |

---

## Scripted Zone Splitting

### Script: `split_reszone_for_cuac.py`

```bash
python split_reszone_for_cuac.py input.cibd22 output.cibd22
```

**What the script does:**
1. Parses DwellUnitTypes to determine bedroom counts
2. Identifies ResZn with mixed bedroom types
3. Creates new ResZn for each bedroom type (e.g., `_1BR`, `_2BR`, `_3BR`)
4. Splits envelope elements proportionally by SF
5. Moves DwellUnits to appropriate new zones
6. Adds `AffordableHousing = 1` to each new zone

### Critical Zone Splitting Rules

**1. Only split DWELLING envelope elements:**
- Split: `ResSlabFlr`, `ResExtWall`, `ResWin` that appear BEFORE `ResOtherZn`
- DO NOT split: Elements within or after `ResOtherZn` blocks (common areas)

**2. Maintain wall-window relationships:**
- Windows must be split with the SAME proportion as their parent wall
- Failure causes "window area greater than wall area" errors

**3. File structure (elements belong to preceding zone):**
```
ResZn "Dwelling Unit_L01"        ← Zone header
   DwellUnit "A1"                ← Dwelling units
   DwellUnit "B1"
   ResSlabFlr "Floor 1"          ← Dwelling envelope (SPLIT these)
   ResExtWall "Left Wall"        ← Dwelling envelope (SPLIT these)
   ResWin "Window 1"             ← Dwelling envelope (SPLIT these)
   ResOtherZn "Corridor_L01"     ← Common area (DO NOT SPLIT)
      ResSlabFlr "Corridor Flr"  ← Common area envelope (preserve)
      ResIntWall "Int Wall"      ← Common area envelope (preserve)
```

**4. Update interior wall references:**
- `ResIntWall` elements with `Outside = "Dwelling Unit_L01"` must be updated
- Point to the largest split zone (e.g., `Outside = "Dwelling Unit_L01_3BR"`)

### Script: `apply_cuac_settings.py`

After zone splitting, apply CUAC settings:

```bash
python apply_cuac_settings.py
```

**What it does:**
1. Adds `CUACReport = 1` to Proj block
2. Updates `PVArray DCSysSize` to specified value
3. Updates `AffordablePVDCSysSize` in CUAC block
4. Corrects `PctIndivUnitPVByBedrms` percentages

---

## Checklist for CUAC Setup

- [ ] `CUACReport = 1` in Proj block
- [ ] ResZn split by bedroom count (one bedroom type per zone)
- [ ] `AffordableHousing = 1` on each ResZn
- [ ] CUAC block with correct utility settings
- [ ] `AffordablePVDCSysSize` ≤ PVArray `DCSysSize`
- [ ] `PctIndivUnitPVByBedrms` sums to 100%
- [ ] Owner/contact information filled in
- [ ] Model loads without errors in CBECC GUI
- [ ] CUAC tab shows correct unit counts by bedroom
- [ ] Verify no "window > wall" errors after zone split

---

## Lessons Learned: Ventura & 7th Project

### Issue Timeline and Resolutions

| Date/Time | Issue | Resolution |
|-----------|-------|------------|
| Initial | Wrong property `IsAffordableHousingUnit` | Changed to `AffordableHousing = 1` |
| Initial | PV allocations summed to 135% | Recalculated based on 54 units (was using 40) |
| Initial | Missing `CUACReport = 1` | Added after `CompOptLtg = 1` in Proj |
| Initial | CUAC PV (302) > Model PV (124.5) | Updated both to 350 kW |
| 15:05:14 | "Window > wall" errors (9 walls) | Zone split script was splitting ResOtherZn walls incorrectly |
| 17:44:09 | Reference resolution errors | Interior wall `Outside` references pointed to old zone names |
| 17:46:21 | Model saved with fixes | Manual correction in CBECC GUI |
| 18:21:28 | **CUAC run completed successfully** | Monthly bills: $11.91/unit all sizes |

### Non-Blocking Warnings (Pre-existing)

These warnings appear but don't prevent CUAC analysis:

1. **Supplemental heating coil warnings** - Heat pumps in common areas (GYM, CLUB) don't have backup heating
2. **Fan motor HP warnings** - Nameplate HP (0.5) less than calculated BHP (0.648)
3. **CUAC GasFueledErrMsg** - Data retrieval warning for DwellUnitType (non-blocking)

### Key Takeaways

1. **Property names are case-sensitive** - `AffordableHousing` works, `IsAffordableHousingUnit` doesn't
2. **Zone splitting must preserve structure** - Only split dwelling envelope, not common areas
3. **Wall-window proportions must match** - Split windows with same ratio as their parent walls
4. **Interior wall references need updating** - Point to new split zone names
5. **PV settings must be consistent** - CUAC PV ≤ Model PV, allocations sum to 100%
6. **Unit counts come from DwellUnit Count property** - Not from zone count

---

## Project-Specific Settings: Ventura & 7th

| Setting | Value |
|---------|-------|
| Location | Fresno, CA (CZ 13) |
| Territory | R |
| Tariff | Rate EM Code B |
| Tariff Adjustment | VNEM2 |
| Gas | No gas service |
| Water/Trash | Not Paid by Tenant |
| PV Size | 350 kWdc |
| Total Units | 54 |
| Unit Mix | 16×1BR, 19×2BR, 19×3BR |
| Total DU Area | 48,023 SF |

**PV Allocation:**
- 1BR: 1.154% per unit (16 units = 18.46%)
- 2BR: 1.681% per unit (19 units = 31.94%)
- 3BR: 2.611% per unit (19 units = 49.61%)

### Successful CUAC Results (Ephoca + Maestros Scenario)

| Metric | 1BR | 2BR | 3BR |
|--------|-----|-----|-----|
| Monthly Electric Bill | $11.91 | $11.91 | $11.91 |
| Annual Cooling kWh | 805 | 1,094 | 1,943 |
| Annual Heating kWh | 31 | 102 | 66 |
| Annual PV Generation kWh | 5,509 | 8,025 | 12,464 |

**Analysis Status:** Valid
**Processing Time:** 35:07
**Output Files Generated:**
- CUAC Draft Submittal.pdf
- CUAC Draft Details.pdf
- CUAC.csv
- AnalysisResults.xml

---

## Output Files Reference

| File | Description |
|------|-------------|
| `*_CUAC - CUAC Draft Submittal.pdf` | Official CUAC submittal document |
| `*_CUAC - CUAC Draft Details.pdf` | Detailed breakdown by end use |
| `*_CUAC - CUAC.csv` | Raw data for analysis |
| `*_CUAC - AnalysisResults.xml` | Full simulation results |
| `*_CUAC - run/` | Simulation working files |

---

*Document created: December 2024*
*Last updated: December 2024*
*Based on CBECC 2022 residential models*
*First successful CUAC run: December 18, 2024*
