# CIBD25 Export - Quick Start Guide

**Last Updated:** November 13, 2025
**Status:** ✅ Production Ready

---

## Quick Summary

Export CIBD22X models to CIBD25 format for Title 24 2025 compliance simulation in CBECC 2025.

**Key Facts:**
- ✅ Full building data preserved (1.2MB+ files)
- ✅ Correct metadata: T24_2025.bin ruleset, CBECC 2025.2.0 (build 1390)
- ✅ Opens directly in CBECC 2025
- ✅ Command-line tool ready for production use

---

## 30-Second Usage

### Convert CIBD22X → CIBD25

```bash
# Navigate to project directory
cd /Users/DavidM/Documents/ECO_Alpha_v7

# Convert file
python3 convert_cibd22x_to_cibd25.py input.cibd22x output.cibd25

# Open in CBECC 2025
open -a 'CBECC 2025' output.cibd25
```

**Example:**
```bash
python3 convert_cibd22x_to_cibd25.py \
    /Users/DavidM/Documents/ECO_Alpha/Bressi_FINAL.cibd22x \
    Bressi_2025.cibd25

open -a 'CBECC 2025' Bressi_2025.cibd25
```

---

## What You Get

### Input (CIBD22X)
- Title 24 2022 format
- XML structure
- RulesetFilename: "T24N_2022.bin"
- Any building model

### Output (CIBD25)
- Title 24 2025 format
- Text structure (CBECC native)
- RulesetFilename: "T24_2025.bin"
- SoftwareVersion: "CBECC 2025.2.0 (1390)"
- BldgEngyModelVersion: 17
- **All building data preserved** (geometry, systems, schedules, materials)

### Example Output Format
```
RulesetFilename   "T24_2025.bin"

Proj   "Bressi Ranch Apartments"
   BldgEngyModelVersion = 17
   SoftwareVersion = "CBECC 2025.2.0 (1390)"
   RulesetFilename = "T24_2025.bin"
   City = "Carlsbad"

   Bldg
      ResZnGrp   "L01"
         Type = "floor"
         ..

      ResZn   "A1_L01"
         FloorArea = 243.75
         ...
```

---

## Verification Checklist

After conversion, verify your CIBD25 file:

**File Size:**
- [ ] File is substantial (100KB+ for typical buildings, 1MB+ for large projects)
- [ ] Not just a few hundred bytes (would indicate missing data)

**First Line:**
- [ ] `RulesetFilename   "T24_2025.bin"`

**Metadata:**
- [ ] Contains `Proj   "Your Building Name"`
- [ ] Contains `SoftwareVersion = "CBECC 2025.2.0 (1390)"`
- [ ] Contains `BldgEngyModelVersion = 17`

**Building Data:**
- [ ] Contains `Bldg` section
- [ ] Contains zones (ResZn, NonResZn, etc.)
- [ ] Contains geometry data

**CBECC 2025:**
- [ ] File opens without errors
- [ ] Can view building in 3D
- [ ] Can run compliance analysis

---

## Common Scenarios

### Scenario 1: Single Building Conversion
```bash
# Convert one building
python3 convert_cibd22x_to_cibd25.py MyBuilding.cibd22x MyBuilding_2025.cibd25

# Verify it opens
open -a 'CBECC 2025' MyBuilding_2025.cibd25
```

### Scenario 2: Batch Conversion
```bash
# Convert multiple buildings
for file in *.cibd22x; do
    output="${file%.cibd22x}_2025.cibd25"
    python3 convert_cibd22x_to_cibd25.py "$file" "$output"
    echo "Converted: $file → $output"
done
```

### Scenario 3: Programmatic Python Usage
```python
from eco_tools.translators.cibd22x import CIBD22XImporter
from eco_tools.translators.cibd25 import CIBD25Exporter

# Load CIBD22X
importer = CIBD22XImporter()
internal = importer.import_file("input.cibd22x")

# Export to CIBD25
exporter = CIBD25Exporter()
exporter.export(internal, "output.cibd25")
```

---

## Troubleshooting

### Problem: File opens but says "Unable to read/parse"
**Solution:** Make sure you're using `.cibd25` extension (not `.xml`). The extension determines the format.

### Problem: File only contains metadata (< 1KB)
**Cause:** Source CIBD22X didn't have building data, or export failed.
**Solution:** Check source file has building data. Re-run conversion with error output.

### Problem: Wrong CBECC version shown
**Solution:** This is expected - the file will update to correct version when opened in CBECC 2025.

### Problem: Python import errors
**Solution:** Make sure you're running from the project root directory:
```bash
cd /Users/DavidM/Documents/ECO_Alpha_v7
python3 convert_cibd22x_to_cibd25.py ...
```

---

## Testing

### Run the Demo Test
```bash
python3 test_cibd25_final_demo.py
```

**Expected Output:**
```
✅ CIBD25 EXPORT DEMONSTRATION SUCCESSFUL

Summary:
  • Size:   1,218,773 bytes (1.16 MB)
  • Format: CIBD25 text format
  • Ruleset: T24_2025.bin (Title 24 2025)
  • Version: CBECC 2025.2.0 (1390)
```

---

## File Locations

**Converter Tool:**
```
/Users/DavidM/Documents/ECO_Alpha_v7/convert_cibd22x_to_cibd25.py
```

**Core Libraries:**
```
eco_tools/translators/cibd25/exporter.py        - CIBD25 export logic
eco_tools/translators/cibd_xml_to_text.py       - XML→Text converter
eco_tools/translators/cibd22x/importer.py       - CIBD22X import logic
```

**Tests:**
```
test_cibd25_final_demo.py                       - Demonstration test
test_cibd25_complete.py                         - Integration test
```

**Documentation:**
```
docs/CIBD25_IMPLEMENTATION_COMPLETE.md         - Technical details
docs/CIBD25_EXPORT_STATUS.md                    - Implementation status
docs/CBECC_2025_VERSION_CONFIRMATION.md        - Version info
```

---

## Support

**Questions about the export process?**
- Check `/Users/DavidM/Documents/ECO_Alpha_v7/docs/CIBD25_IMPLEMENTATION_COMPLETE.md`
- Review test output: `python3 test_cibd25_final_demo.py`

**Found a bug?**
- Check that source CIBD22X file is valid
- Run demo test to verify system is working
- Review error messages in terminal output

---

## Summary

**Command:**
```bash
python3 convert_cibd22x_to_cibd25.py input.cibd22x output.cibd25
```

**Result:**
- Full building model in CIBD25 text format
- Ready for Title 24 2025 compliance simulation
- Opens directly in CBECC 2025

**Verified With:**
- Bressi Ranch Apartments (1.16 MB)
- Full geometry, systems, and schedules
- Opens successfully in CBECC 2025.2.0 (build 1390)

✅ **Ready for production use**
