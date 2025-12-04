# CIBD Input/Output for EMJSON Architecture

## Overview

This document describes the bidirectional translation architecture between California Building Energy Compliance Data (CIBD) formats and EMJSON v6, enabling seamless conversion between Title 24 2022 and 2025 compliance formats.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         CIBD ↔ EMJSON Translation                           │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   ┌─────────────┐      ┌─────────────┐      ┌─────────────┐                │
│   │  CIBD22X    │      │   EMJSON    │      │   CIBD25    │                │
│   │    (XML)    │◄────►│     v6      │◄────►│   (Text)    │                │
│   └─────────────┘      └─────────────┘      └─────────────┘                │
│         ▲                    ▲                    ▲                         │
│         │                    │                    │                         │
│         ▼                    │                    ▼                         │
│   ┌─────────────┐            │              ┌─────────────┐                │
│   │   CIBD22    │◄───────────┴──────────────►   CBECC     │                │
│   │   (Text)    │                           │  Validator  │                │
│   └─────────────┘                           └─────────────┘                │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Supported Formats

### 1. CIBD22X (XML Format)
- **Extension**: `.cibd22x`
- **Standard**: Title 24 2022
- **Structure**: XML with nested elements
- **Source**: CBECC 2022 GUI exports, legacy building models

### 2. CIBD22 (Text Format)
- **Extension**: `.cibd22`
- **Standard**: Title 24 2022
- **Ruleset**: `T24_2022.bin`
- **Structure**: Property-based text with `..` terminators

### 3. CIBD25 (Text Format)
- **Extension**: `.cibd25`
- **Standard**: Title 24 2025
- **Ruleset**: `T24_2025.bin`
- **Structure**: Property-based text with `..` terminators
- **Target**: CBECC 2025 compliance software

### 4. EMJSON v6 (Internal Format)
- **Structure**: JSON with standardized schema
- **Purpose**: Unified internal representation
- **Features**: Rich annotations, geometry, HVAC systems, DHW

---

## Module Structure

```
eco_tools/translators/
├── cibd22x/                    # XML format importer
│   ├── importer.py             # Main CIBD22XImporter class
│   └── parsers/                # Modular element parsers
│       ├── base_parser.py
│       ├── proj_parser.py
│       ├── zone_parser.py
│       ├── zone_group_parser.py
│       ├── surface_parser.py
│       ├── opening_parser.py
│       ├── material_parser.py
│       ├── construction_parser.py
│       └── ...
│
├── cibd22/                     # CIBD22 text format
│   └── text_parser.py          # Text → XML conversion
│
├── cibd25/                     # CIBD25 text format
│   └── direct_writer.py        # EMJSON → CIBD25 text
│
├── cibd_text/                  # Unified text translator
│   ├── __init__.py             # Public API
│   ├── version_config.py       # Version-specific settings
│   ├── parser.py               # Unified text parser
│   └── writer.py               # Unified text writer
│
└── CIBD_CONVERSION_FIXES.md    # Fix history documentation
```

---

## Translation Pipeline

### Import Pipeline (CIBD → EMJSON)

```
┌──────────────┐    ┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│  CIBD File   │───►│ Text Parser  │───►│  XML Tree    │───►│   EMJSON     │
│ (.cibd22/25) │    │ (Unified)    │    │ (Structured) │    │     v6       │
└──────────────┘    └──────────────┘    └──────────────┘    └──────────────┘
                           │
                           ▼
                    ┌──────────────┐
                    │  Reorganize  │
                    │ Zones/Surfs  │
                    └──────────────┘
```

**Stages:**
1. **Text Parsing**: Convert property-based text to structured objects
2. **Zone Reorganization**: Nest zones inside zone groups (sequential ordering)
3. **Surface Reorganization**: Nest surfaces inside zones (name matching)
4. **Opening Reorganization**: Nest openings inside surfaces
5. **XML Conversion**: Build ElementTree structure
6. **EMJSON Translation**: Use CIBD22X parsers to extract to EMJSON

