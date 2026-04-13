"""Snapshot module: capture and compare cron job output across runs."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

DEFAULT_SNAPSHOT_DIR = Path(".cronwatch") / "snapshots"


@dataclass
class Snapshot:
    command: str
    stdout_hash: str
    captured_at: str
    stdout_preview: str  # first 200 chars

    def to_dict(self) -> dict:
        return {
            "command": self.command,
            "stdout_hash": self.stdout_hash,
            "captured_at": self.captured_at,
            "stdout_preview": self.stdout_preview,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Snapshot":
        return cls(
            command=data["command"],
            stdout_hash=data["stdout_hash"],
            captured_at=data["captured_at"],
            stdout_preview=data.get("stdout_preview", ""),
        )


def _snapshot_path(command: str, base_dir: Path = DEFAULT_SNAPSHOT_DIR) -> Path:
    key = hashlib.md5(command.encode()).hexdigest()[:12]
    return base_dir / f"{key}.json"


def _hash_output(stdout -> str:
    return hashlib.sha256(stdout.encode()).hexdigest()


def save_snapshot(
    command: str,
    stdout: str,
    base_dir: Path = DEFAULT_SNAPSHOT_DIR,
) -> Snapshot:
    """Persist a snapshot of the job's stdout."""
    path = _snapshot_path(command, base_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    snap = Snapshot(
        command=command,
        stdout_hash=_hash_output(stdout),
        captured_at=datetime.now(timezone.utc).isoformat(),
        stdout_preview=stdout[:200],
    )
    path.write_text(json.dumps(snap.to_dict(), indent=2))
    return snap


def load_snapshot(
    command: str,
    base_dir: Path = DEFAULT_SNAPSHOT_DIR,
) -> Optional[Snapshot]:
    """Load the most recent snapshot for a command, or None if absent."""
    path = _snapshot_path(command, base_dir)
    if not path.exists():
        return None
    data = json.loads(path.read_text())
    return Snapshot.from_dict(data)


def output_changed(command: str, stdout: str, base_dir: Path = DEFAULT_SNAPSHOT_DIR) -> bool:
    """Return True if stdout differs from the last saved snapshot."""
    existing = load_snapshot(command, base_dir)
    if existing is None:
        return True
    return existing.stdout_hash != _hash_output(stdout)
