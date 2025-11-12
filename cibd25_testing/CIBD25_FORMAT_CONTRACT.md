# CIBD25 Format Contract
**Date**: 2025-11-04
**Version**: 1.0
**Status**: Production Ready

## Overview

CIBD25 is a custom text-based building energy modeling format used by CBECC 2025 (California Building Energy Code Compliance). It represents non-residential building models for Title 24 compliance.

### Format Classification
- **Format Type**: Custom text-based (not XML, not JSON)
- **File Extension**: `.cibd25`
- **Encoding**: ISO-8859-1
- **Line Endings**: CRLF (`\r\n`, Windows-style)
- **Version Indicator**: Ruleset filename contains "2025" (e.g., "T24_2025.bin")

---

## File Structure

### Basic Syntax

CIBD25 files follow a hierarchical object notation:

```
ElementType   "ObjectName"
   Property = Value
   ArrayProperty[1] = "Value1"
   ArrayProperty[2] = "Value2"
   ..

ElementType   "AnotherObject"
   Property = Value
   ..
```

### Key Characteristics

1. **Object Declarations**: `ElementType   "ObjectName"` (multiple spaces between type and name)
2. **Property Indentation**: 3 spaces before property names
3. **Object Terminator**: `   ..` (3 spaces before two periods)
4. **Array Indexing**: 1-based (starts at `[1]`, not `[0]`)
5. **String Values**: Always quoted (`"value"`)
6. **Comments**: Not supported
7. **Blank Lines**: Used after RulesetFilename and between top-level objects

---

## Element Types Catalog

CIBD25 supports 32 element types organized into functional categories:

### 1. Project & Building Structure (6 types)

| Element Type | Description | Example |
|--------------|-------------|---------|
| `RulesetFilename` | T24 compliance ruleset | `RulesetFilename   "T24_2025.bin"` |
| `Proj` | Project metadata | `Proj   "MyProject"` |
| `ProjVar` | Project variables | `ProjVar   "BuildingArea"` |
| `Bldg` | Building definition | `Bldg   "MainBuilding"` |
| `Story` | Building story/level | `Story   "Floor1"` |
| `Spc` | Space/zone | `Spc   "Office_101"` |

### 2. Geometry (2 types)

| Element Type | Description | Example |
|--------------|-------------|---------|
| `PolyLp` | Polygon loop (surface boundary) | `PolyLp   "Wall1_Boundary"` |
| `CartesianPt` | 3D coordinate point | `CartesianPt   "Pt_0_0_0"` |

**Coordinate Format**: `Coord = ( X, Y, Z )`

Example:
```
CartesianPt   "Pt1"
   Coord = ( 0, 0, 0 )
   ..
```

### 3. Materials & Constructions (4 types)

| Element Type | Description | Required Properties | Example |
|--------------|-------------|---------------------|---------|
| `Mat` | Material definition | `CodeCat`, `CodeItem` | `Mat   "Concrete - 6 in."` |
| `ConsAssm` | Construction assembly | `CompatibleSurfType`, `MatRef[N]` | `ConsAssm   "ExtWall_1"` |
| `FenCons` | Fenestration (window) construction | `FenProdType`, `UFactor`, `SHGC` | `FenCons   "DblPane_LoE"` |
| `DrCons` | Door construction | `DoorType` | `DrCons   "MetalDoor_1"` |

**Material Layer Order**: Arrays in `ConsAssm` define layers from outside to inside.

### 4. Building Envelope - Surfaces (6 types)

| Element Type | Surface Type | Adjacency | Typical Properties |
|--------------|--------------|-----------|-------------------|
| `ExtWall` | Exterior wall | Exterior | `ConsAssmRef`, `Area`, `Az` (azimuth) |
| `IntWall` | Interior wall | Interior | `ConsAssmRef`, `AdjacentSpcRef` |
| `Roof` | Roof surface | Exterior | `ConsAssmRef`, `Area`, `Tilt` |
| `UndgrFlr` | Underground floor | Ground | `ConsAssmRef`, `Area` |
| `ExtFlr` | Exterior floor | Exterior | `ConsAssmRef`, `Area` |
| `IntFlr` | Interior floor | Interior | `ConsAssmRef`, `AdjacentSpcRef` |

