"""Watcher integration for the pause/resume feature."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from cronwatch.pause import PauseOptions, is_paused, load_pause_state


@dataclass
class PauseWatchOptions:
    enabled: bool = True
    state_dir: str = ""
    _opts: PauseOptions = field(init=False)

    def __post_init__(self) -> None:
        self._opts = PauseOptions(
            enabled=self.enabled,
            state_dir=self.state_dir or PauseOptions().state_dir,
        )

    @classmethod
    def from_dict(cls, data: dict) -> "PauseWatchOptions":
        nested = data.get("pause", data)
        return cls(
            enabled=bool(nested.get("enabled", True)),
            state_dir=str(nested.get("state_dir", "")),
        )


def check_pause(job_name: str, opts: Optional[PauseWatchOptions] = None) -> bool:
    """Return True if the job should be skipped due to pause state."""
    if opts is None:
        opts = PauseWatchOptions()
    if not opts.enabled:
        return False
    return is_paused(job_name, opts._opts.state_dir)


def format_pause_notice(job_name: str, opts: Optional[PauseWatchOptions] = None) -> str:
    """Return a human-readable notice string for a paused job."""
    if opts is None:
        opts = PauseWatchOptions()
    state = load_pause_state(job_name, opts._opts.state_dir)
    parts = [f"Job '{job_name}' is paused."]
    if state.reason:
        parts.append(f"Reason: {state.reason}")
    if state.resume_after:
        parts.append(f"Resumes after: {state.resume_after}")
    return " ".join(parts)
