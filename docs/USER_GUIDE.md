# ECO_Alpha v7 - User Guide

**Version**: 7.0.0
**Date**: November 11, 2025
**Status**: Production Ready

---

## Table of Contents

1. [Getting Started](#getting-started)
2. [Quick Start Tutorial](#quick-start-tutorial)
3. [Import Workflows](#import-workflows)
4. [Using the Wizard](#using-the-wizard)
5. [Running Simulations](#running-simulations)
6. [Comparing Results](#comparing-results)
7. [Exporting Data](#exporting-data)
8. [Tips & Best Practices](#tips--best-practices)
9. [Troubleshooting](#troubleshooting)

---

## Getting Started

### Prerequisites

**Required**:
- Python 3.11+
- Streamlit
- Basic building energy modeling knowledge

**Optional** (for full functionality):
- CBECC-Com (Title 24 compliance)
- EnergyPlus (detailed energy analysis)
- Wine (macOS, for CBECC)

### Installation

```bash
# Clone repository
git clone <repository-url>
cd ECO_Alpha_v7

# Install dependencies
pip install -r requirements.txt

# Launch GUI
streamlit run gui/main.py
```

---

## Quick Start Tutorial

### Complete Workflow (15 minutes)

**Goal**: Import a model, complete it with the wizard, run simulations, and compare results.

#### Step 1: Import a Model (2 min)

1. Navigate to **Import** page
2. Click **Browse** and select a `.gem`, `.hbjson`, or `.cibd22x` file
3. Click **Import**
4. Review imported model in **Active Model** page

#### Step 2: Complete Model with Wizard (5 min)

1. Navigate to **🧙 Build Model** page
2. Fill in project information:
   - Project Name
   - Building Type (e.g., "Office")
   - Climate Zone (e.g., "CZ12 - Sacramento")
3. Click **Quick Setup** to auto-generate:
   - HVAC systems
   - Construction assemblies
   - Schedules
4. Review created systems
5. Model is now complete!

#### Step 3: Run CBECC Simulation (3 min)

1. Navigate to **⚡ Simulate** page
2. Go to **CBECC-Com** tab
3. Enter output filename (e.g., `my_model.cibd22x`)
4. Click **Export Model to CIBD22X**
5. Click **Run CBECC-Com Simulation**
6. Wait for completion (1-2 minutes)
7. View parsed results:
   - Compliance status
   - TDV metrics
   - End use breakdown

#### Step 4: Run EnergyPlus Simulation (3 min)

1. Go to **EnergyPlus** tab
2. Enter filename (e.g., `my_model.hbjson`)
3. Click **Export Model to HBJSON**
4. Select weather file for your climate zone
5. Click **Run EnergyPlus Simulation**
6. Wait for completion (1-3 minutes)
7. View detailed results:
   - EUI
   - Total energy
   - End use breakdown

#### Step 5: Compare Results (2 min)

1. Go to **Compare Results** tab
2. View side-by-side comparison:
   - CBECC compliance vs EnergyPlus energy
   - End use comparison table
   - Delta calculations
3. Go to **Visual Analysis** section
4. Explore interactive charts:
   - End use comparison bars
   - Delta analysis
   - Compliance gauge
   - Pie charts
5. Export data:
   - Click **Export Comparison to CSV**
   - Download CSV file

**✅ Complete!** You've now modeled, simulated, and analyzed a building.

---

## Import Workflows

### Supported Formats

| Format | Extension | Use Case |
|--------|-----------|----------|
| **CIBD22X** | `.cibd22x` | CBECC-Com Title 24 models |
| **HBJSON** | `.hbjson` | Honeybee/Ladybug models |
| **GEM** | `.gem` | Revit exports |
| **EMJSON** | `.json` | Internal format |

### Import Process

1. **Navigate to Import Page**
2. **Select File Type** (auto-detected)
3. **Browse and Select File**
4. **Click Import**
5. **Review Import Log**
6. **Check Active Model**

### Post-Import Checklist

After importing, verify:
- [ ] Building geometry loaded
- [ ] Spaces/zones present
- [ ] Windows and doors imported
- [ ] No import errors in log

If incomplete, use the **Wizard** to add missing components.

---

## Using the Wizard

### When to Use the Wizard

Use the wizard to:
- Complete partially defined models
- Add HVAC systems to geometry-only models
- Assign construction assemblies
- Generate schedules
- Set up Title 24 compliance parameters

### Wizard Steps

#### 1. Project Information

Fill in:
- **Project Name**: Your project identifier
- **Building Type**: Office, Multifamily, Retail, etc.
- **Climate Zone**: California climate zone (CZ01-CZ16)
- **Weather Station**: Auto-filled based on climate zone

#### 2. Quick Setup (Recommended)

Click **Quick Setup** to auto-generate:
- **HVAC Systems**: Appropriate for building type and climate
- **Constructions**: Title 24 compliant assemblies
- **Schedules**: Typical operating schedules

**Or** use manual setup for custom configurations.

#### 3. Review Systems

Check created systems:
- Air systems (HVAC)
- Hot water systems
- Zones assignments

#### 4. Complete

Click **Complete Wizard** to apply changes to model.

---

## Running Simulations

### CBECC-Com (Title 24 Compliance)

**Purpose**: California Title 24 compliance analysis

**Steps**:
1. Export model to CIBD22X format
2. Run CBECC simulation
3. View compliance results:
   - Pass/Fail status
   - TDV (Time Dependent Valuation) metrics
   - Compliance margin (% better than standard)

**Typical Runtime**: 1-3 minutes

**Requirements**:
- CBECC-Com installed
- Wine (macOS only)
- Complete building model

### EnergyPlus (Detailed Energy)

**Purpose**: Detailed annual energy simulation

**Steps**:
1. Export model to HBJSON format
2. Select EPW weather file
3. Run EnergyPlus simulation
4. View detailed results:
   - EUI (Energy Use Intensity)
   - Total site energy
   - End use breakdown
   - Monthly profiles

**Typical Runtime**: 2-5 minutes

**Requirements**:
- EnergyPlus installed
- Honeybee-Energy package
- Weather file (EPW)

---

## Comparing Results

### Side-by-Side Comparison

View both simulation results simultaneously:

**CBECC-Com** (Left):
- Compliance status
- TDV metrics
- Building area

**EnergyPlus** (Right):
- EUI
- Total energy
- End use summary

### Comparison Table

Detailed end use comparison showing:
- **CBECC Value**: From Title 24 analysis
- **EnergyPlus Value**: From detailed simulation
- **Delta**: Difference (EnergyPlus - CBECC)
- **% Difference**: Percentage difference

**Interpretation**:
- **< 10% difference**: Good agreement
- **10-20% difference**: Fair agreement, investigate
- **> 20% difference**: Poor agreement, check inputs

### Visual Analysis

#### End Use Comparison Chart
Side-by-side bars comparing energy consumption by category.

#### Delta Analysis Chart
Shows differences with color coding:
- **Red**: EnergyPlus predicts higher (worse)
- **Green**: EnergyPlus predicts lower (better)

#### Compliance Gauge
Visual indicator of Title 24 compliance margin:
- **Red Zone**: Not compliant (< 0%)
- **Yellow Zone**: Marginal (0-10%)
- **Green Zone**: Good compliance (> 10%)

#### Energy Breakdown Pies
Pie charts showing proportion of each end use for both engines.

---

## Exporting Data

### CSV Export

Export simulation results to CSV for analysis in Excel/Google Sheets.

**Options**:
1. **Export CBECC to CSV**: Title 24 compliance results
2. **Export EnergyPlus to CSV**: Detailed energy results
3. **Export Comparison to CSV**: Side-by-side comparison with deltas

**CSV Includes**:
- Metadata (project name, date, software version)
- Summary metrics (EUI, TDV, building area)
- End use breakdown
- Compliance results

**Usage**:
```
Click export button → CSV generated → Download button appears → Click download
```

Files saved to: `test_output/<filename>.csv`

---

## Tips & Best Practices

### Modeling Tips

1. **Start Simple**: Import basic geometry, use wizard to complete
2. **Use Templates**: Leverage building type templates for quick setup
3. **Check Geometry**: Verify all spaces have proper adjacencies
4. **Validate Before Simulating**: Use diagnostics to catch errors early

### Simulation Tips

1. **Run Both Engines**: CBECC for compliance, EnergyPlus for detailed analysis
2. **Match Weather**: Use appropriate EPW file for climate zone
3. **Compare Results**: Look for agreement between engines
4. **Save Intermediates**: Keep exported CIBD22X/HBJSON files

### Performance Tips

1. **Large Models**: May take longer (5-10 minutes for 200+ zones)
2. **Simplify Geometry**: Combine similar zones where appropriate
3. **Background Processing**: Simulations run asynchronously

---

## Troubleshooting

### Import Issues

**Problem**: Import fails with error
**Solution**:
- Check file format is supported
- Verify file is not corrupted
- Review import log for specific errors

**Problem**: Missing geometry after import
**Solution**:
- Use diagnostics to identify issues
- Complete model with wizard
- Check original file in source software

### Simulation Issues

**Problem**: CBECC-Com not found
**Solution**:
```bash
# macOS
brew install --cask wine-stable
wine ~/Downloads/CBECCcom_2022_Setup.exe
```

**Problem**: EnergyPlus not found
**Solution**:
- Download from: https://energyplus.net/downloads
- Install EnergyPlus 23.1 or later
- Verify: `pip install honeybee-energy`

**Problem**: Simulation fails
**Solution**:
- Check export log for errors
- Verify model is complete
- Review simulation log file
- Ensure all systems are defined

### Comparison Issues

**Problem**: No comparison data available
**Solution**:
- Run both CBECC and EnergyPlus simulations
- Wait for both to complete successfully
- Check that results were parsed correctly

**Problem**: Large discrepancies (> 20%)
**Solution**:
- Verify weather files match climate zone
- Check HVAC system definitions
- Compare construction assemblies
- Review operating schedules

---

## Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Ctrl+R` | Refresh page |
| `Esc` | Close dialog |
| `Tab` | Navigate fields |

---

## Getting Help

**Documentation**:
- `docs/` - Technical documentation
- `docs/API_REFERENCE.md` - API documentation
- `docs/TROUBLESHOOTING.md` - Common issues

**Support**:
- GitHub Issues: Report bugs
- Email: Contact development team

---

## Appendix

### California Climate Zones

| Zone | Representative City | Characteristics |
|------|-------------------|----------------|
| CZ01 | Arcata | Cool coastal |
| CZ02 | Santa Rosa | Cool valley |
| CZ03 | Oakland | Moderate coastal |
| CZ04 | San Jose | Moderate valley |
| CZ06 | Los Angeles | Warm coastal |
| CZ07 | San Diego | Warm coastal |
| CZ12 | Sacramento | Hot valley |
| CZ13 | Fresno | Very hot valley |
| CZ16 | Mount Shasta | Cold mountain |

### Building Types

- **Office**: Commercial office buildings
- **Retail**: Retail stores and shopping centers
- **Multifamily**: Apartment buildings and condos
- **Mixed-Use**: Combined residential and commercial
- **Hotel**: Hotels and motels
- **School**: Educational facilities
- **Healthcare**: Medical facilities

### End Use Categories

- **Space Heating**: HVAC heating energy
- **Space Cooling**: HVAC cooling energy
- **Indoor Fans**: Ventilation fans
- **Indoor Lighting**: Interior lighting
- **Equipment**: Plug loads and appliances
- **DHW**: Domestic hot water
- **Pumps**: HVAC pumps
- **Heat Rejection**: Cooling towers

---

**End of User Guide**

For more detailed technical information, see:
- `API_REFERENCE.md` - Developer documentation
- `PHASE_*.md` - Implementation details
- Source code comments - Inline documentation

