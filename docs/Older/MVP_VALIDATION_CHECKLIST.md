# ECO Tools v7 - MVP Validation Checklist

**Date:** November 13, 2025
**Current Status:** Phase 5/6 Complete (83%)
**Branch:** `v7-restructure`

---

## Executive Summary

ECO Tools v7 is **close to MVP** but requires completion of **critical validation and integration testing** to be production-ready. This document identifies what remains to achieve a validated MVP tool.

**Overall MVP Readiness: 75%**

---

## 🎯 MVP Definition

A **validated MVP** for ECO Tools must be able to:

1. ✅ **Import** building models from multiple formats (GEM, CIBD22X, HBJSON)
2. ✅ **Create** building models via interactive wizard
3. ✅ **Edit** models through GUI
4. ✅ **Export** to compliance formats (CIBD22, CIBD22X, CIBD25, HBJSON)
5. ⚠️ **Simulate** models using CBECC (Title 24) - **NEEDS VALIDATION**
6. ⚠️ **Simulate** models using EnergyPlus (detailed analysis) - **NEEDS VALIDATION**
7. ⚠️ **Compare** results from both engines - **NEEDS VALIDATION**
8. ❌ **Visualize** results with charts and graphs - **NOT COMPLETE**
9. ❌ **Export** results to reports (PDF/CSV) - **PARTIAL** (CSV only)
10. ❌ **Test** end-to-end workflows - **NOT COMPLETE**

---

## 📊 Feature Completion Status

### ✅ COMPLETE (100%)

#### 1. Multi-Format Import/Export
- **CIBD22** - Title 24 2019/2022 format ✅
- **CIBD22X** - Title 24 2022 XML format ✅
- **CIBD25** - Title 24 2025 format ✅
- **HBJSON** - Ladybug/Honeybee format ✅
- **GEM** - IES VE Revit export format ✅
- **EMJSON** - Internal format ✅

**Status:** Production-ready with comprehensive schema validation

#### 2. Model Building Wizard
- Interactive step-by-step wizard ✅
- Building type templates (20+ types) ✅
- Climate zone library (all 16 CA zones) ✅
- HVAC system creation ✅
- Construction assignments ✅
- Schedule generation ✅

**Status:** Fully functional, user-tested

#### 3. GUI Application
- Import page ✅
- Wizard page ✅
- Active model viewer ✅
- Model editor (tables, geometry) ✅
- Export page ✅
- Diagnostics page ✅
- Round-trip checker ✅
- Simulation page ✅

**Status:** Complete with all planned pages

### ⚠️ IMPLEMENTED BUT NOT VALIDATED (50-90%)

#### 4. CBECC Integration
**What Works:**
- ✅ CBECC subprocess execution via CLI
- ✅ Results parser (XML structure)
- ✅ Compliance status extraction
- ✅ TDV value parsing
- ✅ End use breakdown parsing

**What Needs Validation:**
- ❌ **Actual CBECC simulation runs** (not tested with real CBECC yet)
- ❌ **Results parser accuracy** (no sample AnalysisResults.xml files tested)
- ❌ **Error handling** (unknown failure modes)
- ❌ **CLI flag compatibility** (CBECC 2022 vs 2025)

**Gap:** Need to run actual CBECC simulations and validate parser with real outputs

**Files:**
- `eco_tools/simulation/cbecc_bridge.py` - Bridge implementation ⚠️
- `eco_tools/simulation/cbecc_results_parser.py` - Parser ⚠️
- `docs/CBECC_CLI_FINDINGS.md` - Research complete ✅
- `docs/ECO_TOOLS_CBECC_INTEGRATION.md` - Integration guide ✅

#### 5. EnergyPlus Integration
**What Works:**
- ✅ EnergyPlus runner via Honeybee-Energy
- ✅ HBJSON export for simulation
- ✅ SQL results parsing
- ✅ EUI extraction
- ✅ End use extraction

