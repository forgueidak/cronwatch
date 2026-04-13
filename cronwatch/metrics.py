"""Lightweight in-process metrics collection for cronwatch job runs."""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional


@dataclass
class MetricPoint:
    command: str
    success: bool
    duration: float
    timestamp: float = field(default_factory=time.time)
    exit_code: int = 0
    tags: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "command": self.command,
            "success": self.success,
            "duration": self.duration,
            "timestamp": self.timestamp,
            "exit_code": self.exit_code,
            "tags": self.tags,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "MetricPoint":
        return cls(
            command=data["command"],
            success=data["success"],
            duration=data["duration"],
            timestamp=data.get("timestamp", 0.0),
            exit_code=data.get("exit_code", 0),
            tags=data.get("tags", []),
        )


@dataclass
class MetricsSummary:
    command: str
    total: int
    successes: int
    failures: int
    avg_duration: float
    min_duration: float
    max_duration: float

    @property
    def success_rate(self) -> float:
        return (self.successes / self.total * 100) if self.total else 0.0


def _metrics_path(metrics_dir: Path, command: str) -> Path:
    safe = command.replace("/", "_").replace(" ", "_").strip("_")
    return metrics_dir / f"{safe}.jsonl"


def record_metric(point: MetricPoint, metrics_dir: Path) -> None:
    path = _metrics_path(metrics_dir, point.command)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a") as fh:
        fh.write(json.dumps(point.to_dict()) + "\n")


def load_metrics(command: str, metrics_dir: Path, limit: Optional[int] = None) -> List[MetricPoint]:
    path = _metrics_path(metrics_dir, command)
    if not path.exists():
        return []
    points: List[MetricPoint] = []
    with path.open() as fh:
        for line in fh:
            line = line.strip()
            if line:
                points.append(MetricPoint.from_dict(json.loads(line)))
    points.sort(key=lambda p: p.timestamp, reverse=True)
    return points[:limit] if limit else points


def summarize_metrics(command: str, metrics_dir: Path, limit: Optional[int] = None) -> Optional[MetricsSummary]:
    points = load_metrics(command, metrics_dir, limit=limit)
    if not points:
        return None
    durations = [p.duration for p in points]
    successes = sum(1 for p in points if p.success)
    return MetricsSummary(
        command=command,
        total=len(points),
        successes=successes,
        failures=len(points) - successes,
        avg_duration=sum(durations) / len(durations),
        min_duration=min(durations),
        max_duration=max(durations),
    )
