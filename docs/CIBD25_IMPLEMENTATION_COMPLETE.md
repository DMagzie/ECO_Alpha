# CIBD25 Export Implementation - COMPLETE ✅

**Date:** November 13, 2025
**Status:** Production Ready for File-to-File Conversion

---

## ✅ Implementation Complete

### What Was Delivered

Full support for exporting CIBD22X models to CIBD25 format for Title 24 2025 compliance simulation in CBECC 2025.

**Key Features:**
- ✅ Correct Title 24 2025 metadata (RulesetFilename: "T24_2025.bin")
- ✅ Correct software version (CBECC 2025.2.0 build 1390)
- ✅ XML to text format conversion
- ✅ Preserves full building data (geometry, systems, schedules)
- ✅ Opens successfully in CBECC 2025
- ✅ Command-line conversion tool
- ✅ GUI export infrastructure (with known limitation)

---

## 🚀 Production Usage

### Method 1: Command-Line Conversion (RECOMMENDED)

Convert existing CIBD22X files to CIBD25 text format:

```bash
cd /Users/DavidM/Documents/ECO_Alpha_v7

# Convert CIBD22X → CIBD25
python3 convert_cibd22x_to_cibd25.py input.cibd22x output.cibd25

# Example: Convert Bressi Ranch
python3 convert_cibd22x_to_cibd25.py \
    /Users/DavidM/Documents/ECO_Alpha/Bressi_FINAL.cibd22x \
    Bressi_Ranch_2025.cibd25

# Open in CBECC 2025
open -a 'CBECC 2025' Bressi_Ranch_2025.cibd25
```

**Result:** Full 1.1MB+ files with complete building data, ready for simulation.

### Method 2: Programmatic Python API

```python
from eco_tools.translators.cibd25 import CIBD25Exporter
from eco_tools.translators.cibd22x import translate_cibd22x_to_internal

# Load CIBD22X model
internal = translate_cibd22x_to_internal("input.cibd22x")

# Export to CIBD25 text format
exporter = CIBD25Exporter()
exporter.export(internal, "output.cibd25")  # Text format

# Or export to XML format
exporter.export(internal, "output.xml")      # XML format
```

### Method 3: Direct XML to Text Conversion

If you already have a CIBD25 XML file and just need text format:

```python
from eco_tools.translators.cibd_xml_to_text import convert_xml_to_text

convert_xml_to_text("input.xml", "output.cibd25")
```

---

## 📋 Verification

### Test Results

**File:** Bressi Ranch Apartments
**Source:** CIBD22X (v22)
**Output:** CIBD25 text format
**Size:** 1.1 MB
**Status:** ✅ Opens in CBECC 2025

**Format Verification:**
```
RulesetFilename   "T24_2025.bin"

Proj   "Bressi Ranch Apartments"
   BldgEngyModelVersion = 17
   SoftwareVersion = "CBECC 2025.2.0 (1390)"
   RulesetFilename = "T24_2025.bin"

   Bldg
      ResZnGrp   "L01"
         Type = "floor"
         ..

      ResZn   "A1_L01"
         FloorArea = 243.75
         ...
```

### What Was Tested

1. ✅ CIBD22X → CIBD25 conversion preserves all data
2. ✅ Text format matches CBECC 2025 expectations
3. ✅ Metadata correctly updated for Title 24 2025
4. ✅ File opens without errors in CBECC 2025
5. ✅ Building geometry preserved
6. ✅ HVAC systems preserved
7. ✅ Schedules preserved
8. ✅ Materials and constructions preserved

---

## 🔧 Technical Implementation

### Files Created

**New Tools:**
```
convert_cibd22x_to_cibd25.py                      - CLI conversion tool
eco_tools/translators/cibd_xml_to_text.py         - XML→Text converter
eco_tools/translators/cibd25/exporter.py          - CIBD25 exporter
test_cibd25_complete.py                            - Integration test
docs/CBECC_2025_VERSION_CONFIRMATION.md          - Version docs
```

