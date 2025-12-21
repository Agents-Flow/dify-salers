"""
Timezone-aware global scheduler service.
Enables 24/7 operations by scheduling tasks according to target audience timezones.
"""

import logging
import operator
from dataclasses import dataclass, field
from datetime import datetime, time, timedelta
from typing import Any
from zoneinfo import ZoneInfo

logger = logging.getLogger(__name__)


# Common timezone mappings by region
REGION_TIMEZONES = {
    "US": ["America/New_York", "America/Chicago", "America/Denver", "America/Los_Angeles"],
    "EU": ["Europe/London", "Europe/Paris", "Europe/Berlin", "Europe/Rome"],
    "UK": ["Europe/London"],
    "DE": ["Europe/Berlin"],
    "FR": ["Europe/Paris"],
    "APAC": ["Asia/Tokyo", "Asia/Shanghai", "Asia/Singapore", "Australia/Sydney"],
    "JP": ["Asia/Tokyo"],
    "CN": ["Asia/Shanghai"],
    "SG": ["Asia/Singapore"],
    "AU": ["Australia/Sydney"],
    "TR": ["Europe/Istanbul"],
    "IN": ["Asia/Kolkata"],
    "BR": ["America/Sao_Paulo"],
    "MX": ["America/Mexico_City"],
    "MENA": ["Asia/Dubai", "Asia/Riyadh", "Africa/Cairo"],
}

# Default optimal engagement hours (local time)
DEFAULT_ENGAGEMENT_WINDOWS = [
    (time(7, 0), time(9, 0)),   # Morning commute
    (time(12, 0), time(14, 0)),  # Lunch break
    (time(17, 0), time(19, 0)),  # After work
    (time(20, 0), time(22, 0)),  # Evening leisure
]


@dataclass
class TimezoneWindow:
    """An active time window in a specific timezone."""
    timezone: str
    start_time: time
    end_time: time
    priority: int = 1  # Higher = more important

    def is_active_at(self, dt: datetime) -> bool:
        """Check if the window is active at a given UTC datetime."""
        try:
            tz = ZoneInfo(self.timezone)
            local_time = dt.astimezone(tz).time()
            if self.start_time <= self.end_time:
                return self.start_time <= local_time <= self.end_time
            else:  # Crosses midnight
                return local_time >= self.start_time or local_time <= self.end_time
        except Exception:
            return False

    def next_start_utc(self, from_dt: datetime | None = None) -> datetime:
        """Get the next start time in UTC."""
        try:
            tz = ZoneInfo(self.timezone)
            now = (from_dt or datetime.now(tz)).astimezone(tz)

            # Create today's start time
            start_dt = now.replace(
                hour=self.start_time.hour,
                minute=self.start_time.minute,
                second=0,
                microsecond=0,
            )

            # If we've passed today's start, move to tomorrow
            if now.time() >= self.start_time:
                start_dt += timedelta(days=1)

            return start_dt.astimezone(ZoneInfo("UTC")).replace(tzinfo=None)
        except Exception:
            return datetime.now() + timedelta(hours=1)


@dataclass
class RegionSchedule:
    """Schedule configuration for a geographic region."""
    region_code: str
    timezones: list[str]
    windows: list[TimezoneWindow] = field(default_factory=list)
    weight: float = 1.0  # Relative importance/traffic weight

    def get_active_windows(self, dt: datetime | None = None) -> list[TimezoneWindow]:
        """Get currently active windows."""
        check_time = dt or datetime.now(ZoneInfo("UTC"))
        return [w for w in self.windows if w.is_active_at(check_time)]


@dataclass
class ScheduledSlot:
    """A scheduled time slot for operations."""
    start_utc: datetime
    end_utc: datetime
    timezone: str
    region: str
    priority: int = 1

    def duration_minutes(self) -> int:
        return int((self.end_utc - self.start_utc).total_seconds() / 60)

    def to_dict(self) -> dict[str, Any]:
        return {
            "start_utc": self.start_utc.isoformat(),
            "end_utc": self.end_utc.isoformat(),
            "timezone": self.timezone,
            "region": self.region,
            "priority": self.priority,
            "duration_minutes": self.duration_minutes(),
        }


