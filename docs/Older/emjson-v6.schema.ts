/**
 * EMJSON v6.1 TypeScript Schema Definition
 *
 * Energy Model JSON - Universal building energy modeling interchange format
 * Used by ECO Tools for format conversion between CIBD22, CIBD22X, CIBD25, HBJSON, GEM
 *
 * @version 6.1
 * @date 2025-11-13
 * @status Production Ready
 */

// ============================================================================
// Root Schema
// ============================================================================

export interface EMJSON {
  schema_version: "6.1";
  project: ProjectMetadata;
  geometry: GeometryData;
  catalogs: CatalogData;
  systems: SystemsData;
  proj_metadata?: Record<string, any>;
  metadata?: Record<string, any>;
  diagnostics?: Diagnostic[];
}

// ============================================================================
// Project Metadata
// ============================================================================

export interface ProjectMetadata {
  name: string;
  description?: string;
  location?: LocationData;

  // Title 24 specific
  ruleset_filename?: string;         // "T24N_2022.bin" or "T24_2025.bin"
  software_version?: string;         // "CBECC 2022.3.1 (1343)" or "CBECC 2025.2.0 (1390)"
  bldg_engy_model_version?: number;  // 16 (T24 2022) or 17 (T24 2025)

  // Project classification
  building_type?: "MF" | "NR";       // Multifamily or Nonresidential
  compliance_type?: "Residential" | "Nonresidential" | "Mixed";

  // Authoring
  author?: string;
  created_date?: string;             // ISO 8601
  modified_date?: string;            // ISO 8601
}

export interface LocationData {
  latitude?: number;
  longitude?: number;
  elevation_m?: number;
  climate_zone?: string;             // Title 24 climate zone
  weather_file?: string;             // Weather file reference
  city?: string;
  state?: string;
  country?: string;
}

// ============================================================================
// Geometry Data
// ============================================================================

export interface GeometryData {
  zones: Zone[];
  zone_groups: ZoneGroup[];
  surfaces: Surface[];
  openings: Opening[];
}

export interface Zone {
  id: string;
  name: string;
  building_type: "MF" | "NR";
  zone_type?: "residential" | "commercial" | "other_residential";

  // Geometric properties
  multiplier?: number;
  floor_area_m2?: number;
  volume_m3?: number;
  stories_above?: number;

  // Space classification
  space_function?: string;
  conditioned?: boolean;             // True=conditioned, False=unconditioned

  // References
  du_ref?: string;                   // Dwelling unit type reference
  served_by?: string[];              // HVAC system IDs
  surfaces?: string[];               // Surface IDs

  annotation?: Record<string, any>;
}

export interface ZoneGroup {
  id: string;
  name: string;
  group_type: "floor" | "wing" | "building";

  // Floor properties
  floor_number?: number;
  floor_to_floor_height_m?: number;
  floor_to_ceiling_height_m?: number;
  z_coordinate_m?: number;

  // References
  zone_refs?: string[];

  annotation?: Record<string, any>;
}

export interface Surface {
  id: string;
  name: string;
  parent_zone_id: string;

  // Surface classification
  surface_type: "wall" | "roof" | "floor" | "ceiling";
  surface_subtype?: string;          // CBECC subtype (e.g., "res_ext_wall")

  // Geometric properties
  tilt_deg?: number;                 // 0=horizontal, 90=vertical
  azimuth_deg?: number;              // 0=North, 90=East, 180=South, 270=West
  area_m2?: number;
  perimeter_m?: number;              // For slab floors

  // Construction
  construction_ref?: string;

  // Boundary conditions
  adjacency?: "exterior" | "interior" | "ground" | "adiabatic";
  is_party_surface?: boolean;
  adjacent_space_ref?: string;       // For interior surfaces

  // Thermal properties
  ext_solar_abs?: number;            // 0-1
  ext_thermal_abs?: number;          // 0-1

  // References
  openings?: string[];

  annotation?: Record<string, any>;
}

export interface Opening {
  id: string;
  parent_surface_id: string;
  type: "window" | "door" | "skylight";

