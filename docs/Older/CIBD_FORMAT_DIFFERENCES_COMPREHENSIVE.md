# CIBD Format Differences: Comprehensive Analysis
## CIBD22, CIBD22X, and CIBD25 Format Comparison

**Date:** January 14, 2025
**Purpose:** Document all structural, formatting, and schema differences between CBECC formats to enable reliable import/export across all three formats

---

## Executive Summary

Our ECO Tools translator was built around **CIBD22X** (XML format). This document analyzes the differences needed to reliably import and export:

- **CIBD22** - Title 24 2022 text-based format
- **CIBD22X** - Title 24 2022 XML format
- **CIBD25** - Title 24 2025 text-based format

### Key Finding: Three Critical Differences

1. **Structural:** XML nesting vs text sibling relationships (ResProj, ProjVar)
2. **Schema:** Property name and value changes between 2022 and 2025 compliance rules
3. **Formatting:** Property quoting rules differ by schema field type (STRING vs INTEGER)

---

## Format Overview

### CIBD22X (XML Format)
- **File Extension:** `.cibd22x`
- **Structure:** XML with namespace `<SDDXML>`
- **Compliance:** Title 24 2022
- **Ruleset:** `T24N_2022.bin`
- **Nesting:** Elements can be nested children in XML
- **Our Status:** ✅ Fully supported (primary format)

### CIBD22 (Text Format - 2022)
- **File Extension:** `.cibd22`
- **Structure:** Text-based with indentation
- **Compliance:** Title 24 2022
- **Ruleset:** `T24N_2022.bin`
- **Nesting:** Top-level siblings with references
- **Our Status:** ⚠️ Import only (no exporter yet)

### CIBD25 (Text Format - 2025)
- **File Extension:** `.cibd25`
- **Structure:** Text-based with indentation (same as CIBD22)
- **Compliance:** Title 24 2025
- **Ruleset:** `T24_2025.bin`
- **Nesting:** Top-level siblings with references
- **Our Status:** ✅ Export working (import needs testing)

---

## 1. Structural Differences

### 1.1 XML vs Text Format Structure

#### CIBD22X (XML):
```xml
<SDDXML>
  <RulesetFilename file="T24N_2022.bin"/>
  <Proj>
    <Name>Building Name</Name>
    <ZipCode>92009</ZipCode>
    <ResProj>                          <!-- Nested inside Proj -->
      <Name>Residential Project</Name>
      <StdDesignFuel_HVAC>Electricity</StdDesignFuel_HVAC>
    </ResProj>
    <Bldg>
      <Name>Building 1</Name>
    </Bldg>
  </Proj>
</SDDXML>
```

#### CIBD22/CIBD25 (Text):
```
RulesetFilename   "T24N_2022.bin"

Proj   "Building Name"
   ZipCode = 92009
   ..

ResProj   "Residential Project"         # Top-level sibling (NOT nested)
   StdDesignFuel_HVAC = "Electricity"
   ..

Bldg   "Building 1"                     # Also top-level sibling
   ..
```

### 1.2 Top-Level Sibling Pattern

**Critical Discovery:** Certain elements that are XML children of `<Proj>` must be written as **top-level siblings** in text format.

#### Elements Requiring Sibling Treatment:

| Element | Purpose | Appears In | XML Parent | Text Position |
|---------|---------|------------|------------|---------------|
| `ResProj` | Residential compliance data | Residential buildings | `<Proj>` | Top-level sibling |
| `ProjVar` | Exception condition variants | Commercial buildings (2025) | `<Proj>` | Top-level sibling |
| `DwellUnitType` | Dwelling unit type definitions | Residential buildings | (varies) | Top-level sibling |

**Implementation:** Our `cibd_xml_to_text.py` converter now implements the "deferred siblings" pattern:

```python
def _is_top_level_sibling(self, child_tag: str, parent_tag: str) -> bool:
    """Check if element should be written as top-level sibling instead of nested."""
    if parent_tag == 'Proj':
        return child_tag in ['ResProj', 'ProjVar', 'DwellUnitType']
    return False
```

**Status:** ✅ Fixed in eco_tools/translators/cibd_xml_to_text.py (lines 187-204)

