# CIBD25 Export - Complete Implementation Plan

**Date:** January 14, 2025
**Status:** Ready for Implementation
**Estimated Effort:** 1 hour

---

## Executive Summary

We have been fixing CIBD25 export errors one-by-one (ResProj sibling, DocAuthZipCode quoting, ResHVAC objects). This is inefficient and error-prone.

**Root Cause:** The XML-to-text converter has incomplete lists of:
1. Object types that should be extracted as top-level siblings
2. Properties that require quoting

**Solution:** Implement complete lists based on comprehensive analysis of official CIBD25 samples.

---

## The Core Problem

### Current Implementation
```python
def _is_top_level_sibling(self, child_tag: str, parent_tag: str) -> bool:
    if parent_tag == 'Proj':
        return child_tag in ['ResProj', 'ProjVar', 'DwellUnitType']
    return False
```

**This only handles 3 object types!**

### What's Actually Needed

**26+ object types** that are children of `<Proj>` in XML but must be top-level siblings in text:

- **Residential HVAC Catalog (10 types):** ResHtgSys, ResClgSys, ResHtPumpSys, ResDistSys, ResFanSys, ResIAQFan, ResDHWSys, ResWtrHtr, ResLpTankHtr, ResCentralVentSys
- **Residential Construction (3 types):** ResConsAssm, ResMat, ResWinType
- **HERS/Compliance (8 types):** HERSCool, HERSHeat, HERSHtPump, HERSDist, HERSFan, HERSDHWSys, HERSOther, SpeclFtr
- **Report Objects (5 types):** ResDHWSysRpt, DwellUnitRpt, ResIAQVentRpt, ResSCSysRpt, EUseSummary

---

## Implementation Checklist

### ✅ Task 1: Update `_is_top_level_sibling()` Method

**File:** `eco_tools/translators/cibd_xml_to_text.py`
**Lines:** 195-212 (current implementation)

**Replace with:**

```python
def _is_top_level_sibling(self, child_tag: str, parent_tag: str) -> bool:
    """
    Check if an element should be written as a top-level sibling instead of nested.

    In CIBD XML, many elements are nested inside Proj for structure,
    but in CIBD text format they should be top-level siblings.

    Args:
        child_tag: Tag of the child element
        parent_tag: Tag of the parent element

    Returns:
        True if child should be written as top-level sibling
    """
    # Elements that appear as children of Proj in XML but should be siblings in text
    if parent_tag == 'Proj':
        # Project variants (compliance data)
        if child_tag in ['ResProj', 'ProjVar']:
            return True

        # Dwelling unit type definitions
        if child_tag == 'DwellUnitType':
            return True

        # Residential HVAC catalog (all systems are top-level library objects)
        if child_tag in [
            'ResHtgSys',           # Heating systems
            'ResClgSys',           # Cooling systems
            'ResHtPumpSys',        # Heat pump systems
            'ResDistSys',          # Distribution systems
            'ResFanSys',           # Fan systems
            'ResIAQFan',           # IAQ fans
            'ResDHWSys',           # DHW systems
            'ResWtrHtr',           # Water heaters
            'ResLpTankHtr',        # Loop tank heaters
            'ResCentralVentSys',   # Central ventilation
        ]:
            return True

        # Residential construction catalog
        if child_tag in [
            'ResConsAssm',         # Construction assemblies
            'ResMat',              # Materials
            'ResWinType',          # Window types
        ]:
            return True

        # HERS/Compliance objects
        if child_tag in [
            'HERSCool',            # HERS cooling
            'HERSHeat',            # HERS heating
            'HERSHtPump',          # HERS heat pump
            'HERSDist',            # HERS distribution
            'HERSFan',             # HERS fan
            'HERSDHWSys',          # HERS DHW
            'HERSOther',           # HERS other
            'SpeclFtr',            # Special features
        ]:
            return True

        # Report objects
        if child_tag in [
            'ResDHWSysRpt',        # DHW system reports
            'DwellUnitRpt',        # Dwelling unit reports
            'ResIAQVentRpt',       # IAQ ventilation reports
            'ResSCSysRpt',         # Space conditioning reports
            'EUseSummary',         # End use summary
        ]:
            return True

    return False
```

