"""
Split ResZn for CUAC Compliance
================================

CBECC CUAC requires each ResZn to have dwellings with the same bedroom count.
This script splits consolidated ResZn elements into separate zones by bedroom type,
distributing envelope elements proportionally by conditioned floor area.

Key improvements in this version:
- Only splits envelope elements BEFORE ResOtherZn (dwelling envelope only)
- Groups walls with their following windows to maintain wall-window relationships
- Splits wall-window pairs with same proportion to prevent window > wall errors
- Preserves ResOtherZn blocks unchanged

Usage:
    python split_reszone_for_cuac.py input.cibd22 output.cibd22
"""

import re
import sys
from pathlib import Path
from dataclasses import dataclass, field
from typing import Dict, List, Tuple, Optional


@dataclass
class DwellUnitType:
    """Dwelling unit type definition."""
    name: str
    num_bedrooms: int = 1
    cond_flr_area: float = 0.0
    raw_content: str = ""


@dataclass
class DwellUnit:
    """Dwelling unit instance in a ResZn."""
    name: str
    unit_type_ref: str
    count: int = 1
    raw_content: str = ""


@dataclass
class WallWithWindows:
    """A wall element with its associated windows."""
    wall_type: str  # ResExtWall
    wall_name: str
    wall_area: float
    wall_content: str
    windows: List[Tuple[str, float, str]] = field(default_factory=list)  # (name, area, content)

    def split_proportionally(self, proportion: float, suffix: str) -> str:
        """Split this wall and its windows by the given proportion."""
        # Scale wall area
        new_wall_area = round(self.wall_area * proportion, 1)
        new_wall_content = self.wall_content

        # Update wall name
        new_wall_content = re.sub(
            rf'^{self.wall_type}\s+"[^"]+"',
            f'{self.wall_type}   "{self.wall_name}_{suffix}"',
            new_wall_content,
            flags=re.MULTILINE
        )

        # Update wall area
        new_wall_content = re.sub(r'Area\s*=\s*[\d.]+', f'Area = {new_wall_area}', new_wall_content)

        result = [new_wall_content]

        # Split each window with same proportion
        for win_name, win_area, win_content in self.windows:
            new_win_area = round(win_area * proportion, 1)
            new_win_content = win_content

            # Update window name
            new_win_content = re.sub(
                r'^ResWin\s+"[^"]+"',
                f'ResWin   "{win_name}_{suffix}"',
                new_win_content,
                flags=re.MULTILINE
            )

            # Update window area
            new_win_content = re.sub(r'Area\s*=\s*[\d.]+', f'Area = {new_win_area}', new_win_content)

            result.append(new_win_content)

        return ''.join(result)


@dataclass
class FloorElement:
    """A floor element (ResSlabFlr, ResIntFlr)."""
    element_type: str
    name: str
    area: float
    perimeter: float
    content: str

    def split_proportionally(self, proportion: float, suffix: str) -> str:
        """Split this floor by the given proportion."""
        new_area = round(self.area * proportion, 1)
        new_perimeter = round(self.perimeter * proportion, 1) if self.perimeter else 0
        new_content = self.content

        # Update name
        new_content = re.sub(
            rf'^{self.element_type}\s+"[^"]+"',
            f'{self.element_type}   "{self.name}_{suffix}"',
            new_content,
            flags=re.MULTILINE
        )

        # Update area
        new_content = re.sub(r'Area\s*=\s*[\d.]+', f'Area = {new_area}', new_content)

        # Update perimeter if present
        if new_perimeter:
            new_content = re.sub(r'Perimeter\s*=\s*[\d.]+', f'Perimeter = {new_perimeter}', new_content)

        return new_content


def parse_dwell_unit_types(content: str) -> Dict[str, DwellUnitType]:
    """Parse all DwellUnitType definitions from the file."""
    unit_types = {}

    pattern = r'^DwellUnitType\s+"([^"]+)".*?(?=^(?:DwellUnitType|ResZnGrp|ResZn|$))'
    matches = re.finditer(pattern, content, re.MULTILINE | re.DOTALL)

    for match in matches:
        name = match.group(1)
        block = match.group(0)

        bedrooms_match = re.search(r'NumBedrooms\s*=\s*(\d+)', block)
        num_bedrooms = int(bedrooms_match.group(1)) if bedrooms_match else 1

        area_match = re.search(r'CondFlrArea\s*=\s*([\d.]+)', block)
        cond_flr_area = float(area_match.group(1)) if area_match else 0.0

        unit_types[name] = DwellUnitType(
            name=name,
            num_bedrooms=num_bedrooms,
            cond_flr_area=cond_flr_area,
            raw_content=block
        )

    return unit_types