**What Needs Validation:**
- ❌ **Full workflow test** (EMJSON → HBJSON → IDF → Simulate → Parse)
- ❌ **Large model performance** (290+ zones)
- ❌ **Results accuracy** (comparison with known values)
- ❌ **Weather file handling** (different locations)

**Gap:** Need end-to-end simulation workflow testing

**Files:**
- `eco_tools/simulation/energyplus_runner.py` - Runner implementation ⚠️
- `gui/pages/simulation_page.py` - GUI integration ⚠️

#### 6. Results Comparison
**What Works:**
- ✅ Side-by-side comparison table
- ✅ Delta calculations
- ✅ Percentage differences
- ✅ GUI display

**What Needs Validation:**
- ❌ **Accuracy of comparisons** (no real simulation data yet)
- ❌ **Unit conversions** (CBECC vs EnergyPlus units)
- ❌ **Metric alignment** (mapping end uses correctly)

**Gap:** Need real simulation results to validate comparison logic

### ❌ NOT COMPLETE (0-30%)

#### 7. Results Visualization
**Status: 30% Complete**

**What Exists:**
- ✅ Basic chart infrastructure (`eco_tools/visualization/charts.py`)
- ✅ Unit tests for charts (`tests/unit/test_charts.py`)
- ✅ Plotly integration capability

**What's Missing:**
- ❌ **Interactive bar charts** for end use comparison
- ❌ **Line charts** for monthly profiles
- ❌ **Heatmaps** for hourly data
- ❌ **Gauge charts** for compliance margins
- ❌ **GUI integration** (charts not shown in simulation page)

**Estimated Effort:** 1-2 days

**Priority:** HIGH - Critical for MVP

#### 8. PDF Report Generation
**Status: 0% Complete**

**What's Missing:**
- ❌ Report generator module
- ❌ PDF template system
- ❌ Chart export to PDF
- ❌ Executive summary generation
- ❌ Compliance certificate output

**Partial Implementation:**
- ✅ CSV export exists (`eco_tools/reporting/csv_exporter.py`)
- ✅ Unit tests for CSV export

**Estimated Effort:** 2-3 days

**Priority:** MEDIUM - Nice to have for MVP, not critical

#### 9. Comprehensive Testing
**Status: 20% Complete**

**What Exists:**
- ✅ Unit tests for CBECC parser (18 tests)
- ✅ Unit tests for charts (7 tests)
- ✅ Unit tests for CSV exporter
- ✅ One roundtrip test (CIBD22X)

**What's Missing:**
- ❌ **Integration tests** for full workflows
- ❌ **Simulation workflow tests** (import → simulate → compare)
- ❌ **Large model tests** (performance benchmarks)
- ❌ **Multi-format roundtrip tests** (all 9 combinations)
- ❌ **GUI workflow tests**
- ❌ **Error handling tests**

**Estimated Effort:** 2-3 days

**Priority:** HIGH - Critical for production readiness

#### 10. User Documentation
**Status: 10% Complete**

**What Exists:**
- ✅ Technical documentation (EMJSON schema, CBECC integration)
- ✅ Architecture docs
- ✅ Phase completion docs

**What's Missing:**
- ❌ **User guide** (getting started, tutorials)
- ❌ **Feature guides** (how to use each feature)
- ❌ **Troubleshooting guide**
- ❌ **FAQ**
- ❌ **Video tutorials** (optional)

**Estimated Effort:** 1-2 days

**Priority:** MEDIUM - Important for adoption, not blocking MVP

---

## 🚧 Critical Gaps for MVP

### Priority 1: MUST HAVE (Blocking MVP)

#### Gap 1: CBECC Simulation Validation
**Issue:** CBECC integration implemented but never tested with actual CBECC execution

