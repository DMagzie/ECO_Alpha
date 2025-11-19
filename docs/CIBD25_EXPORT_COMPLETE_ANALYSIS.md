# CIBD25 Export Implementation Plan - Complete Analysis

**Date:** 2025-11-14  
**Status:** Comprehensive Analysis Complete

## Executive Summary

After thorough analysis of official CIBD22X (XML) and CIBD25 (text) sample files, this document provides a complete specification of all structural differences, object type placements, and property quoting rules needed to implement proper CIBD25 export support.

**Key Finding:** The residential HVAC system objects (ResHtgSys, ResClgSys, ResHtPumpSys, ResDistSys, ResFanSys, ResIAQFan, ResDHWSys, ResWtrHtr, ResLpTankHtr) and catalog objects (DwellUnitType, ResConsAssm, ResMat, ResWinType, etc.) are **TOP-LEVEL siblings** in both XML and text formats, NOT nested under Proj.

---

## 1. Complete Object Type Inventory

### 1.1 Top-Level Objects (Root Siblings)

These appear as siblings to `<Proj>` in XML and top-level in text format:

#### Core Project Objects
- **RulesetFilename** - Attribute in XML root, top-level property in text
- **Proj** - Project metadata container
- **ProjVar** - Project variables (sibling extraction needed)
- **ResProj** - Residential project data (sibling extraction needed)

#### Building Hierarchy
- **Bldg** - Building container
- **Story** - Story/floor level
- **Spc** - Space (commercial)
- **ThrmlZn** - Thermal zone

#### Geometry Objects (Nested in Spc/Story)
- **PolyLp** - Polygon loop
- **CartesianPt** - Cartesian point
- **ExtWall** - Exterior wall
- **IntWall** - Interior wall
- **IntFlr** - Interior floor
- **Win** - Window
- **Dr** - Door

#### Residential Geometry (Nested in ResZn)
- **ResZnGrp** - Residential zone group container
- **ResZn** - Residential zone
- **ResOtherZn** - Other residential zone (corridors, stairs, etc.)
- **ResExtWall** - Residential exterior wall
- **ResIntWall** - Residential interior wall
- **ResIntFlr** - Residential interior floor
- **ResSlabFlr** - Residential slab floor
- **ResUndgrFlr** - Residential underground floor
- **ResUndgrWall** - Residential underground wall
- **ResCathedralCeiling** - Cathedral ceiling
- **ResWin** - Residential window
- **ResDr** - Residential door
- **ResOpening** - Residential opening
- **DwellUnit** - Dwelling unit instance (nested in ResZn)

#### **CRITICAL: Residential HVAC Systems (TOP-LEVEL)**
These are **TOP-LEVEL** catalog objects, NOT nested in ResProj or Proj:

- **ResHtgSys** - Residential heating system
- **ResClgSys** - Residential cooling system
- **ResHtPumpSys** - Residential heat pump system
- **ResDistSys** - Residential distribution system
- **ResFanSys** - Residential fan system
- **ResIAQFan** - Residential IAQ fan
- **ResDHWSys** - Residential DHW system
- **ResWtrHtr** - Residential water heater
- **ResLpTankHtr** - Residential loop tank heater
- **ResCentralVentSys** - Residential central ventilation system

#### Residential Catalog Objects (TOP-LEVEL)
- **DwellUnitType** - Dwelling unit type definition
- **ResConsAssm** - Residential construction assembly
- **ResMat** - Residential material
- **ResWinType** - Residential window type

#### Commercial HVAC Systems (TOP-LEVEL)
- **AirSys** - Air system
- **AirSeg** - Air segment (nested in AirSys)
- **CoilClg** - Cooling coil (nested in AirSys)
- **CoilHtg** - Heating coil (nested in AirSys)
- **Fan** - Fan (nested in AirSys)
- **OACtrl** - Outside air control (nested in AirSys)
- **TrmlUnit** - Terminal unit (nested in AirSys)
- **FluidSys** - Fluid system
- **FluidSeg** - Fluid segment (nested in FluidSys)
- **Pump** - Pump (nested in FluidSys)
- **Blr** - Boiler (nested in FluidSys)
- **WtrHtr** - Water heater

#### Commercial Catalog Objects (TOP-LEVEL)
- **ConsAssm** - Construction assembly
- **Mat** - Material
- **FenCons** - Fenestration construction
- **SpcFuncDefaults** - Space function defaults

