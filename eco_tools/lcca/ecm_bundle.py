"""
ECM (Energy Conservation Measure) Bundle System.

Provides tracking and analysis of individual energy conservation measures:
- Define ECMs with their costs, energy impacts, and incentives
- Calculate marginal value of individual measures
- Create scenarios with different ECM combinations
- Compare "with ECM" vs "without ECM" for any measure

ECM Categories (aligned with OpenStudio BCL):
- Generation: PV, Battery storage, CHP
- Envelope: Walls, Roofs, Windows, Infiltration
- HVAC: Heating, Cooling, Ventilation, Controls
- DHW: Heat pump water heaters, Solar thermal
- Lighting: LED upgrades, Controls, Daylighting
- Refrigeration: Walk-ins, Display cases
- Controls: BMS, Scheduling, FDD

Example:
    >>> from eco_tools.lcca import ECMBundle, ECM, ScenarioManager
    >>>
    >>> bundle = ECMBundle()
    >>> bundle.add_ecm(ECM(
    ...     name="343 kW PV System",
    ...     category=ECMCategory.GENERATION,
    ...     subcategory=ECMSubcategory.PHOTOVOLTAIC,
    ...     capex=857500,
    ...     annual_kwh_generation=343177,
    ... ))
    >>> bundle.add_ecm(ECM(
    ...     name="HVAC Electrification",
    ...     category=ECMCategory.HVAC,
    ...     subcategory=ECMSubcategory.HVAC_HEATING,
    ...     capex=500000,
    ...     annual_kwh_delta=-50000,  # Increased electric
    ...     annual_therm_delta=-46000,  # Eliminated gas
    ... ))
    >>>
    >>> # Get marginal value of PV only
    >>> pv_value = bundle.marginal_analysis("343 kW PV System", manager)
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Tuple, Set
from enum import Enum
import json
from pathlib import Path


class ECMCategory(Enum):
    """
    Standard ECM categories (aligned with OpenStudio BCL).

    Categories match BCL top-level taxonomy for interoperability.
    """
    GENERATION = "generation"      # PV, wind, CHP
    STORAGE = "storage"            # Battery, thermal storage
    HVAC = "hvac"                  # Heating, cooling, ventilation
    ENVELOPE = "envelope"          # Insulation, windows, air sealing
    LIGHTING = "lighting"          # LED, controls, daylighting
    DHW = "dhw"                    # Domestic hot water
    PLUGLOAD = "plugload"          # Equipment efficiency
    CONTROLS = "controls"          # BMS, scheduling, FDD
    REFRIGERATION = "refrigeration"  # Walk-ins, display cases
    OTHER = "other"


class ECMSubcategory(Enum):
    """
    ECM subcategories for detailed classification.

    Mapped to OpenStudio BCL and CEC CASE report structure.
    """
    # Generation subcategories
    PHOTOVOLTAIC = "photovoltaic"
    BATTERY = "battery"
    CHP = "chp"
    WIND = "wind"

    # Envelope subcategories (BCL: 88 measures)
    ENVELOPE_OPAQUE = "opaque"              # Walls, roofs, floors (41 BCL)
    ENVELOPE_FENESTRATION = "fenestration"  # Windows, skylights (12 BCL)
    ENVELOPE_INFILTRATION = "infiltration"  # Air sealing (8 BCL)
    ENVELOPE_COOL_ROOF = "cool_roof"
    ENVELOPE_FORM = "form"                  # Geometry (25 BCL)

    # HVAC subcategories (BCL: 69 measures)
    HVAC_HEATING = "heating"                # Heat pumps, furnaces (8 BCL)
    HVAC_COOLING = "cooling"                # Chillers, DX (14 BCL)
    HVAC_VENTILATION = "ventilation"        # ERV, DOAS, DCV (6 BCL)
    HVAC_DISTRIBUTION = "distribution"      # Ducts, VAV (7 BCL)
    HVAC_CONTROLS = "hvac_controls"         # Economizer, setpoints (5 BCL)
    HVAC_WHOLE_SYSTEM = "whole_system"      # VRF, packaged (28 BCL)
    HVAC_ENERGY_RECOVERY = "energy_recovery"  # ERV/HRV (1 BCL)

    # DHW subcategories (BCL: 6 measures)
    DHW_HEAT_PUMP = "dhw_heat_pump"
    DHW_SOLAR = "dhw_solar"
    DHW_DISTRIBUTION = "dhw_distribution"
    DHW_CONVENTIONAL = "dhw_conventional"

    # Lighting subcategories (BCL: 15 measures)
    LIGHTING_EQUIPMENT = "lighting_equipment"  # LED (10 BCL)
    LIGHTING_CONTROLS = "lighting_controls"    # Occupancy, daylight (5 BCL)
    LIGHTING_DAYLIGHTING = "daylighting"

    # Plugload subcategories
    PLUGLOAD_EQUIPMENT = "plugload_equipment"
    PLUGLOAD_CONTROLS = "plugload_controls"

    # Controls subcategories
    CONTROLS_BMS = "bms"
    CONTROLS_SCHEDULING = "scheduling"
    CONTROLS_FDD = "fdd"
    CONTROLS_GUIDELINE36 = "guideline_36"

    # Refrigeration subcategories
    REFRIG_WALKIN = "walkin"
    REFRIG_DISPLAY = "display"
    REFRIG_EVAPORATOR = "evaporator"

    # Electrification subcategories (Title 24 2025 focus)
    ELEC_COOKING = "elec_cooking"
    ELEC_DRYER = "elec_dryer"
    ELEC_READY = "elec_ready"
    ELEC_PANEL = "elec_panel"
    ELEC_EV_CHARGING = "ev_charging"

    # Other subcategories (CEC CASE specific)
    OTHER_COMMERCIAL_KITCHEN = "commercial_kitchen"
    OTHER_POOL_SPA = "pool_spa"
    OTHER_LABORATORY = "laboratory"
    OTHER_HORTICULTURE = "horticulture"
    OTHER_GENERIC = "generic"


class BuildingType(Enum):
    """Building types for ECM applicability."""
    SINGLE_FAMILY = "single_family"
    MULTIFAMILY_LOW = "multifamily_low"      # 1-3 stories
    MULTIFAMILY_HIGH = "multifamily_high"    # 4+ stories
    OFFICE_SMALL = "office_small"
    OFFICE_LARGE = "office_large"
    RETAIL = "retail"
    WAREHOUSE = "warehouse"
    HOTEL = "hotel"
    RESTAURANT = "restaurant"
    HEALTHCARE = "healthcare"
    EDUCATION = "education"
    LABORATORY = "laboratory"
    ALL_RESIDENTIAL = "all_residential"
    ALL_COMMERCIAL = "all_commercial"
    ALL = "all"


class CodeBaseline(Enum):
    """Code baseline references for ECM savings calculations."""
    T24_2019 = "T24-2019"
    T24_2022 = "T24-2022"
    T24_2025 = "T24-2025"
    ASHRAE_90_1_2016 = "ASHRAE 90.1-2016"
    ASHRAE_90_1_2019 = "ASHRAE 90.1-2019"
    ASHRAE_90_1_2022 = "ASHRAE 90.1-2022"
    IECC_2021 = "IECC-2021"
    CUSTOM = "custom"


@dataclass
class ECM:
    """
    Individual Energy Conservation Measure.

    Tracks the cost and energy impact of a single measure.
    Energy impacts can be specified as absolute values or percentages.

    Attributes:
        name: Descriptive name for the ECM
        category: ECM category (generation, hvac, envelope, etc.)
        subcategory: Detailed subcategory (e.g., HVAC_HEATING, ENVELOPE_OPAQUE)
        capex: Capital cost ($)
        opex_annual: Annual operating cost change ($, positive = increase)
        maintenance_annual: Annual maintenance cost change ($)

        # Energy impacts (use one approach per energy type)
        annual_kwh_delta: Change in annual kWh (negative = reduction)
        annual_kwh_pct: Percentage change in kWh (e.g., -0.20 for 20% reduction)
        annual_kwh_generation: kWh generated (for PV, CHP)

        annual_therm_delta: Change in annual therms (negative = reduction)
        annual_therm_pct: Percentage change in therms

        demand_kw_delta: Change in peak demand (kW)

        # Incentives
        incentives: List of associated incentives

        # Applicability
        applicable_building_types: Building types where ECM applies
        climate_zones: California climate zones where applicable (1-16)

        # Code compliance
        code_baseline: Reference code for savings calculation
        compliance_credit: Compliance pathway credit type

        # Cost uncertainty
        capex_range: (low, high) cost range for sensitivity
        savings_range: (low, high) savings range for sensitivity

        # Data provenance
        source: Data source reference
        bcl_uid: OpenStudio BCL measure UUID (if applicable)
        vintage: Year of cost/performance data

        # Metadata
        description: Detailed description
        useful_life_years: Expected useful life
        notes: Additional notes

    Example:
        >>> pv = ECM(
        ...     name="100 kW PV",
        ...     category=ECMCategory.GENERATION,
        ...     subcategory=ECMSubcategory.PHOTOVOLTAIC,
        ...     capex=250000,
        ...     annual_kwh_generation=150000,
        ...     applicable_building_types=[BuildingType.ALL],
        ... )
    """
    name: str
    category: ECMCategory = ECMCategory.OTHER
    subcategory: Optional[ECMSubcategory] = None

    # Capital and operating costs
    capex: float = 0.0
    opex_annual: float = 0.0
    maintenance_annual: float = 0.0

    # Electricity impacts
    annual_kwh_delta: float = 0.0       # Absolute change (negative = savings)
    annual_kwh_pct: float = 0.0         # Percentage change (e.g., -0.20)
    annual_kwh_generation: float = 0.0  # Generation (PV, CHP)

    # Gas impacts
    annual_therm_delta: float = 0.0     # Absolute change
    annual_therm_pct: float = 0.0       # Percentage change

    # Demand impacts
    demand_kw_delta: float = 0.0        # Change in peak demand

    # Incentives (stored as list of dicts for flexibility)
    incentives: List[Dict[str, Any]] = field(default_factory=list)

    # Applicability
    applicable_building_types: List[BuildingType] = field(default_factory=lambda: [BuildingType.ALL])
    climate_zones: List[int] = field(default_factory=lambda: list(range(1, 17)))  # All CA zones

    # Code compliance
    code_baseline: Optional[CodeBaseline] = None
    compliance_credit: Optional[str] = None

    # Cost uncertainty for sensitivity analysis
    capex_range: Optional[Tuple[float, float]] = None  # (low, high)
    savings_range: Optional[Tuple[float, float]] = None  # (low_pct, high_pct)

    # Data provenance
    source: Optional[str] = None
    bcl_uid: Optional[str] = None
    vintage: Optional[int] = None  # Year of cost data

    # Metadata
    description: str = ""
    useful_life_years: int = 20
    notes: str = ""

    @property
    def net_capex(self) -> float:
        """Capital cost minus upfront incentives."""
        upfront_incentives = sum(
            inc.get('amount', 0)
            for inc in self.incentives
            if inc.get('pays_in_year', 0) == 0
        )
        return self.capex - upfront_incentives

    @property
    def total_incentives(self) -> float:
        """Sum of all incentives."""
        return sum(inc.get('amount', 0) for inc in self.incentives)

    def get_kwh_impact(self, baseline_kwh: float = 0) -> float:
        """
        Calculate total kWh impact of this ECM.

        Args:
            baseline_kwh: Baseline consumption (needed for percentage calc)

        Returns:
            Net kWh change (negative = reduction, positive for generation)
        """
        impact = self.annual_kwh_delta

        if self.annual_kwh_pct != 0 and baseline_kwh > 0:
            impact += baseline_kwh * self.annual_kwh_pct

        # Generation is positive (offsets consumption)
        impact -= self.annual_kwh_generation

        return impact

    def get_therm_impact(self, baseline_therms: float = 0) -> float:
        """
        Calculate total therm impact of this ECM.

        Args:
            baseline_therms: Baseline consumption (needed for percentage calc)

        Returns:
            Net therm change (negative = reduction)
        """
        impact = self.annual_therm_delta

        if self.annual_therm_pct != 0 and baseline_therms > 0:
            impact += baseline_therms * self.annual_therm_pct

        return impact


@dataclass
class ECMAnalysisResult:
    """Results from analyzing an individual ECM."""
    ecm_name: str
    ecm_category: ECMCategory

    # Costs
    capex: float
    net_capex: float
    total_incentives: float

    # Energy impacts
    annual_kwh_impact: float
    annual_therm_impact: float
    annual_generation_kwh: float

    # Financial results (from LCCA)
    annual_cost_savings: float
    npv: float
    irr: Optional[float]
    simple_payback_years: Optional[float]
    sir: Optional[float]

    # Cost effectiveness
    cost_per_kwh_saved: Optional[float] = None  # $/kWh lifetime
    cost_per_therm_saved: Optional[float] = None


@dataclass
class ECMBundle:
    """
    Bundle of Energy Conservation Measures for a project.

    Manages multiple ECMs and enables:
    - Adding/removing ECMs
    - Calculating combined costs and impacts
    - Analyzing marginal value of individual ECMs
    - Creating scenarios with different ECM combinations

    Example:
        >>> bundle = ECMBundle("Gibraltar ECMs")
        >>> bundle.add_ecm(pv_ecm)
        >>> bundle.add_ecm(electrification_ecm)
        >>> bundle.add_ecm(led_ecm)
        >>>
        >>> # Get total package cost
        >>> print(f"Total CapEx: ${bundle.total_capex:,.0f}")
        >>>
        >>> # Analyze individual ECM
        >>> pv_analysis = bundle.analyze_ecm("343 kW PV", scenario_manager)
    """
    name: str = "ECM Bundle"
    _ecms: Dict[str, ECM] = field(default_factory=dict)

    def add_ecm(self, ecm: ECM) -> None:
        """
        Add an ECM to the bundle.

        Args:
            ecm: ECM to add

        Raises:
            ValueError: If ECM with same name already exists
        """
        if ecm.name in self._ecms:
            raise ValueError(f"ECM '{ecm.name}' already exists in bundle")
        self._ecms[ecm.name] = ecm

    def remove_ecm(self, name: str) -> None:
        """Remove an ECM from the bundle."""
        if name in self._ecms:
            del self._ecms[name]

    def get_ecm(self, name: str) -> ECM:
        """
        Get an ECM by name.

        Raises:
            KeyError: If ECM not found
        """
        if name not in self._ecms:
            raise KeyError(f"ECM '{name}' not found. Available: {self.ecm_names}")
        return self._ecms[name]

    @property
    def ecm_names(self) -> List[str]:
        """List of ECM names in the bundle."""
        return list(self._ecms.keys())

    @property
    def ecm_count(self) -> int:
        """Number of ECMs in the bundle."""
        return len(self._ecms)

    @property
    def total_capex(self) -> float:
        """Total capital cost of all ECMs."""
        return sum(ecm.capex for ecm in self._ecms.values())

    @property
    def total_net_capex(self) -> float:
        """Total capital cost minus incentives."""
        return sum(ecm.net_capex for ecm in self._ecms.values())

    @property
    def total_incentives(self) -> float:
        """Total incentives for all ECMs."""
        return sum(ecm.total_incentives for ecm in self._ecms.values())

    @property
    def total_annual_opex(self) -> float:
        """Total annual operating cost change."""
        return sum(ecm.opex_annual for ecm in self._ecms.values())

    @property
    def total_annual_maintenance(self) -> float:
        """Total annual maintenance cost change."""
        return sum(ecm.maintenance_annual for ecm in self._ecms.values())

    def get_ecms_by_category(self, category: ECMCategory) -> List[ECM]:
        """Get all ECMs in a specific category."""
        return [ecm for ecm in self._ecms.values() if ecm.category == category]

    def get_category_capex(self, category: ECMCategory) -> float:
        """Get total capex for a category."""
        return sum(ecm.capex for ecm in self.get_ecms_by_category(category))

    def get_total_kwh_impact(self, baseline_kwh: float = 0) -> float:
        """
        Get combined kWh impact of all ECMs.

        Args:
            baseline_kwh: Baseline consumption for percentage calculations

        Returns:
            Net kWh change
        """
        return sum(ecm.get_kwh_impact(baseline_kwh) for ecm in self._ecms.values())

    def get_total_therm_impact(self, baseline_therms: float = 0) -> float:
        """
        Get combined therm impact of all ECMs.

        Args:
            baseline_therms: Baseline consumption for percentage calculations

        Returns:
            Net therm change
        """
        return sum(ecm.get_therm_impact(baseline_therms) for ecm in self._ecms.values())

    def get_total_generation(self) -> float:
        """Get total annual generation from all ECMs."""
        return sum(ecm.annual_kwh_generation for ecm in self._ecms.values())

    def create_subset(self, ecm_names: List[str]) -> "ECMBundle":
        """
        Create a new bundle with only specified ECMs.

        Args:
            ecm_names: Names of ECMs to include

        Returns:
            New ECMBundle with subset of ECMs
        """
        subset = ECMBundle(name=f"{self.name} (subset)")
        for name in ecm_names:
            if name in self._ecms:
                subset.add_ecm(self._ecms[name])
        return subset

    def create_excluding(self, ecm_names: List[str]) -> "ECMBundle":
        """
        Create a new bundle excluding specified ECMs.

        Args:
            ecm_names: Names of ECMs to exclude

        Returns:
            New ECMBundle without specified ECMs
        """
        exclude_set = set(ecm_names)
        subset = ECMBundle(name=f"{self.name} (excluding)")
        for name, ecm in self._ecms.items():
            if name not in exclude_set:
                subset.add_ecm(ecm)
        return subset

    def summary_table(self) -> str:
        """
        Generate a summary table of all ECMs.

        Returns:
            Formatted text table
        """
        lines = [
            "=" * 90,
            f"ECM BUNDLE: {self.name}",
            "=" * 90,
            "",
            f"{'ECM Name':<30} {'Category':<12} {'CapEx':>12} {'Incentives':>12} {'Net CapEx':>12}",
            "-" * 90,
        ]

        for ecm in self._ecms.values():
            lines.append(
                f"{ecm.name:<30} {ecm.category.value:<12} "
                f"${ecm.capex:>11,.0f} ${ecm.total_incentives:>11,.0f} "
                f"${ecm.net_capex:>11,.0f}"
            )

        lines.extend([
            "-" * 90,
            f"{'TOTAL':<30} {'':<12} "
            f"${self.total_capex:>11,.0f} ${self.total_incentives:>11,.0f} "
            f"${self.total_net_capex:>11,.0f}",
            "=" * 90,
        ])

        return "\n".join(lines)


# =============================================================================
# ECM Library - Centralized ECM Template Management
# =============================================================================

@dataclass
class ECMTemplate:
    """
    Template for creating ECMs with default values.

    Templates define the structure and defaults for ECM types,
    allowing consistent ECM creation with project-specific overrides.
    """
    template_id: str
    name_template: str  # e.g., "{capacity_kw} kW PV System"
    category: ECMCategory
    subcategory: ECMSubcategory
    description: str

    # Default cost parameters
    default_cost_per_unit: float = 0.0
    cost_unit: str = "each"  # "watt", "sqft", "ton", "cfm", etc.

    # Default energy parameters
    default_savings_pct: float = 0.0
    default_generation_per_unit: float = 0.0

    # Applicability
    applicable_building_types: List[BuildingType] = field(
        default_factory=lambda: [BuildingType.ALL]
    )
    climate_zones: List[int] = field(default_factory=lambda: list(range(1, 17)))

    # Metadata
    useful_life_years: int = 20
    source: str = ""
    vintage: int = 2024


class ECMLibrary:
    """
    Centralized library of ECM templates.

    Provides:
    - Pre-defined templates for common ECMs (OpenStudio BCL + CEC CASE)
    - Filtering by category, building type, climate zone
    - Template instantiation with project-specific parameters
    - JSON import/export for custom ECM definitions

    Example:
        >>> lib = ECMLibrary()
        >>> lib.list_by_category(ECMCategory.HVAC)
        ['heat_pump_minisplit', 'vrf_system', 'erv_residential', ...]
        >>>
        >>> hp_ecm = lib.create_ecm('heat_pump_minisplit', unit_count=54, tons_per_unit=1.5)
    """

    def __init__(self):
        self._templates: Dict[str, ECMTemplate] = {}
        self._load_default_templates()

    def _load_default_templates(self) -> None:
        """Load built-in ECM templates."""
        # Templates are organized by category
        self._load_generation_templates()
        self._load_envelope_templates()
        self._load_hvac_templates()
        self._load_dhw_templates()
        self._load_lighting_templates()
        self._load_controls_templates()
        self._load_refrigeration_templates()
        self._load_electrification_templates()

    def _load_generation_templates(self) -> None:
        """Load generation ECM templates."""
        self._templates['pv_rooftop'] = ECMTemplate(
            template_id='pv_rooftop',
            name_template='{capacity_kw:.0f} kW Rooftop PV',
            category=ECMCategory.GENERATION,
            subcategory=ECMSubcategory.PHOTOVOLTAIC,
            description='Rooftop photovoltaic system',
            default_cost_per_unit=2.50,  # $/W installed
            cost_unit='watt',
            default_generation_per_unit=1500,  # kWh/kW/year
            useful_life_years=25,
            source='NREL ATB 2024',
            vintage=2024,
        )
        self._templates['pv_carport'] = ECMTemplate(
            template_id='pv_carport',
            name_template='{capacity_kw:.0f} kW Carport PV',
            category=ECMCategory.GENERATION,
            subcategory=ECMSubcategory.PHOTOVOLTAIC,
            description='Carport/canopy photovoltaic system',
            default_cost_per_unit=3.50,  # $/W installed (higher for structure)
            cost_unit='watt',
            default_generation_per_unit=1550,  # Slightly better tilt
            useful_life_years=25,
            source='NREL ATB 2024',
            vintage=2024,
        )
        self._templates['battery_storage'] = ECMTemplate(
            template_id='battery_storage',
            name_template='{capacity_kwh:.0f} kWh Battery Storage',
            category=ECMCategory.STORAGE,
            subcategory=ECMSubcategory.BATTERY,
            description='Lithium-ion battery energy storage',
            default_cost_per_unit=500,  # $/kWh
            cost_unit='kwh',
            useful_life_years=15,
            source='NREL ATB 2024',
            vintage=2024,
        )

    def _load_envelope_templates(self) -> None:
        """Load envelope ECM templates (BCL: 88 measures)."""
        # Opaque envelope (41 BCL measures)
        self._templates['wall_insulation_upgrade'] = ECMTemplate(
            template_id='wall_insulation_upgrade',
            name_template='Wall Insulation R-{r_value}',
            category=ECMCategory.ENVELOPE,
            subcategory=ECMSubcategory.ENVELOPE_OPAQUE,
            description='Exterior wall insulation upgrade',
            default_cost_per_unit=2.50,  # $/sqft
            cost_unit='sqft',
            default_savings_pct=0.08,  # 8% heating/cooling savings
            useful_life_years=30,
            source='RSMeans 2024',
            vintage=2024,
        )
        self._templates['roof_insulation_upgrade'] = ECMTemplate(
            template_id='roof_insulation_upgrade',
            name_template='Roof Insulation R-{r_value}',
            category=ECMCategory.ENVELOPE,
            subcategory=ECMSubcategory.ENVELOPE_OPAQUE,
            description='Roof/attic insulation upgrade',
            default_cost_per_unit=1.80,  # $/sqft
            cost_unit='sqft',
            default_savings_pct=0.12,  # 12% heating/cooling savings
            useful_life_years=30,
            source='RSMeans 2024',
            vintage=2024,
        )
        self._templates['cool_roof'] = ECMTemplate(
            template_id='cool_roof',
            name_template='Cool Roof (SRI {sri})',
            category=ECMCategory.ENVELOPE,
            subcategory=ECMSubcategory.ENVELOPE_COOL_ROOF,
            description='High solar reflectance roofing',
            default_cost_per_unit=0.50,  # $/sqft premium
            cost_unit='sqft',
            default_savings_pct=0.10,  # 10% cooling savings
            applicable_building_types=[BuildingType.ALL_COMMERCIAL],
            climate_zones=[2, 4, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15],  # Hot zones
            useful_life_years=20,
            source='CEC CASE 2025',
            vintage=2024,
        )

        # Fenestration (12 BCL measures)
        self._templates['window_upgrade_double'] = ECMTemplate(
            template_id='window_upgrade_double',
            name_template='Double-Pane Low-E Windows (U-{u_factor})',
            category=ECMCategory.ENVELOPE,
            subcategory=ECMSubcategory.ENVELOPE_FENESTRATION,
            description='Double-pane low-e window replacement',
            default_cost_per_unit=45,  # $/sqft
            cost_unit='sqft',
            default_savings_pct=0.10,  # 10% HVAC savings
            useful_life_years=25,
            source='RSMeans 2024',
            vintage=2024,
        )
        self._templates['window_upgrade_triple'] = ECMTemplate(
            template_id='window_upgrade_triple',
            name_template='Triple-Pane Windows (U-{u_factor})',
            category=ECMCategory.ENVELOPE,
            subcategory=ECMSubcategory.ENVELOPE_FENESTRATION,
            description='Triple-pane window replacement',
            default_cost_per_unit=75,  # $/sqft
            cost_unit='sqft',
            default_savings_pct=0.15,  # 15% HVAC savings
            climate_zones=[1, 16],  # Cold climates
            useful_life_years=30,
            source='RSMeans 2024',
            vintage=2024,
        )

        # Infiltration (8 BCL measures)
        self._templates['air_sealing'] = ECMTemplate(
            template_id='air_sealing',
            name_template='Air Sealing ({ach50} ACH50)',
            category=ECMCategory.ENVELOPE,
            subcategory=ECMSubcategory.ENVELOPE_INFILTRATION,
            description='Building envelope air sealing',
            default_cost_per_unit=0.75,  # $/sqft floor area
            cost_unit='sqft',
            default_savings_pct=0.08,  # 8% heating/cooling savings
            useful_life_years=20,
            source='DEER 2024',
            vintage=2024,
        )

    def _load_hvac_templates(self) -> None:
        """Load HVAC ECM templates (BCL: 69 measures)."""
        # Heating (8 BCL measures)
        self._templates['ashp_ducted'] = ECMTemplate(
            template_id='ashp_ducted',
            name_template='Ducted ASHP (SEER {seer}/HSPF {hspf})',
            category=ECMCategory.HVAC,
            subcategory=ECMSubcategory.HVAC_HEATING,
            description='Ducted air-source heat pump',
            default_cost_per_unit=4000,  # $/ton
            cost_unit='ton',
            default_savings_pct=0.30,  # vs gas furnace + AC
            useful_life_years=15,
            source='CEC CASE 2025',
            vintage=2024,
        )
        self._templates['minisplit'] = ECMTemplate(
            template_id='minisplit',
            name_template='Ductless Mini-Split ({seer} SEER/{hspf} HSPF)',
            category=ECMCategory.HVAC,
            subcategory=ECMSubcategory.HVAC_HEATING,
            description='Ductless mini-split heat pump',
            default_cost_per_unit=3500,  # $/ton
            cost_unit='ton',
            default_savings_pct=0.35,  # High efficiency
            applicable_building_types=[
                BuildingType.SINGLE_FAMILY,
                BuildingType.MULTIFAMILY_LOW,
                BuildingType.MULTIFAMILY_HIGH,
            ],
            useful_life_years=15,
            source='CEC CASE 2025',
            vintage=2024,
        )
        self._templates['gshp'] = ECMTemplate(
            template_id='gshp',
            name_template='Ground-Source Heat Pump (COP {cop})',
            category=ECMCategory.HVAC,
            subcategory=ECMSubcategory.HVAC_HEATING,
            description='Ground-source (geothermal) heat pump',
            default_cost_per_unit=8000,  # $/ton (includes ground loop)
            cost_unit='ton',
            default_savings_pct=0.45,  # High efficiency
            useful_life_years=25,
            source='ASHRAE',
            vintage=2024,
        )

        # Cooling (14 BCL measures)
        self._templates['high_eff_chiller'] = ECMTemplate(
            template_id='high_eff_chiller',
            name_template='High-Efficiency Chiller ({kw_per_ton} kW/ton)',
            category=ECMCategory.HVAC,
            subcategory=ECMSubcategory.HVAC_COOLING,
            description='High-efficiency centrifugal/screw chiller',
            default_cost_per_unit=800,  # $/ton
            cost_unit='ton',
            default_savings_pct=0.20,  # 20% cooling savings
            applicable_building_types=[BuildingType.ALL_COMMERCIAL],
            useful_life_years=25,
            source='ASHRAE 90.1-2022',
            vintage=2024,
        )
        self._templates['evap_cooling'] = ECMTemplate(
            template_id='evap_cooling',
            name_template='Indirect Evaporative Cooling',
            category=ECMCategory.HVAC,
            subcategory=ECMSubcategory.HVAC_COOLING,
            description='Indirect/direct evaporative pre-cooling',
            default_cost_per_unit=3.00,  # $/cfm
            cost_unit='cfm',
            default_savings_pct=0.25,  # 25% cooling savings
            climate_zones=[2, 3, 4, 10, 11, 12, 13, 14, 15, 16],  # Dry climates
            useful_life_years=20,
            source='CEC CASE',
            vintage=2024,
        )

        # Ventilation (6 BCL measures)
        self._templates['erv_residential'] = ECMTemplate(
            template_id='erv_residential',
            name_template='Residential ERV ({cfm} CFM)',
            category=ECMCategory.HVAC,
            subcategory=ECMSubcategory.HVAC_ENERGY_RECOVERY,
            description='Energy recovery ventilator for dwelling units',
            default_cost_per_unit=1200,  # $/unit
            cost_unit='each',
            default_savings_pct=0.15,  # Heating/cooling recovery
            applicable_building_types=[
                BuildingType.SINGLE_FAMILY,
                BuildingType.MULTIFAMILY_LOW,
                BuildingType.MULTIFAMILY_HIGH,
            ],
            useful_life_years=15,
            source='CEC CASE 2025',
            vintage=2024,
        )
        self._templates['erv_commercial'] = ECMTemplate(
            template_id='erv_commercial',
            name_template='Commercial ERV ({effectiveness}% effectiveness)',
            category=ECMCategory.HVAC,
            subcategory=ECMSubcategory.HVAC_ENERGY_RECOVERY,
            description='Commercial energy recovery wheel/plate',
            default_cost_per_unit=5.00,  # $/cfm
            cost_unit='cfm',
            default_savings_pct=0.20,  # 20% OA heating/cooling
            applicable_building_types=[BuildingType.ALL_COMMERCIAL],
            useful_life_years=20,
            source='ASHRAE 90.1-2022',
            vintage=2024,
        )
        self._templates['doas'] = ECMTemplate(
            template_id='doas',
            name_template='Dedicated Outdoor Air System',
            category=ECMCategory.HVAC,
            subcategory=ECMSubcategory.HVAC_VENTILATION,
            description='DOAS with energy recovery',
            default_cost_per_unit=8.00,  # $/cfm
            cost_unit='cfm',
            default_savings_pct=0.25,  # 25% OA load reduction
            applicable_building_types=[BuildingType.ALL_COMMERCIAL],
            useful_life_years=20,
            source='ASHRAE',
            vintage=2024,
        )
        self._templates['dcv'] = ECMTemplate(
            template_id='dcv',
            name_template='Demand Control Ventilation (DCV)',
            category=ECMCategory.HVAC,
            subcategory=ECMSubcategory.HVAC_VENTILATION,
            description='CO2-based demand control ventilation',
            default_cost_per_unit=1.50,  # $/sqft
            cost_unit='sqft',
            default_savings_pct=0.15,  # 15% OA reduction
            applicable_building_types=[BuildingType.ALL_COMMERCIAL],
            useful_life_years=15,
            source='CEC CASE 2025',
            vintage=2024,
        )

        # Distribution (7 BCL measures)
        self._templates['duct_sealing'] = ECMTemplate(
            template_id='duct_sealing',
            name_template='Duct Sealing ({leakage_pct}% leakage)',
            category=ECMCategory.HVAC,
            subcategory=ECMSubcategory.HVAC_DISTRIBUTION,
            description='Ductwork sealing and insulation',
            default_cost_per_unit=0.80,  # $/sqft floor area
            cost_unit='sqft',
            default_savings_pct=0.10,  # 10% distribution savings
            useful_life_years=20,
            source='DEER 2024',
            vintage=2024,
        )
        self._templates['vav_conversion'] = ECMTemplate(
            template_id='vav_conversion',
            name_template='CAV to VAV Conversion',
            category=ECMCategory.HVAC,
            subcategory=ECMSubcategory.HVAC_DISTRIBUTION,
            description='Convert constant volume to VAV',
            default_cost_per_unit=4.00,  # $/cfm
            cost_unit='cfm',
            default_savings_pct=0.25,  # 25% fan energy savings
            applicable_building_types=[BuildingType.ALL_COMMERCIAL],
            useful_life_years=20,
            source='ASHRAE',
            vintage=2024,
        )

        # HVAC Controls (5 BCL measures)
        self._templates['economizer'] = ECMTemplate(
            template_id='economizer',
            name_template='Airside Economizer',
            category=ECMCategory.HVAC,
            subcategory=ECMSubcategory.HVAC_CONTROLS,
            description='Airside economizer with DX lockout',
            default_cost_per_unit=2.00,  # $/cfm
            cost_unit='cfm',
            default_savings_pct=0.15,  # 15% cooling savings
            applicable_building_types=[BuildingType.ALL_COMMERCIAL],
            useful_life_years=15,
            source='CEC T24-2025',
            vintage=2024,
        )
        self._templates['setpoint_reset'] = ECMTemplate(
            template_id='setpoint_reset',
            name_template='Supply Air/Water Temperature Reset',
            category=ECMCategory.HVAC,
            subcategory=ECMSubcategory.HVAC_CONTROLS,
            description='Optimal setpoint reset based on load',
            default_cost_per_unit=0.50,  # $/sqft
            cost_unit='sqft',
            default_savings_pct=0.10,  # 10% HVAC savings
            applicable_building_types=[BuildingType.ALL_COMMERCIAL],
            useful_life_years=15,
            source='ASHRAE Guideline 36',
            vintage=2024,
        )

        # Whole System (28 BCL measures)
        self._templates['vrf'] = ECMTemplate(
            template_id='vrf',
            name_template='VRF System ({seer} SEER)',
            category=ECMCategory.HVAC,
            subcategory=ECMSubcategory.HVAC_WHOLE_SYSTEM,
            description='Variable Refrigerant Flow system',
            default_cost_per_unit=5000,  # $/ton
            cost_unit='ton',
            default_savings_pct=0.30,  # 30% vs conventional
            applicable_building_types=[
                BuildingType.OFFICE_SMALL,
                BuildingType.OFFICE_LARGE,
                BuildingType.HOTEL,
                BuildingType.MULTIFAMILY_HIGH,
            ],
            useful_life_years=20,
            source='ASHRAE',
            vintage=2024,
        )
        self._templates['central_vent_supply'] = ECMTemplate(
            template_id='central_vent_supply',
            name_template='Central Supply Ventilation',
            category=ECMCategory.HVAC,
            subcategory=ECMSubcategory.HVAC_WHOLE_SYSTEM,
            description='Central supply ventilation system (Maestro-type)',
            default_cost_per_unit=500,  # $/unit
            cost_unit='each',
            applicable_building_types=[
                BuildingType.MULTIFAMILY_LOW,
                BuildingType.MULTIFAMILY_HIGH,
            ],
            useful_life_years=20,
            source='CEC CASE 2025',
            vintage=2024,
        )

    def _load_dhw_templates(self) -> None:
        """Load domestic hot water ECM templates (BCL: 6 measures)."""
        self._templates['hpwh_residential'] = ECMTemplate(
            template_id='hpwh_residential',
            name_template='Residential HPWH (UEF {uef})',
            category=ECMCategory.DHW,
            subcategory=ECMSubcategory.DHW_HEAT_PUMP,
            description='Heat pump water heater for dwelling units',
            default_cost_per_unit=2500,  # $/unit
            cost_unit='each',
            default_savings_pct=0.65,  # 65% vs gas
            applicable_building_types=[
                BuildingType.SINGLE_FAMILY,
                BuildingType.MULTIFAMILY_LOW,
                BuildingType.MULTIFAMILY_HIGH,
            ],
            useful_life_years=12,
            source='CEC CASE 2025',
            vintage=2024,
        )
        self._templates['hpwh_central'] = ECMTemplate(
            template_id='hpwh_central',
            name_template='Central HPWH System (COP {cop})',
            category=ECMCategory.DHW,
            subcategory=ECMSubcategory.DHW_HEAT_PUMP,
            description='Central heat pump water heating',
            default_cost_per_unit=200,  # $/gallon storage
            cost_unit='gallon',
            default_savings_pct=0.60,  # 60% vs gas
            applicable_building_types=[
                BuildingType.MULTIFAMILY_HIGH,
                BuildingType.HOTEL,
                BuildingType.HEALTHCARE,
            ],
            useful_life_years=15,
            source='CEC CASE 2025',
            vintage=2024,
        )
        self._templates['pipe_insulation'] = ECMTemplate(
            template_id='pipe_insulation',
            name_template='DHW Pipe Insulation (R-{r_value})',
            category=ECMCategory.DHW,
            subcategory=ECMSubcategory.DHW_DISTRIBUTION,
            description='Hot water pipe insulation upgrade',
            default_cost_per_unit=3.00,  # $/linear foot
            cost_unit='linear_foot',
            default_savings_pct=0.08,  # 8% DHW savings
            useful_life_years=25,
            source='T24-2025',
            vintage=2024,
        )
        self._templates['solar_thermal'] = ECMTemplate(
            template_id='solar_thermal',
            name_template='Solar Thermal DHW ({sqft} sqft)',
            category=ECMCategory.DHW,
            subcategory=ECMSubcategory.DHW_SOLAR,
            description='Solar thermal water heating',
            default_cost_per_unit=100,  # $/sqft collector
            cost_unit='sqft',
            default_savings_pct=0.50,  # 50% DHW load offset
            climate_zones=[1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15],
            useful_life_years=20,
            source='SRCC',
            vintage=2024,
        )

    def _load_lighting_templates(self) -> None:
        """Load lighting ECM templates (BCL: 15 measures)."""
        # Equipment (10 BCL measures)
        self._templates['led_interior'] = ECMTemplate(
            template_id='led_interior',
            name_template='LED Interior Lighting ({lpd} W/sqft)',
            category=ECMCategory.LIGHTING,
            subcategory=ECMSubcategory.LIGHTING_EQUIPMENT,
            description='LED interior lighting retrofit',
            default_cost_per_unit=3.00,  # $/sqft
            cost_unit='sqft',
            default_savings_pct=0.40,  # 40% lighting savings
            useful_life_years=15,
            source='DEER 2024',
            vintage=2024,
        )
        self._templates['led_exterior'] = ECMTemplate(
            template_id='led_exterior',
            name_template='LED Exterior Lighting',
            category=ECMCategory.LIGHTING,
            subcategory=ECMSubcategory.LIGHTING_EQUIPMENT,
            description='LED site/parking lighting',
            default_cost_per_unit=500,  # $/fixture
            cost_unit='each',
            default_savings_pct=0.50,  # 50% savings
            useful_life_years=15,
            source='DEER 2024',
            vintage=2024,
        )

        # Controls (5 BCL measures)
        self._templates['occupancy_sensors'] = ECMTemplate(
            template_id='occupancy_sensors',
            name_template='Occupancy Sensors',
            category=ECMCategory.LIGHTING,
            subcategory=ECMSubcategory.LIGHTING_CONTROLS,
            description='Occupancy-based lighting controls',
            default_cost_per_unit=1.50,  # $/sqft
            cost_unit='sqft',
            default_savings_pct=0.20,  # 20% additional savings
            applicable_building_types=[BuildingType.ALL_COMMERCIAL],
            useful_life_years=15,
            source='DEER 2024',
            vintage=2024,
        )
        self._templates['daylight_dimming'] = ECMTemplate(
            template_id='daylight_dimming',
            name_template='Daylight Dimming Controls',
            category=ECMCategory.LIGHTING,
            subcategory=ECMSubcategory.LIGHTING_CONTROLS,
            description='Photosensor-based daylight dimming',
            default_cost_per_unit=2.00,  # $/sqft
            cost_unit='sqft',
            default_savings_pct=0.25,  # 25% perimeter savings
            applicable_building_types=[BuildingType.ALL_COMMERCIAL],
            useful_life_years=15,
            source='T24-2025',
            vintage=2024,
        )

    def _load_controls_templates(self) -> None:
        """Load controls ECM templates."""
        self._templates['ems_bms'] = ECMTemplate(
            template_id='ems_bms',
            name_template='Energy Management System',
            category=ECMCategory.CONTROLS,
            subcategory=ECMSubcategory.CONTROLS_BMS,
            description='Building energy management system',
            default_cost_per_unit=0.75,  # $/sqft
            cost_unit='sqft',
            default_savings_pct=0.10,  # 10% whole building
            applicable_building_types=[BuildingType.ALL_COMMERCIAL],
            useful_life_years=15,
            source='ASHRAE',
            vintage=2024,
        )
        self._templates['guideline_36'] = ECMTemplate(
            template_id='guideline_36',
            name_template='ASHRAE Guideline 36 Controls',
            category=ECMCategory.CONTROLS,
            subcategory=ECMSubcategory.CONTROLS_GUIDELINE36,
            description='Advanced HVAC control sequences per G36',
            default_cost_per_unit=1.00,  # $/sqft
            cost_unit='sqft',
            default_savings_pct=0.15,  # 15% HVAC savings
            applicable_building_types=[BuildingType.ALL_COMMERCIAL],
            useful_life_years=15,
            source='CEC CASE 2025',
            vintage=2024,
        )
        self._templates['fdd'] = ECMTemplate(
            template_id='fdd',
            name_template='Fault Detection & Diagnostics',
            category=ECMCategory.CONTROLS,
            subcategory=ECMSubcategory.CONTROLS_FDD,
            description='Automated fault detection system',
            default_cost_per_unit=0.50,  # $/sqft
            cost_unit='sqft',
            default_savings_pct=0.08,  # 8% ongoing savings
            applicable_building_types=[BuildingType.ALL_COMMERCIAL],
            useful_life_years=10,
            source='CEC CASE 2025',
            vintage=2024,
        )

    def _load_refrigeration_templates(self) -> None:
        """Load refrigeration ECM templates."""
        self._templates['walkin_ec_motors'] = ECMTemplate(
            template_id='walkin_ec_motors',
            name_template='Walk-in EC Evaporator Motors',
            category=ECMCategory.REFRIGERATION,
            subcategory=ECMSubcategory.REFRIG_EVAPORATOR,
            description='ECM evaporator fan motors for walk-ins',
            default_cost_per_unit=400,  # $/motor
            cost_unit='each',
            default_savings_pct=0.30,  # 30% fan savings
            applicable_building_types=[
                BuildingType.RESTAURANT,
                BuildingType.RETAIL,
                BuildingType.WAREHOUSE,
            ],
            useful_life_years=15,
            source='CEC CASE 2025',
            vintage=2024,
        )
        self._templates['display_case_led'] = ECMTemplate(
            template_id='display_case_led',
            name_template='Display Case LED Lighting',
            category=ECMCategory.REFRIGERATION,
            subcategory=ECMSubcategory.REFRIG_DISPLAY,
            description='LED lighting for refrigerated display cases',
            default_cost_per_unit=150,  # $/linear foot
            cost_unit='linear_foot',
            default_savings_pct=0.50,  # 50% lighting + reduced heat
            applicable_building_types=[BuildingType.RETAIL],
            useful_life_years=12,
            source='DEER 2024',
            vintage=2024,
        )

    def _load_electrification_templates(self) -> None:
        """
        Load electrification ECM templates.

        Supports Title 24 2025 requirements for electric-ready buildings
        and California's gas phase-out initiatives.
        """
        # Induction cooking (replacing gas range)
        self._templates['induction_cooktop'] = ECMTemplate(
            template_id='induction_cooktop',
            name_template='Induction Cooktop',
            category=ECMCategory.PLUGLOAD,
            subcategory=ECMSubcategory.ELEC_COOKING,
            description='Induction cooktop replacing gas range',
            default_cost_per_unit=1200,  # $/unit premium over gas
            cost_unit='each',
            default_savings_pct=0.0,  # Energy neutral, fuel switch
            applicable_building_types=[
                BuildingType.SINGLE_FAMILY,
                BuildingType.MULTIFAMILY_LOW,
                BuildingType.MULTIFAMILY_HIGH,
            ],
            useful_life_years=15,
            source='CEC CASE 2025',
            vintage=2024,
        )
        self._templates['induction_range'] = ECMTemplate(
            template_id='induction_range',
            name_template='Induction Range (Full)',
            category=ECMCategory.PLUGLOAD,
            subcategory=ECMSubcategory.ELEC_COOKING,
            description='Full induction range with oven',
            default_cost_per_unit=2500,  # $/unit
            cost_unit='each',
            default_savings_pct=0.0,
            applicable_building_types=[
                BuildingType.SINGLE_FAMILY,
                BuildingType.MULTIFAMILY_LOW,
                BuildingType.MULTIFAMILY_HIGH,
            ],
            useful_life_years=15,
            source='CEC CASE 2025',
            vintage=2024,
        )

        # Electric dryer (replacing gas)
        self._templates['electric_dryer'] = ECMTemplate(
            template_id='electric_dryer',
            name_template='Electric Dryer',
            category=ECMCategory.PLUGLOAD,
            subcategory=ECMSubcategory.ELEC_DRYER,
            description='Electric dryer replacing gas dryer',
            default_cost_per_unit=800,  # $/unit
            cost_unit='each',
            default_savings_pct=0.0,
            applicable_building_types=[
                BuildingType.SINGLE_FAMILY,
                BuildingType.MULTIFAMILY_LOW,
                BuildingType.MULTIFAMILY_HIGH,
            ],
            useful_life_years=12,
            source='Energy Star',
            vintage=2024,
        )
        self._templates['heat_pump_dryer'] = ECMTemplate(
            template_id='heat_pump_dryer',
            name_template='Heat Pump Dryer',
            category=ECMCategory.PLUGLOAD,
            subcategory=ECMSubcategory.ELEC_DRYER,
            description='Heat pump dryer (high efficiency)',
            default_cost_per_unit=1400,  # $/unit premium
            cost_unit='each',
            default_savings_pct=0.50,  # 50% more efficient than standard
            applicable_building_types=[
                BuildingType.SINGLE_FAMILY,
                BuildingType.MULTIFAMILY_LOW,
                BuildingType.MULTIFAMILY_HIGH,
            ],
            useful_life_years=15,
            source='Energy Star',
            vintage=2024,
        )

        # Electric-ready infrastructure
        self._templates['elec_ready_cooking'] = ECMTemplate(
            template_id='elec_ready_cooking',
            name_template='Electric-Ready Cooking Infrastructure',
            category=ECMCategory.OTHER,
            subcategory=ECMSubcategory.ELEC_READY,
            description='240V circuit for future electric cooking',
            default_cost_per_unit=500,  # $/unit
            cost_unit='each',
            default_savings_pct=0.0,
            applicable_building_types=[BuildingType.ALL_RESIDENTIAL],
            useful_life_years=40,
            source='CEC CASE 2025',
            vintage=2024,
        )
        self._templates['elec_ready_dryer'] = ECMTemplate(
            template_id='elec_ready_dryer',
            name_template='Electric-Ready Dryer Infrastructure',
            category=ECMCategory.OTHER,
            subcategory=ECMSubcategory.ELEC_READY,
            description='240V circuit for future electric dryer',
            default_cost_per_unit=400,  # $/unit
            cost_unit='each',
            default_savings_pct=0.0,
            applicable_building_types=[BuildingType.ALL_RESIDENTIAL],
            useful_life_years=40,
            source='CEC CASE 2025',
            vintage=2024,
        )
        self._templates['elec_ready_hvac'] = ECMTemplate(
            template_id='elec_ready_hvac',
            name_template='Electric-Ready HVAC Infrastructure',
            category=ECMCategory.OTHER,
            subcategory=ECMSubcategory.ELEC_READY,
            description='Infrastructure for future heat pump conversion',
            default_cost_per_unit=800,  # $/unit
            cost_unit='each',
            default_savings_pct=0.0,
            applicable_building_types=[BuildingType.ALL_RESIDENTIAL],
            useful_life_years=40,
            source='CEC CASE 2025',
            vintage=2024,
        )
        self._templates['elec_ready_water_heater'] = ECMTemplate(
            template_id='elec_ready_water_heater',
            name_template='Electric-Ready Water Heater Infrastructure',
            category=ECMCategory.OTHER,
            subcategory=ECMSubcategory.ELEC_READY,
            description='240V/30A circuit for future HPWH',
            default_cost_per_unit=600,  # $/unit
            cost_unit='each',
            default_savings_pct=0.0,
            applicable_building_types=[BuildingType.ALL_RESIDENTIAL],
            useful_life_years=40,
            source='CEC CASE 2025',
            vintage=2024,
        )

        # Panel upgrade
        self._templates['panel_upgrade_200a'] = ECMTemplate(
            template_id='panel_upgrade_200a',
            name_template='Panel Upgrade to 200A',
            category=ECMCategory.OTHER,
            subcategory=ECMSubcategory.ELEC_PANEL,
            description='Electrical panel upgrade to 200A for electrification',
            default_cost_per_unit=3500,  # $/panel
            cost_unit='each',
            default_savings_pct=0.0,
            applicable_building_types=[BuildingType.SINGLE_FAMILY],
            useful_life_years=40,
            source='RSMeans 2024',
            vintage=2024,
        )
        self._templates['panel_upgrade_400a'] = ECMTemplate(
            template_id='panel_upgrade_400a',
            name_template='Panel Upgrade to 400A',
            category=ECMCategory.OTHER,
            subcategory=ECMSubcategory.ELEC_PANEL,
            description='Electrical panel upgrade to 400A for full electrification + EV',
            default_cost_per_unit=6000,  # $/panel
            cost_unit='each',
            default_savings_pct=0.0,
            applicable_building_types=[BuildingType.SINGLE_FAMILY],
            useful_life_years=40,
            source='RSMeans 2024',
            vintage=2024,
        )
        self._templates['smart_panel'] = ECMTemplate(
            template_id='smart_panel',
            name_template='Smart Electrical Panel',
            category=ECMCategory.CONTROLS,
            subcategory=ECMSubcategory.ELEC_PANEL,
            description='Smart panel with load management (Span, Lumin)',
            default_cost_per_unit=4500,  # $/panel installed
            cost_unit='each',
            default_savings_pct=0.05,  # 5% from load optimization
            applicable_building_types=[BuildingType.SINGLE_FAMILY],
            useful_life_years=20,
            source='Manufacturer Data',
            vintage=2024,
        )

        # EV charging infrastructure
        self._templates['ev_l2_residential'] = ECMTemplate(
            template_id='ev_l2_residential',
            name_template='Residential Level 2 EV Charger',
            category=ECMCategory.OTHER,
            subcategory=ECMSubcategory.ELEC_EV_CHARGING,
            description='Level 2 (240V) EV charging station',
            default_cost_per_unit=1500,  # $/charger installed
            cost_unit='each',
            default_savings_pct=0.0,
            applicable_building_types=[BuildingType.SINGLE_FAMILY],
            useful_life_years=15,
            source='NREL',
            vintage=2024,
        )
        self._templates['ev_l2_multifamily'] = ECMTemplate(
            template_id='ev_l2_multifamily',
            name_template='Multifamily Level 2 EV Charger',
            category=ECMCategory.OTHER,
            subcategory=ECMSubcategory.ELEC_EV_CHARGING,
            description='Level 2 EV charging for multifamily parking',
            default_cost_per_unit=3500,  # $/charger (includes infrastructure)
            cost_unit='each',
            default_savings_pct=0.0,
            applicable_building_types=[
                BuildingType.MULTIFAMILY_LOW,
                BuildingType.MULTIFAMILY_HIGH,
            ],
            useful_life_years=15,
            source='CEC',
            vintage=2024,
        )
        self._templates['ev_ready_conduit'] = ECMTemplate(
            template_id='ev_ready_conduit',
            name_template='EV-Ready Conduit',
            category=ECMCategory.OTHER,
            subcategory=ECMSubcategory.ELEC_EV_CHARGING,
            description='Conduit and panel capacity for future EV charging',
            default_cost_per_unit=800,  # $/parking space
            cost_unit='each',
            default_savings_pct=0.0,
            applicable_building_types=[
                BuildingType.MULTIFAMILY_LOW,
                BuildingType.MULTIFAMILY_HIGH,
                BuildingType.OFFICE_SMALL,
                BuildingType.OFFICE_LARGE,
            ],
            useful_life_years=40,
            source='CALGreen',
            vintage=2024,
        )

    # =========================================================================
    # Public API
    # =========================================================================

    def list_templates(self) -> List[str]:
        """List all available template IDs."""
        return sorted(self._templates.keys())

    def list_by_category(self, category: ECMCategory) -> List[str]:
        """List template IDs for a specific category."""
        return [
            tid for tid, t in self._templates.items()
            if t.category == category
        ]

    def list_by_subcategory(self, subcategory: ECMSubcategory) -> List[str]:
        """List template IDs for a specific subcategory."""
        return [
            tid for tid, t in self._templates.items()
            if t.subcategory == subcategory
        ]

    def list_for_building_type(self, building_type: BuildingType) -> List[str]:
        """List template IDs applicable to a building type."""
        results = []
        for tid, t in self._templates.items():
            if BuildingType.ALL in t.applicable_building_types:
                results.append(tid)
            elif building_type in t.applicable_building_types:
                results.append(tid)
            elif (building_type in [BuildingType.SINGLE_FAMILY,
                                    BuildingType.MULTIFAMILY_LOW,
                                    BuildingType.MULTIFAMILY_HIGH]
                  and BuildingType.ALL_RESIDENTIAL in t.applicable_building_types):
                results.append(tid)
            elif (building_type not in [BuildingType.SINGLE_FAMILY,
                                        BuildingType.MULTIFAMILY_LOW,
                                        BuildingType.MULTIFAMILY_HIGH]
                  and BuildingType.ALL_COMMERCIAL in t.applicable_building_types):
                results.append(tid)
        return sorted(results)

    def list_for_climate_zone(self, climate_zone: int) -> List[str]:
        """List template IDs applicable to a climate zone."""
        return [
            tid for tid, t in self._templates.items()
            if climate_zone in t.climate_zones
        ]

    def get_template(self, template_id: str) -> ECMTemplate:
        """Get a template by ID."""
        if template_id not in self._templates:
            raise KeyError(
                f"Template '{template_id}' not found. "
                f"Available: {self.list_templates()}"
            )
        return self._templates[template_id]

    def search(self, query: str) -> List[str]:
        """Search templates by name or description."""
        query_lower = query.lower()
        results = []
        for tid, t in self._templates.items():
            if (query_lower in tid.lower() or
                query_lower in t.name_template.lower() or
                query_lower in t.description.lower()):
                results.append(tid)
        return sorted(results)

    def get_category_summary(self) -> Dict[str, int]:
        """Get count of templates by category."""
        summary: Dict[str, int] = {}
        for t in self._templates.values():
            cat_name = t.category.value
            summary[cat_name] = summary.get(cat_name, 0) + 1
        return summary

    def load_from_json(self, json_path: Path) -> None:
        """
        Load custom ECM templates from JSON file.

        JSON format:
        {
            "template_id": {
                "name_template": "...",
                "category": "hvac",
                "subcategory": "heating",
                ...
            }
        }
        """
        with open(json_path, 'r') as f:
            data = json.load(f)

        for tid, tdata in data.items():
            self._templates[tid] = ECMTemplate(
                template_id=tid,
                name_template=tdata['name_template'],
                category=ECMCategory(tdata['category']),
                subcategory=ECMSubcategory(tdata['subcategory']),
                description=tdata.get('description', ''),
                default_cost_per_unit=tdata.get('default_cost_per_unit', 0),
                cost_unit=tdata.get('cost_unit', 'each'),
                default_savings_pct=tdata.get('default_savings_pct', 0),
                default_generation_per_unit=tdata.get('default_generation_per_unit', 0),
                useful_life_years=tdata.get('useful_life_years', 20),
                source=tdata.get('source', ''),
                vintage=tdata.get('vintage', 2024),
            )

    def export_to_json(self, json_path: Path) -> None:
        """Export all templates to JSON file."""
        data = {}
        for tid, t in self._templates.items():
            data[tid] = {
                'name_template': t.name_template,
                'category': t.category.value,
                'subcategory': t.subcategory.value,
                'description': t.description,
                'default_cost_per_unit': t.default_cost_per_unit,
                'cost_unit': t.cost_unit,
                'default_savings_pct': t.default_savings_pct,
                'default_generation_per_unit': t.default_generation_per_unit,
                'useful_life_years': t.useful_life_years,
                'source': t.source,
                'vintage': t.vintage,
            }
        with open(json_path, 'w') as f:
            json.dump(data, f, indent=2)


# Global library instance
_ecm_library: Optional[ECMLibrary] = None


def get_ecm_library() -> ECMLibrary:
    """Get the global ECM library instance."""
    global _ecm_library
    if _ecm_library is None:
        _ecm_library = ECMLibrary()
    return _ecm_library


# =============================================================================
# Measure Interaction Matrix (Feature 2)
# =============================================================================

class InteractionType(Enum):
    """Types of interactions between ECMs."""
    SYNERGY = "synergy"          # ECMs work better together
    CONFLICT = "conflict"        # ECMs cannot both be applied
    PREREQUISITE = "prerequisite"  # ECM A requires ECM B
    EXCLUSIVE = "exclusive"      # Only one of the set can be selected
    REDUCES = "reduces"          # ECM A reduces effectiveness of ECM B


@dataclass
class MeasureInteraction:
    """
    Defines an interaction between two or more ECMs.

    Attributes:
        ecm_ids: Template IDs of ECMs involved
        interaction_type: Type of interaction
        effect: Multiplier or description of effect
        description: Human-readable explanation
        bidirectional: Whether interaction applies both ways
    """
    ecm_ids: Tuple[str, ...]
    interaction_type: InteractionType
    effect: float = 1.0  # Multiplier for synergy/reduction
    description: str = ""
    bidirectional: bool = True


class MeasureInteractionMatrix:
    """
    Tracks interactions between ECMs for validation and optimization.

    Supports:
    - Conflict detection (invalid combinations)
    - Synergy identification (enhanced savings)
    - Prerequisite validation (dependencies)
    - Exclusive group enforcement (mutually exclusive options)

    Example:
        >>> matrix = MeasureInteractionMatrix()
        >>> # Check if combination is valid
        >>> matrix.validate_combination(['erv_residential', 'central_vent'])
        (False, ['ERV and central ventilation are mutually exclusive'])
        >>> # Get synergies for a bundle
        >>> matrix.get_synergies(['minisplit', 'envelope_upgrade'])
        [MeasureInteraction(synergy, effect=1.15)]
    """

    def __init__(self):
        self._interactions: List[MeasureInteraction] = []
        self._exclusive_groups: Dict[str, Set[str]] = {}
        self._prerequisites: Dict[str, Set[str]] = {}
        self._load_default_interactions()

    def _load_default_interactions(self) -> None:
        """Load built-in measure interactions."""

        # =====================================================================
        # Exclusive Groups (only one can be selected)
        # =====================================================================

        # Ventilation systems are mutually exclusive
        self._add_exclusive_group('ventilation', [
            'erv_residential', 'central_vent', 'hrv_residential'
        ])

        # Heating systems are mutually exclusive
        self._add_exclusive_group('heating', [
            'minisplit', 'gshp', 'ashp_ducted', 'vrf', 'gas_furnace_high_eff'
        ])

        # Water heating systems are mutually exclusive
        self._add_exclusive_group('dhw', [
            'hpwh_residential', 'hpwh_commercial', 'solar_thermal',
            'gas_tankless', 'gas_storage_high_eff'
        ])

        # Cooking equipment is mutually exclusive
        self._add_exclusive_group('cooking', [
            'induction_cooktop', 'induction_range', 'gas_range'
        ])

        # Panel upgrades are mutually exclusive
        self._add_exclusive_group('panel', [
            'panel_upgrade_200a', 'panel_upgrade_400a', 'smart_panel'
        ])

        # =====================================================================
        # Prerequisites (ECM A requires ECM B)
        # =====================================================================

        # HPWH requires electric-ready infrastructure (in new construction)
        self._add_prerequisite('hpwh_residential', 'elec_ready_water_heater')

        # Mini-split/ASHP may require panel upgrade
        self._add_prerequisite('minisplit', 'panel_upgrade_200a')
        self._add_prerequisite('ashp_ducted', 'panel_upgrade_200a')

        # EV charger requires panel capacity
        self._add_prerequisite('ev_l2_residential', 'panel_upgrade_200a')
        self._add_prerequisite('ev_l2_multifamily', 'panel_upgrade_400a')

        # Induction cooking requires electric-ready
        self._add_prerequisite('induction_range', 'elec_ready_cooking')

        # =====================================================================
        # Synergies (ECMs that work better together)
        # =====================================================================

        # Mini-split + envelope upgrade = better performance
        self._interactions.append(MeasureInteraction(
            ecm_ids=('minisplit', 'envelope_upgrade'),
            interaction_type=InteractionType.SYNERGY,
            effect=1.15,  # 15% enhanced savings
            description="Right-sized heat pump with improved envelope",
        ))

        # PV + battery = enhanced self-consumption
        self._interactions.append(MeasureInteraction(
            ecm_ids=('pv_rooftop', 'battery_storage'),
            interaction_type=InteractionType.SYNERGY,
            effect=1.20,  # 20% better TOU arbitrage
            description="Battery enables TOU optimization of PV generation",
        ))

        # ERV + mini-split = reduced HVAC sizing
        self._interactions.append(MeasureInteraction(
            ecm_ids=('erv_residential', 'minisplit'),
            interaction_type=InteractionType.SYNERGY,
            effect=1.10,
            description="ERV pre-conditions air, reducing heat pump load",
        ))

        # HPWH + PV = daytime generation matches hot water load
        self._interactions.append(MeasureInteraction(
            ecm_ids=('hpwh_residential', 'pv_rooftop'),
            interaction_type=InteractionType.SYNERGY,
            effect=1.12,
            description="HPWH can shift load to solar generation hours",
        ))

        # Smart panel + electrification = load balancing
        self._interactions.append(MeasureInteraction(
            ecm_ids=('smart_panel', 'minisplit', 'hpwh_residential', 'ev_l2_residential'),
            interaction_type=InteractionType.SYNERGY,
            effect=1.08,
            description="Smart panel prevents demand spikes from stacked loads",
        ))

        # Cool roof + HVAC upgrade in hot climates
        self._interactions.append(MeasureInteraction(
            ecm_ids=('cool_roof', 'minisplit'),
            interaction_type=InteractionType.SYNERGY,
            effect=1.18,
            description="Cool roof reduces cooling load for right-sized HP",
        ))

        # =====================================================================
        # Reductions (ECM A reduces effectiveness of ECM B)
        # =====================================================================

        # High-efficiency envelope reduces HVAC savings potential
        self._interactions.append(MeasureInteraction(
            ecm_ids=('envelope_upgrade', 'minisplit'),
            interaction_type=InteractionType.REDUCES,
            effect=0.85,  # HVAC upgrade provides 15% less incremental savings
            description="Envelope improvements reduce heating/cooling loads, "
                       "making HVAC efficiency less impactful",
            bidirectional=False,  # Envelope doesn't reduce, HVAC does
        ))

        # =====================================================================
        # Conflicts (cannot both be applied)
        # =====================================================================

        # ERV and exhaust-only ventilation conflict
        self._interactions.append(MeasureInteraction(
            ecm_ids=('erv_residential', 'exhaust_only_vent'),
            interaction_type=InteractionType.CONFLICT,
            description="ERV provides balanced ventilation; cannot combine "
                       "with exhaust-only approach",
        ))

    def _add_exclusive_group(self, group_name: str, ecm_ids: List[str]) -> None:
        """Add a mutually exclusive group of ECMs."""
        self._exclusive_groups[group_name] = set(ecm_ids)
        # Also add as explicit EXCLUSIVE interactions
        if len(ecm_ids) >= 2:
            self._interactions.append(MeasureInteraction(
                ecm_ids=tuple(ecm_ids),
                interaction_type=InteractionType.EXCLUSIVE,
                description=f"Mutually exclusive {group_name} options",
            ))

    def _add_prerequisite(self, ecm_id: str, requires: str) -> None:
        """Add a prerequisite relationship."""
        if ecm_id not in self._prerequisites:
            self._prerequisites[ecm_id] = set()
        self._prerequisites[ecm_id].add(requires)
        self._interactions.append(MeasureInteraction(
            ecm_ids=(ecm_id, requires),
            interaction_type=InteractionType.PREREQUISITE,
            description=f"{ecm_id} may require {requires}",
            bidirectional=False,
        ))

    def validate_combination(
        self,
        ecm_ids: List[str],
        strict: bool = False,
    ) -> Tuple[bool, List[str]]:
        """
        Validate that a combination of ECMs is compatible.

        Args:
            ecm_ids: List of ECM template IDs
            strict: If True, treat missing prerequisites as errors

        Returns:
            Tuple of (is_valid, list of warning/error messages)
        """
        messages = []
        is_valid = True
        ecm_set = set(ecm_ids)

        # Check exclusive groups
        for group_name, group_ecms in self._exclusive_groups.items():
            overlap = ecm_set & group_ecms
            if len(overlap) > 1:
                is_valid = False
                messages.append(
                    f"CONFLICT: Multiple {group_name} options selected: "
                    f"{sorted(overlap)}. Only one allowed."
                )

        # Check explicit conflicts
        for interaction in self._interactions:
            if interaction.interaction_type == InteractionType.CONFLICT:
                conflict_set = set(interaction.ecm_ids)
                if conflict_set <= ecm_set:
                    is_valid = False
                    messages.append(
                        f"CONFLICT: {', '.join(interaction.ecm_ids)} - "
                        f"{interaction.description}"
                    )

        # Check prerequisites
        for ecm_id in ecm_ids:
            if ecm_id in self._prerequisites:
                missing = self._prerequisites[ecm_id] - ecm_set
                for prereq in missing:
                    msg = f"PREREQUISITE: {ecm_id} may require {prereq}"
                    if strict:
                        is_valid = False
                        messages.append(f"ERROR: {msg}")
                    else:
                        messages.append(f"WARNING: {msg}")

        return is_valid, messages

    def get_synergies(self, ecm_ids: List[str]) -> List[MeasureInteraction]:
        """
        Get synergistic interactions for a set of ECMs.

        Args:
            ecm_ids: List of ECM template IDs

        Returns:
            List of applicable synergy interactions
        """
        ecm_set = set(ecm_ids)
        synergies = []

        for interaction in self._interactions:
            if interaction.interaction_type == InteractionType.SYNERGY:
                # Check if all ECMs in the interaction are present
                if set(interaction.ecm_ids) <= ecm_set:
                    synergies.append(interaction)

        return synergies

    def get_reductions(self, ecm_ids: List[str]) -> List[MeasureInteraction]:
        """
        Get reduction interactions for a set of ECMs.

        These indicate where one ECM reduces effectiveness of another.

        Args:
            ecm_ids: List of ECM template IDs

        Returns:
            List of applicable reduction interactions
        """
        ecm_set = set(ecm_ids)
        reductions = []

        for interaction in self._interactions:
            if interaction.interaction_type == InteractionType.REDUCES:
                if set(interaction.ecm_ids) <= ecm_set:
                    reductions.append(interaction)

        return reductions

    def calculate_bundle_factor(self, ecm_ids: List[str]) -> float:
        """
        Calculate combined savings factor for a bundle of ECMs.

        Applies synergy bonuses and reduction penalties.

        Args:
            ecm_ids: List of ECM template IDs

        Returns:
            Multiplier to apply to total bundle savings
        """
        factor = 1.0

        for synergy in self.get_synergies(ecm_ids):
            # Synergy effects multiply (compound)
            factor *= synergy.effect

        for reduction in self.get_reductions(ecm_ids):
            # Reduction effects are also multiplicative
            factor *= reduction.effect

        return factor

    def get_prerequisites(self, ecm_id: str) -> Set[str]:
        """Get prerequisites for an ECM."""
        return self._prerequisites.get(ecm_id, set())

    def get_exclusive_options(self, ecm_id: str) -> Optional[Set[str]]:
        """Get other ECMs in the same exclusive group."""
        for group_name, ecms in self._exclusive_groups.items():
            if ecm_id in ecms:
                return ecms - {ecm_id}
        return None

    def list_interactions(
        self,
        interaction_type: Optional[InteractionType] = None,
    ) -> List[MeasureInteraction]:
        """List all interactions, optionally filtered by type."""
        if interaction_type is None:
            return list(self._interactions)
        return [i for i in self._interactions
                if i.interaction_type == interaction_type]

    def format_interaction_summary(self, ecm_ids: List[str]) -> str:
        """Format a summary of interactions for a bundle."""
        is_valid, messages = self.validate_combination(ecm_ids)
        synergies = self.get_synergies(ecm_ids)
        reductions = self.get_reductions(ecm_ids)
        factor = self.calculate_bundle_factor(ecm_ids)

        lines = [
            "ECM Interaction Analysis",
            "=" * 40,
            f"Bundle: {', '.join(ecm_ids)}",
            f"Valid: {is_valid}",
            "",
        ]

        if messages:
            lines.append("Messages:")
            for msg in messages:
                lines.append(f"  - {msg}")
            lines.append("")

        if synergies:
            lines.append(f"Synergies ({len(synergies)}):")
            for s in synergies:
                lines.append(f"  + {s.ecm_ids}: {s.description}")
                lines.append(f"    Effect: {s.effect:.0%} enhanced savings")
            lines.append("")

        if reductions:
            lines.append(f"Reductions ({len(reductions)}):")
            for r in reductions:
                lines.append(f"  - {r.ecm_ids}: {r.description}")
                lines.append(f"    Effect: {r.effect:.0%} of base savings")
            lines.append("")

        lines.append(f"Combined Bundle Factor: {factor:.2%}")

        return "\n".join(lines)


# Global interaction matrix instance
_interaction_matrix: Optional[MeasureInteractionMatrix] = None


def get_interaction_matrix() -> MeasureInteractionMatrix:
    """Get the global measure interaction matrix."""
    global _interaction_matrix
    if _interaction_matrix is None:
        _interaction_matrix = MeasureInteractionMatrix()
    return _interaction_matrix


# =============================================================================
# Climate-Adaptive Defaults (Feature 4)
# =============================================================================

class ClimateZoneType(Enum):
    """California climate zone classifications."""
    MILD_COASTAL = "mild_coastal"      # CZ 1-5 (moderate heating, minimal cooling)
    HOT_DRY = "hot_dry"                # CZ 10-15 (high cooling, moderate heating)
    HOT_HUMID = "hot_humid"            # CZ 6-9 (cooling dominant, some humidity)
    COLD_MOUNTAIN = "cold_mountain"    # CZ 16 (heating dominant)


# Climate zone classifications (based on CEC definitions)
CLIMATE_ZONE_CLASSIFICATION: Dict[int, ClimateZoneType] = {
    1: ClimateZoneType.MILD_COASTAL,
    2: ClimateZoneType.MILD_COASTAL,
    3: ClimateZoneType.MILD_COASTAL,
    4: ClimateZoneType.MILD_COASTAL,
    5: ClimateZoneType.MILD_COASTAL,
    6: ClimateZoneType.HOT_HUMID,
    7: ClimateZoneType.HOT_HUMID,
    8: ClimateZoneType.HOT_HUMID,
    9: ClimateZoneType.HOT_HUMID,
    10: ClimateZoneType.HOT_DRY,
    11: ClimateZoneType.HOT_DRY,
    12: ClimateZoneType.HOT_DRY,
    13: ClimateZoneType.HOT_DRY,
    14: ClimateZoneType.HOT_DRY,
    15: ClimateZoneType.HOT_DRY,
    16: ClimateZoneType.COLD_MOUNTAIN,
}


@dataclass
class ClimateAdaptiveFactors:
    """
    Climate-specific adjustment factors for ECM calculations.

    All factors are multipliers (1.0 = no adjustment).
    """
    # Energy savings adjustments
    heating_savings_factor: float = 1.0
    cooling_savings_factor: float = 1.0
    pv_generation_factor: float = 1.0
    erv_effectiveness: float = 1.0

    # Sizing adjustments
    hvac_sizing_factor: float = 1.0

    # Cost adjustments
    labor_cost_factor: float = 1.0

    # Annual operating hours
    heating_hours: float = 1000
    cooling_hours: float = 500

    # Description
    zone_type: Optional[ClimateZoneType] = None
    climate_zone: Optional[int] = None


class ClimateAdaptiveDefaults:
    """
    Provides climate zone-specific adjustments for ECM parameters.

    California's 16 climate zones have different heating/cooling loads,
    solar resources, and cost-effectiveness characteristics. This class
    provides adjustment factors to adapt generic ECM templates.

    Example:
        >>> cad = ClimateAdaptiveDefaults()
        >>> factors = cad.get_factors(13)  # Hot-dry zone
        >>> print(f"PV generation: {factors.pv_generation_factor:.0%}")
        >>> # Apply to ERV savings
        >>> erv_savings = base_savings * factors.erv_effectiveness
    """

    def __init__(self):
        self._factors: Dict[int, ClimateAdaptiveFactors] = {}
        self._load_default_factors()

    def _load_default_factors(self) -> None:
        """Load climate-specific adjustment factors."""

        # CZ 1: Arcata (mild coastal, heating dominant)
        self._factors[1] = ClimateAdaptiveFactors(
            heating_savings_factor=1.15,  # More heating savings value
            cooling_savings_factor=0.50,  # Little cooling needed
            pv_generation_factor=0.85,    # Overcast/foggy
            erv_effectiveness=1.20,       # Good for heat recovery
            hvac_sizing_factor=0.85,      # Smaller AC loads
            labor_cost_factor=1.00,
            heating_hours=1800,
            cooling_hours=100,
            zone_type=ClimateZoneType.MILD_COASTAL,
            climate_zone=1,
        )

        # CZ 2: Santa Rosa (mild, some heating)
        self._factors[2] = ClimateAdaptiveFactors(
            heating_savings_factor=1.10,
            cooling_savings_factor=0.70,
            pv_generation_factor=0.95,
            erv_effectiveness=1.15,
            hvac_sizing_factor=0.90,
            labor_cost_factor=1.10,
            heating_hours=1500,
            cooling_hours=200,
            zone_type=ClimateZoneType.MILD_COASTAL,
            climate_zone=2,
        )

        # CZ 3: Oakland/San Francisco (mild coastal, minimal HVAC)
        self._factors[3] = ClimateAdaptiveFactors(
            heating_savings_factor=1.00,
            cooling_savings_factor=0.40,
            pv_generation_factor=0.90,
            erv_effectiveness=1.10,
            hvac_sizing_factor=0.80,
            labor_cost_factor=1.20,  # Bay Area premium
            heating_hours=1200,
            cooling_hours=50,
            zone_type=ClimateZoneType.MILD_COASTAL,
            climate_zone=3,
        )

        # CZ 4: San Jose/Sunnyvale (mild, more cooling than CZ3)
        self._factors[4] = ClimateAdaptiveFactors(
            heating_savings_factor=0.95,
            cooling_savings_factor=0.80,
            pv_generation_factor=1.00,
            erv_effectiveness=1.05,
            hvac_sizing_factor=0.90,
            labor_cost_factor=1.20,
            heating_hours=1100,
            cooling_hours=300,
            zone_type=ClimateZoneType.MILD_COASTAL,
            climate_zone=4,
        )

        # CZ 5: Santa Maria (coastal, very mild)
        self._factors[5] = ClimateAdaptiveFactors(
            heating_savings_factor=0.90,
            cooling_savings_factor=0.50,
            pv_generation_factor=0.95,
            erv_effectiveness=1.00,
            hvac_sizing_factor=0.85,
            labor_cost_factor=1.05,
            heating_hours=1300,
            cooling_hours=100,
            zone_type=ClimateZoneType.MILD_COASTAL,
            climate_zone=5,
        )

        # CZ 6: Los Angeles Coast (mild, low HVAC loads)
        self._factors[6] = ClimateAdaptiveFactors(
            heating_savings_factor=0.80,
            cooling_savings_factor=0.70,
            pv_generation_factor=1.00,
            erv_effectiveness=0.90,
            hvac_sizing_factor=0.85,
            labor_cost_factor=1.15,
            heating_hours=800,
            cooling_hours=200,
            zone_type=ClimateZoneType.HOT_HUMID,
            climate_zone=6,
        )

        # CZ 7: San Diego (very mild, low HVAC loads)
        self._factors[7] = ClimateAdaptiveFactors(
            heating_savings_factor=0.70,
            cooling_savings_factor=0.60,
            pv_generation_factor=1.05,
            erv_effectiveness=0.85,
            hvac_sizing_factor=0.80,
            labor_cost_factor=1.10,
            heating_hours=600,
            cooling_hours=200,
            zone_type=ClimateZoneType.HOT_HUMID,
            climate_zone=7,
        )

        # CZ 8: El Toro/Fullerton (inland LA, more cooling)
        self._factors[8] = ClimateAdaptiveFactors(
            heating_savings_factor=0.85,
            cooling_savings_factor=0.95,
            pv_generation_factor=1.05,
            erv_effectiveness=0.90,
            hvac_sizing_factor=1.00,
            labor_cost_factor=1.15,
            heating_hours=700,
            cooling_hours=600,
            zone_type=ClimateZoneType.HOT_HUMID,
            climate_zone=8,
        )

        # CZ 9: Pasadena/Burbank (inland valleys, hot summers)
        self._factors[9] = ClimateAdaptiveFactors(
            heating_savings_factor=0.90,
            cooling_savings_factor=1.10,
            pv_generation_factor=1.05,
            erv_effectiveness=0.95,
            hvac_sizing_factor=1.05,
            labor_cost_factor=1.15,
            heating_hours=800,
            cooling_hours=800,
            zone_type=ClimateZoneType.HOT_HUMID,
            climate_zone=9,
        )

        # CZ 10: Riverside/Ontario (hot desert transition)
        self._factors[10] = ClimateAdaptiveFactors(
            heating_savings_factor=0.85,
            cooling_savings_factor=1.20,
            pv_generation_factor=1.10,
            erv_effectiveness=0.85,  # ERV less effective in dry heat
            hvac_sizing_factor=1.10,
            labor_cost_factor=1.00,
            heating_hours=700,
            cooling_hours=1000,
            zone_type=ClimateZoneType.HOT_DRY,
            climate_zone=10,
        )

        # CZ 11: Red Bluff (Central Valley, extreme temps)
        self._factors[11] = ClimateAdaptiveFactors(
            heating_savings_factor=1.05,
            cooling_savings_factor=1.25,
            pv_generation_factor=1.10,
            erv_effectiveness=0.95,
            hvac_sizing_factor=1.15,
            labor_cost_factor=0.95,
            heating_hours=1200,
            cooling_hours=1100,
            zone_type=ClimateZoneType.HOT_DRY,
            climate_zone=11,
        )

        # CZ 12: Sacramento (hot summers, cold winters)
        self._factors[12] = ClimateAdaptiveFactors(
            heating_savings_factor=1.00,
            cooling_savings_factor=1.15,
            pv_generation_factor=1.10,
            erv_effectiveness=1.00,
            hvac_sizing_factor=1.10,
            labor_cost_factor=1.05,
            heating_hours=1100,
            cooling_hours=900,
            zone_type=ClimateZoneType.HOT_DRY,
            climate_zone=12,
        )

        # CZ 13: Fresno (Central Valley, very hot summers)
        self._factors[13] = ClimateAdaptiveFactors(
            heating_savings_factor=0.95,
            cooling_savings_factor=1.30,  # High cooling savings value
            pv_generation_factor=1.15,    # Excellent solar
            erv_effectiveness=0.80,       # Less effective in dry heat
            hvac_sizing_factor=1.20,      # Larger AC loads
            labor_cost_factor=0.90,
            heating_hours=900,
            cooling_hours=1200,
            zone_type=ClimateZoneType.HOT_DRY,
            climate_zone=13,
        )

        # CZ 14: Palmdale/Lancaster (high desert)
        self._factors[14] = ClimateAdaptiveFactors(
            heating_savings_factor=1.10,
            cooling_savings_factor=1.25,
            pv_generation_factor=1.20,  # Excellent solar
            erv_effectiveness=0.90,
            hvac_sizing_factor=1.15,
            labor_cost_factor=0.95,
            heating_hours=1300,
            cooling_hours=1100,
            zone_type=ClimateZoneType.HOT_DRY,
            climate_zone=14,
        )

        # CZ 15: El Centro/Imperial Valley (extreme desert heat)
        self._factors[15] = ClimateAdaptiveFactors(
            heating_savings_factor=0.70,
            cooling_savings_factor=1.40,  # Highest cooling value
            pv_generation_factor=1.25,    # Excellent solar
            erv_effectiveness=0.70,       # ERV less useful
            hvac_sizing_factor=1.30,      # Large AC loads
            labor_cost_factor=0.90,
            heating_hours=500,
            cooling_hours=1500,
            zone_type=ClimateZoneType.HOT_DRY,
            climate_zone=15,
        )

        # CZ 16: Blue Canyon/Mountain (cold, heating dominant)
        self._factors[16] = ClimateAdaptiveFactors(
            heating_savings_factor=1.30,  # Highest heating value
            cooling_savings_factor=0.60,
            pv_generation_factor=1.05,
            erv_effectiveness=1.30,       # ERV very effective
            hvac_sizing_factor=1.20,      # Large heating loads
            labor_cost_factor=1.10,
            heating_hours=2500,
            cooling_hours=300,
            zone_type=ClimateZoneType.COLD_MOUNTAIN,
            climate_zone=16,
        )

    def get_factors(self, climate_zone: int) -> ClimateAdaptiveFactors:
        """
        Get adjustment factors for a specific climate zone.

        Args:
            climate_zone: California climate zone (1-16)

        Returns:
            ClimateAdaptiveFactors with zone-specific multipliers
        """
        if climate_zone not in self._factors:
            raise ValueError(f"Invalid climate zone: {climate_zone}. Valid: 1-16")
        return self._factors[climate_zone]

    def get_zone_type(self, climate_zone: int) -> ClimateZoneType:
        """Get the climate type classification for a zone."""
        return CLIMATE_ZONE_CLASSIFICATION.get(climate_zone, ClimateZoneType.MILD_COASTAL)

    def adjust_hvac_savings(
        self,
        climate_zone: int,
        heating_savings: float,
        cooling_savings: float,
    ) -> Tuple[float, float]:
        """
        Adjust HVAC savings for climate zone.

        Args:
            climate_zone: California climate zone
            heating_savings: Base heating savings ($)
            cooling_savings: Base cooling savings ($)

        Returns:
            Tuple of (adjusted_heating_savings, adjusted_cooling_savings)
        """
        factors = self.get_factors(climate_zone)
        return (
            heating_savings * factors.heating_savings_factor,
            cooling_savings * factors.cooling_savings_factor,
        )

    def adjust_pv_generation(
        self,
        climate_zone: int,
        base_generation_kwh: float,
    ) -> float:
        """
        Adjust PV generation for climate zone.

        Args:
            climate_zone: California climate zone
            base_generation_kwh: Base annual generation (kWh)

        Returns:
            Adjusted annual generation (kWh)
        """
        factors = self.get_factors(climate_zone)
        return base_generation_kwh * factors.pv_generation_factor

    def adjust_erv_effectiveness(
        self,
        climate_zone: int,
        base_savings: float,
    ) -> float:
        """
        Adjust ERV savings for climate zone.

        ERV effectiveness varies significantly by climate:
        - Very effective in cold/heating-dominant zones
        - Less effective in hot-dry climates (dry air = less latent recovery)

        Args:
            climate_zone: California climate zone
            base_savings: Base ERV savings ($)

        Returns:
            Adjusted ERV savings ($)
        """
        factors = self.get_factors(climate_zone)
        return base_savings * factors.erv_effectiveness

    def adjust_capex(
        self,
        climate_zone: int,
        base_cost: float,
    ) -> float:
        """
        Adjust capital cost for regional labor rates.

        Args:
            climate_zone: California climate zone
            base_cost: Base capital cost ($)

        Returns:
            Adjusted capital cost ($)
        """
        factors = self.get_factors(climate_zone)
        return base_cost * factors.labor_cost_factor

    def get_recommended_ecms(self, climate_zone: int) -> List[str]:
        """
        Get recommended ECMs for a climate zone.

        Returns template IDs of ECMs that are most cost-effective
        in this climate zone.

        Args:
            climate_zone: California climate zone

        Returns:
            List of recommended ECM template IDs
        """
        zone_type = self.get_zone_type(climate_zone)

        # Base recommendations for all zones
        recommended = ['pv_rooftop', 'led_lighting']

        if zone_type == ClimateZoneType.COLD_MOUNTAIN:
            recommended.extend([
                'erv_residential',       # Heat recovery very valuable
                'envelope_upgrade',      # Insulation critical
                'high_perf_windows',     # Reduce heat loss
                'ashp_ducted',          # Heat pump for heating
            ])
        elif zone_type == ClimateZoneType.HOT_DRY:
            recommended.extend([
                'cool_roof',            # Reduce cooling load
                'minisplit',            # Efficient cooling
                'evap_cooling',         # Works well in dry climates
                'exterior_shade',       # Reduce solar gain
            ])
        elif zone_type == ClimateZoneType.HOT_HUMID:
            recommended.extend([
                'minisplit',            # High SEER
                'cool_roof',            # Some benefit
                'hpwh_residential',     # Dehumidifies space
            ])
        else:  # MILD_COASTAL
            recommended.extend([
                'hpwh_residential',     # Easy electrification win
                'minisplit',            # Minimal HVAC needs
                'envelope_upgrade',     # Modest improvements
            ])

        return recommended

    def format_zone_summary(self, climate_zone: int) -> str:
        """Format a summary of climate zone characteristics."""
        factors = self.get_factors(climate_zone)
        zone_type = self.get_zone_type(climate_zone)

        lines = [
            f"Climate Zone {climate_zone} Summary",
            "=" * 40,
            f"Classification: {zone_type.value.replace('_', ' ').title()}",
            "",
            "Adjustment Factors:",
            f"  Heating savings:  {factors.heating_savings_factor:+.0%}"
            if factors.heating_savings_factor != 1.0 else "  Heating savings:  baseline",
            f"  Cooling savings:  {factors.cooling_savings_factor:+.0%}"
            if factors.cooling_savings_factor != 1.0 else "  Cooling savings:  baseline",
            f"  PV generation:    {factors.pv_generation_factor:+.0%}"
            if factors.pv_generation_factor != 1.0 else "  PV generation:    baseline",
            f"  ERV effectiveness:{factors.erv_effectiveness:+.0%}"
            if factors.erv_effectiveness != 1.0 else "  ERV effectiveness:baseline",
            f"  Labor costs:      {factors.labor_cost_factor:+.0%}"
            if factors.labor_cost_factor != 1.0 else "  Labor costs:      baseline",
            "",
            "Annual Operating Hours:",
            f"  Heating: {factors.heating_hours:.0f} hrs",
            f"  Cooling: {factors.cooling_hours:.0f} hrs",
            "",
            "Recommended ECMs:",
        ]

        for ecm_id in self.get_recommended_ecms(climate_zone):
            lines.append(f"  - {ecm_id}")

        return "\n".join(lines)


# Global climate adaptive defaults instance
_climate_defaults: Optional[ClimateAdaptiveDefaults] = None


def get_climate_defaults() -> ClimateAdaptiveDefaults:
    """Get the global climate adaptive defaults instance."""
    global _climate_defaults
    if _climate_defaults is None:
        _climate_defaults = ClimateAdaptiveDefaults()
    return _climate_defaults


# =============================================================================
# Parametric ECM Support (Feature 5)
# =============================================================================

@dataclass
class ParametricRange:
    """
    Defines a range for parametric ECM generation.

    Attributes:
        min_value: Minimum parameter value
        max_value: Maximum parameter value
        step: Step size for discrete options (None for continuous)
        unit: Unit label for display
    """
    min_value: float
    max_value: float
    step: Optional[float] = None
    unit: str = ""

    def get_values(self, n_points: int = 10) -> List[float]:
        """Get a list of values across the range."""
        if self.step is not None:
            # Discrete steps
            values = []
            current = self.min_value
            while current <= self.max_value:
                values.append(current)
                current += self.step
            return values
        else:
            # Continuous, generate n_points
            if n_points <= 1:
                return [self.min_value]
            step = (self.max_value - self.min_value) / (n_points - 1)
            return [self.min_value + i * step for i in range(n_points)]


@dataclass
class ParametricECMDefinition:
    """
    Defines a parametric ECM with variable sizing/parameters.

    Example:
        >>> # Define a PV system that can range from 50-500 kW
        >>> pv_param = ParametricECMDefinition(
        ...     name_template="PV System ({size:.0f} kW)",
        ...     category=ECMCategory.GENERATION,
        ...     parameters={'size': ParametricRange(50, 500, step=50, unit='kW')},
        ...     capex_formula=lambda p: p['size'] * 1000 * 2.50,
        ...     generation_formula=lambda p: p['size'] * 1500,
        ... )
    """
    name_template: str
    category: ECMCategory
    parameters: Dict[str, ParametricRange]
    capex_formula: Any  # Callable[[Dict], float]
    subcategory: Optional[ECMSubcategory] = None
    generation_formula: Optional[Any] = None  # Callable[[Dict], float]
    kwh_delta_formula: Optional[Any] = None   # Callable[[Dict], float]
    therm_delta_formula: Optional[Any] = None  # Callable[[Dict], float]
    useful_life_years: int = 20
    description: str = ""

    def generate_ecm(self, param_values: Dict[str, float]) -> ECM:
        """Generate an ECM instance with specific parameter values."""
        capex = self.capex_formula(param_values)

        generation = 0.0
        if self.generation_formula:
            generation = self.generation_formula(param_values)

        kwh_delta = 0.0
        if self.kwh_delta_formula:
            kwh_delta = self.kwh_delta_formula(param_values)

        therm_delta = 0.0
        if self.therm_delta_formula:
            therm_delta = self.therm_delta_formula(param_values)

        # Format name with parameter values
        name = self.name_template.format(**param_values)

        return ECM(
            name=name,
            category=self.category,
            subcategory=self.subcategory,
            capex=capex,
            annual_kwh_generation=generation,
            annual_kwh_delta=kwh_delta,
            annual_therm_delta=therm_delta,
            useful_life_years=self.useful_life_years,
            description=self.description,
        )

    def generate_all_variants(self, n_points: int = 10) -> List[ECM]:
        """Generate all ECM variants across parameter ranges."""
        # For single parameter, simple iteration
        if len(self.parameters) == 1:
            param_name = list(self.parameters.keys())[0]
            param_range = self.parameters[param_name]
            variants = []
            for value in param_range.get_values(n_points):
                variants.append(self.generate_ecm({param_name: value}))
            return variants

        # For multiple parameters, generate all combinations
        from itertools import product
        param_names = list(self.parameters.keys())
        param_value_lists = [
            self.parameters[name].get_values(n_points)
            for name in param_names
        ]

        variants = []
        for values in product(*param_value_lists):
            param_dict = dict(zip(param_names, values))
            variants.append(self.generate_ecm(param_dict))
        return variants


@dataclass
class ParametricOptimizationResult:
    """Result of parametric optimization."""
    optimal_ecm: ECM
    optimal_params: Dict[str, float]
    optimal_npv: float
    all_variants: List[Tuple[Dict[str, float], ECM, float]]  # (params, ecm, npv)
    objective: str


class ParametricECMOptimizer:
    """
    Optimizes parametric ECM sizing for best financial outcome.

    Supports:
    - NPV maximization
    - Payback minimization
    - IRR maximization
    - Custom objective functions

    Example:
        >>> optimizer = ParametricECMOptimizer()
        >>> pv_def = create_parametric_pv(50, 500, step=50)
        >>> result = optimizer.optimize(
        ...     pv_def,
        ...     baseline_scenario,
        ...     annual_load_kwh=500000,
        ...     tariff=get_tariff_by_name('SCE-TOU-GS-3'),
        ... )
        >>> print(f"Optimal PV: {result.optimal_params['capacity_kw']} kW")
        >>> print(f"NPV: ${result.optimal_npv:,.0f}")
    """

    def __init__(self):
        pass

    def optimize_npv(
        self,
        parametric_def: ParametricECMDefinition,
        baseline_annual_kwh: float,
        baseline_annual_cost: float,
        electricity_rate: float = 0.20,
        discount_rate: float = 0.05,
        analysis_years: int = 30,
        n_points: int = 20,
    ) -> ParametricOptimizationResult:
        """
        Find optimal sizing for maximum NPV.

        Args:
            parametric_def: Parametric ECM definition
            baseline_annual_kwh: Annual electricity consumption
            baseline_annual_cost: Annual electricity cost
            electricity_rate: Average $/kWh for savings
            discount_rate: Discount rate for NPV
            analysis_years: Years for NPV calculation
            n_points: Number of points to evaluate

        Returns:
            ParametricOptimizationResult with optimal sizing
        """
        variants = parametric_def.generate_all_variants(n_points)
        results = []

        for ecm in variants:
            # Calculate annual savings
            if ecm.annual_kwh_generation > 0:
                # Generation-based (PV)
                annual_savings = min(
                    ecm.annual_kwh_generation * electricity_rate,
                    baseline_annual_cost
                )
            elif ecm.get_kwh_impact() < 0:
                # Efficiency-based
                annual_savings = abs(ecm.get_kwh_impact()) * electricity_rate
            else:
                annual_savings = 0

            # Simple NPV calculation
            npv = self._calculate_simple_npv(
                -ecm.net_capex,
                annual_savings,
                discount_rate,
                analysis_years,
            )

            # Extract params from ECM name (reverse lookup)
            params = self._extract_params_from_ecm(ecm, parametric_def)
            results.append((params, ecm, npv))

        # Find optimal
        results.sort(key=lambda x: x[2], reverse=True)  # Sort by NPV descending
        optimal = results[0]

        return ParametricOptimizationResult(
            optimal_ecm=optimal[1],
            optimal_params=optimal[0],
            optimal_npv=optimal[2],
            all_variants=results,
            objective="maximize_npv",
        )

    def optimize_payback(
        self,
        parametric_def: ParametricECMDefinition,
        baseline_annual_kwh: float,
        electricity_rate: float = 0.20,
        max_payback_years: float = 15.0,
        n_points: int = 20,
    ) -> ParametricOptimizationResult:
        """
        Find optimal sizing for minimum payback period.

        Only considers variants with payback <= max_payback_years.
        """
        variants = parametric_def.generate_all_variants(n_points)
        results = []

        for ecm in variants:
            # Calculate annual savings
            if ecm.annual_kwh_generation > 0:
                annual_savings = ecm.annual_kwh_generation * electricity_rate
            elif ecm.get_kwh_impact() < 0:
                annual_savings = abs(ecm.get_kwh_impact()) * electricity_rate
            else:
                continue  # Skip if no savings

            # Calculate payback
            if annual_savings > 0:
                payback = ecm.net_capex / annual_savings
            else:
                payback = float('inf')

            if payback <= max_payback_years:
                params = self._extract_params_from_ecm(ecm, parametric_def)
                # Use negative payback as "value" for sorting (min payback = best)
                results.append((params, ecm, -payback))

        if not results:
            raise ValueError(
                f"No variants meet payback requirement of {max_payback_years} years"
            )

        results.sort(key=lambda x: x[2], reverse=True)  # Min payback
        optimal = results[0]

        return ParametricOptimizationResult(
            optimal_ecm=optimal[1],
            optimal_params=optimal[0],
            optimal_npv=-optimal[2],  # Return actual payback
            all_variants=[(p, e, -v) for p, e, v in results],
            objective="minimize_payback",
        )

    def optimize_load_coverage(
        self,
        parametric_def: ParametricECMDefinition,
        target_coverage: float,
        annual_load_kwh: float,
        n_points: int = 20,
    ) -> ParametricOptimizationResult:
        """
        Find sizing to achieve target load coverage.

        Args:
            parametric_def: Parametric ECM definition (PV)
            target_coverage: Target fraction of load to cover (e.g., 1.0 = 100%)
            annual_load_kwh: Annual electricity consumption
            n_points: Number of points to evaluate

        Returns:
            Result with sizing closest to target coverage
        """
        target_generation = annual_load_kwh * target_coverage
        variants = parametric_def.generate_all_variants(n_points)
        results = []

        for ecm in variants:
            if ecm.annual_kwh_generation > 0:
                coverage = ecm.annual_kwh_generation / annual_load_kwh
                deviation = abs(coverage - target_coverage)
                params = self._extract_params_from_ecm(ecm, parametric_def)
                results.append((params, ecm, -deviation))  # Negative for sorting

        results.sort(key=lambda x: x[2], reverse=True)  # Min deviation
        optimal = results[0]

        return ParametricOptimizationResult(
            optimal_ecm=optimal[1],
            optimal_params=optimal[0],
            optimal_npv=-optimal[2],  # Return deviation
            all_variants=[(p, e, -v) for p, e, v in results],
            objective=f"target_coverage_{target_coverage:.0%}",
        )

    def _calculate_simple_npv(
        self,
        initial: float,
        annual: float,
        rate: float,
        years: int,
    ) -> float:
        """Calculate simple NPV with uniform annual cash flows."""
        npv = initial
        for year in range(1, years + 1):
            npv += annual / ((1 + rate) ** year)
        return npv

    def _extract_params_from_ecm(
        self,
        ecm: ECM,
        parametric_def: ParametricECMDefinition,
    ) -> Dict[str, float]:
        """Extract parameter values from ECM (reverse lookup from name/capex)."""
        # For single-parameter definitions, derive from capex
        if len(parametric_def.parameters) == 1:
            param_name = list(parametric_def.parameters.keys())[0]
            param_range = parametric_def.parameters[param_name]

            # Try each value to find match
            for value in param_range.get_values(100):
                test_ecm = parametric_def.generate_ecm({param_name: value})
                if abs(test_ecm.capex - ecm.capex) < 0.01:
                    return {param_name: value}

        # Fallback: return empty dict
        return {}


# =============================================================================
# Parametric ECM Factory Functions
# =============================================================================

def create_parametric_pv(
    min_kw: float = 10,
    max_kw: float = 500,
    step_kw: Optional[float] = None,
    cost_per_watt: float = 2.50,
    kwh_per_kw: float = 1500,
    itc_pct: float = 0.30,
) -> ParametricECMDefinition:
    """
    Create a parametric PV system definition.

    Args:
        min_kw: Minimum system size (kW DC)
        max_kw: Maximum system size (kW DC)
        step_kw: Step size for discrete options (None for continuous)
        cost_per_watt: Installed cost ($/W DC)
        kwh_per_kw: Annual generation per kW (kWh/kW/year)
        itc_pct: Federal ITC percentage

    Returns:
        ParametricECMDefinition for PV system
    """
    return ParametricECMDefinition(
        name_template="PV System ({capacity_kw:.0f} kW)",
        category=ECMCategory.GENERATION,
        subcategory=ECMSubcategory.PHOTOVOLTAIC,
        parameters={
            'capacity_kw': ParametricRange(min_kw, max_kw, step_kw, 'kW')
        },
        capex_formula=lambda p: p['capacity_kw'] * 1000 * cost_per_watt * (1 - itc_pct),
        generation_formula=lambda p: p['capacity_kw'] * kwh_per_kw,
        useful_life_years=25,
        description=f"Parametric PV: {min_kw}-{max_kw} kW @ ${cost_per_watt}/W",
    )


def create_parametric_battery(
    min_kwh: float = 10,
    max_kwh: float = 500,
    step_kwh: Optional[float] = None,
    cost_per_kwh: float = 400,
    power_ratio: float = 0.25,  # kW per kWh
) -> ParametricECMDefinition:
    """
    Create a parametric battery storage definition.

    Args:
        min_kwh: Minimum storage capacity (kWh)
        max_kwh: Maximum storage capacity (kWh)
        step_kwh: Step size for discrete options
        cost_per_kwh: Installed cost ($/kWh)
        power_ratio: Power-to-energy ratio (kW/kWh)

    Returns:
        ParametricECMDefinition for battery storage
    """
    return ParametricECMDefinition(
        name_template="Battery Storage ({capacity_kwh:.0f} kWh)",
        category=ECMCategory.STORAGE,
        subcategory=ECMSubcategory.BATTERY,
        parameters={
            'capacity_kwh': ParametricRange(min_kwh, max_kwh, step_kwh, 'kWh')
        },
        capex_formula=lambda p: p['capacity_kwh'] * cost_per_kwh,
        useful_life_years=15,
        description=f"Parametric battery: {min_kwh}-{max_kwh} kWh @ ${cost_per_kwh}/kWh",
    )


def create_parametric_hvac(
    min_tons: float = 1,
    max_tons: float = 20,
    step_tons: Optional[float] = None,
    cost_per_ton: float = 3500,
    seer: float = 20,
    hspf: float = 10,
    cooling_load_factor: float = 3000,  # kWh/ton/year baseline
    heating_load_factor: float = 2000,  # kWh/ton/year baseline
) -> ParametricECMDefinition:
    """
    Create a parametric HVAC system definition.

    Args:
        min_tons: Minimum capacity (tons)
        max_tons: Maximum capacity (tons)
        step_tons: Step size for discrete options
        cost_per_ton: Installed cost ($/ton)
        seer: Seasonal Energy Efficiency Ratio
        hspf: Heating Seasonal Performance Factor
        cooling_load_factor: Annual cooling load per ton
        heating_load_factor: Annual heating load per ton

    Returns:
        ParametricECMDefinition for HVAC system
    """
    # Baseline efficiencies (code minimum)
    baseline_seer = 14
    baseline_hspf = 8

    def calc_kwh_delta(p: Dict[str, float]) -> float:
        tons = p['capacity_tons']
        # Cooling savings
        baseline_cooling = tons * cooling_load_factor
        proposed_cooling = baseline_cooling * (baseline_seer / seer)
        cooling_savings = baseline_cooling - proposed_cooling

        # Heating savings
        baseline_heating = tons * heating_load_factor
        proposed_heating = baseline_heating * (baseline_hspf / hspf)
        heating_savings = baseline_heating - proposed_heating

        return -(cooling_savings + heating_savings)  # Negative = reduction

    return ParametricECMDefinition(
        name_template="HVAC System ({capacity_tons:.1f} tons)",
        category=ECMCategory.HVAC,
        subcategory=ECMSubcategory.HVAC_WHOLE_SYSTEM,
        parameters={
            'capacity_tons': ParametricRange(min_tons, max_tons, step_tons, 'tons')
        },
        capex_formula=lambda p: p['capacity_tons'] * cost_per_ton,
        kwh_delta_formula=calc_kwh_delta,
        useful_life_years=15,
        description=f"Parametric HVAC: {min_tons}-{max_tons} tons, SEER {seer}",
    )


def format_optimization_result(result: ParametricOptimizationResult) -> str:
    """Format optimization result as text."""
    lines = [
        "Parametric ECM Optimization Result",
        "=" * 50,
        f"Objective: {result.objective}",
        "",
        "Optimal Configuration:",
        f"  {result.optimal_ecm.name}",
        f"  Capex: ${result.optimal_ecm.capex:,.0f}",
    ]

    if result.optimal_ecm.annual_kwh_generation > 0:
        lines.append(f"  Generation: {result.optimal_ecm.annual_kwh_generation:,.0f} kWh/yr")

    if result.objective == "maximize_npv":
        lines.append(f"  NPV: ${result.optimal_npv:,.0f}")
    elif result.objective == "minimize_payback":
        lines.append(f"  Payback: {result.optimal_npv:.1f} years")
    elif "target_coverage" in result.objective:
        lines.append(f"  Coverage deviation: {result.optimal_npv:.2%}")

    lines.extend([
        "",
        "Parameters:",
    ])
    for name, value in result.optimal_params.items():
        lines.append(f"  {name}: {value:.1f}")

    if len(result.all_variants) > 1:
        lines.extend([
            "",
            f"Variants evaluated: {len(result.all_variants)}",
        ])

    return "\n".join(lines)


def analyze_ecm_marginal_value(
    ecm: ECM,
    baseline_scenario: Any,  # TouLccaScenario
    proposed_with_ecm: Any,  # TouLccaScenario
    proposed_without_ecm: Any,  # TouLccaScenario
) -> ECMAnalysisResult:
    """
    Analyze the marginal value of a single ECM.

    Compares scenarios with and without the ECM to isolate its value.

    Args:
        ecm: The ECM to analyze
        baseline_scenario: Original baseline scenario
        proposed_with_ecm: Proposed scenario including this ECM
        proposed_without_ecm: Proposed scenario excluding this ECM

    Returns:
        ECMAnalysisResult with financial metrics
    """
    from .calculators import run_tou_lcca

    # Run LCCA comparing without ECM to with ECM
    results = run_tou_lcca(proposed_without_ecm, proposed_with_ecm)

    # Calculate cost effectiveness
    analysis_years = results.analysis_years
    total_kwh_saved = abs(ecm.get_kwh_impact()) * analysis_years if ecm.get_kwh_impact() < 0 else 0
    total_therms_saved = abs(ecm.get_therm_impact()) * analysis_years if ecm.get_therm_impact() < 0 else 0

    cost_per_kwh = ecm.net_capex / total_kwh_saved if total_kwh_saved > 0 else None
    cost_per_therm = ecm.net_capex / total_therms_saved if total_therms_saved > 0 else None

    return ECMAnalysisResult(
        ecm_name=ecm.name,
        ecm_category=ecm.category,
        capex=ecm.capex,
        net_capex=ecm.net_capex,
        total_incentives=ecm.total_incentives,
        annual_kwh_impact=ecm.get_kwh_impact(),
        annual_therm_impact=ecm.get_therm_impact(),
        annual_generation_kwh=ecm.annual_kwh_generation,
        annual_cost_savings=results.annual_savings,
        npv=results.npv,
        irr=results.irr,
        simple_payback_years=results.simple_payback_years,
        sir=results.sir,
        cost_per_kwh_saved=cost_per_kwh,
        cost_per_therm_saved=cost_per_therm,
    )


def format_ecm_analysis(result: ECMAnalysisResult) -> str:
    """
    Format ECM analysis result as text.

    Args:
        result: ECMAnalysisResult to format

    Returns:
        Formatted text report
    """
    lines = [
        "=" * 60,
        f"ECM ANALYSIS: {result.ecm_name}",
        f"Category: {result.ecm_category.value}",
        "=" * 60,
        "",
        "Investment",
        "-" * 40,
        f"  Capital Cost:       ${result.capex:>12,.0f}",
        f"  Incentives:         ${result.total_incentives:>12,.0f}",
        f"  Net Cost:           ${result.net_capex:>12,.0f}",
        "",
        "Energy Impact",
        "-" * 40,
    ]

    if result.annual_generation_kwh > 0:
        lines.append(f"  Annual Generation:  {result.annual_generation_kwh:>12,.0f} kWh")
    if result.annual_kwh_impact != 0:
        lines.append(f"  kWh Change:         {result.annual_kwh_impact:>12,.0f} kWh")
    if result.annual_therm_impact != 0:
        lines.append(f"  Therm Change:       {result.annual_therm_impact:>12,.0f} therms")

    lines.extend([
        "",
        "Financial Results",
        "-" * 40,
        f"  Annual Savings:     ${result.annual_cost_savings:>12,.0f}",
        f"  NPV:                ${result.npv:>12,.0f}",
    ])

    if result.irr is not None:
        lines.append(f"  IRR:                {result.irr*100:>12.1f}%")
    else:
        lines.append("  IRR:                         N/A")

    if result.simple_payback_years is not None:
        lines.append(f"  Simple Payback:     {result.simple_payback_years:>12.1f} years")
    else:
        lines.append("  Simple Payback:              N/A")

    if result.sir is not None:
        lines.append(f"  SIR:                {result.sir:>12.2f}")
    else:
        lines.append("  SIR:                         N/A")

    if result.cost_per_kwh_saved is not None:
        lines.extend([
            "",
            "Cost Effectiveness",
            "-" * 40,
            f"  $/kWh saved:        ${result.cost_per_kwh_saved:>12.4f}",
        ])

    lines.append("=" * 60)

    return "\n".join(lines)


# Pre-defined ECM templates for common measures
def create_pv_ecm(
    capacity_kw: float,
    cost_per_watt: float = 2.50,
    annual_kwh_per_kw: float = 1500,
    itc_pct: float = 0.0,
    name: Optional[str] = None,
) -> ECM:
    """
    Create a PV system ECM.

    Args:
        capacity_kw: System capacity in kW DC
        cost_per_watt: Installed cost per watt
        annual_kwh_per_kw: Annual generation per kW (default 1500 for CA)
        itc_pct: Federal Investment Tax Credit percentage (e.g., 0.30)
        name: ECM name (default: "{capacity} kW PV")

    Returns:
        Configured PV ECM
    """
    capex = capacity_kw * 1000 * cost_per_watt
    generation = capacity_kw * annual_kwh_per_kw

    incentives = []
    if itc_pct > 0:
        incentives.append({
            'name': f'Federal ITC ({itc_pct*100:.0f}%)',
            'amount': capex * itc_pct,
            'pays_in_year': 0,
        })

    return ECM(
        name=name or f"{capacity_kw:.0f} kW PV",
        category=ECMCategory.GENERATION,
        subcategory=ECMSubcategory.PHOTOVOLTAIC,
        capex=capex,
        annual_kwh_generation=generation,
        incentives=incentives,
        useful_life_years=25,
        description=f"Rooftop PV system, {capacity_kw} kW DC",
        source="NREL ATB",
    )


def create_electrification_ecm(
    name: str,
    capex: float,
    annual_kwh_increase: float,
    annual_therm_reduction: float,
    description: str = "",
) -> ECM:
    """
    Create an electrification ECM (replacing gas with electric).

    Args:
        name: ECM name
        capex: Capital cost
        annual_kwh_increase: Additional electric consumption
        annual_therm_reduction: Gas consumption eliminated (positive value)
        description: Description

    Returns:
        Configured electrification ECM
    """
    return ECM(
        name=name,
        category=ECMCategory.HVAC,
        subcategory=ECMSubcategory.HVAC_HEATING,
        capex=capex,
        annual_kwh_delta=annual_kwh_increase,
        annual_therm_delta=-abs(annual_therm_reduction),  # Ensure negative
        useful_life_years=15,
        description=description or "Fuel switching from gas to electric",
    )


def create_efficiency_ecm(
    name: str,
    category: ECMCategory,
    capex: float,
    kwh_reduction_pct: float = 0.0,
    therm_reduction_pct: float = 0.0,
    useful_life_years: int = 15,
) -> ECM:
    """
    Create an efficiency improvement ECM.

    Args:
        name: ECM name
        category: ECM category
        capex: Capital cost
        kwh_reduction_pct: Percentage reduction in kWh (e.g., 0.20 for 20%)
        therm_reduction_pct: Percentage reduction in therms
        useful_life_years: Expected useful life

    Returns:
        Configured efficiency ECM
    """
    return ECM(
        name=name,
        category=category,
        capex=capex,
        annual_kwh_pct=-abs(kwh_reduction_pct),  # Ensure negative (reduction)
        annual_therm_pct=-abs(therm_reduction_pct),
        useful_life_years=useful_life_years,
    )


# =============================================================================
# Residential HVAC ECM Templates
# =============================================================================

def create_erv_ecm(
    unit_count: int,
    cfm_per_unit: float = 35,
    cost_per_unit: float = 1200,
    fan_kwh_per_unit: float = 80,
    heating_savings_pct: float = 0.25,
    cooling_savings_pct: float = 0.05,
    name: Optional[str] = None,
) -> ECM:
    """
    Create an ERV (Energy Recovery Ventilator) ECM for residential units.

    ERVs provide balanced ventilation with heat/energy recovery. They add
    fan energy but can reduce heating/cooling loads through heat exchange.

    Based on Ventura & 7th analysis:
    - ERV fan energy: ~67-135 kWh/unit/year (varies by CFM)
    - Heating savings: ~60-80 kWh/unit/year in mild climates
    - Net impact depends on climate zone

    Args:
        unit_count: Number of dwelling units
        cfm_per_unit: Ventilation CFM per unit (default 35)
        cost_per_unit: Installed cost per ERV unit
        fan_kwh_per_unit: Annual fan energy per unit (varies by CFM)
        heating_savings_pct: Reduction in heating from heat recovery
        cooling_savings_pct: Reduction in cooling from energy recovery
        name: ECM name

    Returns:
        Configured ERV ECM

    Example:
        >>> erv = create_erv_ecm(54, cfm_per_unit=35, cost_per_unit=1500)
        >>> print(f"Total cost: ${erv.capex:,.0f}")
    """
    capex = unit_count * cost_per_unit
    fan_energy = unit_count * fan_kwh_per_unit

    return ECM(
        name=name or f"ERV System ({unit_count} units @ {cfm_per_unit} CFM)",
        category=ECMCategory.HVAC,
        subcategory=ECMSubcategory.HVAC_ENERGY_RECOVERY,
        capex=capex,
        annual_kwh_delta=fan_energy,  # Fan adds energy
        # Note: heating/cooling savings captured via annual_kwh_pct on HVAC load
        useful_life_years=15,
        description=f"Energy Recovery Ventilators for {unit_count} dwelling units",
        notes=f"Fan energy: {fan_energy:,.0f} kWh/yr. "
              f"Expect {heating_savings_pct*100:.0f}% heating, "
              f"{cooling_savings_pct*100:.0f}% cooling savings from recovery.",
        source="CEC CASE 2025",
    )


def create_central_vent_ecm(
    unit_count: int,
    total_cfm: float,
    cost_per_unit: float = 500,
    central_fan_kw: float = 0.5,
    hours_per_day: float = 24,
    name: Optional[str] = None,
) -> ECM:
    """
    Create a central ventilation ECM (like Maestro systems).

    Central supply ventilation provides fresh air through a common
    air handler. Lower per-unit cost but no heat recovery.

    Args:
        unit_count: Number of dwelling units served
        total_cfm: Total ventilation CFM
        cost_per_unit: Per-unit allocation of system cost
        central_fan_kw: Central fan power (kW)
        hours_per_day: Daily operating hours
        name: ECM name

    Returns:
        Configured central ventilation ECM
    """
    capex = unit_count * cost_per_unit
    annual_fan_kwh = central_fan_kw * hours_per_day * 365

    return ECM(
        name=name or f"Central Ventilation ({total_cfm:.0f} CFM)",
        category=ECMCategory.HVAC,
        subcategory=ECMSubcategory.HVAC_WHOLE_SYSTEM,
        capex=capex,
        annual_kwh_delta=annual_fan_kwh,
        useful_life_years=20,
        description=f"Central supply ventilation for {unit_count} units",
        source="CEC CASE 2025",
    )


def create_minisplit_ecm(
    unit_count: int,
    tons_per_unit: float = 1.5,
    seer: float = 20,
    hspf: float = 10,
    cost_per_ton: float = 3500,
    baseline_seer: float = 15,
    baseline_hspf: float = 8.5,
    annual_cooling_hours: float = 1000,
    annual_heating_hours: float = 500,
    name: Optional[str] = None,
) -> ECM:
    """
    Create a ductless mini-split heat pump ECM.

    Mini-splits offer high efficiency heating and cooling without ductwork.
    Common for multifamily retrofits and high-performance new construction.

    Args:
        unit_count: Number of dwelling units
        tons_per_unit: Cooling capacity per unit (tons)
        seer: Seasonal Energy Efficiency Ratio (cooling)
        hspf: Heating Seasonal Performance Factor
        cost_per_ton: Installed cost per ton
        baseline_seer: Comparison baseline SEER
        baseline_hspf: Comparison baseline HSPF
        annual_cooling_hours: Equivalent full-load cooling hours
        annual_heating_hours: Equivalent full-load heating hours
        name: ECM name

    Returns:
        Configured mini-split ECM
    """
    total_tons = unit_count * tons_per_unit
    capex = total_tons * cost_per_ton

    # Estimate baseline consumption (kWh)
    btuh_per_ton = 12000
    baseline_cooling_kwh = (total_tons * btuh_per_ton * annual_cooling_hours) / (baseline_seer * 1000)
    baseline_heating_kwh = (total_tons * btuh_per_ton * annual_heating_hours) / (baseline_hspf * 1000)

    # Calculate proposed consumption
    proposed_cooling_kwh = (total_tons * btuh_per_ton * annual_cooling_hours) / (seer * 1000)
    proposed_heating_kwh = (total_tons * btuh_per_ton * annual_heating_hours) / (hspf * 1000)

    # Savings = baseline - proposed (positive = savings)
    cooling_savings = baseline_cooling_kwh - proposed_cooling_kwh
    heating_savings = baseline_heating_kwh - proposed_heating_kwh
    total_savings = cooling_savings + heating_savings

    return ECM(
        name=name or f"Mini-Split Heat Pumps ({seer} SEER/{hspf} HSPF)",
        category=ECMCategory.HVAC,
        subcategory=ECMSubcategory.HVAC_HEATING,
        capex=capex,
        annual_kwh_delta=-total_savings,  # Negative = reduction
        useful_life_years=15,
        description=f"{unit_count} ductless mini-split systems, {tons_per_unit} tons each",
        notes=f"Cooling: {cooling_savings:,.0f} kWh savings, "
              f"Heating: {heating_savings:,.0f} kWh savings",
        source="CEC CASE 2025",
    )


def create_hpwh_ecm(
    unit_count: int,
    gallons_per_unit: float = 50,
    uef: float = 3.5,
    baseline_uef: float = 0.92,  # Standard gas water heater
    annual_hot_water_therms: float = 200,  # Per unit
    cost_per_unit: float = 2500,
    name: Optional[str] = None,
) -> ECM:
    """
    Create a Heat Pump Water Heater ECM.

    HPWHs use heat pump technology for highly efficient water heating.
    Common electrification measure replacing gas water heaters.

    Args:
        unit_count: Number of dwelling units
        gallons_per_unit: Tank capacity per unit
        uef: Uniform Energy Factor of HPWH
        baseline_uef: UEF of baseline water heater
        annual_hot_water_therms: Annual gas consumption per unit (baseline)
        cost_per_unit: Installed cost per HPWH
        name: ECM name

    Returns:
        Configured HPWH ECM
    """
    capex = unit_count * cost_per_unit

    # Convert baseline therms to equivalent electric kWh
    # 1 therm = 29.3 kWh (thermal equivalent)
    baseline_energy_kwh = annual_hot_water_therms * 29.3 / baseline_uef
    hpwh_energy_kwh = baseline_energy_kwh / uef * baseline_uef

    annual_kwh_per_unit = hpwh_energy_kwh
    total_annual_kwh = unit_count * annual_kwh_per_unit
    total_therms_eliminated = unit_count * annual_hot_water_therms

    return ECM(
        name=name or f"Heat Pump Water Heaters (UEF {uef})",
        category=ECMCategory.DHW,
        subcategory=ECMSubcategory.DHW_HEAT_PUMP,
        capex=capex,
        annual_kwh_delta=total_annual_kwh,  # Electric increase
        annual_therm_delta=-total_therms_eliminated,  # Gas elimination
        useful_life_years=12,
        description=f"{unit_count} HPWHs replacing gas water heaters",
        source="CEC CASE 2025",
    )


# =============================================================================
# CUAC Integration - Generate ECMs from scenario comparison
# =============================================================================

def create_ecm_from_cuac_comparison(
    baseline_name: str,
    proposed_name: str,
    baseline_kwh: float,
    proposed_kwh: float,
    capex: float,
    category: ECMCategory = ECMCategory.HVAC,
    useful_life_years: int = 15,
) -> ECM:
    """
    Create an ECM from a CUAC scenario comparison.

    Use this to convert CUAC analysis results into ECM format for
    financial analysis and comparison.

    Args:
        baseline_name: Name of baseline scenario
        proposed_name: Name of proposed scenario
        baseline_kwh: Annual kWh for baseline scenario
        proposed_kwh: Annual kWh for proposed scenario
        capex: Capital cost difference (proposed - baseline)
        category: ECM category
        useful_life_years: Expected useful life

    Returns:
        ECM representing the change from baseline to proposed

    Example:
        >>> # From CUAC comparison: Maestro baseline vs Ephoca proposed
        >>> ecm = create_ecm_from_cuac_comparison(
        ...     "Maestro", "Ephoca ERV",
        ...     baseline_kwh=272512, proposed_kwh=280094,
        ...     capex=25000,  # Additional cost for ERVs
        ... )
    """
    kwh_delta = proposed_kwh - baseline_kwh  # Positive = increase

    return ECM(
        name=f"{proposed_name} vs {baseline_name}",
        category=category,
        capex=capex,
        annual_kwh_delta=kwh_delta,
        useful_life_years=useful_life_years,
        description=f"Comparison: {proposed_name} relative to {baseline_name}",
        notes=f"Baseline: {baseline_kwh:,.0f} kWh/yr, "
              f"Proposed: {proposed_kwh:,.0f} kWh/yr, "
              f"Delta: {kwh_delta:+,.0f} kWh/yr",
    )
