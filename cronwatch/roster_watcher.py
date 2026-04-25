"""roster_watcher.py — Auto-register jobs in the roster on each run."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

from cronwatch.roster import RosterEntry, RosterOptions, register_job, load_job
from cronwatch.runner import JobResult


@dataclass
class RosterWatchOptions:
    enabled: bool = True
    roster_dir: str = "/var/lib/cronwatch/roster"
    tags: List[str] = field(default_factory=list)
    description: str = ""
    schedule: str = ""

    @classmethod
    def from_dict(cls, data: dict) -> "RosterWatchOptions":
        d = data.get("roster", data)
        return cls(
            enabled=bool(d.get("enabled", True)),
            roster_dir=str(d.get("roster_dir", "/var/lib/cronwatch/roster")),
            tags=list(d.get("tags") or []),
            description=str(d.get("description", "")),
            schedule=str(d.get("schedule", "")),
        )


def ensure_registered(
    result: JobResult,
    opts: RosterWatchOptions,
    job_name: Optional[str] = None,
) -> Optional[RosterEntry]:
    """Register the job in the roster if not already present.

    Returns the RosterEntry that was saved, or None if disabled.
    """
    if not opts.enabled:
        return None

    name = job_name or result.command
    existing = load_job(name, opts.roster_dir)
    if existing is not None:
        return existing

    entry = RosterEntry(
        name=name,
        command=result.command,
        schedule=opts.schedule,
        tags=opts.tags,
        enabled=True,
        description=opts.description,
    )
    register_job(entry, opts.roster_dir)
    return entry


def format_roster_notice(entry: RosterEntry) -> str:
    """Return a human-readable notice that a job was registered."""
    tag_str = ", ".join(entry.tags) if entry.tags else "none"
    return (
        f"[roster] Registered job '{entry.name}' "
        f"(schedule={entry.schedule or 'unset'}, tags={tag_str})"
    )
