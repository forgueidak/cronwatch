"""Per-job timeout policy with grace period and kill escalation."""

from __future__ import annotations

import os
import signal
import subprocess
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class TimeoutPolicy:
    """Defines how timeouts are enforced for a job."""

    seconds: int = 60
    grace_seconds: int = 5
    kill_after: int = 10
    enabled: bool = True

    @classmethod
    def from_dict(cls, data: dict) -> "TimeoutPolicy":
        return cls(
            seconds=int(data.get("seconds", 60)),
            grace_seconds=int(data.get("grace_seconds", 5)),
            kill_after=int(data.get("kill_after", 10)),
            enabled=bool(data.get("enabled", True)),
        )


@dataclass
class TimeoutResult:
    """Outcome of a timeout enforcement action."""

    timed_out: bool = False
    escalated_to_kill: bool = False
    signal_sent: Optional[int] = None
    message: str = ""

    @property
    def ok(self) -> bool:
        return not self.timed_out


def _send_signal(proc: subprocess.Popen, sig: int) -> bool:
    """Send signal to process group; return True if sent."""
    try:
        os.killpg(os.getpgid(proc.pid), sig)
        return True
    except (ProcessLookupError, PermissionError):
        return False


def enforce_timeout(proc: subprocess.Popen, policy: TimeoutPolicy) -> TimeoutResult:
    """Attempt graceful SIGTERM then escalate to SIGKILL if needed."""
    if not policy.enabled:
        return TimeoutResult()

    sent = _send_signal(proc, signal.SIGTERM)
    result = TimeoutResult(
        timed_out=True,
        signal_sent=signal.SIGTERM if sent else None,
        message="Job exceeded timeout; SIGTERM sent.",
    )

    try:
        proc.wait(timeout=policy.grace_seconds + policy.kill_after)
    except subprocess.TimeoutExpired:
        _send_signal(proc, signal.SIGKILL)
        result.escalated_to_kill = True
        result.signal_sent = signal.SIGKILL
        result.message = "Job did not stop after SIGTERM; SIGKILL sent."
        try:
            proc.wait(timeout=2)
        except subprocess.TimeoutExpired:
            pass

    return result
