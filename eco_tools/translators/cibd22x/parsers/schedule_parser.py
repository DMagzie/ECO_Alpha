"""
Schedule Parser - Time-Based Schedule Catalog Parser
===================================================

PURPOSE:
Extracts time-dependent operating schedules from CIBD22X XML catalogs.
Schedules control equipment operation, occupancy patterns, lighting, etc.

CBECC SCHEDULE HIERARCHY:
CBECC uses a THREE-TIER catalog reference system:

1. SchDay (Day Schedule) - Bottom tier
   ├─ Contains: 24 hourly values (0-23)
   ├─ Data type: fraction, temperature, on/off
   └─ Example: "Weekday_Office_Hours" = [0,0,0,0,0,0,0,1,1,1,1,1,0,1,1,1,1,1,0,0,0,0,0,0]

2. SchWeek (Week Schedule) - Middle tier
   ├─ Contains: References to 7 day schedules (Sun-Sat)
   ├─ Example: "Office_Week" → {Mon: "Weekday", Tue: "Weekday", ..., Sun: "Weekend"}
   └─ Does NOT contain raw values, only references

3. Sch (Annual Schedule) - Top tier
   ├─ Contains: References to week schedules for entire year
   ├─ Example: "Office_Year" → {Jan-Mar: "Office_Week", Apr-Sep: "Summer_Week", ...}
   └─ Does NOT contain raw values, only references

This hierarchical catalog pattern enables:
- Reusability: Same day schedule used across multiple weeks
- Compact representation: Change one day schedule, affects all weeks
- Title 24 compliance: Match prescribed schedules at any tier

PARSING STRATEGY:
We parse all three tiers independently and store them as separate Schedule objects.
The internal representation preserves the reference structure so the exporter
can reconstruct the three-tier hierarchy.

DATA TYPES:
- 'fraction': 0.0-1.0 (e.g., occupancy fraction, equipment load fraction)
- 'temperature': °F (e.g., thermostat setpoints)
- 'on/off': Binary control (e.g., lighting control)

DESIGN PATTERN:
This is a "Simple Catalog Parser" with internal cross-references but no
dependencies on other parsers. All schedules are catalog elements.
"""

from typing import List, Optional
import xml.etree.ElementTree as ET
import logging

from eco_tools.core.internal_repr import Schedule
from eco_tools.core.id_registry import IDRegistry
from .base_parser import BaseParser

# Get module logger
logger = logging.getLogger('eco_tools.parsers')


