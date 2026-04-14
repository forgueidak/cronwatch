"""runlog.py — Track per-job run counts and last-run timestamps."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from cronwatch.runner import JobResult

_DEFAULT_DIR = Path(os.environ.get("CRONWATCH_STATE_DIR", "~/.cronwatch/state")).expanduser()


@dataclass
class RunLogEntry:
    command: str
    run_count: int = 0
    success_count: int = 0
    failure_count: int = 0
    last_run: Optional[str] = None  # ISO-8601
    last_status: Optional[str] = None  # "success" | "failure"

    def to_dict(self) -> dict:
        return {
            "command": self.command,
            "run_count": self.run_count,
            "success_count": self.success_count,
            "failure_count": self.failure_count,
            "last_run": self.last_run,
            "last_status": self.last_status,
        }

    @staticmethod
    def from_dict(data: dict) -> "RunLogEntry":
        return RunLogEntry(
            command=data.get("command", ""),
            run_count=int(data.get("run_count", 0)),
            success_count=int(data.get("success_count", 0)),
            failure_count=int(data.get("failure_count", 0)),
            last_run=data.get("last_run"),
            last_status=data.get("last_status"),
        )


def _runlog_path(command: str, state_dir: Path = _DEFAULT_DIR) -> Path:
    safe = command.replace("/", "_").replace(" ", "_")[:64]
    return state_dir / "runlog" / f"{safe}.json"


def load_run_log(command: str, state_dir: Path = _DEFAULT_DIR) -> RunLogEntry:
    path = _runlog_path(command, state_dir)
    if not path.exists():
        return RunLogEntry(command=command)
    try:
        data = json.loads(path.read_text())
        return RunLogEntry.from_dict(data)
    except (json.JSONDecodeError, KeyError):
        return RunLogEntry(command=command)


def save_run_log(entry: RunLogEntry, state_dir: Path = _DEFAULT_DIR) -> None:
    path = _runlog_path(entry.command, state_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(entry.to_dict(), indent=2))


def update_run_log(result: JobResult, state_dir: Path = _DEFAULT_DIR) -> RunLogEntry:
    """Load, update, and persist the run log for the job described by *result*."""
    entry = load_run_log(result.command, state_dir)
    entry.run_count += 1
    entry.last_run = datetime.now(timezone.utc).isoformat()
    if result.returncode == 0:
        entry.success_count += 1
        entry.last_status = "success"
    else:
        entry.failure_count += 1
        entry.last_status = "failure"
    save_run_log(entry, state_dir)
    return entry
