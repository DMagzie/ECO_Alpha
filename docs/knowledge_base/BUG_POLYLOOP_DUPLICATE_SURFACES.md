# BUG: Polyloop Parser Duplicate Surface Parsing

**Bug ID**: POLY-001
**Severity**: High
**Status**: FIXED
**Reported**: December 2024
**Fixed**: January 2026
**Affected Project**: Gibralter Distribution Center
**Component**: `eco_tools/translators/cibd22x/parsers/surface_parser.py`
**Fix Applied**: Option A - Changed `zone_elem.iter()` to `zone_elem` (direct children only)

---

## Summary

The polyloop parser's surface parsing logic causes floor surfaces to be added twice to rooms, resulting in doubled floor area and halved ceiling height calculations. This was identified in the Gibralter model where the break room slab-on-grade floor was duplicated.

---

## Symptoms

| Observed Behavior | Expected Behavior |
|-------------------|-------------------|
| Break room floor area: 2x actual | Break room floor area: 1x actual |
| Ceiling height: half of actual | Ceiling height: correct value |
| HVAC sizing: oversized | HVAC sizing: correct |

**Client Report**: "The break room slab on grade floor was added twice, which doubled the square footage of that room and halved the ceiling height."

---

## Root Cause Analysis

### Location

**File**: `eco_tools/translators/cibd22x/parsers/surface_parser.py`
**Lines**: 87-96

### Problematic Code

```python
# Find all surfaces in this zone - namespace-aware
for surf_tag in self.SURFACE_TAGS:  # 17 surface tag types
    for surf_elem in zone_elem.iter():  # ALL descendants
        if self._local_tag(surf_elem.tag) == surf_tag:
            surface = self._parse_single_surface(surf_elem, surf_tag, zone_id, zone_name)
            if surface:
                surfaces.append(surface)  # May add same surface multiple times
```

### Why This Causes Duplicates

1. **Nested Loop Structure**: The code iterates through 17 surface tag types for each zone
2. **`iter()` Traversal**: `zone_elem.iter()` finds ALL descendants at ALL depths, not just direct children
3. **Tag Ambiguity**: Slab-on-grade floors can match multiple tag types:
   - `ExtFlr` (exterior floor)
   - `UndgrFlr` (underground/at-grade floor)
4. **No Deduplication**: No check prevents the same surface element from being added twice

### Affected Surface Tags

The full `SURFACE_TAGS` list (lines 42-46):
```python
SURFACE_TAGS = [
    'ResExtWall', 'ResIntWall', 'ResIntFlr', 'ResSlabFlr', 'ResUndgrWall', 'ResUndgrFlr',
    'ResCathedralCeiling', 'ResCeilingBelowAttic', 'ResAtticRoof', 'ResOtherFlr',
    'ExtWall', 'IntWall', 'Roof', 'ExtFlr', 'IntFlr', 'UndgrWall', 'UndgrFlr'
]
```

**Floor-related tags prone to duplication**:
- `ExtFlr` and `UndgrFlr` (commercial)
- `ResSlabFlr` and `ResUndgrFlr` (residential)

---

## Impact Analysis

### Direct Impact

| Metric | Correct Value | Buggy Value | Error Factor |
|--------|---------------|-------------|--------------|
| Floor Area | A | 2A | 2x |
| Ceiling Height | V/A | V/(2A) | 0.5x |
| Volume (derived) | V | V | correct |

### Downstream Impact

1. **HVAC Sizing**: Based on floor area, oversized by 2x
2. **Lighting Calculations**: LPD * Area = 2x actual lighting load
3. **LCCA Metrics**: kWh/SF values halved (incorrect normalization)
4. **Compliance**: Potential false pass/fail on area-based requirements

---

## Reproduction Steps

1. Import a CIBD22X file with slab-on-grade floors
2. Parse using `surface_parser.parse_surfaces()`
3. Count floor surfaces per zone
4. Compare against source file floor count
5. Observe duplicate entries for slab-on-grade floors

### Test Query