**Required Actions:**
1. ✅ Install CBECC 2022 and/or CBECC 2025 (already done on macOS)
2. ❌ Export a model to CIBD22X/CIBD25
3. ❌ Run CBECC simulation via CLI
4. ❌ Collect AnalysisResults.xml output
5. ❌ Validate parser with real results
6. ❌ Fix any parsing issues
7. ❌ Document actual CLI flags and behavior

**Estimated Time:** 4-6 hours

**Risk:** HIGH - Unknown if parser will work with real data

#### Gap 2: EnergyPlus Workflow Testing
**Issue:** EnergyPlus integration implemented but full workflow not tested

**Required Actions:**
1. ❌ Create test model (via wizard or import)
2. ❌ Export to HBJSON
3. ❌ Run EnergyPlus simulation
4. ❌ Parse SQL results
5. ❌ Validate accuracy
6. ❌ Test with large model (290 zones)
7. ❌ Document performance characteristics

**Estimated Time:** 3-4 hours

**Risk:** MEDIUM - Honeybee should work but needs validation

#### Gap 3: Results Visualization
**Issue:** Charts infrastructure exists but not integrated or functional

**Required Actions:**
1. ❌ Implement end use comparison bar chart
2. ❌ Add monthly energy line chart
3. ❌ Create compliance gauge chart
4. ❌ Integrate charts into simulation page
5. ❌ Add chart export capability
6. ❌ Test with real simulation data

**Estimated Time:** 1-2 days

**Risk:** LOW - Plotly well documented, straightforward implementation

#### Gap 4: Integration Testing
**Issue:** No end-to-end workflow tests exist

**Required Actions:**
1. ❌ Create integration test suite structure
2. ❌ Test: Import GEM → Export CIBD22X → Simulate CBECC
3. ❌ Test: Wizard → Export HBJSON → Simulate EnergyPlus
4. ❌ Test: Import → Edit → Export → Simulate → Compare
5. ❌ Test: Large model performance (Bressi Ranch)
6. ❌ Test: All format roundtrips
7. ❌ Document test results

**Estimated Time:** 2-3 days

**Risk:** MEDIUM - May uncover integration bugs

### Priority 2: SHOULD HAVE (Important but not blocking)

#### Gap 5: PDF Report Generation
**Estimated Time:** 2-3 days
**Risk:** LOW - Well-established libraries available

#### Gap 6: User Documentation
**Estimated Time:** 1-2 days
**Risk:** LOW - Straightforward content creation

#### Gap 7: Error Handling & UI Polish
**Estimated Time:** 1 day
**Risk:** LOW - Incremental improvements

---

## 📋 MVP Validation Checklist

### Phase 1: Core Functionality Validation (MUST HAVE)

#### CBECC Simulation
- [ ] Export model to CIBD22X format
- [ ] Run CBECC 2022 simulation via CLI (`-nrp -b`)
- [ ] Verify AnalysisResults.xml is created
- [ ] Parse results successfully
- [ ] Extract compliance status (Pass/Fail)
- [ ] Extract TDV values and margin
- [ ] Extract end use breakdown
- [ ] Handle simulation errors gracefully
- [ ] Test with CIBD25 and CBECC 2025
- [ ] Document actual behavior vs expected

**Success Criteria:** Can run CBECC simulation and parse results for any model

#### EnergyPlus Simulation
- [ ] Export model to HBJSON format
- [ ] Verify HBJSON is valid (open in Honeybee)
- [ ] Run EnergyPlus simulation
- [ ] Verify SQL results file created
- [ ] Parse EUI successfully
- [ ] Parse end uses successfully
- [ ] Test with weather file variations
- [ ] Test with large model (290+ zones)
- [ ] Measure simulation time
- [ ] Document performance characteristics

**Success Criteria:** Can run EnergyPlus simulation and extract results for any model

