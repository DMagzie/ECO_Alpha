"""
Exporter modules for serializing InternalRepresentation to CIBD22X XML

Each exporter is responsible for converting one type of element from the
internal representation format back to CIBD22X XML format.

EXPORT ARCHITECTURE:
Mirrors the parser architecture but in reverse direction:
  InternalRepresentation → CIBD22X XML

LOGGING:
All exporters log warnings for skipped elements and conversion issues.
Configure logging level to control verbosity:
- WARNING: Shows skipped elements and conversion issues
- INFO: Shows export progress
- DEBUG: Shows detailed export operations

UNIT CONVERSIONS:
Exporters reverse the parser unit conversions (SI → Imperial):
- Area: m² → ft² (÷ 0.092903)
- Volume: m³ → ft³ (× 35.3147)
- R-value: m²·K/W → ft²·°F·h/Btu (× 5.678263)
- U-factor: W/(m²·K) → Btu/(h·ft²·°F) (× 0.176110)
- Length: m → ft (÷ 0.3048)

ANNOTATION USAGE:
Exporters rely on annotations stored during import:
- 'xml_tag': Original XML tag name (Mat vs ResMat)
- 'original_*': Original IP unit values for round-trip fidelity
- Format-specific properties not in universal model
"""

import logging

# Configure module-level logger for all exporters
logger = logging.getLogger('eco_tools.exporters')

from .base_exporter import BaseExporter
from .material_exporter import MaterialExporter
from .construction_exporter import ConstructionExporter
from .windowtype_exporter import WindowTypeExporter
from .opening_exporter import OpeningExporter
from .surface_exporter import SurfaceExporter
from .zone_exporter import ZoneExporter
from .schedule_exporter import ScheduleExporter
from .hvac_exporter import HVACExporter
from .dhw_exporter import DHWExporter
from .pv_exporter import PVExporter

__all__ = [
    'BaseExporter',
    'MaterialExporter',
    'ConstructionExporter',
    'WindowTypeExporter',
    'OpeningExporter',
    'SurfaceExporter',
    'ZoneExporter',
    'ScheduleExporter',
    'HVACExporter',
    'DHWExporter',
    'PVExporter',
]
