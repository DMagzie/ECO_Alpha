# Phase 1 Testing Plan - ECO_Alpha v7.0.0

**Purpose**: Verify core functionality works end-to-end
**Duration**: 15-20 minutes
**Status**: Ready to execute

---

## Prerequisites

### Before You Start

**1. GUI is Running**:
```bash
cd /Users/DavidM/Documents/ECO_Alpha_v7
streamlit run gui/main.py
```
- Browser at http://localhost:8501
- "Running" status (green dot) in top-right corner

**2. Test File Ready**:
- Path: `reference_data/cbecc/CBECC Models/Bressi Ranch/Bressi Ranch Apartments.cibd22x`
- Size: ~1.4 MB
- Format: CIBD22X (2022)

**3. Have This Checklist Handy**:
- Text editor or note-taking app
- Browser console open (F12) for debugging if needed

---

## Test 1: Import Model (5 minutes)

### Objective
Verify file import works and model loads into internal format.

### Steps

**1.1 Navigate to Import Page**
- [ ] Click "Import" in left sidebar
- [ ] Page loads without errors
- [ ] See two tabs: "📁 Upload File" and "📋 Paste XML"

**1.2 Upload Test File**
- [ ] Stay on "📁 Upload File" tab
- [ ] Click "Browse files" button (should be active now, not greyed)
- [ ] Navigate to: `reference_data/cbecc/CBECC Models/Bressi Ranch/`
- [ ] Select: `Bressi Ranch Apartments.cibd22x`
- [ ] File appears in upload box

**1.3 Select Translator**
- [ ] See "Select Translator" section
- [ ] Two radio button options:
  - "em-tools (Modular Parser)" ← **Select this one**
  - "Universal Translator (Adapter-based)"
- [ ] Info message shows translator description

**1.4 Import the File**
- [ ] Click "Import CIBD22X XML" button (blue/primary button)
- [ ] Spinner appears: "Importing CIBD22X XML using cibd22x..."
- [ ] Wait for completion (5-15 seconds)

### Expected Results ✅

**Success Indicators**:
- Green success message: "✅ Import successful!"
- Import log shows:
  - "Import completed successfully"
  - Number of spaces/zones imported
  - Number of surfaces imported
  - No critical errors

**What You Should See**:
```
✅ Import successful!
Import Log:
  ℹ️ Parsed 24 spaces
  ℹ️ Parsed 156 surfaces
  ℹ️ Import completed successfully
```

**If You See Errors**:
- Red error message → Copy full error text and report
- Import log shows "❌ Error" → Check what failed
- No success message after 30 seconds → Check terminal

### Troubleshooting

**"File upload button greyed out"**:
- Refresh page (Cmd+Shift+R)
- Check terminal for errors

**"Import failed" error**:
- Check file path is correct
- Verify file is actually CIBD22X format
- Try the other translator (Universal Translator)

**Import hangs**:
- Wait up to 60 seconds (large file)
- Check terminal for progress messages
- Check browser console (F12) for errors

---

## Test 2: View Active Model (3 minutes)

### Objective
Verify imported model is accessible and displays correctly.

### Steps

**2.1 Navigate to Active Model**
- [ ] Click "Active Model" in left sidebar
- [ ] Page loads without errors

**2.2 Check Model Information**
- [ ] See model name: "Bressi Ranch Apartments" or similar
- [ ] See building information card with:
  - Total floor area
  - Number of spaces
  - Number of surfaces
  - Climate zone (should be CZ06)

**2.3 Browse Model Data**
- [ ] See sections for:
  - Spaces/Zones
  - Surfaces (Walls, Roofs, Floors)
  - Windows
  - Systems (may be empty if not generated yet)
- [ ] Expand a space/zone → See details
- [ ] Check that data looks reasonable (not empty or all zeros)

### Expected Results ✅

**Success Indicators**:
- Model data displays in organized sections
- Numbers make sense (e.g., floor area ~20,000-30,000 sq ft for Bressi Ranch)
- Can expand/collapse sections
- No "Model not loaded" or "No data" messages

**Key Metrics to Verify** (Bressi Ranch):
- Spaces: ~24 spaces
- Surfaces: ~150-200 surfaces
- Floor area: ~25,000 sq ft
- Climate Zone: CZ06 (San Diego)

### Troubleshooting

**"No model loaded"**:
- Go back to Import page
- Re-import the file
- Check import was successful

**Empty sections**:
- This might be normal for systems (generated later by wizard)
- Spaces and surfaces should NOT be empty

**Strange values** (e.g., floor area = 0):
- This might be a parser issue
- Note it for reporting
- Try importing again with other translator

---

## Test 3: Run Wizard (5 minutes)

### Objective
Verify wizard can complete model with HVAC systems and defaults.

### Steps

**3.1 Navigate to Build Model**
- [ ] Click "🧙 Build Model" in left sidebar
- [ ] Page loads without errors
- [ ] See wizard interface

