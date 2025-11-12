# CIBD25 Parser Architecture Design
**Date**: 2025-11-04
**Status**: Design Complete

## Overview

The CIBD25 adapter will be a **separate, standalone adapter** that implements the same `FormatAdapter` interface as the CIBD22X adapter, allowing seamless integration with the Universal Translator framework.

## Architecture Decision: Separate Adapter

### Rationale
1. **Format Incompatibility**: CIBD25 is custom text, CIBD22X is XML
2. **Different Parsing Strategies**: ElementTree vs custom tokenizer
3. **Zero Risk**: No impact on production CIBD22X adapter
4. **Clean Code**: Separation of concerns
5. **Maintainability**: Easier to test, debug, and evolve separately

### File Structure
```
eco_tools/formats/
├── __init__.py
├── cibd22x_adapter.py    # Existing (XML-based, production ready)
├── cibd25_adapter.py     # NEW (custom text parser)
└── format_detector.py    # Updated to detect both formats
```

---

## CIBD25 Adapter Class Structure

### Main Adapter Class
```python
class CIBD25Adapter(FormatAdapter):
    """
    Format adapter for CBECC 2025 CIBD25 files.

    CIBD25 uses a custom text-based format with object notation:
        ElementType   "ObjectName"
           Property = Value
           ArrayProp[1] = "Value1"
           ..
    """

    def __init__(self):
        self.tokenizer = CIBD25Tokenizer()
        self.parser = CIBD25Parser()
        self.serializer = CIBD25Serializer()

    def parse(self, file_path: str) -> InternalRepresentation:
        """Parse CIBD25 file into internal representation."""
        # Read file with correct encoding
        with open(file_path, 'r', encoding='iso-8859-1') as f:
            content = f.read()

        # Tokenize
        tokens = self.tokenizer.tokenize(content)

        # Parse tokens into object graph
        objects = self.parser.parse_tokens(tokens)

        # Build internal representation
        internal = self._build_internal_representation(objects)

        return internal

    def serialize(self, internal: InternalRepresentation, output_path: str):
        """Serialize internal representation to CIBD25 file."""
        # Convert internal representation to CIBD25 objects
        objects = self._convert_from_internal(internal)

        # Serialize to text
        content = self.serializer.serialize(objects)

        # Write with correct encoding and line endings
        with open(output_path, 'w', encoding='iso-8859-1', newline='\r\n') as f:
            f.write(content)

    def _build_internal_representation(self, objects: List[CIBD25Object]) -> InternalRepresentation:
        """Convert CIBD25 objects to internal representation."""
        # Implementation here
        pass

    def _convert_from_internal(self, internal: InternalRepresentation) -> List[CIBD25Object]:
        """Convert internal representation to CIBD25 objects."""
        # Implementation here
        pass
```

---

## Tokenizer Design

### Token Types
```python
from enum import Enum
from dataclasses import dataclass

class TokenType(Enum):
    OBJECT_DECLARATION = "object_declaration"    # ElementType   "Name"
    PROPERTY = "property"                         # Property = Value
    ARRAY_PROPERTY = "array_property"             # Property[N] = Value
    OBJECT_TERMINATOR = "object_terminator"       # ..
    EOF = "eof"

@dataclass
class Token:
    type: TokenType
    value: Any
    line_number: int

    # For OBJECT_DECLARATION
    element_type: Optional[str] = None
    element_name: Optional[str] = None

    # For PROPERTY and ARRAY_PROPERTY
    property_name: Optional[str] = None
    property_value: Optional[Any] = None
    array_index: Optional[int] = None  # For ARRAY_PROPERTY only
```

