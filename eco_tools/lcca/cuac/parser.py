"""
CUAC Parsers
============

Parsers for CBECC CUAC output files:
- AnalysisResults.xml: CUAC configuration and dwelling unit types
- PVBattery.csv: Per-zone PV and battery allocations
- er.json: Utility rate structure

Usage:
    from eco_tools.lcca.cuac import (
        parse_cuac_config,
        parse_pv_battery_csv,
        parse_utility_rate,
    )

    cuac = parse_cuac_config('/path/to/AnalysisResults.xml')
    allocations = parse_pv_battery_csv('/path/to/PVBattery.csv')
    rate = parse_utility_rate('/path/to/er.json')
"""

import csv
import json
import logging
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import List, Optional, Dict, Any

from .models import (
    CuacConfig,
    DwellUnitAllocation,
    DwellUnitType,
    UtilityRate,
    RateSeason,
    TouPeriod,
    EnergyCostComponent,
    Tier,
)

logger = logging.getLogger('eco_tools.lcca.cuac')


def _local_tag(tag: str) -> str:
    """Strip namespace from XML tag."""
    if '}' in tag:
        return tag.split('}')[1]
    return tag


def _get_text(elem: ET.Element, tag: str) -> Optional[str]:
    """Get text content of a child element."""
    if elem is None:
        return None
    for child in elem.iter():
        if _local_tag(child.tag) == tag and child.text:
            return child.text.strip()
    return None


def _get_indexed_values(elem: ET.Element, tag: str) -> Dict[int, float]:
    """
    Get indexed values from elements like <PctIndivUnitPVByBedrms index="1">2.51</...>

    Args:
        elem: Parent element
        tag: Tag name to search for

    Returns:
        Dict mapping index to value
    """
    result = {}
    for child in elem.iter():
        if _local_tag(child.tag) == tag:
            index_str = child.get('index')
            if index_str is not None and child.text:
                try:
                    index = int(index_str)
                    value = float(child.text.strip())
                    result[index] = value
                except (ValueError, TypeError):
                    pass
    return result


def parse_cuac_config(xml_path: str) -> Optional[CuacConfig]:
    """
    Parse CUAC configuration from AnalysisResults.xml.

    Args:
        xml_path: Path to AnalysisResults.xml file

    Returns:
        CuacConfig object or None if CUAC section not found
    """
    try:
        tree = ET.parse(xml_path)
        root = tree.getroot()
    except Exception as e:
        logger.error(f"Failed to parse XML file {xml_path}: {e}")
        return None

    # Find CUAC element
    cuac_elem = None
    for elem in root.iter():
        if _local_tag(elem.tag) == 'CUAC':
            cuac_elem = elem
            break

    if cuac_elem is None:
        logger.warning(f"No CUAC section found in {xml_path}")
        return None

    # Parse CUAC configuration
    config = CuacConfig(
        name=_get_text(cuac_elem, 'Name') or 'CalUtilityAllowanceCalc',
        report_option=_get_text(cuac_elem, 'RptOption') or 'Draft',
        project_id=_get_text(cuac_elem, 'ProjectID'),
        locality=_get_text(cuac_elem, 'Locality'),
        unit_type=_get_text(cuac_elem, 'UnitType') or 'Affordable Housing',
        # Electric
        elec_utility=_get_text(cuac_elem, 'ElecUtility'),
        elec_territory=_get_text(cuac_elem, 'G2ElecTerritory'),
        elec_tariff=_get_text(cuac_elem, 'G2ElecTariff'),
        elec_tariff_adj=_get_text(cuac_elem, 'ElecTariffAdj'),
        # Gas
        gas_utility=_get_text(cuac_elem, 'GasUtility'),
        # Water/Trash
        water_rate_type=_get_text(cuac_elem, 'WaterRateType') or 'Not Paid by Tenant',
        water_monthly_cost=float(_get_text(cuac_elem, 'WaterMonthlyCost') or 0),
        water_volume_cost=float(_get_text(cuac_elem, 'WaterVolumeCost') or 0),
        trash_rate_type=_get_text(cuac_elem, 'TrashRateType') or 'Not Paid by Tenant',
        trash_monthly_cost=float(_get_text(cuac_elem, 'TrashMonthlyCost') or 0),
        # PV
        pv_billing_option=_get_text(cuac_elem, 'PVBillingOption') or 'PV Offsets Monthly Use',
        pct_indiv_unit_pv_by_bedrms=_get_indexed_values(cuac_elem, 'PctIndivUnitPVByBedrms'),
        # Battery
        pct_indiv_unit_batt_by_bedrms=_get_indexed_values(cuac_elem, 'PctIndivUnitBattByBedrms'),
    )

    # Parse PV system size
    pv_size_str = _get_text(cuac_elem, 'AffordablePVDCSysSize')
    if pv_size_str:
        try:
            config.affordable_pv_dc_sys_size = float(pv_size_str)
        except ValueError:
            pass

    # Parse battery capacity
    batt_cap_str = _get_text(cuac_elem, 'AffordableBattMaxCap')
    if batt_cap_str:
        try:
            config.affordable_batt_max_cap = float(batt_cap_str)
        except ValueError:
            pass

    logger.info(f"Parsed CUAC config: utility={config.elec_utility}, "
                f"PV={config.affordable_pv_dc_sys_size}kWdc, "
                f"Batt={config.affordable_batt_max_cap}kWh")

    return config


