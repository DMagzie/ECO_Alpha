# Quick Start Guide - CIBD22X Translation Pipeline

## Installation

```bash
cd /Users/DavidM/Documents/ECO_Alpha/cibd22x_uni_base
pip install -r requirements.txt
pip install -e .
```

## Basic Usage

```python
from eco_tools import UniversalTranslator

# Load a CIBD22X file
translator = UniversalTranslator()
building = translator.load('your_file.cibd22x')

# Access building data
print(f"Zones: {len(building.zones)}")
print(f"Surfaces: {len(building.surfaces)}")
print(f"Windows: {len(building.openings)}")
```

## What You Can Extract

### Phase 1: Building Geometry
```python
# Zones
for zone in building.zones:
    print(f"{zone.name}: {zone.floor_area_m2:.2f} m²")

# Surfaces (walls, roofs, floors)
for surface in building.surfaces:
    print(f"{surface.name}: {surface.area_m2:.2f} m²")

# Openings (windows, doors)
for opening in building.openings:
    print(f"{opening.type}: {opening.area_m2:.2f} m²")
```

### Phase 2: Building Systems
```python
# Zone hierarchy (floors)
for floor in building.zone_groups:
    print(f"{floor.name}: {len(floor.zone_refs)} zones")

# HVAC systems
for hvac in building.hvac_systems:
    print(f"{hvac.name}: {hvac.type}")

# Materials
for material in building.materials:
    if material.r_value_SI:
        print(f"{material.name}: R={material.r_value_SI:.3f}")
```

### Phase 3: Building Catalogs
```python
# Window types
for wt in building.window_types:
    if wt.u_factor_SI:
        print(f"{wt.name}: U={wt.u_factor_SI:.3f} W/m²·K")

# Constructions
for cons in building.constructions:
    if cons.r_value_SI:
        print(f"{cons.name}: R={cons.r_value_SI:.3f} m²·K/W")

# PV arrays
for pv in building.pv_arrays:
    if pv.rated_capacity_w:
        print(f"{pv.name}: {pv.rated_capacity_w/1000:.2f} kW")
```

## Real Example

```python
from eco_tools import UniversalTranslator

# Load Freedom Circle building
translator = UniversalTranslator()
building = translator.load('Freedom Circle_Building A - LEED.cibd22x')

# Show summary
print(f"Building has:")
print(f"  {len(building.zones):,} zones")
print(f"  {len(building.surfaces):,} surfaces")
print(f"  {len(building.window_types):,} window types")
print(f"  {len(building.pv_arrays)} PV arrays")

# Expected output:
# Building has:
#   328 zones
#   3,344 surfaces
#   1,367 window types
#   2 PV arrays
```

## Running Tests

```bash
# Run all tests
pytest tests/

# Run specific test
pytest tests/unit/test_format_detector.py
```

## Getting Help

See `README.md` for detailed documentation.
See `PIPELINE_VALIDATION_SUMMARY.md` for validation results.

---

**Status:** ✅ Production Ready (85% schema coverage)
**Performance:** 1,600+ objects/second
**Objects Parsed:** 6,578 from single building
