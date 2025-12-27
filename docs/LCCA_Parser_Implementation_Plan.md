# LCCA Parser Implementation Plan

## Objective
Maximize granularity of LCCA input data by parsing all relevant CBECC simulation artifacts.

## Current State

### Existing Parsers (Implemented)
| Parser | File | Status |
|--------|------|--------|
| `HourlyResultsParser` | `*- ap - HourlyResults.csv` | Complete |
| `CseHourlyParser` | `*CSE*.csv` | Basic - needs update |
| `HVACSecondaryParser` | `*- ap - HVACSecondary.csv` | Complete |
| `HVACPrimaryParser` | `*- ap - HVACPrimary.csv` | Complete |
| `EnvelopeParser` | `*- ap - Envelope.csv` | Complete |
| `AnalysisResultsParser` | `*AnalysisResults.xml` | Complete (DHW, breakdowns added) |

### New Parsers Needed
| Parser | File | Priority |
|--------|------|----------|
| `HVACCapsParser` | `*-HVACCAPS.CSV` | High - residential sizing |
| `CSEInputParser` | `*-cse.cse` | High - DHW specifications |
| `NRCCPRFParser` | `*- NRCCPRF.xml` | Medium - project summary |
| `EnergyComparisonParser` | AnalysisResults.xml | High - extend existing |
| `CSEHourlyParserV2` | `*-CSE.CSV` | Medium - detailed end uses |

---

## Phase 1: Energy Comparison from AnalysisResults.xml (Priority: Critical)

**Goal:** Extract Proposed AND Standard energy data from single XML file

### Data to Extract
```python
@dataclass
class EnergyEndUse:
    name: str                    # "Space Heating", "Cooling", etc.
    proposed_elec_kbtu: float    # PropElecEnergy
    standard_elec_kbtu: float    # StdElecEnergy
    proposed_gas_kbtu: float     # PropNatGasEnergy
    standard_gas_kbtu: float     # StdNatGasEnergy
    proposed_tdv: float          # ProposedTDV (kTDV/ft²)
    standard_tdv: float          # StandardTDV
    margin_tdv: float            # CompMarginTDV

@dataclass
class EnergyComparison:
    end_uses: List[EnergyEndUse]
    total_proposed_elec: float
    total_standard_elec: float
    total_proposed_gas: float
    total_standard_gas: float
    compliance_margin: float
```

### Implementation
- **File:** `parsers/analysis_results_xml.py` (extend existing)
- **Method:** `_parse_energy_comparison(root)`
- **XPath:** `//Model[@Name="Standard"]/EnergyUse`

### Estimated Effort: 2-3 hours

---

## Phase 2: HVACCAPS.CSV Parser (Priority: High)

**Goal:** Parse residential HVAC auto-sized capacities

### File Format
```csv
"runDateTime","SysName","HtgCap","ClgCap","SysName","HtgCap","ClgCap",...
"Tue 23-Dec-25  8:5 am","Dwelling Unit_L01_1BR HVACSys",33.8878,34.3957,...
```

### Data to Extract
```python
@dataclass
class HVACCapacity:
    system_name: str          # "Dwelling Unit_L01_1BR HVACSys"
    heating_cap_kbtuh: float  # 33.88 kBtu/h
    cooling_cap_kbtuh: float  # 34.40 kBtu/h

@dataclass
class HVACCapsOutput:
    run_datetime: datetime
    capacities: List[HVACCapacity]
    total_heating_cap: float
    total_cooling_cap: float
```

### Implementation
- **File:** `parsers/hvac_caps.py` (new)
- **Format:** Simple CSV with repeating column groups
- **Discovery:** Add `HVAC_CAPS_PROPOSED`, `HVAC_CAPS_BASELINE` to file types

### Estimated Effort: 2-3 hours

---

## Phase 3: CSE Input Parser for DHW (Priority: High)

**Goal:** Extract DHW equipment specifications from CSE input files

### File Format
```
DHWHEATER "dhwhtr1-t24-CHPWH"
   whType = "BuiltUp"
   whASHPType = "SandenGS3"
   whVol = 111.111111
   whEF = 0.92
```

### Data to Extract
```python
@dataclass
class CSEDHWHeater:
    name: str                      # "dhwhtr1-t24-CHPWH"
    heater_type: str               # "BuiltUp", "SmallInstantaneous"
    ashp_type: Optional[str]       # "SandenGS3", "Scalable_SP"
    volume_gal: float              # 111.11
    energy_factor: Optional[float] # 0.92
    uef: Optional[float]           # Uniform Energy Factor
    input_rating_btuh: Optional[float]
    recovery_efficiency: Optional[float]

@dataclass
class CSEDHWSystem:
    name: str
    heaters: List[CSEDHWHeater]
    recirculation_type: str

@dataclass
class CSEInputOutput:
    dhw_heaters: List[CSEDHWHeater]
    dhw_systems: List[CSEDHWSystem]
    # Future: HVAC system specs if useful
```

