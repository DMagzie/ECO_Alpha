"""
ResOther Zone Parser
====================

Parsers for extracting ResOther zone data from CBECC files.
Supports both .cibd22/.cibd25 input files and AnalysisResults.xml output.
"""

import re
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from collections import defaultdict

from .models import (
    CommonAreaCategory,
    ResOtherZone,
    CommonAreaMeterAllocation,
    classify_space_function,
)


def parse_res_other_zones(file_path: str) -> List[ResOtherZone]:
    """
    Parse ResOther zones from a CBECC file.

    Automatically detects file type (.cibd22, .cibd25, .xml) and
    uses appropriate parser.

    Args:
        file_path: Path to CBECC input or output file

    Returns:
        List of ResOtherZone objects
    """
    path = Path(file_path)

    if path.suffix.lower() == '.xml':
        return parse_res_other_from_xml(file_path)
    elif path.suffix.lower() in ['.cibd22', '.cibd25', '.cibd22x', '.cibd25x']:
        return parse_res_other_from_cibd(file_path)
    else:
        # Try both formats
        try:
            return parse_res_other_from_xml(file_path)
        except Exception:
            return parse_res_other_from_cibd(file_path)


def parse_res_other_from_cibd(file_path: str) -> List[ResOtherZone]:
    """
    Parse ResOther zones from a CBECC .cibd22/.cibd25 file.

    The CIBD format uses a simple key-value structure:
    ResOtherZn   "ZoneName"
       Type = "Conditioned"
       SpcFunc = "Corridor Area"
       Area = 1234
       ...

    Args:
        file_path: Path to .cibd22 or .cibd25 file

    Returns:
        List of ResOtherZone objects
    """
    zones = []

    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()

    # Pattern to match ResOtherZn blocks
    # Match: ResOtherZn   "name"  followed by indented properties until next element
    pattern = r'ResOtherZn\s+"([^"]+)"\s*\n((?:\s+[^\n]+\n)*?)(?=\n\s*\w+\s+"|$|\n--)'

    for match in re.finditer(pattern, content, re.MULTILINE):
        zone_name = match.group(1)
        properties_block = match.group(2)

        # Parse properties
        props = parse_cibd_properties(properties_block)

        # Extract zone properties
        zone = ResOtherZone(
            name=zone_name,
            space_function=props.get('SpcFunc', 'Unknown'),
            conditioning_type=props.get('Type', 'Conditioned'),
            area_sqft=float(props.get('Area', 0)),
            ceiling_height=float(props.get('CeilingHeight', 10)),
            hvac_system_ref=props.get('ozHVACSystem'),
            dhw_system_ref=props.get('ozDHWSys'),
            iaq_option=props.get('IAQOption'),
            multiplier=int(props.get('Mult', 1)),
        )

        # Try to extract floor level from name
        zone.floor_level = extract_floor_level(zone_name)

        zones.append(zone)

    return zones


def parse_cibd_properties(block: str) -> Dict[str, str]:
    """Parse key-value properties from a CIBD block."""
    props = {}

    for line in block.split('\n'):
        line = line.strip()
        if '=' in line:
            # Handle: Key = "Value" or Key = Value
            match = re.match(r'(\w+)\s*=\s*"?([^"\n]*)"?', line)
            if match:
                key, value = match.groups()
                props[key] = value.strip()

    return props


def extract_floor_level(zone_name: str) -> Optional[str]:
    """
    Extract floor level from zone name.

    Common patterns:
    - Corridor_L01 -> L01
    - Zone_P01 -> P01 (parking level)
    - Zone_B1 -> B1 (basement)
    - Zone_3F -> 3F (3rd floor)
    """
    patterns = [
        r'[_-]?(L\d+)',      # L01, L02, etc.
        r'[_-]?(P\d+)',      # P01 (parking)
        r'[_-]?(B\d+)',      # B1 (basement)
        r'[_-]?(\d+F)',      # 3F (floor)
        r'[_-]?Floor[_\s]*(\d+)',  # Floor 3
    ]

    for pattern in patterns:
        match = re.search(pattern, zone_name, re.IGNORECASE)
        if match:
            return match.group(1).upper()

    return None


def parse_res_other_from_xml(file_path: str) -> List[ResOtherZone]:
    """
    Parse ResOther zones from an AnalysisResults.xml file.

    Args:
        file_path: Path to AnalysisResults.xml

    Returns:
        List of ResOtherZone objects
    """
    zones = []
    tree = ET.parse(file_path)
    root = tree.getroot()

    # Find all ResOtherZn elements
    for elem in root.iter():
        if elem.tag == 'ResOtherZn' or elem.tag.endswith('}ResOtherZn'):
            zone = parse_xml_res_other_zone(elem)
            if zone:
                zones.append(zone)

    return zones


