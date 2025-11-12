"""
Schedule Exporter - Three-Tier Hierarchical Catalog Exporter
============================================================

PURPOSE:
Serializes Schedule objects from InternalRepresentation to CIBD22X XML format.

CBECC SCHEDULE HIERARCHY:
Schedules have a three-tier structure:
1. SchDay (Day Schedule) - Bottom tier with hourly values
2. SchWeek (Week Schedule) - Middle tier referencing day schedules
3. Sch (Annual Schedule) - Top tier referencing week schedules

EXPORT STRATEGY:
1. Determine schedule tier from annotation ('schedule_tier')
2. Export SchDay with hourly values
3. Export SchWeek with day schedule references
4. Export Sch with week schedule references
5. Restore all format-specific properties from annotations

FLAT LIST EXPORT:
Unlike zones/surfaces which nest in XML, schedules are exported as a flat list
where higher tiers reference lower tiers by name (not by nesting).

ANNOTATION RESTORATION:
- 'schedule_tier': 'day', 'week', or 'annual'
- 'data_type': 'Fraction', 'Temperature', 'OnOff'
- Day references for week schedules
- Week/date references for annual schedules

PATTERN: Three-tier catalog exporter with reference-based hierarchy
"""

from typing import List, Optional
import xml.etree.ElementTree as ET
import logging

from eco_tools.core.internal_repr import Schedule
from .base_exporter import BaseExporter

# Get module logger
logger = logging.getLogger('eco_tools.exporters')


class ScheduleExporter(BaseExporter):
    """Exporter for CIBD22X schedule elements"""

    def __init__(self):
        super().__init__()

    def export_schedules(self, parent: ET.Element, schedules: List[Schedule]) -> None:
        """
        Export all schedules to CIBD22X XML.

        Schedules are exported in order: SchDay → SchWeek → Sch
        This ensures referenced schedules exist before they are referenced.

        Args:
            parent: Parent XML element (typically <Building>)
            schedules: List of Schedule objects to export
        """
        if not schedules:
            logger.info("No schedules to export")
            return

        # Separate schedules by tier
        day_schedules = []
        week_schedules = []
        annual_schedules = []

        for schedule in schedules:
            tier = self.get_annotation(schedule.annotation, 'schedule_tier')
            if tier == 'day':
                day_schedules.append(schedule)
            elif tier == 'week':
                week_schedules.append(schedule)
            elif tier == 'annual':
                annual_schedules.append(schedule)
            else:
                # Infer from schedule_type or values presence
                if schedule.values:
                    day_schedules.append(schedule)
                else:
                    annual_schedules.append(schedule)

        # Export in order: day → week → annual
        exported_count = 0
        for schedule in day_schedules:
            if self._export_day_schedule(parent, schedule):
                exported_count += 1

        for schedule in week_schedules:
            if self._export_week_schedule(parent, schedule):
                exported_count += 1

        for schedule in annual_schedules:
            if self._export_annual_schedule(parent, schedule):
                exported_count += 1

        logger.info(f"Exported {exported_count} schedules (all tiers)")

    def _export_day_schedule(self, parent: ET.Element, schedule: Schedule) -> bool:
        """Export a day schedule (SchDay) with hourly values."""
        if not schedule.name:
            return False

        # Create SchDay element
        sch_elem = self.create_element(parent, 'SchDay')

        # Add name (required)
        self.add_text_element(sch_elem, 'Name', schedule.name)

        # Schedule type (data type: Fraction, Temperature, OnOff)
        # CRITICAL: Use data_type from annotation, NOT schedule.schedule_type
        # schedule.schedule_type may contain tier ('day') not data type ('Fraction')
        data_type = self.get_annotation(schedule.annotation, 'data_type', 'Fraction')
        self.add_text_element(sch_elem, 'Type', data_type)

        # Export hourly values (24 hours, indexed 0-23)
        if schedule.values:
            for i, value in enumerate(schedule.values[:24]):  # Ensure max 24 values
                hr_elem = ET.SubElement(sch_elem, 'Hr')
                hr_elem.set('index', str(i))
                hr_elem.text = str(value)

        return True

    def _export_week_schedule(self, parent: ET.Element, schedule: Schedule) -> bool:
        """Export a week schedule (SchWeek) with day schedule references."""
        if not schedule.name:
            return False

        # Create SchWeek element
        sch_elem = self.create_element(parent, 'SchWeek')

        # Add name (required)
        self.add_text_element(sch_elem, 'Name', schedule.name)

        # Restore day schedule references from annotations
        if schedule.annotation:
            # Week schedules reference 7 day schedules (Sun-Sat)
            day_map = {
                'sun': 'Sun',
                'mon': 'Mon',
                'tue': 'Tue',
                'wed': 'Wed',
                'thu': 'Thu',
                'fri': 'Fri',
                'sat': 'Sat'
            }
            
            for day_key, day_tag in day_map.items():
                day_ref = self.get_annotation(schedule.annotation, f'{day_key}_ref')
                if day_ref:
                    self.add_text_element(sch_elem, day_tag, day_ref)

        return True

    def _export_annual_schedule(self, parent: ET.Element, schedule: Schedule) -> bool:
        """Export an annual schedule (Sch) with week schedule references."""
        if not schedule.name:
            return False

        # Create Sch element
        sch_elem = self.create_element(parent, 'Sch')

        # Add name (required)
        self.add_text_element(sch_elem, 'Name', schedule.name)

        # Schedule type
        if schedule.schedule_type:
            self.add_text_element(sch_elem, 'Type', schedule.schedule_type)

        # Restore week schedule references from annotations
        if schedule.annotation:
            # Annual schedules can have multiple week schedule references
            # with start/end dates
            week_refs = self.get_annotation(schedule.annotation, 'week_refs')
            if week_refs and isinstance(week_refs, list):
                for i, week_ref_data in enumerate(week_refs):
                    if isinstance(week_ref_data, dict):
                        week_sch_ref = week_ref_data.get('week_schedule_ref')
                        if week_sch_ref:
                            ref_elem = ET.SubElement(sch_elem, 'WeekSchRef')
                            ref_elem.text = week_sch_ref
                            
                            # Optional date range
                            start_date = week_ref_data.get('start_date')
                            if start_date:
                                start_elem = ET.SubElement(sch_elem, 'BeginDate')
                                start_elem.text = start_date
                            
                            end_date = week_ref_data.get('end_date')
                            if end_date:
                                end_elem = ET.SubElement(sch_elem, 'EndDate')
                                end_elem.text = end_date

        return True
