# ESPM/BBC Integration Plan for ECO Alpha v7
## Integration with Energy Star Portfolio Manager & DOE Better Buildings Challenge

**Project**: ECO Tools Suite - Mercy Housing Integration  
**Target**: Alphav7 Streamlit Application  
**Timeline**: 12-16 weeks  
**Complexity**: Medium-High

---

## Executive Summary

This plan integrates ECO Alpha v7 with:
1. **Energy Star Portfolio Manager (ESPM)** - EPA's building benchmarking platform
2. **DOE Better Buildings Challenge (BBC)** - 20% energy reduction over 10 years
3. **DOE Better Climate Challenge (BCC)** - 50% GHG reduction over 10 years
4. **EnergyScoreCards** - Bright Power's utility analytics platform (optional)

The integration leverages Alphav7's existing architecture:
- **Streamlit GUI** for user interface
- **InternalRepresentation** for building data
- **LCCA Module** for energy and financial tracking
- **CBECC Integration** for simulation results

### Key Insight

Alphav7 is NOT a REST API application - it's a Streamlit-based GUI tool. Therefore, our integration strategy focuses on:
- Adding new Streamlit pages for ESPM/BBC management
- Creating Python service modules (not FastAPI endpoints)
- Exporting data for ESPM upload (not bi-directional sync)
- Building compliance reporting dashboards

---

## 1. Architecture Review: Key Findings

### Current State
```
ECO Alpha v7 (Streamlit Application)
├── Core Data: InternalRepresentation (23 element types)
├── GUI: 13 Streamlit pages
├── LCCA: ~6,000 lines of financial analysis
├── Simulation: CBECC-COM integration via Wine
└── Integrations: CBECC, Ladybug Tools, CUAC utility rates
```

### What's NOT There
- No EC3 integration (embodied carbon)
- No REopt integration (distributed energy)
- No REST API layer
- No ESPM connection
- No portfolio management beyond LCCA comparison

### Integration Approach

**NOT a microservice architecture** - We're adding:
1. New Python modules in `eco_tools/integrations/espm/`
2. New Streamlit pages in `gui/pages/`
3. Data export utilities
4. Reporting dashboards

---

## 2. ESPM Data Model Mapping

### ESPM Required Fields → InternalRepresentation Mapping

| ESPM Field | IR Source | Status |
|------------|-----------|--------|
| **Property Name** | `proj_metadata['name']` | ✅ Available |
| **Address** | `proj_metadata['address']` | ✅ Available |
| **Gross Floor Area** | Sum of `zone.floor_area_m2` | ✅ Calculated |
| **Year Built** | `proj_metadata['year_built']` | ⚠️  Add to metadata |
| **Building Type** | `zone.building_type` + `zone.space_function` | ✅ Available |
| **Occupancy** | `proj_metadata['occupancy']` | ⚠️  Add to metadata |
| **Operating Hours** | Not stored | ⚠️  Add to metadata |
| **Climate Zone** | CBECC climate zone | ✅ Available |

### ESPM Meter Data → LCCA HourlyEnergy Mapping

| ESPM Meter Type | LCCA Source | Status |
|-----------------|-------------|--------|
| **Electric - Grid** | `HourlyEnergy.elec_total_kwh` | ✅ Available |
| **Electric - On-Site Solar** | `HourlyEnergy.pv_generation_kwh` | ✅ Available |
| **Natural Gas** | `HourlyEnergy.gas_total_therm` | ✅ Available |
| **Electric - Battery** | `HourlyEnergy.battery_kwh` | ✅ Available |

### BBC/BCC Metrics → LCCA Mapping

| BBC/BCC Requirement | LCCA Source | Status |
|---------------------|-------------|--------|
| **Baseline EUI** | `annual.total_elec_kwh / area` | ✅ Available |
| **Current EUI** | Calculated from scenarios | ✅ Available |
| **% Reduction** | Scenario comparison | ✅ Available |
| **GHG Emissions** | `AnnualEnergySummary.co2_total` | ✅ Available |
| **Cost Savings** | `LccaResult.annual_savings` | ✅ Available |

---

## 3. Proposed Module Structure

```
eco_tools/
  integrations/
    espm/                          # NEW MODULE
      __init__.py
      espm_client.py               # ESPM API wrapper
      espm_mapper.py               # IR → ESPM data mapping
      espm_xml_builder.py          # ESPM XML Portfolio Manager format
      bbc_tracker.py               # BBC/BCC goal tracking
      espm_models.py               # ESPM Pydantic models
    
    energyscorecards/              # OPTIONAL
      esc_exporter.py              # Export to ESC format

gui/
  pages/
    portfolio_page.py              # NEW: Portfolio management
    espm_export_page.py            # NEW: ESPM data export
    bbc_dashboard_page.py          # NEW: BBC/BCC tracking
    compliance_page.py             # NEW: Compliance reporting
```

---

## 4. Phase 1: ESPM Data Models (Weeks 1-2)

### 4.1 ESPM Pydantic Models

**File**: `eco_tools/integrations/espm/espm_models.py`

```python
from pydantic import BaseModel, Field
from typing import Optional, List, Literal
from datetime import date

class ESPMProperty(BaseModel):
    """ESPM Property (Building) Definition"""
    # Required fields
    name: str
    address: str
    city: str
    state: str
    postal_code: str
    
    # Building characteristics
    gross_floor_area: float  # square feet
    year_built: int
    
    # Property use types (ESPM supports 80+ types)
    primary_use_type: str  # e.g., "Multifamily Housing", "Office"
    primary_use_area: float  # square feet
    
    # Secondary uses (for mixed-use)
    secondary_uses: List[dict] = []
    
    # Occupancy
    number_of_buildings: int = 1
    occupancy: float = 95.0  # percent
    
    # Operating characteristics
    weekly_operating_hours: float = 168.0
    number_of_workers: Optional[int] = None
    
    # Construction year
    construction_status: str = "Existing"


class ESPMMeter(BaseModel):
    """ESPM Meter Definition"""
    meter_id: str
    meter_name: str
    meter_type: Literal[
        "Electric - Grid",
        "Electric - on Site Solar",
        "Natural Gas",
        "Fuel Oil (No. 2)",
        "District Steam",
        "District Hot Water",
        "District Chilled Water"
    ]
    
    # Aggregation (for multi-tenant)
    is_bulk_meter: bool = False
    
    # Units
    units: str  # "kWh", "therms", "ccf", etc.
    
    # First bill date
    first_bill_date: date
    in_use: bool = True


class ESPMBillEntry(BaseModel):
    """Single meter reading (monthly bill)"""
    meter_id: str
    start_date: date
    end_date: date
    usage: float
    cost: Optional[float] = None
    demand: Optional[float] = None  # kW for electric
    
    # Estimation flag
    is_estimated: bool = False


class ESPMPropertyMetrics(BaseModel):
    """ESPM-calculated metrics (returned from API)"""
    property_id: str
    
    # ENERGY STAR Score (1-100)
    energy_star_score: Optional[int] = None
    
    # Site EUI
    site_eui: float  # kBtu/sf/year
    site_eui_wn: float  # Weather-normalized
    
    # Source EUI
    source_eui: float  # kBtu/sf/year
    source_eui_wn: float  # Weather-normalized
    
    # GHG Emissions
    total_ghg_emissions: float  # Metric Tons CO2e
    ghg_emissions_intensity: float  # kgCO2e/sf
    
    # National median comparison
    percent_better_than_median: Optional[float] = None
    
    # Ranking
    national_median_site_eui: Optional[float] = None
    national_median_source_eui: Optional[float] = None


class BBCGoal(BaseModel):
    """Better Buildings Challenge Goal Tracking"""
    organization_name: str
    commitment_date: date
    baseline_year: int
    target_year: int
    
    # Energy reduction goal
    energy_reduction_goal_pct: float = 20.0  # Default BBC goal
    
    # Baseline metrics
    baseline_eui: float  # kBtu/sf/year
    baseline_total_energy_mmbtu: float
    baseline_ghg_emissions_mt: float
    
    # Portfolio scope
    total_buildings: int
    total_square_feet: float
    
    # Goal type
    goal_type: Literal["BBC", "BCC", "Both"] = "BBC"
    
    # BCC-specific (if applicable)
    ghg_reduction_goal_pct: Optional[float] = 50.0


class BBCProgressReport(BaseModel):
    """Quarterly/Annual Progress Report"""
    report_date: date
    report_period: str  # "Q1 2024", "Annual 2023"
    
    # Current performance
    current_eui: float
    current_total_energy_mmbtu: float
    current_ghg_emissions_mt: float
    
    # Progress
    energy_reduction_achieved_pct: float
    ghg_reduction_achieved_pct: float
    
    # Status
    on_track: bool
    years_elapsed: float
    years_remaining: float
    
    # Implemented ECMs
    ecms_implemented: List[str] = []
    total_investment: float = 0.0
    verified_savings_mmbtu: float = 0.0
```

