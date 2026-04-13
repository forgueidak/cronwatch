"""Retry logic for cron job execution with configurable attempts and backoff."""

from __future__ import annotations

import time
import logging
from dataclasses import dataclass, field
from typing import Callable, Optional

from cronwatch.runner import JobResult, run_job

logger = logging.getLogger(__name__)


@dataclass
class RetryOptions:
    max_attempts: int = 1
    delay_seconds: float = 5.0
    backoff_factor: float = 1.0
    retry_on_timeout: bool = False


@dataclass
class RetryResult:
    final: JobResult
    attempts: int
    all_results: list[JobResult] = field(default_factory=list)

    @property
    def succeeded(self) -> bool:
        return self.final.returncode == 0

    @property
    def gave_up(self) -> bool:
        return not self.succeeded and self.attempts >= 1


def run_with_retry(
    command: str,
    options: RetryOptions,
    timeout: Optional[float] = None,
    _sleep_fn: Callable[[float], None] = time.sleep,
) -> RetryResult:
    """Run a command, retrying on failure according to RetryOptions."""
    all_results: list[JobResult] = []
    delay = options.delay_seconds

    for attempt in range(1, options.max_attempts + 1):
        result = run_job(command, timeout=timeout)
        all_results.append(result)

        if result.returncode == 0:
            logger.debug("Job succeeded on attempt %d: %s", attempt, command)
            return RetryResult(final=result, attempts=attempt, all_results=all_results)

        timed_out = result.returncode == -1 and result.stderr == "timeout"
        if timed_out and not options.retry_on_timeout:
            logger.warning("Job timed out and retry_on_timeout is False; giving up.")
            return RetryResult(final=result, attempts=attempt, all_results=all_results)

        if attempt < options.max_attempts:
            logger.info(
                "Job failed (attempt %d/%d), retrying in %.1fs: %s",
                attempt, options.max_attempts, delay, command,
            )
            _sleep_fn(delay)
            delay *= options.backoff_factor

    logger.warning("Job failed after %d attempt(s): %s", options.max_attempts, command)
    return RetryResult(final=all_results[-1], attempts=options.max_attempts, all_results=all_results)