### Export Pipeline (EMJSON → CIBD)

```
┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│   EMJSON     │───►│ DirectWriter │───►│  CIBD File   │
│     v6       │    │ (Versioned)  │    │ (.cibd22/25) │
└──────────────┘    └──────────────┘    └──────────────┘
                           │
                           ▼
                    ┌──────────────┐
                    │  Version     │
                    │  Patching    │
                    └──────────────┘
```

**Stages:**
1. **DirectWriter**: Convert EMJSON to CIBD25 text format
2. **Version Patching**: Apply version-specific settings (ruleset, software version)
3. **File Output**: Write to disk with correct extension

---

## Public API

### Primary Functions

```python
from eco_tools.translators.cibd_text import (
    translate_to_emjson,
    translate_from_emjson,
    CIBDVersion,
)
```

### Import: CIBD → EMJSON

```python
def translate_to_emjson(
    file_path: str,
    version: CIBDVersion = None
) -> Dict[str, Any]:
    """
    Translate CIBD text file to EMJSON v6 format.

    Supports both CIBD22 and CIBD25 text formats.
    Version is auto-detected if not specified.

    Args:
        file_path: Path to CIBD text file (.cibd22 or .cibd25)
        version: Target version (auto-detected if None)

    Returns:
        EMJSON v6 dictionary with diagnostics
    """
```

**Example:**
```python
# Auto-detect version from file extension
emjson = translate_to_emjson('building.cibd25')

# Access geometry
zones = emjson['geometry']['zones']
surfaces = emjson['geometry']['surfaces']
zone_groups = emjson['geometry']['zone_groups']

# Access systems
hvac = emjson['systems']['hvac']
dhw = emjson['systems']['dhw']
```

### Export: EMJSON → CIBD

```python
def translate_from_emjson(
    emjson: Dict[str, Any],
    output_path: str,
    version: CIBDVersion = CIBDVersion.CIBD25
) -> bool:
    """
    Translate EMJSON v6 to CIBD text format.

    Supports output to both CIBD22 and CIBD25 formats.

    Args:
        emjson: EMJSON v6 dictionary
        output_path: Path to output file
        version: Target version (default: CIBD25)

    Returns:
        True if successful, False otherwise
    """
```

**Example:**
```python
# Export to CIBD25 (Title 24 2025)
translate_from_emjson(emjson, 'output.cibd25', version=CIBDVersion.CIBD25)

# Export to CIBD22 (Title 24 2022)
translate_from_emjson(emjson, 'output.cibd22', version=CIBDVersion.CIBD22)
```

---

## Version Configuration

### CIBDVersion Enum

```python
from enum import Enum

class CIBDVersion(Enum):
    CIBD22 = "22"  # Title 24 2022
    CIBD25 = "25"  # Title 24 2025
```

### Version-Specific Settings

| Setting | CIBD22 | CIBD25 |
|---------|--------|--------|
| Ruleset | `T24_2022.bin` | `T24_2025.bin` |
| Software Version | `CBECC 2022.3.0 (ECO Tools)` | `CBECC 2025.2.0 (ECO Tools)` |
| Run Title | `Title 24 2022 Compliance` | `Title 24 2025 Compliance` |

---

## EMJSON v6 Structure

### Top-Level Schema

```json
{
    "schema_version": "6.0",
    "project": {
        "name": "Building Name",
        "description": "Project description",
        "location": { ... }
    },
    "geometry": {
        "zones": [ ... ],
        "zone_groups": [ ... ],
        "surfaces": [ ... ],
        "openings": [ ... ]
    },
    "catalogs": {
        "materials": [ ... ],
        "constructions": [ ... ],
        "window_types": [ ... ],
        "schedules": [ ... ],
        "du_types": [ ... ]
    },
    "systems": {
        "hvac": [ ... ],
        "dhw": [ ... ],
        "water_heaters": [ ... ],
        "iaq_fans": [ ... ],
        "pv_arrays": [ ... ],
        "battery_systems": [ ... ]
    },
    "proj_metadata": {
        "ResProj": { ... },
        "ProjVar": { ... }
    },
    "diagnostics": [ ... ]
}
```