def parse_dwelling_envelope(block: str) -> Tuple[List[FloorElement], List[WallWithWindows]]:
    """
    Parse dwelling envelope elements from a ResZn block.
    Only parses elements BEFORE the first ResOtherZn.
    Groups walls with their following windows.
    """
    # Find where ResOtherZn starts (stop parsing there)
    other_zn_match = re.search(r'^ResOtherZn\s+', block, re.MULTILINE)
    if other_zn_match:
        dwelling_section = block[:other_zn_match.start()]
    else:
        dwelling_section = block

    floors = []
    walls_with_windows = []

    # Parse floor elements
    for floor_type in ['ResSlabFlr', 'ResIntFlr', 'ResCathedralCeiling']:
        floor_pattern = rf'^{floor_type}\s+"([^"]+)".*?(?=^(?:ResSlabFlr|ResIntFlr|ResCathedralCeiling|ResExtWall|ResWin|ResIntWall|ResOtherZn|ResZn|$))'
        for match in re.finditer(floor_pattern, dwelling_section, re.MULTILINE | re.DOTALL):
            name = match.group(1)
            content = match.group(0)

            area_match = re.search(r'Area\s*=\s*([\d.]+)', content)
            area = float(area_match.group(1)) if area_match else 0.0

            perim_match = re.search(r'Perimeter\s*=\s*([\d.]+)', content)
            perimeter = float(perim_match.group(1)) if perim_match else 0.0

            floors.append(FloorElement(
                element_type=floor_type,
                name=name,
                area=area,
                perimeter=perimeter,
                content=content
            ))

    # Parse walls and group with following windows
    # Find all ResExtWall and ResWin positions
    wall_pattern = r'^ResExtWall\s+"([^"]+)".*?(?=^(?:ResSlabFlr|ResIntFlr|ResCathedralCeiling|ResExtWall|ResIntWall|ResOtherZn|ResZn|$))'
    win_pattern = r'^ResWin\s+"([^"]+)".*?(?=^(?:ResSlabFlr|ResIntFlr|ResCathedralCeiling|ResExtWall|ResWin|ResIntWall|ResOtherZn|ResZn|$))'

    # Get all walls
    for wall_match in re.finditer(wall_pattern, dwelling_section, re.MULTILINE | re.DOTALL):
        wall_name = wall_match.group(1)
        wall_content = wall_match.group(0)
        wall_end = wall_match.end()

        area_match = re.search(r'Area\s*=\s*([\d.]+)', wall_content)
        wall_area = float(area_match.group(1)) if area_match else 0.0

        wall_obj = WallWithWindows(
            wall_type='ResExtWall',
            wall_name=wall_name,
            wall_area=wall_area,
            wall_content=wall_content
        )

        # Find windows that follow this wall (before next wall or other element)
        remaining = dwelling_section[wall_end:]
        next_wall = re.search(r'^ResExtWall\s+', remaining, re.MULTILINE)
        next_other = re.search(r'^(?:ResIntWall|ResOtherZn|ResZn)', remaining, re.MULTILINE)

        if next_wall:
            window_section = remaining[:next_wall.start()]
        elif next_other:
            window_section = remaining[:next_other.start()]
        else:
            window_section = remaining

        # Parse windows in this section
        for win_match in re.finditer(win_pattern, window_section, re.MULTILINE | re.DOTALL):
            win_name = win_match.group(1)
            win_content = win_match.group(0)

            win_area_match = re.search(r'Area\s*=\s*([\d.]+)', win_content)
            win_area = float(win_area_match.group(1)) if win_area_match else 0.0

            wall_obj.windows.append((win_name, win_area, win_content))

        walls_with_windows.append(wall_obj)

    return floors, walls_with_windows


