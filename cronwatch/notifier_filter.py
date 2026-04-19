"""Filter notifications based on job result severity and rules."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional
from cronwatch.runner import JobResult


@dataclass
class NotifierFilterOptions:
    enabled: bool = True
    min_duration_seconds: float = 0.0
    only_on_failure: bool = False
    suppress_exit_codes: list[int] = field(default_factory=list)
    require_stderr: bool = False

    @classmethod
    def from_dict(cls, d: dict) -> "NotifierFilterOptions":
        return cls(
            enabled=bool(d.get("enabled", True)),
            min_duration_seconds=float(d.get("min_duration_seconds", 0.0)),
            only_on_failure=bool(d.get("only_on_failure", False)),
            suppress_exit_codes=[int(c) for c in d.get("suppress_exit_codes", [])],
            require_stderr=bool(d.get("require_stderr", False)),
        )


@dataclass
class FilterDecision:
    should_notify: bool
    reason: str

    @property
    def ok(self) -> bool:
        return self.should_notify


def check_notifier_filter(
    result: JobResult,
    opts: Optional[NotifierFilterOptions] = None,
) -> FilterDecision:
    if opts is None or not opts.enabled:
        return FilterDecision(should_notify=True, reason="filter disabled")

    if opts.only_on_failure and result.exit_code == 0:
        return FilterDecision(should_notify=False, reason="only_on_failure: job succeeded")

    if result.exit_code in opts.suppress_exit_codes:
        return FilterDecision(
            should_notify=False,
            reason=f"exit code {result.exit_code} is suppressed",
        )

    if opts.min_duration_seconds > 0 and result.duration < opts.min_duration_seconds:
        return FilterDecision(
            should_notify=False,
            reason=f"duration {result.duration:.2f}s below minimum {opts.min_duration_seconds}s",
        )

    if opts.require_stderr and not (result.stderr or "").strip():
        return FilterDecision(should_notify=False, reason="require_stderr: no stderr output")

    return FilterDecision(should_notify=True, reason="passed all filters")