class ScheduleParser(BaseParser):
    """Parser for CIBD22X schedule elements"""

    # CIBD22X schedule catalog tags
    SCHEDULE_CATALOG_TAGS = [
        'SchDay',   # Day schedules (hourly values)
        'SchWeek',  # Week schedules (day references)
        'Sch'       # Annual schedules (week references)
    ]

    def __init__(self, id_registry: IDRegistry):
        """
        Initialize the schedule parser.

        Args:
            id_registry: ID registry for generating unique schedule IDs
        """
        super().__init__()
        self.id_registry = id_registry

    def parse_schedules(self, root: ET.Element) -> List[Schedule]:
        """
        Parse all three tiers of the CBECC schedule hierarchy.

        PARSING ORDER:
        We parse all three tiers into a flat list of Schedule objects.
        The order doesn't matter because schedules reference each other by NAME,
        not by object pointer. The references will be resolved at runtime when needed.

        TIER 1: Day Schedules (SchDay)
        - Bottom tier with actual hourly values
        - 24 values representing hours 0-23
        - Data type specifies interpretation (fraction, temperature, on/off)

        TIER 2: Week Schedules (SchWeek)
        - Middle tier with day schedule references
        - 7 references for Sunday through Saturday
        - No raw values, only references to SchDay names

        TIER 3: Annual Schedules (Sch)
        - Top tier with week schedule references
        - Date ranges mapped to week schedule names
        - No raw values, only references to SchWeek names

        WHY FLAT LIST:
        Instead of building a nested hierarchy (Sch → SchWeek → SchDay),
        we store all schedules in a flat list with cross-references.
        This matches the CBECC catalog pattern and simplifies export logic.

        Args:
            root: Root XML element

        Returns:
            Flat list of Schedule objects from all three tiers
        """
        schedules = []

        # ================================================================
        # TIER 1: Parse Day Schedules (Bottom - Contains Actual Values)
        # ================================================================
        # Day schedules are the only tier with actual numeric values.
        # They define hourly patterns for a 24-hour period.
        for sch_elem in root.iter():
            if self._local_tag(sch_elem.tag) == 'SchDay':
                schedule = self._parse_day_schedule(sch_elem)
                if schedule:
                    schedules.append(schedule)
                else:
                    name = self._get_name(sch_elem) or "unnamed"
                    logger.warning(f"Failed to parse SchDay '{name}'")

        # ================================================================
        # TIER 2: Parse Week Schedules (Middle - References Day Schedules)
        # ================================================================
        # Week schedules assign day schedules to each day of the week.
        # They reference SchDay names, not direct values.
        for sch_elem in root.iter():
            if self._local_tag(sch_elem.tag) == 'SchWeek':
                schedule = self._parse_week_schedule(sch_elem)
                if schedule:
                    schedules.append(schedule)
                else:
                    name = self._get_name(sch_elem) or "unnamed"
                    logger.warning(f"Failed to parse SchWeek '{name}'")

        # ================================================================
        # TIER 3: Parse Annual Schedules (Top - References Week Schedules)
        # ================================================================
        # Annual schedules assign week schedules to date ranges across the year.
        # They reference SchWeek names, not direct values.
        for sch_elem in root.iter():
            if self._local_tag(sch_elem.tag) == 'Sch':
                schedule = self._parse_annual_schedule(sch_elem)
                if schedule:
                    schedules.append(schedule)
                else:
                    name = self._get_name(sch_elem) or "unnamed"
                    logger.warning(f"Failed to parse Sch '{name}'")

        logger.info(f"Parsed {len(schedules)} schedules (all tiers)")
        return schedules

    def _parse_day_schedule(self, sch_elem: ET.Element) -> Optional[Schedule]:
        """
        Parse a day schedule (SchDay) - the only tier with actual hourly values.

        CBECC XML STRUCTURE:
        <SchDay>
            <n>Weekday_Office_Hours</n>
            <Type>Fraction</Type>
            <Hr>0.0</Hr>  <!-- Hour 0: midnight -->
            <Hr>0.0</Hr>  <!-- Hour 1 -->
            ...
            <Hr>1.0</Hr>  <!-- Hour 8: 8 AM - occupied -->
            ...
            <Hr>0.0</Hr>  <!-- Hour 23: 11 PM -->
        </SchDay>

        PARSING STRATEGY:
        1. Extract name and generate unique ID
        2. Determine data type (fraction, temperature, on/off)
        3. Parse 24 <Hr> elements into values array
        4. Build hours array as [0, 1, 2, ..., 23]
        5. Store in Schedule object with type='day'

        DATA INTERPRETATION:
        - fraction: 0.0-1.0 (e.g., 0.5 = 50% occupancy)
        - temperature: °F (e.g., 72.0 = 72°F setpoint)
        - on/off: typically 0 or 1 (binary control)

        Args:
            sch_elem: SchDay XML element

        Returns:
            Schedule object with type='day' and hourly values
        """
        # Extract name (required for catalog references)
        name = self._get_name(sch_elem)
        if not name:
            name = "Day Schedule"  # Fallback for rare missing name

        # Generate unique ID for this schedule
        sch_id = self.id_registry.generate_id('SCH', name, '', 'CIBD22X')

        # Data type determines how values are interpreted
        # Default to 'fraction' if not specified (most common)
        data_type = self.get_property(sch_elem, 'Type') or 'fraction'

        # ================================================================
        # Parse Hourly Values (24 hours: 0-23)
        # ================================================================
        # CBECC stores hours as sequential <Hr> elements
        # Values are parsed in order: first <Hr> = hour 0, second = hour 1, etc.
        values = []
        hours = []
        for hr_elem in sch_elem.findall('.//Hr'):
            hr_text = hr_elem.text
            if hr_text:
                try:
                    val = float(hr_text.strip())
                    values.append(val)
                    # Hour index = position in array (0-based)
                    hours.append(len(values) - 1)
                except ValueError:
                    # Invalid numeric value - skip this hour
                    # This is rare but possible in malformed files
                    pass

        # Build annotation for round-trip fidelity
        # Store original XML tag so exporter knows to write <SchDay>
        annotation = {
            'xml_tag': 'SchDay',
            'schedule_tier': 'day',
            'data_type': data_type  # Store for round-trip export
        }

        # Create Schedule object
        # Note: day_schedules is empty for SchDay (only used in SchWeek/Sch)
        schedule = Schedule(
            id=sch_id,
            name=name,
            schedule_type='day',             # Bottom tier
            data_type=data_type,             # How to interpret values
            values=values,                    # Actual hourly values [0-23]
            hours=hours,                      # Hour indices [0, 1, ..., 23]
            day_schedules=[],                 # Empty for day schedules
            annotation=annotation
        )

        return schedule

    def _parse_week_schedule(self, sch_elem: ET.Element) -> Optional[Schedule]:
        """
        Parse a week schedule (SchWeek) with day schedule references.

        Args:
            sch_elem: SchWeek XML element

        Returns:
            Schedule object with type='week'
        """
        # Get name
        name = self._get_name(sch_elem)
        if not name:
            name = "Week Schedule"

        # Generate schedule ID
        sch_id = self.id_registry.generate_id('SCH', name, '', 'CIBD22X')

        # Parse day schedule references
        day_schedules = []
        for day_ref_elem in sch_elem.findall('.//DaySchRef'):
            if day_ref_elem.text:
                day_schedules.append(day_ref_elem.text.strip())

        # Build annotation
        annotation = {'xml_tag': 'SchWeek'}

        # Create Schedule object
        schedule = Schedule(
            id=sch_id,
            name=name,
            schedule_type='week',
            data_type=None,
            values=[],
            hours=[],
            day_schedules=day_schedules,
            annotation=annotation
        )

        return schedule

    def _parse_annual_schedule(self, sch_elem: ET.Element) -> Optional[Schedule]:
        """
        Parse an annual schedule (Sch) with week schedule references.

        Args:
            sch_elem: Sch XML element

        Returns:
            Schedule object with type='year'
        """
        # Get name
        name = self._get_name(sch_elem)
        if not name:
            name = "Annual Schedule"

        # Generate schedule ID
        sch_id = self.id_registry.generate_id('SCH', name, '', 'CIBD22X')

        # Data type
        data_type = self.get_property(sch_elem, 'Type')

        # Week schedule references
        week_schedules = []
        for week_ref_elem in sch_elem.findall('.//WeekSchRef'):
            if week_ref_elem.text:
                week_schedules.append(week_ref_elem.text.strip())

        # Build annotation
        annotation = {'xml_tag': 'Sch'}

        # Create Schedule object
        # Note: Reuse day_schedules field for week schedule references
        schedule = Schedule(
            id=sch_id,
            name=name,
            schedule_type='year',
            data_type=data_type,
            values=[],
            hours=[],
            day_schedules=week_schedules,  # Reuse field for week refs
            annotation=annotation
        )

        return schedule

    def _get_name(self, element: ET.Element) -> Optional[str]:
        """
        Extract name from element (CIBD22X format).

        Tries: <n>, <Name>, id attribute

        Args:
            element: XML element

        Returns:
            Element name or None
        """
        # Try <n> child (CIBD22X format) - namespace-aware
        for child in element:
            tag = self._local_tag(child.tag)
            if tag == 'n' and child.text:
                return child.text.strip()

        # Try <Name> child - namespace-aware
        for child in element:
            tag = self._local_tag(child.tag)
            if tag == 'Name' and child.text:
                return child.text.strip()

        # Try id attribute
        name = element.get('id')
        if name:
            return name

        return None
