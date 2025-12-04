# CIBD25 Translator Consolidation Plan

**Date:** December 2, 2025
**Status:** Planning
**Goal:** Single unified EMJSON → CIBD25 translator with all V7 lessons learned

---

## Executive Summary

We currently have two parallel CIBD25 export paths:
1. **V7 Translator** (`cibd_xml_to_text.py`) - Battle-tested, 7 production models verified
2. **DirectWriter** (`cibd25/direct_writer.py`) - Newer, cleaner architecture, incomplete

This plan consolidates both into a single well-architected translator.

---

## Current State

### V7 Translator (`cibd_xml_to_text.py`)
- **Input:** CIBD22X XML
- **Output:** CIBD25 text
- **Status:** Production-ready, all fixes implemented
- **Fixes included:** #39-44 (element ordering, deprecated properties, required defaults)
- **Test coverage:** 7 models verified in CBECC 2025 GUI

### DirectWriter (`cibd25/direct_writer.py`)
- **Input:** EMJSON v6
- **Output:** CIBD25 text
- **Status:** Framework complete, implementation incomplete (many TODOs)
- **Missing:** V7 property filtering, element ordering logic
- **Advantage:** No XML intermediate step

### The Problem
- Duplicate code paths = duplicate maintenance
- V7 lessons not in DirectWriter
- Risk of divergent behavior

---

## Target Architecture

```
                    ┌──────────────────────────────────┐
                    │      CIBD25PropertyRules         │
                    │  (Single source of truth)        │
                    │                                  │
                    │  - DEPRECATED_PROPERTIES         │
                    │  - REQUIRED_DEFAULTS             │
                    │  - ELEMENT_PRIORITIES            │
                    │  - SKIP_ELEMENTS                 │
                    └──────────────────────────────────┘
                                    │
                                    ▼
CIBD22X ──→ EMJSON ──┐    ┌─────────────────────┐
                     │    │                     │
IDF ──────→ EMJSON ──┼───→│   CIBD25Writer      │───→ CIBD25
                     │    │   (Unified)         │
gbXML ────→ EMJSON ──┘    │                     │
                          └─────────────────────┘
```

**Key principle:** All exports flow through EMJSON → CIBD25Writer

---

## V7 Lessons to Port

These fixes from `cibd_xml_to_text.py` must be incorporated:

### 1. Deprecated Properties (MUST FILTER)

| Property | Context | Effect if Present |
|----------|---------|-------------------|
| `VentSpcFunc` | ResZn, ResOtherZn | DwellUnitType not recognized |
| `PVBattSizeBldgType` | ResZn, ResOtherZn, DwellUnit | GUI stalls/hangs |
| `BattReq_PartOfLargeTenantArea` | ResZn, ResOtherZn, DwellUnit | GUI stalls/hangs |
| `MassThickness` | ResConsAssm | Validation warnings |

### 2. Required Property Defaults

| Element | Property | Default | Notes |
|---------|----------|---------|-------|
| ResCentralVentSys | Type | "Balanced" | Required or GUI stalls |
| ResZn | Type | "Conditioned" | Default if missing |
| ResOtherZn | Type | "Unconditioned" | Default if missing |

### 3. Elements to Skip

| Element | Reason |
|---------|--------|
| `Batt` | Battery storage not properly supported in CIBD25 text format |

### 4. Element Ordering (Priorities)

```
Priority 80-85:   HVAC Components (ResHtgSys, ResClgSys, etc.) - BEFORE Bldg
Priority 100:     Bldg
Priority 200:     Commercial HVAC (AirSys, FluidSys, etc.)
Priority 300:     Schedules (SchDay, SchWeek)
Priority 500:     Construction catalog (Mat, ConsAssm, FenCons)
Priority 600:     Equipment (Lum, WtrHtr, Chiller, etc.)
Priority 900:     DwellUnitType - AFTER all DwellUnit instances
Priority 950:     HVAC Systems (ResHVACSys, ResDHWSys) - AFTER DwellUnitType
Priority 1000:    Report objects (always last)
```

### 5. Version Markers

- `RunTitle` = "Title 24 2025 Compliance"
- `SoftwareVersion` = "CBECC 2025.2.0 (ECO Tools)"
- No `END_OF_FILE` marker

---

## Implementation Phases

### Phase 1: Create Shared Rules Module
**File:** `cibd25/property_rules.py`

