# 📘 Construction Cost Database Initiative

## 🎯 Purpose
To build a transparent and extensible backend database of construction costs used by the EM Tools LCCA Track. This database integrates multiple trusted sources and supports scenario-based cost modeling.

## 🧱 Core Components

- **System_Costs**: Cost per system type (HVAC, Envelope, etc.)
- **Material_Costs**: Material-level pricing by region and unit
- **Labor_Markups**: GC markup rates, escalation %, labor class types
- **Normalized_Costs**: Scenario-filtered $/unit or $/sf values
- **Source Tags**: Metadata tagging every entry with provenance

## 🔗 Tracked Sources (see cost_sources.csv)
- HUD Multifamily Construction Index
- NREL OpenStudio Cost Libraries
- CEC Cost Effectiveness Reports
- GSA Estimating Guides
- CalBEM IOU-sponsored cost models

## 📦 Output Files
- `CostDB_v0.05.xlsx`
- `cost_sources.csv`
- Public reference PDFs (if available)

## 📅 Update Plan
- Reviewed quarterly
- Updates tagged by version in both CSV and Excel outputs

## 🔒 Licensing
All sources tracked in `cost_sources.csv`. No proprietary data redistributed.
