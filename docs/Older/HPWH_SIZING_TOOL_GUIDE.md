# Central HPWH Tank Sizing Tool
## User Guide and Documentation

**Version:** 1.0
**Date:** November 20, 2025
**Purpose:** Automated central heat pump water heater tank sizing for Title 24 2025 compliance

---

## Overview

The Central HPWH Tank Sizing Tool automates the sizing of central heat pump water heater systems for multifamily buildings, combining:

1. **CBECC 2025 Formula** - Code-compliant minimum sizing per Title 24 Part 6
2. **Load Shifting Optimization** - Thermal storage sizing for NEM3/LSC compliance benefits
3. **CIBD25 Integration** - Direct export to CBECC compliance model format
4. **Performance Validation** - Recovery rates, first hour rating, peak capacity

### Key Features

✓ **Code-Compliant Sizing** - Implements CBECC 2025 formula: `max(50, (DUs × 10) + (Bedrooms × 3))`
✓ **Load Shifting Optimization** - 25-50% tank oversizing for thermal energy storage
✓ **Compressor Array Sizing** - Optimal number and capacity of HPWH compressors
✓ **Multi-Tank Configuration** - Automatic splitting for large systems
✓ **CIBD25 Export** - Direct export to compliance model format
✓ **CLI and Python API** - Use from command line or integrate into workflows

---

## Installation

### Prerequisites
- Python 3.11 or later
- ECO Tools v0.7 or later

### Setup
```bash
cd /Users/DavidM/Documents/ECO_Alpha_v7
# Tool is already installed in eco_tools/sizing/

# Test installation
python3 test_hpwh_sizer.py
```

---

## Quick Start

### Command Line Usage

#### Basic Sizing (Code Minimum)
```bash
python3 eco_tools/sizing/hpwh_sizing_tool.py \
    --units 30 \
    --bedrooms 60 \
    --climate-zone 12
```

#### With Load Shifting Optimization
```bash
python3 eco_tools/sizing/hpwh_sizing_tool.py \
    --units 30 \
    --bedrooms 60 \
    --climate-zone 12 \
    --load-shift \
    --oversize 1.25
```

#### Aggressive Optimization (50% Oversize)
```bash
python3 eco_tools/sizing/hpwh_sizing_tool.py \
    --units 50 \
    --avg-br 2.0 \
    --optimize  # Shortcut for load-shift + 50% oversize
```

#### Export to JSON
```bash
python3 eco_tools/sizing/hpwh_sizing_tool.py \
    --units 30 \
    --bedrooms 60 \
    --load-shift \
    --json sizing_results.json \
    --cibd25-export cibd25_properties.json
```

### Python API Usage

```python
from eco_tools.sizing import (
    CentralHPWHSizer,
    BuildingProfile,
    HPWHSystemConfig,
    size_from_dwelling_units,
    create_sizing_report,
)

# Quick sizing
results = size_from_dwelling_units(
    num_units=30,
    avg_bedrooms_per_unit=2.0,
    climate_zone="12",
    enable_load_shifting=True,
    oversizing_factor=1.25
)

print(create_sizing_report(results))

# Access specific results
print(f"Final Tank Volume: {results.final_tank_volume_gal} gallons")
print(f"Number of Compressors: {results.num_compressors}")
print(f"Evening Peak Coverage: {results.evening_peak_hours_covered:.1f} hours")

# Export to CIBD25
cibd25_dict = CentralHPWHSizer.export_to_cibd25_dict(results)
```

---

## Sizing Methodology

### 1. Code-Minimum Calculation

Per CBECC 2025 `Rules_Default_ResDHW.rule`:

```
TankVolume (gallons) = max(50, (NumDwellingUnits × 10) + (NumBedrooms × 3))
```

**Example:**
- 30 dwelling units
- 60 total bedrooms
- Minimum = max(50, (30 × 10) + (60 × 3)) = max(50, 480) = **480 gallons**

### 2. Load Shifting Optimization

For NEM3/LSC compliance, larger tanks enable:
- **Midday heating** during low-cost solar hours
- **Evening service** from thermal storage
- **Reduced peak demand** by avoiding evening HPWH operation

**Optimization Formula:**
```
Optimized Volume = max(
    Minimum × Oversizing Factor,
    Evening Peak Load × Coverage Hours × 1.15
)
```

**Typical Oversizing:**
- Conservative: 1.25× (25% oversize)
- Moderate: 1.35× (35% oversize)
- Aggressive: 1.5× (50% oversize)

### 3. Thermal Storage Capacity

```
Storage (BTU) = Volume (gal) × 8.34 (lb/gal) × ΔT (°F)
```

**Example: 750 gallon tank, 60°F temperature swing**
```
750 × 8.34 × 60 = 375,300 BTU thermal storage
```