```python
"""
CIBD25 Property Rules - Single source of truth for all CIBD25 export logic.

This module captures ALL lessons learned from V7 translator development.
Both DirectWriter and any legacy code paths should use these rules.
"""

# Properties that MUST be filtered (cause GUI issues)
DEPRECATED_PROPERTIES = {
    'VentSpcFunc',                    # Fix #41 - Invalid on ResZn/ResOtherZn
    'PVBattSizeBldgType',             # Fix #44 - Causes GUI stall
    'BattReq_PartOfLargeTenantArea',  # Fix #44 - Causes GUI stall
    'MassThickness',                  # Validation warnings
}

# Properties deprecated only on specific element types
DEPRECATED_ON_ELEMENT = {
    'ResZn': ['VentSpcFunc', 'PVBattSizeBldgType', 'BattReq_PartOfLargeTenantArea'],
    'ResOtherZn': ['VentSpcFunc', 'PVBattSizeBldgType', 'BattReq_PartOfLargeTenantArea'],
    'DwellUnit': ['PVBattSizeBldgType', 'BattReq_PartOfLargeTenantArea'],
}

# Elements to completely skip during conversion
SKIP_ELEMENTS = {'Batt'}  # Fix #43 - Battery not supported in text format

# Required defaults when property is missing
REQUIRED_DEFAULTS = {
    'ResCentralVentSys': {'Type': 'Balanced'},  # Fix #43
    'ResZn': {'Type': 'Conditioned'},
    'ResOtherZn': {'Type': 'Unconditioned'},
}

# Element ordering priorities (lower = earlier in file)
ELEMENT_PRIORITIES = {
    # HVAC Components (before Bldg)
    'ResHtgSys': 80,
    'ResClgSys': 80,
    'ResHtPumpSys': 81,
    'ResFanSys': 82,
    'ResCentralVentSys': 83,
    'ResDistSys': 84,
    'ResIAQFan': 85,
    'ResLpTankHtr': 85,

    # Building structure
    'Bldg': 100,

    # Commercial HVAC
    'AirSys': 200,
    'FluidSys': 200,
    'VRFSys': 200,
    'ZnSys': 200,

    # Schedules
    'SchDay': 300,
    'SchWeek': 300,
    'Sch': 300,
    'ResProj': 300,
    'ProjVar': 300,

    # Construction catalog
    'ResConsAssm': 500,
    'ResMat': 500,
    'ResWinType': 500,
    'ConsAssm': 500,
    'Mat': 500,
    'FenCons': 500,
    'DrCons': 500,

    # Equipment
    'Lum': 600,
    'WtrHtr': 600,
    'Chiller': 600,
    'Boiler': 600,
    'Pump': 600,
    'ThrmlEngyStor': 600,
    'PVArray': 600,

    # Type definitions (AFTER instances)
    'DwellUnitType': 900,

    # HVAC systems (AFTER DwellUnitType)
    'ResHVACSys': 950,
    'ResDHWSys': 950,
    'ResWtrHtr': 950,

    # Reports (always last)
    'ResDHWSysRpt': 1000,
    'DwellUnitRpt': 1000,
}

# Root-level elements that must be deferred for proper ordering
DEFER_ROOT_ELEMENTS = {
    'DwellUnitType',
    'ResHVACSys',
    'ResDHWSys',
    'ResWtrHtr',
}


def should_skip_element(element_type: str) -> bool:
    """Check if element should be completely skipped."""
    return element_type in SKIP_ELEMENTS


def should_skip_property(element_type: str, prop_name: str) -> bool:
    """Check if property should be filtered for this element type."""
    # Global deprecated properties
    if prop_name in DEPRECATED_PROPERTIES:
        return True

    # Element-specific deprecated properties
    element_deprecated = DEPRECATED_ON_ELEMENT.get(element_type, [])
    if prop_name in element_deprecated:
        return True

    return False


def get_required_defaults(element_type: str) -> dict:
    """Get required default properties for element type."""
    return REQUIRED_DEFAULTS.get(element_type, {})


def get_element_priority(element_type: str) -> int:
    """Get sorting priority for element type (lower = earlier)."""
    return ELEMENT_PRIORITIES.get(element_type, 500)  # Default to catalog priority
```

**Deliverable:** Single module containing all V7 rules

---

### Phase 2: Update DirectWriter to Use Rules

**Changes to `direct_writer.py`:**

1. Import and use `property_rules` module
2. Call `should_skip_element()` before writing elements
3. Call `should_skip_property()` before writing properties
4. Call `get_required_defaults()` to add missing required properties
5. Use `get_element_priority()` for ordering deferred elements

**Example integration:**

```python
from .property_rules import (
    should_skip_element,
    should_skip_property,
    get_required_defaults,
    get_element_priority
)

class CIBD25DirectWriter:
    def _write_element(self, element_type: str, element_data: dict) -> None:
        # Skip entire elements
        if should_skip_element(element_type):
            logger.debug(f"Skipping element {element_type} (in SKIP_ELEMENTS)")
            return

        # Add required defaults
        defaults = get_required_defaults(element_type)
        for prop, value in defaults.items():
            if prop not in element_data:
                element_data[prop] = value

        # Filter properties
        filtered_props = {
            k: v for k, v in element_data.items()
            if not should_skip_property(element_type, k)
        }

        # Write element with filtered properties
        self._write_element_properties(element_type, filtered_props)
```