### Tokenizer Class
```python
import re

class CIBD25Tokenizer:
    """
    Tokenizer for CIBD25 format.

    Patterns:
    - Object declaration: ElementType   "Name" (multiple spaces, quoted name)
    - Property: (3 spaces)PropertyName = Value
    - Array property: (3 spaces)PropertyName[N] = Value
    - Terminator: (3 spaces)..
    """

    # Regex patterns
    OBJECT_DECL_PATTERN = re.compile(r'^([A-Z][a-zA-Z]+)\s{2,}"([^"]+)"\s*$')
    PROPERTY_PATTERN = re.compile(r'^   (\w+)\s*=\s*(.+)$')
    ARRAY_PROPERTY_PATTERN = re.compile(r'^   (\w+)\[(\d+)\]\s*=\s*(.+)$')
    TERMINATOR_PATTERN = re.compile(r'^   \.\.\s*$')

    def tokenize(self, content: str) -> List[Token]:
        """Tokenize CIBD25 content into token stream."""
        tokens = []
        lines = content.split('\n')

        for line_num, line in enumerate(lines, start=1):
            # Remove trailing whitespace but preserve leading
            line = line.rstrip()

            # Skip empty lines
            if not line:
                continue

            # Try to match patterns
            token = self._match_line(line, line_num)
            if token:
                tokens.append(token)

        tokens.append(Token(TokenType.EOF, None, len(lines) + 1))
        return tokens

    def _match_line(self, line: str, line_num: int) -> Optional[Token]:
        """Match a single line against all patterns."""

        # Try object declaration
        match = self.OBJECT_DECL_PATTERN.match(line)
        if match:
            return Token(
                type=TokenType.OBJECT_DECLARATION,
                value=match.group(2),
                line_number=line_num,
                element_type=match.group(1),
                element_name=match.group(2)
            )

        # Try array property
        match = self.ARRAY_PROPERTY_PATTERN.match(line)
        if match:
            prop_name = match.group(1)
            index = int(match.group(2))
            value = self._parse_value(match.group(3))
            return Token(
                type=TokenType.ARRAY_PROPERTY,
                value=value,
                line_number=line_num,
                property_name=prop_name,
                property_value=value,
                array_index=index
            )

        # Try property
        match = self.PROPERTY_PATTERN.match(line)
        if match:
            prop_name = match.group(1)
            value = self._parse_value(match.group(2))
            return Token(
                type=TokenType.PROPERTY,
                value=value,
                line_number=line_num,
                property_name=prop_name,
                property_value=value
            )

        # Try terminator
        if self.TERMINATOR_PATTERN.match(line):
            return Token(
                type=TokenType.OBJECT_TERMINATOR,
                value=None,
                line_number=line_num
            )

        # Unknown line format (could be RulesetFilename, etc.)
        if not line.startswith('   '):
            # Top-level special case
            parts = line.split(None, 1)
            if len(parts) == 2:
                return Token(
                    type=TokenType.PROPERTY,
                    value=parts[1].strip('"'),
                    line_number=line_num,
                    property_name=parts[0],
                    property_value=parts[1].strip('"')
                )

        return None

    def _parse_value(self, value_str: str) -> Any:
        """Parse property value to appropriate Python type."""
        value_str = value_str.strip()

        # Quoted string
        if value_str.startswith('"') and value_str.endswith('"'):
            return value_str[1:-1]

        # Coordinate tuple: ( X, Y, Z )
        if value_str.startswith('(') and value_str.endswith(')'):
            coords = value_str[1:-1].split(',')
            return tuple(float(c.strip()) for c in coords)

        # Numeric
        try:
            # Try integer
            if '.' not in value_str and 'e' not in value_str.lower():
                return int(value_str)
            else:
                return float(value_str)
        except ValueError:
            pass

        # Unquoted string
        return value_str
```

---

## Parser Design

### Object Representation
```python
@dataclass
class CIBD25Object:
    """
    Represents a parsed CIBD25 object.
    """
    element_type: str           # "Bldg", "Spc", "ExtWall", etc.
    name: str                   # Object name
    properties: Dict[str, Any]  # Simple properties
    arrays: Dict[str, List[Any]]  # Array properties (e.g., MatRef[1], MatRef[2])
    children: List['CIBD25Object']  # Child objects
    parent: Optional['CIBD25Object'] = None
    line_number: int = 0
```

