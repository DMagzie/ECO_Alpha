# Ventura & 7th Equipment Cost Analysis

## Overview

Cost analysis for three HVAC/ventilation scenarios at the Ventura & 7th Apartments project.

**Project Details:**
- 40 dwelling units (12x1BR, 14x2BR, 14x3BR)
- Climate Zone 13 (Fresno, CA)
- All-electric building with 302 kWdc PV
- Master-metered with VNEM2 allocation

---

## Scenario Configurations

| Scenario | Packaged Units/DU | Ventilation | Heat Recovery |
|----------|------------------|-------------|---------------|
| **Baseline (Maestro)** | 1x Maestro Pro 12 HP | Central supply | None |
| **Ephoca + Maestros** | 1x Ephoca w/ERV + 1x Maestro | Individual ERV | 67% SRE |
| **Ephoca Min** | 1x Ephoca w/ERV | Individual ERV | 67% SRE |

---

## Equipment Pricing

### Maestro Olimpia Pro 12 HP

| Item | Price | Notes |
|------|-------|-------|
| MSRP | $6,748.65 | List price |
| **Discounted** | **$4,799.00** | Current market (Dec 2024) |

- Type: Room Heat Pump (non-central)
- Capacity: 12,000 BTU heating/cooling
- Through-wall installation, no external condenser

