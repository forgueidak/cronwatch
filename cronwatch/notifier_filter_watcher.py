"""Integrate NotifierFilter into the notification pipeline."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Optional
from cronwatch.runner import JobResult
from cronwatch.notifier_filter import (
    NotifierFilterOptions,
    FilterDecision,
    check_notifier_filter,
)


@dataclass
class NotifierFilterWatchOptions:
    filter: NotifierFilterOptions = None  # type: ignore[assignment]

    def __post_init__(self):
        if self.filter is None:
            self.filter = NotifierFilterOptions()

    @classmethod
    def from_dict(cls, d: dict) -> "NotifierFilterWatchOptions":
        raw = d.get("notifier_filter", {})
        return cls(filter=NotifierFilterOptions.from_dict(raw))


def should_send_notification(
    result: JobResult,
    opts: Optional[NotifierFilterWatchOptions] = None,
) -> FilterDecision:
    """Return a FilterDecision indicating whether notifications should fire."""
    filter_opts = opts.filter if opts is not None else None
    return check_notifier_filter(result, filter_opts)


def format_suppression_notice(decision: FilterDecision, command: str) -> str:
    return (
        f"[cronwatch] Notification suppressed for '{command}': {decision.reason}"
    )
