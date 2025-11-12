# CIBD25 Element Type Catalog
**Date**: 2025-11-04
**Status**: Complete Structure Analysis

## Element Type Summary

Total unique element types found: **36**

## Element Categories

### Root Level
| Element Type | Description | Example |
|--------------|-------------|---------|
| `RulesetFilename` | CBECC ruleset file reference | `"T24_2025.bin"` |
| `Proj` | Project-level metadata | Project name, dates, settings |
| `ProjVar` | Project variant/exceptions | Compliance exceptions |

### Building Structure
| Element Type | Description | Example |
|--------------|-------------|---------|
| `Bldg` | Building definition | Building name, story count |
| `Story` | Building story/floor | Story name |
| `Spc` | Space/Zone definition | Space name, volume, function |

### Geometry
| Element Type | Description | Example |
|--------------|-------------|---------|
| `PolyLp` | Polygon loop (surface boundary) | `"PolyLoop 25"` |
| `CartesianPt` | 3D coordinate point | `Coord = ( 74.4423, 16.4042, 0 )` |

### Building Envelope - Materials & Constructions
| Element Type | Description | Example |
|--------------|-------------|---------|
| `Mat` | Material definition | Concrete, insulation, gypsum |
| `ConsAssm` | Construction assembly | Wall, roof, floor assemblies |
| `FenCons` | Fenestration construction | Window constructions (U-factor, SHGC) |
| `DrCons` | Door construction | Door U-factor, type |

### Building Envelope - Surfaces
| Element Type | Description | Example |
|--------------|-------------|---------|
| `ExtWall` | Exterior wall | Wall with construction reference |
| `IntWall` | Interior wall | Interior partition |
| `Roof` | Roof surface | Roof with construction reference |
| `UndgrFlr` | Underground floor (slab) | Slab on grade |
| `ExtFlr` | Exterior floor | Exposed floor |
| `IntFlr` | Interior floor/ceiling | Interior horizontal surface |

### Building Envelope - Openings
| Element Type | Description | Example |
|--------------|-------------|---------|
| `Win` | Window | Window with fenestration construction |
| `Skylt` | Skylight | Roof window |
| `Dr` | Door | Opaque door |

### HVAC Systems
| Element Type | Description | Example |
|--------------|-------------|---------|
| `ThrmlZn` | Thermal zone | Conditioned space grouping |
| `AirSys` | Air system | HVAC air distribution system |
| `AirSeg` | Air segment | Supply/return air segment |
| `ZnSys` | Zone system | Exhaust, ventilation systems |
| `TrmlUnit` | Terminal unit | Zone terminal equipment |
| `OACtrl` | Outside air control | Ventilation control |
| `HtRcvry` | Heat recovery | Energy recovery ventilator |

### HVAC Equipment
| Element Type | Description | Example |
|--------------|-------------|---------|
| `CoilClg` | Cooling coil | DX, chilled water coil |
| `CoilHtg` | Heating coil | Hot water, heat pump, resistance |
| `Fan` | Fan equipment | Supply, return, exhaust fans |

### DHW (Domestic Hot Water)
| Element Type | Description | Example |
|--------------|-------------|---------|
| `FluidSys` | Fluid system | Service hot water system |
| `FluidSeg` | Fluid segment | Supply, makeup segments |
| `WtrHtr` | Water heater | Electric, gas water heater |

### Renewable Energy & Storage
| Element Type | Description | Example |
|--------------|-------------|---------|
| `PVArray` | Photovoltaic array | Solar PV system |
| `Batt` | Battery storage | Energy storage system |

### Compliance & Results
| Element Type | Description | Example |
|--------------|-------------|---------|
| `EUseSummary` | Energy use summary | Compliance metrics table |
| `SpcFuncDefaults` | Space function defaults | Default ventilation, occupancy |

---

## Detailed Element Structure

### Root Level Elements

#### RulesetFilename
```
RulesetFilename   "T24_2025.bin"
```
- Single line, no properties
- Specifies CBECC ruleset version