  // Geometric properties
  area_m2?: number;
  height_m?: number;
  width_m?: number;

  // Fenestration properties
  window_type_ref?: string;
  fenestration_cons_ref?: string;
  u_factor_SI?: number;              // W/m²·K
  shgc?: number;                     // 0-1
  vt?: number;                       // 0-1

  annotation?: Record<string, any>;
}

// ============================================================================
// Catalog Data
// ============================================================================

export interface CatalogData {
  materials: Material[];
  constructions: Construction[];
  window_types: WindowType[];
  schedules: Schedule[];
  du_types?: DwellingUnitType[];
}

export interface Material {
  id: string;
  name: string;
  material_type: string;

  // Thermal properties
  thickness_m?: number;
  r_value_SI?: number;               // m²·K/W

  // Physical properties
  density_kg_m3?: number;
  specific_heat?: number;            // J/kg·K

  annotation?: Record<string, any>;
}

export interface Construction {
  id: string;
  name: string;
  construction_type: "wall" | "roof" | "floor" | "ceiling";

  // Thermal properties
  u_factor_SI?: number;              // W/m²·K
  r_value_SI?: number;               // m²·K/W

  // Layer composition
  material_layers?: string[];        // Material IDs (outside to inside)

  // Framing (wood-frame assemblies)
  framing_config?: string;           // "16in_oc", "24in_oc"
  framing_depth_m?: number;
  framing_spacing_m?: number;

  annotation?: Record<string, any>;
}

export interface WindowType {
  id: string;
  name: string;
  fenestration_type: "window" | "door" | "skylight";

  // Overall area
  area_m2?: number;

  // Thermal/optical properties
  u_factor_SI?: number;              // W/m²·K
  shgc?: number;                     // 0-1
  vt?: number;                       // 0-1

  // Frame and glazing
  frame_type?: string;               // "Aluminum", "Vinyl", "Wood", "Fiberglass"
  glazing_type?: string;             // "Single", "Double", "Triple"
  num_panes?: number;
  gas_fill?: string;                 // "Air", "Argon", "Krypton"

  annotation?: Record<string, any>;
}

export interface Schedule {
  id: string;
  name: string;
  schedule_type: "day" | "week" | "year";
  data_type?: "fraction" | "temperature" | "on/off";

  // Time series data
  values?: number[];
  hours?: number[];
  day_schedules?: string[];          // For week schedules

  annotation?: Record<string, any>;
}

export interface DwellingUnitType {
  id: string;
  name: string;
  bedrooms?: number;
  bathrooms?: number;
  floor_area_m2?: number;
  occupant_count?: number;
}

// ============================================================================
// Systems Data
// ============================================================================

export interface SystemsData {
  hvac: HVACSystem[];
  zone_terminals: ZoneTerminal[];
  dhw: DHWSystem[];
  water_heaters: WaterHeater[];
  recirculation_loops: RecirculationLoop[];
  iaq_fans: IAQFan[];
  pv_arrays: PVArray[];
  battery_systems: BatterySystem[];
  lighting_systems: LightingSystem[];
  luminaires: Luminaire[];
  fan_systems: FanSystem[];
  heat_pumps: HeatPump[];
  distribution_systems: DistributionSystem[];
  control_systems: ControlSystem[];
}

export interface HVACSystem {
  id: string;
  name: string;

  // CBECC system classification
  type: 1 | 2 | 4;                   // 1=Heat+Cool, 2=HeatPump, 4=Central
  status?: 1 | 2 | 3 | 4;            // 1=Existing, 2=Altered, 3=New, 4=Mixed

  fuel?: string;
  multiplier?: number;

  // Equipment arrays with counts
  heating_systems?: string[];
  heating_counts?: number[];

  cooling_systems?: string[];
  cooling_counts?: number[];

  heat_pump_systems?: string[];
  heat_pump_counts?: number[];

  central_equipment?: string[];
  central_counts?: number[];

  // Distribution and controls
  distribution_ref?: string;
  fan_ref?: string;

  // Zone terminal units (for central systems)
  zone_terminals?: string[];

