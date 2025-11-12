# ECO_Alpha v7 - Quick Start for Testing

**Ready to test?** Follow these 3 steps to get started.

---

## Step 1: Pre-Flight Check (30 seconds)

Run the automated verification:

```bash
cd /Users/DavidM/Documents/ECO_Alpha_v7
python3 preflight_check.py
```

**Expected Output**: `✅ ALL CHECKS PASSED`

If any checks fail, the script will tell you what to install.

---

## Step 2: Launch the GUI (10 seconds)

```bash
streamlit run gui/main.py
```

**Expected Result**: Browser opens to `http://localhost:8501`

---

## Step 3: Run Quick Test (5 minutes)

### Fastest Path to See Results:

1. **Import** → Select CIBD22X → Browse to Bressi Ranch file → Import
2. **Build Model** → Fill project info → Click "Quick Setup"
3. **Simulate** → CBECC tab → Export to CIBD22X
4. **View** → Active Model to see completed model

**That's it!** You've verified the core workflow works.

---

## Full Testing (Optional - 60 minutes)

See `docs/TESTING_CHECKLIST.md` for comprehensive testing guide covering:
- All 7 testing phases
- CBECC and EnergyPlus simulations
- Visualization and export features
- Edge cases and performance

---

## Key Files

**For Testing**:
- `docs/TESTING_CHECKLIST.md` - Detailed testing guide
- `preflight_check.py` - Automated verification
- `docs/USER_GUIDE.md` - Usage instructions

**For Development**:
- `docs/API_REFERENCE.md` - Technical API docs
- `docs/PHASE_6_COMPLETE.md` - What was built
- `docs/FUTURE_3D_MODELING_ENHANCEMENT.md` - Next steps

---

## Test File Location

**CIBD22X files**:
```
/Users/DavidM/Documents/ECO_Alpha/reference_data/cbecc/CBECC Models/
├── Bressi Ranch/
│   └── Bressi Ranch Apartments.cibd22x  ← Recommended test file
└── (other sample projects)
```

---

## Common Commands

**Launch GUI**:
```bash
streamlit run gui/main.py
```

**Run Unit Tests**:
```bash
python3 -m pytest tests/unit/ -v
```

**Check Dependencies**:
```bash
python3 preflight_check.py
```

---

## What to Test

**Priority 1 (Must Work)**:
- ✅ Import CIBD22X file
- ✅ Wizard completes model
- ✅ Active Model displays data
- ✅ Export to CIBD22X works

**Priority 2 (Important)**:
- ✅ CBECC simulation runs (if CBECC installed)
- ✅ EnergyPlus simulation runs
- ✅ Results comparison displays
- ✅ Charts render correctly

**Priority 3 (Nice to Have)**:
- ✅ All chart types work
- ✅ CSV exports download
- ✅ Performance acceptable
- ✅ No crashes on edge cases

---

## Expected Performance

- **GUI Launch**: < 5 seconds
- **Import CIBD22X**: < 10 seconds
- **Wizard Quick Setup**: < 2 seconds
- **Export to CIBD22X**: < 5 seconds
- **CBECC Simulation**: 1-3 minutes
- **EnergyPlus Simulation**: 1-5 minutes
- **Chart Rendering**: < 1 second
- **CSV Export**: < 1 second

---

## If Something Goes Wrong

**GUI won't launch**:
```bash
pip install --upgrade streamlit plotly
```

**Import fails**:
- Check file path is correct
- Verify file is valid CIBD22X format
- Check import log for specific errors

**Simulation fails**:
- CBECC: Check CBECC-Com is installed
- EnergyPlus: Check honeybee-energy installed
- Both: Review simulation logs for details

**Charts missing**:
```bash
pip install --upgrade plotly
```

---

## Getting Help

1. **Check User Guide**: `docs/USER_GUIDE.md` - Troubleshooting section
2. **Check Testing Guide**: `docs/TESTING_CHECKLIST.md` - Known issues
3. **Check API Docs**: `docs/API_REFERENCE.md` - Technical details
4. **Create Notes**: Document issues for discussion

---

## Success Indicators

**You'll know it's working when**:
- ✅ GUI loads without errors
- ✅ Files import successfully
- ✅ Wizard generates systems
- ✅ Simulations complete (or clear error if not installed)
- ✅ Results display with charts
- ✅ CSV files download

---

## Quick Reference Card

```
┌─────────────────────────────────────────────────────────┐
│ ECO_Alpha v7 Quick Reference                            │
├─────────────────────────────────────────────────────────┤
│ Launch:     streamlit run gui/main.py                   │
│ Pre-Check:  python3 preflight_check.py                  │
│ Tests:      python3 -m pytest tests/unit/ -v            │
├─────────────────────────────────────────────────────────┤
│ Docs:       docs/USER_GUIDE.md                          │
│ Testing:    docs/TESTING_CHECKLIST.md                   │
│ API:        docs/API_REFERENCE.md                       │
├─────────────────────────────────────────────────────────┤
│ Test File:  ECO_Alpha/reference_data/cbecc/...          │
│ Output:     ECO_Alpha_v7/test_output/                   │
└─────────────────────────────────────────────────────────┘
```

---

## Ready to Test!

**Minimum viable test** (5 minutes):
1. Run preflight check
2. Launch GUI
3. Import a file
4. Run wizard
5. View active model

**Full test** (60 minutes):
- Follow `docs/TESTING_CHECKLIST.md`

**Questions?**
- See documentation in `docs/` directory
- All APIs documented in `docs/API_REFERENCE.md`

---

**Happy Testing! 🚀**

The platform is production-ready and waiting for your feedback.
