# ECO Alpha v7

**Energy Compliance and Optimization Tools - Alpha Release**

A building energy modeling platform with proven CIBD22X/CIBD25 round-trip translation, 3D geometry builder, and Streamlit GUI. Supports California Title 24 energy compliance workflows.

---

## What's Working Now

### Production-Ready Components

| Component | Status | Description |
|-----------|--------|-------------|
| **CIBD22X Round-Trip** | Working | Import/export CBECC-Com XML files with 0 errors |
| **CIBD Text Round-Trip** | Working | Import/export CIBD22/CIBD25 text formats |
| **Cross-Format Translation** | Working | Convert between CIBD22 and CIBD25 |
| **EMJSON v6 Schema** | Complete | Universal internal representation |
| **3D Geometry Builder** | Working | Interactive Plotly-based visualization |
| **Streamlit GUI** | Functional | Web-based model editor |
| **Zone-Level LCCA** | Working | TOU/VNBT costs per zone with 8760 hourly data (electric + gas) |
| **LCCA CLI** | Working | `zone-analyze` command with `--gas-rate` for dual-fuel analysis |

### Proven Performance

**CIBD22X Test Case: Bressi Ranch Apartments** (Large multi-family residential)
- 290 zones round-trip with 100% fidelity
- 3,472 surfaces round-trip with 100% fidelity
- 1,308 openings round-trip with 100% fidelity
- 0 CBECC-Com errors when loading exported file

**CIBD Text Test Case: Round-Trip Fidelity**
- 3 zones, 11 surfaces, 3 zone groups preserved through round-trip
- Cross-format: CIBD25 to CIBD22 with correct ruleset translation

---

## Quick Start

### 1. Clone and Install

```bash
git clone https://github.com/yourusername/ECO_Alpha_v7.git
cd ECO_Alpha_v7

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Or install as package
pip install -e .
```

### 2. Launch GUI

```bash
cd gui
streamlit run main.py
```

Opens at: `http://localhost:8501`

### 3. Python API Usage

#### CIBD22X (XML Format)

```python
from eco_tools.translators.cibd22x.importer import CIBD22XImporter
from eco_tools.translators.cibd22x.exporter import CIBD22XExporter

# Import CBECC file
importer = CIBD22XImporter()
model = importer.import_file('input.cibd22x')

# Edit model (EMJSON v6 format)
# ... make changes ...

# Export back to CBECC
exporter = CIBD22XExporter()
exporter.export_to_file(model, 'output.cibd22x')
```

#### CIBD Text Format (CIBD22/CIBD25)

```python
from eco_tools.translators.cibd_text import (
    translate_to_emjson,
    translate_from_emjson,
    CIBDVersion,
)

# Import CIBD25 text file to EMJSON
emjson = translate_to_emjson('input.cibd25')

# Edit model...

# Export to CIBD25 (same format)
translate_from_emjson(emjson, 'output.cibd25', version=CIBDVersion.CIBD25)

# Or convert to CIBD22
translate_from_emjson(emjson, 'output.cibd22', version=CIBDVersion.CIBD22)
```

---

## Repository Structure

```
ECO_Alpha_v7/
├── eco_tools/                  # Core translation engine
│   ├── core/                   # Internal representation (EMJSON v6)
│   │   ├── internal_repr.py    # Data model
│   │   └── id_registry.py      # ID tracking for round-trip
│   │
│   ├── translators/            # Format translators
│   │   ├── cibd22x/           # CBECC-Com XML format
│   │   │   ├── importer.py     # CIBD22X -> EMJSON
│   │   │   ├── exporter.py     # EMJSON -> CIBD22X
│   │   │   ├── parsers/        # 26 specialized parsers
│   │   │   └── exporters/      # 22 specialized exporters
│   │   │
│   │   └── cibd_text/         # CIBD text format (CIBD22/CIBD25)
│   │       ├── __init__.py     # Public API
│   │       ├── parser.py       # Text parser
│   │       ├── direct_writer.py # Text exporter
│   │       ├── to_emjson.py    # CIBD -> EMJSON conversion
│   │       ├── from_emjson.py  # EMJSON -> CIBD conversion
│   │       └── version_config.py # Version-specific settings
│   │
│   └── geometry/               # 3D Geometry Builder
│       ├── builder.py          # GeometryBuilder class
│       ├── models.py           # Geometry data models
│       ├── operations.py       # Geometric operations
│       └── validator.py        # Geometry validation
│
├── gui/                        # Streamlit web interface
│   ├── main.py                # Entry point
│   ├── config.py              # App configuration
│   └── pages/                 # GUI pages
│
├── tests/                      # Test suite
│   ├── test_cibd_text_unified.py  # CIBD text translator tests
│   └── fixtures/              # Test data files
│
├── docs/                       # Documentation
│   ├── CIBD_EMJSON_Architecture.md  # Architecture overview
│   ├── EMJSON_V6_SCHEMA.md    # Schema specification
│   └── API_REFERENCE.md       # API documentation
│
└── examples/                   # Example projects
```

