# ECM Library Reference

## Overview

The ECM (Energy Conservation Measure) Library provides a centralized, standardized system for defining and analyzing energy efficiency measures. The library is aligned with:

- **OpenStudio BCL** (Building Component Library) - 303 measures across 11 categories
- **CEC CASE Reports** (2025 Title 24) - California cost-effectiveness studies
- **DEER** (Database for Energy Efficient Resources) - California IOU measure data

## Quick Start

```python
from eco_tools.lcca import (
    get_ecm_library,
    ECMCategory,
    ECMSubcategory,
    BuildingType,
    create_pv_ecm,
    create_hpwh_ecm,
)

# Get the library
lib = get_ecm_library()

# List available templates
print(lib.list_templates())  # 37 templates

# Filter by category
hvac_templates = lib.list_by_category(ECMCategory.HVAC)

# Filter by building type
mf_templates = lib.list_for_building_type(BuildingType.MULTIFAMILY_HIGH)

# Search
heat_pump_options = lib.search("heat pump")

# Get template details
template = lib.get_template('hpwh_residential')
print(f"Cost: ${template.default_cost_per_unit}/{template.cost_unit}")
```

---

## Data Model

### ECMCategory Enum

Primary ECM categories aligned with OpenStudio BCL:

| Category | Value | Description |
|----------|-------|-------------|
| `GENERATION` | `"generation"` | PV, wind, CHP |
| `STORAGE` | `"storage"` | Battery, thermal storage |
| `HVAC` | `"hvac"` | Heating, cooling, ventilation |
| `ENVELOPE` | `"envelope"` | Insulation, windows, air sealing |
| `LIGHTING` | `"lighting"` | LED, controls, daylighting |
| `DHW` | `"dhw"` | Domestic hot water |
| `PLUGLOAD` | `"plugload"` | Equipment efficiency |
| `CONTROLS` | `"controls"` | BMS, scheduling, FDD |
| `REFRIGERATION` | `"refrigeration"` | Walk-ins, display cases |
| `OTHER` | `"other"` | Specialty measures |

### ECMSubcategory Enum

Detailed subcategories for precise classification:

#### Generation & Storage
| Subcategory | Value | BCL Reference |
|-------------|-------|---------------|
| `PHOTOVOLTAIC` | `"photovoltaic"` | Onsite Power Gen (3) |
| `BATTERY` | `"battery"` | - |
| `CHP` | `"chp"` | - |
| `WIND` | `"wind"` | - |

#### Envelope (BCL: 88 measures)
| Subcategory | Value | BCL Count |
|-------------|-------|-----------|
| `ENVELOPE_OPAQUE` | `"opaque"` | 41 |
| `ENVELOPE_FENESTRATION` | `"fenestration"` | 12 |
| `ENVELOPE_INFILTRATION` | `"infiltration"` | 8 |
| `ENVELOPE_COOL_ROOF` | `"cool_roof"` | - |
| `ENVELOPE_FORM` | `"form"` | 25 |

#### HVAC (BCL: 69 measures)
| Subcategory | Value | BCL Count |
|-------------|-------|-----------|
| `HVAC_HEATING` | `"heating"` | 8 |
| `HVAC_COOLING` | `"cooling"` | 14 |
| `HVAC_VENTILATION` | `"ventilation"` | 6 |
| `HVAC_DISTRIBUTION` | `"distribution"` | 7 |
| `HVAC_CONTROLS` | `"hvac_controls"` | 5 |
| `HVAC_WHOLE_SYSTEM` | `"whole_system"` | 28 |
| `HVAC_ENERGY_RECOVERY` | `"energy_recovery"` | 1 |

#### DHW (BCL: 6 measures)
| Subcategory | Value |
|-------------|-------|
| `DHW_HEAT_PUMP` | `"dhw_heat_pump"` |
| `DHW_SOLAR` | `"dhw_solar"` |
| `DHW_DISTRIBUTION` | `"dhw_distribution"` |
| `DHW_CONVENTIONAL` | `"dhw_conventional"` |

#### Lighting (BCL: 15 measures)
| Subcategory | Value | BCL Count |
|-------------|-------|-----------|
| `LIGHTING_EQUIPMENT` | `"lighting_equipment"` | 10 |
| `LIGHTING_CONTROLS` | `"lighting_controls"` | 5 |
| `LIGHTING_DAYLIGHTING` | `"daylighting"` | - |

