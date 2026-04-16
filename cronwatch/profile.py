"""Job profiling: track and compare execution duration over time."""
from __future__ import annotations

import json
import statistics
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

from cronwatch.runner import JobResult

_DEFAULT_DIR = Path(".cronwatch/profiles")


@dataclass
class ProfileOptions:
    enabled: bool = False
    directory: Path = _DEFAULT_DIR
    window: int = 20  # number of recent runs to consider
    warn_factor: float = 2.0  # alert if duration > mean * factor

    @classmethod
    def from_dict(cls, d: dict) -> "ProfileOptions":
        return cls(
            enabled=bool(d.get("enabled", False)),
            directory=Path(d.get("directory", _DEFAULT_DIR)),
            window=int(d.get("window", 20)),
            warn_factor=float(d.get("warn_factor", 2.0)),
        )


@dataclass
class ProfileResult:
    slow: bool
    duration: float
    mean: Optional[float]
    threshold: Optional[float]
    message: str

    def ok(self) -> bool:
        return not self.slow


def _profile_path(directory: Path, command: str) -> Path:
    safe = command.replace("/", "_").replace(" ", "_")[:64]
    return directory / f"{safe}.jsonl"


def load_durations(directory: Path, command: str, window: int) -> List[float]:
    path = _profile_path(directory, command)
    if not path.exists():
        return []
    lines = path.read_text().splitlines()
    entries = []
    for line in lines[-window:]:
        try:
            entries.append(float(json.loads(line)["duration"]))
        except (KeyError, ValueError, json.JSONDecodeError):
            continue
    return entries


def record_duration(directory: Path, command: str, duration: float) -> None:
    path = _profile_path(directory, command)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a") as f:
        f.write(json.dumps({"duration": duration}) + "\n")


def check_profile(result: JobResult, opts: ProfileOptions) -> Optional[ProfileResult]:
    if not opts.enabled or not result.success:
        return None
    duration = result.duration
    record_duration(opts.directory, result.command, duration)
    history = load_durations(opts.directory, result.command, opts.window)
    if len(history) < 2:
        return ProfileResult(slow=False, duration=duration, mean=None, threshold=None,
                             message="Not enough history to profile.")
    mean = statistics.mean(history)
    threshold = mean * opts.warn_factor
    slow = duration > threshold
    msg = (f"Duration {duration:.2f}s exceeds threshold {threshold:.2f}s (mean={mean:.2f}s)"
           if slow else f"Duration {duration:.2f}s within normal range (mean={mean:.2f}s)")
    return ProfileResult(slow=slow, duration=duration, mean=mean, threshold=threshold, message=msg)
