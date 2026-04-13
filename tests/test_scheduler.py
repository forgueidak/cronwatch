"""Tests for cronwatch.scheduler."""

from datetime import datetime

import pytest

from cronwatch.scheduler import is_valid_cron, next_run


# ---------------------------------------------------------------------------
# is_valid_cron
# ---------------------------------------------------------------------------


def test_valid_five_field_expression():
    assert is_valid_cron("0 * * * *") is True


def test_valid_named_shortcut_daily():
    assert is_valid_cron("@daily") is True


def test_valid_named_shortcut_hourly():
    assert is_valid_cron("@hourly") is True


def test_invalid_expression_too_few_fields():
    assert is_valid_cron("0 * *") is False


def test_invalid_expression_letters():
    assert is_valid_cron("abc def * * *") is False


def test_invalid_expression_empty():
    assert is_valid_cron("") is False


# ---------------------------------------------------------------------------
# next_run
# ---------------------------------------------------------------------------


_BASE = datetime(2024, 6, 15, 12, 0)  # Saturday, noon


def test_next_run_every_hour():
    result = next_run("0 * * * *", after=_BASE)
    assert result == datetime(2024, 6, 15, 13, 0)


def test_next_run_specific_minute():
    result = next_run("30 * * * *", after=_BASE)
    assert result == datetime(2024, 6, 15, 12, 30)


def test_next_run_daily_midnight():
    result = next_run("@daily", after=_BASE)
    assert result == datetime(2024, 6, 16, 0, 0)


def test_next_run_named_hourly():
    result = next_run("@hourly", after=_BASE)
    assert result == datetime(2024, 6, 15, 13, 0)


def test_next_run_specific_day_of_month():
    # 1st of each month at 08:00
    result = next_run("0 8 1 * *", after=_BASE)
    assert result == datetime(2024, 7, 1, 8, 0)


def test_next_run_raises_for_invalid_expression():
    with pytest.raises(ValueError, match="Invalid cron expression"):
        next_run("bad expression", after=_BASE)


def test_next_run_without_after_returns_future():
    """Smoke-test: result must be in the future when *after* is omitted."""
    result = next_run("* * * * *")
    assert result > datetime.now()