#### Schedules (TOP-LEVEL)
- **SchDay** - Day schedule

#### Renewable Energy (TOP-LEVEL)
- **PVArray** - Photovoltaic array
- **Batt** - Battery storage

#### HERS/Compliance Objects (TOP-LEVEL)
- **HERSCool** - HERS cooling
- **HERSHeat** - HERS heating
- **HERSHtPump** - HERS heat pump
- **HERSDist** - HERS distribution
- **HERSFan** - HERS fan
- **HERSDHWSys** - HERS DHW system
- **HERSOther** - HERS other
- **SpeclFtr** - Special features

#### Report Objects (TOP-LEVEL)
- **ResDHWSysRpt** - Residential DHW system report
- **DwellUnitRpt** - Dwelling unit report
- **ResIAQVentRpt** - Residential IAQ ventilation report
- **ResSCSysRpt** - Residential space conditioning system report
- **EUseSummary** - End use summary

---

## 2. Structural Transformation Rules

### 2.1 Sibling Extraction Pattern

**Elements that appear as children of `<Proj>` in XML but should be TOP-LEVEL siblings in text:**

1. **ResProj** - Extract from `<Proj>` to top-level
2. **ProjVar** - Extract from `<Proj>` to top-level  
3. **DwellUnitType** - Extract from `<Proj>` to top-level (already correctly handled)

**Current Implementation Gap:**
The converter currently only handles ResProj and ProjVar. It does NOT handle the following catalog objects which are also XML children of `<Proj>` but should be top-level:

- ResHtgSys, ResClgSys, ResHtPumpSys (HVAC catalog)
- ResDistSys, ResFanSys, ResIAQFan (distribution/ventilation catalog)
- ResDHWSys, ResWtrHtr, ResLpTankHtr (DHW catalog)
- ResConsAssm, ResMat, ResWinType (construction catalog)
- All HERS objects
- All Report objects

### 2.2 Nesting Rules

**Objects that REMAIN nested (children in both XML and text):**

#### In Proj:
- Bldg

#### In Bldg:
- ResZnGrp (residential buildings)
- Story (commercial buildings)

#### In Story:
- Spc
- ThrmlZn

#### In Spc:
- PolyLp, ExtWall, IntWall, IntFlr, Win, Dr

#### In ResZnGrp:
- ResZn, ResOtherZn

#### In ResZn/ResOtherZn:
- ResExtWall, ResIntWall, ResIntFlr, ResSlabFlr, ResUndgrFlr, ResUndgrWall
- ResCathedralCeiling, ResWin, ResDr, ResOpening
- DwellUnit (unit instance, NOT DwellUnitType)

#### In ResExtWall:
- ResWin, ResDr

#### In AirSys:
- AirSeg, CoilClg, CoilHtg, Fan, OACtrl, TrmlUnit

#### In FluidSys:
- FluidSeg, Pump, Blr

#### In Geometry Objects (PolyLp, ExtWall, etc.):
- PolyLp (polygon loop)
- CartesianPt (within PolyLp)

---

## 3. Property Quoting Rules

### 3.1 Always Quote (STRING type in schema)

**Properties that MUST be quoted even if they look numeric:**

1. **DocAuthZipCode** - STRING field (author ZIP code)
2. **StAddress** - Street address
3. **City** - City name
4. **State** - State abbreviation
5. **DocAuthAddress** - Document author address
6. **DocAuthCity** - Document author city
7. **DocAuthState** - Document author state
8. **WeatherStation** - Weather station name
9. **WeatherFileName** - Weather file name
10. **RunDateFmt** - Formatted date string
11. **RunDateISO** - ISO date string
12. **RunTitle** - Run title
13. **SoftwareVersion** - Software version string
14. **ProjFileName** - Project file name
15. **ResultsCurrentMessage** - Results message
16. **AnalysisType** - Analysis type enum
17. **GasType** - Gas type enum
18. **CliZn** - Climate zone (e.g., "ClimateZone12")
19. **Type** properties - Most are enums (quoted)
20. **Status** properties - Enums like "New", "Existing"
21. **Orientation** - Cardinal directions ("Front", "Back", "Left", "Right")
22. **Construction** - Construction assembly reference
23. **Outside** - Adjacent space reference
24. **HVACSysType** - HVAC system type description
25. **IAQOption** - IAQ option type
26. **CompactDistrib** - Compact distribution type
27. **DHWSystemType** - DHW system type
28. **DHWAmbientCond** - DHW ambient condition
29. **DHWSolFracType** - DHW solar fraction type
30. **DryerFuel**, **CookFuel** - Fuel type enums
31. **ExcptCondNoClgSys**, **ExcptCondRtdCap**, **ExcptCondNarrative** - Exception enums ("Yes"/"No")

