"""Splay: randomize job start times across a fixed window to avoid thundering herd."""
from __future__ import annotations

import random
import time
from dataclasses import dataclass, field
from typing import Any, Dict, Optional


@dataclass
class SplayOptions:
    enabled: bool = False
    window_seconds: int = 60
    seed: Optional[int] = None  # deterministic splay for testing

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SplayOptions":
        cfg = data.get("splay", {})
        return cls(
            enabled=bool(cfg.get("enabled", False)),
            window_seconds=int(cfg.get("window_seconds", 60)),
            seed=cfg.get("seed"),
        )


@dataclass
class SplayResult:
    enabled: bool
    delay_seconds: float
    skipped: bool = False

    def ok(self) -> bool:
        return True

    def summary(self) -> str:
        if not self.enabled or self.skipped:
            return "splay disabled"
        return f"splay delay={self.delay_seconds:.2f}s window={self.delay_seconds:.2f}s"


def compute_splay(opts: SplayOptions) -> SplayResult:
    """Return a SplayResult with a random delay within the configured window."""
    if not opts.enabled:
        return SplayResult(enabled=False, delay_seconds=0.0, skipped=True)

    rng = random.Random(opts.seed)
    delay = rng.uniform(0, max(0, opts.window_seconds))
    return SplayResult(enabled=True, delay_seconds=delay)


def apply_splay(opts: SplayOptions, *, _sleep=time.sleep) -> SplayResult:
    """Compute splay delay and sleep for that duration."""
    result = compute_splay(opts)
    if result.enabled and not result.skipped:
        _sleep(result.delay_seconds)
    return result


def format_splay_notice(result: SplayResult) -> str:
    if not result.enabled or result.skipped:
        return ""
    return f"[splay] delaying start by {result.delay_seconds:.2f}s"
