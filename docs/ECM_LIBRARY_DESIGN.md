# ECM Library Design Document

## Research Summary

This document synthesizes findings from three major sources to inform a comprehensive
ECM (Energy Conservation Measure) library for the LCCA module.

### Sources Reviewed

1. **OpenStudio BCL (Building Component Library)**
   - 303 measures across 11 categories
   - Source: [BCL Browse](https://bcl.nrel.gov/browse)
   - Assessment: [ORNL Pub204139](https://info.ornl.gov/sites/publications/Files/Pub204139.pdf)

2. **CEC CASE Reports (2025 Title 24)**
   - Cost-effectiveness studies for California Energy Code
   - Source: [Title 24 Stakeholders](https://title24stakeholders.com/2025-cycle-case-reports/)
   - Focus: Residential, Multifamily, Nonresidential measures

3. **Ladybug Tools / Honeybee**
   - Parametric energy analysis framework
   - Source: [Ladybug Tools](https://www.ladybug.tools/)
   - Integration: OpenStudio measures + EnergyPlus

---

## Proposed ECM Taxonomy

### Expanded Category Structure

Based on BCL structure with California-specific additions:

```
ECMCategory (Expanded)
├── GENERATION
│   ├── Photovoltaic
│   ├── Battery Storage
│   └── CHP/Cogeneration
│
├── ENVELOPE
│   ├── Opaque (Walls, Roofs, Floors)
│   ├── Fenestration (Windows, Skylights)
│   ├── Infiltration (Air Sealing)
│   ├── Cool Roofs
│   └── Form (Geometry optimization)
│
├── HVAC
│   ├── Heating
│   │   ├── Heat Pumps (Air-source, Ground-source)
│   │   ├── Furnace Efficiency
│   │   └── Radiant Systems
│   ├── Cooling
│   │   ├── Chillers
│   │   ├── DX Systems
│   │   └── Evaporative Cooling
│   ├── Ventilation
│   │   ├── ERV/HRV
│   │   ├── Central Supply
│   │   ├── DOAS
│   │   └── Demand Control (DCV)
│   ├── Distribution
│   │   ├── Duct Sealing
│   │   ├── VAV
│   │   └── Ductless
│   ├── Controls
│   │   ├── Guideline 36 (ASHRAE)
│   │   ├── Economizer
│   │   └── Night Setback
│   └── Whole System
│       ├── VRF
│       ├── Packaged Systems
│       └── Central Plant
│
├── DHW (Domestic Hot Water)
│   ├── Heat Pump Water Heaters
│   ├── Solar Thermal
│   ├── Pipe Insulation
│   └── Distribution Efficiency
│
├── LIGHTING
│   ├── Equipment (LED)
│   ├── Controls (Occupancy, Daylighting)
│   └── Daylighting Integration
│
├── PLUGLOAD
│   ├── Equipment Efficiency
│   └── Controls (Scheduling, Power Management)
│
├── REFRIGERATION
│   ├── Walk-in Coolers/Freezers
│   ├── Display Cases
│   └── Evaporator Efficiency
│
├── CONTROLS
│   ├── BMS/EMS
│   ├── Scheduling
│   └── Fault Detection (FDD)
│
└── OTHER
    ├── Commercial Kitchens
    ├── Pools/Spas
    ├── Laboratories
    └── Horticulture
```

---

## BCL Measure Coverage Analysis

### Category Breakdown (303 measures)

| Category              | Count | Subcategories                                    |
|-----------------------|-------|--------------------------------------------------|
| Envelope              | 88    | Opaque (41), Form (25), Fenestration (12), Infiltration (8) |
| HVAC                  | 69    | Whole System (28), Cooling (14), Heating (8), Distribution (7), Ventilation (6) |
| Whole Building        | 51    | Space Types (38), Schedules (13)                 |
| Reporting/QAQC        | 45    | QAQC (40), Troubleshooting (5)                   |
| Electric Lighting     | 15    | Equipment (10), Controls (5)                     |
| Economics             | 14    | Life Cycle Cost Analysis (14)                    |
| Equipment             | 11    | Electric (6), Controls (5)                       |
| Service Water Heating | 6     | Water Heating (6)                                |
| Onsite Power Gen      | 3     | Photovoltaic (3)                                 |
| People                | 1     | Characteristics (1)                              |

### Identified Gaps (per ORNL assessment)

- Different types of PV panels
- Green roof systems
- Thermal storage
- Chiller heat recovery
- Low-temperature heat pumps
- Decarbonization-focused measures (emerging)

---

## CEC CASE Measures (2025 Title 24)

### Multifamily (Priority for CUAC workflow)

| Measure                    | Key Elements                                       |
|----------------------------|----------------------------------------------------|
| Indoor Air Quality         | Compartmentalization, balanced ventilation         |
| Domestic Hot Water         | HPWH ventilation, pipe sizing, demand control      |
| Envelope                   | Cool roofs, wall R-values, high-performance windows|
| HVAC Performance           | HP sizing, refrigerant charge, defrost efficiency  |
| Restructuring              | Slab insulation, VT requirements, shaft sealing    |

### Single Family

| Measure                    | Key Elements                                       |
|----------------------------|----------------------------------------------------|
| High-Performance Envelope  | U-factor requirements for walls and windows        |
| Residential HVAC           | Heat pump sizing, charge verification, defrost     |
| Buried Ducts               | Cathedral ceiling requirements                     |

### Nonresidential

| Measure                    | Key Elements                                       |
|----------------------------|----------------------------------------------------|
| HVAC Controls              | ASHRAE Guideline 36 implementation                 |
| Cooling Towers             | Efficiency, FDD, air-cooled limits                 |
| Laboratory Airflow         | Nighttime setback, exhaust, reheat limits          |
| Commercial Kitchens        | DCKV, electric readiness                           |
| Nonresidential Envelope    | Opaque assemblies, vestibules, windows             |

---

## Implementation Priority

### Phase 1: Residential/Multifamily (Current Focus)

Already implemented:
- [x] `create_pv_ecm()` - PV systems
- [x] `create_electrification_ecm()` - Generic fuel switching
- [x] `create_efficiency_ecm()` - Generic efficiency
- [x] `create_erv_ecm()` - ERV systems
- [x] `create_central_vent_ecm()` - Central ventilation (Maestro)
- [x] `create_minisplit_ecm()` - Ductless heat pumps
- [x] `create_hpwh_ecm()` - Heat pump water heaters
- [x] `create_ecm_from_cuac_comparison()` - CUAC integration

To add:
- [ ] `create_envelope_ecm()` - Wall/roof insulation improvements
- [ ] `create_window_ecm()` - High-performance windows
- [ ] `create_air_sealing_ecm()` - Infiltration reduction
- [ ] `create_central_hpwh_ecm()` - Central HPWH systems
- [ ] `create_led_lighting_ecm()` - Interior lighting

### Phase 2: Commercial/Nonresidential

- [ ] `create_vrf_ecm()` - VRF systems
- [ ] `create_chiller_ecm()` - High-efficiency chillers
- [ ] `create_cooling_tower_ecm()` - Cooling tower upgrades
- [ ] `create_economizer_ecm()` - Economizer addition/upgrade
- [ ] `create_dcv_ecm()` - Demand control ventilation
- [ ] `create_bms_ecm()` - Building management system
- [ ] `create_exterior_lighting_ecm()` - Site lighting

### Phase 3: Specialized

- [ ] Laboratory measures
- [ ] Commercial kitchen measures
- [ ] Refrigeration measures
- [ ] Pool/spa heating
- [ ] Horticulture

---

## ECM Data Model Enhancements

### Proposed Additions to ECM Dataclass

```python
@dataclass
class ECM:
    # ... existing fields ...

    # New fields for BCL compatibility
    subcategory: Optional[str] = None      # e.g., "Opaque", "Fenestration"
    bcl_uid: Optional[str] = None          # BCL measure UUID
    applicable_building_types: List[str] = field(default_factory=list)
    climate_zone_applicability: List[int] = field(default_factory=list)

    # Code compliance
    code_baseline: Optional[str] = None    # e.g., "T24-2022", "ASHRAE 90.1-2019"
    compliance_credit: Optional[str] = None  # Compliance pathway credit

    # Uncertainty/sensitivity
    capex_range: Optional[Tuple[float, float]] = None  # (low, high)
    savings_range: Optional[Tuple[float, float]] = None

    # Data quality
    source: Optional[str] = None           # Data source reference
    vintage: Optional[int] = None          # Year of cost/performance data
```

### ECMLibrary Class (New)

```python
class ECMLibrary:
    """
    Centralized library of ECM templates with cost data.

    Supports:
    - Loading from JSON/YAML configuration
    - Filtering by building type, climate zone, category
    - Automatic cost escalation
    - Regional cost adjustments
    """

    def __init__(self):
        self._templates: Dict[str, ECMTemplate] = {}
        self._cost_data: CostDatabase = create_default_costdb()

    def get_ecm(self, name: str, **overrides) -> ECM:
        """Get ECM from template with optional overrides."""
        pass

    def list_by_category(self, category: ECMCategory) -> List[str]:
        """List all ECMs in a category."""
        pass

    def list_for_building_type(self, building_type: str) -> List[str]:
        """List applicable ECMs for building type."""
        pass

    def search(self, query: str) -> List[str]:
        """Search ECM names and descriptions."""
        pass
```

---

## Integration with Existing Code

### Current Module Structure
```
eco_tools/lcca/
├── ecm_bundle.py       # ECM dataclass and templates
├── costdb.py           # Cost database
├── calculators.py      # NPV, IRR, payback
├── sensitivity.py      # Monte Carlo, tornado
└── cuac/               # CUAC parsing
```

### Proposed Additions
```
eco_tools/lcca/
├── ecm_bundle.py       # Core ECM dataclass (enhanced)
├── ecm_library.py      # NEW: ECM template library
├── ecm_templates/      # NEW: Category-specific templates
│   ├── __init__.py
│   ├── residential.py  # Residential HVAC, DHW, envelope
│   ├── commercial.py   # Commercial HVAC, lighting
│   ├── generation.py   # PV, battery, CHP
│   └── envelope.py     # Walls, roofs, windows, infiltration
├── ecm_data/           # NEW: ECM configuration files
│   ├── residential_hvac.json
│   ├── commercial_hvac.json
│   └── envelope.json
```

---

## Cost Data Sources

### Primary Sources

1. **RSMeans** - Construction cost data
2. **NREL Annual Technology Baseline (ATB)** - PV, storage costs
3. **CEC CASE Reports** - California-specific measure costs
4. **DEER (Database for Energy Efficient Resources)** - IOU program costs

### Cost Escalation

Use existing `EscalationRate` from `costdb.py`:
- Electricity: 2.5%/year
- Natural gas: 2.0%/year
- Construction: 3.0%/year

### Regional Adjustments

Use existing `RegionalFactor` from `costdb.py`:
- Bay Area: 1.15
- Los Angeles: 1.10
- Central Valley: 0.95
- San Diego: 1.08

---

## Next Steps

1. **Expand ECM dataclass** with subcategory, applicability fields
2. **Create ECMLibrary class** for template management
3. **Add Phase 1 templates** (envelope, windows, air sealing)
4. **Build JSON configuration** for ECM defaults
5. **Integrate with CUAC workflow** for automatic ECM generation
6. **Add unit tests** for new templates and library

---

## References

- [OpenStudio BCL](https://bcl.nrel.gov/browse)
- [CEC 2025 CASE Reports](https://title24stakeholders.com/2025-cycle-case-reports/)
- [Ladybug Tools](https://www.ladybug.tools/)
- [Honeybee Energy Standards](https://github.com/ladybug-tools/honeybee-energy-standards)
- [ASHRAE Guideline 36](https://www.ashrae.org/technical-resources/guideline-36)