```python
# Check for duplicate floors in parsed output
from collections import Counter
floor_counts = Counter()
for surface in parsed_surfaces:
    if surface['type'] in ['ExtFlr', 'UndgrFlr', 'ResSlabFlr']:
        key = (surface['zone_id'], surface['name'])
        floor_counts[key] += 1

duplicates = {k: v for k, v in floor_counts.items() if v > 1}
print(f"Duplicate floors found: {duplicates}")
```

---

## Proposed Fix

### Option A: Use Direct Children Only (Recommended)

Replace `zone_elem.iter()` with direct child iteration:

```python
# BEFORE (buggy):
for surf_elem in zone_elem.iter():

# AFTER (fixed):
for surf_elem in zone_elem:  # Direct children only
```

### Option B: Track Parsed Elements

Add deduplication via element tracking:

```python
parsed_elements = set()
for surf_tag in self.SURFACE_TAGS:
    for surf_elem in zone_elem.iter():
        if id(surf_elem) in parsed_elements:
            continue  # Skip already-parsed elements
        if self._local_tag(surf_elem.tag) == surf_tag:
            surface = self._parse_single_surface(...)
            if surface:
                surfaces.append(surface)
                parsed_elements.add(id(surf_elem))
```

### Option C: Post-Parse Deduplication

Add deduplication after parsing:

```python
def _deduplicate_surfaces(surfaces: List[dict]) -> List[dict]:
    """Remove duplicate surfaces based on zone + name + type."""
    seen = set()
    unique = []
    for s in surfaces:
        key = (s['zone_id'], s['name'], s['type'])
        if key not in seen:
            seen.add(key)
            unique.append(s)
    return unique
```

### Recommendation

**Option A** is preferred because:
- Addresses root cause directly
- Minimal code change
- No performance overhead
- Matches expected CIBD22X structure (surfaces are direct children of zones)

---

## Testing Requirements

### Unit Tests

1. Parse file with single slab-on-grade floor per zone
2. Verify floor count matches source
3. Verify calculated area matches expected
4. Verify ceiling height derivation is correct

### Regression Tests

1. Re-run Gibralter model through parser
2. Verify break room floor appears exactly once
3. Verify all zone areas match CBECC GUI values
4. Run existing `test_gibraltar_regression.py`

### Integration Tests

1. Full translation workflow with Gibralter
2. CBECC compliance simulation passes
3. LCCA calculations produce expected values

---

## Related Files

| File | Relevance |
|------|-----------|
| `eco_tools/translators/cibd22x/parsers/surface_parser.py` | Bug location |
| `eco_tools/translators/cibd22x/parsers/zone_parser.py` | Consumes surface data |
| `eco_tools/translators/cibd22x/importer.py` | Orchestrates parsing |
| `tests/test_gibraltar_regression.py` | Existing regression test |
| `docs/knowledge_base/GIBRALTAR_LESSONS_LEARNED.md` | Related documentation |

---

## Related Issues

### From GIBRALTAR_LESSONS_LEARNED.md (Section 1)

> "Warehouse Spc:Area = 0" error documented the confusion between `UndgrFlr` and `ExtFlr` for grade-level floors. This bug is the inverse problem: instead of missing floors, floors are duplicated.

### Connection to Area Calculation

The lessons learned document states:
> "CBECC calculates space area from actual floor SURFACES (UndgrFlr), not from boundary polygons (PolyLp)."

When duplicate floor surfaces exist, the area calculation sums them, resulting in 2x the correct area.

---

## Workaround (Manual)

Until the fix is implemented, affected projects can be manually corrected:

1. Export EMJSON from parser
2. Identify zones with duplicate floor surfaces
3. Remove duplicate entries from `surfaces` array
4. Re-import corrected EMJSON

**Note**: This is a temporary workaround. The parser fix is the proper solution.

---

## References

- Gibralter project files: `/Users/DavidM/Documents/EM_Projects/Project Files/Gibralter`
- Surface parser: `eco_tools/translators/cibd22x/parsers/surface_parser.py:87-96`
- Polyloop calculation: `eco_tools/translators/cibd22x/parsers/surface_parser.py:213-249`
- Gibraltar lessons: `docs/knowledge_base/GIBRALTAR_LESSONS_LEARNED.md`

---

**Last Updated**: December 29, 2024
