"""Job history tracking: persist and query past job results."""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

from cronwatch.runner import JobResult

_DEFAULT_HISTORY_FILE = ".cronwatch_history.jsonl"


def _history_path(history_file: Optional[str] = None) -> Path:
    """Return the resolved path to the history file."""
    return Path(history_file or os.environ.get("CRONWATCH_HISTORY", _DEFAULT_HISTORY_FILE))


def record_result(result: JobResult, history_file: Optional[str] = None) -> None:
    """Append a JobResult to the history file as a JSONL entry."""
    path = _history_path(history_file)
    path.parent.mkdir(parents=True, exist_ok=True)
    entry = {
        "command": result.command,
        "exit_code": result.exit_code,
        "stdout": result.stdout,
        "stderr": result.stderr,
        "duration": result.duration,
        "timed_out": result.timed_out,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry) + "\n")


def load_history(
    command: Optional[str] = None,
    limit: int = 50,
    history_file: Optional[str] = None,
) -> List[dict]:
    """Load past job entries, optionally filtered by command, newest first."""
    path = _history_path(history_file)
    if not path.exists():
        return []

    entries: List[dict] = []
    with path.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                continue
            if command is None or entry.get("command") == command:
                entries.append(entry)

    return list(reversed(entries))[:limit]


def last_failure(
    command: str, history_file: Optional[str] = None
) -> Optional[dict]:
    """Return the most recent failed entry for *command*, or None."""
    for entry in load_history(command=command, history_file=history_file):
        if entry.get("exit_code") != 0 or entry.get("timed_out"):
            return entry
    return None
