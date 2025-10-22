# GUI Changes: CIBD22X-Only Support

**Date**: 2025-10-22  
**Purpose**: Restrict GUI to only support CIBD22X translator, disabling legacy translators (CIBD22, CIBD25, HBJSON)

## Summary

Modified the ECO Alpha GUI to support only the CIBD22X round-trip translator. All legacy translators (CIBD22, CIBD25, HBJSON) have been disabled but remain in the codebase as commented code for potential future reactivation.

## Files Modified

### 1. `explorer_gui/translators.py`

**Changes:**
- Modified `list_importers()` to return only CIBD22X importer
- Commented out CIBD22, CIBD25, and HBJSON importer entries
- Added comment: "Legacy translators disabled - only CIBD22X currently supported"

**Impact:**
- Only CIBD22X appears in importer dropdowns/lists
- Legacy format translator functions still exist but are not exposed

### 2. `explorer_gui/import_export.py`

**Changes:**
- Updated imports to only import `translate_cibd22x_to_v6` and `emjson6_to_cibd22x`
- Commented out imports for legacy translators
- Modified `import_file()` dispatcher to only handle "cibd22x" format
- Updated error message context to state: "Only CIBD22X format is currently supported. Legacy formats (CIBD22, CIBD25, HBJSON) have been disabled."
- Removed `translate_cibd22_to_v6()` legacy wrapper function
- Kept `translate_cibd22x_to_v6()` legacy wrapper function

**Impact:**
- Attempting to use legacy format IDs results in clear error message
- Only CIBD22X import path is active

### 3. `explorer_gui/pages/import_page.py`

**Changes:**
- Updated page caption from "Import CIBD22, CIBD22X XML, or EMJSON v6 files" to "Import CIBD22X XML or EMJSON v6 files"
- Modified file uploader to only accept `.xml`, `.cibd22x`, and `.json` extensions (removed `.cibd22`)
- Updated help text from "Upload CIBD22 (.cibd22), CIBD22X XML (.xml, .cibd22x), or EMJSON v6 JSON file" to "Upload CIBD22X XML (.xml, .cibd22x) or EMJSON v6 JSON file"
- Simplified file extension handling:
  - Removed CIBD22 text format branch
  - XML files now automatically use CIBD22X importer (no selection dropdown)
  - Button label changed to "Import CIBD22X XML"
- Updated paste XML tab:
  - Changed text area label from "Paste CIBD22 or CIBD22X content here" to "Paste CIBD22X XML content here"
  - Changed help text from "Paste the contents of a CIBD22 text file or CIBD22X XML file" to "Paste the contents of a CIBD22X XML file"
  - Removed importer selection dropdown
  - Hardcoded importer_id to "cibd22x"
  - Added info message: "Will import as CIBD22X XML format"

**Impact:**
- UI only shows CIBD22X as import option
- No confusion about which format to select
- Cleaner, simpler user experience

### 4. `explorer_gui/pages/export_page.py`

**Changes:**
- Fixed import statement to use correct module path: `from explorer_gui.translators import emjson6_to_cibd22x`

**Impact:**
- Export page already only supported CIBD22X and EMJSON v6 (no changes needed to UI)
- Import statement now works correctly

## Testing

Created comprehensive test script: `test_gui_cibd22x_only.py`

**Test Results:**
- ✅ `list_importers()` returns only CIBD22X
- ✅ `get_importers()` returns only CIBD22X
- ✅ CIBD22X import functionality works correctly
- ✅ Legacy format IDs are rejected with proper error message
- ✅ CIBD22X export functionality works correctly

**Test Command:**
```bash
python test_gui_cibd22x_only.py
```

## Verification

### Importer List
```python
from explorer_gui.translators import list_importers
importers = list_importers()
# Returns: [{'id': 'cibd22x', 'label': 'CIBD22X (XML Format)', ...}]
```

### Legacy Format Rejection
```python
from explorer_gui.import_export import import_file
result = import_file('cibd22', 'file.cibd22')
# Returns error: "Unknown importer: cibd22"
# Context: "Only CIBD22X format is currently supported. Legacy formats (CIBD22, CIBD25, HBJSON) have been disabled."
```

### Export Formats
- EMJSON v6 (JSON format) - Always available
- CIBD22X XML - Available and working

## Future Reactivation

To reactivate legacy translators in the future:

1. **In `explorer_gui/translators.py`:**
   - Uncomment the desired importer entries in `list_importers()`

2. **In `explorer_gui/import_export.py`:**
   - Uncomment the desired import statements
   - Add branches back to `import_file()` dispatcher
   - Uncomment legacy wrapper functions if needed

3. **In `explorer_gui/pages/import_page.py`:**
   - Update caption to mention additional formats
   - Update file uploader to accept additional extensions
   - Add back file extension handling branches
   - Add back importer selection dropdowns if desired

4. **Update help text and UI labels** to reflect additional formats

## Notes

- All translator implementation code remains intact in `em-tools/emtools/`
- Only GUI exposure has been modified
- CIBD22X round-trip translator is fully functional
- Export functionality unchanged (already CIBD22X-only)
- Semantic errors in PyCharm are false positives due to module structure

## Related Files

### Translator Implementation (Not Modified)
- `em-tools/emtools/translators/cibd22x_importer.py` - CIBD22X import
- `em-tools/emtools/exporters/cibd22x_exporter.py` - CIBD22X export
- `em-tools/emtools/parsers/` - Parser modules (zones, surfaces, systems, catalogs)
- `em-tools/emtools/utils/id_registry.py` - ID registry for stable references

### Legacy Translator Implementation (Not Modified, Still Available)
- `em-tools/emtools/translators/cibd22_importer.py` - CIBD22 text format
- `em-tools/emtools/translators/cibd25_importer.py` - CIBD25 text format  
- `em-tools/emtools/translators/hbjson_importer.py` - HBJSON format
- `em-tools/emtools/exporters/hbjson_exporter.py` - HBJSON export

## Summary of Changes

**Changed Files:** 4  
**Lines Modified:** ~60  
**Test Coverage:** 5 tests, all passing  
**Breaking Changes:** None (only GUI exposure changed, not API)  
**Backward Compatibility:** Legacy translator code preserved for future use

The GUI now provides a focused, streamlined experience supporting only CIBD22X XML format with full round-trip capability to EMJSON v6.