**Deliverable:** DirectWriter using shared rules

---

### Phase 3: Update ElementWriter

**Changes to `element_writer.py`:**

1. Remove TODO comments, implement actual filtering
2. Use `property_rules` for all filtering decisions
3. Ensure ResidentialElementWriter filters VentSpcFunc

**Deliverable:** Complete ElementWriter implementation

---

### Phase 4: Create Legacy Wrapper

**File:** `cibd_xml_to_text_wrapper.py`

For backward compatibility, wrap the new DirectWriter:

```python
"""
Legacy wrapper - CIBD22X XML → CIBD25 via DirectWriter

This maintains backward compatibility for CLI tools that expect
XML input. Internally converts to EMJSON first, then uses DirectWriter.
"""

from eco_tools.translators.cibd22x.parsers import parse_cibd22x
from eco_tools.translators.cibd25 import CIBD25DirectWriter


def convert_cibd22x_to_cibd25(input_path: str, output_path: str) -> bool:
    """
    Convert CIBD22X XML to CIBD25 text format.

    This is a legacy wrapper that:
    1. Parses CIBD22X to EMJSON
    2. Uses CIBD25DirectWriter to produce CIBD25

    Args:
        input_path: Path to .cibd22x file
        output_path: Path to output .cibd25 file

    Returns:
        True if successful
    """
    # Parse XML to EMJSON
    emjson = parse_cibd22x(input_path)

    # Use unified DirectWriter
    writer = CIBD25DirectWriter(emjson)
    return writer.write_file(output_path)
```

**Deliverable:** CLI backward compatibility maintained

---

### Phase 5: Update GUI Integration

**File:** `gui/translators.py`

Update to use unified DirectWriter:

```python
def emjson6_to_cibd25(emjson_data: dict, output_path: str) -> bool:
    """
    Export EMJSON v6 to CIBD25 format.

    Uses the unified CIBD25DirectWriter with all V7 lessons learned.
    """
    from eco_tools.translators.cibd25 import CIBD25DirectWriter

    writer = CIBD25DirectWriter(emjson_data)
    return writer.write_file(output_path)


# Remove emjson6_to_cibd25_direct and emjson6_to_cibd25_legacy
# There is now only ONE path
```

**Deliverable:** Single GUI export path

---

### Phase 6: Testing

1. **Unit tests** for `property_rules.py`
2. **Integration tests** comparing output to V7 translator
3. **Regression tests** with all 7 verified models:
   - Freedom_Circle_A (157 DwellUnits)
   - Freedom_Circle_B (182 DwellUnits)
   - Euclid_A (82 DwellUnits)
   - Euclid_B (73 DwellUnits)
   - Euclid_C (13 DwellUnits)
   - Del_Amo_Circle (88 DwellUnits)
   - Mainplace_Mall (124 DwellUnits)

**Test criteria:**
- Command-line validation: `button returned:OK`
- GUI opens without stalling
- DwellUnitTypes display correctly
- All associations intact

---

## File Changes Summary

| File | Action |
|------|--------|
| `cibd25/property_rules.py` | **CREATE** - Shared rules module |
| `cibd25/direct_writer.py` | **UPDATE** - Use property_rules |
| `cibd25/element_writer.py` | **UPDATE** - Use property_rules |
| `cibd_xml_to_text.py` | **KEEP** - Mark as legacy, eventually deprecate |
| `cibd_xml_to_text_wrapper.py` | **CREATE** - Legacy CLI wrapper |
| `gui/translators.py` | **UPDATE** - Single export path |

---

## Success Criteria

1. **Single code path** for CIBD25 export
2. **All V7 fixes** incorporated in DirectWriter
3. **All 7 test models** pass (CLI + GUI)
4. **Backward compatibility** maintained for CLI tools
5. **Documentation** updated

---

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| DirectWriter incomplete | Keep V7 translator as fallback during transition |
| Breaking CLI tools | Legacy wrapper maintains compatibility |
| Missing edge cases | Extensive testing with production models |
| EMJSON parsing issues | Existing CIBD22X→EMJSON parser is stable |

---

## Timeline Estimate

| Phase | Effort |
|-------|--------|
| Phase 1: Property Rules | 1-2 hours |
| Phase 2: DirectWriter Update | 2-4 hours |
| Phase 3: ElementWriter | 1-2 hours |
| Phase 4: Legacy Wrapper | 1 hour |
| Phase 5: GUI Integration | 1 hour |
| Phase 6: Testing | 2-4 hours |

**Total:** 8-14 hours of focused work

---

## Next Steps

1. [ ] Review and approve this plan
2. [ ] Create `property_rules.py` with all V7 lessons
3. [ ] Update DirectWriter to use shared rules
4. [ ] Test with production models
5. [ ] Update GUI integration
6. [ ] Mark V7 translator as legacy

---

*Plan created as part of ECO_Alpha_v7 translator consolidation.*
