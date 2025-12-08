# ECO_Alpha v7 - Testing Checklist

**Version**: 7.0.0
**Date**: November 11, 2025
**Status**: Ready for Testing

---

## Pre-Testing Setup

### 1. Launch the GUI

```bash
cd /Users/DavidM/Documents/ECO_Alpha_v7
streamlit run gui/main.py
```

**Expected Result**: Browser opens to `http://localhost:8501` with ECO_Alpha GUI

### 2. Verify Dependencies

All required packages should already be installed. If you encounter import errors:

```bash
pip install streamlit plotly honeybee-energy
```

### 3. Prepare Test Files

**Recommended test files**:
- **CIBD22X**: `/Users/DavidM/Documents/ECO_Alpha/reference_data/cbecc/CBECC Models/Bressi Ranch/Bressi Ranch Apartments.cibd22x`
- **Weather File**: Any `.epw` file for California (e.g., Sacramento, San Diego)

---

## Testing Workflow

### Phase 1: Import Testing (5 min)

#### Test 1.1: CIBD22X Import

**Steps**:
1. Navigate to **Import** page
2. Select "CIBD22X" format
3. Browse to Bressi Ranch `.cibd22x` file
4. Click **Import**

**Expected Results**:
- ✅ Success message displayed
- ✅ Import log shows parsed elements
- ✅ No critical errors in log

**Navigate to Active Model page to verify**:
- ✅ Model name displayed
- ✅ Spaces/zones listed
- ✅ Building area shown

---

### Phase 2: Wizard Testing (10 min)

#### Test 2.1: Quick Setup

**Steps**:
1. Navigate to **🧙 Build Model** page
2. Fill in project information:
   - Project Name: "Test Building"
   - Building Type: "Office"
   - Climate Zone: "CZ12 - Sacramento"
3. Click **Quick Setup**
4. Review generated systems

**Expected Results**:
- ✅ HVAC systems auto-generated
- ✅ Construction assemblies assigned
- ✅ Schedules created
- ✅ Success message displayed

#### Test 2.2: Manual System Creation (Optional)

**Steps**:
1. Expand "Manual Setup" section
2. Add HVAC system manually
3. Assign zones
4. Save system

**Expected Results**:
- ✅ System added to model
- ✅ Zones assigned correctly
- ✅ System appears in Active Model

---

### Phase 3: CBECC Simulation (15 min)

#### Test 3.1: Export to CIBD22X

**Steps**:
1. Navigate to **⚡ Simulate** page
2. Go to **CBECC-Com** tab
3. Enter output filename: `test_model.cibd22x`
4. Click **Export Model to CIBD22X**

**Expected Results**:
- ✅ Export success message
- ✅ File created in `test_output/` directory
- ✅ Export log shows no critical errors

#### Test 3.2: Run CBECC Simulation

**Prerequisites**:
- CBECC-Com installed
- Wine installed (macOS)

**Steps**:
1. In CBECC-Com tab, click **Run CBECC-Com Simulation**
2. Wait for simulation to complete (1-3 minutes)
3. Check simulation log

**Expected Results**:
- ✅ Simulation completes successfully
- ✅ AnalysisResults.xml file created
- ✅ No fatal errors in log

#### Test 3.3: View Parsed Results

**Steps**:
1. After simulation completes, check for **📊 Parsed Results** section
2. Review compliance status
3. Check TDV metrics
4. Review end use breakdown

**Expected Results**:
- ✅ Compliance status displayed (Pass/Fail/Unknown)
- ✅ TDV values shown if available
- ✅ End uses listed with values
- ✅ No parsing errors

---

### Phase 4: EnergyPlus Simulation (15 min)

#### Test 4.1: Export to HBJSON

**Steps**:
1. Go to **EnergyPlus** tab
2. Enter filename: `test_model.hbjson`
3. Click **Export Model to HBJSON**

**Expected Results**:
- ✅ Export success message
- ✅ HBJSON file created
- ✅ No critical errors

#### Test 4.2: Run EnergyPlus Simulation

**Prerequisites**:
- EnergyPlus installed
- Honeybee-Energy package installed
- Weather file (.epw) available