### 3.2 Never Quote (Numeric types)

**Properties that should NEVER be quoted:**

1. **ZipCode** - INTEGER field (building ZIP code) - different from DocAuthZipCode!
2. **BldgEngyModelVersion** - Integer
3. **CreateDate**, **ModDate**, **RunDate** - Unix timestamps (integers)
4. **Area** - Float
5. **Volume**, **Vol** - Float
6. **CeilingHeight**, **FloorHeight** - Float
7. **NumBedrooms** - Integer
8. **CondFlrArea** - Float
9. **Count** - Integer
10. **TreeState** - Integer (bit flags)
11. **BldgAz** - Float (azimuth)
12. **Z** - Float (elevation)
13. **FlrToFlrHgt**, **FlrToCeilingHgt** - Float
14. **Bottom** - Float
15. **NumStories** - Integer
16. **OrientationValue** - Float (degrees)
17. **Tilt** - Float
18. **FloorZ** - Float
19. **DepthBelowGrade** - Float
20. **TotStoryCnt**, **AboveGrdStoryCnt** - Integer
21. **UseExcptDsgnModel**, **AutoHardSize**, **AutoEffInput** - Integer (0/1 boolean)
22. **All Coord tuples** - e.g., `Coord = ( 101, 155, 0 )` - numeric tuples
23. **All array properties with numeric values** - e.g., `Hr = ( 0.023, 0.019, ... )`
24. **IAQCFM**, **WperCFMIAQ** - Float
25. **AutoSize** - Integer (0/1)
26. **HSPF2**, **SEER2**, **Cap17**, **Cap47** - Float

### 3.3 Reference Properties (Always Quote)

**Properties ending in Ref or containing references:**

- All properties ending in `Ref` - e.g., "ThrmlZnRef", "ConsAssmRef", "AdjacentSpcRef"
- All properties ending in `Type` when referring to catalog object
- Array references like `DHWSysRef[1] = "DHW Heat Pump"`

### 3.4 Mixed Arrays

**Array properties with quoted elements:**
```
IAQFanRef[1] = "1-Bed IAQ Fan"
DHWSysRef[1] = "DHW Heat Pump"
SCSysRptRef[1] = "F5 Studio SW Court | :Heat Pump System - Res:..."
ApplRefrigZone[1] = "F2 Res Zn E Court"
```

**Array properties with unquoted numeric elements:**
```
Coord = ( 101, 155, 0 )
Hr = ( 0.023, 0.019, 0.015, ... )
PVWDCSysSize = ( 0, 0, 0, 0, 0 )
IAQFanCnt = ( 1, 1, 1, 1 )
HeaterMult = ( 1, 1, 1, 1 )
```

---

## 4. Implementation Checklist

### 4.1 Current cibd_xml_to_text.py Issues

**Issue 1: Incomplete Sibling Extraction**
- Currently extracts: ResProj, ProjVar, DwellUnitType
- Missing: ALL catalog objects (ResHVAC, ResConsAssm, ResMat, ResWinType, HERS, Reports)

**Issue 2: Insufficient Property Quoting Rules**
- Currently has: DocAuthZipCode (good!)
- Missing: All string enums, fuel types, status fields, orientation, etc.

**Issue 3: No Type Detection Logic**
- No enum detection
- No reference property detection pattern
- No comprehensive type mapping

### 4.2 Required Fixes

#### Fix 1: Expand `_is_top_level_sibling()` method

