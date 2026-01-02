# Site Load Data Collection Sheet Specification

**Version:** 1.0
**Date:** December 2024
**Purpose:** Define the data collection format for non-modeled site energy loads for upload to Streamlit GUI

---

## 1. Overview

This document specifies the data collection sheet format for capturing non-modeled site energy loads. The sheet is designed for:
- Excel upload to Streamlit GUI
- JSON export/import
- Integration with the LCCA workflow

---

## 2. Complete Load Categories

Based on research including [ASHRAE 90.1](https://www.ashrae.org/technical-resources/bookstore/standard-90-1), [DOE Better Buildings](https://betterbuildingssolutioncenter.energy.gov/plug-process-loads), [LEED requirements](https://leeduser.buildinggreen.com/credit/NC-v4/EAp2), and [EIA CBECS](https://www.eia.gov/consumption/commercial/), the following categories represent a comprehensive set of non-modeled site loads:

### 2.1 Categories from Existing Excel (Validated)

| Category | Sub-Categories | Source Standard |
|----------|----------------|-----------------|
| Interior Lighting | Corridors, Stairs, Lobbies, Offices, Restrooms, Kitchens, Laundry, Mechanical, Storage, Fitness, Conference, Leasing, Mail, Trash | Title 24 2022 Table 140.6-C |
| Parking Garage | Lighting, Mechanical Ventilation | NRCC-LTO, ASHRAE 62.1 |
| Site Lighting | Hardscape, Parking Lot, Pathways | NRCC-LTO |
| Pool/Spa | Pump, Heater (Gas/Electric/Heat Pump) | ENERGY STAR, DOE |
| EV Chargers | Level 2 Ports | Usage assumptions |
| Elevators | Hydraulic, Traction, MRL | VDI 4707, ENERGY STAR |
| Water Pumps | Fire Pump, Booster Pump, HW Circulator | Equipment specs |

### 2.2 Additional Categories Identified (New)

| Category | Sub-Categories | Source/Rationale |
|----------|----------------|------------------|
| Trash Compactor | Self-contained, Stationary | [WM SmartEnergy](https://www.wm.com/us/en/business/business-waste-compactors) |
| IT/Telecom Room | Server closet, Network equipment | [DOE Server Rooms](https://www.osti.gov/biblio/1172953) - can be 50%+ of building energy |
| Security Systems | Cameras, Access Control, Monitoring | 24/7 operation |
| Fire/Life Safety | Alarm Panel, Devices, Emergency Lighting | 24/7 standby power |
| Commercial Kitchen | Refrigeration, Cooking, Dishwashing | [DOE Commercial Kitchens](https://buildingenergyscore.energy.gov/resources/download?key=publications/Final_ASHRAE_PNNL_CommercialKitchen.pdf) |
| Common Laundry | Commercial Washers, Dryers | Per machine energy |
| Irrigation | Landscape Pumps, Controllers | Seasonal operation |
| Exhaust Systems | Garage Exhaust, Trash Room, Kitchen Hood | Continuous/intermittent |
| Vending/Ice | Vending Machines, Ice Makers | 24/7 operation |
| Escalators | Moving walkways | If present |
| Snowmelt | Heated driveways/walkways | Cold climates only |
| Signage | Exterior building signage | 24/7 or dusk-to-dawn |

---

## 3. Data Collection Sheet Structure

### 3.1 Sheet 1: Project Information

| Field | Type | Required | Description | Example |
|-------|------|----------|-------------|---------|
| project_name | text | Yes | Project identifier | "Modera Neptune" |
| project_address | text | No | Street address | "123 Main St" |
| city | text | No | City | "San Jose" |
| climate_zone | integer | Yes | CA Climate Zone (1-16) or ASHRAE Zone | 4 |
| building_type | dropdown | Yes | Multifamily, Office, Retail, Mixed-Use | "Multifamily" |
| total_units | integer | Conditional | Dwelling units (if multifamily) | 359 |
| total_building_sf | number | Yes | Gross building area (SF) | 425000 |
| floors_above_grade | integer | No | Number of stories | 5 |
| floors_below_grade | integer | No | Basement levels | 1 |
| year_built | integer | No | Construction year | 2025 |

### 3.2 Sheet 2: Utility Rates

| Field | Type | Required | Description | Example |
|-------|------|----------|-------------|---------|
| utility_electric | text | No | Electric utility name | "PG&E" |
| utility_gas | text | No | Gas utility name | "PG&E" |
| rate_schedule | text | No | Rate schedule name | "B-20" |
| elec_rate_kwh | number | Yes | Average electric rate ($/kWh) | 0.22 |
| gas_rate_therm | number | Yes | Gas rate ($/therm) | 1.85 |
| demand_rate_kw | number | No | Demand charge ($/kW/month) | 15.00 |
| fixed_charge_month | number | No | Monthly fixed charge ($) | 50.00 |
| billing_months | integer | No | Billing periods per year | 12 |

### 3.3 Sheet 3: Interior Lighting - Common Areas

| Field | Type | Required | Units | Description |
|-------|------|----------|-------|-------------|
| space_type | dropdown | Yes | - | Space type from Title 24 list |
| area_sf | number | Yes | SF | Floor area |
| lpd_override | number | No | W/SF | Override default LPD |
| hours_per_year | number | No | hrs/yr | Operating hours (default by type) |
| control_factor | number | No | 0-1 | Lighting control savings (default 0.8) |
| diversity_factor | number | No | 0-1 | Simultaneous use factor (default 0.9) |
| notes | text | No | - | Additional notes |

**Space Type Options (Title 24 2022):**
```
corridor (0.40 W/SF, 4380 hrs)
stairwell (0.49 W/SF, 4380 hrs)
lobby (0.65 W/SF, 4380 hrs)
office (0.65 W/SF, 2600 hrs)
restroom (0.63 W/SF, 2600 hrs)
kitchen_common (0.95 W/SF, 2600 hrs)
laundry_common (0.53 W/SF, 2600 hrs)
mechanical (0.43 W/SF, 1000 hrs)
storage (0.42 W/SF, 1000 hrs)
fitness (0.72 W/SF, 4380 hrs)
conference (0.80 W/SF, 2600 hrs)
leasing_office (0.65 W/SF, 2600 hrs)
mail_room (0.53 W/SF, 2600 hrs)
trash_room (0.42 W/SF, 1000 hrs)
```

### 3.4 Sheet 4: Parking

| Field | Type | Required | Units | Description |
|-------|------|----------|-------|-------------|
| parking_type | dropdown | Yes | - | Surface, Garage, Underground |
| area_sf | number | Yes | SF | Parking area |
| lighting_lpd | number | No | W/SF | Lighting power density (default 0.30) |
| lighting_hours | number | No | hrs/yr | Operating hours (default 4380) |
| has_ventilation | boolean | No | - | Mechanical ventilation? |
| vent_cfm_sf | number | No | CFM/SF | Ventilation rate (default 0.75) |
| vent_hours | number | No | hrs/yr | Ventilation hours (default 8760) |
| num_ev_chargers | integer | No | - | EV charging ports |
| ev_kw_per_port | number | No | kW | Charger power (default 7.2) |
| ev_hours_per_day | number | No | hrs | Average charge time (default 6) |

### 3.5 Sheet 5: Site/Exterior Lighting

| Field | Type | Required | Units | Description |
|-------|------|----------|-------|-------------|
| area_type | dropdown | Yes | - | Hardscape, Parking, Pathway, Building Facade |
| area_sf | number | Yes | SF | Area served |
| lpd_override | number | No | W/SF | Override NRCC-LTO allowance |
| hours_per_year | number | No | hrs/yr | Operating hours (default 4380 dusk-dawn) |
| control_type | dropdown | No | - | Photocell, Timer, Motion, None |
| control_factor | number | No | 0-1 | Control savings factor |

### 3.6 Sheet 6: Pool & Spa

| Field | Type | Required | Units | Description |
|-------|------|----------|-------|-------------|
| pool_name | text | Yes | - | Pool identifier |
| pool_type | dropdown | Yes | - | Pool, Spa, Combined |
| surface_area_sf | number | Yes | SF | Water surface area |
| pump_hp | number | Yes | HP | Pump motor horsepower |
| pump_type | dropdown | Yes | - | Single-speed, Two-speed, Variable-speed |
| pump_hours_day | number | No | hrs | Daily pump operation |
| has_cover | boolean | No | - | Pool cover installed? |
| heater_type | dropdown | No | - | None, Gas, Electric, Heat Pump |
| heater_efficiency | number | No | % | Heater efficiency (default by type) |
| setpoint_f | number | No | °F | Temperature setpoint (default 78) |
| months_operated | integer | No | - | Months per year (default 12) |

### 3.7 Sheet 7: Vertical Transportation

| Field | Type | Required | Units | Description |
|-------|------|----------|-------|-------------|
| equipment_type | dropdown | Yes | - | Elevator, Escalator |
| quantity | integer | Yes | - | Number of units |
| elevator_type | dropdown | Conditional | - | Hydraulic, Traction-Geared, Traction-Gearless, MRL |
| capacity_lbs | number | No | lbs | Elevator capacity |
| floors_served | integer | No | - | Number of floors |
| usage_factor | dropdown | No | - | Low, Medium, High |
| annual_kwh_override | number | No | kWh/yr | Override default calculation |

**Default Annual kWh by Type:**
```
hydraulic_small: 6,000 kWh/yr
hydraulic_standard: 8,000 kWh/yr
traction_geared: 10,000 kWh/yr
traction_gearless: 7,500 kWh/yr
machine_room_less: 5,500 kWh/yr
escalator: 15,000 kWh/yr
```

### 3.8 Sheet 8: Water Pumps

| Field | Type | Required | Units | Description |
|-------|------|----------|-------|-------------|
| pump_type | dropdown | Yes | - | Fire, Booster, HW_Circulator, Irrigation, Sump |
| quantity | integer | Yes | - | Number of pumps |
| hp | number | Yes | HP | Motor horsepower |
| efficiency | number | No | % | Motor efficiency (default 85%) |
| hours_per_day | number | Yes | hrs | Daily operation hours |
| days_per_year | number | No | days | Annual operation days (default 365) |
| notes | text | No | - | Additional notes |

**Typical Values:**
```
fire_pump: 55 HP, 1 hr/day, 12 days/yr (testing only)
booster_pump: 3 HP, 24 hrs/day, 365 days/yr
hw_circulator: 0.5 HP, 24 hrs/day, 365 days/yr
irrigation: 2 HP, 4 hrs/day, 180 days/yr (seasonal)
sump_pump: 1 HP, 2 hrs/day, 365 days/yr
```

### 3.9 Sheet 9: IT/Telecom (NEW)

| Field | Type | Required | Units | Description |
|-------|------|----------|-------|-------------|
| room_name | text | Yes | - | Room identifier |
| room_type | dropdown | Yes | - | IT_Closet, Server_Room, Telecom |
| area_sf | number | No | SF | Room area |
| num_racks | integer | No | - | Number of server racks |
| kw_per_rack | number | No | kW | Power per rack (default 3.5) |
| total_it_kw | number | No | kW | Total IT load (alternative input) |
| pue | number | No | - | Power Usage Effectiveness (default 2.0) |
| hours_per_year | number | No | hrs | Operating hours (default 8760) |

**Note:** Per [DOE guidance](https://www.osti.gov/biblio/1172953), IT closets with 5-50 servers can account for over 50% of building energy.

### 3.10 Sheet 10: Trash Handling (NEW)

| Field | Type | Required | Units | Description |
|-------|------|----------|-------|-------------|
| equipment_type | dropdown | Yes | - | Compactor, Chute, Recycling_Baler |
| quantity | integer | Yes | - | Number of units |
| hp | number | No | HP | Motor HP (default 10 for compactor) |
| cycles_per_day | number | No | - | Compaction cycles (default 10) |
| cycle_minutes | number | No | min | Minutes per cycle (default 2) |
| days_per_year | number | No | days | Operating days (default 365) |

### 3.11 Sheet 11: Commercial Kitchen (NEW)

| Field | Type | Required | Units | Description |
|-------|------|----------|-------|-------------|
| kitchen_type | dropdown | Yes | - | Community_Kitchen, Cafe, Full_Service |
| area_sf | number | Yes | SF | Kitchen area |
| refrigeration_kw | number | No | kW | Refrigeration load |
| cooking_gas_therms_day | number | No | therms | Daily gas cooking |
| cooking_electric_kw | number | No | kW | Electric cooking load |
| dishwasher_kw | number | No | kW | Dishwasher load |
| hood_exhaust_hp | number | No | HP | Kitchen hood exhaust |
| hours_per_day | number | No | hrs | Daily operation |
| days_per_year | number | No | days | Annual operation days |

### 3.12 Sheet 12: Common Laundry (NEW)

| Field | Type | Required | Units | Description |
|-------|------|----------|-------|-------------|
| washer_quantity | integer | Yes | - | Number of washers |
| washer_type | dropdown | No | - | Standard, High_Efficiency |
| washer_kwh_cycle | number | No | kWh | Energy per wash cycle (default 2.0) |
| dryer_quantity | integer | Yes | - | Number of dryers |
| dryer_type | dropdown | No | - | Electric, Gas |
| dryer_kwh_cycle | number | No | kWh | Electric dryer per cycle (default 3.0) |
| dryer_therms_cycle | number | No | therms | Gas dryer per cycle (default 0.2) |
| cycles_per_day | number | No | - | Average cycles per machine per day |

### 3.13 Sheet 13: Security & Life Safety (NEW)

| Field | Type | Required | Units | Description |
|-------|------|----------|-------|-------------|
| system_type | dropdown | Yes | - | Security_Cameras, Access_Control, Fire_Alarm, Emergency_Lighting |
| quantity | integer | No | - | Number of devices/zones |
| total_kw | number | No | kW | Total system power draw |
| hours_per_year | number | No | hrs | Operating hours (default 8760 for 24/7) |

### 3.14 Sheet 14: Miscellaneous Loads (NEW)

| Field | Type | Required | Units | Description |
|-------|------|----------|-------|-------------|
| load_name | text | Yes | - | Load description |
| load_category | dropdown | Yes | - | Vending, Ice_Maker, Signage, Exhaust_Fan, Snowmelt, Other |
| quantity | integer | Yes | - | Number of units |
| kw_per_unit | number | Yes | kW | Power per unit |
| hours_per_year | number | Yes | hrs | Annual operating hours |
| gas_therms_year | number | No | therms | Annual gas (if applicable) |

**Typical Values:**
```
vending_machine: 0.4 kW, 8760 hrs/yr
ice_maker: 0.8 kW, 8760 hrs/yr
exterior_signage: 0.5 kW, 4380 hrs/yr (dusk-dawn)
exhaust_fan: 0.5 HP, 8760 hrs/yr
snowmelt_electric: 30 W/SF, seasonal
```

---

## 4. Calculation Summary Sheet (Auto-Generated)

This sheet is populated automatically after upload and calculation:

| Field | Description |
|-------|-------------|
| **Category Totals** | |
| interior_lighting_kwh | Total interior lighting energy |
| parking_kwh | Total parking (lighting + vent + EV) |
| site_lighting_kwh | Total exterior/site lighting |
| pool_kwh | Total pool pump energy |
| pool_therms | Total pool heater gas |
| elevators_kwh | Total vertical transportation |
| pumps_kwh | Total water pump energy |
| it_telecom_kwh | Total IT/telecom energy |
| trash_kwh | Total trash handling energy |
| kitchen_kwh | Total kitchen electric |
| kitchen_therms | Total kitchen gas |
| laundry_kwh | Total laundry electric |
| laundry_therms | Total laundry gas (if gas dryers) |
| security_kwh | Total security/life safety |
| misc_kwh | Total miscellaneous loads |
| misc_therms | Total miscellaneous gas |
| **Grand Totals** | |
| total_annual_kwh | Sum of all electric loads |
| total_annual_therms | Sum of all gas loads |
| total_peak_kw | Estimated coincident peak demand |
| **Cost Estimates** | |
| annual_electric_cost | total_kwh × rate |
| annual_gas_cost | total_therms × rate |
| annual_demand_cost | peak_kw × demand_rate × 12 |
| total_annual_cost | Sum of all costs |

---

## 5. JSON Schema for Programmatic Input

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "SiteLoadInput",
  "type": "object",
  "required": ["project_info", "utility_rates"],
  "properties": {
    "project_info": {
      "type": "object",
      "required": ["project_name", "climate_zone", "building_type", "total_building_sf"],
      "properties": {
        "project_name": {"type": "string"},
        "climate_zone": {"type": "integer", "minimum": 1, "maximum": 16},
        "building_type": {"type": "string", "enum": ["Multifamily", "Office", "Retail", "Mixed-Use", "Hospitality", "Industrial"]},
        "total_building_sf": {"type": "number", "minimum": 0},
        "total_units": {"type": "integer", "minimum": 0}
      }
    },
    "utility_rates": {
      "type": "object",
      "required": ["elec_rate_kwh", "gas_rate_therm"],
      "properties": {
        "elec_rate_kwh": {"type": "number", "minimum": 0},
        "gas_rate_therm": {"type": "number", "minimum": 0},
        "demand_rate_kw": {"type": "number", "minimum": 0}
      }
    },
    "interior_lighting": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["space_type", "area_sf"],
        "properties": {
          "space_type": {"type": "string"},
          "area_sf": {"type": "number", "minimum": 0},
          "lpd_override": {"type": "number", "minimum": 0},
          "hours_per_year": {"type": "number", "minimum": 0},
          "control_factor": {"type": "number", "minimum": 0, "maximum": 1},
          "diversity_factor": {"type": "number", "minimum": 0, "maximum": 1}
        }
      }
    },
    "parking": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["parking_type", "area_sf"],
        "properties": {
          "parking_type": {"type": "string", "enum": ["Surface", "Garage", "Underground"]},
          "area_sf": {"type": "number"},
          "has_ventilation": {"type": "boolean"},
          "num_ev_chargers": {"type": "integer"}
        }
      }
    },
    "pools": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["pool_type", "surface_area_sf", "pump_hp", "pump_type"],
        "properties": {
          "pool_type": {"type": "string", "enum": ["Pool", "Spa", "Combined"]},
          "surface_area_sf": {"type": "number"},
          "pump_hp": {"type": "number"},
          "pump_type": {"type": "string", "enum": ["Single-speed", "Two-speed", "Variable-speed"]},
          "heater_type": {"type": "string", "enum": ["None", "Gas", "Electric", "Heat_Pump"]}
        }
      }
    },
    "elevators": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["equipment_type", "quantity"],
        "properties": {
          "equipment_type": {"type": "string", "enum": ["Elevator", "Escalator"]},
          "quantity": {"type": "integer"},
          "elevator_type": {"type": "string"}
        }
      }
    },
    "pumps": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["pump_type", "quantity", "hp", "hours_per_day"],
        "properties": {
          "pump_type": {"type": "string"},
          "quantity": {"type": "integer"},
          "hp": {"type": "number"},
          "hours_per_day": {"type": "number"}
        }
      }
    },
    "it_telecom": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["room_type"],
        "properties": {
          "room_type": {"type": "string"},
          "num_racks": {"type": "integer"},
          "kw_per_rack": {"type": "number"},
          "total_it_kw": {"type": "number"}
        }
      }
    },
    "trash_handling": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["equipment_type", "quantity"],
        "properties": {
          "equipment_type": {"type": "string"},
          "quantity": {"type": "integer"},
          "hp": {"type": "number"}
        }
      }
    },
    "kitchen": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["kitchen_type", "area_sf"],
        "properties": {
          "kitchen_type": {"type": "string"},
          "area_sf": {"type": "number"}
        }
      }
    },
    "laundry": {
      "type": "object",
      "properties": {
        "washer_quantity": {"type": "integer"},
        "dryer_quantity": {"type": "integer"},
        "dryer_type": {"type": "string", "enum": ["Electric", "Gas"]}
      }
    },
    "security_life_safety": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["system_type"],
        "properties": {
          "system_type": {"type": "string"},
          "total_kw": {"type": "number"}
        }
      }
    },
    "misc_loads": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["load_name", "load_category", "quantity", "kw_per_unit", "hours_per_year"],
        "properties": {
          "load_name": {"type": "string"},
          "load_category": {"type": "string"},
          "quantity": {"type": "integer"},
          "kw_per_unit": {"type": "number"},
          "hours_per_year": {"type": "number"}
        }
      }
    }
  }
}
```

---

## 6. Streamlit Upload Workflow

### 6.1 User Flow

```
1. User downloads blank Excel template from GUI
2. User fills in project info, utility rates, and applicable load sections
3. User uploads completed Excel to Streamlit
4. System validates input data
5. System calculates all site loads
6. System displays summary with breakdown by category
7. User can adjust inputs and recalculate
8. User exports results (Excel, JSON, or integrates with LCCA)
```

### 6.2 Validation Rules

| Rule | Error Message |
|------|---------------|
| project_name required | "Project name is required" |
| climate_zone 1-16 | "Climate zone must be between 1 and 16" |
| elec_rate > 0 | "Electric rate must be positive" |
| area_sf >= 0 | "Area cannot be negative" |
| control_factor 0-1 | "Control factor must be between 0 and 1" |
| pump_hp > 0 | "Pump HP must be positive" |

### 6.3 GUI Components

```python
# Streamlit page structure
st.title("Site Load Calculator")