#### Proj
```
Proj   "020012-OffSml-CECStd25"
   BldgEngyModelVersion = 17
   CreateDate = 1414951358
   ModDate = 1750731527
   RunDate = 1750731528
   ZipCode = 95814
   AutoHardSize = 1
   AutoEffInput = 1
   DefaultDayltgCtrls = 1
   AirBarrier = "Air barrier - not verified"
   SoftwareVersion = "CBECC 2025.1.0 (1381)"
   CompReportPDF = 1
   ResultsCurrentMessage = "(not current)"
   ..
```

**Key Properties**:
- `BldgEngyModelVersion` - Model format version
- Dates stored as Unix timestamps
- `ZipCode` - Climate zone determination
- `AutoHardSize`, `AutoEffInput`, `DefaultDayltgCtrls` - Automation flags (0/1)
- `AirBarrier` - Compliance string
- `SoftwareVersion` - CBECC version info

#### ProjVar
```
ProjVar   "020012-OffSml-CECStd25 - ProjVar"
   ExcptCondNoClgSys = "No"
   ExcptCondRtdCap = "No"
   ExcptCondNarrative = "No"
   ..
```

**Purpose**: Compliance exceptions and special conditions

---

### Building Structure

#### Bldg
```
Bldg   "Small Office"
   FuncClassMthd = "AreaCategoryMethod"
   TotStoryCnt = 1
   AboveGrdStoryCnt = 1
   ..
```

**Hierarchy**: Root building container

#### Story
```
Story   "Building Story 1"
   ..
```

**Hierarchy**: Child of Bldg
**Note**: Often minimal properties

#### Spc (Space)
```
Spc   "Perimeter_ZN_1"
   TreeState = 254
   ThrmlZnRef = "Perimeter_ZN_1 Thermal Zone"
   Vol = 12219.7
   SpcFunc = "Office Area (>250 square feet)"
   SHWFluidSegRef = "SHWSupplyElec"
   ..
```

**Hierarchy**: Child of Story
**Key Properties**:
- `TreeState` - UI tree expansion state (254 = expanded)
- `ThrmlZnRef` - Reference to thermal zone (name-based)
- `Vol` - Volume in cubic feet
- `SpcFunc` - Space function type (compliance)
- `SHWFluidSegRef` - DHW supply reference (name-based)
- `CondgType` - "IndirectlyConditioned" for unconditioned spaces

---

### Geometry

#### PolyLp (Polygon Loop)
```
PolyLp   "PolyLoop 25"
   ..
```

**Purpose**: Defines boundary of a surface
**Hierarchy**: Child of surface element (Wall, Floor, Window, etc.)
**Contains**: Multiple CartesianPt child elements

#### CartesianPt (Cartesian Point)
```
CartesianPt   "CartesianPoint 100"
   Coord = ( 74.4423, 16.4042, 0 )
   ..
```

**Purpose**: 3D coordinate in building geometry
**Hierarchy**: Child of PolyLp
**Format**: `Coord = ( X, Y, Z )` - coordinates in feet
**Note**: Scientific notation used for very small values (e.g., `6.69906e-15`)

---

### Materials & Constructions

#### Mat (Material)
```
Mat   "Concrete - 140 lb/ft3 - 6 in."
   CodeCat = "Concrete"
   CodeItem = "Concrete - 140 lb/ft3 - 6 in."
   ..
```

**Purpose**: Material from CBECC catalog
**Key Properties**:
- `CodeCat` - Material category
- `CodeItem` - Specific catalog item
**Reference Pattern**: Name-based (referenced by name string)

#### ConsAssm (Construction Assembly)
```
ConsAssm   "Base_CZ12-NonresMetalFrameWallU055"
   CompatibleSurfType = "ExteriorWall"
   MatRef[1] = "Stucco - 7/8 in."
   MatRef[2] = "Compliance Insulation R14.60"
   MatRef[3] = "Compliance Insulation R1.41"
   MatRef[4] = "Compliance Insulation R0.02"
   MatRef[5] = "Compliance Insulation R0.02"
   MatRef[6] = "Air - Metal Wall Framing - 16 or 24 in. OC"
   MatRef[7] = "Gypsum Board - 1/2 in."
   ..
```

