"""
CBECC Template Module.

Tools for modifying CBECC models with site load data.

This module provides:
- CbeccTemplate: Inject data into CBECC models
- IntakeLoader: Load site load intake YAML files
- SiteLoadIntake: Structured intake data for calculators and templates

Part of the CBECC modification tools library.

Example - Direct API:
    >>> from eco_tools.lcca.cbecc_template import CbeccTemplate
    >>> template = CbeccTemplate("base_model.cibd22")
    >>> template.set_elevator_count("Lobby_L01", 4, power_kw=15.0)
    >>> template.set_parking_exhaust("Parking_L01", cfm=50000)
    >>> template.write("updated_model.cibd25")

Example - From Intake YAML:
    >>> from eco_tools.lcca.cbecc_template import CbeccTemplate, IntakeLoader
    >>> intake = IntakeLoader.load("project_intake.yaml")
    >>> template = CbeccTemplate("base_model.cibd22")
    >>> template.apply_intake(intake)
    >>> template.write("updated_model.cibd25")
"""

from .intake_loader import (
    IntakeLoader,
    SiteLoadIntake,
    AnalysisScope,
    ProjectIntake,
    ElevatorIntake,
    EscalatorIntake,
    ParkingGarageIntake,
    ParkingExhaustIntake,
    EVChargingIntake,
    PoolIntake,
    SpaIntake,
)

from .template import (
    CbeccTemplate,
    InjectionResult,
)

__all__ = [
    # Template
    'CbeccTemplate',
    'InjectionResult',
    # Loader
    'IntakeLoader',
    # Data classes
    'SiteLoadIntake',
    'AnalysisScope',
    'ProjectIntake',
    'ElevatorIntake',
    'EscalatorIntake',
    'ParkingGarageIntake',
    'ParkingExhaustIntake',
    'EVChargingIntake',
    'PoolIntake',
    'SpaIntake',
]
