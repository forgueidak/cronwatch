"""Alert throttling and deduplication for cronwatch notifications."""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

_DEFAULT_THROTTLE_SECONDS = 3600  # 1 hour


@dataclass
class AlertState:
    job_name: str
    last_alerted_at: float
    consecutive_failures: int = 1


def _state_path(state_dir: Path, job_name: str) -> Path:
    safe = job_name.replace("/", "_").replace(" ", "_")
    return state_dir / f"{safe}.alert.json"


def load_alert_state(state_dir: Path, job_name: str) -> Optional[AlertState]:
    """Load persisted alert state for a job, or None if not found."""
    path = _state_path(state_dir, job_name)
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text())
        return AlertState(
            job_name=data["job_name"],
            last_alerted_at=float(data["last_alerted_at"]),
            consecutive_failures=int(data.get("consecutive_failures", 1)),
        )
    except (KeyError, ValueError, json.JSONDecodeError):
        return None


def save_alert_state(state_dir: Path, state: AlertState) -> None:
    """Persist alert state for a job."""
    state_dir.mkdir(parents=True, exist_ok=True)
    path = _state_path(state_dir, state.job_name)
    path.write_text(
        json.dumps({
            "job_name": state.job_name,
            "last_alerted_at": state.last_alerted_at,
            "consecutive_failures": state.consecutive_failures,
        })
    )


def clear_alert_state(state_dir: Path, job_name: str) -> None:
    """Remove alert state when a job recovers."""
    path = _state_path(state_dir, job_name)
    if path.exists():
        path.unlink()


def should_alert(
    state_dir: Path,
    job_name: str,
    failed: bool,
    throttle_seconds: int = _DEFAULT_THROTTLE_SECONDS,
) -> tuple[bool, AlertState | None]:
    """Determine whether an alert should fire.

    Returns (alert_now, updated_state). Caller must call save_alert_state
    or clear_alert_state based on the result.
    """
    now = time.time()
    existing = load_alert_state(state_dir, job_name)

    if not failed:
        return False, None

    if existing is None:
        new_state = AlertState(job_name=job_name, last_alerted_at=now, consecutive_failures=1)
        return True, new_state

    elapsed = now - existing.last_alerted_at
    new_state = AlertState(
        job_name=job_name,
        last_alerted_at=now if elapsed >= throttle_seconds else existing.last_alerted_at,
        consecutive_failures=existing.consecutive_failures + 1,
    )
    return elapsed >= throttle_seconds, new_state
