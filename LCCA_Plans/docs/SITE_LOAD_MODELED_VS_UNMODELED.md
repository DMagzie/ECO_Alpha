# Site Loads: Modeled vs. Non-Modeled Boundaries

**Version:** 1.0
**Date:** December 2024
**Purpose:** Define the boundary between CBECC-modeled and non-modeled site loads to prevent double-counting

---

## 1. The Double-Counting Problem

When combining CBECC simulation results with site load calculations, there's a risk of counting the same energy twice. This occurs when:
- A load is already included in the CBECC model
- The same load is calculated separately and added to LCCA

**Example**: Common area laundry rooms are typically modeled in CBECC with their full process loads. Adding separate laundry calculations would double-count that energy.

---

## 2. Load Classification Matrix

### 2.1 Loads Typically MODELED in CBECC

These loads are included in standard CBECC compliance models:

| Load Category | CBECC Element | Notes |
|---------------|---------------|-------|
| **Zone HVAC** | AirSys, ZnSys, ThrmlZn | Heating, cooling, fans for conditioned zones |
| **Interior Lighting (Regulated)** | IntLtgSys, Lum | Per space function, Title 24 LPD |
| **Receptacles (Plug Loads)** | SpcFuncDefaults → RecptPwrDens | Default by space function |
| **Domestic Hot Water** | FluidSys (ServiceHotWater) | Central and distributed |
| **Ventilation** | AirSeg, OACtrl | Per zone requirements |
| **Elevator Machine Room** | Space with HVAC | Cooling load only (not motor energy) |
| **Common Laundry (if modeled)** | Spc with process loads | Per space function defaults |

### 2.2 Loads Sometimes Modeled (Project-Specific)

These depend on the project scope and LEED requirements:

| Load Category | When Modeled | When NOT Modeled |
|---------------|--------------|------------------|
| **Garage Exhaust Fans** | LEED whole-building models | CA compliance-only |
| **Kitchen Exhaust** | Commercial kitchens with explicit HVAC | Small break rooms |
| **Pool Equipment Room** | If room is conditioned space | Equipment energy itself |
| **Elevator Motors** | Never in CBECC | Always non-modeled |

### 2.3 Loads Typically NOT MODELED in CBECC

These are candidates for site load calculations:

| Load Category | Why Not Modeled | Calculation Approach |
|---------------|-----------------|---------------------|
| **Exterior/Site Lighting** | Outside building envelope | W × hours |
| **Parking Garage Lighting** | Often unconditioned/exempt | LPD × area × hours |
| **EV Chargers** | Not building load | kW × ports × hours |
| **Elevator Motors** | Process load, not in CSE | Empirical kWh/yr |
| **Pool Pumps** | External equipment | HP × efficiency × hours |
| **Pool/Spa Heaters** | Not building DHW | GBCI calculator or DOE baseline |
| **Irrigation Pumps** | Landscape, not building | HP × seasonal hours |
| **Trash Compactors** | Intermittent process | Cycles × energy/cycle |
| **IT/Telecom Closets** | Process loads often excluded | kW × PUE × 8760 |
| **Fire Pumps** | Standby/testing only | HP × test hours |
| **Signage** | Exterior, not building | W × hours |

---

## 3. Two Workflow Approaches

### Approach A: Separate Calculation with Flags (Simpler)

Calculate site loads separately and add to CBECC results post-simulation.

```
┌─────────────────┐      ┌─────────────────┐
│  CBECC Model    │      │  Site Load      │
│  Simulation     │      │  Calculator     │
└────────┬────────┘      └────────┬────────┘
         │                        │
         │  Modeled kWh           │  Non-modeled kWh
         │                        │
         └──────────┬─────────────┘
                    │
                    ▼
         ┌─────────────────────┐
         │  LCCA Aggregator    │
         │  (Check flags to    │
         │   avoid duplicates) │
         └─────────────────────┘
```

**Pros:**
- Simpler implementation
- No CBECC file modifications
- Flexible for different project types

**Cons:**
- Requires user to track what's modeled
- Risk of double-counting if flags wrong
- Site loads don't get hourly simulation treatment

**Implementation:**
```python
@dataclass
class SiteLoad:
    name: str
    category: LoadCategory
    annual_kwh: float
    is_modeled_in_cbecc: bool = False  # Flag to prevent double-counting

def aggregate_energy(sim: SimulationOutput, site_loads: SiteLoadProfile) -> float:
    """Combine modeled and non-modeled energy, avoiding duplicates."""
    modeled_kwh = sim.annual.total_elec_kwh

    # Only add site loads NOT already in CBECC
    non_modeled_kwh = sum(
        load.annual_kwh
        for load in site_loads.loads
        if not load.is_modeled_in_cbecc
    )

    return modeled_kwh + non_modeled_kwh
```