def parse_xml_res_other_zone(elem: ET.Element) -> Optional[ResOtherZone]:
    """Parse a single ResOtherZn XML element."""

    def get_text(tag: str) -> Optional[str]:
        child = elem.find(tag)
        if child is not None and child.text:
            return child.text.strip()
        return None

    def get_float(tag: str, default: float = 0.0) -> float:
        text = get_text(tag)
        if text:
            try:
                return float(text)
            except ValueError:
                pass
        return default

    name = get_text('Name')
    if not name:
        return None

    return ResOtherZone(
        name=name,
        space_function=get_text('SpcFunc') or 'Unknown',
        conditioning_type=get_text('Type') or 'Conditioned',
        area_sqft=get_float('Area'),
        ceiling_height=get_float('CeilingHeight', 10.0),
        hvac_system_ref=get_text('ozHVACSystem'),
        dhw_system_ref=get_text('ozDHWSys'),
        iaq_option=get_text('IAQOption'),
        multiplier=int(get_float('Mult', 1)),
        floor_level=extract_floor_level(name),
    )


def aggregate_by_category(zones: List[ResOtherZone]) -> Dict[CommonAreaCategory, CommonAreaMeterAllocation]:
    """
    Aggregate zones by their space function category.

    Args:
        zones: List of ResOtherZone objects

    Returns:
        Dict mapping category to meter allocation
    """
    allocations: Dict[CommonAreaCategory, CommonAreaMeterAllocation] = {}

    for zone in zones:
        category = zone.category

        if category not in allocations:
            allocations[category] = CommonAreaMeterAllocation(
                category=category,
                meter_name=f"MtrElec_{category.value.title()}",
            )

        allocations[category].add_zone(zone)

    return allocations


def create_meter_allocations(
    zones: List[ResOtherZone],
    group_by: str = "category"
) -> List[CommonAreaMeterAllocation]:
    """
    Create meter allocations for ResOther zones.

    Args:
        zones: List of ResOtherZone objects
        group_by: How to group zones:
            - "category": Group by space function category (default)
            - "floor": Group by floor level
            - "individual": Each zone gets its own meter
            - "all": All zones to single meter

    Returns:
        List of CommonAreaMeterAllocation objects
    """
    if group_by == "category":
        return list(aggregate_by_category(zones).values())

    elif group_by == "floor":
        floor_groups: Dict[str, CommonAreaMeterAllocation] = {}
        for zone in zones:
            floor = zone.floor_level or "Unknown"
            if floor not in floor_groups:
                floor_groups[floor] = CommonAreaMeterAllocation(
                    category=CommonAreaCategory.OTHER,
                    meter_name=f"MtrElec_Floor_{floor}",
                )
            floor_groups[floor].add_zone(zone)
        return list(floor_groups.values())

    elif group_by == "individual":
        return [
            CommonAreaMeterAllocation(
                category=zone.category,
                meter_name=f"MtrElec_{zone.name.replace(' ', '_')}",
                zones=[zone],
            )
            for zone in zones
        ]

    elif group_by == "all":
        allocation = CommonAreaMeterAllocation(
            category=CommonAreaCategory.OTHER,
            meter_name="MtrElec_CommonArea",
        )
        for zone in zones:
            allocation.add_zone(zone)
        return [allocation]

    else:
        raise ValueError(f"Unknown grouping: {group_by}")


def summarize_common_areas(zones: List[ResOtherZone]) -> Dict[str, any]:
    """
    Generate a summary of common area zones.

    Args:
        zones: List of ResOtherZone objects

    Returns:
        Summary dict with statistics
    """
    allocations = aggregate_by_category(zones)

    total_area = sum(z.total_area for z in zones)
    conditioned_area = sum(z.total_area for z in zones if z.is_conditioned)

    category_summary = {}
    for cat, alloc in allocations.items():
        category_summary[cat.value] = {
            'zone_count': alloc.zone_count,
            'total_area_sqft': alloc.total_area_sqft,
            'conditioned_area_sqft': alloc.conditioned_area_sqft,
            'area_fraction': alloc.get_area_fraction(total_area),
            'zones': alloc.zone_names,
        }

    return {
        'total_zones': len(zones),
        'total_area_sqft': total_area,
        'conditioned_area_sqft': conditioned_area,
        'unconditioned_area_sqft': total_area - conditioned_area,
        'categories': category_summary,
    }