---

## Architecture Overview

### Data Flow

```
┌─────────────────┐     ┌─────────────────┐
│  CIBD22X (XML)  │     │  CIBD25 (Text)  │
│  CBECC-Com      │     │  CBECC 2025     │
└────────┬────────┘     └────────┬────────┘
         │                       │
         ▼                       ▼
┌─────────────────┐     ┌─────────────────┐
│ CIBD22XImporter │     │ cibd_text.parser│
│  (26 parsers)   │     │                 │
└────────┬────────┘     └────────┬────────┘
         │                       │
         └───────────┬───────────┘
                     ▼
           ┌─────────────────┐
           │   EMJSON v6     │
           │ (Internal Model)│
           └────────┬────────┘
                    │
         ┌──────────┴──────────┐
         ▼                     ▼
┌─────────────────┐   ┌─────────────────┐
│ CIBD22XExporter │   │ direct_writer   │
│  (22 exporters) │   │                 │
└────────┬────────┘   └────────┬────────┘
         │                     │
         ▼                     ▼
┌─────────────────┐   ┌─────────────────┐
│  CIBD22X (XML)  │   │ CIBD22/25 (Text)│
└─────────────────┘   └─────────────────┘
```

### Key Design Patterns

1. **Orchestrator Pattern** - Main importer/exporter coordinate specialized modules
2. **Modular Parsers** - Each element type has dedicated parser
3. **Shared ID Registry** - Ensures consistent IDs across round-trip
4. **Annotation Preservation** - CBECC-specific properties stored in annotations
5. **Version Configuration** - Separate configs for CIBD22 vs CIBD25

---

## Supported Formats

| Format | Extension | Import | Export | Notes |
|--------|-----------|--------|--------|-------|
| CIBD22X | .cibd22x | Yes | Yes | CBECC-Com 2022 XML |
| CIBD22 | .cibd22 | Yes | Yes | CBECC 2022 text format |
| CIBD25 | .cibd25 | Yes | Yes | CBECC 2025 text format |
| EMJSON | .emjson | Yes | Yes | Internal JSON format |

---

## Testing

### Run All Tests

```bash
pytest tests/ -v
```

### Run CIBD Text Tests

```bash
pytest tests/test_cibd_text_unified.py -v
```

Expected output: 17 tests passing

### Validate with CBECC

```bash
# CBECC 2022
"/Applications/CBECC 2022.app/Contents/MacOS/CBECC 2022" -nrp -b "output.cibd22x"

# CBECC 2025
"/Applications/CBECC 2025.app/Contents/MacOS/CBECC 2025" -nrcc -b "output.cibd25"
```

---

## Documentation

### Key Documents

- `docs/CIBD_EMJSON_Architecture.md` - Complete architecture guide
- `docs/EMJSON_V6_SCHEMA.md` - Internal representation specification
- `docs/API_REFERENCE.md` - Python API documentation

---

## Known Limitations

1. **HVAC Systems** - Full HVAC hierarchy export not yet implemented for CIBD22X
2. **Control Systems** - OACtrl elements require HVAC hierarchy
3. **DHW Systems** - Domestic hot water not yet exported
4. **Geometry** - Simplified geometry only (no detailed polygon coordinates)

### Workarounds

- For HVAC: Use CBECC's built-in HVAC design wizard after import
- For DHW: Add domestic hot water systems in CBECC
- For detailed geometry: Use CBECC's native geometry editor

---

## Contributing

### Development Setup

```bash
# Install development dependencies
pip install -r requirements.txt
pip install -e ".[dev]"

# Run tests
pytest tests/ -v

# Type checking
mypy eco_tools/
```

### Code Style

- Python 3.9+
- Type hints required for public functions
- Docstrings for all public classes and methods

---

## License

MIT License - See LICENSE file

---

## Acknowledgments

- **CBECC-Com/CBECC** - California Energy Commission compliance software
- **Ladybug Tools** - Open-source building performance analysis
- **Streamlit** - Web GUI framework

---

## Project Status

**Current Version**: v7.0.0
**Status**: Production Ready
**Stability**: Production-ready for CIBD22X, CIBD text round-trip, and Zone-Level LCCA

---

**Last Updated**: January 2026