**3.2 Fill Project Information**
- [ ] **Project Name**: "Bressi Ranch Test"
- [ ] **Building Type**: Select "Multifamily" or "Residential"
- [ ] **Climate Zone**: Select "CZ06 - San Diego" (should auto-detect)
- [ ] **Construction Type**: Leave default or select "Wood Frame"
- [ ] **Year**: Leave default or select "2022"

**3.3 Run Quick Setup**
- [ ] Find "Quick Setup" button (should be prominent)
- [ ] Click "Quick Setup" button
- [ ] Spinner appears: "Generating HVAC systems..."
- [ ] Wait for completion (5-10 seconds)

### Expected Results ✅

**Success Indicators**:
- Green success message: "✅ Model completed successfully!"
- Shows summary of what was generated:
  - Number of HVAC systems added
  - Number of zones assigned
  - Default constructions applied
  - Schedules created

**What You Should See**:
```
✅ Model completed successfully!
Generated:
  - 2 HVAC systems
  - 24 zones assigned to systems
  - Default Title 24 constructions applied
  - Standard schedules created
```

### Troubleshooting

**"Quick Setup button greyed out"**:
- Check that model is loaded (go to Active Model to verify)
- Try refreshing page
- Check terminal for errors

**Wizard fails with error**:
- Note the specific error message
- Check if project info is filled correctly
- Try using "Manual Setup" instead (if available)

**No systems generated**:
- This might indicate wizard logic issue
- Check Active Model to see if anything was added
- Note for reporting

---

## Test 4: View Updated Model (2 minutes)

### Objective
Verify wizard added systems and defaults to the model.

### Steps

**4.1 Return to Active Model**
- [ ] Click "Active Model" in left sidebar
- [ ] Page refreshes with updated data

**4.2 Check for New Data**
- [ ] **Systems section** should now have content:
  - HVAC systems listed (e.g., "HVAC-1", "HVAC-2")
  - System types shown (e.g., "Package Terminal AC", "Split System")
  - Zones assigned to each system
- [ ] **Construction section** (if visible):
  - Wall/roof/floor constructions assigned
- [ ] **Schedule section** (if visible):
  - Occupancy, lighting, equipment schedules

