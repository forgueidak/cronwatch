"""Generate a human-readable summary of recent cron job activity."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import List, Optional

from cronwatch.digest import DigestEntry, build_digest, success_rate
from cronwatch.history import load_history


@dataclass
class SummaryOptions:
    job_name: str
    limit: int = 20
    since: Optional[datetime] = None


def build_summary(options: SummaryOptions) -> List[DigestEntry]:
    """Load history for a job and return digest entries up to *limit*."""
    history = load_history(options.job_name)
    if options.since is not None:
        since_ts = options.since.timestamp()
        history = [e for e in history if e.get("timestamp", 0) >= since_ts]
    history = history[: options.limit]
    return build_digest(history)


def format_summary_text(entries: List[DigestEntry], job_name: str) -> str:
    """Render a plain-text summary table for *job_name*."""
    if not entries:
        return f"No history found for job '{job_name}'."

    rate = success_rate(entries)
    lines: List[str] = [
        f"Summary for: {job_name}",
        f"Entries shown: {len(entries)}  |  Success rate: {rate:.0%}",
        "-" * 60,
        f"{'Timestamp':<22} {'Status':<10} {'Duration':>10}  Command",
        "-" * 60,
    ]

    for entry in entries:
        ts = datetime.fromtimestamp(entry.timestamp, tz=timezone.utc).strftime(
            "%Y-%m-%d %H:%M:%S"
        )
        status = "OK" if entry.success else "FAIL"
        duration = f"{entry.duration:.2f}s"
        cmd = entry.command if len(entry.command) <= 30 else entry.command[:27] + "..."
        lines.append(f"{ts:<22} {status:<10} {duration:>10}  {cmd}")

    lines.append("-" * 60)
    return "\n".join(lines)


def print_summary(options: SummaryOptions) -> None:
    """Print a formatted summary to stdout."""
    entries = build_summary(options)
    print(format_summary_text(entries, options.job_name))