**Source:** [Mini Split Systems Direct](https://minisplitsystemsdirect.com/products/olimpia-splendid-maestro-pro-12-hp-inverter-12000-btu-pthp-heat-pump-wall-unit)

---

### Ephoca AIO Wall Mount Pro

| Configuration | Price | Notes |
|--------------|-------|-------|
| Base Unit (HP only) | $4,188 | Heat pump without ERV |
| **With ERV Module** | **$6,605** | Integrated HP + ERV |
| ERV Premium | $2,417 | Additional for ERV |

- Type: Packaged Terminal Heat Pump (PTHP)
- Integrated ERV: 35-70 CFM per unit size
- Heat Recovery: 67% SRE / 72% ASRE
- Through-wall installation

**Source:** [Green Building Advisor - All-in-One Heat Pumps](https://www.greenbuildingadvisor.com/article/all-in-one-heat-pumps)

---

### Central Supply Ventilation System

| Component | Cost | Notes |
|-----------|------|-------|
| Supply fan(s) | $4,000 | Building-level |
| Ductwork | $12,000 | Risers + branch ducts |
| Registers | $2,000 | 40 units @ $50 each |
| Controls | $2,000 | Demand control |
| Installation | $10,000 | Labor |
| **Total System** | **$30,000** | |
| **Per Unit Allocation** | **$750** | $30,000 ÷ 40 units |

---

### Installation Labor (Per Packaged Unit)

| Work Type | Cost | Notes |
|-----------|------|-------|
| Wall penetration | $150-250 | Core/sleeve |
| Unit mounting | $150-250 | Structural support |
| Sealing/flashing | $100-150 | Weather barrier |
| Electrical circuit | $350-500 | 208/230V, 20A |
| Commissioning | $50-100 | Startup/testing |
| **Total per Unit** | **$800-1,250** | |
| **Used for Analysis** | **$875** | Midpoint estimate |

---

## Scenario Cost Breakdown

### Baseline (Maestro + Central Ventilation)

| Item | Qty | Unit Cost | Total |
|------|-----|-----------|-------|
| Maestro Pro 12 HP | 40 | $4,799 | $191,960 |
| Installation (per unit) | 40 | $875 | $35,000 |
| Central Ventilation | 1 | $30,000 | $30,000 |
| **Baseline Total** | | | **$256,960** |
| **Per Unit** | | | **$6,424** |

---

### Ephoca + Maestros (Dual System, No Central Vent)

| Item | Qty | Unit Cost | Total |
|------|-----|-----------|-------|
| Ephoca w/ERV | 40 | $6,605 | $264,200 |
| Maestro Pro 12 HP | 40 | $4,799 | $191,960 |
| Installation (Ephoca) | 40 | $875 | $35,000 |
| Installation (Maestro) | 40 | $875 | $35,000 |
| Central Ventilation | 0 | — | $0 |
| **Total** | | | **$526,160** |
| **Per Unit** | | | **$13,154** |

**Incremental vs Baseline:**
| | Per Unit | 40 Units |
|-|----------|----------|
| **Delta** | +$6,730 | **+$269,200** |

---

### Ephoca Min (Single System, No Central Vent)

| Item | Qty | Unit Cost | Total |
|------|-----|-----------|-------|
| Ephoca w/ERV | 40 | $6,605 | $264,200 |
| Installation | 40 | $875 | $35,000 |
| Central Ventilation | 0 | — | $0 |
| **Total** | | | **$299,200** |
| **Per Unit** | | | **$7,480** |

**Incremental vs Baseline:**
| | Per Unit | 40 Units |
|-|----------|----------|
| **Delta** | +$1,056 | **+$42,240** |

---

## Cost Summary

| Scenario | Total CapEx | Per Unit | Delta vs Baseline |
|----------|-------------|----------|-------------------|
| Baseline (Maestro) | $256,960 | $6,424 | — |
| Ephoca Min | $299,200 | $7,480 | **+$42,240** |
| Ephoca + Maestros | $526,160 | $13,154 | **+$269,200** |

---

## Annual Operating Cost Considerations

### Maintenance

| Item | Baseline | Ephoca Min | Ephoca + Maestros |
|------|----------|------------|-------------------|
| Filter replacement | $20/unit | $60/unit* | $80/unit* |
| Central vent maintenance | $500/year | $0 | $0 |
| Equipment service | $50/unit | $50/unit | $100/unit |
| **Annual Total** | **$3,300** | **$4,400** | **$7,700** |

*ERV filters require more frequent replacement (~$40/unit/year additional)

### Energy Costs

Energy cost differences depend on:
1. Heat recovery efficiency (67% SRE reduces heating/cooling load)
2. Equipment COP/EER ratings
3. Fan energy (individual ERV vs central supply)

**Expected savings from heat recovery in CZ13:**
- Heating: 15-25% reduction
- Cooling: 10-20% reduction (pre-conditioning OA)

---

## Simple Payback Analysis Framework

| Scenario | Incremental CapEx | Required Annual Savings | Notes |
|----------|------------------|------------------------|-------|
| Ephoca Min | $42,240 | ~$2,800/year for 15-yr payback | Heat recovery + efficiency |
| Ephoca + Maestros | $269,200 | ~$18,000/year for 15-yr payback | Unlikely to achieve |

**Preliminary Assessment:**
- **Ephoca Min** is the cost-effective upgrade path
- **Ephoca + Maestros** requires extraordinary energy savings to justify

---

## Data Sources

1. **Mini Split Systems Direct** - Maestro Pro 12 HP pricing
   - https://minisplitsystemsdirect.com
   - Accessed: December 2024

2. **Green Building Advisor** - Ephoca AIO specifications and pricing
   - "All-in-One Heat Pumps" article
   - https://www.greenbuildingadvisor.com/article/all-in-one-heat-pumps

3. **HomeAdvisor / RS Means** - Installation labor estimates
   - Regional data for California multifamily

4. **ASHRAE 62.2** - Ventilation requirements
   - Heat recovery efficiency definitions (SRE, ASRE)

---

## Assumptions & Limitations

1. Equipment pricing as of December 2024; subject to change
2. Installation costs assume new construction (not retrofit)
3. Central ventilation estimate based on typical 4-story MF building
4. Maintenance costs are estimates; actual may vary by service contract
5. Energy savings require CBECC simulation to quantify
6. No utility rebates or incentives included in CapEx

---

*Document created: December 2024*
*Project: Ventura & 7th Apartments LCCA Analysis*
*Last updated: December 18, 2024*
