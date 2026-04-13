"""Integrate timeout enforcement into the job-watching pipeline."""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from typing import Optional

from cronwatch.runner import JobResult
from cronwatch.timeout import TimeoutPolicy, TimeoutResult, enforce_timeout


@dataclass
class TimeoutWatchOptions:
    policy: TimeoutPolicy = None  # type: ignore[assignment]
    log_escalation: bool = True

    def __post_init__(self) -> None:
        if self.policy is None:
            self.policy = TimeoutPolicy()

    @classmethod
    def from_dict(cls, data: dict) -> "TimeoutWatchOptions":
        policy = TimeoutPolicy.from_dict(data.get("timeout", {}))
        return cls(
            policy=policy,
            log_escalation=bool(data.get("log_escalation", True)),
        )


def watch_with_timeout(
    proc: subprocess.Popen,
    opts: TimeoutWatchOptions,
) -> Optional[TimeoutResult]:
    """Block until *proc* finishes or the timeout policy fires.

    Returns a :class:`TimeoutResult` only when a timeout occurred,
    otherwise returns ``None``.
    """
    if not opts.policy.enabled:
        return None

    try:
        proc.wait(timeout=opts.policy.seconds)
        return None  # finished in time
    except subprocess.TimeoutExpired:
        return enforce_timeout(proc, opts.policy)


def annotate_result(
    result: JobResult,
    timeout_result: Optional[TimeoutResult],
) -> JobResult:
    """Attach timeout metadata to a :class:`JobResult`.

    The original result is returned unchanged when no timeout occurred.
    When a timeout did occur the return code is forced to a non-zero value
    and the timeout message is appended to stderr.
    """
    if timeout_result is None or timeout_result.ok:
        return result

    extra = f"\n[cronwatch] {timeout_result.message}"
    if timeout_result.escalated_to_kill:
        extra += " (escalated to SIGKILL)"

    return JobResult(
        command=result.command,
        returncode=result.returncode if result.returncode != 0 else -1,
        stdout=result.stdout,
        stderr=(result.stderr or "") + extra,
        duration=result.duration,
        started_at=result.started_at,
    )
