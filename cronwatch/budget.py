"""Runtime budget enforcement — fail a job if it exceeds a wall-clock budget."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class BudgetOptions:
    enabled: bool = False
    max_seconds: float = 60.0
    warn_at_seconds: Optional[float] = None  # warn before hard limit

    @classmethod
    def from_dict(cls, data: dict) -> "BudgetOptions":
        return cls(
            enabled=bool(data.get("enabled", False)),
            max_seconds=float(data.get("max_seconds", 60.0)),
            warn_at_seconds=(
                float(data["warn_at_seconds"]) if "warn_at_seconds" in data else None
            ),
        )


@dataclass
class BudgetResult:
    enabled: bool
    duration_seconds: float
    max_seconds: float
    warn_at_seconds: Optional[float]
    exceeded: bool
    warned: bool

    def ok(self) -> bool:
        return not self.exceeded

    def summary(self) -> str:
        if not self.enabled:
            return "budget: disabled"
        status = "exceeded" if self.exceeded else ("warning" if self.warned else "ok")
        return (
            f"budget: {status} "
            f"({self.duration_seconds:.1f}s / {self.max_seconds:.1f}s max)"
        )


def check_budget(duration_seconds: float, opts: BudgetOptions) -> BudgetResult:
    """Evaluate whether a job's runtime exceeded its budget."""
    if not opts.enabled:
        return BudgetResult(
            enabled=False,
            duration_seconds=duration_seconds,
            max_seconds=opts.max_seconds,
            warn_at_seconds=opts.warn_at_seconds,
            exceeded=False,
            warned=False,
        )

    exceeded = duration_seconds > opts.max_seconds
    warned = (
        not exceeded
        and opts.warn_at_seconds is not None
        and duration_seconds >= opts.warn_at_seconds
    )
    return BudgetResult(
        enabled=True,
        duration_seconds=duration_seconds,
        max_seconds=opts.max_seconds,
        warn_at_seconds=opts.warn_at_seconds,
        exceeded=exceeded,
        warned=warned,
    )
