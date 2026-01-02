# Whole-Building Energy Architecture

**Version:** 1.0
**Date:** December 2024
**Status:** Design

---

## 1. Executive Summary

This document defines the architecture for whole-building energy reporting that:
- Combines simulation engine output (CBECC, future EnergyPlus) with calculated site loads
- Maintains clean separation between modeled and calculated energy
- Provides full 8760 hourly profiles for accurate TOU analysis
- Supports configurable reporting granularity
- Is engine-agnostic for future EnergyPlus/ASHRAE 90.1 integration

**Key Principle**: No injection of site loads into simulation models. Parallel calculation with aggregation at the reporting layer.

---

## 2. Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Report granularity | Configurable | Clients have different needs - some want full transparency, others want simple totals |
| TOU precision | Full 8760 profiles | Site loads get synthetic hourly data via load shapes for accurate TOU |
| EnergyPlus timeline | Medium-term (2026) | Design abstractions now, implement when LEED v5 requires it |
| Integration method | Parallel aggregation | No injection into simulation files - cleaner architecture |

---

## 3. High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         DATA SOURCES                                         │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌─────────────────────────┐       ┌─────────────────────────┐             │
│  │  SIMULATION ENGINE      │       │  SITE LOAD INPUTS       │             │
│  │                         │       │                         │             │
│  │  • CBECC (T-24)        │       │  • Data Collection      │             │
│  │  • EnergyPlus (future) │       │    Sheet (Excel/JSON)   │             │
│  │                         │       │                         │             │
│  │  Output:                │       │  Categories:            │             │
│  │  • HourlyResults CSV   │       │  • Interior lighting    │             │
│  │  • CSE hourly          │       │  • Parking              │             │
│  │  • E+ SQL (future)     │       │  • Pools/spas           │             │
│  │                         │       │  • Elevators            │             │
│  └───────────┬─────────────┘       │  • EV chargers          │             │
│              │                      │  • IT/telecom           │             │
│              │                      │  • Pumps                │             │
│              │                      │  • etc.                 │             │
│              │                      └───────────┬─────────────┘             │
│              │                                  │                            │
└──────────────┼──────────────────────────────────┼────────────────────────────┘
               │                                  │
               ▼                                  ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         PARSING LAYER                                        │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌─────────────────────────┐       ┌─────────────────────────┐             │
│  │  SimulationParser       │       │  SiteLoadCalculator     │             │
│  │  (Abstract Interface)   │       │                         │             │
│  │                         │       │  For each load:         │             │
│  │  Implementations:       │       │  1. Calculate annual    │             │
│  │  • CbeccParser         │       │     kWh/therms          │             │
│  │  • EnergyPlusParser    │       │  2. Apply load shape    │             │
│  │    (future)            │       │  3. Generate 8760       │             │
│  │                         │       │     hourly profile      │             │
│  │  Returns:               │       │                         │             │
│  │  SimulationOutput       │       │  Returns:               │             │
│  │  (8760 hourly)          │       │  SiteLoadOutput         │             │
│  │                         │       │  (8760 hourly)          │             │
│  └───────────┬─────────────┘       └───────────┬─────────────┘             │
│              │                                  │                            │
└──────────────┼──────────────────────────────────┼────────────────────────────┘
               │                                  │
               ▼                                  ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                    UNIFIED ENERGY SCHEMA                                     │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌───────────────────────────────────────────────────────────────────────┐ │
