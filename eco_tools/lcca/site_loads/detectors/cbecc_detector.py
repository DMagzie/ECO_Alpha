"""
CBECC Modeled Load Detector.

Examines CBECC input files (.cibd22, .cibd25, .cibd22x, .cibd25x) to detect
which loads are already modeled in the simulation vs which need to be
calculated as site loads.

"Sometimes Modeled" Loads in CBECC:
-----------------------------------
1. Parking Garage Exhaust Fans
   - Properties: PrkgGarExhFlow (CFM), PrkgGarExhFanPwr (W/CFM)
   - When modeled: Values > 0 in ResOtherZn with SpcFunc = "Parking Garage Area"
   - Typical: NOT modeled for compliance-only (defaults to 0)

2. Central Ventilation Systems
   - Properties: IAQOption, CentralVentSysRef, CentralExhaustCFM
   - When modeled: IAQOption = "Central Supply / Central Exhaust"
   - This is for corridors/lobbies, not individual units

3. Common Area Lighting
   - Always modeled in ResOtherZn zones
   - Interior lighting = SpcFunc LPD * Area * hours
   - No need to calculate separately

4. Elevator Energy (CAN BE MODELED)
   - Properties: ElevCnt (count), ElevPwr (kW), ElevLostFrac (heat to space)
   - Found on: Spc (commercial) and ResOtherZn (residential) elements
   - Rule files: Space-ElevatorEscalator.rule, ResOtherZn-ElevatorEscalator.rule
   - CBECC uses CEC standard process loads which may not reflect actual equipment

5. Escalator Energy (CAN BE MODELED)
   - Properties: EscalCnt (count), EscalPwr (kW), EscalLostFrac (heat to space)
   - Found on: Spc elements (commercial spaces)
   - Rule files: Space-ElevatorEscalator.rule

6. Pool/Spa Energy
   - NEVER modeled in CBECC
   - Always needs to be calculated as site load

7. EV Charging (LIMITED in CBECC)
   - CBECC 2025 has CALGreen flag but no detailed EV load modeling
   - 2025 CALGreen requires: 1 Level 2 receptacle per dwelling unit + 25% common chargers
   - Always needs to be calculated as site load for accurate LCCA
"""

from __future__ import annotations
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Dict, Optional, Any
from enum import Enum


class LoadStatus(Enum):
    """Status of a load type in the simulation model."""
    MODELED = "modeled"           # Load is fully modeled
    PARTIALLY_MODELED = "partial" # Load is partially modeled
    NOT_MODELED = "not_modeled"   # Load is not modeled
    NOT_APPLICABLE = "n/a"        # Load type doesn't apply to this building


@dataclass
class LoadDetectionResult:
    """
    Detection result for a single load type.

    Attributes:
        load_type: Type of load (e.g., "parking_garage_exhaust")
        status: Whether the load is modeled
        confidence: Confidence level (0-1) in the detection
        details: Dict with detection specifics
        recommendation: Whether to calculate this as a site load
        notes: Human-readable notes about the detection
    """
    load_type: str
    status: LoadStatus
    confidence: float = 1.0
    details: Dict[str, Any] = field(default_factory=dict)
    recommendation: str = ""
    notes: str = ""

    @property
    def should_calculate_as_site_load(self) -> bool:
        """True if this load should be calculated as a site load."""
        return self.status in [LoadStatus.NOT_MODELED, LoadStatus.NOT_APPLICABLE]

    @property
    def is_modeled(self) -> bool:
        """True if this load is modeled in simulation."""
        return self.status in [LoadStatus.MODELED, LoadStatus.PARTIALLY_MODELED]


