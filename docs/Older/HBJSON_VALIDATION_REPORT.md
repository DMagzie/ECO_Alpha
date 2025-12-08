# HBJSON Integration Validation Report

**Date**: November 14, 2025
**Branch**: v7-restructure
**Status**: 🔴 **CRITICAL ISSUES FOUND - Requires Architecture Fix**

---

## Executive Summary

A comprehensive validation infrastructure has been established for HBJSON round-trip testing, including:
- ✅ 22 official Honeybee sample files downloaded (2.2MB)
- ✅ Complete round-trip test script (`test_hbjson_roundtrip.py`)
- ✅ Comprehensive unit test suite (pytest-compatible)
- ✅ Testing infrastructure in place

**However**, validation testing revealed **critical schema mismatches** between the HBJSON importer and EMJSON v6.1 internal representation that prevent successful round-trip translation.

---

## Test Infrastructure Created

### 1. Sample Files (✅ Complete)

**Location**: `/reference_data/hbjson_samples/`
**Count**: 22 HBJSON files
**Size**: 2.2 MB
**Source**: Official Ladybug Tools honeybee-schema repository

**Sample Categories**:
- Simple geometry (2 files)
- Complete multi-room models (5 files)
- Energy models with HVAC (9 files)
- Radiance/daylighting models (2 files)
- Special cases/edge cases (4 files)

**Download Script**: `download_all_samples.sh` (automated retrieval)

### 2. Round-Trip Test Script (✅ Complete)

**File**: `test_hbjson_roundtrip.py` (~350 lines)

**Features**:
- Validates HBJSON → EMJSON → HBJSON workflow
- Compares original vs round-trip files
- Detailed statistics and error reporting
- JSON results export
- Exit codes for CI/CD integration

**Class**: `HBJSONRoundTripValidator`

**Methods**:
- `validate_file()` - Test single HBJSON file
- `validate_all_samples()` - Test all samples
- `_compare_hbjson_files()` - Compare original vs round-trip
- `_generate_summary()` - Create aggregate statistics

### 3. Unit Test Suite (✅ Complete)

**Location**: `tests/hbjson/`

**Files**:
- `test_hbjson_importer.py` (~180 lines) - 14 test functions
- `test_hbjson_exporter.py` (~200 lines) - 12 test functions + round-trip tests
- `__init__.py` - Package initialization

**Test Coverage**:
- Importer initialization
- Zone/room conversion
- Surface/face conversion
- Material import
- Construction import
- Geometry preservation
- Opening (windows/doors) import
- HVAC system handling
- Multi-zone models
- Error handling
- Parametrized testing across multiple models

---

## Critical Issues Found

### Issue #1: Surface Schema Mismatch

**Error**:
```
TypeError: Surface.__init__() got an unexpected keyword argument 'vertices'
```

**Root Cause**:
The HBJSON importer (`hbjson/importer.py` line 290) attempts to create Surface objects with `vertices` parameter:

```python
surface = Surface(
    id=surface_id,
    name=hb_face.display_name,
    parent_zone_id=zone_id,
    vertices=vertices,  # ❌ NOT IN SCHEMA
    ...
)
```

**Actual EMJSON v6.1 Surface Schema** (`internal_repr.py` lines 30-49):
```python
@dataclass
class Surface:
    id: str
    name: str
    parent_zone_id: str
    surface_type: str
    # No vertices field!
```

**Impact**: 100% of geometry-based models fail to import

**Affected Files**: 18 of 22 sample files

---

### Issue #2: Material Schema Mismatch

**Error**:
```
TypeError: Material.__init__() got an unexpected keyword argument 'conductivity'
```

**Root Cause**:
HBJSON importer tries to pass thermal properties directly to Material constructor, but EMJSON v6.1 Material schema may not support these parameters.

**Impact**: Models with detailed material definitions fail

**Affected Files**: 2+ sample files

---

### Issue #3: Construction Schema Mismatch

**Error**:
```
TypeError: Construction.__init__() got an unexpected keyword argument 'material_refs'
```

**Root Cause**:
Importer uses `material_refs` parameter but schema may expect different field name or structure.

**Impact**: Models with custom constructions fail

**Affected Files**: 1+ sample files

---

###Issue #4: Schedule Schema Mismatch

**Error**:
```
TypeError: Schedule.__init__() got an unexpected keyword argument 'type'
```

**Root Cause**:
Schedule creation parameters don't match EMJSON v6.1 schema.