│  │  WholeBuildingEnergy                                                   │ │
│  │                                                                        │ │
│  │  ├── project_info: ProjectInfo                                        │ │
│  │  │                                                                     │ │
│  │  ├── modeled: EnergyStream                                            │ │
│  │  │   ├── source: "CBECC" | "EnergyPlus"                              │ │
│  │  │   ├── annual: AnnualSummary                                        │ │
│  │  │   ├── hourly: List[HourlyRecord]  # 8760                          │ │
│  │  │   └── end_uses: Dict[EndUse, float]                               │ │
│  │  │                                                                     │ │
│  │  ├── site_loads: EnergyStream                                         │ │
│  │  │   ├── source: "Calculated"                                         │ │
│  │  │   ├── annual: AnnualSummary                                        │ │
│  │  │   ├── hourly: List[HourlyRecord]  # 8760 synthetic                │ │
│  │  │   ├── by_category: Dict[LoadCategory, CategorySummary]            │ │
│  │  │   └── load_details: List[SiteLoad]                                │ │
│  │  │                                                                     │ │
│  │  └── combined: EnergyStream                                           │ │
│  │      ├── annual: AnnualSummary  # modeled + site_loads               │ │
│  │      ├── hourly: List[HourlyRecord]  # merged 8760                   │ │
│  │      └── peak_demand_kw: float  # coincident peak                    │ │
│  │                                                                        │ │
│  └───────────────────────────────────────────────────────────────────────┘ │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         REPORTING LAYER                                      │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐       │
│  │   LCCA      │  │   TOU       │  │   Energy    │  │   Client    │       │
│  │  Analysis   │  │  Analysis   │  │   Summary   │  │  Reports    │       │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘       │
│                                                                              │
│  Report Modes (Configurable):                                               │
│  ┌────────────────────────────────────────────────────────────────────┐    │
│  │ FULL:     Show modeled | site loads | combined (3 columns)        │    │
│  │ SUMMARY:  Show site loads | combined (2 columns)                  │    │
│  │ SIMPLE:   Show combined only (1 column)                           │    │
│  └────────────────────────────────────────────────────────────────────┘    │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 4. Core Data Models

### 4.1 Unified Energy Schema

```python
from dataclasses import dataclass, field
from typing import List, Dict, Optional
from enum import Enum
from datetime import datetime

class EnergySource(Enum):
    CBECC = "cbecc"
    ENERGYPLUS = "energyplus"
    CALCULATED = "calculated"

class ReportMode(Enum):
    FULL = "full"           # Modeled | Site Loads | Combined
    SUMMARY = "summary"     # Site Loads | Combined
    SIMPLE = "simple"       # Combined only

@dataclass
class HourlyRecord:
    """Single hour of energy data."""
    month: int
    day: int
    hour: int
    elec_kwh: float = 0.0
    gas_therms: float = 0.0
    demand_kw: float = 0.0

    # End-use breakdown (optional, for modeled data)
    cooling_kwh: float = 0.0
    heating_kwh: float = 0.0
    heating_therms: float = 0.0
    fans_kwh: float = 0.0
    lighting_kwh: float = 0.0
    plugs_kwh: float = 0.0
    dhw_kwh: float = 0.0
    dhw_therms: float = 0.0
    pv_kwh: float = 0.0

@dataclass
class AnnualSummary:
    """Annual energy totals."""
    total_elec_kwh: float = 0.0
    total_gas_therms: float = 0.0
    peak_demand_kw: float = 0.0
    pv_generation_kwh: float = 0.0
    net_elec_kwh: float = 0.0

    # Monthly peaks for demand analysis
    monthly_peaks_kw: List[float] = field(default_factory=lambda: [0.0] * 12)

@dataclass
class EnergyStream:
    """A stream of energy data (modeled, site loads, or combined)."""
    source: EnergySource
    annual: AnnualSummary
    hourly: List[HourlyRecord]  # 8760 records

    @classmethod
    def from_hourly(cls, source: EnergySource, hourly: List[HourlyRecord]) -> 'EnergyStream':
        """Create stream with annual summary calculated from hourly data."""
        annual = AnnualSummary(
            total_elec_kwh=sum(h.elec_kwh for h in hourly),
            total_gas_therms=sum(h.gas_therms for h in hourly),
            peak_demand_kw=max(h.demand_kw for h in hourly)
        )
        # Calculate monthly peaks
        for month in range(1, 13):
            month_hours = [h for h in hourly if h.month == month]
            if month_hours:
                annual.monthly_peaks_kw[month - 1] = max(h.demand_kw for h in month_hours)

        return cls(source=source, annual=annual, hourly=hourly)

@dataclass
class SiteLoadDetail:
    """Detail for a single site load category."""
    category: str
    name: str
    annual_kwh: float = 0.0
    annual_therms: float = 0.0
    peak_kw: float = 0.0
    hourly: List[HourlyRecord] = field(default_factory=list)

    # Calculation inputs (audit trail)
    inputs: Dict = field(default_factory=dict)
    calculation_method: str = ""

@dataclass
class ProjectInfo:
    """Project metadata."""
    name: str
    address: Optional[str] = None
    climate_zone: Optional[int] = None
    building_type: Optional[str] = None
    floor_area_sf: Optional[float] = None
    simulation_engine: Optional[str] = None
    simulation_file: Optional[str] = None

@dataclass
class WholeBuildingEnergy:
    """Complete whole-building energy data."""
    project: ProjectInfo
    modeled: EnergyStream
    site_loads: EnergyStream
    combined: EnergyStream

    # Detailed site load breakdown
    site_load_details: List[SiteLoadDetail] = field(default_factory=list)

    @classmethod
    def create(
        cls,
        project: ProjectInfo,
        modeled: EnergyStream,
        site_loads: EnergyStream
    ) -> 'WholeBuildingEnergy':
        """Create whole-building energy with auto-calculated combined stream."""

        # Merge hourly data
        combined_hourly = []
        for i in range(8760):
            m = modeled.hourly[i]
            s = site_loads.hourly[i]
            combined_hourly.append(HourlyRecord(
                month=m.month,
                day=m.day,
                hour=m.hour,
                elec_kwh=m.elec_kwh + s.elec_kwh,
                gas_therms=m.gas_therms + s.gas_therms,
                demand_kw=m.demand_kw + s.demand_kw,  # Simplified; real would use diversity
                cooling_kwh=m.cooling_kwh,
                heating_kwh=m.heating_kwh,
                heating_therms=m.heating_therms,
                fans_kwh=m.fans_kwh,
                lighting_kwh=m.lighting_kwh + s.lighting_kwh,
                plugs_kwh=m.plugs_kwh,
                dhw_kwh=m.dhw_kwh,
                dhw_therms=m.dhw_therms,
                pv_kwh=m.pv_kwh
            ))

        combined = EnergyStream.from_hourly(EnergySource.CALCULATED, combined_hourly)

        return cls(
            project=project,
            modeled=modeled,
            site_loads=site_loads,
            combined=combined
        )
```

