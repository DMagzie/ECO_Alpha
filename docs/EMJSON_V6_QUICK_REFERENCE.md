# EMJSON v6.1 Quick Reference Guide

**Last Updated:** November 13, 2025

---

## Document Overview

This quick reference provides a summary of EMJSON v6.1, the universal energy modeling interchange format used by ECO Tools.

**Related Documents:**
- `EMJSON_V6_SCHEMA.md` - Complete schema definition with all object types
- `EMJSON_V6_SAMPLE.json` - Full working example (290 units, 3,472 surfaces)
- `MODULAR_CIBD_COMPLETE.md` - Modular import/export system documentation

---

## File Structure at a Glance

```json
{
  "schema_version": "6.1",
  "project": { ... },          // Project metadata (required)
  "geometry": {                // Building geometry (required)
    "zones": [...],
    "zone_groups": [...],
    "surfaces": [...],
    "openings": [...]
  },
  "catalogs": {                // Material & component catalogs (required)
    "materials": [...],
    "constructions": [...],
    "window_types": [...],
    "schedules": [...],
    "du_types": [...]
  },
  "systems": {                 // Building systems (required)
    "hvac": [...],
    "zone_terminals": [...],
    "dhw": [...],
    "water_heaters": [...],
    "recirculation_loops": [...],
    "iaq_fans": [...],
    "pv_arrays": [...],
    "battery_systems": [...],
    "lighting_systems": [...],
    "luminaires": [...],
    "fan_systems": [...],
    "heat_pumps": [...],
    "distribution_systems": [...],
    "control_systems": [...]
  },
  "proj_metadata": { ... },    // CBECC project metadata (optional)
  "metadata": { ... },         // General metadata (optional)
  "diagnostics": [...]         // Import/export diagnostics (optional)
}
```

---

## Core Object Types

### Geometry Objects

| Object Type | Description | Key Fields |
|------------|-------------|------------|
| **Zone** | Building zone/space | `id`, `name`, `floor_area_m2`, `zone_type`, `conditioned` |
| **ZoneGroup** | Floor/wing grouping | `id`, `name`, `group_type`, `floor_number`, `zone_refs` |
| **Surface** | Wall/roof/floor | `id`, `parent_zone_id`, `surface_type`, `area_m2`, `construction_ref` |
| **Opening** | Window/door/skylight | `id`, `parent_surface_id`, `type`, `area_m2`, `window_type_ref` |

### Catalog Objects

| Object Type | Description | Key Fields |
|------------|-------------|------------|
| **Material** | Construction layer | `id`, `name`, `material_type`, `r_value_SI`, `thickness_m` |
| **Construction** | Assembly definition | `id`, `name`, `construction_type`, `u_factor_SI`, `material_layers` |
| **WindowType** | Fenestration type | `id`, `name`, `u_factor_SI`, `shgc`, `vt` |
| **Schedule** | Time-based data | `id`, `name`, `schedule_type`, `values`, `hours` |

### System Objects

| Object Type | Description | Key Fields |
|------------|-------------|------------|
| **HVACSystem** | HVAC system | `id`, `name`, `type`, `heating_systems`, `cooling_systems`, `zone_refs` |
| **ZoneTerminal** | Terminal unit | `id`, `parent_hvac_system_id`, `zone_served_ref`, `terminal_type` |
| **DHWSystem** | Hot water system | `id`, `name`, `system_type`, `water_heaters`, `recirculation_loops` |
| **WaterHeater** | Water heater equipment | `id`, `heater_type`, `storage_volume_gal`, `uniform_energy_factor` |
| **PVArray** | Solar PV system | `id`, `array_type`, `rated_capacity_kw`, `tilt_deg`, `azimuth_deg` |
| **BatterySystem** | Energy storage | `id`, `battery_type`, `usable_capacity_kwh`, `round_trip_efficiency` |
| **LightingSystem** | Lighting system | `id`, `space_ref`, `power_density_w_m2`, `control_type` |

---

## HVAC System Types (CBECC Classification)

```typescript
type: 1  // Separate heating + cooling equipment
type: 2  // Heat pump (single equipment for both)
type: 4  // Central system (RTU, boiler/chiller, etc.)
```

**Examples:**

```json
// Type 1: Residential split system
{
  "type": 1,
  "heating_systems": ["Furnace_Gas_80AFUE"],
  "cooling_systems": ["AC_SEER13"]
}

// Type 2: Heat pump
{
  "type": 2,
  "heat_pump_systems": ["ASHP_SEER15_HSPF9"]
}

// Type 4: Central VAV system
{
  "type": 4,
  "central_equipment": ["RTU_GasHeat_DX"],
  "zone_terminals": ["ZnSys_101_VAVR", "ZnSys_102_VAV"]
}
```

