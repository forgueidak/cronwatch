"""Quota enforcement: limit how many times a job may run within a time window."""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

_STATE_DIR = Path.home() / ".cronwatch" / "quota"


@dataclass
class QuotaOptions:
    enabled: bool = False
    max_runs: int = 10
    window_seconds: int = 3600
    state_dir: Path = _STATE_DIR

    @classmethod
    def from_dict(cls, data: dict) -> "QuotaOptions":
        raw = data.get("quota", {})
        return cls(
            enabled=bool(raw.get("enabled", False)),
            max_runs=int(raw.get("max_runs", 10)),
            window_seconds=int(raw.get("window_seconds", 3600)),
            state_dir=Path(raw.get("state_dir", _STATE_DIR)),
        )


@dataclass
class QuotaState:
    timestamps: List[float] = field(default_factory=list)


@dataclass
class QuotaResult:
    allowed: bool
    run_count: int
    max_runs: int
    window_seconds: int

    @property
    def ok(self) -> bool:
        return self.allowed

    def summary(self) -> str:
        if self.allowed:
            return f"Quota OK: {self.run_count}/{self.max_runs} runs in {self.window_seconds}s window"
        return f"Quota exceeded: {self.run_count}/{self.max_runs} runs in {self.window_seconds}s window"


def _state_path(state_dir: Path, job_name: str) -> Path:
    safe = job_name.replace("/", "_").replace(" ", "_")
    return state_dir / f"{safe}.json"


def load_quota_state(opts: QuotaOptions, job_name: str) -> QuotaState:
    path = _state_path(opts.state_dir, job_name)
    if not path.exists():
        return QuotaState()
    try:
        data = json.loads(path.read_text())
        return QuotaState(timestamps=data.get("timestamps", []))
    except (json.JSONDecodeError, OSError):
        return QuotaState()


def save_quota_state(opts: QuotaOptions, job_name: str, state: QuotaState) -> None:
    path = _state_path(opts.state_dir, job_name)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"timestamps": state.timestamps}))


def check_quota(opts: QuotaOptions, job_name: str, now: Optional[float] = None) -> QuotaResult:
    """Check whether the job is within its run quota. Records a timestamp if allowed."""
    if not opts.enabled:
        return QuotaResult(allowed=True, run_count=0, max_runs=opts.max_runs, window_seconds=opts.window_seconds)

    now = now if now is not None else time.time()
    cutoff = now - opts.window_seconds

    state = load_quota_state(opts, job_name)
    state.timestamps = [t for t in state.timestamps if t >= cutoff]

    run_count = len(state.timestamps)
    allowed = run_count < opts.max_runs

    if allowed:
        state.timestamps.append(now)
        save_quota_state(opts, job_name, state)

    return QuotaResult(
        allowed=allowed,
        run_count=run_count,
        max_runs=opts.max_runs,
        window_seconds=opts.window_seconds,
    )
