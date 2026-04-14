"""Concurrency guard: limit how many instances of a job run simultaneously."""
from __future__ import annotations

import os
import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import List

_STATE_DIR = Path(os.environ.get("CRONWATCH_STATE_DIR", "~/.cronwatch/concurrency")).expanduser()


@dataclass
class ConcurrencyOptions:
    enabled: bool = False
    max_instances: int = 1
    state_dir: Path = _STATE_DIR

    @classmethod
    def from_dict(cls, data: dict) -> "ConcurrencyOptions":
        return cls(
            enabled=bool(data.get("enabled", False)),
            max_instances=int(data.get("max_instances", 1)),
            state_dir=Path(data.get("state_dir", _STATE_DIR)).expanduser(),
        )


@dataclass
class ConcurrencyResult:
    allowed: bool
    active_pids: List[int] = field(default_factory=list)
    reason: str = ""

    @property
    def ok(self) -> bool:
        return self.allowed

    def summary(self) -> str:
        if self.allowed:
            return f"concurrency ok ({len(self.active_pids)} active)"
        return f"concurrency denied: {self.reason}"


def _slot_path(state_dir: Path, job_name: str) -> Path:
    safe = job_name.replace("/", "_").replace(" ", "_")
    return state_dir / f"{safe}.json"


def _live_pids(pids: List[int]) -> List[int]:
    """Return only PIDs that are still running."""
    alive = []
    for pid in pids:
        try:
            os.kill(pid, 0)
            alive.append(pid)
        except (ProcessLookupError, PermissionError):
            pass
    return alive


def acquire_slot(job_name: str, opts: ConcurrencyOptions) -> ConcurrencyResult:
    """Try to acquire a concurrency slot for *job_name*."""
    if not opts.enabled:
        return ConcurrencyResult(allowed=True, reason="disabled")

    opts.state_dir.mkdir(parents=True, exist_ok=True)
    path = _slot_path(opts.state_dir, job_name)

    existing: List[int] = []
    if path.exists():
        try:
            existing = json.loads(path.read_text()).get("pids", [])
        except (json.JSONDecodeError, KeyError):
            existing = []

    live = _live_pids(existing)

    if len(live) >= opts.max_instances:
        return ConcurrencyResult(allowed=False, active_pids=live,
                                 reason=f"max_instances={opts.max_instances} reached")

    live.append(os.getpid())
    path.write_text(json.dumps({"pids": live, "updated": time.time()}))
    return ConcurrencyResult(allowed=True, active_pids=live)


def release_slot(job_name: str, opts: ConcurrencyOptions) -> None:
    """Remove the current PID from the concurrency slot file."""
    if not opts.enabled:
        return
    path = _slot_path(opts.state_dir, job_name)
    if not path.exists():
        return
    try:
        data = json.loads(path.read_text())
        pids = [p for p in data.get("pids", []) if p != os.getpid()]
        path.write_text(json.dumps({"pids": pids, "updated": time.time()}))
    except (json.JSONDecodeError, OSError):
        pass