### 4.2 Data Mapper

**File**: `eco_tools/integrations/espm/espm_mapper.py`

```python
from typing import Dict, List, Optional
from eco_tools.core.internal_repr import InternalRepresentation
from eco_tools.lcca.model import SimulationOutput, LccaScenario
from .espm_models import ESPMProperty, ESPMMeter, ESPMBillEntry

class ESPMMapper:
    """Map InternalRepresentation to ESPM data structures"""
    
    # ESPM Property Type mapping
    SPACE_FUNCTION_TO_ESPM = {
        'Office': 'Office',
        'Retail': 'Retail Store',
        'Restaurant': 'Food Service',
        'School': 'K-12 School',
        'Warehouse': 'Warehouse',
        'Apartment': 'Multifamily Housing',
        'Hotel': 'Hotel',
        # Add all CBECC space functions
    }
    
    def __init__(self):
        pass
    
    def map_property(
        self, 
        model: InternalRepresentation,
        additional_metadata: Optional[Dict] = None
    ) -> ESPMProperty:
        """
        Convert InternalRepresentation to ESPM Property
        
        Args:
            model: Building model
            additional_metadata: User-supplied fields not in model
                - address, city, state, postal_code
                - year_built
                - occupancy
                - number_of_workers
        """
        # Calculate total area
        total_area_m2 = sum(z.floor_area_m2 or 0 for z in model.zones)
        total_area_sf = total_area_m2 * 10.764  # m2 to sf
        
        # Determine primary use
        primary_use, primary_area = self._determine_primary_use(model)
        
        # Get metadata
        meta = additional_metadata or {}
        proj_meta = model.proj_metadata or {}
        
        return ESPMProperty(
            name=proj_meta.get('name', 'Unnamed Building'),
            address=meta.get('address', ''),
            city=meta.get('city', ''),
            state=meta.get('state', 'CA'),
            postal_code=meta.get('postal_code', ''),
            
            gross_floor_area=total_area_sf,
            year_built=meta.get('year_built', 2000),
            
            primary_use_type=primary_use,
            primary_use_area=primary_area,
            
            occupancy=meta.get('occupancy', 95.0),
            weekly_operating_hours=meta.get('weekly_hours', 168.0),
            number_of_workers=meta.get('num_workers'),
            
            number_of_buildings=1,
            construction_status="Existing"
        )
    
    def _determine_primary_use(
        self, 
        model: InternalRepresentation
    ) -> tuple[str, float]:
        """
        Determine ESPM primary use type from zones
        
        Returns: (use_type, area_sf)
        """
        # Group zones by space function
        use_areas = {}
        for zone in model.zones:
            func = zone.space_function or 'Office'
            area_m2 = zone.floor_area_m2 or 0
            area_sf = area_m2 * 10.764
            
            espm_type = self.SPACE_FUNCTION_TO_ESPM.get(func, 'Other')
            use_areas[espm_type] = use_areas.get(espm_type, 0) + area_sf
        
        # Find largest use
        primary_use = max(use_areas, key=use_areas.get)
        primary_area = use_areas[primary_use]
        
        return primary_use, primary_area
    
    def map_meters(
        self,
        simulation: SimulationOutput
    ) -> List[ESPMMeter]:
        """
        Create ESPM meters from simulation results
        """
        meters = []
        
        # Electric meter (always present)
        meters.append(ESPMMeter(
            meter_id="elec_001",
            meter_name="Electric - Grid",
            meter_type="Electric - Grid",
            units="kWh",
            first_bill_date=date(2023, 1, 1),  # From simulation
            is_bulk_meter=True
        ))
        
        # Gas meter (if gas consumption > 0)
        if simulation.annual.total_gas_therm > 0:
            meters.append(ESPMMeter(
                meter_id="gas_001",
                meter_name="Natural Gas",
                meter_type="Natural Gas",
                units="therms",
                first_bill_date=date(2023, 1, 1),
                is_bulk_meter=True
            ))
        
        # Solar meter (if PV present)
        if simulation.annual.pv_generation_kwh > 0:
            meters.append(ESPMMeter(
                meter_id="solar_001",
                meter_name="On-Site Solar",
                meter_type="Electric - on Site Solar",
                units="kWh",
                first_bill_date=date(2023, 1, 1),
                is_bulk_meter=False
            ))
        
        return meters
    
    def aggregate_monthly_bills(
        self,
        hourly_data: List,  # List[HourlyEnergy]
    ) -> List[ESPMBillEntry]:
        """
        Aggregate 8760 hourly data to monthly bills for ESPM
        """
        from collections import defaultdict
        from datetime import datetime, timedelta
        
        monthly = defaultdict(lambda: {'elec': 0, 'gas': 0, 'solar': 0})
        
        # Aggregate by month
        for hour in hourly_data:
            key = (hour.month,)
            monthly[key]['elec'] += hour.elec_total_kwh
            monthly[key]['gas'] += hour.gas_total_therm
            monthly[key]['solar'] += hour.pv_generation_kwh
        
        # Create bill entries
        bills = []
        year = 2023  # Get from simulation
        
        for (month,), values in monthly.items():
            # Month date range
            start = date(year, month, 1)
            if month == 12:
                end = date(year + 1, 1, 1) - timedelta(days=1)
            else:
                end = date(year, month + 1, 1) - timedelta(days=1)
            
            # Electric bill
            bills.append(ESPMBillEntry(
                meter_id="elec_001",
                start_date=start,
                end_date=end,
                usage=values['elec'],
                is_estimated=False
            ))
            
            # Gas bill
            if values['gas'] > 0:
                bills.append(ESPMBillEntry(
                    meter_id="gas_001",
                    start_date=start,
                    end_date=end,
                    usage=values['gas'],
                    is_estimated=False
                ))
            
            # Solar generation
            if values['solar'] > 0:
                bills.append(ESPMBillEntry(
                    meter_id="solar_001",
                    start_date=start,
                    end_date=end,
                    usage=values['solar'],
                    is_estimated=False
                ))
        
        return bills
```