  // Service tracking
  zone_refs?: string[];
  floor_area_served?: number;

  // Legacy properties
  heating_source?: string;
  cooling_source?: string;
  distribution_type?: string;

  annotation?: Record<string, any>;
}

export interface ZoneTerminal {
  id: string;
  name: string;
  parent_hvac_system_id: string;
  zone_served_ref: string;

  terminal_type: string;             // "VAVR", "VAV", "FC", "PTAC", "PTHP"
  floor_area_served?: number;

  // VAV with Reheat properties
  min_cfm?: number;
  reheat_type?: string;
  reheat_source?: string;

  // Fan Coil properties
  coil_type?: string;
  has_heating?: boolean;
  has_cooling?: boolean;

  // PTAC/PTHP properties
  capacity_btuh?: number;
  eer?: number;
  hspf?: number;

  annotation?: Record<string, any>;
}

export interface DHWSystem {
  id: string;
  name: string;
  system_type: string;

  // Central DHW classification
  is_central?: boolean;
  central_system_type?: string;      // "Multifamily", "Commercial", "Residential"

  // Water heater arrays
  water_heaters?: string[];
  water_heater_counts?: number[];

  // Recirculation loops
  recirculation_loops?: string[];

  // Distribution properties
  distribution_type?: string;        // "Compact", "Standard", "Recirculating"
  pipe_insulation_level?: string;    // "None", "R2", "R4", "R6", "R8"

  // Service tracking
  floor_area_served?: number;
  dwelling_units_served?: number;

  // Legacy properties
  recirc_type?: string;
  requirements?: string[];

  annotation?: Record<string, any>;
}

export interface WaterHeater {
  id: string;
  name: string;
  heater_type: string;               // "Electric", "Gas", "HeatPump", "Solar"

  // Tank classification
  tank_type?: string;                // "Storage", "Tankless", "LargeStorage"

  // Capacity
  storage_volume_gal?: number;
  input_capacity_btu_hr?: number;

  // Efficiency metrics
  energy_factor?: number;            // EF (legacy)
  uniform_energy_factor?: number;    // UEF (current)
  thermal_efficiency?: number;       // TE (instantaneous)
  first_hour_rating?: number;        // FHR (gal/hr)
  recovery_efficiency?: number;      // RE

  // Heat pump specific
  cop?: number;
  compressor_location?: string;      // "Integral", "External"

  // Installation
  fuel_type?: string;
  location?: string;                 // "Conditioned", "Unconditioned", "Exterior"

  annotation?: Record<string, any>;
}

export interface RecirculationLoop {
  id: string;
  name: string;
  parent_dhw_system_id: string;

  // Loop configuration
  loop_type: string;                 // "Central", "Demand", "Timer", "TempSensor"
  pipe_length_ft?: number;
  pipe_diameter_in?: number;
  pipe_insulation_r_value?: number;

  // Pump properties
  pump_power_w?: number;
  flow_rate_gpm?: number;

  // Control
  control_type?: string;
  operating_hours_per_day?: number;

  // Loss calculation
  heat_loss_btu_hr?: number;

  annotation?: Record<string, any>;
}

export interface IAQFan {
  id: string;
  name: string;
  fan_type: string;
  airflow_cfm?: number;
  power_w?: number;
  zone_refs?: string[];

  annotation?: Record<string, any>;
}

export interface PVArray {
  id: string;
  name: string;
  array_type: string;                // "FixedRoof", "FixedGround", "Tracking"

  // Module specification
  module_ref?: string;
  module_type?: string;              // "Standard", "Premium", "ThinFilm"

  // System sizing
  rated_capacity_w?: number;
  rated_capacity_kw?: number;
  num_modules?: number;
  module_power_w?: number;

  // Array orientation
  tilt_deg?: number;
  azimuth_deg?: number;
  tracking_type?: string;            // "Fixed", "1-Axis", "2-Axis"

  // Inverter
  inverter_efficiency?: number;
  inverter_type?: string;            // "String", "Micro", "Central"
  inverter_ref?: string;