### 4.2 Simulation Parser Interface

```python
from abc import ABC, abstractmethod

class SimulationParser(ABC):
    """Abstract interface for simulation engine parsers."""

    @abstractmethod
    def parse(self, file_path: str) -> EnergyStream:
        """Parse simulation output to unified energy stream."""
        pass

    @abstractmethod
    def get_project_info(self, file_path: str) -> ProjectInfo:
        """Extract project metadata from simulation files."""
        pass

class CbeccParser(SimulationParser):
    """Parser for CBECC HourlyResults CSV."""

    def parse(self, file_path: str) -> EnergyStream:
        # Existing implementation in eco_tools/lcca/parsers/hourly_results.py
        pass

class EnergyPlusParser(SimulationParser):
    """Parser for EnergyPlus output (future implementation)."""

    def parse(self, file_path: str) -> EnergyStream:
        # Future: Parse E+ SQL or CSV output
        # Normalize to same EnergyStream format as CBECC
        raise NotImplementedError("EnergyPlus parser planned for 2026")
```

---

## 5. Load Shape Profiles for 8760 Generation

### 5.1 Concept

Site loads are calculated as annual totals. To enable accurate TOU analysis, we generate synthetic hourly profiles using **load shape profiles** that represent typical usage patterns.

```
Annual kWh × Load Shape Profile = 8760 Hourly kWh
```

### 5.2 Load Shape Categories

