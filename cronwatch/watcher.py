"""Core watch loop: run a job, log it, record history, and notify."""

from __future__ import annotations

import logging
from typing import Optional

from cronwatch.config import CronwatchConfig
from cronwatch.history import record_result
from cronwatch.logger import write_job_log
from cronwatch.notifier import send_notifications
from cronwatch.runner import JobResult, run_job

logger = logging.getLogger(__name__)


def watch(
    command: str,
    config: CronwatchConfig,
    timeout: Optional[int] = None,
    notify_on_success: bool = False,
) -> JobResult:
    """Run *command*, log the result, record history, and dispatch notifications.

    Args:
        command: Shell command string to execute.
        config: Loaded CronwatchConfig instance.
        timeout: Optional override for the job timeout in seconds.
        notify_on_success: When True, send notifications even on success.

    Returns:
        The JobResult produced by running the command.
    """
    effective_timeout = timeout if timeout is not None else config.timeout

    logger.info("Starting job: %s", command)
    result = run_job(command, timeout=effective_timeout)
    logger.info(
        "Job finished: exit_code=%s duration=%.2fs",
        result.exit_code,
        result.duration,
    )

    # Persist structured log entry
    if config.log_dir:
        try:
            write_job_log(result, log_dir=config.log_dir)
        except OSError as exc:
            logger.warning("Failed to write job log: %s", exc)

    # Append to history file
    try:
        record_result(result, history_file=config.history_file)
    except OSError as exc:
        logger.warning("Failed to record history: %s", exc)

    # Notify on failure (or always when flag is set)
    failed = result.exit_code != 0 or result.timed_out
    if failed or notify_on_success:
        send_notifications(result, config)

    return result
