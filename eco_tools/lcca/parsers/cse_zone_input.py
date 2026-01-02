"""
Parser for CBECC-generated CSE input files (.cse) for zone-level metering.

Parses CSE input files into structured Python objects for manipulation,
enabling zone-level meter transformations. This parser focuses on:
- ZONE blocks with nested GAIN, SURFACE, TERMINAL objects
- RSYS blocks with meter assignments
- AIRHANDLER blocks with meter assignments
- METER blocks with submeter hierarchies
- EXPORT blocks for hourly data export

This is distinct from cse_input.py which focuses on DHW component parsing.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import re
import logging

logger = logging.getLogger(__name__)


@dataclass
class CSEGain:
    """Parsed GAIN definition from CSE input."""
    name: str
    zone_name: str
    meter: Optional[str] = None  # gnMeter assignment
    end_use: Optional[str] = None  # gnEndUse: Lit, Rcp, Proc, etc.
    power_expr: Optional[str] = None  # gnPower expression
    frac_radiant: Optional[float] = None
    frac_latent: Optional[float] = None
    line_start: int = 0
    line_end: int = 0
    raw_lines: List[str] = field(default_factory=list)


@dataclass
class CSESurface:
    """Parsed SURFACE definition from CSE input."""
    name: str
    zone_name: str
    surface_type: Optional[str] = None  # sfType: Wall, Ceiling, Floor
    construction: Optional[str] = None  # sfCon
    area_sf: Optional[float] = None
    line_start: int = 0
    line_end: int = 0


@dataclass
class CSETerminal:
    """Parsed TERMINAL definition from CSE input."""
    name: str
    zone_name: str
    air_handler: Optional[str] = None  # tuAh
    heating_setpoint: Optional[float] = None  # tuTH
    cooling_setpoint: Optional[float] = None  # tuTC
    line_start: int = 0
    line_end: int = 0


@dataclass
class CSEZone:
    """Parsed ZONE definition from CSE input."""
    name: str
    model: Optional[str] = None  # "CZM", "UZM", etc.
    area_sf: Optional[float] = None  # znArea
    volume_cf: Optional[float] = None  # znVol
    ceiling_height: Optional[float] = None  # znCeilingHt
    gains: List[CSEGain] = field(default_factory=list)
    surfaces: List[CSESurface] = field(default_factory=list)
    terminals: List[CSETerminal] = field(default_factory=list)
    line_start: int = 0
    line_end: int = 0
    raw_lines: List[str] = field(default_factory=list)


@dataclass
class CSEDuctSeg:
    """Parsed DUCTSEG definition from CSE input."""
    name: str
    rsys_name: str
    duct_type: Optional[str] = None  # dsTy: SUPPLY, RETURN
    diameter: Optional[float] = None
    insul_r: Optional[float] = None
    line_start: int = 0
    line_end: int = 0


@dataclass
class CSERsys:
    """Parsed RSYS (residential HVAC system) from CSE input."""
    name: str
    system_type: Optional[str] = None  # rsType: ASHP, etc.
    elec_meter: Optional[str] = None  # rsElecMtr
    supply_fan_meter: Optional[str] = None  # sfanMtr (for AIRHANDLER)
    cooling_coil_meter: Optional[str] = None  # ahccMtr
    heating_coil_meter: Optional[str] = None  # ahhcMtr
    seer: Optional[float] = None  # rsSEER
    hspf: Optional[float] = None  # rsHSPF
    eer: Optional[float] = None  # rsEER
    duct_segments: List[CSEDuctSeg] = field(default_factory=list)
    line_start: int = 0
    line_end: int = 0
    raw_lines: List[str] = field(default_factory=list)


@dataclass
class CSEAirHandler:
    """Parsed AIRHANDLER definition from CSE input."""
    name: str
    supply_fan_meter: Optional[str] = None  # sfanMtr
    cooling_coil_meter: Optional[str] = None  # ahccMtr
    heating_coil_meter: Optional[str] = None  # ahhcMtr
    line_start: int = 0
    line_end: int = 0
    raw_lines: List[str] = field(default_factory=list)


@dataclass
class CSEMeter:
    """Parsed METER definition from CSE input."""
    name: str
    submeters: List[str] = field(default_factory=list)  # mtrSubMeters
    submeter_mults: List[float] = field(default_factory=list)  # mtrSubMeterMults
    line_start: int = 0
    line_end: int = 0
    raw_lines: List[str] = field(default_factory=list)


@dataclass
class CSEExport:
    """Parsed EXPORT definition from CSE input."""
    name: str
    meter: Optional[str] = None  # exMeter
    frequency: Optional[str] = None  # exFreq: HOUR, DAY, MONTH, YEAR
    export_type: Optional[str] = None  # exType: MTR, UDT
    export_file: Optional[str] = None  # exExportfile
    btu_sf: Optional[float] = None  # exBtuSf
    line_start: int = 0
    line_end: int = 0
    raw_lines: List[str] = field(default_factory=list)


@dataclass
class CSEZoneInputModel:
    """Complete parsed CSE input file for zone-level metering."""
    filepath: Path = field(default_factory=Path)
    zones: Dict[str, CSEZone] = field(default_factory=dict)
    rsys_list: Dict[str, CSERsys] = field(default_factory=dict)
    air_handlers: Dict[str, CSEAirHandler] = field(default_factory=dict)
    meters: Dict[str, CSEMeter] = field(default_factory=dict)
    exports: Dict[str, CSEExport] = field(default_factory=dict)
    raw_lines: List[str] = field(default_factory=list)  # Complete file lines

    # Lookup maps
    gain_to_zone: Dict[str, str] = field(default_factory=dict)  # gain_name -> zone_name
    rsys_to_zones: Dict[str, List[str]] = field(default_factory=dict)  # rsys_name -> zone_names

    @property
    def all_gains(self) -> List[CSEGain]:
        """Get all gains across all zones."""
        gains = []
        for zone in self.zones.values():
            gains.extend(zone.gains)
        return gains

    def get_gains_with_meter(self, meter_name: str) -> List[CSEGain]:
        """Get all gains assigned to a specific meter."""
        return [g for g in self.all_gains if g.meter == meter_name]

    def get_zone_names(self) -> List[str]:
        """Get list of all zone names."""
        return list(self.zones.keys())

    def get_meter_names(self) -> List[str]:
        """Get list of all meter names."""
        return list(self.meters.keys())


class CSEZoneInputParser:
    """Parser for CBECC-generated CSE input files for zone-level metering."""

    # Regex patterns for CSE syntax
    OBJECT_START = re.compile(r'^(\w+)\s+"([^"]+)"\s*$')
    PROPERTY_LINE = re.compile(r'^\s*(\w+)\s*=\s*(.+)$')  # Property with or without leading space
    QUOTED_STRING = re.compile(r'^"([^"]*)"')
    MULTILINE_CONTINUE = re.compile(r',\s*$')

    # Object types that can be nested inside ZONE
    ZONE_NESTED = {'GAIN', 'SURFACE', 'TERMINAL', 'SGDIST', 'SHADE'}
    RSYS_NESTED = {'DUCTSEG'}
    AIRHANDLER_NESTED = {'COILCOOLING', 'COILHEATING', 'FAN'}

    def __init__(self):
        self.model = CSEZoneInputModel()
        self.parse_errors: List[str] = []
        self.parse_warnings: List[str] = []

    def parse_file(self, filepath: Path) -> CSEZoneInputModel:
        """
        Parse CSE input file into structured model.

        Args:
            filepath: Path to CSE input file (.cse)

        Returns:
            CSEZoneInputModel with parsed objects
        """
        filepath = Path(filepath)
        if not filepath.exists():
            raise FileNotFoundError(f"CSE input file not found: {filepath}")

        # Read file with encoding handling
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
        except UnicodeDecodeError:
            with open(filepath, 'r', encoding='latin-1') as f:
                content = f.read()

        lines = content.splitlines()

        self.model = CSEZoneInputModel(
            filepath=filepath,
            raw_lines=lines.copy()
        )
        self.parse_errors = []
        self.parse_warnings = []

        # Parse file
        self._parse_lines(lines)

        # Build lookup maps
        self._build_lookup_maps()

        if self.parse_errors:
            logger.warning(f"Parse errors in {filepath}: {len(self.parse_errors)}")
            for err in self.parse_errors[:5]:
                logger.debug(f"  {err}")

        logger.info(f"Parsed {filepath.name}: {len(self.model.zones)} zones, "
                   f"{len(self.model.meters)} meters, {len(self.model.rsys_list)} RSYS")

        return self.model

    def _parse_lines(self, lines: List[str]) -> None:
        """Parse all lines, identifying object blocks."""
        i = 0
        n = len(lines)

        while i < n:
            line = lines[i]
            stripped = line.strip()

            # Skip empty lines, comments, preprocessor directives
            if not stripped or stripped.startswith('//') or stripped.startswith('#'):
                i += 1
                continue

            # Check for object start
            match = self.OBJECT_START.match(stripped)
            if match:
                obj_type = match.group(1).upper()
                obj_name = match.group(2)

                # Parse object block
                if obj_type == 'ZONE':
                    i = self._parse_zone(lines, i, obj_name)
                elif obj_type == 'RSYS':
                    i = self._parse_rsys(lines, i, obj_name)
                elif obj_type == 'AIRHANDLER':
                    i = self._parse_airhandler(lines, i, obj_name)
                elif obj_type == 'METER':
                    i = self._parse_meter(lines, i, obj_name)
                elif obj_type == 'EXPORT':
                    i = self._parse_export(lines, i, obj_name)
                else:
                    # Skip other object types
                    i = self._skip_block(lines, i)
            else:
                i += 1

    def _parse_zone(self, lines: List[str], start: int, name: str) -> int:
        """Parse ZONE block including nested objects."""
        zone = CSEZone(name=name, line_start=start)
        i = start + 1
        n = len(lines)

        while i < n:
            line = lines[i]
            stripped = line.strip()

            # Check for nested object
            match = self.OBJECT_START.match(stripped)
            if match:
                obj_type = match.group(1).upper()
                obj_name = match.group(2)

                if obj_type in self.ZONE_NESTED:
                    if obj_type == 'GAIN':
                        gain, i = self._parse_gain(lines, i, obj_name, name)
                        zone.gains.append(gain)
                    elif obj_type == 'SURFACE':
                        surface, i = self._parse_surface(lines, i, obj_name, name)
                        zone.surfaces.append(surface)
                    elif obj_type == 'TERMINAL':
                        terminal, i = self._parse_terminal(lines, i, obj_name, name)
                        zone.terminals.append(terminal)
                    else:
                        i = self._skip_nested_block(lines, i)
                    # Don't increment i - nested parser returns next position
                    continue
                else:
                    # New top-level object - end of ZONE
                    zone.line_end = i - 1
                    zone.raw_lines = lines[start:i]
                    self.model.zones[name] = zone
                    return i
            elif stripped and not stripped.startswith('//'):
                # Property line
                props = self._parse_property(stripped)
                if props:
                    prop_name, prop_value = props
                    if prop_name == 'znModel':
                        zone.model = self._clean_string(prop_value)
                    elif prop_name == 'znArea':
                        zone.area_sf = self._parse_float(prop_value)
                    elif prop_name == 'znVol':
                        zone.volume_cf = self._parse_float(prop_value)
                    elif prop_name == 'znCeilingHt':
                        zone.ceiling_height = self._parse_float(prop_value)

            i += 1

        # End of file
        zone.line_end = n - 1
        zone.raw_lines = lines[start:n]
        self.model.zones[name] = zone
        return n

    def _parse_gain(self, lines: List[str], start: int, name: str, zone_name: str) -> Tuple[CSEGain, int]:
        """Parse GAIN block."""
        gain = CSEGain(name=name, zone_name=zone_name, line_start=start)
        i = start + 1
        n = len(lines)

        while i < n:
            line = lines[i]
            stripped = line.strip()

            # Check for next object (nested or new top-level)
            if self.OBJECT_START.match(stripped):
                gain.line_end = i - 1
                gain.raw_lines = lines[start:i]
                return gain, i

            if stripped and not stripped.startswith('//'):
                props = self._parse_property(stripped)
                if props:
                    prop_name, prop_value = props
                    if prop_name == 'gnMeter':
                        gain.meter = self._clean_string(prop_value)
                    elif prop_name == 'gnEndUse':
                        gain.end_use = self._clean_string(prop_value)
                    elif prop_name == 'gnPower':
                        gain.power_expr = prop_value
                    elif prop_name == 'gnFrRad':
                        gain.frac_radiant = self._parse_float(prop_value)
                    elif prop_name == 'gnFrLat':
                        gain.frac_latent = self._parse_float(prop_value)

            i += 1

        gain.line_end = n - 1
        gain.raw_lines = lines[start:n]
        return gain, n

    def _parse_surface(self, lines: List[str], start: int, name: str, zone_name: str) -> Tuple[CSESurface, int]:
        """Parse SURFACE block."""
        surface = CSESurface(name=name, zone_name=zone_name, line_start=start)
        i = start + 1
        n = len(lines)

        while i < n:
            line = lines[i]
            stripped = line.strip()

            if self.OBJECT_START.match(stripped):
                surface.line_end = i - 1
                return surface, i

            if stripped and not stripped.startswith('//'):
                props = self._parse_property(stripped)
                if props:
                    prop_name, prop_value = props
                    if prop_name == 'sfType':
                        surface.surface_type = self._clean_string(prop_value)
                    elif prop_name == 'sfCon':
                        surface.construction = self._clean_string(prop_value)
                    elif prop_name == 'sfArea':
                        surface.area_sf = self._parse_float(prop_value)

            i += 1

        surface.line_end = n - 1
        return surface, n

    def _parse_terminal(self, lines: List[str], start: int, name: str, zone_name: str) -> Tuple[CSETerminal, int]:
        """Parse TERMINAL block."""
        terminal = CSETerminal(name=name, zone_name=zone_name, line_start=start)
        i = start + 1
        n = len(lines)

        while i < n:
            line = lines[i]
            stripped = line.strip()

            if self.OBJECT_START.match(stripped):
                terminal.line_end = i - 1
                return terminal, i

            if stripped and not stripped.startswith('//'):
                props = self._parse_property(stripped)
                if props:
                    prop_name, prop_value = props
                    if prop_name == 'tuAh':
                        terminal.air_handler = self._clean_string(prop_value)
                    elif prop_name == 'tuTH':
                        terminal.heating_setpoint = self._parse_float(prop_value)
                    elif prop_name == 'tuTC':
                        terminal.cooling_setpoint = self._parse_float(prop_value)

            i += 1

        terminal.line_end = n - 1
        return terminal, n

    def _parse_rsys(self, lines: List[str], start: int, name: str) -> int:
        """Parse RSYS block including nested DUCTSEG."""
        rsys = CSERsys(name=name, line_start=start)
        i = start + 1
        n = len(lines)

        while i < n:
            line = lines[i]
            stripped = line.strip()

            match = self.OBJECT_START.match(stripped)
            if match:
                obj_type = match.group(1).upper()
                obj_name = match.group(2)

                if obj_type == 'DUCTSEG':
                    ductseg, i = self._parse_ductseg(lines, i, obj_name, name)
                    rsys.duct_segments.append(ductseg)
                else:
                    # New top-level object
                    rsys.line_end = i - 1
                    rsys.raw_lines = lines[start:i]
                    self.model.rsys_list[name] = rsys
                    return i
            elif stripped and not stripped.startswith('//'):
                props = self._parse_property(stripped)
                if props:
                    prop_name, prop_value = props
                    if prop_name == 'rsType':
                        rsys.system_type = self._clean_string(prop_value)
                    elif prop_name == 'rsElecMtr':
                        rsys.elec_meter = self._clean_string(prop_value)
                    elif prop_name == 'rsSEER':
                        rsys.seer = self._parse_float(prop_value)
                    elif prop_name == 'rsHSPF':
                        rsys.hspf = self._parse_float(prop_value)
                    elif prop_name == 'rsEER':
                        rsys.eer = self._parse_float(prop_value)

            i += 1

        rsys.line_end = n - 1
        rsys.raw_lines = lines[start:n]
        self.model.rsys_list[name] = rsys
        return n

    def _parse_ductseg(self, lines: List[str], start: int, name: str, rsys_name: str) -> Tuple[CSEDuctSeg, int]:
        """Parse DUCTSEG block."""
        ductseg = CSEDuctSeg(name=name, rsys_name=rsys_name, line_start=start)
        i = start + 1
        n = len(lines)

        while i < n:
            line = lines[i]
            stripped = line.strip()

            if self.OBJECT_START.match(stripped):
                ductseg.line_end = i - 1
                return ductseg, i

            if stripped and not stripped.startswith('//'):
                props = self._parse_property(stripped)
                if props:
                    prop_name, prop_value = props
                    if prop_name == 'dsTy':
                        ductseg.duct_type = self._clean_string(prop_value)
                    elif prop_name == 'dsDiameter':
                        ductseg.diameter = self._parse_float(prop_value)
                    elif prop_name == 'dsInsulR':
                        ductseg.insul_r = self._parse_float(prop_value)

            i += 1

        ductseg.line_end = n - 1
        return ductseg, n

    def _parse_airhandler(self, lines: List[str], start: int, name: str) -> int:
        """Parse AIRHANDLER block."""
        ah = CSEAirHandler(name=name, line_start=start)
        i = start + 1
        n = len(lines)

        while i < n:
            line = lines[i]
            stripped = line.strip()

            match = self.OBJECT_START.match(stripped)
            if match:
                obj_type = match.group(1).upper()
                if obj_type in self.AIRHANDLER_NESTED:
                    i = self._skip_nested_block(lines, i)
                else:
                    ah.line_end = i - 1
                    ah.raw_lines = lines[start:i]
                    self.model.air_handlers[name] = ah
                    return i
            elif stripped and not stripped.startswith('//'):
                props = self._parse_property(stripped)
                if props:
                    prop_name, prop_value = props
                    if prop_name == 'sfanMtr':
                        ah.supply_fan_meter = self._clean_string(prop_value)
                    elif prop_name == 'ahccMtr':
                        ah.cooling_coil_meter = self._clean_string(prop_value)
                    elif prop_name == 'ahhcMtr':
                        ah.heating_coil_meter = self._clean_string(prop_value)

            i += 1

        ah.line_end = n - 1
        ah.raw_lines = lines[start:n]
        self.model.air_handlers[name] = ah
        return n

    def _parse_meter(self, lines: List[str], start: int, name: str) -> int:
        """Parse METER block."""
        meter = CSEMeter(name=name, line_start=start)
        i = start + 1
        n = len(lines)

        # Track multi-line property continuation
        current_prop = None
        current_value = []

        while i < n:
            line = lines[i]
            stripped = line.strip()

            if self.OBJECT_START.match(stripped):
                # Process any pending multi-line property
                if current_prop:
                    self._apply_meter_property(meter, current_prop, ' '.join(current_value))

                meter.line_end = i - 1
                meter.raw_lines = lines[start:i]
                self.model.meters[name] = meter
                return i

            if stripped and not stripped.startswith('//'):
                # Check if this is a continuation line (starts with " or digit, no = sign before ")
                is_continuation = False
                if current_prop:
                    first_char = stripped[0] if stripped else ''
                    # Continuation if line starts with " or digit and no property assignment
                    if first_char == '"' or first_char.isdigit():
                        # Make sure it's not a new property (no = before first ")
                        eq_pos = stripped.find('=')
                        quote_pos = stripped.find('"')
                        if eq_pos < 0 or (quote_pos >= 0 and quote_pos < eq_pos):
                            is_continuation = True

                if is_continuation:
                    # Continuation of previous property
                    current_value.append(stripped)
                else:
                    # Process pending property
                    if current_prop:
                        self._apply_meter_property(meter, current_prop, ' '.join(current_value))
                        current_prop = None
                        current_value = []

                    props = self._parse_property(stripped)
                    if props:
                        prop_name, prop_value = props
                        # Check if property value ends with comma (multi-line)
                        if prop_value.rstrip().endswith(','):
                            current_prop = prop_name
                            current_value = [prop_value]
                        else:
                            self._apply_meter_property(meter, prop_name, prop_value)

            i += 1

        if current_prop:
            self._apply_meter_property(meter, current_prop, ' '.join(current_value))

        meter.line_end = n - 1
        meter.raw_lines = lines[start:n]
        self.model.meters[name] = meter
        return n

    def _apply_meter_property(self, meter: CSEMeter, prop_name: str, prop_value: str) -> None:
        """Apply a property to a METER object."""
        if prop_name == 'mtrSubMeters':
            meter.submeters = self._parse_string_list(prop_value)
        elif prop_name == 'mtrSubMeterMults':
            meter.submeter_mults = self._parse_float_list(prop_value)

    def _parse_export(self, lines: List[str], start: int, name: str) -> int:
        """Parse EXPORT block."""
        export = CSEExport(name=name, line_start=start)
        i = start + 1
        n = len(lines)

        while i < n:
            line = lines[i]
            stripped = line.strip()

            match = self.OBJECT_START.match(stripped)
            if match:
                obj_type = match.group(1).upper()
                if obj_type == 'EXPORTCOL':
                    i = self._skip_nested_block(lines, i)
                else:
                    export.line_end = i - 1
                    export.raw_lines = lines[start:i]
                    self.model.exports[name] = export
                    return i
            elif stripped and not stripped.startswith('//'):
                props = self._parse_property(stripped)
                if props:
                    prop_name, prop_value = props
                    if prop_name == 'exMeter':
                        export.meter = self._clean_string(prop_value)
                    elif prop_name == 'exFreq':
                        export.frequency = self._clean_string(prop_value)
                    elif prop_name == 'exType':
                        export.export_type = self._clean_string(prop_value)
                    elif prop_name == 'exExportfile':
                        export.export_file = self._clean_string(prop_value)
                    elif prop_name == 'exBtuSf':
                        export.btu_sf = self._parse_float(prop_value)

            i += 1

        export.line_end = n - 1
        export.raw_lines = lines[start:n]
        self.model.exports[name] = export
        return n

    def _skip_block(self, lines: List[str], start: int) -> int:
        """Skip an object block we don't need to parse."""
        i = start + 1
        n = len(lines)

        while i < n:
            line = lines[i]
            stripped = line.strip()

            if self.OBJECT_START.match(stripped):
                return i

            i += 1

        return n

    def _skip_nested_block(self, lines: List[str], start: int) -> int:
        """Skip a nested object block."""
        return self._skip_block(lines, start)

    def _parse_property(self, line: str) -> Optional[Tuple[str, str]]:
        """Parse a property line into (name, value) tuple."""
        match = self.PROPERTY_LINE.match(line)
        if match:
            prop_name = match.group(1)
            prop_value = match.group(2).strip()
            # Remove trailing comment if present (but not inside quotes)
            if '//' in prop_value:
                # Find // that's outside of quoted strings
                in_quotes = False
                for i, char in enumerate(prop_value):
                    if char == '"':
                        in_quotes = not in_quotes
                    elif prop_value[i:i+2] == '//' and not in_quotes:
                        prop_value = prop_value[:i].strip()
                        break
            return prop_name, prop_value
        return None

    def _clean_string(self, value: str) -> str:
        """Remove quotes and comments from a string value."""
        # Remove inline comment
        if '//' in value:
            value = value.split('//')[0].strip()

        # Remove quotes
        match = self.QUOTED_STRING.match(value)
        if match:
            return match.group(1)

        return value.strip('"').strip()

    def _parse_float(self, value: str) -> Optional[float]:
        """Parse a float value from property."""
        try:
            # Remove comments
            if '//' in value:
                value = value.split('//')[0].strip()
            return float(value)
        except (ValueError, TypeError):
            return None

    def _parse_string_list(self, value: str) -> List[str]:
        """Parse a comma-separated list of quoted strings."""
        # Remove comments
        if '//' in value:
            value = value.split('//')[0].strip()

        # Find all quoted strings
        strings = re.findall(r'"([^"]*)"', value)
        return strings

    def _parse_float_list(self, value: str) -> List[float]:
        """Parse a comma-separated list of floats."""
        # Remove comments
        if '//' in value:
            value = value.split('//')[0].strip()

        floats = []
        for part in value.split(','):
            part = part.strip()
            if part:
                try:
                    floats.append(float(part))
                except ValueError:
                    pass
        return floats

    def _build_lookup_maps(self) -> None:
        """Build lookup maps for quick access."""
        # Gain to zone mapping
        for zone in self.model.zones.values():
            for gain in zone.gains:
                self.model.gain_to_zone[gain.name] = zone.name

        # RSYS to zones - infer from naming convention
        # e.g., "rsys-Dwelling Unit_L01_1BR HVACSys" -> "Dwelling Unit_L01_1BR-zn"
        for rsys_name in self.model.rsys_list:
            # Extract zone base name from rsys name
            if rsys_name.startswith('rsys-'):
                base = rsys_name[5:]  # Remove "rsys-"
                if ' HVACSys' in base:
                    base = base.replace(' HVACSys', '')
                zone_name = f"{base}-zn"
                if zone_name in self.model.zones:
                    self.model.rsys_to_zones[rsys_name] = [zone_name]


def parse_cse_zone_input(filepath: Path) -> CSEZoneInputModel:
    """
    Parse a CSE input file for zone-level metering.

    Args:
        filepath: Path to the CSE input file

    Returns:
        CSEZoneInputModel with parsed objects
    """
    parser = CSEZoneInputParser()
    return parser.parse_file(filepath)
