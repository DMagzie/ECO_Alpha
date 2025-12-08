# LCCA Integration Plans for ECO Tools

This folder consolidates planning documents for Life Cycle Cost Analysis (LCCA) integration with the ECO_Alpha_v7 CBECC translation pipeline.

## Current Status

**ECO_Alpha_v7 CBECC Pipeline:** Production Ready
**LCCA Integration:** Planning Phase

## Prerequisites for LCCA

The LCCA workflow requires **simulation outputs** as inputs:

1. **Hourly Energy Consumption** - kWh electricity, therms gas
2. **Peak Demand** - kW for demand charges
3. **TDV Data** - Time Dependent Valuation (California Title 24)
4. **Utility Rate Structures** - TOU schedules, demand tiers

## Integration Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    ECO TOOLS WORKFLOW                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────┐     ┌──────────┐     ┌──────────┐                │
│  │ CIBD22X  │────▶│ EMJSON   │────▶│ CIBD25   │                │
│  │ Import   │     │ v6       │     │ Export   │                │
│  └──────────┘     └────┬─────┘     └────┬─────┘                │
│                        │                │                       │
│                        ▼                ▼                       │
│                   ┌─────────────────────────┐                   │
│                   │    CBECC Simulation     │                   │
│                   │    (External CLI)       │                   │
│                   └───────────┬─────────────┘                   │
│                               │                                 │
│                               ▼                                 │
│  ┌────────────────────────────────────────────────────────┐    │
│  │              SIMULATION OUTPUTS                         │    │
│  │  • Hourly CSV (8760 rows)                              │    │
│  │  • Annual Summary (kWh, therms, peak kW)               │    │
│  │  • TDV Results                                         │    │
│  └───────────────────────────┬────────────────────────────┘    │
│                              │                                  │
│                              ▼                                  │
│  ┌────────────────────────────────────────────────────────┐    │
│  │                 LCCA TRACK                              │    │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │    │
│  │  │ Energy Costs │  │ System Costs │  │ Incentives   │  │    │
│  │  │ (from sim)   │  │ (from CostDB)│  │ (rules eng)  │  │    │
│  │  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘  │    │
│  │         │                 │                 │          │    │
│  │         └────────────────┬┴─────────────────┘          │    │
│  │                          ▼                             │    │
│  │              ┌───────────────────┐                     │    │
│  │              │  LCCA Calculator  │                     │    │
│  │              │  NPV, IRR, SIR    │                     │    │
│  │              └─────────┬─────────┘                     │    │
│  │                        │                               │    │
│  │         ┌──────────────┼──────────────┐               │    │
│  │         ▼              ▼              ▼               │    │
│  │   ┌──────────┐  ┌──────────┐  ┌──────────┐           │    │
│  │   │ ECON-1   │  │ Excel    │  │ ESG      │           │    │
│  │   │ PDF      │  │ Dashboard│  │ Report   │           │    │
│  │   └──────────┘  └──────────┘  └──────────┘           │    │
│  └────────────────────────────────────────────────────────┘    │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

## Folder Contents

```
LCCA_Plans/
├── README.md                     # This file
├── docs/
│   ├── CHANGELOG_CONSOLIDATED.md # Combined history from all LCCA work
│   ├── SIMULATION_REQUIREMENTS.md# What simulation outputs LCCA needs
│   └── INTEGRATION_ROADMAP.md    # Step-by-step integration plan
├── reference/
│   └── existing_lcca_code.md     # Inventory of existing LCCA code
└── schemas/
    └── lcca_scenario_schema.md   # LCCA data model documentation
```

## Next Steps

1. **Simulation Track** - Parse CBECC hourly outputs into standardized format
2. **Cost Database** - Structure CostDB for automated system cost lookups
3. **LCCA Core** - Port calculators (NPV, IRR, payback) into eco_tools
4. **Deliverables** - ECON-1 PDF, Excel dashboard, ESG report

## Related Locations

| Location | Contents |
|----------|----------|
| `EM_Projects/v5 Other/lcca_track/` | Primary scaffold with calculators |
| `EM-Tools/v0.4/LCCA_Track/` | v0.04 planning (empty scaffold) |
| `Documents/SNO/lcca/` | Working ECON-1 generator |
| `Deliverables/LCCA/` | v0.02 changelog |
