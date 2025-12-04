# CIBD25 Element Ordering & Conversion Lessons Learned

**Version**: V7 Final Translator
**Last Updated**: 2025-12-03
**Status**: Production Ready

This document captures critical lessons about CIBD22X to CIBD25 text format conversion.
CBECC 2025 is sensitive to element order and property compatibility. Incorrect ordering or
deprecated properties can cause validation failures, GUI display issues, or application stalls
even when command-line validation succeeds.

---

## Table of Contents

1. [Element Order Summary](#element-order-summary)
2. [Critical Ordering Rules](#critical-ordering-rules)
3. [Deprecated Properties](#deprecated-properties-cibd22x--cibd25)
4. [Required Property Defaults](#required-property-defaults)
5. [Elements to Skip](#elements-to-skip)
6. [Element Priority Table](#element-priority-table)
7. [Debugging Tips](#debugging-tips)
8. [Fix History](#fix-history)

---

## Element Order Summary

The CIBD25 text format requires elements to be written in a specific order:

```
1.  RulesetFilename          - Must be first
2.  Proj                     - Project definition
3.  ProjVar                  - Project variants
4.  ResProj                  - Residential project settings
5.  SchDay                   - Schedule definitions
6.  Construction catalog     - FenCons, ConsAssm, DrCons, Mat, ResConsAssm, ResMat, ResWinType
7.  HVAC components          - ResHtgSys, ResClgSys, ResHtPumpSys, ResFanSys,
                               ResCentralVentSys, ResDistSys, ResIAQFan
8.  Bldg                     - Building with hierarchy (ResZnGrp → ResZn → DwellUnit → geometry)
9.  ResAttic, PVArray        - After building hierarchy
10. DwellUnitType            - Type definitions (MUST come AFTER all DwellUnit instances)
11. ResDHWSys, ResWtrHtr     - HVAC systems (AFTER DwellUnitType)
12. Report objects           - ResDHWSysRpt, DwellUnitRpt, etc. (always last)
```

---

## Critical Ordering Rules

### Rule 1: DwellUnitType AFTER DwellUnit Instances (Fix #26)

**Problem**: DwellUnitType definitions were written before building structure.

**Root Cause**: XML source has DwellUnitType at root level before Bldg.

**Solution**: Defer root-level DwellUnitType to be written after building hierarchy.

**Symptom if violated**: File validates but GUI shows "No DwellUnitType assigned".

---

### Rule 2: HVAC Systems AFTER DwellUnitType (Fix #34)

**Problem**: ResHVACSys, ResDHWSys, ResWtrHtr appeared before DwellUnitType.

**Root Cause**: These elements are at root level in XML and were written immediately.

**Solution**: Defer root-level ResHVACSys, ResDHWSys, ResWtrHtr with priority > DwellUnitType.

**Reference Order**: Bldg → DwellUnitType → ResWtrHtr → ResHVACSys → ResDHWSys

**Symptom if violated**: File validates but DwellUnitType not recognized in GUI.

---

### Rule 3: HVAC Components BEFORE Bldg (Fix #42)

**Observation**: In working files, HVAC components appear early in the file, before Bldg.

**Component Order** (based on working reference files):
```
ResHtgSys → ResClgSys → ResHtPumpSys → ResFanSys → ResCentralVentSys → ResDistSys → ResIAQFan
```

**Note**: These are HVAC *components* (equipment definitions), distinct from HVAC *systems*
(ResHVACSys, ResDHWSys) which come at the end after DwellUnitType.

---

### Rule 4: Bldg Hierarchy Must Be Contiguous

**Problem**: Breaking up the Bldg hierarchy with other elements causes GUI issues.

**Solution**: Write elements in proper parent-child order:
- ResZnGrp immediately after Bldg
- ResZn immediately after ResZnGrp
- DwellUnit/ResOtherZn within their ResZn
- Geometry elements (ResExtWall, ResWin, etc.) within their zone

**Implementation**: Use `_is_immediate_sibling()` to control which extracted elements are
written immediately vs. deferred.

---

### Rule 5: ResCentralVentSys Must Have Type Property (Fix #43)

**Problem**: Files with ResCentralVentSys but missing Type property cause GUI to stall.

**Root Cause**: CBECC GUI requires Type property on ResCentralVentSys elements.

**Solution**: If ResCentralVentSys element lacks Type property, add default:
```
Type = "Balanced"
```

**Symptom if violated**: File validates OK but GUI stalls/hangs when opening.

---

### Rule 6: No END_OF_FILE Marker (Fix #40)

**Problem**: Working CBECC files do not have an END_OF_FILE marker.

**Solution**: Do not write END_OF_FILE marker at end of converted files.

---

### Rule 7: Version Markers for 2025 (Fix #39)

**Problem**: Converted files retained 2022 version markers from source CIBD22X files.

**Solution**: Update properties in Proj element:
- `RunTitle` = "Title 24 2025 Compliance"
- `SoftwareVersion` = "CBECC 2025.2.0 (converted from CIBD22X)"

---

## Deprecated Properties (CIBD22X → CIBD25)

These properties exist in CIBD22X but are NOT valid in CIBD25 and **must be filtered**
during conversion. Unrecognized properties can cause:
- GUI display failures (elements not showing correctly)
- Application stalls/hangs
- Cascading errors that break element associations

| Property | Element Types | Effect if Present | Fix |
|----------|---------------|-------------------|-----|
| `VentSpcFunc` | ResZn, ResOtherZn | DwellUnitType not recognized, GUI shows "No DwellUnitType assigned" | #41 |
| `MassThickness` | ResConsAssm | Validation warnings | Pre-existing |
| `PVBattSizeBldgType` | ResZn, ResOtherZn, DwellUnit | **GUI stalls/hangs on file open** | #44 |
| `BattReq_PartOfLargeTenantArea` | ResZn, ResOtherZn, DwellUnit | **GUI stalls/hangs on file open** | #44 |

### Key Insight

**Command-line validation success does NOT guarantee GUI functionality.** A file can return
`button returned:OK` from CBECC command-line validation but still:
- Stall the GUI when opening
- Show empty folders (e.g., DwellingUnitTypes)
- Fail to display element associations

Always test converted files in the actual CBECC GUI.

---

## Required Property Defaults

Some elements require specific properties that may be missing from CIBD22X source files:

| Element | Property | Default Value | Notes |
|---------|----------|---------------|-------|
| ResCentralVentSys | Type | "Balanced" | Required or GUI stalls (Fix #43) |
| ResZn | Type | "Conditioned" | Default if missing |
| ResOtherZn | Type | "Unconditioned" | Default if missing |

---

## Elements to Skip

These elements should be completely skipped during conversion:

| Element | Reason | Fix |
|---------|--------|-----|
| `Batt` | Battery storage not properly supported in CIBD25 text format; causes issues | #43 |

---

## Element Priority Table

Priority values used by the deferred sibling sorting system:

| Priority | Elements | Notes |
|----------|----------|-------|
| 80 | ResHtgSys, ResClgSys | Heating/cooling system definitions |
| 81 | ResHtPumpSys | Heat pump systems |
| 82 | ResFanSys | Fan systems |
| 83 | ResCentralVentSys | Central ventilation systems |
| 84 | ResDistSys | Distribution systems |
| 85 | ResIAQFan, ResLpTankHtr | IAQ fans and tank heaters |
| 90 | Other HVAC components | Catch-all for HVAC |
| 100 | Bldg | Building structure |
| 200 | AirSys, FluidSys, VRFSys, ZnSys | Commercial HVAC structure |
| 300 | SchDay, SchWeek, Sch, ResProj, ProjVar | Schedules and variants |
| 500 | ResConsAssm, ResMat, ResWinType, ConsAssm, Mat, FenCons, DrCons | Construction catalog |
| 600 | Lum, WtrHtr, Chiller, Boiler, Pump, ThrmlEngyStor, PVArray | Equipment catalog |
| 700 | HERSCool, HERSHeat, HERSHtPump, etc. | HERS/Compliance |
| 900 | DwellUnitType | Type definitions (after instances) |
| 950 | ResHVACSys, ResDHWSys, ResWtrHtr | HVAC systems (after DwellUnitType) |
| 1000 | ResDHWSysRpt, DwellUnitRpt, etc. | Report objects (always last) |

---

## Root-Level Elements to Defer

These elements, when at XML root level, must be deferred for proper ordering:

```python
DEFER_ROOT_ELEMENTS = {
    'DwellUnitType',    # Type definitions (must come after DwellUnit instances)
    'ResHVACSys',       # HVAC systems (must come after DwellUnitType)
    'ResDHWSys',        # DHW systems (must come after DwellUnitType)
    'ResWtrHtr',        # Water heaters (must come after DwellUnitType)
}
```

---

## Debugging Tips

### 1. Compare with working files
```bash
# Hex comparison
xxd converted.cibd25 > converted.hex
xxd working.cibd25 > working.hex
diff converted.hex working.hex

# Element order comparison
grep -o "^[A-Z][a-zA-Z]*" file.cibd25 | uniq
```

### 2. Check for deprecated properties
```bash
# Check for known problematic properties
grep -c "VentSpcFunc\|PVBattSizeBldgType\|BattReq_PartOfLargeTenantArea" file.cibd25
```

### 3. Verify element counts
```bash
# Count key elements
for elem in DwellUnit DwellUnitType ResZnGrp ResHVACSys ResDHWSys PVArray; do
    echo "$elem: $(grep -c "^$elem " file.cibd25)"
done
```

### 4. Check line endings
```bash
file file.cibd25  # Should show "ASCII text" (LF) not "ASCII text, with CRLF line terminators"
```

### 5. Validate before GUI testing
```bash
"/Applications/CBECC 2025.app/Contents/MacOS/CBECC 2025" -nrcc -b file.cibd25
# Should return: button returned:OK
```

---

## Related Files

- `cibd_xml_to_text.py` - Main converter (V7 Final)
- `CIBD_CONVERSION_FIXES.md` - Detailed fix documentation
- `CIBD_TRANSLATOR_README.md` - Translator overview

---

## Fix History

| Fix | Date | Issue | Solution |
|-----|------|-------|----------|
| #44 | 2025-12-03 | `PVBattSizeBldgType`, `BattReq_PartOfLargeTenantArea` cause GUI stall | Filter deprecated battery properties |
| #43 | 2025-12-02 | ResCentralVentSys missing Type causes stall; Batt element issues | Add Type="Balanced" default; skip Batt element |
| #42 | 2025-12-02 | HVAC component ordering incorrect | Specific sub-priorities for HVAC components |
| #41 | 2025-12-02 | `VentSpcFunc` prevents DwellUnitType recognition | Filter deprecated property |
| #40 | 2025-12-02 | END_OF_FILE marker not in working files | Remove END_OF_FILE marker |
| #39 | 2025-12-02 | 2022 version markers in converted files | Update to 2025 version markers |
| #34 | 2025-12-01 | HVAC systems before DwellUnitType | Defer HVAC systems with higher priority |
| #26 | 2025-12-01 | DwellUnitType before DwellUnit instances | Defer DwellUnitType to after building hierarchy |

---

## Test Models (V7 Verified)

The following models have been successfully converted and tested in CBECC 2025 GUI:

| Model | DwellUnits | DwellUnitTypes | Status |
|-------|-----------|----------------|--------|
| Freedom_Circle_A | 157 | 47 | ✓ Opens, displays correctly |
| Freedom_Circle_B | 182 | 60 | ✓ Opens, displays correctly |
| Euclid_A | 82 | 7 | ✓ Opens, displays correctly |
| Euclid_B | 73 | 10 | ✓ Opens, displays correctly |
| Euclid_C | 13 | 6 | ✓ Opens, displays correctly |
| Del_Amo_Circle | 88 | 22 | ✓ Opens, displays correctly |
| Mainplace_Mall | 124 | 36 | ✓ Opens, displays correctly |

---

*Document maintained as part of ECO_Alpha_v7 CIBD translator development.*