def parse_reszone(content: str, start_pos: int, end_pos: int) -> dict:
    """Parse a single ResZn block into components."""
    block = content[start_pos:end_pos]

    # Get zone name
    name_match = re.search(r'^ResZn\s+"([^"]+)"', block, re.MULTILINE)
    zone_name = name_match.group(1) if name_match else "Unknown"

    # Find the zone header (ResZn line to first DwellUnit or envelope)
    header_match = re.search(r'^(ResZn\s+"[^"]+".*?\.\.)\s*\n', block, re.MULTILINE | re.DOTALL)
    zone_header = header_match.group(1) if header_match else ""

    # Parse DwellUnits
    dwell_units = []
    du_pattern = r'^DwellUnit\s+"([^"]+)".*?(?=^(?:DwellUnit|ResSlabFlr|ResExtWall|ResIntWall|ResOtherZn|ResZn|$))'
    for match in re.finditer(du_pattern, block, re.MULTILINE | re.DOTALL):
        du_name = match.group(1)
        du_block = match.group(0)

        type_ref_match = re.search(r'DwellUnitTypeRef\s*=\s*"([^"]+)"', du_block)
        type_ref = type_ref_match.group(1) if type_ref_match else ""

        count_match = re.search(r'Count\s*=\s*(\d+)', du_block)
        count = int(count_match.group(1)) if count_match else 1

        dwell_units.append(DwellUnit(
            name=du_name,
            unit_type_ref=type_ref,
            count=count,
            raw_content=du_block
        ))

    # Parse dwelling envelope (before ResOtherZn)
    floors, walls = parse_dwelling_envelope(block)

    # Extract ResOtherZn section (everything from first ResOtherZn to end)
    other_zn_match = re.search(r'^(ResOtherZn\s+.*)', block, re.MULTILINE | re.DOTALL)
    other_zones_section = other_zn_match.group(1) if other_zn_match else ""

    return {
        'name': zone_name,
        'header': zone_header,
        'dwell_units': dwell_units,
        'floors': floors,
        'walls': walls,
        'other_zones': other_zones_section,
        'raw_content': block
    }


def needs_splitting(dwell_units: List[DwellUnit], unit_types: Dict[str, DwellUnitType]) -> bool:
    """Check if zone has mixed bedroom types."""
    bedroom_counts = set()
    for du in dwell_units:
        if du.unit_type_ref in unit_types:
            bedroom_counts.add(unit_types[du.unit_type_ref].num_bedrooms)
    return len(bedroom_counts) > 1


def get_bedroom_groups(dwell_units: List[DwellUnit], unit_types: Dict[str, DwellUnitType]) -> Dict[int, List[DwellUnit]]:
    """Group dwelling units by bedroom count."""
    by_bedroom = {}
    for du in dwell_units:
        if du.unit_type_ref in unit_types:
            bedrooms = unit_types[du.unit_type_ref].num_bedrooms
            if bedrooms not in by_bedroom:
                by_bedroom[bedrooms] = []
            by_bedroom[bedrooms].append(du)
    return by_bedroom


def calculate_proportions(dwell_units: List[DwellUnit], unit_types: Dict[str, DwellUnitType]) -> Dict[int, float]:
    """Calculate area proportions for each bedroom type in the zone."""
    total_area = 0.0
    bedroom_areas = {}

    for du in dwell_units:
        if du.unit_type_ref in unit_types:
            ut = unit_types[du.unit_type_ref]
            area = ut.cond_flr_area * du.count
            bedrooms = ut.num_bedrooms
            bedroom_areas[bedrooms] = bedroom_areas.get(bedrooms, 0) + area
            total_area += area

    if total_area == 0:
        return {}

    return {br: area / total_area for br, area in bedroom_areas.items()}