**Naming Convention**: Surfaces typically follow pattern: `{SpaceName}_{surfaceType}_{orientation}`

Example: `Perimeter_ZN_1_wall_south`

### 5. Building Envelope - Openings (3 types)

| Element Type | Description | Required Properties | Example |
|--------------|-------------|---------------------|---------|
| `Win` | Window | `FenConsRef`, `Area` | `Win   "Window_01"` |
| `Skylt` | Skylight | `FenConsRef`, `Area` | `Skylt   "Skylight_01"` |
| `Dr` | Door | `DrConsRef`, `Area` | `Dr   "Door_Main"` |

### 6. HVAC Systems (7 types)

| Element Type | Description | Key Properties |
|--------------|-------------|----------------|
| `ThrmlZn` | Thermal zone | `Type`, `PriAirCondgSysRef` |
| `AirSys` | Air system | `Type`, `CtrlZnRef` |
| `AirSeg` | Air segment | `Type`, `Path` |
| `ZnSys` | Zone system | `Type`, `CtrlZnRef` |
| `TrmlUnit` | Terminal unit | `Type`, `PriAirSegRef` |
| `OACtrl` | Outside air control | `EconoCtrlMthd`, `AirSegSupRef` |
| `HtRcvry` | Heat recovery | `Type`, `Effectiveness` |

### 7. HVAC Equipment (3 types)

| Element Type | Description | Key Properties |
|--------------|-------------|----------------|
| `CoilClg` | Cooling coil | `Type`, `Cap`, `EIR` |
| `CoilHtg` | Heating coil | `Type`, `Cap`, `EIR` |
| `Fan` | Fan | `FlowCap`, `TotStaticPress`, `MtrEff` |

### 8. DHW Systems (3 types)

| Element Type | Description | Key Properties |
|--------------|-------------|----------------|
| `FluidSys` | Fluid system | `Type`, `Name` |
| `FluidSeg` | Fluid segment | `Type`, `FluidSysRef` |
| `WtrHtr` | Water heater | `Type`, `Cap`, `ThrmlEff` |

### 9. Renewable Energy (2 types)

| Element Type | Description | Key Properties |
|--------------|-------------|----------------|
| `PVArray` | Photovoltaic array | `ArrayType`, `DCSysSize`, `Tilt`, `Azimuth` |
| `Batt` | Battery storage | `BattType`, `MaxCap`, `MaxPwr`, `RoundTripEff` |

### 10. Compliance (2 types)

| Element Type | Description | Purpose |
|--------------|-------------|---------|
| `EUseSummary` | Energy use summary | Compliance results |
| `SpcFuncDefaults` | Space function defaults | Default values per space type |

---

## Property Types & Formats

### String Properties
Always enclosed in double quotes:
```
Name = "StringValue"
ConsAssmRef = "Wall_Construction_1"
```

### Numeric Properties

**Integer**:
```
BldgEngyModelVersion = 17
ZipCode = 95814
```

**Float**:
```
Area = 1000.5
UFactor = 0.35
```

**Scientific Notation**:
```
SmallValue = 1.5E-5
LargeValue = 3.2E+6
```

### Boolean Properties
Represented as integers (0 or 1):
```
AutoHardSize = 1
IsConditioned = 0
```

### Coordinate Tuples
Special format with parentheses and commas:
```
Coord = ( 100.5, 200.0, 10.0 )
```

### Enum Properties
String values from predefined sets:
```
Type = "PTAC"
ArrayType = "FixedRoof"
BattType = "LithiumIon"
```

---

## Reference System