def parse_dwelling_unit_types(xml_path: str) -> List[DwellUnitType]:
    """
    Parse DwellUnitType elements from AnalysisResults.xml.

    Args:
        xml_path: Path to AnalysisResults.xml file

    Returns:
        List of DwellUnitType objects
    """
    try:
        tree = ET.parse(xml_path)
        root = tree.getroot()
    except Exception as e:
        logger.error(f"Failed to parse XML file {xml_path}: {e}")
        return []

    unit_types = []

    for elem in root.iter():
        if _local_tag(elem.tag) == 'DwellUnitType':
            name = _get_text(elem, 'Name')
            if not name:
                continue

            num_bedrooms_str = _get_text(elem, 'NumBedrooms')
            cond_floor_area_str = _get_text(elem, 'CondFlrArea')

            try:
                num_bedrooms = int(num_bedrooms_str) if num_bedrooms_str else 0
                cond_floor_area = float(cond_floor_area_str) if cond_floor_area_str else 0.0
            except ValueError:
                logger.warning(f"Invalid values for DwellUnitType '{name}'")
                continue

            unit_type = DwellUnitType(
                name=name,
                num_bedrooms=num_bedrooms,
                cond_floor_area=cond_floor_area,
                dryer_fuel=_get_text(elem, 'DryerFuel'),
                cook_fuel=_get_text(elem, 'CookFuel'),
                hvac_sys_type=_get_text(elem, 'HVACSysType'),
                hvac_heat_pump_ref=_get_text(elem, 'HVACHtPumpRef'),
                dhw_sys_ref=_get_text(elem, 'DHWSysRef'),
                iaq_option=_get_text(elem, 'IAQOption'),
            )
            unit_types.append(unit_type)

    logger.info(f"Parsed {len(unit_types)} dwelling unit types")
    return unit_types


def parse_pv_battery_csv(csv_path: str) -> List[DwellUnitAllocation]:
    """
    Parse PVBattery.csv for per-zone PV and battery allocations.

    The CSV format includes:
    - Zone name, conditioning type, space function
    - Floor area and multiplier
    - Prescriptive PV (kWdc) and Battery (kWh, kW)

    Args:
        csv_path: Path to PVBattery.csv file

    Returns:
        List of DwellUnitAllocation objects
    """
    allocations = []

    try:
        with open(csv_path, 'r', newline='', encoding='utf-8-sig') as f:
            # Skip header rows (first ~8 lines are metadata)
            lines = f.readlines()
    except Exception as e:
        logger.error(f"Failed to read CSV file {csv_path}: {e}")
        return []

    # Find the data start line (after "Name,Conditioning Type,...")
    data_start = 0
    for i, line in enumerate(lines):
        if line.startswith('"S-') or (line.startswith('S-') and ',' in line):
            data_start = i
            break

    if data_start == 0:
        # Try alternative: look for header row
        for i, line in enumerate(lines):
            if 'Name' in line and 'Conditioning Type' in line:
                data_start = i + 1
                break

    # Parse data rows
    for line in lines[data_start:]:
        line = line.strip()
        if not line or line.startswith(',') or 'Sums:' in line or 'Bldg Cond Area:' in line:
            continue

        # Parse CSV line with proper quoting handling
        try:
            reader = csv.reader([line])
            row = next(reader)
        except:
            continue

        if len(row) < 5:
            continue

        # Extract values (column positions based on observed CSV format)
        zone_name = row[0].strip('"') if row[0] else ''
        if not zone_name or zone_name == 'Name':
            continue

        conditioning_type = row[1].strip('"') if len(row) > 1 else ''
        space_function = row[2].strip('"') if len(row) > 2 else ''
        pv_batt_bldg_type = row[3].strip('"') if len(row) > 3 else ''

        try:
            floor_area = float(row[4]) if len(row) > 4 and row[4] else 0.0
            multiplier = int(float(row[5])) if len(row) > 5 and row[5] else 1

            # PV, Battery columns are at the end
            # Format: ...,# Res Dwellings, MultArea, , PV, Batt Energy, Batt Power
            num_dwellings = 1
            pv_kwdc = 0.0
            batt_kwh = 0.0
            batt_kw = 0.0

            # Find numeric columns from the end
            for i in range(len(row) - 1, -1, -1):
                val = row[i].strip() if row[i] else ''
                if val and val.replace('.', '').replace('-', '').isdigit():
                    # This is a numeric value
                    pass

            # Try to find PV/Batt values in expected positions
            if len(row) >= 22:
                try:
                    num_dwellings = int(float(row[18])) if row[18] else 1
                    pv_kwdc = float(row[20]) if row[20] else 0.0
                    batt_kwh = float(row[21]) if row[21] else 0.0
                    batt_kw = float(row[22]) if len(row) > 22 and row[22] else 0.0
                except (ValueError, IndexError):
                    pass

        except (ValueError, IndexError) as e:
            logger.debug(f"Skipping row due to parse error: {e}")
            continue

        allocation = DwellUnitAllocation(
            zone_name=zone_name,
            conditioning_type=conditioning_type,
            space_function=space_function,
            pv_batt_bldg_type=pv_batt_bldg_type,
            floor_area_sqft=floor_area,
            multiplier=multiplier,
            num_res_dwellings=num_dwellings,
            prescriptive_pv_kwdc=pv_kwdc,
            prescriptive_batt_kwh=batt_kwh,
            prescriptive_batt_kw=batt_kw,
        )
        allocations.append(allocation)

    logger.info(f"Parsed {len(allocations)} dwelling unit allocations")
    return allocations


