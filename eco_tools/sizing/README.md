# Central HPWH Tank Sizing Tool

**Version:** 1.0
**Status:** Production Ready ✅

## Quick Links
- 📖 [Full User Guide](../../docs/HPWH_SIZING_TOOL_GUIDE.md)
- 📊 [Load Shifting Analysis](../../docs/CBECC_2025_LOAD_SHIFTING_OPTIMIZATION.md)
- 🔬 [NEM3 Technical Analysis](../../docs/CBECC_2025_NEM3_ANALYSIS.md)

## Overview

Automated central heat pump water heater tank sizing tool that combines CBECC 2025 compliance formulas with load shifting optimization for Title 24 compliance.

### What It Does

✅ **Code-Compliant Sizing** - Implements CBECC 2025 formula
✅ **Load Shifting Optimization** - 25-50% tank oversizing for thermal storage
✅ **Compressor Array Sizing** - Optimal HPWH compressor count and capacity
✅ **CIBD25 Export** - Direct integration with compliance models
✅ **CLI & GUI** - Use from command line or Streamlit interface
✅ **Production Tested** - Comprehensive test suite included

## Installation

```bash
cd /Users/DavidM/Documents/ECO_Alpha_v7

# Already installed - no additional setup needed!
# Sizing module located at: eco_tools/sizing/
```

## Quick Start

### Command Line

```bash
# Basic sizing
PYTHONPATH=/Users/DavidM/Documents/ECO_Alpha_v7 \
python3 eco_tools/sizing/hpwh_sizing_tool.py \
    --units 30 --bedrooms 60 --climate-zone 12

# With load shifting
PYTHONPATH=/Users/DavidM/Documents/ECO_Alpha_v7 \
python3 eco_tools/sizing/hpwh_sizing_tool.py \
    --units 30 --bedrooms 60 --load-shift

# Aggressive optimization
PYTHONPATH=/Users/DavidM/Documents/ECO_Alpha_v7 \
python3 eco_tools/sizing/hpwh_sizing_tool.py \
    --units 50 --avg-br 2.0 --optimize
```

### GUI (Streamlit)

```bash
# Run ECO Tools GUI
cd /Users/DavidM/Documents/ECO_Alpha_v7
streamlit run gui/main.py

# Navigate to: Utilities Page → Central HPWH Tank Sizing
```

### Python API

```python
from eco_tools.sizing import size_from_dwelling_units, create_sizing_report

# Quick sizing
results = size_from_dwelling_units(
    num_units=30,
    avg_bedrooms_per_unit=2.0,
    climate_zone="12",
    enable_load_shifting=True,
    oversizing_factor=1.25
)

print(create_sizing_report(results))
print(f"Tank: {results.final_tank_volume_gal} gallons")
print(f"Compressors: {results.num_compressors}")
```

## Testing

```bash
cd /Users/DavidM/Documents/ECO_Alpha_v7
python3 test_hpwh_sizer.py
```

**Expected Output:**
```
✓ Code minimum formula verified
✓ Load shifting optimization verified
✓ Thermal storage calculations verified
✓ CIBD25 export properties verified
ALL TESTS COMPLETED
```

## Key Features

### 1. CBECC 2025 Formula Implementation

**Code Formula:**
```
TankVolume = max(50, (NumDUs × 10) + (NumBedrooms × 3))
```

**Example:**
30 units, 60 bedrooms → 480 gallons minimum

### 2. Load Shifting Optimization

**Strategy:**
- Heat water during low-cost midday hours (11am-5pm)
- Serve evening loads from thermal storage
- Reduce peak electrical demand during high LSC hours

**Typical Oversizing:**
- Conservative: 1.25× (25%)
- Moderate: 1.35× (35%)
- Aggressive: 1.5× (50%)

### 3. Thermal Storage Calculations

**Formula:**
```
Storage (BTU) = Volume × 8.34 lb/gal × ΔT (°F)
```

**Example:**
750 gallons × 60°F rise = 375,300 BTU storage
= 6-7 hours evening coverage without HPWH operation!

### 4. Compressor Array Sizing

**Approach:**
- Size for 4-6 hour midday charge window
- Prefer multiple smaller compressors (better modulation)
- Match capacity to tank and load profile

**Compressor Types:**
- Small NEEA: 4.5 kW (residential-duty)
- Commercial Moderate: 10 kW
- Commercial Large: 20 kW
- Integrated Packaged: 15 kW

### 5. CIBD25 Integration

**Exported Properties:**
- `CHPWHTotTankVol` - Total tank volume
- `CHPWHTankCount` - Number of tanks
- `CHPWHNumComp` - Number of compressors
- `CHPWHCompCap` - Compressor capacity (kW)
- `CHPWHTankSetpt` - Setpoint temperature
- `CHPWHTankRVal` - Tank R-value
- Ready for direct import to CIBD25 model

