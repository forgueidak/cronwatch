"""Rate limiting for notifications to prevent alert storms."""
from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

_STATE_DIR = Path.home() / ".cronwatch" / "ratelimit"


@dataclass
class RateLimitOptions:
    enabled: bool = True
    max_per_hour: int = 5
    max_per_day: int = 20
    window_seconds: int = 3600  # 1 hour


@dataclass
class RateLimitState:
    job_name: str
    timestamps: list[float] = field(default_factory=list)

    def prune(self, window_seconds: int) -> None:
        """Remove timestamps older than the window."""
        cutoff = time.time() - window_seconds
        self.timestamps = [t for t in self.timestamps if t >= cutoff]

    def count_in_window(self, window_seconds: int) -> int:
        self.prune(window_seconds)
        return len(self.timestamps)

    def record(self) -> None:
        self.timestamps.append(time.time())


def _state_path(job_name: str, state_dir: Optional[Path] = None) -> Path:
    base = state_dir or _STATE_DIR
    safe = job_name.replace("/", "_").replace(" ", "_")
    return base / f"{safe}.ratelimit.json"


def load_rate_limit_state(job_name: str, state_dir: Optional[Path] = None) -> RateLimitState:
    path = _state_path(job_name, state_dir)
    if not path.exists():
        return RateLimitState(job_name=job_name)
    try:
        data = json.loads(path.read_text())
        return RateLimitState(
            job_name=data.get("job_name", job_name),
            timestamps=data.get("timestamps", []),
        )
    except (json.JSONDecodeError, KeyError):
        return RateLimitState(job_name=job_name)


def save_rate_limit_state(state: RateLimitState, state_dir: Optional[Path] = None) -> None:
    path = _state_path(state.job_name, state_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"job_name": state.job_name, "timestamps": state.timestamps}))


def is_allowed(
    job_name: str,
    opts: RateLimitOptions,
    state_dir: Optional[Path] = None,
) -> bool:
    """Return True if a notification is allowed under the current rate limit."""
    if not opts.enabled:
        return True
    state = load_rate_limit_state(job_name, state_dir)
    hourly = state.count_in_window(opts.window_seconds)
    if hourly >= opts.max_per_hour:
        return False
    daily = state.count_in_window(86400)
    if daily >= opts.max_per_day:
        return False
    state.record()
    save_rate_limit_state(state, state_dir)
    return True
