"""Cooldown: prevent a job from running again too soon after a previous run."""
from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class CooldownOptions:
    enabled: bool = False
    min_interval_seconds: int = 300  # 5 minutes default
    state_dir: str = "/tmp/cronwatch/cooldown"

    @classmethod
    def from_dict(cls, data: dict) -> "CooldownOptions":
        return cls(
            enabled=bool(data.get("enabled", False)),
            min_interval_seconds=int(data.get("min_interval_seconds", 300)),
            state_dir=str(data.get("state_dir", "/tmp/cronwatch/cooldown")),
        )


@dataclass
class CooldownResult:
    allowed: bool
    last_run_at: Optional[float]
    seconds_remaining: float = 0.0

    @property
    def ok(self) -> bool:
        return self.allowed

    def summary(self) -> str:
        if self.allowed:
            return "cooldown: job allowed to run"
        return (
            f"cooldown: job suppressed — "
            f"{self.seconds_remaining:.0f}s remaining before next allowed run"
        )


def _state_path(state_dir: str, job_name: str) -> Path:
    safe = job_name.replace("/", "_").replace(" ", "_")
    return Path(state_dir) / f"{safe}.json"


def load_last_run(state_dir: str, job_name: str) -> Optional[float]:
    path = _state_path(state_dir, job_name)
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text())
        return float(data.get("last_run_at", 0))
    except (json.JSONDecodeError, ValueError):
        return None


def save_last_run(state_dir: str, job_name: str, ts: Optional[float] = None) -> None:
    path = _state_path(state_dir, job_name)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"last_run_at": ts or time.time()}))


def check_cooldown(opts: CooldownOptions, job_name: str) -> CooldownResult:
    """Return a CooldownResult indicating whether the job may run now."""
    if not opts.enabled:
        return CooldownResult(allowed=True, last_run_at=None)

    last = load_last_run(opts.state_dir, job_name)
    if last is None:
        return CooldownResult(allowed=True, last_run_at=None)

    elapsed = time.time() - last
    if elapsed >= opts.min_interval_seconds:
        return CooldownResult(allowed=True, last_run_at=last)

    remaining = opts.min_interval_seconds - elapsed
    return CooldownResult(allowed=False, last_run_at=last, seconds_remaining=remaining)