### Zone Object

```json
{
    "id": "Z_zone1",
    "name": "Zone1",
    "type": "Conditioned",
    "floor_area_m2": 92.9,
    "floor_to_ceiling_height": 2.74,
    "space_function": "Office - Open",
    "conditioned": true,
    "annotation": {
        "xml_tag": "ResZn",
        "parent_zone_group_id": "ZG_floor_1",
        "zone_group": "Floor 1",
        "original_floor_area_ft": "1000"
    }
}
```

### Zone Group Object

```json
{
    "id": "ZG_floor_1",
    "name": "Floor 1",
    "z_height": 0,
    "floor_to_floor_height": 3.05,
    "zone_refs": ["Z_zone1", "Z_zone2"],
    "annotation": {
        "xml_tag": "ResZnGrp",
        "TreeState": "254"
    }
}
```

### Surface Object

```json
{
    "id": "S_zone1_wall_n",
    "name": "Zone1WallNorth",
    "surface_type": "ExteriorWall",
    "parent_zone_id": "Z_zone1",
    "area_m2": 18.58,
    "tilt": 90,
    "azimuth": 0,
    "construction_ref": "CONS_exterior_wall",
    "annotation": {
        "xml_tag": "ResExtWall",
        "Orientation": "Front"
    }
}
```

---

## CIBD Text Format Reference

### Basic Structure

```
RulesetFilename   "T24_2025.bin"

Proj   "Project Name"
   BldgEngyModelVersion = 17
   GeometryInpType = "Simplified"
   ..

ResProj   "Residential Project"
   StdDesignFuel_HVAC = "Electricity"
   ..

Bldg   "Building"
   BldgAz = 0
   ..

ResZnGrp   "Floor 1"
   TreeState = 254
   ..

ResZn   "Zone1"
   Type = "Conditioned"
   FloorArea = 1000
   CeilingHeight = 9
   ..

ResExtWall   "Zone1WallFront"
   Orientation = "Front"
   Area = 200
   Construction = "Exterior Wall Cons"
   ..

ResWin   "Zone1WinFront"
   WinType = "Standard Window"
   Area = 20
   ..
```

### Element Hierarchy

```
Root Level
├── Proj (required)
├── ResProj (required for residential)
├── ProjVar (project variables)
├── ResMat[] (materials)
├── ConsAssm[] (constructions)
├── FenCons[] (fenestration constructions)
├── ResWinType[] (window types)
├── SchDay[] (schedules)
├── DwellUnitType[] (dwelling unit types)
├── ResHtPumpSys[] (heat pumps)
├── ResFanSys[] (fans)
├── ResDistSys[] (distribution systems)
├── ResIAQFan[] (IAQ fans)
├── ResWtrHtr[] (water heaters)
├── ResDHWSys[] (DHW systems)
├── Bldg (building definition)
├── ResZnGrp[] (zone groups - floors)
│   └── (zones follow sequentially at root level)
├── ResZn[] (zones - at root level after their group)
│   └── (surfaces follow at root level)
├── ResExtWall[] (surfaces - at root level)
│   └── (openings follow at root level)
├── ResWin[] (openings - at root level)
└── DwellUnit[] (dwelling unit instances)
```

### Property Format

| Type | Format | Example |
|------|--------|---------|
| String | `key = "value"` | `Name = "Zone1"` |
| Number | `key = value` | `Area = 1000` |
| Boolean | `key = 0` or `key = 1` | `IsDefault = 1` |
| Array | `key[index] = value` | `HVACRef[1] = "HP1"` |
| Terminator | `..` | `..` |

---

## Zone Hierarchy Handling

### The Challenge

In CIBD text format, zone groups and zones appear at the same indentation level:

