"""Time window enforcement for cron jobs.

Allows restricting job execution to specific time windows (e.g., only
run between 08:00 and 18:00, or only on weekdays).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, time
from typing import List, Optional


@dataclass
class WindowOptions:
    enabled: bool = False
    # e.g. ["08:00", "18:00"] — start and end times (24h)
    allowed_hours: Optional[List[str]] = None
    # 0=Monday … 6=Sunday
    allowed_weekdays: Optional[List[int]] = None
    # Human-readable label for log messages
    label: str = "time-window"

    @classmethod
    def from_dict(cls, data: dict) -> "WindowOptions":
        return cls(
            enabled=bool(data.get("enabled", False)),
            allowed_hours=data.get("allowed_hours"),
            allowed_weekdays=data.get("allowed_weekdays"),
            label=str(data.get("label", "time-window")),
        )


@dataclass
class WindowResult:
    allowed: bool
    reason: str

    def ok(self) -> bool:
        return self.allowed

    def summary(self) -> str:
        status = "allowed" if self.allowed else "blocked"
        return f"[window] {status}: {self.reason}"


def _parse_time(t: str) -> time:
    """Parse 'HH:MM' into a datetime.time object."""
    parts = t.strip().split(":")
    if len(parts) != 2:
        raise ValueError(f"Invalid time format: {t!r} (expected HH:MM)")
    return time(int(parts[0]), int(parts[1]))


def check_window(
    opts: WindowOptions,
    now: Optional[datetime] = None,
) -> Optional[WindowResult]:
    """Return a WindowResult if the window check is enabled, else None."""
    if not opts.enabled:
        return None

    now = now or datetime.now()

    # Weekday check
    if opts.allowed_weekdays is not None:
        if now.weekday() not in opts.allowed_weekdays:
            return WindowResult(
                allowed=False,
                reason=f"weekday {now.weekday()} not in {opts.allowed_weekdays}",
            )

    # Hour-range check
    if opts.allowed_hours is not None:
        if len(opts.allowed_hours) != 2:
            raise ValueError("allowed_hours must be a list of exactly two 'HH:MM' strings")
        start = _parse_time(opts.allowed_hours[0])
        end = _parse_time(opts.allowed_hours[1])
        current = now.time().replace(second=0, microsecond=0)
        if not (start <= current <= end):
            return WindowResult(
                allowed=False,
                reason=f"current time {current} outside [{start}, {end}]",
            )

    return WindowResult(allowed=True, reason="within allowed window")