#### Results Comparison
- [ ] Run both CBECC and EnergyPlus on same model
- [ ] Compare EUI values (should be within reasonable range)
- [ ] Verify end use categories align
- [ ] Calculate deltas correctly
- [ ] Display comparison table in GUI
- [ ] Test with multiple building types
- [ ] Document expected accuracy ranges

**Success Criteria:** Can compare results from both engines with clear visualizations

#### Visualization
- [ ] Implement end use bar chart (CBECC vs EnergyPlus)
- [ ] Implement compliance gauge (Title 24 margin)
- [ ] Implement monthly energy line chart
- [ ] Integrate charts into simulation page
- [ ] Test chart updates with different data
- [ ] Add chart export (PNG)
- [ ] Ensure charts are responsive

**Success Criteria:** All simulation results have clear visual representations

### Phase 2: Integration & Reliability (SHOULD HAVE)

#### End-to-End Workflows
- [ ] **Workflow 1:** Import GEM → View → Export CIBD22X → Simulate
- [ ] **Workflow 2:** Wizard → Build Model → Export HBJSON → Simulate
- [ ] **Workflow 3:** Import CIBD22 → Edit → Export CIBD25 → Simulate
- [ ] **Workflow 4:** Create Model → Simulate Both → Compare → Export CSV
- [ ] **Workflow 5:** Large Model (290 zones) → Full workflow

**Success Criteria:** All workflows complete without errors

#### Format Roundtrips
- [ ] CIBD22 → EMJSON → CIBD22 (data preserved)
- [ ] CIBD22X → EMJSON → CIBD22X (data preserved)
- [ ] CIBD25 → EMJSON → CIBD25 (data preserved)
- [ ] HBJSON → EMJSON → HBJSON (geometry preserved)
- [ ] GEM → EMJSON → CIBD22X (conversion accurate)

**Success Criteria:** All format conversions preserve essential data

#### Error Handling
- [ ] Invalid file import handled gracefully
- [ ] Simulation failure shows helpful error
- [ ] Missing CBECC installation detected
- [ ] Missing EnergyPlus installation detected
- [ ] Network/file permission errors handled
- [ ] User sees actionable error messages

**Success Criteria:** No crashes, all errors are user-friendly

### Phase 3: Documentation & Polish (NICE TO HAVE)

#### User Documentation
- [ ] Getting started guide
- [ ] Import workflow tutorial
- [ ] Wizard usage guide
- [ ] Simulation guide
- [ ] Troubleshooting common issues
- [ ] FAQ section

**Success Criteria:** New user can complete basic workflow using docs

#### Reporting
- [ ] CSV export works for all results
- [ ] PDF report generation (optional)
- [ ] Report includes all key metrics
- [ ] Report is professional quality

**Success Criteria:** Users can export results for stakeholders

---

## ⏱️ Time Estimates to MVP

### Minimum MVP (Core Functionality Only)
**Focus:** Get simulations working and validated

| Task | Time | Priority |
|------|------|----------|
| CBECC simulation validation | 4-6 hours | P0 |
| EnergyPlus workflow testing | 3-4 hours | P0 |
| Results visualization | 1-2 days | P0 |
| Basic integration tests | 1 day | P0 |
| Bug fixes from testing | 1 day | P0 |

**Total: 4-5 days** ⚡

### Full MVP (Production Ready)
**Focus:** Complete all MVP features

| Phase | Time | Priority |
|-------|------|----------|
| Core functionality validation | 4-5 days | P0 |
| Comprehensive integration tests | 2-3 days | P1 |
| PDF reporting | 2-3 days | P1 |
| User documentation | 1-2 days | P1 |
| UI/UX polish | 1 day | P2 |
| Final testing & bug fixes | 1-2 days | P0 |

**Total: 11-16 days** (aligns with Phase 6 estimate)

---

## 🎯 Recommended Approach

### Week 1: Core Validation (Days 1-5)
**Goal:** Get simulations working and validated

**Day 1-2: CBECC Integration**
- Set up test environment
- Run actual CBECC simulations
- Validate parser with real results
- Fix any issues
- Document findings

