# HBJSON Validation Setup - ✅ COMPLETE

**Date**: November 14, 2025
**Status**: Infrastructure ready, awaiting schema fixes
**Location**: `/Users/DavidM/Documents/ECO_Alpha_v7`

---

## What Was Accomplished

### ✅ Complete Test Infrastructure

1. **22 Official Sample Files** (2.2 MB)
   - Location: `reference_data/hbjson_samples/`
   - Source: Ladybug Tools honeybee-schema repository
   - Auto-download script: `download_all_samples.sh`

2. **Round-Trip Validation Script** (350 lines)
   - File: `test_hbjson_roundtrip.py`
   - Tests: HBJSON → EMJSON → HBJSON workflow
   - Output: `test_output/hbjson_roundtrip/validation_results.json`

3. **Unit Test Suite** (380 lines)
   - Location: `tests/hbjson/`
   - Files: `test_hbjson_importer.py`, `test_hbjson_exporter.py`
   - Framework: pytest-compatible

4. **Comprehensive Documentation**
   - Report: `docs/HBJSON_VALIDATION_REPORT.md`
   - Status overview with next steps

---

## Quick Reference

### Run Full Validation

```bash
cd /Users/DavidM/Documents/ECO_Alpha_v7
python3 test_hbjson_roundtrip.py
```

**Output**: Detailed report with pass/fail status for all 22 samples

### Run Unit Tests

```bash
cd /Users/DavidM/Documents/ECO_Alpha_v7
pytest tests/hbjson/ -v
```

**Output**: Pytest results for individual importer/exporter functions

### Re-Download Samples

```bash
cd /Users/DavidM/Documents/ECO_Alpha_v7/reference_data/hbjson_samples
./download_all_samples.sh
```

**Output**: Fresh copies of all 22 HBJSON files

---

## Current Status: 🔴 Schema Mismatch

**Issue**: HBJSON importer incompatible with EMJSON v6.1 schema

**Validation Results**:
- Total Files: 22
- Success: 0 (0%)
- Errors: 22 (100%)

**Root Cause**: Missing geometry fields in EMJSON v6.1 Surface class

---

## Sample Files Available

### Simple Geometry (Good for Initial Testing)
- `model_energy_shoe_box.hbjson` (23 KB) - Basic rectangular room
- `model_complete_single_zone_office.hbjson` (82 KB) - Office with HVAC
- `model_energy_no_program.hbjson` (29 KB) - Geometry only

### HVAC Systems (Test Mechanical)
- `model_energy_doas_hvac.hbjson` (89 KB) - DOAS system
- `model_energy_allair_hvac.hbjson` (89 KB) - All-air system
- `model_energy_window_ac.hbjson` (21 KB) - Window AC units

### Multi-Zone (Stress Testing)
- `model_complete_multi_zone_office.hbjson` (104 KB) - Multiple zones
- `model_complete_office_floor.hbjson` (104 KB) - Full floor layout

### Edge Cases (Validation)
- `model_5vertex_sub_faces.hbjson` (16 KB) - Non-rectangular windows
- `model_complete_holes.hbjson` (27 KB) - Complex apertures
- `model_with_shade_mesh.hbjson` (57 KB) - Shading geometry

### Detailed Models (Full Features)
- `model_energy_fixed_interval.hbjson` (665 KB) - Largest file
- `model_energy_detailed_loads.hbjson` (61 KB) - Detailed loads
- `model_radiance_grid_views.hbjson` (346 KB) - Daylighting

---

## Next Steps

### 1. Schema Extension (4-8 hours)

**Extend EMJSON v6.1 Classes**:

```python
# eco_tools/core/internal_repr.py

@dataclass
class Surface:
    # Existing fields...
    id: str
    name: str
    parent_zone_id: str

    # NEW: Geometry support
    vertices: Optional[List[Dict[str, float]]] = None
    normal: Optional[Dict[str, float]] = None

@dataclass
class Material:
    # Existing fields...
    id: str
    name: str

    # NEW: Thermal properties
    conductivity: Optional[float] = None
    density: Optional[float] = None
    specific_heat: Optional[float] = None
```

### 2. Fix HBJSON Importer

**Update Parameter Names** in `eco_tools/translators/hbjson/importer.py`:
- Lines 129-145: Material constructor
- Lines 159-175: Construction constructor
- Lines 190-200: Schedule constructor
- Lines 290-310: Surface constructor

### 3. Re-Run Validation

```bash
python3 test_hbjson_roundtrip.py
```

**Target**: 80%+ success rate (18/22 files)

### 4. Run Unit Tests

```bash
pytest tests/hbjson/ -v
```

**Target**: All tests passing

---

## Files Created

```
ECO_Alpha_v7/
├── test_hbjson_roundtrip.py              # Main validation script
├── reference_data/
│   └── hbjson_samples/
│       ├── download_all_samples.sh       # Auto-download script
│       └── *.hbjson                      # 22 sample files
├── tests/
│   └── hbjson/
│       ├── __init__.py
│       ├── test_hbjson_importer.py       # Importer tests
│       └── test_hbjson_exporter.py       # Exporter tests
├── test_output/
│   └── hbjson_roundtrip/                 # Validation results
└── docs/
    ├── HBJSON_VALIDATION_REPORT.md       # Detailed analysis
    └── (this file)
```

---

## Testing Workflow

### Phase 1: Fix Schema ✓
1. Extend EMJSON v6.1 classes
2. Add geometry storage
3. Add thermal properties

### Phase 2: Fix Importers ✓
1. Update HBJSON importer
2. Match parameter names to schema
3. Handle optional fields

### Phase 3: Validate ✓
1. Run `test_hbjson_roundtrip.py`
2. Verify 80%+ success rate
3. Check geometry preservation

### Phase 4: Unit Test ✓
1. Run `pytest tests/hbjson/`
2. All tests pass
3. Document any failures

---

## Key Decisions Made

✅ **Download all 22 samples** - Comprehensive coverage
✅ **Create round-trip test** - Automated validation
✅ **Unit test suite** - pytest framework
✅ **Detailed documentation** - Clear path forward

⏳ **Pending**: Schema extension (Option 1)
⏳ **Pending**: Importer fixes
⏳ **Pending**: Re-validation

---

## Success Metrics

| Metric | Current | Target |
|--------|---------|--------|
| Sample files | 22/22 ✅ | 22/22 |
| Test infrastructure | Complete ✅ | Complete |
| Import success | 0% 🔴 | 80%+ |
| Round-trip success | 0% 🔴 | 70%+ |
| Unit tests passing | 0% 🔴 | 90%+ |

---

## Resources

### Documentation
- Full report: `docs/HBJSON_VALIDATION_REPORT.md`
- Honeybee schema: https://github.com/ladybug-tools/honeybee-schema
- Sample models: `reference_data/hbjson_samples/`

### Scripts
- Validation: `test_hbjson_roundtrip.py`
- Unit tests: `tests/hbjson/test_*.py`
- Download: `reference_data/hbjson_samples/download_all_samples.sh`

### Support
- Ladybug Tools forum: https://discourse.ladybug.tools
- Honeybee docs: https://docs.ladybug.tools/honeybee-primer

---

**Setup Complete**: November 14, 2025
**Ready For**: Schema extension and importer fixes
**Estimated Time to Working**: 4-8 hours
