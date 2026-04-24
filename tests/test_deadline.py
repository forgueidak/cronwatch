"""Tests for cronwatch/deadline.py"""
from __future__ import annotations

from datetime import datetime, time

import pytest

from cronwatch.deadline import DeadlineOptions, DeadlineResult, check_deadline


# ---------------------------------------------------------------------------
# DeadlineOptions.from_dict
# ---------------------------------------------------------------------------

class TestDeadlineOptionsFromDict:
    def test_defaults(self):
        opts = DeadlineOptions.from_dict({})
        assert opts.enabled is False
        assert opts.by == ""
        assert opts.timezone == "local"

    def test_full(self):
        opts = DeadlineOptions.from_dict(
            {"deadline": {"enabled": True, "by": "06:30", "timezone": "UTC"}}
        )
        assert opts.enabled is True
        assert opts.by == "06:30"
        assert opts.timezone == "UTC"

    def test_enabled_coerced_to_bool(self):
        opts = DeadlineOptions.from_dict({"deadline": {"enabled": 1}})
        assert opts.enabled is True

    def test_missing_nested_key_uses_defaults(self):
        opts = DeadlineOptions.from_dict({"deadline": {}})
        assert opts.enabled is False
        assert opts.by == ""


# ---------------------------------------------------------------------------
# DeadlineOptions._parse_by
# ---------------------------------------------------------------------------

class TestParseBy:
    def test_valid_time(self):
        opts = DeadlineOptions(enabled=True, by="06:00")
        assert opts._parse_by() == time(6, 0)

    def test_single_digit_hour(self):
        opts = DeadlineOptions(enabled=True, by="9:15")
        assert opts._parse_by() == time(9, 15)

    def test_invalid_format_returns_none(self):
        opts = DeadlineOptions(enabled=True, by="not-a-time")
        assert opts._parse_by() is None

    def test_out_of_range_hour_returns_none(self):
        opts = DeadlineOptions(enabled=True, by="25:00")
        assert opts._parse_by() is None

    def test_empty_string_returns_none(self):
        opts = DeadlineOptions(enabled=True, by="")
        assert opts._parse_by() is None


# ---------------------------------------------------------------------------
# check_deadline
# ---------------------------------------------------------------------------

def test_check_deadline_disabled_returns_none():
    opts = DeadlineOptions(enabled=False, by="06:00")
    assert check_deadline(opts) is None


def test_check_deadline_invalid_by_returns_ok_result():
    opts = DeadlineOptions(enabled=True, by="bad")
    result = check_deadline(opts)
    assert result is not None
    assert result.ok() is True
    assert "invalid" in result.summary().lower()


def test_check_deadline_met():
    opts = DeadlineOptions(enabled=True, by="10:00")
    # Run at 09:30 — before the deadline
    now = datetime(2024, 1, 15, 9, 30, 0)
    result = check_deadline(opts, now=now)
    assert result is not None
    assert result.ok() is True
    assert result.missed is False
    assert "met" in result.summary().lower()


def test_check_deadline_missed():
    opts = DeadlineOptions(enabled=True, by="06:00")
    # Run at 07:05 — after the deadline
    now = datetime(2024, 1, 15, 7, 5, 0)
    result = check_deadline(opts, now=now)
    assert result is not None
    assert result.ok() is False
    assert result.missed is True
    assert "missed" in result.summary().lower()


def test_check_deadline_exactly_on_boundary_is_met():
    # current_time == deadline_time → not missed (strict >)
    opts = DeadlineOptions(enabled=True, by="08:00")
    now = datetime(2024, 1, 15, 8, 0, 45)  # seconds stripped
    result = check_deadline(opts, now=now)
    assert result is not None
    assert result.ok() is True


def test_check_deadline_result_contains_deadline_time():
    opts = DeadlineOptions(enabled=True, by="23:59")
    now = datetime(2024, 1, 15, 22, 0, 0)
    result = check_deadline(opts, now=now)
    assert result.deadline_time == time(23, 59)


def test_check_deadline_checked_at_uses_provided_now():
    opts = DeadlineOptions(enabled=True, by="12:00")
    now = datetime(2024, 6, 1, 11, 0, 0)
    result = check_deadline(opts, now=now)
    assert result.checked_at == now