## File Structure

```
eco_tools/sizing/
├── __init__.py                  # Module exports
├── central_hpwh_sizer.py        # Core sizing engine
├── hpwh_sizing_tool.py          # CLI interface
└── README.md                    # This file

gui/
├── components/
│   └── hpwh_sizer_widget.py     # Streamlit widget
└── pages/
    └── utilities_page.py        # GUI utilities page

docs/
├── HPWH_SIZING_TOOL_GUIDE.md    # Complete user guide
├── CBECC_2025_LOAD_SHIFTING_OPTIMIZATION.md
└── CBECC_2025_NEM3_ANALYSIS.md

test_hpwh_sizer.py               # Test suite (root level)
```

## Example Results

### Small Building (10 Units)
```
Minimum:     160 gallons
Optimized:   200 gallons
Compressors: 1 × 4.5 kW
Coverage:    5.3 hours
```

### Medium Building (30 Units, Load Shifting)
```
Minimum:     480 gallons
Optimized:   750 gallons  (+56%)
Compressors: 2 × 4.5 kW
Coverage:    6.6 hours
Thermal Storage: 375,300 BTU
```

### Large Building (100 Units, Aggressive)
```
Minimum:     1,450 gallons
Optimized:   2,000 gallons  (+38%)
Tanks:       2 × 1,000 gallons
Compressors: 1 × 20 kW
Coverage:    7.1 hours
Thermal Storage: 1,000,800 BTU
```

## Use Cases

### 1. Preliminary Design
Use sizing tool **before** creating CBECC model when equipment sizes are unknown.

### 2. Code Compliance Check
Verify that proposed tank size meets Title 24 2025 minimum requirements.

### 3. Load Shifting Analysis
Optimize tank size for maximum NEM3/LSC compliance benefit.

### 4. Cost-Benefit Studies
Compare different oversizing strategies (capital cost vs. compliance benefit).

### 5. CIBD25 Model Setup
Export sizing results directly to compliance model for accurate simulation.

## Technical References

### California Title 24 Standards
- **Section 110.3** - DHW system requirements
- **Section 140.10** - Related load shifting measures
- **Table 140.10-B** - Prescriptive requirements

### CBECC 2025 Ruleset Files
- `Rules_Default_ResDHW.rule` (lines 737-787)
- `BEMBase_Res DHW.txt` (lines 150-200)
- `Rules_CSE_Simulation_ResDHW.rule`

### Related Standards
- ASHRAE 90.2 - Residential water heating
- NEEA HPWH Specifications
- California Plumbing Code

## Troubleshooting

### Issue: Module not found error
**Solution:** Set PYTHONPATH before running:
```bash
export PYTHONPATH=/Users/DavidM/Documents/ECO_Alpha_v7
# Or use inline:
PYTHONPATH=/Users/DavidM/Documents/ECO_Alpha_v7 python3 ...
```

### Issue: Tank size seems too large
**Solution:** Reduce oversizing factor or disable load shifting:
```bash
--oversize 1.2  # Instead of 1.5
# Or
--no-oversize   # Code minimum only
```

### Issue: GUI not showing utilities page
**Solution:** Ensure utilities_page.py is in gui/pages/ and restart Streamlit.

## Future Enhancements

Potential areas for expansion:
- [ ] Full CIBD25 file parsing (currently placeholder)
- [ ] Climate-zone-specific load profiles
- [ ] Integration with utility rate structures
- [ ] Autosizing iteration (like CBECC HPWHSIZE)
- [ ] Cost estimation database
- [ ] Multi-building campus sizing
- [ ] Secondary loop optimization
- [ ] Legionella prevention analysis

## Contributing

Contributions welcome! The tool is modular and extensible.

**Key Extension Points:**
- `BuildingProfile` - Add custom load factors
- `HPWHSystemConfig` - Add new optimization strategies
- `CentralHPWHSizer` - Extend sizing algorithms
- GUI widgets - Add visualization features

## Support

- 📖 Full documentation: `docs/HPWH_SIZING_TOOL_GUIDE.md`
- 🧪 Run tests: `python3 test_hpwh_sizer.py`
- 💬 Issues: File in ECO Tools repository

## Version History

**v1.0** (November 20, 2025)
- ✅ Initial release
- ✅ CBECC 2025 formula implementation
- ✅ Load shifting optimization
- ✅ Compressor array sizing
- ✅ CIBD25 export
- ✅ CLI and GUI interfaces
- ✅ Comprehensive test suite
- ✅ Full documentation

---

**Maintainer:** ECO Tools Development Team
**License:** (Same as ECO Tools)
**Status:** Production Ready ✅
