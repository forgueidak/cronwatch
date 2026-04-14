"""Exponential backoff strategy for retry delays."""
from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class BackoffOptions:
    enabled: bool = False
    base_delay: float = 1.0        # seconds
    multiplier: float = 2.0
    max_delay: float = 60.0
    jitter: bool = True
    jitter_range: float = 0.5      # fraction of computed delay

    @classmethod
    def from_dict(cls, data: dict) -> "BackoffOptions":
        return cls(
            enabled=bool(data.get("enabled", False)),
            base_delay=float(data.get("base_delay", 1.0)),
            multiplier=float(data.get("multiplier", 2.0)),
            max_delay=float(data.get("max_delay", 60.0)),
            jitter=bool(data.get("jitter", True)),
            jitter_range=float(data.get("jitter_range", 0.5)),
        )


@dataclass
class BackoffResult:
    attempt: int
    delay: float
    capped: bool

    def ok(self) -> bool:
        return self.delay >= 0

    def summary(self) -> str:
        cap = " (capped)" if self.capped else ""
        return f"attempt={self.attempt} delay={self.delay:.2f}s{cap}"


def compute_delay(
    opts: BackoffOptions,
    attempt: int,
    _random: Optional[random.Random] = None,
) -> BackoffResult:
    """Return the delay for *attempt* (1-based) using exponential backoff."""
    if not opts.enabled or attempt <= 0:
        return BackoffResult(attempt=attempt, delay=0.0, capped=False)

    rng = _random or random
    raw = opts.base_delay * (opts.multiplier ** (attempt - 1))
    capped = raw >= opts.max_delay
    delay = min(raw, opts.max_delay)

    if opts.jitter:
        spread = delay * opts.jitter_range
        delay = delay + rng.uniform(-spread, spread)
        delay = max(0.0, delay)

    return BackoffResult(attempt=attempt, delay=round(delay, 4), capped=capped)
