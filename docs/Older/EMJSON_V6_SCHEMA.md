# EMJSON v6.1 Schema Definition

**Version:** 6.1
**Date:** November 13, 2025
**Status:** Production Ready

---

## Overview

EMJSON (Energy Model JSON) v6.1 is the universal internal representation format used by ECO Tools for building energy modeling. It serves as the interchange format between all supported file formats (CIBD22, CIBD22X, CIBD25, HBJSON, GEM).

**Key Features:**
- Title 24 compliance (2022 and 2025)
- Complete building system representation
- CBECC-compliant data structures
- Honeybee/Ladybug Tools compatibility
- Full roundtrip preservation

---

## Root Schema

```typescript
{
  "schema_version": "6.1",           // Required: Schema version identifier
  "project": ProjectMetadata,         // Required: Project-level information
  "geometry": GeometryData,           // Required: Building geometry
  "catalogs": CatalogData,            // Required: Material and component catalogs
  "systems": SystemsData,             // Required: Building systems (HVAC, DHW, PV, etc.)
  "proj_metadata": Object,            // Optional: CBECC project metadata
  "metadata": Object,                 // Optional: General metadata
  "diagnostics": Array<Diagnostic>    // Optional: Import/export diagnostics
}
```

---

## 1. Project Metadata

```typescript
interface ProjectMetadata {
  name: string;                       // Project name
  description?: string;               // Project description
  location?: LocationData;            // Geographic location

  // Title 24 specific
  ruleset_filename?: string;          // "T24N_2022.bin" or "T24_2025.bin"
  software_version?: string;          // "CBECC 2022.3.1 (1343)" or "CBECC 2025.2.0 (1390)"
  bldg_engy_model_version?: number;   // 16 (T24 2022) or 17 (T24 2025)

  // Project classification
  building_type?: string;             // "MF" (Multifamily) or "NR" (Nonresidential)
  compliance_type?: string;           // "Residential", "Nonresidential", "Mixed"

  // Authoring
  author?: string;
  created_date?: string;              // ISO 8601 format
  modified_date?: string;             // ISO 8601 format
}
```

**Example:**
```json
{
  "name": "Bressi Ranch Apartments",
  "description": "290-unit multifamily residential development",
  "location": {
    "latitude": 33.1212,
    "longitude": -117.2298,
    "climate_zone": "7",
    "weather_file": "CZ07RV2.bin"
  },
  "ruleset_filename": "T24N_2022.bin",
  "software_version": "CBECC 2022.3.1 (1343)",
  "bldg_engy_model_version": 16,
  "building_type": "MF",
  "compliance_type": "Residential"
}
```

---

## 2. Geometry Data

```typescript
interface GeometryData {
  zones: Array<Zone>;                 // Building zones/spaces
  zone_groups: Array<ZoneGroup>;      // Zone groupings (floors, wings)
  surfaces: Array<Surface>;           // Walls, roofs, floors
  openings: Array<Opening>;           // Windows, doors, skylights
}
```

### 2.1 Zone

```typescript
interface Zone {
  id: string;                         // Unique identifier
  name: string;                       // Display name
  building_type: "MF" | "NR";         // Building classification
  zone_type?: "residential" | "commercial" | "other_residential";

  // Geometric properties
  multiplier?: number;                // Default: 1
  floor_area_m2?: number;             // Floor area in square meters
  volume_m3?: number;                 // Volume in cubic meters
  stories_above?: number;             // Number of stories

  // Space classification
  space_function?: string;            // Space function type
  conditioned?: boolean;              // True=conditioned, False=unconditioned

  // References
  du_ref?: string;                    // Dwelling unit type reference
  served_by?: Array<string>;          // HVAC system IDs serving this zone
  surfaces?: Array<string>;           // Surface IDs belonging to this zone

  annotation?: Object;                // Additional properties
}
```

**Example:**
```json
{
  "id": "Unit_101",
  "name": "Unit 101",
  "building_type": "MF",
  "zone_type": "residential",
  "multiplier": 1,
  "floor_area_m2": 79.0,
  "volume_m3": 189.6,
  "stories_above": 1,
  "space_function": "LivingSpace",
  "conditioned": true,
  "du_ref": "DUT_2BR_1BA",
  "served_by": ["HVAC_System_1"],
  "surfaces": ["Wall_101_N", "Wall_101_S", "Floor_101", "Roof_101"]
}
```