### Parser Class
```python
class CIBD25Parser:
    """
    Parser for CIBD25 token stream.

    Builds object graph from flat token stream using:
    1. Object declarations start new objects
    2. Properties belong to current object
    3. Terminators close current object
    4. Hierarchy inferred from document order
    """

    def parse_tokens(self, tokens: List[Token]) -> List[CIBD25Object]:
        """Parse token stream into object graph."""
        objects = []
        current_object = None
        object_stack = []  # Stack for nesting if needed

        for token in tokens:
            if token.type == TokenType.OBJECT_DECLARATION:
                # Create new object
                obj = CIBD25Object(
                    element_type=token.element_type,
                    name=token.element_name,
                    properties={},
                    arrays={},
                    children=[],
                    line_number=token.line_number
                )

                # Add to parent if exists
                if current_object:
                    obj.parent = current_object
                    current_object.children.append(obj)
                else:
                    objects.append(obj)

                current_object = obj

            elif token.type == TokenType.PROPERTY:
                if current_object:
                    current_object.properties[token.property_name] = token.property_value
                else:
                    # Special case: RulesetFilename, etc.
                    obj = CIBD25Object(
                        element_type=token.property_name,
                        name=str(token.property_value),
                        properties={},
                        arrays={},
                        children=[],
                        line_number=token.line_number
                    )
                    objects.append(obj)

            elif token.type == TokenType.ARRAY_PROPERTY:
                if current_object:
                    prop_name = token.property_name
                    index = token.array_index

                    # Initialize array if needed
                    if prop_name not in current_object.arrays:
                        current_object.arrays[prop_name] = []

                    # Extend array if necessary (fill gaps with None)
                    while len(current_object.arrays[prop_name]) < index:
                        current_object.arrays[prop_name].append(None)

                    # Set value at index (1-based to 0-based conversion)
                    current_object.arrays[prop_name][index - 1] = token.property_value

            elif token.type == TokenType.OBJECT_TERMINATOR:
                # Close current object, return to parent
                if current_object and current_object.parent:
                    current_object = current_object.parent
                else:
                    current_object = None

        return objects
```

---

## Hierarchy Inference

The CIBD25 format is **flat** (no XML-style nesting), but hierarchy is determined by:

1. **Document Order**: Child elements follow parent in file
2. **Element Type Rules**: Certain types are always children of others
3. **Terminators**: `..` marks end of current object and its children

### Hierarchy Rules

```python
class HierarchyRules:
    """
    Defines parent-child relationships for CIBD25 elements.
    """

    # Element types that are always top-level
    TOP_LEVEL = {
        'RulesetFilename', 'Proj', 'ProjVar', 'Bldg',
        'Mat', 'ConsAssm', 'FenCons', 'DrCons',
        'ThrmlZn', 'AirSys', 'ZnSys', 'FluidSys',
        'PVArray', 'Batt', 'EUseSummary', 'SpcFuncDefaults'
    }

    # Parent -> allowed children mapping
    CHILDREN = {
        'Bldg': {'Story'},
        'Story': {'Spc'},
        'Spc': {'ExtWall', 'IntWall', 'Roof', 'UndgrFlr', 'ExtFlr', 'IntFlr', 'PolyLp'},
        'ExtWall': {'Win', 'Dr', 'PolyLp'},
        'IntWall': {'PolyLp'},
        'Roof': {'Skylt', 'PolyLp'},
        'Win': {'PolyLp'},
        'Dr': {'PolyLp'},
        'Skylt': {'PolyLp'},
        'UndgrFlr': {'PolyLp'},
        'ExtFlr': {'PolyLp'},
        'IntFlr': {'PolyLp'},
        'PolyLp': {'CartesianPt'},
        'AirSys': {'AirSeg', 'CoilClg', 'CoilHtg', 'Fan', 'TrmlUnit', 'OACtrl', 'HtRcvry'},
        'ZnSys': {'Fan'},
        'FluidSys': {'FluidSeg', 'WtrHtr'},
    }

    @classmethod
    def is_top_level(cls, element_type: str) -> bool:
        """Check if element type is top-level."""
        return element_type in cls.TOP_LEVEL

    @classmethod
    def can_be_child_of(cls, child_type: str, parent_type: str) -> bool:
        """Check if child_type can be a child of parent_type."""
        return child_type in cls.CHILDREN.get(parent_type, set())
```

---

## Reference Resolution

### Reference System
- **All references in CIBD25 are name-based** (string matching)
- No ID-based references like CIBD22X
- References are property values that match object names

