# CIBD25 Export Issues - January 14, 2025

## Current Status: Export Incomplete

**File:** `/Users/DavidM/Downloads/bressi_ranch_export-10.cibd25`
**Log:** `/Users/DavidM/Downloads/bressi_ranch_export-10.log`
**Result:** ❌ CBECC 2025 cannot load file (return code 6)

---

## Issue 1: MassThickness Property Quoting

### Error Messages (Lines 3-5)
```
ERROR - reading file: ResConsAssm 'Ext Wall Cons (Concrete)' property MassThickness = '8 in.' on line # 281
ERROR - reading file: ResConsAssm 'Interior Floor Cons(Concrete)' property MassThickness = '8 in.' on line # 289
ERROR - reading file: ResConsAssm 'Interior Concrete Wall' property MassThickness = '8 in.' on line # 303
```

### Current Export
```
ResConsAssm   "Ext Wall Cons (Concrete)"
   ...
   MassThickness = "8 in."     ❌ Quoted string
   ..
```

### Expected Format
```
ResConsAssm   "Ext Wall Cons (Concrete)"
   ...
   MassThickness = 8           ✅ Numeric value (inches)
   ..
```

### Root Cause
The MassThickness value `"8 in."` is being exported as a quoted string, but CBECC schema expects a numeric INTEGER field.

### Fix Required
**File:** `eco_tools/translators/cibd_xml_to_text.py`

The property needs special handling to:
1. Parse the text "8 in."
2. Extract the numeric value (8)
3. Export without quotes as integer

**OR** - Check the source to see if "8 in." should be converted to 8 during parsing.

### Priority
**Medium** - Affects residential constructions with mass walls. File can partially load but constructions are invalid.

---

## Issue 2: Missing Residential HVAC System Objects (CRITICAL)

### Error Message (Line 104)
```
Error resolving project component references: 124 not found.
   'HP-1' (12 times)
   'ResidentialFanSystem 1' (23 times)
   'ResidentialDistributionSystem 1' (41 times)
   'HP-2' (7 times)
   'HP-3' (4 times)
   'TOSHIBA RAV-SP122AT2P' (18 times)
   'MS-1 (Fan)' (18 times)
   '96 percent 250000 100-gal' (once)
```

### Error Message (Lines 6-103)
```
ERROR - unable to create component 'Component 0'. Invalid component type ''.
(repeated 104 times)
```

### Current Export
File has **only 1 HVAC object:**
```
ResDHWSys   "ResidentialDHWSystem 1"
   ..
```

**Missing objects** that are referenced but not defined:
- `HP-1`, `HP-2`, `HP-3` (ResHtPumpSys)
- `ResidentialFanSystem 1` (ResFanSys)
- `ResidentialDistributionSystem 1` (ResDistSys)
- `TOSHIBA RAV-SP122AT2P` (heat pump)
- `MS-1 (Fan)` (fan)

### Source File Structure (CIBD22X XML)

In the source file, these HVAC objects are **nested inside ResZnGrp**:

```xml
<ResZnGrp>
  <Name>L01</Name>
  ...
  <ResHtPumpSys>
    <Name>HP-1</Name>
    <Type>Air-Source Heat Pump</Type>
    ...
  </ResHtPumpSys>

  <ResFanSys>
    <Name>ResidentialFanSystem 1</Name>
    ...
  </ResFanSys>

  <ResDistSys>
    <Name>ResidentialDistributionSystem 1</Name>
    ...
  </ResDistSys>

  <ResZn>
    <Name>A1_L01</Name>
    <HVACHtPumpRef>HP-1</HVACHtPumpRef>
    <HVACFanRef>ResidentialFanSystem 1</HVACFanRef>
    <HVACDistRef>ResidentialDistributionSystem 1</HVACDistRef>
  </ResZn>
</ResZnGrp>
```

### Expected CIBD25 Structure

In CIBD25 text format, these must be **top-level catalog objects**:

```
ResZnGrp   "L01"
   ...
   ResZn   "A1_L01"
      HVACHtPumpRef = "HP-1"
      HVACFanRef = "ResidentialFanSystem 1"
      HVACDistRef = "ResidentialDistributionSystem 1"
      ..
   ..
..

# Top-level catalog objects (like materials, constructions, etc.)
ResHtPumpSys   "HP-1"
   Type = "Air-Source Heat Pump"
   ...
   ..

ResFanSys   "ResidentialFanSystem 1"
   ...
   ..

ResDistSys   "ResidentialDistributionSystem 1"
   ...
   ..
```

### Comparison with Official Sample

In the official CIBD25 sample (`MF88Unit_5Story_ELEC-CZ12.cibd25`), these appear as top-level objects:

```
Line 16145: ResHtPumpSys   "Heat Pump System - Res"
Line 16155: ResDistSys   "Air Distribution System - Res"
Line 16164: ResFanSys   "HVAC Fan - Heat Pump"
Line 16170: ResFanSys   "HVAC Fan - Furnace"
```

### Root Cause

This is **similar to the ResProj sibling issue** we fixed earlier:

- In **XML format:** HVAC system objects are nested children of `<ResZnGrp>` for structural organization
- In **Text format:** HVAC system objects must be top-level siblings (catalog objects) that zones reference

The current XML-to-text converter:
1. ✅ Correctly writes ResZnGrp and ResZn
2. ❌ Does NOT extract nested ResHtPumpSys/ResFanSys/ResDistSys to top level
3. ❌ Zones reference these objects but they don't exist

### Fix Required

**File:** `eco_tools/translators/cibd_xml_to_text.py`

Need to enhance the "deferred siblings" pattern to handle residential HVAC objects:

```python
def _is_top_level_sibling(self, child_tag: str, parent_tag: str) -> bool:
    """Check if element should be written as top-level sibling instead of nested."""
    # Elements that appear as children of Proj in XML but should be siblings in text
    if parent_tag == 'Proj':
        return child_tag in ['ResProj', 'ProjVar', 'DwellUnitType']

    # NEW: Elements that appear as children of ResZnGrp but should be top-level
    if parent_tag == 'ResZnGrp':
        return child_tag in ['ResHtPumpSys', 'ResFanSys', 'ResDistSys',
                              'ResHtgSys', 'ResClgSys', 'ResHVACSys']

    return False
```

**Challenge:** These objects need to be collected from **all ResZnGrp** elements and written once at the top level (avoiding duplicates).

### Priority
**CRITICAL** - Without these objects, CBECC cannot resolve HVAC references and file fails to load completely.

---

## Issue 3: Additional Component Type Errors

### Error Message (Lines 6-103)
```
ERROR - unable to create component 'Component 0'. Invalid component type ''.
(104 errors)
```

These are likely the HVAC objects that failed to create because:
1. They're not top-level (still nested)
2. OR they have missing/invalid Type properties

### Investigation Needed
Need to check the export file around where HVAC objects should be to see what's actually being written.

---

## Implementation Strategy

### Phase 1: Fix ResHtPumpSys/ResFanSys/ResDistSys Export (Critical)

1. **Identify all residential HVAC object types:**
   - ResHtPumpSys (heat pump systems)
   - ResFanSys (fan systems)
   - ResDistSys (distribution systems)
   - ResHtgSys (heating systems)
   - ResClgSys (cooling systems)
   - ResHVACSys (combined HVAC systems)

2. **Enhance deferred siblings pattern:**
   - Add these types to `_is_top_level_sibling()` check
   - When found inside ResZnGrp, defer to top level
   - Write after all ResZnGrp objects are processed

3. **Handle duplicates:**
   - Track system names to avoid writing duplicates
   - Multiple zones may reference the same system

### Phase 2: Fix MassThickness Property (Medium Priority)

**Option A:** Parse during XML import
- Convert "8 in." to 8 in CIBD22X importer
- Store as integer in internal representation

**Option B:** Handle during text export
- Check if MassThickness value ends with " in."
- Strip units and export numeric part only

**Recommendation:** Option A (parse during import) is cleaner

### Phase 3: Validate Complete Export

1. Export Bressi Ranch to CIBD25
2. Verify all HVAC system objects present
3. Verify MassThickness is numeric
4. Test in CBECC 2025
5. Compare with official samples

