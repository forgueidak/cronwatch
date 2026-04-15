"""Checkpoint support: persist and restore a job's last successful run timestamp."""
from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from cronwatch.runner import JobResult

_DEFAULT_DIR = Path(os.environ.get("CRONWATCH_STATE_DIR", "~/.cronwatch/checkpoints"))


@dataclass
class CheckpointOptions:
    enabled: bool = False
    state_dir: Path = _DEFAULT_DIR

    @classmethod
    def from_dict(cls, data: dict) -> "CheckpointOptions":
        raw_dir = data.get("state_dir", str(_DEFAULT_DIR))
        return cls(
            enabled=bool(data.get("enabled", False)),
            state_dir=Path(raw_dir),
        )


@dataclass
class CheckpointResult:
    updated: bool
    last_success: Optional[datetime]

    @property
    def ok(self) -> bool:
        return self.updated or self.last_success is not None

    def summary(self) -> str:
        if self.updated:
            return f"Checkpoint updated at {self.last_success.isoformat()}"
        if self.last_success:
            return f"Last checkpoint: {self.last_success.isoformat()}"
        return "No checkpoint recorded yet"


def _checkpoint_path(state_dir: Path, command: str) -> Path:
    safe = command.replace("/", "_").replace(" ", "_")[:64]
    return Path(state_dir).expanduser() / f"{safe}.checkpoint.json"


def load_checkpoint(state_dir: Path, command: str) -> Optional[datetime]:
    path = _checkpoint_path(state_dir, command)
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text())
        ts = data.get("last_success")
        if ts:
            return datetime.fromisoformat(ts)
    except (json.JSONDecodeError, KeyError, ValueError):
        return None
    return None


def save_checkpoint(state_dir: Path, command: str, ts: datetime) -> None:
    path = _checkpoint_path(state_dir, command)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"command": command, "last_success": ts.isoformat()}))


def update_checkpoint(result: JobResult, opts: CheckpointOptions) -> CheckpointResult:
    """Record a checkpoint if the job succeeded; always return the last known timestamp."""
    if not opts.enabled:
        last = load_checkpoint(opts.state_dir, result.command)
        return CheckpointResult(updated=False, last_success=last)

    last = load_checkpoint(opts.state_dir, result.command)
    if result.success:
        now = datetime.now(timezone.utc)
        save_checkpoint(opts.state_dir, result.command, now)
        return CheckpointResult(updated=True, last_success=now)

    return CheckpointResult(updated=False, last_success=last)