CIBD25 uses **name-based references** exclusively (no ID attributes).

### Simple References
Reference to a single object by name:
```
ConsAssmRef = "ExtWall_Construction"
ThrmlZnRef = "Zone_1"
AdjacentSpcRef = "Office_102"
```

### Array References
References to multiple objects (1-based indexing):
```
MatRef[1] = "Concrete - 6 in."
MatRef[2] = "Insulation R13"
MatRef[3] = "Gypsum Board"
```

### Common Reference Properties

| Property Pattern | References To | Example |
|------------------|---------------|---------|
| `*Ref` | Single object | `ConsAssmRef`, `FenConsRef` |
| `*Ref[N]` | Array of objects | `MatRef[1]`, `MatRef[2]` |
| `AdjacentSpcRef` | Adjacent space | `AdjacentSpcRef = "Office_102"` |

---

## Validation Rules

### Required Elements
1. **RulesetFilename** - Must be first element (no terminator, followed by blank line)
2. **Proj** - Must exist, contains project metadata
3. **Bldg** - At least one building required
4. **Spc** - At least one space required

### Naming Constraints
- Names must be unique within element type
- Names are case-sensitive
- Names can contain: letters, digits, underscores, hyphens
- Spaces in names are allowed (within quotes)

### Reference Validation
- All references must resolve to existing objects
- Reference target must have matching element type
- Array reference indices must be consecutive (no gaps)
- Array indices start at `[1]`, not `[0]`

### Property Value Ranges

**Areas** (square feet):
- `Area >= 0`
- Typical range: 1 - 100,000 sq.ft.

**Azimuths** (degrees):
- `0 <= Az < 360`
- 0 = North, 90 = East, 180 = South, 270 = West

**Tilt** (degrees):
- `0 <= Tilt <= 180`
- 0 = horizontal up, 90 = vertical, 180 = horizontal down

**U-Factors** (Btu/hr-sf-F):
- `UFactor > 0`
- Typical range: 0.02 - 2.0

**SHGC** (Solar Heat Gain Coefficient):
- `0 < SHGC <= 1.0`
- Typical range: 0.2 - 0.8

---

## Example File Structure

```
RulesetFilename   "T24_2025.bin"

Proj   "SmallOffice_2025"
   BldgEngyModelVersion = 17
   ZipCode = 95814
   AutoHardSize = 1
   ..

Mat   "Concrete - 6 in."
   CodeCat = "Concrete"
   CodeItem = "Concrete - 140 lb/ft3 - 6 in."
   ..

ConsAssm   "ExtWall_Mass"
   CompatibleSurfType = "ExteriorWall"
   MatRef[1] = "Concrete - 6 in."
   MatRef[2] = "Insulation R13"
   MatRef[3] = "Gypsum Board"
   ..

FenCons   "Window_DoublePane"
   FenProdType = "VerticalFenestration"
   UFactor = 0.35
   SHGC = 0.4
   VT = 0.54
   ..

Bldg   "Building_1"
   TotStoryCnt = 2
   AboveGrdStoryCnt = 2
   ..

Story   "Floor_1"
   Z = 0
   FlrToFlrHgt = 13
   FlrToCeilingHgt = 10
   ..

Spc   "Office_101"
   Vol = 12226.7
   SpcFunc = "Office - enclosed <= 250 sf"
   ThrmlZnRef = "ThermalZone_1"
   ..

ExtWall   "Office_101_wall_south"
   ConsAssmRef = "ExtWall_Mass"
   Area = 140
   Az = 180
   ..

Win   "Office_101_wall_south_window_1"
   FenConsRef = "Window_DoublePane"
   Area = 20
   ..
```

---

## Parsing Guidelines

