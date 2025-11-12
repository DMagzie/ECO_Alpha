"""
Parser modules for importing CIBD22X files

Each parser is responsible for extracting one type of element from the XML
and converting it to the internal representation format.

LOGGING:
All parsers log warnings for skipped elements and suspicious data.
Configure logging level to control verbosity:
- WARNING: Shows skipped elements and data issues
- INFO: Shows parsing progress
- DEBUG: Shows detailed parsing operations
"""

import logging

# Configure module-level logger for all parsers
logger = logging.getLogger('eco_tools.parsers')

from .base_parser import BaseParser
from .zone_parser import ZoneParser
from .zonegroup_parser import ZoneGroupParser
from .surface_parser import SurfaceParser
from .opening_parser import OpeningParser
from .windowtype_parser import WindowTypeParser
from .construction_parser import ConstructionParser
from .material_parser import MaterialParser
from .schedule_parser import ScheduleParser
from .fan_parser import FanParser
from .iaqfan_parser import IAQFanParser
from .luminaire_parser import LuminaireParser
from .lightingsystem_parser import LightingSystemParser
from .heatpump_parser import HeatPumpParser
from .distributionsystem_parser import DistributionSystemParser
from .controlsystem_parser import ControlSystemParser
from .dutype_parser import DUTypeParser
from .hvac_parser import HVACSystemParser
from .dhw_parser import DHWSystemParser
from .waterheater_parser import WaterHeaterParser
from .recirculationloop_parser import RecirculationLoopParser
from .pvarray_parser import PVArrayParser
from .battery_parser import BatterySystemParser

__all__ = [
    'BaseParser',
    'ZoneParser',
    'ZoneGroupParser',
    'SurfaceParser',
    'OpeningParser',
    'WindowTypeParser',
    'ConstructionParser',
    'MaterialParser',
    'ScheduleParser',
    'FanParser',
    'IAQFanParser',
    'LuminaireParser',
    'LightingSystemParser',
    'HeatPumpParser',
    'DistributionSystemParser',
    'ControlSystemParser',
    'DUTypeParser',
    'HVACSystemParser',
    'DHWSystemParser',
    'WaterHeaterParser',
    'RecirculationLoopParser',
    'PVArrayParser',
    'BatterySystemParser',
]