# File upload
uploaded_file = st.file_uploader("Upload Site Load Data", type=['xlsx', 'json'])

# Or manual entry tabs
tab1, tab2, tab3 = st.tabs(["Project Info", "Load Entry", "Results"])

with tab1:
    st.text_input("Project Name")
    st.selectbox("Building Type", ["Multifamily", "Office", ...])
    st.number_input("Climate Zone", 1, 16)

with tab2:
    # Expandable sections for each load category
    with st.expander("Interior Lighting"):
        # Dynamic table for space entries

with tab3:
    # Results summary
    st.metric("Total Annual kWh", f"{total_kwh:,.0f}")
    st.metric("Total Annual Cost", f"${total_cost:,.0f}")

    # Category breakdown chart
    fig = px.pie(df, values='kwh', names='category')
    st.plotly_chart(fig)

    # Export buttons
    st.download_button("Download Excel", excel_bytes)
    st.download_button("Download JSON", json_bytes)
```

---

## 7. Excel Template Structure

### Workbook Sheets

1. **Instructions** - How to use the template
2. **Project_Info** - Project and utility rate data
3. **Interior_Lighting** - Common area lighting entries
4. **Parking** - Parking and EV charging
5. **Site_Lighting** - Exterior lighting
6. **Pool_Spa** - Pool and spa systems
7. **Elevators** - Vertical transportation
8. **Pumps** - Water system pumps
9. **IT_Telecom** - Server rooms and IT closets
10. **Trash** - Trash compactors and handling
11. **Kitchen** - Commercial kitchen equipment
12. **Laundry** - Common laundry facilities
13. **Security** - Security and life safety
14. **Misc** - Other miscellaneous loads
15. **Reference_Data** (hidden) - LPD tables, defaults
16. **Summary** (protected) - Auto-calculated results

### Data Validation

- Dropdown lists for all categorical fields
- Range validation for numeric inputs
- Conditional formatting for errors
- Named ranges for programmatic access

---

## 8. Integration with LCCA Workflow

```python
# Import site loads from Excel
from eco_tools.lcca.site_loads import import_site_loads_excel

