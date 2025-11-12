# CIBD25 Format - Initial Analysis
**Date**: 2025-11-04
**Status**: Discovery Phase

## Critical Discovery

**CIBD25 (.cibd25) is NOT XML format!**

Unlike CIBD22X which uses standard XML, CIBD25 uses a completely different custom text-based format.

---

## Format Characteristics

### File Type
- **Extension**: `.cibd25`
- **Encoding**: ISO-8859 text
- **Line Endings**: CRLF (Windows-style)
- **Format**: Custom property list / object notation
- **NOT**: XML, JSON, or any standard format

### Syntax Pattern

**Object Declaration**:
```
ElementType   "ObjectName"
   Property1 = Value1
   Property2 = Value2
   ArrayProp[1] = "Element1"
   ArrayProp[2] = "Element2"
   ..
```

**Key Syntax Rules**:
1. Object declaration: `ElementType   "Name"` (multiple spaces between)
2. Properties indented with 3 spaces
3. String values in double quotes
4. Numbers without quotes
5. Arrays use 1-based indexing: `[1]`, `[2]`, `[3]`
6. Object terminator: `..` (two dots on separate line)

---

## Structure Examples

### Root Level
```
RulesetFilename   "T24_2025.bin"

Proj   "020012-OffSml-CECStd25"
   BldgEngyModelVersion = 17
   CreateDate = 1414951358
   ModDate = 1750731527
   RunDate = 1750731528
   ZipCode = 95814
   AutoHardSize = 1
   ..
```

### Material Definition
```
Mat   "Concrete - 140 lb/ft3 - 6 in."
   CodeCat = "Concrete"
   CodeItem = "Concrete - 140 lb/ft3 - 6 in."
   ..
```

### Construction Assembly with Array References
```
ConsAssm   "Base_CZ12-NonresMetalFrameWallU055"
   CompatibleSurfType = "ExteriorWall"
   MatRef[1] = "Stucco - 7/8 in."
   MatRef[2] = "Compliance Insulation R14.60"
   MatRef[3] = "Compliance Insulation R1.41"
   MatRef[4] = "Compliance Insulation R0.02"
   MatRef[5] = "Compliance Insulation R0.02"
   MatRef[6] = "Air - Metal Wall Framing - 16 or 24 in. OC"
   MatRef[7] = "Gypsum Board - 1/2 in."
   ..
```

### Building Structure
```
Bldg   "Small Office"
   [properties...]
   ..

Story   "Building Story 1"
   [properties...]
   ..

Spc   "Perimeter_ZN_1"
   [properties...]
   ..
```

### Geometry (PolyLoop, CartesianPt)
```
PolyLp   "PolyLoop 25"
   [properties...]
   ..

CartesianPt   "CartesianPoint 100"
   [coordinates...]
   ..
```

---

## Key Differences from CIBD22X

### Fundamental Format
| Aspect | CIBD22X | CIBD25 |
|--------|---------|--------|
| Format | XML | Custom text |
| Hierarchy | XML tags | Indentation |
| Attributes | XML attributes | Properties |
| Arrays | Multiple elements | Indexed properties |
| Parsing | XML parser | Custom parser |

### Naming Conventions
| Element Type | CIBD22X Tag | CIBD25 Type |
|--------------|-------------|-------------|
| Material | `<ResMat>` or `<Mat>` | `Mat` |
| Construction | `<ResCons>` | `ConsAssm` |
| Window | `<ResWinType>` | `FenCons` |
| Building | `<SDDXML>` root | `Bldg` |
| Story | `<Story>` | `Story` |
| Space/Zone | `<ResZn>` | `Spc` |
| Geometry | XML elements | `PolyLp`, `CartesianPt` |

### Array Indexing
- **CIBD22X**: 0-based (`index="0"`, `index="1"`)
- **CIBD25**: 1-based (`[1]`, `[2]`, `[3]`)

### Reference Pattern
- **CIBD22X**: Both ID-based and Name-based references
- **CIBD25**: Appears to be Name-based only (TBD - needs more analysis)

---

## Implications for Universal Translator

### Current Status
**V7 Universal Translator is XML-based and cannot parse CIBD25 files.**

The CIBD22X adapter uses ElementTree (XML parser), which is fundamentally incompatible with the CIBD25 text format.

### Required Changes

#### Option 1: Separate CIBD25 Adapter (RECOMMENDED)
**Pros**:
- Clean separation of concerns
- No risk to existing CIBD22X functionality
- Different parsing strategies for different formats

**Implementation**:
1. Create new `cibd25_adapter.py`
2. Implement custom parser for CIBD25 text format
3. Map CIBD25 objects to same InternalRepresentation
4. Reuse serialization logic where possible
5. Format detector chooses adapter based on file extension or content

**Structure**:
```
eco_tools/formats/
├── cibd22x_adapter.py  (existing, XML-based)
├── cibd25_adapter.py   (new, custom text parser)
├── cibd22_adapter.py   (if needed for older format)
└── format_detector.py  (updated to detect all formats)
```

#### Option 2: Unified Adapter with Format Switching
**Pros**:
- Single adapter file
- Potentially shared code

