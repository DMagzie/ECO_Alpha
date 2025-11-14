# GEM Import Status

## Summary

GEM import functionality has been successfully implemented with support for **both** simplified GEM text format **and** IES VE native GEM format.

## Supported Format

### Simplified GEM Text Format ✅

The translator supports a simplified text-based GEM format with keywords like:
- `PROJECT "name"`
- `SPACE "name"`
- `SURFACE "name"`
- `WINDOW "name"`
- `COORDS` / `END-COORDS`

**Example:**
```
PROJECT "Simple Box Test"

SPACE "Room 1"
  FLOOR-PLAN-COORDS
    POINT 0.0 0.0 0.0
    POINT 10.0 0.0 0.0
    POINT 10.0 8.0 0.0
    POINT 0.0 8.0 0.0
  END-FLOOR-PLAN-COORDS

  SURFACE "South Wall"
    TYPE = ExteriorWall
    COORDS
      POINT 0.0 0.0 0.0
      POINT 10.0 0.0 0.0
      POINT 10.0 0.0 3.0
      POINT 0.0 0.0 3.0
    END-COORDS
  END-SURFACE
END-SPACE
```

**Test Results:**
- File: `simple_box.gem`
- ✅ 1 zone imported
- ✅ 6 surfaces (with calculated areas: 268 m² total)
- ✅ 1 window opening
- ✅ Automatic area calculation from 3D vertices

### IES VE Native GEM Format ✅

The native IES VE GEM format uses low-level geometry mesh format and is now fully supported:
- `COM GEM data file` headers
- Raw vertex coordinate arrays
- Face definitions with 1-based indices
- Automatic surface type detection (floor/roof/wall)
- `LAYER`, `COLOUR`, `CATEGORY` properties

**Example file**: `1000 Gibraltar.gem` (55.6KB)

**Test Results**:
- ✅ 35 zones imported
- ✅ 247 surfaces (32 floors, 35 roofs, 180 walls)
- ✅ 283 windows with calculated areas
- ✅ 114,195 m² total surface area
- ✅ Automatic area calculation from vertices
- ✅ 2D to 3D coordinate transformation working

## Recommended Alternative: gbXML

**IES VE can export to gbXML format**, which is a standard building information XML format.

### Finding gbXML Export in IES VE:
1. Open your model in IES VE
2. File > Export > gbXML
3. Use the exported XML file instead of GEM

### gbXML Format Details:
- Standard: http://www.gbxml.org/schema
- Contains: Spaces, surfaces, constructions, HVAC systems
- Used by: IES VE, Revit, DesignBuilder, OpenStudio, etc.

**Example gbXML files found:**
- `/Users/DavidM/Documents/ECO_Alpha/Test Projects/Gib/Gibralter/1000 Gibraltar.xml`
- Contains complete building geometry with:
  - Multiple spaces (Aerosol, Flammable, Area B restroom, etc.)
  - Surface boundaries with coordinates
  - Area and volume data
  - Building storey information

## Implementation Status

### Current Capabilities ✅
1. **GEM Parser** (`eco_tools/translators/gem/importer.py`)
   - Parses simplified GEM text format
   - Returns dictionary with spaces, surfaces, windows

2. **GEM to EMJSON v6 Translator** (`eco_tools/translators/gem/__init__.py`)
   - Converts GEM dictionary to EMJSON v6
   - Automatic 3D polygon area calculation
   - Proper ID generation and name sanitization
   - Comprehensive error handling

3. **Area Calculation** (`_calculate_polygon_area()`)
   - Cross product method for 3D polygons
   - Works for planar and non-planar surfaces
   - Calculates from vertex coordinates

### Supported Features ✅
1. **IES VE native GEM format**
   - Vertex/face mesh parsing
   - Automatic surface type detection from normals
   - 2D to 3D coordinate transformation for openings
   - Space ID and name extraction

2. **Simplified GEM text format**
   - Keyword-based parsing (PROJECT/SPACE/SURFACE)
   - Direct vertex coordinate parsing
   - Window and door support

### Limitations ⚠️
1. **No gbXML importer yet**
   - gbXML is a standard format with richer building data
   - Would complement GEM support well
   - Contains HVAC, schedules, and more

2. **Construction/material data not yet parsed from GEM**
   - Currently focuses on geometry
   - Could be extended to parse construction assemblies

## Next Steps

### For Users:
1. **GEM files now work with ECO Tools!**
   - Both simplified and native IES VE formats supported
   - Automatic geometry reconstruction
   - Surface areas calculated automatically

2. For projects with many windows, gbXML may provide better results
   - IES VE: File > Export > gbXML

### For Developers:
1. **Implement gbXML importer** (HIGH PRIORITY)
   - Standard format with richer building data
   - Complements GEM support
   - Used by many tools (Revit, DesignBuilder, etc.)

3. Add format detection to import UI
4. Show format-specific guidance to users

## Testing

### Test Files:
- **Simplified format**: `/Users/DavidM/Documents/ECO_Alpha_v7/examples/simple_box.gem` ✅
- **Native IES format**: `/Users/DavidM/Documents/ECO_Alpha/Test Projects/Gib/Gibralter/1000 Gibraltar.gem` ✅
- **gbXML alternative**: `/Users/DavidM/Documents/ECO_Alpha/Test Projects/Gib/Gibralter/1000 Gibraltar.xml` (not yet supported)

### Test Script:
```bash
python3 test_gem_import.py
```

## Technical Architecture

```
GEM File (Simplified Format)
    ↓
GEMParser.parse()
    ↓
Dictionary {spaces: [...], surfaces: [...]}
    ↓
_gem_dict_to_emjson_v6()
    ↓
EMJSON v6 {geometry: {zones, surfaces, openings}}
```

### Key Functions:
- `translate_gem_to_v6(gem_file)` - Main translator entry point
- `_gem_dict_to_emjson_v6(gem_data, project_name)` - Converts dictionary to EMJSON v6
- `_calculate_polygon_area(vertices)` - Calculates 3D polygon areas

### Error Handling:
- Detects IES native format and provides helpful message
- Suggests alternative export options
- Returns proper diagnostic codes (E-GEM-PARSE)

## Files Modified

1. **`eco_tools/translators/gem/__init__.py`** (245 lines)
   - Complete rewrite
   - Added area calculation
   - Simplified error handling (native format now supported)

2. **`eco_tools/translators/gem/importer.py`** (657 lines)
   - Added `_is_native_ies_format()` - format detection
   - Added `_parse_native_ies_spaces()` - native IES parser (lines 349-532)
   - Added `_determine_surface_type_from_vertices()` - surface classification
   - Added `_transform_2d_to_3d()` - opening coordinate transformation
   - Automatic format detection and routing

3. **`test_gem_import.py`** (updated)
   - Tests both formats
   - Comprehensive statistics
   - Updated test file paths