### Implementation
- **File:** `parsers/cse_input.py` (new)
- **Format:** Custom text with named blocks and parameters
- **Parser approach:**
  ```python
  def parse_block(lines, block_type):
      # Match: BLOCKTYPE "name"
      # Extract indented key = value pairs
  ```

### Estimated Effort: 4-5 hours (text parsing complexity)

---

## Phase 4: Enhanced CSE.CSV Parser (Priority: Medium)

**Goal:** Parse detailed hourly data with 20+ end-use columns

### File Format
```csv
"Meter","Mon","Day","Hr","Subhr","Tot","Clg","Htg","HPBU","Dhw","DhwBU",...
"MtrElec",1,1,1,"",80.0593,0,8.36018,0.0960447,0,0,...
```

### Data to Extract
```python
@dataclass
class CSEHourlyRow:
    meter: str           # "MtrElec", "MtrFuel"
    month: int
    day: int
    hour: int
    total: float
    cooling: float
    heating: float
    hp_backup: float
    dhw: float
    dhw_backup: float
    dhw_mfl: float       # Makeup/Losses
    fan_cooling: float
    fan_heating: float
    fan_ventilation: float
    fan_other: float
    auxiliary: float
    process: float
    lighting: float
    receptacle: float
    exterior: float
    refrigerator: float
    dishwasher: float
    dryer: float
    washer: float
    cooking: float
    user1: float
    user2: float
    battery: float
    pv: float

@dataclass
class CSEHourlyOutput:
    electric_rows: List[CSEHourlyRow]
    fuel_rows: List[CSEHourlyRow]

    # Aggregated
    annual_by_enduse: Dict[str, float]
    peak_demand_kw: float
    peak_hour: Tuple[int, int, int]  # month, day, hour
```

### Implementation
- **File:** `parsers/cse_hourly.py` (update existing)
- **Add:** New V2 parser for detailed format
- **Benefit:** Individual appliance breakdown for residential

### Estimated Effort: 3-4 hours

---

## Phase 5: NRCCPRF.xml Parser (Priority: Medium)

**Goal:** Quick access to project summary metrics

### Data to Extract
```python
@dataclass
class ProjectSummary:
    project_name: str
    dwelling_units: int
    conditioned_floor_area_sf: float
    unconditioned_floor_area_sf: float
    climate_zone: int
    above_grade_stories: int
    building_type: str
    compliance_result: str  # Pass/Fail
    compliance_margin: float
```

### Implementation
- **File:** `parsers/nrccprf.py` (new)
- **Format:** Simple XML with Info* tags
- **Use case:** Dashboard summary, project identification

### Estimated Effort: 1-2 hours

---

## Phase 6: Auto-Discovery Updates

### New File Types to Discover
```python
class SimulationFileType(str, Enum):
    # Existing...

    # New types
    HVAC_CAPS_PROPOSED = "hvac_caps_proposed"
    HVAC_CAPS_BASELINE = "hvac_caps_baseline"
    CSE_INPUT_PROPOSED = "cse_input_proposed"
    CSE_INPUT_BASELINE = "cse_input_baseline"
    CSE_HOURLY_PROPOSED = "cse_hourly_proposed"
    CSE_HOURLY_BASELINE = "cse_hourly_baseline"
    NRCCPRF = "nrccprf"
```

### File Patterns
| Type | Pattern |
|------|---------|
| HVAC Caps (Proposed) | `*- AP-HVACCAPS.CSV` |
| HVAC Caps (Baseline) | `*- AB-HVACCAPS.CSV` |
| CSE Input (Proposed) | `*- ap-cse.cse` |
| CSE Input (Baseline) | `*- ab-cse.cse` |
| CSE Hourly (Proposed) | `*- AP-CSE.CSV` |
| CSE Hourly (Baseline) | `*- AB-CSE.CSV` |
| NRCCPRF | `*- NRCCPRF.xml` |

### Estimated Effort: 2 hours

---

## Phase 7: Unified LCCA Data Aggregator

**Goal:** Single entry point that aggregates all parsed data

