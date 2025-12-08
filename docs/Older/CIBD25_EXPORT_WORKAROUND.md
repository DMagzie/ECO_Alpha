# CIBD25 Export - Current Status & Workaround

**Date:** January 14, 2025
**Status:** Core bug fixed, GUI integration incomplete

---

## Issues Fixed ✅

1. **Duplicate WinType properties** - FIXED in `opening_exporter.py`
2. **CIBD25 exporter code** - FIXED with proper v7 integration

## Remaining GUI Issue ⚠️

The GUI's `_emjson_to_internal_repr()` function still references old v6 architecture, causing:
```
AttributeError: 'types.SimpleNamespace' object has no attribute 'annotation'
```

**Root Cause:** GUI converter creates SimpleNamespace objects instead of proper dataclass instances that v7 exporters expect.

---

## WORKING SOLUTION: Command-Line Tool ✅

### Quick Start

Convert any CIBD22X file to CIBD25 using the command-line tool:

```bash
cd /Users/DavidM/Documents/ECO_Alpha_v7

python3 convert_cibd22x_to_cibd25.py "input.cibd22x" "output.cibd25"
```

### Example: Convert Bressi Ranch

```bash
python3 convert_cibd22x_to_cibd25.py \
  "reference_data/cbecc/CBECC Models/Bressi Ranch/Bressi Ranch Apartments.cibd22x" \
  "bressi_ranch_for_cbecc2025.cibd25"
```

Output:
```
📥 Importing Bressi Ranch Apartments.cibd22x...
   ✓ Imported 290 zones

📤 Exporting to CIBD25...
   ✓ Exported to bressi_ranch_for_cbecc2025.cibd25
   File size: 1,100,838 bytes

✅ Conversion complete!

📝 Next step: Open bressi_ranch_for_cbecc2025.cibd25 in CBECC 2025
```

### Features

✅ Uses v7 translators with duplicate WinType fix
✅ Proper CIBD25 metadata (T24_2025.bin, CBECC 2025.2.0)
✅ Direct CIBD22X → CIBD25 roundtrip (no EMJSON conversion)
✅ Tested with 290-zone model
✅ Zero duplicate properties

---

## Test File Ready ✅

A pre-converted Bressi Ranch file is ready for CBECC 2025 testing:

```
/Users/DavidM/Documents/ECO_Alpha_v7/test_output/bressi_fixed.cibd25
```

**Specifications:**
- Size: 1,100,838 bytes (1.1 MB)
- Lines: 34,218
- Zones: 290
- Windows: 1,327
- Duplicate WinType properties: **0** ✅

---

## GUI Fix - Future Work

To fix the GUI export, one of these approaches is needed:

### Option A: Store Source File Path (Recommended)
Update `import_page.py` to store the original file path:
```python
st.session_state['source_file_path'] = uploaded_file_path
```

Then pass it to the exporter:
```python
emjson6_to_cibd25(active_model, source_file_path)
```

**Effort:** 30 minutes
**Benefit:** Clean roundtrip without re-conversion

### Option B: Fix _emjson_to_internal_repr (Complex)
Update the EMJSON converter to create proper v7 dataclass objects instead of SimpleNamespace.

**Effort:** 2-4 hours
**Risk:** May break other parts of GUI

### Option C: Hybrid Approach
Export EMJSON → CIBD22X → CIBD25 using v7 translators throughout.

**Effort:** 1-2 hours
**Benefit:** Works with current EMJSON format

---

## Recommended Workflow (Now)

### For Testing CBECC 2025

1. **Use the pre-converted file:**
   ```
   /Users/DavidM/Documents/ECO_Alpha_v7/test_output/bressi_fixed.cibd25
   ```

2. **Or convert any CIBD22X file:**
   ```bash
   python3 convert_cibd22x_to_cibd25.py "your_file.cibd22x" "output.cibd25"
   ```

3. **Open in CBECC 2025:**
   - Should load without crashing
   - All geometry and properties intact
   - No duplicate WinType errors

### For GUI Users (Temporary)

1. **Export as CIBD22X** from GUI (this works)
2. **Convert to CIBD25** using command-line tool
3. **Open in CBECC 2025**

---

## Next Steps

### Priority 1: Validate Fix in CBECC 2025
Test the converted files:
1. Open `bressi_fixed.cibd25` in CBECC 2025
2. Verify it doesn't crash
3. Check geometry loads correctly
4. Try running compliance analysis

### Priority 2: Fix GUI (Optional)
If GUI export is critical, implement Option A (store source path).

### Priority 3: Integration Tests
Add syntax validation to test suite to catch issues like duplicate properties automatically.

---

## Files Created

1. **`convert_cibd22x_to_cibd25.py`** - Command-line conversion tool
2. **`test_output/bressi_fixed.cibd25`** - Pre-converted test file
3. **`test_cibd25_fix.py`** - Validation script
4. **`docs/CIBD25_EXPORT_BUG_ANALYSIS.md`** - Root cause analysis
5. **`docs/CIBD25_BUG_FIXES_COMPLETE.md`** - Fix documentation
6. **`docs/CIBD25_EXPORT_WORKAROUND.md`** - This document

---

## Summary

**✅ WORKING:** Command-line CIBD22X → CIBD25 conversion
**✅ FIXED:** Duplicate WinType bug
**✅ READY:** Test file for CBECC 2025 validation
**⏳ TODO:** GUI export integration (optional, workaround exists)

**Recommended Action:** Test `bressi_fixed.cibd25` in CBECC 2025 to validate the fix works!