### Reference Resolver
```python
class ReferenceResolver:
    """
    Resolves name-based references in CIBD25 object graph.
    """

    # Properties that contain references (name of property -> referenced element type)
    REFERENCE_PROPERTIES = {
        'ThrmlZnRef': 'ThrmlZn',
        'ConsAssmRef': 'ConsAssm',
        'FenConsRef': 'FenCons',
        'DrConsRef': 'DrCons',
        'AdjacentSpcRef': 'Spc',
        'SHWFluidSegRef': 'FluidSeg',
        'CtrlZnRef': 'ThrmlZn',
        'AirSegSupRef': 'AirSeg',
        'AirSegRetRef': 'AirSeg',
        'FluidSegOutRef': 'FluidSeg',
        'FluidSegMakeupRef': 'FluidSeg',
        'HtPumpSuppCoilHtgRef': 'CoilHtg',
        'SpcFuncDefaultsRef': 'SpcFuncDefaults',
    }

    # Array properties that contain references
    ARRAY_REFERENCE_PROPERTIES = {
        'MatRef': 'Mat',
    }

    def __init__(self, objects: List[CIBD25Object]):
        self.objects = objects
        self.name_index = self._build_name_index()

    def _build_name_index(self) -> Dict[Tuple[str, str], CIBD25Object]:
        """Build index of (element_type, name) -> object."""
        index = {}

        def index_object(obj):
            key = (obj.element_type, obj.name)
            index[key] = obj
            for child in obj.children:
                index_object(child)

        for obj in self.objects:
            index_object(obj)

        return index

    def resolve_references(self):
        """Resolve all references in object graph."""

        def resolve_object(obj):
            # Resolve simple property references
            for prop_name, ref_value in obj.properties.items():
                if prop_name in self.REFERENCE_PROPERTIES:
                    target_type = self.REFERENCE_PROPERTIES[prop_name]
                    target = self.name_index.get((target_type, ref_value))
                    if target:
                        # Store resolved reference (could add metadata)
                        obj.properties[f'_resolved_{prop_name}'] = target

            # Resolve array property references
            for arr_name, arr_values in obj.arrays.items():
                if arr_name in self.ARRAY_REFERENCE_PROPERTIES:
                    target_type = self.ARRAY_REFERENCE_PROPERTIES[arr_name]
                    resolved = []
                    for ref_value in arr_values:
                        target = self.name_index.get((target_type, ref_value))
                        resolved.append(target)
                    obj.arrays[f'_resolved_{arr_name}'] = resolved

            # Recurse to children
            for child in obj.children:
                resolve_object(child)

        for obj in self.objects:
            resolve_object(obj)
```

---

## Serializer Design

### Serializer Class
```python
class CIBD25Serializer:
    """
    Serializer for CIBD25 format.

    Converts object graph back to CIBD25 text format.
    """

    def serialize(self, objects: List[CIBD25Object]) -> str:
        """Serialize object graph to CIBD25 text."""
        lines = []

        for obj in objects:
            self._serialize_object(obj, lines)

        # Join with CRLF line endings
        return '\r\n'.join(lines) + '\r\n'

    def _serialize_object(self, obj: CIBD25Object, lines: List[str], level: int = 0):
        """Serialize a single object and its children."""

        # Special case: RulesetFilename (no quotes, no terminator)
        if obj.element_type == 'RulesetFilename':
            lines.append(f'{obj.element_type}   "{obj.name}"')
            return

        # Object declaration
        lines.append(f'{obj.element_type}   "{obj.name}"')

        # Properties (sorted for consistency)
        for prop_name in sorted(obj.properties.keys()):
            # Skip internal resolved references
            if prop_name.startswith('_resolved_'):
                continue

            value = obj.properties[prop_name]
            lines.append(self._format_property(prop_name, value))

        # Array properties (maintain order, 1-based indexing)
        for arr_name in sorted(obj.arrays.keys()):
            if arr_name.startswith('_resolved_'):
                continue

            values = obj.arrays[arr_name]
            for idx, value in enumerate(values, start=1):
                lines.append(self._format_array_property(arr_name, idx, value))

        # Children (recursive)
        for child in obj.children:
            self._serialize_object(child, lines, level + 1)

        # Terminator
        lines.append('   ..')

        # Blank line after top-level objects (optional, for readability)
        if level == 0:
            lines.append('')

    def _format_property(self, name: str, value: Any) -> str:
        """Format a single property."""
        formatted_value = self._format_value(value)
        return f'   {name} = {formatted_value}'

    def _format_array_property(self, name: str, index: int, value: Any) -> str:
        """Format an array property with index."""
        formatted_value = self._format_value(value)
        return f'   {name}[{index}] = {formatted_value}'

    def _format_value(self, value: Any) -> str:
        """Format a value for serialization."""
        if isinstance(value, str):
            # Check if it needs quotes (has spaces or special chars)
            if ' ' in value or any(c in value for c in '()[]{}'):
                return f'"{value}"'
            return f'"{value}"'  # Always quote strings for safety

        elif isinstance(value, tuple):
            # Coordinate tuple
            formatted = ', '.join(str(v) for v in value)
            return f'( {formatted} )'

        elif isinstance(value, (int, float)):
            return str(value)

        else:
            return str(value)
```

