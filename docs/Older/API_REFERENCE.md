# ECO_Alpha v7 - API Reference

**Version**: 7.0.0
**Date**: November 11, 2025
**Status**: Production Ready

---

## Table of Contents

1. [Simulation Module](#simulation-module)
2. [Visualization Module](#visualization-module)
3. [Reporting Module](#reporting-module)
4. [Translation Module](#translation-module)
5. [Core Data Structures](#core-data-structures)

---

## Simulation Module

### CBECC Results Parser

**Module**: `eco_tools.simulation.cbecc_results_parser`

#### Class: `CBECCResultsParser`

Parses CBECC-Com AnalysisResults.xml files to extract Title 24 compliance and energy metrics.

##### Constructor

```python
CBECCResultsParser(xml_file: str)
```

**Parameters**:
- `xml_file` (str): Path to CBECC-Com AnalysisResults.xml file

**Example**:
```python
from eco_tools.simulation.cbecc_results_parser import CBECCResultsParser

parser = CBECCResultsParser("model - AnalysisResults.xml")
results = parser.parse()
```

##### Method: `parse()`

```python
def parse() -> Dict[str, Any]
```

Parse the XML file and extract all available metrics.

**Returns**: Dictionary with the following keys:
- `status` (str): "success" or "error"
- `xml_file` (str): Path to parsed file
- `project_name` (str): Project name from CBECC model
- `climate_zone` (str): California climate zone (e.g., "CZ12")
- `weather_station` (str): Weather station name
- `building_area` (float): Conditioned floor area in sqft
- `compliance_status` (str): "Pass", "Fail", or "Unknown"
- `proposed_tdv` (float): Proposed design TDV (kBtu/ft²/yr)
- `standard_tdv` (float): Standard design TDV (kBtu/ft²/yr)
- `compliance_margin` (float): Percentage better/worse than standard
- `end_uses` (Dict[str, float]): Energy end uses (kBtu/ft²/yr)
- `end_use_categories` (List[str]): List of end use category names

**Example**:
```python
results = parser.parse()

if results["status"] == "success":
    print(f"Project: {results['project_name']}")
    print(f"Climate Zone: {results['climate_zone']}")
    print(f"Compliance: {results['compliance_status']}")
    print(f"TDV Margin: {results['compliance_margin']:.1f}%")

    for use, value in results["end_uses"].items():
        print(f"  {use}: {value:.2f} kBtu/ft²/yr")
```

##### Method: `compare_with_energyplus()`

```python
def compare_with_energyplus(energyplus_result: Dict[str, Any]) -> Dict[str, Any]
```

Compare CBECC results with EnergyPlus results.

**Parameters**:
- `energyplus_result` (Dict): Result dictionary from EnergyPlus simulation

**Returns**: Dictionary with comparison metrics:
- `cbecc` (Dict): CBECC summary metrics
- `energyplus` (Dict): EnergyPlus summary metrics
- `comparison` (Dict): Delta calculations and agreement assessment

**Example**:
```python
ep_results = {...}  # From EnergyPlus simulation
comparison = parser.compare_with_energyplus(ep_results)

print(f"Agreement: {comparison['comparison']['agreement']}")
print(f"EUI Delta: {comparison['comparison']['eui_delta']:.2f} kBtu/ft²/yr")
```

#### Function: `extract_compliance_summary()`

```python
def extract_compliance_summary(xml_file: str) -> Dict[str, Any]
```

Quick extraction of compliance summary without full parsing.

**Parameters**:
- `xml_file` (str): Path to AnalysisResults.xml

**Returns**: Dictionary with basic compliance info:
- `project_name` (str)
- `climate_zone` (str)
- `building_area` (float)
- `compliance_status` (str)
- `software_version` (str)

**Example**:
```python
from eco_tools.simulation.cbecc_results_parser import extract_compliance_summary

summary = extract_compliance_summary("model - AnalysisResults.xml")
print(f"{summary['project_name']}: {summary['compliance_status']}")
```

---

### EnergyPlus Runner

**Module**: `eco_tools.simulation.energyplus_runner`

#### Class: `EnergyPlusRunner`

Runs EnergyPlus simulations via Honeybee-Energy.

##### Constructor

```python
EnergyPlusRunner(model: Dict[str, Any])
```

**Parameters**:
- `model` (Dict): EMJSON model dictionary

##### Method: `run_simulation()`

```python
def run_simulation(
    epw_file: str,
    output_dir: Optional[str] = None,
    run_period: Optional[Dict[str, int]] = None
) -> Dict[str, Any]
```

Run EnergyPlus simulation and parse results.

**Parameters**:
- `epw_file` (str): Path to EnergyPlus Weather file
- `output_dir` (str, optional): Output directory path
- `run_period` (Dict, optional): Run period specification

**Returns**: Dictionary with simulation results:
- `status` (str): "success" or "error"
- `eui` (float): Energy Use Intensity (kBtu/ft²/yr)
- `total_energy_kwh` (float): Total site energy (kWh)
- `building_area_m2` (float): Building area (m²)
- `end_uses` (Dict[str, float]): Energy end uses
- `errors` (List[str]): Error messages
- `warnings` (List[str]): Warning messages

**Example**:
```python
from eco_tools.simulation.energyplus_runner import EnergyPlusRunner

runner = EnergyPlusRunner(model)
results = runner.run_simulation(
    epw_file="USA_CA_Sacramento.epw",
    output_dir="test_output/energyplus"
)

if results["status"] == "success":
    print(f"EUI: {results['eui']:.1f} kBtu/ft²/yr")
    print(f"Total Energy: {results['total_energy_kwh']:,.0f} kWh")
```

---

## Visualization Module

**Module**: `eco_tools.visualization.charts`

### Function: `create_end_use_comparison_chart()`

```python
def create_end_use_comparison_chart(
    cbecc_end_uses: Dict[str, float],
    energyplus_end_uses: Dict[str, float],
    title: str = "Energy End Use Comparison"
) -> go.Figure
```

Create side-by-side bar chart comparing CBECC and EnergyPlus end uses.

**Parameters**:
- `cbecc_end_uses` (Dict): CBECC end use values (kBtu/ft²/yr)
- `energyplus_end_uses` (Dict): EnergyPlus end use values
- `title` (str): Chart title

**Returns**: Plotly Figure object

**Color Scheme**:
- CBECC: `#4A90E2` (blue)
- EnergyPlus: `#50C878` (green)

**Example**:
```python
from eco_tools.visualization.charts import create_end_use_comparison_chart

cbecc = {"space_heating": 10.5, "space_cooling": 15.2}
ep = {"space_heating": 11.2, "space_cooling": 14.8}

fig = create_end_use_comparison_chart(cbecc, ep)

# In Streamlit
import streamlit as st
st.plotly_chart(fig, use_container_width=True)

# Standalone
fig.show()
```

---

### Function: `create_delta_chart()`

```python
def create_delta_chart(
    cbecc_end_uses: Dict[str, float],
    energyplus_end_uses: Dict[str, float],
    title: str = "Energy Delta (EnergyPlus - CBECC)"
) -> go.Figure
```

Create bar chart showing difference between EnergyPlus and CBECC values.

**Parameters**:
- `cbecc_end_uses` (Dict): CBECC end use values
- `energyplus_end_uses` (Dict): EnergyPlus end use values
- `title` (str): Chart title

**Returns**: Plotly Figure with color-coded deltas:
- Positive delta (EnergyPlus > CBECC): Red
- Negative delta (EnergyPlus < CBECC): Green

**Example**:
```python
from eco_tools.visualization.charts import create_delta_chart

fig = create_delta_chart(cbecc_end_uses, ep_end_uses)
st.plotly_chart(fig)
```

---

### Function: `create_compliance_gauge()`

```python
def create_compliance_gauge(
    compliance_margin: float,
    proposed_tdv: Optional[float] = None,
    standard_tdv: Optional[float] = None,
    title: str = "Title 24 Compliance Margin"
) -> go.Figure
```

Create gauge chart showing Title 24 compliance margin.

**Parameters**:
- `compliance_margin` (float): Percentage better/worse than standard
- `proposed_tdv` (float, optional): Proposed TDV value
- `standard_tdv` (float, optional): Standard TDV value
- `title` (str): Chart title

**Returns**: Plotly gauge Figure

**Zones**:
- Red: -20% to 0% (non-compliant)
- Yellow: 0% to 10% (marginally compliant)
- Green: 10% to 30% (good compliance)

**Example**:
```python
from eco_tools.visualization.charts import create_compliance_gauge

fig = create_compliance_gauge(
    compliance_margin=12.5,
    proposed_tdv=250000.0,
    standard_tdv=280000.0
)
st.plotly_chart(fig)
```

---

### Function: `create_total_energy_pie()`

```python
def create_total_energy_pie(
    end_uses: Dict[str, float],
    title: str = "Energy End Use Breakdown"
) -> go.Figure
```

Create pie chart (donut chart) showing energy end use breakdown.

**Parameters**:
- `end_uses` (Dict): End use values
- `title` (str): Chart title

**Returns**: Plotly pie chart Figure (30% hole for donut effect)

**Example**:
```python
from eco_tools.visualization.charts import create_total_energy_pie

fig = create_total_energy_pie(cbecc_end_uses, title="CBECC Energy Breakdown")
st.plotly_chart(fig)
```

---

## Reporting Module

**Module**: `eco_tools.reporting.csv_exporter`

### Function: `export_cbecc_results_to_csv()`

```python
def export_cbecc_results_to_csv(
    results: Dict[str, Any],
    output_file: str
) -> None
```

Export CBECC results to CSV format.

**Parameters**:
- `results` (Dict): Parsed CBECC results from `CBECCResultsParser.parse()`
- `output_file` (str): Output CSV file path

**CSV Structure**:
1. Metadata section (title, timestamp)
2. Project Information section
3. Title 24 Compliance section
4. Energy End Uses section

**Example**:
```python
from eco_tools.reporting.csv_exporter import export_cbecc_results_to_csv

parser = CBECCResultsParser("model.xml")
results = parser.parse()

export_cbecc_results_to_csv(results, "cbecc_results.csv")
print("✅ Exported to cbecc_results.csv")
```

---

### Function: `export_energyplus_results_to_csv()`

```python
def export_energyplus_results_to_csv(
    results: Dict[str, Any],
    output_file: str
) -> None
```

Export EnergyPlus results to CSV format.

**Parameters**:
- `results` (Dict): EnergyPlus simulation results
- `output_file` (str): Output CSV file path

**CSV Structure**:
1. Metadata section
2. Summary Metrics (EUI, total energy)
3. Energy End Uses
4. Errors and Warnings (if any)

**Example**:
```python
from eco_tools.reporting.csv_exporter import export_energyplus_results_to_csv

runner = EnergyPlusRunner(model)
results = runner.run_simulation(epw_file)

export_energyplus_results_to_csv(results, "energyplus_results.csv")
```

---

### Function: `export_comparison_to_csv()`

```python
def export_comparison_to_csv(
    cbecc_results: Dict[str, Any],
    energyplus_results: Dict[str, Any],
    output_file: str
) -> None
```

Export side-by-side comparison of CBECC and EnergyPlus results.

**Parameters**:
- `cbecc_results` (Dict): CBECC parsed results
- `energyplus_results` (Dict): EnergyPlus simulation results
- `output_file` (str): Output CSV file path

**CSV Structure**:
1. Metadata section
2. Summary Comparison
3. End Use Comparison table with columns:
   - End Use name
   - CBECC value
   - EnergyPlus value
   - Delta (EnergyPlus - CBECC)
   - % Difference

**Example**:
```python
from eco_tools.reporting.csv_exporter import export_comparison_to_csv

export_comparison_to_csv(
    cbecc_results,
    energyplus_results,
    "comparison.csv"
)
```

---

## Translation Module

**Module**: `eco_tools.translators.cibd22x`

### CIBD22X Adapter

#### Function: `export_to_cibd22x()`

```python
def export_to_cibd22x(
    model: Dict[str, Any],
    output_file: str
) -> None
```

Export EMJSON model to CBECC-Com CIBD22X format.

**Parameters**:
- `model` (Dict): EMJSON internal representation
- `output_file` (str): Output .cibd22x file path

**Example**:
```python
from eco_tools.translators.cibd22x import export_to_cibd22x

# Assuming model is loaded from import
export_to_cibd22x(model, "output_model.cibd22x")
```

---

#### Function: `import_from_cibd22x()`

```python
def import_from_cibd22x(
    input_file: str
) -> Dict[str, Any]
```

Import CIBD22X file to EMJSON internal representation.

**Parameters**:
- `input_file` (str): Path to .cibd22x file

**Returns**: EMJSON model dictionary

**Example**:
```python
from eco_tools.translators.cibd22x import import_from_cibd22x

model = import_from_cibd22x("input_model.cibd22x")
print(f"Loaded {len(model.get('spaces', []))} spaces")
```

---

### HBJSON Adapter

**Module**: `eco_tools.translators.hbjson`

#### Function: `export_to_hbjson()`

```python
def export_to_hbjson(
    model: Dict[str, Any],
    output_file: str
) -> None
```

Export EMJSON model to Honeybee JSON format.

**Parameters**:
- `model` (Dict): EMJSON internal representation
- `output_file` (str): Output .hbjson file path

**Example**:
```python
from eco_tools.translators.hbjson import export_to_hbjson

export_to_hbjson(model, "model.hbjson")
```

---

#### Function: `import_from_hbjson()`

```python
def import_from_hbjson(
    input_file: str
) -> Dict[str, Any]
```

Import HBJSON file to EMJSON internal representation.

**Parameters**:
- `input_file` (str): Path to .hbjson file

**Returns**: EMJSON model dictionary

**Example**:
```python
from eco_tools.translators.hbjson import import_from_hbjson

model = import_from_hbjson("model.hbjson")
```

---

## Core Data Structures

### EMJSON Internal Representation

The internal model format used throughout ECO_Alpha v7.

```python
{
    "project": {
        "name": str,
        "building_type": str,
        "climate_zone": str,
        "weather_station": str
    },
    "building": {
        "area": float,  # sqft
        "stories": int,
        "orientation": float  # degrees
    },
    "spaces": [
        {
            "name": str,
            "type": str,
            "area": float,
            "volume": float,
            "geometry": {
                "vertices": [[x, y, z], ...],
                "height": float
            },
            "surfaces": [
                {
                    "type": str,  # "Wall", "Floor", "Ceiling", "Window", "Door"
                    "area": float,
                    "vertices": [[x, y, z], ...],
                    "construction": str,
                    "adjacency": str  # Adjacent space name (optional)
                }
            ]
        }
    ],
    "hvac_systems": [
        {
            "name": str,
            "type": str,
            "zones": [str],  # Space names served
            "efficiency": float
        }
    ],
    "constructions": {
        "walls": {...},
        "floors": {...},
        "roofs": {...},
        "windows": {...}
    },
    "schedules": {
        "occupancy": {...},
        "lighting": {...},
        "equipment": {...}
    }
}
```

---

### CBECC Results Dictionary

Returned by `CBECCResultsParser.parse()`:

```python
{
    "status": "success",
    "xml_file": str,
    "project_name": str,
    "climate_zone": str,  # "CZ12"
    "weather_station": str,
    "building_area": float,  # sqft
    "compliance_status": str,  # "Pass", "Fail", "Unknown"
    "proposed_tdv": float,  # kBtu/ft²/yr
    "standard_tdv": float,
    "compliance_margin": float,  # percentage
    "end_uses": {
        "space_heating": float,
        "space_cooling": float,
        "indoor_fans": float,
        "indoor_lighting": float,
        "equipment": float,
        "dhw": float,
        "pumps": float,
        "heat_rejection": float
    },
    "end_use_categories": [str]
}
```

---

### EnergyPlus Results Dictionary

Returned by `EnergyPlusRunner.run_simulation()`:

```python
{
    "status": "success",
    "eui": float,  # kBtu/ft²/yr
    "total_energy_kwh": float,
    "building_area_m2": float,
    "end_uses": {
        "space_heating": float,
        "space_cooling": float,
        "indoor_fans": float,
        "indoor_lighting": float,
        "equipment": float,
        "dhw": float
    },
    "errors": [str],
    "warnings": [str]
}
```

---

## Common Workflows

### Complete Simulation Workflow

```python
from eco_tools.translators.cibd22x import import_from_cibd22x, export_to_cibd22x
from eco_tools.translators.hbjson import export_to_hbjson
from eco_tools.simulation.cbecc_results_parser import CBECCResultsParser
from eco_tools.simulation.energyplus_runner import EnergyPlusRunner
from eco_tools.visualization.charts import create_end_use_comparison_chart
from eco_tools.reporting.csv_exporter import export_comparison_to_csv

# 1. Import model
model = import_from_cibd22x("input.cibd22x")

# 2. Run CBECC simulation
export_to_cibd22x(model, "output.cibd22x")
# ... run CBECC externally ...
cbecc_parser = CBECCResultsParser("output - AnalysisResults.xml")
cbecc_results = cbecc_parser.parse()

# 3. Run EnergyPlus simulation
export_to_hbjson(model, "model.hbjson")
ep_runner = EnergyPlusRunner(model)
ep_results = ep_runner.run_simulation("weather.epw")

# 4. Visualize comparison
fig = create_end_use_comparison_chart(
    cbecc_results["end_uses"],
    ep_results["end_uses"]
)
fig.show()

# 5. Export results
export_comparison_to_csv(cbecc_results, ep_results, "comparison.csv")
```

---

### Quick Compliance Check

```python
from eco_tools.simulation.cbecc_results_parser import extract_compliance_summary

summary = extract_compliance_summary("model - AnalysisResults.xml")
print(f"{summary['project_name']}: {summary['compliance_status']}")
print(f"Climate Zone: {summary['climate_zone']}")
print(f"Building Area: {summary['building_area']:,.0f} sqft")
```

---

### Custom Visualization

```python
from eco_tools.visualization.charts import (
    create_compliance_gauge,
    create_total_energy_pie
)
import streamlit as st

# Compliance gauge
fig1 = create_compliance_gauge(
    compliance_margin=15.2,
    proposed_tdv=250000,
    standard_tdv=290000
)
st.plotly_chart(fig1)

# Energy breakdown
fig2 = create_total_energy_pie(
    end_uses=cbecc_results["end_uses"],
    title="CBECC Energy Distribution"
)
st.plotly_chart(fig2)
```

---

## Error Handling

All API functions handle errors gracefully and return error status in result dictionaries:

```python
results = parser.parse()

if results["status"] == "error":
    print(f"Error: {results['message']}")
else:
    # Process results
    pass
```

For simulation functions:

```python
results = runner.run_simulation(epw_file)

if results["status"] == "success":
    if results.get("warnings"):
        print("⚠️ Warnings:")
        for warning in results["warnings"]:
            print(f"  - {warning}")
else:
    print(f"❌ Simulation failed")
    for error in results.get("errors", []):
        print(f"  - {error}")
```

---

## Type Annotations

All modules use Python type hints for clarity:

```python
from typing import Dict, List, Optional, Any
import plotly.graph_objects as go

def create_chart(
    data: Dict[str, float],
    title: Optional[str] = None
) -> go.Figure:
    ...
```

---

## Version Compatibility

- **Python**: 3.11+
- **Streamlit**: 1.34.0+
- **Plotly**: 6.4.0+
- **Honeybee-Energy**: 1.106.0+
- **CBECC-Com**: 2022.1.0+
- **EnergyPlus**: 23.1+

---

## Additional Resources

- **User Guide**: `docs/USER_GUIDE.md`
- **Phase Documentation**: `docs/PHASE_*.md`
- **Source Code**: `eco_tools/` and `gui/`
- **Tests**: `tests/unit/` and `tests/integration/`

---

**End of API Reference**

For implementation examples and tutorials, see the User Guide.