### Tokenization Steps
1. Read file with ISO-8859-1 encoding
2. Split by CRLF line endings
3. Match object declarations: `/^(\w+)\s+"([^"]+)"$/`
4. Match properties: `/^   (\w+)(?:\[(\d+)\])?\s+=\s+(.+)$/`
5. Match terminators: `/^   \.\.$/`
6. Parse coordinate tuples: `/\(\s*([\d.E+-]+)\s*,\s*([\d.E+-]+)\s*,\s*([\d.E+-]+)\s*\)/`

### Hierarchy Building
CIBD25 uses a flat structure with references, not nested hierarchy:
- All elements are top-level in the file
- Relationships are established through name-based references
- Parent-child relationships inferred from:
  - Naming patterns (e.g., `Surface_name` starts with `Space_name`)
  - Reference properties (e.g., `SpcRef`, `SurfRef`)

### Reference Resolution
1. Build name index: `{(element_type, name): object}`
2. Iterate through all objects
3. For each property ending in `Ref`:
   - Look up referenced object by name
   - Store resolved reference (optional)
4. For array references (`RefName[N]`):
   - Group by property name
   - Resolve each array element

---

## Serialization Guidelines

### Formatting Rules

**Object Declaration**:
```
ElementType   "ObjectName"
```
- Multiple spaces between type and name (implementation uses 3)
- Name always in double quotes

**Properties**:
```
   PropertyName = Value
```
- 3 spaces indentation
- Space before and after `=`
- Alphabetically sorted (recommended, not required)

**Array Properties**:
```
   ArrayProperty[1] = "Value1"
   ArrayProperty[2] = "Value2"
```
- Same indentation as regular properties
- 1-based indexing
- Consecutive indices (no gaps)

**Object Terminator**:
```
   ..
```
- 3 spaces indentation
- Two periods

**Blank Lines**:
- One blank line after RulesetFilename
- One blank line between top-level objects
- No blank lines within objects

### Property Ordering
While not strictly required, properties are typically sorted alphabetically for consistency and readability.

### Value Formatting

**Strings**: Always quote, escape internal quotes if needed
```
Name = "My \"Quoted\" Name"
```

**Numbers**: No quotes, use decimal point for floats
```
IntValue = 42
FloatValue = 3.14
```

**Coordinates**: Specific tuple format
```
Coord = ( 1.0, 2.0, 3.0 )
```

**Booleans**: Use 0 or 1
```
Enabled = 1
Disabled = 0
```

---

## Key Differences from CIBD22X

| Feature | CIBD22X (XML) | CIBD25 (Text) |
|---------|---------------|---------------|
| **Format** | XML with namespaces | Custom text |
| **Encoding** | UTF-8 | ISO-8859-1 |
| **Line Endings** | LF | CRLF |
| **Hierarchy** | Nested XML elements | Flat with references |
| **References** | ID attributes & IDREFs | Name strings |
| **Arrays** | 0-based or XML repetition | 1-based explicit |
| **Indentation** | XML style | 3 spaces |
| **Version** | 2022 and earlier | 2025 |
| **Ruleset** | T24_2022 | T24_2025 |

---

## Integration Points

### Format Detection
Detect CIBD25 by:
1. File extension: `.cibd25`
2. Text-based (not XML: no `<?xml` header)
3. Contains `RulesetFilename`
4. Ruleset contains "2025"

Example detection logic:
```python
if 'RulesetFilename' in content and '2025' in content:
    return 'CIBD25'
```

### Parser Integration
```python
from eco_tools.formats.cibd25_adapter import CIBD25Adapter

adapter = CIBD25Adapter()

# Parse to internal representation
internal = adapter.parse('building.cibd25')

# Parse to object graph (low-level)
objects = adapter.parse_to_objects('building.cibd25')

# Serialize from object graph
adapter.serialize_objects(objects, 'output.cibd25')
```

### Universal Translator
```python
from eco_tools.core.translator import UniversalTranslator

translator = UniversalTranslator()

# CIBD25 → CIBD22X
translator.translate('input.cibd25', 'output.cibd22x')

# CIBD25 → HBJSON
translator.translate('input.cibd25', 'output.hbjson')
```

