"""Digest report generation for cronwatch.

Builds a summary report of recent job history across all watched jobs,
suitable for periodic (e.g. daily) digest emails or Slack posts.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import List

from cronwatch.history import load_history
from cronwatch.runner import JobResult


@dataclass
class DigestEntry:
    command: str
    total_runs: int
    failures: int
    last_status: str
    last_run: str

    @property
    def success_rate(self) -> float:
        if self.total_runs == 0:
            return 0.0
        return round((self.total_runs - self.failures) / self.total_runs * 100, 1)


def build_digest(commands: List[str], log_dir: str, limit: int = 50) -> List[DigestEntry]:
    """Build a digest entry for each command using its stored history."""
    entries: List[DigestEntry] = []
    for command in commands:
        results: List[JobResult] = load_history(command, log_dir, limit=limit)
        if not results:
            continue
        failures = sum(1 for r in results if not r.success)
        latest = results[0]  # load_history returns newest-first
        entry = DigestEntry(
            command=command,
            total_runs=len(results),
            failures=failures,
            last_status="OK" if latest.success else "FAILED",
            last_run=datetime.fromtimestamp(
                latest.started_at, tz=timezone.utc
            ).strftime("%Y-%m-%d %H:%M UTC"),
        )
        entries.append(entry)
    return entries


def format_digest_text(entries: List[DigestEntry]) -> str:
    """Render digest entries as a plain-text report string."""
    if not entries:
        return "No job history available for digest."

    lines = ["=== Cronwatch Digest Report ===", ""]
    for e in entries:
        status_icon = "✅" if e.last_status == "OK" else "❌"
        lines.append(f"{status_icon} {e.command}")
        lines.append(
            f"   Runs: {e.total_runs}  |  Failures: {e.failures}  "
            f"|  Success rate: {e.success_rate}%  |  Last run: {e.last_run}"
        )
        lines.append("")
    return "\n".join(lines).rstrip()