---

## Reference Fields

All `*_ref` fields must reference existing object IDs:

| Reference Field | Target Object Type |
|----------------|-------------------|
| `du_ref` | Dwelling unit type (in `du_types`) |
| `construction_ref` | Construction |
| `window_type_ref` | WindowType |
| `fenestration_cons_ref` | Construction |
| `parent_zone_id` | Zone |
| `parent_surface_id` | Surface |
| `parent_hvac_system_id` | HVACSystem |
| `parent_dhw_system_id` | DHWSystem |
| `zone_served_ref` | Zone |
| `adjacent_space_ref` | Zone |
| `schedule_ref` | Schedule |
| `module_ref` | PV module (catalog) |
| `inverter_ref` | Inverter (catalog) |
| `coupled_pv_array_ref` | PVArray |

---

## Surface Types and Subtypes

### surface_type
- `wall` - Vertical surface
- `roof` - Top surface (exterior)
- `floor` - Bottom surface
- `ceiling` - Top surface (interior)

### surface_subtype (CBECC-specific)
- `res_ext_wall` - Residential exterior wall
- `res_int_wall` - Residential interior wall (party wall)
- `res_slab_floor` - Slab-on-grade floor
- `res_raised_floor` - Raised floor over crawlspace/garage
- `res_ceiling` - Ceiling below attic/plenum
- `res_roof` - Roof/ceiling assembly

### adjacency
- `exterior` - Exposed to outside
- `interior` - Adjacent to another zone
- `ground` - In contact with ground
- `adiabatic` - No heat transfer

---

## Title 24 Version Metadata

### Title 24 2022
```json
{
  "ruleset_filename": "T24N_2022.bin",
  "software_version": "CBECC 2022.3.1 (1343)",
  "bldg_engy_model_version": 16
}
```

### Title 24 2025
```json
{
  "ruleset_filename": "T24_2025.bin",
  "software_version": "CBECC 2025.2.0 (1390)",
  "bldg_engy_model_version": 17
}
```

---

## Units Convention

**All measurements use SI units by default:**

| Quantity | Unit | Field Suffix |
|----------|------|-------------|
| Area | square meters | `_m2` |
| Length | meters | `_m` |
| Volume | cubic meters | `_m3` |
| Temperature | Celsius | `_C` |
| U-factor | W/m²·K | `_SI` |
| R-value | m²·K/W | `_SI` |
| Power | Watts | `_w` |
| Energy | Watt-hours | `_wh` |

**Exceptions (imperial units retained for CBECC compatibility):**

| Quantity | Unit | Context |
|----------|------|---------|
| Storage volume | gallons | Water heaters |
| Heat capacity | Btu/h | HVAC equipment |
| Airflow | CFM | Fans, terminals |
| Pipe length | feet | DHW distribution |
| Pipe diameter | inches | DHW distribution |

---

## Common Patterns

### Creating a Residential Unit

```json
{
  "id": "Unit_101",
  "name": "Unit 101 - 2BR/1BA",
  "building_type": "MF",
  "zone_type": "residential",
  "floor_area_m2": 79.0,
  "conditioned": true,
  "du_ref": "DUT_2BR_1BA",
  "served_by": ["HVAC_System_Unit_101"],
  "surfaces": ["Wall_101_N", "Wall_101_S", "Floor_101", "Ceiling_101"]
}
```

### Creating an HVAC System

```json
{
  "id": "HVAC_System_Unit_101",
  "name": "Unit 101 Split System",
  "type": 1,
  "status": 3,
  "heating_systems": ["Furnace_Gas_80AFUE"],
  "heating_counts": [1],
  "cooling_systems": ["AC_SEER13"],
  "cooling_counts": [1],
  "zone_refs": ["Unit_101"],
  "floor_area_served": 79.0
}
```

### Creating a Window

```json
{
  "id": "Win_101_N1",
  "parent_surface_id": "Wall_101_North",
  "type": "window",
  "area_m2": 1.5,
  "window_type_ref": "WT_DblPane_LowE",
  "u_factor_SI": 2.27,
  "shgc": 0.25,
  "vt": 0.40
}
```

### Creating a Construction

```json
{
  "id": "Cons_ExtWall_Wood_R19",
  "name": "Wood Frame Exterior Wall R-19",
  "construction_type": "wall",
  "u_factor_SI": 0.34,
  "r_value_SI": 2.94,
  "material_layers": [
    "Mat_Stucco",
    "Mat_Sheathing",
    "Mat_Insulation_R19",
    "Mat_Gypsum"
  ],
  "framing_config": "16in_oc"
}
```

---

## Validation Rules