**4.3 Spot Check Data**
- [ ] Expand an HVAC system → See details (capacity, efficiency, etc.)
- [ ] Check that zones are properly assigned
- [ ] Look for any "null" or "undefined" values (shouldn't have)

### Expected Results ✅

**Success Indicators**:
- Systems section is populated (not empty)
- At least 1-2 HVAC systems visible
- All zones have system assignments
- Data looks complete and reasonable

**Red Flags**:
- Systems section still empty → Wizard may have failed silently
- All zones unassigned → System assignment logic failed
- Many "null" or missing values → Parser issue

---

## Test 5: Export Model (3 minutes)

### Objective
Verify model can be exported back to CIBD22X format.

### Steps

**5.1 Navigate to Export Page**
- [ ] Click "Export" in left sidebar
- [ ] Page loads without errors
- [ ] See export options

**5.2 Export to CIBD22X**
- [ ] Select export format: **CIBD22X** (if dropdown)
- [ ] Enter filename: `bressi_ranch_test_export.cibd22x`
- [ ] Choose export location: `test_output/` (or default)
- [ ] Click "Export" button

**5.3 Verify Export**
- [ ] Spinner appears: "Exporting to CIBD22X..."
- [ ] Wait for completion (5-10 seconds)
- [ ] Success message appears

**5.4 Check Output File**
- [ ] Navigate to `test_output/` directory
- [ ] Verify file exists: `bressi_ranch_test_export.cibd22x`
- [ ] Check file size (should be ~1-2 MB, similar to original)
- [ ] File has .cibd22x extension

### Expected Results ✅

**Success Indicators**:
- Green success message: "✅ Export successful!"
- File created in `test_output/` directory
- File size is reasonable (~1-2 MB)
- No error messages

**File Verification**:
```bash
# Check file exists and size
ls -lh test_output/bressi_ranch_test_export.cibd22x
```

Should show file with size around 1-2 MB.

### Troubleshooting

**Export fails with error**:
- Note the specific error message
- Check that model is complete (wizard ran)
- Try exporting to different format (JSON) to isolate issue

**File not created**:
- Check permissions on `test_output/` directory
- Try different output location
- Check terminal for error messages

**File is tiny** (< 100 KB):
- Export may have failed partially
- Open file to check if it's valid XML
- Compare with original file structure

---

## Test 6: Bonus - Try Another Import (Optional, 3 minutes)

### Objective
Verify import works with different files and formats.

### Steps

**6.1 Import Another CIBD22X File**
- [ ] Go to Import page
- [ ] Try a different model from `reference_data/cbecc/CBECC Models/`
- [ ] Suggestions:
  - Del Amo (if exists)
  - Freedom Circle (if exists)
  - Any 2025 Sample Model

**6.2 Import CIBD25 File** (if available)
- [ ] Navigate to: `reference_data/cbecc/CBECC Models/2025 Sample Models/`
- [ ] Select any `.cibd25` file
- [ ] Import using appropriate translator
- [ ] Verify import succeeds

**6.3 Quick Check**
- [ ] Each import succeeds
- [ ] Active Model shows different data for each
- [ ] No crashes or hangs

### Expected Results ✅

**Success Indicators**:
- Multiple imports work without issues
- Each model loads with different data
- Can switch between models without restarting

---

## Test Results Summary

### Use This Template

```
PHASE 1 TESTING RESULTS
Date: ___________
Tester: ___________
Duration: ___________ minutes

Test 1: Import Model
Status: [ ] Pass  [ ] Fail  [ ] Partial
Notes: _________________________________

Test 2: View Active Model
Status: [ ] Pass  [ ] Fail  [ ] Partial
Notes: _________________________________

Test 3: Run Wizard
Status: [ ] Pass  [ ] Fail  [ ] Partial
Notes: _________________________________

Test 4: View Updated Model
Status: [ ] Pass  [ ] Fail  [ ] Partial
Notes: _________________________________

Test 5: Export Model
Status: [ ] Pass  [ ] Fail  [ ] Partial
Notes: _________________________________

Test 6: Bonus Testing (Optional)
Status: [ ] Pass  [ ] Fail  [ ] Partial  [ ] Skipped
Notes: _________________________________

OVERALL STATUS: [ ] All Pass  [ ] Some Failures  [ ] Major Issues

Critical Issues Found:
1. _________________________________
2. _________________________________
3. _________________________________

Minor Issues Found:
1. _________________________________
2. _________________________________
3. _________________________________

Overall Impression:
_________________________________
_________________________________
```

---

## Success Criteria

### Minimum Acceptable (Core Functionality)
- ✅ Can import at least one CIBD22X file
- ✅ Can view imported model data
- ✅ Can export model back to CIBD22X
- ✅ No crashes or app-breaking errors

### Fully Functional (All Features)
- ✅ All 5 main tests pass
- ✅ Wizard successfully generates systems
- ✅ Multiple imports work
- ✅ Exported file is valid
- ✅ GUI is responsive and user-friendly

### Production Ready
- ✅ All tests pass consistently
- ✅ No critical errors
- ✅ Performance is acceptable (<10s for operations)
- ✅ Data integrity maintained (no data loss)

---

## What to Do After Testing

### If All Tests Pass ✅
1. Document success in results template
2. Move to Phase 2 testing (simulation features)
3. Push all bugfix commits to GitHub
4. Celebrate! 🎉

### If Some Tests Fail ⚠️
1. Document which tests failed
2. Copy exact error messages
3. Note specific steps that caused failure
4. Report here for immediate fixes

### If Major Issues 🔴
1. Stop testing
2. Document the critical issue
3. Copy full error traces
4. Report immediately for emergency fix

---

## Quick Commands Reference

**Launch GUI**:
```bash
cd /Users/DavidM/Documents/ECO_Alpha_v7
streamlit run gui/main.py
```

**Check running**:
```bash
lsof -ti:8501
```

**Stop GUI**:
```bash
# Press Ctrl+C in terminal
```

**Clear cache** (if issues):
```bash
rm -rf ~/.streamlit/cache
```

**Check file**:
```bash
ls -lh test_output/bressi_ranch_test_export.cibd22x
```

---

## Known Issues (from development)

### Expected/Normal
- First import may be slower (loading modules)
- Large files (>5MB) may take 30+ seconds
- Some wizard options may not be visible yet (Phase 6 features)

### May Encounter
- File upload button briefly greyed during page load (normal)
- Spinner may appear stuck but is actually working (wait)
- Some advanced features may not be fully implemented

### Report If Seen
- Any Python errors in terminal
- Any "ModuleNotFoundError" messages
- GUI becomes unresponsive (not just slow)
- Data loss (import succeeds but model is empty)

---

## Tips for Effective Testing

### Do's ✅
- Test one step at a time
- Wait for operations to complete
- Document exact error messages
- Take screenshots of issues
- Note the sequence of actions that caused problem

### Don'ts ❌
- Don't click multiple times rapidly (can confuse Streamlit)
- Don't close browser while import/export running
- Don't skip verification steps
- Don't assume failure without checking terminal

---

## After Phase 1

If Phase 1 tests pass, you're ready for:

**Phase 2**: Simulation Testing
- Run CBECC-Com simulation
- Run EnergyPlus simulation
- View results
- Test visualization

**Phase 3**: Advanced Features
- Editing modes
- Comparison tools
- Template browser
- Round-trip validation

---

**Ready to begin! Start with Test 1: Import Model** 🚀

Good luck! Report any issues as you encounter them for immediate fixes.