### 2.2 Zone Group

```typescript
interface ZoneGroup {
  id: string;                         // Unique identifier
  name: string;                       // Display name (e.g., "Level 1")
  group_type: "floor" | "wing" | "building";

  // Floor properties
  floor_number?: number;              // Floor number (1-indexed)
  floor_to_floor_height_m?: number;   // Floor-to-floor height
  floor_to_ceiling_height_m?: number; // Floor-to-ceiling height
  z_coordinate_m?: number;            // Vertical position

  // References
  zone_refs?: Array<string>;          // Zone IDs in this group

  annotation?: Object;
}
```

**Example:**
```json
{
  "id": "L01",
  "name": "Level 1",
  "group_type": "floor",
  "floor_number": 1,
  "floor_to_floor_height_m": 3.048,
  "floor_to_ceiling_height_m": 2.438,
  "z_coordinate_m": 0.0,
  "zone_refs": ["Unit_101", "Unit_102", "Unit_103"]
}
```

### 2.3 Surface

```typescript
interface Surface {
  id: string;                         // Unique identifier
  name: string;                       // Display name
  parent_zone_id: string;             // Zone containing this surface

  // Surface classification
  surface_type: "wall" | "roof" | "floor" | "ceiling";
  surface_subtype?: string;           // CBECC subtype (e.g., "res_ext_wall")

  // Geometric properties
  tilt_deg?: number;                  // Tilt angle (0=horizontal, 90=vertical)
  azimuth_deg?: number;               // Compass direction (0=North, 90=East)
  area_m2?: number;                   // Surface area
  perimeter_m?: number;               // Perimeter (for slab floors)

  // Construction
  construction_ref?: string;          // Construction assembly reference

  // Boundary conditions
  adjacency?: "exterior" | "interior" | "ground" | "adiabatic";
  is_party_surface?: boolean;         // Party wall designation
  adjacent_space_ref?: string;        // Adjacent zone for interior surfaces

  // Thermal properties
  ext_solar_abs?: number;             // Exterior solar absorptance (0-1)
  ext_thermal_abs?: number;           // Exterior thermal absorptance (0-1)

  // References
  openings?: Array<string>;           // Window/door IDs on this surface

  annotation?: Object;
}
```

**Example:**
```json
{
  "id": "Wall_101_N",
  "name": "Unit 101 North Wall",
  "parent_zone_id": "Unit_101",
  "surface_type": "wall",
  "surface_subtype": "res_ext_wall",
  "tilt_deg": 90.0,
  "azimuth_deg": 0.0,
  "area_m2": 12.5,
  "construction_ref": "Cons_ExtWall_Wood",
  "adjacency": "exterior",
  "ext_solar_abs": 0.7,
  "ext_thermal_abs": 0.9,
  "openings": ["Win_101_N1"]
}
```

### 2.4 Opening

```typescript
interface Opening {
  id: string;                         // Unique identifier
  parent_surface_id: string;          // Surface containing this opening
  type: "window" | "door" | "skylight";

  // Geometric properties
  area_m2?: number;                   // Opening area
  height_m?: number;                  // Height
  width_m?: number;                   // Width

  // Fenestration properties
  window_type_ref?: string;           // Window type reference
  fenestration_cons_ref?: string;     // Fenestration construction reference
  u_factor_SI?: number;               // U-factor (W/m²·K)
  shgc?: number;                      // Solar heat gain coefficient (0-1)
  vt?: number;                        // Visible transmittance (0-1)

  annotation?: Object;
}
```

**Example:**
```json
{
  "id": "Win_101_N1",
  "parent_surface_id": "Wall_101_N",
  "type": "window",
  "area_m2": 1.5,
  "height_m": 1.5,
  "width_m": 1.0,
  "window_type_ref": "WT_DblPane_LowE",
  "u_factor_SI": 2.27,
  "shgc": 0.25,
  "vt": 0.40
}
```