```python
def _is_top_level_sibling(self, child_tag: str, parent_tag: str) -> bool:
    """
    Check if an element should be written as a top-level sibling.
    
    In CIBD XML, many catalog and system objects are nested inside Proj
    for document structure, but in CIBD text format they should be 
    top-level siblings.
    """
    if parent_tag == 'Proj':
        # Project variants
        if child_tag in ['ResProj', 'ProjVar']:
            return True
        
        # Dwelling unit types (catalog)
        if child_tag == 'DwellUnitType':
            return True
        
        # Residential HVAC catalog objects
        if child_tag in [
            'ResHtgSys', 'ResClgSys', 'ResHtPumpSys',
            'ResDistSys', 'ResFanSys', 'ResIAQFan',
            'ResDHWSys', 'ResWtrHtr', 'ResLpTankHtr',
            'ResCentralVentSys'
        ]:
            return True
        
        # Residential construction catalog
        if child_tag in ['ResConsAssm', 'ResMat', 'ResWinType']:
            return True
        
        # HERS/compliance objects
        if child_tag in [
            'HERSCool', 'HERSHeat', 'HERSHtPump',
            'HERSDist', 'HERSFan', 'HERSDHWSys',
            'HERSOther', 'SpeclFtr'
        ]:
            return True
        
        # Report objects
        if child_tag in [
            'ResDHWSysRpt', 'DwellUnitRpt',
            'ResIAQVentRpt', 'ResSCSysRpt',
            'EUseSummary'
        ]:
            return True
    
    return False
```

#### Fix 2: Expand `_requires_quotes()` method

```python
def _requires_quotes(self, prop_name: str) -> bool:
    """
    Check if property should always be quoted (even if numeric-looking).
    
    These are STRING fields in the CBECC schema that must be quoted.
    """
    # String fields that might look numeric
    always_quote = [
        'DocAuthZipCode',  # Author ZIP - STRING (vs ZipCode which is INTEGER)
        'CliZn',           # Climate zone - STRING like "ClimateZone12"
    ]
    
    # String address/location fields
    address_fields = [
        'StAddress', 'City', 'State',
        'DocAuthAddress', 'DocAuthCity', 'DocAuthState',
        'WeatherStation', 'WeatherFileName',
    ]
    
    # String descriptive fields
    string_fields = [
        'RunDateFmt', 'RunDateISO', 'RunTitle',
        'SoftwareVersion', 'ProjFileName',
        'ResultsCurrentMessage', 'Address',
    ]
    
    # Enum fields (always strings)
    enum_fields = [
        'AnalysisType', 'GasType', 'Status',
        'Orientation', 'Type', 'SpcFunc', 'VentSpcFunc',
        'HVACSysType', 'IAQOption', 'IAQFanType',
        'CompactDistrib', 'DHWSystemType',
        'DHWAmbientCond', 'DHWSolFracType',
        'DryerFuel', 'CookFuel', 'WasherOption', 'DryerOption',
        'ExcptCondNoClgSys', 'ExcptCondRtdCap', 'ExcptCondNarrative',
        'HeaterElementType', 'TankType', 'HPWHCategory',
        'BackupOption', 'VCHPDucts', 'Surface',
        'EffMetric', 'ACCharge', 'RefrigerantType',
        'CentralRecircType', 'CentralDHWType',
        'CHPWHSysDescrip', 'CHPWHIntegPkgType', 'CHPWHCompType',
        'CHPWHLoopTankConfig', 'CHPWHLoopTankType',
        'BranchLossModel', 'SolFracType', 'DemRespControl',
        'SimSpeedOption', 'InsulConsQuality', 'UnitClVentOption',
        'GeometryInpType', 'SpecMethod', 'Exception',
    ]
    
    # Construction/material references (always strings)
    if 'Construction' in prop_name or 'ConsAssm' in prop_name:
        return True
    
    # Outside/adjacent references
    if prop_name in ['Outside', 'AdjacentSpcRef', 'OtherSideModeled']:
        return True
    
    # Combine all lists
    all_string_props = (
        always_quote + address_fields + 
        string_fields + enum_fields
    )
    
    return prop_name in all_string_props
```

#### Fix 3: Enhance `_is_reference()` method

```python
def _is_reference(self, prop_name: str) -> bool:
    """
    Check if property name indicates a reference to another object.
    """
    # Properties ending in Ref are references
    if prop_name.endswith('Ref'):
        return True
    
    # Properties ending in Type that reference catalog objects
    if prop_name.endswith('Type') and prop_name not in [
        'Type',  # Object type itself
        'TankType', 'HeaterElementType',  # Enum types, not references
    ]:
        return True
    
    # Zone/space references
    zone_refs = [
        'Zone', 'Space', 'ThrmlZnRef', 'SpcRef',
        'ZnServedRef', 'CtrlZnRef', 'CHPWHTankZone',
        'CHPWHLoopTankZone', 'TankZone',
    ]
    if any(ref in prop_name for ref in zone_refs):
        return True
    
    # System references
    system_refs = [
        'System', 'Schedule', 'Bldg', 'Story',
        'HERSCheck', 'HERSHtPumpRef', 'HERSDist',
        'HERSFan', 'HERSDHW', 'HERSProj',
    ]
    if any(ref in prop_name for ref in system_refs):
        return True
    
    # Surface/window/door references
    surface_refs = ['Surface', 'Window', 'Door', 'Win', 'Dr']
    if any(ref in prop_name for ref in surface_refs):
        return True
    
    return False
```

