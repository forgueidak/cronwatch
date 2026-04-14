"""Heartbeat tracking: detect jobs that haven't run within an expected interval."""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class HeartbeatOptions:
    enabled: bool = False
    interval_seconds: int = 3600  # expected max gap between runs
    state_dir: str = "/tmp/cronwatch/heartbeat"

    @classmethod
    def from_dict(cls, data: dict) -> "HeartbeatOptions":
        return cls(
            enabled=bool(data.get("enabled", False)),
            interval_seconds=int(data.get("interval_seconds", 3600)),
            state_dir=str(data.get("state_dir", "/tmp/cronwatch/heartbeat")),
        )


@dataclass
class HeartbeatResult:
    job_name: str
    last_seen: Optional[float]
    now: float
    interval_seconds: int
    missed: bool

    @property
    def ok(self) -> bool:
        return not self.missed

    @property
    def summary(self) -> str:
        if self.last_seen is None:
            return f"[{self.job_name}] No heartbeat recorded yet."
        gap = self.now - self.last_seen
        if self.missed:
            return (
                f"[{self.job_name}] Heartbeat missed: last seen {gap:.0f}s ago "
                f"(limit {self.interval_seconds}s)."
            )
        return f"[{self.job_name}] Heartbeat OK: last seen {gap:.0f}s ago."


def _state_path(state_dir: str, job_name: str) -> Path:
    safe = job_name.replace("/", "_").replace(" ", "_")
    return Path(state_dir) / f"{safe}.heartbeat.json"


def record_heartbeat(job_name: str, options: HeartbeatOptions) -> None:
    """Record the current time as the latest heartbeat for a job."""
    path = _state_path(options.state_dir, job_name)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"last_seen": time.time()}))


def check_heartbeat(job_name: str, options: HeartbeatOptions) -> HeartbeatResult:
    """Check whether a job has missed its expected heartbeat interval."""
    path = _state_path(options.state_dir, job_name)
    now = time.time()
    last_seen: Optional[float] = None

    if path.exists():
        try:
            data = json.loads(path.read_text())
            last_seen = float(data["last_seen"])
        except (KeyError, ValueError, json.JSONDecodeError):
            last_seen = None

    missed = last_seen is None or (now - last_seen) > options.interval_seconds
    return HeartbeatResult(
        job_name=job_name,
        last_seen=last_seen,
        now=now,
        interval_seconds=options.interval_seconds,
        missed=missed,
    )