---

## Internal Representation Mapping

### Mapping Strategy

The `InternalRepresentation` class is **format-agnostic** and should work with both CIBD22X and CIBD25.

Key mappings:
- CIBD25 `Spc` → Internal `Zone`
- CIBD25 `Bldg` → Internal `Building`
- CIBD25 `Mat` → Internal `Material`
- CIBD25 `ConsAssm` → Internal `Construction`
- etc.

### Conversion Methods

```python
def _build_internal_representation(self, objects: List[CIBD25Object]) -> InternalRepresentation:
    """Convert CIBD25 objects to internal representation."""
    internal = InternalRepresentation()

    # Index objects by type for quick lookup
    objects_by_type = self._index_by_type(objects)

    # Extract project info
    proj = objects_by_type.get('Proj', [None])[0]
    if proj:
        internal.project_name = proj.name
        internal.zip_code = proj.properties.get('ZipCode')
        # ... more project properties

    # Extract building
    bldg = objects_by_type.get('Bldg', [None])[0]
    if bldg:
        internal.building = self._convert_building(bldg)

    # Extract materials
    for mat in objects_by_type.get('Mat', []):
        internal.materials.append(self._convert_material(mat))

    # Extract constructions
    for cons in objects_by_type.get('ConsAssm', []):
        internal.constructions.append(self._convert_construction(cons))

    # Extract zones (from Spc objects)
    for spc in objects_by_type.get('Spc', []):
        internal.zones.append(self._convert_space_to_zone(spc))

    # ... more conversions

    return internal

def _convert_space_to_zone(self, spc: CIBD25Object) -> Zone:
    """Convert CIBD25 Spc to internal Zone."""
    zone = Zone()
    zone.name = spc.name
    zone.volume = spc.properties.get('Vol')
    zone.space_function = spc.properties.get('SpcFunc')

    # Extract surfaces (children of Spc)
    for child in spc.children:
        if child.element_type in ('ExtWall', 'IntWall', 'Roof', 'UndgrFlr'):
            surface = self._convert_surface(child)
            zone.surfaces.append(surface)

    return zone

# ... similar conversion methods for other element types
```

---

## Format Detection

Update `format_detector.py` to handle both CIBD22X and CIBD25:

```python
class FormatDetector:
    """Detect file format (CIBD22X, CIBD25, etc.)"""

    @staticmethod
    def detect_format(file_path: str) -> str:
        """
        Detect format from file content.

        Returns:
            'cibd22x', 'cibd25', 'unknown'
        """
        with open(file_path, 'rb') as f:
            # Read first 1000 bytes
            header = f.read(1000)

        try:
            # Try decoding as UTF-8 (XML)
            header_str = header.decode('utf-8')

            # Check for XML declaration
            if header_str.strip().startswith('<?xml'):
                return 'cibd22x'
        except UnicodeDecodeError:
            pass

        try:
            # Try decoding as ISO-8859-1 (CIBD25)
            header_str = header.decode('iso-8859-1')

            # Check for CIBD25 patterns
            if 'RulesetFilename' in header_str and 'T24_2025.bin' in header_str:
                return 'cibd25'

            # Check for CIBD25 object pattern
            if re.search(r'[A-Z][a-zA-Z]+\s{2,}"[^"]+"', header_str):
                return 'cibd25'
        except Exception:
            pass

        return 'unknown'

    @staticmethod
    def get_adapter(file_path: str):
        """Get appropriate adapter for file."""
        format_type = FormatDetector.detect_format(file_path)

        if format_type == 'cibd22x':
            from eco_tools.formats.cibd22x_adapter import CIBD22XAdapter
            return CIBD22XAdapter()
        elif format_type == 'cibd25':
            from eco_tools.formats.cibd25_adapter import CIBD25Adapter
            return CIBD25Adapter()
        else:
            raise ValueError(f"Unknown format for file: {file_path}")
```

---

## Testing Strategy

### Unit Tests

1. **Tokenizer Tests**
   - Test all token patterns
   - Test value parsing (strings, numbers, coordinates, arrays)
   - Test edge cases (scientific notation, special characters)

2. **Parser Tests**
   - Test object creation
   - Test hierarchy building
   - Test property assignment (simple and array)
   - Test terminator handling

3. **Reference Resolver Tests**
   - Test name-based reference resolution
   - Test array references
   - Test missing reference handling