This can cover 6-7 hours of evening DHW demand without HPWH operation!

### 4. Compressor Array Sizing

**Strategy:**
- Size for 4-6 hour midday charging window
- Prefer multiple smaller compressors for modulation
- Avoid oversizing (causes cycling inefficiency)

**Calculation:**
```
Required Capacity = Thermal Storage / Charge Window Hours
Number of Compressors = ceil(Required Capacity / Base Compressor Size)
```

**Compressor Types:**
- Small NEEA: 4.5 kW (residential-duty)
- Commercial Moderate: 10 kW
- Commercial Large: 20 kW
- Integrated Packaged: 15 kW

---

## CLI Reference

### Required Arguments

One of:
- `--units NUM` - Number of dwelling units
- `--cibd25 FILE` - Extract from CIBD25 file (not yet fully implemented)

### Building Parameters

| Argument | Type | Default | Description |
|----------|------|---------|-------------|
| `--bedrooms NUM` | int | - | Total bedrooms (required with --units) |
| `--avg-br NUM` | float | 2.0 | Average bedrooms per unit |
| `--common-du-equiv NUM` | float | 0.0 | Common area as DU equivalent |
| `--climate-zone CZ` | 1-16 | 12 | California climate zone |

### Optimization Options

| Argument | Type | Default | Description |
|----------|------|---------|-------------|
| `--load-shift` | flag | false | Enable load shifting optimization |
| `--oversize NUM` | float | 1.25 | Tank oversizing factor |
| `--no-oversize` | flag | false | Use code minimum only |
| `--charge-start HR` | 0-23 | 11 | Hour to start heating (noon) |
| `--charge-end HR` | 0-23 | 17 | Hour to stop heating (5pm) |
| `--optimize` | flag | false | Shortcut: load-shift + 1.5× oversize |

### System Configuration

| Argument | Type | Default | Description |
|----------|------|---------|-------------|
| `--compressor-type TYPE` | enum | small_neea | HPWH compressor type |
| `--tank-setpoint TEMP` | float | 140.0 | Tank setpoint °F |
| `--tank-r-value R` | float | 16.0 | Tank insulation R-value |
| `--compressor-cop COP` | float | 3.0 | Heat pump COP |

**Compressor Types:**
- `small_neea` - NEEA-rated residential HPWH (4.5 kW)
- `commercial_moderate` - Moderate commercial (10 kW)
- `commercial_large` - Large commercial (20 kW)
- `integrated_packaged` - Integrated packaged system (15 kW)

### Output Options

| Argument | Type | Description |
|----------|------|-------------|
| `--json FILE` | path | Export full results to JSON |
| `--cibd25-export FILE` | path | Export CIBD25 properties to JSON |
| `--quiet` | flag | Suppress detailed report |

---

## Example Scenarios

### Scenario 1: Small Building (10 Units)

**Building:**
- 10 dwelling units
- 2 bedrooms per unit average
- Climate Zone 12

**Command:**
```bash
python3 eco_tools/sizing/hpwh_sizing_tool.py \
    --units 10 \
    --avg-br 2.0 \
    --climate-zone 12 \
    --load-shift
```

**Result:**
- Minimum: 160 gallons
- Optimized: 200 gallons
- Final: 200 gallons
- Compressors: 1 × 4.5 kW
- Evening Coverage: 5.3 hours

### Scenario 2: Medium Building (30 Units)

**Building:**
- 30 dwelling units
- 60 total bedrooms
- Climate Zone 12
- Aggressive load shifting desired

**Command:**
```bash
python3 eco_tools/sizing/hpwh_sizing_tool.py \
    --units 30 \
    --bedrooms 60 \
    --climate-zone 12 \
    --optimize
```

**Result:**
- Minimum: 480 gallons
- Optimized: 720 gallons
- Final: 750 gallons (rounded to standard size)
- Compressors: 2 × 4.5 kW
- Evening Coverage: 6.6 hours
- Load Shifting Benefit: 56%

### Scenario 3: Large Building (100 Units)

**Building:**
- 100 dwelling units
- 150 total bedrooms (mix of studios, 1BR, 2BR)
- 5 DU equivalent for common areas
- Climate Zone 12

**Command:**
```bash
python3 eco_tools/sizing/hpwh_sizing_tool.py \
    --units 100 \
    --bedrooms 150 \
    --common-du-equiv 5.0 \
    --climate-zone 12 \
    --load-shift \
    --oversize 1.3 \
    --compressor-type commercial_large
```

**Result:**
- Minimum: 1,500 gallons
- Optimized: 1,950 gallons
- Final: 2,000 gallons
- Configuration: 2 tanks × 1,000 gallons
- Compressors: 1 × 20 kW
- Evening Coverage: 7.1 hours

