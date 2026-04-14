"""Audit log: immutable append-only record of every cronwatch action."""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional


@dataclass
class AuditEntry:
    timestamp: str
    event: str          # e.g. "job_run", "alert_sent", "lock_acquired"
    job: str
    actor: str = "cronwatch"
    detail: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "timestamp": self.timestamp,
            "event": self.event,
            "job": self.job,
            "actor": self.actor,
            "detail": self.detail,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "AuditEntry":
        return cls(
            timestamp=data.get("timestamp", ""),
            event=data.get("event", ""),
            job=data.get("job", ""),
            actor=data.get("actor", "cronwatch"),
            detail=data.get("detail", {}),
        )


def _audit_path(log_dir: str, job: str) -> Path:
    safe = job.replace("/", "_").replace(" ", "_")
    return Path(log_dir) / f"{safe}.audit.jsonl"


def record_audit(
    log_dir: str,
    event: str,
    job: str,
    detail: Optional[dict] = None,
    actor: str = "cronwatch",
) -> AuditEntry:
    """Append one audit entry to the job's audit log file."""
    entry = AuditEntry(
        timestamp=datetime.now(timezone.utc).isoformat(),
        event=event,
        job=job,
        actor=actor,
        detail=detail or {},
    )
    path = _audit_path(log_dir, job)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry.to_dict()) + "\n")
    return entry


def load_audit_log(log_dir: str, job: str) -> List[AuditEntry]:
    """Return all audit entries for *job*, newest first."""
    path = _audit_path(log_dir, job)
    if not path.exists():
        return []
    entries: List[AuditEntry] = []
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                try:
                    entries.append(AuditEntry.from_dict(json.loads(line)))
                except (json.JSONDecodeError, KeyError):
                    pass
    entries.reverse()
    return entries