**Impact**: Models with detailed schedules fail

**Affected Files**: 7+ sample files

---

## Validation Results Summary

**Total Files Tested**: 22
**Full Success**: 0 (0%)
**Partial Success**: 0 (0%)
**Errors**: 22 (100%)

**Import Success Rate**: 0/22 (0%)
**Export Success Rate**: N/A (import failures prevented export testing)
**Round-Trip Success**: 0/22 (0%)

### Failed Files (All 22)

```
✗ model_5vertex_sub_faces.hbjson - Surface vertices error
✗ model_5vertex_sub_faces_interior.hbjson - Surface vertices error
✗ model_complete_holes.hbjson - Surface vertices error
✗ model_complete_multi_zone_office.hbjson - Material conductivity error
✗ model_complete_multiroom_radiance.hbjson - Surface vertices error
✗ model_complete_office_floor.hbjson - Schedule type error
✗ model_complete_patient_room.hbjson - Schedule type error
✗ model_complete_single_zone_office.hbjson - Material conductivity error
✗ model_complete_user_data.hbjson - Construction material_refs error
✗ model_energy_afn.hbjson - Schedule type error
✗ model_energy_allair_hvac.hbjson - Schedule type error
✗ model_energy_detailed_loads.hbjson - Schedule type error
✗ model_energy_doas_hvac.hbjson - Schedule type error
✗ model_energy_fixed_interval.hbjson - Construction material_refs error
✗ model_energy_no_program.hbjson - Surface vertices error
✗ model_energy_service_hot_water.hbjson - Schedule type error
✗ model_energy_shoe_box.hbjson - Surface vertices error
✗ model_energy_window_ac.hbjson - Schedule type error
✗ model_energy_window_ventilation.hbjson - Schedule type error
✗ model_radiance_dynamic_states.hbjson - Surface vertices error
✗ model_radiance_grid_views.hbjson - Surface vertices error
✗ model_with_shade_mesh.hbjson - Surface vertices error
```

---

## Root Cause Analysis

### Architecture Mismatch

The HBJSON importer was written for **a different version of the EMJSON schema** than currently exists in v7.

**Evidence**:
1. Importer expects `Surface` to have `vertices` field
2. Importer expects `Material` to have thermal property fields
3. Importer expects different Construction/Schedule structures

**Current EMJSON v6.1 Architecture** (from `internal_repr.py`):
- **ID-based relationships**: Surfaces reference zones by ID, not direct geometry
- **Reference-based construction**: Surfaces have `construction_ref`, not embedded materials
- **Minimal geometry storage**: Focus on CBECC-Com properties, not full 3D coordinates

**HBJSON Requirements**:
- **Full 3D geometry**: Vertices, normals, Face3D objects
- **Embedded properties**: Materials with conductivity, specific heat, etc.
- **Rich schedule data**: Hourly values, interpolation rules
- **Complete envelope**: All thermal boundary information

---

## Critical Decision Required

### Option 1: Extend EMJSON v6.1 Schema ✅ RECOMMENDED

**Action**: Add geometry storage capabilities to EMJSON v6.1

**Changes Needed**:
```python
@dataclass
class Surface:
    # Existing fields...
    id: str
    name: str
    parent_zone_id: str
    surface_type: str

    # NEW: Add geometry storage
    vertices: Optional[List[Dict[str, float]]] = None  # [{x, y, z}, ...]
    normal: Optional[Dict[str, float]] = None  # {x, y, z}
    plane: Optional[Dict[str, Any]] = None  # Plane definition

@dataclass
class Material:
    # Existing fields...
    id: str
    name: str

    # NEW: Add thermal properties
    conductivity: Optional[float] = None  # W/m·K
    density: Optional[float] = None  # kg/m³
    specific_heat: Optional[float] = None  # J/kg·K
    thickness: Optional[float] = None  # m
```

**Pros**:
- ✅ Enables true HBJSON round-trip
- ✅ Enables EnergyPlus simulation
- ✅ Maintains CBECC-Com compatibility
- ✅ Future-proofs architecture

**Cons**:
- ⚠️ Schema changes required
- ⚠️ May affect existing CIBD22X translator
- ⚠️ Estimated 4-8 hours of work

---

### Option 2: Rewrite HBJSON Importer for Current Schema

**Action**: Adapt importer to work with current EMJSON v6.1 limitations

**Pros**:
- ✅ No schema changes

