"""Watcher integration for suppression: decides whether to send a notification."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime

from cronwatch.suppress import SuppressOptions, SuppressResult, check_suppress
from cronwatch.runner import JobResult


@dataclass
class SuppressWatchOptions:
    suppress: SuppressOptions = field(default_factory=SuppressOptions)

    @classmethod
    def from_dict(cls, d: dict) -> "SuppressWatchOptions":
        raw = d.get("suppress", {})
        return cls(suppress=SuppressOptions.from_dict(raw))


def should_suppress_notification(
    opts: SuppressWatchOptions,
    result: JobResult,
    now: Optional[datetime] = None,
) -> SuppressResult:
    """Return a SuppressResult indicating whether the notification should be suppressed."""
    return check_suppress(
        opts.suppress,
        exit_code=result.exit_code,
        now=now,
    )


def format_suppress_notice(result: SuppressResult) -> str:
    return f"[cronwatch] notification suppressed — {result.reason}"
