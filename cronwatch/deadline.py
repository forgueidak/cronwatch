"""deadline.py — Absolute deadline enforcement for cron jobs.

Allows a job to declare a wall-clock deadline (e.g. "must finish by 06:00").
If the job starts or is still running past the deadline, a DeadlineResult
flags it so downstream notifiers can act accordingly.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime, time
from typing import Optional


@dataclass
class DeadlineOptions:
    enabled: bool = False
    # Wall-clock time string "HH:MM" (24-hour) by which the job must complete.
    by: str = ""  # e.g. "06:00"
    # Timezone name — kept as a label for display; comparison uses local time.
    timezone: str = "local"

    @classmethod
    def from_dict(cls, data: dict) -> "DeadlineOptions":
        raw = data.get("deadline", {})
        return cls(
            enabled=bool(raw.get("enabled", False)),
            by=str(raw.get("by", "")),
            timezone=str(raw.get("timezone", "local")),
        )

    def _parse_by(self) -> Optional[time]:
        """Return a datetime.time from the 'by' string, or None if invalid."""
        m = re.fullmatch(r"(\d{1,2}):(\d{2})", self.by.strip())
        if not m:
            return None
        hour, minute = int(m.group(1)), int(m.group(2))
        if hour > 23 or minute > 59:
            return None
        return time(hour, minute)


@dataclass
class DeadlineResult:
    enabled: bool
    deadline_time: Optional[time]
    checked_at: datetime
    missed: bool
    message: str

    def ok(self) -> bool:
        return not self.missed

    def summary(self) -> str:
        return self.message


def check_deadline(opts: DeadlineOptions, now: Optional[datetime] = None) -> Optional[DeadlineResult]:
    """Check whether the current time has passed the declared deadline.

    Returns None when the feature is disabled.
    Returns a DeadlineResult indicating whether the deadline was missed.
    """
    if not opts.enabled:
        return None

    deadline_time = opts._parse_by()
    if deadline_time is None:
        return DeadlineResult(
            enabled=True,
            deadline_time=None,
            checked_at=now or datetime.now(),
            missed=False,
            message=f"Deadline 'by' value {opts.by!r} is invalid — skipping check.",
        )

    checked_at = now or datetime.now()
    current_time = checked_at.time().replace(second=0, microsecond=0)
    missed = current_time > deadline_time

    if missed:
        msg = (
            f"Deadline missed: job ran at {current_time.strftime('%H:%M')} "
            f"but was required to complete by {deadline_time.strftime('%H:%M')} "
            f"({opts.timezone})."
        )
    else:
        msg = (
            f"Deadline met: job ran at {current_time.strftime('%H:%M')}, "
            f"within deadline of {deadline_time.strftime('%H:%M')} ({opts.timezone})."
        )

    return DeadlineResult(
        enabled=True,
        deadline_time=deadline_time,
        checked_at=checked_at,
        missed=missed,
        message=msg,
    )
