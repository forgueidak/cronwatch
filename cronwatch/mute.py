"""Mute: temporarily silence notifications for a job without pausing execution."""
from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class MuteOptions:
    enabled: bool = False
    state_dir: str = "/tmp/cronwatch/mute"

    @classmethod
    def from_dict(cls, d: dict) -> "MuteOptions":
        return cls(
            enabled=bool(d.get("enabled", False)),
            state_dir=str(d.get("state_dir", "/tmp/cronwatch/mute")),
        )


@dataclass
class MuteState:
    muted_until: Optional[float] = None  # epoch seconds
    reason: str = ""

    def to_dict(self) -> dict:
        return {"muted_until": self.muted_until, "reason": self.reason}

    @classmethod
    def from_dict(cls, d: dict) -> "MuteState":
        return cls(
            muted_until=d.get("muted_until"),
            reason=d.get("reason", ""),
        )


def _state_path(state_dir: str, job_name: str) -> str:
    safe = job_name.replace("/", "_").replace(" ", "_")
    return os.path.join(state_dir, f"{safe}.mute.json")


def load_mute_state(state_dir: str, job_name: str) -> MuteState:
    path = _state_path(state_dir, job_name)
    if not os.path.exists(path):
        return MuteState()
    with open(path) as fh:
        return MuteState.from_dict(json.load(fh))


def save_mute_state(state_dir: str, job_name: str, state: MuteState) -> None:
    path = _state_path(state_dir, job_name)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as fh:
        json.dump(state.to_dict(), fh)


def clear_mute_state(state_dir: str, job_name: str) -> None:
    path = _state_path(state_dir, job_name)
    if os.path.exists(path):
        os.remove(path)


def is_muted(state_dir: str, job_name: str) -> bool:
    """Return True if the job is currently muted."""
    state = load_mute_state(state_dir, job_name)
    if state.muted_until is None:
        return False
    return time.time() < state.muted_until


def mute_job(state_dir: str, job_name: str, duration_seconds: int, reason: str = "") -> MuteState:
    """Mute a job for *duration_seconds* seconds."""
    state = MuteState(muted_until=time.time() + duration_seconds, reason=reason)
    save_mute_state(state_dir, job_name, state)
    return state