**Purpose**: Layered construction assembly
**Key Properties**:
- `CompatibleSurfType` - Surface type it applies to
- `MatRef[N]` - Array of material references (1-based indexing)
- `SlabType` - For underground floors
- `CRRCInitialRefl`, `CRRCAgedRefl` - Cool roof properties (roofs only)
- `CRRCInitialEmit`, `CRRCAgedEmit` - Cool roof emittance
- `CRRCProdID` - Cool Roof Rating Council product ID

**Reference Pattern**: Name-based

#### FenCons (Fenestration Construction)
```
FenCons   "Base_AllCZ_FixedWindowU34"
   FenType = "VerticalFenestration"
   FenProdType = "FixedWindow"
   AssmContext = "Manufactured"
   CertificationMthd = "NFRCRated"
   SHGC = 0.22
   UFactor = 0.34
   VT = 0.42
   ..
```

**Purpose**: Window/glazing construction
**Key Properties**:
- `FenType` - "VerticalFenestration" or "Skylight"
- `FenProdType` - "FixedWindow", "GlazedDoor", "OperableWindow"
- `CertificationMthd` - "NFRCRated", etc.
- `SHGC` - Solar Heat Gain Coefficient
- `UFactor` - Thermal conductance (Btu/hr-ft²-°F)
- `VT` - Visible Transmittance

**Reference Pattern**: Name-based

#### DrCons (Door Construction)
```
DrCons   "Base_AllCZ_Swng-ExtDoorU070"
   CertificationMthd = "NFRCRated"
   UFactor = 0.7
   Open = "Swinging"
   ..
```

**Purpose**: Opaque door construction
**Key Properties**:
- `UFactor` - Thermal conductance
- `Open` - "Swinging" or "NonSwinging"

**Reference Pattern**: Name-based

---

### Building Envelope - Surfaces

#### ExtWall (Exterior Wall)
```
ExtWall   "Perimeter_ZN_1_wall_south"
   TreeState = 254
   ConsAssmRef = "Base_CZ12-NonresMetalFrameWallU055"
   ..
```

**Hierarchy**: Child of Spc
**Contains**: PolyLp (geometry) and Win/Dr (openings)
**Key Properties**:
- `ConsAssmRef` - Construction assembly reference (name-based)

#### IntWall (Interior Wall)
```
IntWall   "Perimeter_ZN_1_wall_east"
   AdjacentSpcRef = "Perimeter_ZN_2"
   ConsAssmRef = "NACM_Interior Wall"
   ..
```

**Hierarchy**: Child of Spc
**Key Properties**:
- `AdjacentSpcRef` - Adjacent space reference (name-based)
- `ConsAssmRef` - Construction reference

#### Roof
```
Roof   "east-roof"
   ConsAssmRef = "Base_CZ12-SteepNonresWoodFramingAndOtherRoofU028"
   ..
```

**Hierarchy**: Child of Spc
**Contains**: PolyLp (geometry) and Skylt (skylights)

#### UndgrFlr (Underground Floor)
```
UndgrFlr   "Perimeter_ZN_1_floor"
   ConsAssmRef = "Base_CZ12-SlabOnOrBelowGradeF073"
   ..
```

**Hierarchy**: Child of Spc
**Purpose**: Slab on grade or below-grade floor

#### ExtFlr (Exterior Floor)
```
ExtFlr   "exposed_floor"
   ConsAssmRef = "Base_CZ12-NonresOtherFloorU071"
   ..
```

**Hierarchy**: Child of Spc
**Purpose**: Floor exposed to outside (e.g., over parking)