---

## 5. Phase 2: ESPM Export Module (Weeks 3-4)

### 5.1 ESPM XML Builder

**File**: `eco_tools/integrations/espm/espm_xml_builder.py`

```python
import xml.etree.ElementTree as ET
from typing import List
from .espm_models import ESPMProperty, ESPMMeter, ESPMBillEntry

class ESPMXMLBuilder:
    """
    Build ESPM Portfolio Manager XML format
    
    ESPM supports XML import for bulk data upload:
    - Property definitions
    - Meter definitions  
    - Meter consumption data
    """
    
    def __init__(self):
        self.ns = {
            'pm': 'http://portfoliomanager.energystar.gov/schema'
        }
    
    def build_property_xml(
        self,
        property_data: ESPMProperty
    ) -> ET.Element:
        """
        Build <property> XML element
        """
        prop = ET.Element('property')
        
        # Name
        name_elem = ET.SubElement(prop, 'name')
        name_elem.text = property_data.name
        
        # Address
        addr = ET.SubElement(prop, 'address')
        ET.SubElement(addr, 'address1').text = property_data.address
        ET.SubElement(addr, 'city').text = property_data.city
        ET.SubElement(addr, 'state').text = property_data.state
        ET.SubElement(addr, 'postalCode').text = property_data.postal_code
        ET.SubElement(addr, 'country').text = 'US'
        
        # Construction year
        ET.SubElement(prop, 'yearBuilt').text = str(property_data.year_built)
        
        # Floor area
        ET.SubElement(prop, 'grossFloorArea', units='Square Feet').text = \
            str(property_data.gross_floor_area)
        
        # Primary use
        use = ET.SubElement(prop, 'primaryFunction')
        ET.SubElement(use, 'name').text = property_data.primary_use_type
        ET.SubElement(use, 'grossFloorArea', units='Square Feet').text = \
            str(property_data.primary_use_area)
        
        return prop
    
    def build_meter_xml(
        self,
        meter: ESPMMeter
    ) -> ET.Element:
        """Build <meter> XML element"""
        meter_elem = ET.Element('meter')
        
        ET.SubElement(meter_elem, 'name').text = meter.meter_name
        ET.SubElement(meter_elem, 'type').text = meter.meter_type
        ET.SubElement(meter_elem, 'unitOfMeasure').text = meter.units
        ET.SubElement(meter_elem, 'firstBillDate').text = \
            meter.first_bill_date.isoformat()
        ET.SubElement(meter_elem, 'inUse').text = str(meter.in_use).lower()
        
        if meter.is_bulk_meter:
            ET.SubElement(meter_elem, 'aggregateMeter').text = 'true'
        
        return meter_elem
    
    def build_consumption_xml(
        self,
        bills: List[ESPMBillEntry]
    ) -> ET.Element:
        """Build <meterData> XML for consumption entries"""
        meter_data = ET.Element('meterData')
        
        for bill in bills:
            entry = ET.SubElement(meter_data, 'meterConsumption')
            
            ET.SubElement(entry, 'startDate').text = bill.start_date.isoformat()
            ET.SubElement(entry, 'endDate').text = bill.end_date.isoformat()
            ET.SubElement(entry, 'usage').text = str(bill.usage)
            
            if bill.cost is not None:
                ET.SubElement(entry, 'cost').text = str(bill.cost)
            
            if bill.demand is not None:
                ET.SubElement(entry, 'demand').text = str(bill.demand)
            
            if bill.is_estimated:
                ET.SubElement(entry, 'estimatedValue').text = 'true'
        
        return meter_data
    
    def build_complete_xml(
        self,
        property_data: ESPMProperty,
        meters: List[ESPMMeter],
        bills: List[ESPMBillEntry]
    ) -> str:
        """
        Build complete ESPM XML for import
        
        Returns: XML string
        """
        root = ET.Element('propertyReport', xmlns=self.ns['pm'])
        
        # Property
        root.append(self.build_property_xml(property_data))
        
        # Meters
        meters_elem = ET.SubElement(root, 'meters')
        for meter in meters:
            meters_elem.append(self.build_meter_xml(meter))
        
        # Consumption data
        root.append(self.build_consumption_xml(bills))
        
        # Pretty print
        self._indent(root)
        
        tree = ET.ElementTree(root)
        import io
        f = io.BytesIO()
        tree.write(f, encoding='unicode', xml_declaration=True)
        return f.getvalue()
    
    def _indent(self, elem, level=0):
        """Add whitespace for pretty printing"""
        i = "\n" + level*"  "
        if len(elem):
            if not elem.text or not elem.text.strip():
                elem.text = i + "  "
            if not elem.tail or not elem.tail.strip():
                elem.tail = i
            for child in elem:
                self._indent(child, level+1)
            if not child.tail or not child.tail.strip():
                child.tail = i
        else:
            if level and (not elem.tail or not elem.tail.strip()):
                elem.tail = i
```

### 5.2 ESPM Exporter Service

**File**: `eco_tools/integrations/espm/espm_exporter.py`