#### Fix 4: Add Property Type Detection

```python
def _get_property_type(self, prop_name: str, prop_value: str) -> str:
    """
    Determine the type of a property value.
    
    Returns: 'INTEGER', 'FLOAT', 'STRING', 'REFERENCE', 'ARRAY'
    """
    # Check for array syntax
    if prop_value and prop_value.startswith('(') and prop_value.endswith(')'):
        return 'ARRAY'
    
    # Check if it's a reference
    if self._is_reference(prop_name):
        return 'REFERENCE'
    
    # Check if it must be quoted
    if self._requires_quotes(prop_name):
        return 'STRING'
    
    # Check if it's numeric
    if self._is_number(prop_value):
        # Distinguish integer from float
        try:
            if '.' in prop_value or 'e' in prop_value.lower():
                return 'FLOAT'
            else:
                return 'INTEGER'
        except:
            return 'INTEGER'
    
    # Check for boolean-like keywords
    if prop_value and prop_value.lower() in ['true', 'false', 'yes', 'no']:
        return 'STRING'
    
    # Default to string
    return 'STRING'
```

#### Fix 5: Update `_write_object()` Property Writing

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
    
    # Detect if this is an array reference
    array_match = re.match(r'(.+)\[(\d+)\]', prop_name)
    
    if array_match:
        # Array reference: MatRef[1] = "Material Name"
        base_name = array_match.group(1)
        index = array_match.group(2)
        output.write(f'{indent_str}   {base_name}[{index}] = "{prop_value}"\n')
    else:
        # Determine property type
        prop_type = self._get_property_type(prop_name, prop_value)
        
        if prop_type == 'ARRAY':
            # Array values: keep as-is (may contain commas, parens)
            output.write(f'{indent_str}   {prop_name} = {prop_value}\n')
        elif prop_type in ['REFERENCE', 'STRING']:
            # Quote references and strings
            output.write(f'{indent_str}   {prop_name} = "{prop_value}"\n')
        elif prop_type in ['INTEGER', 'FLOAT']:
            # No quotes for numbers
            output.write(f'{indent_str}   {prop_name} = {prop_value}\n')
        else:
            # Fallback: quote it to be safe
            output.write(f'{indent_str}   {prop_name} = "{prop_value}"\n')
```

---

## 5. Testing Strategy

### 5.1 Unit Tests

Create unit tests for each component:

1. **Test sibling extraction:**
   - Verify all catalog objects are extracted to top-level
   - Verify nested objects remain nested

2. **Test property quoting:**
   - Test all STRING fields are quoted
   - Test all numeric fields are unquoted
   - Test ZipCode vs DocAuthZipCode distinction
   - Test enum fields are quoted

3. **Test reference detection:**
   - Test all Ref properties are quoted
   - Test catalog object references
   - Test zone/space references

4. **Test array handling:**
   - Test numeric arrays (unquoted)
   - Test string arrays (quoted)
   - Test indexed references

### 5.2 Integration Tests

1. **Round-trip test:**
   - Convert XML → Text → (parse with CBECC)
   - Verify CBECC accepts the file
   - Compare simulation results

2. **Sample file tests:**
   - Test Bressi Ranch conversion
   - Test MF88 conversion
   - Test commercial building conversion

3. **Edge cases:**
   - Empty properties
   - Special characters in strings
   - Very long strings
   - Unicode characters

### 5.3 Validation Checklist

For each test file, verify:

- [ ] RulesetFilename at top
- [ ] Proj, ProjVar, ResProj as siblings
- [ ] All DwellUnitType objects at top-level
- [ ] All ResHVAC objects at top-level (NOT nested in Proj)
- [ ] All catalog objects at top-level
- [ ] All HERS objects at top-level
- [ ] DocAuthZipCode is quoted
- [ ] ZipCode is NOT quoted
- [ ] All enum fields are quoted
- [ ] All numeric fields are unquoted
- [ ] All reference fields are quoted
- [ ] Array syntax preserved correctly
- [ ] Geometry hierarchy correct (PolyLp → CartesianPt)
- [ ] HVAC hierarchy correct (AirSys → AirSeg → Coil/Fan)
- [ ] Object terminators (..) present and correctly indented

---

## 6. Critical Patterns Summary

### Pattern 1: XML to Text Structure Mapping

**XML:**
```xml
<SDDXML>
  <RulesetFilename file="T24_2025.bin"/>
  <Proj>
    <Name>Project Name</Name>
    <ResProj>...</ResProj>        <!-- Child of Proj in XML -->
    <DwellUnitType>...</DwellUnitType>  <!-- Child of Proj in XML -->
  </Proj>
  <ResHtPumpSys>...</ResHtPumpSys>  <!-- Sibling of Proj in XML -->
  <ResDHWSys>...</ResDHWSys>        <!-- Sibling of Proj in XML -->
