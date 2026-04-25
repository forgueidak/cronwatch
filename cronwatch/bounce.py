"""bounce.py — detect rapid job state changes (flapping) and suppress noise."""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

from cronwatch.runner import JobResult


@dataclass
class BounceOptions:
    enabled: bool = False
    window_seconds: int = 300
    min_flaps: int = 3
    state_dir: str = "/tmp/cronwatch/bounce"

    @classmethod
    def from_dict(cls, data: dict) -> "BounceOptions":
        d = data.get("bounce", {})
        return cls(
            enabled=bool(d.get("enabled", False)),
            window_seconds=int(d.get("window_seconds", 300)),
            min_flaps=int(d.get("min_flaps", 3)),
            state_dir=str(d.get("state_dir", "/tmp/cronwatch/bounce")),
        )


@dataclass
class BounceState:
    transitions: List[float] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {"transitions": self.transitions}

    @classmethod
    def from_dict(cls, data: dict) -> "BounceState":
        return cls(transitions=list(data.get("transitions", [])))


@dataclass
class BounceResult:
    flapping: bool
    flap_count: int
    message: str

    def ok(self) -> bool:
        return not self.flapping

    def summary(self) -> str:
        return self.message


def _state_path(state_dir: str, job_name: str) -> Path:
    safe = job_name.replace("/", "_").replace(" ", "_")
    return Path(state_dir) / f"{safe}.bounce.json"


def load_bounce_state(state_dir: str, job_name: str) -> BounceState:
    path = _state_path(state_dir, job_name)
    if not path.exists():
        return BounceState()
    try:
        return BounceState.from_dict(json.loads(path.read_text()))
    except Exception:
        return BounceState()


def save_bounce_state(state_dir: str, job_name: str, state: BounceState) -> None:
    path = _state_path(state_dir, job_name)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state.to_dict()))


def check_bounce(
    result: JobResult,
    opts: BounceOptions,
    *,
    _now: Optional[float] = None,
) -> Optional[BounceResult]:
    """Record a state transition and return a BounceResult if flapping is detected."""
    if not opts.enabled:
        return None

    now = _now if _now is not None else datetime.now(timezone.utc).timestamp()
    cutoff = now - opts.window_seconds

    job_name = result.command
    state = load_bounce_state(opts.state_dir, job_name)

    state.transitions.append(now)
    state.transitions = [t for t in state.transitions if t >= cutoff]

    save_bounce_state(opts.state_dir, job_name, state)

    flap_count = len(state.transitions)
    flapping = flap_count >= opts.min_flaps
    msg = (
        f"Job '{job_name}' is flapping: {flap_count} transitions in "
        f"{opts.window_seconds}s window."
        if flapping
        else f"Job '{job_name}' stable: {flap_count} transitions recorded."
    )
    return BounceResult(flapping=flapping, flap_count=flap_count, message=msg)