```python
from pathlib import Path
from typing import Optional
from eco_tools.core.internal_repr import InternalRepresentation
from eco_tools.lcca.model import SimulationOutput
from .espm_mapper import ESPMMapper
from .espm_xml_builder import ESPMXMLBuilder

class ESPMExporter:
    """
    Export building model and simulation results to ESPM format
    """
    
    def __init__(self):
        self.mapper = ESPMMapper()
        self.xml_builder = ESPMXMLBuilder()
    
    def export_to_espm_xml(
        self,
        model: InternalRepresentation,
        simulation: SimulationOutput,
        output_path: str,
        additional_metadata: Optional[dict] = None
    ) -> str:
        """
        Create ESPM XML file for Portfolio Manager import
        
        Args:
            model: Building model
            simulation: Simulation results with 8760 hourly data
            output_path: Where to save XML
            additional_metadata: User-supplied property info
        
        Returns:
            Path to created XML file
        """
        # Map property
        property_data = self.mapper.map_property(model, additional_metadata)
        
        # Map meters
        meters = self.mapper.map_meters(simulation)
        
        # Aggregate hourly to monthly bills
        bills = self.mapper.aggregate_monthly_bills(simulation.hourly)
        
        # Build XML
        xml_content = self.xml_builder.build_complete_xml(
            property_data, meters, bills
        )
        
        # Write file
        output_file = Path(output_path)
        output_file.write_text(xml_content, encoding='utf-8')
        
        return str(output_file)
    
    def export_to_csv(
        self,
        simulation: SimulationOutput,
        output_dir: str
    ) -> dict:
        """
        Export meter data as CSV files (alternative to XML)
        
        Creates separate CSVs for:
        - Electric consumption
        - Gas consumption
        - Solar generation
        
        Returns: Dict of created file paths
        """
        import pandas as pd
        from pathlib import Path
        
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        # Aggregate monthly
        bills = self.mapper.aggregate_monthly_bills(simulation.hourly)
        
        # Group by meter
        meter_data = {}
        for bill in bills:
            if bill.meter_id not in meter_data:
                meter_data[bill.meter_id] = []
            meter_data[bill.meter_id].append({
                'Start Date': bill.start_date,
                'End Date': bill.end_date,
                'Usage': bill.usage,
                'Cost': bill.cost,
                'Demand': bill.demand
            })
        
        # Write CSVs
        created_files = {}
        for meter_id, data in meter_data.items():
            df = pd.DataFrame(data)
            csv_path = output_path / f"{meter_id}_consumption.csv"
            df.to_csv(csv_path, index=False)
            created_files[meter_id] = str(csv_path)
        
        return created_files
```

---

## 6. Phase 3: BBC/BCC Tracking Module (Weeks 5-6)

### 6.1 BBC Tracker

**File**: `eco_tools/integrations/espm/bbc_tracker.py`

```python
from typing import List, Optional, Dict
from dataclasses import dataclass
from datetime import date
from .espm_models import BBCGoal, BBCProgressReport

@dataclass
class PortfolioBuilding:
    """Individual building in BBC portfolio"""
    building_id: str
    name: str
    gross_area_sf: float
    baseline_eui: float  # kBtu/sf/year
    current_eui: float
    baseline_ghg: float  # mtCO2e/year
    current_ghg: float
    
    # ECM tracking
    ecms_implemented: List[str]
    total_investment: float
    verified_savings: float  # MMBtu/year


class BBCTracker:
    """
    Track Better Buildings Challenge progress
    
    Manages:
    - Portfolio-wide goal tracking
    - Individual building performance
    - Quarterly/annual reporting
    - Goal achievement validation
    """
    
    def __init__(self, goal: BBCGoal):
        self.goal = goal
        self.buildings: List[PortfolioBuilding] = []
    
    def add_building(self, building: PortfolioBuilding):
        """Add building to portfolio tracking"""
        self.buildings.append(building)
    
    def calculate_portfolio_progress(self) -> BBCProgressReport:
        """
        Calculate current portfolio-wide progress toward goals
        """
        # Current portfolio metrics
        total_area = sum(b.gross_area_sf for b in self.buildings)
        
        # Weighted average EUI
        current_eui = sum(
            b.current_eui * b.gross_area_sf 
            for b in self.buildings
        ) / total_area
        
        # Total energy (MMBtu)
        baseline_energy = self.goal.baseline_total_energy_mmbtu
        current_energy = sum(
            b.current_eui * b.gross_area_sf / 1000  # kBtu to MMBtu
            for b in self.buildings
        )
        
        # Energy reduction
        energy_reduction_pct = (
            (baseline_energy - current_energy) / baseline_energy * 100
        )
        
        # GHG
        current_ghg = sum(b.current_ghg for b in self.buildings)
        ghg_reduction_pct = (
            (self.goal.baseline_ghg_emissions_mt - current_ghg) /
            self.goal.baseline_ghg_emissions_mt * 100
        )
        
        # Time progress
        years_elapsed = (
            (date.today() - self.goal.commitment_date).days / 365.25
        )
        years_remaining = (
            self.goal.target_year - date.today().year
        )
        
        # On-track status
        expected_progress = (
            self.goal.energy_reduction_goal_pct * 
            (years_elapsed / 10.0)  # 10-year goal
        )
        on_track = energy_reduction_pct >= expected_progress * 0.9  # Within 10%
        
        # Implemented ECMs
        all_ecms = []
        total_investment = 0
        total_verified_savings = 0
        
        for building in self.buildings:
            all_ecms.extend(building.ecms_implemented)
            total_investment += building.total_investment
            total_verified_savings += building.verified_savings
        
        return BBCProgressReport(
            report_date=date.today(),
            report_period=f"Q{(date.today().month-1)//3 + 1} {date.today().year}",
            
            current_eui=current_eui,
            current_total_energy_mmbtu=current_energy,
            current_ghg_emissions_mt=current_ghg,
            
            energy_reduction_achieved_pct=energy_reduction_pct,
            ghg_reduction_achieved_pct=ghg_reduction_pct,
            
            on_track=on_track,
            years_elapsed=years_elapsed,
            years_remaining=years_remaining,
            
            ecms_implemented=list(set(all_ecms)),  # Unique
            total_investment=total_investment,
            verified_savings_mmbtu=total_verified_savings
        )
    
    def generate_doe_submission(self) -> Dict:
        """
        Generate quarterly DOE submission data
        
        DOE requires:
        - Current portfolio performance
        - List of implemented ECMs
        - Investment details
        - Verification methodology
        """
        progress = self.calculate_portfolio_progress()
        
        return {
            'organization': self.goal.organization_name,
            'reporting_period': progress.report_period,
            
            # Performance metrics
            'baseline_year': self.goal.baseline_year,
            'baseline_eui': self.goal.baseline_eui,
            'current_eui': progress.current_eui,
            'energy_reduction_pct': progress.energy_reduction_achieved_pct,
            
            'baseline_ghg_mt': self.goal.baseline_ghg_emissions_mt,
            'current_ghg_mt': progress.current_ghg_emissions_mt,
            'ghg_reduction_pct': progress.ghg_reduction_achieved_pct,
            
            # Portfolio scope
            'total_buildings': len(self.buildings),
            'total_square_feet': self.goal.total_square_feet,
            
            # Progress
            'goal_achievement_pct': (
                progress.energy_reduction_achieved_pct / 
                self.goal.energy_reduction_goal_pct * 100
            ),
            'on_track': progress.on_track,
            
            # ECMs
            'ecms_implemented_count': len(progress.ecms_implemented),
            'ecms_list': progress.ecms_implemented,
            'total_investment_usd': progress.total_investment,
            'verified_energy_savings_mmbtu': progress.verified_savings_mmbtu,
            
            # Buildings detail
            'buildings': [
                {
                    'name': b.name,
                    'area_sf': b.gross_area_sf,
                    'baseline_eui': b.baseline_eui,
                    'current_eui': b.current_eui,
                    'reduction_pct': (
                        (b.baseline_eui - b.current_eui) / 
                        b.baseline_eui * 100
                    )
                }
                for b in self.buildings
            ]
        }
    
    def export_progress_report_pdf(self, output_path: str):
        """
        Generate formatted PDF progress report
        
        Uses reportlab to create professional DOE-format report
        """
        from reportlab.lib.pagesizes import letter
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.lib.units import inch
        from reportlab.platypus import (
            SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
        )
        from reportlab.lib import colors
        
        doc = SimpleDocTemplate(output_path, pagesize=letter)
        story = []
        styles = getSampleStyleSheet()
        
        # Get progress
        progress = self.calculate_portfolio_progress()
        
        # Title
        title = Paragraph(
            f"<b>Better Buildings Challenge Progress Report</b><br/>"
            f"{self.goal.organization_name}",
            styles['Title']
        )
        story.append(title)
        story.append(Spacer(1, 0.2*inch))
        
        # Reporting period
        story.append(Paragraph(
            f"<b>Reporting Period:</b> {progress.report_period}",
            styles['Normal']
        ))
        story.append(Spacer(1, 0.1*inch))
        
        # Goal summary table
        goal_data = [
            ['Goal Type', self.goal.goal_type],
            ['Commitment Date', self.goal.commitment_date.isoformat()],
            ['Target Date', str(self.goal.target_year)],
            ['Energy Reduction Goal', f"{self.goal.energy_reduction_goal_pct}%"],
        ]
        if self.goal.goal_type in ['BCC', 'Both']:
            goal_data.append([
                'GHG Reduction Goal', 
                f"{self.goal.ghg_reduction_goal_pct}%"
            ])
        
        goal_table = Table(goal_data)
        goal_table.setStyle(TableStyle([
            ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
            ('BACKGROUND', (0,0), (0,-1), colors.lightgrey),
            ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ]))
        story.append(goal_table)
        story.append(Spacer(1, 0.2*inch))
        
        # Progress summary
        story.append(Paragraph("<b>Current Progress</b>", styles['Heading2']))
        progress_data = [
            ['Metric', 'Baseline', 'Current', 'Reduction', 'Status'],
            [
                'Energy (EUI)',
                f"{self.goal.baseline_eui:.1f} kBtu/sf",
                f"{progress.current_eui:.1f} kBtu/sf",
                f"{progress.energy_reduction_achieved_pct:.1f}%",
                '✓ On Track' if progress.on_track else '⚠ Behind'
            ]
        ]
        
        if self.goal.goal_type in ['BCC', 'Both']:
            progress_data.append([
                'GHG Emissions',
                f"{self.goal.baseline_ghg_emissions_mt:.0f} mtCO2e",
                f"{progress.current_ghg_emissions_mt:.0f} mtCO2e",
                f"{progress.ghg_reduction_achieved_pct:.1f}%",
                ''
            ])
        
        progress_table = Table(progress_data)
        progress_table.setStyle(TableStyle([
            ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
            ('BACKGROUND', (0,0), (-1,0), colors.lightblue),
            ('ALIGN', (1,1), (-1,-1), 'RIGHT'),
        ]))
        story.append(progress_table)
        story.append(Spacer(1, 0.2*inch))
        
        # ECMs implemented
        story.append(Paragraph(
            "<b>Energy Conservation Measures Implemented</b>", 
            styles['Heading2']
        ))
        story.append(Paragraph(
            f"Total ECMs: {len(progress.ecms_implemented)}<br/>"
            f"Total Investment: ${progress.total_investment:,.0f}<br/>"
            f"Verified Savings: {progress.verified_savings_mmbtu:,.0f} MMBtu/year",
            styles['Normal']
        ))
        
        # Build PDF
        doc.build(story)
```

