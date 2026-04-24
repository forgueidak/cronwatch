"""drain.py – graceful shutdown / drain support for cronwatch.

Allows a job run to be marked as "draining" so that new executions are
blocked while an in-flight run is allowed to finish cleanly.
"""
from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class DrainOptions:
    enabled: bool = False
    state_dir: str = "/tmp/cronwatch/drain"
    drain_timeout_seconds: int = 300

    @classmethod
    def from_dict(cls, data: dict) -> "DrainOptions":
        d = data.get("drain", {})
        return cls(
            enabled=bool(d.get("enabled", False)),
            state_dir=str(d.get("state_dir", "/tmp/cronwatch/drain")),
            drain_timeout_seconds=int(d.get("drain_timeout_seconds", 300)),
        )


@dataclass
class DrainState:
    draining: bool = False
    started_at: Optional[float] = None
    job_name: str = ""

    def to_dict(self) -> dict:
        return {
            "draining": self.draining,
            "started_at": self.started_at,
            "job_name": self.job_name,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "DrainState":
        return cls(
            draining=bool(data.get("draining", False)),
            started_at=data.get("started_at"),
            job_name=str(data.get("job_name", "")),
        )


def _state_path(state_dir: str, job_name: str) -> Path:
    safe = job_name.replace("/", "_").replace(" ", "_")
    return Path(state_dir) / f"{safe}.drain.json"


def load_drain_state(state_dir: str, job_name: str) -> DrainState:
    path = _state_path(state_dir, job_name)
    if not path.exists():
        return DrainState()
    try:
        return DrainState.from_dict(json.loads(path.read_text()))
    except (json.JSONDecodeError, OSError):
        return DrainState()


def save_drain_state(state_dir: str, job_name: str, state: DrainState) -> None:
    path = _state_path(state_dir, job_name)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state.to_dict()))


def clear_drain_state(state_dir: str, job_name: str) -> None:
    path = _state_path(state_dir, job_name)
    if path.exists():
        path.unlink()


def is_draining(opts: DrainOptions, job_name: str) -> bool:
    """Return True if the job is currently in drain mode."""
    if not opts.enabled:
        return False
    state = load_drain_state(opts.state_dir, job_name)
    if not state.draining:
        return False
    if state.started_at is None:
        return True
    elapsed = time.time() - state.started_at
    if elapsed > opts.drain_timeout_seconds:
        clear_drain_state(opts.state_dir, job_name)
        return False
    return True


def begin_drain(opts: DrainOptions, job_name: str) -> None:
    """Mark a job as draining."""
    state = DrainState(draining=True, started_at=time.time(), job_name=job_name)
    save_drain_state(opts.state_dir, job_name, state)


def end_drain(opts: DrainOptions, job_name: str) -> None:
    """Clear drain state after job completes."""
    clear_drain_state(opts.state_dir, job_name)
