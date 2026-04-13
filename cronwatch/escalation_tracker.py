"""Track consecutive failure counts per job to drive escalation decisions."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Dict

from cronwatch.runner import JobResult

_DEFAULT_DIR = Path.home() / ".cronwatch" / "escalation"


def _state_path(job_name: str, state_dir: Path = _DEFAULT_DIR) -> Path:
    safe = job_name.replace("/", "_").replace(" ", "_")
    return state_dir / f"{safe}.json"


def load_consecutive_failures(
    job_name: str,
    state_dir: Path = _DEFAULT_DIR,
) -> int:
    path = _state_path(job_name, state_dir)
    if not path.exists():
        return 0
    try:
        data: Dict = json.loads(path.read_text())
        return int(data.get("consecutive_failures", 0))
    except (json.JSONDecodeError, ValueError):
        return 0


def save_consecutive_failures(
    job_name: str,
    count: int,
    state_dir: Path = _DEFAULT_DIR,
) -> None:
    path = _state_path(job_name, state_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"consecutive_failures": count}))


def reset_consecutive_failures(
    job_name: str,
    state_dir: Path = _DEFAULT_DIR,
) -> None:
    path = _state_path(job_name, state_dir)
    if path.exists():
        path.unlink()


def update_consecutive_failures(
    job_name: str,
    result: JobResult,
    state_dir: Path = _DEFAULT_DIR,
) -> int:
    """Increment on failure, reset on success. Returns the updated count."""
    if result.success:
        reset_consecutive_failures(job_name, state_dir)
        return 0
    count = load_consecutive_failures(job_name, state_dir) + 1
    save_consecutive_failures(job_name, count, state_dir)
    return count
