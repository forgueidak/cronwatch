"""roster.py — Track which jobs are registered and their metadata."""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Dict, List, Optional


@dataclass
class RosterEntry:
    name: str
    command: str
    schedule: str = ""
    tags: List[str] = field(default_factory=list)
    enabled: bool = True
    description: str = ""

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "RosterEntry":
        return cls(
            name=data.get("name", ""),
            command=data.get("command", ""),
            schedule=data.get("schedule", ""),
            tags=list(data.get("tags") or []),
            enabled=bool(data.get("enabled", True)),
            description=data.get("description", ""),
        )


@dataclass
class RosterOptions:
    enabled: bool = True
    roster_dir: str = "/var/lib/cronwatch/roster"

    @classmethod
    def from_dict(cls, data: dict) -> "RosterOptions":
        d = data.get("roster", data)
        return cls(
            enabled=bool(d.get("enabled", True)),
            roster_dir=str(d.get("roster_dir", "/var/lib/cronwatch/roster")),
        )


def _roster_path(roster_dir: str, job_name: str) -> Path:
    safe = job_name.replace("/", "_").replace(" ", "_")
    return Path(roster_dir) / f"{safe}.json"


def register_job(entry: RosterEntry, roster_dir: str) -> Path:
    path = _roster_path(roster_dir, entry.name)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(entry.to_dict(), indent=2))
    return path


def load_job(job_name: str, roster_dir: str) -> Optional[RosterEntry]:
    path = _roster_path(roster_dir, job_name)
    if not path.exists():
        return None
    data = json.loads(path.read_text())
    return RosterEntry.from_dict(data)


def list_jobs(roster_dir: str) -> List[RosterEntry]:
    base = Path(roster_dir)
    if not base.exists():
        return []
    entries = []
    for p in sorted(base.glob("*.json")):
        try:
            entries.append(RosterEntry.from_dict(json.loads(p.read_text())))
        except (json.JSONDecodeError, KeyError):
            continue
    return entries


def deregister_job(job_name: str, roster_dir: str) -> bool:
    path = _roster_path(roster_dir, job_name)
    if path.exists():
        path.unlink()
        return True
    return False