#### IntFlr (Interior Floor)
```
IntFlr   "attic-floor-dinning"
   AdjacentSpcRef = "Dining"
   ConsAssmRef = "NACM_Drop Ceiling"
   ..
```

**Hierarchy**: Child of Spc
**Key Properties**:
- `AdjacentSpcRef` - Adjacent space reference (name-based)

---

### Building Envelope - Openings

#### Win (Window)
```
Win   "Perimeter_ZN_1_wall_south_Window_1"
   FenConsRef = "Base_AllCZ_FixedWindowU34"
   ..
```

**Hierarchy**: Child of ExtWall
**Contains**: PolyLp (geometry)
**Key Properties**:
- `FenConsRef` - Fenestration construction reference (name-based)

#### Skylt (Skylight)
```
Skylt   "Sub Surface 264"
   FenConsRef = "Base_AllCZ_Skylt-Gl-CurbMntU58"
   ..
```

**Hierarchy**: Child of Roof
**Contains**: PolyLp (geometry)
**Key Properties**:
- `FenConsRef` - Fenestration construction reference (name-based)

#### Dr (Door)
```
Dr   "Office Front Door"
   DrConsRef = "Base_AllCZ_Swng-ExtDoorU070"
   ..
```

**Hierarchy**: Child of ExtWall
**Contains**: PolyLp (geometry)
**Key Properties**:
- `DrConsRef` - Door construction reference (name-based)

---

### HVAC Systems

#### ThrmlZn (Thermal Zone)
```
ThrmlZn   "Perimeter_ZN_1 Thermal Zone"
   ..
```

**Purpose**: Groups spaces with same HVAC control
**Hierarchy**: Top-level, referenced by Spc elements
**Reference Pattern**: Name-based (from `Spc.ThrmlZnRef`)

#### AirSys (Air System)
```
AirSys   "CoreZnPSZ AirSys"
   Type = "SZHP"
   CtrlZnRef = "Core_ZN Thermal Zone"
   ..
```

**Purpose**: HVAC air distribution system
**Hierarchy**: Top-level
**Contains**: AirSeg, CoilClg, CoilHtg, Fan, TrmlUnit, OACtrl
**Key Properties**:
- `Type` - "SZHP" (Single Zone Heat Pump), "SZAC" (Single Zone AC), etc.
- `CtrlZnRef` - Controlling thermal zone (name-based)
- `TreeState` - UI expansion state

#### AirSeg (Air Segment)
```
AirSeg   "CoreZnSysSupply AirSeg"
   Type = "Supply"
   ..
```

**Hierarchy**: Child of AirSys
**Purpose**: Supply or return air path
**Key Properties**:
- `Type` - "Supply" or "Return"

#### ZnSys (Zone System)
```
ZnSys   "KitchenExhaust"
   TreeState = 253
   Type = "Exhaust"
   ExhSysType = "CommercialKitchen"
   FullyDuctedExhFlag = 0
   ExhFiltersFlag = 0
   BiosftyCabExhFlag = 0
   ..
```

**Purpose**: Zone-level HVAC systems (exhaust, ventilation)
**Hierarchy**: Top-level
**Contains**: Fan
**Key Properties**:
- `Type` - "Exhaust", "Ventilation"
- `ExhSysType` - "CommercialKitchen", etc.
- Flags for system characteristics (0/1)

#### TrmlUnit (Terminal Unit)
```
TrmlUnit   "CoreZn TU"
   Type = "Uncontrolled"
   ..
```

**Hierarchy**: Child of AirSys
**Purpose**: Zone terminal equipment
**Key Properties**:
- `Type` - "Uncontrolled", "VAV", "SeriesFanPowered", etc.

#### OACtrl (Outside Air Control)
```
OACtrl   "CoreZnOAControl"
   AirSegSupRef = "CoreZnSysSupply AirSeg"
   AirSegRetRef = "CoreZnSysReturnAirSeg"
   ..
```