**Verification:** Run test to ensure all HVAC/catalog objects are extracted.

---

### ✅ Task 2: Update `_requires_quotes()` Method

**File:** `eco_tools/translators/cibd_xml_to_text.py`
**Lines:** 214-221 (current implementation)

**Replace with:**

```python
def _requires_quotes(self, prop_name: str) -> bool:
    """
    Check if property should always be quoted (even if numeric-looking).

    This handles properties where CBECC schema defines them as STRING type
    even though they may contain digits or look numeric.
    """
    # Properties that look like numbers but must be quoted (STRING fields in CBECC schema)
    always_quote = [
        # Author/document metadata (STRING fields)
        'DocAuthZipCode',      # Author ZIP - STRING (can have leading zeros)
        'DocAuthAddress',      # Author address
        'DocAuthCity',         # Author city
        'DocAuthState',        # Author state
        'DocAuthCompany',      # Author company

        # Location/weather (STRING fields)
        'StAddress',           # Street address
        'City',                # City name
        'State',               # State abbreviation
        'WeatherStation',      # Weather station name
        'WeatherFileName',     # Weather file name
        'DDWeatherFile',       # Design day weather file
        'AnnualWeatherFile',   # Annual weather file
        'AnnualWeatherFileNoPath',  # Weather file (no path)

        # Date/time strings (STRING fields)
        'RunDateFmt',          # Formatted date
        'RunDateISO',          # ISO date

        # Enum/choice properties (always quoted in CBECC)
        'Status',              # Component status (New, Existing, etc.)
        'DryerFuel',           # Dryer fuel type
        'CookingApplType',     # Cooking appliance type
        'CliZn',               # Climate zone (e.g., "ClimateZone12")
        'Orientation',         # Orientation (Front, Back, Left, Right)
        'GasType',             # Gas type (NaturalGas, Propane)
        'AnalysisType',        # Analysis type
        'SimSpeedOption',      # Simulation speed option

        # Exception conditions (enum fields)
        'ExcptCondNoClgSys',   # "Yes" or "No"
        'ExcptCondRtdCap',     # "Yes" or "No"
        'ExcptCondNarrative',  # "Yes" or "No"

        # Construction properties (STRING fields)
        'Type',                # Component type (generic enum)
        'CanAssignTo',         # Construction assignment type
        'MassLayer',           # Mass layer material name

        # HVAC properties (enum fields)
        'FanCtrlMthd',         # Fan control method
        'FuelType',            # Fuel type

        # Residential properties (enum fields)
        'InsulConsQuality',    # Insulation quality ("No", "Yes")
        'UnitClVentOption',    # Unit ventilation option

        # Special format strings
        'SoftwareVersion',     # Version string (e.g., "CBECC 2025.1.0 (1381)")
        'RunTitle',            # Run title
        'ResultsCurrentMessage',  # Results message

        # NOTE: 'ZipCode' is an INTEGER field - should NOT be quoted
    ]
    return prop_name in always_quote
```

**Verification:** Check that DocAuthZipCode is quoted and ZipCode is not.

---

### ✅ Task 3: Add Property Type Detection (Optional Enhancement)

**File:** `eco_tools/translators/cibd_xml_to_text.py`
**Insert after `_requires_quotes()` method**

```python
def _get_property_type(self, prop_name: str, prop_value: str) -> str:
    """
    Determine property type for quoting decisions.

    Returns: 'string', 'number', 'reference', or 'enum'
    """
    # Force-quoted properties (from _requires_quotes)
    if self._requires_quotes(prop_name):
        return 'string'

    # Reference properties (always quoted)
    if self._is_reference(prop_name):
        return 'reference'

    # Numeric properties (never quoted)
    if self._is_number(prop_value):
        return 'number'

    # Boolean-like keywords (quoted as enums)
    if prop_value and prop_value.lower() in ['true', 'false', 'yes', 'no']:
        return 'enum'

    # Default to string (quoted)
    return 'string'
```