#### Controls
| Subcategory | Value |
|-------------|-------|
| `CONTROLS_BMS` | `"bms"` |
| `CONTROLS_SCHEDULING` | `"scheduling"` |
| `CONTROLS_FDD` | `"fdd"` |
| `CONTROLS_GUIDELINE36` | `"guideline_36"` |

#### Refrigeration
| Subcategory | Value |
|-------------|-------|
| `REFRIG_WALKIN` | `"walkin"` |
| `REFRIG_DISPLAY` | `"display"` |
| `REFRIG_EVAPORATOR` | `"evaporator"` |

### BuildingType Enum

Building types for ECM applicability:

| Type | Value | Description |
|------|-------|-------------|
| `SINGLE_FAMILY` | `"single_family"` | Single-family residential |
| `MULTIFAMILY_LOW` | `"multifamily_low"` | 1-3 stories |
| `MULTIFAMILY_HIGH` | `"multifamily_high"` | 4+ stories |
| `OFFICE_SMALL` | `"office_small"` | Small office |
| `OFFICE_LARGE` | `"office_large"` | Large office |
| `RETAIL` | `"retail"` | Retail/mercantile |
| `WAREHOUSE` | `"warehouse"` | Warehouse/storage |
| `HOTEL` | `"hotel"` | Lodging |
| `RESTAURANT` | `"restaurant"` | Food service |
| `HEALTHCARE` | `"healthcare"` | Healthcare facilities |
| `EDUCATION` | `"education"` | Schools |
| `LABORATORY` | `"laboratory"` | Labs |
| `ALL_RESIDENTIAL` | `"all_residential"` | All residential types |
| `ALL_COMMERCIAL` | `"all_commercial"` | All commercial types |
| `ALL` | `"all"` | Universal applicability |

### CodeBaseline Enum

Code references for savings calculations:

| Baseline | Value |
|----------|-------|
| `T24_2019` | `"T24-2019"` |
| `T24_2022` | `"T24-2022"` |
| `T24_2025` | `"T24-2025"` |
| `ASHRAE_90_1_2016` | `"ASHRAE 90.1-2016"` |
| `ASHRAE_90_1_2019` | `"ASHRAE 90.1-2019"` |
| `ASHRAE_90_1_2022` | `"ASHRAE 90.1-2022"` |
| `IECC_2021` | `"IECC-2021"` |
| `CUSTOM` | `"custom"` |

---

## ECM Dataclass

The `ECM` dataclass defines individual energy conservation measures:

```python
@dataclass
class ECM:
    # Identity
    name: str
    category: ECMCategory = ECMCategory.OTHER
    subcategory: Optional[ECMSubcategory] = None

    # Costs
    capex: float = 0.0                    # Capital cost ($)
    opex_annual: float = 0.0              # Annual operating cost change
    maintenance_annual: float = 0.0        # Annual maintenance cost change

    # Electricity Impacts
    annual_kwh_delta: float = 0.0         # Absolute change (negative = savings)
    annual_kwh_pct: float = 0.0           # Percentage change (e.g., -0.20)
    annual_kwh_generation: float = 0.0    # Generation (PV, CHP)

    # Gas Impacts
    annual_therm_delta: float = 0.0       # Absolute change
    annual_therm_pct: float = 0.0         # Percentage change

    # Demand Impacts
    demand_kw_delta: float = 0.0          # Change in peak demand (kW)

    # Incentives
    incentives: List[Dict[str, Any]]      # List of incentive dicts

    # Applicability
    applicable_building_types: List[BuildingType]  # Default: [ALL]
    climate_zones: List[int]              # CA climate zones 1-16

    # Code Compliance
    code_baseline: Optional[CodeBaseline] = None
    compliance_credit: Optional[str] = None

    # Uncertainty (for sensitivity analysis)
    capex_range: Optional[Tuple[float, float]] = None   # (low, high)
    savings_range: Optional[Tuple[float, float]] = None # (low_pct, high_pct)

    # Data Provenance
    source: Optional[str] = None          # Data source reference
    bcl_uid: Optional[str] = None         # OpenStudio BCL UUID
    vintage: Optional[int] = None         # Year of cost data

    # Metadata
    description: str = ""
    useful_life_years: int = 20
    notes: str = ""
```

