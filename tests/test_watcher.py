"""Tests for cronwatch.watcher.watch()."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from cronwatch.runner import JobResult
from cronwatch.watcher import watch


def _make_result(success: bool = True, exit_code: int = 0) -> JobResult:
    return JobResult(
        command="echo hi",
        job_name="test-job",
        exit_code=exit_code,
        stdout="hi",
        stderr="",
        duration=0.1,
        timed_out=False,
    )


@patch("cronwatch.watcher.send_notifications")
@patch("cronwatch.watcher.write_job_log")
@patch("cronwatch.watcher.run_job")
@patch("cronwatch.watcher.load_config")
def test_watch_success_no_notify(mock_cfg, mock_run, mock_log, mock_notify):
    cfg = MagicMock(timeout=30, log_dir="/tmp/logs", notify_on_success=False)
    mock_cfg.return_value = cfg
    mock_run.return_value = _make_result(success=True)

    result = watch("echo hi", job_name="test-job")

    mock_run.assert_called_once_with("echo hi", job_name="test-job", timeout=30)
    mock_log.assert_called_once()
    mock_notify.assert_not_called()  # success + notify_on_success=False
    assert result.success is True


@patch("cronwatch.watcher.send_notifications")
@patch("cronwatch.watcher.write_job_log")
@patch("cronwatch.watcher.run_job")
@patch("cronwatch.watcher.load_config")
def test_watch_failure_triggers_notify(mock_cfg, mock_run, mock_log, mock_notify):
    cfg = MagicMock(timeout=30, log_dir="/tmp/logs", notify_on_success=False)
    mock_cfg.return_value = cfg
    mock_run.return_value = _make_result(success=False, exit_code=1)

    result = watch("false", job_name="test-job")

    mock_notify.assert_called_once()
    assert result.success is False


@patch("cronwatch.watcher.send_notifications")
@patch("cronwatch.watcher.write_job_log")
@patch("cronwatch.watcher.run_job")
@patch("cronwatch.watcher.load_config")
def test_watch_notify_on_success_flag(mock_cfg, mock_run, mock_log, mock_notify):
    cfg = MagicMock(timeout=10, log_dir="/tmp/logs", notify_on_success=True)
    mock_cfg.return_value = cfg
    mock_run.return_value = _make_result(success=True)

    watch("echo hi")

    mock_notify.assert_called_once()


@patch("cronwatch.watcher.send_notifications")
@patch("cronwatch.watcher.write_job_log")
@patch("cronwatch.watcher.run_job")
@patch("cronwatch.watcher.load_config")
def test_watch_uses_explicit_timeout(mock_cfg, mock_run, mock_log, mock_notify):
    cfg = MagicMock(timeout=60, log_dir=None, notify_on_success=False)
    mock_cfg.return_value = cfg
    mock_run.return_value = _make_result(success=True)

    watch("sleep 1", timeout=5)

    mock_run.assert_called_once_with("sleep 1", job_name="sleep 1", timeout=5)


@patch("cronwatch.watcher.send_notifications")
@patch("cronwatch.watcher.write_job_log")
@patch("cronwatch.watcher.run_job")
@patch("cronwatch.watcher.load_config")
def test_watch_skips_log_when_no_log_dir(mock_cfg, mock_run, mock_log, mock_notify):
    cfg = MagicMock(timeout=30, log_dir=None, notify_on_success=False)
    mock_cfg.return_value = cfg
    mock_run.return_value = _make_result(success=True)

    watch("echo hi")

    mock_log.assert_not_called()
