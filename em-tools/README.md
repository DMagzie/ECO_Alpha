# FILE 2: em-tools/README.md
# ============================================================================
"""
# EM-Tools

Energy Modeling Translation Hub - EMJSON v6 universal format

## Features

- ✅ CIBD22X → EMJSON v6 translator with stable IDs
- ✅ EMJSON v6 → CIBD22X exporter
- ✅ Modular parser architecture
- ✅ Comprehensive unit conversions (IP ↔ SI)
- ✅ Diagnostic logging system
- ✅ Round-trip validation

## Installation

```bash
# From em-tools directory
pip install -e .

# With GUI support
pip install -e ".[gui]"
```

## Quick Start

### Python API

```python
from emtools.translators import translate_cibd22x_to_v6
from emtools.exporters import write_xml

# Import CIBD22X file
emjson = translate_cibd22x_to_v6("input.xml")

# Access data
zones = emjson['geometry']['zones']
print(f"Imported {len(zones)} zones")

# Export back to XML
write_xml(emjson, "output.xml")
```

### Command Line

```bash
# Translate XML to EMJSON
emtools-translate input.xml output.emjson

# Round-trip test
emtools-roundtrip model.emjson
```

### Streamlit GUI

```bash
# From project root
streamlit run explorer_gui/main.py
```

## Structure

- `emtools/translators/` - Import from various formats
- `emtools/exporters/` - Export to various formats  
- `emtools/parsers/` - Modular XML parsing
- `emtools/utils/` - ID registry, diagnostics

## Documentation

See `docs/` for detailed API documentation and examples.
"""
