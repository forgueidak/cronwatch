"""Alert throttling: suppress repeated notifications within a cooldown window."""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class ThrottleOptions:
    cooldown_seconds: int = 3600  # default: 1 hour between repeated alerts
    state_dir: str = "/tmp/cronwatch/throttle"


@dataclass
class ThrottleState:
    job_name: str
    last_alerted_at: float = field(default_factory=time.time)


def _state_path(job_name: str, state_dir: str) -> Path:
    safe = job_name.replace("/", "_").replace(" ", "_")
    return Path(state_dir) / f"{safe}.json"


def load_throttle_state(job_name: str, state_dir: str) -> Optional[ThrottleState]:
    path = _state_path(job_name, state_dir)
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text())
        return ThrottleState(
            job_name=data["job_name"],
            last_alerted_at=float(data["last_alerted_at"]),
        )
    except (KeyError, ValueError, json.JSONDecodeError):
        return None


def save_throttle_state(job_name: str, state_dir: str) -> ThrottleState:
    path = _state_path(job_name, state_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    state = ThrottleState(job_name=job_name, last_alerted_at=time.time())
    path.write_text(json.dumps({"job_name": state.job_name, "last_alerted_at": state.last_alerted_at}))
    return state


def clear_throttle_state(job_name: str, state_dir: str) -> None:
    path = _state_path(job_name, state_dir)
    if path.exists():
        path.unlink()


def is_throttled(job_name: str, options: ThrottleOptions) -> bool:
    """Return True if an alert for job_name was sent within the cooldown window."""
    state = load_throttle_state(job_name, options.state_dir)
    if state is None:
        return False
    elapsed = time.time() - state.last_alerted_at
    return elapsed < options.cooldown_seconds


def record_alert(job_name: str, options: ThrottleOptions) -> ThrottleState:
    """Persist that an alert was just sent for job_name."""
    return save_throttle_state(job_name, options.state_dir)
