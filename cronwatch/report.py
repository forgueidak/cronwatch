"""Generate summary reports for monitored cron jobs."""

from __future__ import annotations

import datetime
from dataclasses import dataclass
from typing import List, Optional

from cronwatch.digest import DigestEntry, build_digest, format_digest_text, success_rate
from cronwatch.history import load_history


@dataclass
class ReportOptions:
    job_name: str
    limit: int = 20
    since: Optional[datetime.datetime] = None
    format: str = "text"  # "text" or "json"


def _filter_entries(
    entries: List[DigestEntry], since: Optional[datetime.datetime]
) -> List[DigestEntry]:
    """Return only entries at or after *since*, if provided."""
    if since is None:
        return entries
    return [e for e in entries if e.timestamp >= since]


def build_report(options: ReportOptions) -> str:
    """Build a human-readable or JSON report for a single job."""
    history = load_history(options.job_name, limit=options.limit)
    digest_entries = build_digest(history)
    filtered = _filter_entries(digest_entries, options.since)

    if not filtered:
        return f"No history found for job '{options.job_name}'."

    if options.format == "json":
        import json

        return json.dumps(
            {
                "job": options.job_name,
                "total": len(filtered),
                "success_rate": round(success_rate(filtered), 4),
                "entries": [
                    {
                        "timestamp": e.timestamp.isoformat(),
                        "success": e.success,
                        "duration": e.duration,
                        "exit_code": e.exit_code,
                    }
                    for e in filtered
                ],
            },
            indent=2,
        )

    return format_digest_text(options.job_name, filtered)


def print_report(options: ReportOptions) -> None:
    """Convenience wrapper that prints the report to stdout."""
    print(build_report(options))
