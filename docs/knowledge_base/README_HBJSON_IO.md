# EM Core Tools – HBJSON I/O Module (v0.05)

## Overview
`hbjson_io.py` enables translation between Honeybee JSON (HBJSON) and EM Tools' normalized JSON format (`normalized_model.json`). Supports import from geometry modelers like Rhino/Grasshopper via Pollination.

## Modes
- **Import**: HBJSON → EM JSON
- **Export**: EM JSON → HBJSON

## Usage

```bash
# Import from HBJSON
python hbjson_io.py import input_model.hbjson normalized_model.json

# Export to HBJSON
python hbjson_io.py export normalized_model.json output_model.hbjson
```

## Mapping Logic
| HBJSON Field                    | EM JSON Field             |
|--------------------------------|---------------------------|
| `rooms[*].identifier`          | `zones[*].name`           |
| `rooms[*].is_conditioned`      | `zones[*].conditioned`    |
| `rooms[*].properties.energy.*` | `zones[*].hvac_type` etc. |
| `properties.energy.*`          | `building.*`              |

## Integration
- Geometry workflows using Pollination/Rhino
- Future GUI import/export buttons
- Baseline + scenario I/O sync

## Limitations
- No geometry validation or zone boundary handling
- Assumes standard Honeybee schema structure
- No surface-level data or detailed constructions (yet)