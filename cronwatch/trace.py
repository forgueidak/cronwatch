"""Execution trace: record per-run timing spans for a job."""
from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

from cronwatch.runner import JobResult


@dataclass
class TraceSpan:
    name: str
    started_at: float
    ended_at: float

    @property
    def duration_ms(self) -> float:
        return round((self.ended_at - self.started_at) * 1000, 2)

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "started_at": self.started_at,
            "ended_at": self.ended_at,
            "duration_ms": self.duration_ms,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "TraceSpan":
        return cls(name=d["name"], started_at=d["started_at"], ended_at=d["ended_at"])


@dataclass
class TraceOptions:
    enabled: bool = False
    trace_dir: str = "/var/log/cronwatch/traces"
    keep_last: int = 50

    @classmethod
    def from_dict(cls, d: dict) -> "TraceOptions":
        return cls(
            enabled=bool(d.get("enabled", False)),
            trace_dir=d.get("trace_dir", "/var/log/cronwatch/traces"),
            keep_last=int(d.get("keep_last", 50)),
        )


def _trace_path(trace_dir: str, command: str) -> Path:
    safe = command.replace("/", "_").replace(" ", "_")[:64]
    return Path(trace_dir) / f"{safe}.jsonl"


def record_trace(result: JobResult, spans: List[TraceSpan], opts: TraceOptions) -> Optional[Path]:
    if not opts.enabled:
        return None
    path = _trace_path(opts.trace_dir, result.command)
    path.parent.mkdir(parents=True, exist_ok=True)
    entry = {
        "command": result.command,
        "started_at": result.started_at,
        "duration_s": result.duration,
        "exit_code": result.exit_code,
        "spans": [s.to_dict() for s in spans],
    }
    with path.open("a") as fh:
        fh.write(json.dumps(entry) + "\n")
    _prune(path, opts.keep_last)
    return path


def load_traces(command: str, opts: TraceOptions) -> List[dict]:
    path = _trace_path(opts.trace_dir, command)
    if not path.exists():
        return []
    lines = path.read_text().splitlines()
    entries = []
    for line in reversed(lines):
        try:
            entries.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return entries


def _prune(path: Path, keep_last: int) -> None:
    lines = path.read_text().splitlines()
    if len(lines) > keep_last:
        path.write_text("\n".join(lines[-keep_last:]) + "\n")
