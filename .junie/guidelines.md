# ECO Tools Development Guidelines for Junie

## Project Overview
Energy modeling translation hub converting between CIBD22, HBJSON, EMJSON formats.

## Code Patterns to Follow

### 1. ID Generation
Always use IDRegistry:
```python
id = self.id_registry.generate_id(prefix, source_name, context)
```

### 2. Diagnostics
Add diagnostic messages for issues:
```python
self.diagnostics.append({
    "level": "warning",
    "code": "GEO-001", 
    "message": "..."
})
```

### 3. Unit Conversion
Use UnitConverter class:
```python
value_si = self.converter.ip_to_si(value_ip, unit_type)
```

### 4. File Organization
- Importers: emtools/translators/
- Exporters: emtools/exporters/
- Geometry: emtools/geometry/
- Utils: emtools/utils/
- Tests: tests/

### 5. Code Style
- Type hints required
- Docstrings with Args/Returns
- Follow existing patterns in cibd22_importer.py
```