---

## 7. Phase 4: Streamlit GUI Integration (Weeks 7-9)

### 7.1 Portfolio Management Page

**File**: `gui/pages/portfolio_page.py`

```python
import streamlit as st
from typing import List
from eco_tools.integrations.espm.bbc_tracker import (
    BBCTracker, PortfolioBuilding, BBCGoal
)
from datetime import date

def handle_portfolio():
    """
    Portfolio-level management page
    
    Features:
    - Track multiple buildings
    - Set BBC/BCC goals
    - View portfolio-wide metrics
    - Building comparison
    """
    st.title("Portfolio Management")
    
    # Initialize portfolio in session state
    if 'portfolio_buildings' not in st.session_state:
        st.session_state.portfolio_buildings = []
    
    if 'bbc_goal' not in st.session_state:
        st.session_state.bbc_goal = None
    
    # Tabs
    tab1, tab2, tab3 = st.tabs([
        "Buildings", 
        "BBC/BCC Goals", 
        "Portfolio Analytics"
    ])
    
    with tab1:
        show_buildings_list()
    
    with tab2:
        show_bbc_goals()
    
    with tab3:
        show_portfolio_analytics()


def show_buildings_list():
    """Display list of buildings in portfolio"""
    st.subheader("Portfolio Buildings")
    
    buildings = st.session_state.portfolio_buildings
    
    if not buildings:
        st.info("No buildings in portfolio. Import a model to add buildings.")
        return
    
    # Add current model to portfolio
    if st.button("Add Current Model to Portfolio"):
        if 'active_model' in st.session_state:
            model = st.session_state.active_model
            # Extract building info
            building = PortfolioBuilding(
                building_id=model.proj_metadata.get('id', 'building_001'),
                name=model.proj_metadata.get('name', 'Unnamed Building'),
                gross_area_sf=sum(z.floor_area_m2 * 10.764 for z in model.zones),
                baseline_eui=0,  # User will set
                current_eui=0,   # From simulation
                baseline_ghg=0,
                current_ghg=0,
                ecms_implemented=[],
                total_investment=0,
                verified_savings=0
            )
            buildings.append(building)
            st.success(f"Added {building.name} to portfolio")
            st.rerun()
    
    # Display buildings table
    import pandas as pd
    
    df = pd.DataFrame([
        {
            'Name': b.name,
            'Area (sf)': f"{b.gross_area_sf:,.0f}",
            'Baseline EUI': f"{b.baseline_eui:.1f}",
            'Current EUI': f"{b.current_eui:.1f}",
            'Reduction': (
                f"{(b.baseline_eui - b.current_eui) / b.baseline_eui * 100:.1f}%"
                if b.baseline_eui > 0 else 'N/A'
            )
        }
        for b in buildings
    ])
    
    st.dataframe(df, use_container_width=True)
    
    # Building detail editor
    st.subheader("Edit Building Details")
    
    if buildings:
        selected = st.selectbox(
            "Select Building",
            options=range(len(buildings)),
            format_func=lambda i: buildings[i].name
        )
        
        building = buildings[selected]
        
        with st.form(f"edit_building_{selected}"):
            col1, col2 = st.columns(2)
            
            with col1:
                building.baseline_eui = st.number_input(
                    "Baseline EUI (kBtu/sf/yr)",
                    value=building.baseline_eui,
                    min_value=0.0
                )
                
                building.current_eui = st.number_input(
                    "Current EUI (kBtu/sf/yr)",
                    value=building.current_eui,
                    min_value=0.0
                )
            
            with col2:
                building.baseline_ghg = st.number_input(
                    "Baseline GHG (mtCO2e/yr)",
                    value=building.baseline_ghg,
                    min_value=0.0
                )
                
                building.current_ghg = st.number_input(
                    "Current GHG (mtCO2e/yr)",
                    value=building.current_ghg,
                    min_value=0.0
                )
            
            if st.form_submit_button("Update"):
                st.success("Building updated")
                st.rerun()


def show_bbc_goals():
    """Set and manage BBC/BCC goals"""
    st.subheader("Better Buildings Challenge Goals")
    
    # Create goal if doesn't exist
    if st.session_state.bbc_goal is None:
        st.info("Set up your BBC/BCC commitment")
        
        with st.form("create_bbc_goal"):
            org_name = st.text_input(
                "Organization Name",
                value="Mercy Housing"
            )
            
            col1, col2 = st.columns(2)
            with col1:
                baseline_year = st.number_input(
                    "Baseline Year",
                    min_value=2000,
                    max_value=2030,
                    value=2019
                )
            
            with col2:
                commitment_date = st.date_input(
                    "Commitment Date",
                    value=date(2020, 1, 1)
                )
            
            goal_type = st.radio(
                "Goal Type",
                options=["BBC", "BCC", "Both"],
                help=(
                    "BBC = 20% energy reduction / "
                    "BCC = 50% GHG reduction / "
                    "Both = Dual goals"
                )
            )
            
            # Portfolio baseline
            st.subheader("Portfolio Baseline")
            
            col1, col2, col3 = st.columns(3)
            with col1:
                baseline_eui = st.number_input(
                    "Baseline EUI (kBtu/sf/yr)",
                    min_value=0.0,
                    value=80.0
                )
            
            with col2:
                total_area = st.number_input(
                    "Total Area (sf)",
                    min_value=0.0,
                    value=1000000.0,
                    format="%.0f"
                )
            
            with col3:
                baseline_ghg = st.number_input(
                    "Baseline GHG (mtCO2e/yr)",
                    min_value=0.0,
                    value=5000.0
                )
            
            if st.form_submit_button("Create Goal"):
                baseline_energy = baseline_eui * total_area / 1000  # MMBtu
                
                goal = BBCGoal(
                    organization_name=org_name,
                    commitment_date=commitment_date,
                    baseline_year=baseline_year,
                    target_year=baseline_year + 10,
                    
                    baseline_eui=baseline_eui,
                    baseline_total_energy_mmbtu=baseline_energy,
                    baseline_ghg_emissions_mt=baseline_ghg,
                    
                    total_buildings=len(st.session_state.portfolio_buildings),
                    total_square_feet=total_area,
                    
                    goal_type=goal_type
                )
                
                st.session_state.bbc_goal = goal
                st.success("BBC/BCC goal created!")
                st.rerun()
    
    else:
        # Display existing goal
        goal = st.session_state.bbc_goal
        
        st.write(f"**Organization:** {goal.organization_name}")
        st.write(f"**Goal Type:** {goal.goal_type}")
        st.write(f"**Commitment Date:** {goal.commitment_date}")
        st.write(f"**Baseline Year:** {goal.baseline_year}")
        st.write(f"**Target Year:** {goal.target_year}")
        
        col1, col2 = st.columns(2)
        with col1:
            st.metric(
                "Energy Reduction Goal",
                f"{goal.energy_reduction_goal_pct}%"
            )
            st.metric(
                "Baseline EUI",
                f"{goal.baseline_eui:.1f} kBtu/sf/yr"
            )
        
        with col2:
            if goal.goal_type in ['BCC', 'Both']:
                st.metric(
                    "GHG Reduction Goal",
                    f"{goal.ghg_reduction_goal_pct}%"
                )
            st.metric(
                "Total Area",
                f"{goal.total_square_feet:,.0f} sf"
            )


def show_portfolio_analytics():
    """Portfolio-wide analytics and BBC progress"""
    st.subheader("Portfolio Performance")
    
    goal = st.session_state.bbc_goal
    buildings = st.session_state.portfolio_buildings
    
    if not goal or not buildings:
        st.warning("Set up BBC goal and add buildings to view analytics")
        return
    
    # Calculate progress
    tracker = BBCTracker(goal)
    for building in buildings:
        tracker.add_building(building)
    
    progress = tracker.calculate_portfolio_progress()
    
    # Progress metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            "Current EUI",
            f"{progress.current_eui:.1f}",
            delta=f"{progress.current_eui - goal.baseline_eui:.1f}",
            delta_color="inverse"
        )
    
    with col2:
        st.metric(
            "Energy Reduction",
            f"{progress.energy_reduction_achieved_pct:.1f}%",
            delta=(
                f"{progress.energy_reduction_achieved_pct - goal.energy_reduction_goal_pct:.1f}%"
                if progress.on_track else None
            )
        )
    
    with col3:
        st.metric(
            "Years Remaining",
            f"{progress.years_remaining:.1f}",
            help="Years until 10-year goal completion"
        )
    
    with col4:
        st.metric(
            "Status",
            "✓ On Track" if progress.on_track else "⚠ Behind",
            help="Based on linear interpolation to goal"
        )
    
    # Progress chart
    st.subheader("Goal Progress Visualization")
    
    import plotly.graph_objects as go
    
    # Create timeline
    years = list(range(goal.baseline_year, goal.target_year + 1))
    
    # Target trajectory (linear)
    target_trajectory = [
        goal.baseline_eui * (1 - goal.energy_reduction_goal_pct/100 * i/10)
        for i in range(len(years))
    ]
    
    # Current trajectory (extrapolated)
    current_year_index = years.index(date.today().year) if date.today().year in years else -1
    
    fig = go.Figure()
    
    # Target line
    fig.add_trace(go.Scatter(
        x=years,
        y=target_trajectory,
        mode='lines+markers',
        name='Target Trajectory',
        line=dict(color='green', dash='dash')
    ))
    
    # Current point
    if current_year_index >= 0:
        fig.add_trace(go.Scatter(
            x=[years[current_year_index]],
            y=[progress.current_eui],
            mode='markers',
            name='Current Performance',
            marker=dict(size=15, color='blue')
        ))
    
    fig.update_layout(
        title="BBC Energy Reduction Progress",
        xaxis_title="Year",
        yaxis_title="EUI (kBtu/sf/yr)",
        hovermode='closest'
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    # DOE submission
    st.subheader("DOE Quarterly Submission")
    
    if st.button("Generate DOE Report"):
        submission = tracker.generate_doe_submission()
        
        import json
        st.json(submission)
        
        # Download as JSON
        st.download_button(
            "Download JSON",
            data=json.dumps(submission, indent=2),
            file_name=f"bbc_report_{progress.report_period}.json",
            mime="application/json"
        )
    
    # PDF report
    if st.button("Generate PDF Progress Report"):
        import tempfile
        with tempfile.NamedTemporaryFile(
            delete=False, suffix='.pdf'
        ) as tmp:
            tracker.export_progress_report_pdf(tmp.name)
            
            with open(tmp.name, 'rb') as f:
                st.download_button(
                    "Download PDF Report",
                    data=f.read(),
                    file_name=f"bbc_progress_{progress.report_period}.pdf",
                    mime="application/pdf"
                )
```

