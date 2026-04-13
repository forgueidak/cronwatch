"""Tests for cronwatch.retry module."""

from __future__ import annotations

from unittest.mock import patch, MagicMock
import pytest

from cronwatch.runner import JobResult
from cronwatch.retry import RetryOptions, RetryResult, run_with_retry


def _make_result(returncode: int = 0, stdout: str = "", stderr: str = "") -> JobResult:
    return JobResult(
        command="echo test",
        returncode=returncode,
        stdout=stdout,
        stderr=stderr,
        duration=0.1,
    )


def _no_sleep(seconds: float) -> None:
    pass


class TestRetryOptions:
    def test_defaults(self):
        opts = RetryOptions()
        assert opts.max_attempts == 1
        assert opts.delay_seconds == 5.0
        assert opts.backoff_factor == 1.0
        assert opts.retry_on_timeout is False


class TestRunWithRetry:
    def test_success_on_first_attempt(self):
        with patch("cronwatch.retry.run_job", return_value=_make_result(0)) as mock_run:
            result = run_with_retry("echo hi", RetryOptions(max_attempts=3), _sleep_fn=_no_sleep)
        assert result.succeeded
        assert result.attempts == 1
        assert mock_run.call_count == 1

    def test_retries_on_failure_then_succeeds(self):
        side_effects = [_make_result(1), _make_result(1), _make_result(0)]
        with patch("cronwatch.retry.run_job", side_effect=side_effects):
            result = run_with_retry("cmd", RetryOptions(max_attempts=3), _sleep_fn=_no_sleep)
        assert result.succeeded
        assert result.attempts == 3
        assert len(result.all_results) == 3

    def test_gives_up_after_max_attempts(self):
        with patch("cronwatch.retry.run_job", return_value=_make_result(1)) as mock_run:
            result = run_with_retry("cmd", RetryOptions(max_attempts=3), _sleep_fn=_no_sleep)
        assert not result.succeeded
        assert result.gave_up
        assert result.attempts == 3
        assert mock_run.call_count == 3

    def test_no_retry_on_timeout_by_default(self):
        timeout_result = _make_result(returncode=-1, stderr="timeout")
        with patch("cronwatch.retry.run_job", return_value=timeout_result) as mock_run:
            result = run_with_retry("cmd", RetryOptions(max_attempts=3), _sleep_fn=_no_sleep)
        assert not result.succeeded
        assert result.attempts == 1
        assert mock_run.call_count == 1

    def test_retry_on_timeout_when_enabled(self):
        timeout_result = _make_result(returncode=-1, stderr="timeout")
        opts = RetryOptions(max_attempts=2, retry_on_timeout=True)
        with patch("cronwatch.retry.run_job", return_value=timeout_result) as mock_run:
            result = run_with_retry("cmd", opts, _sleep_fn=_no_sleep)
        assert mock_run.call_count == 2

    def test_backoff_applied_between_attempts(self):
        sleep_calls: list[float] = []
        side_effects = [_make_result(1), _make_result(1), _make_result(0)]
        opts = RetryOptions(max_attempts=3, delay_seconds=2.0, backoff_factor=2.0)
        with patch("cronwatch.retry.run_job", side_effect=side_effects):
            run_with_retry("cmd", opts, _sleep_fn=sleep_calls.append)
        assert sleep_calls == [2.0, 4.0]

    def test_single_attempt_no_sleep(self):
        sleep_calls: list[float] = []
        with patch("cronwatch.retry.run_job", return_value=_make_result(1)):
            run_with_retry("cmd", RetryOptions(max_attempts=1), _sleep_fn=sleep_calls.append)
        assert sleep_calls == []