  // Installation
  location?: string;                 // "Roof", "Ground", "Carport"
  mounting_type?: string;            // "Flush", "Standoff", "Ballasted"

  // SARA (Solar Access Roof Area)
  sara_zone_ref?: string;
  sara_area_m2?: number;

  // Performance
  performance_ratio?: number;
  dc_to_ac_ratio?: number;
  annual_production_kwh?: number;

  annotation?: Record<string, any>;
}

export interface BatterySystem {
  id: string;
  name: string;
  battery_type: string;              // "LithiumIon", "LeadAcid", "Flow"

  // Capacity
  usable_capacity_kwh?: number;
  rated_capacity_kwh?: number;
  rated_power_kw?: number;

  // Efficiency
  round_trip_efficiency?: number;
  charge_efficiency?: number;
  discharge_efficiency?: number;

  // Control and operation
  control_strategy?: string;         // "SelfConsumption", "TOU", "Backup"
  max_charge_rate_kw?: number;
  max_discharge_rate_kw?: number;

  // Depth of discharge
  min_state_of_charge?: number;      // 0-1
  max_state_of_charge?: number;      // 0-1

  // Integration
  coupled_pv_array_ref?: string;
  coupling_type?: string;            // "DC", "AC"

  location?: string;

  annotation?: Record<string, any>;
}

export interface LightingSystem {
  id: string;
  name: string;
  system_type: "interior" | "exterior";

  space_ref?: string;

  // Power
  power_density_w_m2?: number;
  total_power_w?: number;

  // Controls
  control_type?: string;

  // Luminaires
  luminaire_refs?: string[];

  // Schedule
  schedule_ref?: string;

  annotation?: Record<string, any>;
}

export interface Luminaire {
  id: string;
  name: string;
  luminaire_type: string;
  power_w?: number;
  count?: number;
  efficiency?: number;
  lighting_system_ref?: string;

  annotation?: Record<string, any>;
}

export interface FanSystem {
  id: string;
  name: string;
  fan_type: string;
  airflow_cfm?: number;
  power_w?: number;
  efficiency?: number;
  control_method?: string;
  zone_served?: string;

  annotation?: Record<string, any>;
}

export interface HeatPump {
  id: string;
  name: string;
  pump_type: string;                 // "air-source", "ground-source", "water-source"
  heating_capacity_w?: number;
  cooling_capacity_w?: number;
  heating_cop?: number;
  cooling_eer?: number;
  backup_fuel?: string;
  zone_refs?: string[];

  annotation?: Record<string, any>;
}

export interface DistributionSystem {
  id: string;
  name: string;
  distribution_type: string;         // "ducted", "hydronic", "ductless"
  duct_location?: string;
  duct_insulation_r_value_SI?: number;
  duct_leakage_pct?: number;
  hvac_system_ref?: string;

  annotation?: Record<string, any>;
}

export interface ControlSystem {
  id: string;
  name: string;
  control_type: string;              // "outdoor_air", "economizer", "demand", "occupancy"
  control_method?: string;
  setpoint_high?: number;
  setpoint_low?: number;
  system_ref?: string;

  annotation?: Record<string, any>;
}

// ============================================================================
// Diagnostics
// ============================================================================

export interface Diagnostic {
  level: "info" | "warning" | "error";
  code: string;
  message: string;
  stage: "import" | "export" | "validation";
  ts?: string;                       // ISO 8601
  path?: string;
  context?: string;
  source: string;
}

// ============================================================================
// Type Guards
// ============================================================================

export function isEMJSON(obj: any): obj is EMJSON {
  return (
    obj &&
    obj.schema_version === "6.1" &&
    typeof obj.project === "object" &&
    typeof obj.geometry === "object" &&
    typeof obj.catalogs === "object" &&
    typeof obj.systems === "object"
  );
}

export function isZone(obj: any): obj is Zone {
  return (
    obj &&
    typeof obj.id === "string" &&
    typeof obj.name === "string" &&
    (obj.building_type === "MF" || obj.building_type === "NR")
  );
}