def generate_split_zones(zone: dict, unit_types: Dict[str, DwellUnitType]) -> str:
    """Generate new ResZn blocks split by bedroom type."""
    dwell_units = zone['dwell_units']
    proportions = calculate_proportions(dwell_units, unit_types)
    bedroom_groups = get_bedroom_groups(dwell_units, unit_types)

    new_zones = []

    for bedrooms in sorted(bedroom_groups.keys()):
        dus = bedroom_groups[bedrooms]
        prop = proportions[bedrooms]
        suffix = f"{bedrooms}BR"

        # Create new zone name
        new_zone_name = f"{zone['name']}_{suffix}"

        # Generate zone header with new name and AffordableHousing flag
        new_header = zone['header'].replace(f'"{zone["name"]}"', f'"{new_zone_name}"')
        if "AffordableHousing" not in new_header:
            new_header = re.sub(r'(\s+\.\.)', r'\n   AffordableHousing = 1\1', new_header)

        zone_content = [new_header + '\n\n']

        # Add dwelling units for this bedroom count
        for du in dus:
            du_content = du.raw_content.replace(f'"{du.name}"', f'"{du.name}_{suffix}"')
            zone_content.append(du_content)

        # Add split floor elements
        for floor in zone['floors']:
            zone_content.append(floor.split_proportionally(prop, suffix))

        # Add split wall-window pairs
        for wall in zone['walls']:
            zone_content.append(wall.split_proportionally(prop, suffix))

        new_zones.append(''.join(zone_content))

    # Add the original ResOtherZn section after all new zones
    # Update references to the old zone name
    other_zones = zone['other_zones']
    if other_zones:
        # Update interior wall references to point to the largest (3BR) zone
        new_zone_names = [f"{zone['name']}_{br}BR" for br in sorted(bedroom_groups.keys())]
        primary_zone = sorted(new_zone_names, reverse=True)[0]  # 3BR zone
        other_zones = re.sub(
            rf'Outside\s*=\s*"{re.escape(zone["name"])}"',
            f'Outside = "{primary_zone}"',
            other_zones
        )
        new_zones.append(other_zones)

    return '\n'.join(new_zones)


def process_cibd_file(input_path: Path, output_path: Path):
    """Process a CIBD file to split ResZn for CUAC compliance."""
    content = input_path.read_text(encoding='utf-8')

    # Parse DwellUnitTypes
    unit_types = parse_dwell_unit_types(content)
    print(f"Found {len(unit_types)} DwellUnitTypes:")
    for name, ut in unit_types.items():
        print(f"  {name}: {ut.num_bedrooms}BR, {ut.cond_flr_area} SF")

    # Find all ResZn blocks (not ResZnGrp)
    reszone_starts = [(m.start(), m.group(1)) for m in re.finditer(r'^ResZn\s+"([^"]+)"', content, re.MULTILINE)]

    # Determine end positions
    zone_boundaries = []
    for i, (start, name) in enumerate(reszone_starts):
        if i + 1 < len(reszone_starts):
            end = reszone_starts[i + 1][0]
        else:
            next_grp = re.search(r'^ResZnGrp\s+', content[start+1:], re.MULTILINE)
            if next_grp:
                end = start + 1 + next_grp.start()
            else:
                end = len(content)
        zone_boundaries.append((start, end, name))

    # Find zones that need splitting
    zones_to_split = []
    for start, end, name in zone_boundaries:
        zone = parse_reszone(content, start, end)
        if needs_splitting(zone['dwell_units'], unit_types):
            zones_to_split.append((zone, start, end))
            print(f"\nZone '{zone['name']}' needs splitting:")
            for du in zone['dwell_units']:
                ut = unit_types.get(du.unit_type_ref)
                if ut:
                    print(f"  - {du.name}: {du.count}x {ut.num_bedrooms}BR ({ut.cond_flr_area} SF each)")
            print(f"  Proportions: {calculate_proportions(zone['dwell_units'], unit_types)}")

    if not zones_to_split:
        print("\nNo zones need splitting!")
        output_path.write_text(content, encoding='utf-8')
        return

    # Process in reverse order to maintain positions
    new_content = content
    for zone, start, end in reversed(zones_to_split):
        replacement = generate_split_zones(zone, unit_types)
        new_content = new_content[:start] + replacement + new_content[end:]

    # Write output
    output_path.write_text(new_content, encoding='utf-8')
    print(f"\nWrote split model to: {output_path}")


def main():
    if len(sys.argv) < 3:
        print("Usage: python split_reszone_for_cuac.py input.cibd22 output.cibd22")
        print("\nThis script splits consolidated ResZn elements by bedroom type for CUAC compliance.")
        print("\nKey features:")
        print("  - Only splits dwelling envelope (before ResOtherZn)")
        print("  - Groups walls with their windows to maintain area relationships")
        print("  - Preserves ResOtherZn blocks unchanged")
        print("  - Adds AffordableHousing = 1 to each new zone")
        sys.exit(1)

    input_path = Path(sys.argv[1])
    output_path = Path(sys.argv[2])

    if not input_path.exists():
        print(f"Error: Input file not found: {input_path}")
        sys.exit(1)

    process_cibd_file(input_path, output_path)


if __name__ == "__main__":
    main()
