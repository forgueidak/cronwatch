"""Integrate budget checks into the job watch pipeline."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from cronwatch.budget import BudgetOptions, BudgetResult, check_budget
from cronwatch.runner import JobResult


@dataclass
class BudgetWatchOptions:
    budget: BudgetOptions

    @classmethod
    def from_dict(cls, data: dict) -> "BudgetWatchOptions":
        return cls(budget=BudgetOptions.from_dict(data.get("budget", {})))


def watch_budget(result: JobResult, opts: BudgetWatchOptions) -> Optional[BudgetResult]:
    """Return a BudgetResult if budget checking is enabled, else None."""
    if not opts.budget.enabled:
        return None
    return check_budget(result.duration, opts.budget)


def format_budget_notice(br: BudgetResult) -> str:
    """Format a human-readable notice for budget warnings or violations."""
    if br.exceeded:
        return (
            f"BUDGET EXCEEDED: job ran for {br.duration_seconds:.1f}s, "
            f"limit is {br.max_seconds:.1f}s."
        )
    if br.warned:
        return (
            f"Budget warning: job ran for {br.duration_seconds:.1f}s "
            f"(warn threshold {br.warn_at_seconds:.1f}s, "
            f"limit {br.max_seconds:.1f}s)."
        )
    return f"Budget ok: {br.duration_seconds:.1f}s / {br.max_seconds:.1f}s."