export function isHVACSystem(obj: any): obj is HVACSystem {
  return (
    obj &&
    typeof obj.id === "string" &&
    typeof obj.name === "string" &&
    (obj.type === 1 || obj.type === 2 || obj.type === 4)
  );
}

// ============================================================================
// Enums
// ============================================================================

export enum HVACSystemType {
  SeparateHeatCool = 1,
  HeatPump = 2,
  Central = 4
}

export enum SystemStatus {
  Existing = 1,
  Altered = 2,
  New = 3,
  Mixed = 4
}

export enum BuildingType {
  Multifamily = "MF",
  Nonresidential = "NR"
}

export enum ZoneType {
  Residential = "residential",
  Commercial = "commercial",
  OtherResidential = "other_residential"
}

export enum SurfaceType {
  Wall = "wall",
  Roof = "roof",
  Floor = "floor",
  Ceiling = "ceiling"
}

export enum Adjacency {
  Exterior = "exterior",
  Interior = "interior",
  Ground = "ground",
  Adiabatic = "adiabatic"
}

export enum OpeningType {
  Window = "window",
  Door = "door",
  Skylight = "skylight"
}

export enum DiagnosticLevel {
  Info = "info",
  Warning = "warning",
  Error = "error"
}

// ============================================================================
// Validation
// ============================================================================

export class EMJSONValidator {
  private errors: string[] = [];

  validate(emjson: EMJSON): boolean {
    this.errors = [];

    // Required fields
    if (!emjson.schema_version) {
      this.errors.push("Missing schema_version");
    }
    if (emjson.schema_version !== "6.1") {
      this.errors.push(`Invalid schema_version: ${emjson.schema_version}`);
    }

    // Validate structure
    this.validateGeometry(emjson.geometry);
    this.validateCatalogs(emjson.catalogs);
    this.validateSystems(emjson.systems);
    this.validateReferences(emjson);

    return this.errors.length === 0;
  }

  getErrors(): string[] {
    return this.errors;
  }

  private validateGeometry(geometry: GeometryData): void {
    if (!Array.isArray(geometry.zones)) {
      this.errors.push("geometry.zones must be an array");
    }
    if (!Array.isArray(geometry.surfaces)) {
      this.errors.push("geometry.surfaces must be an array");
    }
  }

  private validateCatalogs(catalogs: CatalogData): void {
    if (!Array.isArray(catalogs.materials)) {
      this.errors.push("catalogs.materials must be an array");
    }
    if (!Array.isArray(catalogs.constructions)) {
      this.errors.push("catalogs.constructions must be an array");
    }
  }

  private validateSystems(systems: SystemsData): void {
    if (!Array.isArray(systems.hvac)) {
      this.errors.push("systems.hvac must be an array");
    }
    if (!Array.isArray(systems.dhw)) {
      this.errors.push("systems.dhw must be an array");
    }
  }

  private validateReferences(emjson: EMJSON): void {
    const zoneIds = new Set(emjson.geometry.zones.map(z => z.id));
    const surfaceIds = new Set(emjson.geometry.surfaces.map(s => s.id));
    const hvacIds = new Set(emjson.systems.hvac.map(h => h.id));

    // Validate surface → zone references
    for (const surface of emjson.geometry.surfaces) {
      if (!zoneIds.has(surface.parent_zone_id)) {
        this.errors.push(`Surface ${surface.id} references invalid zone ${surface.parent_zone_id}`);
      }
    }

    // Validate opening → surface references
    for (const opening of emjson.geometry.openings) {
      if (!surfaceIds.has(opening.parent_surface_id)) {
        this.errors.push(`Opening ${opening.id} references invalid surface ${opening.parent_surface_id}`);
      }
    }

    // Validate zone → HVAC references
    for (const zone of emjson.geometry.zones) {
      if (zone.served_by) {
        for (const hvacId of zone.served_by) {
          if (!hvacIds.has(hvacId)) {
            this.errors.push(`Zone ${zone.id} references invalid HVAC system ${hvacId}`);
          }
        }
      }
    }
  }
}

// ============================================================================
// Exports
// ============================================================================

export default EMJSON;