**Steps**:
1. Browse and select weather file (e.g., `USA_CA_Sacramento.epw`)
2. Click **Run EnergyPlus Simulation**
3. Wait for simulation (1-5 minutes)
4. Check simulation log

**Expected Results**:
- ✅ Simulation completes successfully
- ✅ EUI calculated and displayed
- ✅ Total energy shown
- ✅ End use breakdown displayed
- ✅ Warnings/errors listed if any

---

### Phase 5: Results Comparison (10 min)

#### Test 5.1: View Comparison

**Prerequisites**: Both CBECC and EnergyPlus simulations completed

**Steps**:
1. Navigate to **Compare Results** tab
2. Review side-by-side comparison
3. Check comparison table

**Expected Results**:
- ✅ Both result sets displayed
- ✅ Comparison table shows deltas
- ✅ Percentage differences calculated
- ✅ Agreement assessment provided

---

### Phase 6: Visualization (5 min)

#### Test 6.1: View Charts

**Steps**:
1. In Compare Results tab, scroll to **📊 Visual Analysis**
2. Review all 4 chart tabs:
   - **End Use Comparison**
   - **Delta Analysis**
   - **Compliance Gauge**
   - **Energy Breakdown**

**Expected Results**:
- ✅ All charts display correctly
- ✅ Charts are interactive (hover, zoom, pan)
- ✅ Data matches comparison table
- ✅ Colors consistent (CBECC=blue, EnergyPlus=green)

#### Test 6.2: Chart Interactions

**Steps**:
1. Hover over chart elements
2. Try zooming in/out
3. Pan around charts
4. Reset view

**Expected Results**:
- ✅ Hover shows detailed tooltips
- ✅ Zoom works smoothly
- ✅ Pan navigates chart
- ✅ Reset returns to original view

---

### Phase 7: Data Export (5 min)

#### Test 7.1: Export CBECC Results

**Steps**:
1. Scroll to **📥 Export Results** section
2. Click **Export CBECC to CSV**
3. Click **Download CSV** button

**Expected Results**:
- ✅ Success message displayed
- ✅ CSV file generated in `test_output/`
- ✅ Download initiated
- ✅ CSV opens correctly in Excel/Google Sheets

#### Test 7.2: Export Comparison

**Steps**:
1. Click **Export Comparison to CSV**
2. Download and open CSV

**Expected Results**:
- ✅ CSV contains both result sets
- ✅ Delta calculations present
- ✅ Percentage differences shown
- ✅ All end uses included
- ✅ Metadata (timestamp, software version) present

#### Test 7.3: Verify CSV Structure

**Open exported CSV and verify**:
- ✅ Clear section headers
- ✅ Readable formatting
- ✅ Numeric values properly formatted
- ✅ No encoding issues
- ✅ Can be imported into Excel

---

## Edge Case Testing (Optional)

### Test 8.1: Empty Model

**Steps**:
1. Start with blank model (no spaces)
2. Try to run wizard
3. Check error handling

**Expected Results**:
- ✅ Appropriate error messages
- ✅ No crashes
- ✅ Clear guidance on what's missing

### Test 8.2: Incomplete Simulation

**Steps**:
1. Run CBECC simulation on incomplete model
2. Check how parser handles failed simulation

**Expected Results**:
- ✅ "Unknown" status displayed
- ✅ Informative message about missing results
- ✅ No crashes

### Test 8.3: Missing Weather File

**Steps**:
1. Try to run EnergyPlus without weather file
2. Check error handling

**Expected Results**:
- ✅ Clear error message
- ✅ Guidance on required file
- ✅ No crash

---

## Performance Testing

### Test 9.1: Large Model Performance

**Steps**:
1. Import large model (200+ zones)
2. Monitor GUI responsiveness
3. Time simulations

**Expected Benchmarks**:
- ⏱️ GUI remains responsive (<2s page loads)
- ⏱️ CBECC simulation: 2-5 minutes
- ⏱️ EnergyPlus simulation: 3-10 minutes
- ⏱️ Chart rendering: <1 second

### Test 9.2: Multiple Simulations

**Steps**:
1. Run CBECC simulation
2. Modify model
3. Run again
4. Compare results

**Expected Results**:
- ✅ Previous results preserved
- ✅ New results displayed correctly
- ✅ No memory leaks
- ✅ Session state maintained