**Hierarchy**: Child of AirSys
**Purpose**: Ventilation and economizer control
**Key Properties**:
- `AirSegSupRef` - Supply air segment reference (name-based)
- `AirSegRetRef` - Return air segment reference (name-based)

#### HtRcvry (Heat Recovery)
```
HtRcvry   "BulkStorage_HtRcvry"
   ..
```

**Hierarchy**: Child of AirSys
**Purpose**: Energy recovery ventilator

---

### HVAC Equipment

#### CoilClg (Cooling Coil)
```
CoilClg   "CoreZnCoolingCoil"
   Type = "DirectExpansion"
   ..
```

**Hierarchy**: Child of AirSys
**Key Properties**:
- `Type` - "DirectExpansion", "ChilledWater", etc.

#### CoilHtg (Heating Coil)
```
CoilHtg   "CoreZnHeatingCoil"
   Type = "HeatPump"
   HtPumpSuppCoilHtgRef = "CoreZnSupplyHeatingCoil"
   ..
```

**Hierarchy**: Child of AirSys
**Key Properties**:
- `Type` - "HeatPump", "HotWater", "Resistance", "Furnace"
- `HtPumpSuppCoilHtgRef` - Supplemental heating coil reference (name-based)

#### Fan
```
Fan   "CoreZnSupplyFan"
   ..
```

**Hierarchy**: Child of AirSys or ZnSys
**Purpose**: Air moving equipment
**Key Properties**:
- `ModelingMthd` - "StaticPressure", etc.

---

### DHW (Domestic Hot Water)

#### FluidSys (Fluid System)
```
FluidSys   "SHWFluidSysElec"
   Type = "ServiceHotWater"
   ..
```

**Purpose**: Service hot water system
**Hierarchy**: Top-level
**Contains**: FluidSeg, WtrHtr
**Key Properties**:
- `Type` - "ServiceHotWater"

#### FluidSeg (Fluid Segment)
```
FluidSeg   "SHWSupplyElec"
   Type = "PrimarySupply"
   ..

FluidSeg   "SHWMakeupElec"
   Type = "MakeupFluid"
   Src = "MunicipalWater"
   ..
```

**Hierarchy**: Child of FluidSys
**Purpose**: Supply or makeup water segment
**Key Properties**:
- `Type` - "PrimarySupply" or "MakeupFluid"
- `Src` - "MunicipalWater" (for makeup)

#### WtrHtr (Water Heater)
```
WtrHtr   "WaterHeaterElec"
   FluidSegOutRef = "SHWSupplyElec"
   FluidSegMakeupRef = "SHWMakeupElec"
   StorCap = 29.991
   UEF = 0.9217
   RE = 0.99
   FirstHrRating = 60
   FuelSrc = "Electricity"
   InpPwr = 8.74173
   ..
```

**Hierarchy**: Child of FluidSys
**Key Properties**:
- `FluidSegOutRef` - Output fluid segment (name-based)
- `FluidSegMakeupRef` - Makeup fluid segment (name-based)
- `StorCap` - Storage capacity (gallons)
- `UEF` - Uniform Energy Factor
- `RE` - Recovery Efficiency
- `FirstHrRating` - First hour rating (gallons)
- `FuelSrc` - "Electricity", "NaturalGas", "Propane"
- `InpPwr` - Input power (kW) or capacity (kBtu/hr)

---

### Renewable Energy & Storage

#### PVArray (Photovoltaic Array)
```
PVArray   "T24 PVArray"
   DCSysSize = 17.2214
   ..
```

**Purpose**: Solar PV system
**Hierarchy**: Top-level
**Key Properties**:
- `DCSysSize` - DC system size (kW)

**Note**: Simplified compared to CIBD22X (no inverter details, tilt, azimuth in this element)

#### Batt (Battery Storage)
```
Batt   "T24 Batt"
   MaxCap = 30.464
   Ctrl = "Time of Use"
   MaxChrgPwr = 7.616
   MaxDschrgPwr = 7.616
   ..
```