---

## 3. Catalog Data

```typescript
interface CatalogData {
  materials: Array<Material>;         // Material layers
  constructions: Array<Construction>; // Construction assemblies
  window_types: Array<WindowType>;    // Window/fenestration types
  schedules: Array<Schedule>;         // Time-based schedules
  du_types?: Array<Object>;           // Dwelling unit types (CBECC)
}
```

### 3.1 Material

```typescript
interface Material {
  id: string;                         // Unique identifier
  name: string;                       // Material name
  material_type: string;              // "insulation", "concrete", "wood", etc.

  // Thermal properties
  thickness_m?: number;               // Thickness in meters
  r_value_SI?: number;                // R-value (m²·K/W)

  // Physical properties
  density_kg_m3?: number;             // Density (kg/m³)
  specific_heat?: number;             // Specific heat (J/kg·K)

  annotation?: Object;
}
```

**Example:**
```json
{
  "id": "Mat_Insulation_R19",
  "name": "Batt Insulation R-19",
  "material_type": "insulation",
  "thickness_m": 0.152,
  "r_value_SI": 3.35,
  "density_kg_m3": 12.0,
  "specific_heat": 840.0
}
```

### 3.2 Construction

```typescript
interface Construction {
  id: string;                         // Unique identifier
  name: string;                       // Construction name
  construction_type: "wall" | "roof" | "floor" | "ceiling";

  // Thermal properties
  u_factor_SI?: number;               // U-factor (W/m²·K)
  r_value_SI?: number;                // R-value (m²·K/W)

  // Layer composition
  material_layers?: Array<string>;    // Material IDs (outside to inside)

  // Framing (wood-frame assemblies)
  framing_config?: string;            // "16in_oc", "24in_oc"
  framing_depth_m?: number;           // Framing depth
  framing_spacing_m?: number;         // Framing spacing

  annotation?: Object;
}
```

**Example:**
```json
{
  "id": "Cons_ExtWall_Wood",
  "name": "Wood Frame Exterior Wall",
  "construction_type": "wall",
  "u_factor_SI": 0.34,
  "r_value_SI": 2.94,
  "material_layers": [
    "Mat_Stucco",
    "Mat_Sheathing",
    "Mat_Insulation_R19",
    "Mat_Gypsum"
  ],
  "framing_config": "16in_oc",
  "framing_depth_m": 0.089
}
```

### 3.3 Window Type

```typescript
interface WindowType {
  id: string;                         // Unique identifier
  name: string;                       // Window type name
  fenestration_type: "window" | "door" | "skylight";

  // Overall area (for "Overall Window Area" method)
  area_m2?: number;

  // Thermal/optical properties
  u_factor_SI?: number;               // U-factor (W/m²·K)
  shgc?: number;                      // Solar heat gain coefficient (0-1)
  vt?: number;                        // Visible transmittance (0-1)

  // Frame and glazing
  frame_type?: string;                // "Aluminum", "Vinyl", "Wood", "Fiberglass"
  glazing_type?: string;              // "Single", "Double", "Triple"
  num_panes?: number;                 // Number of panes
  gas_fill?: string;                  // "Air", "Argon", "Krypton"

  annotation?: Object;
}
```

**Example:**
```json
{
  "id": "WT_DblPane_LowE",
  "name": "Double-Pane Low-E Window",
  "fenestration_type": "window",
  "u_factor_SI": 2.27,
  "shgc": 0.25,
  "vt": 0.40,
  "frame_type": "Vinyl",
  "glazing_type": "Double",
  "num_panes": 2,
  "gas_fill": "Argon"
}
```

### 3.4 Schedule

```typescript
interface Schedule {
  id: string;                         // Unique identifier
  name: string;                       // Schedule name
  schedule_type: "day" | "week" | "year";
  data_type?: "fraction" | "temperature" | "on/off";

  // Time series data
  values?: Array<number>;             // Schedule values
  hours?: Array<number>;              // Hour markers (for day schedules)
  day_schedules?: Array<string>;      // Day schedule IDs (for week schedules)

  annotation?: Object;
}
```

