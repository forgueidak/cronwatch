"""Circuit breaker pattern for cron job execution.

Prevents a repeatedly failing job from being retried until a cooldown
period has elapsed, reducing noise and downstream impact.
"""
from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class CircuitBreakerOptions:
    enabled: bool = False
    failure_threshold: int = 3       # consecutive failures before opening
    cooldown_seconds: int = 300      # seconds to stay open before half-open probe
    state_dir: str = "/tmp/cronwatch/circuit"

    @classmethod
    def from_dict(cls, data: dict) -> "CircuitBreakerOptions":
        return cls(
            enabled=bool(data.get("enabled", False)),
            failure_threshold=int(data.get("failure_threshold", 3)),
            cooldown_seconds=int(data.get("cooldown_seconds", 300)),
            state_dir=str(data.get("state_dir", "/tmp/cronwatch/circuit")),
        )


@dataclass
class CircuitState:
    status: str = "closed"           # closed | open | half_open
    consecutive_failures: int = 0
    opened_at: Optional[float] = None


@dataclass
class CircuitResult:
    allowed: bool
    status: str
    reason: str = ""

    @property
    def ok(self) -> bool:
        return self.allowed

    def summary(self) -> str:
        if self.allowed:
            return f"circuit {self.status}: job allowed to run"
        return f"circuit open: {self.reason}"


def _state_path(job_name: str, state_dir: str) -> Path:
    safe = job_name.replace("/", "_").replace(" ", "_")
    return Path(state_dir) / f"{safe}.json"


def load_circuit_state(job_name: str, state_dir: str) -> CircuitState:
    path = _state_path(job_name, state_dir)
    if not path.exists():
        return CircuitState()
    try:
        data = json.loads(path.read_text())
        return CircuitState(
            status=data.get("status", "closed"),
            consecutive_failures=int(data.get("consecutive_failures", 0)),
            opened_at=data.get("opened_at"),
        )
    except (json.JSONDecodeError, OSError):
        return CircuitState()


def save_circuit_state(job_name: str, state: CircuitState, state_dir: str) -> None:
    path = _state_path(job_name, state_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({
        "status": state.status,
        "consecutive_failures": state.consecutive_failures,
        "opened_at": state.opened_at,
    }))


def check_circuit(
    job_name: str,
    opts: CircuitBreakerOptions,
    succeeded: bool,
    now: Optional[float] = None,
) -> CircuitResult:
    """Evaluate and update circuit breaker state for a job run."""
    if not opts.enabled:
        return CircuitResult(allowed=True, status="disabled")

    now = now if now is not None else time.time()
    state = load_circuit_state(job_name, opts.state_dir)

    if state.status == "open":
        elapsed = now - (state.opened_at or now)
        if elapsed < opts.cooldown_seconds:
            remaining = int(opts.cooldown_seconds - elapsed)
            return CircuitResult(
                allowed=False,
                status="open",
                reason=f"cooldown active, {remaining}s remaining",
            )
        # transition to half-open probe
        state.status = "half_open"

    if succeeded:
        state.status = "closed"
        state.consecutive_failures = 0
        state.opened_at = None
    else:
        state.consecutive_failures += 1
        if state.consecutive_failures >= opts.failure_threshold:
            state.status = "open"
            state.opened_at = now

    save_circuit_state(job_name, state, opts.state_dir)
    return CircuitResult(allowed=True, status=state.status)