---

## CIBD25 Integration

### Export Properties

The tool exports the following CIBD25 `ResDHWSys` properties:

| Property | Description | Type |
|----------|-------------|------|
| `CHPWHTotTankVol` | Total primary tank volume | Float (gallons) |
| `CHPWHTankCount` | Number of storage tanks | Integer |
| `CHPWHNumComp` | Number of compressors | Integer |
| `CHPWHCompCap` | Compressor capacity | Float (kW) |
| `CHPWHTankSetpt` | Tank setpoint temperature | Float (°F) |
| `CHPWHTankRVal` | Tank insulation R-value | Float |
| `CHPWHTankMinRVal` | Minimum tank R-value (2025 code) | Float |
| `CHPWHAutosize` | Autosizing flag (0 = user-specified) | Integer |

### Export to JSON

```bash
python3 eco_tools/sizing/hpwh_sizing_tool.py \
    --units 30 \
    --bedrooms 60 \
    --load-shift \
    --cibd25-export cibd25_dhw.json
```

**Output (`cibd25_dhw.json`):**
```json
{
  "Name": "Central HPWH System",
  "SystemType": "Central",
  "CentralDHW": 1,
  "CentralDHWType": "CommercialPackagedBoiler",
  "CHPWHTotTankVol": 750.0,
  "CHPWHTankCount": 1,
  "CHPWHNumComp": 2,
  "CHPWHCompCap": 4.5,
  "CHPWHTankSetpt": 140.0,
  "CHPWHTankRVal": 16.0,
  "CHPWHTankMinRVal": 12.5,
  "CHPWHAutosize": 0
}
```

### Importing to CIBD25 Model

```python
import json
from eco_tools.translators.cibd25.direct_writer import CIBD25Writer

# Load sizing results
with open('cibd25_dhw.json') as f:
    dhw_properties = json.load(f)

# Apply to CIBD25 model
# (Integration with CIBD25 writer - implement as needed)
```

---

## Understanding Results

### Sizing Report Sections

#### 1. Tank Sizing
- **Minimum Required**: Code formula result
- **Recommended**: After load shifting optimization
- **Final Specified**: Rounded to standard size
- **Number of Tanks**: 1 or multiple for large systems
- **Volume per Tank**: Individual tank capacity

#### 2. Compressor Sizing
- **Number of Compressors**: For capacity and redundancy
- **Capacity per Compressor**: Heating capacity (kW or BTU/h)
- **Total Heating Capacity**: Sum of all compressors

#### 3. Performance Metrics
- **Recovery Rate**: Gallons per hour @ 90°F rise
- **First Hour Rating**: Tank + 1 hour recovery
- **Peak Hour Capacity**: Tank + 4 hours recovery

#### 4. Load Shifting Capability
- **Thermal Storage**: BTUs stored in tank
- **Evening Peak Coverage**: Hours without HPWH operation
- **Benefit from Oversizing**: % improvement from code minimum

### Key Performance Indicators

**Good Performance:**
- Evening Peak Coverage: **≥ 4 hours**
- Load Shifting Benefit: **≥ 25%**
- Recovery Rate: **> 50 gal/hour for most MF buildings**

**Optimal Performance:**
- Evening Peak Coverage: **≥ 6 hours**
- Load Shifting Benefit: **≥ 50%**
- Compressors: **Multiple for redundancy and modulation**

---

## Best Practices

### 1. Choosing Oversizing Factor

| Building Type | Recommended Factor | Reason |
|---------------|-------------------|--------|
| Small (< 20 DUs) | 1.2-1.3× | Modest benefit, lower cost |
| Medium (20-50 DUs) | 1.25-1.35× | Balanced optimization |
| Large (> 50 DUs) | 1.3-1.5× | Maximum LSC benefit |
| High-Performance | 1.5× | Maximum load shifting |

### 2. Compressor Selection

- **Small buildings** (< 20 DUs): 1-2 × Small NEEA (4.5 kW)
- **Medium buildings** (20-50 DUs): 2-3 × Small NEEA or 1-2 × Commercial Moderate
- **Large buildings** (> 50 DUs): Multiple Commercial Large (20 kW) with redundancy

### 3. Charge Window Configuration

**Default (Recommended):**
- Start: 11:00 (noon)
- End: 17:00 (5pm)
- Rationale: Peak solar generation, low LSC hours

**Alternatives:**
- Extended: 10:00-18:00 (for slower compressors)
- Flexible: Based on utility TOU rates

### 4. Tank Setpoint

- **Standard:** 140°F (default)
- **High Storage:** 145°F (more thermal capacity)
- **Efficiency:** 135°F (higher COP, less capacity)
- **Legionella Prevention:** ≥ 140°F recommended

