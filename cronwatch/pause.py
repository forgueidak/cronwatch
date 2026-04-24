"""Pause/resume support for cronwatch jobs.

Allows a job to be temporarily paused so that watcher skips execution
without removing the cron entry. State is persisted to a small JSON file.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

_DEFAULT_STATE_DIR = os.path.expanduser("~/.cronwatch/pause")


@dataclass
class PauseOptions:
    enabled: bool = True
    state_dir: str = _DEFAULT_STATE_DIR

    @classmethod
    def from_dict(cls, data: dict) -> "PauseOptions":
        return cls(
            enabled=bool(data.get("enabled", True)),
            state_dir=str(data.get("state_dir", _DEFAULT_STATE_DIR)),
        )


@dataclass
class PauseState:
    paused: bool = False
    paused_at: Optional[str] = None
    reason: str = ""
    resume_after: Optional[str] = None  # ISO-8601 datetime

    def to_dict(self) -> dict:
        return {
            "paused": self.paused,
            "paused_at": self.paused_at,
            "reason": self.reason,
            "resume_after": self.resume_after,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "PauseState":
        return cls(
            paused=bool(data.get("paused", False)),
            paused_at=data.get("paused_at"),
            reason=str(data.get("reason", "")),
            resume_after=data.get("resume_after"),
        )


def _state_path(job_name: str, state_dir: str) -> Path:
    safe = job_name.replace("/", "_").replace(" ", "_")
    return Path(state_dir) / f"{safe}.json"


def load_pause_state(job_name: str, state_dir: str = _DEFAULT_STATE_DIR) -> PauseState:
    path = _state_path(job_name, state_dir)
    if not path.exists():
        return PauseState()
    try:
        return PauseState.from_dict(json.loads(path.read_text()))
    except (json.JSONDecodeError, OSError):
        return PauseState()


def save_pause_state(job_name: str, state: PauseState, state_dir: str = _DEFAULT_STATE_DIR) -> None:
    path = _state_path(job_name, state_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state.to_dict(), indent=2))


def pause_job(job_name: str, reason: str = "", resume_after: Optional[str] = None,
              state_dir: str = _DEFAULT_STATE_DIR) -> PauseState:
    state = PauseState(
        paused=True,
        paused_at=datetime.now(timezone.utc).isoformat(),
        reason=reason,
        resume_after=resume_after,
    )
    save_pause_state(job_name, state, state_dir)
    return state


def resume_job(job_name: str, state_dir: str = _DEFAULT_STATE_DIR) -> PauseState:
    state = PauseState(paused=False)
    save_pause_state(job_name, state, state_dir)
    return state


def is_paused(job_name: str, state_dir: str = _DEFAULT_STATE_DIR) -> bool:
    """Return True if the job is currently paused (respects resume_after)."""
    state = load_pause_state(job_name, state_dir)
    if not state.paused:
        return False
    if state.resume_after:
        try:
            resume_dt = datetime.fromisoformat(state.resume_after)
            if datetime.now(timezone.utc) >= resume_dt:
                resume_job(job_name, state_dir)
                return False
        except ValueError:
            pass
    return True
