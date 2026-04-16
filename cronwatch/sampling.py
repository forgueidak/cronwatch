"""Sampling: probabilistically skip job notifications or actions."""
from __future__ import annotations
import random
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class SamplingOptions:
    enabled: bool = False
    rate: float = 1.0  # 0.0–1.0; 1.0 means always, 0.0 means never
    seed: Optional[int] = None

    @classmethod
    def from_dict(cls, d: dict) -> "SamplingOptions":
        return cls(
            enabled=bool(d.get("enabled", False)),
            rate=float(d.get("rate", 1.0)),
            seed=d.get("seed"),
        )


@dataclass
class SamplingResult:
    enabled: bool
    rate: float
    sampled: bool  # True → proceed; False → skip

    def ok(self) -> bool:
        return self.sampled

    def summary(self) -> str:
        if not self.enabled:
            return "sampling disabled"
        status = "sampled" if self.sampled else "skipped"
        return f"sampling rate={self.rate:.2f} → {status}"


def should_sample(opts: SamplingOptions, rng: Optional[random.Random] = None) -> SamplingResult:
    """Return a SamplingResult indicating whether this run should proceed."""
    if not opts.enabled:
        return SamplingResult(enabled=False, rate=opts.rate, sampled=True)

    rate = max(0.0, min(1.0, opts.rate))
    r = rng if rng is not None else (random.Random(opts.seed) if opts.seed is not None else random)
    sampled = r.random() < rate
    return SamplingResult(enabled=True, rate=rate, sampled=sampled)
