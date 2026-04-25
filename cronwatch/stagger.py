"""Stagger: distribute job start times to avoid thundering herd."""
from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class StaggerOptions:
    enabled: bool = False
    max_delay_seconds: float = 60.0
    seed: str = ""  # extra entropy; defaults to job name at call site
    deterministic: bool = False  # use hash-based delay instead of random

    @classmethod
    def from_dict(cls, data: dict) -> "StaggerOptions":
        raw = data.get("stagger", {})
        return cls(
            enabled=bool(raw.get("enabled", False)),
            max_delay_seconds=float(raw.get("max_delay_seconds", 60.0)),
            seed=str(raw.get("seed", "")),
            deterministic=bool(raw.get("deterministic", False)),
        )


@dataclass
class StaggerResult:
    delay_seconds: float = 0.0
    skipped: bool = False
    reason: str = ""

    def ok(self) -> bool:
        return True  # stagger never blocks a job

    def summary(self) -> str:
        if self.skipped:
            return f"stagger skipped: {self.reason}"
        return f"stagger delay={self.delay_seconds:.2f}s"


def _deterministic_delay(seed: str, max_delay: float) -> float:
    """Return a stable delay in [0, max_delay) derived from seed."""
    digest = hashlib.sha256(seed.encode()).hexdigest()
    fraction = int(digest[:8], 16) / 0xFFFFFFFF
    return round(fraction * max_delay, 3)


def compute_stagger(
    opts: StaggerOptions,
    job_name: str,
    *,
    _random_source=None,  # injectable for tests
) -> StaggerResult:
    """Compute (and optionally apply) a stagger delay."""
    if not opts.enabled:
        return StaggerResult(skipped=True, reason="disabled")

    if opts.max_delay_seconds <= 0:
        return StaggerResult(skipped=True, reason="max_delay_seconds <= 0")

    if opts.deterministic:
        seed = f"{job_name}:{opts.seed}"
        delay = _deterministic_delay(seed, opts.max_delay_seconds)
    else:
        import random
        rng = _random_source or random.Random()
        delay = round(rng.uniform(0, opts.max_delay_seconds), 3)

    return StaggerResult(delay_seconds=delay)


def apply_stagger(
    opts: StaggerOptions,
    job_name: str,
    *,
    _sleep=time.sleep,
    _random_source=None,
) -> StaggerResult:
    """Compute and sleep for the stagger delay, then return the result."""
    result = compute_stagger(opts, job_name, _random_source=_random_source)
    if not result.skipped and result.delay_seconds > 0:
        _sleep(result.delay_seconds)
    return result
