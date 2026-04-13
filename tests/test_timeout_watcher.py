"""Tests for cronwatch.timeout_watcher."""

from __future__ import annotations

import subprocess
import sys
from unittest.mock import MagicMock, patch

import pytest

from cronwatch.timeout import TimeoutPolicy, TimeoutResult
from cronwatch.timeout_watcher import (
    TimeoutWatchOptions,
    annotate_result,
    watch_with_timeout,
)
from cronwatch.runner import JobResult
import datetime


def _make_result(**kwargs) -> JobResult:
    defaults = dict(
        command="echo hi",
        returncode=0,
        stdout="hi",
        stderr="",
        duration=0.1,
        started_at=datetime.datetime.utcnow(),
    )
    defaults.update(kwargs)
    return JobResult(**defaults)


# ---------------------------------------------------------------------------
# TimeoutWatchOptions
# ---------------------------------------------------------------------------

class TestTimeoutWatchOptions:
    def test_defaults(self):
        opts = TimeoutWatchOptions()
        assert opts.policy.seconds == 60
        assert opts.log_escalation is True

    def test_from_dict(self):
        opts = TimeoutWatchOptions.from_dict(
            {"timeout": {"seconds": 45, "enabled": False}, "log_escalation": False}
        )
        assert opts.policy.seconds == 45
        assert opts.policy.enabled is False
        assert opts.log_escalation is False


# ---------------------------------------------------------------------------
# watch_with_timeout
# ---------------------------------------------------------------------------

def test_watch_with_timeout_disabled_returns_none():
    proc = MagicMock(spec=subprocess.Popen)
    opts = TimeoutWatchOptions(policy=TimeoutPolicy(enabled=False))
    result = watch_with_timeout(proc, opts)
    assert result is None
    proc.wait.assert_not_called()


def test_watch_with_timeout_no_timeout_returns_none():
    proc = MagicMock(spec=subprocess.Popen)
    proc.wait.return_value = 0
    opts = TimeoutWatchOptions(policy=TimeoutPolicy(seconds=10))
    result = watch_with_timeout(proc, opts)
    assert result is None


def test_watch_with_timeout_fires_enforce():
    proc = MagicMock(spec=subprocess.Popen)
    proc.wait.side_effect = subprocess.TimeoutExpired(cmd="x", timeout=1)

    fake_tr = TimeoutResult(timed_out=True, message="timed out")
    with patch("cronwatch.timeout_watcher.enforce_timeout", return_value=fake_tr) as mock_enforce:
        opts = TimeoutWatchOptions(policy=TimeoutPolicy(seconds=1))
        result = watch_with_timeout(proc, opts)

    assert result is fake_tr
    mock_enforce.assert_called_once()


# ---------------------------------------------------------------------------
# annotate_result
# ---------------------------------------------------------------------------

def test_annotate_result_no_timeout_unchanged():
    r = _make_result()
    out = annotate_result(r, None)
    assert out is r


def test_annotate_result_timeout_appends_message():
    r = _make_result(returncode=0, stderr="")
    tr = TimeoutResult(timed_out=True, message="Job exceeded timeout; SIGTERM sent.")
    out = annotate_result(r, tr)
    assert "cronwatch" in out.stderr
    assert out.returncode == -1


def test_annotate_result_escalation_noted():
    r = _make_result(returncode=0, stderr="")
    tr = TimeoutResult(timed_out=True, escalated_to_kill=True, message="SIGKILL")
    out = annotate_result(r, tr)
    assert "SIGKILL" in out.stderr
