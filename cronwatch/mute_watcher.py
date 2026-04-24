"""MuteWatcher: check mute state before sending notifications."""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Optional

from cronwatch.mute import MuteOptions, MuteState, load_mute_state
from cronwatch.runner import JobResult


@dataclass
class MuteWatchOptions:
    mute: MuteOptions = field(default_factory=MuteOptions)
    job_name: str = ""

    def __post_init__(self) -> None:
        if not self.job_name:
            self.job_name = "default"

    @classmethod
    def from_dict(cls, d: dict) -> "MuteWatchOptions":
        raw = d.get("mute", {})
        return cls(
            mute=MuteOptions.from_dict(raw),
            job_name=str(d.get("job_name", "default")),
        )


def check_mute(opts: MuteWatchOptions) -> Optional[MuteState]:
    """Return the active MuteState if the job is currently muted, else None."""
    if not opts.mute.enabled:
        return None
    state = load_mute_state(opts.mute.state_dir, opts.job_name)
    if state.muted_until is not None and time.time() < state.muted_until:
        return state
    return None


def format_mute_notice(state: MuteState, job_name: str) -> str:
    remaining = max(0, int((state.muted_until or 0) - time.time()))
    reason_part = f" Reason: {state.reason}." if state.reason else ""
    return (
        f"[cronwatch] Notifications for '{job_name}' are muted "
        f"for {remaining}s.{reason_part}"
    )