**Example:**
```json
{
  "id": "Sch_Occupancy_Residential",
  "name": "Residential Occupancy",
  "schedule_type": "day",
  "data_type": "fraction",
  "values": [1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 0.5, 0.2, 0.2, 0.2, 0.2, 0.2,
             0.2, 0.2, 0.2, 0.2, 0.2, 0.5, 0.8, 1.0, 1.0, 1.0, 1.0, 1.0],
  "hours": [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23]
}
```

---

## 4. Systems Data

```typescript
interface SystemsData {
  hvac: Array<HVACSystem>;            // HVAC systems
  zone_terminals: Array<ZoneTerminal>; // Zone terminal units
  dhw: Array<DHWSystem>;              // Domestic hot water systems
  water_heaters: Array<WaterHeater>;  // Water heater equipment
  recirculation_loops: Array<RecirculationLoop>;
  iaq_fans: Array<IAQFan>;            // Indoor air quality fans
  pv_arrays: Array<PVArray>;          // Photovoltaic arrays
  battery_systems: Array<BatterySystem>;
  lighting_systems: Array<LightingSystem>;
  luminaires: Array<Luminaire>;       // Light fixtures
  fan_systems: Array<FanSystem>;      // Residential fans
  heat_pumps: Array<HeatPump>;        // Heat pump systems
  distribution_systems: Array<DistributionSystem>;
  control_systems: Array<ControlSystem>;
}
```

### 4.1 HVAC System

```typescript
interface HVACSystem {
  id: string;                         // Unique identifier
  name: string;                       // System name

  // CBECC system classification
  type: 1 | 2 | 4;                   // 1=Heat+Cool, 2=HeatPump, 4=Central
  status?: 1 | 2 | 3 | 4;            // 1=Existing, 2=Altered, 3=New, 4=Mixed

  fuel?: string;                      // "Electric", "NaturalGas", "Propane"
  multiplier?: number;                // Default: 1

  // Equipment arrays (CBECC Phase 1.5)
  heating_systems?: Array<string>;    // Heating equipment IDs
  heating_counts?: Array<number>;     // Equipment counts

  cooling_systems?: Array<string>;    // Cooling equipment IDs
  cooling_counts?: Array<number>;     // Equipment counts

  heat_pump_systems?: Array<string>;  // Heat pump IDs
  heat_pump_counts?: Array<number>;   // Equipment counts

  central_equipment?: Array<string>;  // Central equipment IDs
  central_counts?: Array<number>;     // Equipment counts

  // Distribution and controls
  distribution_ref?: string;          // Distribution system ID
  fan_ref?: string;                   // Fan system ID

  // Zone terminal units (for central systems)
  zone_terminals?: Array<string>;     // ZoneTerminal IDs

  // Service tracking
  zone_refs?: Array<string>;          // Zone IDs served
  floor_area_served?: number;         // Total floor area served (m²)

  annotation?: Object;
}
```

**Example - Residential Split System:**
```json
{
  "id": "HVAC_Sys_1",
  "name": "Residential Split System",
  "type": 1,
  "status": 3,
  "fuel": "Electric",
  "multiplier": 1,
  "heating_systems": ["Furnace_Gas_80AFUE"],
  "heating_counts": [1],
  "cooling_systems": ["AC_SEER13"],
  "cooling_counts": [1],
  "distribution_ref": "Dist_Ducted_Sys1",
  "zone_refs": ["Unit_101"],
  "floor_area_served": 79.0
}
```

**Example - Central VAV System:**
```json
{
  "id": "HVAC_Central_RTU1",
  "name": "Rooftop Unit 1 - VAV",
  "type": 4,
  "status": 3,
  "fuel": "NaturalGas",
  "central_equipment": ["RTU_GasHeat_DX_Cooling"],
  "central_counts": [1],
  "distribution_ref": "Dist_VAV_RTU1",
  "fan_ref": "Fan_Supply_RTU1",
  "zone_terminals": ["ZnSys_101_VAVR", "ZnSys_102_VAVR", "ZnSys_103_VAV"],
  "zone_refs": ["Office_101", "Office_102", "Office_103"],
  "floor_area_served": 500.0
}
```