### Architecture
```python
@dataclass
class LCCAInputData:
    """Complete LCCA input data from all sources."""

    # Project info
    project: ProjectSummary

    # Energy data
    energy_comparison: EnergyComparison
    hourly_proposed: CSEHourlyOutput
    hourly_baseline: CSEHourlyOutput

    # HVAC data
    hvac_systems_proposed: HVACSecondaryOutput
    hvac_systems_baseline: HVACSecondaryOutput
    hvac_capacities_proposed: HVACCapsOutput
    hvac_capacities_baseline: HVACCapsOutput

    # DHW data
    dhw_proposed: CSEInputOutput
    dhw_baseline: CSEInputOutput

    # Envelope data
    envelope_proposed: EnvelopeOutput
    envelope_baseline: EnvelopeOutput

    # Construction breakdowns (from XML)
    wall_breakdown: List[ConstructionTypeBreakdown]
    roof_breakdown: List[ConstructionTypeBreakdown]
    window_breakdown: List[ConstructionTypeBreakdown]

class LCCADataAggregator:
    """Aggregates data from all parsers."""

    def __init__(self, project_dir: Path):
        self.discovery = SimulationDiscovery(project_dir)

    def parse_all(self) -> LCCAInputData:
        """Parse all available files and return unified data."""
        files = self.discovery.discover()

        data = LCCAInputData(
            project=self._parse_project_summary(files),
            energy_comparison=self._parse_energy_comparison(files),
            # ... etc
        )

        return data
```

### Estimated Effort: 4-5 hours

---

## Implementation Schedule

### Week 1: Critical Path
| Day | Task | Hours |
|-----|------|-------|
| 1 | Phase 1: Energy comparison parsing | 3 |
| 2 | Phase 2: HVACCAPS.CSV parser | 3 |
| 3-4 | Phase 3: CSE input parser for DHW | 5 |

### Week 2: Enhancement
| Day | Task | Hours |
|-----|------|-------|
| 1-2 | Phase 4: Enhanced CSE.CSV parser | 4 |
| 3 | Phase 5: NRCCPRF.xml parser | 2 |
| 4 | Phase 6: Auto-discovery updates | 2 |

### Week 3: Integration
| Day | Task | Hours |
|-----|------|-------|
| 1-2 | Phase 7: Unified aggregator | 5 |
| 3 | Testing across all models | 3 |
| 4 | Documentation and cleanup | 2 |

---

## Data Granularity Achieved

After implementation, LCCA will have access to:

### Energy Data
- [ ] Annual energy by end use (Proposed vs Baseline)
- [ ] Hourly profiles (8760 hours)
- [ ] Individual appliance consumption (Dish, Dry, Wash, Cook, Refr)
- [ ] Peak demand and timing
- [ ] TDV values by end use
- [ ] Compliance margin

### HVAC Data
- [ ] System types (SZHP, VRF, PVAV, etc.)
- [ ] Auto-sized capacities (heating/cooling kBtu/h)
- [ ] Efficiency ratings (SEER, HSPF, COP)
- [ ] Fan power
- [ ] Coil details

### DHW Data
- [ ] Water heater type (HPWH, conventional, tankless)
- [ ] Heat pump model (SandenGS3, Scalable_SP, etc.)
- [ ] Tank volume
- [ ] Energy factor / UEF
- [ ] Input rating
- [ ] Proposed vs Baseline equipment comparison

### Envelope Data
- [ ] Wall areas by construction type with U-factors
- [ ] Roof areas by construction type with U-factors
- [ ] Window areas by type with U-factor and SHGC
- [ ] Solar reflectance
- [ ] Window-to-wall ratio

### Project Data
- [ ] Dwelling units
- [ ] Conditioned floor area
- [ ] Climate zone
- [ ] Building stories
- [ ] Compliance result

---

## Files to Create/Modify

### New Files
1. `parsers/hvac_caps.py` - HVACCAPS parser
2. `parsers/cse_input.py` - CSE input file parser
3. `parsers/nrccprf.py` - NRCCPRF parser
4. `lcca_aggregator.py` - Unified data aggregator

### Files to Modify
1. `parsers/analysis_results_xml.py` - Add energy comparison
2. `parsers/cse_hourly.py` - Add V2 detailed parser
3. `parsers/__init__.py` - Export new parsers
4. `auto_discovery.py` - Add new file types

---

## Testing Strategy

### Unit Tests
- Parser tests for each new file format
- Edge case handling (missing files, partial data)
- Cross-version compatibility (CBECC 2022 vs 2025)

### Integration Tests
- Full aggregation on Bressi Ranch
- Full aggregation on Del Amo
- Full aggregation on CUAC 2025 sample
- Baseline vs Proposed data matching

### Validation
- Compare parsed capacities to CBECC UI values
- Verify energy totals match HourlyResults sums
- Confirm DHW specs match model inputs

---

*Plan created: December 2024*
*Based on LCCA_Data_Sources_Lessons_Learned.md*