**Day 2-3: EnergyPlus Integration**
- Test full workflow
- Validate results accuracy
- Test large models
- Document performance

**Day 4-5: Visualization**
- Implement charts
- Integrate into GUI
- Test with real data
- Polish presentation

**Deliverable:** Working simulations with visual results

### Week 2: Validation & Testing (Days 6-10)
**Goal:** Ensure reliability and document usage

**Day 6-8: Integration Testing**
- Create test suite
- Test all workflows
- Test edge cases
- Fix bugs

**Day 8-9: Documentation**
- Write user guide
- Create tutorials
- Document troubleshooting

**Day 10: Polish & Release**
- Final testing
- Bug fixes
- Prepare v7.0.0 release

**Deliverable:** Production-ready MVP

---

## 🚀 Quick Start Path to MVP

If you need the **fastest path to a working MVP**:

### Essential Only (3-4 days)

1. **Day 1: CBECC Validation** (6 hours)
   - Run one CBECC simulation
   - Validate parser works
   - Fix critical issues only

2. **Day 1-2: EnergyPlus Test** (4 hours)
   - Run one EnergyPlus simulation
   - Verify results parsing works

3. **Day 2-3: Basic Charts** (1 day)
   - End use bar chart only
   - Compliance gauge only
   - Integrate into GUI

4. **Day 4: Integration Test** (1 day)
   - One complete workflow test
   - Fix blocking bugs only

**Result:** Minimal viable product that demonstrates all features

---

## 📊 Current State vs MVP Target

| Feature | Current | MVP Target | Gap |
|---------|---------|------------|-----|
| Import/Export | 100% | 100% | ✅ None |
| Model Building | 100% | 100% | ✅ None |
| GUI | 95% | 95% | ✅ None |
| CBECC Sim | 70% | 100% | ⚠️ Validation needed |
| EnergyPlus Sim | 80% | 100% | ⚠️ Testing needed |
| Visualization | 30% | 90% | ❌ Charts needed |
| Reporting | 40% | 80% | ⚠️ CSV only |
| Testing | 20% | 80% | ❌ Integration tests needed |
| Documentation | 10% | 70% | ❌ User docs needed |

**Overall: 75% → 95% = 20% gap to MVP**

---

## ✅ Definition of Done (MVP)

The MVP is **complete and validated** when:

1. ✅ User can import any supported format
2. ✅ User can create models via wizard
3. ✅ User can export to all compliance formats
4. ✅ User can run CBECC simulation successfully
5. ✅ User can run EnergyPlus simulation successfully
6. ✅ User can compare results visually (charts)
7. ✅ User can export results (CSV minimum)
8. ✅ All core workflows tested end-to-end
9. ✅ Common errors handled gracefully
10. ✅ Basic user documentation exists

**Success Metric:** Complete one full workflow (Import → Edit → Simulate → Compare → Export) without errors

---

## 🎉 Next Steps

### Immediate (This Week)
1. **Run first CBECC simulation** - Validate integration works
2. **Run first EnergyPlus simulation** - Test full workflow
3. **Implement basic charts** - End use comparison + compliance gauge

### Short Term (Next Week)
4. **Create integration test suite** - Automate workflow testing
5. **Write user guide** - Getting started + tutorials
6. **Final testing & polish** - Bug fixes and refinements

### Release Preparation
7. **Version bump to v7.0.0** - Official MVP release
8. **Git tag and release notes** - Document achievements
9. **Share with stakeholders** - Gather feedback

---

**Status:** Ready to begin MVP validation
**Confidence:** HIGH - Clear path to completion
**Timeline:** 4-16 days depending on scope
**Recommendation:** Start with 3-4 day fast path, expand if time permits

---

**Created:** November 13, 2025
**Author:** ECO Tools Development Team
**Purpose:** Define clear path to validated MVP