### 4.2 Zone Terminal

```typescript
interface ZoneTerminal {
  id: string;                         // Unique identifier
  name: string;                       // Terminal name
  parent_hvac_system_id: string;      // Parent HVAC system ID
  zone_served_ref: string;            // Zone ID served

  terminal_type: string;              // "VAVR", "VAV", "FC", "PTAC", "PTHP"
  floor_area_served?: number;         // Floor area served (m²)

  // VAV with Reheat properties
  min_cfm?: number;                   // Minimum airflow
  reheat_type?: string;               // "Electric", "HotWater"
  reheat_source?: string;             // Reheat source

  // Fan Coil properties
  coil_type?: string;                 // "2Pipe", "4Pipe"
  has_heating?: boolean;
  has_cooling?: boolean;

  // PTAC/PTHP properties
  capacity_btuh?: number;             // Capacity (Btu/h)
  eer?: number;                       // Energy efficiency ratio
  hspf?: number;                      // Heating seasonal performance factor

  annotation?: Object;
}
```

**Example:**
```json
{
  "id": "ZnSys_101_VAVR",
  "name": "Office 101 VAV Reheat",
  "parent_hvac_system_id": "HVAC_Central_RTU1",
  "zone_served_ref": "Office_101",
  "terminal_type": "VAVR",
  "floor_area_served": 150.0,
  "min_cfm": 100.0,
  "reheat_type": "Electric",
  "reheat_source": "Electric"
}
```

### 4.3 DHW System

```typescript
interface DHWSystem {
  id: string;                         // Unique identifier
  name: string;                       // System name
  system_type: string;                // "Central", "Individual", "Recirculating"

  // Central DHW classification
  is_central?: boolean;
  central_system_type?: string;       // "Multifamily", "Commercial", "Residential"

  // Water heater arrays (CBECC Phase 2)
  water_heaters?: Array<string>;      // WaterHeater IDs
  water_heater_counts?: Array<number>; // Equipment counts

  // Recirculation loops
  recirculation_loops?: Array<string>; // RecirculationLoop IDs

  // Distribution properties
  distribution_type?: string;         // "Compact", "Standard", "Recirculating"
  pipe_insulation_level?: string;     // "None", "R2", "R4", "R6", "R8"

  // Service tracking
  floor_area_served?: number;         // Floor area served (m²)
  dwelling_units_served?: number;     // Number of dwelling units

  annotation?: Object;
}
```

**Example:**
```json
{
  "id": "DHW_Central_1",
  "name": "Central DHW System",
  "system_type": "Recirculating",
  "is_central": true,
  "central_system_type": "Multifamily",
  "water_heaters": ["WH_Gas_Central", "WH_Solar_Thermal"],
  "water_heater_counts": [2, 1],
  "recirculation_loops": ["Recirc_Loop_Main"],
  "distribution_type": "Recirculating",
  "pipe_insulation_level": "R4",
  "dwelling_units_served": 290
}
```

### 4.4 Water Heater

```typescript
interface WaterHeater {
  id: string;                         // Unique identifier
  name: string;                       // Heater name
  heater_type: string;                // "Electric", "Gas", "HeatPump", "Solar"

  // Tank classification
  tank_type?: string;                 // "Storage", "Tankless", "LargeStorage"

  // Capacity
  storage_volume_gal?: number;        // Tank volume (gallons)
  input_capacity_btu_hr?: number;     // Input capacity (Btu/h)

  // Efficiency metrics
  energy_factor?: number;             // EF (legacy)
  uniform_energy_factor?: number;     // UEF (current)
  thermal_efficiency?: number;        // TE (instantaneous)
  first_hour_rating?: number;         // FHR (gal/hr)
  recovery_efficiency?: number;       // RE

  // Heat pump specific
  cop?: number;                       // Coefficient of performance
  compressor_location?: string;       // "Integral", "External"

  // Installation
  fuel_type?: string;                 // "Electric", "NaturalGas", "Propane"
  location?: string;                  // "Conditioned", "Unconditioned", "Exterior"

  annotation?: Object;
}
```