---

### Approach B: Process Load Injection into CBECC (Recommended for LEED)

Calculate site loads and inject as process loads into CBECC model before simulation.

```
┌─────────────────┐
│  Site Load      │
│  Calculator     │
└────────┬────────┘
         │
         │  Calculate kWh → Convert to W/SF
         │
         ▼
┌─────────────────┐
│  CBECC Model    │◄── Inject ProcElecKwPerFt2
│  (Modified)     │◄── Inject ProcGasKbtuPerHr
└────────┬────────┘
         │
         │  Run simulation with injected loads
         │
         ▼
┌─────────────────┐
│  Simulation     │
│  Results        │ ← Includes all site loads in hourly output
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  LCCA           │ ← Single source of truth
└─────────────────┘
```

**Pros:**
- Single source of truth (all energy in CBECC output)
- Proper hourly profiles for TOU calculations
- No double-counting risk
- Consistent with LEED whole-building methodology
- Already used for pool energy (per user's existing workflow)

**Cons:**
- Requires CBECC file modification capability
- Need to add process load parsing/exporting to translators
- Must re-run simulation after injection

**CBECC Properties for Injection:**

Based on CBECC file analysis, these space-level properties accept process loads:

| Property | Units | Description |
|----------|-------|-------------|
| `RecptPwrDens` | W/SF | Receptacle (plug) power density - can be used for misc electric |
| `ProcElecKwPerFt2` | kW/SF | Process electric load intensity |
| `ProcGasKbtuPerHr` | kBtu/hr | Process gas load (absolute, not per SF) |

**Conversion Formulas:**

```python
def kwh_to_process_density(annual_kwh: float, area_sf: float, hours_per_year: float = 8760) -> float:
    """Convert annual kWh to W/SF for CBECC process load injection."""
    # annual_kwh = W/SF * area_sf * hours / 1000
    # W/SF = (annual_kwh * 1000) / (area_sf * hours)
    w_per_sf = (annual_kwh * 1000) / (area_sf * hours_per_year)
    return w_per_sf

def therms_to_gas_load(annual_therms: float, hours_per_year: float = 8760) -> float:
    """Convert annual therms to kBtu/hr for CBECC process gas injection."""
    # 1 therm = 100 kBtu
    annual_kbtu = annual_therms * 100
    kbtu_per_hr = annual_kbtu / hours_per_year
    return kbtu_per_hr

# Example: Pool pump room with 7,000 kWh/yr and 500 SF
pool_room_w_sf = kwh_to_process_density(7000, 500, 8760)  # = 1.6 W/SF
```

---

## 4. Recommended Implementation Strategy

### Phase 1: Approach A (Immediate)
- Implement site load calculator with `is_modeled_in_cbecc` flags
- Add guidance in data collection sheet for common scenarios
- Document which loads are typically modeled vs. not
- LCCA reports show separate columns: "Modeled" | "Site Loads" | "Total"

### Phase 2: Approach B (Future)
- Add process load parsing to zone_parser.py
- Add process load export to zone_exporter.py
- Create injection workflow: Site Calc → Convert → Inject → Simulate
- Integrate with existing pool energy injection workflow

---

## 5. Load-by-Load Guidance

### Common Area Laundry

**Typically Modeled?** YES - CBECC includes laundry in space function defaults

**Recommendation:**
- Check if laundry room exists as explicit space in CBECC model
- If yes, set `is_modeled_in_cbecc = True`
- If no laundry space in model, calculate separately

**CBECC Space Function:** "Laundry Area (common)"
- Default includes washer/dryer process loads

---

### Garage Exhaust Fans

**Typically Modeled?** DEPENDS on project type

| Project Type | Modeled? |
|--------------|----------|
| CA Compliance Only | Usually NO - garage often exempt |
| LEED Whole Building | Usually YES - explicit exhaust fans |

**Recommendation:**
- For LEED projects: Check if garage has exhaust system in CBECC model
- For compliance-only: Calculate separately as non-modeled

---

### Pool/Spa Equipment

**Typically Modeled?** PARTIAL
- Pool equipment ROOM may be modeled (HVAC for room)
- Pool EQUIPMENT (pumps, heaters) is NOT modeled

**Current Workflow (per user):**
1. Calculate pool energy from GBCI spreadsheet
2. Convert to W/SF process load
3. Inject into pool equipment room in CBECC
4. Re-run simulation

**Recommendation:** Continue this injection approach for LEED projects

---

### Elevators

**Typically Modeled?** NO - never in CBECC
- Elevator machine room HVAC may be modeled
- Elevator motor energy is NEVER in CBECC

**Recommendation:** Always calculate separately (8,000 kWh/yr default)

---

### Exterior/Site Lighting

**Typically Modeled?** NO - outside building envelope

**Recommendation:** Always calculate separately

---

### Parking Structure Lighting

**Typically Modeled?** DEPENDS
- If parking is conditioned space: Lighting may be modeled
- If unconditioned/exempt: NOT modeled

**Recommendation:** Check CBECC model for parking space with lighting systems

---

### IT/Server Rooms

**Typically Modeled?** PARTIAL
- Room HVAC typically modeled
- IT equipment load may or may not be in process loads

**Recommendation:**
- Check space function and RecptPwrDens value
- If RecptPwrDens is low/default, IT load likely not included
- Calculate separately or inject as process load

---

## 6. Data Collection Sheet Updates

Add these fields to the Site Load Data Collection sheet:

```
| Field | Type | Description |
|-------|------|-------------|
| is_in_cbecc_model | boolean | Is this space/load already in CBECC? |
| cbecc_space_name | text | Name of space in CBECC model (for verification) |
| override_reason | text | Why including if might be modeled |
```

### Workflow Guidance in Sheet:

```
BEFORE ENTERING SITE LOADS:
1. Review your CBECC model to identify which spaces/loads are included
2. For each site load category, check the "is_in_cbecc_model" flag
3. If load IS in CBECC: Set flag = TRUE (will be excluded from totals)
4. If load is NOT in CBECC: Set flag = FALSE (will be included)
5. Document any uncertainties in the override_reason field

COMMON SCENARIOS:
- Laundry Room modeled in CBECC → Set laundry flag = TRUE
- Garage modeled as unconditioned → Set garage lighting flag = FALSE
- Pool equipment room modeled → Set pool flag = TRUE (but equipment = FALSE)
```

---

## 7. Future: Process Load Injection Implementation

### Required Code Changes

**1. Zone Parser Extension** (`zone_parser.py`):
```python
def _parse_single_zone(self, zone_elem, ...):
    # ... existing code ...

    # Add process load parsing
    recpt_pwr_dens = self.get_property(zone_elem, 'RecptPwrDens')
    proc_elec_kw_ft2 = self.get_property(zone_elem, 'ProcElecKwPerFt2')
    proc_gas_kbtu_hr = self.get_property(zone_elem, 'ProcGasKbtuPerHr')

    zone['process_loads'] = {
        'receptacle_w_sf': recpt_pwr_dens,
        'process_elec_kw_sf': proc_elec_kw_ft2,
        'process_gas_kbtu_hr': proc_gas_kbtu_hr
    }
```

**2. Zone Exporter Extension** (`zone_exporter.py`):
```python
def _export_zone(self, zone: dict, ...):
    # ... existing code ...

    # Export process loads if present
    if 'process_loads' in zone:
        pl = zone['process_loads']
        if pl.get('receptacle_w_sf'):
            self.set_property(zone_elem, 'RecptPwrDens', pl['receptacle_w_sf'])
        if pl.get('process_elec_kw_sf'):
            self.set_property(zone_elem, 'ProcElecKwPerFt2', pl['process_elec_kw_sf'])
        if pl.get('process_gas_kbtu_hr'):
            self.set_property(zone_elem, 'ProcGasKbtuPerHr', pl['process_gas_kbtu_hr'])
```

**3. Site Load Injector** (new module):
```python
def inject_site_loads(cibd_path: str, site_loads: SiteLoadProfile, output_path: str):
    """Inject calculated site loads into CBECC model as process loads."""

    # Load CIBD file
    model = import_cibd(cibd_path)

    # Map site loads to spaces
    for load in site_loads.loads:
        if load.target_space:
            space = find_space(model, load.target_space)
            if space:
                # Convert annual kWh to W/SF
                w_sf = kwh_to_process_density(
                    load.annual_kwh,
                    space['area_sf'],
                    load.hours_per_year
                )

                # Add to existing process loads
                existing = space.get('process_loads', {}).get('process_elec_kw_sf', 0)
                space['process_loads']['process_elec_kw_sf'] = existing + (w_sf / 1000)

    # Export modified model
    export_cibd(model, output_path)
```

---

## 8. Summary

| Aspect | Approach A (Separate) | Approach B (Injection) |
|--------|----------------------|------------------------|
| Implementation | Simpler, immediate | More complex, future phase |
| Double-counting prevention | Manual flags | Automatic (single source) |
| TOU accuracy | Limited (annual totals) | Full (hourly simulation) |
| LEED compatibility | Requires adjustment | Native support |
| Existing workflow | New | Extends pool energy workflow |

**Recommended Path:**
1. **Immediate**: Implement Approach A with robust flagging and guidance
2. **Future**: Add Approach B for LEED projects and enhanced TOU analysis
3. **Document**: Clear guidance on which loads are modeled by default

---

**Last Updated**: December 2024
