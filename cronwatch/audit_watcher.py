"""Thin integration layer: record audit entries during a watched job run."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from cronwatch.audit import record_audit
from cronwatch.runner import JobResult


@dataclass
class AuditWatchOptions:
    enabled: bool = False
    log_dir: str = "/var/log/cronwatch/audit"
    actor: str = "cronwatch"
    # Subset of events to record; empty list means record all.
    events: list = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict) -> "AuditWatchOptions":
        return cls(
            enabled=bool(data.get("enabled", False)),
            log_dir=str(data.get("log_dir", "/var/log/cronwatch/audit")),
            actor=str(data.get("actor", "cronwatch")),
            events=list(data.get("events", [])),
        )


def _should_record(opts: AuditWatchOptions, event: str) -> bool:
    return not opts.events or event in opts.events


def audit_job_run(
    opts: AuditWatchOptions,
    result: JobResult,
    extra_events: Optional[list] = None,
) -> None:
    """Record audit entries for a completed job run.

    Always records ``job_run``.  Any additional event names passed via
    *extra_events* (e.g. ``"alert_sent"``) are recorded when allowed by
    the options filter.
    """
    if not opts.enabled:
        return

    if _should_record(opts, "job_run"):
        record_audit(
            opts.log_dir,
            event="job_run",
            job=result.command,
            actor=opts.actor,
            detail={
                "exit_code": result.exit_code,
                "success": result.success,
                "duration": round(result.duration, 3),
            },
        )

    for ev in extra_events or []:
        if _should_record(opts, ev):
            record_audit(
                opts.log_dir,
                event=ev,
                job=result.command,
                actor=opts.actor,
            )