**Example:**
```json
{
  "id": "WH_Gas_Central",
  "name": "Central Gas Water Heater",
  "heater_type": "Gas",
  "tank_type": "LargeStorage",
  "storage_volume_gal": 100.0,
  "input_capacity_btu_hr": 199000.0,
  "uniform_energy_factor": 0.82,
  "thermal_efficiency": 0.80,
  "recovery_efficiency": 0.78,
  "fuel_type": "NaturalGas",
  "location": "Unconditioned"
}
```

### 4.5 PV Array

```typescript
interface PVArray {
  id: string;                         // Unique identifier
  name: string;                       // Array name
  array_type: string;                 // "FixedRoof", "FixedGround", "Tracking"

  // Module specification
  module_ref?: string;                // Module reference
  module_type?: string;               // "Standard", "Premium", "ThinFilm"

  // System sizing
  rated_capacity_w?: number;          // DC rating (Watts)
  rated_capacity_kw?: number;         // DC rating (kW)
  num_modules?: number;               // Module count
  module_power_w?: number;            // Individual module power

  // Array orientation
  tilt_deg?: number;                  // Tilt angle
  azimuth_deg?: number;               // Compass direction
  tracking_type?: string;             // "Fixed", "1-Axis", "2-Axis"

  // Inverter
  inverter_efficiency?: number;       // Inverter efficiency (0-1)
  inverter_type?: string;             // "String", "Micro", "Central"
  inverter_ref?: string;              // Inverter reference

  // Installation
  location?: string;                  // "Roof", "Ground", "Carport"
  mounting_type?: string;             // "Flush", "Standoff", "Ballasted"

  // SARA (Solar Access Roof Area)
  sara_zone_ref?: string;             // SARA zone reference
  sara_area_m2?: number;              // SARA area

  // Performance
  performance_ratio?: number;         // System efficiency
  dc_to_ac_ratio?: number;            // DC/AC ratio
  annual_production_kwh?: number;     // Annual production

  annotation?: Object;
}
```

**Example:**
```json
{
  "id": "PV_Roof_Array",
  "name": "Rooftop Solar Array",
  "array_type": "FixedRoof",
  "module_type": "Premium",
  "rated_capacity_kw": 10.0,
  "num_modules": 30,
  "module_power_w": 333,
  "tilt_deg": 20.0,
  "azimuth_deg": 180.0,
  "tracking_type": "Fixed",
  "inverter_efficiency": 0.96,
  "inverter_type": "String",
  "location": "Roof",
  "mounting_type": "Standoff",
  "performance_ratio": 0.80,
  "dc_to_ac_ratio": 1.2
}
```

### 4.6 Battery System

```typescript
interface BatterySystem {
  id: string;                         // Unique identifier
  name: string;                       // Battery name
  battery_type: string;               // "LithiumIon", "LeadAcid", "Flow"

  // Capacity
  usable_capacity_kwh?: number;       // Usable energy capacity
  rated_capacity_kwh?: number;        // Total capacity
  rated_power_kw?: number;            // Maximum discharge rate

  // Efficiency
  round_trip_efficiency?: number;     // Charge-discharge efficiency (0-1)
  charge_efficiency?: number;         // Charge efficiency (0-1)
  discharge_efficiency?: number;      // Discharge efficiency (0-1)

  // Control and operation
  control_strategy?: string;          // "SelfConsumption", "TOU", "Backup"
  max_charge_rate_kw?: number;        // Max charge rate
  max_discharge_rate_kw?: number;     // Max discharge rate

  // Depth of discharge
  min_state_of_charge?: number;       // Min SOC (0-1)
  max_state_of_charge?: number;       // Max SOC (0-1)

  // Integration
  coupled_pv_array_ref?: string;      // PV array if DC-coupled
  coupling_type?: string;             // "DC", "AC"

  location?: string;                  // "Indoor", "Outdoor", "Garage"

  annotation?: Object;
}
```