4. **Serializer Tests**
   - Test object serialization
   - Test property formatting
   - Test array property formatting (1-based indexing)
   - Test coordinate tuple formatting
   - Test line ending (CRLF) and encoding (ISO-8859-1)

5. **Roundtrip Tests**
   - Parse CIBD25 → Internal → Serialize CIBD25
   - Compare with original (semantically, not byte-for-byte)

### Integration Tests

1. **Complete File Parsing**
   - Test on all 5 sample files
   - Verify all elements parsed correctly
   - Verify no data loss

2. **Format Detection**
   - Test CIBD22X detection
   - Test CIBD25 detection
   - Test mixed file handling

3. **Translation Tests**
   - CIBD25 → Internal → CIBD22X (if supported)
   - Validate cross-format compatibility

---

## Implementation Checklist

### Phase 1: Core Parser (4-6 hours)
- [ ] Create `cibd25_adapter.py` file
- [ ] Implement `CIBD25Tokenizer` class
- [ ] Implement `CIBD25Parser` class
- [ ] Implement `CIBD25Object` dataclass
- [ ] Implement `HierarchyRules` class
- [ ] Unit tests for tokenizer and parser

### Phase 2: Reference Resolution (2-3 hours)
- [ ] Implement `ReferenceResolver` class
- [ ] Build name index
- [ ] Resolve simple references
- [ ] Resolve array references
- [ ] Unit tests for reference resolution

### Phase 3: Serializer (3-4 hours)
- [ ] Implement `CIBD25Serializer` class
- [ ] Implement property formatting
- [ ] Implement array property formatting
- [ ] Implement coordinate formatting
- [ ] Handle line endings (CRLF) and encoding (ISO-8859-1)
- [ ] Unit tests for serializer

### Phase 4: Internal Representation Mapping (4-6 hours)
- [ ] Implement `_build_internal_representation()`
- [ ] Implement `_convert_from_internal()`
- [ ] Map all 36 element types
- [ ] Handle reference conversions
- [ ] Unit tests for mapping

### Phase 5: Integration (2-3 hours)
- [ ] Update `format_detector.py`
- [ ] Integrate with Universal Translator
- [ ] Test format detection
- [ ] Test adapter selection

### Phase 6: Testing & Validation (2-4 hours)
- [ ] Test on all 5 CIBD25 sample files
- [ ] Roundtrip validation
- [ ] Compare with CBECC 2025 output
- [ ] Performance testing
- [ ] Edge case testing

### Phase 7: Documentation (2-3 hours)
- [ ] Create CIBD25 format contract
- [ ] API documentation
- [ ] Usage examples
- [ ] Known limitations

---

## Performance Considerations

### Memory Efficiency
- Stream processing where possible
- Avoid loading entire file into memory (large warehouses are 175 KB)
- Use generators for large object collections

### Parsing Speed
- Compiled regex patterns (already done)
- Single-pass parsing
- Minimal string copying

### Expected Performance
- Small files (26 KB): < 0.5 seconds
- Large files (175 KB): < 2 seconds
- Roundtrip: < 3 seconds total

---

## Error Handling

### Parser Errors
- Malformed object declarations
- Missing terminators
- Invalid property syntax
- Invalid array indices
- Unknown element types (warn but continue)

### Reference Errors
- Missing reference targets (warn, don't fail)
- Circular references (detect and warn)

### Serialization Errors
- Invalid property values
- Missing required properties
- Encoding errors

### Error Reporting Strategy
```python
class CIBD25ParseError(Exception):
    """Base exception for CIBD25 parsing errors."""
    def __init__(self, message: str, line_number: int = None):
        self.line_number = line_number
        super().__init__(f"Line {line_number}: {message}" if line_number else message)

# Use throughout parser
raise CIBD25ParseError("Expected object terminator", token.line_number)
```

---

## Future Enhancements

### Potential Additions (Post-MVP)
1. **Schema Validation**: Validate against CIBD25 schema
2. **Property Type Validation**: Check property value types
3. **Compliance Checking**: Validate Title 24 2025 requirements
4. **Pretty Printing**: Format output with consistent spacing
5. **Diff Tool**: Compare two CIBD25 files
6. **Migration Tool**: Convert CIBD22X → CIBD25

---

**Status**: ✅ Architecture Design Complete
**Next Step**: Begin implementation - Phase 1 (Core Parser)
**Estimated Total Effort**: 20-30 hours