| Load Category | Profile Type | Peak Hours | Weekend Factor |
|---------------|--------------|------------|----------------|
| Interior Lighting (Common) | Building hours | 6am-10pm | 0.8 |
| Interior Lighting (24/7) | Flat | 24/7 | 1.0 |
| Parking Lighting | Inverse daylight | Dusk-dawn | 1.0 |
| Pool Pump | Daytime | 8am-6pm | 1.0 |
| Pool Heater | Morning peak | 5am-9am | 1.0 |
| EV Chargers | Evening/night | 6pm-6am | 0.7 |
| Elevators | Building hours | 7am-7pm | 0.5 |
| IT/Telecom | Flat 24/7 | Constant | 1.0 |
| Trash Compactor | Midday spikes | 10am, 2pm, 6pm | 0.3 |
| Security Systems | Flat 24/7 | Constant | 1.0 |

### 5.3 Load Shape Data Structure

```python
@dataclass
class LoadShapeProfile:
    """8760 hourly multipliers that sum to 1.0."""
    name: str
    category: str
    hourly_factors: List[float]  # 8760 values, sum = 1.0

    def apply(self, annual_kwh: float) -> List[float]:
        """Apply profile to annual total, returning hourly values."""
        return [annual_kwh * factor for factor in self.hourly_factors]

class LoadShapeLibrary:
    """Library of standard load shape profiles."""

    profiles: Dict[str, LoadShapeProfile] = {}

    @classmethod
    def get_profile(cls, category: str) -> LoadShapeProfile:
        """Get load shape profile for a category."""
        return cls.profiles.get(category, cls.profiles['flat_24x7'])

    @classmethod
    def generate_building_hours_profile(
        cls,
        start_hour: int = 6,
        end_hour: int = 22,
        weekend_factor: float = 0.8
    ) -> LoadShapeProfile:
        """Generate a typical building hours profile."""
        factors = []
        for month in range(1, 13):
            for day in range(1, 32):  # Simplified
                for hour in range(24):
                    is_weekend = (day % 7) in [0, 6]  # Simplified
                    if start_hour <= hour < end_hour:
                        factor = 1.0 if not is_weekend else weekend_factor
                    else:
                        factor = 0.1  # Minimal overnight
                    factors.append(factor)

        # Normalize to sum = 1.0
        total = sum(factors)
        factors = [f / total for f in factors]

        return LoadShapeProfile(
            name="Building Hours",
            category="building_hours",
            hourly_factors=factors[:8760]  # Truncate to 8760
        )
```

### 5.4 Profile Sources

Load shape profiles can come from:
1. **Standard templates** - Based on typical usage patterns
2. **ASHRAE 90.1 schedules** - Mapped from standard schedules
3. **CBECC schedules** - Extracted from CIBD schedule definitions
4. **Custom profiles** - User-defined for specific projects
5. **Metered data** - If available from similar buildings

---

## 6. Site Load Calculator with Hourly Output

