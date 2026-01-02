"""
CSE Input Transformer
=====================

Transforms CBECC-generated CSE input files with zone-level metering.

This module:
- Injects new METER definitions (zone-level + hierarchical)
- Updates GAIN gnMeter references to point to zone-specific meters
- Updates RSYS meter references (rsElecMtr)
- Injects EXPORT definitions for hourly data from all new meters
- Generates transformed CSE content as a new file

The transformation preserves all original CSE content while adding
zone-level metering capability.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple
import re
import logging

from .parsers.cse_zone_input import (
    CSEZoneInputModel,
    CSEZone,
    CSEGain,
    CSERsys,
    CSEMeter,
    CSEExport,
    parse_cse_zone_input,
)
from .zone_meter_mapper import (
    ZoneMeterAssignment,
    MeterHierarchy,
    ZoneMeterMapper,
)

logger = logging.getLogger(__name__)


# =============================================================================
# CONSTANTS
# =============================================================================

# Export file name for zone-level meter exports
ZONE_EXPORT_FILE = "Primary"  # Use same as existing exports

# Export settings
EXPORT_TYPE = "MTR"
EXPORT_FREQ = "HOUR"
EXPORT_BTU_SF = 1000  # Electric: kWh = kBtu / 3.412
EXPORT_BTU_SF_GAS = 100  # Gas: therms = kBtu / 100
EXPORT_DAY_BEG = "Jan 1"
EXPORT_DAY_END = "Dec 31"

# Fuel types
FUEL_ELECTRIC = "ELEC"
FUEL_GAS = "GAS"


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class TransformResult:
    """Result of CSE input transformation."""
    success: bool
    original_file: str
    transformed_content: str

    # Electric statistics
    meters_added: int = 0
    exports_added: int = 0
    gains_updated: int = 0
    rsys_updated: int = 0

    # Gas statistics
    gas_meters_added: int = 0
    gas_exports_added: int = 0
    rsys_fuel_updated: int = 0

    # Mapping info
    zone_assignments: Dict[str, ZoneMeterAssignment] = field(default_factory=dict)
    meter_hierarchy: Optional[MeterHierarchy] = None

    # Errors and warnings
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


@dataclass
class CSEMeterDefinition:
    """CSE METER definition for injection."""
    name: str
    submeters: List[str] = field(default_factory=list)
    submeter_mults: List[int] = field(default_factory=list)

    def to_cse_string(self) -> str:
        """Convert to CSE METER block string."""
        lines = [f'METER   "{self.name}"  ']

        if self.submeters:
            # Format submeter list
            submeter_str = ', '.join(f'"{m}"' for m in self.submeters)
            lines.append(f'   mtrSubMeters = {submeter_str}')

            # Format multiplier list
            mult_str = ', '.join(str(m) for m in self.submeter_mults)
            lines.append(f'   mtrSubMeterMults = {mult_str}')

        lines.append('')  # Blank line after block
        return '\n'.join(lines)


@dataclass
class CSEExportDefinition:
    """CSE EXPORT definition for injection."""
    name: str
    meter: str
    fuel_type: str = FUEL_ELECTRIC  # "ELEC" or "GAS"
    exportfile: str = ZONE_EXPORT_FILE
    export_type: str = EXPORT_TYPE
    freq: str = EXPORT_FREQ
    btu_sf: int = EXPORT_BTU_SF  # Will be overridden for gas
    day_beg: str = EXPORT_DAY_BEG
    day_end: str = EXPORT_DAY_END

    def __post_init__(self):
        """Set appropriate BTU scaling factor based on fuel type."""
        if self.fuel_type == FUEL_GAS and self.btu_sf == EXPORT_BTU_SF:
            self.btu_sf = EXPORT_BTU_SF_GAS  # 100 for therms

    def to_cse_string(self) -> str:
        """Convert to CSE EXPORT block string."""
        lines = [
            f'EXPORT   "{self.name}"  ',
            f'   exExportfile = "{self.exportfile}"',
            f'   exType = "{self.export_type}"',
            f'   exFreq = "{self.freq}"',
            f'   exMeter = "{self.meter}"',
            f'   exBtuSf = {self.btu_sf}',
            f'   exDayBeg = {self.day_beg}',
            f'   exDayEnd = {self.day_end}',
            '',  # Blank line after block
        ]
        return '\n'.join(lines)


# =============================================================================
# CSE TRANSFORMER
# =============================================================================

class CSETransformer:
    """
    Transforms CSE input files with zone-level metering.

    Example usage:
        >>> transformer = CSETransformer()
        >>> result = transformer.transform_file(cse_path)
        >>> if result.success:
        ...     with open(output_path, 'w') as f:
        ...         f.write(result.transformed_content)
    """

    # Regex patterns for finding insertion points
    METER_BLOCK_PATTERN = re.compile(r'^METER\s+"([^"]+)"', re.MULTILINE)
    EXPORT_BLOCK_PATTERN = re.compile(r'^EXPORT\s+"([^"]+)"', re.MULTILINE)
    GAIN_METER_PATTERN = re.compile(
        r'(gnMeter\s*=\s*)"([^"]+)"',
        re.MULTILINE
    )
    RSYS_METER_PATTERN = re.compile(
        r'(rsElecMtr\s*=\s*)"([^"]+)"',
        re.MULTILINE
    )
    # Gas fuel meter pattern for RSYS
    RSYS_FUEL_METER_PATTERN = re.compile(
        r'(rsFuelMtr\s*=\s*)"([^"]+)"',
        re.MULTILINE
    )

    def __init__(self):
        """Initialize the transformer."""
        self._model: Optional[CSEZoneInputModel] = None
        self._mapper = ZoneMeterMapper()
        self._original_content: str = ""
        self._transformed_content: str = ""

    def transform_file(
        self,
        filepath: Path,
        output_path: Optional[Path] = None,
    ) -> TransformResult:
        """
        Transform a CSE input file with zone-level metering.

        Args:
            filepath: Path to original CSE file
            output_path: Optional path to write transformed file

        Returns:
            TransformResult with transformed content and statistics
        """
        filepath = Path(filepath)

        result = TransformResult(
            success=False,
            original_file=str(filepath),
            transformed_content="",
        )

        try:
            # Read original file
            self._original_content = self._read_file(filepath)

            # Parse CSE input
            self._model = parse_cse_zone_input(filepath)
            if not self._model.zones:
                result.errors.append("No zones found in CSE file")
                return result

            # Map zones to meters
            self._mapper.map_zones(self._model.zones)
            result.zone_assignments = self._mapper.get_zone_assignments()
            result.meter_hierarchy = self._mapper.get_meter_hierarchy()

            # Perform transformation
            self._transformed_content = self._original_content

            # === ELECTRIC METERS ===
            # 1. Update GAIN gnMeter references
            gains_updated = self._update_gain_meters()
            result.gains_updated = gains_updated

            # 2. Update RSYS electric meter references
            rsys_updated = self._update_rsys_meters()
            result.rsys_updated = rsys_updated

            # 3. Inject new electric METER definitions
            new_meters = self._generate_meter_definitions()
            meters_added = self._inject_meter_definitions(new_meters)
            result.meters_added = meters_added

            # 4. Inject new electric EXPORT definitions
            new_exports = self._generate_export_definitions()
            exports_added = self._inject_export_definitions(new_exports)
            result.exports_added = exports_added

            # === GAS METERS ===
            # 5. Update RSYS fuel meter references
            rsys_fuel_updated = self._update_rsys_fuel_meters()
            result.rsys_fuel_updated = rsys_fuel_updated

            # 6. Inject new gas METER definitions
            gas_meters = self._generate_gas_meter_definitions()
            gas_meters_added = self._inject_meter_definitions(gas_meters, is_gas=True)
            result.gas_meters_added = gas_meters_added

            # 7. Inject new gas EXPORT definitions
            gas_exports = self._generate_gas_export_definitions()
            gas_exports_added = self._inject_export_definitions(gas_exports, is_gas=True)
            result.gas_exports_added = gas_exports_added

            result.transformed_content = self._transformed_content
            result.success = True

            # Write output if path provided
            if output_path:
                output_path = Path(output_path)
                output_path.parent.mkdir(parents=True, exist_ok=True)
                with open(output_path, 'w', encoding='utf-8') as f:
                    f.write(result.transformed_content)
                logger.info(f"Wrote transformed CSE to {output_path}")

            logger.info(
                f"Transformation complete: "
                f"{meters_added} elec meters, {gas_meters_added} gas meters, "
                f"{exports_added} elec exports, {gas_exports_added} gas exports, "
                f"{gains_updated} gains updated"
            )

        except Exception as e:
            result.errors.append(f"Transformation failed: {e}")
            logger.error(f"Error transforming {filepath}: {e}")

        return result

    def _read_file(self, filepath: Path) -> str:
        """Read file with encoding fallback."""
        encodings = ['utf-8', 'latin-1', 'cp1252']
        for encoding in encodings:
            try:
                with open(filepath, 'r', encoding=encoding) as f:
                    return f.read()
            except UnicodeDecodeError:
                continue

        # Last resort
        with open(filepath, 'rb') as f:
            return f.read().decode('utf-8', errors='replace')

    def _update_gain_meters(self) -> int:
        """
        Update GAIN gnMeter references to zone-specific meters.

        Returns:
            Number of gains updated
        """
        updated_count = 0
        assignments = self._mapper.get_zone_assignments()

        # Build map from original meter to zone info
        # Original meters are shared across zones, need to use gain name to match

        # For each zone, find its gains and update their meters
        for zone_name, zone in self._model.zones.items():
            assignment = assignments.get(zone_name)
            if not assignment:
                continue

            new_meter = assignment.zone_meter

            for gain in zone.gains:
                if gain.meter:
                    # Find and replace this specific gain's meter reference
                    # Pattern: gnMeter = "old_meter" within the gain block
                    old_meter = gain.meter

                    # Create pattern that matches within the specific gain block
                    # Look for GAIN "gain_name" ... gnMeter = "old_meter"
                    gain_block_pattern = re.compile(
                        rf'(GAIN\s+"{re.escape(gain.name)}".*?gnMeter\s*=\s*)"({re.escape(old_meter)})"',
                        re.DOTALL
                    )

                    new_content, count = gain_block_pattern.subn(
                        rf'\1"{new_meter}"',
                        self._transformed_content
                    )

                    if count > 0:
                        self._transformed_content = new_content
                        updated_count += count

        return updated_count

    def _update_rsys_meters(self) -> int:
        """
        Update RSYS rsElecMtr references to zone-specific meters.

        For RSYS, we need to determine which zone(s) the system serves
        and assign an appropriate meter.

        Returns:
            Number of RSYS updated
        """
        updated_count = 0

        # For now, we'll update RSYS to use the first zone they serve
        # A more sophisticated approach would create RSYS-specific meters
        for rsys_name, rsys in self._model.rsys_list.items():
            if not rsys.elec_meter:
                continue

            # Find which zone(s) this RSYS serves
            served_zones = self._find_rsys_served_zones(rsys.name)
            if not served_zones:
                continue

            # Use the first served zone's meter
            first_zone = served_zones[0]
            assignment = self._mapper.get_assignment(first_zone)
            if not assignment:
                continue

            new_meter = assignment.zone_meter
            old_meter = rsys.elec_meter

            # Find and replace the RSYS meter reference
            rsys_block_pattern = re.compile(
                rf'(RSYS\s+"{re.escape(rsys.name)}".*?rsElecMtr\s*=\s*)"({re.escape(old_meter)})"',
                re.DOTALL
            )

            new_content, count = rsys_block_pattern.subn(
                rf'\1"{new_meter}"',
                self._transformed_content
            )

            if count > 0:
                self._transformed_content = new_content
                updated_count += count

        return updated_count

    def _find_rsys_served_zones(self, rsys_name: str) -> List[str]:
        """Find zones served by an RSYS."""
        # Look for zones that reference this RSYS
        # In CSE, zones typically have a znRSYS property or similar
        served_zones = []

        # For now, use a simple heuristic based on naming
        # RSYS names often contain zone references
        rsys_lower = rsys_name.lower()

        for zone_name in self._model.zones:
            zone_lower = zone_name.lower()

            # Check if zone name is part of RSYS name
            if zone_lower.replace('-zn', '') in rsys_lower:
                served_zones.append(zone_name)

        return served_zones

    def _update_rsys_fuel_meters(self) -> int:
        """
        Update RSYS rsFuelMtr references to zone-specific gas meters.

        Similar to _update_rsys_meters but for gas fuel meters.

        Returns:
            Number of RSYS fuel meters updated
        """
        updated_count = 0

        # For now, we'll update RSYS fuel meters to use the first zone they serve
        for rsys_name, rsys in self._model.rsys_list.items():
            # Check if RSYS has a fuel meter (look in raw content)
            rsys_block_pattern = re.compile(
                rf'RSYS\s+"{re.escape(rsys.name)}".*?rsFuelMtr\s*=\s*"([^"]+)"',
                re.DOTALL
            )
            match = rsys_block_pattern.search(self._transformed_content)
            if not match:
                continue

            old_meter = match.group(1)

            # Find which zone(s) this RSYS serves
            served_zones = self._find_rsys_served_zones(rsys.name)
            if not served_zones:
                continue

            # Use the first served zone's gas meter
            first_zone = served_zones[0]
            assignment = self._mapper.get_assignment(first_zone)
            if not assignment or not assignment.has_gas:
                continue

            new_meter = assignment.gas_zone_meter
            if not new_meter:
                continue

            # Find and replace the RSYS fuel meter reference
            rsys_replace_pattern = re.compile(
                rf'(RSYS\s+"{re.escape(rsys.name)}".*?rsFuelMtr\s*=\s*)"({re.escape(old_meter)})"',
                re.DOTALL
            )

            new_content, count = rsys_replace_pattern.subn(
                rf'\1"{new_meter}"',
                self._transformed_content
            )

            if count > 0:
                self._transformed_content = new_content
                updated_count += count

        return updated_count

    def _generate_meter_definitions(self) -> List[CSEMeterDefinition]:
        """
        Generate new METER definitions for zone-level metering.

        Returns:
            List of CSEMeterDefinition objects
        """
        definitions = []
        hierarchy = self._mapper.get_meter_hierarchy()
        assignments = self._mapper.get_zone_assignments()

        # Get existing meter names to avoid duplicates
        existing_meters = set(self._model.meters.keys())

        # 1. Zone-level meters (leaf nodes)
        for zone_name, assignment in assignments.items():
            meter_name = assignment.zone_meter
            if meter_name not in existing_meters:
                definitions.append(CSEMeterDefinition(name=meter_name))

        # 2. Aggregation meters with submeters (category, dwelling type)
        for meter_name, children in hierarchy.submeter_map.items():
            if meter_name in existing_meters:
                continue
            if meter_name == hierarchy.building_meter:
                continue  # Don't recreate building meter

            # Get multipliers
            mults_map = hierarchy.multiplier_map.get(meter_name, {})
            mults = [mults_map.get(c, 1) for c in children]

            definitions.append(CSEMeterDefinition(
                name=meter_name,
                submeters=children,
                submeter_mults=mults,
            ))

        return definitions

    def _generate_gas_meter_definitions(self) -> List[CSEMeterDefinition]:
        """
        Generate new gas METER definitions for zone-level metering.

        Returns:
            List of CSEMeterDefinition objects for gas meters
        """
        definitions = []
        hierarchy = self._mapper.get_meter_hierarchy()
        assignments = self._mapper.get_zone_assignments()

        # Get existing meter names to avoid duplicates
        existing_meters = set(self._model.meters.keys())

        # 1. Zone-level gas meters (leaf nodes) - only for zones with gas
        for zone_name, assignment in assignments.items():
            if not assignment.has_gas:
                continue
            meter_name = assignment.gas_zone_meter
            if meter_name and meter_name not in existing_meters:
                definitions.append(CSEMeterDefinition(name=meter_name))

        # 2. Gas aggregation meters with submeters (category, dwelling type)
        for meter_name, children in hierarchy.gas_submeter_map.items():
            if meter_name in existing_meters:
                continue
            if meter_name == hierarchy.gas_building_meter:
                continue  # Don't recreate building meter

            # Get multipliers
            mults_map = hierarchy.gas_multiplier_map.get(meter_name, {})
            mults = [mults_map.get(c, 1) for c in children]

            definitions.append(CSEMeterDefinition(
                name=meter_name,
                submeters=children,
                submeter_mults=mults,
            ))

        return definitions

    def _inject_meter_definitions(
        self,
        meters: List[CSEMeterDefinition],
        is_gas: bool = False,
    ) -> int:
        """
        Inject new METER definitions into the CSE content.

        Inserts after the last existing METER block.

        Args:
            meters: List of meter definitions to inject
            is_gas: If True, label as gas meters in comment

        Returns:
            Number of meters injected
        """
        if not meters:
            return 0

        # Find last METER block position
        last_meter_pos = 0
        for match in self.METER_BLOCK_PATTERN.finditer(self._transformed_content):
            last_meter_pos = match.end()

        # Find the end of the last METER block (next blank line or new block)
        if last_meter_pos > 0:
            # Look for the next empty line or new block definition
            remaining = self._transformed_content[last_meter_pos:]

            # Find end of block (empty line followed by new block)
            block_end_pattern = re.compile(r'\n\s*\n', re.MULTILINE)
            match = block_end_pattern.search(remaining)
            if match:
                insert_pos = last_meter_pos + match.end()
            else:
                insert_pos = last_meter_pos
        else:
            # No existing meters, insert near top (after any #define blocks)
            define_end = 0
            for match in re.finditer(r'^#define.*$', self._transformed_content, re.MULTILINE):
                define_end = match.end()
            insert_pos = define_end + 1 if define_end > 0 else 0

        # Generate meter definition strings
        meter_strings = []
        fuel_label = "gas" if is_gas else "electric"
        meter_strings.append(f"\n// Zone-level {fuel_label} meters (auto-generated)")
        for meter in meters:
            meter_strings.append(meter.to_cse_string())

        injection = '\n'.join(meter_strings)

        # Insert into content
        self._transformed_content = (
            self._transformed_content[:insert_pos] +
            injection +
            self._transformed_content[insert_pos:]
        )

        return len(meters)

    def _generate_export_definitions(self) -> List[CSEExportDefinition]:
        """
        Generate new EXPORT definitions for zone-level meters.

        Returns:
            List of CSEExportDefinition objects
        """
        definitions = []
        assignments = self._mapper.get_zone_assignments()

        # Get existing export meter names to avoid duplicates
        existing_export_meters = {exp.meter for exp in self._model.exports.values()}

        # Create exports for zone-level meters
        for zone_name, assignment in assignments.items():
            meter_name = assignment.zone_meter
            if meter_name in existing_export_meters:
                continue

            # Generate export name from meter name
            export_name = f"Export_{meter_name.replace('MtrElec_', '')}"

            definitions.append(CSEExportDefinition(
                name=export_name,
                meter=meter_name,
                fuel_type=FUEL_ELECTRIC,
            ))

        return definitions

    def _generate_gas_export_definitions(self) -> List[CSEExportDefinition]:
        """
        Generate new EXPORT definitions for zone-level gas meters.

        Returns:
            List of CSEExportDefinition objects for gas meters
        """
        definitions = []
        assignments = self._mapper.get_zone_assignments()

        # Get existing export meter names to avoid duplicates
        existing_export_meters = {exp.meter for exp in self._model.exports.values()}

        # Create exports for zone-level gas meters
        for zone_name, assignment in assignments.items():
            if not assignment.has_gas:
                continue

            meter_name = assignment.gas_zone_meter
            if not meter_name or meter_name in existing_export_meters:
                continue

            # Generate export name from meter name
            export_name = f"Export_{meter_name.replace('MtrGas_', 'Gas_')}"

            definitions.append(CSEExportDefinition(
                name=export_name,
                meter=meter_name,
                fuel_type=FUEL_GAS,
            ))

        return definitions

    def _inject_export_definitions(
        self,
        exports: List[CSEExportDefinition],
        is_gas: bool = False,
    ) -> int:
        """
        Inject new EXPORT definitions into the CSE content.

        Inserts before the RUN statement to avoid interfering with
        existing EXPORT blocks that may have EXPORTCOL children.

        Args:
            exports: List of export definitions to inject
            is_gas: If True, label as gas exports in comment

        Returns:
            Number of exports injected
        """
        if not exports:
            return 0

        # Find the RUN statement - insert before it
        # This ensures we're after ALL existing content including EXPORTCOL children
        run_pattern = re.compile(r'^\s*RUN\s*$', re.MULTILINE)
        run_match = run_pattern.search(self._transformed_content)

        if run_match:
            insert_pos = run_match.start()
        else:
            # No RUN statement found, insert at end (before $EOF if present)
            eof_pattern = re.compile(r'^\s*\$EOF\s*$', re.MULTILINE)
            eof_match = eof_pattern.search(self._transformed_content)
            if eof_match:
                insert_pos = eof_match.start()
            else:
                insert_pos = len(self._transformed_content)

        # Generate export definition strings
        export_strings = []
        fuel_label = "gas" if is_gas else "electric"
        export_strings.append(f"\n// Zone-level {fuel_label} meter exports (auto-generated)")
        for export in exports:
            export_strings.append(export.to_cse_string())
        export_strings.append("")  # Blank line before RUN

        injection = '\n'.join(export_strings)

        # Insert into content
        self._transformed_content = (
            self._transformed_content[:insert_pos] +
            injection +
            self._transformed_content[insert_pos:]
        )

        return len(exports)


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def transform_cse_file(
    input_path: Path,
    output_path: Optional[Path] = None,
) -> TransformResult:
    """
    Transform a CSE input file with zone-level metering.

    Args:
        input_path: Path to original CSE file
        output_path: Optional path to write transformed file

    Returns:
        TransformResult with transformed content and statistics
    """
    transformer = CSETransformer()
    return transformer.transform_file(input_path, output_path)


def format_transform_summary(result: TransformResult) -> str:
    """
    Format transformation result as summary text.

    Args:
        result: TransformResult from transformation

    Returns:
        Formatted summary string
    """
    lines = [
        "=" * 70,
        "CSE TRANSFORMATION SUMMARY",
        "=" * 70,
        "",
        f"Input File: {result.original_file}",
        f"Success: {result.success}",
        "",
        "Electric Metering:",
        f"  Meters Added: {result.meters_added}",
        f"  Exports Added: {result.exports_added}",
        f"  GAINs Updated: {result.gains_updated}",
        f"  RSYS Updated: {result.rsys_updated}",
        "",
        "Gas Metering:",
        f"  Meters Added: {result.gas_meters_added}",
        f"  Exports Added: {result.gas_exports_added}",
        f"  RSYS Fuel Updated: {result.rsys_fuel_updated}",
    ]

    if result.zone_assignments:
        lines.extend([
            "",
            f"Zone Assignments: {len(result.zone_assignments)}",
        ])

    if result.errors:
        lines.extend([
            "",
            "Errors:",
        ])
        for err in result.errors:
            lines.append(f"  - {err}")

    if result.warnings:
        lines.extend([
            "",
            "Warnings:",
        ])
        for warn in result.warnings:
            lines.append(f"  - {warn}")

    lines.append("=" * 70)

    return "\n".join(lines)
