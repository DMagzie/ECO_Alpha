"""
Simulation output parsers for LCCA.

Parsers for CBECC simulation output files:
- HourlyResults CSV: Combined hourly energy data
- CSE CSV: Detailed end-use hourly data
- HVACSecondary CSV: Air systems, zone systems, coils, fans
- HVACPrimary CSV: DHW, boilers, chillers, pumps
- Envelope CSV: Walls, windows, roofs, materials
- AnalysisResults XML: Detailed envelope data (roof, window performance)
- CSE Input (.cse): DHW equipment specifications from simulation input
"""

from .hourly_results import parse_hourly_results, HourlyResultsParser
from .cse_hourly import (
    parse_cse_csv,
    parse_cse_detailed,
    CseHourlyParser,
    CseDetailedParser,
    CSEDetailedOutput,
    CSEDetailedAnnual,
    CSEDetailedHourly,
)
from .cbecc_csv_base import CebeccCsvParser, CebeccSection
from .analysis_results_xml import (
    parse_analysis_results,
    AnalysisResultsParser,
    AnalysisResultsOutput,
    RoofElement,
    WallElement,
    WindowElement,
    WindowType,
    ConstructionLayer,
    DHWHeater,
    DHWSystem,
    ConstructionTypeBreakdown,
    EnergyEndUse,
    EnergyComparison,
)
from .hvac_secondary import (
    parse_hvac_secondary,
    HVACSecondaryParser,
    HVACSecondaryOutput,
    AirSystem,
    ZoneSystem,
    CoolingCoil,
    HeatingCoil,
    Fan,
    TerminalUnit,
)
from .hvac_caps import (
    parse_hvac_caps,
    HVACCapsParser,
    HVACCapsOutput,
    HVACCapacity,
)
from .hvac_primary import (
    parse_hvac_primary,
    HVACPrimaryParser,
    HVACPrimaryOutput,
    FluidSystem,
    WaterHeater,
    Boiler,
    Chiller,
    CoolingTower,
    Pump,
)
from .envelope import (
    parse_envelope,
    parse_envelope_with_xml,
    supplement_envelope_with_xml,
    EnvelopeParser,
    EnvelopeOutput,
    BuildingAreas,
    ExteriorWall,
    Window,
    ExteriorRoof,
    UndergroundFloor,
    ConstructionAssembly,
    ConstructionMaterial,
)
from .cse_input import (
    parse_cse_input,
    CSEInputParser,
    CSEInputOutput,
    CSEDHWHeater,
    CSEDHWTank,
    CSEDHWLoop,
    CSEDHWSystem,
)
from .nrccprf import (
    parse_nrccprf,
    NRCCPRFParser,
    NRCCPRFOutput,
    NRCCPRFProjectInfo,
    NRCCPRFComplianceResult,
    NRCCPRFEndUseBreakdown,
)

__all__ = [
    # Hourly data parsers
    "parse_hourly_results",
    "HourlyResultsParser",
    "parse_cse_csv",
    "parse_cse_detailed",
    "CseHourlyParser",
    "CseDetailedParser",
    "CSEDetailedOutput",
    "CSEDetailedAnnual",
    "CSEDetailedHourly",
    # Base parser
    "CebeccCsvParser",
    "CebeccSection",
    # XML Analysis Results
    "parse_analysis_results",
    "AnalysisResultsParser",
    "AnalysisResultsOutput",
    "RoofElement",
    "WallElement",
    "WindowElement",
    "WindowType",
    "ConstructionLayer",
    "DHWHeater",
    "DHWSystem",
    "ConstructionTypeBreakdown",
    "EnergyEndUse",
    "EnergyComparison",
    # HVAC Secondary
    "parse_hvac_secondary",
    "HVACSecondaryParser",
    "HVACSecondaryOutput",
    "AirSystem",
    "ZoneSystem",
    "CoolingCoil",
    "HeatingCoil",
    "Fan",
    "TerminalUnit",
    # HVAC Capacities
    "parse_hvac_caps",
    "HVACCapsParser",
    "HVACCapsOutput",
    "HVACCapacity",
    # HVAC Primary
    "parse_hvac_primary",
    "HVACPrimaryParser",
    "HVACPrimaryOutput",
    "FluidSystem",
    "WaterHeater",
    "Boiler",
    "Chiller",
    "CoolingTower",
    "Pump",
    # Envelope
    "parse_envelope",
    "parse_envelope_with_xml",
    "supplement_envelope_with_xml",
    "EnvelopeParser",
    "EnvelopeOutput",
    "BuildingAreas",
    "ExteriorWall",
    "Window",
    "ExteriorRoof",
    "UndergroundFloor",
    "ConstructionAssembly",
    "ConstructionMaterial",
    # CSE Input (DHW specs)
    "parse_cse_input",
    "CSEInputParser",
    "CSEInputOutput",
    "CSEDHWHeater",
    "CSEDHWTank",
    "CSEDHWLoop",
    "CSEDHWSystem",
    # NRCCPRF (Project Summary)
    "parse_nrccprf",
    "NRCCPRFParser",
    "NRCCPRFOutput",
    "NRCCPRFProjectInfo",
    "NRCCPRFComplianceResult",
    "NRCCPRFEndUseBreakdown",
]
