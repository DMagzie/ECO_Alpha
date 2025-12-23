# CIBD22X Format Contract
**Version**: 1.0
**Date**: 2025-11-04
**Status**: Complete - Based on Universal Translator V7 Development

## Purpose

This document defines the complete contract for CIBD22X (CBECC 2022 XML) file format based on empirical analysis of production files and the Universal Translator development process. It serves as the definitive reference for parsing and serializing CBECC building energy models.

---

## Table of Contents

1. [File Structure](#file-structure)
2. [Root Element](#root-element)
3. [Reference Patterns](#reference-patterns)
4. [Building Structure](#building-structure)
5. [Catalog Elements](#catalog-elements)
6. [Mechanical Systems](#mechanical-systems)
7. [Renewable Energy](#renewable-energy)
8. [Lighting Systems](#lighting-systems)
9. [Metadata & Compliance](#metadata--compliance)
10. [Data Types & Units](#data-types--units)
11. [Special Patterns](#special-patterns)
12. [Validation Rules](#validation-rules)

---

## File Structure

### XML Declaration
```xml
<?xml version='1.0' encoding='utf-8'?>
```

### Document Structure Hierarchy
```
SDDXML (root)
├── RulesetFilename (required)
├── Proj (project metadata)
├── ResProj (compliance settings)
├── Catalogs (materials, constructions, windows, etc.)
│   ├── ResMat (material catalog)
│   ├── ResCons (construction catalog)
│   ├── ResWinType (window type catalog)
│   ├── ResIAQFan (IAQ fan catalog)
│   ├── Lum (luminaire catalog)
│   ├── ResHtPumpSys (heat pump catalog)
│   ├── ResDHWSys (DHW system catalog)
│   ├── ResWtrHtr (water heater catalog)
│   ├── ResFanSys (fan system catalog)
│   └── DwellUnitType (dwelling unit type catalog)
├── Building Elements
│   ├── ResZnGrp (zone groups)
│   ├── Story (building stories)
│   ├── ResZn / ResOtherZn / ComZn (zones)
│   └── DwellUnit (dwelling units)
└── ResProj (after building elements)
```

**Critical Ordering**:
1. RulesetFilename must be first child of SDDXML
2. Catalogs must come before elements that reference them
3. ResProj can appear either before or after building elements

---

## Root Element

### SDDXML Element

**Tag**: `SDDXML`
**Attributes**:
- `xmlns:xsi` = `"http://www.w3.org/2001/XMLSchema-instance"` (required)
- `xmlns:xsd` = `"http://www.w3.org/2001/XMLSchema"` (required)

**Children**:
- `RulesetFilename` (required, first child)
- `Proj` (optional, project metadata)
- All catalog and building elements

**Example**:
```xml
<SDDXML xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
        xmlns:xsd="http://www.w3.org/2001/XMLSchema">
  <RulesetFilename file="T24N_2022.bin" />
  <!-- rest of document -->
</SDDXML>
```

### RulesetFilename Element

**Tag**: `RulesetFilename`
**Attributes**:
- `file` (required) - Path to ruleset binary file

**Common Values**:
- `T24N_2022.bin` (Title 24 2022 Nonresidential)
- `T24R_2022.bin` (Title 24 2022 Residential)

**Example**:
```xml
<RulesetFilename file="T24N_2022.bin" />
```

---

## Reference Patterns

### Pattern 1: ID-Based References

**Catalog Elements with `id` Attributes**:
- `ResMat` (materials)
- `ResCons` (constructions)
- `ResWinType` (window types)
- `ResHtPumpSys` (heat pumps)
- `ResDHWSys` (DHW systems)
- `ResZn`, `ResOtherZn`, `ComZn` (zones)
- `Story` (building stories)

**Reference Elements** (contain ID text):
- `ConsRef` → points to `ResCons/@id`
- `WinTypeRef` → points to `ResWinType/@id`
- `HVACSystemRef` → points to `ResHtPumpSys/@id`
- `DHWSystemRef` → points to `ResDHWSys/@id`
- `ZnRef` → points to zone `@id`
- `SpcRef` → points to space `@id`

**Example**:
```xml
<!-- Catalog item -->
<ResCons id="CONS_wall_wood_frame">
  <Name>Wall Wood Frame</Name>
  <!-- properties -->
</ResCons>

<!-- Reference -->
<ResExtWall>
  <ConsRef>CONS_wall_wood_frame</ConsRef>
</ResExtWall>
```

### Pattern 2: Name-Based References

**Catalog Elements WITHOUT `id` Attributes** (identified by `<Name>` child):
- `ResIAQFan` (IAQ fans)
- `DwellUnitType` (dwelling unit types)
- `Lum` (luminaires)

**Reference Elements** (contain Name text):
- `IAQFanRef` → points to `ResIAQFan/Name/text()`
- `DwellUnitTypeRef` → points to `DwellUnitType/Name/text()`
- `LumRef` → points to `Lum/Name/text()`

**Special Value**: `"- none -"` is a valid placeholder indicating no reference

**Example**:
```xml
<!-- Catalog item (NO id attribute) -->
<ResIAQFan>
  <Name>IAQ Fan_50 CFM</Name>
  <!-- properties -->
</ResIAQFan>

<!-- Reference (by name text) -->
<DwellUnitType>
  <IAQFanRef index="0">IAQ Fan_50 CFM</IAQFanRef>
</DwellUnitType>

<!-- No reference -->
<ResZn>
  <IAQFanRef index="0">- none -</IAQFanRef>
</ResZn>
```

### Pattern 3: Text-Based Array References

**DHW Heater References**:
- `DHWHeater[@index]` - Text content references `ResWtrHtr/Name`
- `HeaterMult[@index]` - Multiplier for corresponding heater

**Indexing**: 0-based (index="0", "1", "2", ...)

**Example**:
```xml
<!-- Water heater catalog -->
<ResWtrHtr>
  <Name>94 percent 499000 119-gal</Name>
  <HeaterElementType>Gas</HeaterElementType>
  <!-- properties -->
</ResWtrHtr>

<!-- DHW system referencing catalog by name -->
<ResDHWSys id="D_dhw_system_1">
  <DHWHeater index="0">94 percent 499000 119-gal</DHWHeater>
  <DHWHeater index="1">96 percent 250000 100-gal</DHWHeater>
  <HeaterMult index="0">4</HeaterMult>
  <HeaterMult index="1">2</HeaterMult>
</ResDHWSys>
```

### Pattern 4: Nested Components (No IDs)

**Elements that should NOT have `id` attributes**:
- `ResFanSys` (nested in HVAC systems)
- `ResWtrHtr` (when nested in DHW systems, but catalog items have Names)
- Surface elements nested in zones

**Example**:
```xml
<!-- CORRECT: No id attribute -->
<ResHtPumpSys id="HP_system_1">
  <ResFanSys>
    <Name>Fan</Name>
    <FlowCap>400</FlowCap>
  </ResFanSys>
</ResHtPumpSys>

<!-- INCORRECT: Do not add id -->
<ResFanSys id="FAN_fan">  <!-- ❌ WRONG -->
```

---

## Building Structure

### Zone Groups (ResZnGrp)

**Purpose**: Define vertical organization for multi-story buildings

**Tag**: `ResZnGrp`
**Attributes**: `id` (required)

**Children**:
- `Name` (required)
- `FlrToFlrHgt` (floor-to-floor height in feet)
- `FlrToCeilingHgt` (floor-to-ceiling height in feet)
- `Z` (Z-coordinate of floor level in feet)

**Example**:
```xml
<ResZnGrp id="ZG_level_1">
  <Name>Level 1</Name>
  <FlrToFlrHgt>10.0</FlrToFlrHgt>
  <FlrToCeilingHgt>9.0</FlrToCeilingHgt>
  <Z>0.0</Z>
</ResZnGrp>
```

### Zones (ResZn, ResOtherZn, ComZn)

**Purpose**: Define thermal zones in the building

**Tags**:
- `ResZn` (residential zone)
- `ResOtherZn` (residential other zone - corridors, stairwells, etc.)
- `ComZn` (commercial zone)

**Attributes**: `id` (required)

**Common Children**:
- `Name` (required)
- `FloorArea` (gross floor area in sq ft)
- `CondFloorArea` (conditioned floor area in sq ft)
- `Volume` (zone volume in cu ft)
- `ZnGrpRef` (reference to ResZnGrp)
- `IAQFanRef[@index]` (IAQ fan reference, name-based)
- `HVACSystemRef` (HVAC system reference)
- `DHWSystemRef` (DHW system reference)
- Surface elements (nested)
  - `ResExtWall`, `ResIntWall`, `Roof`, `Ceiling`, `IntFlr`, `SlabFlr`
- Opening elements (nested in surfaces)
  - `Win`, `Door`, `Skylt`

**Example**:
```xml
<ResZn id="ZN_unit_a1_living">
  <Name>Unit A1 Living Room</Name>
  <FloorArea>250.5</FloorArea>
  <CondFloorArea>250.5</CondFloorArea>
  <Volume>2254.5</Volume>
  <ZnGrpRef>ZG_level_1</ZnGrpRef>
  <IAQFanRef index="0">IAQ Fan_50 CFM</IAQFanRef>

  <!-- Surfaces nested in zone -->
  <ResExtWall>
    <Name>ExtWall (Front) : Unit A1 Living_L01</Name>
    <ConsRef>CONS_wall_wood_frame</ConsRef>
    <Area>120.5</Area>

    <!-- Windows nested in surface -->
    <Win>
      <Name>Win (Front 1) : Unit A1 Living_L01</Name>
      <WinTypeRef>WIN_dbl_clear</WinTypeRef>
      <Area>15.0</Area>
    </Win>
  </ResExtWall>
</ResZn>
```

### Surfaces

**Nested In**: Zone elements (ResZn, ResOtherZn, ComZn)

**Tags**:
- `ResExtWall` (exterior wall)
- `ResIntWall` (interior wall)
- `Roof` (roof surface)
- `Ceiling` (ceiling surface)
- `IntFlr` (interior floor)
- `SlabFlr` (slab-on-grade floor)

**NO `id` Attribute**: Surfaces are nested components, not catalog items

**Common Children**:
- `Name` (required)
- `ConsRef` (construction reference)
- `Area` (surface area in sq ft)
- `Orientation` (for vertical surfaces: Front, Back, Left, Right)
- `FloorZ` (Z-coordinate in feet)
- `Bottom` (bottom elevation in feet for slabs)
- `Perimeter` (perimeter length in feet for slabs)
- Opening elements (nested)

**Example**:
```xml
<ResExtWall>
  <Name>ExtWall (Front) : Living Room_L01</Name>
  <ConsRef>CONS_wall_wood_frame</ConsRef>
  <Area>120.5</Area>
  <Orientation>Front</Orientation>
  <FloorZ>0.0</FloorZ>
</ResExtWall>
```

### Openings (Windows, Doors, Skylights)

**Nested In**: Surface elements

**Tags**:
- `Win` (window)
- `Door` (door)
- `Skylt` (skylight)

**NO `id` Attribute**: Openings are nested components

**Common Children**:
- `Name` (required)
- `WinTypeRef` (window type reference for Win/Skylt)
- `Area` (opening area in sq ft)
- `U-Factor` (optional override)
- `SHGC` (optional solar heat gain coefficient override)

**Example**:
```xml
<Win>
  <Name>Win (Front 1) : Living Room_L01</Name>
  <WinTypeRef>WIN_dbl_clear_low_e</WinTypeRef>
  <Area>15.0</Area>
</Win>
```

---

## Catalog Elements

### Material Catalog (ResMat)

**Tag**: `ResMat`
**Attributes**: `id` (required)

**Children**:
- `Name` (required)
- `CodeCat` (code category)
- `CodeItem` (code item)
- `FrmMat` (framing material)
- `FrmConfig` (framing configuration)
- `FrmDepth` (framing depth in inches)
- `FrmSpacing` (framing spacing in inches)
- `CavityInsOpt` (cavity insulation option)
- `CavityInsRVal` (cavity R-value)
- `ContInsOpt` (continuous insulation option)
- `ContInsRVal` (continuous R-value)
- `ConductivityCT` (conductivity variants for different conditions)

**ConductivityCT Variants**:
```xml
<ConductivityCT cond="0">0.025</ConductivityCT>  <!-- Base -->
<ConductivityCT cond="1">0.028</ConductivityCT>  <!-- Aged -->
<ConductivityCT cond="2">0.030</ConductivityCT>  <!-- Wet -->
```

**Example**:
```xml
<ResMat id="MAT_wall_r13">
  <Name>Wall R-13 Wood Frame</Name>
  <CodeCat>Wood Framed Wall</CodeCat>
  <CodeItem>R-13</CodeItem>
  <FrmMat>Wood</FrmMat>
  <FrmConfig>Wall16inOC</FrmConfig>
  <FrmDepth>3.5</FrmDepth>
  <FrmSpacing>16</FrmSpacing>
  <CavityInsOpt>R-13</CavityInsOpt>
  <CavityInsRVal>13</CavityInsRVal>
</ResMat>
```

### Construction Catalog (ResCons)

**Tag**: `ResCons`
**Attributes**: `id` (required)

**Children**:
- `Name` (required)
- `Type` (construction type)
- `ExtIns` (exterior insulation option)
- `ExtInsRVal` (exterior R-value)
- `MatRef` (material reference array)
  - `[@index]` attribute (0-based indexing)

**Example**:
```xml
<ResCons id="CONS_wall_wood_r13">
  <Name>Wood Frame Wall R-13</Name>
  <Type>WoodFramedWall</Type>
  <MatRef index="0">MAT_wall_r13</MatRef>
</ResCons>
```

### Window Type Catalog (ResWinType)

**Tag**: `ResWinType`
**Attributes**: `id` (required)

**Children**:
- `Name` (required)
- `FenType` (fenestration type)
- `FenProdType` (product type)
- `FenFrameType` (frame type)
- `FenGlzgType` (glazing type)
- `FenGlzgTint` (glazing tint)
- `FenGlzgCoating` (glazing coating)
- `NFRC_CertID` (NFRC certification ID)
- `NFRC_Manufacturer` (manufacturer)
- `NFRC_ProdName` (product name)
- `NFRC_UFactor` (U-factor)
- `NFRC_SHGC` (solar heat gain coefficient)
- `NFRC_VT` (visible transmittance)

**Example**:
```xml
<ResWinType id="WIN_dbl_clear_low_e">
  <Name>Double Clear Low-E</Name>
  <FenType>VerticalFenestration</FenType>
  <FenProdType>CurtainWall</FenProdType>
  <FenFrameType>AluminumThermalBreak</FenFrameType>
  <FenGlzgType>DoublePane</FenGlzgType>
  <FenGlzgCoating>e2</FenGlzgCoating>
  <NFRC_UFactor>0.35</NFRC_UFactor>
  <NFRC_SHGC>0.40</NFRC_SHGC>
  <NFRC_VT>0.60</NFRC_VT>
</ResWinType>
```

### Dwelling Unit Type Catalog (DwellUnitType)

**Tag**: `DwellUnitType`
**NO `id` Attribute** (referenced by Name)

**Children**:
- `Name` (required, used for references)
- `Bedrooms` (number of bedrooms)
- `Bathrooms` (number of bathrooms)
- `CondFloorArea` (conditioned floor area)
- `IAQFanRef[@index]` (IAQ fan reference array)
- `HVACSystemRef` (HVAC system reference)
- `DHWSystemRef` (DHW system reference)
- Zone references

**Example**:
```xml
<DwellUnitType>
  <Name>Unit A1</Name>
  <Bedrooms>2</Bedrooms>
  <Bathrooms>2</Bathrooms>
  <CondFloorArea>850.5</CondFloorArea>
  <IAQFanRef index="0">IAQ Fan_50 CFM</IAQFanRef>
  <HVACSystemRef>HP_system_1</HVACSystemRef>
  <DHWSystemRef>D_dhw_system_1</DHWSystemRef>
</DwellUnitType>
```

### IAQ Fan Catalog (ResIAQFan)

**Tag**: `ResIAQFan`
**NO `id` Attribute** (referenced by Name)

**Children**:
- `Name` (required, used for references)
- `IAQFanType` (fan type)
- `IAQCFM` (airflow in CFM)
- `WperCFMIAQ` (watts per CFM)
- `IAQOption` (IAQ option type)

**Example**:
```xml
<ResIAQFan>
  <Name>IAQ Fan_50 CFM</Name>
  <IAQFanType>ExhaustOnly</IAQFanType>
  <IAQCFM>50</IAQCFM>
  <WperCFMIAQ>0.35</WperCFMIAQ>
  <IAQOption>Title24_2022_MF</IAQOption>
</ResIAQFan>
```

---

## Mechanical Systems

### Heat Pump Catalog (ResHtPumpSys)

**Tag**: `ResHtPumpSys`
**Attributes**: `id` (required)

**Children**:
- `Name` (required)
- `Type` (system type)
- `HeatPumpType` (heat pump type)
- `NumOfUnits` (number of units)
- `CapRtd` (rated capacity in Btu/h)
- `CapRtdSens` (rated sensible capacity)
- `HSPF` (heating seasonal performance factor)
- `SEER` (seasonal energy efficiency ratio)
- `EER` (energy efficiency ratio)
- `COP` (coefficient of performance)
- `AuxHtCapRated` (auxiliary heat capacity)
- `AuxHtSrc` (auxiliary heat source)
- `ResFanSys` (fan system, nested - NO id attribute)
- `DistribSystem` (distribution system, nested)

**Example**:
```xml
<ResHtPumpSys id="HP_system_1">
  <Name>Heat Pump System 1</Name>
  <Type>HeatPump</Type>
  <HeatPumpType>AirSource</HeatPumpType>
  <NumOfUnits>1</NumOfUnits>
  <CapRtd>36000</CapRtd>
  <CapRtdSens>27000</CapRtdSens>
  <HSPF>9.0</HSPF>
  <SEER>16.0</SEER>

  <!-- Fan system nested without id -->
  <ResFanSys>
    <Name>Fan</Name>
    <FlowCap>1200</FlowCap>
    <Pwr>400</Pwr>
  </ResFanSys>
</ResHtPumpSys>
```

### DHW System Catalog (ResDHWSys)

**Tag**: `ResDHWSys`
**Attributes**: `id` (required)

**Children**:
- `Name` (required)
- `Type` (system type)
- `DHWHeater[@index]` (water heater references, 0-based)
  - Text content = ResWtrHtr/Name
- `HeaterMult[@index]` (heater multipliers, 0-based)
- `DHWDistSys` (distribution system)
- `WtHtrPipeInsul` (pipe insulation)
- `SolSys` (solar system, optional)

**Example**:
```xml
<ResDHWSys id="D_dhw_system_1">
  <Name>DHW System 1</Name>
  <Type>IndividualStorage</Type>

  <!-- Text references to catalog items -->
  <DHWHeater index="0">94 percent 499000 119-gal</DHWHeater>
  <DHWHeater index="1">96 percent 250000 100-gal</DHWHeater>

  <!-- Multipliers for each heater -->
  <HeaterMult index="0">4</HeaterMult>
  <HeaterMult index="1">2</HeaterMult>

  <DHWDistSys>
    <DHWDist>
      <Name>Distribution</Name>
      <DistType>Recirculating</DistType>
    </DHWDist>
  </DHWDistSys>
</ResDHWSys>
```

### Water Heater Catalog (ResWtrHtr)

**Tag**: `ResWtrHtr`
**NO `id` Attribute** (referenced by Name via DHWHeater)

**Children**:
- `Name` (required, used for references)
- `HeaterElementType` (Gas, Electric, HeatPump)
- `TankType` (tank type)
- `InputRating` (input rating in Btu/h)
- `EnergyFactor` (energy factor)
- `TankVolume` (tank volume in gallons)
- `RecovEff` (recovery efficiency)
- `UniformEnergyFactor` (UEF, optional)

**Example**:
```xml
<ResWtrHtr>
  <Name>94 percent 499000 119-gal</Name>
  <HeaterElementType>Gas</HeaterElementType>
  <TankType>Commercial Storage (TE & SBL)</TankType>
  <InputRating>499000</InputRating>
  <EnergyFactor>0.94</EnergyFactor>
  <TankVolume>119</TankVolume>
  <RecovEff>94</RecovEff>
</ResWtrHtr>
```

---

## Renewable Energy

### PV Array Catalog (PVArray)

**Tag**: `PVArray` (NOT ResPVSys)
**Attributes**: `id` (optional in some versions)

**Children**:
- `Name` (required)
- `DCSysSize` (DC system size in kW) - NOT RatedCap
- `ModuleType` (module type)
- `PwrElec` (inverter type) - NOT InverterType
- `ArrayAz` (array azimuth in degrees)
- `ArrayTilt` (array tilt in degrees)
- `DCAC_Ratio` (DC to AC ratio)
- `InverterEff` (inverter efficiency)
- `SysLoss` (system losses %)

**IMPORTANT Tag Names** (CBECC-specific):
- Use `PVArray` not `ResPVSys`
- Use `DCSysSize` not `RatedCap`
- Use `PwrElec` not `InverterType`

**Example**:
```xml
<PVArray>
  <Name>Rooftop PV System</Name>
  <DCSysSize>25.5</DCSysSize>
  <ModuleType>Standard</ModuleType>
  <PwrElec>StringInverter</PwrElec>
  <ArrayAz>180</ArrayAz>
  <ArrayTilt>20</ArrayTilt>
  <DCAC_Ratio>1.15</DCAC_Ratio>
  <InverterEff>0.96</InverterEff>
  <SysLoss>14</SysLoss>
</PVArray>
```

---

## Lighting Systems

### Luminaire Catalog (Lum)

**Tag**: `Lum`
**NO `id` Attribute** (referenced by Name)

**Children**:
- `Name` (required, used for references)
- `Pwr` (power in watts)
- `LumEff` (luminous efficacy in lumens/watt)
- `Type` (luminaire type)
- `CtrlType` (control type)

**Example**:
```xml
<Lum>
  <Name>LF-01</Name>
  <Pwr>28</Pwr>
  <LumEff>92</LumEff>
  <Type>Recessed</Type>
  <CtrlType>Manual</CtrlType>
</Lum>
```

### Interior Lighting System (IntLtgSys)

**Tag**: `IntLtgSys`
**Parent**: Zone element (ResZn, ComZn, etc.)

**Children**:
- `LumRef[@index]` (luminaire references, name-based)
- `LumCnt[@index]` (luminaire counts)
- `Pwr` (total power)
- `VentSpcFunc` (ventilated space function)

**Example**:
```xml
<IntLtgSys>
  <LumRef index="0">LF-01</LumRef>
  <LumRef index="1">LF-02</LumRef>
  <LumCnt index="0">8</LumCnt>
  <LumCnt index="1">4</LumCnt>
  <Pwr>336</Pwr>
</IntLtgSys>
```

---

## Metadata & Compliance

### Project Metadata (Proj)

**Tag**: `Proj`
**NO `id` Attribute**
**Position**: Near beginning of file, before or after catalogs

**Children**:
- `Name` (project name)
- `BldgEngyModelVersion` (model version)
- `CreateDate` (creation date)
- `ModDate` (modification date)
- `RunDate` (run date)
- `GeometryInpType` (geometry input type)
- `EffMetric` (efficiency metric)
- `StAddress` (street address)
- `City` (city)
- `State` (state)
- `ZipCode` (zip code)
- `WeatherStation` (weather station)
- `Lat` (latitude)
- `Lon` (longitude)
- `Elevation` (elevation in feet)
- `BldgType` (building type)
- `ConstructionPeriod` (construction period)

**Example**:
```xml
<Proj>
  <Name>Sample Building Project</Name>
  <BldgEngyModelVersion>22.0.0</BldgEngyModelVersion>
  <CreateDate>2024-01-15</CreateDate>
  <ModDate>2024-11-04</ModDate>
  <GeometryInpType>DetailedGeometry</GeometryInpType>
  <StAddress>123 Main Street</StAddress>
  <City>Los Angeles</City>
  <State>CA</State>
  <ZipCode>90001</ZipCode>
  <WeatherStation>LOS-ANGELES-INTL-AP</WeatherStation>
  <Lat>33.9425</Lat>
  <Lon>-118.4081</Lon>
  <Elevation>100</Elevation>
  <BldgType>Multifamily</BldgType>
</Proj>
```

### Compliance Settings (ResProj)

**Tag**: `ResProj`
**NO `id` Attribute**
**Position**: Can appear before or after building elements (prefer after)

**Children**:
- `Name` (required)
- `StdDesignFuel_HVAC` (standard design fuel for HVAC)
- `StdDesignFuel_DHW` (standard design fuel for DHW)
- `StdDesignFuel_IAQVent` (standard design fuel for IAQ ventilation)
- `Exception_NRCC_DHW` (DHW exception flag)
- `Exception_NRCC_IAQVent` (IAQ ventilation exception flag)
- Compliance calculation settings

**Example**:
```xml
<ResProj>
  <Name>Residential Project Settings</Name>
  <StdDesignFuel_HVAC>Electric</StdDesignFuel_HVAC>
  <StdDesignFuel_DHW>Gas</StdDesignFuel_DHW>
  <StdDesignFuel_IAQVent>Electric</StdDesignFuel_IAQVent>
  <Exception_NRCC_DHW>false</Exception_NRCC_DHW>
  <Exception_NRCC_IAQVent>false</Exception_NRCC_IAQVent>
</ResProj>
```

---

## Data Types & Units

### Unit Conversions

**Length**:
- CBECC uses **feet** for all lengths
- Meters → Feet: multiply by `1 / 0.3048` (or 3.28084)
- Feet → Meters: multiply by `0.3048`

**Area**:
- CBECC uses **square feet**
- Square meters → Square feet: multiply by `10.7639`

**Volume**:
- CBECC uses **cubic feet**
- Cubic meters → Cubic feet: multiply by `35.3147`

**Temperature**:
- CBECC uses **Fahrenheit**
- Celsius → Fahrenheit: `F = C * 9/5 + 32`

**Energy**:
- Power: **watts**
- Capacity: **Btu/h**
- Energy Factor: dimensionless ratio

### Boolean Values

**String Representation**:
- True: `"true"` (lowercase)
- False: `"false"` (lowercase)

**Example**:
```xml
<Exception_NRCC_DHW>false</Exception_NRCC_DHW>
<UseEERinAnalysis>true</UseEERinAnalysis>
```

### Numeric Precision

**Decimal Precision**: Generally 1-4 decimal places
- Areas: 1-2 decimals (e.g., `120.5`)
- R-values: 1-2 decimals (e.g., `13.0`)
- Efficiency ratings: 1-2 decimals (e.g., `16.0`, `0.94`)
- Coordinates: 4 decimals (e.g., `33.9425`)

---

## Special Patterns

### Indexed Arrays

**Pattern**: Multiple child elements with `[@index]` attribute

**Indexing**: **0-based** (index="0", "1", "2", ...)

**Examples**:
```xml
<!-- IAQ Fan References (0-based) -->
<IAQFanRef index="0">IAQ Fan_50 CFM</IAQFanRef>
<IAQFanRef index="1">IAQ Fan_60 CFM</IAQFanRef>

<!-- DHW Heater References (0-based) -->
<DHWHeater index="0">94 percent 499000 119-gal</DHWHeater>
<DHWHeater index="1">96 percent 250000 100-gal</DHWHeater>

<!-- Material References (0-based) -->
<MatRef index="0">MAT_layer_1</MatRef>
<MatRef index="1">MAT_layer_2</MatRef>
```

### Empty Reference Placeholder

**Value**: `"- none -"`
**Usage**: Indicates no reference (not null or empty string)
**Applies To**: Name-based references (IAQFanRef, LumRef, etc.)

**Example**:
```xml
<IAQFanRef index="0">- none -</IAQFanRef>
```

### Conditional Elements

**HVAC Fan Systems**: Only serialize if actually used in HVAC system
**DHW Heaters**: Use text references if referring to catalog, inline definitions if custom

### Annotation Preservation

**Purpose**: Store format-specific data that doesn't map to internal representation

**Common Annotations**:
- `dhw_heater_refs`: List of (index, text) tuples for DHWHeater references
- `heater_mults`: List of (index, multiplier) tuples
- `use_eer_in_analysis`: Flag for heat pump analysis

**Storage**: Annotation dictionary on object

---

## Validation Rules

### Required Elements

**Root Level**:
- ✅ SDDXML element with namespaces
- ✅ RulesetFilename element
- ✅ At least one zone element

**Zone Level**:
- ✅ Name child element
- ✅ At least FloorArea or CondFloorArea

**Catalog Items**:
- ✅ Name child element (always required)
- ✅ `id` attribute if ID-based reference pattern
- ❌ NO `id` attribute if Name-based reference pattern

### ID Uniqueness

**Rule**: All `id` attributes must be unique across entire document

**Scope**:
- Materials, constructions, windows
- Zones, spaces, stories
- HVAC systems, DHW systems
- All catalog items with IDs

**Exception**: Nested components (ResFanSys, surfaces, openings) have no IDs

### Reference Integrity

**ID-Based References**:
- Referenced ID must exist in document
- Reference element text must match an `@id` attribute

**Name-Based References**:
- Referenced name must exist in document
- Reference element text must match a `<Name>` child element
- Special value `"- none -"` is always valid

**Example Validation**:
```python
# ID-based
cons_ref = "CONS_wall_1"
assert cons_ref in [elem.get('id') for elem in root.findall('.//ResCons')]

# Name-based
iaq_ref = "IAQ Fan_50 CFM"
assert iaq_ref in [elem.find('Name').text for elem in root.findall('.//ResIAQFan')]
or iaq_ref == "- none -"
```

### Nested Structure Rules

**Surfaces**:
- ✅ Must be nested in zone elements
- ❌ NOT top-level elements

**Openings**:
- ✅ Must be nested in surface elements
- ❌ NOT in zones or top-level

**Fan Systems**:
- ✅ Nested in HVAC systems
- ❌ NOT catalog items with IDs
- ❌ NOT top-level elements

### Ordering Rules

**Critical Order**:
1. SDDXML root
2. RulesetFilename (first child)
3. Proj (optional, early in file)
4. Catalogs (before references)
5. Building elements
6. ResProj (after building elements, optional)

**Catalog Order** (recommended, not strictly required):
1. ResMat (materials)
2. ResCons (constructions)
3. ResWinType (windows)
4. ResIAQFan (IAQ fans)
5. Lum (luminaires)
6. ResHtPumpSys (heat pumps)
7. ResDHWSys (DHW systems)
8. ResWtrHtr (water heaters)
9. DwellUnitType (dwelling unit types)

---

## Parsing Strategy

### Two-Pass Approach

**Pass 1: Collect Catalogs**
1. Parse all catalog elements
2. Store in dictionaries by ID or Name
3. Build lookup tables for references

**Pass 2: Build Relationships**
1. Parse building elements (zones, surfaces)
2. Resolve references using lookup tables
3. Build object graph

### ID Registry Pattern

**Purpose**: Generate unique, deterministic IDs

**Format**: `{PREFIX}_{normalized_name}`
- Prefix indicates type (MAT, CONS, WIN, HP, DHW, etc.)
- Normalized name: lowercase, underscores, alphanumeric only

**Examples**:
- Material: `MAT_wall_r13` ← "Wall R-13"
- Construction: `CONS_wood_frame_wall` ← "Wood Frame Wall"
- Zone: `ZN_unit_a1_living` ← "Unit A1 Living"

### Reference Resolution

**ID-Based**:
```python
# Store during catalog parsing
catalog_by_id[elem.get('id')] = parsed_object

# Resolve during building parsing
ref_text = ref_elem.text
referenced_object = catalog_by_id[ref_text]
```

**Name-Based**:
```python
# Store during catalog parsing (no ID!)
catalog_by_name[name_elem.text] = parsed_object

# Resolve during building parsing
ref_text = ref_elem.text
if ref_text != "- none -":
    referenced_object = catalog_by_name[ref_text]
```

---

## Serialization Strategy

### Order of Operations

1. **Create root and namespaces**
2. **Add RulesetFilename**
3. **Serialize project metadata (Proj)**
4. **Serialize catalogs** (order matters for readability)
5. **Serialize zone groups**
6. **Serialize zones with nested surfaces/openings**
7. **Serialize dwelling units**
8. **Serialize compliance settings (ResProj)**

### ID Assignment Rules

**Add IDs**:
- ✅ Catalog items: ResMat, ResCons, ResWinType, ResHtPumpSys, ResDHWSys
- ✅ Building elements: ResZn, ResOtherZn, ComZn, Story, ResZnGrp

**NO IDs**:
- ❌ Name-based catalog: ResIAQFan, DwellUnitType, Lum, ResWtrHtr
- ❌ Nested components: ResFanSys, surfaces, openings
- ❌ Metadata: Proj, ResProj

### Reference Serialization

**ID-Based**:
```python
# Serialize reference element with ID text
ref_elem = ET.SubElement(parent, 'ConsRef')
ref_elem.text = construction.id
```

**Name-Based**:
```python
# Serialize reference element with Name text
ref_elem = ET.SubElement(parent, 'IAQFanRef', index="0")
ref_elem.text = iaq_fan.name
```

**Array References**:
```python
# Multiple indexed elements
for i, (idx, heater_name) in enumerate(dhw_heater_refs):
    heater_elem = ET.SubElement(dhw_elem, 'DHWHeater', index=str(idx))
    heater_elem.text = heater_name
```

### Annotation Handling

**Preserve Format-Specific Data**:
```python
# Store during parsing
object.annotation['dhw_heater_refs'] = [(0, 'Heater 1'), (1, 'Heater 2')]

# Restore during serialization
if 'dhw_heater_refs' in dhw_system.annotation:
    for idx, heater_ref in dhw_system.annotation['dhw_heater_refs']:
        heater_elem = ET.SubElement(dhw_elem, 'DHWHeater', index=str(idx))
        heater_elem.text = heater_ref
```

---

## Common Pitfalls & Solutions

### Pitfall 1: Adding IDs to Nested Components

**Problem**: Adding `id` attributes to ResFanSys, surfaces, openings
**Symptom**: Duplicate ID errors, validation failures
**Solution**: Never add `id` to nested components

**Correct**:
```xml
<ResHtPumpSys id="HP_system_1">
  <ResFanSys>  <!-- NO id attribute -->
    <Name>Fan</Name>
  </ResFanSys>
</ResHtPumpSys>
```

### Pitfall 2: Using ID for Name-Based References

**Problem**: Looking up IAQ fans, dwelling units, luminaires by ID
**Symptom**: "Broken reference" errors
**Solution**: Look up by Name element text, not by ID

**Correct**:
```python
# Wrong: Looking for ID
catalog_by_id = {elem.get('id'): elem for elem in root.findall('.//ResIAQFan')}

# Right: Looking for Name
catalog_by_name = {elem.find('Name').text: elem for elem in root.findall('.//ResIAQFan')}
```

### Pitfall 3: Wrong PV Tag Names

**Problem**: Using ResPVSys, RatedCap, InverterType (generic names)
**Symptom**: CBECC doesn't recognize PV systems
**Solution**: Use CBECC-specific names: PVArray, DCSysSize, PwrElec

**Correct**:
```xml
<PVArray>  <!-- NOT ResPVSys -->
  <DCSysSize>25.5</DCSysSize>  <!-- NOT RatedCap -->
  <PwrElec>StringInverter</PwrElec>  <!-- NOT InverterType -->
</PVArray>
```

### Pitfall 4: 1-Based Indexing

**Problem**: Using index="1" for first element
**Symptom**: Missing first IAQ fan, DHW heater, etc.
**Solution**: Always use 0-based indexing (index="0" for first)

**Correct**:
```xml
<IAQFanRef index="0">First Fan</IAQFanRef>  <!-- 0, not 1 -->
<IAQFanRef index="1">Second Fan</IAQFanRef>
```

### Pitfall 5: Surfaces as Top-Level Elements

**Problem**: Serializing surfaces at root level instead of nested in zones
**Symptom**: CBECC doesn't associate surfaces with zones
**Solution**: Always nest surfaces inside zone elements

**Correct**:
```xml
<ResZn id="ZN_living">
  <!-- Surfaces nested inside zone -->
  <ResExtWall>
    <Name>Wall</Name>
  </ResExtWall>
</ResZn>
```

### Pitfall 6: Missing Namespaces

**Problem**: Omitting xmlns:xsi and xmlns:xsd attributes
**Symptom**: CBECC XML validation warnings
**Solution**: Always include both namespaces on SDDXML root

**Correct**:
```xml
<SDDXML xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
        xmlns:xsd="http://www.w3.org/2001/XMLSchema">
```

### Pitfall 7: Unit Conversion Errors

**Problem**: Using meters instead of feet
**Symptom**: Incorrect geometry, area calculations
**Solution**: Always convert to feet before serialization

**Correct**:
```python
# Convert meters to feet
height_ft = height_m / 0.3048
area_ft2 = area_m2 * 10.7639
```

---

## Version History

### Version 1.0 (2025-11-04)
- Initial comprehensive contract based on Universal Translator V7 development
- Covers all building structure, mechanical systems, renewable energy
- Documents both ID-based and Name-based reference patterns
- Includes validation rules, serialization strategies, common pitfalls
- Based on empirical analysis of 8 production files (1,917 zones, 38,051 elements)
- 100% validation pass rate across diverse building types

---

## References

### Source Files Analyzed
- Bressi Ranch Apartments.cibd22x (290 zones, multi-family)
- Euclid Buildings A, B, C (132, 95, 18 zones, commercial/mixed-use)
- Del Amo Circle (254 zones, mixed-use)
- Freedom Circle Buildings A, B (342, 442 zones, mixed-use)
- Mainplace Mall (344 zones, commercial)

### Related Documentation
- Universal Translator V7 source code
- ITERATION_10_COMPLETE.md
- ITERATION_9.5_COMPLETE.md
- VALIDATION_RESULTS.md
- V7_TRANSLATOR_COMPLETE.md

### CBECC Resources
- CBECC 2022 Software (via Wine)
- Title 24 2022 Standards
- California Energy Commission documentation

---

**Document Status**: ✅ COMPLETE
**Validation**: Tested across 8 diverse production files
**Confidence Level**: HIGH (based on empirical validation)