```python
@dataclass
class SiteLoadCalculator:
    """Calculator that produces 8760 hourly output for each site load."""

    load_shapes: LoadShapeLibrary = field(default_factory=LoadShapeLibrary)

    def calculate_load(
        self,
        load_type: str,
        inputs: Dict,
        load_shape: Optional[str] = None
    ) -> SiteLoadDetail:
        """Calculate a site load with hourly profile."""

        # Step 1: Calculate annual totals
        annual_kwh, annual_therms, peak_kw = self._calculate_annual(load_type, inputs)

        # Step 2: Get load shape profile
        profile = self.load_shapes.get_profile(load_shape or load_type)

        # Step 3: Generate 8760 hourly data
        hourly_kwh = profile.apply(annual_kwh)
        hourly_therms = profile.apply(annual_therms) if annual_therms > 0 else [0.0] * 8760

        # Step 4: Create hourly records
        hourly = self._create_hourly_records(hourly_kwh, hourly_therms)

        return SiteLoadDetail(
            category=load_type,
            name=inputs.get('name', load_type),
            annual_kwh=annual_kwh,
            annual_therms=annual_therms,
            peak_kw=peak_kw,
            hourly=hourly,
            inputs=inputs,
            calculation_method=f"Annual × {profile.name} load shape"
        )

    def calculate_all_loads(
        self,
        site_load_inputs: Dict[str, List[Dict]]
    ) -> EnergyStream:
        """Calculate all site loads and combine into single stream."""

        all_loads: List[SiteLoadDetail] = []

        for load_type, load_list in site_load_inputs.items():
            for inputs in load_list:
                load = self.calculate_load(load_type, inputs)
                all_loads.append(load)

        # Combine all hourly profiles
        combined_hourly = self._combine_hourly(all_loads)

        return EnergyStream.from_hourly(EnergySource.CALCULATED, combined_hourly)

    def _calculate_annual(
        self,
        load_type: str,
        inputs: Dict
    ) -> Tuple[float, float, float]:
        """Calculate annual kWh, therms, and peak kW."""

        # Route to appropriate calculator
        calculators = {
            'interior_lighting': self._calc_interior_lighting,
            'parking': self._calc_parking,
            'pool_pump': self._calc_pool_pump,
            'pool_heater': self._calc_pool_heater,
            'elevator': self._calc_elevator,
            'ev_charger': self._calc_ev_charger,
            'it_telecom': self._calc_it_telecom,
            # ... etc
        }

        calc_func = calculators.get(load_type)
        if calc_func:
            return calc_func(inputs)
        else:
            raise ValueError(f"Unknown load type: {load_type}")

    def _calc_interior_lighting(self, inputs: Dict) -> Tuple[float, float, float]:
        """Calculate interior lighting load."""
        area_sf = inputs['area_sf']
        lpd = inputs.get('lpd_w_sf', 0.5)  # Default LPD
        hours = inputs.get('hours_per_year', 4380)
        control = inputs.get('control_factor', 0.8)
        diversity = inputs.get('diversity_factor', 0.9)

        connected_kw = area_sf * lpd / 1000
        annual_kwh = connected_kw * hours * control * diversity
        peak_kw = connected_kw * diversity

        return annual_kwh, 0.0, peak_kw

    # ... other calculator methods ...
```

---

## 7. Reporting with Configurable Granularity

```python
class WholeBuildingReport:
    """Generate reports at configurable granularity."""

    def __init__(
        self,
        energy: WholeBuildingEnergy,
        tariff: Tariff,
        mode: ReportMode = ReportMode.FULL
    ):
        self.energy = energy
        self.tariff = tariff
        self.mode = mode

    def generate_summary(self) -> Dict:
        """Generate summary based on report mode."""

        result = {
            'project': self.energy.project.name,
            'mode': self.mode.value
        }

        if self.mode == ReportMode.FULL:
            result['modeled'] = self._format_stream(self.energy.modeled)
            result['site_loads'] = self._format_stream(self.energy.site_loads)
            result['combined'] = self._format_stream(self.energy.combined)

        elif self.mode == ReportMode.SUMMARY:
            result['site_loads'] = self._format_stream(self.energy.site_loads)
            result['combined'] = self._format_stream(self.energy.combined)

        elif self.mode == ReportMode.SIMPLE:
            result['whole_building'] = self._format_stream(self.energy.combined)

        return result

    def generate_tou_analysis(self) -> Dict:
        """Generate TOU analysis using full 8760 hourly data."""

        # Use combined hourly for whole-building TOU
        hourly = self.energy.combined.hourly

        tou_costs = calculate_tou_costs(hourly, self.tariff)

        return {
            'on_peak_kwh': tou_costs['on_peak_kwh'],
            'off_peak_kwh': tou_costs['off_peak_kwh'],
            'on_peak_cost': tou_costs['on_peak_cost'],
            'off_peak_cost': tou_costs['off_peak_cost'],
            'demand_cost': tou_costs['demand_cost'],
            'total_annual_cost': tou_costs['total_cost']
        }

    def _format_stream(self, stream: EnergyStream) -> Dict:
        """Format energy stream for reporting."""
        return {
            'annual_kwh': stream.annual.total_elec_kwh,
            'annual_therms': stream.annual.total_gas_therms,
            'peak_demand_kw': stream.annual.peak_demand_kw,
            'net_kwh': stream.annual.net_elec_kwh
        }
```

