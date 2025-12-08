# CIBD25 Export Bug Analysis

**Date:** January 14, 2025
**Issue:** CBECC 2025 crashes when opening exported CIBD25 files
**Priority:** CRITICAL

---

## Problem Summary

Two distinct issues discovered with CIBD25 export:

### Issue 1: Duplicate WinType Properties (CRITICAL BUG)
**File:** `/Users/DavidM/Documents/ECO_Alpha_v7/test_output/roundtrip/Bressi_from_cibd22x.cibd25`
**Symptom:** CBECC 2025 crashes when opening file
**Root Cause:** Duplicate `WinType` properties in window elements

**Example of Invalid Output:**
```
ResWin   "O_extwall_front_1_a1_l01_window_front_1_a1_l01"
   Area = 38.75
   WinType = "ResidentialWindowType 1"
   WinType = "ResidentialWindowType 1"  ← DUPLICATE!
   ..
```

**Root Cause Identified:**
`eco_tools/translators/cibd22x/exporters/opening_exporter.py:102-107`

```python
# Window type reference (for catalog-based windows) - use format-aware tag
window_type_tag = get_window_type_ref_tag(format_type)
if opening.window_type_ref:
    self.add_text_element(open_elem, window_type_tag, opening.window_type_ref)

# Fenestration construction reference - use format-aware tag
if opening.fenestration_cons_ref:
    self.add_text_element(open_elem, window_type_tag, opening.fenestration_cons_ref)  # ← BUG!
```

**The Problem:**
Both `window_type_ref` and `fenestration_cons_ref` are written using the **SAME TAG** (`window_type_tag`), which resolves to "WinType". When both properties are present in the InternalRepresentation, they both get written to the same XML element tag, creating duplicates.

**Why Tests Didn't Catch It:**
The integration tests only verify:
1. Zone counts match after roundtrip
2. Files are created successfully
3. Files can be re-imported

They don't:
- Validate XML/text syntax
- Actually run CBECC to open the files
- Check for duplicate properties

### Issue 2: Incomplete Export from GUI
**File:** `/Users/DavidM/Downloads/bressi_ranch_export.cibd25`
**Symptom:** File only contains 31 lines (just Proj metadata, no Bldg element)
**Possible Causes:**
1. GUI export error handling silently failing
2. InternalRepresentation not fully populated
3. Export path issue in Streamlit

**File Contents:**
```
RulesetFilename   "T24_2025.bin"

Proj   "Bressi Ranch Apartments"
   BldgEngyModelVersion = 17
   City = "Carlsbad"
   ...
   ZipCode = 92009
   ..

```

No `Bldg`, `ResZnGrp`, `ResZn`, or other geometry elements exported.

---

## Fix for Issue 1: Duplicate WinType

### Problem Code
`eco_tools/translators/cibd22x/exporters/opening_exporter.py:100-107`

### Solution
Use **different tags** for `window_type_ref` vs `fenestration_cons_ref`, or use **conditional logic** to prefer one over the other.

**Option A: Conditional Logic (Recommended)**
```python
# Window type reference (for catalog-based windows) - use format-aware tag
window_type_tag = get_window_type_ref_tag(format_type)

# Prefer window_type_ref if available, otherwise use fenestration_cons_ref
if opening.window_type_ref:
    self.add_text_element(open_elem, window_type_tag, opening.window_type_ref)
elif opening.fenestration_cons_ref:
    self.add_text_element(open_elem, window_type_tag, opening.fenestration_cons_ref)
```

**Rationale:**
- `window_type_ref` is the primary window type reference (from catalog)
- `fenestration_cons_ref` is a fallback for construction-based windows
- Only one should be used at a time

**Option B: Separate Tags**
```python
# Window type reference (for catalog-based windows)
window_type_tag = get_window_type_ref_tag(format_type)
if opening.window_type_ref:
    self.add_text_element(open_elem, window_type_tag, opening.window_type_ref)

# Fenestration construction reference (use different tag)
if opening.fenestration_cons_ref:
    self.add_text_element(open_elem, 'FenCons', opening.fenestration_cons_ref)
```

**Recommended:** Option A, as CBECC format likely only supports one window type reference per window.

---

## Fix for Issue 2: Incomplete GUI Export

**Investigation Needed:**
1. Check GUI export code path
2. Verify InternalRepresentation is fully populated before export
3. Add error handling and logging to GUI export
4. Test with smaller sample file first

**Likely Location:** `gui/pages/*.py` or `explorer_gui/import_export.py`

---

## Testing Plan

### 1. Fix Duplicate WinType Bug
1. Apply Option A fix to `opening_exporter.py`
2. Re-run integration tests
3. Export Bressi Ranch to CIBD25
4. Manually inspect for duplicates: `grep -A2 "WinType" file.cibd25 | grep "WinType" | sort | uniq -d`
5. Try opening in CBECC 2025

### 2. Debug Incomplete Export
1. Test export with smaller file (Del Amo, small office)
2. Add logging to GUI export path
3. Check for exceptions in Streamlit console
4. Verify InternalRepresentation has zones before export

### 3. Comprehensive Validation
1. Create validation script to check for:
   - Duplicate properties
   - Missing required elements
   - Syntax errors
2. Add to integration tests
3. Run against all 13 CIBD22X samples

---

## Impact Assessment

### Current State
- ❌ CIBD25 export produces invalid files
- ❌ CBECC 2025 crashes on open
- ✅ Integration tests pass (false positive)
- ⚠️ GUI export incomplete

### After Fix
- ✅ Valid CIBD25 syntax
- ✅ CBECC 2025 can open files
- ✅ Tests enhanced to catch syntax issues
- ✅ GUI export working

### Affected Features
- CIBD25 export (broken)
- CIBD22X export (may have same bug)
- Cross-format conversion (broken for CIBD25)
- GUI export functionality (incomplete)

---

## Related Files

**Source of Bug:**
- `eco_tools/translators/cibd22x/exporters/opening_exporter.py:102-107`

**May Need Updates:**
- `eco_tools/translators/cibd25/exporter.py` (uses CIBD22X exporter)
- `eco_tools/translators/cibd22/exporter.py` (may have same issue)
- `gui/pages/*.py` (GUI export path)
- `explorer_gui/import_export.py` (GUI export handlers)

**Test Files:**
- `tests/integration/test_format_roundtrips.py` (add syntax validation)
- Create: `tests/integration/test_cibd_syntax_validation.py`

---

## Priority Actions

1. **CRITICAL** - Fix duplicate WinType bug (15 minutes)
2. **HIGH** - Debug GUI export issue (30 minutes)
3. **HIGH** - Test fix with CBECC 2025 (10 minutes)
4. **MEDIUM** - Add syntax validation to tests (30 minutes)
5. **MEDIUM** - Check CIBD22 exporter for same bug (15 minutes)

**Estimated Total Effort:** 2 hours to fix and validate

---

**Status:** ANALYSIS COMPLETE - READY TO FIX
**Next Step:** Apply Option A fix to opening_exporter.py