**Purpose**: Energy storage system
**Hierarchy**: Top-level
**Key Properties**:
- `MaxCap` - Maximum capacity (kWh)
- `Ctrl` - Control strategy ("Time of Use")
- `MaxChrgPwr` - Maximum charge power (kW)
- `MaxDschrgPwr` - Maximum discharge power (kW)

---

### Compliance & Results

#### EUseSummary (Energy Use Summary)
```
EUseSummary   "Metrics 2025 (Oct 2022)"
   Title1[2] = "Proposed Design"
   Title1[3] = "Proposed"
   Title1[4] = "Proposed"
   Title1[5] = "Standard Design"
   ...
```

**Purpose**: Compliance metrics and results table
**Hierarchy**: Top-level
**Key Properties**:
- Array properties with compliance report data

#### SpcFuncDefaults (Space Function Defaults)
```
SpcFuncDefaults   "Dining Area Defaults"
   SpcFunc = "Dining Area (Cafeteria/Fast Food)"
   VentPerArea = 0.15
   ..
```

**Purpose**: Default values for space types
**Hierarchy**: Top-level
**Key Properties**:
- `SpcFunc` - Space function type
- `VentPerArea` - Ventilation rate (CFM/ft²)

---

## Property Data Types

### Numeric Types
- **Integer**: `1`, `254`, `17`
- **Float**: `12219.7`, `0.22`, `0.34`
- **Scientific Notation**: `6.69906e-15`, `-2.76065e-16`

### String Types
- **Quoted Strings**: `"Small Office"`, `"Concrete - 140 lb/ft3 - 6 in."`
- **Unquoted Values**: Property values without spaces

### Coordinate Tuples
- **Format**: `Coord = ( X, Y, Z )`
- **Example**: `Coord = ( 74.4423, 16.4042, 0 )`

### Boolean/Flags
- **Values**: `0` (false), `1` (true)
- **Examples**: `AutoHardSize = 1`, `FullyDuctedExhFlag = 0`

### Array Properties
- **Format**: `PropertyName[Index] = Value`
- **Indexing**: **1-based** (starts at 1, not 0)
- **Example**: `MatRef[1]`, `MatRef[2]`, `MatRef[3]`

---

## Reference Patterns

### Name-Based References
**All references in CIBD25 appear to be name-based** (string matching)

Examples:
- `ThrmlZnRef = "Perimeter_ZN_1 Thermal Zone"`
- `ConsAssmRef = "Base_CZ12-NonresMetalFrameWallU055"`
- `FenConsRef = "Base_AllCZ_FixedWindowU34"`
- `MatRef[1] = "Stucco - 7/8 in."`
- `AdjacentSpcRef = "Perimeter_ZN_2"`
- `FluidSegOutRef = "SHWSupplyElec"`

**No ID-based references observed** (unlike CIBD22X which has both)

---

## Hierarchy Patterns

### Building Structure
```
Bldg
└── Story
    └── Spc
        ├── ExtWall
        │   ├── PolyLp → CartesianPt (multiple)
        │   ├── Win
        │   │   └── PolyLp → CartesianPt (multiple)
        │   └── Dr
        │       └── PolyLp → CartesianPt (multiple)
        ├── IntWall
        │   └── PolyLp → CartesianPt (multiple)
        ├── Roof
        │   ├── PolyLp → CartesianPt (multiple)
        │   └── Skylt
        │       └── PolyLp → CartesianPt (multiple)
        └── UndgrFlr
            └── PolyLp → CartesianPt (multiple)
```

### HVAC Structure
```
AirSys
├── AirSeg (Supply)
├── AirSeg (Return)
├── CoilClg
├── CoilHtg
├── CoilHtg (supplemental)
├── Fan
├── TrmlUnit
├── OACtrl
└── HtRcvry

ZnSys
└── Fan
```

### DHW Structure
```
FluidSys
├── FluidSeg (PrimarySupply)
├── FluidSeg (MakeupFluid)
└── WtrHtr
```

---

## Comparison with CIBD22X

