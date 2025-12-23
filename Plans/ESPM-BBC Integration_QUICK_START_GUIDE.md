# ESPM/BBC Integration - Quick Start Guide

## Executive Summary

Based on review of ECO Alpha v7 codebase, this integration adds Energy Star Portfolio Manager (ESPM) and Better Buildings Challenge (BBC) capabilities to your existing Streamlit application.

**Key Finding**: Alphav7 uses **Streamlit** (not FastAPI), so our integration strategy differs from the original ECO Tools Suite plans which assumed REST APIs.

---

## What We're Building

### New Capabilities
1. **Portfolio Management** - Track multiple buildings across Mercy Housing portfolio
2. **ESPM Export** - Generate XML files for Portfolio Manager upload
3. **BBC/BCC Tracking** - Monitor progress toward 20%/50% reduction goals
4. **Compliance Reporting** - Automated quarterly DOE submissions

### Integration Points
```
Alphav7 Architecture:
├── Core: InternalRepresentation → Maps to ESPM Property
├── LCCA: HourlyEnergy (8760) → Maps to ESPM Monthly Bills
├── Simulation: CBECC Results → ENERGY STAR Metrics
└── GUI: Streamlit Pages → New Portfolio/ESPM pages
```

---

## Phase 1: Getting Started (Week 1)

### 1. Create Module Structure

```bash
cd /Users/DavidM/Documents/ECO_Alpha_v7/

# Create new integration directory
mkdir -p eco_tools/integrations/espm

# Create Python files
touch eco_tools/integrations/espm/__init__.py
touch eco_tools/integrations/espm/espm_models.py
touch eco_tools/integrations/espm/espm_mapper.py
touch eco_tools/integrations/espm/espm_xml_builder.py
touch eco_tools/integrations/espm/espm_exporter.py
touch eco_tools/integrations/espm/bbc_tracker.py
```

### 2. Install Dependencies

```bash
# Update requirements.txt
cat >> requirements.txt << EOF

# ESPM Integration
requests>=2.31.0
reportlab>=4.0.0
openpyxl>=3.1.0
EOF

# Install
pip install -r requirements.txt
```

### 3. Implement Data Models

Start with `eco_tools/integrations/espm/espm_models.py` - copy from the main plan document, Section 4.1.

**Critical Models**:
- `ESPMProperty` - Building characteristics
- `ESPMMeter` - Utility meters
- `ESPMBillEntry` - Monthly consumption
- `BBCGoal` - Organization commitment
- `BBCProgressReport` - Quarterly tracking

---

## Phase 2: Data Mapping (Week 2)

### Key Mapping Logic

**InternalRepresentation → ESPM**:
```python
# Total area
total_area_m2 = sum(z.floor_area_m2 for z in model.zones)
total_area_sf = total_area_m2 * 10.764

# Primary use type
space_functions = [z.space_function for z in model.zones]
# Map to ESPM types: 'Office', 'Multifamily Housing', etc.

# Address - from user input (not in IR)
# Year built - from user input
# Occupancy - from user input
```

**HourlyEnergy → Monthly Bills**:
```python
# Aggregate 8760 hours to 12 months
monthly_elec = {}
for hour in simulation.hourly:
    month_key = hour.month
    monthly_elec[month_key] = monthly_elec.get(month_key, 0) + hour.elec_total_kwh

# Create bill entries
for month, kwh in monthly_elec.items():
    bill = ESPMBillEntry(
        meter_id="elec_001",
        start_date=date(2023, month, 1),
        end_date=date(2023, month, 28),  # Adjust for month
        usage=kwh
    )
```

Implement `espm_mapper.py` - copy from Section 4.2 of main plan.

---

## Phase 3: XML Export (Week 3)

### ESPM XML Structure

```xml
<?xml version="1.0"?>
<propertyReport xmlns="http://portfoliomanager.energystar.gov/schema">
  <property>
    <name>Building Name</name>
    <address>
      <address1>123 Main St</address1>
      <city>Los Angeles</city>
      <state>CA</state>
    </address>
    <yearBuilt>2015</yearBuilt>
    <grossFloorArea units="Square Feet">50000</grossFloorArea>
  </property>
  
  <meters>
    <meter>
      <name>Electric - Grid</name>
      <type>Electric - Grid</type>
      <unitOfMeasure>kWh</unitOfMeasure>
    </meter>
  </meters>
  
  <meterData>
    <meterConsumption>
      <startDate>2023-01-01</startDate>
      <endDate>2023-01-31</endDate>
      <usage>10000</usage>
    </meterConsumption>
  </meterData>
</propertyReport>
```

Implement `espm_xml_builder.py` and `espm_exporter.py`.

