"""Tests for cronwatch.timeout."""

from __future__ import annotations

import subprocess
import sys
import time

import pytest

from cronwatch.timeout import (
    TimeoutPolicy,
    TimeoutResult,
    enforce_timeout,
)


# ---------------------------------------------------------------------------
# TimeoutPolicy
# ---------------------------------------------------------------------------

class TestTimeoutPolicy:
    def test_defaults(self):
        p = TimeoutPolicy()
        assert p.seconds == 60
        assert p.grace_seconds == 5
        assert p.kill_after == 10
        assert p.enabled is True

    def test_from_dict_full(self):
        p = TimeoutPolicy.from_dict(
            {"seconds": 30, "grace_seconds": 3, "kill_after": 5, "enabled": False}
        )
        assert p.seconds == 30
        assert p.grace_seconds == 3
        assert p.kill_after == 5
        assert p.enabled is False

    def test_from_dict_empty(self):
        p = TimeoutPolicy.from_dict({})
        assert p.seconds == 60
        assert p.enabled is True


# ---------------------------------------------------------------------------
# TimeoutResult
# ---------------------------------------------------------------------------

class TestTimeoutResult:
    def test_ok_when_not_timed_out(self):
        r = TimeoutResult(timed_out=False)
        assert r.ok is True

    def test_not_ok_when_timed_out(self):
        r = TimeoutResult(timed_out=True)
        assert r.ok is False


# ---------------------------------------------------------------------------
# enforce_timeout integration
# ---------------------------------------------------------------------------

def _sleep_proc(seconds: float) -> subprocess.Popen:
    return subprocess.Popen(
        [sys.executable, "-c", f"import time; time.sleep({seconds})"],
        start_new_session=True,
    )


def test_enforce_timeout_disabled_returns_ok():
    proc = _sleep_proc(0.05)
    policy = TimeoutPolicy(enabled=False)
    result = enforce_timeout(proc, policy)
    proc.wait(timeout=2)
    assert result.ok is True
    assert result.timed_out is False


def test_enforce_timeout_sends_sigterm():
    proc = _sleep_proc(60)
    policy = TimeoutPolicy(seconds=1, grace_seconds=1, kill_after=2, enabled=True)
    result = enforce_timeout(proc, policy)
    assert result.timed_out is True
    assert result.signal_sent is not None


def test_enforce_timeout_escalates_to_sigkill():
    # Process that ignores SIGTERM
    code = (
        "import signal, time; "
        "signal.signal(signal.SIGTERM, signal.SIG_IGN); "
        "time.sleep(60)"
    )
    proc = subprocess.Popen(
        [sys.executable, "-c", code],
        start_new_session=True,
    )
    policy = TimeoutPolicy(seconds=1, grace_seconds=1, kill_after=2, enabled=True)
    result = enforce_timeout(proc, policy)
    assert result.timed_out is True
    assert result.escalated_to_kill is True
