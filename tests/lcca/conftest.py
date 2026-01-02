"""
Pytest fixtures for LCCA module tests.

Shared fixtures for:
- Sample CBECC file content
- Temporary file creation
- Calculator instances
- Intake form data
"""

import pytest
from pathlib import Path


# ============================================
# Sample CBECC Content
# ============================================

SAMPLE_CIBD_MINIMAL = '''Proj   "Minimal Project"
   BldgEngyModelVersion = 11
   ..

Bldg   "Building 1"
   TotStoryCnt = 3
   ..

ResOtherZn "Lobby"
   SpcFunc = "Lobby (Main Entry)"
   Area = 1000
   ..

END_OF_FILE
'''

SAMPLE_CIBD_MULTIFAMILY = '''Proj   "MF Apartments"
   BldgEngyModelVersion = 11
   ..

DwellUnit "Unit_101"
   DwellUnitTypeRef = "2BR_Unit"
   ..

DwellUnit "Unit_102"
   DwellUnitTypeRef = "1BR_Unit"
   ..

ResZn "Living_101"
   ..

ResZn "Living_102"
   ..

ResOtherZn "Lobby_L01"
   SpcFunc = "Lobby (Main Entry)"
   Area = 1500
   ..

ResOtherZn "Corridor_L01"
   SpcFunc = "Corridor"
   Area = 800
   ..

ResOtherZn "Parking_L01"
   SpcFunc = "Parking Garage Area (Parking Zone and Ramps)"
   Area = 25000
   ..

END_OF_FILE
'''

SAMPLE_CIBD_COMMERCIAL = '''Proj   "Office Building"
   BldgEngyModelVersion = 11
   ..

ThrmlZn "Office_Floor_1"
   ..

Spc "Office_Open_L01"
   SpcFunc = "Office - Open Plan"
   Area = 5000
   ..

Spc "Lobby_L01"
   SpcFunc = "Lobby (Main Entry)"
   Area = 1200
   ..

END_OF_FILE
'''


# ============================================
# File Fixtures
# ============================================

@pytest.fixture
def sample_cibd_minimal(tmp_path):
    """Create a minimal CBECC file."""
    cibd_file = tmp_path / "minimal.cibd22"
    cibd_file.write_text(SAMPLE_CIBD_MINIMAL)
    return cibd_file


@pytest.fixture
def sample_cibd_multifamily(tmp_path):
    """Create a multifamily CBECC file."""
    cibd_file = tmp_path / "multifamily.cibd22"
    cibd_file.write_text(SAMPLE_CIBD_MULTIFAMILY)
    return cibd_file


@pytest.fixture
def sample_cibd_commercial(tmp_path):
    """Create a commercial CBECC file."""
    cibd_file = tmp_path / "commercial.cibd22"
    cibd_file.write_text(SAMPLE_CIBD_COMMERCIAL)
    return cibd_file


# ============================================
# Intake Data Fixtures
# ============================================

@pytest.fixture
def sample_intake_dict():
    """Return sample intake dictionary."""
    return {
        "project": {
            "name": "Test Apartments",
            "building_type": "multifamily",
            "climate_zone": 9,
            "dwelling_units": 100,
            "floor_area_sf": 120000,
        },
        "elevators": {
            "count": 3,
            "type": "traction_geared",
            "floors_served": 6,
            "zone_assignment": "Lobby_L01",
        },
        "escalators": {
            "count": 0,
        },
        "parking_garage": {
            "total_area_sf": 30000,
            "parking_spaces": 150,
            "levels": 1,
            "exhaust": {
                "system_type": "variable_speed",
                "cfm_per_sf": 0.75,
                "fan_power_w_cfm": 0.30,
                "co_control": True,
                "zone_assignment": "Parking_L01",
            },
        },
        "ev_charging": {
            "calgreen_2025": True,
            "dwelling_units": 100,
            "common_parking_spaces": 20,
            "alms_enabled": True,
        },
        "pools": [
            {
                "name": "Main Pool",
                "surface_area_sf": 600,
                "heated": True,
                "heater_type": "heat_pump",
                "variable_speed_pump": True,
            }
        ],
        "spas": [
            {
                "name": "Rooftop Spa",
                "volume_gallons": 400,
                "heater_type": "electric",
            }
        ],
    }


@pytest.fixture
def sample_intake_yaml_content():
    """Return sample YAML intake content."""
    return """
project:
  name: Sample Building
  building_type: multifamily
  climate_zone: 12
  dwelling_units: 80

elevators:
  count: 2
  type: hydraulic
  floors_served: 4

parking_garage:
  total_area_sf: 20000
  parking_spaces: 100
  exhaust:
    system_type: constant_volume
    cfm_per_sf: 0.75

ev_charging:
  calgreen_2025: true
  dwelling_units: 80
  alms_enabled: true
"""


@pytest.fixture
def sample_intake_yaml(tmp_path, sample_intake_yaml_content):
    """Create a sample YAML intake file."""
    yaml_file = tmp_path / "intake.yaml"
    yaml_file.write_text(sample_intake_yaml_content)
    return yaml_file


# ============================================
# Calculator Fixtures
# ============================================

@pytest.fixture
def ev_calculator():
    """Create EV charger calculator instance."""
    from eco_tools.lcca.site_loads.calculators.miscellaneous import EVChargerCalculator
    return EVChargerCalculator()


@pytest.fixture
def it_calculator():
    """Create IT/Telecom calculator instance."""
    from eco_tools.lcca.site_loads.calculators.miscellaneous import ITTelecomCalculator
    return ITTelecomCalculator()


@pytest.fixture
def water_pump_calculator():
    """Create water pump calculator instance."""
    from eco_tools.lcca.site_loads.calculators.miscellaneous import WaterPumpCalculator
    return WaterPumpCalculator()


@pytest.fixture
def trash_compactor_calculator():
    """Create trash compactor calculator instance."""
    from eco_tools.lcca.site_loads.calculators.miscellaneous import TrashCompactorCalculator
    return TrashCompactorCalculator()


# ============================================
# Template & Detector Fixtures
# ============================================

@pytest.fixture
def cbecc_template(sample_cibd_multifamily):
    """Create CbeccTemplate instance from sample file."""
    from eco_tools.lcca.cbecc_template.template import CbeccTemplate
    return CbeccTemplate(sample_cibd_multifamily)


@pytest.fixture
def cbecc_detector():
    """Create CbeccModeledLoadDetector instance."""
    from eco_tools.lcca.site_loads.detectors.cbecc_detector import CbeccModeledLoadDetector
    return CbeccModeledLoadDetector()