---

## Testing Plan

### Test 1: HVAC Objects Present
```bash
grep -c "^ResHtPumpSys\|^ResFanSys\|^ResDistSys" output.cibd25
```
Should return count > 0

### Test 2: HVAC Objects Referenced
```bash
grep "HVACHtPumpRef\|HVACFanRef\|HVACDistRef" output.cibd25 | head -5
```
Verify references match object names

### Test 3: MassThickness Format
```bash
grep "MassThickness" output.cibd25
```
Should show numeric values, not quoted strings

### Test 4: CBECC 2025 Load
```bash
"/Applications/CBECC 2025.app/Contents/MacOS/CBECC 2025" -nrp -b output.cibd25
```
Should return "button returned:OK"

---

## Related Issues

This is the **third structural pattern** we've discovered:

1. ✅ **Fixed:** ResProj/ProjVar - Children of Proj → Top-level siblings
2. ✅ **Fixed:** DocAuthZipCode quoting - STRING field must be quoted
3. ❌ **New:** ResHVAC objects - Children of ResZnGrp → Top-level catalog objects

### Pattern Summary

**XML Nesting → Text Sibling Pattern:**

| Object Type | XML Parent | Text Position | Status |
|-------------|------------|---------------|--------|
| ResProj | `<Proj>` | Top-level sibling | ✅ Fixed |
| ProjVar | `<Proj>` | Top-level sibling | ✅ Fixed |
| ResHtPumpSys | `<ResZnGrp>` | Top-level catalog | ❌ Not implemented |
| ResFanSys | `<ResZnGrp>` | Top-level catalog | ❌ Not implemented |
| ResDistSys | `<ResZnGrp>` | Top-level catalog | ❌ Not implemented |

---

## Next Steps

1. **Immediate:** Fix ResHtPumpSys/ResFanSys/ResDistSys export
   - Update `_is_top_level_sibling()`
   - Test with Bressi Ranch export
   - Verify CBECC 2025 can load file

2. **Follow-up:** Fix MassThickness property
   - Parse "X in." values during import
   - Export as numeric values

3. **Validation:** Test with multiple residential buildings
   - Bressi Ranch (high-rise)
   - MF88 sample buildings
   - Verify all HVAC references resolve

---

## Files to Modify

1. **eco_tools/translators/cibd_xml_to_text.py** (lines 187-204)
   - Enhance `_is_top_level_sibling()` method
   - Add ResZnGrp child handling

2. **eco_tools/translators/cibd22x/parsers/construction_parser.py** (TBD)
   - Parse MassThickness "X in." to numeric

3. **Test file:** Create `test_residential_hvac_export.py`
   - Validate HVAC objects exported
   - Validate references resolve
   - Validate CBECC 2025 loads file

---

## Success Criteria

Export is successful when:

1. ✅ All ResHtPumpSys/ResFanSys/ResDistSys objects present as top-level
2. ✅ All HVAC references resolve (124 → 0 missing references)
3. ✅ MassThickness properties are numeric (not quoted)
4. ✅ CBECC 2025 loads file with "button returned:OK"
5. ✅ No "Invalid component type" errors

---

## Documentation Updates Needed

After fixes are implemented, update:

1. **CIBD_FORMAT_DIFFERENCES_COMPREHENSIVE.md**
   - Add ResHVAC objects to sibling pattern section
   - Document MassThickness property handling

2. **CIBD_FORMAT_QUICK_REFERENCE.md**
   - Add ResHVAC objects to structural differences
   - Add to common errors section

---

## Estimated Effort

- **ResHVAC objects fix:** 2-3 hours
  - Code changes: 1 hour
  - Testing: 1-2 hours

- **MassThickness fix:** 1 hour
  - Code changes: 30 min
  - Testing: 30 min

**Total:** 3-4 hours to complete both fixes and validate

---

## Priority Assessment

**Priority: HIGH**

Without the ResHVAC objects fix, CIBD25 export is **non-functional** for residential buildings. The file cannot be loaded or simulated in CBECC 2025.

MassThickness is secondary - affects construction definitions but doesn't block file loading.