### ECM Properties

| Property | Description |
|----------|-------------|
| `net_capex` | Capital cost minus upfront incentives |
| `total_incentives` | Sum of all incentives |

### ECM Methods

| Method | Description |
|--------|-------------|
| `get_kwh_impact(baseline_kwh)` | Calculate total kWh impact including percentage |
| `get_therm_impact(baseline_therms)` | Calculate total therm impact |

---

## ECMLibrary Class

The `ECMLibrary` class provides centralized template management:

### Initialization

```python
from eco_tools.lcca import ECMLibrary, get_ecm_library

# Create new instance
lib = ECMLibrary()

# Or use global singleton
lib = get_ecm_library()
```

### Listing Methods

| Method | Description |
|--------|-------------|
| `list_templates()` | List all template IDs |
| `list_by_category(category)` | Filter by ECMCategory |
| `list_by_subcategory(subcategory)` | Filter by ECMSubcategory |
| `list_for_building_type(building_type)` | Filter by BuildingType |
| `list_for_climate_zone(cz)` | Filter by CA climate zone (1-16) |
| `search(query)` | Full-text search |
| `get_category_summary()` | Count by category |

### Template Access

| Method | Description |
|--------|-------------|
| `get_template(template_id)` | Get ECMTemplate by ID |

### JSON Import/Export

```python
from pathlib import Path

# Export all templates
lib.export_to_json(Path("my_templates.json"))

# Load custom templates
lib.load_from_json(Path("custom_ecms.json"))
```

---

## Available Templates (37 Total)

### Generation (2 templates)

| Template ID | Name | Cost Unit | Default Cost | Life |
|-------------|------|-----------|--------------|------|
| `pv_rooftop` | Rooftop PV | $/watt | $2.50 | 25 yr |
| `pv_carport` | Carport PV | $/watt | $3.50 | 25 yr |

### Storage (1 template)

| Template ID | Name | Cost Unit | Default Cost | Life |
|-------------|------|-----------|--------------|------|
| `battery_storage` | Battery Storage | $/kWh | $500 | 15 yr |

### Envelope (6 templates)

| Template ID | Name | Cost Unit | Default Cost | Savings |
|-------------|------|-----------|--------------|---------|
| `wall_insulation_upgrade` | Wall Insulation | $/sqft | $2.50 | 8% |
| `roof_insulation_upgrade` | Roof Insulation | $/sqft | $1.80 | 12% |
| `cool_roof` | Cool Roof | $/sqft | $0.50 | 10% |
| `window_upgrade_double` | Double-Pane Low-E | $/sqft | $45 | 10% |
| `window_upgrade_triple` | Triple-Pane | $/sqft | $75 | 15% |
| `air_sealing` | Air Sealing | $/sqft | $0.75 | 8% |

### HVAC (15 templates)

| Template ID | Subcategory | Cost Unit | Default Cost |
|-------------|-------------|-----------|--------------|
| `ashp_ducted` | Heating | $/ton | $4,000 |
| `minisplit` | Heating | $/ton | $3,500 |
| `gshp` | Heating | $/ton | $8,000 |
| `high_eff_chiller` | Cooling | $/ton | $800 |
| `evap_cooling` | Cooling | $/cfm | $3.00 |
| `erv_residential` | Energy Recovery | $/each | $1,200 |
| `erv_commercial` | Energy Recovery | $/cfm | $5.00 |
| `doas` | Ventilation | $/cfm | $8.00 |
| `dcv` | Ventilation | $/sqft | $1.50 |
| `duct_sealing` | Distribution | $/sqft | $0.80 |
| `vav_conversion` | Distribution | $/cfm | $4.00 |
| `economizer` | Controls | $/cfm | $2.00 |
| `setpoint_reset` | Controls | $/sqft | $0.50 |
| `vrf` | Whole System | $/ton | $5,000 |
| `central_vent_supply` | Whole System | $/each | $500 |

### DHW (4 templates)

| Template ID | Name | Cost Unit | Default Cost | Savings |
|-------------|------|-----------|--------------|---------|
| `hpwh_residential` | Residential HPWH | $/each | $2,500 | 65% |
| `hpwh_central` | Central HPWH | $/gallon | $200 | 60% |
| `pipe_insulation` | DHW Pipe Insulation | $/linear ft | $3.00 | 8% |
| `solar_thermal` | Solar Thermal DHW | $/sqft | $100 | 50% |