**Purpose:** Centralize type detection logic for easier maintenance.

---

### ✅ Task 4: Update Property Writing Logic

**File:** `eco_tools/translators/cibd_xml_to_text.py`
**Lines:** 134-168 (current property writing)

**Update the elif chain to use type detection:**

```python
# Write properties
for prop_name, prop_value in properties:
    if prop_value is None:
        continue

    # Skip Name if it was used as object name
    if prop_name == 'Name' and obj_name == prop_value:
        continue

    # Skip properties that are defined as root attributes
    if hasattr(self, 'root_attributes') and prop_name in self.root_attributes:
        continue

    # Detect if this is a reference (array or single)
    array_match = re.match(r'(.+)\[(\d+)\]', prop_name)

    if array_match:
        # Array reference: MatRef[1] = "Material Name"
        base_name = array_match.group(1)
        index = array_match.group(2)
        output.write(f'{indent_str}   {base_name}[{index}] = "{prop_value}"\n')
    else:
        # Determine property type
        prop_type = self._get_property_type(prop_name, prop_value)

        if prop_type == 'number':
            # Numeric value (no quotes)
            output.write(f'{indent_str}   {prop_name} = {prop_value}\n')
        else:
            # String, reference, or enum (quoted)
            output.write(f'{indent_str}   {prop_name} = "{prop_value}"\n')
```

**Benefit:** Cleaner logic, easier to debug quoting issues.

---

### ✅ Task 5: Handle MassThickness Special Case

**File:** `eco_tools/translators/cibd_xml_to_text.py`
**In property writing section, add special handling**

```python
# Special case: MassThickness "8 in." → 8
if prop_name == 'MassThickness' and prop_value:
    # Parse "X in." to numeric value
    match = re.match(r'(\d+)\s*in\.?', prop_value, re.IGNORECASE)
    if match:
        prop_value = match.group(1)  # Extract just the number
```

**Insert this BEFORE the array_match check in the property writing loop.**

**Alternative:** Handle during XML import in `construction_parser.py` to store as integer.

---

## Testing Plan

### Test 1: Residential Building (Bressi Ranch)

```bash
# Export Bressi Ranch to CIBD25
python3 -c "
from eco_tools.translators.cibd22x import CIBD22XImporter
from eco_tools.translators.cibd25 import CIBD25Exporter

importer = CIBD22XImporter()
internal = importer.import_file('reference_data/cbecc/CBECC Models/Bressi Ranch/Bressi Ranch Apartments.cibd22x')

exporter = CIBD25Exporter()
exporter.export(internal, 'test_output/bressi_complete_test.cibd25')
"

# Verify HVAC objects present
grep -c "^ResHtPumpSys\|^ResFanSys\|^ResDistSys\|^ResDHWSys" test_output/bressi_complete_test.cibd25

# Expected: Count > 0 (at least 4-5 objects)

# Verify MassThickness is numeric
grep "MassThickness" test_output/bressi_complete_test.cibd25

# Expected: MassThickness = 8 (not "8 in.")

# Verify property quoting
grep "DocAuthZipCode\|ZipCode" test_output/bressi_complete_test.cibd25 | head -5

# Expected:
# DocAuthZipCode = "92868"  ← Quoted
# ZipCode = 92009           ← NOT quoted

# Test in CBECC 2025
"/Applications/CBECC 2025.app/Contents/MacOS/CBECC 2025" -nrp -b test_output/bressi_complete_test.cibd25

# Expected: "button returned:OK"
```

### Test 2: Verify Object Counts