site_profile = import_site_loads_excel("project_site_loads.xlsx")

# Combine with CBECC simulation
from eco_tools.lcca.parsers import parse_hourly_results
from eco_tools.lcca.site_loads import WholeBuildingEnergy

sim = parse_hourly_results("project_hourly_results.csv")

whole_building = WholeBuildingEnergy(
    project_name=sim.project_name,
    modeled_annual_kwh=sim.annual.total_elec_kwh,
    modeled_annual_therms=sim.annual.total_gas_therm,
    modeled_peak_kw=sim.annual.peak_demand_kw,
    site_load_profile=site_profile,
    pv_generation_kwh=sim.pv_generation_kwh
)

# Run whole-building LCCA
from eco_tools.lcca import run_lcca_with_site_loads

results = run_lcca_with_site_loads(
    whole_building=whole_building,
    tariff=tariff,
    capital_cost=project_capex
)
```

---

## 9. Sources

- [ASHRAE Standard 90.1](https://www.ashrae.org/technical-resources/bookstore/standard-90-1) - Energy efficiency standards
- [DOE Better Buildings - Plug & Process Loads](https://betterbuildingssolutioncenter.energy.gov/plug-process-loads) - PPL guidance
- [DOE Server Rooms and Closets](https://www.osti.gov/biblio/1172953) - IT energy efficiency
- [EIA CBECS](https://www.eia.gov/consumption/commercial/) - Commercial building energy data
- [LEED EAp2](https://leeduser.buildinggreen.com/credit/NC-v4/EAp2) - Energy modeling requirements
- [ENERGY STAR Multifamily](https://www.energystar.gov/buildings/resources-audience/multifamily-housing) - Multifamily resources
- [WM SmartEnergy Compactors](https://www.wm.com/us/en/business/business-waste-compactors) - Compactor efficiency
- [DOE Commercial Kitchens](https://buildingenergyscore.energy.gov/resources/download?key=publications/Final_ASHRAE_PNNL_CommercialKitchen.pdf) - Kitchen energy

---

**Last Updated**: December 29, 2024