</SDDXML>
```

**Text:**
```
RulesetFilename   "T24_2025.bin"

Proj   "Project Name"
   ...
   ..

ResProj   "..."         # Sibling in text (extracted)
   ...
   ..

DwellUnitType   "..."   # Sibling in text (extracted)
   ...
   ..

ResHtPumpSys   "..."    # Sibling in text (already sibling in XML)
   ...
   ..

ResDHWSys   "..."       # Sibling in text (already sibling in XML)
   ...
   ..
```

### Pattern 2: Property Quoting

```
# Always unquoted (INTEGER/FLOAT)
ZipCode = 95814
BldgEngyModelVersion = 17
Area = 1080.5

# Always quoted (STRING/ENUM)
DocAuthZipCode = "92868"
CliZn = "ClimateZone12"
Status = "New"
DryerFuel = "Electricity"
ExcptCondNoClgSys = "No"

# References (always quoted)
ThrmlZnRef = "Thermal Zone: F1 Retail N-NW"
ConsAssmRef = "Res Exterior Wall Cons"
DHWSysRef[1] = "DHW Heat Pump"
```

### Pattern 3: Nested vs Top-Level Decision Tree

```
Is object type in top_level_sibling list?
├─ YES → Write at root level (indent=0)
└─ NO  → Is parent one of: Proj, Bldg, Story, Spc, ResZnGrp, ResZn, AirSys, FluidSys?
        ├─ YES → Write as nested child (indent=parent_indent+1)
        └─ NO  → ERROR: unexpected nesting
```

---

## 7. Implementation Priority

### Phase 1 (Critical - Fixes Current Errors)
1. Add all ResHVAC objects to sibling extraction
2. Add ResConsAssm, ResMat, ResWinType to sibling extraction
3. Expand property quoting rules for common enums

### Phase 2 (Complete Coverage)
4. Add all HERS objects to sibling extraction
5. Add all Report objects to sibling extraction
6. Add comprehensive enum detection

### Phase 3 (Robustness)
7. Add property type detection logic
8. Add validation/error checking
9. Add round-trip testing

---

## 8. Known Edge Cases

1. **ZipCode vs DocAuthZipCode:**
   - ZipCode (building) is INTEGER → unquoted
   - DocAuthZipCode (author) is STRING → quoted

2. **Type property:**
   - Object type enums → quoted
   - Some are empty strings in XML → becomes `Type = ""`

3. **Array properties:**
   - Can contain numeric or string values
   - Must detect element type, not array itself

4. **Index notation:**
   - XML: `<DHWSysRef index="0">value</DHWSysRef>`
   - Text: `DHWSysRef[1] = "value"` (1-indexed in text!)

5. **Coordinate tuples:**
   - Always unquoted: `Coord = ( 101, 155, 0 )`
   - No commas outside parentheses

---

## Conclusion

The key insight is that **residential catalog objects are siblings, not children**. The current converter's architecture is sound, but its sibling extraction list is incomplete. By expanding the `_is_top_level_sibling()` method to include all catalog and system objects, and enhancing property quoting rules to cover all enum/string fields, we can achieve complete CIBD25 export support.

The implementation is straightforward:
- Expand one list (sibling objects)
- Expand another list (quoted properties)  
- Add type detection logic
- Test thoroughly

This avoids the inefficient one-by-one error fixing approach and provides a complete, maintainable solution.