```
ResZnGrp   "Floor 1"
   TreeState = 254
   ..

ResZn   "Zone1"
   FloorArea = 1000
   ..

ResZn   "Zone2"
   FloorArea = 1200
   ..

ResZnGrp   "Floor 2"
   ..

ResZn   "Zone3"
   ...
```

### The Solution: Sequential Reorganization

The parser infers parent-child relationships based on **sequential ordering**:

1. Track current zone group as parser encounters `ResZnGrp`
2. When encountering a zone (`ResZn`, `ResOtherZn`, `ResAttic`), associate it with the current zone group
3. Move zone inside zone group in the XML tree

```python
def _reorganize_zones(self, root: ET.Element):
    """Move zones from root level to parent zone groups."""
    current_zone_group = None

    for elem in list(root):
        if elem.tag == 'ResZnGrp':
            current_zone_group = elem
            continue

        if elem.tag in ZONE_TYPES and current_zone_group is not None:
            root.remove(elem)
            current_zone_group.append(elem)
```

### Surface and Opening Reorganization

Similar logic applies to surfaces and openings:

- **Surfaces**: Matched to zones by name pattern (e.g., `Zone1WallFront` → `Zone1`)
- **Openings**: Matched to surfaces by orientation and zone (e.g., `Zone1WinFront` → `Zone1WallFront`)

---

## Cross-Format Translation

### CIBD25 → CIBD22

```python
# Import CIBD25
emjson = translate_to_emjson('input.cibd25')

# Export to CIBD22
translate_from_emjson(emjson, 'output.cibd22', version=CIBDVersion.CIBD22)
```

**Automatic transformations:**
- Ruleset changed to `T24_2022.bin`
- Software version updated
- Run title changed

### CIBD22 → CIBD25

```python
# Import CIBD22
emjson = translate_to_emjson('input.cibd22')

# Export to CIBD25
translate_from_emjson(emjson, 'output.cibd25', version=CIBDVersion.CIBD25)
```

### CIBD22X (XML) → CIBD25

```python
from eco_tools.translators.cibd22x.importer import CIBD22XImporter
from eco_tools.translators.cibd25.direct_writer import CIBD25DirectWriter

# Import XML
importer = CIBD22XImporter()
internal = importer.import_file('input.cibd22x')

# Convert to EMJSON
emjson = internal.to_emjson()

# Export to CIBD25
writer = CIBD25DirectWriter(emjson)
writer.write('output.cibd25')
```

---

## Element Type Mappings

### Preserved Types (Round-Trip)

These types are preserved exactly for round-trip fidelity:

| Original | Mapped To |
|----------|-----------|
| `ResZn` | `ResZn` |
| `ResOtherZn` | `ResOtherZn` |
| `ResAttic` | `ResAttic` |
| `ResExtWall` | `ResExtWall` |
| `ResIntWall` | `ResIntWall` |
| `ResWin` | `ResWin` |
| `ResDr` | `ResDr` |
| `ResWinType` | `ResWinType` |

### Zone Types

```python
ZONE_TYPES = {
    'ThrmlZn',      # Commercial thermal zone
    'ResZn',        # Residential dwelling zone
    'ResOtherZn',   # Residential common area
    'ResAttic',     # Attic zone
    'Spc',          # Commercial space
    'ComZn',        # Commercial zone
}
```

### Surface Types

```python
SURFACE_TYPES = {
    # Residential
    'ResExtWall', 'ResIntWall', 'ResSlabFlr', 'ResCathedralCeiling',
    'ResAtticRoof', 'ResOtherFlr', 'ResIntFlr', 'ResUndgrWall',
    'ResUndgrFlr', 'ResCeilingBelowAttic', 'ResRoof', 'ResCeiling',
    # Commercial
    'ExtWall', 'IntWall', 'Roof', 'FlrOnGrade', 'Ceiling',
    'FlrAbvAttic', 'UndgrWall', 'UndgrFlr', 'ExtFlr', 'IntFlr',
}
```

---