**Modified Files:**
```
eco_tools/translators/cibd22/text_parser.py        - Capture RulesetFilename
eco_tools/translators/cibd22x/importer.py          - Capture root attributes
eco_tools/translators/cibd25/__init__.py           - Added exports
gui/translators.py                                  - Added emjson6_to_cibd25()
gui/pages/export_page.py                          - Added CIBD25 export UI
```

### Architecture

```
┌─────────────────────────────────────────────────┐
│         CIBD25 Export Pipeline                   │
└─────────────────────────────────────────────────┘
                    │
                    ▼
┌───────────────────────────────────────────────┐
│  Input: CIBD22X File (.cibd22x or .xml)       │
└───────────────────────────────────────────────┘
                    │
                    ▼
┌───────────────────────────────────────────────┐
│  Parse to InternalRepresentation              │
│  (via CIBD22XImporter)                        │
└───────────────────────────────────────────────┘
                    │
                    ▼
┌───────────────────────────────────────────────┐
│  Export to CIBD22X XML                        │
│  (via CIBD22XExporter)                        │
└───────────────────────────────────────────────┘
                    │
                    ▼
┌───────────────────────────────────────────────┐
│  Update Metadata for Title 24 2025            │
│  - RulesetFilename: "T24_2025.bin"            │
│  - SoftwareVersion: "CBECC 2025.2.0 (1390)"   │
│  - BldgEngyModelVersion: 17                   │
└───────────────────────────────────────────────┘
                    │
                    ▼
┌───────────────────────────────────────────────┐
│  Convert XML → Text Format                    │
│  (via cibd_xml_to_text.py)                    │
│  - Object headers: Proj "Name"                │
│  - Properties: key = value                    │
│  - Numbers without quotes                     │
│  - Strings with quotes                        │
│  - Object terminators: ..                     │
└───────────────────────────────────────────────┘
                    │
                    ▼
┌───────────────────────────────────────────────┐
│  Output: CIBD25 Text File                     │
│  Ready for CBECC 2025 Simulation              │
└───────────────────────────────────────────────┘
```

### Key Technical Details

**1. RulesetFilename Capture**

Modified text parser to capture standalone properties:
```python
# eco_tools/translators/cibd22/text_parser.py
standalone_prop_match = re.match(r'^([A-Z][A-Za-z0-9_]*)\s+"([^"]+)"', line)
if standalone_prop_match and not self.current_stack:
    prop_name = standalone_prop_match.group(1)
    prop_value = standalone_prop_match.group(2)
    self.root_metadata[prop_name] = prop_value
```

**2. Format Detection**

CIBD25 exporter detects output format based on file extension:
- `.cibd25` → Text format (CBECC native)
- `.xml` → XML format

**3. Metadata Enforcement**

Automatically ensures correct Title 24 2025 metadata:
```python
def _ensure_2025_metadata(self, internal: InternalRepresentation):
    if 'RulesetFilename' not in internal.proj_metadata:
        internal.proj_metadata['RulesetFilename'] = 'T24_2025.bin'

    if 'SoftwareVersion' not in internal.proj_metadata or \
       '2022' in str(internal.proj_metadata.get('SoftwareVersion', '')):
        internal.proj_metadata['SoftwareVersion'] = 'CBECC 2025.2.0 (1390)'

    if 'BldgEngyModelVersion' not in internal.proj_metadata:
        internal.proj_metadata['BldgEngyModelVersion'] = '17'
```

**4. Text Format Conversion**

Proper formatting rules implemented:
- Numbers: `BldgEngyModelVersion = 17` (no quotes)
- Strings: `City = "Carlsbad"` (with quotes)
- Objects: `Proj   "Name"` (double-quoted name)
- Nesting: 3-space indentation
- Terminators: `..` on new line

---

## ⚠️ Known Limitations

### GUI EMJSON Export

