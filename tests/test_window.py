"""Tests for cronwatch.window — time window enforcement."""

from datetime import datetime

import pytest

from cronwatch.window import (
    WindowOptions,
    WindowResult,
    check_window,
    _parse_time,
)


# ---------------------------------------------------------------------------
# WindowOptions.from_dict
# ---------------------------------------------------------------------------

class TestWindowOptionsFromDict:
    def test_defaults(self):
        opts = WindowOptions.from_dict({})
        assert opts.enabled is False
        assert opts.allowed_hours is None
        assert opts.allowed_weekdays is None
        assert opts.label == "time-window"

    def test_full(self):
        opts = WindowOptions.from_dict({
            "enabled": True,
            "allowed_hours": ["09:00", "17:00"],
            "allowed_weekdays": [0, 1, 2, 3, 4],
            "label": "business-hours",
        })
        assert opts.enabled is True
        assert opts.allowed_hours == ["09:00", "17:00"]
        assert opts.allowed_weekdays == [0, 1, 2, 3, 4]
        assert opts.label == "business-hours"

    def test_enabled_coerced(self):
        opts = WindowOptions.from_dict({"enabled": 1})
        assert opts.enabled is True


# ---------------------------------------------------------------------------
# _parse_time
# ---------------------------------------------------------------------------

def test_parse_time_valid():
    from datetime import time
    assert _parse_time("08:30") == time(8, 30)


def test_parse_time_invalid_raises():
    with pytest.raises(ValueError):
        _parse_time("8")


# ---------------------------------------------------------------------------
# WindowResult
# ---------------------------------------------------------------------------

class TestWindowResult:
    def test_ok_when_allowed(self):
        r = WindowResult(allowed=True, reason="fine")
        assert r.ok() is True

    def test_not_ok_when_blocked(self):
        r = WindowResult(allowed=False, reason="too early")
        assert r.ok() is False

    def test_summary_allowed(self):
        r = WindowResult(allowed=True, reason="within allowed window")
        assert "allowed" in r.summary()

    def test_summary_blocked(self):
        r = WindowResult(allowed=False, reason="outside hours")
        assert "blocked" in r.summary()


# ---------------------------------------------------------------------------
# check_window
# ---------------------------------------------------------------------------

def test_check_window_disabled_returns_none():
    opts = WindowOptions(enabled=False)
    assert check_window(opts) is None


def test_check_window_no_rules_allows():
    opts = WindowOptions(enabled=True)
    result = check_window(opts, now=datetime(2024, 6, 3, 12, 0))  # Monday noon
    assert result is not None
    assert result.allowed is True


def test_check_window_weekday_allowed():
    opts = WindowOptions(enabled=True, allowed_weekdays=[0, 1, 2, 3, 4])
    monday = datetime(2024, 6, 3, 10, 0)  # Monday
    result = check_window(opts, now=monday)
    assert result.allowed is True


def test_check_window_weekday_blocked():
    opts = WindowOptions(enabled=True, allowed_weekdays=[0, 1, 2, 3, 4])
    saturday = datetime(2024, 6, 8, 10, 0)  # Saturday
    result = check_window(opts, now=saturday)
    assert result.allowed is False
    assert "weekday" in result.reason


def test_check_window_hours_allowed():
    opts = WindowOptions(enabled=True, allowed_hours=["09:00", "17:00"])
    noon = datetime(2024, 6, 3, 12, 0)
    result = check_window(opts, now=noon)
    assert result.allowed is True


def test_check_window_hours_blocked_before():
    opts = WindowOptions(enabled=True, allowed_hours=["09:00", "17:00"])
    early = datetime(2024, 6, 3, 7, 30)
    result = check_window(opts, now=early)
    assert result.allowed is False


def test_check_window_hours_blocked_after():
    opts = WindowOptions(enabled=True, allowed_hours=["09:00", "17:00"])
    late = datetime(2024, 6, 3, 20, 0)
    result = check_window(opts, now=late)
    assert result.allowed is False


def test_check_window_invalid_hours_raises():
    opts = WindowOptions(enabled=True, allowed_hours=["09:00"])  # only one entry
    with pytest.raises(ValueError):
        check_window(opts, now=datetime(2024, 6, 3, 10, 0))