### Element Name Mapping

| CIBD25 Type | CIBD22X Type | Notes |
|-------------|--------------|-------|
| `Proj` | `<ResProj>` | Same concept, different names |
| `ProjVar` | (properties in ResProj) | Separated in CIBD25 |
| `Bldg` | `<SDDXML>` root | Top-level container |
| `Story` | `<Story>` | Same |
| `Spc` | `<ResZn>` | Zone → Space naming |
| `Mat` | `<ResMat>` or `<Mat>` | Catalog materials |
| `ConsAssm` | `<ResCons>` | Construction assembly |
| `FenCons` | `<ResWinType>` | Window construction |
| `DrCons` | `<DrType>` | Door construction |
| `ExtWall` | `<ResExtWall>` | Exterior wall |
| `IntWall` | `<ResIntWall>` | Interior wall |
| `Roof` | `<ResRoof>` | Roof |
| `UndgrFlr` | `<ResUndgrFlr>` | Underground floor |
| `ExtFlr` | `<ResExtFlr>` | Exterior floor |
| `IntFlr` | `<ResIntFlr>` | Interior floor |
| `Win` | `<ResWin>` | Window |
| `Skylt` | `<Skylt>` | Skylight |
| `Dr` | `<Dr>` | Door |
| `PolyLp` | `<PolyLp>` | Polygon loop |
| `CartesianPt` | `<CartesianPt>` | 3D point |
| `ThrmlZn` | `<ThrmlZn>` | Thermal zone |
| `AirSys` | `<AirSys>` | Air system |
| `AirSeg` | `<AirSeg>` | Air segment |
| `ZnSys` | `<ZnSys>` | Zone system |
| `TrmlUnit` | `<TrmlUnit>` | Terminal unit |
| `OACtrl` | `<OACtrl>` | Outside air control |
| `HtRcvry` | `<HtRcvry>` | Heat recovery |
| `CoilClg` | `<CoilClg>` | Cooling coil |
| `CoilHtg` | `<CoilHtg>` | Heating coil |
| `Fan` | `<Fan>` | Fan |
| `FluidSys` | `<FluidSys>` | Fluid system |
| `FluidSeg` | `<FluidSeg>` | Fluid segment |
| `WtrHtr` | `<WtrHtr>` | Water heater |
| `PVArray` | `<ResPVSys>` | PV system (simplified) |
| `Batt` | `<Batt>` | Battery |
| `EUseSummary` | `<EUseSummary>` | Energy summary |
| `SpcFuncDefaults` | `<SpcFuncDefaults>` | Space defaults |

### Key Structural Differences

| Aspect | CIBD22X | CIBD25 |
|--------|---------|--------|
| **Format** | XML | Custom text |
| **Root Element** | `<SDDXML>` | `Bldg` |
| **Hierarchy** | XML nesting | Flat with references |
| **References** | ID-based and Name-based | Name-based only |
| **Array Indexing** | 0-based | 1-based |
| **Attributes** | XML attributes | Properties |
| **Namespace** | XML namespaces | None |

---

## Implementation Notes

### Parser Requirements
1. **Tokenizer**: Handle object declarations, properties, array properties, terminators
2. **Indentation Handling**: 3-space indentation for properties
3. **Data Type Parsing**: String, numeric, boolean, coordinate tuples, arrays
4. **Reference Resolution**: All name-based (simpler than CIBD22X)
5. **Hierarchy Reconstruction**: Build parent-child relationships from flat structure

### Serializer Requirements
1. **Formatting**: Exact spacing (multiple spaces between type and name)
2. **Indentation**: 3 spaces for properties
3. **Array Formatting**: 1-based indexing
4. **Terminator**: `..` on separate line with 3-space indent
5. **Line Endings**: CRLF (Windows)
6. **Encoding**: ISO-8859-1

---

**Status**: ✅ Complete Element Catalog
**Total Elements Documented**: 36 types
**Next Step**: Design CIBD25 adapter architecture