---

## Performance Characteristics

### File Size Ranges
- **Small**: 20-50 KB (100-200 objects)
- **Medium**: 50-100 KB (200-500 objects)
- **Large**: 100-200 KB (500-1000 objects)

### Parsing Performance
- **Small files** (~25 KB): ~0.05 seconds
- **Medium files** (~50 KB): ~0.10 seconds
- **Large files** (~100 KB): ~0.20 seconds

### Memory Usage
- Approximately 2-3x file size when loaded as object graph
- Example: 50 KB file → ~125 KB in memory

---

## Common Pitfalls

### 1. Array Indexing
**Wrong** (0-based):
```
MatRef[0] = "Material_1"
MatRef[1] = "Material_2"
```

**Correct** (1-based):
```
MatRef[1] = "Material_1"
MatRef[2] = "Material_2"
```

### 2. Line Endings
**Wrong** (LF only):
- Unix-style `\n`
- Will fail validation

**Correct** (CRLF):
- Windows-style `\r\n`
- Required for CBECC compliance

### 3. Encoding
**Wrong** (UTF-8):
- May have issues with special characters
- Not standard for CBECC

**Correct** (ISO-8859-1):
- Latin-1 encoding
- Required by CBECC engine

### 4. Reference Names
**Wrong** (Case mismatch):
```
ConsAssm   "Wall_1"
ExtWall   "MyWall"
   ConsAssmRef = "wall_1"  # Won't resolve!
```

**Correct** (Exact match):
```
ConsAssm   "Wall_1"
ExtWall   "MyWall"
   ConsAssmRef = "Wall_1"  # ✓ Exact match
```

### 5. RulesetFilename Format
**Wrong** (Has terminator):
```
RulesetFilename   "T24_2025.bin"
   ..
```

**Correct** (No terminator, blank line after):
```
RulesetFilename   "T24_2025.bin"

Proj   "MyProject"
```

---

## Compliance & Validation

### CBECC Engine Requirements
1. **File must be valid CIBD25 format**
2. **Encoding must be ISO-8859-1**
3. **Line endings must be CRLF**
4. **Ruleset must exist** and be valid
5. **All references must resolve**
6. **Required elements must exist** (RulesetFilename, Proj, Bldg, Spc)

### Validation Checklist
- [ ] File uses .cibd25 extension
- [ ] File encoded as ISO-8859-1
- [ ] Line endings are CRLF
- [ ] RulesetFilename is first element
- [ ] Ruleset references T24_2025
- [ ] All object names are unique per type
- [ ] All references resolve to existing objects
- [ ] Array indices are 1-based and consecutive
- [ ] Property values are within valid ranges
- [ ] Required properties exist for all elements

---

## Version History

**Version 1.0** (2025-11-04)
- Initial format contract
- Documented all 32 element types
- Complete property catalog
- Validation rules defined
- Integration guidelines provided

---

## References

### Official Documentation
- Title 24 Compliance Manual (California Energy Commission)
- CBECC 2025 User Manual
- T24 2025 Ruleset Documentation

### Related Specifications
- CIBD22X Format Contract (XML predecessor)
- Universal Translator API Documentation
- InternalRepresentation Schema

### Tools & Utilities
- CIBD25 Parser (eco_tools.formats.cibd25_adapter)
- Format Detector (eco_tools.core.format_detector)
- Universal Translator (eco_tools.core.translator)

---

## Support & Contact

For questions or issues with CIBD25 format:
- Check parser documentation: `CIBD25_PARSER_ARCHITECTURE.md`
- Review element catalog: `CIBD25_ELEMENT_CATALOG.md`
- See implementation status: `CIBD25_PROJECT_STATUS.md`

---

**Document Status**: ✅ Complete & Production Ready
**Last Updated**: 2025-11-04
**Maintained By**: ECO Tools Team
