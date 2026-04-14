"""Jitter support: add randomized delay before running a cron job.

Useful for spreading load when many jobs share the same schedule.
"""

from __future__ import annotations

import random
import time
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class JitterOptions:
    """Configuration for pre-job random delay."""

    enabled: bool = False
    min_seconds: float = 0.0
    max_seconds: float = 30.0
    seed: Optional[int] = None  # for deterministic testing

    @classmethod
    def from_dict(cls, data: dict) -> "JitterOptions":
        return cls(
            enabled=bool(data.get("enabled", False)),
            min_seconds=float(data.get("min_seconds", 0.0)),
            max_seconds=float(data.get("max_seconds", 30.0)),
            seed=data.get("seed"),
        )


@dataclass
class JitterResult:
    """Outcome of a jitter delay operation."""

    skipped: bool
    delay_seconds: float

    @property
    def ok(self) -> bool:
        return True  # jitter never fails; it only delays or skips

    def summary(self) -> str:
        if self.skipped:
            return "jitter disabled — no delay applied"
        return f"jitter delay applied: {self.delay_seconds:.2f}s"


def apply_jitter(
    opts: JitterOptions,
    *,
    _sleep=time.sleep,
) -> JitterResult:
    """Optionally sleep for a random duration within [min_seconds, max_seconds].

    Args:
        opts: JitterOptions controlling the behaviour.
        _sleep: injectable sleep callable (for testing).

    Returns:
        JitterResult describing what happened.
    """
    if not opts.enabled:
        return JitterResult(skipped=True, delay_seconds=0.0)

    rng = random.Random(opts.seed)
    delay = rng.uniform(opts.min_seconds, opts.max_seconds)
    _sleep(delay)
    return JitterResult(skipped=False, delay_seconds=delay)