## Diagnostics

The translation process generates diagnostics for tracking issues:

```python
emjson = translate_to_emjson('input.cibd25')

for diagnostic in emjson.get('diagnostics', []):
    print(f"[{diagnostic['level']}] {diagnostic['code']}: {diagnostic['message']}")
```

### Diagnostic Levels

| Level | Description |
|-------|-------------|
| `error` | Fatal error preventing translation |
| `warning` | Non-fatal issue that may affect results |
| `info` | Informational message |

### Common Diagnostic Codes

| Code | Description |
|------|-------------|
| `E-IMPORT-FAILED` | Import failed with exception |
| `W-MISSING-ZONE-GROUP` | Zone without parent zone group |
| `W-ORPHAN-SURFACE` | Surface without parent zone |
| `I-VERSION-DETECTED` | Auto-detected file version |

---

## Testing

### Unit Tests

```bash
# Run unified translator tests
python3 -m pytest tests/test_cibd_text_unified.py -v

# Run all CIBD-related tests
python3 -m pytest tests/test_cibd*.py -v
```

### Integration Tests

```bash
# Run CIBD22 round-trip test suite
python3 tests/test_cibd22_round_trip.py -o /tmp/test_output
```

### CBECC Validation

```bash
# Validate exported file with CBECC 2025
"/Applications/CBECC 2025.app/Contents/MacOS/CBECC 2025" -nrcc -b output.cibd25
```

---

## Best Practices

### 1. Always Use Auto-Detection

```python
# Good: Let the translator detect version
emjson = translate_to_emjson('file.cibd25')

# Avoid: Hardcoding version unless necessary
emjson = translate_to_emjson('file.cibd25', version=CIBDVersion.CIBD25)
```

### 2. Check Diagnostics

```python
emjson = translate_to_emjson('input.cibd25')

errors = [d for d in emjson.get('diagnostics', []) if d['level'] == 'error']
if errors:
    for e in errors:
        print(f"Error: {e['message']}")
    raise ValueError("Import failed with errors")
```

### 3. Validate Before Submission

Always validate exports with CBECC before submitting for compliance:

```python
import subprocess

result = subprocess.run([
    '/Applications/CBECC 2025.app/Contents/MacOS/CBECC 2025',
    '-nrcc', '-b', 'output.cibd25'
], capture_output=True, text=True, timeout=30)

if 'Error' in result.stdout:
    print("Validation failed!")
```

### 4. Preserve Original Annotations

When modifying EMJSON, preserve annotations for round-trip fidelity:

```python
# Good: Preserve annotation
zone['floor_area_m2'] = new_area
zone['annotation']['original_floor_area_ft'] = str(new_area * 10.7639)

# Bad: Lose original value
zone['floor_area_m2'] = new_area  # original_floor_area_ft now stale
```

---

## Troubleshooting

### CBECC Hangs on Residential Model

**Cause**: Missing `ResProj` element

**Solution**: Ensure `proj_metadata.ResProj` is present in EMJSON:
```python
emjson['proj_metadata']['ResProj'] = {
    'n': 'Residential Project',
    'StdDesignFuel_HVAC': 'Electricity',
}
```

### Zones Not Re-imported

**Cause**: Zone groups missing `zone_refs`

**Solution**: Ensure zones have `parent_zone_group_id` in annotations

### Surfaces Not Associated with Zones

**Cause**: Surface names don't contain zone names

**Solution**: Use naming convention `{ZoneName}{SurfaceType}{Orientation}`

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2025-12-03 | Initial unified translator implementation |

---

## Related Documentation

- [CIBD_CONVERSION_FIXES.md](../eco_tools/translators/CIBD_CONVERSION_FIXES.md) - Fix history
- [EMJSON v6 Schema](./EMJSON_Schema.md) - Full EMJSON specification
- [CBECC 2025 User Guide](https://www.energy.ca.gov/programs-and-topics/programs/building-energy-efficiency-standards) - Official CBECC documentation
