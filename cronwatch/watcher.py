"""Watcher module: orchestrates job execution, logging, and notifications."""

from __future__ import annotations

import logging
from typing import Optional

from cronwatch.config import CronwatchConfig, load_config
from cronwatch.runner import JobResult, run_job
from cronwatch.logger import write_job_log
from cronwatch.notifier import send_notifications

logger = logging.getLogger(__name__)


def watch(
    command: str,
    job_name: Optional[str] = None,
    config_path: Optional[str] = None,
    timeout: Optional[int] = None,
) -> JobResult:
    """Run *command* under cronwatch supervision.

    Loads configuration, executes the job, writes a structured log entry,
    and dispatches notifications when the job fails (or always, if configured).

    Returns the :class:`~cronwatch.runner.JobResult` for the run.
    """
    cfg: CronwatchConfig = load_config(config_path)

    effective_timeout = timeout if timeout is not None else cfg.timeout
    effective_name = job_name or command

    logger.debug("Starting job '%s' (timeout=%s)", effective_name, effective_timeout)

    result: JobResult = run_job(command, job_name=effective_name, timeout=effective_timeout)

    # Always write a log entry.
    if cfg.log_dir:
        try:
            write_job_log(result, log_dir=cfg.log_dir)
        except Exception as exc:  # pragma: no cover
            logger.warning("Failed to write job log: %s", exc)

    # Notify on failure, or on every run when notify_on_success is set.
    should_notify = (not result.success) or cfg.notify_on_success
    if should_notify:
        try:
            send_notifications(result, cfg)
        except Exception as exc:  # pragma: no cover
            logger.warning("Notification error: %s", exc)

    if result.success:
        logger.info("Job '%s' completed successfully.", effective_name)
    else:
        logger.error(
            "Job '%s' failed (exit_code=%s).", effective_name, result.exit_code
        )

    return result
