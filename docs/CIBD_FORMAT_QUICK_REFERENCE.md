# CIBD Format Quick Reference
## Common Differences Between CIBD22, CIBD22X, and CIBD25

**Last Updated:** January 14, 2025

---

## Format Selection Guide

| If you have... | Format | Can Import? | Can Export? |
|----------------|--------|-------------|-------------|
| `.cibd22x` file | CIBD22X XML | ✅ Yes | ✅ Yes |
| `.cibd22` file | CIBD22 Text | ⚠️ Partial | ❌ No |
| `.cibd25` file | CIBD25 Text | ⚠️ Untested | ✅ Yes |

**Recommendation:** Use CIBD22X as your working format, export to CIBD25 for CBECC 2025 simulation.

---

## Critical Structural Differences

### 1. ResProj Position

**CIBD22X (XML):**
```xml
<Proj>
  <Name>Building</Name>
  <ResProj>              <!-- Nested INSIDE Proj -->
    <Name>Residential</Name>
  </ResProj>
</Proj>
```

**CIBD22/CIBD25 (Text):**
```
Proj   "Building"
   ..

ResProj   "Residential"   # Top-level SIBLING (NOT nested)
   ..
```

### 2. ProjVar Position (2025 Only)

**CIBD25:**
```
Proj   "Building"
   ..

ProjVar   "Building - ProjVar"   # Top-level sibling
   ExcptCondNoClgSys = "No"
   ExcptCondRtdCap = "No"
   ..
```

**CIBD22:**
```
Proj   "Building"
   ExcptCondNoClgSys = "No"      # Properties inside Proj
   ExcptCondRtdCap = "No"
   ..
```

---

## Property Quoting Rules

### Always Quote (STRING fields):
```
DocAuthZipCode = "92868"
City = "Sacramento"
CliZn = "ClimateZone12"
StAddress = "123 Main St"
```

### Never Quote (INTEGER/FLOAT fields):
```
ZipCode = 92009
BldgEngyModelVersion = 17
UFactor = 0.34
SHGC = 0.22
Vol = 42220.3
```

**Critical:** `DocAuthZipCode` (quoted) vs `ZipCode` (not quoted) - different field types!

---

## Array References

**Text Format:**
```
MatRef[1] = "Concrete - 140 lb/ft3 - 6 in."
MatRef[2] = "Stucco - 7/8 in."
ApplRefrigZone[1] = "Zone Name"
```

**XML Format:**
```xml
<MatRef>Concrete - 140 lb/ft3 - 6 in.</MatRef>
<MatRef>Stucco - 7/8 in.</MatRef>
<ApplRefrigZone>Zone Name</ApplRefrigZone>
```

---

## Schema Version Differences

### Ruleset Files

| Format | Ruleset | Title 24 Version |
|--------|---------|------------------|
| CIBD22/CIBD22X | `T24N_2022.bin` | 2022 |
| CIBD25 | `T24_2025.bin` | 2025 |

### Moved Properties (2022 → 2025)

| Property | CIBD22 Location | CIBD25 Location |
|----------|----------------|-----------------|
| `ExcptCondNoClgSys` | `Proj` | `ProjVar` |
| `ExcptCondRtdCap` | `Proj` | `ProjVar` |
| `ExcptCondNarrative` | `Proj` | `ProjVar` |

### Removed Properties (2022 → 2025)

| Property | Present in 2022? | Present in 2025? |
|----------|------------------|------------------|
| `OccSensorCtrl` | ✅ Yes | ❌ No |
| `StdDesignIAQType[1]` (in ResProj) | ✅ Yes | ❌ No |
| `StdDesignIAQFanPwr[1]` (in ResProj) | ✅ Yes | ❌ No |

---

## Common Errors

### Error: "Expected Quote" at line X
**Cause:** STRING field exported without quotes
**Fix:** Add property to `_requires_quotes()` list in `cibd_xml_to_text.py`
**Example:** `DocAuthZipCode = "92868"` (must be quoted)

### Error: "Expected Integer" at line X
**Cause:** INTEGER field exported with quotes
**Fix:** Remove property from `_requires_quotes()` list
**Example:** `ZipCode = 92009` (must NOT be quoted)

### Error: Missing ResProj in export
**Cause:** ResProj nested inside Proj instead of top-level sibling
**Fix:** Already fixed in `_is_top_level_sibling()` method
**Status:** ✅ Working as of Jan 14, 2025

### Error: ResProj empty after EMJSON roundtrip
**Cause:** proj_metadata not restored from EMJSON
**Fix:** Already fixed in `gui/translators.py:1034`
**Status:** ✅ Working as of Jan 14, 2025

---

## File Structure Comparison

### CIBD22X (XML)
```xml
<?xml version="1.0"?>
<SDDXML>
  <RulesetFilename file="T24N_2022.bin"/>
  <Proj>
    <Name>Building</Name>
    <ZipCode>92009</ZipCode>
    <Bldg>
      <Name>Building 1</Name>
    </Bldg>
  </Proj>
</SDDXML>
```

### CIBD22/CIBD25 (Text)
```
RulesetFilename   "T24N_2022.bin"

Proj   "Building"
   ZipCode = 92009
   ..

Bldg   "Building 1"
   ..
```

---

## Testing Commands

### Export CIBD25 from CIBD22X
```bash
python3 eco_tools/translators/cibd25.py \
  "reference_data/cbecc/CBECC Models/Bressi Ranch/Bressi Ranch Apartments.cibd22x" \
  "test_output/bressi_export.cibd25"
```

### Validate with CBECC 2025
```bash
"/Applications/CBECC 2025.app/Contents/MacOS/CBECC 2025" \
  -nrp -b "test_output/bressi_export.cibd25"
```

### Check file structure
```bash
head -50 test_output/bressi_export.cibd25
```

---

## Related Documentation

- **Comprehensive Analysis:** `docs/CIBD_FORMAT_DIFFERENCES_COMPREHENSIVE.md`
- **CIBD25 ZipCode Fix:** `docs/CIBD25_ZIPCODE_FIX_COMPLETE.md`
- **v7 Architecture:** `docs/V7_INTEGRATION_COMPLETE.md`

---

## Key Takeaways

1. **CIBD22 and CIBD25 use identical text structure** - Only schema differs
2. **ResProj/ProjVar must be top-level siblings** in text format
3. **Property quoting depends on schema field type** - Not value appearance
4. **Our tool is CIBD22X-primary** - Export to CIBD25 works, import needs testing
5. **Schema differences between 2022 and 2025** - Some properties moved/removed

---

## Quick Decision Tree

**Starting with CIBD22X?**
→ ✅ You're all set! This is our primary format.

**Starting with CIBD25?**
→ ⚠️ Import untested. Consider opening in CBECC 2025 and saving as CIBD22X first.

**Starting with CIBD22?**
→ ⚠️ Limited import support. Open in CBECC 2022 and save as CIBD22X.

**Need to simulate in CBECC 2025?**
→ ✅ Export to CIBD25 format (fully working)

**Need to preserve residential compliance data?**
→ ✅ ResProj/ProjVar roundtrip working through EMJSON

**Seeing property quoting errors?**
→ Check if property is STRING (quote) or INTEGER (no quote) in schema