@dataclass
class ModeledLoadReport:
    """
    Complete report of modeled vs site loads for a building.

    This report helps users understand what's already in the simulation
    and what needs to be calculated as site loads.
    """
    file_path: str
    building_type: str = "Unknown"
    detections: List[LoadDetectionResult] = field(default_factory=list)

    # Summary counts
    modeled_load_count: int = 0
    site_load_count: int = 0

    def add_detection(self, result: LoadDetectionResult):
        """Add a detection result to the report."""
        self.detections.append(result)
        if result.is_modeled:
            self.modeled_load_count += 1
        elif result.should_calculate_as_site_load:
            self.site_load_count += 1

    def get_detection(self, load_type: str) -> Optional[LoadDetectionResult]:
        """Get detection result for a specific load type."""
        for det in self.detections:
            if det.load_type == load_type:
                return det
        return None

    def get_site_load_recommendations(self) -> List[str]:
        """Get list of load types that should be calculated as site loads."""
        return [d.load_type for d in self.detections if d.should_calculate_as_site_load]

    def get_modeled_loads(self) -> List[str]:
        """Get list of load types that are modeled in simulation."""
        return [d.load_type for d in self.detections if d.is_modeled]

    def to_dict(self) -> Dict[str, Any]:
        """Convert report to dictionary format."""
        return {
            "file_path": self.file_path,
            "building_type": self.building_type,
            "modeled_loads": self.get_modeled_loads(),
            "site_load_recommendations": self.get_site_load_recommendations(),
            "detections": [
                {
                    "load_type": d.load_type,
                    "status": d.status.value,
                    "confidence": d.confidence,
                    "recommendation": d.recommendation,
                    "notes": d.notes,
                    "details": d.details,
                }
                for d in self.detections
            ],
        }