---

## 2. Schema Differences (2022 vs 2025)

### 2.1 Compliance Properties Moved to ProjVar (2025 Only)

In **CIBD22**, exception conditions are properties of `Proj`:

```
Proj   "Building Name"
   ExcptCondNoClgSys = "No"
   ExcptCondRtdCap = "No"
   ExcptCondNarrative = "No"
   ..
```

In **CIBD25**, these moved to a separate `ProjVar` object:

```
Proj   "Building Name"
   (exception properties removed)
   ..

ProjVar   "Building Name - ProjVar"     # Top-level sibling
   ExcptCondNoClgSys = "No"
   ExcptCondRtdCap = "No"
   ExcptCondNarrative = "No"
   ..
```

**Impact:** CIBD25 files MUST have ProjVar as top-level sibling for commercial buildings.

### 2.2 ResProj Property Differences

Comparing residential files, ResProj gained/lost properties between 2022 and 2025:

#### CIBD22 ResProj (2022):
```
ResProj   "Name"
   StdDesignFuel_Ckg = "Proposed"
   StdDesignFuel_Dry = "Proposed"
   StdDesignFuel_HVAC = "Electricity"
   StdDesignFuel_DHW = "Proposed"
   StdDesignCompactDistrib = 0
   StdDesignDrnWtrHtRecov = 0
   StdDesignHPWHLocOverride = 0
   StdDesignWinPerfAdjust = 0
   StdDesignIAQType[1] = "Bal w/ Ht Recov"  # 2022 only
   StdDesignIAQFanPwr[1] = 0.6               # 2022 only
   StdIAQHtRec_SRE[1] = 67                   # 2022 only
   StdIAQHtRec_ASRE[1] = 72                  # 2022 only
   ...
```

#### CIBD25 ResProj (2025):
```
ResProj   "Name"
   (StdDesignFuel properties removed)
   (StdDesignIAQ properties removed)
   CALGreen = 0
   InCmntySlrProjTerritory = 0
   PVCompCredit = 0
   ...
```

**Impact:** Properties are not 1:1 compatible between versions. Must handle missing/extra properties gracefully.

### 2.3 Property Name Changes

| CIBD22 Property | CIBD25 Property | Notes |
|-----------------|-----------------|-------|
| `OccSensorCtrl` | (removed) | Space-level property removed in 2025 |
| `TreeState` | `TreeState` | Moved from Space to Story in some cases |
| Various roof U-values | Updated values | Compliance requirements changed |

---

## 3. Formatting Differences

### 3.1 Property Quoting Rules

**Rule:** Quoting depends on CBECC schema field type, NOT the value's appearance.

#### String Fields (Must Be Quoted):
```
DocAuthZipCode = "92868"        # ✅ Quoted (STRING field)
City = "Sacramento"             # ✅ Quoted
CliZn = "ClimateZone12"         # ✅ Quoted
```

#### Integer Fields (Must NOT Be Quoted):
```
ZipCode = 92009                 # ✅ NOT quoted (INTEGER field)
BldgEngyModelVersion = 17       # ✅ NOT quoted
TotStoryCnt = 5                 # ✅ NOT quoted
```

#### Float Fields (Must NOT Be Quoted):
```
UFactor = 0.34                  # ✅ NOT quoted
SHGC = 0.22                     # ✅ NOT quoted
Vol = 42220.3                   # ✅ NOT quoted
```

**Critical Cases:**

| Property | Type | Example | Notes |
|----------|------|---------|-------|
| `DocAuthZipCode` | STRING | `"92868"` | Must be quoted (can have leading zeros) |
| `ZipCode` | INTEGER | `92009` | Must NOT be quoted |
| `CliZn` | STRING | `"ClimateZone12"` | Must be quoted |

**Implementation:** Our converter uses property-name-based override:

```python
def _requires_quotes(self, prop_name: str) -> bool:
    """Properties that must always be quoted (even if numeric-looking)."""
    always_quote = [
        'DocAuthZipCode',  # STRING field in schema
    ]
    return prop_name in always_quote
```

**Status:** ✅ Fixed in eco_tools/translators/cibd_xml_to_text.py (lines 214-221)

### 3.2 Array Reference Notation