### Lighting (4 templates)

| Template ID | Name | Cost Unit | Default Cost | Savings |
|-------------|------|-----------|--------------|---------|
| `led_interior` | LED Interior | $/sqft | $3.00 | 40% |
| `led_exterior` | LED Exterior | $/fixture | $500 | 50% |
| `occupancy_sensors` | Occupancy Sensors | $/sqft | $1.50 | 20% |
| `daylight_dimming` | Daylight Dimming | $/sqft | $2.00 | 25% |

### Controls (3 templates)

| Template ID | Name | Cost Unit | Default Cost | Savings |
|-------------|------|-----------|--------------|---------|
| `ems_bms` | Energy Management System | $/sqft | $0.75 | 10% |
| `guideline_36` | ASHRAE Guideline 36 | $/sqft | $1.00 | 15% |
| `fdd` | Fault Detection | $/sqft | $0.50 | 8% |

### Refrigeration (2 templates)

| Template ID | Name | Cost Unit | Default Cost | Savings |
|-------------|------|-----------|--------------|---------|
| `walkin_ec_motors` | Walk-in EC Motors | $/motor | $400 | 30% |
| `display_case_led` | Display Case LED | $/linear ft | $150 | 50% |

---

## Template Factory Functions

Pre-built functions for common ECM types:

### PV System

```python
from eco_tools.lcca import create_pv_ecm

pv = create_pv_ecm(
    capacity_kw=100,
    cost_per_watt=2.50,
    annual_kwh_per_kw=1500,  # CA average
    itc_pct=0.30,            # 30% ITC
)
# Returns ECM with $250,000 capex, 150,000 kWh generation, $75,000 ITC incentive
```

### Heat Pump Water Heater

```python
from eco_tools.lcca import create_hpwh_ecm

hpwh = create_hpwh_ecm(
    unit_count=54,
    uef=3.5,
    baseline_uef=0.92,           # Gas baseline
    annual_hot_water_therms=200, # Per unit
    cost_per_unit=2500,
)
# Returns ECM with gas elimination and electric consumption increase
```

### ERV System

```python
from eco_tools.lcca import create_erv_ecm

erv = create_erv_ecm(
    unit_count=54,
    cfm_per_unit=35,
    cost_per_unit=1200,
    fan_kwh_per_unit=80,
)
# Returns ECM with fan energy penalty (annual_kwh_delta > 0)
```

### Central Ventilation (Maestro-type)

```python
from eco_tools.lcca import create_central_vent_ecm

vent = create_central_vent_ecm(
    unit_count=54,
    total_cfm=2000,
    cost_per_unit=500,
    central_fan_kw=0.5,
)
```

### Mini-Split Heat Pump

```python
from eco_tools.lcca import create_minisplit_ecm

ms = create_minisplit_ecm(
    unit_count=54,
    tons_per_unit=1.5,
    seer=20,
    hspf=10,
    cost_per_ton=3500,
    baseline_seer=15,
    baseline_hspf=8.5,
)
# Returns ECM with calculated kWh savings vs baseline
```

### Electrification

```python
from eco_tools.lcca import create_electrification_ecm

elec = create_electrification_ecm(
    name="HVAC Electrification",
    capex=500000,
    annual_kwh_increase=50000,      # Added electric
    annual_therm_reduction=46000,   # Eliminated gas
)
```

### CUAC Comparison ECM

```python
from eco_tools.lcca import create_ecm_from_cuac_comparison

ecm = create_ecm_from_cuac_comparison(
    baseline_name="Maestro",
    proposed_name="Ephoca ERV",
    baseline_kwh=272512,
    proposed_kwh=280094,
    capex=25000,
)
# Creates ECM representing delta between CUAC scenarios
```

---

## ECMBundle Class

Group and analyze multiple ECMs together:

```python
from eco_tools.lcca import ECMBundle, create_pv_ecm, create_hpwh_ecm

bundle = ECMBundle(name="Gibraltar ECMs")

# Add ECMs
bundle.add_ecm(create_pv_ecm(343))
bundle.add_ecm(create_hpwh_ecm(120))

# Properties
print(f"Total CapEx: ${bundle.total_capex:,.0f}")
print(f"Net CapEx: ${bundle.total_net_capex:,.0f}")
print(f"Total Incentives: ${bundle.total_incentives:,.0f}")

# Filter by category
hvac_ecms = bundle.get_ecms_by_category(ECMCategory.HVAC)

# Create subsets
pv_only = bundle.create_subset(["343 kW PV"])
no_pv = bundle.create_excluding(["343 kW PV"])

# Summary table
print(bundle.summary_table())
```

---

## Climate Zone Applicability

California climate zones for ECM filtering:

| Zone | Representative City | Climate Type |
|------|---------------------|--------------|
| 1 | Arcata | Marine, Cool |
| 2 | Santa Rosa | Marine, Mild |
| 3 | Oakland | Marine, Mild |
| 4 | San Jose | Marine, Mild |
| 5 | Santa Maria | Marine, Cool |
| 6 | Los Angeles (Coast) | Marine, Warm |
| 7 | San Diego | Marine, Mild |
| 8 | Fullerton | Marine, Hot |
| 9 | Burbank | Marine, Hot |
| 10 | Riverside | Hot-Dry |
| 11 | Red Bluff | Hot-Dry |
| 12 | Sacramento | Hot-Dry |
| 13 | Fresno | Hot-Dry |
| 14 | Palmdale | Hot-Dry, Cold Winter |
| 15 | Palm Springs | Hot-Dry, Desert |
| 16 | Mount Shasta | Cold, Mountain |

### Climate-Specific Recommendations

```python
lib = get_ecm_library()

# Hot-dry climate (CZ 13 - Fresno)
cz13_templates = lib.list_for_climate_zone(13)
# Includes: evap_cooling, cool_roof, dcv

# Cold climate (CZ 16 - Mountain)
cz16_templates = lib.list_for_climate_zone(16)
# Includes: triple-pane windows, high insulation
```

---

## Data Sources

| Source | Description | Templates |
|--------|-------------|-----------|
| NREL ATB 2024 | Annual Technology Baseline | PV, Battery |
| CEC CASE 2025 | Title 24 cost-effectiveness | HVAC, DHW, Envelope |
| DEER 2024 | Database for Energy Efficient Resources | Lighting, Envelope |
| RSMeans 2024 | Construction cost data | Envelope, General |
| ASHRAE 90.1-2022 | Commercial building standard | HVAC, Controls |
| ASHRAE Guideline 36 | HVAC control sequences | Controls |

---

## JSON Configuration Format

Custom ECM templates can be loaded from JSON:

```json
{
  "custom_heat_pump": {
    "name_template": "Custom HP ({capacity} tons)",
    "category": "hvac",
    "subcategory": "heating",
    "description": "Custom heat pump measure",
    "default_cost_per_unit": 5000,
    "cost_unit": "ton",
    "default_savings_pct": 0.35,
    "useful_life_years": 15,
    "source": "Project Data",
    "vintage": 2024
  }
}
```

---

## Integration with LCCA

ECMs integrate with the full LCCA workflow:

```python
from eco_tools.lcca import (
    get_ecm_library,
    ECMBundle,
    run_tou_lcca,
    TouLccaScenario,
    analyze_ecm_marginal_value,
)

# Build ECM bundle
lib = get_ecm_library()
bundle = ECMBundle("Project ECMs")
bundle.add_ecm(create_pv_ecm(100))
bundle.add_ecm(create_hpwh_ecm(54))

# Use with TOU LCCA scenarios
baseline = TouLccaScenario(...)
proposed = TouLccaScenario(
    capex=bundle.total_capex,
    ...
)

results = run_tou_lcca(baseline, proposed)
print(f"NPV: ${results.npv:,.0f}")
print(f"IRR: {results.irr*100:.1f}%")
```

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | Dec 2024 | Initial ECM library with 37 templates |

## References

- [OpenStudio BCL](https://bcl.nrel.gov/browse)
- [CEC 2025 CASE Reports](https://title24stakeholders.com/2025-cycle-case-reports/)
- [DEER Database](https://deeresources.com/)
- [NREL Annual Technology Baseline](https://atb.nrel.gov/)
- [ASHRAE Guideline 36](https://www.ashrae.org/technical-resources/guideline-36)
