"""Suppression rules: skip notifications during defined time windows or for specific exit codes."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Optional
from datetime import datetime, time


@dataclass
class SuppressOptions:
    enabled: bool = False
    exit_codes: List[int] = field(default_factory=list)
    time_windows: List[dict] = field(default_factory=list)  # [{start: "HH:MM", end: "HH:MM"}]
    weekdays: List[int] = field(default_factory=list)  # 0=Mon ... 6=Sun

    @classmethod
    def from_dict(cls, d: dict) -> "SuppressOptions":
        return cls(
            enabled=bool(d.get("enabled", False)),
            exit_codes=[int(c) for c in d.get("exit_codes", [])],
            time_windows=d.get("time_windows", []),
            weekdays=[int(w) for w in d.get("weekdays", [])],
        )


@dataclass
class SuppressResult:
    suppressed: bool
    reason: str = ""

    def ok(self) -> bool:
        return not self.suppressed

    def summary(self) -> str:
        if self.suppressed:
            return f"suppressed: {self.reason}"
        return "not suppressed"


def _parse_time(s: str) -> time:
    h, m = s.strip().split(":")
    return time(int(h), int(m))


def _in_window(now: time, start: time, end: time) -> bool:
    if start <= end:
        return start <= now <= end
    # overnight window
    return now >= start or now <= end


def check_suppress(
    opts: SuppressOptions,
    exit_code: Optional[int],
    now: Optional[datetime] = None,
) -> SuppressResult:
    if not opts.enabled:
        return SuppressResult(suppressed=False)

    if exit_code is not None and exit_code in opts.exit_codes:
        return SuppressResult(suppressed=True, reason=f"exit code {exit_code} in suppressed list")

    dt = now or datetime.now()
    current_time = dt.time().replace(second=0, microsecond=0)
    current_weekday = dt.weekday()

    if opts.weekdays and current_weekday in opts.weekdays:
        return SuppressResult(suppressed=True, reason=f"weekday {current_weekday} suppressed")

    for window in opts.time_windows:
        start = _parse_time(window["start"])
        end = _parse_time(window["end"])
        if _in_window(current_time, start, end):
            return SuppressResult(suppressed=True, reason=f"inside time window {window['start']}-{window['end']}")

    return SuppressResult(suppressed=False)