def parse_utility_rate(json_path: str) -> Optional[UtilityRate]:
    """
    Parse utility rate structure from er.json.

    The er.json file contains detailed utility rate information including:
    - Rate type (Electric/Gas)
    - Utility name and territory
    - Seasons and TOU periods
    - Tiered pricing

    Args:
        json_path: Path to er.json file

    Returns:
        UtilityRate object or None if parsing fails
    """
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:
        logger.error(f"Failed to parse JSON file {json_path}: {e}")
        return None

    # Parse seasons
    seasons = []
    for season_data in data.get('RateSeasons', []):
        tou_periods = []
        for tou_data in season_data.get('TimeOfUsePeriods', []):
            # Parse energy cost components
            energy_components = []
            cost_data = tou_data.get('CostComponents', {})
            for comp_data in cost_data.get('EnergyCostComponents', []):
                tiers = []
                for tier_data in comp_data.get('Tiers', []):
                    tier = Tier(
                        tier_number=tier_data.get('TierNumber', 0),
                        price=tier_data.get('Price', 0.0),
                        quantity=tier_data.get('Quantity'),
                    )
                    tiers.append(tier)

                component = EnergyCostComponent(
                    name=comp_data.get('Name', ''),
                    cost_component_period_type=comp_data.get('CostComponentPeriodType', ''),
                    delivery=comp_data.get('Delivery', False),
                    non_bypassable=comp_data.get('NonBypassable', False),
                    total_consumption=comp_data.get('TotalConsumption', False),
                    tiers=tiers,
                )
                energy_components.append(component)

            # Parse time periods
            for time_period in tou_data.get('TimePeriods', []):
                period = TouPeriod(
                    name=tou_data.get('Name', ''),
                    start_time=time_period.get('StartTime', 0.0),
                    end_time=time_period.get('EndTime', 24.0),
                    applicable_days=time_period.get('ApplicableDays', 'all'),
                    energy_cost_components=energy_components,
                )
                tou_periods.append(period)

        # Parse season periods
        season_periods = season_data.get('SeasonPeriods', [])
        start_month = season_periods[0].get('StartMonth', 1) if season_periods else 1
        end_month = season_periods[0].get('EndMonth', 12) if season_periods else 12

        # Parse minimum bill
        min_bill = None
        season_costs = season_data.get('SeasonCostComponents', {})
        for min_bill_comp in season_costs.get('MinimumBillCostComponents', []):
            min_bill = min_bill_comp.get('Amount', 0.0)
            break

        season = RateSeason(
            season_name=season_data.get('SeasonName', ''),
            start_month=start_month,
            end_month=end_month,
            tou_periods=tou_periods,
            minimum_bill_amount=min_bill,
        )
        seasons.append(season)

    rate = UtilityRate(
        rate_type=data.get('RateType', ''),
        utility=data.get('Utility', ''),
        rate_territory=data.get('RateTerritory', ''),
        rate_name=data.get('RateName', ''),
        public_id=data.get('PublicId', ''),
        encoded_rate_name=data.get('EncodedRateName', ''),
        description=data.get('Description', ''),
        metering_type=data.get('MeteringType', 'Standard'),
        seasons=seasons,
    )

    logger.info(f"Parsed utility rate: {rate.rate_name} ({rate.utility})")
    return rate


def find_cuac_files(run_folder: str) -> Dict[str, Optional[str]]:
    """
    Find CUAC-related files in a CBECC run folder.

    Args:
        run_folder: Path to CBECC run folder (e.g., "Project - run/")

    Returns:
        Dict with paths to found files:
        - 'analysis_results': Path to AnalysisResults.xml
        - 'pv_battery': Path to PVBattery.csv
        - 'utility_rate': Path to er.json
    """
    run_path = Path(run_folder)
    parent_path = run_path.parent

    result = {
        'analysis_results': None,
        'pv_battery': None,
        'utility_rate': None,
    }

    # Find AnalysisResults.xml (in parent folder)
    for xml_file in parent_path.glob('*AnalysisResults.xml'):
        result['analysis_results'] = str(xml_file)
        break

    # Find PVBattery.csv (in run folder)
    for csv_file in run_path.glob('*PVBattery.csv'):
        result['pv_battery'] = str(csv_file)
        break

    # Find er.json (in run folder)
    er_json = run_path / 'er.json'
    if er_json.exists():
        result['utility_rate'] = str(er_json)

    return result