---

## Phase 4: Streamlit GUI (Weeks 4-6)

### New Pages to Create

```bash
cd gui/pages

# Create new page files
touch portfolio_page.py
touch espm_export_page.py
touch bbc_dashboard_page.py
```

### Update Main Navigation

Edit `gui/main.py`:

```python
# Add to page list
pages = [
    "Import",
    "Build Model",
    # ... existing pages ...
    "Portfolio Management",      # NEW
    "ESPM Export",              # NEW
    "BBC Dashboard",            # NEW
]
```

### Portfolio Page Features

1. **Buildings List**
   - Display all buildings in portfolio
   - Show EUI, emissions, area
   - Add/remove buildings

2. **BBC Goals**
   - Set baseline year and metrics
   - Define 10-year targets
   - Track commitment dates

3. **Analytics Dashboard**
   - Progress charts
   - On-track status
   - DOE report generation

---

## Testing Strategy

### Unit Tests

```bash
# Create test files
mkdir -p tests/integration
touch tests/integration/test_espm_integration.py
```

**Test Coverage**:
- Data model validation
- Mapping accuracy
- XML generation
- BBC calculations

### Integration Testing

```python
# Test complete workflow
def test_complete_espm_export():
    # 1. Load test model
    model = load_test_cibd()
    
    # 2. Run simulation (mock)
    sim = create_mock_simulation()
    
    # 3. Export to ESPM
    exporter = ESPMExporter()
    xml_path = exporter.export_to_espm_xml(
        model, sim, 'test_export.xml'
    )
    
    # 4. Validate XML
    assert os.path.exists(xml_path)
    # Parse and validate structure
```

---

## Deployment Checklist

### Pre-Deployment
- [ ] All unit tests passing
- [ ] Integration tests passing
- [ ] Documentation complete
- [ ] User guide created
- [ ] Feature flags configured

### Deployment
- [ ] Merge to main branch
- [ ] Update requirements.txt
- [ ] Create release notes
- [ ] Tag version (e.g., v7.1.0)

### Post-Deployment
- [ ] User training for Mercy Housing
- [ ] Monitor error logs
- [ ] Collect user feedback
- [ ] Plan Phase 2 enhancements

---

## Key Differences from Original Plans

### What Changed?

**Original ECO Tools Plans** (from implementation_plan_X.md):
- Assumed FastAPI REST API
- Planned web service endpoints
- API authentication layer
- Database-backed persistence

**Actual Alphav7 Architecture**:
- ✅ Streamlit GUI (not REST API)
- ✅ Session state (not database)
- ✅ Direct file export (not API sync)
- ✅ Python modules (not microservices)

### Why This Matters

Instead of bi-directional API integration, we're building:
1. **Export-focused** - Generate files for ESPM upload
2. **GUI-driven** - Streamlit pages for user interaction
3. **Session-based** - Portfolio data in `st.session_state`
4. **File-based reporting** - XML/CSV/PDF downloads

This is **simpler and faster** than the original API approach, and perfectly suited for Mercy Housing's workflow where they manually upload to Portfolio Manager.

---

## Success Metrics for Mercy Housing

### Immediate Value (Month 1)
- ✅ Export 10+ buildings to ESPM XML
- ✅ Set BBC goal baseline
- ✅ Generate first quarterly report

### 3-Month Goals
- ✅ 50+ buildings in portfolio
- ✅ Quarterly reporting automated
- ✅ BBC progress tracking live

### 6-Month Goals
- ✅ Integration with EnergyScoreCards (optional)
- ✅ Historical data import
- ✅ Multi-year trend analysis

---

## Next Steps

1. **Review this plan** with your team
2. **Set up development environment**
3. **Start with Phase 1** (data models)
4. **Test with one building** from Mercy Housing
5. **Iterate based on feedback**

---

## Questions for Discussion

1. **Data Sources**: Where does Mercy Housing currently store baseline EUI and emissions data?
2. **Reporting Frequency**: Are quarterly DOE submissions manual or can they be automated?
3. **EnergyScoreCards**: Do you want to integrate with their existing ESC workflow?
4. **Historical Data**: Do you need to import past years' performance data?
5. **Portfolio Scope**: How many buildings total? How many in first pilot?

---

## Resources

- **Main Integration Plan**: See full document for complete code examples
- **ESPM Documentation**: https://portfoliomanager.energystar.gov
- **BBC Program**: https://betterbuildingssolutioncenter.energy.gov/challenge
- **Alphav7 Docs**: See `/mnt/project/` for architecture reference

---

**Ready to Start?** Begin with Phase 1 - create the module structure and implement the Pydantic models. Let me know if you need any clarification or want to dive deeper into any section!
