"""Integration layer: record and check heartbeats as part of a job run."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from cronwatch.heartbeat import (
    HeartbeatOptions,
    HeartbeatResult,
    check_heartbeat,
    record_heartbeat,
)
from cronwatch.runner import JobResult


@dataclass
class HeartbeatWatchOptions:
    options: HeartbeatOptions
    alert_on_miss: bool = True
    record_on_success_only: bool = True

    @classmethod
    def from_dict(cls, data: dict) -> "HeartbeatWatchOptions":
        return cls(
            options=HeartbeatOptions.from_dict(data),
            alert_on_miss=bool(data.get("alert_on_miss", True)),
            record_on_success_only=bool(data.get("record_on_success_only", True)),
        )


def pre_run_check(
    job_name: str, watch_opts: HeartbeatWatchOptions
) -> Optional[HeartbeatResult]:
    """Check heartbeat before a job runs; returns result if enabled, else None."""
    if not watch_opts.options.enabled:
        return None
    return check_heartbeat(job_name, watch_opts.options)


def post_run_record(
    job_name: str, result: JobResult, watch_opts: HeartbeatWatchOptions
) -> bool:
    """Record heartbeat after a run; returns True if heartbeat was recorded."""
    if not watch_opts.options.enabled:
        return False
    if watch_opts.record_on_success_only and result.returncode != 0:
        return False
    record_heartbeat(job_name, watch_opts.options)
    return True


def format_miss_notice(result: HeartbeatResult) -> str:
    """Return a human-readable alert string for a missed heartbeat."""
    return (
        f"\u26a0\ufe0f  Heartbeat MISSED for job '{result.job_name}'.\n"
        f"{result.summary}"
    )