1. **Unique IDs**: All `id` fields must be unique within their object type
2. **Reference Integrity**: All `*_ref` fields must reference existing objects
3. **Required Fields**: `id` and `name` are required for all objects
4. **Parent References**: Child objects must reference valid parent IDs
   - Opening → Surface
   - Surface → Zone
   - ZoneTerminal → HVACSystem
   - RecirculationLoop → DHWSystem
5. **Equipment Arrays**: Equipment counts must match equipment array length
6. **Zone Coverage**: All zones should have HVAC assignments (for conditioned zones)

---

## Conversion Between Formats

### CIBD22/22X/25 → EMJSON

```python
from eco_tools.translators.cibd22x import CIBD22XImporter
from dataclasses import asdict

# Import
importer = CIBD22XImporter()
internal = importer.import_file("building.cibd22x")

# Convert to EMJSON
emjson = {
    "schema_version": "6.1",
    "geometry": {
        "zones": [asdict(z) for z in internal.zones],
        "surfaces": [asdict(s) for s in internal.surfaces],
        # ... etc
    }
}
```

### EMJSON → CIBD22/22X/25

```python
from eco_tools.translators.cibd22 import CIBD22Exporter
from eco_tools.translators.cibd22x.exporter import CIBD22XExporter
from eco_tools.translators.cibd25 import CIBD25Exporter

# Export to CIBD22 (Title 24 2022 text)
CIBD22Exporter().export(internal, "building.cibd22")

# Export to CIBD22X (Title 24 2022 XML)
CIBD22XExporter().export_to_file(internal, "building.xml")

# Export to CIBD25 (Title 24 2025 text)
CIBD25Exporter().export(internal, "building.cibd25")
```

---

## Diagnostics

```json
{
  "level": "info" | "warning" | "error",
  "code": "E-IMPORT-FAILED",
  "message": "Human-readable description",
  "stage": "import" | "export" | "validation",
  "ts": "2025-11-13T14:30:00Z",
  "path": "file.cibd22x",
  "source": "cibd22x_importer"
}
```

**Common Diagnostic Codes:**

| Code | Level | Description |
|------|-------|-------------|
| `I-IMPORT-SUCCESS` | info | Successful import |
| `W-SURFACE-NO-CONSTRUCTION` | warning | Surface missing construction |
| `W-ZONE-NO-HVAC` | warning | Conditioned zone without HVAC |
| `W-MATERIAL-COUNT-LOW` | warning | Few materials (may use catalog) |
| `E-IMPORT-FAILED` | error | Import failed |
| `E-REFERENCE-INVALID` | error | Invalid reference |
| `E-EXPORT-FAILED` | error | Export failed |

---

## Best Practices

1. **Use Meaningful IDs**: `Unit_101` not `obj_1234`
2. **Include Annotations**: Store format-specific data in `annotation` fields
3. **Add Diagnostics**: Log import/export issues for debugging
4. **Validate References**: Check all `*_ref` fields resolve before export
5. **Preserve Metadata**: Keep `proj_metadata` for CBECC roundtrip
6. **Version Tracking**: Update `modified_date` on changes
7. **Units Clarity**: Use field suffixes (`_m2`, `_SI`, `_w`)

---

## Tools and Libraries

**Import/Export:**
- `eco_tools/translators/cibd22/` - CIBD22 text format
- `eco_tools/translators/cibd22x/` - CIBD22X XML format
- `eco_tools/translators/cibd25/` - CIBD25 text format
- `eco_tools/translators/hbjson/` - Honeybee JSON

**Data Structures:**
- `eco_tools/core/internal_repr.py` - Python dataclasses

**Validation:**
- `eco_tools/validation/` - Validation utilities

---

## Examples

**Simple Residential Building:**
```bash
# See EMJSON_V6_SAMPLE.json for complete example
cat docs/EMJSON_V6_SAMPLE.json
```

**Test Files:**
```bash
# Format roundtrip test outputs
ls test_output/format_roundtrips/

# Example conversions
python test_complete_roundtrip.py
python test_all_format_roundtrips.py
```

---

## Support

**Documentation:**
- Full Schema: `EMJSON_V6_SCHEMA.md`
- Sample File: `EMJSON_V6_SAMPLE.json`
- Modular System: `MODULAR_CIBD_COMPLETE.md`

**Code:**
- Internal Representation: `eco_tools/core/internal_repr.py:508`
- CIBD22 Importer: `eco_tools/translators/cibd22/importer.py`
- CIBD22X Parsers: `eco_tools/translators/cibd22x/parsers/`
- CIBD25 Exporter: `eco_tools/translators/cibd25/exporter.py`

---

**Last Updated:** November 13, 2025
**Schema Version:** 6.1
**Status:** Production Ready ✅