Both text formats use bracket notation for array references:

```
MatRef[1] = "Concrete - 140 lb/ft3 - 6 in."
MatRef[2] = "Stucco - 7/8 in."
ApplRefrigZone[1] = "F2 Res Zn E Court"
```

XML format uses multiple child elements:

```xml
<MatRef>Concrete - 140 lb/ft3 - 6 in.</MatRef>
<MatRef>Stucco - 7/8 in.</MatRef>
```

**Implementation:** Our converter detects array notation with regex:

```python
array_match = re.match(r'(.+)\[(\d+)\]', prop_name)
if array_match:
    base_name = array_match.group(1)
    index = array_match.group(2)
    output.write(f'{indent_str}   {base_name}[{index}] = "{prop_value}"\n')
```

### 3.3 Object Nesting and Indentation

Text format uses 3-space indentation for nesting:

```
Proj   "Building"
   ZipCode = 92009
   Bldg   "Building 1"          # Nested inside Proj
      TotStoryCnt = 5
      Story   "Level 1"          # Nested inside Bldg
         Spc   "Room 1"          # Nested inside Story
            Vol = 1000
            ..
         ..
      ..
   ..
```

XML uses standard XML nesting:

```xml
<Proj>
  <Name>Building</Name>
  <ZipCode>92009</ZipCode>
  <Bldg>
    <Name>Building 1</Name>
    <TotStoryCnt>5</TotStoryCnt>
    <Story>
      <Name>Level 1</Name>
      <Spc>
        <Name>Room 1</Name>
        <Vol>1000</Vol>
      </Spc>
    </Story>
  </Bldg>
</Proj>
```

**Rule:** In text format, objects use `..` terminator to close scope.

---

## 4. Catalog/Library Handling

### 4.1 Material Catalogs

Both CIBD22 and CIBD25 text formats define materials the same way:

```
Mat   "Concrete - 140 lb/ft3 - 6 in."
   CodeCat = "Concrete"
   CodeItem = "Concrete - 140 lb/ft3 - 6 in."
   ..
```

CIBD22X XML format:

```xml
<Mat>
  <Name>Concrete - 140 lb/ft3 - 6 in.</Name>
  <CodeCat>Concrete</CodeCat>
  <CodeItem>Concrete - 140 lb/ft3 - 6 in.</CodeItem>
</Mat>
```

**Key Finding:** Catalog items work the same way in both text formats. The difference is only XML vs text structure.

### 4.2 Catalog References

Text format uses string references:

```
ConsAssm   "Wall Assembly"
   MatRef[1] = "Concrete - 140 lb/ft3 - 6 in."
   MatRef[2] = "Stucco - 7/8 in."
   ..

ExtWall   "Wall 1"
   ConsAssmRef = "Wall Assembly"
   ..
```

XML format is identical:

```xml
<ConsAssm>
  <Name>Wall Assembly</Name>
  <MatRef>Concrete - 140 lb/ft3 - 6 in.</MatRef>
  <MatRef>Stucco - 7/8 in.</MatRef>
</ConsAssm>

<ExtWall>
  <Name>Wall 1</Name>
  <ConsAssmRef>Wall Assembly</ConsAssmRef>
</ExtWall>
```

**Conclusion:** References work identically across all formats. No special handling needed.

---

## 5. Implementation Status

### 5.1 Current Support Matrix

| Format | Import | Export | Roundtrip | Status |
|--------|--------|--------|-----------|--------|
| CIBD22X | ✅ Yes | ✅ Yes | ✅ Yes | Primary format - fully working |
| CIBD22 | ⚠️ Partial | ❌ No | ❌ No | Can read, no export yet |
| CIBD25 | ⚠️ Untested | ✅ Yes | ⚠️ Partial | Export working, import untested |

### 5.2 Fixed Issues

#### 1. ResProj/ProjVar Sibling Structure ✅
- **File:** `eco_tools/translators/cibd_xml_to_text.py`
- **Fix:** Deferred siblings pattern (lines 187-212)
- **Test:** Bressi Ranch roundtrip - ResProj appears as sibling

