# CIBD25 Export - Key Findings Summary

## The Core Problem

We've been fixing CIBD25 export errors one-by-one (ResProj, DocAuthZipCode, ResHVAC). This is inefficient because the converter's sibling extraction list is **incomplete**.

## The Key Insight

**ALL residential catalog objects are top-level siblings in both XML and text formats.**

The XML file structure is misleading - catalog objects appear as children of `<Proj>` in XML **only for document organization**, but they should be written as **top-level siblings** in the text format, just like they are in the XML.

## What's Missing

The current `_is_top_level_sibling()` method only handles:
- ResProj
- ProjVar  
- DwellUnitType

But it needs to handle **50+ additional object types**:

### Residential HVAC Catalog (10 types)
- ResHtgSys, ResClgSys, ResHtPumpSys
- ResDistSys, ResFanSys, ResIAQFan
- ResDHWSys, ResWtrHtr, ResLpTankHtr
- ResCentralVentSys

### Residential Construction Catalog (3 types)
- ResConsAssm, ResMat, ResWinType

### HERS/Compliance (8 types)
- HERSCool, HERSHeat, HERSHtPump
- HERSDist, HERSFan, HERSDHWSys
- HERSOther, SpeclFtr

### Report Objects (5 types)
- ResDHWSysRpt, DwellUnitRpt
- ResIAQVentRpt, ResSCSysRpt
- EUseSummary

## The Simple Fix

Instead of adding one object type at a time as we encounter errors, add them all at once:

```python
def _is_top_level_sibling(self, child_tag: str, parent_tag: str) -> bool:
    if parent_tag == 'Proj':
        # Project variants
        if child_tag in ['ResProj', 'ProjVar']:
            return True
        
        # Dwelling unit types
        if child_tag == 'DwellUnitType':
            return True
        
        # Residential HVAC catalog
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
        
        # HERS/compliance
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

## Property Quoting - Two Critical Rules

### Rule 1: ZipCode vs DocAuthZipCode

This is a schema-level distinction that CBECC enforces:

- **ZipCode** (building location) → INTEGER field → **unquoted**
- **DocAuthZipCode** (author ZIP) → STRING field → **quoted**

### Rule 2: Enum Properties Always Quoted

All enum/choice properties must be quoted, even if they look like simple values:

```python
# Always quoted (enums)
Status = "New"
DryerFuel = "Electricity"
CliZn = "ClimateZone12"
Orientation = "Front"
ExcptCondNoClgSys = "No"

# Never quoted (numbers)
ZipCode = 95814
Area = 1080.5
NumBedrooms = 2
```

The expanded `_requires_quotes()` method needs ~50 property names.

## Verification Evidence

From actual CIBD25 file (line 16130):
```
DwellUnitType   "Studio Type"     # Top-level at line 16090
   ...
   ..

ResHtgSys   "Heating Component - Res"     # Top-level at line 16130
   Type = "CntrlFurnace - Fuel-fired central furnace"
   AutoSize = 1
   ..

ResClgSys   "Cooling Component - Res"     # Top-level at line 16135
   ...
   ..

ResHtPumpSys   "Heat Pump System - Res"   # Top-level at line 16145
   ...
   ..
```

These are NOT nested under any parent - they're all at root indentation level (0).

## Implementation Effort

- **Expand sibling list:** 5 minutes
- **Expand quoting rules:** 10 minutes  
- **Add type detection:** 15 minutes
- **Testing:** 30 minutes

**Total: ~1 hour** for complete solution vs. fixing errors one-by-one indefinitely.

## Next Steps

1. Update `cibd_xml_to_text.py` with expanded lists (see full analysis document)
2. Test with Bressi Ranch sample file
3. Test with MF88 sample file
4. Validate CBECC accepts output files
5. Document any edge cases discovered

See `CIBD25_EXPORT_COMPLETE_ANALYSIS.md` for full implementation details.