---

## Known Issues & Workarounds

### Issue 1: CBECC Not Found (macOS)

**Symptom**: "CBECC-Com executable not found"

**Workaround**:
```bash
# Install Wine if not present
brew install --cask wine-stable

# Run CBECC installer
wine ~/Downloads/CBECCcom_2022_Setup.exe
```

### Issue 2: EnergyPlus Import Error

**Symptom**: "No module named 'honeybee_energy'"

**Workaround**:
```bash
pip install honeybee-energy ladybug-comfort
```

### Issue 3: Charts Not Displaying

**Symptom**: Charts section shows error or empty

**Workaround**:
```bash
pip install --upgrade plotly streamlit
```

### Issue 4: Weather File Not Found

**Symptom**: EnergyPlus simulation fails with "Weather file not found"

**Workaround**:
- Download EPW files from: https://energyplus.net/weather
- Place in accessible directory
- Use full absolute path in file browser

---

## Test Results Documentation

### Test Session Template

```
Date: __________
Tester: __________
Version: 7.0.0

Phase 1: Import                 [ ] Pass  [ ] Fail  Notes: ____________
Phase 2: Wizard                 [ ] Pass  [ ] Fail  Notes: ____________
Phase 3: CBECC Simulation       [ ] Pass  [ ] Fail  Notes: ____________
Phase 4: EnergyPlus Simulation  [ ] Pass  [ ] Fail  Notes: ____________
Phase 5: Comparison             [ ] Pass  [ ] Fail  Notes: ____________
Phase 6: Visualization          [ ] Pass  [ ] Fail  Notes: ____________
Phase 7: Export                 [ ] Pass  [ ] Fail  Notes: ____________

Overall Status: [ ] Pass  [ ] Fail

Issues Found:
1. ________________________________________________________________
2. ________________________________________________________________
3. ________________________________________________________________

Suggestions:
1. ________________________________________________________________
2. ________________________________________________________________
```

---

## Success Criteria

**Minimum Acceptable**:
- ✅ Can import CIBD22X file
- ✅ Wizard completes model successfully
- ✅ CBECC simulation runs (or clear error if CBECC not installed)
- ✅ EnergyPlus simulation runs
- ✅ Results display correctly
- ✅ At least one export format works

**Fully Functional**:
- ✅ All import formats work
- ✅ Both simulations complete successfully
- ✅ All charts display and are interactive
- ✅ All export formats work
- ✅ No crashes during normal workflow
- ✅ Performance acceptable for typical models

---

## Reporting Issues

If you encounter issues during testing:

1. **Note the exact steps** that led to the issue
2. **Capture error messages** (copy text or screenshot)
3. **Check the console** for Python errors
4. **Document the context**:
   - What file were you using?
   - What had you done previously in the session?
   - Can you reproduce it?

**Where to Report**:
- Create notes in `docs/TESTING_NOTES.md`
- Or communicate directly for immediate fixes

---

## Post-Testing

After completing testing:

1. **Review all test sections** - Note pass/fail for each
2. **Document any issues** - Clear descriptions with steps to reproduce
3. **Provide feedback** on:
   - User experience
   - Workflow clarity
   - Documentation accuracy
   - Performance
   - Missing features

---

## Quick Reference

**Launch GUI**:
```bash
cd /Users/DavidM/Documents/ECO_Alpha_v7
streamlit run gui/main.py
```

**Run Tests**:
```bash
python3 -m pytest tests/unit/ -v
```

**Test File Locations**:
- CIBD22X: `/Users/DavidM/Documents/ECO_Alpha/reference_data/cbecc/CBECC Models/`
- Test Output: `/Users/DavidM/Documents/ECO_Alpha_v7/test_output/`

**Documentation**:
- User Guide: `docs/USER_GUIDE.md`
- API Reference: `docs/API_REFERENCE.md`
- Phase Summaries: `docs/PHASE_*.md`

---

**Happy Testing! 🎉**

If you encounter any issues or have questions, the documentation should provide guidance. The platform is designed to handle errors gracefully with clear messages.

**Remember**: The platform is production-ready, but testing will help identify any edge cases or platform-specific issues before wider deployment.