**Cons**:
- Complex conditional logic
- Risk of breaking existing CIBD22X support
- Harder to maintain

**NOT RECOMMENDED** due to fundamental format differences.

---

## Parsing Strategy for CIBD25

### Lexer/Tokenizer Approach

**Phase 1: Tokenization**
- Read line by line
- Identify tokens:
  - Object declaration (`ElementType   "Name"`)
  - Property assignment (`   Property = Value`)
  - Array property (`   Property[N] = Value`)
  - Object terminator (`   ..`)

**Phase 2: Object Building**
- Track indentation level
- Build object hierarchy
- Store properties in dictionaries
- Handle array properties as lists

**Phase 3: Reference Resolution**
- Collect all named objects
- Resolve property references by name
- Build object graph

### Example Parser Structure
```python
class CIBD25Adapter(FormatAdapter):
    def parse(self, file_path: str) -> InternalRepresentation:
        with open(file_path, 'r', encoding='iso-8859-1') as f:
            lines = f.readlines()

        objects = self._tokenize_and_parse(lines)
        internal = self._build_internal_representation(objects)
        return internal

    def _tokenize_and_parse(self, lines):
        current_object = None
        objects = []

        for line in lines:
            if self._is_object_declaration(line):
                current_object = self._parse_object_declaration(line)
                objects.append(current_object)
            elif self._is_property_assignment(line):
                prop, value = self._parse_property(line)
                current_object[prop] = value
            elif self._is_object_terminator(line):
                current_object = None

        return objects
```

---

## Next Steps

### Immediate Actions

1. **✅ COMPLETE: Initial format analysis**
2. **IN PROGRESS: Detailed structure analysis**
   - Parse entire CIBD25 file manually
   - Document all element types
   - Document all property types
   - Identify geometry representation

3. **TODO: Design CIBD25 adapter architecture**
   - Define parser classes
   - Define object model
   - Map to InternalRepresentation

4. **TODO: Implement CIBD25 parser**
   - Tokenizer/lexer
   - Object parser
   - Reference resolver

5. **TODO: Implement CIBD25 serializer**
   - Object writer
   - Property formatter
   - Indentation handler

6. **TODO: Test and validate**
   - Parse all 5 sample files
   - Roundtrip validation
   - Compare with CBECC 2025 output

7. **TODO: Create CIBD25 format contract**
   - Complete syntax specification
   - Element catalog
   - Property types
   - Reference patterns

---

## Sample Files Available

1. `01_SmallOffice.cibd25` (47 KB) - Office building
2. `02_SmallRestaurant.cibd25` (26 KB) - Restaurant
3. `03_Warehouse.cibd25` (112 KB) - Industrial
4. `04_MediumOffice.cibd25` (79 KB) - Office building
5. `05_LargeRetail.cibd25` (175 KB) - Retail store

**Total Size Range**: 26 KB to 175 KB
**Building Types**: Office, restaurant, warehouse, retail

---

## Complexity Assessment

### Parser Implementation: MODERATE TO HIGH
- Custom text format (not standard)
- Indentation-based hierarchy
- Array notation
- Multiple property types
- Reference resolution

**Estimated Effort**: 16-24 hours
- Parser design: 2-3 hours
- Tokenizer implementation: 3-4 hours
- Object parser: 4-6 hours
- Reference resolution: 2-3 hours
- Serializer: 3-4 hours
- Testing & debugging: 2-4 hours

### Format Contract: MODERATE
- Simpler than XML (no attributes, namespaces)
- Need to document all element types
- Property type catalog
- Geometry representation

**Estimated Effort**: 4-6 hours

### Total CIBD25 Support: 20-30 hours

---

## Recommendations

### Priority 1: Understand Complete Format
- Parse multiple complete files
- Document all element types found
- Map to CIBD22X equivalents
- Identify CIBD25-specific features

### Priority 2: Design Clean Architecture
- Separate adapter for CIBD25
- Reuse InternalRepresentation (no changes needed)
- Format detector to choose adapter
- Maintain CIBD22X quality

### Priority 3: Incremental Implementation
- Start with simple elements (Mat, ConsAssm)
- Add building structure (Bldg, Story, Spc)
- Add geometry (PolyLp, CartesianPt)
- Add mechanical systems
- Test at each stage

### Priority 4: Comprehensive Testing
- All 5 sample files
- Roundtrip validation
- CBECC 2025 compatibility
- Format contract documentation

---

## Open Questions

1. **Geometry Representation**: How are 3D coordinates stored in CartesianPt and PolyLp?
2. **Nested Objects**: Can objects be nested beyond 1 level?
3. **Reference Format**: Are all references name-based, or do IDs exist?
4. **HVAC/DHW Systems**: What format do mechanical systems use?
5. **Compliance Data**: How are ResProj/ProjVar properties stored?
6. **Special Characters**: How are quotes, newlines escaped in string values?
7. **Numeric Precision**: What's the expected precision for coordinates, areas, etc.?

---

**Analysis Status**: Initial Discovery Complete
**Next Phase**: Detailed Structure Analysis
**Complexity**: Higher than initially expected (new format, not just XML variant)
