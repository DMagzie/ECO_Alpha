# CIBD25 Export Implementation Status

**Date:** November 13, 2025
**Status:** Partial Implementation Complete

## ✅ What Works

### 1. CIBD22X File → CIBD25 File Conversion (COMPLETE)

**Workflow:**
```
CIBD22X XML file → Update metadata → Convert to text format → CIBD25 file
```

**Features:**
- ✅ Full building data preserved (1.1MB+ files)
- ✅ Automatic format detection (.cibd25 → text, .xml → XML)
- ✅ Correct Title 24 2025 metadata:
  - `RulesetFilename: "T24_2025.bin"`
  - `SoftwareVersion: "CBECC 2025.2.0 (1390)"`
  - `BldgEngyModelVersion: 17`
- ✅ Opens successfully in CBECC 2025
- ✅ Text format matches CBECC expectations

**Tools:**
- `convert_cibd22x_to_cibd25.py` - Command-line converter
- `eco_tools/translators/cibd_xml_to_text.py` - XML→Text converter
- `eco_tools/translators/cibd25/exporter.py` - Format-aware exporter

**Test Results:**
```
File: Bressi_Ranch.cibd25
Size: 1.1 MB
Format: Text (CBECC native)
CBECC 2025: Opens successfully ✓
```

### 2. XML-to-Text Converter (COMPLETE)

**Features:**
- ✅ Converts CBECC XML to text format
- ✅ Handles namespaces correctly
- ✅ Proper formatting:
  - Numbers without quotes (17, not "17")
  - Strings with quotes ("value")
  - Objects with names: `Proj   "Name"`
  - Object terminators: `..`
- ✅ Nested objects and properties
- ✅ Array references: `MatRef[1] = "Material"`

## ⚠️ What Needs Work

### EMJSON → CIBD25 Export from GUI

**Current Limitation:**
The GUI export function (`emjson6_to_cibd25()`) can export EMJSON to CIBD25, but currently only exports metadata because:

1. The active EMJSON model in GUI only contains project metadata
2. Full building data (geometry, systems) isn't being preserved in EMJSON during GUI workflows
3. The v7 CIBD22X exporter expects InternalRepresentation, not EMJSON directly

**Why it doesn't work yet:**
```python
# Current flow:
EMJSON (metadata only) → CIBD22X exporter → Empty XML → CIBD25 text
# Result: Only 76 bytes (just metadata, no building data)
```

**What's needed:**
Either:
1. Implement full EMJSON → InternalRepresentation conversion (populate geometry, systems, etc.)
2. OR: Update GUI to preserve full building data when loading models
3. OR: Use file-to-file conversion instead of in-memory EMJSON

## 🔧 Implementation Details

### Files Created/Modified

**New Files:**
```
eco_tools/translators/cibd_xml_to_text.py         - XML to text converter
convert_cibd22x_to_cibd25.py                      - CLI conversion tool
test_cibd25_complete.py                            - Integration test
test_gui_cibd25_export.py                         - GUI export test
docs/CBECC_2025_VERSION_CONFIRMATION.md          - Version info
```

**Modified Files:**
```
eco_tools/translators/cibd25/exporter.py          - Added text format support
eco_tools/translators/cibd22/text_parser.py        - Capture RulesetFilename
eco_tools/translators/cibd22x/importer.py          - Capture root attributes
gui/translators.py                                  - Added emjson6_to_cibd25()
gui/pages/export_page.py                          - Added CIBD25 export UI
```

### Architecture

```
┌─────────────────────────────────────────┐
│         CIBD25 Export Pipeline           │
└─────────────────────────────────────────┘
              │
              ▼
┌──────────────────────────────┐
│  Input: CIBD22X XML File     │
└──────────────────────────────┘
              │
              ▼
┌──────────────────────────────┐
│  Update Metadata for 2025    │
│  - RulesetFilename           │
│  - SoftwareVersion           │
│  - BldgEngyModelVersion      │
└──────────────────────────────┘
              │
              ▼
┌──────────────────────────────┐
│  Convert XML → Text Format   │
│  (cibd_xml_to_text.py)       │
└──────────────────────────────┘
              │
              ▼
┌──────────────────────────────┐
│  Output: CIBD25 Text File    │
│  Ready for CBECC 2025        │
└──────────────────────────────┘
```

## 📋 Testing

### Successful Tests

**Test 1: XML to Text Conversion**
```bash
python3 eco_tools/translators/cibd_xml_to_text.py \
    Bressi_Ranch_CIBD25_Full.xml \
    Bressi_Ranch.cibd25
# Result: ✓ 1.1MB file with full building data
```

**Test 2: CIBD22X → CIBD25 Conversion**
```bash
python3 convert_cibd22x_to_cibd25.py \
    Bressi_FINAL.cibd22x \
    Bressi_Ranch.cibd25
# Result: ✓ Opens in CBECC 2025
```

**Test 3: Format Verification**
```bash
head -30 Bressi_Ranch.cibd25
# Shows:
#   RulesetFilename   "T24_2025.bin"
#   Proj   "Bressi Ranch Apartments"
#   BldgEngyModelVersion = 17
#   SoftwareVersion = "CBECC 2025.2.0 (1390)"
#   [Building data...]
```

### Test Failures

**Test: GUI EMJSON → CIBD25**
```
Input: EMJSON from GUI (metadata only)
Output: 76 bytes (empty building)
Issue: Missing building geometry/systems data
```

## 🎯 Recommended Usage

### For Production Use

**Use Case 1: Convert Existing CIBD22X Files to CIBD25**
```bash
python3 convert_cibd22x_to_cibd25.py input.cibd22x output.cibd25
open -a 'CBECC 2025' output.cibd25
```

**Use Case 2: Programmatic Export from Python**
```python
from eco_tools.translators.cibd25 import CIBD25Exporter
from eco_tools.core.internal_repr import InternalRepresentation

# Load your model into InternalRepresentation
internal = InternalRepresentation()
# ... populate internal with building data ...

# Export to CIBD25
exporter = CIBD25Exporter()
exporter.export(internal, "output.cibd25")  # Text format
exporter.export(internal, "output.xml")      # XML format
```

### Not Yet Ready for Production

**GUI EMJSON Export** - Needs full data pipeline implementation

## 🔮 Next Steps

### Priority 1: Fix GUI Export (if needed)
1. Implement full EMJSON → InternalRepresentation converter
2. Update GUI model loading to preserve all building data
3. Test with actual models that have geometry/systems

### Priority 2: Documentation
1. User guide for CIBD22X → CIBD25 conversion
2. API documentation for programmatic use
3. Integration guide for GUI workflows

### Priority 3: Validation
1. Test with more complex models
2. Verify compliance analysis results match
3. Test roundtrip: CIBD22X → CIBD25 → CBECC → Export → Compare

## 📝 Summary

**What's Ready:**
- ✅ File-to-file CIBD22X → CIBD25 conversion
- ✅ XML to text format conversion
- ✅ Correct Title 24 2025 metadata
- ✅ CBECC 2025 compatibility

**What's Not Ready:**
- ⚠️ GUI EMJSON → CIBD25 export (metadata only, missing building data)

**Recommendation:**
Use the file-to-file conversion approach for now. The GUI export will work once the full EMJSON → InternalRepresentation pipeline is implemented.