class TimezoneSchedulerService:
    """
    Service for timezone-aware task scheduling.
    Enables 24/7 global operations by distributing tasks across timezones.
    """

    def __init__(self):
        self._region_schedules: dict[str, RegionSchedule] = {}
        self._initialize_default_schedules()

    def _initialize_default_schedules(self) -> None:
        """Initialize default schedules for major regions."""
        for region_code, timezones in REGION_TIMEZONES.items():
            windows = []
            for tz in timezones:
                for start, end in DEFAULT_ENGAGEMENT_WINDOWS:
                    windows.append(TimezoneWindow(
                        timezone=tz,
                        start_time=start,
                        end_time=end,
                        priority=1,
                    ))
            self._region_schedules[region_code] = RegionSchedule(
                region_code=region_code,
                timezones=timezones,
                windows=windows,
            )

    def add_region_schedule(self, schedule: RegionSchedule) -> None:
        """Add or update a region schedule."""
        self._region_schedules[schedule.region_code] = schedule
        logger.info("Added/updated schedule for region: %s", schedule.region_code)

    def get_region_schedule(self, region_code: str) -> RegionSchedule | None:
        """Get schedule for a region."""
        return self._region_schedules.get(region_code.upper())

    def get_current_active_regions(self) -> list[str]:
        """Get list of regions currently in their active windows."""
        now = datetime.now(ZoneInfo("UTC"))
        active = []
        for region_code, schedule in self._region_schedules.items():
            if schedule.get_active_windows(now):
                active.append(region_code)
        return active

    def get_optimal_schedule_time(
        self,
        target_regions: list[str],
        from_time: datetime | None = None,
    ) -> datetime:
        """
        Find the optimal time to execute a task for target regions.
        Returns the soonest time when at least one target region is active.
        """
        from_time = from_time or datetime.now(ZoneInfo("UTC"))

        # Collect all upcoming windows
        upcoming_starts: list[tuple[datetime, str]] = []

        for region_code in target_regions:
            schedule = self._region_schedules.get(region_code.upper())
            if not schedule:
                continue

            for window in schedule.windows:
                if window.is_active_at(from_time):
                    # Already active, can execute now
                    return from_time.replace(tzinfo=None) if from_time.tzinfo else from_time

                next_start = window.next_start_utc(from_time)
                upcoming_starts.append((next_start, region_code))

        if not upcoming_starts:
            # No schedules found, default to 1 hour from now
            return (from_time + timedelta(hours=1)).replace(tzinfo=None)

        # Return the soonest upcoming window
        upcoming_starts.sort(key=operator.itemgetter(0))
        return upcoming_starts[0][0]

    def get_24h_schedule(
        self,
        target_regions: list[str] | None = None,
        from_time: datetime | None = None,
    ) -> list[ScheduledSlot]:
        """
        Generate a 24-hour schedule of active slots across regions.
        Useful for planning global operations.
        """
        from_time = from_time or datetime.now(ZoneInfo("UTC"))
        end_time = from_time + timedelta(hours=24)
        regions = target_regions or list(self._region_schedules.keys())

        slots: list[ScheduledSlot] = []

        for region_code in regions:
            schedule = self._region_schedules.get(region_code.upper())
            if not schedule:
                continue

            for window in schedule.windows:
                # Find all occurrences of this window in the next 24h
                current = from_time
                while current < end_time:
                    if window.is_active_at(current):
                        # Find window boundaries
                        try:
                            tz = ZoneInfo(window.timezone)
                            local_current = current.astimezone(tz)

                            # Calculate end time
                            if window.end_time > window.start_time:
                                local_end = local_current.replace(
                                    hour=window.end_time.hour,
                                    minute=window.end_time.minute,
                                )
                            else:
                                local_end = local_current.replace(
                                    hour=window.end_time.hour,
                                    minute=window.end_time.minute,
                                ) + timedelta(days=1)

                            slot_end = min(
                                local_end.astimezone(ZoneInfo("UTC")).replace(tzinfo=None),
                                end_time.replace(tzinfo=None) if end_time.tzinfo else end_time,
                            )

                            slots.append(ScheduledSlot(
                                start_utc=current.replace(tzinfo=None) if current.tzinfo else current,
                                end_utc=slot_end,
                                timezone=window.timezone,
                                region=region_code,
                                priority=window.priority,
                            ))

                            # Move to end of this window
                            current = local_end.astimezone(ZoneInfo("UTC"))
                        except Exception as e:
                            logger.warning("Error calculating slot: %s", e)
                            current += timedelta(hours=1)
                    else:
                        current += timedelta(minutes=30)  # Check in 30min intervals

        # Sort by start time
        slots.sort(key=lambda s: s.start_utc)
        return slots

    def distribute_tasks_by_timezone(
        self,
        task_count: int,
        target_regions: list[str],
        start_time: datetime | None = None,
        end_time: datetime | None = None,
    ) -> list[tuple[datetime, str]]:
        """
        Distribute tasks evenly across timezones within their active windows.
        Returns list of (scheduled_time, region) tuples.
        """
        start_time = start_time or datetime.now(ZoneInfo("UTC"))
        end_time = end_time or (start_time + timedelta(hours=24))

        # Get 24h schedule
        slots = self.get_24h_schedule(target_regions, start_time)

        if not slots:
            # Fallback: distribute evenly over 24h
            interval = timedelta(hours=24) / task_count
            return [
                (start_time + interval * i, target_regions[i % len(target_regions)])
                for i in range(task_count)
            ]

        # Calculate total available minutes
        total_minutes = sum(s.duration_minutes() for s in slots)

        if total_minutes == 0:
            return []

        # Distribute tasks proportionally to slot duration
        scheduled_tasks: list[tuple[datetime, str]] = []
        tasks_remaining = task_count

        for slot in slots:
            if tasks_remaining <= 0:
                break

            # Tasks for this slot based on its proportion of total time
            slot_tasks = max(1, int(task_count * slot.duration_minutes() / total_minutes))
            slot_tasks = min(slot_tasks, tasks_remaining)

            # Distribute within slot
            slot_duration = (slot.end_utc - slot.start_utc).total_seconds()
            for i in range(slot_tasks):
                offset = timedelta(seconds=slot_duration * (i + 1) / (slot_tasks + 1))
                task_time = slot.start_utc + offset
                scheduled_tasks.append((task_time, slot.region))
                tasks_remaining -= 1

        return scheduled_tasks

    def is_within_work_hours(
        self,
        timezone: str,
        dt: datetime | None = None,
    ) -> bool:
        """Check if a time is within work hours for a timezone."""
        dt = dt or datetime.now(ZoneInfo("UTC"))
        try:
            tz = ZoneInfo(timezone)
            local_hour = dt.astimezone(tz).hour
            return 8 <= local_hour < 22  # 8 AM to 10 PM
        except Exception:
            return True

    def get_timezone_for_region(self, region_code: str) -> str:
        """Get primary timezone for a region."""
        schedule = self._region_schedules.get(region_code.upper())
        if schedule and schedule.timezones:
            return schedule.timezones[0]
        return "UTC"

    def get_global_overview(self) -> dict[str, Any]:
        """Get overview of global schedule status."""
        now = datetime.now(ZoneInfo("UTC"))
        active_regions = self.get_current_active_regions()

        overview = {
            "current_utc": now.isoformat(),
            "active_regions": active_regions,
            "total_regions": len(self._region_schedules),
            "regions": {},
        }

        for region_code, schedule in self._region_schedules.items():
            active_windows = schedule.get_active_windows(now)
            overview["regions"][region_code] = {
                "is_active": len(active_windows) > 0,
                "active_windows_count": len(active_windows),
                "total_windows": len(schedule.windows),
                "timezones": schedule.timezones,
            }

        return overview


def create_timezone_scheduler_service() -> TimezoneSchedulerService:
    """Factory function to create TimezoneSchedulerService."""
    return TimezoneSchedulerService()