#### 2. DocAuthZipCode Quoting ✅
- **File:** `eco_tools/translators/cibd_xml_to_text.py`
- **Fix:** Property-name-based quoting (lines 214-221)
- **Test:** DocAuthZipCode = "92868" (quoted), ZipCode = 92009 (not quoted)

#### 3. ResProj Preservation in EMJSON ✅
- **File:** `eco_tools/translators/cibd22x/parsers/proj_parser.py`
- **Fix:** Parse nested elements as dictionaries (lines 69-102)
- **File:** `gui/translators.py`
- **Fix:** Restore proj_metadata from EMJSON (line 1034)
- **Test:** Complete CIBD22X → EMJSON → CIBD25 roundtrip

### 5.3 Remaining Work

#### CIBD22 Import (Not Critical)
- Text parser for CIBD22 format
- Same structure as CIBD25, different schema
- **Priority:** Low (can convert CIBD22 → CIBD22X in CBECC GUI first)

#### CIBD25 Import Testing
- Need to test CIBD25 → EMJSON import path
- Schema differences from CIBD22X need mapping
- **Priority:** Medium

#### Schema Property Mapping
- Document all property changes between 2022 and 2025
- Create mapping table for automatic conversion
- Handle missing/extra properties gracefully
- **Priority:** High (needed for CIBD22X ↔ CIBD25 conversion)

---

## 6. Critical Patterns Summary

### Pattern 1: Top-Level Siblings
**When:** Converting XML to text format
**Elements:** ResProj, ProjVar, DwellUnitType
**Rule:** If child of `<Proj>` in XML, write as top-level sibling in text

### Pattern 2: Property Quoting
**When:** Writing property values in text format
**Rule:** Check property name BEFORE checking value type
**Exception:** DocAuthZipCode must always be quoted (STRING field)

### Pattern 3: Nested Element Preservation
**When:** Parsing CIBD22X XML
**Rule:** Parse nested elements (ResProj, ProjVar) as dictionaries, not strings
**Storage:** Store in proj_metadata for roundtrip

### Pattern 4: Array References
**When:** Converting array properties
**Text:** `MatRef[1] = "Value"`
**XML:** `<MatRef>Value</MatRef>` (multiple elements)

### Pattern 5: Object Termination
**When:** Writing text format
**Rule:** Each object closes with `..` on its own line
**Indentation:** Match the object header indentation

---

## 7. Testing Strategy

### 7.1 Format Conversion Tests

| Test | Input | Output | Status |
|------|-------|--------|--------|
| Commercial 2022 roundtrip | CIBD22X | CIBD22X | ✅ Working |
| Commercial 2022 → 2025 | CIBD22X | CIBD25 | ✅ Working |
| Residential 2022 roundtrip | CIBD22X | CIBD22X | ✅ Working |
| Residential 2022 → 2025 | CIBD22X | CIBD25 | ✅ Working |
| CIBD25 → CIBD22X | CIBD25 | CIBD22X | ⚠️ Needs testing |

### 7.2 Validation Tests

| Test | Description | Status |
|------|-------------|--------|
| CBECC 2022 acceptance | Open exported CIBD22X in CBECC 2022 | ✅ Passing |
| CBECC 2025 acceptance | Open exported CIBD25 in CBECC 2025 | ✅ Passing |
| ResProj preservation | ResProj survives EMJSON roundtrip | ✅ Passing |
| ProjVar preservation | ProjVar survives EMJSON roundtrip | ✅ Passing |
| Property quoting | DocAuthZipCode quoted, ZipCode not | ✅ Passing |

---

## 8. Schema Reference Files

### 8.1 Available Schema Documentation

Located in `/Users/DavidM/Dropbox/EM-Tools-Assets/CBECC Models/`:

- `EMTools_Schema_2019_Comprehensive.xlsx`
- `EMTools_Schema_2025_Comprehensive.xlsx`
- `EMTools_Schema_cibd22_Comprehensive.xlsx`

**Note:** These are user-created documentation, not official CBECC schemas.

### 8.2 Official Sample Files

**Title 24 2022 Samples:**
- `/Users/DavidM/Documents/ECO_Alpha_v7/reference_data/cbecc/CBECC Models/2022 Standard Models/StandardModelTests2022/`
- Commercial buildings (010012-SchSml, 020012-OffSml, etc.)
- Residential buildings (MF88Unit_5Story_ELEC-CZ12.cibd22)