---

## Troubleshooting

### Issue: Tank size seems too large

**Cause:** Aggressive oversizing factor

**Solution:**
- Reduce `--oversize` factor (try 1.2 instead of 1.5)
- Disable load shifting with `--no-oversize`
- Balance cost vs. compliance benefit

### Issue: Too many compressors specified

**Cause:** Large tank, short charge window

**Solution:**
- Extend charge window (`--charge-end 18`)
- Use larger compressor type (`--compressor-type commercial_large`)
- Reduce tank size if possible

### Issue: Multiple tanks required

**Cause:** Total volume exceeds 1,000 gallon maximum per tank

**Solution:**
- This is normal for large buildings
- Consider separate systems per building wing
- Verify available mechanical room space

### Issue: Low evening peak coverage

**Cause:** Insufficient oversizing for load profile

**Solution:**
- Increase `--oversize` factor
- Enable `--load-shift` if not already
- Consider higher tank setpoint for more storage

---

## Validation and Compliance

### Code Compliance Verification

The tool ensures:
✓ Minimum tank volume meets CBECC 2025 formula
✓ Tank R-value ≥ 12.5 (2025 minimum)
✓ Compressor capacity sufficient for recovery
✓ Standard tank sizes used (manufactured availability)

### Performance Validation

Run the test suite to verify calculations:
```bash
python3 test_hpwh_sizer.py
```

Expected output:
- ✓ Code minimum formula verified
- ✓ Load shifting optimization verified
- ✓ Thermal storage calculations verified
- ✓ CIBD25 export properties verified

---

## Advanced Usage

### Batch Processing

```bash
# Size multiple buildings
for units in 10 20 30 50 100; do
    python3 eco_tools/sizing/hpwh_sizing_tool.py \
        --units $units \
        --avg-br 2.0 \
        --load-shift \
        --json "results_${units}units.json" \
        --quiet
done
```

### Sensitivity Analysis

```python
from eco_tools.sizing import size_from_dwelling_units

# Test various oversizing factors
for factor in [1.0, 1.25, 1.5, 1.75]:
    results = size_from_dwelling_units(
        num_units=30,
        enable_load_shifting=True,
        oversizing_factor=factor
    )
    print(f"Factor {factor}: {results.final_tank_volume_gal} gal, "
          f"{results.evening_peak_hours_covered:.1f} hours coverage")
```

### Custom Building Profiles

```python
from eco_tools.sizing import CentralHPWHSizer, BuildingProfile, HPWHSystemConfig

# Complex building with custom parameters
building = BuildingProfile(
    num_dwelling_units=50,
    total_bedrooms=85,  # Mixed unit sizes
    common_area_du_equiv=8.0,  # Large amenity spaces
    climate_zone="6",
    peak_hour_draw_factor=0.75,  # Higher simultaneous use
    daily_dhw_gal_per_bedroom=15.0,  # Above-average usage
)

config = HPWHSystemConfig(
    enable_load_shifting=True,
    oversizing_factor=1.4,
    tank_setpoint_f=145.0,  # Higher for more storage
    tank_r_value=18.0,  # Better insulation
    compressor_cop=3.2,  # High-efficiency units
)

results = CentralHPWHSizer.size_central_hpwh(building, config)
```

---

## References

### Technical Standards
- **Title 24 Part 6, Section 110.3** - DHW system requirements
- **Title 24 Part 6, Section 140.10** - PV and battery (related load shifting)
- **ASHRAE 90.2** - Residential water heating

### CBECC 2025 Ruleset Files
- `Rules_Default_ResDHW.rule` - Tank sizing logic (lines 737-787)
- `BEMBase_Res DHW.txt` - Central HPWH properties (lines 150-200)
- `Rules_CSE_Simulation_ResDHW.rule` - Simulation parameters

### Related Documentation
- `CBECC_2025_NEM3_ANALYSIS.md` - NEM3 background
- `CBECC_2025_LOAD_SHIFTING_OPTIMIZATION.md` - Load shifting strategies

---

## Support and Contributing

### Getting Help
- Check test suite: `python3 test_hpwh_sizer.py`
- Review examples in this guide
- Inspect `central_hpwh_sizer.py` source code

### Reporting Issues
File issues or feature requests in the ECO Tools repository.

### Contributing
Contributions welcome! Areas for enhancement:
- Full CIBD25 file parsing (currently placeholder)
- Climate-zone-specific load profiles
- Integration with utility rate structures
- Autosizing iteration algorithm (like CBECC HPWHSIZE)
- GUI/web interface

---

**Document Version:** 1.0
**Last Updated:** November 20, 2025
**Maintainer:** ECO Tools Development Team
