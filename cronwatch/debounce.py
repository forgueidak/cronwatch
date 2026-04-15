"""Debounce: suppress repeated notifications until a quiet period has elapsed."""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class DebounceOptions:
    enabled: bool = False
    window_seconds: int = 300  # suppress repeat alerts within this window
    state_dir: str = "/var/lib/cronwatch/debounce"

    @classmethod
    def from_dict(cls, data: dict) -> "DebounceOptions":
        return cls(
            enabled=bool(data.get("enabled", False)),
            window_seconds=int(data.get("window_seconds", 300)),
            state_dir=str(data.get("state_dir", "/var/lib/cronwatch/debounce")),
        )


@dataclass
class DebounceState:
    last_notified_at: Optional[float] = None
    suppressed_count: int = 0


@dataclass
class DebounceResult:
    suppressed: bool
    last_notified_at: Optional[float]
    suppressed_count: int

    def ok(self) -> bool:
        """Return True when the notification should proceed (not suppressed)."""
        return not self.suppressed

    def summary(self) -> str:
        if self.suppressed:
            return (
                f"Notification suppressed (debounce). "
                f"Total suppressed: {self.suppressed_count}."
            )
        return "Notification allowed by debounce."


def _state_path(state_dir: str, job_name: str) -> Path:
    safe = job_name.replace("/", "_").replace(" ", "_")
    return Path(state_dir) / f"{safe}.json"


def load_debounce_state(state_dir: str, job_name: str) -> DebounceState:
    path = _state_path(state_dir, job_name)
    if not path.exists():
        return DebounceState()
    try:
        data = json.loads(path.read_text())
        return DebounceState(
            last_notified_at=data.get("last_notified_at"),
            suppressed_count=int(data.get("suppressed_count", 0)),
        )
    except (json.JSONDecodeError, OSError):
        return DebounceState()


def save_debounce_state(state_dir: str, job_name: str, state: DebounceState) -> None:
    path = _state_path(state_dir, job_name)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({
        "last_notified_at": state.last_notified_at,
        "suppressed_count": state.suppressed_count,
    }))


def check_debounce(
    opts: DebounceOptions,
    job_name: str,
    now: Optional[float] = None,
) -> DebounceResult:
    """Return a DebounceResult indicating whether a notification should fire."""
    if not opts.enabled:
        return DebounceResult(suppressed=False, last_notified_at=None, suppressed_count=0)

    now = now if now is not None else time.time()
    state = load_debounce_state(opts.state_dir, job_name)

    if (
        state.last_notified_at is not None
        and (now - state.last_notified_at) < opts.window_seconds
    ):
        state.suppressed_count += 1
        save_debounce_state(opts.state_dir, job_name, state)
        return DebounceResult(
            suppressed=True,
            last_notified_at=state.last_notified_at,
            suppressed_count=state.suppressed_count,
        )

    # Allow notification and record the timestamp
    state.last_notified_at = now
    state.suppressed_count = 0
    save_debounce_state(opts.state_dir, job_name, state)
    return DebounceResult(
        suppressed=False,
        last_notified_at=now,
        suppressed_count=0,
    )