The GUI export function (`emjson6_to_cibd25()`) exists and is wired up, but currently only exports metadata (76 bytes) because:

**Root Cause:**
The active EMJSON model in GUI only contains project metadata. Full building data (geometry, systems) isn't preserved during GUI workflows.

**Current Behavior:**
```python
# GUI workflow:
Load CIBD22X → Parse → Store in EMJSON (metadata only) → Export CIBD25
# Result: Only 76 bytes (just Proj metadata, no building data)
```

**Workaround:**
Use command-line file-to-file conversion instead of GUI export.

**Future Fix Options:**
1. Implement full EMJSON → InternalRepresentation conversion
2. Update GUI to preserve full building data when loading models
3. Use file paths instead of in-memory EMJSON in GUI export

---

## 📚 Documentation

### User Guide

**Q: How do I convert a CIBD22X model to CIBD25?**

```bash
python3 convert_cibd22x_to_cibd25.py input.cibd22x output.cibd25
open -a 'CBECC 2025' output.cibd25
```

**Q: What's the difference between .cibd25 and .xml files?**

- `.cibd25` = Text format (CBECC native, human-readable)
- `.xml` = XML format (machine-readable)

Both contain the same data. CBECC 2025 prefers text format.

**Q: Can I export from the GUI?**

Yes, the GUI has a CIBD25 export option, but it currently only exports metadata. Use the command-line tool for full building data.

**Q: Will my CIBD22X data be preserved?**

Yes, all building data (geometry, systems, schedules, materials) is preserved during conversion.

**Q: What version of Title 24 does this support?**

Title 24 2025 (RulesetFilename: "T24_2025.bin")

---

## ✅ Acceptance Criteria Met

- [x] Captures RulesetFilename from input files
- [x] Exports with correct T24_2025.bin ruleset
- [x] Uses CBECC 2025.2.0 (build 1390) version string
- [x] Converts XML to text format for .cibd25 files
- [x] Preserves full building data (1.1MB+ files)
- [x] Opens successfully in CBECC 2025
- [x] Command-line tool for production use
- [x] GUI export infrastructure (with documented limitation)
- [x] Comprehensive documentation

---

## 🎯 Recommendations

**For Production Use:**
1. Use `convert_cibd22x_to_cibd25.py` for converting existing CIBD22X files
2. Output format: `.cibd25` (text format) for CBECC 2025
3. Verify metadata: Check first few lines contain `RulesetFilename   "T24_2025.bin"`

**For Development:**
1. GUI export limitation documented - use file-to-file conversion
2. Consider implementing full EMJSON preservation in future GUI updates

**For Testing:**
1. Test file size: Should be ~1MB+ for typical multi-family buildings
2. Test opening in CBECC 2025: Should open without errors
3. Test simulation: Should run Title 24 2025 compliance analysis

---

## 📊 Summary

**Status:** ✅ **PRODUCTION READY**

**What Works:**
- File-to-file CIBD22X → CIBD25 conversion
- XML to text format conversion
- Correct Title 24 2025 metadata
- Full building data preservation
- CBECC 2025 compatibility

**What's Documented:**
- RulesetFilename capture during import: `eco_tools/translators/cibd22x/importer.py:271-275`
- CIBD25 export with metadata enforcement: `eco_tools/translators/cibd25/exporter.py:45-80`
- XML to text converter: `eco_tools/translators/cibd_xml_to_text.py`
- Command-line tool: `convert_cibd22x_to_cibd25.py`
- GUI integration: `gui/translators.py:399-487`, `gui/pages/export_page.py:112-131`

**Delivered Value:**
Users can now export their CIBD22X models to CIBD25 format for Title 24 2025 compliance simulation in CBECC 2025, with full building data preservation and correct metadata.

---

**Implementation Complete:** November 13, 2025
**Tested With:** Bressi Ranch Apartments (1.1MB multi-family building)
**CBECC Version:** 2025.2.0 (build 1390)
**Status:** Ready for production use ✅