class CbeccModeledLoadDetector:
    """
    Detects which loads are modeled in a CBECC simulation file.

    Examines .cibd22, .cibd25, .cibd22x, .cibd25x files to identify:
    1. Which "sometimes modeled" loads are actually included
    2. Which loads need to be calculated as site loads

    Example:
        >>> detector = CbeccModeledLoadDetector()
        >>> report = detector.analyze("building.cibd22x")
        >>> print(report.get_site_load_recommendations())
        ['parking_garage_exhaust', 'elevator', 'pool_pump', 'ev_charger']
    """

    # Load types that CBECC can model but often doesn't
    # These need detection logic to determine if they're in the model
    SOMETIMES_MODELED = [
        "parking_garage_exhaust",
        "central_ventilation",
        "elevator",      # ElevCnt, ElevPwr on Spc/ResOtherZn
        "escalator",     # EscalCnt, EscalPwr on Spc
    ]

    # Load types that CBECC never models (always calculate as site load)
    NEVER_MODELED = [
        "pool_pump",
        "pool_heater",
        "spa",
        "ev_charger",    # Limited CALGreen flag in 2025 but no energy modeling
        "it_telecom",
        "water_pumps",
        "trash_compactor",
        "site_lighting",
    ]

    # Load types that CBECC always models for ResOtherZn
    ALWAYS_MODELED = [
        "interior_lighting",  # Part of zone loads
        "hvac",              # If zone is conditioned
    ]

    def analyze(self, file_path: str | Path) -> ModeledLoadReport:
        """
        Analyze a CBECC file to detect modeled loads.

        Args:
            file_path: Path to .cibd22, .cibd25, .cibd22x, or .cibd25x file

        Returns:
            ModeledLoadReport with detection results
        """
        file_path = Path(file_path)
        report = ModeledLoadReport(file_path=str(file_path))

        # Read and parse file
        content = self._read_file(file_path)
        is_xml = file_path.suffix.lower() in ['.cibd22x', '.cibd25x']

        # Detect building type
        report.building_type = self._detect_building_type(content, is_xml)

        # Check "sometimes modeled" loads
        report.add_detection(self._detect_parking_garage_exhaust(content, is_xml))
        report.add_detection(self._detect_central_ventilation(content, is_xml))
        report.add_detection(self._detect_elevator(content, is_xml))
        report.add_detection(self._detect_escalator(content, is_xml))

        # Add "never modeled" loads
        for load_type in self.NEVER_MODELED:
            report.add_detection(self._create_never_modeled_detection(load_type))

        # Add "always modeled" loads
        for load_type in self.ALWAYS_MODELED:
            report.add_detection(self._create_always_modeled_detection(load_type, content, is_xml))

        return report

    def _read_file(self, file_path: Path) -> str:
        """Read file content."""
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            return f.read()

    def _detect_building_type(self, content: str, is_xml: bool) -> str:
        """Detect building type from file content."""
        if is_xml:
            if '<ResZn>' in content or '<DwellUnit>' in content:
                return "Residential"
            elif '<ThrmlZn>' in content and '<ResZn>' not in content:
                return "Nonresidential"
            elif '<ThrmlZn>' in content and '<ResZn>' in content:
                return "Mixed-Use"
        else:
            if 'DwellUnit ' in content or 'ResZn ' in content:
                return "Residential"
            elif 'ThrmlZn ' in content and 'ResZn ' not in content:
                return "Nonresidential"
            elif 'ThrmlZn ' in content and 'ResZn ' in content:
                return "Mixed-Use"
        return "Unknown"

    def _detect_parking_garage_exhaust(self, content: str, is_xml: bool) -> LoadDetectionResult:
        """
        Detect if parking garage exhaust fans are modeled.

        Looks for ResOtherZn with:
        - SpcFunc = "Parking Garage Area (Parking Zone and Ramps)"
        - PrkgGarExhFlow > 0
        - PrkgGarExhFanPwr > 0
        """
        result = LoadDetectionResult(
            load_type="parking_garage_exhaust",
            status=LoadStatus.NOT_MODELED,
            details={},
        )

        # Check for parking garage zones
        has_parking_zone = False
        parking_exhaust_cfm = 0.0
        parking_exhaust_power = 0.0
        parking_area_sqft = 0.0

        if is_xml:
            # XML format
            try:
                root = ET.fromstring(content)
                for zone in root.iter():
                    if zone.tag == 'ResOtherZn' or zone.tag.endswith('}ResOtherZn'):
                        spc_func = zone.find('SpcFunc')
                        if spc_func is not None and 'parking' in spc_func.text.lower():
                            has_parking_zone = True
                            area = zone.find('Area')
                            if area is not None:
                                parking_area_sqft += float(area.text or 0)

                            exh_flow = zone.find('PrkgGarExhFlow')
                            if exh_flow is not None:
                                parking_exhaust_cfm += float(exh_flow.text or 0)

                            exh_power = zone.find('PrkgGarExhFanPwr')
                            if exh_power is not None:
                                parking_exhaust_power = float(exh_power.text or 0)
            except ET.ParseError:
                pass
        else:
            # Text format
            # Look for parking zone patterns
            parking_pattern = r'ResOtherZn\s+"[^"]*[Pp]arking[^"]*"'
            if re.search(parking_pattern, content):
                has_parking_zone = True

            # Look for exhaust properties
            exh_flow_match = re.search(r'PrkgGarExhFlow\s*=\s*([\d.]+)', content)
            if exh_flow_match:
                parking_exhaust_cfm = float(exh_flow_match.group(1))

            exh_power_match = re.search(r'PrkgGarExhFanPwr\s*=\s*([\d.]+)', content)
            if exh_power_match:
                parking_exhaust_power = float(exh_power_match.group(1))

        # Set result based on findings
        result.details = {
            "has_parking_zone": has_parking_zone,
            "parking_area_sqft": parking_area_sqft,
            "exhaust_cfm": parking_exhaust_cfm,
            "exhaust_power_w_per_cfm": parking_exhaust_power,
        }

        if not has_parking_zone:
            result.status = LoadStatus.NOT_APPLICABLE
            result.recommendation = "No parking garage zones found in model"
            result.notes = "Building does not have modeled parking garage zones"
        elif parking_exhaust_cfm > 0 and parking_exhaust_power > 0:
            result.status = LoadStatus.MODELED
            result.recommendation = "Do NOT calculate parking exhaust as site load"
            result.notes = f"Parking exhaust is modeled: {parking_exhaust_cfm:.0f} CFM at {parking_exhaust_power:.2f} W/CFM"
        elif parking_exhaust_cfm > 0 or parking_exhaust_power > 0:
            result.status = LoadStatus.PARTIALLY_MODELED
            result.confidence = 0.7
            result.recommendation = "Review parking exhaust - partially modeled"
            result.notes = "Parking exhaust properties are partially specified"
        else:
            result.status = LoadStatus.NOT_MODELED
            result.recommendation = "Calculate parking exhaust as site load"
            result.notes = f"Parking zone(s) exist ({parking_area_sqft:.0f} SF) but exhaust fans not modeled"

        return result

    def _detect_central_ventilation(self, content: str, is_xml: bool) -> LoadDetectionResult:
        """
        Detect if central ventilation is modeled for common areas.

        Looks for IAQOption = "Central Supply / Central Exhaust"
        """
        result = LoadDetectionResult(
            load_type="central_ventilation",
            status=LoadStatus.NOT_MODELED,
            details={},
        )

        central_exhaust_zones = []
        total_exhaust_cfm = 0.0

        if is_xml:
            try:
                root = ET.fromstring(content)
                for zone in root.iter():
                    if zone.tag == 'ResOtherZn' or zone.tag.endswith('}ResOtherZn'):
                        iaq = zone.find('IAQOption')
                        if iaq is not None and 'central' in iaq.text.lower():
                            name = zone.find('Name')
                            zone_name = name.text if name is not None else "Unknown"
                            central_exhaust_zones.append(zone_name)

                            exh_cfm = zone.find('CentralExhaustCFM')
                            if exh_cfm is not None:
                                total_exhaust_cfm += float(exh_cfm.text or 0)
            except ET.ParseError:
                pass
        else:
            # Text format
            matches = re.findall(r'IAQOption\s*=\s*"([^"]*[Cc]entral[^"]*)"', content)
            if matches:
                central_exhaust_zones = [f"Zone with {m}" for m in matches]

            cfm_matches = re.findall(r'CentralExhaustCFM\s*=\s*([\d.]+)', content)
            total_exhaust_cfm = sum(float(m) for m in cfm_matches)

        result.details = {
            "zones_with_central_ventilation": len(central_exhaust_zones),
            "zone_names": central_exhaust_zones[:10],  # First 10
            "total_exhaust_cfm": total_exhaust_cfm,
        }

        if central_exhaust_zones:
            result.status = LoadStatus.MODELED
            result.recommendation = "Central ventilation is modeled - included in HVAC fan energy"
            result.notes = f"{len(central_exhaust_zones)} zone(s) have central ventilation ({total_exhaust_cfm:.0f} CFM total)"
        else:
            result.status = LoadStatus.NOT_MODELED
            result.recommendation = "No central ventilation detected"
            result.notes = "Common areas may use individual exhaust or natural ventilation"

        return result

    def _detect_elevator(self, content: str, is_xml: bool) -> LoadDetectionResult:
        """
        Detect if elevators are modeled in CBECC.

        CBECC has elevator properties at the space/zone level:
        - ElevCnt: Number of elevators
        - ElevPwr: Elevator power (kW)
        - ElevLostFrac: Fraction of energy as heat to space

        These can appear on Spc (commercial) or ResOtherZn (residential) elements.
        """
        result = LoadDetectionResult(
            load_type="elevator",
            status=LoadStatus.NOT_MODELED,
            details={},
        )

        # NOTE: ElevCnt is often distributed across multiple zones for heat gain
        # purposes, but represents the SAME elevators. We use MAX instead of SUM.
        elevator_count = 0
        elevator_power = 0.0
        zones_with_elevators = []
        all_elev_counts = []

        if is_xml:
            try:
                root = ET.fromstring(content)
                # Check both Spc and ResOtherZn elements
                for zone in root.iter():
                    if zone.tag in ['Spc', 'ResOtherZn'] or \
                       zone.tag.endswith('}Spc') or zone.tag.endswith('}ResOtherZn'):
                        elev_cnt = zone.find('ElevCnt')
                        elev_pwr = zone.find('ElevPwr')
                        if elev_cnt is not None and float(elev_cnt.text or 0) > 0:
                            name = zone.find('Name')
                            zone_name = name.text if name is not None else "Unknown"
                            count = int(float(elev_cnt.text))
                            all_elev_counts.append(count)
                            zones_with_elevators.append(zone_name)
                            if elev_pwr is not None and elevator_power == 0:
                                # Take power from first zone that has it
                                elevator_power = float(elev_pwr.text or 0) * count
            except ET.ParseError:
                pass
        else:
            # Text format - look for ElevCnt properties
            elev_matches = re.findall(r'ElevCnt\s*=\s*(\d+)', content)
            all_elev_counts = [int(m) for m in elev_matches]

            pwr_matches = re.findall(r'ElevPwr\s*=\s*([\d.]+)', content)
            if pwr_matches:
                elevator_power = float(pwr_matches[0])  # Take first value

        # Use MAX count - same elevators may be assigned to multiple zones
        elevator_count = max(all_elev_counts) if all_elev_counts else 0

        result.details = {
            "elevator_count": elevator_count,
            "total_elevator_power_kw": elevator_power,
            "zones_with_elevators": zones_with_elevators[:10] if zones_with_elevators else [],
            "zones_served": len(zones_with_elevators) if zones_with_elevators else len(all_elev_counts),
        }

        if elevator_count > 0:
            result.status = LoadStatus.MODELED
            result.confidence = 1.0
            result.recommendation = "Elevators are modeled using CEC standard process loads"
            result.notes = (
                f"{elevator_count} elevator(s) modeled ({elevator_power:.1f} kW total). "
                f"Note: CEC values may differ from actual equipment - consider LCCA override."
            )
        else:
            result.status = LoadStatus.NOT_MODELED
            result.recommendation = "Calculate elevator energy as site load if building has elevators"
            result.notes = "No ElevCnt > 0 found in model - elevator energy not included"

        return result

    def _detect_escalator(self, content: str, is_xml: bool) -> LoadDetectionResult:
        """
        Detect if escalators are modeled in CBECC.

        CBECC has escalator properties at the space level:
        - EscalCnt: Number of escalators
        - EscalPwr: Escalator power (kW)
        - EscalLostFrac: Fraction of energy as heat to space

        These appear on Spc (commercial) elements only.
        """
        result = LoadDetectionResult(
            load_type="escalator",
            status=LoadStatus.NOT_MODELED,
            details={},
        )

        # NOTE: Similar to elevators, EscalCnt may be distributed across zones
        escalator_count = 0
        escalator_power = 0.0
        zones_with_escalators = []
        all_escal_counts = []

        if is_xml:
            try:
                root = ET.fromstring(content)
                for zone in root.iter():
                    if zone.tag == 'Spc' or zone.tag.endswith('}Spc'):
                        escal_cnt = zone.find('EscalCnt')
                        escal_pwr = zone.find('EscalPwr')
                        if escal_cnt is not None and float(escal_cnt.text or 0) > 0:
                            name = zone.find('Name')
                            zone_name = name.text if name is not None else "Unknown"
                            count = int(float(escal_cnt.text))
                            all_escal_counts.append(count)
                            zones_with_escalators.append(zone_name)
                            if escal_pwr is not None and escalator_power == 0:
                                escalator_power = float(escal_pwr.text or 0) * count
            except ET.ParseError:
                pass
        else:
            # Text format
            escal_matches = re.findall(r'EscalCnt\s*=\s*(\d+)', content)
            all_escal_counts = [int(m) for m in escal_matches]

            pwr_matches = re.findall(r'EscalPwr\s*=\s*([\d.]+)', content)
            if pwr_matches:
                escalator_power = float(pwr_matches[0])

        # Use MAX count - same escalators may be assigned to multiple zones
        escalator_count = max(all_escal_counts) if all_escal_counts else 0

        result.details = {
            "escalator_count": escalator_count,
            "total_escalator_power_kw": escalator_power,
            "zones_with_escalators": zones_with_escalators[:10] if zones_with_escalators else [],
            "zones_served": len(zones_with_escalators) if zones_with_escalators else len(all_escal_counts),
        }

        if escalator_count > 0:
            result.status = LoadStatus.MODELED
            result.confidence = 1.0
            result.recommendation = "Escalators are modeled using CEC standard process loads"
            result.notes = (
                f"{escalator_count} escalator(s) modeled ({escalator_power:.1f} kW total). "
                f"Note: CEC values may differ from actual equipment."
            )
        else:
            result.status = LoadStatus.NOT_MODELED
            result.recommendation = "Calculate escalator energy as site load if building has escalators"
            result.notes = "No EscalCnt > 0 found in model - escalator energy not included"

        return result

    def _create_never_modeled_detection(self, load_type: str) -> LoadDetectionResult:
        """Create detection result for a load type CBECC never models."""
        descriptions = {
            "pool_pump": "Pool pumps are not simulated in CBECC",
            "pool_heater": "Pool heaters are not simulated in CBECC",
            "spa": "Spa/hot tub loads are not simulated in CBECC",
            "ev_charger": "EV charging is not simulated in CBECC",
            "it_telecom": "IT/telecom loads are not simulated in CBECC",
            "water_pumps": "Water pumps (booster, fire, recirc) are not simulated in CBECC",
            "trash_compactor": "Trash compactors are not simulated in CBECC",
            "site_lighting": "Exterior/site lighting is not simulated in CBECC",
        }

        return LoadDetectionResult(
            load_type=load_type,
            status=LoadStatus.NOT_MODELED,
            confidence=1.0,
            recommendation=f"Calculate {load_type.replace('_', ' ')} as site load if applicable",
            notes=descriptions.get(load_type, "This load type is not modeled in CBECC"),
        )

    def _create_always_modeled_detection(self, load_type: str, content: str, is_xml: bool) -> LoadDetectionResult:
        """Create detection result for loads CBECC always models."""
        if load_type == "interior_lighting":
            # Count ResOtherZn zones
            zone_count = 0
            if is_xml:
                zone_count = content.count('<ResOtherZn>') + content.count('ResOtherZn>')
            else:
                zone_count = len(re.findall(r'ResOtherZn\s+"', content))

            return LoadDetectionResult(
                load_type=load_type,
                status=LoadStatus.MODELED if zone_count > 0 else LoadStatus.NOT_APPLICABLE,
                confidence=1.0,
                details={"common_area_zone_count": zone_count},
                recommendation="Do NOT calculate common area lighting separately",
                notes=f"Interior lighting is included in zone loads for {zone_count} ResOtherZn zone(s)",
            )

        elif load_type == "hvac":
            return LoadDetectionResult(
                load_type=load_type,
                status=LoadStatus.MODELED,
                confidence=1.0,
                recommendation="HVAC energy is always modeled in simulation",
                notes="Heating and cooling for conditioned zones is simulated",
            )

        return LoadDetectionResult(
            load_type=load_type,
            status=LoadStatus.MODELED,
            confidence=0.9,
        )


def detect_modeled_loads(file_path: str | Path) -> ModeledLoadReport:
    """
    Convenience function to detect modeled loads in a CBECC file.

    Args:
        file_path: Path to CBECC .cibd22, .cibd25, .cibd22x, or .cibd25x file

    Returns:
        ModeledLoadReport with detection results

    Example:
        >>> report = detect_modeled_loads("MyBuilding.cibd22x")
        >>> print("Site loads to calculate:", report.get_site_load_recommendations())
        >>> print("Already modeled:", report.get_modeled_loads())
    """
    detector = CbeccModeledLoadDetector()
    return detector.analyze(file_path)