---

## 8. Module Structure

```
eco_tools/
├── lcca/
│   ├── whole_building/                  # NEW MODULE
│   │   ├── __init__.py
│   │   ├── schema.py                    # WholeBuildingEnergy, EnergyStream, etc.
│   │   ├── aggregator.py                # Combine modeled + site loads
│   │   └── report.py                    # Configurable reporting
│   │
│   ├── parsers/
│   │   ├── __init__.py
│   │   ├── base.py                      # SimulationParser ABC (NEW)
│   │   ├── hourly_results.py            # CBECC parser (existing)
│   │   ├── cse_hourly.py                # CSE parser (existing)
│   │   └── energyplus.py                # E+ parser (FUTURE - 2026)
│   │
│   ├── site_loads/
│   │   ├── __init__.py
│   │   ├── calculator.py                # Site load calculations
│   │   ├── load_shapes/
│   │   │   ├── __init__.py
│   │   │   ├── library.py               # LoadShapeLibrary
│   │   │   └── profiles/                # Standard profile data
│   │   │       ├── building_hours.json
│   │   │       ├── parking_lighting.json
│   │   │       ├── pool_pump.json
│   │   │       └── flat_24x7.json
│   │   ├── calculators/                 # Per-category calculators
│   │   │   ├── lighting.py
│   │   │   ├── parking.py
│   │   │   ├── pools.py
│   │   │   └── ...
│   │   └── reference_data/
│   │       ├── title24_lpd.json
│   │       └── ...
│   │
│   └── ... (existing LCCA modules)
```

---

## 9. EnergyPlus Integration Path (2026)

### 9.1 Interface Abstraction

The `SimulationParser` abstract base class ensures EnergyPlus integration requires only:
1. Implement `EnergyPlusParser` class
2. Map E+ output to `EnergyStream` format
3. No changes to downstream code

### 9.2 E+ Output Mapping

| EnergyPlus Output | Maps To |
|-------------------|---------|
| `eplusout.sql` Zone/Meter tables | `HourlyRecord` |
| `Zone Electric Equipment Energy` | `plugs_kwh` |
| `Zone Lights Electric Energy` | `lighting_kwh` |
| `Facility Total Electric Demand Power` | `demand_kw` |
| `Zone HVAC System Sensible Heating Energy` | `heating_kwh` |
| `Zone HVAC System Sensible Cooling Energy` | `cooling_kwh` |

### 9.3 ASHRAE 90.1 2019 Considerations

- E+ models may have different end-use categories
- Load shapes may need climate-zone adjustment
- Receptacle schedules differ from T-24 defaults
- Process loads more commonly modeled in E+

---

## 10. Implementation Phases

### Phase 1: Core Schema and Site Load Calculator (Q1)
- Implement `WholeBuildingEnergy` schema
- Implement `SiteLoadCalculator` with 8760 output
- Create standard load shape profiles
- Basic reporting (FULL mode only)

### Phase 2: Configurable Reporting (Q1-Q2)
- Implement `ReportMode` enum
- Add report mode to Excel export
- Add report mode to PDF export

### Phase 3: Load Shape Library Expansion (Q2)
- Add more load shape profiles
- Allow custom profile upload
- Climate-zone adjustments

### Phase 4: EnergyPlus Parser (2026)
- Implement `EnergyPlusParser`
- Map E+ output to unified schema
- Validate with ASHRAE 90.1 2019 models

---

## 11. Benefits of This Architecture

| Benefit | Description |
|---------|-------------|
| **Clean separation** | No messy injection; simulation files remain clean |
| **Engine-agnostic** | Same schema for CBECC and EnergyPlus |
| **Full TOU accuracy** | 8760 hourly profiles enable precise TOU calculations |
| **Audit trail** | Clear distinction between modeled and calculated |
| **Configurable** | Clients choose detail level (full/summary/simple) |
| **Future-proof** | EnergyPlus support is a parser addition, not rewrite |

---

**Last Updated**: December 2024
