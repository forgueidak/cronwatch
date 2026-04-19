"""Tests for cronwatch.notifier_filter."""
import pytest
from cronwatch.notifier_filter import (
    NotifierFilterOptions,
    FilterDecision,
    check_notifier_filter,
)
from cronwatch.runner import JobResult


def _make_result(exit_code=0, duration=1.0, stderr="") -> JobResult:
    return JobResult(
        command="echo hi",
        exit_code=exit_code,
        stdout="out",
        stderr=stderr,
        duration=duration,
        timed_out=False,
    )


def _opts(**kwargs) -> NotifierFilterOptions:
    return NotifierFilterOptions(**kwargs)


class TestNotifierFilterOptionsFromDict:
    def test_defaults(self):
        o = NotifierFilterOptions.from_dict({})
        assert o.enabled is True
        assert o.only_on_failure is False
        assert o.suppress_exit_codes == []
        assert o.min_duration_seconds == 0.0
        assert o.require_stderr is False

    def test_full(self):
        o = NotifierFilterOptions.from_dict({
            "enabled": False,
            "only_on_failure": True,
            "suppress_exit_codes": [1, 2],
            "min_duration_seconds": 5.0,
            "require_stderr": True,
        })
        assert o.enabled is False
        assert o.only_on_failure is True
        assert o.suppress_exit_codes == [1, 2]
        assert o.min_duration_seconds == 5.0
        assert o.require_stderr is True


def test_filter_disabled_always_notifies():
    opts = _opts(enabled=False, only_on_failure=True)
    result = _make_result(exit_code=0)
    d = check_notifier_filter(result, opts)
    assert d.should_notify is True


def test_no_opts_always_notifies():
    result = _make_result(exit_code=1)
    d = check_notifier_filter(result, None)
    assert d.should_notify is True


def test_only_on_failure_suppresses_success():
    opts = _opts(only_on_failure=True)
    d = check_notifier_filter(_make_result(exit_code=0), opts)
    assert d.should_notify is False
    assert "only_on_failure" in d.reason


def test_only_on_failure_allows_failure():
    opts = _opts(only_on_failure=True)
    d = check_notifier_filter(_make_result(exit_code=1), opts)
    assert d.should_notify is True


def test_suppress_exit_code_matches():
    opts = _opts(suppress_exit_codes=[2, 3])
    d = check_notifier_filter(_make_result(exit_code=2), opts)
    assert d.should_notify is False
    assert "2" in d.reason


def test_suppress_exit_code_no_match():
    opts = _opts(suppress_exit_codes=[2, 3])
    d = check_notifier_filter(_make_result(exit_code=1), opts)
    assert d.should_notify is True


def test_min_duration_too_short():
    opts = _opts(min_duration_seconds=10.0)
    d = check_notifier_filter(_make_result(duration=2.0), opts)
    assert d.should_notify is False
    assert "duration" in d.reason


def test_min_duration_long_enough():
    opts = _opts(min_duration_seconds=1.0)
    d = check_notifier_filter(_make_result(duration=5.0), opts)
    assert d.should_notify is True


def test_require_stderr_no_stderr():
    opts = _opts(require_stderr=True)
    d = check_notifier_filter(_make_result(stderr=""), opts)
    assert d.should_notify is False
    assert "stderr" in d.reason


def test_require_stderr_with_stderr():
    opts = _opts(require_stderr=True)
    d = check_notifier_filter(_make_result(stderr="some error"), opts)
    assert d.should_notify is True


def test_filter_decision_ok_property():
    assert FilterDecision(should_notify=True, reason="x").ok is True
    assert FilterDecision(should_notify=False, reason="x").ok is False