```bash
# Count top-level residential HVAC objects
for type in ResHtgSys ResClgSys ResHtPumpSys ResDistSys ResFanSys ResIAQFan ResDHWSys ResWtrHtr; do
    count=$(grep -c "^$type " test_output/bressi_complete_test.cibd25)
    echo "$type: $count"
done
```

### Test 3: Verify References Resolve

```bash
# Check for missing references in CBECC log
"/Applications/CBECC 2025.app/Contents/MacOS/CBECC 2025" -nrp -b test_output/bressi_complete_test.cibd25 2>&1 | grep "not found"

# Expected: No "not found" errors (or count = 0)
```

---

## Validation Checklist

After implementation, verify:

- [ ] All 26+ object types extracted as top-level siblings
- [ ] ResHtPumpSys, ResFanSys, ResDistSys, etc. present in output
- [ ] DocAuthZipCode quoted, ZipCode not quoted
- [ ] MassThickness is numeric (not "8 in.")
- [ ] Enum properties (Status, DryerFuel, etc.) quoted
- [ ] CBECC 2025 loads file without errors
- [ ] No "component not found" reference errors
- [ ] File structure matches official CIBD25 samples

---

## Success Criteria

Export is complete when:

1. ✅ All residential HVAC catalog objects export as top-level
2. ✅ All construction catalog objects export as top-level
3. ✅ All HERS/compliance objects export as top-level
4. ✅ All property quoting follows schema rules
5. ✅ MassThickness exports as numeric value
6. ✅ CBECC 2025 opens file with "button returned:OK"
7. ✅ Zero "component not found" errors
8. ✅ Zero "invalid component type" errors

---

## Rollback Plan

If issues arise:

1. **Backup current implementation:**
   ```bash
   cp eco_tools/translators/cibd_xml_to_text.py eco_tools/translators/cibd_xml_to_text.py.backup
   ```

2. **Test incrementally:**
   - First: Add HVAC object types only
   - Second: Add construction catalog types
   - Third: Add HERS/report types
   - Fourth: Update quoting rules

3. **Validate after each step** before proceeding.

---

## Documentation Updates

After implementation, update:

1. **CIBD_FORMAT_DIFFERENCES_COMPREHENSIVE.md**
   - Mark all issues as resolved
   - Add final object type inventory

2. **CIBD_FORMAT_QUICK_REFERENCE.md**
   - Update status: CIBD25 export fully working

3. **CIBD25_EXPORT_ISSUES_JAN14.md**
   - Mark as resolved, reference this implementation

---

## Implementation Timeline

**Estimated:** 1 hour total

- **15 min:** Update `_is_top_level_sibling()` method
- **10 min:** Update `_requires_quotes()` method
- **10 min:** Add `_get_property_type()` method
- **5 min:** Update property writing logic
- **5 min:** Handle MassThickness special case
- **15 min:** Test with Bressi Ranch sample
- **10 min:** Verify in CBECC 2025
- **5 min:** Update documentation

---

## Next Steps

1. **Implement changes** to `cibd_xml_to_text.py` following this plan
2. **Test thoroughly** with residential buildings
3. **Validate** CBECC 2025 accepts output
4. **Document** any additional edge cases discovered
5. **Mark this task complete** and move to next priority

---

## Related Documentation

- **Complete Analysis:** `docs/CIBD25_EXPORT_COMPLETE_ANALYSIS.md`
- **Key Findings:** `docs/CIBD25_KEY_FINDINGS_SUMMARY.md`
- **Current Issues:** `docs/CIBD25_EXPORT_ISSUES_JAN14.md`
- **Format Comparison:** `docs/CIBD_FORMAT_DIFFERENCES_COMPREHENSIVE.md`

---

## Summary

**Problem:** Incomplete object type and property lists causing errors
**Solution:** Implement complete lists based on comprehensive analysis
**Benefit:** Single implementation fixes all current and future issues
**Effort:** ~1 hour vs. debugging errors indefinitely
**Status:** Ready to implement

This is a **planned, comprehensive fix** rather than a reactive debugging approach.
