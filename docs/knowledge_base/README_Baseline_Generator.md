# EM Core Tools Track – Baseline Generator

## Overview
`baseline_generator.py` creates a standardized baseline model using climate-zone-specific and building-type-specific prescriptive standards. It is core to generating Title 24 and ASHRAE 90.1 baseline models for performance comparison.

## Inputs
- `model_data.json`: A structured dictionary of proposed model inputs.
- `prescriptive_data.json`: A dictionary of code-standard parameters by climate zone and building type.

## Output
- A JSON dictionary representing the generated baseline scenario, including:
  - Envelope specs
  - HVAC system type
  - Lighting power density
  - Ventilation requirements
  - Water heating system

## Usage

```bash
python baseline_generator.py model_data.json prescriptive_data.json
```

## Example
For a CZ03 multifamily building, the output baseline might include:
```json
{
  "envelope": "R-13 walls, R-30 roof",
  "hvac": "Packaged RTU with economizer",
  "lighting": "0.75 W/ft²",
  "ventilation": "ASHRAE 62.1 default",
  "hot_water": "Gas boiler, 80% efficiency"
}
```

## Integration
This module supports:
- Scenario Manager
- Export pipelines (to EnergyPlus, IESVE, CBECC)
- GUI for baseline previewing

## Limitations
- Currently supports JSON input only
- No parametric overrides or GUI input support yet (planned for v0.5+)