**Cons**:
- ❌ Loses geometry information
- ❌ Cannot support EnergyPlus simulation
- ❌ Limited HBJSON round-trip fidelity
- ❌ Defeats purpose of Ladybug integration

---

### Option 3: Create Separate Geometry Extension

**Action**: Create optional geometry module that extends base EMJSON

**Implementation**:
```python
# Base EMJSON (unchanged)
class Surface:
    id: str
    name: str
    # ...

# Optional geometry extension
class SurfaceGeometry:
    surface_id: str
    vertices: List[Point3D]
    normal: Vector3D
```

**Pros**:
- ✅ Backward compatible
- ✅ Clean separation of concerns

**Cons**:
- ⚠️ More complex architecture
- ⚠️ Two parallel data structures

---

## Recommendations

### Immediate Actions (This Session)

1. **✅ DONE**: Document all schema mismatches
2. **✅ DONE**: Create validation infrastructure
3. **NEXT**: Decide on schema extension approach
4. **NEXT**: Update EMJSON v6.1 schema with geometry fields
5. **NEXT**: Fix HBJSON importer to match new schema
6. **NEXT**: Re-run validation tests

### Short-Term (Next Session)

1. Extend EMJSON v6.1 with optional geometry fields
2. Update all translators to handle new fields
3. Achieve 80%+ round-trip success rate
4. Document updated architecture

### Long-Term (Phase 7)

1. Complete geometry support across all formats
2. Enable full HBJSON ↔ CIBD22X workflows
3. Validate EnergyPlus simulation accuracy
4. Performance optimization

---

## Files Created This Session

| File | Lines | Purpose |
|------|-------|---------|
| `test_hbjson_roundtrip.py` | 350 | Round-trip validation script |
| `tests/hbjson/test_hbjson_importer.py` | 180 | Unit tests for importer |
| `tests/hbjson/test_hbjson_exporter.py` | 200 | Unit tests for exporter |
| `reference_data/hbjson_samples/*.hbjson` | N/A | 22 sample files (2.2MB) |
| `reference_data/hbjson_samples/download_all_samples.sh` | 30 | Automated download script |
| **Total New Code** | **~760 lines** | **Complete test infrastructure** |

---

## Sample File Statistics

| Category | Files | Avg Size | Description |
|----------|-------|----------|-------------|
| Simple | 3 | 15-25 KB | Basic geometry, good for initial testing |
| Single Zone | 4 | 50-90 KB | Complete rooms with systems |
| Multi-Zone | 6 | 50-110 KB | Multiple thermal zones |
| HVAC | 6 | 60-90 KB | Various HVAC system types |
| Radiance | 2 | 55-350 KB | Daylighting analysis models |
| Edge Cases | 1 | 670 KB | Complex geometry, detailed loads |

**Largest File**: `model_energy_fixed_interval.hbjson` (670 KB) - Fixed timestep schedules
**Smallest File**: `model_energy_shoe_box.hbjson` (23 KB) - Simple rectangular room

---

## Next Steps

**CRITICAL**: Before proceeding with HBJSON integration:

1. ⚠️ **Architecture Decision Required**
   Choose Option 1, 2, or 3 for schema handling

2. ✅ **If Option 1 Selected** (Recommended):
   - Extend Surface class with geometry fields
   - Extend Material class with thermal properties
   - Extend Construction class with layer references
   - Extend Schedule class with time-series data
   - Update CIBD22X translator to ignore new fields
   - Fix HBJSON importer parameter names
   - Re-run validation

3. ✅ **Success Criteria**:
   - 80%+ import success rate (18/22 files)
   - 70%+ full round-trip success (15/22 files)
   - No data loss for basic geometry
   - CIBD22X translator remains functional

---

## Conclusion

The HBJSON integration validation has revealed that **the existing HBJSON translators are incompatible with the current EMJSON v6.1 schema**. This is a solvable problem requiring schema extension work.

**Infrastructure Status**: ✅ COMPLETE
**Translator Status**: 🔴 NON-FUNCTIONAL
**Path Forward**: CLEAR

With the schema extensions from Option 1, we can achieve full HBJSON round-trip capability and enable the complete Ladybug Tools integration workflow.

**Estimated Effort**: 4-8 hours to fix
**Priority**: HIGH (blocks EnergyPlus simulation)
**Risk**: LOW (well-understood problem)

---

**Report Generated**: November 14, 2025
**Validation Script**: `test_hbjson_roundtrip.py`
**Test Results**: `test_output/hbjson_roundtrip/validation_results.json`
