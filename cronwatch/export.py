"""Export job history to CSV or JSON formats."""

from __future__ import annotations

import csv
import io
import json
from dataclasses import dataclass
from typing import List, Literal

from cronwatch.history import load_history
from cronwatch.digest import DigestEntry

ExportFormat = Literal["csv", "json"]


@dataclass
class ExportOptions:
    job_name: str
    fmt: ExportFormat = "csv"
    limit: int = 100
    history_dir: str = "~/.cronwatch/history"


def _entries_to_dicts(entries: List[DigestEntry]) -> List[dict]:
    """Convert DigestEntry objects to plain dicts suitable for serialisation."""
    return [
        {
            "job_name": e.job_name,
            "timestamp": e.timestamp.isoformat(),
            "success": e.success,
            "exit_code": e.exit_code,
            "duration": round(e.duration, 3),
            "stderr": e.stderr or "",
        }
        for e in entries
    ]


def export_to_csv(entries: List[DigestEntry]) -> str:
    """Return a CSV string for the given entries."""
    rows = _entries_to_dicts(entries)
    if not rows:
        return ""
    fieldnames = list(rows[0].keys())
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=fieldnames, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return buf.getvalue()


def export_to_json(entries: List[DigestEntry]) -> str:
    """Return a pretty-printed JSON string for the given entries."""
    return json.dumps(_entries_to_dicts(entries), indent=2)


def run_export(options: ExportOptions) -> str:
    """Load history and return exported content as a string."""
    raw = load_history(
        options.job_name,
        limit=options.limit,
        history_dir=options.history_dir,
    )
    entries = [
        DigestEntry(
            job_name=r.job_name,
            timestamp=r.timestamp,
            success=r.success,
            exit_code=r.exit_code,
            duration=r.duration,
            stderr=r.stderr,
        )
        for r in raw
    ]
    if options.fmt == "json":
        return export_to_json(entries)
    return export_to_csv(entries)