**Title 24 2025 Samples:**
- `/Users/DavidM/Dropbox/EM-Tools-Assets/CBECC Models/2025 Sample Models/`
- Commercial buildings (010012-SchSml, 020012-OffSml, etc.)
- Residential buildings (MF88Unit_5Story_ELEC-CZ12.cibd25)

**Recommendation:** Use official sample files as validation targets for testing.

---

## 9. Common Errors and Fixes

### Error 1: "Expected Quote" at DocAuthZipCode
**Cause:** DocAuthZipCode exported without quotes
**Fix:** Add to `_requires_quotes()` list
**File:** cibd_xml_to_text.py:214-221

### Error 2: "Expected Integer" at ZipCode
**Cause:** ZipCode exported with quotes
**Fix:** Remove from `_requires_quotes()` list
**File:** cibd_xml_to_text.py:214-221

### Error 3: Missing ResProj in export
**Cause:** ResProj nested inside Proj instead of sibling
**Fix:** Add to `_is_top_level_sibling()` check
**File:** cibd_xml_to_text.py:187-204

### Error 4: ResProj empty in EMJSON roundtrip
**Cause:** proj_metadata not restored from EMJSON
**Fix:** Add `internal.proj_metadata = emjson.get("proj_metadata", {})`
**File:** gui/translators.py:1034

### Error 5: HVACSystem field mapping error
**Cause:** Equipment detail fields don't exist in dataclass
**Fix:** Store in annotation dict instead
**File:** gui/translators.py:939-959

---

## 10. Future Work

### 10.1 Schema Mapping Table
Create comprehensive property mapping for 2022 ↔ 2025 conversion:
- Properties that renamed
- Properties that moved (Proj → ProjVar)
- Properties that were removed/added
- Default values for missing properties

### 10.2 CIBD22 Import Support
If needed, create text parser for CIBD22 format:
- Same text structure as CIBD25
- Different schema (2022 rules)
- Can reuse most CIBD25 parsing logic

### 10.3 Automatic Version Detection
Detect file version from RulesetFilename:
- `T24N_2022.bin` → CIBD22/CIBD22X
- `T24_2025.bin` → CIBD25
- Auto-apply correct schema rules

### 10.4 Property Validation
Validate properties against schema:
- Check required vs optional
- Validate data types
- Check allowed values (enumerations)
- Warn on unknown properties

---

## 11. Conclusion

### Key Takeaways

1. **CIBD22 and CIBD25 are structurally identical** - Both use text format with same syntax
2. **Schema differences are the real challenge** - Properties changed between 2022 and 2025
3. **XML to text conversion has structural patterns** - ResProj/ProjVar must be siblings
4. **Property quoting depends on schema** - Not on value appearance

### Current Status

✅ **Ready for Production:**
- CIBD22X import
- CIBD22X → CIBD25 export
- ResProj/ProjVar preservation
- Residential compliance support

⚠️ **Needs Testing:**
- CIBD25 import
- Schema property mapping (2022 ↔ 2025)

❌ **Not Implemented:**
- CIBD22 import (low priority)
- Automatic schema version conversion

### Recommendation

**For current projects:** Use CIBD22X as primary format, export to CIBD25 for simulation.

**For future work:** Focus on schema property mapping to enable bidirectional 2022 ↔ 2025 conversion.

---

## References

- **Official Samples:** `/Users/DavidM/Dropbox/EM-Tools-Assets/CBECC Models/2025 Sample Models/`
- **Test Files:** `/Users/DavidM/Documents/ECO_Alpha_v7/test_output/`
- **Documentation:**
  - `docs/CIBD25_ZIPCODE_FIX_COMPLETE.md` - Property quoting fix
  - `docs/V7_INTEGRATION_COMPLETE.md` - v7 translator architecture
- **Code:**
  - `eco_tools/translators/cibd_xml_to_text.py` - XML to text converter
  - `eco_tools/translators/cibd22x/` - CIBD22X parser/exporter
  - `eco_tools/translators/cibd25.py` - CIBD25 exporter
