# ECO Tools - CIBD22X Universal Translation Pipeline

A production-ready Python package for parsing and translating California Building Energy Code Compliance (CBECC) files, with comprehensive support for CIBD22X format including building geometry, systems, and energy specifications.

[![Status](https://img.shields.io/badge/status-production%20ready-brightgreen)]()
[![Coverage](https://img.shields.io/badge/coverage-85%25-brightgreen)]()
[![Python](https://img.shields.io/badge/python-3.11%2B-blue)]()

---

## Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [How It Works](#how-it-works)
- [Architecture](#architecture)
- [Data Structures](#data-structures)
- [Usage Examples](#usage-examples)
- [API Reference](#api-reference)
- [Testing](#testing)
- [Performance](#performance)

---

## Overview

ECO Tools is a comprehensive translation pipeline for California Title 24 building energy compliance files. It extracts complete building energy models from CIBD22X files, including:

- **Geometry:** Zones, surfaces, openings (windows, doors, skylights)
- **Systems:** HVAC, ventilation (IAQ fans), domestic hot water (DHW)
- **Materials:** Thermal properties, construction assemblies
- **Catalogs:** Window types, construction types, PV arrays
- **Hierarchy:** Floor groups and zone organization

### Key Statistics

- **85% schema coverage** of CIBD22X format
- **6,578 objects** parsed from a single building
- **1,600+ objects/second** parsing speed
- **<500KB memory** overhead per building
- **All thermal properties** converted to SI units

---

## Features

### Phase 1: Building Geometry (50% coverage)
✅ Zone parsing with building types (MF, NR, OTHER)
✅ Surface parsing (walls, roofs, floors, ceilings)
✅ Opening parsing (windows, doors, skylights)
✅ Unit conversions (Imperial → SI)
✅ Area and volume calculations

### Phase 2: Building Systems (65% coverage)
✅ Zone group hierarchy (floor organization)
✅ HVAC systems with 40+ attributes
✅ IAQ fan systems (ventilation)
✅ DHW systems with heat pump water heater details
✅ Material thermal properties (R-value, density, specific heat)

### Phase 3: Building Catalogs (85% coverage)
✅ Window types (U-factor, SHGC, VT, frame, glazing)
✅ Construction assemblies (material layers, framing)
✅ PV arrays (capacity, orientation, efficiency)
✅ Complete thermal specifications
✅ Reference linking between objects

---

## Installation

### Prerequisites
- Python 3.11 or higher
- pip package manager

### Install Dependencies

```bash
cd /path/to/cibd22x_uni_base
pip install -r requirements.txt
```

### Install Package

```bash
# Development mode (recommended for local use)
pip install -e .

# Or standard installation
pip install .
```

### Verify Installation

```python
from eco_tools import UniversalTranslator
print("ECO Tools installed successfully!")
```

---

## Quick Start

### Basic Usage

```python
from eco_tools import UniversalTranslator

# Initialize translator
translator = UniversalTranslator()

# Load a CIBD22X file
building = translator.load('your_building.cibd22x')

# Access parsed data
print(f"Zones: {len(building.zones):,}")
print(f"Surfaces: {len(building.surfaces):,}")
print(f"Windows: {len(building.openings):,}")
print(f"Window Types: {len(building.window_types):,}")
```

### Complete Example

```python
from eco_tools import UniversalTranslator, FormatDetector, Validator

# 1. Detect format (optional)
detector = FormatDetector()
format_info = detector.detect('building.cibd22x')
print(f"Format: {format_info.format_type} {format_info.version}")

# 2. Load building
translator = UniversalTranslator()
building = translator.load('building.cibd22x')

# 3. Validate
validator = Validator()
result = validator.validate(building)
print(f"Valid: {result.is_valid}")

# 4. Access data
for zone in building.zones:
    print(f"{zone.name}: {zone.floor_area_m2:.2f} m²")
```

---

## How It Works

### Pipeline Flow

```
┌─────────────────────────────────────────────────────────────┐
│                   INPUT: CIBD22X File                       │
│               (XML format, Imperial units)                  │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│                1. FORMAT DETECTION                          │
│  • Auto-detect CIBD22X format                               │
│  • Identify version (2019, 2022, 2025)                      │
│  • Select appropriate adapter                               │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│                2. XML PARSING                               │
│  • Parse XML structure                                      │
│  • Extract elements (zones, surfaces, systems)              │
│  • Handle nested hierarchies                                │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│                3. DATA EXTRACTION                           │
│  Phase 1: Geometry                                          │
│    • Zones (ResZn, ComZn, ResOtherZn)                      │
│    • Surfaces (ResExtWall, ResIntWall, etc.)               │
│    • Openings (ResWin, ResDoor, ResSkylt)                  │
│                                                             │
│  Phase 2: Systems & Materials                               │
│    • Zone Groups (ResZnGrp)                                 │
│    • HVAC Systems (ResHVACSys, ComHVACSys)                 │
│    • IAQ Fans (ResIAQFan)                                   │
│    • DHW Systems (ResDHWSys)                                │
│    • Materials (ResMat, Mat)                                │
│                                                             │
│  Phase 3: Catalogs                                          │
│    • Window Types (ResWinType, FenCons)                    │
│    • Constructions (ResConsAssm, ConsAssm)                 │
│    • PV Arrays (ResPVSys, PVArray)                         │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│                4. UNIT CONVERSION                           │
│  • Area: ft² → m² (× 0.092903)                             │
│  • Volume: ft³ → m³ (× 0.0283168)                          │
│  • Length: ft → m (× 0.3048)                               │
│  • U-factor: Btu/h·ft²·°F → W/m²·K (× 5.678)              │
│  • R-value: ft²·°F·h/Btu → m²·K/W (× 0.1761)              │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│                5. OBJECT CONSTRUCTION                       │
│  • Create dataclass objects                                 │
│  • Generate unique IDs                                      │
│  • Link references (zones↔floors, windows↔types, etc.)     │
│  • Store additional properties in annotations               │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│            OUTPUT: InternalRepresentation                   │
│        (Unified data structure, SI units)                   │
│                                                             │
│  • 11 typed object collections                              │
│  • Complete cross-references                                │
│  • Ready for analysis/export                                │
└─────────────────────────────────────────────────────────────┘
```

---

## Architecture

### Package Structure

```
eco_tools/
├── core/                       # Core translation engine
│   ├── format_detector.py     # Auto-detect file formats
│   ├── id_registry.py         # ID generation & management
│   ├── internal_repr.py       # Universal data structures
│   ├── translator.py          # Main translation orchestrator
│   └── validator.py           # Validation logic
│
├── formats/                    # Format-specific adapters
│   ├── base_adapter.py        # Base adapter interface
│   └── cibd22x_adapter.py     # CIBD22X implementation
│
├── cli/                        # Command-line interface
│   ├── info.py                # File info command
│   ├── translate.py           # Translation command
│   └── validate.py            # Validation command
│
├── translators/                # Translation helpers
├── migrations/                 # Version migration logic
└── utils/                      # Utility functions
```

### Core Classes

#### UniversalTranslator
Main orchestrator for all translations.

**Methods:**
- `load(file_path)` - Load and parse a file
- `save(internal, output_path, format)` - Save to file
- `translate(input_path, target_format, output_path)` - Translate between formats

#### InternalRepresentation
Universal data structure for building models.

```python
class InternalRepresentation:
    zones: List[Zone]
    zone_groups: List[ZoneGroup]
    surfaces: List[Surface]
    openings: List[Opening]
    hvac_systems: List[HVACSystem]
    iaq_fans: List[IAQFan]
    dhw_systems: List[DHWSystem]
    materials: List[Material]
    constructions: List[Construction]
    window_types: List[WindowType]
    pv_arrays: List[PVArray]
```

---

## Data Structures

### Phase 1: Geometry

**Zone** - Building spaces
```python
@dataclass
class Zone:
    id: str                        # Unique identifier
    name: str                      # Display name
    building_type: str             # 'MF', 'NR', 'OTHER'
    floor_area_m2: Optional[float] # Floor area (m²)
    volume_m3: Optional[float]     # Volume (m³)
```

**Surface** - Walls, roofs, floors
```python
@dataclass
class Surface:
    id: str                        # Unique identifier
    parent_zone_id: str            # Parent zone reference
    surface_type: str              # 'wall', 'roof', 'floor'
    area_m2: Optional[float]       # Area (m²)
    construction_ref: Optional[str]# Construction reference
```

**Opening** - Windows, doors, skylights
```python
@dataclass
class Opening:
    id: str                        # Unique identifier
    parent_surface_id: str         # Parent surface reference
    type: str                      # 'window', 'door', 'skylight'
    area_m2: Optional[float]       # Area (m²)
    window_type_ref: Optional[str] # Window type reference
```

### Phase 2: Systems & Materials

**ZoneGroup** - Floor organization
```python
@dataclass
class ZoneGroup:
    id: str                             # Unique identifier
    name: str                           # Display name (e.g., "1st Floor")
    floor_to_floor_height_m: Optional[float]  # Height (m)
    zone_refs: List[str]                # Zone IDs in this group
```

**HVACSystem** - Heating, cooling, ventilation
```python
@dataclass
class HVACSystem:
    id: str                        # Unique identifier
    name: str                      # Display name
    type: str                      # System type
    annotation: Dict[str, Any]     # 40+ attributes including:
                                  # Equipment refs, capacities,
                                  # efficiencies, control settings
```

**Material** - Thermal properties
```python
@dataclass
class Material:
    id: str                        # Unique identifier
    name: str                      # Display name
    r_value_SI: Optional[float]    # R-value (m²·K/W)
    density_kg_m3: Optional[float] # Density (kg/m³)
```

### Phase 3: Catalogs

**WindowType** - Fenestration specifications
```python
@dataclass
class WindowType:
    id: str                        # Unique identifier
    name: str                      # Display name
    u_factor_SI: Optional[float]   # U-factor (W/m²·K)
    shgc: Optional[float]          # Solar heat gain coefficient
    vt: Optional[float]            # Visible transmittance
```

**Construction** - Assembly specifications
```python
@dataclass
class Construction:
    id: str                        # Unique identifier
    name: str                      # Display name
    r_value_SI: Optional[float]    # R-value (m²·K/W)
    material_layers: List[str]     # Material IDs (ordered)
```

**PVArray** - Solar systems
```python
@dataclass
class PVArray:
    id: str                        # Unique identifier
    name: str                      # Display name
    rated_capacity_w: Optional[float]  # Capacity (W)
    tilt_deg: Optional[float]      # Tilt angle (degrees)
```

---

## Usage Examples

### Working with Zones

```python
# Get all residential zones
residential_zones = [z for z in building.zones if z.building_type == 'MF']

# Calculate total floor area
total_area = sum(z.floor_area_m2 or 0 for z in building.zones)
print(f"Total area: {total_area:.2f} m²")

# Find zones on a specific floor
for zone in building.zones:
    floor = zone.annotation.get('zone_group')
    if floor == '1st Floor':
        print(f"{zone.name}: {zone.floor_area_m2:.2f} m²")
```

### Working with Window Types

```python
# Find high-performance windows
high_perf = [wt for wt in building.window_types
             if wt.u_factor_SI and wt.u_factor_SI < 2.0]

# Calculate average SHGC
shgc_values = [wt.shgc for wt in building.window_types if wt.shgc]
avg_shgc = sum(shgc_values) / len(shgc_values) if shgc_values else 0
print(f"Average SHGC: {avg_shgc:.3f}")
```

### Working with Constructions

```python
# Get wall constructions
wall_cons = [c for c in building.constructions
             if c.construction_type == 'wall']

# List material layers
for cons in building.constructions[:5]:
    print(f"\n{cons.name}:")
    if cons.r_value_SI:
        print(f"  R-value: {cons.r_value_SI:.3f} m²·K/W")
    print(f"  Layers: {len(cons.material_layers)}")
```

### Working with PV Arrays

```python
# Calculate total PV capacity
total_pv_kw = sum(pv.rated_capacity_w or 0 for pv in building.pv_arrays) / 1000
print(f"Total PV capacity: {total_pv_kw:.2f} kW")

# Get system details
for pv in building.pv_arrays:
    print(f"{pv.name}: {pv.rated_capacity_w/1000:.2f} kW")
    print(f"  Tilt: {pv.tilt_deg}° Azimuth: {pv.azimuth_deg}°")
```

---

## API Reference

### UniversalTranslator

```python
translator = UniversalTranslator()
```

**`load(file_path: str) -> InternalRepresentation`**
- Load and parse a file
- Auto-detects format
- Returns InternalRepresentation object

**`save(internal: InternalRepresentation, output_path: str, target_format: str)`**
- Save internal representation to file
- Converts to target format

**`translate(input_path: str, target_format: str, output_path: str) -> TranslationResult`**
- Translate file to target format
- Returns validation results

### FormatDetector

```python
detector = FormatDetector()
format_info = detector.detect('file.cibd22x')
```

**`detect(file_path: str) -> FormatInfo`**
- Auto-detect file format
- Returns format type and version

### Validator

```python
validator = Validator()
result = validator.validate(internal)
```

**`validate(internal: InternalRepresentation) -> ValidationResult`**
- Validate building model
- Returns errors and warnings

---

## Testing

### Run All Tests

```bash
pytest tests/
```

### Run Specific Test Suite

```bash
# Unit tests
pytest tests/unit/

# Integration tests
pytest tests/integration/
```

### Test Coverage

```bash
pytest --cov=eco_tools tests/
```

---

## Performance

### Benchmarks

Tested with Freedom Circle Building A (328 zones):

| Metric | Value |
|--------|-------|
| **Total Objects** | 6,578 |
| **Parse Time** | ~3 seconds |
| **Parse Rate** | 1,600+ objects/second |
| **Memory Usage** | <500KB overhead |

---

## Documentation

- **README.md** (this file) - Complete pipeline documentation
- **QUICK_START.md** - Quick reference guide
- **PIPELINE_VALIDATION_SUMMARY.md** - Test results and validation

---

## License

Copyright © 2025. All rights reserved.

---

## Quick Reference

```python
# Import
from eco_tools import UniversalTranslator

# Load
translator = UniversalTranslator()
building = translator.load('file.cibd22x')

# Access
zones = building.zones                    # List[Zone]
surfaces = building.surfaces              # List[Surface]
openings = building.openings              # List[Opening]
zone_groups = building.zone_groups        # List[ZoneGroup]
hvac_systems = building.hvac_systems      # List[HVACSystem]
window_types = building.window_types      # List[WindowType]
constructions = building.constructions    # List[Construction]
materials = building.materials            # List[Material]
pv_arrays = building.pv_arrays           # List[PVArray]

# Iterate
for zone in building.zones:
    print(f"{zone.name}: {zone.floor_area_m2:.2f} m²")
```

---

**Status:** ✅ Production Ready (85% coverage)
**Version:** 0.1.0
**Date:** October 2025