**Example:**
```json
{
  "id": "Battery_1",
  "name": "Lithium Ion Battery Storage",
  "battery_type": "LithiumIon",
  "usable_capacity_kwh": 13.5,
  "rated_capacity_kwh": 15.0,
  "rated_power_kw": 5.0,
  "round_trip_efficiency": 0.90,
  "control_strategy": "SelfConsumption",
  "max_charge_rate_kw": 5.0,
  "max_discharge_rate_kw": 5.0,
  "min_state_of_charge": 0.10,
  "max_state_of_charge": 1.00,
  "coupled_pv_array_ref": "PV_Roof_Array",
  "coupling_type": "DC",
  "location": "Garage"
}
```

### 4.7 Lighting System

```typescript
interface LightingSystem {
  id: string;                         // Unique identifier
  name: string;                       // System name
  system_type: "interior" | "exterior";

  space_ref?: string;                 // Zone/space reference

  // Power
  power_density_w_m2?: number;        // Lighting power density (W/m²)
  total_power_w?: number;             // Total power (W)

  // Controls
  control_type?: string;              // "Manual", "Occupancy", "Daylight", "Dimming"

  // Luminaires
  luminaire_refs?: Array<string>;     // Luminaire IDs

  // Schedule
  schedule_ref?: string;              // Schedule ID

  annotation?: Object;
}
```

**Example:**
```json
{
  "id": "LtgSys_Unit_101",
  "name": "Unit 101 Lighting",
  "system_type": "interior",
  "space_ref": "Unit_101",
  "power_density_w_m2": 6.5,
  "total_power_w": 513.5,
  "control_type": "Manual",
  "schedule_ref": "Sch_Lighting_Residential"
}
```

---

## 5. Diagnostics

```typescript
interface Diagnostic {
  level: "info" | "warning" | "error"; // Severity level
  code: string;                        // Diagnostic code (e.g., "E-IMPORT-FAILED")
  message: string;                     // Human-readable message
  stage: string;                       // "import", "export", "validation"
  ts?: string;                         // Timestamp (ISO 8601)
  path?: string;                       // File path
  context?: string;                    // Additional context (stack trace, etc.)
  source: string;                      // Source module
}
```

**Example:**
```json
{
  "level": "warning",
  "code": "W-SURFACE-NO-CONSTRUCTION",
  "message": "Surface 'Wall_101_N' has no construction assignment",
  "stage": "import",
  "ts": "2025-11-13T10:30:45Z",
  "path": "Bressi_Ranch.cibd22x",
  "source": "cibd22x_importer"
}
```

---

## Complete Sample Document

See `EMJSON_V6_SAMPLE.json` for a complete example of a multi-unit residential building with:
- 290 residential zones
- 3,472 surfaces
- HVAC systems
- DHW system with recirculation
- PV array and battery storage
- Complete material catalog
- Full Title 24 compliance metadata

---

## Version History

**v6.1 (November 2025)**
- Complete CBECC Phase 1-3 support
- Zone terminal units for central systems
- Water heater arrays with counts
- Recirculation loop support
- PV and battery system enhancements
- Full Title 24 2025 compatibility

**v6.0 (October 2025)**
- Initial production release
- Core geometry and systems support
- Basic HVAC and DHW systems
- Material catalog support

---

## Usage Notes

1. **All IDs must be unique** across all object types within a project
2. **References must resolve** - all `*_ref` fields must reference existing objects
3. **Units are SI by default** - use `_m2`, `_m`, `_m3` suffixes for clarity
4. **Optional fields may be null** - importers should handle missing data gracefully
5. **Annotation objects** preserve format-specific properties not in core schema

---

## Conversion Notes

**From CIBD22/22X/25:**
- Use modular parsers in `eco_tools/translators/cibd22x/parsers/`
- InternalRepresentation → EMJSON via dataclass serialization
- Preserve CBECC metadata in `proj_metadata`

**To CIBD22/22X/25:**
- Use modular exporters in `eco_tools/translators/cibd22x/exporters/`
- EMJSON → InternalRepresentation → CIBD format
- Ensure proper Title 24 version metadata

**From/To HBJSON:**
- Use Honeybee schema mappings
- Geometry translation via Honeybee Face/Room objects
- HVAC via IdealAirSystem or detailed templates

---

**For questions or issues:** See `docs/V7_DOCUMENTATION_INDEX.md`