### 7.2 ESPM Export Page

**File**: `gui/pages/espm_export_page.py`

```python
import streamlit as st
from eco_tools.integrations.espm.espm_exporter import ESPMExporter

def handle_espm_export():
    """
    ESPM data export page
    
    Features:
    - Export building model to ESPM XML
    - Export simulation results as meter data
    - Provide instructions for Portfolio Manager upload
    """
    st.title("Energy Star Portfolio Manager Export")
    
    # Check prerequisites
    if 'active_model' not in st.session_state:
        st.error("Please import a building model first")
        return
    
    model = st.session_state.active_model
    
    # Check for simulation results
    if 'simulation_results' not in st.session_state:
        st.warning(
            "No simulation results found. "
            "Run simulation first to export meter data."
        )
        has_sim = False
    else:
        has_sim = True
        sim = st.session_state.simulation_results
    
    st.write("---")
    
    # Additional metadata form
    st.subheader("Property Information")
    st.caption("Additional information needed for ESPM that's not in the model")
    
    with st.form("espm_metadata"):
        col1, col2 = st.columns(2)
        
        with col1:
            address = st.text_input("Street Address")
            city = st.text_input("City")
            state = st.text_input("State", value="CA")
            postal_code = st.text_input("Postal Code")
        
        with col2:
            year_built = st.number_input(
                "Year Built",
                min_value=1800,
                max_value=2030,
                value=2000
            )
            
            occupancy = st.number_input(
                "Occupancy (%)",
                min_value=0.0,
                max_value=100.0,
                value=95.0
            )
            
            weekly_hours = st.number_input(
                "Weekly Operating Hours",
                min_value=0.0,
                max_value=168.0,
                value=168.0
            )
            
            num_workers = st.number_input(
                "Number of Workers",
                min_value=0,
                value=100
            )
        
        submit = st.form_submit_button("Prepare ESPM Export")
    
    if submit:
        st.session_state.espm_metadata = {
            'address': address,
            'city': city,
            'state': state,
            'postal_code': postal_code,
            'year_built': year_built,
            'occupancy': occupancy,
            'weekly_hours': weekly_hours,
            'num_workers': num_workers if num_workers > 0 else None
        }
        st.success("Metadata saved")
    
    st.write("---")
    
    # Export options
    st.subheader("Export Options")
    
    export_type = st.radio(
        "Export Format",
        options=["ESPM XML (Recommended)", "CSV Files (Manual Upload)"],
        help=(
            "XML: Single file for bulk upload to Portfolio Manager\n"
            "CSV: Separate files for manual entry"
        )
    )
    
    if not has_sim:
        st.info("Simulation results required for meter data export")
    
    if st.button("Generate Export", disabled=not has_sim):
        exporter = ESPMExporter()
        
        metadata = st.session_state.get('espm_metadata', {})
        
        try:
            if export_type == "ESPM XML (Recommended)":
                # Export to XML
                import tempfile
                with tempfile.NamedTemporaryFile(
                    delete=False, suffix='.xml', mode='w'
                ) as tmp:
                    xml_path = exporter.export_to_espm_xml(
                        model, sim, tmp.name, metadata
                    )
                
                with open(xml_path, 'r') as f:
                    xml_content = f.read()
                
                st.download_button(
                    "Download ESPM XML",
                    data=xml_content,
                    file_name="portfolio_manager_import.xml",
                    mime="application/xml"
                )
                
                st.success("ESPM XML generated successfully!")
                
                # Instructions
                with st.expander("Upload Instructions"):
                    st.markdown("""
                    ### How to upload to Energy Star Portfolio Manager
                    
                    1. Log in to [Portfolio Manager](https://portfoliomanager.energystar.gov)
                    2. Navigate to **My Portfolio** > **Import/Export**
                    3. Select **Import** > **Property with Meter Data**
                    4. Upload the XML file
                    5. Review imported data
                    6. Verify property details and meter associations
                    
                    ### What's included in this export:
                    - Property definition (name, address, area, use types)
                    - Meter definitions (Electric, Gas, Solar if applicable)
                    - Monthly consumption data from simulation results
                    """)
            
            else:  # CSV export
                import tempfile
                with tempfile.TemporaryDirectory() as tmpdir:
                    csv_files = exporter.export_to_csv(sim, tmpdir)
                    
                    for meter_id, csv_path in csv_files.items():
                        with open(csv_path, 'r') as f:
                            csv_content = f.read()
                        
                        st.download_button(
                            f"Download {meter_id}",
                            data=csv_content,
                            file_name=f"{meter_id}.csv",
                            mime="text/csv",
                            key=f"download_{meter_id}"
                        )
                
                st.success(f"Generated {len(csv_files)} CSV files")
                
                with st.expander("Manual Upload Instructions"):
                    st.markdown("""
                    ### Manual CSV upload process
                    
                    1. Create property in Portfolio Manager
                    2. Add meters for each utility type
                    3. Upload meter consumption:
                       - Electric: `elec_001_consumption.csv`
                       - Gas: `gas_001_consumption.csv` (if applicable)
                       - Solar: `solar_001_consumption.csv` (if applicable)
                    """)
        
        except Exception as e:
            st.error(f"Export failed: {str(e)}")
            st.exception(e)
```

