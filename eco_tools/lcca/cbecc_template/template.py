"""
CBECC Template Module.

Injects site load data into CBECC model files.

This module supports injecting:
- Elevator counts and power (ElevCnt, ElevPwr)
- Escalator counts and power (EscalCnt, EscalPwr)
- Parking garage exhaust (PrkgGarExhFlow, PrkgGarExhFanPwr, PrkgGarExhCtrlMthd)

Two implementation modes:
1. Direct text manipulation (current) - simple, works with .cibd22/.cibd25
2. InternalRepresentation (future) - robust, uses import/export pipeline

Part of the CBECC modification tools library.
"""

from __future__ import annotations
import re
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field


@dataclass
class InjectionResult:
    """Result of a template injection operation."""
    success: bool
    zone_name: str
    property_name: str
    old_value: Optional[str] = None
    new_value: Optional[str] = None
    message: str = ""


class CbeccTemplate:
    """
    CBECC model template for site load injection.

    Loads a CBECC model file and provides methods to inject
    elevator, escalator, and parking exhaust properties into
    specific zones.

    Example:
        >>> template = CbeccTemplate("base_model.cibd22")
        >>> template.set_elevator_count("Lobby_L01", 4, power_kw=15.0)
        >>> template.set_parking_exhaust("Parking_L01", cfm=50000, fan_power=0.25)
        >>> template.write("updated_model.cibd25")

    Note: Currently works with text-based CIBD files (.cibd22, .cibd25).
    XML format (.cibd22x, .cibd25x) support planned for future.
    """

    def __init__(self, file_path: str | Path):
        """
        Load a CBECC model file.

        Args:
            file_path: Path to .cibd22, .cibd25 file
        """
        self.file_path = Path(file_path)
        self.content: str = ""
        self.injections: List[InjectionResult] = []
        self._modified = False

        self._load()

    def _load(self):
        """Load file content."""
        if not self.file_path.exists():
            raise FileNotFoundError(f"CBECC file not found: {self.file_path}")

        suffix = self.file_path.suffix.lower()
        if suffix in ['.cibd22x', '.cibd25x']:
            raise NotImplementedError(
                f"XML format {suffix} not yet supported. "
                "Use text format (.cibd22, .cibd25) or convert first."
            )

        with open(self.file_path, 'r', encoding='utf-8', errors='ignore') as f:
            self.content = f.read()

    def _find_zone_block(self, zone_name: str) -> Optional[tuple]:
        """
        Find the start and end positions of a zone block.

        Args:
            zone_name: Name of the zone to find

        Returns:
            Tuple of (start_pos, end_pos) or None if not found
        """
        # Pattern to find zone declaration
        # Handles both ResOtherZn and Spc elements
        patterns = [
            rf'(ResOtherZn\s+"{re.escape(zone_name)}")',
            rf'(Spc\s+"{re.escape(zone_name)}")',
        ]

        for pattern in patterns:
            match = re.search(pattern, self.content)
            if match:
                start = match.start()
                # Find end of zone block (next element at same indentation or end of file)
                # Zone blocks end with ".." or next element at same level
                block_end = self.content.find('\n..', start)
                if block_end == -1:
                    block_end = len(self.content)
                else:
                    block_end += 3  # Include the ".."

                return (start, block_end)

        return None

    def _set_property(
        self,
        zone_name: str,
        property_name: str,
        value: Any,
        zone_types: List[str] = None
    ) -> InjectionResult:
        """
        Set a property on a zone.

        Args:
            zone_name: Name of the zone
            property_name: CBECC property name (e.g., "ElevCnt")
            value: Value to set
            zone_types: List of zone types to search ("ResOtherZn", "Spc")

        Returns:
            InjectionResult with success status
        """
        if zone_types is None:
            zone_types = ["ResOtherZn", "Spc"]

        # Find the zone
        zone_block = self._find_zone_block(zone_name)
        if zone_block is None:
            return InjectionResult(
                success=False,
                zone_name=zone_name,
                property_name=property_name,
                message=f"Zone '{zone_name}' not found in model"
            )

        start, end = zone_block
        block = self.content[start:end]

        # Check if property already exists
        prop_pattern = rf'(\s+{property_name}\s*=\s*)([^\n]+)'
        prop_match = re.search(prop_pattern, block)

        if prop_match:
            # Update existing property
            old_value = prop_match.group(2).strip()
            new_block = block[:prop_match.start(2)] + str(value) + block[prop_match.end(2):]
            self.content = self.content[:start] + new_block + self.content[end:]
            self._modified = True

            result = InjectionResult(
                success=True,
                zone_name=zone_name,
                property_name=property_name,
                old_value=old_value,
                new_value=str(value),
                message=f"Updated {property_name}: {old_value} → {value}"
            )
        else:
            # Add new property after zone declaration line
            # Find end of first line (zone declaration)
            first_newline = block.find('\n')
            if first_newline == -1:
                first_newline = len(block)

            # Insert new property with proper indentation
            new_prop = f"\n   {property_name} = {value}"
            new_block = block[:first_newline] + new_prop + block[first_newline:]
            self.content = self.content[:start] + new_block + self.content[end:]
            self._modified = True

            result = InjectionResult(
                success=True,
                zone_name=zone_name,
                property_name=property_name,
                old_value=None,
                new_value=str(value),
                message=f"Added {property_name} = {value}"
            )

        self.injections.append(result)
        return result

    def set_elevator_count(
        self,
        zone_name: str,
        count: int,
        power_kw: Optional[float] = None,
        lost_fraction: Optional[float] = None
    ) -> List[InjectionResult]:
        """
        Set elevator count on a zone.

        Args:
            zone_name: Zone to assign elevators to
            count: Number of elevators
            power_kw: Power per elevator in kW (optional, uses CEC default if not set)
            lost_fraction: Fraction of energy as heat to space (optional)

        Returns:
            List of InjectionResult for each property set
        """
        results = []

        # Set elevator count
        result = self._set_property(zone_name, "ElevCnt", count)
        results.append(result)

        # Set power if specified
        if power_kw is not None:
            result = self._set_property(zone_name, "ElevPwr", power_kw)
            results.append(result)

        # Set lost fraction if specified
        if lost_fraction is not None:
            result = self._set_property(zone_name, "ElevLostFrac", lost_fraction)
            results.append(result)

        return results

    def set_escalator_count(
        self,
        zone_name: str,
        count: int,
        power_kw: Optional[float] = None,
        lost_fraction: Optional[float] = None
    ) -> List[InjectionResult]:
        """
        Set escalator count on a zone.

        Args:
            zone_name: Zone to assign escalators to
            count: Number of escalators
            power_kw: Power per escalator in kW (optional)
            lost_fraction: Fraction of energy as heat to space (optional)

        Returns:
            List of InjectionResult for each property set
        """
        results = []

        result = self._set_property(zone_name, "EscalCnt", count, zone_types=["Spc"])
        results.append(result)

        if power_kw is not None:
            result = self._set_property(zone_name, "EscalPwr", power_kw, zone_types=["Spc"])
            results.append(result)

        if lost_fraction is not None:
            result = self._set_property(zone_name, "EscalLostFrac", lost_fraction, zone_types=["Spc"])
            results.append(result)

        return results

    def set_parking_exhaust(
        self,
        zone_name: str,
        cfm: float,
        fan_power_w_cfm: float = 0.35,
        control_method: str = "NoCOControl"
    ) -> List[InjectionResult]:
        """
        Set parking garage exhaust properties on a zone.

        Args:
            zone_name: Parking zone name
            cfm: Exhaust airflow in CFM
            fan_power_w_cfm: Fan power in W/CFM (default 0.35)
            control_method: Control method ("NoCOControl" or "COControl")

        Returns:
            List of InjectionResult for each property set
        """
        results = []

        result = self._set_property(zone_name, "PrkgGarExhFlow", cfm)
        results.append(result)

        result = self._set_property(zone_name, "PrkgGarExhFanPwr", fan_power_w_cfm)
        results.append(result)

        result = self._set_property(zone_name, "PrkgGarExhCtrlMthd", f'"{control_method}"')
        results.append(result)

        return results

    def apply_intake(self, intake: "SiteLoadIntake") -> List[InjectionResult]:
        """
        Apply all injections from an intake form.

        Args:
            intake: SiteLoadIntake object with injection data

        Returns:
            List of all InjectionResult objects
        """
        from .intake_loader import SiteLoadIntake

        results = []
        injections = intake.get_cbecc_injections()

        # Elevators
        if "elevators" in injections:
            elev = injections["elevators"]
            if elev.get("zone") and elev.get("count"):
                elev_results = self.set_elevator_count(
                    zone_name=elev["zone"],
                    count=elev["count"],
                    power_kw=elev.get("power_kw"),
                )
                results.extend(elev_results)

        # Escalators
        if "escalators" in injections:
            escal = injections["escalators"]
            if escal.get("zone") and escal.get("count"):
                escal_results = self.set_escalator_count(
                    zone_name=escal["zone"],
                    count=escal["count"],
                    power_kw=escal.get("power_kw"),
                )
                results.extend(escal_results)

        # Parking exhaust
        if "parking_exhaust" in injections:
            pkg = injections["parking_exhaust"]
            if pkg.get("zone") and pkg.get("exhaust_cfm"):
                control = "COControl" if pkg.get("co_control") else "NoCOControl"
                pkg_results = self.set_parking_exhaust(
                    zone_name=pkg["zone"],
                    cfm=pkg["exhaust_cfm"],
                    fan_power_w_cfm=pkg.get("fan_power_w_cfm", 0.35),
                    control_method=control,
                )
                results.extend(pkg_results)

        return results

    def write(self, output_path: str | Path):
        """
        Write modified model to file.

        Args:
            output_path: Path for output file
        """
        output_path = Path(output_path)
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(self.content)

    def get_injection_summary(self) -> Dict[str, Any]:
        """
        Get summary of all injections performed.

        Returns:
            Dictionary with injection statistics and details
        """
        successful = [r for r in self.injections if r.success]
        failed = [r for r in self.injections if not r.success]

        return {
            "total_injections": len(self.injections),
            "successful": len(successful),
            "failed": len(failed),
            "modified": self._modified,
            "details": [
                {
                    "zone": r.zone_name,
                    "property": r.property_name,
                    "success": r.success,
                    "old_value": r.old_value,
                    "new_value": r.new_value,
                    "message": r.message,
                }
                for r in self.injections
            ]
        }

    def list_zones(self, zone_type: Optional[str] = None) -> List[str]:
        """
        List all zones in the model.

        Args:
            zone_type: Filter by type ("ResOtherZn", "Spc", or None for all)

        Returns:
            List of zone names
        """
        zones = []

        if zone_type is None or zone_type == "ResOtherZn":
            pattern = r'ResOtherZn\s+"([^"]+)"'
            zones.extend(re.findall(pattern, self.content))

        if zone_type is None or zone_type == "Spc":
            pattern = r'Spc\s+"([^"]+)"'
            zones.extend(re.findall(pattern, self.content))

        return zones

    def get_zone_properties(self, zone_name: str) -> Dict[str, str]:
        """
        Get all properties of a zone.

        Args:
            zone_name: Name of the zone

        Returns:
            Dictionary of property name → value
        """
        zone_block = self._find_zone_block(zone_name)
        if zone_block is None:
            return {}

        start, end = zone_block
        block = self.content[start:end]

        # Parse properties
        props = {}
        pattern = r'\s+(\w+)\s*=\s*([^\n]+)'
        for match in re.finditer(pattern, block):
            prop_name = match.group(1)
            prop_value = match.group(2).strip()
            props[prop_name] = prop_value

        return props