---

## 8. Phase 5: Testing & Integration (Weeks 10-12)

### 8.1 Unit Tests

**File**: `tests/integration/test_espm_integration.py`

```python
import pytest
from datetime import date
from eco_tools.integrations.espm.espm_mapper import ESPMMapper
from eco_tools.integrations.espm.espm_models import ESPMProperty
from eco_tools.core.internal_repr import InternalRepresentation, Zone

def test_property_mapping():
    """Test InternalRepresentation → ESPM Property mapping"""
    # Create test model
    model = InternalRepresentation(
        proj_metadata={'name': 'Test Building'},
        zones=[
            Zone(
                id='zone1',
                name='Zone 1',
                building_type='NR',
                floor_area_m2=1000.0,
                space_function='Office'
            )
        ]
    )
    
    mapper = ESPMMapper()
    
    metadata = {
        'address': '123 Main St',
        'city': 'Los Angeles',
        'state': 'CA',
        'postal_code': '90001',
        'year_built': 2015
    }
    
    property_data = mapper.map_property(model, metadata)
    
    assert property_data.name == 'Test Building'
    assert property_data.address == '123 Main St'
    assert property_data.gross_floor_area > 0
    assert property_data.primary_use_type == 'Office'


def test_meter_mapping():
    """Test simulation results → ESPM meter mapping"""
    from eco_tools.lcca.model import SimulationOutput, AnnualEnergySummary
    
    sim = SimulationOutput(
        annual=AnnualEnergySummary(
            total_elec_kwh=100000,
            total_gas_therm=5000,
            pv_generation_kwh=20000
        )
    )
    
    mapper = ESPMMapper()
    meters = mapper.map_meters(sim)
    
    # Should have 3 meters: Electric, Gas, Solar
    assert len(meters) == 3
    
    meter_types = [m.meter_type for m in meters]
    assert "Electric - Grid" in meter_types
    assert "Natural Gas" in meter_types
    assert "Electric - on Site Solar" in meter_types


def test_bbc_tracking():
    """Test BBC goal tracking calculations"""
    from eco_tools.integrations.espm.bbc_tracker import (
        BBCTracker, BBCGoal, PortfolioBuilding
    )
    
    goal = BBCGoal(
        organization_name="Test Org",
        commitment_date=date(2020, 1, 1),
        baseline_year=2019,
        target_year=2029,
        
        baseline_eui=80.0,
        baseline_total_energy_mmbtu=80000,
        baseline_ghg_emissions_mt=5000,
        
        total_buildings=1,
        total_square_feet=1000000,
        
        goal_type="BBC"
    )
    
    tracker = BBCTracker(goal)
    
    # Add building with 10% reduction
    building = PortfolioBuilding(
        building_id='bldg1',
        name='Building 1',
        gross_area_sf=1000000,
        baseline_eui=80.0,
        current_eui=72.0,  # 10% reduction
        baseline_ghg=5000,
        current_ghg=4500,
        ecms_implemented=['LED Lighting', 'HVAC Controls'],
        total_investment=500000,
        verified_savings=8000
    )
    
    tracker.add_building(building)
    
    progress = tracker.calculate_portfolio_progress()
    
    assert progress.energy_reduction_achieved_pct == pytest.approx(10.0, rel=0.1)
    assert len(progress.ecms_implemented) == 2
```

### 8.2 Integration Testing

Create test workflow:

```bash
# Test complete export workflow
pytest tests/integration/test_espm_workflow.py -v

# Test GUI pages (requires Streamlit)
streamlit run gui/main.py --server.headless true
```

---

## 9. Deployment Strategy (Weeks 13-16)

### 9.1 Package Dependencies

Update `requirements.txt`:

```txt
# Existing dependencies
streamlit>=1.28.0
pydantic>=2.0.0
lxml>=4.9.0
pandas>=1.5.0
plotly>=5.14.0

# NEW for ESPM integration
requests>=2.31.0  # For future ESPM API calls
reportlab>=4.0.0  # PDF generation
openpyxl>=3.1.0   # Excel export (optional)
```

### 9.2 Feature Flags

Add to `gui/config.py`:

```python
FEATURES = {
    'geometry_builder': True,
    'espm_integration': True,     # NEW
    'bbc_tracking': True,         # NEW
    'portfolio_management': True, # NEW
}
```

### 9.3 Documentation

Create user documentation:

**File**: `docs/ESPM_INTEGRATION_GUIDE.md`

```markdown
# ESPM Integration User Guide

## Overview
ECO Alpha v7 now integrates with Energy Star Portfolio Manager (ESPM)
for building benchmarking and Better Buildings Challenge tracking.

## Features

### 1. Portfolio Management
- Track multiple buildings
- Set BBC/BCC goals
- Monitor progress toward 20% reduction target

### 2. ESPM Export
- Export building data to ESPM XML format
- Generate monthly meter consumption data
- Create CSV files for manual upload

### 3. BBC/BCC Reporting
- Quarterly progress reports
- DOE submission data generation
- PDF formatted reports

## Workflow

### Step 1: Create Building Model
1. Import CIBD or build model in wizard
2. Run CBECC simulation
3. Complete LCCA analysis

### Step 2: Add to Portfolio
1. Navigate to **Portfolio Management**
2. Click "Add Current Model to Portfolio"
3. Set baseline EUI and emissions

### Step 3: Set BBC Goal
1. Go to **BBC/BCC Goals** tab
2. Fill in organization details
3. Set baseline metrics
4. Save goal

### Step 4: Export to ESPM
1. Navigate to **ESPM Export**
2. Fill in property metadata
3. Generate XML export
4. Upload to Portfolio Manager

### Step 5: Track Progress
1. View **Portfolio Analytics** tab
2. Review current vs. target
3. Generate quarterly reports
4. Submit to DOE
```

---

## 10. Success Metrics

### Technical KPIs

| Metric | Target |
|--------|--------|
| ESPM XML validation rate | >98% |
| Data mapping accuracy | >95% |
| Export generation time | <10 seconds |
| PDF report generation | <5 seconds |

### User KPIs

| Metric | 3-Month Target |
|--------|----------------|
| Buildings exported to ESPM | 50+ |
| Active BBC portfolios | 10+ |
| Quarterly reports generated | 30+ |
| User satisfaction | >4.0/5.0 |

---

## 11. Future Enhancements (Phase 6+)

### 11.1 ESPM API Integration (NOT in initial release)

Future consideration for bi-directional sync:

```python
class ESPMAPIClient:
    """
    Direct ESPM API integration (future)
    
    Requires EPA approval and authentication
    """
    
    def authenticate(self, username, password):
        """OAuth authentication"""
        pass
    
    def create_property(self, property_data):
        """POST /property"""
        pass
    
    def fetch_metrics(self, property_id):
        """GET /property/{id}/metrics"""
        pass
```

### 11.2 EnergyScoreCards Integration

Optional integration for Mercy Housing:

```python
class ESCExporter:
    """Export to EnergyScoreCards format"""
    
    def export_utility_bills(self, simulation):
        """Format for ESC upload"""
        pass
```

### 11.3 Automated Reporting

```python
class AutomatedReporter:
    """
    Schedule automatic quarterly reporting
    
    - Cron-based report generation
    - Email delivery to DOE contacts
    - Dashboard notifications
    """
    pass
```

---

## 12. Conclusion

This integration plan provides Mercy Housing with comprehensive ESPM and BBC/BCC support while maintaining Alphav7's Streamlit architecture. The modular design allows phased implementation and future enhancements without disrupting existing functionality.

### Key Deliverables

1. ✅ ESPM data models and mappers
2. ✅ XML export generation
3. ✅ BBC/BCC goal tracking
4. ✅ Portfolio management GUI
5. ✅ Quarterly reporting automation
6. ✅ DOE submission preparation

### Next Steps

1. Review and approve architecture approach
2. Begin Phase 1 implementation (ESPM models)
3. Set up testing infrastructure
4. Develop GUI pages incrementally
5. User acceptance testing with Mercy Housing
6. Production deployment

---

## Appendix A: ESPM Property Types

**Supported by ESPM (80+ types)**:

- Multifamily Housing
- Office
- Hotel
- K-12 School
- Warehouse
- Retail Store
- Medical Office
- Data Center
- Hospital
- Senior Care Facility
- [Full list in ESPM documentation]

## Appendix B: BBC Requirements

**DOE Better Buildings Challenge**:
- 20% energy reduction over 10 years
- Quarterly progress reporting
- Public sharing of results
- Showcase projects
- Best practices documentation

**DOE Better Climate Challenge**:
- 50% GHG reduction over 10 years
- Portfolio-wide commitment
- Annual reporting
- Climate action plan

---

**Document Version**: 1.0  
**Last Updated**: December 2025  
**Author**: Claude  
**Project**: ECO Tools Suite - ESPM Integration
